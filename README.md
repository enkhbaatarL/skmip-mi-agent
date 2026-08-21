# SKMIP MI Agent

시나리오 그룹 생성·검증·Signpost와 수급모델 파라미터 제안·확정을 제공하는 MI Agent API 서비스입니다.

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
│   │   ├── schemas/          # shared or flow-less API schema
│   │   └── subgraphs/
│   │       ├── scenario_generation/
│   │       ├── scenario_review/
│   │       └── signpost_generation/
│   └── model_parameter_agent/
│       ├── flows/             # proposal / confirmation
│       ├── utils/lut/         # LUT adapter, catalog, exact slot
│       └── resources/         # Basecase, LUT, canonical mapping
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
    ├── schema_base.py
    └── enums.py
```

`scenario_group_agent`가 시나리오 생성/검증/Signpost 생성 흐름의 기준 구현입니다.
공유 DB ORM, repository, service와 persistence DTO는 `apps.persistence`에서 소유합니다.

Model Parameter Agent의 공용 master는 21행·활성 16개입니다. v1/v3는 공유 dimension mapping 129행(35 direct, 6 routing, 55 indirect, 33 na)에서 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`, `HurricaneIntensity`, `LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`, `SupplyDisruption` 10개까지 후보로 만들 수 있습니다. v4는 이 mapping을 조회하지 않고 선택된 dimension value의 Lever state와 active Lever catalog binding으로 독립적으로 후보를 만듭니다. v4 master 21행·활성 16개, Impact Lever 16개·binding occurrence 20건, catalog와 기존 v4 Scenario/proposal 결과는 이 v1/v3 mapping 정비의 변경 대상이 아닙니다. 활성 16개 중 LUT-backed 10개는 Basecase 우선/LUT fallback을 사용하고, `User-Adjusted Gas Demand`, `RegasAdjustment`, `PNG Contract Volume`, `RemainingUnrestrictedAmount`, `ShippingCost`, `VolumeCancelled`는 검증된 Basecase exact slot에서만 실행합니다. 공개 proposal/confirmation endpoint와 payload shape은 바뀌지 않습니다.

## Key Docs

- [Agent Guide](AGENTS.md)
- [Project Directory Structure](docs/architectures/project_directory_structure.md)
- [Scenario Group Agent Flow Pipeline](docs/architectures/scenario_group_agent_flow_pipeline.md)
- [Scenario Group Agent API Request/Response](docs/architectures/scenario_group_agent_api_request_response.md)
- [Model Parameter Agent Overview](apps/agents/model_parameter_agent/docs/01_MODEL_PARAMETER_AGENT_OVERVIEW.md)
- [Model Parameter Canonical Mapping](apps/agents/model_parameter_agent/resources/Model_Parameter_Base_Case_Mapping.md)
- [Model Parameter v4 Master Canonical](scripts/model_parameter/model-parameter-canonical-v4.json)
- [Model Impact Lever v4 Canonical](scripts/model_parameter/model-impact-lever-canonical-v4.json)
- [Model Parameter v4 Canonical Workbook](apps/agents/model_parameter_agent/resources/mapping/260813_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.xlsx)
- [Model Parameter Canonical Rollout Skill](.claude/skills/rollout-model-parameters/SKILL.md)
- [Model Parameter Release Verification Skill](.claude/skills/verify-model-parameter-release/SKILL.md)

## Development

```bash
pytest tests/automated/test_scenario_group_agent_contract.py
pytest tests/automated/test_scenario_group_pipeline_contract.py
pytest tests/automated/test_scenario_group_dimension_values.py
pytest tests/automated/test_scenario_group_validation_review.py
pytest tests/automated/test_model_parameter_canonical_consistency.py
pytest tests/automated/test_model_parameter_lut_pipeline.py
poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only
```

Smoke checks:

```bash
python -m compileall apps tests
python -c "import main"
```
