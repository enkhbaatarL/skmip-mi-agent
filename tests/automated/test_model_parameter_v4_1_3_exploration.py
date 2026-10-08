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
    LLMSlotAxis,
    LLMSlotProposal,
    LLMSlotProposalResponse,
    LLMValueAdjustment,
    LLMValueCell,
    LLMValueProposalResponse,
    RoutingDecision,
)
from apps.agents.model_parameter_agent.utils.variation_policy import (
    CONDITIONAL_ROUTING_POLICIES,
    PARAMETER_VARIATION_POLICIES,
    VARIATION_POLICY_RELEASE,
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
    assert VARIATION_POLICY_RELEASE == "bounded-expert-v1"
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

    assert nodes._configured_routing_candidate_limit(  # noqa: SLF001
        settings,
        V4_CONTEXT,
    ) == 3
    assert nodes._configured_routing_candidate_limit(  # noqa: SLF001
        settings,
        {"scenario_group": {"api_version": "v3"}},
    ) == 2


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
        "derivation_rationale": (
            "실제 LNG 선박 통항 지연과 우회로 항차 시간이 늘어나는 경로"
        ),
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
        candidate_assessments=[
            _not_applicable_assessment(str(candidate["candidate_key"]))
            for candidate in candidates
        ],
    )

    recovered, warnings = (
        nodes._recover_all_not_applicable_v4_conditional_candidates(  # noqa: SLF001
            [decision],
            [task],
            [],
            variation_mode="balanced",
        )
    )

    assert [item["canonical_parameter_name"] for item in recovered] == [
        "ShippingCost",
    ]
    evidence = recovered[0]["routing_evidence"][0]
    assert evidence["decision"] == "ASSUMPTION_ELIGIBLE"
    assert evidence["evidence_basis"] == "BOUNDED_ASSUMPTION"
    assert evidence["direction"] == "increase"
    assert evidence["confidence"] == "medium"
    assert "선복" in evidence["causal_path_ko"]
    assert "연료가격" in evidence["rationale_ko"]
    assert recovered[0]["_routing_selection_method"] == (
        "POLICY_BACKED_ALL_NOT_APPLICABLE_RECOVERY"
    )
    assert len(warnings) == 1


def test_route_routing_policy_keeps_hallucination_boundaries() -> None:
    assert set(CONDITIONAL_ROUTING_POLICIES) == {
        ("route_disruption", "ShippingCost"),
        ("route_disruption", "ShippingFuelCost"),
        ("route_disruption", "CanalToll"),
    }
    assert CONDITIONAL_ROUTING_POLICIES[
        ("route_disruption", "ShippingCost")
    ].allow_policy_recovery is True
    assert CONDITIONAL_ROUTING_POLICIES[
        ("route_disruption", "ShippingFuelCost")
    ].allow_policy_recovery is False
    assert CONDITIONAL_ROUTING_POLICIES[
        ("route_disruption", "CanalToll")
    ].allow_policy_recovery is False

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

    assert [
        item["canonical_parameter_name"] for item in output["candidate_mappings"]
    ] == ["ShippingCost"]
    assert output["candidate_mappings"][0]["routing_evidence"][0][
        "evidence_basis"
    ] == "BOUNDED_ASSUMPTION"
    assert any(
        "bounded routing 정책" in warning
        for warning in output["validation_warnings"]
    )


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
    assert "적용 정책: bounded-expert-v1/balanced/decrease/medium" in rationale
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


def test_step2_repairs_only_a_missing_candidate_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = {
        "candidate_key": "shipping-cost",
        "mapping_strategy": "v4",
        "canonical_parameter_name": "ShippingCost",
        "parameter_name": "ShippingCost",
    }
    responses = [
        LLMSlotProposalResponse(parameter_slots=[]),
        LLMSlotProposalResponse(
            parameter_slots=[
                LLMSlotProposal(
                    candidate_key="shipping-cost",
                    slot_axes=[LLMSlotAxis(axis_name="Year", axis_value=2026)],
                ),
            ],
        ),
    ]

    async def fake_invoke(**_: object) -> SimpleNamespace:
        return SimpleNamespace(result=responses.pop(0), usage=None, model="test")

    monkeypatch.setattr(nodes, "_invoke_structured", fake_invoke)
    monkeypatch.setattr(nodes, "_debug_stage_payload", lambda *_args, **_kwargs: None)
    state = ModelParameterProposalState(
        scenario_id=501,
        scenario_context=V4_CONTEXT,
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
                        "available_periods": [{"Year": 2026}],
                    },
                ],
            },
        ],
        resolved_config={"model_parameter_semantic_repair_max_attempts": 2},
    )

    output = asyncio.run(nodes.propose_parameter_slots(state))

    assert len(output["parameter_slots"]) == 1
    assert output["semantic_repair_count"] == 1
    assert [call["step"] for call in output["llm_calls"]] == [
        "Step2 slot proposal",
        "Step2 semantic repair",
    ]


def test_step3_repairs_missing_evidence_and_uses_server_policy(
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
    repaired = LLMValueProposalResponse(
        parameter_adjustments=[
            LLMValueAdjustment(
                candidate_key="liq-util",
                rationale_ko="가동률 하락",
                slot_values=[
                    LLMValueCell(
                        slot_key="slot-1",
                        proposed_value=0.5,
                        rationale_ko="정성적 feedgas 차질을 보수적으로 반영",
                        evidence_basis="BOUNDED_ASSUMPTION",
                        direction="decrease",
                        severity="medium",
                        assumption_ko="차질 강도를 medium으로 한정",
                    ),
                ],
            ),
        ],
    )
    responses = [invalid, repaired]

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
            "model_parameter_semantic_repair_max_attempts": 2,
            "model_parameter_variation_mode": "balanced",
        },
    )

    output = asyncio.run(nodes.propose_parameter_values(state))

    assert output["parameter_adjustments"][0]["value_grid"][0][
        "proposed_value"
    ] == pytest.approx(0.72)
    assert output["semantic_repair_count"] == 1
    assert [call["step"] for call in output["llm_calls"]] == [
        "Step3 value proposal",
        "Step3 semantic repair",
    ]


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
    assert packet["variation_policy_release"] == "bounded-expert-v1"
