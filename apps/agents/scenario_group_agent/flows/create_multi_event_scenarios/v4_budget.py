from __future__ import annotations  # noqa: CPY001

from typing import Literal


_EVENT_OPEN_QUESTION_BUDGETS: dict[int, tuple[int, ...]] = {
    1: (3,),
    2: (3, 3),
    3: (3, 3, 2),
    4: (2, 2, 2, 2),
    5: (2, 2, 2, 1, 1),
}

_INTERACTION_COUNT_TARGETS: dict[int, tuple[int, int]] = {
    1: (0, 0),
    2: (1, 1),
    3: (2, 2),
    4: (2, 3),
    5: (2, 3),
}


ScenarioSynthesisPolicy = Literal["band_unique", "distinct_driver"]

# 어떤 정책에서도 생성 결과가 지켜야 하는 Scenario 개수 경계
V4_SCENARIO_HARD_MIN = 3
V4_SCENARIO_HARD_MAX = 8


def scenario_count_range(event_count: int, *, policy: ScenarioSynthesisPolicy) -> tuple[int, int]:
    """Return the (target minimum, maximum) Scenario count for the selected Event count.

    band_unique는 압력 band당 1개라 항상 3~5개다. distinct_driver는 이벤트 1~2개면 3~5개,
    3개 이상이면 (이벤트 수 + 1)~(이벤트 수 + 3)개다. 최소값은 생성 목표이며 서버가 강제하는 하한은
    V4_SCENARIO_HARD_MIN이다.
    """
    if not 1 <= event_count <= 5:
        detail = "v4 Scenario count range requires 1~5 Events"
        raise ValueError(detail)
    if policy == "band_unique" or event_count <= 2:
        return 3, 5
    return event_count + 1, min(event_count + 3, V4_SCENARIO_HARD_MAX)


def event_open_question_budgets(event_count: int) -> list[int]:
    """Return the deterministic Event question budgets in request order."""
    try:
        return list(_EVENT_OPEN_QUESTION_BUDGETS[event_count])
    except KeyError as exc:
        detail = "v4 Event question budgets require 1~5 Events"
        raise ValueError(detail) from exc


def interaction_count_target(event_count: int) -> tuple[int, int]:
    """Return the meaningful Interaction target minimum and hard maximum."""
    try:
        return _INTERACTION_COUNT_TARGETS[event_count]
    except KeyError as exc:
        detail = "v4 Interaction count targets require 1~5 Events"
        raise ValueError(detail) from exc


def interaction_question_budget(
    *,
    retained_interaction_count: int,
    retained_event_question_count: int,
) -> int:
    """Cap Interaction questions by relationship count and the final ten-question budget."""
    return max(
        0,
        min(
            2,
            retained_interaction_count,
            10 - retained_event_question_count,
        ),
    )


__all__ = [
    "V4_SCENARIO_HARD_MAX",
    "V4_SCENARIO_HARD_MIN",
    "ScenarioSynthesisPolicy",
    "event_open_question_budgets",
    "interaction_count_target",
    "interaction_question_budget",
    "scenario_count_range",
]
