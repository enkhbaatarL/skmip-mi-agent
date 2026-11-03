from __future__ import annotations

from pydantic import ValidationError
import pytest

from apps.agents.scenario_group_agent.prompts.event_recommendation import (
    EventRecommendationItem,
    EventRecommendationOutput,
)
from apps.agents.scenario_group_agent.utils.event_recommendation import (
    prepare_event_recommendation_candidates,
    validate_event_recommendation_output,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventPayload


def _event(event_id: int | str) -> EventPayload:
    return EventPayload(
        mi_event_id=event_id,
        event_title_ko="LNG 시장 변화",
        one_line_summary="기관 A는 겨울 수요 증가를 전망했다.",
        key_bullets=["영향 기간은 미확인이다."],
        detail_analysis="설비 가동이 중단됐다. 복구 일정은 발표되지 않았다.",
    )


def _item(event_id: int) -> EventRecommendationItem:
    return EventRecommendationItem(
        mi_event_id=event_id,
        relation_type="supply_demand",
        impact_path="공급 차질과 수요 변화가 시장 수급에 함께 영향을 줄 가능성이 있다.",
        period_assessment="unknown",
        period_reason="영향 기간이 명시되지 않았다.",
        incremental_information="수요 측 불확실성을 추가한다.",
        scenario_question="수요 변화가 공급 차질을 증폭할 것인가?",
        source_evidence="설비 가동이 중단됐다.",
        candidate_evidence="기관 A는 겨울 수요 증가를 전망했다.",
        reason="공급과 수요 조건을 함께 검토할 수 있다.",
    )


def test_candidates_exclude_self_ineligible_explicit_exclusions_and_duplicate_ids() -> None:
    source = _event(1)
    candidates = prepare_event_recommendation_candidates(
        source,
        [_event(1), _event(2), _event("2"), _event(3), _event(4)],
        eligible_event_ids=frozenset({1, 2, 4}),
        excluded_event_ids=frozenset({4}),
    )

    assert [event.mi_event_id for event in candidates] == [2]


def test_ineligible_source_stops_before_prompt_creation() -> None:
    with pytest.raises(MIBaseError) as exc_info:
        prepare_event_recommendation_candidates(_event(1), [_event(2)], eligible_event_ids=frozenset({2}))

    assert exc_info.value.error_code == ErrorCode.RDB_ACCESS_DENIED


@pytest.mark.parametrize("count", [0, 1, 2])
def test_zero_to_two_recommendations_are_valid(count: int) -> None:
    candidates = [_event(2), _event(3)]
    output = EventRecommendationOutput(
        items=[_item(event_id) for event_id in range(2, count + 2)],
        selection_reason="후보 근거를 비교한 결과다.",
    )

    result = validate_event_recommendation_output(output, source_event=_event(1), candidates=candidates)

    assert len(result.items) == count


def test_more_than_two_recommendations_are_rejected() -> None:
    with pytest.raises(ValidationError):
        EventRecommendationOutput(items=[_item(2), _item(3), _item(4)], selection_reason="조합 선정 이유")


@pytest.mark.parametrize("event_ids", [(1,), (99,), (2, 2)])
def test_self_unknown_and_duplicate_recommendations_are_rejected(event_ids: tuple[int, ...]) -> None:
    output = EventRecommendationOutput(items=[_item(event_id) for event_id in event_ids], selection_reason="선정 이유")

    with pytest.raises(MIBaseError) as exc_info:
        validate_event_recommendation_output(output, source_event=_event(1), candidates=[_event(2)])

    assert exc_info.value.error_code == ErrorCode.LLM_INVALID_RESPONSE_ERROR


@pytest.mark.parametrize("field", ["source_evidence", "candidate_evidence"])
def test_fabricated_evidence_is_rejected(field: str) -> None:
    payload = _item(2).model_dump()
    payload[field] = "존재하지 않는 원문 인용"
    output = EventRecommendationOutput(
        items=[EventRecommendationItem.model_validate(payload)],
        selection_reason="선정 이유",
    )

    with pytest.raises(MIBaseError) as exc_info:
        validate_event_recommendation_output(output, source_event=_event(1), candidates=[_event(2)])

    assert exc_info.value.error_code == ErrorCode.LLM_INVALID_RESPONSE_ERROR


def test_quote_cannot_be_stitched_across_different_source_fields() -> None:
    source = _event(1)
    source.event_title_ko = "앞부분"
    source.one_line_summary = "뒷부분"
    payload = _item(2).model_dump()
    payload["source_evidence"] = "앞부분뒷부분"
    output = EventRecommendationOutput(
        items=[EventRecommendationItem.model_validate(payload)],
        selection_reason="선정 이유",
    )

    with pytest.raises(MIBaseError):
        validate_event_recommendation_output(output, source_event=source, candidates=[_event(2)])


@pytest.mark.parametrize("field", ["reason", "period_reason", "candidate_evidence", "scenario_question"])
def test_whitespace_only_required_fields_are_rejected(field: str) -> None:
    payload = _item(2).model_dump()
    payload[field] = "  "

    with pytest.raises(ValidationError):
        EventRecommendationItem.model_validate(payload)
