from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from langgraph.runtime import Runtime
from langgraph.types import Send

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    ExcludedCandidate,
    GenerationDiagnostics,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.nodes import (
    MAX_STAGE_ATTEMPTS,
    _backoff,
    classify_llm_error,
    error_code_from_name,
    invoke_stage_structured_output,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import (
    V4EventAnalysisOutcome,
    V4EventAnalysisTask,
    V4MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDesignResult,
    V4EventAnalysisResult,
    V4GenerationResult,
    V4ScenarioSynthesisResult,
    finalize_v4_dimension_design,
    finalize_v4_generation_result,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    MODEL_LEVER_SYSTEM_PROMPT,
    build_v4_dimension_design_user_prompt,
    build_v4_event_analysis_user_prompt,
    build_v4_scenario_synthesis_user_prompt,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import DimensionDefinition, SourceLineage


def dispatch_v4_event_analyses(state: V4MultiEventGenerationState) -> list[Send]:
    return [
        Send(
            "extract_event_facts",
            {"event_task": V4EventAnalysisTask(event=event)},
        )
        for event in state.events
    ]


def _latest_outcomes(
    outcomes: Iterable[V4EventAnalysisOutcome],
) -> dict[int, V4EventAnalysisOutcome]:
    latest: dict[int, V4EventAnalysisOutcome] = {}
    for outcome in outcomes:
        current = latest.get(outcome.event_id)
        if current is None or outcome.attempt >= current.attempt:
            latest[outcome.event_id] = outcome
    return latest


class ExtractEventFactsNode(BaseNode):
    async def run(
        self,
        state: V4MultiEventGenerationState | dict[str, Any],
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        state = V4MultiEventGenerationState.model_validate(state)
        task = state.event_task
        if task is None:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="v4 event analysis task is required")
        await _backoff(task.attempt)
        event_id = int(task.event.mi_event_id)
        try:
            result: V4EventAnalysisResult = await invoke_stage_structured_output(
                output_schema=V4EventAnalysisResult,
                system_prompt=(
                    MODEL_LEVER_SYSTEM_PROMPT
                    + "\n현재 단계에서는 impact lever를 선택하지 말고 입력 Event 하나의 사실만 추출하십시오."
                ),
                user_prompt=build_v4_event_analysis_user_prompt(
                    event=task.event.model_dump(),
                    validation_feedback=task.validation_feedback,
                ),
                trace_context=runtime.context if runtime is not None else None,
            )
            fact_ids = [fact.fact_id for fact in result.event_impact_facts]
            if len(fact_ids) != len(set(fact_ids)):
                raise ValueError(f"v4 Event facts contain duplicate factId: eventId={event_id}")
            if any(int(fact.event_id) != event_id for fact in result.event_impact_facts):
                raise ValueError(f"v4 Event facts must all reference eventId={event_id}")
            if any(fact.common_impact_lever_refs for fact in result.event_impact_facts):
                raise ValueError("v4 Event fact extraction must not select common impact levers")
            outcome = V4EventAnalysisOutcome(
                event_id=event_id,
                attempt=task.attempt,
                event_impact_facts=result.event_impact_facts,
            )
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            outcome = V4EventAnalysisOutcome(
                event_id=event_id,
                attempt=task.attempt,
                error=detail,
                error_code=error_code,
                retryable=retryable,
            )
        return {"event_analysis_outcomes": [outcome]}


def validate_v4_event_analyses(state: V4MultiEventGenerationState) -> dict[str, Any]:
    latest = _latest_outcomes(state.event_analysis_outcomes)
    missing = [int(event.mi_event_id) for event in state.events if int(event.mi_event_id) not in latest]
    if missing:
        return {
            "failed_stage": "event_analysis",
            "terminal_error": f"v4 Event fact results are missing: {missing}",
            "terminal_error_code": ErrorCode.LLM_INVALID_RESPONSE_ERROR.name,
        }
    failures = [latest[int(event.mi_event_id)] for event in state.events if latest[int(event.mi_event_id)].error]
    if failures:
        terminal = next(
            (failure for failure in failures if not failure.retryable or failure.attempt >= MAX_STAGE_ATTEMPTS),
            None,
        )
        return {
            "failed_stage": "event_analysis",
            "terminal_error": (
                f"eventId={terminal.event_id}, attempts={terminal.attempt}, error={terminal.error}"
                if terminal is not None
                else None
            ),
            "terminal_error_code": terminal.error_code if terminal is not None else None,
        }
    fact_ids: set[str] = set()
    ordered_facts = []
    for event in state.events:
        outcome = latest[int(event.mi_event_id)]
        for fact in outcome.event_impact_facts:
            if fact.fact_id in fact_ids:
                return {
                    "failed_stage": "event_analysis",
                    "terminal_error": f"v4 factId must be globally unique: {fact.fact_id}",
                    "terminal_error_code": ErrorCode.LLM_INVALID_RESPONSE_ERROR.name,
                }
            fact_ids.add(fact.fact_id)
            ordered_facts.append(fact)
    return {
        "event_impact_facts": ordered_facts,
        "failed_stage": None,
        "terminal_error": None,
        "terminal_error_code": None,
    }


def route_after_v4_event_analyses(state: V4MultiEventGenerationState) -> str | list[Send]:
    latest = _latest_outcomes(state.event_analysis_outcomes)
    if state.terminal_error and not any(
        outcome.error and outcome.retryable and outcome.attempt < MAX_STAGE_ATTEMPTS for outcome in latest.values()
    ):
        return "fail_generation"
    failures = [latest[int(event.mi_event_id)] for event in state.events if latest[int(event.mi_event_id)].error]
    if not failures:
        return "design_model_lever_dimensions"
    if any(not failure.retryable or failure.attempt >= MAX_STAGE_ATTEMPTS for failure in failures):
        return "fail_generation"
    event_by_id = {int(event.mi_event_id): event for event in state.events}
    return [
        Send(
            "extract_event_facts",
            {
                "event_task": V4EventAnalysisTask(
                    event=event_by_id[failure.event_id],
                    attempt=failure.attempt + 1,
                    validation_feedback=failure.error,
                )
            },
        )
        for failure in failures
    ]


class DesignModelLeverDimensionsNode(BaseNode):
    async def run(
        self,
        state: V4MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        attempt = state.dimension_attempt + 1
        await _backoff(attempt)
        try:
            draft: V4DimensionDesignResult = await invoke_stage_structured_output(
                output_schema=V4DimensionDesignResult,
                system_prompt=(
                    MODEL_LEVER_SYSTEM_PROMPT
                    + "\n현재 단계에서는 검증된 fact를 catalog lever와 dimension에 매핑하고 "
                    "Scenario는 생성하지 마십시오."
                ),
                user_prompt=build_v4_dimension_design_user_prompt(
                    event_impact_facts=[fact.model_dump() for fact in state.event_impact_facts],
                    impact_levers=[lever.model_dump() for lever in state.impact_levers],
                    catalog_version=state.impact_catalog_version,
                    validation_feedback=state.dimension_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
            )
            return {
                "dimension_attempt": attempt,
                "dimension_draft": draft,
                "dimension_error": None,
                "dimension_error_code": None,
                "dimension_retryable": False,
            }
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            return {
                "dimension_attempt": attempt,
                "dimension_draft": None,
                "dimension_error": detail,
                "dimension_error_code": error_code,
                "dimension_retryable": retryable,
            }


def validate_v4_dimensions(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if state.dimension_draft is None:
        return {}
    try:
        finalized_design, hydrated_facts = finalize_v4_dimension_design(
            state.dimension_draft,
            event_impact_facts=state.event_impact_facts,
            event_ids=[int(event.mi_event_id) for event in state.events],
            impact_levers=state.impact_levers,
        )
        return {
            "dimension_draft": finalized_design,
            "event_impact_facts": hydrated_facts,
            "dimension_error": None,
            "dimension_error_code": None,
            "dimension_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        return {
            "dimension_error": detail,
            "dimension_error_code": error_code,
            "dimension_retryable": retryable,
        }


def route_after_v4_dimensions(state: V4MultiEventGenerationState) -> str:
    if state.dimension_draft is not None and state.dimension_error is None:
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
        if state.dimension_draft is None:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="v4 dimension design is required")
        attempt = state.scenario_attempt + 1
        await _backoff(attempt)
        try:
            draft: V4ScenarioSynthesisResult = await invoke_stage_structured_output(
                output_schema=V4ScenarioSynthesisResult,
                system_prompt=(
                    MODEL_LEVER_SYSTEM_PROMPT
                    + "\n현재 단계에서는 검증된 fact와 dimension을 변경하지 말고 "
                    "Scenario와 그룹 메타데이터만 생성하십시오."
                ),
                user_prompt=build_v4_scenario_synthesis_user_prompt(
                    event_impact_facts=[fact.model_dump() for fact in state.event_impact_facts],
                    interactions=[interaction.model_dump() for interaction in state.dimension_draft.interactions],
                    dimension_definitions=[
                        definition.model_dump() for definition in state.dimension_draft.dimension_definitions
                    ],
                    validation_feedback=state.scenario_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
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
            return {
                "scenario_attempt": attempt,
                "scenario_draft": None,
                "scenario_error": detail,
                "scenario_error_code": error_code,
                "scenario_retryable": retryable,
                "finalized_result": None,
            }


def finalize_v4_scenarios(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if state.scenario_draft is None or state.dimension_draft is None:
        return {}
    try:
        result = V4GenerationResult(
            group_title=state.scenario_draft.group_title,
            group_description=state.scenario_draft.group_description,
            event_impact_facts=state.event_impact_facts,
            interactions=state.dimension_draft.interactions,
            dimension_definitions=state.dimension_draft.dimension_definitions,
            scenarios=state.scenario_draft.scenarios,
            event_dimension_coverage=state.dimension_draft.event_dimension_coverage,
            excluded_scenarios=state.scenario_draft.excluded_scenarios,
            excluded_dimensions=state.dimension_draft.excluded_dimensions,
        )
        finalized, coverage = finalize_v4_generation_result(
            result,
            event_ids=[int(event.mi_event_id) for event in state.events],
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
                ]
            }
        )
        for definition in definitions
    ]


def persist_v4_generation(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if (
        state.scenario_group is None
        or state.finalized_result is None
        or state.parameter_coverage is None
        or state.user_id is None
    ):
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="v4 persistence input is incomplete")
    finalized = state.finalized_result
    coverage = state.parameter_coverage
    dimension_definitions = _with_event_lineage(finalized.dimension_definitions, state.events)
    diagnostics = GenerationDiagnostics(
        excluded_candidates=[
            ExcludedCandidate(
                global_pressure_band=candidate.global_pressure_band,
                reason_code=candidate.reason_code,
                reason=candidate.reason,
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
        event_impact_facts=[fact.model_dump() for fact in finalized.event_impact_facts],
        event_interactions=[interaction.model_dump() for interaction in finalized.interactions],
        event_dimension_coverage=finalized.event_dimension_coverage,
    )
    scenarios = [
        {
            **scenario.model_dump(),
            "baseline_yn": "Y" if scenario.baseline_yn else "N",
            "global_pressure_band": scenario.global_pressure_band,
            "global_pressure_rationale": scenario.global_pressure_rationale,
            "related_markets": [related_market.model_dump() for related_market in scenario.related_markets],
        }
        for scenario in finalized.scenarios
    ]
    saved_group, saved_scenarios = ScenarioGroupService().persist_multi_event_generation(
        scenario_group_id=state.scenario_group.scenario_group_id,
        title=finalized.group_title,
        description=finalized.group_description,
        dimension_definitions=[definition.model_dump() for definition in dimension_definitions],
        generation_diagnostics=diagnostics.model_dump(),
        scenarios=scenarios,
        user_id=state.user_id,
    )
    return {
        "generation_diagnostics": diagnostics,
        "saved_group": saved_group,
        "saved_scenarios": saved_scenarios,
        "finalized_result": finalized.model_copy(update={"dimension_definitions": dimension_definitions}),
    }


def fail_v4_generation(state: V4MultiEventGenerationState) -> dict[str, Any]:
    if state.terminal_error:
        detail = state.terminal_error
        error_code = error_code_from_name(state.terminal_error_code)
    elif state.dimension_error:
        detail = f"stage=dimension_design, attempts={state.dimension_attempt}, error={state.dimension_error}"
        error_code = error_code_from_name(state.dimension_error_code)
    else:
        detail = f"stage=scenario_synthesis, attempts={state.scenario_attempt}, error={state.scenario_error}"
        error_code = error_code_from_name(state.scenario_error_code)
    raise MIBaseError(error_code, detail=detail)
