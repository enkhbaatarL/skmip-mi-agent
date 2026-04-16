#   agents/event_flow_agent/flows/event_flow_adapters.py

from __future__ import annotations

from typing import Any

from apps.agents.event_flow_agent.schemas.event_flow_input import EventFlowInput
from apps.agents.event_flow_agent.schemas.event_flow_output import EventFlowOutput
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def to_state(input_data: EventFlowInput | dict[str, Any], **_: object) -> EventFlowState:
    parsed = EventFlowInput.model_validate(input_data)

    return EventFlowState(
        limit=parsed.limit,
    )


def to_output(state: EventFlowState | dict[str, Any]) -> EventFlowOutput:
    if isinstance(state, dict):
        state = EventFlowState.model_validate(state)

    return EventFlowOutput(
        summary=state.summary or "",
        llm_result=state.llm_result or "",
        rdb_result=state.rdb_result,
    )