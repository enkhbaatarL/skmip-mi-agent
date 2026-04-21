#   apps/agents/event_flow_agent/nodes/read_rdb.py
#   kmj20260421화 수정

from __future__ import annotations

from apps.agents.event_flow_agent.services.event_service import EventService
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


async def read_rdb_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "read_rdb"
    state.executed_nodes.append("read_rdb")

    try:
        rows = EventService().get_events(limit=state.limit)
        state.rdb_result = rows
        state.summary = f"midb 에서 {len(rows)}건 조회했습니다."
        return state

    except Exception as e:
        msg = f"RDB 조회 중 오류가 발생했습니다: {e!s}"
        state.rdb_result = []
        state.summary = msg
        state.errors.append(msg)
        return state