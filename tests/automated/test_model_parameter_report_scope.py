# ruff: noqa: S101

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from tests.manual.model_parameter_agent import evaluate_proposals as proposal_evaluation
from tests.manual.model_parameter_agent.evaluate_event_type_proposals import (
    EventTypeTarget,
    _build_parameter_scenario_targets,
    _discover_parameter_scenario_targets,
    _discover_targets,
    _failed_scenario_detail_lines,
    _group_status,
    _lut_summary_line,
    _parse_parameter_scenarios,
    _proposal_parameters_from_record,
    _proposal_value_table_lines,
    _records_for_target,
    _render_report,
    _scenario_result_summary,
    _scenario_result_table_lines,
    _scenario_token_summary,
    _timing_special_note,
    _timing_special_summary,
)
from tests.manual.model_parameter_agent.evaluate_proposals import (
    _build_step_summary,
    _value_reference_records,
)


TARGET_PARAMETERS = (
    "GDP",
    "PMI",
    "PowerMix",
    "Temperature",
    "LiqUtilAdjustment",
)


def test_report_uses_runtime_proposal_values_to_preserve_lut_reference() -> None:
    runtime_parameter = {
        "parameterName": "GDP",
        "values": [{"basecaseValue": 0.01, "lutValue": 0.02, "proposedValue": 0.005}],
    }
    db_parameter = {
        "parameterName": "GDP",
        "values": [{"basecaseValue": 0.01, "proposedValue": 0.005}],
    }

    parameters = _proposal_parameters_from_record(
        {
            "final_response": {"data": {"proposalParameters": [runtime_parameter]}},
            "proposal_db_row": {"proposal_parameters": [db_parameter]},
        },
    )

    assert parameters == [runtime_parameter]


@pytest.mark.parametrize(
    ("elapsed_seconds", "attempts", "failed", "expected"),
    [
        (60.0, 1, False, "PASS · 특이사항 없음 (retry 0회, 180초 이내)"),
        (60.0, 2, False, "REVIEW · outer retry 1회, 180초 이내"),
        (181.0, 1, False, "FAIL · 180초 초과 (181.000s, outer retry 0회)"),
        (None, 1, False, "REVIEW · 소요시간 미수집 (outer retry 0회)"),
        (30.0, 2, True, "FAIL · 최종 실패 (outer retry 1회)"),
    ],
)
def test_timing_special_note(
    elapsed_seconds: float | None,
    attempts: int,
    *,
    failed: bool,
    expected: str,
) -> None:
    assert (
        _timing_special_note(
            elapsed_seconds=elapsed_seconds,
            attempts=attempts,
            failed=failed,
        )
        == expected
    )


def test_timing_special_summary_aggregates_attention_scenarios() -> None:
    summary = _timing_special_summary(
        [
            {"scenario_id": 1, "elapsed_seconds": 60.0, "attempt": 1},
            {"scenario_id": 2, "elapsed_seconds": 60.0, "attempt": 2},
            {"scenario_id": 3, "elapsed_seconds": 181.0, "attempt": 1},
        ],
        [{"scenario_id": 4}],
    )

    assert summary == (
        "PASS 1건, REVIEW 1건, FAIL 2건; "
        "확인 필요 scenario_ids=[2, 3, 4]; "
        "최장 scenario_id=3 (181.000s)"
    )


def test_failed_timing_note_includes_compact_error() -> None:
    note = _timing_special_note(
        elapsed_seconds=30.0,
        attempts=2,
        failed=True,
        error="Step3\n504 Gateway Time-out",
    )

    assert note == (
        "FAIL · 최종 실패 (outer retry 1회): "
        "Step3 504 Gateway Time-out"
    )


