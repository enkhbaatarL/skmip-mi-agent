from __future__ import annotations

import time
from typing import Any

from apps.agents.scenario_group_agent.constants import (
    AGENT_NAME,
    API_IDENTIFIER_CREATE_SCENARIOS,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    ExcludedCandidate,
    GenerationDiagnostics,
    V4MultiEventCreateScenariosIn,
    VersionedCreateScenariosData,
    VersionedCreateScenariosOut,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    ParameterCoverage,
    V4GenerationResult,
    finalize_v4_generation_result,
)
from apps.agents.scenario_group_agent.persistence.event_service import EventService
from apps.agents.scenario_group_agent.persistence.scenario_group_service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    MODEL_LEVER_SYSTEM_PROMPT,
    build_model_lever_user_prompt,
)
from apps.agents.scenario_group_agent.schemas.endpoint import CreateScenariosOut
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import (
    TraceContext,
    mlflow_trace_context,
    new_transaction_id,
)
from apps.common.values.error_codes import ErrorCode
from apps.common.values.response import CallBackBody
from apps.connectors.callback.callback_client import send_callback
from apps.persistence.event.schema import EventPayload
from apps.persistence.model_parameter.schema import ModelImpactLeverPayload
from apps.persistence.model_parameter.service import ModelImpactLeverService
from apps.persistence.scenario.schema import DimensionDefinition, SourceLineage
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
        target_market=payload.target_market,
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
        "target_market": payload.target_market,
        "comparison_run_id": payload.comparison_run_id,
        "user_id": payload.user_id,
    }


async def _invoke_v4_generation(
    *,
    events: list[EventPayload],
    target_market: str,
    impact_levers: list[ModelImpactLeverPayload],
    catalog_version: str,
    trace_context: TraceContext | None,
    validation_feedback: str | None = None,
) -> V4GenerationResult:
    from apps.common.configs.config import get_settings
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    user_prompt = build_model_lever_user_prompt(
        events=[event.model_dump() for event in events],
        target_market=target_market,
        impact_levers=[lever.model_dump() for lever in impact_levers],
        catalog_version=catalog_version,
        validation_feedback=validation_feedback,
    )
    response = await invoke_llm_structured_output(
        output_schema=V4GenerationResult,
        messages=[
            {"role": "system", "content": MODEL_LEVER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_retries=2,
        trace_context=trace_context,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
    )
    return V4GenerationResult.model_validate(response.result)


async def _generate_validated_v4_result(
    *,
    events: list[EventPayload],
    target_market: str,
    impact_levers: list[ModelImpactLeverPayload],
    catalog_version: str,
    trace_context: TraceContext | None,
) -> tuple[V4GenerationResult, ParameterCoverage]:
    last_error: ValueError | None = None
    for _attempt in range(3):
        result = await _invoke_v4_generation(
            events=events,
            target_market=target_market,
            impact_levers=impact_levers,
            catalog_version=catalog_version,
            trace_context=trace_context,
            validation_feedback=str(last_error) if last_error is not None else None,
        )
        try:
            return finalize_v4_generation_result(
                result,
                event_ids=[int(event.mi_event_id) for event in events],
                impact_levers=impact_levers,
            )
        except ValueError as exc:
            last_error = exc
    raise MIBaseError(
        ErrorCode.LLM_INVALID_RESPONSE_ERROR,
        detail=(f"v4 multi-event generation result failed semantic validation after 3 attempts: {last_error}"),
    ) from last_error


async def run_v4_multi_event_scenarios_inline(
    prepared: dict[str, Any],
    *,
    trace_context: TraceContext | None = None,
) -> VersionedCreateScenariosOut:
    group = ScenarioGroupPayload.model_validate(prepared["scenario_group"])
    events = [EventPayload.model_validate(event) for event in prepared["events"]]
    impact_levers = [ModelImpactLeverPayload.model_validate(lever) for lever in prepared["impact_levers"]]
    target_market = str(prepared["target_market"])
    catalog_version = str(prepared["impact_catalog_version"])
    finalized, coverage = await _generate_validated_v4_result(
        events=events,
        target_market=target_market,
        impact_levers=impact_levers,
        catalog_version=catalog_version,
        trace_context=trace_context,
    )
    dimension_definitions = _with_event_lineage(
        finalized.dimension_definitions,
        events,
    )
    diagnostics = GenerationDiagnostics(
        excluded_candidates=[
            ExcludedCandidate(
                global_pressure_band=candidate.target_market_pressure_band,
                reason_code=candidate.reason_code,
                reason=candidate.reason,
            )
            for candidate in finalized.excluded_scenarios
        ],
        excluded_dimensions=[{"reason": reason} for reason in finalized.excluded_dimensions],
        target_market=target_market,
        impact_catalog_version=catalog_version,
        covered_dimensions=coverage.covered_dimension_ids,
        uncovered_dimensions=coverage.uncovered_dimension_ids,
        unsupported_levers=coverage.unsupported_lever_codes,
        unsupported_lever_details=coverage.unsupported_lever_details,
        coverage_status=coverage.coverage_status,
        event_impact_facts=[fact.model_dump() for fact in finalized.event_impact_facts],
        event_interactions=[interaction.model_dump() for interaction in finalized.interactions],
    )
    scenarios = [
        {
            **scenario.model_dump(),
            "baseline_yn": "Y" if scenario.baseline_yn else "N",
            "global_pressure_band": scenario.target_market_pressure_band,
            "global_pressure_rationale": (scenario.target_market_pressure_rationale),
        }
        for scenario in finalized.scenarios
    ]
    saved_group, saved_scenarios = ScenarioGroupService().persist_multi_event_generation(
        scenario_group_id=group.scenario_group_id,
        title=finalized.group_title,
        description=finalized.group_description,
        dimension_definitions=[definition.model_dump() for definition in dimension_definitions],
        generation_diagnostics=diagnostics.model_dump(),
        scenarios=scenarios,
        user_id=int(prepared["user_id"]),
    )
    table_data = build_scenario_group_table_data(
        saved_group.model_dump(),
        [scenario.model_dump() for scenario in saved_scenarios],
    )
    return VersionedCreateScenariosOut(
        data=VersionedCreateScenariosData(
            api_version="v4",
            generation_strategy=V4_GENERATION_STRATEGY,
            comparison_run_id=prepared["comparison_run_id"],
            target_market=target_market,
            impact_catalog_version=catalog_version,
            scenario_group=table_data.scenario_group,
            events=events,
            dimension_definitions=dimension_definitions,
            table=table_data.table,
            generation_diagnostics=diagnostics,
        ),
    )


def _with_event_lineage(
    definitions: list[DimensionDefinition],
    events: list[EventPayload],
) -> list[DimensionDefinition]:
    event_type_l2_by_id = {int(event.mi_event_id): event.event_type_l2_id for event in events}
    return [
        definition.model_copy(
            update={
                "source_refs": [
                    SourceLineage(
                        event_id=event_id,
                        event_type_l2_id=event_type_l2_by_id[event_id],
                        dim_key=definition.dimension_id,
                        source_type="derived_interpretation",
                        assumption_yn="N",
                        rationale=(
                            f"Event {event_id} 사실과 모델 영향 레버를 기반으로 "
                            f"{definition.dimension_id} dimension을 구성했다."
                        ),
                    )
                    for event_id in definition.source_event_ids
                ],
            },
        )
        for definition in definitions
    ]


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
    "prepare_v4_multi_event_scenarios",
    "run_v4_multi_event_scenarios_background",
    "run_v4_multi_event_scenarios_inline",
]
