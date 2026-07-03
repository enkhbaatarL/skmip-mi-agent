#   apps/common/runtime/runtime.py

from __future__ import annotations

import asyncio

import httpx

from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.common.runtime.runtime_context import RuntimeContext
from apps.common.runtime.shutdown_hooks import install_shutdown_hooks
from apps.common.values.enums import SemaphoreName


_runtime_context = RuntimeContext()
_shutdown_hook_installed = False
_shutdown_hook_lock = asyncio.Lock()


async def ensure_runtime_context_ready() -> RuntimeContext:
    await _runtime_context.ensure_ready()

    global _shutdown_hook_installed
    if not _shutdown_hook_installed:
        async with _shutdown_hook_lock:
            if not _shutdown_hook_installed:
                install_shutdown_hooks(_runtime_context.close_all)
                _shutdown_hook_installed = True

    return _runtime_context


def get_runtime_resources() -> RuntimeContext:
    if not _runtime_context.is_ready:
        raise MIBaseError(ErrorCode.RUNTIME_REGISTRY_NOT_READY)
    return _runtime_context


async def get_http_client(
    *,
    base_url: str = "",
    verify: bool | None = None,
    http2: bool | None = None,
) -> httpx.AsyncClient:
    if not _runtime_context.is_ready:
        await ensure_runtime_context_ready()
    return await _runtime_context.get_http_client(
        base_url=base_url,
        verify=verify,
        http2=http2,
    )


def get_semaphore(name: SemaphoreName) -> asyncio.Semaphore:
    return get_runtime_resources().get_semaphore(name)


def get_http_semaphore() -> asyncio.Semaphore:
    return get_runtime_resources().get_http_semaphore()


def get_llm_semaphore() -> asyncio.Semaphore:
    return get_runtime_resources().get_llm_semaphore()
