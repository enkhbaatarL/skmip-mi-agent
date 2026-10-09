# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from apps.agents.model_parameter_agent.flows.propose_parameters import nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    CandidateRoutingAssessment,
    LLMSlotProposalResponse,
    LLMValueAdjustment,
    LLMValueCell,
    LLMValueProposalResponse,
    LLMVariationFactors,
    RoutingDecision,
)
from apps.agents.model_parameter_agent.utils.variation_policy import (
    CONDITIONAL_ROUTING_POLICIES,
    PARAMETER_VARIATION_POLICIES,
    VARIATION_POLICY_RELEASE,
    VariationFactors,
    calculate_bounded_assumption,
    validate_atomic_share_assumption,
)
from apps.common.exceptions.custom import MIBaseError


V4_CONTEXT = {
    "scenario": {"scenario_id": 501, "title": "공급 차질 심화"},
    "scenario_group": {
        "api_version": "v4",
        "generation_strategy": "multi_event_model_lever_dimensions",
    },
    "events": [{"mi_event_id": 11, "event_title_ko": "설비 차질"}],
}


def test_bounded_expert_policy_covers_exactly_the_active_v4_1_parameters() -> None:
    assert VARIATION_POLICY_RELEASE == "bounded-expert-v3"
    assert set(PARAMETER_VARIATION_POLICIES) == {
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "Population",
        "HurricaneIntensity",
        "LiqProdAdjustment",
        "LiqUtilAdjustment",
        "PipelineAdjustment",
        "RegasAdjustment",
        "SupplyDisruption",
        "PNG Contract Volume",
        "ShippingCost",
        "RegionalProductionAdjustment",
        "ShippingFuelCost",
        "CanalToll",
    }


def test_v4_routing_limit_is_separate_from_the_legacy_limit() -> None:
    settings = SimpleNamespace(
        model_parameter_max_routing_candidates_per_dimension=2,
        model_parameter_v4_max_routing_candidates_per_dimension=3,
    )

    assert (
        nodes._configured_routing_candidate_limit(  # noqa: SLF001
            settings,
            V4_CONTEXT,
        )
        == 3
    )
    assert (
        nodes._configured_routing_candidate_limit(  # noqa: SLF001
            settings,
            {"scenario_group": {"api_version": "v3"}},
        )
        == 2
    )


def test_balanced_policy_clips_strong_assumption_to_parameter_specific_medium() -> None:
    result = calculate_bounded_assumption(
        parameter_name="Temperature",
        reference_value=20.0,
        direction="increase",
        severity="strong",
        mode="balanced",
    )

    assert result.proposed_value == 21.5
    assert result.applied_severity == "medium"
    assert result.clipped is True
    assert "절대 변화" in result.calculation_ko


def test_profiled_assumption_is_deterministic_and_varies_inside_the_severity_band() -> None:
    lower = VariationFactors(
        duration="short",
        scope="narrow",
        offset="strong",
        confidence="low",
        sibling_position="lower",
        rationale_ko="단기·국소 영향이며 대체 수단이 충분함",
    )
    upper = VariationFactors(
        duration="long",
        scope="broad",
        offset="none",
        confidence="high",
        sibling_position="upper",
        rationale_ko="장기·광역 영향이며 상쇄 수단이 없음",
    )

    low_result = calculate_bounded_assumption(
        parameter_name="ShippingCost",
        reference_value=100_000.0,
        direction="increase",
        severity="medium",
        mode="balanced",
        variation_factors=lower,
    )
    high_result = calculate_bounded_assumption(
        parameter_name="ShippingCost",
        reference_value=100_000.0,
        direction="increase",
        severity="medium",
        mode="balanced",
        variation_factors=upper,
    )
    repeated = calculate_bounded_assumption(
        parameter_name="ShippingCost",
        reference_value=100_000.0,
        direction="increase",
        severity="medium",
        mode="balanced",
        variation_factors=upper,
    )

    assert low_result.proposed_value == 105_000.0
    assert high_result.proposed_value == 115_000.0
    assert repeated == high_result
    assert low_result.profile_position == 0.0
    assert high_result.profile_position == 1.0


def test_missing_profile_preserves_the_existing_severity_cap() -> None:
    result = calculate_bounded_assumption(
        parameter_name="ShippingCost",
        reference_value=100_000.0,
        direction="increase",
        severity="medium",
        mode="balanced",
    )

    assert result.proposed_value == 115_000.0
    assert result.profile_position is None


def test_strict_mode_rejects_assumption_and_power_mix_enforces_member_guardrail() -> None:
    with pytest.raises(MIBaseError, match="strict variation mode"):
        calculate_bounded_assumption(
            parameter_name="GDP",
            reference_value=0.03,
            direction="decrease",
            severity="weak",
            mode="strict",
        )

    with pytest.raises(MIBaseError, match="share guardrail"):
        validate_atomic_share_assumption(
            reference_value=0.2,
            proposed_value=0.3,
            severity="medium",
            mode="balanced",
        )


