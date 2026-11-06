from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, JsonValue, field_validator

from apps.agents.scenario_group_agent.schemas.api.event_verifications import EventVerificationItem
from apps.agents.scenario_group_agent.schemas.base import ApiModel


class EventVerificationUpdateIn(ApiModel):
    model_config = ConfigDict(extra="forbid")
    actor_usr_logn_id: str = Field(strict=True, min_length=1, max_length=100)
    expected_updated_at: datetime | None = None

    @field_validator("actor_usr_logn_id")
    @classmethod
    def nonempty_actor(cls, value: str) -> str:
        if not value.strip():
            message = "actorUsrLognId는 공백일 수 없습니다."
            raise ValueError(message)
        return value.strip()


class EventContentChange(ApiModel):
    field: str
    before: JsonValue
    after: JsonValue
    reason: str
    source_urls: list[str]


class EventVerificationUpdateOut(ApiModel):
    mi_event_id: int
    checked_at: datetime
    update_status: Literal["updated", "unchanged", "skipped"]
    message: str
    verification: EventVerificationItem
    post_verification: EventVerificationItem | None = None
    mi_event_snapshot_id: int | None = None
    snapshot_version_no: int | None = None
    previous_mi_event_snapshot_id: int | None = None
    updated_at: datetime | None = None
    changed_fields: list[str] = Field(default_factory=list)
    changes: list[EventContentChange] = Field(default_factory=list)
