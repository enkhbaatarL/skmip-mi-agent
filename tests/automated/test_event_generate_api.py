# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.agents.event_generate_agent.api import router
from apps.agents.event_generate_agent.flows.generate_from_query.api_schema import (
    GenerateFromQueryMetaOut,
    GenerateFromQueryResult,
)
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.persistence.event_generation_service import EventGenerationService
from apps.agents.event_generate_agent.schemas.api.event import GeneratedEventOut


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.mark.parametrize("user_id", ["12345", "employee-a"])
def test_create_event_generation_accepts_string_user_id_header(user_id: str) -> None:
    result = GenerateFromQueryResult(meta=GenerateFromQueryMetaOut(), events=[])
    with patch(
        "apps.agents.event_generate_agent.api.run_generate_from_query",
        new=AsyncMock(return_value=result),
    ) as run_generate:
        response = _client().post(
            "/events/generations",
            headers={"X-User-ID": user_id},
            json={"userQuery": "LNG 시장 이벤트"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    run_generate.assert_awaited_once_with(
        user_query="LNG 시장 이벤트",
        date_from=None,
        date_to=None,
        user_id=user_id,
    )


@pytest.mark.parametrize(
    ("date_from", "date_to"),
    [
        ("2026-10-20", "2026-10-01"),
        (" 2026-10-20 ", "2026-10-01"),
    ],
)
def test_create_event_generation_rejects_inverted_date_range(date_from: str, date_to: str) -> None:
    run_generate = AsyncMock()
    with patch(
        "apps.agents.event_generate_agent.api.run_generate_from_query",
        new=run_generate,
    ):
        response = _client().post(
            "/events/generations",
            headers={"X-User-ID": "employee-a"},
            json={
                "userQuery": "LNG 시장 이벤트",
                "dateFrom": date_from,
                "dateTo": date_to,
            },
        )

    assert response.status_code == 422
    assert "dateFrom must be earlier than or equal to dateTo" in response.json()["detail"][0]["msg"]
    run_generate.assert_not_awaited()


@pytest.mark.parametrize(
    ("date_from", "date_to"),
    [
        ("2026-10-01", "2026-10-20"),
        ("2026-10-20", "2026-10-20"),
    ],
)
def test_create_event_generation_accepts_non_inverted_date_range(date_from: str, date_to: str) -> None:
    result = GenerateFromQueryResult(meta=GenerateFromQueryMetaOut(), events=[])
    run_generate = AsyncMock(return_value=result)
    with patch(
        "apps.agents.event_generate_agent.api.run_generate_from_query",
        new=run_generate,
    ):
        response = _client().post(
            "/events/generations",
            headers={"X-User-ID": "employee-a"},
            json={
                "userQuery": "LNG 시장 이벤트",
                "dateFrom": date_from,
                "dateTo": date_to,
            },
        )

    assert response.status_code == 200
    run_generate.assert_awaited_once_with(
        user_query="LNG 시장 이벤트",
        date_from=date_from,
        date_to=date_to,
        user_id="employee-a",
    )


def test_generate_from_query_state_preserves_text_user_id() -> None:
    state = GenerateFromQueryState(user_id="employee-a")

    assert state.user_id == "employee-a"


def test_event_generation_service_uses_text_user_id_for_actor_columns() -> None:
    session = Mock()
    repository = Mock()
    repository.insert_event.return_value = 101
    event = GeneratedEventOut(one_line_summary="LNG 시장 이벤트", event_type_l2_id=10)

    with (
        patch(
            "apps.common.configs.database.sync_database.connection.get_sync_session",
            return_value=session,
        ),
        patch(
            "apps.agents.event_generate_agent.persistence.event_generation_service.EventRepository",
            return_value=repository,
        ),
    ):
        result = EventGenerationService().create_event(event, user_id="employee-a")

    payload = repository.insert_event.call_args.args[0]
    assert payload["crt_usr_logn_id"] == "mcp_employee-a"
    assert payload["mod_usr_logn_id"] == "mcp_employee-a"
    assert result.mi_event_id == 101
    session.commit.assert_called_once_with()
    session.close.assert_called_once_with()


@pytest.mark.parametrize(
    ("search_text", "expected"),
    [
        (
            "독일·영국 둔켈플라우테(Dunkelflaute)와 한파 동시 발생 가정.",
            "독일·영국 둔켈플라우테(Dunkelflaute)와 한파 동시 발생 가정.",
        ),
        ("", "LNG 시장 이벤트"),
    ],
)
def test_event_generation_service_stores_search_text_with_summary_fallback(search_text: str, expected: str) -> None:
    session = Mock()
    repository = Mock()
    repository.insert_event.return_value = 102
    event = GeneratedEventOut(one_line_summary="LNG 시장 이벤트", event_type_l2_id=10)

    with (
        patch(
            "apps.common.configs.database.sync_database.connection.get_sync_session",
            return_value=session,
        ),
        patch(
            "apps.agents.event_generate_agent.persistence.event_generation_service.EventRepository",
            return_value=repository,
        ),
    ):
        EventGenerationService().create_event(event, search_text=search_text)

    payload = repository.insert_event.call_args.args[0]
    assert payload["one_line_summary"] == "LNG 시장 이벤트"
    # search_text 는 NOT NULL 이라 LLM 이 비워 두면 한 줄 요약으로 대신한다.
    assert payload["search_text"] == expected


def test_search_text_is_persisted_but_not_exposed_in_api_response() -> None:
    from apps.agents.event_generate_agent.flows.generate_from_query.api_schema import GeneratedFromQueryEventOut
    from apps.agents.event_generate_agent.flows.generate_from_query.nodes import persist
    from apps.agents.event_generate_agent.schemas.api.event import ConfirmedEventOut
    from apps.agents.event_generate_agent.schemas.domain import EventDraft, EventTypeAssignment, EventValidation

    assert "search_text" not in GeneratedFromQueryEventOut.model_fields

    state = GenerateFromQueryState(
        draft=EventDraft(one_line_summary="[독일·영국 저풍 한파] 동시 충격 가정", search_text="검색용 요약"),
        validation=EventValidation(),
        type_assignment=EventTypeAssignment(event_type_l2_id=9),
    )
    service = Mock()
    service.create_event.return_value = ConfirmedEventOut(mi_event_id=51, event_type_l2_id=9)
    with patch.object(persist, "EventGenerationService", return_value=service):
        update = asyncio.run(persist.persist_events(state))

    assert update["saved_event_id"] == 51
    assert service.create_event.call_args.kwargs["search_text"] == "검색용 요약"
