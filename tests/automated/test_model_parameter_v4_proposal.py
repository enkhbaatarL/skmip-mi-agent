# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import pytest

from apps.agents.model_parameter_agent.flows.confirm_parameters.flow import (
    to_output as confirmation_to_output,
    to_state as confirmation_to_state,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.nodes import (
    confirm_parameters,
)
from apps.agents.model_parameter_agent.flows.propose_parameters import nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.flow import (
    prepare_propose_parameters_callback,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _build_candidate_validation_prompt_packet,
    _build_value_proposal_prompt_packet,
    _compact_numeric_facts_md,
    _merge_candidates_by_parameter,
    _partition_candidate_validation_work,
    _routing_candidate_prompt_payload,
    _routing_task_for_prompt,
    _sanitize_llm_adjustments,
    _scenario_brief_for_value_prompt,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
    _load_v4_context,
    _proposal_event_id,
)
from apps.agents.model_parameter_agent.presentation import _context_ids
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMValueAdjustment,
    LLMValueCell,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    MappingRule,
    ParameterDefinition,
    ParameterKnowledgeBase,
    match_parameter_candidates,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload


V4_STRATEGY = "multi_event_model_lever_dimensions"
CATALOG_VERSION = "v4"
CATALOG_CHECKSUM = "catalog-checksum-v4"


@pytest.mark.parametrize(
    ("proposed_value", "warning_fragment"),
    [(4.5, "최대값"), (3.5, "정수 제약")],
)
def test_hurricane_step3_rejects_out_of_range_or_non_integer_values(
    proposed_value: float,
    warning_fragment: str,
) -> None:
    candidate_key = "parameter|12"
    sanitized, warnings = _sanitize_llm_adjustments(
        [
            LLMValueAdjustment(
                candidate_key=candidate_key,
                slot_values=[
                    LLMValueCell(slot_key="slot-1", proposed_value=proposed_value, rationale_ko="test"),
                ],
                rationale_ko="test",
            ),
        ],
        [
            {
                "candidate_key": candidate_key,
                "canonical_parameter_name": "HurricaneIntensity",
                "proposal_constraints": {"minimum": 0, "maximum": 4, "integer_only": True},
            },
        ],
        [
            {
                "candidate_key": candidate_key,
                "slot_key": "slot-1",
                "slot_axes": [
                    {"axis_name": "Year", "axis_value": 2027},
                    {"axis_name": "Month", "axis_value": 8},
                ],
            },
        ],
        [
            {
                "candidate_key": candidate_key,
                "slot_key": "slot-1",
                "axes": {"Year": 2027, "Month": 8},
                "value": 0,
                "reference_id": "test:hurricane",
            },
        ],
        scenario_context={
            "scenario_group": {
                "api_version": "v4",
                "generation_strategy": V4_STRATEGY,
            },
        },
    )

    assert sanitized == []
    assert any(warning_fragment in warning for warning in warnings)


def _parameter_definition(
    name: str,
    *,
    model_file: str = "Demand",
    model_sheet: str = "Input",
) -> ParameterDefinition:
    return ParameterDefinition(
        canonical_parameter_name=name,
        parameter_hint=f"{name} scenario adjustment",
        model_file=model_file,
        model_sheet=model_sheet,
        model_table="InputTable",
        parameter_name=name,
        semantic_axes="Country, Year, Month",
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
    *definitions: ParameterDefinition,
    mapping_rules: list[MappingRule] | None = None,
) -> ParameterKnowledgeBase:
    return ParameterKnowledgeBase(
        mapping_source="test:v4-lever-catalog-only",
        basecase_dir_path="",
        parameter_definitions={definition.canonical_parameter_name: definition for definition in definitions},
        mapping_rules=mapping_rules or [],
        basecase_profiles={},
    )


def _binding(
    parameter_name: str,
    *,
    role: str = "primary",
    selection_mode: str = "deterministic",
    applicability: str = "",
    support_status: str = "executable",
    unsupported_reason_code: str | None = None,
) -> dict[str, Any]:
    return {
        "parameter_name": parameter_name,
        "role": role,
        "selection_mode": selection_mode,
        "applicability": applicability,
        "support_status": support_status,
        "unsupported_reason_code": unsupported_reason_code,
    }


def _lever(
    impact_lever_id: int,
    lever_code: str,
    *,
    domain: str,
    bindings: list[dict[str, Any]],
) -> ModelImpactLeverPayload:
    return ModelImpactLeverPayload.model_validate(
        {
            "impact_lever_id": impact_lever_id,
            "lever_code": lever_code,
            "domain": domain,
            "label": lever_code.replace("_", " "),
            "description": f"{lever_code} test Lever",
            "applicability_hint": f"Apply {lever_code} only when grounded in event evidence.",
            "parameter_bindings": bindings,
            "catalog_version": CATALOG_VERSION,
        },
    )


def _catalog() -> list[ModelImpactLeverPayload]:
    return [
        _lever(
            101,
            "economic_activity",
            domain="demand",
            bindings=[
                _binding(
                    "GDP",
                    applicability="Default economic activity indicator.",
                ),
                _binding(
                    "Population",
                    role="alternative",
                    applicability="Only when population or migration is explicit.",
                ),
                _binding(
                    "CDD",
                    role="alternative",
                    support_status="known_unsupported",
                    unsupported_reason_code="INACTIVE_MODEL_PARAMETER",
                ),
            ],
        ),
        _lever(
            102,
            "direct_gas_demand",
            domain="demand",
            bindings=[_binding("User-Adjusted Gas Demand")],
        ),
        _lever(
            103,
            "shipping_cost",
            domain="trade",
            bindings=[_binding("ShippingCost")],
        ),
        _lever(
            104,
            "price_marker",
            domain="price_only",
            bindings=[],
        ),
        _lever(
            105,
            "unbound_supply",
            domain="supply",
            bindings=[],
        ),
    ]


def _lever_state(
    lever_code: str,
    impact_lever_id: int,
    *,
    direction: str,
    domain: str,
    bindings: list[dict[str, Any]],
    is_primary: bool = True,
) -> dict[str, Any]:
    return {
        "lever_code": lever_code,
        "impact_lever_id": impact_lever_id,
        "lever_label": lever_code.replace("_", " "),
        "lever_description": f"{lever_code} test Lever",
        "lever_domain": domain,
        "lever_applicability_hint": f"Use {lever_code} with evidence.",
        "direction": direction,
        "level": "high",
        "scope": "global",
        "time_window": "2027-2028",
        "is_primary_lever": is_primary,
        "parameter_bindings": bindings,
    }


def _lineage(
    dimension_key: str,
    lever_states: list[dict[str, Any]],
    *,
    value_id: str = "high",
    source_event_ids: list[int] | None = None,
    pressure_contribution: str = "상방 압력",
) -> dict[str, Any]:
    return {
        "scenario_dimension_key": dimension_key,
        "scenario_dimension_label": dimension_key.replace("_", " "),
        "scenario_dimension_description": "Lever-native test dimension",
        "scenario_dimension_rationale": "Derived from ordered Event evidence.",
        "scenario_dimension_value": value_id,
        "scenario_dimension_value_id": value_id,
        "scenario_dimension_value_label": value_id,
        "assumption_rationale": "Selected value rationale",
        "pressure_contribution": pressure_contribution,
        "source_event_ids": source_event_ids or [101],
        "source_impact_path_ids": [f"path-{dimension_key}"],
        "source_uncertainty_ids": [f"uncertainty-{dimension_key}"],
        "primary_lever_code": lever_states[0]["lever_code"],
        "primary_impact_lever_id": lever_states[0]["impact_lever_id"],
        "model_support_status": "supported",
        "lever_states": lever_states,
    }


def _matcher_context(*lineage: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario": {
            "scenario_id": 501,
            "scenario_group_id": 701,
            "dimension_values": {
                item["scenario_dimension_key"]: item["scenario_dimension_value_id"] for item in lineage
            },
        },
        "scenario_group": {
            "scenario_group_id": 701,
            "api_version": "v4",
            "generation_strategy": V4_STRATEGY,
        },
        "dimension_lineage": list(lineage),
    }