def test_scenario_result_summary_covers_success_timing_and_mapping_failure() -> None:
    success_record = {
        "mapping_ok": True,
        "selected_ok": True,
        "routing_status": "PASS",
        "elapsed_seconds": 60.0,
        "attempt": 1,
        "final_response": {
            "data": {"proposalParameters": [{"parameterName": "GDP"}]},
        },
    }
    assert _scenario_result_summary(record=success_record) == "PASS · proposal 생성 및 검증 완료"

    slow_record = {**success_record, "elapsed_seconds": 181.0}
    assert _scenario_result_summary(record=slow_record).startswith(
        "FAIL · proposal 성공, 180초 초과",
    )

    mapping_error = {
        "error": "No model parameter mapping candidates found for scenario_id=619",
    }
    assert _scenario_result_summary(error=mapping_error) == "FAIL · 매핑 후보 없음"


def test_scenario_result_table_includes_failed_execution() -> None:
    target = EventTypeTarget(
        1,
        "Upstream Utilization 변동",
        100,
        "노르웨이 해상 시추 중단",
        (619,),
    )
    lines = _scenario_result_table_lines(
        targets=(target,),
        records=[],
        errors=[
            {
                "target": target,
                "scenario_id": 619,
                "error": "No model parameter mapping candidates found for scenario_id=619",
                "elapsed_seconds": 3.391,
            },
        ],
        target_parameters=("LiqUtilAdjustment",),
        target_event_type_l2_ids_by_parameter={"LiqUtilAdjustment": (1,)},
    )

    assert len([line for line in lines if line.startswith("| 100 ·")]) == 1
    assert "| 619 | 1 · Upstream Utilization 변동 | LiqUtilAdjustment |" in lines[-1]
    assert "FAIL · 매핑 후보 없음 | 00:03.391 (3.391s) | N/A |" in lines[-1]


def test_failed_scenario_detail_includes_context_and_attempt_stage_tracing() -> None:
    context = {
        "scenario": {
            "scenario_id": 637,
            "scenario_group_id": 105,
            "title": "단기 고가동 뒤 빠르게 정상화",
            "narrative": "단기 흡수력 증가 후 정상화된다.",
            "dimension_values": {"period": "1개월"},
        },
    }
    step_summary = {
        "termination_stage": "Step2 종료 - selected slot 없음",
        "rule_candidate_count": 2,
        "validated_candidate_count": 1,
        "selected_slot_count": 0,
        "slot_basecase_record_count": 21656,
        "value_cell_count": 0,
    }
    attempt_trace = {
        "context": context,
        "attempt": 1,
        "elapsed_seconds": 25.5,
        "failed_stage": "output validation/persistence",
        "error": "No valid model parameter proposal parameters generated",
        "expected_candidates": [
            {"canonical_parameter_name": "LiqUtilAdjustment"},
        ],
        "result": {
            "parameter_adjustments": [],
            "validation_warnings": ["Step2 selected slot 없음"],
        },
        "step_summary": step_summary,
        "llm_calls": [
            {
                "step": "Step2 slot proposal",
                "success": True,
                "model_name": "gpt-test",
                "elapsed_seconds": 20.0,
                "usage": {
                    "prompt_tokens": 1000,
                    "completion_tokens": 50,
                    "total_tokens": 1050,
                },
            },
        ],
    }
    error = {
        "scenario_id": 637,
        "context": context,
        "error": "No valid model parameter proposal parameters generated",
        "attempts": 2,
        "elapsed_seconds": 53.611,
        "attempt_traces": [
            attempt_trace,
            {**attempt_trace, "attempt": 2, "elapsed_seconds": 26.0},
        ],
    }

    report = "\n".join(
        _failed_scenario_detail_lines(
            error,
            heading_level=5,
            target_parameter="LiqUtilAdjustment",
        ),
    )

    assert "##### scenario_id=637 단기 고가동 뒤 빠르게 정상화" in report
    assert "###### Scenario Major Info" in report
    assert '"period": "1개월"' in report
    assert "###### Attempt별 단계 Tracing" in report
    assert "**Attempt 1**" in report
    assert "**Attempt 2**" in report
    assert "| Step1 mapping | PASS | rule_candidates=2 |" in report
    assert "| Step1.5 candidate validation | PASS | validated_candidates=1 |" in report
    assert "| Step2 slot proposal/filter | FAIL |" in report
    assert "| Step3 value proposal | SKIPPED |" in report
    assert "| Output validation/persistence | FAIL |" in report
    assert "| Step2 slot proposal | True | gpt-test | 00:20.000 | 20.000 | 1000 | 50 | 1050 |" in report
    assert "Confirmation: N/A · proposal 실패로 미수행" in report


