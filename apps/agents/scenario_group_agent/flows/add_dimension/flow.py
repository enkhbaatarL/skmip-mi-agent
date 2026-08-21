from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

# ruff: noqa: CPY001
from apps.agents.scenario_group_agent.constants import (
    ADDITIONAL_DIMENSION_API_VERSION,
    AGENT_NAME,
    API_IDENTIFIER_ADD_DIMENSION,
)
from apps.agents.scenario_group_agent.flows.add_dimension.api_schema import (
    AdditionalDimensionsData,
    AdditionalDimensionsOut,
)
from apps.agents.scenario_group_agent.flows.add_dimension.nodes import (
    AdditionalDimensionHydrationResult,
    build_unused_impact_analysis,
    filter_available_candidates,
    hydrate_additional_dimension_candidates,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.nodes import (
    invoke_stage_structured_output,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4EventImpactAnalysisResult,
    V4ReadableAdditionalDimensionDesignDraft,
)
from apps.agents.scenario_group_agent.persistence.model_impact_lever_service import (
    ModelImpactLeverService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.presentation import build_presentation_dimension_definitions
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    V4_ADDITIONAL_DIMENSION_SYSTEM_PROMPT,
    build_v4_additional_dimension_user_prompt,
)
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext, mlflow_trace_context, new_transaction_id
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload


MAX_ADDITIONAL_DIMENSION_ATTEMPTS = 3
ADDITIONAL_DIMENSION_CANDIDATES_INVALID = "ADDITIONAL_DIMENSION_CANDIDATES_INVALID"
ADDITIONAL_DIMENSION_STALE_TIMEOUT = "STALE_TIMEOUT"


@contextmanager
def _additional_dimension_attempt_span(*, attempt: int) -> Iterator[Any | None]:
    try:
        from apps.common.configs.config import get_settings

        settings = get_settings()
        is_enabled = getattr(settings, "is_mlflow_tracing_enabled", None)
        enabled = (
            bool(is_enabled(agent_name=AGENT_NAME))
            if callable(is_enabled)
            else bool(getattr(settings, "mlflow_tracing_enabled", False))
        )
    except Exception as exc:
        logger.warning(
            "Additional Dimension attempt span disabled | attempt={} | error={!r}",
            attempt,
            exc,
        )
        with nullcontext(None) as span:
            yield span
        return
    if not enabled:
        with nullcontext(None) as span:
            yield span
        return
    try:
        import mlflow

        manager = mlflow.start_span(
            name="additional_dimension_design_attempt",
            span_type="CHAIN",
            attributes={"attempt": attempt},
        )
    except Exception as exc:
        logger.warning(
            "Additional Dimension attempt span disabled | attempt={} | error={!r}",
            attempt,
            exc,
        )
        with nullcontext(None) as span:
            yield span
        return
    try:
        span = manager.__enter__()
    except Exception as exc:
        logger.warning(
            "Additional Dimension attempt span enter failed | attempt={} | error={!r}",
            attempt,
            exc,
        )
        with nullcontext(None) as fallback_span:
            yield fallback_span
        return
    try:
        yield span
    except BaseException as exc:
        try:
            manager.__exit__(type(exc), exc, exc.__traceback__)
        except Exception as exit_exc:
            logger.warning(
                "Additional Dimension attempt span exit failed | attempt={} | error={!r}",
                attempt,
                exit_exc,
            )
        raise
    else:
        try:
            manager.__exit__(None, None, None)
        except Exception as exc:
            logger.warning(
                "Additional Dimension attempt span exit failed | attempt={} | error={!r}",
                attempt,
                exc,
            )


def _record_attempt_result(span: Any | None, result: AdditionalDimensionHydrationResult) -> None:  # noqa: ANN401
    if span is None:
        return
    try:
        span.set_attributes(
            {
                "input_candidate_count": result.input_candidate_count,
                "valid_candidate_count": len(result.valid_candidates),
                "rejected_candidate_count": len(result.rejected_candidates),
                "rejection_reason_codes": ",".join(result.rejection_reason_codes) or "none",
            },
        )
    except Exception as exc:
        logger.warning("Additional Dimension attempt span result logging failed | error={!r}", exc)


def _candidate_validation_feedback(result: AdditionalDimensionHydrationResult) -> str:
    details = [
        f"candidate {item.candidate_index} ({', '.join(item.source_aliases) or 'source 없음'}): "
        f"{item.reason_code} - {item.detail}"
        for item in result.rejected_candidates
    ]
    return "Additional Dimension 후보가 모두 검증에서 탈락했습니다. " + " | ".join(details)


async def _generate_candidates_with_retries(
    *,
    scenario_group_id: int,
    transaction_id: str,
    impact_analysis: V4EventImpactAnalysisResult,
    impact_levers: list[ModelImpactLeverPayload],
    selected_definitions: list[dict[str, Any]],
    trace_context: TraceContext,
) -> AdditionalDimensionHydrationResult:
    hydration_result = AdditionalDimensionHydrationResult(input_candidate_count=0)
    validation_feedback: str | None = None
    for attempt in range(1, MAX_ADDITIONAL_DIMENSION_ATTEMPTS + 1):
        if attempt > 1:
            await asyncio.sleep(float(2 ** (attempt - 2)))
        with _additional_dimension_attempt_span(attempt=attempt) as attempt_span:
            readable: V4ReadableAdditionalDimensionDesignDraft = await invoke_stage_structured_output(
                output_schema=V4ReadableAdditionalDimensionDesignDraft,
                system_prompt=V4_ADDITIONAL_DIMENSION_SYSTEM_PROMPT,
                user_prompt=build_v4_additional_dimension_user_prompt(
                    impact_analysis=impact_analysis.model_dump(),
                    impact_levers=[lever.model_dump() for lever in impact_levers],
                    selected_definitions=selected_definitions,
                    validation_feedback=validation_feedback,
                ),
                trace_context=trace_context,
                stage="additional_dimension_design",
            )
            hydration_result = hydrate_additional_dimension_candidates(
                readable,
                impact_analysis=impact_analysis,
                impact_levers=impact_levers,
            )
            _record_attempt_result(attempt_span, hydration_result)

        rejected_count = len(hydration_result.rejected_candidates)
        reason_codes = ",".join(hydration_result.rejection_reason_codes) or "none"
        if rejected_count:
            logger.warning(
                "Additional Dimension candidates rejected | scenario_group_id={} | transaction_id={} | "
                "attempt={} | input_count={} | valid_count={} | rejected_count={} | reason_codes={}",
                scenario_group_id,
                transaction_id,
                attempt,
                hydration_result.input_candidate_count,
                len(hydration_result.valid_candidates),
                rejected_count,
                reason_codes,
            )
        if hydration_result.input_candidate_count == 0 or hydration_result.valid_candidates:
            return hydration_result
        validation_feedback = _candidate_validation_feedback(hydration_result)
    return hydration_result


async def run_additional_dimension_generation(
    scenario_group_id: int,
    *,
    run_id: str | None = None,
) -> None:
    active_run_id = run_id or str(uuid4())
    service = ScenarioGroupService()
    try:
        started = await asyncio.to_thread(
            service.start_additional_dimension_generation,
            scenario_group_id,
            run_id=active_run_id,
        )
    except Exception as exc:
        try:
            await asyncio.to_thread(
                service.fail_additional_dimension_claim,
                scenario_group_id,
                run_id=active_run_id,
                error_code="ADDITIONAL_DIMENSION_CLAIM_FAILED",
            )
        except Exception as status_exc:
            logger.error(
                "Additional Dimension claim failure status update failed | scenario_group_id={} | error={!r}",
                scenario_group_id,
                status_exc,
            )
        logger.error(
            "Additional Dimension initial claim failed | scenario_group_id={} | "
            "error_code=ADDITIONAL_DIMENSION_CLAIM_FAILED | error={!r}",
            scenario_group_id,
            exc,
        )
        return
    if started is None:
        logger.info(
            "Additional Dimension generation skipped | scenario_group_id={} | reason=not_runnable",
            scenario_group_id,
        )
        return
    source_fingerprint = str(started["source_fingerprint"])
    transaction_id = new_transaction_id()
    try:
        from apps.common.configs.config import get_settings

        agent_config = get_settings().get_agent_config(AGENT_NAME)
        trace_context = TraceContext(
            transaction_id=transaction_id,
            app_identifier=agent_config.aip_app_id,
            agent_name=AGENT_NAME,
            api_identifier=API_IDENTIFIER_ADD_DIMENSION,
            session_id=str(scenario_group_id),
            tags={"api_version": ADDITIONAL_DIMENSION_API_VERSION},
        )
        with mlflow_trace_context(trace_context):
            logger.info(
                "Additional Dimension generation started | scenario_group_id={} | transaction_id={} | "
                "api_identifier={} | api_version={}",
                scenario_group_id,
                transaction_id,
                API_IDENTIFIER_ADD_DIMENSION,
                ADDITIONAL_DIMENSION_API_VERSION,
            )
            impact_analysis = build_unused_impact_analysis(
                started["generation_diagnostics"],
                started["dimension_definitions"],
            )
            uncertainties = [*impact_analysis.path_uncertainties, *impact_analysis.interaction_uncertainties]
            if not uncertainties:
                stored = await asyncio.to_thread(
                    service.complete_additional_dimension_generation,
                    scenario_group_id,
                    source_fingerprint=source_fingerprint,
                    run_id=active_run_id,
                    candidates=[],
                )
                logger.info(
                    "Additional Dimension generation completed | scenario_group_id={} | transaction_id={} | "
                    "candidate_count=0 | persisted={} | api_identifier={} | api_version={}",
                    scenario_group_id,
                    transaction_id,
                    stored,
                    API_IDENTIFIER_ADD_DIMENSION,
                    ADDITIONAL_DIMENSION_API_VERSION,
                )
                return
            impact_levers, _version, _checksum = await asyncio.to_thread(
                ModelImpactLeverService().load_active_catalog,
            )
            hydration_result = await _generate_candidates_with_retries(
                scenario_group_id=scenario_group_id,
                transaction_id=transaction_id,
                impact_analysis=impact_analysis,
                impact_levers=impact_levers,
                selected_definitions=started["dimension_definitions"],
                trace_context=trace_context,
            )
            if hydration_result.input_candidate_count > 0 and not hydration_result.valid_candidates:
                await asyncio.to_thread(
                    service.fail_additional_dimension_generation,
                    scenario_group_id,
                    source_fingerprint=source_fingerprint,
                    run_id=active_run_id,
                    error_code=ADDITIONAL_DIMENSION_CANDIDATES_INVALID,
                )
                logger.error(
                    "Additional Dimension generation failed | scenario_group_id={} | transaction_id={} | "
                    "attempts={} | input_count={} | valid_count=0 | rejected_count={} | reason_codes={} | "
                    "api_identifier={} | api_version={} | error_code={}",
                    scenario_group_id,
                    transaction_id,
                    MAX_ADDITIONAL_DIMENSION_ATTEMPTS,
                    hydration_result.input_candidate_count,
                    len(hydration_result.rejected_candidates),
                    ",".join(hydration_result.rejection_reason_codes),
                    API_IDENTIFIER_ADD_DIMENSION,
                    ADDITIONAL_DIMENSION_API_VERSION,
                    ADDITIONAL_DIMENSION_CANDIDATES_INVALID,
                )
                return
            candidates = hydration_result.valid_candidates
            stored = await asyncio.to_thread(
                service.complete_additional_dimension_generation,
                scenario_group_id,
                source_fingerprint=source_fingerprint,
                run_id=active_run_id,
                candidates=[item.model_dump() for item in candidates],
            )
            logger.info(
                "Additional Dimension generation completed | scenario_group_id={} | transaction_id={} | "
                "input_count={} | valid_count={} | rejected_count={} | reason_codes={} | persisted={} | "
                "api_identifier={} | api_version={}",
                scenario_group_id,
                transaction_id,
                hydration_result.input_candidate_count,
                len(candidates),
                len(hydration_result.rejected_candidates),
                ",".join(hydration_result.rejection_reason_codes) or "none",
                stored,
                API_IDENTIFIER_ADD_DIMENSION,
                ADDITIONAL_DIMENSION_API_VERSION,
            )
    except asyncio.CancelledError:
        await asyncio.shield(
            asyncio.to_thread(
                service.fail_additional_dimension_generation,
                scenario_group_id,
                source_fingerprint=source_fingerprint,
                run_id=active_run_id,
                error_code="SERVER_SHUTDOWN",
                interrupted=True,
            ),
        )
        logger.error(
            "Additional Dimension generation interrupted | scenario_group_id={} | transaction_id={} | "
            "api_identifier={} | api_version={} | error_code=SERVER_SHUTDOWN",
            scenario_group_id,
            transaction_id,
            API_IDENTIFIER_ADD_DIMENSION,
            ADDITIONAL_DIMENSION_API_VERSION,
        )
        raise
    except Exception as exc:
        try:
            await asyncio.to_thread(
                service.fail_additional_dimension_generation,
                scenario_group_id,
                source_fingerprint=source_fingerprint,
                run_id=active_run_id,
                error_code="ADDITIONAL_DIMENSION_GENERATION_FAILED",
            )
        except Exception as status_exc:
            logger.error(
                "Additional Dimension failure status update failed | scenario_group_id={} | transaction_id={} | "
                "api_identifier={} | api_version={} | error={!r}",
                scenario_group_id,
                transaction_id,
                API_IDENTIFIER_ADD_DIMENSION,
                ADDITIONAL_DIMENSION_API_VERSION,
                status_exc,
            )
        logger.error(
            "Additional Dimension generation failed | scenario_group_id={} | transaction_id={} | "
            "api_identifier={} | api_version={} | error={!r}",
            scenario_group_id,
            transaction_id,
            API_IDENTIFIER_ADD_DIMENSION,
            ADDITIONAL_DIMENSION_API_VERSION,
            exc,
        )


def _generation_field(generation: dict[str, Any], snake_key: str, camel_key: str) -> object:
    return generation.get(snake_key, generation.get(camel_key))


def _parse_generation_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    elif value:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            return None
    else:
        return None
    return parsed.replace(tzinfo=parsed.tzinfo or UTC).astimezone(UTC)


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _active_generation_timestamp(generation: dict[str, Any]) -> datetime | None:
    status = str(generation.get("status") or "not_requested")
    if status == "queued":
        raw_timestamp = _generation_field(generation, "queued_at", "queuedAt")
    elif status == "running":
        raw_timestamp = _generation_field(generation, "started_at", "startedAt")
        if raw_timestamp is None or raw_timestamp == "":
            raw_timestamp = _generation_field(generation, "queued_at", "queuedAt")
    else:
        return None
    return _parse_generation_timestamp(raw_timestamp)


def _get_additional_dimension_stale_after_seconds() -> float:
    from apps.common.configs.config import get_settings

    return get_settings().additional_dimension_stale_after_seconds


def _is_stale_generation(
    generation: dict[str, Any],
    *,
    stale_after_seconds: float,
    now: datetime,
) -> bool:
    timestamp = _active_generation_timestamp(generation)
    if timestamp is None:
        return False
    normalized_now = now.replace(tzinfo=now.tzinfo or UTC).astimezone(UTC)
    return (normalized_now - timestamp).total_seconds() >= stale_after_seconds


def get_additional_dimensions(scenario_group_id: int) -> AdditionalDimensionsOut:
    payload = ScenarioGroupService().load_additional_dimensions(scenario_group_id)
    generation = payload["generation"]
    status = str(generation.get("status") or "not_requested")
    stale = False
    if _active_generation_timestamp(generation) is not None:
        stale = _is_stale_generation(
            generation,
            stale_after_seconds=_get_additional_dimension_stale_after_seconds(),
            now=_utc_now(),
        )
    if stale:
        status = "interrupted"
    candidates = filter_available_candidates(
        payload["candidates"],
        dimension_selected=payload["dimension_selected"],
        active_definitions=payload["dimension_definitions"],
    )
    if status == "ready":
        presentation_status = "ready"
        items = build_presentation_dimension_definitions(candidates, engine_version="v4")
        message = "성공"
    elif status in {"queued", "running"}:
        presentation_status = "pending"
        items = []
        message = "추가 Dimension 후보를 생성하고 있습니다."
    else:
        presentation_status = "unavailable"
        items = []
        message = "추가 Dimension 후보를 사용할 수 없습니다."
    return AdditionalDimensionsOut(
        message=message,
        data=AdditionalDimensionsData(
            scenario_group_id=scenario_group_id,
            generation_status=status,
            dimension_definitions={"status": presentation_status, "items": items},
            available_count=len(items),
            updated_at=payload.get("updated_at"),
            error_code=(
                ADDITIONAL_DIMENSION_STALE_TIMEOUT
                if stale
                else generation.get("error_code") or generation.get("errorCode")
            ),
        ),
    )
