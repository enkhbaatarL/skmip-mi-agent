from __future__ import annotations

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupPayload,
    ScenarioTable,
)
from apps.common.values.response import CommonResponse


class ConfirmGenerationIn(ApiModel):
    scenario_group: ScenarioGroupPayload
    table: ScenarioTable


class ConfirmGenerationData(ApiModel):
    scenario_group_id: int
    status: str
    stage: str


class ConfirmGenerationOut(CommonResponse):
    data: ConfirmGenerationData | None = None
