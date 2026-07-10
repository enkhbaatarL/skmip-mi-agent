from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Body, Path

from apps.agents.model_parameter_agent.flows.confirm_parameters.flow import (
    get_runnable_graph as get_confirm_parameters_runnable,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.api_schema import (
    ConfirmParametersIn,
    ConfirmParametersOut,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.flow import (
    get_runnable_graph,
    prepare_propose_parameters_callback,
    run_propose_parameters_background,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.api_schema import (
    ProposeParametersAcceptedData,
    ProposeParametersAcceptedOut,
    ProposeParametersOut,
    ProposeParametersRequest,
)


router = APIRouter()


@router.post(
    "/model-parameters/scenarios/{scenario_id}/proposals/sync",
    response_model=ProposeParametersOut,
    response_model_exclude_none=False,
    summary="수급모델 Input Parameter 제안(sync 테스트용)",
    description=(
        "scenario_id로 시나리오/이벤트/Dimension context를 DB에서 조회하고, "
        "DB 매핑 정보와 Basecase 입력시트 record를 근거로 LLM이 "
        "수급모델 parameter slot/value를 제안합니다. "
        "제안 결과를 DB에 저장한 뒤 status/message/data wrapper의 "
        "modelParamProposalId와 proposalParameters로 반환합니다. "
        "테스트 및 로컬 검증용 sync API이며 values에는 LUT 기준값을 "
        "lutValue로 추가해 반환합니다. lutValue는 DB 저장 payload와 운영 callback에는 포함되지 않습니다."
    ),
)
async def propose_parameters_sync(
    scenario_id: int,
    payload: ProposeParametersRequest | None = Body(default=None),
) -> ProposeParametersOut:
    user_id = payload.user_id if payload is not None else None
    return await get_runnable_graph().ainvoke(
        {
            "scenario_id": scenario_id,
            "user_id": user_id,
        },
    )


@router.post(
    "/model-parameters/scenarios/{scenario_id}/proposals",
    response_model=ProposeParametersAcceptedOut,
    response_model_exclude_none=False,
    summary="수급모델 Input Parameter 제안 접수",
    description=(
        "scenario_id의 기본 context와 DB 매핑 후보 존재 여부를 확인하고 "
        "PROCESSING proposal row를 생성한 뒤 즉시 반환합니다. "
        "수급모델 parameter slot/value 제안은 백그라운드에서 수행되며 완료 시 설정된 callback URL로 "
        "proposal 생성 완료 신호를 전달합니다. Backend는 callback 수신 후 proposal row를 재조회합니다. "
        "sync proposal API는 /proposals/sync에서 "
        "테스트용으로 제공합니다."
    ),
)
async def propose_parameters(
    scenario_id: int,
    background_tasks: BackgroundTasks,
    payload: ProposeParametersRequest | None = Body(default=None),
) -> ProposeParametersAcceptedOut:
    user_id = payload.user_id if payload is not None else None
    result = prepare_propose_parameters_callback(
        scenario_id,
        user_id=user_id,
    )
    background_tasks.add_task(
        run_propose_parameters_background,
        model_param_proposal_id=result["model_param_proposal_id"],
        scenario_id=result["scenario_id"],
        scenario_group_id=result["scenario_group_id"],
        event_id=result["event_id"],
    )
    return ProposeParametersAcceptedOut(
        data=ProposeParametersAcceptedData(
            model_param_proposal_id=result["model_param_proposal_id"],
            status="PROCESSING",
        ),
    )


@router.post(
    "/model-parameters/proposals/{modelParamProposalId}/confirmation",
    response_model=ConfirmParametersOut,
    response_model_exclude_none=False,
    summary="수급모델 Input Parameter 확정",
    description=(
        "사용자가 검토/수정/추가/삭제한 confirmationParameters를 기본 구조와 "
        "slot 중복 기준으로 검증한 뒤, 해당 model parameter proposal row에 "
        "confirmation_parameters를 저장하고 status를 CONFIRMED로 전이합니다. "
        "이미 CONFIRMED 상태인 row는 confirmation_parameters를 새 요청값으로 덮어씁니다. "
        "LLM 호출 없이 sync로 동작합니다."
    ),
)
async def confirm_parameters(
    payload: ConfirmParametersIn,
    model_param_proposal_id: int = Path(alias="modelParamProposalId"),
) -> ConfirmParametersOut:
    return await get_confirm_parameters_runnable().ainvoke(
        {
            "model_param_proposal_id": model_param_proposal_id,
            **payload.model_dump(exclude_unset=True),
        },
    )
