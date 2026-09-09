---
name: verify-model-parameter-release
description: Verify v4 MI Model Parameter releases across canonical fixture consistency, LUT startup/catalog and prompt guards, YAML/Kubernetes parity, Excel/archive state, Python regressions, optional disposable-MySQL static-SQL checks, explicitly authorized target-DB transactions, and v4 multi-event proposal/confirmation evidence.
---

# Verify a v4 Model Parameter Release

Prove the v4 rollout from immutable inputs through runtime behavior and DB persistence. This skill does not route legacy canonical maintenance or any non-v4 flow. Keep non-mutating verification, disposable destructive verification, target-DB transactions, and live multi-event writes as separate gates.

## Establish scope and authority

1. Work from the repository root and read `AGENTS.md` and [references/verification-matrix.md](references/verification-matrix.md) completely.
2. Inspect `git status --short`, the selected v4 canonical fixtures, immutable snapshot, config, workbook, and changed files. Preserve unrelated user changes.
3. Confirm that the selected release is v4. If it requires a different canonical generation or a runner that does not match the approved snapshot/live baseline, stop and report the missing version-aware route; never fall back to a generic or historical runner.
4. Identify the configured target DB host/environment without printing credentials. Record each authority independently:
   - target DB dry-run, which locks rows and performs DML before rollback;
   - target DB commit;
   - live v4 multi-event proposal/confirmation rows and external LLM usage;
   - remote resource download/upload or cache writes, when applicable.
5. Require explicit user authority for each requested external-write category. Approval for a dry-run does not authorize commit or live proposal rows, and DB-apply approval does not authorize proposal/confirmation, LLM usage, or remote cache writes. Stop at the last authorized phase.
6. Treat the static-SQL verifier as destructive. Run it only on a disposable MySQL 8 server/database whose tables and teardown are owned by the verification run; a matching database name alone is not sufficient.

## Phase 1: Complete all non-mutating gates

No target-DB DML may run until this phase passes.

1. Validate the workbook/archive with `scripts/model_parameter/sync_mapping_workbook.py --check-only`.
2. Inventory `apps/agents/model_parameter_agent/new_resources/` as incoming staging without modifying it. Missing `new_resources/lut/` or no staged LUT is `NOT PRESENT`, not a failure. If staged LUTs exist, exclude `.DS_Store` and `~$*`, capture filename/size/digest and Unicode-normalized collisions, and fail release acceptance if any claimed release LUT remains staging-only or is consumed directly instead of being explicitly promoted and declared under canonical `resources/`.
3. Run `core-smoke`, then every affected v4 domain suite from the verification matrix.
4. Verify the runtime allow-list from code separately from raw DB/canonical/catalog active coverage. Classify active parameters outside the runtime boundary as `active-but-blocked` and prove they are excluded before LLM execution.
5. Run the full automated suite once on the final worktree using the safe test environment and explicitly exclude the opt-in MySQL test. This full run is a prerequisite for both target-DB dry-run and commit.
6. Run Ruff and compile checks over changed Python files, then `git diff --check`. Do not reformat unrelated files.
7. If any check fails, stop before external DML. Fix code only when the user's task includes implementation; otherwise report the defect and failed command.

## Phase 2: Optional static SQL verification in disposable MySQL

Run this phase only when the matching v4 static SQL artifact is part of the release scope. Static SQL is not an unconditional acceptance item; record `SKIPPED — static SQL out of scope` when the release uses only the Python runner or contains no DB artifact change.

1. Confirm the host is disposable and that dropping/recreating the verifier tables cannot affect shared data.
2. Use only `tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py` with a database name matching `model_parameter_v4_sql_verify(?:_[a-z0-9_]+)?`.
3. Require first apply, second semantic-idempotent apply, forced master-precondition rollback, forced Impact Lever precondition rollback, forced post-DML invariant rollback, and exact preservation of the snapshot mapping state.
4. Exclude `mod_dtm` only from the semantic idempotency digest. Require exact whole-table digests for failure-path rollback.
5. Capture the MySQL version and teardown result, then remove only the disposable database/container owned by this run. Never point this verifier at the target DB.

