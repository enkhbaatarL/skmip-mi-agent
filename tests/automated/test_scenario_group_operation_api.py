from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
import pytest

from apps.agents.scenario_group_agent.api import router as agent_router
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation import (
    V4OperationProgressRecorder,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
    new_operation_id,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.agents.scenario_group_agent.routers.multi_event_scenario_group_sync import (
    router as multi_event_sync_router,
)
from apps.agents.scenario_group_agent.routers.scenario_generation_sync import (
    router as scenario_generation_sync_router,
)
from apps.agents.scenario_group_agent.routers.scenario_group_stream import stream_operation_events
from apps.agents.scenario_group_agent.routers.scenario_groups import router as scenario_groups_router
from apps.agents.scenario_group_agent.runtime import (
    ScenarioGroupOperationEventHub,
    ScenarioGroupOperationTaskRunner,
)
from apps.agents.scenario_group_agent.schemas.api.manage_scenario_groups import (
    ScenarioGroupDetailOut,
)
from apps.agents.scenario_group_agent.schemas.endpoint import (
    ScenarioGroupDetailOut as LegacyScenarioGroupDetailOut,
)
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.scenario_group_operation.repository import ScenarioGroupOperationRepository
from apps.persistence.scenario_group_operation.schema import (
    ScenarioGroupOperationEventPayload,
    ScenarioGroupOperationPayload,
)


class _ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


class _DisconnectedRequest:
    async def is_disconnected(self) -> bool:
        return True


def _operation(*, status: str = "running", latest_sequence: int = 3) -> ScenarioGroupOperationPayload:
    return ScenarioGroupOperationPayload(
        operation_id="01JABCDEF0123456789ABCDEFX",
        scenario_group_id=120,
        operation_type="create",
        engine_version="v4",
        status=status,
        latest_sequence=latest_sequence,
    )


def _event(sequence: int, event_type: str) -> ScenarioGroupOperationEventPayload:
    return ScenarioGroupOperationEventPayload(
        operation_id="01JABCDEF0123456789ABCDEFX",
        scenario_group_id=120,
        sequence=sequence,
        event_type=event_type,
        phase="scenario_synthesis",
        title=event_type,
        message_markdown=event_type,
        payload={"status": "succeeded"} if event_type == "completed" else {},
        created_at=datetime(2026, 8, 10, 4, 0, 0),
    )


def test_canonical_scenario_group_routes_are_exposed_without_v1_or_deprecation() -> None:
    app = FastAPI()
    app.include_router(agent_router)
    schema = app.openapi()
    paths = schema["paths"]

    assert set(paths["/scenario-groups"]) == {"get", "post"}
    assert set(paths["/scenario-groups/{scenario_group_id}"]) == {"get", "delete"}
    assert "/scenario-groups/{scenario_group_id}/operations/{operation_id}" in paths
    assert "/scenario-groups/{scenario_group_id}/operations/{operation_id}/stream" in paths
    canonical_flow_paths = {
        "/scenario-groups/{scenario_group_id}/validation",
        "/scenario-groups/{scenario_group_id}/signposts",
        "/scenario-groups/{scenario_group_id}/confirmation",
    }
    assert canonical_flow_paths <= set(paths)
    assert not any(path.startswith("/v1/") for path in paths)
    assert all("deprecated" not in paths[path]["post"] for path in canonical_flow_paths)
    assert paths["/scenario-groups"]["post"]["tags"] == ["scenario-groups"]
    assert all(
        parameter["name"].lower() != "accept" for parameter in paths["/scenario-groups"]["post"].get("parameters", [])
    )
    assert paths["/scenario-groups/{scenario_group_id}/operations/{operation_id}"]["get"]["tags"] == [
        "scenario-groups",
    ]
    assert paths["/scenario-groups/{scenario_group_id}/validation"]["post"]["tags"] == ["scenario-groups"]
    assert paths["/v4/scenario-groups/sync"]["post"]["tags"] == ["scenario-groups-sync-test"]


def test_routes_are_declared_by_the_documented_owner_routers() -> None:
    scenario_group_paths = {route.path for route in scenario_groups_router.routes}
    assert {
        "/scenario-groups/{scenario_group_id}/validation",
        "/scenario-groups/{scenario_group_id}/signposts",
        "/scenario-groups/{scenario_group_id}/confirmation",
    } <= scenario_group_paths
    assert {route.path for route in scenario_generation_sync_router.routes} == {
        "/scenario-groups/{scenario_group_id}/validation/sync",
        "/scenario-groups/{scenario_group_id}/signposts/sync",
    }
    assert {route.path for route in multi_event_sync_router.routes} == {
        "/v2/scenario-groups/sync",
        "/v3/scenario-groups/sync",
        "/v4/scenario-groups/sync",
    }


def test_management_schema_legacy_import_is_compatible() -> None:
    assert LegacyScenarioGroupDetailOut is ScenarioGroupDetailOut


def test_operation_id_is_ulid_shaped() -> None:
    first = new_operation_id()
    second = new_operation_id()

    assert len(first) == 26
    assert set(first) <= set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    assert first != second


def test_create_accepted_in_session_returns_operation_payload() -> None:
    session = Mock()
    repository = Mock()
    operation_model = object()
    expected = _operation(status="queued", latest_sequence=1)
    repository.insert_operation.return_value = operation_model
    service = ScenarioGroupOperationService()

    with (
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationRepository",
            return_value=repository,
        ),
        patch.object(service, "operation_payload_from_model", return_value=expected) as build_payload,
    ):
        result = service.create_accepted_in_session(
            session,
            scenario_group_id=120,
            operation_id="01JABCDEF0123456789ABCDEFX",
            user_id=7,
        )

    assert result is expected
    build_payload.assert_called_once_with(operation_model)
    repository.append_event.assert_called_once()
    assert repository.append_event.call_args.kwargs["event_type"] == "accepted"


