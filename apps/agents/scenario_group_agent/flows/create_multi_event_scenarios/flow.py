from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    GenerationDiagnostics,
    MultiEventCreateScenariosIn,
    VersionedCreateScenariosData,
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    MultiEventGenerationResult,
    finalize_generation_result,
    multi_event_generation_schema,
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
from apps.agents.scenario_group_agent.prompts.multi_event_scenario_generation import (
    MULTI_EVENT_SYSTEM_PROMPT,
    build_multi_event_user_prompt,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import ScenarioPipelineTemplate
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


GENERATION_STRATEGIES = {
    "v2": "multi_event_source_dimensions",
    "v3": "multi_event_composite_dimensions",
}


def prepare_multi_event_scenarios(
    payload: MultiEventCreateScenariosIn,
    *,
    api_version: str,
) -> MultiEventGenerationResult:
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


async def _invoke_multi_event_generation(
    *,
    api_version: str,
    events: list[EventPayload],
    templates: list[ScenarioPipelineTemplate],
    trace_context: TraceContext | None = None,
    validation_feedback: str | None = None,
) -> dict[str, Any]:
    from apps.common.configs.config import get_settings
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    user_prompt = build_multi_event_user_prompt(
        api_version=api_version,
        events=[event.model_dump() for event in events],
        templates=[template.model_dump() for template in templates],
        validation_feedback=validation_feedback,
    )
    generation_schema = multi_event_generation_schema(api_version)
    response = await invoke_llm_structured_output(
        output_schema=generation_schema,
        messages=[
            {"role": "system", "content": MULTI_EVENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_retries=2,
        trace_context=trace_context,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
    )
    return response.result


async def run_multi_event_scenarios_inline(
    prepared: dict[str, Any],
    *,
    trace_context: TraceContext | None = None,
) -> VersionedCreateScenariosOut:
    group = ScenarioGroupPayload.model_validate(prepared["scenario_group"])
    events = [EventPayload.model_validate(event) for event in prepared["events"]]
    templates = [ScenarioPipelineTemplate.model_validate(template) for template in prepared["templates"]]
    api_version = str(prepared["api_version"])
    generation_strategy = str(prepared["generation_strategy"])
    finalized = await _generate_validated_result(
        api_version=api_version,
        generation_strategy=generation_strategy,
        events=events,
        templates=templates,
        trace_context=trace_context,
    )
    diagnostics = GenerationDiagnostics(
        excluded_candidates=[candidate.model_dump() for candidate in finalized.excluded_candidates],
        excluded_dimensions=[
            item.model_dump() if hasattr(item, "model_dump") else item
            for item in finalized.excluded_dimensions
        ],
        event_shocks=finalized.event_shocks,
        event_interactions=finalized.interactions,
    )
    saved_group, saved_scenarios = ScenarioGroupService().persist_multi_event_generation(
        scenario_group_id=group.scenario_group_id,
        title=finalized.scenario_group_title,
        description=finalized.scenario_group_description,
        dimension_definitions=[definition.model_dump() for definition in finalized.dimension_definitions],
        generation_diagnostics=diagnostics.model_dump(),
        scenarios=[scenario.model_dump() for scenario in finalized.scenarios],
        user_id=int(prepared["user_id"]),
    )
    table_data = build_scenario_group_table_data(
        saved_group.model_dump(),
        [scenario.model_dump() for scenario in saved_scenarios],
    )
    return VersionedCreateScenariosOut(
        data=VersionedCreateScenariosData(
            api_version=api_version,
            generation_strategy=generation_strategy,
            comparison_run_id=prepared["comparison_run_id"],
            scenario_group=table_data.scenario_group,
            events=events,
            dimension_definitions=finalized.dimension_definitions,
            table=table_data.table,
            generation_diagnostics=diagnostics,
        ),
    )


async def _generate_validated_result(
    *,
    api_version: str,
    generation_strategy: str,
    events: list[EventPayload],
    templates: list[ScenarioPipelineTemplate],
    trace_context: TraceContext | None,
) -> MultiEventGenerationResult:
    last_error: ValueError | MIBaseError | None = None
    for _attempt in range(3):
        try:
            result = await _invoke_multi_event_generation(
                api_version=api_version,
                events=events,
                templates=templates,
                trace_context=trace_context,
                validation_feedback=(str(last_error) if last_error is not None else None),
            )
            return finalize_generation_result(
                result,
                generation_strategy=generation_strategy,
                event_ids=[int(event.mi_event_id) for event in events],
                source_dimensions_by_event={
                    int(event.mi_event_id): {
                        dimension.dim_key: {
                            "required": dimension.required,
                            "label": dimension.label,
                            "description": dimension.description,
                            "event_type_l2_id": int(
                                template.event_type_l2_id or event.event_type_l2_id,
                            ),
                            "scenario_dimension_template_id": template.scenario_dimension_template_id,
                            "template_checksum": template.template_checksum,
                            "value_enums": list(dimension.value_enums),
                        }
                        for dimension in template.dimensions
                    }
                    for event, template in zip(
                        events,
                        templates,
                        strict=True,
                    )
                },
            )
        except MIBaseError as exc:
            if exc.error_code is not ErrorCode.LLM_INVALID_RESPONSE_ERROR:
                raise
            last_error = exc
        except ValueError as exc:
            last_error = exc
    raise MIBaseError(
        ErrorCode.LLM_INVALID_RESPONSE_ERROR,
        detail=(f"Multi-event generation result failed semantic validation after 3 attempts: {last_error}"),
    ) from last_error
