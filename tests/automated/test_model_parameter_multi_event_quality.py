# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101, S105, SLF001

from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from tests.manual.model_parameter_agent import (
    evaluate_multi_event_quality as quality_runner,
)
from tests.manual.model_parameter_agent.evaluate_multi_event_quality import (
    ContractCaseEvidence,
    ContractEvidence,
    CoverageRow,
    ProjectionResult,
    ScenarioEvidence,
    SchemaPreflight,
    build_coverage_matrix,
    build_parameter_quality_rows,
    build_parser,
    build_performance_rows,
    build_prompt_grounding_rows,
    capture_execute_prompt_packets,
    execute_targets,
    project_expected_mappings,
    render_report,
    run_automated_contract_preflight,
    schema_preflight,
    select_quality_targets,
)
from tests.manual.model_parameter_agent.runner_common import serialize_proposal_row


def _parameter_definition(
    parameter_name: str,
    model_file: str = "Demand",
) -> dict[str, object]:
    return {
        "canonical_parameter_name": parameter_name,
        "parameter_name": parameter_name,
        "model_file": model_file,
        "model_sheet": f"{parameter_name}Adjustment",
    }


def _relations() -> list[dict[str, int]]:
    return [
        {
            "mi_event_id": 101,
            "event_type_l2_id": 10,
            "scenario_dimension_template_id": 1001,
            "display_order": 1,
        },
        {
            "mi_event_id": 102,
            "event_type_l2_id": 20,
            "scenario_dimension_template_id": 2001,
            "display_order": 2,
        },
    ]


def _definitions() -> list[dict[str, object]]:
    return [
        {
            "dimensionId": "composite_pressure",
            "sourceEventIds": [101, 102],
            "sourceRefs": [
                {"scenarioDimensionTemplateId": 1001, "dimKey": "demand"},
                {"scenarioDimensionTemplateId": 2001, "dimKey": "supply"},
            ],
        },
    ]


def _mapping_rules() -> list[dict[str, object]]:
    return [
        {
            "event_type_l2_id": 10,
            "dimension_key": "demand",
            "canonical_parameter_name": "GDP",
            "mapping_method": "direct",
        },
        {
            "event_type_l2_id": 10,
            "dimension_key": "demand",
            "canonical_parameter_name": "PMI",
            "mapping_method": "routing",
        },
        {
            "event_type_l2_id": 20,
            "dimension_key": "supply",
            "canonical_parameter_name": "GDP",
            "mapping_method": "direct",
        },
    ]


_PRESSURE_PROJECTION = {
    "sourceEventId": 101,
    "value": "high",
    "rationale": "수요·공급 복합 압력",
}
_DURATION_PROJECTION = {
    "sourceEventId": 102,
    "value": "long",
    "rationale": "공급 충격 지속 기간",
}


def _projection() -> ProjectionResult:
    return project_expected_mappings(
        dimension_definitions=_definitions(),
        scenario_dimension_values={"composite_pressure": "high"},
        relations=_relations(),
        mapping_rules=_mapping_rules(),
        parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
    )


def _evidence(
    *,
    scenario_id: int = 501,
    occurrences: tuple[dict[str, object], ...] | None = None,
) -> ScenarioEvidence:
    projection = _projection()
    return ScenarioEvidence(
        scenario_group_id=50,
        scenario_id=scenario_id,
        group_title="multi-event group",
        scenario_title="composite scenario",
        parameter_mapping_ready=False,
        relation_count=2,
        group_event_ids=(101, 102),
        ordered_events=(
            {
                "display_order": 1,
                "mi_event_id": 101,
                "event_type_l2_id": 10,
                "scenario_dimension_template_id": 1001,
                "title": "수요 충격",
                "one_line_summary": "수요가 빠르게 증가한다.",
                "key_bullets": ["강한 상방 압력"],
                "tags": ["demand"],
                "detail_excerpt": "단기간 수요 급증이 복합 압력에 기여한다.",
            },
            {
                "display_order": 2,
                "mi_event_id": 102,
                "event_type_l2_id": 20,
                "scenario_dimension_template_id": 2001,
                "title": "공급 충격",
                "one_line_summary": "공급이 감소한다.",
                "key_bullets": ["강한 하방 압력"],
                "tags": ["supply"],
                "detail_excerpt": "중기 공급 감소가 복합 압력과 충돌한다.",
            },
        ),
        occurrences=occurrences if occurrences is not None else projection.occurrences,
        dimension_values={
            "composite_pressure": "high",
            "composite_duration": "long",
            "composite_unrelated": "ignored",
        },
        projection_statuses=(
            "composite_pressure=approved",
            "composite_duration=approved",
            "composite_unrelated=missing",
        ),
        dimension_source_event_ids={
            "composite_pressure": (101, 102),
            "composite_duration": (102,),
            "composite_unrelated": (101,),
        },
        dimension_source_refs={
            "composite_pressure": (
                {
                    "scenario_dimension_template_id": 1001,
                    "dim_key": "demand",
                },
                {
                    "scenario_dimension_template_id": 2001,
                    "dim_key": "supply",
                },
            ),
            "composite_duration": (
                {
                    "scenario_dimension_template_id": 2001,
                    "dim_key": "duration",
                },
            ),
            "composite_unrelated": (
                {
                    "scenario_dimension_template_id": 1001,
                    "dim_key": "unrelated",
                },
            ),
        },
        approved_source_projections={
            "composite_pressure": (_PRESSURE_PROJECTION,),
            "composite_duration": (_DURATION_PROJECTION,),
        },
    )


def _runtime_candidate(occurrence: dict[str, object]) -> dict[str, object]:
    return {
        **occurrence,
        "canonical_parameter_name": occurrence["parameter_name"],
        "source_dimension_id": occurrence["scenario_dimension_key"],
        "mapping_strategy": "v3",
        "source_refs": [
            {
                "scenario_dimension_template_id": occurrence["scenario_dimension_template_id"],
                "dim_key": occurrence["mapping_dimension_key"],
            },
        ],
        "approved_source_projections": [_PRESSURE_PROJECTION],
    }


def _runtime_task_key(
    parameter_name: str,
    *,
    model_file: str = "Demand",
    model_sheet: str | None = None,
) -> str:
    from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
        _parameter_candidate_key,
    )

    return _parameter_candidate_key(
        {
            "mapping_strategy": "v3",
            "canonical_parameter_name": parameter_name,
            "model_file": model_file,
            "model_sheet": model_sheet or f"{parameter_name}Adjustment",
        },
    )


def _proposal_parameter(
    parameter_name: str,
    *,
    include_lut: bool = False,
) -> dict[str, object]:
    value = {
        "Year": 2026,
        "basecaseValue": 1.0,
        "proposedValue": 1.1,
        "rationale": "복합 압력의 방향과 강도를 단일 값으로 반영했다.",
    }
    if include_lut:
        value["lutValue"] = 0.9
    return {
        "parameterName": parameter_name,
        "modelTarget": {
            "modelFile": "Demand",
            "modelSheet": f"{parameter_name}Adjustment",
            "slotAxesFieldNames": ["Year"],
        },
        "rationale": "두 이벤트와 composite pressure를 함께 고려했다.",
        "values": [value],
    }


