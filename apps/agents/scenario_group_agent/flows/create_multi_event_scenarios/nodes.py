from __future__ import annotations

import asyncio
from typing import Any

from langgraph.runtime import Runtime
from pydantic import BaseModel

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    GenerationDiagnostics,
    V2GenerationDiagnostics,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    EventInteraction,
    V2DimensionDefinition,
    V2DimensionDesignResult,
    V2EventShock,
    V2FinalizedGenerationResult,
    V2MultiEventGenerationResult,
    V2ScenarioSynthesisResult,
    V3AnalysisDesignResult,
    V3DimensionDefinition,
    V3DimensionDesignResult,
    V3MultiEventGenerationResult,
    V3ScenarioSynthesisResult,
    finalize_generation_result,
    validate_v2_fact_consistency,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import MultiEventGenerationState
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.prompts.multi_event_scenario_generation import (
    V3_ANALYSIS_SYSTEM_PROMPT,
    V3_SCENARIO_SYSTEM_PROMPT,
    build_dimension_design_user_prompt,
    build_scenario_synthesis_user_prompt,
    build_v3_analysis_design_user_prompt,
    multi_event_system_prompt,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import ScenarioPipelineTemplate


MAX_STAGE_ATTEMPTS = 3
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504, 529}
_RETRYABLE_KEYWORDS = ("timeout", "timed out", "connection", "overloaded", "rate limit", "gateway")


def _exception_chain(exc: BaseException) -> list[BaseException]:
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def classify_llm_error(exc: BaseException) -> tuple[str, str, bool]:
    """Return a bounded detail, domain error name and graph retry decision."""
    chain = _exception_chain(exc)
    detail = str(exc)[:600]
    if isinstance(exc, MIBaseError):
        error_code = exc.error_code
    elif isinstance(exc, ValueError):
        error_code = ErrorCode.LLM_INVALID_RESPONSE_ERROR
    else:
        error_code = ErrorCode.LLM_INVOCATION_ERROR

    combined = " ".join(f"{item.__class__.__name__}: {item}".lower() for item in chain)
    has_validation_failure = any(isinstance(item, ValueError) for item in chain) or any(
        marker in combined for marker in ("validation error", "structured output", "invalid response")
    )
    if has_validation_failure:
        return detail, ErrorCode.LLM_INVALID_RESPONSE_ERROR.name, True
    if error_code in {ErrorCode.LLM_INVALID_RESPONSE_ERROR, ErrorCode.LLM_RESPONSE_TIMEOUT}:
        return detail, error_code.name, True
    status_codes = {getattr(item, "status_code", None) for item in chain}
    retryable = bool(status_codes & _RETRYABLE_STATUS_CODES) or any(
        keyword in combined for keyword in _RETRYABLE_KEYWORDS
    )
    return detail, error_code.name, retryable


def error_code_from_name(name: str | None) -> ErrorCode:
    if name and name in ErrorCode.__members__:
        return ErrorCode[name]
    return ErrorCode.LLM_INVOCATION_ERROR


async def _backoff(attempt: int) -> None:
    if attempt > 1:
        await asyncio.sleep(float(2 ** (attempt - 2)))


async def invoke_stage_structured_output[T: BaseModel](
    *,
    output_schema: type[T],
    system_prompt: str,
    user_prompt: str,
    trace_context: TraceContext | None,
) -> T:
    from apps.common.configs.config import get_settings
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    response = await invoke_llm_structured_output(
        output_schema=output_schema,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_retries=0,
        trace_context=trace_context,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=cfg.llm_reasoning_effort,
    )
    return response.result


def source_dimensions_by_event(state: MultiEventGenerationState) -> dict[int, dict[str, dict[str, object]]]:
    return {
        int(event.mi_event_id): {
            dimension.dim_key: {
                "required": dimension.required,
                "label": dimension.label,
                "description": dimension.description,
                "event_type_l2_id": int(template.event_type_l2_id or event.event_type_l2_id),
                "scenario_dimension_template_id": template.scenario_dimension_template_id,
                "template_checksum": template.template_checksum,
                "value_enums": list(dimension.value_enums),
            }
            for dimension in template.dimensions
        }
        for event, template in zip(state.events, state.templates, strict=True)
    }


def dispatch_initial_analysis(state: MultiEventGenerationState) -> str:
    if state.api_version == "v3":
        return "analyze_v3_events"
    return "prepare_v2_event_grounding"


