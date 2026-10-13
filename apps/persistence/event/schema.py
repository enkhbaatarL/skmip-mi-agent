from __future__ import annotations

from typing import Any

from pydantic import Field

from apps.persistence.schema_base import ApiModel


class EventPayload(ApiModel):
    mi_event_id: int | str
    event_type_l2_id: int
    event_title_ko: str = ""
    one_line_summary: str = ""
    detail_analysis: str = ""
    key_bullets: list[str] = Field(default_factory=list)
    event_type: dict[str, Any] = Field(default_factory=dict)
    source_mi_record_ids: list[int] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    language: str = "ko"
    occurred_at: str = ""
    latest_record_first_created: str = ""
    oldest_record_first_created: str = ""
    tags: list[str] = Field(default_factory=list)
