# Scenario Group Agent API Spec

## 기준

- canonical 업무 경로는 `/scenario-groups`다.
- 신규 Scenario Group 생성 엔진은 v4다.
- `/v2|v3|v4/.../sync`는 개발·비교용이며 운영 Client 진입점이 아니다.
- `/v4/scenario-groups`는 callback 호환용 deprecated API다.
- JSON 필드는 Pydantic alias 기준 camelCase로 표시한다.
- gateway prefix는 배포 환경이 소유하며 이 문서는 app 내부 path를 기준으로 한다.

## API 목록

### 운영 API

| Method | Path | 역할 |
| --- | --- | --- |
| `POST` | `/scenario-groups` | v4 Scenario Group 생성 및 진행 SSE |
| `GET` | `/scenario-groups` | Scenario Group 목록 |
| `GET` | `/scenario-groups/{id}` | 업무 상세 또는 table view |
| `GET` | `/scenario-groups/{id}/presentation` | 화면 전용 read model |
| `GET` | `/scenario-groups/{id}/additional-dimensions` | v4 Additional Dimension 후보 |
| `GET` | `/scenario-groups/{id}/operations/{operationId}` | operation polling |
| `GET` | `/scenario-groups/{id}/operations/{operationId}/stream` | SSE replay·재연결 |
| `POST` | `/scenario-groups/{id}/validation` | Scenario table 검증 접수 |
| `POST` | `/scenario-groups/{id}/signposts` | Signpost 생성 접수 |
| `POST` | `/scenario-groups/{id}/confirmation` | 최종 확정 |
| `POST` | `/scenario-groups/{id}/dimension-mapping-approvals` | legacy 자유값 mapping 승인·거절 |
| `DELETE` | `/scenario-groups/{id}` | 소유자 soft delete |
| `GET` | `/events` | Event 목록 |
| `GET` | `/events/{miEventId}` | Event 상세와 Scenario Template |

### 개발·테스트·호환 API

| 분류 | Method / Path | 비고 |
| --- | --- | --- |
| sync | `POST /v2/scenario-groups/sync` | Event별 원본 Template Dimension 비교 |
| sync | `POST /v3/scenario-groups/sync` | 합성 Dimension 비교 |
| sync | `POST /v4/scenario-groups/sync` | v4 create 완료 응답과 usage |
| sync | `POST /scenario-groups/{id}/validation/sync` | callback body를 동기 반환 |
| sync | `POST /scenario-groups/{id}/signposts/sync` | callback body를 동기 반환 |
| QA | `GET /scenario-groups/{id}/presentation/follow-up-request-bodies` | Validation·Signpost 초기 body 생성 |
| local | `DELETE /scenario-groups/{id}/signposts` | 관리자 토큰 필요 |
| local | `DELETE /scenario-groups/{id}/hard` | 관리자 토큰과 `confirm` 필요 |
| deprecated | `POST /v4/scenario-groups` | background callback 호환 경로 |

## 1. Scenario Group 생성

### Request

```http
POST /scenario-groups
Content-Type: application/json
```

```json
{
  "miEventIds": [1463, 1464, 1433],
  "userId": 10603
}
```

- Event ID는 중복 없는 양의 정수 1~5개다.
- 요청 배열 순서는 Event 표시 순서로 보존된다.
- 중복 판정은 요청 순서와 무관한 Event ID 집합과 engine version을 사용한다.
- 성공 응답은 HTTP 200, `Content-Type: text/event-stream`, `Cache-Control: no-cache`,
  `X-Accel-Buffering: no`다.
- POST body가 필요하므로 브라우저에서는 기본 `EventSource`가 아니라 `fetch` streaming을 사용한다.

요청 검증, Event 조회, 중복·소유권 확인이 실패하면 SSE가 아닌 JSON 오류를 반환한다. Client는 body를
읽기 전에 status와 `Content-Type`을 확인한다.

### SSE 계약

```text
id: {sequence}
event: {eventType}
data: {JSON}
```

모든 업무 event는 `operationId`, `scenarioGroupId`, `sequence`, `eventType`, `phase`, `title`,
`messageMarkdown`, `snapshotRevision`, `mlflowTraceId`, `createdAt`을 공통으로 가진다. SSE `id`, JSON
`sequence`, `event`, `eventType`은 서로 일치해야 한다.

