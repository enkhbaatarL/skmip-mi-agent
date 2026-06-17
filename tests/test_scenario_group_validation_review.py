# ruff: noqa: S101

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from apps.agents.scenario_group_agent.flows.validate_scenarios.review import (
    CompatibilityItem,
    CompatibilityOutput,
    build_context,
    run_review,
)


TEMPLATE = [
    {
        "dim_key": "period",
        "label": "기간",
        "value_enums": ["단기", "장기"],
    },
    {
        "dim_key": "severity",
        "label": "강도",
        "value_enums": ["낮음", "높음"],
    },
]
GROUP = {
    "scenario_group_id": 10,
    "mi_event_id": 20,
    "event_type_l2_id": 30,
    "title": "group",
    "dimension_selected": ["period", "severity"],
    "scenario_count": 2,
    "status": "created",
    "stage": "scenario_created",
}
PERSISTED_SCENARIOS = [
    {
        "scenario_id": 100,
        "scenario_group_id": 10,
        "title": "short",
        "narrative": "short narrative",
        "status": "created",
        "probability_score": 40,
        "probability_delta": 0,
        "impact_jkm": "neutral",
        "impact_ttf": "mild_bull",
        "impact_hh": "mild_bear",
        "baseline_yn": "Y",
    },
    {
        "scenario_id": 101,
        "scenario_group_id": 10,
        "title": "long",
        "narrative": "long narrative",
        "status": "created",
        "probability_score": 60,
        "probability_delta": 0,
        "impact_jkm": "bull",
        "impact_ttf": "bear",
        "impact_hh": "neutral",
        "baseline_yn": "N",
    },
]
ROWS = [
    {
        "scenario_id": 100,
        "title": "short",
        "narrative": "short narrative",
        "cells": {"period": "단기", "severity": "낮음"},
        "metrics": {"probability_score": 40, "probability_delta": 0},
        "impact": {"jkm": "neutral", "ttf": "mild_bull", "hh": "mild_bear"},
        "baseline_yn": "Y",
    },
    {
        "scenario_id": 101,
        "title": "long",
        "narrative": "long narrative",
        "cells": {"period": "장기", "severity": "높음"},
        "metrics": {"probability_score": 60, "probability_delta": 0},
        "impact": {"jkm": "bull", "ttf": "bear", "hh": "neutral"},
        "baseline_yn": "N",
    },
]


def _llm_result(*items: CompatibilityItem) -> SimpleNamespace:
    return SimpleNamespace(result=CompatibilityOutput(items=list(items)))


class ScenarioGroupValidationReviewTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_checks_pass(self) -> None:
        context = build_context(GROUP, ROWS, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "PASS"
        assert report.is_valid
        assert report.summary == {"PASS": 5, "WARN": 0, "FAIL": 0, "INFO": 0}

    async def test_warning_does_not_block_validation(self) -> None:
        rows = [dict(ROWS[0]), dict(ROWS[1])]
        rows[1]["cells"] = {"period": "장기", "severity": "낮음"}
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert report.is_valid
        assert report.summary["WARN"] == 2

    async def test_duplicate_combination_is_warning(self) -> None:
        rows = [dict(ROWS[0]), dict(ROWS[1])]
        rows[1]["cells"] = dict(rows[0]["cells"])
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert report.is_valid
        assert next(check for check in report.checks if check.check_id == "R04").status == "WARN"

    async def test_llm_incompatibility_is_warning(self) -> None:
        context = build_context(GROUP, ROWS, PERSISTED_SCENARIOS, TEMPLATE)
        incompatible = _llm_result(
            CompatibilityItem(
                scenario_id=100,
                compatible=False,
                reason="기간과 복구 조건이 모순",
            ),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=incompatible),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert report.is_valid
        assert next(check for check in report.checks if check.check_id == "R03").status == "WARN"

    async def test_llm_error_is_non_blocking_warning(self) -> None:
        context = build_context(GROUP, ROWS, PERSISTED_SCENARIOS, TEMPLATE)

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(side_effect=RuntimeError("unavailable")),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert report.is_valid
        assert next(check for check in report.checks if check.check_id == "R03").status == "WARN"


if __name__ == "__main__":
    unittest.main()
