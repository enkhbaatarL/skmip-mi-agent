# SKMIP MI Agent

시나리오 그룹 기반 MI 시나리오 생성/검증/Signpost 생성 API 서비스입니다.

## Current Agent Structure

```text
apps/
├── agents/
│   ├── scenario_group_agent/
│   │   ├── flows/
│   │   │   ├── create_scenarios/
│   │   │   ├── validate_scenarios/
│   │   │   ├── create_signposts/
│   │   │   └── confirm_generation/
│   │   ├── schemas/
│   │   └── subgraphs/
│   │       ├── scenario_generation/
│   │       └── signpost_generation/
├── common/
│   ├── configs/
│   ├── runtime/
│   └── values/
├── connectors/
│   ├── callback/
│   ├── http/
│   ├── llm/
│   └── vdb/
└── persistence/
    ├── event/
    ├── scenario_group/
    ├── scenario/
    ├── signpost/
    └── schemas/
```

`scenario_group_agent`가 시나리오 생성/검증/Signpost 생성 흐름의 기준 구현입니다.
공유 DB ORM, repository, service는 `apps.persistence`에서 소유합니다.

## Key Docs

- [Agent Guide](AGENTS.md)
- [Project Directory Structure](docs/architectures/project_directory_structure.md)
- [Scenario Group Agent Flow Pipeline](docs/architectures/scenario_group_agent_flow_pipeline.md)
- [Scenario Group Agent API Request/Response](docs/architectures/scenario_group_agent_api_request_response.md)

## Development

```bash
pytest tests/automated/test_scenario_group_agent_contract.py
pytest tests/automated/test_scenario_group_pipeline_contract.py
pytest tests/automated/test_scenario_group_dimension_values.py
pytest tests/automated/test_scenario_group_validation_review.py
```

Smoke checks:

```bash
python -m compileall apps tests
python -c "import main"
```
