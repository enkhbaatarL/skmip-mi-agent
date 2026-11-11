from __future__ import annotations

# ruff: noqa: S101, SLF001
import asyncio
from datetime import UTC, datetime
import json
from types import SimpleNamespace
from typing import get_args
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from apps.agents.scenario_group_agent.persistence import event_verification_service as service_module
from apps.agents.scenario_group_agent.prompts.event_verification import EventVerificationOutput
from apps.agents.scenario_group_agent.routers.events import router
from apps.agents.scenario_group_agent.schemas.api.event_verifications import VerificationAspect, VerificationVerdict
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventSearchSource, EventUpdateContext


SOURCE_URL = "https://example.com/news/update"


def _row(event_id: int) -> EventSearchSource:
    return EventSearchSource(
        mi_event_id=event_id,
        one_line_summary=f"Event {event_id}",
        detail_analysis="Train 1의 가동 일정",
        numeric_facts_md="연간 5 mtpa",
        institution_view_synthesis="기관 A는 내년 가동을 전망",
        occurred_at=datetime(2026, 10, 1, tzinfo=UTC),
        mod_dtm=datetime(2026, 10, 2, tzinfo=UTC),
        del_yn="N",
        publish_status="PUBLISHED",
    )


def _output(verdict: VerificationVerdict = "matched") -> EventVerificationOutput:
    return EventVerificationOutput.model_validate(
        {
            "review": "비교 결과입니다.\n후속 근거를 확인했습니다.",
            "checks": [
                {
                    "aspect": aspect,
                    "verdict": verdict if aspect == "freshness" else "matched",
                    "event_claim": "기존 가동 일정",
                    "finding": "공식 발표의 가동 일정과 비교했습니다.",
                    "source_ids": [1],
                }
                for aspect in get_args(VerificationAspect)
            ],
        },
    )


