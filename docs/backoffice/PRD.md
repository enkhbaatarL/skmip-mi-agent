# Scenario Comparison Backoffice PRD

## 1. 문서 목적

Scenario Comparison Backoffice는 Scenario Group Agent의 sync API를 브라우저에서 실행하고 결과를 비교하는 내부 QA용 frontend다.

제품은 다음 두 테스트 흐름을 명확히 분리한다.

1. v1 단일 이벤트 시나리오 테스트
   - 이벤트 1건으로 기존 시나리오 생성 파이프라인을 순차 실행한다.
   - 생성, validation, signpost, confirmation 결과를 단계별로 확인한다.
2. v2/v3/v4 다중 이벤트 시나리오 비교
   - 동일한 이벤트 2~5건으로 v2, v3, v4 생성 API를 실행한다.
   - 버전별 dimension, Scenario, pressure band, lineage, 진단 정보와 비용/시간을 한 화면에서 비교한다.

기존 Backoffice backend가 담당하던 callback 수신, 상태 중계, OAuth mock, SSE 기능은 더 이상 필요하지 않다. frontend는 Agent의 테스트용 sync API를 직접 호출한다.

## 2. 목표

- 단일 이벤트 v1 파이프라인을 화면에서 단계별로 실행하고 검증한다.
- 동일한 입력 조건으로 v2/v3/v4의 다중 이벤트 시나리오 생성 결과를 비교한다.
- 요청 body, 원본 응답, 수행 시간, token usage, 성공/실패 판정을 보존한다.
- 버전별 생성 전략과 결과 차이를 domain reviewer가 이해할 수 있게 시각화한다.
- callback 설정이나 별도 Backoffice 서버 없이 정적 frontend만으로 실행한다.
- 테스트 결과를 JSON으로 내보내 재현과 후속 분석에 사용할 수 있게 한다.

## 3. 비목표

- Agent의 background/callback API를 테스트하지 않는다.
- callback receiver, callback OAuth2 token mock, SSE, WebSocket을 구현하지 않는다.
- Backoffice 전용 FastAPI proxy나 상태 저장 backend를 운영하지 않는다.
- v2/v3/v4 비교에서 validation, signpost, confirmation을 실행하지 않는다.
- v1 흐름과 v2/v3/v4 비교 흐름을 하나의 실행으로 섞지 않는다.
- 운영자용 Scenario Group 관리, 권한 관리, 사용자 관리 화면을 만들지 않는다.
- 브라우저에서 LLM API key를 보관하거나 LLM Judge를 직접 실행하지 않는다.
- 본 제품을 운영 사용자용 관리 콘솔로 사용하지 않는다.

## 4. 사용자

- QA tester
  - 실제 sync API의 성공/실패와 단계별 응답을 확인한다.
  - 같은 입력으로 버전별 결과를 재현하고 비교한다.
- Agent developer
  - 요청 body, 원본 응답, 오류, latency, token usage를 확인한다.
  - dimension lineage와 generation diagnostics로 실패 원인을 진단한다.
- PM/domain reviewer
  - 입력 Event와 생성 Scenario 사이의 논리적 연결을 검토한다.
  - 버전별 Scenario 구성, 가격 압력 방향, baseline 및 확률 차이를 비교한다.

## 5. 제품 구조

### 5.1 실행 구조

Backoffice는 React + Vite 기반 정적 frontend로 구성한다.

```text
Browser
  └─ Scenario Comparison Frontend
       ├─ GET Agent event APIs
       ├─ POST Agent sync APIs
       ├─ browser session state
       └─ JSON result export

Scenario Group Agent
  ├─ GET /events
  ├─ GET /events/{miEventId}
  ├─ v1 sync workflow APIs
  └─ /v2, /v3, /v4 scenario-groups/sync
```

- frontend는 사용자가 입력한 `Agent Base URL`로 직접 요청한다.
- Agent는 허용된 Backoffice origin에 대해 CORS를 지원해야 한다.
- HTTPS로 제공되는 frontend에서 HTTP Agent URL을 호출하는 mixed-content 구성은 지원하지 않는다.
- API 인증이 필요한 환경에서는 기존 Agent 인증 방식을 사용한다. frontend bundle에 secret을 포함하지 않는다.
- 실행 중 상태는 frontend memory에 둔다.
- 새로고침 복구가 필요하면 secret을 제외한 설정과 결과만 browser storage에 저장한다.

### 5.2 기존 backend 제거

구현 시 기존 `backoffice/backend/`와 다음 backend 전용 기능을 삭제한다.

