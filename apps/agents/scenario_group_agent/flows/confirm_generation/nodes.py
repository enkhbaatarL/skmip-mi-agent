from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.signpost.service import (
    SignpostService,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState


def load_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.scenario_group_id is None:
        return {
            "status": "failure",
            "error": "scenario_group_id is required",
            "message": "scenario_group_id is required",
        }
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    if group is None:
        return {
            "status": "failure",
            "error": f"Scenario group not found: {state.scenario_group_id}",
            "message": f"Scenario group not found: {state.scenario_group_id}",
        }
    return {"scenario_group": group}


def load_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        return {
            "status": "failure",
            "error": "No scenarios found",
            "message": "No scenarios found",
        }
    return {"scenarios": scenarios}


def load_signposts(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure":
        return {}
    signposts = SignpostService().load_by_scenario_ids(
        [int(s["scenario_id"]) for s in state.scenarios]
    )
    if not signposts:
        return {
            "status": "failure",
            "error": "No signposts found",
            "message": "No signposts found",
        }
    return {"signposts": signposts}


def confirm_outputs(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    if state.request_scenario_group is None or state.request_table is None:
        return {
            "status": "failure",
            "message": "scenarioGroup and table are required",
            "confirmed": False,
        }
    result = ScenarioGroupService().apply_confirmation(
        state.scenario_group_id,
        state.request_scenario_group,
        state.request_table,
    )
    if result.get("status") != "success":
        return {
            "status": "failure",
            "message": result.get("message", "Confirmation failed"),
            "confirmed": False,
        }
    return {
        "snapshot_id": result["snapshot_id"],
        "scenario_group": result["group"],
        "confirmed": True,
        "status": "success",
        "message": "Generation confirmed",
    }
