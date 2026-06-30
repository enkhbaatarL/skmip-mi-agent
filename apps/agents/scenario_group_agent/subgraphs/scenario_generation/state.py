from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from apps.agents.scenario_group_agent.schemas.domain.event import EventPayload
from apps.agents.scenario_group_agent.schemas.graph.generation import (
    ScenarioGenerationResult,
    ScenarioTemplate,
    Stage1ContextPack,
    Stage2DimensionSelection,
    Stage3ValueSelection,
    Stage4ScenarioSynthesis,
    Stage6RepairInstruction,
)


class ScenarioGenerationState(BaseModel):
    event_data: EventPayload | dict[str, Any] | None = None
    template: ScenarioTemplate | None = None
    stage1_context_pack: Stage1ContextPack | None = None
    stage2_dimension_selection: Stage2DimensionSelection | None = None
    stage3_value_selection: Stage3ValueSelection | None = None
    stage4_scenario_synthesis: Stage4ScenarioSynthesis | None = None
    scenario_result: ScenarioGenerationResult | None = None
    skip_generation: bool = False
    error: str | None = None
    validation_feedback: str | None = None
    validation_repairs: list[Stage6RepairInstruction] = Field(default_factory=list)
    quick_validate_retry_count: int = 0
