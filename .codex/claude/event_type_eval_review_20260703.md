# Event-Type Eval Review — 2026-07-03 00:06:02 run

Source: `apps/agents/model_parameter_agent/reports/model_parameter_proposal_evaluation_event_types_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_21_20260703_000602.md`

Scope: 21 event types (l2_id 1–21), 1 scenario_group / 1 scenario each. concurrency=4, retries=1. ERROR_COUNT=0, 1-pass completion, only group 48 (scenario 281) FAIL.

## Summary metrics

| Metric | Value |
|---|---|
| Mapping candidate coverage | 21/21 PASS (100%) |
| Group status | 20/21 PASS, 1 FAIL (group 48 / scn 281) |
| Selected-param exact match (unique set) | 12/21 scenarios (57%) |
| Param-level selection recall | ~19/36 expected params (~53%) |
| False-empty recommendations | 3 (scn 92, 129, 281) |
| Correct-empty (expected=[]) | 6 (scn 99, 295, 297, 299, 301, 303) |
| Value-cell structural validity | 34 cells, 0 duplicate/missing-axis/type issues |
| Basecase sample count | NOT in report (see gap #4) |
| Total LLM tokens | 405,663 |
| Total elapsed | 789.170s (13:09), per-scn 15.2s–301.8s |

## Findings

1. **Mapping accuracy is solid; selection is the weak link.** All 21 scenarios pass `mapping_candidate_coverage` (candidates always cover the expected params), but the LLM selection/value step drops params. Exact selected-set match is only 12/21; param recall ~53%.

2. **Systematic drop of secondary/demand-side params.** Consistently dropped even when the candidate was present:
   - `LiqUtilAdjustment` / `LiqProdAdjustment` secondary leg (scn 283, 105, 285, 279)
   - `User-Adjusted Gas Demand` alongside `PowerMix` (scn 261, 305)
   The model tends to keep only the single primary parameter and drop the alternate-route / demand-side companion the expected set lists.

3. **3 false-empty recommendations (the real gap behind EMPTY=9).** EMPTY_RECOMMENDATIONS=9, but 6 are legitimately empty (expected=[]: scn 99, 295, 297, 299, 301, 303). Only **92, 129, 281** are true misses:
   - scn 92 (ET17, group 16) — expected LiqUtil/LiqProd/SupplyDisruption, got []; mapping PASS.
   - scn 129 (ET18, group 22) — expected 5 params (incl. PowerMix/UAGD), got []; mapping PASS; slowest run (301.8s).
   - scn 281 (ET19, group 48) — **only FAIL**: routing REVIEW, expected `Gas Futures Price`. `routing_messages`: required routing candidate `19|impactintensity|shippingcost|trade|shippingcostinput` was not selected; `selected_messages`: "후보는 검증됐지만 slot/value를 확정 못함". Candidate/coverage PASS but Step2/3 failed to commit a slot → empty.
   These 3 all reached the LLM (candidates found) and returned nothing — a Step2/Step3 confirmation failure, not a mapping failure.

4. **"Absorption=100%" scenarios collapse to zero-delta.** In scn 287/289/291/293/261/267 the model selects the right params but proposes `proposedValue: 0` (or holds basecase) because `alt_energy_absorption`/`alt_supply_availability`=100%. Structurally valid, but yields no model impact — worth confirming this is the intended semantics for these test scenarios rather than a silent no-op.

5. **Basecase matching is partial.** Many value cells carry `basecaseValue: null` with rationale "전달된 기준값에는 동일한 … 행이 없습니다" (scn 287, 289, 291 fully null; scn 2/7/8/10/21 partially matched). Base-record lookup misses the selected coordinate in a large share of cells.

## Gaps in the report itself

- **Basecase sample count not persisted** — the report exposes `dimension_template` value_count but no per-scenario count of loaded basecase records, so the requested "basecase sample count" metric can't be read off the markdown; it's only weakly inferable from non-null `basecaseValue` cells.
- Per-scenario token totals are present, but there is **no aggregate token line** in "최종 요약" (405,663 had to be summed externally).
- `model_name` column is blank in every step table.

## Recommendations (no code changes made — review only)

1. Investigate Step2/Step3 for scn 92, 129, 281: coverage passes but slot/value confirmation returns empty. Priority = 281 (only FAIL, routing REVIEW on a required shipping-cost routing candidate).
2. Add prompt/eval guidance so the secondary/demand-side companion param (LiqUtil↔LiqProd, PowerMix↔User-Adjusted Gas Demand) isn't dropped when a primary is selected.
3. Persist per-scenario basecase-record count (and matched vs null cell count) into the report so basecase coverage is directly reportable.
4. Add an aggregate total-tokens line and separate "false-empty vs expected-empty" counts to 최종 요약 (EMPTY=9 is misleading; true misses = 3).
5. Confirm intended semantics of absorption=100% → zero-delta proposals (valid vs silent no-op).
