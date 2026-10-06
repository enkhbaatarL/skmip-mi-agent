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
    V4_DETAIL_ANALYSIS_MAX_CHARS,
    build_model_lever_user_prompt,
    build_v4_interaction_analysis_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.multi_event_scenario_generation import (
    build_multi_event_user_prompt,
    multi_event_system_prompt,
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


def test_v1_signpost_v2_and_v3_prompts_use_shared_context(
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
            event_contexts=[pack.C1_base_event.model_dump()],
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
                "## Compact Template Candidates"
                if "## Compact Template Candidates" in prompt
                else (
                    "## Template Domain Knowledge"
                    if "## Template Domain Knowledge" in prompt
                    else "## Model Impact Lever Catalog"
                )
            ),
        )
        assert event_section.index("[Event 202]") < event_section.index("[Event 101]")
        assert "eventTypeL2Id" not in event_section
        assert "eventType" not in event_section
        assert "{" not in event_section


def test_v2_prompt_uses_compact_selection_contract_without_detailed_lineage() -> None:
    combined = multi_event_system_prompt("v2") + build_multi_event_user_prompt(
        api_version="v2",
        events=[_raw_event(202, title="첫 Event"), _raw_event(101, title="둘째 Event")],
        templates=[{}, {}],
    )

    for expected in (
        "direct_event_fact",
        "lng_impact_path",
        "both",
        "selectedDimensions",
        "sourceRef",
        "selectionRationale",
        "scenarioDimensionTemplateId",
        "bullish=+1",
        "합계가 감소하지 않아야",
    ):
        assert expected in combined

    for removed in (
        "templateChecksum",
        "sourceAssignments",
        "excludedDimensions 각 항목",
        "impactLeverRefs",
    ):
        assert removed not in combined


def test_v3_prompt_requires_empty_v2_only_excluded_dimensions() -> None:
    prompt = build_multi_event_user_prompt(
        api_version="v3",
        events=[_raw_event(202, title="첫 Event"), _raw_event(101, title="둘째 Event")],
        templates=[{}, {}],
    )

    assert "excludedDimensions" in prompt
    assert "빈 배열" in prompt


def test_v3_prompt_uses_compact_event_and_dimension_lineage_contract() -> None:
    combined = multi_event_system_prompt("v3") + build_multi_event_user_prompt(
        api_version="v3",
        events=[_raw_event(202, title="첫 Event"), _raw_event(101, title="둘째 Event")],
        templates=[{}, {}],
    )

    for expected in (
        "shockSummary",
        "sourceEventIds",
        "scenarioDimensionTemplateId",
        "pressureContribution",
        "관련 Event 사실과 예상 JKM 가격 영향 방향",
    ):
        assert expected in combined
    assert "v3 value에는 sourceAssignments를 출력하지 마십시오" in combined
    assert "Template checksum" in combined


