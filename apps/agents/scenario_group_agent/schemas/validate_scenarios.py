from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.common.values.response import CommonResponse


class ValidateScenariosIn(BaseModel):
    include_details: bool = Field(
        default=True,
        description="Whether to include the detailed validation result in the response",
    )


class ValidateScenariosData(BaseModel):
    scenario_group_id: int
    is_valid: bool = False
    reason: str = ""
    validation_result: dict[str, Any] | None = None


class ValidateScenariosOut(CommonResponse):
    data: ValidateScenariosData | None = None
