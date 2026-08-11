from __future__ import annotations

# ruff: noqa: CPY001
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from .artifacts import RunArtifacts


# Agent-runtime judge contracts for scenario-quality evaluation. The manual
# evaluator exports evidence and a JSON schema. The Codex or Claude instance
# executing the skill writes the semantic judgment; this module validates it.

PROMPT_VERSION = "v2-agent-runtime"

SCENARIO_JUDGE_IDS = ("J-01", "J-02", "J-03", "J-04", "J-05", "J-06", "J-11")
SIGNPOST_JUDGE_IDS = ("J-07", "J-08", "J-09", "J-10")

SCENARIO_RUBRIC = {
    "J-01": "Event grounding: 이벤트 핵심 driver, 수치, 지역 반영 및 근거 없는 사실 생성을 평가한다.",
    "J-02": "Baseline validity: baseline이 edge case가 아닌 가장 개연성 높은 전개인지 평가한다.",
    "J-03": "Scenario spectrum: 낙관·비관·고충격 edge path와 중복 narrative를 평가한다.",
    "J-04": "Dimension quality: dimension과 value가 이벤트 기반 분기 논리를 표현하는지 평가한다.",
    "J-05": "Internal consistency: scenario 내부 모순과 상호 배타성 위반을 평가한다.",
    "J-06": "Domain/geography/market consistency: 시장·지역·상품 맥락이 이벤트와 맞는지 평가한다.",
    "J-11": "Clarity: 시장 참여자가 인과 사슬을 따라갈 수 있는지 평가한다.",
}
SIGNPOST_RUBRIC = {
    "J-07": "Signpost relevance: signpost가 이벤트 및 소속 scenario와 직접 연결되는지 평가한다.",
    "J-08": "Signpost discriminativeness: 소속 scenario를 다른 scenario와 구분하는지 평가한다.",
    "J-09": "Observability/temporal relevance: 관측 가능한 표현이며 이벤트 horizon에 맞는지 평가한다.",
    "J-10": "Causal direction/strength: direction, strength, reason이 scenario probability와 맞는지 평가한다.",
}


class Violation(BaseModel):
    """An evidence-backed quality issue found by a judge rubric item."""

    target_type: str
    target_id: str
    evidence: str
    reason: str
    suggested_fix: str
    fact_dependency: Literal["NONE", "EVENT_PAYLOAD_ONLY", "EXTERNAL_FACT_REQUIRED"]


class JudgeItemScore(BaseModel):
    """Score and violations for one rubric item."""

    judge_id: str
    score: int = Field(ge=1, le=5)
    verdict: Literal["PASS", "WARN", "FAIL"]
    violations: list[Violation] = Field(default_factory=list)


class JudgeResult(BaseModel):
    """One bounded rubric group evaluated by the skill runtime model."""

    items: list[JudgeItemScore]
    model: str = Field(min_length=1)
    prompt_version: str


class AgentJudgePass(BaseModel):
    """The scenario and signpost judgments from one evaluation pass."""

    scenario_set: JudgeResult
    signposts: JudgeResult


class AgentJudgeEvaluation(BaseModel):
    """All requested passes for one Event."""

    mi_event_id: int
    passes: list[AgentJudgePass] = Field(min_length=1, max_length=2)


class AgentJudgeOutput(BaseModel):
    """File written by the Codex or Claude instance executing the skill."""

    schema_version: Literal[1]
    batch_id: str
    evaluations: list[AgentJudgeEvaluation]


