from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import Field, model_validator

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    PRESSURE_BANDS,
    PRESSURE_RANK,
    PressureBand,
)
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.persistence.model_parameter.schema import (
    ModelImpactLeverPayload,
    ModelImpactLeverSupportIssue,
)
from apps.persistence.scenario.schema import DimensionDefinition, RelatedMarket


class EventImpactFact(ApiModel):
    event_id: int = Field(gt=0)
    lever_code: str = Field(min_length=1)
    domain: Literal["demand", "supply", "trade", "price_only"]
    change_direction: Literal["increase", "decrease", "neutral"]
    global_pressure_direction: Literal["bullish", "bearish", "neutral"]
    affected_scope: list[str] = Field(default_factory=list)
    timing: str = Field(min_length=1)
    magnitude_evidence: str = Field(min_length=1)
    fact_basis: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)


class EventInteraction(ApiModel):
    event_ids: list[int] = Field(min_length=2)
    relation: Literal[
        "amplification",
        "offset",
        "causal_link",
        "regional_coupling",
        "independent",
    ]
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_events(self) -> EventInteraction:
        if len(set(self.event_ids)) != len(self.event_ids):
            raise ValueError("interaction event_ids must be unique")
        return self


class V4ScenarioCandidate(ApiModel):
    title: str = Field(min_length=1)
    narrative: str = Field(min_length=1)
    dimension_values: dict[str, str]
    global_pressure_band: PressureBand
    global_pressure_rationale: str = Field(min_length=1)
    related_markets: list[RelatedMarket] = Field(default_factory=list, max_length=3)
    probability_score: float = Field(ge=0, le=100)
    mixed_factors: list[str] = Field(default_factory=list)
    scenario_role: Literal["floor", "ceiling", "mixed"] | None = None
    baseline_yn: bool = False

    @model_validator(mode="after")
    def validate_unique_related_markets(self) -> V4ScenarioCandidate:
        markets = [item.market for item in self.related_markets]
        if len(markets) != len(set(markets)):
            raise ValueError("related markets must be unique within a scenario")
        return self


class V4ExcludedScenarioCandidate(ApiModel):
    global_pressure_band: PressureBand
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class V4GenerationResult(ApiModel):
    group_title: str = Field(min_length=1)
    group_description: str = Field(min_length=1)
    event_impact_facts: list[EventImpactFact] = Field(min_length=1)
    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_definitions: list[DimensionDefinition] = Field(
        min_length=3,
        max_length=6,
    )
    scenarios: list[V4ScenarioCandidate] = Field(min_length=3, max_length=5)
    excluded_scenarios: list[V4ExcludedScenarioCandidate] = Field(default_factory=list)
    excluded_dimensions: list[str] = Field(default_factory=list)


class ParameterCoverage(ApiModel):
    covered_dimension_ids: list[str]
    uncovered_dimension_ids: list[str]
    unsupported_lever_codes: list[str]
    unsupported_lever_details: list[ModelImpactLeverSupportIssue]
    coverage_status: Literal["full", "partial", "none"]


def _lever_support_status(
    lever_codes: list[str],
    catalog_by_code: dict[str, ModelImpactLeverPayload],
) -> Literal["full", "partial", "none", "price_only"]:
    levers = [catalog_by_code[code] for code in lever_codes]
    if all(lever.domain == "price_only" for lever in levers):
        return "price_only"

    executable = [
        binding for lever in levers for binding in lever.parameter_bindings if binding.support_status == "executable"
    ]
    unsupported = [
        binding for lever in levers for binding in lever.parameter_bindings if binding.support_status != "executable"
    ]
    has_price_only = any(lever.domain == "price_only" for lever in levers)

    if executable and not unsupported and not has_price_only:
        return "full"
    if executable:
        return "partial"
    return "none"


