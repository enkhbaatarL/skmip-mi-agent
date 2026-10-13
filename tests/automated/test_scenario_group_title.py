from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import v4_nodes
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_group_title import (
    events_for_dimensions,
    select_v4_group_title_focus,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4DimensionDefinition,
    V4DimensionValueDefinition,
    V4GroupTitleDraft,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    build_v4_group_title_user_prompt,
)
from apps.agents.scenario_group_agent.utils.scenario_group_title import (
    FALLBACK_GROUP_TITLE_MAX_LENGTH,
    build_fallback_group_title,
    find_events_missing_from_group_title,
    format_group_title_missing_events,
)
from apps.common.values.enums import ModelPreference
from apps.persistence.event.schema import EventPayload


def _group_238_events() -> list[EventPayload]:
    return [
        EventPayload(
            mi_event_id=801,
            event_type_l2_id=9,
            event_title_ko="스페인 가스 수요·저탄소가스 전망",
            one_line_summary="[스페인 가스 수요] 2032년 수요 감소와 저탄소가스 확대 전망 → 장기 가스 수요 완화",
        ),
        EventPayload(
            mi_event_id=797,
            event_type_l2_id=19,
            event_title_ko="캐나다·프랑스 LNG 협력 가능성",
            one_line_summary="[캐나다·프랑스 LNG 협력] 태평양 연안 LNG 활용 논의 → 장기 공급 다변화 선택지 부각",
        ),
        EventPayload(
            mi_event_id=18,
            event_type_l2_id=1,
            event_title_ko="미 가스 생산 증가와 HH 약세",
            one_line_summary="[미국 가스 공급] 9월 평균 생산 113.1 bcfd로 증가 속 HH 약세",
        ),
    ]


def test_group_238_title_reports_events_merged_into_region() -> None:
    missing = find_events_missing_from_group_title("스페인 수요 감소와 북미 LNG 공급완화", _group_238_events())

    assert [item.mi_event_id for item in missing] == [797, 18]
    assert missing[0].event_index == 2
    assert missing[0].label == "캐나다·프랑스 LNG 협력"
    assert "캐나다" in missing[0].expected_tokens
    assert "lng" not in missing[0].expected_tokens
    assert "가능성" not in missing[0].expected_tokens
    assert "미국" in missing[1].expected_tokens
    assert "공급" not in missing[1].expected_tokens


def test_title_mentioning_every_event_passes() -> None:
    title = "스페인 가스 수요 감소 전망·미국 가스 생산 증가·캐나다-프랑스 LNG 협력 논의"

    assert find_events_missing_from_group_title(title, _group_238_events()) == []


def test_events_without_tokens_are_not_checked() -> None:
    events = [
        EventPayload(mi_event_id=1, event_type_l2_id=1, one_line_summary="한파로 난방 수요가 증가했다."),
        EventPayload(mi_event_id=2, event_type_l2_id=1, event_title_ko="LNG 가격 상승"),
        EventPayload(mi_event_id=3, event_type_l2_id=1, event_title_ko="미국 LNG 수출"),
    ]

    # 1번은 제목·label이 없고, 2번은 일반어만 남아 판정 근거가 없다.
    assert [item.mi_event_id for item in find_events_missing_from_group_title("무관한 제목", events)] == [3]


def test_shared_theme_token_counts_for_similar_events() -> None:
    events = [
        EventPayload(
            mi_event_id=1,
            event_type_l2_id=1,
            event_title_ko="미·이란 충돌 속 호르무즈 통항 차질",
            one_line_summary="[호르무즈 물류] 미·이란 충돌 확대 속 통항 제한",
        ),
        EventPayload(
            mi_event_id=2,
            event_type_l2_id=1,
            event_title_ko="미·이란 공습 재개와 호르무즈 긴장",
            one_line_summary="[중동 지정학 리스크] 미·이란 공습 재개와 호르무즈 통항 불안",
        ),
    ]

    assert find_events_missing_from_group_title("호르무즈 통항 둔화와 걸프 선적 재둔화", events) == []


def test_missing_event_feedback_names_event_and_expected_tokens() -> None:
    missing = find_events_missing_from_group_title("스페인 수요 감소와 북미 LNG 공급완화", _group_238_events())

    feedback = format_group_title_missing_events(missing)

    assert "[이벤트 2] 캐나다·프랑스 LNG 협력" in feedback
    assert "[이벤트 3] 미국 가스 공급" in feedback
    assert "지역명으로 합치지 말고" in feedback


