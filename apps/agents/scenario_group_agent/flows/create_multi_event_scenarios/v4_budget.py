from __future__ import annotations  # noqa: CPY001


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
    "event_open_question_budgets",
    "interaction_count_target",
    "interaction_question_budget",
]
