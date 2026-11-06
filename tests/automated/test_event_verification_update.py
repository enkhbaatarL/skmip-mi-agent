from __future__ import annotations

# ruff: noqa: S101, SLF001, DTZ001
import asyncio
from collections.abc import Iterator
from datetime import datetime
import json
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    DefaultClause,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    event,
    func,
    select,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.scenario_group_agent.persistence import event_verification_update_service as orchestration
from apps.agents.scenario_group_agent.persistence.event_verification_service import (
    VerificationEvidence,
    VerificationSource,
)
from apps.agents.scenario_group_agent.prompts.event_verification_update import EventUpdateProposal
from apps.agents.scenario_group_agent.routers.events import router
from apps.agents.scenario_group_agent.schemas.api.event_verification_updates import EventVerificationUpdateIn
from apps.agents.scenario_group_agent.schemas.api.event_verifications import (
    EventVerificationCheck,
    EventVerificationItem,
    VerificationAspect,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.middleware.exception_handler import register_exception_handlers
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.models import MiEventModel, MiEventSnapshotModel
from apps.persistence.event.repository import EventRepository
from apps.persistence.event.service import EventService
from apps.persistence.event.update_repository import EventUpdateRepository


SOURCE_URL = "https://example.com/news/confirmed"
EVIDENCE = "운영사는 2026년 11월 1일 가동 계획을 12월로 연기했다고 발표했다."
OLD_DATE = datetime(2020, 1, 1)


@pytest.fixture
def update_logs() -> Iterator[list[str]]:
    messages: list[str] = []
    sink = orchestration.logger.add(
        lambda message: messages.append(message.record["message"]),
        filter=lambda record: record["message"].startswith("[EVENT_VERIFICATION_UPDATE]"),
    )
    try:
        yield messages
    finally:
        orchestration.logger.remove(sink)


@pytest.fixture
def db(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def collation(connection: object, record: object) -> None:
        connection.create_collation("utf8mb4_bin", lambda a, b: (a > b) - (a < b))

    metadata = MetaData()
    Table("tmm_mi_event_type_l2_m", metadata, Column("event_type_l2_id", Integer, primary_key=True))
    tables = []
    for model in (MiEventModel, MiEventSnapshotModel):
        table = model.__table__.to_metadata(metadata)
        for column in table.c:
            column.type = column.type.as_generic()
            if column.name in {"crt_dtm", "mod_dtm"}:
                column.server_default = DefaultClause(text("CURRENT_TIMESTAMP"))
        table.append_column(Column("event_revision", Integer, nullable=False, server_default="0"))
        table.append_column(Column("summary_json", JSON, nullable=True))
        tables.append(table)
    events, snapshots = tables
    snapshots.append_column(Column("mod_usr_logn_id", String(100), nullable=False, server_default="system"))
    snapshots.append_column(Column("mod_dtm", DateTime, nullable=False, server_default=func.current_timestamp()))
    snapshots.append_column(Column("del_yn", String(1), nullable=False, server_default="N"))
    metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    from apps.common.configs.database.sync_database import connection

    monkeypatch.setattr(connection, "get_sync_session", factory)
    original = {
        "mi_event_id": 1,
        "event_type_l2_id": 7,
        "one_line_summary": "10월 가동 예정",
        "key_bullets_json": {"bullets": ["10월 가동"], "format": "v1"},
        "detail_analysis": "가동 예정일은 10월이다.",
        "numeric_facts_md": "연간 5 mtpa",
        "tags_json": ["LNG"],
        "occurred_at": OLD_DATE,
        "latest_record_first_created": OLD_DATE,
        "oldest_record_first_created": OLD_DATE,
        "institution_view_synthesis": "기관 전망",
        "estimated_impact_id": "JKM",
        "signal_yn": "Y",
        "signal_confidence": 0.8,
        "signal_reason": "공급 변화",
        "scenario_suggest_yn": "Y",
        "scenario_suggest_reason": "가동 일정",
        "new_yn": "Y",
        "publish_status": "PUBLISHED",
        "del_yn": "N",
        "crt_usr_logn_id": "creator",
        "mod_usr_logn_id": "previous-editor",
        "crt_dtm": OLD_DATE,
        "mod_dtm": OLD_DATE,
        "event_revision": 9,
        "summary_json": {"original": "preserve extension columns"},
    }
    original["search_text"] = "10월 가동 계획"
    with factory.begin() as session:
        session.execute(events.insert().values(**original))
    yield SimpleNamespace(
        service=EventService(),
        factory=factory,
        events=events,
        snapshots=snapshots,
        engine=engine,
    )
    engine.dispose()


def _row(db: SimpleNamespace) -> dict[str, object]:
    with db.factory() as session:
        return dict(session.execute(select(db.events)).mappings().one())


def _snapshots(db: SimpleNamespace) -> list[dict[str, object]]:
    with db.factory() as session:
        return [
            dict(row)
            for row in session.execute(select(db.snapshots).order_by(db.snapshots.c.mi_event_snapshot_id)).mappings()
        ]


def test_snapshot_copies_complete_preimage_and_audit_defaults(db: SimpleNamespace) -> None:
    before = _row(db)
    context = db.service.prepare_verification_update(1)
    result = db.service.apply_verification_update(
        1,
        context.fingerprint,
        {"one_line_summary": "12월로 가동 연기"},
        "actor",
        "검증 후 일정 수정",
    )
    snapshot = _snapshots(db)[0]
    assert snapshot["snapshot_version_no"] == 1
    assert snapshot["previous_mi_event_snapshot_id"] is None
    assert snapshot["changed_fields_json"] == []
    assert snapshot["update_trigger_cd"] == "LLM_VALIDATION_UPDATE"
    assert snapshot["update_reason"] == "검증 후 일정 수정"
    assert snapshot["crt_usr_logn_id"] == snapshot["mod_usr_logn_id"] == "actor"
    assert snapshot["del_yn"] == "N"
    assert snapshot["crt_dtm"] is not None
    assert snapshot["mod_dtm"] is not None
    audit = {
        "crt_usr_logn_id": "event_crt_usr_logn_id",
        "mod_usr_logn_id": "event_mod_usr_logn_id",
        "crt_dtm": "event_crt_dtm",
        "mod_dtm": "event_mod_dtm",
        "del_yn": "event_del_yn",
    }
    for name, value in before.items():
        target = audit.get(name, name)
        if target in snapshot:
            assert snapshot[target] == value, name
    assert _row(db)["one_line_summary"] == "12월로 가동 연기"
    assert _row(db)["mod_usr_logn_id"] == "actor"
    assert _row(db)["new_yn"] == "N"
    assert result.changed_fields == ["one_line_summary"]
    assert result.snapshot_id == snapshot["mi_event_snapshot_id"]


def test_version_chain_and_only_actual_content_changes(db: SimpleNamespace) -> None:
    first = db.service.prepare_verification_update(1)
    first_result = db.service.apply_verification_update(1, first.fingerprint, {"one_line_summary": "수정 1"}, "a", "r")
    second = db.service.prepare_verification_update(1)
    result = db.service.apply_verification_update(
        1,
        second.fingerprint,
        {"one_line_summary": "수정 1", "key_bullets_json": ["12월 가동"]},
        "b",
        "r2",
    )
    snapshots = _snapshots(db)
    assert result.snapshot_version_no == 2
    assert result.previous_snapshot_id == first_result.snapshot_id
    assert snapshots[1]["one_line_summary"] == "수정 1"
    assert snapshots[1]["changed_fields_json"] == ["key_bullets_json"]
    assert snapshots[1]["key_bullets_json"] == {"bullets": ["10월 가동"], "format": "v1"}
    assert _row(db)["key_bullets_json"] == {"bullets": ["12월 가동"], "format": "v1"}


def test_noop_and_stale_updates_do_not_create_snapshots(db: SimpleNamespace) -> None:
    context = db.service.prepare_verification_update(1)
    result = db.service.apply_verification_update(
        1,
        context.fingerprint,
        {"one_line_summary": "10월 가동 예정"},
        "a",
        "r",
    )
    assert result.snapshot_id is None
    assert _snapshots(db) == []
    # Even a writer that forgets mod_dtm is caught by the full-row fingerprint.
    with db.factory.begin() as session:
        session.execute(db.events.update().values(detail_analysis="동시에 다른 사용자가 수정"))
    with pytest.raises(MIBaseError) as exc:
        db.service.apply_verification_update(1, context.fingerprint, {"one_line_summary": "12월"}, "a", "r")
    assert exc.value.error_code == ErrorCode.EVENT_UPDATE_STALE
    assert _snapshots(db) == []


@pytest.mark.parametrize("failure", ["snapshot", "event"])
def test_transaction_rolls_back_on_either_write_failure(db: SimpleNamespace, failure: str) -> None:
    before = _row(db)
    context = db.service.prepare_verification_update(1)
    ddl = (
        "CREATE TRIGGER reject_write BEFORE INSERT ON tmm_mi_mievent_snapshot_m BEGIN SELECT RAISE(ABORT, 'test'); END"
        if failure == "snapshot"
        else "CREATE TRIGGER reject_write BEFORE UPDATE ON tmm_mi_mievent_m BEGIN SELECT RAISE(ABORT, 'test'); END"
    )
    with db.engine.begin() as connection:
        connection.execute(text(ddl))
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db.service.apply_verification_update(1, context.fingerprint, {"one_line_summary": "12월"}, "a", "r")
    assert _snapshots(db) == []
    assert _row(db) == before


@pytest.mark.parametrize("patch", [{"del_yn": "Y"}, {"one_line_summary": "x" * 301}, {"key_bullets_json": []}])
def test_persistence_rejects_invalid_changes(db: SimpleNamespace, patch: dict[str, object]) -> None:
    context = db.service.prepare_verification_update(1)
    with pytest.raises(MIBaseError):
        db.service.apply_verification_update(1, context.fingerprint, patch, "a", "r")
    assert _snapshots(db) == []


def test_current_title_and_search_context_are_updated_and_preserved_separately(db: SimpleNamespace) -> None:
    context = db.service.prepare_verification_update(1)
    assert context.source.one_line_summary == "10월 가동 예정"
    assert context.source.search_text == "10월 가동 계획"
    assert "event_title" not in context.content
    db.service.apply_verification_update(
        1,
        context.fingerprint,
        {"one_line_summary": "12월 가동", "search_text": "운영사 가동 계획 연기"},
        "a",
        "r",
    )
    snapshot = _snapshots(db)[0]
    assert snapshot["one_line_summary"] == "10월 가동 예정"
    assert snapshot["search_text"] == "10월 가동 계획"
    current = _row(db)
    assert current["one_line_summary"] == "12월 가동"
    assert current["search_text"] == "운영사 가동 계획 연기"


@pytest.mark.parametrize("table_name", ["tmm_mi_mievent_m", "tmm_mi_mievent_snapshot_m"])
def test_missing_current_search_column_rejected(db: SimpleNamespace, table_name: str) -> None:
    statements = {
        "tmm_mi_mievent_m": "ALTER TABLE tmm_mi_mievent_m DROP COLUMN search_text",
        "tmm_mi_mievent_snapshot_m": "ALTER TABLE tmm_mi_mievent_snapshot_m DROP COLUMN search_text",
    }
    with db.engine.begin() as connection:
        connection.execute(text(statements[table_name]))
    with pytest.raises(MIBaseError) as exc:
        db.service.prepare_verification_update(1)
    assert exc.value.error_code == ErrorCode.EVENT_UPDATE_SCHEMA_ERROR


def test_deleted_unpublished_missing_and_old_client_version(db: SimpleNamespace) -> None:
    with pytest.raises(MIBaseError) as exc:
        db.service.prepare_verification_update(1, datetime(2019, 1, 1))
    assert exc.value.error_code == ErrorCode.EVENT_UPDATE_STALE
    with pytest.raises(MIBaseError) as exc:
        db.service.prepare_verification_update(999)
    assert exc.value.error_code == ErrorCode.ENTITY_NOT_FOUND
    for changes in ({"publish_status": "DRAFT"}, {"publish_status": "PUBLISHED", "del_yn": "Y"}):
        with db.factory.begin() as session:
            session.execute(db.events.update().values(**changes))
        with pytest.raises(MIBaseError) as exc:
            db.service.prepare_verification_update(1)
        assert exc.value.error_code == ErrorCode.ENTITY_NOT_FOUND


def test_snapshot_insert_precedes_update_and_parent_uses_mysql_lock(db: SimpleNamespace) -> None:
    context = db.service.prepare_verification_update(1)
    statements = []

    @event.listens_for(db.engine, "before_cursor_execute")
    def capture(conn: object, cursor: object, statement: str, parameters: object, ctx: object, many: object) -> None:
        statements.append(statement)

    db.service.apply_verification_update(1, context.fingerprint, {"one_line_summary": "12월"}, "a", "r")
    writes = [stmt for stmt in statements if stmt.startswith(("INSERT", "UPDATE"))]
    assert writes[0].startswith("INSERT INTO tmm_mi_mievent_snapshot_m")
    assert writes[1].startswith("UPDATE tmm_mi_mievent_m")
    with db.factory() as session:
        repo = EventUpdateRepository(session)
        captured = []
        original = session.execute

        def execute(statement: object, *args: object, **kwargs: object) -> object:
            captured.append(str(statement.compile(dialect=mysql.dialect())))
            return original(statement, *args, **kwargs)

        session.execute = execute
        repo.read_event(1, lock=True)
        assert "FOR UPDATE" in captured[0]


def test_preupdate_snapshot_not_selected_for_new_scenario(db: SimpleNamespace) -> None:
    context = db.service.prepare_verification_update(1)
    result = db.service.apply_verification_update(1, context.fingerprint, {"one_line_summary": "12월"}, "a", "r")
    with db.factory() as session:
        assert EventRepository(session).fetch_latest_snapshot_id(1) is None
    current = _row(db)
    with db.factory.begin() as session:
        # SQLite stores CURRENT_TIMESTAMP without fractional digits; bind both timestamps identically.
        session.execute(db.events.update().values(mod_dtm=current["mod_dtm"]))
        session.execute(
            db.snapshots.update().values(
                update_trigger_cd="RECORD_INGESTION",
                event_mod_dtm=current["mod_dtm"],
                one_line_summary=current["one_line_summary"],
            ),
        )
    with db.factory() as session:
        assert EventRepository(session).fetch_latest_snapshot_id(1) == result.snapshot_id


def _verification(status: str) -> EventVerificationItem:
    return EventVerificationItem(
        mi_event_id=1,
        title="가동 일정",
        source_updated_at=OLD_DATE,
        status=status,
        reason_code="outdated" if status == "fail" else "verified" if status == "pass" else "no_evidence",
        review="가동 일정을 확인했습니다.",
        links=[SOURCE_URL],
        checks=[
            EventVerificationCheck(
                aspect=aspect,
                verdict="outdated" if status == "fail" and aspect == "freshness" else "matched",
                event_claim="10월 가동",
                finding=EVIDENCE,
                source_urls=[SOURCE_URL],
            )
            for aspect in get_args(VerificationAspect)
        ],
    )


@pytest.fixture
def analysis(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    verifier = SimpleNamespace(
        verify_with_evidence=AsyncMock(
            return_value=VerificationEvidence(
                verification=_verification("fail"),
                sources=[VerificationSource(id=1, url=SOURCE_URL, title="뉴스", content=EVIDENCE)],
            ),
        ),
        compare_evidence=AsyncMock(return_value=_verification("pass")),
    )
    monkeypatch.setattr(orchestration, "EventVerificationService", lambda: verifier)
    settings = SimpleNamespace(
        event_verification_update_timeout_sec=5,
        llm_stream_enabled=False,
        llm_reasoning_effort=None,
    )
    monkeypatch.setattr(orchestration, "get_settings", lambda: settings)
    proposal = EventUpdateProposal.model_validate(
        {
            "reason": "가동 일정 연기 반영",
            "changes": [
                {
                    "field": "one_line_summary",
                    "value": "12월 가동 예정",
                    "reason": "일정 변경",
                    "evidence": [{"source_id": 1, "quote": EVIDENCE}],
                },
            ],
        },
    )
    llm = AsyncMock(return_value=SimpleNamespace(result=proposal))
    monkeypatch.setattr(orchestration, "invoke_llm_structured_output", llm)
    return SimpleNamespace(verifier=verifier, proposal=proposal, llm=llm, settings=settings)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    register_exception_handlers(app)
    return TestClient(app)


@pytest.fixture
def conditional_analysis(analysis: SimpleNamespace) -> SimpleNamespace:
    qualification = "2026년 11월 1일 발표 기준이며 이후 일정 변경 여부는 확인되지 않았습니다."
    post = _verification("pass")
    post.status = "warning"
    post.reason_code = "review_required"
    freshness = next(item for item in post.checks if item.aspect == "freshness")
    freshness.verdict = "caution"
    freshness.caution_reason = "as_of_limitation"
    freshness.qualification_quote = qualification
    freshness.finding = "발표 시점의 사실은 확인되나 이후 상황은 미확인입니다."
    analysis.verifier.compare_evidence.return_value = post
    analysis.proposal.changes.append(
        analysis.proposal.changes[0].model_copy(update={"field": "detail_analysis", "value": EVIDENCE + qualification}),
    )
    return analysis


def test_as_of_warning_saved_with_snapshot_and_warning_audit(
    db: SimpleNamespace,
    conditional_analysis: SimpleNamespace,
    client: TestClient,
    update_logs: list[str],
) -> None:
    before = _row(db)
    response = client.post("/events/1/verification-updates", json={"actorUsrLognId": "actor"})
    assert response.status_code == 200
    result = response.json()
    assert result["updateStatus"] == "updated"
    assert result["postVerification"]["status"] == "warning"
    assert "주의" in result["message"]
    freshness = next(item for item in result["postVerification"]["checks"] if item["aspect"] == "freshness")
    assert freshness["cautionReason"] == "as_of_limitation"
    assert freshness["qualificationQuote"] in _row(db)["detail_analysis"]
    snapshot = _snapshots(db)[0]
    assert snapshot["detail_analysis"] == before["detail_analysis"]
    audit = json.loads(snapshot["update_reason"])
    assert audit["post_verification_status"] == "warning"
    assert audit["remaining_cautions"][0]["reason"] == "as_of_limitation"
    assert audit["remaining_cautions"][0]["qualification_quote"] == freshness["qualificationQuote"]
    assert any('"post_caution_reasons": {"freshness": "as_of_limitation"}' in message for message in update_logs)


@pytest.mark.parametrize(
    "issue",
    [
        "source_conflict",
        "insufficient_evidence",
        "other",
        "missing_reason",
        "missing_quote",
        "invented_quote",
        "missing_source",
        "unverified",
        "contradicted",
        "outdated",
        "other_caution",
        "unresolved_original",
        "missing_check",
    ],
)
def test_warning_exceptions_do_not_bypass_save_guards(
    db: SimpleNamespace,
    conditional_analysis: SimpleNamespace,
    issue: str,
) -> None:
    post = conditional_analysis.verifier.compare_evidence.return_value
    freshness = next(item for item in post.checks if item.aspect == "freshness")
    if issue in {"source_conflict", "insufficient_evidence", "other"}:
        freshness.caution_reason = issue
    elif issue == "missing_reason":
        freshness.caution_reason = None
    elif issue == "missing_quote":
        freshness.qualification_quote = None
    elif issue == "invented_quote":
        freshness.qualification_quote = "본문에 없는 확인 시점 한계"
    elif issue == "missing_source":
        freshness.source_urls = []
    elif issue in {"unverified", "contradicted", "outdated"}:
        freshness.verdict = issue
    elif issue == "other_caution":
        post.checks[0].verdict = "caution"
    elif issue == "unresolved_original":
        conditional_analysis.verifier.verify_with_evidence.return_value.verification.checks[0].verdict = "contradicted"
        post.checks[0].verdict = "not_applicable"
    else:
        post.checks.pop()
    result = asyncio.run(
        orchestration.EventVerificationUpdateService().update(1, EventVerificationUpdateIn(actor_usr_logn_id="actor")),
    )
    assert result.update_status == "skipped"
    assert _snapshots(db) == []
    assert _row(db)["one_line_summary"] == "10월 가동 예정"


def test_update_api_runs_verification_and_saves_preimage(
    db: SimpleNamespace,
    analysis: SimpleNamespace,
    client: TestClient,
    update_logs: list[str],
) -> None:
    response = client.post(
        "/events/1/verification-updates",
        json={"actorUsrLognId": "actor", "expectedUpdatedAt": "2020-01-01T00:00:00"},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["updateStatus"] == "updated"
    assert result["snapshotVersionNo"] == 1
    assert result["miEventSnapshotId"] == _snapshots(db)[0]["mi_event_snapshot_id"]
    assert result["verification"]["status"] == "fail"
    assert result["postVerification"]["status"] == "pass"
    assert result["changes"][0]["sourceUrls"] == [SOURCE_URL]
    assert _snapshots(db)[0]["one_line_summary"] == "10월 가동 예정"
    assert _row(db)["one_line_summary"] == "12월 가동 예정"
    reason = json.loads(_snapshots(db)[0]["update_reason"])
    assert reason["changes"][0]["before_hash"] == orchestration._content_hash("10월 가동 예정")
    assert reason["sources"][0]["quote_excerpt"] == EVIDENCE
    committed = next(message for message in update_logs if " DB_COMMITTED | " in message)
    result_log = next(message for message in update_logs if " RESULT | " in message)
    logged = json.loads(result_log.split(" | ", 1)[1])
    assert update_logs.index(committed) < update_logs.index(result_log)
    assert logged["update_status"] == "updated"
    assert logged["snapshot_id"] == result["miEventSnapshotId"]
    assert "database=" in committed
    assert any(" DB_TARGET | " in message for message in update_logs)
    assert all(EVIDENCE not in message and "12월 가동 예정" not in message for message in update_logs)


@pytest.mark.parametrize(
    ("initial", "post", "expected"),
    [("pass", "pass", "unchanged"), ("warning", "pass", "skipped"), ("fail", "warning", "skipped")],
)
def test_update_skipped_without_verified_correction(
    db: SimpleNamespace,
    analysis: SimpleNamespace,
    initial: str,
    post: str,
    expected: str,
    update_logs: list[str],
) -> None:
    analysis.verifier.verify_with_evidence.return_value.verification = _verification(initial)
    analysis.verifier.compare_evidence.return_value = _verification(post)
    result = asyncio.run(
        orchestration.EventVerificationUpdateService().update(1, EventVerificationUpdateIn(actor_usr_logn_id="a")),
    )
    assert result.update_status == expected
    logged = json.loads(next(message for message in update_logs if " RESULT | " in message).split(" | ", 1)[1])
    assert logged["update_status"] == expected
    assert logged["verification_status"] == initial
    assert logged["post_verification_status"] == (post if initial == "fail" else None)
    assert logged["message"] == result.message
    assert logged["snapshot_id"] is None
    assert not any(" DB_COMMITTED | " in message for message in update_logs)
    assert _snapshots(db) == []
    assert _row(db)["one_line_summary"] == "10월 가동 예정"


def test_commit_failure_never_logs_saved_result(
    db: SimpleNamespace,
    analysis: SimpleNamespace,
    update_logs: list[str],
) -> None:
    def reject_commit(session: object) -> None:
        message = "sensitive SQL parameters must not be logged"
        raise RuntimeError(message)

    event.listen(db.factory, "before_commit", reject_commit)
    try:
        with pytest.raises(RuntimeError, match="sensitive SQL"):
            asyncio.run(
                orchestration.EventVerificationUpdateService().update(
                    1,
                    EventVerificationUpdateIn(actor_usr_logn_id="a"),
                ),
            )
    finally:
        event.remove(db.factory, "before_commit", reject_commit)
    assert _snapshots(db) == []
    assert _row(db)["one_line_summary"] == "10월 가동 예정"
    assert any(" FAILED | " in message and "error_type=RuntimeError" in message for message in update_logs)
    assert not any(" DB_COMMITTED | " in message or " RESULT | " in message for message in update_logs)
    assert all("sensitive SQL" not in message for message in update_logs)


@pytest.mark.parametrize("invalid", ["source", "quote", "duplicate", "unknown_column"])
def test_untrusted_proposal_never_writes(db: SimpleNamespace, analysis: SimpleNamespace, invalid: str) -> None:
    change = analysis.proposal.changes[0]
    if invalid == "source":
        change.evidence[0].source_id = 99
    elif invalid == "quote":
        change.evidence[0].quote = "없는 근거"
    elif invalid == "duplicate":
        analysis.proposal.changes.append(change)
    else:
        change.field = "event_title"
    with pytest.raises(MIBaseError) as exc:
        asyncio.run(
            orchestration.EventVerificationUpdateService().update(1, EventVerificationUpdateIn(actor_usr_logn_id="a")),
        )
    assert exc.value.error_code == ErrorCode.LLM_INVALID_RESPONSE_ERROR
    assert _snapshots(db) == []


@pytest.mark.parametrize(
    "body",
    [{}, {"actorUsrLognId": " "}, {"actorUsrLognId": 123}, {"actorUsrLognId": "a", "changes": []}],
)
def test_update_request_contract(client: TestClient, body: dict[str, object]) -> None:
    assert client.post("/events/1/verification-updates", json=body).status_code == 422


def test_api_returns_conflict_before_external_calls(
    db: SimpleNamespace,
    analysis: SimpleNamespace,
    client: TestClient,
) -> None:
    response = client.post(
        "/events/1/verification-updates",
        json={"actorUsrLognId": "a", "expectedUpdatedAt": "2019-01-01T00:00:00"},
    )
    assert response.status_code == 409
    assert response.json()["data"]["error_name"] == "EVENT_UPDATE_STALE"
    analysis.verifier.verify_with_evidence.assert_not_called()


def test_update_timeout_never_writes(db: SimpleNamespace, analysis: SimpleNamespace) -> None:
    async def pending(*args: object, **kwargs: object) -> None:
        await asyncio.Event().wait()

    analysis.settings.event_verification_update_timeout_sec = 0.01
    analysis.llm.side_effect = pending
    with pytest.raises(MIBaseError) as exc:
        asyncio.run(
            orchestration.EventVerificationUpdateService().update(1, EventVerificationUpdateIn(actor_usr_logn_id="a")),
        )
    assert exc.value.error_code == ErrorCode.LLM_RESPONSE_TIMEOUT
    assert _snapshots(db) == []


def test_concurrent_edit_during_analysis_returns_conflict_without_snapshot(
    db: SimpleNamespace,
    analysis: SimpleNamespace,
    client: TestClient,
) -> None:
    async def edit_before_apply(*args: object, **kwargs: object) -> EventVerificationItem:
        with db.factory.begin() as session:
            session.execute(db.events.update().values(detail_analysis="다른 사용자가 저장한 내용"))
        return _verification("pass")

    analysis.verifier.compare_evidence.side_effect = edit_before_apply
    response = client.post("/events/1/verification-updates", json={"actorUsrLognId": "actor"})
    assert response.status_code == 409
    assert _snapshots(db) == []
    assert _row(db)["detail_analysis"] == "다른 사용자가 저장한 내용"


def test_large_content_does_not_overflow_snapshot_reason(db: SimpleNamespace, analysis: SimpleNamespace) -> None:
    change = analysis.proposal.changes[0]
    change.field = "detail_analysis"
    change.value = "긴 본문" * 20000
    result = asyncio.run(
        orchestration.EventVerificationUpdateService().update(
            1,
            EventVerificationUpdateIn(actor_usr_logn_id="actor"),
        ),
    )
    snapshot = _snapshots(db)[0]
    assert len(snapshot["update_reason"].encode("utf-8")) < 65535
    assert _row(db)["detail_analysis"] == change.value
    assert result.changes[0].after == change.value


def test_snapshot_versions_include_deleted_history(db: SimpleNamespace) -> None:
    context = db.service.prepare_verification_update(1)
    first = db.service.apply_verification_update(1, context.fingerprint, {"one_line_summary": "수정 1"}, "a", "r")
    with db.factory.begin() as session:
        session.execute(db.snapshots.update().values(snapshot_version_no=7, del_yn="Y"))
    context = db.service.prepare_verification_update(1)
    second = db.service.apply_verification_update(1, context.fingerprint, {"one_line_summary": "수정 2"}, "a", "r")
    assert second.snapshot_version_no == 8
    assert second.previous_snapshot_id == first.snapshot_id


def test_missing_snapshot_audit_column_blocks_all_writes(db: SimpleNamespace) -> None:
    with db.engine.begin() as connection:
        connection.execute(text("ALTER TABLE tmm_mi_mievent_snapshot_m DROP COLUMN mod_usr_logn_id"))
    with pytest.raises(MIBaseError) as exc:
        db.service.prepare_verification_update(1)
    assert exc.value.error_code == ErrorCode.EVENT_UPDATE_SCHEMA_ERROR
    assert _row(db)["one_line_summary"] == "10월 가동 예정"