def _execution_context(target: ScenarioEvidence) -> dict[str, object]:
    lineage = [
        {
            "scenario_dimension_key": dimension_key,
            "scenario_dimension_label": dimension_key,
            "scenario_dimension_value": target.dimension_values[dimension_key],
            "source_event_ids": list(
                target.dimension_source_event_ids.get(dimension_key) or (),
            ),
            "source_refs": [dict(item) for item in target.dimension_source_refs.get(dimension_key) or ()],
            "approved_source_projections": [
                dict(item) for item in target.approved_source_projections.get(dimension_key) or ()
            ],
        }
        for dimension_key in target.dimension_values
    ]
    return {
        "scenario": {
            "scenario_id": target.scenario_id,
            "title": target.scenario_title,
            "dimension_values": dict(target.dimension_values),
        },
        "scenario_group": {
            "title": target.group_title,
            "api_version": "v3",
            "generation_strategy": "multi_event_composite_dimensions",
            "parameter_mapping_ready": target.parameter_mapping_ready,
            "dimension_selected": list(target.dimension_values),
        },
        "dimension_template": [{"dimension_id": key, "label": key} for key in target.dimension_values],
        "dimension_lineage": lineage,
        "events": [
            {
                "mi_event_id": event["mi_event_id"],
                "event_type_l2_id": event["event_type_l2_id"],
                "event_title_ko": event["title"],
                "one_line_summary": event["one_line_summary"],
                "key_bullets": list(event["key_bullets"]),
                "tags": list(event["tags"]),
                "detail_analysis": event["detail_excerpt"],
            }
            for event in target.ordered_events
        ],
    }


def _indirect_dimension() -> dict[str, object]:
    return {
        "source_dimension_id": "composite_duration",
        "scenario_dimension_key": "composite_duration",
        "mapping_dimension_key": "duration",
        "source_dimension_label": "지속 기간",
        "source_dimension_value": "long",
        "source_event_ids": [102],
        "source_refs": [
            {
                "scenario_dimension_template_id": 2001,
                "dim_key": "duration",
            },
        ],
        "approved_source_projections": [_DURATION_PROJECTION],
        "mapping_method": "indirect",
        "reason": "모든 parameter의 기간 근거",
    }


