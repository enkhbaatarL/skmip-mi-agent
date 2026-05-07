"""
Scenario Flow Agent Graph

LangGraph StateGraph definition for scenario generation pipeline.
Follows same architecture pattern as event_flow_agent.
"""
from langgraph.graph import StateGraph

from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState
from apps.agents.scenario_flow_agent.nodes.load_event_from_file import load_event_from_file
from apps.agents.scenario_flow_agent.nodes.run_scenario_pipeline import run_scenario_pipeline
from apps.agents.scenario_flow_agent.nodes.save_result_to_file import save_result_to_file


def build_scenario_flow_graph() -> StateGraph:
    """Build scenario generation pipeline graph"""
    
    builder = StateGraph(ScenarioFlowState)
    
    # Add nodes
    builder.add_node("load_event_from_file", load_event_from_file)
    builder.add_node("run_scenario_pipeline", run_scenario_pipeline)
    builder.add_node("save_result_to_file", save_result_to_file)
    
    # Set entry point
    builder.set_entry_point("load_event_from_file")
    
    # Define edges (sequential execution for Stage 1)
    builder.add_edge("load_event_from_file", "run_scenario_pipeline")
    builder.add_edge("run_scenario_pipeline", "save_result_to_file")
    
    # Set end node
    builder.set_finish_point("save_result_to_file")
    
    graph = builder.compile()
    
    return graph


scenario_flow_graph = build_scenario_flow_graph()