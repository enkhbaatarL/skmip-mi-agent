from __future__ import annotations

from apps.agents.scenario_group_agent.persistence.event.service import EventService
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.schemas.domain.scenario_group import (
    ScenarioGroupPayload,
)
from apps.agents.scenario_group_agent.schemas.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState, state_update
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


def _existing_group_state_update(
    scenario_group: ScenarioGroupPayload,
) -> dict[str, object]:
    return {
        "scenario_group_id": scenario_group.scenario_group_id,
        "scenario_group": scenario_group,
    }


def load_event(state: ScenarioDesignState) -> dict[str, object]:
    if state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    event = EventService().load_event(state.mi_event_id)
    if event is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Event not found for mi_event_id={state.mi_event_id}")
    return {"event_data": event}


def check_existing_scenario_group(state: ScenarioDesignState) -> dict[str, object]:
    if state.status == "failure" or state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    existing = ScenarioGroupService().load_by_mi_event_id(state.mi_event_id)
    if existing is None:
        # 새로 생성
        return {}
    if existing.stage == ScenarioGroupStage.READY.value:
        if existing.request_usr_id != state.user_id:
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
                detail=f"시나리오 작성자: {existing.request_usr_id}, 시나리오 그룹 ID: {existing.scenario_group_id}",
            )
        return _existing_group_state_update(existing)
    if existing.status == ScenarioGroupStatus.CREATING.value:
        if existing.request_usr_id == state.user_id:
            raise MIBaseError(
                ErrorCode.SCENARIO_GROUP_ALREADY_CREATED,
                detail=f"초안 생성 완료. 다음 단계를 진행해주세요. 시나리오 그룹 ID: {existing.scenario_group_id}",
            )
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"시나리오 작성자: {existing.request_usr_id}, 시나리오 그룹 ID: {existing.scenario_group_id}",
        )
    raise MIBaseError(
        ErrorCode.SCENARIO_GROUP_ALREADY_CREATED,
        detail=f"시나리오 그룹 ID: {existing.scenario_group_id}",
    )

    # scenarios = ScenarioService().load_by_group_id(existing["scenario_group_id"])
    # return {
    #     "scenario_group_id": existing["scenario_group_id"],
    #     "scenario_group": existing,
    #     "scenarios": scenarios,
    #     "status": "already_exist",
    #     "message": "Scenario group already exists",
    # }


def create_group_record(state: ScenarioDesignState) -> dict[str, object]:
    """Prepare 단계: agent 실행 전 group row를 미리 INSERT해 scenarioGroupId를 확보한다."""
    if state.event_data is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="event_data is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")
    payload = {
        "mi_event_id": int(state.event_data["mi_event_id"]),
        "event_type_l2_id": int(state.event_data["event_type_l2_id"]),
        "request_usr_id": state.user_id,
        "title": (
            state.event_data.get("event_title_ko")
            or f"Scenario group {state.event_data['mi_event_id']}"
        )[:255],
        "summary": state.event_data.get("one_line_summary"),
        "description": None, #initialize
        "dimension_selected": [],
        "scenario_count": 0,
        "status": ScenarioGroupStatus.CREATING.value,
        "stage": ScenarioGroupStage.READY.value,
        "crt_usr_logn_id": state.user_id,
        "mod_usr_logn_id": state.user_id,
    }
    scenario_group_id = ScenarioGroupService().create_group(payload)
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    if group is None:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail="Scenario group not found after creation",
        )
    return {
        "scenario_group_id": scenario_group_id,
        "scenario_group": group,
    }


def save_scenario_group(state: ScenarioDesignState) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.event_data is None or state.scenario_result is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_result is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")

    stage2 = state.scenario_result.get("stage2_dimension_selection", {}) or {}
    stage4 = state.scenario_result.get("stage4_scenario_synthesis", {}) or {}
    scenario_group_metadata = state.scenario_result.get("scenario_group_metadata", {}) or {}
    selected_dimensions = stage2.get("selected_dimensions", []) or []
    dimension_selected = [
        item.get("dim_key")
        for item in selected_dimensions
        if isinstance(item, dict) and item.get("dim_key")
    ]
    payload = {
        "mi_event_id": int(state.event_data["mi_event_id"]),
        "event_type_l2_id": int(state.event_data["event_type_l2_id"]),
        "request_usr_id": state.user_id,
        "title": (
            scenario_group_metadata.get("title")
            or state.event_data.get("event_title_ko")
            or f"Scenario group {state.event_data['mi_event_id']}"
        )[:255],
        "summary": state.event_data.get("one_line_summary"),
        "description": (
            scenario_group_metadata.get("description")
            or state.event_data.get("detail_analysis")
        ),
        "dimension_selected": dimension_selected,
        "scenario_count": len(stage4.get("scenarios", []) or []),
        "status": ScenarioGroupStatus.CREATING.value,
        "stage": ScenarioGroupStage.READY.value,
        "crt_usr_logn_id": state.user_id,
        "mod_usr_logn_id": state.user_id,
    }
    if state.scenario_group_id is not None:
        scenario_group_id = state.scenario_group_id
    else:
        scenario_group_id = ScenarioGroupService().create_group(payload)
    scenario_result = state.scenario_result.model_dump()
    scenario_result["scenario_group_id"] = scenario_group_id
    return state_update(
        scenario_group_id=scenario_group_id,
        scenario_result=scenario_result,
    )


def save_scenarios(state: ScenarioDesignState) -> dict[str, object]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.scenario_group_id is None or state.scenario_result is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")

    stage2 = state.scenario_result.get("stage2_dimension_selection", {}) or {}
    scenario_group_metadata = state.scenario_result.get("scenario_group_metadata", {}) or {}
    selected_dimensions = stage2.get("selected_dimensions", []) or []
    dimension_selected = [
        item.get("dim_key")
        for item in selected_dimensions
        if isinstance(item, dict) and item.get("dim_key")
    ]

    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        status=ScenarioGroupStatus.CREATING,
        stage=ScenarioGroupStage.SCENARIO_CREATED,
        dimension_selected=dimension_selected,
        title=scenario_group_metadata.get("title"),
        description=scenario_group_metadata.get("description"),
        user_id=state.user_id,
    )
    if group is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Fail to save scenarios because scenario group is deleted: {state.scenario_group_id}.",
        )

    saved_ids = ScenarioService().save_generated_scenarios(
        state.scenario_group_id,
        state.scenario_result.model_dump(),
        state.user_id,
    )
    ScenarioGroupService().update_scenario_count(
        state.scenario_group_id, len(saved_ids)
    )
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    return state_update(
        saved_scenario_ids=saved_ids,
        scenario_group=group,
        scenarios=scenarios,
        status="success",
        message=f"Created {len(saved_ids)} scenarios",
    )
