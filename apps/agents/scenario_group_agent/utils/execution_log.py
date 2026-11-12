from __future__ import annotations

# ruff: noqa: CPY001, ANN401
import asyncio
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from functools import wraps
from time import perf_counter
from typing import Any, Literal
from uuid import uuid4

from apps.agents.scenario_group_agent.schemas.api.execution_log import AgentExecutionEvent
from apps.common.logging.console import full_console_logs
from apps.common.logging.logger_config import logger


class ExecutionTrace:
    def __init__(self, feature: str, run_id: str, parent_run_id: str | None = None) -> None:
        self.feature = feature
        self.run_id = run_id
        self.parent_run_id = parent_run_id
        self.started = perf_counter()
        self.events: list[AgentExecutionEvent] = []
        self.persisted_sequence = 0


_current_trace: ContextVar[ExecutionTrace | None] = ContextVar("scenario_execution_trace", default=None)


def execution_event(
    phase: str,
    summary: str,
    *,
    status: Literal["started", "completed", "failed", "interrupted", "skipped", "warning"] = "completed",
    **details: Any,
) -> AgentExecutionEvent | None:
    trace = _current_trace.get()
    if trace is None:
        return None
    event = AgentExecutionEvent(
        run_id=trace.run_id,
        parent_run_id=trace.parent_run_id,
        sequence=len(trace.events) + 1,
        feature=trace.feature,
        phase=phase,
        status=status,
        summary=summary,
        occurred_at=datetime.now(UTC),
        elapsed_ms=round((perf_counter() - trace.started) * 1000),
        details=details,
    )
    trace.events.append(event)
    logger.bind(agent_execution=event.model_dump(mode="json", by_alias=True)).info(
        "[AGENT_EXECUTION] {} | {} | {}",
        phase,
        summary,
        event.model_dump_json(by_alias=True),
    )
    return event


def execution_events() -> list[AgentExecutionEvent]:
    trace = _current_trace.get()
    return list(trace.events) if trace else []


def logged_run[**P, R](
    feature: str,
    *,
    operation_arg: int | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Isolate concurrent requests; operation IDs link background work to existing APIs."""

    def decorate(function: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(function)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            with full_console_logs():
                parent = _current_trace.get()
                operation_id = (
                    args[operation_arg]
                    if operation_arg is not None and len(args) > operation_arg
                    else kwargs.get("operation_id")
                )
                trace = ExecutionTrace(feature, str(operation_id or uuid4()), parent.run_id if parent else None)
                token = _current_trace.set(trace)
                execution_event("execution", "실행을 시작합니다.", status="started")
                try:
                    result = await function(*args, **kwargs)
                except asyncio.CancelledError:
                    execution_event("execution", "실행이 취소되었습니다.", status="interrupted")
                    raise
                except Exception as exc:
                    # Exception messages, prompts and credentials are deliberately excluded.
                    execution_event("execution", "실행에 실패했습니다.", status="failed", errorType=type(exc).__name__)
                    raise
                else:
                    failed = any(e.phase == "outcome" and e.status in {"failed", "interrupted"} for e in trace.events)
                    if not failed:
                        execution_event("execution", "요청 처리가 종료되었습니다. 세부 판정은 결과를 확인하세요.")
                    if result is not None and hasattr(result, "execution_log"):
                        result.execution_log = list(trace.events)
                    return result
                finally:
                    _current_trace.reset(token)

        return wrapped

    return decorate


async def traced_call[T](
    kind: str,
    name: str,
    function: Callable[..., Awaitable[T]],
    /,
    *args: Any,
    **kwargs: Any,
) -> T:
    call_id = str(uuid4())
    started = perf_counter()
    execution_event("call", f"{name} 호출", status="started", callId=call_id, kind=kind, name=name)
    try:
        result = await function(*args, **kwargs)
    except asyncio.CancelledError:
        execution_event(
            "call",
            f"{name} 취소",
            status="interrupted",
            callId=call_id,
            kind=kind,
            name=name,
            durationMs=round((perf_counter() - started) * 1000),
        )
        raise
    except Exception as exc:
        execution_event(
            "call",
            f"{name} 실패",
            status="failed",
            callId=call_id,
            kind=kind,
            name=name,
            durationMs=round((perf_counter() - started) * 1000),
            errorType=type(exc).__name__,
        )
        raise
    execution_event(
        "call",
        f"{name} 호출 완료",
        callId=call_id,
        kind=kind,
        name=name,
        durationMs=round((perf_counter() - started) * 1000),
    )
    return result


async def traced_llm_call[T](function: Callable[..., Awaitable[T]], **kwargs: Any) -> T:
    call_name = kwargs.pop("call_name", None) or kwargs.get("log_label") or "structured_output"
    return await traced_call("llm", str(call_name), function, **kwargs)


async def persist_execution_events(group_id: int, operation_id: str, phase: str) -> None:
    """Checkpoint a bounded batch in the existing operation timeline; telemetry must not break work."""
    from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
        ScenarioGroupOperationService,
    )

    trace = _current_trace.get()
    if trace is None:
        return
    pending = trace.events[trace.persisted_sequence :]
    if not pending:
        return
    try:
        await asyncio.to_thread(
            ScenarioGroupOperationService().append_event,
            group_id,
            operation_id,
            event_type="progress",
            phase=phase,
            title=pending[-1].summary[:255],
            message_markdown=pending[-1].summary,
            payload={"executionLog": [event.model_dump(mode="json", by_alias=True) for event in pending]},
        )
    except Exception as exc:
        logger.warning(
            "Execution log checkpoint failed | operation_id={} | error_type={}",
            operation_id,
            type(exc).__name__,
        )
    else:
        trace.persisted_sequence += len(pending)
