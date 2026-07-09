from __future__ import annotations

import json
import re
from typing import Any

from apps.agents.model_parameter_agent.utils.basecase import (
    basecase_slot_axis_names_from_candidate,
    basecase_value_field_name_from_candidate,
)
from apps.agents.model_parameter_agent.schemas.api.parameters import (
    ProposalParameter,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


RESERVED_VALUE_FIELDS = {"basecaseValue", "proposedValue", "rationale"}
MAX_ERROR_DETAILS = 12


def validate_confirmation_parameters(
    parameters: list[ProposalParameter],
    *,
    parameter_definitions: list[dict[str, Any]] | None = None,
) -> None:
    errors: list[str] = []
    if not parameters:
        errors.append("data.confirmationParameters must contain at least one parameter")

    definitions_by_parameter = _index_parameter_definitions(parameter_definitions or [])
    seen_parameter_targets: set[str] = set()
    for parameter_index, parameter in enumerate(parameters):
        location = f"data.confirmationParameters[{parameter_index}]"
        target = parameter.model_target
        parameter_name = parameter.parameter_name.strip()
        if not parameter_name:
            errors.append(f"{location}.parameterName is required")

        model_file = target.model_file.strip()
        model_sheet = target.model_sheet.strip()
        table_name = target.table_name.strip()
        if not model_file:
            errors.append(f"{location}.modelTarget.modelFile is required")
        if not model_sheet:
            errors.append(f"{location}.modelTarget.modelSheet is required")
        if not table_name:
            errors.append(f"{location}.modelTarget.tableName is required")

        value_fields = _normalized_names(target.value_field_names)
        slot_axes = _normalized_names(target.slot_axes_field_names)
        if not value_fields:
            errors.append(f"{location}.modelTarget.valueFieldNames must not be empty")
        if not slot_axes:
            errors.append(f"{location}.modelTarget.slotAxesFieldNames must not be empty")
        _append_duplicate_name_errors(
            errors,
            names=value_fields,
            field_path=f"{location}.modelTarget.valueFieldNames",
        )
        _append_duplicate_name_errors(
            errors,
            names=slot_axes,
            field_path=f"{location}.modelTarget.slotAxesFieldNames",
        )

        reserved_slot_axes = sorted(set(slot_axes) & RESERVED_VALUE_FIELDS)
        if reserved_slot_axes:
            errors.append(
                f"{location}.modelTarget.slotAxesFieldNames uses reserved value fields: "
                f"{reserved_slot_axes}",
            )
        reserved_value_fields = sorted(set(value_fields) & RESERVED_VALUE_FIELDS)
        if reserved_value_fields:
            errors.append(
                f"{location}.modelTarget.valueFieldNames uses reserved value fields: "
                f"{reserved_value_fields}",
            )
        field_intersection = sorted(set(value_fields) & set(slot_axes))
        if field_intersection:
            errors.append(
                f"{location}.modelTarget value fields and slot axes overlap: "
                f"{field_intersection}",
            )

        parameter_signature = _signature(
            [parameter_name, model_file, model_sheet, table_name],
        )
        if parameter_signature in seen_parameter_targets:
            errors.append(
                f"{location} duplicates parameter target "
                f"({parameter_name}, {model_file}, {model_sheet}, {table_name})",
            )
        seen_parameter_targets.add(parameter_signature)

        if not parameter.rationale.strip():
            errors.append(f"{location}.rationale is required")
        if not parameter.values:
            errors.append(f"{location}.values must not be empty")

        definition = definitions_by_parameter.get(_field_key(parameter_name))
        if definition is not None:
            _append_parameter_definition_errors(
                errors,
                parameter=parameter,
                definition=definition,
                value_fields=value_fields,
                slot_axes=slot_axes,
                location=location,
            )

        _append_value_errors(
            errors,
            values=parameter.values,
            slot_axes=slot_axes,
            location=location,
        )

    if errors:
        detail = "; ".join(errors[:MAX_ERROR_DETAILS])
        if len(errors) > MAX_ERROR_DETAILS:
            detail += f"; ... and {len(errors) - MAX_ERROR_DETAILS} more"
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def _append_parameter_definition_errors(
    errors: list[str],
    *,
    parameter: ProposalParameter,
    definition: dict[str, Any],
    value_fields: list[str],
    slot_axes: list[str],
    location: str,
) -> None:
    target = parameter.model_target
    expected_model_file = str(definition.get("model_file") or "").strip()
    expected_model_sheet = str(definition.get("model_sheet") or "").strip()
    expected_table_name = str(definition.get("model_table") or "").strip()
    _append_expected_field_error(
        errors,
        actual=target.model_file,
        expected=expected_model_file,
        field_path=f"{location}.modelTarget.modelFile",
    )
    _append_expected_field_error(
        errors,
        actual=target.model_sheet,
        expected=expected_model_sheet,
        field_path=f"{location}.modelTarget.modelSheet",
    )
    _append_expected_field_error(
        errors,
        actual=target.table_name,
        expected=expected_table_name,
        field_path=f"{location}.modelTarget.tableName",
    )

    expected_value_field = basecase_value_field_name_from_candidate(definition)
    expected_value_key = _field_key(expected_value_field)
    invalid_value_fields = [
        field for field in value_fields if _field_key(field) != expected_value_key
    ]
    if invalid_value_fields:
        errors.append(
            f"{location}.modelTarget.valueFieldNames has invalid fields "
            f"{invalid_value_fields}; expected [{expected_value_field!r}]",
        )

    allowed_slot_axes = _allowed_slot_axes(definition)
    invalid_slot_axes = [
        axis for axis in slot_axes if not _is_allowed_slot_axis(axis, allowed_slot_axes)
    ]
    if invalid_slot_axes:
        errors.append(
            f"{location}.modelTarget.slotAxesFieldNames has invalid fields "
            f"{invalid_slot_axes}; allowed {allowed_slot_axes}",
        )


def _append_expected_field_error(
    errors: list[str],
    *,
    actual: str,
    expected: str,
    field_path: str,
) -> None:
    if expected and _field_key(actual) != _field_key(expected):
        errors.append(f"{field_path} must be {expected!r}")


def _allowed_slot_axes(definition: dict[str, Any]) -> list[str]:
    axes = basecase_slot_axis_names_from_candidate(definition)
    if axes:
        return axes

    role_names = _column_role_names(definition.get("basecase_column_roles"))
    read_mode = str(definition.get("basecase_read_mode") or "").lower()
    if read_mode == "matrix_time_columns":
        axes = role_names
        for axis_name in ("Year", "Month", "Period"):
            _append_unique(axes, axis_name)
        return axes

    value_field_key = _field_key(definition.get("parameter_name"))
    axes: list[str] = []
    last_role_index = len(role_names) - 1
    for index, role_name in enumerate(role_names):
        if index == last_role_index:
            continue
        if _field_key(role_name) == value_field_key:
            continue
        _append_unique(axes, role_name)
    return axes


def _is_allowed_slot_axis(axis_name: str, allowed_axes: list[str]) -> bool:
    axis_key = _field_key(axis_name)
    if not axis_key:
        return False
    allowed_keys = {_field_key(axis) for axis in allowed_axes}
    if axis_key in allowed_keys:
        return True

    country_axes = [axis for axis in allowed_axes if _field_key(axis).endswith("country")]
    if axis_key in {"country", "province"} and len(country_axes) == 1:
        return True
    return any(_field_key(axis) == f"{axis_key}country" for axis in country_axes)


def _column_role_names(raw: Any) -> list[str]:
    names: list[str] = []
    for part in str(raw or "").split(","):
        separator = ":" if ":" in part else "=" if "=" in part else ""
        if not separator:
            continue
        _, role = part.split(separator, 1)
        role_name = str(role or "").strip()
        if role_name:
            _append_unique(names, role_name)
    return names


def _index_parameter_definitions(
    parameter_definitions: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for definition in parameter_definitions:
        parameter_key = _field_key(definition.get("parameter_name"))
        if parameter_key and parameter_key not in indexed:
            indexed[parameter_key] = definition
    return indexed


def _append_value_errors(
    errors: list[str],
    *,
    values: list[dict[str, Any]],
    slot_axes: list[str],
    location: str,
) -> None:
    allowed_keys = set(slot_axes) | RESERVED_VALUE_FIELDS
    seen_slots: set[str] = set()
    for value_index, value in enumerate(values):
        value_location = f"{location}.values[{value_index}]"
        if not isinstance(value, dict):
            errors.append(f"{value_location} must be an object")
            continue

        missing_axes = [axis for axis in slot_axes if axis not in value]
        if missing_axes:
            errors.append(f"{value_location} missing slot axes: {missing_axes}")

        extra_keys = sorted(set(value) - allowed_keys)
        if extra_keys:
            errors.append(f"{value_location} has undeclared fields: {extra_keys}")

        for required_key in ("basecaseValue", "proposedValue", "rationale"):
            if required_key not in value:
                errors.append(f"{value_location}.{required_key} is required")
        rationale = value.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            errors.append(f"{value_location}.rationale must be a non-empty string")

        slot_key = _signature([value.get(axis) for axis in slot_axes])
        if slot_key in seen_slots:
            errors.append(f"{value_location} duplicates slot coordinates")
        seen_slots.add(slot_key)


def _append_duplicate_name_errors(
    errors: list[str],
    *,
    names: list[str],
    field_path: str,
) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in names:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)
    if duplicates:
        errors.append(f"{field_path} contains duplicates: {duplicates}")


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _field_key(value: Any) -> str:
    return re.sub(r"[^0-9a-zA-Z가-힣]+", "", str(value or "")).lower()


def _normalized_names(values: list[str]) -> list[str]:
    return [str(value).strip() for value in values if str(value).strip()]


def _signature(values: list[Any]) -> str:
    return json.dumps(values, ensure_ascii=False, sort_keys=False, default=str)
