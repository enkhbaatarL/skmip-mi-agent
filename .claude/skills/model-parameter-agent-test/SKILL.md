---
name: model-parameter-agent-test
description: Run and document MI 수급모델파라미터 proposal agent tests against the current DB mapping state. Use when the user asks to test one scenario, asks "xxx 시나리오 테스트해줘", asks "모든 이벤트타입에 해당하는 시나리오그룹 1개씩 테스트해줘", or asks to test 폭염/폭엄/한파 event type scenarios and write markdown result files.
---

# Model Parameter Agent Test

## Overview

Run 수급모델파라미터 proposal tests from `/Users/messiah/skg-mi/skmip-mi-agent` and write markdown reports under `tests/reports/model_parameter_agent/`.

Use `poetry run` from the repo root. Do not start the API server for these tests.

## Request Mapping

For a single scenario request such as `289 시나리오 테스트해줘` or `scenario_id=289 테스트해줘`, run:

```bash
poetry run python .claude/skills/model-parameter-agent-test/scripts/run_single_scenario_report.py --scenario-id 289 --max-candidates 30
```

If the user provides a scenario title instead of an id, resolve the `scenario_id` from local `midb` by searching scenario title, scenario group title, and event title. If there are multiple plausible matches, ask the user to choose.

For `모든 이벤트타입에 해당하는 시나리오그룹 1개씩 테스트해줘`, run one scenario group per event type and two scenarios per group:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --all-event-types --groups-per-event 1 --scenarios-per-group 2 --concurrency 4 --retries 1 --max-candidates 30
```

For `폭염/한파 이벤트타입에 해당하는 시나리오 테스트해줘`, include event_type_l2_id `6` (겨울 한파) and `7` (여름 폭염). Treat the typo `폭엄` as `폭염`. By default, test all existing groups/scenarios for these two event types:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --event-type-l2-ids 6 7 --concurrency 4 --retries 1 --max-candidates 30
```

If the user explicitly says `1개씩`, `샘플`, or asks for a quick check, add `--groups-per-event 1 --scenarios-per-group 2`.

If the user specifies one or more target parameters such as `GDP`, `PMI`, `PowerMix`, `Temperature`, or `LiqUtilAdjustment`, use parameter mode. The script resolves event types where the parameter is a current DB `direct` or `routing` mapping candidate, then writes the report body in `parameter -> event_type -> scenario` order:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --target-parameters GDP --groups-per-event 1 --scenarios-per-group 2 --concurrency 4 --retries 1 --max-candidates 30
```

If the user specifies both target parameters and explicit event types, keep the explicit event type scope while still rendering the report in `parameter -> event_type -> scenario` order:

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_event_type_proposals.py --target-parameters GDP PMI --event-type-l2-ids 1 2 4 --groups-per-event 1 --scenarios-per-group 2 --concurrency 4 --retries 1 --max-candidates 30
```

## Report Handling

Use the report path printed as `REPORT` or `REPORT_IN_PROGRESS`. Event-type evaluation updates the markdown as scenarios finish, so the partial report can be inspected while the run continues.

Write one integrated markdown report per user test request. If an automated script already created a markdown report, append any parameter-specific quality evaluation, findings, and improvement plan to that same file instead of creating a second markdown file. Do not split "raw execution result" and "quality evaluation" into separate report files unless the user explicitly asks for separate files.

Report ordering depends on the user's requested scope:

- If the user specifies event types, scenario groups, or scenarios, keep the current `event_type -> scenario_group -> scenario` order.
- If the user specifies target parameters, write the main result body in `parameter -> event_type -> scenario` order. The scenario subsection should filter the proposed parameter summary/value tables to the current parameter, while the final DB proposal row remains the full stored row for traceability.

For event-type or multi-scenario runs that use `tests/manual/model_parameter_agent/evaluate_event_type_proposals.py`, treat the generated `REPORT` file as the base integrated report. Before the final response, make sure the same `REPORT` path contains the scenario group, dimension template, event, scenario major information, final DB proposal row, proposed parameter/value details, and parameter-specific quality evaluation. Prompt packet details are appendix material, not the primary report structure.

Every markdown report must include scenario-level execution time and per-LLM-call execution time. A scenario section should show total scenario elapsed time, and a `모델 호출별 소요시간` table with Step1.5 candidate validation, Step2 slot proposal, and Step3 value proposal rows when those LLM calls were executed.

Every markdown report must make the information needed for human proposal review visible in this order:

1. `Scenario Group`: show the DB-loaded scenario group once per group, including `scenario_group_id`, `mi_event_id`, `event_type_l2_id`, event type labels, `title`, `summary`, `description`, `dimension_selected`, `scenario_count`, `status`, and `stage`.
2. `Dimension Template`: show the full `dimension_template` rows for the event type, including dimension key/label/required/options when present.
3. `Dimension -> Parameter Mapping`: immediately below the dimension template, show DB-loaded dimension-to-parameter mapping rows for the same `event_type_l2_id`. Keep this compact. Include source tables, `mapping_count`, and for each row only `dimension`, `mapping_method`, `parameter`, and `comment`.
4. `Event`: show the DB-loaded event once under the group, including `mi_event_id`, `event_type_l2_id`, `event_title_ko`, `one_line_summary`, date fields, source record ids, `key_bullets`, `tags`, and bounded `detail_analysis`.
5. `Scenarios`: for each scenario in the group, show scenario major information and the actual final DB proposal row.

For each scenario subsection, include:

