from __future__ import annotations

from functools import lru_cache

from langchain_core.runnables import Runnable
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes import (
    RunReviewNode,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import (
    ScenarioReviewState,
)


def build_scenario_review_subgraph() -> Runnable:
    graph = StateGraph(state_schema=ScenarioReviewState)
    graph.add_node("run_review", RunReviewNode())
    graph.set_entry_point("run_review")
    graph.set_finish_point("run_review")
    return graph.compile()


@lru_cache(maxsize=1)
def get_scenario_review_subgraph() -> Runnable:
    return build_scenario_review_subgraph()
