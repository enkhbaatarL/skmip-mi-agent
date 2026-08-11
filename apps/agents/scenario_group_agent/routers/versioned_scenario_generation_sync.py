from __future__ import annotations

from apps.agents.scenario_group_agent.constants import (
    AGENT_NAME,
    API_IDENTIFIER_CREATE_SCENARIOS,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    MultiEventCreateScenariosIn,
    V2CreateScenariosOut,
    V4MultiEventCreateScenariosSyncIn,
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
from apps.common.logging.logger_config import logger
from apps.common.runtime.usage_context import get_accumulated_usage, reset_usage
from apps.common.tracing.context import (
    TraceContext,
    mlflow_trace_context,
    new_transaction_id,
)


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
