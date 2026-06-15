from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.flows.create_scenarios.nodes import (
    check_existing_scenario_group,
    load_event,
    save_scenario_group,
    save_scenarios,
)
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.agents.scenario_group_agent.schemas.create_scenarios import (
    CreateScenariosIn,
    CreateScenariosOut,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.subgraph_builder import (
    scenario_generation_runnable,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


def build_graph() -> Runnable:
    builder = StateGraph(ScenarioDesignState)
    builder.add_node("load_event", load_event)
    builder.add_node("check_existing_scenario_group", check_existing_scenario_group)
    builder.add_node("run_scenario_generation", scenario_generation_runnable)
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
    return ScenarioDesignState(
        mi_event_id=parsed.mi_event_id,
        user_id=parsed.user_id,
        include_details=True,
    )


def to_output(state: dict[str, Any] | ScenarioDesignState) -> CreateScenariosOut:
    data = state if isinstance(state, dict) else state.model_dump()
    if data.get("status") in {"failure", "error"}:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail=data.get("message") or "Scenario creation failed")
    group = data.get("scenario_group")
    if not group:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario group not found in state")
    table_data = build_scenario_group_table_data(group, data.get("scenarios") or [])
    return CreateScenariosOut(
        result="success",
        scenario_group=table_data.scenario_group,
        table=table_data.table,
    )


def build_runnable_graph() -> Runnable:
    return (
        RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)
    ).with_types(
        input_type=CreateScenariosIn,
        output_type=CreateScenariosOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
