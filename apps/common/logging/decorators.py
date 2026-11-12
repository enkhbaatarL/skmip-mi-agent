"""Logging decorators for nodes, tools, and connectors.

Usage:
    from apps.common.logging.decorators import log_node, log_tool, log_connector

    @log_node
    async def my_node(state: MariAgentState) -> MariAgentState:
        ...

    @log_tool
    async def my_tool(param: str) -> Result:
        ...

    @log_connector(connector_type="LLM", log_input=False, log_output=False)
    async def invoke_llm(...):
        ...
"""

from __future__ import annotations

from collections.abc import Callable
import functools
import inspect
import json
import time
from typing import Any, ParamSpec, TypeVar

from pydantic import BaseModel

from apps.common.logging.console import full_payloads_enabled
from apps.common.logging.logger_config import logger


P = ParamSpec("P")
T = TypeVar("T")


# ============================================
# Serialization Utilities
# ============================================


def serialize(obj: Any, max_length: int = 2000) -> str:
    """Serialize objects for logging with truncation support.

    Args:
        obj: Object to serialize (BaseModel, dict, list, or any).
        max_length: Maximum length of output string. Truncates if exceeded.

    Returns:
        JSON string representation of the object.

    """
    if full_payloads_enabled():
        # Preserve all logged content, including newlines and literal backslash sequences.
        try:
            if isinstance(obj, BaseModel):
                obj = obj.model_dump(mode="json")
            if isinstance(obj, (dict, list, tuple)):
                return json.dumps(obj, ensure_ascii=False, indent=2, default=str)
            return str(obj)
        except Exception:
            return repr(obj)
    if obj is None:
        return "None"

    try:
        if isinstance(obj, BaseModel):
            result = obj.model_dump_json()
        elif isinstance(obj, (dict, list)):
            result = json.dumps(obj, ensure_ascii=False, default=str)
        else:
            result = str(obj)
    except Exception:
        result = repr(obj)

    result = result.replace("\n", " ").replace("\\n", " ")
    if len(result) > max_length:
        return result[:max_length] + f"... [truncated, total {len(result)} chars]"
    return result


def compute_state_diff(before: BaseModel, after: BaseModel) -> dict[str, Any]:
    """Compute changed fields between two Pydantic model states.

    Args:
        before: State before node execution.
        after: State after node execution.

    Returns:
        Dict with changed field names as keys and {"before": ..., "after": ...} as values.

    """
    before_dict = before.model_dump()
    after_dict = after.model_dump()

    diff: dict[str, Any] = {}
    all_keys = set(before_dict.keys()) | set(after_dict.keys())

    for key in all_keys:
        before_val = before_dict.get(key)
        after_val = after_dict.get(key)

        if before_val != after_val:
            diff[key] = {
                "before": before_val,
                "after": after_val,
            }

    return diff


# ============================================
# Node Logging Decorator
# ============================================


def log_node(func: Callable[P, T]) -> Callable[P, T]:
    """Log node execution with state diff tracking.

    Logging levels:
        - INFO: Node start/end with elapsed time
        - DEBUG: State diff (changed fields only)
        - ERROR: Exception details

    Works with both sync and async functions.
    Designed to stack with @stream_step decorator.

    """
    is_async = inspect.iscoroutinefunction(func)
    node_name = func.__name__

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        # Extract state from first positional argument
        state = args[0] if args else kwargs.get("state")
        state_before = state.model_copy(deep=True) if hasattr(state, "model_copy") else None

        logger.info(f"[NODE][{node_name}] START")
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            # Compute and log state diff at DEBUG level
            if state_before is not None and hasattr(result, "model_dump"):
                diff = compute_state_diff(state_before, result)
                if diff:
                    logger.debug(f"[NODE][{node_name}] STATE_DIFF | diff={serialize(diff)}")

            logger.info(f"[NODE][{node_name}] END | elapsed={elapsed_ms}ms")
            return result

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"[NODE][{node_name}] FAILED | elapsed={elapsed_ms}ms | error={e!r}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        state = args[0] if args else kwargs.get("state")
        state_before = state.model_copy(deep=True) if hasattr(state, "model_copy") else None

        logger.info(f"[NODE][{node_name}] START")
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            if state_before is not None and hasattr(result, "model_dump"):
                diff = compute_state_diff(state_before, result)
                if diff:
                    logger.debug(f"[NODE][{node_name}] STATE_DIFF | diff={serialize(diff)}")

            logger.info(f"[NODE][{node_name}] END | elapsed={elapsed_ms}ms")
            return result

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"[NODE][{node_name}] FAILED | elapsed={elapsed_ms}ms | error={e!r}")
            raise

    return async_wrapper if is_async else sync_wrapper  # type: ignore[return-value]


# ============================================
# Tool Logging Decorator
# ============================================


