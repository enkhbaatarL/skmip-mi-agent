from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda

from apps.agents.model_parameter_agent.flows.confirm_parameters.api_schema import (
    ConfirmParametersDataOut,
    ConfirmParametersIn,
    ConfirmParametersOut,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.validation import (
    validate_confirmation_parameters,
)
from apps.agents.model_parameter_agent.persistence.model_input_service import (
    ModelInputService,
)


def confirm_parameters(payload: dict[str, Any]) -> ConfirmParametersOut:
    proposal_id = int(payload["model_param_proposal_id"])
    request = ConfirmParametersIn.model_validate(payload)
    confirmation_parameters = request.data.confirmation_parameters
    model_input_service = ModelInputService()
    validate_confirmation_parameters(
        confirmation_parameters,
        parameter_definitions=model_input_service.load_model_parameter_definitions(),
    )
    result = model_input_service.confirm_proposal_result(
        model_param_proposal_id=proposal_id,
        confirmation_parameters=confirmation_parameters,
    )
    return ConfirmParametersOut(
        data=ConfirmParametersDataOut(
            model_param_proposal_id=result["model_param_proposal_id"],
            status=result["status"],
        ),
    )


def build_runnable_graph() -> Runnable:
    return RunnableLambda(confirm_parameters).with_types(
        input_type=ConfirmParametersIn,
        output_type=ConfirmParametersOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
