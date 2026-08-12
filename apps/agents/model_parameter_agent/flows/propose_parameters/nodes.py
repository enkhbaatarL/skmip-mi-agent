from __future__ import annotations

from datetime import date
import json
import re
import time
from typing import Any, Optional

from langchain_core.runnables.config import RunnableConfig
from langgraph.runtime import Runtime

from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.agents.model_parameter_agent.prompts.model_parameter_proposal import (
    CANDIDATE_VALIDATION_SYSTEM,
    SLOT_PROPOSAL_SYSTEM,
    VALUE_PROPOSAL_SYSTEM,
)
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMCandidateValidationResponse,
    LLMSlotProposal,
    LLMSlotProposalResponse,
    LLMValueAdjustment,
    LLMValueCell,
    LLMValueProposalResponse,
    ParameterAdjustment,
    ParameterSlotAxis,
    ParameterSlotProposal,
    ParameterValueCell,
    RoutingDecision,
)
from apps.agents.model_parameter_agent.utils.basecase import (
    basecase_slot_axis_names_from_candidate,
    build_basecase_records,
)
from apps.agents.model_parameter_agent.utils.lut import (
    BasecaseIndex,
    EffectiveReference,
    ReferenceLoadPolicy,
    build_basecase_index,
    build_slot_catalog,
    get_lut_catalog,
    resolve_effective_reference,
)
from apps.agents.model_parameter_agent.utils.lut.keys import (
    apply_numeric_precision,
)
from apps.agents.model_parameter_agent.utils.lut.models import (
    CandidateSlotCatalog,
    SlotCatalog,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    ParameterKnowledgeBase,
    get_parameter_knowledge_base_from_resources,
    match_parameter_candidates,
    to_compact_json,
)
from apps.agents.model_parameter_agent.utils.resource_runtime import (
    get_model_parameter_resource_paths,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext, langchain_callbacks_context
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode


TIME_SLOT_AXIS_NAMES = {"Year", "Month", "Period"}
HARD_MAX_PARAMETER_SLOTS = 100
DEFAULT_MAX_TOTAL_SELECTED_SLOTS = 300
DEFAULT_MAX_PROMPT_BYTES = 262_144


def _debug_stage_payload(
    stage: str,
    scenario_id: int,
    payload: dict[str, Any],
) -> None:
    """Log one readable multiline result for a model-parameter processing step."""
    logger.opt(lazy=True).debug(
        f"[model-parameter][summary] stage={stage} scenario_id={scenario_id} payload=\n{{}}",
        lambda: json.dumps(
            payload,
            ensure_ascii=False,
            default=str,
            indent=2,
        ),
    )


def _scenario_event_debug_summary(
    scenario_context: dict[str, Any] | None,
    scenario_id: int,
) -> dict[str, Any]:
    context = scenario_context or {}
    scenario = context.get("scenario") or {}
    scenario_group = context.get("scenario_group") or {}
    event = context.get("event") or {}
    events = context.get("events") or []
    return {
        "scenario": {
            "scenario_id": scenario.get("scenario_id") or scenario_id,
            "scenario_group_id": scenario.get("scenario_group_id"),
            "title": scenario.get("title"),
            "dimension_values": scenario.get("dimension_values") or {},
        },
        "event": {
            "mi_event_id": event.get("mi_event_id") or scenario_group.get("mi_event_id"),
            "event_type_l2_id": (event.get("event_type_l2_id") or scenario_group.get("event_type_l2_id")),
            "title": (event.get("event_title") or event.get("event_title_ko") or event.get("title")),
        },
        "events": [
            {
                "mi_event_id": item.get("mi_event_id"),
                "event_type_l2_id": item.get("event_type_l2_id"),
                "scenario_dimension_template_id": item.get(
                    "scenario_dimension_template_id",
                ),
                "title": (item.get("event_title") or item.get("event_title_ko") or item.get("title")),
            }
            for item in events
            if isinstance(item, dict)
        ],
        "generation_strategy": scenario_group.get("generation_strategy"),
        "parameter_mapping_ready": scenario_group.get(
            "parameter_mapping_ready",
        ),
        "dimension_lineage_count": len(context.get("dimension_lineage") or []),
        "validation_warnings": context.get("validation_warnings") or [],
    }


def _parameter_names(
    candidates: list[dict[str, Any]],
) -> list[str]:
    names: list[str] = []
    for candidate in candidates:
        name = str(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
        ).strip()
        if name and name not in names:
            names.append(name)
    return names


def _parameter_selection_summary(
    candidates: list[dict[str, Any]],
) -> list[dict[str, str]]:
    summaries: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for candidate in candidates:
        parameter_name = str(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
        ).strip()
        raw_mapping_method = str(candidate.get("mapping_method") or "").lower()
        mapping_method = "route" if raw_mapping_method == "routing" else raw_mapping_method
        summary_key = (parameter_name, mapping_method)
        if not parameter_name or summary_key in seen:
            continue
        seen.add(summary_key)
        summaries.append(
            {
                "parameter_name": parameter_name,
                "mapping_method": mapping_method,
            },
        )
    return summaries


def _slot_debug_summary(
    slots: list[Any],
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    parameter_by_candidate = {
        str(candidate.get("candidate_key") or ""): str(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
        )
        for candidate in candidates
    }
    summaries: list[dict[str, Any]] = []
    for raw_slot in slots:
        slot = raw_slot.model_dump() if hasattr(raw_slot, "model_dump") else raw_slot
        candidate_key = str(slot.get("candidate_key") or "")
        summary = {
            "parameter_name": parameter_by_candidate.get(candidate_key) or candidate_key,
            "coordinates": _coordinates_for_selected_slot(slot),
        }
        if slot.get("slot_key") is not None:
            summary["slot_key"] = slot["slot_key"]
        summaries.append(summary)
    return summaries


def _adjustment_debug_summary(
    adjustments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for adjustment in adjustments:
        parameter_name = adjustment.get("parameter_name")
        for cell in adjustment.get("value_grid") or []:
            summaries.append(
                {
                    "parameter_name": parameter_name,
                    "slot": cell.get("coordinates") or {},
                    "value": cell.get("proposed_value"),
                },
            )
    return summaries


def get_settings() -> Any:
    from apps.common.configs.config import get_settings as load_settings

    return load_settings()


def _available_periods_for_prompt(
    candidate: CandidateSlotCatalog,
    periods: list[dict[str, int]],
) -> list[dict[str, Any]]:
    if candidate.time_axes == ("Year", "Month"):
        months_by_year: dict[int, list[int]] = {}
        for period in periods:
            year = int(period["Year"])
            month = int(period["Month"])
            months = months_by_year.setdefault(year, [])
            if month not in months:
                months.append(month)
        return [{"Year": year, "Months": sorted(months)} for year, months in sorted(months_by_year.items())]
    return periods


def _fixed_axis_hierarchy_for_prompt(
    candidate: CandidateSlotCatalog,
    period_group_ids_by_leaf: list[str],
) -> list[dict[str, Any]]:
    if not candidate.non_time_axes:
        return [{"period_group_id": period_group_ids_by_leaf[0]}] if period_group_ids_by_leaf else []

    hierarchy: dict[tuple[str, str], dict[str, Any]] = {}
    for leaf, period_group_id in zip(
        candidate.leaves,
        period_group_ids_by_leaf,
        strict=True,
    ):
        level = hierarchy
        terminal: dict[str, Any] | None = None
        for axis_name in candidate.non_time_axes:
            axis_value = leaf.axes[axis_name]
            value_key = (type(axis_value).__name__, to_compact_json(axis_value))
            terminal = level.setdefault(
                value_key,
                {
                    "axis_value": axis_value,
                    "children": {},
                },
            )
            level = terminal["children"]
        if terminal is not None:
            terminal["period_group_id"] = period_group_id

    def serialize_level(
        nodes_by_value: dict[tuple[str, str], dict[str, Any]],
    ) -> list[dict[str, Any]]:
        serialized: list[dict[str, Any]] = []
        for value_key in sorted(nodes_by_value):
            node = nodes_by_value[value_key]
            item: dict[str, Any] = {"axis_value": node["axis_value"]}
            children = serialize_level(node["children"])
            if children:
                item["children"] = children
            else:
                item["period_group_id"] = node["period_group_id"]
            serialized.append(item)
        return serialized

    return serialize_level(hierarchy)


def _candidate_slot_catalog_for_prompt(
    candidate: CandidateSlotCatalog,
) -> dict[str, Any]:
    period_groups: list[dict[str, Any]] = []
    period_group_id_by_payload: dict[str, str] = {}
    period_group_ids_by_leaf: list[str] = []
    for leaf in candidate.leaves:
        periods = [dict(period.values) for period in leaf.available_periods]
        prompt_periods = _available_periods_for_prompt(candidate, periods)
        period_payload_key = to_compact_json(prompt_periods)
        period_group_id = period_group_id_by_payload.get(period_payload_key)
        if period_group_id is None:
            period_group_id = f"period-group-{len(period_groups) + 1}"
            period_group_id_by_payload[period_payload_key] = period_group_id
            period_groups.append(
                {
                    "period_group_id": period_group_id,
                    "available_periods": prompt_periods,
                },
            )
        period_group_ids_by_leaf.append(period_group_id)

    return {
        "candidate_key": candidate.candidate_key,
        "parameter_name": candidate.parameter_name,
        "key_axes": list(candidate.key_axes),
        "fixed_axis_names": list(candidate.non_time_axes),
        "time_axis_names": list(candidate.time_axes),
        "period_groups": period_groups,
        "fixed_axis_hierarchy": _fixed_axis_hierarchy_for_prompt(
            candidate,
            period_group_ids_by_leaf,
        ),
    }


def _slot_catalog_for_prompt(slot_catalog: SlotCatalog) -> list[dict[str, Any]]:
    return [_candidate_slot_catalog_for_prompt(candidate) for candidate in slot_catalog.candidates]


def _configured_positive_int(
    settings: object,
    field_name: str,
    default: int,
) -> int:
    raw_value = getattr(settings, field_name, default)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int) or raw_value < 1:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=f"{field_name} must be a positive integer: value={raw_value!r}",
        )
    return raw_value


def _prompt_parameter_bytes(
    packet: dict[str, Any],
    *,
    task_field: str,
) -> dict[str, int]:
    bytes_by_parameter: dict[str, int] = {}
    for task in packet.get(task_field) or []:
        parameter = task.get("parameter") or {}
        parameter_name = str(
            parameter.get("parameter_name") or parameter.get("candidate_key") or task.get("dimension_key") or "unknown",
        )
        task_bytes = len(to_compact_json(task).encode("utf-8"))
        bytes_by_parameter[parameter_name] = bytes_by_parameter.get(parameter_name, 0) + task_bytes
    return {parameter_name: bytes_by_parameter[parameter_name] for parameter_name in sorted(bytes_by_parameter)}


def _guard_prompt_bytes(
    packet: dict[str, Any],
    *,
    step: str,
    task_field: str,
    limit: int,
) -> tuple[str, int, dict[str, int]]:
    compact_json = to_compact_json(packet)
    actual_bytes = len(compact_json.encode("utf-8"))
    parameter_bytes = _prompt_parameter_bytes(packet, task_field=task_field)
    if actual_bytes > limit:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(
                f"{step} compact prompt exceeds configured byte limit: "
                f"actual_bytes={actual_bytes}, limit_bytes={limit}, "
                f"parameter_bytes={to_compact_json(parameter_bytes)}"
            ),
        )
    return compact_json, actual_bytes, parameter_bytes


def _guard_total_selected_slots(
    slots: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    stage: str,
    limit: int,
) -> None:
    selected_slots = _selected_parameter_slots(slots)
    if len(selected_slots) <= limit:
        return
    raise MIBaseError(
        ErrorCode.INVALID_REQUEST,
        detail=(
            f"{stage} selected slots exceed the request total limit before Step3: "
            f"actual_slots={len(selected_slots)}, limit_slots={limit}, "
            "parameter_slots="
            f"{to_compact_json(_slot_counts_by_parameter(selected_slots, candidates))}"
        ),
    )


