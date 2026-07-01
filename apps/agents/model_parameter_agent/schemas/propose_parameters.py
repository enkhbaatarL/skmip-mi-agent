from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, field_validator

from apps.agents.scenario_group_agent.schemas.common import ApiModel


class ProposeParametersIn(ApiModel):
    mapping_excel_path: str | None = Field(default=None)
    basecase_dir_path: str | None = Field(default=None)
    max_candidates: int = Field(default=8, ge=1, le=30)
    max_basecase_sample_rows: int = Field(default=5, ge=1, le=20)
    max_basecase_cols: int = Field(default=18, ge=6, le=60)
    allow_llm_fallback: bool = Field(default=False)
    model_name: str | None = Field(default=None)


class ParameterCandidate(ApiModel):
    candidate_key: str
    event_no: int | None = None
    event_label: str | None = None
    source_dimension_id: str | None = None
    source_dimension_label: str | None = None
    source_dimension_value: Any = None
    mapping_method: str
    model_file: str | None = None
    model_sheet: str | None = None
    parameter_name: str
    canonical_parameter_name: str
    unit: str | None = None
    semantic_axes: str | None = None
    mapping_comment: str | None = None
    basecase_available: bool = False


class ParameterSlotAxis(ApiModel):
    axis_name: str
    axis_value: str
    rationale: str | None = None


class ParameterValueCell(ApiModel):
    coordinates: dict[str, Any] = Field(default_factory=dict)
    basecase_value: Any = None
    proposed_value: Any = None
    unit: str | None = None
    operation: Literal[
        "absolute",
        "delta",
        "percent_change",
        "overwrite",
        "not_applicable",
        "unknown",
    ] = "unknown"
    value_selection_rationale_ko: str
    proposed_value_rationale_ko: str
    basecase_reference_ids: list[str] = Field(default_factory=list)


class ParameterAdjustment(ApiModel):
    candidate_key: str
    model_file: str
    model_sheet: str
    parameter_name: str
    selected: bool = True
    slot_axes: list[ParameterSlotAxis] = Field(default_factory=list)
    value_grid: list[ParameterValueCell] = Field(default_factory=list)
    parameter_selection_rationale_ko: str
    confidence_overall: float = Field(ge=0.0, le=1.0)
    needs_user_review: bool = False
    warnings: list[str] = Field(default_factory=list)

    @field_validator("slot_axes", mode="before")
    @classmethod
    def _coerce_slot_axes(cls, value: Any) -> Any:
        return value or []

    @field_validator("value_grid", mode="before")
    @classmethod
    def _coerce_value_grid(cls, value: Any) -> Any:
        return value or []


class ParameterSlotProposal(ApiModel):
    candidate_key: str
    selected: bool = True
    slot_axes: list[ParameterSlotAxis] = Field(default_factory=list)
    rationale_ko_overall: str
    confidence_overall: float = Field(ge=0.0, le=1.0)
    needs_user_review: bool = False
    warnings: list[str] = Field(default_factory=list)

    @field_validator("slot_axes", mode="before")
    @classmethod
    def _coerce_slot_axes(cls, value: Any) -> Any:
        return value or []


class ParameterCandidateDecision(ApiModel):
    candidate_key: str
    selected: bool
    rationale_ko: str
    confidence_overall: float = Field(ge=0.0, le=1.0)
    warnings: list[str] = Field(default_factory=list)


class NonInputItem(ApiModel):
    source_dimension_label: str | None = None
    source_dimension_value: Any = None
    mapping_method: str
    reason: str


class BasecaseRecord(ApiModel):
    candidate_key: str
    model_file: str
    sheet_name: str
    parameter_name: str
    reference_id: str
    axes: dict[str, Any] = Field(default_factory=dict)
    value_name: str | None = None
    value: Any = None
    unit: str | None = None
    source_row: int
    source_col: int


class LLMParameterProposalResponse(ApiModel):
    parameter_adjustments: list[ParameterAdjustment] = Field(default_factory=list)
    non_input_items: list[NonInputItem] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class LLMCandidateValidationResponse(ApiModel):
    candidate_decisions: list[ParameterCandidateDecision] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class LLMSlotProposalResponse(ApiModel):
    parameter_slots: list[ParameterSlotProposal] = Field(default_factory=list)
    non_input_items: list[NonInputItem] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class LLMValueProposalResponse(ApiModel):
    parameter_adjustments: list[ParameterAdjustment] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)


class ModelParameterTarget(ApiModel):
    model_file: str
    model_sheet: str
    value_field_names: list[str] = Field(default_factory=list)
    slot_axes_field_names: list[str] = Field(default_factory=list)


class ProposalParameter(ApiModel):
    parameter_name: str
    model_target: ModelParameterTarget
    rationale: str
    values: list[dict[str, Any]] = Field(default_factory=list)


class ProposeParametersData(ApiModel):
    model_param_proposal_id: int | None = None
    scenario_id: int | None = None
    scenario_group_id: int | None = None
    event_id: int | None = None
    proposal_parameters: list[ProposalParameter] = Field(default_factory=list)


class ProposeParametersOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "model parameter proposal completed"
    data: ProposeParametersData
