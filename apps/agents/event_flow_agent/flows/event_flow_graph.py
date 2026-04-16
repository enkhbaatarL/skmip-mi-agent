#   agents/event_flow_agent/flows/event_flow_graph.py

from __future__ import annotations

from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from apps.agents.event_flow_agent.nodes.analyze_with_llm import analyze_with_llm_node
from apps.agents.event_flow_agent.nodes.read_rdb import read_rdb_node
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def build_event_flow_agent() -> Runnable:
    graph = StateGraph(state_schema=EventFlowState)

    graph.add_node("read_rdb", read_rdb_node)
    graph.add_node("analyze_with_llm", analyze_with_llm_node)

    graph.set_entry_point("read_rdb")
    graph.add_edge("read_rdb", "analyze_with_llm")
    graph.add_edge("analyze_with_llm", END)

    return graph.compile()


_event_flow_agent = build_event_flow_agent()


def get_event_flow_agent() -> Runnable:
    return _event_flow_agent