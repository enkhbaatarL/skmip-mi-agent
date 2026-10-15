# ruff: noqa: S101

from __future__ import annotations

import asyncio
from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from apps.agents.model_parameter_agent.flows.propose_parameters import nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _build_candidate_validation_prompt_packet,
    _merge_candidates_by_parameter,
    _merge_v3_routing_candidates_for_validation,
    _partition_candidate_validation_work,
    _routing_groups_by_dimension,
    _scenario_brief_for_value_prompt,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    _load_v3_context,
)
from apps.agents.model_parameter_agent.presentation import _to_response_data
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    MappingRule,
    ParameterDefinition,
    ParameterKnowledgeBase,
    match_parameter_candidates,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


V3_STRATEGY = "multi_event_composite_dimensions"


def _scenario(*, dimension_values: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_id=501,
        scenario_group_id=701,
        title="멀티 이벤트 시나리오",
        narrative="연결된 이벤트를 함께 반영한다.",
        status="created",
        dimension_values=dimension_values,
        probability_score=0.5,
        probability_delta=0.0,
        impact_jkm=None,
        impact_ttf=None,
        impact_hh=None,
        baseline_yn="N",
    )


def _group(*, definitions: list[dict[str, Any]], mapping_ready: bool) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_id=701,
        mi_event_id=None,
        event_type_l2_id=None,
        request_usr_id=41,
        title="멀티 이벤트 그룹",
        summary="복합 압력",
        description="여러 사건에서 파생된 복합 차원",
        dimension_selected=[definition["dimensionId"] for definition in definitions],
        scenario_count=1,
        status="created",
        stage="scenario_created",
        api_version="v3",
        generation_strategy=V3_STRATEGY,
        parameter_mapping_ready=mapping_ready,
        dimension_definitions=definitions,
    )


def _relation(index: int) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_event_id=9000 + index,
        scenario_group_id=701,
        mi_event_id=100 + index,
        event_type_l2_id=10 + index,
        scenario_dimension_template_id=1000 + index,
        template_checksum=f"checksum-{index}",
        display_order=index,
    )


def _composite_definition(event_count: int) -> dict[str, Any]:
    return {
        "dimensionId": "composite_pressure",
        "label": "복합 압력",
        "description": "연결 사건이 만드는 복합 압력",
        "rationale": "각 사건의 공급 영향을 함께 본다.",
        "sourceEventIds": [100 + index for index in range(1, event_count + 1)],
        "sourceRefs": [
            {
                "scenarioDimensionTemplateId": 1000 + index,
                "dimKey": f"source_dimension_{index}",
            }
            for index in range(1, event_count + 1)
        ],
        "values": [
            {
                "valueId": "pressure_high",
                "label": "높음",
                "description": "공급 압력이 높다.",
                "derivationRationale": "연결 사건이 동시에 지속된다.",
                "pressureContribution": "상방",
            },
        ],
    }


def _dimension_mapping(
    *,
    display_value: str,
    status: str,
    source_projections: list[dict[str, Any]],
) -> SimpleNamespace:
    return SimpleNamespace(
        dimension_value_id="dv-custom",
        dimension_id="composite_pressure",
        display_value=display_value,
        source_projections=source_projections,
        mapping_proposal={"reason": "test"},
        mapping_version=1,
        status=status,
    )


