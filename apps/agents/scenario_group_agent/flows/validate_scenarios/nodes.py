from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.flows.validate_scenarios.review import (
    build_context,
    generate_new_dimension_values,
    run_review,
)
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


def _assert_group_owner(group: dict[str, Any], user_id: int | None) -> None:
    request_usr_id = group.get("request_usr_id")
    if request_usr_id is not None and request_usr_id != user_id:
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"이미 사용자 {request_usr_id}가 점유하고 있습니다.",
        )


def load_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.scenario_group_id is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="scenario_group_id is required")
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    if group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Scenario group not found: {state.scenario_group_id}")
    _assert_group_owner(group, state.user_id)

    return {"scenario_group": group}


def load_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="No scenarios found")
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


async def generate_dimension_values(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure":
        return {}

    request_table = state.request_table or {}
    headers = request_table.get("headers") or []
    rows = request_table.get("rows") or []
    header_keys = {str(header["key"]) for header in headers}

    event_type_l2_id = int((state.scenario_group or {})["event_type_l2_id"])
    template = ScenarioService().load_scenario_template(event_type_l2_id)

    required_keys = [
        dimension.dimension_id
        for dimension in template.dimensions
        if dimension.required
    ]
    label_by_key = {
        dimension.dimension_id: dimension.label_ko
        for dimension in template.dimensions
    }
    missing_required = [key for key in required_keys if key not in header_keys]
    if missing_required:
        missing_labels = ", ".join(
            label_by_key.get(key, key) for key in missing_required
        )
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail=f"필수 dimension 누락: {missing_labels}",
        )

    new_dimensions = [
        key
        for key in header_keys
        if rows and all((row.get("cells") or {}).get(key) is None for row in rows)
    ]

    for row in rows:
        if row.get("scenario_id") is not None:
            continue
        cells = row.get("cells") or {}
        missing_cells = [
            key
            for key, value in cells.items()
            if value is None and key not in new_dimensions
        ]
        if missing_cells:
            missing_labels = ", ".join(
                label_by_key.get(key, key) for key in missing_cells
            )
            title = row.get("title") or "(제목 없음)"
            raise MIBaseError(
                ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
                detail=(
                    f"새로 추가된 시나리오 '{title}'의 값을 모두 입력해야 합니다. "
                    f"누락: {missing_labels}"
                ),
            )

    if new_dimensions:
        generated = await generate_new_dimension_values(
            template,
            rows,
            new_dimensions,
        )
        for index, row in enumerate(rows):
            values = generated.get(index) or {}
            if not values:
                continue
            cells = row.get("cells")
            if cells is None:
                cells = {}
                row["cells"] = cells
            for key, value in values.items():
                if cells.get(key) is None:
                    cells[key] = value

    return {"request_table": request_table}


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
    ScenarioService().update_status(state.scenario_group_id, "creating")
    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        status="creating",
        stage="scenario_validated",
        user_id=state.user_id,
    )
    return {
        "scenario_group": group,
        "status": "success",
        "message": "Validation completed",
    }
