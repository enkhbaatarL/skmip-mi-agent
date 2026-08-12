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
├── Dockerfile_interpret
├── Dockerfile.base
├── Dockerfile.internal
├── README.md
├── main.py
├── interpret.py
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

- `main.py`: Scenario Group Agent 전용 FastAPI app 구성과 router 등록
- `interpret.py`: Interpret Agent 전용 FastAPI app 구성과 router 등록. `Dockerfile_interpret`가 이미지에서 이 파일을 `main.py`로 복사한다.
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
├── routers/
│   ├── __init__.py
│   ├── events.py
│   ├── multi_event_scenario_group_sync.py
│   ├── scenario_generation_sync.py
│   ├── scenario_groups.py
│   ├── scenario_group_stream.py
│   └── security.py
├── persistence/
│   ├── event_service.py
│   ├── model_impact_lever_service.py
│   ├── scenario_service.py
│   ├── scenario_group_service.py
│   ├── scenario_group_operation_service.py
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
│   ├── api/
│   │   ├── dimension_mapping.py       # flow-less mapping 승인 API DTO
│   │   ├── manage_scenario_groups.py  # 공통 조회·삭제·operation API DTO
│   │   └── scenario_group_presentation.py # 화면 전용 Presentation read model DTO
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
  - Agent router 조립을 담당한다.
  - 실제 FastAPI endpoint 선언은 `routers/` 하위 파일에 둔다.
- `routers/`
  - FastAPI endpoint 선언, request schema 수신, background task 등록, flow 진입점 호출을 담당한다.
  - endpoint 내부에 도메인 로직을 길게 두지 않고 schema 변환, validation, flow/service 호출까지만 담당한다.
  - `/scenario-groups`를 canonical API로 삼는다. 버전 prefix가 있는 경로는 legacy 호환 또는 sync 테스트용이며,
    router 파일 분리는 도메인 분리가 아니라 API 수명주기와 transport 책임 분리다.
  - Scenario Group 생성·검증·Signpost·확정과 공통 업무 CRUD는 `scenario_groups.py`,
    validation/signpost sync 테스트 API는 `scenario_generation_sync.py`, v2/v3/v4 생성 sync는
    `multi_event_scenario_group_sync.py`,
    operation 조회·SSE transport는 `scenario_group_stream.py`, Event 조회는 `events.py`에 둔다.
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
  - 예: `create_multi_event_scenarios`, `validate_scenarios`, `create_signposts`, `confirm_generation`
  - versioned 다중 Event 생성은 `create_multi_event_scenarios/`에 두며
    v2 원본 dimension, v3 합성 dimension, v4 모델 영향 레버 dimension의
    공통 계약·실행을 소유한다.
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
  - 신규/이관 대상 API 공통 schema 위치다. 기존 flow는 아직 `schemas/endpoint.py`, `schemas/table.py`를 사용한다.
  - `common.py`, `table.py`, `manage_scenario_groups.py`처럼 flow 경계에 속하지 않는 공유 API schema를 둔다.

## 현재 Agent 예시: `scenario_group_agent`

`scenario_group_agent`는 위 기본 구조를 따르는 현재 런타임 Agent다.

- `flows/create_multi_event_scenarios/`: v2/v3 Template 기반 sync와 v4 모델
  영향 레버 기반 sync/비동기 다중 Event scenario 생성 flow
  - `state.py`가 v2/v3/v4 graph state를, `flow.py`가 v2/v3 graph를,
    `v4_flow.py`가 v4 graph를 소유한다. LLM 호출 node는 `nodes.py`와
    `v4_nodes.py`에 두고 sync 및 background 실행이 같은 compiled graph를 사용한다.
  - Event/Template/impact catalog 조회와 빈 Scenario Group 준비는 graph 진입 전에
    service로 일괄 수행한다. graph 안에서는 LLM 단계와 최종 일괄 저장만 node로 표현한다.
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
- `apps/persistence/event/`, `apps/persistence/model_impact_lever/`, `apps/persistence/scenario_group/`, `apps/persistence/scenario_group_operation/`, `apps/persistence/scenario/`, `apps/persistence/signpost/`: DB domain 단위 persistence 계층
- `apps/persistence/model_impact_lever/`: v4 Scenario 생성이 사용하는 모델 영향 레버 catalog의 ORM, DTO, repository. 기존 모델 파라미터 master는 binding 활성 상태 확인을 위한 외부 참조로만 사용한다.
- `apps/agents/scenario_group_agent/persistence/model_impact_lever_service.py`: v4 생성 유스케이스에 필요한 레버 catalog hydration과 checksum 조립을 담당한다.
- `apps/persistence/scenario_group/event_set.py`: 요청 순서와 무관한 Event 조합 canonical 값과 SHA-256 hash
- `apps/persistence/scenario_group/models.py`: Scenario Group master와 Event 연결 ORM의 기준. master에는
  `mi_event_id`, `event_type_l2_id`를 두지 않고 Event lineage는
  `tmm_mi_scenario_group_event_m`에서만 관리한다.