def _successful_execution(
    target: ScenarioEvidence,
    *,
    selected_candidates: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    candidates = [_runtime_candidate(item) for item in target.occurrences]
    selected_sources = candidates if selected_candidates is None else selected_candidates
    selected_by_parameter: dict[str, list[dict[str, object]]] = {}
    for candidate in selected_sources:
        selected_by_parameter.setdefault(
            str(candidate["canonical_parameter_name"]),
            [],
        ).append(candidate)
    selected: list[dict[str, object]] = []
    for parameter_name, sources in selected_by_parameter.items():
        merged = dict(sources[0])
        merged["candidate_key"] = _runtime_task_key(parameter_name)
        merged["source_dimensions"] = [dict(source) for source in sources]
        methods = {str(source["mapping_method"]) for source in sources}
        merged["mapping_method"] = next(iter(methods)) if len(methods) == 1 else "merged"
        selected.append(merged)
    parameter_names = sorted(
        {str(candidate["canonical_parameter_name"]) for candidate in selected},
    )
    candidate_keys = {parameter_name: _runtime_task_key(parameter_name) for parameter_name in parameter_names}
    api_proposed = [_proposal_parameter(parameter_name, include_lut=True) for parameter_name in parameter_names]
    stored_proposed = [_proposal_parameter(parameter_name) for parameter_name in parameter_names]
    slots = [
        {
            "candidate_key": candidate_key,
            "slot_key": f"{parameter_name}-2026",
            "slot_axes": [{"axis_name": "Year", "axis_value": 2026}],
        }
        for parameter_name, candidate_key in candidate_keys.items()
    ]
    slot_catalog = [
        {
            "candidate_key": candidate_key,
            "parameter_name": parameter_name,
            "key_axes": ["Year"],
            "fixed_axis_names": [],
            "time_axis_names": ["Year"],
            "period_groups": [
                {
                    "period_group_id": "period-group-1",
                    "available_periods": [{"Year": 2026}],
                },
            ],
            "fixed_axis_hierarchy": [
                {"period_group_id": "period-group-1"},
            ],
        }
        for parameter_name, candidate_key in candidate_keys.items()
    ]
    references = [
        {
            "candidate_key": candidate_key,
            "slot_key": f"{parameter_name}-2026",
            "axes": {"Year": 2026},
            "actual_basecase_value": 1.0,
            "lut_default_value": 0.9,
            "llm_reference_value": 1.0,
            "effective_source": "basecase",
            "basecase_reference_id": f"basecase:{parameter_name}:2026",
            "lut_reference_id": f"lut:{parameter_name}:2026",
        }
        for parameter_name, candidate_key in candidate_keys.items()
    ]
    adjustments = [
        {
            "candidate_key": candidate_key,
            "parameter_name": parameter_name,
            "parameter_selection_rationale_ko": ("연결된 이벤트와 composite dimension 근거를 함께 반영했다."),
            "value_grid": [
                {
                    "coordinates": {"Year": 2026},
                    "basecase_value": 1.0,
                    "lut_value": 0.9,
                    "proposed_value": 1.1,
                    "rationale_ko": "복합 압력의 방향과 강도를 반영했다.",
                },
            ],
        }
        for parameter_name, candidate_key in candidate_keys.items()
    ]
    indirect_items = [_indirect_dimension()]
    execution: dict[str, object] = {
        "attempts": 1,
        "elapsed_seconds": 10.0,
        "context": _execution_context(target),
        "rule_candidates": candidates,
        "expected_candidates": selected,
        "non_input_items": indirect_items,
        "parameter_slots": slots,
        "slot_catalog": slot_catalog,
        "effective_references": references,
        "result": {
            "parameter_adjustments": adjustments,
            "non_input_items": indirect_items,
        },
        "step_summary": {
            "selected_slot_count": len(slots),
            "value_reference_record_count": len(references),
            "value_cell_count": len(adjustments),
            "proposal_parameter_count": len(api_proposed),
        },
        "final_response": {
            "data": {
                "scenarioGroupId": target.scenario_group_id,
                "eventId": None,
                "proposalParameters": deepcopy(api_proposed),
            },
        },
        "proposal_db_row": {
            "scenario_group_id": target.scenario_group_id,
            "mi_event_id": None,
            "proposal_parameters": deepcopy(stored_proposed),
            "confirmation_parameters": deepcopy(stored_proposed),
        },
        "confirmation": {
            "status": "PASS",
            "invalid_payload": {"status": "PASS"},
            "valid_confirmation": {"status": "PASS"},
            "reconfirmation": {"status": "PASS"},
        },
    }
    execution["prompt_packets"] = capture_execute_prompt_packets(execution)
    return execution


def _llm_call(step: str) -> dict[str, object]:
    return {
        "step": step,
        "success": True,
        "prompt_bytes": 100,
        "prompt_limit_bytes": 1000,
        "elapsed_seconds": 1.5,
        "internal_retry_count": 0,
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


def test_actual_prompt_grounding_passes_with_completed_graph_packet_evidence() -> None:
    target = _evidence()
    execution = _successful_execution(target)

    rows = build_prompt_grounding_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert [row.step for row in rows] == ["Step1.5", "Step2", "Step3"]
    assert {row.verdict for row in rows} == {"PASS"}
    assert all(row.event_ids == (101, 102) for row in rows)
    assert all(row.dimension_keys == ("composite_duration", "composite_pressure") for row in rows)
    assert all("composite_unrelated" not in row.dimension_keys for row in rows)


def test_actual_prompt_grounding_fails_missing_step_context() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    prompt_packets = execution["prompt_packets"]
    assert isinstance(prompt_packets, dict)
    step2 = prompt_packets["Step2"]
    assert isinstance(step2, dict)
    del step2["scenario_brief"]

    rows = build_prompt_grounding_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    step2_row = next(row for row in rows if row.step == "Step2")

    assert step2_row.verdict == "FAIL"
    assert "scenario_brief 누락" in step2_row.evidence


def test_actual_prompt_grounding_fails_lineage_projection_mismatch() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    prompt_packets = execution["prompt_packets"]
    assert isinstance(prompt_packets, dict)
    step3 = prompt_packets["Step3"]
    assert isinstance(step3, dict)
    brief = step3["scenario_brief"]
    assert isinstance(brief, dict)
    brief["events"] = list(reversed(brief["events"]))
    pressure = next(item for item in brief["selected_dimensions"] if item["dimension_key"] == "composite_pressure")
    pressure["source_event_ids"] = [999]
    pressure["approved_source_projections"] = [{"value": "wrong"}]

    rows = build_prompt_grounding_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    step3_row = next(row for row in rows if row.step == "Step3")

    assert step3_row.verdict == "FAIL"
    assert "display order event ID 불일치" in step3_row.evidence
    assert "source event lineage 불일치" in step3_row.evidence
    assert "승인 projection 불일치/누락" in step3_row.evidence


def test_discovery_event_excerpt_matches_production_raw_slice() -> None:
    detail = "D" * 1400

    events, errors = quality_runner._bounded_event_evidence(
        relation_rows=[
            {
                "display_order": 1,
                "mi_event_id": 101,
                "event_type_l2_id": 10,
                "scenario_dimension_template_id": 1001,
            },
        ],
        event_records={
            101: {
                "event_type_l2_id": 10,
                "event_title_ko": "긴 본문 이벤트",
                "detail_analysis": detail,
            },
        },
    )

    assert errors == []
    assert events[0]["detail_excerpt"] == detail[:1200]
    assert not events[0]["detail_excerpt"].endswith("…")


def test_projection_preserves_convergence_expansion_and_event_lineage() -> None:
    result = _projection()

    assert result.errors == ()
    assert len(result.occurrences) == 3
    assert [item["parameter_name"] for item in result.occurrences].count("GDP") == 2
    assert {item["parameter_name"] for item in result.occurrences} == {"GDP", "PMI"}
    assert {event_id for item in result.occurrences for event_id in item["source_event_ids"]} == {101, 102}
    assert {item["candidate_key"] for item in result.occurrences} == {
        "parameter|v3|demand|gdpadjustment|gdp",
        "parameter|v3|demand|pmiadjustment|pmi",
    }


def test_stable_task_key_matches_production_normalization() -> None:
    expected = "parameter|v3|demandmodelxlsx|gdpadjustment|gdp"

    assert (
        quality_runner._stable_task_key(
            "GDP %",
            "Demand.Model.xlsx",
            "GDP Adjustment (%)",
        )
        == expected
    )
    assert (
        _runtime_task_key(
            "GDP %",
            model_file="Demand.Model.xlsx",
            model_sheet="GDP Adjustment (%)",
        )
        == expected
    )


def test_projection_fails_orphan_event_before_execution() -> None:
    definitions = _definitions()
    definitions[0]["sourceEventIds"] = [101, 999]

    result = project_expected_mappings(
        dimension_definitions=definitions,
        scenario_dimension_values={"composite_pressure": "high"},
        relations=_relations(),
        mapping_rules=_mapping_rules(),
        parameter_definitions=[_parameter_definition("GDP")],
    )

    assert any("group relation에 없습니다" in error for error in result.errors)
    assert result.occurrences == ()


def test_projection_warns_and_excludes_unmapped_valid_source() -> None:
    result = project_expected_mappings(
        dimension_definitions=_definitions(),
        scenario_dimension_values={"composite_pressure": "high"},
        relations=_relations(),
        mapping_rules=[_mapping_rules()[0]],
        parameter_definitions=[_parameter_definition("GDP")],
    )

    assert result.errors == ()
    assert len(result.occurrences) == 1
    assert any("활성 DB mapping이 없어 제외" in warning for warning in result.warnings)


@pytest.mark.parametrize("mode", ["missing", "duplicate"])
def test_projection_fails_missing_or_duplicate_display_order(mode: str) -> None:
    relations: list[dict[str, object]] = [dict(item) for item in _relations()]
    if mode == "missing":
        relations[0].pop("display_order")
    else:
        relations[1]["display_order"] = 1

    result = project_expected_mappings(
        dimension_definitions=_definitions(),
        scenario_dimension_values={"composite_pressure": "high"},
        relations=relations,
        mapping_rules=_mapping_rules(),
        parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
    )

    assert any("display_order" in error for error in result.errors)


def test_scenario_evidence_loads_bounded_ordered_event_core_info() -> None:
    group = SimpleNamespace(
        scenario_group_id=50,
        title="group",
        parameter_mapping_ready=False,
        dimension_definitions=_definitions(),
    )
    scenario = SimpleNamespace(
        scenario_id=501,
        title="scenario",
        dimension_values={"composite_pressure": "high"},
    )
    event_records = {
        event_id: {
            "mi_event_id": event_id,
            "event_type_l2_id": event_type_id,
            "event_title_ko": "T" * 600,
            "one_line_summary": "S" * 400,
            "key_bullets": [f"bullet-{index}" for index in range(8)],
            "tags": [f"tag-{index}" for index in range(12)],
            "detail_analysis": "D" * 1400,
        }
        for event_id, event_type_id in ((101, 10), (102, 20))
    }

    evidence = quality_runner._build_scenario_evidence(
        group=group,
        scenario=scenario,
        relations=_relations(),
        dimension_mappings=[],
        mapping_rules=_mapping_rules(),
        parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        event_records=event_records,
    )

    assert [event["display_order"] for event in evidence.ordered_events] == [1, 2]
    assert all(len(event["title"]) <= 500 for event in evidence.ordered_events)
    assert all(len(event["one_line_summary"]) <= 300 for event in evidence.ordered_events)
    assert all(len(event["key_bullets"]) == 5 for event in evidence.ordered_events)
    assert all(len(event["tags"]) == 8 for event in evidence.ordered_events)
    assert all(len(event["detail_excerpt"]) <= 1200 for event in evidence.ordered_events)


def test_dynamic_selection_does_not_gate_mapping_ready_false() -> None:
    gdp_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "GDP")
    gdp_only = _evidence(scenario_id=501, occurrences=gdp_occurrences)
    all_parameters = _evidence(scenario_id=502)

    selected, skipped = select_quality_targets(
        [gdp_only, all_parameters],
        max_scenarios=1,
        explicit_scope=False,
    )

    assert selected == [all_parameters]
    assert selected[0].parameter_mapping_ready is False
    assert skipped == [gdp_only]
    assert skipped[0].selection_skip_reason == ("max_scenarios=1 cap으로 미선택; unique eligible occurrence=0")


def test_selection_cap_reports_all_discovered_unique_eligible_coverage() -> None:
    projection = _projection()
    gdp_only = _evidence(
        scenario_id=501,
        occurrences=tuple(item for item in projection.occurrences if item["parameter_name"] == "GDP"),
    )
    pmi_only = _evidence(
        scenario_id=502,
        occurrences=tuple(item for item in projection.occurrences if item["parameter_name"] == "PMI"),
    )
    duplicate_pmi = deepcopy(pmi_only)
    duplicate_pmi.scenario_id = 503
    discovered = [gdp_only, pmi_only, duplicate_pmi]

    selected, skipped = select_quality_targets(
        discovered,
        max_scenarios=1,
        explicit_scope=False,
    )
    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=selected,
        discovered_targets=discovered,
        executions={},
        execute=False,
    )
    by_name = {row.parameter_name: row for row in rows}

    assert selected == [gdp_only]
    assert skipped == [pmi_only, duplicate_pmi]
    assert all(
        target.selection_skip_reason == "max_scenarios=1 cap으로 미선택; unique eligible occurrence=1"
        for target in skipped
    )
    assert issues == []
    assert by_name["GDP"].eligible == 2
    assert by_name["PMI"].eligible == 1
    assert by_name["PMI"].candidate is None
    assert by_name["PMI"].verdict == "COVERAGE LIMIT"
    assert "discovered eligible=1, selected eligible=0, skipped unique=1" in by_name["PMI"].evidence
    assert "max_scenarios=1 cap으로 미선택" in by_name["PMI"].evidence


