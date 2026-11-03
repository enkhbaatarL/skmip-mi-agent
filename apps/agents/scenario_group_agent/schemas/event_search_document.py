from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EventSearchMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(gt=0)
    event_type_l2_id: int | None
    source_table: Literal["tmm_mi_mievent_m"] = "tmm_mi_mievent_m"
    document_version: str
    source_hash: str
    text_hash: str
    title: str
    tags: list[str]
    occurred_at: datetime | None
    source_created_at: datetime | None
    source_updated_at: datetime | None
    publish_status: Literal["PUBLISHED"] = "PUBLISHED"
    del_yn: Literal["N"] = "N"
    source_record_ids: list[int]
    chunk_index: int = Field(ge=0)
    chunk_count: int = Field(gt=0)
    content_start: int = Field(ge=0)
    content_end: int = Field(gt=0)
    max_content_chars: int = Field(ge=128)
    warnings: list[str]


class EventSearchDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    text: str = Field(min_length=1)  # Embedding input, including title context.
    content: str = Field(min_length=1)  # Exact slice of the normalized Event document.
    metadata: EventSearchMetadata
