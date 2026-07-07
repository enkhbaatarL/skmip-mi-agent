from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from apps.agents.model_parameter_agent.mapping import ParameterKnowledgeBase


class ModelParameterProposalState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    scenario_id: int
    user_id: int | None = None
    basecase_dir_path: str | None = None
    max_candidates: int = 8
    max_basecase_sample_rows: int = 5
    max_basecase_cols: int = 18
    allow_llm_fallback: bool = False
    model_name: str | None = None

    scenario_context: dict[str, Any] | None = None
    parameter_knowledge_base: ParameterKnowledgeBase | None = None
    candidate_mappings: list[dict[str, Any]] = Field(default_factory=list)
    non_input_items: list[dict[str, Any]] = Field(default_factory=list)
    basecase_records: list[dict[str, Any]] = Field(default_factory=list)
    parameter_slots: list[dict[str, Any]] = Field(default_factory=list)
    parameter_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    validation_warnings: list[str] = Field(default_factory=list)
    llm_usage: dict[str, Any] | None = None
    llm_calls: list[dict[str, Any]] = Field(default_factory=list)
