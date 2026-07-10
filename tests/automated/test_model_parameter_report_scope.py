# ruff: noqa: S101

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from tests.manual.model_parameter_agent.evaluate_event_type_proposals import (
    EventTypeTarget,
    _build_parameter_scenario_targets,
    _group_status,
    _parse_parameter_scenarios,
    _records_for_target,
    _render_report,
    _runtime_reference_lines,
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
    assert [selection.scenario_id for selection in selections] == [305, 306, 287, 289, 105]


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


def test_parameter_scenarios_must_match_target_parameters_exactly() -> None:
    with pytest.raises(ValueError, match="match --target-parameters exactly"):
        _parse_parameter_scenarios(
            ("GDP=305", "PowerMix=287"),
            ("GDP", "PMI"),
        )


def test_parameter_scenario_targets_create_exactly_one_execution_per_parameter() -> None:
    selections = _parse_parameter_scenarios(
        (
            "GDP=305",
            "PMI=306",
            "PowerMix=287",
            "Temperature=289",
            "LiqUtilAdjustment=105",
        ),
        TARGET_PARAMETERS,
    )
    targets = _build_parameter_scenario_targets(
        selections,
        [
            (105, 2, 18, "Cameron LNG", "터미널 Utilization 변동"),
            (287, 5, 51, "발전 차질", "발전소 Utilization 변동"),
            (289, 6, 52, "겨울 한파", "겨울 한파"),
            (305, 21, 60, "국가별 경기", "국가별 경기"),
            (306, 21, 60, "국가별 경기", "국가별 경기"),
        ],
    )

    assert len(targets) == 5
    assert sum(len(target.scenario_ids) for target in targets) == 5
    assert {target.target_parameter: target.scenario_ids[0] for target in targets} == {
        "GDP": 305,
        "PMI": 306,
        "PowerMix": 287,
        "Temperature": 289,
        "LiqUtilAdjustment": 105,
    }


def test_parameter_scenario_targets_reject_missing_scenario() -> None:
    selections = _parse_parameter_scenarios(("GDP=999999",), ("GDP",))

    with pytest.raises(ValueError, match=r"missing or deleted scenarios: \[999999\]"):
        _build_parameter_scenario_targets(selections, [])


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


def test_reference_runtime_lines_include_config_and_lut_version_only() -> None:
    lines = _runtime_reference_lines(
        {
            "resolved_config": {"model_parameter_lut_enabled": True},
            "lut_version": "lut-v1",
        },
        heading="######",
    )
    rendered = "\n".join(lines)

    assert "Reference Runtime" in rendered
    assert "model_parameter_lut_enabled" in rendered
    assert "lut-v1" in rendered
    assert "reference_diagnostics" not in rendered


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
    ) == [{"candidate_key": "legacy"}]
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
            "llm_calls": [],
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
    assert "Reference Runtime" in report
    assert "lut-v1" in report
