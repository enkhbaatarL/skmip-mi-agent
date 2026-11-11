from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

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
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_budget import scenario_count_range
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_enums import (
    StateDirection,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDefinition,
    V4DimensionDesignDraft,
    V4DimensionDesignResult,
    V4EventAnalysisExclusion,
    V4EventImpactAnalysisDraft,
    V4EventImpactAnalysisResult,
    V4ExcludedScenarioCandidate,
    V4ForecastClaim,
    V4GenerationResult,
    V4GroupTitleDraft,
    V4LeverStateDraft,
    V4ReadableAdditionalDimensionDesignDraft,
    V4ReadableDimensionDesignDraft,
    V4ReadableEventAnalysisDraft,
    V4ReadableInteractionAnalysisDraft,
    V4ReadableScenarioSynthesisDraft,
    V4ScenarioCandidateDraft,
    V4ScenarioSynthesisResult,
    expand_v4_readable_dimension_design,
    expand_v4_readable_event_analysis,
    finalize_v4_dimension_design,
    finalize_v4_event_impact_analysis,
    finalize_v4_generation_result,
    merge_v4_readable_interactions,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    build_model_lever_user_prompt,
    build_v4_additional_dimension_user_prompt,
    build_v4_dimension_design_user_prompt,
    build_v4_event_fact_candidates,
    build_v4_event_impact_analysis_user_prompt,
    build_v4_forecast_claims,
    build_v4_interaction_analysis_user_prompt,
    build_v4_scenario_synthesis_user_prompt,
    event_open_question_budgets,
    is_v4_unconfirmed_statement,
    summarize_parameter_slots,
)
from apps.agents.scenario_group_agent.utils.pressure_band import (
    assign_relative_pressure_bands,
    uses_unique_strong_bands,
)
from apps.agents.scenario_group_agent.utils.scenario_similarity import (
    ScenarioSimilarityInput,
    find_similar_scenario_pairs,
)
from apps.agents.scenario_group_agent.utils.scenario_group_summary import (
    EVENT_SUMMARY_PREVIEW_LENGTH,
    build_scenario_group_event_summary,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload
from apps.persistence.model_impact_lever.schema import (
    ModelImpactLeverParameterBinding,
    ModelImpactLeverPayload,
)
from apps.persistence.scenario.schema import RelatedMarket
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


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
        applicability_hint=f"{code}의 강도·기간·범위가 달라질 때 선택한다.",
        parameter_bindings=bindings,
        catalog_version="v1",
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


def _analysis_draft() -> V4EventImpactAnalysisDraft:
    return V4EventImpactAnalysisDraft.model_validate(
        {
            "decisionBasis": [
                "분석 기준일 2026-08-07 현재 동북아 한파 전망의 실제 강도와 지속 기간은 아직 확정되지 않았다.",
                "미국 Gulf LNG 액화시설 중단은 확인됐지만 재가동 목표일은 제공되지 않았다.",
            ],
            "eventFacts": [
                {
                    "factId": "fact_101_1",
                    "eventId": 101,
                    "observedBasis": "기상기관이 동북아 한파 지속 전망을 발표했다.",
                    "factStatus": "forecast",
                    "observedAt": "2026-08-05",
                    "confidence": "medium",
                    "noMaterialImpactReason": None,
                },
                {
                    "factId": "fact_202_1",
                    "eventId": 202,
                    "observedBasis": "미국 Gulf LNG 액화시설의 가동 중단이 확인됐다.",
                    "factStatus": "observed",
                    "observedAt": "2026-08-05",
                    "confidence": "high",
                    "noMaterialImpactReason": None,
                },
            ],
            "eventExclusions": [],
            "impactPaths": [
                {
                    "impactPathId": "path_101_demand",
                    "eventId": 101,
                    "sourceFactIds": ["fact_101_1"],
                    "mechanism": "한파가 동북아 난방·발전용 LNG 수요를 늘린다.",
                    "leverSteps": [
                        {
                            "leverCode": "weather_demand",
                            "pathRole": "primary",
                            "stateDirection": "increase",
                            "scope": "동북아",
                            "timing": "단기",
                        },
                    ],
                    "balanceEffect": {
                        "domain": "demand",
                        "direction": "increase",
                        "rationale": "동북아의 추가 현물 LNG 수요가 발생한다.",
                    },
                    "priceEffect": {
                        "targetMarket": "JKM",
                        "direction": "bullish",
                        "timeHorizon": "short_term",
                        "rationale": "아시아 현물 화물 경쟁을 강화한다.",
                    },
                    "materiality": "high",
                },
                {
                    "impactPathId": "path_202_supply",
                    "eventId": 202,
                    "sourceFactIds": ["fact_202_1"],
                    "mechanism": "액화시설 중단이 수출 가능한 LNG 물량을 줄인다.",
                    "leverSteps": [
                        {
                            "leverCode": "liquefaction_availability",
                            "pathRole": "primary",
                            "stateDirection": "decrease",
                            "scope": "US Gulf",
                            "timing": "즉시",
                        },
                        {
                            "leverCode": "financial_market_sentiment",
                            "pathRole": "transmission",
                            "stateDirection": "increase",
                            "scope": "글로벌 LNG 시장",
                            "timing": "단기",
                        },
                    ],
                    "balanceEffect": {
                        "domain": "supply",
                        "direction": "decrease",
                        "rationale": "미국발 LNG 공급 가용성이 감소한다.",
                    },
                    "priceEffect": {
                        "targetMarket": "JKM",
                        "direction": "bullish",
                        "timeHorizon": "short_term",
                        "rationale": "대체 화물을 구하려는 아시아 구매자 경쟁이 강화된다.",
                    },
                    "materiality": "high",
                },
            ],
            "pathUncertainties": [
                {
                    "uncertaintyId": "u_weather_magnitude",
                    "impactPathIds": ["path_101_demand"],
                    "axisType": "magnitude",
                    "subject": "한파에 따른 추가 LNG 수요 규모",
                    "affectedLeverCode": "weather_demand",
                    "reason": "한파 전망은 발표됐지만 실제 강도는 확정되지 않았다.",
                    "materiality": "high",
                    "semanticKey": "weather_demand:magnitude:northeast_asia",
                },
                {
                    "uncertaintyId": "u_liq_recovery",
                    "impactPathIds": ["path_202_supply"],
                    "axisType": "recovery",
                    "subject": "액화시설 재가동 시점",
                    "affectedLeverCode": "liquefaction_availability",
                    "reason": "가동 중단은 확인됐지만 재가동 일정은 확정되지 않았다.",
                    "materiality": "high",
                    "semanticKey": "liquefaction_availability:recovery:us_gulf",
                },
                {
                    "uncertaintyId": "u_risk_magnitude",
                    "impactPathIds": ["path_202_supply"],
                    "axisType": "magnitude",
                    "subject": "공급 차질 위험 프리미엄",
                    "affectedLeverCode": "financial_market_sentiment",
                    "reason": "시장 위험 프리미엄의 확대 폭은 확정되지 않았다.",
                    "materiality": "medium",
                    "semanticKey": "financial_market_sentiment:magnitude:global",
                },
            ],
            "interactions": [
                {
                    "interactionId": "interaction_1",
                    "eventIds": [101, 202],
                    "impactPathIds": ["path_101_demand", "path_202_supply"],
                    "relation": "amplification",
                    "mechanism": "동북아 추가 수요와 미국 공급 감소가 겹쳐 현물 경쟁을 강화한다.",
                    "priceEffect": "bullish",
                },
            ],
            "interactionUncertainties": [
                {
                    "uncertaintyId": "u_overlap_duration",
                    "interactionId": "interaction_1",
                    "impactPathIds": ["path_101_demand", "path_202_supply"],
                    "axisType": "duration",
                    "subject": "수요·공급 충격의 중첩 기간",
                    "affectedLeverCode": "liquefaction_availability",
                    "reason": "두 충격이 동시에 유지되는 기간은 확정되지 않았다.",
                    "materiality": "medium",
                    "semanticKey": "interaction_1:duration:overlap",
                },
            ],
        },
    )


def _analysis() -> V4EventImpactAnalysisResult:
    return finalize_v4_event_impact_analysis(
        _analysis_draft(),
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )


def _dimension_draft() -> V4DimensionDesignDraft:
    def value(
        value_id: str,
        label: str,
        lever_code: str,
        direction: str,
        level: str,
        contribution: str,
    ) -> dict[str, object]:
        return {
            "valueId": value_id,
            "label": label,
            "leverStates": [
                {
                    "leverCode": lever_code,
                    "direction": direction,
                    "level": level,
                    "scope": "관련 시장 범위",
                    "timeWindow": "단기",
                },
            ],
            "pressureContribution": contribution,
            "assumptionRationale": f"{label} 상태가 공통 영향 대비 JKM 압력 차이를 만든다.",
        }

    return V4DimensionDesignDraft.model_validate(
        {
            "dimensionDefinitions": [
                {
                    "dimensionId": "cold_wave_intensity",
                    "label": "한파 수요 강도",
                    "description": "동북아 한파가 만드는 추가 LNG 수요 규모",
                    "rationale": "한파 수요 분기 기준",
                    "sourceImpactPathIds": ["path_101_demand"],
                    "sourceUncertaintyIds": ["u_weather_magnitude"],
                    "primaryLeverCode": "weather_demand",
                    "dimensionType": "magnitude",
                    "valueKind": "categorical",
                    "unit": None,
                    "values": [
                        value("low", "제한적 증가", "weather_demand", "unchanged", "limited", "bearish"),
                        value("high", "큰 폭 증가", "weather_demand", "increase", "high", "bullish"),
                    ],
                },
                {
                    "dimensionId": "liquefaction_recovery",
                    "label": "액화시설 회복",
                    "description": "미국 Gulf 액화시설 재가동 속도",
                    "rationale": "공급 회복 분기 기준",
                    "sourceImpactPathIds": ["path_202_supply"],
                    "sourceUncertaintyIds": ["u_liq_recovery"],
                    "primaryLeverCode": "liquefaction_availability",
                    "dimensionType": "recovery",
                    "valueKind": "temporal",
                    "unit": "주",
                    "values": [
                        value(
                            "fast",
                            "2주 내 회복",
                            "liquefaction_availability",
                            "recover",
                            "high_availability",
                            "bearish",
                        ),
                        value(
                            "delayed",
                            "6주 이상 지연",
                            "liquefaction_availability",
                            "disrupt",
                            "low_availability",
                            "bullish",
                        ),
                    ],
                },
                {
                    "dimensionId": "risk_premium",
                    "label": "위험 프리미엄",
                    "description": "공급 차질에 대한 시장 위험 프리미엄 확대 폭",
                    "rationale": "위험 프리미엄 분기",
                    "sourceImpactPathIds": ["path_202_supply"],
                    "sourceUncertaintyIds": ["u_risk_magnitude"],
                    "primaryLeverCode": "financial_market_sentiment",
                    "dimensionType": "magnitude",
                    "valueKind": "categorical",
                    "unit": None,
                    "values": [
                        value(
                            "low",
                            "빠른 안정",
                            "financial_market_sentiment",
                            "decrease",
                            "low_premium",
                            "bearish",
                        ),
                        value(
                            "high",
                            "프리미엄 확대",
                            "financial_market_sentiment",
                            "increase",
                            "high_premium",
                            "bullish",
                        ),
                    ],
                },
            ],
            "excludedDimensions": [],
        },
    )


def _dimensions() -> V4DimensionDesignResult:
    return finalize_v4_dimension_design(
        _dimension_draft(),
        impact_analysis=_analysis(),
        impact_levers=_catalog(),
    )


def _synthesis() -> V4ScenarioSynthesisResult:
    common_paths = ["path_101_demand", "path_202_supply"]

    def scenario(
        title: str,
        values: dict[str, str],
        band: str,
        score: float,
        mixed: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "title": title,
            "narrative": f"{title} 전개",
            "dimensionValues": values,
            "commonImpactPathIds": common_paths,
            "appliedInteractionIds": ["interaction_1"],
            "pressureBand": band,
            "pressureBreakdown": {
                "commonImpact": "한파 수요 증가와 미국 공급 감소를 공통으로 반영한다.",
                "valueDelta": "선택된 Value의 레버 상태가 공통 영향 대비 압력을 조정한다.",
                "interactionEffect": "수요·공급 충격 중첩이 현물 경쟁을 증폭한다.",
            },
            "relatedMarkets": (
                [{"market": "TTF", "rationale": "유럽과 아시아의 유연 화물 경쟁도 강화될 수 있다."}]
                if band == "strong_bullish"
                else []
            ),
            "probabilityScore": score,
            "mixedFactors": mixed or [],
            "explanation": f"{title}의 JKM 압력 근거를 자연어로 설명한다.",
        }

    return V4ScenarioSynthesisResult.model_validate(
        {
            "groupDescription": "공통 영향 경로와 잔여 불확실성을 결합한 JKM 시나리오",
            "scenarios": [
                scenario(
                    "상단",
                    {"cold_wave_intensity": "high", "liquefaction_recovery": "delayed", "risk_premium": "high"},
                    "strong_bullish",
                    35,
                ),
                scenario(
                    "혼합",
                    {"cold_wave_intensity": "high", "liquefaction_recovery": "fast", "risk_premium": "low"},
                    "balanced",
                    50,
                    ["한파 수요 증가", "액화시설 조기 회복"],
                ),
                scenario(
                    "하단",
                    {"cold_wave_intensity": "low", "liquefaction_recovery": "fast", "risk_premium": "low"},
                    "strong_bearish",
                    15,
                ),
            ],
            "excludedScenarios": [
                {
                    "pressureBand": "bullish",
                    "reasonCode": "LOW_DISTINCTIVENESS",
                    "reason": "상단과 유사",
                    "dimensionValues": {
                        "cold_wave_intensity": "high",
                        "liquefaction_recovery": "fast",
                        "risk_premium": "high",
                    },
                },
                {
                    "pressureBand": "bearish",
                    "reasonCode": "LOW_DISTINCTIVENESS",
                    "reason": "하단과 유사",
                    "dimensionValues": {
                        "cold_wave_intensity": "low",
                        "liquefaction_recovery": "delayed",
                        "risk_premium": "low",
                    },
                },
            ],
        },
    )


def _group_summary() -> str:
    return build_scenario_group_event_summary(
        [
            EventPayload(
                mi_event_id=101,
                event_type_l2_id=8,
                one_line_summary="동북아 한파 수요가 증가했다.",
            ),
            EventPayload(
                mi_event_id=202,
                event_type_l2_id=12,
                one_line_summary="미국 액화시설 공급 차질이 발생했다.",
            ),
        ],
    )


def _finalized() -> tuple[V4GenerationResult, object]:
    return finalize_v4_generation_result(
        _synthesis(),
        group_title="테스트 그룹",
        group_summary=_group_summary(),
        impact_analysis=_analysis(),
        dimension_design=_dimensions(),
        impact_levers=_catalog(),
    )


def test_v4_request_requires_one_to_five_unique_events() -> None:
    payload = V4MultiEventCreateScenariosIn(mi_event_ids=[101], user_id=7)
    assert payload.mi_event_ids == [101]
    with pytest.raises(ValueError):
        V4MultiEventCreateScenariosIn(mi_event_ids=[101, 101], user_id=7)
    with pytest.raises(ValueError):
        V4MultiEventCreateScenariosIn(mi_event_ids=[], user_id=7)
    with pytest.raises(ValueError):
        V4MultiEventCreateScenariosIn(mi_event_ids=[1, 2, 3, 4, 5, 6], user_id=7)


def test_v4_group_summary_preserves_text_up_to_40_characters() -> None:
    summary = "가" * EVENT_SUMMARY_PREVIEW_LENGTH

    result = build_scenario_group_event_summary(
        [EventPayload(mi_event_id=101, event_type_l2_id=8, one_line_summary=summary)],
    )

    assert result == summary


def test_v4_group_summary_truncates_without_ellipsis() -> None:
    result = build_scenario_group_event_summary(
        [EventPayload(mi_event_id=101, event_type_l2_id=8, one_line_summary="가" * 45)],
    )

    assert result == "가" * EVENT_SUMMARY_PREVIEW_LENGTH
    assert "…" not in result


def test_v4_group_summary_combines_five_events_in_request_order_at_max_length() -> None:
    events = [
        EventPayload(mi_event_id=index, event_type_l2_id=8, one_line_summary=str(index) * 45) for index in range(1, 6)
    ]

    result = build_scenario_group_event_summary(events)

    assert result == " | ".join(str(index) * EVENT_SUMMARY_PREVIEW_LENGTH for index in range(1, 6))
    assert len(result) == 212


def test_v4_group_summary_normalizes_whitespace_and_uses_title_then_id_fallback() -> None:
    result = build_scenario_group_event_summary(
        [
            EventPayload(
                mi_event_id=101,
                event_type_l2_id=8,
                one_line_summary="  한파로\n난방\t 수요가   증가했다.  ",
            ),
            EventPayload(
                mi_event_id=202,
                event_type_l2_id=12,
                event_title_ko="  액화시설\n 정비  ",
                one_line_summary=" \t ",
            ),
            EventPayload(mi_event_id=303, event_type_l2_id=15),
        ],
    )

    assert result == "한파로 난방 수요가 증가했다. | 액화시설 정비 | 이벤트 303"


def test_v4_sync_and_background_routes_are_registered() -> None:
    from apps.agents.scenario_group_agent.api import router

    paths = {route.path for route in router.routes if "POST" in getattr(route, "methods", set())}
    assert "/v4/scenario-groups" in paths
    assert "/v4/scenario-groups/sync" in paths


def test_v4_event_impact_analysis_hydrates_ordered_lever_steps_and_lineage() -> None:
    result = _analysis()
    assert [step.impact_lever_id for step in result.impact_paths[1].lever_steps] == [2, 3]
    assert result.interactions[0].impact_path_ids == ["path_101_demand", "path_202_supply"]
    assert result.validation_warnings == []
    assert "fact_status" not in result.event_facts[0].model_dump()
    assert "confidence" not in result.event_facts[0].model_dump()
    assert "no_material_impact_reason" not in result.event_facts[0].model_dump()
    assert "price_effect" not in result.impact_paths[0].model_dump()
    assert "price_effect" not in result.interactions[0].model_dump()


def test_v4_event_impact_analysis_rejects_unknown_fact_and_lever() -> None:
    draft = _analysis_draft()
    draft.impact_paths[0].source_fact_ids = ["missing"]
    with pytest.raises(ValueError, match="unknown facts"):
        finalize_v4_event_impact_analysis(draft, event_ids=[101, 202], impact_levers=_catalog())

    draft = _analysis_draft()
    draft.impact_paths[0].lever_steps[0].lever_code = "invented"
    with pytest.raises(ValueError, match="unknown lever"):
        finalize_v4_event_impact_analysis(draft, event_ids=[101, 202], impact_levers=_catalog())


def test_v4_event_impact_analysis_requires_complete_event_coverage() -> None:
    draft = _analysis_draft()
    draft.event_facts = [fact for fact in draft.event_facts if fact.event_id != 202]
    draft.impact_paths = [path for path in draft.impact_paths if path.event_id != 202]
    draft.path_uncertainties = [
        item for item in draft.path_uncertainties if "path_202_supply" not in item.impact_path_ids
    ]
    draft.interactions = []
    draft.interaction_uncertainties = []
    with pytest.raises(ValueError, match="does not cover Events"):
        finalize_v4_event_impact_analysis(draft, event_ids=[101, 202], impact_levers=_catalog())


def test_v4_legacy_price_effect_is_ignored_without_affecting_analysis() -> None:
    result = finalize_v4_event_impact_analysis(_analysis_draft(), event_ids=[101, 202], impact_levers=_catalog())

    assert result.validation_warnings == []
    assert all("price_effect" not in path.model_dump() for path in result.impact_paths)
    assert all("price_effect" not in interaction.model_dump() for interaction in result.interactions)


def test_v4_dimension_contract_derives_event_and_lever_ids_without_legacy_fields() -> None:
    result = _dimensions()
    definition = result.dimension_definitions[0]
    schema_fields = V4DimensionDefinition.model_json_schema(by_alias=True)["properties"]
    assert definition.source_event_ids == [101]
    assert definition.primary_impact_lever_id == 1
    assert definition.rationale == "한파 수요 분기 기준"
    assert definition.values[0].lever_states[0].impact_lever_id == 1
    assert "rationale" in schema_fields
    assert "eventGroundings" not in schema_fields
    assert "leverMappings" not in schema_fields


def test_v4_state_direction_is_shared_by_schema_and_wire_parser() -> None:
    expected = {
        "increase": "증가",
        "decrease": "감소",
        "disrupt": "차질",
        "recover": "회복",
        "unchanged": "현 수준 유지",
    }

    assert {direction.value: direction.label_ko for direction in StateDirection} == expected
    schema = V4LeverStateDraft.model_json_schema(by_alias=True)
    assert schema["$defs"]["StateDirection"]["enum"] == list(expected)

    for direction in StateDirection:
        state = V4LeverStateDraft(
            lever_code="weather_demand",
            direction=direction,
            level="추가 LNG 수요",
            scope="동북아",
            time_window="단기",
        )
        assert state.model_dump(mode="json", by_alias=True)["direction"] == direction.value

        payload = _readable_dimension_draft().model_dump(by_alias=True)
        payload["dimensions"][0]["choices"][0]["states"] = [
            f"weather_demand|{direction.value}|추가 LNG 수요|동북아|단기",
        ]
        expanded = expand_v4_readable_dimension_design(
            V4ReadableDimensionDesignDraft.model_validate(payload),
            impact_analysis=_analysis(),
        )
        assert expanded.dimension_definitions[0].values[0].lever_states[0].direction == direction

        readable_event = _readable_event_draft(101)
        readable_event.impacts[0].lever_states = [
            f"weather_demand|primary|{direction.value}|동북아|단기",
        ]
        expanded_event = expand_v4_readable_event_analysis(
            readable_event,
            event_id=101,
            observed_at="2026-08-05",
            fact_candidates={"f1": "동북아 한파 지속 전망"},
        )
        assert expanded_event.impact_paths[0].lever_steps[0].state_direction == direction

    invalid = _readable_dimension_draft().model_dump(by_alias=True)
    invalid["dimensions"][0]["choices"][0]["states"] = [
        "weather_demand|sideways|추가 LNG 수요|동북아|단기",
    ]
    with pytest.raises(ValueError, match="invalid Dimension state direction: sideways"):
        expand_v4_readable_dimension_design(
            V4ReadableDimensionDesignDraft.model_validate(invalid),
            impact_analysis=_analysis(),
        )

    invalid_event = _readable_event_draft(101)
    invalid_event.impacts[0].lever_states = [
        "weather_demand|primary|sideways|동북아|단기",
    ]
    with pytest.raises(ValueError, match="invalid lever direction: sideways"):
        expand_v4_readable_event_analysis(
            invalid_event,
            event_id=101,
            observed_at="2026-08-05",
            fact_candidates={"f1": "동북아 한파 지속 전망"},
        )


def test_v4_dimension_rejects_lever_outside_source_paths() -> None:
    draft = _dimension_draft()
    draft.dimension_definitions[0].values[0].lever_states[0].lever_code = "direct_gas_demand"
    with pytest.raises(ValueError, match="omits the primary Lever|outside its source paths"):
        finalize_v4_dimension_design(draft, impact_analysis=_analysis(), impact_levers=_catalog())


def test_v4_dimension_records_explained_counter_directional_value_warning() -> None:
    draft = _dimension_draft()
    value = draft.dimension_definitions[0].values[1]
    value.lever_states[0].direction = StateDirection.DECREASE
    value.assumption_rationale = "대체 연료 전환이 동시에 제한되어 수요 감소에도 JKM 압력이 상승하는 예외를 가정한다."

    result = finalize_v4_dimension_design(
        draft,
        impact_analysis=_analysis(),
        impact_levers=_catalog(),
    )

    assert [warning.code for warning in result.validation_warnings] == [
        "COUNTER_DIRECTIONAL_VALUE_PRESSURE",
    ]


def test_v4_finalizer_assigns_roles_builds_pressure_rationale_and_coverage() -> None:
    finalized, coverage = _finalized()
    assert [scenario.scenario_role for scenario in finalized.scenarios] == ["ceiling", "mixed", "floor"]
    assert [scenario.baseline_yn for scenario in finalized.scenarios] == [False, True, False]
    assert [scenario.probability_score for scenario in finalized.scenarios] == [35, 50, 15]
    assert finalized.scenarios[0].pressure_rationale == "상단의 JKM 압력 근거를 자연어로 설명한다."
    assert coverage.coverage_status == "partial"
    assert coverage.covered_dimension_ids == ["cold_wave_intensity"]
    assert coverage.uncovered_dimension_ids == ["liquefaction_recovery", "risk_premium"]


def test_v4_finalizer_normalizes_fractional_probabilities_to_integer_percentages() -> None:
    synthesis = _synthesis()
    for scenario, probability_score in zip(synthesis.scenarios, [0.35, 0.5, 0.15], strict=True):
        scenario.probability_score = probability_score

    finalized, _coverage = finalize_v4_generation_result(
        synthesis,
        group_title="테스트 그룹",
        group_summary=_group_summary(),
        impact_analysis=_analysis(),
        dimension_design=_dimensions(),
        impact_levers=_catalog(),
    )

    assert [scenario.probability_score for scenario in finalized.scenarios] == [35, 50, 15]
    assert sum(scenario.probability_score for scenario in finalized.scenarios) == 100
    assert [scenario.baseline_yn for scenario in finalized.scenarios] == [False, True, False]


def test_v4_finalizer_distributes_zero_probability_weights_deterministically() -> None:
    synthesis = _synthesis()
    # 동률(zero) tie-break는 입력 순서의 index 0이 이긴다. "상단"(strong_bullish)이 index 0이면
    # tie-break로 뽑힌 Base가 그룹 내 가장 bullish한 Scenario와 같아져, Base가 floor/ceiling(=
    # Bearish/Bullish)과 겹치는 것을 막는 새 검증에 걸린다. 이 테스트는 확률 정규화의 tie-break
    # 결정성 자체를 검증하는 목적이므로, "balanced"인 "혼합"이 tie-break로 뽑히도록 순서만 바꾼다.
    synthesis.scenarios = [synthesis.scenarios[1], synthesis.scenarios[0], synthesis.scenarios[2]]
    for scenario in synthesis.scenarios:
        scenario.probability_score = 0

    finalized, _coverage = finalize_v4_generation_result(
        synthesis,
        group_title="테스트 그룹",
        group_summary=_group_summary(),
        impact_analysis=_analysis(),
        dimension_design=_dimensions(),
        impact_levers=_catalog(),
    )

    assert [scenario.probability_score for scenario in finalized.scenarios] == [33, 34, 33]
    assert sum(scenario.probability_score for scenario in finalized.scenarios) == 100
    assert [scenario.baseline_yn for scenario in finalized.scenarios] == [False, True, False]


def test_v4_finalizer_retries_when_injected_fallback_is_below_minimum_probability() -> None:
    # LLM이 제출한 Scenario 3개가 Base(가장 높은 probabilityScore) 대비 전부 bullish 방향이라,
    # bearish 방향 Scenario가 하나도 없는 상황을 재현한다. 서버가 방향 보완용 fallback을
    # 1%로 구성하더라도 최종 Scenario의 최소 확률 5% 계약을 인위적으로 우회하지 않고
    # 합성 재시도로 넘기는지 확인한다.
    def scenario(title: str, values: dict[str, str], band: str, score: float) -> V4ScenarioCandidateDraft:
        return V4ScenarioCandidateDraft.model_validate(
            {
                "title": title,
                "narrative": f"{title} 전개",
                "dimensionValues": values,
                "commonImpactPathIds": ["path_101_demand", "path_202_supply"],
                "appliedInteractionIds": ["interaction_1"],
                "pressureBand": band,
                "pressureBreakdown": {
                    "commonImpact": "x",
                    "valueDelta": "x",
                    "interactionEffect": "x",
                },
                "relatedMarkets": [],
                "probabilityScore": score,
                "mixedFactors": [],
                "explanation": f"{title} 설명",
            },
        )

    base = scenario(
        "base",
        {"cold_wave_intensity": "high", "liquefaction_recovery": "fast", "risk_premium": "low"},
        "balanced",
        80,
    )
    combo_a = scenario(
        "combo-a",
        {"cold_wave_intensity": "low", "liquefaction_recovery": "delayed", "risk_premium": "high"},
        "bullish",
        10,
    )
    combo_b = scenario(
        "combo-b",
        {"cold_wave_intensity": "high", "liquefaction_recovery": "fast", "risk_premium": "high"},
        "strong_bullish",
        10,
    )
    excluded = [
        V4ExcludedScenarioCandidate.model_validate(
            {
                "pressureBand": "strong_bearish",
                "reasonCode": "LOW_PROBABILITY",
                "reason": "x",
                "dimensionValues": {
                    "cold_wave_intensity": "low",
                    "liquefaction_recovery": "fast",
                    "risk_premium": "low",
                },
            },
        ),
        V4ExcludedScenarioCandidate.model_validate(
            {
                "pressureBand": "bearish",
                "reasonCode": "LOW_PROBABILITY",
                "reason": "x",
                "dimensionValues": {
                    "cold_wave_intensity": "low",
                    "liquefaction_recovery": "fast",
                    "risk_premium": "high",
                },
            },
        ),
    ]
    synthesis = V4ScenarioSynthesisResult.model_validate(
        {
            "groupDescription": "test",
            "scenarios": [base.model_dump(), combo_a.model_dump(), combo_b.model_dump()],
            "excludedScenarios": [item.model_dump() for item in excluded],
        },
    )

    with pytest.raises(ValueError, match=r"Final probabilityScore must be >= 5%"):
        finalize_v4_generation_result(
            synthesis,
            group_title="테스트 그룹",
            group_summary=_group_summary(),
            impact_analysis=_analysis(),
            dimension_design=_dimensions(),
            impact_levers=_catalog(),
        )


def test_v4_finalizer_excludes_excess_same_direction_scenarios_beyond_two_slots() -> None:
    # pressure_band는 방향당 slot이 2개(strong_X/X)뿐이라, Base 대비 같은 방향(여기서는 bullish)에
    # 3개가 몰리면 전부 다른 band를 줄 수 없다. 가장 극단적인 2개만 남고 나머지 1개는
    # excludedScenarios로 빠져야 한다(에러 없이 바로 유효한 결과가 나와야 함).
    def scenario(title: str, values: dict[str, str], band: str, score: float) -> V4ScenarioCandidateDraft:
        return V4ScenarioCandidateDraft.model_validate(
            {
                "title": title,
                "narrative": f"{title} 전개",
                "dimensionValues": values,
                "commonImpactPathIds": ["path_101_demand", "path_202_supply"],
                "appliedInteractionIds": ["interaction_1"],
                "pressureBand": band,
                "pressureBreakdown": {
                    "commonImpact": "x",
                    "valueDelta": "x",
                    "interactionEffect": "x",
                },
                "relatedMarkets": [],
                "probabilityScore": score,
                "mixedFactors": [],
                "explanation": f"{title} 설명",
            },
        )

    # 사전 검증(LLM 원본 band 분산·5-band 커버리지)을 통과시키기 위해 원본 band는 서로 다르게
    # 둔다. 실제 recompute는 Base 선정 후 delta 기준으로 다시 계산되므로 이 값 자체는 중요하지
    # 않다 — 핵심은 bullish_1/2/3이 Base 대비 같은(양수) 방향이라는 것.
    base = scenario(
        "base",
        {"cold_wave_intensity": "high", "liquefaction_recovery": "fast", "risk_premium": "low"},
        "bearish",
        40,
    )
    bearish = scenario(
        "bearish",
        {"cold_wave_intensity": "low", "liquefaction_recovery": "fast", "risk_premium": "low"},
        "strong_bearish",
        15,
    )
    bullish_1 = scenario(
        "bullish-1",
        {"cold_wave_intensity": "low", "liquefaction_recovery": "delayed", "risk_premium": "high"},
        "balanced",
        15,
    )
    bullish_2 = scenario(
        "bullish-2",
        {"cold_wave_intensity": "high", "liquefaction_recovery": "fast", "risk_premium": "high"},
        "bullish",
        15,
    )
    bullish_3 = scenario(
        "bullish-3",
        {"cold_wave_intensity": "high", "liquefaction_recovery": "delayed", "risk_premium": "low"},
        "strong_bullish",
        15,
    )
    synthesis = V4ScenarioSynthesisResult.model_validate(
        {
            "groupDescription": "test",
            "scenarios": [item.model_dump() for item in (base, bearish, bullish_1, bullish_2, bullish_3)],
            "excludedScenarios": [],
        },
    )

    finalized, _coverage = finalize_v4_generation_result(
        synthesis,
        group_title="테스트 그룹",
        group_summary=_group_summary(),
        impact_analysis=_analysis(),
        dimension_design=_dimensions(),
        impact_levers=_catalog(),
    )

    assert len(finalized.scenarios) == 4
    non_base_bands = [scenario.pressure_band for scenario in finalized.scenarios if not scenario.baseline_yn]
    assert len(non_base_bands) == len(set(non_base_bands))
    assert len(finalized.excluded_scenarios) == 1
    excluded = finalized.excluded_scenarios[0]
    assert excluded.reason_code == "LOW_DISTINCTIVENESS"
    # 세 bullish 후보가 delta 동률(+2)이라 정렬이 안정적으로 유지되고, 제출 순서상 마지막
    # (bullish-3)이 상위 2개(bullish-1, bullish-2) 밖으로 밀려 제외된다.
    assert excluded.dimension_values == {
        "cold_wave_intensity": "high",
        "liquefaction_recovery": "delayed",
        "risk_premium": "low",
    }
    assert sum(scenario.probability_score for scenario in finalized.scenarios) == 100


def test_v4_scenario_rejects_missing_common_path() -> None:
    synthesis = _synthesis()
    synthesis.scenarios[0].common_impact_path_ids = ["path_101_demand"]
    with pytest.raises(ValueError, match="all common Impact Paths"):
        finalize_v4_generation_result(
            synthesis,
            group_title="테스트 그룹",
        group_summary=_group_summary(),
            impact_analysis=_analysis(),
            dimension_design=_dimensions(),
            impact_levers=_catalog(),
        )


def test_v4_scenario_duplicate_combination_error_identifies_both_scenarios() -> None:
    synthesis = _synthesis()
    synthesis.scenarios[1].dimension_values = dict(synthesis.scenarios[0].dimension_values)

    with pytest.raises(ValueError) as error:
        finalize_v4_generation_result(
            synthesis,
            group_title="테스트 그룹",
        group_summary=_group_summary(),
            impact_analysis=_analysis(),
            dimension_design=_dimensions(),
            impact_levers=_catalog(),
        )

    detail = str(error.value)
    assert "scenarios[1] ('혼합').dimensionValues" in detail
    assert "scenarios[0] ('상단').dimensionValues" in detail
    assert "cold_wave_intensity" in detail


def _readable_event_draft(event_id: int) -> V4ReadableEventAnalysisDraft:
    if event_id == 101:
        fact = "동북아 한파 지속 전망"
        return V4ReadableEventAnalysisDraft.model_validate(
            {
                "eventFacts": [fact],
                "decisionBasis": [
                    "분석 기준일 2026-08-07 현재 한파 전망은 미래 사실이며 실제 수요 규모는 아직 확정되지 않았다."
                ],
                "impacts": [
                    {
                        "evidence": [fact],
                        "analysis": "한파 전망이 동북아 LNG 수요를 늘려 JKM에 단기 상승 압력을 준다.",
                        "leverStates": ["weather_demand|primary|increase|동북아|단기"],
                        "balance": "demand|increase",
                        "importance": "high",
                    },
                ],
                "openQuestions": [
                    {
                        "impact": 1,
                        "question": "한파에 따른 추가 LNG 수요 규모는 얼마인가?",
                        "axis": "magnitude",
                        "lever": "weather_demand",
                    },
                ],
                "excludedBecause": None,
            },
        )
    fact = "미국 LNG 액화시설 가동 중단"
    return V4ReadableEventAnalysisDraft.model_validate(
        {
            "eventFacts": [fact],
            "decisionBasis": ["분석 기준일 2026-08-07 현재 가동 중단은 확인됐지만 재가동 목표일은 제공되지 않았다."],
            "impacts": [
                {
                    "evidence": [fact],
                    "analysis": "액화시설 중단이 미국발 LNG 공급을 줄이고 위험 프리미엄을 높여 JKM에 상승 압력을 준다.",
                    "leverStates": [
                        "liquefaction_availability|primary|decrease|US Gulf|즉시",
                        "financial_market_sentiment|transmission|increase|글로벌|단기",
                    ],
                    "balance": "supply|decrease",
                    "importance": "high",
                },
            ],
            "openQuestions": [
                {
                    "impact": 1,
                    "question": "액화시설은 언제 재가동되는가?",
                    "axis": "recovery",
                    "lever": "liquefaction_availability",
                },
            ],
            "excludedBecause": None,
        },
    )


def test_v4_readable_event_fact_must_match_a_source_sentence() -> None:
    readable = _readable_event_draft(101)
    readable.event_facts = ["모델이 새로 지어낸 사실"]
    readable.impacts[0].evidence = readable.event_facts

    with pytest.raises(ValueError, match="outside the provided candidates"):
        expand_v4_readable_event_analysis(
            readable,
            event_id=101,
            observed_at="2026-08-05",
            fact_candidates={"f1": "동북아 한파 지속 전망"},
        )


def test_v4_readable_event_preserves_natural_language_decision_basis() -> None:
    readable = _readable_event_draft(101)

    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": "동북아 한파 지속 전망"},
    )
    result = finalize_v4_event_impact_analysis(
        draft,
        event_ids=[101],
        impact_levers=_catalog(),
    )

    assert result.decision_basis == readable.decision_basis


