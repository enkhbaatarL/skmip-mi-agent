from __future__ import annotations

import copy
import json
from typing import Any

MEMORY_RULE_MARKER = "memory_rule="
SKILL_RULE_MARKER = "skill_rule="


def _runtime_context(context: dict[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(context[key])
        for key in ("scope", "scenarioKey", "focusParameter", "eventIds", "leverCodes", "parameterCodes")
        if context.get(key) not in (None, [], {})
    }


def learning_rule_payload(
    classification: str,
    raw_text: str,
    context: dict[str, Any],
    answer: dict[str, Any],
    adjustment: dict[str, Any],
) -> dict[str, Any]:
    if classification == "skill":
        return {
            "kind": "procedure",
            "instruction": raw_text.strip(),
            "context": _runtime_context(context),
        }
    if adjustment:
        return {
            "kind": "adjustment",
            "adjustment": copy.deepcopy(adjustment),
            "context": _runtime_context(context),
        }
    question_id = answer.get("questionId")
    if question_id and "value" in answer:
        return {
            "kind": "clarification_default",
            "questionId": str(question_id),
            "value": copy.deepcopy(answer["value"]),
            "context": _runtime_context(context),
        }
    return {
        "kind": "preference",
        "instruction": raw_text.strip(),
        "context": _runtime_context(context),
    }


def encoded_rule_suffix(classification: str, payload: dict[str, Any] | None) -> str:
    if payload is None:
        return ""
    marker = SKILL_RULE_MARKER if classification == "skill" else MEMORY_RULE_MARKER
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f" [{marker}{encoded}]"


def parse_embedded_rules(content: str, marker: str) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    token = f"[{marker}"
    for line in content.splitlines():
        start = line.find(token)
        if start < 0:
            continue
        encoded = line[start + len(token) :]
        encoded = encoded.removesuffix("]")
        try:
            value = json.loads(encoded)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rules.append(value)
    return rules


def apply_clarification_defaults(content: str, answers: dict[str, Any]) -> dict[str, Any]:
    effective = copy.deepcopy(answers)
    for rule in reversed(parse_embedded_rules(content, MEMORY_RULE_MARKER)):
        if rule.get("kind") != "clarification_default":
            continue
        question_id = rule.get("questionId")
        if isinstance(question_id, str) and question_id not in effective:
            effective[question_id] = copy.deepcopy(rule.get("value"))
    return effective


def active_skill_guidance(content: str) -> list[str]:
    embedded = parse_embedded_rules(content, SKILL_RULE_MARKER)
    return [
        str(rule["instruction"]).strip()
        for rule in embedded
        if rule.get("kind") == "procedure" and str(rule.get("instruction", "")).strip()
    ]
