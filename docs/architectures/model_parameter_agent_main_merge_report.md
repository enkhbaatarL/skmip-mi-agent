# Model Parameter Agent Main Merge Report

## 작업 기준

- 작업 브랜치: `feature/model-parameter-db-proposal-main-merge`
- 기준 proposal 커밋: `6684cbd`
- merge 대상: `origin/main` `4c2f241`
- 목적: proposal 브랜치와 main 브랜치는 변경하지 않고, PR 준비용 로컬 브랜치에서 main 병합 및 conflict 해결

## Conflict 해결 원칙

- `apps/agents/model_parameter_agent/` 하위 기능 로직은 proposal 브랜치 내용을 우선했다.
- 그 외 디렉토리는 main 브랜치 내용을 우선했다.
- main의 `docs/architectures/project_directory_structure.md` 기준에 맞추기 위해 model parameter agent의 DB persistence와 flow schema/state 위치를 조정했다.
- 파라미터 제안 기능 동작에 필요한 공용 wiring은 최소 범위로 반영했다.

## Conflict 파일별 처리

- `.vscode/launch.json`
  - main 버전을 선택했다.
  - main의 `.venv` 기반 launch/preLaunchTask 설정을 유지했다.
- `apps/connectors/llm/llm_client.py`
  - main 버전을 선택했다.
  - main의 request별 `httpx.AsyncClient` 생성/종료 방식과 `http_verify`, timeout, connection limit 설정을 유지했다.
- `apps/persistence/event/models.py`
  - main 버전을 선택했다.
  - event ORM은 main의 `apps/persistence/event` 소유 구조를 기준으로 유지했다.
- `envs/config.yaml`
  - main 버전을 선택했다.
  - main의 `http_max_concurrency: 20` 설정을 유지했다.
- `apps/common/configs/database/application_tables.py`
  - main 버전을 기준으로 선택했다.
  - model parameter proposal 기능의 schema validation을 위해 `apps.persistence.model_input.models`의 3개 테이블만 추가 등록했다.

## 구조 변경

- DB ORM/repository를 agent 하위에서 공용 persistence 계층으로 이동했다.
  - 기존: `apps/agents/model_parameter_agent/persistence/model_input/models.py`
  - 기존: `apps/agents/model_parameter_agent/persistence/model_input/repository.py`
  - 변경: `apps/persistence/model_input/models.py`
  - 변경: `apps/persistence/model_input/repository.py`
- agent 유스케이스 service를 scenario_group_agent 표준처럼 agent-local service 파일로 이동했다.
  - 기존: `apps/agents/model_parameter_agent/persistence/model_input/service.py`
  - 변경: `apps/agents/model_parameter_agent/persistence/model_input_service.py`
- flow 전용 DTO/state를 `flows/propose_parameters/` 아래로 이동했다.
  - 기존: `apps/agents/model_parameter_agent/schemas/propose_parameters.py`
  - 변경: `apps/agents/model_parameter_agent/flows/propose_parameters/api_schema.py`
  - 기존: `apps/agents/model_parameter_agent/state.py`
  - 변경: `apps/agents/model_parameter_agent/flows/propose_parameters/state.py`
- API schema의 `ApiModel` 의존을 cross-agent 경로에서 공용 base로 변경했다.
  - 변경: `apps.persistence.schema_base.ApiModel`
- 테스트 파일을 main의 테스트 배치 기준에 맞춰 이동했다.
  - 기존: `tests/test_model_parameter_agent_contract.py`
  - 변경: `tests/automated/test_model_parameter_agent_contract.py`

## 기능 유지 사항

- `model_parameter_agent`의 candidate selection, Step1.5 candidate validation, Step2 slot proposal, Step3 value proposal 로직은 proposal 브랜치 기준을 유지했다.
- `tmm_mi_model_param_m`, `tmm_mi_model_param_dimension_map`, `tmm_mi_model_param_proposal_m` ORM과 repository 동작은 유지했다.
- 최종 proposal 저장은 `ModelInputService.save_proposal_result()` 경로를 유지하되, repository import만 `apps/persistence/model_input`으로 변경했다.
- `main.py`의 model parameter router 등록은 유지했다.

## 검증

```bash
poetry run python -m pytest tests/automated/test_model_parameter_agent_contract.py -q
```

결과:

- `63 passed`
- `11 warnings`

경고는 Pydantic v1 ForwardRef deprecation, LangGraph pending deprecation, openpyxl data validation warning으로 테스트 실패와 무관하다.
