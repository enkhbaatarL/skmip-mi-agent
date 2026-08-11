from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from apps.agents.scenario_group_agent.flows.confirm_generation.flow import run_confirm_generation
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.flow import (
    prepare_create_scenarios,
    run_create_scenarios_background,
)
from apps.agents.scenario_group_agent.flows.create_signposts.flow import (
    prepare_create_signposts,
    run_create_signposts_background,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.flow import (
    prepare_validate_scenarios,
    run_validate_scenarios_background,
)
from apps.agents.scenario_group_agent.routers.scenario_generation_sync import (
    create_signposts_sync,
    validate_scenarios_sync,
)
from apps.agents.scenario_group_agent.routers.versioned_scenario_generation_sync import create_v1_scenarios_sync
from apps.agents.scenario_group_agent.schemas.endpoint import (
    ConfirmGenerationIn,
    ConfirmGenerationOut,
    CreateScenariosIn,
    CreateSignpostsIn,
    CreateSignpostsSyncOut,
    ScenarioGroupAcceptedData,
    ScenarioGroupAcceptedOut,
    ValidateScenariosIn,
    ValidateScenariosSyncOut,
)
from apps.common.logging.logger_config import logger


router = APIRouter(tags=["scenario-groups-legacy-v1"])


@router.post(
    "/v1/scenario-groups",
    response_model=ScenarioGroupAcceptedOut,
    summary="시나리오 그룹 생성",
    deprecated=True,
)
async def create_scenarios(
    payload: CreateScenariosIn,
    background_tasks: BackgroundTasks,
) -> ScenarioGroupAcceptedOut:
    result = prepare_create_scenarios(payload.mi_event_id, payload.user_id)
    if result["should_run_background"]:
        background_tasks.add_task(
            run_create_scenarios_background,
            scenario_group_id=result["scenario_group_id"],
            event_data=result["event_data"],
            user_id=result["user_id"],
        )
    else:
        logger.info(
            "Skip background scenario creation | scenario_group_id={} | stage={}",
            result["scenario_group_id"],
            result["stage"],
        )
    return ScenarioGroupAcceptedOut(
        data=ScenarioGroupAcceptedData(
            scenario_group_id=result["scenario_group_id"],
            status=result["status"],
            stage=result["stage"],
        ),
    )


@router.post(
    "/v1/scenario-groups/{scenario_group_id}/validation",
    response_model=ScenarioGroupAcceptedOut,
    summary="시나리오 테이블 검증",
    deprecated=True,
)
async def validate_scenarios(
    scenario_group_id: int,
    payload: ValidateScenariosIn,
    background_tasks: BackgroundTasks,
) -> ScenarioGroupAcceptedOut:
    result = prepare_validate_scenarios(scenario_group_id, payload.user_id, payload.table.model_dump())
    background_tasks.add_task(
        run_validate_scenarios_background,
        scenario_group_id=result["scenario_group_id"],
        user_id=result["user_id"],
        request_table=result["request_table"],
    )
    return ScenarioGroupAcceptedOut(
        data=ScenarioGroupAcceptedData(
            scenario_group_id=result["scenario_group_id"],
            status=result["status"],
            stage=result["stage"],
        ),
    )


@router.post(
    "/v1/scenario-groups/{scenario_group_id}/signposts",
    response_model=ScenarioGroupAcceptedOut,
    summary="Signpost 생성",
    deprecated=True,
)
async def create_signposts(
    scenario_group_id: int,
    payload: CreateSignpostsIn,
    background_tasks: BackgroundTasks,
) -> ScenarioGroupAcceptedOut:
    result = prepare_create_signposts(scenario_group_id, payload.user_id, payload.table.model_dump())
    background_tasks.add_task(
        run_create_signposts_background,
        scenario_group_id=result["scenario_group_id"],
        user_id=result["user_id"],
        request_table=result["request_table"],
    )
    return ScenarioGroupAcceptedOut(
        data=ScenarioGroupAcceptedData(
            scenario_group_id=result["scenario_group_id"],
            status=result["status"],
            stage=result["stage"],
        ),
    )


@router.post(
    "/v1/scenario-groups/{scenario_group_id}/confirmation",
    response_model=ConfirmGenerationOut,
    summary="시나리오 생성 확정",
    deprecated=True,
)
async def confirm_generation(
    scenario_group_id: int,
    payload: ConfirmGenerationIn,
) -> ConfirmGenerationOut:
    result = await run_confirm_generation(
        {"scenario_group_id": scenario_group_id, **payload.model_dump(exclude_unset=True)},
    )
    return ConfirmGenerationOut.model_validate(result)


router.add_api_route(
    "/v1/scenario-groups/sync",
    create_v1_scenarios_sync,
    methods=["POST"],
    response_model=VersionedCreateScenariosOut,
    summary="v1 단일 이벤트 시나리오 그룹 생성 동기 실행",
    deprecated=True,
)
router.add_api_route(
    "/v1/scenario-groups/{scenario_group_id}/validation/sync",
    validate_scenarios_sync,
    methods=["POST"],
    response_model=ValidateScenariosSyncOut,
    summary="시나리오 테이블 검증 동기 실행",
    deprecated=True,
)
router.add_api_route(
    "/v1/scenario-groups/{scenario_group_id}/signposts/sync",
    create_signposts_sync,
    methods=["POST"],
    response_model=CreateSignpostsSyncOut,
    summary="Signpost 생성 동기 실행",
    deprecated=True,
)


__all__ = ["router"]
