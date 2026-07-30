from __future__ import annotations

import pytest

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    EventImpactFact,
    V4ExcludedScenarioCandidate,
    V4GenerationResult,
    V4ScenarioCandidate,
    finalize_v4_generation_result,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    build_model_lever_user_prompt,
)
from apps.persistence.model_parameter.schema import (
    ModelImpactLeverParameterBinding,
    ModelImpactLeverPayload,
)
from apps.persistence.scenario.schema import (
    DimensionDefinition,
    DimensionValueDefinition,
)


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
    event_ids: list[int],
    lever_code: str,
) -> DimensionDefinition:
    return DimensionDefinition(
        dimension_id=dimension_id,
        label=dimension_id,
        description=f"{dimension_id} description",
        required=True,
        display_order=1,
        dimension_type="magnitude",
        value_kind="categorical",
        source_event_ids=event_ids,
        lever_refs=[lever_code],
        values=[
            DimensionValueDefinition(value_id="low", label="낮음"),
            DimensionValueDefinition(value_id="high", label="높음"),
        ],
    )


def _valid_result() -> V4GenerationResult:
    return V4GenerationResult(
        group_title="JKM 복수 이벤트 시나리오",
        group_description="이벤트 결합에 따른 JKM 가격 범위",
        event_impact_facts=[
            EventImpactFact(
                event_id=101,
                lever_code="weather_demand",
                domain="demand",
                change_direction="increase",
                target_market_direction="bullish",
                timing="2027년 동절기",
                magnitude_evidence="평년 대비 낮은 기온",
                fact_basis="이벤트의 한파 전망",
                confidence=0.8,
            ),
            EventImpactFact(
                event_id=202,
                lever_code="liquefaction_availability",
                domain="supply",
                change_direction="decrease",
                target_market_direction="bullish",
                timing="2027년 상반기",
                magnitude_evidence="일부 Train 정비",
                fact_basis="이벤트의 정비 일정",
                confidence=0.7,
            ),
        ],
        dimension_definitions=[
            _dimension(
                dimension_id="cold_wave_intensity",
                event_ids=[101],
                lever_code="weather_demand",
            ),
            _dimension(
                dimension_id="liquefaction_recovery",
                event_ids=[202],
                lever_code="liquefaction_availability",
            ),
            _dimension(
                dimension_id="risk_premium",
                event_ids=[101, 202],
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
                target_market_pressure_band="strong_bullish",
                target_market_pressure_rationale="JKM 상승 압력",
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
                target_market_pressure_band="balanced",
                target_market_pressure_rationale="상승·하락 요인 상쇄",
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
                target_market_pressure_band="strong_bearish",
                target_market_pressure_rationale="JKM 하락 압력",
                probability_score=15,
            ),
        ],
        excluded_scenarios=[
            V4ExcludedScenarioCandidate(
                target_market_pressure_band="bullish",
                reason_code="LOW_DISTINCTIVENESS",
                reason="상단 시나리오와 독립적인 검토 가치가 낮음",
            ),
            V4ExcludedScenarioCandidate(
                target_market_pressure_band="bearish",
                reason_code="LOW_DISTINCTIVENESS",
                reason="하단 시나리오와 독립적인 검토 가치가 낮음",
            ),
        ],
    )


def _catalog() -> list[ModelImpactLeverPayload]:
    return [
        _lever(
            lever_id=1,
            code="weather_demand",
            domain="demand",
            support_status="executable",
        ),
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
    ]


def test_v4_request_requires_two_to_five_unique_events() -> None:
    payload = V4MultiEventCreateScenariosIn(
        mi_event_ids=[101, 202],
        target_market="JKM",
        user_id=7,
    )

    assert payload.mi_event_ids == [101, 202]
    with pytest.raises(ValueError):
        V4MultiEventCreateScenariosIn(
            mi_event_ids=[101, 101],
            target_market="JKM",
            user_id=7,
        )


def test_v4_sync_and_background_routes_are_registered() -> None:
    from apps.agents.scenario_group_agent.api import router

    paths = {route.path for route in router.routes if "POST" in getattr(route, "methods", set())}

    assert "/v4/scenario-groups" in paths
    assert "/v4/scenario-groups/sync" in paths


def test_v4_finalizer_assigns_roles_and_parameter_coverage() -> None:
    result, coverage = finalize_v4_generation_result(
        _valid_result(),
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )

    assert [scenario.scenario_role for scenario in result.scenarios] == [
        "ceiling",
        "mixed",
        "floor",
    ]
    assert result.scenarios[1].baseline_yn is True
    assert result.dimension_definitions[0].model_support_status == "full"
    assert result.dimension_definitions[1].model_support_status == "none"
    assert result.dimension_definitions[2].model_support_status == "price_only"
    assert coverage.coverage_status == "partial"
    assert coverage.covered_dimension_ids == ["cold_wave_intensity"]
    assert coverage.uncovered_dimension_ids == [
        "liquefaction_recovery",
        "risk_premium",
    ]
    assert [detail.model_dump() for detail in coverage.unsupported_lever_details] == [
        {
            "lever_code": "financial_market_sentiment",
            "reason_code": "PRICE_ONLY",
            "parameter_name": None,
        },
        {
            "lever_code": "liquefaction_availability",
            "reason_code": "INACTIVE_MODEL_PARAMETER",
            "parameter_name": "Parameter2",
        },
    ]


def test_v4_finalizer_rejects_unknown_lever() -> None:
    result = _valid_result()
    result.dimension_definitions[0].lever_refs = ["invented_parameter"]

    with pytest.raises(ValueError, match="unknown levers"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_requires_an_executable_dimension() -> None:
    result = _valid_result()
    result.dimension_definitions[0].lever_refs = ["liquefaction_availability"]

    with pytest.raises(
        ValueError,
        match="at least one dimension must reference an executable",
    ):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_prompt_uses_event_facts_target_market_and_catalog() -> None:
    prompt = build_model_lever_user_prompt(
        events=[
            {
                "mi_event_id": 101,
                "event_title_ko": "동북아 한파",
                "one_line_summary": "겨울 수요 증가 가능성",
            },
        ],
        target_market="JKM",
        impact_levers=[lever.model_dump() for lever in _catalog()],
        catalog_version="v1",
    )

    assert "동북아 한파" in prompt
    assert "JKM" in prompt
    assert "weather_demand" in prompt
    assert "적어도 하나의 dimension은 executable" in prompt
    assert "Template Domain Knowledge" not in prompt
