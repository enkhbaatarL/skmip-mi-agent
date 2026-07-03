from __future__ import annotations

from pydantic import Field

from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.schema_base import ApiModel


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

    @classmethod
    def from_model(cls, model: MiScenarioGroupModel) -> ScenarioGroupPayload:
        return cls.model_validate(
            {
                "scenario_group_id": model.scenario_group_id,
                "mi_event_id": model.mi_event_id,
                "event_type_l2_id": model.event_type_l2_id,
                "request_usr_id": model.request_usr_id,
                "title": model.title,
                "summary": model.summary,
                "description": model.description,
                "dimension_selected": model.dimension_selected or [],
                "scenario_count": model.scenario_count,
                "status": model.status,
                "stage": model.stage,
            }
        )