def test_dynamic_selection_keeps_invalid_lineage_as_fail_evidence() -> None:
    invalid = ScenarioEvidence(
        scenario_group_id=51,
        scenario_id=503,
        group_title="invalid group",
        scenario_title="invalid scenario",
        parameter_mapping_ready=False,
        relation_count=2,
        group_event_ids=(101, 102),
        errors=("orphan sourceRef",),
    )

    selected, skipped = select_quality_targets(
        [_evidence(), invalid],
        max_scenarios=1,
        explicit_scope=False,
    )

    assert invalid in selected
    assert invalid not in skipped
    report = render_report(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execute=False,
        preflight=SchemaPreflight("PASS", ("schema ok",)),
        selected_targets=selected,
        skipped_targets=skipped,
        discovery_messages=[],
        active_parameter_definitions=[_parameter_definition("GDP")],
        coverage_rows=[],
        executions={},
        integrity_issues=[],
    )
    assert "- 판정: **FAIL**" in report


def test_explicit_selection_is_not_capped_by_discovery_limit() -> None:
    first = _evidence(scenario_id=501)
    second = _evidence(scenario_id=502)

    selected, skipped = select_quality_targets(
        [first, second],
        max_scenarios=1,
        explicit_scope=True,
    )

    assert selected == [first, second]
    assert skipped == []


def test_schema_preflight_requires_dimension_value_display_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    models = (
        quality_runner.MiScenarioGroupModel,
        quality_runner.MiScenarioGroupEventModel,
        quality_runner.MiDimensionValueMappingModel,
        quality_runner.MiScenarioModel,
        quality_runner.MiModelParamProposalModel,
        quality_runner.MiModelParamModel,
        quality_runner.MiModelParamDimensionMapModel,
    )
    columns_by_table = {
        model.__tablename__: [
            {"name": column.name, "nullable": column.nullable}
            for column in model.__table__.columns
            if not (model is quality_runner.MiDimensionValueMappingModel and column.name == "display_value")
        ]
        for model in models
    }
    inspector = SimpleNamespace(
        get_table_names=lambda: list(columns_by_table),
        get_columns=lambda table_name: columns_by_table[table_name],
    )
    monkeypatch.setattr(quality_runner, "inspect", lambda _bind: inspector)

    preflight = schema_preflight(
        SimpleNamespace(get_bind=lambda: object()),
    )

    assert preflight.verdict == "FAIL"
    assert any(
        quality_runner.MiDimensionValueMappingModel.__tablename__ in message and "display_value" in message
        for message in preflight.messages
    )


def test_execute_targets_globally_blocks_writes_on_any_lineage_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = _evidence(scenario_id=502)
    invalid.errors = ("orphan sourceRef",)
    called: list[int] = []

    async def fake_execute(scenario_id: int) -> dict[str, object]:
        called.append(scenario_id)
        return {}

    monkeypatch.setattr(
        quality_runner,
        "execute_proposal_and_confirmation",
        fake_execute,
    )

    executions = asyncio.run(
        execute_targets([_evidence(scenario_id=501), invalid], retries=0),
    )

    assert called == []
    assert set(executions) == {501, 502}
    assert all(record["attempts"] == 0 for record in executions.values())
    assert all("all graph/write calls blocked" in record["error"] for record in executions.values())


def test_read_only_matrix_marks_only_eligible_rows_as_unexecuted_coverage_limit() -> None:
    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
            _parameter_definition("Temperature"),
        ],
        targets=[_evidence()],
        executions={},
        execute=False,
    )
    by_name = {row.parameter_name: row for row in rows}

    assert issues == []
    assert by_name["GDP"].eligible == 2
    assert by_name["GDP"].candidate is None
    assert by_name["GDP"].verdict == "COVERAGE LIMIT"
    assert by_name["Temperature"].eligible == 0
    assert "적합한 sourceRef가 없음" in by_name["Temperature"].evidence


def test_executed_matrix_reaches_pass_with_nullable_v3_persistence() -> None:
    target = _evidence()
    execution = _successful_execution(target)

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={501: execution},
        execute=True,
    )

    assert issues == []
    by_name = {row.parameter_name: row for row in rows}
    assert by_name["GDP"].verdict == "REVIEW"
    assert by_name["PMI"].verdict == "REVIEW"
    assert {row.proposed for row in rows} == {1}
    assert {row.confirmed for row in rows} == {1}


def test_executed_matrix_fails_when_candidate_loses_source_lineage() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    candidates = execution["rule_candidates"]
    assert isinstance(candidates, list)
    candidates[0] = {**candidates[0], "source_event_ids": []}

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={501: execution},
        execute=True,
    )

    assert any(row.verdict == "FAIL" for row in rows)
    assert any("candidate mismatch" in issue for issue in issues)


def test_executed_matrix_requires_explicit_null_api_event_id() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    response_data = execution["final_response"]
    assert isinstance(response_data, dict)
    data = response_data["data"]
    assert isinstance(data, dict)
    del data["eventId"]

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={501: execution},
        execute=True,
    )

    assert {row.verdict for row in rows} == {"FAIL"}
    assert any("API eventId" in issue for issue in issues)