def test_v4_readable_event_balance_uses_structured_output_literals() -> None:
    payload = _readable_event_draft(101).model_dump(by_alias=True)
    payload["impacts"][0]["balance"] = "supply|disrupt"

    with pytest.raises(ValueError, match="balance"):
        V4ReadableEventAnalysisDraft.model_validate(payload)


def test_v4_physical_path_rejects_none_with_lever_domain_feedback() -> None:
    readable = _readable_event_draft(101)
    readable.impacts[0].balance = "none"
    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": "동북아 한파 지속 전망"},
    )

    with pytest.raises(
        ValueError,
        match=r"e101_p1 balance cannot be none; weather_demand=demand\. Use demand\|<direction>\.",
    ):
        finalize_v4_event_impact_analysis(
            draft,
            event_ids=[101],
            impact_levers=_catalog(),
        )


def test_v4_mixed_physical_and_price_only_path_requires_physical_balance() -> None:
    readable = _readable_event_draft(202)
    readable.impacts[0].balance = "none"
    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=202,
        observed_at="2026-08-05",
        fact_candidates={"f1": "미국 LNG 액화시설 가동 중단"},
    )

    with pytest.raises(
        ValueError,
        match=(
            r"e202_p1 balance cannot be none; liquefaction_availability=supply, "
            r"financial_market_sentiment=price_only\. Use supply\|<direction>\."
        ),
    ):
        finalize_v4_event_impact_analysis(
            draft,
            event_ids=[202],
            impact_levers=_catalog(),
        )

    readable.impacts[0].balance = "supply|decrease"
    corrected = expand_v4_readable_event_analysis(
        readable,
        event_id=202,
        observed_at="2026-08-05",
        fact_candidates={"f1": "미국 LNG 액화시설 가동 중단"},
    )
    result = finalize_v4_event_impact_analysis(
        corrected,
        event_ids=[202],
        impact_levers=_catalog(),
    )

    assert result.impact_paths[0].balance_effect is not None
    assert result.impact_paths[0].balance_effect.domain == "supply"


