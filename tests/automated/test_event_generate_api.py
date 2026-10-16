# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

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
