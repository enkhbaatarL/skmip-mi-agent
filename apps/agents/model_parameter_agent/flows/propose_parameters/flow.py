from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable, RunnableLambda
from langgraph.graph import END, StateGraph

from apps.agents.model_parameter_agent.presentation import (
    _callback_error_output,
    _callback_success_output,
    _context_ids,
    _proposal_parameter_summary,
    _proposal_parameters_from_state,
    _to_response_data,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.validation import (
    _ensure_context_has_mapping_candidates,
    _ensure_mapping_candidates,
    _ensure_proposal_parameters,
    _route_after_basecase_filter,
    _route_after_candidate_validation,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    finalize_empty_parameter_values,
    filter_basecase_records_by_slots,
    load_basecase_samples,
    propose_parameter_slots,
    load_scenario_context,
    propose_parameter_values,
    select_parameter_candidates,
    validate_parameter_candidates,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.api_schema import (
    ProposeParametersAcceptedData,
    ProposeParametersAcceptedOut,
    ProposeParametersCallbackOut,
    ProposeParametersIn,
    ProposeParametersOut,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.callback.callback_client import send_callback


def build_graph() -> Runnable:
    builder = StateGraph(ModelParameterProposalState)
    builder.add_node("load_scenario_context", load_scenario_context)
    builder.add_node("select_parameter_candidates", select_parameter_candidates)
    builder.add_node("validate_parameter_candidates", validate_parameter_candidates)
    builder.add_node("load_basecase_samples", load_basecase_samples)
    builder.add_node("propose_parameter_slots", propose_parameter_slots)
    builder.add_node("filter_basecase_records_by_slots", filter_basecase_records_by_slots)
    builder.add_node("propose_parameter_values", propose_parameter_values)
    builder.add_node("finalize_empty_parameter_values", finalize_empty_parameter_values)
    builder.set_entry_point("load_scenario_context")
    builder.add_edge("load_scenario_context", "select_parameter_candidates")
    builder.add_edge("select_parameter_candidates", "validate_parameter_candidates")
    builder.add_conditional_edges(
        "validate_parameter_candidates",
        _route_after_candidate_validation,
        {
            "load_basecase_samples": "load_basecase_samples",
            "finalize_empty_parameter_values": "finalize_empty_parameter_values",
        },
    )
    builder.add_edge("load_basecase_samples", "propose_parameter_slots")
    builder.add_edge("propose_parameter_slots", "filter_basecase_records_by_slots")
    builder.add_conditional_edges(
        "filter_basecase_records_by_slots",
        _route_after_basecase_filter,
        {
            "propose_parameter_values": "propose_parameter_values",
            "finalize_empty_parameter_values": "finalize_empty_parameter_values",
        },
    )
    builder.add_edge("propose_parameter_values", END)
    builder.add_edge("finalize_empty_parameter_values", END)
    return builder.compile()


def to_state(payload: dict[str, Any]) -> ModelParameterProposalState:
    scenario_id = payload.get("scenario_id")
    if scenario_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_id is required")
    body = {key: value for key, value in payload.items() if key != "scenario_id"}
    parsed = ProposeParametersIn.model_validate(body)
    return ModelParameterProposalState(
        scenario_id=int(scenario_id),
        **parsed.model_dump(),
    )


def to_output(state: dict[str, Any] | ModelParameterProposalState) -> ProposeParametersOut:
    data = state if isinstance(state, dict) else state.model_dump()
    scenario_context = data.get("scenario_context") or {}
    if not scenario_context:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario context not found in state")
    _ensure_mapping_candidates(data)
    adjustments = data.get("parameter_adjustments") or []
    warnings = data.get("validation_warnings") or []
    proposal_parameters = _proposal_parameters_from_state(data)
    _ensure_proposal_parameters(data, proposal_parameters)
    model_param_proposal_id = ModelParameterService().save_proposal_result(
        scenario_context=scenario_context,
        user_id=data.get("user_id"),
        proposal_parameters=proposal_parameters,
    )
    response_data = _to_response_data(
        data,
        model_param_proposal_id=model_param_proposal_id,
        proposal_parameters=proposal_parameters,
    )
    logger.info(
        "[model-parameter] response ready | scenario_id={} proposal_id={} adjustment_count={} non_input_count={} warning_count={}",
        response_data.scenario_id,
        model_param_proposal_id,
        len(adjustments),
        len(data.get("non_input_items") or []),
        len(warnings),
    )
    return ProposeParametersOut(
        data=response_data,
    )


def prepare_propose_parameters_callback(
    scenario_id: int,
    *,
    user_id: int | None = None,
) -> dict[str, Any]:
    model_parameter_service = ModelParameterService()
    scenario_context = model_parameter_service.load_context(scenario_id)
    _ensure_context_has_mapping_candidates(
        scenario_id=scenario_id,
        scenario_context=scenario_context,
    )
    model_param_proposal_id = model_parameter_service.create_processing_proposal(
        scenario_context=scenario_context,
        user_id=user_id,
    )
    scenario_id_value, scenario_group_id, event_id = _context_ids(
        scenario_context,
        scenario_id,
    )
    return {
        "model_param_proposal_id": model_param_proposal_id,
        "scenario_id": scenario_id_value,
        "scenario_group_id": scenario_group_id,
        "event_id": event_id,
    }


async def run_propose_parameters_background(
    *,
    model_param_proposal_id: int,
    scenario_id: int,
    scenario_group_id: int | None,
    event_id: int | None,
) -> None:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    callback_path = cfg.callback_model_parameter_proposals_path.format(
        model_param_proposal_id=model_param_proposal_id,
        scenario_id=scenario_id,
        scenario_group_id=scenario_group_id,
        event_id=event_id,
    )
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path
    model_parameter_service = ModelParameterService()

    logger.info(
        "[BG][model-parameter] START | proposal_id={} scenario_id={}",
        model_param_proposal_id,
        scenario_id,
    )
    start = time.perf_counter()
    callback_payload: ProposeParametersCallbackOut
    try:
        final_state = await build_graph().ainvoke(ModelParameterProposalState(scenario_id=scenario_id))
        data = final_state if isinstance(final_state, dict) else final_state.model_dump()
        _ensure_mapping_candidates(data)
        proposal_parameters = _proposal_parameters_from_state(data)
        _ensure_proposal_parameters(data, proposal_parameters)
        response_data = _to_response_data(
            data,
            model_param_proposal_id=model_param_proposal_id,
            proposal_parameters=proposal_parameters,
        )
        model_parameter_service.complete_proposal_result(
            model_param_proposal_id=model_param_proposal_id,
            proposal_parameters=proposal_parameters,
        )
        callback_payload = _callback_success_output(response_data)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[BG][model-parameter] PROPOSAL_DONE | proposal_id={} scenario_id={} elapsed={}ms parameter_summary={}",
            model_param_proposal_id,
            scenario_id,
            elapsed_ms,
            _proposal_parameter_summary(proposal_parameters),
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        message = str(exc)
        error_code = (
            exc.error_code.name
            if isinstance(exc, MIBaseError)
            else exc.__class__.__name__
        )
        logger.error(
            "[BG][model-parameter] FAILED | proposal_id={} scenario_id={} elapsed={}ms error={!r}",
            model_param_proposal_id,
            scenario_id,
            elapsed_ms,
            exc,
        )
        model_parameter_service.fail_proposal_result(
            model_param_proposal_id=model_param_proposal_id,
            error_code=error_code,
            error_message=message,
        )
        callback_payload = _callback_error_output(
            message=message,
        )

    try:
        await send_callback(callback_url, callback_payload)
        model_parameter_service.update_callback_status(
            model_param_proposal_id=model_param_proposal_id,
            callback_status="SUCCEEDED",
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[BG][model-parameter] CALLBACK_DONE | proposal_id={} scenario_id={} elapsed={}ms",
            model_param_proposal_id,
            scenario_id,
            elapsed_ms,
        )
    except Exception as callback_exc:
        logger.error(
            "[BG][model-parameter] CALLBACK_FAILED | proposal_id={} error={!r}",
            model_param_proposal_id,
            callback_exc,
        )
        model_parameter_service.update_callback_status(
            model_param_proposal_id=model_param_proposal_id,
            callback_status="FAILED",
        )


def build_runnable_graph() -> Runnable:
    return RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