def test_v4_multi_domain_path_accepts_selected_domain_and_rejects_unrelated_domain() -> None:
    readable = _readable_event_draft(101)
    readable.impacts[0].lever_states.append(
        "liquefaction_availability|transmission|decrease|글로벌|단기",
    )
    readable.impacts[0].balance = "demand|increase"
    valid_draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": "동북아 한파 지속 전망"},
    )

    result = finalize_v4_event_impact_analysis(
        valid_draft,
        event_ids=[101],
        impact_levers=_catalog(),
    )

    assert result.impact_paths[0].balance_effect is not None
    assert result.impact_paths[0].balance_effect.domain == "demand"

    readable.impacts[0].balance = "trade|decrease"
    invalid_draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": "동북아 한파 지속 전망"},
    )
    with pytest.raises(
        ValueError,
        match=(
            r"e101_p1 balance domain trade does not match Lever domains; weather_demand=demand, "
            r"liquefaction_availability=supply\. Use demand\|<direction> or supply\|<direction>\."
        ),
    ):
        finalize_v4_event_impact_analysis(
            invalid_draft,
            event_ids=[101],
            impact_levers=_catalog(),
        )


def test_v4_price_only_path_discards_non_physical_balance_hint() -> None:
    fact = "유럽 LNG 현물가격이 상승했다."
    readable = V4ReadableEventAnalysisDraft.model_validate(
        {
            "eventFacts": [fact],
            "impacts": [
                {
                    "evidence": [fact],
                    "analysis": "유럽 가격 상승이 지역 가격 신호를 강화해 JKM에 단기 상승 압력을 준다.",
                    "leverStates": ["financial_market_sentiment|primary|increase|유럽|단기"],
                    "balance": "trade|decrease",
                    "importance": "medium",
                },
            ],
            "openQuestions": [
                {
                    "impact": 1,
                    "question": "유럽 가격 강세는 언제까지 지속되는가?",
                    "axis": "duration",
                    "lever": "financial_market_sentiment",
                },
            ],
            "excludedBecause": None,
        },
    )
    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=303,
        observed_at="2026-08-05",
        fact_candidates={"f1": fact},
    )

    result = finalize_v4_event_impact_analysis(
        draft,
        event_ids=[303],
        impact_levers=_catalog(),
    )

    assert result.impact_paths[0].balance_effect is None


def test_v4_readable_question_reports_allowed_impact_levers() -> None:
    readable = _readable_event_draft(101)
    readable.open_questions[0].lever = "liquefaction_availability"

    with pytest.raises(ValueError, match=r"Impact 1 Lever codes: \['weather_demand'\]"):
        expand_v4_readable_event_analysis(
            readable,
            event_id=101,
            observed_at="2026-08-05",
            fact_candidates={"f1": "동북아 한파 지속 전망"},
        )


def test_v4_readable_event_question_count_is_not_schema_limited() -> None:
    payload = _readable_event_draft(101).model_dump(by_alias=True)
    second = dict(payload["openQuestions"][0])
    second["question"] = "한파의 현재 전망은 언제까지 유효한가?"
    second["axis"] = "duration"
    payload["openQuestions"].append(second)

    parsed = V4ReadableEventAnalysisDraft.model_validate(payload)

    assert len(parsed.open_questions) == 2
    payload["openQuestions"].append(dict(second))
    assert len(V4ReadableEventAnalysisDraft.model_validate(payload).open_questions) == 3


def test_v4_readable_event_allows_three_lever_states_and_rejects_four() -> None:
    payload = _readable_event_draft(101).model_dump(by_alias=True)
    payload["impacts"][0]["leverStates"] = [
        "financial_market_sentiment|driver|increase|글로벌|단기",
        "direct_gas_demand|transmission|increase|동북아|단기",
        "weather_demand|primary|increase|동북아|단기",
    ]

    readable = V4ReadableEventAnalysisDraft.model_validate(payload)
    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": "동북아 한파 지속 전망"},
    )
    result = finalize_v4_event_impact_analysis(
        draft,
        event_ids=[101],
        impact_levers=_catalog(),
    )

    assert [step.path_role for step in result.impact_paths[0].lever_steps] == [
        "driver",
        "transmission",
        "primary",
    ]
    assert [step.impact_lever_id for step in result.impact_paths[0].lever_steps] == [3, 4, 1]

    payload["impacts"][0]["leverStates"].append(
        "liquefaction_availability|transmission|decrease|US Gulf|단기",
    )
    with pytest.raises(ValueError, match="leverStates"):
        V4ReadableEventAnalysisDraft.model_validate(payload)


def test_v4_readable_event_allows_three_facts_and_impacts_and_rejects_four() -> None:
    facts = [
        "동북아 한파 지속 전망",
        "역내 LNG 재고가 평년보다 낮다.",
        "현물 LNG 선박 가용성이 감소했다.",
    ]

    facts_payload = _readable_event_draft(101).model_dump(by_alias=True)
    facts_payload["eventFacts"] = list(facts)
    assert len(V4ReadableEventAnalysisDraft.model_validate(facts_payload).event_facts) == 3
    facts_payload["eventFacts"].append("네 번째 사실")
    with pytest.raises(ValueError, match="eventFacts"):
        V4ReadableEventAnalysisDraft.model_validate(facts_payload)

    impacts_payload = _readable_event_draft(101).model_dump(by_alias=True)
    base_impact = impacts_payload["impacts"][0]
    impacts_payload["impacts"] = [
        {
            **base_impact,
            "evidence": [fact],
            "analysis": f"{fact}가 LNG 수급 경로를 바꿔 JKM에 단기 상승 압력을 주는 영향 {index}이다.",
        }
        for index, fact in enumerate(facts, start=1)
    ]
    impacts_payload["openQuestions"][0]["impact"] = 3
    assert len(V4ReadableEventAnalysisDraft.model_validate(impacts_payload).impacts) == 3
    impacts_payload["impacts"].append(dict(impacts_payload["impacts"][-1]))
    with pytest.raises(ValueError, match="impacts"):
        V4ReadableEventAnalysisDraft.model_validate(impacts_payload)


def test_v4_readable_event_allows_three_evidence_items_and_rejects_four() -> None:
    facts = [
        "동북아 한파 지속 전망",
        "역내 LNG 재고가 평년보다 낮다.",
        "현물 LNG 선박 가용성이 감소했다.",
    ]
    payload = _readable_event_draft(101).model_dump(by_alias=True)
    payload["eventFacts"] = facts
    payload["impacts"][0]["evidence"] = list(facts)

    parsed = V4ReadableEventAnalysisDraft.model_validate(payload)

    assert parsed.impacts[0].evidence == facts
    draft = expand_v4_readable_event_analysis(
        parsed,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={f"f{index}": fact for index, fact in enumerate(facts, start=1)},
    )
    assert draft.impact_paths[0].source_fact_ids == ["e101_f1", "e101_f2", "e101_f3"]

    payload["impacts"][0]["evidence"].append("네 번째 사실")
    with pytest.raises(ValueError, match="evidence"):
        V4ReadableEventAnalysisDraft.model_validate(payload)


def test_v4_readable_event_moves_candidate_one_to_primary_fact() -> None:
    candidates = {"f1": "동북아 한파 지속 전망", "f2": "역내 LNG 재고가 평년보다 낮다."}
    readable = _readable_event_draft(101)
    readable.event_facts = [candidates["f2"], candidates["f1"]]
    readable.impacts[0].evidence = readable.event_facts

    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates=candidates,
    )

    assert [fact.observed_basis for fact in draft.event_facts] == [candidates["f1"], candidates["f2"]]
    assert [fact.fact_id for fact in draft.event_facts] == ["e101_f1", "e101_f2"]
    assert draft.impact_paths[0].source_fact_ids == ["e101_f2", "e101_f1"]


def test_v4_readable_event_requires_candidate_one_when_impacts_exist() -> None:
    candidates = {"f1": "동북아 한파 지속 전망", "f2": "역내 LNG 재고가 평년보다 낮다."}
    readable = _readable_event_draft(101)
    readable.event_facts = [candidates["f2"]]
    readable.impacts[0].evidence = readable.event_facts

    with pytest.raises(ValueError, match="Fact candidate 1"):
        expand_v4_readable_event_analysis(
            readable,
            event_id=101,
            observed_at="2026-08-05",
            fact_candidates=candidates,
        )


def _two_impact_readable(primary_state: str, supporting_state: str) -> V4ReadableEventAnalysisDraft:
    facts = ["호르무즈 해협 LNG 통항이 사실상 중단됨.", "동남아 수입업체들이 현물 공급 부족에 직면함."]
    return V4ReadableEventAnalysisDraft.model_validate(
        {
            "eventFacts": facts,
            "decisionBasis": [],
            "impacts": [
                {
                    "evidence": [fact],
                    "analysis": f"{fact} 이 변화가 아시아 LNG 공급을 줄여 JKM에 단기 상승 압력을 준다.",
                    "leverStates": [state],
                    "balance": "trade|decrease",
                    "importance": "high",
                }
                for fact, state in zip(facts, [primary_state, supporting_state], strict=True)
            ],
            "openQuestions": [],
            "excludedBecause": None,
        },
    )


def test_v4_supporting_impact_must_differ_from_primary_route() -> None:
    readable = _two_impact_readable(
        "route_disruption|primary|disrupt|호르무즈 해협|단기",
        "route_disruption|primary|disrupt| 호르무즈  해협 |단기",
    )

    with pytest.raises(ValueError, match="Impact 2 repeats Impact 1 with the same Lever, direction, scope and timing"):
        expand_v4_readable_event_analysis(
            readable,
            event_id=1157,
            observed_at=None,
            fact_candidates={"f1": readable.event_facts[0], "f2": readable.event_facts[1]},
        )


@pytest.mark.parametrize(
    "supporting_state",
    [
        "route_disruption|primary|disrupt|동남아 수입국|단기",  # 같은 Lever, 다른 대상
        "route_disruption|primary|recover|호르무즈 해협|단기",  # 같은 Lever, 다른 방향
        "route_disruption|primary|disrupt|호르무즈 해협|중기",  # 같은 Lever, 다른 시점
        "inventory_condition|primary|decrease|호르무즈 해협|단기",  # 다른 Lever
    ],
)
def test_v4_supporting_impact_on_same_lever_is_kept_when_route_differs(supporting_state: str) -> None:
    readable = _two_impact_readable("route_disruption|primary|disrupt|호르무즈 해협|단기", supporting_state)

    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=1157,
        observed_at=None,
        fact_candidates={"f1": readable.event_facts[0], "f2": readable.event_facts[1]},
    )

    assert [path.source_fact_ids for path in draft.impact_paths] == [["e1157_f1"], ["e1157_f2"]]


def test_v4_three_facts_hydrate_to_ordered_paths_and_preserve_lineage() -> None:
    facts = [
        "동북아 한파 지속 전망",
        "역내 LNG 재고가 평년보다 낮다.",
        "현물 LNG 선박 가용성이 감소했다.",
    ]
    readable = V4ReadableEventAnalysisDraft.model_validate(
        {
            "eventFacts": facts,
            "decisionBasis": [],
            "impacts": [
                {
                    "evidence": [fact],
                    "analysis": f"{fact}가 동북아 LNG 수요를 바꾸는 대표 경로 {index}로 JKM에 단기 상승 압력을 준다.",
                    # 같은 Lever라도 대상(scope)이 다르면 별도 경로로 인정한다.
                    "leverStates": [f"weather_demand|primary|increase|{scope}|단기"],
                    "balance": "demand|increase",
                    "importance": "high" if index == 1 else "medium",
                }
                for index, (fact, scope) in enumerate(zip(facts, ["동북아", "한국", "일본"], strict=True), start=1)
            ],
            "openQuestions": [
                {
                    "impact": 3,
                    "question": "세 번째 경로의 영향은 언제까지 지속되는가?",
                    "axis": "duration",
                    "lever": "weather_demand",
                },
            ],
            "excludedBecause": None,
        },
    )

    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={f"f{index}": fact for index, fact in enumerate(facts, start=1)},
    )
    result = finalize_v4_event_impact_analysis(
        draft,
        event_ids=[101],
        impact_levers=_catalog(),
    )

    assert [fact.fact_id for fact in result.event_facts] == ["e101_f1", "e101_f2", "e101_f3"]
    assert [fact.observed_basis for fact in result.event_facts] == facts
    assert [path.impact_path_id for path in result.impact_paths] == ["e101_p1", "e101_p2", "e101_p3"]
    assert [path.source_fact_ids for path in result.impact_paths] == [
        ["e101_f1"],
        ["e101_f2"],
        ["e101_f3"],
    ]
    assert result.path_uncertainties[0].impact_path_ids == ["e101_p3"]


def test_v4_three_selected_facts_still_reject_an_unused_fact() -> None:
    readable = _readable_event_draft(101)
    facts = [
        "동북아 한파 지속 전망",
        "역내 LNG 재고가 평년보다 낮다.",
        "현물 LNG 선박 가용성이 감소했다.",
    ]
    readable.event_facts = facts
    readable.impacts[0].evidence = facts[:2]

    with pytest.raises(ValueError, match="every selected Event Fact"):
        expand_v4_readable_event_analysis(
            readable,
            event_id=101,
            observed_at="2026-08-05",
            fact_candidates={f"f{index}": fact for index, fact in enumerate(facts, start=1)},
        )


def test_v4_readable_event_fact_requires_character_exact_match() -> None:
    readable = _readable_event_draft(101)
    readable.event_facts = ["동북아  한파 지속 전망"]
    readable.impacts[0].evidence = readable.event_facts

    with pytest.raises(ValueError, match="outside the provided candidates"):
        expand_v4_readable_event_analysis(
            readable,
            event_id=101,
            observed_at="2026-08-05",
            fact_candidates={"f1": "동북아 한파 지속 전망"},
        )


def test_v4_fact_ids_follow_selected_array_order_and_preserve_modality() -> None:
    readable = _readable_event_draft(101)
    forecast = "기상기관은 다음 주 한파가 이어질 것으로 전망했다."
    announced = "정부는 LNG 비축 확대 계획을 발표했다."
    readable.event_facts = [forecast, announced]
    readable.impacts[0].evidence = [forecast, announced]

    result = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": forecast, "f2": announced},
    )

    assert [fact.fact_id for fact in result.event_facts] == ["e101_f1", "e101_f2"]
    assert [fact.observed_basis for fact in result.event_facts] == [forecast, announced]
    assert result.impact_paths[0].source_fact_ids == ["e101_f1", "e101_f2"]


def test_v4_fact_candidates_do_not_truncate_the_source_sentence() -> None:
    fact = "장기 전망 " + ("상승 가능성을 검토했으며 " * 20) + "아직 확정하지 않았다고 발표했다."

    candidates = build_v4_event_fact_candidates({"mi_event_id": 101, "key_bullets": [fact]})

    assert candidates == {"f1": fact}


@pytest.mark.parametrize(
    "sentence",
    [
        "신규 보도에 LNG선, LNG 화물, 가스 설비 피해나 카타르 LNG 수출 차질은 명시되지 않음.",
        "본 Event와 직접 연결된 가격 반응은 신규 근거에서 확인되지 않음",
        "피해 범위와 규모는 아직 확인되지 않았음.",
        "신규 기사에서 확정 물량 변화는 확인되지 않아 단기 실물 수급 변화 근거는 제한적임.",
        "국가·터미널별 실제 utilization 변동 근거는 포함되지 않음.",
        "Sakhalin-2 제재·운영·정비·생산 상태 변화에 대한 신규 근거 부재임.",
        # 앞 절도 미확인 진술이면 혼합 문장이 아니다.
        "신규 리포트는 터키 발전용 가스 수요 수치를 제시하지 않았으며, 기존 사건의 상태 변경은 확인되지 않음.",
    ],
)
def test_v4_unconfirmed_statement_detects_sentences_that_conclude_with_absence(sentence: str) -> None:
    assert is_v4_unconfirmed_statement(sentence)


@pytest.mark.parametrize(
    "sentence",
    [
        "신규 기사에 JKM 가격 수치는 제시되지 않았으나, 공급 확대 신호는 LNG 프리미엄 하방 압력으로 작용할 수 있음.",
        "미 중부사령부는 상선 55척이 통과했다고 밝혀 즉각적인 물동량 중단은 확인되지 않았으며, 이는 차질을 제한하는 요인임.",
        "Freeport LNG는 10월 2일 압축기 정비로 Train 2를 중단함.",
        # 앞 절에 관측 사실이 있는 혼합 문장 (1168 재고 근거가 빠져 inventory_condition이 사라진 회귀)
        "일본 주요 전력사 LNG 재고는 직전 공표 기준 저점 수준으로 언급되었으며 최신 수치 업데이트는 신규 근거에서 확인되지 않음.",
        "러시아가 해당 시설에 대규모 드론 공격을 가했으며, 피해 범위와 규모는 아직 확인되지 않았음.",
    ],
)
def test_v4_unconfirmed_statement_keeps_substantive_sentences(sentence: str) -> None:
    assert not is_v4_unconfirmed_statement(sentence)


def test_v4_fact_candidates_exclude_unconfirmed_supporting_statements() -> None:
    primary = "Troll 가스전 비계획 가동 중단으로 노르웨이 가스 공급이 56 mcm/d 감소함."
    unconfirmed = "본 Event와 직접 연결된 TTF·JKM 가격 반응은 신규 근거에서 확인되지 않음."
    supporting = "유럽 저장률은 68.8%로 전년 대비 12.1%포인트 낮음."
    event = {"mi_event_id": 101, "one_line_summary": "Troll 차질 지속", "key_bullets": [primary, unconfirmed, supporting]}

    assert build_v4_event_fact_candidates(event) == {"f1": primary, "f2": supporting}