def test_projection_fails_relation_event_unused_by_every_definition() -> None:
    relations = [
        *_relations(),
        {
            "mi_event_id": 103,
            "event_type_l2_id": 30,
            "scenario_dimension_template_id": 3001,
            "display_order": 3,
        },
    ]

    result = project_expected_mappings(
        dimension_definitions=_definitions(),
        scenario_dimension_values={"composite_pressure": "high"},
        relations=relations,
        mapping_rules=_mapping_rules(),
        parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
    )

    assert any("어떤 dimensionDefinition/sourceRef에도 연결되지" in error for error in result.errors)


def test_quality_rows_validate_exact_slots_basecase_and_convergence_review() -> None:
    target = _evidence()
    execution = _successful_execution(target)

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    by_name = {row.parameter_name: row for row in rows}

    assert by_name["PMI"].verdict == "REVIEW"
    assert by_name["PMI"].selected_slot_count == 1
    assert by_name["PMI"].exact_slot_count == 1
    assert by_name["PMI"].reference_sources == ("basecase",)
    assert by_name["GDP"].verdict == "REVIEW"
    assert by_name["GDP"].source_count == 2
    assert "방향·강도·기간·대상" in by_name["GDP"].manual_review


def test_quality_rows_fail_explicit_rationale_direction_conflict() -> None:
    pmi_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "PMI")
    target = _evidence(occurrences=pmi_occurrences)
    execution = _successful_execution(target)
    conflict = "source event와 모순되는 방향 역전"
    adjustment = execution["result"]["parameter_adjustments"][0]
    adjustment["parameter_selection_rationale_ko"] = conflict
    adjustment["value_grid"][0]["rationale_ko"] = conflict
    api_parameter = execution["final_response"]["data"]["proposalParameters"][0]
    proposal_parameter = execution["proposal_db_row"]["proposal_parameters"][0]
    confirmed_parameter = execution["proposal_db_row"]["confirmation_parameters"][0]
    for parameter in (api_parameter, proposal_parameter, confirmed_parameter):
        parameter["rationale"] = conflict
        parameter["values"][0]["rationale"] = conflict

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert rows[0].verdict == "FAIL"
    assert "방향 역전" in rows[0].evidence


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("Year", 2099),
        ("proposedValue", 999.0),
        ("basecaseValue", 999.0),
        ("lutValue", 999.0),
    ],
)
def test_quality_rows_fail_step3_to_final_value_signature_divergence(
    field_name: str,
    replacement: float,
) -> None:
    pmi_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "PMI")
    target = _evidence(occurrences=pmi_occurrences)
    execution = _successful_execution(target)
    response = execution["final_response"]
    proposal_row = execution["proposal_db_row"]
    assert isinstance(response, dict)
    assert isinstance(proposal_row, dict)
    api_parameter = response["data"]["proposalParameters"][0]
    stored_parameters = [
        proposal_row["proposal_parameters"][0],
        proposal_row["confirmation_parameters"][0],
    ]
    api_parameter["values"][0][field_name] = replacement
    if field_name != "lutValue":
        for parameter in stored_parameters:
            parameter["values"][0][field_name] = replacement

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert rows[0].verdict == "FAIL"
    assert "signature" in rows[0].evidence


def test_quality_rows_allow_single_lut_fallback_when_basecase_is_absent() -> None:
    pmi_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "PMI")
    target = _evidence(occurrences=pmi_occurrences)
    execution = _successful_execution(target)
    references = execution["effective_references"]
    assert isinstance(references, list)
    reference = references[0]
    assert isinstance(reference, dict)
    reference.update(
        {
            "actual_basecase_value": None,
            "llm_reference_value": 0.9,
            "effective_source": "lut",
            "basecase_reference_id": None,
        },
    )
    adjustments = execution["result"]
    assert isinstance(adjustments, dict)
    adjustments["parameter_adjustments"][0]["value_grid"][0]["basecase_value"] = None
    response = execution["final_response"]
    assert isinstance(response, dict)
    response["data"]["proposalParameters"][0]["values"][0]["basecaseValue"] = None
    proposal_row = execution["proposal_db_row"]
    assert isinstance(proposal_row, dict)
    proposal_row["proposal_parameters"][0]["values"][0]["basecaseValue"] = None
    proposal_row["confirmation_parameters"][0]["values"][0]["basecaseValue"] = None

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert len(rows) == 1
    assert rows[0].verdict == "REVIEW"
    assert rows[0].reference_sources == ("lut",)


def test_quality_rows_allow_output_enrichment_with_dependent_slot_axes() -> None:
    pmi_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "PMI")
    target = _evidence(occurrences=pmi_occurrences)
    execution = _successful_execution(target)
    execution["effective_references"][0]["metadata"] = {
        "Country": "Angola",
    }
    adjustment = execution["result"]["parameter_adjustments"][0]
    adjustment["value_grid"][0]["coordinates"]["Country"] = "Angola"
    response_parameter = execution["final_response"]["data"]["proposalParameters"][0]
    stored_parameter = execution["proposal_db_row"]["proposal_parameters"][0]
    confirmed_parameter = execution["proposal_db_row"]["confirmation_parameters"][0]
    for parameter in (
        response_parameter,
        stored_parameter,
        confirmed_parameter,
    ):
        parameter["modelTarget"]["slotAxesFieldNames"] = ["Country", "Year"]
        parameter["values"][0]["Country"] = "Angola"

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert rows[0].verdict == "REVIEW"
    assert "coordinates" not in rows[0].evidence
    assert "signature" not in rows[0].evidence


def test_quality_rows_fail_reference_metadata_mismatch() -> None:
    pmi_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "PMI")
    target = _evidence(occurrences=pmi_occurrences)
    execution = _successful_execution(target)
    execution["effective_references"][0]["metadata"] = {
        "Country": "Nigeria",
    }
    adjustment = execution["result"]["parameter_adjustments"][0]
    adjustment["value_grid"][0]["coordinates"]["Country"] = "Angola"
    response_parameter = execution["final_response"]["data"]["proposalParameters"][0]
    stored_parameter = execution["proposal_db_row"]["proposal_parameters"][0]
    confirmed_parameter = execution["proposal_db_row"]["confirmation_parameters"][0]
    for parameter in (
        response_parameter,
        stored_parameter,
        confirmed_parameter,
    ):
        parameter["modelTarget"]["slotAxesFieldNames"] = ["Country", "Year"]
        parameter["values"][0]["Country"] = "Angola"

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert rows[0].verdict == "FAIL"
    assert "reference axes+metadata" in rows[0].evidence


def test_quality_rows_fail_missing_reference_and_value_rationale() -> None:
    pmi_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "PMI")
    target = _evidence(occurrences=pmi_occurrences)
    execution = _successful_execution(target)
    execution["effective_references"] = []
    response = execution["final_response"]
    assert isinstance(response, dict)
    data = response["data"]
    assert isinstance(data, dict)
    parameters = data["proposalParameters"]
    assert isinstance(parameters, list)
    values = parameters[0]["values"]
    assert isinstance(values, list)
    values[0]["rationale"] = ""

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert rows[0].verdict == "FAIL"
    assert "value 수 불일치" in rows[0].evidence
    assert "value rationale 비어 있음" in rows[0].evidence


