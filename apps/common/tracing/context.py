from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from typing import Any
from uuid import uuid4

from pydantic import BaseModel


class TraceContext(BaseModel):
    transaction_id: str
    app_identifier: str
    scenario_group_id: str | None = None


def new_transaction_id() -> str:
    return str(uuid4())


def build_aip_headers(context: TraceContext) -> dict[str, str]:
    headers = {
        "aip-transaction-id": context.transaction_id,
        "aip-app-id": context.app_identifier,
    }
    if context.scenario_group_id:
        headers["aip-chat-id"] = context.scenario_group_id
    return headers


def build_langgraph_config(context: TraceContext) -> dict[str, object]:
    return {"configurable": {"thread_id": context.transaction_id}}


def _mlflow_metadata(context: TraceContext) -> dict[str, str]:
    metadata = {
        "aip.transaction_id": context.transaction_id,
        "aip.app_id": context.app_identifier,
    }
    if context.scenario_group_id:
        metadata["scenario_group_id"] = context.scenario_group_id
    return metadata


def _mlflow_tags(context: TraceContext) -> dict[str, str]:
    tags = {"app_id": context.app_identifier}
    if context.scenario_group_id:
        tags["scenario_group_id"] = context.scenario_group_id
    return tags


@contextmanager
def mlflow_trace_context(context: TraceContext) -> Iterator[None]:
    try:
        import mlflow
    except Exception:
        with nullcontext():
            yield
        return

    metadata = _mlflow_metadata(context)
    tags = _mlflow_tags(context)
    session_id = context.scenario_group_id
    context_kwargs: dict[str, Any] = {
        "client_request_id": context.transaction_id,
        "metadata": metadata,
        "tags": tags,
    }
    if session_id:
        context_kwargs["session_id"] = session_id

    try:
        manager = mlflow.tracing.context(**context_kwargs)
    except TypeError:
        fallback_kwargs: dict[str, Any] = {"metadata": metadata}
        if session_id:
            fallback_kwargs["session_id"] = session_id
        try:
            manager = mlflow.tracing.context(**fallback_kwargs)
        except Exception:
            manager = nullcontext()
    except Exception:
        manager = nullcontext()

    with manager:
        yield
