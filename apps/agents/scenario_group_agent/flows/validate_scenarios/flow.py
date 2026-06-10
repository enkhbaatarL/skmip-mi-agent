from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    load_scenario_group,
    load_scenarios,
    save_validation_result,
    validate_scenarios,
)
from apps.agents.scenario_group_agent.schemas.validate_scenarios import (
    ValidateScenariosData,
    ValidateScenariosIn,
    ValidateScenariosOut,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState


def build_graph() -> Runnable:
    builder = StateGraph(ScenarioDesignState)
    builder.add_node("load_scenario_group", load_scenario_group)
    builder.add_node("load_scenarios", load_scenarios)
    builder.add_node("validate_scenarios", validate_scenarios)
    builder.add_node("save_validation_result", save_validation_result)
    builder.set_entry_point("load_scenario_group")
    builder.add_edge("load_scenario_group", "load_scenarios")
    builder.add_edge("load_scenarios", "validate_scenarios")
    builder.add_edge("validate_scenarios", "save_validation_result")
    builder.set_finish_point("save_validation_result")
    return builder.compile()


def to_state(payload: dict[str, Any]) -> ScenarioDesignState:
    parsed = ValidateScenariosIn.model_validate(payload)
    return ScenarioDesignState(
        scenario_group_id=int(payload["scenario_group_id"]),
        user_id=parsed.user_id,
        request_scenario_group=parsed.scenario_group.model_dump(),
        request_table=parsed.table.model_dump(),
    )


def _resolve_status(raw_status: Any) -> str:
    return "error" if raw_status in {"failure", "error"} else "success"


def to_output(state: dict[str, Any] | ScenarioDesignState) -> ValidateScenariosOut:
    data = state if isinstance(state, dict) else state.model_dump()
    status = _resolve_status(data.get("status"))
    group = data.get("scenario_group") or {}
    return ValidateScenariosOut(
        status=status,
        message=data.get("message") or "",
        data=(
            ValidateScenariosData(
                scenario_group_id=data.get("scenario_group_id") or 0,
                is_valid=data.get("is_valid") or False,
                reason=data.get("reason") or data.get("message") or "",
                status=group.get("status") or "creating",
                stage=group.get("stage") or "scenario_created",
            )
            if status == "success"
            else None
        ),
    )


def build_runnable_graph() -> Runnable:
    return (
        RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)
    ).with_types(
        input_type=ValidateScenariosIn,
        output_type=ValidateScenariosOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
