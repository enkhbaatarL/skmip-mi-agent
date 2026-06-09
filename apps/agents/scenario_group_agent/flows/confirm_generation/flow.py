from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.flows.confirm_generation.nodes import (
    confirm_outputs,
    load_scenario_group,
    load_scenarios,
    load_signposts,
)
from apps.agents.scenario_group_agent.schemas.confirm_generation import ConfirmGenerationOut
from apps.agents.scenario_group_agent.state import ScenarioDesignState


def build_graph() -> Runnable:
    builder = StateGraph(ScenarioDesignState)
    builder.add_node("load_scenario_group", load_scenario_group)
    builder.add_node("load_scenarios", load_scenarios)
    builder.add_node("load_signposts", load_signposts)
    builder.add_node("confirm_outputs", confirm_outputs)
    builder.set_entry_point("load_scenario_group")
    builder.add_edge("load_scenario_group", "load_scenarios")
    builder.add_edge("load_scenarios", "load_signposts")
    builder.add_edge("load_signposts", "confirm_outputs")
    builder.set_finish_point("confirm_outputs")
    return builder.compile()


def to_state(payload: dict[str, Any]) -> ScenarioDesignState:
    return ScenarioDesignState(scenario_group_id=int(payload["scenario_group_id"]))


def to_output(state: dict[str, Any] | ScenarioDesignState) -> dict[str, Any]:
    data = state if isinstance(state, dict) else state.model_dump()
    return {
        "scenario_group_id": data.get("scenario_group_id") or 0,
        "confirmed": data.get("confirmed") or False,
        "confirmed_at": data.get("completed_at"),
        "snapshot_id": data.get("snapshot_id"),
        "scenario_count": len(data.get("scenarios") or []),
        "signpost_count": len(data.get("signposts") or []),
        "status": data.get("status") or "success",
        "message": data.get("message") or "",
    }


def build_runnable_graph() -> Runnable:
    return (RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)).with_types(
        output_type=ConfirmGenerationOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
