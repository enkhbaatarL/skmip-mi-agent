from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from apps.agents.scenario_group_agent.flows.confirm_generation.flow import (
    run_confirm_generation,
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
from apps.agents.scenario_group_agent.schemas.endpoint import (
    ConfirmGenerationIn,
    ConfirmGenerationOut,
    CreateScenariosIn,
    CreateSignpostsIn,
    ScenarioGroupAcceptedData,
    ScenarioGroupAcceptedOut,
    ValidateScenariosIn,
)
from apps.common.logging.logger_config import logger


router = APIRouter(tags=["scenario-generation"])


@router.post(
    "/scenario-groups",
    response_model=ScenarioGroupAcceptedOut,
    summary="시나리오 그룹 생성",
    description=(
        "MI 이벤트 ID와 요청 사용자 ID를 기준으로 시나리오 그룹을 즉시 생성하고 200을 반환합니다. "
        "시나리오 초안 생성은 백그라운드에서 실행되며 완료 시 콜백으로 결과를 전달합니다. "
        "이미 다른 사용자가 점유한 이벤트이면 권한 오류를 반환합니다."
    ),
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
    "/scenario-groups/{scenario_group_id}/validation",
    response_model=ScenarioGroupAcceptedOut,
    summary="시나리오 테이블 검증",
    description=(
        "시나리오 그룹 존재·권한을 확인하고 200을 반환합니다. "
        "검증 및 차원값 자동생성은 백그라운드에서 실행되며 완료 시 콜백으로 결과를 전달합니다. "
        "시나리오 그룹 점유자와 요청 사용자 ID가 다르면 권한 오류를 반환합니다."
    ),
)
async def validate_scenarios(
    scenario_group_id: int,
    payload: ValidateScenariosIn,
    background_tasks: BackgroundTasks,
) -> ScenarioGroupAcceptedOut:
    result = prepare_validate_scenarios(
        scenario_group_id,
        payload.user_id,
        payload.table.model_dump(),
    )
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
    "/scenario-groups/{scenario_group_id}/signposts",
    response_model=ScenarioGroupAcceptedOut,
    summary="Signpost 생성",
    description=(
        "시나리오 그룹 존재·권한을 확인하고 200을 반환합니다. "
        "시나리오 동기화 및 signpost 생성은 백그라운드에서 실행되며 완료 시 콜백으로 결과를 전달합니다."
    ),
)
async def create_signposts(
    scenario_group_id: int,
    payload: CreateSignpostsIn,
    background_tasks: BackgroundTasks,
) -> ScenarioGroupAcceptedOut:
    result = prepare_create_signposts(
        scenario_group_id,
        payload.user_id,
        payload.table.model_dump(),
    )
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
    "/scenario-groups/{scenario_group_id}/confirmation",
    response_model=ConfirmGenerationOut,
    summary="시나리오 생성 확정",
    description=(
        "검증 및 signpost 생성이 끝난 시나리오 그룹을 최종 확정합니다. "
        "확정 시 시나리오/signpost 변경 내용을 저장하고 confirmation snapshot을 생성합니다."
    ),
)
async def confirm_generation(
    scenario_group_id: int,
    payload: ConfirmGenerationIn,
) -> ConfirmGenerationOut:
    result = await run_confirm_generation(
        {
            "scenario_group_id": scenario_group_id,
            **payload.model_dump(exclude_unset=True),
        },
    )
    return ConfirmGenerationOut.model_validate(result)
