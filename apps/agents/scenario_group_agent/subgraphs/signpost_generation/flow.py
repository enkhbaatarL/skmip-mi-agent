from __future__ import annotations

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.subgraphs.signpost_generation.nodes import (
    assemble_signposts_node,
    direction_strength_node,
    keyword_hints_node,
    observability_filter_node,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.subgraph_adapter import (
    to_output,
    to_state,
)


def build_signpost_generation_subgraph() -> Runnable:
    graph = StateGraph(state_schema=SignpostGenerationState)
    graph.add_node("observability_filter", observability_filter_node)
    graph.add_node("assign_direction_strength", direction_strength_node)
    graph.add_node("mint_keyword_hints", keyword_hints_node)
    graph.add_node("assemble_signposts", assemble_signposts_node)
    graph.set_entry_point("observability_filter")
    graph.add_edge("observability_filter", "assign_direction_strength")
    graph.add_edge("assign_direction_strength", "mint_keyword_hints")
    graph.add_edge("mint_keyword_hints", "assemble_signposts")
    graph.set_finish_point("assemble_signposts")
    return graph.compile()


_signpost_generation_subgraph = build_signpost_generation_subgraph()

signpost_generation_runnable: Runnable = (
    RunnableLambda(to_state)
    | _signpost_generation_subgraph
    | RunnableLambda(to_output)
).with_types(
    input_type=dict[str, object],
    output_type=dict[str, object],
)
