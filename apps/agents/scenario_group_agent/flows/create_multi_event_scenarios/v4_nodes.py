from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    ExcludedCandidate,
    GenerationDiagnostics,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.nodes import (
    MAX_STAGE_ATTEMPTS,
    _backoff,
    _retry_validation_feedback,
    classify_llm_error,
    error_code_from_name,
    invoke_stage_structured_output,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import (
    V4MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDesignDraft,
    V4DimensionDesignResult,
    V4EventImpactAnalysisDraft,
    V4EventImpactAnalysisResult,
    V4ReadableDimensionDesignDraft,
    V4ReadableEventAnalysisDraft,
    V4ReadableInteractionAnalysisDraft,
    V4ReadableScenarioSynthesisDraft,
    expand_v4_readable_dimension_design,
    expand_v4_readable_event_analysis,
    expand_v4_readable_scenario_synthesis,
    finalize_v4_dimension_design,
    finalize_v4_event_impact_analysis,
    finalize_v4_generation_result,
    merge_v4_readable_interactions,
    v4_analysis_result_to_draft,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    V4_DIMENSION_SYSTEM_PROMPT,
    V4_EVENT_IMPACT_SYSTEM_PROMPT,
    V4_INTERACTION_SYSTEM_PROMPT,
    V4_SCENARIO_SYSTEM_PROMPT,
    build_v4_dimension_design_user_prompt,
    build_v4_event_fact_candidates,
    build_v4_event_impact_analysis_user_prompt,
    build_v4_interaction_analysis_user_prompt,
    build_v4_scenario_synthesis_user_prompt,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload


V4_EVENT_LLM_TIMEOUT_SECONDS = 180.0


def _emit_internal_retry(
    *,
    phase: str,
    attempt: int,
    validation_code: str | None,
    reference_ids: list[str] | None = None,
) -> None:
    if attempt > MAX_STAGE_ATTEMPTS:
        return
    try:
        writer = get_stream_writer()
    except RuntimeError:
        return
    writer(
        {
            "kind": "stage_retry",
            "phase": phase,
            "attempt": attempt,
            "maxAttempts": MAX_STAGE_ATTEMPTS,
            "validationCode": validation_code,
            "referenceIds": reference_ids or [],
        }
    )


@dataclass(frozen=True, slots=True)
class _EventAnalysisOutcome:
    event_id: int
    attempts: int
    result: V4EventImpactAnalysisResult | None = None
    error: str | None = None
    error_code: str | None = None


async def _analyze_event_with_retries(
    *,
    event: EventPayload,
    impact_levers: list[ModelImpactLeverPayload],
    catalog_version: str,
    analysis_as_of: str,
    trace_context: TraceContext | None,
) -> _EventAnalysisOutcome:
    event_id = int(event.mi_event_id)
    event_payload = event.model_dump()
    fact_candidates = build_v4_event_fact_candidates(event_payload)
    feedback: str | None = None
    for attempt in range(1, MAX_STAGE_ATTEMPTS + 1):
        await _backoff(attempt)
        try:
            try:
                async with asyncio.timeout(V4_EVENT_LLM_TIMEOUT_SECONDS):
                    readable: V4ReadableEventAnalysisDraft = await invoke_stage_structured_output(
                        output_schema=V4ReadableEventAnalysisDraft,
                        system_prompt=V4_EVENT_IMPACT_SYSTEM_PROMPT,
                        user_prompt=build_v4_event_impact_analysis_user_prompt(
                            events=[event_payload],
                            impact_levers=[lever.model_dump() for lever in impact_levers],
                            catalog_version=catalog_version,
                            analysis_as_of=analysis_as_of,
                            validation_feedback=feedback,
                        ),
                        trace_context=trace_context,
                        stage=f"event_impact_analysis:{event_id}",
                        reasoning_effort_override="low",
                    )
            except TimeoutError as exc:
                raise TimeoutError(
                    f"Event {event_id} impact analysis exceeded {V4_EVENT_LLM_TIMEOUT_SECONDS:g}s",
                ) from exc
            draft = expand_v4_readable_event_analysis(
                readable,
                event_id=event_id,
                observed_at=event.occurred_at,
                fact_candidates=fact_candidates,
            )
            result = finalize_v4_event_impact_analysis(
                draft,
                event_ids=[event_id],
                impact_levers=impact_levers,
            )
            return _EventAnalysisOutcome(event_id=event_id, attempts=attempt, result=result)
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            feedback = detail
            if retryable and attempt < MAX_STAGE_ATTEMPTS:
                _emit_internal_retry(
                    phase="event_analysis",
                    attempt=attempt + 1,
                    validation_code=error_code,
                    reference_ids=[str(event_id)],
                )
            if not retryable or attempt >= MAX_STAGE_ATTEMPTS:
                return _EventAnalysisOutcome(
                    event_id=event_id,
                    attempts=attempt,
                    error=detail,
                    error_code=error_code,
                )
    return _EventAnalysisOutcome(
        event_id=event_id,
        attempts=MAX_STAGE_ATTEMPTS,
        error="Event analysis retry state exhausted",
        error_code=ErrorCode.LLM_INVOCATION_ERROR.name,
    )


class AnalyzeEventImpactsNode(BaseNode):
    async def run(
        self,
        state: V4MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        trace_context = runtime.context if runtime is not None else None
        outcomes = await asyncio.gather(
            *[
                _analyze_event_with_retries(
                    event=event,
                    impact_levers=state.impact_levers,
                    catalog_version=state.impact_catalog_version,
                    analysis_as_of=state.analysis_as_of,
                    trace_context=trace_context,
                )
                for event in state.events
            ],
        )
        attempts = max((outcome.attempts for outcome in outcomes), default=0)
        failures = [outcome for outcome in outcomes if outcome.result is None]
        if failures:
            detail = "; ".join(f"Event {item.event_id}: {item.error}" for item in failures)[:600]
            return {
                "analysis_attempt": attempts,
                "analysis_draft": None,
                "analysis_error": detail,
                "analysis_error_code": failures[0].error_code,
                "analysis_retryable": False,
            }
        local_drafts = [v4_analysis_result_to_draft(outcome.result) for outcome in outcomes if outcome.result]
        merged = V4EventImpactAnalysisDraft(
            event_facts=[fact for draft in local_drafts for fact in draft.event_facts],
            decision_basis=[item for draft in local_drafts for item in draft.decision_basis],
            event_exclusions=[item for draft in local_drafts for item in draft.event_exclusions],
            impact_paths=[path for draft in local_drafts for path in draft.impact_paths],
            path_uncertainties=[item for draft in local_drafts for item in draft.path_uncertainties],
        )
        return {
            "analysis_attempt": attempts,
            "analysis_draft": merged,
            "analysis_error": None,
            "analysis_error_code": None,
            "analysis_retryable": False,
        }


def validate_v4_event_impacts(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if not isinstance(state.analysis_draft, V4EventImpactAnalysisDraft):
        return {}
    try:
        finalized = finalize_v4_event_impact_analysis(
            state.analysis_draft,
            event_ids=[int(event.mi_event_id) for event in state.events],
            impact_levers=state.impact_levers,
        )
        return {
            "analysis_draft": finalized,
            "analysis_error": None,
            "analysis_error_code": None,
            "analysis_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        if retryable and state.analysis_attempt < MAX_STAGE_ATTEMPTS:
            _emit_internal_retry(
                phase="event_analysis",
                attempt=state.analysis_attempt + 1,
                validation_code=error_code,
            )
        return {
            "analysis_error": detail,
            "analysis_error_code": error_code,
            "analysis_retryable": retryable,
        }


def route_after_v4_event_impacts(state: V4MultiEventGenerationState) -> str:
    if isinstance(state.analysis_draft, V4EventImpactAnalysisResult) and state.analysis_error is None:
        return "analyze_event_interactions"
    if state.analysis_retryable and state.analysis_attempt < MAX_STAGE_ATTEMPTS:
        return "analyze_event_impacts"
    return "fail_generation"


class AnalyzeEventInteractionsNode(BaseNode):
    async def run(
        self,
        state: V4MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(state.analysis_draft, V4EventImpactAnalysisResult):
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="validated v4 Impact Paths are required")
        path_event_ids = {path.event_id for path in state.analysis_draft.impact_paths}
        if len(path_event_ids) < 2:
            return {
                "interaction_attempt": 0,
                "interaction_draft": V4ReadableInteractionAnalysisDraft(),
                "interaction_error": None,
                "interaction_error_code": None,
                "interaction_retryable": False,
            }
        attempt = state.interaction_attempt + 1
        await _backoff(attempt)
        try:
            draft: V4ReadableInteractionAnalysisDraft = await invoke_stage_structured_output(
                output_schema=V4ReadableInteractionAnalysisDraft,
                system_prompt=V4_INTERACTION_SYSTEM_PROMPT,
                user_prompt=build_v4_interaction_analysis_user_prompt(
                    impact_paths=[path.model_dump() for path in state.analysis_draft.impact_paths],
                    validation_feedback=state.interaction_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
                stage="event_interaction_analysis",
                reasoning_effort_override="low",
            )
            return {
                "interaction_attempt": attempt,
                "interaction_draft": draft,
                "interaction_error": None,
                "interaction_error_code": None,
                "interaction_retryable": False,
            }
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            if retryable and attempt < MAX_STAGE_ATTEMPTS:
                _emit_internal_retry(
                    phase="event_analysis",
                    attempt=attempt + 1,
                    validation_code=error_code,
                )
            return {
                "interaction_attempt": attempt,
                "interaction_draft": None,
                "interaction_error": detail,
                "interaction_error_code": error_code,
                "interaction_retryable": retryable,
            }


def validate_v4_event_interactions(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if not isinstance(state.analysis_draft, V4EventImpactAnalysisResult):
        return {}
    if not isinstance(state.interaction_draft, V4ReadableInteractionAnalysisDraft):
        return {}
    try:
        merged = merge_v4_readable_interactions(state.analysis_draft, state.interaction_draft)
        finalized = finalize_v4_event_impact_analysis(
            merged,
            event_ids=[int(event.mi_event_id) for event in state.events],
            impact_levers=state.impact_levers,
        )
        return {
            "analysis_draft": finalized,
            "interaction_draft": None,
            "interaction_error": None,
            "interaction_error_code": None,
            "interaction_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        if retryable and state.interaction_attempt < MAX_STAGE_ATTEMPTS:
            _emit_internal_retry(
                phase="event_analysis",
                attempt=state.interaction_attempt + 1,
                validation_code=error_code,
            )
        return {
            "interaction_error": detail,
            "interaction_error_code": error_code,
            "interaction_retryable": retryable,
        }


def route_after_v4_event_interactions(state: V4MultiEventGenerationState) -> str:
    if (
        isinstance(state.analysis_draft, V4EventImpactAnalysisResult)
        and state.interaction_draft is None
        and state.interaction_error is None
    ):
        return "design_model_lever_dimensions"
    if state.interaction_retryable and state.interaction_attempt < MAX_STAGE_ATTEMPTS:
        return "analyze_event_interactions"
    return "fail_generation"


class DesignModelLeverDimensionsNode(BaseNode):
    async def run(
        self,
        state: V4MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(state.analysis_draft, V4EventImpactAnalysisResult):
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="v4 Event impact analysis is required")
        attempt = state.dimension_attempt + 1
        await _backoff(attempt)
        try:
            readable: V4ReadableDimensionDesignDraft = await invoke_stage_structured_output(
                output_schema=V4ReadableDimensionDesignDraft,
                system_prompt=V4_DIMENSION_SYSTEM_PROMPT,
                user_prompt=build_v4_dimension_design_user_prompt(
                    impact_analysis=state.analysis_draft.model_dump(),
                    validation_warnings=[warning.model_dump() for warning in state.analysis_draft.validation_warnings],
                    analysis_as_of=state.analysis_as_of,
                    validation_feedback=state.dimension_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
                stage="dimension_design",
            )
            draft = expand_v4_readable_dimension_design(readable, impact_analysis=state.analysis_draft)
            return {
                "dimension_attempt": attempt,
                "dimension_draft": draft,
                "dimension_error": None,
                "dimension_error_code": None,
                "dimension_retryable": False,
            }
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            if retryable and attempt < MAX_STAGE_ATTEMPTS:
                _emit_internal_retry(
                    phase="dimension_design",
                    attempt=attempt + 1,
                    validation_code=error_code,
                )
            return {
                "dimension_attempt": attempt,
                "dimension_draft": None,
                "dimension_error": detail,
                "dimension_error_code": error_code,
                "dimension_retryable": retryable,
            }


def validate_v4_dimensions(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if not isinstance(state.dimension_draft, V4DimensionDesignDraft):
        return {}
    if not isinstance(state.analysis_draft, V4EventImpactAnalysisResult):
        return {
            "dimension_error": "validated v4 Event impact analysis is required",
            "dimension_error_code": ErrorCode.INVALID_REQUEST.name,
            "dimension_retryable": False,
        }
    try:
        finalized_design = finalize_v4_dimension_design(
            state.dimension_draft,
            impact_analysis=state.analysis_draft,
            impact_levers=state.impact_levers,
        )
        return {
            "dimension_draft": finalized_design,
            "dimension_error": None,
            "dimension_error_code": None,
            "dimension_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        if retryable and state.dimension_attempt < MAX_STAGE_ATTEMPTS:
            _emit_internal_retry(
                phase="dimension_design",
                attempt=state.dimension_attempt + 1,
                validation_code=error_code,
            )
        return {
            "dimension_error": detail,
            "dimension_error_code": error_code,
            "dimension_retryable": retryable,
        }


def route_after_v4_dimensions(state: V4MultiEventGenerationState) -> str:
    if isinstance(state.dimension_draft, V4DimensionDesignResult) and state.dimension_error is None:
        return "synthesize_v4_scenarios"
    if state.dimension_retryable and state.dimension_attempt < MAX_STAGE_ATTEMPTS:
        return "design_model_lever_dimensions"
    return "fail_generation"


class SynthesizeV4ScenariosNode(BaseNode):
    async def run(
        self,
        state: V4MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if not isinstance(state.analysis_draft, V4EventImpactAnalysisResult):
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="v4 Event impact analysis is required")
        if not isinstance(state.dimension_draft, V4DimensionDesignResult):
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="v4 dimension design is required")
        attempt = state.scenario_attempt + 1
        await _backoff(attempt)
        try:
            warnings = [
                *state.analysis_draft.validation_warnings,
                *state.dimension_draft.validation_warnings,
            ]
            readable: V4ReadableScenarioSynthesisDraft = await invoke_stage_structured_output(
                output_schema=V4ReadableScenarioSynthesisDraft,
                system_prompt=V4_SCENARIO_SYSTEM_PROMPT,
                user_prompt=build_v4_scenario_synthesis_user_prompt(
                    impact_analysis=state.analysis_draft.model_dump(),
                    dimension_definitions=[
                        definition.model_dump() for definition in state.dimension_draft.dimension_definitions
                    ],
                    validation_warnings=[warning.model_dump() for warning in warnings],
                    validation_feedback=_retry_validation_feedback(
                        state.scenario_error,
                        state.scenario_error_code,
                    ),
                ),
                trace_context=runtime.context if runtime is not None else None,
                stage="scenario_synthesis",
            )
            draft = expand_v4_readable_scenario_synthesis(
                readable,
                impact_analysis=state.analysis_draft,
                dimension_design=state.dimension_draft,
            )
            return {
                "scenario_attempt": attempt,
                "scenario_draft": draft,
                "scenario_error": None,
                "scenario_error_code": None,
                "scenario_retryable": False,
                "finalized_result": None,
            }
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            if retryable and attempt < MAX_STAGE_ATTEMPTS:
                _emit_internal_retry(
                    phase="scenario_synthesis",
                    attempt=attempt + 1,
                    validation_code=error_code,
                )
            return {
                "scenario_attempt": attempt,
                "scenario_draft": None,
                "scenario_error": detail,
                "scenario_error_code": error_code,
                "scenario_retryable": retryable,
                "finalized_result": None,
            }


def finalize_v4_scenarios(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if (
        state.scenario_draft is None
        or not isinstance(state.analysis_draft, V4EventImpactAnalysisResult)
        or not isinstance(state.dimension_draft, V4DimensionDesignResult)
    ):
        return {}
    try:
        finalized, coverage = finalize_v4_generation_result(
            state.scenario_draft,
            impact_analysis=state.analysis_draft,
            dimension_design=state.dimension_draft,
            impact_levers=state.impact_levers,
        )
        return {
            "finalized_result": finalized,
            "parameter_coverage": coverage,
            "scenario_error": None,
            "scenario_error_code": None,
            "scenario_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        if retryable and state.scenario_attempt < MAX_STAGE_ATTEMPTS:
            _emit_internal_retry(
                phase="scenario_synthesis",
                attempt=state.scenario_attempt + 1,
                validation_code=error_code,
            )
        return {
            "finalized_result": None,
            "parameter_coverage": None,
            "scenario_error": detail,
            "scenario_error_code": error_code,
            "scenario_retryable": retryable,
        }


def route_after_v4_scenarios(state: V4MultiEventGenerationState) -> str:
    if state.finalized_result is not None and state.parameter_coverage is not None and state.scenario_error is None:
        return "persist_generation"
    if state.scenario_retryable and state.scenario_attempt < MAX_STAGE_ATTEMPTS:
        return "synthesize_v4_scenarios"
    return "fail_generation"


def persist_v4_generation(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if (
        state.scenario_group is None
        or state.finalized_result is None
        or state.parameter_coverage is None
        or state.user_id is None
    ):
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="v4 persistence input is incomplete")
    finalized = state.finalized_result
    analysis = finalized.impact_analysis
    coverage = state.parameter_coverage
    diagnostics = GenerationDiagnostics(
        excluded_candidates=[
            ExcludedCandidate(
                pressure_band=candidate.pressure_band,
                reason_code=candidate.reason_code,
                reason=candidate.reason,
                dimension_values=candidate.dimension_values,
            )
            for candidate in finalized.excluded_scenarios
        ],
        excluded_dimensions=[{"reason": reason} for reason in finalized.excluded_dimensions],
        impact_catalog_version=state.impact_catalog_version,
        covered_dimensions=coverage.covered_dimension_ids,
        uncovered_dimensions=coverage.uncovered_dimension_ids,
        unsupported_levers=coverage.unsupported_lever_codes,
        unsupported_lever_details=coverage.unsupported_lever_details,
        coverage_status=coverage.coverage_status,
        analysis_as_of=state.analysis_as_of,
        event_facts=analysis.event_facts,
        decision_basis=analysis.decision_basis,
        event_exclusions=analysis.event_exclusions,
        impact_paths=analysis.impact_paths,
        path_uncertainties=analysis.path_uncertainties,
        event_interactions=analysis.interactions,
        interaction_uncertainties=analysis.interaction_uncertainties,
        validation_warnings=finalized.validation_warnings,
        scenario_pressure_breakdowns=[
            {
                "title": scenario.title,
                "dimension_values": scenario.dimension_values,
                "common_impact_path_ids": scenario.common_impact_path_ids,
                "applied_interaction_ids": scenario.applied_interaction_ids,
                "pressure_breakdown": scenario.pressure_breakdown.model_dump(),
            }
            for scenario in finalized.scenarios
        ],
    )
    scenarios = [
        {
            **scenario.model_dump(),
            "baseline_yn": "Y" if scenario.baseline_yn else "N",
            "pressure_band": scenario.pressure_band,
            "pressure_rationale": scenario.pressure_rationale,
            "related_markets": [related_market.model_dump() for related_market in scenario.related_markets],
        }
        for scenario in finalized.scenarios
    ]
    saved_group, saved_scenarios = ScenarioGroupService().persist_multi_event_generation(
        scenario_group_id=state.scenario_group.scenario_group_id,
        title=finalized.group_title,
        description=finalized.group_description,
        dimension_definitions=[definition.model_dump() for definition in finalized.dimension_definitions],
        generation_diagnostics=diagnostics.model_dump(),
        scenarios=scenarios,
        user_id=state.user_id,
    )
    return {
        "generation_diagnostics": diagnostics,
        "saved_group": saved_group,
        "saved_scenarios": saved_scenarios,
    }


def fail_v4_generation(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if state.analysis_error:
        detail = f"stage=event_impact_analysis, attempts={state.analysis_attempt}, error={state.analysis_error}"
        error_code = error_code_from_name(state.analysis_error_code)
    elif state.interaction_error:
        detail = (
            f"stage=event_interaction_analysis, attempts={state.interaction_attempt}, error={state.interaction_error}"
        )
        error_code = error_code_from_name(state.interaction_error_code)
    elif state.dimension_error:
        detail = f"stage=dimension_design, attempts={state.dimension_attempt}, error={state.dimension_error}"
        error_code = error_code_from_name(state.dimension_error_code)
    else:
        detail = f"stage=scenario_synthesis, attempts={state.scenario_attempt}, error={state.scenario_error}"
        error_code = error_code_from_name(state.scenario_error_code)
    raise MIBaseError(error_code, detail=detail)
