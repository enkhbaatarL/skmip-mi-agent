# Interpret Agent 테스트와 품질 가이드

## 이 문서는 누구를 위한 문서인가요?

이 문서는 Interpret Agent의 API 계약, callback, tracing, 일반 텍스트 출력과 배포 preview를 확인하려는 개발자와
검증 담당자를 위한 문서다.

현재 repository에는 Interpret Agent 전용 Codex·Claude Skill이 없다. Scenario Agent의
`scenario-sync-pipeline`이나 Model Parameter Agent용 Skill을 Interpret 테스트에 사용한다고 가정하지 않는다.
현재 정본은 `tests/automated/test_interpret_*.py`와
`tests/manual/interpret_agent/smoke_test_deployed_api.py`다.

```text
자동 테스트
  → schema·route·callback·plain text·trace 계약 확인

배포 smoke
  → OpenAPI·route 격리·request validation·실제 preview 확인

사람의 품질 검토
  → 근거 범위·시장 해석·신뢰도·실무 제언 확인
```

## 가장 먼저 구분할 것

### API 성공

다음과 같은 transport·구조 계약이 맞는지 확인한다.

- preview가 HTTP 200과 예상 JSON shape을 반환함
- 요청한 대상 중 실제 조회된 Scenario가 결과에 나타남
- meta의 기준 ID와 지수 순서가 맞음
- async success·failure callback shape이 맞음
- 사용자 표시 문자열에 Markdown·HTML 표현 서식이 남지 않음

### 해석 품질

다음과 같은 내용 판단이 타당한지 확인한다.

- Feature 변화와 가격 반응의 방향을 근거와 다르게 쓰지 않음
- JKM·TTF·HH의 차이를 과장하거나 바꾸지 않음
- 수렴 시점과 anomaly를 근거가 있을 때만 설명함
- 데이터 품질 문제가 있으면 신뢰도를 낮춰 설명함
- 실무 대응이 해석 근거와 연결됨

API가 성공해도 해석 품질이 자동으로 보장되지는 않는다. 두 결과를 구분해서 보고한다.

## 빠른 자동 테스트

repository root에서 다음 명령을 실행한다.

```bash
PYTHONDONTWRITEBYTECODE=1 METADATA_DB_PORT=3306 pytest -p no:cacheprovider \
  tests/automated/test_interpret_callback_contract.py \
  tests/automated/test_interpret_plain_text.py \
  tests/automated/test_interpret_tracing.py \
  tests/automated/test_model_parameter_nullable_event_consumers.py
```

마지막 파일은 Model Parameter 공통 회귀도 포함하지만, Interpret가 `mi_event_id=null`인 proposal을 읽는 계약을
직접 검증한다.

개별 영역만 빠르게 확인하려면 다음처럼 실행한다.

```bash
METADATA_DB_PORT=3306 pytest tests/automated/test_interpret_callback_contract.py
METADATA_DB_PORT=3306 pytest tests/automated/test_interpret_plain_text.py
METADATA_DB_PORT=3306 pytest tests/automated/test_interpret_tracing.py
```

`envs/config.yaml`의 `${METADATA_DB_PORT}` placeholder가 shell에서 이미 치환되는 환경이면 기존 값을 사용해도
된다. 위 3306은 DB를 호출하지 않는 이 단위 test 묶음의 Settings parsing을 위한 기본값이다.

## 자동 테스트가 확인하는 것

### `test_interpret_callback_contract.py`

| 검사 | 확인 내용 |
| --- | --- |
| callback URL | base URL과 기존 callback path가 정확히 결합됨 |
| route isolation | Interpret 두 route는 `interpret.py` app에만 있고 `main.py` app에는 없음 |
| callback content | Scenario 네 필드가 고정 label과 개행으로 합쳐짐 |
| success callback | `result=success`, `reason=null`, integer `scenarioId`, interpretations 배열 |
| failure callback | `result=failure`, failure reason, `interpretations=null` |
| plain text | callback fixture에 사용한 Markdown·HTML 표식이 남지 않음 |

callback 전송 함수는 mock이다. 실제 OAuth2 token 발급, network, 수신 backend 저장은 이 테스트가 검증하지
않는다.

### `test_interpret_plain_text.py`

다음 표현을 일반 텍스트로 바꾸는 규칙을 검증한다.

- Markdown heading과 blockquote
- `**`, `__` 이중 강조와 inline code 표식
- Markdown link
- unordered·ordered list
- code indentation과 horizontal rule
- 알려진 HTML tag
- 불완전하게 남은 강조 표식

