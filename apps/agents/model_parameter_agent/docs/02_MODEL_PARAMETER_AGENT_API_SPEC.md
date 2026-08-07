# Model Parameter Agent API 사용법

## 한눈에 보기

| 목적 | 사용할 API |
|---|---|
| 결과를 바로 확인 | `POST /model-parameters/scenarios/{scenario_id}/proposals/sync` |
| 운영에서 제안 작업 접수 | `POST /model-parameters/scenarios/{scenario_id}/proposals` |
| 사용자가 검토한 값 확정 | `POST /model-parameters/proposals/{modelParamProposalId}/confirmation` |
| 현재 성공 HTTP 상태 | 세 API 모두 `200` |

경로의 두 ID는 실제 숫자로 바꿉니다. 배포 환경에 따라 경로 앞에 별도 공통 prefix가 붙을 수 있습니다. `userId`는 선택 항목이며, 제안 API는 body 자체를 생략해도 됩니다.

master 활성 범위가 canonical 10개로 확장되어도 이 문서의 endpoint, request body, proposal/confirmation payload schema는 바뀌지 않는다. 실제 응답의 `proposalParameters`에는 해당 scenario의 활성 direct/routing mapping과 exact LUT/Basecase slot을 통과한 항목만 나타난다.

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

`POST /model-parameters/scenarios/{scenario_id}/proposals`는 scenario context와 DB mapping 후보를 확인하고 `PROCESSING` proposal row를 만든 뒤 background 작업을 등록합니다. 다음 오류는 background 작업을 시작하기 전에 즉시 반환됩니다.

| 실패 케이스 | HTTP | `data.error_code` | `data.error_name` | `message` |
|---|---:|---:|---|---|
| scenario 또는 scenario group을 찾지 못함 | `404` | `-201` | `ENTITY_NOT_FOUND` | `요청한 리소스를 찾을 수 없습니다 - Scenario context not found: scenario_id={scenario_id}` |
| DB mapping rule 또는 parameter definition이 비어 있음 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - parameter mapping resources not loaded from DB` |
| event type과 scenario dimension에 대응하는 유효 mapping 후보가 없음 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - No model parameter mapping candidates found for scenario_id={scenario_id}` |
| proposal 저장에 필요한 scenario/group/event ID가 비정상 | `400` | `-202` | `INVALID_REQUEST` | `요청이 유효하지 않습니다. - {field} is required for model parameter proposal persistence` |
| DB 연결 또는 proposal row 생성 중 예상하지 못한 예외 | `500` | `-9999` | `UNKNOWN_ERROR` | `알 수 없는 오류가 발생했습니다. - {원본 예외 메시지}` |
| `scenario_id`, `userId` 타입 또는 JSON 형식 오류 | `422` | 없음 | 없음 | 없음. `detail` 배열 반환 |

mapping 후보가 없는 요청은 `PROCESSING` row를 만들기 전에 거절합니다. proposal row 생성 중 오류가 발생하면 transaction을 rollback하므로 정상적으로 commit된 접수 row는 남지 않습니다.

### 4.3 Background 처리 실패 callback과 DB 오류

접수 후 background 작업에서 실패하면 다음 callback을 보냅니다.

```json
{
  "status": "error",
  "message": "[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id=100",
  "data": {
    "modelParamProposalId": 42,
    "scenarioId": 100,
    "scenarioGroupId": 20,
    "eventId": 30,
    "status": "FAILED"
  }
}
```

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

| 실패 케이스 | callback code | DB `error_code` | callback `message` / DB `error_message` |
|---|---|---|---|
| background 재조회 시 scenario/group이 사라짐 | 없음 | `ENTITY_NOT_FOUND` | `[ENTITY_NOT_FOUND] 요청한 리소스를 찾을 수 없습니다 - Scenario context not found: scenario_id={scenario_id}` |
| mapping 리소스가 비어 있음 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - parameter mapping resources not loaded from DB` |
| 후보 검증 후 유효 mapping 후보가 없음 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - No model parameter mapping candidates found for scenario_id={scenario_id}` |
| 최종 유효 proposal parameter가 없음 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id={scenario_id}`. 뒤에 최근 validation warning이 최대 3개 붙을 수 있음 |
| Model Parameter 리소스 runtime이 등록되지 않음 | 없음 | `RUNTIME_REGISTRY_NOT_READY` | `[RUNTIME_REGISTRY_NOT_READY] Runtime Registry 준비 안됨 - model parameter resource runtime has not been registered` |
| LLM 호출 또는 structured output 처리 실패 | 없음 | `LLM_INVOCATION_ERROR` | `[LLM_INVOCATION_ERROR] LLM 호출 후 비정상 오류가 발생했습니다. - {원본 원인}` |
| Basecase/LUT 설정 또는 도메인 검증 실패 | 없음 | `INVALID_REQUEST` | `[INVALID_REQUEST] 요청이 유효하지 않습니다. - {구체적인 검증 사유}` |
| 예상하지 못한 일반 예외 | 없음 | 예외 클래스명. 예: `ValueError`, `OperationalError` | 원본 `str(exc)`. 예: `value proposal failed` |

같은 `MIBaseError`라도 즉시 API 응답과 background의 `message` 형식은 다릅니다. 즉시 API는 `exc.error_message`를 사용하지만 background는 `str(exc)`를 사용하므로 background message 앞에는 `[INVALID_REQUEST]`와 같은 오류 이름이 붙습니다. 또한 즉시 응답의 숫자 코드 `-202`, `-5002` 등은 background DB와 callback에 저장하거나 전달하지 않습니다.

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
