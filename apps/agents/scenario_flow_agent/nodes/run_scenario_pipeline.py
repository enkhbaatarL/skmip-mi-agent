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
    
    Args:
        state: Current flow state
        
    Returns:
        State updates with all pipeline results
    """
    service = ScenarioGenerationService()
    
    # Generate scenario group ID
    scenario_group_id = f"scg_{uuid.uuid4().hex[:10]}"
    
    # Run full pipeline
    result = service.generate_scenario_group(state.event_file_path)
    
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