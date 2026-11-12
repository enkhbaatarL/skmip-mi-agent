from __future__ import annotations

# ruff: noqa: CPY001
from datetime import datetime
from typing import Literal

from pydantic import Field, JsonValue

from apps.agents.scenario_group_agent.schemas.base import ApiModel


class AgentExecutionEvent(ApiModel):
    """Observable decisions and execution evidence, never private model reasoning."""

    run_id: str
    parent_run_id: str | None = None
    sequence: int
    feature: str
    phase: str
    status: Literal["started", "completed", "failed", "interrupted", "skipped", "warning"]
    summary: str
    occurred_at: datetime
    elapsed_ms: int
    details: dict[str, JsonValue] = Field(default_factory=dict)
