from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json

from apps.agents.scenario_group_agent.prompts.event_recommendation import (
    EVENT_RECOMMENDATION_SYSTEM_PROMPT,
    MULTI_EVENT_RECOMMENDATION_INSTRUCTION,
    EventRecommendationItem,
    EventRecommendationOutput,
    MultiEventRecommendationOutput,
)
from apps.agents.scenario_group_agent.schemas.api.event_recommendations import (
    EventRecommendationsOut,
    RecommendedEvent,
)
from apps.agents.scenario_group_agent.utils.event_recommendation import validate_event_recommendation_output
from apps.agents.scenario_group_agent.utils.event_search_document import build_event_search_text
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.connectors.llm.llm_client import invoke_llm_structured_output
from apps.connectors.vdb.local_event_search import get_local_event_search
from apps.persistence.event.schema import EventPayload, EventSearchSource
from apps.persistence.event.service import EventService


def _payload(source: EventSearchSource) -> EventPayload:
    text, tags, _ = build_event_search_text(source)
    return EventPayload(
        mi_event_id=source.mi_event_id,
        event_title_ko=source.one_line_summary,
        one_line_summary=source.search_text,
        detail_analysis=text,
        tags=tags,
        occurred_at=source.occurred_at.isoformat() if source.occurred_at else "",
        source_mi_record_ids=source.source_record_ids,
    )


class EventRecommendationService:
    """Local shared-corpus recommendation; caller backend owns user authentication."""

    async def recommend(self, event_ids: list[int]) -> EventRecommendationsOut:
        service = EventService()
        sources = await asyncio.to_thread(service.load_search_sources, event_ids=event_ids)
        source_by_id = {source.mi_event_id: _payload(source) for source in sources}
        if set(source_by_id) != set(event_ids):
            raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="선택한 Event가 없거나 게시 상태가 아닙니다.")
        cfg = get_settings()
        search = get_local_event_search(
            cfg.event_search_documents,
            cfg.event_search_db_path,
            cfg.event_search_model_cache,
        )
        candidate_ids = await asyncio.to_thread(
            search.search,
            [source_by_id[event_id].detail_analysis for event_id in event_ids],
            event_ids,
        )
        candidate_ids = list(dict.fromkeys(event_id for event_id in candidate_ids if event_id not in source_by_id))
        if not candidate_ids:
            return EventRecommendationsOut(items=[], selection_reason="검색된 후보 Event가 없습니다.")
        # Vector payload is a snapshot. Only current published, non-deleted DB rows enter the prompt.
        rows = await asyncio.to_thread(service.load_search_sources, event_ids=candidate_ids)
        candidate_by_id = {row.mi_event_id: _payload(row) for row in rows}
        candidates = [candidate_by_id[event_id] for event_id in candidate_ids if event_id in candidate_by_id][:10]
        if not candidates:
            return EventRecommendationsOut(items=[], selection_reason="현재 게시 상태인 후보 Event가 없습니다.")
        result = await invoke_llm_structured_output(
            output_schema=MultiEventRecommendationOutput,
            messages=[
                {
                    "role": "system",
                    "content": EVENT_RECOMMENDATION_SYSTEM_PROMPT + MULTI_EVENT_RECOMMENDATION_INSTRUCTION,
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "as_of": datetime.now(UTC).date().isoformat(),
                            "source_events": [source_by_id[event_id].model_dump(mode="json") for event_id in event_ids],
                            "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.0,
            max_retries=0,
            stream=cfg.llm_stream_enabled,
            reasoning_effort=cfg.llm_reasoning_effort,
            log_label="event_recommendation",
        )
        output = result.result
        seen = set(event_ids)
        items: list[RecommendedEvent] = []
        for item in output.items:
            if item.source_event_id not in source_by_id or item.mi_event_id in seen:
                raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail="추천 ID가 유효하지 않거나 중복입니다.")
            validate_event_recommendation_output(
                EventRecommendationOutput(
                    items=[EventRecommendationItem.model_validate(item.model_dump(exclude={"source_event_id"}))],
                    selection_reason=output.selection_reason,
                ),
                source_event=source_by_id[item.source_event_id],
                candidates=candidates,
            )
            seen.add(item.mi_event_id)
            items.append(
                RecommendedEvent(
                    mi_event_id=item.mi_event_id,
                    title=candidate_by_id[item.mi_event_id].event_title_ko,
                    reason=item.reason,
                ),
            )
        return EventRecommendationsOut(items=items, selection_reason=output.selection_reason)
