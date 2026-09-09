# v4 Model Parameter release verification matrix

Run commands from the repository root. This matrix covers only the v4 canonical release and its v4 multi-event live E2E route.

## Release route

| Scope | Route | Blocking guard |
|---|---|---|
| Local artifacts and runtime | Safe automated environment and workbook check below | Must pass completely before target-DB DML |
| Incoming resource staging | Read-only inventory of `apps/agents/model_parameter_agent/new_resources/` | Never a runtime root; absent LUT is valid, claimed release files must be explicitly promoted |
| Disposable static SQL | `tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py` | Optional unless the matching v4 SQL artifact is in release scope; disposable MySQL 8 only |
| Target DB | `scripts/model_parameter/apply_model_parameter_v4.py` | Explicit dry-run authority; snapshot-compatible baseline only |
| Target DB commit | Same runner with `--apply`, or explicitly selected matching v4 SQL procedure | Separate explicit commit authority; exactly one commit path |
| Live E2E | `.claude/skills/model-parameter-multi-event-quality/SKILL.md` | v4 multi-event only; separate proposal/confirmation and LLM authority |

If the canonical, snapshot, or live baseline does not match this v4 route, stop and report the missing version-aware runner. Do not fall back to another canonical generation or generic filename.

## Safe local environment

Automated suites must not use the target DB, Object Storage, or an LLM provider. The committed `tests/automated/.env.example` supplies dummy DB settings and disables remote resource storage. Use it only for automated suites; separately authorized target DB and live E2E commands use their intended environment.

Before tests, inventory `new_resources/` without changing it. Ignore `.DS_Store` and `~$*`. Record `NOT PRESENT` when `new_resources/lut/` has no LUT; when it does, record source digests and normalized-name collisions with canonical `resources/lut/`. Tests and manifests must continue to read canonical `resources/` only. A release that claims a staged LUT but has not explicitly promoted and declared it is `FAIL`; unrelated future staging is reported as pending and left untouched.

### Core gate

```bash
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q -m model_parameter_core \
  tests/automated/test_model_parameter_agent_contract.py \
  tests/automated/test_model_parameter_multi_event_quality.py \
  tests/automated/test_model_parameter_runner_common.py
```

Record the runtime collected count; do not hard-code a historical total.

### Affected v4 domain suites

| Suite | Run when | Membership |
|---|---|---|
| `agent-contract-detail` | API, graph, prompt, persistence, confirmation, callback | `test_model_parameter_agent_contract.py` without marker filtering; `test_model_parameter_runner_common.py` |
| `canonical-workbook` | v4 canonical JSON/SQL, workbook/docs, or active set | workbook `--check-only` and `test_model_parameter_canonical_consistency.py` |
| `lut-runtime` | LUT adapter, catalog, exact reference, prompt guard | `test_model_parameter_lut_domain.py`, `test_model_parameter_lut_pipeline.py` |
| `resource-config-storage` | resource manifest, YAML/ConfigMap, Object Storage/cache | `test_model_parameter_resource_sync.py` |
| `impact-lever` | v4 Impact Lever canonical/service behavior | `test_model_impact_lever_canonical.py`, `test_model_impact_lever_service.py` |
| `v4-proposal` | v4 candidate, proposal, or Lever-to-parameter behavior | `test_model_parameter_v4_proposal.py` |
| `v4-basecase` | v4 Basecase interpretation | `test_model_parameter_v4_basecase.py` |
| `v4-multi-event` | v4 multi-event selection, ordered Event cardinality, lineage, boundary, or persistence | `test_v4_multi_event_model_lever_scenarios.py`, `test_model_parameter_multi_event_quality.py` |
| `report-runner` | v4 quality runner, shared write workflow, or integrated report contract | `test_model_parameter_multi_event_quality.py`, `test_model_parameter_runner_common.py`, `test_model_parameter_report_scope.py` |

Use the safe environment prefix for every pytest command. Example:

```bash
poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q \
  tests/automated/test_model_parameter_canonical_consistency.py \
  tests/automated/test_model_impact_lever_canonical.py \
  tests/automated/test_model_impact_lever_service.py \
  tests/automated/test_model_parameter_v4_proposal.py \
  tests/automated/test_model_parameter_v4_basecase.py \
  tests/automated/test_v4_multi_event_model_lever_scenarios.py \
  tests/automated/test_model_parameter_multi_event_quality.py \
  tests/automated/test_model_parameter_runner_common.py \
  tests/automated/test_model_parameter_report_scope.py
```

### Full pre-DML regression gate

Run this once on the final worktree before any target-DB dry-run or commit:

