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
from apps.persistence.scenario.schema import (
    DimensionDefinition,
    ImpactLeverReference,
    RelatedMarket,
)


class EventImpactFact(ApiModel):
    fact_id: str = Field(min_length=1)
    event_id: int = Field(gt=0)
    domain: Literal["demand", "supply", "trade", "price_only"]
    change_direction: Literal["increase", "decrease", "neutral"]
    global_pressure_direction: Literal["bullish", "bearish", "neutral"]
    affected_scope: list[str] = Field(default_factory=list)
    timing: str = Field(min_length=1)
    magnitude_evidence: str = Field(min_length=1)
    fact_basis: str = Field(min_length=1)
    confidence: float = Field(ge=0, le=1)
    common_impact_lever_refs: list[ImpactLeverReference] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def normalize_fact_id(self) -> EventImpactFact:
        self.fact_id = self.fact_id.strip()
        if not self.fact_id:
            raise ValueError("factId must not be blank")
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


class EventDimensionCoverage(ApiModel):
    event_id: int = Field(gt=0)
    dimension_ids: list[str] = Field(default_factory=list)
    no_dimension_reason: Literal[
        "NO_EXECUTABLE_UNCERTAINTY",
        "PRICE_ONLY_OR_UNSUPPORTED",
        "COMMON_FACT_NO_SCENARIO_DELTA",
    ] | None = None
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_coverage(self) -> EventDimensionCoverage:
        self.dimension_ids = [dimension_id.strip() for dimension_id in self.dimension_ids]
        if any(not dimension_id for dimension_id in self.dimension_ids):
            raise ValueError("event dimension coverage must not contain blank dimensionIds")
        if len(self.dimension_ids) != len(set(self.dimension_ids)):
            raise ValueError("event dimension coverage dimensionIds must be unique")
        self.rationale = self.rationale.strip()
        if not self.rationale:
            raise ValueError("event dimension coverage rationale must not be blank")
        return self


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
    event_dimension_coverage: list[EventDimensionCoverage] = Field(
        min_length=2,
        max_length=5,
    )
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


class V4EventAnalysisResult(ApiModel):
    """Per-Event fact extraction response before lever selection."""

    model_config = ConfigDict(extra="forbid")

    event_impact_facts: list[EventImpactFact] = Field(min_length=1)


class V4CommonFactLeverMapping(ApiModel):
    """Lever mapping for a fact that is intentionally not used by a dimension."""

    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1)
    common_impact_lever_refs: list[ImpactLeverReference] = Field(min_length=1)


class V4DimensionDesignResult(ApiModel):
    """v4 dimension-only response based on validated Event facts."""

    model_config = ConfigDict(extra="forbid")

    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_definitions: list[DimensionDefinition] = Field(min_length=3, max_length=6)
    event_dimension_coverage: list[EventDimensionCoverage] = Field(min_length=2, max_length=5)
    common_fact_lever_mappings: list[V4CommonFactLeverMapping] = Field(default_factory=list)
    excluded_dimensions: list[str] = Field(default_factory=list)


class V4ScenarioSynthesisResult(ApiModel):
    """v4 Scenario-only response based on validated fact/lever dimensions."""

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


def _hydrate_impact_lever_reference(
    reference: ImpactLeverReference,
    *,
    catalog_by_code: dict[str, ModelImpactLeverPayload],
    source_facts_by_id: dict[str, EventImpactFact],
    allowed_source_fact_ids: set[str],
    owner_description: str,
) -> None:
    lever = catalog_by_code.get(reference.lever_code)
    if lever is None:
        raise ValueError(
            f"{owner_description} references unknown lever: {reference.lever_code}",
        )
    if reference.impact_lever_id is not None and reference.impact_lever_id != lever.impact_lever_id:
        raise ValueError(
            f"{owner_description} impact lever id/code mismatch: "
            f"impact_lever_id={reference.impact_lever_id}, lever_code={reference.lever_code}",
        )
    if not reference.source_fact_ids:
        raise ValueError(f"{owner_description} impact lever must reference source facts")
    referenced_fact_ids = set(reference.source_fact_ids)
    unknown_fact_ids = referenced_fact_ids - set(source_facts_by_id)
    if unknown_fact_ids:
        raise ValueError(
            f"{owner_description} impact lever references unknown facts: {sorted(unknown_fact_ids)}",
        )
    if not referenced_fact_ids.issubset(allowed_source_fact_ids):
        raise ValueError(
            f"{owner_description} impact lever references facts outside its owner: "
            f"{sorted(referenced_fact_ids - allowed_source_fact_ids)}",
        )
    mismatched_domains = sorted(
        fact_id
        for fact_id in referenced_fact_ids
        if source_facts_by_id[fact_id].domain != lever.domain
    )
    if mismatched_domains:
        raise ValueError(
            f"{owner_description} lever {reference.lever_code} domain must match source facts: "
            f"{mismatched_domains}",
        )
    reference.impact_lever_id = lever.impact_lever_id


