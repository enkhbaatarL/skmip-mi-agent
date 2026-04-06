from __future__ import annotations

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.tools.classify_intent import classify_intent
from apps.common.logging.decorators import log_node
from apps.common.streaming.decorators import stream_step


@stream_step(step_key="classify_intent")
@log_node
async def classify_intent_node(state: MariAgentState) -> MariAgentState:
    state.analysis_type = await classify_intent(state.rewritten_query)

    return state
