from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.interpret_agent.schemas.base import ApiModel
from apps.common.values.response import CallBackBody


class ForecastPoint(ApiModel):
    month: str = Field(description="YYYY-MM")
    value: float = Field(description="월별 forecast 값(float)")


class InterpretationScenarioIn(ApiModel):
    scenario_id: int
    forecast: list[ForecastPoint] = Field(min_length=1)


class CreateInterpretationIn(ApiModel):
    scenario_group_id: int
    scenarios: list[InterpretationScenarioIn] = Field(min_length=1)


class InterpretationAcceptedData(ApiModel):
    job_id: str
    scenario_group_id: int
    status: str
    stage: str
    accepted_at: str


class InterpretationAcceptedOut(BaseModel):
    status: str = "success"
    message: str = "성공"
    data: InterpretationAcceptedData


class InterpretationJobStatusData(ApiModel):
    job_id: str
    scenario_group_id: int
    status: str
    stage: str
    updated_at: str
    error: dict[str, Any] | None = None


class InterpretationJobStatusOut(BaseModel):
    status: str = "success"
    message: str = "성공"
    data: InterpretationJobStatusData


class BaseEventOut(ApiModel):
    event_id: int
    title: str
    summary: str
    event_type: dict[str, str] = Field(default_factory=dict)
    key_drivers: list[str] = Field(default_factory=list)
    occurred_at: str | None = None


class DimensionDefinitionOut(ApiModel):
    dimension_id: str
    label: str
    rationale: str | None = None
    enum_used: list[str] = Field(default_factory=list)


class InterpretationScenarioOut(ApiModel):
    scenario_id: int | str
    title: str
    description: str | None = None
    dimension_values: dict[str, Any] = Field(default_factory=dict)
    pattern: dict[str, Any] = Field(default_factory=dict)
    causal_narrative: str | None = None
    likelihood_prior: str | None = None
    forecast: list[ForecastPoint] | None = None


class InterpretationMetaOut(ApiModel):
    scenario_group_id: int | str
    base_event_id: int | str
    interpretation_date: str
    indices: list[str] = Field(default_factory=list)
    unit: str


class InterpretationResultOut(ApiModel):
    meta: InterpretationMetaOut
    scenarios: list[InterpretationScenarioOut] = Field(default_factory=list)
    synthesis: dict[str, Any] = Field(default_factory=dict)
    # Backward compatibility for previous documentation drafts.
    base_event: BaseEventOut | None = None
    dimensions: list[DimensionDefinitionOut] = Field(default_factory=list)


class InterpretationCallbackData(ApiModel):
    job_id: str
    scenario_group_id: int
    interpretation: InterpretationResultOut


class InterpretationCallbackOut(CallBackBody):
    data: InterpretationCallbackData | None = None

