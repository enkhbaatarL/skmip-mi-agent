from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from unittest.mock import MagicMock

from pydantic import ValidationError
import pytest
from sqlalchemy.dialects import mysql

from apps.agents.scenario_group_agent.schemas.event_search_document import EventSearchDocument
from apps.agents.scenario_group_agent.utils.event_search_document import (
    build_event_search_documents,
    build_event_search_text,
)
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.event.repository import EventRepository
from apps.persistence.event.schema import EventSearchSource
from scripts.export_event_search_documents import export_sample, main, select_sample_events


def _source(**changes: object) -> EventSearchSource:
    data = {
        "mi_event_id": 7,
        "one_line_summary": "제목: 설비 가동 차질",
        "search_text": "요약: 복구 시점은 미확인이다.",
        "key_bullets_json": {"bullets": ["기관 A는 2027년 5월 복구를 전망했다.", "감소량은 1.5 bcm이다."]},
        "tags_json": {"tags": ["LNG", "Freeport"]},
        "detail_analysis": "# 상세 분석\r\n\r\n기관 B는 2027년 6월까지 차질을 예상한다.\r\n출처: https://example.com/report",
        "numeric_facts_md": "| 항목 | 값 |\n| --- | --- |\n| 공급 변화 | -1.5 bcm |",
        "institution_view_synthesis": "기관별 복구 시점 전망은 상충한다.",
        "publish_status": "PUBLISHED",
        "del_yn": "N",
        "occurred_at": "2026-10-01T12:00:00",
        "mod_dtm": "2026-10-29T10:00:00",
        "source_record_ids": [14, 13, 14],
    }
    data.update(changes)
    return EventSearchSource.model_validate(data)


def test_document_preserves_source_claims_quantities_links_and_db_title_mapping() -> None:
    document = build_event_search_documents(_source())[0]

    assert document.text.startswith("제목:\n제목: 설비 가동 차질\n\n요약:\n요약: 복구 시점은 미확인이다.")
    assert "기관 A는 2027년 5월 복구를 전망했다." in document.text
    assert "기관 B는 2027년 6월까지 차질을 예상한다." in document.text
    assert "-1.5 bcm" in document.text
    assert "https://example.com/report" in document.text
    assert "기관별 복구 시점 전망은 상충한다." in document.text
    assert "\r" not in document.text
    assert document.metadata.tags == ["LNG", "Freeport"]
    assert document.metadata.source_record_ids == [13, 14]
    assert document.metadata.occurred_at == datetime.fromisoformat("2026-10-01T12:00:00")
    assert document.metadata.occurred_at.tzinfo is None


@pytest.mark.parametrize("body", ["긴문장" * 200, ("기관 A의 전망이다. " * 30 + "\n\n") * 5])
def test_chunk_boundaries_cover_every_character_without_overlap_or_loss(body: str) -> None:
    source = _source(detail_analysis=body)
    documents = build_event_search_documents(source, max_content_chars=128)
    canonical, _, _ = build_event_search_text(source)

    assert len(documents) > 1
    assert "".join(document.content for document in documents) == canonical
    assert all(len(document.content) <= 128 for document in documents)
    assert all(document.metadata.event_id == 7 for document in documents)
    assert all(document.metadata.chunk_count == len(documents) for document in documents)
    assert len({document.document_id for document in documents}) == len(documents)
    assert documents[-1].metadata.content_end == len(canonical)
    for index, document in enumerate(documents):
        assert document.metadata.chunk_index == index
        assert document.content == canonical[document.metadata.content_start : document.metadata.content_end]
        assert document.text.endswith(document.content)
        if index:
            assert document.metadata.content_start == documents[index - 1].metadata.content_end
            assert document.text.startswith("제목: 제목: 설비 가동 차질")


@pytest.mark.parametrize("value", [["전망 보존"], {"bullets": ["전망 보존"]}, '{"bullets":["전망 보존"]}'])
def test_supported_json_shapes_preserve_bullets(value: object) -> None:
    text, _, warnings = build_event_search_text(_source(key_bullets_json=value))

    assert "전망 보존" in text
    assert warnings == []


