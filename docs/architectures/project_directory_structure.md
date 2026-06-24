# Project Directory Structure Guide

## 문서 목적

이 문서는 프로젝트 전체 디렉터리 배치, 파일 책임, Agent 패키지 확장 기준을 빠르게 확인하기 위한 구조 가이드다.
현재 런타임 Agent는 `scenario_group_agent` 하나지만, 향후 Agent가 늘어날 때도 이 문서의 배치 기준을 따른다.

최근 디렉터리 정리 기준은 `local/plan/06_refact_directory_arch.md`의 미사용 Agent 정리 계획을 따른다.
`event_flow_agent`, `mi_agent`, `scenario_agent`, `scenario_flow_agent`, `signpost_flow_agent`는 현행 런타임 기준 Agent 구조에서 제거되었고,
MI Event/Scenario/Signpost 관련 소유권은 `scenario_group_agent` 내부로 통합되었다.

## 프로젝트 루트 배치

```text
skmip-mi-agent/
├── main.py
├── apps/
│   ├── agents/
│   │   └── scenario_group_agent/
│   ├── common/
│   └── connectors/
├── docs/
│   └── architectures/
│       ├── project_directory_structure.md
│       └── scenario_group_agent_flow_pipeline.md
└── tests/
    ├── automated/
    └── manual/
```

- `main.py`: FastAPI app 구성, schema validation, 공통 middleware/openapi 설정, `scenario_group_agent.api.router` 등록
- `apps/agents/scenario_group_agent/`: 시나리오 그룹 생성/조회/검증/Signpost 생성/확정의 기준 구현
- `tests/automated/`: pytest로 자동 실행되는 회귀/계약 테스트
- `tests/manual/`: 로컬 API 확인과 요청 바디 생성용 수동 실행 스크립트

## 현재 Agent 구조: `scenario_group_agent`

`__pycache__` 디렉터리는 생략한다.

```text
apps/agents/scenario_group_agent/
├── __init__.py
├── api.py
├── baseline_contrast.py
├── presentation.py
├── state.py
├── flows/
│   ├── __init__.py
│   ├── create_scenarios/
│   │   ├── __init__.py
│   │   ├── flow.py
│   │   ├── flow_async.py
│   │   └── nodes.py
│   ├── validate_scenarios/
│   │   ├── __init__.py
│   │   ├── flow.py
│   │   ├── flow_async.py
│   │   ├── nodes.py
│   │   └── review.py
│   ├── create_signposts/
│   │   ├── __init__.py
│   │   ├── flow.py
│   │   ├── flow_async.py
│   │   └── nodes.py
│   └── confirm_generation/
│       ├── __init__.py
│       ├── flow.py
│       └── nodes.py
├── persistence/
│   ├── __init__.py
│   ├── event/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── service.py
│   ├── scenario_group/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── service.py
│   ├── scenario/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── service.py
│   └── signpost/
│       ├── __init__.py
│       ├── models.py
│       ├── repository.py
│       └── service.py
├── prompts/
│   ├── __init__.py
│   └── builders/
│       └── __init__.py
├── schemas/
│   ├── __init__.py
│   ├── base.py
│   ├── enums.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── table.py
│   │   ├── confirm_generation.py
│   │   ├── create_scenarios.py
│   │   ├── create_signposts.py
│   │   ├── manage_scenario_groups.py
│   │   └── validate_scenarios.py
│   ├── domain/
│   │   ├── __init__.py
│   │   ├── event.py
│   │   ├── scenario_group.py
│   │   ├── scenario.py
│   │   ├── signpost.py
│   │   └── template.py
│   └── graph/
│       ├── __init__.py
│       └── generation.py
└── subgraphs/
    ├── __init__.py
    ├── scenario_generation/
    │   ├── __init__.py
    │   ├── state.py
    │   ├── nodes.py
    │   ├── generation_stages.py
    │   ├── subgraph_adapter.py
    │   └── flow.py
    └── signpost_generation/
        ├── __init__.py
        ├── state.py
        ├── nodes.py
        ├── generation_stages.py
        ├── subgraph_adapter.py
        └── flow.py
```