| eventType | 의미 | Client 처리 |
| --- | --- | --- |
| `accepted` | 생성 접수와 식별자 확정 | group·operation ID와 sequence 저장 |
| `phase_started` | 새 phase 시작 | 진행 문구 갱신 |
| `retrying` | 현재 단계 자동 재시도 | 실패로 확정하지 않음 |
| `validated` | 단계 검증 성공 | 진행 상태 갱신 |
| `section_ready` | Presentation snapshot 갱신 | revision 증가 시 Presentation 재조회 |
| `completed` | 생성·저장 성공 | 최종 Presentation 재조회 |
| `failed` | 생성 실패 | `lastError` 확인 |
| `interrupted` | producer 중단 | 자동 재개하지 않음 |

terminal event는 `completed`, `failed`, `interrupted`뿐이다. 성공은 `completed.status=succeeded`다.
keep-alive는 `: keep-alive` comment이며 업무 event나 sequence로 계산하지 않는다.

현재 create phase는 `event_analysis`, `dimension_design`, `scenario_synthesis`, `persistence`다.
같은 phase에서 Event 영향과 Interaction처럼 검증 경계가 여러 번 생길 수 있으므로 event 개수에 의존하지 않는다.

### 연결 복구

`accepted` 이후 연결이 끊겨도 producer는 계속 실행된다. 마지막으로 연속 처리한 sequence를 보내 재연결한다.

```http
GET /scenario-groups/{scenarioGroupId}/operations/{operationId}/stream
Accept: text/event-stream
Last-Event-ID: 7
```

서버는 8번부터 DB 이력을 replay하고 실행 중이면 live-tail을 계속한다. `Last-Event-ID`가 없으면 0이며,
음수·비정수는 400이다. sequence gap이 보이면 마지막 연속 sequence로 다시 연결한다.

현재 상태만 확인하려면 다음 polling API를 사용한다.

```http
GET /scenario-groups/{scenarioGroupId}/operations/{operationId}
```

operation status는 `queued | running | succeeded | failed | interrupted`다. `queued|running`이면 stream을
재연결하고, `succeeded`이면 Presentation을 조회하며, 실패·중단이면 `lastError`를 표시한다.

### 중복 요청

| 기존 상태 | 같은 사용자 | 다른 사용자 |
| --- | --- | --- |
| 동일 조합 operation이 실행 중 | 409 `SCENARIO_GROUP_OPERATION_CONFLICT` | 403 `SCENARIO_GROUP_OWNERSHIP_CONFLICT` |
| 생성 성공, Confirmation 전 | 400 `SCENARIO_GROUP_ALREADY_CREATED` | 403 ownership conflict |
| `stage=completed` | 새 그룹 생성 허용 | 새 그룹 생성 허용 |
| latest operation 실패·중단 | 새 그룹 생성 허용 | 새 그룹 생성 허용 |
| soft delete됨 | 새 그룹 생성 허용 | 새 그룹 생성 허용 |

오류 `data`에는 `error_code`, `error_name`, 가능한 `scenarioGroupId`, `operationId`가 포함된다. Client는
`message` 문자열이 아니라 HTTP status와 `error_name`으로 분기한다. create POST는 멱등하지 않으므로 timeout
뒤 자동 재시도하지 말고 operation·목록·DB 증적을 먼저 확인한다.

## 2. 조회와 Presentation

### Scenario Group 목록·상세

`GET /scenario-groups`의 query는 `includeDeleted`, `miEventId`, `keyword`, `status`, `stage`, `sort`다.
응답은 group 목록과 latest/active operation 요약을 제공한다. 다중 Event 그룹의 단일 Event 호환 필드는
`null`이다.

`GET /scenario-groups/{id}`는 `includeDeleted`와 `view=full|table`을 받는다. `full`은 업무 상세,
`table`은 group 기본 메타데이터와 Scenario table만 반환한다.

### Presentation

```http
GET /scenario-groups/{scenarioGroupId}/presentation?operationId={operationId}
```

`operationId`를 생략하면 최신 operation을 선택한다. 응답은 engine version과 관계없이 다음 세 section을
가진다.

- `sections.eventAnalysis`
- `sections.scenarioDesign`
- `sections.roleSelectionRationale`

