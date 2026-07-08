from __future__ import annotations

from fastapi import APIRouter

from apps.agents.scenario_group_agent.flows.create_scenarios.flow import (
    prepare_create_scenarios,
    run_create_scenarios_inline,
)
from apps.agents.scenario_group_agent.flows.create_signposts.flow import (
    prepare_create_signposts,
    run_create_signposts_inline,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.flow import (
    prepare_validate_scenarios,
    run_validate_scenarios_inline,
)
from apps.agents.scenario_group_agent.schemas.endpoint import (
    CreateScenariosIn,
    CreateScenariosOut,
    CreateSignpostsIn,
    CreateSignpostsOut,
    ValidateScenariosIn,
    ValidateScenariosOut,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode


router = APIRouter(tags=["scenario-generation-sync"])


@router.post(
    "/scenario-groups/sync",
    response_model=CreateScenariosOut,
    summary="시나리오 그룹 생성 동기 실행",
    description=(
        "테스트용 API입니다. 기존 시나리오 그룹 생성 API와 같은 prepare 및 생성 graph를 실행하되, "
        "백그라운드 task와 callback 전송 없이 callback body를 HTTP 응답으로 반환합니다."
    ),
)
async def create_scenarios_sync(payload: CreateScenariosIn) -> CreateScenariosOut:
    result = prepare_create_scenarios(payload.mi_event_id, payload.user_id)
    if not result["should_run_background"]:
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_ALREADY_CREATED,
            detail=f"시나리오 그룹 ID: {result['scenario_group_id']}",
        )
    try:
        return await run_create_scenarios_inline(
            scenario_group_id=result["scenario_group_id"],
            event_data=result["event_data"],
            user_id=result["user_id"],
        )
    except Exception as exc:
        logger.error(
            "[SYNC][create_scenarios] FAILED | group_id={} | error={!r}",
            result["scenario_group_id"],
            exc,
        )
        return CreateScenariosOut(result="failure", reason=str(exc))


@router.post(
    "/scenario-groups/{scenario_group_id}/validation/sync",
    response_model=ValidateScenariosOut,
    summary="시나리오 테이블 검증 동기 실행",
    description=(
        "테스트용 API입니다. 기존 검증 API와 같은 prepare 및 검증 graph를 실행하되, "
        "백그라운드 task와 callback 전송 없이 callback body를 HTTP 응답으로 반환합니다."
    ),
)
async def validate_scenarios_sync(
    scenario_group_id: int,
    payload: ValidateScenariosIn,
) -> ValidateScenariosOut:
    result = prepare_validate_scenarios(
        scenario_group_id,
        payload.user_id,
        payload.table.model_dump(),
    )
    try:
        return await run_validate_scenarios_inline(
            scenario_group_id=result["scenario_group_id"],
            user_id=result["user_id"],
            request_table=result["request_table"],
        )
    except Exception as exc:
        logger.error(
            "[SYNC][validate_scenarios] FAILED | group_id={} | error={!r}",
            result["scenario_group_id"],
            exc,
        )
        return ValidateScenariosOut(result="failure", reason=str(exc))


@router.post(
    "/scenario-groups/{scenario_group_id}/signposts/sync",
    response_model=CreateSignpostsOut,
    summary="Signpost 생성 동기 실행",
    description=(
        "테스트용 API입니다. 기존 signpost 생성 API와 같은 prepare 및 생성 graph를 실행하되, "
        "백그라운드 task와 callback 전송 없이 callback body를 HTTP 응답으로 반환합니다."
    ),
)
async def create_signposts_sync(
    scenario_group_id: int,
    payload: CreateSignpostsIn,
) -> CreateSignpostsOut:
    result = prepare_create_signposts(
        scenario_group_id,
        payload.user_id,
        payload.table.model_dump(),
    )
    try:
        return await run_create_signposts_inline(
            scenario_group_id=result["scenario_group_id"],
            user_id=result["user_id"],
            request_table=result["request_table"],
        )
    except Exception as exc:
        logger.error(
            "[SYNC][create_signposts] FAILED | group_id={} | error={!r}",
            result["scenario_group_id"],
            exc,
        )
        return CreateSignpostsOut(result="failure", reason=str(exc))
