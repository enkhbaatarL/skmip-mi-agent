# Model Parameter Agent API 사용법

## 한눈에 보기

| 목적 | 사용할 API |
|---|---|
| 결과를 바로 확인 | `POST /model-parameters/scenarios/{scenario_id}/proposals/sync` |
| 운영에서 제안 작업 접수 | `POST /model-parameters/scenarios/{scenario_id}/proposals` |
| 사용자가 검토한 값 확정 | `POST /model-parameters/proposals/{modelParamProposalId}/confirmation` |
| 현재 성공 HTTP 상태 | 세 API 모두 `200` |

경로의 두 ID는 실제 숫자로 바꿉니다. 배포 환경에 따라 경로 앞에 별도 공통 prefix가 붙을 수 있습니다. `userId`는 선택 항목이며, 제안 API는 body 자체를 생략해도 됩니다.

v4 canonical master 21행·활성 16개, LUT-backed 10개·Basecase-only 6개, v1/v3 raw mapping-reachable 10개와 v4 raw executable-binding 16개는 그대로다. 다만 모든 버전의 신규 proposal runtime allow-list는 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment` 5개다. 실제 응답의 `proposalParameters`에는 전략별 raw matching, runtime allow-list, exact Basecase/LUT slot을 모두 통과한 항목만 나타난다. endpoint, request body와 proposal/confirmation payload schema는 바뀌지 않는다.

같은 세 API가 v1 단일 이벤트, `generation_strategy=multi_event_composite_dimensions`인 v3, `generation_strategy=multi_event_model_lever_dimensions`인 v4를 모두 처리한다. 요청자는 버전 필드나 event ID를 추가로 보내지 않으며, path의 `scenario_id`가 속한 scenario group으로 서버가 분기한다.

| 구분 | `scenarioGroupId` | `eventId` |
|---|---|---|
| v1 단일 이벤트 | scenario가 속한 그룹 ID | 그룹의 대표 event ID |
| v3 멀티 이벤트 | 여러 event를 묶는 authoritative 그룹 ID | `null` |
| v4 Lever-native 멀티 이벤트 | 여러 event를 묶는 authoritative 그룹 ID | `null` |

v3/v4에서도 endpoint와 기존 optional `eventId` 필드는 유지된다. 개별 source event와 v4 Lever provenance·미지원 진단은 public proposal 응답에 필드를 추가해 노출하지 않고 내부 state, trace, validation warning과 prompt grounding에만 사용한다.

## 1. 동기 제안 API

```http
POST /model-parameters/scenarios/100/proposals/sync
```

```json
{"userId": 123}
```

아래 Basecase `0.019`와 LUT `0.02063`은 실제 리소스에서 확인한 값입니다. ID와 `proposedValue`는 설명용 샘플입니다.

```json
{
  "status": "success",
  "message": "model parameter proposal completed",
  "data": {
    "modelParamProposalId": 42,
    "scenarioId": 100,
    "scenarioGroupId": 20,
    "eventId": 30,
    "proposalParameters": [{
      "parameterName": "GDP",
      "modelTarget": {
        "modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment",
        "tableName": "table1", "valueFieldNames": ["% change (+/-)"],
        "slotAxesFieldNames": ["Country", "Year"]
      },
      "rationale": "GDP 입력값 제안입니다.",
      "values": [{
        "Country": "United States", "Year": 2026,
        "basecaseValue": 0.019, "lutValue": 0.02063,
        "proposedValue": 0.0185,
        "rationale": "경기 둔화 영향을 반영한 샘플입니다."
      }]
    }]
  }
}
```

`proposalParameters`가 사용자가 검토할 제안 목록입니다. `basecaseValue`는 현재 모델 값, `lutValue`는 참고값, `proposedValue`는 AI 제안값입니다. GDP는 비율 단위이므로 이 샘플의 `0.019`는 `1.9%`, `0.0185`는 `1.85%`를 뜻합니다.

위 식별자는 v1 예시다. 같은 응답이 v3 또는 v4 scenario를 대상으로 하면 `scenarioGroupId`는 그대로 채워지고 `eventId`는 다음처럼 명시적으로 `null`이다.

```json
{"scenarioId": 100, "scenarioGroupId": 20, "eventId": null}
```

## 2. 비동기 제안 API

```http
POST /model-parameters/scenarios/100/proposals
```

```json
{"userId": 123}
```

즉시 다음처럼 응답합니다.

```json
{
  "status": "success",
  "message": "accepted",
  "data": {"modelParamProposalId": 42, "status": "PROCESSING"}
}
```

이 응답은 제안이 끝났다는 뜻이 아니라 **작업 접수 완료**라는 뜻입니다. 현재 HTTP 상태는 `202`가 아니라 `200`입니다.

접수 전 preflight는 v1/v3 direct/routing 또는 v4 executable binding으로 raw 후보를 만든 뒤 runtime allow-list를 적용한다. raw 후보가 있어도 모두 allow-list 밖이면 `PROCESSING` proposal row와 background task를 만들지 않고 `INVALID_REQUEST`를 즉시 반환한다.

처리가 끝나면 callback으로 proposal ID와 다음 상태가 전달됩니다.

| 상태 | 의미 | 연동 측 조치 |
|---|---|---|
| `PROPOSED` | 제안 생성 성공 | 연동 시스템의 별도 조회 기능 또는 DB를 통해 저장 결과 확인 |
| `FAILED` | 제안 생성 실패 | 연동 시스템의 별도 조회 기능 또는 DB에서 오류를 확인하고 재시도 여부 판단 |

callback은 전체 제안값이 아니라 “처리가 끝났으니 저장 결과를 확인하라”는 알림입니다. 이 Agent에는 proposal을 조회하는 `GET` API가 없으므로, 연동 시스템이 제공하는 조회 기능이나 저장 DB 확인 경로가 별도로 필요합니다.

## 3. 확정 API

사용자가 제안값을 유지하거나 수정한 뒤 호출합니다. 동기 응답을 복사했다면 각 값의 `lutValue`는 제거해야 합니다.

```http
POST /model-parameters/proposals/42/confirmation
```

```json
{
  "userId": 123,
  "data": {
    "confirmationParameters": [{
      "parameterName": "GDP",
      "modelTarget": {
        "modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment",
        "tableName": "table1", "valueFieldNames": ["% change (+/-)"],
        "slotAxesFieldNames": ["Country", "Year"]
      },
      "rationale": "사용자가 검토한 값입니다.",
      "values": [{
        "Country": "United States", "Year": 2026,
        "basecaseValue": 0.019, "proposedValue": 0.0185,
        "rationale": "검토 후 이 값으로 확정했습니다."
      }]
    }]
  }
}
```

저장이 끝나면 다음처럼 응답합니다.

```json
{
  "status": "success",
  "message": "model parameter proposal confirmed",
  "data": {"modelParamProposalId": 42, "status": "CONFIRMED"}
}
```

확정할 항목은 최소 1개가 필요합니다. 이미 `CONFIRMED`인 제안을 다시 확정하면 이전 확정 내용을 새 요청으로 바꿉니다.

기존 confirmation 호환성도 유지한다. runtime allow-list는 신규 proposal 생성에만 적용하며 기존 `PROPOSED`/`CONFIRMED` 행이나 confirmation payload를 새로 제한하지 않는다. canonical master에 없는 custom parameter라도 현재의 공통 payload 구조 검증을 통과하면 확정할 수 있다. proposal과 confirmation의 숫자 필드는 persistence의 기존 유한 숫자·정밀도 정규화를 적용하며, public confirmation 필드나 parameter별 min/max·정수·단위 validator가 새로 추가되지는 않는다.

## 4. 오류를 받았을 때 확인할 것

### 4.1 HTTP 상태와 Agent 오류 코드의 차이

HTTP 상태와 `data.error_code`는 서로 다른 값입니다.

- HTTP 상태는 요청의 처리 결과를 나타내는 표준 프로토콜 값입니다. 예: `400`, `404`, `500`
- `data.error_code`는 Agent 내부에서 오류 종류를 구분하는 업무 코드입니다. 예: `-201`, `-202`
- `-201`과 `-202`는 표기상의 기호가 아니라, 실제 JSON number로 전달되는 음수입니다.

예를 들어 scenario를 찾지 못하면 HTTP 응답 상태는 `404`이고 body의 내부 오류 코드는 `-201`입니다.

```http
HTTP/1.1 404 Not Found
```

```json
{
  "status": "error",
  "message": "요청한 리소스를 찾을 수 없습니다 - Scenario context not found: scenario_id=100",
  "data": {
    "error_code": -201,
    "error_name": "ENTITY_NOT_FOUND"
  }
}
```

Model Parameter Agent 처리에서 주로 확인하게 되는 코드는 다음과 같습니다.

| HTTP | `data.error_code` | `data.error_name` | 기본 의미 |
|---:|---:|---|---|
| `503` | `-100` | `RUNTIME_REGISTRY_NOT_READY` | Basecase/LUT 또는 공통 runtime이 준비되지 않음 |
| `404` | `-201` | `ENTITY_NOT_FOUND` | scenario, scenario group 또는 proposal을 찾지 못함 |
| `400` | `-202` | `INVALID_REQUEST` | 요청 또는 처리할 데이터가 유효하지 않음 |
| `500` | `-5002` | `LLM_INVOCATION_ERROR` | LLM 호출 또는 structured output 처리 실패 |
| `500` | `-9999` | `UNKNOWN_ERROR` | 별도로 분류되지 않은 내부 오류 |

HTTP `422`는 path/body 타입 오류나 잘못된 JSON처럼 FastAPI 요청 검증에서 실패한 경우입니다. 이 경우에는 공통 오류 body가 아니라 `{"detail": [...]}` 형식이 반환되므로 `data.error_code`, `data.error_name`, `message`가 없습니다.

### 4.2 비동기 proposal API가 접수 전에 실패하는 경우

`POST /model-parameters/scenarios/{scenario_id}/proposals`는 scenario context에서 전략별 raw 후보를 확인하고 runtime allow-list 5개로 필터한 뒤에만 `PROCESSING` proposal row와 background 작업을 등록합니다. 다음 오류는 background 작업을 시작하기 전에 즉시 반환됩니다.

v4에서 처리 결과가 의미상 비어 있는 경우의 `message`는 `유형 분류 1줄 + 개행 + 상세 사유 1줄`로 고정합니다. 상세 사유는 1자 이상 300자 이하이며, Scenario/Event ID, `candidateKey`·`slotKey` 같은 내부 키와 재실행을 권하는 표현을 포함하지 않습니다. `INVALID_REQUEST(-202)`, HTTP `400`, callback/DB 상태 및 payload 구조는 바뀌지 않습니다.

| 실패 케이스 | HTTP | `data.error_code` | `data.error_name` | `message` |
|---|---:|---:|---|---|
| scenario 또는 scenario group을 찾지 못함 | `404` | `-201` | `ENTITY_NOT_FOUND` | `요청한 리소스를 찾을 수 없습니다 - Scenario context not found: scenario_id={scenario_id}` |
| v1/v3 DB mapping rule 또는 parameter definition이 비어 있음 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - parameter mapping resources not loaded from DB` |
| v3 group relation이 2~5개 경계를 벗어나거나 group event가 선택 dimension lineage에서 orphan임 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - {구체적인 lineage 검증 사유}` |
| v3 `sourceEventIds`가 그룹 밖 event를 가리키거나 `sourceRefs` template이 그룹 관계와 연결되지 않음 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - {구체적인 lineage 검증 사유}` |
| event type과 scenario dimension에 대응하는 유효 mapping 후보가 없음 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - No model parameter mapping candidates found for scenario_id={scenario_id}` |
| v1/v3 raw mapping 후보는 있지만 모두 runtime allow-list 밖임 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - No model parameter mapping candidates found for scenario_id={scenario_id}` |
| v4 group의 API version/strategy 또는 catalog checksum이 현재 v4 catalog와 맞지 않음 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - {구체적인 catalog 검증 사유}` |
| v4 선택 value·primary Lever가 없거나 `sourceEventIds`가 그룹 밖 event를 가리킴 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - {구체적인 Lever lineage 검증 사유}` |
| v4 Lever code/ID가 catalog와 일치하지 않음 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - {구체적인 catalog 검증 사유}` |
| v4 후보 생성에서 `unchanged`·`price_only`·binding 없음·known unsupported·runtime allow-list 제외만 남아 허용 변경 항목이 0개임 | `400` | `-202` | `INVALID_REQUEST` | `파라미터로 반영할 변경 항목이 없습니다.\n이벤트와 시나리오 분기값을 확인했지만, 현재 활성화된 수급모델 파라미터와 연결되는 변경 항목이 없습니다.` |
| v4 executable binding의 active parameter target 정의가 누락됨 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - No model parameter mapping candidates found for scenario_id={scenario_id}; exclusion_reason_codes=['ACTIVE_PARAMETER_DEFINITION_MISSING']` |
| proposal 저장에 필요한 scenario/group ID 또는 v1 대표 event ID가 비정상 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - {field} is required for model parameter proposal persistence` |
| DB 연결 또는 proposal row 생성 중 예상하지 못한 예외 | `500` | `-9999` | `UNKNOWN_ERROR` | `알 수 없는 오류가 발생했습니다. - {원본 예외 메시지}` |
| `scenario_id`, `userId` 타입 또는 JSON 형식 오류 | `422` | 없음 | 없음 | 없음. `detail` 배열 반환 |

전략별 raw 후보가 없거나 runtime allow-list 필터 후 후보가 없는 요청은 `PROCESSING` row를 만들기 전에 거절합니다. proposal row 생성 중 오류가 발생하면 transaction을 rollback하므로 정상적으로 commit된 접수 row는 남지 않습니다.

v3의 `parameter_mapping_ready=false`, 승인 projection 부재, pending 또는 rejected projection은 접수 거절 조건이 아니다. 승인된 projection이 있으면 보조 근거로 사용하고 나머지는 validation warning과 trace에 남긴다. 다만 source lineage 자체가 잘못됐거나 lineage에서 복원한 모든 `(event_type_l2_id, dimKey)`에 유효한 DB mapping 후보가 없으면 위 표처럼 접수 전에 실패한다.

v4는 선택된 dimension value의 `lever_states`만 읽는다. `price_only`, binding 없음, 비활성 parameter, catalog unsupported state와 `direction=unchanged`만 있는 state는 raw 변화 후보에서 제외하고 내부 reason code를 남긴다. 그 뒤 executable raw 후보에 runtime allow-list를 적용한다. 허용 후보가 0개면 proposal row를 저장하지 않는다. catalog checksum이 바뀐 경우 기존 v4 Scenario를 새 catalog로 재해석하지 않으므로, master와 Lever catalog를 원자적으로 적용한 뒤 v4 Scenario를 다시 생성해야 한다.

배포 전 DB에는 scenario group의 전략·dimension·catalog checksum, event의 authoritative link인 group-event relation, v3 dimension-value mapping, v4 active Lever catalog와 proposal `mi_event_id` nullable schema가 먼저 적용되어 있어야 한다. Parameter master와 Lever catalog는 원자적으로 적용한다. Agent는 이 API 호출로 DDL이나 canonical DML을 수행하지 않으며, 필수 테이블·컬럼 또는 nullable 계약이 없으면 시작 시 schema validation이나 context 조회 단계에서 명확히 실패한다.

### 4.3 Background 처리 실패 callback과 DB 오류

접수 후 background 작업에서 실패하면 다음 callback을 보냅니다.

```json
{
  "status": "error",
  "message": "파라미터를 적용할 모델 입력 위치를 찾지 못했습니다.\n액화설비 가동률 파라미터는 확인했지만, 해당 설비와 적용 기간에 대응하는 모델 입력 위치가 없습니다.",
  "data": {
    "modelParamProposalId": 42,
    "scenarioId": 100,
    "scenarioGroupId": 20,
    "eventId": null,
    "status": "FAILED"
  }
}
```

위 callback은 v4 Step2 실패 예시다. v3/v4 성공·실패 callback은 같은 필드를 유지하되 `eventId: null`을 보내고, `scenarioGroupId`로 대상 그룹을 식별한다.

현재 실패 callback에는 별도의 `code` 또는 `errorCode` 필드가 없습니다.

- callback `status`: `error`
- callback `data.status`: `FAILED`
- callback `message`: 발생한 예외의 `str(exc)`
- callback code: 없음

같은 실패를 `tmm_mi_model_param_proposal_m`에는 다음과 같이 저장합니다.

| DB 컬럼 | 저장값 |
|---|---|
| `status` | `FAILED` |
| `proposal_parameters` | `[]` |
| `error_code` | `MIBaseError`이면 `INVALID_REQUEST` 같은 `ErrorCode` 이름, 그 외에는 `ValueError` 같은 Python 예외 클래스명 |
| `error_message` | callback `message`와 동일한 `str(exc)` |
| `proposal_completed_dtm` | 실패 처리 시각 |

대표적인 background 실패값은 다음과 같습니다.

runtime allow-list에서 모두 제외된 요청은 background를 시작하지 않으므로 아래 표의 `FAILED` callback/DB 유형이 아니다.

| 실패 케이스 | callback code | DB `error_code` | callback `message` / DB `error_message` |
|---|---|---|---|
| background 재조회 시 scenario/group이 사라짐 | 없음 | `ENTITY_NOT_FOUND` | `[ENTITY_NOT_FOUND] 요청한 리소스를 찾을 수 없습니다 - Scenario context not found: scenario_id={scenario_id}` |
| mapping 리소스가 비어 있음 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - parameter mapping resources not loaded from DB` |
| v1/v3 후보 검증 후 유효 mapping 후보가 없음 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - No model parameter mapping candidates found for scenario_id={scenario_id}` |
| v4 catalog checksum/code/ID 또는 primary Lever 검증 실패 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - {구체적인 catalog/Lever 검증 사유}` |
| v4 후보 생성에서 의미상 변경 항목이 없음 | 없음 | `INVALID_REQUEST` | `파라미터로 반영할 변경 항목이 없습니다.\n이벤트와 시나리오 분기값을 확인했지만, 현재 활성화된 수급모델 파라미터와 연결되는 변경 항목이 없습니다.` |
| v4 Step1.5에서 적용 조건을 충족하는 후보가 없음 | 없음 | `INVALID_REQUEST` | `파라미터로 반영할 변경 항목이 없습니다.\nGDP·PMI 파라미터 후보는 확인했지만, 시나리오·이벤트 근거와 파라미터 적용 조건을 함께 충족하는 항목을 확정하지 못했습니다.` |
| v4 Step2에서 유효한 모델 입력 위치가 없음 | 없음 | `INVALID_REQUEST` | `파라미터를 적용할 모델 입력 위치를 찾지 못했습니다.\n액화설비 가동률 파라미터는 확인했지만, 해당 설비와 적용 기간에 대응하는 모델 입력 위치가 없습니다.` |
| v4 Step3에서 유효한 적용값이 없음 | 없음 | `INVALID_REQUEST` | `적용할 파라미터 값을 생성하지 못했습니다.\n액화설비 가동률 파라미터와 모델 입력 위치는 확인했지만, 시나리오·이벤트 근거와 기준값에 부합하는 유효한 적용 수치를 생성하지 못했습니다.` |
| v1/v3 최종 유효 proposal parameter가 없음 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id={scenario_id}`. 뒤에 최근 validation warning이 최대 3개 붙을 수 있음 |
| Model Parameter 리소스 runtime이 등록되지 않음 | 없음 | `RUNTIME_REGISTRY_NOT_READY` | `[RUNTIME_REGISTRY_NOT_READY] Runtime Registry 준비 안됨 - model parameter resource runtime has not been registered` |
| LLM 호출 또는 structured output 처리 실패 | 없음 | `LLM_INVOCATION_ERROR` | `[LLM_INVOCATION_ERROR] LLM 호출 후 비정상 오류가 발생했습니다. - {원본 원인}` |
| Basecase/LUT 설정 또는 도메인 검증 실패 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - {구체적인 검증 사유}` |
| 예상하지 못한 일반 예외 | 없음 | 예외 클래스명. 예: `ValueError`, `OperationalError` | 원본 `str(exc)`. 예: `value proposal failed` |

