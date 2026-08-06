from __future__ import annotations

import re
from typing import Any

SKILL_SIGNALS = ("검증", "순서", "절차", "계산 전", "선행 조건", "반드시", "먼저", "단계")
MEMORY_SIGNALS = (
    "기본",
    "선호",
    "표시",
    "낮춰",
    "줄여",
    "완화",
    "높여",
    "강화",
    "보수적",
    "현물",
    "cargo",
    "수요",
    "공급",
    "위험",
)


def classify_feedback(raw_text: str, source: str, answer: dict[str, Any]) -> dict[str, Any]:
    normalized = re.sub(r"\s+", " ", raw_text.strip().lower())
    skill_matches = [signal for signal in SKILL_SIGNALS if signal in normalized]
    memory_matches = [signal for signal in MEMORY_SIGNALS if signal in normalized]
    if skill_matches:
        return {
            "classification": "skill",
            "matchedSignals": skill_matches,
            "confidence": min(0.95, 0.65 + len(skill_matches) * 0.05),
            "rationale": "반복 가능한 검증·순서·선행 절차 변경 신호를 감지했습니다.",
        }
    if memory_matches:
        return {
            "classification": "memory",
            "matchedSignals": memory_matches,
            "confidence": min(0.9, 0.55 + len(memory_matches) * 0.05),
            "rationale": "반복 가능한 표현·수치·선호 조정 신호를 감지했습니다.",
        }
    if source == "clarification" and answer:
        return {
            "classification": "memory",
            "matchedSignals": ["clarification_default"],
            "confidence": 0.45,
            "rationale": "객관식 Clarification 응답을 반복 가능한 낮은 신뢰도 기본값으로 분류했습니다.",
        }
    return {
        "classification": "no_candidate",
        "matchedSignals": [],
        "confidence": 0.2,
        "rationale": "일회성·모호·중복 또는 신호 부족으로 영구 Asset 변경을 제안하지 않습니다.",
    }
