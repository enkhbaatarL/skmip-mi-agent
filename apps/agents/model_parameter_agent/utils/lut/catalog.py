from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from apps.agents.model_parameter_agent.utils.lut.adapters import FileSnapshot, load_parameter_records
from apps.agents.model_parameter_agent.utils.lut.keys import canonical_key_from_axes
from apps.agents.model_parameter_agent.utils.lut.models import (
    CanonicalKey,
    LutLoadPolicy,
    LutRecord,
    domain_error,
)
from apps.agents.model_parameter_agent.utils.lut.registry import ParameterSpecRegistry


@dataclass(frozen=True, slots=True)
class LutCatalog:
    version: str
    policy: LutLoadPolicy
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
    policy: LutLoadPolicy,
    snapshots_by_path: Mapping[str, FileSnapshot],
    *,
    version: str,
) -> LutCatalog:
    all_records: list[LutRecord] = []
    all_diagnostics: list[str] = []
    by_parameter: dict[str, Mapping[CanonicalKey, LutRecord]] = {}
    for parameter_name, spec in registry.specs.items():
        role_snapshots = {role: snapshots_by_path[file_spec.relative_path] for role, file_spec in spec.files.items()}
        loaded = load_parameter_records(spec, policy, role_snapshots)
        if not loaded:
            msg = f"registered LUT parameter produced no records in the configured horizon: {parameter_name}"
            raise domain_error(
                msg,
            )
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