## Phase 3: Explicitly authorized target-DB transaction

Skip this phase when DB artifacts are out of scope or either the target identity or required authority is missing.

1. Reconfirm the exact target identity and snapshot provenance. The dated `scripts/model_parameter/apply_model_parameter_v4.py` runner is valid only for its snapshot-compatible live baseline. If the live baseline differs, stop; do not weaken the guard or select another version's runner.
2. After explicit dry-run authority, execute the runner without `--apply`. Require its preconditions, invariants, full read-back, and rollback digest to pass. This is DML with locks, not a read-only query.
3. Review the intended diff and report unexpected live state. Do not commit after a failed or ambiguous dry-run.
4. After separate explicit commit authority, use exactly one commit path: prefer the v4 Python runner with `--apply`, or use the matching static SQL procedure only when the user explicitly selected it. Never run both against the target.
5. Read back every master domain column and mapping plus the complete Impact Lever state. Verify active names, FK/orphan/natural-key rules, scenario-template keys, creation-audit stability, snapshot mapping preservation, cross-table binding counts, and hydrated catalog checksum.
6. With dry-run authority still in force, run the selected Python runner once more without `--apply` to prove the committed state is accepted and rolls back cleanly.
7. Preserve the pre-apply snapshot; never regenerate it from the final state.

## Phase 4: v4 multi-event real-flow evidence

This is the only live E2E route in this release-verification skill.

1. Read `.claude/skills/model-parameter-multi-event-quality/SKILL.md` completely and use it as the discovery, execution, confirmation, and reporting contract.
2. Start with its SELECT-only discovery. Accept E2E evidence only for `api_version=v4` and `generation_strategy=multi_event_model_lever_dimensions`, derived dynamically from the current DB and pinned v4 catalog. Preserve the route's ordered Event cardinality of 1–5; “multi-event” names the v4 route and does not narrow it to two or more Events. Do not substitute a different generation strategy or legacy mapping flow.
3. If the current multi-event runner cannot select and prove the v4 route, stop with a precise `COVERAGE LIMIT` or tooling blocker. Do not relabel another API version's evidence as v4.
4. Use `--execute` only after separate explicit authority for proposal/confirmation DB writes and external LLM usage. Also confirm the fixed Basecase/LUT release and any resource-cache write authority.
5. For every successful proposal, require the stored proposal row, empty-confirmation rollback, valid full confirmation, reconfirmation, and DB read-back. Preserve exact scenario/group/proposal IDs, selected Lever/parameter lineage, slots/values, provider tokens, timing, retries, and failure attempts.
6. Keep evidence rows unless the user separately requests scoped cleanup. Missing suitable v4 multi-event scenarios is a `COVERAGE LIMIT`; broken lineage, persistence, rollback, or confirmation is `FAIL`.

## Phase 5: Integrated result

Write one Markdown report under `tests/reports/model_parameter_agent/` and extend the multi-event runner's report instead of creating competing reports.

Include:

- v4 canonical, snapshot, workbook, config, and resource hashes;
- every executed command and suite-level collected/passed/failed/skipped counts;
- independent authority and outcome for target dry-run, commit, proposal/confirmation, LLM, and remote cache writes;
- conditional disposable static-SQL evidence or its explicit out-of-scope reason;
- target DB diff/read-back and post-apply dry-run when authorized;
- v4 multi-event lineage, proposal, confirmation, token, timing, retry, and coverage results;
- all failed-attempt classifications and remaining blockers.

A full PASS requires Phase 1 to pass before any target DML, zero execution errors in every executed phase, canonical/config/docs/workbook consistency, active resource startup, exact slot/value consistency, and successful authorized DB/E2E contracts. Do not turn an unauthorized or unavailable external phase into PASS; report it as `NOT RUN`, `COVERAGE LIMIT`, or a blocker with the exact authority or capability needed.
