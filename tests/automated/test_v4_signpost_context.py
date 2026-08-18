# ruff: noqa: ANN001, S101

from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock

from apps.agents.scenario_group_agent.flows.create_signposts.context import (
    build_v4_scenario_context,
)
from apps.agents.scenario_group_agent.flows.create_signposts.nodes import run_signpost_generation
from apps.agents.scenario_group_agent.flows.create_signposts.state import CreateSignpostsState
from apps.agents.scenario_group_agent.prompts.signpost_generation import (
    STAGE2_SYSTEM_PROMPT,
    STAGE45_SYSTEM_PROMPT,
    build_stage2_user_prompt,
    build_stage45_user_prompt,
)
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import GeneratedSignpost
from apps.persistence.event.schema import EventPayload
from apps.persistence.scenario.schema import ScenarioPayload
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


DIMENSION_DEFINITIONS = [
    {
        "dimensionId": "supply_state",
        "label": "공급 복구 상태",
        "description": "주요 공급시설의 복구 속도",
        "rationale": "복구 속도가 JKM 공급 압력을 구분한다.",
        "values": [
            {
                "valueId": "slow",
                "label": "복구 지연",
                "assumptionRationale": "Event 101의 정비 일정 지연을 가정한다.",
            },
            {
                "valueId": "fast",
                "label": "조기 복구",
                "assumptionRationale": "Event 101의 조기 재가동을 가정한다.",
            },
        ],
    },
    {
        "dimensionId": "shipping_state",
        "label": "운송 병목 상태",
        "description": "핵심 항로의 통항 가능 수준",
        "rationale": "통항 수준이 Event 간 증폭 여부를 결정한다.",
        "values": [
            {
                "valueId": "blocked",
                "label": "통항 중단",
                "assumptionRationale": "Event 202의 항로 제한이 지속된다고 가정한다.",
            },
            {
                "valueId": "open",
                "label": "정상 통항",
                "assumptionRationale": "항로 제한이 해소된다고 가정한다.",
            },
        ],
    },
]


GENERATION_DIAGNOSTICS = {
    "impactPaths": [
        {"impactPathId": "P1", "eventId": 101, "mechanism": "공급시설 정지로 현물 공급이 감소한다."},
        {"impactPathId": "P2", "eventId": 202, "mechanism": "항로 제한으로 운송 가용성이 감소한다."},
    ],
    "eventInteractions": [
        {
            "interactionId": "I1",
            "eventIds": [101, 202],
            "mechanism": "공급 감소와 운송 병목이 동시에 현물 조달 경쟁을 증폭한다.",
        },
    ],
    "scenarioPressureBreakdowns": [
        {
            "title": "검증 전 과거 제목",
            "dimensionValues": {"supply_state": "slow", "shipping_state": "blocked"},
            "commonImpactPathIds": ["P1", "P2"],
            "appliedInteractionIds": ["I1"],
        },
    ],
}


def _scenario(**overrides: object) -> dict[str, object]:
    scenario = {
        "scenario_id": 301,
        "title": "검증 후 변경된 제목",
        "description": "공급 복구가 늦고 운송 병목이 지속되는 미래 가정이다.",
        "dimension_values": {"supply_state": "slow", "shipping_state": "blocked"},
        "probability_score": 42,
        "baseline_yn": "Y",
        "scenario_role": "ceiling",
        "global_pressure_band": "strong_bullish",
        "global_pressure_rationale": "공급과 운송 제약이 JKM 상승 압력을 강화한다.",
        "related_markets": [{"market": "TTF", "rationale": "유럽 현물 조달 경쟁과 연결된다."}],
    }
    scenario.update(overrides)
    return scenario