또한 Scenario output, Group synthesis, callback item의 모든 사용자 표시 필드가 schema 생성 시 정규화되는지
확인한다. 프롬프트와 structured-output description이 일반 텍스트를 요구하는지도 확인한다.

### `test_interpret_tracing.py`

| 검사 | 확인 내용 |
| --- | --- |
| config profile | `interpret_agent` MLflow experiment·AIP app ID·enabled 값 |
| startup | lifespan이 Interpret Agent 이름으로 tracing을 초기화함 |
| graph | `TraceContext`를 context schema로 선언함 |
| top-level invoke | 하나의 transaction·session context를 graph에 전달함 |
| LLM nodes | Scenario별 호출과 Group synthesis가 같은 trace context·callbacks를 받음 |
| stream setting | `llm_stream_enabled`가 LLM connector로 전달됨 |

이 테스트는 실제 MLflow server에 trace가 저장되는지 조회하지 않는다.

### `test_model_parameter_nullable_event_consumers.py`

Interpret 관련 검사는 다음 두 가지다.

- 최신 proposal의 `mi_event_id`가 null이어도 Feature 정규화가 성공함
- loader가 proposal Event ID를 요구하지 않고 target Scenario와 Feature를 구성함

가격 loader는 mock이므로 실제 모델 결과 SQL은 검증하지 않는다.

## 배포 preview smoke test

### 안전 범위

수동 runner는 다음 endpoint만 업무 호출한다.

```text
POST /scenario-groups/{scenario_group_id}/price-interpretations/preview
```

비동기 endpoint는 호출하지 않으므로 callback을 발생시키지 않는다. DB에는 SELECT만 수행한다. 다만 실제 LLM
호출과 trace·log 기록은 발생할 수 있고 실행 비용과 시간이 든다.

### 실행 명령

```bash
python tests/manual/interpret_agent/smoke_test_deployed_api.py \
  --base-url <Interpret Agent base URL> \
  --scenario-group-id <Scenario Group ID> \
  --scenario-id <Scenario ID> \
  --timeout-sec 900 \
  --output local/output/interpret_agent/<run_id>/result.json
```

Scenario ID를 여러 개 고르려면 `--scenario-id`를 반복한다.

```bash
python tests/manual/interpret_agent/smoke_test_deployed_api.py \
  --base-url http://localhost:8003 \
  --scenario-group-id 183 \
  --scenario-id 1077 \
  --scenario-id 1078 \
  --output local/output/interpret_agent/manual/result.json
```

실행 전에 Group의 최신 `PROPOSED` 또는 `CONFIRMED` proposal과 완료 가격 run이 있는지 확인한다. runner의
default ID는 특정 배포 예시일 뿐 다른 환경에서 유효하다는 보장이 없다.

### smoke check 목록

| ID | 확인 내용 | 실패 의미 |
| --- | --- | --- |
| `INT-DOCS-001` | `/docs` HTTP 200 | local docs 제공 문제 |
| `INT-OPENAPI-002` | `/openapi.json` HTTP 200 | OpenAPI 제공 문제 |
| `INT-ROUTE-ISOLATION-003` | 업무 path가 Interpret 두 개뿐 | 잘못된 app package 포함 또는 route 변경 |
| `INT-VALIDATION-004` | 숫자로 변환할 수 없는 string Scenario ID가 HTTP 422 | request schema 회귀 |
| `INT-PREVIEW-HTTP-005` | preview HTTP 200 | DB·LLM·서버 오류 |
| `INT-PREVIEW-SCENARIOS-006` | 반환 ID set과 요청 ID set 일치 | proposal 누락, filter subset, 잘못된 결과 |
| `INT-PREVIEW-META-007` | `MI Base`, JKM·TTF·HH 순서 | meta 계약 회귀 |
| `INT-PLAIN-TEXT-008` | 필수 표시값 non-empty, runner가 열거한 금지 marker 없음 | prompt 또는 sanitizer 회귀 |

`INT-PREVIEW-SCENARIOS-006`은 API 자체보다 엄격하다. API는 요청 ID 일부의 proposal이 없어도 발견된 subset으로
성공하지만 smoke runner는 요청한 ID set 전체가 돌아오기를 기대한다. 따라서 이 check가 실패하면 먼저 실제
proposal availability를 확인한다.

`INT-PLAIN-TEXT-008`도 모든 Markdown 문법을 파싱하는 검사가 아니다. runner에 등록된 heading, link, 일부
목록·code·HTML·강조 marker를 확인하므로, single emphasis, 취소선, `~~~` fence 같은 미등록 문법은 별도
검토가 필요하다.

### 결과 파일

`--output`을 지정하면 JSON에 다음 증적이 저장된다.