def test_operation_from_another_scenario_group_is_not_found() -> None:
    session = Mock()
    repository = Mock()
    repository.fetch_by_id.return_value = None
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationRepository",
            return_value=repository,
        ),
        pytest.raises(MIBaseError) as caught,
    ):
        ScenarioGroupOperationService().get_operation(120, "operation-owned-by-another-group")

    assert caught.value.status_code == 404
    repository.fetch_by_id.assert_called_once_with(120, "operation-owned-by-another-group")


def test_sse_replays_only_after_last_event_id_and_closes_at_terminal() -> None:
    async def collect() -> list[str]:
        with (
            patch.object(
                ScenarioGroupOperationService,
                "list_events_after",
                return_value=[_event(2, "section_ready"), _event(3, "completed")],
            ) as list_events,
            patch.object(ScenarioGroupOperationService, "get_operation", return_value=_operation(status="succeeded")),
        ):
            chunks = [
                chunk
                async for chunk in stream_operation_events(
                    _ConnectedRequest(),  # type: ignore[arg-type]
                    120,
                    "01JABCDEF0123456789ABCDEFX",
                    after_sequence=1,
                )
            ]
        list_events.assert_called_once_with(120, "01JABCDEF0123456789ABCDEFX", 1)
        return chunks

    chunks = asyncio.run(collect())
    payload = "".join(chunks)
    assert "id: 1\n" not in payload
    assert "id: 2\n" in payload
    assert "id: 3\n" in payload
    assert "event: completed" in payload


def test_custom_retry_is_sanitized_before_operation_event_storage() -> None:
    async def record() -> AsyncMock:
        recorder = V4OperationProgressRecorder(120, "01JABCDEF0123456789ABCDEFX", "trace-1")
        append = AsyncMock()
        recorder._append = append  # type: ignore[method-assign]
        await recorder.on_node_update(
            "__custom__",
            {
                "kind": "stage_retry",
                "phase": "dimension_design",
                "attempt": 2,
                "maxAttempts": 3,
                "validationCode": "UNKNOWN_SOURCE_REFERENCE",
                "referenceIds": ["D2"],
                "message": "raw validation payload must not be persisted",
                "draft": {"secret": "failed draft"},
            },
            None,  # type: ignore[arg-type]
        )
        return append

    append = asyncio.run(record())
    kwargs = append.await_args.kwargs
    assert kwargs["event_type"] == "retrying"
    assert kwargs["payload"] == {
        "phase": "dimension_design",
        "attempt": 2,
        "maxAttempts": 3,
        "validationCode": "UNKNOWN_SOURCE_REFERENCE",
        "referenceIds": ["D2"],
    }
    assert "raw validation payload" not in str(kwargs)
    assert "failed draft" not in str(kwargs)


def test_section_ready_event_contains_projection_revision_details() -> None:
    operation = SimpleNamespace(
        operation_id="01JABCDEF0123456789ABCDEFX",
        scenario_group_id=120,
        latest_sequence=4,
        snapshot_revision=2,
        presentation_snapshot={},
        heartbeat_at=None,
        current_phase=None,
        status="running",
        started_at=datetime(2026, 8, 11, 4, 0, 0),
        completed_at=None,
        last_error=None,
        retry_summary={},
        mlflow_trace_id=None,
    )
    session = Mock()
    repository = ScenarioGroupOperationRepository(session=session)
    snapshot = {
        "sections": {
            "eventAnalysis": {"status": "ready"},
            "scenarioDesign": {"status": "partial"},
        }
    }

    event = repository.append_event(
        operation,
        event_type="section_ready",
        phase="dimension_design",
        title="ready",
        message_markdown="ready",
        payload={},
        now=datetime(2026, 8, 11, 4, 1, 0),
        presentation_snapshot=snapshot,
    )

    assert operation.snapshot_revision == 3
    assert event.snapshot_revision == 3
    assert event.payload["details"] == {
        "sections": [
            {"key": "eventAnalysis", "status": "ready"},
            {"key": "scenarioDesign", "status": "partial"},
        ],
        "snapshotRevision": 3,
    }


