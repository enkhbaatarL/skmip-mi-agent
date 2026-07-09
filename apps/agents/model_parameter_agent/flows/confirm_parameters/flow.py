from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import END, StateGraph

from apps.agents.model_parameter_agent.flows.confirm_parameters.api_schema import (
    ConfirmParametersDataOut,
    ConfirmParametersIn,
    ConfirmParametersOut,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.nodes import (
    confirm_parameters,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.state import (
    ConfirmParametersState,
)


def to_state(payload: dict[str, Any]) -> ConfirmParametersState:
    proposal_id = int(payload["model_param_proposal_id"])
    request = ConfirmParametersIn.model_validate(payload)
    return ConfirmParametersState(
        model_param_proposal_id=proposal_id,
        user_id=request.user_id,
        confirmation_parameters=request.data.confirmation_parameters,
    )


def build_graph() -> Runnable:
    builder = StateGraph(ConfirmParametersState)
    builder.add_node("confirm_parameters", confirm_parameters)
    builder.set_entry_point("confirm_parameters")
    builder.add_edge("confirm_parameters", END)
    return builder.compile()


def to_output(state: dict[str, Any] | ConfirmParametersState) -> ConfirmParametersOut:
    data = state if isinstance(state, dict) else state.model_dump()
    result = data.get("result") or {}
    return ConfirmParametersOut(
        data=ConfirmParametersDataOut(
            model_param_proposal_id=result["model_param_proposal_id"],
            status=result["status"],
        ),
    )


def build_runnable_graph() -> Runnable:
    return RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
