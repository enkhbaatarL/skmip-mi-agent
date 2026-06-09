from __future__ import annotations

from typing import Any

from apps.agents.scenario_design_agent.persistence.event.service import EventService
from apps.agents.scenario_design_agent.persistence.scenario.service import ScenarioService
from apps.agents.scenario_design_agent.persistence.scenario_group.service import ScenarioGroupService
from apps.agents.scenario_design_agent.state import ScenarioDesignState


def load_event(state: ScenarioDesignState) -> dict[str, Any]:
    if state.mi_event_id is None:
        return {"status": "failure", "error": "mi_event_id is required", "message": "mi_event_id is required"}
    event = EventService().load_event(state.mi_event_id)
    if event is None:
        return {
            "status": "failure",
            "error": f"Event not found for mi_event_id={state.mi_event_id}",
            "message": f"Event not found for mi_event_id={state.mi_event_id}",
        }
    return {"event_data": event}


def check_existing_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.mi_event_id is None:
        return {}
    existing = ScenarioGroupService().load_by_mi_event_id(state.mi_event_id)
    if existing is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(existing["scenario_group_id"])
    return {
        "scenario_group_id": existing["scenario_group_id"],
        "scenario_group": existing,
        "scenarios": scenarios,
        "status": "already_exist",
        "message": "Scenario group already exists",
    }


def run_scenario_generation(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.event_data is None:
        return {"status": "failure", "error": "event_data is required", "message": "event_data is required"}
    from apps.agents.scenario_agent.services.scenario_generation_service import ScenarioGenerationService

    result = ScenarioGenerationService().generate_scenario_group_from_event(state.event_data)
    return {"scenario_result": result}


def save_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.event_data is None or state.scenario_result is None:
        return {"status": "failure", "error": "scenario_result is required", "message": "scenario_result is required"}

    stage2 = state.scenario_result.get("stage2_dimension_selection", {}) or {}
    stage4 = state.scenario_result.get("stage4_scenario_synthesis", {}) or {}
    selected_dimensions = stage2.get("selected_dimensions", []) or []
    dimension_selected = [
        item.get("dimension_id")
        for item in selected_dimensions
        if isinstance(item, dict) and item.get("dimension_id")
    ]
    payload = {
        "mi_event_id": int(state.event_data["mi_event_id"]),
        "event_type_l2_id": int(state.event_data["event_type_l2_id"]),
        "title": (state.event_data.get("event_title_ko") or f"Scenario group {state.event_data['mi_event_id']}")[:255],
        "summary": state.event_data.get("one_line_summary"),
        "description": state.event_data.get("detail_analysis"),
        "dimension_selected": dimension_selected,
        "scenario_count": len(stage4.get("scenarios", []) or []),
    }
    scenario_group_id = ScenarioGroupService().create_group(payload)
    scenario_result = dict(state.scenario_result)
    scenario_result["scenario_group_id"] = scenario_group_id
    return {"scenario_group_id": scenario_group_id, "scenario_result": scenario_result}


def save_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.scenario_group_id is None or state.scenario_result is None:
        return {"status": "failure", "error": "scenario_group_id is required", "message": "scenario_group_id is required"}
    saved_ids = ScenarioService().save_generated_scenarios(state.scenario_group_id, state.scenario_result)
    ScenarioGroupService().update_scenario_count(state.scenario_group_id, len(saved_ids))
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    return {
        "saved_scenario_ids": saved_ids,
        "scenarios": scenarios,
        "status": "success",
        "message": f"Created {len(saved_ids)} scenarios",
    }
