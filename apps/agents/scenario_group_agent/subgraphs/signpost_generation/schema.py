from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.persistence.enums import DirectionCode, SignpostStrength


class GeneratedSignpost(ApiModel):
    scenario_id: int
    signpost_id: int | None = None
    signpost_class: Literal["observation"] = "observation"
    label: str
    signpost_source: Literal["mi_record"] = "mi_record"
    direction: DirectionCode = DirectionCode.SUP
    strength: SignpostStrength | None = None
    rationale_ko: str = ""
    keyword_hints: list[str] = Field(default_factory=list)


class SignpostGenerationResult(ApiModel):
    scenario_group_id: int | None = None
    scenario_results: list[dict[str, Any]] = Field(default_factory=list)
    signposts: list[GeneratedSignpost] = Field(default_factory=list)
