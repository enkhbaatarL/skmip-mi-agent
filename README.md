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
│   │   ├── persistence/
│   │   │   ├── event/
│   │   │   ├── scenario_group/
│   │   │   ├── scenario/
│   │   │   └── signpost/
│   │   ├── schemas/
│   │   └── subgraphs/
│   │       ├── scenario_generation/
│   │       └── signpost_generation/
├── common/
│   ├── configs/
│   ├── runtime/
│   └── values/
└── connectors/
    ├── callback/
    ├── http/
    ├── llm/
    └── vdb/
```

`scenario_group_agent`가 시나리오 생성/검증/Signpost 생성 흐름의 기준 구현입니다.
MI Event ORM도 `scenario_group_agent.persistence.event`에서 소유합니다.

## Key Docs

- [Architecture Index](docs/architectures/index.md)
- [Scenario Group Agent Directory Structure](docs/architectures/scenario_group_agent_directory_structure.md)
- [Scenario Group Agent Logic](docs/architectures/scenario_group_agent_logic.md)

## Development

```bash
pytest tests/test_scenario_group_agent_contract.py
pytest tests/test_scenario_group_pipeline_contract.py
pytest tests/test_scenario_group_dimension_values.py
pytest tests/test_scenario_group_validation_review.py
```

Smoke checks:

```bash
python -m compileall apps tests
python -c "import main"
```
