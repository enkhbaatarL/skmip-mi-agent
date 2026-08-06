from __future__ import annotations

from app.pipeline.impact import derive_impacts, map_parameters, resolve_event_ranges
from app.pipeline.interactions import interaction_factor
from app.seed import load_seed_document


def test_catalog_mapping_and_double_counting_exclusion() -> None:
    seed = load_seed_document()
    scenario = seed.example1
    impacts, exclusions = derive_impacts(scenario, scenario["scenarios"][0], resolve_event_ranges(scenario, {}), seed)
    mappings, mapping_exclusions = map_parameters(impacts, seed)
    assert all(item["parameterCode"] in seed.parameters for item in mappings)
    assert len({(item["eventId"], item["leverCode"]) for item in impacts}) == len(impacts)
    assert all(item["code"] == "DOUBLE_COUNT_EVENT_LEVER" for item in exclusions)
    assert all(item["code"] == "MAPPING_PRIORITY" for item in mapping_exclusions)


def test_amplification_requires_overlap_and_excludes_price_only() -> None:
    base = {
        "impactId": "one",
        "eventId": 1,
        "sourceEventIds": [1],
        "domain": "demand",
        "targetMarketDirection": "bullish",
        "start": "2028-01",
        "end": "2028-02",
        "recoveryMonths": 0,
    }
    same = {**base, "impactId": "two", "eventId": 2, "sourceEventIds": [2], "domain": "supply"}
    rules = [{"eventIds": [1, 2], "relation": "amplification"}]
    factor, reasons = interaction_factor(base, [base, same], "2028-01", rules)
    assert factor == 1.15
    assert reasons
    assert interaction_factor(base, [base, same], "2028-01", [])[0] == 1.0
    assert interaction_factor(base, [base, same], "2028-03", rules)[0] == 1.0
    assert interaction_factor({**base, "domain": "price_only"}, [base, same], "2028-01", rules)[0] == 1.0


def test_amplification_cap() -> None:
    impacts = [
        {
            "impactId": str(index),
            "eventId": index,
            "sourceEventIds": [index],
            "domain": "demand",
            "targetMarketDirection": "bullish",
            "start": "2028-01",
            "end": "2028-01",
            "recoveryMonths": 0,
        }
        for index in range(4)
    ]
    rules = [{"eventIds": list(range(4)), "relation": "amplification"}]
    assert interaction_factor(impacts[0], impacts, "2028-01", rules)[0] == 1.25
