# Scenario Comparison Backoffice Test Scenarios

## 1. 목적

이 문서는 [`PRD.md`](./PRD.md)와 [`DESIGN.md`](./DESIGN.md)에 정의된 정적 frontend와 Scenario Group Agent 기반 Scenario Comparison Backoffice의 QA 시나리오를 정의한다.

검증 대상:

- Browser에서 Scenario Group Agent API 직접 호출
- v1 단일 이벤트 create → validation → signpost → confirmation
- v2/v3/v4 다중 이벤트 create 결과 비교
- v2/v3 종료 barrier 이후 v4 실행
- request/response, elapsed time, token usage, raw JSON 증적
- 결정적 품질 검사
- 사용자 요청 기반 의미 품질 평가와 우수 version 선정
- 사용자용 label·생성 근거 view와 Raw 증적 분리
- timeout, 취소, 부분 실패 및 중복 요청 방지
- JSON export와 secret 제거
- CORS, mixed content, 반응형 및 접근성

검증 제외:

- callback API
- callback OAuth2 token
- SSE/WebSocket
- Backoffice FastAPI proxy
- v2/v3/v4 validation, signpost, confirmation
- 브라우저에서 외부 LLM API 또는 LLM API key 직접 사용
- 운영용 Scenario Group 관리 기능

## 2. 테스트 흐름 분리

테스트 요청은 반드시 다음 중 하나로 분류한다.

| 흐름 | Event | API 범위 | 비교 |
| --- | --- | --- | --- |
| v1 단일 이벤트 | 1건 | unversioned create, validation, signpost, detail, confirmation | 없음 |
| v2/v3/v4 비교 | 중복 없는 2~5건 | versioned create sync, 사용자 요청 시 Agent 품질 평가 | 성공 version 비교 |

한 테스트 run에서 두 흐름을 섞지 않는다.

## 3. 공통 사전조건

- 정적 frontend가 실행 중이어야 한다.
  - 예: Vite `http://127.0.0.1:5173`
- Scenario Group Agent가 실행 중이어야 한다.
  - local 권장: `http://127.0.0.1:8001`
- Agent가 frontend origin을 CORS allowlist에 포함해야 한다.
- frontend와 Agent의 HTTP/HTTPS scheme이 browser mixed-content 정책에 맞아야 한다.
- 유효한 `userId`가 준비되어 있어야 한다.
- sync 실행 timeout은 기본 1,200초로 설정한다.
- v1용 Event 1건과 비교용 Event 2~5건이 준비되어 있어야 한다.
- 기존 Scenario Group 정리에 필요한 admin token 또는 delete authorization은 필요할 때만 준비한다.
- 브라우저 network log와 Evidence Drawer를 함께 확인할 수 있어야 한다.

### 3.1 Agent 실행 조건

v2와 v3의 병렬 호출을 처리할 수 있도록 local Agent는 Gunicorn/UvicornWorker 3개 구성을 권장한다.

```bash
poetry run dotenv -f envs/.env run --no-override -- \
  gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 3 \
  --bind 127.0.0.1:8001 \
  --timeout 1200 \
  --graceful-timeout 1200
```

v1 순차 테스트만 수행할 때는 기존 Uvicorn local 실행도 허용한다.

### 3.2 테스트 데이터 원칙

- 비교 테스트마다 고유 `comparisonRunId`를 사용한다.
- 동일 comparison run에서 Event 순서와 userId를 변경하지 않는다.
- create POST의 중복 실행 여부를 확인할 수 있도록 browser network log를 보존한다.
- 테스트 중 생성된 모든 `scenarioGroupId`를 기록한다.
- 기존 group이 있는 Event를 v1에 사용하려면 테스트 시작 전에 명시적으로 soft delete한다.
- hard delete는 사용하지 않는다.

### 3.3 종료 및 정리

frontend 제품 범위에 별도 Scenario Group 관리 화면은 없다. 테스트 종료 후 데이터 정리는 승인된 manual script 또는 Agent soft-delete API로 수행한다.

정리 절차:

1. 생성된 `scenarioGroupId`, API version, comparisonRunId를 기록한다.
2. 필요한 결과 JSON을 export한다.
3. 유효한 권한으로 Agent soft-delete API 또는 기존 정리 도구를 실행한다.
4. `GET /scenario-groups/{scenarioGroupId}` 또는 목록 조회로 삭제 상태를 확인한다.
5. 정리 실패 시 group ID와 원인을 테스트 보고서에 남긴다.

timeout/unknown인 create는 서버에서 완료되었을 수 있으므로 DB/API 증적 확인 후 정리한다. 동일 POST를 정리 목적으로 재호출하지 않는다.

## 4. 공통 통과 기준

### 4.1 API 정확성

- frontend가 `/backoffice/api/...`가 아니라 Agent Base URL을 직접 호출한다.
- v1 request body는 현재 Event, userId, 최신 editable table을 사용한다.
- comparison의 세 version은 동일 Event 순서, userId, comparisonRunId를 사용한다.
- 세 version request는 동일한 Event, userId, comparisonRunId를 사용한다.
- HTTP 200의 `result=failure` 또는 `status=error`를 성공으로 표시하지 않는다.
- create POST는 사용자 action 한 번당 정확히 한 번 전송된다.

