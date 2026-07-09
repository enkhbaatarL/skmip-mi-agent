from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Security
from fastapi.security import HTTPAuthorizationCredentials

from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.presentation import build_scenario_group_query_data
from apps.agents.scenario_group_agent.routers.security import admin_bearer_scheme, authorization_header
from apps.agents.scenario_group_agent.schemas.endpoint import (
    HardDeleteScenarioGroupIn,
    HardDeleteScenarioGroupOut,
    ScenarioGroupDetailOut,
    SoftDeleteScenarioGroupIn,
    SoftDeleteScenarioGroupOut,
    SoftDeleteSignpostsIn,
    SoftDeleteSignpostsOut,
)


router = APIRouter(tags=["scenario-group-management"])


@router.get(
    "/scenario-groups",
    summary="Scenario Group 목록 조회",
    description="Backoffice Scenario Group List 화면용 Scenario Group 목록을 반환합니다.",
)
async def list_scenario_groups(
    *,
    include_deleted: Annotated[bool, Query(alias="includeDeleted")] = False,
    mi_event_id: int | None = Query(default=None, alias="miEventId"),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    sort: str = Query(default="latest"),
) -> dict[str, object]:
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
    summary="시나리오 그룹 상세 조회",
    description=(
        "시나리오 그룹, 시나리오 테이블, 각 시나리오의 signpost를 조회합니다. "
        "기본적으로 soft deleted 데이터는 제외하며, `includeDeleted=true`이면 "
        "삭제 데이터와 `delYn` 상태 및 삭제 count를 함께 반환합니다."
    ),
)
async def get_scenario_group(
    scenario_group_id: int,
    *,
    include_deleted: Annotated[
        bool,
        Query(
            alias="includeDeleted",
            description="true이면 soft deleted scenario group/scenario/signpost까지 포함합니다.",
        ),
    ] = False,
) -> ScenarioGroupDetailOut:
    result = ScenarioGroupService().load_detail(
        scenario_group_id,
        include_deleted=include_deleted,
    )
    return build_scenario_group_query_data(**result)


@router.delete(
    "/scenario-groups/{scenario_group_id}/signposts",
    response_model=SoftDeleteSignpostsOut,
    summary="[로컬 개발 전용] 시나리오 그룹 signpost soft delete",
    description=(
        "로컬 개발 환경에서 테스트 데이터를 정리하기 위한 API입니다. "
        "운영 또는 일반 업무 플로우에서는 사용하지 마세요. "
        "시나리오 그룹 하위의 signpost를 `del_yn='Y'`로 soft delete합니다. "
        "시나리오 그룹과 시나리오는 유지됩니다. Swagger Authorize를 사용하거나 "
        "`Authorization: Bearer <token>` 헤더에 "
        "`scenario_group_admin_bearer_tokens`에 등록된 토큰을 전달해야 합니다."
    ),
)
async def delete_signposts(
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
    "/scenario-groups/{scenario_group_id}",
    response_model=SoftDeleteScenarioGroupOut,
    summary="[로컬 개발 전용] 시나리오 그룹 soft delete",
    description=(
        "로컬 개발 환경에서 테스트 데이터를 정리하기 위한 API입니다. "
        "운영 또는 일반 업무 플로우에서는 사용하지 마세요. "
        "시나리오 그룹과 하위 시나리오/signpost를 `del_yn='Y'`로 soft delete하며, "
        "snapshot 계열 테이블은 보존합니다. Swagger Authorize를 사용하거나 "
        "`Authorization: Bearer <token>` 헤더에 "
        "`scenario_group_admin_bearer_tokens`에 등록된 토큰을 전달해야 합니다."
    ),
)
async def delete_scenario_group(
    scenario_group_id: int,
    payload: SoftDeleteScenarioGroupIn,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(admin_bearer_scheme)] = None,
) -> SoftDeleteScenarioGroupOut:
    result = ScenarioGroupService().soft_delete_group(
        scenario_group_id,
        user_id=payload.user_id,
        authorization=authorization_header(credentials),
    )
    return SoftDeleteScenarioGroupOut.model_validate(result)


@router.delete(
    "/scenario-groups/{scenario_group_id}/hard",
    response_model=HardDeleteScenarioGroupOut,
    summary="[로컬 개발 전용] 시나리오 그룹 hard delete",
    description=(
        "로컬 개발 환경에서 테스트 데이터를 물리 삭제하기 위한 API입니다. "
        "운영 또는 일반 업무 플로우에서는 사용하지 마세요. "
        "`confirm=true`가 필요하며, snapshot/signpost/scenario/scenario group 관련 "
        "테이블을 FK 순서에 맞춰 hard delete합니다. Swagger Authorize를 사용하거나 "
        "`Authorization: Bearer <token>` 헤더에 "
        "`scenario_group_admin_bearer_tokens`에 등록된 토큰을 전달해야 합니다."
    ),
)
async def hard_delete_scenario_group(
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
