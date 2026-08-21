from __future__ import annotations

import asyncio
import json
from pathlib import Path

# ruff: noqa: S101
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from openai import pydantic_function_tool
from openpyxl import Workbook
from pydantic import ValidationError
import pytest

from apps.agents.scenario_group_agent.api import router as agent_router
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import (
    flow as multi_event_flow,
    nodes as multi_event_nodes,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    EventInteraction,
    V2DimensionDesignResult,
    V2MultiEventGenerationResult,
    V2ScenarioSynthesisResult,
    V3AnalysisDesignResult,
    V3CompositeDimensionDraft,
    V3DimensionDefinition,
    V3DimensionDesignResult,
    V3DimensionSourceMapping,
    V3DimensionValueDraft,
    V3MultiEventGenerationResult,
    V3ScenarioSynthesisResult,
    V3TemplateDimensionSelectionDraft,
    V3TemplateValueAnchor,
    finalize_generation_result as _finalize_generation_result,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import (
    MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.flows.create_signposts.nodes import (
    _load_group_event_context,
    sync_scenarios_from_table,
)
from apps.agents.scenario_group_agent.flows.create_signposts.state import (
    CreateSignpostsState,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    create_mapping_proposals,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.state import (
    ValidateScenariosState,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.agents.scenario_group_agent.prompts.multi_event_scenario_generation import (
    build_dimension_design_user_prompt,
    build_multi_event_user_prompt,
    build_scenario_synthesis_user_prompt,
    build_v3_analysis_design_user_prompt,
    build_v3_dimension_design_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    MULTI_EVENT_COMPAT_SYSTEM_PROMPT,
    CompatibilityItem,
)
from apps.agents.scenario_group_agent.routers.scenario_generation import router
from apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes import (
    _has_only_unusable_enum_recommendations,
    build_context,
)
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.event.schema import EventPayload
from apps.agents.scenario_group_agent.persistence.model_impact_lever_service import (
    ModelImpactLeverService,
)
from apps.persistence.scenario.schema import (
    ScenarioPayload,
    ScenarioPipelineTemplate,
    SourceLineage,
)
from apps.persistence.scenario_group.schema import ScenarioGroupPayload
from scripts.scenario_generation.import_template_domain_knowledge import (
    load_template_updates,
)


EVENT_IDS = [101, 202]


def _revisioned_sources(
    source_dimensions_by_event: dict[int, dict[str, object]],
) -> dict[int, dict[str, dict[str, object]]]:
    normalized: dict[int, dict[str, dict[str, object]]] = {}
    for event_id, source_dimensions in source_dimensions_by_event.items():
        event_type_l2_id = 8 if event_id == 101 else 12
        template_id = 81 if event_id == 101 else 121
        template_checksum = "checksum-8" if event_id == 101 else "checksum-12"
        normalized[event_id] = {}
        for dim_key, raw_definition in source_dimensions.items():
            definition = (
                dict(raw_definition) if isinstance(raw_definition, dict) else {"required": bool(raw_definition)}
            )
            normalized[event_id][dim_key] = {
                "required": False,
                "label": dim_key,
                "description": f"{dim_key} 설명",
                "event_type_l2_id": event_type_l2_id,
                "scenario_dimension_template_id": template_id,
                "template_checksum": template_checksum,
                "value_enums": ["낮음", "높음"],
                **definition,
            }
    return normalized


def finalize_generation_result(*args: object, **kwargs: object) -> object:
    strategy = kwargs.get("generation_strategy")
    result = args[0] if args else kwargs.get("result")
    source_dimensions = kwargs.get("source_dimensions_by_event")
    if (
        strategy == "multi_event_source_dimensions"
        and isinstance(result, V2MultiEventGenerationResult)
        and not isinstance(source_dimensions, dict)
    ):
        source_dimensions = {
            event_id: {
                selected.source_ref.dim_key: False
                for selected in result.selected_dimensions
                if selected.source_ref.event_id == event_id
            }
            for event_id in EVENT_IDS
        }
        kwargs["source_dimensions_by_event"] = source_dimensions
    if isinstance(source_dimensions, dict):
        revisioned = _revisioned_sources(
            source_dimensions,
        )
        kwargs["source_dimensions_by_event"] = revisioned
    return _finalize_generation_result(*args, **kwargs)


def _source(event_id: int, dim_key: str, value: str | None = None) -> dict[str, object]:
    return {
        "eventId": event_id,
        "eventTypeL2Id": 8 if event_id == 101 else 12,
        "scenarioDimensionTemplateId": 81 if event_id == 101 else 121,
        "templateChecksum": "checksum-8" if event_id == 101 else "checksum-12",
        "dimKey": dim_key,
        "value": value,
        "sourceType": "event_fact",
        "assumptionYn": "N",
        "rationale": "현재 Event 사실을 해당 source dimension에 투영한다.",
    }


def _dimension(
    *,
    dimension_id: str,
    event_id: int,
    dim_key: str,
    display_order: int,
    source_event_ids: list[int] | None = None,
) -> dict[str, object]:
    del display_order, source_event_ids
    return {
        "dimensionId": dimension_id,
        "sourceRef": {
            "eventId": event_id,
            "scenarioDimensionTemplateId": 81 if event_id == 101 else 121,
            "dimKey": dim_key,
        },
        "selectionCriterion": "both",
        "selectionRationale": "Event 사실과 LNG 영향 경로에 모두 연결된다.",
        "values": [
            {
                "valueId": value_id,
                "label": label,
                "pressureContribution": contribution,
            }
            for value_id, label, contribution in (
                ("low", "Event별 완화", "bearish"),
                ("mid", "Event 사실 기반 균형", "balanced"),
                ("high", "Event별 심화", "bullish"),
            )
        ],
    }


def _compact_dimension(
    *,
    dimension_id: str,
    source_event_ids: list[int],
    source_refs: list[tuple[int, str]],
) -> dict[str, object]:
    return {
        "dimensionId": dimension_id,
        "label": dimension_id,
        "description": f"{dimension_id} 설명",
        "rationale": "관련 Event 사실이 LNG 가격의 상승 또는 하락 압력을 바꿀 수 있다.",
        "sourceEventIds": source_event_ids,
        "sourceRefs": [
            {
                "scenarioDimensionTemplateId": template_id,
                "dimKey": dim_key,
            }
            for template_id, dim_key in source_refs
        ],
        "values": [
            {
                "valueId": value_id,
                "label": label,
                "pressureContribution": contribution,
                "description": f"{label} 상태가 구체적으로 전개된다.",
                "derivationRationale": "원본 Template enum 의미를 Event 맥락에 맞게 결합했다.",
            }
            for value_id, label, contribution in (
                ("low", "Event별 완화", "bearish"),
                ("mid", "Event 사실 기반 균형", "balanced"),
                ("high", "Event별 심화", "bullish"),
            )
        ],
    }


def _result(
    *,
    strategy: str,
) -> V2MultiEventGenerationResult | V3MultiEventGenerationResult:
    if strategy == "multi_event_source_dimensions":
        dimensions = [
            _dimension(
                dimension_id="e101__heat",
                event_id=101,
                dim_key="heat",
                display_order=1,
            ),
            _dimension(
                dimension_id="e101__duration",
                event_id=101,
                dim_key="duration",
                display_order=2,
            ),
            _dimension(
                dimension_id="e202__inventory",
                event_id=202,
                dim_key="inventory",
                display_order=3,
            ),
            _dimension(
                dimension_id="e202__recovery",
                event_id=202,
                dim_key="recovery",
                display_order=4,
            ),
            _dimension(
                dimension_id="e202__competition",
                event_id=202,
                dim_key="competition",
                display_order=5,
            ),
        ]
    else:
        dimensions = [
            _compact_dimension(
                dimension_id="demand_inventory_tightness",
                source_event_ids=[101, 202],
                source_refs=[(81, "tightness"), (121, "tightness")],
            ),
            _compact_dimension(
                dimension_id="heat_duration",
                source_event_ids=[101],
                source_refs=[(81, "duration")],
            ),
            _compact_dimension(
                dimension_id="inventory_recovery",
                source_event_ids=[202],
                source_refs=[(121, "recovery")],
            ),
            _compact_dimension(
                dimension_id="regional_competition",
                source_event_ids=[202],
                source_refs=[(121, "competition")],
            ),
        ]
    dimension_ids = [str(dimension["dimensionId"]) for dimension in dimensions]
    result_schema = (
        V2MultiEventGenerationResult if strategy == "multi_event_source_dimensions" else V3MultiEventGenerationResult
    )
    payload: dict[str, object] = {
        "scenarioGroupTitle": "복수 Event 시나리오",
        "scenarioGroupDescription": "두 Event를 공동 전제로 비교한다.",
        "eventShocks": [
            {
                "eventId": event_id,
                "shockSummary": "확인된 수급 충격이 JKM 가격 압력을 변화시킬 수 있다.",
            }
            for event_id in EVENT_IDS
        ],
        "scenarios": [
            {
                "title": "상단",
                "narrative": "공동 전제의 상승 압력이 심화된다.",
                "dimensionValues": {key: "high" for key in dimension_ids},
                "pressureBand": "strong_bullish",
                "probabilityScore": 20,
                "pressureRationale": "공급·수요 압력이 가격을 높인다.",
            },
            {
                "title": "혼합",
                "narrative": "상승과 완화 요인이 함께 작용한다.",
                "dimensionValues": {
                    key: "high" if index == 0 else ("low" if index == 1 else "mid")
                    for index, key in enumerate(dimension_ids)
                },
                "pressureBand": "balanced",
                "probabilityScore": 60,
                "pressureRationale": "상승과 하락 요인이 상쇄된다.",
                **({"mixedFactors": True} if strategy == "multi_event_composite_dimensions" else {}),
            },
            {
                "title": "하단",
                "narrative": "완화와 대체 공급이 가격 압력을 낮춘다.",
                "dimensionValues": {key: "low" for key in dimension_ids},
                "pressureBand": "strong_bearish",
                "probabilityScore": 20,
                "pressureRationale": "완화 경로가 우세하다.",
            },
        ],
    }
    if strategy == "multi_event_source_dimensions":
        payload["selectedDimensions"] = dimensions
    else:
        payload.update(
            {
                "interactions": [
                    {
                        "eventIds": EVENT_IDS,
                        "relation": "regional_coupling",
                        "rationale": "수요와 재고가 지역 구매 경쟁으로 연결된다.",
                    },
                ],
                "dimensionDefinitions": dimensions,
                "excludedCandidates": [
                    {
                        "pressureBand": "bullish",
                        "reasonCode": "NOT_INDEPENDENT",
                        "reason": "상단 후보와 독립적인 검토 가치가 부족하다.",
                    },
                    {
                        "pressureBand": "bearish",
                        "reasonCode": "LOW_PROBABILITY",
                        "reason": "Event 사실을 유지한 현실적 조합의 가능성이 낮다.",
                    },
                ],
            },
        )
    return result_schema.model_validate(payload)


def _v3_analysis_result() -> V3AnalysisDesignResult:
    aggregate = _result(strategy="multi_event_composite_dimensions")
    selections = [
        (101, 81, "tightness"),
        (101, 81, "duration"),
        (101, 81, "intensity"),
        (202, 121, "tightness"),
        (202, 121, "recovery"),
        (202, 121, "competition"),
    ]
    return V3AnalysisDesignResult(
        event_shocks=aggregate.event_shocks,
        interactions=aggregate.interactions,
        template_dimension_selections=[
            V3TemplateDimensionSelectionDraft(
                event_id=event_id,
                scenario_dimension_template_id=template_id,
                dim_key=dim_key,
                relevance_type="direct_event_fact",
                observed_basis=f"Event {event_id}에서 {dim_key} 관련 사실이 관측됐다.",
                selection_rationale="현재 Event 사실과 LNG 가격 영향 경로에 직접 연결된다.",
            )
            for event_id, template_id, dim_key in selections
        ],
    )


def _v3_dimension_design_result() -> V3DimensionDesignResult:
    aggregate = _result(strategy="multi_event_composite_dimensions")
    event_for_ref = {(81, "tightness"): 101, (121, "tightness"): 202}
    enum_by_value = {"low": "낮음", "mid": "중간", "high": "높음"}
    dimensions: list[V3CompositeDimensionDraft] = []
    for public_dimension in aggregate.dimension_definitions:
        mappings = [
            V3DimensionSourceMapping(
                event_id=event_for_ref.get(
                    (source.scenario_dimension_template_id, source.dim_key),
                    public_dimension.source_event_ids[0],
                ),
                scenario_dimension_template_id=source.scenario_dimension_template_id,
                dim_key=source.dim_key,
                composition_rationale="선택 후보가 합성 축의 상태를 구체화한다.",
            )
            for source in public_dimension.source_refs
        ]
        dimensions.append(
            V3CompositeDimensionDraft(
                dimension_id=public_dimension.dimension_id,
                label=public_dimension.label,
                description=public_dimension.description,
                rationale=public_dimension.rationale,
                source_mappings=mappings,
                values=[
                    V3DimensionValueDraft(
                        value_id=value.value_id,
                        label=value.label,
                        description=value.description or "구체적 상태 설명",
                        derivation_rationale=value.derivation_rationale or "enum 의미 결합 근거",
                        pressure_contribution=value.pressure_contribution,
                        template_value_anchors=[
                            V3TemplateValueAnchor(
                                event_id=mapping.event_id,
                                scenario_dimension_template_id=mapping.scenario_dimension_template_id,
                                dim_key=mapping.dim_key,
                                template_value=enum_by_value[value.value_id],
                            )
                            for mapping in mappings
                        ],
                    )
                    for value in public_dimension.values
                ],
            ),
        )
    return V3DimensionDesignResult(dimension_definitions=dimensions)


def _v3_generation_state() -> MultiEventGenerationState:
    template_dimensions = {
        81: ["tightness", "duration", "intensity"],
        121: ["tightness", "recovery", "competition"],
    }
    return MultiEventGenerationState(
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            api_version="v3",
            generation_strategy="multi_event_composite_dimensions",
        ),
        events=[
            EventPayload(mi_event_id=101, event_type_l2_id=8),
            EventPayload(mi_event_id=202, event_type_l2_id=12),
        ],
        templates=[
            ScenarioPipelineTemplate(
                scenario_dimension_template_id=template_id,
                event_type_l2_id=event_type_id,
                template_checksum=f"checksum-{event_type_id}",
                dimensions=[
                    {
                        "dim_key": dim_key,
                        "label": f"{dim_key} 원본 라벨",
                        "description": f"{dim_key} 원본 설명",
                        "required": index == 0,
                        "value_enums": ["낮음", "중간", "높음"],
                    }
                    for index, dim_key in enumerate(template_dimensions[template_id])
                ],
            )
            for template_id, event_type_id in ((81, 8), (121, 12))
        ],
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        user_id=7,
    )


def test_multi_event_request_requires_one_to_five_unique_events() -> None:
    valid = MultiEventCreateScenariosIn.model_validate(
        {
            "miEventIds": [1],
            "userId": 10,
        },
    )
    assert valid.mi_event_ids == [1]

    for event_ids in ([], [1, 1], [1, 2, 3, 4, 5, 6]):
        with pytest.raises(ValidationError):
            MultiEventCreateScenariosIn.model_validate(
                {
                    "miEventIds": event_ids,
                    "userId": 10,
                },
            )


def test_v3_single_event_prompt_forbids_interactions() -> None:
    state = _v3_generation_state()
    prompt = build_v3_analysis_design_user_prompt(
        events=[state.events[0].model_dump()],
        templates=[state.templates[0].model_dump()],
    )

    assert "입력 Event가 하나이므로 interactions는 빈 배열" in prompt


@pytest.mark.parametrize(
    ("api_version", "generation_strategy"),
    [
        ("v2", "multi_event_source_dimensions"),
        ("v3", "multi_event_composite_dimensions"),
    ],
)
def test_v2_v3_prepare_does_not_load_model_impact_levers(
    api_version: str,
    generation_strategy: str,
) -> None:
    payload = MultiEventCreateScenariosIn(
        mi_event_ids=EVENT_IDS,
        user_id=7,
    )
    events = [
        EventPayload(mi_event_id=101, event_type_l2_id=8),
        EventPayload(mi_event_id=202, event_type_l2_id=12),
    ]
    templates = [
        SimpleNamespace(
            model_dump=Mock(
                return_value={
                    "scenario_dimension_template_id": template_id,
                    "template_checksum": checksum,
                },
            ),
        )
        for template_id, checksum in ((81, "checksum-8"), (121, "checksum-12"))
    ]
    prepared_group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version=api_version,
        generation_strategy=generation_strategy,
    )

    with (
        patch.object(EventService, "load_events", return_value=events),
        patch.object(
            ScenarioService,
            "load_pipeline_template_with_metadata",
            side_effect=templates,
        ),
        patch.object(
            ScenarioGroupService,
            "prepare_multi_event_group",
            return_value=prepared_group,
        ),
        patch.object(
            ModelImpactLeverService,
            "load_active_catalog",
            side_effect=AssertionError(f"{api_version} must not load the Lever catalog"),
        ),
    ):
        prepared = multi_event_flow.prepare_multi_event_scenarios(
            payload,
            api_version=api_version,
        )

    assert prepared["api_version"] == api_version
    assert prepared["templates"] == templates


def test_v2_schema_exposes_only_compact_event_and_dimension_fields() -> None:
    payload = _result(strategy="multi_event_source_dimensions").model_dump(by_alias=True)

    assert set(payload["eventShocks"][0]) == {"eventId", "shockSummary"}
    assert set(payload["selectedDimensions"][0]) == {
        "dimensionId",
        "sourceRef",
        "selectionCriterion",
        "selectionRationale",
        "values",
    }
    assert set(payload["selectedDimensions"][0]["sourceRef"]) == {
        "eventId",
        "scenarioDimensionTemplateId",
        "dimKey",
    }
    assert set(payload["selectedDimensions"][0]["values"][0]) == {
        "valueId",
        "label",
        "pressureContribution",
    }


def test_v2_llm_schema_stays_smaller_than_v3_composite_schema() -> None:
    v2_size = len(
        json.dumps(
            multi_event_flow.multi_event_generation_schema("v2").model_json_schema(),
            ensure_ascii=False,
        ),
    )
    v3_size = len(
        json.dumps(
            multi_event_flow.multi_event_generation_schema("v3").model_json_schema(),
            ensure_ascii=False,
        ),
    )

    assert v2_size < 5_000
    assert v2_size < v3_size


def test_v2_schema_rejects_removed_detailed_lineage_fields() -> None:
    payload = _result(strategy="multi_event_source_dimensions").model_dump(by_alias=True)
    payload["eventShocks"][0]["impactPaths"] = []
    payload["selectedDimensions"][0]["values"][0]["sourceAssignments"] = []

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        V2MultiEventGenerationResult.model_validate(payload)


def test_v3_schema_discards_v2_only_excluded_dimensions_before_validation() -> None:
    payload = _result(
        strategy="multi_event_composite_dimensions",
    ).model_dump(by_alias=True)
    payload["excludedDimensions"] = [
        {
            "eventId": 202,
            "eventTypeL2Id": 12,
            "scenarioDimensionTemplateId": 121,
            "templateChecksum": "checksum-12",
            "dimKey": "inventory",
            "selectionCriterion": "none",
            "required": False,
            "reasonCode": "LOWER_PRIORITY",
            "reason": "합성 dimension에서 별도 축으로 사용하지 않는다.",
        },
    ]

    parsed = V3MultiEventGenerationResult.model_validate(payload)

    assert parsed.excluded_dimensions == []


@pytest.mark.parametrize(
    "schema",
    [V2MultiEventGenerationResult, V3MultiEventGenerationResult],
)
def test_multi_event_generation_schema_is_openai_strict_compatible(
    schema: type[V2MultiEventGenerationResult] | type[V3MultiEventGenerationResult],
) -> None:
    parameters = pydantic_function_tool(schema)["function"]["parameters"]
    invalid_objects: list[str] = []

    def inspect_schema(value: object, path: str = "$") -> None:
        if isinstance(value, dict):
            if value.get("type") == "object":
                properties = value.get("properties", {})
                if value.get("additionalProperties") is not False:
                    invalid_objects.append(f"{path}: additionalProperties")
                if set(value.get("required", [])) != set(properties):
                    invalid_objects.append(f"{path}: required")
            for key, child in value.items():
                inspect_schema(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect_schema(child, f"{path}[{index}]")

    inspect_schema(parameters)

    assert invalid_objects == []
    definitions = parameters["$defs"]
    if schema is V2MultiEventGenerationResult:
        assert set(definitions["V2EventShock"]["properties"]) == {"eventId", "shockSummary"}
        assert set(definitions["V2SelectedDimension"]["properties"]) == {
            "dimensionId",
            "sourceRef",
            "selectionCriterion",
            "selectionRationale",
            "values",
        }
        scenario_definition = definitions["V2ScenarioCandidate"]
    else:
        assert set(definitions["V3EventShock"]["properties"]) == {
            "eventId",
            "shockSummary",
        }
        assert set(definitions["V3DimensionDefinition"]["properties"]) == {
            "dimensionId",
            "label",
            "description",
            "rationale",
            "sourceEventIds",
            "sourceRefs",
            "values",
        }
        assert set(definitions["V3SourceReference"]["properties"]) == {
            "scenarioDimensionTemplateId",
            "dimKey",
        }
        assert set(definitions["V3DimensionValueDefinition"]["properties"]) == {
            "valueId",
            "label",
            "pressureContribution",
            "description",
            "derivationRationale",
        }
        scenario_definition = definitions["ScenarioCandidate"]
    assert scenario_definition["properties"]["dimensionValues"]["type"] == "array"


def test_v2_schema_converts_strict_wire_scenario_cells_to_domain_map() -> None:
    payload = _result(
        strategy="multi_event_source_dimensions",
    ).model_dump(by_alias=True)
    scenario = payload["scenarios"][0]
    scenario["dimensionValues"] = [
        {"dimensionId": key, "valueId": value} for key, value in scenario["dimensionValues"].items()
    ]

    parsed = V2MultiEventGenerationResult.model_validate(payload)

    assert parsed.scenarios[0].dimension_values


def test_initial_schema_validation_failure_enters_feedback_retry_loop() -> None:
    valid_analysis = _v3_analysis_result()
    invalid_response = MIBaseError(
        multi_event_flow.ErrorCode.LLM_INVALID_RESPONSE_ERROR,
        detail="dimensionDefinitions is invalid",
    )
    invoke = AsyncMock(side_effect=[invalid_response, valid_analysis])
    state = MultiEventGenerationState(
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
    )

    with (
        patch.object(
            multi_event_nodes,
            "invoke_stage_structured_output",
            new=invoke,
        ),
        patch.object(
            multi_event_nodes,
            "_backoff",
            new=AsyncMock(),
        ),
    ):
        first = asyncio.run(multi_event_nodes.AnalyzeV3EventsNode().run(state))
        state = state.model_copy(update=first)
        assert multi_event_nodes.route_after_v3_analysis(state) == "analyze_v3_events"
        second = asyncio.run(multi_event_nodes.AnalyzeV3EventsNode().run(state))

    assert second["analysis_draft"] == valid_analysis
    assert invoke.await_count == 2
    retry_prompt = invoke.await_args_list[1].kwargs["user_prompt"]
    assert "dimensionDefinitions" in retry_prompt


def test_v2_semantic_validation_stops_after_three_graph_attempts() -> None:
    invoke = AsyncMock(
        side_effect=MIBaseError(
            multi_event_flow.ErrorCode.LLM_INVALID_RESPONSE_ERROR,
            detail="selectedDimensions is invalid",
        ),
    )
    state = MultiEventGenerationState(
        api_version="v2",
        generation_strategy="multi_event_source_dimensions",
    )

    with (
        patch.object(multi_event_nodes, "invoke_stage_structured_output", new=invoke),
        patch.object(multi_event_nodes, "_backoff", new=AsyncMock()),
    ):
        for attempt in range(1, 4):
            update = asyncio.run(multi_event_nodes.GenerateDimensionsNode().run(state))
            state = state.model_copy(update=update)
            expected_route = "generate_dimensions" if attempt < 3 else "fail_generation"
            assert multi_event_nodes.route_after_dimensions(state) == expected_route

    assert invoke.await_count == 3
    assert "selectedDimensions" in invoke.await_args_list[1].kwargs["user_prompt"]


def test_v3_langgraph_uses_three_independent_llm_stages() -> None:
    aggregate = _result(strategy="multi_event_composite_dimensions")
    analysis = _v3_analysis_result()
    dimension_design = _v3_dimension_design_result()
    calls: list[str] = []

    async def invoke_stage(*, output_schema: type[object], user_prompt: str, **_kwargs: object) -> object:
        calls.append(output_schema.__name__)
        if output_schema is V3AnalysisDesignResult:
            return analysis
        if output_schema is V3DimensionDesignResult:
            return dimension_design
        return V3ScenarioSynthesisResult(
            scenario_group_title=aggregate.scenario_group_title,
            scenario_group_description=aggregate.scenario_group_description,
            scenarios=aggregate.scenarios,
            excluded_candidates=aggregate.excluded_candidates,
        )

    template_dimensions = {
        81: ["tightness", "duration", "intensity"],
        121: ["tightness", "recovery", "competition"],
    }
    state = MultiEventGenerationState(
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            api_version="v3",
            generation_strategy="multi_event_composite_dimensions",
        ),
        events=[
            EventPayload(mi_event_id=101, event_type_l2_id=8),
            EventPayload(mi_event_id=202, event_type_l2_id=12),
        ],
        templates=[
            ScenarioPipelineTemplate(
                scenario_dimension_template_id=template_id,
                event_type_l2_id=event_type_id,
                template_checksum=f"checksum-{event_type_id}",
                dimensions=[
                    {
                        "dim_key": dim_key,
                        "label": dim_key,
                        "description": f"{dim_key} 설명",
                        "value_enums": ["낮음", "중간", "높음"],
                    }
                    for dim_key in template_dimensions[template_id]
                ],
            )
            for template_id, event_type_id in ((81, 8), (121, 12))
        ],
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        user_id=7,
    )

    multi_event_flow.get_compiled_graph.cache_clear()
    with (
        patch.object(multi_event_nodes, "invoke_stage_structured_output", side_effect=invoke_stage),
        patch.object(multi_event_nodes, "_backoff", new=AsyncMock()),
        patch.object(
            ScenarioGroupService,
            "persist_multi_event_generation",
            return_value=(state.scenario_group, []),
        ) as persist,
    ):
        final_state = asyncio.run(multi_event_flow.get_compiled_graph().ainvoke(state))
    multi_event_flow.get_compiled_graph.cache_clear()

    assert calls.count("V3AnalysisDesignResult") == 1
    assert calls.count("V3DimensionDesignResult") == 1
    assert calls.count("V3ScenarioSynthesisResult") == 1
    assert len(calls) == 3
    assert final_state["analysis_attempt"] == 1
    assert final_state["dimension_attempt"] == 1
    assert final_state["scenario_attempt"] == 1
    diagnostics = final_state["generation_diagnostics"]
    assert len(diagnostics.template_dimension_selections) == 6
    unused = next(
        selection for selection in diagnostics.template_dimension_selections if selection.dim_key == "intensity"
    )
    assert unused.label == "intensity"
    assert unused.value_enum_examples == ["낮음", "중간", "높음"]
    assert unused.used_in_dimension_ids == []
    persisted_diagnostics = persist.call_args.kwargs["generation_diagnostics"]
    assert "template_dimension_selections" in persisted_diagnostics
    persist.assert_called_once()


@pytest.mark.parametrize("schema", [V3AnalysisDesignResult, V3DimensionDesignResult, V3ScenarioSynthesisResult])
def test_each_v3_llm_stage_schema_is_openai_strict_compatible(schema: type[object]) -> None:
    parameters = pydantic_function_tool(schema)["function"]["parameters"]
    invalid_objects: list[str] = []

    def inspect_schema(value: object, path: str = "$") -> None:
        if isinstance(value, dict):
            if value.get("type") == "object":
                properties = value.get("properties", {})
                if value.get("additionalProperties") is not False:
                    invalid_objects.append(f"{path}: additionalProperties")
                if set(value.get("required", [])) != set(properties):
                    invalid_objects.append(f"{path}: required")
            for key, child in value.items():
                inspect_schema(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect_schema(child, f"{path}[{index}]")

    inspect_schema(parameters)

    assert invalid_objects == []


def test_v3_analysis_hydrates_only_event_owned_template_candidates() -> None:
    state = _v3_generation_state().model_copy(update={"analysis_draft": _v3_analysis_result()})

    update = multi_event_nodes.validate_v3_analysis_design(state)

    selections = update["template_dimension_selections"]
    first = selections[0]
    assert first.label == "tightness 원본 라벨"
    assert first.description == "tightness 원본 설명"
    assert first.required is True
    assert first.value_enums == ["낮음", "중간", "높음"]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda items: setattr(items[0], "event_id", 202), "does not belong"),
        (lambda items: setattr(items[0], "scenario_dimension_template_id", 999), "does not belong"),
        (lambda items: items.append(items[0]), "duplicate"),
        (
            lambda items: items.__setitem__(slice(None), [item for item in items if item.event_id != 202]),
            "without a Template dimension selection",
        ),
    ],
)
def test_v3_analysis_rejects_invalid_template_candidate_sets(
    mutate: object,
    message: str,
) -> None:
    analysis = _v3_analysis_result().model_copy(deep=True)
    mutate(analysis.template_dimension_selections)  # type: ignore[operator]
    state = _v3_generation_state().model_copy(update={"analysis_draft": analysis})

    update = multi_event_nodes.validate_v3_analysis_design(state)

    assert message in update["analysis_error"]
    assert update["template_dimension_selections"] == []


