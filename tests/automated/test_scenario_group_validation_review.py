# ruff: noqa: S101

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from apps.agents.scenario_group_agent.flows.validate_scenarios.review import (
    CompatibilityItem,
    CompatibilityOutput,
    build_context,
    run_review,
)
from apps.agents.scenario_group_agent.schemas.graph.generation import (
    C1BaseEvent,
    PerDimensionValue,
    PriceDirection,
    Scenario,
    ScenarioTemplate,
    Stage5RepairInstruction,
    Stage1ContextPack,
    Stage3ValueSelection,
    Stage4ScenarioSynthesis,
    TemplateDimension,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.generation_stages import (
    _apply_repair_instructions,
    stage5_quick_validate,
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
        # R05(확률/증감 값 범위)는 비활성화되어 검사 4종(R01~R04)만 수행된다.
        assert report.summary == {"PASS": 4, "WARN": 0, "FAIL": 0, "INFO": 0}

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
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert context.selected_dims == ["period", "severity"]
        assert report.verdict == "PASS"
        assert report.summary == {"PASS": 4, "WARN": 0, "FAIL": 0, "INFO": 0}

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
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        assert report.checks != []

    async def test_warning_sets_invalid(self) -> None:
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
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
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
            "apps.agents.scenario_group_agent.flows.validate_scenarios.review."
            "_invoke_compatibility",
            new=AsyncMock(return_value=compatible),
        ):
            report = await run_review(context)

        contrast_check = next(
            check for check in report.checks if check.check_id == "R01"
        )
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

    async def test_llm_error_sets_invalid(self) -> None:
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
                    price_direction=PriceDirection(
                        brent="neutral",
                        jkm="neutral",
                        ttf="neutral",
                        hh="neutral",
                    ),
                )
            ],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation."
            "generation_stages._ainvoke_with_retry",
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
        assert Stage5RepairInstruction(
            scenario_ref="S_01",
            issue_type="baseline_contrast",
            dim_key="period",
            current_value="단기",
            recommended_value="장기",
            reason="baseline 대비 대안값 coverage 확보",
        ) in repairs
        assert {repair.dim_key for repair in repairs} == {
            "period",
            "severity",
            "recovery",
        }
        invoke.assert_not_called()

    def test_stage4_repair_instruction_replaces_target_combo(self) -> None:
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
            ],
        )
        target = [
            {"period": "단기", "severity": "낮음"},
            {"period": "단기", "severity": "높음"},
        ]
        replacement = {"period": "장기", "severity": "높음"}
        repairs = [
            Stage5RepairInstruction(
                scenario_ref="S_02",
                issue_type="compatibility",
                dim_key="period",
                current_value="단기",
                recommended_value="장기",
                reason="조합 호환성 개선",
            )
        ]

        repaired = _apply_repair_instructions(
            target,
            [*target, replacement],
            stage3,
            repairs,
        )

        assert repaired == [target[0], replacement]

    def test_stage5_compatibility_failure_returns_repair_instruction(self) -> None:
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
                    price_direction=PriceDirection(
                        brent="neutral",
                        jkm="neutral",
                        ttf="neutral",
                        hh="neutral",
                    ),
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
                    price_direction=PriceDirection(
                        brent="neutral",
                        jkm="neutral",
                        ttf="neutral",
                        hh="neutral",
                    ),
                ),
            ],
        )
        compat_output = CompatibilityOutput(
            items=[
                CompatibilityItem(
                    scenario_id=1,
                    compatible=True,
                    reason="정상",
                ),
                CompatibilityItem(
                    scenario_id=2,
                    compatible=False,
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
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation."
            "generation_stages._ainvoke_with_retry",
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
        assert "PowerMix 수요 감소량" in feedback
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
                price_direction=PriceDirection(
                    brent="neutral",
                    jkm="neutral",
                    ttf="neutral",
                    hh="neutral",
                ),
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
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation."
            "generation_stages._ainvoke_with_retry",
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
        assert repairs
        assert repairs[0].scenario_ref == "S_02"
        assert repairs[0].issue_type == "duplicate"
        invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
