"""
Node: Save Signposts to Database

Saves generated signposts to tmm_signpostm table,
and writes a JSON dump for debugging/reference.
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from apps.agents.signpost_flow_agent.services.signpost_db_service import SignpostDbService
from apps.agents.signpost_flow_agent.state.signpost_flow_state import SignpostFlowState


def save_signposts_to_db(state: SignpostFlowState) -> Dict[str, Any]:
    """
    Save generated signposts to tmm_signpostm.

    Also writes a JSON dump to ./tmp/ for debugging/reference.

    Args:
        state: Current flow state with signposts_generated from run_signpost_pipeline

    Returns:
        State updates
    """
    signposts = state.signposts_generated or []
    if not signposts:
        return {
            "saved_signpost_ids": [],
            "error": None,
        }

    db_service = SignpostDbService()

    # Save to DB
    saved_ids = db_service.save_signposts(signposts)

    # Write JSON file dump for debugging
    mi_event_id = state.mi_event_id or "unknown"
    output_path = Path(f"./tmp/signpost_result_{mi_event_id}.json")

    debug_doc = {
        "mi_event_id": mi_event_id,
        "scenario_group_id": state.scenario_group_id,
        "scenario_results": state.scenario_results,
        "signposts": signposts,
        "saved_signpost_ids": saved_ids,
        "created_at": datetime.utcnow().isoformat(),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(debug_doc, f, ensure_ascii=False, indent=2)

    return {
        "saved_signpost_ids": saved_ids,
        "error": None,
    }