- Agent proxy API
- callback receiver
- callback OAuth2 token endpoint
- in-memory run store
- SSE event stream
- backend 정규화 schema
- callback용 Docker/Compose 설정
- backend 전용 테스트와 문서

frontend의 기존 API client는 Backoffice proxy가 아니라 Agent Base URL을 직접 사용하도록 교체한다.

## 6. 정보 구조

상단에는 공통 runtime 설정과 두 개의 독립 workspace를 둔다.

```text
Runtime Settings
  - Agent Base URL
  - userId
  - timeout
  - connection check

Workspace A: v1 단일 이벤트
  - Event 선택
  - Create
  - Validation
  - Signpost
  - Confirmation
  - 단계별 요청/응답

Workspace B: v2/v3/v4 비교
  - Event 2~5건 선택
  - 비교 조건 고정
  - v2/v3 실행
  - v4 실행
  - 버전 비교
  - 결과 export
```

탭을 전환해도 각 workspace의 입력과 최근 결과는 서로 독립적으로 유지한다.

## 7. 공통 기능 요구사항

### 7.1 Runtime Settings

필수 입력:

- `Agent Base URL`
- `userId`
- 요청 timeout

기본 timeout은 장시간 sync 실행을 고려해 1,200초로 한다.

필수 동작:

- `GET /events` 또는 별도 health endpoint로 연결 가능 여부를 확인한다.
- 마지막으로 사용한 Base URL과 userId를 로컬에 저장할 수 있다.
- token, password 등 secret은 browser storage에 저장하지 않는다.
- 실행 중에는 해당 실행의 Base URL, userId, Event 입력을 변경하지 못하게 한다.

### 7.2 Event 선택

공통 Event selector는 다음 방법을 지원한다.

- Event ID 직접 입력
- 최신순/오래된순 조회
- keyword 검색
- Event 목록에서 선택

Event 목록은 `GET /events`를 사용하고 상세는 `GET /events/{miEventId}`를 사용한다.

표시 정보:

- `miEventId`
- 제목과 요약
- 발생 시각
- Event Type L1/L2
- JKM/TTF/HH 영향 정보
- Scenario 추천 여부와 사유
- 기존 Scenario Group 정보와 실행 가능 상태

### 7.3 공통 실행 증적

각 API 호출은 다음 정보를 보존한다.

- URL과 method
- request body
- 시작/종료 시각
- elapsed time
- HTTP status
- transport status
- parsed response
- raw response text
- 성공/실패/불명 판정
- 오류 메시지
- token usage가 있으면 prompt/completion/total token

Raw JSON panel에서 request와 response를 그대로 확인하고 복사할 수 있어야 한다.

## 8. v1 단일 이벤트 테스트

### 8.1 범위

v1 화면은 `scenario-sync-pipeline`의 기존 단일 이벤트 흐름을 따른다.

`POST /v1/scenario-groups/sync`를 v2/v3/v4 비교에 섞지 않는다. v1 전체 workflow는 기존 unversioned sync API로 실행한다.

```text
Event detail
  → Create scenarios
  → Validate scenarios
  → Create signposts
  → Get latest group detail
  → Confirm generation
```

### 8.2 입력

- `miEventId`: 양의 정수 1개
- `userId`
- 선택: 기존 Scenario Group soft delete 여부
- soft delete에 필요한 권한 값이 있다면 실행 시에만 입력

### 8.3 API 순서

1. `GET /events/{miEventId}`
2. `POST /scenario-groups/sync`

```json
{
  "miEventId": 12345,
  "userId": 10001
}
```

3. `POST /scenario-groups/{scenarioGroupId}/validation/sync`

```json
{
  "userId": 10001,
  "table": {}
}
```

4. `POST /scenario-groups/{scenarioGroupId}/signposts/sync`

```json
{
  "userId": 10001,
  "table": {}
}
```

5. `GET /scenario-groups/{scenarioGroupId}`
6. `POST /scenario-groups/{scenarioGroupId}/confirmation`

```json
{
  "userId": 10001,
  "scenarioGroup": {},
  "table": {}
}
```

`table`과 `scenarioGroup`은 직전 실제 응답 및 사용자의 화면 편집값으로 구성한다. 식별자와 API schema에 필요한 필드를 임의로 재생성하지 않는다.

### 8.4 단계 제어

- 기본값은 단계별 수동 진행이다.
- 이전 단계가 완료되어야 다음 단계 버튼이 활성화된다.
- 각 단계 실행 전 request preview를 보여준다.
- validation 결과가 invalid여도 warning으로 표시하고, 사용자가 확인 후 signpost 단계로 계속 진행할 수 있다.
- create 또는 signpost의 실패는 다음 단계 진행을 막는다.
- confirmation은 callback 없이 동기 응답으로 완료 여부를 판단한다.
- 단계 재실행은 새 DB row 또는 중복 데이터를 만들 수 있음을 경고하고 사용자의 명시적 확인을 받는다.

