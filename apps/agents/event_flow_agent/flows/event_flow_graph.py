#   apps/agents/event_flow_agent/flows/event_flow_graph.py
#   kmj20260420월 수정

from __future__ import annotations

from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from apps.agents.event_flow_agent.nodes.analyze_records_with_llm import (
    analyze_records_with_llm_node,
)
from apps.agents.event_flow_agent.nodes.analyze_with_llm import analyze_with_llm_node
from apps.agents.event_flow_agent.nodes.extract_events_with_llm import (
    extract_events_with_llm_node,
)
from apps.agents.event_flow_agent.nodes.read_rdb import read_rdb_node
from apps.agents.event_flow_agent.nodes.read_record_source import (
    read_record_source_node,
)
from apps.agents.event_flow_agent.nodes.save_events import save_events_node
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def build_event_flow_agent() -> Runnable:
    graph = StateGraph(state_schema=EventFlowState)

    graph.add_node("read_record_source", read_record_source_node)
    graph.add_node("analyze_records_with_llm", analyze_records_with_llm_node)
    graph.add_node("extract_events_with_llm", extract_events_with_llm_node)
    graph.add_node("save_events", save_events_node)
    graph.add_node("read_rdb", read_rdb_node)
    graph.add_node("analyze_with_llm", analyze_with_llm_node)

    graph.set_entry_point("read_record_source")

    graph.add_edge("read_record_source", "analyze_records_with_llm")
    graph.add_edge("analyze_records_with_llm", "extract_events_with_llm")
    graph.add_edge("extract_events_with_llm", "save_events")
    graph.add_edge("save_events", "read_rdb")
    graph.add_edge("read_rdb", "analyze_with_llm")
    graph.add_edge("analyze_with_llm", END)

    return graph.compile()


_event_flow_agent = build_event_flow_agent()


def get_event_flow_agent() -> Runnable:
    return _event_flow_agent