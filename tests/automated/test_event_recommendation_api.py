from __future__ import annotations

# ruff: noqa: S101, SLF001
import asyncio
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from apps.agents.scenario_group_agent.persistence import event_recommendation_service as service_module
from apps.agents.scenario_group_agent.prompts.event_recommendation import MultiEventRecommendationOutput
from apps.agents.scenario_group_agent.routers.events import router
from apps.agents.scenario_group_agent.schemas.api.event_recommendations import EventRecommendationsOut
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventSearchSource


def _row(event_id: int) -> EventSearchSource:
    return EventSearchSource(
        mi_event_id=event_id,
        one_line_summary=f"Event {event_id}",
        search_text="Demand is expected to rise",
        detail_analysis="Supply decreased.",
        del_yn="N",
        publish_status="PUBLISHED",
    )


def _output(event_id: int = 3, source_id: int = 2) -> MultiEventRecommendationOutput:
    return MultiEventRecommendationOutput.model_validate(
        {
            "items": [
                {
                    "mi_event_id": event_id,
                    "source_event_id": source_id,
                    "relation_type": "supply_demand",
                    "impact_path": "Supply and demand",
                    "period_assessment": "unknown",
                    "period_reason": "Unknown period",
                    "incremental_information": "Supply and demand",
                    "scenario_question": "How will the market change?",
                    "source_evidence": "Supply decreased.",
                    "candidate_evidence": "Demand is expected to rise",
                    "reason": "Consider supply and demand together.",
                },
            ],
            "selection_reason": "Additional demand information.",
        },
    )


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize("ids", [[], [0], [-1], [True], ["1"], [1, 1], [1, 2, 3, 4, 5, 6]])
def test_invalid_request(client: TestClient, ids: list[object]) -> None:
    assert client.post("/events/recommendations", json={"miEventIds": ids}).status_code == 422


