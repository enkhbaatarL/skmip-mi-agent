from __future__ import annotations

from typing import Any, Literal, NoReturn

from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.agents.model_parameter_agent.schemas.api.parameters import ProposalParameter
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    is_proposal_parameter_allowed,
    match_v4_parameter_candidates_from_rows,
    partition_proposal_parameter_candidates,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode


V4_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"
V4_NO_CHANGE_TITLE = "파라미터로 반영할 변경 항목이 없습니다."
V4_NO_MODEL_INPUT_TITLE = "파라미터를 적용할 모델 입력 위치를 찾지 못했습니다."
V4_NO_PARAMETER_VALUE_TITLE = "적용할 파라미터 값을 생성하지 못했습니다."
V4_FAILURE_DETAIL_MAX_LENGTH = 300
V4_CANDIDATE_CONFIGURATION_ERROR_CODES = {"ACTIVE_PARAMETER_DEFINITION_MISSING"}
V4_PARAMETER_PUBLIC_LABELS = {
    "GDP": "GDP",
    "PMI": "PMI",
    "PowerMix": "발전원 구성",
    "Temperature": "기온",
    "Population": "인구",
    "User-Adjusted Gas Demand": "사용자 조정 가스 수요",
    "HurricaneIntensity": "허리케인 강도",
    "LiqProdAdjustment": "액화설비 생산량",
    "LiqUtilAdjustment": "액화설비 가동률",
    "PipelineAdjustment": "파이프라인 공급량",
    "RegasAdjustment": "재기화 처리량",
    "SupplyDisruption": "상류 가스 공급량",
    "PNG Contract Volume": "PNG 계약 물량",
    "RemainingUnrestrictedAmount": "잔여 비제한 물량",
    "ShippingCost": "해상 운송비",
    "VolumeCancelled": "취소 물량",
}

V4SemanticEmptyStage = Literal[
    "candidate_generation",
    "step1_5",
    "step2",
    "step3",
]


class ModelParameterSemanticEmptyError(MIBaseError):
    """V4의 의미상 빈 결과를 현업용 두 줄 메시지로 전달합니다."""

    def __init__(self, *, title: str, detail: str) -> None:
        normalized_detail = " ".join(str(detail or "").split())
        if not normalized_detail:
            normalized_detail = "처리 결과를 수급모델 파라미터 제안으로 확정하지 못했습니다."
        if len(normalized_detail) > V4_FAILURE_DETAIL_MAX_LENGTH:
            normalized_detail = normalized_detail[: V4_FAILURE_DETAIL_MAX_LENGTH - 1].rstrip() + "…"
        public_message = f"{title}\n{normalized_detail}"
        super().__init__(ErrorCode.INVALID_REQUEST)
        self.error_message = public_message
        self.args = (public_message,)


def _scenario_context_from_state(
    state: ModelParameterProposalState | dict[str, Any],
) -> dict[str, Any]:
    context = (
        state.scenario_context if isinstance(state, ModelParameterProposalState) else state.get("scenario_context")
    )
    return context if isinstance(context, dict) else {}


def _is_v4_scenario_context(scenario_context: dict[str, Any] | None) -> bool:
    scenario_group = (scenario_context or {}).get("scenario_group") or {}
    return str(scenario_group.get("generation_strategy") or "") == V4_GENERATION_STRATEGY


def _public_lever_scope(items: list[dict[str, Any]]) -> str | None:
    labels: list[str] = []
    forbidden_fragments = (
        "candidate_key",
        "candidatekey",
        "slot_key",
        "slotkey",
        "scenario_id",
        "scenarioid",
        "event_id",
        "eventid",
    )
    for item in items:
        if not isinstance(item, dict):
            continue
        label = " ".join(str(item.get("lever_label") or "").split())
        if not label or any(fragment in label.lower() for fragment in forbidden_fragments):
            continue
        if len(label) > 80:
            label = label[:79].rstrip() + "…"
        if label not in labels:
            labels.append(label)
        if len(labels) == 2:
            break
    if not labels:
        return None
    return "·".join(labels)


def _candidate_exclusion_reason_codes(non_input_items: list[dict[str, Any]]) -> set[str]:
    return {
        str(item.get("reason_code") or "").strip()
        for item in non_input_items
        if isinstance(item, dict) and str(item.get("reason_code") or "").strip()
    }