### 8.5 성공 판정

- Create
  - 응답 `result=success`
  - `scenarioGroup`과 `table` 존재
- Validation
  - `stage=scenario_validated`이면 통과
  - invalid 결과는 warning으로 기록하되 결과와 reason을 보존
- Signpost
  - 응답 `result=success`
- Confirmation
  - `status=success`
  - `data.stage=completed`

HTTP 200이어도 callback body 또는 common response의 실패 필드가 있으면 실패로 판정한다.

### 8.6 v1 화면

상단 요약:

- 선택 Event
- `scenarioGroupId`
- 현재 status/stage
- 전체 elapsed time
- 누적 token usage

단계별 panel:

- Create 결과
- editable Scenario table
- Validation 결과와 warning/reason
- Scenario별 Signpost
- Confirmation 결과
- 각 단계 request/response JSON

Scenario table에는 최소 다음을 표시한다.

- Scenario 순서
- baseline 여부
- title
- narrative
- dimension별 value
- probability
- Scenario role 또는 pressure 정보가 존재하면 해당 값

## 9. v2/v3/v4 다중 이벤트 비교

### 9.1 범위

v2/v3/v4 비교는 create sync API만 실행한다.

- validation 실행 안 함
- signpost 실행 안 함
- confirmation 실행 안 함
- callback API 사용 안 함

모든 버전은 동일한 Event 목록, userId, `comparisonRunId`를 사용한다.

### 9.2 입력

- 중복 없는 `miEventIds` 2~5개
- `userId`
- 고유 `comparisonRunId`

`comparisonRunId`는 기본적으로 frontend가 고유값을 생성하며 실행 시작 후 변경할 수 없다.

Event 선택 시 상세를 모두 조회하고 다음 조건을 manifest 형태로 고정한다.

- Event 순서와 ID
- Event 상세 snapshot
- Base URL
- userId
- comparisonRunId
- 생성 시각

### 9.3 API 요청

v2:

```http
POST /v2/scenario-groups/sync
```

v3:

```http
POST /v3/scenario-groups/sync
```

공통 body:

```json
{
  "miEventIds": [101, 202],
  "userId": 10001,
  "comparisonRunId": "multi-event-unique-id"
}
```

v4:

```http
POST /v4/scenario-groups/sync
```

```json
{
  "miEventIds": [101, 202],
  "userId": 10001,
  "comparisonRunId": "multi-event-unique-id"
}
```

### 9.4 실행 순서와 재시도 정책

1. 입력 manifest를 고정한다.
2. v2와 v3를 병렬 실행한다.
3. v2와 v3가 모두 성공, 실패 또는 불명 상태로 종료될 때까지 기다린다.
4. v4를 실행한다.
5. 완료된 응답을 비교 화면에 반영한다.

v4를 v2/v3와 동시에 실행하지 않는다. v4 저장 결과가 먼저 생성되면 같은 `comparisonRunId`의 lineage 검증과 충돌할 수 있다.

동일 version의 POST는 자동 재시도하지 않는다.

- API와 DB에 중복 Scenario Group이 생길 수 있기 때문이다.
- timeout은 실패가 아니라 `결과 불명`으로 표시한다.
- timeout 후 재호출 버튼은 비활성화하고 새 comparison 실행 생성을 안내한다.
- 한 버전이 실패해도 나머지 결과는 보존하고 가능한 비교를 계속한다.

### 9.5 버전 의미

| Version | 입력 | 생성 전략 | 기대 dimension |
| --- | --- | --- | --- |
| v2 | Event 2~5건 | Event별 원본 Template dimension을 namespace하여 사용 | 5~8개 |
| v3 | Event 2~5건 | Event 충격과 상호작용을 합성 dimension으로 구성 | 4~7개 |
| v4 | Event 2~5건 | Event 사실과 모델 영향 레버 기반 dimension 구성 | 3~6개 |

모든 version의 `globalPressureBand`는 global LNG pressure다. v4의
`relatedMarkets`는 Scenario별 관련 시장과 근거를 담는 보조정보이며 시장별
pressure나 Scenario role로 사용하지 않는다.

### 9.6 성공 판정

각 version은 다음을 모두 만족하면 API 성공이다.

- transport 성공
- HTTP 2xx
- response `status=success`
- response `data` 존재
- `apiVersion`이 요청 version과 일치
- `comparisonRunId`가 manifest와 일치
- 입력 Event lineage가 manifest와 일치

