# Project Directory Structure

## 목적

이 문서는 여러 Agent가 같은 저장소에서 일할 때 지켜야 하는 package 경계와 문서 배치 원칙을 정의한다.
Agent별 endpoint, graph, DB 필드의 상세 설명은 `docs/agents/<agent_name>/`의 정본을 따른다.

## 루트 구조

```text
skmip-mi-agent/
├── AGENTS.md
├── README.md
├── main.py
├── model_param.py
├── interpret.py
├── event_generate.py
├── apps/
│   ├── agents/
│   ├── common/
│   ├── connectors/
│   └── persistence/
├── docs/
│   ├── architectures/
│   ├── agents/
│   └── guides/
├── envs/
├── local/
├── scripts/
└── tests/
    ├── automated/
    └── manual/
```

| 위치 | 책임 |
| --- | --- |
| `apps/agents/<agent_name>/` | Agent별 router, flow, prompt, schema, 유스케이스 service |
| `apps/common/` | 설정, 예외, logging, middleware, runtime 등 공통 실행 기반 |
| `apps/connectors/` | callback, HTTP, LLM, MLflow, VDB 등 외부 시스템 adapter |
| `apps/persistence/<domain>/` | 공유 DB ORM, repository, persistence DTO |
| `tests/automated/` | 자동 회귀·계약 테스트 |
| `tests/manual/` | 로컬 API 실행, 증적·보고서 생성 도구 |
| `scripts/` | 데이터 준비, migration 보조, 일회성 운영·실험 script |
| `local/` | 커밋하지 않는 문서·계획·실험·실행 산출물 |

## Agent package 기준

```text
apps/agents/<agent_name>/
├── api.py                 # Agent router 조립
├── routers/               # HTTP endpoint와 transport
├── flows/<flow_name>/     # flow별 state, graph, node, API schema
├── subgraphs/             # 여러 flow에서 재사용하는 graph
├── persistence/           # Agent 유스케이스 service
├── schemas/               # 공유 또는 flow-less API schema
├── prompts/               # prompt와 structured output 정의
├── presentation.py        # 외부 응답·화면 read model 조립
├── runtime.py             # Agent 전용 lifespan/background runtime
└── utils/                 # Agent 내부의 결정적 helper
```

- `api.py`는 router를 조립하고 endpoint 구현은 `routers/`에 둔다.
- endpoint는 입력 변환, 권한·요청 검증, flow/service 호출까지만 담당한다.
- flow 전용 request/response는 `flows/<flow_name>/api_schema.py`에 둔다.
- 여러 flow가 공유하거나 flow가 없는 API schema는 `schemas/api/`에 둔다.
- graph state는 flow 또는 subgraph의 `state.py`, graph 조립은 `flow.py`, node는 `nodes.py`가 소유한다.
- flow/node는 SQL을 직접 호출하지 않고 Agent 유스케이스 service를 사용한다.

## Persistence 경계

Event 사전 웹 검증은 `routers/events.py`의 `POST /events/verifications`에서
`persistence/event_verification_service.py`를 호출하는 flow-less read-only 유스케이스다.
HTTP 스키마는 `schemas/api/event_verifications.py`, 검색·비교 지침 및 structured output은
`prompts/event_verification.py`가 소유한다. 현재 게시된 Event 조회는
`apps/persistence/event/service.py`, 외부 검색·비교는 기존 `apps/connectors/web/`와
`apps/connectors/llm/`를 재사용한다. 검증 결과는 요청에 반환하며 DB에 저장하지 않는다.

`POST /events/{miEventId}/verification-updates`는
`persistence/event_verification_update_service.py`에서 웹 검증·수정안 생성·재검증을 수행한다.
HTTP 스키마는 `schemas/api/event_verification_updates.py`, 수정 지침은 `prompts/event_verification_update.py`다.
DB 조회·transaction은 `apps/persistence/event/service.py`, row lock·Snapshot INSERT·Event UPDATE는
`apps/persistence/event/update_repository.py`가 소유한다. 이 repository는 현재 DB 컬럼을 reflection하여
조회 ORM에 없는 원본 확장 컬럼까지 Snapshot에 보존하고, 수정은 명시적 본문 allowlist로 제한한다.
DB migration은 관리 저장소를 따르며 실행 시 테이블 변경은 수행하지 않는다.

Event 추천은 `routers/events.py`의 `POST /events/recommendations`에서
`persistence/event_recommendation_service.py`를 호출한다. HTTP 스키마는
`schemas/api/event_recommendations.py`, 로컬 Qdrant adapter는
`apps/connectors/vdb/local_event_search.py`가 소유한다. MySQL 조회는 기존
`apps/persistence/event/service.py`를 사용한다. CLI와 API는 같은 컬렉션 식별 함수를 공유한다.

Scenario 품질 평가는 `scenario_group_agent/flows/evaluate_scenarios`와
`persistence/scenario_quality_evaluation_service.py`가 실행·transaction을 담당하고,
공유 ORM/repository/DTO는 `apps/persistence/scenario_quality_evaluation`에 둔다.

