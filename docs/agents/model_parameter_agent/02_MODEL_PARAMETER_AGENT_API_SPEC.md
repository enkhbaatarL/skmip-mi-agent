# Model Parameter Agent API Spec

> 현재 핵심 Skill과 release 판정은 `api_version=v4`,
> `generation_strategy=multi_event_model_lever_dimensions`만 실행한다. v1/v3 항목은 기존 API 호환과
> 저장 데이터 해석을 위한 참고 계약이다.

## 기준

| 목적 | 사용할 API |
|---|---|
| 결과를 바로 확인 | `POST /model-parameters/scenarios/{scenario_id}/proposals/sync` |
| 운영에서 제안 작업 접수 | `POST /model-parameters/scenarios/{scenario_id}/proposals` |
| 사용자가 검토한 값 확정 | `POST /model-parameters/proposals/{modelParamProposalId}/confirmation` |
| 현재 성공 HTTP 상태 | 세 API 모두 `200` |

경로의 두 ID는 실제 숫자로 바꾼다. 배포 환경에 따라 경로 앞에 별도 공통 prefix가 붙을 수 있다. `userId`는 선택 항목이며, 제안 API는 body 자체를 생략해도 된다.

외부개발 DB v4.1 기준선은 master 24행·활성 16개, Agent proposal capability 16개
(LUT-backed 10개 + Basecase-only 6개),
v1/v3 raw mapping-reachable 전역 합집합 10개와 v4 effective executable-binding 전역 합집합 16개다.
v4.1 active Lever는 21개이고 binding occurrence는 56개(conditional 37개)다. 이 수치는 요청 하나의
후보 수가 아니다. v1/v3는 기존 5종 이름 allow-list를 유지하고, v4 extend16은 DB ID/name/target과
`model-parameter-proposal-capabilities-v4`가 일치하는 ID
`{4, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 24}`을 허용한다. 실제 응답의 `proposalParameters`에는 요청별 raw matching, version별 capability gate,
exact Basecase/LUT slot을 모두 통과한 하위 집합만 나타난다. endpoint, request body와
proposal/confirmation의 파라미터 JSON shape는 유지한다. proposal 결과에는 처리 결과를 명확히 구분하기 위한
`status`, `resultCode`, `resultMessage`, `resultStage`가 추가된다.

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

아래 값과 ID는 응답 shape과 숫자 의미를 설명하기 위한 예시다.

