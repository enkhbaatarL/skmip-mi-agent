# model_parameter_agent — Backfill Removal Review (review-only)

Date: 2026-07-02 · Branch: `feature/model-parameter-db-proposal` · Scope: `flows/propose_parameters/{flow.py,nodes.py}`

## What changed (confirmed from diff)
- **Step3 automatic rule-based value backfill is fully removed.** Deleted: `_backfill_rule_based_adjustments`, `_build_rule_based_adjustment`, `_apply_slot_coordinates_to_cells`, `_slot_coordinates_for_candidate`, and all `_*_fallback_cells` / `_infer_countries` / `_intensity_percent` / `_percent_from_dimension` helpers. No value-hardcoding remnants remain in the Step3 path.
- **Retained:** LLM structured calls for Step1.5 (candidate validation) / Step2 (slot) / Step3 (value), all schema/coordinate sanitization, and final output dedupe by slot coordinates.
- `mapping_excel_path` dropped from `ProposeParametersIn` and state (now DB-resourced).
- Graph unchanged: `load_scenario_context → select_candidates → validate_candidates → load_basecase → propose_slots → filter_records_by_slots → propose_values`.

## Flow-level fact that governs the whole test cycle
`allow_llm_fallback` defaults to **False** (`state.py:18`, `schemas:15`). With it off, an LLM failure at any step **raises** — it does NOT silently produce empty/fallback output. So during the test cycle:
- An empty report with **no error** = LLM legitimately produced nothing usable (candidates existed but every cell was filtered). This is now expected behavior, not a bug.
- An empty report from a **raised exception** = infra/LLM failure, judge separately.
- Confirm the eval run does not pass `--allow-llm-fallback`; if it does, the deterministic fallbacks below re-activate.

---

## Judging checklist for report failures (per scenario)

### 1. Empty recommendations (top risk after backfill removal)
- `_build_proposal_parameters` skips any (file,sheet,param) group with no values (`flow.py:305-306`); if all groups empty, `proposal_parameters == []`.
- **Verdict rule:** empty is a *quality failure* only if the scenario/event clearly implies a quantifiable model input. Otherwise it's an acceptable "needs user review" outcome.
- **How to tell them apart — read `validation_warnings` + `non_input_items`:**
  - Empty output **with** cell-level warnings ("proposed_value가 null", "모호한 값", "value type 충돌") → LLM under-produced or gave ambiguous values → real quality issue worth a prompt/data look.
  - Empty output **with no warnings and empty `candidate_mappings`** → candidate gate (Step1.5) returned nothing → investigate matching/routing, not Step3.
  - Empty output where warnings say all candidates were `non_input` → genuinely no direct model input → acceptable.

### 2. Duplicate slot values
Two dedupe layers exist; a duplicate surviving to the report means one of them is misfiring.
- Intra-adjustment: `_dedupe_value_grid_by_slot` (`nodes.py:1363`) — same coordinates + different value ⇒ whole adjustment `selected=false` (conservative, good).
- Cross-adjustment (same file/sheet/param): `_finalize_group_values` (`flow.py:214-233`) dedupes by slot-coord key and **silently keeps the first value, drops the later one on conflict** (`flow.py:224-230`). This is a silent quality loss, not a crash.
- **Verdict rule:** any parameter whose `values[]` contains two identical `slot_axes_field_names` coordinate tuples = bug (dedupe should have collapsed). If seen, flag; do not "fix" by re-adding backfill.

### 3. slotAxesFieldNames mismatch (elevated risk now)
- `slot_axes_field_names` is the **union** of normalized coordinate keys across all cells in a group (`flow.py:285-286`). `_finalize_group_values` then forces every value to carry all union axes, filling absent ones with `None` (`flow.py:219`).
- Without backfill normalizing coordinates, cells in one param group are more likely heterogeneous (e.g. one cell `{Year,Month}`, another `{Year}`), so a value can declare an axis in `slotAxesFieldNames` while carrying `null` for it.
- **Verdict rule:** for each parameter, every entry in `values[]` must have a non-null value for every name in `model_target.slot_axes_field_names`. A `null`/missing axis = mismatch to flag.