```bash
poetry run dotenv -f tests/automated/.env.example run --override \
  pytest -q tests/automated \
  --ignore=tests/automated/test_model_parameter_multi_event_mysql.py
git diff --check
```

`test_model_parameter_multi_event_mysql.py` is opt-in and is not part of the non-mutating gate. Run it only with its explicit integration environment against a separately confirmed disposable MySQL database. Never let inherited target/shared DB settings satisfy that opt-in.

## Optional disposable MySQL static-SQL check

Skip this section, without failing acceptance, when the matching v4 static SQL artifact is outside the release scope. When it is in scope, the verifier drops and recreates test tables, so both the server and database must be disposable and owned by the run.

```bash
poetry run python tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py \
  --host 127.0.0.1 \
  --port <disposable-port> \
  --user <test-user> \
  --password <test-only-password> \
  --database model_parameter_v4_sql_verify_<run_id>
```

The database name must match `model_parameter_v4_sql_verify(?:_[a-z0-9_]+)?`, but the name guard does not prove that the host is disposable. Never use target/shared credentials or point the verifier at the target DB.

Require and capture:

- MySQL server version;
- first apply and second semantic-idempotent apply;
- master and Impact Lever precondition rollback;
- post-DML invariant rollback;
- exact snapshot mapping preservation;
- semantic digest equality excluding only `mod_dtm`;
- exact whole-table failure-path digests;
- teardown completion.

## Target DB transaction gate

The target runner performs DML and locks before rollback even without `--apply`. Do not run either command until the exact target identity, snapshot provenance, lock window, and corresponding authority are recorded.

The dated v4 runner is valid only for its snapshot-compatible baseline. Any live-state mismatch is a blocker, not a reason to weaken its guard or choose another runner.

Dry-run, after explicit dry-run authority:

```bash
poetry run python scripts/model_parameter/apply_model_parameter_v4.py
```

Commit, only after the dry-run passes and separate explicit commit authority is recorded:

```bash
poetry run python scripts/model_parameter/apply_model_parameter_v4.py --apply
```

Use the matching v4 static SQL procedure only as an explicitly selected alternative commit path. Never execute both target commit paths. After commit, perform full read-back and, while dry-run authority remains valid, rerun the command without `--apply` to verify the final state.

Required target evidence:

- exact v4 master and Impact Lever identities and domain columns;
- active names and binding counts;
- mapping and scenario-template invariance required by the snapshot;
- FK, orphan, duplicate-natural-key, and creation-audit checks;
- hydrated catalog checksum;
- before/intended/after digests and post-apply dry-run result;
- preserved immutable pre-apply snapshot.

## v4 multi-event live E2E gate

Read and follow `.claude/skills/model-parameter-multi-event-quality/SKILL.md`; do not duplicate its execution and report contract here.

Start with SELECT-only discovery:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py
```

Accept only dynamically discovered `api_version=v4`, `generation_strategy=multi_event_model_lever_dimensions` evidence with 1–5 ordered Events. The route name does not impose a two-Event minimum. If the runner cannot select and prove that route, report a tooling blocker or `COVERAGE LIMIT`; do not substitute another generation strategy or another API version.

Execute only after separate explicit authority for proposal/confirmation writes and external LLM usage:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py \
  --scenario-group-id <v4-group-id> \
  --execute
```

Also establish the fixed Basecase/LUT release and authority for any remote cache write. Require dynamic DB-derived candidates, catalog-pinned Lever lineage, proposal persistence, empty-confirm rollback, valid full confirmation, reconfirmation, DB read-back, IDs, exact slots/values, provider token usage, timing, and retry evidence.

## Acceptance evidence

| Area | Required evidence |
|---|---|
| Pre-DML regression | Workbook check, `core-smoke`, affected v4 suites, final full automated run, Ruff/compile for changed Python, `git diff --check` |
| Incoming staging | `new_resources/` inventory, ignored-artifact list, staged LUT digests/collisions, and explicit `NOT PRESENT` or pending/promoted classification |
| Canonical/resources | v4 fixture and snapshot hashes, YAML/ConfigMap parity, one classification per CSV, active startup, exact catalog slots |
| Static SQL | Required only when the matching v4 SQL artifact is in scope; otherwise record an explicit skip reason |
| Target DB | Required only when authorized and in scope: dry-run authority/result, separate commit authority/path, full read-back, post-apply dry-run |
| Live E2E | v4 multi-event discovery; when separately authorized, proposal/confirmation/LLM results and retained evidence-row IDs |
| Coverage | Distinguish `FAIL`, `COVERAGE LIMIT`, `NOT RUN`, and authority/capability blockers |

Never claim full DB or E2E PASS for a phase that was unauthorized, unavailable, or exercised a different API/canonical route.
