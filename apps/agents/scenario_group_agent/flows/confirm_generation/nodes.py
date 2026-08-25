from __future__ import annotations

from apps.agents.scenario_group_agent.flows.confirm_generation.state import (
    ConfirmGenerationState,
    confirm_generation_state_update,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.signpost_service import (
    SignpostService,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


def load_scenario_group(state: ConfirmGenerationState) -> dict[str, object]:
    if state.scenario_group_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_group_id is required")
    group = ScenarioGroupService().load_by_id(state.scenario_group_id)
    if group is None:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail=f"Scenario group not found: {state.scenario_group_id}")
    request_usr_id = group.get("request_usr_id")
    if request_usr_id is not None and request_usr_id != state.user_id:
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"이미 사용자 {request_usr_id}가 점유하고 있습니다.",
        )
    return {"scenario_group": group}


def load_scenarios(state: ConfirmGenerationState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    scenarios = ScenarioService().load_by_group_id(state.scenario_group_id)
    if not scenarios:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="No scenarios found")
    return {"scenarios": scenarios}


def load_signposts(state: ConfirmGenerationState) -> dict[str, object]:
    if state.status == "failure":
        return {}
    signposts = SignpostService().load_by_scenario_ids(
        [int(scenario.scenario_id) for scenario in state.scenarios],
    )
    if not signposts:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="No signposts found")
    return {"signposts": signposts}


def confirm_outputs(state: ConfirmGenerationState) -> dict[str, object]:
    if state.status == "failure" or state.scenario_group_id is None:
        return {}
    if state.request_scenario_group is None or state.request_table is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenarioGroup and table are required")
    result = ScenarioGroupService().apply_confirmation(
        state.scenario_group_id,
        state.request_scenario_group.model_dump(exclude_unset=True),
        state.request_table.model_dump(exclude_unset=True),
        user_id=state.user_id,
    )
    if result.get("status") != "success":
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail=result.get("message", "Confirmation failed"))
    return confirm_generation_state_update(
        scenario_group=result["group"],
        confirmed=True,
        status="success",
        message="Generation confirmed",
    )