@pytest.mark.parametrize("value", ['{"broken":', {"bullets": ["본문"], "extra": "별도 근거"}, ["본문", {"value": 3}]])
def test_nonstandard_json_is_kept_with_diagnostics(value: object) -> None:
    source = _source(key_bullets_json=value)
    text, _, warnings = build_event_search_text(source)

    assert warnings
    if isinstance(value, str):
        assert value in text
    elif isinstance(value, dict):
        assert "별도 근거" in text
    else:
        assert '"value": 3' in text


@pytest.mark.parametrize("changes", [{"publish_status": "DRAFT"}, {"publish_status": None}, {"del_yn": "Y"}])
def test_unpublished_and_deleted_sources_are_rejected(changes: dict[str, object]) -> None:
    with pytest.raises(MIBaseError):
        build_event_search_documents(_source(**changes))


def test_missing_dates_and_assumptions_are_not_filled_or_promoted_to_facts() -> None:
    document = build_event_search_documents(_source(occurred_at=None, detail_analysis="설비 복구를 가정한다."))[0]

    assert document.metadata.occurred_at is None
    assert "missing_occurred_at" in document.metadata.warnings
    assert "contains_assumption_or_test_marker" in document.metadata.warnings
    assert "설비 복구를 가정한다." in document.text


def test_stable_ids_and_hashes_distinguish_text_and_metadata_updates() -> None:
    original = build_event_search_documents(_source())[0]
    same = build_event_search_documents(_source())[0]
    changed = build_event_search_documents(_source(detail_analysis="수정된 기관 전망"))[0]
    metadata_only = build_event_search_documents(_source(mod_dtm="2026-10-30T10:00:00"))[0]

    assert original == same
    assert original.document_id == changed.document_id == metadata_only.document_id
    assert original.metadata.source_hash != changed.metadata.source_hash
    assert original.metadata.source_hash != metadata_only.metadata.source_hash
    assert original.metadata.text_hash == metadata_only.metadata.text_hash
    assert original.metadata.text_hash != changed.metadata.text_hash


def test_sample_includes_short_long_and_forecast_examples() -> None:
    sources = [
        _source(mi_event_id=1, detail_analysis="짧음"),
        _source(mi_event_id=2, detail_analysis="길다" * 100),
        _source(mi_event_id=3),
    ]

    assert {source.mi_event_id for source in select_sample_events(sources, 3)} == {1, 2, 3}


def test_repository_filters_published_active_events_and_retains_nullable_types() -> None:
    session = MagicMock()
    source_result = MagicMock()
    source_result.mappings.return_value.all.return_value = [{"mi_event_id": 7}]
    record_result = MagicMock()
    record_result.all.return_value = [(7, 14), (7, 13), (7, 14)]
    session.execute.side_effect = [source_result, record_result]

    rows = EventRepository(session=session).list_search_sources(limit=30, event_ids=[7])

    sql = str(
        session.execute.call_args_list[0]
        .args[0]
        .compile(dialect=mysql.dialect(), compile_kwargs={"literal_binds": True}),
    )
    assert "publish_status = 'PUBLISHED'" in sql
    assert "del_yn = 'N'" in sql
    assert "mi_event_id IN (7)" in sql
    assert "LIMIT 30" in sql
    assert " JOIN " not in sql
    assert rows[0]["source_record_ids"] == [13, 14]
    session.commit.assert_not_called()


def test_jsonl_export_roundtrip_and_offline_replay(tmp_path: Path) -> None:
    first_dir = tmp_path / "first"
    report = export_sample([_source()], output_dir=first_dir, max_content_chars=128)
    documents = [
        EventSearchDocument.model_validate_json(line)
        for line in (first_dir / "documents.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    restored = EventSearchSource.model_validate_json(
        (first_dir / "source_events.jsonl").read_text(encoding="utf-8").strip(),
    )

    assert restored == _source()
    assert report["coverage_passed"] is True
    assert report["document_count"] == len(documents)
    assert json.loads((first_dir / "report.json").read_text(encoding="utf-8"))["event_count"] == 1
    assert (
        main(["--input-jsonl", str(first_dir / "source_events.jsonl"), "--output-dir", str(tmp_path / "replay")]) == 0
    )


def test_duplicate_sources_and_reusing_output_directory_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(MIBaseError):
        export_sample([_source(), _source()], output_dir=tmp_path / "duplicate")
    with pytest.raises(FileExistsError):
        export_sample([_source()], output_dir=tmp_path)


def test_invalid_event_id_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _source(mi_event_id=0)
