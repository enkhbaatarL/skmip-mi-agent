from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import StateGraph

from apps.agents.scenario_group_agent.constants import AGENT_NAME, API_IDENTIFIER_CONFIRM_GENERATION
from apps.agents.scenario_group_agent.flows.confirm_generation.nodes import (
    confirm_outputs,
    load_scenario_group,
    load_scenarios,
    load_signposts,
)
from apps.agents.scenario_group_agent.flows.confirm_generation.state import ConfirmGenerationState
from apps.agents.scenario_group_agent.schemas.endpoint import (
    ConfirmGenerationData,
    ConfirmGenerationIn,
    ConfirmGenerationOut,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import (
    TraceContext,
    build_langgraph_config,
    mlflow_trace_context,
    new_transaction_id,
)
from apps.common.values.error_codes import ErrorCode
from apps.persistence.enums import (
    ScenarioGroupStage,
    ScenarioGroupStatus,
)


def build_graph() -> Runnable:
    builder = StateGraph(ConfirmGenerationState, context_schema=TraceContext)
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


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    return build_graph()


def to_state(payload: dict[str, Any]) -> ConfirmGenerationState:
    parsed = ConfirmGenerationIn.model_validate(payload)
    return ConfirmGenerationState(
        scenario_group_id=int(payload["scenario_group_id"]),
        user_id=parsed.user_id,
        request_scenario_group=parsed.scenario_group,
        request_table=parsed.table.model_dump(exclude_unset=True),
    )


def to_output(state: dict[str, Any] | ConfirmGenerationState) -> ConfirmGenerationOut:
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
        RunnableLambda(to_state) | get_compiled_graph() | RunnableLambda(to_output)
    ).with_types(
        input_type=ConfirmGenerationIn,
        output_type=ConfirmGenerationOut,
    )


async def run_confirm_generation(payload: dict[str, Any]) -> ConfirmGenerationOut:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    agent_config = cfg.get_agent_config(AGENT_NAME)
    state = to_state(payload)
    trace_context = TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        api_identifier=API_IDENTIFIER_CONFIRM_GENERATION,
        session_id=str(state.scenario_group_id),
    )
    with mlflow_trace_context(trace_context):
        final_state = await get_compiled_graph().ainvoke(
            state,
            config=build_langgraph_config(trace_context),
            context=trace_context,
        )
    return to_output(final_state)


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
