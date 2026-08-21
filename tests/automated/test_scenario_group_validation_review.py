# ruff: noqa: S101

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from apps.agents.scenario_group_agent.prompts.scenario_generation import (
    NarrativeOnly,
    Stage4StructuredOutput,
)
from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    EventCoverageItem,
    QuickCompatibilityItem,
    QuickCompatibilityStructuredOutput,
    SimilarTitlePair,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation import nodes
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes import (
    stage4_synthesize_scenarios,
    stage5_quick_validate,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import (
    C1BaseEvent,
    PerDimensionValue,
    Scenario,
    ScenarioTemplate,
    Stage1ContextPack,
    Stage3ValueSelection,
    Stage4ScenarioSynthesis,
    Stage5RepairInstruction,
    TemplateDimension,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.state import (
    ScenarioGenerationState,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes import (
    CompatibilityItem,
    CompatibilityOutput,
    build_context,
    run_review,
)
from apps.common.exceptions.custom import MIBaseError


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


def _llm_result(
    *items: CompatibilityItem,
    similar_title_pairs: list[SimilarTitlePair] | None = None,
    event_coverage: list[EventCoverageItem] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        result=CompatibilityOutput(
            items=list(items),
            similar_title_pairs=similar_title_pairs or [],
            event_coverage=event_coverage or [],
        ),
    )


class ScenarioGroupValidationReviewTest(unittest.IsolatedAsyncioTestCase):
    async def test_multi_event_review_prompt_includes_current_generation_grounding(
        self,
    ) -> None:
        context = build_context(
            {
                **GROUP,
                "generation_strategy": "multi_event_model_lever_dimensions",
            },
            ROWS,
            PERSISTED_SCENARIOS,
            TEMPLATE,
            events=[
                {"mi_event_id": 20, "event_title_ko": "Event A"},
                {"mi_event_id": 21, "event_title_ko": "Event B"},
            ],
            generation_diagnostics={
                "event_shocks": [{"shock_id": "v3-shock-evidence"}],
                "event_facts": [{"fact_id": "v4-fact-evidence"}],
                "event_exclusions": [{"reason": "v4-exclusion-evidence"}],
                "impact_paths": [{"impact_path_id": "v4-impact-path-evidence"}],
                "path_uncertainties": [{"reason": "v4-path-uncertainty-evidence"}],
                "event_interactions": [
                    {"interaction_id": "v4-interaction-evidence"},
                ],
            },
        )
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
            event_coverage=[
                EventCoverageItem(
                    scenario_id=scenario_id,
                    event_id=event_id,
                    grounded=True,
                    reason="공동 사실 유지",
                )
                for scenario_id in (100, 101)
                for event_id in (20, 21)
            ],
        )
        invoke_compatibility = AsyncMock(return_value=compatible)

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=invoke_compatibility,
        ):
            await run_review(context)

        messages = invoke_compatibility.await_args.kwargs["messages"]
        user_prompt = messages[1]["content"]
        assert "## Generation grounding" in user_prompt
        for key, evidence in (
            ("event_shocks", "v3-shock-evidence"),
            ("event_facts", "v4-fact-evidence"),
            ("event_exclusions", "v4-exclusion-evidence"),
            ("impact_paths", "v4-impact-path-evidence"),
            ("path_uncertainties", "v4-path-uncertainty-evidence"),
            ("event_interactions", "v4-interaction-evidence"),
        ):
            assert key in user_prompt
            assert evidence in user_prompt

    async def test_multi_event_review_requires_and_reports_cartesian_event_coverage(
        self,
    ) -> None:
        context = build_context(
            {
                **GROUP,
                "generation_strategy": "multi_event_composite_dimensions",
            },
            ROWS,
            PERSISTED_SCENARIOS,
            TEMPLATE,
            events=[
                {"mi_event_id": 20, "event_title_ko": "Event A"},
                {"mi_event_id": 21, "event_title_ko": "Event B"},
            ],
        )
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
            event_coverage=[
                EventCoverageItem(
                    scenario_id=scenario_id,
                    event_id=event_id,
                    grounded=True,
                    reason="공동 사실 유지",
                )
                for scenario_id in (100, 101)
                for event_id in (20, 21)
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "PASS"
        assert any(check.check_id == "R07" for check in report.checks)

    async def test_multi_event_review_rejects_incomplete_event_coverage(self) -> None:
        context = build_context(
            {
                **GROUP,
                "generation_strategy": "multi_event_composite_dimensions",
            },
            ROWS,
            PERSISTED_SCENARIOS,
            TEMPLATE,
            events=[
                {"mi_event_id": 20, "event_title_ko": "Event A"},
                {"mi_event_id": 21, "event_title_ko": "Event B"},
            ],
        )
        incomplete = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
            event_coverage=[
                EventCoverageItem(
                    scenario_id=100,
                    event_id=20,
                    grounded=True,
                    reason="공동 사실 유지",
                ),
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=incomplete),
        ):
            with self.assertRaisesRegex(
                MIBaseError,
                "Event coverage 집합 불일치",
            ):
                await run_review(context)

    async def test_all_checks_pass(self) -> None:
        context = build_context(GROUP, ROWS, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "PASS"
        assert report.is_valid
        # R05(확률/증감 값 범위)는 비활성화된다.
        assert report.summary == {"PASS": 6, "WARN": 0, "FAIL": 0, "INFO": 0}

    async def test_requested_headers_define_review_dimensions(self) -> None:
        group = {
            **GROUP,
            "dimension_selected": ["period", "severity", "recovery"],
        }
        template = [
            *TEMPLATE,
            {
                "dim_key": "recovery",
                "label": "회복",
                "value_enums": ["빠름", "느림"],
            },
        ]
        requested_headers = [
            {"key": "period", "label": "기간", "display_order": 1},
            {"key": "severity", "label": "강도", "display_order": 2},
        ]
        context = build_context(
            group,
            ROWS,
            PERSISTED_SCENARIOS,
            template,
            requested_headers=requested_headers,
        )
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert context.selected_dims == ["period", "severity"]
        assert report.verdict == "PASS"
        assert report.summary == {"PASS": 6, "WARN": 0, "FAIL": 0, "INFO": 0}

    async def test_unchanged_request_skips_review(self) -> None:
        # 요청 본문이 DB(create scenario 결과)와 정확히 일치하면 사용자가 수정한
        # 것이 없으므로 어떤 warning 도 발생시키지 않고 통과 처리한다.
        persisted = [
            {
                "scenario_id": 100,
                "scenario_group_id": 10,
                "title": "short",
                "narrative": "short narrative",
                "status": "created",
                "dimension_values": {"period": "단기", "severity": "낮음"},
                "probability_score": 40,
                "probability_delta": 0,
                "baseline_yn": "Y",
            },
            {
                "scenario_id": 101,
                "scenario_group_id": 10,
                "title": "long",
                "narrative": "long narrative",
                "status": "created",
                "dimension_values": {"period": "단기", "severity": "낮음"},
                "probability_score": 60,
                "probability_delta": 0,
                "baseline_yn": "N",
            },
        ]
        # 동일 조합(중복)이라 원래라면 R04(MECE) WARN 이 발생하지만,
        # 요청 == DB 이므로 review 자체를 건너뛰어 warning 이 없어야 한다.
        rows = [
            {
                "scenario_id": 100,
                "title": "short",
                "narrative": "short narrative",
                "cells": {"period": "단기", "severity": "낮음"},
                "metrics": {"probability_score": 40, "probability_delta": 0},
                "baseline_yn": "Y",
            },
            {
                "scenario_id": 101,
                "title": "long",
                "narrative": "long narrative",
                "cells": {"period": "단기", "severity": "낮음"},
                "metrics": {"probability_score": 60, "probability_delta": 0},
                "baseline_yn": "N",
            },
        ]
        context = build_context(GROUP, rows, persisted, TEMPLATE)
        assert context.unchanged is True

        report = await run_review(context)

        assert report.verdict == "PASS"
        assert report.is_valid
        assert report.summary["WARN"] == 0
        assert report.checks == []

    async def test_unchanged_validation_request_ignores_fields_absent_from_body(self) -> None:
        # validation request schema 는 title/cells 만 받으므로, GET 응답에 있던
        # narrative/metrics/baselineYn 이 요청에서 빠져도 변경으로 보지 않는다.
        persisted = [
            {
                "scenario_id": 100,
                "scenario_group_id": 10,
                "title": "short",
                "narrative": "short narrative",
                "status": "created",
                "dimension_values": {"period": "단기", "severity": "낮음"},
                "probability_score": 40,
                "probability_delta": 0,
                "baseline_yn": "Y",
            },
            {
                "scenario_id": 101,
                "scenario_group_id": 10,
                "title": "long",
                "narrative": "long narrative",
                "status": "created",
                "dimension_values": {"period": "단기", "severity": "낮음"},
                "probability_score": 60,
                "probability_delta": 0,
                "baseline_yn": "N",
            },
        ]
        rows = [
            {
                "scenario_id": 100,
                "title": "short",
                "cells": {"period": "단기", "severity": "낮음"},
            },
            {
                "scenario_id": 101,
                "title": "long",
                "cells": {"period": "단기", "severity": "낮음"},
            },
        ]
        context = build_context(GROUP, rows, persisted, TEMPLATE)
        assert context.unchanged is True

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(),
        ) as invoke:
            report = await run_review(context)

        invoke.assert_not_called()
        assert report.verdict == "PASS"
        assert report.summary["WARN"] == 0
        assert report.checks == []

    async def test_modified_request_still_runs_review(self) -> None:
        # DB 와 한 글자라도 다르면(여기선 cells 변경) review 가 정상 수행된다.
        persisted = [
            {
                "scenario_id": 100,
                "scenario_group_id": 10,
                "title": "short",
                "narrative": "short narrative",
                "status": "created",
                "dimension_values": {"period": "단기", "severity": "낮음"},
                "probability_score": 40,
                "probability_delta": 0,
                "baseline_yn": "Y",
            },
            {
                "scenario_id": 101,
                "scenario_group_id": 10,
                "title": "long",
                "narrative": "long narrative",
                "status": "created",
                "dimension_values": {"period": "단기", "severity": "낮음"},
                "probability_score": 60,
                "probability_delta": 0,
                "baseline_yn": "N",
            },
        ]
        rows = [
            {
                "scenario_id": 100,
                "title": "short",
                "narrative": "short narrative",
                "cells": {"period": "단기", "severity": "낮음"},
                "metrics": {"probability_score": 40, "probability_delta": 0},
                "baseline_yn": "Y",
            },
            {
                "scenario_id": 101,
                "title": "long",
                "narrative": "long narrative",
                # 사용자가 조합을 수정 → 더 이상 DB 와 일치하지 않는다.
                "cells": {"period": "장기", "severity": "높음"},
                "metrics": {"probability_score": 60, "probability_delta": 0},
                "baseline_yn": "N",
            },
        ]
        context = build_context(GROUP, rows, persisted, TEMPLATE)
        assert context.unchanged is False

        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )
        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.checks != []

    async def test_normalized_exact_duplicate_title_blocks_without_raising(self) -> None:
        rows = [dict(ROWS[0]), dict(ROWS[1])]
        rows[0]["title"] = "LNG 공급 차질"
        rows[1]["title"] = " lng-공급, 차질 "
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
            similar_title_pairs=[
                SimilarTitlePair(
                    scenario_id_a=100,
                    scenario_id_b=101,
                    reason="표현상 동일",
                    suggested_fix="기간 차이를 제목에 표시",
                ),
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "BLOCK"
        assert not report.is_valid
        assert report.summary["FAIL"] == 1
        assert next(check for check in report.checks if check.check_id == "R00").status == "FAIL"
        assert next(check for check in report.checks if check.check_id == "R06").status == "PASS"
        assert "[실패] 시나리오명 중복" in report.reason

    async def test_semantically_similar_title_is_warning_and_blocks_review(self) -> None:
        rows = [dict(ROWS[0]), dict(ROWS[1])]
        rows[0]["title"] = "가격 상승함"
        rows[1]["title"] = "가격 상승임"
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
            similar_title_pairs=[
                SimilarTitlePair(
                    scenario_id_a=100,
                    scenario_id_b=101,
                    reason="종결어미만 다르고 같은 가격 상승을 의미합니다.",
                    suggested_fix="단기 상승과 장기 상승처럼 기간 차이를 표시하세요.",
                ),
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert not report.is_valid
        title_check = next(check for check in report.checks if check.check_id == "R06")
        assert title_check.status == "WARN"
        assert "[주의] 유사한 시나리오명" in report.reason
        assert "단기 상승과 장기 상승" in report.reason

    async def test_invalid_similar_title_pairs_raise_llm_response_error(self) -> None:
        invalid_pair_sets = [
            [SimilarTitlePair(scenario_id_a=100, scenario_id_b=100, reason="self", suggested_fix="fix")],
            [SimilarTitlePair(scenario_id_a=100, scenario_id_b=999, reason="unknown", suggested_fix="fix")],
            [
                SimilarTitlePair(scenario_id_a=100, scenario_id_b=101, reason="first", suggested_fix="fix"),
                SimilarTitlePair(scenario_id_a=101, scenario_id_b=100, reason="duplicate", suggested_fix="fix"),
            ],
        ]
        context = build_context(GROUP, ROWS, PERSISTED_SCENARIOS, TEMPLATE)

        for pairs in invalid_pair_sets:
            with self.subTest(pairs=pairs):
                result = _llm_result(
                    CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
                    CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
                    similar_title_pairs=pairs,
                )
                with patch(
                    "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
                    new=AsyncMock(return_value=result),
                ):
                    with self.assertRaises(MIBaseError) as error:
                        await run_review(context)
                assert error.exception.error_code.name == "LLM_INVALID_RESPONSE_ERROR"

    async def test_warning_sets_invalid(self) -> None:
        rows = [dict(ROWS[0]), dict(ROWS[1])]
        rows[1]["cells"] = {"period": "장기", "severity": "낮음"}
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert not report.is_valid
        assert report.summary["WARN"] == 2

    async def test_tail_override_is_not_applied(self) -> None:
        template = [
            {
                "dim_key": "supply_disruption_pattern",
                "label": "공급 차질 - 발생/회복 패턴",
                "value_enums": [
                    "P1: Short disruption",
                    "P4: Permanent loss",
                    "P5: No disruption",
                ],
            },
            {
                "dim_key": "severity",
                "label": "강도",
                "value_enums": ["낮음", "높음"],
            },
        ]
        group = {
            **GROUP,
            "dimension_selected": ["supply_disruption_pattern", "severity"],
        }
        rows = [
            {
                **ROWS[0],
                "cells": {
                    "supply_disruption_pattern": "P1: Short disruption",
                    "severity": "낮음",
                },
            },
            {
                **ROWS[1],
                "cells": {
                    "supply_disruption_pattern": "P5: No disruption",
                    "severity": "높음",
                },
            },
        ]
        context = build_context(group, rows, PERSISTED_SCENARIOS, template)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.verdict == "PASS"
        assert report.is_valid

    async def test_enum_order_does_not_define_low_probability_value(self) -> None:
        template = [
            {
                "dim_key": "period",
                "label": "기간",
                "value_enums": ["A", "B", "C", "D", "E"],
            },
            {
                "dim_key": "severity",
                "label": "강도",
                "value_enums": ["낮음", "높음"],
            },
        ]
        rows = [
            {
                **ROWS[0],
                "cells": {"period": "D", "severity": "낮음"},
            },
            {
                **ROWS[1],
                "cells": {"period": "A", "severity": "높음"},
            },
        ]
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, template)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        contrast_check = next(check for check in report.checks if check.check_id == "R01")
        assert contrast_check.status == "PASS"

    async def test_duplicate_combination_is_warning(self) -> None:
        rows = [dict(ROWS[0]), dict(ROWS[1])]
        rows[1]["cells"] = dict(rows[0]["cells"])
        context = build_context(GROUP, rows, PERSISTED_SCENARIOS, TEMPLATE)
        compatible = _llm_result(
            CompatibilityItem(scenario_id=100, compatible=True, reason="정상"),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
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
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=incompatible),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert not report.is_valid
        assert next(check for check in report.checks if check.check_id == "R03").status == "WARN"

    async def test_v4_llm_incompatibility_remains_non_blocking_warning(self) -> None:
        context = build_context(
            {**GROUP, "generation_strategy": "multi_event_model_lever_dimensions"},
            ROWS,
            PERSISTED_SCENARIOS,
            TEMPLATE,
        )
        incompatible = _llm_result(
            CompatibilityItem(
                scenario_id=100,
                compatible=False,
                reason="자동 배정값과 기존 설명이 의미상 어색함",
            ),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=incompatible),
        ):
            report = await run_review(context)

        assert report.verdict == "REVIEW"
        assert report.is_valid is True
        compatibility = next(check for check in report.checks if check.check_id == "R03")
        assert compatibility.status == "WARN"
        assert compatibility.offenders == ["'short' 시나리오: 자동 배정값과 기존 설명이 의미상 어색함"]
        assert "100" not in compatibility.offenders[0]

    async def test_llm_incompatibility_passes_when_only_recommendation_is_outside_template_enum(self) -> None:
        context = build_context(GROUP, ROWS, PERSISTED_SCENARIOS, TEMPLATE)
        incompatible = _llm_result(
            CompatibilityItem(
                scenario_id=100,
                compatible=False,
                reason="기간 값이 더 자연스러운 중간 선택지를 필요로 함",
                conflict_dim_a="강도 (severity)",
                conflict_value_a="낮음",
                conflict_dim_b="기간 (period)",
                conflict_value_b="단기",
                recommended_value_b="중기",
            ),
            CompatibilityItem(scenario_id=101, compatible=True, reason="정상"),
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=incompatible),
        ):
            report = await run_review(context)

        assert report.verdict == "PASS"
        assert report.is_valid
        r03 = next(check for check in report.checks if check.check_id == "R03")
        assert r03.status == "PASS"
        assert "enum 안 실행 가능한 권장 변경 없음" in r03.detail

    async def test_llm_error_raises_instead_of_marking_content_invalid(self) -> None:
        context = build_context(GROUP, ROWS, PERSISTED_SCENARIOS, TEMPLATE)

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(side_effect=RuntimeError("unavailable")),
        ):
            with self.assertRaises(MIBaseError) as error:
                await run_review(context)

        assert error.exception.error_code.name == "LLM_INVOCATION_ERROR"

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
            "apps.agents.scenario_group_agent.subgraphs.scenario_review.nodes._invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert "3번째 시나리오" in report.reason
        assert "-3" not in report.reason


