from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    EventInteraction,
    EventShock,
    ExcludedDimensionDecision,
    PressureBand,
    V2DimensionDefinition,
    V2EventShock,
    V2SourceReference,
    V3DimensionDefinition,
    V3EventShock,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDefinition,
    V4EventAnalysisExclusion,
    V4EventFact,
    V4EventImpactPath,
    V4EventInteraction,
    V4ForecastClaim,
    V4InteractionUncertainty,
    V4PathUncertainty,
    V4ScenarioCountRange,
    V4ScenarioCountShortfall,
    V4SimilarScenarioPair,
    V4ValidationWarning,
)
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.table import ScenarioTable
from apps.common.values.llm_usage import LLMUsageModel
from apps.persistence.event.schema import EventPayload
from apps.persistence.model_impact_lever.schema import ModelImpactLeverSupportIssue
from apps.persistence.scenario.schema import DimensionDefinition
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


ApiVersion = Literal["v1", "v2", "v3", "v4"]
GenerationStrategy = Literal[
    "single_event_template_dimensions",
    "multi_event_source_dimensions",
    "multi_event_composite_dimensions",
    "multi_event_model_lever_dimensions",
]


class MultiEventCreateScenariosIn(ApiModel):
    mi_event_ids: list[int] = Field(min_length=1, max_length=5)
    user_id: int

    @model_validator(mode="after")
    def _validate_event_ids(self) -> MultiEventCreateScenariosIn:
        if len(set(self.mi_event_ids)) != len(self.mi_event_ids):
            msg = "miEventIds must not contain duplicates"
            raise ValueError(msg)
        if any(event_id <= 0 for event_id in self.mi_event_ids):
            msg = "miEventIds must contain positive IDs"
            raise ValueError(msg)
        return self


class V4MultiEventCreateScenariosIn(ApiModel):
    mi_event_ids: list[int] = Field(min_length=1, max_length=5)
    user_id: int

    @model_validator(mode="after")
    def _validate_v4_request(self) -> V4MultiEventCreateScenariosIn:
        if len(set(self.mi_event_ids)) != len(self.mi_event_ids):
            msg = "miEventIds must not contain duplicates"
            raise ValueError(msg)
        if any(event_id <= 0 for event_id in self.mi_event_ids):
            msg = "miEventIds must contain positive IDs"
            raise ValueError(msg)
        return self


class V4MultiEventCreateScenariosSyncIn(V4MultiEventCreateScenariosIn):
    pass


class ExcludedCandidate(ApiModel):
    pressure_band: Literal[
        "strong_bullish",
        "bullish",
        "balanced",
        "bearish",
        "strong_bearish",
    ]
    reason_code: str
    reason: str
    dimension_values: dict[str, str] = Field(default_factory=dict)


class V3TemplateDimensionSelectionDiagnostic(ApiModel):
    event_id: int
    scenario_dimension_template_id: int
    dim_key: str
    relevance_type: Literal[
        "direct_event_fact",
        "lng_impact_path",
        "interaction_driver",
    ]
    observed_basis: str
    selection_rationale: str
    label: str
    description: str
    required: bool
    value_enum_examples: list[str] = Field(default_factory=list)
    used_in_dimension_ids: list[str] = Field(default_factory=list)


class AdditionalDimensionGeneration(ApiModel):
    status: Literal[
        "not_requested",
        "queued",
        "running",
        "ready",
        "failed",
        "interrupted",
        "discarded",
    ] = "not_requested"
    source_fingerprint: str | None = None
    source_uncertainty_ids: list[str] = Field(default_factory=list)
    queued_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None


