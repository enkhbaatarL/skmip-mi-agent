from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.agents.scenario_group_agent.schemas.table import ScenarioTable
from apps.common.values.llm_usage import LLMUsageModel
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import DimensionDefinition
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


ApiVersion = Literal["v1", "v2", "v3"]
GenerationStrategy = Literal[
    "single_event_template_dimensions",
    "multi_event_source_dimensions",
    "multi_event_composite_dimensions",
]


class VersionedCreateScenariosIn(ApiModel):
    mi_event_id: int = Field(gt=0)
    user_id: int
    comparison_run_id: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def _normalize_comparison_run_id(self) -> VersionedCreateScenariosIn:
        if self.comparison_run_id is not None:
            self.comparison_run_id = self.comparison_run_id.strip()
            if not self.comparison_run_id:
                raise ValueError("comparisonRunId must not be blank")
        return self


class MultiEventCreateScenariosIn(ApiModel):
    mi_event_ids: list[int]
    user_id: int
    comparison_run_id: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def _validate_event_ids(self) -> MultiEventCreateScenariosIn:
        if not 2 <= len(self.mi_event_ids) <= 5:
            raise ValueError("miEventIds must contain 2 to 5 events")
        if len(set(self.mi_event_ids)) != len(self.mi_event_ids):
            raise ValueError("miEventIds must not contain duplicates")
        if any(event_id <= 0 for event_id in self.mi_event_ids):
            raise ValueError("miEventIds must contain positive IDs")
        self.comparison_run_id = self.comparison_run_id.strip()
        if not self.comparison_run_id:
            raise ValueError("comparisonRunId is required")
        return self


class ExcludedCandidate(ApiModel):
    global_pressure_band: Literal[
        "strong_bullish",
        "bullish",
        "balanced",
        "bearish",
        "strong_bearish",
    ]
    reason_code: str
    reason: str


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
    excluded_dimensions: list[dict[str, object]] = Field(default_factory=list)


class VersionedCreateScenariosData(ApiModel):
    api_version: ApiVersion
    generation_strategy: GenerationStrategy
    comparison_run_id: str | None = None
    scenario_group: ScenarioGroupPayload
    events: list[EventPayload] = Field(default_factory=list)
    dimension_definitions: list[DimensionDefinition] = Field(default_factory=list)
    table: ScenarioTable
    generation_diagnostics: GenerationDiagnostics = Field(
        default_factory=GenerationDiagnostics,
    )
    usage: LLMUsageModel | None = None


class VersionedCreateScenariosOut(ApiModel):
    status: Literal["success", "error"] = "success"
    message: str = "성공"
    data: VersionedCreateScenariosData | None = None
