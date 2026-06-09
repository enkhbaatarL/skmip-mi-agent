from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_design_agent.flows.create_scenarios.nodes import (
    check_existing_scenario_group,
    load_event,
    run_scenario_generation,
    save_scenario_group,
    save_scenarios,
)
from apps.agents.scenario_design_agent.schemas.create_scenarios import CreateScenariosIn, CreateScenariosOut
from apps.agents.scenario_design_agent.state import ScenarioDesignState


def build_graph() -> Runnable:
    builder = StateGraph(ScenarioDesignState)
    builder.add_node("load_event", load_event)
    builder.add_node("check_existing_scenario_group", check_existing_scenario_group)
    builder.add_node("run_scenario_generation", run_scenario_generation)
    builder.add_node("save_scenario_group", save_scenario_group)
    builder.add_node("save_scenarios", save_scenarios)
    builder.set_entry_point("load_event")
    builder.add_edge("load_event", "check_existing_scenario_group")
    builder.add_edge("check_existing_scenario_group", "run_scenario_generation")
    builder.add_edge("run_scenario_generation", "save_scenario_group")
    builder.add_edge("save_scenario_group", "save_scenarios")
    builder.set_finish_point("save_scenarios")
    return builder.compile()


def to_state(payload: dict[str, Any]) -> ScenarioDesignState:
    parsed = CreateScenariosIn.model_validate(payload)
    return ScenarioDesignState(mi_event_id=parsed.mi_event_id, include_details=True)


def to_output(state: dict[str, Any] | ScenarioDesignState) -> dict[str, Any]:
    data = state if isinstance(state, dict) else state.model_dump()
    scenarios = data.get("scenarios") or []
    return {
        "mi_event_id": data.get("mi_event_id") or 0,
        "scenario_group_id": data.get("scenario_group_id"),
        "scenario_count": len(scenarios),
        "saved_scenario_ids": data.get("saved_scenario_ids") or [],
        "scenario_result": data.get("scenario_result"),
        "status": data.get("status") or "success",
        "message": data.get("message") or "",
    }


def build_runnable_graph() -> Runnable:
    return (RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)).with_types(
        input_type=CreateScenariosIn,
        output_type=CreateScenariosOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