def _validate_dimensions(
    result: V4GenerationResult,
    event_ids: list[int],
    catalog_by_code: dict[str, ModelImpactLeverPayload],
) -> None:
    dimension_ids = [dimension.dimension_id for dimension in result.dimension_definitions]
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("dimension ids must be unique")

    covered_events: set[int] = set()
    event_id_set = set(event_ids)
    for display_order, dimension in enumerate(result.dimension_definitions, start=1):
        if not dimension.source_event_ids:
            raise ValueError(f"dimension {dimension.dimension_id} must reference source events")
        if not set(dimension.source_event_ids).issubset(event_id_set):
            raise ValueError(f"dimension {dimension.dimension_id} references an unknown event")
        if not dimension.lever_refs:
            raise ValueError(f"dimension {dimension.dimension_id} must reference impact levers")
        unknown_levers = set(dimension.lever_refs) - set(catalog_by_code)
        if unknown_levers:
            raise ValueError(f"dimension {dimension.dimension_id} references unknown levers: {sorted(unknown_levers)}")
        if len(dimension.values) < 2 or len(dimension.values) > 4:
            raise ValueError(f"dimension {dimension.dimension_id} must have 2-4 values")
        if len({value.value_id for value in dimension.values}) != len(dimension.values):
            raise ValueError(f"dimension {dimension.dimension_id} value ids must be unique")

        dimension.model_support_status = _lever_support_status(
            dimension.lever_refs,
            catalog_by_code,
        )
        dimension.required = True
        dimension.display_order = display_order
        covered_events.update(dimension.source_event_ids)

    if covered_events != event_id_set:
        missing = sorted(event_id_set - covered_events)
        raise ValueError(f"all source events must affect a dimension; missing={missing}")
    if not any(
        dimension.model_support_status in {"full", "partial"}
        for dimension in result.dimension_definitions
    ):
        raise ValueError(
            "at least one dimension must reference an executable model parameter binding",
        )


def _validate_event_grounding(
    result: V4GenerationResult,
    event_ids: list[int],
    catalog_by_code: dict[str, ModelImpactLeverPayload],
) -> None:
    fact_event_ids = {fact.event_id for fact in result.event_impact_facts}
    if fact_event_ids != set(event_ids):
        raise ValueError("event impact facts must cover every selected event")

    fact_keys: Counter[tuple[int, str]] = Counter()
    for fact in result.event_impact_facts:
        if fact.lever_code not in catalog_by_code:
            raise ValueError(f"unknown impact lever: {fact.lever_code}")
        expected_domain = catalog_by_code[fact.lever_code].domain
        if fact.domain != expected_domain:
            raise ValueError(f"lever {fact.lever_code} domain must be {expected_domain}")
        fact_keys[(fact.event_id, fact.lever_code)] += 1
    duplicates = [key for key, count in fact_keys.items() if count > 1]
    if duplicates:
        raise ValueError(f"duplicate event impact facts: {duplicates}")

    event_id_set = set(event_ids)
    for interaction in result.interactions:
        if not set(interaction.event_ids).issubset(event_id_set):
            raise ValueError("interaction references an unknown event")


def _validate_scenarios(result: V4GenerationResult) -> None:
    dimension_by_id = {dimension.dimension_id: dimension for dimension in result.dimension_definitions}
    combinations: set[tuple[tuple[str, str], ...]] = set()
    generated_bands: list[PressureBand] = []

    for scenario in result.scenarios:
        if set(scenario.dimension_values) != set(dimension_by_id):
            raise ValueError("every scenario must provide every dimension value")
        for dimension_id, selected_value in scenario.dimension_values.items():
            dimension = dimension_by_id[dimension_id]
            allowed_values = {candidate for value in dimension.values for candidate in (value.value_id, value.label)}
            if selected_value not in allowed_values:
                raise ValueError(f"invalid value {selected_value!r} for dimension {dimension_id}")
        combination = tuple(sorted(scenario.dimension_values.items()))
        if combination in combinations:
            raise ValueError("scenario dimension combinations must be unique")
        combinations.add(combination)
        generated_bands.append(scenario.global_pressure_band)

    if len(set(generated_bands)) != len(generated_bands):
        raise ValueError("generated scenarios must use distinct pressure bands")

    excluded_bands = [scenario.global_pressure_band for scenario in result.excluded_scenarios]
    if set(generated_bands) & set(excluded_bands):
        raise ValueError("generated and excluded pressure bands must not overlap")
    if set(generated_bands + excluded_bands) != set(PRESSURE_BANDS):
        raise ValueError("generated and excluded scenarios must cover all pressure bands")

    ordered = sorted(
        result.scenarios,
        key=lambda scenario: PRESSURE_RANK[scenario.global_pressure_band],
    )
    for scenario in result.scenarios:
        scenario.scenario_role = None
        scenario.baseline_yn = False
    ordered[0].scenario_role = "floor"
    ordered[-1].scenario_role = "ceiling"

    interior = ordered[1:-1]
    if not interior:
        raise ValueError("at least one mixed scenario is required")
    mixed = min(
        interior,
        key=lambda scenario: (
            abs(PRESSURE_RANK[scenario.global_pressure_band] - 2),
            -scenario.probability_score,
        ),
    )
    mixed.scenario_role = "mixed"
    if not mixed.mixed_factors:
        raise ValueError("mixed scenario must explain its offsetting factors")

    baseline = max(result.scenarios, key=lambda scenario: scenario.probability_score)
    baseline.baseline_yn = True
    result.scenarios.sort(
        key=lambda scenario: PRESSURE_RANK[scenario.global_pressure_band],
        reverse=True,
    )