### 4.2 상태 정확성

- transport, HTTP, API body 판정이 구분된다.
- timeout 또는 응답 수신 전 취소는 `unknown`으로 표시된다.
- 오류가 발생해도 이전 성공 결과와 입력값이 유지된다.
- 실행 중 workspace tab을 변경해도 요청과 화면 상태가 유지된다.
- v2/v3가 terminal 상태가 되기 전 v4가 시작되지 않는다.

### 4.3 증적 정확성

모든 API call에 다음이 표시되어야 한다.

- method와 URL
- request body
- 시작/종료 시각
- elapsed time
- HTTP status
- transport/API 판정
- parsed response
- raw response 또는 raw text
- 오류
- token usage가 존재하면 prompt/completion/total token

### 4.4 UX

- 요청 중 중복 클릭이 방지된다.
- loading 중 기존 결과를 blank 처리하지 않는다.
- warning/error/unknown은 원인과 다음 행동을 안내한다.
- 긴 Scenario table과 JSON을 스크롤, 검색, 복사할 수 있다.
- 상태는 색상뿐 아니라 icon과 text로 구분된다.

### 4.5 보안

- 인증값은 마스킹된다.
- browser storage에 token/secret이 없다.
- export JSON에 Authorization, cookie, token이 없다.
- frontend build artifact에 secret이 없다.

## 5. v1 정상 동작

### TC-V1-N-001 연결 확인과 단일 Event 선택

목적: frontend가 Agent에 직접 연결하고 Event 한 건을 선택하는지 확인한다.

절차:

1. `v1 단일 이벤트` tab을 연다.
2. Runtime Settings에 Agent Base URL, userId, timeout을 입력한다.
3. `연결 확인`을 클릭한다.
4. Event 목록을 최신순으로 조회한다.
5. Event 한 건을 선택한다.
6. Event detail이 표시되는지 확인한다.

기대결과:

- browser가 Agent의 `GET /events`를 직접 호출한다.
- 연결 상태가 `연결됨`으로 표시된다.
- 선택 Event의 `miEventId`, 제목, Event Type, 시장 영향이 표시된다.
- `GET /events/{miEventId}` request/response가 Evidence Drawer에 남는다.
- Event 한 건만 선택된다.

### TC-V1-N-002 Create 성공

목적: 단일 Event create sync 응답을 Scenario table로 표시하는지 확인한다.

절차:

1. TC-V1-N-001을 완료한다.
2. `Create 실행` 전 request preview를 연다.
3. `miEventId`와 userId를 확인한다.
4. `Create 실행`을 한 번 클릭한다.
5. 실행 중 버튼과 Event/runtime 입력 상태를 확인한다.
6. 응답 완료 후 Run Header와 Scenario table을 확인한다.

기대결과:

- 정확히 한 번 `POST /scenario-groups/sync`가 호출된다.
- request body는 선택 Event와 userId를 사용한다.
- 실행 중 Create 중복 클릭과 runtime 변경이 차단된다.
- `result=success`일 때 success로 판정된다.
- `scenarioGroupId`, status/stage, Scenario 수가 표시된다.
- API table header 순서대로 dimension column이 표시된다.
- baseline, title, narrative, probability가 표시된다.
- elapsed time과 token usage가 있으면 표시된다.

확인 증적:

- browser network POST 1건
- Create request/response
- Scenario table 화면

### TC-V1-N-003 Scenario 편집 후 Validation 성공

목적: 화면 편집값이 validation sync request에 반영되는지 확인한다.

절차:

1. Create 성공 후 Scenario 한 건의 title과 dimension cell을 수정한다.
2. probability를 수정한다.
3. 신규 row 한 건을 추가하고 필수값을 채운다.
4. 기존 non-baseline row 한 건을 삭제한다.
5. validation request preview를 확인한다.
6. `Validation 실행`을 클릭한다.

기대결과:

- 삭제 row는 request에 없다.
- 신규 row와 수정 값이 `table.rows`에 포함된다.
- row/display order가 중복되지 않는다.
- 기존 API 식별자는 유지된다.
- `stage=scenario_validated`이면 success로 판정된다.
- validation 응답의 최신 table이 안전하게 반영된다.
- 사용자가 편집한 값이 요청 중 유실되지 않는다.

### TC-V1-N-004 Validation invalid 경고 후 계속

목적: invalid validation을 pipeline 실패로 숨기지 않고 warning으로 처리하는지 확인한다.

절차:

1. 상호 모순되거나 invalid한 Scenario 조합을 만든다.
2. Validation을 실행한다.
3. 결과와 다음 단계 버튼을 확인한다.
4. warning 확인 control을 선택한다.
5. Signpost 단계로 이동한다.

기대결과:

- invalid 결과, stage, `isValid`, reason이 표시된다.
- 상태가 warning으로 표시된다.
- 현재 Scenario 입력값이 유지된다.
- 사용자가 warning을 확인하기 전에는 계속 진행 action이 비활성화된다.
- 확인 후 Signpost 단계 진행이 가능하다.
- 결과를 success로 잘못 표시하지 않는다.