def _validate_dimensions(
    result: V4GenerationResult,
    event_ids: list[int],
    catalog_by_code: dict[str, ModelImpactLeverPayload],
    source_facts_by_id: dict[str, EventImpactFact],
) -> set[str]:
    dimension_ids = [dimension.dimension_id for dimension in result.dimension_definitions]
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("dimension ids must be unique")

    dimension_source_fact_ids: set[str] = set()
    event_id_set = set(event_ids)
    for display_order, dimension in enumerate(result.dimension_definitions, start=1):
        if not dimension.source_fact_ids:
            raise ValueError(f"dimension {dimension.dimension_id} must reference source facts")
        if len(dimension.source_fact_ids) != len(set(dimension.source_fact_ids)):
            raise ValueError(f"dimension {dimension.dimension_id} source fact ids must be unique")
        unknown_fact_ids = set(dimension.source_fact_ids) - set(source_facts_by_id)
        if unknown_fact_ids:
            raise ValueError(
                f"dimension {dimension.dimension_id} references unknown facts: {sorted(unknown_fact_ids)}",
            )
        if not dimension.impact_lever_refs:
            raise ValueError(f"dimension {dimension.dimension_id} must reference impact levers")
        lever_codes = [reference.lever_code for reference in dimension.impact_lever_refs]
        if len(lever_codes) != len(set(lever_codes)):
            raise ValueError(f"dimension {dimension.dimension_id} impact levers must be unique")
        mapped_source_fact_ids: set[str] = set()
        for reference in dimension.impact_lever_refs:
            _hydrate_impact_lever_reference(
                reference,
                catalog_by_code=catalog_by_code,
                source_facts_by_id=source_facts_by_id,
                allowed_source_fact_ids=set(dimension.source_fact_ids),
                owner_description=f"dimension {dimension.dimension_id}",
            )
            mapped_source_fact_ids.update(reference.source_fact_ids)
        if mapped_source_fact_ids != set(dimension.source_fact_ids):
            raise ValueError(
                f"dimension {dimension.dimension_id} impact lever refs must cover "
                "source facts exactly: "
                f"missing={sorted(set(dimension.source_fact_ids) - mapped_source_fact_ids)}",
            )
        if len(dimension.values) < 2 or len(dimension.values) > 4:
            raise ValueError(f"dimension {dimension.dimension_id} must have 2-4 values")
        if len({value.value_id for value in dimension.values}) != len(dimension.values):
            raise ValueError(f"dimension {dimension.dimension_id} value ids must be unique")

        dimension.model_support_status = _lever_support_status(
            lever_codes,
            catalog_by_code,
        )
        dimension.required = True
        dimension.display_order = display_order
        dimension.source_event_ids = list(
            dict.fromkeys(
                source_facts_by_id[fact_id].event_id
                for fact_id in dimension.source_fact_ids
            ),
        )
        if not set(dimension.source_event_ids).issubset(event_id_set):
            raise ValueError(f"dimension {dimension.dimension_id} references an unknown event")
        dimension.lever_refs = lever_codes
        dimension_source_fact_ids.update(dimension.source_fact_ids)

    if not any(
        dimension.model_support_status in {"full", "partial"}
        for dimension in result.dimension_definitions
    ):
        raise ValueError(
            "at least one dimension must reference an executable model parameter binding",
        )
    return dimension_source_fact_ids