def test_v4_fact_candidates_use_summary_as_primary_when_headline_bullet_is_unconfirmed() -> None:
    unconfirmed = "이번 신규 기록에서는 해당 설비의 복구·연장·물량 변화가 직접 확인되지 않음."
    background = "동일 기간 호르무즈 통항 리스크가 아시아 LNG 가격 상승을 주도함."
    summary = "[노르웨이 가스 공급] Troll 비계획 중단 지속 → 유럽 가스 공급 제약"
    event = {"mi_event_id": 101, "one_line_summary": summary, "key_bullets": [unconfirmed, background]}

    assert build_v4_event_fact_candidates(event) == {"f1": summary, "f2": background}


def test_v4_fact_candidates_use_summary_when_headline_is_mixed_but_keep_it_as_a_candidate() -> None:
    headline = (
        "아시아 단기 공급 보고는 MLNG Dua 정지와 Tangguh LNG 약세를 강조했으며, Sakhalin-2 상태 변경의 직접 근거는 제시되지 않음."
    )
    constraint = "러시아 법인 전환 이후 제재와 예비부품 접근 제약 지속으로 운영 안정성 리스크 잔존임."
    summary = "[러시아 LNG 제재] Sakhalin-2 상태 업데이트 부재 → 운영·정비 리스크 유지"
    event = {"mi_event_id": 1184, "one_line_summary": summary, "key_bullets": [headline, constraint]}

    assert build_v4_event_fact_candidates(event) == {"f1": summary, "f2": headline, "f3": constraint}


def test_v4_fact_candidates_fall_back_to_summary_when_every_bullet_is_unconfirmed() -> None:
    event = {
        "mi_event_id": 101,
        "one_line_summary": "Cove Point LNG가 약 5주간 연례 정비로 생산을 중단함.",
        "key_bullets": ["신규 리포트에는 정비 종료나 생산 재개 정보가 포함되지 않음."],
    }

    assert build_v4_event_fact_candidates(event) == {"f1": "Cove Point LNG가 약 5주간 연례 정비로 생산을 중단함."}


@pytest.mark.parametrize(
    ("dates", "expected"),
    [
        ({"oldest_record_first_created": "2026-06-01T00:00:00", "latest_record_first_created": "2026-07-20T23:00:00"},
         "- 관련 기록 기간: 2026-06-01 ~ 2026-07-20 (원문 기록 수집 시점)"),
        ({"oldest_record_first_created": "2026-07-20T23:00:00", "latest_record_first_created": "2026-07-20T23:00:00"},
         "- 관련 기록 기간: 2026-07-20 (원문 기록 수집 시점)"),
        ({"latest_record_first_created": "2026-07-20T23:00:00"}, "- 관련 기록 기간: 2026-07-20 (원문 기록 수집 시점)"),
    ],
)
def test_v4_event_prompt_falls_back_to_record_period_without_occurred_at(
    dates: dict[str, str],
    expected: str,
) -> None:
    lever = {"lever_code": "us_gom_hurricane_disruption", "domain": "supply", "applicability_hint": "GoM"}
    event = EventPayload.model_validate(
        {"mi_event_id": 1522, "event_type_l2_id": 11, "event_title_ko": "걸프만 셧인", "key_bullets": ["셧인"], **dates},
    )

    prompt = build_model_lever_user_prompt(
        events=[event.model_dump()], impact_levers=[lever], catalog_version="v4", analysis_as_of="2026-10-11"
    )

    assert "- 발생시각: 미제공\n" in prompt
    assert expected in prompt
    assert "관련 기록 기간은 사건이 관측된 연도·월입니다" in prompt
    assert "사건의 시작점이나 잔여 기간 계산의 기준으로는\n  쓰지 않습니다" in prompt
    # "Catalog 조건"을 직접 언급하면 모델이 다른 Lever의 적용 조건까지 엄격하게 읽어 Event를 제외했다 (1706).
    assert "Catalog의 적용 연도·월 조건" not in prompt


def test_v4_event_prompt_prefers_occurred_at_over_record_period() -> None:
    lever = {"lever_code": "us_gom_hurricane_disruption", "domain": "supply", "applicability_hint": "GoM"}
    with_time = {
        "mi_event_id": 101,
        "key_bullets": ["셧인"],
        "occurred_at": "2026-08-13T00:00:00",
        "latest_record_first_created": "2026-08-28T08:00:00",
    }
    without_dates = {"mi_event_id": 102, "key_bullets": ["셧인"]}

    timed = build_model_lever_user_prompt(
        events=[with_time], impact_levers=[lever], catalog_version="v4", analysis_as_of="2026-10-11"
    )
    undated = build_model_lever_user_prompt(
        events=[without_dates], impact_levers=[lever], catalog_version="v4", analysis_as_of="2026-10-11"
    )

    assert "- 발생시각: 2026-08-13T00:00:00\n" in timed
    assert "관련 기록 기간" not in timed
    assert "- 발생시각: 미제공\n" in undated
    assert "관련 기록 기간" not in undated


@pytest.mark.parametrize(
    ("semantic_axes", "expected"),
    [
        ("slot=B:Year(YYYY, 2026~2030); value=F:User Input Absolute Value ($/d)", "Year(YYYY, 2026~2030)"),
        (
            "slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: United States, Taiwan (China), Spain); "
            "value=F:% change(+/-)",
            "Year(YYYY, 2026~2030), Country",
        ),
        (
            "slot=Country(국가명; 예: Algeria), LNG Plant(예: Arzew GL1Z), LNG Plant Train(348개 basecase Train 중 선택; "
            "예: Angola LNG T1), Year(YYYY), Month(1~12); value=Utilization Rate",
            "Country, LNG Plant, LNG Plant Train, Year(YYYY), Month(1~12)",
        ),
        (
            "slot=J:Year(YYYY, 2026~2030), K:Country(국가명), value=M:Population (Thousands)",
            "Year(YYYY, 2026~2030), Country",
        ),
        (None, ""),
    ],
)
def test_summarize_parameter_slots_keeps_slot_names_and_ranges(semantic_axes: str | None, expected: str) -> None:
    assert summarize_parameter_slots(semantic_axes) == expected


def test_v4_event_prompt_renders_levers_by_meaning_and_parameter_slots() -> None:
    levers = [
        {
            "lever_code": "lng_charter_rate",
            "domain": "trade",
            "description": "연도별 LNG 선박 charter rate($/day)의 최종 절대값 변화",
            "applicability_hint": "선박 charter 시장의 전역·연간 충격에만 사용한다.",
            "parameter_bindings": [{"parameter_name": "ShippingCost", "support_status": "executable"}],
        },
        {
            "lever_code": "direct_gas_demand",
            "domain": "demand",
            "description": "국가·연월·수요 하위부문별 최종 가스수요 BCM 직접 입력",
            "applicability_hint": "exact Country·Year·Month·Demand Sub-Sector가 있을 때만 최후 수단으로 사용한다.",
            "parameter_bindings": [
                {
                    "parameter_name": "User-Adjusted Gas Demand",
                    "support_status": "known_unsupported",
                    "unsupported_reason_code": "INACTIVE_MODEL_PARAMETER",
                },
            ],
        },
        {"lever_code": "regional_price_spread", "domain": "price_only", "description": "상대 가격 spread 변화"},
    ]
    axes = {
        "ShippingCost": "slot=B:Year(YYYY, 2026~2030); value=F:User Input Absolute Value ($/d)",
        "User-Adjusted Gas Demand": "slot=D:Country, E:Year(YYYY, 2026~2030), F:Month(1~12), G:Demand Sub-Sector",
    }

    prompt = build_model_lever_user_prompt(
        events=[{"mi_event_id": 1682, "key_bullets": ["대서양 용선료 저점"]}],
        impact_levers=levers,
        catalog_version="v4",
        analysis_as_of="2026-10-12",
        parameter_axes=axes,
    )

    assert "- lng_charter_rate: 연도별 LNG 선박 charter rate($/day)의 최종 절대값 변화" in prompt
    assert "· ShippingCost [사용 가능] 필요 slot: Year(YYYY, 2026~2030)" in prompt
    assert "· User-Adjusted Gas Demand [비활성(모델 입력 불가)] 필요 slot: Country, Year(YYYY, 2026~2030)" in prompt
    assert "- regional_price_spread: 상대 가격 spread 변화\n  · binding 없음" in prompt
    # 자연어 적용 조건은 Lever 탈락의 원인이었으므로 Event 분석 프롬프트에 넣지 않는다 (1682·1706·1309).
    assert "전역·연간 충격에만" not in prompt
    assert "최후 수단" not in prompt
    assert "세부 slot이 없다는 이유만으로\n     Lever를 버리거나 Event를 제외하지 않습니다" in prompt
    assert "위험·가능성·업데이트 부재만 있으면 binding 없는 price_only Lever" in prompt
    assert "binding parameter가 비활성이거나 사실의 Year가 범위 밖이면" in prompt
    assert "적용 조건을 이 Event의 사실이 실제로 충족할 때만" not in prompt


def _catalog_blocked_readable(**overrides: object) -> V4ReadableEventAnalysisDraft:
    payload: dict[str, object] = {
        "eventFacts": ["대서양 용선료가 저점에서 보합을 유지함."],
        "decisionBasis": [],
        "impacts": [],
        "openQuestions": [],
        "excludedBecause": "운임 영향은 있으나 맞는 Lever의 조건을 충족하지 않는다.",
        "excludedReason": "catalog_condition_unmet",
        "blockedLevers": ["direct_gas_demand"],
    }
    payload.update(overrides)
    return V4ReadableEventAnalysisDraft.model_validate(payload)


def test_v4_catalog_condition_unmet_exclusion_is_hydrated_and_finalized() -> None:
    readable = _catalog_blocked_readable()
    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=1682,
        observed_at=None,
        fact_candidates={"f1": "대서양 용선료가 저점에서 보합을 유지함."},
    )

    result = finalize_v4_event_impact_analysis(draft, event_ids=[1682], impact_levers=_catalog())

    assert [(item.reason_type, item.blocked_lever_codes) for item in result.event_exclusions] == [
        ("catalog_condition_unmet", ["direct_gas_demand"]),
    ]


def test_v4_exclusion_without_reason_defaults_to_no_material_impact() -> None:
    readable = _catalog_blocked_readable(excludedReason=None, blockedLevers=[])
    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=1682,
        observed_at=None,
        fact_candidates={"f1": "대서양 용선료가 저점에서 보합을 유지함."},
    )

    assert [(item.reason_type, item.blocked_lever_codes) for item in draft.event_exclusions] == [
        ("no_material_impact", []),
    ]


def test_v4_catalog_condition_unmet_rejects_unknown_blocked_levers() -> None:
    draft = expand_v4_readable_event_analysis(
        _catalog_blocked_readable(blockedLevers=["not_in_catalog"]),
        event_id=1682,
        observed_at=None,
        fact_candidates={"f1": "대서양 용선료가 저점에서 보합을 유지함."},
    )

    with pytest.raises(ValueError, match="blockedLevers must be catalog Lever codes"):
        finalize_v4_event_impact_analysis(draft, event_ids=[1682], impact_levers=_catalog())


@pytest.mark.parametrize(
    ("overrides", "expected_reason", "expected_blocked"),
    [
        ({"eventFacts": [], "excludedBecause": "사용할 사실이 없다."}, None, []),
        ({"excludedReason": "no_material_impact"}, "no_material_impact", []),
        (
            {"blockedLevers": ["direct_gas_demand", "direct_gas_demand"]},
            "catalog_condition_unmet",
            ["direct_gas_demand"],
        ),
    ],
)
def test_v4_readable_exclusion_reason_normalizes_inconsistent_fields(
    overrides: dict[str, object],
    expected_reason: str | None,
    expected_blocked: list[str],
) -> None:
    # 모순된 사유·Lever 조합은 분석 내용에 영향이 없으므로 재시도 대신 정규화한다.
    readable = _catalog_blocked_readable(**overrides)

    assert (readable.excluded_reason, readable.blocked_levers) == (expected_reason, expected_blocked)


def test_v4_stored_exclusion_without_blocked_levers_still_loads() -> None:
    exclusion = V4EventAnalysisExclusion.model_validate(
        {"eventId": 1309, "reasonType": "no_material_impact", "reason": "중요한 영향 없음"},
    )

    assert exclusion.blocked_lever_codes == []


def test_v4_event_markdown_labels_catalog_condition_exclusions() -> None:
    from apps.agents.scenario_group_agent import presentation

    markdown = presentation._v4_event_markdown(
        [{"mi_event_id": 1682, "event_title_ko": "대서양 운임"}, {"mi_event_id": 1309, "event_title_ko": "EU 메탄"}],
        {
            "event_exclusions": [
                {"event_id": 1682, "reason_type": "catalog_condition_unmet", "reason": "Lever 조건 미충족"},
                {"event_id": 1309, "reason_type": "no_material_impact", "reason": "중요한 영향 없음"},
            ],
        },
    )

    assert "- 분석 제외(Catalog 조건 미충족): Lever 조건 미충족" in markdown
    assert "- 분석 제외: 중요한 영향 없음" in markdown


def test_v4_event_prompt_explains_exclusion_reason_types() -> None:
    prompt = build_model_lever_user_prompt(
        events=[{"mi_event_id": 1682, "key_bullets": ["대서양 용선료 저점"]}],
        impact_levers=[],
        catalog_version="v4",
        analysis_as_of="2026-10-12",
    )

    assert "· catalog_condition_unmet: LNG 시장 영향은 있지만 의미가 맞는 Lever를 위 규칙" in prompt
    # 새 유형이 제외를 늘리지 않도록 price_only로 설명할 수 있으면 제외하지 않는다 (1706: 4/4 제외 → 1/3).
    assert "price_only Lever로도 영향 경로를 설명할 수 없어 제외할 때만 씁니다" in prompt
    assert "blockedLevers에 검토했지만 쓸 수 없었던\n    Lever code를 최대 3개" in prompt
    assert "· no_material_impact: 그 밖에 LNG 시장에 중요한 영향이 없을 때" in prompt


def test_v4_event_prompt_omits_unconfirmed_statements_entirely() -> None:
    unconfirmed = "본 Event와 직접 연결된 JKM 가격 반응은 신규 근거에서 확인되지 않음."
    primary = "카타르에너지는 Edison에 대한 LNG 인도를 12월 초까지 재개하지 못한다고 밝힘."
    lever = {"lever_code": "weather_demand", "domain": "demand", "applicability_hint": "한파·폭염"}
    event = {"mi_event_id": 101, "event_title_ko": "카타르 불가항력", "key_bullets": [primary, unconfirmed]}

    prompt = build_model_lever_user_prompt(
        events=[event], impact_levers=[lever], catalog_version="v4", analysis_as_of="2026-10-09"
    )

    assert f"1. {primary}" in prompt
    # 미확인 문장을 별도 섹션으로 보여 주면 모델이 Catalog 조건을 엄격하게 읽어 Lever·Event를 버렸다
    # (1522 GoM Lever 0/5 → 섹션 제거 3/5, 1706 제외 3/4 → 섹션 제거 1/5).
    assert unconfirmed not in prompt
    assert "확인되지 않은 사항" not in prompt


def _readable_interaction_draft() -> V4ReadableInteractionAnalysisDraft:
    return V4ReadableInteractionAnalysisDraft.model_validate(
        {
            "interactions": [
                {
                    "paths": ["E101-P1", "E202-P1"],
                    "analysis": "동북아 수요 증가와 미국 공급 감소가 동시에 단기 JKM 상승 압력을 강화한다.",
                    "relation": "amplification",
                },
            ],
            "openQuestions": [
                {
                    "interaction": 1,
                    "question": "두 충격이 실제로 겹치는 기간은 얼마인가?",
                    "axis": "duration",
                    "lever": "financial_market_sentiment",
                },
            ],
        },
    )


def _interaction_budget_analysis(
    event_count: int,
    *,
    event_question_count: int = 0,
    two_paths_for_first_event: bool = False,
) -> V4EventImpactAnalysisResult:
    paths: list[dict[str, object]] = []
    for event_id in range(1, event_count + 1):
        path_count = 2 if event_id == 1 and two_paths_for_first_event else 1
        for path_index in range(1, path_count + 1):
            path_id = f"path_{event_id}_{path_index}"
            paths.append(
                {
                    "impactPathId": path_id,
                    "eventId": event_id,
                    "sourceFactIds": [f"fact_{event_id}_{path_index}"],
                    "mechanism": f"Event {event_id} 영향 경로 {path_index}",
                    "leverSteps": [
                        {
                            "impactLeverId": event_id,
                            "leverCode": f"lever_{event_id}",
                            "pathRole": "primary" if path_index == 1 else "transmission",
                            "stateDirection": "increase",
                            "scope": "글로벌 LNG",
                            "timing": "단기",
                        },
                    ],
                    "materiality": "high",
                },
            )
    uncertainties = []
    primary_paths = [path for path in paths if str(path["impactPathId"]).endswith("_1")]
    axes = ["magnitude", "scope", "timing", "duration", "recovery", "mitigation", "substitution"]
    for index in range(event_question_count):
        path = primary_paths[index % len(primary_paths)]
        event_id = int(path["eventId"])
        path_id = str(path["impactPathId"])
        uncertainties.append(
            {
                "uncertaintyId": f"event_u{index + 1}",
                "impactPathIds": [path_id],
                "axisType": axes[index % len(axes)],
                "subject": f"Event 질문 {index + 1}",
                "affectedLeverCode": f"lever_{event_id}",
                "reason": f"Event 질문 {index + 1}",
                "materiality": "high",
                "semanticKey": f"{path_id}:{axes[index % len(axes)]}:{index + 1}",
            },
        )
    return V4EventImpactAnalysisResult.model_validate(
        {
            "impactPaths": paths,
            "pathUncertainties": uncertainties,
        },
    )


def test_v4_readable_interaction_question_reports_allowed_path_levers() -> None:
    readable = _readable_interaction_draft()
    readable.open_questions[0].lever = "direct_gas_demand"

    with pytest.raises(ValueError, match=r"Interaction 1 Path Lever codes"):
        merge_v4_readable_interactions(_analysis(), readable)


def test_v4_readable_interaction_question_count_is_not_schema_limited() -> None:
    payload = _readable_interaction_draft().model_dump(by_alias=True)
    payload["openQuestions"].append(dict(payload["openQuestions"][0]))

    assert len(V4ReadableInteractionAnalysisDraft.model_validate(payload).open_questions) == 2


