from __future__ import annotations

from copy import deepcopy
import re
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, ConfigDict, Field, WithJsonSchema, model_validator

from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.persistence.scenario.schema import DimensionDefinition, SourceLineage


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

SelectionCriterion = Literal[
    "direct_event_fact",
    "lng_impact_path",
    "both",
    "none",
]
V2SelectionCriterion = Literal[
    "direct_event_fact",
    "lng_impact_path",
    "both",
]


def _wire_entries_to_dict(
    value: Any,
    *,
    key_field: str,
    value_field: str,
) -> Any:
    if not isinstance(value, list):
        return value

    result: dict[str, Any] = {}
    for item in value:
        if not isinstance(item, dict):
            return value
        raw_key = item.get(key_field)
        if raw_key is None:
            return value
        key = str(raw_key).strip()
        if not key or key in result:
            raise ValueError(f"{key_field} entries must have unique non-blank keys")
        result[key] = item.get(value_field)
    return result


def _generated_event_values_from_wire(value: Any) -> Any:
    return _wire_entries_to_dict(
        value,
        key_field="dimKey",
        value_field="value",
    )


def _template_value_examples_from_wire(value: Any) -> Any:
    return _wire_entries_to_dict(
        value,
        key_field="dimKey",
        value_field="valueExamples",
    )


def _scenario_dimension_values_from_wire(value: Any) -> Any:
    return _wire_entries_to_dict(
        value,
        key_field="dimensionId",
        value_field="valueId",
    )


GeneratedEventValues = Annotated[
    dict[str, str],
    BeforeValidator(_generated_event_values_from_wire),
    WithJsonSchema(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimKey": {"type": "string"},
                    "value": {"type": "string"},
                },
                "required": ["dimKey", "value"],
                "additionalProperties": False,
            },
        },
        mode="validation",
    ),
]
TemplateValueExamplesConsulted = Annotated[
    dict[str, list[str]],
    BeforeValidator(_template_value_examples_from_wire),
    WithJsonSchema(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimKey": {"type": "string"},
                    "valueExamples": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["dimKey", "valueExamples"],
                "additionalProperties": False,
            },
        },
        mode="validation",
    ),
]
ScenarioDimensionValues = Annotated[
    dict[str, str],
    BeforeValidator(_scenario_dimension_values_from_wire),
    WithJsonSchema(
        {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "dimensionId": {"type": "string"},
                    "valueId": {"type": "string"},
                },
                "required": ["dimensionId", "valueId"],
                "additionalProperties": False,
            },
        },
        mode="validation",
    ),
]


def _normalize_event_shock_examples(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = deepcopy(value)
    raw_event_id = normalized.get("eventId", normalized.get("event_id"))
    namespace_prefix = f"e{raw_event_id}__" if raw_event_id is not None else ""
    raw_sources = normalized.get(
        "sourceDimensions",
        normalized.get("source_dimensions", []),
    )
    if not isinstance(raw_sources, list):
        return normalized

    source_key_by_normalized_key: dict[str, str] = {}
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            continue
        raw_dim_key = raw_source.get("dimKey", raw_source.get("dim_key"))
        if raw_dim_key is None:
            continue
        dim_key = str(raw_dim_key).strip()
        if not dim_key:
            continue
        normalized_key = (
            dim_key.removeprefix(namespace_prefix)
            if namespace_prefix and dim_key.startswith(namespace_prefix)
            else dim_key
        )
        source_key_by_normalized_key[normalized_key] = dim_key

    examples_field = (
        "templateValueExamplesConsulted"
        if "templateValueExamplesConsulted" in normalized
        else "template_value_examples_consulted"
    )
    raw_examples = _template_value_examples_from_wire(
        normalized.get(examples_field, {}),
    )
    if not isinstance(raw_examples, dict):
        return normalized

    filtered_examples: dict[str, Any] = {}
    for raw_key, examples in raw_examples.items():
        example_key = str(raw_key).strip()
        normalized_key = (
            example_key.removeprefix(namespace_prefix)
            if namespace_prefix and example_key.startswith(namespace_prefix)
            else example_key
        )
        source_key = source_key_by_normalized_key.get(normalized_key)
        if source_key is not None:
            filtered_examples[source_key] = examples
    normalized[examples_field] = filtered_examples
    return normalized


class EventShockImpactPath(ApiModel):
    domain: Literal["supply", "demand", "trade"]
    direction: Literal["increase", "decrease", "neutral", "not_applicable"]
    rationale: str = Field(min_length=1)
    affected_scope: list[str]


class EventShockSourceDimension(ApiModel):
    event_id: int = Field(gt=0)
    scenario_dimension_template_id: int = Field(gt=0)
    template_checksum: str = Field(min_length=1)
    dim_key: str = Field(min_length=1)


class ExcludedDimensionDecision(ApiModel):
    event_id: int = Field(gt=0)
    event_type_l2_id: int = Field(gt=0)
    scenario_dimension_template_id: int = Field(gt=0)
    template_checksum: str = Field(min_length=1)
    dim_key: str = Field(min_length=1)
    selection_criterion: SelectionCriterion
    required: bool = False
    reason_code: Literal[
        "NOT_RELEVANT",
        "LOWER_PRIORITY",
        "DIMENSION_LIMIT",
    ]
    reason: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_relevance_reason(self) -> ExcludedDimensionDecision:
        if self.selection_criterion == "none" and self.reason_code != "NOT_RELEVANT":
            raise ValueError(
                "selectionCriterion=none requires reasonCode=NOT_RELEVANT",
            )
        if self.selection_criterion != "none" and self.reason_code == "NOT_RELEVANT":
            raise ValueError(
                "relevant excluded dimensions cannot use reasonCode=NOT_RELEVANT",
            )
        return self


class EventShock(ApiModel):
    event_id: int
    supply_direction: Literal["increase", "decrease", "neutral", "not_applicable"]
    demand_direction: Literal["increase", "decrease", "neutral", "not_applicable"]
    trade_direction: Literal["increase", "decrease", "neutral", "not_applicable"]
    affected_regions: list[str]
    affected_countries: list[str]
    affected_facilities: list[str]
    duration: str
    intensity: str
    recovery_or_persistence: str
    mitigation: str
    source_dimension_keys: list[str]
    generated_event_values: GeneratedEventValues
    impact_paths: list[EventShockImpactPath]
    source_dimensions: list[EventShockSourceDimension]
    template_value_examples_consulted: TemplateValueExamplesConsulted

    @model_validator(mode="after")
    def _validate_structured_shock(self) -> EventShock:
        expected_directions = {
            "supply": self.supply_direction,
            "demand": self.demand_direction,
            "trade": self.trade_direction,
        }
        actual_paths = [path.domain for path in self.impact_paths]
        if len(actual_paths) != 3 or set(actual_paths) != set(expected_directions):
            raise ValueError(
                "impactPaths must contain supply, demand and trade exactly once",
            )
        for path in self.impact_paths:
            if path.direction != expected_directions[path.domain]:
                raise ValueError(
                    f"impactPath direction does not match {path.domain}Direction",
                )

        structured_keys = [source.dim_key for source in self.source_dimensions]
        if len(structured_keys) != len(set(structured_keys)):
            raise ValueError("sourceDimensions must not contain duplicate dimKey values")
        if set(structured_keys) != set(self.source_dimension_keys):
            raise ValueError(
                "sourceDimensions must match sourceDimensionKeys exactly",
            )
        if set(structured_keys) != set(self.generated_event_values):
            raise ValueError(
                "generatedEventValues must match sourceDimensions exactly",
            )
        if any(not str(value).strip() for value in self.generated_event_values.values()):
            raise ValueError("generatedEventValues must not contain blank values")
        if any(source.event_id != self.event_id for source in self.source_dimensions):
            raise ValueError(
                "sourceDimensions eventId must match EventShock eventId",
            )
        example_keys = set(self.template_value_examples_consulted)
        if not example_keys <= set(structured_keys):
            raise ValueError(
                "templateValueExamplesConsulted must reference sourceDimensions",
            )
        return self


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
    dimension_values: ScenarioDimensionValues
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
    excluded_dimensions: list[ExcludedDimensionDecision] = Field(
        default_factory=list,
    )


class V2EventShock(ApiModel):
    """Compact v2 Event grounding without repeated source lineage."""

    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(gt=0)
    shock_summary: str = Field(min_length=1, max_length=300)

    @model_validator(mode="after")
    def _normalize_summary(self) -> V2EventShock:
        self.shock_summary = self.shock_summary.strip()
        if not self.shock_summary:
            raise ValueError("shockSummary must not be blank")
        return self


class V2SourceReference(ApiModel):
    """A source dimension is unique by Event, Template revision owner and key."""

    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(gt=0)
    scenario_dimension_template_id: int = Field(gt=0)
    dim_key: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def _normalize_dim_key(self) -> V2SourceReference:
        self.dim_key = self.dim_key.strip()
        if not self.dim_key:
            raise ValueError("dimKey must not be blank")
        return self


class V2DimensionValueDefinition(ApiModel):
    model_config = ConfigDict(extra="forbid")

    value_id: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=120)
    global_pressure_contribution: Literal["bullish", "balanced", "bearish"]


