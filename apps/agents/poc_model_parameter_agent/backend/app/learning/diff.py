from __future__ import annotations

import difflib

from app.learning.memory_rules import encoded_rule_suffix


def append_learning_line(
    base_content: str,
    classification: str,
    raw_text: str,
    rule_payload: dict[str, object] | None = None,
) -> tuple[str, str, str]:
    cleaned = " ".join(raw_text.strip().split())
    suffix = encoded_rule_suffix(classification, rule_payload)
    if classification == "skill":
        existing_steps = sum(1 for line in base_content.splitlines() if line.strip() and line.lstrip()[0:1].isdigit())
        change_line = f"{existing_steps + 1}. 사용자 검토 규칙: {cleaned}{suffix}"
    else:
        change_line = f"- 사용자 검토 선호: {cleaned}{suffix}"
    proposed = f"{base_content.rstrip()}\n{change_line}\n"
    diff_lines = difflib.unified_diff(
        base_content.splitlines(),
        proposed.splitlines(),
        fromfile="active",
        tofile="proposed",
        lineterm="",
    )
    return proposed, change_line, "\n".join(diff_lines)