@pytest.mark.parametrize(
    ("event_count", "expected_limit"),
    [(2, 1), (3, 2), (4, 3), (5, 3)],
)
def test_v4_interaction_count_overage_is_deterministically_capped(
    event_count: int,
    expected_limit: int,
) -> None:
    analysis = _interaction_budget_analysis(event_count)
    interactions = [
        {
            "paths": [f"E{pair_index % event_count + 1}-P1", f"E{(pair_index + 1) % event_count + 1}-P1"],
            "analysis": f"중요도 {pair_index + 1}의 서로 다른 Event 결합 효과가 단기 JKM 분기를 만든다.",
            "relation": "amplification",
        }
        for pair_index in range(5)
    ]
    readable = V4ReadableInteractionAnalysisDraft.model_validate({"interactions": interactions})

    merged = merge_v4_readable_interactions(analysis, readable, event_count=event_count)

    assert [item.interaction_id for item in merged.interactions] == [
        f"i{index}" for index in range(1, expected_limit + 1)
    ]
    assert len(merged.interactions) == expected_limit
    assert any(warning.code == "INTERACTION_COUNT_LIMIT_APPLIED" for warning in merged.validation_warnings)


def test_v4_same_event_interaction_is_dropped_before_budget_and_references_are_renumbered() -> None:
    analysis = _interaction_budget_analysis(3, two_paths_for_first_event=True)
    readable = V4ReadableInteractionAnalysisDraft.model_validate(
        {
            "interactions": [
                {
                    "paths": ["E1-P1", "E2-P1"],
                    "analysis": "첫 번째 cross-Event 결합 효과가 단기 JKM 상승 분기를 강화한다.",
                    "relation": "amplification",
                },
                {
                    "paths": ["E1-P1", "E1-P2"],
                    "analysis": "동일 Event 내부의 원인과 전달 경로를 별도 관계로 잘못 구성했다.",
                    "relation": "causal_link",
                },
                {
                    "paths": ["E2-P1", "E3-P1"],
                    "analysis": "세 번째 원래 Interaction의 cross-Event 효과가 JKM 분기를 만든다.",
                    "relation": "offset",
                },
            ],
            "openQuestions": [
                {"interaction": 1, "question": "첫 결합 기간은?", "axis": "duration", "lever": "lever_1"},
                {"interaction": 2, "question": "내부 결합 기간은?", "axis": "duration", "lever": "lever_1"},
                {"interaction": 3, "question": "셋째 결합 기간은?", "axis": "duration", "lever": "lever_2"},
            ],
        },
    )

    merged = merge_v4_readable_interactions(analysis, readable, event_count=3)

    assert [item.interaction_id for item in merged.interactions] == ["i1", "i2"]
    assert [item.interaction_id for item in merged.interaction_uncertainties] == ["i1", "i2"]
    assert [item.uncertainty_id for item in merged.interaction_uncertainties] == ["iu1", "iu2"]
    same_event_warning = next(
        warning for warning in merged.validation_warnings if warning.code == "SAME_EVENT_INTERACTION_DROPPED"
    )
    assert same_event_warning.reference_ids == ["2", "1", "E1-P1", "E1-P2"]
    assert "연결 질문 1개" in same_event_warning.message


def test_v4_interaction_questions_use_one_per_interaction_and_final_ten_question_budget() -> None:
    analysis = _interaction_budget_analysis(4, event_question_count=8)
    readable = V4ReadableInteractionAnalysisDraft.model_validate(
        {
            "interactions": [
                {
                    "paths": [f"E{index}-P1", f"E{index + 1}-P1"],
                    "analysis": f"Interaction {index}의 결합 효과가 단기 JKM 분기를 만든다.",
                    "relation": "amplification",
                }
                for index in range(1, 4)
            ],
            "openQuestions": [
                {
                    "interaction": interaction,
                    "question": f"Interaction {interaction} 질문 {question}",
                    "axis": "duration" if question == 1 else "timing",
                    "lever": f"lever_{interaction}",
                }
                for interaction in range(1, 4)
                for question in range(1, 3)
            ],
        },
    )

    merged = merge_v4_readable_interactions(analysis, readable, event_count=4)

    assert len(merged.interactions) == 3
    assert len(merged.path_uncertainties) + len(merged.interaction_uncertainties) == 10
    assert [item.interaction_id for item in merged.interaction_uncertainties] == ["i1", "i2"]
    assert [item.subject for item in merged.interaction_uncertainties] == [
        "Interaction 1 질문 1",
        "Interaction 2 질문 1",
    ]
    assert any(warning.code == "INTERACTION_OPEN_QUESTION_LIMIT_APPLIED" for warning in merged.validation_warnings)


def _readable_dimension_draft() -> V4ReadableDimensionDesignDraft:
    def dimension(
        source: str,
        label: str,
        question: str,
        lever: str,
        axis: str,
        low_label: str,
        high_label: str,
        low_state: str,
        high_state: str,
    ) -> dict[str, object]:
        return {
            "from": [source],
            "label": label,
            "question": question,
            "rationale": f"{label[:10]} 분기 기준",
            "lever": lever,
            "axis": axis,
            "unit": "주" if axis == "recovery" else None,
            "choices": [
                {
                    "label": low_label,
                    "states": [low_state],
                    "pressure": "bearish",
                    "why": (f"관측된 시장 사실을 기반으로, {low_label} 상태가 이어지고 JKM 상승 압력이 완화되는 가정."),
                },
                {
                    "label": high_label,
                    "states": [high_state],
                    "pressure": "bullish",
                    "why": (
                        f"관측된 시장 사실을 기반으로, {high_label} 상태가 이어지고 JKM 상승 압력이 강화되는 가정."
                    ),
                },
            ],
        }

    return V4ReadableDimensionDesignDraft.model_validate(
        {
            "dimensions": [
                dimension(
                    "U1",
                    "동북아 한파와 추가 LNG 수요",
                    "한파에 따른 추가 LNG 수요 규모는 얼마인가?",
                    "weather_demand",
                    "magnitude",
                    "한파 수요가 기존 공급에 흡수",
                    "추가 LNG 조달 수요가 확대",
                    "weather_demand|unchanged|limited|동북아|단기",
                    "weather_demand|increase|high|동북아|단기",
                ),
                dimension(
                    "U2",
                    "미국 액화시설 재가동과 공급 회복",
                    "액화시설은 언제 재가동되는가?",
                    "liquefaction_availability",
                    "recovery",
                    "액화시설 정상 가동이 빠르게 회복",
                    "액화시설 차질과 공급 손실 지속",
                    "liquefaction_availability|recover|high_availability|US Gulf|2주",
                    "liquefaction_availability|disrupt|low_availability|US Gulf|6주 이상",
                ),
                dimension(
                    "U3",
                    "공급 차질과 글로벌 위험 프리미엄",
                    "공급 차질 위험 프리미엄은 얼마나 확대되는가?",
                    "financial_market_sentiment",
                    "magnitude",
                    "공급 우려 완화로 프리미엄 축소",
                    "공급 차질 우려와 프리미엄 확대",
                    "financial_market_sentiment|decrease|low_premium|글로벌|단기",
                    "financial_market_sentiment|increase|high_premium|글로벌|단기",
                ),
            ],
            "notUsed": [],
        },
    )


def test_v4_readable_dimension_omits_format_and_derives_value_kind() -> None:
    readable = _readable_dimension_draft()
    payload = readable.model_dump(by_alias=True)

    assert all("format" not in dimension for dimension in payload["dimensions"])
    expanded = expand_v4_readable_dimension_design(readable, impact_analysis=_analysis())
    assert [dimension.value_kind for dimension in expanded.dimension_definitions] == [
        "categorical",
        "temporal",
        "categorical",
    ]

    six_dimension_payload = dict(payload)
    six_dimension_payload["dimensions"] = [
        dict(payload["dimensions"][index % len(payload["dimensions"])]) for index in range(6)
    ]
    six_dimensions = V4ReadableDimensionDesignDraft.model_validate(six_dimension_payload)
    assert (
        len(expand_v4_readable_dimension_design(six_dimensions, impact_analysis=_analysis()).dimension_definitions) == 6
    )

    numeric_payload = readable.model_dump(by_alias=True)
    numeric_payload["dimensions"][0]["unit"] = "%"
    numeric = V4ReadableDimensionDesignDraft.model_validate(numeric_payload)
    numeric_expanded = expand_v4_readable_dimension_design(numeric, impact_analysis=_analysis())
    assert numeric_expanded.dimension_definitions[0].value_kind == "numeric_range"


def test_v4_readable_dimension_ignores_legacy_format() -> None:
    payload = _readable_dimension_draft().model_dump(by_alias=True)
    payload["dimensions"][0]["format"] = "temporal"

    readable = V4ReadableDimensionDesignDraft.model_validate(payload)
    expanded = expand_v4_readable_dimension_design(readable, impact_analysis=_analysis())

    assert "format" not in readable.model_dump(by_alias=True)["dimensions"][0]
    assert expanded.dimension_definitions[0].value_kind == "categorical"


def _readable_scenario_draft() -> V4ReadableScenarioSynthesisDraft:
    def scenario(title: str, choices: list[str], pressure: str, probability: int) -> dict[str, object]:
        return {
            "title": title,
            "narrative": (
                f"{title}에서는 검증된 공통 영향 위에 Scenario를 구분하는 핵심 조건과 선택된 분기가 함께 전개된다. "
                "선택된 영향 경로와 Event Interaction의 결합이 다른 효과를 상쇄하거나 강화해 최종 JKM 압력을 결정한다."
            ),
            "choices": choices,
            "interactions": ["I1"],
            "pressure": pressure,
            "explanation": "한파 수요와 공급 감소에 선택한 분기와 상호작용을 더해 JKM 압력을 설명한다.",
            "probability": probability,
            "relatedMarkets": (
                ["TTF|유럽과 아시아의 화물 경쟁도 영향을 받는다."] if pressure == "strong_bullish" else []
            ),
        }

    return V4ReadableScenarioSynthesisDraft.model_validate(
        {
            "description": (
                "동북아 한파 전망과 미국 Gulf LNG 액화시설 가동 중단이 관측됐다. "
                "수요 충격의 지속과 공급 차질의 전달·증폭, 기온 완화와 설비 회복에 따른 상쇄가 핵심 분기를 만든다."
            ),
            "scenarios": [
                scenario(
                    "한파 수요와 액화시설 차질이 결합되는 상방 천장",
                    ["D1.V2", "D2.V2", "D3.V2"],
                    "strong_bullish",
                    35,
                ),
                scenario(
                    "수요 증가와 공급 회복이 상쇄되는 기준 경로",
                    ["D1.V2", "D2.V1", "D3.V1"],
                    "balanced",
                    50,
                ),
                scenario(
                    "수요 완화와 공급 정상화가 겹치는 하방 바닥",
                    ["D1.V1", "D2.V1", "D3.V1"],
                    "strong_bearish",
                    15,
                ),
            ],
            "excluded": [
                {
                    "pressureBand": "bullish",
                    "reasonCode": "LOW_DISTINCTIVENESS",
                    "reason": "상단과 유사",
                    "choices": ["D1.V2", "D2.V1", "D3.V2"],
                },
                {
                    "pressureBand": "bearish",
                    "reasonCode": "LOW_DISTINCTIVENESS",
                    "reason": "하단과 유사",
                    "choices": ["D1.V1", "D2.V2", "D3.V1"],
                },
            ],
        },
    )


def test_v4_graph_parallelizes_events_and_retries_only_the_failed_event() -> None:
    calls: list[str] = []
    attempts_by_event = {101: 0, 202: 0}

    async def invoke_stage(
        *,
        output_schema: type[object],
        user_prompt: str,
        **_kwargs: object,
    ) -> object:
        calls.append(output_schema.__name__)
        if output_schema is V4ReadableEventAnalysisDraft:
            event_id = 101 if "- ID: 101" in user_prompt else 202
            attempts_by_event[event_id] += 1
            if event_id == 101 and attempts_by_event[event_id] == 1:
                raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail="analysis validation failed")
            return _readable_event_draft(event_id)
        if output_schema is V4ReadableInteractionAnalysisDraft:
            return _readable_interaction_draft()
        if output_schema is V4ReadableDimensionDesignDraft:
            return _readable_dimension_draft()
        if output_schema is V4GroupTitleDraft:
            return V4GroupTitleDraft(title="동북아 한파 지속 속 미국 액화시설 정비 지속성")
        return _readable_scenario_draft()

    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v4",
        generation_strategy="multi_event_model_lever_dimensions",
    )
    state = V4MultiEventGenerationState(
        scenario_group=group,
        events=[
            EventPayload(
                mi_event_id=101,
                event_type_l2_id=8,
                one_line_summary="한파로 난방 수요가 증가했다.",
                key_bullets=["동북아 한파 지속 전망"],
            ),
            EventPayload(
                mi_event_id=202,
                event_type_l2_id=12,
                one_line_summary="액화시설 유지보수가 시작됐다.",
                key_bullets=["미국 LNG 액화시설 가동 중단"],
            ),
        ],
        impact_levers=_catalog(),
        impact_catalog_version="v1",
        impact_catalog_checksum="checksum-v1",
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

    assert calls.count("V4ReadableEventAnalysisDraft") == 3
    assert calls[-4:] == [
        "V4ReadableInteractionAnalysisDraft",
        "V4ReadableDimensionDesignDraft",
        "V4ReadableScenarioSynthesisDraft",
        "V4GroupTitleDraft",
    ]
    assert attempts_by_event == {101: 2, 202: 1}
    assert final_state["analysis_attempt"] == 2
    assert final_state["interaction_attempt"] == 1
    assert final_state["dimension_attempt"] == 1
    assert final_state["scenario_attempt"] == 1
    persist.assert_called_once()
    assert persist.call_args.kwargs["title"] == "동북아 한파 지속 속 미국 액화시설 정비 지속성"
    assert persist.call_args.kwargs["summary"] == ("한파로 난방 수요가 증가했다. | 액화시설 유지보수가 시작됐다.")
    assert persist.call_args.kwargs["dimension_definitions"][0]["rationale"] == "동북아 한파와 추가 분기 기준"


def test_prepare_v4_fixes_analysis_as_of_for_the_run() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v4",
        generation_strategy="multi_event_model_lever_dimensions",
    )
    events = [
        EventPayload(mi_event_id=101, event_type_l2_id=8),
        EventPayload(mi_event_id=202, event_type_l2_id=12),
    ]
    payload = V4MultiEventCreateScenariosIn(miEventIds=[202, 101], userId=7)
    with (
        patch.object(v4_flow_module, "_analysis_as_of", return_value="2026-08-07"),
        patch.object(
            v4_flow_module,
            "get_settings",
            return_value=SimpleNamespace(
                scenario_group_v4_impact_catalog_version="v4.1",
                scenario_synthesis_policy="distinct_driver",
            ),
        ),
        patch.object(v4_flow_module.EventService, "load_events", return_value=events),
        patch.object(
            v4_flow_module.ModelImpactLeverService,
            "load_active_catalog",
            return_value=(_catalog(), "v1", "checksum-v1"),
        ) as load_active_catalog,
        patch.object(
            v4_flow_module.ModelImpactLeverService,
            "load_parameter_semantic_axes",
            return_value={"HurricaneIntensity": "slot=B:Year(YYYY, 2026~2030), C:Month(1~12)"},
        ),
        patch.object(
            v4_flow_module.ScenarioGroupService,
            "prepare_v4_multi_event_group",
            return_value=group,
        ),
    ):
        prepared = v4_flow_module.prepare_v4_multi_event_scenarios(payload)

    assert prepared["impact_parameter_axes"] == {"HurricaneIntensity": "slot=B:Year(YYYY, 2026~2030), C:Month(1~12)"}
    assert prepared["analysis_as_of"] == "2026-08-07"
    assert prepared["scenario_synthesis_policy"] == "distinct_driver"
    assert prepared["scenario_count_range"] == (3, 5)
    assert [event.mi_event_id for event in prepared["events"]] == [202, 101]
    load_active_catalog.assert_called_once_with(catalog_version="v4.1")


def test_v4_event_timeout_is_retried_without_blocking_the_batch() -> None:
    async def never_returns(**_kwargs: object) -> object:
        await asyncio.sleep(1)
        return _readable_event_draft(101)

    with (
        patch.object(v4_nodes, "invoke_stage_structured_output", side_effect=never_returns),
        patch.object(v4_nodes, "_backoff", new=AsyncMock()),
        patch.object(v4_nodes, "_stage_timeout_seconds", return_value=0.001),
    ):
        outcome = asyncio.run(
            v4_nodes._analyze_event_with_retries(
                event=EventPayload(
                    mi_event_id=101,
                    event_type_l2_id=8,
                    key_bullets=["동북아 한파 지속 전망"],
                ),
                impact_levers=_catalog(),
                catalog_version="v1",
                analysis_as_of="2026-08-07",
                trace_context=None,
            ),
        )

    assert outcome.attempts == 3
    assert outcome.result is None
    assert outcome.error == "Event 101 impact analysis exceeded 0.001s"


def test_v4_invalid_balance_is_included_in_event_retry_prompt() -> None:
    prompts: list[str] = []
    invalid = _readable_event_draft(101)
    invalid.impacts[0].balance = "none"
    corrected = _readable_event_draft(101)

    async def invoke_stage(*, user_prompt: str, **_kwargs: object) -> object:
        prompts.append(user_prompt)
        return invalid if len(prompts) == 1 else corrected

    with (
        patch.object(v4_nodes, "invoke_stage_structured_output", side_effect=invoke_stage),
        patch.object(v4_nodes, "_backoff", new=AsyncMock()),
    ):
        outcome = asyncio.run(
            v4_nodes._analyze_event_with_retries(
                event=EventPayload(
                    mi_event_id=101,
                    event_type_l2_id=8,
                    key_bullets=["동북아 한파 지속 전망"],
                ),
                impact_levers=_catalog(),
                catalog_version="v1",
                analysis_as_of="2026-08-07",
                trace_context=None,
            ),
        )

    assert outcome.attempts == 2
    assert outcome.result is not None
    assert len(prompts) == 2
    assert "이전 Event Impact Analysis 검증 실패" not in prompts[0]
    assert "e101_p1 balance cannot be none; weather_demand=demand. Use demand|<direction>." in prompts[1]
    assert "잘못된 영향 경로·Lever·balance·열린 질문만 수정" in prompts[1]


def test_v4_event_analysis_calls_are_concurrent() -> None:
    active_calls = 0
    max_active_calls = 0

    async def invoke_stage(*, user_prompt: str, **_kwargs: object) -> object:
        nonlocal active_calls, max_active_calls
        event_id = 101 if "- ID: 101" in user_prompt else 202
        active_calls += 1
        max_active_calls = max(max_active_calls, active_calls)
        await asyncio.sleep(0)
        active_calls -= 1
        return _readable_event_draft(event_id)

    state = V4MultiEventGenerationState(
        events=[
            EventPayload(mi_event_id=101, event_type_l2_id=8, key_bullets=["동북아 한파 지속 전망"]),
            EventPayload(mi_event_id=202, event_type_l2_id=12, key_bullets=["미국 LNG 액화시설 가동 중단"]),
        ],
        impact_levers=_catalog(),
        impact_catalog_version="v1",
    )
    with (
        patch.object(v4_nodes, "invoke_stage_structured_output", side_effect=invoke_stage),
        patch.object(v4_nodes, "_backoff", new=AsyncMock()),
    ):
        result = asyncio.run(v4_nodes.AnalyzeEventImpactsNode().run(state))

    assert max_active_calls == 2
    assert isinstance(result["analysis_draft"], V4EventImpactAnalysisDraft)


