from __future__ import annotations

from datetime import datetime

from apps.agents.scenario_group_agent.schemas.common import BaseScenarioDesignOut


class ConfirmGenerationOut(BaseScenarioDesignOut):
    scenario_group_id: int
    confirmed: bool = False
    confirmed_at: datetime | None = None
    snapshot_id: int | None = None
    scenario_count: int = 0
    signpost_count: int = 0
