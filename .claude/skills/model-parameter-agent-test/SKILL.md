---
name: model-parameter-agent-test
description: Run and document MI 수급모델파라미터 proposal and post-proposal confirmation tests against the current DB mapping state. Use when the user asks to test one scenario, asks "xxx 시나리오 테스트해줘", asks "모든 이벤트타입에 해당하는 시나리오그룹 1개씩 테스트해줘", asks to validate confirmation success/failure, or asks to test 폭염/폭엄/한파 event type scenarios and write markdown result files.
---

# Model Parameter Agent Test

## Overview

Run 수급모델파라미터 proposal and confirmation tests from the repository root and write markdown reports under `tests/reports/model_parameter_agent/`.

Use `poetry run` from the repo root. Do not start the API server for these tests.

Before raw-graph execution, the shared test runner initializes Model Parameter resources once from
`model_parameter_resource_storage` in the active `APP_CONFIG`:

- `enabled: false`: use packaged `resources/basecase` and `resources/lut` without accessing `local_root`.
- `enabled: true`: reuse a valid `<local_root>/current`; only sync from Object Storage when current is absent or invalid.
- Keep the selected release fixed for the lifetime of the test process. Do not initialize resources per scenario.

## Request Mapping

For a single scenario request such as `289 시나리오 테스트해줘` or `scenario_id=289 테스트해줘`, run:

```bash
poetry run python .claude/skills/model-parameter-agent-test/scripts/run_single_scenario_report.py --scenario-id 289 --max-candidates 30
```

If the user provides a scenario title instead of an id, resolve the `scenario_id` from local `midb` by searching scenario title, scenario group title, and event title. If there are multiple plausible matches, ask the user to choose.

For `모든 이벤트타입에 해당하는 시나리오그룹 1개씩 테스트해줘`, run one scenario group per event type and two scenarios per group:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --all-event-types --groups-per-event 1 --scenarios-per-group 2 --concurrency 4 --retries 1
```

For `폭염/한파 이벤트타입에 해당하는 시나리오 테스트해줘`, include event_type_l2_id `6` (겨울 한파) and `7` (여름 폭염). Treat the typo `폭엄` as `폭염`. By default, test all existing groups/scenarios for these two event types:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --event-type-l2-ids 6 7 --concurrency 4 --retries 1
```

If the user explicitly says `1개씩`, `샘플`, or asks for a quick check, add `--groups-per-event 1 --scenarios-per-group 2`.

If the user specifies one or more target parameters such as `GDP`, `PMI`, `PowerMix`, `Temperature`, or `LiqUtilAdjustment`, use parameter mode. The script resolves event types where the parameter is a current DB `direct` or `routing` mapping candidate, then writes the report body in `parameter -> event_type -> scenario` order:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --target-parameters GDP --groups-per-event 1 --scenarios-per-group 2 --concurrency 4 --retries 1
```

If the user asks for exactly one scenario group and multiple scenarios **per target parameter**, resolve one current DB group per parameter first and pass the selected scenario IDs explicitly. Separate multiple IDs with commas. All IDs for one parameter must belong to the same group, and do not reuse a scenario ID across parameters:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py \
  --target-parameters GDP PMI PowerMix Temperature LiqUtilAdjustment \
  --parameter-scenarios GDP=1132,1133 PMI=1131,1136 PowerMix=867,868 Temperature=1043,1046 LiqUtilAdjustment=1031,1032 \
  --concurrency 4 --retries 1
```

The IDs above are syntax examples only. Always select them from the current DB mapping and scenario state; do not reuse historical IDs blindly.