@pytest.mark.parametrize(
    ("event_count", "expected"),
    [
        (1, [3]),
        (2, [3, 3]),
        (3, [3, 3, 2]),
        (4, [2, 2, 2, 2]),
        (5, [2, 2, 2, 1, 1]),
    ],
)
def test_v4_event_question_budgets_follow_request_order(
    event_count: int,
    expected: list[int],
) -> None:
    captured: list[int | None] = []

    async def analyze_event(**kwargs: object) -> v4_nodes._EventAnalysisOutcome:
        captured.append(kwargs.get("open_question_budget"))  # type: ignore[arg-type]
        event = kwargs["event"]
        assert isinstance(event, EventPayload)
        return v4_nodes._EventAnalysisOutcome(
            event_id=int(event.mi_event_id),
            attempts=1,
            result=V4EventImpactAnalysisResult(),
        )

    state = V4MultiEventGenerationState(
        events=[EventPayload(mi_event_id=index + 1, event_type_l2_id=8) for index in range(event_count)],
    )
    with patch.object(v4_nodes, "_analyze_event_with_retries", side_effect=analyze_event):
        asyncio.run(v4_nodes.AnalyzeEventImpactsNode().run(state))

    assert event_open_question_budgets(event_count) == expected
    assert captured == expected


@pytest.mark.parametrize(
    ("event_count", "expected_budgets"),
    [
        (1, [3]),
        (2, [3, 3]),
        (3, [3, 3, 2]),
        (4, [2, 2, 2, 2]),
        (5, [2, 2, 2, 1, 1]),
    ],
)
def test_v4_event_question_overage_is_capped_in_output_order(
    event_count: int,
    expected_budgets: list[int],
) -> None:
    retained_counts: list[int] = []
    warning_counts: list[int] = []
    for event_id, budget in enumerate(expected_budgets, start=1):
        payload = _readable_event_draft(101).model_dump(by_alias=True)
        payload["openQuestions"] = [
            {
                "impact": 1,
                "question": f"Event {event_id} 중요 질문 {index}",
                "axis": axis,
                "lever": "weather_demand",
            }
            for index, axis in enumerate(["magnitude", "scope", "timing", "duration"], start=1)
        ]
        draft = expand_v4_readable_event_analysis(
            V4ReadableEventAnalysisDraft.model_validate(payload),
            event_id=event_id,
            observed_at="2026-08-05",
            fact_candidates={"f1": "동북아 한파 지속 전망"},
            open_question_limit=budget,
        )

        retained_counts.append(len(draft.path_uncertainties))
        warning_counts.append(
            sum(warning.code == "EVENT_OPEN_QUESTION_LIMIT_APPLIED" for warning in draft.validation_warnings),
        )
        assert [item.subject for item in draft.path_uncertainties] == [
            f"Event {event_id} 중요 질문 {index}" for index in range(1, budget + 1)
        ]

    assert retained_counts == expected_budgets
    assert warning_counts == [1] * event_count


def test_v4_single_event_skips_interaction_and_accepts_three_questions_without_warning() -> None:
    payload = _readable_event_draft(101).model_dump(by_alias=True)
    payload["openQuestions"] = [
        {
            "impact": 1,
            "question": f"단일 Event 분기 질문 {index}",
            "axis": axis,
            "lever": "weather_demand",
        }
        for index, axis in enumerate(["magnitude", "scope", "timing"], start=1)
    ]
    readable = V4ReadableEventAnalysisDraft.model_validate(payload)
    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": "동북아 한파 지속 전망"},
        open_question_limit=3,
    )
    analysis = finalize_v4_event_impact_analysis(draft, event_ids=[101], impact_levers=_catalog())
    state = V4MultiEventGenerationState(
        events=[EventPayload(mi_event_id=101, event_type_l2_id=8)],
        impact_levers=_catalog(),
        analysis_draft=analysis,
    )
    invoke = AsyncMock()
    with patch.object(v4_nodes, "invoke_stage_structured_output", invoke):
        interaction_update = asyncio.run(v4_nodes.AnalyzeEventInteractionsNode().run(state))

    invoke.assert_not_awaited()
    validated = v4_nodes.validate_v4_event_interactions(state.model_copy(update=interaction_update))
    finalized = validated["analysis_draft"]
    assert isinstance(finalized, V4EventImpactAnalysisResult)
    assert len(finalized.path_uncertainties) == 3
    assert finalized.interactions == []
    assert finalized.interaction_uncertainties == []
    assert finalized.validation_warnings == []


def test_v4_persistence_keeps_analysis_graph_in_diagnostics() -> None:
    finalized, coverage = _finalized()
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v4",
        generation_strategy="multi_event_model_lever_dimensions",
    )
    state = V4MultiEventGenerationState(
        scenario_group=group,
        events=[EventPayload(mi_event_id=101, event_type_l2_id=8), EventPayload(mi_event_id=202, event_type_l2_id=12)],
        impact_levers=_catalog(),
        impact_catalog_version="v1",
        impact_catalog_checksum="checksum-v1",
        user_id=7,
        analysis_as_of="2026-08-07",
        analysis_draft=finalized.impact_analysis,
        dimension_draft=V4DimensionDesignResult(
            dimension_definitions=finalized.dimension_definitions,
            excluded_dimensions=finalized.excluded_dimensions,
        ),
        finalized_result=finalized,
        parameter_coverage=coverage,
    )
    with patch.object(
        v4_nodes.ScenarioGroupService,
        "persist_multi_event_generation",
        return_value=(group, []),
    ) as persist:
        result = v4_nodes.persist_v4_generation(state)

    saved_dimensions = persist.call_args.kwargs["dimension_definitions"]
    saved_diagnostics = persist.call_args.kwargs["generation_diagnostics"]
    saved_scenarios = persist.call_args.kwargs["scenarios"]
    assert persist.call_args.kwargs["title"] == finalized.group_title
    assert persist.call_args.kwargs["summary"] == finalized.group_summary
    assert persist.call_args.kwargs["description"] == finalized.group_description
    assert "event_groundings" not in saved_dimensions[0]
    assert "lever_mappings" not in saved_dimensions[0]
    assert saved_dimensions[0]["source_impact_path_ids"] == ["path_101_demand"]
    assert saved_diagnostics["event_facts"][0]["fact_id"] == "fact_101_1"
    assert saved_diagnostics["analysis_as_of"] == "2026-08-07"
    assert saved_diagnostics["decision_basis"] == finalized.impact_analysis.decision_basis
    assert saved_diagnostics["impact_paths"][0]["lever_steps"][0]["impact_lever_id"] == 1
    assert saved_diagnostics["event_interactions"][0]["impact_path_ids"]
    assert saved_diagnostics["excluded_candidates"][0]["dimension_values"]
    assert saved_diagnostics["scenario_pressure_breakdowns"]
    assert [scenario["probability_score"] for scenario in saved_scenarios] == [35, 50, 15]
    assert result["generation_diagnostics"].impact_paths


def test_v4_prompts_follow_fact_path_uncertainty_contract() -> None:
    first = build_model_lever_user_prompt(
        events=[{"mi_event_id": 101, "event_title_ko": "동북아 한파"}],
        impact_levers=[lever.model_dump() for lever in _catalog()],
        catalog_version="v1",
        analysis_as_of="2026-08-07",
    )
    retry = build_model_lever_user_prompt(
        events=[{"mi_event_id": 101, "event_title_ko": "동북아 한파"}],
        impact_levers=[lever.model_dump() for lever in _catalog()],
        catalog_version="v1",
        analysis_as_of="2026-08-07",
        validation_feedback="leverStates List should have at most 3 items",
    )
    dimension = build_v4_dimension_design_user_prompt(
        impact_analysis=_analysis().model_dump(),
        validation_warnings=[],
        analysis_as_of="2026-08-07",
    )
    scenario = build_v4_scenario_synthesis_user_prompt(
        events=[
            {
                "mi_event_id": 101,
                "event_title_ko": "동북아 한파",
                "one_line_summary": "한파로 난방 수요가 증가했다.",
                "occurred_at": "2026-08-07T00:00:00Z",
                "key_facts": ["동북아 기온이 평년을 밑돌았다."],
                "tags": ["한파", "수요"],
            },
            {
                "mi_event_id": 202,
                "event_title_ko": "액화시설 정비",
                "one_line_summary": "액화시설 유지보수가 시작됐다.",
            },
        ],
        impact_analysis=_analysis().model_dump(),
        dimension_definitions=[item.model_dump() for item in _dimensions().dimension_definitions],
        validation_warnings=[],
        analysis_as_of="2026-08-07",
    )
    scenario_retry = build_v4_scenario_synthesis_user_prompt(
        events=[{"mi_event_id": 101, "event_title_ko": "동북아 한파"}],
        impact_analysis=_analysis().model_dump(),
        dimension_definitions=[item.model_dump() for item in _dimensions().dimension_definitions],
        validation_warnings=[],
        analysis_as_of="2026-08-07",
        validation_feedback="scenarios[1].dimensionValues duplicates scenarios[0].dimensionValues",
    )
    interaction = build_v4_interaction_analysis_user_prompt(
        impact_paths=[path.model_dump() for path in _analysis().impact_paths],
    )
    assert "## 핵심 사실 후보" in first
    assert "eventFacts에는 위 후보 문장을 글자까지 그대로 복사" in first
    assert "decisionBasis" in first
    assert "이번 Event openQuestions 목표·상한: 3개" in first
    assert "eventFacts는 Impact의 근거가 되는 후보를 최대 3개까지 모두 선택" in first
    assert "impacts[].evidence에는 선택한 eventFacts를 1~3개 포함하며" in first
    assert "impacts는 Primary Impact와 별도 경로 Fact 수만큼 작성하며 최대 3개" in first
    assert "1) 별도 경로 Fact: Primary Fact와 다른 대상(국가·지역·구매자·시설), 반대 방향, 구분되는 시점의 변화를" in first
    assert "2) 보강 Fact: Primary Fact와 같은 변화의 수치·관측일" in first
    assert "Lever·direction·scope·timing이 모두 같으면 서버가 같은 경로로 보고 거부합니다" in first
    assert "leverStates는 Impact마다 가급적 1~2개만 작성" in first
    assert "세 단계가 모두 중요한 전달 경로일 때만 최대 3개" in first
    assert "중요한 3개만 선택" in first
    assert "같은 Impact의 leverStates 안에서 `lever` code는 반드시 서로 달라야 합니다" in first
    assert "동일 Lever code를" in first
    assert "전달 경로를 가장 잘 대표하는 하나의 step으로" in first
    assert "서로 다른 Impact에서는 같은 Lever code를 다시 사용할 수 있습니다" in first
    assert "첫 번째 `lever` code를 비교해" in first
    assert "루트 summary" not in scenario
    assert "그룹 제목은 다음 단계에서" not in scenario
    assert "루트 title" not in scenario
    assert "첫 문장은 관측된 이벤트 사실을 직접 서술" in scenario
    assert "`반영한다`, `바탕으로 한다`, `정리한다`" in scenario
    assert "Dimension 이름을" in scenario
    assert "충격의 지속·전달·증폭과 대체·회복·상쇄" in scenario
    assert "독립 이벤트에는 임의의 상호작용을 만들지 않습니다" in scenario
    lever_states_schema = V4ReadableEventAnalysisDraft.model_json_schema(by_alias=True)["$defs"][
        "V4ReadableEventImpact"
    ]["properties"]["leverStates"]
    assert "첫 번째 lever code가 모두 달라야" in lever_states_schema["description"]
    assert "대표 step 하나로 통합" in lever_states_schema["description"]
    assert "demand, supply, trade domain Lever가 하나라도 있으면 balance에 none을 사용할 수 없습니다" in first
    assert "지배적인 domain을 정할 수 없으면 Impact를 나눕니다" in first
    assert "leverStates는 Impact마다 가급적 1~2개만 작성" in retry
    assert "세 단계가 모두 중요한 전달 경로일 때만 최대 3개" in retry
    assert "같은 Impact의 leverStates 안에서 `lever` code는 반드시 서로 달라야 합니다" in retry
    assert "leverStates List should have at most 3 items" in retry
    assert "eventFacts는 Impact의 근거가 되는 후보를 최대 3개까지 모두 선택" in retry
    assert "impacts[].evidence에는 선택한 eventFacts를 1~3개 포함하며" in retry
    assert "impacts는 Primary Impact와 별도 경로 Fact 수만큼 작성하며 최대 3개" in retry
    assert "잘못된 영향 경로·Lever·balance·열린 질문만 수정" in retry
    assert "48시간 사전 요청처럼 반복되는 운영 조건" in first
    assert "분석 기준일: 2026-08-07" in first
    assert "JKM의 상승·하락·혼조 방향" in first
    assert "별도의 price 필드는 만들지 않습니다" in first
    assert f"direction은 {StateDirection.prompt_values()}" in first
    assert "factStatus" not in first
    assert "selectionHint" not in first
    assert "parameterBindings" not in first
    assert "## 검증된 영향 경로" in interaction
    assert "[E101-P1]" in interaction
    assert "JKM의 순방향·영향 기간" in interaction
    assert "실제 Event openQuestions 수: 0개" in interaction
    assert "Interaction openQuestions 전체 상한: 1개" in interaction
    assert "## Dimension 후보가 되는 열린 질문" in dimension
    assert "실제 open question 수: 4개" in dimension
    assert "초기 Dimension 권장 범위: 3개" in dimension
    assert "unused question을 최소 1개" in dimension
    assert "## 숫자·시점 판단 근거" in dimension
    assert "분석 기준일 2026-08-07 현재 동북아 한파 전망" in dimension
    assert "## 그룹 설명의 근거가 되는 이벤트" in scenario
    assert "[이벤트 1]" in scenario
    assert "제목: 동북아 한파" in scenario
    assert "요약: 한파로 난방 수요가 증가했다." in scenario
    assert "동북아 기온이 평년을 밑돌았다." in scenario
    assert "태그: 한파, 수요" in scenario
    assert "[이벤트 2]" in scenario
    assert "제목: 액화시설 정비" in scenario
    assert scenario.index("[이벤트 1]") < scenario.index("[이벤트 2]")
    assert "영문 `Event`, `Scenario`와 `입력 사실`을 쓰지 않습니다" in scenario
    assert "`JKM`을 쓰지 않습니다" not in scenario
    assert "LNG·JKM·TTF·HH 등 시장·상품 약어와 시설·기업 고유명은" in scenario
    assert "원문 표기 그대로 쓰고 `엘엔지`, `제이케이엠`처럼 한글로 음역하지 않습니다" in scenario
    assert "[U1]" in dimension
    assert "label은 핵심 대상과 변화 축을 담되 30자를 넘지 않습니다" in dimension
    assert "원문 관측값·전망치는 Choice 경계로 그대로 사용합니다" in dimension
    assert "만든 차이·증가분·감소분·비율은" in dimension
    assert "label에 `폭`·`변화량`·`감소분`·`증가분`을 쓰려고 Choice 값을 계산해 바꾸지 말고" in dimension
    assert "Dimension label은 판단 대상(누가·무엇이)과 판단 축(규모·기간·시점·범위)을 함께 담습니다" in dimension
    assert "행위 주체나 대상과 그 상태 변화를 함께 씁니다" in dimension
    assert "두 상태를 `·`로 나열하지 않습니다" in dimension
    assert "rationale은 최대 200자의 구체적인 한국어 한 문장" in dimension
    assert "question은 필요한 관측 정보와 판단 대상을 충분히 포함" in dimension
    assert "`사실: … | 전망: … | 파생: … | 가정: … | 영향: …` 형식" in dimension
    assert "## 전망·계획 원문 (관측 사실 아님)" in dimension
    assert "Choice끼리 pressure가 겹치지 않게" in dimension
    assert "Impact의 현재 상태가\n  지속·강화되는 Choice는 그 Impact와 같은 방향" in dimension
    assert "같은 상태를 다르게 매기지 않습니다" in dimension
    assert "월 단위 시점" in dimension
    assert "Choice label은 비교 가능한 하나의 시장·운영 상태를 30자 이내" in dimension
    assert "새로운 수치 경계" in dimension
    assert f"direction은 {StateDirection.prompt_values()}" in dimension
    assert "`Event 배경으로 제시된 사실` 같은 메타 표현" in dimension
    assert "`답`, `응답`, `선택`" in dimension
    assert "| 가정: 11월 이전에 스프레드가 다시 벌어짐 |" in dimension
    assert "별도 Anchor 참조 ID, 새 사실을" in dimension
    assert "sourceImpactPathIds" not in dimension
    assert "## Dimension 질문과 선택지" in scenario
    assert "[D1.V1]" in scenario
    assert "미리 정한 유형에 맞추지 말고" in scenario
    assert "pressure 단계만 한 칸씩 바꾼" in scenario
    assert "title은 대체로 22~38자의 서술형 구절이며 40자를 넘지 않습니다" in scenario
    assert "핵심 주체(누가·무엇이)와 그 상태 변화를 함께 써서" in scenario
    assert "조사 없이 명사와 동작 명사를 이어 붙이거나" in scenario
    assert "narrative는 80~300자의 한국어 두 문장" in scenario
    assert "상반된 효과가 있으면 우세·상쇄" in scenario
    assert "내부 참조 ID를 노출하지 말고" in scenario
    assert "ID는 choices와 interactions 필드에서만 사용" in scenario
    assert "commonImpactPathIds" not in scenario
    assert "TTF와 HH는 각각 최대 한 번만 작성" in scenario
    assert "0~100 정수 백분율" in scenario
    assert "합계를 정확히 100" in scenario
    assert "검증 오류: scenarios[1].dimensionValues duplicates scenarios[0].dimensionValues" in scenario_retry
    assert "동일한 실수를 반복하지 마십시오" in scenario_retry


@pytest.mark.parametrize(
    ("event_question_count", "expected_limit"),
    [(8, 2), (10, 0), (12, 0)],
)
def test_v4_interaction_prompt_applies_the_remaining_question_capacity(
    event_question_count: int,
    expected_limit: int,
) -> None:
    prompt = build_v4_interaction_analysis_user_prompt(
        impact_paths=[path.model_dump() for path in _analysis().impact_paths],
        event_question_count=event_question_count,
        event_count=4,
    )

    assert f"실제 Event openQuestions 수: {event_question_count}개" in prompt
    assert f"Interaction openQuestions 전체 상한: {expected_limit}개" in prompt
    assert "의미 있는 Interaction 목표: 2~3개" in prompt
    assert "Interaction 상한: 3개" in prompt


