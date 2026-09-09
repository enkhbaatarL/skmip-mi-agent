---
name: rollout-model-parameters
description: Implement canonical MI Model Parameter v4 rollouts for Scenario API v4 groups using multi_event_model_lever_dimensions. Use when changing the v4 parameter master, Impact Lever catalog or bindings, hydrated catalog checksum, Basecase/LUT sources or formulas, runtime resources, canonical JSON/SQL, workbook, config, tests, or docs. Legacy dimension mapping is a protected invariant, never a rollout target or fallback. Hand release acceptance to verify-model-parameter-release and live v4 quality execution to model-parameter-multi-event-quality.
---

# Roll Out Model Parameters for Scenario API v4

Implement one reproducible v4 release set and propagate it through the parameter master, Impact Lever catalog, runtime resources, configuration, workbook, tests, and documentation. This workflow supports only `api_version=v4` with `generation_strategy=multi_event_model_lever_dimensions`. Preserve the public proposal/confirmation API unless the user explicitly authorizes an API change.

## Establish scope and authority

1. Work from the repository root, read `AGENTS.md`, and read [references/repository-map.md](references/repository-map.md) completely.
2. Read `.claude/rules/python-conventions.md` before changing Python and `docs/architectures/project_directory_structure.md` before changing ownership or package boundaries.
3. Inspect `git status --short` and preserve unrelated user changes.
4. State the requested parameter, Lever binding, LUT/Basecase, formula, or runtime-boundary changes; the new canonical and catalog versions; the target DB environment; and public API compatibility.
5. Record authorization separately for target DB commit, remote resource upload or deployment, live Scenario creation, LLM execution, and proposal/confirmation writes. A transactional dry-run may still lock rows and execute rolled-back DML, so confirm DB access and an acceptable lock window before running it.
6. Separate reversible repository implementation, release acceptance, external mutation, and live quality execution in the plan. Do not widen this workflow to schema changes, unrelated tables, or legacy dimension mapping. Stop and establish a separately owned workflow if any is requested; DB migrations remain owned by the sibling `skmip-mi-agent-mgmt` repository.

## Build the canonical v4 release set

1. Inspect the configured parameter master, active Impact Lever catalog, existing v4 Scenario catalog pins, Basecase workbooks, LUT CSVs, resource manifests, configuration, current canonical files, workbook, tests, and operator docs before editing.
2. Capture an immutable, versioned pre-apply snapshot before any DML. It must include the affected master and Impact Lever rows plus digests of protected legacy dimension mappings and active v4 Scenario templates. Do not expose credentials or connection details, and never regenerate a pre-apply snapshot from final state.
3. Treat `model-parameter-canonical-v4.json` and `model-impact-lever-canonical-v4.json` as one release set:
   - the parameter fixture owns every master domain field, activation state, Basecase metadata, audit expectations, source snapshot, and expected counts;
   - the Impact Lever fixture owns Lever identity and hierarchy, domain, primary/alternative bindings, applicability, support state, catalog version, binding counts, and hydrated catalog checksum.
4. Record every parameter and binding as active, pending, unsupported, or excluded with an evidence-backed reason. Keep raw catalog capability distinct from the runtime proposal allow-list and from exact executable slot coverage.
5. Resolve conflicts using current DB, workbook, Basecase/LUT, and runtime evidence. Do not inherit an old fixture, archived workbook, historical report, or prose table without verification.
6. Derive the transactional runner and SQL, workbook, Impact Lever/catalog expectations, LUT classification, configuration markers, documentation tables, and consistency tests from this release set. Avoid independent hand-maintained value copies.
7. Compute the hydrated catalog checksum deterministically from the active, fully bound v4 catalog. Require the canonical value, DB read-back, runtime catalog, and newly created v4 Scenario group pin to agree.
8. A checksum change does not authorize reinterpretation or in-place rewriting of existing v4 Scenarios. They remain pinned to their original catalog; create new v4 Scenarios through the owning Scenario API flow only when that write is authorized.

## Preserve the v4 input contract

1. Make Scenario API v4 inputs first-class implementation and test inputs: one to five ordered active Event relations, selected values for every dimension, dimension lineage, `primary_lever_code`, `primary_impact_lever_id`, selected-value `lever_states`, source Event/path/uncertainty IDs, model support state, and the group catalog version/checksum.
2. Accept the Lever route only for `api_version=v4` and `generation_strategy=multi_event_model_lever_dimensions`. Reject missing or stale catalog pins before proposal generation.
3. Validate selected-value completeness; Event membership and order; Lever code/ID/catalog identity; active and non-deleted state; primary Lever presence; duplicate Lever states; direction, domain, role, applicability, and support status; bound parameter identity and activation; and exact Basecase/LUT slot availability.
4. Build raw candidates only from the selected values' hydrated Lever states and current active catalog bindings. Unselected values must not contribute candidates or prompt payloads.
5. Never query or mutate legacy dimension mapping to serve v4, and never fall back to representative Event Type mapping, v3 composite `sourceRefs`, historical `lever_mappings`, or another API version when v4 input is incomplete. Fail with the existing domain/API error contract.
6. Preserve lineage when multiple Events, dimensions, or Lever states converge on one parameter, and keep primary/alternative bindings together as one deterministic routing task.

## Implement DB artifacts safely