성공 version이 2개 미만이면 비교 결론은 `판정 불가`로 표시한다.

### 9.7 비교 화면

#### 입력 Event 영역

- 선택한 Event 2~5건을 카드 또는 table로 표시
- Event 제목, 요약, Event Type, 시장 영향 표시
- comparisonRunId 표시 및 복사

#### 실행 상태 영역

버전별로 다음 상태를 표시한다.

- ready
- running
- success
- error
- unknown

각 버전 card에는 elapsed time, token usage, group ID, 오류 메시지를 표시한다.

#### 결과 요약 table

버전별 최소 비교 항목:

- generation strategy
- Scenario Group ID와 이름
- dimension 수
- Scenario 수
- baseline Scenario
- floor/ceiling/mixed 수
- target/global pressure band 분포
- 총 probability
- Event lineage coverage
- generation diagnostics의 coverage status
- excluded candidate/dimension 수
- unsupported lever 수
- elapsed time
- token usage

#### Dimension 비교

- version별 dimension key, label, value 목록
- source Event와 source dimension lineage
- v2 namespace
- v3 composite source 관계
- v4 lever reference, supported/unsupported 상태
- covered/uncovered dimension

#### Scenario 비교

pressure band 또는 Scenario role을 기준으로 version별 Scenario를 나란히 배치한다.

표시 항목:

- baseline
- title
- narrative
- dimension cells
- role
- pressure band
- pressure rationale
- probability
- source Event coverage

특정 version에 대응 Scenario가 없으면 빈 상태와 제외 사유를 표시한다.

#### Generation Diagnostics

- target pressure bands
- excluded candidates와 reason
- excluded dimensions
- coverage status
- Event impact facts
- Event interactions
- v4 impact catalog version
- v4 unsupported lever details

### 9.8 결정적 품질 검사

frontend는 실제 Event와 API 응답만 사용해 다음 결정적 검사를 제공한다.

- Event 사실과 Scenario/dimension의 명백한 식별자·lineage 불일치
- Scenario 3~5개
- baseline 정확히 1개
- floor와 ceiling 각각 1개
- mixed 최소 1개
- Scenario 조합과 pressure band 중복 없음
- probability 합계
- 버전별 dimension 수 범위
- 전체 입력 Event lineage coverage

검사 결과는 PASS/WARN/FAIL과 근거 필드로 표시한다.

이 검사는 `scenario-sync-pipeline`의 LLM Judge를 대체하지 않는다. 의미적 타당성 평가와 우수 version 선정이 필요하면 별도의 수동 pipeline 실행 결과를 사용한다. frontend MVP는 LLM 점수나 우수 version을 임의로 생성하지 않는다.

## 10. 결과 저장과 내보내기

### 10.1 v1 export

다음을 하나의 JSON으로 내보낸다.

- runtime 조건
- Event detail
- 단계별 request/response
- 단계별 판정과 elapsed time
- 최종 Scenario Group detail
- 전체 token usage
- 오류와 warning

### 10.2 v2/v3/v4 export

다음을 하나의 comparison bundle JSON으로 내보낸다.

- manifest
- selected Events
- v2/v3/v4 request/response
- version별 transport/API 상태
- elapsed time과 token usage
- 결정적 검사 결과

내보낸 파일에는 인증 token이나 secret을 포함하지 않는다.

## 11. 상태 및 오류 처리

### 11.1 공통 상태

- `idle`
- `ready`
- `running`
- `success`
- `warning`
- `error`
- `unknown`

### 11.2 오류 원칙

- HTTP 오류와 API body 오류를 구분한다.
- HTTP 200의 `result=failure` 또는 `status=error`를 성공으로 표시하지 않는다.
- 파싱할 수 없는 응답은 raw text를 보존한다.
- 진행 중인 요청을 취소하면 서버 실행은 계속될 수 있음을 안내하고 상태를 `unknown`으로 둔다.
- 이전의 성공 결과는 후속 단계 오류가 발생해도 유지한다.
- 오류 화면에는 version/step, URL, HTTP status, message, raw response를 표시한다.

### 11.3 중복 생성 보호

- 실행 버튼은 요청 중 중복 클릭할 수 없다.
- 완료 또는 timeout된 create POST를 같은 실행에서 자동 재호출하지 않는다.
- 기존 Scenario Group으로 v1 create가 거부되면 기존 group ID와 soft delete 선택지를 표시한다.
- soft delete는 사용자의 명시적 확인과 필요한 권한 입력 후에만 실행한다.
- hard delete는 제공하지 않는다.

## 12. Frontend 기술 요구사항

