"""
Node: Load Event from Database

Loads base event from tmm_mi_mievent_m by mi_event_id,
replacing the previous file-based loader.
"""
from typing import Dict, Any

from apps.agents.scenario_flow_agent.services.scenario_db_service import ScenarioDbService
from apps.agents.scenario_flow_agent.state.scenario_flow_state import ScenarioFlowState
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger as app_logger


@log_tool
def load_event_from_db(state: ScenarioFlowState) -> Dict[str, Any]:
    """
    Load base event from database by mi_event_id.

    Args:
        state: Current flow state containing mi_event_id

    Returns:
        State updates with loaded event data
    """
    mi_event_id = state.mi_event_id

    if mi_event_id is None:
        return {
            "error": "mi_event_id is required but not provided in state"
        }

    try:
        db_service = ScenarioDbService()
        event = db_service.load_event(int(mi_event_id))
    except Exception as e:
        app_logger.error(
            "[SCENARIO_BATCH] load_event_from_db failed for mi_event_id=%s: %s",
            mi_event_id,
            e,
            exc_info=True,
        )
        return {
            "error": f"Failed to load event from DB: {e}"
        }

    if event is None:
        return {
            "error": f"Event not found for mi_event_id={mi_event_id}"
        }

    return {
        "event_data": event,
        "mi_event_id": str(mi_event_id),
        "event_type_l1_l2": (
            f"{event.get('event_type', {}).get('level_1_code', '')}"
            f"::{event.get('event_type', {}).get('level_2_code', '')}"
        ),
        "error": None
    }