def test_evaluate_scenario_preserves_partial_trace_on_output_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = {
        "scenario": {
            "scenario_id": 637,
            "scenario_group_id": 105,
            "title": "단기 고가동 뒤 빠르게 정상화",
        },
    }
    candidate = {
        "candidate_key": "liq",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "model_file": "model.xlsx",
        "model_sheet": "LiqUtilAdjustment",
        "mapping_method": "direct",
    }

    class FakeService:
        def load_context(self, scenario_id: int) -> dict[str, object]:
            assert scenario_id == 637
            return context

    class FakeGraph:
        async def ainvoke(self, _state: object) -> dict[str, object]:
            return {
                "candidate_mappings": [candidate],
                "parameter_slots": [],
                "parameter_adjustments": [
                    {
                        "candidate_key": "liq",
                        "parameter_name": "LiqUtilAdjustment",
                        "model_file": "model.xlsx",
                        "model_sheet": "LiqUtilAdjustment",
                        "selected": False,
                    },
                ],
                "validation_warnings": ["Step2 selected slot 없음"],
                "llm_calls": [
                    {
                        "step": "Step2 slot proposal",
                        "success": True,
                        "usage": {
                            "prompt_tokens": 100,
                            "completion_tokens": 10,
                            "total_tokens": 110,
                        },
                    },
                ],
            }

    def raise_output_error(_state: object) -> None:
        raise RuntimeError("No valid model parameter proposal parameters generated")

    monkeypatch.setattr(proposal_evaluation, "ModelParameterService", FakeService)
    monkeypatch.setattr(
        proposal_evaluation,
        "get_parameter_knowledge_base",
        lambda _basecase_dir=None: object(),
    )
    monkeypatch.setattr(
        proposal_evaluation,
        "match_parameter_candidates",
        lambda _kb, _context: ([candidate], [], []),
    )
    monkeypatch.setattr(proposal_evaluation, "RAW_GRAPH", FakeGraph())
    monkeypatch.setattr(
        proposal_evaluation,
        "build_basecase_records",
        lambda _kb, _candidates, _context: ([], []),
    )
    monkeypatch.setattr(proposal_evaluation, "to_output", raise_output_error)

    with pytest.raises(RuntimeError) as caught:
        asyncio.run(proposal_evaluation._evaluate_scenario(637))

    trace = proposal_evaluation._failure_trace_from_exception(caught.value)
    assert trace["context"] == context
    assert trace["failed_stage"] == "output validation/persistence"
    assert trace["step_summary"]["termination_stage"] == "Step2 종료 - selected slot 없음"
    assert trace["step_summary"]["validated_candidate_count"] == 1
    assert trace["step_summary"]["selected_slot_count"] == 0
    assert trace["llm_calls"][0]["usage"]["total_tokens"] == 110


def test_scenario_token_summary_sums_all_recorded_llm_calls() -> None:
    assert _scenario_token_summary(
        {
            "llm_calls": [
                {
                    "step": "Step2",
                    "usage": {
                        "prompt_tokens": 1234,
                        "completion_tokens": 56,
                        "total_tokens": 1290,
                    },
                },
                {
                    "step": "Step3",
                    "usage": {
                        "prompt_tokens": 2000,
                        "completion_tokens": 100,
                        "total_tokens": 2100,
                    },
                },
            ],
        },
    ) == "3,234 / 156 / 3,390"