- React + Vite + TypeScript
- Backoffice proxy 없는 Agent API client
- 요청별 `AbortController`
- 1,200초 이상 설정 가능한 timeout
- 긴 JSON을 다룰 수 있는 접기/검색/복사 기능
- 넓은 Scenario table의 가로 스크롤
- 2~5개 Event 및 3개 version 비교에 대응하는 반응형 layout
- 비교 중 다른 workspace로 이동해도 실행 상태 유지
- 단위 테스트 가능한 request builder와 response 판정 함수

권장 frontend module:

```text
backoffice/frontend/src/
  api/
    agentClient.ts
    v1Pipeline.ts
    multiEventComparison.ts
  features/
    runtime/
    event-selector/
    v1-pipeline/
    version-comparison/
    json-inspector/
  domain/
    apiTypes.ts
    judgments.ts
    deterministicChecks.ts
    exportBundle.ts
```

## 13. 운영 및 배포

- frontend는 정적 asset으로 build한다.
- 로컬 개발은 Vite dev server를 사용한다.
- 배포는 사내 정적 hosting 또는 기존 정적 web server를 사용한다.
- 별도 Python runtime과 Backoffice container는 필요하지 않다.
- 배포 환경별 Agent Base URL은 runtime 입력 또는 공개 설정 파일로 제공한다.
- secret을 frontend 환경 변수나 build artifact에 포함하지 않는다.

## 14. 인수 조건

### 14.1 backend 제거

- repository에 실행 가능한 Backoffice FastAPI backend가 남아 있지 않다.
- callback receiver, OAuth token mock, SSE endpoint가 없다.
- frontend가 `/backoffice/api/...`를 호출하지 않는다.
- callback 관련 Compose 설정 없이 frontend를 실행할 수 있다.

### 14.2 v1

- Event 1건을 선택해 create → validation → signpost → confirmation을 순차 실행할 수 있다.
- 모든 작업은 sync endpoint를 사용하며 callback을 기다리지 않는다.
- 각 단계의 request/response, elapsed time, 판정을 볼 수 있다.
- validation invalid 결과가 warning과 reason으로 표시된다.
- confirmation 성공은 `status=success`, `data.stage=completed`로 판정된다.
- 같은 create POST가 자동 재시도되지 않는다.

### 14.3 v2/v3/v4

- 중복 없는 Event 2~5건을 선택할 수 있다.
- 동일 Event, userId, comparisonRunId를 세 version에 사용한다.
- v2와 v3 종료 후에만 v4를 실행한다.
- 각 version POST는 정확히 한 번만 호출된다.
- timeout은 unknown으로 표시되고 자동 재시도되지 않는다.
- 한 version이 실패해도 다른 결과를 확인하고 export할 수 있다.
- dimension, Scenario, pressure, lineage, diagnostics, latency, token usage를 비교할 수 있다.
- 성공 version이 2개 미만이면 비교 결론이 `판정 불가`로 표시된다.

### 14.4 보안과 실행 환경

- 브라우저 bundle과 export 파일에 secret이 없다.
- 허용된 CORS 환경에서 Browser → Agent 직접 호출이 동작한다.
- HTTPS/HTTP mixed-content 오류를 사전에 안내한다.
- 새로고침 복구 데이터에 인증 정보가 저장되지 않는다.

## 15. 위험과 대응

- Agent가 CORS를 허용하지 않음
  - 허용 origin 설정을 Agent 배포 구성에 추가한다.
- 장시간 sync 요청이 브라우저나 중간 proxy에서 timeout
  - 기본 timeout을 1,200초로 두고, timeout 결과는 unknown으로 보존한다.
- timeout 후 서버에서는 생성이 완료됨
  - 자동 재시도하지 않고 새 comparison 실행 또는 DB 증적 확인을 안내한다.
- v4가 v2/v3보다 먼저 저장되어 lineage 충돌
  - v2/v3 완료 barrier 뒤 v4를 실행한다.
- 브라우저 저장소의 결과가 커짐
  - 최근 실행 수와 저장 용량을 제한하고 JSON export 후 삭제 기능을 제공한다.
- 결정적 검사만으로 의미적 품질을 판단하기 어려움
  - 의미 평가가 필요한 경우 `tests/manual/test_multi_event_scenario_versions.py` 보고서를 별도로 생성한다.

## 16. 향후 확장

- 수동 pipeline의 `comparison_report.md`와 `comparison_judge.json` import
- 과거 comparison bundle 불러오기 및 재비교
- 여러 comparison 결과의 latency/token 추세
- screenshot 또는 PDF 비교 보고서 export
- Agent가 제공하는 경우 server-side comparison report API 연동