@pytest.fixture
def dependencies(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    load = Mock(return_value=[_row(1), _row(2)])
    store = Mock()

    def prepare(ids: list[int]) -> list[EventUpdateContext]:
        return [EventUpdateContext(source=row, fingerprint="f" * 64, content={}) for row in load(event_ids=ids)]

    monkeypatch.setattr(
        service_module,
        "EventService",
        lambda: SimpleNamespace(prepare_verifications=prepare, store_verifications=store),
    )
    settings = SimpleNamespace(
        event_verification_timeout_sec=5,
        event_verification_reuse_ttl_sec=1800,
        llm_stream_enabled=False,
        llm_reasoning_effort=None,
    )
    monkeypatch.setattr(service_module, "get_settings", lambda: settings)
    search = AsyncMock(
        return_value={
            "status": "completed",
            "results": [{"url": SOURCE_URL, "title": "공식 발표", "content": "2026년 10월 2일 가동 일정 발표"}],
        },
    )
    factory = Mock(return_value=SimpleNamespace(search=search))
    monkeypatch.setattr(service_module.WebSearchProviderFactory, "create_from_settings", factory)
    llm = AsyncMock(return_value=SimpleNamespace(result=_output()))
    monkeypatch.setattr(service_module, "invoke_llm_structured_output", llm)
    return SimpleNamespace(load=load, store=store, settings=settings, search=search, factory=factory, llm=llm)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_api_returns_ordered_camelcase_results(client: TestClient, dependencies: SimpleNamespace) -> None:
    response = client.post("/events/verifications", json={"actorUsrLognId": "actor", "miEventIds": [2, 1]})
    assert response.status_code == 200
    body = response.json()
    assert body["checkedAt"].endswith("Z")
    assert [item["miEventId"] for item in body["items"]] == [2, 1]
    item = body["items"][0]
    assert item["status"] == "pass"
    assert item["reasonCode"] == "verified"
    assert item["links"] == [SOURCE_URL]
    assert len(item["checks"]) == 6
    assert item["checks"][0]["sourceUrls"] == [SOURCE_URL]
    assert "\n" not in item["review"]
    assert item["sourceUpdatedAt"] == "2026-10-02T00:00:00Z"
    assert item["verificationId"]
    records, actor = dependencies.store.call_args.args
    assert actor == "actor"
    assert records[0].mi_event_verification_id == item["verificationId"]
    assert (records[0].expires_at - records[0].checked_at).total_seconds() == 1800
    assert records[0].search_evidence_json[0]["content"]
    dependencies.load.assert_called_once_with(event_ids=[2, 1])
    call = dependencies.search.call_args.kwargs
    assert call["tool_choice"] == "required"
    assert call["max_results"] == 8
    context = json.loads(call["context"])
    assert context["event"]["numeric_facts_md"] == "연간 5 mtpa"
    assert context["event"]["institution_view_synthesis"]
    assert call["end_date"] == context["as_of"][:10]


def test_as_of_caution_is_preserved_in_public_pass(
    client: TestClient,
    dependencies: SimpleNamespace,
) -> None:
    output = _output("caution").model_dump()
    check = next(item for item in output["checks"] if item["aspect"] == "freshness")
    check["caution_reason"] = "as_of_limitation"
    check["qualification_quote"] = "2026년 10월 2일 기준이며 이후 변경 여부는 미확인입니다."
    row = _row(1)
    row.detail_analysis += check["qualification_quote"]
    dependencies.load.return_value = [row]
    dependencies.llm.return_value.result = EventVerificationOutput.model_validate(output)
    response = client.post("/events/verifications", json={"actorUsrLognId": "actor", "miEventIds": [1]})
    assert response.status_code == 200
    result = response.json()["items"][0]
    assert result["status"] == "pass"
    assert result["reasonCode"] == "no_contradiction"
    freshness = next(item for item in result["checks"] if item["aspect"] == "freshness")
    assert freshness["cautionReason"] == "as_of_limitation"
    assert freshness["qualificationQuote"] == check["qualification_quote"]
    assert freshness["sourceUrls"] == [SOURCE_URL]


@pytest.mark.parametrize(
    "patch",
    [
        {"verdict": "matched"},
        {"aspect": "time"},
        {"source_ids": []},
        {"qualification_quote": None},
        {"qualification_quote": " "},
        {"caution_reason": "other"},
    ],
)
def test_invalid_as_of_classification_rejected(patch: dict[str, object]) -> None:
    output = _output("caution").model_dump()
    check = next(item for item in output["checks"] if item["aspect"] == "freshness")
    check.update(caution_reason="as_of_limitation", qualification_quote="2026년 10월 2일 이후 상황은 미확인입니다.")
    check.update(patch)
    with pytest.raises(ValidationError):
        EventVerificationOutput.model_validate(output)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"miEventIds": []},
        {"miEventIds": [1, 1]},
        {"miEventIds": [0]},
        {"miEventIds": [-1]},
        {"miEventIds": [True]},
        {"miEventIds": ["1"]},
        {"miEventIds": [1.0]},
        {"miEventIds": [1, 2, 3, 4, 5, 6]},
        {"miEventIds": [1], "extra": 1},
    ],
)
def test_invalid_request_rejected_before_io(
    client: TestClient,
    dependencies: SimpleNamespace,
    body: dict[str, object],
) -> None:
    assert client.post("/events/verifications", json={"actorUsrLognId": "actor", **body}).status_code == 422
    dependencies.load.assert_not_called()
    dependencies.search.assert_not_called()


def test_missing_or_unpublished_event_prevents_search(dependencies: SimpleNamespace) -> None:
    with pytest.raises(MIBaseError) as exc:
        asyncio.run(service_module.EventVerificationService().verify([1, 3], "actor"))
    assert exc.value.error_code == ErrorCode.ENTITY_NOT_FOUND
    dependencies.factory.assert_not_called()


@pytest.mark.parametrize(
    ("verdict", "status", "reason"),
    [
        ("matched", "pass", "verified"),
        ("caution", "pass", "no_contradiction"),
        ("unverified", "pass", "no_contradiction"),
        ("outdated", "fail", "outdated"),
        ("contradicted", "fail", "contradicted"),
    ],
)
def test_aggregate_verdict(
    dependencies: SimpleNamespace,
    verdict: VerificationVerdict,
    status: str,
    reason: str,
) -> None:
    dependencies.llm.return_value = SimpleNamespace(result=_output(verdict))
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert result.items[0].status == status
    assert result.items[0].reason_code == reason


