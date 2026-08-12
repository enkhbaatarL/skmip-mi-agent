from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
from types import TracebackType
from typing import Any, Protocol, cast
from uuid import uuid4

from pydantic import BaseModel, Field

from apps.common.logging.logger_config import logger


class TraceContext(BaseModel):
    transaction_id: str = Field(
        description=(
            "요청 단위 trace ID. AIP aip-transaction-id header, MLflow aip.transaction_id, "
            "LangGraph transaction_id로 사용된다."
        ),
    )
    app_identifier: str = Field(
        description=(
            "A.X Platform app ID. AIP aip-app-id header, MLflow aip.app_id/app_id로 사용된다."
        ),
    )
    agent_name: str | None = Field(
        default=None,
        description=(
            "Agent 설정 profile key. MLflow tracing on/off와 experiment 설정 조회 기준으로 사용된다."
        ),
    )
    api_identifier: str | None = Field(
        default=None,
        description=(
            "API/flow 단위 식별자. MLflow api_identifier metadata/tag로 기록된다. 예: create_scenarios"
        ),
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "business session ID. MLflow session_id, LangGraph thread_id/session_id, "
            "AIP aip-chat-id header로 사용된다."
        ),
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Agent/flow별 MLflow trace tag. app_id, session_id, api_identifier 공통 태그는 "
            "이 값보다 우선한다."
        ),
    )


class _TraceManager(Protocol):
    def __enter__(self) -> object:
        pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> object:
        pass


_current_langchain_callbacks: ContextVar[Any | None] = ContextVar("current_langchain_callbacks", default=None)


def new_transaction_id() -> str:
    return str(uuid4())


def build_aip_headers(context: TraceContext) -> dict[str, str]:
    headers = {
        "aip-transaction-id": context.transaction_id,
        "aip-app-id": context.app_identifier,
    }
    if context.session_id:
        headers["aip-chat-id"] = context.session_id
    return headers


def build_langgraph_config(context: TraceContext) -> dict[str, object]:
    # thread_id 가 mlflow의 session_id가 됨. mlflow 에서 키값을 고정해놓음
    configurable = {
        "thread_id": context.session_id or context.transaction_id,
        "transaction_id": context.transaction_id,
    }
    if context.session_id:
        configurable["session_id"] = context.session_id
    return {"configurable": configurable}


@contextmanager
def langchain_callbacks_context(callbacks: Any | None) -> Iterator[None]:  # noqa: ANN401
    token = _current_langchain_callbacks.set(callbacks)
    try:
        yield
    finally:
        _current_langchain_callbacks.reset(token)


def get_current_langchain_callbacks() -> Any | None:  # noqa: ANN401
    return _current_langchain_callbacks.get()


def _mlflow_metadata(context: TraceContext) -> dict[str, str]:
    metadata = {
        "aip.transaction_id": context.transaction_id,
        "aip.app_id": context.app_identifier,
    }
    if context.session_id:
        metadata["session_id"] = context.session_id
    if context.api_identifier:
        metadata["api_identifier"] = context.api_identifier
    return metadata


def _mlflow_tags(context: TraceContext) -> dict[str, str]:
    tags = dict(context.tags)
    tags["app_id"] = context.app_identifier
    if context.session_id:
        tags["session_id"] = context.session_id
    if context.api_identifier:
        tags["api_identifier"] = context.api_identifier
    return tags


def _is_mlflow_tracing_enabled(context: TraceContext) -> bool:
    try:
        from apps.common.configs.config import get_settings

        cfg = get_settings()
        is_enabled = getattr(cfg, "is_mlflow_tracing_enabled", None)
        if callable(is_enabled):
            return bool(is_enabled(agent_name=context.agent_name))
        return bool(getattr(cfg, "mlflow_tracing_enabled", False))
    except Exception as exc:
        logger.warning(f"MLflow tracing disabled because settings lookup failed | error={exc!r}")
        return False


def _enter_mlflow_manager(manager: _TraceManager) -> bool:
    try:
        manager.__enter__()
    except Exception as exc:
        logger.warning(f"MLflow tracing context enter failed, continuing without tracing | error={exc!r}")
        return False
    return True


def _exit_mlflow_manager(
    manager: _TraceManager,
    exc_type: type[BaseException] | None = None,
    exc: BaseException | None = None,
    traceback: TracebackType | None = None,
) -> None:
    try:
        manager.__exit__(exc_type, exc, traceback)
    except Exception as exit_exc:
        logger.warning(f"MLflow tracing context exit failed, continuing without tracing | error={exit_exc!r}")


def _create_mlflow_manager(
    mlflow_module: Any,  # noqa: ANN401
    context_kwargs: dict[str, Any],
    metadata: dict[str, str],
    session_id: str | None,
) -> _TraceManager | None:
    try:
        return cast("_TraceManager", mlflow_module.tracing.context(**context_kwargs))
    except TypeError as exc:
        logger.warning(f"MLflow tracing context kwargs unsupported, retrying fallback | error={exc!r}")
        fallback_kwargs: dict[str, Any] = {"metadata": metadata}
        if session_id:
            fallback_kwargs["session_id"] = session_id
        try:
            return cast("_TraceManager", mlflow_module.tracing.context(**fallback_kwargs))
        except Exception as fallback_exc:
            logger.warning(
                "MLflow tracing context creation failed, continuing without tracing | "
                f"error={fallback_exc!r}",
            )
            return None
    except Exception as exc:
        logger.warning(f"MLflow tracing context creation failed, continuing without tracing | error={exc!r}")
        return None


@contextmanager
def mlflow_trace_context(context: TraceContext) -> Iterator[None]:
    if not _is_mlflow_tracing_enabled(context):
        with nullcontext():
            yield
        return

    try:
        import mlflow
    except Exception as exc:
        logger.warning(f"MLflow tracing disabled because mlflow import failed | error={exc!r}")
        with nullcontext():
            yield
        return

    metadata = _mlflow_metadata(context)
    tags = _mlflow_tags(context)
    session_id = context.session_id
    context_kwargs: dict[str, Any] = {
        "metadata": metadata,
        "tags": tags,
    }
    if session_id:
        context_kwargs["session_id"] = session_id

    manager = _create_mlflow_manager(mlflow, context_kwargs, metadata, session_id)
    if manager is None:
        with nullcontext():
            yield
        return

    if not _enter_mlflow_manager(manager):
        with nullcontext():
            yield
        return

    try:
        yield
    except BaseException as exc:
        _exit_mlflow_manager(manager, type(exc), exc, exc.__traceback__)
        raise
    else:
        _exit_mlflow_manager(manager)