def test_v3_analysis_rejects_more_than_four_candidates_per_event() -> None:
    state = _v3_generation_state()
    template = state.templates[0]
    state.templates[0] = template.model_copy(
        update={
            "dimensions": [
                *template.dimensions,
                template.dimensions[0].model_copy(update={"dim_key": "fifth_candidate"}),
                template.dimensions[0].model_copy(update={"dim_key": "sixth_candidate"}),
            ],
            "template_dimensions_total": 5,
        },
    )
    analysis = _v3_analysis_result().model_copy(deep=True)
    for dim_key in ("fifth_candidate", "sixth_candidate"):
        analysis.template_dimension_selections.append(
            analysis.template_dimension_selections[0].model_copy(update={"dim_key": dim_key}),
        )
    state.analysis_draft = analysis

    update = multi_event_nodes.validate_v3_analysis_design(state)

    assert "more than four" in update["analysis_error"]


def _validated_v3_analysis_state() -> MultiEventGenerationState:
    state = _v3_generation_state().model_copy(update={"analysis_draft": _v3_analysis_result()})
    return state.model_copy(update=multi_event_nodes.validate_v3_analysis_design(state))


def test_v3_dimension_mapping_projects_to_compact_lineage_in_mapping_order() -> None:
    state = _validated_v3_analysis_state().model_copy(update={"dimension_draft": _v3_dimension_design_result()})

    update = multi_event_nodes.validate_dimensions(state)

    first = update["dimension_definitions"][0]
    assert first.source_event_ids == [101, 202]
    assert [(source.scenario_dimension_template_id, source.dim_key) for source in first.source_refs] == [
        (81, "tightness"),
        (121, "tightness"),
    ]
    assert first.values[0].description
    assert first.values[0].derivation_rationale


