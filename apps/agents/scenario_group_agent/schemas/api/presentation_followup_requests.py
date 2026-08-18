from __future__ import annotations

# ruff: noqa: CPY001
from typing import Literal

from apps.agents.scenario_group_agent.flows.validate_scenarios.api_schema import ValidateScenariosIn
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.endpoint import CreateSignpostsIn


class PresentationFollowUpRequestBodiesOut(ApiModel):
    scenario_group_id: int
    operation_id: str | None = None
    scenario_table_status: Literal["pending", "partial", "ready", "unavailable"]
    ready: bool
    reason: str | None = None
    validation_request_body: ValidateScenariosIn | None = None
    signpost_request_body: CreateSignpostsIn | None = None