class GenerationDiagnostics(ApiModel):
    target_pressure_bands: list[str] = Field(
        default_factory=lambda: [
            "strong_bullish",
            "bullish",
            "balanced",
            "bearish",
            "strong_bearish",
        ],
    )
    excluded_candidates: list[ExcludedCandidate] = Field(default_factory=list)
    excluded_dimensions: list[ExcludedDimensionDecision | dict[str, object]] = Field(
        default_factory=list,
    )
    impact_catalog_version: str | None = None
    covered_dimensions: list[str] = Field(default_factory=list)
    uncovered_dimensions: list[str] = Field(default_factory=list)
    unsupported_levers: list[str] = Field(default_factory=list)
    unsupported_lever_details: list[ModelImpactLeverSupportIssue] = Field(
        default_factory=list,
    )
    coverage_status: Literal["full", "partial", "none"] | None = None
    analysis_as_of: str | None = None
    event_shocks: list[V3EventShock | EventShock] = Field(default_factory=list)
    event_facts: list[V4EventFact] = Field(default_factory=list)
    # 내부 진단: Event 원문에서 서버가 전망·계획으로 판정한 문장과 전망 고유값.
    forecast_claims: list[V4ForecastClaim] = Field(default_factory=list)
    decision_basis: list[str] = Field(default_factory=list)
    event_exclusions: list[V4EventAnalysisExclusion] = Field(default_factory=list)
    impact_paths: list[V4EventImpactPath] = Field(default_factory=list)
    path_uncertainties: list[V4PathUncertainty] = Field(default_factory=list)
    event_interactions: list[V4EventInteraction | EventInteraction] = Field(
        default_factory=list,
    )
    interaction_uncertainties: list[V4InteractionUncertainty] = Field(default_factory=list)
    validation_warnings: list[V4ValidationWarning] = Field(default_factory=list)
    scenario_pressure_breakdowns: list[dict[str, object]] = Field(default_factory=list)
    additional_dimension_generation: AdditionalDimensionGeneration = Field(
        default_factory=AdditionalDimensionGeneration,
    )
    additional_dimension_candidates: list[V4DimensionDefinition] = Field(default_factory=list)
    # v4 Scenario 합성 정책과 개수 진단. 정책 도입 전에 만든 그룹은 None·빈 값이다.
    scenario_synthesis_policy: str | None = None
    scenario_count_range: V4ScenarioCountRange | None = None
    scenario_count_shortfall: V4ScenarioCountShortfall | None = None
    direction_coverage_gaps: list[str] = Field(default_factory=list)
    similar_scenario_pairs: list[V4SimilarScenarioPair] = Field(default_factory=list)


class V3GenerationDiagnostics(GenerationDiagnostics):
    template_dimension_selections: list[V3TemplateDimensionSelectionDiagnostic] = Field(default_factory=list)


class V2GenerationDiagnostics(ApiModel):
    """Compact diagnostics computed by the v2 server finalizer."""

    target_pressure_bands: list[PressureBand] = Field(
        default_factory=lambda: [
            "strong_bullish",
            "bullish",
            "balanced",
            "bearish",
            "strong_bearish",
        ],
    )
    event_shocks: list[V2EventShock]
    unselected_dimension_refs: list[V2SourceReference] = Field(default_factory=list)
    unrepresented_pressure_bands: list[PressureBand] = Field(default_factory=list)


class V2CreateScenariosData(ApiModel):
    api_version: Literal["v2"] = "v2"
    generation_strategy: Literal["multi_event_source_dimensions"] = "multi_event_source_dimensions"
    scenario_group: ScenarioGroupPayload
    events: list[EventPayload] = Field(default_factory=list)
    dimension_definitions: list[V2DimensionDefinition] = Field(default_factory=list)
    table: ScenarioTable
    generation_diagnostics: V2GenerationDiagnostics
    usage: LLMUsageModel | None = None


class V2CreateScenariosOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "성공"
    data: V2CreateScenariosData | None = None


class VersionedCreateScenariosData(ApiModel):
    api_version: ApiVersion
    generation_strategy: GenerationStrategy
    impact_catalog_version: str | None = None
    scenario_group: ScenarioGroupPayload
    events: list[EventPayload] = Field(default_factory=list)
    dimension_definitions: list[V4DimensionDefinition | V3DimensionDefinition | DimensionDefinition] = Field(
        default_factory=list,
    )
    table: ScenarioTable
    generation_diagnostics: V3GenerationDiagnostics | GenerationDiagnostics = Field(
        default_factory=GenerationDiagnostics,
    )
    usage: LLMUsageModel | None = None


class VersionedCreateScenariosOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "성공"
    data: VersionedCreateScenariosData | None = None
