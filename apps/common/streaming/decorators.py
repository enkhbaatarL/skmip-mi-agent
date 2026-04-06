from __future__ import annotations

import inspect
import time
from functools import wraps
from typing import Any, Callable

from langgraph.config import get_stream_writer

from apps.common.streaming.texts import STREAM_TEXTS


def stream_step(step_key: str | None = None, label: str | None = None):
    def decorator(fn: Callable[..., Any]):
        is_async = inspect.iscoroutinefunction(fn)
        event_key = step_key or fn.__name__

        def _get_text(phase: str) -> str:
            # phase: "start" | "end"
            if label:
                return f"{label} {'시작' if phase == 'start' else '완료'}"

            d = STREAM_TEXTS.get(event_key)
            if d and phase in d:
                return d[phase]
            return f"{event_key} {'시작' if phase == 'start' else '완료'}"

        @wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any):
            writer = get_stream_writer()
            t0 = time.perf_counter()

            writer(
                {
                    "state": "progress",
                    "data": "message",
                    "node": event_key,
                    "value": _get_text("start"),
                    "type": "node_start",
                },
            )
            try:
                out = await fn(*args, **kwargs)
            except Exception as e:
                writer(
                    {
                        "state": "error",
                        "data": "message",
                        "node": event_key,
                        "value": f"{event_key} 실패: {e}",
                        "type": "error",
                    },
                )
                raise

            dt_ms = int((time.perf_counter() - t0) * 1000)
            writer(
                {
                    "state": "progress",
                    "data": "message",
                    "node": event_key,
                    "value": _get_text("end"),
                    "type": "node_end",
                    "latency_ms": dt_ms,
                },
            )
            return out

        @wraps(fn)
        def sync_wrapper(*args: Any, **kwargs: Any):
            writer = get_stream_writer()
            t0 = time.perf_counter()

            writer(
                {
                    "state": "progress",
                    "data": "message",
                    "node": event_key,
                    "value": _get_text("start"),
                    "type": "node_start",
                },
            )
            try:
                out = fn(*args, **kwargs)
            except Exception as e:
                writer(
                    {
                        "state": "error",
                        "data": "message",
                        "node": event_key,
                        "value": f"{event_key} 실패: {e}",
                        "type": "error",
                    },
                )
                raise

            dt_ms = int((time.perf_counter() - t0) * 1000)
            writer(
                {
                    "state": "progress",
                    "data": "message",
                    "node": event_key,
                    "value": _get_text("end"),
                    "type": "node_end",
                    "latency_ms": dt_ms,
                },
            )
            return out

        return async_wrapper if is_async else sync_wrapper

    return decorator
