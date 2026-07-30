from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.persistence.scenario.schema import DimensionDefinition


PressureBand = Literal[
    "strong_bullish",
    "bullish",
    "balanced",
    "bearish",
    "strong_bearish",
]

PRESSURE_BANDS: tuple[PressureBand, ...] = (
    "strong_bullish",
    "bullish",
    "balanced",
    "bearish",
    "strong_bearish",
)
PRESSURE_RANK: dict[str, int] = {
    "strong_bearish": 0,
    "bearish": 1,
    "balanced": 2,
    "bullish": 3,
    "strong_bullish": 4,
}


class EventShock(ApiModel):
    event_id: int
    supply_direction: Literal["increase", "decrease", "neutral", "not_applicable"]
    demand_direction: Literal["increase", "decrease", "neutral", "not_applicable"]
    trade_direction: Literal["increase", "decrease", "neutral", "not_applicable"]
    affected_regions: list[str] = Field(default_factory=list)
    duration: str
    intensity: str
    recovery_or_persistence: str
    mitigation: str
    source_dimension_keys: list[str]
    generated_event_values: dict[str, str]


class EventInteraction(ApiModel):
    event_ids: list[int]
    relation: Literal[
        "amplification",
        "offset",
        "causal_link",
        "regional_coupling",
        "interpretation_conflict",
        "independent",
    ]
    rationale: str = Field(min_length=1)
    resolution_dimension_id: str | None = None

    @model_validator(mode="after")
    def _validate_interaction(self) -> EventInteraction:
        if len(self.event_ids) != len(set(self.event_ids)):
            raise ValueError("interaction eventIds must not contain duplicates")
        if len(self.event_ids) < 2:
            raise ValueError("interaction must reference at least two distinct events")
        if self.relation == "interpretation_conflict" and not self.resolution_dimension_id:
            raise ValueError(
                "interpretation conflicts require a resolution_dimension_id",
            )
        return self


class ScenarioCandidate(ApiModel):
    title: str = Field(min_length=1)
    narrative: str = Field(min_length=1)
    dimension_values: dict[str, str]
    global_pressure_band: PressureBand
    probability_score: int = Field(ge=0, le=100)
    global_pressure_rationale: str = Field(min_length=1)
    mixed_factors: bool = False
    scenario_role: Literal["floor", "ceiling", "mixed"] | None = None
    baseline_yn: Literal["Y", "N"] = "N"


class ExcludedGenerationCandidate(ApiModel):
    global_pressure_band: PressureBand
    reason_code: Literal[
        "LOW_PROBABILITY",
        "FACT_INCONSISTENCY",
        "ELEMENT_CONTRADICTION",
        "NOT_INDEPENDENT",
    ]
    reason: str = Field(min_length=1)


class MultiEventGenerationResult(ApiModel):
    scenario_group_title: str = Field(min_length=1)
    scenario_group_description: str = Field(min_length=1)
    event_shocks: list[EventShock]
    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_definitions: list[DimensionDefinition]
    scenarios: list[ScenarioCandidate]
    excluded_candidates: list[ExcludedGenerationCandidate] = Field(
        default_factory=list,
    )
    excluded_dimensions: list[dict[str, object]] = Field(default_factory=list)


