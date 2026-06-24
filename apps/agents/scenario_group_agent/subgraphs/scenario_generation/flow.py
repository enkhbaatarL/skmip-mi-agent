from __future__ import annotations

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.generation_stages import (
    REF_QUICK_VALIDATE_MAX_RETRIES,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes import (
    build_context_node,
    quick_validate_node,
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


def _route_after_quick_validate(state: ScenarioGenerationState) -> str:
    if state.skip_generation or state.error:
        return "done"
    if state.validation_feedback is None:
        return "done"
    if state.quick_validate_retry_count > REF_QUICK_VALIDATE_MAX_RETRIES:
        return "done"
    return "retry"


def build_scenario_generation_subgraph() -> Runnable:
    graph = StateGraph(state_schema=ScenarioGenerationState)
    graph.add_node("build_context", build_context_node)
    graph.add_node("select_dimensions", select_dimensions_node)
    graph.add_node("reduce_values", reduce_values_node)
    graph.add_node("synthesize_scenarios", synthesize_scenarios_node)
    graph.add_node("quick_validate", quick_validate_node)
    graph.add_node("validate_scenarios", validate_scenarios_node)
    graph.set_entry_point("build_context")
    graph.add_edge("build_context", "select_dimensions")
    graph.add_edge("select_dimensions", "reduce_values")
    graph.add_edge("reduce_values", "synthesize_scenarios")
    graph.add_edge("synthesize_scenarios", "quick_validate")
    graph.add_conditional_edges(
        "quick_validate",
        _route_after_quick_validate,
        {"retry": "synthesize_scenarios", "done": "validate_scenarios"},
    )
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
