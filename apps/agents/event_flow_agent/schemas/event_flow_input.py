#   agents/event_flow_agent/schemas/event_flow_input.py
#   kmj20260414화

from __future__ import annotations

from pydantic import BaseModel, Field

class EventFlowInput(BaseModel):
    limit: int = Field(
        default=20,
        description="RDB 조회 건수 제한",
    )