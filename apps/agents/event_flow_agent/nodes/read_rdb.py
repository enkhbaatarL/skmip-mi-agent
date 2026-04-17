#   apps/agents/event_flow_agent/nodes/read_rdb.py

from __future__ import annotations

from apps.agents.event_flow_agent.repositories.sync_event_repository import SyncEventRepository
from apps.agents.event_flow_agent.services.event_service import EventService
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState
from apps.common.configs.database.sync_database.connection import get_sync_session


async def read_rdb_node(state: EventFlowState) -> EventFlowState:
    limit = state.limit

    state.current_node = "read_rdb"
    state.executed_nodes.append("read_rdb")

    session = get_sync_session()
    try:
        repo = SyncEventRepository(session=session)
        service = EventService(repo=repo)
        rows = service.get_events(limit=limit)

        state.rdb_result = rows
        state.summary = f"midb 에서 {len(rows)}건 조회했습니다."
        return state

    except Exception as e:
        msg = f"RDB 조회 중 오류가 발생했습니다: {e!s}"
        state.rdb_result = []
        state.summary = msg
        state.errors.append(msg)
        return state

    finally:
        session.close()