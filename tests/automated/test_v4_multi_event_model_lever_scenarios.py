from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from openai import pydantic_function_tool
import pytest

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import (
    v4_flow as v4_flow_module,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_flow import (
    run_v4_multi_event_scenarios_inline,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    EventDimensionCoverage,
    EventImpactFact,
    V4ExcludedScenarioCandidate,
    V4GenerationResult,
    V4ScenarioCandidate,
    finalize_v4_generation_result,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    build_model_lever_user_prompt,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.model_parameter.schema import (
    ModelImpactLeverParameterBinding,
    ModelImpactLeverPayload,
)
from apps.persistence.scenario.schema import (
    DimensionDefinition,
    DimensionValueDefinition,
    ImpactLeverReference,
    RelatedMarket,
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
    fact_ids: list[str],
    lever_code: str,
    impact_lever_id: int | None = None,
) -> DimensionDefinition:
    return DimensionDefinition(
        dimension_id=dimension_id,
        label=dimension_id,
        description=f"{dimension_id} description",
        required=True,
        display_order=1,
        dimension_type="magnitude",
        value_kind="categorical",
        source_event_ids=[999],
        source_fact_ids=fact_ids,
        lever_refs=["legacy_value_is_replaced"],
        impact_lever_refs=[
            ImpactLeverReference(
                impact_lever_id=impact_lever_id,
                lever_code=lever_code,
                source_fact_ids=fact_ids,
                mapping_rationale="dimension 불확실성을 이 영향 레버로 연결한다.",
            ),
        ],
        values=[
            DimensionValueDefinition(value_id="low", label="낮음"),
            DimensionValueDefinition(value_id="high", label="높음"),
        ],
    )


def _valid_result() -> V4GenerationResult:
    return V4GenerationResult(
        group_title="글로벌 LNG 복수 이벤트 시나리오",
        group_description="이벤트 결합에 따른 글로벌 LNG 가격 범위",
        event_impact_facts=[
            EventImpactFact(
                fact_id="event_101_weather",
                event_id=101,
                domain="demand",
                change_direction="increase",
                global_pressure_direction="bullish",
                timing="2027년 동절기",
                magnitude_evidence="평년 대비 낮은 기온",
                fact_basis="이벤트의 한파 전망",
                confidence=0.8,
            ),
            EventImpactFact(
                fact_id="event_101_liquefaction",
                event_id=101,
                domain="supply",
                change_direction="decrease",
                global_pressure_direction="bullish",
                timing="2027년 상반기",
                magnitude_evidence="일부 Train 정비",
                fact_basis="이벤트의 정비 일정",
                confidence=0.7,
            ),
            EventImpactFact(
                fact_id="event_101_sentiment",
                event_id=101,
                domain="price_only",
                change_direction="increase",
                global_pressure_direction="bullish",
                timing="2027년 상반기",
                magnitude_evidence="위험 프리미엄 확대",
                fact_basis="시장 심리 Event 근거",
                confidence=0.6,
            ),
            EventImpactFact(
                fact_id="event_202_fixed_outage",
                event_id=202,
                domain="supply",
                change_direction="decrease",
                global_pressure_direction="bullish",
                timing="현재",
                magnitude_evidence="확정 가동 중단",
                fact_basis="Event에서 확인된 공통 영향",
                confidence=0.9,
                common_impact_lever_refs=[
                    ImpactLeverReference(
                        lever_code="liquefaction_availability",
                        source_fact_ids=["event_202_fixed_outage"],
                        mapping_rationale="잔여 불확실성 없이 모든 Scenario에 공통 적용한다.",
                    ),
                ],
            ),
        ],
        dimension_definitions=[
            _dimension(
                dimension_id="cold_wave_intensity",
                fact_ids=["event_101_weather"],
                lever_code="weather_demand",
            ),
            _dimension(
                dimension_id="liquefaction_recovery",
                fact_ids=["event_101_liquefaction"],
                lever_code="liquefaction_availability",
            ),
            _dimension(
                dimension_id="risk_premium",
                fact_ids=["event_101_sentiment"],
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
        event_dimension_coverage=[
            EventDimensionCoverage(
                event_id=101,
                dimension_ids=[],
                rationale="Event 101의 잔여 불확실성이 세 dimension으로 분기된다.",
            ),
            EventDimensionCoverage(
                event_id=202,
                dimension_ids=[],
                no_dimension_reason="COMMON_FACT_NO_SCENARIO_DELTA",
                rationale="Event 202의 영향은 확정되어 공통 영향으로만 유지한다.",
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
        _lever(
            lever_id=4,
            code="direct_gas_demand",
            domain="demand",
            support_status=None,
        ),
    ]


def test_v4_request_requires_two_to_five_unique_events() -> None:
    payload = V4MultiEventCreateScenariosIn(
        mi_event_ids=[101, 202],
        user_id=7,
    )

    assert payload.mi_event_ids == [101, 202]
    assert "targetMarket" not in V4MultiEventCreateScenariosIn.model_json_schema(
        by_alias=True,
    )["properties"]
    with pytest.raises(ValueError):
        V4MultiEventCreateScenariosIn(
            mi_event_ids=[101, 101],
            user_id=7,
        )


def test_v4_sync_and_background_routes_are_registered() -> None:
    from apps.agents.scenario_group_agent.api import router

    paths = {route.path for route in router.routes if "POST" in getattr(route, "methods", set())}

    assert "/v4/scenario-groups" in paths
    assert "/v4/scenario-groups/sync" in paths


def test_v4_storage_uses_scenario_related_markets_without_group_target_market() -> None:
    from apps.persistence.scenario.models import MiScenarioModel
    from apps.persistence.scenario_group.models import (
        MiScenarioGroupModel,
        MiScenarioSnapModel,
    )

    assert "target_market" not in MiScenarioGroupModel.__table__.columns
    assert "related_markets" in MiScenarioModel.__table__.columns
    assert "related_markets" in MiScenarioSnapModel.__table__.columns


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
    assert result.dimension_definitions[0].source_event_ids == [101]
    assert result.dimension_definitions[0].lever_refs == ["weather_demand"]
    assert result.dimension_definitions[0].impact_lever_refs[0].impact_lever_id == 1
    assert result.event_impact_facts[-1].common_impact_lever_refs[0].impact_lever_id == 2
    assert result.event_dimension_coverage[0].dimension_ids == [
        "cold_wave_intensity",
        "liquefaction_recovery",
        "risk_premium",
    ]
    assert result.event_dimension_coverage[1].dimension_ids == []
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


def test_v4_schema_validation_failure_enters_feedback_retry_loop() -> None:
    invalid_response = MIBaseError(
        ErrorCode.LLM_INVALID_RESPONSE_ERROR,
        detail="groupTitle must not be blank",
    )
    invoke = AsyncMock(side_effect=[invalid_response, _valid_result()])

    with patch.object(
        v4_flow_module,
        "_invoke_v4_generation",
        new=invoke,
    ):
        result, _coverage = asyncio.run(
            v4_flow_module._generate_validated_v4_result(
                events=[
                    SimpleNamespace(mi_event_id=101),
                    SimpleNamespace(mi_event_id=202),
                ],
                impact_levers=_catalog(),
                catalog_version="v1",
                trace_context=None,
            ),
        )

    assert result.group_title
    assert invoke.await_count == 2
    assert "groupTitle" in invoke.await_args_list[1].kwargs["validation_feedback"]


def test_v4_inline_converts_boolean_baseline_to_database_yn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import (
        v4_flow,
    )
    from apps.persistence.event.schema import EventPayload
    from apps.persistence.scenario.schema import ScenarioPayload
    from apps.persistence.scenario_group.schema import ScenarioGroupPayload

    finalized, coverage = finalize_v4_generation_result(
        _valid_result(),
        event_ids=[101, 202],
        impact_levers=_catalog(),
    )
    monkeypatch.setattr(
        v4_flow,
        "_generate_validated_v4_result",
        AsyncMock(return_value=(finalized, coverage)),
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
    monkeypatch.setattr(
        v4_flow.ScenarioGroupService,
        "persist_multi_event_generation",
        persist,
    )

    response = asyncio.run(
        run_v4_multi_event_scenarios_inline(
            {
                "scenario_group": ScenarioGroupPayload(
                    scenario_group_id=10,
                    api_version="v4",
                    generation_strategy="multi_event_model_lever_dimensions",
                ),
                "events": [
                    EventPayload(
                        mi_event_id=101,
                        event_type_l2_id=8,
                        event_title_ko="한파",
                    ),
                    EventPayload(
                        mi_event_id=202,
                        event_type_l2_id=12,
                        event_title_ko="액화시설 정비",
                    ),
                ],
                "impact_levers": _catalog(),
                "impact_catalog_version": "v1",
                "comparison_run_id": "compare-1",
                "user_id": 7,
            },
        ),
    )

    saved = persist.call_args.kwargs["scenarios"]
    saved_diagnostics = persist.call_args.kwargs["generation_diagnostics"]
    assert [scenario["baseline_yn"] for scenario in saved] == ["N", "Y", "N"]
    assert saved[0]["related_markets"] == [
        {
            "market": "JKM",
            "rationale": "아시아향 화물 전환 가능성이 특별히 중요함",
        },
    ]
    assert response.data is not None
    assert saved_diagnostics["event_dimension_coverage"][1] == {
        "event_id": 202,
        "dimension_ids": [],
        "no_dimension_reason": "COMMON_FACT_NO_SCENARIO_DELTA",
        "rationale": "Event 202의 영향은 확정되어 공통 영향으로만 유지한다.",
    }
    assert response.data.generation_diagnostics.event_dimension_coverage[0].dimension_ids == [
        "cold_wave_intensity",
        "liquefaction_recovery",
        "risk_premium",
    ]
    assert response.data.table.rows[0].related_markets == [
        RelatedMarket(
            market="JKM",
            rationale="아시아향 화물 전환 가능성이 특별히 중요함",
        ),
    ]


def test_v4_finalizer_rejects_unknown_lever() -> None:
    result = _valid_result()
    result.dimension_definitions[0].impact_lever_refs[0].lever_code = "invented_parameter"

    with pytest.raises(ValueError, match="unknown lever"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_requires_an_executable_dimension() -> None:
    result = _valid_result()
    result.dimension_definitions[0].impact_lever_refs[0] = ImpactLeverReference(
        lever_code="direct_gas_demand",
        source_fact_ids=["event_101_weather"],
        mapping_rationale="실행 binding이 없는 demand 레버로 매핑한다.",
    )

    with pytest.raises(
        ValueError,
        match="at least one dimension must reference an executable",
    ):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_rejects_duplicate_fact_ids() -> None:
    result = _valid_result()
    result.event_impact_facts[1].fact_id = result.event_impact_facts[0].fact_id

    with pytest.raises(ValueError, match="fact ids must be unique"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_rejects_unknown_dimension_source_fact() -> None:
    result = _valid_result()
    dimension = result.dimension_definitions[0]
    dimension.source_fact_ids = ["missing_fact"]
    dimension.impact_lever_refs[0].source_fact_ids = ["missing_fact"]

    with pytest.raises(ValueError, match="references unknown facts"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_requires_impact_levers_to_cover_all_dimension_facts() -> None:
    result = _valid_result()
    dimension = result.dimension_definitions[0]
    dimension.source_fact_ids = [
        "event_101_weather",
        "event_101_liquefaction",
    ]

    with pytest.raises(ValueError, match="must cover source facts exactly"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_rejects_impact_lever_id_code_mismatch() -> None:
    result = _valid_result()
    result.dimension_definitions[0].impact_lever_refs[0].impact_lever_id = 2

    with pytest.raises(ValueError, match="id/code mismatch"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_rejects_fact_and_lever_domain_mismatch() -> None:
    result = _valid_result()
    result.dimension_definitions[0].impact_lever_refs[0].lever_code = "liquefaction_availability"

    with pytest.raises(ValueError, match="domain must match source facts"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_rejects_common_mapping_for_dimension_fact() -> None:
    result = _valid_result()
    result.event_impact_facts[0].common_impact_lever_refs = [
        ImpactLeverReference(
            lever_code="weather_demand",
            source_fact_ids=["event_101_weather"],
            mapping_rationale="dimension에서도 사용된 사실을 공통 매핑하려는 잘못된 결과",
        ),
    ]

    with pytest.raises(ValueError, match="referenced by a dimension"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_requires_common_mapping_for_dimension_free_fact() -> None:
    result = _valid_result()
    result.event_impact_facts[-1].common_impact_lever_refs = []

    with pytest.raises(
        ValueError,
        match="dimension-free fact .* must define common impact levers",
    ):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_finalizer_requires_reason_for_event_without_dimensions() -> None:
    result = _valid_result()
    result.event_dimension_coverage[1].no_dimension_reason = None

    with pytest.raises(ValueError, match="requires noDimensionReason"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_event_dimension_coverage_rejects_unknown_reason_code() -> None:
    with pytest.raises(ValueError, match="noDimensionReason"):
        EventDimensionCoverage.model_validate(
            {
                "eventId": 202,
                "dimensionIds": [],
                "noDimensionReason": "NO_RESIDUAL_UNCERTAINTY",
                "rationale": "지원하지 않는 과거 reason code",
            },
        )


def test_v4_finalizer_rejects_no_dimension_reason_for_covered_event() -> None:
    result = _valid_result()
    result.event_dimension_coverage[0].no_dimension_reason = "COMMON_FACT_NO_SCENARIO_DELTA"

    with pytest.raises(ValueError, match="must not define noDimensionReason"):
        finalize_v4_generation_result(
            result,
            event_ids=[101, 202],
            impact_levers=_catalog(),
        )


def test_v4_prompt_uses_event_facts_global_pressure_and_catalog() -> None:
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
    assert "Target Market" not in prompt
    assert "globalPressureRationale" in prompt
    assert "relatedMarkets" in prompt
    assert "weather_demand" in prompt
    assert "적어도 하나의 dimension은 executable" in prompt
    assert "Template Domain Knowledge" not in prompt


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
        {"dimensionId": key, "valueId": value}
        for key, value in scenario["dimensionValues"].items()
    ]

    parsed = V4GenerationResult.model_validate(payload)

    assert parsed.scenarios[0].dimension_values
