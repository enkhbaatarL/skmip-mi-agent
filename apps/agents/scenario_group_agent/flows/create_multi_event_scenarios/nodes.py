from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from langgraph.runtime import Runtime
from pydantic import BaseModel, ValidationError

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    GenerationDiagnostics,
    V2GenerationDiagnostics,
    V3GenerationDiagnostics,
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
    V3CompositeDimensionDraft,
    V3DimensionDefinition,
    V3DimensionDesignResult,
    V3DimensionSourceMapping,
    V3DimensionValueDefinition,
    V3MultiEventGenerationResult,
    V3ScenarioSynthesisResult,
    V3SourceReference,
    V3TemplateDimensionSelection,
    V3TemplateDimensionSelectionDraft,
    finalize_generation_result,
    validate_v2_fact_consistency,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import MultiEventGenerationState
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.prompts.multi_event_scenario_generation import (
    V3_ANALYSIS_SYSTEM_PROMPT,
    V3_DIMENSION_SYSTEM_PROMPT,
    V3_SCENARIO_SYSTEM_PROMPT,
    build_dimension_design_user_prompt,
    build_scenario_synthesis_user_prompt,
    build_v3_analysis_design_user_prompt,
    build_v3_dimension_design_user_prompt,
    multi_event_system_prompt,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.common.exceptions.custom import MIBaseError
from apps.common.tracing.context import TraceContext
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload


if TYPE_CHECKING:
    from apps.connectors.llm.llm_client import ReasoningEffortOption, StreamStallLimits


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


def _format_pydantic_validation_error(exc: ValidationError) -> str:
    details: list[str] = []
    for error in exc.errors(include_url=False, include_context=False, include_input=False):
        location = ".".join(str(part) for part in error["loc"]) or "<root>"
        details.append(f"field={location}; message={error['msg']}; type={error['type']}")
    return f"Pydantic validation failed: {' | '.join(details)}"[:600]


def _retry_validation_feedback(detail: str | None, error_code: str | None) -> str | None:
    if error_code != ErrorCode.LLM_INVALID_RESPONSE_ERROR.name:
        return None
    return detail


def classify_llm_error(exc: BaseException) -> tuple[str, str, bool]:
    """Return a bounded detail, domain error name and graph retry decision."""
    chain = _exception_chain(exc)
    validation_error = next((item for item in chain if isinstance(item, ValidationError)), None)
    detail = _format_pydantic_validation_error(validation_error) if validation_error is not None else str(exc)[:600]
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
    stage: str | None = None,
    reasoning_effort_override: ReasoningEffortOption | None = None,
    preference: ModelPreference | None = None,
    stall_limits: StreamStallLimits | None = None,
) -> T:
    from apps.common.configs.config import get_settings
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    stage_trace_context = trace_context
    if trace_context is not None and stage:
        stage_trace_context = trace_context.model_copy(
            update={"tags": {**trace_context.tags, "stage": stage}},
        )
    response = await invoke_llm_structured_output(
        output_schema=output_schema,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
        max_retries=0,
        trace_context=stage_trace_context,
        stream=cfg.llm_stream_enabled,
        reasoning_effort=reasoning_effort_override or cfg.llm_reasoning_effort,
        preference=preference,
        stall_limits=stall_limits,
        log_label=stage,
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
        attempt = state.analysis_attempt + 1
        await _backoff(attempt)
        try:
            result = await invoke_stage_structured_output(
                output_schema=V3AnalysisDesignResult,
                system_prompt=V3_ANALYSIS_SYSTEM_PROMPT,
                user_prompt=build_v3_analysis_design_user_prompt(
                    events=[event.model_dump() for event in state.events],
                    templates=[template.model_dump() for template in state.templates],
                    validation_feedback=state.analysis_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
                stage="event_template_analysis",
            )
            return {
                "analysis_attempt": attempt,
                "analysis_draft": result,
                "event_shocks": [],
                "template_dimension_selections": [],
                "interactions": [],
                "analysis_error": None,
                "analysis_error_code": None,
                "analysis_retryable": False,
            }
        except Exception as exc:
            detail, error_code, retryable = classify_llm_error(exc)
            return {
                "analysis_attempt": attempt,
                "analysis_draft": None,
                "event_shocks": [],
                "template_dimension_selections": [],
                "interactions": [],
                "analysis_error": detail,
                "analysis_error_code": error_code,
                "analysis_retryable": retryable,
            }


class SynthesizeV3DimensionsNode(BaseNode):
    async def run(
        self,
        state: MultiEventGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        attempt = state.dimension_attempt + 1
        await _backoff(attempt)
        try:
            draft = await invoke_stage_structured_output(
                output_schema=V3DimensionDesignResult,
                system_prompt=V3_DIMENSION_SYSTEM_PROMPT,
                user_prompt=build_v3_dimension_design_user_prompt(
                    event_shocks=[shock.model_dump() for shock in state.event_shocks],
                    interactions=[interaction.model_dump() for interaction in state.interactions],
                    template_dimension_selections=[
                        selection.model_dump() for selection in state.template_dimension_selections
                    ],
                    validation_feedback=state.dimension_error,
                ),
                trace_context=runtime.context if runtime is not None else None,
                stage="dimension_design",
            )
            return {
                "dimension_attempt": attempt,
                "dimension_draft": draft,
                "dimension_definitions": [],
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
                stage="dimension_design",
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


def _v3_template_dimensions_by_event(
    state: MultiEventGenerationState,
) -> dict[tuple[int, int, str], dict[str, object]]:
    definitions: dict[tuple[int, int, str], dict[str, object]] = {}
    for event, template in zip(state.events, state.templates, strict=True):
        event_id = int(event.mi_event_id)
        template_id = template.scenario_dimension_template_id
        if template_id is None:
            raise ValueError(f"Template ID is missing for eventId={event_id}")
        if template.event_type_l2_id is not None and int(template.event_type_l2_id) != int(event.event_type_l2_id):
            raise ValueError(f"Template does not belong to the Event type: eventId={event_id}")
        for dimension in template.dimensions:
            definitions[(event_id, int(template_id), dimension.dim_key)] = {
                "label": dimension.label,
                "description": dimension.description,
                "required": dimension.required,
                "value_enums": list(dimension.value_enums),
            }
    return definitions


def _hydrate_v3_template_selections(
    state: MultiEventGenerationState,
    selections: list[V3TemplateDimensionSelectionDraft],
) -> list[V3TemplateDimensionSelection]:
    expected_event_ids = [int(event.mi_event_id) for event in state.events]
    known_event_ids = set(expected_event_ids)
    definitions = _v3_template_dimensions_by_event(state)
    seen: set[tuple[int, int, str]] = set()
    counts = {event_id: 0 for event_id in expected_event_ids}
    hydrated: list[V3TemplateDimensionSelection] = []
    for selection in selections:
        key = (
            int(selection.event_id),
            int(selection.scenario_dimension_template_id),
            selection.dim_key,
        )
        if selection.event_id not in known_event_ids:
            raise ValueError(f"Template selection references an unknown Event: eventId={selection.event_id}")
        if key in seen:
            raise ValueError(f"Template dimension selections contain a duplicate: {key}")
        raw = definitions.get(key)
        if raw is None:
            raise ValueError(
                "Template dimension selection does not belong to the Event Template: "
                f"eventId={selection.event_id}, templateId={selection.scenario_dimension_template_id}, "
                f"dimKey={selection.dim_key}"
            )
        seen.add(key)
        counts[selection.event_id] += 1
        if counts[selection.event_id] > 4:
            raise ValueError(f"Event has more than four Template dimension selections: eventId={selection.event_id}")
        hydrated.append(
            V3TemplateDimensionSelection(
                **selection.model_dump(),
                label=str(raw["label"]),
                description=str(raw["description"]),
                required=bool(raw["required"]),
                value_enums=[str(value) for value in raw["value_enums"]],
            )
        )
    missing = [event_id for event_id in expected_event_ids if counts[event_id] == 0]
    if missing:
        raise ValueError(f"Events without a Template dimension selection: {missing}")
    return hydrated


def _mapping_key(mapping: V3DimensionSourceMapping) -> tuple[int, int, str]:
    return (mapping.event_id, mapping.scenario_dimension_template_id, mapping.dim_key)


def _validate_v3_dimension_draft(
    state: MultiEventGenerationState,
    dimension: V3CompositeDimensionDraft,
    selection_by_key: dict[tuple[int, int, str], V3TemplateDimensionSelection],
) -> V3DimensionDefinition:
    mapping_keys = [_mapping_key(mapping) for mapping in dimension.source_mappings]
    if len(mapping_keys) != len(set(mapping_keys)):
        raise ValueError(f"dimension contains duplicate sourceMappings: {dimension.dimension_id}")
    unknown_mappings = [key for key in mapping_keys if key not in selection_by_key]
    if unknown_mappings:
        raise ValueError(
            "dimension sourceMapping is not present in validated Template selections: "
            f"{dimension.dimension_id}, {unknown_mappings}"
        )

    source_event_ids = list(dict.fromkeys(mapping.event_id for mapping in dimension.source_mappings))
    source_refs = [
        V3SourceReference(
            scenario_dimension_template_id=template_id,
            dim_key=dim_key,
        )
        for template_id, dim_key in dict.fromkeys(
            (mapping.scenario_dimension_template_id, mapping.dim_key) for mapping in dimension.source_mappings
        )
    ]
    enum_mappings = {
        key: set(selection_by_key[key].value_enums) for key in mapping_keys if selection_by_key[key].value_enums
    }
    anchored_mapping_keys: set[tuple[int, int, str]] = set()
    public_values: list[V3DimensionValueDefinition] = []
    value_ids: list[str] = []
    for value in dimension.values:
        value_ids.append(value.value_id)
        anchors_seen: set[tuple[int, int, str, str]] = set()
        valid_anchor_count = 0
        for anchor in value.template_value_anchors:
            mapping_key = (anchor.event_id, anchor.scenario_dimension_template_id, anchor.dim_key)
            anchor_key = (*mapping_key, anchor.template_value)
            if anchor_key in anchors_seen:
                raise ValueError(
                    f"value contains duplicate templateValueAnchors: {dimension.dimension_id}/{value.value_id}"
                )
            anchors_seen.add(anchor_key)
            if mapping_key not in selection_by_key or mapping_key not in set(mapping_keys):
                raise ValueError(
                    "templateValueAnchor is not a selected sourceMapping: "
                    f"{dimension.dimension_id}/{value.value_id}/{mapping_key}"
                )
            allowed_values = set(selection_by_key[mapping_key].value_enums)
            if anchor.template_value not in allowed_values:
                raise ValueError(
                    "templateValueAnchor does not match the source Template enum: "
                    f"{dimension.dimension_id}/{value.value_id}/{anchor.template_value}"
                )
            anchored_mapping_keys.add(mapping_key)
            valid_anchor_count += 1
        if enum_mappings and valid_anchor_count == 0:
            raise ValueError(
                f"each value requires a valid templateValueAnchor: {dimension.dimension_id}/{value.value_id}"
            )
        if not value.description.strip() or not value.derivation_rationale.strip():
            raise ValueError(
                f"new v3 values require description and derivationRationale: {dimension.dimension_id}/{value.value_id}"
            )
        public_values.append(
            V3DimensionValueDefinition(
                value_id=value.value_id,
                label=value.label,
                description=value.description,
                derivation_rationale=value.derivation_rationale,
                pressure_contribution=value.pressure_contribution,
            )
        )
    if len(value_ids) != len(set(value_ids)):
        raise ValueError(f"dimension contains duplicate valueId: {dimension.dimension_id}")
    missing_enum_mappings = set(enum_mappings) - anchored_mapping_keys
    if missing_enum_mappings:
        raise ValueError(
            "enum-bearing sourceMappings must be anchored at least once: "
            f"{dimension.dimension_id}, {sorted(missing_enum_mappings)}"
        )
    return V3DimensionDefinition(
        dimension_id=dimension.dimension_id,
        label=dimension.label,
        description=dimension.description,
        rationale=dimension.rationale,
        source_event_ids=source_event_ids,
        source_refs=source_refs,
        values=public_values,
    )


def _validate_v3_dimensions(
    state: MultiEventGenerationState,
    draft: V3DimensionDesignResult,
) -> list[V3DimensionDefinition]:
    known_event_ids = {int(event.mi_event_id) for event in state.events}
    selection_by_key = {
        (selection.event_id, selection.scenario_dimension_template_id, selection.dim_key): selection
        for selection in state.template_dimension_selections
    }
    dimension_ids = [dimension.dimension_id for dimension in draft.dimension_definitions]
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("dimensionDefinitions contains duplicate dimensionId")
    dimensions = [
        _validate_v3_dimension_draft(state, dimension, selection_by_key) for dimension in draft.dimension_definitions
    ]
    covered_event_ids = {event_id for dimension in dimensions for event_id in dimension.source_event_ids}
    if covered_event_ids != known_event_ids:
        raise ValueError(f"events without a selected dimension: {sorted(known_event_ids - covered_event_ids)}")
    dimension_by_id = {dimension.dimension_id: dimension for dimension in dimensions}
    for interaction in state.interactions:
        event_ids = set(interaction.event_ids)
        if not event_ids <= known_event_ids:
            raise ValueError("interaction references an unknown event")
        if interaction.resolution_dimension_id is not None:
            resolution = dimension_by_id.get(interaction.resolution_dimension_id)
            if resolution is None or not event_ids <= set(resolution.source_event_ids):
                raise ValueError("interaction resolution dimension must reference every interaction event")
        if interaction.relation != "independent" and not any(
            event_ids <= set(dimension.source_event_ids) for dimension in dimensions
        ):
            raise ValueError("non-independent interaction must be represented by one dimension")
        if interaction.relation == "independent":
            missing_independent = sorted(
                event_id
                for event_id in event_ids
                if not any(set(dimension.source_event_ids) == {event_id} for dimension in dimensions)
            )
            if missing_independent:
                raise ValueError(
                    f"independent interaction events require separate single-source dimensions: {missing_independent}"
                )
    return dimensions


def validate_v3_analysis_design(state: MultiEventGenerationState) -> dict[str, Any]:
    if state.analysis_draft is None:
        return {}
    try:
        if not isinstance(state.analysis_draft, V3AnalysisDesignResult):
            raise ValueError("v3 analysis stage returned the wrong schema")
        expected_event_ids = [int(event.mi_event_id) for event in state.events]
        actual_event_ids = [int(shock.event_id) for shock in state.analysis_draft.event_shocks]
        if len(actual_event_ids) != len(set(actual_event_ids)):
            raise ValueError("eventShocks contains duplicate eventId")
        if set(actual_event_ids) != set(expected_event_ids):
            raise ValueError(
                "eventShocks must cover every input Event exactly once: "
                f"expected={expected_event_ids}, actual={actual_event_ids}"
            )
        shock_by_event_id = {int(shock.event_id): shock for shock in state.analysis_draft.event_shocks}
        known_event_ids = set(expected_event_ids)
        for interaction in state.analysis_draft.interactions:
            if not set(interaction.event_ids) <= known_event_ids:
                raise ValueError("interaction references an unknown Event")
        selections = _hydrate_v3_template_selections(
            state,
            state.analysis_draft.template_dimension_selections,
        )
        return {
            "event_shocks": [shock_by_event_id[event_id] for event_id in expected_event_ids],
            "template_dimension_selections": selections,
            "interactions": state.analysis_draft.interactions,
            "analysis_error": None,
            "analysis_error_code": None,
            "analysis_retryable": False,
        }
    except Exception as exc:
        detail, error_code, retryable = classify_llm_error(exc)
        return {
            "event_shocks": [],
            "template_dimension_selections": [],
            "interactions": [],
            "analysis_error": detail,
            "analysis_error_code": error_code,
            "analysis_retryable": retryable,
        }


def route_after_v3_analysis(state: MultiEventGenerationState) -> str:
    if state.template_dimension_selections and state.analysis_error is None:
        return "synthesize_v3_dimensions"
    if state.analysis_retryable and state.analysis_attempt < MAX_STAGE_ATTEMPTS:
        return "analyze_v3_events"
    return "fail_generation"


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
            interactions = state.interactions
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
        return "synthesize_v3_dimensions" if state.api_version == "v3" else "generate_dimensions"
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
                    validation_feedback=_retry_validation_feedback(
                        state.scenario_error,
                        state.scenario_error_code,
                    ),
                ),
                trace_context=runtime.context if runtime is not None else None,
                stage="scenario_synthesis",
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
                interactions=state.interactions,
                dimension_definitions=[
                    dimension
                    for dimension in state.dimension_definitions
                    if isinstance(dimension, V3DimensionDefinition)
                ],
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
        diagnostics = V3GenerationDiagnostics(
            excluded_candidates=[candidate.model_dump() for candidate in finalized.excluded_candidates],
            excluded_dimensions=[
                item.model_dump() if hasattr(item, "model_dump") else item for item in finalized.excluded_dimensions
            ],
            event_shocks=finalized.event_shocks,
            event_interactions=finalized.interactions,
            template_dimension_selections=[
                {
                    **selection.model_dump(),
                    "value_enum_examples": selection.value_enums[:3],
                    "used_in_dimension_ids": [
                        dimension.dimension_id
                        for dimension in (
                            state.dimension_draft.dimension_definitions
                            if isinstance(state.dimension_draft, V3DimensionDesignResult)
                            else []
                        )
                        if any(
                            _mapping_key(mapping)
                            == (
                                selection.event_id,
                                selection.scenario_dimension_template_id,
                                selection.dim_key,
                            )
                            for mapping in dimension.source_mappings
                        )
                    ],
                }
                for selection in state.template_dimension_selections
            ],
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
    elif state.analysis_error:
        detail = f"stage=event_template_analysis, attempts={state.analysis_attempt}, error={state.analysis_error}"
        error_code = error_code_from_name(state.analysis_error_code)
    elif state.dimension_error:
        detail = f"stage=dimension_design, attempts={state.dimension_attempt}, error={state.dimension_error}"
        error_code = error_code_from_name(state.dimension_error_code)
    else:
        detail = f"stage=scenario_synthesis, attempts={state.scenario_attempt}, error={state.scenario_error}"
        error_code = error_code_from_name(state.scenario_error_code)
    raise MIBaseError(error_code, detail=detail)
