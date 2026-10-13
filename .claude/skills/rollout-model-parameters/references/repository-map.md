# Model Parameter v4 rollout repository map

Use paths relative to the repository root and verify that each path still exists before using it. This map covers only the canonical v4 Model Parameter path consumed by Scenario API v4 `multi_event_model_lever_dimensions` groups.

## Required first reads

- `AGENTS.md`
- `.claude/rules/python-conventions.md` for Python changes
- `docs/architectures/project_directory_structure.md` for ownership or boundary changes
- `docs/agents/model_parameter_agent/01_MODEL_PARAMETER_AGENT_OVERVIEW.md`
- `docs/agents/model_parameter_agent/02_MODEL_PARAMETER_AGENT_API_SPEC.md`
- `docs/agents/model_parameter_agent/03_MODEL_PARAMETER_AGENT_DB_SPEC.md`
- `docs/agents/model_parameter_agent/05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md`
- `docs/agents/model_parameter_agent/06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md`
- `docs/agents/scenario_group_agent/02_SCENARIO_GROUP_AGENT_API_SPEC.md` when Scenario API inputs change
- `docs/agents/scenario_group_agent/03_SCENARIO_GROUP_AGENT_FLOW.md` when v4 generation or validation changes

## Canonical v4 and DB artifacts

| Path | Role | Safety boundary |
|---|---|---|
| `scripts/model_parameter/model-parameter-canonical-v4.json` | v4 parameter-master authority, including activation and Basecase metadata | Use together with the Impact Lever fixture; do not derive v4 candidates from embedded or adjacent legacy mapping data. |
| `scripts/model_parameter/model-impact-lever-canonical-v4.json` | v4 Impact Lever hierarchy, parameter bindings, support state, catalog version, and hydrated checksum authority | Binding parameter names and active states must agree with the parameter fixture. |
| `scripts/model_parameter/capture_model_parameter_v4_external_snapshot.py` | Existing versioned pre-apply snapshot pattern | A new rollout needs a new immutable output/version; never overwrite or regenerate earlier evidence. |
| `scripts/model_parameter/snapshots/` | Versioned immutable pre-apply evidence | Each snapshot belongs only to its matching release and must never be overwritten or assumed to be a later rollout's baseline. |
| `scripts/model_parameter/generate_model_parameter_v4_sql.py` | Generates the matching v4 MySQL procedure from canonical inputs | Generated SQL must retain snapshot/final preconditions and protected-table invariants. |
| `scripts/model_parameter/apply_model_parameter_v4.py` | Existing transactional v4 replay | Use only when the live state matches its recorded snapshot or exact final-state precondition; create a versioned successor for a new baseline. |
| `scripts/model_parameter/apply_model_parameter_canonical_v4.sql` | Existing explicit MySQL v4 commit procedure | Use only the commit path selected and authorized for the matching release. |
| `tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py` | Disposable-MySQL verifier for the matching v4 procedure | Release acceptance owns execution; its database-name guard does not make a shared DB disposable. |

SQL in this repository is implementation/reference material. Migration ownership remains in the sibling `skmip-mi-agent-mgmt` repository.

## Protected legacy mapping invariant

- `tmm_mi_model_param_dimension_map` is neither a canonical v4 target nor a v4 candidate source.
- Capture all rows and creation-audit fields, compute a deterministic semantic digest, and require exact preservation across successful apply, idempotent replay, dry-run rollback, and every forced failure path.
- Do not run a mapping-only or older full-master workflow as a fallback for a v4 rollout.
- Scenario API v4 and Model Parameter v4 must fail closed when their Lever/catalog inputs are missing or invalid; they must not consult representative Event Type mapping, composite `sourceRefs`, or historical `lever_mappings`.

## Scenario API v4 inputs and ownership

| Path | Role |
|---|---|
| `apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/v4_flow.py` | Creates `multi_event_model_lever_dimensions` groups and pins catalog version/checksum. |
| `apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/v4_schema.py` | Defines v4 Event analysis, dimensions, selected-value Lever states, lineage, and catalog-backed validation. |
| `apps/agents/scenario_group_agent/flows/create_multi_event_scenarios/v4_nodes.py` | Hydrates and persists v4 generation artifacts. |
| `apps/agents/scenario_group_agent/flows/validate_scenarios/v4_validation.py` | Validates persisted v4 Scenario content against the v4 contract. |
| `apps/agents/scenario_group_agent/persistence/model_impact_lever_service.py` | Scenario-generation access to the active Impact Lever catalog. |
| `apps/persistence/model_impact_lever/` | Shared Impact Lever models, schema, repository, and service. |
| `apps/persistence/scenario_group/` | Persists generation strategy and catalog version/checksum pins. |
| `apps/agents/model_parameter_agent/flows/propose_parameters/validation.py` | Enforces v4 strategy, semantic-empty, and proposal-stage validation. |
| `apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py` | Loads v4 context and drives the proposal stages. |
| `apps/agents/model_parameter_agent/utils/parameter_mapping.py` | Matches selected-value Lever states to active catalog bindings and executable parameter definitions. |

Treat these as first-class v4 inputs and invariants:

