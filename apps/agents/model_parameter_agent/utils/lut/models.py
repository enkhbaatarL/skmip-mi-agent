from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeVar

from apps.agents.model_parameter_agent.utils.lut.precision import (
    BASECASE_VALUE_MAX_DECIMAL_PLACES,
    NumericPrecisionMode,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


CanonicalValue = str | int | float
CanonicalKey = tuple[CanonicalValue, ...]
NumericValue = int | float
EffectiveSource = Literal["basecase", "lut"]

_K = TypeVar("_K")
_V = TypeVar("_V")


def domain_error(detail: str) -> MIBaseError:
    return MIBaseError(ErrorCode.INVALID_REQUEST, detail=detail)


def freeze_mapping(values: Mapping[_K, _V] | None = None) -> Mapping[_K, _V]:  # noqa: UP047
    return MappingProxyType(dict(values or {}))


@dataclass(frozen=True, slots=True)
class ReferenceLoadPolicy:
    """Shared horizon and precision rules for Basecase and LUT references."""

    start_year: int = 2026
    end_year: int = 2030
    value_max_decimal_places: int = BASECASE_VALUE_MAX_DECIMAL_PLACES
    value_precision_mode: NumericPrecisionMode = "trunc"

    def __post_init__(self) -> None:
        if isinstance(self.start_year, bool) or isinstance(self.end_year, bool):
            msg = "reference horizon year must be an integer"
            raise domain_error(msg)
        if self.start_year < 2000 or self.end_year < 2000:
            msg = "reference horizon year must be 2000 or later"
            raise domain_error(msg)
        if self.start_year > self.end_year:
            msg = (
                "model_parameter_lut_horizon_start_year must be less than or equal to "
                "model_parameter_lut_horizon_end_year"
            )
            raise domain_error(
                msg,
            )
        if (
            isinstance(self.value_max_decimal_places, bool)
            or not isinstance(self.value_max_decimal_places, int)
            or self.value_max_decimal_places < -1
        ):
            msg = "model_parameter_basecase_value_max_decimal_places must be an integer of -1 or greater"
            raise domain_error(msg)
        if self.value_precision_mode not in {"trunc", "ceil", "round"}:
            msg = "model_parameter_basecase_value_precision_mode must be trunc, ceil, or round"
            raise domain_error(msg)

    @property
    def years(self) -> tuple[int, ...]:
        return tuple(range(self.start_year, self.end_year + 1))

    def contains_year(self, year: int) -> bool:
        return self.start_year <= year <= self.end_year


@dataclass(frozen=True, slots=True)
class LutRecord:
    parameter_name: str
    canonical_key: CanonicalKey
    axes: Mapping[str, CanonicalValue]
    value: NumericValue
    metadata: Mapping[str, CanonicalValue]
    reference_id: str
    diagnostics: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class BasecaseReference:
    candidate_key: str
    parameter_name: str
    canonical_key: CanonicalKey
    axes: Mapping[str, CanonicalValue]
    value: NumericValue | None
    metadata: Mapping[str, CanonicalValue]
    reference_id: str


@dataclass(frozen=True, slots=True)
class BasecaseIndex:
    policy: ReferenceLoadPolicy
    records: tuple[BasecaseReference, ...]
    candidate_parameters: Mapping[str, str]
    candidate_key_axes: Mapping[str, tuple[str, ...]]
    candidate_metadata_axes: Mapping[str, tuple[str, ...]]
    _by_candidate: Mapping[str, Mapping[CanonicalKey, BasecaseReference]] = field(
        repr=False,
        compare=False,
    )
    blocked_exact_keys_by_candidate: Mapping[str, frozenset[CanonicalKey]] = field(
        default_factory=freeze_mapping,
    )

    def lookup(
        self,
        candidate_key: str,
        axes: Mapping[str, Any],
    ) -> BasecaseReference | None:
        from apps.agents.model_parameter_agent.utils.lut.keys import canonical_key_from_axes

        key_axes = self.candidate_key_axes.get(candidate_key)
        if key_axes is None:
            return None
        canonical_key = canonical_key_from_axes(axes, key_axes)
        return (self._by_candidate.get(candidate_key) or {}).get(canonical_key)

    def records_for_candidate(self, candidate_key: str) -> tuple[BasecaseReference, ...]:
        return tuple(record for record in self.records if record.candidate_key == candidate_key)


@dataclass(frozen=True, slots=True)
class SlotPeriod:
    values: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class SlotLeaf:
    axes: Mapping[str, CanonicalValue]
    available_periods: tuple[SlotPeriod, ...]
    applicability_attributes: Mapping[str, tuple[CanonicalValue, ...]] = field(
        default_factory=freeze_mapping,
    )


@dataclass(frozen=True, slots=True)
class CandidateSlotCatalog:
    candidate_key: str
    parameter_name: str
    key_axes: tuple[str, ...]
    non_time_axes: tuple[str, ...]
    time_axes: tuple[str, ...]
    leaves: tuple[SlotLeaf, ...]

    def contains(self, axes: Mapping[str, Any]) -> bool:
        from apps.agents.model_parameter_agent.utils.lut.keys import canonical_key_from_axes

        try:
            canonical_key = canonical_key_from_axes(axes, self.key_axes)
        except MIBaseError:
            return False
        normalized_axes = dict(zip(self.key_axes, canonical_key, strict=True))
        for leaf in self.leaves:
            if any(normalized_axes.get(axis_name) != axis_value for axis_name, axis_value in leaf.axes.items()):
                continue
            return any(
                all(normalized_axes.get(axis_name) == axis_value for axis_name, axis_value in period.values.items())
                for period in leaf.available_periods
            )
        return False


@dataclass(frozen=True, slots=True)
class SlotCatalog:
    candidates: tuple[CandidateSlotCatalog, ...]
    _by_candidate: Mapping[str, CandidateSlotCatalog] = field(
        repr=False,
        compare=False,
    )

    def for_candidate(self, candidate_key: str) -> CandidateSlotCatalog | None:
        return self._by_candidate.get(candidate_key)

    def contains(self, candidate_key: str, axes: Mapping[str, Any]) -> bool:
        candidate = self.for_candidate(candidate_key)
        return candidate.contains(axes) if candidate is not None else False


@dataclass(frozen=True, slots=True)
class EffectiveReference:
    candidate_key: str
    parameter_name: str
    canonical_slot_key: CanonicalKey
    axes: Mapping[str, CanonicalValue]
    metadata: Mapping[str, CanonicalValue]
    actual_basecase_value: NumericValue | None
    lut_default_value: NumericValue | None
    llm_reference_value: NumericValue
    effective_source: EffectiveSource
    basecase_reference_id: str | None
    lut_reference_id: str | None
    lut_version: str | None
    diagnostics: tuple[str, ...] = ()
