from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass

from apps.common.logging.logger_config import logger
from apps.persistence.scenario_group_operation.schema import TERMINAL_OPERATION_STATUSES


@dataclass(frozen=True, slots=True)
class OperationEventWakeup:
    latest_sequence: int
    terminal: bool = False


class ScenarioGroupOperationEventHub:
    """Process-local fan-out plus one adaptive DB tail watcher per remote operation."""

    def __init__(
        self,
        *,
        initial_poll_interval_seconds: float = 1.0,
        max_poll_interval_seconds: float = 5.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._initial_poll_interval_seconds = initial_poll_interval_seconds
        self._max_poll_interval_seconds = max_poll_interval_seconds
        self._sleep = sleep
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: dict[str, set[asyncio.Queue[OperationEventWakeup | None]]] = {}
        self._scenario_group_ids: dict[str, int] = {}
        self._latest_sequences: dict[str, int] = {}
        self._owner_operations: set[str] = set()
        self._tail_watchers: dict[str, asyncio.Task[None]] = {}
        self._stopping = False

    async def start(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._stopping = False

    async def shutdown(self) -> None:
        self._stopping = True
        watchers = list(self._tail_watchers.values())
        for watcher in watchers:
            watcher.cancel()
        if watchers:
            await asyncio.gather(*watchers, return_exceptions=True)
        self._tail_watchers.clear()
        for queues in self._subscribers.values():
            for queue in queues:
                self._replace_queue_value(queue, None)
        self._subscribers.clear()
        self._scenario_group_ids.clear()
        self._latest_sequences.clear()
        self._owner_operations.clear()
        self._loop = None

    def register_owner(self, operation_id: str) -> None:
        self._owner_operations.add(operation_id)
        watcher = self._tail_watchers.pop(operation_id, None)
        if watcher is not None:
            watcher.cancel()

    def unregister_owner(self, operation_id: str) -> None:
        self._owner_operations.discard(operation_id)
        self._ensure_tail_watcher(operation_id)

    def publish(self, operation_id: str, latest_sequence: int, *, terminal: bool = False) -> None:
        loop = self._loop
        if loop is None or loop.is_closed() or self._stopping:
            return
        loop.call_soon_threadsafe(
            self._publish_on_loop,
            operation_id,
            OperationEventWakeup(latest_sequence=latest_sequence, terminal=terminal),
        )

    @asynccontextmanager
    async def subscribe(
        self,
        scenario_group_id: int,
        operation_id: str,
        *,
        known_latest_sequence: int,
    ) -> AsyncIterator[asyncio.Queue[OperationEventWakeup | None]]:
        current_loop = asyncio.get_running_loop()
        if self._loop is None or self._loop.is_closed() or self._loop is not current_loop:
            await self.start()
        queue: asyncio.Queue[OperationEventWakeup | None] = asyncio.Queue(maxsize=1)
        self._subscribers.setdefault(operation_id, set()).add(queue)
        self._scenario_group_ids[operation_id] = scenario_group_id
        self._latest_sequences[operation_id] = max(
            known_latest_sequence,
            self._latest_sequences.get(operation_id, 0),
        )
        self._ensure_tail_watcher(operation_id)
        try:
            yield queue
        finally:
            queues = self._subscribers.get(operation_id)
            if queues is not None:
                queues.discard(queue)
                if not queues:
                    self._subscribers.pop(operation_id, None)
                    self._scenario_group_ids.pop(operation_id, None)
                    self._latest_sequences.pop(operation_id, None)
                    watcher = self._tail_watchers.pop(operation_id, None)
                    if watcher is not None:
                        watcher.cancel()

    def _publish_on_loop(self, operation_id: str, wakeup: OperationEventWakeup) -> None:
        queues = self._subscribers.get(operation_id)
        if not queues:
            return
        self._latest_sequences[operation_id] = max(
            wakeup.latest_sequence,
            self._latest_sequences.get(operation_id, 0),
        )
        for queue in queues:
            self._replace_queue_value(queue, wakeup)

    def _ensure_tail_watcher(self, operation_id: str) -> None:
        if (
            self._stopping
            or self._loop is None
            or operation_id in self._owner_operations
            or operation_id not in self._subscribers
            or operation_id in self._tail_watchers
        ):
            return
        scenario_group_id = self._scenario_group_ids.get(operation_id)
        if scenario_group_id is None:
            return
        self._tail_watchers[operation_id] = self._loop.create_task(
            self._watch_remote_operation(scenario_group_id, operation_id),
            name=f"scenario-group-operation-tail:{operation_id}",
        )

    async def _watch_remote_operation(self, scenario_group_id: int, operation_id: str) -> None:
        from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
            ScenarioGroupOperationService,
        )

        interval = self._initial_poll_interval_seconds
        service = ScenarioGroupOperationService()
        current_task = asyncio.current_task()
        try:
            while operation_id in self._subscribers and operation_id not in self._owner_operations:
                await self._sleep(interval)
                operation = await asyncio.to_thread(service.get_operation, scenario_group_id, operation_id)
                previous_sequence = self._latest_sequences.get(operation_id, 0)
                changed = operation.latest_sequence > previous_sequence
                terminal = operation.status in TERMINAL_OPERATION_STATUSES
                if changed or terminal:
                    self._publish_on_loop(
                        operation_id,
                        OperationEventWakeup(
                            latest_sequence=operation.latest_sequence,
                            terminal=terminal,
                        ),
                    )
                if terminal:
                    return
                interval = (
                    self._initial_poll_interval_seconds
                    if changed
                    else min(interval * 2, self._max_poll_interval_seconds)
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error(
                "Scenario Group remote operation tail failed | operation_id={} | error={!r}",
                operation_id,
                exc,
            )
        finally:
            if self._tail_watchers.get(operation_id) is current_task:
                self._tail_watchers.pop(operation_id, None)

    @staticmethod
    def _replace_queue_value(
        queue: asyncio.Queue[OperationEventWakeup | None],
        value: OperationEventWakeup | None,
    ) -> None:
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        queue.put_nowait(value)


class ScenarioGroupOperationTaskRunner:
    """Lifespan-owned registry for producer tasks that outlive SSE consumers."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._accepting = False

    async def start(self) -> None:
        self._accepting = True

    def submit(self, operation_id: str, producer: Awaitable[None]) -> None:
        if not self._accepting:
            # Router-only TestClient apps do not run the project lifespan. The task
            # still belongs to this runner and will be cleaned up by its event loop.
            self._accepting = True
        if operation_id in self._tasks:
            msg = f"Operation task already registered: {operation_id}"
            raise RuntimeError(msg)
        get_scenario_group_operation_event_hub().register_owner(operation_id)
        task = asyncio.create_task(producer, name=f"scenario-group-operation:{operation_id}")
        self._tasks[operation_id] = task
        task.add_done_callback(lambda completed: self._discard(operation_id, completed))

    async def shutdown(self) -> None:
        self._accepting = False
        tasks = list(self._tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()

    def _discard(self, operation_id: str, task: asyncio.Task[None]) -> None:
        self._tasks.pop(operation_id, None)
        get_scenario_group_operation_event_hub().unregister_owner(operation_id)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Scenario Group operation producer escaped | operation_id={} | error={!r}",
                operation_id,
                error,
            )


_operation_task_runner = ScenarioGroupOperationTaskRunner()
_operation_event_hub = ScenarioGroupOperationEventHub()


def get_scenario_group_operation_task_runner() -> ScenarioGroupOperationTaskRunner:
    return _operation_task_runner


def get_scenario_group_operation_event_hub() -> ScenarioGroupOperationEventHub:
    return _operation_event_hub