### TC-V1-N-005 Signpost 성공

목적: 최신 Scenario table로 signpost sync API를 실행하고 결과를 표시하는지 확인한다.

절차:

1. Validation 단계를 완료하거나 warning 진행을 확인한다.
2. Signpost request preview를 확인한다.
3. `Signpost 실행`을 클릭한다.
4. Scenario별 Signpost를 확인한다.

기대결과:

- `POST /scenario-groups/{scenarioGroupId}/signposts/sync`가 한 번 호출된다.
- request body에 userId와 최신 table이 포함된다.
- `result=success`일 때만 success로 판정된다.
- Scenario별 label, direction, impact, evidence가 표시된다.
- Signpost 실패 전에는 Confirmation이 활성화되지 않는다.

### TC-V1-N-006 최신 detail 조회 후 Confirmation 성공

목적: 최신 Agent detail로 confirmation body를 만들고 completed를 확인하는지 검증한다.

절차:

1. Signpost 성공 후 Confirmation 단계로 이동한다.
2. 화면이 `GET /scenario-groups/{scenarioGroupId}`를 호출하는지 확인한다.
3. Scenario Group명/설명과 최종 table을 검토한다.
4. confirmation request preview를 확인한다.
5. `Confirmation 실행`을 한 번 클릭한다.

기대결과:

- confirmation 직전에 최신 detail이 조회된다.
- request body의 `scenarioGroup`과 `table`이 최신 detail 및 편집값을 사용한다.
- `POST /scenario-groups/{scenarioGroupId}/confirmation`은 한 번 호출된다.
- `status=success && data.stage=completed`일 때 완료로 판정된다.
- final summary가 현재 workspace에 유지된다.
- 별도 callback이나 detail 관리 화면을 기다리지 않는다.

### TC-V1-N-007 V1 결과 Export

목적: 전체 v1 실행 증적을 secret 없이 내보내는지 확인한다.

절차:

1. v1 workflow를 완료한다.
2. `결과 Export`를 클릭한다.
3. 생성된 JSON을 연다.

기대결과:

- runtime snapshot, Event detail, 단계별 request/response가 포함된다.
- 판정, elapsed time, token usage, warning/error가 포함된다.
- final Scenario Group detail이 포함된다.
- token, Authorization, cookie는 포함되지 않는다.
- UI에 표시된 scenarioGroupId와 export 값이 일치한다.

## 6. v1 오류 및 경계값

### TC-V1-E-001 잘못된 Runtime 입력

입력 조합:

- 빈 Base URL
- 잘못된 URL
- 빈 userId
- 정수가 아닌 userId
- 0 이하 timeout

기대결과:

- 잘못된 값은 API 호출 전에 차단된다.
- `NaN`, 빈 문자열이 request body에 들어가지 않는다.
- 오류 후 입력을 수정할 수 있다.

### TC-V1-E-002 CORS 오류

절차:

1. frontend origin이 허용되지 않은 Agent를 입력한다.
2. 연결 확인을 실행한다.

기대결과:

- 연결 실패로 표시된다.
- 일반 HTTP 500으로 오인하지 않는다.
- CORS allowlist 확인 안내가 표시된다.
- 원본 Event 선택과 기존 결과는 유지된다.

### TC-V1-E-003 Mixed Content

절차:

1. HTTPS frontend에서 HTTP Agent Base URL을 입력한다.
2. 연결 확인을 실행한다.

기대결과:

- 요청 전 또는 browser 차단 후 mixed-content 안내가 표시된다.
- 재시도 loop가 발생하지 않는다.

### TC-V1-E-004 기존 Scenario Group 중복 오류

절차:

1. 기존 group이 있는 Event로 Create를 실행한다.
2. 중복 오류를 확인한다.

기대결과:

- 실패 body와 기존 group 정보가 가능한 범위에서 표시된다.
- 자동 soft delete나 자동 create 재시도가 발생하지 않는다.
- 사용자가 명시적으로 정리 action을 선택할 수 있다.
- hard delete는 노출하지 않는다.

### TC-V1-E-005 HTTP 200 + Create failure

절차:

1. create sync 응답이 HTTP 200, `result=failure`가 되도록 한다.
2. 화면을 확인한다.

기대결과:

- Create가 error로 표시된다.
- failure reason이 표시된다.
- Validation은 잠긴다.
- HTTP 성공을 API 성공으로 오인하지 않는다.

### TC-V1-E-006 Create timeout 또는 취소

절차:

1. 짧은 timeout으로 Create를 실행하거나 응답 전에 취소한다.
2. 상태와 network call 수를 확인한다.

기대결과:

- 상태가 `unknown`으로 표시된다.
- 서버에서 완료되었을 수 있다는 안내가 표시된다.
- 같은 request가 자동 재시도되지 않는다.
- 현재 run의 Create 버튼으로 동일 POST를 다시 보낼 수 없다.
- DB/API 증적 확인 또는 새 run 시작을 안내한다.

### TC-V1-E-007 Validation transport/API 실패

기대결과:

