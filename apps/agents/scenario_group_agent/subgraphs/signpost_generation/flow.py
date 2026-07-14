from __future__ import annotations

from functools import lru_cache

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.subgraphs.signpost_generation.nodes import (
    AssembleSignpostsNode,
    EnrichSignpostsNode,
    ObservabilityFilterNode,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)
from apps.common.tracing.context import TraceContext


def build_signpost_generation_subgraph() -> Runnable:
    graph = StateGraph(state_schema=SignpostGenerationState, context_schema=TraceContext)
    graph.add_node("observability_filter", ObservabilityFilterNode())
    graph.add_node("enrich_signposts", EnrichSignpostsNode())
    graph.add_node("assemble_signposts", AssembleSignpostsNode())
    graph.set_entry_point("observability_filter")
    graph.add_edge("observability_filter", "enrich_signposts")
    graph.add_edge("enrich_signposts", "assemble_signposts")
    graph.set_finish_point("assemble_signposts")
    return graph.compile()


@lru_cache(maxsize=1)
def get_signpost_generation_subgraph() -> Runnable:
    return build_signpost_generation_subgraph()
