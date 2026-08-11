from __future__ import annotations

from fastapi import APIRouter

from apps.agents.scenario_group_agent.constants import (
    AGENT_NAME,
    API_IDENTIFIER_CREATE_SCENARIOS,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    GenerationDiagnostics,
    MultiEventCreateScenariosIn,
    V2CreateScenariosOut,
    V4MultiEventCreateScenariosSyncIn,
    VersionedCreateScenariosData,
    VersionedCreateScenariosIn,
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.flow import (
    prepare_multi_event_scenarios,
    run_multi_event_scenarios_inline,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_flow import (
    V4_GENERATION_STRATEGY,
    prepare_v4_multi_event_scenarios,
    run_v4_multi_event_scenarios_inline,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.flow import (
    prepare_create_scenarios,
    run_create_scenarios_inline,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.schemas.endpoint import CreateScenariosOut
from apps.common.logging.logger_config import logger
from apps.common.runtime.usage_context import get_accumulated_usage, reset_usage
from apps.common.tracing.context import (
    TraceContext,
    mlflow_trace_context,
    new_transaction_id,
)
from apps.persistence.scenario.schema import (
    DimensionDefinition,
    DimensionValueDefinition,
    ScenarioPipelineTemplateDimension,
    SourceLineage,
)


router = APIRouter(tags=["versioned-scenario-generation-sync"])


async def create_v1_scenarios_sync(
    payload: VersionedCreateScenariosIn,
) -> VersionedCreateScenariosOut:
    reset_usage()
    prepared = prepare_create_scenarios(
        payload.mi_event_id,
        payload.user_id,
    )
    try:
        output = await run_create_scenarios_inline(
            scenario_group_id=prepared["scenario_group_id"],
            event_data=prepared["event_data"],
            user_id=prepared["user_id"],
        )
        _ensure_v1_output_complete(output)
        event = prepared["event_data"]
        template = ScenarioService().load_pipeline_template_with_metadata(
            int(event["event_type_l2_id"]),
        )
        selected = set(output.scenario_group.dimension_selected)
        definitions = [
            _v1_dimension_definition(
                event_id=int(event["mi_event_id"]),
                event_type_l2_id=int(event["event_type_l2_id"]),
                dimension=dimension,
                display_order=index,
            )
            for index, dimension in enumerate(
                (dimension for dimension in template.ordered_dimensions() if dimension.dim_key in selected),
                start=1,
            )
        ]
        return VersionedCreateScenariosOut(
            data=VersionedCreateScenariosData(
                api_version="v1",
                generation_strategy="single_event_template_dimensions",
                scenario_group=output.scenario_group,
                events=[event],
                dimension_definitions=definitions,
                table=output.table,
                generation_diagnostics=GenerationDiagnostics(
                    target_pressure_bands=[],
                ),
                usage=get_accumulated_usage(),
            ),
        )
    except Exception as exc:
        logger.error("[SYNC][v1 create_scenarios] FAILED | error={!r}", exc)
        return VersionedCreateScenariosOut(status="error", message=str(exc))


async def create_v2_scenarios_sync(
    payload: MultiEventCreateScenariosIn,
) -> V2CreateScenariosOut:
    output = await _create_multi_event_scenarios_sync(payload, api_version="v2")
    if isinstance(output, V2CreateScenariosOut):
        return output
    return V2CreateScenariosOut(status=output.status, message=output.message)


async def create_v3_scenarios_sync(
    payload: MultiEventCreateScenariosIn,
) -> VersionedCreateScenariosOut:
    return await _create_multi_event_scenarios_sync(payload, api_version="v3")


async def create_v4_scenarios_sync(
    payload: V4MultiEventCreateScenariosSyncIn,
) -> VersionedCreateScenariosOut:
    reset_usage()
    prepared = prepare_v4_multi_event_scenarios(payload)
    try:
        from apps.common.configs.config import get_settings

        agent_config = get_settings().get_agent_config(AGENT_NAME)
        trace_context = TraceContext(
            transaction_id=new_transaction_id(),
            app_identifier=agent_config.aip_app_id,
            agent_name=AGENT_NAME,
            api_identifier=API_IDENTIFIER_CREATE_SCENARIOS,
            session_id=str(prepared["scenario_group"].scenario_group_id),
            tags={
                "api_version": "v4",
                "generation_strategy": V4_GENERATION_STRATEGY,
            },
        )
        with mlflow_trace_context(trace_context):
            output = await run_v4_multi_event_scenarios_inline(
                prepared,
                trace_context=trace_context,
            )
    except Exception as exc:
        logger.error(
            "[SYNC][v4 create_scenarios] FAILED | group_id={} | error={!r}",
            prepared["scenario_group"].scenario_group_id,
            exc,
        )
        return VersionedCreateScenariosOut(status="error", message=str(exc))
    else:
        if output.data is not None:
            output.data.usage = get_accumulated_usage()
        return output


async def _create_multi_event_scenarios_sync(
    payload: MultiEventCreateScenariosIn,
    *,
    api_version: str,
) -> V2CreateScenariosOut | VersionedCreateScenariosOut:
    reset_usage()
    prepared = prepare_multi_event_scenarios(
        payload,
        api_version=api_version,
    )
    try:
        from apps.common.configs.config import get_settings

        agent_config = get_settings().get_agent_config(AGENT_NAME)
        trace_context = TraceContext(
            transaction_id=new_transaction_id(),
            app_identifier=agent_config.aip_app_id,
            agent_name=AGENT_NAME,
            api_identifier=API_IDENTIFIER_CREATE_SCENARIOS,
            session_id=str(
                prepared["scenario_group"].scenario_group_id,
            ),
            tags={
                "api_version": api_version,
                "generation_strategy": str(prepared["generation_strategy"]),
            },
        )
        with mlflow_trace_context(trace_context):
            output = await run_multi_event_scenarios_inline(
                prepared,
                trace_context=trace_context,
            )
    except Exception as exc:
        logger.error(
            "[SYNC][{} create_scenarios] FAILED | group_id={} | error={!r}",
            api_version,
            prepared["scenario_group"].scenario_group_id,
            exc,
        )
        if api_version == "v2":
            return V2CreateScenariosOut(status="error", message=str(exc))
        return VersionedCreateScenariosOut(status="error", message=str(exc))
    else:
        if output.data is not None:
            output.data.usage = get_accumulated_usage()
        return output


def _ensure_v1_output_complete(output: CreateScenariosOut) -> None:
    if output.scenario_group is None or output.table is None:
        message = "v1 scenario generation output is incomplete"
        raise ValueError(message)


def _v1_dimension_definition(
    *,
    event_id: int,
    event_type_l2_id: int,
    dimension: ScenarioPipelineTemplateDimension,
    display_order: int,
) -> DimensionDefinition:
    dim_key = dimension.dim_key
    source_ref = SourceLineage(
        event_id=event_id,
        event_type_l2_id=event_type_l2_id,
        dim_key=dim_key,
        source_type="template_domain_knowledge",
        assumption_yn="N",
        rationale="단일 Event Type Template의 원본 dimension을 사용한다.",
    )
    return DimensionDefinition(
        dimension_id=dim_key,
        label=dimension.label,
        description=dimension.description,
        required=dimension.required,
        display_order=display_order,
        source_refs=[source_ref],
        values=[
            DimensionValueDefinition(
                value_id=str(value),
                label=str(value),
                source_assignments=[
                    source_ref.model_copy(update={"value": str(value)}),
                ],
            )
            for value in dimension.value_enums
        ],
    )
