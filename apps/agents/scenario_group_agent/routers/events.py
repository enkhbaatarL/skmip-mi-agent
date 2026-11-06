from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Path, Query

from apps.agents.scenario_group_agent.persistence.event_recommendation_service import EventRecommendationService
from apps.agents.scenario_group_agent.persistence.event_verification_service import EventVerificationService
from apps.agents.scenario_group_agent.persistence.event_verification_update_service import (
    EventVerificationUpdateService,
)
from apps.agents.scenario_group_agent.schemas.api.event_recommendations import (
    EventRecommendationsIn,
    EventRecommendationsOut,
)
from apps.agents.scenario_group_agent.schemas.api.event_verification_updates import (
    EventVerificationUpdateIn,
    EventVerificationUpdateOut,
)
from apps.agents.scenario_group_agent.schemas.api.event_verifications import EventVerificationsIn, EventVerificationsOut
from apps.agents.scenario_group_agent.schemas.endpoint import EventDetailOut, EventListOut
from apps.persistence.event.service import EventService


router = APIRouter(tags=["events"])


@router.post(
    "/events/{mi_event_id}/verification-updates",
    response_model=EventVerificationUpdateOut,
    summary="저장된 검증 근거로 수정안을 재검증하고 Snapshot 저장 후 Event 업데이트",
)
async def update_verified_event(
    body: EventVerificationUpdateIn,
    mi_event_id: Annotated[int, Path(gt=0)],
) -> EventVerificationUpdateOut:
    return await EventVerificationUpdateService().update(mi_event_id, body)


@router.post(
    "/events/verifications",
    response_model=EventVerificationsOut,
    summary="시나리오 설계 전 Event 사실·최신성 웹 검증",
)
async def verify_events(body: EventVerificationsIn) -> EventVerificationsOut:
    return await EventVerificationService().verify(body.mi_event_ids, body.actor_usr_logn_id)


@router.post(
    "/events/recommendations",
    response_model=EventRecommendationsOut,
    summary="선택한 Event와 관련된 Event 최대 2개 추천",
)
async def recommend_events(body: EventRecommendationsIn) -> EventRecommendationsOut:
    return await EventRecommendationService().recommend(body.mi_event_ids)


@router.get(
    "/events",
    response_model=EventListOut,
    summary="MI Event 목록 조회",
    description="Backoffice Event List 화면에서 사용하는 MI Event 목록과 관련 Scenario Group 요약을 반환합니다.",
)
async def list_events(
    *,
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None, description="new 또는 updated"),
    event_type_l1_id: int | None = Query(default=None, alias="eventTypeL1Id"),
    event_type_l2_id: int | None = Query(default=None, alias="eventTypeL2Id"),
    recommended_only: Annotated[bool, Query(alias="recommendedOnly")] = False,
    date_from: str | None = Query(
        default=None,
        alias="dateFrom",
        description="조회 시작일. ISO 형식 YYYY-MM-DD",
    ),
    date_to: str | None = Query(
        default=None,
        alias="dateTo",
        description="조회 종료일. ISO 형식 YYYY-MM-DD",
    ),
    sort: str = Query(default="latest", description="latest 또는 oldest"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
) -> EventListOut:
    result = EventService().list_events(
        keyword=keyword,
        status=status,
        event_type_l1_id=event_type_l1_id,
        event_type_l2_id=event_type_l2_id,
        recommended_only=recommended_only,
        date_from=_parse_date(date_from),
        date_to=_parse_date(date_to),
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return EventListOut.model_validate(result)


@router.get(
    "/events/{mi_event_id}",
    response_model=EventDetailOut,
    summary="MI Event 상세 조회",
    description="Event metadata, 상세 분석, source record, scenario template, 관련 Scenario Group 요약을 반환합니다.",
)
async def get_event_detail(mi_event_id: int) -> EventDetailOut:
    return EventDetailOut.model_validate(EventService().get_event_detail(mi_event_id))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)