def test_v4_interaction_question_overage_is_dropped_without_retry() -> None:
    axes = ["magnitude", "scope", "timing", "duration", "recovery", "mitigation", "substitution"]
    levers = ["weather_demand", "liquefaction_availability", "financial_market_sentiment"]
    payload = _readable_interaction_draft().model_dump(by_alias=True)
    payload["openQuestions"] = [
        {
            "interaction": 1,
            "question": f"Interaction 추가 분기 질문 {index}",
            "axis": axes[index % len(axes)],
            "lever": levers[index % len(levers)],
        }
        for index in range(8)
    ]
    state = V4MultiEventGenerationState(
        events=[
            EventPayload(mi_event_id=101, event_type_l2_id=8),
            EventPayload(mi_event_id=202, event_type_l2_id=12),
        ],
        impact_levers=_catalog(),
        analysis_draft=_analysis(),
        interaction_draft=V4ReadableInteractionAnalysisDraft.model_validate(payload),
        interaction_attempt=1,
    )

    update = v4_nodes.validate_v4_event_interactions(state)

    finalized = update["analysis_draft"]
    assert isinstance(finalized, V4EventImpactAnalysisResult)
    assert update["interaction_error"] is None
    assert update["interaction_retryable"] is False
    assert len(finalized.path_uncertainties) == 3
    assert len(finalized.interaction_uncertainties) == 1
    assert finalized.interaction_uncertainties[0].uncertainty_id == "iu1"
    assert any(warning.code == "INTERACTION_OPEN_QUESTION_LIMIT_APPLIED" for warning in finalized.validation_warnings)


@pytest.mark.parametrize("dimension_count", [5, 6])
def test_v4_dimension_contract_accepts_five_or_six_dimensions(dimension_count: int) -> None:
    readable = _readable_dimension_draft()
    dimensions = list(readable.dimensions)
    while len(dimensions) < dimension_count:
        clone = dimensions[0].model_copy(
            update={
                "label": f"추가 분기 축 {len(dimensions) + 1}",
                "question": f"추가 분기 질문 {len(dimensions) + 1}",
                "rationale": f"추가 분기 근거 {len(dimensions) + 1}",
            },
        )
        dimensions.append(clone)
    parsed = V4ReadableDimensionDesignDraft.model_validate(
        readable.model_copy(update={"dimensions": dimensions}).model_dump(by_alias=True),
    )
    expanded = expand_v4_readable_dimension_design(parsed, impact_analysis=_analysis())

    finalized = finalize_v4_dimension_design(
        expanded,
        impact_analysis=_analysis(),
        impact_levers=_catalog(),
    )

    assert len(finalized.dimension_definitions) == dimension_count


def test_v4_additional_dimension_prompt_recommends_unused_count_but_allows_empty_result() -> None:
    prompt = build_v4_additional_dimension_user_prompt(
        impact_analysis=_analysis().model_dump(),
        impact_levers=[lever.model_dump() for lever in _catalog()],
        selected_definitions=[],
    )

    assert "실제 unused question 수: 4개" in prompt
    assert "Additional Dimension 후보 권장 범위: 1~4개" in prompt
    assert "빈 dimensions도 정상 결과" in prompt
    assert "두 상태를 `·`로 나열하지 않습니다" in prompt
    assert V4ReadableAdditionalDimensionDesignDraft(dimensions=[]).dimensions == []


def test_llm_validation_error_detail_preserves_field_locations_for_retry() -> None:
    with pytest.raises(ValueError) as error:
        V4ReadableScenarioSynthesisDraft.model_validate(
            {
                "description": "테스트 설명",
                "scenarios": [{}],
            },
        )

    detail, error_code, retryable = v4_nodes.classify_llm_error(error.value)

    assert "field=scenarios.0.title" in detail
    assert "type=missing" in detail
    assert "input_value" not in detail
    assert error_code == "LLM_INVALID_RESPONSE_ERROR"
    assert retryable is True
    assert v4_nodes._retry_validation_feedback(detail, error_code) == detail
    assert v4_nodes._retry_validation_feedback(detail, "LLM_RESPONSE_TIMEOUT") is None


def test_v4_scenario_structured_output_rejects_llm_summary() -> None:
    payload = _readable_scenario_draft().model_dump(by_alias=True)
    payload["summary"] = "LLM이 생성하면 안 되는 summary"

    with pytest.raises(ValueError, match="Extra inputs are not permitted"):
        V4ReadableScenarioSynthesisDraft.model_validate(payload)


def test_v4_readable_copy_contract_matches_table_density() -> None:
    readable = _readable_dimension_draft()
    expanded = expand_v4_readable_dimension_design(readable, impact_analysis=_analysis())
    rationale_schema = V4ReadableDimensionDesignDraft.model_json_schema(by_alias=True)["$defs"]["V4ReadableDimension"][
        "properties"
    ]["rationale"]
    why_schema = V4ReadableDimensionDesignDraft.model_json_schema(by_alias=True)["$defs"]["V4ReadableDimensionChoice"][
        "properties"
    ]["why"]

    assert expanded.dimension_definitions[0].label == "동북아 한파와 추가 LNG 수요"
    assert expanded.dimension_definitions[0].description == "한파에 따른 추가 LNG 수요 규모는 얼마인가?"
    assert expanded.dimension_definitions[0].rationale == "동북아 한파와 추가 분기 기준"
    assert "관측 시점·수치·시장 신호·대상·영향 경로" in rationale_schema["description"]
    assert rationale_schema["maxLength"] == 200
    assert "minLength" not in rationale_schema
    assert "'사실: 관측 사실 | 전망: 원문의 주체·발표일을 붙인 전망·계획 | 파생:" in why_schema["description"]
    assert "전망 수치는 사실 칸에 쓰지 않음" in why_schema["description"]
    assert "영향: JKM 전달 경로와 방향" in why_schema["description"]
    assert "답·응답·선택으로 표현하지 않음" in why_schema["description"]
    assert all(len(choice.label) <= 30 for dimension in readable.dimensions for choice in dimension.choices)

    invalid_choice = readable.model_dump(by_alias=True)
    invalid_choice["dimensions"][0]["choices"][0]["label"] = "낮음"
    assert V4ReadableDimensionDesignDraft.model_validate(invalid_choice).dimensions[0].choices[0].label == "낮음"

    short_rationale = readable.model_dump(by_alias=True)
    short_rationale["dimensions"][0]["rationale"] = "너무 짧음"
    assert V4ReadableDimensionDesignDraft.model_validate(short_rationale).dimensions[0].rationale == "너무 짧음"

    long_rationale = readable.model_dump(by_alias=True)
    long_rationale["dimensions"][0]["rationale"] = "가" * 201
    with pytest.raises(ValueError, match="rationale"):
        V4ReadableDimensionDesignDraft.model_validate(long_rationale)

    synthesis = _readable_scenario_draft()
    assert all(20 <= len(scenario.title) <= 40 for scenario in synthesis.scenarios)
    assert all(80 <= len(scenario.narrative) <= 300 for scenario in synthesis.scenarios)

    invalid_scenario = synthesis.model_dump(by_alias=True)
    invalid_scenario["scenarios"][0]["title"] = "가" * 41
    with pytest.raises(ValueError, match="title"):
        V4ReadableScenarioSynthesisDraft.model_validate(invalid_scenario)


def test_v4_structured_output_schemas_are_openai_strict_compatible() -> None:
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

    schemas = {
        model.__name__: pydantic_function_tool(model)["function"]["parameters"]
        for model in (
            V4ReadableEventAnalysisDraft,
            V4ReadableInteractionAnalysisDraft,
            V4ReadableDimensionDesignDraft,
            V4ReadableScenarioSynthesisDraft,
        )
    }
    for name, parameters in schemas.items():
        inspect_schema(parameters, name)
    assert invalid_objects == []
    assert "price" not in schemas["V4ReadableEventAnalysisDraft"]["$defs"]["V4ReadableEventImpact"]["properties"]
    assert "price" not in schemas["V4ReadableInteractionAnalysisDraft"]["$defs"]["V4ReadableInteraction"]["properties"]
    assert "format" not in schemas["V4ReadableDimensionDesignDraft"]["$defs"]["V4ReadableDimension"]["properties"]
    assert "valueKind" in V4DimensionDefinition.model_json_schema(by_alias=True)["properties"]
    assert len(str(schemas["V4ReadableEventAnalysisDraft"])) < len(str(V4EventImpactAnalysisDraft.model_json_schema()))
    assert "dimensionValues" not in str(schemas["V4ReadableScenarioSynthesisDraft"])
    assert "summary" not in schemas["V4ReadableScenarioSynthesisDraft"]["properties"]


def test_v4_scenario_group_metadata_schema_describes_korean_event_wording() -> None:
    schema = V4ReadableScenarioSynthesisDraft.model_json_schema()
    properties = schema["properties"]

    assert "title" not in properties
    title_description = V4GroupTitleDraft.model_json_schema()["properties"]["title"]["description"]
    assert "모든 시나리오가 공유하는 전제와 시나리오를 가르는 핵심 질문" in title_description
    assert "특정 시나리오의 답이나 결말을 쓰지 않음" in title_description
    assert "summary" not in properties
    assert "영문 Event/Scenario" in properties["description"]["description"]
    assert "영문 Event/Scenario와 '입력 사실'은 사용하지 않음" in properties["description"]["description"]
    assert "원문 표기 그대로 쓰고 한글로 음역하지 않음" in properties["description"]["description"]
    assert "0~100 정수 백분율" in schema["$defs"]["V4ReadableScenario"]["properties"]["probability"]["description"]
    assert "합계는 100" in schema["$defs"]["V4ReadableScenario"]["properties"]["probability"]["description"]


def test_related_markets_excludes_primary_jkm_market() -> None:
    with pytest.raises(ValueError, match="TTF|HH"):
        RelatedMarket(market="JKM", rationale="JKM은 pressure breakdown에서 설명한다.")


def test_v4_scenario_discards_duplicate_related_markets_after_first() -> None:
    payload = _synthesis().model_dump(by_alias=True)
    payload["scenarios"][0]["relatedMarkets"] = [
        {"market": "TTF", "rationale": "첫 번째 TTF 근거를 유지한다."},
        {"market": "TTF", "rationale": "중복된 두 번째 TTF 근거는 버린다."},
    ]

    synthesis = V4ScenarioSynthesisResult.model_validate(payload)

    assert synthesis.scenarios[0].related_markets == [
        RelatedMarket(market="TTF", rationale="첫 번째 TTF 근거를 유지한다."),
    ]


# --- distinct_driver Scenario 합성 정책 ---------------------------------------------------------

# _dimensions()의 값별 pressureContribution 합산:
# cold_wave_intensity high=+1 low=-1, liquefaction_recovery delayed=+1 fast=-1, risk_premium high=+1 low=-1


def _policy_synthesis(
    scenarios: list[tuple[str, dict[str, str], float]],
    excluded: list[tuple[str, dict[str, str]]] | None = None,
) -> V4ScenarioSynthesisResult:
    return V4ScenarioSynthesisResult.model_validate(
        {
            "groupDescription": "공통 영향 경로와 잔여 불확실성을 결합한 JKM 시나리오",
            "scenarios": [
                {
                    "title": title,
                    "narrative": f"{title} 전개",
                    "dimensionValues": values,
                    "commonImpactPathIds": ["path_101_demand", "path_202_supply"],
                    "appliedInteractionIds": [],
                    # distinct_driver는 서버가 Base 대비로 band를 다시 계산하므로 LLM band는 결과에 쓰지 않는다.
                    "pressureBand": "balanced",
                    "pressureBreakdown": {
                        "commonImpact": "공통 영향",
                        "valueDelta": "선택값 효과",
                        "interactionEffect": "적용된 Event Interaction이 없다.",
                    },
                    "probabilityScore": probability,
                    "explanation": f"{title}의 JKM 압력 근거를 자연어로 설명한다.",
                }
                for title, values, probability in scenarios
            ],
            "excludedScenarios": [
                {
                    "pressureBand": "balanced",
                    "reasonCode": reason_code,
                    "reason": "검토 후 제외",
                    "dimensionValues": values,
                }
                for reason_code, values in (excluded or [])
            ],
        },
    )


def _combo(cold: str, liquefaction: str, risk: str) -> dict[str, str]:
    return {"cold_wave_intensity": cold, "liquefaction_recovery": liquefaction, "risk_premium": risk}


def _finalize_policy(
    synthesis: V4ScenarioSynthesisResult,
    *,
    count_range: tuple[int, int] = (3, 5),
) -> tuple[V4GenerationResult, object]:
    return finalize_v4_generation_result(
        synthesis,
        group_title="테스트 그룹",
        group_summary=_group_summary(),
        impact_analysis=_analysis(),
        dimension_design=_dimensions(),
        impact_levers=_catalog(),
        policy="distinct_driver",
        scenario_count_range=count_range,
    )


@pytest.mark.parametrize(
    ("event_count", "band_unique_range", "distinct_driver_range"),
    [(1, (3, 5), (3, 5)), (2, (3, 5), (3, 5)), (3, (3, 5), (4, 6)), (4, (3, 5), (5, 7)), (5, (3, 5), (6, 8))],
)
def test_scenario_count_range_by_policy_and_event_count(
    event_count: int,
    band_unique_range: tuple[int, int],
    distinct_driver_range: tuple[int, int],
) -> None:
    assert scenario_count_range(event_count, policy="band_unique") == band_unique_range
    assert scenario_count_range(event_count, policy="distinct_driver") == distinct_driver_range


def test_distinct_driver_allows_shared_bands_and_rebases_bands_on_the_baseline() -> None:
    synthesis = _policy_synthesis(
        [
            ("기준", _combo("high", "fast", "low"), 40),  # -1, Base
            ("수요 주도 상방", _combo("high", "delayed", "low"), 25),  # +1 → delta +2
            ("공급 주도 상방", _combo("low", "delayed", "high"), 20),  # +1 → delta +2
            ("전면 완화", _combo("low", "fast", "low"), 15),  # -3 → delta -2
        ],
        excluded=[("INSUFFICIENT_EVIDENCE", _combo("low", "delayed", "low"))],  # -1 → delta 0
    )

    finalized, _coverage = _finalize_policy(synthesis)

    by_title = {scenario.title: scenario for scenario in finalized.scenarios}
    assert by_title["기준"].baseline_yn is True
    assert by_title["기준"].pressure_band == "balanced"
    assert by_title["수요 주도 상방"].pressure_band == "strong_bullish"
    assert by_title["공급 주도 상방"].pressure_band == "strong_bullish"
    assert by_title["전면 완화"].pressure_band == "strong_bearish"
    assert by_title["전면 완화"].scenario_role == "floor"
    assert by_title["수요 주도 상방"].scenario_role == "ceiling"
    assert [scenario.title for scenario in finalized.scenarios][-1] == "전면 완화"
    assert finalized.excluded_scenarios[0].pressure_band == "balanced"
    assert finalized.scenario_synthesis_policy == "distinct_driver"
    assert finalized.scenario_count_range is not None
    assert (finalized.scenario_count_range.target_min, finalized.scenario_count_range.max) == (3, 5)
    assert finalized.scenario_count_shortfall is None
    assert finalized.direction_coverage_gaps == []


def test_distinct_driver_retries_when_a_reachable_direction_is_missing() -> None:
    synthesis = _policy_synthesis(
        [
            ("기준", _combo("high", "fast", "low"), 50),  # -1, Base
            ("전면 완화", _combo("low", "fast", "low"), 30),  # -3
            ("공급 회복 지연 상쇄", _combo("low", "delayed", "low"), 20),  # -1
        ],
    )

    with pytest.raises(ValueError, match="상방 Scenario가 없습니다"):
        _finalize_policy(synthesis)


def test_distinct_driver_records_an_unreachable_direction_as_a_gap() -> None:
    synthesis = _policy_synthesis(
        [
            ("전면 경색", _combo("high", "delayed", "high"), 50),  # +3, 가능한 최대 합산인 Base
            ("수요만 강세", _combo("high", "fast", "low"), 30),  # -1
            ("전면 완화", _combo("low", "fast", "low"), 20),  # -3
        ],
    )

    finalized, _coverage = _finalize_policy(synthesis)

    assert finalized.direction_coverage_gaps == ["bullish"]
    assert [scenario.pressure_band for scenario in finalized.scenarios] == [
        "balanced",
        "strong_bearish",
        "strong_bearish",
    ]


def test_distinct_driver_trims_scenarios_over_the_maximum_and_keeps_both_directions() -> None:
    synthesis = _policy_synthesis(
        [
            ("기준", _combo("high", "fast", "low"), 30),  # -1, Base
            ("수요 주도 상방", _combo("high", "delayed", "low"), 15),  # delta +2
            ("전면 경색", _combo("high", "delayed", "high"), 15),  # delta +4
            ("공급 주도 상방", _combo("low", "delayed", "high"), 14),  # delta +2
            ("수요 약세 상쇄", _combo("low", "delayed", "low"), 13),  # delta 0
            ("전면 완화", _combo("low", "fast", "low"), 13),  # delta -2
        ],
    )

    finalized, _coverage = _finalize_policy(synthesis, count_range=(3, 4))

    titles = [scenario.title for scenario in finalized.scenarios]
    assert len(titles) == 4
    assert "전면 완화" in titles
    assert {"수요 약세 상쇄", "공급 주도 상방"}.isdisjoint(titles)
    assert [candidate.reason_code for candidate in finalized.excluded_scenarios] == [
        "EXCEEDS_MAX_COUNT",
        "EXCEEDS_MAX_COUNT",
    ]
    assert sum(scenario.probability_score for scenario in finalized.scenarios) == 100


def test_distinct_driver_rejects_legacy_exclusion_reason_codes() -> None:
    synthesis = _policy_synthesis(
        [
            ("기준", _combo("high", "fast", "low"), 40),
            ("수요 주도 상방", _combo("high", "delayed", "low"), 35),
            ("전면 완화", _combo("low", "fast", "low"), 25),
        ],
        excluded=[("NOT_INDEPENDENT", _combo("low", "delayed", "low"))],
    )

    with pytest.raises(ValueError, match="reasonCode must be one of"):
        _finalize_policy(synthesis)


def test_distinct_driver_records_shortfall_below_the_target_minimum() -> None:
    synthesis = _policy_synthesis(
        [
            ("기준", _combo("high", "fast", "low"), 40),
            ("수요 주도 상방", _combo("high", "delayed", "low"), 35),
            ("전면 완화", _combo("low", "fast", "low"), 25),
        ],
        excluded=[
            ("INSUFFICIENT_EVIDENCE", _combo("low", "delayed", "low")),
            ("DUPLICATE", _combo("low", "delayed", "high")),
        ],
    )

    finalized, _coverage = _finalize_policy(synthesis, count_range=(5, 7))

    assert finalized.scenario_count_shortfall is not None
    assert finalized.scenario_count_shortfall.target_min == 5
    assert finalized.scenario_count_shortfall.actual == 3
    assert finalized.scenario_count_shortfall.excluded_reason_counts == {"DUPLICATE": 1, "INSUFFICIENT_EVIDENCE": 1}


def test_band_unique_finalizer_records_policy_and_similarity_without_changing_results() -> None:
    finalized, _coverage = _finalized()

    assert finalized.scenario_synthesis_policy == "band_unique"
    assert finalized.scenario_count_range is not None
    assert (finalized.scenario_count_range.target_min, finalized.scenario_count_range.max) == (3, 5)
    assert finalized.scenario_count_shortfall is None


