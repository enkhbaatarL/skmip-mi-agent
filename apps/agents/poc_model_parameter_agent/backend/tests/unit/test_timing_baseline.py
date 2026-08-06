from __future__ import annotations

from datetime import date

import pytest
from app.pipeline.baseline import synthetic_baseline
from app.pipeline.timing import parse_month_range, ramp_factor, recovery_factor
from app.seed import load_seed_document


def test_korean_month_ranges_and_ambiguous_text() -> None:
    full = parse_month_range("2027년 12월부터 2028년 2월")
    omitted_year = parse_month_range("2028년 7월부터 8월")
    single = parse_month_range("2028년 7월")
    assert full and (full.start_key, full.end_key) == ("2027-12", "2028-02")
    assert omitted_year and (omitted_year.start_key, omitted_year.end_key) == ("2028-07", "2028-08")
    assert single and (single.start_key, single.end_key) == ("2028-07", "2028-07")
    assert parse_month_range("다가오는 동절기 후반") is None
    assert parse_month_range("2028년 12월부터 2028년 2월") is None
    assert parse_month_range("2028-12:2028-02") is None


def test_ramp_and_recovery_are_deterministic() -> None:
    assert [ramp_factor(index, 3) for index in range(3)] == [0.5, 1.0, 0.75]
    assert recovery_factor(1, 2) == pytest.approx(2 / 3)
    assert recovery_factor(2, 2) == pytest.approx(1 / 3)


def test_synthetic_baseline_is_stable_and_seasonal() -> None:
    parameter = load_seed_document().parameters["nea_lng_demand_index"]
    first = synthetic_baseline(parameter, date(2028, 1, 1))
    second = synthetic_baseline(parameter, date(2028, 1, 1))
    summer = synthetic_baseline(parameter, date(2028, 7, 1))
    assert first == second
    assert first > summer
    assert 0 <= first <= 200
