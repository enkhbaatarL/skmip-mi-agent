from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from apps.agents.scenario_group_agent.subgraphs.scenario_generation.pipeline import (
    Stage1ContextPack,
    Stage2DimensionSelection,
    Stage3ValueSelection,
    Stage4ScenarioSynthesis,
)


class ScenarioGenerationState(BaseModel):
    event_data: dict[str, Any] | None = None
    template: dict[str, Any] | None = None
    stage1_context_pack: Stage1ContextPack | None = None
    stage2_dimension_selection: Stage2DimensionSelection | None = None
    stage3_value_selection: Stage3ValueSelection | None = None
    stage4_scenario_synthesis: Stage4ScenarioSynthesis | None = None
    scenario_result: dict[str, Any] | None = None
    skip_generation: bool = False
    error: str | None = None
