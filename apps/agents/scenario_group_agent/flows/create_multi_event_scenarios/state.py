from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    GenerationDiagnostics,
    V2GenerationDiagnostics,
    V3GenerationDiagnostics,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    EventInteraction,
    MultiEventGenerationResult,
    V2DimensionDefinition,
    V2DimensionDesignResult,
    V2EventShock,
    V2FinalizedGenerationResult,
    V2ScenarioSynthesisResult,
    V3AnalysisDesignResult,
    V3DimensionDefinition,
    V3DimensionDesignResult,
    V3EventShock,
    V3MultiEventGenerationResult,
    V3ScenarioSynthesisResult,
    V3TemplateDimensionSelection,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    ParameterCoverage,
    V4DimensionDesignDraft,
    V4DimensionDesignResult,
    V4EventImpactAnalysisDraft,
    V4EventImpactAnalysisResult,
    V4GenerationResult,
    V4ReadableInteractionAnalysisDraft,
    V4ScenarioSynthesisResult,
)
from apps.persistence.event.schema import EventPayload
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload
from apps.persistence.scenario.schema import ScenarioPayload, ScenarioPipelineTemplate
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


GenerationStage = Literal[
    "event_template_analysis",
    "event_impact_analysis",
    "event_interaction_analysis",
    "dimension_design",
    "scenario_synthesis",
    "persistence",
]


class MultiEventGenerationState(BaseModel):
    scenario_group: ScenarioGroupPayload | None = None
    events: list[EventPayload] = Field(default_factory=list)
    templates: list[ScenarioPipelineTemplate] = Field(default_factory=list)
    api_version: Literal["v2", "v3"] = "v2"
    generation_strategy: str = ""
    user_id: int | None = None

    event_shocks: list[V2EventShock | V3EventShock] = Field(default_factory=list)

    analysis_attempt: int = 0
    analysis_draft: V3AnalysisDesignResult | None = None
    template_dimension_selections: list[V3TemplateDimensionSelection] = Field(default_factory=list)
    analysis_error: str | None = None
    analysis_error_code: str | None = None
    analysis_retryable: bool = False

    dimension_attempt: int = 0
    dimension_draft: V2DimensionDesignResult | V3DimensionDesignResult | None = None
    dimension_definitions: list[V2DimensionDefinition | V3DimensionDefinition] = Field(default_factory=list)
    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_error: str | None = None
    dimension_error_code: str | None = None
    dimension_retryable: bool = False

    scenario_attempt: int = 0
    scenario_draft: V2ScenarioSynthesisResult | V3ScenarioSynthesisResult | None = None
    scenario_error: str | None = None
    scenario_error_code: str | None = None
    scenario_retryable: bool = False

    finalized_result: V2FinalizedGenerationResult | MultiEventGenerationResult | V3MultiEventGenerationResult | None = (
        None
    )
    generation_diagnostics: V2GenerationDiagnostics | V3GenerationDiagnostics | GenerationDiagnostics | None = None
    saved_group: ScenarioGroupPayload | None = None
    saved_scenarios: list[ScenarioPayload] = Field(default_factory=list)

    failed_stage: GenerationStage | None = None
    terminal_error: str | None = None
    terminal_error_code: str | None = None


class V4MultiEventGenerationState(BaseModel):
    scenario_group: ScenarioGroupPayload | None = None
    events: list[EventPayload] = Field(default_factory=list)
    impact_levers: list[ModelImpactLeverPayload] = Field(default_factory=list)
    impact_catalog_version: str = ""
    impact_catalog_checksum: str = ""
    user_id: int | None = None
    analysis_as_of: str = ""

    analysis_attempt: int = 0
    analysis_draft: V4EventImpactAnalysisDraft | V4EventImpactAnalysisResult | None = None
    analysis_error: str | None = None
    analysis_error_code: str | None = None
    analysis_retryable: bool = False

    interaction_attempt: int = 0
    interaction_draft: V4ReadableInteractionAnalysisDraft | None = None
    interaction_error: str | None = None
    interaction_error_code: str | None = None
    interaction_retryable: bool = False

    dimension_attempt: int = 0
    dimension_draft: V4DimensionDesignDraft | V4DimensionDesignResult | None = None
    dimension_error: str | None = None
    dimension_error_code: str | None = None
    dimension_retryable: bool = False

    scenario_attempt: int = 0
    scenario_draft: V4ScenarioSynthesisResult | None = None
    scenario_error: str | None = None
    scenario_error_code: str | None = None
    scenario_retryable: bool = False

    finalized_result: V4GenerationResult | None = None
    parameter_coverage: ParameterCoverage | None = None
    generation_diagnostics: GenerationDiagnostics | None = None
    saved_group: ScenarioGroupPayload | None = None
    saved_scenarios: list[ScenarioPayload] = Field(default_factory=list)

    failed_stage: GenerationStage | None = None
    terminal_error: str | None = None
    terminal_error_code: str | None = None
