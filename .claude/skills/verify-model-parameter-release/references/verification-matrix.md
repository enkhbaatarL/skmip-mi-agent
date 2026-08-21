# Model Parameter release verification matrix
Run commands from the repository root. Derive future expectations from the selected canonical fixture rather than copying the dated v1 counts below.

## Version-aware release route

Resolve the selected Model Parameter canonical before running any DB command. Generic v1 filenames are legacy paths, not fallbacks for newer releases.

| Canonical | Target DB runner | Disposable static-SQL verifier | Static SQL | Legacy mapping policy |
|---|---|---|---|---|
| historical `model-parameter-canonical-v4` release replay | `scripts/model_parameter/apply_model_parameter_v4.py` against its dated 128-row snapshot-compatible state only | `tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py` | `scripts/model_parameter/apply_model_parameter_canonical_v4.sql` | Immutable 128-row release replay; do not run this dated target runner as post-maintenance acceptance on the current 129-row DB |
| v1/v3 shared mapping only | `scripts/model_parameter/apply_model_parameter_v1_v3_mapping.py` | focused runner/unit verification | not required for this minimal Python-runner rollout | v1 fixture `dimension_mappings` owns the 129-row target; current v4 master/Lever must match and remain unchanged |
| full legacy `model-parameter-canonical-v1` maintenance | `scripts/model_parameter/apply_canonical.py` | `tests/manual/model_parameter_agent/verify_canonical_sql_mysql.py` | `scripts/model_parameter/apply_model_parameter_canonical_v1.sql` | Historical full-master path; do not use for mapping-only rollout |
| Later version | Explicit compatible version runner required | Explicit compatible version verifier required | Matching versioned SQL required | Derive from its approved snapshot; never fall back to v1 |

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
| `v3-v4-engine-comparison` | confirmed-input export, proposal comparison, LNG engine report or campaign contract | `test_model_parameter_confirmed_input_export.py`, `test_model_parameter_v3_v4_comparison.py`, `test_model_parameter_v3_v4_engine_report.py` |

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

The selected verifier drops and recreates its test tables. Confirm the host is disposable in addition to satisfying the verifier's DB-name regex.

For v4, verify master, legacy dimension mapping, Impact Lever and active scenario template with the v4 snapshot:

```bash
poetry run python tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py \
  --host 127.0.0.1 \
  --port <disposable-port> \
  --user <test-user> \
  --password <test-only-password> \
  --database model_parameter_v4_sql_verify_<run-id>
```

Require first apply, semantic idempotency, master/Impact-Lever precondition rollback, post-invariant rollback, and exact preservation of the historical 128-row seed. This verifier is a disposable historical release replay, not evidence that the dated v4 target runner accepts the current 129-row DB.

For legacy v1 maintenance only:

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

Default dry-run performs DML and invariant/read-back checks inside a transaction and then rolls back. The following v4 command is retained for the dated 128-row release state only; do not run it as current post-maintenance acceptance after the shared mapping becomes 129 rows:

```bash
poetry run python scripts/model_parameter/apply_model_parameter_v4.py
```

Commit v4 only after target/diff authorization:

```bash
poetry run python scripts/model_parameter/apply_model_parameter_v4.py --apply
```

The dated v4 runner may update only the 21-row parameter master and 16-row Impact Lever catalog, but its precondition intentionally pins the 128-row snapshot. A future master/Lever rollout from the current 129-row state requires a new snapshot and versioned runner rather than weakening this historical guard.

For the approved v1/v3 mapping-only rollout, dry-run and commit with `scripts/model_parameter/apply_model_parameter_v1_v3_mapping.py`. Require 129 rows, method counts 35/6/55/33, the exact ten-candidate set, no FK/template/natural-key violation, and exact preservation of v4 master, Impact Lever catalog and hydrated checksum. Run the same command again without `--apply` after commit, then compare SELECT-only v4 runtime/persistence fingerprints with `tests/manual/model_parameter_agent/capture_v4_mapping_invariance.py`.

For legacy v1 maintenance only:

```bash
poetry run python scripts/model_parameter/apply_canonical.py
```

The legacy runner accepts explicit v1-compatible files:

```bash
poetry run python scripts/model_parameter/apply_canonical.py \
  --canonical <canonical-json> \
  --snapshot <pre-apply-snapshot>
```

Commit legacy v1 only after target/diff authorization:

```bash
poetry run python scripts/model_parameter/apply_canonical.py --apply
```

Then rerun the target DB dry-run and read-back. Do not present a local mocked unit-suite rerun as proof of the applied DB
state. Use the matching versioned static MySQL procedure as an alternative commit path, never as an additional target-DB test.

## Real proposal and confirmation checks

Use `.claude/skills/model-parameter-agent-test/SKILL.md` and its maintained runners:

- `tests/manual/model_parameter_agent/evaluate_event_type_proposals.py`
- `.claude/skills/model-parameter-agent-test/scripts/run_single_scenario_report.py`

Select scenarios dynamically from the current DB mapping. Do not duplicate that skill's command and report contract here.

For v3/v4 LNG engine comparisons, additionally follow
`references/v3-v4-lng-comparison.md` and the nested
`tests/lng_model/skills/evaluate-lng-price-tags/SKILL.md`. Run the comparison suite before executing external workbooks:

```bash
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q \
  tests/automated/test_model_parameter_confirmed_input_export.py \
  tests/automated/test_model_parameter_v3_v4_comparison.py \
  tests/automated/test_model_parameter_v3_v4_engine_report.py
```

## Acceptance evidence

| Area | Required evidence |
|---|---|
| Canonical | Full fixture comparison; version, snapshot, active set, counts, audit rules |
| Config/resources | YAML/ConfigMap parity; one classification per CSV; active startup and exact catalog slots |
| Runtime | Compression round-trip; exact effective Step3 reference; slot/byte guards before LLM |
| Workbook/docs | Current workbook matches fixture; archive is historical; docs contain no stale active state or unverified claims |
| Static SQL | Selected version/verifier, two applies, semantic idempotency, precondition rollback, post-invariant rollback, teardown; v4 also proves transaction-entry mapping preservation |
| Target DB | Version-aware dry-run, authorized single commit path, full read-back, post-apply dry-run; mapping-only rollout proves v4 master/Lever/checksum invariance |
| E2E | DB-derived candidates, proposal persistence, empty-confirm rollback, confirm, reconfirm, IDs/tokens/timing |
| Regression | `core-smoke`, affected named domain suites, then one final full `tests/automated` run; suite별 counts |

## Current shared mapping baseline
As of 2026-08-13, v1/v3 share 129 mappings with 35 direct / 6 routing / 55 indirect / 33 na and an exact ten-parameter direct/routing candidate set. The shared v4 master remains 21 rows/16 active and v4 continues to use only the Impact Lever catalog. The completed 2026-08-07 baseline reported 60,420 LUT records; keep that number historical unless resource validation is rerun.
