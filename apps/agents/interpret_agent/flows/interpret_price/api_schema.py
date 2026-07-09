"""interpret_price flow 전용 API request/response schema.

동기(sync) preview 엔드포인트가 반환하는 해석 결과 shape을 정의한다.
결과는 시나리오 간 '동일 구조 비교'(같은 항목을 시나리오별로 채운 형태)를 지향하며,
지역별 특징은 각 시나리오 해석 안에 녹인다. (MI Base 자체 정보는 출력 제외,
플래그·원지표 등 과도한 디테일은 신뢰도 서술로 압축)
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from apps.agents.interpret_agent.schemas.base import ApiModel
from apps.common.values.response import CallBackBody


class CreatePriceInterpretationPreviewIn(ApiModel):
    """해석 미리보기 요청 body.

    scenarioGroupId는 path param으로 전달된다. scenarioIds가 비어 있으면
    입력에 존재하는 (MI Base 제외) 전체 시나리오를 해석한다.
    """

    scenario_ids: list[int] = Field(
        default_factory=list,
        description="해석 대상 시나리오 ID 목록(비우면 전체, MI Base는 항상 제외)",
    )


class ScenarioComparisonOut(ApiModel):
    """시나리오 1건의 보고서형 해석(시나리오별 상세 분석 한 블록).

    지역별(아시아·유럽/미국) 특징과 base 복귀 시점은 driver_phase/price_character에,
    신뢰도·실무 대응은 summary에 녹여 서술한다.
    """

    scenario_id: str
    identity: str = Field(
        description="한 줄 정체성(굵게 표기되는 시나리오 헤드라인 문장)"
    )
    driver_phase: str = Field(
        description="동인 및 국면(Driver Phase). 여러 feature 움직임과 지역·수렴 시점을 종합"
    )
    price_character: str = Field(
        description="가격 특성(Price Character). 지역별 반응과 정상화 시점을 포함"
    )
    summary: str = Field(
        description="시나리오 요약. 신뢰도(데이터 품질)와 실무 대응을 포함한 서술 한 단락"
    )


class GroupSynthesisOut(ApiModel):
    overall_message: str = Field(
        default="", description="그룹 전체를 아우르는 종합 메시지 한 단락"
    )


class PriceInterpretationMetaOut(ApiModel):
    scenario_group_id: int | None = None
    base_scenario_id: str
    features: list[str] = Field(default_factory=list, description="해석에 사용된 입력 feature 목록")
    indices: list[str] = Field(default_factory=list)
    period_start: str | None = None
    period_end: str | None = None
    unit: str = "$/MMBtu"


class PriceInterpretationResult(ApiModel):
    """해석 결과 본문."""

    meta: PriceInterpretationMetaOut
    scenarios: list[ScenarioComparisonOut] = Field(default_factory=list)
    synthesis: GroupSynthesisOut


class PriceInterpretationPreviewOut(ApiModel):
    """동기 preview 응답 envelope."""

    status: str = "success"
    message: str = ""
    data: PriceInterpretationResult | None = None


class PriceInterpretationAcceptedData(ApiModel):
    """비동기 요청 접수 응답 data.

    해석 결과 자체는 콜백으로 전달되므로, 접수 응답에는 대상 그룹과
    처리 상태만 담는다(별도 해석 결과 저장 row가 없어 id는 두지 않는다).
    """

    scenario_group_id: int
    status: Literal["PROCESSING"] = "PROCESSING"


class PriceInterpretationAcceptedOut(ApiModel):
    """비동기 접수(202-style) 응답 envelope."""

    status: Literal["success", "error"] = "success"
    message: str = "accepted"
    data: PriceInterpretationAcceptedData


class PriceInterpretationCallbackOut(CallBackBody):
    """가격전망 해석 비동기 콜백 payload.

    성공 시 해석 결과(data)를 실어 보내고, 실패 시 result="failure" + reason만 채운다.
    (result/reason 공통 필드는 CallBackBody에서 상속하며 camelCase alias로 직렬화된다.)
    """

    data: PriceInterpretationResult | None = None
