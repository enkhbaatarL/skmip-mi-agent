# Model Parameter Agent Structure Improvement Plan

## 문서 목적

이 문서는 `model_parameter_agent`의 디렉터리/파일 구조를 `project_directory_structure.md`와
현재 기준 예시인 `scenario_group_agent` 구조에 맞추기 위한 개선 계획서다.

목표는 로직 변경이 아니라 다음 항목을 한 번에 정리하기 위한 사전 합의다.

- schema 소유 경계 세분화
- Agent-local persistence service와 공용 persistence domain 경계 명확화
- flow, node, prompt, presentation, utility 책임 분리
- 파일 이동/분리 시 변경 범위와 테스트 영향 사전 정리

## 기준 원칙

- `api.py`는 FastAPI endpoint, request 수신, background task 등록, flow/service 호출까지만 담당한다.
- `presentation.py`는 API 응답, callback payload, 외부 표시용 payload 조립을 담당한다.
- `flows/<flow_name>/flow.py`는 graph/runnable 조립, prepare/background/API runnable entrypoint를 담당한다.
- `flows/<flow_name>/nodes.py`는 flow node wrapper와 flow 전용 node 함수를 담당한다.
- `flows/<flow_name>/api_schema.py`는 해당 flow endpoint 전용 API request/response schema만 둔다.
- `flows/<flow_name>/state.py`는 해당 flow가 읽고 쓰는 LangGraph state만 둔다.
- `prompts/`는 LLM prompt template과 prompt builder를 둔다.
- `utils/`는 Agent 도메인에 묶인 계산/정규화 helper를 둔다.
- `subgraphs/`는 여러 flow에서 재사용되거나 독립적으로 테스트할 가치가 있는 LLM/검색/생성 pipeline을 둔다.
- `apps/agents/<agent>/persistence/*_service.py`는 Agent 유스케이스 service 계층이다.
- `apps/persistence/<domain>/models.py`는 해당 DB domain의 ORM model만 둔다.
- `apps/persistence/<domain>/repository.py`는 해당 DB domain의 query만 둔다.
- `apps/persistence/<domain>/schema.py`는 service/repository 경계에서 쓰는 persistence DTO를 둔다.
- flow/node는 SQLAlchemy session/query를 직접 다루지 않고 Agent service를 호출한다.

## Schema 구조 개선

### 현재 상태

`scenario_group_agent`도 아직 `schemas/endpoint.py`, `schemas/table.py`에 통합 schema가 남아 있다.
따라서 현재 구조는 완성형이라기보다 운영 중인 기준 예시와 일부 레거시 통합 schema가 공존하는 상태로 본다.

`model_parameter_agent`는 특히 `flows/propose_parameters/api_schema.py`에 API DTO, LLM structured output DTO,
내부 stage DTO가 함께 들어 있어 역할 경계가 흐리다.

### 개선 방향

schema는 하나의 `schemas/` 디렉터리에 모두 모으는 대신 소유 경계별로 둔다.

```text
flows/<flow_name>/api_schema.py
```

- 해당 flow endpoint 전용 request/response DTO
- 예: proposal 접수 응답, sync proposal 응답, callback payload

```text
flows/<flow_name>/state.py
```

- 해당 flow 전용 LangGraph state

```text
schemas/api/<focused_name>.py
```

- 여러 endpoint 또는 여러 flow에서 공유하는 외부 API DTO
- 예: `ProposalParameter`, `ModelParameterTarget`

```text
schemas/<focused_name>.py
```

- Agent 내부 graph/LLM/stage DTO
- 여러 flow에서 공유되거나 flow 하위 파일명을 가이드에 맞춰 단순하게 유지해야 하는 schema
- subgraph는 이번 개선 범위에 포함하지 않는다.

```text
flows/<flow_name>/<helper>.py
```

- 특정 flow 안에서만 쓰는 prompt payload builder, validation, normalization helper
- flow 하위 파일은 `api_schema.py`, `state.py`, `flow.py`, `nodes.py`와 가이드에서 허용한 helper 파일 중심으로 둔다.

```text
apps/persistence/<domain>/schema.py
```

- DB domain service/repository 경계 DTO
- DB row payload, aggregate payload, persistence command/result DTO

### 권장 목표

```text
apps/agents/model_parameter_agent/
├── schemas/
│   ├── model_parameter_proposal.py
│   └── api/
│       ├── __init__.py
│       └── parameters.py
├── flows/
│   ├── propose_parameters/
│   │   ├── api_schema.py
│   │   └── state.py
│   └── confirm_parameters/
│       ├── api_schema.py
│       └── state.py
apps/persistence/model_parameter/
└── schema.py
```

### 파일별 개선안

| 현재 파일 | 현재 역할 | 개선 필요 사항 | 목표 위치 |
| --- | --- | --- | --- |
| `flows/propose_parameters/api_schema.py` | API DTO, LLM DTO, stage DTO 혼재 | API 입출력만 남긴다. | 유지 |
| `schemas/api/parameters.py` | 외부 API 공유 DTO | `ProposalParameter`, `ModelParameterTarget` 유지 | 유지 |
| `flows/propose_parameters/state.py` | proposal flow state | flow 전용 state로 유지 | 유지 |
| `flows/confirm_parameters/api_schema.py` | confirm API DTO | 유지 | 유지 |
| 없음 | confirm flow state | `ConfirmParametersState` 추가 검토 | `flows/confirm_parameters/state.py` |
| 없음 | LLM structured output/stage DTO | LLM candidate/slot/value schema 분리 | `schemas/model_parameter_proposal.py` |
| 없음 | persistence DTO | model parameter DB domain DTO 추가 | `apps/persistence/model_parameter/schema.py` |

## Persistence 구조 개선

### 현재 구조

