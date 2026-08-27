# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.manual.model_parameter_agent.compare_v3_v4_proposals import (
    ComparisonScopeError,
    GroupSnapshot,
    ScenarioMatch,
    ScenarioSnapshot,
    _comparison_metrics,
    _record_passes,
    _scenario_snapshot,
    _version_metrics,
    match_scenarios,
    overall_verdict,
    render_dashboard,
    render_report,
    select_group_pair,
)


def _scenario(
    scenario_id: int,
    *,
    role: str | None,
    pressure_band: str | None,
    display_order: int,
    baseline_yn: str = "N",
) -> ScenarioSnapshot:
    return ScenarioSnapshot(
        scenario_id=scenario_id,
        title=f"scenario-{scenario_id}",
        display_order=display_order,
        scenario_role=role,
        pressure_band=pressure_band,
        baseline_yn=baseline_yn,
        status="created",
        dimension_values=({"dimensionId": "demand", "value": "high"},),
    )


def _group(
    group_id: int,
    version: str,
    event_ids: tuple[int, ...],
    scenarios: tuple[ScenarioSnapshot, ...],
) -> GroupSnapshot:
    return GroupSnapshot(
        scenario_group_id=group_id,
        api_version=version,  # type: ignore[arg-type]
        generation_strategy=(
            "multi_event_composite_dimensions" if version == "v3" else "multi_event_model_lever_dimensions"
        ),
        title=f"{version}-group-{group_id}",
        status="created",
        stage="validation_completed",
        request_usr_id=1,
        ordered_event_ids=event_ids,
        event_type_l2_ids=tuple(range(1, len(event_ids) + 1)),
        scenarios=scenarios,
        impact_catalog_version="v4" if version == "v4" else None,
        impact_catalog_checksum="a" * 64 if version == "v4" else None,
    )


def _parameter(name: str, value: float) -> dict[str, object]:
    return {
        "parameterName": name,
        "modelTarget": {
            "modelFile": "Demand",
            "modelSheet": f"{name}Adjustment",
            "slotAxesFieldNames": ["Year"],
        },
        "rationale": "scenario evidence",
        "values": [
            {
                "Year": 2027,
                "basecaseValue": 1.0,
                "proposedValue": value,
                "rationale": "scenario evidence",
            },
        ],
    }


def _record(
    scenario_id: int,
    group_id: int,
    proposal_id: int,
    parameters: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "scenario_id": scenario_id,
        "proposal_db_row": {
            "model_param_proposal_id": proposal_id,
            "scenario_id": scenario_id,
            "scenario_group_id": group_id,
            "status": "CONFIRMED",
            "proposal_parameters": parameters,
            "confirmation_parameters": parameters,
        },
        "confirmation": {
            "status": "PASS",
            "invalid_payload": {"status": "PASS"},
            "valid_confirmation": {"status": "PASS"},
            "reconfirmation": {"status": "PASS"},
        },
        "elapsed_seconds": 12.5,
        "attempts": [{"attempt": 1, "status": "PASS"}],
        "llm_calls": [
            {
                "step": "Step2",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 20,
                    "total_tokens": 120,
                },
            },
        ],
    }


def _groups() -> tuple[GroupSnapshot, GroupSnapshot]:
    v3 = _group(
        301,
        "v3",
        (101, 102),
        (
            _scenario(3001, role="floor", pressure_band="bearish", display_order=1),
            _scenario(3002, role="ceiling", pressure_band="bullish", display_order=2, baseline_yn="Y"),
        ),
    )
    v4 = _group(
        401,
        "v4",
        (101, 102),
        (
            _scenario(4001, role="ceiling", pressure_band="bullish", display_order=1, baseline_yn="Y"),
            _scenario(4002, role="floor", pressure_band="bearish", display_order=2),
        ),
    )
    return v3, v4


