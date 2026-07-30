from __future__ import annotations

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.state import (
    BaseFlowState,
    ScenarioTableState,
    ScenarioValidationResult,
    state_update,
)
from apps.persistence.scenario.schema import ScenarioPayload, ScenarioTemplateDimension
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


class ValidateScenariosState(BaseFlowState):
    scenario_group: ScenarioGroupPayload | None = None
    scenarios: list[ScenarioPayload] = Field(default_factory=list)
    dimension_template: list[ScenarioTemplateDimension] = Field(default_factory=list)
    request_table: ScenarioTableState | None = None
    validation_result: ScenarioValidationResult | None = None
    is_valid: bool = False
    reason: str = ""


def validate_scenarios_state_update(**values: object) -> dict[str, object]:
    return state_update(ValidateScenariosState, **values)
