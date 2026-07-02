from __future__ import annotations

from decimal import Decimal
from typing import Protocol

from pydantic import Field

from apps.persistence.enums import SignpostStrength
from apps.persistence.schema_base import ApiModel
from apps.persistence.signpost.models import MiSignpostModel


class SignpostPayload(ApiModel):
    signpost_id: int
    scenario_id: int
    label: str
    probability_direction_code: str | None = None
    probability_impact_score: Decimal | None = None
    signpost_reason: str | None = None
    display_order: int = 0
    strength: str | None = None
    use_yn: str | None = None
    keyword_hints: list[str] = Field(default_factory=list)
    del_yn: str | None = None

    @classmethod
    def from_model(cls, model: MiSignpostModel) -> SignpostPayload:
        return cls.model_validate(
            {
                "signpost_id": model.signpost_id,
                "scenario_id": model.scenario_id,
                "label": model.label,
                "probability_direction_code": model.probability_direction_code,
                "probability_impact_score": model.probability_impact_score,
                "signpost_reason": model.signpost_reason,
                "display_order": model.display_order,
                "strength": model.strength,
                "use_yn": model.use_yn,
                "keyword_hints": model.keyword_hints or [],
                "del_yn": getattr(model, "del_yn", None),
            }
        )


class DirectionCodeLike(Protocol):
    def to_string(self) -> str: ...


class GeneratedSignpostPayload(Protocol):
    scenario_id: int
    label: str
    direction: DirectionCodeLike
    strength: SignpostStrength | str | None
    rationale_ko: str
    keyword_hints: list[str]
