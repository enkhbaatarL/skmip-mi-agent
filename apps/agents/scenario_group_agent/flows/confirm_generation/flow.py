from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.flows.confirm_generation.api_schema import (
    ConfirmGenerationData,
    ConfirmGenerationIn,
    ConfirmGenerationOut,
)
from apps.agents.scenario_group_agent.flows.confirm_generation.nodes import (
    confirm_outputs,
    load_scenario_group,
    load_scenarios,
    load_signposts,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)


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
    parsed = ConfirmGenerationIn.model_validate(payload)
    return ScenarioDesignState(
        scenario_group_id=int(payload["scenario_group_id"]),
        user_id=parsed.user_id,
        request_scenario_group=parsed.scenario_group,
        request_table=parsed.table.model_dump(exclude_unset=True),
    )


def to_output(state: dict[str, Any] | ScenarioDesignState) -> ConfirmGenerationOut:
    data = state if isinstance(state, dict) else state.model_dump()
    if data.get("status") in {"failure", "error"}:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail=data.get("message") or "Confirmation failed")
    group = data.get("scenario_group") or {}
    return ConfirmGenerationOut(
        status="success",
        message=data.get("message") or "",
        data=ConfirmGenerationData(
            scenario_group_id=data.get("scenario_group_id") or 0,
            status=group.get("status") or ScenarioGroupStatus.CREATED.value,
            stage=group.get("stage") or ScenarioGroupStage.COMPLETED.value,
        ),
    )


def build_runnable_graph() -> Runnable:
    return (
        RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)
    ).with_types(
        input_type=ConfirmGenerationIn,
        output_type=ConfirmGenerationOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
