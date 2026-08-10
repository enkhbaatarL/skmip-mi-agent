from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from apps.agents.scenario_group_agent.flows.confirm_generation.flow import (
    run_confirm_generation,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_flow import (
    prepare_v4_multi_event_scenarios,
    run_v4_multi_event_scenarios_background,
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
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.schemas.api.dimension_mapping import (
    DimensionMappingApprovalData,
    DimensionMappingApprovalIn,
    DimensionMappingApprovalOut,
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
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode


router = APIRouter(tags=["scenario-generation"])


@router.post(
    "/v4/scenario-groups",
    response_model=ScenarioGroupAcceptedOut,
    summary="v4 1~5개 이벤트 모델 영향 레버 시나리오 그룹 생성",
)
async def create_v4_scenarios(
    payload: V4MultiEventCreateScenariosIn,
    background_tasks: BackgroundTasks,
) -> ScenarioGroupAcceptedOut:
    prepared = prepare_v4_multi_event_scenarios(payload)
    group = prepared["scenario_group"]
    background_tasks.add_task(
        run_v4_multi_event_scenarios_background,
        prepared,
    )
    return ScenarioGroupAcceptedOut(
        data=ScenarioGroupAcceptedData(
            scenario_group_id=group.scenario_group_id,
            status=group.status,
            stage=group.stage,
        ),
    )


@router.post(
    "/scenario-groups/{scenario_group_id}/dimension-mapping-approvals",
    response_model=DimensionMappingApprovalOut,
    summary="자유 dimension value mapping proposal 승인/거절",
)
async def approve_dimension_mappings(
    scenario_group_id: int,
    payload: DimensionMappingApprovalIn,
) -> DimensionMappingApprovalOut:
    group = ScenarioGroupService().load_by_id(scenario_group_id)
    if group is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Scenario group not found: {scenario_group_id}",
        )
    if group.request_usr_id is not None and group.request_usr_id != payload.user_id:
        raise MIBaseError(
            ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT,
            detail=f"이미 사용자 {group.request_usr_id}가 점유하고 있습니다.",
        )
    decisions = ScenarioService().decide_mapping_proposals(
        scenario_group_id,
        [decision.model_dump() for decision in payload.decisions],
        payload.user_id,
    )
    refreshed = ScenarioGroupService().load_by_id(scenario_group_id)
    if refreshed is None:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Scenario group not found: {scenario_group_id}",
        )
    return DimensionMappingApprovalOut(
        data=DimensionMappingApprovalData(
            scenario_group_id=scenario_group_id,
            parameter_mapping_ready=refreshed.parameter_mapping_ready,
            decisions=decisions,
        ),
    )


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
