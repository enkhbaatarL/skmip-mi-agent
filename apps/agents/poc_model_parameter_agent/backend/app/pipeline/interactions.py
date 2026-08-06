from __future__ import annotations

from datetime import date
from typing import Any

from app.pipeline.timing import add_months, months_between


def impact_active_months(impact: dict[str, Any]) -> set[str]:
    start = date.fromisoformat(f"{impact['start']}-01")
    end = date.fromisoformat(f"{impact['end']}-01")
    recovery_end = add_months(end, int(impact.get("recoveryMonths", 0)))
    return {month.strftime("%Y-%m") for month in months_between(start, recovery_end)}


def _declares_amplification(impact: dict[str, Any], other: dict[str, Any], interactions: list[dict[str, Any]]) -> bool:
    left_ids = {int(value) for value in impact.get("sourceEventIds", [impact["eventId"]])}
    right_ids = {int(value) for value in other.get("sourceEventIds", [other["eventId"]])}
    for rule in interactions:
        rule_ids = {int(value) for value in rule.get("eventIds", [])}
        if (
            rule.get("relation") == "amplification"
            and bool(left_ids & rule_ids)
            and bool(right_ids & rule_ids)
            and bool(left_ids - right_ids or right_ids - left_ids)
        ):
            return True
    return False


def interaction_factor(
    impact: dict[str, Any],
    all_impacts: list[dict[str, Any]],
    month_key: str,
    interactions: list[dict[str, Any]],
) -> tuple[float, list[str]]:
    if impact["domain"] == "price_only":
        return 1.0, ["price_only 경로는 amplification에서 제외"]
    same_direction = [
        item
        for item in all_impacts
        if item["impactId"] != impact["impactId"]
        and item["domain"] != "price_only"
        and item["targetMarketDirection"] == impact["targetMarketDirection"]
        and month_key in impact_active_months(item)
        and _declares_amplification(impact, item, interactions)
    ]
    if not same_direction:
        return 1.0, []
    factor = min(1.25, 1.0 + 0.15 * len(same_direction))
    return factor, [f"{item['impactId']}와 같은 시장 방향 중첩" for item in same_direction]