def _scenario(
    *,
    selected_value_id: str = "high",
    dimension_values: dict[str, str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_id=501,
        scenario_group_id=701,
        title="Lever-native scenario",
        narrative="Selected Lever states determine Model Parameter candidates.",
        status="created",
        dimension_values=dimension_values or {"economic_pressure": selected_value_id},
        probability_score=0.5,
        probability_delta=0.0,
        impact_jkm=None,
        impact_ttf=None,
        impact_hh=None,
        baseline_yn="N",
        global_pressure_band="bullish",
        scenario_role="ceiling",
        global_pressure_rationale="공급 감소가 가격 상방 압력을 만듭니다.",
        related_markets=[
            {"market": "JKM", "reason": "아시아 현물 조달 경쟁"},
        ],
    )


def _dimension_definition() -> dict[str, Any]:
    return {
        "dimension_id": "economic_pressure",
        "label": "Economic pressure",
        "description": "Economic and direct-demand pressure",
        "rationale": "Built from both ordered Events.",
        "source_event_ids": [101, 202],
        "source_impact_path_ids": ["path-economic"],
        "source_uncertainty_ids": ["uncertainty-economic"],
        "primary_lever_code": "economic_activity",
        "primary_impact_lever_id": 101,
        "model_support_status": "supported",
        "values": [
            {
                "value_id": "low",
                "label": "Low",
                "assumption_rationale": "Economic activity contracts.",
                "pressure_contribution": "하방 압력",
                "lever_states": [
                    {
                        "lever_code": "economic_activity",
                        "impact_lever_id": 101,
                        "direction": "decrease",
                        "level": "low",
                        "scope": "global",
                        "time_window": "2027",
                    },
                    {
                        "lever_code": "shipping_cost",
                        "impact_lever_id": 103,
                        "direction": "increase",
                        "level": "high",
                        "scope": "global",
                        "time_window": "2027",
                    },
                ],
            },
            {
                "value_id": "high",
                "label": "High",
                "assumption_rationale": "Economic activity and gas demand expand.",
                "pressure_contribution": "상방 압력",
                "lever_states": [
                    {
                        "lever_code": "economic_activity",
                        "impact_lever_id": 101,
                        "direction": "increase",
                        "level": "high",
                        "scope": "global",
                        "time_window": "2027-2028",
                    },
                    {
                        "lever_code": "direct_gas_demand",
                        "impact_lever_id": 102,
                        "direction": "increase",
                        "level": "medium",
                        "scope": "regional",
                        "time_window": "2027-2028",
                    },
                ],
            },
        ],
    }


def _group(
    definition: dict[str, Any],
    *,
    api_version: str = "v4",
    catalog_checksum: str = CATALOG_CHECKSUM,
) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_id=701,
        mi_event_id=None,
        event_type_l2_id=None,
        request_usr_id=41,
        title="Lever-native group",
        summary="Economic pressure",
        description="Two ordered Events with a Lever-native dimension.",
        dimension_selected=["economic_pressure"],
        scenario_count=1,
        status="created",
        stage="scenario_created",
        api_version=api_version,
        generation_strategy=V4_STRATEGY,
        parameter_mapping_ready=False,
        dimension_definitions=[definition],
        impact_catalog_version=CATALOG_VERSION,
        impact_catalog_checksum=catalog_checksum,
    )


