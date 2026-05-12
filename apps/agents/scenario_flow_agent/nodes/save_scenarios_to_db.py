"""
Node: Save Scenarios to Database

Saves generated scenarios to tmm_scenariom table,
replacing the previous file-based saver.
Also writes a JSON dump to ./tmp/ for debugging/reference.
"""
import json
from typing import Dict, Any
from pathlib import Path

from apps.agents.scenario_flow_agent.services.scenario_db_service import ScenarioDbService
from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState


def save_scenarios_to_db(state: ScenarioFlowState) -> Dict[str, Any]:
    """
    Save complete scenario results to tmm_scenariom.

    Also writes a JSON dump to ./tmp/ for debugging/reference.

    Args:
        state: Current flow state with pipeline results

    Returns:
        State updates
    """
    db_service = ScenarioDbService()

    # Build complete result document for file dump (optional)
    mi_event_id = state.mi_event_id
    output_path = str(Path("./tmp/") / f"stage_result_{mi_event_id}.json")
    result = {
        "scenario_group_id": state.scenario_group_id,
        "created_at": state.completed_at.isoformat() if state.completed_at else "",
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
        "template_id": state.template_id,
    }

    # Save to DB
    stage4 = result.get("stage4_scenario_synthesis", {}) or {}
    stage5 = result.get("stage5_validation", {}) or {}
    mi_event_id_int = int(state.mi_event_id) if state.mi_event_id else 0

    saved_ids = db_service.save_scenario_group(
        scenario_group_id=state.scenario_group_id,
        mi_event_id=mi_event_id_int,
        stage4=stage4,
        stage5=stage5,
    )

    # Also write JSON file dump for debugging
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return {
        "output_file_path": output_path,
        "saved_scenario_ids": saved_ids,
        "error": None,
    }
