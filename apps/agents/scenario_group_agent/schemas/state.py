from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.table import SignpostBasePayload


class BaseFlowState(BaseModel):
    scenario_group_id: int | None = None
    user_id: int | None = None
    status: str = "success"
    message: str = ""
    error: str | None = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class ScenarioTableHeaderState(ApiModel):
    key: str
    label: str | None = None
    display_order: int = 0


class ScenarioMetricsState(ApiModel):
    probability_score: Decimal | None = None
    probability_delta: Decimal | None = Field(default=Decimal("0.0"))

    @model_validator(mode="after")
    def _coerce_delta(self) -> ScenarioMetricsState:
        if self.probability_delta is None:
            self.probability_delta = Decimal("0.0")
        return self


class ScenarioImpactState(ApiModel):
    jkm: str | None = None
    ttf: str | None = None
    hh: str | None = None


BaselineYn = Literal["Y", "N"]


class ScenarioTableRowState(ApiModel):
    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    narrative: str | None = None
    cells: dict[str, Any] = Field(default_factory=dict)
    metrics: ScenarioMetricsState | None = None
    impact: ScenarioImpactState | None = None
    baseline_yn: BaselineYn | None = None
    signposts: list[SignpostBasePayload] = Field(default_factory=list)


class ScenarioTableState(ApiModel):
    headers: list[ScenarioTableHeaderState]
    rows: list[ScenarioTableRowState]


class ConfirmScenarioGroupState(ApiModel):
    title: str
    summary: str | None = None
    description: str | None = None


ValidationCheckStatus = Literal["PASS", "WARN", "FAIL", "INFO"]
ValidationVerdict = Literal["PASS", "REVIEW", "BLOCK", ""]


class ScenarioValidationResult(ApiModel):
    scenario_group_id: int | None = None
    scenario_count: int = 0
    verdict: ValidationVerdict = ""
    summary: dict[ValidationCheckStatus, int] = Field(default_factory=dict)
    checks: list[dict[str, Any]] = Field(default_factory=list)


def extend_unique_ints(current: list[int], update: list[int] | None) -> list[int]:
    if not update:
        return current
    merged = list(current)
    seen = set(merged)
    for item in update:
        value = int(item)
        if value not in seen:
            merged.append(value)
            seen.add(value)
    return merged


def state_update(state_type: type[BaseModel], **values: object) -> dict[str, object]:
    return state_type(**values).model_dump(
        exclude_none=True,
        exclude_unset=True,
    )