```text
apps/agents/model_parameter_agent/persistence/
└── model_input_service.py

apps/persistence/model_input/
├── models.py
└── repository.py
```

현재 `apps/persistence/model_input/repository.py`는 model parameter 관련 3개 테이블뿐 아니라
scenario, scenario_group, event, dimension template 조회까지 함께 수행한다.

이 구조는 `repository.py`가 특정 DB domain query 계층을 넘어 scenario context 조립 책임까지 갖게 하므로
도메인 경계가 흐려진다.

### 개선 방향

공용 persistence에는 model parameter 관련 3개 테이블의 model/repository/schema만 둔다.

대상 테이블:

- `tmm_mi_model_param_m`
- `tmm_mi_model_param_dimension_map`
- `tmm_mi_model_param_proposal_m`

Agent service는 각 domain repository를 조합해 유스케이스 payload를 만든다.

```text
ModelParameterService.load_context(scenario_id)
→ ScenarioRepository로 scenario 조회
→ ScenarioGroupRepository로 scenario group 조회
→ EventRepository로 event 조회
→ ScenarioRepository의 public 메서드로 dimension template 조회
→ ModelParameterRepository로 parameter/mapping resource 조회
→ model_parameter_agent용 context payload 조립
```

### 권장 목표

디렉터리명은 통일성을 위해 `model_parameter`를 우선 후보로 둔다.
기존 이름 유지가 더 안전하다고 판단하면 `model_input` 이름을 유지하되 역할만 정리한다.

```text
apps/persistence/model_parameter/
├── __init__.py
├── models.py
├── repository.py
└── schema.py

apps/agents/model_parameter_agent/persistence/
├── __init__.py
└── model_parameter_service.py
```

### 공용 repository 책임

`ModelParameterRepository`는 아래 역할만 담당한다.

- model parameter definition 조회
- dimension-to-parameter mapping rule 조회
- proposal row 생성
- proposal row 조회
- proposal 완료 처리
- proposal 실패 처리
- proposal 확정 처리
- callback status 갱신

`ModelParameterRepository`에서 제거할 책임:

- scenario 조회
- scenario group 조회
- event 조회
- event type 조회
- dimension template 조회
- 여러 domain 데이터를 합친 scenario context 조립

### 공용 persistence schema 책임

`apps/persistence/model_parameter/schema.py`에는 model parameter 관련 3개 테이블과 직접 관련된 DTO만 둔다.

후보 DTO:

- `ModelParameterDefinitionPayload`
- `ModelParameterMappingRulePayload`
- `ModelParameterProposalPayload`

scenario, event, scenario_group, dimension template, parameter mapping resource를 합친 Agent context DTO는
공용 persistence schema에 두지 않는다. 기존 `scenario_group_agent` 패턴처럼 Agent service 안에서
TypedDict 또는 기존 dict shape으로 관리한다.

후보 위치:

```text
apps/agents/model_parameter_agent/persistence/model_parameter_service.py
```

후보 타입:

```python
class ModelParameterScenarioContext(TypedDict):
    scenario: dict[str, Any]
    scenario_group: dict[str, Any]
    event: dict[str, Any]
    event_type: dict[str, Any]
    dimension_template: list[dict[str, Any]]
    parameter_mapping_resources: dict[str, list[dict[str, Any]]]
```

### Agent service 책임

`ModelParameterService`는 아래 역할을 담당한다.

- scenario/event/scenario_group/model_parameter repository 조합
- 필요한 조회 메서드가 기존 repository에 없으면 해당 domain repository에 public 메서드를 추가한다.
- proposal 생성/완료/실패/확정 유스케이스 orchestration
- transaction 경계 관리
- Agent flow가 필요로 하는 context payload 조립
- API/flow 정책성 validation

### 파일별 개선안

| 현재 파일 | 현재 역할 | 개선 필요 사항 | 목표 위치 |
| --- | --- | --- | --- |
| `apps/persistence/model_input/models.py` | model parameter 3개 테이블 ORM | 이름을 `model_parameter`로 바꿀지 결정. ORM은 3개 테이블만 소유 | `apps/persistence/model_parameter/models.py` |
| `apps/persistence/model_input/repository.py` | model parameter query + scenario/event context query | scenario/event/group/template 조회 제거. model parameter 3개 테이블 query만 유지 | `apps/persistence/model_parameter/repository.py` |
| 없음 | model parameter persistence DTO | repository/service 경계 DTO 추가 | `apps/persistence/model_parameter/schema.py` |
| `apps/agents/model_parameter_agent/persistence/model_input_service.py` | Agent 유스케이스 service | repository 조합 책임 명확화. 파일명 변경 검토 | `apps/agents/model_parameter_agent/persistence/model_parameter_service.py` |
| `apps/agents/model_parameter_agent/persistence/model_input/` | 빈 디렉터리 | 제거 | 제거 |

## Model Parameter Agent 전체 목표 구조 초안

```text
apps/agents/model_parameter_agent/
├── __init__.py
├── api.py
├── presentation.py
├── persistence/
│   ├── __init__.py
│   └── model_parameter_service.py
├── flows/
│   ├── __init__.py
│   ├── propose_parameters/
│   │   ├── __init__.py
│   │   ├── api_schema.py
│   │   ├── state.py
│   │   ├── flow.py
│   │   ├── nodes.py
│   │   └── validation.py
│   └── confirm_parameters/
│       ├── __init__.py
│       ├── api_schema.py
│       ├── state.py
│       ├── flow.py
│       ├── nodes.py
│       └── validation.py
├── prompts/
│   ├── __init__.py
│   └── model_parameter_proposal.py
├── schemas/
│   ├── __init__.py
│   ├── model_parameter_proposal.py
│   └── api/
│       ├── __init__.py
│       └── parameters.py
├── tools/
│   └── __init__.py
└── utils/
    ├── __init__.py
    ├── basecase.py
    └── parameter_mapping.py
```

