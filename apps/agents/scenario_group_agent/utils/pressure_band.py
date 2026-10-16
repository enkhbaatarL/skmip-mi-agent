from __future__ import annotations  # noqa: CPY001

from typing import Literal


PressureBandValue = Literal["strong_bearish", "bearish", "balanced", "bullish", "strong_bullish"]

PRESSURE_CONTRIBUTION_SCORES: dict[str, int] = {"bullish": 1, "balanced": 0, "bearish": -1}
# Base 대비 pressureContribution 합산 차이가 이 값 이상이면 strong band로 본다.
STRONG_PRESSURE_DELTA = 2


def relative_pressure_band(delta: int) -> PressureBandValue:
    """Base Scenario 대비 pressureContribution 합산 차이를 pressure band로 바꾼다.

    Base 자신은 차이가 0이므로 항상 balanced다.
    """
    if delta >= STRONG_PRESSURE_DELTA:
        return "strong_bullish"
    if delta > 0:
        return "bullish"
    if delta <= -STRONG_PRESSURE_DELTA:
        return "strong_bearish"
    if delta < 0:
        return "bearish"
    return "balanced"


__all__ = [
    "PRESSURE_CONTRIBUTION_SCORES",
    "STRONG_PRESSURE_DELTA",
    "PressureBandValue",
    "relative_pressure_band",
]