## 디렉터리별 역할

- `api.py`
  - FastAPI endpoint 선언, request schema 수신, background task 등록, flow 진입점 호출을 담당한다.
- `baseline_contrast.py`
  - 기준 시나리오 대비 차이점 계산/표현에 필요한 공통 helper를 제공한다.
- `presentation.py`
  - API 응답 payload, scenario table, signpost 표시값 등 외부 응답 형태를 조립/정규화한다.
- `state.py`
  - 여러 flow와 subgraph에서 공유하는 상위 `ScenarioDesignState` 타입을 정의한다.
- `flows/<api_name>/flow.py`
  - LangGraph `StateGraph` 기반 runnable을 구성한다.
  - 동기적으로 graph를 invoke하는 내부/테스트 경로에서 기준 구현으로 사용한다.
- `flows/<api_name>/flow_async.py`
  - HTTP API가 즉시 200을 반환한 뒤 FastAPI `BackgroundTasks`에서 실행할 준비/백그라운드 실행 함수를 제공한다.
  - 현재 `create_scenarios`, `validate_scenarios`, `create_signposts`가 이 계층을 사용한다.
- `flows/<api_name>/nodes.py`
  - 해당 flow 전용 node 함수 집합이다.
  - 저장/조회는 직접 SQL을 쓰지 않고 `persistence/*/service.py`를 통해 수행한다.
- `flows/validate_scenarios/review.py`
  - 검증 결과 review, 오류 메시지 구성, 차원값/시나리오 조합 검토 로직을 담당한다.
- `subgraphs/scenario_generation/`
  - 시나리오 초안 생성용 LangGraph subgraph 계층이다.
  - `generation_stages.py`는 stage 구현, LLM 호출, retry, validation, fallback을 담당한다.
  - `nodes.py`는 LangGraph node wrapper, `state.py`는 subgraph state를 담당한다.
  - `subgraph_adapter.py`는 flow state와 subgraph state의 변환, `flow.py`는 runnable graph 조립을 담당한다.
- `subgraphs/signpost_generation/`
  - 단일 scenario Signpost 생성을 담당하는 LangGraph subgraph 계층이다.
  - `generation_stages.py`는 Stage 2/4/5 구현, LLM 호출, retry, validation, fallback을 담당한다.
  - `nodes.py`는 LangGraph node wrapper, `subgraph_adapter.py`는 parent 입력과 subgraph state 변환, `flow.py`는 runnable graph 조립을 담당한다.
  - Signpost 저장/조회는 `persistence/signpost`가 기준이다.
- `persistence/<domain>/models.py`
  - SQLAlchemy ORM 모델 정의. DB 테이블명/컬럼명/FK/index 소유권의 기준이다.
- `persistence/<domain>/repository.py`
  - DB 접근 단위 쿼리 로직을 담당한다.
- `persistence/<domain>/service.py`
  - flow/node가 호출하는 비즈니스 친화 API를 제공한다.
- `prompts/builders/`
  - 프롬프트 builder 확장 위치다. 현재 핵심 생성 프롬프트는 subgraph의 `generation_stages.py`와 `prompts/` 하위 모듈 중심으로 유지된다.
- `schemas/base.py`
  - API alias 설정 등 Pydantic schema 공통 기반 타입을 정의한다.
- `schemas/enums.py`
  - scenario group, scenario, signpost stage/status/strength 등 공통 enum을 정의한다.
- `schemas/api/`
  - FastAPI request/response 전용 schema를 정의한다.
  - `schemas/api/table.py`는 외부 API table 응답/요청 shape, `schemas/api/common.py`은 API 공통 응답 wrapper를 담당한다.
- `schemas/domain/`
  - service outward boundary DTO와 domain/template payload를 정의한다.
- `schemas/graph/`
  - LangGraph state에 저장되는 generation pipeline stage/template/result DTO를 정의한다.

## API Endpoint ↔ Flow 경로 매핑

