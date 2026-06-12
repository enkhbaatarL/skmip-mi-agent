from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.flows.validate_scenarios.review import (
    build_context,
    run_review,
)
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
    try:
        dimension_template = ScenarioService().load_dimension_template(
            int(state.scenario_group["event_type_l2_id"]),
        )
    except (KeyError, ValueError):
        dimension_template = []
    return {
        "scenarios": scenarios,
        "dimension_template": dimension_template,
    }


async def validate_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure":
        return {}
    requested_rows = (state.request_table or {}).get("rows", [])
    context = build_context(
        group=state.scenario_group or {},
        requested_rows=requested_rows,
        persisted_scenarios=state.scenarios,
        template_dims=state.dimension_template,
    )
    report = await run_review(context)
    validation_result = {
        "scenario_group_id": state.scenario_group_id,
        "scenario_count": len(requested_rows),
        "verdict": report.verdict,
        "summary": report.summary,
        "checks": [check.to_dict() for check in report.checks],
    }
    return {
        "is_valid": report.is_valid,
        "reason": report.reason,
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