def _public_parameter_scope(candidates: list[dict[str, Any]]) -> str | None:
    parameter_names: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        parameter_name = " ".join(
            str(candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "").split(),
        )
        if parameter_name and parameter_name not in parameter_names:
            parameter_names.append(parameter_name)
    if {"LiqUtilAdjustment", "LiqProdAdjustment"} <= set(parameter_names):
        return "액화설비 가동률과 생산량"

    labels: list[str] = []
    for parameter_name in parameter_names[:3]:
        label = V4_PARAMETER_PUBLIC_LABELS.get(parameter_name, parameter_name)
        if len(label) > 60:
            label = label[:59].rstrip() + "…"
        labels.append(label)
    if not labels:
        return None
    suffix = " 등" if len(parameter_names) > len(labels) else ""
    return "·".join(labels) + suffix


def _v4_semantic_empty_detail(
    *,
    stage: V4SemanticEmptyStage,
    candidates: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
) -> tuple[str, str]:
    lever_scope = _public_lever_scope(candidates or non_input_items)
    parameter_scope = _public_parameter_scope(candidates)
    if stage == "candidate_generation":
        reason_codes = _candidate_exclusion_reason_codes(non_input_items)
        if reason_codes and reason_codes <= {"UNCHANGED_LEVER_STATE"}:
            subject = f"{lever_scope} 영향 항목은" if lever_scope else "선택된 모델 영향 항목은"
            return (
                V4_NO_CHANGE_TITLE,
                f'{subject} 확인했지만, 변화 방향이 모두 "변화 없음"으로 설정되어 '
                "수급모델에 반영할 변경 항목이 없습니다.",
            )
        return (
            V4_NO_CHANGE_TITLE,
            "이벤트와 시나리오 분기값을 확인했지만, 현재 활성화된 수급모델 파라미터와 연결되는 변경 항목이 없습니다.",
        )
    if stage == "step1_5":
        if parameter_scope:
            subject = f"{parameter_scope} 파라미터 후보는"
        elif lever_scope:
            subject = f"{lever_scope} 관련 파라미터 후보는"
        else:
            subject = "수급모델 파라미터 후보는"
        return (
            V4_NO_CHANGE_TITLE,
            f"{subject} 확인했지만, 시나리오·이벤트 근거와 파라미터 적용 조건을 함께 "
            "충족하는 항목을 확정하지 못했습니다.",
        )
    if stage == "step2":
        if parameter_scope:
            subject = f"{parameter_scope} 파라미터는"
        elif lever_scope:
            subject = f"{lever_scope} 관련 파라미터는"
        else:
            subject = "관련 파라미터는"
        return (
            V4_NO_MODEL_INPUT_TITLE,
            f"{subject} 확인했지만, 해당 대상과 적용 기간에 대응하는 모델 입력 위치가 없습니다.",
        )
    if parameter_scope:
        subject = f"{parameter_scope} 파라미터와"
    elif lever_scope:
        subject = f"{lever_scope} 관련 파라미터와"
    else:
        subject = "관련 파라미터와"
    return (
        V4_NO_PARAMETER_VALUE_TITLE,
        f"{subject} 모델 입력 위치는 확인했지만, 시나리오·이벤트 근거와 기준값에 부합하는 "
        "유효한 적용 수치를 생성하지 못했습니다.",
    )


def _raise_v4_semantic_empty_if_applicable(
    *,
    stage: V4SemanticEmptyStage,
    scenario_context: dict[str, Any] | None,
    candidates: list[dict[str, Any]] | None = None,
    non_input_items: list[dict[str, Any]] | None = None,
) -> None:
    if not _is_v4_scenario_context(scenario_context):
        return
    reason_codes = sorted(_candidate_exclusion_reason_codes(non_input_items or []))
    logger.warning(
        "[model-parameter] v4 semantic empty result | stage={} candidate_count={} exclusion_reason_codes={}",
        stage,
        len(candidates or []),
        reason_codes,
    )
    if stage == "candidate_generation" and set(reason_codes) & V4_CANDIDATE_CONFIGURATION_ERROR_CODES:
        return
    title, detail = _v4_semantic_empty_detail(
        stage=stage,
        candidates=candidates or [],
        non_input_items=non_input_items or [],
    )
    raise ModelParameterSemanticEmptyError(title=title, detail=detail)


def _route_after_candidate_validation(state: ModelParameterProposalState | dict[str, Any]) -> str:
    candidates = (
        state.candidate_mappings
        if isinstance(state, ModelParameterProposalState)
        else state.get("candidate_mappings") or []
    )
    if candidates:
        return "load_basecase_samples"
    _raise_no_mapping_candidates(state)


