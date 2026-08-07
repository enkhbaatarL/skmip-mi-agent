# Model Parameter rollout repository map

Use paths relative to the repository root. Verify every path still exists before using it.

## Required first reads

- `AGENTS.md`
- `.claude/rules/python-conventions.md` for Python changes
- `docs/architectures/project_directory_structure.md` for ownership or boundary changes
- `apps/agents/model_parameter_agent/docs/01_MODEL_PARAMETER_AGENT_OVERVIEW.md`
- `apps/agents/model_parameter_agent/docs/03_MODEL_PARAMETER_AGENT_DB_SPEC.md`
- `apps/agents/model_parameter_agent/docs/05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md`
- `apps/agents/model_parameter_agent/docs/06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md`

## Canonical and DB artifacts

| Path | Role | Safety note |
|---|---|---|
| `scripts/model_parameter/prepare_canonical.py` | Capture configured DB and generate the dated snapshot/canonical fixture | Current code is hard-coded to v1/date. Default snapshot creation is exclusive. Run only before apply with resolved project settings; do not replace an applied snapshot. |
| `scripts/model_parameter/snapshots/external_dev_before_20260807.json` | Immutable v1 pre-apply evidence | Copy/version for a future release; do not rewrite history. |
| `scripts/model_parameter/model-parameter-canonical-v1.json` | Current machine-readable authority | Create a new version for a changed canonical state. |
| `scripts/model_parameter/apply_canonical.py` | Transactional preflight and optional commit | Default rolls back; only `--apply` commits. Supports `--canonical` and `--snapshot`. |
| `scripts/model_parameter/apply_model_parameter_canonical_v1.sql` | Explicit MySQL 8 commit procedure | Verify in an isolated DB first; use only one commit path on the target DB. |
| `tests/manual/model_parameter_agent/verify_canonical_sql_mysql.py` | Destructive isolated static-SQL verifier | Drops/seeds three tables and accepts only DB names matching `model_parameter_sql_verify*`; still confirm the host is disposable. |

Load project settings without exposing secrets. A typical pre-apply capture form is:

```bash
poetry run dotenv -f envs/.env run --no-override python scripts/model_parameter/prepare_canonical.py
```

Do not use `--replace-snapshot` unless the snapshot has never been applied and the user explicitly authorizes replacing it.

## Runtime and resource artifacts

- `envs/config.yaml`
- `devops/k8s/configmap.yaml`
- `apps/common/configs/config.py`
- `apps/agents/model_parameter_agent/resources/basecase/`
- `apps/agents/model_parameter_agent/resources/lut/`
- `apps/agents/model_parameter_agent/utils/resource_manifest.py`
- `apps/agents/model_parameter_agent/utils/resource_bootstrap.py`
- `apps/agents/model_parameter_agent/utils/lut/adapters.py`
- `apps/agents/model_parameter_agent/utils/lut/catalog.py`
- `apps/agents/model_parameter_agent/utils/lut/registry.py`
- `apps/agents/model_parameter_agent/utils/lut/runtime.py`
- `apps/agents/model_parameter_agent/utils/parameter_mapping.py`
- `apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py`
- `apps/agents/model_parameter_agent/prompts/model_parameter_proposal.py`

Keep LUT objects under the established prefixes `fundamental_model_artifact/LUT/demand/...` and `fundamental_model_artifact/LUT/supply/supply_bc/...`.

## Workbook, docs, and consistency artifacts

- `scripts/model_parameter/sync_mapping_workbook.py`
- `apps/agents/model_parameter_agent/resources/mapping/`
- `apps/agents/model_parameter_agent/resources/mapping/archive/README.md`
- `apps/agents/model_parameter_agent/resources/Model_Parameter_Base_Case_Mapping.md`
- `apps/agents/model_parameter_agent/docs/01_MODEL_PARAMETER_AGENT_OVERVIEW.md` through `07_MODEL_PARAMETER_AGENT_COMPREHENSION_QUIZ.md`
- `README.md`
- `tests/automated/test_model_parameter_canonical_consistency.py`
- `tests/reports/model_parameter_agent/`

Generate and check the workbook with:

```bash
poetry run python scripts/model_parameter/sync_mapping_workbook.py
poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only
```

## Current v1 baseline (dated 2026-08-07)

Use this only to detect regression while maintaining v1. The current fixture contains 21 master rows, 129 dimension mappings, and 10 active parameters: GDP, PMI, PowerMix, Temperature, Population, HurricaneIntensity, LiqProdAdjustment, LiqUtilAdjustment, PipelineAdjustment, and SupplyDisruption. Mapping methods total 35 direct, 6 routing, 55 indirect, and 33 na.

For any v2 or later rollout, derive all expected sets and counts from the new approved canonical fixture and update the tests, SQL verifier, workbook, and documents together.