- Validation이 error로 표시된다.
- Scenario table 편집값이 유지된다.
- error raw body가 남는다.
- Signpost는 잠긴다.
- 사용자가 값을 수정한 후 명시적으로 Validation을 다시 실행할 수 있다.

### TC-V1-E-008 Validation invalid 재검증

절차:

1. invalid warning을 만든다.
2. Scenario 값을 수정한다.
3. request preview 확인 후 Validation을 다시 실행한다.

기대결과:

- 재실행 전 확인 dialog가 표시된다.
- 수정된 table만 새 request에 포함된다.
- 이전 validation call record가 보존된다.
- 새 결과가 현재 판정으로 표시된다.

### TC-V1-E-009 Signpost failure

기대결과:

- HTTP 200의 `result=failure`도 error다.
- 이전 Create/Validation 결과가 유지된다.
- Confirmation은 잠긴다.
- failure reason과 raw body가 표시된다.

### TC-V1-E-010 Confirmation failure

입력:

- HTTP 4xx/5xx
- HTTP 200 + `status=error`
- `status=success`지만 `data.stage!=completed`

기대결과:

- 모두 confirmation failure 또는 warning으로 명확히 판정된다.
- 완료 상태로 잘못 이동하지 않는다.
- request/response가 보존된다.
- 수정 후 명시적 재실행만 허용한다.

### TC-V1-E-011 긴 Scenario/JSON

기대결과:

- 긴 title/narrative/signpost가 layout을 깨지 않는다.
- Scenario table은 가로 스크롤된다.
- JSON viewer에서 검색, 접기, 복사가 가능하다.
- 원문을 확인할 수 있다.

### TC-V1-E-012 Browser 새로고침

절차:

1. 완료된 v1 결과를 저장한 상태에서 새로고침한다.
2. 복구 상태를 확인한다.

기대결과:

- secret은 복구되지 않는다.
- 저장 정책 범위의 runtime metadata와 최근 결과가 복구된다.
- 진행 중이던 request는 `unknown`으로 표시된다.
- 자동 API 재호출이 발생하지 않는다.

## 7. v2/v3/v4 정상 동작

### TC-M-N-001 Event ID 직접 선택과 Manifest 고정

목적: 중복 없는 Event 2~5건으로 immutable comparison 조건을 만드는지 확인한다.

절차:

1. `v2/v3/v4 비교` tab을 연다.
2. Event ID 2~5개를 순서대로 입력한다.
3. 각 Event detail 조회 결과를 확인한다.
4. 자동 생성된 comparisonRunId를 확인한다.
5. Manifest Summary에서 실행 조건을 확인한다.
7. `비교 실행`을 클릭한다.

기대결과:

- Event ID가 중복 없이 선택 순서대로 고정된다.
- Event detail snapshot이 manifest에 포함된다.
- Base URL, userId, comparisonRunId가 고정된다.
- 실행 시작 후 입력 control이 잠긴다.

### TC-M-N-002 최신순/오래된순 Event 선택

절차:

1. 목록 선택 mode에서 최신순으로 Event 3건을 선택한다.
2. 선택을 초기화한다.
3. 오래된순으로 Event 3건을 선택한다.

기대결과:

- `GET /events`의 sort query가 선택과 일치한다.
- 선택 순서와 Event ID가 Summary에 표시된다.
- paging 후에도 기존 선택이 유지된다.

### TC-M-N-003 Keyword Event 선택

절차:

1. keyword를 입력하고 최신순 조회한다.
2. 결과에서 Event 2~5건을 선택한다.

기대결과:

- keyword가 `GET /events` query에 포함된다.
- 기본 정렬은 최신순이다.
- 선택 Event detail이 모두 로드된 후 실행 가능하다.

### TC-M-N-004 v2/v3 병렬 후 v4 실행

목적: pipeline의 version barrier를 검증한다.

절차:

1. 유효한 manifest로 비교를 실행한다.
2. browser network와 version card 시간을 확인한다.
3. v2 또는 v3 중 더 늦은 요청이 끝나기 전 v4 호출 여부를 확인한다.

기대결과:

- v2와 v3 POST가 병렬로 시작된다.
- 두 요청 body의 Event, userId, comparisonRunId가 같다.
- v2/v3가 모두 terminal 상태가 된 뒤 v4가 시작된다.
- v4 body에도 동일한 Event, userId, comparisonRunId만 포함된다.
- 각 version POST는 한 번만 호출된다.

확인 증적:

- 세 call의 startedAt/finishedAt
- browser network waterfall
- version별 request body

### TC-M-N-005 세 Version 성공 비교

목적: 세 응답을 Overview에 정확히 표시하는지 확인한다.

기대결과:

- 각 version의 `status=success`와 data가 success로 판정된다.
- `apiVersion`, `comparisonRunId`, Event lineage가 manifest와 일치한다.
- group ID, 제목, 요약, 설명, dimension 수, Scenario 수가 표시된다.
- baseline, floor/ceiling/mixed 수가 표시된다.
- elapsed time과 token usage가 표시된다.
- 성공 version이 2개 이상이므로 비교 view가 활성화된다.

### TC-M-N-006 Dimension 비교

기대결과:

