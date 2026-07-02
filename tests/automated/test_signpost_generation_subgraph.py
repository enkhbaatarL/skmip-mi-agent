# ruff: noqa: ANN001, ANN202, S101

from __future__ import annotations

import asyncio

from apps.agents.scenario_group_agent.subgraphs.signpost_generation import nodes
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.flow import (
    signpost_generation_runnable,
)
from apps.persistence.enums import SignpostStrength


def _scenario() -> dict[str, object]:
    return {
        "scenario_id": 100,
        "title": "LNG 공급 차질",
        "description": "공급망 제약이 가격에 영향을 주는 시나리오",
        "dimension_values": {"supply": "tight"},
    }


def _event_summary() -> dict[str, str]:
    return {
        "title": "기준 이벤트",
        "summary": "공급 차질 가능성",
        "driver": "수급",
    }


def test_signpost_generation_subgraph_returns_generated_signposts(monkeypatch) -> None:
    async def fake_stage2(scenario, base_event_summary):
        return ["정부 공식 발표", "주요 터미널 가동률 보도", "선박 운임 급등 보도"]

    async def fake_stage4(scenario, base_event_summary, labels):
        return [
            {
                "label_ko": label,
                "strength": SignpostStrength.MEDIUM.to_string(),
                "rationale_ko": f"{label} 근거",
            }
            for label in labels
        ]

    async def fake_stage5(scenario, base_event_summary, labels):
        return [[label, "보도", "확인"] for label in labels]

    monkeypatch.setattr(nodes, "stage2_observability_filter", fake_stage2)
    monkeypatch.setattr(nodes, "stage4_assign_direction_strength", fake_stage4)
    monkeypatch.setattr(nodes, "stage5_mint_keywords", fake_stage5)

    output = asyncio.run(
        signpost_generation_runnable.ainvoke(
            {
                "scenario": _scenario(),
                "base_event_summary": _event_summary(),
            },
        ),
    )

    signposts = output["signposts"]
    assert len(signposts) == 3
    assert signposts[0].scenario_id == 100
    assert signposts[0].label == "정부 공식 발표"
    assert signposts[0].keyword_hints == ["정부 공식 발표", "보도", "확인"]


def test_stage2_empty_result_still_completes(monkeypatch) -> None:
    async def fake_stage2(scenario, base_event_summary):
        return []

    monkeypatch.setattr(nodes, "stage2_observability_filter", fake_stage2)

    output = asyncio.run(
        signpost_generation_runnable.ainvoke(
            {
                "scenario": _scenario(),
                "base_event_summary": _event_summary(),
            },
        ),
    )

    assert output["signposts"] == []


def test_stage4_and_stage5_results_are_assembled(monkeypatch) -> None:
    async def fake_stage2(scenario, base_event_summary):
        return ["공식 비축 방출 발표", "수입 입찰 증가 보도"]

    async def fake_stage4(scenario, base_event_summary, labels):
        return [
            {
                "label_ko": labels[0],
                "strength": SignpostStrength.STRONG.to_string(),
                "rationale_ko": "강한 근거",
            },
            {
                "label_ko": labels[1],
                "strength": SignpostStrength.WEAK.to_string(),
                "rationale_ko": "약한 근거",
            },
        ]

    async def fake_stage5(scenario, base_event_summary, labels):
        return [["비축", "방출", "발표"], ["입찰", "수입", "보도"]]

    monkeypatch.setattr(nodes, "stage2_observability_filter", fake_stage2)
    monkeypatch.setattr(nodes, "stage4_assign_direction_strength", fake_stage4)
    monkeypatch.setattr(nodes, "stage5_mint_keywords", fake_stage5)

    output = asyncio.run(
        signpost_generation_runnable.ainvoke(
            {
                "scenario": _scenario(),
                "base_event_summary": _event_summary(),
            },
        ),
    )

    first, second = output["signposts"]
    assert first.strength == SignpostStrength.STRONG
    assert first.rationale_ko == "강한 근거"
    assert first.keyword_hints == ["비축", "방출", "발표"]
    assert second.strength == SignpostStrength.WEAK
    assert second.rationale_ko == "약한 근거"
    assert second.keyword_hints == ["입찰", "수입", "보도"]
