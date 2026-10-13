"""generate_from_query flow 라우팅 함수.

라우팅 함수는 상태만 읽는 순수 함수로 유지한다(LLM 재호출 금지).
분기 판단 자체는 classify_route가 state.route 에 담아 두고,
여기서는 그 값을 노드 이름으로 옮기기만 한다.
"""

from __future__ import annotations

from apps.agents.event_generate_agent.flows.generate_from_query.schema import SearchRoute
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState


NODE_SEARCH_WEB = "search_web"
NODE_SEARCH_EXISTING_EVENTS = "search_existing_events"
NODE_BUILD_FACT_TIMELINE = "build_fact_timeline"
NODE_DRAFT_EVENTS = "draft_events"
NODE_PERSIST_EVENTS = "persist_events"
NODE_VALIDATE_CLAIMS = "validate_claims"
NODE_CLASSIFY_EVENT_TYPE = "classify_event_type"
NODE_JOIN_DRAFT_REVIEW = "join_draft_review"

# 노드 이름 목록을 반환하면 LangGraph 가 그 노드들을 같은 superstep 에서 병렬 실행한다.
# BOTH 는 두 검색 노드를 함께 띄우고, 둘 다 끝나면 공통 하위 노드인 summarize_topics 가
# 한 번만 실행된다. 두 노드의 근거는 state.evidences 의 누적 reducer 로 합쳐진다.
_NODE_BY_ROUTE = {
    SearchRoute.WEB: [NODE_SEARCH_WEB],
    SearchRoute.EXISTING_EVENT: [NODE_SEARCH_EXISTING_EVENTS],
    SearchRoute.BOTH: [NODE_SEARCH_WEB, NODE_SEARCH_EXISTING_EVENTS],
}


def route_after_plan(state: GenerateFromQueryState) -> list[str]:
    """선택된 분기로 보낸다. BOTH 면 두 분기를 병렬로 띄운다."""
    return _NODE_BY_ROUTE[state.route]


def route_after_summary(state: GenerateFromQueryState) -> list[str]:
    """관련 근거가 없는 토픽의 폴백이 예약된 경우에만 반대 분기로 보낸다(그 토픽만 재검색)."""
    if state.pending_fallback and state.fallback_route is not None:
        return _NODE_BY_ROUTE[state.fallback_route]
    return [NODE_BUILD_FACT_TIMELINE]


def route_after_validation(state: GenerateFromQueryState) -> str:
    """Claim 검증이 재작성을 예약했으면 초안 생성으로 되돌리고, 아니면 뒷단으로 보낸다.

    join_draft_review(검증·유형 분류 합류) 뒤에서 호출된다.
    """
    return NODE_DRAFT_EVENTS if state.pending_revision else NODE_PERSIST_EVENTS
