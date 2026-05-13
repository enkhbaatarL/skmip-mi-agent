"""
Signpost Flow Agent Graph

LangGraph StateGraph definition for signpost generation pipeline.
Follows same architecture pattern as scenario_flow_agent.
"""
from langgraph.graph import StateGraph

from apps.agents.signpost_flow_agent.state.signpost_flow_state import SignpostFlowState
from apps.agents.signpost_flow_agent.nodes.load_event_from_db import load_event_from_db
from apps.agents.signpost_flow_agent.nodes.run_signpost_pipeline import run_signpost_pipeline
from apps.agents.signpost_flow_agent.nodes.save_signposts_to_db import save_signposts_to_db


def build_signpost_flow_graph() -> StateGraph:
    """Build signpost generation pipeline graph"""
    
    builder = StateGraph(SignpostFlowState)
    
    # Add nodes
    builder.add_node("load_event_from_db", load_event_from_db)
    builder.add_node("run_signpost_pipeline", run_signpost_pipeline)
    builder.add_node("save_signposts_to_db", save_signposts_to_db)
    
    # Set entry point
    builder.set_entry_point("load_event_from_db")
    
    # Define edges (sequential execution)
    builder.add_edge("load_event_from_db", "run_signpost_pipeline")
    builder.add_edge("run_signpost_pipeline", "save_signposts_to_db")
    
    # Set end node
    builder.set_finish_point("save_signposts_to_db")
    
    graph = builder.compile()
    
    return graph


signpost_flow_graph = build_signpost_flow_graph()