- v2는 Event별 namespace key와 단일 source lineage를 표시한다.
- v3는 composite dimension과 source 관계를 표시한다.
- v4는 Event grounding, lever reference와 supported/unsupported 상태를 표시한다.
- 기본 화면에는 내부 `dimensionId`/`valueId` 대신 Dimension/Value label이 표시된다.
- 중복 Dimension label에는 Event lineage가 붙는다.
- Dimension 선택 근거와 Value별 가격 기여·선택/가정 근거가 표시된다.
- 응답에 근거가 없으면 `제공된 근거 없음`으로 표시하며 새 근거를 추정하지 않는다.
- version별 dimension 수가 v2·v3·v4 모두 3~6개 기준으로 검사된다.
- v2는 dimension에 직접 표현되지 않은 Event도 공동 문맥에 유지한다.
- v3·v4의 covered/uncovered dimension이 원본 diagnostics와 일치한다.

### TC-M-N-007 Scenario 비교

기대결과:

- version별 실제 Scenario title, narrative, cells가 표시된다.
- baseline, role, pressure band, rationale, probability가 표시된다.
- Scenario cells가 사용자용 Dimension/Value label로 표시된다.
- 각 선택 Value에 Dimension 선택 근거와 Value 선택 근거가 연결된다.
- `globalPressureRationale`이 Scenario 조합과 가격 판단 근거로 표시된다.
- 대응 Scenario가 없으면 빈 상태와 제외 사유가 표시된다.
- 모든 version pressure는 `Global LNG pressure`로 표시된다.
- v4 관련 시장은 Scenario 상세 보조정보이며 별도 pressure 태그로 표시하지 않는다.

### TC-M-N-008 Diagnostics 비교

기대결과:

- excluded candidates와 reason이 표시된다.
- excluded dimensions가 표시된다.
- Event impact facts와 interactions가 표시된다.
- coverage status가 표시된다.
- v4 impact catalog version과 unsupported lever details가 표시된다.
- 원본 diagnostics JSON을 펼쳐볼 수 있다.

### TC-M-N-009 결정적 품질 검사

기대결과:

- Scenario 3~5개를 검사한다.
- baseline 정확히 1개를 검사한다.
- M-01~M-08 ID와 검사 목적을 표시한다.
- floor/ceiling 각각 1개를 검사한다.
- mixed가 없어도 M-04를 실패시키지 않는다.
- mixed가 있으면 비극단 band, 실제 bullish·bearish contribution 공존, 상쇄 rationale을 검사한다.
- Scenario 조합과 pressure band 중복, dimension 3~6개, Event lineage, pressure rationale, target band 설명을 검사한다.
- 각 항목에 PASS/WARN/FAIL과 실제 근거가 표시된다.
- 결정적 검사 자체는 LLM 점수나 우수 version을 임의 생성하지 않는다.

### TC-M-N-010 의미 품질 평가와 우수 Version

절차:

1. v2/v3/v4가 모두 성공한 comparison을 완료한다.
2. 자동 LLM 호출이 발생하지 않았는지 확인한다.
3. `품질 평가 실행`을 클릭한다.

기대결과:

- `POST /scenario-group-comparisons/judge/sync`가 한 번 호출된다.
- 요청에는 동일 `comparisonRunId`, userId와 성공한 version/group ID가 포함된다.
- Event 정합성, LNG Dimension, floor/ceiling, mixed 품질이 version별로 표시된다.
- 적용 가능한 기준은 score 1~5와 PASS/WARN/FAIL, 근거, 판단 이유를 가진다.
- 각 Scenario의 verdict와 근거가 해당 Scenario card에 표시된다.
- 적용 가능한 기준의 평균 최고 version이 우수 version으로 표시된다.
- 평균 동점이면 모든 동점 version이 공동 우수로 표시된다.
- 평가 call의 elapsed time과 token usage가 Evidence Drawer에 남는다.

### TC-M-N-011 Optional Mixed 품질 평가

입력 A:

- mixed Scenario가 없는 성공 version

기대결과 A:

- mixed가 없다는 이유로 결정적 검사에서 실패하거나 의미 품질 점수가 감점되지 않는다.
- `mixed_quality`는 `N/A`, `score=null`로 표시되고 평균에서 제외된다.

입력 B:

- mixed role이 있고 bullish와 bearish contribution을 함께 선택한 Scenario

기대결과 B:

- 비극단 pressure band인지 확인한다.
- 실제 상·하방 Value 조합과 `globalPressureRationale`의 상쇄 설명을 근거로 평가한다.
- mixed label만 있고 상쇄 조합이나 근거가 없으면 WARN 또는 FAIL이다.

### TC-M-N-012 Comparison Export

기대결과:

- manifest와 selected Event snapshot이 포함된다.
- v2/v3/v4 request/response가 포함된다.
- transport/API 상태, elapsed time, token usage가 포함된다.
- 결정적 검사 결과가 포함된다.
- 품질 평가 request/response, 기준별 판정, 평균과 `bestVersions`, token usage가 포함된다.
- secret이 없다.
- export의 version별 결과가 화면과 일치한다.

### TC-M-N-013 사용자용 View와 Raw 증적 분리

