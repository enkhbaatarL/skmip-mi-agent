from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from apps.persistence.schema_base import ApiModel


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
    model_table: str | None = None
    parameter_name: str
    canonical_parameter_name: str
    parameter_hint: str | None = None
    semantic_axes: str | None = None
    mapping_comment: str | None = None
    basecase_available: bool = False


class ParameterSlotAxis(ApiModel):
    axis_name: str
    axis_value: Any = Field(
        description=(
            "Slot axis value. If axis_name is Year, Month, or Period, return an "
            'integer JSON number such as 2026, not a string such as "2026".'
        ),
    )


class LLMSlotAxis(ApiModel):
    axis_name: str
    axis_value: Any = Field(
        description=(
            "Slot axis value. If axis_name is Year, Month, or Period, return an "
            'integer JSON number such as 2026, not a string such as "2026".'
        ),
    )


class ParameterValueCell(ApiModel):
    coordinates: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Exact slot coordinates. Values for Year, Month, and Period keys must be "
            'integer JSON numbers such as 2026, not strings such as "2026".'
        ),
    )
    basecase_value: Any = None
    lut_value: Any = None
    proposed_value: Any = None
    rationale_ko: str
    basecase_reference_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_rationale(cls, value: Any) -> Any:
        if isinstance(value, BaseModel):
            value = value.model_dump()
        if not isinstance(value, dict):
            return value
        if value.get("rationale_ko"):
            return value
        value_selection = str(value.get("value_selection_rationale_ko") or "").strip()
        proposed_value = str(value.get("proposed_value_rationale_ko") or "").strip()
        rationale = " ".join(
            item
            for item in (value_selection, proposed_value)
            if item
        )
        return {
            **value,
            "rationale_ko": rationale or "값 선택 및 제안 근거가 제공되지 않았습니다.",
        }


class ParameterAdjustment(ApiModel):
    candidate_key: str
    model_file: str | None = None
    model_sheet: str | None = None
    parameter_name: str
    selected: bool = True
    slot_axes: list[ParameterSlotAxis] = Field(default_factory=list)
    value_grid: list[ParameterValueCell] = Field(default_factory=list)
    parameter_selection_rationale_ko: str

    @field_validator("slot_axes", mode="before")
    @classmethod
    def _coerce_slot_axes(cls, value: Any) -> Any:
        return value or []

    @field_validator("value_grid", mode="before")
    @classmethod
    def _coerce_value_grid(cls, value: Any) -> Any:
        return value or []


class LLMValueCell(ApiModel):
    # Optional only at the receive boundary so a malformed item can be dropped
    # without retrying the entire LLM call. The prompt still requires every key.
    slot_key: str | None = Field(
        default=None,
        description=(
            "Return the exact input slot_key for every slot. The nullable receive "
            "boundary exists only so malformed items can be dropped without retry."
        ),
    )
    proposed_value: Any
    rationale_ko: str


class LLMValueAdjustment(ApiModel):
    candidate_key: str
    slot_values: list[LLMValueCell] = Field(default_factory=list)
    rationale_ko: str

    @field_validator("slot_values", mode="before")
    @classmethod
    def _coerce_slot_values(cls, value: Any) -> Any:
        return value or []


class LLMSlotProposal(ApiModel):
    candidate_key: str
    slot_axes: list[LLMSlotAxis] = Field(default_factory=list)

    @field_validator("slot_axes", mode="before")
    @classmethod
    def _coerce_slot_axes(cls, value: Any) -> Any:
        return value or []


class ParameterSlotProposal(ApiModel):
    candidate_key: str
    slot_key: str | None = None
    slot_axes: list[ParameterSlotAxis] = Field(default_factory=list)

    @field_validator("slot_axes", mode="before")
    @classmethod
    def _coerce_slot_axes(cls, value: Any) -> Any:
        return value or []


class RoutingDecision(ApiModel):
    dimension_key: str
    selected_candidate_keys: list[str] = Field(default_factory=list)


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
    source_row: int
    source_col: int


class LLMCandidateValidationResponse(ApiModel):
    routing_decisions: list[RoutingDecision] = Field(
        default_factory=list,
    )


class LLMSlotProposalResponse(ApiModel):
    parameter_slots: list[LLMSlotProposal] = Field(default_factory=list)


class LLMValueProposalResponse(ApiModel):
    parameter_adjustments: list[LLMValueAdjustment] = Field(default_factory=list)
