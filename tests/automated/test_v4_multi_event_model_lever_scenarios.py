from __future__ import annotations

import asyncio
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
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_enums import (
    StateDirection,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDefinition,
    V4DimensionDesignDraft,
    V4DimensionDesignResult,
    V4EventImpactAnalysisDraft,
    V4EventImpactAnalysisResult,
    V4GenerationResult,
    V4LeverStateDraft,
    V4ReadableAdditionalDimensionDesignDraft,
    V4ReadableDimensionDesignDraft,
    V4ReadableEventAnalysisDraft,
    V4ReadableInteractionAnalysisDraft,
    V4ReadableScenarioSynthesisDraft,
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
    build_v4_interaction_analysis_user_prompt,
    build_v4_scenario_synthesis_user_prompt,
    event_open_question_budgets,
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
            "groupTitle": "JKM 복수 Event 시나리오",
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
    for scenario in synthesis.scenarios:
        scenario.probability_score = 0

    finalized, _coverage = finalize_v4_generation_result(
        synthesis,
        group_summary=_group_summary(),
        impact_analysis=_analysis(),
        dimension_design=_dimensions(),
        impact_levers=_catalog(),
    )

    assert [scenario.probability_score for scenario in finalized.scenarios] == [34, 33, 33]
    assert sum(scenario.probability_score for scenario in finalized.scenarios) == 100
    assert [scenario.baseline_yn for scenario in finalized.scenarios] == [True, False, False]


def test_v4_scenario_rejects_missing_common_path() -> None:
    synthesis = _synthesis()
    synthesis.scenarios[0].common_impact_path_ids = ["path_101_demand"]
    with pytest.raises(ValueError, match="all common Impact Paths"):
        finalize_v4_generation_result(
            synthesis,
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
                    "leverStates": ["weather_demand|primary|increase|동북아|단기"],
                    "balance": "demand|increase",
                    "importance": "high" if index == 1 else "medium",
                }
                for index, fact in enumerate(facts, start=1)
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
        fact_candidates={f"f{index}": fact for index, fact in enumerate(reversed(facts), start=1)},
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
        fact_candidates={"f1": announced, "f2": forecast},
    )

    assert [fact.fact_id for fact in result.event_facts] == ["e101_f1", "e101_f2"]
    assert [fact.observed_basis for fact in result.event_facts] == [forecast, announced]
    assert result.impact_paths[0].source_fact_ids == ["e101_f1", "e101_f2"]


def test_v4_fact_candidates_do_not_truncate_the_source_sentence() -> None:
    fact = "장기 전망 " + ("상승 가능성을 검토했으며 " * 20) + "아직 확정하지 않았다고 발표했다."

    candidates = build_v4_event_fact_candidates({"mi_event_id": 101, "key_bullets": [fact]})

    assert candidates == {"f1": fact}


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
            "title": "동북아 한파와 미국 Gulf 액화시설 중단",
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
    assert calls[-3:] == [
        "V4ReadableInteractionAnalysisDraft",
        "V4ReadableDimensionDesignDraft",
        "V4ReadableScenarioSynthesisDraft",
    ]
    assert attempts_by_event == {101: 2, 202: 1}
    assert final_state["analysis_attempt"] == 2
    assert final_state["interaction_attempt"] == 1
    assert final_state["dimension_attempt"] == 1
    assert final_state["scenario_attempt"] == 1
    persist.assert_called_once()
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
        patch.object(v4_flow_module.EventService, "load_events", return_value=events),
        patch.object(
            v4_flow_module.ModelImpactLeverService,
            "load_active_catalog",
            return_value=(_catalog(), "v1", "checksum-v1"),
        ),
        patch.object(
            v4_flow_module.ScenarioGroupService,
            "prepare_v4_multi_event_group",
            return_value=group,
        ),
    ):
        prepared = v4_flow_module.prepare_v4_multi_event_scenarios(payload)

    assert prepared["analysis_as_of"] == "2026-08-07"
    assert [event.mi_event_id for event in prepared["events"]] == [202, 101]


