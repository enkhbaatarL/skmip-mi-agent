from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import ConfigDict, Field

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.enums import ScenarioStatus


class ScenarioPayload(ApiModel):
    scenario_id: int
    scenario_group_id: int = 0
    display_order: int = 0
    title: str = ""
    description: str = ""
    narrative: str | None = None
    dimension_values: dict[str, Any] = Field(default_factory=dict)
    price_direction: dict[str, Any] = Field(default_factory=dict)
    probability_score: Decimal | None = None
    probability_delta: Decimal | None = Decimal("0.0")
    impact_jkm: str | None = None
    impact_ttf: str | None = None
    impact_hh: str | None = None
    baseline_yn: str | None = "N"
    status: str = ScenarioStatus.CREATING.value
    del_yn: str | None = None


class NewScenarioGeneratedDetails(ApiModel):
    model_config = ConfigDict(frozen=True)

    narrative: str
    probability_weight: Decimal
    probability_delta: Decimal
    impact_jkm: str | None
    impact_ttf: str | None
    impact_hh: str | None
