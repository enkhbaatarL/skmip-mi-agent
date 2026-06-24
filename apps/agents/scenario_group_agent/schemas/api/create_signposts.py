from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

from apps.agents.scenario_group_agent.schemas.api.table import (
    ScenarioHeader,
    ScenarioTable,
)
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.domain.scenario_group import (
    ScenarioGroupPayload,
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
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    user_id: int
    table: CreateSignpostsTableIn


class CreateSignpostsOut(CallBackBody):
    scenario_group: ScenarioGroupPayload | None = None
    table: ScenarioTable | None = None
