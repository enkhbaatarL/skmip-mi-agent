from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Query, Request, Security
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation import run_v4_create_operation
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_flow import (
    prepare_v4_multi_event_scenarios,
    run_v4_multi_event_scenarios_background,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    new_operation_id,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.presentation import build_common_scenario_group_query_data
from apps.agents.scenario_group_agent.routers.scenario_group_stream import stream_operation_events
from apps.agents.scenario_group_agent.routers.security import admin_bearer_scheme, authorization_header
from apps.agents.scenario_group_agent.runtime import get_scenario_group_operation_task_runner
from apps.agents.scenario_group_agent.schemas.api.dimension_mapping import (
    DimensionMappingApprovalData,
    DimensionMappingApprovalIn,
    DimensionMappingApprovalOut,
)
from apps.agents.scenario_group_agent.schemas.api.manage_scenario_groups import (
    HardDeleteScenarioGroupIn,
    HardDeleteScenarioGroupOut,
    ScenarioGroupDetailOut,
    SoftDeleteScenarioGroupIn,
    SoftDeleteScenarioGroupOut,
    SoftDeleteSignpostsIn,
    SoftDeleteSignpostsOut,
)
from apps.agents.scenario_group_agent.schemas.endpoint import (
    ScenarioGroupAcceptedData,
    ScenarioGroupAcceptedOut,
)


router = APIRouter(tags=["scenario-groups"])


@router.post(
    "/v4/scenario-groups",
    response_model=ScenarioGroupAcceptedOut,
    summary="v4 1~5개 이벤트 모델 영향 레버 시나리오 그룹 생성",
    deprecated=True,
)
async def create_v4_scenarios_compatibility(
    payload: V4MultiEventCreateScenariosIn,
    background_tasks: BackgroundTasks,
) -> ScenarioGroupAcceptedOut:
    prepared = prepare_v4_multi_event_scenarios(payload)
    group = prepared["scenario_group"]
    background_tasks.add_task(run_v4_multi_event_scenarios_background, prepared)
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
    ready, decisions = ScenarioGroupService().approve_dimension_mappings(
        scenario_group_id,
        user_id=payload.user_id,
        decisions=[decision.model_dump() for decision in payload.decisions],
    )
    return DimensionMappingApprovalOut(
        data=DimensionMappingApprovalData(
            scenario_group_id=scenario_group_id,
            parameter_mapping_ready=ready,
            decisions=decisions,
        ),
    )


@router.post(
    "/scenario-groups",
    summary="Multi-Event Scenario Group 생성 및 진행 SSE",
    response_class=StreamingResponse,
)
async def create_scenario_group(
    request: Request,
    payload: V4MultiEventCreateScenariosIn,
) -> StreamingResponse:
    operation_id = new_operation_id()
    prepared = prepare_v4_multi_event_scenarios(payload, operation_id=operation_id)
    group_id = int(prepared["scenario_group"].scenario_group_id)
    get_scenario_group_operation_task_runner().submit(
        operation_id,
        run_v4_create_operation(prepared, operation_id),
    )
    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(
        stream_operation_events(request, group_id, operation_id, after_sequence=0),
        media_type="text/event-stream",
        headers=headers,
    )


@router.get(
    "/scenario-groups",
    summary="Scenario Group 목록 조회",
)
async def list_scenario_groups(
    *,
    include_deleted: Annotated[bool, Query(alias="includeDeleted")] = False,
    mi_event_id: int | None = Query(default=None, alias="miEventId"),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    sort: str = Query(default="latest"),
) -> dict[str, Any]:
    return ScenarioGroupService().list_groups(
        include_deleted=include_deleted,
        mi_event_id=mi_event_id,
        keyword=keyword,
        status=status,
        stage=stage,
        sort=sort,
    )


@router.get(
    "/scenario-groups/{scenario_group_id}",
    response_model=ScenarioGroupDetailOut,
    summary="Scenario Group 공통 상세 조회",
)
async def get_scenario_group(
    scenario_group_id: int,
    *,
    include_deleted: Annotated[bool, Query(alias="includeDeleted")] = False,
) -> ScenarioGroupDetailOut:
    context = ScenarioGroupService().load_common_detail(
        scenario_group_id,
        include_deleted=include_deleted,
    )
    return build_common_scenario_group_query_data(**context)


@router.delete(
    "/scenario-groups/{scenario_group_id}",
    response_model=SoftDeleteScenarioGroupOut,
    summary="Scenario Group soft delete",
)
async def delete_scenario_group(
    scenario_group_id: int,
    payload: SoftDeleteScenarioGroupIn,
) -> SoftDeleteScenarioGroupOut:
    result = ScenarioGroupService().soft_delete_group_for_owner(
        scenario_group_id,
        user_id=payload.user_id,
    )
    return SoftDeleteScenarioGroupOut.model_validate(result)


@router.delete(
    "/scenario-groups/{scenario_group_id}/signposts",
    response_model=SoftDeleteSignpostsOut,
    summary="[로컬 개발 전용] Scenario Group signpost soft delete",
)
async def delete_signposts_for_local_testing(
    scenario_group_id: int,
    payload: SoftDeleteSignpostsIn,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(admin_bearer_scheme)] = None,
) -> SoftDeleteSignpostsOut:
    result = ScenarioGroupService().soft_delete_signposts_by_group_id(
        scenario_group_id,
        user_id=payload.user_id,
        authorization=authorization_header(credentials),
    )
    return SoftDeleteSignpostsOut.model_validate(result)


@router.delete(
    "/scenario-groups/{scenario_group_id}/hard",
    response_model=HardDeleteScenarioGroupOut,
    summary="[로컬 개발 전용] Scenario Group hard delete",
)
async def hard_delete_scenario_group_for_local_testing(
    scenario_group_id: int,
    payload: HardDeleteScenarioGroupIn,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(admin_bearer_scheme)] = None,
) -> HardDeleteScenarioGroupOut:
    result = ScenarioGroupService().hard_delete_group(
        scenario_group_id,
        user_id=payload.user_id,
        confirm=payload.confirm,
        authorization=authorization_header(credentials),
    )
    return HardDeleteScenarioGroupOut.model_validate(result)
