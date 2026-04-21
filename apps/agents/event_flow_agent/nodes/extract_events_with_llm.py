# apps/agents/event_flow_agent/nodes/extract_events_with_llm.py
#   kmj20260420월

from __future__ import annotations

from apps.agents.event_flow_agent.services.event_extraction_service import (
    EventExtractionService,
)
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


async def extract_events_with_llm_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "extract_events_with_llm"
    state.executed_nodes.append("extract_events_with_llm")

    try:
        service = EventExtractionService()
        result = await service.extract(state.record_analyses)
        state.extracted_events = [event.model_dump(mode="json") for event in result.events]
        return state

    except Exception as exc:
        state.extracted_events = []
        state.errors.append(f"event 추출 실패: {exc}")
        return state