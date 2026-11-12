from __future__ import annotations

# ruff: noqa: CPY001
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
import json
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from loguru import Record


_full_payloads: ContextVar[bool] = ContextVar("full_console_payloads", default=False)
_HEADER = "<green>[{time:YYYY-MM-DD HH:mm:ss.SSS}]</green> <level>[{level:8}]</level>"
_SOURCE = "<cyan>[{name}:{function}:{line}]</cyan>"
_RULE = "─" * 80


def full_payloads_enabled() -> bool:
    return _full_payloads.get()


@contextmanager
def full_console_logs(*, enabled: bool = True) -> Iterator[None]:
    """Scope presentation and unabridged payloads to this request and its child tasks."""
    if not enabled:
        yield
        return
    token = _full_payloads.set(True)
    try:
        yield
    finally:
        _full_payloads.reset(token)


def format_console_record(record: Record) -> str:
    """Keep original message/extra intact; only the console representation is expanded."""
    event = record["extra"].get("agent_execution")
    if isinstance(event, dict):
        try:
            body = json.dumps(event, ensure_ascii=False, indent=2, allow_nan=False)
        except (TypeError, ValueError, OverflowError):
            # Invalid telemetry must not hide the original log or traceback.
            return _HEADER + " " + _SOURCE + "\n{message}\n{exception}"
        record["extra"]["_console_body"] = body
        record["extra"]["_console_heading"] = " | ".join(
            str(event.get(key, "")) for key in ("feature", "phase", "status")
        )
        # Use placeholders: braces/markup in model output must never become format instructions.
        return (
            "\n<cyan>"
            + _RULE
            + "</cyan>\n"
            + _HEADER
            + " <level>[AGENT_EXECUTION]</level> {extra[_console_heading]}\n"
            + _SOURCE
            + "\n{extra[_console_body]}\n"
            + "<cyan>"
            + _RULE
            + "</cyan>\n{exception}"
        )
    if full_payloads_enabled():
        return _HEADER + "\n" + _SOURCE + "\n{message}\n{exception}"
    return _HEADER + " " + _SOURCE + " {message}\n{exception}"
