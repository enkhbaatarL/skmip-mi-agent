from __future__ import annotations

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupPayload,
    ScenarioTable,
)
from apps.common.values.response import CommonResponse


class ValidateScenariosIn(ApiModel):
    user_id: int
    scenario_group: ScenarioGroupPayload
    table: ScenarioTable


class ValidateScenariosData(ApiModel):
    scenario_group_id: int
    is_valid: bool = False
    reason: str = ""
    status: str
    stage: str


class ValidateScenariosOut(CommonResponse):
    data: ValidateScenariosData | None = None
