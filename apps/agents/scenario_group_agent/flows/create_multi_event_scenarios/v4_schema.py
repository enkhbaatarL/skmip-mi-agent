from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    PRESSURE_BANDS,
    PRESSURE_RANK,
    PressureBand,
    ScenarioDimensionValues,
)
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.persistence.model_parameter.schema import (
    ModelImpactLeverPayload,
    ModelImpactLeverSupportIssue,
)
from apps.persistence.scenario.schema import RelatedMarket


class V4EventGrounding(ApiModel):
    """Compact Event evidence and residual uncertainty owned by one dimension."""

    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(gt=0)
    observed_basis: str = Field(min_length=1)
    uncertainty: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_text(self) -> V4EventGrounding:
        self.observed_basis = self.observed_basis.strip()
        self.uncertainty = self.uncertainty.strip()
        if not self.observed_basis or not self.uncertainty:
            raise ValueError("event grounding text must not be blank")
        return self


class V4LeverMapping(ApiModel):
    """Stable model-impact lever reference with only the mapping explanation."""

    model_config = ConfigDict(extra="forbid")

    impact_lever_id: int | None = Field(default=None, gt=0)
    lever_code: str = Field(min_length=1)
    mapping_rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_mapping(self) -> V4LeverMapping:
        self.lever_code = self.lever_code.strip()
        self.mapping_rationale = self.mapping_rationale.strip()
        if not self.lever_code or not self.mapping_rationale:
            raise ValueError("lever mapping fields must not be blank")
        return self


class V4DimensionValueDefinition(ApiModel):
    """Scenario branch value and the assumption that makes the branch distinct."""

    model_config = ConfigDict(extra="forbid")

    value_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    global_pressure_contribution: str = Field(min_length=1)
    assumption_rationale: str = Field(min_length=1)


