from __future__ import annotations

import asyncio

from apps.agents.scenario_group_agent.constants import (
    AGENT_NAME,
    API_IDENTIFIER_CREATE_SCENARIOS,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    AdditionalDimensionGeneration,
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
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
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

    if output.data is not None:
        scenario_group_id = int(prepared["scenario_group"].scenario_group_id)
        group_service = ScenarioGroupService()
        try:
            generation_payload = await asyncio.to_thread(
                group_service.queue_additional_dimension_generation,
                scenario_group_id,
                user_id=int(prepared["user_id"]),
            )
        except Exception as exc:
            generation_payload = {
                "status": "failed",
                "error_code": "ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
            }
            try:
                generation_payload = await asyncio.to_thread(
                    group_service.fail_additional_dimension_enqueue,
                    scenario_group_id,
                    user_id=int(prepared["user_id"]),
                    error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
                )
            except Exception as status_exc:
                logger.error(
                    "[SYNC][v4] Additional Dimension enqueue failure status update failed | "
                    "scenario_group_id={} | error={!r}",
                    scenario_group_id,
                    status_exc,
                )
            logger.error(
                "[SYNC][v4] Additional Dimension enqueue failed without failing create response | "
                "scenario_group_id={} | error_code=ADDITIONAL_DIMENSION_ENQUEUE_FAILED | error={!r}",
                scenario_group_id,
                exc,
            )
        generation = AdditionalDimensionGeneration.model_validate(generation_payload)
        output.data.generation_diagnostics.additional_dimension_generation = generation
        logger.info(
            "[SYNC][v4] Additional Dimension generation lifecycle recorded | scenario_group_id={} | "
            "generation_status={} | source_count={}",
            scenario_group_id,
            generation.status,
            len(generation.source_uncertainty_ids),
        )
        if generation.status == "queued":
            from apps.agents.scenario_group_agent.runtime import get_additional_dimension_task_runner

            try:
                get_additional_dimension_task_runner().submit(scenario_group_id)
            except Exception as exc:
                try:
                    await asyncio.to_thread(
                        group_service.fail_additional_dimension_enqueue,
                        scenario_group_id,
                        user_id=int(prepared["user_id"]),
                        error_code="ADDITIONAL_DIMENSION_ENQUEUE_FAILED",
                    )
                except Exception as status_exc:
                    logger.error(
                        "[SYNC][v4] Additional Dimension submit failure status update failed | "
                        "scenario_group_id={} | error={!r}",
                        scenario_group_id,
                        status_exc,
                    )
                generation.status = "failed"
                generation.error_code = "ADDITIONAL_DIMENSION_ENQUEUE_FAILED"
                logger.error(
                    "[SYNC][v4] Additional Dimension task submit failed without failing create response | "
                    "scenario_group_id={} | error_code=ADDITIONAL_DIMENSION_ENQUEUE_FAILED | error={!r}",
                    scenario_group_id,
                    exc,
                )
        else:
            logger.info(
                "[SYNC][v4] Additional Dimension generation completed without background task | "
                "scenario_group_id={} | generation_status={} | candidate_count=0",
                scenario_group_id,
                generation.status,
            )
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
