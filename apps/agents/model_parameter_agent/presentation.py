from __future__ import annotations

import json
import re
from typing import Any

from apps.agents.model_parameter_agent.flows.propose_parameters.api_schema import (
    ProposeParametersCallbackData,
    ProposeParametersCallbackOut,
    ProposeParametersData,
)
from apps.agents.model_parameter_agent.schemas.api.parameters import (
    ModelParameterTarget,
    ProposalParameter,
)
from apps.agents.model_parameter_agent.utils.basecase import (
    basecase_slot_axis_names_from_candidate,
    basecase_value_field_name_from_candidate,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


def _slot_from_axes(slot_axes: list[dict[str, Any]]) -> dict[str, Any]:
    slot: dict[str, Any] = {}
    for axis in slot_axes or []:
        axis_name = axis.get("axis_name")
        if not axis_name:
            continue
        slot[str(axis_name)] = axis.get("axis_value")
    return slot


def _append_unique(items: list[str], value: Any) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _value_rationale(cell: dict[str, Any]) -> str:
    rationale = str(cell.get("rationale_ko") or "").strip()
    if rationale:
        return rationale
    parts: list[str] = []
    _append_unique(parts, cell.get("value_selection_rationale_ko"))
    _append_unique(parts, cell.get("proposed_value_rationale_ko"))
    return " ".join(parts) or "값 선택 및 제안 근거가 제공되지 않았습니다."


def _value_key(value: dict[str, Any]) -> str:
    return json.dumps(
        {key: item for key, item in value.items() if key != "rationale"},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _axis_value_key(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text.lower()
    if number.is_integer():
        return int(number)
    return number


def _slot_value_key(value: dict[str, Any], axes: list[str]) -> str:
    return json.dumps(
        {axis_name: _axis_value_key(value.get(axis_name)) for axis_name in axes},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _value_field_for(
    adjustment: dict[str, Any],
    candidate_index: dict[str, dict[str, Any]],
) -> str:
    candidate_key = str(adjustment.get("candidate_key") or "")
    candidate = candidate_index.get(candidate_key) or {}
    value_field_name = basecase_value_field_name_from_candidate(candidate)
    if value_field_name:
        return value_field_name
    return str(adjustment.get("parameter_name") or "")


def _field_key(value: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(value or "")).lower()


def _column_role_names(raw: Any) -> list[str]:
    names: list[str] = []
    for part in str(raw or "").split(","):
        if ":" not in part:
            continue
        _, role = part.split(":", 1)
        role_name = str(role or "").strip()
        if role_name:
            _append_unique(names, role_name)
    return names


def _allowed_slot_axes_for_candidate(
    candidate: dict[str, Any],
    value_field_name: str,
) -> list[str]:
    axes = basecase_slot_axis_names_from_candidate(candidate)
    if axes:
        return axes

    value_field_key = _field_key(value_field_name)
    axes: list[str] = []
    for role_name in _column_role_names(candidate.get("basecase_column_roles")):
        if _field_key(role_name) == value_field_key:
            continue
        _append_unique(axes, role_name)
    if str(candidate.get("basecase_read_mode") or "").lower() == "matrix_time_columns":
        for axis_name in ("Year", "Month", "Period"):
            _append_unique(axes, axis_name)
    return axes


def _canonical_slot_axis_name(axis_name: str, allowed_axes: list[str]) -> str | None:
    axis_key = _field_key(axis_name)
    if not axis_key:
        return None
    if not allowed_axes:
        return axis_name

    allowed_by_key = {_field_key(axis): axis for axis in allowed_axes}
    if axis_key in allowed_by_key:
        return allowed_by_key[axis_key]

    country_axes = [
        axis for axis in allowed_axes
        if _field_key(axis).endswith("country")
    ]
    if axis_key in {"country", "province"} and len(country_axes) == 1:
        return country_axes[0]
    for axis in country_axes:
        if _field_key(axis) == f"{axis_key}country":
            return axis
    return None


def _normalize_slot_coordinates(
    slot: dict[str, Any],
    allowed_axes: list[str],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for axis_name, axis_value in (slot or {}).items():
        canonical_axis = _canonical_slot_axis_name(str(axis_name), allowed_axes)
        if canonical_axis is None:
            continue
        normalized[canonical_axis] = axis_value
    return normalized


def _finalize_group_values(
    group: dict[str, Any],
    *,
    include_lut_value: bool,
) -> None:
    axes = group["slot_axes_field_names"]
    finalized_values: list[dict[str, Any]] = []
    slot_index: dict[str, int] = {}
    for value in group["values"]:
        finalized = {axis_name: value.get(axis_name) for axis_name in axes}
        finalized["basecaseValue"] = value.get("basecaseValue")
        if include_lut_value:
            finalized["lutValue"] = value.get("lutValue")
        finalized["proposedValue"] = value.get("proposedValue")
        finalized["rationale"] = value.get("rationale")
        slot_key = _slot_value_key(finalized, axes)
        if slot_key in slot_index:
            existing = finalized_values[slot_index[slot_key]]
            if _value_key(existing) == _value_key(finalized):
                rationales = [existing.get("rationale")]
                _append_unique(rationales, finalized.get("rationale"))
                existing["rationale"] = " ".join(rationales)
            continue
        slot_index[slot_key] = len(finalized_values)
        finalized_values.append(finalized)
    group["values"] = finalized_values


def _build_proposal_parameters(
    adjustments: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    *,
    include_lut_value: bool = False,
) -> list[ProposalParameter]:
    candidate_index = {
        str(candidate.get("candidate_key") or ""): candidate
        for candidate in candidates
    }
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for adjustment in adjustments:
        if adjustment.get("selected", True) is False:
            continue
        candidate = candidate_index.get(str(adjustment.get("candidate_key") or "")) or {}
        key = (
            str(adjustment.get("model_file") or ""),
            str(adjustment.get("model_sheet") or ""),
            str(adjustment.get("parameter_name") or ""),
        )
        group = grouped.setdefault(
            key,
            {
                "model_file": key[0],
                "model_sheet": key[1],
                "model_table": str(candidate.get("model_table") or ""),
                "parameter_name": key[2],
                "slot_axes_field_names": [],
                "value_field_names": [],
                "rationales": [],
                "values": [],
                "value_index": {},
            },
        )
        if not group["model_table"] and candidate.get("model_table"):
            group["model_table"] = str(candidate.get("model_table") or "")
        _append_unique(group["rationales"], adjustment.get("parameter_selection_rationale_ko"))
        value_field_name = _value_field_for(adjustment, candidate_index)
        _append_unique(group["value_field_names"], value_field_name)
        allowed_axes = _allowed_slot_axes_for_candidate(
            candidate_index.get(str(adjustment.get("candidate_key") or "")) or {},
            value_field_name,
        )

        fallback_slot = _slot_from_axes(adjustment.get("slot_axes") or [])
        for cell in adjustment.get("value_grid") or []:
            if cell.get("proposed_value") is None:
                continue
            slot = _normalize_slot_coordinates(
                cell.get("coordinates") or fallback_slot,
                allowed_axes,
            )
            for slot_name in slot:
                _append_unique(group["slot_axes_field_names"], slot_name)
            value = {
                **slot,
                "basecaseValue": cell.get("basecase_value"),
                "proposedValue": cell.get("proposed_value"),
                "rationale": _value_rationale(cell),
            }
            if include_lut_value:
                value["lutValue"] = cell.get("lut_value")
            value_key = _value_key(value)
            if value_key in group["value_index"]:
                existing = group["values"][group["value_index"][value_key]]
                rationales = [existing.get("rationale")]
                _append_unique(rationales, value.get("rationale"))
                existing["rationale"] = " ".join(rationales)
                continue
            group["value_index"][value_key] = len(group["values"])
            group["values"].append(value)

    proposal_parameters: list[ProposalParameter] = []
    for group in grouped.values():
        if not group["values"]:
            continue
        _finalize_group_values(
            group,
            include_lut_value=include_lut_value,
        )
        proposal_parameters.append(
            ProposalParameter(
                parameter_name=group["parameter_name"],
                model_target=ModelParameterTarget(
                    model_file=group["model_file"],
                    model_sheet=group["model_sheet"],
                    table_name=group["model_table"],
                    value_field_names=group["value_field_names"],
                    slot_axes_field_names=group["slot_axes_field_names"],
                ),
                rationale=" ".join(group["rationales"])
                or "파라미터 선택 근거가 제공되지 않았습니다.",
                values=group["values"],
            ),
        )
    return proposal_parameters


def _context_ids(
    scenario_context: dict[str, Any],
    fallback_scenario_id: Any,
) -> tuple[int, int | None, int | None]:
    scenario = scenario_context.get("scenario") or {}
    scenario_group = scenario_context.get("scenario_group") or {}
    event = scenario_context.get("event") or {}
    scenario_id = int(scenario.get("scenario_id") or fallback_scenario_id)
    scenario_group_id = _int_or_none(
        scenario.get("scenario_group_id")
        or scenario_group.get("scenario_group_id"),
    )
    event_id = _int_or_none(event.get("mi_event_id") or scenario_group.get("mi_event_id"))
    return scenario_id, scenario_group_id, event_id


def _proposal_parameters_from_state(
    data: dict[str, Any],
    *,
    include_lut_value: bool = False,
) -> list[ProposalParameter]:
    adjustments = data.get("parameter_adjustments") or []
    candidates = data.get("candidate_mappings") or []
    return _build_proposal_parameters(
        adjustments,
        candidates,
        include_lut_value=include_lut_value,
    )


def _to_response_data(
    data: dict[str, Any],
    *,
    model_param_proposal_id: int,
    proposal_parameters: list[ProposalParameter],
) -> ProposeParametersData:
    scenario_context = data.get("scenario_context") or {}
    if not scenario_context:
        raise MIBaseError(ErrorCode.UNKNOWN_ERROR, detail="Scenario context not found in state")
    scenario_id, scenario_group_id, event_id = _context_ids(
        scenario_context,
        data.get("scenario_id"),
    )
    return ProposeParametersData(
        model_param_proposal_id=model_param_proposal_id,
        scenario_id=scenario_id,
        scenario_group_id=scenario_group_id,
        event_id=event_id,
        proposal_parameters=proposal_parameters,
    )


def _callback_success_output(
    response_data: ProposeParametersData,
) -> ProposeParametersCallbackOut:
    return ProposeParametersCallbackOut(
        status="success",
        message="model parameter proposal completed",
        data=ProposeParametersCallbackData(
            model_param_proposal_id=response_data.model_param_proposal_id,
            scenario_id=response_data.scenario_id,
            scenario_group_id=response_data.scenario_group_id,
            event_id=response_data.event_id,
            status="PROPOSED",
        ),
    )


def _callback_error_output(
    *,
    message: str,
) -> ProposeParametersCallbackOut:
    return ProposeParametersCallbackOut(
        status="error",
        message=message,
        data=None,
    )


def _proposal_parameter_summary(proposal_parameters: list[ProposalParameter]) -> list[dict[str, Any]]:
    return [
        {
            "parameter_name": parameter.parameter_name,
            "value_count": len(parameter.values),
        }
        for parameter in proposal_parameters
    ]
