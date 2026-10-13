"""flow 간 공유하는 이벤트 API schema.

특정 flow 전용 request/response 는 각 flow의 api_schema.py 에 두고,
여기에는 여러 레이어(flow / persistence)가 함께 참조하는 shape만 둔다.
"""

from __future__ import annotations

from pydantic import Field

from apps.agents.event_generate_agent.schemas.base import ApiModel


class GeneratedEventOut(ApiModel):
    """생성된 이벤트 초안 1건."""

    one_line_summary: str = ""
    detail_analysis: str = ""
    key_bullets: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    occurred_at: str = ""
    event_type_l2_id: int | None = None


class ConfirmedEventOut(ApiModel):
    """DB에 저장된 이벤트 1건."""

    mi_event_id: int
    event_type_l2_id: int | None = None
