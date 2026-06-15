from __future__ import annotations

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioTable,
)
from apps.common.values.response import CallBackBody


class ValidateScenariosIn(ApiModel):
    user_id: int
    table: ScenarioTable


class ValidateScenariosCallBackScenarioGroup(ApiModel):
    scenario_group_id: int
    status: str
    stage: str


class ValidateScenariosOut(CallBackBody):
    is_valid: bool | None = None
    scenario_group: ValidateScenariosCallBackScenarioGroup | None = None
    table: ScenarioTable | None = None
