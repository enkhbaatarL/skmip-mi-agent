# Scenario Group Agent 개요

## 한눈에 보기

Scenario Group Agent는 MI Event 1~5개를 근거로 LNG 시장 Scenario Group을 만들고, 사용자가 편집한
Scenario를 검증한 뒤 Scenario별 Signpost를 생성한다. 현재 신규 생성의 정본은 v4
`multi_event_model_lever_dimensions` 방식이다.

```text
Event 선택
  → v4 Scenario Group 생성
  → Scenario 검토·편집
  → Validation
  → Signpost 생성
  → Confirmation
```

FastAPI 진입점은 저장소 루트의 `main.py`다. Agent router는
`apps/agents/scenario_group_agent/api.py`에서 조립한다.

## 문서 읽기 순서

| 순서 | 문서 | 대상 |
| ---: | --- | --- |
| 1 | 이 문서 | PL, 신규 담당자, 협업 Agent 개발자 |
| 2 | [API Spec](02_SCENARIO_GROUP_AGENT_API_SPEC.md) | Client·Platform·API 개발자 |
| 3 | [v4 Flow](03_SCENARIO_GROUP_AGENT_FLOW.md) | Scenario Agent 개발자 |
| 4 | [DB Spec](04_SCENARIO_GROUP_AGENT_DB_SPEC.md) | Agent·DB·운영 담당자 |
| 5 | [테스트와 품질 평가](05_SCENARIO_GROUP_AGENT_TEST_AND_QUALITY.md) | 개발·QA·품질 담당자 |

공통 package 경계는 [Project Directory Structure](../../architectures/project_directory_structure.md),
Python 구현 규칙은 [Python conventions](../../../.claude/rules/python-conventions.md)를 먼저 따른다.

## 책임과 경계

Scenario Group Agent가 소유하는 책임은 다음과 같다.

- Event와 Model Impact Lever를 근거로 v4 Dimension과 Scenario를 생성한다.
- Scenario Group 생성 작업의 operation, SSE event, Presentation projection을 관리한다.
- 사용자가 편집한 Scenario table을 검증하고 통과 가능한 Change Set을 만든다.
- 최신 Validation 결과를 적용하고 Scenario별 Signpost를 생성한다.
- Scenario Group 조회, soft delete, Confirmation API를 제공한다.

다음 책임은 다른 영역에 있다.

- ORM과 table 단위 query: `apps/persistence/<domain>/`
- 공통 설정·예외·runtime 기반: `apps/common/`
- callback, LLM, MLflow 등 외부 연동: `apps/connectors/`
- Model Parameter proposal 계산: `apps/agents/model_parameter_agent/`
- 가격 해석: `apps/agents/interpret_agent/`

## Package 지도

```text
apps/agents/scenario_group_agent/
├── api.py
├── routers/
│   ├── scenario_groups.py
│   ├── scenario_group_stream.py
│   ├── scenario_generation_sync.py
│   ├── multi_event_scenario_group_sync.py
│   └── events.py
├── flows/
│   ├── create_multi_event_scenarios/
│   ├── add_dimension/
│   ├── validate_scenarios/
│   ├── create_signposts/
│   └── confirm_generation/
├── subgraphs/
├── persistence/
├── schemas/
├── prompts/
├── presentation.py
└── runtime.py
```

| 위치 | 확인할 내용 |
| --- | --- |
| `routers/` | endpoint, 즉시 응답, background/stream transport |
| `flows/*/flow.py` | prepare, graph 조립, inline/background 실행 |
| `flows/*/nodes.py` | 단계별 state 변경과 검증·저장 호출 |
| `prompts/` | LLM 입력과 structured output 계약 |
| `persistence/` | 여러 repository를 조합하는 Agent 유스케이스 |
| `presentation.py` | 상세·Presentation·후속 요청 body read model |
| `runtime.py` | create producer, EventHub, heartbeat, recovery |

## v4 핵심 결정

- 생성 입력은 중복 없는 양의 정수 `miEventIds` 1~5개와 `userId`다.
- canonical 생성 API는 `POST /scenario-groups`이며 응답 transport는 SSE다.
- Event Type Template이 아니라 Event 사실과 `tmm_mi_model_impact_lever_m` catalog로 Dimension을 설계한다.
- 최종 Dimension은 3~6개, Scenario는 3~5개다.
- Scenario 가격 결과는 절대 가격이 아니라 JKM 기준 `pressureBand`와 근거다.
- `probabilityScore`는 서버가 정수 백분율 합계 100으로 정규화하고 baseline은 정확히 하나다.
- Event lineage는 Scenario Group master의 대표 Event 컬럼이 아니라
  `tmm_mi_scenario_group_event_m` 관계가 정본이다.
- create POST는 멱등하지 않다. timeout이나 stream 오류 뒤 동일 POST를 자동 재시도하지 않는다.
- v2/v3는 비교와 과거 데이터 호환을 위한 경로다. 신규 생성·문서·개선의 기본 판단은 v4를 따른다.

## 실행 수명과 상태

canonical create는 Scenario Group, operation, `accepted` event를 한 transaction으로 저장한 뒤 lifespan task
runner에서 producer를 실행한다. SSE 연결이 끊겨도 producer는 계속되며 operation 조회와 재연결 stream으로
복구한다.

Validation과 Signpost는 즉시 접수 응답 후 FastAPI background task에서 처리하고 callback을 전송한다.
v4에서는 두 작업도 operation과 heartbeat를 기록한다. Confirmation은 동기 처리한다.

Scenario Group의 주요 stage는 다음 순서다.

```text
ready → scenario_created → scenario_validated → signpost_created → completed
```

Validation blocking 결과는 `scenario_created`에 남는다. Validation 실행 자체가 정상 종료됐더라도 콘텐츠가
차단될 수 있으므로 HTTP 성공, operation 성공, `canProceed`를 구분해서 확인한다.

## Source of truth

| 궁금한 내용 | 우선 확인 위치 |
| --- | --- |
| 등록 endpoint | `api.py`, `routers/*.py` |
| request/response 필드 | flow `api_schema.py`, `schemas/api/`, `schemas/endpoint.py` |
| v4 생성 graph | `flows/create_multi_event_scenarios/v4_flow.py`, `v4_nodes.py` |
| Validation 규칙 | `flows/validate_scenarios/v4_validation.py` |
| Signpost context·graph | `flows/create_signposts/`, `subgraphs/signpost_generation/` |
| DB table·column mapping | `apps/persistence/*/models.py` |
| DB query | `apps/persistence/*/repository.py` |
| 화면 read model | `presentation.py`, `schemas/api/scenario_group_presentation.py` |
| 실행·품질 검증 | `tests/manual/`, `.claude/skills/scenario-*` |

문서와 코드가 다르면 코드를 먼저 확인하고, 의도된 변경이라면 같은 변경에서 문서를 갱신한다.

## 인수인계 체크리스트

- 변경하려는 endpoint가 운영, 테스트, deprecated 중 어디에 속하는지 확인한다.
- create 변경은 SSE event, Presentation snapshot, operation recovery까지 함께 검토한다.
- Validation 변경은 `checks`, Change Set, fingerprint, Signpost 적용 시점을 함께 검토한다.
- DB 접근은 Agent service와 공유 repository 경계를 지킨다.
- callback body 변경은 Platform 수신 계약과 sync 응답을 함께 확인한다.
- 기능 성공과 생성 품질을 분리해 테스트한다.
- 운영 토큰, MLflow 계정, 개인 메모는 `local/` 또는 `*.local`에만 둔다.
