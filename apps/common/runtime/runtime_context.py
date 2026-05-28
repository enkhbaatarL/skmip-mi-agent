#   apps/common/runtime/runtime_context.py

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import inspect
import os

import httpx

from apps.agents.mi_agent.components.context import set_search_policies
from apps.agents.mi_agent.components.policies import SearchPolicySet, build_search_policy_set
from apps.common.configs.settings import Settings, get_settings
from apps.common.exceptions.custom import (
    RuntimeRegistryNotReadyError,
    SemaphoreManagementError,
)
from apps.common.logging.logger_config import logger
from apps.common.values.enums import SemaphoreName
from apps.connectors.http.http_client_manager import HttpClientManager
from apps.connectors.mcp.mcp_client_pool import MCPClientPool
from apps.connectors.web.base import WebSearchProvider


_ShutdownCallback = Callable[[], None] | Callable[[], Awaitable[None]]


class RuntimeContext:
    """프로세스 전역 리소스(MCP 풀, HTTP 클라이언트, 세마포어 등)를 관리하는 컨테이너.

    - 실제 리소스의 생명주기/초기화/셧다운은 이 클래스가 담당
    - 싱글톤 여부는 모듈 전역의 `_runtime_context`로 관리
    """

    def __init__(self) -> None:
        self.cfg: Settings = get_settings()

        # MCP
        self.mcp_pool: MCPClientPool | None = None
        self.mcp_lock = asyncio.Lock()
        self._mcp_pool_url: str | None = None

        # MCP default pool (항상 default URL로 고정, company_code와 무관)
        self.default_mcp_pool: MCPClientPool | None = None
        self._default_mcp_pool_url: str | None = None

        # HTTP
        self.http_lock = asyncio.Lock()
        self.http_manager = HttpClientManager(self.cfg)

        # Web Search Provider
        self.web_search_provider: WebSearchProvider | None = None
        self.web_search_lock = asyncio.Lock()

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

            # TODO: 위치 옮기는거 검토
            search_policy_set: SearchPolicySet = build_search_policy_set()
            set_search_policies(search_policy_set)

            self._initialized = True

            return self

    async def close_all(self) -> None:
        await self._close_default_mcp_pool()
        await self._close_mcp_pool()
        await self._close_http_clients()
        await self._close_web_search_provider()
        await self._run_shutdown_callbacks()

    def _init_global_semaphores(self) -> None:
        self.semaphores[SemaphoreName.HTTP] = asyncio.Semaphore(
            self.cfg.http_max_concurrency,
        )
        self.semaphores[SemaphoreName.MCP] = asyncio.Semaphore(
            self.cfg.mcp_max_concurrency,
        )
        self.semaphores[SemaphoreName.LLM] = asyncio.Semaphore(self.cfg.llm_concurrency)

        self.semaphores[SemaphoreName.RDB_EXEC] = asyncio.Semaphore(self.cfg.rdb_exec_max_parallel)

        self.semaphores[SemaphoreName.WEB] = asyncio.Semaphore(
            self.cfg.web_search_max_concurrent,
        )

    async def ensure_mcp_pool(self, company_code: str | None) -> None:
        await self._ensure_mcp_client_pool(self._resolve_mcp_pool_url(company_code))

    async def ensure_mcp_pool_by_key(self, pool_key: str) -> None:
        """pool_key(예: database_name)로 직접 MCP 풀 URL을 결정해 풀을 초기화한다."""
        await self._ensure_mcp_client_pool(self._resolve_mcp_pool_url_by_key(pool_key))

    def _resolve_mcp_pool_url(self, company_code: str | None) -> str:
        pool_urls = self.cfg.mcp_pool_urls or {}

        default_url = pool_urls.get("default", "http://localhost:9000/sse")
        if not company_code:
            return default_url
        pool_key = self.cfg.company_mcp_map.get(company_code)
        if not pool_key:
            return default_url
        return pool_urls.get(pool_key, default_url)

    def _resolve_mcp_pool_url_by_key(self, pool_key: str) -> str:
        """pool_key를 MCP_POOL_URLS에 직접 조회해 URL을 반환한다. 없으면 default 사용."""
        pool_urls = self.cfg.mcp_pool_urls or {}
        default_url = pool_urls.get("default", "http://localhost:9000/sse")
        return pool_urls.get(pool_key, default_url)

    async def _ensure_default_mcp_pool(self, url: str) -> None:
        """default_mcp_pool은 항상 default URL로만 초기화되며 이후 변경되지 않는다."""
        if self.default_mcp_pool is not None and self._default_mcp_pool_url == url:
            return
        self.default_mcp_pool = MCPClientPool(
            url,
            size=self.cfg.mcp_pool_size,
            per_session_limit=self.cfg.mcp_per_session_limit,
            client_timeout=self.cfg.mcp_client_timeout,
            client_sse_read_timeout=self.cfg.mcp_client_sse_read_timeout,
        )
        self._default_mcp_pool_url = url
        await self.default_mcp_pool.start()

    async def _ensure_mcp_client_pool(self, url: str) -> None:
        async with self.mcp_lock:
            if self.mcp_pool is not None and self._mcp_pool_url == url:
                return

            if self.mcp_pool is not None:
                await self.mcp_pool.close()

            self.mcp_pool = MCPClientPool(
                url,
                size=self.cfg.mcp_pool_size,
                per_session_limit=self.cfg.mcp_per_session_limit,
                client_timeout=self.cfg.mcp_client_timeout,
                client_sse_read_timeout=self.cfg.mcp_client_sse_read_timeout,
            )
            self._mcp_pool_url = url
            await self.mcp_pool.start()

    async def _close_default_mcp_pool(self) -> None:
        async with self.mcp_lock:
            pool = self.default_mcp_pool
            self.default_mcp_pool = None
            self._default_mcp_pool_url = None

            if pool:
                try:
                    await pool.close()
                except Exception as ex:
                    logger.warning(
                        "[shutdown] Default MCP pool close failed (type={}, msg={}): {!r}",
                        type(ex).__name__,
                        str(ex),
                        ex,
                    )

    async def _close_mcp_pool(self) -> None:
        async with self.mcp_lock:
            pool = self.mcp_pool
            self.mcp_pool = None
            self._mcp_pool_url = None

            if pool:
                try:
                    await pool.close()
                except Exception as ex:
                    logger.warning(
                        "[shutdown] MCP pool close failed (type={}, msg={}): {!r}",
                        type(ex).__name__,
                        str(ex),
                        ex,
                    )

    async def _close_http_clients(self) -> None:
        async with self.http_lock:
            return await self.http_manager.close_http_clients()

    async def _close_web_search_provider(self) -> None:
        """Close web search provider if it has cleanup logic."""
        async with self.web_search_lock:
            self.web_search_provider = None

            # Future: if provider has cleanup method, call it
            # if provider and hasattr(provider, 'close'):
            #     await provider.close()

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
            raise RuntimeRegistryNotReadyError

        return await self.http_manager.get_http_client(
            base_url=base_url,
            verify=verify,
            http2=http2,
        )

    def get_semaphore(self, name: SemaphoreName) -> asyncio.Semaphore:
        if not self._initialized:
            raise RuntimeRegistryNotReadyError

        sem = self.semaphores.get(name)
        if sem is None:
            raise SemaphoreManagementError(detail=f"Semaphore '{name}' not initialized")
        return sem

    def get_http_semaphore(self) -> asyncio.Semaphore:
        return self.get_semaphore(SemaphoreName.HTTP)

    def get_mcp_semaphore(self) -> asyncio.Semaphore:
        return self.get_semaphore(SemaphoreName.MCP)

    def get_llm_semaphore(self) -> asyncio.Semaphore:
        return self.get_semaphore(SemaphoreName.LLM)

    def get_rdb_exec_semaphore(self) -> asyncio.Semaphore:
        return self.get_semaphore(SemaphoreName.RDB_EXEC)

    def get_web_semaphore(self) -> asyncio.Semaphore:
        return self.get_semaphore(SemaphoreName.WEB)

    def get_default_mcp_pool(self) -> MCPClientPool:
        """항상 default URL에 연결된 풀을 반환한다 (company_code와 무관)."""
        if not self._initialized:
            raise RuntimeRegistryNotReadyError
        pool = self.default_mcp_pool
        if pool is None:
            raise RuntimeRegistryNotReadyError(detail="Default MCP pool not initialized")
        return pool

    def get_mcp_pool(self) -> MCPClientPool:
        if not self._initialized:
            raise RuntimeRegistryNotReadyError
        pool = self.mcp_pool
        if pool is None:
            raise RuntimeRegistryNotReadyError(detail="MCP pool not initialized")
        return pool

    async def get_web_search_provider(self) -> WebSearchProvider:
        if not self._initialized:
            raise RuntimeRegistryNotReadyError

        if self.web_search_provider:
            return self.web_search_provider

        async with self.web_search_lock:
            if self.web_search_provider:
                return self.web_search_provider

            from apps.connectors.web.factory import WebSearchProviderFactory

            self.web_search_provider = WebSearchProviderFactory.create_from_settings()
            logger.info(f"Initialized web search provider: {self.cfg.web_search_provider}")
            return self.web_search_provider
