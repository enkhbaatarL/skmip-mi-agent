"""interpret_price flow LangGraph state."""

from __future__ import annotations

from pydantic import BaseModel, Field

from apps.agents.interpret_agent.flows.interpret_price.api_schema import (
    GroupSynthesisOut,
    PriceInterpretationResult,
    ScenarioComparisonOut,
)
from apps.agents.interpret_agent.flows.interpret_price.schema import (
    InterpretInput,
    ScenarioDiffBundle,
)


class InterpretPriceState(BaseModel):
    scenario_group_id: int | None = None
    scenario_ids: list[str] = Field(default_factory=list)

    interpret_input: InterpretInput | None = None
    diff_bundles: dict[str, ScenarioDiffBundle] = Field(default_factory=dict)
    interpretations: list[ScenarioComparisonOut] = Field(default_factory=list)
    synthesis: GroupSynthesisOut | None = None
    result: PriceInterpretationResult | None = None
