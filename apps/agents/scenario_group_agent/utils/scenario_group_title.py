from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

# ruff: noqa: CPY001
from apps.persistence.event.schema import EventPayload


_EVENT_LABEL_PATTERN = re.compile(r"^\s*\[([^\]]+)\]")
_TOKEN_SEPARATOR_PATTERN = re.compile(r"[\s·,/()\[\]\-→~|:]+")
_MIN_TOKEN_LENGTH = 2
FALLBACK_GROUP_TITLE_MAX_LENGTH = 120
_FALLBACK_LABEL_SEPARATOR = ", "
_FALLBACK_TITLE_SUFFIX = "에 따른 JKM 시나리오"
# 여러 이벤트에 공통으로 쓰여 이벤트를 구분하지 못하는 시장·방향 일반어
_GENERIC_TOKENS = frozenset(
    {
        "가스",
        "천연가스",
        "lng",
        "공급",
        "수요",
        "가격",
        "시장",
        "전망",
        "가능성",
        "증가",
        "감소",
        "확대",
        "축소",
        "상승",
        "하락",
        "지속",
        "완화",
        "둔화",
        "강세",
        "약세",
        "우려",
        "영향",
    }
)


@dataclass(frozen=True)
class GroupTitleMissingEvent:
    event_index: int
    mi_event_id: int | str
    label: str
    expected_tokens: tuple[str, ...]


def _event_label(event: EventPayload) -> str:
    match = _EVENT_LABEL_PATTERN.match(event.one_line_summary)
    if match:
        return match.group(1).strip()
    return event.event_title_ko.strip()


def _event_tokens(event: EventPayload) -> set[str]:
    sources = [event.event_title_ko]
    match = _EVENT_LABEL_PATTERN.match(event.one_line_summary)
    if match:
        sources.append(match.group(1))
    tokens: set[str] = set()
    for source in sources:
        for token in _TOKEN_SEPARATOR_PATTERN.split(source.lower()):
            if len(token) >= _MIN_TOKEN_LENGTH and token not in _GENERIC_TOKENS:
                tokens.add(token)
    return tokens


def find_events_missing_from_group_title(
    title: str,
    events: Sequence[EventPayload],
) -> list[GroupTitleMissingEvent]:
    """Return events none of whose label/title tokens appear in the group title.

    비슷한 주제의 이벤트가 함께 선택되면 공통 단어(예: 호르무즈)로 묶어 쓴 제목도 반영으로 인정한다.
    일반어를 빼고 남는 토큰이 없는 이벤트는 판정 근거가 없으므로 검사하지 않는다.
    """
    normalized_title = title.lower()
    missing: list[GroupTitleMissingEvent] = []
    for index, event in enumerate(events, start=1):
        tokens = sorted(_event_tokens(event))
        if not tokens or any(token in normalized_title for token in tokens):
            continue
        missing.append(
            GroupTitleMissingEvent(
                event_index=index,
                mi_event_id=event.mi_event_id,
                label=_event_label(event),
                expected_tokens=tuple(tokens),
            )
        )
    return missing


def format_group_title_missing_events(missing: Sequence[GroupTitleMissingEvent]) -> str:
    details = "; ".join(
        f"[이벤트 {item.event_index}] {item.label} (다음 중 하나 포함: {', '.join(item.expected_tokens)})"
        for item in missing
    )
    return (
        "title에 핵심 질문의 출처 이벤트 대상이 드러나야 합니다. 이벤트를 지역명으로 합치지 말고 "
        f"원문 표현으로 반영하십시오. 누락: {details}"
    )


def build_fallback_group_title(events: Sequence[EventPayload]) -> str:
    """Deterministic group title from event labels, used when LLM titles keep dropping events."""
    labels = list(dict.fromkeys(_event_label(event) or f"이벤트 {event.mi_event_id}" for event in events))
    body_limit = FALLBACK_GROUP_TITLE_MAX_LENGTH - len(_FALLBACK_TITLE_SUFFIX)
    body = _FALLBACK_LABEL_SEPARATOR.join(labels)
    if len(body) > body_limit:
        body = body[: body_limit - 1].rstrip(" ,") + "…"
    return f"{body}{_FALLBACK_TITLE_SUFFIX}"
