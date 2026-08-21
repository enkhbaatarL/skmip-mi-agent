# v3/v4 LNG engine comparison campaign

This reference defines the repeatable comparison contract. It supplements, rather than replaces, the single-group engine skill under `tests/lng_model/skills/evaluate-lng-price-tags/`.

## Pairing and campaign scope

- A comparison pair is one v3 group and one v4 group with the same ordered active `mi_event_id` set.
- v3 and v4 share the same database, Event rows, parameter master, Basecase files, and LNG engine. They intentionally use different candidate routes: v3 uses the external DB AS-IS legacy dimension mapping; v4 uses the selected value's catalog-pinned Lever states.
- Do not require equal scenario counts or equal proposed parameter sets. Compare matched semantic/pressure roles where possible and report one-sided cases explicitly.
- For an expanded release campaign, default to at least three distinct Event-set pairs and at least 20 total engine cases. Cover more than one domain and include both shared-parameter and v4-only-parameter behavior. If the database lacks suitable groups and inserts are not authorized, stop at a documented `COVERAGE LIMIT`.
- Execute and evidence one group at a time. A campaign index may aggregate multiple completed group reports, but it must not merge or renumber their case identities.

Recommended coverage axes:

| Axis | Examples |
|---|---|
| Domain | demand, supply, trade/shipping |
| Candidate relation | shared v3/v4 parameter, v4-only parameter, primary/alternative binding |
| Reference source | LUT-backed, Basecase-only exact slot |
| Lever state | increase/decrease, disrupt/recover, conflicting merged states, unchanged-only exclusion |
| Price evidence | responsive East Asia/TTF case, tie, one-sided version case |
| Scenario shape | single Event, multi-Event, 3/4/5 pressure-role rows where available |

## Preflight before engine execution

Do not use the first failed engine stage as an environment probe.

1. Resolve the requested interpreter without dereferencing it out of its virtual environment. Record `sys.executable`, `sys.prefix`, `sys.base_prefix`, and import paths.
2. In that exact child-process environment, import every engine dependency required by all four stages, including `pandas`, `numpy`, `openpyxl`, and the engine modules.
3. Confirm each case directory contains exactly the expected Demand, Supply, and Trade `.xlsm` inputs. Reject missing, duplicate, zero-byte, unreadable, or non-ZIP files.
4. Open every workbook as OOXML with VBA preservation, verify its expected workbook/sheet role, and record its SHA-256. A filename alone is not proof that the file is a usable XLSM.
5. Confirm engine, LUT, template, and source workbook hashes and ensure every reserved run ID is unused.

If preflight cannot prove all five items, do not start the engine.

## Confirmed-input export contract

- Reuse the latest `CONFIRMED` payload and export with DB `SELECT` only; do not call the proposal LLM again.
- Resolve each confirmed value by parameter-specific exact semantics. A valued Basecase reference uses the existing exact Basecase cell path.
- A `LiqProdAdjustment` value with `basecaseValue=null` is LUT-backed: revalidate its canonical LUT value and full coordinates, require the same-row Basecase metadata anchor, and resolve the existing cell with exact Year/Month/Period headers. Do not use partial keys, nearest periods, or a newly created cell.
- Preserve all unmodified OOXML parts and VBA content. Record changed formula cells, removed `calcChain`, source/target hashes, and the confirmed snapshot hash.
- If export returns nonzero before an engine run map exists, retain a standalone failed-attempt JSON with attempt ID, native return code, classification, stage, cause, DB-mutation flag, partial-output inventory, exact cleanup, and remediation. Do not add it to the completed engine-run denominator.

## Failure taxonomy and retry rule

| Classification | Typical evidence | Required action |
|---|---|---|
| `PREFLIGHT_ENVIRONMENT` | virtualenv resolved to a base interpreter; dependency import failure | repair interpreter/env propagation, rerun preflight |
| `PREFLIGHT_INPUT_XLSM` | missing/zero-byte/bad ZIP workbook; required workbook/sheet mismatch | regenerate or repair only the affected exported input |
| `ENGINE_RUNTIME` | non-zero stage return code after a clean preflight | preserve stage log/manifest and diagnose engine execution |
| `ENGINE_MODEL_OUTPUT` | process succeeds but mandatory output, finite value, or CSV/XLSX parity check fails | preserve run and diagnose model/output contract |
| `EVIDENCE_VALIDATION` | hash/lineage/run-map/report binding fails | do not publish the comparison as final |

Every non-zero return code is a recorded failed attempt. A retry is allowed only after the cause and scoped remediation are written to evidence. Delete only the exact incomplete `outputs/<run_id>` and `log/<run_id>` paths reserved by that failed attempt. The aggregate report shows both the failed attempt and the successful retry.

## Formal report contract

Output Markdown and PNG only when the user requests those formats. The Markdown is the source; the PNG is a compact executive summary rendered from the same deterministic evidence.

For a report-oriented request, render a portrait document figure with title, document status, comparison metrics, independent quality axes, price charts, and attempt footer. Avoid dashboard navigation, interactive controls, or card-heavy UI. Visually inspect the PNG for clipping and legibility before publishing it.

The report must include:

- document control, scope, timestamp/timezone, source branch/SHA and target DB identity without credentials;
- pair manifest: ordered Event IDs, v3/v4 group IDs, scenario/proposal/confirmation IDs and statuses;
- canonical/snapshot/catalog/workbook/engine/LUT/template hashes;
- parameter proposal comparison, including one-sided parameters and exact slot coordinates;
- engine attempt register with command, interpreter identity, run IDs, return code, failure classification, remediation, and cleanup;
- per-case Demand/Supply/Trade propagation and annual/monthly predicted prices;
- version comparison separated into execution integrity, numeric response, pressure-tag alignment, and expressiveness;
- test commands with collected/passed/failed/skipped counts, warnings, coverage limits, and remaining risks.

Do not reuse a v3-only quality template. Do not call price equality a failure when both versions validly produced different parameter values or scenario sets; explain whether the difference follows the saved proposal and engine propagation evidence.

## Scaling to tens of cases

- Reserve globally unique run-ID ranges before the campaign and keep every pair's manifest, failed-attempt register, run map, evaluation, and report independent.
- Measure one representative completed case's workbook/output/log footprint, then require free disk for `estimated_case_size × planned_cases × 1.2` before starting. Recheck between groups.
- Keep group execution sequential because the LNG model root has a single-group lock. Use `--jobs` only for cases inside the active group.
- Aggregate `met/reversed/tie`, responsive regions, proposal signatures, warnings, elapsed time, token usage, and disk use without hiding a pair-level `REVIEW` or `FAIL`.
