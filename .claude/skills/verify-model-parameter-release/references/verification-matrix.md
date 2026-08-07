# Model Parameter release verification matrix
Run commands from the repository root. Derive future expectations from the selected canonical fixture rather than copying the dated v1 counts below.

## Non-mutating checks

Validate workbook, canonical fixture, manifests, LUT behavior, prompt guards, report contracts, and persistence/API contracts:

```bash
poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only
poetry run pytest -q \
  tests/automated/test_model_parameter_agent_contract.py \
  tests/automated/test_model_parameter_canonical_consistency.py \
  tests/automated/test_model_parameter_lut_domain.py \
  tests/automated/test_model_parameter_lut_pipeline.py \
  tests/automated/test_model_parameter_report_scope.py \
  tests/automated/test_model_parameter_resource_sync.py
```

After focused checks pass, run:

```bash
poetry run pytest -q tests/automated
git diff --check
```

Run Ruff/compile checks only over changed Python paths. Use `git diff --name-only` to build the reviewed file set; do not use a formatter over unrelated dirty files.

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

Then rerun the dry-run command and focused tests. Use the static MySQL procedure as an alternative commit path, never as an additional target-DB test.

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
| Regression | Focused Model Parameter suite and full `tests/automated` suite |

## Current v1 comparison baseline
As of 2026-08-07, `model-parameter-canonical-v1` expects 21 master rows, 129 mappings, 10 active parameters, and mapping method counts 35 direct / 6 routing / 55 indirect / 33 na. The completed baseline reported 60,420 active LUT records. Recompute these values from artifacts for any later version; do not make a new release pass by preserving obsolete v1 numbers.
