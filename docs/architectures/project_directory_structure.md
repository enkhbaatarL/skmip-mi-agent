# Project Directory Structure Guide

## 문서 목적

이 문서는 앞으로 여러 Agent가 추가되더라도 각 Agent 패키지가 동일한 디렉터리 규칙과 책임 분리를 따르도록 하는 기준 가이드다.
프로젝트 루트 배치와 Agent 내부의 공통 구조 원칙을 정의하고, 현재 런타임 Agent인 `scenario_group_agent`는 그 기준을 적용한 예시로 둔다.

## 용어

- DTO(Data Transfer Object): 계층 사이에서 주고받는 데이터 shape을 정의한 객체다.
  이 문서에서는 FastAPI request/response schema, LangGraph state/subgraph payload, persistence service 입력/반환 payload처럼 ORM 모델이 아닌 Pydantic/dataclass 타입을 통칭한다.
- ORM model: DB 테이블과 직접 매핑되는 SQLAlchemy 모델이다.
  DTO와 구분해 `apps/persistence/<domain>/models.py`에 둔다.

## 프로젝트 루트 배치

```text
skmip-mi-agent/
├── AGENTS.md
├── Dockerfile
├── Dockerfile.base
├── Dockerfile.internal
├── README.md
├── main.py
├── pyproject.toml
├── poetry.lock
├── poetry.toml
├── requirements.txt
├── skmip-mi-agent.code-workspace
├── apps/
│   ├── agents/
│   │   └── scenario_group_agent/
│   ├── common/
│   ├── connectors/
│   └── persistence/
├── devops/
│   ├── compose/
│   └── k8s/
├── docs/
│   ├── architectures/
│   │   ├── project_directory_structure.md
│   │   ├── scenario_group_agent_api_request_response.md
│   │   └── scenario_group_agent_flow_pipeline.md
│   └── guides/
│       └── launch.md
├── envs/
├── local/
├── scripts/
└── tests/
    ├── automated/
    └── manual/
```

- `main.py`: FastAPI app 구성, schema validation, 공통 middleware/openapi 설정, Agent router 등록
- `apps/agents/<agent_name>/`: Agent별 API, flow, API/graph schema, prompt, subgraph 구현 위치
- `apps/common/`: 설정, 공통 예외, logging, middleware, openapi, runtime, streaming, 공통 util/value 구현 위치
- `apps/connectors/`: callback, HTTP client, LLM client, observability, vector DB 같은 외부 시스템 adapter 구현 위치
- `apps/persistence/`: 여러 Agent가 공유하는 DB ORM, repository, 공용 persistence DTO 구현 위치
- `apps/agents/scenario_group_agent/`: 현재 운영 중인 Agent이자 새 Agent 구조의 기준 예시
- `devops/`: docker compose와 Kubernetes manifest
- `envs/`: 로컬/배포 실행 설정 파일 템플릿과 config
- `local/`: 로컬 검증, 산출물, 실험 자료. 운영 app import 경로로 사용하지 않는다.
- `scripts/`: 과거 POC, 데이터 준비, SQL, 실험용 pipeline script. 운영 runtime 소스와 분리한다.
- `tests/automated/`: pytest로 자동 실행되는 회귀/계약 테스트
- `tests/manual/`: 로컬 API 확인과 요청 바디 생성용 수동 실행 스크립트
- `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `release-artifacts/`는 실행/빌드/배포 산출물이며 구조 기준 문서에는 포함하지 않는다.

## Agent 패키지 기본 구조

새 Agent는 아래 구조를 기본으로 잡는다. 현재는 `scenario_group_agent`만 있지만, 향후 Agent가 늘어나면 `apps/agents/<agent_name>/` 아래에 같은 기준으로 배치한다.
`__pycache__` 디렉터리는 생략한다.

```text
apps/agents/<agent_name>/
├── __init__.py
├── api.py
├── presentation.py
├── persistence/
│   ├── event_service.py
│   ├── scenario_service.py
│   ├── scenario_group_service.py
│   └── signpost_service.py
├── flows/
│   ├── __init__.py
│   ├── <feature_or_domain>/
│   │   ├── __init__.py
│   │   ├── api_schema.py       # 신규 flow 전용 API request/response schema
│   │   ├── state.py            # flow 전용 LangGraph state
│   │   ├── flow.py             # graph assembly, prepare/background/API runnable entrypoint
│   │   └── nodes.py
│   └── <another_feature_or_domain>/
│       └── ...
├── prompts/
│   ├── __init__.py
│   └── <prompt_area>.py
├── tools/
│   ├── __init__.py
│   └── <llm_tool>.py
├── utils/
│   ├── __init__.py
│   └── <agent_util>.py
├── schemas/
│   ├── __init__.py
│   ├── base.py
│   ├── endpoint.py             # 기존 통합 FastAPI request/response 및 callback DTO
│   ├── state.py                # flow 공통 base state와 공통 state DTO
│   └── table.py                # 기존 endpoint/presentation/state 공유 table schema
└── subgraphs/
    ├── __init__.py
    ├── <subgraph_name>/
    │   ├── __init__.py
    │   ├── schema.py
    │   ├── nodes.py
    │   └── flow.py
    └── <another_subgraph>/
        └── ...