def test_v4_prompt_matches_fact_path_analysis_contract() -> None:
    prompt = build_model_lever_user_prompt(
        events=[_raw_event(202, title="첫 Event")],
        impact_levers=[
            {
                "impact_lever_id": 17,
                "lever_code": "weather_demand",
                "domain": "demand",
                "label": "기상 수요",
                "description": "기온 변화에 따른 LNG 수요",
                "applicability_hint": "한파·폭염의 강도와 지속 기간이 수요를 바꿀 때 선택",
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
        analysis_as_of="2026-08-07",
    )
    combined = MODEL_LEVER_SYSTEM_PROMPT + prompt

    for expected in (
        "## 핵심 사실 후보",
        "eventFacts",
        "eventFacts[0]은 Primary Fact",
        "impacts[0]은 Primary Impact",
        "Event 제목과 요약의 핵심 주체·지표·상태·변화",
        "서로 다른 Lever·방향·기간",
        "decisionBasis는 Primary Fact나 Primary Impact를 대신할 수 없습니다",
        "Primary Impact의 규모·기간·회복 시점",
        "impacts.analysis",
        "eventFacts는 가급적 1~2개만 선택",
        "impacts[].evidence에는 선택한 eventFacts를 1~3개 포함하되 가급적 1~2개만 사용",
        "impacts는 가급적 1~2개만 작성",
        "leverStates",
        "openQuestions",
        "decisionBasis",
        "후보 문장을 글자까지 그대로 복사",
    ):
        assert expected in combined

    assert "impactLeverId" not in prompt
    assert "분석 기준일: 2026-08-07" in prompt
    assert "### demand" in prompt
    assert "- weather_demand: 한파·폭염의 강도와 지속 기간이 수요를 바꿀 때 선택" in prompt
    assert "기온 변화에 따른 LNG 수요" not in prompt
    assert "factStatus" not in prompt
    assert "confidence" not in prompt
    assert "selectionHint" not in prompt
    assert '"label":"기상 수요"' not in prompt
    assert "parameterBindings" not in prompt
    assert "둘째 Event" not in prompt
    assert "detailAnalysis" not in prompt
    # v4 Event analysis (unlike the shared v1~v3 compact context) receives detail_analysis as reference only.
    assert "## 상세 분석 (참고)\n절대 포함하면 안 되는 상세 분석\n" in prompt
    assert prompt.index("## 핵심 사실 후보") < prompt.index("## 상세 분석 (참고)") < prompt.index("## 사용할 수 있는 Lever")
    assert "상세 분석 문장을 eventFacts로 쓰지 않습니다" in prompt


def test_v4_event_prompt_omits_empty_detail_and_caps_long_detail() -> None:
    lever = {"lever_code": "weather_demand", "domain": "demand", "applicability_hint": "한파·폭염"}
    empty = _raw_event(202, title="상세 없음")
    empty["detail_analysis"] = "   "
    long_event = _raw_event(303, title="긴 상세")
    long_event["detail_analysis"] = "나" * (V4_DETAIL_ANALYSIS_MAX_CHARS + 500)

    without_detail = build_model_lever_user_prompt(
        events=[empty], impact_levers=[lever], catalog_version="v4", analysis_as_of="2026-10-06"
    )
    with_long_detail = build_model_lever_user_prompt(
        events=[long_event], impact_levers=[lever], catalog_version="v4", analysis_as_of="2026-10-06"
    )

    assert "## 상세 분석 (참고)" not in without_detail
    assert "나" * V4_DETAIL_ANALYSIS_MAX_CHARS in with_long_detail
    assert "나" * (V4_DETAIL_ANALYSIS_MAX_CHARS + 1) not in with_long_detail


def test_v4_interaction_prompt_marks_first_path_per_event_as_primary() -> None:
    prompt = build_v4_interaction_analysis_user_prompt(
        impact_paths=[
            {
                "event_id": 101,
                "mechanism": "첫 Event 대표 경로",
                "lever_steps": [],
                "materiality": "high",
            },
            {
                "event_id": 101,
                "mechanism": "첫 Event 보조 경로",
                "lever_steps": [],
                "materiality": "medium",
            },
            {
                "event_id": 202,
                "mechanism": "둘째 Event 대표 경로",
                "lever_steps": [],
                "materiality": "high",
            },
        ],
    )

    p1 = prompt.split("### [E101-P1]", maxsplit=1)[1].split("### [E101-P2]", maxsplit=1)[0]
    p2 = prompt.split("### [E101-P2]", maxsplit=1)[1].split("## Event 202", maxsplit=1)[0]
    p3 = prompt.split("### [E202-P1]", maxsplit=1)[1].split("## Interaction 개수 목표", maxsplit=1)[0]

    assert "역할: Primary Impact" in p1
    assert "역할: Supporting Impact" in p2
    assert "역할: Primary Impact" in p3
    assert prompt.index("[E101-P1]") < prompt.index("[E101-P2]") < prompt.index("[E202-P1]")
    assert "실제 추가 효과가 있을 때만" in prompt


def test_v4_interaction_prompt_separates_copyable_lever_code_from_state() -> None:
    prompt = build_v4_interaction_analysis_user_prompt(
        impact_paths=[
            {
                "event_id": 101,
                "mechanism": "스프레드 경로",
                "lever_steps": [
                    {
                        "lever_code": "regional_price_spread",
                        "path_role": "driver",
                        "state_direction": "increase",
                        "scope": "유럽 프리미엄",
                        "timing": "단기",
                    },
                    {
                        "lever_code": "trade_restriction",
                        "path_role": "primary",
                        "state_direction": "decrease",
                        "scope": "아시아 접근 물량",
                        "timing": "단기",
                    },
                ],
                "materiality": "high",
            },
            {
                "event_id": 202,
                "mechanism": "운임 경로",
                "lever_steps": [
                    {
                        "lever_code": "lng_charter_rate",
                        "path_role": "primary",
                        "state_direction": "decrease",
                        "scope": "대서양 용선",
                        "timing": "단기",
                    },
                ],
                "materiality": "medium",
            },
        ],
    )

    p1 = prompt.split("### [E101-P1]", maxsplit=1)[1].split("## Event 202", maxsplit=1)[0]

    assert "- Lever code: regional_price_spread, trade_restriction\n" in p1
    assert (
        "- Lever 상태: regional_price_spread increase (유럽 프리미엄, 단기); "
        "trade_restriction decrease (아시아 접근 물량, 단기)"
    ) in p1
    assert "- Lever: " not in prompt
    assert "`Lever code` 줄에 있는 code 하나만 글자까지 그대로 복사합니다" in prompt
    assert "`Lever 상태` 줄의 방향·범위·시점 설명은 lever 값에 넣지 않습니다" in prompt
