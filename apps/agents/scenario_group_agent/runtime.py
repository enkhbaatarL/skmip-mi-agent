from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import uuid4

from apps.common.logging.logger_config import logger
from apps.persistence.scenario_group_operation.schema import TERMINAL_OPERATION_STATUSES


_OperationResult = TypeVar("_OperationResult")


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
                try:
                    operation = await asyncio.to_thread(service.get_operation, scenario_group_id, operation_id)
                except Exception as exc:
                    interval = min(interval * 2, self._max_poll_interval_seconds)
                    logger.warning(
                        "Scenario Group remote operation tail poll failed; retrying | "
                        "operation_id={} | retry_in_seconds={} | error={!r}",
                        operation_id,
                        interval,
                        exc,
                    )
                    continue
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

    def __init__(
        self,
        *,
        heartbeat_interval_seconds: float = 30.0,
        touch_heartbeat: Callable[[int, str], bool] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._accepting = False
        self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._touch_heartbeat = touch_heartbeat or self._touch_active_heartbeat
        self._sleep = sleep

    async def start(self, *, heartbeat_interval_seconds: float | None = None) -> None:
        if heartbeat_interval_seconds is not None:
            self._heartbeat_interval_seconds = heartbeat_interval_seconds
        self._accepting = True

    def submit(self, scenario_group_id: int, operation_id: str, producer: Awaitable[None]) -> None:
        if not self._accepting:
            # Router-only TestClient apps do not run the project lifespan. The task
            # still belongs to this runner and will be cleaned up by its event loop.
            self._accepting = True
        if operation_id in self._tasks:
            msg = f"Operation task already registered: {operation_id}"
            raise RuntimeError(msg)
        get_scenario_group_operation_event_hub().register_owner(operation_id)
        task = asyncio.create_task(
            self.run_with_heartbeat(scenario_group_id, operation_id, producer),
            name=f"scenario-group-operation:{operation_id}",
        )
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

    async def run_with_heartbeat(
        self,
        scenario_group_id: int,
        operation_id: str,
        operation: Awaitable[_OperationResult],
    ) -> _OperationResult:
        owner_task = asyncio.current_task()
        heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(scenario_group_id, operation_id, owner_task),
            name=f"scenario-group-operation-heartbeat:{operation_id}",
        )
        try:
            return await operation
        finally:
            heartbeat_task.cancel()
            await asyncio.gather(heartbeat_task, return_exceptions=True)

    async def _heartbeat_loop(
        self,
        scenario_group_id: int,
        operation_id: str,
        owner_task: asyncio.Task[object] | None,
    ) -> None:
        while True:
            await self._sleep(self._heartbeat_interval_seconds)
            try:
                touched = await asyncio.to_thread(
                    self._touch_heartbeat,
                    scenario_group_id,
                    operation_id,
                )
            except Exception as exc:
                logger.warning(
                    "Scenario Group operation heartbeat failed; retrying | "
                    "operation_id={} | retry_in_seconds={} | error={!r}",
                    operation_id,
                    self._heartbeat_interval_seconds,
                    exc,
                )
                continue
            if touched:
                continue
            if owner_task is not None and owner_task is not asyncio.current_task():
                owner_task.cancel()
            return

    @staticmethod
    def _touch_active_heartbeat(scenario_group_id: int, operation_id: str) -> bool:
        from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
            ScenarioGroupOperationService,
        )

        return ScenarioGroupOperationService().touch_active_heartbeat(scenario_group_id, operation_id)

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


class ScenarioGroupOperationRecoveryMonitor:
    """Periodically marks active operations with expired heartbeats as interrupted."""

    def __init__(
        self,
        *,
        stale_after_seconds: float = 120.0,
        scan_interval_seconds: float = 30.0,
        recover_stale: Callable[[datetime], object] | None = None,
        now: Callable[[], datetime] | None = None,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._stale_after_seconds = stale_after_seconds
        self._scan_interval_seconds = scan_interval_seconds
        self._recover_stale = recover_stale or self._interrupt_stale_operations
        self._now = now or self._utc_now
        self._sleep = sleep
        self._task: asyncio.Task[None] | None = None

    async def start(
        self,
        *,
        stale_after_seconds: float | None = None,
        scan_interval_seconds: float | None = None,
    ) -> None:
        if stale_after_seconds is not None:
            self._stale_after_seconds = stale_after_seconds
        if scan_interval_seconds is not None:
            self._scan_interval_seconds = scan_interval_seconds
        await self._recover_once()
        self._task = asyncio.create_task(self._run(), name="scenario-group-operation-reaper")

    async def shutdown(self) -> None:
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def _run(self) -> None:
        while True:
            await self._sleep(self._scan_interval_seconds)
            await self._recover_once()

    async def _recover_once(self) -> None:
        cutoff = self._now() - timedelta(seconds=self._stale_after_seconds)
        try:
            recovered = await asyncio.to_thread(self._recover_stale, cutoff)
        except Exception as exc:
            logger.warning(
                "Scenario Group stale operation recovery failed; retrying | retry_in_seconds={} | error={!r}",
                self._scan_interval_seconds,
                exc,
            )
            return
        recovered_count = len(recovered) if hasattr(recovered, "__len__") else 0
        if recovered_count:
            logger.warning(
                "Scenario Group stale operations interrupted | count={} | cutoff={}",
                recovered_count,
                cutoff.isoformat(),
            )

    @staticmethod
    def _interrupt_stale_operations(heartbeat_cutoff: datetime) -> object:
        from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
            ScenarioGroupOperationService,
        )

        return ScenarioGroupOperationService().interrupt_stale_operations(heartbeat_cutoff)

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)


