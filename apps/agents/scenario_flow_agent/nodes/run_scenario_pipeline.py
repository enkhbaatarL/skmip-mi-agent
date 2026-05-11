"""
Node: Run Scenario Generation Pipeline

Runs the complete 5 stage scenario generation pipeline.
"""
from datetime import datetime
from typing import Dict, Any
import uuid

from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState
from apps.agents.scenario_flow_agent.services.scenario_generation_service import ScenarioGenerationService
from apps.common.logging.decorators import log_node


@log_node
def run_scenario_pipeline(state: ScenarioFlowState) -> Dict[str, Any]:
    """
    Execute complete scenario generation pipeline.
    Uses event_data (loaded from DB) instead of file path.
    
    Args:
        state: Current flow state with event_data from load_event_from_db
        
    Returns:
        State updates with all pipeline results
    """
    if state.event_data is None:
        return {
            "error": "event_data is None. Ensure load_event_from_db ran successfully."
        }
    
    service = ScenarioGenerationService()
    
    # Generate scenario group ID
    scenario_group_id = f"scg_{uuid.uuid4().hex[:10]}"
    
    # Run full pipeline with event dict (loaded from DB)
    result = service.generate_scenario_group_from_event(state.event_data)
    
    return {
        "scenario_group_id": scenario_group_id,
        "template_id": result["template_id"],
        "stage1_context_pack": result["stage1_context_pack"],
        "stage2_dimension_selection": result["stage2_dimension_selection"],
        "stage3_value_selection": result["stage3_value_selection"],
        "stage4_scenario_synthesis": result["stage4_scenario_synthesis"],
        "stage5_validation": result["stage5_validation"],
        "cartesian_total": result["cartesian_total"],
        "filtered_by_compatibility": result["filtered_by_compatibility"],
        "scenario_count": result["scenario_count"],
        "mece_passed": result["mece_passed"],
        "completed_at": datetime.utcnow(),
        "error": None
    }
