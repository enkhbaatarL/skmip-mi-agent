from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import Any

from apps.agents.model_parameter_agent.utils.basecase import (
    basecase_slot_axis_names_from_candidate,
)
from apps.agents.model_parameter_agent.utils.lut.catalog import LutCatalog
from apps.agents.model_parameter_agent.utils.lut.keys import (
    TIME_AXES,
    canonical_axis_value,
    canonical_key_from_axes,
    strict_float,
)
from apps.agents.model_parameter_agent.utils.lut.models import (
    BasecaseIndex,
    BasecaseReference,
    CandidateSlotCatalog,
    CanonicalKey,
    CanonicalValue,
    EffectiveReference,
    LutLoadPolicy,
    SlotCatalog,
    SlotLeaf,
    SlotPeriod,
    domain_error,
    freeze_mapping,
)
from apps.agents.model_parameter_agent.utils.lut.registry import ParameterSpecRegistry
from apps.agents.model_parameter_agent.utils.lut.runtime import get_parameter_spec_registry


def _parameter_name(candidate: Mapping[str, Any]) -> str:
    name = str(
        candidate.get("canonical_parameter_name") or candidate.get("parameter_name") or "",
    ).strip()
    if not name:
        msg = "candidate canonical parameter name is required"
        raise domain_error(msg)
    return name


def _candidate_key(candidate: Mapping[str, Any]) -> str:
    key = str(candidate.get("candidate_key") or "").strip()
    if not key:
        msg = "candidate_key is required for exact reference isolation"
        raise domain_error(msg)
    return key


def canonical_axes_for_candidate(
    candidate: Mapping[str, Any],
    *,
    registry: ParameterSpecRegistry | None = None,
) -> tuple[str, ...]:
    active_registry = registry or get_parameter_spec_registry()
    spec = active_registry.get(_parameter_name(candidate))
    if spec is not None:
        return spec.key_axes
    axes = tuple(basecase_slot_axis_names_from_candidate(dict(candidate)))
    if len(axes) != len(set(axes)):
        msg = f"candidate canonical axes contain duplicates: {axes!r}"
        raise domain_error(msg)
    return axes