@pytest.mark.parametrize(
    ("record", "expected"),
    [
        ({"llm_calls": []}, "0 / 0 / 0"),
        (None, "N/A"),
        ({"llm_calls": [{"step": "Step2"}]}, "N/A"),
    ],
)
def test_scenario_token_summary_handles_unavailable_usage(
    record: dict[str, object] | None,
    expected: str,
) -> None:
    assert _scenario_token_summary(record) == expected


def test_proposal_value_table_includes_basecase_and_lut_samples() -> None:
    lines = _proposal_value_table_lines(
        [
            {
                "parameterName": "GDP",
                "modelTarget": {"slotAxesFieldNames": ["Country", "Year"]},
                "values": [
                    {
                        "Country": "Germany",
                        "Year": 2026,
                        "basecaseValue": 0.01,
                        "lutValue": 0.02,
                        "proposedValue": 0.005,
                        "rationale": "event forecast",
                    },
                ],
            },
        ],
    )

    report = "\n".join(lines)
    assert "| basecaseValue | lutValue | proposedValue |" in report
    assert "| 0.01 | 0.02 | 0.005 |" in report


def test_parameter_scenarios_are_validated_and_ordered_by_target_parameter() -> None:
    selections = _parse_parameter_scenarios(
        (
            "Temperature=289",
            "GDP=305",
            "LiqUtilAdjustment=105",
            "PowerMix=287",
            "PMI=306",
        ),
        TARGET_PARAMETERS,
    )

    assert [selection.parameter_name for selection in selections] == list(TARGET_PARAMETERS)
    assert [selection.scenario_ids for selection in selections] == [
        (305,),
        (306,),
        (287,),
        (289,),
        (105,),
    ]


def test_parameter_scenarios_accept_multiple_scenarios_per_parameter() -> None:
    selections = _parse_parameter_scenarios(
        ("GDP=305,307", "PMI=306,308"),
        ("GDP", "PMI"),
    )

    assert [selection.scenario_ids for selection in selections] == [
        (305, 307),
        (306, 308),
    ]


def test_empty_parameter_scenario_scope_preserves_existing_discovery_mode() -> None:
    assert _parse_parameter_scenarios((), TARGET_PARAMETERS) == ()

    target = EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (305, 306))
    records = [
        {"target": target, "scenario_id": 305},
        {"target": target, "scenario_id": 306},
    ]
    assert _records_for_target(target, records) == records


@pytest.mark.parametrize(
    "raw_value",
    ["GDP", "=305", "GDP=", "GDP=not-an-int", "GDP=0", "GDP=305=extra"],
)
def test_parameter_scenarios_reject_malformed_entries(raw_value: str) -> None:
    with pytest.raises(ValueError, match=r"parameter-scenarios|scenario id"):
        _parse_parameter_scenarios((raw_value,), ("GDP",))


def test_parameter_scenarios_reject_duplicate_parameter_and_scenario() -> None:
    with pytest.raises(ValueError, match="duplicate parameter"):
        _parse_parameter_scenarios(("GDP=305", "gdp=306"), ("GDP",))

    with pytest.raises(ValueError, match="duplicate scenario id"):
        _parse_parameter_scenarios(
            ("GDP=305", "PMI=305"),
            ("GDP", "PMI"),
        )

    with pytest.raises(ValueError, match="duplicate scenario id"):
        _parse_parameter_scenarios(("GDP=305,305",), ("GDP",))


def test_parameter_scenarios_must_match_target_parameters_exactly() -> None:
    with pytest.raises(ValueError, match="match --target-parameters exactly"):
        _parse_parameter_scenarios(
            ("GDP=305", "PowerMix=287"),
            ("GDP", "PMI"),
        )


