from __future__ import annotations

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupTableData,
)
from apps.common.values.response import CommonResponse


class CreateSignpostsIn(ApiModel):
    user_id: int | None = None


class CreateSignpostsOut(CommonResponse):
    data: ScenarioGroupTableData | None = None
