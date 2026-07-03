from __future__ import annotations

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.state import (
    BaseFlowState,
    ConfirmScenarioGroupState,
    ScenarioTableState,
    state_update,
)
from apps.persistence.scenario.schema import ScenarioPayload
from apps.persistence.scenario_group.schema import ScenarioGroupPayload
from apps.persistence.signpost.schema import SignpostPayload


class ConfirmGenerationState(BaseFlowState):
    scenario_group: ScenarioGroupPayload | None = None
    scenarios: list[ScenarioPayload] = Field(default_factory=list)
    signposts: list[SignpostPayload] = Field(default_factory=list)
    request_scenario_group: ConfirmScenarioGroupState | None = None
    request_table: ScenarioTableState | None = None
    snapshot_id: int | None = None
    confirmed: bool = False


def confirm_generation_state_update(**values: object) -> dict[str, object]:
    return state_update(ConfirmGenerationState, **values)
