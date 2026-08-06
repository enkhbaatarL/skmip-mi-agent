from __future__ import annotations

from typing import Any


def evaluate_candidate(
    classification: str,
    target_type: str,
    base_content: str,
    proposed_content: str,
    source_feedback_id: str,
    duplicate: bool,
) -> dict[str, Any]:
    checks = [
        {"checkId": "schema_valid", "label": "Content schema valid", "passed": bool(proposed_content.strip())},
        {
            "checkId": "learnable_target",
            "label": "Memory/Skill target only",
            "passed": target_type in {"memory", "skill"},
        },
        {"checkId": "source_trace", "label": "Source feedback trace", "passed": bool(source_feedback_id)},
        {"checkId": "non_empty_diff", "label": "Non-empty change", "passed": proposed_content != base_content},
        {
            "checkId": "forbidden_action",
            "label": "No automatic code/catalog/approval instruction",
            "passed": not any(
                word in proposed_content.lower() for word in ("자동 승인", "코드 자가 수정", "catalog 자동")
            ),
        },
        {
            "checkId": "classification",
            "label": "Candidate classification",
            "passed": classification in {"memory", "skill"},
        },
        {"checkId": "duplicate", "label": "No pending duplicate", "passed": not duplicate},
    ]
    passed = sum(item["passed"] for item in checks)
    return {"passed": passed, "total": len(checks), "allPassed": passed == len(checks), "checks": checks}