기대결과:

- Overview, Dimensions, Scenarios에는 사용자용 label과 설명·근거가 우선 표시된다.
- 내부 ID만으로 구성된 표를 사용자가 해석하도록 요구하지 않는다.
- Raw 탭과 Evidence Drawer에는 create 및 judge 원본 request/response가 secret redaction 외 의미 변환 없이 남는다.
- 사용자용 변환에 실패한 필드가 있어도 Raw 원본과 export가 유실되지 않는다.

## 8. v2/v3/v4 오류 및 경계값

### TC-M-E-001 Event 개수 부족/초과

입력:

- Event 0건
- Event 1건
- Event 6건 이상

기대결과:

- 비교 실행이 비활성화된다.
- `중복 없는 Event 2~5건` 안내가 표시된다.
- API call이 발생하지 않는다.

### TC-M-E-002 중복 Event

절차:

1. 같은 Event ID를 두 번 입력하거나 선택한다.

기대결과:

- 중복 선택이 즉시 차단된다.
- manifest와 request body에 중복 ID가 들어가지 않는다.

### TC-M-E-003 Event detail 일부 실패

기대결과:

- 실패 Event card에 오류가 표시된다.
- manifest 고정과 비교 실행이 차단된다.
- 성공한 Event detail은 유지된다.
- 재조회는 GET에 대해서만 허용된다.

### TC-M-E-004 comparisonRunId 공백/길이 초과

기대결과:

- 공백-only와 255자 초과는 validation 오류다.
- API request가 전송되지 않는다.
- 기본 고유값 재생성 action을 제공한다.

### TC-M-E-006 v2 실패, v3 성공

절차:

1. v2만 API error가 되도록 한다.
2. 실행 순서와 결과 보존을 확인한다.

기대결과:

- v2는 error, v3는 success로 독립 표시된다.
- v2/v3가 terminal이므로 v4는 실행된다.
- v3와 v4 결과 비교가 가능하다.
- v3와 v4가 모두 성공하면 두 version만으로 품질 평가를 실행할 수 있다.
- v2 raw 오류가 보존된다.
- 자동 v2 재시도는 없다.

### TC-M-E-007 v2/v3 모두 실패

기대결과:

- 두 version error 이후 v4는 한 번 실행된다.
- v4 성공 여부와 무관하게 성공 version이 2개 미만이면 `비교 판정 불가`다.
- 개별 version 결과와 raw body는 확인 가능하다.

### TC-M-E-008 v2 timeout

절차:

1. v2가 timeout되도록 한다.
2. v3와 v4 실행 상태를 확인한다.

기대결과:

- v2는 unknown이다.
- v2 POST는 재시도되지 않는다.
- v3 terminal과 v2 unknown 처리 이후 barrier가 종료된다.
- v4가 한 번 실행된다.
- 중복 DB 생성 가능성을 경고한다.

### TC-M-E-009 v3 응답 전 v4 금지

절차:

1. v3 응답을 지연시킨다.
2. v2가 먼저 완료되도록 한다.

기대결과:

- v4 card는 `v2/v3 종료 대기`다.
- v3 terminal 전 v4 network request가 없다.

### TC-M-E-010 v4 실패

기대결과:

- v2/v3 성공 결과는 유지된다.
- v4 오류와 raw body가 표시된다.
- v2/v3 비교는 가능하다.
- v4 자동 재시도는 없다.

### TC-M-E-011 HTTP 200 + `status=error`

각 version에 대해 반복한다.

기대결과:

- HTTP 200이어도 error로 판정된다.
- message가 version card와 Evidence Drawer에 표시된다.
- `data=null`을 안전하게 처리한다.

### TC-M-E-012 apiVersion 불일치

기대결과:

- transport/API success와 별도로 integrity FAIL을 표시한다.
- 다른 version column에 잘못 배치하지 않는다.
- raw response를 유지한다.

### TC-M-E-013 comparisonRunId 불일치

기대결과:

- integrity FAIL이다.
- 결과를 정상 비교에 포함하지 않는다.
- manifest 값과 응답 값을 함께 표시한다.

### TC-M-E-014 Event lineage 불일치

입력:

- Event 누락
- Event 추가
- 순서 또는 ID 불일치

기대결과:

- lineage check가 FAIL 또는 명시적 WARN이다.
- 불일치 Event ID가 표시된다.
- 원본 response를 변경하지 않는다.

### TC-M-E-015 성공 Version 1개

기대결과:

- 상단 결론은 `비교 판정 불가`다.
- 성공 version의 Dimensions, Scenarios, Diagnostics는 조회 가능하다.
- 우수 version을 표시하지 않는다.
- 품질 평가 버튼이 비활성화되고 Agent judge API를 호출하지 않는다.

### TC-M-E-016 모든 Version 실패/unknown

기대결과:

- 빈 비교 table 대신 version별 실패 원인을 표시한다.
- manifest와 call records를 export할 수 있다.
- 자동 새 run 또는 자동 재시도가 없다.

### TC-M-E-017 요청 취소

절차:

1. v2/v3 실행 중 한 요청을 취소한다.

기대결과:

