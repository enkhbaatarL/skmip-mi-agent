from __future__ import annotations

from typing import Literal

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.common import (
    ApiModel,
    ScenarioTable,
)
from apps.common.values.response import CommonResponse


class ValidateScenarioGroupIn(ApiModel):
    mi_event_id: int
    event_type_l2_id: int
    title: str
    summary: str | None = None
    description: str | None = None


class ValidateScenariosIn(ApiModel):
    user_id: int
    scenario_group: ValidateScenarioGroupIn
    table: ScenarioTable


class ValidationCheck(ApiModel):
    check_id: str
    stage: str
    name: str
    status: Literal["PASS", "WARN", "FAIL", "INFO"]
    detail: str
    offenders: list[str] = Field(default_factory=list)


class ValidationSummary(ApiModel):
    passed: int = Field(default=0, alias="PASS")
    warned: int = Field(default=0, alias="WARN")
    failed: int = Field(default=0, alias="FAIL")
    info: int = Field(default=0, alias="INFO")


class ValidateScenariosData(ApiModel):
    scenario_group_id: int
    is_valid: bool = False
    reason: str = ""
    status: str
    stage: str
    verdict: Literal["PASS", "REVIEW", "BLOCK"] = "BLOCK"
    summary: ValidationSummary = Field(default_factory=ValidationSummary)
    checks: list[ValidationCheck] = Field(default_factory=list)


class ValidateScenariosOut(CommonResponse):
    data: ValidateScenariosData | None = None
