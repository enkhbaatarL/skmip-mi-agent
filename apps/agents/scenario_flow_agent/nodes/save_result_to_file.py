"""
Node: Save Result to File

Writes scenario generation result to output JSON file.
"""
from typing import Dict, Any
from pathlib import Path

from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState
from apps.agents.scenario_flow_agent.services.scenario_generation_service import ScenarioGenerationService


def save_result_to_file(state: ScenarioFlowState) -> Dict[str, Any]:
    """
    Save complete scenario result to JSON file.
    
    Args:
        state: Current flow state
        
    Returns:
        State updates
    """
    service = ScenarioGenerationService()
    
    # Build output path
    mi_event_id = state.mi_event_id
    output_path = str(Path("./tmp/") / f"stage_result_{mi_event_id}.json")
    
    # Build complete result document
    result = {
        "scenario_group_id": state.scenario_group_id,
        "created_at": state.completed_at.isoformat(),
        "stage1_context_pack": state.stage1_context_pack,
        "stage2_dimension_selection": state.stage2_dimension_selection,
        "stage3_value_selection": state.stage3_value_selection,
        "stage4_scenario_synthesis": state.stage4_scenario_synthesis,
        "stage5_validation": state.stage5_validation,
        "cartesian_total": state.cartesian_total,
        "filtered_by_compatibility": state.filtered_by_compatibility,
        "scenario_count": state.scenario_count,
        "mece_passed": state.mece_passed,
        "mi_event_id": state.mi_event_id,
        "event_type_l1_l2": state.event_type_l1_l2,
        "template_id": state.template_id
    }
    
    service.save_result(result, output_path)
    
    return {
        "output_file_path": output_path,
        "error": None
    }