- `prompts/scenario_generation.py`, `prompts/scenario_validation.py`, `prompts/signpost_generation.py`: 생성/검증/Signpost LLM prompt와 structured output schema
- `schemas/endpoint.py`: 기존 통합 flow endpoint request/response와 callback DTO. 이관된 관리 DTO는 호환 import만 제공
- `schemas/api/manage_scenario_groups.py`: 공통 조회·삭제·operation API DTO
- `schemas/api/scenario_group_presentation.py`: v1/v3/v4 공통 화면 Presentation read model DTO
- `schemas/table.py`: 현재 endpoint, presentation, flow state에서 공유하는 table DTO
- `apps/persistence/<domain>/schema.py`: `event`, `scenario_group`, `scenario_group_operation`, `scenario`, `signpost` service DTO
- `subgraphs/scenario_generation/schema.py`, `subgraphs/scenario_review/schema.py`, `subgraphs/signpost_generation/schema.py`: 각 subgraph의 graph/review DTO
- `apps/persistence/scenario/baseline_contrast.py`: scenario/signpost persistence와 generation/review에서 공유하는 baseline 대비 coverage 계산 helper
- `tools/`: 현재 구현된 Agent 전용 LLM tool은 없으며, 향후 tool 구현 위치로 예약
- `subgraphs/scenario_generation/`: scenario 생성 pipeline subgraph
- `subgraphs/scenario_review/`: scenario validation review subgraph
- `subgraphs/signpost_generation/`: signpost 생성 pipeline subgraph

`routers/scenario_generation.py`는 호환 import 집계 모듈이고,
`versioned_scenario_generation_sync.py`는 v2/v3/v4 sync 실행 함수를 제공한다.
운영 endpoint 조립은 `api.py`가 `scenario_groups.py`, `scenario_generation_sync.py`,
`multi_event_scenario_group_sync.py`, `scenario_group_stream.py`, `events.py`만 직접 include한다.

## API Endpoint ↔ Flow 경로 매핑

아래는 `scenario_group_agent`의 현재 매핑 예시다.
`main.py`에서 router prefix는 빈 문자열이며, 실제 ingress/API prefix가 필요한 환경은 별도 gateway 또는 `OPENAPI_PREFIX` 설정에서 처리한다.
Interpret Agent API는 전용 엔트리포인트 `interpret.py`에서만 등록하며 Scenario Group Agent의
`main.py`에는 등록하지 않는다.

```text
POST /scenario-groups
→ api.py
→ routers/scenario_groups.py
→ flows/create_multi_event_scenarios/v4_flow.py (prepare)
→ persistence/scenario_group_operation_service.py (group + operation + accepted transaction)
→ runtime.py (lifespan task runner)
→ flows/create_multi_event_scenarios/operation.py (producer)
→ apps/persistence/scenario_group_operation/

GET /scenario-groups/{scenario_group_id}
→ api.py
→ routers/scenario_groups.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_service.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_operation_service.py
→ presentation.py

DELETE /scenario-groups/{scenario_group_id}
→ api.py
→ routers/scenario_groups.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_service.py (running operation은 409)

GET /scenario-groups/{scenario_group_id}/operations/{operation_id}
→ api.py
→ routers/scenario_group_stream.py
→ apps/agents/scenario_group_agent/persistence/scenario_group_operation_service.py

GET /scenario-groups/{scenario_group_id}/operations/{operation_id}/stream
→ api.py
→ routers/scenario_group_stream.py
→ runtime.py (local EventHub 또는 operation별 adaptive DB tail watcher)
→ operation event DB replay + live-tail

POST /scenario-groups/{scenario_group_id}/{validation|signposts|confirmation}
→ api.py
→ routers/scenario_groups.py
→ 해당 flow

POST /scenario-groups/{scenario_group_id}/{validation|signposts}/sync
→ api.py
→ routers/scenario_generation_sync.py (테스트용, OpenAPI 미노출)
→ 해당 flow 동기 실행
```

`interpret_agent`의 현재 매핑은 아래와 같다.

```text
POST /scenario-groups/{scenario_group_id}/price-interpretations/preview
POST /scenario-groups/{scenario_group_id}/price-interpretations
→ interpret.py
→ apps/agents/interpret_agent/api.py
→ flows/interpret_price/flow.py
```

두 경로의 `scenario-groups`는 해석 대상 범위를 나타내며, endpoint 소유자는 Interpret Agent다.

