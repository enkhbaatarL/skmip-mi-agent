from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import ApiModel


class EventImpactFact(ApiModel):
    event_id: int
    lever_code: str
    domain: str
    change_direction: Literal["increase", "decrease"]
    target_market_direction: Literal["bullish", "bearish"]
    timing: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class InteractionDefinition(ApiModel):
    event_ids: list[int] = Field(min_length=2)
    relation: Literal["amplification", "offset"]
    rationale: str = ""


class DimensionValueDefinition(ApiModel):
    value_id: str
    label: str


class DimensionDefinition(ApiModel):
    dimension_id: str
    label: str
    required: bool
    source_event_ids: list[int] = Field(min_length=1)
    lever_refs: list[str] = Field(min_length=1)
    values: list[DimensionValueDefinition] = Field(min_length=1)


class ScenarioDefinition(ApiModel):
    title: str
    narrative: str
    dimension_values: dict[str, str]
    target_market_pressure_band: str
    probability_score: float = Field(ge=0, le=100)
    mixed_factors: list[str] = Field(default_factory=list)


class ScenarioDocument(ApiModel):
    group_title: str
    event_impact_facts: list[EventImpactFact] = Field(min_length=1)
    interactions: list[InteractionDefinition] = Field(default_factory=list)
    dimension_definitions: list[DimensionDefinition] = Field(min_length=1)
    scenarios: list[ScenarioDefinition] = Field(min_length=1)


class RunMetadata(ApiModel):
    mi_event_ids: list[int] = Field(min_length=1)
    target_market: str = Field(min_length=1, max_length=64)
    comparison_run_id: str | None = Field(default=None, max_length=128)

    @field_validator("mi_event_ids")
    @classmethod
    def unique_event_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            raise ValueError("miEventIds에는 중복 Event ID를 사용할 수 없습니다.")
        return value


class PlanRequest(ApiModel):
    metadata: RunMetadata
    scenario_json: dict[str, Any]


class ClarificationAnswer(ApiModel):
    question_id: str
    choice_id: str | None = None
    text: str | None = None

    @model_validator(mode="after")
    def require_value(self) -> ClarificationAnswer:
        if not self.choice_id and not (self.text and self.text.strip()):
            raise ValueError("choiceId 또는 text가 필요합니다.")
        return self


class RunRequest(PlanRequest):
    clarification_answers: dict[str, Any] = Field(default_factory=dict)


class FinalFeedbackRequest(ApiModel):
    scope: Literal["parameter", "scenario", "run"]
    scenario_key: str | None = None
    parameter_code: str | None = None
    text: str = Field(min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def validate_scope(self) -> FinalFeedbackRequest:
        if self.scope == "parameter" and (not self.parameter_code or not self.scenario_key):
            raise ValueError("parameter scope에는 scenarioKey와 parameterCode가 필요합니다.")
        if self.scope == "scenario" and not self.scenario_key:
            raise ValueError("scenario scope에는 scenarioKey가 필요합니다.")
        return self


class ReviewRequest(ApiModel):
    reviewer_note: str | None = Field(default=None, max_length=2_000)
