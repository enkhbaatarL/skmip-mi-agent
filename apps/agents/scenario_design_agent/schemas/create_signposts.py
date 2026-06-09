from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.scenario_design_agent.schemas.common import BaseScenarioDesignOut


class CreateSignpostsIn(BaseModel):
    pass


class CreateSignpostsOut(BaseScenarioDesignOut):
    scenario_group_id: int
    signpost_count: int = 0
    saved_signpost_ids: list[int] = Field(default_factory=list)
    signpost_result: dict[str, Any] | None = None
