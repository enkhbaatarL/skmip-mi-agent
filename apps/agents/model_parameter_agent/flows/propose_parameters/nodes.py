from __future__ import annotations

from datetime import date
import re
import time
from typing import Any

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
    ParameterCandidateGroupDecision,
    ParameterSlotAxis,
    ParameterSlotProposal,
    ParameterValueCell,
)
from apps.agents.model_parameter_agent.utils.basecase import (
    basecase_slot_axis_names_from_candidate,
    build_basecase_records,
)
from apps.agents.model_parameter_agent.utils.lut import (
    BasecaseIndex,
    EffectiveReference,
    LutLoadPolicy,
    build_basecase_index,
    build_slot_catalog,
    get_lut_catalog,
    get_parameter_spec_registry,
    resolve_effective_reference,
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
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode


TIME_SLOT_AXIS_NAMES = {"Year", "Month", "Period"}


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
        return [
            {"Year": year, "Months": sorted(months)}
            for year, months in sorted(months_by_year.items())
        ]
    return periods


def _candidate_slot_catalog_for_prompt(
    candidate: CandidateSlotCatalog,
) -> dict[str, Any]:
    leaves: list[dict[str, Any]] = []
    for leaf in candidate.leaves:
        periods = [dict(period.values) for period in leaf.available_periods]
        leaves.append(
            {
                "fixed_axes": dict(leaf.axes),
                "available_periods": _available_periods_for_prompt(
                    candidate,
                    periods,
                ),
            },
        )
    return {
        "candidate_key": candidate.candidate_key,
        "parameter_name": candidate.parameter_name,
        "key_axes": list(candidate.key_axes),
        "fixed_axis_names": list(candidate.non_time_axes),
        "time_axis_names": list(candidate.time_axes),
        "leaves": leaves,
    }


def _slot_catalog_for_prompt(slot_catalog: SlotCatalog) -> list[dict[str, Any]]:
    return [
        _candidate_slot_catalog_for_prompt(candidate)
        for candidate in slot_catalog.candidates
    ]


def _slot_axis_rationale(slot: dict[str, Any], axis_name: str) -> str | None:
    for axis in slot.get("slot_axes") or []:
        if str(axis.get("axis_name") or "") == axis_name:
            rationale = str(axis.get("rationale") or "").strip()
            return rationale or None
    return None


def _effective_reference_to_state(reference: EffectiveReference) -> dict[str, Any]:
    return {
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


def _effective_reference_diagnostics(
    references: list[dict[str, Any]],
    *,
    rejected_slot_count: int,
) -> dict[str, Any]:
    source_counts = {"basecase": 0, "lut": 0}
    lut_only_count = 0
    basecase_and_lut_count = 0
    for reference in references:
        source = str(reference.get("effective_source") or "")
        if source in source_counts:
            source_counts[source] += 1
        if reference.get("actual_basecase_value") is None:
            lut_only_count += 1
        if (
            reference.get("actual_basecase_value") is not None
            and reference.get("lut_default_value") is not None
        ):
            basecase_and_lut_count += 1
    return {
        "selected_reference_count": len(references),
        "rejected_exact_slot_count": rejected_slot_count,
        "effective_source_counts": source_counts,
        "lut_only_count": lut_only_count,
        "basecase_and_lut_count": basecase_and_lut_count,
        "references": references,
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
    return {"scenario_context": context, "parameter_knowledge_base": kb}


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
    return get_parameter_knowledge_base_from_resources(
        mapping_rows=mapping_rules,
        parameter_rows=parameter_definitions,
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
    return {
        "candidate_mappings": candidates,
        "non_input_items": non_inputs,
        "validation_warnings": [*state.validation_warnings, *warnings],
    }


async def validate_parameter_candidates(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "candidate_mappings": [],
            "validation_warnings": state.validation_warnings,
        }

    packet = _build_candidate_validation_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
    )
    messages = [
        {"role": "system", "content": CANDIDATE_VALIDATION_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step1.5 수급모델 parameter 후보를 검증하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMCandidateValidationResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_validation_warnings: list[str] = []
        llm_call = _llm_call_trace(
            step="Step1.5 candidate validation",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        logger.warning(
            "[model-parameter] Step1.5 LLM call failed | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        raise

    candidates, validation_warnings = _sanitize_parameter_candidate_group_decisions(
        llm_payload.parameter_candidate_groups,
        state.candidate_mappings,
    )
    candidates, routing_warnings = _apply_routing_comment_overrides(
        state.candidate_mappings,
        candidates,
    )
    candidates, routing_cap_warnings = _cap_routing_candidates_per_dimension(candidates)
    merged_candidates, merge_warnings = _merge_candidates_by_parameter(candidates)
    logger.info(
        "[model-parameter] validated candidate mappings | scenario_id={} before_count={} after_count={} merged_count={} selected_candidate_keys={} warning_count={}",
        state.scenario_id,
        len(state.candidate_mappings),
        len(candidates),
        len(merged_candidates),
        [candidate.get("candidate_key") for candidate in merged_candidates],
        len(llm_validation_warnings)
        + len(validation_warnings)
        + len(routing_warnings)
        + len(routing_cap_warnings)
        + len(merge_warnings),
    )
    return {
        "candidate_mappings": merged_candidates,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_validation_warnings,
            *validation_warnings,
            *routing_warnings,
            *routing_cap_warnings,
            *merge_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


def load_basecase_samples(state: ModelParameterProposalState) -> dict[str, Any]:
    if state.parameter_knowledge_base is None:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter_knowledge_base is required",
        )
    records, warnings = build_basecase_records(
        state.parameter_knowledge_base,
        state.candidate_mappings,
        state.scenario_context or {},
    )
    cfg = get_settings()
    policy = LutLoadPolicy(
        start_year=cfg.model_parameter_lut_horizon_start_year,
        end_year=cfg.model_parameter_lut_horizon_end_year,
    )
    registry = get_parameter_spec_registry()
    lut_catalog = (
        get_lut_catalog(policy, registry=registry)
        if cfg.model_parameter_lut_enabled
        else None
    )
    basecase_index = build_basecase_index(
        records,
        state.candidate_mappings,
        policy=policy,
        registry=registry,
    )
    slot_catalog = build_slot_catalog(basecase_index, lut_catalog)
    lut_record_count_by_parameter: dict[str, int] = {}
    if lut_catalog is not None:
        for parameter_name in sorted(set(basecase_index.candidate_parameters.values())):
            lut_record_count_by_parameter[parameter_name] = len(
                lut_catalog.records_for_parameter(parameter_name),
            )
    basecase_record_count_by_candidate = {
        candidate_key: len(basecase_index.records_for_candidate(candidate_key))
        for candidate_key in basecase_index.candidate_parameters
    }
    slot_leaf_count_by_candidate = {
        candidate.candidate_key: len(candidate.leaves)
        for candidate in slot_catalog.candidates
    }
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
    return {
        # Full basecase/LUT rows are deliberately kept out of serialized graph state.
        "basecase_records": [],
        "basecase_index": basecase_index,
        "slot_catalog": _slot_catalog_for_prompt(slot_catalog),
        "effective_references": [],
        "selected_slot_keys": [],
        "lut_version": lut_catalog.version if lut_catalog is not None else None,
        "resolved_config": {
            "model_parameter_lut_enabled": cfg.model_parameter_lut_enabled,
            "model_parameter_lut_horizon_start_year": policy.start_year,
            "model_parameter_lut_horizon_end_year": policy.end_year,
            "model_parameter_max_parameter_slots": cfg.model_parameter_max_parameter_slots,
            "model_parameter_max_value_prompt_basecase_records": (
                cfg.model_parameter_max_value_prompt_basecase_records
            ),
            "model_parameter_llm_stream_enabled": cfg.model_parameter_llm_stream_enabled,
            "model_parameter_llm_reasoning_effort": cfg.model_parameter_llm_reasoning_effort,
        },
        "reference_diagnostics": {
            "source": {
                "basecase_record_count": len(basecase_index.records),
                "basecase_record_count_by_candidate": basecase_record_count_by_candidate,
                "lut_record_count": sum(lut_record_count_by_parameter.values()),
                "lut_record_count_by_parameter": lut_record_count_by_parameter,
                "slot_leaf_count": sum(slot_leaf_count_by_candidate.values()),
                "slot_leaf_count_by_candidate": slot_leaf_count_by_candidate,
            },
        },
        "validation_warnings": [*state.validation_warnings, *warnings],
    }


def filter_basecase_records_by_slots(state: ModelParameterProposalState) -> dict[str, Any]:
    if not isinstance(state.basecase_index, BasecaseIndex):
        # Compatibility path for direct unit/local-tool calls created before the
        # request-scoped exact index was introduced. The runnable graph always
        # supplies BasecaseIndex through load_basecase_samples().
        records = state.basecase_records or []
        filtered = _filter_records_by_selected_slots(records, state.parameter_slots)
        return {
            "basecase_records": filtered,
            "validation_warnings": state.validation_warnings,
        }

    cfg = get_settings()
    policy = state.basecase_index.policy
    registry = get_parameter_spec_registry()
    lut_catalog = (
        get_lut_catalog(policy, registry=registry)
        if bool(state.resolved_config.get("model_parameter_lut_enabled"))
        else None
    )
    effective_references: list[dict[str, Any]] = []
    selected_slot_keys: list[dict[str, Any]] = []
    patched_slots: list[dict[str, Any]] = []
    warnings = list(state.validation_warnings)
    counts_by_candidate: dict[str, int] = {}
    rejected_exact_slot_count = 0
    seen_selected_keys: set[tuple[str, str]] = set()

    for raw_slot in state.parameter_slots:
        slot = dict(raw_slot)
        if slot.get("selected", True) is False:
            patched_slots.append(slot)
            continue
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
            warnings.append(
                "Step2 selected slot의 axis schema가 canonical business key와 달라 "
                f"제외했습니다: candidate={candidate_key}, expected={list(expected_axes or ())}, "
                f"provided={provided_axis_names}",
            )
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
                warnings.append(
                    "Step2 selected slot의 canonical exact key가 유효하지 않아 제외했습니다: "
                    f"candidate={candidate_key}, coordinates={to_compact_json(coordinates)}, "
                    f"detail={exc}",
                )
        if reference is None:
            slot["selected"] = False
            slot["slot_axes"] = []
            rejected_exact_slot_count += 1
            warnings.append(
                "Step2 selected slot이 활성 BasecaseIndex/LutCatalog exact union에 없어 "
                f"제외했습니다: candidate={candidate_key}, coordinates={to_compact_json(coordinates)}",
            )
            patched_slots.append(slot)
            continue

        selected_key = (
            candidate_key,
            _canonical_coordinate_key(dict(reference.axes)),
        )
        if selected_key in seen_selected_keys:
            slot["selected"] = False
            slot["slot_axes"] = []
            rejected_exact_slot_count += 1
            warnings.append(
                "Step2가 동일한 canonical exact slot을 중복 반환해 후속 항목을 "
                f"제외했습니다: candidate={candidate_key}, coordinates={selected_key[1]}",
            )
            patched_slots.append(slot)
            continue
        seen_selected_keys.add(selected_key)

        candidate_count = counts_by_candidate.get(candidate_key, 0) + 1
        if candidate_count > cfg.model_parameter_max_value_prompt_basecase_records:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    "selected exact references exceed the per-parameter Step3 limit: "
                    f"candidate={candidate_key}, limit="
                    f"{cfg.model_parameter_max_value_prompt_basecase_records}"
                ),
            )
        counts_by_candidate[candidate_key] = candidate_count
        canonical_axes = dict(reference.axes)
        slot["slot_axes"] = [
            {
                "axis_name": axis_name,
                "axis_value": axis_value,
                "rationale": _slot_axis_rationale(slot, axis_name),
            }
            for axis_name, axis_value in canonical_axes.items()
        ]
        patched_slots.append(slot)
        selected_slot_keys.append(
            {"candidate_key": candidate_key, "axes": canonical_axes},
        )
        effective_references.append(_effective_reference_to_state(reference))

    records = state.basecase_records or []
    logger.info(
        "[model-parameter] resolved exact selected references | scenario_id={} "
        "selected_reference_count={} counts_by_candidate={} rejected_slot_count={}",
        state.scenario_id,
        len(effective_references),
        counts_by_candidate,
        rejected_exact_slot_count,
    )
    return {
        "basecase_records": records,
        "parameter_slots": patched_slots,
        "selected_slot_keys": selected_slot_keys,
        "effective_references": effective_references,
        "reference_diagnostics": {
            **state.reference_diagnostics,
            "selected_references": _effective_reference_diagnostics(
                effective_references,
                rejected_slot_count=rejected_exact_slot_count,
            ),
        },
        "validation_warnings": warnings,
    }


def finalize_empty_parameter_values(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        reason = (
            "Step1/Step1.5 candidate 결과가 없어 Step2 slot proposal 및 "
            "Step3 value proposal LLM 호출을 생략했습니다."
        )
    else:
        reason = "Step2 selected slot이 없어 Step3 value proposal LLM 호출을 생략했습니다."
    logger.info(
        "[model-parameter] finalized empty parameter values | scenario_id={} candidate_count={} reason={}",
        state.scenario_id,
        len(state.candidate_mappings),
        reason,
    )
    return {
        "parameter_adjustments": _unselected_adjustments_for_missing_slots(
            state.candidate_mappings,
            reason,
        ),
        "validation_warnings": [*state.validation_warnings, reason],
    }


async def propose_parameter_values(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "parameter_adjustments": [],
            "validation_warnings": [
                *state.validation_warnings,
                "Step1.5 candidate 결과가 없어 Step3 value 산정을 수행하지 않았습니다.",
            ],
        }

    selected_slots = _selected_parameter_slots(state.parameter_slots)
    if not selected_slots:
        return finalize_empty_parameter_values(state)

    value_references = state.effective_references or state.basecase_records
    packet = _build_value_proposal_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        state.parameter_slots,
        value_references,
        state.non_input_items,
    )
    messages = [
        {"role": "system", "content": VALUE_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step3 수급모델 parameter value_grid를 제안하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMValueProposalResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step3 value proposal",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
        )
    except Exception as exc:
        logger.warning(
            "[model-parameter] Step3 LLM call failed | scenario_id={} error={}",
            state.scenario_id,
            repr(exc),
        )
        raise

    adjustments, validation_warnings, cell_diagnostics = _sanitize_llm_adjustments(
        llm_payload.parameter_adjustments,
        state.candidate_mappings,
        state.parameter_slots,
        value_references,
    )
    llm_validation_warnings = list(
        getattr(llm_payload, "validation_warnings", []) or [],
    )
    selected_adjustments = [adjustment for adjustment in adjustments if adjustment.get("selected", True)]
    logger.info(
        "[model-parameter] proposed parameter values | scenario_id={} adjustment_count={} selected_count={} value_counts_by_parameter={} warning_count={}",
        state.scenario_id,
        len(adjustments),
        len(selected_adjustments),
        _value_counts_by_parameter(selected_adjustments),
        len(llm_validation_warnings) + len(validation_warnings),
    )
    return {
        "parameter_adjustments": adjustments,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
        "reference_diagnostics": {
            **state.reference_diagnostics,
            "cell_validation": cell_diagnostics,
        },
    }


async def propose_parameter_slots(state: ModelParameterProposalState) -> dict[str, Any]:
    if not state.candidate_mappings:
        return {
            "parameter_slots": [],
            "validation_warnings": state.validation_warnings,
        }

    slot_catalog = state.slot_catalog or _legacy_slot_catalog_for_prompt(
        state.candidate_mappings,
        state.basecase_records,
    )
    packet = _build_slot_proposal_prompt_packet(
        state.scenario_context or {},
        state.candidate_mappings,
        slot_catalog,
        state.non_input_items,
    )
    logger.info(
        "[model-parameter] built compact slot catalog prompt | scenario_id={} "
        "candidate_count={} leaf_count={}",
        state.scenario_id,
        len(packet["parameter_slot_tasks"]),
        sum(
            len((task.get("slot_catalog") or {}).get("leaves") or [])
            for task in packet["parameter_slot_tasks"]
        ),
    )
    messages = [
        {"role": "system", "content": SLOT_PROPOSAL_SYSTEM},
        {
            "role": "user",
            "content": (
                "아래 JSON만 근거로 Step2 수급모델 parameter slot 축을 제안하십시오.\n"
                f"{to_compact_json(packet)}"
            ),
        },
    ]

    llm_started = time.perf_counter()
    try:
        result = await _invoke_structured(
            output_schema=LLMSlotProposalResponse,
            messages=messages,
            model_name=state.model_name,
        )
        llm_payload = result.result
        usage = result.usage.model_dump() if result.usage is not None else None
        llm_call = _llm_call_trace(
            step="Step2 slot proposal",
            model_name=getattr(result, "model", None) or state.model_name,
            elapsed_seconds=time.perf_counter() - llm_started,
            usage=usage,
            success=True,
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
    llm_non_input_items = list(getattr(llm_payload, "non_input_items", []) or [])
    llm_validation_warnings = list(
        getattr(llm_payload, "validation_warnings", []) or [],
    )
    non_inputs = [
        item.model_dump()
        for item in llm_non_input_items
    ] or state.non_input_items
    selected_slots = [slot for slot in slots if slot.get("selected", True)]
    logger.info(
        "[model-parameter] proposed parameter slots | scenario_id={} slot_count={} selected_count={} slot_counts_by_parameter={} warning_count={}",
        state.scenario_id,
        len(slots),
        len(selected_slots),
        _slot_counts_by_parameter(selected_slots, state.candidate_mappings),
        len(llm_validation_warnings) + len(validation_warnings),
    )
    return {
        "parameter_slots": slots,
        "non_input_items": non_inputs,
        "validation_warnings": [
            *state.validation_warnings,
            *llm_validation_warnings,
            *validation_warnings,
        ],
        "llm_usage": usage,
        "llm_calls": [*state.llm_calls, llm_call],
    }


def _llm_call_trace(
    *,
    step: str,
    model_name: str | None,
    elapsed_seconds: float,
    usage: dict[str, Any] | None,
    success: bool,
    error: str | None = None,
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "step": step,
        "success": success,
        "model_name": model_name,
        "elapsed_seconds": round(max(0.0, elapsed_seconds), 3),
    }
    if usage is not None:
        trace["usage"] = usage
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
            candidate.get("parameter_name") or "unknown",
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
) -> Any:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    return await invoke_llm_structured_output(
        output_schema=output_schema,
        messages=messages,
        model_name=model_name,
        preference=ModelPreference.QUALITY,
        temperature=0.0,
        max_retries=cfg.llm_max_retries,
        stream=getattr(cfg, "model_parameter_llm_stream_enabled", False),
        reasoning_effort=getattr(
            cfg,
            "model_parameter_llm_reasoning_effort",
            "default",
        ),
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
        candidate.get("canonical_parameter_name")
        or candidate.get("parameter_name")
        or "",
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
            candidate.get("dimension_key")
            or candidate.get("source_dimension_id")
        ),
        "source_dimension_id": candidate.get("source_dimension_id"),
        "source_dimension_label": candidate.get("source_dimension_label"),
        "source_dimension_value": candidate.get("source_dimension_value"),
        "mapping_method": candidate.get("mapping_method"),
        "mapping_comment": candidate.get("mapping_comment"),
    }
    return {
        key: value
        for key, value in payload.items()
        if value is not None
    }


def _source_dimensions_for_prompt(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    raw = candidate.get("source_dimensions")
    if isinstance(raw, list) and raw:
        return [
            item
            for item in raw
            if isinstance(item, dict)
        ]
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
    return {
        "source_dimension_id": item.get("source_dimension_id"),
        "source_dimension_label": item.get("source_dimension_label"),
        "source_dimension_value": item.get("source_dimension_value"),
        "mapping_method": item.get("mapping_method"),
        "reason": item.get("reason"),
    }


def _candidate_group_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(candidate.get("model_file") or ""),
        str(candidate.get("model_sheet") or ""),
        str(
            candidate.get("canonical_parameter_name")
            or candidate.get("parameter_name")
            or "",
        ),
    )


def _parameter_candidate_key(candidate: dict[str, Any]) -> str:
    event_type_l2_id = candidate.get("event_type_l2_id")
    parts = [
        "parameter",
        _field_key(event_type_l2_id),
        _field_key(candidate.get("model_file")),
        _field_key(candidate.get("model_sheet")),
    ]
    parts.append(
        _field_key(
            candidate.get("canonical_parameter_name")
            or candidate.get("parameter_name"),
        ),
    )
    return "|".join(parts)


def _merge_candidates_by_parameter(
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        groups.setdefault(_candidate_group_key(candidate), []).append(candidate)

    merged_candidates: list[dict[str, Any]] = []
    for group_candidates in groups.values():
        if len(group_candidates) == 1:
            candidate = dict(group_candidates[0])
            candidate["merged_candidate_keys"] = (
                candidate.get("merged_candidate_keys")
                or [candidate.get("candidate_key")]
            )
            candidate["source_dimensions"] = _source_dimensions_for_prompt(candidate)
            merged_candidates.append(candidate)
            continue

        base = dict(group_candidates[0])
        merged_candidate_keys: list[str] = []
        source_dimensions: list[dict[str, Any]] = []
        mapping_methods: list[str] = []
        mapping_comments: list[str] = []
        for candidate in group_candidates:
            for candidate_key in (
                candidate.get("merged_candidate_keys")
                or [candidate.get("candidate_key")]
            ):
                _append_unique_text(merged_candidate_keys, candidate_key)
            for source_dimension in _source_dimensions_for_prompt(candidate):
                _append_unique_source_dimension(source_dimensions, source_dimension)
            _append_unique_text(mapping_methods, candidate.get("mapping_method"))
            _append_unique_text(mapping_comments, candidate.get("mapping_comment"))

        merged_method = (
            mapping_methods[0]
            if len(mapping_methods) == 1
            else "merged"
        )
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
            },
        )
        merged_candidates.append(base)

    return merged_candidates, []


def _parameter_validation_prompt_payload(candidate: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "parameter_name": (
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
            ),
            "parameter_hint": candidate.get("parameter_hint"),
            "semantic_axes": candidate.get("semantic_axes"),
        },
    )


def _build_candidate_validation_tasks(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        key = _candidate_group_key(candidate)
        task = groups.setdefault(
            key,
            {
                "parameter": _parameter_validation_prompt_payload(candidate),
                "candidate_keys": [],
                "selection_dimensions": [],
            },
        )
        parameter = task["parameter"]
        if "parameter_hint" not in parameter and candidate.get("parameter_hint"):
            parameter["parameter_hint"] = candidate.get("parameter_hint")
        if "semantic_axes" not in parameter and candidate.get("semantic_axes"):
            parameter["semantic_axes"] = candidate.get("semantic_axes")

        for candidate_key in (
            candidate.get("merged_candidate_keys")
            or [candidate.get("candidate_key")]
        ):
            _append_unique_text(task["candidate_keys"], candidate_key)
        for source_dimension in _source_dimensions_for_prompt(candidate):
            dimension = _source_dimension_for_value_task(source_dimension)
            if dimension:
                _append_unique_source_dimension(task["selection_dimensions"], dimension)

    return [
        _drop_none_or_empty(task)
        for task in groups.values()
    ]


def _build_candidate_validation_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(
            scenario_context,
            allowed_dimension_keys=_allowed_prompt_dimension_keys(candidates),
        ),
        "candidate_validation_tasks": _build_candidate_validation_tasks(candidates),
    }


def _legacy_slot_catalog_for_prompt(
    candidates: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the new compact shape for older direct callers with raw rows."""
    records_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        records_by_candidate.setdefault(
            str(record.get("candidate_key") or ""),
            [],
        ).append(record)

    catalogs: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        candidate_records = records_by_candidate.get(candidate_key, [])
        key_axes: list[str] = []
        for record in candidate_records:
            for axis_name in (record.get("axes") or {}):
                _append_unique_text(key_axes, axis_name)
        non_time_axes = [axis for axis in key_axes if not _is_time_slot_axis(axis)]
        time_axes = [axis for axis in key_axes if _is_time_slot_axis(axis)]
        leaves_by_key: dict[str, dict[str, Any]] = {}
        for record in candidate_records:
            axes = record.get("axes") or {}
            fixed_axes = {
                axis_name: _slot_option_value(axes.get(axis_name))
                for axis_name in non_time_axes
            }
            leaf_key = to_compact_json(fixed_axes)
            leaf = leaves_by_key.setdefault(
                leaf_key,
                {"fixed_axes": fixed_axes, "available_periods": []},
            )
            period = {
                axis_name: _slot_option_value(axes.get(axis_name))
                for axis_name in time_axes
            }
            if period not in leaf["available_periods"]:
                leaf["available_periods"].append(period)
        catalogs.append(
            {
                "candidate_key": candidate_key,
                "parameter_name": (
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                ),
                "key_axes": key_axes,
                "fixed_axis_names": non_time_axes,
                "time_axis_names": time_axes,
                "leaves": list(leaves_by_key.values()),
            },
        )
    return catalogs


def _build_slot_proposal_prompt_packet(
    scenario_context: dict[str, Any],
    candidates: list[dict[str, Any]],
    slot_catalog: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> dict[str, Any]:
    cfg = get_settings()
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
            "maxParameterSlots": cfg.model_parameter_max_parameter_slots,
            "applicationScope": "independent_per_parameter_task",
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


def _slot_for_value_prompt(slot: dict[str, Any]) -> dict[str, Any]:
    slot_axes = slot.get("slot_axes") or []
    return {
        "candidate_key": slot.get("candidate_key"),
        "slot_axes": slot_axes,
        "selected_slot_axes_field_names": _slot_axis_names(slot_axes),
    }


def _slot_axis_names(slot_axes: list[dict[str, Any]]) -> list[str]:
    axis_names: list[str] = []
    for axis in slot_axes or []:
        axis_name = axis.get("axis_name")
        if axis_name:
            _append_unique_text(axis_names, axis_name)
    return axis_names


def _build_basecase_value_groups(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for record in records:
        axes = record.get("axes") or {}
        fixed_axes: dict[str, Any] = {}
        cell_axes: dict[str, Any] = {}
        for axis_name, axis_value in axes.items():
            axis_name_text = str(axis_name)
            display_value = _slot_option_value(axis_value)
            if _is_time_slot_axis(axis_name_text):
                cell_axes[axis_name_text] = display_value
            else:
                fixed_axes[axis_name_text] = display_value

        group_key = to_compact_json(
            [
                record.get("candidate_key"),
                record.get("value_name") or record.get("parameter_name"),
                fixed_axes,
            ],
        )
        group = groups.setdefault(
            group_key,
            {
                "candidate_key": record.get("candidate_key"),
                "value_name": record.get("value_name") or record.get("parameter_name"),
                "fixed_axes": fixed_axes,
                "variable_axis_names": [],
                "cells": [],
            },
        )
        for axis_name in cell_axes:
            _append_unique_text(group["variable_axis_names"], axis_name)
        group["cells"].append(
            {
                "reference_id": (
                    record.get("basecase_reference_id")
                    or record.get("lut_reference_id")
                    or record.get("reference_id")
                ),
                "axes": cell_axes,
                (
                    "llm_reference_value"
                    if "llm_reference_value" in record
                    else "basecase_value"
                ): (
                    record.get("llm_reference_value")
                    if "llm_reference_value" in record
                    else record.get("value")
                ),
            },
        )
    return list(groups.values())


def _filter_dimension_values(
    dimension_values: Any,
    allowed_dimension_keys: set[str] | None,
) -> Any:
    if allowed_dimension_keys is None or not isinstance(dimension_values, dict):
        return dimension_values
    return {
        key: value
        for key, value in dimension_values.items()
        if str(key) in allowed_dimension_keys
    }


def _filter_dimension_selected(
    dimension_selected: Any,
    allowed_dimension_keys: set[str] | None,
) -> Any:
    if allowed_dimension_keys is None:
        return dimension_selected

    if isinstance(dimension_selected, str):
        return [
            item
            for item in re.findall(r"[A-Za-z0-9_]+", dimension_selected)
            if item in allowed_dimension_keys
        ]

    if not isinstance(dimension_selected, list):
        return dimension_selected

    filtered: list[Any] = []
    for item in dimension_selected:
        if isinstance(item, dict):
            key = item.get("dim_key") or item.get("dimension_key") or item.get("key")
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
        key = item.get("dim_key") or item.get("dimension_key") or item.get("key")
        if key is not None and str(key) in allowed_dimension_keys:
            filtered.append(item)
    return filtered


def _scenario_brief_for_value_prompt(
    scenario_context: dict[str, Any],
    *,
    allowed_dimension_keys: set[str] | None = None,
) -> dict[str, Any]:
    scenario = scenario_context.get("scenario") or {}
    scenario_group = scenario_context.get("scenario_group") or {}
    dimension_template = scenario_context.get("dimension_template") or []
    event = scenario_context.get("event") or {}
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
    brief = {
        "scenario_id": scenario.get("scenario_id"),
        "title": scenario.get("title"),
        "selected_dimensions": _selected_dimensions_for_value_prompt(
            scenario_context,
            allowed_dimension_keys=allowed_dimension_keys,
        ),
        "scenario_group": scenario_group_brief,
        "scenario": scenario_detail,
        "dimension_template": dimension_template_brief,
        "event": event_brief,
    }
    return _drop_none_or_empty(brief)


def _selected_dimensions_for_value_prompt(
    scenario_context: dict[str, Any],
    *,
    allowed_dimension_keys: set[str] | None = None,
) -> list[dict[str, Any]]:
    scenario = scenario_context.get("scenario") or {}
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
        key = item.get("dim_key")
        if key:
            label_by_key[str(key)] = item.get("label")

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
    return {
        key: item
        for key, item in value.items()
        if item is not None and item != "" and item != [] and item != {}
    }


def _source_dimension_for_value_task(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_or_empty(
        {
            "dimension_key": (
                item.get("dimension_key")
                or item.get("source_dimension_id")
            ),
            "dimension_label": item.get("source_dimension_label"),
            "dimension_value": item.get("source_dimension_value"),
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
            "dimension_key": item.get("source_dimension_id"),
            "dimension_label": item.get("source_dimension_label"),
            "dimension_value": item.get("source_dimension_value"),
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


def _slot_for_value_task(slot: dict[str, Any]) -> dict[str, Any]:
    return {
        "slot_axes": slot.get("slot_axes") or [],
    }


def _strip_candidate_key_from_basecase_group(group: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in group.items()
        if key != "candidate_key"
    }


def _strip_candidate_key_from_slot_option(option: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in option.items()
        if key != "candidate_key"
    }


def _selected_slot_axis_names_for_task(slots: list[dict[str, Any]]) -> list[str]:
    axis_names: list[str] = []
    for slot in slots:
        for axis_name in _slot_axis_names(slot.get("slot_axes") or []):
            _append_unique_text(axis_names, axis_name)
    return axis_names


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
            "parameter_name": (
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
            ),
            "parameter_hint": candidate.get("parameter_hint"),
            "semantic_axes": candidate.get("semantic_axes"),
            "allowed_slot_axes_field_names": (
                allowed_slot_axes
                if allowed_slot_axes is not None
                else _allowed_slot_axes_field_names(candidate)
            ),
        },
    )


def _build_parameter_slot_tasks(
    candidates: list[dict[str, Any]],
    slot_catalog: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    max_parameter_slots = get_settings().model_parameter_max_parameter_slots
    catalog_by_key = {
        str(candidate_catalog.get("candidate_key") or ""): {
            key: value
            for key, value in candidate_catalog.items()
            if key != "candidate_key"
        }
        for candidate_catalog in slot_catalog
    }

    tasks: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        candidate_catalog = catalog_by_key.get(
            candidate_key,
            {
                "parameter_name": (
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                ),
                "key_axes": _allowed_slot_axes_field_names(candidate),
                "fixed_axis_names": [],
                "time_axis_names": [],
                "leaves": [],
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
    max_reference_records = get_settings().model_parameter_max_value_prompt_basecase_records
    selected_slots_by_key = _group_selected_slots_by_candidate(parameter_slots)
    basecase_groups_by_key: dict[str, list[dict[str, Any]]] = {}
    for group in _build_basecase_value_groups(basecase_records):
        candidate_key = str(group.get("candidate_key") or "")
        basecase_groups_by_key.setdefault(candidate_key, []).append(
            _strip_candidate_key_from_basecase_group(group),
        )

    tasks: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        selected_slots = selected_slots_by_key.get(candidate_key, [])
        selected_axis_names = _selected_slot_axis_names_for_task(selected_slots)
        task = {
            "parameter": _parameter_prompt_payload(candidate),
            "limits": {
                "maxReferenceRecords": max_reference_records,
                "applicationScope": "independent_per_parameter_task",
            },
            "selection_dimensions": _selection_dimensions_for_task(candidate),
            "supporting_dimensions": _supporting_dimensions_for_task(
                non_input_items,
                candidate,
            ),
            "selected_slot_axes_field_names": selected_axis_names,
            "selected_slots": [
                _slot_for_value_task(slot)
                for slot in selected_slots
            ],
            "basecase_value_groups": basecase_groups_by_key.get(candidate_key, []),
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
    cfg = get_settings()
    return {
        "scenario_brief": _scenario_brief_for_value_prompt(
            scenario_context,
            allowed_dimension_keys=_allowed_prompt_dimension_keys(
                candidates,
                non_input_items,
            ),
        ),
        "period_resolution_policy": _compact_period_resolution_policy(),
        "basecase_record_selection_policy": {
            "maxRecords": cfg.model_parameter_max_value_prompt_basecase_records,
        },
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


def _slot_axis_pairs(slot: dict[str, Any]) -> list[tuple[str, Any]]:
    pairs: list[tuple[str, Any]] = []
    for axis in slot.get("slot_axes") or []:
        axis_name = axis.get("axis_name")
        if axis_name:
            pairs.append((str(axis_name), axis.get("axis_value")))
    return pairs


def _record_axis_matches(
    record_axes: dict[str, Any],
    axis_name: str,
    axis_value: Any,
) -> bool:
    return (
        axis_name in record_axes
        and _normalize_axis_value(record_axes.get(axis_name))
        == _normalize_axis_value(axis_value)
    )


def _record_fully_matches_slot(record: dict[str, Any], slot: dict[str, Any]) -> bool:
    record_axes = record.get("axes") or {}
    axis_pairs = _slot_axis_pairs(slot)
    if not axis_pairs:
        return True
    for axis_name, axis_value in axis_pairs:
        if not _record_axis_matches(record_axes, axis_name, axis_value):
            return False
    return True


def _record_matches_slot_prefix_depth(
    record: dict[str, Any],
    slot: dict[str, Any],
    depth: int,
) -> bool:
    axis_pairs = _slot_axis_pairs(slot)
    if depth <= 0 or depth > len(axis_pairs):
        return False
    record_axes = record.get("axes") or {}
    return all(
        _record_axis_matches(record_axes, axis_name, axis_value)
        for axis_name, axis_value in axis_pairs[:depth]
    )


def _filter_records_by_selected_slots(
    records: list[dict[str, Any]],
    slots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected_slots = _selected_parameter_slots(slots)
    if not selected_slots:
        return []

    max_records = get_settings().model_parameter_max_value_prompt_basecase_records
    if len(records) <= max_records:
        return records

    slots_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for slot in selected_slots:
        candidate_key = str(slot.get("candidate_key") or "")
        if not candidate_key:
            continue
        slots_by_candidate.setdefault(candidate_key, []).append(slot)

    filtered: list[dict[str, Any]] = []
    included_indices: set[int] = set()

    def append_record(index: int, record: dict[str, Any]) -> bool:
        if index in included_indices:
            return False
        included_indices.add(index)
        filtered.append(record)
        return len(filtered) >= max_records

    for index, record in enumerate(records):
        candidate_key = str(record.get("candidate_key") or "")
        candidate_slots = slots_by_candidate.get(candidate_key) or []
        if any(_record_fully_matches_slot(record, slot) for slot in candidate_slots):
            if append_record(index, record):
                return filtered

    max_axis_count = max(
        (
            len(_slot_axis_pairs(slot))
            for candidate_slots in slots_by_candidate.values()
            for slot in candidate_slots
        ),
        default=0,
    )
    for depth in range(max_axis_count - 1, 0, -1):
        for index, record in enumerate(records):
            candidate_key = str(record.get("candidate_key") or "")
            candidate_slots = slots_by_candidate.get(candidate_key) or []
            if any(
                _record_matches_slot_prefix_depth(record, slot, depth)
                for slot in candidate_slots
            ):
                if append_record(index, record):
                    return filtered
    return filtered


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
        non_time_axes = [
            axis_name
            for axis_name in option["axis_names"]
            if not _is_time_slot_axis(axis_name)
        ]
        option["slot_hierarchy_axes"] = non_time_axes
        root = hierarchy_roots_by_candidate.setdefault(candidate_key, {})
        for record in records:
            if str(record.get("candidate_key") or "") != candidate_key:
                continue
            axes = record.get("axes") or {}
            path = [
                axes.get(axis_name)
                for axis_name in non_time_axes
            ]
            if path and all(value not in (None, "") for value in path):
                _add_hierarchy_path(root, path)
        option["slot_hierarchy"] = _hierarchy_for_prompt(root)
        axis_values = axis_values_by_candidate.get(candidate_key) or {}
        option["axis_values"] = {
            axis_name: [
                value
                for _, value in sorted(values.items(), key=lambda item: str(item[1]))
            ]
            for axis_name, values in axis_values.items()
        }
    return list(options.values())


def _sanitize_parameter_candidate_group_decisions(
    groups: list[ParameterCandidateGroupDecision],
    candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    selected_by_key: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    returned_keys: set[str] = set()

    for group in groups:
        group_candidate_keys = [
            str(candidate_key)
            for candidate_key in group.candidate_keys
            if str(candidate_key or "").strip()
        ]
        if not group_candidate_keys:
            warnings.append("LLM parameter_candidate_groups에 빈 candidate_keys가 있어 제외했습니다.")
            continue

        known_keys = [
            candidate_key
            for candidate_key in group_candidate_keys
            if candidate_key in candidate_by_key
        ]
        unknown_keys = sorted(set(group_candidate_keys) - set(known_keys))
        if unknown_keys:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 parameter_candidate_groups에 반환해 제외했습니다: "
                f"{unknown_keys}",
            )
        returned_keys.update(known_keys)
        if not group.selected:
            continue

        for candidate_key in known_keys:
            candidate = candidate_by_key[candidate_key]
            selected_by_key[candidate_key] = dict(candidate)

    for candidate in candidates:
        candidate_key = str(candidate.get("candidate_key") or "")
        if candidate_key in selected_by_key:
            continue
        mapping_method = str(candidate.get("mapping_method") or "").lower()
        if mapping_method == "direct":
            enriched = dict(candidate)
            if candidate_key in returned_keys:
                warning = (
                    "direct 후보는 LLM parameter group selected=false와 무관하게 유지했습니다: "
                    f"{candidate_key}"
                )
            else:
                warning = (
                    "LLM parameter group 응답에 누락된 direct candidate_key는 유지했습니다: "
                    f"{candidate_key}"
                )
            selected_by_key[candidate_key] = enriched
            warnings.append(warning)

    missing_keys = sorted(
        key
        for key in set(candidate_by_key) - returned_keys
        if str(candidate_by_key[key].get("mapping_method") or "").lower() != "direct"
    )
    if missing_keys:
        warnings.append(
            "LLM parameter group 응답에 누락된 candidate_key는 제외했습니다: "
            f"{missing_keys}",
        )
    selected_candidates = [
        selected_by_key[str(candidate.get("candidate_key") or "")]
        for candidate in candidates
        if str(candidate.get("candidate_key") or "") in selected_by_key
    ]
    if candidates and not selected_candidates:
        warnings.append("LLM parameter group 검증 결과 selected=true candidate가 없습니다.")
    return selected_candidates, warnings


def _routing_groups_by_dimension(
    candidates: list[dict[str, Any]],
) -> dict[tuple[Any, str], list[dict[str, Any]]]:
    routing_groups: dict[tuple[Any, str], list[dict[str, Any]]] = {}
    for candidate in candidates:
        if str(candidate.get("mapping_method") or "").lower() != "routing":
            continue
        group_key = (
            candidate.get("event_type_l2_id"),
            str(candidate.get("dimension_key") or candidate.get("source_dimension_id") or ""),
        )
        routing_groups.setdefault(group_key, []).append(candidate)
    return routing_groups


ROUTING_COMMENT_GENERIC_TOKENS = {
    "경우",
    "시설",
    "시",
    "영향",
    "유형",
    "피해",
    "facility",
    "impact",
    "type",
    "when",
}

def _routing_match_tokens(value: Any) -> list[str]:
    tokens = re.findall(r"[0-9a-zA-Z가-힣]+", str(value or "").lower())
    return [
        token
        for token in tokens
        if len(token) >= 2 and token not in ROUTING_COMMENT_GENERIC_TOKENS
    ]


def _routing_comment_matches_dimension_value(value: Any, comment: Any) -> bool:
    value_tokens = _routing_match_tokens(value)
    comment_tokens = _routing_match_tokens(comment)
    if not value_tokens or not comment_tokens:
        return False
    comment_text = " ".join(comment_tokens)
    return all(token in comment_text for token in value_tokens)


def _apply_routing_comment_overrides(
    all_candidates: list[dict[str, Any]],
    selected_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Use bridge-sheet routing comments as deterministic tiebreakers.

    LLM still performs the candidate gate, but when the DB dimension value
    clearly matches a routing row comment such as "생산 시설 피해 시", that row is
    the authoritative route for the dimension.
    """

    selected_by_key = {
        str(candidate.get("candidate_key") or ""): dict(candidate)
        for candidate in selected_candidates
    }
    warnings: list[str] = []
    routing_groups = _routing_groups_by_dimension(all_candidates)

    for group_candidates in routing_groups.values():
        matched = [
            candidate
            for candidate in group_candidates
            if _routing_comment_matches_dimension_value(
                candidate.get("source_dimension_value"),
                candidate.get("mapping_comment"),
            )
        ]
        if not matched:
            continue
        matched_keys = {str(candidate.get("candidate_key") or "") for candidate in matched}
        for candidate in group_candidates:
            candidate_key = str(candidate.get("candidate_key") or "")
            if candidate_key in matched_keys:
                if candidate_key not in selected_by_key:
                    enriched = dict(candidate)
                    selected_by_key[candidate_key] = enriched
                    warnings.append(
                        "routing 후보를 DB 매핑 comment 기준으로 selected=true 보정했습니다: "
                        f"{candidate_key}",
                    )
                continue
            if candidate_key in selected_by_key:
                selected_by_key.pop(candidate_key, None)
                warnings.append(
                    "routing 후보를 DB 매핑 comment 기준으로 selected=false 보정했습니다: "
                    f"{candidate_key}",
                )

    ordered = [
        selected_by_key[str(candidate.get("candidate_key") or "")]
        for candidate in all_candidates
        if str(candidate.get("candidate_key") or "") in selected_by_key
    ]
    return ordered, warnings


def _cap_routing_candidates_per_dimension(
    selected_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Keep at most 2 routing candidates per (event_type_l2_id, dimension_key).

    Must run after _apply_routing_comment_overrides (which may add candidates)
    and before _merge_candidates_by_parameter (which clears dimension_key).
    Priority: comment-matched candidates first, then original candidate order.
    """

    dropped_keys: set[str] = set()
    warnings: list[str] = []
    max_candidates_per_dimension = get_settings().model_parameter_max_routing_candidates_per_dimension
    for group_candidates in _routing_groups_by_dimension(selected_candidates).values():
        if len(group_candidates) <= max_candidates_per_dimension:
            continue
        matched: list[dict[str, Any]] = []
        unmatched: list[dict[str, Any]] = []
        for candidate in group_candidates:
            if _routing_comment_matches_dimension_value(
                candidate.get("source_dimension_value"),
                candidate.get("mapping_comment"),
            ):
                matched.append(candidate)
            else:
                unmatched.append(candidate)
        for candidate in (matched + unmatched)[max_candidates_per_dimension:]:
            candidate_key = str(candidate.get("candidate_key") or "")
            if not candidate_key:
                continue
            dropped_keys.add(candidate_key)
            warnings.append(
                "routing 후보가 dimension당 최대 "
                f"{max_candidates_per_dimension}개를 초과해 제외했습니다: "
                f"{candidate_key}",
            )

    if not dropped_keys:
        return selected_candidates, warnings
    return (
        [
            candidate
            for candidate in selected_candidates
            if str(candidate.get("candidate_key") or "") not in dropped_keys
        ],
        warnings,
    )


def _sanitize_llm_slots(
    slots: list[LLMSlotProposal],
    candidates: list[dict[str, Any]],
    *,
    max_selected_slots: int | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if max_selected_slots is None:
        max_selected_slots = get_settings().model_parameter_max_parameter_slots
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    selected_slot_count_by_candidate: dict[str, int] = {}
    for slot in slots:
        if slot.candidate_key not in candidate_by_key:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 반환해 slot을 제외했습니다: "
                f"{slot.candidate_key}",
            )
            continue
        issues = _slot_axis_issues(slot.slot_axes)
        if issues:
            reason = (
                "LLM이 실제 모델 input으로 사용할 수 없는 모호한 slot 값을 반환해 "
                f"selected=false로 보정했습니다: {', '.join(issues)}"
            )
            warnings.append(f"{reason}: {slot.candidate_key}")
            patched = slot.model_copy(
                update={
                    "selected": False,
                    "slot_axes": [],
                },
            )
            sanitized.append(_parameter_slot_from_llm(patched))
            continue
        if slot.selected is not False:
            selected_slot_count = selected_slot_count_by_candidate.get(slot.candidate_key, 0) + 1
            selected_slot_count_by_candidate[slot.candidate_key] = selected_slot_count
            if selected_slot_count > max_selected_slots:
                reason = (
                    "LLM이 parameter task의 limits.maxParameterSlots를 초과해 반환하여 "
                    "초과 slot을 selected=false로 보정했습니다."
                )
                warnings.append(f"{reason}: {slot.candidate_key}")
                patched = slot.model_copy(
                    update={
                        "selected": False,
                    },
                )
                sanitized.append(_parameter_slot_from_llm(patched))
                continue
        sanitized.append(_parameter_slot_from_llm(slot))
    return sanitized, warnings


def _parameter_slot_from_llm(slot: LLMSlotProposal) -> dict[str, Any]:
    return ParameterSlotProposal(
        candidate_key=slot.candidate_key,
        selected=slot.selected,
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


def _requested_slot_coordinates(slots: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    requested: dict[str, dict[str, Any]] = {}
    for slot in slots:
        coordinates = _coordinates_for_selected_slot(slot)
        requested[_canonical_coordinate_key(coordinates)] = coordinates
    return requested


def _coordinate_request_issues(
    coordinates: dict[str, Any],
    requested_coordinates_by_key: dict[str, dict[str, Any]],
) -> list[str]:
    if not requested_coordinates_by_key:
        return ["Step2 selected slot이 없어 value_grid cell을 받을 수 없습니다"]

    coordinate_key = _canonical_coordinate_key(coordinates)
    if coordinate_key in requested_coordinates_by_key:
        return []

    requested_axis_names: set[str] = set()
    for requested_coordinates in requested_coordinates_by_key.values():
        requested_axis_names.update(requested_coordinates)
    provided_axis_names = {
        str(axis_name).strip()
        for axis_name in (coordinates or {})
        if str(axis_name).strip()
    }

    issues: list[str] = []
    missing_axis_names = sorted(requested_axis_names - provided_axis_names)
    extra_axis_names = sorted(provided_axis_names - requested_axis_names)
    if missing_axis_names:
        issues.append(f"요청 slot axis 누락: {', '.join(missing_axis_names)}")
    if extra_axis_names:
        issues.append(f"요청하지 않은 slot axis 포함: {', '.join(extra_axis_names)}")
    if not issues:
        issues.append(
            "요청 selected_slots에 없는 좌표: "
            f"{to_compact_json(coordinates or {})}",
        )
    return issues


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


def _value_cell_signature(cell: ParameterValueCell) -> str:
    return to_compact_json(
        {
            "basecase_value": cell.basecase_value,
            "proposed_value": cell.proposed_value,
        },
    )


def _dedupe_value_grid_by_slot(
    cells: list[ParameterValueCell],
) -> tuple[list[ParameterValueCell], list[str]]:
    deduped: list[ParameterValueCell] = []
    seen_by_slot: dict[str, tuple[str, ParameterValueCell]] = {}
    conflicts: list[str] = []

    for cell in cells:
        slot_key = _canonical_coordinate_key(cell.coordinates)
        signature = _value_cell_signature(cell)
        existing = seen_by_slot.get(slot_key)
        if existing is None:
            seen_by_slot[slot_key] = (signature, cell)
            deduped.append(cell)
            continue
        if existing[0] == signature:
            continue
        conflicts.append(
            "동일 slot 좌표에 서로 다른 value 제안이 반환되었습니다: "
            f"slot={slot_key}",
        )

    return deduped, conflicts


def _parameter_value_cell_from_llm(cell: LLMValueCell) -> ParameterValueCell:
    return ParameterValueCell(
        coordinates=cell.coordinates,
        basecase_value=None,
        proposed_value=cell.proposed_value,
        rationale_ko=cell.rationale_ko,
        basecase_reference_ids=cell.basecase_reference_ids,
    )


def _effective_references_by_candidate_and_coordinate(
    records: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    indexed: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        if "llm_reference_value" not in record:
            continue
        candidate_key = str(record.get("candidate_key") or "")
        coordinate_key = _canonical_coordinate_key(record.get("axes") or {})
        candidate_records = indexed.setdefault(candidate_key, {})
        if coordinate_key in candidate_records:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail=(
                    "selected EffectiveReference contains a duplicate exact coordinate: "
                    f"candidate={candidate_key}, coordinates={coordinate_key}"
                ),
            )
        candidate_records[coordinate_key] = record
    return indexed


def _materialize_effective_cell(
    cell: ParameterValueCell,
    reference: dict[str, Any],
) -> ParameterValueCell:
    coordinates = {
        **cell.coordinates,
        **(reference.get("metadata") or {}),
    }
    basecase_reference_id = reference.get("basecase_reference_id")
    return cell.model_copy(
        update={
            "coordinates": coordinates,
            "basecase_value": reference.get("actual_basecase_value"),
            "basecase_reference_ids": (
                [str(basecase_reference_id)]
                if basecase_reference_id is not None
                else []
            ),
        },
    )


def _sanitize_llm_adjustments(
    adjustments: list[LLMValueAdjustment],
    candidates: list[dict[str, Any]],
    slots: list[dict[str, Any]],
    reference_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    candidate_by_key = {str(candidate["candidate_key"]): candidate for candidate in candidates}
    slots_by_key = _group_selected_slots_by_candidate(slots)
    effective_by_candidate = _effective_references_by_candidate_and_coordinate(
        reference_records,
    )
    basecase_by_reference_id = {
        str(record["reference_id"]): record
        for record in reference_records
        if record.get("reference_id") is not None
    }
    sanitized: list[dict[str, Any]] = []
    warnings: list[str] = []
    returned_candidate_keys: set[str] = set()
    diagnostics: dict[str, Any] = {
        "selected_cell_count": 0,
        "returned_cell_count": 0,
        "valid_cell_count": 0,
        "missing_cell_count": 0,
        "invalid_cell_count": 0,
        "by_candidate": {},
    }
    for adjustment in adjustments:
        candidate = candidate_by_key.get(adjustment.candidate_key)
        if candidate is None:
            warnings.append(
                "LLM이 알 수 없는 candidate_key를 반환해 제외했습니다: "
                f"{adjustment.candidate_key}",
            )
            continue
        returned_candidate_keys.add(adjustment.candidate_key)
        selected_slots = slots_by_key.get(adjustment.candidate_key, [])
        slot_axes = _slot_axes_for_candidate(selected_slots)
        requested_coordinates_by_key = _requested_slot_coordinates(selected_slots)
        returned_coordinate_keys: set[str] = set()
        candidate_diagnostics = {
            "selected_cell_count": len(requested_coordinates_by_key),
            "returned_cell_count": len(adjustment.value_grid),
            "valid_cell_count": 0,
            "missing_cell_count": 0,
            "invalid_cell_count": 0,
        }
        slot_issues = _slot_axis_issues(slot_axes)
        if slot_issues:
            reason = (
                "Step2 selected slot_axes에 실제 모델 input으로 사용할 수 없는 값이 있어 "
                f"검토 경고로 기록했습니다: {', '.join(slot_issues)}"
            )
            warnings.append(f"{reason}: {adjustment.candidate_key}")

        value_grid: list[ParameterValueCell] = []
        for raw_cell in adjustment.value_grid:
            cell = _parameter_value_cell_from_llm(raw_cell)
            coordinate_issues = _coordinate_issues(cell.coordinates)
            if coordinate_issues:
                reason = (
                    "Step3 응답 value_grid.coordinates에 모호한 값이 있어 "
                    f"cell을 제외했습니다: {', '.join(coordinate_issues)}"
                )
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                candidate_diagnostics["invalid_cell_count"] += 1
                continue
            coordinate_request_issues = _coordinate_request_issues(
                cell.coordinates,
                requested_coordinates_by_key,
            )
            if coordinate_request_issues:
                reason = (
                    "Step3 응답 value_grid.coordinates가 요청 기준 slot 좌표를 그대로 반영하지 않아 "
                    f"cell을 제외했습니다: {', '.join(coordinate_request_issues)}"
                )
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                candidate_diagnostics["invalid_cell_count"] += 1
                continue
            if cell.proposed_value is None:
                reason = (
                    "Step3 응답 value_grid.proposed_value가 null이라 "
                    "cell을 제외했습니다. 범위형 dimension은 자동 변환해야 합니다."
                )
                warnings.append(f"{reason}: {adjustment.candidate_key}")
                candidate_diagnostics["invalid_cell_count"] += 1
                continue
            business_coordinate_key = _canonical_coordinate_key(cell.coordinates)
            effective_reference = effective_by_candidate.get(
                adjustment.candidate_key,
                {},
            ).get(business_coordinate_key)
            if effective_by_candidate and effective_reference is None:
                warnings.append(
                    "Step3 응답 좌표에 대응하는 selected EffectiveReference가 없어 "
                    f"cell을 제외했습니다: {adjustment.candidate_key}",
                )
                candidate_diagnostics["invalid_cell_count"] += 1
                continue
            if effective_reference is not None:
                patched_cell = _materialize_effective_cell(cell, effective_reference)
            else:
                patched_cell, patch_warning = _patch_basecase_value(
                    cell,
                    basecase_by_reference_id,
                )
                if patch_warning:
                    warnings.append(f"{patch_warning}: {adjustment.candidate_key}")
            value_grid.append(patched_cell)
            returned_coordinate_keys.add(business_coordinate_key)

        value_grid, slot_conflicts = _dedupe_value_grid_by_slot(value_grid)
        if slot_conflicts:
            reason = (
                "Step3 응답 value_grid에 동일 slot 좌표의 value 충돌이 있어 "
                "첫 번째 유효 cell만 유지했습니다."
            )
            warnings.append(f"{reason}: {adjustment.candidate_key}")
            warnings.extend(f"{conflict}: {adjustment.candidate_key}" for conflict in slot_conflicts)
            candidate_diagnostics["invalid_cell_count"] += len(slot_conflicts)

        missing_coordinate_keys = sorted(set(requested_coordinates_by_key) - returned_coordinate_keys)
        if missing_coordinate_keys:
            missing_coordinates = [
                requested_coordinates_by_key[key]
                for key in missing_coordinate_keys
            ]
            warnings.append(
                "Step3 응답 value_grid에 요청 selected_slot 좌표가 누락되었습니다: "
                f"{to_compact_json(missing_coordinates)}: {adjustment.candidate_key}",
            )

        candidate_diagnostics["valid_cell_count"] = len(value_grid)
        candidate_diagnostics["missing_cell_count"] = len(missing_coordinate_keys)
        diagnostics["by_candidate"][adjustment.candidate_key] = candidate_diagnostics
        for field_name in (
            "selected_cell_count",
            "returned_cell_count",
            "valid_cell_count",
            "missing_cell_count",
            "invalid_cell_count",
        ):
            diagnostics[field_name] += candidate_diagnostics[field_name]

        selected = bool(value_grid)
        if not selected:
            reason = "명확한 value_grid 좌표/제안값이 없어 selected=false로 보정했습니다."
            warnings.append(f"{reason}: {adjustment.candidate_key}")

        patched = ParameterAdjustment(
            candidate_key=adjustment.candidate_key,
            model_file=str(candidate.get("model_file") or ""),
            model_sheet=str(candidate.get("model_sheet") or ""),
            parameter_name=str(
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
                or "",
            ),
            selected=selected,
            slot_axes=slot_axes,
            value_grid=value_grid if selected else [],
            parameter_selection_rationale_ko=adjustment.rationale_ko,
        )
        sanitized.append(patched.model_dump())

    missing_candidate_keys = sorted(set(candidate_by_key) - returned_candidate_keys)
    for candidate_key in missing_candidate_keys:
        candidate = candidate_by_key[candidate_key]
        reason = (
            "LLM Step3 응답에 candidate_key가 누락되어 서버가 selected=false "
            "검토 항목으로 보강했습니다."
        )
        slot_axes = [
            *_slot_axes_for_candidate(slots_by_key.get(candidate_key, [])),
        ]
        sanitized.append(
            ParameterAdjustment(
                candidate_key=candidate_key,
                model_file=str(candidate.get("model_file") or ""),
                model_sheet=str(candidate.get("model_sheet") or ""),
                parameter_name=str(
                    candidate.get("canonical_parameter_name")
                    or candidate.get("parameter_name")
                    or "",
                ),
                selected=False,
                slot_axes=slot_axes,
                value_grid=[],
                parameter_selection_rationale_ko=reason,
            ).model_dump(),
        )
        warnings.append(f"{reason}: {candidate_key}")
        missing_count = len(_requested_slot_coordinates(slots_by_key.get(candidate_key, [])))
        candidate_diagnostics = {
            "selected_cell_count": missing_count,
            "returned_cell_count": 0,
            "valid_cell_count": 0,
            "missing_cell_count": missing_count,
            "invalid_cell_count": 0,
        }
        diagnostics["by_candidate"][candidate_key] = candidate_diagnostics
        diagnostics["selected_cell_count"] += missing_count
        diagnostics["missing_cell_count"] += missing_count
    return sanitized, warnings, diagnostics


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
    candidates = [
        (current_year if month >= current_month else current_year + 1, month)
        for month in months
    ]
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
        _nearest_current_or_future_month(_month_only_candidates(scenario_text))
        if scenario_explicit is None
        else None
    )
    if scenario_month is not None:
        return (*scenario_month, "scenario에 명시된 월-only를 현재 이후 연월로 변환")

    event_month = (
        _nearest_current_or_future_month(_month_only_candidates(event_text))
        if event_explicit is None
        else None
    )
    if event_month is not None:
        return (*event_month, "event에 명시된 월-only를 현재 이후 연월로 변환")

    current_year, current_month = _current_year_month()
    return current_year, current_month, "명확한 연월 근거가 없어 현재 월부터 전개"


def _patch_basecase_value(
    cell: ParameterValueCell,
    basecase_by_reference_id: dict[str, dict[str, Any]],
) -> tuple[ParameterValueCell, str | None]:
    if cell.basecase_value is not None or not cell.basecase_reference_ids:
        return cell, None
    matched_records = [
        basecase_by_reference_id[reference_id]
        for reference_id in cell.basecase_reference_ids
        if reference_id in basecase_by_reference_id
    ]
    if not matched_records:
        return cell, None
    cell_coordinate_key = _canonical_coordinate_key(cell.coordinates)
    exact_matches = [
        record
        for record in matched_records
        if _canonical_coordinate_key(record.get("axes") or {}) == cell_coordinate_key
    ]
    if len(exact_matches) == 1:
        return (
            cell.model_copy(update={"basecase_value": exact_matches[0].get("value")}),
            None,
        )
    if not exact_matches:
        return cell, (
            "참고 basecase record 좌표가 value cell 좌표와 일치하지 않아 "
            "basecaseValue를 채우지 않았습니다"
        )
    return cell, (
        "value cell 좌표와 일치하는 basecase record가 여러 건이라 "
        "basecaseValue를 채우지 않았습니다"
    )


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
                candidate.get("canonical_parameter_name")
                or candidate.get("parameter_name")
                or "",
            ),
            selected=False,
            slot_axes=[],
            value_grid=[],
            parameter_selection_rationale_ko=reason,
        ).model_dump()
        for candidate in candidates
    ]