def test_scenario_snapshot_preserves_external_db_dimension_value_object() -> None:
    model = SimpleNamespace(
        scenario_id=9001,
        title="external DB object",
        display_order=1,
        scenario_role="mixed",
        global_pressure_band="balanced",
        baseline_yn="Y",
        status="created",
        dimension_values={
            "dim_supply": "restricted",
            "dim_duration": {"valueId": "long", "sourceEventIds": [101, 102]},
        },
    )

    snapshot = _scenario_snapshot(model)

    assert snapshot.dimension_values == {
        "dim_supply": "restricted",
        "dim_duration": {"valueId": "long", "sourceEventIds": [101, 102]},
    }


def test_select_group_pair_requires_same_ordered_event_ids_and_uses_latest_pair() -> None:
    v3, v4 = _groups()
    older_v4 = _group(399, "v4", (101, 102), v4.scenarios)
    selected = select_group_pair([v3, older_v4, v4])

    assert selected == (v3, v4)
    assert selected[0].ordered_event_ids == selected[1].ordered_event_ids

    unrelated = _group(500, "v4", (999, 1000), v4.scenarios)
    with pytest.raises(ComparisonScopeError, match="동일 원천 Event 집합"):
        select_group_pair([v3, unrelated], v3_group_id=301, v4_group_id=500)


def test_select_group_pair_accepts_known_182_183_ordered_event_scope() -> None:
    v3, v4 = _groups()
    group_182 = _group(182, "v3", (1463, 1464, 1523), v3.scenarios)
    group_183 = _group(183, "v4", (1463, 1464, 1523), v4.scenarios)

    assert select_group_pair([group_182, group_183]) == (group_182, group_183)


def test_select_group_pair_rejects_same_event_set_in_different_order() -> None:
    v3, v4 = _groups()
    reordered_v4 = _group(402, "v4", tuple(reversed(v3.ordered_event_ids)), v4.scenarios)

    with pytest.raises(ComparisonScopeError, match="표시 순서 일치"):
        select_group_pair([v3, reordered_v4], v3_group_id=301, v4_group_id=402)


@pytest.mark.parametrize(
    "event_ids",
    [
        (101, 101),
        (101,),
        (101, 102, 103, 104, 105, 106),
    ],
)
def test_select_group_pair_rejects_duplicate_or_out_of_range_event_ids(
    event_ids: tuple[int, ...],
) -> None:
    v3, v4 = _groups()
    invalid_v3 = _group(302, "v3", event_ids, v3.scenarios)
    invalid_v4 = _group(402, "v4", event_ids, v4.scenarios)

    with pytest.raises(ComparisonScopeError, match="중복 없이 2~5개"):
        select_group_pair([invalid_v3, invalid_v4], v3_group_id=302, v4_group_id=402)


def test_match_scenarios_prioritizes_role_over_display_order() -> None:
    v3, v4 = _groups()

    matches = match_scenarios(v3, v4)

    assert [(item.v3_scenario.scenario_id, item.v4_scenario.scenario_id) for item in matches] == [
        (3001, 4002),
        (3002, 4001),
    ]
    assert [item.basis for item in matches] == ["scenarioRole=floor", "scenarioRole=ceiling"]


def test_comparison_metrics_separate_parameter_and_exact_slot_differences() -> None:
    v3, v4 = _groups()
    records = {
        3001: _record(3001, 301, 1, [_parameter("GDP", 1.1), _parameter("PMI", 49.0)]),
        4002: _record(4002, 401, 2, [_parameter("GDP", 1.2), _parameter("Population", 10.0)]),
    }

    metrics = _comparison_metrics(match_scenarios(v3, v4)[0], records)

    assert metrics["common_parameters"] == {"GDP"}
    assert metrics["v3_only_parameters"] == {"PMI"}
    assert metrics["v4_only_parameters"] == {"Population"}
    assert metrics["common_slots"] == 1
    assert metrics["different_common_slot_values"] == 1


