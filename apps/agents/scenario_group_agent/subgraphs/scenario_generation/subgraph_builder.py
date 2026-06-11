from __future__ import annotations

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.stages import (
    build_context_node,
    reduce_values_node,
    select_dimensions_node,
    synthesize_scenarios_node,
    validate_scenarios_node,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.state import (
    ScenarioGenerationState,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.subgraph_adapter import (
    to_output,
    to_state,
)


def build_scenario_generation_subgraph() -> Runnable:
    graph = StateGraph(state_schema=ScenarioGenerationState)
    graph.add_node("build_context", build_context_node)
    graph.add_node("select_dimensions", select_dimensions_node)
    graph.add_node("reduce_values", reduce_values_node)
    graph.add_node("synthesize_scenarios", synthesize_scenarios_node)
    graph.add_node("validate_scenarios", validate_scenarios_node)
    graph.set_entry_point("build_context")
    graph.add_edge("build_context", "select_dimensions")
    graph.add_edge("select_dimensions", "reduce_values")
    graph.add_edge("reduce_values", "synthesize_scenarios")
    graph.add_edge("synthesize_scenarios", "validate_scenarios")
    graph.set_finish_point("validate_scenarios")
    return graph.compile()


_scenario_generation_subgraph = build_scenario_generation_subgraph()

scenario_generation_runnable: Runnable = (
    RunnableLambda(to_state)
    | _scenario_generation_subgraph
    | RunnableLambda(to_output)
).with_types(
    input_type=ScenarioDesignState,
    output_type=dict[str, object],
)