def _load_context(
    *,
    definition: dict[str, Any] | None = None,
    selected_value_id: str = "high",
    api_version: str = "v4",
    catalog_checksum: str = CATALOG_CHECKSUM,
    definitions: list[dict[str, Any]] | None = None,
    dimension_values: dict[str, str] | None = None,
) -> dict[str, Any]:
    relations = [
        SimpleNamespace(mi_event_id=202, event_type_l2_id=12, display_order=2),
        SimpleNamespace(mi_event_id=101, event_type_l2_id=11, display_order=1),
    ]
    events = {
        101: {
            "mi_event_id": 101,
            "event_title_ko": "First Event",
            "one_line_summary": "First event summary",
            "key_bullets": ["first evidence"],
        },
        202: {
            "mi_event_id": 202,
            "event_title_ko": "Second Event",
            "one_line_summary": "Second event summary",
            "key_bullets": ["second evidence"],
        },
    }
    group = _group(
        definition or _dimension_definition(),
        api_version=api_version,
        catalog_checksum=catalog_checksum,
    )
    if definitions is not None:
        group.dimension_definitions = definitions
    return _load_v4_context(
        scenario=_scenario(
            selected_value_id=selected_value_id,
            dimension_values=dimension_values,
        ),
        group=group,
        group_repository=SimpleNamespace(
            fetch_group_events=Mock(return_value=relations),
        ),
        event_repository=SimpleNamespace(
            fetch_event_core_by_id=Mock(side_effect=events.get),
        ),
        impact_levers=_catalog(),
        catalog_version=CATALOG_VERSION,
        catalog_checksum=CATALOG_CHECKSUM,
    )


def test_v4_context_uses_only_selected_value_lever_states_and_ordered_events() -> None:
    context = _load_context(selected_value_id="high")

    assert [event["mi_event_id"] for event in context["events"]] == [101, 202]
    assert [event["event_type_l2_id"] for event in context["events"]] == [11, 12]
    assert context["event"] == {}
    assert context["event_type"] == {}
    assert context["dimension_value_mappings"] == []
    assert len(context["dimension_lineage"]) == 1
    lineage = context["dimension_lineage"][0]
    assert lineage["scenario_dimension_value_id"] == "high"
    assert [state["lever_code"] for state in lineage["lever_states"]] == [
        "economic_activity",
        "direct_gas_demand",
    ]
    assert [state["direction"] for state in lineage["lever_states"]] == [
        "increase",
        "increase",
    ]
    assert "shipping_cost" not in {state["lever_code"] for state in lineage["lever_states"]}
    assert [value["value_id"] for definition in context["dimension_template"] for value in definition["values"]] == [
        "high",
    ]
    assert context["executable_binding_occurrences"] == 3
    assert context["scenario"]["related_markets"] == [
        {"market": "JKM", "reason": "아시아 현물 조달 경쟁"},
    ]
    assert context["candidate_exclusion_reason_codes"] == [
        "INACTIVE_MODEL_PARAMETER",
    ]


def test_v4_event_brief_keeps_larger_detail_excerpt() -> None:
    context = _load_context(selected_value_id="high")
    context["events"] = [
        {
            "mi_event_id": 100 + index,
            "display_order": index,
            "event_title_ko": f"Event {index}",
            "one_line_summary": f"Summary {index}",
            "key_bullets": [f"bullet-{item}" for item in range(nodes.EVENT_KEY_BULLETS_MAX_ITEMS + 2)],
            "tags": [f"tag-{item}" for item in range(nodes.EVENT_TAGS_MAX_ITEMS + 2)],
            "numeric_facts_md": "\n".join(
                [
                    "| 중요도 | 지표 | 값 |",
                    "|---|---|---|",
                    *[
                        f"| {4 if item >= 24 else 1} | {'high' if item >= 24 else 'low'}-{item} | {item} Mt |"
                        for item in range(28)
                    ],
                ],
            ),
            "detail_analysis": str(index) * (nodes.V4_EVENT_DETAIL_MAX_CHARS + 1_000),
            "occurred_at": f"2026-10-0{index}T00:00:00",
            "oldest_record_first_created": f"2026-09-0{index}T00:00:00",
            "latest_record_first_created": f"2026-10-0{index}T01:00:00",
        }
        for index in range(1, 6)
    ]

    brief = _scenario_brief_for_value_prompt(context)

    assert [event["event_id"] for event in brief["events"]] == [101, 102, 103, 104, 105]
    assert all(len(event["detail_excerpt"]) == nodes.V4_EVENT_DETAIL_MAX_CHARS for event in brief["events"])
    assert all(len(event["key_bullets"]) == nodes.EVENT_KEY_BULLETS_MAX_ITEMS for event in brief["events"])
    assert all(len(event["tags"]) == nodes.EVENT_TAGS_MAX_ITEMS for event in brief["events"])
    assert all("high-24" in event["numeric_facts_md"] for event in brief["events"])
    assert all("high-27" in event["numeric_facts_md"] for event in brief["events"])
    assert all("low-20" not in event["numeric_facts_md"] for event in brief["events"])
    assert all("low-23" not in event["numeric_facts_md"] for event in brief["events"])
    assert brief["events"][0]["occurred_at"] == "2026-10-01T00:00:00"
    assert brief["events"][0]["evidence_window_start"] == "2026-09-01T00:00:00"
    assert brief["events"][0]["evidence_window_end"] == "2026-10-01T01:00:00"
    assert brief["scenario"]["baseline_yn"] == "N"
    assert brief["scenario"]["global_pressure_band"] == "bullish"
    assert brief["scenario"]["scenario_role"] == "ceiling"
    assert brief["scenario"]["global_pressure_rationale"] == ("공급 감소가 가격 상방 압력을 만듭니다.")
    assert brief["scenario"]["related_markets"] == [
        {"market": "JKM", "reason": "아시아 현물 조달 경쟁"},
    ]


