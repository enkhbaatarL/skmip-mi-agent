from __future__ import annotations

from typing import Annotated

from pydantic import ConfigDict, Field, field_validator

from apps.agents.scenario_group_agent.schemas.api.execution_log import AgentExecutionEvent
from apps.agents.scenario_group_agent.schemas.base import ApiModel


class EventRecommendationsIn(ApiModel):
    model_config = ConfigDict(extra="forbid")
    mi_event_ids: list[Annotated[int, Field(strict=True, gt=0)]] = Field(min_length=1, max_length=5)

    @field_validator("mi_event_ids")
    @classmethod
    def unique_ids(cls, value: list[int]) -> list[int]:
        if len(value) != len(set(value)):
            message = "miEventIds에는 중복 ID를 넣을 수 없습니다."
            raise ValueError(message)
        return value


class RecommendedEvent(ApiModel):
    mi_event_id: int
    title: str
    reason: str


class EventRecommendationsOut(ApiModel):
    execution_log: list[AgentExecutionEvent] = Field(default_factory=list)
    items: list[RecommendedEvent] = Field(max_length=2)
    selection_reason: str