def test_step1_5_structured_assessment_keeps_grounded_assumption_and_explains_it() -> None:
    candidate = {
        "candidate_key": "pipeline",
        "mapping_strategy": "v4",
        "mapping_method": "routing",
        "binding_selection_mode": "conditional",
        "canonical_parameter_name": "PipelineAdjustment",
    }
    low_confidence = {
        **candidate,
        "candidate_key": "shipping",
        "canonical_parameter_name": "ShippingCost",
    }
    task = {
        "dimension_key": "v4|route|blocked|trade",
        "is_v4": True,
        "selection_mode": "conditional",
        "candidates": [candidate, low_confidence],
    }
    decision = RoutingDecision(
        dimension_key=task["dimension_key"],
        selected_candidate_keys=["pipeline"],
        candidate_assessments=[
            CandidateRoutingAssessment(
                candidate_key="pipeline",
                decision="ASSUMPTION_ELIGIBLE",
                evidence_basis="BOUNDED_ASSUMPTION",
                causal_path_ko="노선 차질이 연결 배관의 가용 물량을 낮춤",
                target_scope_ko="명시된 송·수입국 연결 배관",
                direction="decrease",
                time_scope_ko="차질 지속 기간",
                confidence="medium",
                rationale_ko="대상과 방향은 특정되며 정량 폭만 부재",
            ),
            CandidateRoutingAssessment(
                candidate_key="shipping",
                decision="ASSUMPTION_ELIGIBLE",
                evidence_basis="BOUNDED_ASSUMPTION",
                causal_path_ko="우회 가능성으로 운송비가 상승할 수 있음",
                target_scope_ko="LNG 운송비",
                direction="increase",
                time_scope_ko="차질 지속 기간",
                confidence="low",
                rationale_ko="직접 운임 근거는 약함",
            ),
        ],
    )

    selected, warnings = nodes._sanitize_routing_decisions(  # noqa: SLF001
        [decision],
        [task],
        max_candidates_per_dimension=3,
        variation_mode="balanced",
    )

    assert [item["candidate_key"] for item in selected] == ["pipeline"]
    assert selected[0]["routing_evidence"][0]["evidence_basis"] == "BOUNDED_ASSUMPTION"
    assert selected[0]["routing_evidence"][0]["causal_path_ko"].startswith("노선 차질")
    assert any("low-confidence" in warning for warning in warnings)


def _route_disruption_candidate(
    parameter_name: str,
    *,
    direction: str = "disrupt",
    scope: str = "호르무즈 경유 LNG 선박",
    time_window: str = "분석 기준일 이후 단기",
) -> dict[str, object]:
    return {
        "candidate_key": f"route-{parameter_name}",
        "mapping_strategy": "v4",
        "mapping_method": "routing",
        "binding_selection_mode": "conditional",
        "scenario_dimension_key": "d1",
        "source_dimension_id": "d1",
        "source_dimension_value_id": "d1_v3",
        "canonical_parameter_name": parameter_name,
        "parameter_name": parameter_name,
        "lever_code": "route_disruption",
        "direction": direction,
        "level": "통항 지연·우회",
        "scope": scope,
        "time_window": time_window,
        "source_dimension_label": "항로 차질 강도",
        "source_dimension_value_label": "통항 지연·우회 확인",
        "derivation_rationale": ("실제 LNG 선박 통항 지연과 우회로 항차 시간이 늘어나는 경로"),
    }


def _not_applicable_assessment(candidate_key: str) -> CandidateRoutingAssessment:
    return CandidateRoutingAssessment(
        candidate_key=candidate_key,
        decision="NOT_APPLICABLE",
        evidence_basis="NOT_APPLICABLE",
        causal_path_ko="직접 정량값이 없다고 판단",
        target_scope_ko="대상 미확정",
        direction="unknown",
        time_scope_ko="기간 미확정",
        confidence="high",
        rationale_ko="적용하지 않음",
    )


def test_route_routing_policy_recovers_only_shipping_cost_after_complete_all_na() -> None:
    candidates = [
        _route_disruption_candidate("ShippingCost"),
        _route_disruption_candidate("ShippingFuelCost"),
        _route_disruption_candidate("CanalToll"),
    ]
    task = {
        "dimension_key": "v4|d1|d1v3|routedisruption",
        "is_v4": True,
        "selection_mode": "conditional",
        "candidates": candidates,
    }
    decision = RoutingDecision(
        dimension_key=task["dimension_key"],
        selected_candidate_keys=[],
        candidate_assessments=[_not_applicable_assessment(str(candidate["candidate_key"])) for candidate in candidates],
    )

    recovered, warnings = nodes._recover_all_not_applicable_v4_conditional_candidates(  # noqa: SLF001
        [decision],
        [task],
        [],
        variation_mode="balanced",
    )

    assert [item["canonical_parameter_name"] for item in recovered] == [
        "ShippingCost",
    ]
    evidence = recovered[0]["routing_evidence"][0]
    assert evidence["decision"] == "ASSUMPTION_ELIGIBLE"
    assert evidence["evidence_basis"] == "BOUNDED_ASSUMPTION"
    assert evidence["direction"] == "increase"
    assert evidence["direction_semantics"] == "parameter"
    assert evidence["confidence"] == "medium"
    assert "선복" in evidence["causal_path_ko"]
    assert "제외 경계" in evidence["rationale_ko"]
    assert recovered[0]["_routing_selection_method"] == ("POLICY_BACKED_ALL_NOT_APPLICABLE_RECOVERY")
    assert len(warnings) == 1