def test_parameter_scenario_targets_create_requested_executions_per_parameter() -> None:
    selections = _parse_parameter_scenarios(
        (
            "GDP=305,307",
            "PMI=306,308",
            "PowerMix=287,288",
            "Temperature=289,290",
            "LiqUtilAdjustment=105,106",
        ),
        TARGET_PARAMETERS,
    )
    targets = _build_parameter_scenario_targets(
        selections,
        [
            (105, 2, 18, "Cameron LNG", "터미널 Utilization 변동"),
            (106, 2, 18, "Cameron LNG", "터미널 Utilization 변동"),
            (287, 5, 51, "발전 차질", "발전소 Utilization 변동"),
            (288, 5, 51, "발전 차질", "발전소 Utilization 변동"),
            (289, 6, 52, "겨울 한파", "겨울 한파"),
            (290, 6, 52, "겨울 한파", "겨울 한파"),
            (305, 21, 60, "국가별 경기", "국가별 경기"),
            (306, 21, 60, "국가별 경기", "국가별 경기"),
            (307, 21, 60, "국가별 경기", "국가별 경기"),
            (308, 21, 60, "국가별 경기", "국가별 경기"),
        ],
    )

    assert len(targets) == 5
    assert sum(len(target.scenario_ids) for target in targets) == 10
    assert {target.target_parameter: target.scenario_ids for target in targets} == {
        "GDP": (305, 307),
        "PMI": (306, 308),
        "PowerMix": (287, 288),
        "Temperature": (289, 290),
        "LiqUtilAdjustment": (105, 106),
    }


def test_parameter_scenario_targets_reject_missing_scenario() -> None:
    selections = _parse_parameter_scenarios(("GDP=999999",), ("GDP",))

    with pytest.raises(ValueError, match=r"missing or deleted scenarios: \[999999\]"):
        _build_parameter_scenario_targets(selections, [])


def test_parameter_scenario_targets_reject_scenarios_from_different_groups() -> None:
    selections = _parse_parameter_scenarios(("GDP=305,307",), ("GDP",))

    with pytest.raises(ValueError, match="must belong to one scenario group"):
        _build_parameter_scenario_targets(
            selections,
            [
                (305, 21, 60, "국가별 경기 A", "국가별 경기"),
                (307, 21, 61, "국가별 경기 B", "국가별 경기"),
            ],
        )


def test_parameter_scenario_discovery_joins_scenario_group_event_relation() -> None:
    selections = _parse_parameter_scenarios(("GDP=305",), ("GDP",))
    result = Mock()
    result.all.return_value = [(305, 21, 60, "국가별 경기", "국가별 경기")]
    session = Mock()
    session.execute.return_value = result

    with patch(
        "apps.common.configs.database.sync_database.connection.get_sync_session",
        return_value=session,
    ):
        targets = _discover_parameter_scenario_targets(selections)

    statement = str(session.execute.call_args.args[0])
    assert "JOIN tmm_mi_scenario_group_event_m" in statement
    assert "tmm_mi_scenario_group_event_m.event_type_l2_id" in statement
    assert targets == (EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (305,), "GDP"),)
    session.close.assert_called_once_with()


def test_event_type_target_discovery_joins_relation_without_duplicate_scenarios() -> None:
    label_result = Mock()
    label_result.all.return_value = [(21, "국가별 경기")]
    group_result = Mock()
    group_result.all.return_value = [(21, 60, "국가별 경기")]
    scenario_result = Mock()
    scenario_result.all.return_value = [(60, 305, 0)]
    session = Mock()
    session.execute.side_effect = [label_result, group_result, scenario_result]

    with patch(
        "apps.common.configs.database.sync_database.connection.get_sync_session",
        return_value=session,
    ):
        targets = _discover_targets((21,))

    group_statement = str(session.execute.call_args_list[1].args[0])
    scenario_statement = str(session.execute.call_args_list[2].args[0])
    assert "JOIN tmm_mi_scenario_group_event_m" in group_statement
    assert "JOIN tmm_mi_scenario_group_event_m" in scenario_statement
    assert group_statement.startswith("SELECT DISTINCT")
    assert scenario_statement.startswith("SELECT DISTINCT")
    assert "tmm_mi_scenario_m.display_order" in scenario_statement
    assert targets == (EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (305,)),)
    session.close.assert_called_once_with()


