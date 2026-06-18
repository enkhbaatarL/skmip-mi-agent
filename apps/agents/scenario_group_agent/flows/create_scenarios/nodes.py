from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.persistence.event.service import EventService
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.agents.scenario_group_agent.schemas.enums import ScenarioGroupStatus

def load_event(state: ScenarioDesignState) -> dict[str, Any]:
    if state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    event = EventService().load_event(state.mi_event_id)
    if event is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Event not found for mi_event_id={state.mi_event_id}")
    return {"event_data": event}


def check_existing_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status == "failure" or state.mi_event_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="mi_event_id is required")
    existing = ScenarioGroupService().load_by_mi_event_id(state.mi_event_id)
    if existing is None:
        # 새로 생성
        return {}
    if existing.status == "ready":
        # async API로 create scenario group 요청했는데, 실패해서 다시 시도했을 경우
        return {}
    if existing.status == ScenarioGroupStatus.CREATING :
        if existing.request_usr_id == state.user_id:
            raise MIBaseError(ErrorCode.SCENARIO_GROUP_ALREADY_CREATED, detail="초안 생성 완료. 다음 단계를 진행해주세요.")
        raise MIBaseError(ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT, detail=f"시나리오 작성자: {existing.request_usr_id}")
    else:
        raise MIBaseError(ErrorCode.SCENARIO_GROUP_ALREADY_CREATED)
    
    # scenarios = ScenarioService().load_by_group_id(existing["scenario_group_id"])
    # return {
    #     "scenario_group_id": existing["scenario_group_id"],
    #     "scenario_group": existing,
    #     "scenarios": scenarios,
    #     "status": "already_exist",
    #     "message": "Scenario group already exists",
    # }


def create_group_record(state: ScenarioDesignState) -> dict[str, Any]:
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
        "description": state.event_data.get("detail_analysis"),
        "dimension_selected": [],
        "scenario_count": 0,
        "status": "creating",
        "stage": "ready",
        "crt_usr_logn_id": state.user_id,
        "mod_usr_logn_id": state.user_id,
    }
    scenario_group_id = ScenarioGroupService().create_group(payload)
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    return {"scenario_group_id": scenario_group_id, "scenario_group": group}


def save_scenario_group(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.event_data is None or state.scenario_result is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_result is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")

    stage2 = state.scenario_result.get("stage2_dimension_selection", {}) or {}
    stage4 = state.scenario_result.get("stage4_scenario_synthesis", {}) or {}
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
            state.event_data.get("event_title_ko")
            or f"Scenario group {state.event_data['mi_event_id']}"
        )[:255],
        "summary": state.event_data.get("one_line_summary"),
        "description": state.event_data.get("detail_analysis"),
        "dimension_selected": dimension_selected,
        "scenario_count": len(stage4.get("scenarios", []) or []),
        "status": "creating",
        "stage": "ready",
        "crt_usr_logn_id": state.user_id,
        "mod_usr_logn_id": state.user_id,
    }
    scenario_group_id = ScenarioGroupService().create_group(payload)
    scenario_result = dict(state.scenario_result)
    scenario_result["scenario_group_id"] = scenario_group_id
    return {"scenario_group_id": scenario_group_id, "scenario_result": scenario_result}


def save_scenarios(state: ScenarioDesignState) -> dict[str, Any]:
    if state.status in {"failure", "already_exist"}:
        return {}
    if state.scenario_group_id is None or state.scenario_result is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    if state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="user_id is required")

    stage2 = state.scenario_result.get("stage2_dimension_selection", {}) or {}
    selected_dimensions = stage2.get("selected_dimensions", []) or []
    dimension_selected = [
        item.get("dim_key")
        for item in selected_dimensions
        if isinstance(item, dict) and item.get("dim_key")
    ]

    saved_ids = ScenarioService().save_generated_scenarios(
        state.scenario_group_id,
        state.scenario_result,
        state.user_id,
    )
    ScenarioGroupService().update_scenario_count(
        state.scenario_group_id, len(saved_ids)
    )
    group = ScenarioGroupService().update_state(
        state.scenario_group_id,
        status="creating",
        stage="scenario_created",
        dimension_selected=dimension_selected,
        user_id=state.user_id,
    )
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    return {
        "saved_scenario_ids": saved_ids,
        "scenario_group": group,
        "scenarios": scenarios,
        "status": "success",
        "message": f"Created {len(saved_ids)} scenarios",
    }