def test_v3_dimension_rejects_mapping_not_selected_during_analysis() -> None:
    state = _validated_v3_analysis_state()
    draft = _v3_dimension_design_result().model_copy(deep=True)
    draft.dimension_definitions[0].source_mappings[0].dim_key = "intensity_not_selected"
    state.dimension_draft = draft

    update = multi_event_nodes.validate_dimensions(state)

    assert "not present in validated Template selections" in update["dimension_error"]


def test_v3_dimension_rejects_unknown_template_enum_anchor() -> None:
    state = _validated_v3_analysis_state()
    draft = _v3_dimension_design_result().model_copy(deep=True)
    draft.dimension_definitions[0].values[0].template_value_anchors[0].template_value = "원본에 없음"
    state.dimension_draft = draft

    update = multi_event_nodes.validate_dimensions(state)

    assert "does not match the source Template enum" in update["dimension_error"]


def test_v3_dimension_requires_every_enum_source_and_every_value_to_be_anchored() -> None:
    state = _validated_v3_analysis_state()
    missing_source = _v3_dimension_design_result().model_copy(deep=True)
    first = missing_source.dimension_definitions[0]
    for value in first.values:
        value.template_value_anchors = value.template_value_anchors[:1]
    state.dimension_draft = missing_source

    source_update = multi_event_nodes.validate_dimensions(state)

    assert "enum-bearing sourceMappings" in source_update["dimension_error"]

    missing_value = _v3_dimension_design_result().model_copy(deep=True)
    missing_value.dimension_definitions[0].values[0].template_value_anchors = []
    state.dimension_draft = missing_value

    value_update = multi_event_nodes.validate_dimensions(state)

    assert "each value requires a valid templateValueAnchor" in value_update["dimension_error"]


def test_v3_dimension_allows_event_specific_values_without_template_enums() -> None:
    state = _validated_v3_analysis_state()
    state.template_dimension_selections = [
        selection.model_copy(update={"value_enums": []}) for selection in state.template_dimension_selections
    ]
    draft = _v3_dimension_design_result().model_copy(deep=True)
    for dimension in draft.dimension_definitions:
        for value in dimension.values:
            value.label = f"Event 특화 {value.label}"
            value.template_value_anchors = []
    state.dimension_draft = draft

    update = multi_event_nodes.validate_dimensions(state)

    assert update["dimension_error"] is None
    assert update["dimension_definitions"][0].values[0].label.startswith("Event 특화")


def test_pipeline_template_allows_dimensions_without_enum_anchors() -> None:
    template = ScenarioPipelineTemplate(
        scenario_dimension_template_id=81,
        event_type_l2_id=8,
        dimensions=[
            {"dim_key": f"dimension_{index}", "label": f"Dimension {index}", "value_enums": []} for index in range(3)
        ],
    )

    assert all(dimension.value_enums == [] for dimension in template.dimensions)


def test_v3_public_value_schema_reads_legacy_nullable_details() -> None:
    payload = _result(strategy="multi_event_composite_dimensions").model_dump(by_alias=True)
    for dimension in payload["dimensionDefinitions"]:
        for value in dimension["values"]:
            value.pop("description")
            value.pop("derivationRationale")

    parsed = V3MultiEventGenerationResult.model_validate(payload)

    assert parsed.dimension_definitions[0].values[0].description is None
    assert parsed.dimension_definitions[0].values[0].derivation_rationale is None


def test_v3_dimension_retry_reuses_validated_analysis() -> None:
    aggregate = _result(strategy="multi_event_composite_dimensions")
    stage_calls: list[str] = []
    dimension_calls = 0

    async def invoke_stage(*, output_schema: type[object], **_kwargs: object) -> object:
        nonlocal dimension_calls
        stage_calls.append(output_schema.__name__)
        if output_schema is V3AnalysisDesignResult:
            return _v3_analysis_result()
        if output_schema is V3DimensionDesignResult:
            dimension_calls += 1
            if dimension_calls == 1:
                raise MIBaseError(
                    multi_event_flow.ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                    detail="sourceMappings is invalid",
                )
            return _v3_dimension_design_result()
        return V3ScenarioSynthesisResult(
            scenario_group_title=aggregate.scenario_group_title,
            scenario_group_description=aggregate.scenario_group_description,
            scenarios=aggregate.scenarios,
            excluded_candidates=aggregate.excluded_candidates,
        )

    state = _v3_generation_state()
    multi_event_flow.get_compiled_graph.cache_clear()
    with (
        patch.object(multi_event_nodes, "invoke_stage_structured_output", side_effect=invoke_stage),
        patch.object(multi_event_nodes, "_backoff", new=AsyncMock()),
        patch.object(
            ScenarioGroupService,
            "persist_multi_event_generation",
            return_value=(state.scenario_group, []),
        ),
    ):
        final_state = asyncio.run(multi_event_flow.get_compiled_graph().ainvoke(state))
    multi_event_flow.get_compiled_graph.cache_clear()

    assert stage_calls.count("V3AnalysisDesignResult") == 1
    assert stage_calls.count("V3DimensionDesignResult") == 2
    assert stage_calls.count("V3ScenarioSynthesisResult") == 1
    assert final_state["analysis_attempt"] == 1
    assert final_state["dimension_attempt"] == 2