- 실행 시작·종료 시각
- base URL, Group ID, Scenario ID 목록
- OpenAPI SHA-256과 전체 path
- preview elapsed seconds와 HTTP status
- preview 전체 JSON response
- check별 pass/fail과 detail
- prompt 글자 수 제한 초과 warning
- 전체 `passed`

runner는 output directory를 자동으로 만든다. 비밀값이나 OAuth2 token을 인자로 받거나 저장하지 않는다.

## 비동기 callback을 검증할 때

현재 전용 배포 runner는 async endpoint를 호출하지 않는다. async 검증은 외부 callback을 실제로 발생시키므로
다음을 먼저 정해야 한다.

- callback 수신 환경과 허용된 Scenario Group
- callback OAuth2 credential 주입 여부
- 같은 요청을 다시 실행해도 되는지
- 수신 backend에서 결과를 확인할 방법
- callback 실패 시 server log를 확인할 권한

최소 확인 항목은 다음과 같다.

1. async POST의 실제 HTTP status가 200인지 확인한다.
2. body가 `data.status=PROCESSING`인지 확인한다.
3. success callback의 `scenarioId`가 integer이고 `content`가 plain text인지 확인한다.
4. 실패 입력은 failure callback의 `interpretations=null`로 오는지 확인한다.
5. callback이 오지 않으면 Interpret DB 상태 조회를 시도하지 말고 server·connector log를 확인한다.

현재 operation ID, callback retry queue, polling API가 없으므로 callback 환경을 준비하지 않은 상태에서 async
smoke를 실행하지 않는다.

## 품질 결과를 읽는 법

### 1. 대상 coverage

먼저 요청 ID와 실제 결과 ID를 비교한다. API는 missing ID를 strict하게 차단하지 않기 때문에 일부 Scenario만
해석된 성공 응답이 나올 수 있다.

```text
요청 ID set == response Scenario ID set
```

전체 coverage가 필요한 검증에서는 이 조건을 명시적으로 확인한다.

### 2. 입력 근거 coverage

`meta.features`가 기대한 proposal parameter를 포함하는지 확인한다. 다만 API는 raw Feature diff와 price diff를
반환하지 않으므로 문장 속 수치를 원본과 완전히 대조하려면 DB 조회 또는 trace의 LLM input 증적이 추가로
필요하다.

확인할 질문은 다음과 같다.

- 확정된 proposal이라면 `confirmationParameters`의 값이 반영되었는가?
- monthly·annual Feature가 올바른 기간으로 해석되었는가?
- Country·Region·qualifier가 다른 series가 섞이지 않았는가?
- MI Base와 공통 기간이 없는 근거를 LLM이 있는 것처럼 말하지 않았는가?

### 3. 가격 지수 해석

JKM·TTF·HH의 방향과 상대 크기를 확인한다. `meta.indices`는 고정 목록이므로 세 값이 보인다는 사실만으로 세
지수 price series가 모두 조회되었다고 판단하지 않는다.

Feature의 geo label과 시장 연결은 LLM 추론이다. 다음은 사람이 별도로 확인해야 한다.

- 한국·아시아 Feature를 JKM과 자연스럽게 연결했는가?
- 유럽 Feature를 TTF, 미국 Feature를 HH와 잘못 바꾸지 않았는가?
- 모호한 region을 특정 지수의 확정 원인처럼 과장하지 않았는가?

### 4. 수치와 anomaly

수치 표기는 prompt가 원래 자리수를 유지하도록 요구한다. `+0.003` 같은 작은 값이 `+0.0`으로 뭉개지지 않았는지
본다.

음수 가격, 25% 이상이면서 `1.0 $/MMBtu` 이상인 급변, Feature 극단 편차가 있으면 summary와 Group 제언이
저신뢰·검증 필요성을 설명하는지 확인한다.

### 5. Plain text

최종 사용자 필드에 다음 표현용 서식이 없어야 한다.

- Markdown heading·link·code fence
- `**`, `__`, backtick 같은 강조·code marker
- `<strong>`, `<b>`, `<em>`, `<i>` 같은 HTML tag
- Markdown bullet prefix와 horizontal rule

일반 텍스트의 개행, `■ ` 구분 문자, 음수 기호, 곱셈의 `*`처럼 의미 있는 문자는 허용한다.

### 6. 길이

prompt 기준은 45·220·220·260·600자다. 수동 runner는 초과를 `qualityWarnings`에 기록하지만 전체 smoke
`passed`를 false로 만들지 않는다. schema도 길이를 강제하지 않으므로 초과는 API contract failure가 아니라
현재 prompt 품질 warning이다.

## 바로 복사해서 요청하는 테스트 프롬프트

