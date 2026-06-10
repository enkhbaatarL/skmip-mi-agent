from __future__ import annotations

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupTableData,
)
from apps.common.values.response import CommonResponse


class CreateScenariosIn(ApiModel):
    mi_event_id: int = Field(description="MI Event ID to generate a scenario group for")
    user_id: str


class CreateScenariosOut(CommonResponse):
    data: ScenarioGroupTableData | None = None