- Scenario major information: `scenario_id`, `scenario_group_id`, `title`, bounded `narrative`, `status`, `dimension_values`, probability/impact fields, and `baseline_yn`.
- Validation summary: expected/validated parameter candidates, selected parameters, mapping/selection/routing status, and warnings.
- Final DB proposal row: read back `tmm_mi_model_param_proposal_m` by `modelParamProposalId` and show `model_param_proposal_id`, `scenario_id`, `scenario_group_id`, `mi_event_id`, `request_usr_id`, `status`, callback/error fields when available, `proposal_parameters`, and `confirmation_parameters`.
- Proposed parameter summary: for each stored `proposal_parameters[]`, show `parameterName`, model target, slot axis field names, value field names, rationale, value count, and each value row's slot coordinates, `basecaseValue`, `proposedValue`, and `rationale`.

The primary report should not be prompt-packet centric. If prompt inspection is useful or the user asks for it, include prompt input fields in a collapsed appendix/details block after the scenario result. The appendix may summarize the actual Step1.5/Step2/Step3 packets:

- Step1.5 candidate validation: `scenario_brief`, `candidate_validation_tasks`, and each task's `parameter`, `candidate_keys`, `selection_dimensions`
- Step2 slot proposal: `scenario_brief`, `period_resolution_policy`, `slot_selection_limits`, `parameter_slot_tasks`, and each task's `parameter`, `selection_dimensions`, `supporting_dimensions`, `basecase_slot_options`
- Step3 value proposal: `scenario_brief`, `period_resolution_policy`, `basecase_record_selection_policy`, `parameter_value_tasks`, and each task's `parameter`, `selection_dimensions`, `supporting_dimensions`, `selected_slot_axes_field_names`, `selected_slots`, `basecase_value_groups`

When large text, basecase hierarchies, or cells are included, summarize them with character counts and representative samples while preserving field names. For long event/scenario text such as `detail_analysis`, include the field name, `text_chars`, and an excerpt. For final DB `proposal_parameters`, do not omit parameter/value rows unless the report would become unreadable; if rows are summarized, state the omitted count and keep the full DB row JSON in the report.

When the user asks to evaluate a target parameter such as GDP, PMI, PowerMix, Temperature, or LiqUtilAdjustment, include a `Parameter Quality Evaluation` section in the same markdown report. Use this fixed rubric unless the user explicitly overrides it. Render it as a table with columns `No`, `Criteria`, `Judgement`, `Evidence`, and `Improvement`. Use `PASS`, `FAIL`, `REVIEW`, or `N/A` judgements.

1. 파라미터가 정확히 선정되었나. `direct` mapping candidates must be selected. For `routing` candidates, at least one candidate in the routing group must be selected.
2. slot이 정확히 선정되고 slot의 값이나 범위가 유효한 값인가. Pay special attention to ambiguous country/year/month/period interpretation.
3. slot이 basecase 기반으로 선정된 경우 개연성이 있는가.
4. slot이 basecase에 없지만 시나리오/이벤트 정보를 활용해 추가 선정된 경우 개연성이 있는가.
5. slot이 basecase에 없는 경우를 선정하지 못했다면 선정해도 될 가능성이 없었는가.
6. value가 지정된 범위나 형식으로 선정되었나. Also judge whether the scenario/event information plausibly supports the recommended value.
7. value가 basecase에 있는 경우 적절하게 변경되었나.
8. value가 basecase에 없었던 경우 개연성 있게 선정되었나.
9. 동일 그룹의 시나리오 사이에 dimension value에 따라 해당 value가 적절한 차이를 보이는가.

For each criterion, cite concrete evidence from the same report: selected parameter names, mapping methods, candidate keys, scenario group dimensions, scenario `dimension_values`, stored DB proposal row, slot coordinates, `basecaseValue`, `proposedValue`, and rationale. If a judgement is `REVIEW` or `FAIL`, add a concrete improvement direction. If a criterion is not applicable because no such slot/value exists, use `N/A` and explain why.

Evaluation must be driven by the current DB mapping state. Do not hardcode expected parameters, selected parameters, routing winners, or success/failure by `scenario_id`, `scenario_group_id`, or `event_type_l2_id`. If DB mapping changes, a scenario may legitimately have no mapping candidates, no validated candidates, or no final recommendations.

Treat `EMPTY_RECOMMENDATIONS` and `routing_result: REVIEW` as report flags, not automatic failures. Do not fix agent code solely because a historical scenario no longer selects a previously expected parameter such as `ShippingCost`; first verify that the parameter is present in the current DB-derived candidate set and that the report shows a real consistency error.

After a run, inspect the report with:

```bash
rg -n "ERROR_COUNT|EMPTY_RECOMMENDATIONS|GROUP_STATUS_BY_SCENARIO_GROUP|그룹 종합: FAIL|mapping_candidate_coverage: FAIL|selected_result: FAIL|routing_result: REVIEW" <report-path>
```

If a test fails because of agent logic, mapping logic, or report generation, fix the smallest relevant code path and rerun the affected scope. Do not modify DB data unless the user explicitly asks.

Only classify a run as failed when the report shows execution errors, broken candidate/result consistency such as unknown selected candidate keys, mapping coverage issues for candidates that actually passed validation, or explicit expectations provided by the user for that run.

## Final Response

Report the markdown file path, scenario/event scope, `ERROR_COUNT`, group pass/fail summary, and any notable empty recommendations or review flags. Do not duplicate the raw API response in chat or in the markdown report; the markdown report must keep the final DB proposal row as the single source for stored proposal data.