def test_numeric_facts_plain_text_is_bounded_without_becoming_empty() -> None:
    compact = _compact_numeric_facts_md(
        "수" * (nodes.EVENT_NUMERIC_FACTS_MAX_CHARS + 1_000),
    )

    assert len(compact) == nodes.EVENT_NUMERIC_FACTS_MAX_CHARS


def test_v4_service_load_context_skips_legacy_mapping_repository_and_uses_active_catalog() -> None:
    session = SimpleNamespace(close=Mock())
    scenario = SimpleNamespace(scenario_id=501, scenario_group_id=701)
    group = SimpleNamespace(
        scenario_group_id=701,
        api_version="v4",
        generation_strategy=V4_STRATEGY,
        impact_catalog_version=CATALOG_VERSION,
    )
    parameter_definitions = [
        {
            "canonical_parameter_name": "GDP",
            "use_yn": "Y",
        },
    ]
    impact_levers = _catalog()
    loaded_context = {
        "scenario": {"scenario_id": 501},
        "scenario_group": {"scenario_group_id": 701},
    }

    with (
        patch(
            "apps.common.configs.database.sync_database.connection.get_sync_session",
            return_value=session,
        ),
        patch(
            "apps.agents.model_parameter_agent.persistence.model_parameter_service.ScenarioRepository",
        ) as scenario_repository_cls,
        patch(
            "apps.agents.model_parameter_agent.persistence.model_parameter_service.ScenarioGroupRepository",
        ) as group_repository_cls,
        patch(
            "apps.agents.model_parameter_agent.persistence.model_parameter_service.EventRepository",
        ) as event_repository_cls,
        patch(
            "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
        ) as model_parameter_repository_cls,
        patch(
            "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelImpactLeverService",
        ) as impact_lever_service_cls,
        patch(
            "apps.agents.model_parameter_agent.persistence.model_parameter_service._load_v4_context",
            return_value=loaded_context,
        ) as load_v4_context,
    ):
        scenario_repository_cls.return_value.fetch_model_by_id.return_value = scenario
        group_repository_cls.return_value.fetch_by_id.return_value = group
        model_parameter_repository = model_parameter_repository_cls.return_value
        model_parameter_repository.fetch_model_parameter_definitions.return_value = parameter_definitions
        impact_lever_service_cls.return_value.load_active_catalog.return_value = (
            impact_levers,
            CATALOG_VERSION,
            CATALOG_CHECKSUM,
        )

        context = ModelParameterService().load_context(501)

    model_parameter_repository.fetch_parameter_mapping_resources.assert_not_called()
    model_parameter_repository.fetch_model_parameter_definitions.assert_called_once_with()
    impact_lever_service_cls.assert_called_once_with(session=session)
    impact_lever_service_cls.return_value.load_active_catalog.assert_called_once_with(
        catalog_version=CATALOG_VERSION,
    )
    load_v4_context.assert_called_once_with(
        scenario=scenario,
        group=group,
        group_repository=group_repository_cls.return_value,
        event_repository=event_repository_cls.return_value,
        scenario_repository=scenario_repository_cls.return_value,
        impact_levers=impact_levers,
        catalog_version=CATALOG_VERSION,
        catalog_checksum=CATALOG_CHECKSUM,
    )
    assert context["parameter_mapping_resources"] == {
        "mapping_rules": [],
        "parameter_definitions": parameter_definitions,
    }
    session.close.assert_called_once_with()


def test_v4_multiple_deterministic_bindings_use_step15_routing_prompt() -> None:
    context = _load_context(selected_value_id="high")
    kb = _knowledge_base(
        _parameter_definition("GDP"),
        _parameter_definition("Population"),
        _parameter_definition("User-Adjusted Gas Demand"),
    )
    candidates, non_inputs, warnings = match_parameter_candidates(kb, context)
    deterministic, routing_tasks = _partition_candidate_validation_work(candidates)

    packet = _build_candidate_validation_prompt_packet(
        context,
        routing_tasks,
        non_inputs,
    )

    assert warnings == []
    assert [candidate["canonical_parameter_name"] for candidate in deterministic] == [
        "User-Adjusted Gas Demand",
    ]
    assert len(routing_tasks) == 1
    assert routing_tasks[0]["selection_mode"] == "deterministic"
    assert len(packet["routing_tasks"]) == 1


