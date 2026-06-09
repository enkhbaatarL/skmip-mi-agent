from __future__ import annotations

from typing import Any

from apps.agents.scenario_design_agent.persistence.scenario.service import ScenarioService
from apps.agents.scenario_design_agent.persistence.scenario_group.service import ScenarioGroupService
from apps.agents.scenario_design_agent.state import ScenarioDesignState


def load_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.scenario_group_id is None:
        return {"status": "failure", "error": "scenario_group_id is required", "message": "scenario_group_id is required"}
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
        return {"status": "failure", "error": "No scenarios found", "message": "No scenarios found"}
    return {"scenarios": scenarios}


def validate_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure":
        return {}
    issues: list[str] = []
    seen_dimension_sets: set[tuple[tuple[str, Any], ...]] = set()
    for scenario in state.scenarios:
        if not scenario.get("title"):
            issues.append(f"scenario_id={scenario.get('scenario_id')} has empty title")
        dimension_values = scenario.get("dimension_values") or {}
        if not dimension_values:
            issues.append(f"scenario_id={scenario.get('scenario_id')} has empty dimension_values")
        dimension_key = tuple(sorted(dimension_values.items()))
        if dimension_key in seen_dimension_sets:
            issues.append(f"scenario_id={scenario.get('scenario_id')} duplicates dimension_values")
        seen_dimension_sets.add(dimension_key)

    is_valid = not issues
    reason = "Scenarios are valid" if is_valid else "; ".join(issues)
    validation_result = {
        "scenario_group_id": state.scenario_group_id,
        "scenario_count": len(state.scenarios),
        "issues": issues,
    }
    return {"is_valid": is_valid, "reason": reason, "validation_result": validation_result}


def save_validation_result(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    status_code = "검증완료" if state.is_valid else "검토필요"
    ScenarioService().update_judgment_status(state.scenario_group_id, status_code)
    return {
        "status": "success",
        "message": "Validation completed",
    }
