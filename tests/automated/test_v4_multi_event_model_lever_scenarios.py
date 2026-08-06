from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from openai import pydantic_function_tool
import pytest

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import (
    v4_flow as v4_flow_module,
    v4_nodes,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import (
    V4MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_flow import (
    run_v4_multi_event_scenarios_inline,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDefinition,
    V4DimensionDesignResult,
    V4DimensionValueDefinition,
    V4EventGrounding,
    V4ExcludedScenarioCandidate,
    V4GenerationResult,
    V4LeverMapping,
    V4ScenarioCandidate,
    V4ScenarioSynthesisResult,
    finalize_v4_generation_result,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    build_model_lever_user_prompt,
    build_v4_scenario_synthesis_user_prompt,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.model_parameter.schema import (
    ModelImpactLeverParameterBinding,
    ModelImpactLeverPayload,
)
from apps.persistence.scenario.schema import RelatedMarket


def _lever(
    *,
    lever_id: int,
    code: str,
    domain: str,
    support_status: str | None,
) -> ModelImpactLeverPayload:
    bindings = (
        []
        if support_status is None
        else [
            ModelImpactLeverParameterBinding(
                parameter_name=f"Parameter{lever_id}",
                support_status=support_status,
                unsupported_reason_code=("INACTIVE_MODEL_PARAMETER" if support_status == "known_unsupported" else None),
            ),
        ]
    )
    return ModelImpactLeverPayload(
        impact_lever_id=lever_id,
        lever_code=code,
        domain=domain,
        label=code,
        description=f"{code} description",
        parameter_bindings=bindings,
        catalog_version="v1",
    )


def _dimension(
    *,
    dimension_id: str,
    event_id: int,
    lever_code: str,
    impact_lever_id: int | None = None,
) -> V4DimensionDefinition:
    return V4DimensionDefinition(
        dimension_id=dimension_id,
        label=dimension_id,
        description=f"{dimension_id} description",
        dimension_type="magnitude",
        value_kind="categorical",
        event_groundings=[
            V4EventGrounding(
                event_id=event_id,
                observed_basis=f"Event {event_id}에서 확인된 시장 사실",
                uncertainty=f"{dimension_id}의 강도와 지속 기간",
            ),
        ],
        lever_mappings=[
            V4LeverMapping(
                impact_lever_id=impact_lever_id,
                lever_code=lever_code,
                mapping_rationale="dimension 불확실성을 이 영향 레버로 연결한다.",
            ),
        ],
        values=[
            V4DimensionValueDefinition(
                value_id="low",
                label="낮음",
                global_pressure_contribution="글로벌 LNG 가격 하방 기여",
                assumption_rationale="영향 강도가 제한적이라고 가정한다.",
            ),
            V4DimensionValueDefinition(
                value_id="high",
                label="높음",
                global_pressure_contribution="글로벌 LNG 가격 상방 기여",
                assumption_rationale="영향 강도가 확대된다고 가정한다.",
            ),
        ],
    )


def _valid_result() -> V4GenerationResult:
    return V4GenerationResult(
        group_title="글로벌 LNG 복수 이벤트 시나리오",
        group_description="이벤트 결합에 따른 글로벌 LNG 가격 범위",
        interactions=[
            {
                "event_ids": [101, 202],
                "relation": "amplification",
                "rationale": "수요 증가와 공급 제약이 가격 압력을 증폭한다.",
            },
        ],
        dimension_definitions=[
            _dimension(
                dimension_id="cold_wave_intensity",
                event_id=101,
                lever_code="weather_demand",
            ),
            _dimension(
                dimension_id="liquefaction_recovery",
                event_id=202,
                lever_code="liquefaction_availability",
            ),
            _dimension(
                dimension_id="risk_premium",
                event_id=202,
                lever_code="financial_market_sentiment",
            ),
        ],
        scenarios=[
            V4ScenarioCandidate(
                title="상단",
                narrative="수요 증가와 공급 회복 지연",
                dimension_values={
                    "cold_wave_intensity": "high",
                    "liquefaction_recovery": "low",
                    "risk_premium": "high",
                },
                global_pressure_band="strong_bullish",
                global_pressure_rationale="글로벌 LNG 상승 압력",
                related_markets=[
                    RelatedMarket(
                        market="JKM",
                        rationale="아시아향 화물 전환 가능성이 특별히 중요함",
                    ),
                ],
                probability_score=35,
            ),
            V4ScenarioCandidate(
                title="혼합",
                narrative="수요 증가는 있으나 공급은 빠르게 회복",
                dimension_values={
                    "cold_wave_intensity": "high",
                    "liquefaction_recovery": "high",
                    "risk_premium": "low",
                },
                global_pressure_band="balanced",
                global_pressure_rationale="상승·하락 요인 상쇄",
                probability_score=50,
                mixed_factors=["한파 수요 증가", "액화시설 조기 회복"],
            ),
            V4ScenarioCandidate(
                title="하단",
                narrative="한파가 약하고 공급이 빠르게 회복",
                dimension_values={
                    "cold_wave_intensity": "low",
                    "liquefaction_recovery": "high",
                    "risk_premium": "low",
                },
                global_pressure_band="strong_bearish",
                global_pressure_rationale="글로벌 LNG 하락 압력",
                probability_score=15,
            ),
        ],
        excluded_scenarios=[
            V4ExcludedScenarioCandidate(
                global_pressure_band="bullish",
                reason_code="LOW_DISTINCTIVENESS",
                reason="상단 시나리오와 독립적인 검토 가치가 낮음",
            ),
            V4ExcludedScenarioCandidate(
                global_pressure_band="bearish",
                reason_code="LOW_DISTINCTIVENESS",
                reason="하단 시나리오와 독립적인 검토 가치가 낮음",
            ),
        ],
    )


def _catalog() -> list[ModelImpactLeverPayload]:
    return [
        _lever(lever_id=1, code="weather_demand", domain="demand", support_status="executable"),
        _lever(
            lever_id=2,
            code="liquefaction_availability",
            domain="supply",
            support_status="known_unsupported",
        ),
        _lever(
            lever_id=3,
            code="financial_market_sentiment",
            domain="price_only",
            support_status=None,
        ),
        _lever(lever_id=4, code="direct_gas_demand", domain="demand", support_status=None),
    ]


def test_v4_request_requires_two_to_five_unique_events() -> None:
    payload = V4MultiEventCreateScenariosIn(mi_event_ids=[101, 202], user_id=7)

    assert payload.mi_event_ids == [101, 202]
    assert "targetMarket" not in V4MultiEventCreateScenariosIn.model_json_schema(by_alias=True)["properties"]
    with pytest.raises(ValueError):
        V4MultiEventCreateScenariosIn(mi_event_ids=[101, 101], user_id=7)


def test_v4_sync_and_background_routes_are_registered() -> None:
    from apps.agents.scenario_group_agent.api import router

    paths = {route.path for route in router.routes if "POST" in getattr(route, "methods", set())}

    assert "/v4/scenario-groups" in paths
    assert "/v4/scenario-groups/sync" in paths


def test_v4_storage_uses_scenario_related_markets_without_group_target_market() -> None:
    from apps.persistence.scenario.models import MiScenarioModel
    from apps.persistence.scenario_group.models import MiScenarioGroupModel, MiScenarioSnapModel

    assert "target_market" not in MiScenarioGroupModel.__table__.columns
    assert "related_markets" in MiScenarioModel.__table__.columns
    assert "related_markets" in MiScenarioSnapModel.__table__.columns


def test_v4_finalizer_hydrates_levers_assigns_roles_and_computes_coverage() -> None:
    result, coverage = finalize_v4_generation_result(
        _valid_result(),
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )

    assert [scenario.scenario_role for scenario in result.scenarios] == ["ceiling", "mixed", "floor"]
    assert result.scenarios[1].baseline_yn is True
    assert result.dimension_definitions[0].model_support_status == "full"
    assert result.dimension_definitions[1].model_support_status == "none"
    assert result.dimension_definitions[2].model_support_status == "price_only"
    assert result.dimension_definitions[0].event_groundings[0].event_id == 101
    assert result.dimension_definitions[0].lever_mappings[0].impact_lever_id == 1
    assert coverage.coverage_status == "partial"
    assert coverage.covered_dimension_ids == ["cold_wave_intensity"]
    assert coverage.uncovered_dimension_ids == ["liquefaction_recovery", "risk_premium"]


def test_v4_finalizer_derives_mixed_role_from_actual_contributions() -> None:
    draft = _valid_result()
    for scenario in draft.scenarios:
        scenario.mixed_factors = []

    result, _coverage = finalize_v4_generation_result(
        draft,
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )

    assert [scenario.scenario_role for scenario in result.scenarios] == ["ceiling", "mixed", "floor"]


def test_v4_finalizer_rejects_mixed_factors_without_two_pressure_directions() -> None:
    draft = _valid_result()
    mixed = draft.scenarios[1]
    mixed.dimension_values = {dimension.dimension_id: "high" for dimension in draft.dimension_definitions}

    with pytest.raises(ValueError, match="mixedFactors requires bullish and bearish"):
        finalize_v4_generation_result(
            draft,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_rejects_pressure_band_contribution_contradiction() -> None:
    draft = _valid_result()
    floor = draft.scenarios[-1]
    floor.dimension_values = {dimension.dimension_id: "high" for dimension in draft.dimension_definitions}

    with pytest.raises(ValueError, match="strong_bearish Scenario requires a negative"):
        finalize_v4_generation_result(
            draft,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_baseline_can_be_floor_or_ceiling_when_it_has_highest_probability() -> None:
    draft = _valid_result()
    draft.scenarios[0].probability_score = 90
    draft.scenarios[1].probability_score = 5

    result, _coverage = finalize_v4_generation_result(
        draft,
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )

    baseline = next(scenario for scenario in result.scenarios if scenario.baseline_yn)
    assert baseline.scenario_role == "ceiling"
    assert baseline.probability_score == 90


def test_v4_schema_validation_failure_enters_feedback_retry_loop() -> None:
    aggregate = _valid_result()
    dimension_draft = V4DimensionDesignResult(
        interactions=aggregate.interactions,
        dimension_definitions=aggregate.dimension_definitions,
    )
    valid_draft = V4ScenarioSynthesisResult(
        group_title=aggregate.group_title,
        group_description=aggregate.group_description,
        scenarios=aggregate.scenarios,
        excluded_scenarios=aggregate.excluded_scenarios,
    )
    invalid_response = MIBaseError(
        ErrorCode.LLM_INVALID_RESPONSE_ERROR,
        detail="groupTitle must not be blank",
    )
    invoke = AsyncMock(side_effect=[invalid_response, valid_draft])
    state = V4MultiEventGenerationState(dimension_draft=dimension_draft)

    with (
        patch.object(v4_nodes, "invoke_stage_structured_output", new=invoke),
        patch.object(v4_nodes, "_backoff", new=AsyncMock()),
    ):
        first = asyncio.run(v4_nodes.SynthesizeV4ScenariosNode().run(state))
        state = state.model_copy(update=first)
        assert v4_nodes.route_after_v4_scenarios(state) == "synthesize_v4_scenarios"
        second = asyncio.run(v4_nodes.SynthesizeV4ScenariosNode().run(state))

    assert second["scenario_draft"] == valid_draft
    assert invoke.await_count == 2
    assert "groupTitle" in invoke.await_args_list[1].kwargs["user_prompt"]


def test_v4_langgraph_uses_two_llm_stages_and_retries_only_dimension_stage() -> None:
    from apps.persistence.event.schema import EventPayload
    from apps.persistence.scenario_group.schema import ScenarioGroupPayload

    aggregate = _valid_result()
    dimension_draft = V4DimensionDesignResult(
        interactions=aggregate.interactions,
        dimension_definitions=aggregate.dimension_definitions,
    )
    scenario_draft = V4ScenarioSynthesisResult(
        group_title=aggregate.group_title,
        group_description=aggregate.group_description,
        scenarios=aggregate.scenarios,
        excluded_scenarios=aggregate.excluded_scenarios,
    )
    calls: list[str] = []
    dimension_attempts = 0

    async def invoke_stage(*, output_schema: type[object], **_kwargs: object) -> object:
        nonlocal dimension_attempts
        calls.append(output_schema.__name__)
        if output_schema is V4DimensionDesignResult:
            dimension_attempts += 1
            if dimension_attempts == 1:
                raise MIBaseError(
                    ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                    detail="dimensionDefinitions validation failed",
                )
            return dimension_draft.model_copy(deep=True)
        return scenario_draft.model_copy(deep=True)

    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v4",
        generation_strategy="multi_event_model_lever_dimensions",
    )
    state = V4MultiEventGenerationState(
        scenario_group=group,
        events=[
            EventPayload(mi_event_id=101, event_type_l2_id=8),
            EventPayload(mi_event_id=202, event_type_l2_id=12),
        ],
        impact_levers=_catalog(),
        impact_catalog_version="v1",
        impact_catalog_checksum="checksum-v1",
        comparison_run_id="compare-v4-graph",
        user_id=7,
    )

    v4_flow_module.get_compiled_graph.cache_clear()
    with (
        patch.object(v4_nodes, "invoke_stage_structured_output", side_effect=invoke_stage),
        patch.object(v4_nodes, "_backoff", new=AsyncMock()),
        patch.object(
            v4_nodes.ScenarioGroupService,
            "persist_multi_event_generation",
            return_value=(group, []),
        ) as persist,
    ):
        final_state = asyncio.run(v4_flow_module.get_compiled_graph().ainvoke(state))
    v4_flow_module.get_compiled_graph.cache_clear()

    assert calls == ["V4DimensionDesignResult", "V4DimensionDesignResult", "V4ScenarioSynthesisResult"]
    assert final_state["dimension_attempt"] == 2
    assert final_state["scenario_attempt"] == 1
    persist.assert_called_once()


def test_v4_inline_persists_compact_dimension_grounding_and_database_baseline_yn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import v4_flow
    from apps.persistence.event.schema import EventPayload
    from apps.persistence.scenario.schema import ScenarioPayload
    from apps.persistence.scenario_group.schema import ScenarioGroupPayload

    finalized, coverage = finalize_v4_generation_result(
        _valid_result(),
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )
    persist = Mock(
        return_value=(
            ScenarioGroupPayload(
                scenario_group_id=10,
                dimension_selected=[dimension.dimension_id for dimension in finalized.dimension_definitions],
                scenario_count=len(finalized.scenarios),
                api_version="v4",
                generation_strategy="multi_event_model_lever_dimensions",
            ),
            [
                ScenarioPayload(
                    scenario_id=index,
                    scenario_group_id=10,
                    title=scenario.title,
                    dimension_values=scenario.dimension_values,
                    probability_score=scenario.probability_score,
                    baseline_yn="Y" if scenario.baseline_yn else "N",
                    global_pressure_band=scenario.global_pressure_band,
                    scenario_role=scenario.scenario_role,
                    global_pressure_rationale=scenario.global_pressure_rationale,
                    related_markets=scenario.related_markets,
                )
                for index, scenario in enumerate(finalized.scenarios, start=1)
            ],
        ),
    )
    monkeypatch.setattr(v4_flow.ScenarioGroupService, "persist_multi_event_generation", persist)

    async def run_graph(
        state: V4MultiEventGenerationState,
        **_kwargs: object,
    ) -> V4MultiEventGenerationState:
        graph_state = state.model_copy(
            update={"finalized_result": finalized, "parameter_coverage": coverage},
        )
        return graph_state.model_copy(update=v4_nodes.persist_v4_generation(graph_state))

    graph = SimpleNamespace(ainvoke=AsyncMock(side_effect=run_graph))
    monkeypatch.setattr(v4_flow, "get_compiled_graph", Mock(return_value=graph))

    response = asyncio.run(
        run_v4_multi_event_scenarios_inline(
            {
                "scenario_group": ScenarioGroupPayload(
                    scenario_group_id=10,
                    api_version="v4",
                    generation_strategy="multi_event_model_lever_dimensions",
                ),
                "events": [
                    EventPayload(mi_event_id=101, event_type_l2_id=8, event_title_ko="한파"),
                    EventPayload(mi_event_id=202, event_type_l2_id=12, event_title_ko="액화시설 정비"),
                ],
                "impact_levers": _catalog(),
                "impact_catalog_version": "v1",
                "comparison_run_id": "compare-1",
                "user_id": 7,
            },
        ),
    )

    saved = persist.call_args.kwargs["scenarios"]
    saved_dimensions = persist.call_args.kwargs["dimension_definitions"]
    saved_diagnostics = persist.call_args.kwargs["generation_diagnostics"]
    assert [scenario["baseline_yn"] for scenario in saved] == ["N", "Y", "N"]
    assert saved_dimensions[0]["event_groundings"][0]["event_id"] == 101
    assert saved_dimensions[0]["lever_mappings"][0]["impact_lever_id"] == 1
    assert "source_fact_ids" not in saved_dimensions[0]
    assert "impact_lever_refs" not in saved_dimensions[0]
    assert "source_refs" not in saved_dimensions[0]
    assert "event_impact_facts" not in saved_diagnostics
    assert "event_dimension_coverage" not in saved_diagnostics
    assert response.data is not None
    assert response.data.dimension_definitions[0].event_groundings[0].observed_basis
    assert response.data.table.rows[0].related_markets == [
        RelatedMarket(market="JKM", rationale="아시아향 화물 전환 가능성이 특별히 중요함"),
    ]


def test_v4_finalizer_rejects_unknown_lever() -> None:
    result = _valid_result()
    result.dimension_definitions[0].lever_mappings[0].lever_code = "invented_parameter"

    with pytest.raises(ValueError, match="unknown lever"):
        finalize_v4_generation_result(result, event_ids=[101, 202], impact_levers=_catalog())


def test_v4_finalizer_allows_dimensions_without_executable_binding() -> None:
    result = _valid_result()
    result.dimension_definitions[0].lever_mappings[0] = V4LeverMapping(
        lever_code="direct_gas_demand",
        mapping_rationale="현재 직접 binding이 없어도 중요한 수요 불확실성이다.",
    )

    _finalized, coverage = finalize_v4_generation_result(
        result,
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )

    assert coverage.coverage_status == "none"


def test_v4_finalizer_rejects_impact_lever_id_code_mismatch() -> None:
    result = _valid_result()
    result.dimension_definitions[0].lever_mappings[0].impact_lever_id = 2

    with pytest.raises(ValueError, match="id/code mismatch"):
        finalize_v4_generation_result(result, event_ids=[101, 202], impact_levers=_catalog())


def test_v4_finalizer_rejects_unknown_grounding_event() -> None:
    result = _valid_result()
    result.dimension_definitions[0].event_groundings[0].event_id = 999

    with pytest.raises(ValueError, match="references unknown events"):
        finalize_v4_generation_result(result, event_ids=[101, 202], impact_levers=_catalog())


def test_v4_dimension_allows_multiple_groundings_per_event_but_rejects_duplicate_lever_codes() -> None:
    dimension = _dimension(dimension_id="duplicate", event_id=101, lever_code="weather_demand")
    payload = dimension.model_dump()
    payload["event_groundings"].append(payload["event_groundings"][0])

    parsed = V4DimensionDefinition.model_validate(payload)

    assert [grounding.event_id for grounding in parsed.event_groundings] == [101, 101]

    payload = dimension.model_dump()
    payload["lever_mappings"].append(payload["lever_mappings"][0])
    with pytest.raises(ValueError, match="unique leverCodes"):
        V4DimensionDefinition.model_validate(payload)


def test_v4_prompt_uses_compact_dimension_grounding_contract() -> None:
    prompt = build_model_lever_user_prompt(
        events=[
            {
                "mi_event_id": 101,
                "event_title_ko": "동북아 한파",
                "one_line_summary": "겨울 수요 증가 가능성",
            },
        ],
        impact_levers=[lever.model_dump() for lever in _catalog()],
        catalog_version="v1",
    )

    assert "동북아 한파" in prompt
    assert "eventGroundings" in prompt
    assert "observedBasis" in prompt
    assert "uncertainty" in prompt
    assert "leverMappings" in prompt
    assert "assumptionRationale" in prompt
    assert "bullish, balanced, bearish" in prompt
    assert "추가 가정" in prompt
    assert "weather_demand" in prompt
    assert "sourceFactIds" in prompt
    assert "만들지 마십시오" in prompt
    assert "parameterBindings" not in prompt
    assert "applicabilityHint" not in prompt
    assert "Template Domain Knowledge" not in prompt


def test_v4_scenario_prompt_does_not_repeat_raw_events_or_fact_graph() -> None:
    result = _valid_result()
    prompt = build_v4_scenario_synthesis_user_prompt(
        interactions=[interaction.model_dump() for interaction in result.interactions],
        dimension_definitions=[definition.model_dump() for definition in result.dimension_definitions],
    )

    assert "Validated Dimensions" in prompt
    assert "eventGroundings" in prompt
    assert "leverMappings" in prompt
    assert "Event Context" not in prompt
    assert "Event Impact Facts" not in prompt
    assert "impactLeverId" not in prompt
    assert "modelSupportStatus" not in prompt


def test_v4_rejects_duplicate_related_markets() -> None:
    with pytest.raises(ValueError, match="related markets must be unique"):
        V4ScenarioCandidate(
            title="중복 시장",
            narrative="시장 중복 검증",
            dimension_values={},
            global_pressure_band="balanced",
            global_pressure_rationale="글로벌 압력은 균형",
            related_markets=[
                RelatedMarket(market="JKM", rationale="첫 번째 근거"),
                RelatedMarket(market="JKM", rationale="두 번째 근거"),
            ],
            probability_score=50,
        )


def test_v4_generation_schema_is_openai_strict_compatible() -> None:
    parameters = pydantic_function_tool(V4GenerationResult)["function"]["parameters"]
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
    assert parameters["$defs"]["V4ScenarioCandidate"]["properties"]["dimensionValues"]["type"] == "array"


def test_v4_schema_converts_strict_wire_dimension_values_to_domain_map() -> None:
    payload = _valid_result().model_dump(by_alias=True)
    scenario = payload["scenarios"][0]
    scenario["dimensionValues"] = [
        {"dimensionId": key, "valueId": value} for key, value in scenario["dimensionValues"].items()
    ]

    parsed = V4GenerationResult.model_validate(payload)

    assert parsed.scenarios[0].dimension_values
