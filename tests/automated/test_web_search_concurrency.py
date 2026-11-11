from __future__ import annotations

# ruff: noqa: S101, SLF001
import asyncio
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from apps.common.exceptions.custom import MIBaseError
from apps.connectors.web import provider as provider_module


@pytest.mark.parametrize("request_fails", [False, True])
def test_client_setup_allows_other_coroutines_and_closes_after_request(
    monkeypatch: pytest.MonkeyPatch,
    *,
    request_fails: bool,
) -> None:
    async def run() -> None:
        setup_started = Event()
        release_setup = Event()
        http_client = AsyncMock()
        create = AsyncMock(return_value={"status": "completed", "output": []})
        if request_fails:
            create.side_effect = RuntimeError("upstream unavailable")
        client = SimpleNamespace(responses=SimpleNamespace(create=create))
        provider = provider_module.ResponsesWebSearchProvider()
        llm_gate, http_gate = asyncio.Semaphore(1), asyncio.Semaphore(1)

        def blocking_setup() -> tuple[SimpleNamespace, AsyncMock]:
            setup_started.set()
            # The coroutine below must run while certificate/client setup is still in progress.
            if not release_setup.wait(timeout=2):
                message = "Client setup blocked the event loop"
                raise AssertionError(message)
            return client, http_client

        monkeypatch.setattr(provider, "_create_client", blocking_setup)
        monkeypatch.setattr(provider, "_log_response", Mock())
        monkeypatch.setattr(provider_module, "ensure_runtime_context_ready", AsyncMock())
        monkeypatch.setattr(provider_module, "get_llm_semaphore", lambda: llm_gate)
        monkeypatch.setattr(provider_module, "get_http_semaphore", lambda: http_gate)
        monkeypatch.setattr(provider_module, "accumulate_usage", Mock())
        task = asyncio.create_task(
            provider._invoke(
                query="test",
                start_date=None,
                end_date=None,
                output_schema=None,
                trace_context=None,
                overrides={},
            ),
        )
        try:
            assert await asyncio.to_thread(setup_started.wait, 2)
            release_setup.set()
            if request_fails:
                with pytest.raises(MIBaseError):
                    await task
            else:
                response, _, _ = await task
                assert response["status"] == "completed"
            create.assert_awaited_once()
            http_client.aclose.assert_awaited_once()
            assert not llm_gate.locked()
            assert not http_gate.locked()
        finally:
            release_setup.set()
            if not task.done():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)

    asyncio.run(run())