def test_comparison_metrics_preserve_parameters_for_one_sided_scenarios() -> None:
    v3_only = _scenario(3003, role="v3-only", pressure_band=None, display_order=3)
    v4_only = _scenario(4003, role="v4-only", pressure_band=None, display_order=3)
    records = {
        3003: _record(3003, 301, 21, [_parameter("PMI", 48.0)]),
        4003: _record(4003, 401, 22, [_parameter("LiqUtilAdjustment", 0.84)]),
    }

    v3_metrics = _comparison_metrics(ScenarioMatch(v3_only, None, "v3-only"), records)
    v4_metrics = _comparison_metrics(ScenarioMatch(None, v4_only, "v4-only"), records)

    assert v3_metrics["v3_parameters"] == {"PMI"}
    assert v3_metrics["v3_only_parameters"] == {"PMI"}
    assert v3_metrics["v4_parameters"] == set()
    assert v3_metrics["common_slots"] == 0
    assert v4_metrics["v4_parameters"] == {"LiqUtilAdjustment"}
    assert v4_metrics["v4_only_parameters"] == {"LiqUtilAdjustment"}
    assert v4_metrics["v3_parameters"] == set()
    assert v4_metrics["common_slots"] == 0


def test_overall_verdict_requires_unique_rows_and_matching_shared_db_foreign_keys() -> None:
    v3, v4 = _groups()
    records = {
        3001: _record(3001, 301, 11, [_parameter("GDP", 1.1)]),
        3002: _record(3002, 301, 12, [_parameter("GDP", 1.2)]),
        4001: _record(4001, 401, 13, [_parameter("Population", 10.0)]),
        4002: _record(4002, 401, 14, [_parameter("Population", 9.0)]),
    }

    assert (
        overall_verdict(
            execute=True,
            v3_group=v3,
            v4_group=v4,
            records=records,
            invalid_status={"status": "PASS"},
        )
        == "PASS"
    )
    assert _record_passes(records[3001], scenario_id=3001, scenario_group_id=301)

    records[4001]["proposal_db_row"]["scenario_group_id"] = 301  # type: ignore[index]
    assert (
        overall_verdict(
            execute=True,
            v3_group=v3,
            v4_group=v4,
            records=records,
            invalid_status={"status": "PASS"},
        )
        == "FAIL"
    )


@pytest.mark.parametrize("invalid_status", [None, {"status": "N/A"}, {"status": "FAIL"}])
def test_overall_verdict_requires_passing_invalid_status_check(
    invalid_status: dict[str, str] | None,
) -> None:
    v3, v4 = _groups()
    records = {
        3001: _record(3001, 301, 11, [_parameter("GDP", 1.1)]),
        3002: _record(3002, 301, 12, [_parameter("GDP", 1.2)]),
        4001: _record(4001, 401, 13, [_parameter("Population", 10.0)]),
        4002: _record(4002, 401, 14, [_parameter("Population", 9.0)]),
    }

    assert (
        overall_verdict(
            execute=True,
            v3_group=v3,
            v4_group=v4,
            records=records,
            invalid_status=invalid_status,
        )
        == "FAIL"
    )


def test_report_is_formal_markdown_and_dashboard_is_png(tmp_path: Path) -> None:
    v3, v4 = _groups()
    records = {
        3001: _record(3001, 301, 11, [_parameter("GDP", 1.1)]),
        3002: _record(3002, 301, 12, [_parameter("GDP", 1.2)]),
        4001: _record(4001, 401, 13, [_parameter("Population", 10.0)]),
        4002: _record(4002, 401, 14, [_parameter("Population", 9.0)]),
    }
    report, verdict = render_report(
        started_at=datetime(2026, 8, 13, tzinfo=UTC),
        finished_at=datetime(2026, 8, 13, 0, 2, tzinfo=UTC),
        execute=True,
        v3_group=v3,
        v4_group=v4,
        records=records,
        invalid_status={"status": "PASS"},
        dashboard_name="comparison_summary.png",
    )
    dashboard = tmp_path / "comparison_summary.png"
    render_dashboard(
        output_path=dashboard,
        v3_metrics=_version_metrics(v3, records),
        v4_metrics=_version_metrics(v4, records),
    )

    assert verdict == "PASS"
    assert report.startswith("# Model Parameter Agent v3/v4 비교 검증 보고서")
    assert "## 2. 비교 대상 및 동등성 통제" in report
    assert "## 4. v3/v4 결과 비교" in report
    assert "## 6. 공용 DB 저장 증적" in report
    assert "comparison_summary.png" in report
    assert ".html" not in report.lower()
    assert "<html" not in report.lower()
    assert dashboard.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
