# Scenario Group Agent Backoffice CORS 및 API 계약 점검

## 1. 점검 범위

다음 문서를 기준으로 Browser가 Scenario Group Agent를 직접 호출할 때 필요한 계약을 점검했다.

- `docs/backoffice/PRD.md`
  - 5.1 Browser → Agent 직접 호출과 CORS
  - 9.3 다중 Event 요청
  - 9.5 버전별 생성 의미
  - 9.6 성공 판정
  - 14.2, 14.4 인수 조건
- `docs/backoffice/TEST_SCENARIOS.md`
  - 3 공통 사전조건
  - 3.1 Agent 실행 조건
  - TC-V1-N-001~006
  - TC-M-N-001~009
- `docs/architectures/scenario_group_agent_api_request_response.md`
- `docs/architectures/scenario_group_agent_flow_pipeline.md`
- `docs/architectures/project_directory_structure.md`

소스에서는 아래 router, schema, flow를 확인했다.

- `main.py`
  - FastAPI app과 `CORSMiddleware`
- `apps/agents/scenario_group_agent/api.py`
  - events, unversioned sync, versioned sync, management router가 모두 등록됨
- `routers/events.py`
  - `GET /events`
  - `GET /events/{mi_event_id}`
- `routers/scenario_generation_sync.py`
  - `POST /scenario-groups/sync`
  - `POST /scenario-groups/{scenario_group_id}/validation/sync`
  - `POST /scenario-groups/{scenario_group_id}/signposts/sync`
- `routers/versioned_scenario_generation_sync.py`
  - `POST /v1/scenario-groups/sync`
  - `POST /v2/scenario-groups/sync`
  - `POST /v3/scenario-groups/sync`
  - `POST /v4/scenario-groups/sync`
- `routers/scenario_generation.py`
  - `POST /scenario-groups/{scenario_group_id}/confirmation`
- `routers/scenario_group_management.py`
  - `GET /scenario-groups/{scenario_group_id}`
- `flows/create_multi_event_scenarios/api_schema.py`
- `flows/create_multi_event_scenarios/flow.py`
- `flows/create_multi_event_scenarios/v4_flow.py`
- `flows/confirm_generation/flow.py`
- `flows/confirm_generation/nodes.py`
- `schemas/endpoint.py`
- `apps/persistence/event/schema.py`
- `apps/persistence/scenario/schema.py`

## 2. 이미 올바른 것으로 확인한 계약

### Event 조회

`GET /events`는 `keyword`, `status`, `eventTypeL1Id`, `eventTypeL2Id`,
`recommendedOnly`, `dateFrom`, `dateTo`, `sort`, `page`, `pageSize`를 받고
`EventService.list_events()`에 전달한다. `GET /events/{mi_event_id}`는 Event
상세와 Scenario Template을 `EventService.get_event_detail()`에서 조회한다.

### v1 sync 단계

create, validation, signpost sync endpoint는 각 inline graph를 직접 기다린 뒤
callback body를 HTTP 응답으로 반환한다. inline 함수에는 `send_callback()` 호출이나
callback URL 조립이 없다. callback 설정은 background 함수에서만 사용한다.

confirmation은 `run_confirm_generation()`을 동기 `await`하고, DB 조회·확정·snapshot
저장 graph만 실행한다. callback connector와 callback OAuth 설정을 참조하지 않는다.
성공 응답은 `status=success`, `data.status=created`, `data.stage=completed` 계약이다.
따라서 callback URL/token이 비어 있어도 confirmation HTTP 응답 경로에는 영향이 없다.

### Versioned sync 공통 응답

`VersionedCreateScenariosData`는 `apiVersion`, `generationStrategy`,
`comparisonRunId`, `events`, `dimensionDefinitions`, `table`,
`generationDiagnostics`, 선택적 `usage`를 가진다
(`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/api_schema.py:125`).
v2/v3 flow는 이 필드를 실제 생성 결과에 채운다
(`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/flow.py:157`).

v2/v3 요청은 camelCase alias 기준 `miEventIds`, `userId`, `comparisonRunId`이며,
Event 2~5건, 양수 ID, 중복 금지, 공백이 아닌 255자 이하 run ID를 검증한다.
v4의 `targetMarket`은 `JKM | TTF | HH` Literal로 제한된다
(`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/api_schema.py:63`).

## 3. 변경 사항

### 3.1 명시적 CORS allowlist

`Settings`에 `cors_allowed_origins`를 추가했다
(`apps/common/configs/config.py:231`).

기본값:

```text
http://127.0.0.1:5173
http://localhost:5173
```

환경변수 이름은 `CORS_ALLOWED_ORIGINS`다. `NoDecode`와 before validator를 사용해
다음 두 형식을 모두 지원한다
(`apps/common/configs/config.py:31`, `apps/common/configs/config.py:240`).

