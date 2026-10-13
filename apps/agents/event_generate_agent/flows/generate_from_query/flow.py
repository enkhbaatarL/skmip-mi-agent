"""generate_from_query flow 조립 및 실행 진입점.

사용자 입력 문장을 받아 classify_route 가 근거 수집 분기(web / existing_event / both)를
고르고, plan_search 가 요청을 토픽(사건·주제)별로 나눠 토픽마다 검색 질의를 만든다.
검색 노드는 토픽별 결과를 곧바로 공통 EvidenceItem 으로 바꿔 덧붙이고, summarize_topics 가 토픽마다 정리(시점·상태를 담은
근거 사실 추출)하고, 관련 근거가 없는 토픽만 반대 분기로 1회 재검색한다.
생성 전에 build_fact_timeline 이 근거 사실이 시나리오 기준일에 유효한지 날짜로 판정한 시점표를 만들어 초안 생성에 제약으로 넘긴다.
생성 후에는 validate_claims 가 claim 단위로 근거 지지·충돌·시점·수치 정합성을 검증하고, 고칠 수 있는 error 가 있으면
초안을 1회 재작성한다. error 가 남은 초안은 저장하지 않는다.

classify_route → plan_search → search_web | search_existing_events
  → summarize_topics ─(근거 없는 토픽 폴백)→ 반대 분기 검색 → summarize_topics
                     └→ build_fact_timeline → draft_events ─┬→ validate_claims     ─┬→ join_draft_review
                                                          └→ classify_event_type ─┘
  join_draft_review ─(재작성)→ draft_events
                    └→ persist_events → finalize

validate_claims 와 classify_event_type 은 초안만 있으면 서로 독립이라 병렬로 실행하고 join_draft_review 에서 합류한다.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from apps.agents.event_generate_agent.constants import AGENT_NAME
from apps.agents.event_generate_agent.flows.generate_from_query.api_schema import (
    GenerateFromQueryResult,
)
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.classify_route import classify_route
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.fact_timeline import build_fact_timeline
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.generate import (
    classify_event_type,
    draft_events,
    finalize,
)
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.persist import persist_events
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.plan_search import plan_search
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.search_events import (
    search_existing_events,
)
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.search_web import search_web
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.summarize import summarize_topics
from apps.agents.event_generate_agent.flows.generate_from_query.nodes.validate_claims import (
    join_draft_review,
    validate_claims,
)
from apps.agents.event_generate_agent.flows.generate_from_query.routing import (
    NODE_BUILD_FACT_TIMELINE,
    NODE_CLASSIFY_EVENT_TYPE,
    NODE_DRAFT_EVENTS,
    NODE_JOIN_DRAFT_REVIEW,
    NODE_PERSIST_EVENTS,
    NODE_SEARCH_EXISTING_EVENTS,
    NODE_SEARCH_WEB,
    NODE_VALIDATE_CLAIMS,
    route_after_plan,
    route_after_summary,
    route_after_validation,
)
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import (
    TraceContext,
    build_langgraph_config,
    mlflow_trace_context,
    new_transaction_id,
)
from apps.common.values.error_codes import ErrorCode


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    builder = StateGraph(GenerateFromQueryState, context_schema=TraceContext)
    builder.add_node("classify_route", classify_route)
    builder.add_node("plan_search", plan_search)
    builder.add_node(NODE_SEARCH_WEB, search_web)
    builder.add_node(NODE_SEARCH_EXISTING_EVENTS, search_existing_events)
    builder.add_node("summarize_topics", summarize_topics)
    builder.add_node(NODE_BUILD_FACT_TIMELINE, build_fact_timeline)
    builder.add_node(NODE_DRAFT_EVENTS, draft_events)
    builder.add_node(NODE_VALIDATE_CLAIMS, validate_claims)
    builder.add_node(NODE_CLASSIFY_EVENT_TYPE, classify_event_type)
    builder.add_node(NODE_JOIN_DRAFT_REVIEW, join_draft_review)
    builder.add_node(NODE_PERSIST_EVENTS, persist_events)
    builder.add_node("finalize", finalize)

    builder.set_entry_point("classify_route")
    builder.add_edge("classify_route", "plan_search")
    builder.add_conditional_edges(
        "plan_search",
        route_after_plan,
        {
            NODE_SEARCH_WEB: NODE_SEARCH_WEB,
            NODE_SEARCH_EXISTING_EVENTS: NODE_SEARCH_EXISTING_EVENTS,
        },
    )
    builder.add_edge(NODE_SEARCH_WEB, "summarize_topics")
    builder.add_edge(NODE_SEARCH_EXISTING_EVENTS, "summarize_topics")
    builder.add_conditional_edges(
        "summarize_topics",
        route_after_summary,
        {
            NODE_SEARCH_WEB: NODE_SEARCH_WEB,
            NODE_SEARCH_EXISTING_EVENTS: NODE_SEARCH_EXISTING_EVENTS,
            NODE_BUILD_FACT_TIMELINE: NODE_BUILD_FACT_TIMELINE,
        },
    )
    builder.add_edge(NODE_BUILD_FACT_TIMELINE, NODE_DRAFT_EVENTS)
    # 검증과 유형 분류를 병렬로 띄우고, 둘 다 끝나면 합류 노드에서 재작성 여부를 판단한다.
    builder.add_edge(NODE_DRAFT_EVENTS, NODE_VALIDATE_CLAIMS)
    builder.add_edge(NODE_DRAFT_EVENTS, NODE_CLASSIFY_EVENT_TYPE)
    builder.add_edge([NODE_VALIDATE_CLAIMS, NODE_CLASSIFY_EVENT_TYPE], NODE_JOIN_DRAFT_REVIEW)
    builder.add_conditional_edges(
        NODE_JOIN_DRAFT_REVIEW,
        route_after_validation,
        {
            NODE_DRAFT_EVENTS: NODE_DRAFT_EVENTS,
            NODE_PERSIST_EVENTS: NODE_PERSIST_EVENTS,
        },
    )
    builder.add_edge(NODE_PERSIST_EVENTS, "finalize")
    builder.add_edge("finalize", END)
    return builder.compile()


async def run_generate_from_query(
    user_query: str,
    date_from: str | None = None,
    date_to: str | None = None,
    language: str | None = None,
    user_id: int | None = None,
) -> GenerateFromQueryResult:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    agent_config = cfg.get_agent_config(AGENT_NAME)
    trace_context = TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        session_id=None,
    )
    state = GenerateFromQueryState(
        user_query=user_query,
        date_from=date_from or "",
        date_to=date_to or "",
        user_id=user_id,
        **({"language": language} if language else {}),
    )
    with mlflow_trace_context(trace_context):
        final_state = await get_compiled_graph().ainvoke(
            state,
            config=build_langgraph_config(trace_context),
            context=trace_context,
        )
    if isinstance(final_state, GenerateFromQueryState):
        result = final_state.result
    elif isinstance(final_state, dict):
        result = final_state.get("result")
    else:
        result = getattr(final_state, "result", None)
    if result is None:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail="이벤트 생성에 실패했습니다.",
        )
    return result
