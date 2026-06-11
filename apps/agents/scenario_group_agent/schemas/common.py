from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ScenarioGroupPayload(ApiModel):
    scenario_group_id: int
    mi_event_id: int
    event_type_l2_id: int
    request_usr_id: int | None = None
    title: str
    summary: str | None = None
    description: str | None = None
    dimension_selected: list[str] = Field(default_factory=list)
    scenario_count: int = 0
    status: str = "creating"
    stage: str = "ready"


class ScenarioHeader(ApiModel):
    key: str
    label: str
    display_order: int


class ScenarioMetrics(ApiModel):
    probability_score: Decimal | None = None
    probability_delta: Decimal | None = None


class ScenarioImpact(ApiModel):
    jkm: str | None = None
    ttf: str | None = None
    hh: str | None = None


class SignpostPayload(ApiModel):
    signpost_id: int
    label: str
    probability_direction_code: str | None = None
    probability_impact_score: Decimal | None = None
    signpost_reason: str | None = None
    display_order: int = 0


class ScenarioRow(ApiModel):
    scenario_id: int
    display_order: int = 0
    title: str = ""
    narrative: str | None = None
    cells: dict[str, Any] = Field(default_factory=dict)
    metrics: ScenarioMetrics | None = None
    impact: ScenarioImpact | None = None
    baseline_yn: str | None = None
    signposts: list[SignpostPayload] = Field(default_factory=list)


class ScenarioTable(ApiModel):
    headers: list[ScenarioHeader]
    rows: list[ScenarioRow]


class ScenarioGroupTableData(ApiModel):
    scenario_group: ScenarioGroupPayload
    table: ScenarioTable
