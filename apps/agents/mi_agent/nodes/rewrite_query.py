from __future__ import annotations

from apps.agents.mi_agent.schemas.schemas import RewriteQueryResult
from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.tools.rewrite_query import rewrite_query
from apps.common.logging.decorators import log_node
from apps.common.streaming.decorators import stream_step


@stream_step(step_key="rewrite_query")
@log_node
async def rewrite_query_node(state: MariAgentState) -> MariAgentState:
    rewrite_query_result: RewriteQueryResult = await rewrite_query(state.histories, state.user_query)
    state.rewritten_query, state.user_query_language = (
        rewrite_query_result.rewritten_query,
        rewrite_query_result.user_query_language,
    )
    return state
