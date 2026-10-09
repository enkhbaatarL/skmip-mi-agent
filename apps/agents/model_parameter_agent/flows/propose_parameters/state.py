from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.agents.model_parameter_agent.utils.lut.models import BasecaseIndex
from apps.agents.model_parameter_agent.utils.mi_base_resources import (
    MiBaseResourceSelection,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import ParameterKnowledgeBase


class ModelParameterProposalOutputState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scenario_id: int
    user_id: int | None = None
    model_name: str | None = None

    scenario_context: dict[str, Any] | None = None
    candidate_mappings: list[dict[str, Any]] = Field(default_factory=list)
    non_input_items: list[dict[str, Any]] = Field(default_factory=list)
    slot_catalog: list[dict[str, Any]] = Field(default_factory=list)
    slot_candidate_mappings: list[dict[str, Any]] = Field(default_factory=list)
    effective_references: list[dict[str, Any]] = Field(default_factory=list)
    resolved_config: dict[str, Any] = Field(default_factory=dict)
    lut_version: str | None = None

    parameter_slots: list[dict[str, Any]] = Field(default_factory=list)
    slot_selection_diagnostics: dict[str, int] = Field(default_factory=dict)
    parameter_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    value_selection_diagnostics: dict[str, int] = Field(default_factory=dict)
    validation_warnings: list[str] = Field(default_factory=list)
    llm_usage: dict[str, Any] | None = None
    llm_calls: list[dict[str, Any]] = Field(default_factory=list)


class ModelParameterProposalState(ModelParameterProposalOutputState):
    mi_base_case_id: int | None = Field(default=None, exclude=True)
    mi_base_selection_resolved: bool = Field(default=False, exclude=True)
    # Request-local runtime objects are omitted from Pydantic dumps and the
    # graph output schema so full workbook rows never become API/trace output.
    parameter_knowledge_base: ParameterKnowledgeBase | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    basecase_index: BasecaseIndex | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
    mi_base_resources: MiBaseResourceSelection | None = Field(
        default=None,
        exclude=True,
        repr=False,
    )
