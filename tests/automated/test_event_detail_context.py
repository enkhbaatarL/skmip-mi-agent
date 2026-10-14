# ruff: noqa: S101, SLF001

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from apps.agents.scenario_group_agent.schemas.endpoint import EventDetailOut
from apps.persistence.event.models import MiEventModel, MiEventSnapshotModel
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
        one_line_summary="EemsEnergyTerminal 확장 cFID 발표",
        search_text="중장기 수입능력 확대 요인",
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


def test_event_repository_serializes_unclassified_event_without_type_error() -> None:
    repository = EventRepository(session=Mock())
    event = SimpleNamespace(
        mi_event_id=1117,
        event_type_l2_id=None,
        one_line_summary="분류 대기 이벤트",
        search_text="분류 전 검색 문맥",
        key_bullets_json={"bullets": ["분류 전 근거"]},
        detail_analysis="분류 전 상세 분석",
        tags_json=None,
        occurred_at=None,
        record_maps=[],
        crt_dtm=None,
        mod_dtm=None,
        latest_record_first_created=None,
        oldest_record_first_created=None,
    )

    payload = repository._event_to_core_pipeline_dict(event)

    assert payload["event_type_l2_id"] is None
    assert payload["event_title_ko"] == "분류 대기 이벤트"
    assert payload["one_line_summary"] == "분류 전 검색 문맥"


def test_event_models_match_nullable_v46_event_type_contract() -> None:
    assert MiEventModel.__table__.c.event_type_l2_id.nullable is True
    assert MiEventSnapshotModel.__table__.c.event_type_l2_id.nullable is True


def test_event_repository_serializes_unclassified_snapshot_without_catalog_lookup() -> None:
    repository = EventRepository(session=Mock())
    repository.fetch_event_type_by_l2_id = Mock()
    repository.fetch_source_record_ids = Mock(return_value=[])
    snapshot = SimpleNamespace(
        mi_event_id=1118,
        event_type_l2_id=None,
        one_line_summary="분류 대기 스냅샷",
        search_text="스냅샷 검색 문맥",
        key_bullets_json={"bullets": ["분류 전 근거"]},
        detail_analysis="스냅샷 상세 분석",
        tags_json=None,
        occurred_at=None,
        event_crt_dtm=None,
        event_mod_dtm=None,
        latest_record_first_created=None,
        oldest_record_first_created=None,
    )

    payload = repository._snapshot_to_pipeline_dict(snapshot)

    assert payload["event_type_l2_id"] is None
    assert payload["event_type"]["event_type_l2_id"] is None
    repository.fetch_event_type_by_l2_id.assert_not_called()


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
