# apps/agents/event_flow_agent/nodes/read_record_source.py
#   kmj20260421화 수정

from __future__ import annotations

from apps.agents.event_flow_agent.services.record_source_service import RecordSourceService
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def read_record_source_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "read_record_source"
    state.executed_nodes.append("read_record_source")

    try:
        records = RecordSourceService().fetch_news_records(
            market_category=state.market_category,
            limit=state.limit,
            from_first_created=state.from_first_created,
            to_first_created=state.to_first_created,
        )
        state.source_records = records
        return state

    except Exception as exc:
        state.source_records = []
        state.errors.append(f"원천 record 조회 실패: {exc}")
        return state