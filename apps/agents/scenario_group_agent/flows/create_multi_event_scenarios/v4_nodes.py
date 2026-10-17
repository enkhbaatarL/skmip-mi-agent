from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Any, Literal

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
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_group_title import (
    V4GroupTitleFocus,
    events_for_dimensions,
    select_v4_group_title_focus,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDesignDraft,
    V4DimensionDesignResult,
    V4EventImpactAnalysisDraft,
    V4EventImpactAnalysisResult,
    V4GenerationResult,
    V4GroupTitleDraft,
    V4ReadableDimensionDesignDraft,
    V4ReadableEventAnalysisDraft,
    V4ReadableInteractionAnalysisDraft,
    V4ReadableScenarioSynthesisDraft,
    expand_v4_readable_dimension_design,
    expand_v4_readable_event_analysis,
    expand_v4_readable_scenario_synthesis,
    finalize_open_question_pool,
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
    V4_GROUP_TITLE_SYSTEM_PROMPT,
    V4_INTERACTION_SYSTEM_PROMPT,
    V4_SCENARIO_DISTINCT_DRIVER_SYSTEM_PROMPT,
    V4_SCENARIO_SYSTEM_PROMPT,
    build_v4_dimension_design_user_prompt,
    build_v4_event_fact_candidates,
    build_v4_event_impact_analysis_user_prompt,
    build_v4_group_title_user_prompt,
    build_v4_interaction_analysis_user_prompt,
    build_v4_scenario_synthesis_user_prompt,
    event_open_question_budgets,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.agents.scenario_group_agent.utils.scenario_group_summary import (
    build_scenario_group_event_summary,
)
from apps.agents.scenario_group_agent.utils.scenario_group_title import (
    build_fallback_group_title,
    find_events_missing_from_group_title,
    format_group_title_missing_events,
)
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode
from apps.connectors.llm.llm_client import StreamStallLimits
from apps.persistence.event.schema import EventPayload
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload


V4LlmStage = Literal["event_analysis", "interaction", "dimension", "scenario"]


def _stage_timeout_seconds(stage: V4LlmStage) -> float | None:
    """v4 생성 단계별 LLM 호출 총 시간 상한(초)을 설정에서 읽는다. None이면 상한을 두지 않는다."""
    settings = get_settings()
    return {
        "event_analysis": settings.llm_v4_event_analysis_timeout_sec,
        "interaction": settings.llm_v4_interaction_timeout_sec,
        "dimension": settings.llm_v4_dimension_timeout_sec,
        "scenario": settings.llm_v4_scenario_timeout_sec,
    }[stage]


def _stream_stall_limits() -> StreamStallLimits | None:
    """v4 생성 단계의 스트리밍 멈춤 감지 기준을 설정에서 읽는다. 둘 다 없으면 사용하지 않는다."""
    settings = get_settings()
    first_chunk_sec = settings.llm_v4_stream_first_chunk_timeout_sec
    idle_sec = settings.llm_v4_stream_idle_timeout_sec
    if first_chunk_sec is None and idle_sec is None:
        return None
    return StreamStallLimits(first_chunk_sec=first_chunk_sec, idle_sec=idle_sec)


async def _with_stage_timeout[T](awaitable: Awaitable[T], *, stage: V4LlmStage, label: str) -> T:
    """단계 총 시간 상한을 넘긴 LLM 호출을 끊는다. 상한이 없으면 그대로 기다린다.

    TimeoutError는 classify_llm_error에서 재시도 가능 오류로 분류되어 기존 단계 재시도로 이어진다.
    """
    timeout_seconds = _stage_timeout_seconds(stage)
    if timeout_seconds is None:
        return await awaitable
    try:
        async with asyncio.timeout(timeout_seconds):
            return await awaitable
    except TimeoutError as exc:
        raise TimeoutError(f"{label} exceeded {timeout_seconds:g}s") from exc


def _emit_internal_retry(
    *,
    phase: str,
    stage: str,
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
            "stage": stage,
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
    selected_event_count: int = 1,
    open_question_budget: int | None = None,
    parameter_axes: dict[str, str] | None = None,
) -> _EventAnalysisOutcome:
    event_id = int(event.mi_event_id)
    event_payload = event.model_dump()
    fact_candidates = build_v4_event_fact_candidates(event_payload)
    feedback: str | None = None
    for attempt in range(1, MAX_STAGE_ATTEMPTS + 1):
        await _backoff(attempt)
        try:
            readable: V4ReadableEventAnalysisDraft = await _with_stage_timeout(
                invoke_stage_structured_output(
                    output_schema=V4ReadableEventAnalysisDraft,
                    system_prompt=V4_EVENT_IMPACT_SYSTEM_PROMPT,
                    user_prompt=build_v4_event_impact_analysis_user_prompt(
                        events=[event_payload],
                        impact_levers=[lever.model_dump() for lever in impact_levers],
                        catalog_version=catalog_version,
                        analysis_as_of=analysis_as_of,
                        selected_event_count=selected_event_count,
                        open_question_budget=open_question_budget,
                        validation_feedback=feedback,
                        parameter_axes=parameter_axes,
                    ),
                    trace_context=trace_context,
                    stage=f"event_impact_analysis:{event_id}",
                    stall_limits=_stream_stall_limits(),
                    reasoning_effort_override=get_settings().llm_v4_analysis_reasoning_effort,
                ),
                stage="event_analysis",
                label=f"Event {event_id} impact analysis",
            )
            draft = expand_v4_readable_event_analysis(
                readable,
                event_id=event_id,
                observed_at=event.occurred_at,
                fact_candidates=fact_candidates,
                open_question_limit=open_question_budget,
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
                    stage="event_impact_analysis",
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
        question_budgets = event_open_question_budgets(len(state.events))
        outcomes = await asyncio.gather(
            *[
                _analyze_event_with_retries(
                    event=event,
                    impact_levers=state.impact_levers,
                    catalog_version=state.impact_catalog_version,
                    analysis_as_of=state.analysis_as_of,
                    selected_event_count=len(state.events),
                    open_question_budget=question_budget,
                    trace_context=trace_context,
                    parameter_axes=state.impact_parameter_axes,
                )
                for event, question_budget in zip(state.events, question_budgets, strict=True)
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
            validation_warnings=[item for draft in local_drafts for item in draft.validation_warnings],
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
                stage="event_impact_analysis",
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
            draft: V4ReadableInteractionAnalysisDraft = await _with_stage_timeout(
                invoke_stage_structured_output(
                    output_schema=V4ReadableInteractionAnalysisDraft,
                    system_prompt=V4_INTERACTION_SYSTEM_PROMPT,
                    user_prompt=build_v4_interaction_analysis_user_prompt(
                        impact_paths=[path.model_dump() for path in state.analysis_draft.impact_paths],
                        event_question_count=len(state.analysis_draft.path_uncertainties),
                        event_count=len(state.events),
                        events=[event.model_dump() for event in state.events],
                        validation_feedback=state.interaction_error,
                    ),
                    trace_context=runtime.context if runtime is not None else None,
                    stage="event_interaction_analysis",
                    stall_limits=_stream_stall_limits(),
                    reasoning_effort_override=get_settings().llm_v4_analysis_reasoning_effort,
                ),
                stage="interaction",
                label="Event interaction analysis",
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
                    stage="event_interaction_analysis",
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
        merged = merge_v4_readable_interactions(
            state.analysis_draft,
            state.interaction_draft,
            event_count=len(state.events),
        )
        finalized = finalize_v4_event_impact_analysis(
            merged,
            event_ids=[int(event.mi_event_id) for event in state.events],
            impact_levers=state.impact_levers,
        )
        finalized = finalize_open_question_pool(
            finalized,
            target_minimum=3 if len(state.events) == 1 else 7,
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
                stage="event_interaction_analysis",
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
            readable: V4ReadableDimensionDesignDraft = await _with_stage_timeout(
                invoke_stage_structured_output(
                    output_schema=V4ReadableDimensionDesignDraft,
                    system_prompt=V4_DIMENSION_SYSTEM_PROMPT,
                    user_prompt=build_v4_dimension_design_user_prompt(
                        impact_analysis=state.analysis_draft.model_dump(),
                        validation_warnings=[
                            warning.model_dump() for warning in state.analysis_draft.validation_warnings
                        ],
                        analysis_as_of=state.analysis_as_of,
                        validation_feedback=state.dimension_error,
                    ),
                    trace_context=runtime.context if runtime is not None else None,
                    stage="dimension_design",
                    stall_limits=_stream_stall_limits(),
                ),
                stage="dimension",
                label="Dimension design",
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
                    stage="dimension_design",
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
                stage="dimension_design",
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
            readable: V4ReadableScenarioSynthesisDraft = await _with_stage_timeout(
                invoke_stage_structured_output(
                    output_schema=V4ReadableScenarioSynthesisDraft,
                    system_prompt=(
                        V4_SCENARIO_DISTINCT_DRIVER_SYSTEM_PROMPT
                        if state.scenario_synthesis_policy == "distinct_driver"
                        else V4_SCENARIO_SYSTEM_PROMPT
                    ),
                    user_prompt=build_v4_scenario_synthesis_user_prompt(
                        analysis_as_of=state.analysis_as_of,
                        events=[event.model_dump() for event in state.events],
                        impact_analysis=state.analysis_draft.model_dump(),
                        dimension_definitions=[
                            definition.model_dump() for definition in state.dimension_draft.dimension_definitions
                        ],
                        validation_warnings=[warning.model_dump() for warning in warnings],
                        validation_feedback=_retry_validation_feedback(
                            state.scenario_error,
                            state.scenario_error_code,
                        ),
                        policy=state.scenario_synthesis_policy,
                        scenario_count_range=state.scenario_count_range,
                    ),
                    trace_context=runtime.context if runtime is not None else None,
                    stage="scenario_synthesis",
                    stall_limits=_stream_stall_limits(),
                ),
                stage="scenario",
                label="Scenario synthesis",
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
                    stage="scenario_synthesis",
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


def _shortfall_fallback_update(state: V4MultiEventGenerationState) -> dict[str, Any] | None:
    """개수 미달 재시도 전에 보관한 결과로 Scenario 단계를 마칠 상태 갱신값을 만든다."""
    if state.scenario_shortfall_fallback is None or state.scenario_shortfall_fallback_coverage is None:
        return None
    logger.warning(
        "[NODE][finalize_v4_scenarios] SHORTFALL_FALLBACK_USED | "
        f"scenario_count={len(state.scenario_shortfall_fallback.scenarios)}"
    )
    return {
        "finalized_result": state.scenario_shortfall_fallback,
        "parameter_coverage": state.scenario_shortfall_fallback_coverage,
        "scenario_error": None,
        "scenario_error_code": None,
        "scenario_retryable": False,
    }


def finalize_v4_scenarios(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if not isinstance(state.analysis_draft, V4EventImpactAnalysisResult) or not isinstance(
        state.dimension_draft,
        V4DimensionDesignResult,
    ):
        return {}
    if state.scenario_draft is None:
        # 합성 호출이 실패했다. 더 시도할 수 없으면 개수 미달 재시도 전 결과로 마친다.
        can_retry = state.scenario_retryable and state.scenario_attempt < MAX_STAGE_ATTEMPTS
        if not can_retry and (fallback_update := _shortfall_fallback_update(state)) is not None:
            return fallback_update
        return {}
    try:
        finalized, coverage = finalize_v4_generation_result(
            state.scenario_draft,
            # 그룹 제목은 다음 generate_v4_group_title 노드가 확정하며, 여기서는 이벤트 라벨 기반 임시 제목을 둔다.
            group_title=build_fallback_group_title(state.events),
            group_summary=build_scenario_group_event_summary(state.events),
            impact_analysis=state.analysis_draft,
            dimension_design=state.dimension_draft,
            impact_levers=state.impact_levers,
            policy=state.scenario_synthesis_policy,
            scenario_count_range=state.scenario_count_range,
        )
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        can_retry = retryable and state.scenario_attempt < MAX_STAGE_ATTEMPTS
        if not can_retry and (fallback_update := _shortfall_fallback_update(state)) is not None:
            return fallback_update
        if can_retry:
            _emit_internal_retry(
                phase="scenario_synthesis",
                stage="scenario_synthesis",
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

    shortfall = finalized.scenario_count_shortfall
    if (
        shortfall is not None
        and not state.scenario_shortfall_retried
        and state.scenario_attempt < MAX_STAGE_ATTEMPTS
    ):
        # 목표 최소 개수에 못 미치면 합성을 한 번만 다시 시도한다. 재시도 결과가 더 적거나 실패하면
        # 보관한 이 결과를 쓴다.
        target_min, max_count = state.scenario_count_range
        error_code = ErrorCode.LLM_INVALID_RESPONSE_ERROR.name
        _emit_internal_retry(
            phase="scenario_synthesis",
            stage="scenario_synthesis",
            attempt=state.scenario_attempt + 1,
            validation_code=error_code,
        )
        return {
            "finalized_result": None,
            "parameter_coverage": None,
            "scenario_error": (
                f"생성된 Scenario {shortfall.actual}개가 목표 최소 {target_min}개보다 적습니다. "
                f"Dimension 선택지로 근거가 있고 서로 구분되는 조합을 추가해 {target_min}~{max_count}개를 "
                "만드십시오. 만들 수 없는 조합은 excluded에 INSUFFICIENT_EVIDENCE·CONTRADICTION·DUPLICATE 중 "
                "사유와 함께 기록하십시오."
            ),
            "scenario_error_code": error_code,
            "scenario_retryable": True,
            "scenario_shortfall_retried": True,
            "scenario_shortfall_fallback": finalized,
            "scenario_shortfall_fallback_coverage": coverage,
        }
    fallback = state.scenario_shortfall_fallback
    if (
        fallback is not None
        and state.scenario_shortfall_fallback_coverage is not None
        and len(fallback.scenarios) > len(finalized.scenarios)
    ):
        return _shortfall_fallback_update(state) or {}
    return {
        "finalized_result": finalized,
        "parameter_coverage": coverage,
        "scenario_error": None,
        "scenario_error_code": None,
        "scenario_retryable": False,
    }


def route_after_v4_scenarios(state: V4MultiEventGenerationState) -> str:
    if state.finalized_result is not None and state.parameter_coverage is not None and state.scenario_error is None:
        return "generate_v4_group_title"
    if state.scenario_retryable and state.scenario_attempt < MAX_STAGE_ATTEMPTS:
        return "synthesize_v4_scenarios"
    return "fail_generation"


MAX_GROUP_TITLE_ATTEMPTS = 3


async def generate_v4_group_title(
    result: V4GenerationResult,
    *,
    events: list[EventPayload],
    trace_context: TraceContext | None,
) -> str:
    """Title the group by its common premise and the questions that split its scenarios.

    분기 질문의 출처 이벤트가 제목에 드러나지 않으면 제목만 다시 만들고, 끝까지 실패하면 결정적 제목을 쓴다.
    """
    focus: V4GroupTitleFocus = select_v4_group_title_focus(
        result.dimension_definitions,
        [scenario.dimension_values for scenario in result.scenarios],
    )
    focus_dimensions = [*focus.branching, *([focus.premise] if focus.premise else [])]
    focus_events = events_for_dimensions(focus_dimensions, events) or list(events)
    branching_events = events_for_dimensions(focus.branching, events)
    title: str | None = None
    feedback: str | None = None
    for attempt in range(1, MAX_GROUP_TITLE_ATTEMPTS + 1):
        try:
            draft: V4GroupTitleDraft = await invoke_stage_structured_output(
                output_schema=V4GroupTitleDraft,
                system_prompt=V4_GROUP_TITLE_SYSTEM_PROMPT,
                user_prompt=build_v4_group_title_user_prompt(
                    events=[event.model_dump() for event in focus_events],
                    branching_dimensions=[item.model_dump() for item in focus.branching],
                    premise_dimension=focus.premise.model_dump() if focus.premise else None,
                    previous_title=title,
                    validation_feedback=feedback,
                ),
                trace_context=trace_context,
                stage="group_title",
                reasoning_effort_override=get_settings().llm_v4_group_title_reasoning_effort,
                # 짧은 제목 한 줄이라 가벼운 모델을 쓴다(기본 모델은 low에서도 추론 토큰이 수백 개 발생).
                preference=ModelPreference.SPEED,
            )
        except Exception as exc:
            # 제목 생성 실패로 시나리오 생성 전체를 실패시키지 않는다.
            logger.warning(f"[NODE][generate_v4_group_title] FAILED | attempt={attempt} | error={exc!r}")
            break
        title = draft.title
        missing = find_events_missing_from_group_title(title, branching_events)
        if not missing:
            return title
        feedback = format_group_title_missing_events(missing)
        logger.warning(
            f"[NODE][generate_v4_group_title] RETRY | attempt={attempt} | title={title!r} | "
            f"missing_event_ids={[item.mi_event_id for item in missing]}"
        )
    fallback = build_fallback_group_title(focus_events)
    logger.warning(f"[NODE][generate_v4_group_title] FALLBACK | title={title!r} | fallback={fallback!r}")
    return fallback


class GenerateV4GroupTitleNode(BaseNode):
    async def run(
        self,
        state: V4MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.finalized_result is None:
            return {}
        title = await generate_v4_group_title(
            state.finalized_result,
            events=state.events,
            trace_context=runtime.context if runtime is not None else None,
        )
        return {"finalized_result": state.finalized_result.model_copy(update={"group_title": title})}


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
        scenario_synthesis_policy=finalized.scenario_synthesis_policy,
        scenario_count_range=finalized.scenario_count_range,
        scenario_count_shortfall=finalized.scenario_count_shortfall,
        direction_coverage_gaps=list(finalized.direction_coverage_gaps),
        similar_scenario_pairs=finalized.similar_scenario_pairs,
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
        summary=finalized.group_summary,
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
