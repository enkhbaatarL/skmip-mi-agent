from __future__ import annotations

from apps.agents.mi_agent.state.state import MariAgentState
from apps.common.logging.decorators import log_node
from apps.common.streaming.decorators import stream_step


@stream_step(step_key="plan")
@log_node
async def planner_node(state: MariAgentState) -> MariAgentState:
    return state
