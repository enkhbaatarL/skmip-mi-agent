from __future__ import annotations

from collections.abc import Sequence

from apps.agents.scenario_group_agent.prompts.event_recommendation import EventRecommendationOutput
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload


def prepare_event_recommendation_candidates(
    source_event: EventPayload,
    retrieved_events: Sequence[EventPayload],
    *,
    eligible_event_ids: frozenset[int],
    excluded_event_ids: frozenset[int] = frozenset(),
) -> list[EventPayload]:
    """Keep unique eligible IDs before sending Event text to an LLM.

    The service must obtain eligible_event_ids from current authoritative DB/access checks
    (active, PUBLISHED, accessible to the requesting user), never from the client or the LLM.
    Vector metadata alone is insufficient. This helper does not query the DB or grant access.
    """
    source_id = int(source_event.mi_event_id)
    if source_id not in eligible_event_ids:
        raise MIBaseError(ErrorCode.RDB_ACCESS_DENIED, detail="기준 Event가 추천 조회 대상이 아닙니다.")
    seen = {source_id, *excluded_event_ids}
    candidates: list[EventPayload] = []
    for event in retrieved_events:
        event_id = int(event.mi_event_id)
        if event_id in eligible_event_ids and event_id not in seen:
            candidates.append(event)
            seen.add(event_id)
    return candidates


def _contains_evidence(event: EventPayload, quote: str) -> bool:
    fields = (event.event_title_ko, event.one_line_summary, event.detail_analysis, *event.key_bullets)
    return any(quote in text for text in fields)


def validate_event_recommendation_output(
    output: EventRecommendationOutput,
    *,
    source_event: EventPayload,
    candidates: Sequence[EventPayload],
) -> EventRecommendationOutput:
    """Check IDs and literal evidence against the exact filtered input passed to the LLM.

    The caller must parse output with EventRecommendationOutput first. Semantic relevance,
    duplicate stories and factual entailment remain LLM/reviewer judgments, not substring checks.
    """
    candidate_by_id = {int(event.mi_event_id): event for event in candidates}
    seen = {int(source_event.mi_event_id)}
    for item in output.items:
        candidate = candidate_by_id.get(item.mi_event_id)
        if candidate is None or item.mi_event_id in seen:
            raise MIBaseError(
                ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                detail=f"추천 Event ID가 후보에 없거나 중복입니다: {item.mi_event_id}",
            )
        if not _contains_evidence(source_event, item.source_evidence) or not _contains_evidence(
            candidate,
            item.candidate_evidence,
        ):
            raise MIBaseError(
                ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                detail=f"추천 근거가 입력 Event 원문에 없습니다: {item.mi_event_id}",
            )
        seen.add(item.mi_event_id)
    return output