def test_v2_langgraph_uses_deterministic_event_grounding_and_two_stage_calls() -> None:
    aggregate = _result(strategy="multi_event_source_dimensions")
    calls: list[str] = []

    async def invoke_stage(*, output_schema: type[object], user_prompt: str, **_kwargs: object) -> object:
        calls.append(output_schema.__name__)
        if output_schema is V2DimensionDesignResult:
            return V2DimensionDesignResult(selected_dimensions=aggregate.selected_dimensions)
        return V2ScenarioSynthesisResult(
            scenario_group_title=aggregate.scenario_group_title,
            scenario_group_description=aggregate.scenario_group_description,
            scenarios=aggregate.scenarios,
        )

    template_dimensions = {
        81: ["heat", "duration", "intensity"],
        121: ["inventory", "recovery", "competition"],
    }
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v2",
        generation_strategy="multi_event_source_dimensions",
    )
    state = MultiEventGenerationState(
        scenario_group=group,
        events=[
            EventPayload(
                mi_event_id=101,
                event_type_l2_id=8,
                event_title_ko="한파 시작",
                one_line_summary="한파에 따른 수요 증가가 관측된다.",
            ),
            EventPayload(
                mi_event_id=202,
                event_type_l2_id=12,
                event_title_ko="정비 시작",
                one_line_summary="액화시설 정비가 시작됐다.",
            ),
        ],
        templates=[
            ScenarioPipelineTemplate(
                scenario_dimension_template_id=template_id,
                event_type_l2_id=event_type_id,
                template_checksum=f"checksum-{event_type_id}",
                dimensions=[
                    {
                        "dim_key": dim_key,
                        "label": dim_key,
                        "description": f"{dim_key} 설명",
                        "value_enums": ["낮음", "중간", "높음"],
                    }
                    for dim_key in template_dimensions[template_id]
                ],
            )
            for template_id, event_type_id in ((81, 8), (121, 12))
        ],
        api_version="v2",
        generation_strategy="multi_event_source_dimensions",
        user_id=7,
    )

    multi_event_flow.get_compiled_graph.cache_clear()
    with (
        patch.object(multi_event_nodes, "invoke_stage_structured_output", side_effect=invoke_stage),
        patch.object(multi_event_nodes, "_backoff", new=AsyncMock()),
        patch.object(
            ScenarioGroupService,
            "persist_multi_event_generation",
            return_value=(group, []),
        ) as persist,
    ):
        final_state = asyncio.run(multi_event_flow.get_compiled_graph().ainvoke(state))
    multi_event_flow.get_compiled_graph.cache_clear()

    assert calls.count("V2DimensionDesignResult") == 1
    assert calls.count("V2ScenarioSynthesisResult") == 1
    assert len(calls) == 2
    assert [shock.event_id for shock in final_state["event_shocks"]] == EVENT_IDS
    assert "정비가 시작" in final_state["event_shocks"][1].shock_summary
    assert final_state["dimension_attempt"] == 1
    assert final_state["scenario_attempt"] == 1
    persist.assert_called_once()


def test_multi_event_graph_disables_connector_level_retry() -> None:
    result = V2DimensionDesignResult(
        selected_dimensions=_result(strategy="multi_event_source_dimensions").selected_dimensions,
    )
    invoke = AsyncMock(return_value=SimpleNamespace(result=result))
    settings = SimpleNamespace(
        llm_stream_enabled=True,
        llm_reasoning_effort="medium",
    )
    config_module = ModuleType("apps.common.configs.config")
    config_module.get_settings = Mock(return_value=settings)
    llm_module = ModuleType("apps.connectors.llm.llm_client")
    llm_module.invoke_llm_structured_output = invoke

    with patch.dict(
        sys.modules,
        {
            "apps.common.configs.config": config_module,
            "apps.connectors.llm.llm_client": llm_module,
        },
    ):
        actual = asyncio.run(
            multi_event_nodes.invoke_stage_structured_output(
                output_schema=V2DimensionDesignResult,
                system_prompt="system",
                user_prompt="user",
                trace_context=None,
            ),
        )

    assert actual == result
    assert invoke.await_args.kwargs["max_retries"] == 0
    assert invoke.await_args.kwargs["stream"] is True
    assert invoke.await_args.kwargs["reasoning_effort"] == "medium"


@pytest.mark.parametrize(
    "strategy",
    [
        "multi_event_source_dimensions",
        "multi_event_composite_dimensions",
    ],
)
def test_finalization_assigns_roles_and_single_highest_probability_baseline(
    strategy: str,
) -> None:
    finalized = finalize_generation_result(
        _result(strategy=strategy),
        generation_strategy=strategy,
        event_ids=EVENT_IDS,
    )

    roles = [scenario.scenario_role for scenario in finalized.scenarios]
    assert roles.count("floor") == 1
    assert roles.count("ceiling") == 1
    assert roles.count("mixed") == 1
    baselines = [scenario for scenario in finalized.scenarios if scenario.baseline_yn == "Y"]
    assert len(baselines) == 1
    assert baselines[0].pressure_band == "balanced"


@pytest.mark.parametrize(
    "strategy",
    ["multi_event_source_dimensions", "multi_event_composite_dimensions"],
)
def test_floor_or_ceiling_can_be_baseline_when_it_has_highest_probability(strategy: str) -> None:
    result = _result(strategy=strategy)
    result.scenarios[0].probability_score = 95
    result.scenarios[1].probability_score = 4

    finalized = finalize_generation_result(
        result,
        generation_strategy=strategy,
        event_ids=EVENT_IDS,
    )

    baseline = next(scenario for scenario in finalized.scenarios if scenario.baseline_yn == "Y")
    assert baseline.scenario_role == "ceiling"
    assert baseline.probability_score == 95