def _load_test_context(
    *,
    event_count: int,
    definition: dict[str, Any] | None = None,
    selected_value: str = "높음",
    mappings: list[SimpleNamespace] | None = None,
    mapping_ready: bool = True,
    api_version: str = "v3",
) -> dict[str, Any]:
    active_definition = definition or _composite_definition(event_count)
    relations = [_relation(index) for index in range(1, event_count + 1)]
    event_rows = {
        relation.mi_event_id: {
            "mi_event_id": str(relation.mi_event_id),
            "event_type_l2_id": relation.event_type_l2_id,
            "event_title_ko": f"이벤트 {relation.display_order}",
            "one_line_summary": f"요약 {relation.display_order}",
            "key_bullets": [f"bullet-{number}" for number in range(8)],
            "detail_analysis": "상세" * 800,
            "tags": [f"tag-{number}" for number in range(12)],
        }
        for relation in relations
    }
    event_types = {
        relation.event_type_l2_id: {
            "event_type_l2_id": relation.event_type_l2_id,
            "level_1_code": "SUPPLY",
            "level_1_label": "공급",
            "level_2_code": f"TYPE_{relation.display_order}",
            "level_2_label": f"유형 {relation.display_order}",
        }
        for relation in relations
    }
    scenario_repository = SimpleNamespace(
        fetch_mappings_by_group_id=Mock(return_value=mappings or []),
    )
    group_repository = SimpleNamespace(
        fetch_group_events=Mock(return_value=relations),
    )
    event_repository = SimpleNamespace(
        fetch_event_by_id=Mock(side_effect=event_rows.get),
        fetch_event_type_by_l2_id=Mock(side_effect=event_types.get),
    )
    group = _group(
        definitions=[active_definition],
        mapping_ready=mapping_ready,
    )
    group.api_version = api_version
    return _load_v3_context(
        scenario=_scenario(
            dimension_values={"composite_pressure": selected_value},
        ),
        group=group,
        scenario_repository=scenario_repository,
        group_repository=group_repository,
        event_repository=event_repository,
    )


def _parameter_definition(
    name: str,
    *,
    model_file: str = "Supply",
    model_sheet: str = "Target",
) -> ParameterDefinition:
    return ParameterDefinition(
        canonical_parameter_name=name,
        parameter_hint=f"{name} hint",
        model_file=model_file,
        model_sheet=model_sheet,
        model_table="InputTable",
        parameter_name=name,
        semantic_axes="Country, Year",
        basecase_read_mode=None,
        basecase_header_row=None,
        basecase_data_start_row=None,
        basecase_column_roles=None,
        basecase_row_filter=None,
        basecase_year_row=None,
        basecase_month_row=None,
        basecase_period_row=None,
        basecase_value_start_col=None,
        basecase_value_end_col=None,
        basecase_stop_rule=None,
    )


def _knowledge_base(
    *,
    rules: list[MappingRule],
    definitions: list[ParameterDefinition],
) -> ParameterKnowledgeBase:
    return ParameterKnowledgeBase(
        mapping_source="test",
        basecase_dir_path="",
        parameter_definitions={definition.canonical_parameter_name: definition for definition in definitions},
        mapping_rules=rules,
        basecase_profiles={},
    )


def _mapped_source(
    *,
    event_type_l2_id: int,
    mapping_dimension_key: str,
    template_id: int,
    event_ids: list[int],
) -> dict[str, Any]:
    return {
        "mapping_dimension_key": mapping_dimension_key,
        "event_type_l2_id": event_type_l2_id,
        "scenario_dimension_template_id": template_id,
        "source_event_ids": event_ids,
        "source_ref": {
            "scenario_dimension_template_id": template_id,
            "dim_key": mapping_dimension_key,
        },
    }