```text
apps/persistence/model_parameter/
├── __init__.py
├── models.py
├── repository.py
└── schema.py
```

## 확정 변경안 기준 디렉터리/파일 구조

아래 구조는 인터뷰 결정 Q1-Q16을 모두 반영한 최종 목표 구조다.
`__pycache__`, `.DS_Store` 같은 실행/로컬 산출물은 제외한다.

### Agent runtime package

```text
apps/agents/model_parameter_agent/
├── __init__.py
├── api.py
├── presentation.py
├── persistence/
│   ├── __init__.py
│   └── model_parameter_service.py
├── flows/
│   ├── __init__.py
│   ├── propose_parameters/
│   │   ├── __init__.py
│   │   ├── api_schema.py
│   │   ├── state.py
│   │   ├── flow.py
│   │   ├── nodes.py
│   │   └── validation.py
│   └── confirm_parameters/
│       ├── __init__.py
│       ├── api_schema.py
│       ├── state.py
│       ├── flow.py
│       ├── nodes.py
│       └── validation.py
├── prompts/
│   ├── __init__.py
│   └── model_parameter_proposal.py
├── schemas/
│   ├── __init__.py
│   ├── model_parameter_proposal.py
│   └── api/
│       ├── __init__.py
│       └── parameters.py
├── tools/
│   └── __init__.py
├── utils/
│   ├── __init__.py
│   ├── basecase.py
│   └── parameter_mapping.py
├── docs/
│   ├── BASECASE_LOAD_RESULTS.md
│   ├── MODEL_PARAMETER_AGENT_API_SPEC.md
│   ├── MODEL_PARAMETER_AGENT_DB_DESIGN.md
│   ├── MODEL_PARAMETER_AGENT_DB_SEED_20260701.sql
│   ├── MODEL_PARAMETER_AGENT_FLOW.md
│   ├── MODEL_PARAMETER_AGENT_IMPROVEMENT_PROPOSAL_20260701.md
│   ├── PARAMETER_EXCEL_MAPPING.md
│   ├── PARAMETER_EXCEL_MAPPING_VALIDATION.md
│   ├── basecase_load_values_full_20260630.csv
│   └── model_input_table_ranges_20260630.md
└── resources/
    ├── 260625_시나리오가정_MI수급모델_input_매핑_vfShare_agent.xlsx
    └── LNG수급모델_운영버전_입력시트_Basecase_20260610/
        ├── 복호화_(Base) Demand Model_Input.xlsm
        ├── 복호화_(Base) Supply Model_Input.xlsm
        └── 복호화_(Base) Trade Model_Input.xlsm
```

Agent package에서 제거 또는 이동할 항목:

```text
apps/agents/model_parameter_agent/mapping.py
apps/agents/model_parameter_agent/persistence/model_input_service.py
apps/agents/model_parameter_agent/persistence/model_input/
apps/agents/model_parameter_agent/scripts/
apps/agents/model_parameter_agent/reports/
```

이동 후 위치:

```text
tests/manual/model_parameter_agent/
├── benchmark_cache_key_effect.py
├── benchmark_llm_call_variants.py
├── benchmark_reasoning_quality.py
├── compare_llm_reasoning_outputs.py
├── evaluate_event_type_proposals.py
└── evaluate_proposals.py

tests/reports/model_parameter_agent/
└── *.md
```

### 공용 persistence package

```text
apps/persistence/model_parameter/
├── __init__.py
├── models.py
├── repository.py
└── schema.py
```

제거할 기존 공용 persistence 경로:

```text
apps/persistence/model_input/
```

`apps/persistence/model_parameter/models.py` 소유 테이블:

```text
tmm_mi_model_param_m
tmm_mi_model_param_dimension_map
tmm_mi_model_param_proposal_m
```

`apps/persistence/model_parameter/repository.py` 책임:

- model parameter definition 조회
- dimension-to-parameter mapping rule 조회
- proposal row 생성/조회
- proposal 완료/실패/확정 처리
- callback status 갱신

`apps/persistence/model_parameter/repository.py`에서 제외할 책임:

- scenario 조회
- scenario group 조회
- event 조회
- event type 조회
- dimension template 조회
- Agent context 조립

### 연관 domain repository 보강

필요한 public 조회 메서드가 없으면 기존 domain repository에 추가한다.
예상 후보:

```text
apps/persistence/scenario/repository.py
```

- dimension template 조회용 public 메서드 추가

```text
apps/persistence/scenario_group/repository.py
```

- model parameter service에서 필요한 scenario group 단건 조회 public 메서드가 부족하면 추가

```text
apps/persistence/event/repository.py
```

- 기존 `fetch_event_by_id()`를 재사용한다.

### 테스트/문서 구조

자동화 테스트 파일은 분할하지 않는다.

```text
tests/automated/test_model_parameter_agent_contract.py
```

수동 테스트/검증 스크립트와 테스트 결과 리포트는 아래 위치로 이동한다.

```text
tests/manual/model_parameter_agent/
tests/reports/model_parameter_agent/
```

구조 변경과 직접 관련된 기존 문서는 최소 업데이트한다.

```text
apps/agents/model_parameter_agent/docs/MODEL_PARAMETER_AGENT_FLOW.md
apps/agents/model_parameter_agent/docs/MODEL_PARAMETER_AGENT_API_SPEC.md
apps/agents/model_parameter_agent/docs/MODEL_PARAMETER_AGENT_DB_DESIGN.md
```

### 파일별 책임 요약