def test_v3_finalization_requires_exactly_one_mixed_role() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    without_mixed = result.model_copy(
        update={
            "scenarios": [scenario.model_copy(update={"mixed_factors": False}) for scenario in result.scenarios],
        },
    )

    with pytest.raises(ValueError, match="exactly one non-extreme mixed"):
        finalize_generation_result(
            without_mixed,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v2_requires_namespaced_source_dimensions() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    broken = result.model_copy(
        update={
            "selected_dimensions": [
                result.selected_dimensions[0].model_copy(
                    update={"dimension_id": "heat"},
                ),
                *result.selected_dimensions[1:],
            ],
        },
    )
    with pytest.raises(ValueError, match="namespaced"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v2_rejects_an_event_without_selected_dimension_coverage() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    unrepresented_event_id = 303
    result.event_shocks.append(
        result.event_shocks[0].model_copy(
            update={"event_id": unrepresented_event_id},
        ),
    )

    with pytest.raises(ValueError, match="events without a selected dimension"):
        finalize_generation_result(
            result,
            generation_strategy="multi_event_source_dimensions",
            event_ids=[*EVENT_IDS, unrepresented_event_id],
        )


def test_v2_rejects_value_that_reverses_an_observed_started_state() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    result.event_shocks[0].shock_summary = "액화시설 정비가 시작되어 현재 진행 중이다."
    result.selected_dimensions[0].values[0].label = "정비 취소 및 미착수"

    with pytest.raises(ValueError, match="v2 fact reversal"):
        finalize_generation_result(
            result,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v2_dimension_prompt_preserves_authoritative_facts_without_event_analysis_llm() -> None:
    prompt = build_dimension_design_user_prompt(
        api_version="v2",
        events=[
            {
                "mi_event_id": 101,
                "event_title_ko": "정비 시작",
                "one_line_summary": "액화시설 정비가 이미 시작됐다.",
                "key_bullets": ["현장 작업이 진행 중이다."],
            },
        ],
        templates=[
            {
                "scenario_dimension_template_id": 81,
                "dimensions": [
                    {
                        "dim_key": "duration",
                        "label": "정비 기간",
                        "description": "정비 지속 기간",
                        "value_enums": ["단기", "장기"],
                    },
                ],
            },
        ],
        event_shocks=[{"event_id": 101, "shock_summary": "정비가 이미 시작됐다."}],
    )

    assert "Event Context (authoritative current facts)" in prompt
    assert "모든 입력 Event" in prompt
    assert "취소·미발생 상태로 되돌리는 value" in prompt


def test_v3_prompts_require_independent_drivers_and_one_explicit_mixed_scenario() -> None:
    dimension_definitions = [
        dimension.model_dump()
        for dimension in _result(strategy="multi_event_composite_dimensions").dimension_definitions
    ]
    analysis_prompt = build_v3_analysis_design_user_prompt(events=[], templates=[])
    dimension_prompt = build_v3_dimension_design_user_prompt(
        event_shocks=[],
        interactions=[],
        template_dimension_selections=[],
    )
    scenario_prompt = build_scenario_synthesis_user_prompt(
        api_version="v3",
        event_shocks=[],
        dimension_definitions=dimension_definitions,
        interactions=[],
    )

    assert "Event별 templateDimensionSelections를 1~4개" in analysis_prompt
    assert "Hydrated Template Dimension Candidates" in dimension_prompt
    assert "sourceMappings" in dimension_prompt
    assert "value label은 10~40자" in dimension_prompt
    assert "핵심 수치·범위·기간을 최대 2개" in dimension_prompt
    assert "근거가 없으면 수치를 만들지 말고" in dimension_prompt
    assert "통항 정상화·보험료 부담 잔존" in dimension_prompt
    assert "정확히 하나" in scenario_prompt
    assert "mixedFactors=true" in scenario_prompt
    assert "상태가 구체적으로 전개된다" in scenario_prompt
    assert "원본 Template enum 의미" in scenario_prompt


def test_v3_dimension_prompt_preserves_grounded_quantitative_label_inputs() -> None:
    dimension_prompt = build_v3_dimension_design_user_prompt(
        event_shocks=[
            {
                "event_id": 1342,
                "shock_summary": "유럽 원전 출력 조정이 가스발전 대체수요를 키울 수 있다.",
            },
        ],
        interactions=[],
        template_dimension_selections=[
            {
                "event_id": 1342,
                "scenario_dimension_template_id": 5,
                "dim_key": "capacity_change_scale",
                "observed_basis": "인접국까지 포함하면 원전 감발 규모가 확대될 수 있다.",
                "selection_rationale": "감발 규모가 유럽 LNG 흡수력을 구분한다.",
                "label": "Capacity 변화 규모",
                "description": "원전 설비용량 변화 규모.",
                "required": True,
                "value_enums": ["1 GW 미만", "1~3 GW", "3~5 GW"],
            },
            {
                "event_id": 1342,
                "scenario_dimension_template_id": 5,
                "dim_key": "alt_energy_absorption",
                "observed_basis": "다른 에너지원의 흡수 여력이 LNG 수요 전이를 좌우한다.",
                "selection_rationale": "대체 흡수율이 가스발전 전환 규모를 구분한다.",
                "label": "타 에너지원 흡수 가능성",
                "description": "원전 감소분을 다른 에너지원이 흡수하는 비율.",
                "required": True,
                "value_enums": ["100%", "50%", "25%"],
            },
        ],
    )

    assert "3~5 GW" in dimension_prompt
    assert "25%" in dimension_prompt
    assert "3~5GW 감발·대체 흡수 25%" in dimension_prompt
    assert "입력 후보만 참조" in dimension_prompt


def test_v3_independent_interaction_requires_separate_single_source_dimensions() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    result.interactions[0].relation = "independent"
    result.dimension_definitions[1].source_event_ids = EVENT_IDS

    with pytest.raises(ValueError, match="separate single-source dimensions"):
        finalize_generation_result(
            result,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


@pytest.mark.parametrize(
    "strategy",
    [
        "multi_event_source_dimensions",
        "multi_event_composite_dimensions",
    ],
)
@pytest.mark.parametrize("dimension_count", [2, 7])
def test_multi_event_dimension_count_must_be_between_three_and_six(
    strategy: str,
    dimension_count: int,
) -> None:
    result = _result(strategy=strategy)
    field_name = "selected_dimensions" if strategy == "multi_event_source_dimensions" else "dimension_definitions"
    dimensions = (
        result.selected_dimensions if strategy == "multi_event_source_dimensions" else result.dimension_definitions
    )
    broken = result.model_copy(
        update={
            field_name: [dimensions[0] for _ in range(dimension_count)],
        },
    )

    with pytest.raises(ValueError, match="dimension count is out of range"):
        finalize_generation_result(
            broken,
            generation_strategy=strategy,
            event_ids=EVENT_IDS,
        )


def test_v3_allows_independent_single_source_dimension_without_forced_merge() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    assert any(len(dimension.source_refs) == 1 for dimension in result.dimension_definitions)
    finalized = finalize_generation_result(
        result,
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )
    assert len(finalized.dimension_definitions) == 4


def test_v3_does_not_require_exhaustive_pairwise_interactions() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    third_event_id = 303
    result.event_shocks.append(
        result.event_shocks[1].model_copy(
            update={"event_id": third_event_id},
        ),
    )
    third_dimension = V3DimensionDefinition.model_validate(
        _compact_dimension(
            dimension_id="third_event_path",
            source_event_ids=[third_event_id],
            source_refs=[(3031, "third_path")],
        ),
    )
    result.dimension_definitions.append(third_dimension)
    for scenario in result.scenarios:
        scenario.dimension_values[third_dimension.dimension_id] = "Event 사실 기반 균형"

    finalized = finalize_generation_result(
        result,
        generation_strategy="multi_event_composite_dimensions",
        event_ids=[*EVENT_IDS, third_event_id],
    )

    assert [interaction.event_ids for interaction in finalized.interactions] == [EVENT_IDS]


def test_v3_accepts_one_interaction_with_more_than_two_events() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    third_event_id = 303
    result.event_shocks.append(
        result.event_shocks[1].model_copy(
            update={"event_id": third_event_id},
        ),
    )
    third_dimension = V3DimensionDefinition.model_validate(
        _compact_dimension(
            dimension_id="third_event_path",
            source_event_ids=[third_event_id],
            source_refs=[(3031, "third_path")],
        ),
    )
    result.dimension_definitions.append(third_dimension)
    for scenario in result.scenarios:
        scenario.dimension_values[third_dimension.dimension_id] = "Event 사실 기반 균형"
    result.interactions = [
        EventInteraction.model_validate(
            {
                "eventIds": [*EVENT_IDS, third_event_id],
                "relation": "regional_coupling",
                "rationale": "세 Event가 지역 구매 경쟁으로 함께 연결된다.",
                "resolutionDimensionId": "demand_inventory_tightness",
            },
        ),
    ]
    result.dimension_definitions[0].source_event_ids.append(third_event_id)

    finalized = finalize_generation_result(
        result,
        generation_strategy="multi_event_composite_dimensions",
        event_ids=[*EVENT_IDS, third_event_id],
    )

    assert finalized.interactions[0].event_ids == [101, 202, 303]
    resolution_dimension = next(
        dimension
        for dimension in finalized.dimension_definitions
        if dimension.dimension_id == "demand_inventory_tightness"
    )
    assert set(resolution_dimension.source_event_ids) == {101, 202, 303}


@pytest.mark.parametrize("event_ids", [[], [101], [101, 101]])
def test_v3_interaction_requires_at_least_two_distinct_events(
    event_ids: list[int],
) -> None:
    with pytest.raises(ValidationError):
        EventInteraction.model_validate(
            {
                "eventIds": event_ids,
                "relation": "independent",
                "rationale": "Event 관계를 기록한다.",
            },
        )


def test_v3_non_independent_interaction_rejects_missing_source_event_ids() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    broken_dimension = first_dimension.model_copy(
        update={"source_event_ids": [101]},
    )
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                broken_dimension,
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="sourceEventIds"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v2_source_refs_must_exist_in_the_event_type_templates() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    source_dimensions = {
        101: {"heat": True, "duration": True},
        202: {
            "heat": False,
            "inventory": True,
            "recovery": True,
            "competition": True,
        },
    }
    first_dimension = result.selected_dimensions[0]
    unknown_ref = first_dimension.source_ref.model_copy(
        update={"dim_key": "not_in_template"},
    )
    broken = result.model_copy(
        update={
            "selected_dimensions": [
                first_dimension.model_copy(
                    update={"source_ref": unknown_ref},
                ),
                *result.selected_dimensions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="sourceRef is not present"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
            source_dimensions_by_event=source_dimensions,
        )


def test_v2_rejects_duplicate_compact_source_ref() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    first = result.selected_dimensions[0]
    duplicate = result.selected_dimensions[1].model_copy(
        update={"dimension_id": first.dimension_id, "source_ref": first.source_ref},
    )
    broken = result.model_copy(update={"selected_dimensions": [first, duplicate, *result.selected_dimensions[2:]]})

    with pytest.raises(ValueError, match="duplicate sourceRef"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v3_rejects_display_prefixed_source_keys() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    prefixed_refs = [
        (
            source.model_copy(update={"dim_key": "d1_tightness"})
            if source.scenario_dimension_template_id == 81
            else source
        )
        for source in first_dimension.source_refs
    ]
    source_dimensions = {
        101: {"tightness": True, "duration": True},
        202: {
            "tightness": True,
            "recovery": True,
            "competition": True,
        },
    }

    with pytest.raises(ValueError, match="not present in the input Template"):
        finalize_generation_result(
            result.model_copy(
                update={
                    "dimension_definitions": [
                        first_dimension.model_copy(
                            update={"source_refs": prefixed_refs},
                        ),
                        *result.dimension_definitions[1:],
                    ],
                },
            ),
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
            source_dimensions_by_event=source_dimensions,
        )


def test_v3_rejects_source_ref_from_a_different_template_id() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    first_dimension.source_refs[0].scenario_dimension_template_id = 999
    source_dimensions = _revisioned_sources(
        {
            101: {
                "heat": False,
                "tightness": False,
                "duration": False,
            },
            202: {
                "heat": False,
                "tightness": False,
                "recovery": False,
                "competition": False,
            },
        },
    )

    with pytest.raises(ValueError, match="not present in the input Template"):
        _finalize_generation_result(
            result,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
            source_dimensions_by_event=source_dimensions,
        )


def test_v2_rejects_source_ref_from_a_different_template_id() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    result.selected_dimensions[0].source_ref.scenario_dimension_template_id = 999
    source_dimensions = _revisioned_sources(
        {
            101: {"heat": False, "duration": False},
            202: {
                "inventory": False,
                "recovery": False,
                "competition": False,
            },
        },
    )

    with pytest.raises(ValueError, match="Template ID does not match"):
        _finalize_generation_result(
            result,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
            source_dimensions_by_event=source_dimensions,
        )


def test_v3_event_shock_rejects_removed_detailed_fields() -> None:
    payload = _result(
        strategy="multi_event_composite_dimensions",
    ).model_dump(by_alias=True)
    payload["eventShocks"][0]["sourceDimensions"] = []

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        V3MultiEventGenerationResult.model_validate(payload)


def test_v2_normalizes_source_template_label_description_and_required() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    source_dimensions = {
        101: {
            "heat": {
                "required": True,
                "label": "원본 폭염 강도",
                "description": "원본 폭염 강도의 의미",
            },
            "duration": False,
        },
        202: {
            "heat": False,
            "inventory": True,
            "recovery": True,
            "competition": True,
        },
    }

    finalized = finalize_generation_result(
        result,
        generation_strategy="multi_event_source_dimensions",
        event_ids=EVENT_IDS,
        source_dimensions_by_event=source_dimensions,
    )

    dimension = finalized.dimension_definitions[0]
    assert dimension.label == "원본 폭염 강도"
    assert dimension.description == "원본 폭염 강도의 의미"
    assert dimension.required is True


def test_v3_event_shock_rejects_blank_summary() -> None:
    payload = _result(
        strategy="multi_event_composite_dimensions",
    ).model_dump(by_alias=True)
    payload["eventShocks"][0]["shockSummary"] = "   "

    with pytest.raises(ValidationError, match="shockSummary must not be blank"):
        V3MultiEventGenerationResult.model_validate(payload)


@pytest.mark.parametrize("shock_indexes", [[0], [0, 0, 1]])
def test_v3_requires_each_event_shock_exactly_once(
    shock_indexes: list[int],
) -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    broken = result.model_copy(
        update={
            "event_shocks": [result.event_shocks[index] for index in shock_indexes],
        },
    )

    with pytest.raises(ValueError, match="every input event exactly once"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v3_rejects_duplicate_source_ref() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                first_dimension.model_copy(
                    update={
                        "source_refs": [
                            first_dimension.source_refs[0],
                            first_dimension.source_refs[0],
                        ],
                    },
                ),
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="duplicate sourceRefs"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v3_rejects_duplicate_source_event_id() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                first_dimension.model_copy(
                    update={"source_event_ids": [101, 101, 202]},
                ),
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="duplicate sourceEventIds"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v2_derives_unselected_dimension_refs_from_template_complement() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    source_dimensions = {
        101: {
            "heat": True,
            "duration": True,
            "unselected": True,
        },
        202: {
            "inventory": True,
            "recovery": True,
            "competition": True,
            "unselected": False,
        },
    }

    finalized = finalize_generation_result(
        result,
        generation_strategy="multi_event_source_dimensions",
        event_ids=EVENT_IDS,
        source_dimensions_by_event=source_dimensions,
    )

    assert {
        (source.event_id, source.scenario_dimension_template_id, source.dim_key)
        for source in finalized.unselected_dimension_refs
    } == {(101, 81, "unselected"), (202, 121, "unselected")}


def test_v2_does_not_repair_cross_event_source_ref() -> None:
    result = _result(strategy="multi_event_source_dimensions")
    selected = result.selected_dimensions[0]
    broken_source = selected.source_ref.model_copy(update={"event_id": 202})
    broken = result.model_copy(
        update={
            "selected_dimensions": [
                selected.model_copy(update={"source_ref": broken_source}),
                *result.selected_dimensions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="Template ID does not match"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_source_dimensions",
            event_ids=EVENT_IDS,
        )


def test_multi_event_dimension_requires_three_to_five_values() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    first_dimension = result.dimension_definitions[0]
    broken = result.model_copy(
        update={
            "dimension_definitions": [
                first_dimension.model_copy(
                    update={"values": first_dimension.values[:2]},
                ),
                *result.dimension_definitions[1:],
            ],
        },
    )

    with pytest.raises(ValueError, match="3 to 5 generated values"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_v3_value_rejects_source_assignments() -> None:
    payload = _result(
        strategy="multi_event_composite_dimensions",
    ).model_dump(by_alias=True)
    payload["dimensionDefinitions"][0]["values"][0]["sourceAssignments"] = []

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        V3MultiEventGenerationResult.model_validate(payload)


def test_mixed_scenario_rejects_missing_bullish_and_bearish_contributions() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    mixed = next(scenario for scenario in result.scenarios if scenario.mixed_factors)
    balanced_only = mixed.model_copy(
        update={
            "dimension_values": {
                dimension.dimension_id: "Event 사실 기반 균형" for dimension in result.dimension_definitions
            },
        },
    )
    broken = result.model_copy(
        update={
            "scenarios": [balanced_only if scenario.mixed_factors else scenario for scenario in result.scenarios],
        },
    )

    with pytest.raises(ValueError, match="mixedFactors=true requires"):
        finalize_generation_result(
            broken,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_interpretation_conflict_rejects_incomplete_resolution_source_events() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    interaction = result.interactions[0].model_copy(
        update={
            "relation": "interpretation_conflict",
            "resolution_dimension_id": "heat_duration",
        },
    )

    with pytest.raises(ValueError, match="must reference every interaction event"):
        finalize_generation_result(
            result.model_copy(update={"interactions": [interaction]}),
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_interpretation_conflict_with_composite_resolution_is_valid() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    interaction = result.interactions[0].model_copy(
        update={
            "relation": "interpretation_conflict",
            "resolution_dimension_id": "demand_inventory_tightness",
        },
    )

    finalized = finalize_generation_result(
        result.model_copy(update={"interactions": [interaction]}),
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )

    assert finalized.interactions[0].relation == "interpretation_conflict"


def test_final_scenarios_are_sorted_by_global_pressure() -> None:
    finalized = finalize_generation_result(
        _result(strategy="multi_event_composite_dimensions"),
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )

    assert [scenario.pressure_band for scenario in finalized.scenarios] == [
        "strong_bullish",
        "balanced",
        "strong_bearish",
    ]


def test_pressure_aggregate_rejects_band_direction_contradiction() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    strong_bullish = next(scenario for scenario in result.scenarios if scenario.pressure_band == "strong_bullish")
    strong_bullish.dimension_values = {
        dimension.dimension_id: ("Event별 완화" if index == 0 else "Event 사실 기반 균형")
        for index, dimension in enumerate(result.dimension_definitions)
    }

    with pytest.raises(ValueError, match="positive aggregate pressure"):
        finalize_generation_result(
            result,
            generation_strategy="multi_event_composite_dimensions",
            event_ids=EVENT_IDS,
        )


def test_pressure_aggregate_order_allows_ties() -> None:
    result = _result(strategy="multi_event_composite_dimensions")
    strong_bullish = next(scenario for scenario in result.scenarios if scenario.pressure_band == "strong_bullish")
    mixed = next(scenario for scenario in result.scenarios if scenario.mixed_factors)
    strong_bullish.dimension_values = {
        dimension.dimension_id: ("Event별 심화" if index == 0 else "Event 사실 기반 균형")
        for index, dimension in enumerate(result.dimension_definitions)
    }
    mixed.dimension_values = {
        dimension.dimension_id: (
            "Event별 심화" if index in {0, 1} else ("Event별 완화" if index == 2 else "Event 사실 기반 균형")
        )
        for index, dimension in enumerate(result.dimension_definitions)
    }

    finalized = finalize_generation_result(
        result,
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )

    assert finalized.scenarios[0].pressure_band == "strong_bullish"


def test_lineage_only_marks_scenario_assumptions_as_assumptions() -> None:
    with pytest.raises(ValidationError):
        SourceLineage.model_validate(
            {
                **_source(101, "heat"),
                "sourceType": "event_fact",
                "assumptionYn": "Y",
            },
        )

    generated_outside_template = SourceLineage.model_validate(
        {
            **_source(101, "heat", "Event별 자연스러운 신규 value"),
            "sourceType": "event_fact",
            "assumptionYn": "N",
        },
    )
    assert generated_outside_template.source_type == "event_fact"

    with pytest.raises(ValidationError):
        SourceLineage.model_validate(
            {
                **_source(101, "heat"),
                "rationale": "",
            },
        )


def test_prompt_separates_event_facts_from_template_domain_knowledge() -> None:
    prompt = build_multi_event_user_prompt(
        api_version="v3",
        events=[
            {
                "mi_event_id": 101,
                "event_type_l2_id": 8,
                "event_title_ko": "현재 폭염 Event",
                "key_bullets": ["현재 사실"],
            },
        ],
        templates=[
            {
                "scenario_dimension_template_id": 1,
                "template_checksum": "checksum",
                "event_type_definition": "폭염 정의",
                "lng_price_impact_examples": "과거 대표 사례",
                "dimensions": [
                    {
                        "dim_key": "heat",
                        "label": "폭염",
                        "description": "현재 Event와 별개의 dimension 의미",
                        "value_enums": ["과거 예시값"],
                    },
                ],
            },
        ],
    )

    assert "## Event Context (authoritative current facts)" in prompt
    assert "## Template Domain Knowledge (reference examples" in prompt
    assert prompt.index("현재 사실") < prompt.index("과거 대표 사례")
    assert "valueEnumExamples" in prompt
    assert "eventIds를 정확히 2개로 제한하지 않습니다" in prompt
    assert "모든 Event pair를 기계적으로 만들지" in prompt


def test_legacy_template_description_falls_back_but_new_write_requires_it() -> None:
    legacy = [
        {
            "dim_key": f"dimension_{index}",
            "label": f"Dimension {index}",
            "value_enums": ["낮음", "높음"],
            "display_order": index,
        }
        for index in range(1, 4)
    ]
    mapped = ScenarioService()._map_template_json_to_pipeline_template(
        legacy,
        event_type_l2_id=8,
    )
    assert mapped.dimensions[0].description == "Dimension 1"

    with pytest.raises(ValueError, match="description is required"):
        ScenarioService().validate_template_for_write(
            legacy,
            event_type_l2_id=8,
        )

    for item in legacy:
        item["description"] = f"{item['label']} 상세 설명"
    strict = ScenarioService().validate_template_for_write(
        legacy,
        event_type_l2_id=8,
    )
    assert strict.dimensions[0].description == "Dimension 1 상세 설명"


def test_template_domain_fields_round_trip_and_affect_revision_checksum() -> None:
    template_json = [
        {
            "dim_key": f"dimension_{index}",
            "label": f"Dimension {index}",
            "description": f"Dimension {index} 설명",
            "value_enums": ["낮음", "높음"],
            "display_order": index,
        }
        for index in range(1, 4)
    ]
    first_model = SimpleNamespace(
        scenario_dimension_template_id=81,
        template_json=template_json,
        event_type_definition="폭염 정의 v1",
        lng_price_impact_examples="LNG 가격 영향 사례",
    )
    revised_model = SimpleNamespace(
        scenario_dimension_template_id=81,
        template_json=template_json,
        event_type_definition="폭염 정의 v2",
        lng_price_impact_examples="LNG 가격 영향 사례",
    )
    session = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository.fetch_template_model",
            side_effect=[first_model, revised_model],
        ),
    ):
        first = ScenarioService()._load_template_record_from_db(8)
        revised = ScenarioService()._load_template_record_from_db(8)

    assert first["event_type_definition"] == "폭염 정의 v1"
    assert first["lng_price_impact_examples"] == "LNG 가격 영향 사례"
    assert first["template_json"][0]["description"] == "Dimension 1 설명"
    assert first["template_checksum"] != revised["template_checksum"]
    assert session.close.call_count == 2


def test_template_excel_migration_builds_domain_fields_and_descriptions(
    tmp_path: Path,
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "eventTypeL2Id",
            "이벤트 유형 정의",
            "LNG 가격 영향 대표 사례",
            "dimKey",
            "항목",
            "기준",
            "참고",
            "required",
            "valueEnums",
            "displayOrder",
        ],
    )
    for index in range(1, 4):
        sheet.append(
            [
                8,
                "폭염 정의",
                "대표 사례",
                f"heat_{index}",
                f"폭염 항목 {index}",
                "평년 대비 편차",
                "CDD 참고",
                "Y" if index == 1 else "N",
                "낮음|높음",
                index,
            ],
        )
    workbook_path = tmp_path / "scenario-template.xlsx"
    workbook.save(workbook_path)

    updates = load_template_updates(workbook_path)

    assert len(updates) == 1
    assert updates[0]["event_type_definition"] == "폭염 정의"
    assert updates[0]["lng_price_impact_examples"] == "대표 사례"
    assert updates[0]["template_json"][0]["description"] == ("폭염 항목 1 - 평년 대비 편차 - CDD 참고")
    assert updates[0]["template_json"][0]["value_enums"] == [
        "낮음",
        "높음",
    ]


def test_multi_event_rows_round_trip_pressure_role_and_rationale() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        dimension_selected=["tightness"],
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "description": "설명",
                "display_order": 1,
                "values": [],
            },
        ],
    )
    result = build_scenario_group_table_data(
        group.model_dump(),
        [
            {
                "scenario_id": 100,
                "title": "상단",
                "narrative": "설명",
                "dimension_values": {"tightness": "심화"},
                "probability_score": 30,
                "probability_delta": 0,
                "baseline_yn": "N",
                "global_pressure_band": "strong_bullish",
                "scenario_role": "ceiling",
                "global_pressure_rationale": "상승 근거",
            },
        ],
    )
    row = result.table.rows[0]
    assert row.pressure_target == "JKM"
    assert row.pressure_band == "strong_bullish"
    assert row.scenario_role == "ceiling"
    assert row.probability_score == 30
    assert row.pressure_rationale == "상승 근거"
    serialized = row.model_dump(by_alias=True)
    assert serialized["pressureTarget"] == "JKM"
    assert serialized["pressureBand"] == "strong_bullish"
    assert serialized["pressureRationale"] == "상승 근거"
    assert "globalPressureBand" not in serialized
    assert "globalPressureRationale" not in serialized


def test_v3_compact_definitions_round_trip_through_persistence_and_sync_response() -> None:
    finalized = finalize_generation_result(
        _result(strategy="multi_event_composite_dimensions"),
        generation_strategy="multi_event_composite_dimensions",
        event_ids=EVENT_IDS,
    )
    compact_definitions = [definition.model_dump() for definition in finalized.dimension_definitions]
    saved_group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=[definition.dimension_id for definition in finalized.dimension_definitions],
        dimension_definitions=compact_definitions,
    )
    saved_scenarios = [
        ScenarioPayload(
            scenario_id=index,
            scenario_group_id=10,
            title=scenario.title,
            narrative=scenario.narrative,
            dimension_values=scenario.dimension_values,
            probability_score=scenario.probability_score,
            baseline_yn=scenario.baseline_yn,
            global_pressure_band=scenario.pressure_band,
            scenario_role=scenario.scenario_role,
            global_pressure_rationale=scenario.pressure_rationale,
        )
        for index, scenario in enumerate(finalized.scenarios, start=100)
    ]
    template_dimensions = [
        {
            "label": f"dimension-{index}",
            "dim_key": f"dimension_{index}",
            "value_enums": ["낮음", "높음"],
            "display_order": index,
        }
        for index in range(1, 4)
    ]
    templates = [
        ScenarioPipelineTemplate(
            scenario_dimension_template_id=template_id,
            event_type_l2_id=event_type_id,
            template_checksum=checksum,
            dimensions=template_dimensions,
        )
        for template_id, event_type_id, checksum in (
            (81, 8, "checksum-8"),
            (121, 12, "checksum-12"),
        )
    ]
    prepared = {
        "scenario_group": saved_group,
        "events": [
            EventPayload(mi_event_id=101, event_type_l2_id=8),
            EventPayload(mi_event_id=202, event_type_l2_id=12),
        ],
        "templates": templates,
        "api_version": "v3",
        "generation_strategy": "multi_event_composite_dimensions",
        "user_id": 7,
    }

    async def run_graph(state: MultiEventGenerationState, **_kwargs: object) -> MultiEventGenerationState:
        graph_state = state.model_copy(update={"finalized_result": finalized})
        return graph_state.model_copy(update=multi_event_nodes.persist_generation(graph_state))

    graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=run_graph))

    with (
        patch.object(
            multi_event_flow,
            "get_compiled_graph",
            return_value=graph,
        ),
        patch.object(
            ScenarioGroupService,
            "persist_multi_event_generation",
            return_value=(saved_group, saved_scenarios),
        ) as persist,
    ):
        output = asyncio.run(
            multi_event_flow.run_multi_event_scenarios_inline(prepared),
        )

    assert persist.call_args.kwargs["dimension_definitions"] == compact_definitions
    serialized = output.model_dump(by_alias=True)
    response_definitions = serialized["data"]["dimensionDefinitions"]
    assert response_definitions == [
        definition.model_dump(by_alias=True) for definition in finalized.dimension_definitions
    ]
    assert "displayOrder" not in response_definitions[0]
    assert "sourceAssignments" not in response_definitions[0]["values"][0]


def test_v2_compact_contract_round_trips_through_persistence_and_sync_response() -> None:
    finalized = finalize_generation_result(
        _result(strategy="multi_event_source_dimensions"),
        generation_strategy="multi_event_source_dimensions",
        event_ids=EVENT_IDS,
    )
    compact_definitions = [definition.model_dump() for definition in finalized.dimension_definitions]
    saved_group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v2",
        generation_strategy="multi_event_source_dimensions",
        dimension_selected=[definition.dimension_id for definition in finalized.dimension_definitions],
        dimension_definitions=compact_definitions,
    )
    saved_scenarios = [
        ScenarioPayload(
            scenario_id=index,
            scenario_group_id=10,
            title=scenario.title,
            narrative=scenario.narrative,
            dimension_values=scenario.dimension_values,
            probability_score=scenario.probability_score,
            baseline_yn=scenario.baseline_yn,
            global_pressure_band=scenario.pressure_band,
            scenario_role=scenario.scenario_role,
            global_pressure_rationale=scenario.pressure_rationale,
        )
        for index, scenario in enumerate(finalized.scenarios, start=100)
    ]
    prepared = {
        "scenario_group": saved_group,
        "events": [
            EventPayload(mi_event_id=101, event_type_l2_id=8),
            EventPayload(mi_event_id=202, event_type_l2_id=12),
        ],
        "templates": [
            ScenarioPipelineTemplate(
                scenario_dimension_template_id=template_id,
                event_type_l2_id=event_type_id,
                template_checksum=checksum,
                dimensions=[
                    {
                        "label": f"dimension-{index}",
                        "dim_key": f"dimension_{index}",
                        "value_enums": ["낮음", "높음"],
                        "display_order": index,
                    }
                    for index in range(1, 4)
                ],
            )
            for template_id, event_type_id, checksum in (
                (81, 8, "checksum-8"),
                (121, 12, "checksum-12"),
            )
        ],
        "api_version": "v2",
        "generation_strategy": "multi_event_source_dimensions",
        "user_id": 7,
    }

    async def run_graph(state: MultiEventGenerationState, **_kwargs: object) -> MultiEventGenerationState:
        graph_state = state.model_copy(update={"finalized_result": finalized})
        return graph_state.model_copy(update=multi_event_nodes.persist_generation(graph_state))

    graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=run_graph))

    with (
        patch.object(
            multi_event_flow,
            "get_compiled_graph",
            return_value=graph,
        ),
        patch.object(
            ScenarioGroupService,
            "persist_multi_event_generation",
            return_value=(saved_group, saved_scenarios),
        ) as persist,
    ):
        output = asyncio.run(
            multi_event_flow.run_multi_event_scenarios_inline(prepared),
        )

    assert persist.call_args.kwargs["dimension_definitions"] == compact_definitions
    assert set(persist.call_args.kwargs["generation_diagnostics"]) == {
        "target_pressure_bands",
        "event_shocks",
        "unselected_dimension_refs",
        "unrepresented_pressure_bands",
    }
    serialized = output.model_dump(by_alias=True)
    response_definitions = serialized["data"]["dimensionDefinitions"]
    assert response_definitions == [
        definition.model_dump(by_alias=True) for definition in finalized.dimension_definitions
    ]
    assert set(response_definitions[0]) == {
        "dimensionId",
        "label",
        "description",
        "required",
        "selectionCriterion",
        "selectionRationale",
        "sourceRef",
        "values",
    }
    assert "sourceAssignments" not in response_definitions[0]["values"][0]
    assert set(serialized["data"]["generationDiagnostics"]) == {
        "targetPressureBands",
        "eventShocks",
        "unselectedDimensionRefs",
        "unrepresentedPressureBands",
    }


def test_v3_compact_dimension_array_order_controls_table_headers() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["zeta", "alpha"],
        dimension_definitions=[
            {
                "dimension_id": dimension_id,
                "label": label,
                "description": "설명",
                "rationale": "Event 사실과 LNG 가격 영향 근거",
                "source_event_ids": [101],
                "source_refs": [
                    {
                        "scenario_dimension_template_id": 81,
                        "dim_key": dimension_id,
                    },
                ],
                "values": [],
            }
            for dimension_id, label in (("zeta", "첫 번째"), ("alpha", "두 번째"))
        ],
    )

    result = build_scenario_group_table_data(
        group.model_dump(),
        [
            {
                "scenario_id": 100,
                "title": "배열 순서",
                "dimension_values": {"zeta": "값 1", "alpha": "값 2"},
            },
        ],
    )

    assert [header.key for header in result.table.headers] == ["zeta", "alpha"]


