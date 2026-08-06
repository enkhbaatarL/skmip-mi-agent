from __future__ import annotations

import hashlib
from datetime import date
from typing import Any


def deterministic_jitter(parameter_code: str, month: date) -> float:
    digest = hashlib.sha256(f"{parameter_code}|{month:%Y-%m}".encode()).digest()
    ratio = int.from_bytes(digest[:8], "big") / ((1 << 64) - 1)
    return ratio - 0.5


def seasonal_offset(season: str, amplitude: float, month: int) -> float:
    if season == "winter":
        if month in {12, 1, 2}:
            return amplitude
        if month in {11, 3}:
            return amplitude / 2
    elif season == "summer":
        if month in {7, 8}:
            return amplitude
        if month in {6, 9}:
            return amplitude / 2
    elif season == "winterLow":
        if month in {12, 1, 2}:
            return -amplitude
        if month in {11, 3}:
            return -amplitude / 2
    return 0.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def synthetic_baseline(parameter: dict[str, Any], month: date) -> float:
    constraints = parameter["valueConstraints"]
    value = (
        float(parameter["baselineBase"])
        + seasonal_offset(str(parameter.get("season", "flat")), float(parameter.get("seasonAmp", 0)), month.month)
        + deterministic_jitter(str(parameter["parameterCode"]), month)
    )
    return clamp(value, float(constraints["min"]), float(constraints["max"]))
