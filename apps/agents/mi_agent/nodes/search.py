from __future__ import annotations

from apps.agents.mi_agent.components.context import get_search_policies
from apps.agents.mi_agent.components.policies import SearchPolicySet
from apps.agents.mi_agent.orchestration.supervisors.search_supervisor import (
    SearchSupervisor,
)
from apps.agents.mi_agent.state.state import MariAgentState
from apps.common.logging.decorators import log_node
from apps.common.streaming.decorators import stream_step


@stream_step(step_key="search")
@log_node
async def search_node(state: MariAgentState) -> MariAgentState:
    search_policy_set: SearchPolicySet = get_search_policies()
    supervisor = SearchSupervisor(search_policy_set=search_policy_set)
    merged = await supervisor.run_parallel_searches(agent_state=state)
    state.search_output = merged
    return state
