"""persist_events 노드 — 생성된 이벤트 초안을 tmm_mi_mievent_m 에 저장한다."""

from __future__ import annotations

import asyncio
from typing import Any

from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.persistence.event_generation_service import (
    EventGenerationService,
)
from apps.agents.event_generate_agent.schemas.api.event import GeneratedEventOut
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger


def _persist_target(state: GenerateFromQueryState) -> tuple[GeneratedEventOut | None, str | None]:
    """저장할 이벤트와, 저장하지 않을 때의 경고를 만든다.

    event type L2 는 tmm_mi_mievent_m 의 NOT NULL FK라 분류에 실패한 초안은 저장할 수
    없다. 검증 error 가 있는 초안도 insert 대상이 아니다. 모두 요청 전체를
    실패시키지 않고 경고로만 남겨, 생성된 초안 자체는 응답으로 돌려준다.
    """
    draft = state.draft
    if draft is None:
        return None, None
    validation = state.validation
    if validation is None or validation.blocked:
        # 검증 error(근거 충돌·시점 불일치·검증 실패 등)가 있거나 검증 결과가 없으면 저장하지 않는다.
        # 사유는 finalize 가 검증 이슈로 따로 알리므로 여기서는 경고를 중복으로 남기지 않는다.
        if validation is None:
            return None, f"'{draft.one_line_summary}' 는 검증 결과가 없어 저장하지 않았습니다."
        return None, None
    event_type_l2_id = state.type_assignment.event_type_l2_id if state.type_assignment else None
    if event_type_l2_id is None:
        return None, f"'{draft.one_line_summary}' 는 event type L2 분류 결과가 없어 저장하지 않았습니다."
    target = GeneratedEventOut(
        one_line_summary=draft.one_line_summary,
        detail_analysis=draft.detail_analysis,
        key_bullets=list(draft.key_bullets),
        tags=list(draft.tags),
        occurred_at=draft.occurred_at,
        event_type_l2_id=event_type_l2_id,
    )
    return target, None


@log_node
async def persist_events(state: GenerateFromQueryState) -> dict[str, Any]:
    """저장 가능한 초안을 insert하고 발급된 mi_event_id를 상태에 담는다."""
    target, warning = _persist_target(state)
    warnings = [warning] if warning else []
    if target is None:
        logger.info(f"[NODE][persist_events] NOTHING_TO_PERSIST | has_draft={state.draft is not None}")
        return {"saved_event_id": None, "warnings": warnings}

    try:
        # search_text 는 DB 저장 전용이라 응답 shape(GeneratedEventOut)에 넣지 않고 따로 넘긴다.
        confirmed = await asyncio.to_thread(
            EventGenerationService().create_event,
            target,
            search_text=state.draft.search_text if state.draft else "",
            user_id=state.user_id,
        )
    except Exception as exc:
        # 저장 실패로 LLM 생성 결과까지 잃지 않도록, 경고로 노출하고 초안은 그대로 반환한다.
        logger.error(f"[NODE][persist_events] FAILED | error={exc!r}")
        return {"saved_event_id": None, "warnings": [*warnings, f"이벤트 저장에 실패했습니다: {exc}"]}

    logger.info(f"[NODE][persist_events] PERSISTED | mi_event_id={confirmed.mi_event_id}")
    return {"saved_event_id": confirmed.mi_event_id, "warnings": warnings}