def test_http_contract(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    recommend = AsyncMock(
        return_value=EventRecommendationsOut(
            items=[{"miEventId": 3, "title": "Event 3", "reason": "Relevant"}],
            selection_reason="Supply and demand",
        ),
    )
    monkeypatch.setattr(service_module.EventRecommendationService, "recommend", recommend)
    response = client.post("/events/recommendations", json={"miEventIds": [1, 2]})
    assert response.status_code == 200
    assert response.json() == {
        "items": [{"miEventId": 3, "title": "Event 3", "reason": "Relevant"}],
        "selectionReason": "Supply and demand",
    }
    recommend.assert_awaited_once_with([1, 2])


@pytest.fixture
def dependencies(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    calls: list[list[int]] = []

    def load_search_sources(*, event_ids: list[int]) -> list[EventSearchSource]:
        calls.append(event_ids)
        return [_row(event_id) for event_id in event_ids if event_id != 4]

    monkeypatch.setattr(
        service_module,
        "EventService",
        lambda: SimpleNamespace(load_search_sources=load_search_sources),
    )
    monkeypatch.setattr(
        service_module,
        "get_settings",
        lambda: SimpleNamespace(
            event_search_documents=None,
            event_search_db_path=None,
            event_search_model_cache=None,
            llm_stream_enabled=False,
            llm_reasoning_effort=None,
        ),
    )
    search = SimpleNamespace(search=lambda texts, excluded: [1, 2, 3, 3, 4])
    monkeypatch.setattr(service_module, "get_local_event_search", lambda *args: search)
    llm = AsyncMock(return_value=SimpleNamespace(result=_output()))
    monkeypatch.setattr(service_module, "invoke_llm_structured_output", llm)
    return SimpleNamespace(calls=calls, llm=llm, search=search)


def test_multi_source_excludes_selected_duplicate_and_unpublished(dependencies: SimpleNamespace) -> None:
    result = asyncio.run(service_module.EventRecommendationService().recommend([1, 2]))
    assert [item.mi_event_id for item in result.items] == [3]
    assert dependencies.calls == [[1, 2], [3, 4]]
    prompt = json.loads(dependencies.llm.call_args.kwargs["messages"][1]["content"])
    assert [event["mi_event_id"] for event in prompt["source_events"]] == [1, 2]
    assert [event["mi_event_id"] for event in prompt["candidates"]] == [3]


def test_missing_source_stops_before_llm(dependencies: SimpleNamespace) -> None:
    with pytest.raises(MIBaseError) as exc:
        asyncio.run(service_module.EventRecommendationService().recommend([4]))
    assert exc.value.error_code == ErrorCode.ENTITY_NOT_FOUND
    dependencies.llm.assert_not_called()


def test_no_eligible_candidates_skips_llm(dependencies: SimpleNamespace) -> None:
    dependencies.search.search = lambda texts, excluded: [4]
    result = asyncio.run(service_module.EventRecommendationService().recommend([1]))
    assert result.items == []
    dependencies.llm.assert_not_called()


@pytest.mark.parametrize(("event_id", "source_id"), [(1, 2), (99, 2), (3, 99)])
def test_reject_invalid_llm_ids(dependencies: SimpleNamespace, event_id: int, source_id: int) -> None:
    dependencies.llm.return_value = SimpleNamespace(result=_output(event_id, source_id))
    with pytest.raises(MIBaseError) as exc:
        asyncio.run(service_module.EventRecommendationService().recommend([1, 2]))
    assert exc.value.error_code == ErrorCode.LLM_INVALID_RESPONSE_ERROR


def test_reject_duplicate_llm_recommendations(dependencies: SimpleNamespace) -> None:
    output = _output()
    output.items.append(output.items[0])
    dependencies.llm.return_value = SimpleNamespace(result=output)
    with pytest.raises(MIBaseError):
        asyncio.run(service_module.EventRecommendationService().recommend([1, 2]))


def test_reject_fabricated_evidence(dependencies: SimpleNamespace) -> None:
    output = _output()
    output.items[0].source_evidence = "Fabricated evidence"
    dependencies.llm.return_value = SimpleNamespace(result=output)
    with pytest.raises(MIBaseError):
        asyncio.run(service_module.EventRecommendationService().recommend([1, 2]))


@pytest.mark.parametrize("indexed", [True, False])
def test_local_search_reuses_index_and_closes_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    indexed: bool,
) -> None:
    from apps.connectors.vdb.local_event_search import LocalEventSearch

    documents = tmp_path / "documents.jsonl"
    documents.write_text("{}\n{}\n{}\n", encoding="utf-8")
    client = Mock()
    client.collection_exists.return_value = indexed
    client.count.return_value = SimpleNamespace(count=3)
    client.query_points.side_effect = [
        SimpleNamespace(
            points=[
                SimpleNamespace(payload={"event_id": 3}, score=0.8),
                SimpleNamespace(payload={"event_id": 3}, score=0.7),
                SimpleNamespace(payload={"event_id": 1}, score=1.0),
            ],
        ),
        SimpleNamespace(points=[SimpleNamespace(payload={"event_id": 4}, score=0.9)]),
    ]
    model = Mock()
    model.max_seq_length = 100
    model.tokenizer.return_value = {"input_ids": [1, 2]}
    model.encode.return_value.tolist.return_value = [[0.1], [0.2]]
    model_factory = Mock(return_value=model)
    monkeypatch.setitem(sys.modules, "sentence_transformers", SimpleNamespace(SentenceTransformer=model_factory))
    monkeypatch.setitem(
        sys.modules,
        "qdrant_client",
        SimpleNamespace(
            QdrantClient=Mock(return_value=client),
            models=SimpleNamespace(Filter=Mock(), FieldCondition=Mock(), MatchAny=Mock()),
        ),
    )
    search = LocalEventSearch(documents, tmp_path / "db", tmp_path / "models")
    if indexed:
        assert search.search(["source 1", "source 2"], [1, 2]) == [4, 3]
        model_factory.assert_called_once()
        assert client.query_points.call_count == 2
    else:
        with pytest.raises(MIBaseError) as exc:
            search.search(["source 1"], [1])
        assert exc.value.error_code == ErrorCode.DATA_RETRIEVAL_FAILED
        model_factory.assert_not_called()
    client.close.assert_called_once()
    client.upsert.assert_not_called()


def test_embedding_cache_reuses_identical_text_and_recomputes_changes(tmp_path: Path) -> None:
    from apps.connectors.vdb.local_event_search import LocalEventSearch

    model = Mock(max_seq_length=100)
    model.tokenizer.return_value = {"input_ids": [1, 2]}
    model.encode.side_effect = lambda texts, **kwargs: SimpleNamespace(
        tolist=lambda: [[float(len(text))] for text in texts],
    )
    search = LocalEventSearch(tmp_path / "docs", tmp_path / "db", tmp_path / "models")
    search._model = model
    assert search._encode(["original", "original"]) == [[8.0], [8.0]]
    assert search._encode(["original"]) == [[8.0]]
    assert model.encode.call_count == 1
    assert model.encode.call_args.args[0] == ["original"]
    assert search._encode(["updated", "original"]) == [[7.0], [8.0]]
    assert model.encode.call_args.args[0] == ["updated"]
    assert model.encode.call_count == 2
    assert model.tokenizer.call_count == 2
    model.tokenizer.return_value = {"input_ids": list(range(101))}
    with pytest.raises(MIBaseError) as exc:
        search._encode(["overlong new content"])
    assert exc.value.error_code == ErrorCode.INVALID_REQUEST
    assert model.encode.call_count == 2


def test_embedding_cache_is_bounded_and_preserves_recent_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from apps.connectors.vdb import local_event_search as module

    monkeypatch.setattr(module, "EMBEDDING_CACHE_SIZE", 2)
    model = Mock(max_seq_length=100)
    model.tokenizer.return_value = {"input_ids": [1]}
    model.encode.side_effect = lambda texts, **kwargs: SimpleNamespace(tolist=lambda: [[1.0] for text in texts])
    search = module.LocalEventSearch(tmp_path / "docs", tmp_path / "db", tmp_path / "models")
    search._model = model
    search._encode(["a", "b"])
    search._encode(["a"])
    search._encode(["c"])
    search._encode(["a"])
    assert model.encode.call_count == 2
    search._encode(["b"])
    assert model.encode.call_args.args[0] == ["b"]
    assert len(search._embeddings) == 2
    # A single batch exceeding the capacity still returns every vector in input order.
    assert search._encode(["a", "b", "c", "a"]) == [[1.0]] * 4
    assert len(search._embeddings) == 2
