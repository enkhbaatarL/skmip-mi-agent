"""
화면에 보여지는 Table을 구성하는 schema (DB Table 아님)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import Field, model_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.persistence.scenario.schema import RelatedMarket
from apps.persistence.scenario_group.schema import (
    ScenarioGroupPayload,
)


class SignpostBasePayload(ApiModel):
    signpost_id: int
    label: str
    probability_direction_code: str | None = None
    probability_impact_score: Decimal | None = None
    signpost_reason: str | None = None
    display_order: int = 0
    strength: str | None = None
    use_yn: str | None = None
    keyword_hints: list[str] = Field(default_factory=list)
    del_yn: str | None = None


class ScenarioHeader(ApiModel):
    key: str
    label: str
    display_order: int


class ScenarioMetrics(ApiModel):
    probability_score: Decimal | None = None
    probability_delta: Decimal | None = Field(default=Decimal("0.0"))

    @model_validator(mode="after")
    def _coerce_delta(self) -> ScenarioMetrics:
        if self.probability_delta is None:
            self.probability_delta = Decimal("0.0")
        return self


class ScenarioRow(ApiModel):
    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    narrative: str | None = None
    cells: dict[str, Any] = Field(default_factory=dict)
    metrics: ScenarioMetrics | None = None
    baseline_yn: str | None = None
    global_pressure_band: str | None = None
    scenario_role: str | None = None
    probability_score: Decimal | None = None
    global_pressure_rationale: str | None = None
    related_markets: list[RelatedMarket] = Field(default_factory=list)
    signposts: list[SignpostBasePayload] = Field(default_factory=list)


class ScenarioTable(ApiModel):
    headers: list[ScenarioHeader]
    rows: list[ScenarioRow]


class ScenarioGroupTableData(ApiModel):
    scenario_group: ScenarioGroupPayload
    table: ScenarioTable


class ScenarioGroupQueryPayload(ScenarioGroupPayload):
    del_yn: str = "N"


class SignpostQueryPayload(SignpostBasePayload):
    del_yn: str = "N"


class ScenarioQueryRow(ScenarioRow):
    del_yn: str = "N"
    signposts: list[SignpostQueryPayload] = Field(default_factory=list)


class ScenarioQueryTable(ApiModel):
    headers: list[ScenarioHeader]
    rows: list[ScenarioQueryRow]
