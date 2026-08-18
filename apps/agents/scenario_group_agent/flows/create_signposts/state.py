from __future__ import annotations

from typing import Annotated

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.state import (
    BaseFlowState,
    ScenarioTableState,
    extend_unique_ints,
    state_update,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import SignpostGenerationResult
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import NewScenarioGeneratedDetails, ScenarioPayload
from apps.persistence.scenario_group.schema import ScenarioGroupPayload
from apps.persistence.signpost.schema import SignpostPayload


class CreateSignpostsState(BaseFlowState):
    operation_id: str | None = None
    mi_event_id: int | None = None
    event_data: EventPayload | None = None
    include_details: bool = False
    scenario_group: ScenarioGroupPayload | None = None
    scenarios: list[ScenarioPayload] = Field(default_factory=list)
    signposts: list[SignpostPayload] = Field(default_factory=list)
    request_table: ScenarioTableState | None = None
    signpost_result: SignpostGenerationResult | None = None
    saved_signpost_ids: Annotated[list[int], extend_unique_ints] = Field(default_factory=list)
    signpost_target_scenario_ids: list[int] = Field(default_factory=list)
    new_scenario_row_details: list[NewScenarioGeneratedDetails] = Field(default_factory=list)


def create_signposts_state_update(**values: object) -> dict[str, object]:
    return state_update(CreateSignpostsState, **values)