def test_v4_context_rejects_catalog_checksum_mismatch() -> None:
    with pytest.raises(MIBaseError) as caught:
        _load_context(catalog_checksum="stale-checksum")

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "catalog checksum mismatch" in caught.value.error_message
    assert "Regenerate the v4 Scenario" in caught.value.error_message


def test_v4_context_rejects_non_v4_api_version() -> None:
    with pytest.raises(MIBaseError) as caught:
        _load_context(api_version="v3")

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "requires api_version=v4" in caught.value.error_message


def test_v4_context_rejects_lever_code_id_mismatch() -> None:
    definition = deepcopy(_dimension_definition())
    definition["values"][1]["lever_states"][0]["impact_lever_id"] = 999

    with pytest.raises(MIBaseError) as caught:
        _load_context(definition=definition)

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "Lever code/ID mismatch" in caught.value.error_message


def test_v4_context_rejects_duplicate_selected_value_lever_code() -> None:
    definition = deepcopy(_dimension_definition())
    duplicate_state = deepcopy(definition["values"][1]["lever_states"][0])
    definition["values"][1]["lever_states"].append(duplicate_state)

    with pytest.raises(MIBaseError) as caught:
        _load_context(definition=definition)

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "duplicate leverCode" in caught.value.error_message
    assert "dimension=economic_pressure" in caught.value.error_message
    assert "value=high" in caught.value.error_message
    assert "leverCode=economic_activity" in caught.value.error_message


def test_v4_context_rejects_primary_lever_missing_from_selected_value() -> None:
    definition = deepcopy(_dimension_definition())
    definition["values"][1]["lever_states"] = [
        definition["values"][1]["lever_states"][1],
    ]

    with pytest.raises(MIBaseError) as caught:
        _load_context(definition=definition)

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "omits its primary Lever" in caught.value.error_message


def test_v4_context_rejects_partial_dimension_selection() -> None:
    first_definition = _dimension_definition()
    second_definition = deepcopy(first_definition)
    second_definition["dimension_id"] = "shipping_pressure"

    with pytest.raises(MIBaseError) as caught:
        _load_context(
            definitions=[first_definition, second_definition],
            dimension_values={"economic_pressure": "high"},
        )

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "select exactly one value for every group Dimension" in caught.value.error_message
    assert "shipping_pressure" in caught.value.error_message


def test_v4_context_rejects_source_event_outside_group() -> None:
    definition = deepcopy(_dimension_definition())
    definition["source_event_ids"] = [101, 999]

    with pytest.raises(MIBaseError) as caught:
        _load_context(definition=definition)

    assert caught.value.error_code is ErrorCode.INVALID_REQUEST
    assert "not members of the scenario group" in caught.value.error_message


def test_v4_matcher_ignores_legacy_dimension_mapping_rules() -> None:
    economic_state = _lever_state(
        "economic_activity",
        101,
        direction="increase",
        domain="demand",
        bindings=[_binding("GDP")],
    )
    legacy_rule = MappingRule(
        event_type_l2_id=999,
        dimension_key="economic_pressure",
        dimension_label="Legacy dimension",
        canonical_parameter_name="LegacyParameter",
        mapping_method="direct",
        comment="This rule must never participate in v4 matching.",
    )
    kb = _knowledge_base(
        _parameter_definition("GDP"),
        _parameter_definition("LegacyParameter"),
        mapping_rules=[legacy_rule],
    )
    context = _matcher_context(
        _lineage("economic_pressure", [economic_state]),
    )
    context["scenario_group"]["event_type_l2_id"] = 999

    candidates, non_inputs, warnings = match_parameter_candidates(kb, context)

    assert [candidate["canonical_parameter_name"] for candidate in candidates] == [
        "GDP",
    ]
    assert non_inputs == []
    assert warnings == []
    assert all(candidate["mapping_strategy"] == "v4" for candidate in candidates)


def test_v4_matcher_classifies_executable_unsupported_and_non_changing_levers() -> None:
    economic_state = _lever_state(
        "economic_activity",
        101,
        direction="increase",
        domain="demand",
        bindings=[
            _binding("GDP"),
            _binding(
                "CDD",
                role="alternative",
                support_status="known_unsupported",
                unsupported_reason_code="INACTIVE_MODEL_PARAMETER",
            ),
        ],
    )
    unchanged_state = _lever_state(
        "direct_gas_demand",
        102,
        direction="unchanged",
        domain="demand",
        bindings=[_binding("User-Adjusted Gas Demand")],
        is_primary=False,
    )
    price_only_state = _lever_state(
        "price_marker",
        104,
        direction="increase",
        domain="price_only",
        bindings=[],
        is_primary=False,
    )
    unbound_state = _lever_state(
        "unbound_supply",
        105,
        direction="disrupt",
        domain="supply",
        bindings=[],
        is_primary=False,
    )
    context = _matcher_context(
        _lineage(
            "mixed_support",
            [economic_state, unchanged_state, price_only_state, unbound_state],
        ),
    )
    kb = _knowledge_base(_parameter_definition("GDP"))

    candidates, non_inputs, warnings = match_parameter_candidates(kb, context)

    assert [candidate["canonical_parameter_name"] for candidate in candidates] == [
        "GDP",
    ]
    assert {item["reason_code"] for item in non_inputs} == {
        "INACTIVE_MODEL_PARAMETER",
        "UNCHANGED_LEVER_STATE",
        "PRICE_ONLY",
        "NO_PARAMETER_BINDING",
    }
    unchanged = next(item for item in non_inputs if item["reason_code"] == "UNCHANGED_LEVER_STATE")
    assert unchanged["mapping_method"] == "indirect"
    assert unchanged["direction"] == "unchanged"
    assert warnings == []


