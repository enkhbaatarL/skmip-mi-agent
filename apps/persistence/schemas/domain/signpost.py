from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from pydantic import Field

from apps.persistence.schemas.base import ApiModel
from apps.persistence.schemas.enums import SignpostStrength


class SignpostBasePayload(ApiModel):
    signpost_id: int
    label: str
    probability_direction_code: str | None = None
    probability_impact_score: Decimal | None = None
    signpost_reason: str | None = None
    display_order: int = 0
    strength: str | None = None
    use_yn: str | None = None
    keyword_hints: list[str] = Field(default_factory=list)
    del_yn: str | None = None


class SignpostPayload(SignpostBasePayload):
    scenario_id: int


class DirectionCodeLike(Protocol):
    def to_string(self) -> str: ...


class GeneratedSignpostPayload(Protocol):
    scenario_id: int
    label: str
    direction: DirectionCodeLike
    strength: SignpostStrength | str | None
    rationale_ko: str
    keyword_hints: list[str]
