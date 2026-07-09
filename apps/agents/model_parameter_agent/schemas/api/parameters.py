from __future__ import annotations

from typing import Any

from pydantic import Field

from apps.persistence.schema_base import ApiModel


class ModelParameterTarget(ApiModel):
    model_file: str
    model_sheet: str
    table_name: str
    value_field_names: list[str] = Field(default_factory=list)
    slot_axes_field_names: list[str] = Field(default_factory=list)


class ProposalParameter(ApiModel):
    parameter_name: str
    model_target: ModelParameterTarget
    rationale: str
    values: list[dict[str, Any]] = Field(default_factory=list)