| 파일 | 책임 |
| --- | --- |
| `api.py` | FastAPI endpoint, request 수신, background task 등록, flow entrypoint 호출 |
| `presentation.py` | proposal response, callback payload, parameter summary, 외부 응답용 slot/value normalization |
| `persistence/model_parameter_service.py` | Agent 유스케이스 service, repository 조합, transaction, context 조립, proposal 상태 변경 |
| `flows/propose_parameters/api_schema.py` | propose/sync/callback API request/response DTO |
| `flows/propose_parameters/state.py` | propose flow LangGraph state |
| `flows/propose_parameters/flow.py` | propose graph/runnable 조립, route, prepare/background/API entrypoint |
| `flows/propose_parameters/nodes.py` | propose flow node wrapper와 node 실행 함수 |
| `flows/propose_parameters/validation.py` | propose flow 전용 검증, LLM response 보정/fallback 중 validation 성격 helper |
| `flows/confirm_parameters/api_schema.py` | confirm API request/response DTO |
| `flows/confirm_parameters/state.py` | confirm flow state |
| `flows/confirm_parameters/flow.py` | confirm runnable 조립, state adapter, output adapter |
| `flows/confirm_parameters/nodes.py` | confirm validation/service 호출/상태 update node |
| `flows/confirm_parameters/validation.py` | confirmation parameter payload validation |
| `prompts/model_parameter_proposal.py` | model parameter proposal LLM system prompt와 prompt builder |
| `schemas/api/parameters.py` | proposal/confirmation이 공유하는 외부 API DTO |
| `schemas/model_parameter_proposal.py` | LLM/internal stage schema |
| `utils/parameter_mapping.py` | mapping rule 처리, knowledge base 구성, candidate matching |
| `utils/basecase.py` | Basecase workbook discovery/profile/record 추출 |
| `apps/persistence/model_parameter/models.py` | model parameter 3개 테이블 ORM |
| `apps/persistence/model_parameter/repository.py` | model parameter 3개 테이블 query |
| `apps/persistence/model_parameter/schema.py` | model parameter 3개 테이블 persistence DTO |

## 디렉터리별 개선 사항

### `api.py`

현재:

- endpoint 등록과 flow 호출을 담당한다.
- 구조 기준에 크게 어긋나지는 않는다.

개선:

- import 대상 이름 변경 반영
  - `model_input_service` → 직접 import하지 않는 구조 유지
  - flow entrypoint 이름 정리
- endpoint 함수 내부에서는 schema 변환과 flow/background task 호출만 유지한다.

### `presentation.py`

현재:

- 파일이 없다.
- proposal response 조립과 callback payload 조립이 `flows/propose_parameters/flow.py`에 있다.

개선:

- `ProposalParameter` 조립
- `ProposeParametersData` 조립
- callback success/error payload 조립
- parameter summary 조립
- slot/value output normalization helper 중 외부 응답 payload 조립에 필요한 함수 이동

목표:

- `flow.py`에서 응답 조립 helper를 제거하고 `presentation.py` 호출로 대체한다.
- DB 저장/완료/실패 처리는 `ModelParameterService`에 둔다.
- graph route, state adapter, runnable assembly는 `flow.py`에 둔다.

### `flows/propose_parameters/flow.py`

현재:

- graph 조립
- route function
- state adapter
- proposal response 변환
- DB 저장
- background callback 처리
- callback payload 조립
- mapping candidate 사전 검증

개선:

- graph/runnable 조립과 prepare/background entrypoint 중심으로 축소한다.
- 응답 조립은 `presentation.py`로 이동한다.
- DB 저장/상태 변경은 `ModelParameterService`로 위임한다.
- mapping candidate 사전 검증은 service 또는 flow validation helper로 분리한다.
- `flow.py`에는 핵심 실행 흐름만 남기고 세부 변환/검증/helper는 별도 파일로 분리한다.

### `flows/propose_parameters/nodes.py`

현재:

- node 함수
- 긴 system prompt
- prompt packet builder
- LLM 호출 wrapper
- sanitizer
- fallback response
- period parsing
- basecase record filtering

개선:

- node wrapper는 유지한다.
- prompt 문구는 `prompts/model_parameter_proposal.py`로 이동한다.
- prompt packet builder, sanitizer, fallback은 별도 파일을 과도하게 만들지 않고 `nodes.py` private helper 또는 `validation.py`에 둔다.
- basecase/mapping helper는 `utils/`로 이동한다.

### `flows/propose_parameters/api_schema.py`

현재:

- API DTO와 LLM 내부 DTO가 섞여 있다.

개선:

- API request/response/callback DTO만 남긴다.
- LLM structured output DTO는 `schemas/model_parameter_proposal.py`로 이동한다.
- 공유 API DTO는 `schemas/api/parameters.py`를 사용한다.

### `flows/propose_parameters/state.py`

현재:

- proposal flow state를 정의한다.

개선:

- flow state로 유지한다.
- 이번 개선에서는 subgraph를 만들지 않으므로 proposal flow state로 유지한다.

### `flows/confirm_parameters/flow.py`

현재:

- `RunnableLambda(confirm_parameters)` 하나로 validation, service 호출, response 조립을 수행한다.

개선:

- `state.py`, `nodes.py` 추가를 검토한다.
- `flow.py`는 `to_state`, runnable assembly, `to_output` 중심으로 정리한다.
- confirmation 실행 로직은 `nodes.py`로 이동한다.
- 현재 `flow.py`에 있는 validation/service 호출/상태 update 성격의 함수는 node 역할이면 `nodes.py`로 이관한다.

### `flows/confirm_parameters/validation.py`

현재:

- confirm flow 전용 parameter payload validation을 담당한다.

개선:

- 현재 위치 유지 가능.
- model parameter definition DTO가 생기면 `dict[str, Any]` 대신 persistence schema 타입을 사용할지 검토한다.

### `mapping.py`

현재:

- Agent root에 있으며 mapping resource loading, DB resource conversion, Excel parsing, basecase profiling,
  candidate matching, normalization helper가 모두 섞여 있다.

개선:

- `utils/parameter_mapping.py`
- `utils/basecase.py`

두 파일 정도로만 분리한다. 이름/키 정규화처럼 작은 helper는 우선 관련 파일 내부 private helper로 둔다.
추가 분리는 파일 책임이 다시 커질 때 후속으로 검토한다.

### `schemas/api/parameters.py`

현재:

- `ModelParameterTarget`, `ProposalParameter`를 둔다.

개선:

- 외부 API 공유 DTO로 유지한다.
- persistence DTO와 혼동되지 않도록 DB row shape은 여기 두지 않는다.

### `apps/persistence/model_input`

현재:

- model parameter 관련 3개 테이블의 models/repository가 있다.
- repository가 scenario/event/scenario_group 조회까지 수행한다.
- `schema.py`가 없다.

개선:

- 디렉터리명을 `model_parameter`로 변경할지 결정한다.
- repository는 model parameter 관련 3개 테이블 query만 갖게 한다.
- `schema.py`를 추가한다.

### `docs`, `resources`, `reports`, `scripts`

현재:

- `apps/agents/model_parameter_agent/docs/`
- `apps/agents/model_parameter_agent/resources/`
- `apps/agents/model_parameter_agent/reports/`
- `apps/agents/model_parameter_agent/scripts/`

개선:

- `docs/`는 Agent package 내부에 유지한다.
- `reports/`는 테스트 결과 산출물이므로 `tests/reports/model_parameter_agent/`로 이동한다.
- `scripts/`는 테스트/검증 목적이면 `tests/manual/model_parameter_agent/`로 이동한다.
- `scripts/` 중 POC, 데이터 준비, SQL, 실험용 pipeline 성격이면 root `scripts/model_parameter_agent/` 이동을 검토한다.
- `resources/`는 runtime default로 쓰고 있으므로 유지 또는 명시적 resource package로 문서화 필요

## 결정 필요 사항

아래 항목은 변경 전 사용자 확인이 필요하다.

### Q1. 공용 persistence 디렉터리명

선택지:

- A. `apps/persistence/model_parameter/`로 변경한다.
- B. 기존 `apps/persistence/model_input/` 이름을 유지하고 역할만 정리한다.

권장:

- A. API/Agent/table naming과 맞추기 쉽고 신규 구조 문서와도 일관적이다.

리스크:

- A는 import 경로 변경 범위가 더 크다.
- B는 변경 범위가 작지만 `model_input`과 `model_parameter` 용어가 계속 혼재한다.

결정:

- A. `apps/persistence/model_parameter/`로 변경한다.

### Q2. Agent service 파일명

선택지:

- A. `model_parameter_service.py`로 변경한다.
- B. 기존 `model_input_service.py`를 유지한다.

권장:

- A. Agent 이름, API path, 공용 persistence 디렉터리명과 맞출 수 있다.

리스크:

- A는 테스트 mock path와 import 변경이 필요하다.

결정:

- A. `model_parameter_service.py`로 변경한다.

### Q3. `subgraphs/model_parameter_proposal/` 도입 범위

선택지:

- A. 이번 구조 개선에서 도입한다.
- B. 우선 `prompts/`, `utils/`, `presentation.py`만 분리하고 subgraph는 후속으로 둔다.

권장:

- A. candidate validation, slot proposal, value proposal은 독립 LLM pipeline 성격이 강하고 테스트 가치가 높다.

리스크:

- A는 파일 이동과 import 변경이 크다.
- B는 변경 범위가 작지만 `nodes.py` 비대화가 일부 남는다.

결정:

- B. 이번 구조 개선에는 subgraph를 도입하지 않는다.

### Q4. `resources/` 위치

선택지:

- A. Agent package 내부에 유지하고 runtime packaged resource로 명시한다.
- B. root `local/` 또는 별도 data 위치로 이동한다.

권장:

- A. 현재 기본 실행 경로에서 Excel/Basecase를 참조하므로 로직 영향이 가장 작다.

리스크:

- A는 app package가 큰 resource 파일을 포함한다.
- B는 config/path 처리 변경이 필요하다.

결정:

- A. Agent package 내부에 유지하고 runtime packaged resource로 명시한다.

### Q5. `docs/reports/scripts` 정리 범위

선택지:

- A. `docs/`는 유지하고, 테스트/검증용 `scripts/`와 테스트 결과 `reports/`는 `tests/` 하위로 이동한다.
- B. `docs/`, `reports/`, `scripts/` 모두 현재 위치에 유지한다.
- C. `docs/`, `reports/`, `scripts/` 전체를 root 문서/로컬/스크립트 위치로 이동한다.

권장:

- A. `docs/`는 현재 맥락 보존을 위해 유지하고, runtime package 안의 테스트/검증 스크립트와 테스트 결과 리포트는 테스트 디렉터리로 이동한다.

리스크:

- A는 script import 경로, report 출력 경로, 실행 안내를 수정해야 한다.
- B는 변경 범위가 작지만 runtime package 안에 테스트/검증 script와 report 산출물이 남는다.
- C는 변경 범위가 크고 문서 내 상대 경로 보정이 필요하다.

결정:

- A. `docs/`는 유지하고, 테스트/검증용 `scripts/`는 `tests/manual/model_parameter_agent/`로,
  테스트 결과 `reports/`는 `tests/reports/model_parameter_agent/`로 이동한다.

### Q6. `confirm_parameters` flow 정렬 수준

선택지:

- A. `state.py`, `nodes.py`를 추가해 `scenario_group_agent/confirm_generation`과 유사하게 맞춘다.
- B. 동기 단일 service 호출 flow이므로 현재 `RunnableLambda` 구조를 유지한다.

