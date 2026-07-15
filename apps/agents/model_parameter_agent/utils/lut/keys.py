from __future__ import annotations

from collections.abc import Mapping
from decimal import ROUND_CEILING, ROUND_DOWN, ROUND_HALF_UP, Decimal, localcontext
import math
from typing import Any

from apps.agents.model_parameter_agent.utils.lut.models import (
    CanonicalKey,
    CanonicalValue,
    NumericValue,
    domain_error,
)
from apps.agents.model_parameter_agent.utils.lut.precision import (
    NumericPrecisionMode,
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


def normalize_numeric_value(
    value: Any,  # noqa: ANN401
    *,
    label: str,
    max_decimal_places: int,
) -> NumericValue:
    """Return a finite number rounded to nearest with halves away from zero."""
    return _quantize_numeric_value(
        value,
        label=label,
        max_decimal_places=max_decimal_places,
        rounding=ROUND_HALF_UP,
    )


def truncate_numeric_value(
    value: Any,  # noqa: ANN401
    *,
    label: str,
    max_decimal_places: int,
) -> NumericValue:
    """Return a finite number truncated toward zero for stable JSON serialization."""
    return _quantize_numeric_value(
        value,
        label=label,
        max_decimal_places=max_decimal_places,
        rounding=ROUND_DOWN,
    )


def ceil_numeric_value(
    value: Any,  # noqa: ANN401
    *,
    label: str,
    max_decimal_places: int,
) -> NumericValue:
    """Return a finite number rounded toward positive infinity."""
    return _quantize_numeric_value(
        value,
        label=label,
        max_decimal_places=max_decimal_places,
        rounding=ROUND_CEILING,
    )


def _quantize_numeric_value(
    value: Any,  # noqa: ANN401
    *,
    label: str,
    max_decimal_places: int,
    rounding: str,
) -> NumericValue:
    if (
        isinstance(max_decimal_places, bool)
        or not isinstance(max_decimal_places, int)
        or max_decimal_places < -1
    ):
        msg = f"{label} max decimal places must be an integer of -1 or greater"
        raise domain_error(msg)
    number = strict_float(value, label=label)
    if max_decimal_places == -1:
        return int(number) if number.is_integer() else number
    if number == 0:
        return 0
    decimal_value = Decimal(str(value).strip())
    quantum = Decimal(1).scaleb(-max_decimal_places)
    with localcontext() as context:
        context.prec = max(
            28,
            len(decimal_value.as_tuple().digits) + abs(decimal_value.adjusted()) + max_decimal_places + 2,
        )
        quantized = decimal_value.quantize(quantum, rounding=rounding)
    quantized_number = float(quantized)
    return int(quantized_number) if quantized_number.is_integer() else quantized_number


def apply_numeric_precision(
    value: Any,  # noqa: ANN401
    *,
    label: str,
    max_decimal_places: int,
    mode: NumericPrecisionMode,
) -> NumericValue:
    if mode == "round":
        return normalize_numeric_value(
            value,
            label=label,
            max_decimal_places=max_decimal_places,
        )
    if mode == "ceil":
        return ceil_numeric_value(
            value,
            label=label,
            max_decimal_places=max_decimal_places,
        )
    if mode == "trunc":
        return truncate_numeric_value(
            value,
            label=label,
            max_decimal_places=max_decimal_places,
        )
    msg = f"unsupported numeric precision mode: {mode!r}"
    raise domain_error(msg)


def strict_int(value: Any, *, label: str) -> int:  # noqa: ANN401
    number = strict_float(value, label=label)
    if not number.is_integer():
        msg = f"{label} must be an integer: {value!r}"
        raise domain_error(msg)
    return int(number)
