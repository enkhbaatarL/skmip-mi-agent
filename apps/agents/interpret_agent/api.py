from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    CreatePriceInterpretationPreviewIn,
    PriceInterpretationAcceptedData,
    PriceInterpretationAcceptedOut,
    PriceInterpretationPreviewOut,
)
from apps.agents.interpret_agent.flows.interpret_price.flow import (
    prepare_price_interpretation,
    run_interpret_price,
    run_price_interpretation_background,
)


router = APIRouter()


@router.post(
    "/scenario-groups/{scenario_group_id}/price-interpretations/preview",
    response_model=PriceInterpretationPreviewOut,
    summary="가격전망 해석 미리보기(동기)",
    description=(
        "입력 feature(제안 파라미터) 시계열과 예측 가격 시계열을 MI Base와 비교해, "
        "시나리오별 '입력 차이 → 예측 가격 결과 → 도메인 해석'과 그룹 종합을 "
        "동기적으로 산출해 즉시 반환합니다(콜백 없음). "
        "입력은 DB에서 조회합니다: 제안 파라미터는 tmm_mi_model_param_proposal_m.proposal_parameters "
        "(basecaseValue=MI Base 입력, proposedValue=시나리오 입력), 예측 가격 결과는 모델 실행 결과 "
        "테이블(MI Base=base_case_prc, 시나리오=user_adj_prc). scenarioIds가 비어 있으면 MI Base를 "
        "제외한 전체 시나리오를 해석합니다."
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


@router.post(
    "/scenario-groups/{scenario_group_id}/price-interpretations",
    response_model=PriceInterpretationAcceptedOut,
    response_model_exclude_none=False,
    summary="가격전망 해석 접수(async)",
    description=(
        "가격전망 해석 요청을 즉시 접수하고 status=PROCESSING으로 반환합니다. "
        "실제 해석(입력 차이 → 예측 가격 결과 → 도메인 해석, 그룹 종합)은 백그라운드에서 "
        "동기 preview와 동일한 interpret_price 그래프로 수행되며, 완료 시 설정된 콜백 URL로 "
        "결과(성공 시 result=success + data, 실패 시 result=failure + reason)를 전달합니다. "
        "콜백 수신 엔드포인트는 "
        "/api/v1/mi/next-gen/scenario-groups/{scenarioGroupId}/price-interpretations/callback 입니다. "
        "입력 조회 규칙은 동기 preview(/price-interpretations/preview)와 동일하며, "
        "scenarioIds가 비어 있으면 MI Base를 제외한 전체 시나리오를 해석합니다. "
        "동기 결과가 필요하면 테스트용 /price-interpretations/preview를 사용하세요."
    ),
)
async def create_price_interpretation(
    scenario_group_id: int,
    background_tasks: BackgroundTasks,
    payload: CreatePriceInterpretationPreviewIn | None = None,
) -> PriceInterpretationAcceptedOut:
    scenario_ids = list(payload.scenario_ids) if payload else []
    result = prepare_price_interpretation(
        scenario_group_id=scenario_group_id,
        scenario_ids=scenario_ids,
    )
    background_tasks.add_task(
        run_price_interpretation_background,
        scenario_group_id=result["scenario_group_id"],
        scenario_ids=result["scenario_ids"],
    )
    return PriceInterpretationAcceptedOut(
        data=PriceInterpretationAcceptedData(
            scenario_group_id=result["scenario_group_id"],
            status="PROCESSING",
        ),
    )
