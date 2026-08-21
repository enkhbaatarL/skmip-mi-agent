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

Model Parameter Agent의 공용 master 21행·활성 16개는 그대로입니다. 리소스 capability는 LUT-backed 10개와 Basecase-only 6개(`User-Adjusted Gas Demand`, `RegasAdjustment`, `PNG Contract Volume`, `RemainingUnrestrictedAmount`, `ShippingCost`, `VolumeCancelled`)로 유지됩니다. v1/v3 공유 dimension mapping 129행(35 direct, 6 routing, 55 indirect, 33 na)의 direct/routing이 도달하는 raw 후보는 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`, `HurricaneIntensity`, `LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`, `SupplyDisruption` 10개입니다. v4는 이 mapping을 조회하지 않고 선택된 dimension value의 Lever state와 active Lever catalog binding으로 고유 활성 parameter 16개의 raw 후보를 독립적으로 만듭니다.

모든 버전의 **신규 proposal runtime allow-list**는 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment` 5개입니다. Agent는 raw matching 후 Step1.5·LLM 호출·proposal 행 생성 전에 이 범위를 적용하며, allow-list 밖의 후보만 남으면 비동기 API도 `PROCESSING` 행 없이 `INVALID_REQUEST`로 거절합니다. 이 제한은 DB master·mapping, v4 Lever catalog/checksum, Basecase/LUT 설정·resource bootstrap, canonical JSON/SQL/workbook, 기존 저장 데이터와 confirmation 계약을 변경하지 않습니다. 공개 proposal/confirmation endpoint와 payload shape도 그대로입니다.

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