def test_route_routing_policy_keeps_hallucination_boundaries() -> None:
    assert set(CONDITIONAL_ROUTING_POLICIES) == {
        ("route_disruption", "ShippingCost"),
        ("route_disruption", "ShippingFuelCost"),
        ("route_disruption", "CanalToll"),
        ("regional_price_spread", "ShippingCost"),
    }
    assert CONDITIONAL_ROUTING_POLICIES[("route_disruption", "ShippingCost")].allow_policy_recovery is True
    assert CONDITIONAL_ROUTING_POLICIES[("route_disruption", "ShippingFuelCost")].allow_policy_recovery is False
    assert CONDITIONAL_ROUTING_POLICIES[("route_disruption", "CanalToll")].allow_policy_recovery is False
    assert CONDITIONAL_ROUTING_POLICIES[("regional_price_spread", "ShippingCost")].allow_policy_recovery is True

    candidate = _route_disruption_candidate("ShippingCost", time_window="")
    task = {
        "dimension_key": "v4|d1|d1v3|routedisruption",
        "is_v4": True,
        "selection_mode": "conditional",
        "candidates": [candidate],
    }
    decision = RoutingDecision(
        dimension_key=task["dimension_key"],
        selected_candidate_keys=[],
        candidate_assessments=[
            _not_applicable_assessment(str(candidate["candidate_key"])),
        ],
    )

    no_time, _ = nodes._recover_all_not_applicable_v4_conditional_candidates(  # noqa: SLF001
        [decision],
        [task],
        [],
        variation_mode="balanced",
    )
    strict, _ = nodes._recover_all_not_applicable_v4_conditional_candidates(  # noqa: SLF001
        [decision],
        [task],
        [],
        variation_mode="strict",
    )

    assert no_time == []
    assert strict == []


def test_regional_spread_policy_requires_physical_cargo_reallocation() -> None:
    candidate = {
        "candidate_key": "spread-shipping",
        "mapping_strategy": "v4",
        "mapping_method": "routing",
        "binding_selection_mode": "conditional",
        "canonical_parameter_name": "ShippingCost",
        "parameter_name": "ShippingCost",
        "lever_code": "regional_price_spread",
        "direction": "increase",
        "level": "지역 스프레드 확대",
        "scope": "유럽향 LNG cargo",
        "time_window": "2027년",
        "source_dimension_label": "지역 가격 격차",
        "source_dimension_value_label": "유럽 프리미엄 확대",
        "derivation_rationale": "아시아행 선적이 유럽향으로 재배분되어 장거리 선복 수요가 증가",
    }
    task = {
        "dimension_key": "v4|d1|d1v3|regionalpricespread",
        "is_v4": True,
        "selection_mode": "conditional",
        "candidates": [candidate],
    }
    decision = RoutingDecision(
        dimension_key=task["dimension_key"],
        selected_candidate_keys=[],
        candidate_assessments=[_not_applicable_assessment("spread-shipping")],
    )

    recovered, _ = nodes._recover_all_not_applicable_v4_conditional_candidates(  # noqa: SLF001
        [decision],
        [task],
        [],
        variation_mode="balanced",
    )
    assert [item["canonical_parameter_name"] for item in recovered] == [
        "ShippingCost",
    ]

    price_only = {
        **candidate,
        "scope": "유럽 LNG 가격",
        "derivation_rationale": "유럽 프리미엄이 확대된다",
    }
    price_task = {**task, "candidates": [price_only]}
    excluded, _ = nodes._recover_all_not_applicable_v4_conditional_candidates(  # noqa: SLF001
        [decision],
        [price_task],
        [],
        variation_mode="balanced",
    )
    assert excluded == []


