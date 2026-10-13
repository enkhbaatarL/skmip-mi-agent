"""기존 MI 이벤트 검색 툴.

MI MCP 서버(`mi-next-gen-mcp-server`)의 두 tool 을 이어서 호출한다.

1. `mi_events_list` — 키워드/기간으로 이벤트 목록을 조회해 eventId 를 얻는다.
2. `mi_event_detail` — 얻은 id 마다 상세(분석 본문, 영향도, 기관 종합)를 조회한다.

목록 응답에는 제목·분류·일자만 있어 근거로 쓰기엔 본문이 없다. 그래서 상세를 한 번 더
조회해 `ExistingEventHit` 을 채운다. 상세 조회가 실패한 건은 버리지 않고 목록 정보만으로
남겨, 한 건의 실패가 분기 전체를 빈손으로 만들지 않게 한다.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from mcp import ClientSession

from apps.agents.event_generate_agent.constants import MAX_EXISTING_EVENTS
from apps.agents.event_generate_agent.flows.generate_from_query.schema import ExistingEventHit
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.connectors.mcp.mcp_client import call_mcp_tool, mi_mcp_session


TOOL_EVENTS_LIST = "mi_events_list"
TOOL_EVENT_DETAIL = "mi_event_detail"

# MCP 서버가 startDate/endDate 에 강제하는 형식.
_ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# 상세 조회 fan-out 상한. 목록 상한(MAX_EXISTING_EVENTS)만큼 동시에 던지면
# MCP 서버가 감싸는 원본 API 에 순간 부하가 몰린다.
_DETAIL_CONCURRENCY = 5


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _dedup(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _to_hit(summary: dict[str, Any], detail: dict[str, Any]) -> ExistingEventHit:
    """목록 1건 + 상세 1건을 ExistingEventHit 으로 정규화한다.

    `detail` 이 비면(상세 조회 실패) 목록 정보만으로 만든다.

    - `one_line_summary`: MCP 의 `eventName` 을 담는다(이벤트 제목 역할). 본문은
      `detail_analysis`(AI 분석)와 `key_bullets`(영향도 종합·기관 종합)가 담는다.
    - `event_type_l2_id`: MCP 는 `eventTypeLv2` 를 코드 문자열로만 주고
      tmm_mi_mievent_m 의 정수 id 는 주지 않으므로 None 이다. 이름만 옮긴다.
    """
    impact = detail.get("impactAnalysis") or {}
    ai_insights = detail.get("aiInsights") or {}

    key_bullets = _dedup(
        [
            _text(impact.get("analysisText")),
            _text(detail.get("institutionViewSynthesis")),
        ],
    )
    index_names = [_text(item.get("indexName")) for item in (impact.get("indexImpacts") or [])]
    index_names.extend(_text(item.get("indexName")) for item in (summary.get("indexImpacts") or []))
    tags = _dedup(
        [
            _text(impact.get("eventTypeLv1Label")) or _text(summary.get("eventTypeLv1Label")),
            _text(impact.get("eventTypeLv2Label")),
            _text(summary.get("signalTypeLabel")),
            *index_names,
        ],
    )

    return ExistingEventHit(
        mi_event_id=int(summary["eventId"]),
        one_line_summary=_text(summary.get("eventName")) or _text(detail.get("eventName")),
        detail_analysis=_text(ai_insights.get("detailedAnalysis")),
        key_bullets=key_bullets,
        tags=tags,
        occurred_at=_text(summary.get("latestRecordFirstCreated")) or _text(summary.get("createdAt")),
        event_type_l2_id=None,
        event_type_l2_name=_text(impact.get("eventTypeLv2Label")) or _text(summary.get("eventTypeLv1Label")),
        # 키워드 LIKE 매칭이라 관련도 점수가 없다(schema 규약상 0.0).
    )


def _list_arguments(
    keyword: str,
    *,
    limit: int,
    date_from: str,
    date_to: str,
) -> dict[str, Any]:
    arguments: dict[str, Any] = {"keyword": keyword, "page": 1, "size": limit, "sort": "latest"}
    # 기간은 '최신 연관 레코드 최초 생성일시' 기준이며, 서버가 YYYY-MM-DD 가 아닌 값(빈 문자열 포함)을
    # 거절한다. 기간은 선택적 필터이므로 형식이 어긋나면 그 키만 빼고 나머지 조건으로 검색한다.
    # startDate 없이 endDate 만 보내는 것은 서버가 허용한다.
    for key, value in (("startDate", date_from), ("endDate", date_to)):
        if not value:
            continue
        if not _ISO_DATE_PATTERN.match(value):
            logger.warning(f"[TOOL][search_events_by_keyword] INVALID_DATE | {key}={value!r} | 필터에서 제외")
            continue
        arguments[key] = value
    return arguments


async def _fetch_detail(
    session: ClientSession,
    mi_event_id: int,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """이벤트 상세 1건을 조회한다. 실패는 여기서 삼키고 빈 dict 를 돌려준다."""
    async with semaphore:
        try:
            return await call_mcp_tool(session, TOOL_EVENT_DETAIL, {"eventId": mi_event_id})
        except Exception as exc:
            logger.warning(
                f"[TOOL][search_events_by_keyword] DETAIL_FAILED | mi_event_id={mi_event_id} | error={exc!r}",
            )
            return {}


@log_tool
async def search_events_by_keyword(
    keyword: str,
    *,
    limit: int = MAX_EXISTING_EVENTS,
    date_from: str = "",
    date_to: str = "",
) -> list[ExistingEventHit]:
    """키워드로 기존 이벤트를 찾아 상세까지 붙인 ExistingEventHit 목록을 만든다.

    Args:
        keyword: 이벤트 제목 검색 키워드.
        limit: 조회·반환할 이벤트 상한.
        date_from: 조회 시작일(YYYY-MM-DD). 빈 문자열이면 기간 필터를 걸지 않는다.
        date_to: 조회 종료일(YYYY-MM-DD).

    """
    if not keyword.strip():
        return []

    async with mi_mcp_session() as session:
        payload = await call_mcp_tool(
            session,
            TOOL_EVENTS_LIST,
            _list_arguments(keyword.strip(), limit=limit, date_from=date_from, date_to=date_to),
        )
        events = payload.get("events") or {}
        summaries = [item for item in (events.get("detail") or []) if item.get("eventId") is not None][:limit]
        total = events.get("totalElements")

        if not summaries:
            logger.info(f"[TOOL][search_events_by_keyword] NO_HIT | keyword={keyword!r} | total={total}")
            return []

        semaphore = asyncio.Semaphore(_DETAIL_CONCURRENCY)
        details = await asyncio.gather(
            *(_fetch_detail(session, int(summary["eventId"]), semaphore) for summary in summaries),
        )

    hits = [_to_hit(summary, detail) for summary, detail in zip(summaries, details, strict=True)]
    logger.info(
        f"[TOOL][search_events_by_keyword] DONE | keyword={keyword!r} | total={total} "
        f"| hits={len(hits)} | detail_failed={sum(1 for detail in details if not detail)} "
        f"| ids={[hit.mi_event_id for hit in hits]}",
    )
    return hits
