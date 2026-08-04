from __future__ import annotations

from functools import lru_cache
from typing import Any

from langchain_core.runnables import Runnable
from langgraph.graph import END, START, StateGraph

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    MultiEventCreateScenariosIn,
    V2CreateScenariosData,
    V2CreateScenariosOut,
    VersionedCreateScenariosData,
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.nodes import (
    AnalyzeEventNode,
    GenerateDimensionsNode,
    GenerateScenariosNode,
    dispatch_event_analyses,
    fail_generation,
    finalize_scenarios,
    persist_generation,
    route_after_dimensions,
    route_after_event_analyses,
    route_after_scenarios,
    validate_dimensions,
    validate_event_analyses,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    V2FinalizedGenerationResult,
    multi_event_generation_schema as multi_event_generation_schema,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import (
    MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext, build_langgraph_config
from apps.common.values.error_codes import ErrorCode


GENERATION_STRATEGIES = {
    "v2": "multi_event_source_dimensions",
    "v3": "multi_event_composite_dimensions",
}


def prepare_multi_event_scenarios(
    payload: MultiEventCreateScenariosIn,
    *,
    api_version: str,
) -> dict[str, Any]:
    if api_version not in GENERATION_STRATEGIES:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"Unsupported multi-event API version: {api_version}",
        )
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

    scenario_service = ScenarioService()
    templates = [
        scenario_service.load_pipeline_template_with_metadata(
            event.event_type_l2_id,
        )
        for event in ordered_events
    ]
    group = ScenarioGroupService().prepare_multi_event_group(
        events=[event.model_dump() for event in ordered_events],
        templates=[template.model_dump() for template in templates],
        api_version=api_version,
        generation_strategy=GENERATION_STRATEGIES[api_version],
        comparison_run_id=payload.comparison_run_id,
        user_id=payload.user_id,
    )
    return {
        "scenario_group": group,
        "events": ordered_events,
        "templates": templates,
        "api_version": api_version,
        "generation_strategy": GENERATION_STRATEGIES[api_version],
        "comparison_run_id": payload.comparison_run_id,
        "user_id": payload.user_id,
    }


def _build_graph() -> Runnable:
    builder = StateGraph(MultiEventGenerationState, context_schema=TraceContext)
    builder.add_node("analyze_event", AnalyzeEventNode())
    builder.add_node("validate_event_analyses", validate_event_analyses)
    builder.add_node("generate_dimensions", GenerateDimensionsNode())
    builder.add_node("validate_dimensions", validate_dimensions)
    builder.add_node("generate_scenarios", GenerateScenariosNode())
    builder.add_node("finalize_scenarios", finalize_scenarios)
    builder.add_node("persist_generation", persist_generation)
    builder.add_node("fail_generation", fail_generation)

    builder.add_conditional_edges(START, dispatch_event_analyses, ["analyze_event"])
    builder.add_edge("analyze_event", "validate_event_analyses")
    builder.add_conditional_edges("validate_event_analyses", route_after_event_analyses)
    builder.add_edge("generate_dimensions", "validate_dimensions")
    builder.add_conditional_edges("validate_dimensions", route_after_dimensions)
    builder.add_edge("generate_scenarios", "finalize_scenarios")
    builder.add_conditional_edges("finalize_scenarios", route_after_scenarios)
    builder.add_edge("persist_generation", END)
    builder.add_edge("fail_generation", END)
    return builder.compile()


@lru_cache(maxsize=1)
def get_compiled_graph() -> Runnable:
    return _build_graph()


async def run_multi_event_scenarios_inline(
    prepared: dict[str, Any],
    *,
    trace_context: TraceContext | None = None,
) -> V2CreateScenariosOut | VersionedCreateScenariosOut:
    state = MultiEventGenerationState.model_validate(prepared)
    final_state_raw = await get_compiled_graph().ainvoke(
        state,
        config=build_langgraph_config(trace_context) if trace_context is not None else None,
        context=trace_context,
    )
    final_state = MultiEventGenerationState.model_validate(final_state_raw)
    if final_state.finalized_result is None or final_state.saved_group is None or not final_state.saved_scenarios:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="multi-event graph output is incomplete")
    finalized = final_state.finalized_result
    diagnostics = final_state.generation_diagnostics
    if diagnostics is None:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="multi-event generation diagnostics are missing")
    table_data = build_scenario_group_table_data(
        final_state.saved_group.model_dump(),
        [scenario.model_dump() for scenario in final_state.saved_scenarios],
    )
    if isinstance(finalized, V2FinalizedGenerationResult):
        return V2CreateScenariosOut(
            data=V2CreateScenariosData(
                comparison_run_id=str(prepared["comparison_run_id"]),
                scenario_group=table_data.scenario_group,
                events=final_state.events,
                dimension_definitions=finalized.dimension_definitions,
                table=table_data.table,
                generation_diagnostics=diagnostics,
            ),
        )
    return VersionedCreateScenariosOut(
        data=VersionedCreateScenariosData(
            api_version=final_state.api_version,
            generation_strategy=final_state.generation_strategy,
            comparison_run_id=prepared["comparison_run_id"],
            scenario_group=table_data.scenario_group,
            events=final_state.events,
            dimension_definitions=finalized.dimension_definitions,
            table=table_data.table,
            generation_diagnostics=diagnostics,
        ),
    )
