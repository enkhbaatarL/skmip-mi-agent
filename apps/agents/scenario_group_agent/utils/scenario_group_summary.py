from __future__ import annotations

from collections.abc import Sequence

# ruff: noqa: CPY001
from apps.persistence.event.schema import EventPayload


EVENT_SUMMARY_PREVIEW_LENGTH = 40
EVENT_SUMMARY_SEPARATOR = " | "


def _normalize_preview_text(value: str) -> str:
    return " ".join(value.split())


def build_scenario_group_event_summary(events: Sequence[EventPayload]) -> str:
    """Combine ordered Event previews into the v4 Scenario Group summary."""
    previews: list[str] = []
    for event in events:
        text = _normalize_preview_text(event.one_line_summary)
        if not text:
            text = _normalize_preview_text(event.event_title_ko)
        if not text:
            text = f"이벤트 {event.mi_event_id}"
        previews.append(text[:EVENT_SUMMARY_PREVIEW_LENGTH])
    return EVENT_SUMMARY_SEPARATOR.join(previews)
