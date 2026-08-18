from __future__ import annotations

# ruff: noqa: CPY001
from typing import Any

from pydantic import ConfigDict, Field

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.table import ScenarioHeader, ScenarioTable
from apps.common.values.llm_usage import LLMUsageModel
from apps.common.values.response import CallBackBody


class ValidateScenariosHeaderIn(ScenarioHeader):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )


class ValidateScenariosRowIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    cells: dict[str, Any] = Field(default_factory=dict)


class ValidateScenariosTableIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    headers: list[ValidateScenariosHeaderIn]
    rows: list[ValidateScenariosRowIn]


class ValidateScenariosIn(ApiModel):
    model_config = ConfigDict(
        alias_generator=ApiModel.model_config["alias_generator"],
        populate_by_name=True,
        extra="forbid",
    )

    user_id: int
    table: ValidateScenariosTableIn


class ValidateScenariosCallBackScenarioGroup(ApiModel):
    scenario_group_id: int
    status: str
    stage: str


class ValidateScenariosOut(CallBackBody):
    verdict: str | None = None
    is_valid: bool | None = None
    can_proceed: bool | None = None
    review_skipped: bool | None = None
    summary: dict[str, int] = Field(default_factory=dict)
    checks: list[dict[str, Any]] = Field(default_factory=list)
    generated_details: list[dict[str, Any]] = Field(default_factory=list)
    scenario_group: ValidateScenariosCallBackScenarioGroup | None = None
    table: ScenarioTable | None = None
    mapping_proposals: list[dict[str, Any]] = Field(default_factory=list)
    parameter_mapping_ready: bool | None = None


class ValidateScenariosSyncOut(ValidateScenariosOut):
    usage: LLMUsageModel | None = None