- 취소된 version은 unknown이다.
- 다른 version 요청은 보존된다.
- barrier는 모든 version이 terminal 처리된 뒤 종료된다.
- 취소된 POST를 자동 재호출하지 않는다.

### TC-M-E-018 알 수 없는 응답 필드

기대결과:

- 알려진 비교 UI가 깨지지 않는다.
- unknown field가 raw JSON에 그대로 남는다.
- export에도 원본 response가 포함된다.

### TC-M-E-019 매우 큰 응답

기대결과:

- version card와 Overview가 먼저 렌더링된다.
- JSON viewer가 UI thread를 장시간 차단하지 않는다.
- 긴 Dimensions/Scenarios는 pagination, virtualization 또는 접기를 사용한다.
- export가 원본 데이터를 누락하지 않는다.

### TC-M-E-020 Browser 새로고침

절차:

1. 비교 완료 후 새로고침한다.
2. 비교 실행 중 새로고침하는 경우도 확인한다.

기대결과:

- 완료 결과는 저장 정책 범위에서 복구된다.
- 실행 중 version은 unknown으로 복구된다.
- 동일 POST를 자동 재개하지 않는다.
- secret은 복구되지 않는다.

### TC-M-E-021 품질 평가 요청 무결성 오류

입력:

- 다른 comparisonRunId의 Scenario Group
- 요청 apiVersion과 저장된 apiVersion 불일치
- 다른 userId가 소유한 Scenario Group
- Event lineage가 다른 Scenario Group

기대결과:

- Agent가 품질 평가를 거부한다.
- 오류 원인과 judge raw response가 표시된다.
- 기존 create 결과와 결정적 검사 결과는 유지된다.
- 우수 version을 표시하지 않는다.

### TC-M-E-022 품질 평가 실패와 재실행

절차:

1. judge 요청을 LLM 오류 또는 timeout으로 실패시킨다.
2. create 결과가 유지되는지 확인한다.
3. `품질 평가 다시 실행`을 클릭한다.

기대결과:

- 실패 또는 timeout은 judge 상태에만 error/unknown으로 기록된다.
- v2/v3/v4 create POST는 다시 호출되지 않는다.
- 사용자의 명시적 action으로 judge 요청만 다시 호출된다.
- 각 judge 시도의 request/response와 token usage가 별도 call record로 남는다.

### TC-M-E-023 잘못된 품질 평가 응답

입력:

- 요청 version 누락 또는 추가
- 필수 criterion 누락 또는 중복
- Scenario 판단 누락 또는 다른 Scenario ID
- `mixed_quality=N/A`인데 score가 존재하는 응답
- 평균 최고 version과 `bestVersions` 불일치

기대결과:

- 정상 품질 평가 결과로 수용하지 않는다.
- schema/integrity 오류를 표시하고 우수 version을 노출하지 않는다.
- 원본 judge response는 Raw와 export에 보존된다.

## 9. 공통 UI 테스트

### TC-UI-001 Workspace 독립 상태

절차:

1. v1 결과를 만든다.
2. comparison 실행을 시작한다.
3. 두 tab을 왕복한다.

기대결과:

- 각 workspace의 Event, 실행 상태, 결과가 유지된다.
- tab 전환으로 API가 취소되거나 중복 호출되지 않는다.

### TC-UI-002 Evidence Drawer

기대결과:

- timeline에서 call을 선택할 수 있다.
- request, parsed response, raw response를 전환할 수 있다.
- JSON 검색, 접기, 복사가 동작한다.
- method, URL, HTTP status, elapsed time이 항상 보인다.

### TC-UI-003 Loading과 이전 결과 보존

기대결과:

- active request에만 spinner 또는 overlay가 표시된다.
- 이전 성공 결과가 사라지지 않는다.
- 관련 action만 disabled 된다.

### TC-UI-004 반응형

viewport:

- desktop 1440px
- tablet 1024px
- mobile 390px

기대결과:

- version card와 table이 잘리지 않고 스크롤 가능하다.
- mobile에서 version switcher가 동작한다.
- Evidence Drawer가 full-screen overlay로 열린다.
- primary action이 다른 control과 겹치지 않는다.

### TC-UI-005 Keyboard와 Focus

기대결과:

- Runtime Settings, tabs, Event selector, step action, drawer를 keyboard로 조작할 수 있다.
- focus ring이 보인다.
- dialog focus가 내부에 유지되고 닫힌 뒤 trigger로 돌아간다.

### TC-UI-006 상태 접근성

기대결과:

- success/warning/error/unknown이 색상만으로 표현되지 않는다.
- loading과 완료가 live region으로 전달된다.
- icon-only button에 accessible name이 있다.
- form 오류가 입력과 연결된다.

## 10. 보안 및 배포 테스트

### TC-SEC-001 Backend 의존성 제거

검사:

- frontend network call
- build/runtime 설정
- repository path

기대결과:

- `/backoffice/api/...` 호출이 없다.
- callback receiver, OAuth mock, SSE endpoint 의존성이 없다.
- 정적 frontend만으로 실행된다.
- Backoffice Python runtime이 필요하지 않다.

### TC-SEC-002 Secret 저장 금지

