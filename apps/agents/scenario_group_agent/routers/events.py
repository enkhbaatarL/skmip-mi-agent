from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from apps.agents.scenario_group_agent.schemas.endpoint import EventDetailOut, EventListOut
from apps.persistence.event.service import EventService


router = APIRouter(tags=["events"])


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
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    sort: str = Query(default="latest"),
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