def test_explicit_parameter_targets_do_not_mix_scenarios_in_the_same_group() -> None:
    gdp_target = EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (305,), "GDP")
    pmi_target = EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (306,), "PMI")
    records = [
        {"target": gdp_target, "scenario_id": 305},
        {"target": pmi_target, "scenario_id": 306},
    ]

    assert [record["scenario_id"] for record in _records_for_target(gdp_target, records)] == [305]
    assert [record["scenario_id"] for record in _records_for_target(pmi_target, records)] == [306]


def test_explicit_parameter_status_requires_target_candidate_and_selection() -> None:
    target = EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (305,), "GDP")

    def record(*, expected_parameter: str, selected_parameter: str) -> dict[str, object]:
        return {
            "target": target,
            "scenario_id": 305,
            "expected_candidates": [
                {"canonical_parameter_name": expected_parameter},
            ],
            "result": {
                "parameter_adjustments": [
                    {"parameter_name": selected_parameter, "selected": True},
                ],
            },
            "mapping_ok": True,
            "selected_ok": True,
        }

    assert _group_status(
        target,
        [record(expected_parameter="GDP", selected_parameter="GDP")],
        [],
    )
    assert not _group_status(
        target,
        [record(expected_parameter="GDP", selected_parameter="PMI")],
        [],
    )
    assert not _group_status(
        target,
        [record(expected_parameter="PMI", selected_parameter="GDP")],
        [],
    )


def test_lut_summary_line_is_compact() -> None:
    line = _lut_summary_line(
        [
            {
                "resolved_config": {"model_parameter_lut_enabled": True},
                "lut_version": "lut-v1",
            },
        ],
    )

    assert line == "- LUT: enabled, version=lut-v1"
    assert "Reference Runtime" not in line


def test_step_summary_uses_effective_references_with_per_candidate_cap() -> None:
    effective_references = [
        {"candidate_key": candidate_key, "axes": {"Year": index}}
        for candidate_key in ("gdp", "pmi")
        for index in range(60)
    ]
    assert (
        _value_reference_records(
            {
                "effective_references": effective_references,
                "basecase_records": [{"candidate_key": "legacy"}],
            },
        )
        == effective_references
    )
    assert _value_reference_records(
        {"basecase_records": [{"candidate_key": "legacy"}]},
    ) == []
    assert _value_reference_records(
        {
            "effective_references": [],
            "basecase_records": [{"candidate_key": "legacy"}],
        },
    ) == []

    summary = _build_step_summary(
        rule_candidates=[{"candidate_key": "gdp"}, {"candidate_key": "pmi"}],
        validated_candidates=[
            {"candidate_key": "gdp"},
            {"candidate_key": "pmi"},
        ],
        parameter_slots=[
            {"candidate_key": "gdp", "selected": True, "slot_axes": []},
            {"candidate_key": "pmi", "selected": True, "slot_axes": []},
        ],
        slot_basecase_records=[{"candidate_key": "gdp"}],
        slot_options=[],
        value_reference_records=effective_references,
        adjustments=[],
        final_response={"data": {"proposalParameters": []}},
        llm_calls=[{"step": "Step3"}],
        routing_status="PASS",
    )

    assert summary["basecase_status"] == "PASS"
    assert summary["value_reference_record_count"] == 120
    assert summary["value_reference_counts_by_candidate"] == {
        "gdp": 60,
        "pmi": 60,
    }


