from __future__ import annotations

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSearchOutput
from apps.agents.mi_agent.subgraphs.rdb_search.stages.execute.execute_rdb_search import (
    execute_rdb_search_node,
)
from apps.agents.mi_agent.subgraphs.rdb_search.stages.prepare.candidate_tables import (
    select_candidate_tables_node,
)
from apps.agents.mi_agent.subgraphs.rdb_search.stages.prepare.search_queries import (
    prepare_rdb_search_queries_node,
)
from apps.agents.mi_agent.subgraphs.rdb_search.state import RDBSearchState
from apps.agents.mi_agent.subgraphs.rdb_search.subgraph_adapter import to_output, to_state
from apps.common.streaming.decorators import stream_step


def build_rdb_subgraph() -> Runnable:
    graph = StateGraph(state_schema=RDBSearchState)

    graph.add_node("prepare_rdb_search_queries_node", prepare_rdb_search_queries_node)
    graph.add_node("select_candidate_tables_node", select_candidate_tables_node)
    graph.add_node("execute_rdb_search_node", execute_rdb_search_node)

    graph.set_entry_point("prepare_rdb_search_queries_node")
    graph.add_edge("prepare_rdb_search_queries_node", "select_candidate_tables_node")
    graph.add_edge("select_candidate_tables_node", "execute_rdb_search_node")
    graph.set_finish_point("execute_rdb_search_node")

    return graph.compile()


_rdb_subgraph = build_rdb_subgraph()

runnable_graph: Runnable = (
    RunnableLambda(to_state) | _rdb_subgraph | RunnableLambda(to_output)
).with_types(
    input_type=MariAgentState,
    output_type=RDBSearchOutput,
)


@stream_step(step_key="search_rdb")
async def run_rdb(agent_state: MariAgentState) -> RDBSearchOutput:
    out: RDBSearchOutput = await runnable_graph.ainvoke(agent_state)
    return out
