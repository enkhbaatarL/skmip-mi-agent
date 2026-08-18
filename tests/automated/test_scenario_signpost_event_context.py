# ruff: noqa: S101

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

import pytest

from apps.agents.scenario_group_agent.prompts import event_context as event_context_prompts
from apps.agents.scenario_group_agent.prompts.scenario_generation import (
    build_scenario_group_metadata_user_prompt,
    build_stage2_user_prompt as build_scenario_stage2_user_prompt,
    build_stage3_batch_user_prompt,
    build_stage3_user_prompt,
    build_stage4_fixed_user_prompt,
    build_stage4_user_prompt,
    build_stage6_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.signpost_generation import (
    STAGE2_HARD_CONSTRAINTS,
    STAGE2_SYSTEM_PROMPT,
    build_stage2_user_prompt,
    build_stage45_user_prompt,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.nodes import stage1_build_context_pack
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import Scenario


class FixedDate(date):
    @classmethod
    def today(cls) -> FixedDate:
        return cls(2026, 7, 14)


def _event(*, key_bullets: list[str], detail_analysis: str = "") -> dict[str, object]:
    return {
        "mi_event_id": 1116,
        "event_title_ko": "EemsEnergyTerminal 확장 cFID 발표",
        "one_line_summary": "유럽 LNG 인프라 확장",
        "key_bullets": key_bullets,
        "detail_analysis": detail_analysis,
        "occurred_at": "2026-06-01T06:00:00",
        "tags": ["EemsEnergyTerminal", "Gasunie", "Vopak"],
    }


def _scenario() -> dict[str, object]:
    return {
        "scenario_id": "S_01",
        "title": "인허가 취득 후 확장 진행",
        "description": "인허가와 최종투자결정이 순차적으로 진행되는 시나리오",
        "dimension_values": {"permit": "approved"},
        "price_direction": {"ttf": "mild_bear"},
    }


def test_context_uses_all_bullets_without_detail_fallback() -> None:
    bullets = [
        "Gasunie와 Vopak이 조건부 최종투자결정을 발표했다.",
        "최종투자결정은 인허가 취득을 전제로 한다.",
        "상업화는 2028년 이후로 언급됐다.",
    ]

    pack = stage1_build_context_pack(_event(key_bullets=bullets))
    base_event = pack.C1_base_event

    assert base_event.key_facts == bullets
    assert base_event.occurred_at == "2026-06-01T06:00:00"
    assert base_event.tags == ["EemsEnergyTerminal", "Gasunie", "Vopak"]


def test_context_does_not_fall_back_to_detail_when_bullets_are_insufficient() -> None:
    detail = "상세 분석 " * 100

    pack = stage1_build_context_pack(_event(key_bullets=["짧은 사실"], detail_analysis=detail))

    assert pack.C1_base_event.key_facts == ["짧은 사실"]


def test_scenario_and_signpost_prompts_include_compact_event_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(event_context_prompts, "date", FixedDate)
    pack = stage1_build_context_pack(
        _event(
            key_bullets=[
                "최종투자결정은 인허가 취득을 전제로 한다.",
                "상업화는 2028년 이후로 언급됐다.",
                "단기 가격 영향 근거는 제한적이다.",
            ]
        )
    )
    stage4_prompt = build_stage4_user_prompt(
        pack=pack,
        dim_label_block="- permit (인허가)",
        combos_block="[1] permit=approved",
        target_count=1,
    )
    stage6_prompt = build_stage6_user_prompt(
        pack=pack,
        scenarios=[
            Scenario(
                scenario_id="S_01",
                title="인허가 진행",
                dimension_values={"permit": "approved"},
                description="설명",
                derivation_rationale="근거",
            )
        ],
    )
    context = pack.C1_base_event.model_dump()
    signpost_prompt = build_stage2_user_prompt(
        scenario=_scenario(),
        event_contexts=[context],
        scenario_description="시나리오 설명",
        min_n=3,
        max_n=6,
    )
    enrich_prompt = build_stage45_user_prompt(
        scenario=_scenario(),
        event_contexts=[context],
        scenario_description="시나리오 설명",
        labels=["인허가 승인 공식 발표", "FID 확정 발표", "상업화 일정 공표"],
    )
    template = Mock()
    template.ordered_dimensions.return_value = []
    template.resolved_total.return_value = 0
    scenario_stage2_prompt = build_scenario_stage2_user_prompt(
        pack=pack,
        template=template,
        required_dim_ids=[],
    )
    scenario_stage3_prompt = build_stage3_user_prompt(
        pack=pack,
        dim={"dim_key": "permit", "label_ko": "인허가", "description": "인허가 진행 상태"},
        enum_full_block="pending, approved",
    )
    scenario_stage3_batch_prompt = build_stage3_batch_user_prompt(
        pack=pack,
        dimensions=[
            {
                "dim_key": "permit",
                "label_ko": "인허가",
                "description": "인허가 진행 상태",
                "enum": [
                    {"id": "pending", "label": "심사 중"},
                    {"id": "approved", "label": "승인"},
                ],
            },
        ],
    )
    scenario_stage4_fixed_prompt = build_stage4_fixed_user_prompt(
        pack=pack,
        dim_label_block="- permit (인허가)",
        combos_block="[1] permit=approved",
        target_count=1,
    )
    assert "compact_event_context" not in scenario_stage2_prompt
    metadata_prompt = build_scenario_group_metadata_user_prompt(
        pack=pack,
        scenarios=[
            Scenario(
                scenario_id="S_01",
                title="인허가 진행",
                dimension_values={"permit": "approved"},
                description="설명",
                derivation_rationale="근거",
            ),
        ],
    )

    for prompt in (
        scenario_stage2_prompt,
        scenario_stage3_prompt,
        scenario_stage3_batch_prompt,
        stage4_prompt,
        scenario_stage4_fixed_prompt,
        stage6_prompt,
        metadata_prompt,
        signpost_prompt,
        enrich_prompt,
    ):
        assert "current_date: 2026-07-14" in prompt
        assert "2026-06-01T06:00:00" in prompt
        assert "최근 N일/개월, 계절 및 과거·현재·미래 판단은 current_date를 기준" in prompt
        assert "occurred_at은 Event 발생 시점" in prompt
        assert "최종투자결정은 인허가 취득을 전제로 한다." in prompt
        assert "EemsEnergyTerminal, Gasunie, Vopak" in prompt
        assert "driver:" not in prompt
        assert "detail_analysis" not in prompt


def test_prompt_includes_current_date_when_occurred_at_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(event_context_prompts, "date", FixedDate)
    context = stage1_build_context_pack(_event(key_bullets=["짧은 사실"])).C1_base_event.model_dump()
    context["occurred_at"] = ""

    prompt = build_stage2_user_prompt(
        scenario=_scenario(),
        event_contexts=[context],
        scenario_description="시나리오 설명",
        min_n=3,
        max_n=6,
    )

    assert "current_date: 2026-07-14" in prompt
    assert "occurred_at: (없음)" in prompt


def test_signpost_prompts_do_not_include_price_direction() -> None:
    context_pack = stage1_build_context_pack(_event(key_bullets=["짧은 사실"]))
    context = context_pack.C1_base_event.model_dump()

    stage2_prompt = build_stage2_user_prompt(
        scenario=_scenario(),
        event_contexts=[context],
        scenario_description="시나리오 설명",
        min_n=3,
        max_n=6,
    )
    stage45_prompt = build_stage45_user_prompt(
        scenario=_scenario(),
        event_contexts=[context],
        scenario_description="시나리오 설명",
        labels=["인허가 승인 공식 발표"],
    )

    for prompt in (stage2_prompt, stage45_prompt):
        assert "price_direction" not in prompt
        assert "mild_bear" not in prompt


def test_signpost_prompt_requires_within_scenario_discriminativeness() -> None:
    assert "동일 시나리오 내 후보 차별성" in STAGE2_SYSTEM_PROMPT
    assert "표현 변형 후보" in STAGE2_HARD_CONSTRAINTS