def _events() -> list[dict[str, object]]:
    return [
        {
            "event_id": "101",
            "title": "공급시설 정비 연장",
            "summary": "재가동 일정이 늦어졌다.",
            "occurred_at": "2026-08-01",
            "key_facts": ["운영사가 정비 연장을 공식 발표했다."],
            "tags": ["공급시설", "정비"],
        },
        {
            "event_id": "202",
            "title": "핵심 항로 통항 제한",
            "summary": "선박 통항이 제한됐다.",
            "occurred_at": "2026-08-02",
            "key_facts": ["항만 당국이 통항 제한을 공지했다."],
            "tags": ["항로", "운송"],
        },
    ]


def test_v4_context_resolves_labels_and_matches_evidence_by_dimension_values() -> None:
    context = build_v4_scenario_context(
        _scenario(),
        dimension_definitions=DIMENSION_DEFINITIONS,
        generation_diagnostics=GENERATION_DIAGNOSTICS,
    )

    assert context["title"] == "검증 후 변경된 제목"
    assert context["baseline"] == "Y"
    assert context["role"] == "ceiling"
    assert context["jkm_pressure_band"] == "strong_bullish"
    assert context["dimension_selections"][0] == {
        "dimension_id": "supply_state",
        "dimension_label": "공급 복구 상태",
        "dimension_description": "주요 공급시설의 복구 속도",
        "dimension_rationale": "복구 속도가 JKM 공급 압력을 구분한다.",
        "value_id": "slow",
        "value_label": "복구 지연",
        "assumption_rationale": "Event 101의 정비 일정 지연을 가정한다.",
    }
    assert context["impact_paths"] == [
        {"event_id": 101, "mechanism": "공급시설 정지로 현물 공급이 감소한다."},
        {"event_id": 202, "mechanism": "항로 제한으로 운송 가용성이 감소한다."},
    ]
    assert context["interactions"] == [
        {
            "event_ids": [101, 202],
            "mechanism": "공급 감소와 운송 병목이 동시에 현물 조달 경쟁을 증폭한다.",
        },
    ]


def test_v4_context_drops_stale_evidence_after_combination_change() -> None:
    context = build_v4_scenario_context(
        _scenario(dimension_values={"supply_state": "fast", "shipping_state": "blocked"}),
        dimension_definitions=DIMENSION_DEFINITIONS,
        generation_diagnostics=GENERATION_DIAGNOSTICS,
    )

    assert context["dimension_selections"][0]["value_label"] == "조기 복구"
    assert context["impact_paths"] == []
    assert context["interactions"] == []


def test_v4_context_falls_back_for_unknown_values_and_incomplete_diagnostics() -> None:
    context = build_v4_scenario_context(
        _scenario(dimension_values={"supply_state": "unknown-value", "new_dimension": "new-value"}),
        dimension_definitions=DIMENSION_DEFINITIONS,
        generation_diagnostics={"scenarioPressureBreakdowns": [{"dimensionValues": None}]},
    )

    assert context["dimension_selections"][0]["value_label"] == "unknown-value"
    assert context["dimension_selections"][0]["assumption_rationale"] == ""
    assert context["dimension_selections"][1]["dimension_label"] == "new_dimension"
    assert context["dimension_selections"][1]["value_label"] == "new-value"
    assert context["impact_paths"] == []
    assert context["interactions"] == []


