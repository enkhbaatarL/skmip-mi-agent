from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apps.agents.scenario_group_agent.flows.confirm_generation.flow import (
    get_runnable_graph as get_confirm_generation_runnable,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.flow_async import (
    prepare_create_scenarios,
    run_create_scenarios_background,
)
from apps.agents.scenario_group_agent.flows.create_signposts.flow_async import (
    prepare_create_signposts,
    run_create_signposts_background,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.flow_async import (
    prepare_validate_scenarios,
    run_validate_scenarios_background,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.schemas.api.common import (
    ScenarioGroupAcceptedData,
    ScenarioGroupAcceptedOut,
)
from apps.agents.scenario_group_agent.schemas.api.confirm_generation import (
    ConfirmGenerationIn,
    ConfirmGenerationOut,
)
from apps.agents.scenario_group_agent.schemas.api.create_scenarios import CreateScenariosIn
from apps.agents.scenario_group_agent.schemas.api.create_signposts import CreateSignpostsIn
from apps.agents.scenario_group_agent.schemas.api.manage_scenario_groups import (
    HardDeleteScenarioGroupIn,
    HardDeleteScenarioGroupOut,
    ScenarioGroupDetailOut,
    SoftDeleteScenarioGroupIn,
    SoftDeleteScenarioGroupOut,
    SoftDeleteSignpostsIn,
    SoftDeleteSignpostsOut,
)
from apps.agents.scenario_group_agent.schemas.api.validate_scenarios import ValidateScenariosIn


router = APIRouter()

admin_bearer_scheme = HTTPBearer(
    scheme_name="ScenarioGroupAdminBearer",
    description=(
        "로컬 개발용 정리 API 전용 인증입니다. "
        "`scenario_group_admin_bearer_tokens`에 등록된 토큰을 "
        "`Authorization: Bearer <token>` 형식으로 전달합니다."
    ),
    auto_error=False,
)


def _authorization_header(
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is None:
        return None
    return f"{credentials.scheme} {credentials.credentials}"


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
    background_tasks.add_task(
        run_create_scenarios_background,
        scenario_group_id=result["scenario_group_id"],
        event_data=result["event_data"],
        user_id=result["user_id"],
    )
    return ScenarioGroupAcceptedOut(
        data=ScenarioGroupAcceptedData(
            scenario_group_id=result["scenario_group_id"],
            status=result["status"],
            stage=result["stage"],
        )
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
    include_deleted: bool = Query(
        default=False,
        alias="includeDeleted",
        description="true이면 soft deleted scenario group/scenario/signpost까지 포함합니다.",
    ),
) -> ScenarioGroupDetailOut:
    result = ScenarioGroupService().load_detail(
        scenario_group_id,
        include_deleted=include_deleted,
    )
    return result


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
    credentials: HTTPAuthorizationCredentials | None = Security(admin_bearer_scheme),
) -> SoftDeleteScenarioGroupOut:
    result = ScenarioGroupService().soft_delete_group(
        scenario_group_id,
        user_id=payload.user_id,
        authorization=_authorization_header(credentials),
    )
    return SoftDeleteScenarioGroupOut.model_validate(result)


@router.delete(
    "/admin/scenario-groups/{scenario_group_id}/hard",
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
    credentials: HTTPAuthorizationCredentials | None = Security(admin_bearer_scheme),
) -> HardDeleteScenarioGroupOut:
    result = ScenarioGroupService().hard_delete_group(
        scenario_group_id,
        user_id=payload.user_id,
        confirm=payload.confirm,
        authorization=_authorization_header(credentials),
    )
    return HardDeleteScenarioGroupOut.model_validate(result)


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
        )
    )


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
    credentials: HTTPAuthorizationCredentials | None = Security(admin_bearer_scheme),
) -> SoftDeleteSignpostsOut:
    result = ScenarioGroupService().soft_delete_signposts_by_group_id(
        scenario_group_id,
        user_id=payload.user_id,
        authorization=_authorization_header(credentials),
    )
    return SoftDeleteSignpostsOut.model_validate(result)


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
        )
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
    result = await get_confirm_generation_runnable().ainvoke(
        {
            "scenario_group_id": scenario_group_id,
            **payload.model_dump(exclude_unset=True),
        }
    )
    return ConfirmGenerationOut.model_validate(result)