def test_v4_unchanged_only_lineage_has_no_change_candidate() -> None:
    unchanged_state = _lever_state(
        "economic_activity",
        101,
        direction="unchanged",
        domain="demand",
        bindings=[_binding("GDP")],
    )
    context = _matcher_context(
        _lineage("economic_pressure", [unchanged_state]),
    )

    candidates, non_inputs, warnings = match_parameter_candidates(
        _knowledge_base(_parameter_definition("GDP")),
        context,
    )

    assert candidates == []
    assert [item["reason_code"] for item in non_inputs] == [
        "UNCHANGED_LEVER_STATE",
    ]
    assert "UNCHANGED_LEVER_STATE" in warnings[0]


def test_v4_primary_and_alternative_bindings_form_one_deterministic_routing_task() -> None:
    economic_state = _lever_state(
        "economic_activity",
        101,
        direction="increase",
        domain="demand",
        bindings=[
            _binding(
                "GDP",
                applicability="Default economic activity indicator.",
            ),
            _binding(
                "Population",
                role="alternative",
                applicability="Only when population or migration is explicit.",
            ),
        ],
    )
    kb = _knowledge_base(
        _parameter_definition("GDP"),
        _parameter_definition("Population"),
    )

    candidates, non_inputs, warnings = match_parameter_candidates(
        kb,
        _matcher_context(_lineage("economic_pressure", [economic_state])),
    )
    deterministic, routing_tasks = _partition_candidate_validation_work(
        candidates,
    )

    assert deterministic == []
    assert non_inputs == []
    assert warnings == []
    assert {(candidate["canonical_parameter_name"], candidate["binding_role"]) for candidate in candidates} == {
        ("GDP", "primary"),
        ("Population", "alternative"),
    }
    assert all(candidate["mapping_method"] == "routing" for candidate in candidates)
    assert len(routing_tasks) == 1
    assert routing_tasks[0]["selection_mode"] == "deterministic"
    assert routing_tasks[0]["candidates"] == candidates


def test_v4_deterministic_routing_task_preserves_each_binding_lineage() -> None:
    economic_state = _lever_state(
        "economic_activity",
        101,
        direction="increase",
        domain="demand",
        bindings=[
            _binding("GDP", applicability="Default economic activity indicator."),
            _binding(
                "Population",
                role="alternative",
                applicability="Only when population or migration is explicit.",
            ),
        ],
    )
    candidates, _, _ = match_parameter_candidates(
        _knowledge_base(
            _parameter_definition("GDP"),
            _parameter_definition("Population"),
        ),
        _matcher_context(_lineage("economic_pressure", [economic_state])),
    )
    deterministic, routing_tasks = _partition_candidate_validation_work(candidates)

    assert deterministic == []
    assert len(routing_tasks) == 1
    assert {(item["canonical_parameter_name"], item["binding_role"]) for item in routing_tasks[0]["candidates"]} == {
        ("GDP", "primary"),
        ("Population", "alternative"),
    }
    assert all(
        item["lever_code"] == "economic_activity"
        for item in routing_tasks[0]["candidates"]
    )


def test_v4_single_conditional_price_only_binding_routes_without_default() -> None:
    state = _lever_state(
        "inventory_condition",
        110,
        direction="decrease",
        domain="price_only",
        bindings=[
            _binding(
                "SupplyDisruption",
                role="alternative",
                selection_mode="conditional",
                applicability="Country/Year/Month upstream supply cause is explicit.",
            ),
        ],
    )
    candidates, non_inputs, warnings = match_parameter_candidates(
        _knowledge_base(_parameter_definition("SupplyDisruption")),
        _matcher_context(_lineage("inventory_path", [state])),
    )
    deterministic, routing_tasks = _partition_candidate_validation_work(candidates)

    assert non_inputs == []
    assert warnings == []
    assert deterministic == []
    assert len(routing_tasks) == 1
    assert routing_tasks[0]["selection_mode"] == "conditional"
    assert candidates[0]["binding_selection_mode"] == "conditional"


def test_v4_routing_prompt_deduplicates_large_binding_provenance() -> None:
    repeated_provenance = [{"evidence": "x" * 8_000}]
    candidate = {
        "candidate_key": "inventory-supply",
        "mapping_strategy": "v4",
        "canonical_parameter_name": "SupplyDisruption",
        "parameter_hint": "country/year/month upstream supply",
        "semantic_axes": ["Country", "Year", "Month"],
        "binding_role": "alternative",
        "binding_selection_mode": "conditional",
        "binding_applicability": "Explicit upstream supply cause only.",
        "source_refs": repeated_provenance,
        "approved_source_projections": repeated_provenance,
        "binding_provenance": repeated_provenance,
        "lever_provenance": repeated_provenance,
    }

    payload = _routing_candidate_prompt_payload(candidate)

    assert payload["candidate_key"] == "inventory-supply"
    assert payload["binding_applicability"] == "Explicit upstream supply cause only."
    assert "source_refs" not in payload
    assert "approved_source_projections" not in payload
    assert "binding_provenance" not in payload
    assert "lever_provenance" not in payload


