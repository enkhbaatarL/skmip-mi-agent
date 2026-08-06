from __future__ import annotations

# ruff: noqa: CPY001
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


ApiVersion = Literal["v2", "v3", "v4"]
QualityStatus = Literal["PASS", "WARN", "FAIL"]
PairwiseWinner = Literal["v2", "v3", "v4", "tie"]


class ComparisonModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class QualityCheck(ComparisonModel):
    check_id: str
    status: QualityStatus
    detail: str
    offenders: list[str] = Field(default_factory=list)


class CriterionJudgment(ComparisonModel):
    criterion: Literal[
        "event_consistency",
        "lng_dimension_quality",
        "floor_ceiling_quality",
        "mixed_quality",
    ]
    score: int = Field(ge=1, le=5)
    verdict: QualityStatus
    evidence: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class ScenarioJudgment(ComparisonModel):
    scenario_id: str
    title: str
    global_pressure_band: str
    verdict: QualityStatus
    evidence: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1)


class VersionJudgment(ComparisonModel):
    api_version: ApiVersion
    criteria: list[CriterionJudgment]
    scenario_judgments: list[ScenarioJudgment]
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class PairwiseCriterionJudgment(ComparisonModel):
    criterion: Literal[
        "event_grounding",
        "dimension_and_value_quality",
        "scenario_logic_and_explainability",
        "baseline_and_exclusion_quality",
        "user_comprehensibility",
    ]
    winner: PairwiseWinner
    evidence: list[str] = Field(min_length=1)
    counterargument: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


class PairwiseJudgment(ComparisonModel):
    left_version: ApiVersion
    right_version: ApiVersion
    criteria: list[PairwiseCriterionJudgment]
    overall_winner: PairwiseWinner
    summary: str = Field(min_length=1)


class VersionRecommendation(ComparisonModel):
    versions: list[ApiVersion] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    tradeoffs: list[str] = Field(default_factory=list)
    selection_condition: str = Field(min_length=1)


class ComparisonJudgment(ComparisonModel):
    versions: list[VersionJudgment]
    pairwise_comparisons: list[PairwiseJudgment]
    best_versions: list[ApiVersion] = Field(min_length=1)
    quality_recommendation: VersionRecommendation
    practical_recommendation: VersionRecommendation
    conclusion: str = Field(min_length=1)


JsonObject = dict[str, Any]