def test_v1_backfill_migration_is_idempotent_and_has_scoped_rollback() -> None:
    migration = Path("scripts/migrations/20260811_backfill_v1_presentation_operations.sql").read_text()

    assert migration.count("INSERT IGNORE INTO tmm_mi_scenario_group_operation_m") == 4
    assert "INSERT IGNORE INTO tmm_mi_scenario_group_operation_event_h" in migration
    assert "operation.source = 'legacy_v1_backfill'" in migration
    assert "DELETE FROM tmm_mi_scenario_group_operation_m WHERE source = 'legacy_v1_backfill'" in migration
    assert "UPDATE tmm_mi_scenario_m" not in migration
    assert "UPDATE tmm_mi_signpost_m" not in migration


def test_same_retry_code_for_different_events_preserves_each_reference() -> None:
    async def record() -> list[list[str]]:
        recorder = V4OperationProgressRecorder(120, "01JABCDEF0123456789ABCDEFX", "trace-1")
        append = AsyncMock()
        recorder._append = append  # type: ignore[method-assign]

        await recorder._record_retry(  # noqa: SLF001
            phase="event_analysis",
            attempt=2,
            validation_code="LLM_TIMEOUT",
            reference_ids=["101"],
        )
        await recorder._record_retry(  # noqa: SLF001
            phase="event_analysis",
            attempt=2,
            validation_code="LLM_TIMEOUT",
            reference_ids=["202"],
        )
        await recorder._record_retry(  # noqa: SLF001
            phase="event_analysis",
            attempt=2,
            validation_code="LLM_TIMEOUT",
            reference_ids=[],
        )
        return [item.kwargs["payload"]["referenceIds"] for item in append.await_args_list]

    assert asyncio.run(record()) == [["101"], ["202"]]


def test_remote_tail_uses_adaptive_master_polling_and_reads_history_only_after_sequence_change() -> None:
    async def exercise() -> tuple[list[str], list[float], list[int], int]:
        poll_permissions: asyncio.Queue[None] = asyncio.Queue()
        intervals: list[float] = []

        async def controlled_sleep(interval: float) -> None:
            intervals.append(interval)
            await poll_permissions.get()

        hub = ScenarioGroupOperationEventHub(
            initial_poll_interval_seconds=1.0,
            max_poll_interval_seconds=5.0,
            sleep=controlled_sleep,
        )
        await hub.start()
        get_operation = Mock(
            side_effect=[
                _operation(status="running", latest_sequence=1),
                _operation(status="running", latest_sequence=1),
                _operation(status="succeeded", latest_sequence=2),
            ]
        )
        list_events = Mock(side_effect=[[_event(1, "accepted")], [_event(2, "completed")]])
        try:
            with (
                patch.object(ScenarioGroupOperationService, "get_operation", get_operation),
                patch.object(ScenarioGroupOperationService, "list_events_after", list_events),
            ):
                stream = stream_operation_events(
                    _ConnectedRequest(),  # type: ignore[arg-type]
                    120,
                    "01JABCDEF0123456789ABCDEFX",
                    after_sequence=0,
                    event_hub=hub,
                    keepalive_interval_seconds=60,
                )
                first = await anext(stream)
                next_chunk = asyncio.create_task(anext(stream))

                poll_permissions.put_nowait(None)
                while get_operation.call_count < 2:
                    await asyncio.sleep(0)
                history_calls_while_unchanged = list_events.call_count

                poll_permissions.put_nowait(None)
                second = await asyncio.wait_for(next_chunk, timeout=1)
                await stream.aclose()
        finally:
            await hub.shutdown()

        cursors = [item.args[2] for item in list_events.call_args_list]
        return [first, second], intervals, cursors, history_calls_while_unchanged

    chunks, intervals, cursors, unchanged_history_calls = asyncio.run(exercise())

    assert [chunk.splitlines()[0] for chunk in chunks] == ["id: 1", "id: 2"]
    assert intervals[:2] == [1.0, 2.0]
    assert cursors == [0, 1]
    assert unchanged_history_calls == 1


