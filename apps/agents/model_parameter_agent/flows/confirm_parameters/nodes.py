from __future__ import annotations

from typing import Any

from apps.agents.model_parameter_agent.flows.confirm_parameters.state import ConfirmParametersState
from apps.agents.model_parameter_agent.flows.confirm_parameters.validation import (
    validate_confirmation_parameters,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.agents.model_parameter_agent.presentation import _proposal_parameter_summary
from apps.common.logging.logger_config import logger


def confirm_parameters(state: ConfirmParametersState) -> dict[str, Any]:
    model_parameter_service = ModelParameterService()
    validate_confirmation_parameters(
        state.confirmation_parameters,
        parameter_definitions=model_parameter_service.load_model_parameter_definitions(),
    )
    result = model_parameter_service.confirm_proposal_result(
        model_param_proposal_id=state.model_param_proposal_id,
        user_id=state.user_id,
        confirmation_parameters=state.confirmation_parameters,
    )
    logger.info(
        "[model-parameter] confirmation completed | proposal_id={} parameter_summary={}",
        state.model_param_proposal_id,
        _proposal_parameter_summary(state.confirmation_parameters),
    )
    return {"result": result}
