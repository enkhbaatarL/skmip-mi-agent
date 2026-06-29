from __future__ import annotations

from apps.agents.scenario_group_agent.schemas.api.table import ScenarioTable
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.common.values.response import CommonResponse


class ConfirmScenarioGroupIn(ApiModel):
    title: str
    summary: str | None = None
    description: str | None = None


class ConfirmGenerationIn(ApiModel):
    user_id: int | None = None
    scenario_group: ConfirmScenarioGroupIn
    table: ScenarioTable


class ConfirmGenerationData(ApiModel):
    scenario_group_id: int
    status: str
    stage: str


class ConfirmGenerationOut(CommonResponse):
    data: ConfirmGenerationData | None = None
