from __future__ import annotations

# ruff: noqa: ANN401, CPY001
from collections.abc import Mapping, Sequence
from typing import Any, Literal

from pydantic import BaseModel, Field

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_enums import StateDirection
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDefinition,
    V4EventImpactAnalysisResult,
    V4InteractionUncertainty,
    V4PathUncertainty,
    V4ReadableAdditionalDimensionDesignDraft,
    V4ReadableDimension,
    expand_v4_additional_dimension_candidates,
    finalize_v4_additional_dimension_candidates,
)
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload


AdditionalDimensionRejectionReason = Literal[
    "UNKNOWN_SOURCE_ALIAS",
    "DUPLICATE_SOURCE_USE",
    "INVALID_STATE_FORMAT",
    "LEVER_LINEAGE_ERROR",
    "DUPLICATE_VALUE",
    "INSUFFICIENT_PRESSURE_COVERAGE",
]


class AdditionalDimensionCandidateRejection(BaseModel):
    candidate_index: int = Field(ge=1)
    source_aliases: list[str] = Field(default_factory=list)
    reason_code: AdditionalDimensionRejectionReason
    detail: str


class AdditionalDimensionHydrationResult(BaseModel):
    input_candidate_count: int = Field(ge=0)
    valid_candidates: list[V4DimensionDefinition] = Field(default_factory=list)
    rejected_candidates: list[AdditionalDimensionCandidateRejection] = Field(default_factory=list)

    @property
    def rejection_reason_codes(self) -> list[str]:
        return list(dict.fromkeys(item.reason_code for item in self.rejected_candidates))


def _field(payload: Mapping[str, Any], snake_key: str, camel_key: str) -> Any:
    return payload.get(snake_key, payload.get(camel_key))


def selected_source_uncertainty_ids(dimension_definitions: Sequence[Mapping[str, Any]]) -> set[str]:
    return {
        str(source_id)
        for definition in dimension_definitions
        for source_id in (_field(definition, "source_uncertainty_ids", "sourceUncertaintyIds") or [])
    }


def build_unused_impact_analysis(
    diagnostics: Mapping[str, Any],
    dimension_definitions: Sequence[Mapping[str, Any]],
) -> V4EventImpactAnalysisResult:
    used_ids = selected_source_uncertainty_ids(dimension_definitions)
    path_uncertainties = [
        item
        for item in (_field(diagnostics, "path_uncertainties", "pathUncertainties") or [])
        if isinstance(item, Mapping) and str(_field(item, "uncertainty_id", "uncertaintyId") or "") not in used_ids
    ]
    interaction_uncertainties = [
        item
        for item in (_field(diagnostics, "interaction_uncertainties", "interactionUncertainties") or [])
        if isinstance(item, Mapping) and str(_field(item, "uncertainty_id", "uncertaintyId") or "") not in used_ids
    ]
    return V4EventImpactAnalysisResult.model_validate(
        {
            "event_facts": _field(diagnostics, "event_facts", "eventFacts") or [],
            "forecast_claims": _field(diagnostics, "forecast_claims", "forecastClaims") or [],
            "decision_basis": _field(diagnostics, "decision_basis", "decisionBasis") or [],
            "event_exclusions": _field(diagnostics, "event_exclusions", "eventExclusions") or [],
            "impact_paths": _field(diagnostics, "impact_paths", "impactPaths") or [],
            "path_uncertainties": path_uncertainties,
            "interactions": _field(diagnostics, "event_interactions", "eventInteractions") or [],
            "interaction_uncertainties": interaction_uncertainties,
            "validation_warnings": _field(diagnostics, "validation_warnings", "validationWarnings") or [],
        },
    )


