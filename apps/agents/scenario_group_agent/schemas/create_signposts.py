from __future__ import annotations

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupPayload,
    ScenarioTable,
)
from apps.common.values.response import CallBackBody


class CreateSignpostsIn(ApiModel):
    user_id: int | None = None
    table: ScenarioTable


class CreateSignpostsOut(CallBackBody):
    scenario_group: ScenarioGroupPayload | None = None
    table: ScenarioTable | None = None
