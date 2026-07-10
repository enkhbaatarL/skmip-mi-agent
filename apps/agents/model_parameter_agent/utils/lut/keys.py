from __future__ import annotations

from collections.abc import Mapping
import math
from typing import Any

from apps.agents.model_parameter_agent.utils.lut.models import (
    CanonicalKey,
    CanonicalValue,
    domain_error,
)


INTEGER_AXES = frozenset({"Year", "Month", "Period"})
TIME_AXES = ("Year", "Month")


def canonical_axis_value(axis_name: str, value: Any) -> CanonicalValue:  # noqa: ANN401
    if value is None or isinstance(value, bool):
        msg = f"LUT axis {axis_name!r} has an invalid value: {value!r}"
        raise domain_error(msg)
    if axis_name in INTEGER_AXES:
        return strict_int(value, label=axis_name)
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            msg = f"LUT axis {axis_name!r} must be finite"
            raise domain_error(msg)
        return int(number) if number.is_integer() else number
    text = str(value).strip()
    if not text:
        msg = f"LUT axis {axis_name!r} must not be empty"
        raise domain_error(msg)
    return text


def canonical_key_from_axes(
    axes: Mapping[str, Any],
    key_axes: tuple[str, ...],
) -> CanonicalKey:
    missing = [axis_name for axis_name in key_axes if axis_name not in axes]
    if missing:
        msg = f"exact LUT key axes are missing: {', '.join(missing)}"
        raise domain_error(msg)
    return tuple(canonical_axis_value(axis_name, axes[axis_name]) for axis_name in key_axes)


def strict_float(value: Any, *, label: str) -> float:  # noqa: ANN401
    if value is None or isinstance(value, bool):
        msg = f"{label} must be a finite number: {value!r}"
        raise domain_error(msg)
    text = str(value).strip()
    if not text:
        msg = f"{label} must be a finite number: empty value"
        raise domain_error(msg)
    try:
        number = float(text)
    except (TypeError, ValueError) as exc:
        msg = f"{label} must be a finite number: {value!r}"
        raise domain_error(msg) from exc
    if not math.isfinite(number):
        msg = f"{label} must be a finite number: {value!r}"
        raise domain_error(msg)
    return number


def strict_int(value: Any, *, label: str) -> int:  # noqa: ANN401
    number = strict_float(value, label=label)
    if not number.is_integer():
        msg = f"{label} must be an integer: {value!r}"
        raise domain_error(msg)
    return int(number)
