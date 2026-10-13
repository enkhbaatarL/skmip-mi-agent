"""search_existing_events 노드 — 기존 DB 이벤트에서 토픽별 생성 근거를 수집한다.

classify_route 가 사용자 문장에서 기존 이벤트에 대한 특정 언급을 읽어내면
(`SearchRoute.EXISTING_EVENT`) 이 노드로 들어온다. 실제 조회는
tools/event_search.py 가 MI MCP 서버(mi_events_list → mi_event_detail)로 수행하고,
이 노드는 토픽별 키워드 결정, 실패 처리, 공통 근거(EvidenceItem) 변환만 맡는다.

여러 이벤트를 병합하는 요청은 대상 이벤트마다 토픽이 하나씩 오므로(plan.topics),
토픽별로 병렬 조회하고 결과에 topic_key 를 달아 토픽끼리 섞지 않는다.
같은 이벤트가 두 토픽에 걸리면 토픽마다 따로 남긴다(관련 여부는 summarize_topics 가 토픽별로 판단).
"""

from __future__ import annotations

import asyncio
from typing import Any

from apps.agents.event_generate_agent.constants import MAX_EXISTING_EVENTS
from apps.agents.event_generate_agent.flows.generate_from_query.schema import BranchError, ExistingEventHit
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.flows.generate_from_query.tools.event_search import (
    search_events_by_keyword,
)
from apps.agents.event_generate_agent.flows.generate_from_query.tools.evidence import event_hits_to_evidences
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger


def _branch_error(message: str) -> BranchError:
    return BranchError(stage="search_existing_events", message=message)


def _tag_topic(hits: list[ExistingEventHit], topic_key: str) -> list[ExistingEventHit]:
    """토픽 안에서 같은 이벤트는 첫 등장만 남기고 topic_key 를 단다."""
    tagged: list[ExistingEventHit] = []
    seen: set[int] = set()
    for hit in hits:
        if hit.mi_event_id in seen:
            continue
        seen.add(hit.mi_event_id)
        tagged.append(hit.model_copy(update={"topic_key": topic_key}))
    return tagged


@log_node
async def search_existing_events(state: GenerateFromQueryState) -> dict[str, Any]:
    """토픽별 키워드/기간으로 기존 이벤트를 조회해 state.evidences 에 근거(T1-E1 …)로 덧붙인다.

    MCP 서버는 외부 의존이므로 실패해도 flow 를 중단하지 않고 branch_errors 에 남긴다.
    토픽 일부만 실패하면 성공한 토픽의 결과는 그대로 쓴다.
    폴백 패스(pending_fallback)에서는 재검색 대상 토픽만 조회해 기존 결과 뒤에 덧붙인다.
    """
    plan = state.query_plan
    topics = [topic for topic in state.topics_to_search() if topic.event_keyword.strip()]
    if not topics:
        logger.warning("[NODE][search_existing_events] NO_KEYWORD")
        return {"branch_errors": [_branch_error("검색할 이벤트 키워드가 없습니다.")]}

    results = await asyncio.gather(
        *(
            search_events_by_keyword(
                topic.event_keyword.strip(),
                limit=MAX_EXISTING_EVENTS,
                date_from=plan.date_from if plan else "",
                date_to=plan.date_to if plan else "",
            )
            for topic in topics
        ),
        return_exceptions=True,
    )

    hits: list[ExistingEventHit] = []
    errors: list[BranchError] = []
    for topic, result in zip(topics, results, strict=True):
        if isinstance(result, BaseException):
            # 외부 의존의 실패로 전체 flow 가 중단되지 않게 한다.
            logger.error(
                f"[NODE][search_existing_events] SEARCH_FAILED | topic={topic.topic_key} "
                f"| keyword={topic.event_keyword!r} | error={result!r}",
            )
            errors.append(
                _branch_error(
                    f"기존 이벤트 검색 중 오류가 발생했습니다(topic={topic.label}, keyword={topic.event_keyword}): "
                    f"{result!r}",
                ),
            )
            continue
        topic_hits = _tag_topic(result, topic.topic_key)
        logger.info(
            f"[NODE][search_existing_events] TOPIC_DONE | topic={topic.topic_key} | label={topic.label!r} "
            f"| keyword={topic.event_keyword!r} | events={len(topic_hits)}",
        )
        for index, hit in enumerate(topic_hits, start=1):
            logger.debug(
                f"[NODE][search_existing_events] EVENT | {topic.topic_key} #{index} | id={hit.mi_event_id} "
                f"| occurred_at={hit.occurred_at} | type={hit.event_type_l2_name} | summary={hit.one_line_summary!r}",
            )
        hits.extend(topic_hits)

    # evidences 는 누적 reducer 라 반환한 근거가 기존 근거 뒤에 덧붙는다(폴백 패스도 동일).
    update: dict[str, Any] = {"evidences": event_hits_to_evidences(hits, state.evidences)}
    if errors:
        update["branch_errors"] = errors

    logger.info(
        f"[NODE][search_existing_events] DONE | topics={[topic.topic_key for topic in topics]} "
        f"| fallback={state.pending_fallback} | events={len(hits)}",
    )
    return update