def test_step1_5_live_shape_all_na_is_recovered_before_semantic_abstention(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidates = [
        _route_disruption_candidate("ShippingCost"),
        _route_disruption_candidate("ShippingFuelCost"),
        _route_disruption_candidate("CanalToll"),
    ]
    task_key = "v4|d1|d1v3|routedisruption"
    response = SimpleNamespace(
        result=nodes.LLMCandidateValidationResponse(
            routing_decisions=[
                RoutingDecision(
                    dimension_key=task_key,
                    selected_candidate_keys=[],
                    candidate_assessments=[
                        _not_applicable_assessment(
                            str(candidate["candidate_key"]),
                        )
                        for candidate in candidates
                    ],
                ),
            ],
        ),
        usage=None,
        model="test",
        attempt_count=1,
        retry_count=0,
        retry_reasons=(),
        retry_delays_seconds=(),
    )

    async def fake_invoke(**_: object) -> SimpleNamespace:
        return response

    monkeypatch.setattr(nodes, "_invoke_structured", fake_invoke)
    monkeypatch.setattr(nodes, "_debug_stage_payload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        nodes,
        "get_settings",
        lambda: SimpleNamespace(
            model_parameter_v4_max_routing_candidates_per_dimension=3,
            model_parameter_max_routing_candidates_per_dimension=2,
            model_parameter_max_conditional_parameters_per_scenario=4,
            model_parameter_variation_mode="balanced",
        ),
    )
    state = ModelParameterProposalState(
        scenario_id=501,
        scenario_context=V4_CONTEXT,
        candidate_mappings=candidates,
    )

    output = asyncio.run(nodes.validate_parameter_candidates(state))

    assert [item["canonical_parameter_name"] for item in output["candidate_mappings"]] == ["ShippingCost"]
    assert output["candidate_mappings"][0]["routing_evidence"][0]["evidence_basis"] == "BOUNDED_ASSUMPTION"
    assert any("bounded routing 정책" in warning for warning in output["validation_warnings"])


def test_step2_conservative_recovery_uses_one_target_and_earliest_period_only() -> None:
    candidate = {
        "candidate_key": "shipping-cost",
        "mapping_strategy": "v4",
        "canonical_parameter_name": "ShippingCost",
        "parameter_name": "ShippingCost",
    }
    catalog = [
        {
            "candidate_key": "shipping-cost",
            "fixed_axis_names": [],
            "time_axis_names": ["Year"],
            "fixed_axis_hierarchy": [{"period_group_id": "p1"}],
            "period_groups": [
                {
                    "period_group_id": "p1",
                    "available_periods": [{"Year": 2027}, {"Year": 2026}],
                },
            ],
        },
    ]

    recovered, warnings = nodes._conservative_v4_slot_recovery(  # noqa: SLF001
        [],
        [candidate],
        catalog,
        scenario_context=V4_CONTEXT,
    )

    assert len(recovered) == 1
    assert recovered[0]["slot_axes"] == [{"axis_name": "Year", "axis_value": 2026}]
    assert recovered[0]["_selection_method"] == "V4_CONSERVATIVE_UNIQUE_INFERENCE"
    assert len(warnings) == 1


def test_step2_conservative_recovery_never_selects_a_past_month(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "_current_year_month", lambda: (2026, 10))
    candidate = {
        "candidate_key": "shipping-cost",
        "mapping_strategy": "v4",
        "canonical_parameter_name": "ShippingCost",
        "parameter_name": "ShippingCost",
    }
    catalog = [
        {
            "candidate_key": "shipping-cost",
            "fixed_axis_names": [],
            "time_axis_names": ["Year", "Month"],
            "fixed_axis_hierarchy": [{"period_group_id": "p1"}],
            "period_groups": [
                {
                    "period_group_id": "p1",
                    "available_periods": [
                        {"Year": 2026, "Months": [1, 11]},
                        {"Year": 2027, "Months": [1]},
                    ],
                },
            ],
        },
    ]

    recovered, _ = nodes._conservative_v4_slot_recovery(  # noqa: SLF001
        [],
        [candidate],
        catalog,
        scenario_context=V4_CONTEXT,
    )

    assert recovered[0]["slot_axes"] == [
        {"axis_name": "Year", "axis_value": 2026},
        {"axis_name": "Month", "axis_value": 11},
    ]


def test_step2_grounded_recovery_resolves_unique_pipeline_and_explicit_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "_current_year_month", lambda: (2026, 10))
    candidate = {
        "candidate_key": "pipeline",
        "canonical_parameter_name": "PipelineAdjustment",
        "parameter_name": "PipelineAdjustment",
        "source_event_ids": [11],
    }
    context = {
        **V4_CONTEXT,
        "events": [
            {
                "mi_event_id": 11,
                "detail_analysis": ("Northeast Pipeline의 US발 Canada행 흐름이 2027년에 감소"),
            },
        ],
    }
    catalog = {
        "candidate_key": "pipeline",
        "fixed_axis_names": ["Pipeline", "From", "To"],
        "time_axis_names": ["Year"],
        "fixed_axis_hierarchy": [
            {
                "axis_value": "Northeast Pipeline",
                "children": [
                    {
                        "axis_value": "US",
                        "children": [
                            {"axis_value": "Canada", "period_group_id": "p1"},
                        ],
                    },
                ],
            },
        ],
        "period_groups": [
            {
                "period_group_id": "p1",
                "available_periods": [{"Year": 2026}, {"Year": 2027}],
            },
        ],
    }

    recovered, warnings = nodes._grounded_v4_slot_recovery(  # noqa: SLF001
        [],
        [candidate],
        [catalog],
        scenario_context=context,
    )

    assert recovered[0]["_selection_method"] == "V4_GROUNDED_CATALOG_EXPANSION"
    assert recovered[0]["slot_axes"] == [
        {"axis_name": "Pipeline", "axis_value": "Northeast Pipeline"},
        {"axis_name": "From", "axis_value": "US"},
        {"axis_name": "To", "axis_value": "Canada"},
        {"axis_name": "Year", "axis_value": 2027},
    ]
    assert len(warnings) == 1


def test_step2_grounded_recovery_enriches_existing_slot_for_closed_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "_current_year_month", lambda: (2026, 10))
    candidate = {
        "candidate_key": "shipping-cost",
        "canonical_parameter_name": "ShippingCost",
        "parameter_name": "ShippingCost",
        "source_event_ids": [11],
    }
    context = {
        **V4_CONTEXT,
        "events": [
            {
                "mi_event_id": 11,
                "detail_analysis": "LNG cargo 재배분이 2026년 10월-2026년 12월 이어진다.",
            },
        ],
    }
    catalog = {
        "candidate_key": "shipping-cost",
        "fixed_axis_names": [],
        "time_axis_names": ["Year", "Month"],
        "fixed_axis_hierarchy": [{"period_group_id": "p1"}],
        "period_groups": [
            {
                "period_group_id": "p1",
                "available_periods": [{"Year": 2026, "Months": [10, 11, 12]}],
            },
        ],
    }
    existing = [
        {
            "candidate_key": "shipping-cost",
            "slot_axes": [
                {"axis_name": "Year", "axis_value": 2026},
                {"axis_name": "Month", "axis_value": 10},
            ],
        },
    ]

    expanded, warnings = nodes._grounded_v4_slot_recovery(  # noqa: SLF001
        existing,
        [candidate],
        [catalog],
        scenario_context=context,
    )

    assert [
        nodes._coordinates_for_selected_slot(slot)["Month"]  # noqa: SLF001
        for slot in expanded
    ] == [10, 11, 12]
    assert len(warnings) == 2


