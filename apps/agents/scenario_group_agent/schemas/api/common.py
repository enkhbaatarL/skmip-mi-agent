from __future__ import annotations

from pydantic import BaseModel

from apps.agents.scenario_group_agent.schemas.base import ApiModel


class ScenarioGroupAcceptedData(ApiModel):
    """동기 처리 완료 직후 반환하는 최소 상태 정보."""

    scenario_group_id: int
    status: str
    stage: str


class ScenarioGroupAcceptedOut(BaseModel):
    """Callback API 전환 후 3개 비동기 엔드포인트의 HTTP 200 응답 스키마."""

    status: str = "success"
    message: str = "성공"
    data: ScenarioGroupAcceptedData