def test_v4_routing_prompt_keeps_shared_evidence_once_per_lever_task() -> None:
    repeated_source = {"evidence": "x" * 8_000}
    candidates = [
        {
            "candidate_key": f"inventory-{index}",
            "mapping_strategy": "v4",
            "canonical_parameter_name": parameter_name,
            "binding_selection_mode": "conditional",
            "binding_applicability": f"Applicability {index}",
            "source_refs": [repeated_source],
            "approved_source_projections": [repeated_source],
            "lever_provenance": [repeated_source],
            "source_dimensions": [{"source_dimension_id": "d1"}],
        }
        for index, parameter_name in enumerate(
            ["GDP", "PMI", "PowerMix", "SupplyDisruption"],
            start=1,
        )
    ]
    task = {
        "is_v4": True,
        "selection_mode": "conditional",
        "dimension_key": "v4|d1|d1v3|inventory_condition",
        "lever_code": "inventory_condition",
        "candidates": candidates,
    }

    payload = _routing_task_for_prompt(task)

    assert payload["lever_context"]["source_refs"] == [repeated_source]
    assert all("source_refs" not in candidate for candidate in payload["candidates"])
    assert str(payload).count("x" * 8_000) == 3


def test_v4_same_parameter_merges_all_event_dimension_and_lever_provenance() -> None:
    shipping_binding = [_binding("ShippingCost")]
    shipping_state = _lever_state(
        "shipping_cost",
        103,
        direction="increase",
        domain="trade",
        bindings=shipping_binding,
    )
    route_state = _lever_state(
        "route_disruption",
        106,
        direction="disrupt",
        domain="trade",
        bindings=shipping_binding,
    )
    context = _matcher_context(
        _lineage(
            "shipping_pressure",
            [shipping_state],
            source_event_ids=[101],
        ),
        _lineage(
            "route_pressure",
            [route_state],
            source_event_ids=[202],
            pressure_contribution="하방 압력",
        ),
    )
    kb = _knowledge_base(
        _parameter_definition(
            "ShippingCost",
            model_file="Trade",
            model_sheet="ShippingInput",
        ),
    )

    source_candidates, non_inputs, warnings = match_parameter_candidates(
        kb,
        context,
    )
    merged, merge_warnings = _merge_candidates_by_parameter(source_candidates)
    reverse_merged, _ = _merge_candidates_by_parameter(
        list(reversed(source_candidates)),
    )

    assert len(source_candidates) == 2
    assert non_inputs == []
    assert warnings == []
    assert merge_warnings == []
    assert len(merged) == 1
    assert merged[0]["candidate_key"] == ("parameter|v4|trade|shippinginput|shippingcost")
    assert reverse_merged[0]["candidate_key"] == merged[0]["candidate_key"]
    assert set(merged[0]["source_event_ids"]) == {101, 202}
    assert {item["scenario_dimension_key"] for item in merged[0]["source_dimensions"]} == {
        "shipping_pressure",
        "route_pressure",
    }
    assert {(item["lever_code"], item["direction"]) for item in merged[0]["lever_provenance"]} == {
        ("shipping_cost", "increase"),
        ("route_disruption", "disrupt"),
    }
    assert {item["lever_code"] for item in merged[0]["binding_provenance"]} == {"shipping_cost", "route_disruption"}
    assert set(merged[0]["source_impact_path_ids"]) == {
        "path-shipping_pressure",
        "path-route_pressure",
    }


def test_v4_opposing_lever_directions_survive_merge_and_reach_step3_prompt() -> None:
    shipping_binding = [_binding("ShippingCost")]
    increasing_state = _lever_state(
        "shipping_cost",
        103,
        direction="increase",
        domain="trade",
        bindings=shipping_binding,
    )
    decreasing_state = _lever_state(
        "route_disruption",
        106,
        direction="decrease",
        domain="trade",
        bindings=shipping_binding,
    )
    context = _matcher_context(
        _lineage(
            "shipping_pressure",
            [increasing_state],
            source_event_ids=[101],
        ),
        _lineage(
            "route_pressure",
            [decreasing_state],
            source_event_ids=[202],
            pressure_contribution="하방 압력",
        ),
    )
    source_candidates, _, _ = match_parameter_candidates(
        _knowledge_base(
            _parameter_definition(
                "ShippingCost",
                model_file="Trade",
                model_sheet="ShippingInput",
            ),
        ),
        context,
    )
    merged, warnings = _merge_candidates_by_parameter(source_candidates)
    candidate = merged[0]
    candidate_key = str(candidate["candidate_key"])
    coordinates = {"Route": "Suez", "Year": 2027}

    packet = _build_value_proposal_prompt_packet(
        context,
        merged,
        [
            {
                "candidate_key": candidate_key,
                "slot_axes": [
                    {"axis_name": axis_name, "axis_value": axis_value} for axis_name, axis_value in coordinates.items()
                ],
            },
        ],
        [
            {
                "candidate_key": candidate_key,
                "reference_id": "shipping-reference-1",
                "axes": coordinates,
                "value": 1.0,
            },
        ],
        [],
    )

    assert warnings == []
    assert len(packet["parameter_value_tasks"]) == 1
    parameter_payload = packet["parameter_value_tasks"][0]["parameter"]
    assert {(item["lever_code"], item["direction"]) for item in candidate["lever_provenance"]} == {
        ("shipping_cost", "increase"),
        ("route_disruption", "decrease"),
    }
    assert parameter_payload["lever_provenance"] == candidate["lever_provenance"]
    assert parameter_payload["binding_provenance"] == candidate["binding_provenance"]