def test_remote_subscribers_share_one_operation_master_watcher() -> None:
    async def exercise() -> tuple[int, int, int]:
        poll_permissions: asyncio.Queue[None] = asyncio.Queue()

        async def controlled_sleep(_: float) -> None:
            await poll_permissions.get()

        hub = ScenarioGroupOperationEventHub(sleep=controlled_sleep)
        await hub.start()
        get_operation = Mock(return_value=_operation(status="succeeded", latest_sequence=2))
        try:
            with patch.object(ScenarioGroupOperationService, "get_operation", get_operation):
                async with hub.subscribe(120, "01JABCDEF0123456789ABCDEFX", known_latest_sequence=1) as first:
                    async with hub.subscribe(120, "01JABCDEF0123456789ABCDEFX", known_latest_sequence=1) as second:
                        poll_permissions.put_nowait(None)
                        first_wakeup, second_wakeup = await asyncio.gather(first.get(), second.get())
        finally:
            await hub.shutdown()
        return get_operation.call_count, first_wakeup.latest_sequence, second_wakeup.latest_sequence

    poll_count, first_sequence, second_sequence = asyncio.run(exercise())

    assert poll_count == 1
    assert (first_sequence, second_sequence) == (2, 2)


def test_owner_worker_event_hub_delivers_commit_wakeup_without_db_polling() -> None:
    async def exercise() -> tuple[int, bool]:
        hub = ScenarioGroupOperationEventHub()
        await hub.start()
        hub.register_owner("01JABCDEF0123456789ABCDEFX")
        try:
            with patch.object(ScenarioGroupOperationService, "get_operation") as get_operation:
                async with hub.subscribe(120, "01JABCDEF0123456789ABCDEFX", known_latest_sequence=1) as wakeups:
                    hub.publish("01JABCDEF0123456789ABCDEFX", 2, terminal=False)
                    wakeup = await wakeups.get()
                return get_operation.call_count, wakeup.latest_sequence == 2
        finally:
            hub.unregister_owner("01JABCDEF0123456789ABCDEFX")
            await hub.shutdown()

    poll_count, received = asyncio.run(exercise())

    assert poll_count == 0
    assert received is True


def test_remote_tail_caps_backoff_at_five_seconds_and_resets_after_change() -> None:
    async def exercise() -> tuple[list[float], int]:
        poll_permissions: asyncio.Queue[None] = asyncio.Queue()
        intervals: list[float] = []

        async def controlled_sleep(interval: float) -> None:
            intervals.append(interval)
            await poll_permissions.get()

        hub = ScenarioGroupOperationEventHub(sleep=controlled_sleep)
        await hub.start()
        get_operation = Mock(
            side_effect=[
                _operation(status="running", latest_sequence=1),
                _operation(status="running", latest_sequence=2),
                _operation(status="running", latest_sequence=2),
                _operation(status="running", latest_sequence=2),
                _operation(status="running", latest_sequence=2),
                _operation(status="succeeded", latest_sequence=3),
            ]
        )
        try:
            with patch.object(ScenarioGroupOperationService, "get_operation", get_operation):
                async with hub.subscribe(120, "01JABCDEF0123456789ABCDEFX", known_latest_sequence=1) as wakeups:
                    for _ in range(6):
                        poll_permissions.put_nowait(None)
                    while get_operation.call_count < 6:
                        await asyncio.sleep(0)
                    wakeup = await wakeups.get()
                    if not wakeup.terminal:
                        wakeup = await wakeups.get()
        finally:
            await hub.shutdown()
        return intervals, wakeup.latest_sequence

    intervals, latest_sequence = asyncio.run(exercise())

    assert intervals == [1.0, 2.0, 1.0, 2.0, 4.0, 5.0]
    assert latest_sequence == 3


def test_sse_disconnect_does_not_cancel_registered_producer() -> None:
    async def exercise() -> bool:
        runner = ScenarioGroupOperationTaskRunner()
        finished = asyncio.Event()

        async def producer() -> None:
            await asyncio.sleep(0)
            finished.set()

        await runner.start()
        runner.submit("01JABCDEF0123456789ABCDEFX", producer())
        chunks = [
            chunk
            async for chunk in stream_operation_events(
                _DisconnectedRequest(),  # type: ignore[arg-type]
                120,
                "01JABCDEF0123456789ABCDEFX",
                after_sequence=0,
            )
        ]
        await asyncio.wait_for(finished.wait(), timeout=1)
        await runner.shutdown()
        return not chunks and finished.is_set()

    assert asyncio.run(exercise())


def test_running_operation_blocks_soft_delete_with_409() -> None:
    session = Mock()
    group_repository = Mock()
    group_repository.fetch_by_id_for_query.return_value = SimpleNamespace(request_usr_id=7)
    operation_repository = Mock()
    operation_repository.fetch_active.return_value = SimpleNamespace(status="running", operation_id="op-running")
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]

    with (
        patch.dict(
            sys.modules,
            {"apps.common.configs.database.sync_database.connection": connection_module},
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
    ):
        with pytest.raises(MIBaseError) as caught:
            ScenarioGroupService().soft_delete_group_for_owner(120, user_id=7)

    assert caught.value.status_code == 409
