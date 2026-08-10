from __future__ import annotations

# ruff: noqa: CPY001
import json
from pathlib import Path
from typing import Any

from tests.manual.multi_event_comparison.models import ComparisonJudgment


# Agent-runtime judge request helpers for multi-event comparison. This module
# performs no model call; the Codex or Claude instance executing the skill
# writes a schema-conformant judgment.

PROMPT_VERSION = "v5-agent-runtime-relative-coverage-neutral"

CRITERIA = {
    "event_consistency": "Supplied events와 모순이 없고 인과 근거가 있는지 평가한다.",
    "lng_dimension_quality": (
        "LNG 가격 관련 공급·수요·무역·시점·회복·완화·상호작용 driver가 유용한 dimension으로 반영됐는지 평가한다. "
        "현재 활성 모델 파라미터 catalog의 coverage 자체는 dimension 품질 점수에 반영하지 않는다."
    ),
    "floor_ceiling_quality": (
        "floor와 ceiling이 단순 label이 아니라 실제 cells와 pressure rationale의 일관된 feasible 극단값인지 평가한다. "
        "strong_bearish/strong_bullish band의 존재 자체를 요구하지 말고, 제외된 band가 있으면 excludedCandidates의 "
        "reason과 Event 사실을 함께 검토해 제외 타당성을 평가한다."
    ),
    "mixed_quality": (
        "mixed는 optional이다. mixed의 존재나 부재 자체로 가감점하지 않는다. 생성됐다면 실제 bullish/bearish driver와 "
        "offset·interaction 근거가 타당한지 평가하고, 생성되지 않았다면 누락이 scenario spectrum에 실질적인 공백을 "
        "만드는 경우에만 감점한다."
    ),
}

PAIRWISE_CRITERIA = {
    "event_grounding": (
        "어느 버전이 Event의 관측 사실·수치·지역·lineage를 더 정확히 보존하고 사실과 가정을 더 잘 구분하는지 비교한다."
    ),
    "dimension_and_value_quality": (
        "어느 버전의 dimension과 value가 LNG 공급·수요·저장·무역·회복 driver를 "
        "중복 없이 더 유용한 분기로 표현하는지 비교한다."
    ),
    "scenario_logic_and_explainability": (
        "어느 버전의 관측 사실 → 추가 가정 → 선택 value → 가격 압력 연결이 더 탄탄하고 "
        "Scenario 간 차이가 더 명확한지 비교한다."
    ),
    "baseline_and_exclusion_quality": (
        "어느 버전의 baseline과 floor/ceiling 및 제외 Scenario 근거가 더 개연성 있고 Event 사실과 양립하는지 비교한다."
    ),
    "user_comprehensibility": (
        "도메인 사용자가 결과만 읽었을 때 어느 버전의 선택과 결론을 더 쉽게 추적하고 납득할 수 있는지 비교한다."
    ),
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
            (
                "Do not penalize a missing pressure band when excludedCandidates gives an Event-grounded reason "
                "that makes the omitted band less plausible than the generated floor or ceiling."
            ),
            (
                "Do not penalize the absence of an optional mixed scenario by itself; judge the grounding only "
                "when mixed exists, and penalize absence only for a material spectrum gap demonstrated by the "
                "supplied evidence."
            ),
            (
                "Treat coverageStatus=partial|none, unsupportedLevers, and unsupportedLeverDetails only as "
                "non-scoring capability warnings caused by the currently active model-parameter catalog. Do not "
                "lower criterion scores or verdicts, pairwise outcomes, bestVersions, qualityRecommendation, or "
                "practicalRecommendation solely because full parameter coverage is unavailable. Preserve the "
                "limitation in weaknesses or recommendation tradeoffs."
            ),
            (
                "Do not interpret parameterMappingReady=true as full parameter coverage. Penalize only an "
                "independent quality defect, such as missing Event lineage, incoherent or duplicate dimensions, "
                "a false executable-support claim, or contradictory or missing coverage diagnostics."
            ),
            (
                "Treat absolute criteria scores as eligibility and condition checks, not as the sole relative "
                "winner decision."
            ),
            (
                "Return every unordered successful-version pair exactly once and compare every required pairwise "
                "criterion exactly once."
            ),
            (
                "A pairwise winner must be one of that pair or tie. Consider evidence and a concrete counterargument "
                "before deciding."
            ),
            "Populate strengths and weaknesses from the actual output; do not infer quality from the API version name.",
            "Set bestVersions to every version tied for the highest simple average absolute criterion score.",
            (
                "Choose qualityRecommendation from direct pairwise evidence, prioritizing grounding and user "
                "acceptance over latency/token cost."
            ),
            (
                "Choose practicalRecommendation using both relative quality and supplied performance evidence, "
                "and state when it should be selected."
            ),
        ],
        "criteria": CRITERIA,
        "pairwiseCriteria": PAIRWISE_CRITERIA,
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