@pytest.mark.parametrize(
    ("verdicts", "status", "reason"),
    [
        (["matched"] * 3 + ["caution"] * 2 + ["unverified"], "pass", "no_contradiction"),
        (["matched"] + ["unverified"] * 5, "pass", "no_contradiction"),
        (["unverified"] * 6, "warning", "review_required"),
        (["caution"] * 6, "warning", "review_required"),
        (["not_applicable"] * 5 + ["unverified"], "warning", "review_required"),
        (["matched"] * 3 + ["caution", "unverified", "contradicted"], "fail", "contradicted"),
        (["matched"] * 3 + ["caution", "unverified", "outdated"], "fail", "outdated"),
    ],
)
def test_public_verification_mixed_checks_preserves_details(
    client: TestClient,
    dependencies: SimpleNamespace,
    verdicts: list[VerificationVerdict],
    status: str,
    reason: str,
) -> None:
    output = _output().model_dump()
    for check, verdict in zip(output["checks"], verdicts, strict=True):
        check["verdict"] = verdict
    dependencies.load.return_value = [_row(1)]
    dependencies.llm.return_value.result = EventVerificationOutput.model_validate(output)
    response = client.post("/events/verifications", json={"actorUsrLognId": "actor", "miEventIds": [1]})
    assert response.status_code == 200
    result = response.json()["items"][0]
    assert (result["status"], result["reasonCode"]) == (status, reason)
    assert [check["verdict"] for check in result["checks"]] == verdicts
    assert all(check["finding"] for check in result["checks"])


@pytest.mark.parametrize("verdict", ["caution", "unverified"])
def test_update_verification_keeps_strict_grade(dependencies: SimpleNamespace, verdict: VerificationVerdict) -> None:
    dependencies.llm.return_value.result = _output(verdict)
    verifier = service_module.EventVerificationService()
    evidence = asyncio.run(verifier.verify_with_evidence(_row(1), datetime.now(UTC)))
    assert evidence.verification.status == "warning"
    assert evidence.verification.reason_code == "review_required"
    post = asyncio.run(verifier.compare_evidence(_row(1), evidence.sources, datetime.now(UTC)))
    assert post.status == "warning"
    assert post.reason_code == "review_required"


def test_no_search_evidence_cannot_pass(dependencies: SimpleNamespace) -> None:
    dependencies.search.return_value = {"answer": "문제 없음 https://invented.example/", "results": []}
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert all(item.status == "warning" and item.reason_code == "no_evidence" for item in result.items)
    assert all(item.links == [] for item in result.items)
    dependencies.llm.assert_not_called()


@pytest.mark.parametrize("mode", ["unknown_source", "missing_source", "missing_aspect", "duplicate_aspect"])
def test_invalid_comparison_is_inconclusive(dependencies: SimpleNamespace, mode: str) -> None:
    output = _output("outdated").model_dump()
    if mode == "unknown_source":
        output["checks"][0]["source_ids"] = [99]
    elif mode == "missing_source":
        output["checks"][4]["source_ids"] = []
    elif mode == "missing_aspect":
        output["checks"].pop()
    else:
        output["checks"][0]["aspect"] = "freshness"
    dependencies.llm.return_value = SimpleNamespace(result=output)
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert result.items[0].status == "warning"
    assert result.items[0].reason_code == "verification_error"
    assert result.items[0].links == [SOURCE_URL]


def test_no_applicable_claims_cannot_pass(dependencies: SimpleNamespace) -> None:
    output = _output().model_dump()
    for check in output["checks"]:
        check.update(verdict="not_applicable", source_ids=[])
    dependencies.llm.return_value = SimpleNamespace(result=output)
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert result.items[0].status == "warning"


def test_partial_search_failure_keeps_other_result(dependencies: SimpleNamespace) -> None:
    dependencies.search.side_effect = [RuntimeError("unavailable"), dependencies.search.return_value]
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert [item.status for item in result.items] == ["warning", "pass"]
    assert result.items[0].reason_code == "search_error"
    dependencies.llm.assert_awaited_once()


def test_incomplete_search_does_not_reach_comparison(dependencies: SimpleNamespace) -> None:
    dependencies.search.return_value["status"] = "incomplete"
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert result.items[0].reason_code == "search_error"
    dependencies.llm.assert_not_called()