def test_v3_table_preserves_canonical_value_id() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["europe_gas_pull"],
        dimension_definitions=[
            {
                "dimension_id": "europe_gas_pull",
                "label": "유럽 가스 대체수요",
                "description": "설명",
                "source_event_ids": [1342],
                "source_refs": [
                    {
                        "scenario_dimension_template_id": 5,
                        "dim_key": "capacity_change_scale",
                    },
                ],
                "values": [
                    {
                        "value_id": "eu_nuke_v3",
                        "label": "3~5GW 감발·흡수 25%",
                    },
                ],
            },
        ],
    )

    result = build_scenario_group_table_data(
        group.model_dump(),
        [
            {
                "scenario_id": 100,
                "title": "유럽 LNG 수요 확대",
                "dimension_values": {"europe_gas_pull": "eu_nuke_v3"},
            },
        ],
    )

    assert result.table.rows[0].cells == {"europe_gas_pull": "eu_nuke_v3"}


def test_validation_creates_pending_mapping_for_free_value() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["tightness"],
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "description": "설명",
                "source_event_ids": [101],
                "source_refs": [
                    {
                        "scenario_dimension_template_id": 81,
                        "dim_key": "heat",
                    },
                ],
                "values": [{"value_id": "known", "label": "기존 값"}],
            },
        ],
    )
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=group,
        request_table={
            "headers": [
                {"key": "tightness", "label": "수급 긴축", "display_order": 1},
            ],
            "rows": [
                {
                    "scenario_id": 100,
                    "cells": {"tightness": "사용자 자유 값"},
                },
            ],
        },
    )
    saved = [
        {
            "dimension_value_id": "dv_test",
            "dimension_id": "tightness",
            "display_value": "사용자 자유 값",
            "mapping_version": 1,
            "status": "pending",
        },
    ]
    with (
        patch.object(
            ScenarioService,
            "save_mapping_proposals",
            return_value=saved,
        ) as save,
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioGroupService.set_parameter_mapping_ready",
        ) as set_ready,
    ):
        update = create_mapping_proposals(state)

    assert update["mapping_proposals"] == saved
    assert update["parameter_mapping_ready"] is False
    proposal = save.call_args.args[1][0]
    assert proposal["display_value"] == "사용자 자유 값"
    assert proposal["source_projections"][0]["source_type"] == "derived_interpretation"
    assert proposal["source_projections"][0]["scenario_dimension_template_id"] == 81
    assert proposal["mapping_proposal"]["candidateSourceDimensions"] == [
        {"scenarioDimensionTemplateId": 81, "dimKey": "heat"},
    ]
    set_ready.assert_called_once_with(10, ready=False, user_id=7)


