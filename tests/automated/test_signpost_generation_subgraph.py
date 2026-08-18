# ruff: noqa: ANN001, ANN202, S101

from __future__ import annotations

import asyncio

import pytest

from apps.agents.scenario_group_agent.prompts.signpost_generation import Stage2Candidate
from apps.agents.scenario_group_agent.subgraphs.signpost_generation import nodes
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.flow import (
    get_signpost_generation_subgraph,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)
from apps.common.exceptions.custom import MIBaseError
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


def _event_context() -> dict[str, object]:
    return {
        **_event_summary(),
        "occurred_at": "2026-06-01T06:00:00",
        "key_facts": [
            "조건부 최종투자결정은 인허가 취득을 전제로 한다.",
            "상업화는 2028년 이후로 언급됐다.",
        ],
        "tags": ["EemsEnergyTerminal", "Gasunie", "Vopak"],
    }


def test_signpost_generation_subgraph_returns_generated_signposts(monkeypatch) -> None:
    async def fake_stage2(scenario, event_contexts, scenario_context):
        return ["정부 공식 발표", "주요 터미널 가동률 보도", "선박 운임 급등 보도"]

    async def fake_stage45(scenario, event_contexts, labels, scenario_context):
        assignments = [
            {
                "label_ko": label,
                "strength": SignpostStrength.MEDIUM.to_string(),
                "rationale_ko": f"{label} 근거",
            }
            for label in labels
        ]
        keyword_hints = [[label, "보도", "확인"] for label in labels]
        return assignments, keyword_hints

    monkeypatch.setattr(nodes, "stage2_observability_filter", fake_stage2)
    monkeypatch.setattr(nodes, "stage45_enrich_signposts", fake_stage45)

    output = asyncio.run(
        get_signpost_generation_subgraph().ainvoke(
            SignpostGenerationState(
                scenario=_scenario(),
                event_contexts=[_event_summary()],
            ),
        ),
    )

    signposts = SignpostGenerationState.model_validate(output).signposts
    assert len(signposts) == 3
    assert signposts[0].scenario_id == 100
    assert signposts[0].label == "정부 공식 발표"
    assert signposts[0].keyword_hints == ["정부 공식 발표", "보도", "확인"]


def test_stage2_empty_result_still_completes(monkeypatch) -> None:
    async def fake_stage2(scenario, event_contexts, scenario_context):
        return []

    monkeypatch.setattr(nodes, "stage2_observability_filter", fake_stage2)

    output = asyncio.run(
        get_signpost_generation_subgraph().ainvoke(
            SignpostGenerationState(
                scenario=_scenario(),
                event_contexts=[_event_summary()],
            ),
        ),
    )

    result = SignpostGenerationState.model_validate(output)
    assert result.signposts == []
    assert result.error is not None


def test_stage4_and_stage5_results_are_assembled(monkeypatch) -> None:
    async def fake_stage2(scenario, event_contexts, scenario_context):
        return ["공식 비축 방출 발표", "수입 입찰 증가 보도", "재고 수준 공식 발표"]

    async def fake_stage45(scenario, event_contexts, labels, scenario_context):
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
            {
                "label_ko": labels[2],
                "strength": SignpostStrength.MEDIUM.to_string(),
                "rationale_ko": "중간 근거",
            },
        ], [["비축", "방출", "발표"], ["입찰", "수입", "보도"], ["재고", "수준", "발표"]]

    monkeypatch.setattr(nodes, "stage2_observability_filter", fake_stage2)
    monkeypatch.setattr(nodes, "stage45_enrich_signposts", fake_stage45)

    output = asyncio.run(
        get_signpost_generation_subgraph().ainvoke(
            SignpostGenerationState(
                scenario=_scenario(),
                event_contexts=[_event_summary()],
            ),
        ),
    )

    first, second = SignpostGenerationState.model_validate(output).signposts[:2]
    assert first.strength == SignpostStrength.STRONG
    assert first.rationale_ko == "강한 근거"
    assert first.keyword_hints == ["비축", "방출", "발표"]
    assert second.strength == SignpostStrength.WEAK
    assert second.rationale_ko == "약한 근거"
    assert second.keyword_hints == ["입찰", "수입", "보도"]


def test_retry_exhaustion_raises_original_llm_error(monkeypatch) -> None:
    async def fail_invoke(*_args, **_kwargs):
        raise TimeoutError("gateway timeout")

    monkeypatch.setattr(nodes, "REF_MAX_RETRIES", 1)
    monkeypatch.setattr(nodes, "_invoke_structured", fail_invoke)

    with pytest.raises(MIBaseError) as error:
        asyncio.run(
            nodes._ainvoke_with_retry(
                stage_label="Stage 2",
                schema_cls=nodes.Stage2StructuredOutput,
                system_prompt="system",
                user_prompt="user",
                validate_fn=None,
            )
        )

    assert isinstance(error.value.__cause__, TimeoutError)


def test_stage2_truncates_candidates_above_max_without_retry(monkeypatch) -> None:
    async def fake_invoke(*_args, **_kwargs):
        return nodes.Stage2StructuredOutput(
            candidates=[Stage2Candidate(label_ko=f"관측 신호 {index}") for index in range(1, 8)]
        )

    monkeypatch.setattr(nodes, "_invoke_structured", fake_invoke)
    monkeypatch.setattr(nodes, "REF_MAX_RETRIES", 1)

    labels = asyncio.run(nodes.stage2_observability_filter(_scenario(), [_event_context()]))

    assert labels == [f"관측 신호 {index}" for index in range(1, 7)]


def test_stage2_rejects_candidates_below_minimum(monkeypatch) -> None:
    async def fake_invoke(*_args, **_kwargs):
        return nodes.Stage2StructuredOutput(
            candidates=[Stage2Candidate(label_ko=f"관측 신호 {index}") for index in range(1, 3)]
        )

    monkeypatch.setattr(nodes, "_invoke_structured", fake_invoke)
    monkeypatch.setattr(nodes, "REF_MAX_RETRIES", 1)

    with pytest.raises(MIBaseError):
        asyncio.run(nodes.stage2_observability_filter(_scenario(), [_event_context()]))


def test_assemble_signposts_rejects_count_outside_contract() -> None:
    labels = [f"신호 {index}" for index in range(7)]
    output = asyncio.run(
        nodes.AssembleSignpostsNode().run(
            SignpostGenerationState(
                scenario=_scenario(),
                labels=labels,
                stage4_assignments=[{"strength": SignpostStrength.MEDIUM.to_string()} for _ in labels],
                stage5_keyword_hints=[["a", "b", "c"] for _ in labels],
            )
        )
    )

    assert "허용 범위" in output["error"]