권장:

- A. 구조 통일성과 향후 확장성을 우선한다.

리스크:

- A는 로직은 동일해도 파일 이동과 테스트 변경이 필요하다.

결정:

- A. `state.py`, `nodes.py`를 추가해 `scenario_group_agent/confirm_generation`과 유사하게 맞춘다.
  현재 `flow.py`에 있는 기능 중 node 역할이 명확한 validation/service 호출/상태 update 로직은 `nodes.py`로 이관한다.

### Q7. `mapping.py`, prompt, flow helper 분리 수준

선택지:

- A. prompt는 `prompts/`로 분리하고, `flow.py`에는 핵심 실행 흐름만 남기며, `utils/`는 `parameter_mapping.py`, `basecase.py` 두 파일 정도로만 분리한다.
- B. `mapping.py`를 `parameter_mapping.py`, `knowledge_base.py`, `basecase.py`, `normalization.py`처럼 더 세분화한다.

권장:

- A. 기존 `scenario_group_agent`에도 과도한 `utils/` 세분화 사례는 없고, 이번 목적은 구조 통일이므로 최소 분리가 적절하다.

리스크:

- A는 일부 private helper가 각 파일에 남아 파일이 다시 커질 수 있다.
- B는 책임은 더 세밀해지지만 파일 수와 import 경로 변경이 커진다.

결정:

- A. prompt는 분리하고, `flow.py`는 핵심만 남기며, `utils/`는 두 파일 정도로만 분리한다.

### Q8. LLM/internal schema 위치

선택지:

- A. flow 하위에 `llm_schema.py`를 만들지 않고 `schemas/model_parameter_proposal.py`에 둔다.
- B. flow 하위 helper로 `flows/propose_parameters/llm_schema.py`를 둔다.

권장:

- A. 별도 `schemas/` 디렉터리를 활용하고, flow 하위 파일명은 가이드의 `api_schema.py`, `state.py`, `flow.py`, `nodes.py` 중심으로 유지한다.

리스크:

- A는 propose flow 전용 schema도 Agent-level `schemas/`에 위치한다.
- B는 flow 안에서 응집도는 높지만 flow 하위 파일명이 기준 구조에서 멀어진다.

결정:

- A. LLM/internal schema는 `schemas/model_parameter_proposal.py`로 분리한다.

### Q9. `flows/propose_parameters/` helper 파일 추가 범위

선택지:

- A. flow 하위 helper 파일은 `validation.py` 하나만 추가하고, prompt payload builder/sanitizer/fallback은 `nodes.py` private helper 또는 `validation.py`에 둔다.
- B. `prompt_payload.py`, `sanitization.py` 같은 세부 helper 파일을 추가한다.

권장:

- A. flow 하위 파일명을 `api_schema.py`, `state.py`, `flow.py`, `nodes.py`, `validation.py` 중심으로 유지해 가이드와 가깝게 맞춘다.

리스크:

- A는 `nodes.py`가 완전히 작아지지는 않을 수 있다.
- B는 책임은 더 세밀하지만 flow 디렉터리 파일 수가 늘어난다.

결정:

- A. `flows/propose_parameters/`에는 `validation.py` 하나만 추가한다.

### Q10. `apps/persistence/model_parameter/schema.py` DTO 범위

선택지:

- A. 공용 persistence schema에는 model parameter 3개 테이블 관련 DTO만 둔다. scenario/event/group 조합 context는 Agent service 내부 TypedDict 또는 기존 dict shape으로 유지한다.
- B. scenario/event/group까지 합친 `ModelParameterScenarioContext`도 공용 persistence schema에 둔다.

권장:

- A. `scenario_group_agent`도 공용 persistence schema에는 도메인 payload 중심으로 두고, 여러 도메인을 조합한 service context는 Agent service 쪽에서 관리한다.

리스크:

- A는 context payload가 당분간 dict/TypedDict 중심으로 남는다.
- B는 타입 경계는 더 명확하지만 공용 persistence schema가 Agent 유스케이스 context까지 소유하게 된다.

결정:

- A. 공용 persistence schema에는 model parameter 3개 테이블 관련 DTO만 둔다.

### Q11. scenario/event/group context 조회 책임

선택지:

- A. `ModelParameterService`에서 `ScenarioRepository`, `ScenarioGroupRepository`, `EventRepository`, `ModelParameterRepository`를 조합한다. 필요한 public 조회 메서드가 없으면 각 domain repository에 추가한다.
- B. `ModelParameterRepository`가 기존처럼 scenario/event/group 조회까지 직접 수행한다.

권장:

- A. repository는 자기 domain query만 담당하고, 여러 domain 조합은 Agent service가 담당한다.

리스크:

- A는 기존 repository에 public 조회 메서드 추가와 import 변경이 필요하다.
- B는 변경 범위가 작지만 도메인 경계가 계속 흐려진다.

결정:

- A. `ModelParameterService`에서 각 domain repository를 조합하고, 필요한 public 조회 메서드는 해당 repository에 추가한다.

### Q12. `presentation.py` 이동 범위

선택지:

- A. `flow.py`의 proposal response 조립, callback payload 조립, parameter summary, 외부 응답용 slot/value normalization helper를 `presentation.py`로 이동한다.
- B. callback payload만 `presentation.py`로 이동하고 나머지는 `flow.py`에 유지한다.

권장:

- A. `scenario_group_agent/presentation.py`처럼 외부 응답 shape 조립 책임을 한 곳에 둔다.

리스크:

- A는 이동 범위가 넓어 import/test 수정이 더 필요하다.
- B는 변경 범위가 작지만 `flow.py`에 응답 조립 책임이 계속 남는다.

결정:

- A. 외부 응답/callback payload 조립과 관련 normalization helper는 `presentation.py`로 이동한다.

