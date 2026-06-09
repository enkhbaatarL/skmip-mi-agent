from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_design_agent.flows.create_signposts.nodes import (
    check_existing_signposts,
    load_scenario_group,
    load_scenarios,
    run_signpost_generation,
    save_signposts,
)
from apps.agents.scenario_design_agent.schemas.create_signposts import CreateSignpostsIn, CreateSignpostsOut
from apps.agents.scenario_design_agent.state import ScenarioDesignState


def build_graph() -> Runnable:
    builder = StateGraph(ScenarioDesignState)
    builder.add_node("load_scenario_group", load_scenario_group)
    builder.add_node("load_scenarios", load_scenarios)
    builder.add_node("check_existing_signposts", check_existing_signposts)
    builder.add_node("run_signpost_generation", run_signpost_generation)
    builder.add_node("save_signposts", save_signposts)
    builder.set_entry_point("load_scenario_group")
    builder.add_edge("load_scenario_group", "load_scenarios")
    builder.add_edge("load_scenarios", "check_existing_signposts")
    builder.add_edge("check_existing_signposts", "run_signpost_generation")
    builder.add_edge("run_signpost_generation", "save_signposts")
    builder.set_finish_point("save_signposts")
    return builder.compile()


def to_state(payload: dict[str, Any]) -> ScenarioDesignState:
    CreateSignpostsIn.model_validate(payload)
    return ScenarioDesignState(
        scenario_group_id=int(payload["scenario_group_id"]),
        include_details=True,
    )


def to_output(state: dict[str, Any] | ScenarioDesignState) -> dict[str, Any]:
    data = state if isinstance(state, dict) else state.model_dump()
    return {
        "scenario_group_id": data.get("scenario_group_id") or 0,
        "signpost_count": len(data.get("signposts") or []),
        "saved_signpost_ids": data.get("saved_signpost_ids") or [],
        "signpost_result": data.get("signpost_result"),
        "status": data.get("status") or "success",
        "message": data.get("message") or "",
    }


def build_runnable_graph() -> Runnable:
    return (RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)).with_types(
        input_type=CreateSignpostsIn,
        output_type=CreateSignpostsOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