`model_parameter_agent`의 현재 매핑은 아래와 같다.

실행 엔트리포인트는 저장소 루트의 `model_param.py`이며,
`Dockerfile.model_param`이 이미지 안에서 이 파일을 `main.py`로 복사한다.
기동 시 `utils/resource_bootstrap.py`가
`APP_CONFIG`의 `model_parameter_resources` 영역을 기준으로 Basecase/LUT source를 확정하고,
`utils/resource_runtime.py`에 worker별 immutable 경로를 등록한다. Object Storage가 활성화된 환경은
`apps/connectors/object_storage/`의 exact `HeadObject`/`GetObject`만 사용하며, 원격 실패 시 packaged
리소스로 폴백한다. manifest의 `lut`은 `enabled`로 catalog 생성 여부를 구분하고, `references`는 독립
parameter record를 만들지 않는 보조 CSV를 소유한다. 현재 canonical master는 21행·활성 10개이며
dimension mapping은 129행이다. 정확한 DB matrix는 `scripts/model_parameter/model-parameter-canonical-v1.json`,
사람이 읽는 명세는 `resources/Model_Parameter_Base_Case_Mapping.md`, 업무용 현재 표는
`resources/mapping/260807_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v1.xlsx`가 소유한다.
`resources/mapping/archive/`의 이전 Excel은 역사·검토 자료이며 실행 기준이 아니다.

제안 Flow는 전체 LUT record를 서버 cache/index에 유지한다. Step2 prompt에는 동일 기간을 공유하는 leaf를
`period_groups`로 묶고 Country→Plant→Train 고정축을 `fixed_axis_hierarchy`로 중첩하며, Step3에는 exact
검증된 slot의 단일 effective reference만 전달한다. 파라미터별 slot 상한과 별도로 요청 전체 slot,
Step2·Step3 compact JSON byte 상한을 node에서 LLM 호출 전에 검사한다.

```text
POST /model-parameters/scenarios/{scenario_id}/proposals
→ api.py
→ flows/propose_parameters/api_schema.py
→ flows/propose_parameters/flow.py
  - prepare_propose_parameters_callback()
  - run_propose_parameters_background()
→ flows/propose_parameters/nodes.py
→ utils/basecase.py
→ utils/lut/ + utils/resource_runtime.py
→ config.yaml:model_parameter_resources
→ prompts/model_parameter_proposal.py
→ presentation.py
→ apps/connectors/callback/callback_client.py
→ persistence/model_parameter_service.py
→ apps/persistence/model_parameter/repository.py

POST /model-parameters/scenarios/{scenario_id}/proposals/sync
→ api.py
→ flows/propose_parameters/api_schema.py
→ flows/propose_parameters/flow.py
→ flows/propose_parameters/nodes.py
→ utils/basecase.py
→ utils/lut/ + utils/resource_runtime.py
→ config.yaml:model_parameter_resources
→ prompts/model_parameter_proposal.py
→ presentation.py
→ persistence/model_parameter_service.py
→ apps/persistence/model_parameter/repository.py

POST /model-parameters/proposals/{modelParamProposalId}/confirmation
→ api.py
→ flows/confirm_parameters/api_schema.py
→ flows/confirm_parameters/flow.py
→ flows/confirm_parameters/state.py
→ flows/confirm_parameters/nodes.py
→ flows/confirm_parameters/validation.py
→ persistence/model_parameter_service.py
→ apps/persistence/model_parameter/repository.py
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
  - `tmm_mi_scenario_group_m`은 Event 대표 컬럼을 소유하지 않는다. Event ID, Event Type L2,
    Template lineage와 표시 순서는 `tmm_mi_scenario_group_event_m` 관계 row가 정본이다.
  - API의 호환 `miEventId`, `eventTypeL2Id`는 활성 Event 관계가 정확히 하나일 때만 계산한다.
    다중 Event 그룹은 대표 Event를 임의로 선택하지 않고 두 값을 `null`로 반환한다.
- Scenario
  - `apps/persistence/scenario/*`가 시나리오 저장/조회/동기화의 기준이다.
  - 과거 `scenario_agent`의 모델/서비스/repository를 새 코드에 추가하지 않는다.
- Model Impact Lever
  - `apps/persistence/model_impact_lever/*`가 v4 Scenario 생성용 영향 레버 catalog의 기준이다.
  - `tmm_mi_model_impact_lever_m` ORM과 레버 DTO·DB 조회를 소유한다.
  - `apps/agents/scenario_group_agent/persistence/model_impact_lever_service.py`가 모델 파라미터 binding 지원 상태 hydration과 catalog checksum 조립을 소유한다.
  - Scenario Group flow는 DB나 repository를 직접 조회하지 않고 Agent 내부 `ModelImpactLeverService`를 호출한다.
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
