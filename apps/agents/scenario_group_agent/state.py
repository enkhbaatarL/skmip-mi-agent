from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from apps.agents.scenario_group_agent.schemas.api.table import SignpostBasePayload
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import (
    ScenarioGenerationResult,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import (
    SignpostGenerationResult,
)
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import (
    NewScenarioGeneratedDetails,
    ScenarioPayload,
    ScenarioTemplateDimension,
)
from apps.persistence.scenario_group.schema import (
    ScenarioGroupPayload,
)
from apps.persistence.signpost.schema import (
    SignpostPayload,
)


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


def state_update(**values: object) -> dict[str, object]:
    """Validate node output through ScenarioDesignState before returning a partial update.

    Node outputs should use this helper for non-trivial state updates so field
    validation runs and only explicitly provided fields are merged into LangGraph
    state.
    """
    return ScenarioDesignState(**values).model_dump(
        exclude_none=True,
        exclude_unset=True,
    )


class ScenarioDesignState(BaseModel):
    mi_event_id: int | None = None
    scenario_group_id: int | None = None
    user_id: int | None = None
    include_details: bool = False

    event_data: EventPayload | None = None
    scenario_group: ScenarioGroupPayload | None = None
    scenarios: list[ScenarioPayload] = Field(default_factory=list)
    dimension_template: list[ScenarioTemplateDimension] = Field(default_factory=list)
    signposts: list[SignpostPayload] = Field(default_factory=list)

    scenario_result: ScenarioGenerationResult | None = None
    validation_result: ScenarioValidationResult | None = None
    signpost_result: SignpostGenerationResult | None = None
    request_scenario_group: ConfirmScenarioGroupState | None = None
    request_table: ScenarioTableState | None = None

    saved_scenario_ids: Annotated[list[int], extend_unique_ints] = Field(default_factory=list)
    saved_signpost_ids: Annotated[list[int], extend_unique_ints] = Field(default_factory=list)
    signpost_target_scenario_ids: list[int] = Field(default_factory=list)
    new_scenario_row_details: list[NewScenarioGeneratedDetails] = Field(default_factory=list)
    snapshot_id: int | None = None

    is_valid: bool = False
    reason: str = ""
    confirmed: bool = False

    status: str = "success"
    message: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None
