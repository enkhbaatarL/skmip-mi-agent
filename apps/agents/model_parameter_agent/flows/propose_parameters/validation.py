from __future__ import annotations

from typing import Any, Literal, NoReturn

from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.agents.model_parameter_agent.schemas.api.parameters import ProposalParameter
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    is_proposal_parameter_allowed,
    match_v4_parameter_candidates_from_rows,
    partition_proposal_parameter_candidates,
)
from apps.agents.model_parameter_agent.utils.proposal_policy import (
    has_specific_time_evidence,
    is_v4_contract_context,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode


V4_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"
V4_NO_CHANGE_TITLE = "파라미터로 반영할 변경 항목이 없습니다."
V4_NO_MODEL_INPUT_TITLE = "파라미터를 적용할 위치를 찾지 못했습니다."
V4_NO_PARAMETER_VALUE_TITLE = "적용할 파라미터 값을 생성하지 못했습니다."
V4_FAILURE_DETAIL_MAX_LENGTH = 300
V4_CANDIDATE_CONFIGURATION_ERROR_CODES = {"ACTIVE_PARAMETER_DEFINITION_MISSING"}
ABSTAINED_OUT_OF_PROPOSAL_SCOPE = "ABSTAINED_OUT_OF_PROPOSAL_SCOPE"
ABSTAINED_INSUFFICIENT_EVIDENCE = "ABSTAINED_INSUFFICIENT_EVIDENCE"
ABSTAINED_MODEL_INPUT_NOT_FOUND = "ABSTAINED_MODEL_INPUT_NOT_FOUND"
ABSTAINED_VALUE_NOT_GENERATED = "ABSTAINED_VALUE_NOT_GENERATED"
ABSTAINED_VALUE_OUT_OF_RANGE = "ABSTAINED_VALUE_OUT_OF_RANGE"
ABSTAINED_NO_CHANGE = "ABSTAINED_NO_CHANGE"
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
V4Step2FailureKind = Literal[
    "catalog_unavailable",
    "selection_empty",
    "selection_invalid",
    "exact_mismatch",
    "policy_excluded",
    "unknown",
]

_V4_UNSPECIFIED_CONTEXT_VALUES = frozenset(
    {
        "-",
        "n/a",
        "na",
        "none",
        "unknown",
        "미상",
        "미정",
        "불명",
    },
)
_V4_GENERIC_SCOPE_VALUES = frozenset(
    {
        "all",
        "facility",
        "global",
        "global lng market",
        "local",
        "market",
        "plant",
        "region",
        "regional",
        "관련 시장",
        "관련 시장 범위",
        "글로벌",
        "글로벌 lng 시장",
        "설비",
        "시장",
        "전 세계",
        "전세계",
        "지역",
    },
)


class ModelParameterSemanticEmptyError(MIBaseError):
    """V4의 정상적인 미제안 결과를 구조화해 전달합니다."""

    def __init__(
        self,
        *,
        reason_code: str,
        stage: V4SemanticEmptyStage,
        title: str,
        detail: str,
    ) -> None:
        normalized_detail = " ".join(str(detail or "").split())
        if not normalized_detail:
            normalized_detail = "제안할 값을 정할 수 있는 충분한 근거를 찾지 못했습니다."
        if len(normalized_detail) > V4_FAILURE_DETAIL_MAX_LENGTH:
            normalized_detail = normalized_detail[: V4_FAILURE_DETAIL_MAX_LENGTH - 1].rstrip() + "…"
        public_message = f"{title}\n{normalized_detail}"
        super().__init__(ErrorCode.INVALID_REQUEST)
        self.reason_code = reason_code
        self.stage = stage
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
    return is_v4_contract_context(scenario_context)


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


def _normalized_context_text(value: Any) -> str | None:
    text = " ".join(str(value or "").split())
    if not text or text.casefold() in _V4_UNSPECIFIED_CONTEXT_VALUES:
        return None
    return text


def _candidate_context_values(
    candidates: list[dict[str, Any]],
    *field_names: str,
) -> list[str]:
    values: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        sources = [candidate]
        for collection_name in ("source_dimensions", "lever_provenance"):
            sources.extend(
                item
                for item in candidate.get(collection_name) or []
                if isinstance(item, dict)
            )
        for source in sources:
            for field_name in field_names:
                text = _normalized_context_text(source.get(field_name))
                if text and text not in values:
                    values.append(text)
    return values


def _has_specific_scope_context(candidates: list[dict[str, Any]]) -> bool:
    return any(
        value.casefold() not in _V4_GENERIC_SCOPE_VALUES
        for value in _candidate_context_values(candidates, "scope", "lever_scope")
    )


def _time_context_status(candidates: list[dict[str, Any]]) -> tuple[bool, bool]:
    values = _candidate_context_values(
        candidates,
        "time_window",
        "lever_time_window",
    )
    return bool(values), any(has_specific_time_evidence(value) for value in values)


def _selectable_slot_catalog_candidate_count(
    slot_catalog: list[dict[str, Any]],
) -> int:
    return sum(
        1
        for item in slot_catalog
        if isinstance(item, dict)
        and bool(item.get("fixed_axis_hierarchy") or item.get("leaves"))
    )


def _diagnostic_count(
    diagnostics: dict[str, int],
    field_name: str,
) -> int | None:
    value = diagnostics.get(field_name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _step2_failure_kind(
    *,
    slot_catalog: list[dict[str, Any]],
    diagnostics: dict[str, int],
) -> V4Step2FailureKind:
    catalog_count = _diagnostic_count(
        diagnostics,
        "catalog_candidate_count",
    )
    catalog_observed = catalog_count is not None or bool(slot_catalog)
    if catalog_count is None:
        catalog_count = _selectable_slot_catalog_candidate_count(slot_catalog)
    if catalog_observed and catalog_count == 0:
        return "catalog_unavailable"

    raw_slot_count = _diagnostic_count(diagnostics, "raw_slot_count")
    sanitized_slot_count = _diagnostic_count(
        diagnostics,
        "sanitized_slot_count",
    )
    exact_slot_count = _diagnostic_count(diagnostics, "exact_slot_count")
    if raw_slot_count == 0:
        return "selection_empty"
    if raw_slot_count is not None and sanitized_slot_count == 0:
        return "selection_invalid"
    policy_excluded_slot_count = _diagnostic_count(
        diagnostics,
        "policy_excluded_slot_count",
    )
    if (
        sanitized_slot_count is not None
        and sanitized_slot_count > 0
        and exact_slot_count == 0
        and policy_excluded_slot_count is not None
        and policy_excluded_slot_count > 0
    ):
        return "policy_excluded"
    if sanitized_slot_count is not None and sanitized_slot_count > 0 and exact_slot_count == 0:
        return "exact_mismatch"
    return "unknown"


def _public_fixed_axis_label(axis_name: str) -> str:
    normalized = axis_name.casefold()
    if "train" in normalized:
        return "트레인"
    if "plant" in normalized or "facility" in normalized or "terminal" in normalized:
        return "설비"
    if "country" in normalized:
        return "국가"
    if "region" in normalized:
        return "지역"
    if "generation" in normalized or "fuel" in normalized:
        return "발전원"
    return "세부 대상"


def _step2_axis_guidance(
    slot_catalog: list[dict[str, Any]],
) -> tuple[str, str]:
    fixed_axis_labels: list[str] = []
    time_axis_names: set[str] = set()
    for item in slot_catalog:
        if not isinstance(item, dict):
            continue
        for axis_name in item.get("fixed_axis_names") or []:
            label = _public_fixed_axis_label(str(axis_name))
            if label not in fixed_axis_labels:
                fixed_axis_labels.append(label)
        time_axis_names.update(
            str(axis_name).casefold()
            for axis_name in item.get("time_axis_names") or []
        )

    target_hint = "적용 대상"
    if fixed_axis_labels:
        target_hint = "·".join(fixed_axis_labels[:3])

    if {"year", "month"} <= time_axis_names:
        time_hint = "적용 연도·월(또는 시작·종료 기간)"
    elif "year" in time_axis_names:
        time_hint = "적용 연도"
    elif "month" in time_axis_names:
        time_hint = "적용 월"
    elif "period" in time_axis_names:
        time_hint = "적용 기간"
    else:
        time_hint = "적용 시점"
    return target_hint, time_hint


def _v4_step2_empty_detail(
    *,
    subject: str,
    candidates: list[dict[str, Any]],
    slot_catalog: list[dict[str, Any]],
    diagnostics: dict[str, int],
) -> str:
    failure_kind = _step2_failure_kind(
        slot_catalog=slot_catalog,
        diagnostics=diagnostics,
    )
    target_hint, time_hint = _step2_axis_guidance(slot_catalog)
    if failure_kind == "catalog_unavailable":
        return (
            f"{subject} 확인했지만, 현재 입력 가능한 대상·기간 목록에서 일치하는 위치를 찾지 못해 "
            "제안하지 않았습니다. 시나리오의 적용 대상과 기간을 확인해 주세요."
        )
    if failure_kind == "selection_invalid":
        return (
            f"{subject} 확인했지만, 선택된 적용 위치가 파라미터의 대상·기간 조건과 맞지 않아 "
            "제안하지 않았습니다. 시나리오의 적용 대상과 기간을 확인해 주세요."
        )
    if failure_kind == "policy_excluded":
        return (
            f"{subject} 확인했지만, 시나리오 내용만으로 적용할 대상과 기간을 정할 근거가 부족해 "
            f"제안하지 않았습니다. {target_hint}과 {time_hint}을 확인해 주세요."
        )
    if failure_kind == "exact_mismatch":
        return (
            f"{subject} 확인했지만, 시나리오의 대상·기간 조합이 현재 입력 가능한 위치와 일치하지 않아 "
            "제안하지 않았습니다. "
            f"{target_hint}과 {time_hint}이 사용 가능한 범위에 포함되는지 확인해 주세요."
        )
    if failure_kind == "selection_empty":
        has_specific_scope = _has_specific_scope_context(candidates)
        _, has_specific_time = _time_context_status(candidates)
        if has_specific_scope and not has_specific_time:
            return (
                f"{subject} 확인했고 적용 대상도 찾았지만, "
                f"{time_hint}이 명확하지 않아 제안하지 않았습니다. 적용 기간을 확인해 주세요."
            )
        if has_specific_time and not has_specific_scope:
            return (
                f"{subject} 확인했고 적용 기간도 찾았지만, "
                f"{target_hint}이 명확하지 않아 제안하지 않았습니다. 적용 대상을 확인해 주세요."
            )
        if has_specific_scope and has_specific_time:
            return (
                f"{subject} 확인했고 적용 대상과 기간도 찾았지만, 현재 입력 가능한 위치와 정확히 연결하지 못해 "
                f"제안하지 않았습니다. {target_hint}과 {time_hint}이 사용 가능한 범위와 맞는지 확인해 주세요."
            )
        return (
            f"{subject} 확인했지만, 적용 대상과 기간이 충분히 구체적이지 않아 제안하지 않았습니다. "
            f"{target_hint}과 {time_hint}을 확인해 주세요."
        )
    return (
        f"{subject} 확인했지만, 시나리오 내용만으로 적용할 위치를 확정할 근거가 부족해 제안하지 않았습니다. "
        f"{target_hint}과 {time_hint}을 확인해 주세요."
    )


def _public_scope_subject(
    *,
    parameter_scope: str | None,
    lever_scope: str | None,
    parameter_suffix: str,
    lever_suffix: str,
    default: str,
) -> str:
    if parameter_scope:
        return f"{parameter_scope}{parameter_suffix}"
    if lever_scope:
        return f"{lever_scope}{lever_suffix}"
    return default


def _v4_semantic_empty_detail(
    *,
    stage: V4SemanticEmptyStage,
    candidates: list[dict[str, Any]],
    non_input_items: list[dict[str, Any]],
    slot_catalog: list[dict[str, Any]],
    slot_selection_diagnostics: dict[str, int],
    value_selection_diagnostics: dict[str, int],
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
        if "PROPOSAL_SCOPE_EXCLUDED" in reason_codes:
            return (
                V4_NO_CHANGE_TITLE,
                "시나리오에서 변경 가능성이 있는 항목을 확인했지만, 현재 자동 제안 대상에 "
                "포함되지 않아 제안에서 제외했습니다.",
            )
        return (
            V4_NO_CHANGE_TITLE,
            "이벤트와 선택한 시나리오 조건을 확인했지만, 현재 자동 제안 가능한 파라미터와 "
            "연결되는 변경 항목이 없습니다.",
        )
    if stage == "step1_5":
        subject = _public_scope_subject(
            parameter_scope=parameter_scope,
            lever_scope=lever_scope,
            parameter_suffix=" 관련 항목은",
            lever_suffix=" 관련 항목은",
            default="변경 가능성이 있는 항목은",
        )
        return (
            V4_NO_CHANGE_TITLE,
            f"{subject} 확인했지만, 시나리오와 이벤트 내용만으로 실제 변경이 필요한지 판단할 "
            "근거가 부족해 제안하지 않았습니다.",
        )
    if stage == "step2":
        subject = _public_scope_subject(
            parameter_scope=parameter_scope,
            lever_scope=lever_scope,
            parameter_suffix=" 관련 항목은",
            lever_suffix=" 관련 항목은",
            default="관련 항목은",
        )
        return (
            V4_NO_MODEL_INPUT_TITLE,
            _v4_step2_empty_detail(
                subject=subject,
                candidates=candidates,
                slot_catalog=slot_catalog,
                diagnostics=slot_selection_diagnostics,
            ),
        )
    subject = _public_scope_subject(
        parameter_scope=parameter_scope,
        lever_scope=lever_scope,
        parameter_suffix=" 항목과",
        lever_suffix=" 관련 항목과",
        default="관련 항목과",
    )
    if value_selection_diagnostics.get("out_of_range_value_count", 0) > 0:
        return (
            V4_NO_PARAMETER_VALUE_TITLE,
            f"{subject} 적용 위치는 확인했지만, 생성된 값이 해당 파라미터의 "
            "허용 수치 범위를 벗어나 제안에서 제외했습니다.",
        )
    if (
        value_selection_diagnostics.get("unchanged_value_count", 0) > 0
        and value_selection_diagnostics.get("changed_value_count", 0) == 0
    ):
        return (
            V4_NO_CHANGE_TITLE,
            f"{subject} 적용 위치와 값을 확인했지만, 모든 제안값이 현재 "
            "기준값과 동일해 실제 변경 사항이 없습니다.",
        )
    return (
        V4_NO_PARAMETER_VALUE_TITLE,
        f"{subject} 적용 위치는 확인했지만, 시나리오와 이벤트 내용만으로 기준값에서 얼마나 변경할지 "
        "결정할 근거가 부족해 제안값을 만들지 않았습니다.",
    )


def _v4_semantic_empty_reason_code(
    *,
    stage: V4SemanticEmptyStage,
    non_input_items: list[dict[str, Any]],
    slot_catalog: list[dict[str, Any]],
    slot_selection_diagnostics: dict[str, int],
    value_selection_diagnostics: dict[str, int],
) -> str:
    exclusion_codes = _candidate_exclusion_reason_codes(non_input_items)
    if stage == "candidate_generation":
        if exclusion_codes and exclusion_codes <= {"UNCHANGED_LEVER_STATE"}:
            return ABSTAINED_NO_CHANGE
        return ABSTAINED_OUT_OF_PROPOSAL_SCOPE
    if stage == "step1_5":
        return ABSTAINED_INSUFFICIENT_EVIDENCE
    if stage == "step2":
        if "ABSTAINED_INSUFFICIENT_EVIDENCE" in exclusion_codes:
            return ABSTAINED_INSUFFICIENT_EVIDENCE
        failure_kind = _step2_failure_kind(
            slot_catalog=slot_catalog,
            diagnostics=slot_selection_diagnostics,
        )
        if failure_kind in {"selection_empty", "policy_excluded"}:
            return ABSTAINED_INSUFFICIENT_EVIDENCE
        return ABSTAINED_MODEL_INPUT_NOT_FOUND
    if value_selection_diagnostics.get("out_of_range_value_count", 0) > 0:
        return ABSTAINED_VALUE_OUT_OF_RANGE
    if (
        value_selection_diagnostics.get("unchanged_value_count", 0) > 0
        and value_selection_diagnostics.get("changed_value_count", 0) == 0
    ):
        return ABSTAINED_NO_CHANGE
    return ABSTAINED_VALUE_NOT_GENERATED


def _raise_v4_semantic_empty_if_applicable(
    *,
    stage: V4SemanticEmptyStage,
    scenario_context: dict[str, Any] | None,
    candidates: list[dict[str, Any]] | None = None,
    non_input_items: list[dict[str, Any]] | None = None,
    slot_catalog: list[dict[str, Any]] | None = None,
    slot_selection_diagnostics: dict[str, int] | None = None,
    value_selection_diagnostics: dict[str, int] | None = None,
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
    if stage == "step2" and _step2_failure_kind(
        slot_catalog=slot_catalog or [],
        diagnostics=slot_selection_diagnostics or {},
    ) == "selection_invalid":
        raise MIBaseError(
            ErrorCode.LLM_INVALID_RESPONSE_ERROR,
            detail="선택한 적용 위치가 모두 확인 기준을 통과하지 못했습니다.",
        )
    if (
        stage == "step3"
        and value_selection_diagnostics
        and value_selection_diagnostics.get("generated_value_count", 0) == 0
        and value_selection_diagnostics.get("invalid_response_value_count", 0) > 0
    ):
        raise MIBaseError(
            ErrorCode.LLM_INVALID_RESPONSE_ERROR,
            detail="생성된 제안값이 모두 확인 기준을 통과하지 못했습니다.",
        )
    title, detail = _v4_semantic_empty_detail(
        stage=stage,
        candidates=candidates or [],
        non_input_items=non_input_items or [],
        slot_catalog=slot_catalog or [],
        slot_selection_diagnostics=slot_selection_diagnostics or {},
        value_selection_diagnostics=value_selection_diagnostics or {},
    )
    reason_code = _v4_semantic_empty_reason_code(
        stage=stage,
        non_input_items=non_input_items or [],
        slot_catalog=slot_catalog or [],
        slot_selection_diagnostics=slot_selection_diagnostics or {},
        value_selection_diagnostics=value_selection_diagnostics or {},
    )
    raise ModelParameterSemanticEmptyError(
        reason_code=reason_code,
        stage=stage,
        title=title,
        detail=detail,
    )


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
    if set(reason_codes) & V4_CANDIDATE_CONFIGURATION_ERROR_CODES:
        reason_detail = f"; exclusion_reason_codes={reason_codes}" if reason_codes else ""
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail=(f"No model parameter mapping candidates found for scenario_id={scenario_id}{reason_detail}"),
        )
    raise ModelParameterSemanticEmptyError(
        reason_code=ABSTAINED_OUT_OF_PROPOSAL_SCOPE,
        stage="candidate_generation",
        title=V4_NO_CHANGE_TITLE,
        detail=(
            "이벤트와 선택한 시나리오 조건을 확인했지만, 현재 자동 제안 가능한 파라미터와 "
            "연결되는 변경 항목이 없습니다."
        ),
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
    stage: V4SemanticEmptyStage = "step3" if has_step3_input else "step2"
    _raise_v4_semantic_empty_if_applicable(
        stage=stage,
        scenario_context=_scenario_context_from_state(data),
        candidates=data.get("slot_candidate_mappings") or data.get("candidate_mappings") or [],
        non_input_items=data.get("non_input_items") or [],
        slot_catalog=data.get("slot_catalog") or [],
        slot_selection_diagnostics=data.get("slot_selection_diagnostics") or {},
        value_selection_diagnostics=data.get("value_selection_diagnostics") or {},
    )
    raise ModelParameterSemanticEmptyError(
        reason_code=(
            ABSTAINED_VALUE_NOT_GENERATED
            if has_step3_input
            else ABSTAINED_MODEL_INPUT_NOT_FOUND
        ),
        stage=stage,
        title=(V4_NO_PARAMETER_VALUE_TITLE if has_step3_input else V4_NO_MODEL_INPUT_TITLE),
        detail=(
            "변경 가능성이 있는 항목과 적용 위치는 확인했지만, 시나리오 근거만으로 기준값에서 얼마나 "
            "변경할지 정할 수 없어 제안값을 만들지 않았습니다."
            if has_step3_input
            else "변경 가능성이 있는 항목은 확인했지만, 적용 대상과 기간을 확정할 근거가 부족해 "
            "제안하지 않았습니다."
        ),
    )


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
    if _is_v4_scenario_context(scenario_context):
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
    if strategy == V4_GENERATION_STRATEGY:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="multi_event_model_lever_dimensions requires scenario_group.api_version=v4",
        )
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
    if _is_v4_scenario_context(scenario_context):
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
    elif strategy == V4_GENERATION_STRATEGY:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="multi_event_model_lever_dimensions requires scenario_group.api_version=v4",
        )
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