def hydrate_additional_dimension_candidates(
    readable: V4ReadableAdditionalDimensionDesignDraft,
    *,
    impact_analysis: V4EventImpactAnalysisResult,
    impact_levers: list[ModelImpactLeverPayload],
) -> AdditionalDimensionHydrationResult:
    uncertainties = [*impact_analysis.path_uncertainties, *impact_analysis.interaction_uncertainties]
    uncertainty_by_alias = {f"U{index}": item for index, item in enumerate(uncertainties, start=1)}
    valid_candidates: list[V4DimensionDefinition] = []
    rejected_candidates: list[AdditionalDimensionCandidateRejection] = []
    used_source_ids: set[str] = set()

    for candidate_index, dimension in enumerate(readable.dimensions, start=1):
        source_aliases = list(dimension.source_questions)
        rejection = _prevalidate_additional_dimension_candidate(
            dimension,
            candidate_index=candidate_index,
            source_aliases=source_aliases,
            uncertainty_by_alias=uncertainty_by_alias,
            used_source_ids=used_source_ids,
        )
        if rejection is not None:
            rejected_candidates.append(rejection)
            continue

        source_ids = [uncertainty_by_alias[alias].uncertainty_id for alias in source_aliases]
        try:
            single_readable = V4ReadableAdditionalDimensionDesignDraft(dimensions=[dimension])
            drafts = expand_v4_additional_dimension_candidates(
                single_readable,
                impact_analysis=impact_analysis,
            )
            candidates = finalize_v4_additional_dimension_candidates(
                drafts,
                impact_analysis=impact_analysis,
                impact_levers=impact_levers,
            )
        except ValueError as exc:
            rejected_candidates.append(
                AdditionalDimensionCandidateRejection(
                    candidate_index=candidate_index,
                    source_aliases=source_aliases,
                    reason_code=_classify_candidate_validation_error(exc),
                    detail=str(exc)[:400],
                ),
            )
            continue
        if len(candidates) != 1:
            rejected_candidates.append(
                _candidate_rejection(
                    candidate_index,
                    source_aliases,
                    "LEVER_LINEAGE_ERROR",
                    "candidate did not produce one hydrated Dimension",
                ),
            )
            continue

        valid_candidates.append(candidates[0])
        used_source_ids.update(source_ids)

    return AdditionalDimensionHydrationResult(
        input_candidate_count=len(readable.dimensions),
        valid_candidates=valid_candidates,
        rejected_candidates=rejected_candidates,
    )