현재 Interpret 전용 Skill은 없으므로 아래 요청은 repository의 test file과 runner를 직접 사용하도록 쓴다.

### 자동 계약 테스트

```text
현재 branch의 Interpret Agent 자동 테스트를 실행해 주세요.

- callback contract
- plain-text sanitizer와 output schema
- MLflow trace context 전달
- nullable proposal event 소비

pytest cache와 bytecode를 남기지 말고, 테스트별 성공·실패와 실패 원인을 알려 주세요.
코드나 설정은 수정하지 마세요.
```

### 배포 preview만 검증

```text
tests/manual/interpret_agent/smoke_test_deployed_api.py를 사용해 주세요.

- 실행 환경: <Interpret Agent base URL>
- Scenario Group ID: <ID>
- Scenario ID: <ID 목록>
- 범위: OpenAPI와 route 격리, invalid request 422, preview 결과, plain-text 계약
- 안전 조건: async endpoint와 callback은 호출하지 않음

check별 PASS·FAIL, preview 수행시간, 반환 Scenario coverage, 품질 warning과 결과 JSON 경로를 알려 주세요.
```

### 실제 callback까지 검증

```text
Interpret Agent async callback 계약을 검증해 주세요.

- 실행 환경: <Interpret Agent base URL>
- callback 수신 환경: <허용된 backend 또는 mock server>
- Scenario Group ID: <ID>
- Scenario ID: <ID 목록>
- 확인 범위: HTTP 200 PROCESSING 접수, success callback plain text, failure callback shape

실제 외부 callback side effect가 있으므로 호출 전에 대상과 credential 준비 상태를 확인하고,
같은 요청을 자동 재시도하지 마세요. operation/polling API가 없다는 점도 결과에 명시해 주세요.
```

## 현재 미검증 범위

tracked 자동·수동 테스트만으로는 다음 내용을 보장하지 않는다.

- 실제 MySQL에서 proposal 최신 row·CONFIRMED 우선 query가 기대대로 동작함
- 세 모델 결과 table raw SQL과 최신 completed run 선택이 실제 schema에서 동작함
- 일부 `scenarioIds`만 존재할 때 subset으로 처리되는 API 동작
- 일부 가격 지수만 없을 때 남은 지수로 해석되는 동작
- Feature·가격 diff metric의 모든 threshold·segment·convergence 경계값
- 여러 Scenario proposal의 `basecaseValue` 충돌 처리
- 실제 LLM의 수치 충실도, 지역↔지수 연결 정확도, 문체·글자 수 준수율
- Scenario 원문과 Event 사실에 대한 grounding
- 실제 OAuth2 token 발급과 callback backend 수신
- 401 외 callback 오류의 운영 복구
- process 재시작 중 FastAPI BackgroundTask 유실 여부
- 중복 async 요청과 idempotency
- 대량 Scenario 병렬 호출의 rate limit·성능·비용
- 실제 MLflow server의 trace 저장·검색·민감정보 노출 점검
- endpoint 인증·인가와 사용자별 Scenario 접근 제어

이 항목을 확인하지 않았다면 최종 보고서에 `미실행`, `미검증`, `환경 필요` 중 하나로 명시한다. 추정으로
`PASS` 처리하지 않는다.

## 변경별 최소 회귀 범위

| 변경 | 최소 확인 |
| --- | --- |
| API path·schema | callback contract + 배포 OpenAPI smoke |
| plain-text sanitizer | plain text test + callback content + 배포 preview |
| prompt | structured output test + 실제 preview 품질·길이 warning |
| proposal loader | nullable Event test + MySQL read integration |
| price repository | 실제 세 지수 read + completed run·period 정렬 |
| diff metric | 경계값 단위 테스트 + LLM evidence snapshot |
| callback client·URL | mock contract + 허용된 callback 환경 integration |
| tracing | tracing automated test + 접근 가능한 MLflow trace 확인 |
| async lifecycle | 접수 200, callback terminal, process failure·중복 요청 점검 |

## 구현·테스트 정본

- API contract: `apps/agents/interpret_agent/flows/interpret_price/api_schema.py`
- flow: `apps/agents/interpret_agent/flows/interpret_price/flow.py`
- deterministic metric: `apps/agents/interpret_agent/utils/series_metrics.py`
- callback automated test: `tests/automated/test_interpret_callback_contract.py`
- plain-text automated test: `tests/automated/test_interpret_plain_text.py`
- tracing automated test: `tests/automated/test_interpret_tracing.py`
- nullable Event regression: `tests/automated/test_model_parameter_nullable_event_consumers.py`
- deployed preview smoke: `tests/manual/interpret_agent/smoke_test_deployed_api.py`
