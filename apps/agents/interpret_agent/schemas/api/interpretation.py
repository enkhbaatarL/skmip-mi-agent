from __future__ import annotations

from pydantic import Field

from apps.agents.interpret_agent.schemas.base import ApiModel
from apps.agents.interpret_agent.schemas.enums import PriceInterpretationStatus
from apps.common.values.response import CallBackBody, CommonResponse


class PriceInterpretationItem(ApiModel):
    """시나리오별 가격전망 해석 단위(callback interpretations 항목)."""

    scenario_id: int = Field(description="대상 시나리오 ID")
    content: str = Field(description="가격전망 해석 원본 텍스트")


class CreatePriceInterpretationIn(ApiModel):
    """가격전망 해석 생성 요청 body.

    `scenarioGroupId`는 path param으로 전달되므로 body에서는 생략한다.
    `scenarioIds`에는 이미 해석을 보유한 재실행(re-run) 대상도 포함될 수 있다.
    """

    scenario_ids: list[int] = Field(
        min_length=1,
        description="해석 생성 대상 시나리오 ID 목록(재실행 대상 포함 가능)",
    )


class PriceInterpretationAcceptedData(ApiModel):
    scenario_group_id: int
    scenario_ids: list[int] = Field(description="접수된 대상 시나리오 ID 목록")
    status: str = Field(
        default=PriceInterpretationStatus.PROCESSING.value,
        description="접수 직후 상태(PROCESSING)",
    )


class PriceInterpretationAcceptedOut(CommonResponse):
    """생성 요청 접수(ack) 동기 응답."""

    data: PriceInterpretationAcceptedData | None = None


class PriceInterpretationCallbackOut(CallBackBody):
    """가격전망 해석 생성 완료 callback body(Agent → B.E).

    - result=success: `interpretations`에 시나리오별 해석 원본을 담아 전달
    - result=failure: `reason`에 실패 사유, `interpretations`는 null
    """

    interpretations: list[PriceInterpretationItem] | None = Field(
        default=None,
        description="시나리오별 해석 목록(result=success일 때 필수)",
    )
