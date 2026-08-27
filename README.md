# SKMIP MI Agent 문서 안내

이 README는 저장소 문서의 시작점이다. 구현 상세는 아래 정본 문서에서 확인한다.

## 공통 기준

- [프로젝트 작업 지침](AGENTS.md): 작업 전 읽어야 할 문서, 코드 작성 및 테스트 규칙
- [프로젝트 디렉터리 구조](docs/architectures/project_directory_structure.md): 공통 package 경계와 문서 배치 원칙
- [Python conventions](.claude/rules/python-conventions.md): Python, 설정, async, Pydantic, 예외 처리 기준

`docs/architectures/`에는 모든 Agent가 함께 따라야 하는 공식적이고 간결한 구조·경계만 둔다.
Agent 하나에만 해당하는 구현, API, DB, 테스트 설명은 `docs/agents/<agent_name>/`에 둔다.

## Agent별 공식 문서

| Agent | 시작 문서 | 주요 내용 |
| --- | --- | --- |
| Scenario Group Agent | [개요](docs/agents/scenario_group_agent/01_SCENARIO_GROUP_AGENT_OVERVIEW.md) | v4 API, create·validation·signpost flow, DB, 테스트·품질 평가 |
| Model Parameter Agent | [개요](docs/agents/model_parameter_agent/01_MODEL_PARAMETER_AGENT_OVERVIEW.md) | API, DB, proposal·confirmation flow, Basecase·LUT, 파라미터 추가, 테스트·품질 평가 |
| Interpret Agent | [개요](docs/agents/interpret_agent/01_INTERPRET_AGENT_OVERVIEW.md) | preview·비동기 가격 해석 flow, callback, DB, 테스트·품질 평가 |

Agent별 문서는 번호 순서대로 읽는다. 신규 Agent도 `docs/agents/<agent_name>/` 아래에 개요를 시작으로
공식 문서를 모은다.

## 특수 목적 가이드

`docs/guides/`에는 특정 역할이나 작업을 위한 가이드를 둔다. 공통 Architecture나 한 Agent의 전체 설명을
반복하지 않고, 필요한 정본 문서에 연결한다.

- [실행 가이드](docs/guides/launch.md)
- [MLflow tracing 가이드](docs/guides/mlflow-tracing.md)
- [Scenario v4 Dimension–Model Parameter Lever 인수인계](docs/guides/model_parameter_dimension_lever_handoff.md)
- [Presentation API 후속 request mapping](docs/guides/presentation_followup_api_request_mapping.md)

## 커밋하지 않는 문서

초안, 회의 메모, 실험 계획, 개인 인수인계 메모, 테스트 산출물처럼 Git에 커밋하지 않을 자료는
gitignore 대상인 `local/` 아래에 둔다. 문서 초안의 기본 위치는 `local/docs/`, 실행 결과의 기본 위치는
`local/output/`이다.

`local/` 자료를 공식 정본으로 링크하지 않는다. 팀이 계속 참고해야 하는 내용은 검토 후
`docs/architectures/`, `docs/agents/`, `docs/guides/` 중 성격에 맞는 위치로 옮긴다.
