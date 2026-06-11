from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ScenarioDesignState(BaseModel):
    mi_event_id: int | None = None
    scenario_group_id: int | None = None
    user_id: int | None = None
    include_details: bool = False

    event_data: dict[str, Any] | None = None
    scenario_group: dict[str, Any] | None = None
    scenarios: list[dict[str, Any]] = Field(default_factory=list)
    dimension_template: list[dict[str, Any]] = Field(default_factory=list)
    signposts: list[dict[str, Any]] = Field(default_factory=list)

    scenario_result: dict[str, Any] | None = None
    validation_result: dict[str, Any] | None = None
    signpost_result: dict[str, Any] | None = None
    request_scenario_group: dict[str, Any] | None = None
    request_table: dict[str, Any] | None = None

    saved_scenario_ids: list[int] = Field(default_factory=list)
    saved_signpost_ids: list[int] = Field(default_factory=list)
    snapshot_id: int | None = None

    is_valid: bool = False
    reason: str = ""
    confirmed: bool = False

    status: str = "success"
    message: str = ""
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str | None = None
