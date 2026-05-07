"""
Node: Load Event from File

Stage 1 file based input loader.
Reads event JSON from file path.
"""
import json
from typing import Dict, Any

from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState


def load_event_from_file(state: ScenarioFlowState) -> Dict[str, Any]:
    """
    Load base event from JSON file.
    
    Args:
        state: Current flow state
        
    Returns:
        State updates
    """
    event_file_path = state.event_file_path
    
    with open(event_file_path, "r", encoding="utf-8") as f:
        event = json.load(f)
    
    return {
        "mi_event_id": event.get("mi_event_id"),
        "event_type_l1_l2": f"{event.get('event_type', {}).get('level_1_code')}::{event.get('event_type', {}).get('level_2_code')}",
        "event_file_path": event_file_path,
        "error": None
    }