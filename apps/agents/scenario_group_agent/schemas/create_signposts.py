from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioGroupPayload,
    ScenarioHeader,
    ScenarioTable,
)
from apps.agents.scenario_group_agent.schemas.enums import (
    DirectionCode,
    SignpostStrength,
)
from apps.common.values.response import CallBackBody


class CreateSignpostsHeaderIn(ScenarioHeader):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )


class CreateSignpostsRowIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    cells: dict[str, Any] = Field(default_factory=dict)


class CreateSignpostsTableIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    headers: list[CreateSignpostsHeaderIn]
    rows: list[CreateSignpostsRowIn]


class CreateSignpostsIn(ApiModel):
    user_id: int
    table: CreateSignpostsTableIn


class CreateSignpostsOut(CallBackBody):
    scenario_group: ScenarioGroupPayload | None = None
    table: ScenarioTable | None = None


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
    scenario_results: list[dict] = Field(default_factory=list)
    signposts: list[GeneratedSignpost] = Field(default_factory=list)
