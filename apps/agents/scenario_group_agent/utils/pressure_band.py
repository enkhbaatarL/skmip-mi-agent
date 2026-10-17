from __future__ import annotations  # noqa: CPY001

from collections.abc import Mapping, Sequence
from typing import Any, Literal


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


def uses_unique_strong_bands(generation_diagnostics: Mapping[str, Any] | None) -> bool:
    """그룹이 strong band를 방향당 하나만 두는 band_unique 정책으로 만들어졌는지 판단한다.

    정책 기록이 없는 기존 그룹은 band_unique로 본다.
    """
    diagnostics = generation_diagnostics or {}
    policy = diagnostics.get("scenario_synthesis_policy") or diagnostics.get("scenarioSynthesisPolicy")
    return policy != "distinct_driver"


def assign_relative_pressure_bands(deltas: Sequence[int], *, unique_strong: bool) -> list[PressureBandValue]:
    """Base 대비 차이 목록에 band를 붙인다.

    unique_strong이면 band_unique 생성 단계와 같게, 같은 strong band를 받은 Scenario가 여럿일 때 차이의 절댓값이
    가장 큰 하나만 strong으로 두고 나머지는 같은 방향의 완화된 band로 내린다. 동점이면 앞선 Scenario가 strong을 갖는다.
    """
    bands = [relative_pressure_band(delta) for delta in deltas]
    if not unique_strong:
        return bands
    for strong_band, moderate_band in (("strong_bullish", "bullish"), ("strong_bearish", "bearish")):
        holders = [index for index, band in enumerate(bands) if band == strong_band]
        if len(holders) <= 1:
            continue
        holders.sort(key=lambda index: abs(deltas[index]), reverse=True)
        for index in holders[1:]:
            bands[index] = moderate_band
    return bands


__all__ = [
    "PRESSURE_CONTRIBUTION_SCORES",
    "STRONG_PRESSURE_DELTA",
    "PressureBandValue",
    "assign_relative_pressure_bands",
    "relative_pressure_band",
    "uses_unique_strong_bands",
]
