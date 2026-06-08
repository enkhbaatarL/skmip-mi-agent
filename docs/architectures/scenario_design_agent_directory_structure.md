# Scenario Design Agent 디렉터리 구조 가이드

## 문서 목적

신규 에이전트 추가/확장 시, `scenario_design_agent` 패키지의 디렉터리 배치 기준을 빠르게 확인할 수 있도록 구조와 파일 역할을 정리한다.

## 프로젝트 루트 배치

```text
skmip-mi-agent/
├── main.py
├── apps/
│   └── agents/
│       ├── mi_agent/
│       └── scenario_design_agent/
└── docs/
    └── architectures/
        ├── scenario_design_agent_design.md
        └── scenario_design_agent_directory_structure.md
```

- `main.py`: router 조립만 담당
- `apps/agents/scenario_design_agent/`: 시나리오 설계 에이전트 구현

## `scenario_design_agent` 최종 구조

```text
apps/agents/scenario_design_agent/
├── __init__.py
├── api.py
├── state.py
├── flows/
│   ├── __init__.py
│   ├── create_scenarios/
│   │   ├── __init__.py
│   │   ├── flow.py
│   │   └── nodes.py
│   ├── validate_scenarios/
│   │   ├── __init__.py
│   │   ├── flow.py
│   │   └── nodes.py
│   ├── create_signposts/
│   │   ├── __init__.py
│   │   ├── flow.py
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
│   ├── builders/
│   │   ├── __init__.py
│   │   ├── scenario.py
│   │   ├── scenario_validation.py
│   │   └── signpost.py
│   └── templates/
│       ├── scenario_stage2.yaml
│       ├── scenario_stage3.yaml
│       ├── scenario_stage4.yaml
│       ├── scenario_stage5.yaml
│       ├── scenario_validation.yaml
│       ├── signpost_stage2.yaml
│       ├── signpost_stage3.yaml
│       ├── signpost_stage4.yaml
│       └── signpost_stage5.yaml
└── schemas/
    ├── __init__.py
    ├── common.py
    ├── create_scenarios.py
    ├── validate_scenarios.py
    ├── create_signposts.py
    └── confirm_generation.py
```

## 디렉터리별 역할

- `api.py`
  - API endpoint 선언 및 flow 호출 진입점
- `state.py`
  - 여러 flow에서 공유하는 상위 state 타입
- `flows/<api_name>/flow.py`
  - API별 graph/runnable 구성
- `flows/<api_name>/nodes.py`
  - 해당 flow 전용 node 집합
- `persistence/<domain>/models.py`
  - ORM 모델 정의
- `persistence/<domain>/repository.py`
  - DB 접근 단위 쿼리 로직
- `persistence/<domain>/service.py`
  - 저장/조회 단위 비즈니스 친화 API
- `prompts/builders/*`
  - 템플릿 조합 및 LLM 입력 메시지 구성
- `prompts/templates/*`
  - stage별 prompt YAML 템플릿
- `schemas/*`
  - API request/response Pydantic schema

## API Endpoint ↔ Flow 경로 매핑

```text
POST /scenario-design/scenario-groups
→ flows/create_scenarios/flow.py

POST /scenario-design/scenario-groups/{scenario_group_id}/validation
→ flows/validate_scenarios/flow.py

POST /scenario-design/scenario-groups/{scenario_group_id}/signposts
→ flows/create_signposts/flow.py

POST /scenario-design/scenario-groups/{scenario_group_id}/confirmation
→ flows/confirm_generation/flow.py
```

## 기존 구조에서 이관 매핑

현재 구조:

```text
apps/agents/scenario_agent/
├── flows/
├── nodes/
├── services/
├── repositories/
├── models/
├── schemas/
└── state/

apps/agents/signpost_flow_agent/
├── flows/
├── nodes/
├── services/
├── repositories/
├── models/
├── schemas/
└── state/
```

목표 구조:

```text
apps/agents/scenario_design_agent/
├── api.py
├── state.py
├── flows/
├── persistence/
├── prompts/
└── schemas/
```

세부 매핑:

```text
scenario_agent/services/scenario_pipeline.py
→ scenario_design_agent/flows/create_scenarios/nodes.py
  또는 scenario_design_agent/flows/create_scenarios/flow.py

scenario_agent/services/scenario_generation_service.py
→ scenario_design_agent/flows/create_scenarios/nodes.py

scenario_agent/services/scenario_db_service.py
→ scenario_design_agent/persistence/scenario/service.py
  또는 scenario_design_agent/persistence/scenario_group/service.py

scenario_agent/repositories/sync_scenario_repository.py
→ scenario_design_agent/persistence/scenario/repository.py

scenario_agent/models/scenario_models_orm.py
→ scenario_design_agent/persistence/scenario/models.py

signpost_flow_agent/services/signpost_pipeline.py
→ scenario_design_agent/flows/create_signposts/nodes.py
  또는 scenario_design_agent/flows/create_signposts/flow.py

signpost_flow_agent/services/signpost_db_service.py
→ scenario_design_agent/persistence/signpost/service.py

signpost_flow_agent/repositories/sync_signpost_repository.py
→ scenario_design_agent/persistence/signpost/repository.py

signpost_flow_agent/models/signpost_models_orm.py
→ scenario_design_agent/persistence/signpost/models.py
```

## 신규 에이전트 추가 체크리스트

- API를 추가할 때 `flows/<new_flow>/flow.py`, `flows/<new_flow>/nodes.py`를 같이 만든다.
- DB 저장/조회가 필요하면 먼저 `persistence/<domain>/`를 만들고 flow에서는 service만 호출한다.
- Prompt가 필요하면 `prompts/builders/`와 `prompts/templates/`를 쌍으로 추가한다.
- API 입출력은 `schemas/<new_api>.py`로 분리한다.
- 공통 state가 늘어나면 `state.py`에 추가하고, flow 전용 state는 해당 flow 내부로 이동한다.
