# apps/agents/event_flow_agent/nodes/extract_events_with_llm.py

from __future__ import annotations

from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


async def extract_events_with_llm(state: EventFlowState, service) -> EventFlowState:
    state.current_node = "extract_events_with_llm"
    state.executed_nodes.append(state.current_node)

    try:
        result = await service.extract(state.record_analyses)
        state.extracted_events = [event.model_dump(mode="json") for event in result.events]
    except Exception as exc:
        state.errors.append(f"event 추출 실패: {exc}")

    return state