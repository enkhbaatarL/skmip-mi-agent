from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import (
    ScenarioTemplate,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.state import (
    ScenarioGenerationState,
)
from apps.persistence.scenario.service import (
    ScenarioService,
)


def to_state(
    parent_state: ScenarioDesignState | Mapping[str, Any],
) -> ScenarioGenerationState:
    state = (
        parent_state
        if isinstance(parent_state, ScenarioDesignState)
        else ScenarioDesignState.model_validate(parent_state)
    )
    if state.status in {"failure", "already_exist"}:
        return ScenarioGenerationState(skip_generation=True)
    if state.event_data is None:
        return ScenarioGenerationState(error="event_data is required")

    event_type_l2_id = int(state.event_data.get("event_type_l2_id") or 0)
    persistence_template = ScenarioService().load_pipeline_template(event_type_l2_id)
    template = ScenarioTemplate.model_validate(persistence_template.model_dump())
    return ScenarioGenerationState(
        event_data=state.event_data,
        template=template,
    )


def to_output(
    subgraph_state: ScenarioGenerationState | Mapping[str, Any],
) -> dict[str, Any]:
    state = (
        subgraph_state
        if isinstance(subgraph_state, ScenarioGenerationState)
        else ScenarioGenerationState.model_validate(subgraph_state)
    )
    if state.skip_generation:
        return {}
    if state.error:
        return {
            "status": "failure",
            "error": state.error,
            "message": state.error,
        }
    return {"scenario_result": state.scenario_result}
