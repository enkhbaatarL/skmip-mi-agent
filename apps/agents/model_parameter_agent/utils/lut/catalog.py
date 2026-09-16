from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any

from apps.agents.model_parameter_agent.utils.lut.adapters import FileSnapshot, load_parameter_records
from apps.agents.model_parameter_agent.utils.lut.keys import canonical_key_from_axes
from apps.agents.model_parameter_agent.utils.lut.models import (
    CanonicalKey,
    LutRecord,
    ReferenceLoadPolicy,
    domain_error,
)
from apps.agents.model_parameter_agent.utils.lut.registry import ParameterSpecRegistry


@dataclass(frozen=True, slots=True)
class LutCatalog:
    version: str
    policy: ReferenceLoadPolicy
    registry: ParameterSpecRegistry
    records: tuple[LutRecord, ...]
    diagnostics: tuple[str, ...]
    _by_parameter: Mapping[str, Mapping[CanonicalKey, LutRecord]] = field(
        repr=False,
        compare=False,
    )

    def lookup(
        self,
        parameter_name: str,
        axes: Mapping[str, Any],
    ) -> LutRecord | None:
        spec = self.registry.get(parameter_name)
        if spec is None:
            return None
        canonical_key = canonical_key_from_axes(axes, spec.key_axes)
        return (self._by_parameter.get(parameter_name) or {}).get(canonical_key)

    def records_for_parameter(self, parameter_name: str) -> tuple[LutRecord, ...]:
        records = self._by_parameter.get(parameter_name) or {}
        return tuple(records.values())


def build_lut_catalog(
    registry: ParameterSpecRegistry,
    policy: ReferenceLoadPolicy,
    snapshots_by_path: Mapping[str, FileSnapshot],
    *,
    version: str,
    preserve_value_precision_parameters: frozenset[str] = frozenset(),
) -> LutCatalog:
    all_records: list[LutRecord] = []
    all_diagnostics: list[str] = []
    by_parameter: dict[str, Mapping[CanonicalKey, LutRecord]] = {}
    for parameter_name, spec in registry.specs.items():
        if not spec.enabled:
            continue
        role_snapshots = {role: snapshots_by_path[file_spec.relative_path] for role, file_spec in spec.files.items()}
        parameter_policy = (
            replace(policy, value_max_decimal_places=-1)
            if parameter_name in preserve_value_precision_parameters
            else policy
        )
        loaded = load_parameter_records(spec, parameter_policy, role_snapshots)
        if not loaded:
            msg = f"registered LUT parameter produced no records in the configured horizon: {parameter_name}"
            raise domain_error(
                msg,
            )
        if "Year" in spec.key_axes:
            produced_years = {int(record.axes["Year"]) for record in loaded if record.axes.get("Year") is not None}
            missing_years = sorted(set(policy.years) - produced_years)
            if missing_years:
                msg = (
                    "registered LUT parameter does not cover the complete configured horizon: "
                    f"parameter={parameter_name}, missing_years={missing_years}"
                )
                raise domain_error(msg)
        unique: dict[CanonicalKey, LutRecord] = {}
        for record in loaded:
            all_diagnostics.extend(
                diagnostic
                for diagnostic in record.diagnostics
                if diagnostic.startswith("deduped_identical_lut_source_key=")
            )
            previous = unique.get(record.canonical_key)
            if previous is None:
                unique[record.canonical_key] = record
                continue
            if previous.value != record.value or dict(previous.metadata) != dict(record.metadata):
                msg = (
                    "conflicting duplicate LUT exact key: "
                    f"parameter={parameter_name}, key={record.canonical_key!r}, "
                    f"references=({previous.reference_id}, {record.reference_id})"
                )
                raise domain_error(
                    msg,
                )
            all_diagnostics.append(
                "deduped identical LUT exact key: "
                f"parameter={parameter_name}, key={record.canonical_key!r}, "
                f"kept={previous.reference_id}, dropped={record.reference_id}",
            )
        immutable_index = MappingProxyType(dict(unique))
        by_parameter[parameter_name] = immutable_index
        all_records.extend(immutable_index.values())

    return LutCatalog(
        version=version,
        policy=policy,
        registry=registry,
        records=tuple(all_records),
        diagnostics=tuple(dict.fromkeys(all_diagnostics)),
        _by_parameter=MappingProxyType(by_parameter),
    )
