from __future__ import annotations

import operator
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    GenerationDiagnostics,
    V2GenerationDiagnostics,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    EventInteraction,
    MultiEventGenerationResult,
    V2DimensionDefinition,
    V2DimensionDesignResult,
    V2EventShock,
    V2FinalizedGenerationResult,
    V2ScenarioSynthesisResult,
    V3DimensionDefinition,
    V3DimensionDesignResult,
    V3EventShock,
    V3MultiEventGenerationResult,
    V3ScenarioSynthesisResult,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    EventImpactFact,
    ParameterCoverage,
    V4DimensionDesignResult,
    V4GenerationResult,
    V4ScenarioSynthesisResult,
)
from apps.persistence.event.schema import EventPayload
from apps.persistence.model_parameter.schema import ModelImpactLeverPayload
from apps.persistence.scenario.schema import ScenarioPayload, ScenarioPipelineTemplate
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


GenerationStage = Literal["event_analysis", "dimension_design", "scenario_synthesis", "persistence"]


class EventAnalysisTask(BaseModel):
    api_version: Literal["v2", "v3"]
    event: EventPayload
    template: ScenarioPipelineTemplate
    attempt: int = Field(default=1, ge=1, le=3)
    validation_feedback: str | None = None


class EventAnalysisOutcome(BaseModel):
    event_id: int
    attempt: int
    event_shock: V2EventShock | V3EventShock | None = None
    error: str | None = None
    error_code: str | None = None
    retryable: bool = False


class MultiEventGenerationState(BaseModel):
    scenario_group: ScenarioGroupPayload | None = None
    events: list[EventPayload] = Field(default_factory=list)
    templates: list[ScenarioPipelineTemplate] = Field(default_factory=list)
    api_version: Literal["v2", "v3"] = "v2"
    generation_strategy: str = ""
    comparison_run_id: str | None = None
    user_id: int | None = None

    event_task: EventAnalysisTask | None = None
    event_analysis_outcomes: Annotated[list[EventAnalysisOutcome], operator.add] = Field(default_factory=list)
    event_shocks: list[V2EventShock | V3EventShock] = Field(default_factory=list)

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

    finalized_result: (
        V2FinalizedGenerationResult | MultiEventGenerationResult | V3MultiEventGenerationResult | None
    ) = None
    generation_diagnostics: V2GenerationDiagnostics | GenerationDiagnostics | None = None
    saved_group: ScenarioGroupPayload | None = None
    saved_scenarios: list[ScenarioPayload] = Field(default_factory=list)

    failed_stage: GenerationStage | None = None
    terminal_error: str | None = None
    terminal_error_code: str | None = None


class V4EventAnalysisTask(BaseModel):
    event: EventPayload
    attempt: int = Field(default=1, ge=1, le=3)
    validation_feedback: str | None = None


class V4EventAnalysisOutcome(BaseModel):
    event_id: int
    attempt: int
    event_impact_facts: list[EventImpactFact] = Field(default_factory=list)
    error: str | None = None
    error_code: str | None = None
    retryable: bool = False


class V4MultiEventGenerationState(BaseModel):
    scenario_group: ScenarioGroupPayload | None = None
    events: list[EventPayload] = Field(default_factory=list)
    impact_levers: list[ModelImpactLeverPayload] = Field(default_factory=list)
    impact_catalog_version: str = ""
    impact_catalog_checksum: str = ""
    comparison_run_id: str | None = None
    user_id: int | None = None

    event_task: V4EventAnalysisTask | None = None
    event_analysis_outcomes: Annotated[list[V4EventAnalysisOutcome], operator.add] = Field(default_factory=list)
    event_impact_facts: list[EventImpactFact] = Field(default_factory=list)

    dimension_attempt: int = 0
    dimension_draft: V4DimensionDesignResult | None = None
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