def finalize_generation_result(
    result: MultiEventGenerationResult,
    *,
    generation_strategy: str,
    event_ids: list[int],
    source_dimensions_by_event: (dict[int, dict[str, bool | dict[str, object]]] | None) = None,
) -> MultiEventGenerationResult:
    """Validate the LLM result and deterministically assign roles/baseline."""
    if generation_strategy not in {
        "multi_event_source_dimensions",
        "multi_event_composite_dimensions",
    }:
        raise ValueError(
            f"unsupported multi-event generation strategy: {generation_strategy}",
        )
    dimensions = result.dimension_definitions
    expected_dimension_range = range(5, 9) if generation_strategy == "multi_event_source_dimensions" else range(4, 8)
    if len(dimensions) not in expected_dimension_range:
        raise ValueError(
            f"{generation_strategy} dimension count is out of range: {len(dimensions)}",
        )

    dimension_ids = [dimension.dimension_id for dimension in dimensions]
    if len(set(dimension_ids)) != len(dimension_ids):
        raise ValueError("dimensionDefinitions contains duplicate dimensionId")

    known_event_ids = set(event_ids)
    shock_event_ids = [shock.event_id for shock in result.event_shocks]
    if set(shock_event_ids) != known_event_ids or len(shock_event_ids) != len(
        known_event_ids,
    ):
        raise ValueError("eventShocks must contain every input event exactly once")
    if source_dimensions_by_event is not None:
        for shock in result.event_shocks:
            if not shock.source_dimension_keys:
                raise ValueError(
                    f"EventShock must select a source dimension: {shock.event_id}",
                )
            if len(set(shock.source_dimension_keys)) != len(
                shock.source_dimension_keys,
            ):
                raise ValueError(
                    f"EventShock contains duplicate sourceDimensionKeys: {shock.event_id}",
                )
            if set(shock.generated_event_values) != set(
                shock.source_dimension_keys,
            ):
                raise ValueError(
                    f"EventShock generatedEventValues must match sourceDimensionKeys: eventId={shock.event_id}",
                )
            unknown_keys = set(shock.source_dimension_keys) - set(
                source_dimensions_by_event.get(shock.event_id, {}),
            )
            if unknown_keys:
                raise ValueError(
                    "EventShock sourceDimensionKeys are not present in the "
                    f"Event Type Template: eventId={shock.event_id}, "
                    f"dimKeys={sorted(unknown_keys)}",
                )
    covered_event_ids: set[int] = set()
    for dimension in dimensions:
        if not dimension.source_refs:
            raise ValueError(
                f"dimension has no sourceRefs: {dimension.dimension_id}",
            )
        source_keys = [
            (
                source.event_id,
                source.event_type_l2_id,
                source.dim_key,
            )
            for source in dimension.source_refs
        ]
        if len(set(source_keys)) != len(source_keys):
            raise ValueError(
                f"dimension contains duplicate sourceRefs: {dimension.dimension_id}",
            )
        ref_event_ids = {source.event_id for source in dimension.source_refs}
        if not ref_event_ids <= known_event_ids:
            raise ValueError(
                f"dimension references an unknown event: {dimension.dimension_id}",
            )
        covered_event_ids.update(ref_event_ids)
        if source_dimensions_by_event is not None:
            for source in dimension.source_refs:
                source_definition = source_dimensions_by_event.get(
                    source.event_id,
                    {},
                ).get(source.dim_key)
                if source_definition is None:
                    raise ValueError(
                        "dimension sourceRef is not present in the Event Type "
                        f"Template: eventId={source.event_id}, "
                        f"dimKey={source.dim_key}",
                    )
                if (
                    isinstance(source_definition, dict)
                    and source_definition.get("event_type_l2_id") is not None
                    and source.event_type_l2_id != int(source_definition["event_type_l2_id"])
                ):
                    raise ValueError(
                        "dimension sourceRef eventTypeL2Id does not match the "
                        f"Event Type Template: eventId={source.event_id}",
                    )
        if generation_strategy == "multi_event_source_dimensions":
            if len(dimension.source_refs) != 1:
                raise ValueError("v2 dimensions must have exactly one sourceRef")
            source = dimension.source_refs[0]
            expected_key = f"e{source.event_id}__{source.dim_key}"
            if dimension.dimension_id != expected_key:
                raise ValueError(
                    f"v2 dimensionId must be namespaced as {expected_key}",
                )
            if source_dimensions_by_event is not None:
                source_definition = source_dimensions_by_event.get(
                    source.event_id,
                    {},
                ).get(source.dim_key)
                if isinstance(source_definition, dict):
                    expected_label = str(
                        source_definition.get("label") or source.dim_key,
                    )
                    expected_description = str(
                        source_definition.get("description") or expected_label,
                    )
                    if (
                        dimension.label != expected_label
                        or dimension.description != expected_description
                        or dimension.required != bool(source_definition.get("required", False))
                    ):
                        raise ValueError(
                            "v2 dimensions must preserve the source template "
                            "label, description and required flag: "
                            f"{dimension.dimension_id}",
                        )
        if not 3 <= len(dimension.values) <= 5:
            raise ValueError(
                f"multi-event dimensions must define 3 to 5 generated values: {dimension.dimension_id}",
            )
        for value in dimension.values:
            if value.global_pressure_contribution not in {
                "bullish",
                "balanced",
                "bearish",
            }:
                raise ValueError(
                    "dimension values require a valid "
                    "globalPressureContribution: "
                    f"{dimension.dimension_id}={value.value_id}",
                )
            if not value.source_assignments:
                raise ValueError(
                    f"dimension value has no sourceAssignments: {value.value_id}",
                )
            assignment_event_ids = {assignment.event_id for assignment in value.source_assignments}
            if not assignment_event_ids <= ref_event_ids:
                raise ValueError(
                    "value sourceAssignments must project to the dimension sourceRefs",
                )
            assignment_keys = {
                (
                    assignment.event_id,
                    assignment.event_type_l2_id,
                    assignment.dim_key,
                )
                for assignment in value.source_assignments
            }
            if assignment_keys != set(source_keys):
                raise ValueError(
                    f"each dimension value must project to every sourceRef: {dimension.dimension_id}={value.value_id}",
                )
            if generation_strategy == "multi_event_source_dimensions" and len(value.source_assignments) != 1:
                raise ValueError(
                    "v2 dimension values must have exactly one sourceAssignment",
                )
    if covered_event_ids != known_event_ids:
        missing = sorted(known_event_ids - covered_event_ids)
        raise ValueError(f"events without a selected dimension: {missing}")
    for interaction in result.interactions:
        if not set(interaction.event_ids) <= known_event_ids:
            raise ValueError("interaction references an unknown event")
        if interaction.resolution_dimension_id is not None and interaction.resolution_dimension_id not in dimension_ids:
            raise ValueError(
                "interaction resolutionDimensionId is not a generated dimension",
            )
        if interaction.resolution_dimension_id is not None:
            resolution_dimension = next(
                dimension for dimension in dimensions if dimension.dimension_id == interaction.resolution_dimension_id
            )
            resolution_events = {source.event_id for source in resolution_dimension.source_refs}
            if not set(interaction.event_ids) <= resolution_events:
                raise ValueError(
                    "an interaction resolution dimension must reference every interaction event",
                )
        if interaction.relation != "independent":
            interaction_events = set(interaction.event_ids)
            if not any(
                interaction_events <= {source.event_id for source in dimension.source_refs} for dimension in dimensions
            ):
                raise ValueError(
                    "non-independent interactions must be represented by a multi-source dimension",
                )

    if generation_strategy == "multi_event_source_dimensions" and source_dimensions_by_event is not None:
        for item in result.excluded_dimensions:
            event_id = int(
                item.get("event_id") or item.get("eventId") or 0,
            )
            dim_key = str(
                item.get("dim_key") or item.get("dimKey") or "",
            )
            if (
                event_id not in known_event_ids
                or dim_key not in source_dimensions_by_event.get(event_id, {})
                or not str(item.get("reason") or "").strip()
            ):
                raise ValueError(
                    "v2 excludedDimensions require a valid eventId, template dimKey and reason",
                )
        selected_sources = {
            (source.event_id, source.dim_key) for dimension in dimensions for source in dimension.source_refs
        }
        required_sources = {
            (event_id, dim_key)
            for event_id, source_dimensions in source_dimensions_by_event.items()
            for dim_key, definition in source_dimensions.items()
            if (bool(definition.get("required", False)) if isinstance(definition, dict) else definition)
        }
        omitted_required = required_sources - selected_sources
        if len(required_sources) <= 8 and omitted_required:
            raise ValueError(
                "v2 must select every required source dimension when the "
                f"required count is at most 8: {sorted(omitted_required)}",
            )
        if len(required_sources) > 8:
            documented_exclusions = {
                (
                    int(item.get("event_id") or item.get("eventId") or 0),
                    str(item.get("dim_key") or item.get("dimKey") or ""),
                )
                for item in result.excluded_dimensions
                if isinstance(item, dict) and item.get("reason")
            }
            undocumented = omitted_required - documented_exclusions
            if undocumented:
                raise ValueError(
                    f"omitted required v2 dimensions need an LNG relevance exclusion reason: {sorted(undocumented)}",
                )

    scenarios = sorted(
        result.scenarios,
        key=lambda scenario: PRESSURE_RANK[scenario.global_pressure_band],
        reverse=True,
    )
    if not 3 <= len(scenarios) <= 5:
        raise ValueError("final scenario count must be between 3 and 5")
    pressure_bands = [scenario.global_pressure_band for scenario in scenarios]
    if len(set(pressure_bands)) != len(pressure_bands):
        raise ValueError("final scenarios must have unique globalPressureBand values")
    excluded_bands = [candidate.global_pressure_band for candidate in result.excluded_candidates]
    if set(pressure_bands) & set(excluded_bands):
        raise ValueError("a pressure band cannot be both generated and excluded")
    if set(pressure_bands) | set(excluded_bands) != set(PRESSURE_BANDS):
        raise ValueError(
            "generated and excluded candidates must account for all target pressure bands",
        )

    expected_keys = set(dimension_ids)
    allowed_values = {
        dimension.dimension_id: {value.value_id for value in dimension.values}
        | {value.label for value in dimension.values}
        for dimension in dimensions
    }
    contribution_by_value = {
        dimension.dimension_id: {value.value_id: value.global_pressure_contribution for value in dimension.values}
        | {value.label: value.global_pressure_contribution for value in dimension.values}
        for dimension in dimensions
    }
    combinations: set[tuple[tuple[str, str], ...]] = set()
    for scenario in scenarios:
        if set(scenario.dimension_values) != expected_keys:
            raise ValueError(
                f"scenario cells must match all dimension definitions: {scenario.title}",
            )
        for dimension_id, value in scenario.dimension_values.items():
            if value not in allowed_values[dimension_id]:
                raise ValueError(
                    f"scenario value is missing from dimensionDefinitions.values: {dimension_id}={value}",
                )
        combination = tuple(sorted(scenario.dimension_values.items()))
        if combination in combinations:
            raise ValueError("scenario dimension combinations must be unique")
        combinations.add(combination)
        contributions = {
            contribution_by_value[dimension_id][value] for dimension_id, value in scenario.dimension_values.items()
        }
        if (
            scenario.mixed_factors
            and not {
                "bullish",
                "bearish",
            }
            <= contributions
        ):
            raise ValueError(
                f"mixedFactors=true requires both bullish and bearish dimension contributions: {scenario.title}",
            )

    ranked = sorted(
        range(len(scenarios)),
        key=lambda index: PRESSURE_RANK[scenarios[index].global_pressure_band],
    )
    if len(ranked) < 3:
        raise ValueError("floor, ceiling and mixed roles require three scenarios")
    floor_index = ranked[0]
    ceiling_index = ranked[-1]
    interior = [index for index in ranked[1:-1] if scenarios[index].mixed_factors]
    if not interior:
        raise ValueError("at least one interior scenario must combine bullish and bearish factors")
    mixed_index = min(
        interior,
        key=lambda index: abs(PRESSURE_RANK[scenarios[index].global_pressure_band] - PRESSURE_RANK["balanced"]),
    )
    baseline_index = max(
        range(len(scenarios)),
        key=lambda index: (scenarios[index].probability_score, -index),
    )

    finalized: list[ScenarioCandidate] = []
    for index, scenario in enumerate(scenarios):
        if index == floor_index:
            role = "floor"
        elif index == ceiling_index:
            role = "ceiling"
        elif index == mixed_index:
            role = "mixed"
        else:
            role = None
        finalized.append(
            scenario.model_copy(
                update={
                    "scenario_role": role,
                    "baseline_yn": "Y" if index == baseline_index else "N",
                },
            ),
        )
    return result.model_copy(update={"scenarios": finalized})