def build_agent_judge_input(
    *,
    batch_id: str,
    runs: list[RunArtifacts],
    stability_runs: int,
    deterministic_checks: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build a self-contained request for the model executing the skill."""
    return {
        "schemaVersion": 1,
        "batchId": batch_id,
        "promptVersion": PROMPT_VERSION,
        "stabilityRuns": stability_runs,
        "judgeRuntime": "Use the Codex or Claude model currently executing the skill. Do not call an LLM API.",
        "constraints": [
            "Evaluate only the supplied evidence; do not browse or add outside facts.",
            "Treat missing event detail as missing evidence, not permission to invent facts.",
            "Use EXTERNAL_FACT_REQUIRED when external verification is necessary.",
            "Return every required judge ID exactly once in each pass.",
            "Every WARN or FAIL must include a precise evidence reference, reason, suggested fix, and fact dependency.",
            "Use model='skill-runtime-model' unless the runtime exposes an exact model identifier.",
            f"Use prompt_version='{PROMPT_VERSION}' in every JudgeResult.",
        ],
        "rubrics": {
            "scenarioSet": SCENARIO_RUBRIC,
            "signposts": SIGNPOST_RUBRIC,
        },
        "requiredJudgeIds": {
            "scenarioSet": list(SCENARIO_JUDGE_IDS),
            "signposts": list(SIGNPOST_JUDGE_IDS),
        },
        "outputSchema": AgentJudgeOutput.model_json_schema(),
        "targets": [
            {
                "miEventId": run.mi_event_id,
                "scenarioGroupId": run.scenario_group_id,
                "deterministicChecks": deterministic_checks.get(run.mi_event_id, []),
                "evidence": {
                    "eventDetail": run.event_detail,
                    "step1ScenarioTable": run.step1,
                    "step2ValidationTable": run.step2,
                    "step3SignpostTable": run.step3,
                },
            }
            for run in runs
        ],
    }


def load_agent_judge_output(
    path: Path,
    *,
    batch_id: str,
    expected_event_ids: list[int],
    stability_runs: int,
) -> tuple[dict[int, list[JudgeResult]], list[bool]]:
    """Load and strictly validate an agent-produced judge result."""
    output = AgentJudgeOutput.model_validate_json(path.read_text(encoding="utf-8"))
    if output.batch_id != batch_id:
        msg = f"Agent judge batch mismatch: expected={batch_id}, actual={output.batch_id}"
        raise ValueError(msg)

    actual_event_ids = [evaluation.mi_event_id for evaluation in output.evaluations]
    if set(actual_event_ids) != set(expected_event_ids) or len(actual_event_ids) != len(set(actual_event_ids)):
        msg = f"Agent judge Event set mismatch: expected={sorted(expected_event_ids)}, actual={actual_event_ids}"
        raise ValueError(msg)

    primary_results: dict[int, list[JudgeResult]] = {}
    stability_agreements: list[bool] = []
    for evaluation in output.evaluations:
        if len(evaluation.passes) != stability_runs:
            msg = (
                f"miEventId={evaluation.mi_event_id}: expected {stability_runs} judge passes, "
                f"actual={len(evaluation.passes)}"
            )
            raise ValueError(msg)
        for judge_pass in evaluation.passes:
            _validate_result(judge_pass.scenario_set, SCENARIO_JUDGE_IDS)
            _validate_result(judge_pass.signposts, SIGNPOST_JUDGE_IDS)

        first_pass = evaluation.passes[0]
        primary_results[evaluation.mi_event_id] = [first_pass.scenario_set, first_pass.signposts]
        if stability_runs == 2:
            first_verdicts = _verdicts(first_pass)
            repeated_verdicts = _verdicts(evaluation.passes[1])
            stability_agreements.extend(
                first_verdicts[judge_id] == repeated_verdicts[judge_id] for judge_id in first_verdicts
            )
    return primary_results, stability_agreements


def write_agent_judge_input(path: Path, payload: dict[str, Any]) -> None:
    """Persist an agent judge request deterministically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _validate_result(result: JudgeResult, required_ids: tuple[str, ...]) -> None:
    if result.prompt_version != PROMPT_VERSION:
        msg = f"Agent judge prompt version mismatch: expected={PROMPT_VERSION}, actual={result.prompt_version}"
        raise ValueError(msg)
    actual_ids = [item.judge_id for item in result.items]
    if set(actual_ids) != set(required_ids) or len(actual_ids) != len(set(actual_ids)):
        msg = f"Agent judge rubric mismatch: expected={list(required_ids)}, actual={actual_ids}"
        raise ValueError(msg)


def _verdicts(judge_pass: AgentJudgePass) -> dict[str, str]:
    return {
        item.judge_id: item.verdict
        for result in (judge_pass.scenario_set, judge_pass.signposts)
        for item in result.items
    }
