# ruff: noqa: S101, SLF001

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.agents.scenario_group_agent.schemas.endpoint import EventDetailOut
from apps.persistence.event import service as event_service
from apps.persistence.event.repository import EventRepository


def test_event_repository_parses_direct_and_wrapped_json_lists() -> None:
    repository = EventRepository(session=Mock())

    assert repository._parse_json_list(["a", "b"], wrapper_key="bullets") == ["a", "b"]
    assert repository._parse_json_list({"bullets": ["a", "b"]}, wrapper_key="bullets") == ["a", "b"]
    assert repository._parse_json_list('{"tags": ["lng", "europe"]}', wrapper_key="tags") == [
        "lng",
        "europe",
    ]


def test_event_repository_rejects_unexpected_json_wrapper() -> None:
    repository = EventRepository(session=Mock())

    assert repository._parse_json_list({"unexpected": ["a"]}, wrapper_key="bullets") == []
    assert repository._parse_json_list('"comma,separated"', wrapper_key="tags") == []


def test_event_repository_builds_context_from_operational_wrapper_shape() -> None:
    repository = EventRepository(session=Mock())
    event = SimpleNamespace(
        mi_event_id=1116,
        event_type_l2_id=3,
        event_title="EemsEnergyTerminal 확장 cFID 발표",
        one_line_summary="중장기 수입능력 확대 요인",
        key_bullets_json={"bullets": ["조건부 최종투자결정을 발표함.", "인허가 취득을 전제로 함."]},
        detail_analysis="상세 분석은 prompt context에 사용하지 않음.",
        tags_json={"tags": ["EemsEnergyTerminal", "Gasunie", "Vopak"]},
        occurred_at=None,
        record_maps=[],
        crt_dtm=None,
        mod_dtm=None,
        latest_record_first_created=None,
        oldest_record_first_created=None,
        new_yn="Y",
        signal_yn="Y",
        signal_confidence=None,
        signal_reason=None,
        scenario_suggest_yn="N",
        scenario_suggest_reason=None,
        type_l2=SimpleNamespace(
            event_type_l2_id=3,
            level_2_code="new_terminal_cod_rampup_change",
            level_2_label="신규 터미널 COD 및 램프업 변화",
            level_1=SimpleNamespace(
                event_type_l1_id=1,
                level_1_code="supply",
                level_1_label="공급",
            ),
        ),
    )

    payload = repository._event_to_pipeline_dict(event)

    assert payload["key_bullets"] == ["조건부 최종투자결정을 발표함.", "인허가 취득을 전제로 함."]
    assert payload["tags"] == ["EemsEnergyTerminal", "Gasunie", "Vopak"]
    assert payload["occurred_at"] == ""

    backoffice_payload = repository._event_to_backoffice_dict(event)

    assert "market_impacts" not in backoffice_payload


def test_event_detail_schema_preserves_context_fields() -> None:
    output = EventDetailOut.model_validate(
        {
            "event": {
                "mi_event_id": 1116,
                "scenario_action_state": {
                    "type": "create",
                    "label": "생성하기",
                },
                "key_bullets": ["조건부 최종투자결정을 발표함."],
                "tags": ["EemsEnergyTerminal", "Gasunie"],
                "detail_analysis": "상세 분석",
                "source_mi_record_ids": [2271, 2281],
                "created_at": "2026-06-19T23:00:29",
                "updated_at": "2026-07-02T13:16:36",
                "language": "ko",
                "market_impacts": {
                    "JKM": {"direction": "neutral", "label": "S"},
                },
            },
            "scenario_template": {"event_type_l2_id": 3},
            "source": {"type": "agent_db"},
        },
    ).model_dump(by_alias=True)

    assert output["event"]["keyBullets"] == ["조건부 최종투자결정을 발표함."]
    assert output["event"]["tags"] == ["EemsEnergyTerminal", "Gasunie"]
    assert output["event"]["sourceMiRecordIds"] == [2271, 2281]
    assert "marketImpacts" not in output["event"]


def test_event_detail_resolves_groups_through_multi_event_relations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group_repository = Mock()
    group_repository.fetch_by_any_event_id.return_value = None
    monkeypatch.setattr(
        event_service,
        "ScenarioGroupRepository",
        lambda session: group_repository,
    )
    monkeypatch.setattr(
        event_service,
        "ScenarioRepository",
        lambda session: Mock(),
    )
    monkeypatch.setattr(
        event_service,
        "SignpostRepository",
        lambda session: Mock(),
    )

    payload = event_service.EventService()._with_related_group(
        {"mi_event_id": 1116},
        Mock(),
    )

    group_repository.fetch_by_any_event_id.assert_called_once_with(1116)
    assert payload["related_scenario_group"] is None
    assert payload["scenario_action_state"]["type"] == "create"