def test_quality_rows_fail_duplicate_slot_axis_as_non_exact() -> None:
    pmi_occurrences = tuple(item for item in _projection().occurrences if item["parameter_name"] == "PMI")
    target = _evidence(occurrences=pmi_occurrences)
    execution = _successful_execution(target)
    slots = execution["parameter_slots"]
    assert isinstance(slots, list)
    slot_axes = slots[0]["slot_axes"]
    assert isinstance(slot_axes, list)
    slot_axes.append({"axis_name": "Year", "axis_value": 2026})

    rows = build_parameter_quality_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert rows[0].verdict == "FAIL"
    assert "exact slot 불일치" in rows[0].evidence


def test_executed_matrix_fails_api_db_value_divergence() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    proposal_row = execution["proposal_db_row"]
    assert isinstance(proposal_row, dict)
    db_parameters = proposal_row["proposal_parameters"]
    assert isinstance(db_parameters, list)
    db_values = db_parameters[0]["values"]
    assert isinstance(db_values, list)
    db_values[0]["proposedValue"] = 2.1

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert any(row.verdict == "FAIL" for row in rows)
    assert any("API proposal values와 DB proposal read-back" in issue for issue in issues)


def test_executed_matrix_fails_confirmation_db_value_divergence() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    proposal_row = execution["proposal_db_row"]
    assert isinstance(proposal_row, dict)
    confirmation_parameters = proposal_row["confirmation_parameters"]
    assert isinstance(confirmation_parameters, list)
    confirmation_values = confirmation_parameters[0]["values"]
    assert isinstance(confirmation_values, list)
    confirmation_values[0]["proposedValue"] = 2.1

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert any(row.verdict == "FAIL" for row in rows)
    assert any("confirmation read-back" in issue for issue in issues)


def test_executed_matrix_fails_mapping_outside_active_candidate() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    candidates = execution["rule_candidates"]
    assert isinstance(candidates, list)
    candidates.append(
        {
            **_runtime_candidate(target.occurrences[0]),
            "candidate_key": _runtime_task_key("Temperature"),
            "canonical_parameter_name": "Temperature",
            "parameter_name": "Temperature",
            "model_sheet": "TemperatureAdjustment",
        },
    )
    extra_parameter = _proposal_parameter("Temperature")
    response = execution["final_response"]
    assert isinstance(response, dict)
    response_data = response["data"]
    assert isinstance(response_data, dict)
    response_parameters = response_data["proposalParameters"]
    assert isinstance(response_parameters, list)
    response_parameters.append(deepcopy(extra_parameter))
    proposal_row = execution["proposal_db_row"]
    assert isinstance(proposal_row, dict)
    proposal_parameters = proposal_row["proposal_parameters"]
    confirmation_parameters = proposal_row["confirmation_parameters"]
    assert isinstance(proposal_parameters, list)
    assert isinstance(confirmation_parameters, list)
    proposal_parameters.append(deepcopy(extra_parameter))
    confirmation_parameters.append(deepcopy(extra_parameter))

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
            _parameter_definition("Temperature"),
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    by_name = {row.parameter_name: row for row in rows}

    assert by_name["Temperature"].verdict == "FAIL"
    assert any("mapping 밖 candidate" in issue for issue in issues)
    assert any("mapping 밖 proposal target" in issue for issue in issues)
    assert any("mapping 밖 confirmation target" in issue for issue in issues)


def test_mapping_outside_proposal_only_marks_active_parameter_row_fail() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    response = execution["final_response"]
    proposal_row = execution["proposal_db_row"]
    step_summary = execution["step_summary"]
    assert isinstance(response, dict)
    assert isinstance(proposal_row, dict)
    assert isinstance(step_summary, dict)
    response["data"]["proposalParameters"].append(
        _proposal_parameter("Temperature", include_lut=True),
    )
    proposal_row["proposal_parameters"].append(
        _proposal_parameter("Temperature"),
    )
    proposal_row["confirmation_parameters"].append(
        _proposal_parameter("Temperature"),
    )
    step_summary["proposal_parameter_count"] = 3

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
            _parameter_definition("Temperature"),
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    temperature = next(row for row in rows if row.parameter_name == "Temperature")

    assert temperature.verdict == "FAIL"
    assert temperature.eligible == 0
    assert temperature.candidate == 0
    assert temperature.proposed == 1
    assert temperature.confirmed == 1
    assert any("mapping 밖 proposal target" in issue for issue in issues)


def test_executed_matrix_fails_unstable_v3_task_identity() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    candidates = execution["expected_candidates"]
    assert isinstance(candidates, list)
    for candidate in candidates:
        if candidate["canonical_parameter_name"] == "GDP":
            candidate["candidate_key"] = "v3-source|unstable"

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert any(row.parameter_name == "GDP" and row.verdict == "FAIL" for row in rows)
    assert any("task identity" in issue for issue in issues)


def test_executed_matrix_allows_source_occurrence_keys_before_merge() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    candidates = execution["rule_candidates"]
    assert isinstance(candidates, list)
    for index, candidate in enumerate(candidates):
        candidate["candidate_key"] = f"v3-source|occurrence-{index}"

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert not any("task identity" in issue for issue in issues)
    assert {row.verdict for row in rows} == {"REVIEW"}


def test_executed_matrix_fails_unmerged_selected_parameter_tasks() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    selected = execution["expected_candidates"]
    assert isinstance(selected, list)
    gdp = next(candidate for candidate in selected if candidate["canonical_parameter_name"] == "GDP")
    selected.append(deepcopy(gdp))

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert any(row.parameter_name == "GDP" and row.verdict == "FAIL" for row in rows)
    assert any("task가 1개로 병합되지 않음" in issue for issue in issues)


def test_routing_partial_source_union_is_fail_and_zero_selection_is_review() -> None:
    mapping_rules = [
        *_mapping_rules(),
        {
            "event_type_l2_id": 20,
            "dimension_key": "supply",
            "canonical_parameter_name": "PMI",
            "mapping_method": "routing",
        },
    ]
    projection = project_expected_mappings(
        dimension_definitions=_definitions(),
        scenario_dimension_values={"composite_pressure": "high"},
        relations=_relations(),
        mapping_rules=mapping_rules,
        parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
    )
    target = _evidence(occurrences=projection.occurrences)
    all_candidates = [_runtime_candidate(item) for item in target.occurrences]
    selected_partial = [
        candidate
        for candidate in all_candidates
        if candidate["canonical_parameter_name"] != "PMI" or candidate["event_type_l2_id"] == 10
    ]
    partial_execution = _successful_execution(
        target,
        selected_candidates=selected_partial,
    )
    partial_execution["rule_candidates"] = all_candidates

    partial_rows, partial_issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={target.scenario_id: partial_execution},
        execute=True,
    )
    partial_pmi = next(row for row in partial_rows if row.parameter_name == "PMI")
    assert partial_pmi.verdict == "FAIL"
    assert any("routing selected source union 누락" in issue for issue in partial_issues)

    selected_none = [candidate for candidate in all_candidates if candidate["canonical_parameter_name"] != "PMI"]
    none_execution = _successful_execution(
        target,
        selected_candidates=selected_none,
    )
    none_execution["rule_candidates"] = all_candidates
    none_rows, _ = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        targets=[target],
        executions={target.scenario_id: none_execution},
        execute=True,
    )
    none_pmi = next(row for row in none_rows if row.parameter_name == "PMI")
    assert none_pmi.verdict == "REVIEW"
    assert "routing 후보 미선택" in none_pmi.evidence