- `api_version=v4` and `generation_strategy=multi_event_model_lever_dimensions`;
- one to five ordered active group-to-Event relations;
- group `impact_catalog_version` and `impact_catalog_checksum` equal to the hydrated active catalog;
- one selected value per dimension, with source Event/path/uncertainty lineage;
- `primary_lever_code`, `primary_impact_lever_id`, and selected-value `lever_states` whose code/ID, role, direction, support state, and bindings validate against the catalog;
- active parameter definitions and exact Basecase/LUT slots after the separate runtime allow-list gate.

When the hydrated checksum changes, existing v4 groups remain pinned to their original catalog. New groups must be created through the owning Scenario API flow; a Model Parameter rollout must not rewrite their stored inputs or pins.

## Runtime resources, catalog, and guards

- `apps/agents/model_parameter_agent/new_resources/` — incoming user-owned staging; not a runtime or manifest root
- `apps/agents/model_parameter_agent/new_resources/lut/` — future LUT drop location; absence is valid and staged files require explicit validation/promotion
- `envs/config.yaml`
- `devops/k8s/model-parameter-configmap.yaml` — locally supplied, Git-ignored Neuro Model Parameter configuration; never commit it
- `devops/k8s/configmap.yaml` — shared multi-Agent Kubernetes example; not the Neuro Model Parameter authority
- `apps/common/configs/config.py`
- `apps/agents/model_parameter_agent/constants.py`
- `apps/agents/model_parameter_agent/resources/basecase/`
- `apps/agents/model_parameter_agent/resources/lut/`
- `apps/agents/model_parameter_agent/utils/resource_manifest.py`
- `apps/agents/model_parameter_agent/utils/resource_bootstrap.py`
- `apps/agents/model_parameter_agent/utils/resource_runtime.py`
- `apps/agents/model_parameter_agent/utils/runtime_cache.py`
- `apps/agents/model_parameter_agent/utils/lut/adapters.py`
- `apps/agents/model_parameter_agent/utils/lut/catalog.py`
- `apps/agents/model_parameter_agent/utils/lut/registry.py`
- `apps/agents/model_parameter_agent/utils/lut/runtime.py`
- `apps/agents/model_parameter_agent/prompts/model_parameter_proposal.py`

Never recursively merge `new_resources/` into `resources/`. Inventory staged files read-only, exclude `.DS_Store` and `~$*`, detect Unicode-normalized/basename collisions, and retain source digests. Only an explicitly approved rollout may copy a validated LUT into canonical `resources/lut/` and then update every manifest, adapter, config, fixture, workbook, test, and document consumer. No staged LUT yet is a normal `NOT PRESENT` state, not a release failure.

Keep LUT objects under the established `fundamental_model_artifact/LUT/demand/...` and `fundamental_model_artifact/LUT/supply/supply_bc/...` prefixes. Keep raw active Impact Lever coverage, runtime-allowed proposal coverage, and exact Basecase/LUT slot coverage as three separate reported sets; derive each set from current canonical/config/runtime evidence rather than a copied historical count.

## Workbook, docs, and deterministic tests

- `scripts/model_parameter/sync_mapping_workbook.py`
- `apps/agents/model_parameter_agent/resources/mapping/`
- `apps/agents/model_parameter_agent/resources/mapping/archive/README.md`
- `apps/agents/model_parameter_agent/resources/Model_Parameter_Base_Case_Mapping.md`
- `docs/agents/model_parameter_agent/01_MODEL_PARAMETER_AGENT_OVERVIEW.md` through `07_MODEL_PARAMETER_AGENT_COMPREHENSION_QUIZ.md`
- `README.md`
- `tests/automated/test_model_parameter_canonical_consistency.py`
- `tests/automated/test_model_impact_lever_canonical.py`
- `tests/automated/test_model_parameter_resource_sync.py`
- `tests/automated/test_model_parameter_lut_pipeline.py`
- `tests/automated/test_model_parameter_v4_basecase.py`
- `tests/automated/test_model_parameter_v4_proposal.py`
- `tests/automated/test_v4_multi_event_model_lever_scenarios.py`
- `tests/automated/test_model_parameter_multi_event_quality.py`
- `tests/automated/test_model_parameter_runner_common.py`
- `tests/manual/model_parameter_agent/evaluate_multi_event_quality.py`
- `tests/manual/model_parameter_agent/runner_common.py`
- `tests/reports/model_parameter_agent/`

Generate and check the workbook with:

```bash
poetry run python scripts/model_parameter/sync_mapping_workbook.py
poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only
```

The workbook must expose the v4 master, Impact Lever bindings, catalog version/checksum, resource support, and conflicts. Any legacy mapping sheet is a labeled view of captured invariant state, not a desired rollout matrix.

## Verification ownership

- `.claude/skills/verify-model-parameter-release/SKILL.md` owns release acceptance: canonical/resource/workbook consistency, full regressions, disposable SQL verification, target DB dry-run or authorized commit, idempotency, rollback, read-back, and the integrated release report.
- `.claude/skills/model-parameter-multi-event-quality/SKILL.md` owns live v4 discovery and proposal/confirmation quality: write authorization, eligible Scenario selection, LLM/token/trace evidence, persistence, retry evidence, coverage, and quality reporting.
- This rollout skill owns implementation and focused local checks only. It must not duplicate those acceptance or live-quality procedures or infer their PASS from repository consistency.
