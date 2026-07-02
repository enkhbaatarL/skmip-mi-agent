from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.state import ScenarioDesignState, state_update
from apps.agents.scenario_group_agent.subgraphs.scenario_review.review_stages import (
    generate_new_dimension_values,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
    ScenarioStatus,
)
from apps.persistence.scenario.service import (
    ScenarioService,
)
from apps.persistence.scenario_group.service import (
    ScenarioGroupService,
)


def _build_dimension_generation_rows(
    rows: list[dict[str, Any]],
    persisted_scenarios: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    persisted_by_id = {
        int(scenario["scenario_id"]): scenario
        for scenario in persisted_scenarios
        if scenario.get("scenario_id") is not None
    }
    generation_rows: list[dict[str, Any]] = []
    for row in rows:
        generation_row = dict(row)
        if row.get("scenario_id") is not None:
            persisted = persisted_by_id.get(int(row["scenario_id"])) or {}
            if not generation_row.get("title"):
                generation_row["title"] = persisted.get("title") or ""
            generation_row["narrative"] = persisted.get("narrative") or ""
        generation_rows.append(generation_row)
    return generation_rows


def _model_or_dict_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump()
    return dict(value)


def _assert_group_owner(group: dict[str, Any], user_id: int | None) -> None:
    request_usr_id = group.get("request_usr_id")
    if request_usr_id is not None and request_usr_id != user_id:
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"이미 사용자 {request_usr_id}가 점유하고 있습니다.",
        )


def load_scenario_group(state: ScenarioDesignState) -> dict[str, object]:
    if state.scenario_group_id is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="scenario_group_id is required")
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    if group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Scenario group not found: {state.scenario_group_id}")
    _assert_group_owner(group, state.user_id)

    return {"scenario_group": group}


def load_scenarios(state: ScenarioDesignState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="No scenarios found")
    if state.scenario_group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Scenario group is required")
    try:
        dimension_template = ScenarioService().load_dimension_template(
            int(state.scenario_group.event_type_l2_id),
        )
    except (KeyError, ValueError):
        dimension_template = []
    return {"scenarios": scenarios, "dimension_template": dimension_template}


async def generate_dimension_values(state: ScenarioDesignState) -> dict[str, object]:
    if state.status == "failure":
        return {}

    request_table = (
        state.request_table.model_dump(exclude_unset=True)
        if state.request_table is not None
        else {}
    )
    headers = request_table.get("headers") or []
    rows = request_table.get("rows") or []
    header_key_list = [str(header["key"]) for header in headers]
    header_keys = set(header_key_list)

    if state.scenario_group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="Scenario group is required")
    event_type_l2_id = int(state.scenario_group.event_type_l2_id)
    template = ScenarioService().load_scenario_template(event_type_l2_id)

    # 시나리오화 템플릿(event type 기준)에서 필수 분기(required=True)와
    # 선택 분기(required=False)를 식별한다.
    required_keys = [
        dimension.dimension_id
        for dimension in template.dimensions
        if dimension.required
    ]
    optional_keys = {
        dimension.dimension_id
        for dimension in template.dimensions
        if not dimension.required
    }
    label_by_key = {
        dimension.dimension_id: dimension.label_ko
        for dimension in template.dimensions
    }

    # 필수 분기는 화면에서 삭제가 막혀 있으므로 헤더(컬럼)에도 반드시 존재해야 한다.
    missing_required = [key for key in required_keys if key not in header_keys]
    if missing_required:
        missing_labels = ", ".join(
            label_by_key.get(key, key) for key in missing_required
        )
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail=f"필수 분기 누락: {missing_labels}",
        )

    required_header_keys = [
        key for key in header_key_list if key in set(required_keys)
    ]

    # 필수 분기(required=True) 값은 기존/신규 시나리오 여부와 무관하게 비워 둘 수 없다.
    #  - 신규 시나리오: 필수 분기 값을 반드시 입력해야 함.
    #  - 기존 시나리오: 필수 분기 값을 사용자가 null 로 비우는 것은 미허용.
    # 선택 분기(required=False)의 null 은 아래에서 Agent 가 채우므로 허용한다(부분 null 포함).
    for row in rows:
        cells = row.get("cells") or {}
        missing_required_values = [
            key for key in required_header_keys if cells.get(key) is None
        ]
        if not missing_required_values:
            continue
        missing_labels = ", ".join(
            label_by_key.get(key, key) for key in missing_required_values
        )
        title = row.get("title") or "(제목 없음)"
        if row.get("scenario_id") is None:
            detail = (
                f"새로 추가된 시나리오 '{title}'의 필수 분기 값을 모두 입력해야 합니다. "
                f"누락: {missing_labels}"
            )
        else:
            detail = (
                f"시나리오 '{title}'의 필수 분기 값은 비워 둘 수 없습니다. "
                f"누락: {missing_labels}"
            )
        raise MIBaseError(
            ErrorCode.SCENARIO_VALIDATION_INPUT_ERROR,
            detail=detail,
        )

    # 선택 분기(required=False)의 null 만 Agent 가 채운다(부분 null 포함).
    # 필수 분기 null 은 위에서 이미 에러로 걸러졌다.
    fillable_dims = [
        key
        for key in header_key_list
        if key in optional_keys
        and any((row.get("cells") or {}).get(key) is None for row in rows)
    ]
    if fillable_dims:
        generated = await generate_new_dimension_values(
            template,
            _build_dimension_generation_rows(
                rows,
                [_model_or_dict_dump(scenario) for scenario in state.scenarios],
            ),
            fillable_dims,
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

    return state_update(request_table=request_table)


def save_validation_result(state: ScenarioDesignState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    ScenarioService().update_status(state.scenario_group_id, ScenarioStatus.CREATING.value)
    next_stage = (
        ScenarioGroupStage.SCENARIO_VALIDATED
        if state.is_valid
        else ScenarioGroupStage.SCENARIO_CREATED
    )
    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        status=ScenarioGroupStatus.CREATING,
        stage=next_stage,
        user_id=state.user_id,
    )
    if group is None:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario group update failed")
    return state_update(
        scenario_group=group,
        status="success",
        message="Validation completed",
    )
