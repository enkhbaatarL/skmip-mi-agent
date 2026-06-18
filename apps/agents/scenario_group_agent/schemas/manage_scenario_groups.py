from __future__ import annotations

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupQueryPayload,
    ScenarioQueryTable,
)


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