각 section의 status는 `pending | partial | ready | unavailable`, evidence level은
`full | limited | none`다. 아직 준비되지 않은 배열과 문자열도 shape을 유지한다.

`hide_price_pressure=true`이면 `roleSelectionRationale`은 `null`이고 Role Markdown을 생성하지 않는다.
같은 설정이 활성화되면 `scenarioDesign.scenarioTable.rows[]`의 `scenarioRole`, `pressureTarget`,
`pressureBand`, `pressureRationale`도 `null`로 마스킹한다. Dimension definition value와 cell evidence의
`pressureContribution`은 계산 증적이므로 유지한다. 설정이 비활성화된 Role Markdown은 `분기 기준 설명`,
`분기별 선택 값 설명`, `분기 상세 설명`, `이벤트 간 상호작용 효과` 표현을 사용하고 Dimension 식별자 대신
header `displayOrder`를 표시한다.

`scenarioDesign`은 Dimension definition과 Scenario table을 제공한다. v4 cell은
`{dimensionId: valueId}`이고 표시 label은 definition에서 해석한다. `sourceEventIds`는 Event 근거,
Dimension `rationale`은 선정 근거, value `rationale`은 미래 상태와 JKM 영향 가정이다.

모든 200 응답은 `ETag`를 반환한다. ETag에는 renderer version, operation ID, snapshot revision,
Scenario Group 수정 시각, 현재 Lever label mapping과 `hide_price_pressure` 값이 반영된다. 같은 URL에
`If-None-Match`를 보내고 내용이 같으면 body 없는 304를 반환한다. `section_ready`의 revision이 증가할 때
조회하되 `completed` 뒤에는 최종 조회를 한 번 더 한다.

`GET /scenario-groups/{id}/presentation/follow-up-request-bodies`가 만드는 Validation·Signpost 초기 body의
row는 `scenarioId`, `displayOrder`, `title`, `cells`만 포함한다. `scenarioRole`, `pressureTarget`,
`pressureBand`, `pressureRationale`은 값이 `null`이어도 두 request 계약에서 허용하지 않으며 전송하면
HTTP 422로 거부한다.

### Additional Dimension

`GET /scenario-groups/{id}/additional-dimensions`는 v4 group에서만 사용한다. GET은 저장된 후보만 읽고 LLM을
호출하거나 정식 Dimension을 변경하지 않는다.

`generationStatus`는 `not_requested | queued | running | ready | failed | interrupted | discarded`다.
`queued|running`은 `pending`, 실패·중단·미요청은 `unavailable`, 완료는 `ready`다. `ready`이면서 후보가
0개인 것도 정상이다. v1~v3 group은 400, 없는 group은 404다.

## 3. Validation

```http
POST /scenario-groups/{scenarioGroupId}/validation
```

```json
{
  "userId": 10603,
  "table": {
    "headers": [
      {"key": "d1", "label": "공급 복구 시점", "displayOrder": 1}
    ],
    "rows": [
      {
        "scenarioId": 90001,
        "displayOrder": 1,
        "title": "단기 복구",
        "cells": {"d1": "d1_v1"}
      }
    ]
  }
}
```

요청 row는 `scenarioId`, `displayOrder`, `title`, `cells`만 허용한다. v4 header는 현재 Dimension ID를
Create 순서대로 보내고 cell은 해당 Dimension의 `valueId` 또는 정확한 단일 label이어야 한다. 최종
Scenario 수는 2~7개다.

즉시 응답은 접수 상태다.

```json
{
  "status": "success",
  "message": "성공",
  "data": {
    "scenarioGroupId": 12345,
    "status": "creating",
    "stage": "scenario_created"
  }
}
```

최종 callback은 `result`, `reason`, `verdict`, `isValid`, `canProceed`, `reviewSkipped`, `summary`,
`checks`, `generatedDetails`, `scenarioGroup`, `table`을 제공한다.

| verdict | isValid / canProceed | stage | 의미 |
| --- | --- | --- | --- |
| `PASS` | `true / true` | `scenario_validated` | 차단·경고 없음 |
| `PASS_WITH_WARNINGS` | `true / true` | `scenario_validated` | 경고를 확인하고 진행 가능 |
| `BLOCK` | `false / false` | `scenario_created` | 수정 후 재검증 필요 |

