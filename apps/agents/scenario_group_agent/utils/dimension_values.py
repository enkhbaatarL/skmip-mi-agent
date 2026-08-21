from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

# ruff: noqa: ANN401, CPY001
from apps.common.logging.logger_config import logger


def _field(payload: Mapping[str, Any], snake_key: str, camel_key: str) -> Any:
    return payload.get(snake_key, payload.get(camel_key))


@dataclass(frozen=True, slots=True)
class DimensionValueCatalog:
    ordered_dimension_ids: list[str]
    value_ids_by_dimension: dict[str, frozenset[str]]
    unique_value_id_by_label: dict[str, dict[str, str]]
    dimension_by_value_id: dict[str, str]


def build_dimension_value_catalog(
    dimension_definitions: Sequence[Mapping[str, Any]],
) -> DimensionValueCatalog:
    ordered_dimension_ids: list[str] = []
    value_ids_by_dimension: dict[str, frozenset[str]] = {}
    unique_value_id_by_label: dict[str, dict[str, str]] = {}
    dimension_by_value_id: dict[str, str] = {}
    for definition in dimension_definitions:
        dimension_id = str(_field(definition, "dimension_id", "dimensionId") or "").strip()
        if not dimension_id:
            continue
        ordered_dimension_ids.append(dimension_id)
        value_ids: set[str] = set()
        labels: dict[str, list[str]] = {}
        for raw_value in definition.get("values") or []:
            if not isinstance(raw_value, Mapping):
                continue
            value_id = str(_field(raw_value, "value_id", "valueId") or "").strip()
            label = str(raw_value.get("label") or "").strip()
            if not value_id:
                continue
            value_ids.add(value_id)
            dimension_by_value_id[value_id] = dimension_id
            if label:
                labels.setdefault(label, []).append(value_id)
        value_ids_by_dimension[dimension_id] = frozenset(value_ids)
        unique_value_id_by_label[dimension_id] = {
            label: ids[0] for label, ids in labels.items() if len(ids) == 1
        }
    return DimensionValueCatalog(
        ordered_dimension_ids=ordered_dimension_ids,
        value_ids_by_dimension=value_ids_by_dimension,
        unique_value_id_by_label=unique_value_id_by_label,
        dimension_by_value_id=dimension_by_value_id,
    )


def canonicalize_dimension_value(
    catalog: DimensionValueCatalog,
    dimension_id: str,
    raw_value: object,
    *,
    allow_label_compatibility: bool,
) -> str:
    if raw_value is None or not str(raw_value).strip():
        msg = f"Dimension value is empty: {dimension_id}"
        raise ValueError(msg)
    value = str(raw_value)
    if value in catalog.value_ids_by_dimension.get(dimension_id, frozenset()):
        return value
    owner = catalog.dimension_by_value_id.get(value)
    if owner is not None and owner != dimension_id:
        msg = f"Value belongs to another Dimension: {dimension_id}={value} (owner={owner})"
        raise ValueError(msg)
    if allow_label_compatibility:
        compatible = catalog.unique_value_id_by_label.get(dimension_id, {}).get(value)
        if compatible is not None:
            logger.warning(
                "Deprecated Dimension label compatibility used | dimension_id={} | value_id={}",
                dimension_id,
                compatible,
            )
            return compatible
    msg = f"Unknown Dimension valueId: {dimension_id}={value}"
    raise ValueError(msg)


def canonicalize_dimension_cells(
    catalog: DimensionValueCatalog,
    header_ids: Sequence[str],
    raw_cells: Mapping[str, Any],
    *,
    allow_label_compatibility: bool,
) -> dict[str, str]:
    expected = set(header_ids)
    actual = {str(key) for key in raw_cells}
    if actual != expected:
        msg = (
            "Scenario cell keys do not match headers: "
            f"missing={sorted(expected - actual)}, unknown={sorted(actual - expected)}"
        )
        raise ValueError(msg)
    return {
        dimension_id: canonicalize_dimension_value(
            catalog,
            dimension_id,
            raw_cells[dimension_id],
            allow_label_compatibility=allow_label_compatibility,
        )
        for dimension_id in header_ids
    }


