from __future__ import annotations

from functools import lru_cache

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.subgraphs.signpost_generation.nodes import (
    AssembleSignpostsNode,
    DirectionStrengthNode,
    KeywordHintsNode,
    ObservabilityFilterNode,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)


def build_signpost_generation_subgraph() -> Runnable:
    graph = StateGraph(state_schema=SignpostGenerationState)
    graph.add_node("observability_filter", ObservabilityFilterNode())
    graph.add_node("assign_direction_strength", DirectionStrengthNode())
    graph.add_node("mint_keyword_hints", KeywordHintsNode())
    graph.add_node("assemble_signposts", AssembleSignpostsNode())
    graph.set_entry_point("observability_filter")
    graph.add_edge("observability_filter", "assign_direction_strength")
    graph.add_edge("assign_direction_strength", "mint_keyword_hints")
    graph.add_edge("mint_keyword_hints", "assemble_signposts")
    graph.set_finish_point("assemble_signposts")
    return graph.compile()


@lru_cache(maxsize=1)
def get_signpost_generation_subgraph() -> Runnable:
    return build_signpost_generation_subgraph()