def _validate_event_grounding(
    result: V4GenerationResult,
    event_ids: list[int],
) -> dict[str, EventImpactFact]:
    fact_event_ids = {fact.event_id for fact in result.event_impact_facts}
    if fact_event_ids != set(event_ids):
        raise ValueError("event impact facts must cover every selected event")

    fact_ids = [fact.fact_id for fact in result.event_impact_facts]
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("event impact fact ids must be unique")
    source_facts_by_id = {fact.fact_id: fact for fact in result.event_impact_facts}

    event_id_set = set(event_ids)
    for interaction in result.interactions:
        if not set(interaction.event_ids).issubset(event_id_set):
            raise ValueError("interaction references an unknown event")
    return source_facts_by_id


def _validate_common_impact_lever_refs(
    result: V4GenerationResult,
    *,
    catalog_by_code: dict[str, ModelImpactLeverPayload],
    source_facts_by_id: dict[str, EventImpactFact],
    dimension_source_fact_ids: set[str],
) -> None:
    for fact in result.event_impact_facts:
        if (
            fact.fact_id not in dimension_source_fact_ids
            and not fact.common_impact_lever_refs
        ):
            raise ValueError(
                f"dimension-free fact {fact.fact_id} must define common impact levers",
            )
        if fact.common_impact_lever_refs and fact.fact_id in dimension_source_fact_ids:
            raise ValueError(
                f"fact {fact.fact_id} cannot define common impact levers because it is referenced by a dimension",
            )
        lever_codes = [reference.lever_code for reference in fact.common_impact_lever_refs]
        if len(lever_codes) != len(set(lever_codes)):
            raise ValueError(f"fact {fact.fact_id} common impact levers must be unique")
        for reference in fact.common_impact_lever_refs:
            if fact.fact_id not in reference.source_fact_ids:
                raise ValueError(
                    f"fact {fact.fact_id} common impact lever must include its owner fact id",
                )
            if set(reference.source_fact_ids) & dimension_source_fact_ids:
                raise ValueError(
                    f"fact {fact.fact_id} common impact lever may only reference dimension-free facts",
                )
            _hydrate_impact_lever_reference(
                reference,
                catalog_by_code=catalog_by_code,
                source_facts_by_id=source_facts_by_id,
                allowed_source_fact_ids=set(source_facts_by_id) - dimension_source_fact_ids,
                owner_description=f"fact {fact.fact_id}",
            )


def _validate_event_dimension_coverage(
    result: V4GenerationResult,
    *,
    event_ids: list[int],
    source_facts_by_id: dict[str, EventImpactFact],
) -> None:
    coverage_event_ids = [coverage.event_id for coverage in result.event_dimension_coverage]
    if len(coverage_event_ids) != len(set(coverage_event_ids)):
        raise ValueError("event dimension coverage event ids must be unique")
    if set(coverage_event_ids) != set(event_ids):
        raise ValueError("event dimension coverage must cover every selected event")

    computed_by_event: dict[int, list[str]] = {event_id: [] for event_id in event_ids}
    for dimension in result.dimension_definitions:
        dimension_event_ids = {
            source_facts_by_id[fact_id].event_id
            for fact_id in dimension.source_fact_ids
        }
        for event_id in event_ids:
            if event_id in dimension_event_ids:
                computed_by_event[event_id].append(dimension.dimension_id)

    for coverage in result.event_dimension_coverage:
        coverage.dimension_ids = computed_by_event[coverage.event_id]
        if coverage.dimension_ids and coverage.no_dimension_reason is not None:
            raise ValueError(
                f"event {coverage.event_id} with dimensions must not define noDimensionReason",
            )
        if not coverage.dimension_ids and coverage.no_dimension_reason is None:
            raise ValueError(
                f"event {coverage.event_id} without dimensions requires noDimensionReason",
            )


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