def test_v4_stage2_and_stage45_prompts_share_event_and_scenario_context() -> None:
    scenario = _scenario()
    context = build_v4_scenario_context(
        scenario,
        dimension_definitions=DIMENSION_DEFINITIONS,
        generation_diagnostics=GENERATION_DIAGNOSTICS,
    )
    prompts = [
        build_stage2_user_prompt(
            scenario=scenario,
            event_contexts=_events(),
            scenario_context=context,
            scenario_description=str(scenario["description"]),
            min_n=3,
            max_n=6,
        ),
        build_stage45_user_prompt(
            scenario=scenario,
            event_contexts=_events(),
            scenario_context=context,
            scenario_description=str(scenario["description"]),
            labels=["운영사 재가동 일정 공식 발표"],
        ),
    ]

    for prompt in prompts:
        assert prompt.count("[Event 101]") == 1
        assert prompt.count("[Event 202]") == 1
        assert "운영사가 정비 연장을 공식 발표했다." in prompt
        assert "항만 당국이 통항 제한을 공지했다." in prompt
        assert "## Scenario Assumptions and Rationale (not current facts)" in prompt
        assert "Dimension: 공급 복구 상태 | 주요 공급시설의 복구 속도" in prompt
        assert "Selected Value: 복구 지연 | Event 101의 정비 일정 지연을 가정한다." in prompt
        assert "Dimension rationale: 복구 속도가 JKM 공급 압력을 구분한다." in prompt
        assert "baseline: Y" in prompt
        assert "role: ceiling" in prompt
        assert "JKM pressure band: strong_bullish" in prompt
        assert "공급과 운송 제약이 JKM 상승 압력을 강화한다." in prompt
        assert "TTF | 유럽 현물 조달 경쟁과 연결된다." in prompt
        assert "eventIds=[101, 202]" in prompt

    for system_prompt in (STAGE2_SYSTEM_PROMPT, STAGE45_SYSTEM_PROMPT):
        assert "모든 Event" in system_prompt
        assert "Event 간 Interaction" in system_prompt
        assert "현재 사실" in system_prompt


def test_run_signpost_generation_passes_individual_v4_events_and_enriched_context(monkeypatch) -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        api_version="v4",
        generation_strategy="multi_event_model_lever_dimensions",
        dimension_definitions=DIMENSION_DEFINITIONS,
        generation_diagnostics=GENERATION_DIAGNOSTICS,
    )
    scenario = ScenarioPayload.model_validate(_scenario() | {"scenario_group_id": 10})
    events = [
        EventPayload(
            mi_event_id=101,
            event_type_l2_id=1,
            event_title_ko="공급시설 정비 연장",
            one_line_summary="재가동 일정이 늦어졌다.",
            occurred_at="2026-08-01",
            key_bullets=[f"공급시설 사실 {index}" for index in range(1, 7)],
        ),
        EventPayload(
            mi_event_id=202,
            event_type_l2_id=2,
            event_title_ko="핵심 항로 통항 제한",
            one_line_summary="선박 통항이 제한됐다.",
            occurred_at="2026-08-02",
            key_bullets=[f"운송 제한 사실 {index}" for index in range(1, 7)],
        ),
    ]
    subgraph = SimpleNamespace(
        ainvoke=AsyncMock(return_value={"signposts": [GeneratedSignpost(scenario_id=301, label="signal")]}),
    )
    monkeypatch.setattr(
        "apps.agents.scenario_group_agent.flows.create_signposts.nodes.ScenarioGroupService.load_event_ids",
        lambda _self, _group_id: [101, 202],
    )
    monkeypatch.setattr(
        "apps.agents.scenario_group_agent.flows.create_signposts.nodes.EventService.load_events",
        lambda _self, _event_ids: events,
    )
    monkeypatch.setattr(
        "apps.agents.scenario_group_agent.flows.create_signposts.nodes.get_signpost_generation_subgraph",
        lambda: subgraph,
    )
    monkeypatch.setitem(
        sys.modules,
        "apps.common.configs.config",
        SimpleNamespace(
            get_settings=lambda: SimpleNamespace(create_signposts_max_concurrent_scenarios=2),
        ),
    )

    result = asyncio.run(
        run_signpost_generation(
            CreateSignpostsState(
                scenario_group_id=10,
                user_id=7,
                scenario_group=group,
                scenarios=[scenario],
            ),
        ),
    )

    signpost_state = subgraph.ainvoke.await_args.args[0]
    assert [context["event_id"] for context in signpost_state.event_contexts] == ["101", "202"]
    assert signpost_state.event_contexts[0]["key_facts"] == [f"공급시설 사실 {index}" for index in range(1, 6)]
    assert signpost_state.event_contexts[1]["key_facts"] == [f"운송 제한 사실 {index}" for index in range(1, 6)]
    assert signpost_state.scenario_context["dimension_selections"][0]["value_label"] == "복구 지연"
    assert len(result["signpost_result"]["signposts"]) == 1
