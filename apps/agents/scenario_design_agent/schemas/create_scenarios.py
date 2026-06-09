from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.scenario_design_agent.schemas.common import BaseScenarioDesignOut


class CreateScenariosIn(BaseModel):
    mi_event_id: int = Field(description="MI Event ID to generate a scenario group for")


class CreateScenariosOut(BaseScenarioDesignOut):
    mi_event_id: int
    scenario_group_id: int | None = None
    scenario_count: int = 0
    saved_scenario_ids: list[int] = Field(default_factory=list)
    scenario_result: dict[str, Any] | None = None
