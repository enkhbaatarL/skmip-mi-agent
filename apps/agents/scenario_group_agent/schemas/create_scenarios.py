from __future__ import annotations

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupPayload,
    ScenarioTable,
)
from apps.common.values.response import CallBackBody


class CreateScenariosIn(ApiModel):
    mi_event_id: int = Field(description="MI Event ID to generate a scenario group for")
    user_id: int


class CreateScenariosOut(CallBackBody):
    scenario_group: ScenarioGroupPayload | None = None
    table: ScenarioTable | None = None
