from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.state import ConfirmScenarioGroupState
from apps.agents.scenario_group_agent.schemas.table import (
    ScenarioGroupQueryPayload,
    ScenarioHeader,
    ScenarioQueryTable,
    ScenarioTable,
)
from apps.common.values.response import CallBackBody, CommonResponse
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


class ScenarioGroupAcceptedData(ApiModel):
    scenario_group_id: int
    status: str
    stage: str


class ScenarioGroupAcceptedOut(BaseModel):
    status: str = "success"
    message: str = "성공"
    data: ScenarioGroupAcceptedData


class CreateScenariosIn(ApiModel):
    mi_event_id: int = Field(description="MI Event ID to generate a scenario group for")
    user_id: int


class CreateScenariosOut(CallBackBody):
    scenario_group: ScenarioGroupPayload | None = None
    table: ScenarioTable | None = None


class ValidateScenariosHeaderIn(ScenarioHeader):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )


class ValidateScenariosRowIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    cells: dict[str, Any] = Field(default_factory=dict)


class ValidateScenariosTableIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    headers: list[ValidateScenariosHeaderIn]
    rows: list[ValidateScenariosRowIn]


class ValidateScenariosIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    user_id: int
    table: ValidateScenariosTableIn


class ValidateScenariosCallBackScenarioGroup(ApiModel):
    scenario_group_id: int
    status: str
    stage: str


class ValidateScenariosOut(CallBackBody):
    is_valid: bool | None = None
    scenario_group: ValidateScenariosCallBackScenarioGroup | None = None
    table: ScenarioTable | None = None


class CreateSignpostsHeaderIn(ScenarioHeader):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )


class CreateSignpostsRowIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    cells: dict[str, Any] = Field(default_factory=dict)


class CreateSignpostsTableIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    headers: list[CreateSignpostsHeaderIn]
    rows: list[CreateSignpostsRowIn]


class CreateSignpostsIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    user_id: int
    table: CreateSignpostsTableIn


class CreateSignpostsOut(CallBackBody):
    scenario_group: ScenarioGroupPayload | None = None
    table: ScenarioTable | None = None


class ConfirmScenarioGroupIn(ConfirmScenarioGroupState):
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


class ScenarioGroupDetailOut(ApiModel):
    scenario_group: ScenarioGroupQueryPayload
    table: ScenarioQueryTable
    scenario_count: int = 0
    signpost_count: int = 0
    deleted_scenario_count: int = 0
    deleted_signpost_count: int = 0


class SoftDeleteScenarioGroupIn(ApiModel):
    user_id: int


class SoftDeleteScenarioGroupOut(ApiModel):
    scenario_group_deleted: int = 0
    scenario_deleted: int = 0
    signpost_deleted: int = 0


class SoftDeleteSignpostsIn(ApiModel):
    user_id: int


class SoftDeleteSignpostsOut(ApiModel):
    signpost_deleted: int = 0


class HardDeleteScenarioGroupIn(ApiModel):
    user_id: int
    confirm: bool = False


class HardDeleteScenarioGroupOut(ApiModel):
    tmm_mi_signpost_snap_m: int = Field(default=0, alias="tmm_mi_signpost_snap_m")
    tmm_mi_scenario_snap_m: int = Field(default=0, alias="tmm_mi_scenario_snap_m")
    tmm_mi_snapshot_m: int = Field(default=0, alias="tmm_mi_snapshot_m")
    tmm_mi_signpost_m: int = Field(default=0, alias="tmm_mi_signpost_m")
    tmm_mi_scenario_m: int = Field(default=0, alias="tmm_mi_scenario_m")
    tmm_mi_scenario_group_m: int = Field(default=0, alias="tmm_mi_scenario_group_m")
