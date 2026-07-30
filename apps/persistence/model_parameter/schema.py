from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from apps.persistence.schema_base import ApiModel


KnownUnsupportedReasonCode = Literal[
    "NO_PARAMETER_BINDING",
    "INACTIVE_MODEL_PARAMETER",
    "CATALOG_MARKED_UNSUPPORTED",
]
ModelSupportIssueReasonCode = Literal[
    "NO_PARAMETER_BINDING",
    "INACTIVE_MODEL_PARAMETER",
    "CATALOG_MARKED_UNSUPPORTED",
    "PRICE_ONLY",
]


class ModelParameterDefinitionPayload(ApiModel):
    model_param_id: int | None = None
    use_yn: str = "Y"
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


class ModelImpactLeverParameterBinding(ApiModel):
    parameter_name: str
    role: Literal["primary", "alternative"] = "primary"
    applicability: str = ""
    support_status: Literal["executable", "known_unsupported"]
    unsupported_reason_code: (
        Literal[
            "INACTIVE_MODEL_PARAMETER",
            "CATALOG_MARKED_UNSUPPORTED",
        ]
        | None
    ) = None

    @model_validator(mode="after")
    def _validate_unsupported_reason(self) -> ModelImpactLeverParameterBinding:
        if self.support_status == "executable" and self.unsupported_reason_code is not None:
            raise ValueError("executable binding must not define unsupportedReasonCode")
        if self.support_status == "known_unsupported" and self.unsupported_reason_code is None:
            raise ValueError("known_unsupported binding requires unsupportedReasonCode")
        return self


class ModelImpactLeverPayload(ApiModel):
    impact_lever_id: int
    lever_code: str
    domain: Literal["demand", "supply", "trade", "price_only"]
    label: str
    description: str
    applicability_hint: str | None = None
    parent_lever_code: str | None = None
    parameter_bindings: list[ModelImpactLeverParameterBinding] = Field(
        default_factory=list,
    )
    catalog_version: str

    @model_validator(mode="after")
    def _validate_bindings(self) -> ModelImpactLeverPayload:
        names = [binding.parameter_name for binding in self.parameter_bindings]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate parameter binding: leverCode={self.lever_code}")
        if self.domain == "price_only" and self.parameter_bindings:
            raise ValueError("price_only lever must not define parameter bindings")
        return self


class ModelImpactLeverSupportIssue(ApiModel):
    lever_code: str
    reason_code: ModelSupportIssueReasonCode
    parameter_name: str | None = None


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