def _prevalidate_additional_dimension_candidate(  # noqa: C901
    dimension: V4ReadableDimension,
    *,
    candidate_index: int,
    source_aliases: list[str],
    uncertainty_by_alias: Mapping[str, V4PathUncertainty | V4InteractionUncertainty],
    used_source_ids: set[str],
) -> AdditionalDimensionCandidateRejection | None:
    if len(source_aliases) != len(set(source_aliases)):
        return _candidate_rejection(
            candidate_index,
            source_aliases,
            "DUPLICATE_SOURCE_USE",
            "candidate repeats a source question alias",
        )
    unknown_aliases = sorted(set(source_aliases) - set(uncertainty_by_alias))
    if unknown_aliases:
        return _candidate_rejection(
            candidate_index,
            source_aliases,
            "UNKNOWN_SOURCE_ALIAS",
            f"unknown source question aliases: {unknown_aliases}",
        )
    source_ids = [str(uncertainty_by_alias[alias].uncertainty_id) for alias in source_aliases]
    duplicate_source_ids = sorted(set(source_ids).intersection(used_source_ids))
    if duplicate_source_ids:
        return _candidate_rejection(
            candidate_index,
            source_aliases,
            "DUPLICATE_SOURCE_USE",
            f"source questions already used by a valid candidate: {duplicate_source_ids}",
        )

    affected_levers = {str(uncertainty_by_alias[alias].affected_lever_code) for alias in source_aliases}
    if dimension.lever not in affected_levers:
        return _candidate_rejection(
            candidate_index,
            source_aliases,
            "LEVER_LINEAGE_ERROR",
            "Dimension source Lever is not inherited from its source question",
        )

    value_labels: set[str] = set()
    value_signatures: set[tuple[tuple[str, str, str, str, str], ...]] = set()
    for choice_index, choice in enumerate(dimension.choices, start=1):
        normalized_label = " ".join(choice.label.split()).casefold()
        if normalized_label in value_labels:
            return _candidate_rejection(
                candidate_index,
                source_aliases,
                "DUPLICATE_VALUE",
                f"Choice {choice_index} repeats another Value label",
            )
        value_labels.add(normalized_label)

        parsed_states: list[tuple[str, str, str, str, str]] = []
        for state_index, state in enumerate(choice.states, start=1):
            parts = tuple(part.strip() for part in state.split("|"))
            if len(parts) != 5 or any(not part for part in parts):
                return _candidate_rejection(
                    candidate_index,
                    source_aliases,
                    "INVALID_STATE_FORMAT",
                    f"Choice {choice_index} state {state_index} must use lever|direction|level|scope|timeWindow",
                )
            try:
                StateDirection(parts[1])
            except ValueError:
                return _candidate_rejection(
                    candidate_index,
                    source_aliases,
                    "INVALID_STATE_FORMAT",
                    f"Choice {choice_index} state {state_index} has invalid direction: {parts[1]}",
                )
            parsed_states.append(parts)

        state_levers = [parts[0] for parts in parsed_states]
        if state_levers[0] != dimension.lever:
            return _candidate_rejection(
                candidate_index,
                source_aliases,
                "LEVER_LINEAGE_ERROR",
                f"Choice {choice_index} first state must use source Lever {dimension.lever}",
            )
        if len(state_levers) != len(set(state_levers)):
            return _candidate_rejection(
                candidate_index,
                source_aliases,
                "LEVER_LINEAGE_ERROR",
                f"Choice {choice_index} repeats a Lever code",
            )
        signature = tuple(sorted(parsed_states))
        if signature in value_signatures:
            return _candidate_rejection(
                candidate_index,
                source_aliases,
                "DUPLICATE_VALUE",
                f"Choice {choice_index} repeats another Value state",
            )
        value_signatures.add(signature)

    contributions = {choice.pressure for choice in dimension.choices}
    required_contributions = (
        {"bearish", "bullish"} if len(dimension.choices) == 2 else {"bearish", "balanced", "bullish"}
    )
    missing_contributions = sorted(required_contributions - contributions)
    if missing_contributions:
        return _candidate_rejection(
            candidate_index,
            source_aliases,
            "INSUFFICIENT_PRESSURE_COVERAGE",
            f"{len(dimension.choices)} Choices must cover {sorted(required_contributions)}; "
            f"missing {missing_contributions}",
        )
    return None


def _candidate_rejection(
    candidate_index: int,
    source_aliases: list[str],
    reason_code: AdditionalDimensionRejectionReason,
    detail: str,
) -> AdditionalDimensionCandidateRejection:
    return AdditionalDimensionCandidateRejection(
        candidate_index=candidate_index,
        source_aliases=source_aliases,
        reason_code=reason_code,
        detail=detail,
    )


def _classify_candidate_validation_error(exc: ValueError) -> AdditionalDimensionRejectionReason:
    detail = str(exc).lower()
    if "duplicate value" in detail or "overlapping duplicate value states" in detail:
        return "DUPLICATE_VALUE"
    if "dimension state" in detail or "wire token" in detail:
        return "INVALID_STATE_FORMAT"
    return "LEVER_LINEAGE_ERROR"


def filter_available_candidates(
    candidates: Sequence[Mapping[str, Any]],
    *,
    dimension_selected: Sequence[str],
    active_definitions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    selected_ids = {str(item) for item in dimension_selected}
    used_sources = selected_source_uncertainty_ids(active_definitions)
    available: list[dict[str, Any]] = []
    for candidate in candidates:
        dimension_id = str(_field(candidate, "dimension_id", "dimensionId") or "")
        source_ids = {str(item) for item in (_field(candidate, "source_uncertainty_ids", "sourceUncertaintyIds") or [])}
        if not dimension_id or dimension_id in selected_ids or source_ids.intersection(used_sources):
            continue
        available.append(dict(candidate))
    return available
