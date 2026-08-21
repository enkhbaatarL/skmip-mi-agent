from __future__ import annotations

# ruff: noqa: CPY001, S101
from unittest.mock import patch

import pytest

from apps.agents.scenario_group_agent.flows.add_dimension.flow import get_additional_dimensions
from apps.agents.scenario_group_agent.flows.add_dimension.nodes import (
    build_unused_impact_analysis,
    filter_available_candidates,
    hydrate_additional_dimension_candidates,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_enums import StateDirection
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_schema import (
    V4EventImpactAnalysisResult,
    V4ReadableAdditionalDimensionDesignDraft,
    V4ReadableDimension,
    V4ReadableInteractionAnalysisDraft,
    V4ReadableScenario,
    expand_v4_additional_dimension_candidates,
    finalize_open_question_pool,
    merge_v4_readable_interactions,
)
from apps.agents.scenario_group_agent.prompts.model_lever_scenario_generation import (
    V4_ADDITIONAL_DIMENSION_SYSTEM_PROMPT,
    build_v4_additional_dimension_user_prompt,
)
from apps.agents.scenario_group_agent.utils.dimension_values import (
    build_dimension_value_catalog,
    canonicalize_dimension_cells,
)
from apps.persistence.model_impact_lever.schema import ModelImpactLeverPayload


def _analysis(question_count: int) -> V4EventImpactAnalysisResult:
    paths = []
    uncertainties = []
    axes = ["magnitude", "scope", "timing", "duration", "recovery", "mitigation", "substitution"]
    for index in range(1, question_count + 1):
        event_id = 1 + ((index - 1) % 3)
        path_id = f"p{index}"
        paths.append(
            {
                "impactPathId": path_id,
                "eventId": event_id,
                "sourceFactIds": [f"f{index}"],
                "mechanism": f"영향 경로 {index}",
                "leverSteps": [
                    {
                        "impactLeverId": index,
                        "leverCode": f"lever_{index}",
                        "pathRole": "primary" if index <= 3 else "driver",
                        "stateDirection": "increase",
                        "scope": "시장",
                        "timing": "단기",
                    },
                ],
                "materiality": "high" if index <= 2 else "medium" if index <= 8 else "low",
            },
        )
        uncertainties.append(
            {
                "uncertaintyId": f"u{index}",
                "impactPathIds": [path_id],
                "axisType": axes[(index - 1) % len(axes)],
                "subject": f"질문 {index}",
                "affectedLeverCode": f"lever_{index}",
                "reason": f"질문 {index}",
                "materiality": "high" if index <= 2 else "medium" if index <= 8 else "low",
                "semanticKey": f"{path_id}:{axes[(index - 1) % len(axes)]}:lever_{index}",
            },
        )
    return V4EventImpactAnalysisResult.model_validate(
        {"impactPaths": paths, "pathUncertainties": uncertainties},
    )


def _catalog(question_count: int) -> list[ModelImpactLeverPayload]:
    return [
        ModelImpactLeverPayload(
            impact_lever_id=index,
            lever_code=f"lever_{index}",
            domain="price_only",
            label=f"Lever {index}",
            description=f"Lever {index} 설명",
            catalog_version="v1",
        )
        for index in range(1, question_count + 1)
    ]


def _candidate(source: str, lever: str, *, states: list[list[str]] | None = None) -> dict[str, object]:
    choice_states = states or [
        [f"{lever}|increase|확대|시장|단기"],
        [f"{lever}|unchanged|현 수준|시장|단기"],
    ]
    return {
        "from": [source],
        "label": f"{source} 후보",
        "question": f"{source} 질문",
        "rationale": f"{source}가 Scenario와 JKM을 구분하는 근거",
        "lever": lever,
        "axis": "duration",
        "choices": [
            {
                "label": "확대",
                "states": choice_states[0],
                "pressure": "bullish",
                "why": "관측 사실을 기반으로 미래 상태가 확대되어 JKM 압력이 커지는 가정",
            },
            {
                "label": "유지",
                "states": choice_states[1],
                "pressure": "balanced",
                "why": "관측 사실을 기반으로 미래 상태가 유지되어 JKM 압력이 제한되는 가정",
            },
        ],
    }


def test_open_question_pool_warns_on_soft_minimum_without_capping_maximum() -> None:
    undershot = finalize_open_question_pool(_analysis(3))
    preserved = finalize_open_question_pool(_analysis(12))

    assert len(undershot.path_uncertainties) == 3
    assert [warning.code for warning in undershot.validation_warnings] == ["OPEN_QUESTION_TARGET_UNDERSHOT"]
    assert len(preserved.path_uncertainties) == 12
    assert preserved.validation_warnings == []


def test_unused_questions_and_promoted_sources_are_filtered() -> None:
    analysis = _analysis(3)
    diagnostics = analysis.model_dump()
    formal = [{"dimension_id": "d1", "source_uncertainty_ids": ["u1"]}]

    unused = build_unused_impact_analysis(diagnostics, formal)
    available = filter_available_candidates(
        [
            {"dimension_id": "ad_1", "source_uncertainty_ids": ["u2"]},
            {"dimension_id": "ad_2", "source_uncertainty_ids": ["u1"]},
        ],
        dimension_selected=["d1"],
        active_definitions=formal,
    )

    assert [item.uncertainty_id for item in unused.path_uncertainties] == ["u2", "u3"]
    assert [item["dimension_id"] for item in available] == ["ad_1"]


def test_additional_dimension_get_pending_contract() -> None:
    payload = {
        "generation": {"status": "running"},
        "candidates": [],
        "dimension_selected": ["d1"],
        "dimension_definitions": [],
        "updated_at": None,
    }
    with patch(
        "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
        return_value=payload,
    ):
        output = get_additional_dimensions(10)

    assert output.data is not None
    assert output.data.generation_status == "running"
    assert output.data.dimension_definitions.status == "pending"
    assert output.data.available_count == 0


@pytest.mark.parametrize(
    "generation_status",
    ["not_requested", "failed", "interrupted", "discarded"],
)
def test_additional_dimension_get_unavailable_contract(generation_status: str) -> None:
    payload = {
        "generation": {
            "status": generation_status,
            "error_code": "STABLE_ERROR" if generation_status != "not_requested" else None,
        },
        "candidates": [],
        "dimension_selected": [],
        "dimension_definitions": [],
        "updated_at": None,
    }
    with patch(
        "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
        return_value=payload,
    ):
        output = get_additional_dimensions(10)

    assert output.data is not None
    assert output.data.generation_status == generation_status
    assert output.data.dimension_definitions.status == "unavailable"
    assert output.data.dimension_definitions.items == []
    assert output.data.available_count == 0
    assert output.data.error_code == ("STABLE_ERROR" if generation_status != "not_requested" else None)


def test_additional_dimension_get_ready_empty_is_not_an_error() -> None:
    payload = {
        "generation": {"status": "ready"},
        "candidates": [],
        "dimension_selected": [],
        "dimension_definitions": [],
        "updated_at": None,
    }
    with patch(
        "apps.agents.scenario_group_agent.flows.add_dimension.flow.ScenarioGroupService.load_additional_dimensions",
        return_value=payload,
    ):
        output = get_additional_dimensions(10)

    assert output.status == "success"
    assert output.data is not None
    assert output.data.generation_status == "ready"
    assert output.data.dimension_definitions.status == "ready"
    assert output.data.available_count == 0


def test_dimension_value_catalog_accepts_ids_and_unique_legacy_labels() -> None:
    definitions = [
        {
            "dimensionId": "d1",
            "values": [
                {"valueId": "d1_v1", "label": "낮음"},
                {"valueId": "d1_v2", "label": "높음"},
            ],
        },
    ]
    catalog = build_dimension_value_catalog(definitions)

    assert canonicalize_dimension_cells(
        catalog,
        ["d1"],
        {"d1": "d1_v1"},
        allow_label_compatibility=False,
    ) == {"d1": "d1_v1"}
    assert canonicalize_dimension_cells(
        catalog,
        ["d1"],
        {"d1": "높음"},
        allow_label_compatibility=True,
    ) == {"d1": "d1_v2"}


def test_generated_string_fields_use_maximum_only_contract() -> None:
    dimension = V4ReadableDimension.model_validate(
        {
            "from": ["U1"],
            "label": "",
            "question": "",
            "rationale": "",
            "lever": "supply",
            "axis": "duration",
            "choices": [
                {
                    "label": "",
                    "states": ["supply|increase|high|시장|단기"],
                    "pressure": "bullish",
                    "why": "관측 사실에서 공급 증가와 JKM 상승을 연결한 가정",
                },
                {
                    "label": "유지",
                    "states": ["supply|unchanged|same|시장|단기"],
                    "pressure": "balanced",
                    "why": "관측 사실에서 공급 유지와 JKM 보합을 연결한 가정",
                },
            ],
        },
    )
    scenario = V4ReadableScenario.model_validate(
        {
            "title": "",
            "narrative": "가" * 80,
            "choices": ["D1=V1", "D2=V1", "D3=V1"],
            "pressure": "balanced",
            "explanation": "나" * 30,
            "probability": 50,
        },
    )

    assert dimension.label == ""
    assert dimension.question == ""
    assert scenario.title == ""


def test_generated_string_maximum_boundaries_are_exact() -> None:
    base_dimension = {
        "from": ["U1"],
        "label": "가" * 30,
        "question": "질" * 121,
        "rationale": "나" * 200,
        "lever": "supply",
        "axis": "duration",
        "choices": [
            {
                "label": "다" * 30,
                "states": ["supply|increase|high|시장|단기"],
                "pressure": "bullish",
                "why": "공급 증가가 JKM 상승으로 연결되는 가정",
            },
            {
                "label": "유지",
                "states": ["supply|unchanged|same|시장|단기"],
                "pressure": "balanced",
                "why": "공급 유지가 JKM 보합으로 연결되는 가정",
            },
        ],
    }
    parsed = V4ReadableDimension.model_validate(base_dimension)
    assert len(parsed.question) == 121

    for path, value in (
        (("label",), "가" * 31),
        (("rationale",), "나" * 201),
        (("choices", 0, "label"), "다" * 31),
    ):
        invalid = {
            **base_dimension,
            "choices": [dict(item) for item in base_dimension["choices"]],
        }
        if len(path) == 1:
            invalid[path[0]] = value
        else:
            invalid[path[0]][path[1]][path[2]] = value
        with pytest.raises(ValueError, match="at most"):
            V4ReadableDimension.model_validate(invalid)

    assert (
        V4ReadableScenario.model_validate(
            {
                "title": "라" * 40,
                "narrative": "가" * 80,
                "choices": ["D1=V1", "D2=V1", "D3=V1"],
                "pressure": "balanced",
                "explanation": "나" * 30,
                "probability": 50,
            },
        ).title
        == "라" * 40
    )
    with pytest.raises(ValueError, match="at most"):
        V4ReadableScenario.model_validate(
            {
                "title": "라" * 41,
                "narrative": "가" * 80,
                "choices": ["D1=V1", "D2=V1", "D3=V1"],
                "pressure": "balanced",
                "explanation": "나" * 30,
                "probability": 50,
            },
        )


def test_independent_interaction_does_not_create_open_question() -> None:
    readable = V4ReadableInteractionAnalysisDraft.model_validate(
        {
            "interactions": [
                {
                    "paths": ["E1-P1", "E2-P1"],
                    "analysis": "두 Event 경로 사이에 추가적인 결합 효과가 없어 JKM 영향은 서로 독립적이다.",
                    "relation": "independent",
                },
            ],
            "openQuestions": [
                {
                    "interaction": 1,
                    "question": "결합 기간은 얼마인가?",
                    "axis": "duration",
                    "lever": "lever_1",
                },
            ],
        },
    )

    merged = merge_v4_readable_interactions(_analysis(2), readable)

    assert merged.interactions[0].relation == "independent"
    assert merged.interaction_uncertainties == []


def test_additional_candidate_hydration_drops_only_invalid_item() -> None:
    def dimension(source: str, lever: str, state: str) -> dict[str, object]:
        return {
            "from": [source],
            "label": f"{source} 후보",
            "question": f"{source} 질문",
            "rationale": "추가 분기 기준",
            "lever": lever,
            "axis": "duration",
            "choices": [
                {
                    "label": "낮음",
                    "states": [state],
                    "pressure": "balanced",
                    "why": "변화가 제한되어 JKM 보합으로 연결되는 가정",
                },
                {
                    "label": "높음",
                    "states": [state],
                    "pressure": "bullish",
                    "why": "변화가 확대되어 JKM 상승으로 연결되는 가정",
                },
            ],
        }

    readable = V4ReadableAdditionalDimensionDesignDraft.model_validate(
        {
            "dimensions": [
                dimension("U1", "lever_1", "lever_1|increase|high|시장|단기"),
                dimension("U2", "lever_2", "invalid-state-token"),
            ],
        },
    )

    candidates = expand_v4_additional_dimension_candidates(
        readable,
        impact_analysis=_analysis(2),
    )

    assert len(candidates) == 1
    assert candidates[0].source_uncertainty_ids == ["u1"]


def test_additional_prompt_and_schema_define_the_state_wire_contract() -> None:
    prompt = build_v4_additional_dimension_user_prompt(
        impact_analysis=_analysis(1).model_dump(),
        impact_levers=[item.model_dump() for item in _catalog(1)],
        selected_definitions=[],
    )
    states_schema = V4ReadableAdditionalDimensionDesignDraft.model_json_schema(by_alias=True)["$defs"][
        "V4ReadableDimensionChoice"
    ]["properties"]["states"]

    for text in (V4_ADDITIONAL_DIMENSION_SYSTEM_PROMPT, prompt, states_schema["description"]):
        assert "lever|direction|level|scope|timeWindow" in text
        assert StateDirection.prompt_values() in text
    assert "states와 why는 초기 Dimension 생성 규칙을 그대로 따릅니다" not in prompt
    assert "Group 441" in V4_ADDITIONAL_DIMENSION_SYSTEM_PROMPT
    assert "Group 441" in prompt


def test_group_441_natural_language_states_are_classified_per_candidate() -> None:
    readable = V4ReadableAdditionalDimensionDesignDraft.model_validate(
        {
            "dimensions": [
                _candidate(
                    "U1",
                    "lever_1",
                    states=[
                        ["LNG 수출 설비로의 가스 유입 증가가 실제 액화설비 가동률 상승으로 이어지는 상태"],
                        ["LNG 수출 설비 가동률이 현재 수준에 머무르는 상태"],
                    ],
                ),
            ],
        },
    )

    result = hydrate_additional_dimension_candidates(
        readable,
        impact_analysis=_analysis(1),
        impact_levers=_catalog(1),
    )

    assert result.input_candidate_count == 1
    assert result.valid_candidates == []
    assert [item.reason_code for item in result.rejected_candidates] == ["INVALID_STATE_FORMAT"]


def test_invalid_candidate_does_not_reserve_its_source_for_a_later_valid_candidate() -> None:
    readable = V4ReadableAdditionalDimensionDesignDraft.model_validate(
        {
            "dimensions": [
                _candidate(
                    "U1",
                    "lever_1",
                    states=[["자연어 상태"], ["또 다른 자연어 상태"]],
                ),
                _candidate("U1", "lever_1"),
            ],
        },
    )

    result = hydrate_additional_dimension_candidates(
        readable,
        impact_analysis=_analysis(1),
        impact_levers=_catalog(1),
    )

    assert result.input_candidate_count == 2
    assert len(result.valid_candidates) == 1
    assert result.valid_candidates[0].source_uncertainty_ids == ["u1"]
    assert [item.reason_code for item in result.rejected_candidates] == ["INVALID_STATE_FORMAT"]


def test_additional_hydration_preserves_valid_candidate_and_reports_invalid_candidate() -> None:
    readable = V4ReadableAdditionalDimensionDesignDraft.model_validate(
        {
            "dimensions": [
                _candidate("U1", "lever_1"),
                _candidate("U2", "lever_2", states=[["잘못된 상태"], ["잘못된 상태 2"]]),
            ],
        },
    )

    result = hydrate_additional_dimension_candidates(
        readable,
        impact_analysis=_analysis(2),
        impact_levers=_catalog(2),
    )

    assert result.input_candidate_count == 2
    assert len(result.valid_candidates) == 1
    assert len(result.rejected_candidates) == 1
    assert result.rejection_reason_codes == ["INVALID_STATE_FORMAT"]