def _effective_reference_to_state(
    reference: EffectiveReference,
    *,
    slot_key: str,
) -> dict[str, Any]:
    return {
        "slot_key": slot_key,
        "candidate_key": reference.candidate_key,
        "parameter_name": reference.parameter_name,
        "axes": dict(reference.axes),
        "metadata": dict(reference.metadata),
        "actual_basecase_value": reference.actual_basecase_value,
        "lut_default_value": reference.lut_default_value,
        "llm_reference_value": reference.llm_reference_value,
        "effective_source": reference.effective_source,
        "basecase_reference_id": reference.basecase_reference_id,
        "lut_reference_id": reference.lut_reference_id,
        "lut_version": reference.lut_version,
        "diagnostics": list(reference.diagnostics),
    }


def load_scenario_context(state: ModelParameterProposalState) -> dict[str, Any]:
    context = ModelParameterService().load_context(state.scenario_id)
    scenario = context.get("scenario") or {}
    kb = _knowledge_base_from_context(state, context)
    logger.info(
        "[model-parameter] loaded scenario context | scenario_id={} title={} dimension_keys={} parameter_count={} mapping_rule_count={}",
        state.scenario_id,
        scenario.get("title"),
        sorted((scenario.get("dimension_values") or {}).keys()),
        len(kb.parameter_definitions),
        len(kb.mapping_rules),
    )
    _debug_stage_payload(
        "load_scenario_context.result",
        state.scenario_id,
        _scenario_event_debug_summary(context, state.scenario_id),
    )
    return {
        "scenario_context": context,
        "parameter_knowledge_base": kb,
        "validation_warnings": [
            *state.validation_warnings,
            *(context.get("validation_warnings") or []),
        ],
    }


def _knowledge_base_from_context(
    _state: ModelParameterProposalState,
    context: dict[str, Any],
) -> ParameterKnowledgeBase:
    resources = context.get("parameter_mapping_resources") or {}
    mapping_rules = resources.get("mapping_rules") or []
    parameter_definitions = resources.get("parameter_definitions") or []
    if not mapping_rules or not parameter_definitions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter mapping resources not loaded from DB",
        )
    resource_paths = get_model_parameter_resource_paths()
    return get_parameter_knowledge_base_from_resources(
        mapping_rows=mapping_rules,
        parameter_rows=parameter_definitions,
        basecase_dir_path=str(resource_paths.basecase_dir),
    )


def resolve_event_type_l2_id(scenario_context: dict[str, Any] | None) -> int | None:
    context = scenario_context or {}
    group = context.get("scenario_group") or {}
    event_type = context.get("event_type") or {}
    for raw in (
        group.get("event_type_l2_id"),
        event_type.get("event_type_l2_id"),
        event_type.get("id"),
    ):
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


def select_parameter_candidates(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.scenario_context:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="scenario_context is required")
    if state.parameter_knowledge_base is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter_knowledge_base is required",
        )
    candidates, non_inputs, warnings = match_parameter_candidates(
        state.parameter_knowledge_base,
        state.scenario_context,
    )
    logger.info(
        "[model-parameter] selected candidate mappings | scenario_id={} candidate_count={} candidate_keys={} non_input_count={} warning_count={}",
        state.scenario_id,
        len(candidates),
        [candidate.get("candidate_key") for candidate in candidates],
        len(non_inputs),
        len(warnings),
    )
    output = {
        "candidate_mappings": candidates,
        "non_input_items": non_inputs,
        "validation_warnings": [*state.validation_warnings, *warnings],
    }
    _debug_stage_payload(
        "select_parameter_candidates.result",
        state.scenario_id,
        {"selected_parameters": _parameter_selection_summary(candidates)},
    )
    return output


async def validate_parameter_candidates(
    state: ModelParameterProposalState,
    runtime: Runtime[TraceContext] | None = None,
    # langgraph가 문자열 annotation "Optional[RunnableConfig]"만 config 주입 대상으로 인식함 (PEP 563 환경)
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    if not state.candidate_mappings:
        output = {
            "candidate_mappings": [],
            "validation_warnings": state.validation_warnings,
        }
        _debug_stage_payload(
            "step1.5.result",
            state.scenario_id,
            {
                "selection_method": "skip_llm",
                "selected_parameters": [],
            },
        )
        return output

    validation_candidates = _merge_v3_routing_candidates_for_validation(
        state.candidate_mappings,
    )
    deterministic_candidates, routing_tasks = _partition_candidate_validation_work(
        validation_candidates,
    )
    selected_routing_candidates: list[dict[str, Any]] = []
    validation_warnings: list[str] = []
    usage: dict[str, Any] | None = None
    llm_call: dict[str, Any] | None = None

    if routing_tasks:
        max_routing_candidates_per_dimension = get_settings().model_parameter_max_routing_candidates_per_dimension
        packet = _build_candidate_validation_prompt_packet(
            state.scenario_context or {},
            routing_tasks,
            state.non_input_items,
        )
        prompt_limit_bytes = _configured_positive_int(
            get_settings(),
            "model_parameter_max_step2_prompt_bytes",
            DEFAULT_MAX_PROMPT_BYTES,
        )
        packet_json, prompt_bytes, parameter_bytes = _guard_prompt_bytes(
            packet,
            step="Step1.5",
            task_field="routing_tasks",
            limit=prompt_limit_bytes,
        )
        messages = [
            {
                "role": "system",
                "content": CANDIDATE_VALIDATION_SYSTEM.format(
                    max_routing_candidates_per_dimension=max_routing_candidates_per_dimension,
                ),
            },
            {
                "role": "user",
                "content": (f"아래 JSON만 근거로 Step1.5 수급모델 routing 후보를 선택하십시오.\n{packet_json}"),
            },
        ]

        llm_started = time.perf_counter()
        try:
            result = await _invoke_structured(
                output_schema=LLMCandidateValidationResponse,
                messages=messages,
                model_name=state.model_name,
                trace_context=runtime.context if runtime is not None else None,
                config=config,
            )
            llm_payload = result.result
            usage = result.usage.model_dump() if result.usage is not None else None
            llm_call = _llm_call_trace(
                step="Step1.5 routing selection",
                model_name=getattr(result, "model", None) or state.model_name,
                elapsed_seconds=time.perf_counter() - llm_started,
                usage=usage,
                success=True,
                prompt_bytes=prompt_bytes,
                prompt_limit_bytes=prompt_limit_bytes,
                parameter_bytes=parameter_bytes,
            )
        except Exception as exc:
            logger.warning(
                "[model-parameter] Step1.5 LLM call failed | scenario_id={} error={}",
                state.scenario_id,
                repr(exc),
            )
            raise

        selected_routing_candidates, validation_warnings = _sanitize_routing_decisions(
            llm_payload.routing_decisions,
            routing_tasks,
            max_candidates_per_dimension=max_routing_candidates_per_dimension,
        )

    selected_candidate_keys = {
        str(candidate.get("candidate_key") or "")
        for candidate in [*deterministic_candidates, *selected_routing_candidates]
    }
    candidates = [
        candidate
        for candidate in validation_candidates
        if str(candidate.get("candidate_key") or "") in selected_candidate_keys
    ]
    merged_candidates, merge_warnings = _merge_candidates_by_parameter(candidates)
    logger.info(
        "[model-parameter] validated candidate mappings | scenario_id={} before_count={} "
        "deterministic_count={} routing_task_count={} after_count={} merged_count={} "
        "selected_candidate_keys={} warning_count={}",
        state.scenario_id,
        len(state.candidate_mappings),
        len(deterministic_candidates),
        len(routing_tasks),
        len(candidates),
        len(merged_candidates),
        [candidate.get("candidate_key") for candidate in merged_candidates],
        len(validation_warnings) + len(merge_warnings),
    )
    output: dict[str, Any] = {
        "candidate_mappings": merged_candidates,
        "validation_warnings": [
            *state.validation_warnings,
            *validation_warnings,
            *merge_warnings,
        ],
    }
    if llm_call is not None:
        output["llm_usage"] = usage
        output["llm_calls"] = [*state.llm_calls, llm_call]
    _debug_stage_payload(
        "step1.5.result",
        state.scenario_id,
        {
            "selection_method": "llm" if llm_call is not None else "skip_llm",
            "selected_parameters": _parameter_names(merged_candidates),
        },
    )
    return output


def load_basecase_samples(state: ModelParameterProposalState) -> dict[str, Any]:
    if state.parameter_knowledge_base is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter_knowledge_base is required",
        )
    cfg = get_settings()
    policy = ReferenceLoadPolicy(
        start_year=cfg.model_parameter_lut_horizon_start_year,
        end_year=cfg.model_parameter_lut_horizon_end_year,
        value_max_decimal_places=(cfg.model_parameter_basecase_value_max_decimal_places),
        value_precision_mode=cfg.model_parameter_basecase_value_precision_mode,
    )
    resource_paths = get_model_parameter_resource_paths()
    registry = resource_paths.lut_registry
    records, warnings = build_basecase_records(
        state.parameter_knowledge_base,
        state.candidate_mappings,
        state.scenario_context or {},
        registry=registry,
    )
    lut_catalog = get_lut_catalog(policy, registry=registry) if cfg.model_parameter_lut_enabled else None
    basecase_index = build_basecase_index(
        records,
        state.candidate_mappings,
        policy=policy,
        registry=registry,
    )
    slot_catalog = build_slot_catalog(basecase_index, lut_catalog)
    counts_by_candidate: dict[str, int] = {}
    for record in records:
        key = str(record.get("candidate_key") or "")
        counts_by_candidate[key] = counts_by_candidate.get(key, 0) + 1
    logger.info(
        "[model-parameter] loaded reference sources | scenario_id={} basecase_record_count={} "
        "counts_by_candidate={} lut_enabled={} lut_version={} slot_leaf_count={} warning_count={}",
        state.scenario_id,
        len(records),
        counts_by_candidate,
        cfg.model_parameter_lut_enabled,
        lut_catalog.version if lut_catalog is not None else None,
        sum(len(candidate.leaves) for candidate in slot_catalog.candidates),
        len(warnings),
    )
    prompt_slot_catalog = _slot_catalog_for_prompt(slot_catalog)
    output = {
        "basecase_index": basecase_index,
        "slot_catalog": prompt_slot_catalog,
        "effective_references": [],
        "slot_candidate_mappings": [],
        "lut_version": lut_catalog.version if lut_catalog is not None else None,
        "resolved_config": {
            "model_parameter_lut_enabled": cfg.model_parameter_lut_enabled,
            "model_parameter_lut_horizon_start_year": policy.start_year,
            "model_parameter_lut_horizon_end_year": policy.end_year,
            "model_parameter_basecase_value_max_decimal_places": (
                cfg.model_parameter_basecase_value_max_decimal_places
            ),
            "model_parameter_basecase_value_precision_mode": (cfg.model_parameter_basecase_value_precision_mode),
            "model_parameter_proposed_value_max_decimal_places": (
                cfg.model_parameter_proposed_value_max_decimal_places
            ),
            "model_parameter_proposed_value_precision_mode": (cfg.model_parameter_proposed_value_precision_mode),
            "model_parameter_max_parameter_slots": cfg.model_parameter_max_parameter_slots,
            "model_parameter_max_value_prompt_basecase_records": (
                cfg.model_parameter_max_value_prompt_basecase_records
            ),
            "model_parameter_max_total_selected_slots": _configured_positive_int(
                cfg,
                "model_parameter_max_total_selected_slots",
                DEFAULT_MAX_TOTAL_SELECTED_SLOTS,
            ),
            "model_parameter_max_step2_prompt_bytes": _configured_positive_int(
                cfg,
                "model_parameter_max_step2_prompt_bytes",
                DEFAULT_MAX_PROMPT_BYTES,
            ),
            "model_parameter_max_step3_prompt_bytes": _configured_positive_int(
                cfg,
                "model_parameter_max_step3_prompt_bytes",
                DEFAULT_MAX_PROMPT_BYTES,
            ),
            "llm_stream_enabled": cfg.llm_stream_enabled,
            "llm_reasoning_effort": cfg.llm_reasoning_effort,
        },
        "validation_warnings": [*state.validation_warnings, *warnings],
    }
    return output