def canonicalize_persisted_dimension_values(
    dimension_definitions: Sequence[Mapping[str, Any]],
    raw_values: Mapping[str, Any],
    *,
    allow_label_compatibility: bool = True,
) -> dict[str, str]:
    catalog = build_dimension_value_catalog(dimension_definitions)
    return canonicalize_dimension_cells(
        catalog,
        catalog.ordered_dimension_ids,
        raw_values,
        allow_label_compatibility=allow_label_compatibility,
    )


def normalize_dimension_value_aliases(
    values: Mapping[str, Any],
    dimension_definitions: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    """Normalize known Dimension/value IDs and unique labels without rejecting legacy data."""
    definitions_by_id: dict[str, Mapping[str, Any]] = {}
    dimension_ids_by_label: dict[str, list[str]] = {}
    for definition in dimension_definitions:
        dimension_id = str(_field(definition, "dimension_id", "dimensionId") or "").strip()
        if not dimension_id:
            continue
        definitions_by_id[dimension_id] = definition
        label = str(definition.get("label") or "").strip()
        if label:
            dimension_ids_by_label.setdefault(label, []).append(dimension_id)
    dimension_id_by_alias = {label: ids[0] for label, ids in dimension_ids_by_label.items() if len(ids) == 1}

    normalized: dict[str, str] = {}
    for raw_dimension, raw_value in values.items():
        dimension_alias = str(raw_dimension or "").strip()
        if not dimension_alias:
            continue
        dimension_id = (
            dimension_alias
            if dimension_alias in definitions_by_id
            else dimension_id_by_alias.get(dimension_alias, dimension_alias)
        )
        definition = definitions_by_id.get(dimension_id)
        value_alias = str(raw_value or "").strip()
        canonical_value = value_alias
        if definition is not None:
            value_ids: set[str] = set()
            value_ids_by_label: dict[str, list[str]] = {}
            for raw_definition_value in definition.get("values") or []:
                if not isinstance(raw_definition_value, Mapping):
                    continue
                value_id = str(_field(raw_definition_value, "value_id", "valueId") or "").strip()
                value_label = str(raw_definition_value.get("label") or "").strip()
                if not value_id:
                    continue
                value_ids.add(value_id)
                if value_label:
                    value_ids_by_label.setdefault(value_label, []).append(value_id)
            if value_alias not in value_ids:
                compatible_ids = value_ids_by_label.get(value_alias, [])
                if len(compatible_ids) == 1:
                    canonical_value = compatible_ids[0]
        normalized[dimension_id] = canonical_value
    return normalized


def find_scenario_pressure_breakdown(
    scenario_dimension_values: Mapping[str, Any],
    *,
    dimension_definitions: Sequence[Mapping[str, Any]],
    generation_diagnostics: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    """Find a diagnostics breakdown by its complete canonical Dimension/value combination."""
    normalized_values = normalize_dimension_value_aliases(
        scenario_dimension_values,
        dimension_definitions,
    )
    if not normalized_values:
        return None
    raw_breakdowns = _field(
        generation_diagnostics,
        "scenario_pressure_breakdowns",
        "scenarioPressureBreakdowns",
    )
    if not isinstance(raw_breakdowns, (list, tuple)):
        return None
    for breakdown in raw_breakdowns:
        if not isinstance(breakdown, Mapping):
            continue
        raw_candidate_values = _field(breakdown, "dimension_values", "dimensionValues")
        if not isinstance(raw_candidate_values, Mapping):
            continue
        candidate_values = normalize_dimension_value_aliases(
            raw_candidate_values,
            dimension_definitions,
        )
        if candidate_values == normalized_values:
            return breakdown
    return None