절차:

1. 인증값이 필요한 환경에서 요청한다.
2. localStorage, sessionStorage, IndexedDB를 검사한다.
3. 결과를 export한다.

기대결과:

- secret이 browser storage에 없다.
- export에 Authorization/token/cookie가 없다.
- UI에서 인증값이 마스킹된다.

### TC-SEC-003 URL과 Scheme

기대결과:

- trailing slash가 있어도 API path가 이중 slash가 되지 않는다.
- HTTPS/HTTP mixed-content를 명확히 안내한다.
- 사용자가 입력한 Base URL 외의 임의 host로 요청하지 않는다.

## 11. 수동 Pipeline 교차 검증

frontend의 API 실행 결과를 기존 manual pipeline과 비교할 때 다음 기준을 사용한다.

### 11.1 v1

기준 script:

```bash
python tests/manual/test_sync_pipeline_api.py \
  --base-url http://localhost:8001 \
  --mi-event-id 12345 \
  --user-id 10001 \
  --timeout 1200 \
  --yes
```

교차 확인:

- API 순서
- 각 단계 성공 판정
- validation invalid warning 처리
- Scenario Group ID와 final stage
- elapsed time/token usage

frontend와 script를 같은 Event에 연속 실행하면 중복 group이 발생할 수 있으므로 별도 Event를 사용하거나 실행 사이에 soft delete한다.

### 11.2 v2/v3/v4

기준 script:

```bash
python tests/manual/test_multi_event_scenario_versions.py prepare \
  --base-url http://localhost:8001 \
  --event-ids 101 202 \
  --user-id 10001 \
  --timeout 1200
```

이후 동일 manifest로 v2/v3 barrier 후 v4를 실행하고 report를 만든다.

교차 확인:

- manifest Event/userId/comparisonRunId
- version별 request body
- 실행 순서
- Scenario/dimension 실제 값
- diagnostics
- elapsed time/token usage
- 결정적 검사
- 사용자용 Dimension/Value label과 선택 근거
- 의미 품질 기준, Scenario 판단, 평균과 우수 version

manual report의 Agent Judge와 Backoffice Agent 평가 API는 동일한 Event/API 증적과 평가 기준을 사용해야 한다. 다만 결정적 검사와 의미 품질 평가는 서로 다른 판정이며 같은 결과로 간주하지 않는다. mixed가 없는 version은 Backoffice 계약에 따라 `N/A`로 처리하고 평균에서 제외한다.

## 12. 회귀 체크리스트

### 공통

- [ ] 정적 frontend가 backend 없이 렌더링된다.
- [ ] Agent Base URL 연결 확인이 동작한다.
- [ ] CORS와 mixed-content 오류가 구분된다.
- [ ] `/backoffice/api/...` 호출이 없다.
- [ ] Evidence Drawer에 모든 request/response가 남는다.
- [ ] token/secret이 storage와 export에 없다.
- [ ] tab 전환으로 실행이 취소되거나 중복되지 않는다.

### v1

- [ ] Event 한 건만 선택된다.
- [ ] Create는 `/scenario-groups/sync`를 한 번 호출한다.
- [ ] Scenario table을 편집할 수 있다.
- [ ] Validation body에 최신 table이 포함된다.
- [ ] invalid validation이 warning으로 표시된다.
- [ ] Signpost는 `result=success`로 판정된다.
- [ ] Confirmation 전 최신 detail을 조회한다.
- [ ] Confirmation은 `status=success`, `data.stage=completed`로 판정된다.
- [ ] timeout/cancel 뒤 자동 재시도하지 않는다.
- [ ] v1 bundle export가 동작한다.

### v2/v3/v4

- [ ] Event 2~5건만 선택된다.
- [ ] comparisonRunId가 고유하고 실행 중 고정된다.
- [ ] v2/v3는 동일 manifest로 병렬 실행된다.
- [ ] v2/v3 terminal 이후 v4가 실행된다.
- [ ] v2/v3/v4 request 조건이 동일하다.
- [ ] 동일 version POST를 자동 재시도하지 않는다.
- [ ] 부분 실패 결과가 보존된다.
- [ ] 성공 version 2개 미만이면 `비교 판정 불가`다.
- [ ] 모든 version pressure가 `Global LNG pressure`로 일관되고 v4 `relatedMarkets`는 보조정보로만 표시된다.
- [ ] Dimensions, Scenarios, Diagnostics를 비교할 수 있다.
- [ ] Scenario Group 제목·요약·설명과 Dimension/Value 선택 근거를 사용자용 label로 볼 수 있다.
- [ ] Raw 원본은 사용자용 view와 분리되어 보존된다.
- [ ] 결정적 검사 M-01~M-08 결과가 실제 응답과 일치한다.
- [ ] mixed 미생성은 실패/감점하지 않고 mixed가 있을 때만 실제 조합과 근거를 평가한다.
- [ ] 성공 version 2개 이상이면 사용자 action으로 의미 품질 평가를 실행할 수 있다.
- [ ] 평균 최고 version과 공동 우수 version이 정확히 표시된다.
- [ ] comparison bundle export가 동작한다.
