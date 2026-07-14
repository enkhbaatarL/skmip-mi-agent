from __future__ import annotations

import asyncio
from functools import lru_cache
import json
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
from apps.agents.model_parameter_agent.flows.propose_parameters.state import (
    ModelParameterProposalOutputState,
    ModelParameterProposalState,
)
from apps.agents.model_parameter_agent.utils.tracing import build_trace_context
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import (
    TraceContext,
    build_langgraph_config,
    mlflow_trace_context,
)
from apps.common.values.error_codes import ErrorCode
from apps.connectors.callback.callback_client import send_callback


def _debug_final_storage_payload(
    *,
    stage: str,
    scenario_id: int,
    model_param_proposal_id: int | None,
    proposal_parameters: list[Any],
) -> None:
    """Log the exact proposalParameters JSON passed to the persistence service."""
    logger.opt(lazy=True).debug(
        f"[model-parameter][storage][raw] stage={stage} scenario_id={scenario_id} "
        f"model_param_proposal_id={model_param_proposal_id} proposal_parameters=\n{{}}",
        lambda: json.dumps(
            [
                parameter.model_dump(mode="json", by_alias=True)
                if hasattr(parameter, "model_dump")
                else parameter
                for parameter in proposal_parameters
            ],
            ensure_ascii=False,
            default=str,
            indent=2,
        ),
    )


def build_graph() -> Runnable:
    builder = StateGraph(
        ModelParameterProposalState,
        context_schema=TraceContext,
        output_schema=ModelParameterProposalOutputState,
    )
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
    sync_proposal_parameters = _proposal_parameters_from_state(
        data,
        include_lut_value=True,
    )
    logger.opt(lazy=True).debug(
        f"[model-parameter][sync][output] scenario_id={int(data['scenario_id'])} "
        "proposal_parameters=\n{}",
        lambda: json.dumps(
            [
                parameter.model_dump(mode="json", by_alias=True)
                for parameter in sync_proposal_parameters
            ],
            ensure_ascii=False,
            default=str,
            indent=2,
        ),
    )
    response_data = _to_response_data(
        data,
        model_param_proposal_id=model_param_proposal_id,
        proposal_parameters=sync_proposal_parameters,
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
    model_parameter_service = ModelParameterService()

    logger.info(
        "[BG][model-parameter] START | proposal_id={} scenario_id={}",
        model_param_proposal_id,
        scenario_id,
    )
    start = time.perf_counter()
    callback_payload: ProposeParametersCallbackOut
    trace_context = build_trace_context(session_id=str(model_param_proposal_id))
    try:
        with mlflow_trace_context(trace_context):
            final_state = await build_graph().ainvoke(
                ModelParameterProposalState(scenario_id=scenario_id),
                config=build_langgraph_config(trace_context),
                context=trace_context,
            )
        data = final_state if isinstance(final_state, dict) else final_state.model_dump()
        _ensure_mapping_candidates(data)
        proposal_parameters = _proposal_parameters_from_state(data)
        _ensure_proposal_parameters(data, proposal_parameters)
        response_data = _to_response_data(
            data,
            model_param_proposal_id=model_param_proposal_id,
            proposal_parameters=proposal_parameters,
        )
        _debug_final_storage_payload(
            stage="background.before_complete_proposal_result",
            scenario_id=scenario_id,
            model_param_proposal_id=model_param_proposal_id,
            proposal_parameters=proposal_parameters,
        )
        await asyncio.to_thread(
            model_parameter_service.complete_proposal_result,
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
        await asyncio.to_thread(
            model_parameter_service.fail_proposal_result,
            model_param_proposal_id=model_param_proposal_id,
            error_code=error_code,
            error_message=message,
        )
        callback_payload = _callback_error_output(
            message=message,
            model_param_proposal_id=model_param_proposal_id,
            scenario_id=scenario_id,
            scenario_group_id=scenario_group_id,
            event_id=event_id,
        )

    try:
        callback_path = cfg.callback_model_parameter_proposals_path.format(
            scenario_id=scenario_id,
        )
        callback_url = cfg.callback_base_url.rstrip("/") + callback_path
        await send_callback(callback_url, callback_payload)
        callback_status = "SKIPPED" if cfg.skip_callback else "SUCCEEDED"
        await asyncio.to_thread(
            model_parameter_service.update_callback_status,
            model_param_proposal_id=model_param_proposal_id,
            callback_status=callback_status,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[BG][model-parameter] CALLBACK_DONE | proposal_id={} scenario_id={} "
            "callback_status={} elapsed={}ms",
            model_param_proposal_id,
            scenario_id,
            callback_status,
            elapsed_ms,
        )
    except Exception as callback_exc:
        logger.error(
            "[BG][model-parameter] CALLBACK_FAILED | proposal_id={} error={!r}",
            model_param_proposal_id,
            callback_exc,
        )
        await asyncio.to_thread(
            model_parameter_service.update_callback_status,
            model_param_proposal_id=model_param_proposal_id,
            callback_status="FAILED",
        )


async def run_propose_parameters_sync(payload: dict[str, Any]) -> ProposeParametersOut:
    # sync 테스트 경로는 proposal row가 실행 중에 생성되므로 session_id 없이(transaction 단위) 트레이싱
    trace_context = build_trace_context()
    with mlflow_trace_context(trace_context):
        final_state = await build_graph().ainvoke(
            to_state(payload),
            config=build_langgraph_config(trace_context),
            context=trace_context,
        )
    return to_output(final_state)


def build_runnable_graph() -> Runnable:
    return RunnableLambda(to_state) | build_graph() | RunnableLambda(to_output)


@lru_cache(maxsize=1)
def get_runnable_graph() -> Runnable:
    return build_runnable_graph()