1. Apply the parameter master and Impact Lever catalog as one version-aware transaction. Preserve primary keys and creation-audit columns; update only authorized domain and modification-audit columns.
2. Require snapshot-or-exact-final-state preconditions, lock every affected row, validate the cross-table binding set and hydrated checksum, perform full canonical read-back, and roll back on any mismatch.
3. Treat the entire legacy dimension-mapping table as an invariant. Capture its full semantic digest before the transaction and require the same rows, values, and creation-audit fields after dry-run, apply, idempotent replay, and every failure path. It is not a source for v4 candidate generation and is not a rollout artifact.
4. Preserve unrelated tables and existing Scenario/proposal rows. Do not update stored Scenario catalog pins to make them match a new catalog.
5. Make the versioned Python runner and matching MySQL procedure idempotent from either the captured snapshot state or the exact canonical final state. Use only one authorized commit path.
6. Prepare DB artifacts locally, but hand disposable-MySQL verification, target dry-run/commit/read-back, rollback proofs, and final acceptance to `$verify-model-parameter-release`.

## Implement runtime resources and guards

1. Treat `apps/agents/model_parameter_agent/new_resources/` as user-owned incoming staging only. It may be absent or contain no LUT yet; neither state is an error. Never let runtime discovery, manifests, tests, or deployment glob this directory together with canonical `resources/`.
2. When files arrive under `new_resources/lut/`, inventory them without moving, renaming, deleting, or overwriting them. Ignore OS/Office artifacts such as `.DS_Store` and `~$*`; normalize names only for collision detection, and record source filename, size, digest, candidate classification, and any collision with `resources/lut/`.
3. Promote a staged LUT only as an explicit rollout change. Validate it in isolation first, then update the canonical adapter/registry, resource manifest, config/ConfigMap, fixture/workbook/docs, and tests before copying the approved artifact into `resources/lut/`. A staged file is never an active runtime source by presence alone.
4. Classify every packaged LUT CSV in canonical `resources/lut/` exactly once as active parameter data, pending/disabled data, or an auxiliary reference. Fail consistency checks for unclassified or multiply classified files.
5. Keep `envs/config.yaml` and `devops/k8s/configmap.yaml` semantically identical for Model Parameter resource releases, object keys, schema versions, and limits. Preserve the established Object Storage prefixes.
6. For active LUTs, validate sync, file digest, headers, numeric and empty values, horizon, exact-key uniqueness, joins, exclusions, precision, adapter interpretation, and slot-catalog creation. Validate pending and auxiliary files without exposing them as active parameter slots.
7. Implement formulas in deterministic adapters. Cover missing joins, duplicate aggregation, closed facilities, month bounds, non-finite values, sign handling, and source values that must not be renormalized.
8. Bump adapter, catalog, or resource-manifest schema versions whenever interpretation or serialized shape changes so an incompatible cache cannot be reused.
9. Keep full reference rows in server-side indexes. Send compact period groups and fixed-axis hierarchies to Step2, and only the validated effective reference for each exact slot to Step3.
10. Enforce per-parameter slot, request-wide slot, Step2 byte, and Step3 byte limits before invoking the LLM. Include parameter names and observed sizes in errors without leaking reference payloads.

## Synchronize workbook and documentation

1. Generate the current mapping workbook from the canonical v4 release set. Make the parameter master, Impact Lever bindings, catalog version/checksum, activation/support state, LUT metadata, and conflict resolution directly reviewable.
2. If the workbook displays legacy dimension mappings, source that sheet from the captured invariant state and label it explicitly as unchanged reference data. Never generate a desired mapping state from it.
3. Prefer the spreadsheet skill for workbook changes; `openpyxl` is an authorized fallback for this repository. Preserve styles, tables, filters, formulas, freeze panes, and Unicode text, and validate the result structurally and visually when rendering is available.
4. Write to a temporary workbook, validate it fully, and only then replace the current workbook. Move superseded workbooks to `resources/mapping/archive/`; never overwrite an archive target, and label archives as historical.
5. Update the canonical mapping Markdown, README, Model Parameter docs, Scenario API v4 contract/flow docs, and any architecture document whose ownership or boundary changed. Identify versions, evidence, formulas, resource paths, status, catalog checksum behavior, and reproducible local commands.
6. Do not claim DB apply, acceptance, or live proposal/confirmation success from implementation evidence alone.

## Test and hand off

1. Add or update deterministic tests for canonical cross-file consistency, master-to-Lever bindings, hydrated checksum, protected mapping invariance, YAML/ConfigMap parity, LUT classification and catalog slots, workbook/archive state, docs markers, and public API compatibility.
2. Add focused v4 tests for Scenario input hydration and rejection, selected-value-only candidate generation, catalog pin mismatch, Lever identity and primary/alternative routing, multi-Event lineage convergence, resource startup/cache, prompt compression, exact references, and byte/slot guards.
3. Run the smallest affected local tests while iterating and report every executed result honestly.
4. When repository implementation is ready, load and follow `../verify-model-parameter-release/SKILL.md`. That skill owns release acceptance, disposable and target DB safety checks, idempotency/rollback/read-back evidence, full regression, and the integrated release report.
5. For live v4 Scenario discovery and proposal/confirmation quality, load and follow `../model-parameter-multi-event-quality/SKILL.md`. That skill owns live-write authorization, coverage selection, LLM/token/trace evidence, persistence checks, retry evidence, and quality reporting.
6. Do not duplicate either handoff skill's commands or declare a full PASS here. Finish this skill with the implemented artifact diff, local test evidence, unchanged legacy-mapping proof available at that stage, and the exact remaining acceptance or live-execution authority.
