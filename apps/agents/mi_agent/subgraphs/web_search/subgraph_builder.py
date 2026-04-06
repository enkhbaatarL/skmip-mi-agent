"""Web search subgraph builder."""

from __future__ import annotations

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.web_search.schemas import WebSearchOutput
from apps.agents.mi_agent.subgraphs.web_search.stages.execute.search_web_node import (
    search_web_node,
)
from apps.agents.mi_agent.subgraphs.web_search.state import WebSearchState
from apps.agents.mi_agent.subgraphs.web_search.subgraph_adapter import (
    to_output,
    to_state,
)
from apps.common.streaming.decorators import stream_step


def build_web_subgraph() -> Runnable:
    graph = StateGraph(state_schema=WebSearchState)

    graph.add_node("search_web_node", search_web_node)

    graph.set_entry_point("search_web_node")
    graph.set_finish_point("search_web_node")

    return graph.compile()


_web_subgraph = build_web_subgraph()

runnable_graph: Runnable = (RunnableLambda(to_state) | _web_subgraph | RunnableLambda(to_output)).with_types(
    input_type=MariAgentState,
    output_type=WebSearchOutput,
)


@stream_step(step_key="search_web")
async def run_web(agent_state: MariAgentState) -> WebSearchOutput:
    out: WebSearchOutput = await runnable_graph.ainvoke(agent_state)
    return out