def test_v2_validation_uses_compact_source_ref_identity_for_mapping() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v2",
        generation_strategy="multi_event_source_dimensions",
        dimension_selected=["e101__heat"],
        dimension_definitions=[
            {
                "dimension_id": "e101__heat",
                "label": "수급 긴축",
                "description": "설명",
                "source_ref": {
                    "event_id": 101,
                    "scenario_dimension_template_id": 81,
                    "dim_key": "heat",
                },
                "values": [{"value_id": "known", "label": "기존 값"}],
            },
        ],
    )
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=group,
        request_table={
            "headers": [
                {"key": "e101__heat", "label": "수급 긴축", "display_order": 1},
            ],
            "rows": [
                {
                    "scenario_id": 100,
                    "cells": {"e101__heat": "사용자 자유 값"},
                },
            ],
        },
    )
    saved = [
        {
            "dimension_value_id": "dv_test",
            "dimension_id": "e101__heat",
            "display_value": "사용자 자유 값",
            "mapping_version": 1,
            "status": "pending",
        },
    ]
    with (
        patch.object(
            ScenarioService,
            "save_mapping_proposals",
            return_value=saved,
        ) as save,
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioGroupService.set_parameter_mapping_ready",
        ),
    ):
        update = create_mapping_proposals(state)

    assert update["mapping_proposals"] == saved
    proposal = save.call_args.args[1][0]
    assert proposal["source_projections"] == [
        {
            "event_id": 101,
            "scenario_dimension_template_id": 81,
            "dim_key": "heat",
            "value": "사용자 자유 값",
        },
    ]
    assert proposal["mapping_proposal"]["candidateSourceDimensions"] == [
        {
            "eventId": 101,
            "scenarioDimensionTemplateId": 81,
            "dimKey": "heat",
        },
    ]


def test_validation_keeps_parameter_mapping_ready_for_approved_free_value() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["tightness"],
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "description": "설명",
                "source_event_ids": [101],
                "source_refs": [
                    {
                        "scenario_dimension_template_id": 81,
                        "dim_key": "heat",
                    },
                ],
                "values": [{"value_id": "known", "label": "기존 값"}],
            },
        ],
    )
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=group,
        request_table={
            "headers": [
                {
                    "key": "tightness",
                    "label": "수급 긴축",
                    "display_order": 1,
                },
            ],
            "rows": [
                {
                    "scenario_id": 100,
                    "cells": {"tightness": "승인된 자유 값"},
                },
            ],
        },
    )
    saved = [
        {
            "dimension_value_id": "dv_test",
            "dimension_id": "tightness",
            "display_value": "승인된 자유 값",
            "mapping_version": 1,
            "status": "approved",
        },
    ]
    with (
        patch.object(
            ScenarioService,
            "save_mapping_proposals",
            return_value=saved,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioGroupService.set_parameter_mapping_ready",
        ) as set_ready,
    ):
        update = create_mapping_proposals(state)

    assert update["parameter_mapping_ready"] is True
    set_ready.assert_called_once_with(10, ready=True, user_id=7)


def test_multi_event_compatibility_does_not_treat_values_as_closed_enum() -> None:
    context = build_context(
        group={
            "generation_strategy": ("multi_event_composite_dimensions"),
            "dimension_selected": ["tightness"],
        },
        requested_rows=[
            {
                "scenario_id": 100,
                "title": "자유값 조합",
                "narrative": "현재 Event에 맞춘 자유값 조합",
                "cells": {"tightness": "사용자 자유 값"},
                "metrics": {"probability_score": 60},
            },
        ],
        persisted_scenarios=[],
        template_dims=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "enum": [
                    {
                        "id": "known",
                        "label": "기존 생성 값",
                    },
                ],
            },
        ],
    )
    incompatible = [
        CompatibilityItem(
            scenario_id=100,
            compatible=False,
            reason="자유값 조합이 다른 dimension과 모순된다.",
            conflict_dim_a="다른 분기",
            conflict_value_a="심화",
            conflict_dim_b="tightness",
            conflict_value_b="사용자 자유 값",
            recommended_value_b="새로운 자연스러운 값",
        ),
    ]

    assert not _has_only_unusable_enum_recommendations(
        context,
        incompatible,
    )


def test_multi_event_compatibility_prompt_requires_cartesian_event_coverage() -> None:
    assert "Scenario와 Shared Event 조합" in MULTI_EVENT_COMPAT_SYSTEM_PROMPT
    assert "event_coverage" in MULTI_EVENT_COMPAT_SYSTEM_PROMPT
    assert "scenario_id, event_id, grounded, reason" in MULTI_EVENT_COMPAT_SYSTEM_PROMPT
    assert "closed enum이 아닙니다" in MULTI_EVENT_COMPAT_SYSTEM_PROMPT


def test_mapping_proposal_sync_deactivates_values_no_longer_in_the_table() -> None:
    session = Mock()
    repository = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=repository,
        ),
    ):
        saved = ScenarioService().save_mapping_proposals(
            10,
            [],
            7,
        )

    assert saved == []
    repository.deactivate_mappings_except.assert_called_once_with(
        10,
        set(),
        7,
    )
    session.commit.assert_called_once()


def test_mapping_approval_rejects_stale_version() -> None:
    mapping = Mock(
        mapping_version=2,
        dimension_value_id="dv_test",
        status="pending",
    )
    session = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service."
            "ScenarioRepository.fetch_mapping_by_value_id",
            return_value=mapping,
        ),
    ):
        with pytest.raises(MIBaseError, match="Stale mapping version"):
            ScenarioService().decide_mapping_proposals(
                10,
                [
                    {
                        "dimension_value_id": "dv_test",
                        "mapping_version": 1,
                        "decision": "approve",
                    },
                ],
                7,
            )
    session.rollback.assert_called_once()


def _scenario_group_model(*, summary: str | None, api_version: str = "v4") -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_id=99,
        request_usr_id=7,
        title="준비 중인 시나리오 그룹",
        summary=summary,
        description=None,
        dimension_selected=[],
        scenario_count=0,
        status="creating",
        stage="ready",
        api_version=api_version,
        generation_strategy=(
            "multi_event_model_lever_dimensions" if api_version == "v4" else "multi_event_composite_dimensions"
        ),
        impact_catalog_version="v1" if api_version == "v4" else None,
        impact_catalog_checksum="catalog-checksum" if api_version == "v4" else None,
        template_checksum=None,
        parameter_mapping_ready=api_version == "v4",
        dimension_definitions=[],
        generation_diagnostics={},
    )


def test_prepare_v4_group_keeps_summary_null_until_generation_completes() -> None:
    session = Mock()
    repository = Mock()
    repository.insert_group.return_value = 99
    repository.fetch_single_active_group_event.return_value = None
    repository.fetch_by_id.return_value = _scenario_group_model(summary=None)
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=repository,
        ),
    ):
        group = ScenarioGroupService().prepare_v4_multi_event_group(
            events=[
                {"mi_event_id": 101, "event_type_l2_id": 8},
                {"mi_event_id": 202, "event_type_l2_id": 12},
            ],
            impact_catalog_version="v1",
            impact_catalog_checksum="catalog-checksum",
            user_id=7,
        )

    assert repository.insert_group.call_args.args[0]["summary"] is None
    assert group.summary is None


def test_persist_multi_event_generation_updates_optional_summary() -> None:
    session = Mock()
    group = _scenario_group_model(summary=None)
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.fetch_single_active_group_event.return_value = None
    group_repository.update_group.side_effect = lambda target, payload: [
        setattr(target, key, value) for key, value in payload.items()
    ]
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.return_value = []
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
    ):
        saved_group, _saved_scenarios = ScenarioGroupService().persist_multi_event_generation(
            scenario_group_id=99,
            title="동북아 한파와 미국 액화시설 중단",
            summary="한파 수요와 액화시설 공급 차질의 지속·회복 경로를 비교한다.",
            description="이벤트 사실 문장이다. 검증된 인과 분기 문장이다.",
            dimension_definitions=[],
            generation_diagnostics={},
            scenarios=[],
            user_id=7,
        )

    update = group_repository.update_group.call_args.args[1]
    assert update["summary"] == "한파 수요와 액화시설 공급 차질의 지속·회복 경로를 비교한다."
    assert saved_group.summary == update["summary"]


def test_persist_multi_event_generation_preserves_summary_when_omitted() -> None:
    session = Mock()
    group = _scenario_group_model(summary="기존 v3 summary", api_version="v3")
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.fetch_single_active_group_event.return_value = None
    group_repository.update_group.side_effect = lambda target, payload: [
        setattr(target, key, value) for key, value in payload.items()
    ]
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.return_value = []
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
    ):
        saved_group, _saved_scenarios = ScenarioGroupService().persist_multi_event_generation(
            scenario_group_id=99,
            title="v3 생성 제목",
            description="v3 생성 설명",
            dimension_definitions=[],
            generation_diagnostics={},
            scenarios=[],
            user_id=7,
        )

    update = group_repository.update_group.call_args.args[1]
    assert "summary" not in update
    assert saved_group.summary == "기존 v3 summary"


