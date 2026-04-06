from __future__ import annotations

from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from apps.agents.mi_agent.nodes.analyze import generate_analysis
from apps.agents.mi_agent.nodes.classify_intent import classify_intent_node
from apps.agents.mi_agent.nodes.planner import planner_node
from apps.agents.mi_agent.nodes.rewrite_query import rewrite_query_node
from apps.agents.mi_agent.nodes.search import search_node
from apps.agents.mi_agent.state.state import MariAgentState


def build_mi_agent() -> Runnable:
    graph = StateGraph(state_schema=MariAgentState)

    graph.add_node("rewrite_query", rewrite_query_node)
    graph.add_node("classify_intent", classify_intent_node)
    graph.add_node("plan", planner_node)
    graph.add_node("search", search_node)
    graph.add_node("analysis", generate_analysis)

    graph.set_entry_point("rewrite_query")
    graph.add_edge("rewrite_query", "classify_intent")
    graph.add_edge("classify_intent", "plan")
    graph.add_edge("plan", "search")
    graph.add_edge("search", "analysis")
    graph.add_edge("analysis", END)

    return graph.compile()


_mari_agent = build_mi_agent()

def get_mi_agent() -> Runnable:
    """컴파일된 MI Agent 그래프(Runnable)를 재사용하기 위한 getter."""
    return _mari_agent