def test_step2_grounding_ignores_llm_routing_catalog_horizon(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "_current_year_month", lambda: (2026, 10))
    candidate = {
        "candidate_key": "shipping-cost",
        "canonical_parameter_name": "ShippingCost",
        "parameter_name": "ShippingCost",
        "source_event_ids": [11],
        "routing_evidence": [
            {
                "time_scope_ko": "허용된 2026~2030 Year 좌표에서 선택",
                "target_scope_ko": "Year별 전역 LNG charter rate",
            },
        ],
        "lever_provenance": [
            {
                "source_event_ids": [11],
                "time_window": "분석 기준일 이후 단기",
            },
        ],
    }
    context = {
        **V4_CONTEXT,
        "events": [
            {
                "mi_event_id": 11,
                "detail_analysis": "2026년 10월 이후 LNG cargo 운송 차질이 단기 지속된다.",
            },
        ],
    }
    catalog = {
        "candidate_key": "shipping-cost",
        "fixed_axis_names": [],
        "time_axis_names": ["Year"],
        "fixed_axis_hierarchy": [{"period_group_id": "p1"}],
        "period_groups": [
            {
                "period_group_id": "p1",
                "available_periods": [
                    {"Year": year}
                    for year in range(2026, 2031)
                ],
            },
        ],
    }

    grounded = nodes._grounded_v4_slot_candidates(  # noqa: SLF001
        candidate,
        catalog,
        context,
    )

    assert grounded == [{"Year": 2026}]


def test_step2_grounded_recovery_rejects_ambiguous_pipeline_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "_current_year_month", lambda: (2026, 10))
    candidate = {
        "candidate_key": "pipeline",
        "canonical_parameter_name": "PipelineAdjustment",
        "parameter_name": "PipelineAdjustment",
        "source_event_ids": [11],
    }
    context = {
        **V4_CONTEXT,
        "events": [
            {
                "mi_event_id": 11,
                "detail_analysis": "US발 Canada행 흐름이 2027년에 감소",
            },
        ],
    }
    pipeline_nodes = [
        {
            "axis_value": pipeline,
            "children": [
                {
                    "axis_value": "US",
                    "children": [
                        {"axis_value": "Canada", "period_group_id": "p1"},
                    ],
                },
            ],
        }
        for pipeline in ("Northeast Pipeline", "Northern Pipeline")
    ]
    catalog = {
        "candidate_key": "pipeline",
        "fixed_axis_names": ["Pipeline", "From", "To"],
        "time_axis_names": ["Year"],
        "fixed_axis_hierarchy": pipeline_nodes,
        "period_groups": [
            {"period_group_id": "p1", "available_periods": [{"Year": 2027}]},
        ],
    }

    assert (
        nodes._grounded_v4_slot_candidates(  # noqa: SLF001
            candidate,
            catalog,
            context,
        )
        == []
    )


def test_step2_grounded_recovery_requires_both_liquefaction_plant_and_train(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "_current_year_month", lambda: (2026, 10))
    candidate = {
        "candidate_key": "liq-util",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "parameter_name": "LiqUtilAdjustment",
        "source_event_ids": [11],
    }
    catalog = {
        "candidate_key": "liq-util",
        "fixed_axis_names": ["LNG Plant", "LNG Plant Train"],
        "time_axis_names": ["Year", "Month"],
        "fixed_axis_hierarchy": [
            {
                "axis_value": "Sabine Pass LNG Plant",
                "children": [
                    {"axis_value": "Train 1", "period_group_id": "p1"},
                    {"axis_value": "Train 2", "period_group_id": "p1"},
                ],
            },
        ],
        "period_groups": [
            {
                "period_group_id": "p1",
                "available_periods": [{"Year": 2026, "Months": [9, 11]}],
            },
        ],
    }
    plant_only = {
        **V4_CONTEXT,
        "events": [
            {
                "mi_event_id": 11,
                "detail_analysis": "Sabine Pass LNG Plant의 2026년 11월 이용률 하락",
            },
        ],
    }
    exact = {
        **V4_CONTEXT,
        "events": [
            {
                "mi_event_id": 11,
                "detail_analysis": ("Sabine Pass LNG Plant Train 2의 2026년 11월 이용률 하락"),
            },
        ],
    }

    assert (
        nodes._grounded_v4_slot_candidates(  # noqa: SLF001
            candidate,
            catalog,
            plant_only,
        )
        == []
    )
    assert nodes._grounded_v4_slot_candidates(  # noqa: SLF001
        candidate,
        catalog,
        exact,
    ) == [
        {
            "LNG Plant": "Sabine Pass LNG Plant",
            "LNG Plant Train": "Train 2",
            "Year": 2026,
            "Month": 11,
        },
    ]