class V2SelectedDimension(ApiModel):
    """Minimal dimension selection emitted by the LLM."""

    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1, max_length=255)
    source_ref: V2SourceReference
    selection_criterion: V2SelectionCriterion
    selection_rationale: str = Field(min_length=1, max_length=400)
    values: list[V2DimensionValueDefinition] = Field(min_length=3, max_length=4)


class V2ScenarioCandidate(ApiModel):
    """Compact v2 Scenario; roles and mixed state are derived by the server."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    narrative: str = Field(min_length=1, max_length=800)
    dimension_values: ScenarioDimensionValues
    global_pressure_band: PressureBand
    probability_score: int = Field(ge=0, le=100)
    global_pressure_rationale: str = Field(min_length=1, max_length=500)


class V2MultiEventGenerationResult(ApiModel):
    """Compact LLM response-format contract for v2 generation."""

    model_config = ConfigDict(extra="forbid")

    scenario_group_title: str = Field(min_length=1, max_length=120)
    scenario_group_description: str = Field(min_length=1, max_length=600)
    event_shocks: list[V2EventShock]
    selected_dimensions: list[V2SelectedDimension] = Field(min_length=3, max_length=6)
    scenarios: list[V2ScenarioCandidate] = Field(min_length=3, max_length=5)


class V2EventAnalysisResult(ApiModel):
    """Per-Event v2 LLM response used by the LangGraph fan-out stage."""

    model_config = ConfigDict(extra="forbid")

    event_shock: V2EventShock


class V2DimensionDesignResult(ApiModel):
    """v2 dimension-only response; Scenario narratives are generated later."""

    model_config = ConfigDict(extra="forbid")

    selected_dimensions: list[V2SelectedDimension] = Field(min_length=3, max_length=6)


class V2ScenarioSynthesisResult(ApiModel):
    """v2 Scenario-only response based on validated dimensions."""

    model_config = ConfigDict(extra="forbid")

    scenario_group_title: str = Field(min_length=1, max_length=120)
    scenario_group_description: str = Field(min_length=1, max_length=600)
    scenarios: list[V2ScenarioCandidate] = Field(min_length=3, max_length=5)


class V2DimensionDefinition(ApiModel):
    """Compact persisted/API v2 dimension hydrated from its source Template."""

    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1, max_length=255)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    required: bool = False
    selection_criterion: V2SelectionCriterion
    selection_rationale: str = Field(min_length=1, max_length=400)
    source_ref: V2SourceReference
    values: list[V2DimensionValueDefinition] = Field(min_length=3, max_length=4)


class V2FinalizedGenerationResult(ApiModel):
    """Server-finalized v2 payload used for persistence and API presentation."""

    scenario_group_title: str
    scenario_group_description: str
    event_shocks: list[V2EventShock]
    dimension_definitions: list[V2DimensionDefinition]
    scenarios: list[ScenarioCandidate]
    unselected_dimension_refs: list[V2SourceReference]
    unrepresented_pressure_bands: list[PressureBand]


class V3EventShock(ApiModel):
    """Compact v3 Event shock; Event facts stay in natural-language form."""

    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(gt=0)
    shock_summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def _normalize_summary(self) -> V3EventShock:
        self.shock_summary = self.shock_summary.strip()
        if not self.shock_summary:
            raise ValueError("shockSummary must not be blank")
        return self


class V3SourceReference(ApiModel):
    model_config = ConfigDict(extra="forbid")

    scenario_dimension_template_id: int = Field(gt=0)
    dim_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def _normalize_dim_key(self) -> V3SourceReference:
        self.dim_key = self.dim_key.strip()
        if not self.dim_key:
            raise ValueError("dimKey must not be blank")
        return self


class V3DimensionValueDefinition(ApiModel):
    model_config = ConfigDict(extra="forbid")

    value_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    global_pressure_contribution: Literal["bullish", "balanced", "bearish"]


class V3DimensionDefinition(ApiModel):
    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    source_event_ids: list[int] = Field(min_length=1)
    source_refs: list[V3SourceReference] = Field(min_length=1)
    values: list[V3DimensionValueDefinition] = Field(min_length=3, max_length=5)


class V3MultiEventGenerationResult(MultiEventGenerationResult):
    """Compact LLM response-format contract for v3 generation."""

    event_shocks: list[V3EventShock]
    dimension_definitions: list[V3DimensionDefinition] = Field(
        min_length=3,
        max_length=6,
    )

    excluded_dimensions: list[ExcludedDimensionDecision] = Field(
        default_factory=list,
        max_length=0,
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_v3_input(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = deepcopy(value)
        for alias, field_name in (
            ("interactions", "interactions"),
            ("excludedCandidates", "excluded_candidates"),
        ):
            if alias not in normalized and field_name not in normalized:
                normalized[alias] = []
        if not isinstance(normalized, dict):
            return normalized
        if "excludedDimensions" in normalized:
            normalized["excludedDimensions"] = []
        if "excluded_dimensions" in normalized:
            normalized["excluded_dimensions"] = []
        return normalized


class V3AnalysisDesignResult(ApiModel):
    """v3 cross-Event analysis and composite-dimension response."""

    model_config = ConfigDict(extra="forbid")

    event_shocks: list[V3EventShock] = Field(min_length=2, max_length=5)
    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_definitions: list[V3DimensionDefinition] = Field(min_length=3, max_length=6)


class V3DimensionDesignResult(ApiModel):
    """v3 interaction and composite-dimension design response."""

    model_config = ConfigDict(extra="forbid")

    interactions: list[EventInteraction] = Field(default_factory=list)
    dimension_definitions: list[V3DimensionDefinition] = Field(min_length=3, max_length=6)


class V3ScenarioSynthesisResult(ApiModel):
    """v3 Scenario-only response based on validated composite dimensions."""

    model_config = ConfigDict(extra="forbid")

    scenario_group_title: str = Field(min_length=1, max_length=120)
    scenario_group_description: str = Field(min_length=1, max_length=600)
    scenarios: list[ScenarioCandidate] = Field(min_length=3, max_length=5)
    excluded_candidates: list[ExcludedGenerationCandidate] = Field(default_factory=list, max_length=2)


def _with_multi_event_defaults(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized = deepcopy(value)
    aliases = (
        ("interactions", "interactions"),
        ("excludedCandidates", "excluded_candidates"),
        ("excludedDimensions", "excluded_dimensions"),
    )
    for alias, field_name in aliases:
        if alias not in normalized and field_name not in normalized:
            normalized[alias] = []
    shocks_field = "eventShocks" if "eventShocks" in normalized else "event_shocks"
    raw_shocks = normalized.get(shocks_field)
    if isinstance(raw_shocks, list):
        normalized[shocks_field] = [_normalize_event_shock_examples(shock) for shock in raw_shocks]
    return normalized


def multi_event_generation_schema(
    api_version: str,
) -> type[V2MultiEventGenerationResult] | type[V3MultiEventGenerationResult]:
    if api_version == "v2":
        return V2MultiEventGenerationResult
    if api_version == "v3":
        return V3MultiEventGenerationResult
    raise ValueError(f"Unsupported multi-event API version: {api_version}")


def _normalize_event_shock_source_keys(shock: EventShock) -> None:
    namespace_prefix = f"e{shock.event_id}__"
    original_values = shock.generated_event_values
    normalized_keys: list[str] = []
    normalized_values: dict[str, str] = {}
    normalized_examples: dict[str, list[str]] = {}

    for source_key in shock.source_dimension_keys:
        normalized_key = (
            source_key.removeprefix(namespace_prefix) if source_key.startswith(namespace_prefix) else source_key
        )
        normalized_keys.append(normalized_key)
        value = str(
            original_values.get(source_key) or original_values.get(normalized_key) or "",
        ).strip()
        if value:
            normalized_values[normalized_key] = value
        examples = shock.template_value_examples_consulted.get(
            source_key,
            shock.template_value_examples_consulted.get(normalized_key, []),
        )
        normalized_examples[normalized_key] = list(
            dict.fromkeys(str(example).strip() for example in examples if str(example).strip()),
        )

    shock.source_dimension_keys = normalized_keys
    shock.generated_event_values = normalized_values
    shock.template_value_examples_consulted = normalized_examples
    for source_dimension in shock.source_dimensions:
        if source_dimension.dim_key.startswith(namespace_prefix):
            source_dimension.dim_key = source_dimension.dim_key.removeprefix(
                namespace_prefix,
            )


def _ground_event_shock_source_keys(
    shock: EventShock,
    *,
    dimensions: list[DimensionDefinition],
    source_dimensions_by_event: dict[
        int,
        dict[str, bool | dict[str, object]],
    ],
) -> None:
    source_definitions = source_dimensions_by_event.get(
        shock.event_id,
        {},
    )
    valid_keys = [source_key for source_key in shock.source_dimension_keys if source_key in source_definitions]
    dimension_grounded_keys = [
        source.dim_key
        for dimension in dimensions
        for source in dimension.source_refs
        if source.event_id == shock.event_id and source.dim_key in source_definitions
    ]
    grounded_keys = list(
        dict.fromkeys([*valid_keys, *dimension_grounded_keys]),
    )
    if not grounded_keys:
        required_keys = [
            dim_key
            for dim_key, definition in source_definitions.items()
            if (bool(definition.get("required", False)) if isinstance(definition, dict) else bool(definition))
        ]
        fallback_keys = required_keys or list(source_definitions)
        grounded_keys = fallback_keys[:1]

    original_values = shock.generated_event_values
    shock.source_dimension_keys = grounded_keys
    shock.generated_event_values = {
        dim_key: value
        for dim_key in grounded_keys
        if (
            value := str(
                original_values.get(dim_key) or "",
            ).strip()
        )
    }
    shock.template_value_examples_consulted = {
        dim_key: examples
        for dim_key, examples in shock.template_value_examples_consulted.items()
        if dim_key in grounded_keys
    }


def _normalize_event_shock_values(shock: EventShock) -> None:
    fallback_by_key_fragment = {
        "duration": shock.duration,
        "period": shock.duration,
        "timing": shock.duration,
        "intensity": shock.intensity,
        "magnitude": shock.intensity,
        "recovery": shock.recovery_or_persistence,
        "persistence": shock.recovery_or_persistence,
        "mitigation": shock.mitigation,
    }
    normalized: dict[str, str] = {}
    for source_key in shock.source_dimension_keys:
        existing = str(shock.generated_event_values.get(source_key) or "").strip()
        if existing:
            normalized[source_key] = existing
            continue
        normalized[source_key] = next(
            (
                value
                for fragment, value in fallback_by_key_fragment.items()
                if fragment in source_key.lower() and value.strip()
            ),
            (
                f"Event {shock.event_id} 사실 기반 값: "
                f"{shock.intensity}, {shock.duration}, "
                f"{shock.recovery_or_persistence}"
            ),
        )
    shock.generated_event_values = normalized


def _normalize_event_shock_source_dimensions(
    shock: EventShock,
    *,
    source_dimensions_by_event: dict[
        int,
        dict[str, bool | dict[str, object]],
    ],
) -> None:
    source_definitions = source_dimensions_by_event.get(shock.event_id, {})
    structured_by_key = {source.dim_key: source for source in shock.source_dimensions}
    normalized: list[EventShockSourceDimension] = []
    for dim_key in shock.source_dimension_keys:
        source_definition = source_definitions.get(dim_key)
        if not isinstance(source_definition, dict):
            raise ValueError(
                f"EventShock source dimension metadata is unavailable: eventId={shock.event_id}, dimKey={dim_key}",
            )
        template_id = source_definition.get("scenario_dimension_template_id")
        template_checksum = str(
            source_definition.get("template_checksum") or "",
        ).strip()
        if template_id is None or not template_checksum:
            raise ValueError(
                f"EventShock source dimension requires a template revision: eventId={shock.event_id}, dimKey={dim_key}",
            )
        current = structured_by_key.get(dim_key)
        if current is None:
            normalized.append(
                EventShockSourceDimension(
                    event_id=shock.event_id,
                    scenario_dimension_template_id=int(template_id),
                    template_checksum=template_checksum,
                    dim_key=dim_key,
                ),
            )
            continue
        if current.event_id != shock.event_id:
            raise ValueError(
                f"EventShock source dimension eventId does not match: eventId={shock.event_id}, dimKey={dim_key}",
            )
        if current.scenario_dimension_template_id != int(template_id) or current.template_checksum != template_checksum:
            raise ValueError(
                "EventShock source dimension template revision does not match: "
                f"eventId={shock.event_id}, dimKey={dim_key}",
            )
        normalized.append(current)
    shock.source_dimensions = normalized


def _validate_event_shock_template_examples(
    shock: EventShock,
    *,
    source_dimensions_by_event: dict[
        int,
        dict[str, bool | dict[str, object]],
    ],
) -> None:
    expected_keys = set(shock.source_dimension_keys)
    actual_keys = set(shock.template_value_examples_consulted)
    if not actual_keys <= expected_keys:
        raise ValueError(
            "EventShock templateValueExamplesConsulted must reference at least "
            f"one sourceDimension: eventId={shock.event_id}, "
            f"unknown={sorted(actual_keys - expected_keys)}",
        )
    for dim_key, examples in shock.template_value_examples_consulted.items():
        definition = source_dimensions_by_event.get(shock.event_id, {}).get(dim_key)
        allowed_examples = (
            {str(value).strip() for value in definition.get("value_enums", []) if str(value).strip()}
            if isinstance(definition, dict)
            else set()
        )
        if not examples:
            continue
        unknown_examples = set(examples) - allowed_examples
        if unknown_examples:
            raise ValueError(
                "EventShock templateValueExamplesConsulted contains values "
                f"outside the source Template: eventId={shock.event_id}, "
                f"dimKey={dim_key}, values={sorted(unknown_examples)}",
            )


def _normalize_dimension_source_key_aliases(
    result: MultiEventGenerationResult,
    *,
    source_dimensions_by_event: dict[
        int,
        dict[str, bool | dict[str, object]],
    ],
) -> None:
    def normalize_lineage(lineage: SourceLineage) -> None:
        source_definitions = source_dimensions_by_event.get(
            lineage.event_id,
            {},
        )
        if lineage.dim_key in source_definitions:
            normalized_key = lineage.dim_key
        else:
            without_namespace = lineage.dim_key.removeprefix(
                f"e{lineage.event_id}__",
            )
            without_display_prefix = re.sub(
                r"^d\d+[_-]+",
                "",
                without_namespace,
                count=1,
            )
            normalized_key = without_display_prefix if without_display_prefix in source_definitions else lineage.dim_key

        source_definition = source_definitions.get(normalized_key)
        if source_definition is None:
            return
        lineage.dim_key = normalized_key
        if isinstance(source_definition, dict) and source_definition.get("event_type_l2_id") is not None:
            lineage.event_type_l2_id = int(
                source_definition["event_type_l2_id"],
            )

    for dimension in result.dimension_definitions:
        for source in dimension.source_refs:
            normalize_lineage(source)
        for value in dimension.values:
            for assignment in value.source_assignments:
                normalize_lineage(assignment)


def _normalize_v2_dimension_source_refs(
    result: MultiEventGenerationResult,
    *,
    event_ids: list[int],
    source_dimensions_by_event: dict[
        int,
        dict[str, bool | dict[str, object]],
    ],
) -> None:
    dimensions = result.dimension_definitions
    for dimension in dimensions:
        if len(dimension.source_refs) <= 1:
            continue
        valid_sources = [
            source
            for source in dimension.source_refs
            if source.dim_key in source_dimensions_by_event.get(source.event_id, {})
        ]
        selected_source = valid_sources[0] if valid_sources else dimension.source_refs[0]
        selected_key = (
            selected_source.event_id,
            selected_source.event_type_l2_id,
            selected_source.dim_key,
        )
        dimension.source_refs = [selected_source]
        dimension.source_event_ids = [selected_source.event_id]
        for value in dimension.values:
            selected_assignments = [
                assignment
                for assignment in value.source_assignments
                if (
                    assignment.event_id,
                    assignment.event_type_l2_id,
                    assignment.dim_key,
                )
                == selected_key
            ]
            value.source_assignments = (
                selected_assignments[:1]
                if selected_assignments
                else [
                    selected_source.model_copy(
                        update={"value": value.label},
                    ),
                ]
            )

    reserved_valid_sources = {
        (source.event_id, source.dim_key)
        for dimension in dimensions
        if len(dimension.source_refs) == 1
        for source in dimension.source_refs
        if source.dim_key in source_dimensions_by_event.get(source.event_id, {})
    }
    shock_keys_by_event = {shock.event_id: set(shock.source_dimension_keys) for shock in result.event_shocks}
    used_sources: set[tuple[int, str]] = set()
    dimension_id_renames: dict[str, str] = {}
    dimension_ids_to_remove: set[str] = set()

    for dimension in dimensions:
        if len(dimension.source_refs) != 1:
            continue
        source = dimension.source_refs[0]
        original_definition = source_dimensions_by_event.get(
            source.event_id,
            {},
        ).get(source.dim_key)
        if isinstance(original_definition, dict):
            _hydrate_or_validate_source_revision(
                source,
                source_definition=original_definition,
                context=f"dimension {dimension.dimension_id}",
            )
            for value in dimension.values:
                for assignment in value.source_assignments:
                    if assignment.event_id == source.event_id and assignment.dim_key == source.dim_key:
                        _hydrate_or_validate_source_revision(
                            assignment,
                            source_definition=original_definition,
                            context=(f"dimension value {dimension.dimension_id}={value.value_id}"),
                        )
        target_event_id = source.event_id
        target_dim_key = source.dim_key

        if source.dim_key not in source_dimensions_by_event.get(
            source.event_id,
            {},
        ):
            exact_sources = [
                (event_id, source.dim_key)
                for event_id in event_ids
                if source.dim_key in source_dimensions_by_event.get(event_id, {})
            ]
            exact_event_ids = [
                event_id
                for event_id, dim_key in exact_sources
                if (event_id, dim_key) not in reserved_valid_sources and (event_id, dim_key) not in used_sources
            ]
            if exact_event_ids:
                target_event_id = exact_event_ids[0]
            elif exact_sources and all(
                source_key in reserved_valid_sources or source_key in used_sources for source_key in exact_sources
            ):
                dimension_ids_to_remove.add(dimension.dimension_id)
                continue
            else:
                available_keys = [
                    dim_key
                    for dim_key in source_dimensions_by_event.get(
                        source.event_id,
                        {},
                    )
                    if (source.event_id, dim_key) not in reserved_valid_sources
                    and (source.event_id, dim_key) not in used_sources
                ]
                source_tokens = set(source.dim_key.lower().split("_"))
                ranked_keys = sorted(
                    available_keys,
                    key=lambda dim_key: (
                        dim_key in shock_keys_by_event.get(source.event_id, set()),
                        len(source_tokens & set(dim_key.lower().split("_"))),
                        -len(dim_key),
                        dim_key,
                    ),
                    reverse=True,
                )
                if ranked_keys:
                    best_key = ranked_keys[0]
                    has_token_evidence = bool(
                        source_tokens & set(best_key.lower().split("_")),
                    )
                    if has_token_evidence:
                        target_dim_key = best_key

        target_source = (target_event_id, target_dim_key)
        target_definition = source_dimensions_by_event.get(
            target_event_id,
            {},
        ).get(target_dim_key)
        if target_definition is None:
            continue
        if target_source in used_sources:
            dimension_ids_to_remove.add(dimension.dimension_id)
            continue

        target_event_type_l2_id = source.event_type_l2_id
        target_template_id = source.scenario_dimension_template_id
        target_template_checksum = source.template_checksum
        if isinstance(target_definition, dict) and target_definition.get("event_type_l2_id") is not None:
            target_event_type_l2_id = int(
                target_definition["event_type_l2_id"],
            )
        if isinstance(target_definition, dict):
            if target_definition.get("scenario_dimension_template_id") is not None:
                target_template_id = int(
                    target_definition["scenario_dimension_template_id"],
                )
            target_template_checksum = str(
                target_definition.get("template_checksum") or target_template_checksum or "",
            )

        original_dimension_id = dimension.dimension_id
        target_dimension_id = f"e{target_event_id}__{target_dim_key}"
        source.event_id = target_event_id
        source.event_type_l2_id = target_event_type_l2_id
        source.scenario_dimension_template_id = target_template_id
        source.template_checksum = target_template_checksum
        source.dim_key = target_dim_key
        dimension.dimension_id = target_dimension_id
        dimension.source_event_ids = [target_event_id]
        if len(dimension.values) > 0:
            for value in dimension.values:
                if len(value.source_assignments) != 1:
                    continue
                assignment = value.source_assignments[0]
                assignment.event_id = target_event_id
                assignment.event_type_l2_id = target_event_type_l2_id
                assignment.scenario_dimension_template_id = target_template_id
                assignment.template_checksum = target_template_checksum
                assignment.dim_key = target_dim_key
        if original_dimension_id != target_dimension_id:
            dimension_id_renames[original_dimension_id] = target_dimension_id
        used_sources.add(target_source)

    if dimension_ids_to_remove:
        result.dimension_definitions = [
            dimension for dimension in dimensions if dimension.dimension_id not in dimension_ids_to_remove
        ]

    for scenario in result.scenarios:
        normalized_values: dict[str, str] = {}
        for dimension_id, value in scenario.dimension_values.items():
            if dimension_id in dimension_ids_to_remove:
                continue
            normalized_id = dimension_id_renames.get(
                dimension_id,
                dimension_id,
            )
            if normalized_id in normalized_values:
                raise ValueError(
                    f"v2 sourceRef normalization produced duplicate scenario cells: {normalized_id}",
                )
            normalized_values[normalized_id] = value
        scenario.dimension_values = normalized_values

    for interaction in result.interactions:
        if interaction.resolution_dimension_id in dimension_ids_to_remove:
            interaction.resolution_dimension_id = None
        if interaction.resolution_dimension_id in dimension_id_renames:
            interaction.resolution_dimension_id = dimension_id_renames[interaction.resolution_dimension_id]


def _ensure_interaction_dimension_coverage(
    interaction: EventInteraction,
    dimensions: list[DimensionDefinition],
) -> None:
    if interaction.relation == "independent":
        interaction.resolution_dimension_id = None
        return

    interaction_events = set(interaction.event_ids)
    dimension_by_id = {dimension.dimension_id: dimension for dimension in dimensions}
    current = dimension_by_id.get(interaction.resolution_dimension_id or "")
    complete_candidates = [
        dimension
        for dimension in dimensions
        if interaction_events <= {source.event_id for source in dimension.source_refs}
    ]
    if current in complete_candidates:
        target = current
    elif complete_candidates:
        target = min(
            complete_candidates,
            key=lambda dimension: (
                len(dimension.source_refs),
                dimension.display_order,
                dimension.dimension_id,
            ),
        )
    else:
        target = max(
            dimensions,
            key=lambda dimension: (
                len(
                    interaction_events & {source.event_id for source in dimension.source_refs},
                ),
                -len(dimension.source_refs),
                -dimension.display_order,
                dimension.dimension_id,
            ),
        )
        target_event_ids = {source.event_id for source in target.source_refs}
        for missing_event_id in sorted(interaction_events - target_event_ids):
            source_template = next(
                source
                for dimension in dimensions
                for source in dimension.source_refs
                if source.event_id == missing_event_id
            )
            source_ref = source_template.model_copy(
                update={
                    "value": None,
                    "source_type": "derived_interpretation",
                    "assumption_yn": "N",
                    "rationale": ("상호작용 dimension이 해당 Event의 기존 source lineage를 함께 해석한다."),
                },
            )
            target.source_refs.append(source_ref)
            for value in target.values:
                value.source_assignments.append(
                    source_ref.model_copy(update={"value": value.label}),
                )
        target.source_event_ids = sorted(
            {source.event_id for source in target.source_refs},
        )

    if interaction.resolution_dimension_id is not None:
        interaction.resolution_dimension_id = target.dimension_id


def _validate_source_revision(
    source: SourceLineage,
    *,
    source_definition: dict[str, object],
    context: str,
) -> None:
    template_id = source_definition.get("scenario_dimension_template_id")
    template_checksum = str(
        source_definition.get("template_checksum") or "",
    ).strip()
    if template_id is None or not template_checksum:
        raise ValueError(
            f"{context} source Template revision metadata is unavailable",
        )
    if source.scenario_dimension_template_id != int(template_id) or source.template_checksum != template_checksum:
        raise ValueError(
            f"{context} source Template revision does not match: eventId={source.event_id}, dimKey={source.dim_key}",
        )


def _hydrate_or_validate_source_revision(
    source: SourceLineage,
    *,
    source_definition: dict[str, object],
    context: str,
) -> None:
    template_id = source_definition.get("scenario_dimension_template_id")
    template_checksum = str(
        source_definition.get("template_checksum") or "",
    ).strip()
    if template_id is None or not template_checksum:
        raise ValueError(
            f"{context} source Template revision metadata is unavailable",
        )
    if (
        source.scenario_dimension_template_id is not None and source.scenario_dimension_template_id != int(template_id)
    ) or (source.template_checksum is not None and source.template_checksum != template_checksum):
        raise ValueError(
            f"{context} source Template revision does not match: eventId={source.event_id}, dimKey={source.dim_key}",
        )
    source.scenario_dimension_template_id = int(template_id)
    source.template_checksum = template_checksum


def _validate_v2_selection_partition(
    result: MultiEventGenerationResult,
    *,
    source_dimensions_by_event: dict[
        int,
        dict[str, bool | dict[str, object]],
    ],
) -> None:
    all_sources = {
        (event_id, dim_key)
        for event_id, source_dimensions in source_dimensions_by_event.items()
        for dim_key in source_dimensions
    }
    selected_sources: set[tuple[int, str]] = set()
    selected_required_sources: set[tuple[int, str]] = set()
    for dimension in result.dimension_definitions:
        criterion = dimension.selection_criterion
        rationale = str(dimension.selection_rationale or "").strip()
        if criterion not in {
            "direct_event_fact",
            "lng_impact_path",
            "both",
        }:
            raise ValueError(
                "v2 selected dimensions require a relevant selectionCriterion",
            )
        if not rationale:
            raise ValueError(
                "v2 selected dimensions require selectionRationale",
            )
        expected_prefix = {
            "direct_event_fact": "(a)",
            "lng_impact_path": "(c)",
            "both": "(a)(c)",
        }[criterion]
        if not rationale.startswith(expected_prefix):
            raise ValueError(
                "v2 selectionRationale prefix must match selectionCriterion: "
                f"criterion={criterion}, expectedPrefix={expected_prefix}",
            )
        source = dimension.source_refs[0]
        source_key = (source.event_id, source.dim_key)
        if source_key in selected_sources:
            raise ValueError(
                f"v2 selected dimensions contain a duplicate source: {source_key}",
            )
        selected_sources.add(source_key)
        source_definition = source_dimensions_by_event.get(
            source.event_id,
            {},
        ).get(source.dim_key)
        if isinstance(source_definition, dict) and bool(
            source_definition.get("required", False),
        ):
            selected_required_sources.add(source_key)

    excluded_sources: set[tuple[int, str]] = set()
    relevant_required_sources = set(selected_required_sources)
    for decision in result.excluded_dimensions:
        source_key = (decision.event_id, decision.dim_key)
        if source_key in excluded_sources:
            raise ValueError(
                f"v2 excludedDimensions contains a duplicate source: {source_key}",
            )
        excluded_sources.add(source_key)
        source_definition = source_dimensions_by_event.get(
            decision.event_id,
            {},
        ).get(decision.dim_key)
        if not isinstance(source_definition, dict):
            raise ValueError(
                f"v2 excludedDimensions references an unknown source: {source_key}",
            )
        expected_event_type_l2_id = int(
            source_definition.get("event_type_l2_id") or 0,
        )
        expected_template_id = source_definition.get(
            "scenario_dimension_template_id",
        )
        expected_template_checksum = str(
            source_definition.get("template_checksum") or "",
        )
        if (
            decision.event_type_l2_id != expected_event_type_l2_id
            or expected_template_id is None
            or decision.scenario_dimension_template_id != int(expected_template_id)
            or decision.template_checksum != expected_template_checksum
            or decision.required != bool(source_definition.get("required", False))
        ):
            raise ValueError(
                f"v2 excludedDimensions Template metadata does not match: {source_key}",
            )
        if decision.required and decision.selection_criterion != "none":
            relevant_required_sources.add(source_key)

    overlap = selected_sources & excluded_sources
    if overlap:
        raise ValueError(
            f"v2 selected and excluded dimensions overlap: {sorted(overlap)}",
        )
    partition = selected_sources | excluded_sources
    if partition != all_sources:
        missing = sorted(all_sources - partition)
        unknown = sorted(partition - all_sources)
        raise ValueError(
            "v2 selected/excluded dimensions must partition every Template "
            f"candidate exactly once: missing={missing}, unknown={unknown}",
        )

    omitted_relevant_required = relevant_required_sources - selected_sources
    if len(relevant_required_sources) <= 6 and omitted_relevant_required:
        raise ValueError(
            "v2 must select every relevant required dimension when their "
            f"count is at most 6: {sorted(omitted_relevant_required)}",
        )


def _validate_pressure_aggregate_order(
    scenarios: list[ScenarioCandidate],
    *,
    contribution_by_value: dict[str, dict[str, str | None]],
) -> None:
    contribution_score = {
        "bullish": 1,
        "balanced": 0,
        "bearish": -1,
    }
    scored = [
        (
            scenario,
            sum(
                contribution_score[str(contribution_by_value[dimension_id][value])]
                for dimension_id, value in scenario.dimension_values.items()
            ),
        )
        for scenario in scenarios
    ]
    for scenario, score in scored:
        if scenario.global_pressure_band == "strong_bullish" and score <= 0:
            raise ValueError(
                "strong_bullish Scenario requires a positive aggregate pressure score",
            )
        if scenario.global_pressure_band == "strong_bearish" and score >= 0:
            raise ValueError(
                "strong_bearish Scenario requires a negative aggregate pressure score",
            )
    for (higher, higher_score), (lower, lower_score) in zip(
        scored,
        scored[1:],
        strict=False,
    ):
        if higher_score < lower_score:
            raise ValueError(
                "Scenario aggregate pressure contributions must be "
                "nondecreasing from strong_bearish to strong_bullish: "
                f"{higher.global_pressure_band}={higher_score}, "
                f"{lower.global_pressure_band}={lower_score}",
            )


def _finalize_scenario_candidates(
    *,
    scenarios: list[ScenarioCandidate],
    excluded_candidates: list[ExcludedGenerationCandidate],
    dimensions: list[DimensionDefinition] | list[V2DimensionDefinition] | list[V3DimensionDefinition],
    require_pressure_partition: bool = True,
) -> list[ScenarioCandidate]:
    sorted_scenarios = sorted(
        scenarios,
        key=lambda scenario: PRESSURE_RANK[scenario.global_pressure_band],
        reverse=True,
    )
    if not 3 <= len(sorted_scenarios) <= 5:
        raise ValueError("final scenario count must be between 3 and 5")
    pressure_bands = [scenario.global_pressure_band for scenario in sorted_scenarios]
    if len(set(pressure_bands)) != len(pressure_bands):
        raise ValueError("final scenarios must have unique globalPressureBand values")
    excluded_bands = [candidate.global_pressure_band for candidate in excluded_candidates]
    if set(pressure_bands) & set(excluded_bands):
        raise ValueError("a pressure band cannot be both generated and excluded")
    if require_pressure_partition and set(pressure_bands) | set(excluded_bands) != set(PRESSURE_BANDS):
        raise ValueError(
            "generated and excluded candidates must account for all target pressure bands",
        )

    dimension_ids = [dimension.dimension_id for dimension in dimensions]
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
    seen_combinations: set[tuple[tuple[str, str], ...]] = set()
    for scenario in sorted_scenarios:
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
        if combination in seen_combinations:
            raise ValueError("scenario dimension combinations must be unique")
        seen_combinations.add(combination)
        contributions = {
            contribution_by_value[dimension_id][value] for dimension_id, value in scenario.dimension_values.items()
        }
        if scenario.mixed_factors and not {"bullish", "bearish"} <= contributions:
            raise ValueError(
                f"mixedFactors=true requires both bullish and bearish dimension contributions: {scenario.title}",
            )

    _validate_pressure_aggregate_order(
        sorted_scenarios,
        contribution_by_value=contribution_by_value,
    )

    ranked = sorted(
        range(len(sorted_scenarios)),
        key=lambda index: PRESSURE_RANK[sorted_scenarios[index].global_pressure_band],
    )
    if len(ranked) < 2:
        raise ValueError("floor and ceiling roles require at least two scenarios")
    floor_index = ranked[0]
    ceiling_index = ranked[-1]
    interior = [index for index in ranked[1:-1] if sorted_scenarios[index].mixed_factors]
    mixed_index = (
        min(
            interior,
            key=lambda index: abs(
                PRESSURE_RANK[sorted_scenarios[index].global_pressure_band] - PRESSURE_RANK["balanced"],
            ),
        )
        if interior
        else None
    )
    baseline_index = max(
        range(len(sorted_scenarios)),
        key=lambda index: (sorted_scenarios[index].probability_score, -index),
    )

    finalized: list[ScenarioCandidate] = []
    for index, scenario in enumerate(sorted_scenarios):
        if index == floor_index:
            role = "floor"
        elif index == ceiling_index:
            role = "ceiling"
        elif mixed_index is not None and index == mixed_index:
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
    return finalized


def finalize_v2_generation_result(
    result: V2MultiEventGenerationResult,
    *,
    event_ids: list[int],
    source_dimensions_by_event: dict[int, dict[str, bool | dict[str, object]]] | None,
) -> V2FinalizedGenerationResult:
    """Hydrate and validate compact v2 without detailed lineage repair."""
    if source_dimensions_by_event is None:
        raise ValueError("v2 generation requires input Template dimensions")

    known_event_ids = set(event_ids)
    shock_event_ids = [shock.event_id for shock in result.event_shocks]
    if set(shock_event_ids) != known_event_ids or len(shock_event_ids) != len(known_event_ids):
        raise ValueError("eventShocks must contain every input event exactly once")
    if not 3 <= len(result.selected_dimensions) <= 6:
        raise ValueError(
            f"multi_event_source_dimensions dimension count is out of range: {len(result.selected_dimensions)}",
        )

    selected_source_keys: set[tuple[int, int, str]] = set()
    dimension_ids: set[str] = set()
    dimensions: list[V2DimensionDefinition] = []
    for selected in result.selected_dimensions:
        source = selected.source_ref
        if source.event_id not in known_event_ids:
            raise ValueError(f"v2 dimension references an unknown event: {selected.dimension_id}")
        raw_definition = source_dimensions_by_event.get(source.event_id, {}).get(source.dim_key)
        if not isinstance(raw_definition, dict):
            raise ValueError(
                "v2 sourceRef is not present in the input Template: "
                f"eventId={source.event_id}, dimKey={source.dim_key}",
            )
        expected_template_id = raw_definition.get("scenario_dimension_template_id")
        if expected_template_id is None or source.scenario_dimension_template_id != int(expected_template_id):
            raise ValueError(
                f"v2 sourceRef Template ID does not match: eventId={source.event_id}, dimKey={source.dim_key}",
            )
        expected_dimension_id = f"e{source.event_id}__{source.dim_key}"
        if selected.dimension_id != expected_dimension_id:
            raise ValueError(f"v2 dimensionId must be namespaced as {expected_dimension_id}")

        source_key = (
            source.event_id,
            source.scenario_dimension_template_id,
            source.dim_key,
        )
        if source_key in selected_source_keys:
            raise ValueError(f"v2 selectedDimensions contains duplicate sourceRef: {source_key}")
        if selected.dimension_id in dimension_ids:
            raise ValueError(f"v2 selectedDimensions contains duplicate dimensionId: {selected.dimension_id}")
        selected_source_keys.add(source_key)
        dimension_ids.add(selected.dimension_id)

        value_ids = [value.value_id for value in selected.values]
        if len(value_ids) != len(set(value_ids)):
            raise ValueError(f"v2 dimension contains duplicate valueId: {selected.dimension_id}")
        dimensions.append(
            V2DimensionDefinition(
                dimension_id=selected.dimension_id,
                label=str(raw_definition.get("label") or source.dim_key),
                description=str(raw_definition.get("description") or raw_definition.get("label") or source.dim_key),
                required=bool(raw_definition.get("required", False)),
                selection_criterion=selected.selection_criterion,
                selection_rationale=selected.selection_rationale,
                source_ref=source,
                values=selected.values,
            ),
        )

    scenario_candidates: list[ScenarioCandidate] = []
    contributions = {
        dimension.dimension_id: {value.value_id: value.global_pressure_contribution for value in dimension.values}
        for dimension in dimensions
    }
    for scenario in result.scenarios:
        scenario_contributions = {
            contributions.get(dimension_id, {}).get(value_id)
            for dimension_id, value_id in scenario.dimension_values.items()
        }
        scenario_candidates.append(
            ScenarioCandidate(
                title=scenario.title,
                narrative=scenario.narrative,
                dimension_values=scenario.dimension_values,
                global_pressure_band=scenario.global_pressure_band,
                probability_score=scenario.probability_score,
                global_pressure_rationale=scenario.global_pressure_rationale,
                mixed_factors={"bullish", "bearish"} <= scenario_contributions,
            ),
        )

    finalized_scenarios = _finalize_scenario_candidates(
        scenarios=scenario_candidates,
        excluded_candidates=[],
        dimensions=dimensions,
        require_pressure_partition=False,
    )
    represented_bands = {scenario.global_pressure_band for scenario in finalized_scenarios}
    unrepresented_bands = [band for band in PRESSURE_BANDS if band not in represented_bands]

    unselected_refs: list[V2SourceReference] = []
    for event_id in event_ids:
        for dim_key, raw_definition in source_dimensions_by_event.get(event_id, {}).items():
            if not isinstance(raw_definition, dict):
                continue
            template_id = raw_definition.get("scenario_dimension_template_id")
            if template_id is None:
                continue
            source_key = (event_id, int(template_id), dim_key)
            if source_key not in selected_source_keys:
                unselected_refs.append(
                    V2SourceReference(
                        event_id=event_id,
                        scenario_dimension_template_id=int(template_id),
                        dim_key=dim_key,
                    ),
                )

    return V2FinalizedGenerationResult(
        scenario_group_title=result.scenario_group_title,
        scenario_group_description=result.scenario_group_description,
        event_shocks=result.event_shocks,
        dimension_definitions=dimensions,
        scenarios=finalized_scenarios,
        unselected_dimension_refs=unselected_refs,
        unrepresented_pressure_bands=unrepresented_bands,
    )


def finalize_v3_generation_result(
    result: V3MultiEventGenerationResult,
    *,
    event_ids: list[int],
    source_dimensions_by_event: dict[int, dict[str, bool | dict[str, object]]] | None = None,
) -> V3MultiEventGenerationResult:
    """Validate v3 without applying v2 lineage normalization or projection repair."""
    known_event_ids = set(event_ids)
    shock_event_ids = [shock.event_id for shock in result.event_shocks]
    if set(shock_event_ids) != known_event_ids or len(shock_event_ids) != len(known_event_ids):
        raise ValueError("eventShocks must contain every input event exactly once")

    dimensions = result.dimension_definitions
    if not 3 <= len(dimensions) <= 6:
        raise ValueError(
            f"multi_event_composite_dimensions dimension count is out of range: {len(dimensions)}",
        )
    dimension_ids = [dimension.dimension_id for dimension in dimensions]
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ValueError("dimensionDefinitions contains duplicate dimensionId")

    valid_template_refs: set[tuple[int, str]] | None = None
    if source_dimensions_by_event is not None:
        valid_template_refs = set()
        for definitions in source_dimensions_by_event.values():
            for dim_key, raw_definition in definitions.items():
                if not isinstance(raw_definition, dict):
                    continue
                template_id = raw_definition.get("scenario_dimension_template_id")
                if template_id is not None:
                    valid_template_refs.add((int(template_id), dim_key))

    covered_event_ids: set[int] = set()
    for dimension in dimensions:
        normalized_event_ids = [int(event_id) for event_id in dimension.source_event_ids]
        if len(normalized_event_ids) != len(set(normalized_event_ids)):
            raise ValueError(
                f"dimension contains duplicate sourceEventIds: {dimension.dimension_id}",
            )
        if not set(normalized_event_ids) <= known_event_ids:
            raise ValueError(
                f"dimension references an unknown event: {dimension.dimension_id}",
            )
        dimension.source_event_ids = normalized_event_ids
        covered_event_ids.update(normalized_event_ids)

        source_keys = [(source.scenario_dimension_template_id, source.dim_key) for source in dimension.source_refs]
        if len(source_keys) != len(set(source_keys)):
            raise ValueError(
                f"dimension contains duplicate sourceRefs: {dimension.dimension_id}",
            )
        if valid_template_refs is not None:
            unknown_refs = set(source_keys) - valid_template_refs
            if unknown_refs:
                raise ValueError(
                    "dimension sourceRef is not present in the input Template: "
                    f"dimensionId={dimension.dimension_id}, sourceRefs={sorted(unknown_refs)}",
                )

        if not 3 <= len(dimension.values) <= 5:
            raise ValueError(
                f"multi-event dimensions must define 3 to 5 generated values: {dimension.dimension_id}",
            )
        value_ids = [value.value_id for value in dimension.values]
        if len(value_ids) != len(set(value_ids)):
            raise ValueError(
                f"dimension contains duplicate valueId: {dimension.dimension_id}",
            )

    if covered_event_ids != known_event_ids:
        missing = sorted(known_event_ids - covered_event_ids)
        raise ValueError(f"events without a selected dimension: {missing}")

    dimension_by_id = {dimension.dimension_id: dimension for dimension in dimensions}
    for interaction in result.interactions:
        interaction_event_ids = set(interaction.event_ids)
        if not interaction_event_ids <= known_event_ids:
            raise ValueError("interaction references an unknown event")
        if interaction.resolution_dimension_id is not None:
            resolution_dimension = dimension_by_id.get(interaction.resolution_dimension_id)
            if resolution_dimension is None:
                raise ValueError(
                    "interaction resolutionDimensionId is not a generated dimension",
                )
            if not interaction_event_ids <= set(resolution_dimension.source_event_ids):
                raise ValueError(
                    "an interaction resolution dimension must reference every interaction event",
                )
        if interaction.relation != "independent" and not any(
            interaction_event_ids <= set(dimension.source_event_ids) for dimension in dimensions
        ):
            raise ValueError(
                "non-independent interactions must be represented by sourceEventIds on one dimension",
            )

    finalized_scenarios = _finalize_scenario_candidates(
        scenarios=result.scenarios,
        excluded_candidates=result.excluded_candidates,
        dimensions=dimensions,
    )
    return V3MultiEventGenerationResult.model_validate(
        result.model_copy(update={"scenarios": finalized_scenarios}).model_dump(),
    )


def finalize_generation_result(
    result: V2MultiEventGenerationResult | MultiEventGenerationResult | V3MultiEventGenerationResult,
    *,
    generation_strategy: str,
    event_ids: list[int],
    source_dimensions_by_event: (dict[int, dict[str, bool | dict[str, object]]] | None) = None,
) -> V2FinalizedGenerationResult | MultiEventGenerationResult | V3MultiEventGenerationResult:
    """Validate the LLM result and deterministically assign roles/baseline."""
    if generation_strategy == "multi_event_source_dimensions":
        if not isinstance(result, V2MultiEventGenerationResult):
            raise ValueError("v2 generation requires V2MultiEventGenerationResult")
        return finalize_v2_generation_result(
            result,
            event_ids=event_ids,
            source_dimensions_by_event=source_dimensions_by_event,
        )
    if generation_strategy == "multi_event_composite_dimensions":
        if not isinstance(result, V3MultiEventGenerationResult):
            raise ValueError("v3 generation requires V3MultiEventGenerationResult")
        return finalize_v3_generation_result(
            result,
            event_ids=event_ids,
            source_dimensions_by_event=source_dimensions_by_event,
        )
    if generation_strategy != "multi_event_source_dimensions":
        raise ValueError(
            f"unsupported multi-event generation strategy: {generation_strategy}",
        )
    dimensions = result.dimension_definitions
    expected_dimension_range = range(3, 7)
    if len(dimensions) not in expected_dimension_range:
        raise ValueError(
            f"{generation_strategy} dimension count is out of range: {len(dimensions)}",
        )

    known_event_ids = set(event_ids)
    shock_event_ids = [shock.event_id for shock in result.event_shocks]
    if set(shock_event_ids) != known_event_ids or len(shock_event_ids) != len(
        known_event_ids,
    ):
        raise ValueError("eventShocks must contain every input event exactly once")
    if source_dimensions_by_event is not None:
        _normalize_dimension_source_key_aliases(
            result,
            source_dimensions_by_event=source_dimensions_by_event,
        )
        for shock in result.event_shocks:
            _normalize_event_shock_source_keys(shock)
            _ground_event_shock_source_keys(
                shock,
                dimensions=dimensions,
                source_dimensions_by_event=source_dimensions_by_event,
            )
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
            _normalize_event_shock_values(shock)
            unknown_keys = set(shock.source_dimension_keys) - set(
                source_dimensions_by_event.get(shock.event_id, {}),
            )
            if unknown_keys:
                raise ValueError(
                    "EventShock sourceDimensionKeys are not present in the "
                    f"Event Type Template: eventId={shock.event_id}, "
                    f"dimKeys={sorted(unknown_keys)}",
                )
            _normalize_event_shock_source_dimensions(
                shock,
                source_dimensions_by_event=source_dimensions_by_event,
            )
            _validate_event_shock_template_examples(
                shock,
                source_dimensions_by_event=source_dimensions_by_event,
            )
        if generation_strategy == "multi_event_source_dimensions":
            _normalize_v2_dimension_source_refs(
                result,
                event_ids=event_ids,
                source_dimensions_by_event=source_dimensions_by_event,
            )
            dimensions = result.dimension_definitions
            if len(dimensions) not in expected_dimension_range:
                raise ValueError(
                    f"{generation_strategy} dimension count is out of "
                    f"range after sourceRef normalization: "
                    f"{len(dimensions)}",
                )

    dimension_ids = [dimension.dimension_id for dimension in dimensions]
    if len(set(dimension_ids)) != len(dimension_ids):
        raise ValueError("dimensionDefinitions contains duplicate dimensionId")

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
                if isinstance(source_definition, dict):
                    _validate_source_revision(
                        source,
                        source_definition=source_definition,
                        context=f"dimension {dimension.dimension_id}",
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
                    dimension.label = expected_label
                    dimension.description = expected_description
                    dimension.required = bool(
                        source_definition.get("required", False),
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
            if source_dimensions_by_event is not None:
                for assignment in value.source_assignments:
                    assignment_definition = source_dimensions_by_event.get(
                        assignment.event_id,
                        {},
                    ).get(assignment.dim_key)
                    if isinstance(assignment_definition, dict):
                        _validate_source_revision(
                            assignment,
                            source_definition=assignment_definition,
                            context=(f"dimension value {dimension.dimension_id}={value.value_id}"),
                        )
            if generation_strategy == "multi_event_source_dimensions" and len(value.source_assignments) != 1:
                raise ValueError(
                    "v2 dimension values must have exactly one sourceAssignment",
                )
    if generation_strategy == "multi_event_composite_dimensions" and covered_event_ids != known_event_ids:
        missing = sorted(known_event_ids - covered_event_ids)
        raise ValueError(f"events without a selected dimension: {missing}")
    for interaction in result.interactions:
        if not set(interaction.event_ids) <= known_event_ids:
            raise ValueError("interaction references an unknown event")
        if generation_strategy == "multi_event_composite_dimensions":
            _ensure_interaction_dimension_coverage(
                interaction,
                dimensions,
            )
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
        _validate_v2_selection_partition(
            result,
            source_dimensions_by_event=source_dimensions_by_event,
        )

    finalized = _finalize_scenario_candidates(
        scenarios=result.scenarios,
        excluded_candidates=result.excluded_candidates,
        dimensions=dimensions,
    )
    return MultiEventGenerationResult.model_validate(
        result.model_copy(update={"scenarios": finalized}).model_dump(),
    )
