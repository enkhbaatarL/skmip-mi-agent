# ruff: noqa: S101

from __future__ import annotations

from apps.agents.scenario_group_agent.prompts.scenario_generation import (
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
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import PriceDirection, Scenario


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


def test_context_uses_all_bullets_and_keeps_driver_short() -> None:
    bullets = [
        "Gasunie와 Vopak이 조건부 최종투자결정을 발표했다.",
        "최종투자결정은 인허가 취득을 전제로 한다.",
        "상업화는 2028년 이후로 언급됐다.",
    ]

    pack = stage1_build_context_pack(_event(key_bullets=bullets))
    base_event = pack.C1_base_event

    assert base_event.driver == bullets[0]
    assert base_event.key_facts == bullets
    assert base_event.occurred_at == "2026-06-01T06:00:00"
    assert base_event.tags == ["EemsEnergyTerminal", "Gasunie", "Vopak"]


def test_context_falls_back_to_detail_when_bullets_are_insufficient() -> None:
    detail = "상세 분석 " * 100

    pack = stage1_build_context_pack(_event(key_bullets=["짧은 사실"], detail_analysis=detail))

    assert len(pack.C1_base_event.key_facts) == 2
    assert pack.C1_base_event.key_facts[-1].startswith("상세 분석")
    assert len(pack.C1_base_event.key_facts[-1]) <= 603


def test_scenario_and_signpost_prompts_include_compact_event_context() -> None:
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
                price_direction=PriceDirection(jkm="neutral", ttf="neutral", hh="neutral"),
            )
        ],
    )
    context = pack.C1_base_event.model_dump()
    signpost_prompt = build_stage2_user_prompt(
        scenario=_scenario(),
        base_event_summary=context,
        scenario_description="시나리오 설명",
        min_n=3,
        max_n=6,
    )
    enrich_prompt = build_stage45_user_prompt(
        scenario=_scenario(),
        base_event_summary=context,
        scenario_description="시나리오 설명",
        labels=["인허가 승인 공식 발표", "FID 확정 발표", "상업화 일정 공표"],
    )

    for prompt in (stage4_prompt, stage6_prompt, signpost_prompt, enrich_prompt):
        assert "2026-06-01T06:00:00" in prompt
        assert "최종투자결정은 인허가 취득을 전제로 한다." in prompt
        assert "EemsEnergyTerminal, Gasunie, Vopak" in prompt


def test_signpost_prompt_requires_within_scenario_discriminativeness() -> None:
    assert "동일 시나리오 내 후보 차별성" in STAGE2_SYSTEM_PROMPT
    assert "표현 변형 후보" in STAGE2_HARD_CONSTRAINTS