def test_step2_prompt_exposes_only_grounded_catalog_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "_current_year_month", lambda: (2026, 10))
    monkeypatch.setattr(
        nodes,
        "get_settings",
        lambda: SimpleNamespace(
            model_parameter_max_parameter_slots=100,
            model_parameter_grounded_slot_recovery_enabled=True,
        ),
    )
    candidate = {
        "candidate_key": "liq-util",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "parameter_name": "LiqUtilAdjustment",
        "source_event_ids": [11],
    }
    context = {
        **V4_CONTEXT,
        "events": [
            {
                "mi_event_id": 11,
                "detail_analysis": ("Sabine Pass LNG Plant Train 2의 2026년 11월 이용률 하락"),
            },
        ],
    }
    catalog = {
        "candidate_key": "liq-util",
        "parameter_name": "LiqUtilAdjustment",
        "key_axes": ["LNG Plant", "LNG Plant Train", "Year", "Month"],
        "fixed_axis_names": ["LNG Plant", "LNG Plant Train"],
        "time_axis_names": ["Year", "Month"],
        "fixed_axis_hierarchy": [
            {
                "axis_value": "Sabine Pass LNG Plant",
                "children": [
                    {"axis_value": "Train 2", "period_group_id": "p1"},
                ],
            },
        ],
        "period_groups": [
            {
                "period_group_id": "p1",
                "available_periods": [{"Year": 2026, "Months": [11]}],
            },
        ],
    }

    tasks = nodes._build_parameter_slot_tasks(  # noqa: SLF001
        context,
        [candidate],
        [catalog],
        [],
    )

    assert tasks[0]["evidence_grounded_coordinate_hints"] == [
        {
            "coordinates": {
                "LNG Plant": "Sabine Pass LNG Plant",
                "LNG Plant Train": "Train 2",
                "Year": 2026,
                "Month": 11,
            },
            "policy": (
                "현재 Scenario/Event/Lever 원문과 실제 catalog에서 유일 일치한 대상·기간; "
                "LLM은 현재 task applicability를 재확인하되 다른 target으로 확대하지 않음"
            ),
        },
    ]


def test_step3_bounded_assumption_is_server_calculated_and_slot_rationale_is_explicit() -> None:
    candidate = {
        "candidate_key": "liq-util",
        "mapping_strategy": "v4",
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "parameter_name": "LiqUtilAdjustment",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "proposal_constraints": {"minimum": 0},
        "routing_evidence": [
            {
                "decision": "ASSUMPTION_ELIGIBLE",
                "evidence_basis": "BOUNDED_ASSUMPTION",
                "causal_path_ko": "feedgas 차질로 검증된 Train 이용률 하락",
                "target_scope_ko": "Plant A Train 1",
                "time_scope_ko": "2026년 8월",
            },
        ],
    }
    slots = [
        {
            "candidate_key": "liq-util",
            "slot_key": "slot-1",
            "slot_axes": [
                {"axis_name": "LNG Plant", "axis_value": "Plant A"},
                {"axis_name": "LNG Plant Train", "axis_value": "Train 1"},
                {"axis_name": "Year", "axis_value": 2026},
                {"axis_name": "Month", "axis_value": 8},
            ],
        },
    ]
    references = [
        {
            "candidate_key": "liq-util",
            "slot_key": "slot-1",
            "axes": {
                "LNG Plant": "Plant A",
                "LNG Plant Train": "Train 1",
                "Year": 2026,
                "Month": 8,
            },
            "actual_basecase_value": 0.8,
            "lut_default_value": 0.8,
            "llm_reference_value": 0.8,
            "basecase_reference_id": "ref-1",
        },
    ]
    adjustment = LLMValueAdjustment(
        candidate_key="liq-util",
        rationale_ko="이용률 하락을 반영합니다.",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=0.1,
                rationale_ko="정량값이 없어 중간 강도를 가정했습니다.",
                evidence_basis="BOUNDED_ASSUMPTION",
                direction="decrease",
                severity="medium",
                assumption_ko="차질 강도를 medium으로 한정",
                variation_factors=LLMVariationFactors(
                    duration="long",
                    scope="broad",
                    offset="none",
                    confidence="high",
                    sibling_position="middle",
                    rationale_ko="장기·광역 차질이고 상쇄 수단이 확인되지 않음",
                ),
            ),
        ],
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(  # noqa: SLF001
        [adjustment],
        [candidate],
        slots,
        references,
        scenario_context=V4_CONTEXT,
        variation_mode="balanced",
    )

    assert warnings == []
    assert sanitized[0]["value_grid"][0]["proposed_value"] == pytest.approx(0.72)
    rationale = sanitized[0]["value_grid"][0]["rationale_ko"]
    assert "대상·기간:" in rationale
    assert "근거 유형: BOUNDED_ASSUMPTION" in rationale
    assert "인과 경로:" in rationale
    assert "기준값: 0.8 utilization_fraction" in rationale
    assert "적용 정책: bounded-expert-v3/balanced/decrease/medium" in rationale
    assert "변형 요인: 지속=long, 범위=broad, 상쇄=none, 신뢰도=high" in rationale
    assert "불확실성:" in rationale
    assert sanitized[0]["_variation_policy_trace"][0]["structured_fields_supplied"] is True