def filter_basecase_records_by_slots(state: ModelParameterProposalState) -> dict[str, Any]:
    if not isinstance(state.basecase_index, BasecaseIndex):
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="BasecaseIndex is required before exact slot validation",
        )

    cfg = get_settings()
    step3_slot_limit = min(
        cfg.model_parameter_max_parameter_slots,
        cfg.model_parameter_max_value_prompt_basecase_records,
        HARD_MAX_PARAMETER_SLOTS,
    )
    policy = state.basecase_index.policy
    resource_paths = get_model_parameter_resource_paths()
    registry = resource_paths.lut_registry
    lut_catalog = (
        get_lut_catalog(policy, registry=registry)
        if bool(state.resolved_config.get("model_parameter_lut_enabled"))
        else None
    )
    effective_references: list[dict[str, Any]] = []
    valid_slots: list[dict[str, Any]] = []
    warnings = list(state.validation_warnings)
    counts_by_candidate: dict[str, int] = {}
    rejected_exact_slot_count = 0
    seen_selected_keys: set[tuple[str, str]] = set()
    truncated_slot_counts: dict[str, int] = {}

    for raw_slot in state.parameter_slots:
        slot = dict(raw_slot)
        candidate_key = str(slot.get("candidate_key") or "")
        coordinates = _coordinates_for_selected_slot(slot)
        expected_axes = state.basecase_index.candidate_key_axes.get(candidate_key)
        provided_axis_names = [
            str(axis.get("axis_name") or "").strip()
            for axis in slot.get("slot_axes") or []
            if str(axis.get("axis_name") or "").strip()
        ]
        schema_matches = (
            expected_axes is not None
            and len(provided_axis_names) == len(expected_axes)
            and set(provided_axis_names) == set(expected_axes)
        )
        if not schema_matches:
            reference = None
            warning = (
                "Step2 selected slot의 axis schema가 canonical business key와 달라 "
                f"제외했습니다: candidate={candidate_key}, expected={list(expected_axes or ())}, "
                f"provided={provided_axis_names}"
            )
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
        else:
            try:
                reference = resolve_effective_reference(
                    candidate_key,
                    coordinates,
                    state.basecase_index,
                    lut_catalog,
                )
            except MIBaseError as exc:
                reference = None
                warning = (
                    "Step2 selected slot의 canonical exact key가 유효하지 않아 제외했습니다: "
                    f"candidate={candidate_key}, coordinates={to_compact_json(coordinates)}, "
                    f"detail={exc}"
                )
                logger.warning("[model-parameter] {}", warning)
                warnings.append(warning)
        if reference is None:
            rejected_exact_slot_count += 1
            warning = (
                "Step2 selected slot이 활성 BasecaseIndex/LutCatalog exact union에 없어 "
                f"제외했습니다: candidate={candidate_key}, coordinates={to_compact_json(coordinates)}"
            )
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue

        selected_key = (
            candidate_key,
            _canonical_coordinate_key(dict(reference.axes)),
        )
        if selected_key in seen_selected_keys:
            rejected_exact_slot_count += 1
            warning = (
                "Step2가 동일한 canonical exact slot을 중복 반환해 후속 항목을 "
                f"제외했습니다: candidate={candidate_key}, coordinates={selected_key[1]}"
            )
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue
        seen_selected_keys.add(selected_key)

        candidate_count = counts_by_candidate.get(candidate_key, 0) + 1
        if candidate_count > step3_slot_limit:
            truncated_slot_counts[candidate_key] = truncated_slot_counts.get(candidate_key, 0) + 1
            continue
        counts_by_candidate[candidate_key] = candidate_count
        canonical_axes = dict(reference.axes)
        slot_key = f"slot-{candidate_count}"
        slot["slot_key"] = slot_key
        slot["slot_axes"] = [
            {
                "axis_name": axis_name,
                "axis_value": axis_value,
            }
            for axis_name, axis_value in canonical_axes.items()
        ]
        valid_slots.append(slot)
        effective_references.append(
            _effective_reference_to_state(reference, slot_key=slot_key),
        )

    for candidate_key, truncated_count in sorted(truncated_slot_counts.items()):
        warning = (
            "Step2의 exact·중복 검증을 통과한 slot이 parameter별 상한을 초과해 "
            f"초과분을 제외했습니다: candidate={candidate_key}, "
            f"limit={step3_slot_limit}, excluded={truncated_count}"
        )
        logger.warning("[model-parameter] {}", warning)
        warnings.append(warning)

    total_slot_limit = _configured_positive_int(
        cfg,
        "model_parameter_max_total_selected_slots",
        DEFAULT_MAX_TOTAL_SELECTED_SLOTS,
    )
    _guard_total_selected_slots(
        valid_slots,
        state.candidate_mappings,
        stage="Step2 exact",
        limit=total_slot_limit,
    )

    valid_candidate_keys = set(counts_by_candidate)
    slot_candidate_mappings = [
        candidate
        for candidate in state.candidate_mappings
        if str(candidate.get("candidate_key") or "") in valid_candidate_keys
    ]
    excluded_candidates = [
        str(
            candidate.get("canonical_parameter_name")
            or candidate.get("parameter_name")
            or candidate.get("candidate_key")
            or "",
        )
        for candidate in state.candidate_mappings
        if str(candidate.get("candidate_key") or "") not in valid_candidate_keys
    ]
    logger.info(
        "[model-parameter] resolved exact selected references | scenario_id={} "
        "selected_reference_count={} counts_by_candidate={} rejected_slot_count={} "
        "excluded_parameters={}",
        state.scenario_id,
        len(effective_references),
        counts_by_candidate,
        rejected_exact_slot_count,
        excluded_candidates,
    )
    output = {
        "parameter_slots": valid_slots,
        "slot_candidate_mappings": slot_candidate_mappings,
        "effective_references": effective_references,
        "validation_warnings": warnings,
    }
    return output


