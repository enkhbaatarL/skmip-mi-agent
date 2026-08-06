from __future__ import annotations

from app.learning.classifier import classify_feedback
from app.learning.diff import append_learning_line
from app.learning.evaluator import evaluate_candidate
from app.learning.memory_rules import (
    MEMORY_RULE_MARKER,
    active_skill_guidance,
    apply_clarification_defaults,
    learning_rule_payload,
    parse_embedded_rules,
)
from app.services.feedback_service import interpret_feedback


def test_feedback_rules_honor_specificity_and_scope() -> None:
    spot = interpret_feedback("현물 cargo 영향이 너무 직접적이니 완화", "run", None, None)
    risk = interpret_feedback("위험 프리미엄이 과도하니 보수적으로 줄임", "run", None, None)
    supply = interpret_feedback("공급 효과가 너무 커서 완화", "run", None, None)
    increase = interpret_feedback("너무 작다. 키워", "parameter", "scenario-1", "nea_lng_demand_index")
    demand_increase = interpret_feedback("수요 영향이 너무 작다", "parameter", "scenario-1", "nea_lng_demand_index")
    spot_increase = interpret_feedback(
        "현물 cargo 영향이 너무 작다", "parameter", "scenario-1", "asia_spot_cargo_availability_index"
    )
    assert (spot["parameterCode"], spot["factor"]) == ("asia_spot_cargo_availability_index", 0.7)
    assert (risk["parameterCode"], risk["factor"]) == ("lng_market_risk_proxy_index", 0.6)
    assert (supply["domain"], supply["factor"]) == ("supply", 0.8)
    assert (increase["parameterCode"], increase["factor"]) == ("nea_lng_demand_index", 1.15)
    assert demand_increase["factor"] == 1.15
    assert spot_increase["factor"] == 1.15
    assert interpret_feedback("좋아요", "run", None, None)["interpreted"] is False


def test_learning_classification_diff_and_evaluation() -> None:
    skill = classify_feedback("계산 전에 반드시 검증 절차를 수행", "result_review", {})
    memory = classify_feedback("공급 영향은 기본적으로 보수적으로 표시", "result_review", {})
    no_candidate = classify_feedback("확인", "result_review", {})
    assert skill["classification"] == "skill"
    assert memory["classification"] == "memory"
    assert no_candidate["classification"] == "no_candidate"
    proposed, line, diff = append_learning_line("- base", "memory", "공급 영향 완화")
    evaluation = evaluate_candidate("memory", "memory", "- base", proposed, "feedback-id", False)
    assert line in proposed
    assert line in diff
    assert evaluation["allPassed"] is True


def test_learning_diff_preserves_machine_readable_context() -> None:
    context = {"scope": "parameter", "scenarioKey": "scenario-1", "focusParameter": "p1"}
    payload = learning_rule_payload(
        "memory",
        "너무 작다. 강화",
        context,
        {},
        {"interpreted": True, "factor": 1.15, "parameterCode": "p1", "scenarioKey": "scenario-1"},
    )
    proposed, _, _ = append_learning_line("- base", "memory", "너무 작다. 강화", payload)
    rules = parse_embedded_rules(proposed, MEMORY_RULE_MARKER)
    assert rules[0]["adjustment"]["factor"] == 1.15
    assert rules[0]["context"] == context

    default_payload = learning_rule_payload(
        "memory",
        "event_recovery",
        {"scope": "run"},
        {"questionId": "parameter_horizon", "value": {"choiceId": "event_recovery"}},
        {},
    )
    with_default, _, _ = append_learning_line(proposed, "memory", "event_recovery", default_payload)
    effective = apply_clarification_defaults(with_default, {})
    assert effective["parameter_horizon"] == {"choiceId": "event_recovery"}

    latest_default_payload = learning_rule_payload(
        "memory",
        "event_only",
        {"scope": "run"},
        {"questionId": "parameter_horizon", "value": {"choiceId": "event_only"}},
        {},
    )
    with_latest, _, _ = append_learning_line(
        with_default,
        "memory",
        "event_only",
        latest_default_payload,
    )
    assert apply_clarification_defaults(with_latest, {})["parameter_horizon"] == {"choiceId": "event_only"}
    assert apply_clarification_defaults(
        with_latest,
        {"parameter_horizon": {"choiceId": "event_recovery"}},
    )["parameter_horizon"] == {"choiceId": "event_recovery"}

    skill_payload = learning_rule_payload("skill", "계산 전에 반드시 검증", {}, {}, {})
    skill_content, _, _ = append_learning_line("1. base", "skill", "계산 전에 반드시 검증", skill_payload)
    assert active_skill_guidance(skill_content) == ["계산 전에 반드시 검증"]
