from __future__ import annotations

# ruff: noqa: CPY001
import json
from pathlib import Path
from typing import Any

from tests.manual.multi_event_comparison.models import ComparisonJudgment


# Agent-runtime judge request helpers for multi-event comparison. This module
# performs no model call; the Codex or Claude instance executing the skill
# writes a schema-conformant judgment.

PROMPT_VERSION = "v2-agent-runtime"

CRITERIA = {
    "event_consistency": "Supplied events와 모순이 없고 인과 근거가 있는지 평가한다.",
    "lng_dimension_quality": (
        "LNG 가격 관련 공급·수요·무역·시점·회복·완화·상호작용 driver가 유용한 dimension으로 반영됐는지 평가한다."
    ),
    "floor_ceiling_quality": (
        "floor와 ceiling이 단순 label이 아니라 실제 cells와 pressure rationale의 일관된 극단값인지 평가한다."
    ),
    "mixed_quality": "상반된 driver 조합이 필요한 경우에만 mixed가 존재하고 offset·interaction이 타당한지 평가한다.",
}


def build_agent_judge_input(evidence: dict[str, Any]) -> dict[str, Any]:
    """Build the self-contained semantic review request for the skill model."""
    return {
        "schemaVersion": 1,
        "promptVersion": PROMPT_VERSION,
        "judgeRuntime": "Use the Codex or Claude model currently executing the skill. Do not call an LLM API.",
        "constraints": [
            "Evaluate only the supplied Event and API evidence; do not browse or add outside facts.",
            "Return every successful version exactly once.",
            "Return each required criterion exactly once per version and score it from 1 to 5.",
            "Assess every scenario row exactly once while preserving scenario ID, title, and global pressure band.",
            "Use precise payload paths or actual values as evidence.",
            "Set bestVersions to every version tied for the highest simple average criterion score.",
        ],
        "criteria": CRITERIA,
        "outputSchema": ComparisonJudgment.model_json_schema(by_alias=True),
        "evidence": evidence,
    }


def load_agent_judgment(path: Path) -> ComparisonJudgment:
    """Parse the result written by the model executing the skill."""
    return ComparisonJudgment.model_validate_json(path.read_text(encoding="utf-8"))


def write_agent_judge_input(path: Path, payload: dict[str, Any]) -> None:
    """Persist the request without invoking a model provider."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