def test_v4_event_timeout_is_retried_without_blocking_the_batch() -> None:
    async def never_returns(**_kwargs: object) -> object:
        await asyncio.sleep(1)
        return _readable_event_draft(101)

    with (
        patch.object(v4_nodes, "invoke_stage_structured_output", side_effect=never_returns),
        patch.object(v4_nodes, "_backoff", new=AsyncMock()),
        patch.object(v4_nodes, "V4_EVENT_LLM_TIMEOUT_SECONDS", 0.001),
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
    )
    scenario_retry = build_v4_scenario_synthesis_user_prompt(
        events=[{"mi_event_id": 101, "event_title_ko": "동북아 한파"}],
        impact_analysis=_analysis().model_dump(),
        dimension_definitions=[item.model_dump() for item in _dimensions().dimension_definitions],
        validation_warnings=[],
        validation_feedback="scenarios[1].dimensionValues duplicates scenarios[0].dimensionValues",
    )
    interaction = build_v4_interaction_analysis_user_prompt(
        impact_paths=[path.model_dump() for path in _analysis().impact_paths],
    )
    assert "## 핵심 사실 후보" in first
    assert "eventFacts에는 위 후보 문장을 글자까지 그대로 복사" in first
    assert "decisionBasis" in first
    assert "이번 Event openQuestions 목표·상한: 3개" in first
    assert "eventFacts는 가급적 1~2개만 선택" in first
    assert "impacts[].evidence에는 선택한 eventFacts를 1~3개 포함하되 가급적 1~2개만 사용" in first
    assert "impacts는 가급적 1~2개만 작성" in first
    assert "별도 주요 Lever, 반대 방향, 구분되는 기간 또는 독립 원인" in first
    assert "leverStates는 Impact마다 가급적 1~2개만 작성" in first
    assert "세 단계가 모두 중요한 전달 경로일 때만 최대 3개" in first
    assert "중요한 3개만 선택" in first
    assert "같은 Impact의 leverStates 안에서 `lever` code는 반드시 서로 달라야 합니다" in first
    assert "동일 Lever code를" in first
    assert "전달 경로를 가장 잘 대표하는 하나의 step으로" in first
    assert "서로 다른 Impact에서는 같은 Lever code를 다시 사용할 수 있습니다" in first
    assert "첫 번째 `lever` code를 비교해" in first
    assert "루트 summary" not in scenario
    assert "`선택 MI Event`, `모델 영향 레버`, `복수 이벤트 시나리오`" in scenario
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
    assert "eventFacts는 가급적 1~2개만 선택" in retry
    assert "impacts[].evidence에는 선택한 eventFacts를 1~3개 포함하되 가급적 1~2개만 사용" in retry
    assert "impacts는 가급적 1~2개만 작성" in retry
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
    assert "## 그룹 제목·설명의 근거가 되는 이벤트" in scenario
    assert "[이벤트 1]" in scenario
    assert "제목: 동북아 한파" in scenario
    assert "요약: 한파로 난방 수요가 증가했다." in scenario
    assert "동북아 기온이 평년을 밑돌았다." in scenario
    assert "태그: 한파, 수요" in scenario
    assert "[이벤트 2]" in scenario
    assert "제목: 액화시설 정비" in scenario
    assert scenario.index("[이벤트 1]") < scenario.index("[이벤트 2]")
    assert "루트 title은 20~60자의 한국어" in scenario
    assert "영문 `Event`, `Scenario`를 쓰지 않습니다" in scenario
    assert "description에는\n  `입력 사실`과 `JKM`을 쓰지 않습니다" in scenario
    assert "[U1]" in dimension
    assert "label은 핵심 대상과 변화 축을 담되 30자를 넘지 않습니다" in dimension
    assert "rationale은 최대 200자의 구체적인 한국어 한 문장" in dimension
    assert "question은 필요한 관측 정보와 판단 대상을 충분히 포함" in dimension
    assert "2026년 6월 30일 유럽 저장률이 49.1%로 관측" in dimension
    assert "Choice label은 비교 가능한 하나의 시장·운영 상태를 30자 이내" in dimension
    assert "새로운 수치 경계" in dimension
    assert f"direction은 {StateDirection.prompt_values()}" in dimension
    assert "`관측된 사실 → 미래 상태 → JKM 영향`" in dimension
    assert "문장 끝의 `가정`" in dimension
    assert "가정이라는 메타 표현은 문장 끝에서 한 번만" in dimension
    assert "`상태를 가정하면`, `상황을 가정하면`, `나타나는 가정이다`" in dimension
    assert "`Event 배경으로 제시된 사실` 같은 출처 메타 설명 없이" in dimension
    assert "`답`, `응답`, `선택`, `선택한 값`이라는 말도" in dimension
    assert "주입 부담이 완화되고 NWE 가격 지지" in dimension
    assert "스프레드가 다시 벌어지고 아시아가" in dimension
    assert "별도 Anchor 참조 ID나 새 사실을" in dimension
    assert "sourceImpactPathIds" not in dimension
    assert "## Dimension 질문과 선택지" in scenario
    assert "[D1.V1]" in scenario
    assert "미리 정한 유형에 맞추지 말고" in scenario
    assert "pressure 단계만 한 칸씩 바꾼" in scenario
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
    assert V4ReadableAdditionalDimensionDesignDraft(dimensions=[]).dimensions == []


def test_llm_validation_error_detail_preserves_field_locations_for_retry() -> None:
    with pytest.raises(ValueError) as error:
        V4ReadableScenarioSynthesisDraft.model_validate(
            {
                "title": "테스트 그룹",
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
    assert "Choice의 미래 상태와 JKM 영향을 바로 연결" in why_schema["description"]
    assert "문장 끝의 '가정'으로만" in why_schema["description"]
    assert "가정 의미를 반복" in why_schema["description"]
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

    assert "선택한 이벤트" in properties["title"]["description"]
    assert "summary" not in properties
    assert "영문 Event/Scenario" in properties["description"]["description"]
    assert "'입력 사실', JKM은 사용하지 않음" in properties["description"]["description"]
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