def _lineage(
    composite_key: str,
    mapped_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    source_event_ids = [event_id for mapped_source in mapped_sources for event_id in mapped_source["source_event_ids"]]
    return {
        "scenario_dimension_key": composite_key,
        "scenario_dimension_label": composite_key,
        "scenario_dimension_value": "높음",
        "scenario_dimension_value_label": "높음",
        "source_event_ids": list(dict.fromkeys(source_event_ids)),
        "source_refs": [mapped_source["source_ref"] for mapped_source in mapped_sources],
        "mapped_sources": mapped_sources,
        "approved_source_projections": [],
        "parameter_mapping_ready": False,
        "is_free_value": False,
    }


def _matcher_context(lineage: list[dict[str, Any]]) -> dict[str, Any]:
    event_type_ids = {mapped_source["event_type_l2_id"] for item in lineage for mapped_source in item["mapped_sources"]}
    return {
        "scenario_group": {"generation_strategy": V3_STRATEGY},
        "events": [
            {
                "event_type_l2_id": event_type_l2_id,
                "event_type": {
                    "level_2_code": f"TYPE_{event_type_l2_id}",
                    "level_2_label": f"유형 {event_type_l2_id}",
                },
            }
            for event_type_l2_id in sorted(event_type_ids)
        ],
        "dimension_lineage": lineage,
    }


@pytest.mark.parametrize("event_count", [2, 5])
def test_v3_context_loads_two_and_five_events_in_display_order(event_count: int) -> None:
    context = _load_test_context(event_count=event_count)

    assert [event["mi_event_id"] for event in context["events"]] == [100 + index for index in range(1, event_count + 1)]
    assert [event["display_order"] for event in context["events"]] == list(
        range(1, event_count + 1),
    )
    assert len(context["dimension_lineage"][0]["mapped_sources"]) == event_count
    assert context["event"] == {}
    assert context["event_type"] == {}


@pytest.mark.parametrize("event_count", [1, 6])
def test_v3_context_rejects_event_counts_outside_two_to_five(
    event_count: int,
) -> None:
    with pytest.raises(MIBaseError) as caught:
        _load_test_context(event_count=event_count)

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "must contain 2 to 5 event relations" in caught.value.error_message


@pytest.mark.parametrize(
    ("case", "expected_detail"),
    [
        ("malformed", "sourceRef.dimKey is required"),
        ("outside", "not members of the scenario group"),
        ("template_mismatch", "does not match a scenario group event relation"),
    ],
)
def test_v3_context_rejects_invalid_lineage_before_candidate_matching(
    case: str,
    expected_detail: str,
) -> None:
    definition = deepcopy(_composite_definition(2))
    if case == "malformed":
        definition["sourceRefs"] = [{"scenarioDimensionTemplateId": 1001}]
    elif case == "outside":
        definition["sourceEventIds"] = [101, 999]
    else:
        definition["sourceEventIds"] = [101]
        definition["sourceRefs"] = [
            {
                "scenarioDimensionTemplateId": 1002,
                "dimKey": "source_dimension_2",
            },
        ]

    with pytest.raises(MIBaseError) as caught:
        _load_test_context(event_count=2, definition=definition)

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert expected_detail in caught.value.error_message


def test_v3_context_requires_explicit_v3_api_version() -> None:
    with pytest.raises(MIBaseError) as caught:
        _load_test_context(event_count=2, api_version="")

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "requires api_version=v3" in caught.value.error_message


def test_v3_context_rejects_group_event_orphaned_from_selected_lineage() -> None:
    definition = deepcopy(_composite_definition(2))
    definition["sourceEventIds"] = [101]
    definition["sourceRefs"] = [
        {
            "scenarioDimensionTemplateId": 1001,
            "dimKey": "source_dimension_1",
        },
    ]

    with pytest.raises(MIBaseError) as caught:
        _load_test_context(event_count=2, definition=definition)

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "not referenced by selected dimension lineage" in caught.value.error_message


@pytest.mark.parametrize(
    ("status", "expected_projection_count", "expected_warning"),
    [
        ("approved", 1, None),
        ("pending", 0, "source projection is not approved"),
        ("rejected", 0, "source projection is not approved"),
        (None, 0, "free dimension value has no approved source projection"),
    ],
)
def test_v3_free_value_projection_status_is_supplementary_evidence(
    status: str | None,
    expected_projection_count: int,
    expected_warning: str | None,
) -> None:
    projection = {
        "scenario_dimension_template_id": 1001,
        "dim_key": "source_dimension_1",
        "value": "높음",
        "source_type": "llm",
    }
    mappings = (
        [
            _dimension_mapping(
                display_value="사용자 정의 압력",
                status=status,
                source_projections=[projection],
            ),
        ]
        if status is not None
        else []
    )

    context = _load_test_context(
        event_count=2,
        selected_value="사용자 정의 압력",
        mappings=mappings,
        mapping_ready=True,
    )

    lineage = context["dimension_lineage"][0]
    assert lineage["is_free_value"] is True
    assert len(lineage["approved_source_projections"]) == expected_projection_count
    if expected_projection_count:
        assert lineage["approved_source_projections"] == [projection]
    if expected_warning is None:
        assert context["validation_warnings"] == []
    else:
        assert any(expected_warning in warning for warning in context["validation_warnings"])


def test_v3_free_value_warns_when_approved_mapping_has_no_projection() -> None:
    context = _load_test_context(
        event_count=2,
        selected_value="사용자 정의 압력",
        mappings=[
            _dimension_mapping(
                display_value="사용자 정의 압력",
                status="approved",
                source_projections=[],
            ),
        ],
        mapping_ready=True,
    )

    lineage = context["dimension_lineage"][0]
    assert lineage["approved_source_projections"] == []
    assert any(
        "free dimension value has no approved source projection" in warning
        for warning in context["validation_warnings"]
    )


def test_v3_one_composite_dimension_expands_to_direct_and_routing_parameters() -> None:
    mapped_source = _mapped_source(
        event_type_l2_id=11,
        mapping_dimension_key="source_pressure",
        template_id=1001,
        event_ids=[101, 102],
    )
    rules = [
        MappingRule(
            event_type_l2_id=11,
            dimension_key="source_pressure",
            dimension_label="원본 압력",
            canonical_parameter_name="ParamA",
            mapping_method="direct",
            comment="A 직접",
        ),
        MappingRule(
            event_type_l2_id=11,
            dimension_key="source_pressure",
            dimension_label="원본 압력",
            canonical_parameter_name="ParamB",
            mapping_method="routing",
            comment="B 조건부",
        ),
    ]
    kb = _knowledge_base(
        rules=rules,
        definitions=[
            _parameter_definition("ParamA", model_sheet="SheetA"),
            _parameter_definition("ParamB", model_sheet="SheetB"),
        ],
    )

    candidates, non_inputs, warnings = match_parameter_candidates(
        kb,
        _matcher_context([_lineage("composite_pressure", [mapped_source])]),
    )

    assert non_inputs == []
    assert warnings == []
    assert {(candidate["canonical_parameter_name"], candidate["mapping_method"]) for candidate in candidates} == {
        ("ParamA", "direct"),
        ("ParamB", "routing"),
    }
    assert all(candidate["source_event_ids"] == [101, 102] for candidate in candidates)


def test_v3_dimensions_and_event_types_converge_to_one_stable_parameter_task() -> None:
    first_source = _mapped_source(
        event_type_l2_id=11,
        mapping_dimension_key="first_source",
        template_id=1001,
        event_ids=[101],
    )
    second_source = _mapped_source(
        event_type_l2_id=12,
        mapping_dimension_key="second_source",
        template_id=1002,
        event_ids=[102],
    )
    kb = _knowledge_base(
        rules=[
            MappingRule(
                event_type_l2_id=11,
                dimension_key="first_source",
                dimension_label="첫 원본",
                canonical_parameter_name="SharedParameter",
                mapping_method="direct",
                comment="첫 근거",
            ),
            MappingRule(
                event_type_l2_id=12,
                dimension_key="second_source",
                dimension_label="둘째 원본",
                canonical_parameter_name="SharedParameter",
                mapping_method="direct",
                comment="둘째 근거",
            ),
        ],
        definitions=[_parameter_definition("SharedParameter")],
    )
    context = _matcher_context(
        [
            _lineage("composite_supply", [first_source]),
            _lineage("composite_duration", [second_source]),
        ],
    )

    source_candidates, non_inputs, warnings = match_parameter_candidates(kb, context)
    merged, merge_warnings = _merge_candidates_by_parameter(source_candidates)
    reverse_merged, _ = _merge_candidates_by_parameter(list(reversed(source_candidates)))

    assert non_inputs == []
    assert warnings == []
    assert merge_warnings == []
    assert len(source_candidates) == 2
    assert len(merged) == 1
    assert merged[0]["candidate_key"] == "parameter|v3|supply|target|sharedparameter"
    assert reverse_merged[0]["candidate_key"] == merged[0]["candidate_key"]
    assert set(merged[0]["source_event_ids"]) == {101, 102}
    assert {item["scenario_dimension_key"] for item in merged[0]["source_dimensions"]} == {
        "composite_supply",
        "composite_duration",
    }
    assert {item["event_type_l2_id"] for item in merged[0]["source_dimensions"]} == {11, 12}


def test_v3_routing_convergence_preserves_all_sources_before_selection() -> None:
    first_source = _mapped_source(
        event_type_l2_id=11,
        mapping_dimension_key="first_source",
        template_id=1001,
        event_ids=[101],
    )
    second_source = _mapped_source(
        event_type_l2_id=12,
        mapping_dimension_key="second_source",
        template_id=1002,
        event_ids=[102],
    )
    kb = _knowledge_base(
        rules=[
            MappingRule(
                event_type_l2_id=11,
                dimension_key="first_source",
                dimension_label="첫 원본",
                canonical_parameter_name="SharedParameter",
                mapping_method="routing",
                comment="첫 조건",
            ),
            MappingRule(
                event_type_l2_id=12,
                dimension_key="second_source",
                dimension_label="둘째 원본",
                canonical_parameter_name="SharedParameter",
                mapping_method="routing",
                comment="둘째 조건",
            ),
        ],
        definitions=[_parameter_definition("SharedParameter")],
    )
    context = _matcher_context(
        [
            _lineage(
                "composite_pressure",
                [first_source, second_source],
            ),
        ],
    )

    source_candidates, _, _ = match_parameter_candidates(kb, context)
    validation_candidates = _merge_v3_routing_candidates_for_validation(
        source_candidates,
    )
    _, routing_tasks = _partition_candidate_validation_work(
        validation_candidates,
    )
    final_candidates, _ = _merge_candidates_by_parameter(
        validation_candidates,
    )

    assert len(source_candidates) == 2
    assert len(validation_candidates) == 1
    assert len(routing_tasks) == 1
    assert len(routing_tasks[0]["candidates"]) == 1
    assert set(validation_candidates[0]["source_event_ids"]) == {101, 102}
    assert {source["mapping_dimension_key"] for source in validation_candidates[0]["source_dimensions"]} == {
        "first_source",
        "second_source",
    }
    assert final_candidates[0]["candidate_key"] == ("parameter|v3|supply|target|sharedparameter")


def test_v1_candidate_key_remains_unchanged_before_and_after_merge() -> None:
    kb = _knowledge_base(
        rules=[
            MappingRule(
                event_type_l2_id=7,
                dimension_key="heatwave_intensity",
                dimension_label="폭염 강도",
                canonical_parameter_name="CDD",
                mapping_method="direct",
                comment="CDD 직접 조정",
            ),
        ],
        definitions=[
            _parameter_definition(
                "CDD",
                model_file="Demand",
                model_sheet="WeatherAdjustment",
            ),
        ],
    )
    context = {
        "scenario": {"dimension_values": {"heatwave_intensity": "강"}},
        "scenario_group": {
            "event_type_l2_id": 7,
            "generation_strategy": "single_event_template_dimensions",
        },
        "event_type": {"level_2_code": "HEAT", "level_2_label": "폭염"},
        "dimension_template": [
            {"dim_key": "heatwave_intensity", "label": "폭염 강도"},
        ],
    }

    candidates, _, warnings = match_parameter_candidates(kb, context)
    merged, _ = _merge_candidates_by_parameter(candidates)

    expected_key = "7|heatwaveintensity|cdd|demand|weatheradjustment"
    assert warnings == []
    assert candidates[0]["candidate_key"] == expected_key
    assert merged[0]["candidate_key"] == expected_key


def test_v3_routing_groups_use_composite_dimension_key() -> None:
    mapped_source = _mapped_source(
        event_type_l2_id=11,
        mapping_dimension_key="original_pressure",
        template_id=1001,
        event_ids=[101],
    )
    kb = _knowledge_base(
        rules=[
            MappingRule(
                event_type_l2_id=11,
                dimension_key="original_pressure",
                dimension_label="원본 압력",
                canonical_parameter_name="ConditionalParameter",
                mapping_method="routing",
                comment="조건 충족 시 선택",
            ),
        ],
        definitions=[_parameter_definition("ConditionalParameter")],
    )
    candidates, _, _ = match_parameter_candidates(
        kb,
        _matcher_context([_lineage("composite_pressure", [mapped_source])]),
    )

    groups = _routing_groups_by_dimension(candidates)
    deterministic, routing_tasks = _partition_candidate_validation_work(candidates)

    assert set(groups) == {("v3", "composite_pressure")}
    assert deterministic == []
    assert routing_tasks[0]["dimension_key"] == "composite_pressure"
    assert routing_tasks[0]["candidates"][0]["mapping_dimension_key"] == "original_pressure"
    packet_candidate = _build_candidate_validation_prompt_packet(
        _matcher_context([_lineage("composite_pressure", [mapped_source])]),
        routing_tasks,
    )["routing_tasks"][0]["candidates"][0]
    assert packet_candidate["event_type_l2_id"] == 11
    assert packet_candidate["mapping_dimension_key"] == "original_pressure"
    assert packet_candidate["source_event_ids"] == [101]
    assert packet_candidate["source_refs"] == [mapped_source["source_ref"]]


def test_step15_prompt_includes_related_indirect_dimension() -> None:
    routing_source = _mapped_source(
        event_type_l2_id=11,
        mapping_dimension_key="original_pressure",
        template_id=1001,
        event_ids=[101],
    )
    indirect_source = _mapped_source(
        event_type_l2_id=12,
        mapping_dimension_key="original_duration",
        template_id=1002,
        event_ids=[102],
    )
    unrelated_source = _mapped_source(
        event_type_l2_id=13,
        mapping_dimension_key="original_unrelated",
        template_id=1003,
        event_ids=[103],
    )
    kb = _knowledge_base(
        rules=[
            MappingRule(
                event_type_l2_id=11,
                dimension_key="original_pressure",
                dimension_label="원본 압력",
                canonical_parameter_name="ConditionalParameter",
                mapping_method="routing",
                comment="조건 충족 시 선택",
            ),
            MappingRule(
                event_type_l2_id=12,
                dimension_key="original_duration",
                dimension_label="원본 기간",
                canonical_parameter_name="",
                mapping_method="indirect",
                comment="값 산정의 보조 근거",
            ),
        ],
        definitions=[_parameter_definition("ConditionalParameter")],
    )
    context = _matcher_context(
        [
            _lineage("composite_pressure", [routing_source]),
            _lineage("composite_duration", [indirect_source]),
            _lineage("composite_unrelated", [unrelated_source]),
        ],
    )
    candidates, non_inputs, _ = match_parameter_candidates(kb, context)
    _, routing_tasks = _partition_candidate_validation_work(candidates)

    packet = _build_candidate_validation_prompt_packet(
        context,
        routing_tasks,
        non_inputs,
    )

    selected_keys = {item["dimension_key"] for item in packet["scenario_brief"]["selected_dimensions"]}
    assert selected_keys == {"composite_pressure", "composite_duration"}


def test_step15_prompt_guard_blocks_llm_before_routing_call() -> None:
    mapped_source = _mapped_source(
        event_type_l2_id=11,
        mapping_dimension_key="original_pressure",
        template_id=1001,
        event_ids=[101],
    )
    kb = _knowledge_base(
        rules=[
            MappingRule(
                event_type_l2_id=11,
                dimension_key="original_pressure",
                dimension_label="원본 압력",
                canonical_parameter_name="ConditionalParameter",
                mapping_method="routing",
                comment="조건 충족 시 선택",
            ),
        ],
        definitions=[_parameter_definition("ConditionalParameter")],
    )
    context = _matcher_context(
        [_lineage("composite_pressure", [mapped_source])],
    )
    candidates, _, _ = match_parameter_candidates(kb, context)
    state = ModelParameterProposalState(
        scenario_id=501,
        scenario_context=context,
        candidate_mappings=candidates,
    )
    settings = SimpleNamespace(
        model_parameter_max_routing_candidates_per_dimension=2,
        model_parameter_max_step2_prompt_bytes=1,
    )
    invoke = AsyncMock()

    with (
        patch.object(nodes, "get_settings", return_value=settings),
        patch.object(nodes, "_invoke_structured", invoke),
        pytest.raises(MIBaseError) as caught,
    ):
        asyncio.run(nodes.validate_parameter_candidates(state))

    invoke.assert_not_awaited()
    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "Step1.5 compact prompt exceeds configured byte limit" in caught.value.error_message


def test_v3_presentation_keeps_existing_event_id_field_null() -> None:
    response = _to_response_data(
        {
            "scenario_id": 501,
            "scenario_context": {
                "scenario": {"scenario_id": 501, "scenario_group_id": 701},
                "scenario_group": {
                    "scenario_group_id": 701,
                    "mi_event_id": None,
                    "generation_strategy": V3_STRATEGY,
                },
                "event": {},
                "events": [{"mi_event_id": 101}, {"mi_event_id": 102}],
            },
        },
        model_param_proposal_id=901,
        proposal_parameters=[],
    )

    assert response.scenario_group_id == 701
    assert response.event_id is None
    assert response.model_dump(by_alias=True)["eventId"] is None


def test_five_event_prompt_is_bounded_and_step2_guard_runs_before_llm() -> None:
    context = _load_test_context(event_count=5)
    context["scenario"]["dimension_values"]["unrelated"] = "제외"
    context["scenario_group"]["dimension_selected"].append("unrelated")
    context["dimension_template"].append(
        {"dimensionId": "unrelated", "label": "무관 차원"},
    )
    brief = _scenario_brief_for_value_prompt(
        context,
        allowed_dimension_keys={"composite_pressure"},
    )

    assert len(brief["events"]) == 5
    assert "unrelated" not in brief["scenario"]["dimension_values"]
    assert "unrelated" not in brief["scenario_group"]["dimension_selected"]
    assert [event["event_id"] for event in brief["events"]] == [101, 102, 103, 104, 105]
    assert all(len(event["key_bullets"]) == 5 for event in brief["events"])
    assert all(len(event["tags"]) == 8 for event in brief["events"])
    assert all(len(event["detail_excerpt"]) == 1600 for event in brief["events"])

    candidate = {
        "candidate_key": "parameter|v3|supply|target|sharedparameter",
        "mapping_strategy": "v3",
        "scenario_dimension_key": "composite_pressure",
        "dimension_key": "composite_pressure",
        "source_dimension_id": "composite_pressure",
        "source_dimension_label": "복합 압력",
        "source_dimension_value": "높음",
        "source_event_ids": [101, 102, 103, 104, 105],
        "canonical_parameter_name": "SharedParameter",
        "parameter_name": "SharedParameter",
        "model_file": "Supply",
        "model_sheet": "Target",
        "mapping_method": "direct",
    }
    state = ModelParameterProposalState(
        scenario_id=501,
        scenario_context=context,
        candidate_mappings=[candidate],
        slot_catalog=[],
    )
    settings = SimpleNamespace(
        model_parameter_max_parameter_slots=100,
        model_parameter_max_total_selected_slots=300,
        model_parameter_max_step2_prompt_bytes=1,
    )
    invoke = AsyncMock()

    with (
        patch.object(nodes, "get_settings", return_value=settings),
        patch.object(nodes, "_invoke_structured", invoke),
        pytest.raises(MIBaseError) as caught,
    ):
        asyncio.run(nodes.propose_parameter_slots(state))

    invoke.assert_not_awaited()
    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "Step2 compact prompt exceeds configured byte limit" in caught.value.error_message