def _dimension(
    dimension_id: str,
    lever: str,
    source_event_ids: list[int],
    contributions: list[str],
    *,
    support: str = "full",
) -> V4DimensionDefinition:
    return V4DimensionDefinition.model_construct(
        dimension_id=dimension_id,
        label=f"{dimension_id} label",
        description=f"{dimension_id} 질문",
        source_event_ids=source_event_ids,
        primary_lever_code=lever,
        model_support_status=support,
        values=[
            V4DimensionValueDefinition.model_construct(value_id=f"{dimension_id}_v{index}", pressure_contribution=value)
            for index, value in enumerate(contributions, start=1)
        ],
    )


def _group_238_dimensions() -> list[V4DimensionDefinition]:
    return [
        _dimension("d1", "direct_gas_demand", [801], ["bearish", "bearish"]),
        _dimension("d2", "financial_market_sentiment", [797], ["balanced", "bearish"], support="price_only"),
        _dimension("d3", "upstream_production", [18], ["bearish", "balanced"]),
        _dimension("d4", "upstream_production", [18, 801], ["bearish", "bearish", "balanced"]),
    ]


GROUP_238_SCENARIOS = [
    {"d1": "d1_v1", "d2": "d2_v1", "d3": "d3_v2", "d4": "d4_v3"},
    {"d1": "d1_v1", "d2": "d2_v1", "d3": "d3_v1", "d4": "d4_v2"},
    {"d1": "d1_v2", "d2": "d2_v2", "d3": "d3_v1", "d4": "d4_v1"},
]


def test_group_238_focus_is_us_export_question_with_spain_premise() -> None:
    focus = select_v4_group_title_focus(_group_238_dimensions(), GROUP_238_SCENARIOS)

    # d2는 price_only, d4는 d3와 같은 주 Lever라 제외되고, d1은 모든 Scenario에서 하락 방향이라 공통 전제다.
    assert [item.dimension_id for item in focus.branching] == ["d3"]
    assert focus.premise is not None
    assert focus.premise.dimension_id == "d1"
    assert [event.mi_event_id for event in events_for_dimensions(focus.branching, _group_238_events())] == [18]


def test_focus_picks_up_to_two_branching_dimensions_without_premise() -> None:
    dimensions = [
        _dimension("d1", "lever_a", [1], ["bullish", "bearish"]),
        _dimension("d2", "lever_b", [2], ["balanced", "bearish"]),
        _dimension("d3", "lever_c", [3], ["bearish", "bearish"]),
    ]
    scenarios = [
        {"d1": "d1_v1", "d2": "d2_v1", "d3": "d3_v1"},
        {"d1": "d1_v2", "d2": "d2_v2", "d3": "d3_v2"},
    ]

    focus = select_v4_group_title_focus(dimensions, scenarios)

    assert [item.dimension_id for item in focus.branching] == ["d1", "d2"]
    assert focus.premise is None


def test_focus_falls_back_to_dimension_with_varied_values() -> None:
    dimensions = [
        _dimension("d1", "lever_a", [1], ["bearish", "bearish"]),
        _dimension("d2", "lever_b", [2], ["bearish", "bearish"]),
    ]
    scenarios = [{"d1": "d1_v1", "d2": "d2_v1"}, {"d1": "d1_v1", "d2": "d2_v2"}]

    focus = select_v4_group_title_focus(dimensions, scenarios)

    assert [item.dimension_id for item in focus.branching] == ["d2"]
    assert focus.premise is not None
    assert focus.premise.dimension_id == "d1"


BAD_TITLE = "스페인 수요 감소와 북미 LNG 공급완화"
GOOD_TITLE = "스페인 가스 수요 감소 전망 속 미국 가스 생산의 LNG 수출 전환 여부"
FALLBACK_TITLE = "스페인 가스 수요, 미국 가스 공급에 따른 JKM 시나리오"


def _generate(invoke: AsyncMock) -> str:
    result = SimpleNamespace(
        dimension_definitions=_group_238_dimensions(),
        scenarios=[SimpleNamespace(dimension_values=values) for values in GROUP_238_SCENARIOS],
    )
    with patch.object(v4_nodes, "invoke_stage_structured_output", new=invoke):
        return asyncio.run(v4_nodes.generate_v4_group_title(result, events=_group_238_events(), trace_context=None))