def _lever_support_issues(
    lever: ModelImpactLeverPayload,
) -> list[ModelImpactLeverSupportIssue]:
    if lever.domain == "price_only":
        return [
            ModelImpactLeverSupportIssue(
                lever_code=lever.lever_code,
                reason_code="PRICE_ONLY",
            ),
        ]
    if not lever.parameter_bindings:
        return [
            ModelImpactLeverSupportIssue(
                lever_code=lever.lever_code,
                reason_code="NO_PARAMETER_BINDING",
            ),
        ]
    return [
        ModelImpactLeverSupportIssue(
            lever_code=lever.lever_code,
            reason_code=(binding.unsupported_reason_code or "CATALOG_MARKED_UNSUPPORTED"),
            parameter_name=binding.parameter_name,
        )
        for binding in lever.parameter_bindings
        if binding.support_status == "known_unsupported"
    ]


def build_parameter_coverage(
    result: V4GenerationResult,
    catalog_by_code: dict[str, ModelImpactLeverPayload],
) -> ParameterCoverage:
    covered: list[str] = []
    uncovered: list[str] = []

    for dimension in result.dimension_definitions:
        if dimension.model_support_status == "full":
            covered.append(dimension.dimension_id)
        elif dimension.model_support_status == "partial":
            covered.append(dimension.dimension_id)
            uncovered.append(dimension.dimension_id)
        else:
            uncovered.append(dimension.dimension_id)

    referenced_lever_codes = {
        lever_code for dimension in result.dimension_definitions for lever_code in dimension.lever_refs
    }
    unsupported_details = [
        issue
        for lever_code in sorted(referenced_lever_codes)
        for issue in _lever_support_issues(catalog_by_code[lever_code])
    ]
    unsupported_lever_codes = sorted(
        {detail.lever_code for detail in unsupported_details},
    )

    if covered and not uncovered:
        status: Literal["full", "partial", "none"] = "full"
    elif covered:
        status = "partial"
    else:
        status = "none"
    return ParameterCoverage(
        covered_dimension_ids=covered,
        uncovered_dimension_ids=uncovered,
        unsupported_lever_codes=unsupported_lever_codes,
        unsupported_lever_details=unsupported_details,
        coverage_status=status,
    )


def finalize_v4_generation_result(
    result: V4GenerationResult,
    *,
    event_ids: list[int],
    impact_levers: list[ModelImpactLeverPayload],
) -> tuple[V4GenerationResult, ParameterCoverage]:
    catalog_by_code = {lever.lever_code: lever for lever in impact_levers}
    if not catalog_by_code:
        raise ValueError("active model impact lever catalog is empty")

    _validate_event_grounding(result, event_ids, catalog_by_code)
    _validate_dimensions(result, event_ids, catalog_by_code)
    _validate_scenarios(result)
    return result, build_parameter_coverage(result, catalog_by_code)


__all__ = [
    "EventImpactFact",
    "EventInteraction",
    "ParameterCoverage",
    "V4ExcludedScenarioCandidate",
    "V4GenerationResult",
    "V4ScenarioCandidate",
    "build_parameter_coverage",
    "finalize_v4_generation_result",
]
