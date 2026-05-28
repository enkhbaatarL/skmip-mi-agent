from datetime import datetime
from typing import Any, Dict

from apps.agents.signpost_flow_agent.services.signpost_db_service import SignpostDbService
from apps.agents.signpost_flow_agent.state.signpost_flow_state import SignpostFlowState
from apps.agents.scenario_agent.services.scenario_db_service import ScenarioDbService


def load_event_from_db(state: SignpostFlowState) -> Dict[str, Any]:
    """
    Load base event info and scenarios from database by mi_event_id.

    Args:
        state: Current flow state containing mi_event_id

    Returns:
        State updates with loaded event data and scenarios
    """
    mi_event_id = state.mi_event_id

    if mi_event_id is None:
        return {
            "error": "mi_event_id is required but not provided in state"
        }

    mi_event_id_int = int(mi_event_id)

    # Load base event data (for C1_base_event construction)
    scenario_db = ScenarioDbService()
    event = scenario_db.load_event(mi_event_id_int)

    if event is None:
        return {
            "error": f"Event not found for mi_event_id={mi_event_id}"
        }

    # Load scenarios and scenario_group_id from tmm_scenariom
    signpost_db = SignpostDbService()
    scenario_group_id, scenarios = signpost_db.load_scenarios_for_event(mi_event_id_int)

    if not scenarios:
        return {
            "error": f"No scenarios found for mi_event_id={mi_event_id}. Generate scenarios first."
        }

    # Build a simplified C1_base_event dict for the pipeline
    event_type = event.get("event_type", {}) or {}
    l1 = event_type.get("level_1_code", "")
    l2 = event_type.get("level_2_code", "")
    event_type_l1_l2 = f"{l1}::{l2}" if l1 and l2 else ""

    stage1_context_pack = {
        "C1_base_event": {
            "event_id": event.get("mi_event_id", str(mi_event_id)),
            "title": event.get("event_title_ko", ""),
            "event_type_l1_l2": event_type_l1_l2,
            "summary": event.get("one_line_summary", ""),
            "driver": event.get("detail_analysis", "")[:160] if event.get("detail_analysis") else "",
        },
        "C2_linked_records": {"window_days": 30, "records": []},
        "C3_historical_analogs": [],
        "C4_related_events": [],
    }

    return {
        "event_data": event,
        "scenario_group_id": scenario_group_id or f"sgp_{mi_event_id_int}",
        "scenarios_from_db": scenarios,
        "stage1_context_pack": stage1_context_pack,
        "error": None,
    }