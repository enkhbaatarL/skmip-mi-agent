from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header

from apps.agents.event_generate_agent.flows.generate_from_query.api_schema import (
    GenerateFromQueryIn,
    GenerateFromQueryOut,
)
from apps.agents.event_generate_agent.flows.generate_from_query.flow import run_generate_from_query


router = APIRouter()


@router.post(
    "/events/generations",
    response_model=GenerateFromQueryOut,
    summary="사용자 입력 문장 기반 이벤트 생성",
    description=(
        "사용자 입력 문장을 분석해 웹 검색 또는 기존 이벤트 검색 중 한 분기로 근거를 "
        "수집하고, 그 근거로 이벤트 초안을 생성해 즉시 반환합니다. "
        "응답 meta에 선택된 분기와 그 근거가 함께 담깁니다."
    ),
)
async def create_event_generation(
    payload: GenerateFromQueryIn,
    user_id: Annotated[
        int,
        Header(
            alias="X-User-ID",
            description=(
                "B.E가 인증한 요청 사용자의 ID입니다. "
                "이벤트 저장 시 생성자·수정자 ID로 사용합니다. "
                "인증 토큰이 아닙니다."
            ),
        ),
    ],
) -> GenerateFromQueryOut:
    result = await run_generate_from_query(
        user_query=payload.user_query,
        date_from=payload.date_from,
        date_to=payload.date_to,
        user_id=user_id,  # 기존 payload.user_id 대신 header 값을 전달
    )
    return GenerateFromQueryOut(
        message="이벤트 생성 결과입니다.",
        data=result,
    )
