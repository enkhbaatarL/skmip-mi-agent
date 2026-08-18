from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def build_v4_scenario_context(
    scenario: Mapping[str, Any],
    *,
    dimension_definitions: Sequence[Mapping[str, Any]],
    generation_diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    """Build prompt-only v4 Scenario context without trusting stale title matches."""
    normalized_values = _normalize_dimension_values(
        _mapping(_read(scenario, "dimension_values", "dimensionValues", default={})),
        dimension_definitions,
    )
    breakdown = _matching_pressure_breakdown(
        normalized_values,
        dimension_definitions=dimension_definitions,
        generation_diagnostics=generation_diagnostics,
    )
    impact_paths, interactions = _causal_evidence(
        breakdown,
        generation_diagnostics=generation_diagnostics,
    )
    return {
        "title": _text(_read(scenario, "title")),
        "narrative": _text(_read(scenario, "narrative")) or _text(_read(scenario, "description")),
        "probability": _read(scenario, "probability_score", "probabilityScore"),
        "baseline": _text(_read(scenario, "baseline_yn", "baselineYn")) or "N",
        "role": _text(_read(scenario, "scenario_role", "scenarioRole")),
        "jkm_pressure_band": _text(
            _read(scenario, "global_pressure_band", "globalPressureBand"),
        ),
        "pressure_rationale": _text(
            _read(scenario, "global_pressure_rationale", "globalPressureRationale"),
        ),
        "related_markets": _related_markets(
            _read(scenario, "related_markets", "relatedMarkets", default=[]),
        ),
        "dimension_selections": _dimension_selections(
            normalized_values,
            dimension_definitions=dimension_definitions,
        ),
        "impact_paths": impact_paths,
        "interactions": interactions,
    }


def _dimension_selections(
    normalized_values: Mapping[str, str],
    *,
    dimension_definitions: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    definitions_by_id = {
        dimension_id: definition
        for definition in dimension_definitions
        if (dimension_id := _text(_read(definition, "dimension_id", "dimensionId")))
    }
    ordered_dimension_ids = [
        dimension_id
        for definition in dimension_definitions
        if (dimension_id := _text(_read(definition, "dimension_id", "dimensionId"))) in normalized_values
    ]
    ordered_dimension_ids.extend(
        dimension_id for dimension_id in normalized_values if dimension_id not in definitions_by_id
    )

    selections: list[dict[str, str]] = []
    for dimension_id in ordered_dimension_ids:
        value_id = normalized_values[dimension_id]
        definition = definitions_by_id.get(dimension_id, {})
        value_definition = next(
            (
                item
                for item in _mapping_items(_read(definition, "values", default=[]))
                if value_id == _text(_read(item, "value_id", "valueId"))
            ),
            {},
        )
        selections.append(
            {
                "dimension_id": dimension_id,
                "dimension_label": _text(_read(definition, "label")) or dimension_id,
                "dimension_description": _text(_read(definition, "description")),
                "dimension_rationale": _text(_read(definition, "rationale")),
                "value_id": value_id,
                "value_label": _text(_read(value_definition, "label")) or value_id,
                "assumption_rationale": _text(
                    _read(value_definition, "assumption_rationale", "assumptionRationale"),
                ),
            },
        )
    return selections


def _matching_pressure_breakdown(
    normalized_values: Mapping[str, str],
    *,
    dimension_definitions: Sequence[Mapping[str, Any]],
    generation_diagnostics: Mapping[str, Any],
) -> Mapping[str, Any] | None:
    if not normalized_values:
        return None
    breakdowns = _mapping_items(
        _read(
            generation_diagnostics,
            "scenario_pressure_breakdowns",
            "scenarioPressureBreakdowns",
            default=[],
        ),
    )
    for breakdown in breakdowns:
        candidate_values = _normalize_dimension_values(
            _mapping(_read(breakdown, "dimension_values", "dimensionValues", default={})),
            dimension_definitions,
        )
        if candidate_values == normalized_values:
            return breakdown
    return None


def _causal_evidence(
    breakdown: Mapping[str, Any] | None,
    *,
    generation_diagnostics: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if breakdown is None:
        return [], []

    path_by_id = {
        path_id: path
        for path in _mapping_items(
            _read(generation_diagnostics, "impact_paths", "impactPaths", default=[]),
        )
        if (path_id := _text(_read(path, "impact_path_id", "impactPathId")))
    }
    interaction_by_id = {
        interaction_id: interaction
        for interaction in _mapping_items(
            _read(generation_diagnostics, "event_interactions", "eventInteractions", default=[]),
        )
        if (interaction_id := _text(_read(interaction, "interaction_id", "interactionId")))
    }
    paths = [
        {
            "event_id": _read(path, "event_id", "eventId"),
            "mechanism": _text(_read(path, "mechanism")),
        }
        for path_id in _text_items(
            _read(breakdown, "common_impact_path_ids", "commonImpactPathIds", default=[]),
        )
        if (path := path_by_id.get(path_id)) is not None
    ]
    interactions = [
        {
            "event_ids": _list(_read(interaction, "event_ids", "eventIds", default=[])),
            "mechanism": _text(_read(interaction, "mechanism")),
        }
        for interaction_id in _text_items(
            _read(breakdown, "applied_interaction_ids", "appliedInteractionIds", default=[]),
        )
        if (interaction := interaction_by_id.get(interaction_id)) is not None
    ]
    return paths, interactions


def _normalize_dimension_values(
    values: Mapping[str, Any],
    definitions: Sequence[Mapping[str, Any]],
) -> dict[str, str]:
    definition_by_alias: dict[str, Mapping[str, Any]] = {}
    for definition in definitions:
        dimension_id = _text(_read(definition, "dimension_id", "dimensionId"))
        if not dimension_id:
            continue
        definition_by_alias[dimension_id] = definition
        label = _text(_read(definition, "label"))
        if label:
            definition_by_alias[label] = definition

    normalized: dict[str, str] = {}
    for raw_dimension, raw_value in values.items():
        dimension_alias = _text(raw_dimension)
        if not dimension_alias:
            continue
        definition = definition_by_alias.get(dimension_alias, {})
        dimension_id = _text(_read(definition, "dimension_id", "dimensionId")) or dimension_alias
        value_alias = _text(raw_value)
        canonical_value = value_alias
        for value_definition in _mapping_items(_read(definition, "values", default=[])):
            value_id = _text(_read(value_definition, "value_id", "valueId"))
            value_label = _text(_read(value_definition, "label"))
            if value_alias in {value_id, value_label}:
                canonical_value = value_id or value_alias
                break
        normalized[dimension_id] = canonical_value
    return normalized


def _related_markets(value: object) -> list[dict[str, str]]:
    return [
        {
            "market": _text(_read(item, "market")),
            "rationale": _text(_read(item, "rationale")),
        }
        for item in _mapping_items(value)
    ]


def _read(mapping: Mapping[str, Any], *keys: str, default: object = None) -> object:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return default


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _mapping_items(value: object) -> list[Mapping[str, Any]]:
    return [item for item in _list(value) if isinstance(item, Mapping)]


def _list(value: object) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _text_items(value: object) -> list[str]:
    return [text for item in _list(value) if (text := _text(item))]


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


__all__ = ["build_v4_scenario_context"]
