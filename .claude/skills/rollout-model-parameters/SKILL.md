---
name: rollout-model-parameters
description: Implement end-to-end MI Model Parameter canonical rollouts across master and dimension-mapping DB data, Basecase/LUT adapters and manifests, prompt-size guards, config.yaml/Kubernetes parity, canonical JSON/SQL, Excel mapping workbooks, automated tests, README/docs, and release evidence. Use when adding, activating, deactivating, or remapping model parameters; changing LUT sources or formulas; reconciling DB/LUT/Excel/docs; or implementing a multi-parameter Model Parameter rollout. Do not use it for a scenario-only proposal test.
---

# Roll Out Model Parameters

Implement one versioned, reproducible source of truth and propagate it through DB artifacts, runtime resources, configuration, Excel, tests, and documentation. Preserve the public proposal/confirmation API unless the user explicitly requests an API change.

## Start safely

1. Work from the repository root and read `AGENTS.md`.
2. Read `.claude/rules/python-conventions.md` before changing Python and `docs/architectures/project_directory_structure.md` before changing ownership or package boundaries.
3. Read [references/repository-map.md](references/repository-map.md) completely. Treat its dated baseline as evidence for the current release, not as the desired state of every future rollout.
4. Inspect `git status --short` and preserve unrelated user changes.
5. State the requested parameter scope, canonical version, target DB environment, public API compatibility, and whether DB commit, remote resource upload/deployment, and real proposal execution are authorized.
6. Create a plan that separates reversible implementation, isolated verification, external DB commit, and real proposal/confirmation execution.

## Establish the canonical matrix

1. Inspect the configured DB, Basecase workbooks, LUT CSVs, current canonical JSON, current mapping workbook, YAML manifests, and operator docs before editing.
2. Capture the pre-apply DB state before any DML. Keep master rows, dimension mappings, and scenario dimension templates in the snapshot. Omit credentials and host details.
3. Never overwrite a snapshot after its canonical DML has been applied. The current `prepare_canonical.py` is a dated one-off generator; create a new version/date for a new rollout instead of blindly using `--replace-snapshot`.
4. Make one canonical JSON fixture the machine-readable authority. Include every master domain column, every intended mapping row, counts, active names, version, audit user, and source snapshot.
5. Record every parameter as active, pending, or excluded with a concrete reason. Resolve conflicts using actual DB/workbook/LUT evidence; do not inherit a draft document or historical Excel value without verification.
6. Derive SQL, workbook, config expectations, documentation tables, and consistency tests from the canonical fixture wherever practical. Avoid independent hand-maintained copies.

## Implement DB artifacts

1. Preserve primary keys and creation-audit columns. Update only authorized domain and modification-audit columns.
2. Preserve unrelated dimension mappings. Restore or add only mappings justified by an existing scenario dimension template and an approved `direct`, `routing`, `indirect`, or `na` decision.
3. Keep routing comments operationally specific. Encode when a routing candidate should and should not be selected.
4. Make the Python runner and static MySQL SQL idempotent from either the captured snapshot state or the exact canonical final state.
5. Lock affected master/mapping rows, apply inside one transaction, and roll back on any precondition, invariant, or read-back mismatch.
6. Check at least:
   - exact master IDs and expected row counts;
   - exact active-name set;
   - mapping method values and expected counts;
   - valid parameter foreign keys and no active mapping to an inactive/deleted parameter;
   - existing event type and dimension keys in current scenario templates;
   - no orphan or duplicate natural key;
   - full canonical read-back and stable creation-audit fields.
7. Do not modify other DB tables unless evidence shows they are required and the user authorizes the expanded scope.
8. Prepare the commit path, but defer external DB commit and static-SQL destructive verification to `$verify-model-parameter-release`.

## Implement LUT, runtime, and configuration

1. Classify every packaged LUT CSV exactly once as active parameter data, pending/disabled data, or an auxiliary reference. Fail consistency checks for unclassified or multiply classified files.
2. Keep `envs/config.yaml` and `devops/k8s/configmap.yaml` semantically identical for Model Parameter resources and limits.
3. Preserve the established Object Storage key prefixes. Do not invent a second path convention.
4. For active LUTs, validate download/sync, required headers, numeric and empty values, configured horizon, exact-key uniqueness, joins, exclusion rules, precision, and catalog creation.
5. For pending LUTs, validate declared structure without creating catalog records. For auxiliary references, sync and validate the file without creating an independent parameter record.
6. Implement formulas in deterministic adapters. Test edge cases such as missing joins, duplicate aggregation, closed facilities, month bounds, non-finite values, sign handling, and source values that must not be renormalized.
7. Bump the adapter/catalog schema version when interpretation or serialized shape changes so old caches cannot be reused incorrectly.
8. Keep full reference rows in server-side indexes. Send compact period groups and fixed-axis hierarchies to Step2, and only the validated effective reference for each exact slot to Step3.
9. Enforce per-parameter slot, request-wide slot, Step2 byte, and Step3 byte limits before invoking the LLM. Include parameter names and observed sizes in limit errors without leaking full reference payloads.

## Synchronize Excel and documentation

1. Generate the current mapping workbook from the canonical fixture. Keep parameter and dimension-mapping sheets aligned with the DB rows and include conflict/LUT metadata needed by reviewers.
2. Prefer the spreadsheet skill for workbook work. For this repository workflow, the user has authorized `openpyxl` as a fallback. Preserve styles, tables, filters, formulas, freeze panes, and Unicode text; validate the completed workbook structurally and visually when rendering is available.
3. Write to a temporary workbook, validate it fully, and only then replace the current workbook. Move superseded workbooks to `resources/mapping/archive/`; never silently overwrite an existing archive target. Mark archived files as historical.
4. Update the canonical mapping Markdown, README, Model Parameter docs 01–07, DB/API/flow/LUT/addition guides, and any architecture document whose ownership or flow boundary changed.
5. Keep the canonical JSON as the exact value authority. In human docs, identify the version/date and record resolved conflicts, evidence, formulas, paths, active/pending status, mapping behavior, and reproducible commands.
6. Do not claim a test, DB apply, or E2E result passed before it was actually run. Write the final integrated report only from captured evidence.

## Verify and hand off

1. Add or update consistency tests that compare canonical JSON, DB expectations, config/Kubernetes manifests, LUT classification, workbook/archive state, and documentation markers.
2. Add focused adapter, resource startup, cache, compression, guard, repository, candidate-selection, and public-contract regression tests for changed behavior.
3. Run the smallest affected tests while iterating.
4. When implementation is ready, load and follow `../verify-model-parameter-release/SKILL.md` for the complete acceptance flow. If the user requested implementation and full testing, continue into that skill without waiting unless an external mutation needs new authority.
5. Finish only when canonical artifacts agree, all executed checks are reported honestly, coverage limitations are explicit, and any remaining user approval is named with its exact effect.