Create 결과와 수정 가능한 필드가 같으면 `reviewSkipped=true`로 LLM review를 건너뛴다. `ad_` Additional
Dimension cell은 `null`일 때 허용 방향 안에서 자동 배정할 수 있지만 최초 `d1`, `d2` 계열 Dimension의
`null`은 차단한다. callback table은 canonical `valueId`를 반환한다.

Validation이 blocking 결론을 정상 반환한 경우에도 operation은 `succeeded`일 수 있다. 다음 단계 활성화는
operation status가 아니라 `canProceed`로 결정한다.

## 4. Signpost 생성

```http
POST /scenario-groups/{scenarioGroupId}/signposts
```

v4 request는 다음 값만 필요하다.

```json
{"userId": 10603}
```

schema상 `table`은 optional이다. v4는 request table을 사용하지 않고 최신 Validation operation의
fingerprint와 `canProceed=true`를 확인해 Change Set을 먼저 적용한다. stale이면 409
`SCENARIO_VALIDATION_STALE`을 반환하고 stage를 `scenario_created`로 되돌린다.

즉시 응답 shape은 Validation 접수 응답과 같다. 최종 callback은 다음 핵심 필드를 가진다.

```json
{
  "result": "success",
  "reason": null,
  "scenarioGroup": {
    "scenarioGroupId": 12345,
    "status": "creating",
    "stage": "signpost_created"
  },
  "table": {
    "headers": [],
    "rows": [
      {
        "scenarioId": 90001,
        "title": "단기 복구",
        "cells": {},
        "signposts": [
          {
            "signpostId": 1,
            "label": "주요 설비 재가동 발표",
            "probabilityDirectionCode": "sup",
            "probabilityImpactScore": 1.0,
            "signpostReason": "복구 시나리오를 직접 지지하는 관측 신호",
            "strength": "STRONG"
          }
        ]
      }
    ]
  }
}
```

## 5. Confirmation과 삭제

`POST /scenario-groups/{id}/confirmation`은 `userId`, 수정 가능한 `scenarioGroup`, 최종 `table`을 받는다.
header 순서, 활성 Scenario ID 집합, `{dimensionId: valueId}` 조합이 DB와 같아야 한다. 불일치는 409
`SCENARIO_CONFIRMATION_STALE`이며 Confirmation이 Dimension 조합을 덮어쓰지 않는다.

성공하면 `status=created`, `stage=completed`가 되고 Scenario·Signpost snapshot을 저장한다.

`DELETE /scenario-groups/{id}`는 body의 `userId`로 소유권을 확인하고 soft delete한다. active
`queued|running` operation이 있으면 409다. Signpost soft delete와 hard delete는 로컬 개발 전용이며
관리자 bearer token이 필요하다.

## 6. Callback과 오류

Validation과 Signpost background flow는 다음 설정으로 callback URL을 만든다.

- `callback_base_url`
- `callback_validate_scenarios_path`
- `callback_create_signposts_path`
- `skip_callback`

성공·콘텐츠 차단 callback은 `result=success`, 실행 오류는 `result=failure`와 `reason`을 사용한다.
callback 전송 실패는 Agent 작업 결과와 별도 장애다. 로그에서 graph 실패와 callback delivery 실패를 구분한다.
비밀값과 OAuth2 token은 문서·로그·report에 기록하지 않는다.

공통 domain/API 오류는 보통 다음 shape이다.

```json
{
  "status": "error",
  "message": "오류 설명",
  "data": {
    "error_code": -1005,
    "error_name": "SCENARIO_GROUP_OPERATION_CONFLICT"
  }
}
```

FastAPI request validation은 HTTP 422와 `detail` 배열을 사용한다. sync graph의 처리 실패는 HTTP 200의
`result=failure` callback body가 될 수 있으므로 HTTP status만으로 성공을 판정하지 않는다.

## 구현 정본

- router: `apps/agents/scenario_group_agent/routers/`
- create schema: `flows/create_multi_event_scenarios/api_schema.py`
- validation schema: `flows/validate_scenarios/api_schema.py`
- 공통 callback schema: `schemas/endpoint.py`
- 관리·operation schema: `schemas/api/manage_scenario_groups.py`
- Presentation schema: `schemas/api/scenario_group_presentation.py`
