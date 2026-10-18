from __future__ import annotations

from collections.abc import Awaitable, Callable
from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from apps.agents.scenario_group_agent.constants import (
    AGENT_NAME,
    API_IDENTIFIER_CREATE_SCENARIOS,
)
from apps.agents.scenario_group_agent.flows.callback_delivery import deliver_operation_callback
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
    VersionedCreateScenariosData,
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import (
    V4MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_budget import scenario_count_range
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_nodes import (
    AnalyzeEventImpactsNode,
    AnalyzeEventInteractionsNode,
    DesignModelLeverDimensionsNode,
    GenerateV4GroupTitleNode,
    SynthesizeV4ScenariosNode,
    fail_v4_generation,
    finalize_v4_scenarios,
    persist_v4_generation,
    route_after_v4_dimensions,
    route_after_v4_event_impacts,
    route_after_v4_event_interactions,
    route_after_v4_scenarios,
    validate_v4_dimensions,
    validate_v4_event_impacts,
    validate_v4_event_interactions,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4GenerationResult,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.model_impact_lever_service import (
    ModelImpactLeverService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.presentation import build_scenario_group_table_data
from apps.agents.scenario_group_agent.schemas.endpoint import CreateScenariosOut
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import (
    TraceContext,
    build_langgraph_config,
    mlflow_trace_context,
    new_transaction_id,
)
from apps.common.values.error_codes import ErrorCode
from apps.common.values.response import CallBackBody
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


V4_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"


def _analysis_as_of() -> str:
    # Keep the analysis date aligned with the application's configured timezone.
    # The local import avoids loading settings while this module is imported by tests.
    from apps.common.utils.time_utils import today

    return today()


def prepare_v4_multi_event_scenarios(
    payload: V4MultiEventCreateScenariosIn,
    *,
    operation_id: str | None = None,
) -> dict[str, Any]:
    events = EventService().load_events(payload.mi_event_ids)
    loaded_ids = {int(event.mi_event_id) for event in events}
    missing_ids = [event_id for event_id in payload.mi_event_ids if event_id not in loaded_ids]
    if missing_ids:
        raise MIBaseError(
            ErrorCode.ENTITY_NOT_FOUND,
            detail=f"Events not found: {missing_ids}",
        )
    event_by_id = {int(event.mi_event_id): event for event in events}
    ordered_events = [event_by_id[event_id] for event_id in payload.mi_event_ids]
    synthesis_policy = get_settings().scenario_synthesis_policy

    impact_levers, catalog_version, catalog_checksum = ModelImpactLeverService().load_active_catalog(
        catalog_version=get_settings().scenario_group_v4_impact_catalog_version,
    )
    if not impact_levers:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="Active model impact lever catalog is empty",
        )
    group = ScenarioGroupService().prepare_v4_multi_event_group(
        events=[event.model_dump() for event in ordered_events],
        impact_catalog_version=catalog_version,
        impact_catalog_checksum=catalog_checksum,
        user_id=payload.user_id,
        operation_id=operation_id,
    )
    return {
        "scenario_group": group,
        "events": ordered_events,
        "impact_levers": impact_levers,
        "impact_catalog_version": catalog_version,
        "impact_catalog_checksum": catalog_checksum,
        "impact_parameter_axes": ModelImpactLeverService().load_parameter_semantic_axes(impact_levers),
        "user_id": payload.user_id,
        "analysis_as_of": _analysis_as_of(),
        "scenario_synthesis_policy": synthesis_policy,
        "scenario_count_range": scenario_count_range(len(ordered_events), policy=synthesis_policy),
        "operation_id": operation_id,
    }


def _build_graph() -> Runnable:
    builder = StateGraph(V4MultiEventGenerationState, context_schema=TraceContext)
    builder.add_node("analyze_event_impacts", AnalyzeEventImpactsNode())
    builder.add_node("validate_event_impacts", validate_v4_event_impacts)
    builder.add_node("analyze_event_interactions", AnalyzeEventInteractionsNode())
    builder.add_node("validate_event_interactions", validate_v4_event_interactions)
    builder.add_node("design_model_lever_dimensions", DesignModelLeverDimensionsNode())
    builder.add_node("validate_model_lever_dimensions", validate_v4_dimensions)
    builder.add_node("synthesize_v4_scenarios", SynthesizeV4ScenariosNode())
    builder.add_node("finalize_v4_scenarios", finalize_v4_scenarios)
    builder.add_node("generate_v4_group_title", GenerateV4GroupTitleNode())
    builder.add_node("persist_generation", persist_v4_generation)
    builder.add_node("fail_generation", fail_v4_generation)

    builder.add_edge(START, "analyze_event_impacts")
    builder.add_edge("analyze_event_impacts", "validate_event_impacts")
    builder.add_conditional_edges("validate_event_impacts", route_after_v4_event_impacts)
    builder.add_edge("analyze_event_interactions", "validate_event_interactions")
    builder.add_conditional_edges("validate_event_interactions", route_after_v4_event_interactions)
    builder.add_edge("design_model_lever_dimensions", "validate_model_lever_dimensions")
    builder.add_conditional_edges("validate_model_lever_dimensions", route_after_v4_dimensions)
    builder.add_edge("synthesize_v4_scenarios", "finalize_v4_scenarios")
    builder.add_conditional_edges("finalize_v4_scenarios", route_after_v4_scenarios)
    builder.add_edge("generate_v4_group_title", "persist_generation")
    builder.add_edge("persist_generation", END)
    builder.add_edge("fail_generation", END)
    return builder.compile()


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    return _build_graph()


async def run_v4_multi_event_scenarios_inline(
    prepared: dict[str, Any],
    *,
    trace_context: TraceContext | None = None,
) -> VersionedCreateScenariosOut:
    state = V4MultiEventGenerationState.model_validate(prepared)
    final_state_raw = await get_compiled_graph().ainvoke(
        state,
        config=build_langgraph_config(trace_context) if trace_context is not None else None,
        context=trace_context,
    )
    final_state = V4MultiEventGenerationState.model_validate(final_state_raw)
    return _build_v4_output(final_state)


async def run_v4_multi_event_scenarios_with_progress(
    prepared: dict[str, Any],
    *,
    on_node_start: Callable[[str], Awaitable[None]],
    on_node_update: Callable[[str, dict[str, Any], V4MultiEventGenerationState], Awaitable[None]],
    trace_context: TraceContext | None = None,
) -> VersionedCreateScenariosOut:
    """Execute the v4 graph while exposing node starts and validated updates to the DB event producer."""
    initial_state = V4MultiEventGenerationState.model_validate(prepared)
    accumulated = initial_state.model_dump()
    async for streamed in get_compiled_graph().astream(
        initial_state,
        config=build_langgraph_config(trace_context) if trace_context is not None else None,
        context=trace_context,
        stream_mode=["tasks", "updates", "custom"],
    ):
        if isinstance(streamed, tuple) and len(streamed) == 2:
            stream_mode, chunk = streamed
        else:
            stream_mode, chunk = "updates", streamed
        if stream_mode == "tasks":
            if isinstance(chunk, dict) and "input" in chunk and isinstance(chunk.get("name"), str):
                await on_node_start(chunk["name"])
            continue
        if stream_mode == "custom":
            if isinstance(chunk, dict):
                await on_node_update(
                    "__custom__",
                    chunk,
                    V4MultiEventGenerationState.model_validate(accumulated),
                )
            continue
        if not isinstance(chunk, dict):
            continue
        for node_name, raw_update in chunk.items():
            if not isinstance(raw_update, dict):
                continue
            accumulated.update(raw_update)
            state = V4MultiEventGenerationState.model_validate(accumulated)
            await on_node_update(str(node_name), raw_update, state)
    return _build_v4_output(V4MultiEventGenerationState.model_validate(accumulated))


def _build_v4_output(final_state: V4MultiEventGenerationState) -> VersionedCreateScenariosOut:
    if final_state.finalized_result is None or final_state.saved_group is None or not final_state.saved_scenarios:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="v4 multi-event graph output is incomplete")
    diagnostics = final_state.generation_diagnostics
    if diagnostics is None:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="v4 generation diagnostics are missing")
    finalized: V4GenerationResult = final_state.finalized_result
    table_data = build_scenario_group_table_data(
        final_state.saved_group.model_dump(),
        [scenario.model_dump() for scenario in final_state.saved_scenarios],
    )
    return VersionedCreateScenariosOut(
        data=VersionedCreateScenariosData(
            api_version="v4",
            generation_strategy=V4_GENERATION_STRATEGY,
            impact_catalog_version=final_state.impact_catalog_version,
            scenario_group=table_data.scenario_group,
            events=final_state.events,
            dimension_definitions=finalized.dimension_definitions,
            table=table_data.table,
            generation_diagnostics=diagnostics,
        ),
    )


