from __future__ import annotations

from fastapi import APIRouter

from apps.agents.model_parameter_agent.flows.propose_parameters.flow import (
    get_runnable_graph,
)
from apps.agents.model_parameter_agent.schemas.propose_parameters import (
    ProposeParametersOut,
)


router = APIRouter()


@router.post(
    "/model-parameters/scenarios/{scenario_id}/proposals",
    response_model=ProposeParametersOut,
    response_model_exclude_none=False,
    summary="수급모델 Input Parameter 제안",
    description=(
        "scenario_id로 시나리오/이벤트/Dimension context를 DB에서 조회하고, "
        "DB 매핑 정보와 Basecase 입력시트 record를 근거로 LLM이 "
        "수급모델 parameter slot/value를 제안합니다. "
        "제안 결과를 DB에 저장한 뒤 status/message/data wrapper의 "
        "modelParamProposalId와 proposalParameters로 반환합니다."
    ),
)
async def propose_parameters(
    scenario_id: int,
) -> ProposeParametersOut:
    return await get_runnable_graph().ainvoke({"scenario_id": scenario_id})
