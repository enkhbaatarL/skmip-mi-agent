from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from apps.persistence.schema_base import ApiModel


OperationType = Literal["create", "validation", "signpost", "confirmation"]
OperationStatus = Literal["queued", "running", "succeeded", "failed", "interrupted"]
TERMINAL_OPERATION_STATUSES = frozenset({"succeeded", "failed", "interrupted"})
TERMINAL_EVENT_TYPES = frozenset({"completed", "failed", "interrupted"})


class ScenarioGroupOperationPayload(ApiModel):
    operation_id: str
    scenario_group_id: int
    operation_type: OperationType
    engine_version: str
    source: str = "api"
    status: OperationStatus
    current_phase: str | None = None
    retry_summary: dict[str, Any] = Field(default_factory=dict)
    presentation_snapshot: dict[str, Any] = Field(default_factory=dict)
    snapshot_revision: int = 0
    latest_sequence: int = 0
    last_error: dict[str, Any] | None = None
    mlflow_trace_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    heartbeat_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScenarioGroupOperationEventPayload(ApiModel):
    operation_id: str
    scenario_group_id: int
    sequence: int
    event_type: str
    phase: str | None = None
    title: str
    message_markdown: str
    payload: dict[str, Any] = Field(default_factory=dict)
    snapshot_revision: int = 0
    mlflow_trace_id: str | None = None
    created_at: datetime | None = None

