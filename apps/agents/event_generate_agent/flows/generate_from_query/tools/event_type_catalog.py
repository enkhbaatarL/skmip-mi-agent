"""Event type 카탈로그 조회 툴.

tmm_mi_event_type_l2_m 의 활성 행(del_yn='N')을 읽어, 분류 프롬프트에 넣을
`EventTypeCatalogItem`(event_type_l2_id, level_2_code, level_2_label) 목록으로 돌려준다.
분류 LLM 은 이 목록의 event_type_l2_id 중에서만 고른다.

DB 접근은 sync SQLAlchemy 세션이라 async 노드에서 이벤트 루프를 막지 않도록
`asyncio.to_thread` 로 감싼다(persist_events 노드와 같은 방식).
"""

from __future__ import annotations

import asyncio
from typing import Any

from apps.agents.event_generate_agent.persistence.event_generation_service import (
    EventGenerationService,
)
from apps.agents.event_generate_agent.schemas.domain import EventTypeCatalogItem
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger


def _to_catalog_item(row: dict[str, Any]) -> EventTypeCatalogItem:
    """EventRepository.list_event_types_l2 의 행 1건을 분류 후보로 옮긴다."""
    return EventTypeCatalogItem(
        event_type_l2_id=int(row["event_type_l2_id"]),
        code=str(row.get("level_2_code") or ""),
        label=str(row.get("level_2_label") or ""),
    )


@log_tool
async def load_event_type_catalog() -> list[EventTypeCatalogItem]:
    """tmm_mi_event_type_l2_m 의 event type 후보 전체를 조회한다.

    조회에 실패해도 호출한 노드를 중단시키지 않는다 — 빈 목록을 돌려주면
    분류 노드가 폴백(FALLBACK_EVENT_TYPE_L2_ID)으로 처리한다.
    """
    try:
        rows = await asyncio.to_thread(EventGenerationService().load_event_type_catalog)
    except Exception as exc:
        logger.warning(f"[TOOL][load_event_type_catalog] FAILED | error={exc!r}")
        return []

    catalog: list[EventTypeCatalogItem] = []
    for row in rows:
        try:
            catalog.append(_to_catalog_item(row))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(f"[TOOL][load_event_type_catalog] INVALID_ROW | row={row!r} | error={exc!r}")
    return catalog
