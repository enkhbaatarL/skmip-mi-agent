from __future__ import annotations

from typing import Any

from pydantic import Field

from apps.persistence.schema_base import ApiModel


class ModelParameterDefinitionPayload(ApiModel):
    canonical_parameter_name: str
    parameter_hint: str | None = None
    model_file: str
    model_sheet: str
    model_table: str
    parameter_name: str
    semantic_axes: str | None = None
    basecase_read_mode: str
    basecase_header_row: int
    basecase_data_start_row: int
    basecase_column_roles: str
    basecase_row_filter: str | None = None
    basecase_year_row: int | None = None
    basecase_month_row: int | None = None
    basecase_period_row: int | None = None
    basecase_value_start_col: str | None = None
    basecase_value_end_col: str | None = None
    basecase_stop_rule: str


class ModelParameterMappingRulePayload(ApiModel):
    event_type_l2_id: int
    dimension_key: str
    dimension_label: str
    canonical_parameter_name: str
    mapping_method: str
    comment: str | None = None


class ModelParameterProposalPayload(ApiModel):
    model_param_proposal_id: int | None = None
    scenario_id: int
    scenario_group_id: int
    mi_event_id: int | None = None
    status: str
    proposal_parameters: list[dict[str, Any]] = Field(default_factory=list)
    confirmation_parameters: list[dict[str, Any]] | None = None