def _v2_shock_summary(event: EventPayload) -> str:
    """Build a bounded fact-preserving v2 grounding without an LLM call."""
    parts = [
        str(event.event_title_ko or "").strip(),
        str(event.one_line_summary or "").strip(),
        *[str(item).strip() for item in event.key_bullets[:3]],
    ]
    summary = " | ".join(dict.fromkeys(part for part in parts if part))
    if not summary:
        summary = f"Event {event.mi_event_id}의 입력 사실을 기준으로 시나리오를 설계한다."
    return summary[:300]


def prepare_v2_event_grounding(state: MultiEventGenerationState) -> dict[str, Any]:
    """Preserve input order and facts while removing the per-Event analysis LLM."""
    return {
        "event_shocks": [
            V2EventShock(event_id=int(event.mi_event_id), shock_summary=_v2_shock_summary(event))
            for event in state.events
        ],
    }


class AnalyzeV3EventsNode(BaseNode):
    async def run(
        self,
        state: MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        attempt = state.dimension_attempt + 1
        await _backoff(attempt)
        try:
            result = await invoke_stage_structured_output(
                output_schema=V3AnalysisDesignResult,
                system_prompt=V3_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=build_v3_analysis_design_user_prompt(
                    events=[event.model_dump() for event in state.events],
                    templates=[template.model_dump() for template in state.templates],
                    validation_feedback=state.dimension_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
            )
            return {
                "event_shocks": result.event_shocks,
                "dimension_attempt": attempt,
                "dimension_draft": V3DimensionDesignResult(
                    interactions=result.interactions,
                    dimension_definitions=result.dimension_definitions,
                ),
                "dimension_definitions": [],
                "interactions": [],
                "dimension_error": None,
                "dimension_error_code": None,
                "dimension_retryable": False,
            }
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            return {
                "event_shocks": [],
                "dimension_attempt": attempt,
                "dimension_draft": None,
                "dimension_definitions": [],
                "interactions": [],
                "dimension_error": detail,
                "dimension_error_code": error_code,
                "dimension_retryable": retryable,
            }


class GenerateDimensionsNode(BaseNode):
    async def run(
        self,
        state: MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        attempt = state.dimension_attempt + 1
        await _backoff(attempt)
        try:
            draft = await invoke_stage_structured_output(
                output_schema=V2DimensionDesignResult,
                system_prompt=(
                    multi_event_system_prompt("v2")
                    + "\n현재 단계에서는 검증된 EventShock을 사용해 dimension만 설계하십시오."
                ),
                user_prompt=build_dimension_design_user_prompt(
                    api_version=state.api_version,
                    events=[event.model_dump() for event in state.events],
                    templates=[template.model_dump() for template in state.templates],
                    event_shocks=[shock.model_dump() for shock in state.event_shocks],
                    validation_feedback=state.dimension_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
            )
            return {
                "dimension_attempt": attempt,
                "dimension_draft": draft,
                "dimension_definitions": [],
                "interactions": [],
                "dimension_error": None,
                "dimension_error_code": None,
                "dimension_retryable": False,
            }
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            return {
                "dimension_attempt": attempt,
                "dimension_draft": None,
                "dimension_definitions": [],
                "interactions": [],
                "dimension_error": detail,
                "dimension_error_code": error_code,
                "dimension_retryable": retryable,
            }


def _validate_v2_dimensions(
    state: MultiEventGenerationState,
    draft: V2DimensionDesignResult,
) -> list[V2DimensionDefinition]:
    validate_v2_fact_consistency(
        [shock for shock in state.event_shocks if isinstance(shock, V2EventShock)],
        draft.selected_dimensions,
    )
    definitions = source_dimensions_by_event(state)
    known_event_ids = {int(event.mi_event_id) for event in state.events}
    seen_sources: set[tuple[int, int, str]] = set()
    seen_dimension_ids: set[str] = set()
    hydrated: list[V2DimensionDefinition] = []
    for selected in draft.selected_dimensions:
        source = selected.source_ref
        if source.event_id not in known_event_ids:
            raise ValueError(f"v2 dimension references an unknown event: {selected.dimension_id}")
        raw = definitions.get(source.event_id, {}).get(source.dim_key)
        if raw is None:
            raise ValueError(
                f"v2 sourceRef is not present in the input Template: eventId={source.event_id}, dimKey={source.dim_key}"
            )
        template_id = raw.get("scenario_dimension_template_id")
        if template_id is None or source.scenario_dimension_template_id != int(template_id):
            raise ValueError(
                f"v2 sourceRef Template ID does not match: eventId={source.event_id}, dimKey={source.dim_key}"
            )
        expected_id = f"e{source.event_id}__{source.dim_key}"
        if selected.dimension_id != expected_id:
            raise ValueError(f"v2 dimensionId must be namespaced as {expected_id}")
        source_key = (source.event_id, source.scenario_dimension_template_id, source.dim_key)
        if source_key in seen_sources or selected.dimension_id in seen_dimension_ids:
            raise ValueError(f"v2 dimension selection contains a duplicate: {selected.dimension_id}")
        value_ids = [value.value_id for value in selected.values]
        if len(value_ids) != len(set(value_ids)):
            raise ValueError(f"v2 dimension contains duplicate valueId: {selected.dimension_id}")
        seen_sources.add(source_key)
        seen_dimension_ids.add(selected.dimension_id)
        hydrated.append(
            V2DimensionDefinition(
                dimension_id=selected.dimension_id,
                label=str(raw.get("label") or source.dim_key),
                description=str(raw.get("description") or raw.get("label") or source.dim_key),
                required=bool(raw.get("required", False)),
                selection_criterion=selected.selection_criterion,
                selection_rationale=selected.selection_rationale,
                source_ref=source,
                values=selected.values,
            )
        )
    covered_event_ids = {dimension.source_ref.event_id for dimension in hydrated}
    if covered_event_ids != known_event_ids:
        raise ValueError(f"events without a selected dimension: {sorted(known_event_ids - covered_event_ids)}")
    return hydrated


def _valid_v3_template_refs(
    templates: list[ScenarioPipelineTemplate],
) -> set[tuple[int, str]]:
    return {
        (int(template.scenario_dimension_template_id), dimension.dim_key)
        for template in templates
        if template.scenario_dimension_template_id is not None
        for dimension in template.dimensions
    }


def _validate_v3_dimensions(
    state: MultiEventGenerationState,
    draft: V3DimensionDesignResult,
) -> list[V3DimensionDefinition]:
    known_event_ids = {int(event.mi_event_id) for event in state.events}
    valid_refs = _valid_v3_template_refs(state.templates)
    dimension_ids = [dimension.dimension_id for dimension in draft.dimension_definitions]
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("dimensionDefinitions contains duplicate dimensionId")
    covered_event_ids: set[int] = set()
    for dimension in draft.dimension_definitions:
        source_event_ids = [int(event_id) for event_id in dimension.source_event_ids]
        if len(source_event_ids) != len(set(source_event_ids)):
            raise ValueError(f"dimension contains duplicate sourceEventIds: {dimension.dimension_id}")
        if not set(source_event_ids) <= known_event_ids:
            raise ValueError(f"dimension references an unknown event: {dimension.dimension_id}")
        dimension.source_event_ids = source_event_ids
        covered_event_ids.update(source_event_ids)
        source_refs = [(source.scenario_dimension_template_id, source.dim_key) for source in dimension.source_refs]
        if len(source_refs) != len(set(source_refs)):
            raise ValueError(f"dimension contains duplicate sourceRefs: {dimension.dimension_id}")
        unknown_refs = set(source_refs) - valid_refs
        if unknown_refs:
            raise ValueError(
                "dimension sourceRef is not present in the input Template: "
                f"{dimension.dimension_id}, {sorted(unknown_refs)}"
            )
        value_ids = [value.value_id for value in dimension.values]
        if len(value_ids) != len(set(value_ids)):
            raise ValueError(f"dimension contains duplicate valueId: {dimension.dimension_id}")
    if covered_event_ids != known_event_ids:
        raise ValueError(f"events without a selected dimension: {sorted(known_event_ids - covered_event_ids)}")
    dimension_by_id = {dimension.dimension_id: dimension for dimension in draft.dimension_definitions}
    for interaction in draft.interactions:
        event_ids = set(interaction.event_ids)
        if not event_ids <= known_event_ids:
            raise ValueError("interaction references an unknown event")
        if interaction.resolution_dimension_id is not None:
            resolution = dimension_by_id.get(interaction.resolution_dimension_id)
            if resolution is None or not event_ids <= set(resolution.source_event_ids):
                raise ValueError("interaction resolution dimension must reference every interaction event")
        if interaction.relation != "independent" and not any(
            event_ids <= set(dimension.source_event_ids) for dimension in draft.dimension_definitions
        ):
            raise ValueError("non-independent interaction must be represented by one dimension")
        if interaction.relation == "independent":
            missing_independent = sorted(
                event_id
                for event_id in event_ids
                if not any(set(dimension.source_event_ids) == {event_id} for dimension in draft.dimension_definitions)
            )
            if missing_independent:
                raise ValueError(
                    f"independent interaction events require separate single-source dimensions: {missing_independent}"
                )
    return draft.dimension_definitions


def validate_v3_analysis_design(state: MultiEventGenerationState) -> dict[str, Any]:
    if state.dimension_draft is None:
        return {}
    try:
        if not isinstance(state.dimension_draft, V3DimensionDesignResult):
            raise ValueError("v3 analysis stage returned the wrong schema")
        expected_event_ids = [int(event.mi_event_id) for event in state.events]
        actual_event_ids = [int(shock.event_id) for shock in state.event_shocks]
        if len(actual_event_ids) != len(set(actual_event_ids)):
            raise ValueError("eventShocks contains duplicate eventId")
        if set(actual_event_ids) != set(expected_event_ids):
            raise ValueError(
                "eventShocks must cover every input Event exactly once: "
                f"expected={expected_event_ids}, actual={actual_event_ids}"
            )
        shock_by_event_id = {int(shock.event_id): shock for shock in state.event_shocks}
        dimensions = _validate_v3_dimensions(state, state.dimension_draft)
        return {
            "event_shocks": [shock_by_event_id[event_id] for event_id in expected_event_ids],
            "dimension_definitions": dimensions,
            "interactions": state.dimension_draft.interactions,
            "dimension_error": None,
            "dimension_error_code": None,
            "dimension_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        return {
            "event_shocks": [],
            "dimension_definitions": [],
            "interactions": [],
            "dimension_error": detail,
            "dimension_error_code": error_code,
            "dimension_retryable": retryable,
        }


def validate_dimensions(state: MultiEventGenerationState) -> dict[str, Any]:
    if state.dimension_draft is None:
        return {}
    try:
        if state.api_version == "v2":
            if not isinstance(state.dimension_draft, V2DimensionDesignResult):
                raise ValueError("v2 dimension stage returned the wrong schema")
            dimensions: list[V2DimensionDefinition | V3DimensionDefinition] = _validate_v2_dimensions(
                state, state.dimension_draft
            )
            interactions: list[EventInteraction] = []
        else:
            if not isinstance(state.dimension_draft, V3DimensionDesignResult):
                raise ValueError("v3 dimension stage returned the wrong schema")
            dimensions = _validate_v3_dimensions(state, state.dimension_draft)
            interactions = state.dimension_draft.interactions
        return {
            "dimension_definitions": dimensions,
            "interactions": interactions,
            "dimension_error": None,
            "dimension_error_code": None,
            "dimension_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        return {
            "dimension_definitions": [],
            "interactions": [],
            "dimension_error": detail,
            "dimension_error_code": error_code,
            "dimension_retryable": retryable,
        }


def route_after_dimensions(state: MultiEventGenerationState) -> str:
    if state.dimension_definitions and state.dimension_error is None:
        return "generate_scenarios"
    if state.dimension_retryable and state.dimension_attempt < MAX_STAGE_ATTEMPTS:
        return "analyze_v3_events" if state.api_version == "v3" else "generate_dimensions"
    return "fail_generation"


class GenerateScenariosNode(BaseNode):
    async def run(
        self,
        state: MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        attempt = state.scenario_attempt + 1
        await _backoff(attempt)
        schema = V2ScenarioSynthesisResult if state.api_version == "v2" else V3ScenarioSynthesisResult
        try:
            draft = await invoke_stage_structured_output(
                output_schema=schema,
                system_prompt=(
                    V3_SCENARIO_SYSTEM_PROMPT
                    if state.api_version == "v3"
                    else multi_event_system_prompt(state.api_version)
                    + "\n현재 단계에서는 검증된 dimension을 변경하지 말고 Scenario와 그룹 메타데이터만 생성하십시오."
                ),
                user_prompt=build_scenario_synthesis_user_prompt(
                    api_version=state.api_version,
                    event_shocks=[shock.model_dump() for shock in state.event_shocks],
                    dimension_definitions=[dimension.model_dump() for dimension in state.dimension_definitions],
                    interactions=[interaction.model_dump() for interaction in state.interactions],
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


def finalize_scenarios(state: MultiEventGenerationState) -> dict[str, Any]:
    if state.scenario_draft is None:
        return {}
    try:
        if state.api_version == "v2":
            if not isinstance(state.dimension_draft, V2DimensionDesignResult) or not isinstance(
                state.scenario_draft, V2ScenarioSynthesisResult
            ):
                raise ValueError("v2 stage output is incomplete")
            result: V2MultiEventGenerationResult | V3MultiEventGenerationResult = V2MultiEventGenerationResult(
                scenario_group_title=state.scenario_draft.scenario_group_title,
                scenario_group_description=state.scenario_draft.scenario_group_description,
                event_shocks=state.event_shocks,
                selected_dimensions=state.dimension_draft.selected_dimensions,
                scenarios=state.scenario_draft.scenarios,
            )
        else:
            if not isinstance(state.dimension_draft, V3DimensionDesignResult) or not isinstance(
                state.scenario_draft, V3ScenarioSynthesisResult
            ):
                raise ValueError("v3 stage output is incomplete")
            result = V3MultiEventGenerationResult(
                scenario_group_title=state.scenario_draft.scenario_group_title,
                scenario_group_description=state.scenario_draft.scenario_group_description,
                event_shocks=state.event_shocks,
                interactions=state.dimension_draft.interactions,
                dimension_definitions=state.dimension_draft.dimension_definitions,
                scenarios=state.scenario_draft.scenarios,
                excluded_candidates=state.scenario_draft.excluded_candidates,
                excluded_dimensions=[],
            )
        finalized = finalize_generation_result(
            result,
            generation_strategy=state.generation_strategy,
            event_ids=[int(event.mi_event_id) for event in state.events],
            source_dimensions_by_event=source_dimensions_by_event(state),
        )
        return {
            "finalized_result": finalized,
            "scenario_error": None,
            "scenario_error_code": None,
            "scenario_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        return {
            "finalized_result": None,
            "scenario_error": detail,
            "scenario_error_code": error_code,
            "scenario_retryable": retryable,
        }


def route_after_scenarios(state: MultiEventGenerationState) -> str:
    if state.finalized_result is not None and state.scenario_error is None:
        return "persist_generation"
    if state.scenario_retryable and state.scenario_attempt < MAX_STAGE_ATTEMPTS:
        return "generate_scenarios"
    return "fail_generation"


def persist_generation(state: MultiEventGenerationState) -> dict[str, Any]:
    if state.scenario_group is None or state.finalized_result is None or state.user_id is None:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="multi-event persistence input is incomplete")
    finalized = state.finalized_result
    if isinstance(finalized, V2FinalizedGenerationResult):
        diagnostics: V2GenerationDiagnostics | GenerationDiagnostics = V2GenerationDiagnostics(
            event_shocks=finalized.event_shocks,
            unselected_dimension_refs=finalized.unselected_dimension_refs,
            unrepresented_pressure_bands=finalized.unrepresented_pressure_bands,
        )
    else:
        diagnostics = GenerationDiagnostics(
            excluded_candidates=[candidate.model_dump() for candidate in finalized.excluded_candidates],
            excluded_dimensions=[
                item.model_dump() if hasattr(item, "model_dump") else item for item in finalized.excluded_dimensions
            ],
            event_shocks=finalized.event_shocks,
            event_interactions=finalized.interactions,
        )
    saved_group, saved_scenarios = ScenarioGroupService().persist_multi_event_generation(
        scenario_group_id=state.scenario_group.scenario_group_id,
        title=finalized.scenario_group_title,
        description=finalized.scenario_group_description,
        dimension_definitions=[definition.model_dump() for definition in finalized.dimension_definitions],
        generation_diagnostics=diagnostics.model_dump(),
        scenarios=[scenario.model_dump() for scenario in finalized.scenarios],
        user_id=state.user_id,
    )
    return {
        "generation_diagnostics": diagnostics,
        "saved_group": saved_group,
        "saved_scenarios": saved_scenarios,
    }


def fail_generation(state: MultiEventGenerationState) -> dict[str, Any]:
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
