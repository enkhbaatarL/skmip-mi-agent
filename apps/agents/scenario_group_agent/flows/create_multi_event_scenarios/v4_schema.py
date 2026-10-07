from __future__ import annotations

from collections import defaultdict
from decimal import ROUND_FLOOR, Decimal
import hashlib
from typing import Any, Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.schema import (
    PRESSURE_BANDS,
    PRESSURE_RANK,
    PressureBand,
    ScenarioDimensionValues,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_budget import (
    interaction_count_target,
    interaction_question_budget,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_enums import (
    StateDirection,
)
from apps.agents.scenario_group_agent.schemas.base import ApiModel
from apps.persistence.model_impact_lever.schema import (
    ModelImpactLeverPayload,
    ModelImpactLeverSupportIssue,
)
from apps.persistence.scenario.schema import RelatedMarket


Materiality = Literal["high", "medium", "low"]
BalanceDirection = Literal["increase", "decrease", "mixed", "unchanged"]
BalanceWireValue = Literal[
    "demand|increase",
    "demand|decrease",
    "demand|mixed",
    "demand|unchanged",
    "supply|increase",
    "supply|decrease",
    "supply|mixed",
    "supply|unchanged",
    "trade|increase",
    "trade|decrease",
    "trade|mixed",
    "trade|unchanged",
    "none",
]
UncertaintyAxis = Literal[
    "magnitude",
    "scope",
    "timing",
    "duration",
    "recovery",
    "mitigation",
    "substitution",
]


class V4ValidationWarning(ApiModel):
    model_config = ConfigDict(extra="forbid")

    stage: Literal["event_impact_analysis", "dimension_design", "scenario_synthesis"]
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    reference_ids: list[str] = Field(default_factory=list)


class V4EventFact(ApiModel):
    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1)
    event_id: int = Field(gt=0)
    observed_basis: str = Field(min_length=1)
    observed_at: str | None = None

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_fact_classification(cls, value: Any) -> Any:
        """Read previously stored v4 diagnostics without re-exposing unused classifications."""
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        for key in (
            "factStatus",
            "fact_status",
            "confidence",
            "noMaterialImpactReason",
            "no_material_impact_reason",
        ):
            normalized.pop(key, None)
        return normalized


class V4EventAnalysisExclusion(ApiModel):
    model_config = ConfigDict(extra="forbid")

    event_id: int = Field(gt=0)
    reason_type: Literal["no_usable_fact", "no_material_impact"]
    reason: str = Field(min_length=1)


class V4LeverStepDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    lever_code: str = Field(min_length=1)
    path_role: Literal["primary", "driver", "transmission"]
    state_direction: StateDirection
    scope: str = Field(min_length=1)
    timing: str = Field(min_length=1)


class V4LeverStep(V4LeverStepDraft):
    impact_lever_id: int = Field(gt=0)


class V4BalanceEffect(ApiModel):
    model_config = ConfigDict(extra="forbid")

    domain: Literal["demand", "supply", "trade"]
    direction: BalanceDirection
    rationale: str = Field(min_length=1)


class V4EventImpactPathDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    impact_path_id: str = Field(min_length=1)
    event_id: int = Field(gt=0)
    source_fact_ids: list[str] = Field(min_length=1)
    mechanism: str = Field(min_length=1)
    lever_steps: list[V4LeverStepDraft] = Field(min_length=1)
    balance_effect: V4BalanceEffect | None = None
    materiality: Materiality

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_price_effect(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.pop("priceEffect", None)
        normalized.pop("price_effect", None)
        return normalized

    @model_validator(mode="after")
    def validate_unique_lever_steps(self) -> V4EventImpactPathDraft:
        if len(self.source_fact_ids) != len(set(self.source_fact_ids)):
            raise ValueError("impact path sourceFactIds must be unique")
        lever_codes = [step.lever_code for step in self.lever_steps]
        if len(lever_codes) != len(set(lever_codes)):
            raise ValueError("impact path leverSteps must contain unique leverCodes")
        return self


class V4EventImpactPath(ApiModel):
    model_config = ConfigDict(extra="forbid")

    impact_path_id: str = Field(min_length=1)
    event_id: int = Field(gt=0)
    source_fact_ids: list[str] = Field(min_length=1)
    mechanism: str = Field(min_length=1)
    lever_steps: list[V4LeverStep] = Field(min_length=1)
    balance_effect: V4BalanceEffect | None = None
    materiality: Materiality

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_price_effect(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.pop("priceEffect", None)
        normalized.pop("price_effect", None)
        return normalized


class V4PathUncertainty(ApiModel):
    model_config = ConfigDict(extra="forbid")

    uncertainty_id: str = Field(min_length=1)
    impact_path_ids: list[str] = Field(min_length=1)
    axis_type: UncertaintyAxis
    subject: str
    affected_lever_code: str = Field(min_length=1)
    reason: str
    materiality: Materiality
    semantic_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_paths(self) -> V4PathUncertainty:
        if len(self.impact_path_ids) != len(set(self.impact_path_ids)):
            raise ValueError("path uncertainty impactPathIds must be unique")
        return self


class V4EventInteraction(ApiModel):
    model_config = ConfigDict(extra="forbid")

    interaction_id: str = Field(min_length=1)
    event_ids: list[int] = Field(min_length=2)
    impact_path_ids: list[str] = Field(min_length=2)
    relation: Literal[
        "amplification",
        "offset",
        "causal_link",
        "regional_coupling",
        "independent",
    ]
    mechanism: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_price_effect(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.pop("priceEffect", None)
        normalized.pop("price_effect", None)
        return normalized

    @model_validator(mode="after")
    def validate_unique_references(self) -> V4EventInteraction:
        if len(self.event_ids) != len(set(self.event_ids)):
            raise ValueError("interaction eventIds must be unique")
        if len(self.impact_path_ids) != len(set(self.impact_path_ids)):
            raise ValueError("interaction impactPathIds must be unique")
        return self


class V4InteractionUncertainty(ApiModel):
    model_config = ConfigDict(extra="forbid")

    uncertainty_id: str = Field(min_length=1)
    interaction_id: str = Field(min_length=1)
    impact_path_ids: list[str] = Field(min_length=2)
    axis_type: UncertaintyAxis
    subject: str
    affected_lever_code: str = Field(min_length=1)
    reason: str
    materiality: Materiality
    semantic_key: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_paths(self) -> V4InteractionUncertainty:
        if len(self.impact_path_ids) != len(set(self.impact_path_ids)):
            raise ValueError("interaction uncertainty impactPathIds must be unique")
        return self


class V4ReadableEventImpact(ApiModel):
    """Human-readable Event impact plus only the tokens required for deterministic hydration."""

    model_config = ConfigDict(extra="forbid")

    evidence: list[str] = Field(min_length=1, max_length=3)
    analysis: str = Field(min_length=20, max_length=240)
    lever_states: list[str] = Field(
        min_length=1,
        max_length=3,
        description=(
            "lever|role|direction|scope|timing 형식. 같은 Impact 안에서는 첫 번째 lever code가 모두 달라야 하며, "
            "동일 Lever의 여러 역할·범위·시점은 대표 step 하나로 통합"
        ),
    )
    balance: BalanceWireValue
    importance: Materiality


class V4ReadablePathQuestion(ApiModel):
    model_config = ConfigDict(extra="forbid")

    impact: int = Field(ge=1, le=3)
    question: str
    axis: UncertaintyAxis
    lever: str = Field(min_length=1)


class V4ReadableEventAnalysisDraft(ApiModel):
    """Event-local LLM response optimized for direct reading in traces."""

    model_config = ConfigDict(extra="forbid")

    event_facts: list[str] = Field(default_factory=list, max_length=3)
    decision_basis: list[str] = Field(default_factory=list, max_length=3)
    impacts: list[V4ReadableEventImpact] = Field(default_factory=list, max_length=3)
    open_questions: list[V4ReadablePathQuestion] = Field(default_factory=list)
    excluded_because: str | None = Field(default=None, max_length=160)

    @model_validator(mode="after")
    def validate_event_decision(self) -> V4ReadableEventAnalysisDraft:
        normalized_basis = [item.strip() for item in self.decision_basis]
        if any(not item for item in normalized_basis):
            raise ValueError("decisionBasis must not contain blank statements")
        if len(normalized_basis) != len(set(normalized_basis)):
            raise ValueError("decisionBasis must contain unique statements")
        self.decision_basis = normalized_basis
        if not self.event_facts:
            if self.decision_basis or self.impacts or self.open_questions or not self.excluded_because:
                raise ValueError("Event without selected facts requires excludedBecause and no analysis")
        elif self.impacts:
            if self.excluded_because:
                raise ValueError("Event with impacts cannot define excludedBecause")
        elif not self.excluded_because:
            raise ValueError("Event with facts but no impacts requires excludedBecause")
        return self


class V4ReadableInteraction(ApiModel):
    model_config = ConfigDict(extra="forbid")

    paths: list[str] = Field(min_length=2, max_length=3)
    analysis: str = Field(min_length=20, max_length=240)
    relation: Literal["amplification", "offset", "causal_link", "regional_coupling", "independent"]


class V4ReadableInteractionQuestion(ApiModel):
    model_config = ConfigDict(extra="forbid")

    interaction: int = Field(ge=1)
    question: str
    axis: UncertaintyAxis
    lever: str = Field(min_length=1)


class V4ReadableInteractionAnalysisDraft(ApiModel):
    """Cross-Event response expressed as causal sentences over Path cards."""

    model_config = ConfigDict(extra="forbid")

    interactions: list[V4ReadableInteraction] = Field(default_factory=list)
    open_questions: list[V4ReadableInteractionQuestion] = Field(default_factory=list)


class V4EventImpactAnalysisDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    event_facts: list[V4EventFact] = Field(default_factory=list)
    decision_basis: list[str] = Field(default_factory=list)
    event_exclusions: list[V4EventAnalysisExclusion] = Field(default_factory=list)
    impact_paths: list[V4EventImpactPathDraft] = Field(default_factory=list)
    path_uncertainties: list[V4PathUncertainty] = Field(default_factory=list)
    interactions: list[V4EventInteraction] = Field(default_factory=list)
    interaction_uncertainties: list[V4InteractionUncertainty] = Field(default_factory=list)
    validation_warnings: list[V4ValidationWarning] = Field(default_factory=list)


class V4EventImpactAnalysisResult(ApiModel):
    model_config = ConfigDict(extra="forbid")

    event_facts: list[V4EventFact] = Field(default_factory=list)
    decision_basis: list[str] = Field(default_factory=list)
    event_exclusions: list[V4EventAnalysisExclusion] = Field(default_factory=list)
    impact_paths: list[V4EventImpactPath] = Field(default_factory=list)
    path_uncertainties: list[V4PathUncertainty] = Field(default_factory=list)
    interactions: list[V4EventInteraction] = Field(default_factory=list)
    interaction_uncertainties: list[V4InteractionUncertainty] = Field(default_factory=list)
    validation_warnings: list[V4ValidationWarning] = Field(default_factory=list)


class V4LeverStateDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    lever_code: str = Field(min_length=1)
    direction: StateDirection
    level: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    time_window: str = Field(min_length=1)


class V4LeverState(V4LeverStateDraft):
    impact_lever_id: int = Field(gt=0)


class V4DimensionValueDefinitionDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    value_id: str = Field(min_length=1)
    label: str = Field(max_length=30)
    lever_states: list[V4LeverStateDraft] = Field(min_length=1)
    pressure_contribution: Literal["bullish", "balanced", "bearish"]
    assumption_rationale: str = Field(min_length=1)


class V4DimensionValueDefinition(ApiModel):
    model_config = ConfigDict(extra="forbid")

    value_id: str = Field(min_length=1)
    label: str = Field(max_length=30)
    lever_states: list[V4LeverState] = Field(min_length=1)
    pressure_contribution: Literal["bullish", "balanced", "bearish"]
    assumption_rationale: str = Field(min_length=1)


class V4DimensionDefinitionDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1)
    label: str = Field(max_length=30)
    description: str
    rationale: str = Field(max_length=200)
    source_impact_path_ids: list[str] = Field(min_length=1)
    source_uncertainty_ids: list[str] = Field(min_length=1)
    primary_lever_code: str = Field(min_length=1)
    dimension_type: UncertaintyAxis
    value_kind: Literal["categorical", "numeric_range", "temporal"]
    unit: str | None = None
    values: list[V4DimensionValueDefinitionDraft] = Field(min_length=2, max_length=4)

    @model_validator(mode="after")
    def validate_unique_values(self) -> V4DimensionDefinitionDraft:
        if len(self.source_impact_path_ids) != len(set(self.source_impact_path_ids)):
            raise ValueError("dimension sourceImpactPathIds must be unique")
        if len(self.source_uncertainty_ids) != len(set(self.source_uncertainty_ids)):
            raise ValueError("dimension sourceUncertaintyIds must be unique")
        value_ids = [value.value_id for value in self.values]
        if len(value_ids) != len(set(value_ids)):
            raise ValueError("dimension values must contain unique valueIds")
        return self


class V4DimensionDefinition(ApiModel):
    model_config = ConfigDict(extra="forbid")

    dimension_id: str = Field(min_length=1)
    label: str = Field(max_length=30)
    description: str
    rationale: str = Field(max_length=200)
    source_event_ids: list[int] = Field(min_length=1)
    source_impact_path_ids: list[str] = Field(min_length=1)
    source_uncertainty_ids: list[str] = Field(min_length=1)
    primary_lever_code: str = Field(min_length=1)
    primary_impact_lever_id: int = Field(gt=0)
    dimension_type: UncertaintyAxis
    value_kind: Literal["categorical", "numeric_range", "temporal"]
    unit: str | None = None
    model_support_status: Literal["full", "partial", "none", "price_only"]
    values: list[V4DimensionValueDefinition] = Field(min_length=2, max_length=4)


class V4DimensionDesignDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    dimension_definitions: list[V4DimensionDefinitionDraft] = Field(min_length=3, max_length=6)
    excluded_dimensions: list[str] = Field(default_factory=list)


class V4DimensionDesignResult(ApiModel):
    model_config = ConfigDict(extra="forbid")

    dimension_definitions: list[V4DimensionDefinition]
    excluded_dimensions: list[str] = Field(default_factory=list)
    validation_warnings: list[V4ValidationWarning] = Field(default_factory=list)


class V4PressureBreakdown(ApiModel):
    model_config = ConfigDict(extra="forbid")

    common_impact: str = Field(min_length=1)
    value_delta: str = Field(min_length=1)
    interaction_effect: str = Field(min_length=1)


class V4ScenarioCandidateDraft(ApiModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=40)
    narrative: str = Field(min_length=1)
    dimension_values: ScenarioDimensionValues
    common_impact_path_ids: list[str] = Field(min_length=1)
    applied_interaction_ids: list[str] = Field(default_factory=list)
    pressure_band: PressureBand
    pressure_breakdown: V4PressureBreakdown
    related_markets: list[RelatedMarket] = Field(default_factory=list, max_length=2)
    probability_score: float = Field(
        ge=0,
        le=100,
        description="서버 정규화 후 전체 Scenario 합계가 100이 되는 0~100 정수 백분율 점수",
    )
    mixed_factors: list[str] = Field(default_factory=list)
    explanation: str = Field(min_length=1)

    @field_validator("related_markets")
    @classmethod
    def discard_duplicate_related_markets(cls, value: list[RelatedMarket]) -> list[RelatedMarket]:
        unique_markets: list[RelatedMarket] = []
        seen_markets: set[str] = set()
        for related_market in value:
            if related_market.market in seen_markets:
                continue
            seen_markets.add(related_market.market)
            unique_markets.append(related_market)
        return unique_markets

    @model_validator(mode="after")
    def validate_unique_references(self) -> V4ScenarioCandidateDraft:
        if len(self.common_impact_path_ids) != len(set(self.common_impact_path_ids)):
            raise ValueError("Scenario commonImpactPathIds must be unique")
        if len(self.applied_interaction_ids) != len(set(self.applied_interaction_ids)):
            raise ValueError("Scenario appliedInteractionIds must be unique")
        return self


class V4ScenarioCandidate(V4ScenarioCandidateDraft):
    pressure_rationale: str = Field(min_length=1)
    scenario_role: Literal["floor", "ceiling", "mixed"] | None = None
    baseline_yn: bool = False


class V4ExcludedScenarioCandidate(ApiModel):
    pressure_band: PressureBand
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    dimension_values: dict[str, str]


class V4ScenarioSynthesisResult(ApiModel):
    model_config = ConfigDict(extra="forbid")

    group_title: str = Field(min_length=1)
    group_description: str = Field(min_length=1)
    scenarios: list[V4ScenarioCandidateDraft] = Field(min_length=3, max_length=5)
    excluded_scenarios: list[V4ExcludedScenarioCandidate] = Field(default_factory=list)


class V4ReadableDimensionChoice(ApiModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(max_length=30)
    states: list[str] = Field(
        min_length=1,
        max_length=2,
        description=(
            "각 항목은 정확히 lever|direction|level|scope|timeWindow 형식이며 direction은 "
            "increase, decrease, disrupt, recover, unchanged 중 하나. 첫 번째 lever는 Dimension source Lever이고 "
            "동일 Choice 안에서 Lever code는 중복할 수 없음"
        ),
    )
    pressure: Literal["bullish", "balanced", "bearish"]
    why: str = Field(
        min_length=10,
        max_length=240,
        description=(
            "제공된 관측 사실을 기반으로 Choice의 미래 상태와 JKM 영향을 바로 연결하고 문장 끝의 '가정'으로만 "
            "불확실성을 표시하는 간결한 한국어 문장. 가정 의미를 반복하거나 Choice를 답·응답·선택으로 표현하지 않음"
        ),
    )


class V4ReadableDimension(ApiModel):
    model_config = ConfigDict(extra="forbid")

    source_questions: list[str] = Field(alias="from", min_length=1)
    label: str = Field(max_length=30)
    question: str
    rationale: str = Field(
        max_length=200,
        description=(
            "question의 관측 시점·수치·시장 신호·대상·영향 경로를 빠짐없이 유지하고 질문 어미만 "
            "'...하는지에 따라' 형태로 바꿔, 왜 이 Dimension이 Scenario와 JKM 결과를 구분하는지 설명하는 "
            "구체적인 한국어 근거 문장"
        ),
    )
    lever: str = Field(min_length=1)
    axis: UncertaintyAxis
    unit: str | None = None
    choices: list[V4ReadableDimensionChoice] = Field(min_length=2, max_length=4)

    @model_validator(mode="before")
    @classmethod
    def discard_legacy_format(cls, value: Any) -> Any:
        """Accept cached relaxed-schema responses without retaining LLM-owned format metadata."""
        if not isinstance(value, dict):
            return value
        normalized = dict(value)
        normalized.pop("format", None)
        normalized.pop("value_format", None)
        return normalized


class V4ReadableDimensionDesignDraft(ApiModel):
    """Decision questions and choices without server-owned lineage fields."""

    model_config = ConfigDict(extra="forbid")

    dimensions: list[V4ReadableDimension] = Field(min_length=3, max_length=6)
    not_used: list[str] = Field(alias="notUsed", default_factory=list)


class V4ReadableAdditionalDimensionDesignDraft(ApiModel):
    """Batch output for unused questions; an empty candidate list is valid."""

    model_config = ConfigDict(extra="forbid")

    dimensions: list[V4ReadableDimension] = Field(default_factory=list)


class V4ReadableScenario(ApiModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(max_length=40)
    narrative: str = Field(min_length=80, max_length=300)
    choices: list[str] = Field(min_length=3, max_length=6)
    interactions: list[str] = Field(default_factory=list, max_length=3)
    pressure: PressureBand
    explanation: str = Field(min_length=30, max_length=600)
    probability: float = Field(
        ge=0,
        le=100,
        description="0~100 정수 백분율이며 모든 Scenario probability의 합계는 100",
    )
    related_markets: list[str] = Field(default_factory=list, max_length=2)


class V4ReadableExcludedScenarioCandidate(ApiModel):
    model_config = ConfigDict(extra="forbid")

    pressure_band: PressureBand
    reason_code: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    choices: list[str] = Field(min_length=3, max_length=6)


class V4ReadableScenarioSynthesisDraft(ApiModel):
    """Scenario prose plus readable aliases selected from the rendered decision matrix."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        min_length=1,
        max_length=120,
        description="선택한 이벤트의 구체적인 대상·지역·지표·변화를 나타내는 시나리오 그룹 제목",
    )
    description: str = Field(
        min_length=1,
        max_length=600,
        description=(
            "첫 문장은 관측된 이벤트 사실을 직접 서술하고, 둘째 문장은 검증된 충격의 지속·전달·증폭과 "
            "대체·회복·상쇄를 중심으로 핵심 분기를 설명하는 두 문장. Dimension 이름을 나열하거나 독립 이벤트의 "
            "상호작용을 만들지 않으며 영문 Event/Scenario, '입력 사실', JKM은 사용하지 않음"
        ),
    )
    scenarios: list[V4ReadableScenario] = Field(min_length=3, max_length=5)
    excluded: list[V4ReadableExcludedScenarioCandidate] = Field(default_factory=list, max_length=2)


class V4GenerationResult(ApiModel):
    group_title: str = Field(min_length=1)
    group_summary: str = Field(min_length=1, max_length=300)
    group_description: str = Field(min_length=1)
    impact_analysis: V4EventImpactAnalysisResult
    dimension_definitions: list[V4DimensionDefinition] = Field(min_length=3, max_length=6)
    scenarios: list[V4ScenarioCandidate] = Field(min_length=3, max_length=5)
    excluded_scenarios: list[V4ExcludedScenarioCandidate] = Field(default_factory=list)
    excluded_dimensions: list[str] = Field(default_factory=list)
    validation_warnings: list[V4ValidationWarning] = Field(default_factory=list)


class ParameterCoverage(ApiModel):
    covered_dimension_ids: list[str]
    uncovered_dimension_ids: list[str]
    unsupported_lever_codes: list[str]
    unsupported_lever_details: list[ModelImpactLeverSupportIssue]
    coverage_status: Literal["full", "partial", "none"]


def _split_wire_token(value: str, *, size: int, label: str) -> list[str]:
    parts = [part.strip() for part in value.split("|")]
    if len(parts) != size or any(not part for part in parts):
        raise ValueError(f"{label} must contain {size} non-empty pipe-separated values")
    return parts


def _parse_lever_step(value: str) -> V4LeverStepDraft:
    code, role, direction, scope, timing = _split_wire_token(value, size=5, label="lever state")
    if role not in {"primary", "driver", "transmission"}:
        raise ValueError(f"invalid lever role: {role}")
    try:
        state_direction = StateDirection(direction)
    except ValueError as exc:
        raise ValueError(f"invalid lever direction: {direction}") from exc
    return V4LeverStepDraft(
        lever_code=code,
        path_role=role,
        state_direction=state_direction,
        scope=scope,
        timing=timing,
    )


def _parse_balance_effect(value: str, *, rationale: str) -> V4BalanceEffect | None:
    if value.strip() == "none":
        return None
    domain, direction = _split_wire_token(value, size=2, label="balance")
    if domain not in {"demand", "supply", "trade"}:
        raise ValueError(f"invalid balance domain: {domain}")
    if direction not in {"increase", "decrease", "mixed", "unchanged"}:
        raise ValueError(f"invalid balance direction: {direction}")
    return V4BalanceEffect(domain=domain, direction=direction, rationale=rationale)


def expand_v4_readable_event_analysis(
    readable: V4ReadableEventAnalysisDraft,
    *,
    event_id: int,
    observed_at: str | None,
    fact_candidates: dict[str, str],
    open_question_limit: int | None = None,
) -> V4EventImpactAnalysisDraft:
    """Validate natural-language Fact selection and hydrate server-owned v4 lineage."""
    candidates_by_text = {text: (ref, text) for ref, text in fact_candidates.items()}
    selected: list[tuple[str, str]] = []
    selected_keys: set[str] = set()
    for statement in readable.event_facts:
        key = statement
        candidate = candidates_by_text.get(key)
        if candidate is None:
            raise ValueError(f"Event analysis returned a Fact outside the provided candidates: {statement!r}")
        if key in selected_keys:
            raise ValueError("Event analysis contains duplicate Fact sentences")
        selected_keys.add(key)
        selected.append(candidate)

    fact_id_by_text = {text: f"e{event_id}_f{index}" for index, (_ref, text) in enumerate(selected, start=1)}
    facts = [
        V4EventFact(
            fact_id=fact_id_by_text[text],
            event_id=event_id,
            observed_basis=text,
            observed_at=observed_at or None,
        )
        for _ref, text in selected
    ]
    reason_type: Literal["no_usable_fact", "no_material_impact"] | None = None
    if readable.excluded_because:
        reason_type = "no_material_impact" if readable.event_facts else "no_usable_fact"
    exclusions = (
        [
            V4EventAnalysisExclusion(
                event_id=event_id,
                reason_type=reason_type,
                reason=readable.excluded_because,
            ),
        ]
        if readable.excluded_because is not None and reason_type is not None
        else []
    )

    paths: list[V4EventImpactPathDraft] = []
    used_fact_ids: set[str] = set()
    path_id_by_number: dict[int, str] = {}
    for index, path in enumerate(readable.impacts, start=1):
        evidence_keys = list(path.evidence)
        if len(evidence_keys) != len(set(evidence_keys)):
            raise ValueError(f"Impact {index} contains duplicate evidence sentences")
        unknown_evidence = [statement for statement in path.evidence if statement not in fact_id_by_text]
        if unknown_evidence:
            raise ValueError(f"Impact {index} references unselected Event facts: {unknown_evidence}")
        source_fact_ids = [fact_id_by_text[key] for key in evidence_keys]
        used_fact_ids.update(source_fact_ids)
        path_id = f"e{event_id}_p{index}"
        path_id_by_number[index] = path_id
        paths.append(
            V4EventImpactPathDraft(
                impact_path_id=path_id,
                event_id=event_id,
                source_fact_ids=source_fact_ids,
                mechanism=path.analysis,
                lever_steps=[_parse_lever_step(item) for item in path.lever_states],
                balance_effect=_parse_balance_effect(path.balance, rationale=path.analysis),
                materiality=path.importance,
            ),
        )
    if paths and used_fact_ids != {fact.fact_id for fact in facts}:
        raise ValueError("every selected Event Fact must support at least one Impact")

    retained_questions = (
        readable.open_questions[:open_question_limit] if open_question_limit is not None else readable.open_questions
    )
    removed_question_count = len(readable.open_questions) - len(retained_questions)
    uncertainties: list[V4PathUncertainty] = []
    for index, question in enumerate(retained_questions, start=1):
        path_id = path_id_by_number.get(question.impact)
        if path_id is None:
            raise ValueError(f"open question {index} references an unknown Impact number")
        referenced_path = paths[question.impact - 1]
        allowed_levers = [step.lever_code for step in referenced_path.lever_steps]
        if question.lever not in allowed_levers:
            raise ValueError(
                f"openQuestions[{index}].lever must be one of Impact {question.impact} Lever codes: {allowed_levers}",
            )
        uncertainties.append(
            V4PathUncertainty(
                uncertainty_id=f"e{event_id}_u{index}",
                impact_path_ids=[path_id],
                axis_type=question.axis,
                subject=question.question,
                affected_lever_code=question.lever,
                reason=question.question,
                materiality=referenced_path.materiality,
                semantic_key=f"{path_id}:{question.axis}:{question.lever}",
            ),
        )
    return V4EventImpactAnalysisDraft(
        event_facts=facts,
        decision_basis=readable.decision_basis,
        event_exclusions=exclusions,
        impact_paths=paths,
        path_uncertainties=uncertainties,
        validation_warnings=(
            [
                V4ValidationWarning(
                    stage="event_impact_analysis",
                    code="EVENT_OPEN_QUESTION_LIMIT_APPLIED",
                    message=(
                        f"Event {event_id} openQuestions 상한 {open_question_limit}개를 적용해 "
                        f"{removed_question_count}개를 제거했습니다."
                    ),
                    reference_ids=[str(event_id)],
                ),
            ]
            if removed_question_count
            else []
        ),
    )


def v4_analysis_result_to_draft(result: V4EventImpactAnalysisResult) -> V4EventImpactAnalysisDraft:
    """Remove server-hydrated IDs so the stable validator can re-check a merged analysis."""
    return V4EventImpactAnalysisDraft(
        event_facts=result.event_facts,
        decision_basis=result.decision_basis,
        event_exclusions=result.event_exclusions,
        impact_paths=[
            V4EventImpactPathDraft(
                **path.model_dump(exclude={"lever_steps"}),
                lever_steps=[
                    V4LeverStepDraft(**step.model_dump(exclude={"impact_lever_id"})) for step in path.lever_steps
                ],
            )
            for path in result.impact_paths
        ],
        path_uncertainties=result.path_uncertainties,
        interactions=result.interactions,
        interaction_uncertainties=result.interaction_uncertainties,
        validation_warnings=result.validation_warnings,
    )


def merge_v4_readable_interactions(
    impact_analysis: V4EventImpactAnalysisResult,
    readable: V4ReadableInteractionAnalysisDraft,
    *,
    event_count: int | None = None,
) -> V4EventImpactAnalysisDraft:
    """Validate, cap, and hydrate readable cross-Event decisions deterministically."""
    base = v4_analysis_result_to_draft(impact_analysis)
    path_by_id = {path.impact_path_id: path for path in impact_analysis.impact_paths}
    event_path_counts: dict[int, int] = defaultdict(int)
    path_id_by_alias: dict[str, str] = {}
    for path in impact_analysis.impact_paths:
        event_path_counts[path.event_id] += 1
        path_id_by_alias[f"E{path.event_id}-P{event_path_counts[path.event_id]}"] = path.impact_path_id

    questions_by_interaction: dict[int, list[V4ReadableInteractionQuestion]] = defaultdict(list)
    for question_index, question in enumerate(readable.open_questions, start=1):
        if question.interaction > len(readable.interactions):
            raise ValueError(f"Interaction open question {question_index} references an unknown Interaction number")
        questions_by_interaction[question.interaction].append(question)

    warnings = list(base.validation_warnings)
    cross_event_interactions: list[tuple[int, V4EventInteraction]] = []
    for index, interaction in enumerate(readable.interactions, start=1):
        if len(interaction.paths) != len(set(interaction.paths)):
            raise ValueError(f"Interaction {index} contains duplicate Path aliases")
        unknown_aliases = set(interaction.paths) - set(path_id_by_alias)
        if unknown_aliases:
            raise ValueError(f"Interaction {index} references unknown Path aliases: {sorted(unknown_aliases)}")
        path_ids = [path_id_by_alias[alias] for alias in interaction.paths]
        event_ids = sorted({path_by_id[path_id].event_id for path_id in path_ids})
        if len(event_ids) < 2:
            removed_question_count = len(questions_by_interaction[index])
            warnings.append(
                V4ValidationWarning(
                    stage="event_impact_analysis",
                    code="SAME_EVENT_INTERACTION_DROPPED",
                    message=(
                        f"원래 Interaction {index}가 Event {event_ids[0]} 내부 Path만 선택해 제거됐으며 "
                        f"연결 질문 {removed_question_count}개도 함께 제거했습니다."
                    ),
                    reference_ids=[str(index), str(event_ids[0]), *interaction.paths],
                ),
            )
            continue
        cross_event_interactions.append(
            (
                index,
                V4EventInteraction(
                    interaction_id=f"source_i{index}",
                    event_ids=event_ids,
                    impact_path_ids=path_ids,
                    relation=interaction.relation,
                    mechanism=interaction.analysis,
                ),
            ),
        )

    selected_event_count = event_count
    if selected_event_count is None:
        selected_event_ids = (
            {fact.event_id for fact in impact_analysis.event_facts}
            | {exclusion.event_id for exclusion in impact_analysis.event_exclusions}
            | {path.event_id for path in impact_analysis.impact_paths}
        )
        selected_event_count = len(selected_event_ids)
    interaction_limit = interaction_count_target(selected_event_count)[1]
    retained_sources = cross_event_interactions[:interaction_limit]
    removed_sources = cross_event_interactions[interaction_limit:]
    if removed_sources:
        removed_question_count = sum(len(questions_by_interaction[index]) for index, _item in removed_sources)
        warnings.append(
            V4ValidationWarning(
                stage="event_impact_analysis",
                code="INTERACTION_COUNT_LIMIT_APPLIED",
                message=(
                    f"Event {selected_event_count}개 Interaction 상한 {interaction_limit}개를 적용해 "
                    f"Interaction {len(removed_sources)}개와 연결 질문 {removed_question_count}개를 제거했습니다."
                ),
                reference_ids=[str(index) for index, _item in removed_sources],
            ),
        )

    interactions: list[V4EventInteraction] = []
    interaction_by_source_number: dict[int, V4EventInteraction] = {}
    for retained_index, (source_index, interaction) in enumerate(retained_sources, start=1):
        retained = interaction.model_copy(update={"interaction_id": f"i{retained_index}"})
        interactions.append(retained)
        interaction_by_source_number[source_index] = retained

    cross_event_by_source_number = dict(cross_event_interactions)
    candidate_questions: list[tuple[V4ReadableInteractionQuestion, V4EventInteraction]] = []
    removed_retained_question_count = 0
    seen_question_interactions: set[int] = set()
    for question_index, question in enumerate(readable.open_questions, start=1):
        source_interaction = cross_event_by_source_number.get(question.interaction)
        if source_interaction is None:
            continue
        if source_interaction.relation != "independent":
            allowed_levers = sorted(
                {
                    step.lever_code
                    for path_id in source_interaction.impact_path_ids
                    for step in path_by_id[path_id].lever_steps
                },
            )
            if question.lever not in allowed_levers:
                raise ValueError(
                    f"openQuestions[{question_index}].lever must be one of Interaction {question.interaction} "
                    f"Path Lever codes: {allowed_levers}",
                )
        retained_interaction = interaction_by_source_number.get(question.interaction)
        if retained_interaction is None:
            continue
        if source_interaction.relation == "independent" or question.interaction in seen_question_interactions:
            removed_retained_question_count += 1
            continue
        seen_question_interactions.add(question.interaction)
        candidate_questions.append((question, retained_interaction))

    question_budget = interaction_question_budget(
        retained_interaction_count=len(interactions),
        retained_event_question_count=len(impact_analysis.path_uncertainties),
    )
    retained_questions = candidate_questions[:question_budget]
    removed_retained_question_count += len(candidate_questions) - len(retained_questions)
    if removed_retained_question_count:
        warnings.append(
            V4ValidationWarning(
                stage="event_impact_analysis",
                code="INTERACTION_OPEN_QUESTION_LIMIT_APPLIED",
                message=(
                    f"Interaction별 최대 1개·전체 상한 {question_budget}개를 적용해 "
                    f"질문 {removed_retained_question_count}개를 제거했습니다."
                ),
                reference_ids=[interaction.interaction_id for _question, interaction in retained_questions],
            ),
        )

    uncertainties: list[V4InteractionUncertainty] = []
    for index, (question, interaction) in enumerate(retained_questions, start=1):
        uncertainties.append(
            V4InteractionUncertainty(
                uncertainty_id=f"iu{index}",
                interaction_id=interaction.interaction_id,
                impact_path_ids=interaction.impact_path_ids,
                axis_type=question.axis,
                subject=question.question,
                affected_lever_code=question.lever,
                reason=question.question,
                materiality="high",
                semantic_key=f"{interaction.interaction_id}:{question.axis}:{question.lever}",
            ),
        )
    return base.model_copy(
        update={
            "interactions": interactions,
            "interaction_uncertainties": uncertainties,
            "validation_warnings": warnings,
        },
    )


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def finalize_open_question_pool(
    analysis: V4EventImpactAnalysisResult,
    *,
    target_minimum: int = 7,
) -> V4EventImpactAnalysisResult:
    """Deduplicate the canonical uncertainty pool and warn on a soft-goal undershoot."""
    ordered: list[V4PathUncertainty | V4InteractionUncertainty] = []
    seen_semantic_keys: set[tuple[str, str, str]] = set()
    seen_questions: set[str] = set()
    for uncertainty in [*analysis.path_uncertainties, *analysis.interaction_uncertainties]:
        source_id = (
            uncertainty.interaction_id
            if isinstance(uncertainty, V4InteractionUncertainty)
            else "|".join(sorted(uncertainty.impact_path_ids))
        )
        semantic_key = (source_id, uncertainty.axis_type, uncertainty.affected_lever_code)
        question_key = _normalized(uncertainty.subject)
        if semantic_key in seen_semantic_keys or question_key in seen_questions:
            continue
        seen_semantic_keys.add(semantic_key)
        seen_questions.add(question_key)
        ordered.append(uncertainty)

    selected_ids = {item.uncertainty_id for item in ordered}
    warnings = list(analysis.validation_warnings)
    if len(ordered) < target_minimum and not any(
        warning.code == "OPEN_QUESTION_TARGET_UNDERSHOT" for warning in warnings
    ):
        warnings.append(
            V4ValidationWarning(
                stage="event_impact_analysis",
                code="OPEN_QUESTION_TARGET_UNDERSHOT",
                message=(f"의미 있는 open question이 soft goal {target_minimum}개보다 적은 {len(ordered)}개입니다."),
                reference_ids=[item.uncertainty_id for item in ordered],
            ),
        )
    return analysis.model_copy(
        update={
            "path_uncertainties": [item for item in analysis.path_uncertainties if item.uncertainty_id in selected_ids],
            "interaction_uncertainties": [
                item for item in analysis.interaction_uncertainties if item.uncertainty_id in selected_ids
            ],
            "validation_warnings": warnings,
        },
    )


def _unique_ids(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} ids must be unique")


def _catalog_by_code(impact_levers: list[ModelImpactLeverPayload]) -> dict[str, ModelImpactLeverPayload]:
    catalog_by_code = {lever.lever_code: lever for lever in impact_levers}
    if not catalog_by_code:
        raise ValueError("active model impact lever catalog is empty")
    return catalog_by_code


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
    if executable and not unsupported and not any(lever.domain == "price_only" for lever in levers):
        return "full"
    if executable:
        return "partial"
    return "none"


def _parse_dimension_state(value: str) -> V4LeverStateDraft:
    code, direction, level, scope, time_window = _split_wire_token(value, size=5, label="Dimension state")
    try:
        state_direction = StateDirection(direction)
    except ValueError as exc:
        raise ValueError(f"invalid Dimension state direction: {direction}") from exc
    return V4LeverStateDraft(
        lever_code=code,
        direction=state_direction,
        level=level,
        scope=scope,
        time_window=time_window,
    )


def _derive_dimension_value_kind(
    dimension: V4ReadableDimension,
) -> Literal["categorical", "numeric_range", "temporal"]:
    if dimension.axis in {"timing", "duration", "recovery"}:
        return "temporal"
    if dimension.unit and dimension.unit.strip():
        return "numeric_range"
    return "categorical"


def expand_v4_readable_dimension_design(
    readable: V4ReadableDimensionDesignDraft,
    *,
    impact_analysis: V4EventImpactAnalysisResult,
) -> V4DimensionDesignDraft:
    """Assign stable IDs and derive Path lineage from rendered uncertainty cards."""
    uncertainties = [*impact_analysis.path_uncertainties, *impact_analysis.interaction_uncertainties]
    uncertainty_by_alias = {f"U{index}": item for index, item in enumerate(uncertainties, start=1)}
    dimensions: list[V4DimensionDefinitionDraft] = []
    for dimension_index, dimension in enumerate(readable.dimensions, start=1):
        if len(dimension.source_questions) != len(set(dimension.source_questions)):
            raise ValueError(f"Dimension {dimension_index} contains duplicate source question aliases")
        unknown_aliases = set(dimension.source_questions) - set(uncertainty_by_alias)
        if unknown_aliases:
            raise ValueError(
                f"Dimension {dimension_index} references unknown question aliases: {sorted(unknown_aliases)}"
            )
        source_uncertainties = [uncertainty_by_alias[alias] for alias in dimension.source_questions]
        source_paths = list(
            dict.fromkeys(path_id for uncertainty in source_uncertainties for path_id in uncertainty.impact_path_ids)
        )
        dimension_id = f"d{dimension_index}"
        values = [
            V4DimensionValueDefinitionDraft(
                value_id=f"{dimension_id}_v{value_index}",
                label=choice.label,
                lever_states=[_parse_dimension_state(state) for state in choice.states],
                pressure_contribution=choice.pressure,
                assumption_rationale=choice.why,
            )
            for value_index, choice in enumerate(dimension.choices, start=1)
        ]
        dimensions.append(
            V4DimensionDefinitionDraft(
                dimension_id=dimension_id,
                label=dimension.label,
                description=dimension.question,
                rationale=dimension.rationale,
                source_impact_path_ids=source_paths,
                source_uncertainty_ids=[item.uncertainty_id for item in source_uncertainties],
                primary_lever_code=dimension.lever,
                dimension_type=dimension.axis,
                value_kind=_derive_dimension_value_kind(dimension),
                unit=dimension.unit,
                values=values,
            ),
        )
    return V4DimensionDesignDraft(
        dimension_definitions=dimensions,
        excluded_dimensions=readable.not_used,
    )


def expand_v4_additional_dimension_candidates(
    readable: V4ReadableAdditionalDimensionDesignDraft,
    *,
    impact_analysis: V4EventImpactAnalysisResult,
) -> list[V4DimensionDefinitionDraft]:
    """Hydrate readable candidates with deterministic IDs while preserving item validation boundaries."""
    uncertainties = [*impact_analysis.path_uncertainties, *impact_analysis.interaction_uncertainties]
    uncertainty_by_alias = {f"U{index}": item for index, item in enumerate(uncertainties, start=1)}
    candidates: list[V4DimensionDefinitionDraft] = []
    used_sources: set[str] = set()
    for dimension in readable.dimensions:
        try:
            if len(dimension.source_questions) != len(set(dimension.source_questions)):
                continue
            source_uncertainties = [uncertainty_by_alias[alias] for alias in dimension.source_questions]
        except KeyError:
            continue
        source_ids = [item.uncertainty_id for item in source_uncertainties]
        if used_sources.intersection(source_ids):
            continue
        stable_material = "|".join(sorted(source_ids))
        stable_material += f"|{dimension.lever}|{dimension.axis}"
        dimension_id = f"ad_{hashlib.sha256(stable_material.encode('utf-8')).hexdigest()[:12]}"
        source_paths = list(
            dict.fromkeys(path_id for uncertainty in source_uncertainties for path_id in uncertainty.impact_path_ids)
        )
        try:
            candidate = V4DimensionDefinitionDraft(
                dimension_id=dimension_id,
                label=dimension.label,
                description=dimension.question,
                rationale=dimension.rationale,
                source_impact_path_ids=source_paths,
                source_uncertainty_ids=source_ids,
                primary_lever_code=dimension.lever,
                dimension_type=dimension.axis,
                value_kind=_derive_dimension_value_kind(dimension),
                unit=dimension.unit,
                values=[
                    V4DimensionValueDefinitionDraft(
                        value_id=f"{dimension_id}_v{value_index}",
                        label=choice.label,
                        lever_states=[_parse_dimension_state(state) for state in choice.states],
                        pressure_contribution=choice.pressure,
                        assumption_rationale=choice.why,
                    )
                    for value_index, choice in enumerate(dimension.choices, start=1)
                ],
            )
        except ValueError:
            continue
        candidates.append(candidate)
        used_sources.update(source_ids)
    return candidates


def finalize_v4_additional_dimension_candidates(
    drafts: list[V4DimensionDefinitionDraft],
    *,
    impact_analysis: V4EventImpactAnalysisResult,
    impact_levers: list[ModelImpactLeverPayload],
) -> list[V4DimensionDefinition]:
    """Validate and hydrate candidates independently so one invalid item does not discard the batch."""
    candidates: list[V4DimensionDefinition] = []
    used_sources: set[str] = set()
    for draft in drafts:
        if used_sources.intersection(draft.source_uncertainty_ids):
            continue
        try:
            design = V4DimensionDesignDraft.model_construct(
                dimension_definitions=[draft],
                excluded_dimensions=[],
            )
            result = finalize_v4_dimension_design(
                design,
                impact_analysis=impact_analysis,
                impact_levers=impact_levers,
            )
        except ValueError:
            continue
        if not result.dimension_definitions:
            continue
        candidate = result.dimension_definitions[0]
        candidates.append(candidate)
        used_sources.update(candidate.source_uncertainty_ids)
    return candidates


def _parse_related_market(value: str) -> RelatedMarket:
    market, rationale = _split_wire_token(value, size=2, label="related market")
    return RelatedMarket(market=market, rationale=rationale)


def expand_v4_readable_scenario_synthesis(
    readable: V4ReadableScenarioSynthesisDraft,
    *,
    impact_analysis: V4EventImpactAnalysisResult,
    dimension_design: V4DimensionDesignResult,
) -> V4ScenarioSynthesisResult:
    """Hydrate Scenario choices and shared lineage from the rendered decision matrix."""
    interaction_by_alias = {
        f"I{index}": interaction.interaction_id
        for index, interaction in enumerate(impact_analysis.interactions, start=1)
    }
    interaction_by_id = {interaction.interaction_id: interaction for interaction in impact_analysis.interactions}
    choice_by_alias: dict[str, tuple[V4DimensionDefinition, V4DimensionValueDefinition]] = {}
    for dimension_index, dimension in enumerate(dimension_design.dimension_definitions, start=1):
        for value_index, value in enumerate(dimension.values, start=1):
            choice_by_alias[f"D{dimension_index}.V{value_index}"] = (dimension, value)

    scenarios: list[V4ScenarioCandidateDraft] = []
    common_path_ids = [path.impact_path_id for path in impact_analysis.impact_paths]
    for scenario_index, scenario in enumerate(readable.scenarios, start=1):
        if len(scenario.choices) != len(set(scenario.choices)):
            raise ValueError(f"Scenario {scenario_index} contains duplicate choice aliases")
        unknown_choices = set(scenario.choices) - set(choice_by_alias)
        if unknown_choices:
            raise ValueError(f"Scenario {scenario_index} references unknown choices: {sorted(unknown_choices)}")
        selected = [choice_by_alias[alias] for alias in scenario.choices]
        dimension_values = {dimension.dimension_id: value.value_id for dimension, value in selected}
        if len(dimension_values) != len(dimension_design.dimension_definitions):
            raise ValueError(f"Scenario {scenario_index} must select one Value for every Dimension")
        unknown_interactions = set(scenario.interactions) - set(interaction_by_alias)
        if unknown_interactions:
            raise ValueError(
                f"Scenario {scenario_index} references unknown Interactions: {sorted(unknown_interactions)}"
            )
        contributions = {value.pressure_contribution for _dimension, value in selected}
        applied_interaction_ids = [interaction_by_alias[alias] for alias in scenario.interactions]
        mixed_factors = (
            [value.label for _dimension, value in selected if value.pressure_contribution != "balanced"]
            if {"bullish", "bearish"} <= contributions
            else []
        )
        scenarios.append(
            V4ScenarioCandidateDraft(
                title=scenario.title,
                narrative=scenario.narrative,
                dimension_values=dimension_values,
                common_impact_path_ids=common_path_ids,
                applied_interaction_ids=applied_interaction_ids,
                pressure_band=scenario.pressure,
                pressure_breakdown=V4PressureBreakdown(
                    common_impact=" ".join(path.mechanism for path in impact_analysis.impact_paths),
                    value_delta=" ".join(
                        f"{dimension.label}: {value.assumption_rationale}" for dimension, value in selected
                    ),
                    interaction_effect=(
                        " ".join(interaction_by_id[item].mechanism for item in applied_interaction_ids)
                        or "적용된 Event Interaction이 없다."
                    ),
                ),
                related_markets=[_parse_related_market(item) for item in scenario.related_markets],
                probability_score=scenario.probability,
                mixed_factors=mixed_factors,
                explanation=scenario.explanation,
            ),
        )
    excluded_scenarios: list[V4ExcludedScenarioCandidate] = []
    for candidate_index, candidate in enumerate(readable.excluded, start=1):
        if len(candidate.choices) != len(set(candidate.choices)):
            raise ValueError(f"Excluded Scenario {candidate_index} contains duplicate choice aliases")
        unknown_choices = set(candidate.choices) - set(choice_by_alias)
        if unknown_choices:
            raise ValueError(
                f"Excluded Scenario {candidate_index} references unknown choices: {sorted(unknown_choices)}"
            )
        selected = [choice_by_alias[alias] for alias in candidate.choices]
        dimension_values = {dimension.dimension_id: value.value_id for dimension, value in selected}
        if len(dimension_values) != len(dimension_design.dimension_definitions):
            raise ValueError(f"Excluded Scenario {candidate_index} must select one Value for every Dimension")
        excluded_scenarios.append(
            V4ExcludedScenarioCandidate(
                pressure_band=candidate.pressure_band,
                reason_code=candidate.reason_code,
                reason=candidate.reason,
                dimension_values=dimension_values,
            ),
        )
    return V4ScenarioSynthesisResult(
        group_title=readable.title,
        group_description=readable.description,
        scenarios=scenarios,
        excluded_scenarios=excluded_scenarios,
    )


def finalize_v4_event_impact_analysis(
    draft: V4EventImpactAnalysisDraft,
    *,
    event_ids: list[int],
    impact_levers: list[ModelImpactLeverPayload],
) -> V4EventImpactAnalysisResult:
    catalog_by_code = _catalog_by_code(impact_levers)
    event_id_set = set(event_ids)
    if len(event_ids) != len(event_id_set):
        raise ValueError("input event ids must be unique")

    fact_ids = [fact.fact_id for fact in draft.event_facts]
    _unique_ids(fact_ids, "event fact")
    fact_by_id = {fact.fact_id: fact for fact in draft.event_facts}
    for fact in draft.event_facts:
        if fact.event_id not in event_id_set:
            raise ValueError(f"event fact {fact.fact_id} references an unknown event")

    exclusion_events = [exclusion.event_id for exclusion in draft.event_exclusions]
    if len(exclusion_events) != len(set(exclusion_events)):
        raise ValueError("each Event may have at most one analysis exclusion")
    if not set(exclusion_events).issubset(event_id_set):
        raise ValueError("event analysis exclusion references an unknown event")
    facts_by_event: dict[int, list[V4EventFact]] = defaultdict(list)
    for fact in draft.event_facts:
        facts_by_event[fact.event_id].append(fact)
    covered_events = set(facts_by_event) | set(exclusion_events)
    if covered_events != event_id_set:
        raise ValueError(f"Event impact analysis does not cover Events: {sorted(event_id_set - covered_events)}")

    path_ids = [path.impact_path_id for path in draft.impact_paths]
    _unique_ids(path_ids, "impact path")
    hydrated_paths: list[V4EventImpactPath] = []
    seen_path_signatures: set[tuple[object, ...]] = set()
    used_fact_ids: set[str] = set()
    paths_by_event: dict[int, list[V4EventImpactPath]] = defaultdict(list)
    for path in draft.impact_paths:
        if path.event_id not in event_id_set:
            raise ValueError(f"impact path {path.impact_path_id} references an unknown event")
        unknown_fact_ids = set(path.source_fact_ids) - set(fact_by_id)
        if unknown_fact_ids:
            raise ValueError(f"impact path {path.impact_path_id} references unknown facts: {sorted(unknown_fact_ids)}")
        if any(fact_by_id[fact_id].event_id != path.event_id for fact_id in path.source_fact_ids):
            raise ValueError(f"impact path {path.impact_path_id} references a Fact owned by another Event")

        hydrated_steps: list[V4LeverStep] = []
        for step in path.lever_steps:
            lever = catalog_by_code.get(step.lever_code)
            if lever is None:
                raise ValueError(f"impact path {path.impact_path_id} references unknown lever: {step.lever_code}")
            hydrated_steps.append(
                V4LeverStep(
                    **step.model_dump(),
                    impact_lever_id=lever.impact_lever_id,
                ),
            )
        lever_domains = [(step.lever_code, catalog_by_code[step.lever_code].domain) for step in path.lever_steps]
        non_price_domains = list(
            dict.fromkeys(domain for _lever_code, domain in lever_domains if domain != "price_only")
        )
        catalog_domain_summary = ", ".join(f"{lever_code}={domain}" for lever_code, domain in lever_domains)
        allowed_balances = " or ".join(f"{domain}|<direction>" for domain in non_price_domains)
        if non_price_domains and path.balance_effect is None:
            detail = f"{path.impact_path_id} balance cannot be none; {catalog_domain_summary}. Use {allowed_balances}."
            raise ValueError(detail)
        balance_effect = path.balance_effect if non_price_domains else None
        if balance_effect is not None and balance_effect.domain not in non_price_domains:
            detail = (
                f"{path.impact_path_id} balance domain {balance_effect.domain} does not match Lever domains; "
                f"{catalog_domain_summary}. Use {allowed_balances}."
            )
            raise ValueError(detail)

        signature = (
            path.event_id,
            tuple(sorted(path.source_fact_ids)),
            tuple(step.lever_code for step in path.lever_steps),
            _normalized(path.mechanism),
        )
        if signature in seen_path_signatures:
            raise ValueError(f"duplicate impact path mechanism: {path.impact_path_id}")
        seen_path_signatures.add(signature)
        used_fact_ids.update(path.source_fact_ids)
        hydrated = V4EventImpactPath.model_validate(
            {
                **path.model_dump(exclude={"lever_steps", "balance_effect"}),
                "lever_steps": [step.model_dump() for step in hydrated_steps],
                "balance_effect": balance_effect.model_dump() if balance_effect is not None else None,
            },
        )
        hydrated_paths.append(hydrated)
        paths_by_event[path.event_id].append(hydrated)

    exclusion_by_event = {exclusion.event_id: exclusion for exclusion in draft.event_exclusions}
    for fact in draft.event_facts:
        exclusion = exclusion_by_event.get(fact.event_id)
        if fact.fact_id not in used_fact_ids and (exclusion is None or exclusion.reason_type != "no_material_impact"):
            raise ValueError(f"unused Event Fact requires a no_material_impact Event exclusion: {fact.fact_id}")
    for event_id in event_ids:
        if facts_by_event.get(event_id) and not paths_by_event.get(event_id):
            exclusion = exclusion_by_event.get(event_id)
            if exclusion is None or exclusion.reason_type != "no_material_impact":
                raise ValueError(
                    f"Event {event_id} with usable Facts but no paths requires a no_material_impact exclusion"
                )
        if not facts_by_event.get(event_id):
            exclusion = exclusion_by_event.get(event_id)
            if exclusion is None or exclusion.reason_type != "no_usable_fact":
                raise ValueError(f"Event {event_id} without Facts requires noUsableFactReason")

    path_by_id = {path.impact_path_id: path for path in hydrated_paths}
    uncertainty_ids = [item.uncertainty_id for item in draft.path_uncertainties]
    uncertainty_ids.extend(item.uncertainty_id for item in draft.interaction_uncertainties)
    _unique_ids(uncertainty_ids, "uncertainty")
    for uncertainty in draft.path_uncertainties:
        unknown_path_ids = set(uncertainty.impact_path_ids) - set(path_by_id)
        if unknown_path_ids:
            raise ValueError(
                f"path uncertainty {uncertainty.uncertainty_id} references unknown paths: {sorted(unknown_path_ids)}",
            )
        lever_codes = {
            step.lever_code for path_id in uncertainty.impact_path_ids for step in path_by_id[path_id].lever_steps
        }
        if uncertainty.affected_lever_code not in lever_codes:
            raise ValueError(f"path uncertainty {uncertainty.uncertainty_id} affected Lever is not in its paths")

    interaction_ids = [interaction.interaction_id for interaction in draft.interactions]
    _unique_ids(interaction_ids, "interaction")
    interaction_by_id = {interaction.interaction_id: interaction for interaction in draft.interactions}
    for interaction in draft.interactions:
        unknown_path_ids = set(interaction.impact_path_ids) - set(path_by_id)
        if unknown_path_ids:
            raise ValueError(
                f"interaction {interaction.interaction_id} references unknown paths: {sorted(unknown_path_ids)}",
            )
        derived_event_ids = {path_by_id[path_id].event_id for path_id in interaction.impact_path_ids}
        if len(derived_event_ids) < 2:
            raise ValueError(f"interaction {interaction.interaction_id} must reference paths from different Events")
        if set(interaction.event_ids) != derived_event_ids:
            raise ValueError(f"interaction {interaction.interaction_id} eventIds do not match its paths")
    for uncertainty in draft.interaction_uncertainties:
        interaction = interaction_by_id.get(uncertainty.interaction_id)
        if interaction is None:
            raise ValueError(f"interaction uncertainty {uncertainty.uncertainty_id} references unknown interaction")
        if not set(uncertainty.impact_path_ids).issubset(interaction.impact_path_ids):
            raise ValueError(f"interaction uncertainty {uncertainty.uncertainty_id} references unrelated paths")
        lever_codes = {
            step.lever_code for path_id in uncertainty.impact_path_ids for step in path_by_id[path_id].lever_steps
        }
        if uncertainty.affected_lever_code not in lever_codes:
            raise ValueError(f"interaction uncertainty {uncertainty.uncertainty_id} affected Lever is not in its paths")

    return V4EventImpactAnalysisResult(
        event_facts=draft.event_facts,
        decision_basis=draft.decision_basis,
        event_exclusions=draft.event_exclusions,
        impact_paths=hydrated_paths,
        path_uncertainties=draft.path_uncertainties,
        interactions=draft.interactions,
        interaction_uncertainties=draft.interaction_uncertainties,
        validation_warnings=draft.validation_warnings,
    )


def finalize_v4_dimension_design(
    design: V4DimensionDesignDraft,
    *,
    impact_analysis: V4EventImpactAnalysisResult,
    impact_levers: list[ModelImpactLeverPayload],
) -> V4DimensionDesignResult:
    catalog_by_code = _catalog_by_code(impact_levers)
    path_by_id = {path.impact_path_id: path for path in impact_analysis.impact_paths}
    uncertainty_by_id = {
        item.uncertainty_id: item
        for item in [*impact_analysis.path_uncertainties, *impact_analysis.interaction_uncertainties]
    }
    dimension_ids = [dimension.dimension_id for dimension in design.dimension_definitions]
    _unique_ids(dimension_ids, "dimension")
    hydrated_definitions: list[V4DimensionDefinition] = []
    warnings: list[V4ValidationWarning] = []
    for dimension in design.dimension_definitions:
        unknown_path_ids = set(dimension.source_impact_path_ids) - set(path_by_id)
        if unknown_path_ids:
            raise ValueError(f"dimension {dimension.dimension_id} references unknown paths: {sorted(unknown_path_ids)}")
        unknown_uncertainty_ids = set(dimension.source_uncertainty_ids) - set(uncertainty_by_id)
        if unknown_uncertainty_ids:
            raise ValueError(
                f"dimension {dimension.dimension_id} references unknown uncertainties: "
                f"{sorted(unknown_uncertainty_ids)}",
            )
        source_uncertainties = [uncertainty_by_id[item] for item in dimension.source_uncertainty_ids]
        affected_levers = {item.affected_lever_code for item in source_uncertainties}
        if dimension.primary_lever_code not in affected_levers:
            raise ValueError(f"dimension {dimension.dimension_id} primary Lever is not inherited from its uncertainty")
        primary_lever = catalog_by_code.get(dimension.primary_lever_code)
        if primary_lever is None:
            raise ValueError(f"dimension {dimension.dimension_id} references unknown primary Lever")
        uncertainty_path_ids = {
            path_id for uncertainty in source_uncertainties for path_id in uncertainty.impact_path_ids
        }
        if not uncertainty_path_ids.issubset(dimension.source_impact_path_ids):
            raise ValueError(f"dimension {dimension.dimension_id} does not include all uncertainty source paths")
        source_path_lever_codes = {
            step.lever_code for path_id in dimension.source_impact_path_ids for step in path_by_id[path_id].lever_steps
        }
        source_event_ids = sorted({path_by_id[path_id].event_id for path_id in dimension.source_impact_path_ids})
        hydrated_values: list[V4DimensionValueDefinition] = []
        state_signatures: set[tuple[tuple[str, str, str, str, str], ...]] = set()
        referenced_lever_codes = {dimension.primary_lever_code}
        for value in dimension.values:
            hydrated_states: list[V4LeverState] = []
            value_lever_codes = [state.lever_code for state in value.lever_states]
            if len(value_lever_codes) != len(set(value_lever_codes)):
                raise ValueError(
                    f"dimension {dimension.dimension_id} value {value.value_id} has duplicate Lever states"
                )
            if dimension.primary_lever_code not in value_lever_codes:
                raise ValueError(f"dimension {dimension.dimension_id} value {value.value_id} omits the primary Lever")
            for state in value.lever_states:
                lever = catalog_by_code.get(state.lever_code)
                if lever is None:
                    raise ValueError(
                        f"dimension {dimension.dimension_id} value references unknown Lever: {state.lever_code}"
                    )
                if state.lever_code not in source_path_lever_codes:
                    raise ValueError(
                        f"dimension {dimension.dimension_id} value introduces a Lever outside its source paths"
                    )
                referenced_lever_codes.add(state.lever_code)
                hydrated_states.append(V4LeverState(**state.model_dump(), impact_lever_id=lever.impact_lever_id))
            signature = tuple(
                sorted(
                    (
                        state.lever_code,
                        state.direction,
                        _normalized(state.level),
                        _normalized(state.scope),
                        _normalized(state.time_window),
                    )
                    for state in value.lever_states
                ),
            )
            if signature in state_signatures:
                raise ValueError(f"dimension {dimension.dimension_id} contains overlapping duplicate Value states")
            state_signatures.add(signature)
            primary_state = next(
                state for state in value.lever_states if state.lever_code == dimension.primary_lever_code
            )
            expected_contribution: Literal["bullish", "bearish"] | None = None
            if primary_lever.domain == "demand":
                if primary_state.direction == StateDirection.INCREASE:
                    expected_contribution = "bullish"
                elif primary_state.direction == StateDirection.DECREASE:
                    expected_contribution = "bearish"
            elif primary_lever.domain == "supply":
                if primary_state.direction in {StateDirection.INCREASE, StateDirection.RECOVER}:
                    expected_contribution = "bearish"
                elif primary_state.direction in {StateDirection.DECREASE, StateDirection.DISRUPT}:
                    expected_contribution = "bullish"
            if expected_contribution is not None and value.pressure_contribution not in {
                expected_contribution,
                "balanced",
            }:
                if len(value.assumption_rationale.strip()) < 20:
                    raise ValueError(
                        f"dimension {dimension.dimension_id} value {value.value_id} requires a detailed "
                        "counter-directional pressure rationale",
                    )
                warnings.append(
                    V4ValidationWarning(
                        stage="dimension_design",
                        code="COUNTER_DIRECTIONAL_VALUE_PRESSURE",
                        message=(
                            f"Dimension {dimension.dimension_id} Value {value.value_id} uses "
                            f"{value.pressure_contribution} despite {primary_lever.domain} "
                            f"{primary_state.direction}; retained because a contextual rationale was provided."
                        ),
                        reference_ids=[dimension.dimension_id, value.value_id],
                    ),
                )
            hydrated_values.append(
                V4DimensionValueDefinition.model_validate(
                    {
                        **value.model_dump(exclude={"lever_states"}),
                        "lever_states": [state.model_dump() for state in hydrated_states],
                    },
                ),
            )
        hydrated_definitions.append(
            V4DimensionDefinition(
                **dimension.model_dump(exclude={"values"}),
                source_event_ids=source_event_ids,
                primary_impact_lever_id=primary_lever.impact_lever_id,
                model_support_status=_lever_support_status(sorted(referenced_lever_codes), catalog_by_code),
                values=hydrated_values,
            ),
        )
    return V4DimensionDesignResult(
        dimension_definitions=hydrated_definitions,
        excluded_dimensions=design.excluded_dimensions,
        validation_warnings=warnings,
    )


def _validate_scenarios(
    scenarios: list[V4ScenarioCandidate],
    excluded_scenarios: list[V4ExcludedScenarioCandidate],
    *,
    dimension_definitions: list[V4DimensionDefinition],
    impact_analysis: V4EventImpactAnalysisResult,
) -> None:
    dimension_by_id = {dimension.dimension_id: dimension for dimension in dimension_definitions}
    path_ids = {path.impact_path_id for path in impact_analysis.impact_paths}
    interaction_ids = {interaction.interaction_id for interaction in impact_analysis.interactions}
    combination_owners: dict[tuple[tuple[str, str], ...], str] = {}
    generated_bands: list[PressureBand] = []
    contribution_by_scenario: dict[int, list[int]] = {}
    scores = {"bullish": 1, "balanced": 0, "bearish": -1}
    for scenario_index, scenario in enumerate(scenarios):
        if set(scenario.dimension_values) != set(dimension_by_id):
            raise ValueError("every scenario must provide every dimension value")
        if set(scenario.common_impact_path_ids) != path_ids:
            raise ValueError("every Scenario must include all common Impact Paths")
        unknown_interaction_ids = set(scenario.applied_interaction_ids) - interaction_ids
        if unknown_interaction_ids:
            raise ValueError(f"Scenario references unknown interactions: {sorted(unknown_interaction_ids)}")
        contributions: list[int] = []
        for dimension_id, selected_value in scenario.dimension_values.items():
            dimension = dimension_by_id[dimension_id]
            selected_definition = next(
                (value for value in dimension.values if selected_value in {value.value_id, value.label}),
                None,
            )
            if selected_definition is None:
                raise ValueError(f"invalid value {selected_value!r} for dimension {dimension_id}")
            contributions.append(scores[selected_definition.pressure_contribution])
        combination = tuple(sorted(scenario.dimension_values.items()))
        scenario_reference = f"scenarios[{scenario_index}] ({scenario.title!r})"
        if previous_reference := combination_owners.get(combination):
            raise ValueError(
                f"{scenario_reference}.dimensionValues duplicates {previous_reference}.dimensionValues: "
                f"{dict(combination)}"
            )
        combination_owners[combination] = scenario_reference
        generated_bands.append(scenario.pressure_band)
        contribution_by_scenario[id(scenario)] = contributions
        if scenario.mixed_factors and not ({-1, 1} <= set(contributions)):
            raise ValueError(f"mixedFactors requires bullish and bearish dimension contributions: {scenario.title}")

    if len(set(generated_bands)) != len(generated_bands):
        raise ValueError("generated scenarios must use distinct pressure bands")
    excluded_bands = [scenario.pressure_band for scenario in excluded_scenarios]
    if set(generated_bands) & set(excluded_bands):
        raise ValueError("generated and excluded pressure bands must not overlap")
    if set(generated_bands + excluded_bands) != set(PRESSURE_BANDS):
        raise ValueError("generated and excluded scenarios must cover all pressure bands")
    for scenario_index, scenario in enumerate(excluded_scenarios):
        if set(scenario.dimension_values) != set(dimension_by_id):
            raise ValueError("every excluded Scenario must provide every dimension value")
        for dimension_id, selected_value in scenario.dimension_values.items():
            dimension = dimension_by_id[dimension_id]
            if not any(selected_value == value.value_id for value in dimension.values):
                raise ValueError(f"invalid excluded value {selected_value!r} for dimension {dimension_id}")
        combination = tuple(sorted(scenario.dimension_values.items()))
        scenario_reference = f"excludedScenarios[{scenario_index}]"
        if previous_reference := combination_owners.get(combination):
            raise ValueError(
                f"{scenario_reference}.dimensionValues duplicates {previous_reference}.dimensionValues: "
                f"{dict(combination)}"
            )
        combination_owners[combination] = scenario_reference
    ordered = sorted(scenarios, key=lambda scenario: PRESSURE_RANK[scenario.pressure_band])
    pressure_scores = [sum(contribution_by_scenario[id(scenario)]) for scenario in ordered]
    if ordered[0].pressure_band == "strong_bearish" and pressure_scores[0] >= 0:
        raise ValueError("strong_bearish Scenario requires a negative aggregate pressure score")
    if ordered[-1].pressure_band == "strong_bullish" and pressure_scores[-1] <= 0:
        raise ValueError("strong_bullish Scenario requires a positive aggregate pressure score")
    if any(lower > higher for lower, higher in zip(pressure_scores, pressure_scores[1:], strict=False)):
        raise ValueError("v4 Scenario pressure bands contradict aggregate dimension contributions")

    for scenario in scenarios:
        scenario.scenario_role = None
        scenario.baseline_yn = False
    ordered[0].scenario_role = "floor"
    ordered[-1].scenario_role = "ceiling"
    mixed_candidates = [
        scenario for scenario in ordered[1:-1] if {-1, 1} <= set(contribution_by_scenario[id(scenario)])
    ]
    if mixed_candidates:
        min(
            mixed_candidates,
            key=lambda scenario: (
                abs(PRESSURE_RANK[scenario.pressure_band] - 2),
                -scenario.probability_score,
            ),
        ).scenario_role = "mixed"
    max(scenarios, key=lambda scenario: scenario.probability_score).baseline_yn = True

    # Base는 확률 최고로 선정된 뒤에도 LLM이 매긴 절대 pressure_band를 그대로 유지했다.
    # 그 결과 Base가 bearish/bullish/strong_* 로 동시에 라벨링되는 사례가 실제 운영 데이터에서 확인됐다.
    # Base 선정 이후에는 band를 LLM의 자유 라벨이 아니라 "Base 대비 contribution 합산 차이"로
    # 서버가 결정적으로 재계산한다. Base 자신은 자기 자신과의 차이이므로 항상 0이 되어
    # 정의상 balanced가 되고, 다른 어떤 band와도 동시에 라벨링될 수 없다.
    base_scenario = next(scenario for scenario in scenarios if scenario.baseline_yn)
    base_sum = sum(contribution_by_scenario[id(base_scenario)])
    deltas = {
        id(scenario): sum(contribution_by_scenario[id(scenario)]) - base_sum for scenario in scenarios
    }
    for scenario in scenarios:
        delta = deltas[id(scenario)]
        if delta == 0:
            scenario.pressure_band = "balanced"
        elif delta >= 2:
            scenario.pressure_band = "strong_bullish"
        elif delta > 0:
            scenario.pressure_band = "bullish"
        elif delta <= -2:
            scenario.pressure_band = "strong_bearish"
        else:
            scenario.pressure_band = "bearish"

    # strong band가 겹치면(동일 임계값을 여러 시나리오가 동시에 넘으면), Base 대비 편차의 절댓값이
    # 가장 큰 시나리오만 strong을 유지하고 나머지는 같은 방향의 완화된 band로 내린다(상대적 극단성 순서는 보존).
    for strong_band, moderate_band in (("strong_bullish", "bullish"), ("strong_bearish", "bearish")):
        holders = [scenario for scenario in scenarios if scenario.pressure_band == strong_band]
        if len(holders) > 1:
            holders.sort(key=lambda scenario: abs(deltas[id(scenario)]), reverse=True)
            for demoted in holders[1:]:
                demoted.pressure_band = moderate_band

    # 안전망: 위 완화 로직으로도 band 중복이 해소되지 않으면(예: 같은 방향에 3개 이상 몰린 경우)
    # 에러를 발생시켜 기존 재시도 메커니즘이 다른 조합을 다시 생성하도록 한다.
    non_base_bands = [scenario.pressure_band for scenario in scenarios if not scenario.baseline_yn]
    if len(set(non_base_bands)) != len(non_base_bands):
        raise ValueError(
            "Base 재계산 이후에도 Base가 아닌 시나리오의 pressure_band가 서로 겹칩니다: "
            f"{non_base_bands}"
        )

    scenarios.sort(key=lambda scenario: PRESSURE_RANK[scenario.pressure_band], reverse=True)


def _normalize_v4_probability_scores(scenarios: list[V4ScenarioCandidate]) -> None:
    """v4 Scenario 가중치를 합계 100인 정수 백분율 점수로 정규화한다."""
    if not scenarios:
        return

    scores = [Decimal(str(scenario.probability_score)) for scenario in scenarios]
    total = sum(scores)
    if total <= 0:
        scores = [Decimal(1)] * len(scenarios)
        total = Decimal(len(scenarios))

    exact_scores = [score * Decimal(100) / total for score in scores]
    normalized_scores = [int(score.to_integral_value(rounding=ROUND_FLOOR)) for score in exact_scores]
    deficit = 100 - sum(normalized_scores)
    remainder_order = sorted(
        range(len(scenarios)),
        key=lambda index: (-(exact_scores[index] - normalized_scores[index]), index),
    )
    for index in remainder_order[:deficit]:
        normalized_scores[index] += 1

    for scenario, probability_score in zip(scenarios, normalized_scores, strict=True):
        scenario.probability_score = probability_score


def finalize_v4_generation_result(
    synthesis: V4ScenarioSynthesisResult,
    *,
    group_summary: str,
    impact_analysis: V4EventImpactAnalysisResult,
    dimension_design: V4DimensionDesignResult,
    impact_levers: list[ModelImpactLeverPayload],
) -> tuple[V4GenerationResult, ParameterCoverage]:
    finalized_scenarios = [
        V4ScenarioCandidate(
            **scenario.model_dump(),
            pressure_rationale=scenario.explanation,
        )
        for scenario in synthesis.scenarios
    ]
    _normalize_v4_probability_scores(finalized_scenarios)
    _validate_scenarios(
        finalized_scenarios,
        synthesis.excluded_scenarios,
        dimension_definitions=dimension_design.dimension_definitions,
        impact_analysis=impact_analysis,
    )
    result = V4GenerationResult(
        group_title=synthesis.group_title,
        group_summary=group_summary,
        group_description=synthesis.group_description,
        impact_analysis=impact_analysis,
        dimension_definitions=dimension_design.dimension_definitions,
        scenarios=finalized_scenarios,
        excluded_scenarios=synthesis.excluded_scenarios,
        excluded_dimensions=dimension_design.excluded_dimensions,
        validation_warnings=[
            *impact_analysis.validation_warnings,
            *dimension_design.validation_warnings,
        ],
    )
    catalog_by_code = _catalog_by_code(impact_levers)
    return result, build_parameter_coverage(result, catalog_by_code)


def _lever_support_issues(lever: ModelImpactLeverPayload) -> list[ModelImpactLeverSupportIssue]:
    if lever.domain == "price_only":
        return [ModelImpactLeverSupportIssue(lever_code=lever.lever_code, reason_code="PRICE_ONLY")]
    if not lever.parameter_bindings:
        return [ModelImpactLeverSupportIssue(lever_code=lever.lever_code, reason_code="NO_PARAMETER_BINDING")]
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
    referenced_lever_codes: set[str] = set()
    for dimension in result.dimension_definitions:
        if dimension.model_support_status == "full":
            covered.append(dimension.dimension_id)
        elif dimension.model_support_status == "partial":
            covered.append(dimension.dimension_id)
            uncovered.append(dimension.dimension_id)
        else:
            uncovered.append(dimension.dimension_id)
        referenced_lever_codes.add(dimension.primary_lever_code)
        referenced_lever_codes.update(state.lever_code for value in dimension.values for state in value.lever_states)
    unsupported_details = [
        issue
        for lever_code in sorted(referenced_lever_codes)
        for issue in _lever_support_issues(catalog_by_code[lever_code])
    ]
    if covered and not uncovered:
        status: Literal["full", "partial", "none"] = "full"
    elif covered:
        status = "partial"
    else:
        status = "none"
    return ParameterCoverage(
        covered_dimension_ids=covered,
        uncovered_dimension_ids=uncovered,
        unsupported_lever_codes=sorted({detail.lever_code for detail in unsupported_details}),
        unsupported_lever_details=unsupported_details,
        coverage_status=status,
    )


__all__ = [
    "ParameterCoverage",
    "V4DimensionDefinition",
    "V4DimensionDefinitionDraft",
    "V4DimensionDesignDraft",
    "V4DimensionDesignResult",
    "V4DimensionValueDefinition",
    "V4DimensionValueDefinitionDraft",
    "V4EventImpactAnalysisDraft",
    "V4EventImpactAnalysisResult",
    "V4EventImpactPath",
    "V4EventImpactPathDraft",
    "V4ExcludedScenarioCandidate",
    "V4GenerationResult",
    "V4InteractionUncertainty",
    "V4LeverState",
    "V4LeverStateDraft",
    "V4PathUncertainty",
    "V4ReadableDimensionDesignDraft",
    "V4ReadableEventAnalysisDraft",
    "V4ReadableInteractionAnalysisDraft",
    "V4ReadableScenarioSynthesisDraft",
    "V4ScenarioCandidate",
    "V4ScenarioCandidateDraft",
    "V4ScenarioSynthesisResult",
    "V4ValidationWarning",
    "build_parameter_coverage",
    "expand_v4_readable_dimension_design",
    "expand_v4_readable_event_analysis",
    "expand_v4_readable_scenario_synthesis",
    "finalize_v4_dimension_design",
    "finalize_v4_event_impact_analysis",
    "finalize_v4_generation_result",
    "merge_v4_readable_interactions",
    "v4_analysis_result_to_draft",
]
