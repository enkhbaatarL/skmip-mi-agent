from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel


class DimensionMappingDecision(ApiModel):
    dimension_value_id: str
    mapping_version: int = Field(ge=1)
    decision: Literal["approve", "reject"]


class DimensionMappingApprovalIn(ApiModel):
    user_id: int
    decisions: list[DimensionMappingDecision]

    @model_validator(mode="after")
    def _validate_unique_decisions(self) -> DimensionMappingApprovalIn:
        value_ids = [decision.dimension_value_id for decision in self.decisions]
        if not value_ids:
            raise ValueError("decisions must not be empty")
        if len(set(value_ids)) != len(value_ids):
            raise ValueError("dimensionValueId must not be duplicated")
        return self


class DimensionMappingApprovalData(ApiModel):
    scenario_group_id: int
    parameter_mapping_ready: bool
    decisions: list[dict[str, Any]] = Field(default_factory=list)


class DimensionMappingApprovalOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "성공"
    data: DimensionMappingApprovalData | None = None