```json
{
  "status": "success",
  "message": "model parameter proposal completed",
  "data": {
    "modelParamProposalId": 42,
    "scenarioId": 100,
    "scenarioGroupId": 20,
    "eventId": 30,
    "status": "PROPOSED",
    "resultCode": null,
    "resultMessage": null,
    "resultStage": null,
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

`proposalParameters`가 사용자가 검토할 제안 목록이다. `basecaseValue`는 현재 모델 값, `lutValue`는 참고값, `proposedValue`는 AI 제안값이다. GDP는 비율 단위이므로 이 샘플의 `0.019`는 `1.9%`, `0.0185`는 `1.85%`를 뜻한다.

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

즉시 다음처럼 응답한다.

```json
{
  "status": "success",
  "message": "accepted",
  "data": {"modelParamProposalId": 42, "status": "PROCESSING"}
}
```

이 응답은 제안이 끝났다는 뜻이 아니라 **작업 접수 완료**라는 뜻이다. 현재 HTTP 상태는 `202`가 아니라 `200`이다.

접수 단계는 scenario context의 기본 무결성을 확인한 뒤 항상 `PROCESSING` proposal row를 만들고 background
작업을 등록한다. 제안 범위 밖, 근거 부족, 입력 위치 미확정처럼 정상적으로 “제안하지 않음”을 판단해야 하는
경우도 이 작업 이력에서 `ABSTAINED`로 종결한다. catalog checksum/ID 불일치나 필수 정의 누락처럼 실행 계약이
깨진 경우는 `FAILED`다.

접수 시 `tmd_mdl_scnrcasem.actv_base_yn='Y'` 행을 최대 1건으로 확정해 proposal의
`mi_base_case_id`에 저장한다. background 작업은 그 저장값을 다시 읽으므로 처리 중 활성 Base가
바뀌어도 요청의 기준은 바뀌지 않는다. 활성 Base가 없으면 `NULL`을 저장하고 기존 설정
Basecase를 사용한다. 이 식별자는 내부 추적용이며 기존 요청·응답·callback JSON은 변경하지 않는다.

이 preflight는 resource runtime 등록 여부까지 보장하지 않는다. 허용 후보가 있어 HTTP `200`과 `PROCESSING`을
받은 뒤 background graph에서 Basecase/LUT runtime 미등록을 발견하면 proposal row는 `FAILED`가 되고 실패
callback이 전달된다. 같은 조건을 동기 API가 graph 실행 중 발견하면 즉시 HTTP `503`과
`RUNTIME_REGISTRY_NOT_READY`를 반환한다.

처리가 끝나면 callback으로 proposal ID와 다음 상태가 전달된다.

| 상태 | 의미 | 연동 측 조치 |
|---|---|---|
| `PROPOSED` | 제안 생성 성공 | 연동 시스템의 별도 조회 기능 또는 DB를 통해 저장 결과 확인 |
| `ABSTAINED` | 정상 판단 결과 제안값을 만들지 않음 | `resultCode`와 `resultMessage`로 미제안 사유 표시 |
| `FAILED` | 제안 생성 실패 | 연동 시스템의 별도 조회 기능 또는 DB에서 오류를 확인하고 재시도 여부 판단 |

callback은 전체 제안값이 아니라 “처리가 끝났으니 저장 결과를 확인하라”는 알림이다. 이 Agent에는 proposal을 조회하는 `GET` API가 없으므로, 연동 시스템이 제공하는 조회 기능이나 저장 DB 확인 경로가 별도로 필요하다.

## 3. 확정 API

사용자가 제안값을 유지하거나 수정한 뒤 호출한다. 동기 응답을 복사했다면 각 값의 `lutValue`는 제거해야 한다.

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

저장이 끝나면 다음처럼 응답한다.

```json
{
  "status": "success",
  "message": "model parameter proposal confirmed",
  "data": {"modelParamProposalId": 42, "status": "CONFIRMED"}
}
```

확정할 항목은 최소 1개가 필요하다. 이미 `CONFIRMED`인 제안을 다시 확정하면 이전 확정 내용을 새 요청으로 바꾼다.

기존 confirmation 호환성도 유지한다. runtime allow-list는 신규 proposal 생성에만 적용하며 기존 `PROPOSED`/`CONFIRMED` 행이나 confirmation payload를 새로 제한하지 않는다. Confirmation은 원래 proposal과 항목·값이 같은지 비교하지 않으므로 사용자가 항목을 수정·추가·삭제할 수 있고, canonical master에 없는 custom parameter도 공통 payload 구조 검증을 통과하면 확정할 수 있다. 각 value 객체에는 `basecaseValue`, `proposedValue`, `rationale` key가 모두 필요하지만 `proposedValue` 값은 `null`일 수 있다. `null`이 아닌 값만 persistence 경계에서 엄격한 유한 숫자로 정규화한다. proposal Step3에서 생성하는 `proposedValue`는 유한 숫자여야 한다. 두 경로 모두 설정 기반 소수 자릿수 round/trunc/ceil을 적용하지 않으며, Basecase/LUT 기준값의 기존 정밀도 정책은 유지한다. public confirmation 필드나 parameter별 min/max·정수·단위 validator가 새로 추가되지는 않는다.

## 4. 오류를 받았을 때 확인할 것

### 4.1 HTTP 상태와 Agent 오류 코드의 차이

HTTP 상태와 `data.error_code`는 서로 다른 값이다.

- HTTP 상태는 요청의 처리 결과를 나타내는 표준 프로토콜 값이다. 예: `400`, `404`, `500`
- `data.error_code`는 Agent 내부에서 오류 종류를 구분하는 업무 코드다. 예: `-201`, `-202`
- `-201`과 `-202`는 표기상의 기호가 아니라, 실제 JSON number로 전달되는 음수다.

예를 들어 scenario를 찾지 못하면 HTTP 응답 상태는 `404`이고 body의 내부 오류 코드는 `-201`이다.

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

Model Parameter Agent 처리에서 주로 확인하게 되는 코드는 다음과 같다.

| HTTP | `data.error_code` | `data.error_name` | 기본 의미 |
|---:|---:|---|---|
| `503` | `-100` | `RUNTIME_REGISTRY_NOT_READY` | 동기 graph 실행에서 Basecase/LUT 또는 공통 runtime이 준비되지 않음 |
| `404` | `-201` | `ENTITY_NOT_FOUND` | scenario, scenario group 또는 proposal을 찾지 못함 |
| `400` | `-202` | `INVALID_REQUEST` | 요청 또는 처리할 데이터가 유효하지 않음 |
| `500` | `-5002` | `LLM_INVOCATION_ERROR` | LLM 호출 또는 structured output 처리 실패 |
| `500` | `-9999` | `UNKNOWN_ERROR` | 별도로 분류되지 않은 내부 오류 |

HTTP `422`는 path/body 타입 오류나 잘못된 JSON처럼 FastAPI 요청 검증에서 실패한 경우다. 이 경우에는 공통 오류 body가 아니라 `{"detail": [...]}` 형식이 반환되므로 `data.error_code`, `data.error_name`, `message`가 없다.

### 4.2 접수 오류와 background 결과의 경계

`POST /model-parameters/scenarios/{scenario_id}/proposals`는 scenario context가 조회되면 `PROCESSING` row를 먼저
만든다. 후보가 없거나 제안 범위 밖인 경우도 background에서 판정해 `ABSTAINED` 이력과 callback을 남긴다.
scenario/group 부재, 접수 row 생성 실패, path/body 검증 오류만 background 시작 전 HTTP 오류로 반환한다.

catalog checksum·Lever ID 불일치, 필수 parameter target 누락, 잘못된 lineage처럼 실행 계약 자체가 깨진 경우는
정상적인 미제안이 아니므로 `FAILED`다. proposal row 생성 중 오류가 발생하면 transaction을 rollback한다.

### 4.3 Background 보류·실패 callback과 DB 결과

정상적으로 판단했지만 제안값을 만들지 않은 경우 callback 예시는 다음과 같다.

```json
{
  "status": "success",
  "message": "파라미터를 적용할 위치를 찾지 못했습니다.\n관련 항목은 확인했지만 적용할 위치를 확정하지 못했습니다.",
  "data": {
    "modelParamProposalId": 42,
    "scenarioId": 100,
    "scenarioGroupId": 20,
    "eventId": null,
    "status": "ABSTAINED",
    "resultCode": "ABSTAINED_MODEL_INPUT_NOT_FOUND",
    "resultMessage": "파라미터를 적용할 위치를 찾지 못했습니다.\n관련 항목은 확인했지만 적용할 위치를 확정하지 못했습니다.",
    "resultStage": "step2"
  }
}
```

실패 callback은 최상위 `status=error`, `data.status=FAILED`이며 같은 `resultCode`와 `resultMessage` 필드를
사용한다. `PROPOSED` callback은 `resultCode`, `resultMessage`, `resultStage`가 `null`이다.

| 결과 | DB `status` | DB `error_code` | callback `data.resultCode` |
|---|---|---|---|
| 제안 성공 | `PROPOSED` | `NULL` | `null` |
| 정상 미제안 | `ABSTAINED` | 아래 `ABSTAINED_*` 사유 코드 | DB와 같은 사유 코드 |
| 처리 오류 | `FAILED` | `ErrorCode` 이름 | DB와 같은 오류 코드 |

보류 사유 코드는 다음과 같다. 보류는 오류가 아니므로 별도 음수 숫자 오류 코드를 만들지 않는다.

| 코드 | 의미 | 대표 단계 |
|---|---|---|
| `ABSTAINED_OUT_OF_PROPOSAL_SCOPE` | 후보가 현재 제안 지원 범위 밖이거나 연결 가능한 후보가 없음 | `candidate_generation` |
| `ABSTAINED_INSUFFICIENT_EVIDENCE` | 후보는 있지만 시나리오·이벤트 근거가 부족함 | `step1_5` 또는 `step2` |
| `ABSTAINED_MODEL_INPUT_NOT_FOUND` | 제안 범위 안이지만 exact 모델 입력 위치를 찾지 못함 | `step2` |
| `ABSTAINED_VALUE_NOT_GENERATED` | 입력 위치는 있으나 유효한 값을 생성하지 못함 | `step3` |
| `ABSTAINED_VALUE_OUT_OF_RANGE` | 생성값이 허용 수치 범위를 벗어나 모두 제외됨 | `step3` |
| `ABSTAINED_NO_CHANGE` | Lever가 모두 unchanged이거나 제안값이 기준값과 모두 같음 | `candidate_generation` 또는 `step3` |

예를 들어 제안 범위 밖 결과의 화면 문구는 다음과 같다.

```text
파라미터로 반영할 변경 항목이 없습니다.
시나리오에서 변경 가능성이 있는 항목을 확인했지만, 현재 자동 제안 대상에 포함되지 않아 제안에서 제외했습니다.
```

일부 항목만 제외되고 하나 이상의 유효 제안값이 남으면 전체 결과는 `PROPOSED`다. `ABSTAINED`는 최종 유효
제안값이 0개인 정상 판단에만 사용한다. Step2/Step3 LLM이 응답을 반환했지만 선택 위치나 값이 모두 형식
검증에서 탈락한 경우는 정상 미제안이 아니라 `LLM_INVALID_RESPONSE_ERROR`로 실패 처리한다.

실패의 공통 숫자 코드는 기존 즉시 오류 응답 계약을 유지한다.

| `resultCode` / DB `error_code` | 숫자 코드 | 의미 |
|---|---:|---|
| `LLM_RESPONSE_TIMEOUT` | `-5000` | LLM 응답 시간 초과 |
| `LLM_INVALID_RESPONSE_ERROR` | `-5001` | LLM 응답 형식 또는 검증 오류 |
| `LLM_INVOCATION_ERROR` | `-5002` | LLM 호출 처리 오류 |
| `INVALID_REQUEST` | `-202` | 요청·도메인 계약 오류 |
| `RDB_DATA_FETCH_FAILED` / `RDB_ACCESS_DENIED` | `-6000` / `-6001` | DB 조회 또는 권한 오류 |
| `HTTP_CONNECTION_ERROR` | `-7000` | 외부 HTTP 연결 오류 |
| `UNKNOWN_ERROR` | `-9999` | 분류되지 않은 내부 오류 |

화면에 전달하는 실패 문구는 코드와 분리해 다음 사용자 표현을 사용한다.

| 실패 유형 | `resultMessage` 상세 문구 |
|---|---|
| 처리 시간 초과 | `제안 내용을 만드는 데 시간이 오래 걸려 처리를 완료하지 못했습니다. 잠시 후 다시 시도해 주세요.` |
| 제안 내용 생성·검증 오류 | `제안 내용을 생성하거나 확인하는 과정에서 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.` |
| 필요한 정보 없음 | `제안에 필요한 정보를 찾지 못했습니다. 화면을 새로고침한 뒤 다시 시도해 주세요.` |
| 입력 정보 오류·누락 | `제안에 필요한 정보가 올바르지 않거나 일부 항목이 누락되어 처리하지 못했습니다. 입력 내용을 확인해 주세요.` |
| 기능 준비 오류 | `제안 기능을 준비하는 과정에서 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.` |
| 정보 조회 오류 | `제안에 필요한 정보를 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.` |
| 연결 오류 | `제안 처리에 필요한 정보를 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.` |
| 그 밖의 오류 | `제안 처리 중 예상하지 못한 문제가 발생했습니다. 잠시 후 다시 시도해 주세요.` |

모든 실패 문구는 첫 줄 `파라미터 제안에 실패했습니다.`와 위 표의 상세 문구만 사용한다. 관리자·담당자 확인을
요구하는 문구는 화면에 표시하지 않는다.

DB의 `proposal_parameters`는 `ABSTAINED`와 `FAILED` 모두 `[]`이고, `error_message`와 callback
`resultMessage`에는 사용자가 바로 이해할 수 있는 동일한 안내 문구를 저장한다. 사용자 문구에는 `API`, `LLM`,
내부 처리 단계·키·예외 이름 같은 개발 용어를 넣지 않는다. 플랫폼 개발자는 별도 `resultCode`로 원인을 추적하며,
내부 예외 클래스명이나 원문 stack trace는 화면에 노출하지 않는다.

### 4.4 Callback 전송 자체가 실패한 경우

proposal 생성 실패와 callback 전송 실패는 별도로 관리한다.

| callback 처리 결과 | DB `callback_status` |
|---|---|
| callback 전송 성공 | `SUCCEEDED` |
| `skip_callback=true` | `SKIPPED` |
| callback URL 생성, 인증 또는 HTTP 전송 실패 | `FAILED` |

callback 전송 실패 원인은 proposal의 `error_code`와 `error_message`에 저장하지 않는다. proposal 생성 결과인
`PROPOSED`, `ABSTAINED`, `FAILED`도 그대로 유지한다.

background 실패를 proposal row에 기록하는 작업 자체가 실패하면 실패 callback 생성과 전송까지 진행되지 않는다. 이 경우 proposal row가 `PROCESSING`으로 남을 수 있으므로 서버 로그와 DB 상태를 함께 확인해야 한다.

### 4.5 HTTP 상태별 우선 확인 항목

| HTTP | 주로 뜻하는 것 | 먼저 확인할 내용 |
|---:|---|---|
| `400` | 요청 내용이나 도메인 계약이 올바르지 않음 | 파라미터명, 위치 필드, 빈 목록, 현재 상태 |
| `404` | scenario 또는 proposal을 찾지 못함 | URL의 ID와 삭제 여부 |
| `422` | JSON 형식이나 타입이 맞지 않음 | 필수 `data`, 숫자 ID, 배열·객체 구조 |
| `500` | 제안 생성 과정에서 내부 처리 실패 | 서버 로그와 저장된 오류 정보 |
| `503` | 동기 요청의 graph 실행 중 Basecase/LUT runtime이 준비되지 않음 | 전용 Agent 시작 및 리소스 준비 상태. 이미 접수된 비동기 요청은 HTTP를 다시 반환하지 않고 `FAILED` row와 callback을 남김 |

즉시 오류 응답은 `message`, `data.error_code`, `data.error_name`을 함께 기록한다. background 결과는 callback의
`data.resultCode`, `data.resultMessage`와 proposal DB row의 `status`, `error_code`, `error_message`를 함께 기록한다.

제안 과정은 [Flow 문서](04_MODEL_PARAMETER_AGENT_FLOW.md)를 참고한다.
