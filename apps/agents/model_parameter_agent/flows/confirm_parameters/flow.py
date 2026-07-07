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
from apps.agents.model_parameter_agent.schemas.api.parameters import ProposalParameter
from apps.common.logging.logger_config import logger


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
        user_id=request.user_id,
        confirmation_parameters=confirmation_parameters,
    )
    logger.info(
        "[model-parameter] confirmation completed | proposal_id={} parameter_summary={}",
        proposal_id,
        _proposal_parameter_summary(confirmation_parameters),
    )
    return ConfirmParametersOut(
        data=ConfirmParametersDataOut(
            model_param_proposal_id=result["model_param_proposal_id"],
            status=result["status"],
        ),
    )


def _proposal_parameter_summary(parameters: list[ProposalParameter]) -> list[dict[str, Any]]:
    return [
        {
            "parameter_name": parameter.parameter_name,
            "value_count": len(parameter.values),
        }
        for parameter in parameters
    ]


def build_runnable_graph() -> Runnable:
    return RunnableLambda(confirm_parameters).with_types(
        input_type=ConfirmParametersIn,
        output_type=ConfirmParametersOut,
    )


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
