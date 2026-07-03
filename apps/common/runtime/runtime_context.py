#   apps/common/runtime/runtime_context.py

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import inspect

import httpx

from apps.common.configs.config import Settings, get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.common.logging.logger_config import logger
from apps.common.values.enums import SemaphoreName
from apps.connectors.http.http_client_manager import HttpClientManager


_ShutdownCallback = Callable[[], None] | Callable[[], Awaitable[None]]


class RuntimeContext:
    """프로세스 전역 리소스(HTTP 클라이언트, 세마포어 등)를 관리하는 컨테이너.

    - 실제 리소스의 생명주기/초기화/셧다운은 이 클래스가 담당
    - 싱글톤 여부는 모듈 전역의 `_runtime_context`로 관리
    """

    def __init__(self) -> None:
        self.cfg: Settings = get_settings()

        # HTTP
        self.http_lock = asyncio.Lock()
        self.http_manager = HttpClientManager(self.cfg)

        # 세마포어
        self.semaphores: dict[SemaphoreName, asyncio.Semaphore] = {}

        # 초기화 상태
        self._initialized: bool = False
        self._init_lock = asyncio.Lock()

        # 셧다운 콜백
        self._shutdown_callbacks: list[_ShutdownCallback] = []

    @property
    def is_ready(self) -> bool:
        return self._initialized

    def register_shutdown_callback(self, cb: _ShutdownCallback) -> None:
        self._shutdown_callbacks.append(cb)

    async def ensure_ready(self) -> RuntimeContext:
        if self._initialized:
            return self

        async with self._init_lock:
            if self._initialized:
                return self

            self._init_global_semaphores()

            self._initialized = True

            return self

    async def close_all(self) -> None:
        await self._close_http_clients()
        await self._run_shutdown_callbacks()

    def _init_global_semaphores(self) -> None:
        self.semaphores[SemaphoreName.HTTP] = asyncio.Semaphore(
            self.cfg.http_max_concurrency,
        )
        self.semaphores[SemaphoreName.LLM] = asyncio.Semaphore(self.cfg.llm_concurrency)

    async def _close_http_clients(self) -> None:
        async with self.http_lock:
            return await self.http_manager.close_http_clients()

    async def _run_shutdown_callbacks(self) -> None:
        for cb in list(self._shutdown_callbacks):
            try:
                if inspect.iscoroutinefunction(cb):
                    await cb()
                else:
                    result = cb()
                    if inspect.isawaitable(result):
                        await result
            except Exception as ex:
                logger.warning(
                    "[shutdown] Shutdown callback failed (cb={!r}, type={}, msg={}): {!r}",
                    cb,
                    type(ex).__name__,
                    str(ex),
                    ex,
                )

    async def get_http_client(
        self,
        *,
        base_url: str = "",
        verify: bool | None = None,
        http2: bool | None = None,
    ) -> httpx.AsyncClient:
        if not self._initialized:
            raise MIBaseError(ErrorCode.RUNTIME_REGISTRY_NOT_READY)

        return await self.http_manager.get_http_client(
            base_url=base_url,
            verify=verify,
            http2=http2,
        )

    def get_semaphore(self, name: SemaphoreName) -> asyncio.Semaphore:
        if not self._initialized:
            raise MIBaseError(ErrorCode.RUNTIME_REGISTRY_NOT_READY)

        sem = self.semaphores.get(name)
        if sem is None:
            raise MIBaseError(ErrorCode.SEMAPHORE_MANAGEMENT_ERROR, detail=f"Semaphore '{name}' not initialized")
        return sem

    def get_http_semaphore(self) -> asyncio.Semaphore:
        return self.get_semaphore(SemaphoreName.HTTP)

    def get_llm_semaphore(self) -> asyncio.Semaphore:
        return self.get_semaphore(SemaphoreName.LLM)