def _derived_unregistered_axes(
    records: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    if not records:
        return ()
    first_axes = tuple(str(axis_name) for axis_name in (records[0].get("axes") or {}))
    expected = set(first_axes)
    for record in records[1:]:
        actual = {str(axis_name) for axis_name in (record.get("axes") or {})}
        if actual != expected:
            msg = "unregistered parameter basecase records do not share one canonical axis schema"
            raise domain_error(
                msg,
            )
    return first_axes


def build_basecase_index(  # noqa: C901
    basecase_records: Sequence[Mapping[str, Any]],
    candidates: Sequence[Mapping[str, Any]],
    *,
    policy: LutLoadPolicy | None = None,
    registry: ParameterSpecRegistry | None = None,
) -> BasecaseIndex:
    active_policy = policy or LutLoadPolicy()
    active_registry = registry or get_parameter_spec_registry()
    candidate_by_key = {_candidate_key(candidate): candidate for candidate in candidates}
    if len(candidate_by_key) != len(candidates):
        msg = "candidate_key values must be unique"
        raise domain_error(msg)

    raw_by_candidate: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for raw_record in basecase_records:
        candidate_key = str(raw_record.get("candidate_key") or "").strip()
        if candidate_key not in candidate_by_key:
            msg = f"basecase record references an unknown candidate_key: {candidate_key!r}"
            raise domain_error(msg)
        raw_by_candidate[candidate_key].append(raw_record)

    candidate_parameters: dict[str, str] = {}
    candidate_key_axes: dict[str, tuple[str, ...]] = {}
    candidate_metadata_axes: dict[str, tuple[str, ...]] = {}
    mutable_index: dict[str, dict[CanonicalKey, BasecaseReference]] = {}
    all_records: list[BasecaseReference] = []

    for candidate_key, candidate in candidate_by_key.items():
        parameter_name = _parameter_name(candidate)
        spec = active_registry.get(parameter_name)
        key_axes = canonical_axes_for_candidate(candidate, registry=active_registry)
        if spec is None and not key_axes and raw_by_candidate.get(candidate_key):
            key_axes = _derived_unregistered_axes(raw_by_candidate[candidate_key])
        metadata_axes = spec.metadata_axes if spec is not None else ()
        candidate_parameters[candidate_key] = parameter_name
        candidate_key_axes[candidate_key] = key_axes
        candidate_metadata_axes[candidate_key] = metadata_axes
        by_key: dict[CanonicalKey, BasecaseReference] = {}

        for raw_record in raw_by_candidate.get(candidate_key, []):
            raw_axes = raw_record.get("axes") or {}
            if not isinstance(raw_axes, Mapping):
                msg = f"basecase axes must be a mapping: candidate={candidate_key}"
                raise domain_error(msg)
            axes = {axis_name: canonical_axis_value(axis_name, raw_axes.get(axis_name)) for axis_name in key_axes}
            year = axes.get("Year")
            if isinstance(year, int) and not active_policy.contains_year(year):
                continue
            metadata = {
                axis_name: canonical_axis_value(axis_name, raw_axes.get(axis_name)) for axis_name in metadata_axes
            }
            canonical_key = canonical_key_from_axes(axes, key_axes)
            reference_id = str(raw_record.get("reference_id") or "").strip()
            if not reference_id:
                msg = f"basecase reference_id is required: candidate={candidate_key}"
                raise domain_error(msg)
            record = BasecaseReference(
                candidate_key=candidate_key,
                parameter_name=parameter_name,
                canonical_key=canonical_key,
                axes=freeze_mapping(axes),
                value=strict_float(
                    raw_record.get("value"),
                    label=f"basecase value for {candidate_key}:{reference_id}",
                ),
                metadata=freeze_mapping(metadata),
                reference_id=reference_id,
            )
            previous = by_key.get(canonical_key)
            if previous is not None:
                if previous.value == record.value and dict(previous.metadata) == dict(record.metadata):
                    continue
                msg = f"conflicting duplicate basecase exact key: candidate={candidate_key}, key={canonical_key!r}"
                raise domain_error(
                    msg,
                )
            by_key[canonical_key] = record
            all_records.append(record)
        mutable_index[candidate_key] = by_key

    immutable_index = MappingProxyType(
        {candidate_key: MappingProxyType(dict(records)) for candidate_key, records in mutable_index.items()},
    )
    return BasecaseIndex(
        policy=active_policy,
        records=tuple(all_records),
        candidate_parameters=MappingProxyType(candidate_parameters),
        candidate_key_axes=MappingProxyType(candidate_key_axes),
        candidate_metadata_axes=MappingProxyType(candidate_metadata_axes),
        _by_candidate=immutable_index,
    )


def _sort_key(values: tuple[CanonicalValue, ...]) -> tuple[str, ...]:
    return tuple(f"{type(value).__name__}:{value}" for value in values)


def build_slot_catalog(
    basecase_index: BasecaseIndex,
    lut_catalog: LutCatalog | None = None,
) -> SlotCatalog:
    if lut_catalog is not None and lut_catalog.policy != basecase_index.policy:
        msg = "basecase and LUT catalogs must use the same proposal horizon"
        raise domain_error(msg)
    candidate_catalogs: list[CandidateSlotCatalog] = []
    by_candidate: dict[str, CandidateSlotCatalog] = {}
    for candidate_key, parameter_name in basecase_index.candidate_parameters.items():
        key_axes = basecase_index.candidate_key_axes[candidate_key]
        union_axes: dict[CanonicalKey, Mapping[str, CanonicalValue]] = {
            record.canonical_key: record.axes for record in basecase_index.records_for_candidate(candidate_key)
        }
        if lut_catalog is not None:
            spec = lut_catalog.registry.get(parameter_name)
            if spec is not None:
                if spec.key_axes != key_axes:
                    msg = f"basecase/LUT canonical key axes differ for {parameter_name}"
                    raise domain_error(
                        msg,
                    )
                for record in lut_catalog.records_for_parameter(parameter_name):
                    union_axes.setdefault(record.canonical_key, record.axes)

        time_axes = tuple(axis_name for axis_name in key_axes if axis_name in TIME_AXES)
        non_time_axes = tuple(axis_name for axis_name in key_axes if axis_name not in TIME_AXES)
        periods_by_leaf: dict[
            tuple[CanonicalValue, ...],
            set[tuple[int, ...]],
        ] = defaultdict(set)
        for axes in union_axes.values():
            leaf_key = tuple(axes[axis_name] for axis_name in non_time_axes)
            period_key = tuple(int(axes[axis_name]) for axis_name in time_axes)
            periods_by_leaf[leaf_key].add(period_key)

        leaves: list[SlotLeaf] = []
        for leaf_key in sorted(periods_by_leaf, key=_sort_key):
            leaf_axes = freeze_mapping(dict(zip(non_time_axes, leaf_key, strict=True)))
            periods = tuple(
                SlotPeriod(
                    values=freeze_mapping(dict(zip(time_axes, period, strict=True))),
                )
                for period in sorted(periods_by_leaf[leaf_key])
            )
            leaves.append(SlotLeaf(axes=leaf_axes, available_periods=periods))
        candidate_catalog = CandidateSlotCatalog(
            candidate_key=candidate_key,
            parameter_name=parameter_name,
            key_axes=key_axes,
            non_time_axes=non_time_axes,
            time_axes=time_axes,
            leaves=tuple(leaves),
        )
        candidate_catalogs.append(candidate_catalog)
        by_candidate[candidate_key] = candidate_catalog
    return SlotCatalog(
        candidates=tuple(candidate_catalogs),
        _by_candidate=MappingProxyType(by_candidate),
    )


def resolve_effective_reference(  # noqa: C901
    candidate_key: str,
    axes: Mapping[str, Any],
    basecase_index: BasecaseIndex,
    lut_catalog: LutCatalog | None = None,
) -> EffectiveReference | None:
    if lut_catalog is not None and lut_catalog.policy != basecase_index.policy:
        msg = "basecase and LUT catalogs must use the same proposal horizon"
        raise domain_error(msg)
    parameter_name = basecase_index.candidate_parameters.get(candidate_key)
    key_axes = basecase_index.candidate_key_axes.get(candidate_key)
    if parameter_name is None or key_axes is None:
        msg = f"unknown candidate_key: {candidate_key}"
        raise domain_error(msg)
    canonical_key = canonical_key_from_axes(axes, key_axes)
    basecase = basecase_index.lookup(candidate_key, axes)
    lut_record = None
    lut_version = None
    if lut_catalog is not None:
        spec = lut_catalog.registry.get(parameter_name)
        if spec is not None:
            if spec.key_axes != key_axes:
                msg = f"basecase/LUT canonical key axes differ for {parameter_name}"
                raise domain_error(msg)
            lut_record = lut_catalog.lookup(parameter_name, axes)
            lut_version = lut_catalog.version
    if basecase is None and lut_record is None:
        return None

    effective_source = "basecase" if basecase is not None else "lut"
    selected = basecase or lut_record
    if selected is None:
        return None
    diagnostics: list[str] = []
    if basecase is not None and lut_record is not None:
        diagnostics.append("actual_basecase_overrides_lut_default")
    elif basecase is not None:
        diagnostics.append("basecase_only")
    else:
        diagnostics.append("lut_only")
    if lut_record is not None:
        diagnostics.extend(lut_record.diagnostics)
    return EffectiveReference(
        candidate_key=candidate_key,
        parameter_name=parameter_name,
        canonical_slot_key=canonical_key,
        axes=selected.axes,
        metadata=basecase.metadata if basecase is not None else selected.metadata,
        actual_basecase_value=basecase.value if basecase is not None else None,
        lut_default_value=lut_record.value if lut_record is not None else None,
        llm_reference_value=basecase.value if basecase is not None else selected.value,
        effective_source=effective_source,
        basecase_reference_id=basecase.reference_id if basecase is not None else None,
        lut_reference_id=lut_record.reference_id if lut_record is not None else None,
        lut_version=lut_version,
        diagnostics=tuple(diagnostics),
    )
