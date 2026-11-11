from __future__ import annotations

# ruff: noqa: CPY001, S101, ANN201
import pytest

from tests.manual.quality_eval.repair_report import LABELS, pass_statistics, wilson


def record(verdict: str, score: int = 4):
    return {
        "status": "succeeded",
        "verdict": verdict,
        "averageScore": score,
        "result": {"items": [{"judgeId": key, "verdict": verdict, "score": score} for key in LABELS]},
    }


def test_pass_denominator_keeps_failed_attempts_and_retains_unmodified_pass():
    cases = [
        {"before": record("PASS"), "after": {}, "completed": False, "delta": None},
        {"before": record("WARN", 3), "after": record("PASS", 5), "completed": True, "delta": 2},
        {"before": record("FAIL", 2), "after": {"status": "failed"}, "completed": False, "delta": None},
        {"before": record("NEEDS_FACT"), "after": {}, "completed": False, "delta": None},
    ]
    stats = pass_statistics(cases)
    assert stats["denominator"] == 4
    assert stats["beforeRate"] == 25
    assert stats["afterRate"] == 50
    assert stats["changePercentagePoints"] == 25
    assert stats["finalKnown"] == 3
    assert stats["retainedOriginal"] == 2
    assert stats["criteriaBeforePass"] == 7
    assert stats["criteriaAfterPass"] == 14
    assert stats["criteriaDenominator"] == 28
    assert stats["deltaMedian"] == 2
    assert stats["deltaStdDev"] is None
    assert {"before": "FAIL", "after": "UNKNOWN", "count": 1} in stats["transitions"]


def test_high_score_warn_is_not_counted_as_pass_and_decline_is_preserved():
    stats = pass_statistics([
        {"before": record("WARN", 5), "after": record("FAIL", 2), "completed": True, "delta": -3},
    ])
    assert stats["beforeRate"] == stats["afterRate"] == 0
    assert stats["deltaMedian"] == -3
    assert stats["criteriaAfterRate"] == 0


def test_zero_and_full_pass_intervals_show_small_sample_uncertainty():
    assert wilson(0, 10) == pytest.approx([0, 27.75])
    assert wilson(10, 10) == pytest.approx([72.25, 100])
    assert wilson(0, 0) is None
