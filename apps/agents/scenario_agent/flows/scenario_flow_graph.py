from langgraph.graph import StateGraph

from apps.agents.scenario_agent.state.scenario_flow_state import ScenarioFlowState
from apps.agents.scenario_agent.nodes.load_event_from_db import load_event_from_db
from apps.agents.scenario_agent.nodes.run_scenario_pipeline import run_scenario_pipeline
from apps.agents.scenario_agent.nodes.save_scenarios_to_db import save_scenarios_to_db


def build_scenario_flow_graph() -> StateGraph:
    """Build scenario generation pipeline graph"""
    
    builder = StateGraph(ScenarioFlowState)
    
    # Add nodes
    builder.add_node("load_event_from_db", load_event_from_db)
    builder.add_node("run_scenario_pipeline", run_scenario_pipeline)
    builder.add_node("save_scenarios_to_db", save_scenarios_to_db)
    
    # Set entry point
    builder.set_entry_point("load_event_from_db")
    
    # Define edges (sequential execution)
    builder.add_edge("load_event_from_db", "run_scenario_pipeline")
    builder.add_edge("run_scenario_pipeline", "save_scenarios_to_db")
    
    # Set end node
    builder.set_finish_point("save_scenarios_to_db")
    
    graph = builder.compile()
    
    return graph


scenario_flow_graph = build_scenario_flow_graph()