class AdditionalDimensionTaskRunner:
    """Lifespan-owned auxiliary tasks that are independent from create operation status."""

    def __init__(self) -> None:
        self._tasks: dict[int, asyncio.Task[None]] = {}
        self._run_ids: dict[int, str] = {}
        self._accepting = False

    async def start(self) -> None:
        self._accepting = True

    def submit(self, scenario_group_id: int) -> str:
        if scenario_group_id in self._tasks:
            logger.info(
                "Additional Dimension background task submit skipped | scenario_group_id={} | "
                "reason=already_registered",
                scenario_group_id,
            )
            return self._run_ids[scenario_group_id]
        if not self._accepting:
            self._accepting = True
        from apps.agents.scenario_group_agent.flows.add_dimension.flow import run_additional_dimension_generation

        run_id = str(uuid4())
        task = asyncio.create_task(
            run_additional_dimension_generation(scenario_group_id, run_id=run_id),
            name=f"additional-dimension:{scenario_group_id}",
        )
        self._tasks[scenario_group_id] = task
        self._run_ids[scenario_group_id] = run_id
        task.add_done_callback(lambda completed: self._discard(scenario_group_id, completed))
        logger.info(
            "Additional Dimension background task submitted | scenario_group_id={} | run_id={}",
            scenario_group_id,
            run_id,
        )
        return run_id

    async def shutdown(self) -> None:
        self._accepting = False
        owned_runs = [
            (scenario_group_id, run_id, self._tasks[scenario_group_id])
            for scenario_group_id, run_id in self._run_ids.items()
            if scenario_group_id in self._tasks
        ]
        tasks = [task for _scenario_group_id, _run_id, task in owned_runs]
        for task in tasks:
            if not task.done():
                task.cancel("server_shutdown")
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        if owned_runs:
            from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService

            service = ScenarioGroupService()
            results = await asyncio.gather(
                *(
                    asyncio.to_thread(
                        service.interrupt_additional_dimension_generation,
                        scenario_group_id,
                        run_id=run_id,
                    )
                    for scenario_group_id, run_id, _task in owned_runs
                ),
                return_exceptions=True,
            )
            for (scenario_group_id, run_id, _task), result in zip(owned_runs, results, strict=True):
                if isinstance(result, Exception):
                    logger.error(
                        "Additional Dimension shutdown status update failed | scenario_group_id={} | "
                        "run_id={} | error={!r}",
                        scenario_group_id,
                        run_id,
                        result,
                    )
        self._tasks.clear()
        self._run_ids.clear()

    def _discard(self, scenario_group_id: int, task: asyncio.Task[None]) -> None:
        self._tasks.pop(scenario_group_id, None)
        self._run_ids.pop(scenario_group_id, None)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error(
                "Additional Dimension task escaped | scenario_group_id={} | error={!r}",
                scenario_group_id,
                error,
            )


_operation_task_runner = ScenarioGroupOperationTaskRunner()
_operation_event_hub = ScenarioGroupOperationEventHub()
_operation_recovery_monitor = ScenarioGroupOperationRecoveryMonitor()
_additional_dimension_task_runner = AdditionalDimensionTaskRunner()


def get_scenario_group_operation_task_runner() -> ScenarioGroupOperationTaskRunner:
    return _operation_task_runner


def get_scenario_group_operation_event_hub() -> ScenarioGroupOperationEventHub:
    return _operation_event_hub


def get_scenario_group_operation_recovery_monitor() -> ScenarioGroupOperationRecoveryMonitor:
    return _operation_recovery_monitor


def get_additional_dimension_task_runner() -> AdditionalDimensionTaskRunner:
    return _additional_dimension_task_runner