def test_similar_scenario_pairs_detect_one_dimension_and_title_similarity() -> None:
    pairs = find_similar_scenario_pairs(
        [
            ScenarioSimilarityInput("미국 공급 회복 우세", "bearish", {"d1": "a", "d2": "x"}),
            ScenarioSimilarityInput("유럽 수요 둔화", "bearish", {"d1": "b", "d2": "x"}),
            ScenarioSimilarityInput("미국 공급 회복 우세 지속", "bullish", {"d1": "c", "d2": "y"}),
        ],
    )

    kinds_by_titles = {tuple(pair["scenario_titles"]): pair["kinds"] for pair in pairs}
    assert kinds_by_titles == {
        ("미국 공급 회복 우세", "유럽 수요 둔화"): ["same_band_one_dimension"],
        ("미국 공급 회복 우세", "미국 공급 회복 우세 지속"): ["similar_title"],
    }


def test_v4_synthesis_prompt_keeps_band_unique_rules_and_switches_for_distinct_driver() -> None:
    common = {
        "analysis_as_of": "2026-10-16",
        "events": [{"mi_event_id": 1}, {"mi_event_id": 2}, {"mi_event_id": 3}],
        "impact_analysis": {},
        "dimension_definitions": [],
        "validation_warnings": [],
    }

    band_unique = build_v4_scenario_synthesis_user_prompt(**common)
    distinct_driver = build_v4_scenario_synthesis_user_prompt(
        **common,
        policy="distinct_driver",
        scenario_count_range=(4, 6),
    )

    assert "다섯 pressure band를 한 번씩" in band_unique
    assert "NOT_INDEPENDENT" in band_unique
    assert "다섯 pressure band를 한 번씩" not in distinct_driver
    assert "선택한 이벤트 3개를 기준으로 Scenario 4~6개" in distinct_driver
    assert "Base 대비 상대" in distinct_driver
    for reason_code in ("INSUFFICIENT_EVIDENCE", "CONTRADICTION", "DUPLICATE", "LOW_PROBABILITY"):
        assert reason_code in distinct_driver
    assert "NOT_INDEPENDENT" not in distinct_driver


def _policy_state(**overrides: object) -> V4MultiEventGenerationState:
    return V4MultiEventGenerationState.model_validate(
        {
            "events": [
                EventPayload(mi_event_id=101, event_type_l2_id=8, event_title_ko="동북아 한파"),
                EventPayload(mi_event_id=202, event_type_l2_id=12, event_title_ko="미국 액화 차질"),
            ],
            "impact_levers": _catalog(),
            "analysis_draft": _analysis(),
            "dimension_draft": _dimensions(),
            "scenario_synthesis_policy": "distinct_driver",
            "scenario_count_range": (5, 7),
            "scenario_attempt": 1,
            **overrides,
        },
    )


def _three_scenario_synthesis() -> V4ScenarioSynthesisResult:
    return _policy_synthesis(
        [
            ("기준", _combo("high", "fast", "low"), 40),
            ("수요 주도 상방", _combo("high", "delayed", "low"), 35),
            ("전면 완화", _combo("low", "fast", "low"), 25),
        ],
    )


def test_v4_shortfall_retries_synthesis_once_and_keeps_the_first_result() -> None:
    update = v4_nodes.finalize_v4_scenarios(_policy_state(scenario_draft=_three_scenario_synthesis()))

    assert update["finalized_result"] is None
    assert update["scenario_retryable"] is True
    assert update["scenario_error_code"] == ErrorCode.LLM_INVALID_RESPONSE_ERROR.name
    assert "목표 최소 5개" in update["scenario_error"]
    assert update["scenario_shortfall_retried"] is True
    assert len(update["scenario_shortfall_fallback"].scenarios) == 3


def test_v4_shortfall_is_accepted_after_the_single_retry() -> None:
    first = v4_nodes.finalize_v4_scenarios(_policy_state(scenario_draft=_three_scenario_synthesis()))
    state = _policy_state(
        scenario_draft=_three_scenario_synthesis(),
        scenario_attempt=2,
        **{key: first[key] for key in ("scenario_shortfall_retried", "scenario_shortfall_fallback")},
        scenario_shortfall_fallback_coverage=first["scenario_shortfall_fallback_coverage"],
    )

    update = v4_nodes.finalize_v4_scenarios(state)

    assert update["scenario_error"] is None
    assert update["finalized_result"].scenario_count_shortfall.actual == 3


def test_v4_shortfall_fallback_is_used_when_the_retry_cannot_continue() -> None:
    first = v4_nodes.finalize_v4_scenarios(_policy_state(scenario_draft=_three_scenario_synthesis()))
    state = _policy_state(
        scenario_draft=None,
        scenario_attempt=3,
        scenario_error="LLM 호출 실패",
        scenario_retryable=True,
        scenario_shortfall_retried=True,
        scenario_shortfall_fallback=first["scenario_shortfall_fallback"],
        scenario_shortfall_fallback_coverage=first["scenario_shortfall_fallback_coverage"],
    )

    update = v4_nodes.finalize_v4_scenarios(state)

    assert update["scenario_error"] is None
    assert update["finalized_result"] is first["scenario_shortfall_fallback"]
    assert v4_nodes.route_after_v4_scenarios(state.model_copy(update=update)) == "generate_v4_group_title"



@pytest.mark.parametrize(
    ("node", "state_overrides", "error_key", "label"),
    [
        (v4_nodes.AnalyzeEventInteractionsNode(), {}, "interaction_error", "Event interaction analysis"),
        (v4_nodes.DesignModelLeverDimensionsNode(), {}, "dimension_error", "Dimension design"),
        (
            v4_nodes.SynthesizeV4ScenariosNode(),
            {"dimension_draft": _dimensions()},
            "scenario_error",
            "Scenario synthesis",
        ),
    ],
)
def test_v4_stage_timeout_cuts_a_stuck_call_and_marks_it_retryable(
    node: object,
    state_overrides: dict[str, object],
    error_key: str,
    label: str,
) -> None:
    async def never_returns(**_kwargs: object) -> object:
        await asyncio.sleep(1)
        raise AssertionError("timed-out call must not complete")

    analysis = _analysis()
    state = V4MultiEventGenerationState.model_validate(
        {
            "events": [
                EventPayload(mi_event_id=101, event_type_l2_id=8),
                EventPayload(mi_event_id=202, event_type_l2_id=12),
            ],
            "impact_levers": _catalog(),
            "analysis_draft": analysis,
            **state_overrides,
        },
    )
    with (
        patch.object(v4_nodes, "invoke_stage_structured_output", side_effect=never_returns),
        patch.object(v4_nodes, "_backoff", new=AsyncMock()),
        patch.object(v4_nodes, "_stage_timeout_seconds", return_value=0.001),
    ):
        update = asyncio.run(node.run(state))

    assert update[error_key] == f"{label} exceeded 0.001s"
    assert update[error_key.replace("_error", "_retryable")] is True


def test_v4_stage_timeouts_are_read_from_settings() -> None:
    settings = SimpleNamespace(
        llm_v4_event_analysis_timeout_sec=1.0,
        llm_v4_interaction_timeout_sec=2.0,
        llm_v4_dimension_timeout_sec=3.0,
        llm_v4_scenario_timeout_sec=4.0,
    )
    with patch.object(v4_nodes, "get_settings", return_value=settings):
        timeouts = [
            v4_nodes._stage_timeout_seconds(stage)
            for stage in ("event_analysis", "interaction", "dimension", "scenario")
        ]

    assert timeouts == [1.0, 2.0, 3.0, 4.0]



def test_v4_stage_without_timeout_waits_for_a_slow_call() -> None:
    async def slow(**_kwargs: object) -> str:
        await asyncio.sleep(0.05)
        return "done"

    with patch.object(v4_nodes, "_stage_timeout_seconds", return_value=None):
        result = asyncio.run(v4_nodes._with_stage_timeout(slow(), stage="scenario", label="Scenario synthesis"))

    assert result == "done"


def test_v4_stream_stall_limits_are_disabled_unless_configured() -> None:
    disabled = SimpleNamespace(llm_v4_stream_first_chunk_timeout_sec=None, llm_v4_stream_idle_timeout_sec=None)
    enabled = SimpleNamespace(llm_v4_stream_first_chunk_timeout_sec=150.0, llm_v4_stream_idle_timeout_sec=30.0)

    with patch.object(v4_nodes, "get_settings", return_value=disabled):
        assert v4_nodes._stream_stall_limits() is None
    with patch.object(v4_nodes, "get_settings", return_value=enabled):
        limits = v4_nodes._stream_stall_limits()

    assert (limits.first_chunk_sec, limits.idle_sec) == (150.0, 30.0)



def test_assign_relative_pressure_bands_demotes_extra_strong_bands_only_when_unique() -> None:
    deltas = [0, 2, 3, -2, -2, 1]

    assert assign_relative_pressure_bands(deltas, unique_strong=False) == [
        "balanced",
        "strong_bullish",
        "strong_bullish",
        "strong_bearish",
        "strong_bearish",
        "bullish",
    ]
    assert assign_relative_pressure_bands(deltas, unique_strong=True) == [
        "balanced",
        "bullish",
        "strong_bullish",
        "strong_bearish",
        "bearish",
        "bullish",
    ]


@pytest.mark.parametrize(
    ("diagnostics", "expected"),
    [
        (None, True),
        ({}, True),
        ({"scenario_synthesis_policy": "band_unique"}, True),
        ({"scenarioSynthesisPolicy": "distinct_driver"}, False),
    ],
)
def test_uses_unique_strong_bands_treats_unrecorded_groups_as_band_unique(
    diagnostics: dict[str, object] | None,
    expected: bool,
) -> None:
    assert uses_unique_strong_bands(diagnostics) is expected


# --- Event 사실과 전망 구분 ---

_FORECAST_CONSUMPTION = (
    "같은 전망에서 미국 국내 천연가스 소비는 2025년 91.9 bcfd에서 2026년 92.4 bcfd, 2027년 93.8 bcfd로 늘어 "
    "사상 최고치를 기록할 것으로 예상됐다."
)


def _forecast_event_payload() -> dict[str, object]:
    return {
        "mi_event_id": 32,
        "one_line_summary": "[미국 가스 공급] 생산·소비 전망 상향",
        "key_bullets": [
            (
                "9월 30일 기준 LSEG는 9월 미국 평균 생산이 112.2 bcfd였지만 "
                "최근 1주 평균은 약 109.4 bcfd로 낮아졌다고 제시했다."
            ),
            _FORECAST_CONSUMPTION,
        ],
    }


def _analysis_with_forecast() -> V4EventImpactAnalysisResult:
    return _analysis().model_copy(
        update={
            "forecast_claims": [
                V4ForecastClaim(
                    event_id=101,
                    topic="미국 가스 공급",
                    claim_kind="forecast",
                    text=_FORECAST_CONSUMPTION,
                    anchors=["93.8"],
                ),
            ],
        },
    )


def test_v4_forecast_claims_cover_unselected_source_sentences() -> None:
    claims = build_v4_forecast_claims(_forecast_event_payload(), analysis_as_of="2026-10-14")

    assert claims == [
        {
            "event_id": 32,
            "topic": "미국 가스 공급",
            "claim_kind": "forecast",
            "text": _FORECAST_CONSUMPTION,
            "anchors": ["92.4", "93.8"],
        },
    ]


def test_v4_event_analysis_prompt_tags_forecast_candidates() -> None:
    prompt = build_v4_event_impact_analysis_user_prompt(
        events=[_forecast_event_payload()],
        impact_levers=[],
        catalog_version="v4.1",
        analysis_as_of="2026-10-14",
    )

    assert f"2. [전망] {_FORECAST_CONSUMPTION}" in prompt
    assert "`[전망]`·`[계획]` 표시는 서버가 붙인 분류이므로 복사하지 않고" in prompt


def test_v4_event_analysis_accepts_tagged_copy_and_classifies_fact() -> None:
    readable = _readable_event_draft(101)
    readable.event_facts = ["[전망] 동북아 한파 지속 전망"]
    readable.impacts[0].evidence = ["[전망] 동북아 한파 지속 전망"]
    claim = V4ForecastClaim(event_id=101, claim_kind="forecast", text="동북아 한파 지속 전망", anchors=[])

    draft = expand_v4_readable_event_analysis(
        readable,
        event_id=101,
        observed_at="2026-08-05",
        fact_candidates={"f1": "동북아 한파 지속 전망"},
        forecast_claims=[claim],
    )

    assert draft.event_facts[0].observed_basis == "동북아 한파 지속 전망"
    assert draft.event_facts[0].claim_kind == "forecast"
    assert draft.forecast_claims == [claim]


def test_v4_legacy_event_fact_without_claim_kind_reads_as_observed() -> None:
    assert all(fact.claim_kind == "observed" for fact in _analysis().event_facts)


def test_v4_dimension_rejects_forecast_value_stated_as_fact() -> None:
    draft = _dimension_draft()
    value = draft.dimension_definitions[0].values[1]
    value.assumption_rationale = (
        "사실: 미국 국내 소비가 2027년 93.8 bcfd로 증가함 | 가정: 추가 수요가 국내에서 흡수됨 | 영향: JKM 상승 압력"
    )

    with pytest.raises(ValueError, match=r"사실 칸에 전망값 93\.8"):
        finalize_v4_dimension_design(draft, impact_analysis=_analysis_with_forecast(), impact_levers=_catalog())

    result = finalize_v4_dimension_design(
        draft,
        impact_analysis=_analysis_with_forecast(),
        impact_levers=_catalog(),
        enforce_forecast_separation=False,
    )
    assert [warning.code for warning in result.validation_warnings] == ["FORECAST_STATED_AS_FACT"]


def test_v4_dimension_accepts_forecast_value_in_forecast_field() -> None:
    draft = _dimension_draft()
    draft.dimension_definitions[0].values[1].assumption_rationale = (
        "사실: 9월 실적은 확인됨 | 전망: 10월 6일 단기 에너지 전망은 2027년 소비를 93.8 bcfd로 제시 | "
        "가정: 추가 수요가 국내에서 흡수됨 | 영향: JKM 상승 압력"
    )

    result = finalize_v4_dimension_design(
        draft,
        impact_analysis=_analysis_with_forecast(),
        impact_levers=_catalog(),
    )

    assert "FORECAST_STATED_AS_FACT" not in [warning.code for warning in result.validation_warnings]


def test_v4_dimension_date_does_not_trigger_other_events_forecast_quantity() -> None:
    analysis = _analysis_with_forecast()
    analysis.forecast_claims[0].anchors = ["11"]
    analysis.forecast_claims[0].text = "독일 태양광 발전량이 11GW로 감소할 전망이다."
    draft = _dimension_draft()
    value = draft.dimension_definitions[0].values[1]
    value.assumption_rationale = (
        "사실: 2026-11-10 현재 LNG 화물 지연은 직접 확인되지 않음 | 가정: 한파 지속 | 영향: JKM 상승 압력"
    )
    result = finalize_v4_dimension_design(draft, impact_analysis=analysis, impact_levers=_catalog())
    assert "FORECAST_STATED_AS_FACT" not in [warning.code for warning in result.validation_warnings]
    value.assumption_rationale = (
        "사실: 2026-11-10 태양광 발전량은 11GW임 | 가정: 한파 지속 | 영향: JKM 상승 압력"
    )
    with pytest.raises(ValueError, match="사실 칸에 전망값 11"):
        finalize_v4_dimension_design(draft, impact_analysis=analysis, impact_levers=_catalog())


def test_v4_finalizer_warns_when_scenario_states_forecast_value_as_fact() -> None:
    synthesis = _synthesis()
    synthesis.scenarios[0].explanation = "미국 국내 소비가 2027년 93.8 bcfd로 늘어 원료가스 여력이 줄어든다."

    finalized, _coverage = finalize_v4_generation_result(
        synthesis,
        group_title="테스트 그룹",
        group_summary=_group_summary(),
        impact_analysis=_analysis_with_forecast(),
        dimension_design=_dimensions(),
        impact_levers=_catalog(),
    )

    warnings = [warning for warning in finalized.validation_warnings if warning.code == "FORECAST_STATED_AS_FACT"]
    assert len(warnings) == 1
    assert warnings[0].stage == "scenario_synthesis"


def test_v4_prompts_mark_forecast_based_paths_and_list_forecast_claims() -> None:
    analysis = _analysis_with_forecast().model_dump()
    analysis["event_facts"][0]["claim_kind"] = "forecast"
    analysis["decision_basis"].append("소비 전망치 93.8 bcfd를 감안하면 수출 여력은 제한된다.")

    dimension = build_v4_dimension_design_user_prompt(
        impact_analysis=analysis,
        validation_warnings=[],
        analysis_as_of="2026-10-14",
    )
    scenario = build_v4_scenario_synthesis_user_prompt(
        analysis_as_of="2026-10-14",
        events=[],
        impact_analysis=analysis,
        dimension_definitions=[definition.model_dump() for definition in _dimensions().dimension_definitions],
        validation_warnings=[],
    )

    assert f"- [전망] (미국 가스 공급) {_FORECAST_CONSUMPTION}" in dimension
    assert "Event 101:" not in dimension
    assert "- [전망 포함] 소비 전망치 93.8 bcfd" in dimension
    assert "[전망 기반] " in dimension
    assert "[전망 기반] " in scenario
    assert "`[전망 기반]` 공통 영향은 주체가 밝힌 전망·계획을 전제로 한 경로입니다." in scenario


@pytest.mark.parametrize(
    "why",
    [
        "전망: 주체·발표일이 제시되지 않은 Event 30은 2032년 수요를 284 TWh로 제시 | 가정: 감소 | 영향: JKM 하락",
        "전망: 발표일이 제시되지 않은 스페인 수요 전망은 284 TWh를 제시 | 가정: 감소 | 영향: JKM 하락",
    ],
)
def test_v4_dimension_rejects_source_meta_phrase_and_event_id(why: str) -> None:
    draft = _dimension_draft()
    draft.dimension_definitions[0].values[1].assumption_rationale = why

    with pytest.raises(ValueError, match="출처 부재 설명이나 Event ID"):
        finalize_v4_dimension_design(draft, impact_analysis=_analysis(), impact_levers=_catalog())

    result = finalize_v4_dimension_design(
        draft,
        impact_analysis=_analysis(),
        impact_levers=_catalog(),
        enforce_forecast_separation=False,
    )
    assert [warning.code for warning in result.validation_warnings] == ["WHY_SOURCE_META_PHRASE"]


def test_v4_dimension_accepts_forecast_without_attribution_meta() -> None:
    draft = _dimension_draft()
    draft.dimension_definitions[0].values[1].assumption_rationale = (
        "전망: 스페인 2032년 가스 수요 전망은 284 TWh를 제시 | 가정: 수요가 284 TWh 이하 | 영향: JKM 하락 압력"
    )

    result = finalize_v4_dimension_design(draft, impact_analysis=_analysis(), impact_levers=_catalog())

    assert result.validation_warnings == []


def test_v4_dimension_prompt_forbids_absence_only_fact_and_source_meta() -> None:
    dimension = build_v4_dimension_design_user_prompt(
        impact_analysis=_analysis().model_dump(),
        validation_warnings=[],
        analysis_as_of="2026-10-14",
    )

    assert "근거가 없다는 문장만으로 사실 칸을 채우지 않습니다" in dimension
    assert "`주체·발표일이 제시되지 않은`처럼 출처가 없다는 설명이나" in dimension

