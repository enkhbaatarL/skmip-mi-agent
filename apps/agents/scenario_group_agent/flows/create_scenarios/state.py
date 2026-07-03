from __future__ import annotations

from typing import Annotated

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.state import BaseFlowState, extend_unique_ints, state_update
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import ScenarioGenerationResult
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import ScenarioPayload
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


class CreateScenariosState(BaseFlowState):
    mi_event_id: int | None = None
    event_data: EventPayload | None = None
    scenario_group: ScenarioGroupPayload | None = None
    scenario_result: ScenarioGenerationResult | None = None
    saved_scenario_ids: Annotated[list[int], extend_unique_ints] = Field(default_factory=list)
    scenarios: list[ScenarioPayload] = Field(default_factory=list)


def create_scenarios_state_update(**values: object) -> dict[str, object]:
    return state_update(CreateScenariosState, **values)