def test_provider_unavailable_is_explicit(dependencies: SimpleNamespace) -> None:
    dependencies.factory.side_effect = ValueError("missing provider")
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert all(item.reason_code == "search_error" for item in result.items)
    dependencies.llm.assert_not_called()


def test_timeout_is_warning(dependencies: SimpleNamespace) -> None:
    async def wait_forever(*args: object, **kwargs: object) -> None:
        await asyncio.Event().wait()

    dependencies.settings.event_verification_timeout_sec = 0.02
    dependencies.search.side_effect = wait_forever
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert all(item.reason_code == "search_error" for item in result.items)
    dependencies.llm.assert_not_called()


def test_cancellation_propagates(dependencies: SimpleNamespace) -> None:
    dependencies.search.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    dependencies.store.assert_not_called()


def test_search_pipeline_advances_while_comparison_is_pending(dependencies: SimpleNamespace) -> None:
    """All five searches must start before the first three comparisons can finish."""
    dependencies.load.return_value = [_row(event_id) for event_id in range(1, 6)]

    async def run() -> None:
        all_searched = asyncio.Event()
        comparison_peak = 0
        comparison_active = 0
        search_count = 0

        async def search(**kwargs: object) -> dict[str, object]:
            nonlocal search_count
            search_count += 1
            if search_count == 5:
                all_searched.set()
            return {"results": [{"url": SOURCE_URL, "content": "confirmed"}]}

        async def compare(**kwargs: object) -> SimpleNamespace:
            nonlocal comparison_peak, comparison_active
            comparison_active += 1
            comparison_peak = max(comparison_peak, comparison_active)
            try:
                await all_searched.wait()
                return SimpleNamespace(result=_output())
            finally:
                comparison_active -= 1

        dependencies.search.side_effect = search
        dependencies.llm.side_effect = compare
        result = await asyncio.wait_for(service_module.EventVerificationService().verify([5, 4, 3, 2, 1], "actor"), 2)
        assert [item.mi_event_id for item in result.items] == [5, 4, 3, 2, 1]
        assert all(item.status == "pass" for item in result.items)
        assert search_count == 5
        assert comparison_peak == service_module.MAX_CONCURRENT_EVENTS

    asyncio.run(run())


def test_comparison_queue_timeout_preserves_evidence(dependencies: SimpleNamespace) -> None:
    async def run() -> None:
        dependencies.settings.event_verification_timeout_sec = 0.02
        result = await service_module.EventVerificationService()._verify_evidence(
            _row(1),
            dependencies.factory.return_value,
            datetime.now(UTC),
            asyncio.Semaphore(1),
            asyncio.Semaphore(0),
        )
        assert result.verification.reason_code == "verification_error"
        assert result.sources[0].url == SOURCE_URL
        dependencies.llm.assert_not_called()

    asyncio.run(run())


@pytest.mark.parametrize("actor", [None, "", " ", 123, "a" * 101])
def test_verification_actor_required(client: TestClient, actor: object) -> None:
    body = {"miEventIds": [1]}
    if actor is not None:
        body["actorUsrLognId"] = actor
    assert client.post("/events/verifications", json=body).status_code == 422


def test_persisted_verdict_keeps_strict_grade(dependencies: SimpleNamespace) -> None:
    dependencies.llm.return_value.result = _output("caution")
    result = asyncio.run(service_module.EventVerificationService().verify([1, 2], "actor"))
    assert result.items[0].status == "pass"
    records = dependencies.store.call_args.args[0]
    assert records[0].verification_result_json["status"] == "warning"
    assert records[0].verification_result_json["checks"][4]["verdict"] == "caution"


def test_only_unique_usable_web_citations_are_kept() -> None:
    sources = service_module._search_sources(
        {
            "results": [
                {"url": SOURCE_URL, "content": "confirmed"},
                {"url": SOURCE_URL, "content": "duplicate"},
                {"url": "javascript:alert(1)", "content": "bad"},
                {"url": "file:///etc/passwd", "content": "bad"},
                {"url": "https://user:password@example.com/", "content": "bad"},
                {"url": "https://example.com/empty", "content": " "},
                None,
            ],
        },
    )
    assert [(source.id, source.url) for source in sources] == [(1, SOURCE_URL)]
