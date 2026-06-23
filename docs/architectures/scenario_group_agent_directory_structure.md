# Scenario Group Agent 디렉터리 구조 가이드

## 문서 목적

신규 에이전트 추가/확장 시, `scenario_group_agent` 패키지의 디렉터리 배치 기준을 빠르게 확인할 수 있도록 구조와 파일 역할을 정리한다.

## 프로젝트 루트 배치

```text
skmip-mi-agent/
├── main.py
├── apps/
│   └── agents/
│       ├── scenario_group_agent/
│       └── signpost_flow_agent/
└── docs/
    └── architectures/
        ├── scenario_group_agent_design.md
        └── scenario_group_agent_directory_structure.md
```

- `main.py`: router 조립만 담당
- `apps/agents/scenario_group_agent/`: 시나리오 설계 에이전트 구현

## `scenario_group_agent` 최종 구조

```text
apps/agents/scenario_group_agent/
├── __init__.py
├── api.py
├── presentation.py
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
├── subgraphs/
│   ├── __init__.py
│   └── scenario_generation/
│       ├── __init__.py
│       ├── pipeline.py
│       ├── stages.py
│       ├── state.py
│       ├── subgraph_adapter.py
│       └── subgraph_builder.py
├── prompts/
│   ├── __init__.py
│   ├── builders/
│   │   └── __init__.py
│   └── templates/
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
- `presentation.py`
  - API 응답 payload 조립/정규화 helper
- `state.py`
  - 여러 flow에서 공유하는 상위 state 타입
- `flows/<api_name>/flow.py`
  - API별 graph/runnable 구성 (생성 계열은 subgraph orchestration 호출)
- `flows/<api_name>/nodes.py`
  - 해당 flow 전용 node 집합
- `subgraphs/scenario_generation/pipeline.py`
  - 시나리오 생성 메인 파이프라인(stage 실행 순서) 정의
- `subgraphs/scenario_generation/stages.py`
  - 생성 단계별 stage 함수 집합
- `subgraphs/scenario_generation/subgraph_builder.py`
  - 생성용 subgraph를 flow에서 사용할 runnable로 조립
- `subgraphs/scenario_generation/subgraph_adapter.py`
  - flow state <-> subgraph state 변환/연결
- `persistence/<domain>/models.py`
  - ORM 모델 정의
- `persistence/<domain>/repository.py`
  - DB 접근 단위 쿼리 로직
- `persistence/<domain>/service.py`
  - 저장/조회 단위 비즈니스 친화 API
- `prompts/builders/*`
  - 템플릿 조합 및 LLM 입력 메시지 구성(확장 포인트)
- `prompts/templates/*`
  - stage별 prompt 템플릿 저장 위치(현재 미사용)
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

## 신규 에이전트 추가 체크리스트

- API를 추가할 때 `flows/<new_flow>/flow.py`, `flows/<new_flow>/nodes.py`를 같이 만든다.
- 생성 파이프라인 확장이 필요하면 `subgraphs/scenario_generation/`의 stage/adapter/builder를 우선 수정한다.
- DB 저장/조회가 필요하면 먼저 `persistence/<domain>/`를 만들고 flow에서는 service만 호출한다.
- Prompt가 필요하면 `prompts/builders/`와 `prompts/templates/`를 쌍으로 추가한다.
- API 입출력은 `schemas/<new_api>.py`로 분리한다.
- 공통 state가 늘어나면 `state.py`에 추가하고, flow 전용 state는 해당 flow 내부로 이동한다.
