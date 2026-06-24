from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)


def to_state(parent_state: SignpostGenerationState | Mapping[str, Any]) -> SignpostGenerationState:
    if isinstance(parent_state, SignpostGenerationState):
        return parent_state
    scenario = parent_state.get("scenario")
    if scenario is None:
        return SignpostGenerationState(error="scenario is required")
    return SignpostGenerationState(
        scenario=dict(scenario),
        base_event_summary=dict(parent_state.get("base_event_summary") or {}),
    )


def to_output(subgraph_state: SignpostGenerationState | Mapping[str, Any]) -> dict[str, Any]:
    state = (
        subgraph_state
        if isinstance(subgraph_state, SignpostGenerationState)
        else SignpostGenerationState.model_validate(subgraph_state)
    )
    if state.skip_generation:
        return {}
    if state.error:
        return {"status": "failure", "error": state.error, "message": state.error}
    return {"signposts": state.signposts}
