from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.base import ApiModel


PresentationStatus = Literal["pending", "partial", "ready", "unavailable"]
EvidenceLevel = Literal["full", "limited", "none"]


class PresentationOperation(ApiModel):
    operation_id: str
    status: str
    current_phase: str | None = None
    latest_sequence: int = 0
    snapshot_revision: int = 0


class PresentationMarkdownSection(ApiModel):
    status: PresentationStatus
    evidence_level: EvidenceLevel
    content_type: Literal["text/markdown"] = "text/markdown"
    markdown: str = ""


class PresentationDimensionValue(ApiModel):
    value_id: str
    label: str
    description: str | None = None
    rationale: str = ""
    pressure_contribution: str | None = None
    lever_states: list[dict[str, Any]] = Field(default_factory=list)


class PresentationDimensionDefinition(ApiModel):
    dimension_id: str
    label: str
    description: str | None = None
    rationale: str | None = None
    source_event_ids: list[int] = Field(default_factory=list)
    model_support_status: str | None = None
    source: str | None = None
    values: list[PresentationDimensionValue] = Field(default_factory=list)


class PresentationDimensionDefinitions(ApiModel):
    status: PresentationStatus
    items: list[PresentationDimensionDefinition] = Field(default_factory=list)


class PresentationCellEvidence(ApiModel):
    value_id: str
    value_label: str
    rationale: str = ""
    pressure_contribution: str | None = None
    evidence_level: EvidenceLevel


class PresentationScenarioHeader(ApiModel):
    key: str
    label: str
    display_order: int


class PresentationScenarioRow(ApiModel):
    scenario_id: int | None = None
    display_order: int = 0
    title: str = ""
    narrative: str | None = None
    scenario_role: str | None = None
    baseline_yn: str | None = None
    pressure_target: Literal["JKM"] | None = None
    pressure_band: str | None = None
    probability_score: float | None = None
    pressure_rationale: str | None = None
    cells: dict[str, Any] = Field(default_factory=dict)
    cell_evidence: dict[str, PresentationCellEvidence] = Field(default_factory=dict)


class PresentationScenarioTable(ApiModel):
    status: PresentationStatus
    headers: list[PresentationScenarioHeader] = Field(default_factory=list)
    rows: list[PresentationScenarioRow] = Field(default_factory=list)


class PresentationScenarioDesign(ApiModel):
    status: PresentationStatus
    evidence_level: EvidenceLevel
    dimension_definitions: PresentationDimensionDefinitions
    scenario_table: PresentationScenarioTable


class PresentationSections(ApiModel):
    event_analysis: PresentationMarkdownSection
    scenario_design: PresentationScenarioDesign
    role_selection_rationale: PresentationMarkdownSection


class ScenarioGroupPresentationOut(ApiModel):
    schema_version: Literal["v1"] = "v1"
    renderer_version: str
    scenario_group_id: int
    engine_version: str
    legacy: bool
    warnings: list[str] = Field(default_factory=list)
    operation: PresentationOperation | None = None
    sections: PresentationSections
