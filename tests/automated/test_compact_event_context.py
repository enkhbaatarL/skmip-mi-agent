# ruff: noqa: S101

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

import pytest

from apps.agents.scenario_group_agent.prompts import event_context as event_context_prompts
from apps.agents.scenario_group_agent.prompts.event_context import (
    MAX_KEY_FACT_LENGTH,
    format_compact_event_context,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    MODEL_LEVER_SYSTEM_PROMPT,
    build_model_lever_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.multi_event_scenario_generation import (
    build_multi_event_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.scenario_generation import (
    build_stage2_user_prompt as build_scenario_stage2_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.signpost_generation import (
    build_stage2_user_prompt as build_signpost_stage2_user_prompt,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes import (
    stage1_build_context_pack,
)


class FixedDate(date):
    @classmethod
    def today(cls) -> FixedDate:
        return cls(2026, 8, 3)


def _raw_event(event_id: int, *, title: str) -> dict[str, object]:
    return {
        "mi_event_id": event_id,
        "event_type_l2_id": 8,
        "event_title_ko": title,
        "one_line_summary": f"{title} 요약",
        "occurred_at": "2026-08-01T03:00:00",
        "key_bullets": ["가" * 300, "두 번째", "세 번째", "네 번째", "다섯 번째", "제외할 여섯 번째"],
        "tags": [f"태그-{index}" for index in range(1, 10)],
        "detail_analysis": "절대 포함하면 안 되는 상세 분석",
        "event_type": {"level_1_code": "demand", "level_2_code": "heatwave"},
        "created_at": "절대 포함하면 안 되는 생성 시각",
        "source_mi_record_ids": [999],
    }


def _event_section(prompt: str, *, next_heading: str) -> str:
    return prompt.split("## Event Context", maxsplit=1)[1].split(next_heading, maxsplit=1)[0]


def test_shared_compact_context_limits_fields_lengths_and_preserves_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(event_context_prompts, "date", FixedDate)
    rendered = format_compact_event_context(
        [_raw_event(202, title="먼저 요청한 Event"), _raw_event(101, title="나중에 요청한 Event")],
    )

    assert rendered.count("current_date:") == 1
    assert rendered.count("temporal_reference:") == 1
    assert rendered.index("[Event 202]") < rendered.index("[Event 101]")
    assert "먼저 요청한 Event" in rendered
    assert "제외할 여섯 번째" not in rendered
    assert "태그-8" in rendered
    assert "태그-9" not in rendered
    first_fact = next(line.removeprefix("- ") for line in rendered.splitlines() if line.startswith("- 가"))
    assert len(first_fact) == MAX_KEY_FACT_LENGTH

    for forbidden in (
        "detail_analysis",
        "절대 포함하면 안 되는 상세 분석",
        "event_type",
        "heatwave",
        "created_at",
        "절대 포함하면 안 되는 생성 시각",
        "source_mi_record_ids",
        "999",
        "{",
        "}",
        '"',
    ):
        assert forbidden not in rendered


def test_v1_signpost_v2_v3_and_v4_prompts_use_shared_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(event_context_prompts, "date", FixedDate)
    first = _raw_event(202, title="먼저 요청한 Event")
    second = _raw_event(101, title="나중에 요청한 Event")
    pack = stage1_build_context_pack(first)
    template = Mock()
    template.ordered_dimensions.return_value = []
    template.resolved_total.return_value = 0

    prompts = [
        build_scenario_stage2_user_prompt(pack=pack, template=template, required_dim_ids=[]),
        build_signpost_stage2_user_prompt(
            scenario={"scenario_id": "S1", "dimension_values": {}},
            base_event_summary=pack.C1_base_event.model_dump(),
            scenario_description="설명",
            min_n=3,
            max_n=6,
        ),
        build_multi_event_user_prompt(
            api_version="v2",
            events=[first, second],
            templates=[{}, {}],
        ),
        build_multi_event_user_prompt(
            api_version="v3",
            events=[first, second],
            templates=[{}, {}],
        ),
        build_model_lever_user_prompt(
            events=[first, second],
            impact_levers=[],
            catalog_version="catalog-v1",
        ),
    ]

    for prompt in prompts:
        assert prompt.count("current_date:") == 1
        assert prompt.count("temporal_reference:") == 1
        assert "current_date: 2026-08-03" in prompt
        assert "detailAnalysis" not in prompt
        assert "절대 포함하면 안 되는 상세 분석" not in prompt

    for prompt in prompts[2:]:
        event_section = _event_section(
            prompt,
            next_heading=(
                "## Template Domain Knowledge"
                if "## Template Domain Knowledge" in prompt
                else "## Model Impact Lever Catalog"
            ),
        )
        assert event_section.index("[Event 202]") < event_section.index("[Event 101]")
        assert "eventTypeL2Id" not in event_section
        assert "eventType" not in event_section
        assert "{" not in event_section


def test_v2_prompt_requires_selection_evidence_and_complete_candidate_partition() -> None:
    prompt = build_multi_event_user_prompt(
        api_version="v2",
        events=[_raw_event(202, title="첫 Event"), _raw_event(101, title="둘째 Event")],
        templates=[{}, {}],
    )

    for expected in (
        "direct_event_fact",
        "lng_impact_path",
        "both",
        "selectionRationale",
        "scenarioDimensionTemplateId",
        "templateChecksum",
        "NOT_RELEVANT",
        "LOWER_PRIORITY",
        "DIMENSION_LIMIT",
        "정확히 한 번씩 partition",
    ):
        assert expected in prompt

    assert "none+NOT_RELEVANT" in prompt
    assert "required=true도 관련성 근거를 충족할 때만" in prompt


def test_v4_prompt_matches_dimension_first_hybrid_contract() -> None:
    prompt = build_model_lever_user_prompt(
        events=[_raw_event(202, title="첫 Event"), _raw_event(101, title="둘째 Event")],
        impact_levers=[
            {
                "impact_lever_id": 17,
                "lever_code": "weather_demand",
                "domain": "demand",
                "label": "기상 수요",
                "description": "기온 변화에 따른 LNG 수요",
                "parameter_bindings": [
                    {
                        "parameter_name": "demand_weather",
                        "role": "primary",
                        "applicability": "한파·폭염",
                        "support_status": "executable",
                    },
                ],
            },
        ],
        catalog_version="catalog-v1",
    )
    combined = MODEL_LEVER_SYSTEM_PROMPT + prompt

    for expected in (
        "factId",
        "sourceFactIds",
        "impactLeverRefs",
        "impactLeverId",
        "leverCode",
        "mappingRationale",
        "commonImpactLeverRefs",
        "eventDimensionCoverage",
        "noDimensionReason",
        "모든 Event가\ndimension을 가질 필요는 없습니다",
        "모델 지원 상태는 dimension 선택의\n우선순위가 아닙니다",
        "적어도 하나의 dimension은 executable",
    ):
        assert expected in combined

    assert '"impactLeverId": 17' in prompt
    assert "eventImpactFacts에는 일반 leverCode를 출력하지 마십시오" in prompt
    assert "commonImpactLeverRefs는 어떤 dimension의 sourceFactIds에도 쓰이지 않은 사실에만" in prompt
    assert "dimensionIds가 있으면 noDimensionReason은 null" in prompt
    assert "선택한 Event는 적어도 하나의\ndimension에 연결되어야" not in combined
