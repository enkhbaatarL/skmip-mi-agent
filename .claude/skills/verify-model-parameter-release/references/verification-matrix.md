# Model Parameter release verification matrix
Run commands from the repository root. Derive future expectations from the selected canonical fixture rather than copying the dated v1 counts below.

## Safe local test environment

Automated Model Parameter suites must not use the target DB, Object Storage, or an LLM provider. The committed
`tests/automated/.env.example` contains dummy DB settings and disables remote resource storage so
`Settings` can be imported without loading deployment credentials. Use it only for automated suites; real proposal and
target DB commands use their separately authorized environment.

## Named non-mutating suites

Start with the curated core contract gate. It covers public API/graph wiring, DB-derived mapping, representative
Basecase parsing, Step1.5/Step2/Step3 contracts, output/persistence, confirmation, and callback failure behavior. Record
the collected count from the run instead of hard-coding a historical total.

```bash
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q -m model_parameter_core \
  tests/automated/test_model_parameter_agent_contract.py
```

Then run the domain suites affected by the change:

| Suite | Run when | Membership |
|---|---|---|
| `agent-contract-detail` | API, graph, prompt, Basecase parser, persistence, confirmation, callback | `test_model_parameter_agent_contract.py` without marker filtering |
| `canonical-workbook` | canonical JSON/SQL/Excel/docs or active parameter set | workbook `--check-only` + `test_model_parameter_canonical_consistency.py` |
| `lut-runtime` | LUT adapter, catalog, exact reference, prompt guard | `test_model_parameter_lut_domain.py`, `test_model_parameter_lut_pipeline.py` |
| `resource-config-storage` | resource manifest, YAML/ConfigMap, Object Storage/cache | `test_model_parameter_resource_sync.py` |
| `report-runner` | manual runner or integrated report contract | `test_model_parameter_report_scope.py` |
| `v3-input-export` | scenario proposal XLSM export or calcChain handling | `test_model_parameter_v3_input_export.py` |
| `v3-multi-event` | v3 lineage, nullable event, v3 proposal, quality evaluation | `test_model_parameter_multi_event_contract.py`, `test_model_parameter_v3_proposal.py`, `test_model_parameter_nullable_event_consumers.py`, `test_model_parameter_multi_event_quality.py` |
| `impact-lever` | Model Impact Lever canonical/service behavior | `test_model_impact_lever_canonical.py`, `test_model_impact_lever_service.py` |

Use the same safe environment prefix for every pytest command. Examples:

```bash
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q tests/automated/test_model_parameter_agent_contract.py

poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q \
  tests/automated/test_model_parameter_canonical_consistency.py \
  tests/automated/test_model_parameter_lut_domain.py \
  tests/automated/test_model_parameter_lut_pipeline.py \
  tests/automated/test_model_parameter_resource_sync.py
```

After the core and affected-domain checks pass, run the full automated suite once on the final worktree:

```bash
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q tests/automated
git diff --check
```

`test_model_parameter_multi_event_mysql.py` is not part of the non-mutating suites. Run it only through the disposable
MySQL gate with its explicit opt-in environment. Run Ruff/compile checks only over changed Python paths. Use
`git diff --name-only` to build the reviewed file set; do not format unrelated dirty files.

## Disposable MySQL static-SQL check

The verifier drops and recreates `tmm_mi_model_param_m`, `tmm_mi_model_param_dimension_map`, and `tmm_mi_scenario_dimension_template_m`. Confirm the host is disposable in addition to satisfying its DB-name regex.

```bash
poetry run python tests/manual/model_parameter_agent/verify_canonical_sql_mysql.py \
  --host 127.0.0.1 \
  --port <disposable-port> \
  --user <test-user> \
  --password <test-only-password> \
  --database model_parameter_sql_verify_<run-id>
```

Capture:

- MySQL server version;
- first and second apply PASS;
- semantic digest equality excluding only `mod_dtm`;
- exact digest equality before/after forced precondition failure;
- exact digest equality before/after forced post-DML invariant failure;
- teardown completion.

Never use production/shared credentials in command history. Prefer ephemeral test credentials or a protected environment-specific wrapper.

## Target DB transaction checks

Default dry-run; it performs the DML and invariant/read-back checks inside a transaction and then rolls back:

```bash
poetry run python scripts/model_parameter/apply_canonical.py
```

For a future version, pass both files explicitly:

```bash
poetry run python scripts/model_parameter/apply_canonical.py \
  --canonical <canonical-json> \
  --snapshot <pre-apply-snapshot>
```

Commit only after target/diff authorization:

```bash
poetry run python scripts/model_parameter/apply_canonical.py --apply
```

Then rerun the target DB dry-run and read-back. Do not present a local mocked unit-suite rerun as proof of the applied DB
state. Use the static MySQL procedure as an alternative commit path, never as an additional target-DB test.

## Real proposal and confirmation checks

Use `.claude/skills/model-parameter-agent-test/SKILL.md` and its maintained runners:

- `tests/manual/model_parameter_agent/evaluate_event_type_proposals.py`
- `.claude/skills/model-parameter-agent-test/scripts/run_single_scenario_report.py`

Select scenarios dynamically from the current DB mapping. Do not duplicate that skill's command and report contract here.

## Acceptance evidence

| Area | Required evidence |
|---|---|
| Canonical | Full fixture comparison; version, snapshot, active set, counts, audit rules |
| Config/resources | YAML/ConfigMap parity; one classification per CSV; active startup and exact catalog slots |
| Runtime | Compression round-trip; exact effective Step3 reference; slot/byte guards before LLM |
| Workbook/docs | Current workbook matches fixture; archive is historical; docs contain no stale active state or unverified claims |
| Static SQL | Two applies, semantic idempotency, precondition rollback, post-invariant rollback, teardown |
| Target DB | Dry-run, authorized single commit path, full read-back, post-apply dry-run |
| E2E | DB-derived candidates, proposal persistence, empty-confirm rollback, confirm, reconfirm, IDs/tokens/timing |
| Regression | `core-smoke`, affected named domain suites, then one final full `tests/automated` run; suite별 counts |

## Current v1 comparison baseline
As of 2026-08-07, `model-parameter-canonical-v1` expects 21 master rows, 129 mappings, 10 active parameters, and mapping method counts 35 direct / 6 routing / 55 indirect / 33 na. The completed baseline reported 60,420 active LUT records. Recompute these values from artifacts for any later version; do not make a new release pass by preserving obsolete v1 numbers.
