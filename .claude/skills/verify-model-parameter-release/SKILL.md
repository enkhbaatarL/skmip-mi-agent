---
name: verify-model-parameter-release
description: Verify end-to-end MI Model Parameter releases across canonical fixture consistency, LUT startup/catalog and prompt guards, YAML/Kubernetes parity, Excel/archive state, Python regressions, transactional DB dry-run/apply/read-back, isolated MySQL static-SQL idempotency and rollback, DB-derived proposal/confirmation tests, and one integrated report. Use after a Model Parameter rollout, for full Flow and DB-linked testing, release acceptance, rollback/idempotency checks, or final evidence. Use model-parameter-agent-test directly for a scenario-only request.
---

# Verify a Model Parameter Release

Prove the rollout from immutable inputs through runtime behavior and DB persistence. Separate product failures from unavailable scenario coverage, and never turn a verification shortcut into an unapproved external mutation.

## Establish scope and authority

1. Work from the repository root and read `AGENTS.md`.
2. Read [references/verification-matrix.md](references/verification-matrix.md) completely.
3. Inspect `git status --short`, the current canonical fixture, snapshot, config, workbook, and changed files. Preserve unrelated user changes.
4. Identify the configured DB host/environment without printing credentials. State whether the run covers:
   - local/static checks only;
   - destructive testing in a disposable MySQL database;
   - target DB dry-run;
   - target DB commit;
   - real proposal/confirmation rows, LLM provider usage, and resource-cache writes.
5. Require explicit user intent for target DB commit. Treat a full rollout request that already says to apply the DB as authorization, but stop if the actual target differs or is ambiguous.
6. Treat the isolated SQL verifier as destructive even though it has a database-name guard. Run it only against a disposable server/database.

## Phase 1: Verify artifacts without target DB mutation

1. Validate the current workbook/archive with `sync_mapping_workbook.py --check-only`.
2. Run the named `core-smoke` suite in the verification matrix first. Treat its runtime collected count as evidence; do not make a historical total such as 106 part of the contract.
3. Run only the named domain suites affected by the current change. Use the verification matrix as the single source for suite membership and commands.
4. Use `lut-runtime` and `resource-config-storage` evidence to confirm active resource startup, one classification per packaged CSV, exact catalog round-trip, disabled/reference exclusion, and YAML/ConfigMap parity.
5. Use `agent-contract-detail` evidence for prompt compression, exact Step3 references, request-wide slot limits, and Step2/Step3 byte guards when proposal-flow code changed.
6. Run Ruff and compile checks on changed Python files, then `git diff --check`. Do not reformat unrelated files.
7. Fix the smallest relevant implementation, fixture, mapping, prompt, or document defect and rerun the affected phase before continuing.

## Phase 2: Verify static SQL in disposable MySQL

1. Provision or identify a disposable MySQL 8 instance. Confirm that dropping the verifier's three test tables cannot affect shared data.
2. Use a database name matching `model_parameter_sql_verify(?:_[a-z0-9_]+)?`.
3. Run `tests/manual/model_parameter_agent/verify_canonical_sql_mysql.py` with test-only credentials.
4. Require evidence for first apply, second semantic-idempotent apply, forced master-precondition rollback, and forced post-DML template-invariant rollback.
5. Accept `mod_dtm` exclusion only for the semantic idempotency digest. Require exact whole-table state preservation for both failure-path rollback digests.
6. Tear down the disposable database/container after evidence is captured.

## Phase 3: Verify and optionally apply the target DB

1. Reconfirm target identity and snapshot provenance. Never point the isolated verifier at this DB.
2. Run `apply_canonical.py` without `--apply`. This is not a read-only query: it locks rows and performs DML before rollback, so confirm DB access and an acceptable lock window. Require its snapshot-or-final preconditions, invariants, full read-back, and rollback to pass.
3. Review the intended diff and report any unexpected live state before committing.
4. Commit only when authorized. Prefer `apply_canonical.py --apply`; use the static SQL procedure only when explicitly selected for MySQL operations. Never run both commit paths on the same rollout merely for verification.
5. Read back every master domain column and all mappings. Recheck active names, method/count expectations, FK/orphan/natural-key rules, scenario template keys, creation-audit stability, and absence of active mappings to inactive/deleted parameters.
6. Run the Python apply command again without `--apply` to prove the final state is accepted and rolled back cleanly.
7. Preserve the pre-apply snapshot. Do not regenerate it from the final state.

## Phase 4: Run regression and real flow tests

1. Run the full automated suite once on the final worktree after the core and affected-domain checks. Do not rerun unchanged local suites merely because target DB DML was applied; prove target DB state with dry-run/read-back evidence.
2. For real proposal/confirmation coverage, read `.claude/skills/model-parameter-agent-test/SKILL.md` completely and follow it as the execution/reporting contract.
3. Derive active parameters, event types, mappings, and candidate scenarios from the current DB. Never reuse historical scenario IDs or expected routing winners blindly.
4. Exercise each requested/active parameter where a valid mapped scenario exists. Do not insert synthetic scenario fixtures merely to manufacture coverage; record a precise coverage limit instead.
5. For every successful proposal, verify the stored proposal row and the required confirmation workflow: invalid empty payload rollback, valid full confirmation, DB read-back, and reconfirmation. Use an existing safe non-PROPOSED row for invalid-status testing only if one already exists.
6. Keep proposal/confirmation evidence rows unless the user requested cleanup. Report their IDs.
7. Capture provider-reported input/output/total tokens, per-stage and scenario elapsed time, retries, candidate/slot/value counts, Basecase/LUT source, exact effective references, and confirmation results. Never infer missing token usage.

## Phase 5: Produce one integrated result

1. Write one Markdown report under `tests/reports/model_parameter_agent/`. Extend the runner's report instead of creating competing raw and evaluated reports.
2. Include canonical version, target environment, commit method, canonical/snapshot/workbook hashes, snapshot path, executed commands, suite별 collected/passed/failed/skipped counts, DB read-back, isolated SQL rollback evidence, active/pending parameter outcomes, catalog/slot counts, and API compatibility.
3. For each exercised parameter, include candidate and selected mapping, scenario/event IDs, selected slots and values, rationale, Basecase/LUT source, prompt tokens, time, retry, proposal ID, negative confirmation result, valid confirmation, reconfirmation, and DB read-back.
4. Distinguish `FAIL` from `COVERAGE LIMIT`. Missing a suitable existing scenario is a coverage limit; broken mapping, exact-slot validation, persistence, rollback, or confirmation is a failure.
5. Record any known review result honestly. Do not convert `EMPTY_RECOMMENDATIONS` or a routing review flag into an automatic product failure without checking the current DB-derived candidate set.
6. Require zero execution errors, canonical/config/docs/workbook consistency, active LUT startup, Step2/Step3 count consistency, authorized DB read-back, and confirmation contracts for a full PASS.
7. In the final response, link the report and summarize scope, pass/fail counts, DB apply/read-back, E2E coverage, confirmation results, remaining limitations, and any exact approval still needed.