일반 `MIBaseError`는 즉시 API가 `exc.error_message`, background가 `str(exc)`를 사용하므로 background message 앞에 `[INVALID_REQUEST]` 같은 오류 이름이 붙습니다. 단, 위 v4 의미상 빈 결과 3개 유형은 전용 오류가 두 값을 같은 2줄 문구로 맞추므로 동기 API, background DB, callback에서 동일하게 출력됩니다. 즉시 응답의 숫자 코드 `-202`, `-5002` 등은 background DB와 callback에 저장하거나 전달하지 않습니다.

### 4.4 Callback 전송 자체가 실패한 경우

proposal 생성 실패와 callback 전송 실패는 별도로 관리합니다.

| callback 처리 결과 | DB `callback_status` |
|---|---|
| callback 전송 성공 | `SUCCEEDED` |
| `skip_callback=true` | `SKIPPED` |
| callback URL 생성, 인증 또는 HTTP 전송 실패 | `FAILED` |

callback 전송 실패 원인은 proposal의 `error_code`와 `error_message`에 저장하지 않습니다. proposal 생성 결과인 `PROPOSED` 또는 `FAILED`도 그대로 유지합니다.

background 실패를 proposal row에 기록하는 작업 자체가 실패하면 실패 callback 생성과 전송까지 진행되지 않습니다. 이 경우 proposal row가 `PROCESSING`으로 남을 수 있으므로 서버 로그와 DB 상태를 함께 확인해야 합니다.

### 4.5 HTTP 상태별 우선 확인 항목

| HTTP | 주로 뜻하는 것 | 먼저 확인할 내용 |
|---:|---|---|
| `400` | 처리할 후보가 없거나 요청 내용이 올바르지 않음 | 파라미터명, 위치 필드, 빈 목록, 현재 상태 |
| `404` | scenario 또는 proposal을 찾지 못함 | URL의 ID와 삭제 여부 |
| `422` | JSON 형식이나 타입이 맞지 않음 | 필수 `data`, 숫자 ID, 배열·객체 구조 |
| `500` | 제안 생성 과정에서 내부 처리 실패 | 서버 로그와 저장된 오류 정보 |
| `503` | Basecase/LUT 준비가 되지 않음 | 전용 Agent 시작 및 리소스 준비 상태 |

즉시 오류 응답은 `message`, `data.error_code`, `data.error_name`을 함께 기록합니다. background 오류는 callback에 code가 없으므로 callback `message`와 proposal DB row의 `error_code`, `error_message`를 함께 기록합니다.

제안 과정은 [Flow 문서](04_MODEL_PARAMETER_AGENT_FLOW.md)를 참고합니다.