### 4. Missing required coordinates
- `_normalize_slot_coordinates` **silently drops** any coordinate whose axis name doesn't canonicalize into the candidate's allowed axes (`flow.py:201-211`; `_canonical_slot_axis_name` returns `None` → dropped).
- Step3 sanitize (`_sanitize_llm_adjustments`, `nodes.py:1389`) checks for ambiguous/empty values and null proposed_value, but does **not** verify a cell's coordinates contain the full `selected_slot_axes_field_names` set (that rule lives only in the prompt). So a cell missing a required axis can pass sanitize.
- `matrix_time_columns` candidates require Year/Month/Period; if the LLM omits the time coord, the value has no period anchor.
- **Verdict rule:** a `selected` value with fewer coordinates than the candidate's allowed/required axis set (esp. missing time axis on matrix candidates, or an empty coordinate set on a non-scalar param) = flag.

### 5. Hardcoded / deterministic remnants to scrutinize
- **Value hardcoding: gone.** Confirmed — no rule-based value synthesis remains.
- **Gated LLM-failure fallbacks still exist** (only fire when `allow_llm_fallback=True`):
  - `_fallback_slot_response` (`nodes.py:1682`) injects the raw `source_dimension_value` as a slot axis — hardcoding-like. Keep fallback OFF in the test cycle so this never runs.
  - `_fallback_value_response` (`nodes.py:1708`) emits `operation="unknown"`/`proposed_value=None`, which sanitize then strips → yields no values (safe, review-only).
  - Candidate-validation fallback message "rule-based 후보를 유지" (`nodes.py:340`) is text only, also gated.
- **Deterministic candidate gating that is NOT value-hardcoding but is rule-based** — decide if the "no hardcoding" intent reaches this far:
  - `_apply_routing_comment_overrides` (`nodes.py:1168`) — token-matches DB mapping comments against dimension values to force routing candidates in/out, overriding the LLM gate. It only selects/deselects from the DB-derived candidate set; it never invents values. Closest remaining deterministic logic; call out for a policy decision.
  - `direct` candidates are force-kept regardless of LLM (`nodes.py:1080-1109`). By design (DB marks them as model inputs), not hardcoding of values.

---

## Safe "small fix" boundary (non-major)
Safe to do inline if a report reveals it:
- Add a warning (not a silent drop) when `_finalize_group_values` collapses a conflicting cross-adjustment value, so reports show the loss instead of hiding it (`flow.py:224-230`).
- Add a warning when `_normalize_slot_coordinates` drops an out-of-allowlist coordinate (`flow.py:206-210`) — surfaces LLM axis-name drift.
- Add a coordinate-completeness check in `_sanitize_llm_adjustments` that flags (warns / sets `needs_user_review`) a cell missing a required `selected_slot_axes_field_names` axis — mirrors the prompt rule.
- Prompt-only nudges (wording) in `SLOT_PROPOSAL_SYSTEM` / `VALUE_PROPOSAL_SYSTEM`.

Treat as **major (do not do inline)**:
- Re-introducing any value derivation/backfill.
- Changing the graph topology or the candidate-gating (routing override / direct-keep) semantics.
- Changing dedupe from "keep-first" to a merge/conflict-resolution strategy.

## Retest scope after any small fix
- Fix touches `flow.py` output builder/dedupe → re-run the affected event types only; diff `proposal_parameters` counts and per-parameter `slot_axes_field_names` vs prior report.
- Fix touches `nodes.py` sanitize/prompt → re-run one scenario per affected event type; confirm warning counts moved as intended and no new empty outputs.
- Always eyeball `validation_warnings` deltas — the removal makes warnings the primary signal for "why is this empty/reduced."