```

## 디렉터리별 역할

- `api.py`
  - FastAPI endpoint 선언, request schema 수신, background task 등록, flow 진입점 호출을 담당한다.
  - endpoint 내부에 도메인 로직을 길게 두지 않고 schema 변환, validation, flow/service 호출까지만 담당한다.
- `presentation.py`
  - API 응답 표현 계층이다.
  - API 응답 payload, table, 표시값 등 입출력 shape을 조립/정규화한다.
  - flow/node/subgraph에서 만든 내부 결과를 외부 callback 또는 HTTP response schema에 맞게 변환하는 책임을 둔다.
- `persistence/`
  - Agent 유스케이스 service 계층이다. 여러 repository를 조합하는 저장/조회/확정/동기화 로직을 둔다.
  - DB table 단위 쿼리는 `apps/persistence/<domain>/repository.py`에 유지한다.
- `utils/`
  - 해당 Agent 도메인에 강하게 묶인 공통 계산/정규화 helper를 둔다.
  - 여러 flow/subgraph에서 재사용하지만 `apps/common` 또는 `apps/persistence`에 둘 만큼 공통은 아닌 로직을 모은다.
  - LLM 호출, LangGraph state, runnable 조립이 필요한 수준이면 `subgraphs/`로 분리한다.
  - 예: `scenario_group_agent/utils/baseline_contrast.py`
- `tools/`
  - 현재 runtime tool 구현은 없지만, 앞으로 LLM이 직접 사용할 Agent 전용 tool을 둘 위치다.
  - 외부 API 호출, 검색, 계산 등 LLM tool/function calling 표면으로 노출할 로직을 둔다.
  - 일반 공통 helper는 `tools/`가 아니라 `utils/`에 둔다.
- `flows/<feature_or_domain>/`
  - API 동작 하나 또는 밀접한 기능 묶음 하나를 기능 단위, 도메인 단위로 나눈 flow 패키지다.
  - 예: `create_scenarios`, `validate_scenarios`, `create_signposts`, `confirm_generation`
- `flows/<feature_or_domain>/state.py`
  - 해당 flow가 실제로 읽고 쓰는 LangGraph state 필드만 정의한다.
- `flows/<feature_or_domain>/api_schema.py`
  - 신규 flow endpoint 전용 request/response schema를 둔다.
  - 여러 flow 또는 flow 없는 API에서 공유하는 DTO는 `schemas/api/`로 올린다.
- `flows/<feature_or_domain>/flow.py`
  - LangGraph `StateGraph` 기반 runnable을 구성한다.
  - background flow는 `prepare_*`, cached `get_compiled_graph()`, `run_*_background`를 함께 제공한다.
  - API payload adapter가 필요한 동기 flow는 `get_api_runnable()` 형태의 runnable pipeline을 제공한다.
- `flows/<feature_or_domain>/nodes.py`
  - 해당 flow 전용 node 함수 집합이다.
  - 저장/조회는 직접 SQL을 쓰지 않고 Agent 내부 `persistence/*_service.py`를 통해 수행한다.
- `flows/<feature_or_domain>/<helper>.py`
  - 특정 기능 단위 flow 안에서만 쓰는 review, validation, normalization helper를 둔다.
  - 여러 flow에서 재사용되거나 독립적인 graph 경계가 필요한 로직은 `subgraphs/<subgraph_name>/`로 승격한다.
- `subgraphs/<subgraph_name>/`
  - 여러 flow에서 재사용되거나 독립적인 LLM/검색/생성 pipeline으로 분리할 만한 LangGraph subgraph 계층이다.
  - `flow.py`는 graph 조립과 cached compiled subgraph 제공, `nodes.py`는 LangGraph node wrapper를 담당한다.
  - `schema.py`는 subgraph state와 stage/template/result DTO를 담당한다.
- `apps/persistence/<domain>/models.py`
  - SQLAlchemy ORM 모델 정의. DB 테이블명/컬럼명/FK/index 소유권의 기준이다.
- `apps/persistence/<domain>/schema.py`
  - 여러 Agent가 공유할 수 있는 DB domain DTO/Protocol을 둔다.
- `apps/persistence/<domain>/repository.py`
  - DB 접근 단위 쿼리 로직을 담당한다.
- `apps/persistence/schema_base.py`, `apps/persistence/enums.py`
  - 여러 persistence domain이 공유하는 DTO base class와 DB/domain enum을 둔다.
- `prompts/`
  - Agent에서 쓰는 프롬프트 템플릿과 프롬프트 builder를 API/flow 외부 모듈로 분리해 둔다.
  - LLM 호출과 retry/fallback orchestration은 flow/subgraph가 담당하고, 프롬프트 문구/구성은 `prompts/*.py`가 기준이다.
- `schemas/base.py`
  - API alias 설정 등 Pydantic schema 공통 기반 타입을 정의한다.
- `schemas/endpoint.py`
  - 현재 코드에서 사용 중인 기존 통합 FastAPI request/response schema와 callback DTO 위치다.
  - 신규 flow 전용 schema는 `flows/<flow_name>/api_schema.py`로, 공유 API schema는 `schemas/api/`로 분리한다.
- `schemas/table.py`
  - 현재 코드에서 사용 중인 기존 endpoint, presentation, flow state 공유 scenario table DTO 위치다.
- `schemas/api/`
  - 신규/이관 대상 API 공통 schema 위치다. 현재 런타임 소스는 아직 `schemas/endpoint.py`, `schemas/table.py`를 사용한다.
  - `common.py`, `table.py`, `manage_scenario_groups.py`처럼 flow 경계에 속하지 않는 공유 API schema를 둔다.

## 현재 Agent 예시: `scenario_group_agent`

`scenario_group_agent`는 위 기본 구조를 따르는 현재 런타임 Agent다.

- `flows/create_scenarios/`: scenario 생성 기능 단위 flow
  - `state.py`, `flow.py`, `nodes.py`로 구성되며 API background task 실행 경로만 둔다.
- `flows/validate_scenarios/`: scenario 검증 기능 단위 flow
  - `state.py`, `flow.py`, `nodes.py`로 구성되며 review 실행은 `subgraphs/scenario_review/`에 위임한다.
- `flows/create_signposts/`: signpost 생성 기능 단위 flow
  - `state.py`, `flow.py`, `nodes.py`로 구성되며 API background task 실행 경로만 둔다.
- `flows/confirm_generation/`: 생성 결과 확정 기능 단위 flow
  - `state.py`, `flow.py`, `nodes.py`로 구성되며 API 요청에서 직접 graph를 invoke한다.
- `apps/common/configs/`: config loader, database config, template/taxonomy registry
- `apps/common/exceptions/`, `apps/common/values/`: `MIBaseError`, `ErrorCode`, 공통 response/value 정의
- `apps/common/middleware/`, `apps/common/openapi/`, `apps/common/routing/`, `apps/common/runtime/`: FastAPI 공통 실행/문서/라우팅/runtime 지원
- `apps/connectors/callback/`: 외부 callback API client와 OAuth2 token manager
- `apps/connectors/http/`: 공유 HTTP client와 client manager
- `apps/connectors/llm/`: LLM client adapter
- `apps/connectors/vdb/`: vector DB 설정 loader, schema, client
- `apps/persistence/event/`, `apps/persistence/scenario_group/`, `apps/persistence/scenario/`, `apps/persistence/signpost/`: DB domain 단위 persistence 계층
- `prompts/scenario_generation.py`, `prompts/scenario_validation.py`, `prompts/signpost_generation.py`: 생성/검증/Signpost LLM prompt와 structured output schema
- `schemas/endpoint.py`: 현재 endpoint request/response와 callback DTO
- `schemas/table.py`: 현재 endpoint, presentation, flow state에서 공유하는 table DTO
- `apps/persistence/<domain>/schema.py`: `event`, `scenario_group`, `scenario`, `signpost` service DTO
- `subgraphs/scenario_generation/schema.py`, `subgraphs/scenario_review/schema.py`, `subgraphs/signpost_generation/schema.py`: 각 subgraph의 graph/review DTO
- `apps/persistence/scenario/baseline_contrast.py`: scenario/signpost persistence와 generation/review에서 공유하는 baseline 대비 coverage 계산 helper
- `tools/`: 현재 구현된 Agent 전용 LLM tool은 없으며, 향후 tool 구현 위치로 예약
- `subgraphs/scenario_generation/`: scenario 생성 pipeline subgraph
- `subgraphs/scenario_review/`: scenario validation review subgraph
- `subgraphs/signpost_generation/`: signpost 생성 pipeline subgraph

## API Endpoint ↔ Flow 경로 매핑

아래는 `scenario_group_agent`의 현재 매핑 예시다.
`main.py`에서 router prefix는 빈 문자열이며, 실제 ingress/API prefix가 필요한 환경은 별도 gateway 또는 `OPENAPI_PREFIX` 설정에서 처리한다.

```text
POST /scenario-groups
→ api.py
→ schemas/endpoint.py
→ flows/create_scenarios/flow.py
→ flows/create_scenarios/nodes.py
→ subgraphs/scenario_generation/

GET /scenario-groups/{scenario_group_id}
→ api.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_service.py
→ presentation.py

DELETE /scenario-groups/{scenario_group_id}
→ api.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_service.py

DELETE /admin/scenario-groups/{scenario_group_id}/hard
→ api.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_service.py

POST /scenario-groups/{scenario_group_id}/validation
→ api.py
→ schemas/endpoint.py
→ flows/validate_scenarios/flow.py
→ flows/validate_scenarios/nodes.py
→ subgraphs/scenario_review/

DELETE /scenario-groups/{scenario_group_id}/signposts
→ api.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_service.py

POST /scenario-groups/{scenario_group_id}/signposts
→ api.py
→ schemas/endpoint.py
→ flows/create_signposts/flow.py
→ flows/create_signposts/nodes.py
→ subgraphs/signpost_generation/

POST /scenario-groups/{scenario_group_id}/confirmation
→ api.py
→ schemas/endpoint.py
→ flows/confirm_generation/flow.py
→ flows/confirm_generation/nodes.py
```

`model_parameter_agent`의 현재 매핑은 아래와 같다.

```text
POST /model-parameters/scenarios/{scenario_id}/proposals
→ api.py
→ flows/propose_parameters/api_schema.py
→ flows/propose_parameters/flow.py
  - prepare_propose_parameters_callback()
  - run_propose_parameters_background()
→ flows/propose_parameters/nodes.py
→ apps/connectors/callback/callback_client.py
→ persistence/model_input_service.py
→ apps/persistence/model_input/repository.py

POST /model-parameters/scenarios/{scenario_id}/proposals/sync
→ api.py
→ flows/propose_parameters/api_schema.py
→ flows/propose_parameters/flow.py
→ flows/propose_parameters/nodes.py
→ persistence/model_input_service.py
→ apps/persistence/model_input/repository.py

POST /model-parameters/proposals/{modelParamProposalId}/confirmation
→ api.py
→ flows/confirm_parameters/api_schema.py
→ flows/confirm_parameters/flow.py
→ flows/confirm_parameters/validation.py
→ persistence/model_input_service.py
→ apps/persistence/model_input/repository.py
```

## 도메인 소유권 기준

- 새 Agent에서 공유 DB 테이블 또는 aggregate가 생기면 `apps/persistence/<domain>/models.py`, `repository.py`, `service.py`를 기준 소유 위치로 둔다.
- flow/node/subgraph는 SQLAlchemy session과 query를 직접 다루지 않고 service를 통해 저장/조회한다.
- Agent 전용 임시 저장소가 아니라면 Agent 패키지 하위에 persistence를 만들지 않는다.

`scenario_group_agent`의 현재 도메인 소유권은 아래와 같다.

- MI Event
  - `apps/persistence/event/models.py`, `repository.py`, `service.py`가 기준이다.
  - 과거 `event_flow_agent` 모델 import를 새 코드에 추가하지 않는다.
- Scenario Group
  - `apps/persistence/scenario_group/*`가 시나리오 그룹 aggregate 조회/상태 변경/삭제의 기준이다.
- Scenario
  - `apps/persistence/scenario/*`가 시나리오 저장/조회/동기화의 기준이다.
  - 과거 `scenario_agent`의 모델/서비스/repository를 새 코드에 추가하지 않는다.
- Signpost
  - `apps/persistence/signpost/*`가 Signpost 저장/조회 기준이다.
  - LLM stage 구현과 LangGraph node wrapper는 `subgraphs/signpost_generation/nodes.py`, subgraph 조립은 `subgraphs/signpost_generation/flow.py`에 둔다.
  - 과거 `signpost_flow_agent` standalone runnable 또는 DB service 계층을 되살리지 않는다.

## 신규 기능 추가 기준

- API를 추가할 때는 먼저 별도 flow가 필요한지 판단한다. flow가 있으면 `api.py`, `flows/<feature_or_domain>/api_schema.py`, `flows/<feature_or_domain>/nodes.py`와 실행 방식에 맞는 `flow.py`를 함께 검토한다.
- 별도 flow 없이 service/presentation 호출로 끝나는 API면 `api.py`, `schemas/api/<focused_name>.py`, 관련 service/presentation 책임만 검토한다.
- `flows/<feature_or_domain>/` 이름은 endpoint path를 그대로 따르기보다 기능 단위, 도메인 단위 의미가 드러나게 정한다.
- API가 즉시 200을 반환하고 백그라운드에서 오래 도는 작업이면 `flows/<feature_or_domain>/flow.py`를 둔다.
- 생성/검색/검증 파이프라인이 여러 flow에서 재사용되거나 독립적으로 테스트할 가치가 있으면 `subgraphs/<subgraph_name>/`로 분리한다.
- DB 저장/조회가 필요하면 먼저 `apps/persistence/<domain>/`의 service/repository 책임을 확인하고, flow/node에서는 service를 호출한다.
- flow endpoint 전용 API 입출력은 `flows/<flow_name>/api_schema.py`에 둔다.
- flow가 없는 조회/삭제/관리성 schema는 `schemas/api/manage_scenario_groups.py`처럼 focused file에 둔다.
- API table shape은 `schemas/api/table.py`, API 공통 request/response DTO는 `schemas/api/common.py`에 둔다.
- service 반환 DTO는 `apps/persistence/<domain>/schema.py`, graph generation stage/template/result DTO는 해당 `subgraphs/<subgraph_name>/schema.py`에 둔다.
- 응답 조립/표시용 변환은 `presentation.py`에 둔다.
- flow/subgraph에서 공유하는 상태가 늘어나면 `state.py`에 추가하고, 특정 flow에만 필요한 상태는 해당 flow 내부에 둔다.

## 테스트 배치 기준

```text
tests/
├── automated/
│   ├── test_scenario_group_agent_contract.py
│   ├── test_scenario_group_dimension_values.py
│   ├── test_scenario_group_pipeline_contract.py
│   ├── test_scenario_group_validation_review.py
│   ├── test_schema_validation.py
│   ├── test_signpost_generation_subgraph.py
│   └── test_text_length_prompt_contract.py
├── manual/
│   ├── build_request_bodies_from_group.py
│   └── test_callback_api.py
└── test_config_loader.py
```

- `tests/automated/`: CI 또는 로컬에서 `pytest tests/automated`로 돌릴 수 있는 자동 테스트
- `tests/manual/`: API 서버, callback 수신, 수동 입력 등 외부 상태가 필요한 로컬 확인 스크립트
- `tests/test_config_loader.py`: 공통 설정 loader의 루트 단위 테스트

대표 검증 명령:

```bash
pytest tests/automated
pytest tests
python -m compileall apps tests
```
