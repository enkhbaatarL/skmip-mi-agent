from __future__ import annotations

from typing import Any

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.table import (
    ScenarioGroupQueryPayload,
    ScenarioQueryTable,
)
from apps.persistence.scenario_group_operation.schema import (
    ScenarioGroupOperationEventPayload,
    ScenarioGroupOperationPayload,
)


class ScenarioGroupOperationStatusOut(ApiModel):
    scenario_group_id: int
    operation: ScenarioGroupOperationPayload
    last_event: ScenarioGroupOperationEventPayload | None = None
    last_error: dict[str, Any] | None = None


class ScenarioGroupDetailOut(ApiModel):
    scenario_group: ScenarioGroupQueryPayload
    table: ScenarioQueryTable
    scenario_count: int = 0
    signpost_count: int = 0
    deleted_scenario_count: int = 0
    deleted_signpost_count: int = 0
    presentation_snapshot: dict[str, Any] = Field(default_factory=dict)
    active_operation: dict[str, Any] | None = None
    latest_operation: dict[str, Any] | None = None


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
