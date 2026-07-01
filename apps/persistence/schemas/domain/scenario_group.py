from __future__ import annotations

from pydantic import Field

from apps.persistence.schemas.base import ApiModel
from apps.persistence.schemas.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)


class ScenarioGroupPayload(ApiModel):
    scenario_group_id: int
    mi_event_id: int = 0
    event_type_l2_id: int = 0
    request_usr_id: int | None = None
    title: str = ""
    summary: str | None = None
    description: str | None = None
    dimension_selected: list[str] = Field(default_factory=list)
    scenario_count: int = 0
    status: str = ScenarioGroupStatus.CREATING.value
    stage: str = ScenarioGroupStage.READY.value
