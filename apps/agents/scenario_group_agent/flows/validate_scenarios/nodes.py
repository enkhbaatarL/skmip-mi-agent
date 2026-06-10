from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
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
    requested_group_id = (state.request_scenario_group or {}).get("scenario_group_id")
    if requested_group_id != state.scenario_group_id:
        return {
            "status": "failure",
            "error": "Path and body scenarioGroupId do not match",
            "message": "Path and body scenarioGroupId do not match",
        }
    requested_event_id = (state.request_scenario_group or {}).get("mi_event_id")
    requested_event_type_id = (state.request_scenario_group or {}).get(
        "event_type_l2_id"
    )
    if (
        requested_event_id != group["mi_event_id"]
        or requested_event_type_id != group["event_type_l2_id"]
    ):
        return {
            "status": "failure",
            "error": "Body scenarioGroup identifiers do not match persisted group",
            "message": "Body scenarioGroup identifiers do not match persisted group",
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


def validate_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure":
        return {}
    issues: list[str] = []
    seen_dimension_sets: set[tuple[tuple[str, Any], ...]] = set()
    requested_rows = (state.request_table or {}).get("rows", [])
    if not requested_rows:
        issues.append("No scenarios provided")
    scenario_ids = {int(scenario["scenario_id"]) for scenario in state.scenarios}
    for scenario in requested_rows:
        scenario_id = int(scenario["scenario_id"])
        if scenario_id not in scenario_ids:
            issues.append(
                f"scenario_id={scenario_id} does not belong to scenario group"
            )
        dimension_values = scenario.get("cells") or {}
        if not dimension_values:
            issues.append(f"scenario_id={scenario_id} has empty cells")
        dimension_key = tuple(sorted(dimension_values.items()))
        if dimension_key in seen_dimension_sets:
            issues.append(f"scenario_id={scenario_id} duplicates cells")
        seen_dimension_sets.add(dimension_key)

    is_valid = not issues
    reason = "Scenarios are valid" if is_valid else "; ".join(issues)
    validation_result = {
        "scenario_group_id": state.scenario_group_id,
        "scenario_count": len(requested_rows),
        "issues": issues,
    }
    return {
        "is_valid": is_valid,
        "reason": reason,
        "validation_result": validation_result,
    }


def save_validation_result(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        stage="scenario_validated" if state.is_valid else "scenario_created",
        user_id=state.user_id,
    )
    return {
        "scenario_group": group,
        "status": "success",
        "message": "Validation completed",
    }
