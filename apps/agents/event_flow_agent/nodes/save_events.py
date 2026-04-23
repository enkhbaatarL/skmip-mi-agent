# apps/agents/event_flow_agent/nodes/save_events.py
#   kmj20260423목 수정

from __future__ import annotations

from apps.agents.event_flow_agent.services.event_persistence_service import (
    EventPersistenceService,
)
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def save_events_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "save_events"
    state.executed_nodes.append("save_events")

    try:
        saved_ids, save_errors = EventPersistenceService().save_events(
            state.extracted_events
        )
        state.saved_event_ids = saved_ids
        state.errors.extend(save_errors)
        return state

    except Exception as exc:
        state.saved_event_ids = []
        state.errors.append(f"event 저장 실패: {exc}")
        return state