def test_selected_routing_targets_per_composite_dimension_respect_configured_max() -> None:
    route_names = ["RouteA", "RouteB", "RouteC"]
    mapping_rules = [
        _mapping_rules()[0],
        _mapping_rules()[2],
        *[
            {
                "event_type_l2_id": 10,
                "dimension_key": "demand",
                "canonical_parameter_name": parameter_name,
                "mapping_method": "routing",
            }
            for parameter_name in route_names
        ],
    ]
    projection = project_expected_mappings(
        dimension_definitions=_definitions(),
        scenario_dimension_values={"composite_pressure": "high"},
        relations=_relations(),
        mapping_rules=mapping_rules,
        parameter_definitions=[
            _parameter_definition("GDP"),
            *[_parameter_definition(name) for name in route_names],
        ],
    )
    target = _evidence(occurrences=projection.occurrences)
    execution = _successful_execution(target)

    rows, issues = build_coverage_matrix(
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            *[_parameter_definition(name) for name in route_names],
        ],
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
        routing_limit=2,
    )

    by_name = {row.parameter_name: row for row in rows}
    assert all(by_name[name].verdict == "FAIL" for name in route_names)
    assert any("configured max=2" in issue for issue in issues)


def test_performance_rows_capture_each_step_and_guard() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    execution["llm_calls"] = [
        _llm_call("Step1.5 routing selection"),
        _llm_call("Step2 slot proposal"),
        _llm_call("Step3 value proposal"),
    ]

    rows = build_performance_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )

    assert [row.step for row in rows] == ["Step1.5", "Step2", "Step3"]
    assert {row.verdict for row in rows} == {"PASS"}
    assert {row.prompt_bytes for row in rows} == {100}
    assert {row.total_tokens for row in rows} == {15}
    assert {row.prompt_limit_bytes for row in rows} == {(1000,)}


def test_performance_rows_review_missing_retry_and_elapsed_evidence() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    calls = [
        _llm_call("Step1.5 routing selection"),
        _llm_call("Step2 slot proposal"),
        _llm_call("Step3 value proposal"),
    ]
    del calls[0]["internal_retry_count"]
    del calls[1]["elapsed_seconds"]
    execution["llm_calls"] = calls
    execution.pop("elapsed_seconds")

    rows = build_performance_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    by_step = {row.step: row for row in rows}

    assert by_step["Step1.5"].verdict == "REVIEW"
    assert "internal retry 미수집" in by_step["Step1.5"].evidence
    assert by_step["Step2"].verdict == "REVIEW"
    assert "prompt/token/time/guard 증적 일부 미수집" in by_step["Step2"].evidence
    assert all("scenario 전체 elapsed 미수집" in row.evidence for row in rows)

    missing_execution_rows = build_performance_rows(
        targets=[target],
        executions={},
        execute=True,
    )
    assert {row.verdict for row in missing_execution_rows} == {"REVIEW"}
    assert all("scenario 전체 elapsed 미수집" in row.evidence for row in missing_execution_rows)


def test_performance_rows_fail_configured_prompt_guard() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    step2_call = _llm_call("Step2 slot proposal")
    step2_call["prompt_bytes"] = 1001
    execution["llm_calls"] = [
        _llm_call("Step1.5 routing selection"),
        step2_call,
        _llm_call("Step3 value proposal"),
    ]

    rows = build_performance_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    step2 = next(row for row in rows if row.step == "Step2")

    assert step2.verdict == "FAIL"
    assert "prompt byte guard 초과" in step2.evidence


def test_positive_internal_retry_is_review_and_attempt_trace_is_rendered() -> None:
    target = _evidence()
    execution = _successful_execution(target)
    step1 = _llm_call("Step1.5 routing selection")
    step2 = _llm_call("Step2 slot proposal")
    step3 = _llm_call("Step3 value proposal")
    step2["internal_retry_count"] = 1
    execution["llm_calls"] = [step1, step2, step3]
    execution["attempts"] = 2
    execution["elapsed_seconds"] = 12.5
    execution["attempt_traces"] = [
        {
            "attempt": 1,
            "status": "FAIL",
            "elapsed_seconds": 2.0,
            "llm_calls": [step1],
            "error": "TimeoutError: details redacted",
        },
        {
            "attempt": 2,
            "status": "PASS",
            "elapsed_seconds": 10.5,
            "llm_calls": [step2, step3],
        },
    ]

    performance_rows = build_performance_rows(
        targets=[target],
        executions={target.scenario_id: execution},
        execute=True,
    )
    step2_row = next(row for row in performance_rows if row.step == "Step2")
    assert step2_row.verdict == "REVIEW"
    assert "internal retry 1회" in step2_row.evidence

    report = render_report(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execute=True,
        preflight=SchemaPreflight("PASS", ("schema ok",)),
        selected_targets=[target],
        skipped_targets=[],
        discovery_messages=[],
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        coverage_rows=[],
        executions={target.scenario_id: execution},
        integrity_issues=[],
    )

    assert "### Scenario overall 및 attempt trace" in report
    assert "| 501 | 12.500s | 1 | FAIL | 2.000s |" in report
    assert "| 501 | 12.500s | 2 | PASS | 10.500s |" in report
    assert "복합 압력의 방향과 강도를 단일 값으로 반영했다." in report


def test_execute_report_contains_bounded_stage_input_output_evidence() -> None:
    target = _evidence()
    execution = _successful_execution(target)

    report = render_report(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execute=True,
        preflight=SchemaPreflight("PASS", ("schema ok",)),
        selected_targets=[target],
        skipped_targets=[],
        discovery_messages=[],
        active_parameter_definitions=[
            _parameter_definition("GDP"),
            _parameter_definition("PMI"),
        ],
        coverage_rows=[],
        executions={target.scenario_id: execution},
        integrity_issues=[],
    )

    assert "## 단계별 LLM 입출력 증적" in report
    assert "production과 동일한 packet builder로 사후 재구성" in report
    assert "<details><summary>Step1.5 입력/출력</summary>" in report
    assert "<details><summary>Step2 입력/출력</summary>" in report
    assert "<details><summary>Step3 입력/출력</summary>" in report
    assert '"routing_tasks"' in report
    assert '"parameter_slot_tasks"' in report
    assert '"parameter_value_tasks"' in report
    assert '"selected_candidates"' in report
    assert '"selected_slots"' in report
    assert '"parameter_adjustments"' in report
    assert '"api_event_id": null' in report