### Q13. 자동화 테스트 파일 분할 여부

선택지:

- A. `tests/automated/test_model_parameter_agent_contract.py`를 기능별 테스트 파일로 분할한다.
- B. 테스트 파일 분할은 이번 구조 개선에서 제외하고, import/mock path 수정만 수행한다.

권장:

- B. 이번 작업의 핵심은 runtime 구조 개선이며, 테스트 파일 분할까지 포함하면 변경 범위가 커진다.

리스크:

- B는 큰 테스트 파일이 유지된다.
- A는 테스트 유지보수성은 좋아지지만 변경량이 커진다.

결정:

- B. 테스트 파일 분할은 제외하고, 구조 변경에 필요한 import/mock path 수정만 수행한다.

### Q14. 기존 model parameter 문서 업데이트 범위

선택지:

- A. 구조 변경과 직접 관련된 경로 설명, 디렉터리명, script/report 위치만 최소 업데이트한다.
- B. model parameter Agent 문서 전체를 새 구조 기준으로 전면 개편한다.
- C. 기존 문서는 수정하지 않는다.

권장:

- A. 구조 변경 후 문서 경로가 틀어지는 부분은 방치하지 않되, 문서 전면 개편은 별도 작업으로 둔다.

리스크:

- A는 일부 오래된 설명이 남을 수 있다.
- B는 변경 범위가 커진다.
- C는 구조 변경 직후 문서와 실제 파일 경로가 어긋날 수 있다.

결정:

- A. 구조 변경과 직접 관련된 경로 설명만 최소 업데이트한다.

### Q15. 공유 API DTO 위치

선택지:

- A. `ProposalParameter`, `ModelParameterTarget`처럼 proposal/confirmation 양쪽에서 공유하는 외부 API DTO는 `schemas/api/parameters.py`에 유지한다.
- B. 각 flow의 `api_schema.py`에 중복 또는 재정의한다.
- C. `schemas/model_parameter_proposal.py`로 옮긴다.

권장:

- A. `scenario_group_agent`의 `schemas/table.py`처럼 여러 API/flow가 공유하는 외부 API shape은 별도 shared API schema에 두는 편이 자연스럽다.

리스크:

- A는 flow schema가 한 파일 안에서 완전히 독립적이지는 않다.
- B는 중복이 생긴다.
- C는 LLM/internal schema와 외부 API schema 경계가 흐려진다.

결정:

- A. 공유 외부 API DTO는 `schemas/api/parameters.py`에 유지한다.

### Q16. 기존 import 경로 호환 re-export 여부

선택지:

- A. 기존 `apps/persistence/model_input` 경로 re-export를 두지 않고 모든 import/test/mock path를 새 경로로 수정한다.
- B. 기존 경로에 deprecation re-export를 잠시 둔다.

권장:

- A. 구조 통일 목적의 변경이므로 오래된 alias를 남기지 않는 편이 명확하다.

리스크:

- A는 import/test/mock path 수정 범위가 더 크다.
- B는 이행은 쉽지만 오래된 경로가 계속 남아 구조가 흐려진다.

결정:

- A. 기존 경로 re-export 없이 새 경로로 전면 수정한다.

## 1차 변경 순서 제안

1. persistence naming 결정
2. `apps/persistence/model_parameter/schema.py` 추가
3. `ModelParameterRepository`에서 scenario/event/scenario_group 조회 제거
4. `ModelParameterService`에서 각 domain repository 조합
5. `presentation.py` 추가 및 proposal/callback response 조립 이동
6. `prompts/` 추가 및 system prompt 이동
7. `utils/` 추가 및 `mapping.py`를 `parameter_mapping.py`, `basecase.py` 두 파일 중심으로 분리
8. `api_schema.py`에서 LLM/internal schema를 `schemas/model_parameter_proposal.py`로 분리
9. `confirm_parameters` 구조 정렬
10. 테스트 import/mock path 정리
11. 구조 변경과 직접 관련된 model parameter 문서 경로 설명 최소 업데이트
12. `pytest tests/automated/test_model_parameter_agent_contract.py -q`
13. `python -m compileall apps tests`

테스트 파일 분할은 이번 구조 개선 범위에 포함하지 않는다.

## 테스트 계획

최소 검증:

```bash
pytest tests/automated/test_model_parameter_agent_contract.py -q
python -m compileall apps tests
```

구조 변경 후 추가 검증 후보:

```bash
pytest tests/automated -q
```

수동 검증 필요 여부:

- background proposal callback 경로
- sync proposal API
- confirm proposal API

## 인터뷰 로그

- Q1. 공용 persistence 디렉터리명은 `apps/persistence/model_parameter/`로 변경하기로 결정했다.
- Q2. Agent service 파일명은 `model_parameter_service.py`로 변경하기로 결정했다.
- Q3. 이번 구조 개선에는 `subgraphs/model_parameter_proposal/`를 도입하지 않기로 결정했다.
- Q4. `resources/`는 Agent package 내부에 유지하고 runtime packaged resource로 명시하기로 결정했다.
- Q5. `docs/`는 유지하고, 테스트/검증용 `scripts/`는 `tests/manual/model_parameter_agent/`로,
  테스트 결과 `reports/`는 `tests/reports/model_parameter_agent/`로 이동하기로 결정했다.
- Q6. `confirm_parameters`는 `state.py`, `nodes.py`를 추가해 `scenario_group_agent/confirm_generation`과 유사하게 맞추고,
  현재 `flow.py`에 있는 기능 중 node 역할이 명확한 로직은 `nodes.py`로 이관하기로 결정했다.
- Q7. prompt는 `prompts/`로 분리하고, `flow.py`는 핵심 실행 흐름만 남기며,
  `utils/`는 `parameter_mapping.py`, `basecase.py` 두 파일 정도로만 분리하기로 결정했다.