def test_multi_event_group_has_no_fake_representative_event_and_keeps_order() -> None:
    session = Mock()
    repository = Mock()
    repository.insert_group.return_value = 99
    repository.fetch_single_active_group_event.return_value = None
    repository.fetch_by_id.return_value = SimpleNamespace(
        scenario_group_id=99,
        mi_event_id=None,
        event_type_l2_id=None,
        request_usr_id=7,
        title="Multi-event scenario group (2 events)",
        summary="복수 MI Event 공동 전제 시나리오",
        description=None,
        dimension_selected=[],
        scenario_count=0,
        status="creating",
        stage="ready",
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        comparison_run_id=None,
        template_checksum="aggregate",
        parameter_mapping_ready=False,
        dimension_definitions=[],
        generation_diagnostics={},
    )
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    events = [
        {"mi_event_id": 101, "event_type_l2_id": 8},
        {"mi_event_id": 202, "event_type_l2_id": 12},
    ]
    templates = [
        {
            "scenario_dimension_template_id": 81,
            "template_checksum": "checksum-8",
        },
        {
            "scenario_dimension_template_id": 121,
            "template_checksum": "checksum-12",
        },
    ]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=repository,
        ),
    ):
        group = ScenarioGroupService().prepare_multi_event_group(
            events=events,
            templates=templates,
            api_version="v3",
            generation_strategy="multi_event_composite_dimensions",
            user_id=7,
        )

    inserted_group = repository.insert_group.call_args.args[0]
    assert "mi_event_id" not in inserted_group
    assert "event_type_l2_id" not in inserted_group
    assert inserted_group["comparison_run_id"] is None
    assert group.mi_event_id is None
    assert [call.args[0]["mi_event_id"] for call in repository.insert_group_event.call_args_list] == EVENT_IDS
    assert [call.args[0]["template_checksum"] for call in repository.insert_group_event.call_args_list] == [
        "checksum-8",
        "checksum-12",
    ]
    session.commit.assert_called_once()


def test_multi_event_group_does_not_lookup_comparison_run() -> None:
    session = Mock()
    repository = Mock()
    repository.insert_group.return_value = 99
    repository.fetch_single_active_group_event.return_value = None
    repository.fetch_by_id.return_value = SimpleNamespace(
        scenario_group_id=99,
        mi_event_id=None,
        event_type_l2_id=None,
        request_usr_id=7,
        title="Multi-event scenario group (2 events)",
        summary="복수 MI Event 공동 전제 시나리오",
        description=None,
        dimension_selected=[],
        scenario_count=0,
        status="creating",
        stage="ready",
        api_version="v2",
        generation_strategy="multi_event_source_dimensions",
        comparison_run_id=None,
        template_checksum="aggregate",
        parameter_mapping_ready=False,
        dimension_definitions=[],
        generation_diagnostics={},
    )
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=repository,
        ),
    ):
        ScenarioGroupService().prepare_multi_event_group(
            events=[
                {"mi_event_id": 101, "event_type_l2_id": 8},
                {"mi_event_id": 202, "event_type_l2_id": 12},
            ],
            templates=[
                {
                    "scenario_dimension_template_id": 81,
                    "template_checksum": "checksum-8",
                },
                {
                    "scenario_dimension_template_id": 121,
                    "template_checksum": "checksum-12",
                },
            ],
            api_version="v2",
            generation_strategy="multi_event_source_dimensions",
            user_id=7,
        )

    assert repository.insert_group.call_args.args[0]["comparison_run_id"] is None
    session.commit.assert_called_once()


def test_versioned_sync_and_mapping_routes_are_registered() -> None:
    paths = {route.path for route in agent_router.routes}
    assert "/v1/scenario-groups/sync" not in paths
    assert "/v2/scenario-groups/sync" in paths
    assert "/v3/scenario-groups/sync" in paths
    assert "/scenario-groups/{scenario_group_id}/dimension-mapping-approvals" in paths


def test_mapping_approval_endpoint_does_not_invoke_llm() -> None:
    app = FastAPI()
    app.include_router(router)
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        parameter_mapping_ready=False,
    )
    approved_group = group.model_copy(
        update={"parameter_mapping_ready": True},
    )
    with (
        patch.object(
            ScenarioService,
            "decide_mapping_proposals",
            return_value=[
                {
                    "dimension_value_id": "dv_test",
                    "mapping_version": 1,
                    "status": "approved",
                },
            ],
        ) as decide,
        patch(
            "apps.agents.scenario_group_agent.routers.scenario_generation.ScenarioGroupService.load_by_id",
            side_effect=[group, approved_group],
        ),
    ):
        response = TestClient(app).post(
            "/scenario-groups/10/dimension-mapping-approvals",
            json={
                "userId": 7,
                "decisions": [
                    {
                        "dimensionValueId": "dv_test",
                        "mappingVersion": 1,
                        "decision": "approve",
                    },
                ],
            },
        )

    assert response.status_code == 200
    assert response.json()["data"]["parameterMappingReady"] is True
    decide.assert_called_once()


def test_confirmation_uses_stored_multi_event_dimensions() -> None:
    session = Mock()
    group = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=7,
        generation_strategy="multi_event_composite_dimensions",
        parameter_mapping_ready=True,
        dimension_selected=["tightness"],
        dimension_definitions=[
            {
                "dimension_id": "tightness",
                "label": "수급 긴축",
                "values": [
                    {"value_id": "tightness_v1", "label": "사용자 승인 값"},
                ],
            },
        ],
        event_type_l2_id=None,
    )
    scenario = SimpleNamespace(
        scenario_id=100,
        probability_score=60,
        display_order=1,
        baseline_yn="Y",
        mod_usr_logn_id=7,
        dimension_values={"tightness": "tightness_v1"},
    )
    signpost = SimpleNamespace(
        signpost_id=1000,
        scenario_id=100,
    )
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.create_confirmation_snapshot.return_value = 500
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "created",
        "stage": "completed",
    }
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.return_value = [scenario]
    signpost_repository = Mock()
    signpost_repository.fetch_models_by_scenario_ids.return_value = [
        signpost,
    ]
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.SignpostRepository",
            return_value=signpost_repository,
        ),
        patch.object(
            ScenarioService,
            "cells_to_dimension_values",
        ) as legacy_cell_mapping,
    ):
        result = ScenarioGroupService().apply_confirmation(
            10,
            {"title": "복수 Event 확정"},
            {
                "headers": [{"key": "tightness", "label": "수급 긴축", "display_order": 1}],
                "rows": [
                    {
                        "scenario_id": 100,
                        "cells": {"tightness": "tightness_v1"},
                        "metrics": {
                            "probability_score": 60,
                            "probability_delta": 0,
                        },
                        "signposts": [
                            {
                                "signpost_id": 1000,
                                "label": "관찰 지표",
                            },
                        ],
                    },
                ],
            },
            user_id=7,
        )

    assert result["status"] == "success"
    scenario_update = scenario_repository.update_from_payload.call_args.args[1]
    assert "dimension_values" not in scenario_update
    legacy_cell_mapping.assert_not_called()
    group_repository.create_confirmation_snapshot.assert_called_once()
    session.commit.assert_called_once()


def test_confirmation_waits_for_multi_event_mapping_approval() -> None:
    session = Mock()
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = SimpleNamespace(
        request_usr_id=7,
        generation_strategy="multi_event_source_dimensions",
        parameter_mapping_ready=False,
    )
    scenario_repository = Mock()
    connection_module = ModuleType(
        "apps.common.configs.database.sync_database.connection",
    )
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": (connection_module),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
    ):
        result = ScenarioGroupService().apply_confirmation(
            10,
            {},
            {"rows": []},
            user_id=7,
        )

    assert result == {
        "status": "failure",
        "message": "Dimension value mapping approvals are not complete",
    }
    scenario_repository.fetch_models_by_group_id.assert_not_called()
    session.commit.assert_not_called()


def test_multi_event_signpost_context_preserves_every_event() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
    )
    events = [
        EventPayload.model_validate(
            {
                "mi_event_id": 101,
                "event_type_l2_id": 8,
                "event_title_ko": "폭염",
                "one_line_summary": "아시아 폭염",
                "key_bullets": ["수요 증가"],
                "tags": ["아시아"],
                "occurred_at": "2026-07-01",
            },
        ),
        EventPayload.model_validate(
            {
                "mi_event_id": 202,
                "event_type_l2_id": 12,
                "event_title_ko": "재고 부족",
                "one_line_summary": "유럽 재고 부족",
                "key_bullets": ["구매 경쟁"],
                "tags": ["유럽"],
                "occurred_at": "2026-07-02",
            },
        ),
    ]
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_event_ids",
            return_value=EVENT_IDS,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.EventService.load_events",
            return_value=events,
        ),
    ):
        context = _load_group_event_context(group)

    assert context is not None
    assert context.mi_event_id == "101,202"
    assert context.event_title_ko == "폭염 + 재고 부족"
    assert context.key_bullets == [
        "[Event 101] 수요 증가",
        "[Event 202] 구매 경쟁",
    ]
    assert context.tags == ["아시아", "유럽"]


def test_multi_event_signpost_table_sync_uses_stored_dimension_definitions() -> None:
    definitions = [
        {
            "dimension_id": "tightness",
            "label": "수급 긴축",
            "description": "설명",
            "display_order": 1,
            "values": [],
        },
    ]
    state = CreateSignpostsState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            api_version="v3",
            generation_strategy="multi_event_composite_dimensions",
            dimension_selected=["tightness"],
            dimension_definitions=definitions,
        ),
        request_table={
            "headers": [
                {"key": "tightness", "label": "수급 긴축", "displayOrder": 1},
            ],
            "rows": [
                {
                    "scenarioId": 100,
                    "displayOrder": 1,
                    "title": "혼합",
                    "cells": {"tightness": "균형"},
                },
            ],
        },
    )
    sync_result = {
        "active_scenario_ids": [100],
        "regenerate_scenario_ids": [],
        "inserted_scenario_ids": [],
        "updated_scenario_ids": [],
        "deleted_scenario_ids": [],
        "unchanged_existing_scenario_ids": [100],
    }
    with (
        patch.object(
            ScenarioService,
            "sync_from_table",
            return_value=sync_result,
        ) as sync,
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_by_id",
            return_value=state.scenario_group,
        ),
    ):
        update = sync_scenarios_from_table(state)

    assert update["signpost_target_scenario_ids"] == []
    assert sync.call_args.kwargs["event_type_l2_id"] is None
    assert sync.call_args.kwargs["dimension_definitions"] == definitions


def test_signpost_uses_combined_context_for_multi_event_group() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        mi_event_id=None,
        event_type_l2_id=None,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
    )
    events = [
        EventPayload(
            mi_event_id=101,
            event_type_l2_id=8,
            event_title_ko="폭염",
            one_line_summary="냉방 수요 증가",
            key_bullets=["기온 상승"],
            tags=["아시아"],
        ),
        EventPayload(
            mi_event_id=202,
            event_type_l2_id=12,
            event_title_ko="재고 부족",
            one_line_summary="유럽 재고 긴축",
            key_bullets=["재고 하락"],
            tags=["유럽"],
        ),
    ]
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_event_ids",
            return_value=EVENT_IDS,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.EventService.load_events",
            return_value=events,
        ),
    ):
        combined = _load_group_event_context(group)

    assert combined is not None
    assert combined.mi_event_id == "101,202"
    assert combined.event_title_ko == "폭염 + 재고 부족"
    assert combined.key_bullets == [
        "[Event 101] 기온 상승",
        "[Event 202] 재고 하락",
    ]
    assert combined.tags == ["아시아", "유럽"]


def test_signpost_table_sync_uses_stored_multi_event_dimensions() -> None:
    definitions = [
        {
            "dimension_id": "tightness",
            "label": "수급 긴축",
            "description": "설명",
            "display_order": 1,
            "source_refs": [_source(101, "heat")],
            "values": [{"value_id": "high", "label": "심화"}],
        },
    ]
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        request_usr_id=7,
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        dimension_selected=["tightness"],
        dimension_definitions=definitions,
    )
    state = CreateSignpostsState(
        scenario_group_id=10,
        user_id=7,
        scenario_group=group,
        request_table={
            "headers": [
                {"key": "tightness", "label": "수급 긴축", "display_order": 1},
            ],
            "rows": [
                {
                    "scenario_id": 100,
                    "cells": {"tightness": "심화"},
                },
            ],
        },
    )
    sync_result = {
        "active_scenario_ids": [100],
        "regenerate_scenario_ids": [],
        "inserted_scenario_ids": [],
        "updated_scenario_ids": [],
        "deleted_scenario_ids": [],
        "unchanged_existing_scenario_ids": [100],
    }
    with (
        patch.object(
            ScenarioService,
            "sync_from_table",
            return_value=sync_result,
        ) as sync,
        patch(
            "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_by_id",
            return_value=group,
        ),
    ):
        sync_scenarios_from_table(state)

    assert sync.call_args.kwargs["event_type_l2_id"] is None
    assert sync.call_args.kwargs["dimension_definitions"] == definitions
