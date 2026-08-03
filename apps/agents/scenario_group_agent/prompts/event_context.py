from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import date
from typing import Any

from pydantic import BaseModel, Field


MAX_KEY_FACTS = 5
MAX_KEY_FACT_LENGTH = 280
MAX_TAGS = 8


class CompactEventContext(BaseModel):
    event_id: str = ""
    title: str = ""
    summary: str = ""
    occurred_at: str = ""
    key_facts: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)

    @classmethod
    def from_event(cls, event: Mapping[str, Any]) -> CompactEventContext:
        return cls(
            event_id=_text(event.get("event_id") or event.get("mi_event_id")),
            title=_text(event.get("title") or event.get("event_title_ko")),
            summary=_text(event.get("summary") or event.get("one_line_summary")),
            occurred_at=_text(event.get("occurred_at")),
            key_facts=[
                fact[:MAX_KEY_FACT_LENGTH]
                for item in event.get("key_facts") or event.get("key_bullets") or []
                if (fact := _text(item))
            ][:MAX_KEY_FACTS],
            tags=[tag for item in event.get("tags") or [] if (tag := _text(item))][:MAX_TAGS],
        )


def format_compact_event_context(
    events: Sequence[CompactEventContext | Mapping[str, Any]],
    *,
    as_of: date | None = None,
) -> str:
    compact_events = [
        event if isinstance(event, CompactEventContext) else CompactEventContext.from_event(event) for event in events
    ]
    context_date = as_of or date.today()  # noqa: DTZ011
    blocks = [
        f"current_date: {context_date:%Y-%m-%d}",
        (
            "temporal_reference: 최근 N일/개월, 계절 및 과거·현재·미래 판단은 "
            "current_date를 기준으로 하고, occurred_at은 Event 발생 시점으로 구분할 것."
        ),
    ]
    blocks.extend(_format_event_block(event, index=index) for index, event in enumerate(compact_events, start=1))
    return "\n\n".join(blocks)


def _format_event_block(event: CompactEventContext, *, index: int) -> str:
    event_label = event.event_id or str(index)
    facts = "\n".join(f"- {fact}" for fact in event.key_facts) or "- (없음)"
    tags = ", ".join(event.tags) or "(없음)"
    return (
        f"[Event {event_label}]\n"
        f"event_id: {event.event_id or '(없음)'}\n"
        f"title: {event.title or '(없음)'}\n"
        f"summary: {event.summary or '(없음)'}\n"
        f"occurred_at: {event.occurred_at or '(없음)'}\n"
        f"key_facts:\n{facts}\n"
        f"tags: {tags}"
    )


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


__all__ = [
    "MAX_KEY_FACTS",
    "MAX_KEY_FACT_LENGTH",
    "MAX_TAGS",
    "CompactEventContext",
    "format_compact_event_context",
]