def test_parameter_report_keeps_same_group_scenarios_in_their_parameter_sections() -> None:
    gdp_target = EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (305,), "GDP")
    pmi_target = EventTypeTarget(21, "국가별 경기", 60, "국가별 경기", (306,), "PMI")

    def record(target: EventTypeTarget) -> dict[str, object]:
        scenario_id = target.scenario_ids[0]
        return {
            "target": target,
            "scenario_id": scenario_id,
            "context": {
                "scenario": {
                    "scenario_id": scenario_id,
                    "scenario_group_id": 60,
                    "title": f"scenario-{scenario_id}",
                    "dimension_values": {},
                },
                "scenario_group": {
                    "scenario_group_id": 60,
                    "event_type_l2_id": 21,
                    "title": "국가별 경기",
                },
                "event": {},
                "event_type": {},
                "dimension_template": [],
                "parameter_mapping_resources": {
                    "mapping_rules": [],
                    "parameter_definitions": [],
                },
            },
            "expected_candidates": [],
            "result": {"parameter_adjustments": []},
            "final_response": {"data": {"proposalParameters": []}},
            "proposal_db_row": {},
            "mapping_ok": True,
            "selected_ok": True,
            "routing_status": "N/A",
            "mapping_messages": [],
            "selected_messages": [],
            "routing_messages": [],
            "mapping_warnings": [],
            "basecase_warnings": [],
            "step_summary": {},
            "llm_calls": [
                {
                    "step": "Step2",
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 20,
                        "total_tokens": 120,
                    },
                },
                {
                    "step": "Step3",
                    "usage": {
                        "prompt_tokens": 50,
                        "completion_tokens": 10,
                        "total_tokens": 60,
                    },
                },
            ],
            "elapsed_seconds": 1.0,
            "attempt": 1,
            "resolved_config": {"model_parameter_lut_enabled": True},
            "lut_version": "lut-v1",
        }

    report = _render_report(
        started_at=datetime(2026, 7, 10, 12, 0, 0, tzinfo=UTC),
        finished_at=datetime(2026, 7, 10, 12, 0, 2, tzinfo=UTC),
        event_type_l2_ids=(21,),
        targets=(gdp_target, pmi_target),
        records=[record(gdp_target), record(pmi_target)],
        errors=[],
        concurrency=2,
        retries=0,
        target_parameters=("GDP", "PMI"),
        target_event_type_l2_ids_by_parameter={"GDP": (21,), "PMI": (21,)},
    )

    gdp_section, pmi_and_summary = report.split("### Parameter: GDP", 1)[1].split(
        "### Parameter: PMI",
        1,
    )
    pmi_section = pmi_and_summary.split("## 최종 요약", 1)[0]
    assert "scenario_id=305" in gdp_section
    assert "scenario_id=306" not in gdp_section
    assert "scenario_id=306" in pmi_section
    assert "scenario_id=305" not in pmi_section
    assert "PLANNED_SCENARIO_EXECUTIONS: 2" in report
    assert "COMPLETED_SCENARIO_EXECUTIONS: 2" in report
    assert "scenario_group 1개, scenario 2개" in report
    assert "PARAMETER_SCENARIO_STATUS" in report
    assert '"GDP": {"passed": false, "scenario_ids": [305]}' in report
    assert '"PMI": {"passed": false, "scenario_ids": [306]}' in report
    assert "Reference Runtime" not in report
    assert "LUT: enabled, version=lut-v1" in report
    assert "## 소요시간 특이사항 요약" in report
    assert "PASS 2건, REVIEW 0건, FAIL 0건" in report
    assert report.count("- 소요시간 특이사항:") == 3
    target_summary_index = report.index("## 대상 요약")
    scenario_table_index = report.index("### 시나리오별 결과")
    result_index = report.index("## 호출 결과")
    assert target_summary_index < scenario_table_index < result_index
    assert (
        "| 시나리오그룹 | 시나리오 | 이벤트타입 | 파라미터 | 결과요약 | 소요시간 | Token (입력/출력/합계) |"
        in report
    )
    assert "| 60 · 국가별 경기 | 305 · scenario-305 | 21 · 국가별 경기 | GDP |" in report
    assert "| 60 · 국가별 경기 | 306 · scenario-306 | 21 · 국가별 경기 | PMI |" in report
    assert report[scenario_table_index:result_index].count("| 150 / 30 / 180 |") == 2
    assert report[scenario_table_index:result_index].count("\n| 60 · 국가별 경기 |") == 2
    assert "느린 테스트케이스 상위 10%" not in report
    assert "최장 scenario_id=305 (1.000s)" in report
    assert "lut-v1" in report