- Q8. LLM/internal schema는 flow 하위 `llm_schema.py`가 아니라 `schemas/model_parameter_proposal.py`로 분리하기로 결정했다.
- Q9. `flows/propose_parameters/` 하위 helper 파일은 `validation.py` 하나만 추가하고,
  prompt payload builder/sanitizer/fallback은 `nodes.py` private helper 또는 `validation.py`에 두기로 결정했다.
- Q10. `apps/persistence/model_parameter/schema.py`에는 model parameter 3개 테이블 관련 DTO만 두고,
  scenario/event/group 조합 context는 Agent service 내부 TypedDict 또는 기존 dict shape으로 유지하기로 결정했다.
- Q11. scenario/event/group/dimension template 조회는 `ModelParameterRepository`에서 제거하고,
  `ModelParameterService`가 각 domain repository를 조합한다. 필요한 public 조회 메서드는 해당 repository에 추가하기로 결정했다.
- Q12. proposal response, callback payload, parameter summary, 외부 응답용 slot/value normalization helper는
  `presentation.py`로 이동하기로 결정했다.
- Q13. 자동화 테스트 파일 분할은 이번 구조 개선에서 제외하고, 필요한 import/mock path 수정만 수행하기로 결정했다.
- Q14. 기존 model parameter 문서는 구조 변경과 직접 관련된 경로 설명만 최소 업데이트하기로 결정했다.
- Q15. `ProposalParameter`, `ModelParameterTarget` 같은 공유 외부 API DTO는 `schemas/api/parameters.py`에 유지하기로 결정했다.
- Q16. 기존 `apps/persistence/model_input` 경로 re-export 없이 모든 import/test/mock path를 새 경로로 수정하기로 결정했다.

## 적용 완료 기준 구조

```text
apps/agents/model_parameter_agent/
├── api.py
├── docs/
├── flows/
│   ├── confirm_parameters/
│   │   ├── api_schema.py
│   │   ├── flow.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── validation.py
│   └── propose_parameters/
│       ├── api_schema.py
│       ├── flow.py
│       ├── nodes.py
│       ├── state.py
│       └── validation.py
├── persistence/
│   └── model_parameter_service.py
├── presentation.py
├── prompts/
│   └── model_parameter_proposal.py
├── resources/
├── schemas/
│   ├── api/
│   │   └── parameters.py
│   └── model_parameter_proposal.py
└── utils/
    ├── basecase.py
    └── parameter_mapping.py

apps/persistence/model_parameter/
├── models.py
├── repository.py
└── schema.py

tests/manual/model_parameter_agent/
├── benchmark_cache_key_effect.py
├── benchmark_llm_call_variants.py
├── benchmark_reasoning_quality.py
├── compare_llm_reasoning_outputs.py
├── evaluate_event_type_proposals.py
└── evaluate_proposals.py

tests/reports/model_parameter_agent/
└── *.md
```

## 적용 후 역할 기준

| 경로 | 역할 |
| --- | --- |
| `flows/propose_parameters/flow.py` | LangGraph 조립, `to_state`/`to_output`, proposal 저장 orchestration |
| `flows/propose_parameters/nodes.py` | 제안 graph node, prompt payload builder, LLM sanitizer/fallback/backfill |
| `flows/propose_parameters/validation.py` | graph routing, candidate/proposal 존재 검증 |
| `flows/propose_parameters/api_schema.py` | propose endpoint request/response schema |
| `flows/confirm_parameters/flow.py` | confirm graph 조립, state/output 변환 |
| `flows/confirm_parameters/nodes.py` | confirmation validation 호출 및 proposal 확정 저장 node |
| `flows/confirm_parameters/state.py` | confirmation graph state |
| `prompts/model_parameter_proposal.py` | candidate/slot/value LLM system prompt |
| `presentation.py` | proposal response, callback payload, parameter summary, slot/value output normalization |
| `utils/parameter_mapping.py` | DB mapping resource 변환, candidate matching, Basecase 구현 함수 |
| `utils/basecase.py` | Basecase public helper 재노출 |
| `schemas/model_parameter_proposal.py` | LLM/internal proposal schema |
| `schemas/api/parameters.py` | 외부 API 공유 DTO(`ProposalParameter`, `ModelParameterTarget`) |
| `persistence/model_parameter_service.py` | scenario/event/group repository와 model parameter repository 조합 |
| `apps/persistence/model_parameter/models.py` | model parameter 3개 테이블 ORM |
| `apps/persistence/model_parameter/repository.py` | model parameter 3개 테이블 조회/저장 |
| `apps/persistence/model_parameter/schema.py` | model parameter persistence DTO |

## 적용 후 일치성 평가 기준

- `apps/persistence/model_input/`, `model_input_service.py`, `apps/agents/model_parameter_agent/mapping.py` 소스 경로가 남아 있지 않아야 한다.
- `ModelParameterRepository`는 scenario/event/scenario_group/template repository를 직접 참조하지 않아야 한다.
- `ModelParameterService`가 `ScenarioRepository`, `ScenarioGroupRepository`, `EventRepository`, `ModelParameterRepository`를 조합해야 한다.
- `api_schema.py`는 endpoint schema만 포함하고, LLM/internal schema는 `schemas/model_parameter_proposal.py`에 있어야 한다.
- prompt 문자열은 `prompts/model_parameter_proposal.py`에 있어야 한다.
- 테스트/검증 script와 report는 각각 `tests/manual/model_parameter_agent/`, `tests/reports/model_parameter_agent/`에 있어야 한다.
- 기존 비즈니스 로직의 prompt 내용, sanitizer, candidate/value 생성 규칙은 구조 이동 외 변경하지 않는다.