def log_tool(func: Callable[P, T]) -> Callable[P, T]:
    """Log tool execution with start/end and failure details.

    Logging levels:
        - INFO: Tool start/end with elapsed time
        - ERROR: Exception details

    Works with both sync and async functions.

    """
    is_async = inspect.iscoroutinefunction(func)
    tool_name = func.__name__

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.info(f"[TOOL][{tool_name}] START")
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(f"[TOOL][{tool_name}] END | elapsed={elapsed_ms}ms")
            return result

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"[TOOL][{tool_name}] FAILED | elapsed={elapsed_ms}ms | args={serialize(args)} | kwargs={serialize(kwargs)} | error={e!r}")
            raise

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.info(f"[TOOL][{tool_name}] START")
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)

            logger.info(f"[TOOL][{tool_name}] END | elapsed={elapsed_ms}ms")
            return result

        except Exception as e:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.error(f"[TOOL][{tool_name}] FAILED | args={serialize(args)} | kwargs={serialize(kwargs)} | elapsed={elapsed_ms}ms | error={e!r}")
            raise

    return async_wrapper if is_async else sync_wrapper  # type: ignore[return-value]


# ============================================
# Connector Logging Decorator
# ============================================

# Sensitive parameter names to mask in logs
_SENSITIVE_KEYS = frozenset({"key", "password", "token", "secret", "api_key", "apikey"})


def _mask_sensitive(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Mask sensitive values in kwargs for safe logging."""
    return {
        k: "***" if k.lower() in _SENSITIVE_KEYS else v for k, v in kwargs.items()
    }


def log_connector(
    connector_type: str | None = None,
    *,
    name: str | None = None,
    log_input: bool = True,
    log_output: bool = True,
    log_retry: bool = True,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Log connector execution with optional input/output control.

    Args:
        connector_type: Type identifier (LLM, HTTP, MCP, VDB, WEB).
        name: 로그 태그로 쓸 이름. 미지정 시 함수명을 쓴다. 같은 인터페이스를 구현해
            메서드명이 겹치는 구현체(예: web search provider)를 로그에서 구분할 때 지정한다.
        log_input: Whether to log input at DEBUG level.
        log_output: Whether to log output at DEBUG level.
        log_retry: Whether to log retry attempts at WARNING level.

    Logging levels:
        - INFO: Connector call start/end with elapsed time
        - DEBUG: Request/response details (if enabled)
        - WARNING: Retries (if enabled)
        - ERROR: Failures with exception details

    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        is_async = inspect.iscoroutinefunction(func)
        conn_name = name or func.__name__
        type_tag = f"[{connector_type}]" if connector_type else ""

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger.info(f"[CONNECTOR]{type_tag}[{conn_name}] START")

            safe_kwargs = _mask_sensitive(dict(kwargs))
            if log_input:
                logger.debug(f"[CONNECTOR]{type_tag}[{conn_name}] REQUEST | kwargs={serialize(safe_kwargs)}")

            start_time = time.perf_counter()

            try:
                result = await func(*args, **kwargs)
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                if log_output:
                    logger.debug(
                        f"[CONNECTOR]{type_tag}[{conn_name}] RESPONSE | result={serialize(result, max_length=1000)}",
                    )

                logger.info(f"[CONNECTOR]{type_tag}[{conn_name}] END | elapsed={elapsed_ms}ms")
                return result

            except Exception as e:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                logger.error(
                    f"[CONNECTOR]{type_tag}[{conn_name}] FAILED | elapsed={elapsed_ms}ms"
                    f" | kwargs={serialize(safe_kwargs)} | error={e!r}",
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger.info(f"[CONNECTOR]{type_tag}[{conn_name}] START")

            safe_kwargs = _mask_sensitive(dict(kwargs))
            if log_input:
                logger.debug(f"[CONNECTOR]{type_tag}[{conn_name}] REQUEST | kwargs={serialize(safe_kwargs)}")

            start_time = time.perf_counter()

            try:
                result = func(*args, **kwargs)
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                if log_output:
                    logger.debug(
                        f"[CONNECTOR]{type_tag}[{conn_name}] RESPONSE | result={serialize(result, max_length=1000)}",
                    )

                logger.info(f"[CONNECTOR]{type_tag}[{conn_name}] END | elapsed={elapsed_ms}ms")
                return result

            except Exception as e:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                logger.error(
                    f"[CONNECTOR]{type_tag}[{conn_name}] FAILED | elapsed={elapsed_ms}ms"
                    f" | kwargs={serialize(safe_kwargs)} | error={e!r}",
                )
                raise

        # Store log_retry flag for external retry handlers to check
        wrapper = async_wrapper if is_async else sync_wrapper
        wrapper._log_retry = log_retry  # type: ignore[attr-defined]
        return wrapper  # type: ignore[return-value]

    return decorator


# ============================================
# Time Log Decorator
# ============================================


def time_log(func: Callable[P, T]) -> Callable[P, T]:
    """Log function execution time.

    Logging levels:
        - INFO: Function name and elapsed time

    Works with both sync and async functions.

    Usage:
        @time_log
        async def _read_metadata(...):
            ...
    """
    is_async = inspect.iscoroutinefunction(func)
    func_name = func.__name__

    @functools.wraps(func)
    async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time = time.perf_counter()
        try:
            return await func(*args, **kwargs)
        finally:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(f"[TIME][{func_name}] elapsed={elapsed_ms}ms")

    @functools.wraps(func)
    def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start_time = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            logger.info(f"[TIME][{func_name}] elapsed={elapsed_ms}ms")

    return async_wrapper if is_async else sync_wrapper  # type: ignore[return-value]


__all__ = [
    "compute_state_diff",
    "log_connector",
    "log_node",
    "log_tool",
    "logger",
    "serialize",
    "time_log",
]