class ScenarioGenerationQuickValidationTest(unittest.TestCase):
    def test_stage5_baseline_contrast_precheck_skips_llm_on_missing_coverage(
        self,
    ) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["단기", "중기", "장기"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="severity",
                    label="강도",
                    value_enums=["낮음", "중간", "높음"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="recovery",
                    label="회복",
                    value_enums=["빠름", "보통", "느림"],
                    display_order=3,
                ),
            ]
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["단기", "중기", "장기"],
                    selected_enum=["단기", "장기"],
                ),
                PerDimensionValue(
                    dim_key="severity",
                    template_enum_full=["낮음", "중간", "높음"],
                    selected_enum=["낮음", "높음"],
                ),
                PerDimensionValue(
                    dim_key="recovery",
                    template_enum_full=["빠름", "보통", "느림"],
                    selected_enum=["빠름", "느림"],
                ),
            ]
        )
        stage4 = Stage4ScenarioSynthesis(
            cartesian_total=1,
            filtered_by_compatibility=1,
            scenarios=[
                Scenario(
                    scenario_id="S_01",
                    title="contrast missing",
                    dimension_values={
                        "period": "단기",
                        "severity": "높음",
                        "recovery": "느림",
                    },
                    description="기간 대안값 누락",
                    derivation_rationale="test",
                )
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes._ainvoke_with_retry",
        ) as invoke:
            passed, feedback, repairs = asyncio.run(
                stage5_quick_validate(
                    Stage1ContextPack(C1_base_event=C1BaseEvent()),
                    stage3,
                    stage4,
                    template,
                )
            )

        assert not passed
        assert feedback is not None
        assert "baseline 대비 대안값 누락" in feedback
        assert "period" in feedback
        assert "Stage4 재생성 지시" in feedback
        assert "title, description, derivation_rationale" in feedback
        assert repairs == []
        invoke.assert_not_called()

    def test_stage5_compatibility_failure_returns_regeneration_feedback(self) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["단기", "장기"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="alt_lng",
                    label="대체 LNG 확보량",
                    value_enums=["50%", "100%"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="power_reduction",
                    label="PowerMix 수요 감소량",
                    value_enums=["50%", "100%"],
                    display_order=3,
                ),
            ]
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["단기", "장기"],
                    selected_enum=["단기", "장기"],
                ),
                PerDimensionValue(
                    dim_key="alt_lng",
                    template_enum_full=["50%", "100%"],
                    selected_enum=["50%", "100%"],
                ),
                PerDimensionValue(
                    dim_key="power_reduction",
                    template_enum_full=["50%", "100%"],
                    selected_enum=["50%", "100%"],
                ),
            ]
        )
        stage4 = Stage4ScenarioSynthesis(
            cartesian_total=2,
            filtered_by_compatibility=2,
            scenarios=[
                Scenario(
                    scenario_id="S_01",
                    title="baseline",
                    dimension_values={
                        "period": "단기",
                        "alt_lng": "100%",
                        "power_reduction": "50%",
                    },
                    description="baseline narrative",
                    derivation_rationale="test",
                ),
                Scenario(
                    scenario_id="S_02",
                    title="incompatible",
                    dimension_values={
                        "period": "장기",
                        "alt_lng": "50%",
                        "power_reduction": "100%",
                    },
                    description="incompatible narrative",
                    derivation_rationale="test",
                ),
            ],
        )
        compat_output = QuickCompatibilityStructuredOutput(
            items=[
                QuickCompatibilityItem(
                    scenario_id=2,
                    reason="대체 LNG 50%와 수요 감소 100%는 동시 적용이 과도함",
                    conflict_dim_a="대체 LNG 확보량 (alt_lng)",
                    conflict_value_a="50%",
                    conflict_dim_b="PowerMix 수요 감소량 (power_reduction)",
                    conflict_value_b="100%",
                    recommended_value_b="50%",
                ),
            ]
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes._ainvoke_with_retry",
            new=AsyncMock(return_value=compat_output),
        ):
            passed, feedback, repairs = asyncio.run(
                stage5_quick_validate(
                    Stage1ContextPack(C1_base_event=C1BaseEvent()),
                    stage3,
                    stage4,
                    template,
                )
            )

        assert not passed
        assert feedback is not None
        assert "검증 실패/ 재생성 필요: compatibility" in feedback
        assert "S_02" in feedback
        assert "incompatible" in feedback
        assert "'100%'을(를) '50%'(으)로 바꾸는 것을 권장합니다." in feedback
        assert "title, description, derivation_rationale" in feedback
        assert repairs == [
            Stage5RepairInstruction(
                scenario_ref="S_02",
                issue_type="compatibility",
                dim_key="power_reduction",
                current_value="100%",
                recommended_value="50%",
                reason="대체 LNG 50%와 수요 감소 100%는 동시 적용이 과도함",
            )
        ]

    def test_stage5_compatibility_feedback_allows_recommendation_outside_stage3_selection(self) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="supply_disruption_intensity",
                    label="공급 차질 - 강도",
                    value_enums=["전혀 없음", "낮음"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="supply_disruption_pattern",
                    label="공급 차질 - 발생/회복 패턴",
                    value_enums=["차질 없음", "완만한 차질", "급차질-급회복"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["1개월 이하", "6개월"],
                    display_order=3,
                ),
            ],
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="supply_disruption_intensity",
                    template_enum_full=["전혀 없음", "낮음"],
                    selected_enum=["전혀 없음", "낮음"],
                ),
                PerDimensionValue(
                    dim_key="supply_disruption_pattern",
                    template_enum_full=["차질 없음", "완만한 차질", "급차질-급회복"],
                    selected_enum=["완만한 차질", "급차질-급회복"],
                ),
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["1개월 이하", "6개월"],
                    selected_enum=["1개월 이하", "6개월"],
                ),
            ],
        )
        stage4 = Stage4ScenarioSynthesis(
            cartesian_total=2,
            filtered_by_compatibility=2,
            scenarios=[
                Scenario(
                    scenario_id="S_01",
                    title="incompatible",
                    dimension_values={
                        "supply_disruption_intensity": "전혀 없음",
                        "supply_disruption_pattern": "급차질-급회복",
                        "period": "1개월 이하",
                    },
                    description="incompatible narrative",
                    derivation_rationale="test",
                ),
                Scenario(
                    scenario_id="S_02",
                    title="contrast",
                    dimension_values={
                        "supply_disruption_intensity": "낮음",
                        "supply_disruption_pattern": "완만한 차질",
                        "period": "6개월",
                    },
                    description="contrast narrative",
                    derivation_rationale="test",
                ),
            ],
        )
        compat_output = CompatibilityOutput(
            items=[
                CompatibilityItem(
                    scenario_id=1,
                    compatible=False,
                    reason="공급 차질 없음과 급차질 패턴 충돌",
                    conflict_dim_a="공급 차질 - 강도 (supply_disruption_intensity)",
                    conflict_value_a="전혀 없음",
                    conflict_dim_b="공급 차질 - 발생/회복 패턴 (supply_disruption_pattern)",
                    conflict_value_b="급차질-급회복",
                    recommended_value_b="차질 없음",
                ),
                CompatibilityItem(
                    scenario_id=2,
                    compatible=True,
                    reason="정상",
                ),
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes._ainvoke_with_retry",
            new=AsyncMock(return_value=compat_output),
        ):
            passed, feedback, repairs = asyncio.run(
                stage5_quick_validate(
                    Stage1ContextPack(C1_base_event=C1BaseEvent()),
                    stage3,
                    stage4,
                    template,
                ),
            )

        assert not passed
        assert feedback is not None
        assert "S_01" in feedback
        assert "공급 차질 없음과 급차질 패턴 충돌" in feedback
        assert "'급차질-급회복'을(를) '차질 없음'(으)로 바꾸는 것을 권장합니다." in feedback
        assert repairs == [
            Stage5RepairInstruction(
                scenario_ref="S_01",
                issue_type="compatibility",
                dim_key="supply_disruption_pattern",
                current_value="급차질-급회복",
                recommended_value="차질 없음",
                reason="공급 차질 없음과 급차질 패턴 충돌",
            )
        ]

    def test_stage4_retry_prioritizes_recommended_value_outside_stage3_selection(self) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="supply_disruption_intensity",
                    label="공급 차질 - 강도",
                    value_enums=["전혀 없음", "낮음"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="supply_disruption_pattern",
                    label="공급 차질 - 발생/회복 패턴",
                    value_enums=["차질 없음", "완만한 차질", "급차질-급회복"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["1개월 이하", "6개월"],
                    display_order=3,
                ),
            ],
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="supply_disruption_intensity",
                    template_enum_full=["전혀 없음", "낮음"],
                    selected_enum=["전혀 없음", "낮음"],
                ),
                PerDimensionValue(
                    dim_key="supply_disruption_pattern",
                    template_enum_full=["차질 없음", "완만한 차질", "급차질-급회복"],
                    selected_enum=["완만한 차질", "급차질-급회복"],
                ),
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["1개월 이하", "6개월"],
                    selected_enum=["1개월 이하", "6개월"],
                ),
            ],
        )
        previous_stage4 = Stage4ScenarioSynthesis(
            cartesian_total=2,
            filtered_by_compatibility=2,
            scenarios=[
                Scenario(
                    scenario_id="S_01",
                    title="incompatible",
                    dimension_values={
                        "supply_disruption_intensity": "전혀 없음",
                        "supply_disruption_pattern": "급차질-급회복",
                        "period": "1개월 이하",
                    },
                    description="incompatible narrative",
                    derivation_rationale="test",
                ),
                Scenario(
                    scenario_id="S_02",
                    title="ordinary",
                    dimension_values={
                        "supply_disruption_intensity": "낮음",
                        "supply_disruption_pattern": "완만한 차질",
                        "period": "6개월",
                    },
                    description="ordinary narrative",
                    derivation_rationale="test",
                ),
            ],
        )
        repairs = [
            Stage5RepairInstruction(
                scenario_ref="S_01",
                issue_type="compatibility",
                dim_key="supply_disruption_pattern",
                current_value="급차질-급회복",
                recommended_value="차질 없음",
                reason="공급 차질 없음과 급차질 패턴 충돌",
            )
        ]

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes._ainvoke_with_retry",
            new=AsyncMock(
                return_value=Stage4StructuredOutput(
                    narratives=[
                        NarrativeOnly(
                            title=f"scenario {index}",
                            description="generated narrative",
                            derivation_rationale="generated rationale",
                        )
                        for index in range(6)
                    ],
                ),
            ),
        ):
            stage4 = asyncio.run(
                stage4_synthesize_scenarios(
                    Stage1ContextPack(C1_base_event=C1BaseEvent()),
                    stage3,
                    template,
                    validation_feedback="S_01 supply_disruption_pattern 권장값 차질 없음",
                    validation_repairs=repairs,
                    previous_stage4=previous_stage4,
                )
            )

        assert stage4.scenarios[0].dimension_values == {
            "supply_disruption_intensity": "전혀 없음",
            "supply_disruption_pattern": "차질 없음",
            "period": "1개월 이하",
        }

    def test_stage5_compatibility_passes_when_only_recommendation_is_outside_template_enum(self) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="supply_disruption_intensity",
                    label="공급 차질 - 강도",
                    value_enums=["전혀 없음", "낮음"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="supply_disruption_pattern",
                    label="공급 차질 - 발생/회복 패턴",
                    value_enums=["완만한 차질", "급차질-급회복"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["1개월 이하", "6개월"],
                    display_order=3,
                ),
            ],
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="supply_disruption_intensity",
                    template_enum_full=["전혀 없음", "낮음"],
                    selected_enum=["전혀 없음", "낮음"],
                ),
                PerDimensionValue(
                    dim_key="supply_disruption_pattern",
                    template_enum_full=["완만한 차질", "급차질-급회복"],
                    selected_enum=["완만한 차질", "급차질-급회복"],
                ),
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["1개월 이하", "6개월"],
                    selected_enum=["1개월 이하", "6개월"],
                ),
            ],
        )
        stage4 = Stage4ScenarioSynthesis(
            cartesian_total=2,
            filtered_by_compatibility=2,
            scenarios=[
                Scenario(
                    scenario_id="S_01",
                    title="incompatible",
                    dimension_values={
                        "supply_disruption_intensity": "전혀 없음",
                        "supply_disruption_pattern": "급차질-급회복",
                        "period": "1개월 이하",
                    },
                    description="incompatible narrative",
                    derivation_rationale="test",
                ),
                Scenario(
                    scenario_id="S_02",
                    title="contrast",
                    dimension_values={
                        "supply_disruption_intensity": "낮음",
                        "supply_disruption_pattern": "완만한 차질",
                        "period": "6개월",
                    },
                    description="contrast narrative",
                    derivation_rationale="test",
                ),
            ],
        )
        compat_output = CompatibilityOutput(
            items=[
                CompatibilityItem(
                    scenario_id=1,
                    compatible=False,
                    reason="공급 차질 없음과 급차질 패턴 충돌",
                    conflict_dim_a="공급 차질 - 강도 (supply_disruption_intensity)",
                    conflict_value_a="전혀 없음",
                    conflict_dim_b="공급 차질 - 발생/회복 패턴 (supply_disruption_pattern)",
                    conflict_value_b="급차질-급회복",
                    recommended_value_b="차질 없음",
                ),
                CompatibilityItem(
                    scenario_id=2,
                    compatible=True,
                    reason="정상",
                ),
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes._ainvoke_with_retry",
            new=AsyncMock(return_value=compat_output),
        ):
            passed, feedback, repairs = asyncio.run(
                stage5_quick_validate(
                    Stage1ContextPack(C1_base_event=C1BaseEvent()),
                    stage3,
                    stage4,
                    template,
                ),
            )

        assert passed
        assert feedback is None
        assert repairs == []

    def test_stage5_compatibility_still_fails_when_repair_is_unavailable_for_unresolved_dim(self) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="supply_disruption_intensity",
                    label="공급 차질 - 강도",
                    value_enums=["전혀 없음", "낮음"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="supply_disruption_pattern",
                    label="공급 차질 - 발생/회복 패턴",
                    value_enums=["완만한 차질", "급차질-급회복"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["1개월 이하", "6개월"],
                    display_order=3,
                ),
            ],
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="supply_disruption_intensity",
                    template_enum_full=["전혀 없음", "낮음"],
                    selected_enum=["전혀 없음", "낮음"],
                ),
                PerDimensionValue(
                    dim_key="supply_disruption_pattern",
                    template_enum_full=["완만한 차질", "급차질-급회복"],
                    selected_enum=["완만한 차질", "급차질-급회복"],
                ),
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["1개월 이하", "6개월"],
                    selected_enum=["1개월 이하", "6개월"],
                ),
            ],
        )
        stage4 = Stage4ScenarioSynthesis(
            cartesian_total=1,
            filtered_by_compatibility=1,
            scenarios=[
                Scenario(
                    scenario_id="S_01",
                    title="unresolved-dim",
                    dimension_values={
                        "supply_disruption_intensity": "전혀 없음",
                        "supply_disruption_pattern": "급차질-급회복",
                        "period": "1개월 이하",
                    },
                    description="unresolved dim narrative",
                    derivation_rationale="test",
                ),
                Scenario(
                    scenario_id="S_02",
                    title="contrast",
                    dimension_values={
                        "supply_disruption_intensity": "낮음",
                        "supply_disruption_pattern": "완만한 차질",
                        "period": "6개월",
                    },
                    description="contrast narrative",
                    derivation_rationale="test",
                ),
            ],
        )
        compat_output = CompatibilityOutput(
            items=[
                CompatibilityItem(
                    scenario_id=1,
                    compatible=False,
                    reason="공급 차질 없음과 급차질 패턴 충돌",
                    conflict_dim_a="공급 차질 - 강도 (supply_disruption_intensity)",
                    conflict_value_a="전혀 없음",
                    conflict_dim_b="해석할 수 없는 차원명",
                    conflict_value_b="급차질-급회복",
                    recommended_value_b="차질 없음",
                ),
                CompatibilityItem(
                    scenario_id=2,
                    compatible=True,
                    reason="정상",
                ),
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes._ainvoke_with_retry",
            new=AsyncMock(return_value=compat_output),
        ):
            passed, feedback, repairs = asyncio.run(
                stage5_quick_validate(
                    Stage1ContextPack(C1_base_event=C1BaseEvent()),
                    stage3,
                    stage4,
                    template,
                ),
            )

        assert not passed
        assert feedback is not None
        assert "검증 실패/ 재생성 필요: compatibility" in feedback
        assert repairs == []

    def test_quick_validate_node_routes_failed_stage5_back_to_stage4(self) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="supply_disruption_intensity",
                    label="공급 차질 - 강도",
                    value_enums=["전혀 없음", "낮음"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="supply_disruption_pattern",
                    label="공급 차질 - 발생/회복 패턴",
                    value_enums=["차질 없음", "급차질-급회복"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["1개월 이하", "6개월"],
                    display_order=3,
                ),
            ]
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="supply_disruption_intensity",
                    template_enum_full=["전혀 없음", "낮음"],
                    selected_enum=["전혀 없음", "낮음"],
                ),
                PerDimensionValue(
                    dim_key="supply_disruption_pattern",
                    template_enum_full=["차질 없음", "급차질-급회복"],
                    selected_enum=["차질 없음", "급차질-급회복"],
                ),
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["1개월 이하", "6개월"],
                    selected_enum=["1개월 이하", "6개월"],
                ),
            ]
        )
        stage4 = Stage4ScenarioSynthesis(
            cartesian_total=2,
            filtered_by_compatibility=2,
            scenarios=[
                Scenario(
                    scenario_id="S_01",
                    title="repair target",
                    dimension_values={
                        "supply_disruption_intensity": "전혀 없음",
                        "supply_disruption_pattern": "급차질-급회복",
                        "period": "1개월 이하",
                    },
                    description="target narrative",
                    derivation_rationale="test",
                )
            ],
        )
        state = ScenarioGenerationState(
            event_data={"mi_event_id": 1, "event_type_l2_id": 2},
            template=template,
            stage1_context_pack=Stage1ContextPack(C1_base_event=C1BaseEvent()),
            stage3_value_selection=stage3,
            stage4_scenario_synthesis=stage4,
        )
        repairs = [
            Stage5RepairInstruction(
                scenario_ref="S_01",
                issue_type="compatibility",
                dim_key="supply_disruption_pattern",
                current_value="급차질-급회복",
                recommended_value="차질 없음",
                reason="공급 차질 없음과 급차질 패턴 충돌",
            )
        ]

        with patch.object(
            nodes,
            "stage5_quick_validate",
            new=AsyncMock(return_value=(False, "feedback", repairs)),
        ):
            result = asyncio.run(nodes.quick_validate_node(state))

        assert "stage4_scenario_synthesis" not in result
        assert stage4.scenarios[0].dimension_values["supply_disruption_pattern"] == "급차질-급회복"
        assert result["validation_feedback"] == "feedback"
        assert result["validation_repairs"] == repairs
        assert result["quick_validate_retry_count"] == 1

    def test_stage5_duplicate_combination_precheck_skips_llm(self) -> None:
        template = ScenarioTemplate(
            dimensions=[
                TemplateDimension(
                    dim_key="period",
                    label="기간",
                    value_enums=["단기", "장기"],
                    display_order=1,
                ),
                TemplateDimension(
                    dim_key="severity",
                    label="강도",
                    value_enums=["낮음", "높음"],
                    display_order=2,
                ),
                TemplateDimension(
                    dim_key="recovery",
                    label="회복",
                    value_enums=["빠름", "느림"],
                    display_order=3,
                ),
            ]
        )
        stage3 = Stage3ValueSelection(
            per_dimension=[
                PerDimensionValue(
                    dim_key="period",
                    template_enum_full=["단기", "장기"],
                    selected_enum=["단기", "장기"],
                ),
                PerDimensionValue(
                    dim_key="severity",
                    template_enum_full=["낮음", "높음"],
                    selected_enum=["낮음", "높음"],
                ),
                PerDimensionValue(
                    dim_key="recovery",
                    template_enum_full=["빠름", "느림"],
                    selected_enum=["빠름", "느림"],
                ),
            ]
        )

        def scenario(scenario_id: str, title: str, values: dict[str, str]) -> Scenario:
            return Scenario(
                scenario_id=scenario_id,
                title=title,
                dimension_values=values,
                description=f"{title} narrative",
                derivation_rationale="test",
            )

        stage4 = Stage4ScenarioSynthesis(
            cartesian_total=3,
            filtered_by_compatibility=3,
            scenarios=[
                scenario(
                    "S_01",
                    "baseline",
                    {"period": "단기", "severity": "낮음", "recovery": "빠름"},
                ),
                scenario(
                    "S_02",
                    "duplicate",
                    {"period": "단기", "severity": "낮음", "recovery": "빠름"},
                ),
                scenario(
                    "S_03",
                    "contrast",
                    {"period": "장기", "severity": "높음", "recovery": "느림"},
                ),
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes._ainvoke_with_retry",
        ) as invoke:
            passed, feedback, repairs = asyncio.run(
                stage5_quick_validate(
                    Stage1ContextPack(C1_base_event=C1BaseEvent()),
                    stage3,
                    stage4,
                    template,
                )
            )

        assert not passed
        assert feedback is not None
        assert "동일한 Dimension 값 조합" in feedback
        assert "Stage4 재생성 지시" in feedback
        assert "title, description, derivation_rationale" in feedback
        assert repairs == []
        invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
