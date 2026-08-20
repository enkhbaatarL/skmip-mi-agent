from __future__ import annotations

# ruff: noqa: CPY001
from datetime import datetime
from typing import Literal

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.api.scenario_group_presentation import (
    PresentationDimensionDefinitions,
)
from apps.agents.scenario_group_agent.schemas.base import ApiModel


AdditionalDimensionGenerationStatus = Literal[
    "not_requested",
    "queued",
    "running",
    "ready",
    "failed",
    "interrupted",
    "discarded",
]


class AdditionalDimensionsData(ApiModel):
    scenario_group_id: int
    generation_status: AdditionalDimensionGenerationStatus
    dimension_definitions: PresentationDimensionDefinitions
    available_count: int = Field(ge=0)
    updated_at: datetime | None = None
    error_code: str | None = None


class AdditionalDimensionsOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "성공"
    data: AdditionalDimensionsData | None = None