def test_step3_missing_structured_evidence_is_repaired_then_rejected_if_still_missing() -> None:
    candidate = {
        "candidate_key": "pmi",
        "mapping_strategy": "v4",
        "model_file": "Demand",
        "model_sheet": "PMI",
        "parameter_name": "PMI",
        "canonical_parameter_name": "PMI",
    }
    slot = {
        "candidate_key": "pmi",
        "slot_key": "slot-1",
        "slot_axes": [
            {"axis_name": "Country", "axis_value": "Japan"},
            {"axis_name": "Year", "axis_value": 2026},
        ],
    }
    reference = {
        "candidate_key": "pmi",
        "slot_key": "slot-1",
        "axes": {"Country": "Japan", "Year": 2026},
        "value": 50.0,
        "reference_id": "ref-pmi",
    }
    adjustment = LLMValueAdjustment(
        candidate_key="pmi",
        rationale_ko="PMI 하락을 반영합니다.",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=48.0,
                rationale_ko="하락 시나리오입니다.",
            ),
        ],
    )

    repair_keys = nodes._value_repair_candidate_keys(  # noqa: SLF001
        [adjustment],
        [candidate],
        [slot],
        require_structured_evidence=True,
    )
    sanitized, warnings = nodes._sanitize_llm_adjustments(  # noqa: SLF001
        [adjustment],
        [candidate],
        [slot],
        [reference],
        scenario_context=V4_CONTEXT,
        variation_mode="balanced",
        require_structured_evidence=True,
    )

    assert repair_keys == {"pmi"}
    assert sanitized == []
    assert any("구조화 근거" in warning for warning in warnings)


def test_step3_rejects_direction_that_conflicts_with_derived_value() -> None:
    candidate = {
        "candidate_key": "pmi",
        "mapping_strategy": "v4",
        "model_file": "Demand",
        "model_sheet": "PMI",
        "parameter_name": "PMI",
        "canonical_parameter_name": "PMI",
    }
    slot = {
        "candidate_key": "pmi",
        "slot_key": "slot-1",
        "slot_axes": [{"axis_name": "Year", "axis_value": 2026}],
    }
    reference = {
        "candidate_key": "pmi",
        "slot_key": "slot-1",
        "axes": {"Year": 2026},
        "value": 50.0,
        "reference_id": "ref-pmi",
    }
    adjustment = LLMValueAdjustment(
        candidate_key="pmi",
        rationale_ko="PMI 방향을 계산합니다.",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=48.0,
                rationale_ko="계산 결과",
                evidence_basis="DERIVED",
                direction="increase",
                calculation_ko="기준 50에서 2를 차감",
            ),
        ],
    )

    sanitized, warnings = nodes._sanitize_llm_adjustments(  # noqa: SLF001
        [adjustment],
        [candidate],
        [slot],
        [reference],
        scenario_context=V4_CONTEXT,
        variation_mode="balanced",
        require_structured_evidence=True,
    )

    assert sanitized == []
    assert any("서로 모순" in warning for warning in warnings)


def test_step2_recovers_global_explicit_periods_without_semantic_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "candidate_key": "shipping-cost",
        "mapping_strategy": "v4",
        "canonical_parameter_name": "ShippingCost",
        "parameter_name": "ShippingCost",
    }
    responses = [LLMSlotProposalResponse(parameter_slots=[])]

    async def fake_invoke(**_: object) -> SimpleNamespace:
        return SimpleNamespace(result=responses.pop(0), usage=None, model="test")

    monkeypatch.setattr(nodes, "_invoke_structured", fake_invoke)
    monkeypatch.setattr(nodes, "_debug_stage_payload", lambda *_args, **_kwargs: None)
    state = ModelParameterProposalState(
        scenario_id=501,
        scenario_context={
            **V4_CONTEXT,
            "events": [
                {
                    "mi_event_id": 11,
                    "detail_analysis": "LNG cargo 재배분이 2026-2027년에 이어진다.",
                },
            ],
        },
        candidate_mappings=[candidate],
        slot_catalog=[
            {
                "candidate_key": "shipping-cost",
                "fixed_axis_names": [],
                "time_axis_names": ["Year"],
                "fixed_axis_hierarchy": [{"period_group_id": "p1"}],
                "period_groups": [
                    {
                        "period_group_id": "p1",
                        "available_periods": [{"Year": 2026}, {"Year": 2027}],
                    },
                ],
            },
        ],
    )

    output = asyncio.run(nodes.propose_parameter_slots(state))

    assert [
        slot["slot_axes"][0]["axis_value"]
        for slot in output["parameter_slots"]
    ] == [2026, 2027]
    assert all(
        slot["_selection_method"] == "V4_GROUNDED_CATALOG_EXPANSION"
        for slot in output["parameter_slots"]
    )
    assert [call["step"] for call in output["llm_calls"]] == ["Step2 slot proposal"]


