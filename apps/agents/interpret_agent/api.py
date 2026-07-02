from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from apps.agents.interpret_agent.flows.create_interpretation.flow_async import (
    prepare_create_interpretation,
    run_create_interpretation_background,
)
from apps.agents.interpret_agent.schemas.api.interpretation import (
    CreatePriceInterpretationIn,
    PriceInterpretationAcceptedData,
    PriceInterpretationAcceptedOut,
)


router = APIRouter()


@router.post(
    "/scenario-groups/{scenario_group_id}/price-interpretations",
    response_model=PriceInterpretationAcceptedOut,
    summary="가격전망 해석 생성 요청",
    description=(
        "생성 대상 시나리오들의 가격전망 해석 산출을 접수합니다(async). "
        "대상 시나리오는 MI 수급모델 실행이 선행되어야 하며, 해석 미보유/실패 또는 "
        "수급모델 재실행(N회차)된 시나리오여야 합니다. "
        "요청은 접수(PROCESSING) 상태만 즉시 반환하고, 실제 해석 결과는 콜백으로 비동기 전달됩니다. "
        "콜백 URL은 서버 설정값(callback_base_url + callback_price_interpretations_path)을 사용합니다."
    ),
)
async def create_price_interpretation(
    scenario_group_id: int,
    payload: CreatePriceInterpretationIn,
    background_tasks: BackgroundTasks,
) -> PriceInterpretationAcceptedOut:
    prepared = prepare_create_interpretation(
        scenario_group_id=scenario_group_id,
        scenario_ids=payload.scenario_ids,
    )
    background_tasks.add_task(
        run_create_interpretation_background,
        scenario_group_id=int(prepared["scenario_group_id"]),
        scenario_ids=list(prepared["scenario_ids"]),
    )
    return PriceInterpretationAcceptedOut(
        message="가격전망 해석 생성 요청이 접수되었습니다.",
        data=PriceInterpretationAcceptedData(
            scenario_group_id=int(prepared["scenario_group_id"]),
            scenario_ids=list(prepared["scenario_ids"]),
            status=str(prepared["status"]),
        ),
    )