def finalize_empty_parameter_values(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        reason = (
            "Step1/Step1.5 candidate 결과가 없어 Step2 slot proposal 및 Step3 value proposal LLM 호출을 생략했습니다."
        )
    else:
        reason = "Step2 selected slot이 없어 Step3 value proposal LLM 호출을 생략했습니다."
    logger.info(
        "[model-parameter] finalized empty parameter values | scenario_id={} candidate_count={} reason={}",
        state.scenario_id,
        len(state.candidate_mappings),
        reason,
    )
    output = {
        "parameter_adjustments": _unselected_adjustments_for_missing_slots(
            state.candidate_mappings,
            reason,
        ),
        "validation_warnings": [*state.validation_warnings, reason],
    }
    return output


async def propose_parameter_values(
    state: ModelParameterProposalState,
    runtime: Runtime[TraceContext] | None = None,
    # langgraph가 문자열 annotation "Optional[RunnableConfig]"만 config 주입 대상으로 인식함 (PEP 563 환경)
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    value_candidates = state.slot_candidate_mappings or [
        candidate
        for candidate in state.candidate_mappings
        if str(candidate.get("candidate_key") or "")
        in {str(slot.get("candidate_key") or "") for slot in _selected_parameter_slots(state.parameter_slots)}
    ]
    if not value_candidates:
        output = {
            "parameter_adjustments": [],
            "validation_warnings": [
                *state.validation_warnings,
                "Step2 exact slot이 있는 parameter가 없어 Step3 value 산정을 수행하지 않았습니다.",
            ],
        }
        return output

    selected_slots = _selected_parameter_slots(state.parameter_slots)
    if not selected_slots:
        return finalize_empty_parameter_values(state)

    cfg = get_settings()
    _guard_total_selected_slots(
        selected_slots,
        value_candidates,
        stage="Step3 input",
        limit=_configured_positive_int(
            cfg,
            "model_parameter_max_total_selected_slots",
            DEFAULT_MAX_TOTAL_SELECTED_SLOTS,
        ),
    )

    value_references = state.effective_references
    packet = _build_value_proposal_prompt_packet(
        state.scenario_context or {},
        value_candidates,
        state.parameter_slots,
        value_references,
        state.non_input_items,
    )
    prompt_limit_bytes = _configured_positive_int(
        cfg,
        "model_parameter_max_step3_prompt_bytes",
        DEFAULT_MAX_PROMPT_BYTES,
    )
    packet_json, prompt_bytes, parameter_bytes = _guard_prompt_bytes(
        packet,
        step="Step3",
        task_field="parameter_value_tasks",
        limit=prompt_limit_bytes,
    )
    logger.info(
        "[model-parameter] built compact value prompt | scenario_id={} "
        "candidate_count={} prompt_bytes={} parameter_bytes={}",
        state.scenario_id,
        len(packet["parameter_value_tasks"]),
        prompt_bytes,
        parameter_bytes,
    )
    messages = [
        {"role": "system", "content": VALUE_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (f"아래 JSON만 근거로 Step3 수급모델 parameter slot 값을 제안하십시오.\n{packet_json}"),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMValueProposalResponse,
            messages=messages,
            model_name=state.model_name,
            trace_context=runtime.context if runtime is not None else None,
            config=config,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step3 value proposal",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
            prompt_bytes=prompt_bytes,
            prompt_limit_bytes=prompt_limit_bytes,
            parameter_bytes=parameter_bytes,
        )
    except Exception as exc:
        logger.warning(
            "[model-parameter] Step3 LLM call failed | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        raise

    adjustments, validation_warnings = _sanitize_llm_adjustments(
        llm_payload.parameter_adjustments,
        value_candidates,
        state.parameter_slots,
        value_references,
    )
    selected_adjustments = [adjustment for adjustment in adjustments if adjustment.get("selected", True)]
    logger.info(
        "[model-parameter] proposed parameter values | scenario_id={} adjustment_count={} selected_count={} value_counts_by_parameter={} warning_count={}",
        state.scenario_id,
        len(adjustments),
        len(selected_adjustments),
        _value_counts_by_parameter(selected_adjustments),
        len(validation_warnings),
    )
    output = {
        "parameter_adjustments": adjustments,
        "validation_warnings": [
            *state.validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }
    _debug_stage_payload(
        "step3.result",
        state.scenario_id,
        {"slot_values": _adjustment_debug_summary(adjustments)},
    )
    return output


async def propose_parameter_slots(
    state: ModelParameterProposalState,
    runtime: Runtime[TraceContext] | None = None,
    # langgraph가 문자열 annotation "Optional[RunnableConfig]"만 config 주입 대상으로 인식함 (PEP 563 환경)
    config: Optional[RunnableConfig] = None,  # noqa: UP045
) -> dict[str, Any]:
    if not state.candidate_mappings:
        output = {
            "parameter_slots": [],
            "validation_warnings": state.validation_warnings,
        }
        _debug_stage_payload(
            "step2.result",
            state.scenario_id,
            {"selected_slots": []},
        )
        return output

    slot_catalog = state.slot_catalog
    packet = _build_slot_proposal_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        slot_catalog,
        state.non_input_items,
    )
    cfg = get_settings()
    prompt_limit_bytes = _configured_positive_int(
        cfg,
        "model_parameter_max_step2_prompt_bytes",
        DEFAULT_MAX_PROMPT_BYTES,
    )
    packet_json, prompt_bytes, parameter_bytes = _guard_prompt_bytes(
        packet,
        step="Step2",
        task_field="parameter_slot_tasks",
        limit=prompt_limit_bytes,
    )
    logger.info(
        "[model-parameter] built compact slot catalog prompt | scenario_id={} "
        "candidate_count={} period_group_count={} prompt_bytes={} parameter_bytes={}",
        state.scenario_id,
        len(packet["parameter_slot_tasks"]),
        sum(
            len((task.get("slot_catalog") or {}).get("period_groups") or []) for task in packet["parameter_slot_tasks"]
        ),
        prompt_bytes,
        parameter_bytes,
    )
    messages = [
        {"role": "system", "content": SLOT_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (f"아래 JSON만 근거로 Step2 수급모델 parameter slot 축을 제안하십시오.\n{packet_json}"),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMSlotProposalResponse,
            messages=messages,
            model_name=state.model_name,
            trace_context=runtime.context if runtime is not None else None,
            config=config,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step2 slot proposal",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
            prompt_bytes=prompt_bytes,
            prompt_limit_bytes=prompt_limit_bytes,
            parameter_bytes=parameter_bytes,
        )
    except Exception as exc:
        logger.warning(
            "[model-parameter] Step2 LLM call failed | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        raise

    slots, validation_warnings = _sanitize_llm_slots(
        llm_payload.parameter_slots,
        state.candidate_mappings,
    )
    logger.info(
        "[model-parameter] proposed parameter slots | scenario_id={} slot_count={} "
        "slot_counts_by_parameter={} warning_count={}",
        state.scenario_id,
        len(slots),
        _slot_counts_by_parameter(slots, state.candidate_mappings),
        len(validation_warnings),
    )
    output = {
        "parameter_slots": slots,
        "non_input_items": state.non_input_items,
        "validation_warnings": [
            *state.validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }
    _debug_stage_payload(
        "step2.result",
        state.scenario_id,
        {
            "selected_slots": _slot_debug_summary(
                slots,
                state.candidate_mappings,
            ),
        },
    )
    return output


def _llm_call_trace(
    *,
    step: str,
    model_name: str | None,
    elapsed_seconds: float,
    usage: dict[str, Any] | None,
    success: bool,
    error: str | None = None,
    prompt_bytes: int | None = None,
    prompt_limit_bytes: int | None = None,
    parameter_bytes: dict[str, int] | None = None,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "step": step,
        "success": success,
        "model_name": model_name,
        "elapsed_seconds": round(max(0.0, elapsed_seconds), 3),
    }
    if usage is not None:
        trace["usage"] = usage
    if prompt_bytes is not None:
        trace["prompt_bytes"] = prompt_bytes
    if prompt_limit_bytes is not None:
        trace["prompt_limit_bytes"] = prompt_limit_bytes
    if parameter_bytes is not None:
        trace["parameter_bytes"] = parameter_bytes
    if error:
        trace["error"] = error
    logger.info(
        "[model-parameter] LLM call timing | step={} model_name={} success={} elapsed_seconds={} total_tokens={}",
        step,
        model_name,
        success,
        trace["elapsed_seconds"],
        (usage or {}).get("total_tokens"),
    )
    return trace


def _slot_counts_by_parameter(
    slots: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, int]:
    parameter_by_candidate = {
        str(candidate.get("candidate_key") or ""): str(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "unknown",
        )
        for candidate in candidates
    }
    counts: dict[str, int] = {}
    for slot in slots:
        key = str(slot.get("candidate_key") or "")
        parameter_name = parameter_by_candidate.get(key, key or "unknown")
        counts[parameter_name] = counts.get(parameter_name, 0) + 1
    return counts


def _value_counts_by_parameter(adjustments: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for adjustment in adjustments:
        parameter_name = str(adjustment.get("parameter_name") or "unknown")
        counts[parameter_name] = counts.get(parameter_name, 0) + len(adjustment.get("value_grid") or [])
    return counts


async def _invoke_structured(
    *,
    output_schema: type[Any],
    messages: list[dict[str, str]],
    model_name: str | None,
    trace_context: TraceContext | None = None,
    config: RunnableConfig | None = None,
) -> Any:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    stream = cfg.llm_stream_enabled
    reasoning_effort = cfg.llm_reasoning_effort
    # LangGraph 노드 config의 callbacks를 전파해야 LLM 호출이 그래프 trace의 child span으로 묶임
    callbacks = config.get("callbacks") if isinstance(config, dict) else None
    logger.debug(
        "[model-parameter][llm] trace callbacks | config_type={} callbacks_type={} handlers={}",
        type(config).__name__,
        type(callbacks).__name__,
        [type(h).__name__ for h in getattr(callbacks, "handlers", [])],
    )
    logger.debug(
        "[model-parameter][llm] invoke | output_schema={} model_name={} "
        "stream={} reasoning_effort={} timeout_sec={} connect_timeout_sec={} "
        "max_retries={}",
        output_schema.__name__,
        model_name,
        stream,
        reasoning_effort,
        getattr(cfg, "llm_timeout_sec", None),
        getattr(cfg, "http_connect_timeout", None),
        cfg.llm_max_retries,
    )
    with langchain_callbacks_context(callbacks):
        return await invoke_llm_structured_output(
            output_schema=output_schema,
            messages=messages,
            model_name=model_name,
            preference=ModelPreference.QUALITY,
            temperature=0.0,
            max_retries=cfg.llm_max_retries,
            trace_context=trace_context,
            stream=stream,
            reasoning_effort=reasoning_effort,
        )


def _field_key(value: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(value or "")).lower()


def _append_unique_text(items: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _append_unique_source_dimension(
    items: list[dict[str, Any]],
    value: dict[str, Any],
) -> None:
    key = to_compact_json(value)
    seen = {to_compact_json(item) for item in items}
    if key not in seen:
        items.append(value)


def _column_role_names(raw: Any) -> list[str]:
    names: list[str] = []
    for part in str(raw or "").split(","):
        if ":" not in part:
            continue
        _, role = part.split(":", 1)
        role_name = str(role or "").strip()
        if role_name:
            _append_unique_text(names, role_name)
    return names


def _allowed_slot_axes_field_names(candidate: dict[str, Any]) -> list[str]:
    axis_names = basecase_slot_axis_names_from_candidate(candidate)
    if axis_names:
        return axis_names

    value_field_name = str(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
    )
    value_field_key = _field_key(value_field_name)
    axis_names: list[str] = []
    for role_name in _column_role_names(candidate.get("basecase_column_roles")):
        if _field_key(role_name) == value_field_key:
            continue
        _append_unique_text(axis_names, role_name)

    if str(candidate.get("basecase_read_mode") or "").lower() == "matrix_time_columns":
        for axis_name in ("Year", "Month", "Period"):
            _append_unique_text(axis_names, axis_name)
    return axis_names


def _source_dimension_for_prompt(candidate: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "candidate_key": candidate.get("candidate_key"),
        "dimension_key": (
            candidate.get("scenario_dimension_key")
            or candidate.get("dimension_key")
            or candidate.get("source_dimension_id")
        ),
        "scenario_dimension_key": candidate.get("scenario_dimension_key"),
        "mapping_dimension_key": candidate.get("mapping_dimension_key"),
        "source_dimension_id": candidate.get("source_dimension_id"),
        "source_dimension_label": candidate.get("source_dimension_label"),
        "source_dimension_description": candidate.get(
            "source_dimension_description",
        ),
        "source_dimension_rationale": candidate.get(
            "source_dimension_rationale",
        ),
        "source_dimension_value": candidate.get("source_dimension_value"),
        "source_dimension_value_id": candidate.get(
            "source_dimension_value_id",
        ),
        "source_dimension_value_label": candidate.get(
            "source_dimension_value_label",
        ),
        "value_description": candidate.get("value_description"),
        "derivation_rationale": candidate.get("derivation_rationale"),
        "pressure_contribution": candidate.get("pressure_contribution"),
        "event_type_l2_id": candidate.get("event_type_l2_id"),
        "scenario_dimension_template_id": candidate.get(
            "scenario_dimension_template_id",
        ),
        "source_event_ids": candidate.get("source_event_ids"),
        "source_refs": candidate.get("source_refs"),
        "approved_source_projections": candidate.get(
            "approved_source_projections",
        ),
        "parameter_mapping_ready": candidate.get("parameter_mapping_ready"),
        "is_free_value": candidate.get("is_free_value"),
        "mapping_method": candidate.get("mapping_method"),
        "mapping_comment": candidate.get("mapping_comment"),
    }
    return {key: value for key, value in payload.items() if value is not None}


def _source_dimensions_for_prompt(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    raw = candidate.get("source_dimensions")
    if isinstance(raw, list) and raw:
        return [item for item in raw if isinstance(item, dict)]
    return [_source_dimension_for_prompt(candidate)]


def _source_dimension_key(item: dict[str, Any]) -> str | None:
    key = item.get("dimension_key") or item.get("source_dimension_id")
    if key is None:
        return None
    key_text = str(key).strip()
    return key_text or None


def _candidate_source_dimension_keys(candidates: list[dict[str, Any]]) -> set[str]:
    keys: list[str] = []
    for candidate in candidates:
        for item in _source_dimensions_for_prompt(candidate):
            key = _source_dimension_key(item)
            if key:
                _append_unique_text(keys, key)
    return set(keys)


def _indirect_non_input_dimension_keys(
    non_input_items: list[dict[str, Any]],
) -> set[str]:
    keys: list[str] = []
    for item in non_input_items:
        if str(item.get("mapping_method") or "").lower() != "indirect":
            continue
        key = _source_dimension_key(item)
        if key:
            _append_unique_text(keys, key)
    return set(keys)


def _allowed_prompt_dimension_keys(
    candidates: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]] | None = None,
) -> set[str]:
    keys = _candidate_source_dimension_keys(candidates)
    if non_input_items:
        keys.update(_indirect_non_input_dimension_keys(non_input_items))
    return keys


def _supporting_dimension_for_prompt(item: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "source_dimension_id": item.get("source_dimension_id"),
        "scenario_dimension_key": item.get("scenario_dimension_key"),
        "mapping_dimension_key": item.get("mapping_dimension_key"),
        "source_dimension_label": item.get("source_dimension_label"),
        "source_dimension_value": item.get("source_dimension_value"),
        "value_description": item.get("value_description"),
        "derivation_rationale": item.get("derivation_rationale"),
        "pressure_contribution": item.get("pressure_contribution"),
        "event_type_l2_id": item.get("event_type_l2_id"),
        "source_event_ids": item.get("source_event_ids"),
        "source_refs": item.get("source_refs"),
        "approved_source_projections": item.get(
            "approved_source_projections",
        ),
        "mapping_method": item.get("mapping_method"),
        "reason": item.get("reason"),
    }
    return _drop_none_or_empty(payload)


def _candidate_group_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("model_file") or ""),
        str(candidate.get("model_sheet") or ""),
        str(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
        ),
    )


def _parameter_candidate_key(candidate: dict[str, Any]) -> str:
    event_type_l2_id: Any = candidate.get("event_type_l2_id")
    if str(candidate.get("mapping_strategy") or "").lower() == "v3":
        event_type_l2_id = "v3"
    parts = [
        "parameter",
        _field_key(event_type_l2_id),
        _field_key(candidate.get("model_file")),
        _field_key(candidate.get("model_sheet")),
    ]
    parts.append(
        _field_key(
            candidate.get("canonical_parameter_name") or candidate.get("parameter_name"),
        ),
    )
    return "|".join(parts)


def _merge_candidates_by_parameter(  # noqa: C901
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        groups.setdefault(_candidate_group_key(candidate), []).append(candidate)

    merged_candidates: list[dict[str, Any]] = []
    for group_candidates in groups.values():
        if len(group_candidates) == 1:
            candidate = dict(group_candidates[0])
            original_candidate_key = candidate.get("candidate_key")
            candidate["merged_candidate_keys"] = candidate.get(
                "merged_candidate_keys",
            ) or [original_candidate_key]
            candidate["source_dimensions"] = _source_dimensions_for_prompt(candidate)
            if str(candidate.get("mapping_strategy") or "").lower() == "v3":
                candidate["candidate_key"] = _parameter_candidate_key(candidate)
            merged_candidates.append(candidate)
            continue

        base = dict(group_candidates[0])
        merged_candidate_keys: list[str] = []
        source_dimensions: list[dict[str, Any]] = []
        mapping_methods: list[str] = []
        mapping_comments: list[str] = []
        source_event_ids: list[int] = []
        source_refs: list[dict[str, Any]] = []
        approved_source_projections: list[dict[str, Any]] = []
        for candidate in group_candidates:
            for candidate_key in candidate.get("merged_candidate_keys") or [candidate.get("candidate_key")]:
                _append_unique_text(merged_candidate_keys, candidate_key)
            for source_dimension in _source_dimensions_for_prompt(candidate):
                _append_unique_source_dimension(source_dimensions, source_dimension)
            _append_unique_text(mapping_methods, candidate.get("mapping_method"))
            _append_unique_text(mapping_comments, candidate.get("mapping_comment"))
            for event_id in candidate.get("source_event_ids") or []:
                if event_id not in source_event_ids:
                    source_event_ids.append(event_id)
            for source_ref in candidate.get("source_refs") or []:
                if isinstance(source_ref, dict):
                    _append_unique_source_dimension(source_refs, source_ref)
            for projection in candidate.get("approved_source_projections") or []:
                if isinstance(projection, dict):
                    _append_unique_source_dimension(
                        approved_source_projections,
                        projection,
                    )

        merged_method = mapping_methods[0] if len(mapping_methods) == 1 else "merged"
        base.update(
            {
                "candidate_key": _parameter_candidate_key(base),
                "merged_candidate_keys": merged_candidate_keys,
                "source_dimensions": source_dimensions,
                "source_dimension_id": None,
                "source_dimension_label": None,
                "source_dimension_value": None,
                "dimension_key": None,
                "mapping_method": merged_method,
                "mapping_comment": " ".join(mapping_comments),
                "source_event_ids": source_event_ids,
                "source_refs": source_refs,
                "approved_source_projections": approved_source_projections,
            },
        )
        merged_candidates.append(base)

    return merged_candidates, []


def _routing_candidate_prompt_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "candidate_key": candidate.get("candidate_key"),
            "parameter_name": (candidate.get("canonical_parameter_name") or candidate.get("parameter_name")),
            "parameter_hint": candidate.get("parameter_hint"),
            "semantic_axes": candidate.get("semantic_axes"),
            "scenario_dimension_key": candidate.get(
                "scenario_dimension_key",
            ),
            "mapping_dimension_key": candidate.get(
                "mapping_dimension_key",
            ),
            "event_type_l2_id": candidate.get("event_type_l2_id"),
            "source_event_ids": candidate.get("source_event_ids"),
            "source_refs": candidate.get("source_refs"),
            "approved_source_projections": candidate.get(
                "approved_source_projections",
            ),
            "source_dimensions": _source_dimensions_for_prompt(candidate),
            "mapping_comment": candidate.get("mapping_comment"),
        },
    )


def _partition_candidate_validation_work(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    deterministic: list[dict[str, Any]] = []
    routing_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        mapping_method = str(candidate.get("mapping_method") or "").lower()
        if mapping_method == "direct":
            deterministic.append(candidate)
        elif mapping_method == "routing":
            routing_candidates.append(candidate)

    routing_tasks: list[dict[str, Any]] = []
    for group_candidates in _routing_groups_by_dimension(routing_candidates).values():
        first = group_candidates[0]
        first_source = _source_dimensions_for_prompt(first)[0]
        routing_tasks.append(
            {
                "dimension_key": (
                    first.get("scenario_dimension_key")
                    or first.get("dimension_key")
                    or first.get("source_dimension_id")
                ),
                "dimension_label": (first.get("source_dimension_label") or first_source.get("source_dimension_label")),
                "dimension_value": (first.get("source_dimension_value") or first_source.get("source_dimension_value")),
                "candidates": group_candidates,
            },
        )
    return deterministic, routing_tasks


def _merge_v3_routing_candidates_for_validation(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Collapse one composite dimension's converged routing sources.

    Step1.5 decides whether a parameter is relevant to a composite dimension,
    not whether an arbitrary one of that parameter's sourceRefs survives. Keep
    v1 and direct candidates untouched, while exposing one routing choice with
    the complete source/event union for each v3 dimension and model target.
    """
    routing_groups: dict[
        tuple[str, tuple[str, str, str]],
        list[dict[str, Any]],
    ] = {}
    for candidate in candidates:
        if (
            str(candidate.get("mapping_strategy") or "").lower() == "v3"
            and str(candidate.get("mapping_method") or "").lower() == "routing"
        ):
            composite_key = str(
                candidate.get("scenario_dimension_key")
                or candidate.get("dimension_key")
                or candidate.get("source_dimension_id")
                or "",
            )
            routing_groups.setdefault(
                (composite_key, _candidate_group_key(candidate)),
                [],
            ).append(candidate)

    prepared: list[dict[str, Any]] = []
    emitted_groups: set[tuple[str, tuple[str, str, str]]] = set()
    for candidate in candidates:
        if not (
            str(candidate.get("mapping_strategy") or "").lower() == "v3"
            and str(candidate.get("mapping_method") or "").lower() == "routing"
        ):
            prepared.append(candidate)
            continue
        composite_key = str(
            candidate.get("scenario_dimension_key")
            or candidate.get("dimension_key")
            or candidate.get("source_dimension_id")
            or "",
        )
        group_key = (composite_key, _candidate_group_key(candidate))
        if group_key in emitted_groups:
            continue
        emitted_groups.add(group_key)
        group_candidates = routing_groups[group_key]
        if len(group_candidates) == 1:
            prepared.append(candidate)
            continue
        merged, _ = _merge_candidates_by_parameter(group_candidates)
        merged_candidate = merged[0]
        merged_candidate["candidate_key"] = min(str(item.get("candidate_key") or "") for item in group_candidates)
        merged_candidate["scenario_dimension_key"] = composite_key
        prepared.append(merged_candidate)
    return prepared


def _routing_task_for_prompt(task: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "dimension_key": task.get("dimension_key"),
            "dimension_label": task.get("dimension_label"),
            "dimension_value": task.get("dimension_value"),
            "candidates": [_routing_candidate_prompt_payload(candidate) for candidate in task.get("candidates") or []],
        },
    )


def _build_candidate_validation_prompt_packet(
    scenario_context: dict[str, Any],
    routing_tasks: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    routing_candidates = [
        candidate for task in routing_tasks for candidate in task.get("candidates") or [] if isinstance(candidate, dict)
    ]
    allowed_dimension_keys = _allowed_prompt_dimension_keys(
        routing_candidates,
        non_input_items,
    )
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(
            scenario_context,
            allowed_dimension_keys=allowed_dimension_keys,
        ),
        "routing_tasks": [_routing_task_for_prompt(task) for task in routing_tasks],
    }


def _build_slot_proposal_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
    slot_catalog: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> dict[str, Any]:
    cfg = get_settings()
    max_total_selected_slots = _configured_positive_int(
        cfg,
        "model_parameter_max_total_selected_slots",
        DEFAULT_MAX_TOTAL_SELECTED_SLOTS,
    )
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(
            scenario_context,
            allowed_dimension_keys=_allowed_prompt_dimension_keys(
                candidates,
                non_input_items,
            ),
        ),
        "period_resolution_policy": _compact_period_resolution_policy(),
        "slot_selection_limits": {
            "maxParameterSlots": min(
                cfg.model_parameter_max_parameter_slots,
                HARD_MAX_PARAMETER_SLOTS,
            ),
            "maxTotalSelectedSlots": max_total_selected_slots,
            "applicationScope": (
                "maxParameterSlots applies per parameter task; maxTotalSelectedSlots applies to the whole request"
            ),
            "priority": [
                "scenario/event/dimension과 직접 관련되고 task slot_catalog에 exact 존재하는 slot",
                "LUT-only를 포함하되 active source에 실제 존재하는 slot",
                "최대치를 채우지 말고 관련성이 높은 slot만 선택",
            ],
        },
        "parameter_slot_tasks": _build_parameter_slot_tasks(
            candidates,
            slot_catalog,
            non_input_items,
        ),
    }


def _slot_axis_names(slot_axes: list[dict[str, Any]]) -> list[str]:
    axis_names: list[str] = []
    for axis in slot_axes or []:
        axis_name = axis.get("axis_name")
        if axis_name:
            _append_unique_text(axis_names, axis_name)
    return axis_names


def _filter_dimension_values(
    dimension_values: Any,
    allowed_dimension_keys: set[str] | None,
) -> Any:
    if allowed_dimension_keys is None or not isinstance(dimension_values, dict):
        return dimension_values
    return {key: value for key, value in dimension_values.items() if str(key) in allowed_dimension_keys}


def _filter_dimension_selected(
    dimension_selected: Any,
    allowed_dimension_keys: set[str] | None,
) -> Any:
    if allowed_dimension_keys is None:
        return dimension_selected

    if isinstance(dimension_selected, str):
        return [item for item in re.findall(r"[A-Za-z0-9_]+", dimension_selected) if item in allowed_dimension_keys]

    if not isinstance(dimension_selected, list):
        return dimension_selected

    filtered: list[Any] = []
    for item in dimension_selected:
        if isinstance(item, dict):
            key = (
                item.get("dim_key")
                or item.get("dimension_key")
                or item.get("dimension_id")
                or item.get("dimensionId")
                or item.get("key")
            )
            if key is not None and str(key) in allowed_dimension_keys:
                filtered.append(item)
            continue
        if str(item) in allowed_dimension_keys:
            filtered.append(item)
    return filtered


def _filter_dimension_template(
    dimension_template: Any,
    allowed_dimension_keys: set[str] | None,
) -> Any:
    if allowed_dimension_keys is None or not isinstance(dimension_template, list):
        return dimension_template

    filtered: list[Any] = []
    for item in dimension_template:
        if not isinstance(item, dict):
            continue
        key = (
            item.get("dim_key")
            or item.get("dimension_key")
            or item.get("dimension_id")
            or item.get("dimensionId")
            or item.get("key")
        )
        if key is not None and str(key) in allowed_dimension_keys:
            filtered.append(item)
    return filtered


def _bounded_v3_event_brief(event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("event_type")
    event_type = event_type if isinstance(event_type, dict) else {}
    bullets = event.get("key_bullets")
    tags = event.get("tags")
    detail = str(event.get("detail_analysis") or "")[:1200]
    return _drop_none_or_empty(
        {
            "event_id": event.get("mi_event_id"),
            "event_type_l2_id": event.get("event_type_l2_id"),
            "event_type": _drop_none_or_empty(
                {
                    "level_1_code": event_type.get("level_1_code"),
                    "level_1_label": event_type.get("level_1_label"),
                    "level_2_code": event_type.get("level_2_code"),
                    "level_2_label": event_type.get("level_2_label"),
                },
            ),
            "title": (event.get("event_title_ko") or event.get("event_title") or event.get("title")),
            "one_line_summary": event.get("one_line_summary"),
            "key_bullets": bullets[:5] if isinstance(bullets, list) else [],
            "tags": tags[:8] if isinstance(tags, list) else [],
            "detail_excerpt": detail,
        },
    )


def _scenario_brief_for_value_prompt(
    scenario_context: dict[str, Any],
    *,
    allowed_dimension_keys: set[str] | None = None,
) -> dict[str, Any]:
    scenario = scenario_context.get("scenario") or {}
    scenario_group = scenario_context.get("scenario_group") or {}
    dimension_template = scenario_context.get("dimension_template") or []
    event = scenario_context.get("event") or {}
    events = scenario_context.get("events") or []
    is_v3 = str(scenario_group.get("generation_strategy") or "") == "multi_event_composite_dimensions"
    impact = scenario.get("impact") or {}
    filtered_dimension_values = _filter_dimension_values(
        scenario.get("dimension_values"),
        allowed_dimension_keys,
    )
    filtered_dimension_template = _filter_dimension_template(
        dimension_template,
        allowed_dimension_keys,
    )
    scenario_group_brief = _drop_none_or_empty(
        {
            "title": scenario_group.get("title"),
            "summary": scenario_group.get("summary"),
            "description": scenario_group.get("description"),
            "dimension_selected": _filter_dimension_selected(
                scenario_group.get("dimension_selected"),
                allowed_dimension_keys,
            ),
            "api_version": scenario_group.get("api_version") if is_v3 else None,
            "generation_strategy": (scenario_group.get("generation_strategy") if is_v3 else None),
            "parameter_mapping_ready": (scenario_group.get("parameter_mapping_ready") if is_v3 else None),
        },
    )
    scenario_detail = _drop_none_or_empty(
        {
            "title": scenario.get("title"),
            "narrative": scenario.get("narrative"),
            "dimension_values": filtered_dimension_values,
            "impact_jkm": impact.get("jkm"),
            "impact_ttf": impact.get("ttf"),
            "impact_hh": impact.get("hh"),
        },
    )
    dimension_template_brief = _drop_none_or_empty(
        {
            "template_json": filtered_dimension_template,
        },
    )
    event_brief = _drop_none_or_empty(
        {
            "event_title": event.get("event_title_ko") or event.get("event_title"),
            "one_line_summary": event.get("one_line_summary"),
            "key_bullets_json": event.get("key_bullets"),
            "detail_analysis": event.get("detail_analysis"),
            "tag_json": event.get("tags"),
        },
    )
    brief: dict[str, Any] = {
        "scenario_id": scenario.get("scenario_id"),
        "title": scenario.get("title"),
        "selected_dimensions": _selected_dimensions_for_value_prompt(
            scenario_context,
            allowed_dimension_keys=allowed_dimension_keys,
        ),
        "scenario_group": scenario_group_brief,
        "scenario": scenario_detail,
        "dimension_template": dimension_template_brief,
    }
    if is_v3:
        brief["events"] = [_bounded_v3_event_brief(item) for item in events if isinstance(item, dict)]
    else:
        brief["event"] = event_brief
    return _drop_none_or_empty(brief)


def _selected_dimensions_for_value_prompt(
    scenario_context: dict[str, Any],
    *,
    allowed_dimension_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    scenario = scenario_context.get("scenario") or {}
    scenario_group = scenario_context.get("scenario_group") or {}
    if str(scenario_group.get("generation_strategy") or "") == "multi_event_composite_dimensions":
        selected: list[dict[str, Any]] = []
        for item in scenario_context.get("dimension_lineage") or []:
            if not isinstance(item, dict):
                continue
            dimension_key = str(item.get("scenario_dimension_key") or "")
            if allowed_dimension_keys is not None and dimension_key not in allowed_dimension_keys:
                continue
            selected.append(
                _drop_none_or_empty(
                    {
                        "dimension_key": dimension_key,
                        "dimension_label": item.get("scenario_dimension_label"),
                        "dimension_value": item.get("scenario_dimension_value"),
                        "dimension_value_id": item.get(
                            "scenario_dimension_value_id",
                        ),
                        "dimension_value_label": item.get(
                            "scenario_dimension_value_label",
                        ),
                        "description": item.get("value_description"),
                        "derivation_rationale": item.get(
                            "derivation_rationale",
                        ),
                        "pressure_contribution": item.get(
                            "pressure_contribution",
                        ),
                        "source_event_ids": item.get("source_event_ids"),
                        "source_refs": item.get("source_refs"),
                        "approved_source_projections": item.get(
                            "approved_source_projections",
                        ),
                    },
                ),
            )
        return selected

    dimension_values = _filter_dimension_values(
        scenario.get("dimension_values") or {},
        allowed_dimension_keys,
    )
    if not isinstance(dimension_values, dict):
        return []

    label_by_key: dict[str, Any] = {}
    for item in scenario_context.get("dimension_template") or []:
        if not isinstance(item, dict):
            continue
        key = item.get("dim_key") or item.get("dimension_id") or item.get("dimensionId")
        if key:
            label_by_key[str(key)] = item.get("label") or item.get("label_ko")

    selected: list[dict[str, Any]] = []
    for key, value in dimension_values.items():
        selected.append(
            _drop_none_or_empty(
                {
                    "dimension_key": key,
                    "dimension_label": label_by_key.get(str(key)),
                    "dimension_value": value,
                },
            ),
        )
    return selected


def _drop_none_or_empty(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None and item != "" and item != [] and item != {}}


def _source_dimension_for_value_task(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "dimension_key": (
                item.get("scenario_dimension_key") or item.get("dimension_key") or item.get("source_dimension_id")
            ),
            "scenario_dimension_key": item.get("scenario_dimension_key"),
            "mapping_dimension_key": item.get("mapping_dimension_key"),
            "dimension_label": item.get("source_dimension_label"),
            "dimension_value": item.get("source_dimension_value"),
            "dimension_value_id": item.get("source_dimension_value_id"),
            "dimension_value_label": item.get(
                "source_dimension_value_label",
            ),
            "value_description": item.get("value_description"),
            "derivation_rationale": item.get("derivation_rationale"),
            "pressure_contribution": item.get("pressure_contribution"),
            "event_type_l2_id": item.get("event_type_l2_id"),
            "source_event_ids": item.get("source_event_ids"),
            "source_refs": item.get("source_refs"),
            "approved_source_projections": item.get(
                "approved_source_projections",
            ),
            "parameter_mapping_ready": item.get("parameter_mapping_ready"),
            "mapping_method": item.get("mapping_method"),
            "mapping_comment": item.get("mapping_comment"),
        },
    )


def _supporting_dimension_usage_policy(
    item: dict[str, Any],
    candidate: dict[str, Any],
) -> str:
    reason = str(item.get("reason") or "")
    parameter_terms = [
        candidate.get("canonical_parameter_name"),
        candidate.get("parameter_name"),
    ]
    reason_lower = reason.lower()
    for term in parameter_terms:
        if term and str(term).lower() in reason_lower:
            return "parameter_value_hint"
    return "common_context_only"


def _supporting_dimension_for_value_task(
    item: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    if str(item.get("mapping_method") or "").lower() != "indirect":
        return {}

    return _drop_none_or_empty(
        {
            "dimension_key": (item.get("scenario_dimension_key") or item.get("source_dimension_id")),
            "scenario_dimension_key": item.get("scenario_dimension_key"),
            "mapping_dimension_key": item.get("mapping_dimension_key"),
            "dimension_label": item.get("source_dimension_label"),
            "dimension_value": item.get("source_dimension_value"),
            "value_description": item.get("value_description"),
            "derivation_rationale": item.get("derivation_rationale"),
            "pressure_contribution": item.get("pressure_contribution"),
            "event_type_l2_id": item.get("event_type_l2_id"),
            "source_event_ids": item.get("source_event_ids"),
            "source_refs": item.get("source_refs"),
            "approved_source_projections": item.get(
                "approved_source_projections",
            ),
            "mapping_method": item.get("mapping_method"),
            "usage_policy": _supporting_dimension_usage_policy(item, candidate),
            "reason": item.get("reason"),
        },
    )


def _selection_dimensions_for_task(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    for item in _source_dimensions_for_prompt(candidate):
        dimension = _source_dimension_for_value_task(item)
        if dimension:
            dimensions.append(dimension)
    return dimensions


def _supporting_dimensions_for_task(
    non_input_items: list[dict[str, Any]],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    dimensions: list[dict[str, Any]] = []
    for item in non_input_items:
        dimension = _supporting_dimension_for_value_task(item, candidate)
        if dimension:
            dimensions.append(dimension)
    return dimensions


def _slot_reference_contexts(
    parameter_slots: list[dict[str, Any]],
    reference_records: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    references_by_slot_key = {
        (str(record.get("candidate_key") or ""), str(record.get("slot_key") or "")): record
        for record in reference_records
        if str(record.get("slot_key") or "")
    }
    references_by_coordinate = {
        (
            str(record.get("candidate_key") or ""),
            _canonical_coordinate_key(record.get("axes") or {}),
        ): record
        for record in reference_records
    }
    contexts: dict[str, dict[str, dict[str, Any]]] = {}
    for slot in _assign_slot_keys(parameter_slots):
        candidate_key = str(slot.get("candidate_key") or "")
        slot_key = str(slot.get("slot_key") or "")
        coordinates = _coordinates_for_selected_slot(slot)
        reference = references_by_slot_key.get((candidate_key, slot_key))
        if reference is None:
            reference = references_by_coordinate.get(
                (candidate_key, _canonical_coordinate_key(coordinates)),
            )
        if reference is None:
            logger.warning(
                "[model-parameter] selected slot has no reference and was excluded | "
                "candidate_key={} slot_key={} coordinates={}",
                candidate_key,
                slot_key,
                to_compact_json(coordinates),
            )
            continue
        contexts.setdefault(candidate_key, {})[slot_key] = {
            "slot": slot,
            "reference": reference,
        }
    return contexts


def _slot_for_value_task(
    *,
    slot_key: str,
    slot: dict[str, Any],
    reference: dict[str, Any],
) -> dict[str, Any]:
    return {
        "slot_key": slot_key,
        "coordinates": dict(reference.get("axes") or _coordinates_for_selected_slot(slot)),
        "reference_value": (
            reference.get("llm_reference_value") if "llm_reference_value" in reference else reference.get("value")
        ),
    }


def _compact_period_resolution_policy() -> dict[str, Any]:
    policy = _period_resolution_policy()
    return {
        "current_year": policy.get("current_year"),
        "current_month": policy.get("current_month"),
        "rules": policy.get("rules") or [],
    }


def _parameter_prompt_payload(
    candidate: dict[str, Any],
    *,
    allowed_slot_axes: list[str] | None = None,
) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "candidate_key": candidate.get("candidate_key"),
            "parameter_name": (candidate.get("canonical_parameter_name") or candidate.get("parameter_name")),
            "parameter_hint": candidate.get("parameter_hint"),
            "semantic_axes": candidate.get("semantic_axes"),
            "allowed_slot_axes_field_names": (
                allowed_slot_axes if allowed_slot_axes is not None else _allowed_slot_axes_field_names(candidate)
            ),
        },
    )


def _build_parameter_slot_tasks(
    candidates: list[dict[str, Any]],
    slot_catalog: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    max_parameter_slots = min(
        get_settings().model_parameter_max_parameter_slots,
        HARD_MAX_PARAMETER_SLOTS,
    )
    catalog_by_key = {
        str(candidate_catalog.get("candidate_key") or ""): {
            key: value for key, value in candidate_catalog.items() if key != "candidate_key"
        }
        for candidate_catalog in slot_catalog
    }

    tasks: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        candidate_catalog = catalog_by_key.get(
            candidate_key,
            {
                "parameter_name": (candidate.get("canonical_parameter_name") or candidate.get("parameter_name")),
                "key_axes": _allowed_slot_axes_field_names(candidate),
                "fixed_axis_names": [],
                "time_axis_names": [],
                "period_groups": [],
                "fixed_axis_hierarchy": [],
            },
        )
        task = {
            "parameter": _parameter_prompt_payload(
                candidate,
                allowed_slot_axes=list(candidate_catalog.get("key_axes") or []),
            ),
            "limits": {
                "maxParameterSlots": max_parameter_slots,
                "instruction": "관련된 slot만 선택하며 최대치를 채울 필요는 없음",
            },
            "selection_dimensions": _selection_dimensions_for_task(candidate),
            "supporting_dimensions": _supporting_dimensions_for_task(
                non_input_items,
                candidate,
            ),
            "slot_catalog": candidate_catalog,
        }
        tasks.append(_drop_none_or_empty(task))
    return tasks


def _build_parameter_value_tasks(
    candidates: list[dict[str, Any]],
    parameter_slots: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    slot_contexts = _slot_reference_contexts(parameter_slots, basecase_records)

    tasks: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        candidate_slot_contexts = slot_contexts.get(candidate_key) or {}
        if not candidate_slot_contexts:
            continue
        task = {
            "parameter": _parameter_prompt_payload(candidate),
            "selection_dimensions": _selection_dimensions_for_task(candidate),
            "supporting_dimensions": _supporting_dimensions_for_task(
                non_input_items,
                candidate,
            ),
            "slots": [
                _slot_for_value_task(
                    slot_key=slot_key,
                    slot=context["slot"],
                    reference=context["reference"],
                )
                for slot_key, context in candidate_slot_contexts.items()
            ],
        }
        tasks.append(_drop_none_or_empty(task))
    return tasks


def _build_value_proposal_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
    parameter_slots: list[dict[str, Any]],
    basecase_records: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(
            scenario_context,
            allowed_dimension_keys=_allowed_prompt_dimension_keys(
                candidates,
                non_input_items,
            ),
        ),
        "parameter_value_tasks": _build_parameter_value_tasks(
            candidates,
            parameter_slots,
            basecase_records,
            non_input_items,
        ),
    }


AMBIGUOUS_AXIS_TOKENS = (
    "미정",
    "후보",
    "추정",
    "불명",
    "미상",
    "일부",
    "대체 공급국",
    "확정 불가",
    "unknown",
    "unspecified",
    "not specified",
    "tbd",
    "n/a",
)
MULTI_VALUE_AXIS_MARKERS = (";", "；", " 또는 ", " or ")


def _axis_value_issue(axis_name: Any, axis_value: Any) -> str | None:
    if axis_value is None:
        return "빈 축 값"
    text = str(axis_value).strip()
    if not text:
        return "빈 축 값"
    normalized = " ".join(text.lower().split())
    if "?" in text:
        return "불확실성 표기 포함"
    for token in AMBIGUOUS_AXIS_TOKENS:
        if token in normalized:
            return f"모호한 축 값 포함: {token}"
    for marker in MULTI_VALUE_AXIS_MARKERS:
        if marker in normalized:
            return f"여러 축 값을 하나의 문자열로 결합함: {marker.strip()}"
    axis_name_text = str(axis_name or "").lower()
    if axis_name_text in {"year", "month", "period"} and "향후" in normalized:
        return "기간 표현을 명확한 Year/Month/Period 값으로 변환하지 않음"
    return None


def _slot_axis_issues(slot_axes: list[ParameterSlotAxis]) -> list[str]:
    issues: list[str] = []
    for axis in slot_axes:
        issue = _axis_value_issue(axis.axis_name, axis.axis_value)
        if issue:
            issues.append(f"{axis.axis_name}={axis.axis_value}: {issue}")
    return issues


def _coordinate_issues(coordinates: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    for axis_name, axis_value in coordinates.items():
        issue = _axis_value_issue(axis_name, axis_value)
        if issue:
            issues.append(f"{axis_name}={axis_value}: {issue}")
    period_issue = _year_month_coordinate_issue(coordinates)
    if period_issue:
        issues.append(period_issue)
    return issues


def _int_axis_value(value: Any) -> int | None:
    try:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            return int(float(text))
        return int(value)
    except (TypeError, ValueError):
        return None


def _year_month_coordinate_issue(coordinates: dict[str, Any]) -> str | None:
    year = _int_axis_value(coordinates.get("Year"))
    month = _int_axis_value(coordinates.get("Month"))
    if year is None or month is None:
        return None
    if not 1 <= month <= 12:
        return f"Year/Month 좌표의 Month가 유효하지 않음: {month}"
    return None


def _normalize_axis_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return " ".join(str(value).strip().lower().split())


def _slot_option_value(value: Any) -> Any:
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _is_time_slot_axis(axis_name: str) -> bool:
    return axis_name in TIME_SLOT_AXIS_NAMES


def _new_hierarchy_node(value: Any) -> dict[str, Any]:
    return {"value": value, "children": {}}


def _add_hierarchy_path(root: dict[str, dict[str, Any]], path: list[Any]) -> None:
    if not path:
        return
    display_value = _slot_option_value(path[0])
    key = _normalize_axis_value(display_value)
    node = root.setdefault(key, _new_hierarchy_node(display_value))
    _add_hierarchy_path(node["children"], path[1:])


def _hierarchy_for_prompt(root: dict[str, dict[str, Any]]) -> list[Any]:
    items: list[Any] = []
    for _, node in sorted(root.items(), key=lambda item: str(item[1]["value"])):
        children = _hierarchy_for_prompt(node["children"])
        if children:
            items.append([node["value"], children])
        else:
            items.append(node["value"])
    return items


def _build_basecase_slot_options(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    options: dict[str, dict[str, Any]] = {}
    axis_values_by_candidate: dict[str, dict[str, dict[str, Any]]] = {}
    hierarchy_roots_by_candidate: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        candidate_key = str(record.get("candidate_key") or "")
        option = options.setdefault(
            candidate_key,
            {
                "candidate_key": candidate_key,
                "axis_names": [],
                "axis_values": {},
                "slot_hierarchy_axes": [],
                "slot_hierarchy": [],
            },
        )
        axis_values = axis_values_by_candidate.setdefault(candidate_key, {})
        for axis_name, axis_value in (record.get("axes") or {}).items():
            axis_name_text = str(axis_name)
            if axis_name_text not in option["axis_names"]:
                option["axis_names"].append(axis_name_text)
            if _is_time_slot_axis(axis_name_text):
                values = axis_values.setdefault(axis_name_text, {})
                display_value = _slot_option_value(axis_value)
                values.setdefault(_normalize_axis_value(display_value), display_value)

    for candidate_key, option in options.items():
        non_time_axes = [axis_name for axis_name in option["axis_names"] if not _is_time_slot_axis(axis_name)]
        option["slot_hierarchy_axes"] = non_time_axes
        root = hierarchy_roots_by_candidate.setdefault(candidate_key, {})
        for record in records:
            if str(record.get("candidate_key") or "") != candidate_key:
                continue
            axes = record.get("axes") or {}
            path = [axes.get(axis_name) for axis_name in non_time_axes]
            if path and all(value not in (None, "") for value in path):
                _add_hierarchy_path(root, path)
        option["slot_hierarchy"] = _hierarchy_for_prompt(root)
        axis_values = axis_values_by_candidate.get(candidate_key) or {}
        option["axis_values"] = {
            axis_name: [value for _, value in sorted(values.items(), key=lambda item: str(item[1]))]
            for axis_name, values in axis_values.items()
        }
    return list(options.values())


def _routing_groups_by_dimension(
    candidates: list[dict[str, Any]],
) -> dict[tuple[Any, str], list[dict[str, Any]]]:
    routing_groups: dict[tuple[Any, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        if str(candidate.get("mapping_method") or "").lower() != "routing":
            continue
        is_v3 = str(candidate.get("mapping_strategy") or "").lower() == "v3"
        dimension_key = str(
            candidate.get("scenario_dimension_key")
            or candidate.get("dimension_key")
            or candidate.get("source_dimension_id")
            or "",
        )
        group_key = (
            "v3" if is_v3 else candidate.get("event_type_l2_id"),
            dimension_key,
        )
        routing_groups.setdefault(group_key, []).append(candidate)
    return routing_groups


def _sanitize_routing_decisions(
    decisions: list[RoutingDecision],
    routing_tasks: list[dict[str, Any]],
    *,
    max_candidates_per_dimension: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    task_by_dimension = {str(task.get("dimension_key") or ""): task for task in routing_tasks}
    selected_keys: set[str] = set()
    returned_dimensions: set[str] = set()
    warnings: list[str] = []

    for decision in decisions:
        dimension_key = str(decision.dimension_key or "")
        task = task_by_dimension.get(dimension_key)
        if task is None:
            warning = f"LLM이 알 수 없는 dimension_key를 routing_decisions에 반환해 제외했습니다: {dimension_key}"
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue
        if dimension_key in returned_dimensions:
            warning = (
                "LLM routing_decisions에 중복 dimension task가 있어 후속 응답을 제외했습니다: "
                f"dimension={dimension_key}"
            )
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue
        returned_dimensions.add(dimension_key)
        allowed_keys = {str(candidate.get("candidate_key") or "") for candidate in task.get("candidates") or []}
        selected_dimension_keys: set[str] = set()
        for raw_candidate_key in decision.selected_candidate_keys:
            candidate_key = str(raw_candidate_key or "")
            if candidate_key not in allowed_keys:
                warning = (
                    "LLM이 해당 routing task에 없는 candidate_key를 반환해 제외했습니다: "
                    f"dimension={dimension_key}, candidate={candidate_key}"
                )
                logger.warning("[model-parameter] {}", warning)
                warnings.append(warning)
                continue
            if candidate_key in selected_dimension_keys:
                continue
            if len(selected_dimension_keys) >= max_candidates_per_dimension:
                warning = (
                    "LLM routing_decisions가 dimension별 선택 상한을 초과해 후속 후보를 제외했습니다: "
                    f"dimension={dimension_key}, limit={max_candidates_per_dimension}, "
                    f"candidate={candidate_key}"
                )
                logger.warning("[model-parameter] {}", warning)
                warnings.append(warning)
                continue
            selected_dimension_keys.add(candidate_key)
            selected_keys.add(candidate_key)

    missing_dimensions = sorted(set(task_by_dimension) - returned_dimensions)
    if missing_dimensions:
        warning = (
            "LLM routing_decisions에 누락된 dimension task가 있어 해당 routing 후보를 제외했습니다: "
            f"{missing_dimensions}"
        )
        logger.warning("[model-parameter] {}", warning)
        warnings.append(warning)

    selected_candidates = [
        candidate
        for task in routing_tasks
        for candidate in task.get("candidates") or []
        if str(candidate.get("candidate_key") or "") in selected_keys
    ]
    return selected_candidates, warnings


def _sanitize_llm_slots(
    slots: list[LLMSlotProposal],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    for slot in slots:
        if slot.candidate_key not in candidate_by_key:
            warning = f"LLM이 알 수 없는 candidate_key를 반환해 slot을 제외했습니다: {slot.candidate_key}"
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue
        issues = _slot_axis_issues(slot.slot_axes)
        if issues:
            warning = (
                "LLM이 실제 모델 input으로 사용할 수 없는 모호한 slot 값을 반환해 "
                f"제외했습니다: {', '.join(issues)}: {slot.candidate_key}"
            )
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue
        sanitized.append(_parameter_slot_from_llm(slot))
    return sanitized, warnings


def _parameter_slot_from_llm(slot: LLMSlotProposal) -> dict[str, Any]:
    return ParameterSlotProposal(
        candidate_key=slot.candidate_key,
        slot_axes=[
            ParameterSlotAxis(
                axis_name=axis.axis_name,
                axis_value=axis.axis_value,
            )
            for axis in slot.slot_axes
        ],
    ).model_dump()


def _group_selected_slots_by_candidate(
    slots: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for slot in _selected_parameter_slots(slots):
        candidate_key = str(slot.get("candidate_key") or "")
        if not candidate_key:
            continue
        grouped.setdefault(candidate_key, []).append(slot)
    return grouped


def _assign_slot_keys(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts_by_candidate: dict[str, int] = {}
    assigned: list[dict[str, Any]] = []
    for raw_slot in _selected_parameter_slots(slots):
        slot = dict(raw_slot)
        candidate_key = str(slot.get("candidate_key") or "")
        count = counts_by_candidate.get(candidate_key, 0) + 1
        counts_by_candidate[candidate_key] = count
        slot["slot_key"] = str(slot.get("slot_key") or f"slot-{count}")
        assigned.append(slot)
    return assigned


def _selected_parameter_slots(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [slot for slot in slots if slot.get("selected", True) is not False]


def _slot_axis_value(axis_name: str, axis_value: Any) -> Any:
    if axis_name.lower() in {"year", "month"}:
        parsed = _int_axis_value(axis_value)
        if parsed is not None:
            return parsed
    return axis_value


def _slot_axes_for_candidate(slots: list[dict[str, Any]]) -> list[ParameterSlotAxis]:
    slot_axes: list[ParameterSlotAxis] = []
    seen: set[tuple[str, str]] = set()
    for slot in slots:
        for axis in slot.get("slot_axes") or []:
            axis_name = str(axis.get("axis_name") or "").strip()
            if not axis_name:
                continue
            axis_value = _slot_axis_value(axis_name, axis.get("axis_value"))
            key = (axis_name, _normalize_axis_value(axis_value))
            if key in seen:
                continue
            seen.add(key)
            slot_axes.append(
                ParameterSlotAxis(
                    axis_name=axis_name,
                    axis_value=axis_value,
                ),
            )
    return slot_axes


def _coordinates_for_selected_slot(slot: dict[str, Any]) -> dict[str, Any]:
    coordinates: dict[str, Any] = {}
    for axis in slot.get("slot_axes") or []:
        axis_name = str(axis.get("axis_name") or "").strip()
        if not axis_name:
            continue
        coordinates[axis_name] = _slot_axis_value(axis_name, axis.get("axis_value"))
    return coordinates


def _canonical_coordinate_key(coordinates: dict[str, Any]) -> str:
    normalized = {
        axis_name: _normalize_axis_value(_slot_axis_value(axis_name, axis_value))
        for axis_name, axis_value in sorted(
            (
                (str(raw_axis_name).strip(), axis_value)
                for raw_axis_name, axis_value in (coordinates or {}).items()
                if str(raw_axis_name).strip()
            ),
            key=lambda item: item[0],
        )
    }
    return to_compact_json(normalized)


def _parameter_value_cell_from_slot_value(
    slot_value: LLMValueCell,
    reference: dict[str, Any],
    *,
    proposed_value: int | float,
) -> ParameterValueCell:
    coordinates = {
        **(reference.get("axes") or {}),
        **(reference.get("metadata") or {}),
    }
    if "llm_reference_value" in reference:
        basecase_value = reference.get("actual_basecase_value")
        lut_value = reference.get("lut_default_value")
        basecase_reference_id = reference.get("basecase_reference_id")
    else:
        basecase_value = reference.get("value")
        lut_value = None
        basecase_reference_id = reference.get("reference_id")
    return ParameterValueCell(
        coordinates=coordinates,
        basecase_value=basecase_value,
        lut_value=lut_value,
        proposed_value=proposed_value,
        rationale_ko=slot_value.rationale_ko,
        basecase_reference_ids=([str(basecase_reference_id)] if basecase_reference_id is not None else []),
    )


def _sanitize_llm_adjustments(
    adjustments: list[LLMValueAdjustment],
    candidates: list[dict[str, Any]],
    slots: list[dict[str, Any]],
    reference_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    settings = get_settings()
    max_decimal_places = settings.model_parameter_proposed_value_max_decimal_places
    precision_mode = settings.model_parameter_proposed_value_precision_mode
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    slots_by_key = _group_selected_slots_by_candidate(slots)
    slot_contexts = _slot_reference_contexts(
        slots,
        reference_records,
    )
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    adjustments_by_candidate: dict[str, list[LLMValueAdjustment]] = {}
    for adjustment in adjustments:
        adjustments_by_candidate.setdefault(adjustment.candidate_key, []).append(
            adjustment,
        )
    duplicate_candidate_keys = {
        candidate_key
        for candidate_key, candidate_adjustments in adjustments_by_candidate.items()
        if len(candidate_adjustments) > 1
    }
    for duplicate_candidate_key in sorted(duplicate_candidate_keys):
        warning = (
            f"LLM Step3 응답에 동일 candidate_key의 adjustment가 중복되어 모두 제외했습니다: {duplicate_candidate_key}"
        )
        logger.warning("[model-parameter] {}", warning)
        warnings.append(warning)

    processed_candidate_keys: set[str] = set()
    for adjustment in adjustments:
        if adjustment.candidate_key in duplicate_candidate_keys:
            continue
        candidate = candidate_by_key.get(adjustment.candidate_key)
        if candidate is None:
            warning = f"LLM이 알 수 없는 candidate_key를 반환해 제외했습니다: {adjustment.candidate_key}"
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue
        processed_candidate_keys.add(adjustment.candidate_key)
        selected_slots = slots_by_key.get(adjustment.candidate_key, [])
        slot_axes = _slot_axes_for_candidate(selected_slots)
        slot_issues = _slot_axis_issues(slot_axes)
        if slot_issues:
            warning = (
                "Step2 selected slot_axes에 실제 모델 input으로 사용할 수 없는 값이 있어 "
                f"검토 경고로 기록했습니다: {', '.join(slot_issues)}: "
                f"{adjustment.candidate_key}"
            )
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)

        expected_contexts = slot_contexts.get(adjustment.candidate_key) or {}
        returned_slot_keys: set[str] = set()
        value_grid: list[ParameterValueCell] = []
        for slot_value in adjustment.slot_values:
            slot_key = str(slot_value.slot_key or "").strip()
            context = expected_contexts.get(slot_key)
            if context is None:
                warning = (
                    "Step3 응답의 slotKey가 요청 목록에 없어 제외했습니다: "
                    f"candidate={adjustment.candidate_key}, slotKey={slot_key or '<empty>'}"
                )
                logger.warning("[model-parameter] {}", warning)
                warnings.append(warning)
                continue
            if slot_key in returned_slot_keys:
                warning = (
                    "Step3 응답이 동일 slotKey를 중복 반환해 후속 값을 제외했습니다: "
                    f"candidate={adjustment.candidate_key}, slotKey={slot_key}"
                )
                logger.warning("[model-parameter] {}", warning)
                warnings.append(warning)
                continue
            if slot_value.proposed_value is None:
                warning = (
                    "Step3 응답의 proposedValue가 null이라 제외했습니다: "
                    f"candidate={adjustment.candidate_key}, slotKey={slot_key}"
                )
                logger.warning("[model-parameter] {}", warning)
                warnings.append(warning)
                continue
            try:
                proposed_value = apply_numeric_precision(
                    slot_value.proposed_value,
                    label=(f"Step3 proposedValue (candidate={adjustment.candidate_key}, slotKey={slot_key})"),
                    max_decimal_places=max_decimal_places,
                    mode=precision_mode,
                )
            except MIBaseError:
                warning = (
                    "Step3 응답의 proposedValue가 유한한 숫자가 아니라 제외했습니다: "
                    f"candidate={adjustment.candidate_key}, slotKey={slot_key}, "
                    f"value={slot_value.proposed_value!r}"
                )
                logger.warning("[model-parameter] {}", warning)
                warnings.append(warning)
                continue
            returned_slot_keys.add(slot_key)
            value_grid.append(
                _parameter_value_cell_from_slot_value(
                    slot_value,
                    context["reference"],
                    proposed_value=proposed_value,
                ),
            )

        missing_slot_keys = sorted(set(expected_contexts) - returned_slot_keys)
        if missing_slot_keys:
            warning = (
                "Step3 응답에 요청한 slotKey가 누락되었습니다. 재호출 없이 누락 값을 "
                f"제외하고 진행합니다: candidate={adjustment.candidate_key}, "
                f"slotKeys={missing_slot_keys}"
            )
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)

        if not value_grid:
            warning = f"Step3 응답에 유효한 slot 값이 없어 parameter를 제외했습니다: {adjustment.candidate_key}"
            logger.warning("[model-parameter] {}", warning)
            warnings.append(warning)
            continue

        sanitized.append(
            ParameterAdjustment(
                candidate_key=adjustment.candidate_key,
                model_file=str(candidate.get("model_file") or ""),
                model_sheet=str(candidate.get("model_sheet") or ""),
                parameter_name=str(
                    candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
                ),
                selected=True,
                slot_axes=slot_axes,
                value_grid=value_grid,
                parameter_selection_rationale_ko=adjustment.rationale_ko,
            ).model_dump()
        )

    missing_candidate_keys = sorted(
        set(candidate_by_key) - processed_candidate_keys - duplicate_candidate_keys,
    )
    for candidate_key in missing_candidate_keys:
        warning = (
            "LLM Step3 응답에 candidate_key가 누락되었습니다. 재호출이나 보강 없이 "
            f"해당 parameter를 제외합니다: {candidate_key}"
        )
        logger.warning("[model-parameter] {}", warning)
        warnings.append(warning)
    return sanitized, warnings


def _current_year_month() -> tuple[int, int]:
    today = date.today()
    return today.year, today.month


def _period_resolution_policy() -> dict[str, Any]:
    year, month = _current_year_month()
    return {
        "current_date": date.today().isoformat(),
        "current_year": year,
        "current_month": month,
        "rules": [
            "scenario/event에 YYYY-MM 또는 YYYY년 M월처럼 연월이 명확하고 current_year/current_month 이후이면 그대로 사용합니다.",
            "명시 연월이 current_year/current_month보다 과거이면 그대로 입력하지 말고 시나리오 전개 기간(현재 이후)으로 재해석합니다. 재해석 시 사건·시나리오의 계절/월 맥락이 좌표 의미에 중요하면 현재 이후 가장 가까운 동일 계절/월로 이월하고, 그렇지 않으면 현재 이후부터 전개합니다.",
            "연도 없이 월만 명시되면 current_year/current_month 이후의 가장 가까운 해당 월로 변환합니다.",
            "affected_period/period가 N개월이면 current_year/current_month부터 N개월 범위의 Year/Month/Period만 사용합니다.",
            "명확한 연월/월 근거가 없으면 추론상 current_year/current_month 이후부터 필요한 period 범위만 전개합니다.",
        ],
    }


def _is_current_or_future_year_month(year: int, month: int) -> bool:
    current_year, current_month = _current_year_month()
    return (year, month) >= (current_year, current_month)


def _first_explicit_year_month(text: str) -> tuple[int, int] | None:
    patterns = (
        r"(20\d{2})\s*년\s*(1[0-2]|0?[1-9])\s*월",
        r"(20\d{2})[-./](1[0-2]|0?[1-9])(?:[-./]\d{1,2})?",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


def _month_only_candidates(text: str) -> list[int]:
    months: list[int] = []
    for match in re.finditer(r"(?<!\d)(1[0-2]|0?[1-9])\s*월", text):
        month = int(match.group(1))
        if month not in months:
            months.append(month)
    return months


def _nearest_current_or_future_month(months: list[int]) -> tuple[int, int] | None:
    if not months:
        return None
    current_year, current_month = _current_year_month()
    candidates = [(current_year if month >= current_month else current_year + 1, month) for month in months]
    return min(candidates)


def _scenario_period_text(dimensions: dict[str, Any], scenario_context: dict[str, Any]) -> str:
    scenario = scenario_context.get("scenario") or {}
    return "\n".join(
        str(item or "")
        for item in (
            scenario.get("title"),
            scenario.get("narrative"),
            *dimensions.values(),
        )
    )


def _event_period_text(scenario_context: dict[str, Any]) -> str:
    group = scenario_context.get("scenario_group") or {}
    event = scenario_context.get("event") or {}
    return "\n".join(
        str(item or "")
        for item in (
            group.get("title"),
            group.get("summary"),
            group.get("description"),
            event.get("occurred_at"),
            event.get("latest_record_first_created"),
            event.get("oldest_record_first_created"),
            event.get("event_title_ko"),
            event.get("one_line_summary"),
            event.get("detail_analysis"),
        )
    )


def _period_start_year_month(
    dimensions: dict[str, Any],
    scenario_context: dict[str, Any],
) -> tuple[int, int, str]:
    scenario_text = _scenario_period_text(dimensions, scenario_context)
    scenario_explicit = _first_explicit_year_month(scenario_text)
    if scenario_explicit is not None:
        return (*scenario_explicit, "scenario에 명시된 연월")

    event_text = _event_period_text(scenario_context)
    event_explicit = _first_explicit_year_month(event_text)
    if event_explicit is not None:
        return (*event_explicit, "event에 명시된 연월")

    scenario_month = (
        _nearest_current_or_future_month(_month_only_candidates(scenario_text)) if scenario_explicit is None else None
    )
    if scenario_month is not None:
        return (*scenario_month, "scenario에 명시된 월-only를 현재 이후 연월로 변환")

    event_month = (
        _nearest_current_or_future_month(_month_only_candidates(event_text)) if event_explicit is None else None
    )
    if event_month is not None:
        return (*event_month, "event에 명시된 월-only를 현재 이후 연월로 변환")

    current_year, current_month = _current_year_month()
    return current_year, current_month, "명확한 연월 근거가 없어 현재 월부터 전개"


def _unselected_adjustments_for_missing_slots(
    candidates: list[dict[str, Any]],
    reason: str,
) -> list[dict[str, Any]]:
    return [
        ParameterAdjustment(
            candidate_key=str(candidate["candidate_key"]),
            model_file=str(candidate.get("model_file") or ""),
            model_sheet=str(candidate.get("model_sheet") or ""),
            parameter_name=str(
                candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
            ),
            selected=False,
            slot_axes=[],
            value_grid=[],
            parameter_selection_rationale_ko=reason,
        ).model_dump()
        for candidate in candidates
    ]
