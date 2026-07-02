from __future__ import annotations

from apps.agents.scenario_group_agent.schemas.api.table import ScenarioTable
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.state import ConfirmScenarioGroupState
from apps.common.values.response import CommonResponse


class ConfirmScenarioGroupIn(ConfirmScenarioGroupState):
    # API DTO 이름은 OpenAPI 계약으로 유지하고, 필드는 graph state 계약을 재사용한다.
    pass


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
