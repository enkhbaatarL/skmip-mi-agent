from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

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
    V4MultiEventGenerationState,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDesignResult,
    V4GenerationResult,
    V4ScenarioSynthesisResult,
    finalize_v4_dimension_design,
    finalize_v4_generation_result,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    MODEL_LEVER_SYSTEM_PROMPT,
    build_v4_dimension_design_user_prompt,
    build_v4_scenario_synthesis_user_prompt,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext
from apps.common.values.error_codes import ErrorCode


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
                    + "\n현재 단계에서는 모든 Event를 함께 분석해 근거와 불확실성을 dimension에 직접 저장하고 "
                    "Scenario는 생성하지 마십시오."
                ),
                user_prompt=build_v4_dimension_design_user_prompt(
                    events=[event.model_dump() for event in state.events],
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
        finalized_design = finalize_v4_dimension_design(
            state.dimension_draft,
            event_ids=[int(event.mi_event_id) for event in state.events],
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
                    MODEL_LEVER_SYSTEM_PROMPT + "\n현재 단계에서는 검증된 dimension을 변경하지 말고 "
                    "Scenario와 그룹 메타데이터만 생성하십시오."
                ),
                user_prompt=build_v4_scenario_synthesis_user_prompt(
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
            interactions=state.dimension_draft.interactions,
            dimension_definitions=state.dimension_draft.dimension_definitions,
            scenarios=state.scenario_draft.scenarios,
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
        event_interactions=[interaction.model_dump() for interaction in finalized.interactions],
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
    if state.dimension_error:
        detail = f"stage=dimension_design, attempts={state.dimension_attempt}, error={state.dimension_error}"
        error_code = error_code_from_name(state.dimension_error_code)
    else:
        detail = f"stage=scenario_synthesis, attempts={state.scenario_attempt}, error={state.scenario_error}"
        error_code = error_code_from_name(state.scenario_error_code)
    raise MIBaseError(error_code, detail=detail)