If the user specifies both target parameters and explicit event types, keep the explicit event type scope while still rendering the report in `parameter -> event_type -> scenario` order:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --target-parameters GDP PMI --event-type-l2-ids 1 2 4 --groups-per-event 1 --scenarios-per-group 2 --concurrency 4 --retries 1
```

## Required Confirmation Workflow

Run confirmation after proposal generation by default. Skip it only when the user explicitly requests a proposal-only test. A successful proposal is not an end-to-end PASS until its valid confirmation and DB read-back succeed.

For local raw-graph tests, call `apps.agents.model_parameter_agent.flows.confirm_parameters.flow.run_confirm_parameters()` directly; do not start the API server. For deployed API tests, call `POST /model-parameters/proposals/{modelParamProposalId}/confirmation`.

Use this order so negative cases cannot corrupt a successful confirmation:

1. Read the successful proposal row and require `status=PROPOSED` with non-empty `proposal_parameters`. Save the complete before-row snapshot.
2. On at least one successful proposal per scenario group, submit `confirmationParameters=[]`. Require `INVALID_REQUEST` and verify that status, `confirmation_parameters`, `confirmed_dtm`, and modifier fields are unchanged.
3. For **every** successful proposal, submit the exact stored `proposal_parameters` as `confirmationParameters`. Use the proposal/request user id when available; otherwise omit `userId` rather than hardcoding one.
4. Require a success response with the same proposal id and `status=CONFIRMED`. Read the row back and verify `status=CONFIRMED`, `confirmation_parameters` equals the submitted full set, and `confirmed_dtm` is populated. Keep `proposal_parameters` unchanged.
5. On at least one confirmed proposal per scenario group, submit the same valid full set again. Require `CONFIRMED` to remain, the confirmation payload to be replaced successfully, and `confirmed_dtm` to be refreshed. Do not insert synthetic test text or change a proposed value merely to prove overwrite.
6. Test invalid proposal status once per run when an existing `PROCESSING` or `FAILED` row is safely available. Submit a valid payload, require rejection, and verify the row is unchanged. Never mutate a successful proposal's status or create DB fixture rows solely for this case. If no such row exists, mark only the invalid-status subcase `N/A` with the reason.

If proposal generation fails or produces an empty recommendation, do not attempt confirmation for that proposal. Record confirmation as `N/A` for that failed proposal while retaining the proposal failure.

Treat any failed valid-confirmation call, mismatched stored payload, missing confirmation timestamp, unintended proposal mutation, or rollback violation as `FAIL`. Record confirmation elapsed time separately from the 180-second proposal timing judgement.

## Report Handling

Use the report path printed as `REPORT` or `REPORT_IN_PROGRESS`. Event-type evaluation updates the markdown as scenarios finish, so the partial report can be inspected while the run continues.

Write one integrated markdown report per user test request. If an automated script already created a markdown report, append any parameter-specific quality evaluation, findings, and improvement plan to that same file instead of creating a second markdown file. Do not split "raw execution result" and "quality evaluation" into separate report files unless the user explicitly asks for separate files.

Put an `종합 평가` section at the top of the report, immediately after the title and compact execution metadata. It must summarize total execution/error counts, aggregate judgements for the seven criteria, review/failure flags, confirmation status, and the maximum elapsed scenario as compact timing evidence. Do not leave the aggregate evaluation only at the end of the report.

Keep `종합 평가` compact and do not duplicate the scenario-level result table there. Put the required one-row-per-scenario table under `대상 요약` as specified below; keep failed/review criteria, retry, confirmation, wall-clock elapsed time, and individual elapsed-time totals in the aggregate judgement and detailed scenario sections when they are not part of the seven required table columns.

Do not render a standalone `Confirmation DB read-back` section or a per-proposal timestamp/status table. Keep confirmation evidence compact in the scenario table and aggregate summary. Preserve the detailed DB read-back internally for verification, and show extra before/after evidence only when a confirmation check fails or needs review.

Directly below `종합 평가`, add `추천 개선안`. Base recommendations on evidence from the current run and organize them by graph stage such as candidate selection, Step2 slot proposal, Step3 value proposal, output/DB persistence, confirmation, and observability/retry handling. For each recommendation, state the observed signal, whether graph logic or prompt should change, the concrete change direction, and priority. Focus especially on prompt packet size, Basecase/LUT reference semantics, value direction/magnitude, sibling-scenario consistency, and retry visibility. Do not invent generic improvements when the run provides no supporting evidence; say `개선 필요 없음` for stages with no issue.

After the aggregate section, add `시나리오그룹별 평가 기준 결과`. Render one subsection per unique `scenario_group_id`, even when multiple target parameters share the group. Each group subsection must contain all seven criteria with judgement, concrete evidence, and improvement direction when needed.

Report ordering depends on the user's requested scope:

- If the user specifies event types, scenario groups, or scenarios, keep the current `event_type -> scenario_group -> scenario` order.
- If the user specifies target parameters, write the main result body in `parameter -> event_type -> scenario` order. The scenario subsection should filter the proposed parameter summary/value tables to the current parameter, while the final DB proposal row remains the full stored row for traceability.

Directly under `대상 요약`, after the event-type count bullets and before `호출 결과`, add one `시나리오별 결과` markdown table. It must contain exactly one row per executed scenario and use these columns in this order: `시나리오그룹`, `시나리오`, `이벤트타입`, `파라미터`, `결과요약`, `소요시간`, `Token (입력/출력/합계)`. Include both id and title/label in the first three columns, list every requested target parameter mapped to the event type in one parameter cell, summarize proposal/validation/confirmation outcome compactly, and show both formatted duration and seconds. Do not duplicate a scenario row merely because the same execution is rendered under multiple parameter sections. After the required confirmation workflow, update each successful row from proposal-only wording to the final proposal/confirmation result; use `confirmation N/A` for proposal failures or an explicitly requested proposal-only run.

For the scenario-level Token cell, sum the provider-reported `prompt_tokens`, `completion_tokens`, and `total_tokens` across every recorded LLM call for that scenario, including Step1.5, Step2, and Step3 when executed. Render the values as `<input> / <output> / <total>` with thousands separators. Use `0 / 0 / 0` only when a completed scenario has no LLM calls. Use `N/A` when the scenario failed or any executed call has missing or invalid usage; never infer unrecorded usage from failed, timed-out, or retried calls.

For event-type or multi-scenario runs that use `tests/manual/model_parameter_agent/evaluate_event_type_proposals.py`, treat the generated `REPORT` file as the base integrated report. Before the final response, make sure the same `REPORT` path contains the scenario group, dimension template, event, scenario major information, final DB proposal row, proposed parameter/value details, and parameter-specific quality evaluation. Prompt packet details are appendix material, not the primary report structure.

Never leave a failed scenario only as an `ERROR scenario_id=...` bullet under `Group Test Summary`. Render every failed scenario as a full scenario subsection at the same hierarchy as successful scenarios. Include the scenario title and `Scenario Major Info` loaded before graph execution; if context loading itself failed, show the scenario id and an explicit context-unavailable reason instead of an empty section. The compact group error list may remain as an index, but it does not replace the failed scenario subsection.

Preserve partial execution state whenever a scenario fails. For every outer retry attempt, include an `Attempt별 단계 Tracing` block with attempt number, attempt elapsed time, failing stage, error, validated/selected parameter names, validation warnings, and a stage table covering Step1 mapping, Step1.5 candidate validation, Step2 slot proposal/filter, Step3 value proposal, and output validation/persistence. Mark every stage explicitly as `PASS`, `FAIL`, `SKIPPED`, `NOT_REACHED`, or `UNKNOWN`; include the termination reason and observed counts. Follow it with all recorded LLM-call traces for that attempt, including step, success, model, elapsed time, input/output/total tokens, and error. Do not fabricate a failed LLM call or token usage when the connector raised before returning usage; mark the stage failure and unavailable trace explicitly. Always keep `Confirmation: N/A · proposal 실패로 미수행` in a failed proposal subsection.

Every markdown report must include scenario-level execution time, per-LLM-call execution time, and retry count. A scenario section should show total scenario elapsed time, and a `모델 호출별 소요시간` table with Step1.5 candidate validation, Step2 slot proposal, and Step3 value proposal rows when those LLM calls were executed.

Judge scenario execution time as follows:

- `PASS`: no retry and total scenario elapsed time is at most 180 seconds.
- `REVIEW`: one or more retries occurred, but the scenario completed within 180 seconds.
- `FAIL`: total scenario elapsed time exceeded 180 seconds, or execution still failed after retries.

At the top-level `종합 평가`, add one compact `소요시간 특이사항` aggregate with the PASS/REVIEW/FAIL counts and the scenario IDs requiring attention. In every scenario subsection, immediately after total elapsed time and attempt count, add exactly one line in this format:

```markdown
- 소요시간 특이사항: PASS|REVIEW|FAIL · <one-line reason>
```

Use `PASS · 특이사항 없음 (retry 0회, 180초 이내)` when no retry occurred and the scenario completed within 180 seconds. For `REVIEW` or `FAIL`, state the retry count, failing step/error when known, and whether 180 seconds was exceeded. Count both whole-scenario outer retries and connector/LLM internal retries found in execution logs. If internal retry evidence is not machine-readable, inspect the logs and enrich the generated line before finalizing the report. Never omit the field; failed scenarios must also receive a one-line timing note.

Do not add a standalone slow-case ranking or `느린 테스트케이스 상위 10%` section. Keep the maximum elapsed scenario only as compact evidence in the top-level timing summary and each group's criterion 5 result.

Do not include `Reference Runtime Summary` or repeated per-scenario `Reference Runtime` JSON. Show only one compact metadata line near the top: `LUT: enabled|disabled, version=<version>`.

Every markdown report must make the information needed for human proposal review visible in this order:

1. `Scenario Group`: show the DB-loaded scenario group once per group, including `scenario_group_id`, `mi_event_id`, `event_type_l2_id`, event type labels, `title`, `summary`, `description`, `dimension_selected`, `scenario_count`, `status`, and `stage`.
2. `Dimension Template`: show the full `dimension_template` rows for the event type, including dimension key/label/required/options when present.
3. `Dimension -> Parameter Mapping`: immediately below the dimension template, show DB-loaded dimension-to-parameter mapping rows for the same `event_type_l2_id`. Keep this compact. Include source tables, `mapping_count`, and for each row only `dimension`, `mapping_method`, `parameter`, and `comment`.
4. `Event`: show the DB-loaded event once under the group, including `mi_event_id`, `event_type_l2_id`, `event_title_ko`, `one_line_summary`, date fields, source record ids, `key_bullets`, `tags`, and bounded `detail_analysis`.
5. `Scenarios`: for each scenario in the group, show scenario major information and the actual final DB proposal row.

For each scenario subsection, include:

- Scenario major information: `scenario_id`, `scenario_group_id`, `title`, bounded `narrative`, `status`, `dimension_values`, probability/impact fields, and `baseline_yn`.
- Validation summary: expected/validated parameter candidates, selected parameters, mapping/selection/routing status, and warnings.
- Reference sample summary: Step2 Basecase sample slot count, LUT sample slot count, Basecase+LUT union slot count, selected slot count, and exact validation pass/fail count. For Step3, show valid input slot count, reference sample value count, valid result value count, and final DB value count.
- Final DB proposal row: read back `tmm_mi_model_param_proposal_m` by `modelParamProposalId` and show `model_param_proposal_id`, `scenario_id`, `scenario_group_id`, `mi_event_id`, `request_usr_id`, `status`, callback/error fields when available, `proposal_parameters`, and `confirmation_parameters`.
- Proposed parameter summary: for each stored `proposal_parameters[]`, show `parameterName`, model target, slot axis field names, value field names, rationale, value count, and each value row's slot coordinates, `basecaseValue`, `lutValue`, `proposedValue`, and `rationale`.
- Confirmation summary: show a compact result for invalid-payload rejection, valid confirmation, reconfirmation, and optional invalid-status rejection. Include DB before/after details only for `FAIL` or `REVIEW`. Use `N/A` only for an explicitly requested proposal-only run, a proposal that failed before confirmation, or an unavailable invalid-status fixture.

The primary report should not be prompt-packet centric. If prompt inspection is useful or the user asks for it, include prompt input fields in a collapsed appendix/details block after the scenario result. The appendix may summarize the actual Step1.5/Step2/Step3 packets:

- Step1.5 candidate validation: `scenario_brief`, `candidate_validation_tasks`, and each task's `parameter`, `candidate_keys`, `selection_dimensions`
- Step2 slot proposal: `scenario_brief`, `period_resolution_policy`, `slot_selection_limits`, `parameter_slot_tasks`, and each task's `parameter`, `selection_dimensions`, `supporting_dimensions`, `basecase_slot_options`
- Step3 value proposal: `scenario_brief`, `period_resolution_policy`, `basecase_record_selection_policy`, `parameter_value_tasks`, and each task's `parameter`, `selection_dimensions`, `supporting_dimensions`, `selected_slot_axes_field_names`, `selected_slots`, `basecase_value_groups`

When large text, basecase hierarchies, or cells are included, summarize them with character counts and representative samples while preserving field names. For long event/scenario text such as `detail_analysis`, include the field name, `text_chars`, and an excerpt. For final DB `proposal_parameters`, do not omit parameter/value rows unless the report would become unreadable; if rows are summarized, state the omitted count and keep the full DB row JSON in the report.

When the user asks to evaluate a target parameter such as GDP, PMI, PowerMix, Temperature, or LiqUtilAdjustment, include a `Parameter Quality Evaluation` section in the same markdown report. Use this fixed rubric unless the user explicitly overrides it. Render it as a table with columns `No`, `Criteria`, `Judgement`, `Evidence`, and `Improvement`. Use `PASS`, `FAIL`, `REVIEW`, or `N/A` judgements.

1. **파라미터 선정**: Select parameters from the current DB mapping. Include all applicable `direct` candidates, choose at least one appropriate candidate from each applicable `routing` group, and do not select candidates outside the mapping result.
2. **Slot 선정**: Verify that Step2 received Basecase and LUT sample slots when those sources are active and available. Select scenario-relevant slots from the exact Basecase+LUT union without missing required slots or selecting an excessive range.
3. **Value 산정**: Verify that every valid Step3 input slot received one reference sample value and returned one valid result value. The Step3 input slot count, reference sample value count, valid result value count, and final DB value count must match. Use actual Basecase first and the exact LUT default when Basecase is absent; a LUT-only cell may correctly store `basecaseValue=null`.
4. **근거필드 산정**: Verify that parameter- and value-level rationale explains why the parameter, slot, and value were selected and remains consistent with the scenario, coordinates, reference value, and proposed value.
5. **소요시간**: Apply the retry/180-second rules above. Cite the maximum elapsed scenario for the owning group, but do not render a separate slow-case ranking. Do not judge timing merely by whether it was recorded.
6. **Confirmation 성공/실패 케이스**: After each successful proposal, verify that valid confirmation changes `PROPOSED` to `CONFIRMED`. Per scenario group, also verify invalid-payload rollback and `CONFIRMED` reconfirmation; verify invalid-status rollback once per run when a safe existing row is available. Use `N/A` only under the exceptions defined in `Required Confirmation Workflow`.
7. **동일 시나리오 그룹의 다른 시나리오끼리 value 비교**: Compare scenarios in the same group and judge whether differences in intensity, period, region, or other dimension values produce appropriate slot/value differences. Equal values are acceptable when the event provides the same fixed fact; use `N/A` when no comparable scenario, parameter, or slot exists.

For criterion 2, report Basecase sample slot, LUT sample slot, union slot, selected slot, and exact validation counts. A missing source is not a failure when the source is disabled or unavailable for that parameter; explain it as `N/A` evidence.

For criterion 3, use the valid Step3 input after exact validation and truncation as the comparison baseline. Treat any missing reference sample value, missing result value, or mismatch with the final DB value count as `FAIL`. Use `REVIEW` when all values are present but their range, direction, magnitude, or rationale needs human review.

For each criterion, cite concrete evidence from the same report: selected parameter names, mapping methods, scenario dimensions, sample slot/value counts, stored DB proposal row, slot coordinates, `basecaseValue`, LUT reference value when applicable, `proposedValue`, rationale, timing/retry data, and confirmation results. Aggregate these judgements at the top and repeat the evidence-based result under the owning scenario group. If a judgement is `REVIEW` or `FAIL`, add a concrete improvement direction. If a criterion is not applicable, use `N/A` and explain why.

Evaluation must be driven by the current DB mapping state. Do not hardcode expected parameters, selected parameters, routing winners, or success/failure by `scenario_id`, `scenario_group_id`, or `event_type_l2_id`. If DB mapping changes, a scenario may legitimately have no mapping candidates, no validated candidates, or no final recommendations.

Treat `EMPTY_RECOMMENDATIONS` and `routing_result: REVIEW` as report flags, not automatic failures. Do not fix agent code solely because a historical scenario no longer selects a previously expected parameter such as `ShippingCost`; first verify that the parameter is present in the current DB-derived candidate set and that the report shows a real consistency error.

After a run, inspect the report with:

```bash
rg -n "ERROR_COUNT|EMPTY_RECOMMENDATIONS|GROUP_STATUS_BY_SCENARIO_GROUP|그룹 종합: FAIL|mapping_candidate_coverage: FAIL|selected_result: FAIL|routing_result: REVIEW" <report-path>
```

If a test fails because of agent logic, mapping logic, or report generation, fix the smallest relevant code path and rerun the affected scope. Do not modify DB data unless the user explicitly asks.

Only classify a run as failed when the report shows execution errors, broken candidate/result consistency such as unknown selected candidate keys, mapping coverage issues for candidates that actually passed validation, missing Step2/Step3 sample coverage from an active and available source, mismatched Step3 input/result/final DB value counts, a scenario execution time over 180 seconds, required confirmation contract violations, or explicit expectations provided by the user for that run.

## Final Response

Report the markdown file path, scenario/event scope, `ERROR_COUNT`, group pass/fail summary, maximum elapsed scenario, confirmation success/failure summary, and any notable empty recommendations or review flags. Do not duplicate the raw API response in chat or in the markdown report; the markdown report must keep the final DB proposal row as the single source for stored proposal data.
