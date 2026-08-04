from __future__ import annotations

from functools import lru_cache
import time
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from apps.agents.scenario_group_agent.constants import (
    AGENT_NAME,
    API_IDENTIFIER_CREATE_SCENARIOS,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
    VersionedCreateScenariosData,
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import (
    V4MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_nodes import (
    DesignModelLeverDimensionsNode,
    ExtractEventFactsNode,
    SynthesizeV4ScenariosNode,
    _with_event_lineage as _with_event_lineage,
    dispatch_v4_event_analyses,
    fail_v4_generation,
    finalize_v4_scenarios,
    persist_v4_generation,
    route_after_v4_dimensions,
    route_after_v4_event_analyses,
    route_after_v4_scenarios,
    validate_v4_dimensions,
    validate_v4_event_analyses,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4GenerationResult,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.presentation import build_scenario_group_table_data
from apps.agents.scenario_group_agent.schemas.endpoint import CreateScenariosOut
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
from apps.connectors.callback.callback_client import send_callback
from apps.persistence.model_parameter.service import ModelImpactLeverService
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


V4_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"


def prepare_v4_multi_event_scenarios(
    payload: V4MultiEventCreateScenariosIn,
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

    impact_levers, catalog_version, catalog_checksum = ModelImpactLeverService().load_active_catalog()
    if not impact_levers:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="Active model impact lever catalog is empty",
        )
    group = ScenarioGroupService().prepare_v4_multi_event_group(
        events=[event.model_dump() for event in ordered_events],
        impact_catalog_version=catalog_version,
        impact_catalog_checksum=catalog_checksum,
        comparison_run_id=payload.comparison_run_id,
        user_id=payload.user_id,
    )
    return {
        "scenario_group": group,
        "events": ordered_events,
        "impact_levers": impact_levers,
        "impact_catalog_version": catalog_version,
        "impact_catalog_checksum": catalog_checksum,
        "comparison_run_id": payload.comparison_run_id,
        "user_id": payload.user_id,
    }


def _build_graph() -> Runnable:
    builder = StateGraph(V4MultiEventGenerationState, context_schema=TraceContext)
    builder.add_node("extract_event_facts", ExtractEventFactsNode())
    builder.add_node("validate_event_facts", validate_v4_event_analyses)
    builder.add_node("design_model_lever_dimensions", DesignModelLeverDimensionsNode())
    builder.add_node("validate_model_lever_dimensions", validate_v4_dimensions)
    builder.add_node("synthesize_v4_scenarios", SynthesizeV4ScenariosNode())
    builder.add_node("finalize_v4_scenarios", finalize_v4_scenarios)
    builder.add_node("persist_generation", persist_v4_generation)
    builder.add_node("fail_generation", fail_v4_generation)

    builder.add_conditional_edges(START, dispatch_v4_event_analyses, ["extract_event_facts"])
    builder.add_edge("extract_event_facts", "validate_event_facts")
    builder.add_conditional_edges("validate_event_facts", route_after_v4_event_analyses)
    builder.add_edge("design_model_lever_dimensions", "validate_model_lever_dimensions")
    builder.add_conditional_edges("validate_model_lever_dimensions", route_after_v4_dimensions)
    builder.add_edge("synthesize_v4_scenarios", "finalize_v4_scenarios")
    builder.add_conditional_edges("finalize_v4_scenarios", route_after_v4_scenarios)
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
            comparison_run_id=final_state.comparison_run_id,
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
            **(
                {"comparison_run_id": str(prepared["comparison_run_id"])}
                if prepared["comparison_run_id"] is not None
                else {}
            ),
        },
    )

    logger.info("[BG][v4 create_scenarios] START | group_id={}", group_id)
    start = time.perf_counter()
    try:
        with mlflow_trace_context(trace_context):
            output = await run_v4_multi_event_scenarios_inline(
                prepared,
                trace_context=trace_context,
            )
        output_data = _require_output_data(output)
        await send_callback(
            callback_url,
            CreateScenariosOut(
                result="success",
                scenario_group=output_data.scenario_group,
                table=output_data.table,
            ),
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
        try:
            await send_callback(
                callback_url,
                CallBackBody(result="failure", reason=str(exc)),
            )
        except Exception as callback_exc:
            logger.error(
                "[BG][v4 create_scenarios] CALLBACK_FAILED | error={!r}",
                callback_exc,
            )


__all__ = [
    "V4_GENERATION_STRATEGY",
    "get_compiled_graph",
    "prepare_v4_multi_event_scenarios",
    "run_v4_multi_event_scenarios_background",
    "run_v4_multi_event_scenarios_inline",
]