```dotenv
CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

```dotenv
CORS_ALLOWED_ORIGINS=["http://127.0.0.1:5173","http://localhost:5173"]
```

각 origin의 앞뒤 공백과 마지막 `/`는 제거하고, 중복은 입력 순서를 유지한 채
한 번만 남긴다. 빈 항목은 제외한다. credential CORS에서 잘못된 `*`는 설정
validation 오류로 거부한다.

`main.py:64`는 더 이상 `["*"]`를 사용하지 않고
`get_settings().cors_allowed_origins`를 `CORSMiddleware`에 전달한다.
`allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`는 유지했다.

### 3.2 v2/v3 Event lineage 순서

변경 전에는 v2/v3 prepare가 `miEventIds`를 숫자 오름차순으로 다시 정렬했다.
이 경우 frontend manifest가 고정한 Event 순서와 응답 `events` 순서가 달라지고,
같은 `comparisonRunId`의 v4 lineage 검증과도 충돌할 수 있었다.

변경 후에는 request의 `miEventIds` 순서를 그대로 사용한다
(`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/flow.py:61`).
DB group-event 연결, prompt, 응답 `events`가 모두 같은 순서를 공유한다.

### 3.3 v4 sync의 `comparisonRunId`

기존 `V4MultiEventCreateScenariosIn`은 background v4의 기존 소비자를 위해
선택적 `comparisonRunId` 계약을 유지한다. Backoffice가 사용하는 sync endpoint에는
`V4MultiEventCreateScenariosSyncIn`을 추가해 공백이 아닌 255자 이하
`comparisonRunId`를 필수로 강제했다
(`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/api_schema.py:84`,
`apps/agents/scenario_group_agent/routers/versioned_scenario_generation_sync.py:131`).

### 3.4 v4 dimension Event lineage

변경 전 v4 prompt/결과는 `sourceEventIds`와 `leverRefs`를 사용하고
`sourceRefs`는 비워 두었다. Backoffice의 공통 lineage 비교는
`dimensionDefinitions[].sourceRefs[].eventId/eventTypeL2Id`를 사용하므로
v2/v3와 같은 형태로 비교할 수 없었다.

변경 후 서버가 검증된 `sourceEventIds`와 조회된 Event payload를 이용해 각 v4
dimension의 `sourceRefs`를 결정적으로 구성한다
(`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/v4_flow.py:239`).
각 ref에는 `eventId`, `eventTypeL2Id`, dimension key, source type, rationale이
포함된다. 보강된 정의를 DB와 HTTP 응답에 동일하게 저장·반환한다
(`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/v4_flow.py:210`,
`apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/v4_flow.py:223`).

API 계약 문서에도 v4 sync의 필수 run ID, 요청 Event 순서 보존,
`sourceRefs.eventId/eventTypeL2Id`를 반영했다
(`docs/architectures/scenario_group_agent_api_request_response.md:105`,
`docs/architectures/scenario_group_agent_api_request_response.md:123`).

## 4. 환경별 CORS 설정 예시

local 기본값을 그대로 쓸 때는 별도 환경변수가 필요 없다.

```dotenv
# local
CORS_ALLOWED_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
```

```dotenv
# dev/QA: JSON list
CORS_ALLOWED_ORIGINS=["https://scenario-qa.example.com","https://scenario-dev.example.com"]
```

```dotenv
# staging: comma-separated
CORS_ALLOWED_ORIGINS=https://scenario-staging.example.com,https://scenario-review.example.com
```

origin은 path를 제외한 `scheme://host[:port]` 단위로 등록한다. HTTPS frontend가
HTTP Agent를 직접 호출하는 구성은 browser mixed-content 정책 때문에 지원하지 않는다.

## 5. Backoffice 테스트용 Agent 실행

v2/v3 병렬 요청과 뒤이은 v4 요청을 처리하는 권장 명령은 다음과 같다.

```bash
poetry run dotenv -f envs/.env run --no-override -- \
  gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 3 \
  --bind 127.0.0.1:8001 \
  --timeout 1200 \
  --graceful-timeout 1200
```

로컬에 `envs/.env`를 배치한 후 실행한다. v1 create → validation → signpost →
confirmation만 순차 검증할 때는 단일 Uvicorn도 가능하다.

```bash
poetry run uvicorn main:app --host 127.0.0.1 --port 8001
```

## 6. 검증 결과

현재 checkout에는 `envs/.env`가 없으므로 검증에는 secret이 없는
`envs/.env.example`을 `dotenv --no-override`로 주입했다.

- app import
  - `python -c "import main"`
  - 통과
- Backoffice focused 계약 테스트
  - `pytest tests/automated/test_backoffice_scenario_agent_contract.py -q`
  - `4 passed`
  - CORS comma/JSON env 파싱, 허용/비허용 preflight, v2/v3 Event 순서,
    v4 sync run ID와 Event Type lineage를 검증
- 요청된 Scenario Group 회귀 테스트
  - `pytest tests/automated/test_scenario_group_agent_contract.py tests/automated/test_scenario_group_dimension_values.py tests/automated/test_scenario_group_pipeline_contract.py tests/automated/test_scenario_group_validation_review.py -q`
  - `104 passed, 3 subtests passed, 54 warnings`
  - warning은 기존 `datetime.utcnow()` deprecation warning
- v4 추가 회귀
  - `pytest tests/automated/test_v4_multi_event_model_lever_scenarios.py -q`
  - `6 passed`
- CORS 실제 preflight
  - 허용 `http://127.0.0.1:5173`: HTTP 200,
    `Access-Control-Allow-Origin: http://127.0.0.1:5173`
  - 비허용 `http://evil.example`: HTTP 400, `Access-Control-Allow-Origin` 없음
- lint/format
  - 변경 Python 파일 대상 `ruff check`: 통과
  - 변경 Python 파일 대상 `ruff format --check`: 통과

초기 `poetry install --no-root`는 실행 환경의 PyPI DNS 연결 실패
(`All attempts to connect to pypi.org failed.`)로 완료되지 않았다. 검증은 로컬에
이미 설치되어 있던 호환 Python 3.12 환경을 Poetry 실행 경로로 사용했다.
최종 테스트에는 코드 failure가 남아 있지 않다.
