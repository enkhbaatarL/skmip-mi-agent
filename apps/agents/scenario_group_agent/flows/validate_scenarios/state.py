from __future__ import annotations

from pydantic import Field

from apps.agents.scenario_group_agent.schemas.state import (
    BaseFlowState,
    ScenarioTableState,
    ScenarioValidationResult,
    state_update,
)
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import ScenarioPayload, ScenarioTemplateDimension
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


class ValidateScenariosState(BaseFlowState):
    scenario_group: ScenarioGroupPayload | None = None
    events: list[EventPayload] = Field(default_factory=list)
    generation_diagnostics: dict[str, object] = Field(default_factory=dict)
    scenarios: list[ScenarioPayload] = Field(default_factory=list)
    dimension_template: list[ScenarioTemplateDimension] = Field(default_factory=list)
    request_table: ScenarioTableState | None = None
    validation_result: ScenarioValidationResult | None = None
    is_valid: bool = False
    reason: str = ""
    mapping_proposals: list[dict[str, object]] = Field(default_factory=list)
    parameter_mapping_ready: bool = False


def validate_scenarios_state_update(**values: object) -> dict[str, object]:
    return state_update(ValidateScenariosState, **values)