def _require_output_data(
    output: VersionedCreateScenariosOut,
) -> VersionedCreateScenariosData:
    if output.data is None:
        raise MIBaseError(
            ErrorCode.UNKNOWN_ERROR,
            detail="v4 scenario generation output is empty",
        )
    return output.data


async def run_v4_multi_event_scenarios_background(
    prepared: dict[str, Any],
) -> None:
    from apps.common.configs.config import get_settings

    cfg = get_settings()
    group = ScenarioGroupPayload.model_validate(prepared["scenario_group"])
    group_id = group.scenario_group_id
    callback_path = cfg.callback_create_scenarios_path.format(
        scenario_group_id=group_id,
    )
    callback_url = cfg.callback_base_url.rstrip("/") + callback_path
    agent_config = cfg.get_agent_config(AGENT_NAME)
    trace_context = TraceContext(
        transaction_id=new_transaction_id(),
        app_identifier=agent_config.aip_app_id,
        agent_name=AGENT_NAME,
        api_identifier=API_IDENTIFIER_CREATE_SCENARIOS,
        session_id=str(group_id),
        tags={
            "api_version": "v4",
            "generation_strategy": V4_GENERATION_STRATEGY,
        },
    )

    logger.info("[BG][v4 create_scenarios] START | group_id={}", group_id)
    start = time.perf_counter()
    callback_payload: CallBackBody
    try:
        with mlflow_trace_context(trace_context):
            output = await run_v4_multi_event_scenarios_inline(
                prepared,
                trace_context=trace_context,
            )
        output_data = _require_output_data(output)
        callback_payload = CreateScenariosOut(
            result="success",
            scenario_group=output_data.scenario_group,
            table=output_data.table,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "[BG][v4 create_scenarios] END | group_id={} | elapsed={}ms",
            group_id,
            elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "[BG][v4 create_scenarios] FAILED | group_id={} | elapsed={}ms | error={!r}",
            group_id,
            elapsed_ms,
            exc,
        )
        callback_payload = CallBackBody(result="failure", reason=str(exc))

    await deliver_operation_callback(
        log_tag="v4 create_scenarios",
        callback_url=callback_url,
        payload=callback_payload,
        scenario_group_id=group_id,
        operation_id=prepared.get("operation_id"),
    )


__all__ = [
    "V4_GENERATION_STRATEGY",
    "get_compiled_graph",
    "prepare_v4_multi_event_scenarios",
    "run_v4_multi_event_scenarios_background",
    "run_v4_multi_event_scenarios_inline",
    "run_v4_multi_event_scenarios_with_progress",
]
