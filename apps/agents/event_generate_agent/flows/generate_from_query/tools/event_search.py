"""기존 MI 이벤트 검색 툴.

tmm_mi_mievent_m 을 직접 조회해 키워드(제목·상세 분석 단어별 LIKE)/기간(occurred_at)으로 이벤트를 찾는다.
근거 본문은 `detail_analysis` 컬럼만 쓴다.

DB 접근은 동기 세션이라 이벤트 루프를 막지 않도록 `asyncio.to_thread` 로 감싼다
(event_type_catalog, persist_events 노드와 같은 방식).
"""

from __future__ import annotations

import asyncio
from datetime import date

from apps.agents.event_generate_agent.constants import MAX_EXISTING_EVENTS
from apps.agents.event_generate_agent.flows.generate_from_query.schema import ExistingEventHit
from apps.agents.event_generate_agent.persistence.event_generation_service import EventGenerationService
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger


def _parse_date(key: str, value: str) -> date | None:
    """YYYY-MM-DD 문자열을 date 로 바꾼다.

    기간은 선택적 필터이므로 형식이 어긋나면 그 경계만 빼고 나머지 조건으로 검색한다.
    """
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        logger.warning(f"[TOOL][search_events_by_keyword] INVALID_DATE | {key}={value!r} | 필터에서 제외")
        return None


@log_tool
async def search_events_by_keyword(
    keyword: str,
    *,
    limit: int = MAX_EXISTING_EVENTS,
    date_from: str = "",
    date_to: str = "",
) -> list[ExistingEventHit]:
    """키워드로 기존 이벤트를 찾아 detail_analysis 를 담은 ExistingEventHit 목록을 만든다.

    Args:
        keyword: 이벤트 제목/상세 분석 검색 키워드. 공백 단위로 쪼개 하나라도 맞으면 후보가 된다.
        limit: 조회·반환할 이벤트 상한.
        date_from: 조회 시작일(YYYY-MM-DD, occurred_at 기준). 빈 문자열이면 하한을 걸지 않는다.
        date_to: 조회 종료일(YYYY-MM-DD, 당일 포함).

    """
    keyword = keyword.strip()
    if not keyword:
        return []

    rows = await asyncio.to_thread(
        EventGenerationService().search_events,
        keyword,
        limit=limit,
        date_from=_parse_date("date_from", date_from),
        date_to=_parse_date("date_to", date_to),
    )
    hits = [ExistingEventHit.model_validate(row) for row in rows]

    logger.info(
        f"[TOOL][search_events_by_keyword] DONE | keyword={keyword!r} | hits={len(hits)} "
        f"| ids={[hit.mi_event_id for hit in hits]}",
    )
    return hits
