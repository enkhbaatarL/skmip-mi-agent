from __future__ import annotations

from decimal import Decimal

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.base import ApiModel


class SignpostPayload(ApiModel):
    signpost_id: int
    scenario_id: int | None = None
    label: str
    probability_direction_code: str | None = None
    probability_impact_score: Decimal | None = None
    signpost_reason: str | None = None
    display_order: int = 0
    strength: str | None = None
    use_yn: str | None = None
    keyword_hints: list[str] = Field(default_factory=list)
    del_yn: str | None = None
