from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.agents.scenario_group_agent.state import ScenarioDesignState, state_update
from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import (
    ScenarioReviewState,
)


def _model_or_dict_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


def to_state(parent_state: ScenarioDesignState | Mapping[str, Any]) -> ScenarioReviewState:
    state = (
        parent_state
        if isinstance(parent_state, ScenarioDesignState)
        else ScenarioDesignState.model_validate(parent_state)
    )
    if state.status == "failure":
        return ScenarioReviewState(skip_review=True)
    request_table = state.request_table.model_dump() if state.request_table is not None else {}
    requested_rows = request_table.get("rows", [])
    requested_headers = request_table.get("headers", [])
    return ScenarioReviewState(
        scenario_group_id=state.scenario_group_id,
        group=state.scenario_group.model_dump() if state.scenario_group is not None else {},
        requested_rows=requested_rows,
        requested_headers=requested_headers,
        persisted_scenarios=[_model_or_dict_dump(scenario) for scenario in state.scenarios],
        template_dims=[_model_or_dict_dump(dimension) for dimension in state.dimension_template],
    )


def to_output(subgraph_state: ScenarioReviewState | Mapping[str, Any]) -> dict[str, Any]:
    state = (
        subgraph_state
        if isinstance(subgraph_state, ScenarioReviewState)
        else ScenarioReviewState.model_validate(subgraph_state)
    )
    if state.skip_review:
        return {}
    if state.error:
        return state_update(status="failure", message=state.error, error=state.error)
    if state.report is None:
        return state_update(
            status="failure",
            message="Scenario review report is missing",
            error="Scenario review report is missing",
        )
    report = state.report
    validation_result = {
        "scenario_group_id": state.scenario_group_id,
        "scenario_count": len(state.requested_rows),
        "verdict": report.verdict,
        "summary": report.summary,
        "checks": [check.to_dict() for check in report.checks],
    }
    return state_update(
        is_valid=report.is_valid,
        reason=report.reason,
        validation_result=validation_result,
    )

