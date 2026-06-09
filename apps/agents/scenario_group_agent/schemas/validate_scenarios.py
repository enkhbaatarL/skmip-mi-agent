from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.scenario_group_agent.schemas.common import BaseScenarioDesignOut


class ValidateScenariosIn(BaseModel):
    pass


class ValidateScenariosOut(BaseScenarioDesignOut):
    scenario_group_id: int
    is_valid: bool = False
    reason: str = ""
    validation_result: dict[str, Any] | None = None