def _route_after_basecase_filter(state: ModelParameterProposalState | dict[str, Any]) -> str:
    slots = (
        state.parameter_slots if isinstance(state, ModelParameterProposalState) else state.get("parameter_slots") or []
    )
    selected_slots = [slot for slot in slots if slot.get("selected", True) is not False]
    if selected_slots:
        return "propose_parameter_values"
    return "finalize_empty_parameter_values"


def _scenario_id_from_state(state: ModelParameterProposalState | dict[str, Any]) -> Any:
    if isinstance(state, ModelParameterProposalState):
        return state.scenario_id
    return state.get("scenario_id")


def _raise_no_mapping_candidates(state: ModelParameterProposalState | dict[str, Any]) -> NoReturn:
    scenario_id = _scenario_id_from_state(state)
    non_input_items = (
        state.non_input_items if isinstance(state, ModelParameterProposalState) else state.get("non_input_items") or []
    )
    reason_codes = sorted(
        {
            str(item.get("reason_code") or "")
            for item in non_input_items
            if isinstance(item, dict) and str(item.get("reason_code") or "")
        },
    )
    _raise_v4_semantic_empty_if_applicable(
        stage="candidate_generation",
        scenario_context=_scenario_context_from_state(state),
        non_input_items=non_input_items,
    )
    reason_detail = f"; exclusion_reason_codes={reason_codes}" if reason_codes else ""
    raise MIBaseError(
        ErrorCode.INVALID_REQUEST,
        detail=(f"No model parameter mapping candidates found for scenario_id={scenario_id}{reason_detail}"),
    )


def _ensure_mapping_candidates(data: dict[str, Any]) -> None:
    if not data.get("candidate_mappings"):
        _raise_no_mapping_candidates(data)


def _raise_no_proposal_parameters(
    data: dict[str, Any],
    *,
    reason: str | None = None,
) -> NoReturn:
    adjustments = data.get("parameter_adjustments") or []
    has_step3_input = bool(data.get("parameter_slots") or data.get("effective_references")) or any(
        isinstance(adjustment, dict) and adjustment.get("selected", True) is not False for adjustment in adjustments
    )
    _raise_v4_semantic_empty_if_applicable(
        stage="step3" if has_step3_input else "step2",
        scenario_context=_scenario_context_from_state(data),
        candidates=data.get("slot_candidate_mappings") or data.get("candidate_mappings") or [],
        non_input_items=data.get("non_input_items") or [],
    )
    scenario_id = _scenario_id_from_state(data)
    detail = f"No valid model parameter proposal parameters generated for scenario_id={scenario_id}"
    if reason:
        detail = f"{detail}: {reason}"
    raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def _ensure_proposal_parameters(
    data: dict[str, Any],
    proposal_parameters: list[ProposalParameter],
) -> None:
    if proposal_parameters:
        return
    warnings = [str(warning) for warning in (data.get("validation_warnings") or []) if str(warning).strip()]
    _raise_no_proposal_parameters(
        data,
        reason="; ".join(warnings[-3:]) if warnings else None,
    )


def _normalize_key(value: Any) -> str:
    return str(value or "").strip()


def _event_type_l2_id_from_context(scenario_context: dict[str, Any]) -> int | None:
    scenario_group = scenario_context.get("scenario_group") or {}
    event_type = scenario_context.get("event_type") or {}
    raw_value = (
        scenario_group.get("event_type_l2_id") or event_type.get("event_type_l2_id") or event_type.get("level_2_id")
    )
    if raw_value is None:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def _scenario_dimension_keys(scenario_context: dict[str, Any]) -> set[str]:
    scenario = scenario_context.get("scenario") or {}
    dimension_values = scenario.get("dimension_values")
    if not isinstance(dimension_values, dict):
        return set()
    return {_normalize_key(key) for key in dimension_values if _normalize_key(key)}


def _parameter_definitions_by_name(
    parameter_definitions: list[dict[str, Any]],
) -> set[str]:
    return {
        _normalize_key(
            definition.get("canonical_parameter_name") or definition.get("parameter_name"),
        )
        for definition in parameter_definitions
        if _normalize_key(
            definition.get("canonical_parameter_name") or definition.get("parameter_name"),
        )
        and _normalize_key(definition.get("model_file"))
        and _normalize_key(definition.get("model_sheet"))
    }


