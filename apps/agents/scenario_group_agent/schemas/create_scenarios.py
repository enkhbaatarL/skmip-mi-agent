from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.common.values.response import CommonResponse


class CreateScenariosIn(BaseModel):
    mi_event_id: int = Field(description="MI Event ID to generate a scenario group for")


class CreateScenariosData(BaseModel):
    mi_event_id: int
    scenario_group_id: int | None = None
    scenario_count: int = 0
    saved_scenario_ids: list[int] = Field(default_factory=list)
    scenario_result: dict[str, Any] | None = None


class CreateScenariosOut(CommonResponse):
    data: CreateScenariosData | None = None