class V4DimensionDefinition(ApiModel):
    """v4 grounding, lever mapping, and scenario branch definition."""

    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    dimension_type: Literal[
        "magnitude",
        "scope",
        "timing",
        "recovery",
        "mitigation",
        "interaction",
    ]
    value_kind: Literal["categorical", "numeric_range", "temporal"]
    unit: str | None = None
    event_groundings: list[V4EventGrounding] = Field(min_length=1)
    lever_mappings: list[V4LeverMapping] = Field(min_length=1)
    model_support_status: (
        Literal[
            "full",
            "partial",
            "none",
            "price_only",
        ]
        | None
    ) = None
    values: list[V4DimensionValueDefinition] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def validate_compact_references(self) -> V4DimensionDefinition:
        lever_codes = [mapping.lever_code for mapping in self.lever_mappings]
        if len(lever_codes) != len(set(lever_codes)):
            raise ValueError("dimension leverMappings must contain unique leverCodes")
        value_ids = [value.value_id for value in self.values]
        if len(value_ids) != len(set(value_ids)):
            raise ValueError("dimension values must contain unique valueIds")
        return self


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
    dimension_values: ScenarioDimensionValues
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
    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_definitions: list[V4DimensionDefinition] = Field(min_length=3, max_length=6)
    scenarios: list[V4ScenarioCandidate] = Field(min_length=3, max_length=5)
    excluded_scenarios: list[V4ExcludedScenarioCandidate] = Field(default_factory=list)
    excluded_dimensions: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def apply_generation_defaults(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        aliases = (
            ("interactions", "interactions"),
            ("excludedScenarios", "excluded_scenarios"),
            ("excludedDimensions", "excluded_dimensions"),
        )
        for alias, field_name in aliases:
            if alias not in normalized and field_name not in normalized:
                normalized[alias] = []
        return normalized


class V4DimensionDesignResult(ApiModel):
    """Dimension grounding and lever design created directly from selected Events."""

    model_config = ConfigDict(extra="forbid")

    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_definitions: list[V4DimensionDefinition] = Field(min_length=3, max_length=6)
    excluded_dimensions: list[str] = Field(default_factory=list)


class V4ScenarioSynthesisResult(ApiModel):
    """v4 Scenario-only response based on validated compact dimensions."""

    model_config = ConfigDict(extra="forbid")

    group_title: str = Field(min_length=1)
    group_description: str = Field(min_length=1)
    scenarios: list[V4ScenarioCandidate] = Field(min_length=3, max_length=5)
    excluded_scenarios: list[V4ExcludedScenarioCandidate] = Field(default_factory=list)


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


def _validate_interactions(interactions: list[EventInteraction], event_ids: list[int]) -> None:
    event_id_set = set(event_ids)
    for interaction in interactions:
        if not set(interaction.event_ids).issubset(event_id_set):
            raise ValueError("interaction references an unknown event")


def _hydrate_dimensions(
    definitions: list[V4DimensionDefinition],
    *,
    event_ids: list[int],
    catalog_by_code: dict[str, ModelImpactLeverPayload],
) -> None:
    dimension_ids = [dimension.dimension_id for dimension in definitions]
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("dimension ids must be unique")

    event_id_set = set(event_ids)
    for dimension in definitions:
        grounding_event_ids = {grounding.event_id for grounding in dimension.event_groundings}
        unknown_event_ids = grounding_event_ids - event_id_set
        if unknown_event_ids:
            raise ValueError(
                f"dimension {dimension.dimension_id} references unknown events: {sorted(unknown_event_ids)}",
            )

        for mapping in dimension.lever_mappings:
            lever = catalog_by_code.get(mapping.lever_code)
            if lever is None:
                raise ValueError(
                    f"dimension {dimension.dimension_id} references unknown lever: {mapping.lever_code}",
                )
            if mapping.impact_lever_id is not None and mapping.impact_lever_id != lever.impact_lever_id:
                raise ValueError(
                    f"dimension {dimension.dimension_id} impact lever id/code mismatch: "
                    f"impact_lever_id={mapping.impact_lever_id}, lever_code={mapping.lever_code}",
                )
            mapping.impact_lever_id = lever.impact_lever_id

        dimension.model_support_status = _lever_support_status(
            [mapping.lever_code for mapping in dimension.lever_mappings],
            catalog_by_code,
        )


def _validate_scenarios(result: V4GenerationResult) -> None:
    dimension_by_id = {dimension.dimension_id: dimension for dimension in result.dimension_definitions}
    combinations: set[tuple[tuple[str, str], ...]] = set()
    generated_bands: list[PressureBand] = []
    contribution_by_scenario: dict[int, list[int]] = {}

    def contribution_score(raw: str) -> int:
        normalized = raw.casefold()
        has_bullish = any(marker in normalized for marker in ("bullish", "상방", "상승"))
        has_bearish = any(marker in normalized for marker in ("bearish", "하방", "하락"))
        if has_bullish and has_bearish:
            raise ValueError(f"ambiguous v4 globalPressureContribution: {raw}")
        if has_bullish:
            return 1
        if has_bearish:
            return -1
        if any(marker in normalized for marker in ("balanced", "중립", "균형", "보합")):
            return 0
        raise ValueError(f"unrecognized v4 globalPressureContribution: {raw}")

    for scenario in result.scenarios:
        if set(scenario.dimension_values) != set(dimension_by_id):
            raise ValueError("every scenario must provide every dimension value")
        scenario_contributions: list[int] = []
        for dimension_id, selected_value in scenario.dimension_values.items():
            dimension = dimension_by_id[dimension_id]
            allowed_values = {candidate for value in dimension.values for candidate in (value.value_id, value.label)}
            if selected_value not in allowed_values:
                raise ValueError(f"invalid value {selected_value!r} for dimension {dimension_id}")
            selected_definition = next(
                value for value in dimension.values if selected_value in {value.value_id, value.label}
            )
            scenario_contributions.append(contribution_score(selected_definition.global_pressure_contribution))
        combination = tuple(sorted(scenario.dimension_values.items()))
        if combination in combinations:
            raise ValueError("scenario dimension combinations must be unique")
        combinations.add(combination)
        generated_bands.append(scenario.global_pressure_band)
        contribution_by_scenario[id(scenario)] = scenario_contributions
        if scenario.mixed_factors and not ({-1, 1} <= set(scenario_contributions)):
            raise ValueError(f"mixedFactors requires bullish and bearish dimension contributions: {scenario.title}")

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
    pressure_scores = [sum(contribution_by_scenario[id(scenario)]) for scenario in ordered]
    if ordered[0].global_pressure_band == "strong_bearish" and pressure_scores[0] >= 0:
        raise ValueError("strong_bearish Scenario requires a negative aggregate pressure score")
    if ordered[-1].global_pressure_band == "strong_bullish" and pressure_scores[-1] <= 0:
        raise ValueError("strong_bullish Scenario requires a positive aggregate pressure score")
    if any(lower > higher for lower, higher in zip(pressure_scores, pressure_scores[1:], strict=False)):
        raise ValueError("v4 Scenario pressure bands contradict aggregate dimension contributions")

    for scenario in result.scenarios:
        scenario.scenario_role = None
        scenario.baseline_yn = False
    ordered[0].scenario_role = "floor"
    ordered[-1].scenario_role = "ceiling"

    mixed_candidates = [
        scenario for scenario in ordered[1:-1] if {-1, 1} <= set(contribution_by_scenario[id(scenario)])
    ]
    if mixed_candidates:
        mixed = min(
            mixed_candidates,
            key=lambda scenario: (
                abs(PRESSURE_RANK[scenario.global_pressure_band] - 2),
                -scenario.probability_score,
            ),
        )
        mixed.scenario_role = "mixed"

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
        mapping.lever_code for dimension in result.dimension_definitions for mapping in dimension.lever_mappings
    }
    unsupported_details = [
        issue
        for lever_code in sorted(referenced_lever_codes)
        for issue in _lever_support_issues(catalog_by_code[lever_code])
    ]
    unsupported_lever_codes = sorted({detail.lever_code for detail in unsupported_details})

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