def _has_mapping_candidates_from_db_rows(  # noqa: C901
    *,
    scenario_context: dict[str, Any],
) -> bool:
    resources = scenario_context.get("parameter_mapping_resources") or {}
    mapping_rules = resources.get("mapping_rules") or []
    parameter_definitions = resources.get("parameter_definitions") or []
    scenario_group = scenario_context.get("scenario_group") or {}
    strategy = str(scenario_group.get("generation_strategy") or "")
    if strategy == V4_GENERATION_STRATEGY:
        if not parameter_definitions:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="active parameter definitions not loaded from DB for v4",
            )
        candidates, _, _ = match_v4_parameter_candidates_from_rows(
            parameter_rows=parameter_definitions,
            scenario_context=scenario_context,
        )
        candidates, _ = partition_proposal_parameter_candidates(candidates)
        return bool(candidates)
    if not mapping_rules or not parameter_definitions:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="parameter mapping resources not loaded from DB",
        )

    parameter_names = _parameter_definitions_by_name(parameter_definitions)
    if not parameter_names:
        return False

    is_v3 = str(scenario_group.get("generation_strategy") or "") == "multi_event_composite_dimensions"
    if is_v3:
        source_pairs = {
            (
                int(mapped_source["event_type_l2_id"]),
                _normalize_key(mapped_source.get("mapping_dimension_key")),
            )
            for lineage in scenario_context.get("dimension_lineage") or []
            if isinstance(lineage, dict)
            for mapped_source in lineage.get("mapped_sources") or []
            if isinstance(mapped_source, dict)
            and mapped_source.get("event_type_l2_id") is not None
            and _normalize_key(mapped_source.get("mapping_dimension_key"))
        }
        if not source_pairs:
            return False
    else:
        event_type_l2_id = _event_type_l2_id_from_context(scenario_context)
        dimension_keys = _scenario_dimension_keys(scenario_context)
        if event_type_l2_id is None or not dimension_keys:
            return False

    for rule in mapping_rules:
        if str(rule.get("mapping_method") or "").strip() not in {"direct", "routing"}:
            continue
        try:
            rule_event_type_l2_id = int(rule.get("event_type_l2_id"))
        except (TypeError, ValueError):
            continue
        rule_dimension_key = _normalize_key(rule.get("dimension_key"))
        if is_v3:
            if (rule_event_type_l2_id, rule_dimension_key) not in source_pairs:
                continue
        else:
            if rule_event_type_l2_id != event_type_l2_id:
                continue
            if rule_dimension_key not in dimension_keys:
                continue
        parameter_name = _normalize_key(
            rule.get("canonical_parameter_name") or rule.get("parameter_name"),
        )
        if parameter_name in parameter_names and is_proposal_parameter_allowed(parameter_name):
            return True
    return False


def _ensure_context_has_mapping_candidates(
    *,
    scenario_id: int,
    scenario_context: dict[str, Any],
) -> None:
    scenario_group = scenario_context.get("scenario_group") or {}
    strategy = str(scenario_group.get("generation_strategy") or "")
    preflight_non_inputs: list[dict[str, Any]] = []
    if strategy == V4_GENERATION_STRATEGY:
        resources = scenario_context.get("parameter_mapping_resources") or {}
        parameter_definitions = resources.get("parameter_definitions") or []
        if not parameter_definitions:
            raise MIBaseError(
                ErrorCode.INVALID_REQUEST,
                detail="active parameter definitions not loaded from DB for v4",
            )
        raw_candidates, preflight_non_inputs, _ = match_v4_parameter_candidates_from_rows(
            parameter_rows=parameter_definitions,
            scenario_context=scenario_context,
        )
        candidates, scope_exclusions = partition_proposal_parameter_candidates(
            raw_candidates,
        )
        preflight_non_inputs = [*preflight_non_inputs, *scope_exclusions]
        has_candidates = bool(candidates)
    else:
        has_candidates = _has_mapping_candidates_from_db_rows(
            scenario_context=scenario_context,
        )
    if has_candidates:
        return
    logger.warning(
        "[model-parameter] no DB mapping candidates before callback accept | scenario_id={}",
        scenario_id,
    )
    reason_codes = scenario_context.get("candidate_exclusion_reason_codes") or []
    _raise_no_mapping_candidates(
        {
            "scenario_id": scenario_id,
            "scenario_context": scenario_context,
            "non_input_items": [
                *preflight_non_inputs,
                *[{"reason_code": reason_code} for reason_code in reason_codes if reason_code],
            ],
        },
    )