def finalize_v4_dimension_design(
    design: V4DimensionDesignResult,
    *,
    event_impact_facts: list[EventImpactFact],
    event_ids: list[int],
    impact_levers: list[ModelImpactLeverPayload],
) -> tuple[V4DimensionDesignResult, list[EventImpactFact]]:
    """Hydrate and validate the v4 fact/lever dimension stage before Scenario generation."""
    catalog_by_code = {lever.lever_code: lever for lever in impact_levers}
    if not catalog_by_code:
        raise ValueError("active model impact lever catalog is empty")

    facts = [fact.model_copy(deep=True, update={"common_impact_lever_refs": []}) for fact in event_impact_facts]
    fact_ids = {fact.fact_id for fact in facts}
    dimension_fact_ids = {
        fact_id for dimension in design.dimension_definitions for fact_id in dimension.source_fact_ids
    }
    mappings_by_fact: dict[str, V4CommonFactLeverMapping] = {}
    for mapping in design.common_fact_lever_mappings:
        if mapping.fact_id not in fact_ids:
            raise ValueError(f"common fact lever mapping references an unknown fact: {mapping.fact_id}")
        if mapping.fact_id in mappings_by_fact:
            raise ValueError(f"common fact lever mapping is duplicated: {mapping.fact_id}")
        if mapping.fact_id in dimension_fact_ids:
            raise ValueError(f"dimension fact cannot have a common lever mapping: {mapping.fact_id}")
        mappings_by_fact[mapping.fact_id] = mapping

    unused_fact_ids = fact_ids - dimension_fact_ids
    if set(mappings_by_fact) != unused_fact_ids:
        raise ValueError(
            "commonFactLeverMappings must cover every dimension-free fact exactly: "
            f"missing={sorted(unused_fact_ids - set(mappings_by_fact))}, "
            f"unknown={sorted(set(mappings_by_fact) - unused_fact_ids)}"
        )
    for fact in facts:
        mapping = mappings_by_fact.get(fact.fact_id)
        if mapping is not None:
            fact.common_impact_lever_refs = mapping.common_impact_lever_refs

    partial = V4GenerationResult.model_construct(
        group_title="pending",
        group_description="pending",
        event_impact_facts=facts,
        interactions=design.interactions,
        dimension_definitions=design.dimension_definitions,
        scenarios=[],
        event_dimension_coverage=design.event_dimension_coverage,
        excluded_scenarios=[],
        excluded_dimensions=design.excluded_dimensions,
    )
    source_facts_by_id = _validate_event_grounding(partial, event_ids)
    dimension_source_fact_ids = _validate_dimensions(
        partial,
        event_ids,
        catalog_by_code,
        source_facts_by_id,
    )
    _validate_common_impact_lever_refs(
        partial,
        catalog_by_code=catalog_by_code,
        source_facts_by_id=source_facts_by_id,
        dimension_source_fact_ids=dimension_source_fact_ids,
    )
    _validate_event_dimension_coverage(
        partial,
        event_ids=event_ids,
        source_facts_by_id=source_facts_by_id,
    )
    return (
        design.model_copy(
            update={
                "dimension_definitions": partial.dimension_definitions,
                "event_dimension_coverage": partial.event_dimension_coverage,
            }
        ),
        partial.event_impact_facts,
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

    source_facts_by_id = _validate_event_grounding(result, event_ids)
    dimension_source_fact_ids = _validate_dimensions(
        result,
        event_ids,
        catalog_by_code,
        source_facts_by_id,
    )
    _validate_common_impact_lever_refs(
        result,
        catalog_by_code=catalog_by_code,
        source_facts_by_id=source_facts_by_id,
        dimension_source_fact_ids=dimension_source_fact_ids,
    )
    _validate_event_dimension_coverage(
        result,
        event_ids=event_ids,
        source_facts_by_id=source_facts_by_id,
    )
    _validate_scenarios(result)
    return result, build_parameter_coverage(result, catalog_by_code)


__all__ = [
    "EventImpactFact",
    "EventDimensionCoverage",
    "EventInteraction",
    "ParameterCoverage",
    "V4ExcludedScenarioCandidate",
    "V4CommonFactLeverMapping",
    "V4DimensionDesignResult",
    "V4EventAnalysisResult",
    "V4GenerationResult",
    "V4ScenarioSynthesisResult",
    "V4ScenarioCandidate",
    "build_parameter_coverage",
    "finalize_v4_generation_result",
    "finalize_v4_dimension_design",
]