def finalize_v4_dimension_design(
    design: V4DimensionDesignResult,
    *,
    event_ids: list[int],
    impact_levers: list[ModelImpactLeverPayload],
) -> V4DimensionDesignResult:
    """Hydrate and validate compact v4 dimensions before Scenario generation."""
    catalog_by_code = {lever.lever_code: lever for lever in impact_levers}
    if not catalog_by_code:
        raise ValueError("active model impact lever catalog is empty")

    _validate_interactions(design.interactions, event_ids)
    _hydrate_dimensions(
        design.dimension_definitions,
        event_ids=event_ids,
        catalog_by_code=catalog_by_code,
    )
    return design


def finalize_v4_generation_result(
    result: V4GenerationResult,
    *,
    event_ids: list[int],
    impact_levers: list[ModelImpactLeverPayload],
) -> tuple[V4GenerationResult, ParameterCoverage]:
    catalog_by_code = {lever.lever_code: lever for lever in impact_levers}
    if not catalog_by_code:
        raise ValueError("active model impact lever catalog is empty")

    _validate_interactions(result.interactions, event_ids)
    _hydrate_dimensions(
        result.dimension_definitions,
        event_ids=event_ids,
        catalog_by_code=catalog_by_code,
    )
    _validate_scenarios(result)
    return result, build_parameter_coverage(result, catalog_by_code)


__all__ = [
    "EventInteraction",
    "ParameterCoverage",
    "V4DimensionDefinition",
    "V4DimensionDesignResult",
    "V4DimensionValueDefinition",
    "V4EventGrounding",
    "V4ExcludedScenarioCandidate",
    "V4GenerationResult",
    "V4LeverMapping",
    "V4ScenarioCandidate",
    "V4ScenarioSynthesisResult",
    "build_parameter_coverage",
    "finalize_v4_dimension_design",
    "finalize_v4_generation_result",
]
