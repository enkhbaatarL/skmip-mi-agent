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
| `scripts/model_parameter/capture_model_parameter_v4_external_snapshot.py` | Capture the configured external DB's dated pre-v4 state | Read-only transaction with unconditional rollback; dated output is exclusive and must not be overwritten. |
| `scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json` | Immutable v4 pre-apply evidence | Contains master, external AS-IS legacy mapping, Impact Lever and active template digests; do not regenerate from final state. |
| `scripts/model_parameter/model-parameter-canonical-v4.json` | Current v4 parameter authority | Master 21/active 16; embedded 128 legacy rows preserve the pre-v4 snapshot and are not the current shared mapping target. |
| `scripts/model_parameter/model-impact-lever-canonical-v4.json` | Current v4 Lever authority | Catalog v4 and hydrated checksum; apply atomically with the parameter master. |
| `scripts/model_parameter/apply_model_parameter_v4.py` | Historical v4 transactional replay | Pins the dated 128-row snapshot. Do not use as post-maintenance acceptance on the current 129-row DB; a later master/Lever rollout needs a new snapshot and versioned runner. |
| `scripts/model_parameter/apply_model_parameter_canonical_v4.sql` | Explicit v4 MySQL 8 commit procedure | Verify with the matching v4 isolated verifier; use only one commit path on the target DB. |
| `tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py` | Destructive isolated v4 static-SQL verifier | Seeds four evidence tables and accepts only DB names matching `model_parameter_v4_sql_verify*`; still confirm the host is disposable. |
| `scripts/model_parameter/model-parameter-canonical-v1.json` | Current v1/v3 shared mapping authority | Use only its 129-row `dimension_mappings` for the shared mapping rollout; do not overwrite the v4 master with its historical active-10 master. |
| `scripts/model_parameter/apply_model_parameter_v1_v3_mapping.py` | Mapping-only transactional runner | Validates live v4 master/Lever first, then changes only the shared mapping to 129 rows; default rolls back and `--apply` commits. |
| `scripts/model_parameter/prepare_canonical.py`, `apply_canonical.py`, `apply_model_parameter_canonical_v1.sql` | Legacy full-v1 rollout path | Historical full-master path only; do not use it for the mapping-only rollout or as fallback for v4. |
| `tests/manual/model_parameter_agent/verify_canonical_sql_mysql.py` | Legacy v1 destructive verifier | Use only for the versioned v1 path and a disposable `model_parameter_sql_verify*` database. |

Load project settings without exposing secrets. The v4 pre-apply capture form is:

```bash
poetry run dotenv -f envs/.env run --no-override python \
  scripts/model_parameter/capture_model_parameter_v4_external_snapshot.py
```

The v4 capture refuses to overwrite an existing snapshot. For any later release, create a new dated capture path instead of replacing v4 evidence.

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

## Current v4 baseline (dated 2026-08-13)

The current shared DB keeps the v4 master at 21 rows/16 active and the active Impact Lever catalog at 16 rows. v1/v3 use 129 shared dimension mappings: 35 direct, 6 routing, 55 indirect and 33 na. Their exact direct/routing candidate set contains GDP, PMI, PowerMix, Temperature, Population, HurricaneIntensity, LiqProdAdjustment, LiqUtilAdjustment, PipelineAdjustment and SupplyDisruption. v4 does not query this table for proposal candidates and mapping-only rollout must leave the v4 master, catalog, scenarios and proposal results unchanged.

The dated v4 snapshot's 128 mappings and 25/2/55/46 method counts are historical pre-change evidence, not the current DB state. The v1 fixture's 129-row `dimension_mappings` is the approved shared mapping source, while its master section remains historical and must not replace the current v4 master. For any later rollout, update the runner, tests, workbook and documents together from the newly approved fixture.