def test_nullable_proposal_serializer_keeps_event_id_none() -> None:
    now = datetime.now(UTC)
    proposal = SimpleNamespace(
        model_param_proposal_id=9001,
        scenario_id=501,
        scenario_group_id=50,
        mi_event_id=None,
        request_usr_id=None,
        status="PROPOSED",
        callback_status="SKIPPED",
        proposal_completed_dtm=now,
        callback_sent_dtm=None,
        confirmed_dtm=None,
        error_code=None,
        error_message=None,
        proposal_parameters=[_proposal_parameter("GDP")],
        confirmation_parameters=None,
        mod_usr_logn_id="system",
        mod_dtm=now,
    )

    serialized = serialize_proposal_row(proposal)

    assert serialized["mi_event_id"] is None
    assert serialized["scenario_group_id"] == 50


@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("basecaseValue", float("nan")),
        ("basecaseValue", float("inf")),
        ("proposedValue", float("-inf")),
    ],
)
def test_persistence_contract_rejects_non_finite_numeric_values(
    field_name: str,
    invalid_value: float,
) -> None:
    from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
        _parameter_json_payload,
    )

    with pytest.raises(Exception, match="finite number"):
        _parameter_json_payload(
            {
                "values": [
                    {
                        "basecaseValue": 1.0,
                        "proposedValue": 1.1,
                        field_name: invalid_value,
                    },
                ],
            },
        )


def test_automated_contract_preflight_records_actual_case_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commands: list[list[str]] = []

    def fake_run(command: list[str], **_: object) -> SimpleNamespace:
        commands.append(command)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(quality_runner.subprocess, "run", fake_run)

    evidence = run_automated_contract_preflight(timeout_seconds=1)

    assert evidence.verdict == "PASS"
    assert len(evidence.cases) == len(quality_runner.CONTRACT_TEST_CASES)
    assert {case.verdict for case in evidence.cases} == {"PASS"}
    assert all("no:cacheprovider" in command for command in commands)
    assert all(command[-1] == case.node_id for command, case in zip(commands, evidence.cases, strict=True))


def test_report_redacts_sensitive_exception_output() -> None:
    target = _evidence()
    target.ordered_events[0]["title"] = "api_key=event-secret"
    target.dimension_values["composite_pressure"] = "password=dimension-secret"
    secret = "mysql://user:super-secret@db.local/schema?token=abc123"
    execution = _successful_execution(target)
    execution.update(
        {
            "error": f"ConnectionError: {secret} password=hunter2",
            "attempts": 1,
            "elapsed_seconds": 0.2,
            "attempt_traces": [
                {
                    "attempt": 1,
                    "status": "FAIL",
                    "elapsed_seconds": 0.2,
                    "error": f"Authorization=BearerSecret {secret}",
                },
            ],
        },
    )
    api_parameter = execution["final_response"]["data"]["proposalParameters"][0]
    api_parameter["rationale"] = "authorization=proposal-secret"
    api_parameter["values"][0]["SecretAxis"] = "token=coordinate-secret"
    api_parameter["values"][0]["rationale"] = "secret=value-secret"

    report = render_report(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        execute=True,
        preflight=SchemaPreflight("PASS", ("schema ok",)),
        selected_targets=[target],
        skipped_targets=[],
        discovery_messages=[],
        active_parameter_definitions=[_parameter_definition("GDP")],
        coverage_rows=[
            CoverageRow("GDP", 2, 0, 0, 0, 0, "FAIL", "execution error"),
        ],
        executions={target.scenario_id: execution},
        integrity_issues=[],
    )

    assert "super-secret" not in report
    assert "hunter2" not in report
    assert "abc123" not in report
    assert "event-secret" not in report
    assert "dimension-secret" not in report
    assert "proposal-secret" not in report
    assert "coordinate-secret" not in report
    assert "value-secret" not in report
    assert "[URL REDACTED]" in report


def test_cli_defaults_to_read_only_discovery() -> None:
    args = build_parser().parse_args([])

    assert args.execute is False
    assert args.scenario_group_id is None
    assert args.scenario_id is None
    assert args.max_scenarios == 5


def test_integrated_markdown_report_contains_matrix_verdict_contract() -> None:
    target = _evidence()
    rows = [
        CoverageRow("GDP", 2, None, None, None, None, "COVERAGE LIMIT", "read-only"),
        CoverageRow("PMI", 1, 1, 0, 0, 0, "REVIEW", "routing 검토"),
        CoverageRow("Temperature", 1, 0, 0, 0, 0, "FAIL", "candidate 누락"),
        CoverageRow("PowerMix", 1, 1, 1, 1, 1, "PASS", "일치"),
    ]
    now = datetime.now(UTC)
    contract_evidence = ContractEvidence(
        verdict="PASS",
        cases=tuple(
            ContractCaseEvidence(name, node_id, "PASS", "isolated test passed")
            for name, node_id in quality_runner.CONTRACT_TEST_CASES
        ),
        elapsed_seconds=1.25,
        evidence="all passed",
    )

    report = render_report(
        started_at=now,
        finished_at=now,
        execute=False,
        preflight=SchemaPreflight("PASS", ("schema ok",)),
        selected_targets=[target],
        skipped_targets=[],
        discovery_messages=[],
        active_parameter_definitions=[_parameter_definition(row.parameter_name) for row in rows],
        coverage_rows=rows,
        executions={},
        integrity_issues=[],
        contract_evidence=contract_evidence,
    )

    assert "# Model Parameter v3 Multi-Event Quality Report" in report
    assert "eligible | candidate | selected | proposed | confirmed" in report
    assert "## Slot/reference/value/rationale 계약" in report
    assert "## 성능 및 관측성" in report
    assert "## Confirmation regression evidence" in report
    assert "## Ordered event grounding evidence" in report
    assert "## 단계별 LLM 입출력 증적" in report
    assert "수요 충격" in report
    assert "composite_pressure" in report
    assert "### Proposed value grounding 수동 검토" in report
    assert all(case.node_id in report for case in contract_evidence.cases)
    assert "invalid-status workflow no-mutation" in report
    assert "UNIT PASS" in report
    for verdict in ("PASS", "REVIEW", "FAIL", "COVERAGE LIMIT"):
        assert verdict in report


def test_integrated_report_fails_180_second_performance_contract() -> None:
    target = _evidence()
    now = datetime.now(UTC)
    execution = _successful_execution(target)
    execution["elapsed_seconds"] = 181.0
    execution["llm_calls"] = [
        _llm_call("Step1.5 routing selection"),
        _llm_call("Step2 slot proposal"),
        _llm_call("Step3 value proposal"),
    ]
    report = render_report(
        started_at=now,
        finished_at=now,
        execute=True,
        preflight=SchemaPreflight("PASS", ("schema ok",)),
        selected_targets=[target],
        skipped_targets=[],
        discovery_messages=[],
        active_parameter_definitions=[_parameter_definition("GDP")],
        coverage_rows=[
            CoverageRow("GDP", 2, 2, 2, 1, 1, "PASS", "일치"),
        ],
        executions={501: execution},
        integrity_issues=[],
    )

    assert "- 판정: **FAIL**" in report
    assert "| 501 | Step1.5 | 1 | 100 / 1000 | 10/5/15 | 1.500s | 0 | 0 | FAIL |" in report
    assert "scenario 전체 180초 초과" in report
