from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import V4DimensionDefinition
from apps.persistence.event.schema import EventPayload


MAX_BRANCHING_DIMENSIONS = 2
MAX_FOCUS_DIMENSIONS = 2
_PRESSURE_SCORES = {"bullish": 1, "balanced": 0, "bearish": -1}


@dataclass(frozen=True)
class V4GroupTitleFocus:
    """Dimensions a group title should represent: the common premise and the questions that split scenarios."""

    branching: list[V4DimensionDefinition] = field(default_factory=list)
    premise: V4DimensionDefinition | None = None


def _used_scores(dimension: V4DimensionDefinition, scenario_dimension_values: Sequence[Mapping[str, str]]) -> set[int]:
    used_value_ids = {values.get(dimension.dimension_id) for values in scenario_dimension_values}
    return {
        _PRESSURE_SCORES.get(value.pressure_contribution, 0)
        for value in dimension.values
        if value.value_id in used_value_ids
    }


def select_v4_group_title_focus(
    dimension_definitions: Sequence[V4DimensionDefinition],
    scenario_dimension_values: Sequence[Mapping[str, str]],
) -> V4GroupTitleFocus:
    """Pick the group-title focus from the generated scenarios, not from a single scenario's answer.

    - 핵심 분기: 생성된 Scenario들이 서로 다른 압력 기여의 값을 고른 Dimension (Dimension 순서, 같은 주 Lever 중복 제외)
    - 공통 전제: 모든 Scenario가 같은 방향(0이 아닌 압력 기여)을 고른 Dimension
    모델에 반영되지 않는 price_only Dimension은 제외한다.
    """
    candidates = [item for item in dimension_definitions if item.model_support_status != "price_only"]
    branching: list[V4DimensionDefinition] = []
    for dimension in candidates:
        if len(_used_scores(dimension, scenario_dimension_values)) < 2:
            continue
        if any(item.primary_lever_code == dimension.primary_lever_code for item in branching):
            continue
        branching.append(dimension)
        if len(branching) == MAX_BRANCHING_DIMENSIONS:
            break
    if not branching:
        branching = [
            next(
                (
                    item
                    for item in candidates
                    if len({values.get(item.dimension_id) for values in scenario_dimension_values}) > 1
                ),
                candidates[0] if candidates else dimension_definitions[0],
            )
        ]
    premise = None
    if len(branching) < MAX_FOCUS_DIMENSIONS:
        premise = next(
            (
                item
                for item in candidates
                if item not in branching
                and len(scores := _used_scores(item, scenario_dimension_values)) == 1
                and 0 not in scores
            ),
            None,
        )
    return V4GroupTitleFocus(branching=branching, premise=premise)


def events_for_dimensions(
    dimensions: Sequence[V4DimensionDefinition],
    events: Sequence[EventPayload],
) -> list[EventPayload]:
    """Return source events of the given dimensions in the group's event order."""
    source_ids = {str(event_id) for dimension in dimensions for event_id in dimension.source_event_ids}
    return [event for event in events if str(event.mi_event_id) in source_ids]