def test_v4_lever_direction_is_provenance_not_a_numeric_sign() -> None:
    kb = _knowledge_base(_parameter_definition("SupplyDisruption"))

    def candidate_for(direction: str) -> dict[str, Any]:
        state = _lever_state(
            "supply_disruption",
            107,
            direction=direction,
            domain="supply",
            bindings=[_binding("SupplyDisruption")],
        )
        candidates, _, _ = match_parameter_candidates(
            kb,
            _matcher_context(
                _lineage(
                    "supply_pressure",
                    [state],
                    pressure_contribution="상방 압력",
                ),
            ),
        )
        return candidates[0]

    increasing = candidate_for("increase")
    decreasing = candidate_for("decrease")

    assert increasing["candidate_key"] == decreasing["candidate_key"]
    assert increasing["canonical_parameter_name"] == decreasing["canonical_parameter_name"]
    assert increasing["mapping_method"] == decreasing["mapping_method"] == "direct"
    assert increasing["direction"] == "increase"
    assert decreasing["direction"] == "decrease"
    assert increasing["pressure_contribution"] == decreasing["pressure_contribution"]
    for candidate in (increasing, decreasing):
        assert "sign" not in candidate
        assert "numeric_sign" not in candidate
        assert "adjustment_sign" not in candidate


def test_v4_callback_defers_missing_model_target_until_background() -> None:
    state = _lever_state(
        "economic_activity",
        101,
        direction="increase",
        domain="demand",
        bindings=[_binding("GDP")],
    )
    scenario_context = _matcher_context(
        _lineage("economic_pressure", [state]),
    )
    scenario_context["executable_binding_occurrences"] = 1
    scenario_context["parameter_mapping_resources"] = {
        "mapping_rules": [],
        "parameter_definitions": [
            {
                "canonical_parameter_name": "GDP",
                "parameter_name": "GDP",
                "model_file": "",
                "model_sheet": "",
            },
        ],
    }

    with patch(
        "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
    ) as service_cls:
        service_cls.return_value.load_context.return_value = scenario_context
        service_cls.return_value.create_processing_proposal.return_value = 901

        result = prepare_propose_parameters_callback(501)

    assert result["model_param_proposal_id"] == 901
    service_cls.return_value.create_processing_proposal.assert_called_once_with(
        scenario_context=scenario_context,
        user_id=None,
    )


def test_v4_proposal_persistence_and_presentation_keep_event_id_null() -> None:
    scenario_context = {
        "scenario": {
            "scenario_id": 501,
            "scenario_group_id": 701,
        },
        "scenario_group": {
            "scenario_group_id": 701,
            "mi_event_id": 101,
            "api_version": "v4",
            "generation_strategy": V4_STRATEGY,
        },
        "event": {"mi_event_id": 101},
    }

    assert (
        _proposal_event_id(
            scenario_group=scenario_context["scenario_group"],
            event=scenario_context["event"],
        )
        is None
    )
    assert _context_ids(scenario_context, 999) == (501, 701, None)


def test_v4_parameter_uses_unchanged_public_confirmation_schema_and_flow() -> None:
    payload = {
        "model_param_proposal_id": 901,
        "userId": 55,
        "data": {
            "confirmationParameters": [
                {
                    "parameterName": "ShippingCost",
                    "modelTarget": {
                        "modelFile": "Trade",
                        "modelSheet": "ShippingInput",
                        "tableName": "ShippingCost",
                        "valueFieldNames": ["ShippingCost"],
                        "slotAxesFieldNames": ["Route", "Year"],
                    },
                    "rationale": "상충 Lever 근거를 검토해 사용자가 확정",
                    "values": [
                        {
                            "Route": "Suez",
                            "Year": 2027,
                            "basecaseValue": 1.0,
                            "proposedValue": 1.1,
                            "rationale": "기존 공개 payload 구조로 확정",
                        },
                    ],
                },
            ],
        },
    }
    state = confirmation_to_state(payload)

    with patch(
        "apps.agents.model_parameter_agent.flows.confirm_parameters.nodes.ModelParameterService",
    ) as service_cls:
        service = service_cls.return_value
        service.load_model_parameter_definitions.return_value = []
        service.confirm_proposal_result.return_value = {
            "model_param_proposal_id": 901,
            "status": "CONFIRMED",
        }

        result = confirm_parameters(state)

    service.confirm_proposal_result.assert_called_once_with(
        model_param_proposal_id=901,
        user_id=55,
        confirmation_parameters=state.confirmation_parameters,
    )
    output = confirmation_to_output(result).model_dump(mode="json", by_alias=True)
    assert output == {
        "status": "success",
        "message": "model parameter proposal confirmed",
        "data": {
            "modelParamProposalId": 901,
            "status": "CONFIRMED",
        },
    }