def test_step3_uses_deterministic_weak_fallback_without_semantic_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "candidate_key": "liq-util",
        "mapping_strategy": "v4",
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "parameter_name": "LiqUtilAdjustment",
        "canonical_parameter_name": "LiqUtilAdjustment",
        "proposal_constraints": {"minimum": 0},
        "routing_evidence": [
            {
                "decision": "DIRECT",
                "evidence_basis": "DERIVED",
                "direction": "decrease",
                "direction_semantics": "parameter",
                "lever_code": "liquefaction_utilization",
                "causal_path_ko": "feedgas 차질로 이용률 하락",
                "target_scope_ko": "검증된 exact slot",
                "time_scope_ko": "2026년",
                "rationale_ko": "catalog-pinned 방향",
            },
        ],
    }
    invalid = LLMValueProposalResponse(
        parameter_adjustments=[
            LLMValueAdjustment(
                candidate_key="liq-util",
                rationale_ko="첫 응답",
                slot_values=[
                    LLMValueCell(
                        slot_key="slot-1",
                        proposed_value=0.5,
                        rationale_ko="구조화 근거 누락",
                    ),
                ],
            ),
        ],
    )
    responses = [invalid]

    async def fake_invoke(**_: object) -> SimpleNamespace:
        return SimpleNamespace(result=responses.pop(0), usage=None, model="test")

    monkeypatch.setattr(nodes, "_invoke_structured", fake_invoke)
    monkeypatch.setattr(nodes, "_debug_stage_payload", lambda *_args, **_kwargs: None)
    state = ModelParameterProposalState(
        scenario_id=501,
        scenario_context=V4_CONTEXT,
        candidate_mappings=[candidate],
        slot_candidate_mappings=[candidate],
        parameter_slots=[
            {
                "candidate_key": "liq-util",
                "slot_key": "slot-1",
                "slot_axes": [{"axis_name": "Year", "axis_value": 2026}],
            },
        ],
        effective_references=[
            {
                "candidate_key": "liq-util",
                "slot_key": "slot-1",
                "axes": {"Year": 2026},
                "actual_basecase_value": 0.8,
                "lut_default_value": 0.8,
                "llm_reference_value": 0.8,
                "basecase_reference_id": "ref-1",
            },
        ],
        resolved_config={
            "model_parameter_variation_mode": "balanced",
        },
    )

    output = asyncio.run(nodes.propose_parameter_values(state))

    value = output["parameter_adjustments"][0]["value_grid"][0]["proposed_value"]
    assert value < 0.8
    assert output["parameter_adjustments"][0]["_variation_policy_trace"][0]["applied_severity"] == "weak"
    assert any("deterministic weak fallback" in warning for warning in output["validation_warnings"])
    assert [call["step"] for call in output["llm_calls"]] == ["Step3 value proposal"]


def test_step3_no_change_fallback_requires_one_unambiguous_parameter_direction() -> None:
    candidate = {
        "candidate_key": "shipping-cost",
        "mapping_strategy": "v4",
        "parameter_name": "ShippingCost",
        "canonical_parameter_name": "ShippingCost",
        "routing_evidence": [
            {
                "direction": "increase",
                "direction_semantics": "parameter",
                "lever_code": "regional_price_spread",
            },
        ],
    }
    slots = [
        {
            "candidate_key": "shipping-cost",
            "slot_key": "slot-1",
            "slot_axes": [{"axis_name": "Year", "axis_value": 2027}],
        },
    ]
    references = [
        {
            "candidate_key": "shipping-cost",
            "slot_key": "slot-1",
            "axes": {"Year": 2027},
            "value": 100_000.0,
            "reference_id": "ref-1",
        },
    ]
    unchanged = LLMValueAdjustment(
        candidate_key="shipping-cost",
        rationale_ko="기준값 유지",
        slot_values=[
            LLMValueCell(
                slot_key="slot-1",
                proposed_value=100_000.0,
                rationale_ko="변화 없음",
                evidence_basis="DERIVED",
                direction="unchanged",
                calculation_ko="기준값 유지",
            ),
        ],
    )

    fallback_keys = nodes._derived_no_change_candidate_keys(  # noqa: SLF001
        [unchanged],
        slots,
        references,
    )
    replaced, warnings = nodes._apply_deterministic_value_fallbacks(  # noqa: SLF001
        [unchanged],
        [candidate],
        slots,
        references,
        fallback_candidate_keys=fallback_keys,
        variation_mode="balanced",
    )

    assert fallback_keys == {"shipping-cost"}
    assert replaced[0].slot_values[0].evidence_basis == "BOUNDED_ASSUMPTION"
    assert replaced[0].slot_values[0].direction == "increase"
    assert len(warnings) == 1

    conflicted = {
        **candidate,
        "routing_evidence": [
            *candidate["routing_evidence"],
            {
                "direction": "decrease",
                "direction_semantics": "parameter",
                "lever_code": "route_disruption",
            },
        ],
    }
    retained, conflict_warnings = nodes._apply_deterministic_value_fallbacks(  # noqa: SLF001
        [unchanged],
        [conflicted],
        slots,
        references,
        fallback_candidate_keys=fallback_keys,
        variation_mode="balanced",
    )
    assert retained == [unchanged]
    assert conflict_warnings == []


def test_sibling_scenarios_are_comparison_only_in_v4_prompt() -> None:
    context = {
        **V4_CONTEXT,
        "sibling_scenarios": [
            {
                "scenario_id": 502,
                "title": "완화 경로",
                "narrative": "차질이 빠르게 해소된다.",
                "dimension_values": {"supply_path": "recovery"},
                "scenario_role": "floor",
            },
        ],
    }

    brief = nodes._scenario_brief_for_value_prompt(  # noqa: SLF001
        context,
        allowed_dimension_keys={"supply_path"},
    )

    assert brief["comparison_only_sibling_scenarios"] == [
        {
            "scenario_id": 502,
            "title": "완화 경로",
            "narrative_excerpt": "차질이 빠르게 해소된다.",
            "dimension_values": {"supply_path": "recovery"},
            "scenario_role": "floor",
        },
    ]


def test_v4_value_prompt_exposes_mode_and_policy_without_new_public_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        nodes,
        "get_settings",
        lambda: SimpleNamespace(model_parameter_variation_mode="balanced"),
    )
    packet = nodes._build_value_proposal_prompt_packet(  # noqa: SLF001
        V4_CONTEXT,
        [],
        [],
        [],
        [],
    )

    assert packet["variation_mode"] == "balanced"
    assert packet["variation_policy_release"] == "bounded-expert-v3"
    assert packet["variation_profile_enabled"] is True
