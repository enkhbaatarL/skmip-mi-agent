from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.pipeline.timing import MonthRange, add_months, parse_month_range
from app.schemas.seed import SeedDocument


def _answer_value(answer: Any) -> str | None:
    if isinstance(answer, str):
        return answer
    if isinstance(answer, dict):
        value = answer.get("text") or answer.get("choiceId") or answer.get("choice_id") or answer.get("value")
        return str(value) if value else None
    return None


def resolve_event_ranges(scenario: dict[str, Any], answers: dict[str, Any]) -> dict[int, MonthRange]:
    ranges: dict[int, MonthRange] = {}
    for fact in scenario.get("eventImpactFacts", []):
        event_id = int(fact["eventId"])
        parsed = parse_month_range(str(fact.get("timing", "")))
        if parsed is None:
            answer = _answer_value(answers.get(f"timing_event_{event_id}"))
            parsed = parse_month_range(answer or "")
        if parsed is not None:
            ranges[event_id] = parsed
    return ranges


def normalize_input(scenario: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    event_ranges = resolve_event_ranges(scenario, answers)
    normalized = dict(scenario)
    normalized["eventTimings"] = {
        str(event_id): {"start": value.start_key, "end": value.end_key} for event_id, value in event_ranges.items()
    }
    normalized["clarificationAnswers"] = answers
    return normalized


def _rule_values(rule: dict[str, Any], lever: str) -> tuple[float, int, int]:
    intensity = rule.get("intensity")
    if intensity is None:
        intensity = rule.get("byLever", {}).get(lever, 0)
    return float(intensity or 0), int(rule.get("recoveryMonths", 0)), int(rule.get("shiftMonths", 0))


def derive_impacts(
    scenario: dict[str, Any],
    scenario_item: dict[str, Any],
    event_ranges: dict[int, MonthRange],
    seed: SeedDocument,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    facts = {int(fact["eventId"]): fact for fact in scenario.get("eventImpactFacts", [])}
    definitions = {item["dimensionId"]: item for item in scenario.get("dimensionDefinitions", [])}
    candidates: list[dict[str, Any]] = []
    for dimension_id, value_id in scenario_item.get("dimensionValues", {}).items():
        definition = definitions.get(dimension_id)
        rule = seed.dimension_rules.get(dimension_id, {}).get(value_id)
        if definition is None or rule is None:
            continue
        source_event_ids = [int(value) for value in definition.get("sourceEventIds", [])]
        for lever in definition.get("leverRefs", []):
            matching_fact = next(
                (facts[event_id] for event_id in source_event_ids if facts[event_id].get("leverCode") == lever), None
            )
            evidence_fact = matching_fact or (facts[source_event_ids[0]] if source_event_ids else None)
            if evidence_fact is None:
                continue
            event_id = int(evidence_fact["eventId"])
            event_range = event_ranges.get(event_id)
            if event_range is None:
                continue
            intensity, recovery_months, shift_months = _rule_values(rule, lever)
            fact_for_lever = matching_fact or evidence_fact
            direction = str(fact_for_lever.get("changeDirection", "increase")) if matching_fact else "increase"
            target_direction = (
                str(fact_for_lever.get("targetMarketDirection", "bullish")) if matching_fact else "bullish"
            )
            start = add_months(event_range.start, shift_months)
            end = add_months(event_range.end, shift_months)
            candidates.append(
                {
                    "impactId": f"{event_id}:{dimension_id}:{lever}",
                    "eventId": event_id,
                    "sourceEventIds": source_event_ids,
                    "dimensionId": dimension_id,
                    "dimensionValue": value_id,
                    "dimensionLabel": definition.get("label", dimension_id),
                    "leverCode": lever,
                    "domain": seed.levers[lever]["domain"],
                    "changeDirection": direction,
                    "targetMarketDirection": target_direction,
                    "intensity": intensity,
                    "recoveryMonths": recovery_months,
                    "shiftMonths": shift_months,
                    "start": start.strftime("%Y-%m"),
                    "end": end.strftime("%Y-%m"),
                    "confidence": float(evidence_fact.get("confidence", 0.5)),
                    "note": rule.get("note", ""),
                    "evidenceText": evidence_fact.get("factBasis", ""),
                    "magnitudeEvidence": evidence_fact.get("magnitudeEvidence", ""),
                }
            )

    grouped: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for impact in candidates:
        grouped[(impact["eventId"], impact["leverCode"])].append(impact)
    selected: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for key, items in grouped.items():
        ordered = sorted(
            items, key=lambda item: (item["intensity"], item["confidence"], item["dimensionId"]), reverse=True
        )
        selected.append(ordered[0])
        for excluded in ordered[1:]:
            exclusions.append(
                {
                    "code": "DOUBLE_COUNT_EVENT_LEVER",
                    "eventId": key[0],
                    "leverCode": key[1],
                    "keptImpactId": ordered[0]["impactId"],
                    "excludedImpactId": excluded["impactId"],
                    "reason": "동일 Event·Lever에서 최대 강도 Dimension만 채택했습니다.",
                }
            )
    return selected, exclusions


def event_season(start_key: str) -> str:
    month = int(start_key.split("-")[1])
    if month in {11, 12, 1, 2, 3}:
        return "winter"
    if month in {6, 7, 8, 9}:
        return "summer"
    return "any"


def map_parameters(
    impacts: list[dict[str, Any]], seed: SeedDocument
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    mapped: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    for impact in impacts:
        season = event_season(impact["start"])
        candidates = [item for item in seed.mappings if item["leverCode"] == impact["leverCode"]]
        by_parameter: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for mapping in candidates:
            if mapping.get("season") in {season, "any"}:
                by_parameter[mapping["parameterCode"]].append(mapping)
        for parameter_code, parameter_mappings in by_parameter.items():
            ordered = sorted(
                parameter_mappings,
                key=lambda item: (
                    item.get("season") == season,
                    float(item.get("confidence", 0)),
                    float(item.get("weight", 0)),
                ),
                reverse=True,
            )
            selected = ordered[0]
            mapped.append({**impact, "parameterCode": parameter_code, "mapping": selected})
            for excluded in ordered[1:]:
                exclusions.append(
                    {
                        "code": "MAPPING_PRIORITY",
                        "impactId": impact["impactId"],
                        "parameterCode": parameter_code,
                        "keptReason": selected.get("reason"),
                        "excludedReason": excluded.get("reason"),
                    }
                )
    by_mapped_parameter: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in mapped:
        by_mapped_parameter[item["parameterCode"]].append(item)
    deduplicated: list[dict[str, Any]] = []
    for parameter_code, items in by_mapped_parameter.items():
        ordered = sorted(
            items,
            key=lambda item: (
                float(item["mapping"].get("confidence", 0)),
                float(item.get("confidence", 0)),
                float(item.get("intensity", 0)),
                -int(item.get("eventId", 0)),
            ),
            reverse=True,
        )
        deduplicated.append(ordered[0])
        for excluded in ordered[1:]:
            exclusions.append(
                {
                    "code": "DOUBLE_COUNT_PARAMETER",
                    "parameterCode": parameter_code,
                    "keptImpactId": ordered[0]["impactId"],
                    "excludedImpactId": excluded["impactId"],
                    "reason": "동일 Parameter에 매핑된 Impact 중 confidence·강도 우선순위 1건만 채택했습니다.",
                }
            )
    return deduplicated, exclusions
