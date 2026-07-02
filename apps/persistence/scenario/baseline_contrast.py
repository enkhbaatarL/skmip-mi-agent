from __future__ import annotations


"""시나리오 그룹 생성 및 검증에서 공통으로 쓰는 베이스라인 대비 정책.

이 모듈은 단일 베이스라인 선택 규칙과, 선택된 각 Dimension에서
베이스라인 시나리오와 다른 값이 최소 1개 이상 존재하는지 확인하는
커버리지 검사를 중앙화한다. 시나리오 저장, 생성 파이프라인의
quick validation, validation review에서 함께 사용되어 모든 단계에
동일한 규칙이 적용되도록 한다.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class BaselineSelection:
    index: int | None
    reason: str


@dataclass(frozen=True)
class BaselineContrastResult:
    baseline_index: int | None
    baseline_values: dict[str, Any] = field(default_factory=dict)
    observed_non_baseline_values: dict[str, set[Any]] = field(default_factory=dict)
    missing_dimensions: list[str] = field(default_factory=list)
    baseline_issue: str | None = None

    @property
    def covered(self) -> bool:
        return self.baseline_issue is None and not self.missing_dimensions


def _read(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _display_order(obj: Any, fallback: int) -> int:
    value = _read(obj, "display_order", fallback)
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def select_baseline_by_probability(scenarios: list[Any]) -> BaselineSelection:
    scored: list[tuple[Decimal, int, int]] = []
    for index, scenario in enumerate(scenarios):
        score = _decimal_or_none(_read(scenario, "probability_score"))
        if score is None:
            continue
        scored.append((score, _display_order(scenario, index + 1), index))
    if not scored:
        return BaselineSelection(index=None, reason="probability_score 없음")
    _, _, index = max(scored, key=lambda item: (item[0], -item[1], -item[2]))
    return BaselineSelection(index=index, reason="최고 probability_score")


def apply_single_baseline_by_probability(
    scenarios: list[Any],
    *,
    user_id: int | None = None,
) -> None:
    selection = select_baseline_by_probability(scenarios)
    for index, scenario in enumerate(scenarios):
        if isinstance(scenario, dict):
            scenario["baseline_yn"] = "Y" if index == selection.index else "N"
            if user_id is not None:
                scenario["mod_usr_logn_id"] = user_id
            continue
        scenario.baseline_yn = "Y" if index == selection.index else "N"
        if user_id is not None:
            scenario.mod_usr_logn_id = user_id


def _dimension_values(scenario: Any) -> dict[str, Any]:
    values = _read(scenario, "dimension_values", {})
    return values if isinstance(values, dict) else {}


def check_baseline_contrast_coverage(
    scenarios: list[Any],
    selected_dimensions: list[str],
    *,
    baseline_index: int | None = None,
) -> BaselineContrastResult:
    selected_dimensions = [str(key) for key in selected_dimensions if str(key)]
    if not scenarios:
        return BaselineContrastResult(
            baseline_index=None,
            baseline_issue="검사할 시나리오 없음",
        )
    if baseline_index is None:
        baseline_index = select_baseline_by_probability(scenarios).index
    if baseline_index is None:
        return BaselineContrastResult(
            baseline_index=None,
            baseline_issue="baseline scenario 없음",
        )
    if not 0 <= baseline_index < len(scenarios):
        return BaselineContrastResult(
            baseline_index=baseline_index,
            baseline_issue="baseline scenario index 범위 밖",
        )

    baseline_values = _dimension_values(scenarios[baseline_index])
    observed: dict[str, set[Any]] = {key: set() for key in selected_dimensions}
    missing: list[str] = []
    for key in selected_dimensions:
        if key not in baseline_values:
            missing.append(key)
            continue
        baseline_value = baseline_values.get(key)
        for index, scenario in enumerate(scenarios):
            if index == baseline_index:
                continue
            value = _dimension_values(scenario).get(key)
            if value is not None and value != baseline_value:
                observed[key].add(value)
        if not observed[key]:
            missing.append(key)

    return BaselineContrastResult(
        baseline_index=baseline_index,
        baseline_values={key: baseline_values.get(key) for key in selected_dimensions},
        observed_non_baseline_values=observed,
        missing_dimensions=missing,
    )
