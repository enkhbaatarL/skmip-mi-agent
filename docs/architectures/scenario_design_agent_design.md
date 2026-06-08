# Scenario Design Agent 설계 가이드

## 문서 목적

`scenario_agent`와 `signpost_flow_agent`를 `scenario_design_agent`로 통합할 때, 신규 에이전트/기능 추가자가 따라야 할 설계 기준을 정의한다.

이 에이전트는 아래 4개 API lifecycle을 하나의 패키지에서 제공한다.

1. Scenario group 생성 및 scenarios 생성
2. Scenarios 검증 (`is_valid`, `reason`)
3. Signposts 생성
4. Scenario group, scenarios, signposts 확정

## 설계 원칙

- `main.py`는 FastAPI app/router 조립만 담당한다.
- `scenario_design_agent/api.py`는 endpoint 계층만 담당한다.
- API마다 입력/출력/실패 조건이 다르므로 flow를 API 단위로 분리한다.
- 각 flow는 `flow.py`, `nodes.py`의 최소 구조를 유지한다.
- 공통 DB 조회/저장 로직은 반드시 `persistence/*/service.py`로 분리한다.
- DB 관련 코드는 `persistence/*`에 모으고, flow node에서 직접 SQL/ORM 세부 구현을 하지 않는다.
- 기존 `signpost_flow_agent`는 별도 top-level agent로 유지하지 않고 `scenario_design_agent`로 흡수한다.

## 계층별 책임

### `api.py`

**책임**

- HTTP path/method/response model 선언
- FastAPI dependency 처리
- request schema validation
- API별 flow 호출
- HTTP response 반환

**비책임**

- LangGraph node 조합
- LLM stage 구현
- SQLAlchemy query/insert 상세 구현
- DB payload mapping

### `flows/*/flow.py`

**책임**

- graph 구성
- runnable 생성
- lazy `get_runnable_graph()` 제공
- 간단한 input/output adapter
- flow-level runtime 준비

권장 패턴:

```python
from functools import lru_cache


def build_graph():
    ...


def build_runnable_graph():
    ...


@lru_cache(maxsize=1)
def get_runnable_graph():
    return build_runnable_graph()
```

전역 `runnable_graph = build_runnable_graph()` 패턴은 지양한다.

이유:

- FastAPI import 시점의 graph compile/runtime 초기화 방지
- settings/env 준비 전 import 문제 완화
- circular import 가능성 감소
- 테스트 import만으로 외부 리소스 초기화되는 문제 방지

### `flows/*/nodes.py`

**책임**

- state 입력
- `persistence/*/service.py` 또는 LLM stage 함수 호출
- state update dict 반환

공통 DB 조회/저장 로직을 `nodes.py`에 직접 구현하지 않는다.

### `persistence/*`

**책임**

- ORM model
- repository
- DB 조회/저장 service
- insert/update payload mapping

**비책임**

- LLM 호출
- prompt 구성
- API response 조립
- LangGraph node 구성

`persistence`를 사용하는 이유:

- DB 영속성 전용 계층임을 명확히 표현
- `domains`보다 범위가 좁아 LLM/business policy 혼입을 방지
- `persistent`는 형용사이므로 디렉터리명으로 부적합

### `prompts/*`

- prompt yaml template 관리
- prompt builder 관리
- LLM 호출용 message 조립

### `schemas/*`

- FastAPI request/response schema 정의
- 초기에 flow 내부 stage schema도 함께 둘 수 있음
- 규모가 커지면 `flows/*/schemas.py`로 분리

### `state.py`

- 여러 flow에서 공유하는 top-level/common state 타입 정의
- flow별 state가 커지면 `flows/*/state.py` 추가

## API별 Flow 설계

### 1) Create Scenario Group & Create Scenarios

- Endpoint: `POST /scenario-design/scenario-groups`
- Flow: `flows/create_scenarios/flow.py`
- Node 순서:
  - `load_event`
  - `check_existing_scenario_group`
  - `run_scenario_generation`
  - `save_scenario_group`
  - `save_scenarios`
  - `build_response`
- 주요 응답 필드:
  - `mi_event_id`
  - `scenario_group_id`
  - `scenario_count`
  - `saved_scenario_ids`
  - `scenario_result`
  - `status`
  - `message`

운영 응답 크기 부담이 있으면 요청 필드 `include_details: bool = false`를 두고, `true`일 때만 `scenario_result`를 포함한다.

### 2) Validate Scenarios

- Endpoint: `POST /scenario-design/scenario-groups/{scenario_group_id}/validation`
- Flow: `flows/validate_scenarios/flow.py`
- Node 순서:
  - `load_scenario_group`
  - `load_scenarios`
  - `validate_scenarios`
  - `save_validation_result`
  - `build_response`
- 주요 응답 필드:
  - `scenario_group_id`
  - `is_valid`
  - `reason`
  - `validation_result`
  - `status`
  - `message`

### 3) Create Signposts

- Endpoint: `POST /scenario-design/scenario-groups/{scenario_group_id}/signposts`
- Flow: `flows/create_signposts/flow.py`
- Node 순서:
  - `load_scenario_group`
  - `load_scenarios`
  - `check_existing_signposts`
  - `run_signpost_generation`
  - `save_signposts`
  - `build_response`
- 주요 응답 필드:
  - `scenario_group_id`
  - `signpost_count`
  - `saved_signpost_ids`
  - `signpost_result`
  - `status`
  - `message`

### 4) Confirm Generation

- Endpoint: `POST /scenario-design/scenario-groups/{scenario_group_id}/confirmation`
- Flow: `flows/confirm_generation/flow.py`
- Node 순서:
  - `load_scenario_group`
  - `load_scenarios`
  - `load_signposts`
  - `confirm_outputs`
  - `build_response`
- 주요 응답 필드:
  - `scenario_group_id`
  - `confirmed`
  - `confirmed_at`
  - `scenario_count`
  - `signpost_count`
  - `status`
  - `message`

## Naming 규칙

- Agent package: `scenario_design_agent`
- FastAPI router 파일: `api.py`
- API별 flow 디렉터리: 동사구 사용
  - `create_scenarios`
  - `validate_scenarios`
  - `create_signposts`
  - `confirm_generation`
- Flow 구성 파일:
  - `flow.py`
  - `nodes.py`
- DB 계층: `persistence`
- DB 하위 package: 명사 사용
  - `event`
  - `scenario_group`
  - `scenario`
  - `signpost`

## 설계 결정

### API별 flow 분리

4개 API는 lifecycle은 이어지지만 입력/출력/실패 조건이 다르다.  
따라서 하나의 거대 graph에서 시작 node만 바꾸는 방식 대신 API별 `flows/*/flow.py`를 분리한다.

### `subgraphs` 미도입

현재 단계에서는 구조 단순성을 우선한다.  
필요해지면 `flows/*/stages.py` 또는 `flows/*/stages/`를 추가한다.

### `domains` 대신 `persistence` 사용

이 계층은 DB 관련 파일만 유지하므로, 도메인 전체를 의미하는 `domains`보다 `persistence`가 정확하다.

### `components` 미도입

DB 공통 로직은 `persistence/*/service.py`, flow node는 `flows/*/nodes.py`로 명확히 구분한다.

### 기존 agent 점진 이관

초기에는 `scenario_agent`, `signpost_flow_agent`를 즉시 삭제하지 않는다.  
`scenario_design_agent`가 동일 결과 생성/저장을 검증한 뒤 deprecated 처리한다.
