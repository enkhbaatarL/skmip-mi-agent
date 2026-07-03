# All-Event Run Follow-up — Backfill Removal (review-only)

Report: `reports/…event_types_1_…_21_20260702_230250.md` · Scope: 21 event types × 1 group × 1 scenario · ERROR_COUNT=0

## Verdict: no code change is justified.

The run is clean where the removed backfill mattered:
- duplicate values = 0, missing/null `slotAxesFieldNames` = 0 (the two elevated risks from the prior review did **not** materialize — so adding the speculative silent-drop/coordinate-completeness warnings I earlier floated is not warranted; there is no evidence to act on).
- Empty recommendations `[92,99,281,295,297,299,301,303]` are the correct, honest outcome. All but 281 are low-intensity "흡수/완충/안정/경미/단기/소규모" scenarios where absorbed impact ⇒ no model-input change, or (303) genuinely no DB mapping candidate. Each carries a validation/mapping warning explaining the empty. These are expected PASS empties, exactly the behavior we wanted after removing backfill.

### The single FAIL (scenario 281) is a data gap, not a code defect
Confirmed from the report:
- `expected_parameters: []`, `selected_parameters: []`, `mapping_candidate_coverage: PASS`, `selected_result: PASS`.
- Group FAIL is driven **only** by `routing_result: REVIEW` → *"routing 검증 대상 scenario인데 Step1.5 후보 검증을 통과한 routing 후보가 없습니다."*
- Initial candidates (PowerMix, Coal/Gas Futures Price, User-Adjusted Gas Demand) were the event_type-19 routing rows for *other* dimensions; the LLM correctly rejected all of them for an "IMO 운송 규제" shipping scenario.
- The genuinely-relevant ShippingCost parameter never became a candidate because the mapping resources have **no active ShippingCost parameter definition**, and the event_type-19 `impact_intensity=운송 규제` row is `mapping_method=na` with empty `canonical_parameter_name`.

The pipeline did the right thing at every step: it did not fabricate a shippingcost candidate from an `na` row, and it did not hardcode a value. Making 281 "pass" via code would require exactly the three prohibited moves (reintroduce backfill / hardcode shippingcost / DB write). So the correct action is **none** — the FAIL is a true-positive signal that the mapping data is incomplete for shipping-cost routing.

## Follow-up recommendations (data + test-report, no code)

1. **Data owner (not now, no DB write in this cycle):** add/activate a ShippingCost parameter definition and replace the event_type-19 `impact_intensity=운송 규제` row's `mapping_method=na`/empty canonical with a real direct/routing mapping. Until then, 281 (and any shipping-cost routing scenario) cannot produce a candidate — this is the root cause and the only thing that will flip the FAIL.

2. **Evaluator/test-report clarity:** 281's group FAIL reads like a pipeline regression but is a known data gap on a routing-test fixture whose `expected_parameters` is `[]`. Recommend the evaluator distinguish **"data-gap FAIL"** (routing-test scenario with no mapped routing parameter available) from **"logic FAIL"** (candidate existed but wrong selection), so one incomplete mapping row doesn't mask/inflate as an agent regression across the summary. Reconcile the routing-test fixtures with what the DB mapping can actually produce.

3. **Spot-confirm the other 7 empties as intended PASS** (already consistent in the report): low-intensity/absorbed scenarios and 303's "no direct/routing candidate" are semantically-correct empties. No action; just note in the report summary that empty ≠ failure for these, to pre-empt misreading.

4. **Regression baseline:** keep this run (dup=0, null-axes=0, ERROR=0, 7 expected empties + 1 data-gap FAIL) as the post-backfill baseline. Re-run should hold these invariants; a new non-empty output for 92/99/295/297/299/301/303, or a new duplicate/null-axis, is the signal worth investigating — not the standing 281 FAIL.
