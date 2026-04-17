# apps/agents/event_flow_agent/nodes/read_record_source.py

from __future__ import annotations
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState

def read_record_source(
    state: EventFlowState,
    repository,
) -> EventFlowState:
    state.current_node = "read_record_source"
    state.executed_nodes.append(state.current_node)

    try:
        records = repository.fetch_news_records(
            market_category=state.market_category,
            limit=state.limit,
            from_first_created=state.from_first_created,
            to_first_created=state.to_first_created,
        )
        state.source_records = records
    except Exception as exc:
        state.errors.append(f"원천 record 조회 실패: {exc}")

    return state