```text
router / flow / node
  → apps/agents/<agent_name>/persistence/*_service.py
  → apps/persistence/<domain>/repository.py
  → apps/persistence/<domain>/models.py
```

- 공유 ORM과 table 단위 query는 `apps/persistence/<domain>/`이 소유한다.
- 여러 repository를 조합하는 Agent 유스케이스는 Agent package의 `persistence/` service가 소유한다.
- persistence DTO는 `apps/persistence/<domain>/schema.py`, 공통 base와 enum은
  `apps/persistence/schema_base.py`, `apps/persistence/enums.py`에 둔다.
- Event 검색 문서 준비는 `apps/persistence/event/`의 조회 service/repository/DTO를 사용한다.
  문서 계약·변환은 `scenario_group_agent/schemas/event_search_document.py`와 `utils/event_search_document.py`,
  로컬 export 진입점은 `scripts/export_event_search_documents.py`가 소유한다. API/flow 연결 전 내부 도구다.
- 외부 모델 영역이 소유하는 테이블을 read-only로 조합하는 `model_result`, `mi_base`
  domain은 raw SQL repository를 사용하며 Agent `APPLICATION_TABLES`·ORM schema 소유권에 추가하지 않는다.
- DB schema 변경의 migration 정본이 별도 관리 저장소에 있으면 Agent DB 문서에 그 위치를 명시한다.

## 공통 구현 규칙

- 설정은 `apps.common.configs.config.get_settings()`로 읽는다. 일반 app 코드에서 `os.environ`을 직접 읽지 않는다.
- domain/API 오류는 `MIBaseError(ErrorCode..., detail=...)`를 사용한다.
- 즉시 응답 후 장시간 처리하는 API는 해당 Agent의 기존 background/lifespan 실행 패턴을 따른다.
- 새 구조를 만들기 전에 같은 Agent의 기존 패턴을 우선 재사용한다.
- 제거된 `mi_agent`, `scenario_agent`, `event_flow_agent`, `signpost_flow_agent` package를 되살리지 않는다.

## 문서 배치 기준

| 문서 종류 | 위치 | 예시 |
| --- | --- | --- |
| 모든 Agent가 따라야 하는 구조·경계 | `docs/architectures/` | package ownership, 공통 실행 경계 |
| Agent별 공식 인수인계·구현 문서 | `docs/agents/<agent_name>/` | API, flow, DB, 테스트 |
| 특정 담당자·작업 목적의 가이드 | `docs/guides/` | MLflow, Agent 간 데이터 handoff |
| 커밋하지 않는 초안·실험·산출물 | `local/docs/`, `local/output/` | 회의 메모, 실행 report |

공식 문서는 현재 코드와 함께 갱신한다. package ownership, flow boundary, endpoint-to-flow mapping이 바뀌면
공통 Architecture와 해당 Agent 문서를 함께 검토한다. `local/` 자료는 공식 문서의 정본으로 사용하지 않는다.

## 현재 Agent 진입점

Agent는 진입점별로 별도 이미지·배포 단위로 운영한다. Agent 전용 Dockerfile은 진입점 파일을 이미지의
`main.py`로 복사하므로 컨테이너 실행 명령은 모두 `gunicorn main:app`이다.

| Agent | FastAPI 진입점 | 외부 빌드 Dockerfile | 공식 문서 |
| --- | --- | --- | --- |
| Scenario Group Agent | `main.py` | `Dockerfile` (내부: `Dockerfile.internal`) | [`docs/agents/scenario_group_agent/`](../agents/scenario_group_agent/01_SCENARIO_GROUP_AGENT_OVERVIEW.md) |
| Model Parameter Agent | `model_param.py` | `Dockerfile.model_param` | [`docs/agents/model_parameter_agent/`](../agents/model_parameter_agent/01_MODEL_PARAMETER_AGENT_OVERVIEW.md) |
| Interpret Agent | `interpret.py` | `Dockerfile_interpret` | [`docs/agents/interpret_agent/`](../agents/interpret_agent/01_INTERPRET_AGENT_OVERVIEW.md) |
| Event Generate Agent | `event_generate.py` | `Dockerfile_event_generate` (내부: `Dockerfile_event_generate.internal`) | [`docs/agents/event_generate_agent/`](../agents/event_generate_agent/01_EVENT_GENERATE_AGENT_ONBOARDING.md) |

- 외부 빌드 Dockerfile은 공개 base image와 PyPI를, 내부(`*.internal`) Dockerfile은 내부 base image와 Nexus PyPI를 사용한다.
- Event Generate Agent endpoint: `POST /events/generations` → `flows/generate_from_query`
- `devops/k8s/`의 매니페스트는 참고용 예시다. SKPC dev/prod의 Deployment·Service·ConfigMap·Secret은 AMDP에서 관리한다.