def test_group_title_prompt_uses_focus_dimensions_and_their_events_only() -> None:
    invoke = AsyncMock(return_value=V4GroupTitleDraft(title=GOOD_TITLE))

    assert _generate(invoke) == GOOD_TITLE
    invoke.assert_awaited_once()
    kwargs = invoke.await_args.kwargs
    prompt = kwargs["user_prompt"]
    assert kwargs["output_schema"] is V4GroupTitleDraft
    assert kwargs["stage"] == "group_title"
    assert kwargs["reasoning_effort_override"] == "low"
    assert kwargs["preference"] == ModelPreference.SPEED
    assert "- 질문: d3 질문" in prompt
    assert "- 질문: d1 질문" in prompt
    assert "d4 질문" not in prompt
    assert "캐나다·프랑스" not in prompt
    assert "## 이전 제목 검증 실패" not in prompt


def test_group_title_retries_with_feedback_when_branching_event_is_missing() -> None:
    invoke = AsyncMock(side_effect=[V4GroupTitleDraft(title=BAD_TITLE), V4GroupTitleDraft(title=GOOD_TITLE)])

    assert _generate(invoke) == GOOD_TITLE
    assert invoke.await_count == 2
    retry_prompt = invoke.await_args_list[1].kwargs["user_prompt"]
    assert f"- 이전 제목: {BAD_TITLE}" in retry_prompt
    assert "미국 가스 공급" in retry_prompt


def test_group_title_falls_back_after_max_attempts() -> None:
    invoke = AsyncMock(return_value=V4GroupTitleDraft(title=BAD_TITLE))

    assert _generate(invoke) == FALLBACK_TITLE
    assert invoke.await_count == v4_nodes.MAX_GROUP_TITLE_ATTEMPTS


def test_group_title_error_falls_back() -> None:
    invoke = AsyncMock(side_effect=TimeoutError("llm timeout"))

    assert _generate(invoke) == FALLBACK_TITLE
    invoke.assert_awaited_once()


def test_fallback_title_uses_event_labels_in_order() -> None:
    events = [
        *_group_238_events(),
        EventPayload(mi_event_id=5, event_type_l2_id=1, event_title_ko="동북아 한파"),
        EventPayload(mi_event_id=6, event_type_l2_id=1),
    ]

    title = build_fallback_group_title(events)

    assert title == (
        "스페인 가스 수요, 캐나다·프랑스 LNG 협력, 미국 가스 공급, 동북아 한파, 이벤트 6에 따른 JKM 시나리오"
    )
    assert find_events_missing_from_group_title(title, events) == []


def test_fallback_title_is_bounded() -> None:
    events = [
        EventPayload(mi_event_id=index, event_type_l2_id=1, event_title_ko=f"매우 긴 이벤트 제목 {index}" * 3)
        for index in range(10)
    ]

    title = build_fallback_group_title(events)

    assert len(title) <= FALLBACK_GROUP_TITLE_MAX_LENGTH
    assert title.endswith("…에 따른 JKM 시나리오")


def test_group_title_prompt_contains_rules() -> None:
    prompt = build_v4_group_title_user_prompt(
        events=[event.model_dump() for event in _group_238_events()],
        branching_dimensions=[{"description": "미국 생산이 LNG 수출로 연결되는가?", "source_event_ids": [18]}],
        premise_dimension=None,
        previous_title=BAD_TITLE,
        validation_feedback="누락: [이벤트 3] 미국 가스 공급",
    )

    assert "## 시나리오를 가르는 핵심 질문" in prompt
    assert "- 질문: 미국 생산이 LNG 수출로 연결되는가?" in prompt
    assert "## 모든 시나리오에 공통인 전제\n- 없음" in prompt
    assert "검증 오류: 누락: [이벤트 3] 미국 가스 공급" in prompt
    assert "`여부`, `폭`, `시점`, `지속성`" in prompt
    assert "서로 다른 이벤트를 지역명으로 합치지 않습니다" in prompt
    assert "이벤트를 나열하지 않습니다" in prompt
    assert "`스프레드 여부`, `수요 전망 여부`처럼" in prompt
    assert "핵심 사실" not in prompt
    assert "`전망`, `논의`, `가능성`이 있으면 해당 대상 바로 뒤에 같은 표현을 반드시" in prompt
