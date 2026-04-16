#   agents/event_flow_agent/flows/event_flow_runtime.py

from __future__ import annotations

from typing import TypeVar

from apps.common.runtime.runtime import ensure_runtime_context_ready
from apps.common.runtime.usage_context import reset_usage

T = TypeVar("T")


async def ensure_runtime(x: T, **_: object) -> T:
    await ensure_runtime_context_ready()
    reset_usage()
    return x