`main.py`에서 router prefix는 빈 문자열이며, 실제 ingress/API prefix가 필요한 환경은 별도 gateway 또는 `OPENAPI_PREFIX` 설정에서 처리한다.

```text
POST /scenario-groups
→ api.py
→ flows/create_scenarios/flow_async.py
→ flows/create_scenarios/nodes.py
→ subgraphs/scenario_generation/

GET /scenario-groups/{scenario_group_id}
→ api.py
→ persistence/scenario_group/service.py
→ presentation.py

DELETE /scenario-groups/{scenario_group_id}
→ api.py
→ persistence/scenario_group/service.py

DELETE /admin/scenario-groups/{scenario_group_id}/hard
→ api.py
→ persistence/scenario_group/service.py

POST /scenario-groups/{scenario_group_id}/validation
→ api.py
→ flows/validate_scenarios/flow_async.py
→ flows/validate_scenarios/nodes.py
→ flows/validate_scenarios/review.py

DELETE /scenario-groups/{scenario_group_id}/signposts
→ api.py
→ persistence/scenario_group/service.py

POST /scenario-groups/{scenario_group_id}/signposts
→ api.py
→ flows/create_signposts/flow_async.py
→ flows/create_signposts/nodes.py
→ subgraphs/signpost_generation/

POST /scenario-groups/{scenario_group_id}/confirmation
→ api.py
→ flows/confirm_generation/flow.py
→ flows/confirm_generation/nodes.py
```

## 도메인 소유권 기준

- MI Event
  - `persistence/event/models.py`, `repository.py`, `service.py`가 기준이다.
  - 과거 `event_flow_agent` 모델 import를 새 코드에 추가하지 않는다.
- Scenario Group
  - `persistence/scenario_group/*`가 시나리오 그룹 aggregate 조회/상태 변경/삭제의 기준이다.
- Scenario
  - `persistence/scenario/*`가 시나리오 저장/조회/동기화의 기준이다.
  - 과거 `scenario_agent`의 모델/서비스/repository를 새 코드에 추가하지 않는다.
- Signpost
  - `persistence/signpost/*`가 Signpost 저장/조회 기준이다.
  - LLM stage 구현은 `subgraphs/signpost_generation/generation_stages.py`, subgraph 조립은 `subgraphs/signpost_generation/flow.py`에 둔다.
  - 과거 `signpost_flow_agent` standalone runnable 또는 DB service 계층을 되살리지 않는다.

## 신규 기능 추가 기준

- API를 추가할 때는 `api.py`, `schemas/api/<new_api>.py`, `flows/<new_api>/flow.py`, `flows/<new_api>/nodes.py`를 함께 검토한다.
- API가 즉시 200을 반환하고 백그라운드에서 오래 도는 작업이면 `flows/<new_api>/flow_async.py`를 둔다.
- 생성 파이프라인 확장이 필요하면 `subgraphs/scenario_generation/` 또는 `subgraphs/signpost_generation/` 내부에서 확장한다.
- DB 저장/조회가 필요하면 먼저 `persistence/<domain>/`의 service/repository 책임을 확인하고, flow/node에서는 service를 호출한다.
- API 입출력은 `schemas/api/<new_api>.py`, API table shape은 `schemas/api/table.py`, API 공통 응답은 `schemas/api/common.py`, enum은 `schemas/enums.py`에 둔다.
- 조회/삭제/관리성 schema는 `schemas/api/manage_scenario_groups.py`에 둔다.
- service 반환 DTO는 `schemas/domain/`, graph generation stage/template/result DTO는 `schemas/graph/`에 둔다.
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
│   └── test_text_length_prompt_contract.py
└── manual/
    ├── build_request_bodies_from_group.py
    └── test_callback_api.py
```

- `tests/automated/`: CI 또는 로컬에서 `pytest tests/automated`로 돌릴 수 있는 자동 테스트
- `tests/manual/`: API 서버, callback 수신, 수동 입력 등 외부 상태가 필요한 로컬 확인 스크립트

대표 검증 명령:

```bash
pytest tests/automated
pytest tests
python -m compileall apps tests
```
