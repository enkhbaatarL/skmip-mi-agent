# apps/agents/event_flow_agent/schemas/mi_event_models.py

from __future__ import annotations
from typing import Annotated, List
from pydantic import BaseModel, Field

class EventTypeRef(BaseModel):
    level_1: str
    level_2: str

KeyBullets = Annotated[list[str], Field(min_length=3, max_length=5)]
EvidenceRecordIds = Annotated[list[int], Field(min_length=1)]

class MIEvent(BaseModel):
    event_title_ko: str = Field(default="")
    one_line_summary: str = Field(default="")
    key_bullets: KeyBullets = Field(default_factory=list)
    detail_analysis: str = Field(default="")
    market_and_institution_view: str = Field(default="")
    event_type: EventTypeRef
    evidence_record_ids: EvidenceRecordIds = Field(default_factory=list)
    occurred_at: str = Field(default="")
    tags: List[str] = Field(default_factory=list)

Events = Annotated[list[MIEvent], Field(min_length=1)]

class MIEventList(BaseModel):
    events: Events = Field(default_factory=list)