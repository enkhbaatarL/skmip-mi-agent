from __future__ import annotations

from fastapi import APIRouter

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    CreatePriceInterpretationPreviewIn,
    PriceInterpretationPreviewOut,
)
from apps.agents.interpret_agent.flows.interpret_price.flow import run_interpret_price


router = APIRouter()


@router.post(
    "/scenario-groups/{scenario_group_id}/price-interpretations/preview",
    response_model=PriceInterpretationPreviewOut,
    summary="가격전망 해석 미리보기(동기)",
    description=(
        "입력 feature(현재 기온) 시계열과 예측 가격 시계열을 MI Base와 비교해, "
        "시나리오별 '입력 차이 → 예측 가격 결과 → 도메인 해석'과 그룹 종합을 "
        "동기적으로 산출해 즉시 반환합니다(콜백 없음). "
        "현재 입력은 샘플 파일(proposal_parameters_sample.json, price_forecast_v2.json)에서 "
        "로드하며 추후 DB 조회로 대체됩니다. scenarioIds가 비어 있으면 MI Base를 제외한 "
        "전체 시나리오를 해석합니다."
    ),
)
async def preview_price_interpretation(
    scenario_group_id: int,
    payload: CreatePriceInterpretationPreviewIn | None = None,
) -> PriceInterpretationPreviewOut:
    scenario_ids = list(payload.scenario_ids) if payload else []
    result = await run_interpret_price(
        scenario_group_id=scenario_group_id,
        scenario_ids=scenario_ids,
    )
    return PriceInterpretationPreviewOut(
        message="가격전망 해석 미리보기 결과입니다.",
        data=result,
    )
