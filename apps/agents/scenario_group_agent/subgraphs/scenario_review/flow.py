from __future__ import annotations

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes import (
    run_review_node,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import (
    ScenarioReviewState,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.subgraph_adapter import (
    to_output,
    to_state,
)


def build_scenario_review_subgraph() -> Runnable:
    graph = StateGraph(state_schema=ScenarioReviewState)
    graph.add_node("run_review", run_review_node)
    graph.set_entry_point("run_review")
    graph.set_finish_point("run_review")
    return graph.compile()


_scenario_review_subgraph = build_scenario_review_subgraph()

scenario_review_runnable: Runnable = (
    RunnableLambda(to_state)
    | _scenario_review_subgraph
    | RunnableLambda(to_output)
).with_types(
    input_type=ScenarioDesignState,
    output_type=dict[str, object],
)
