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

    async def test_warning_marks_invalid(self) -> None:
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
        assert not report.is_valid
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
        assert not report.is_valid
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
        assert not report.is_valid
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
        assert not report.is_valid
        assert next(check for check in report.checks if check.check_id == "R03").status == "WARN"

    async def test_new_scenario_gets_temp_negative_id(self) -> None:
        rows = [
            dict(ROWS[0]),
            {
                "scenario_id": None,
                "display_order": 3,
                "title": "신규",
                "narrative": "신규 narrative",
                "cells": {"period": "장기", "severity": "높음"},
                "metrics": {"probability_score": 50, "probability_delta": 0},
                "impact": {"jkm": "neutral", "ttf": "neutral", "hh": "neutral"},
                "baseline_yn": "N",
            },
        ]
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)

        new_scenario = context.scenarios[1]
        assert new_scenario["scenario_id"] == -3
        assert new_scenario["is_new"] is True
        assert new_scenario["display_order"] == 3

    async def test_new_scenario_label_is_user_friendly(self) -> None:
        # 제목이 없는 신규 시나리오는 음수 ID 대신 '{displayOrder}번째 시나리오'로 노출.
        rows = [
            dict(ROWS[0]),
            {
                "scenario_id": None,
                "display_order": 3,
                "title": "",
                "narrative": "",
                # ROWS[0] 과 동일 조합으로 만들어 R04(중복) advice 를 유발한다.
                "cells": dict(ROWS[0]["cells"]),
                "metrics": {"probability_score": 50, "probability_delta": 0},
                "impact": {"jkm": "neutral", "ttf": "neutral", "hh": "neutral"},
                "baseline_yn": "N",
            },
        ]
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=-3, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert "3번째 시나리오" in report.reason
        assert "-3" not in report.reason


if __name__ == "__main__":
    unittest.main()
