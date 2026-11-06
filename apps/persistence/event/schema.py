from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field, JsonValue

from apps.persistence.schema_base import ApiModel


class EventSearchSource(ApiModel):
    """Read-only search export DTO; column names retain their DB meaning."""

    mi_event_id: int = Field(gt=0)
    event_type_l2_id: int | None = None
    one_line_summary: str = ""  # DB title, unlike EventPayload.one_line_summary.
    search_text: str = ""
    key_bullets_json: JsonValue = None
    tags_json: JsonValue = None
    detail_analysis: str = ""
    numeric_facts_md: str | None = None
    institution_view_synthesis: str | None = None
    occurred_at: datetime | None = None
    crt_dtm: datetime | None = None
    mod_dtm: datetime | None = None
    publish_status: str | None = None
    del_yn: str
    source_record_ids: list[int] = Field(default_factory=list)


class EventPayload(ApiModel):
    mi_event_id: int | str
    event_type_l2_id: int | None = None
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


EventUpdateField = Literal[
    "one_line_summary",
    "search_text",
    "key_bullets_json",
    "detail_analysis",
    "numeric_facts_md",
    "institution_view_synthesis",
]


class EventUpdateContext(ApiModel):
    source: EventSearchSource
    fingerprint: str
    content: dict[str, JsonValue]


class EventUpdateApplied(ApiModel):
    mi_event_id: int
    snapshot_id: int | None
    snapshot_version_no: int | None
    previous_snapshot_id: int | None
    changed_fields: list[str]
    updated_at: datetime


class EventVerificationRecord(ApiModel):
    mi_event_verification_id: str
    mi_event_id: int
    event_fingerprint: str
    verification_result_json: dict[str, JsonValue]
    search_evidence_json: list[dict[str, JsonValue]]
    checked_at: datetime
    expires_at: datetime
    applied_mi_event_snapshot_id: int | None = None
