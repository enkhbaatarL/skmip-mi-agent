# mcp_client_manager.py
from __future__ import annotations

import asyncio
from typing import AsyncContextManager

from mcp import ClientSession
from mcp.client.sse import sse_client

from apps.common.logging.logger_config import logger


class MCPClientManager:
    """MCP SSE 스트림 + ClientSession 한 쌍을 관리하는 매니저.

    - 세션 라이프사이클(열기/닫기/재연결)은 _lifecycle_lock으로 보호.
    - 외부에서는 직접 _ensure_started/close/reconnect를 호출하지 말고,
      MCPClientPool.call()을 통해서만 사용하도록 가정.
    """

    _lock: asyncio.Lock = asyncio.Lock()
    _instance: MCPClientManager | None = None  # 싱글톤(기본) 용도

    def __init__(self, url: str, client_timeout: float, client_sse_read_timeout: float) -> None:
        self.url = url
        self.client_timeout = client_timeout
        self.client_sse_read_timeout = client_sse_read_timeout
        self._streams_cm: AsyncContextManager[tuple[object, object]] | None = None
        self._session_cm: AsyncContextManager[ClientSession] | None = None
        self.streams: tuple[object, object] | None = None
        self.session: ClientSession | None = None
        self._started = False
        self._closed = False
        self._lifecycle_lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    async def get(
        cls,
        url: str,
        *,
        force_new: bool = False,
        client_timeout: float,
        client_sse_read_timeout: float,
    ) -> MCPClientManager:
        """기본은 싱글톤 반환.
        풀에서 다수 생성하려면 force_new=True로 독립 인스턴스를 만든다.

        ※ 여기서는 세션을 열지 않는다. 실제 세션 시작은 MCPClientPool.call() 내부에서
        필요 시 _ensure_started()를 통해 lazy-start 한다.
        """
        if force_new:
            # 독립 인스턴스 생성(세션은 아직 열지 않음)
            return MCPClientManager(url, client_timeout, client_sse_read_timeout)

        async with cls._lock:
            if cls._instance is None:
                cls._instance = MCPClientManager(url, client_timeout, client_sse_read_timeout)
            return cls._instance

    async def _ensure_started_impl(self) -> None:
        """실제 세션 시작 로직(락 없음). 반드시 _lifecycle_lock 안에서만 호출."""

        if self._started and not self._closed and self.session is not None:
            return

        self._streams_cm = sse_client(
            url=self.url,
            timeout=self.client_timeout,
            sse_read_timeout=self.client_sse_read_timeout,
        )
        self.streams = await self._streams_cm.__aenter__()
        self._session_cm = ClientSession(*self.streams)
        self.session = await self._session_cm.__aenter__()
        await self.session.initialize()
        self._started = True
        self._closed = False

    async def _close_impl(self) -> Exception | None:
        """실제 세션 정리 로직(락 없음). 반드시 _lifecycle_lock 안에서만 호출.
        하나라도 실패하면 예외를 반환하고, 호출자가 raise 여부를 결정.
        """
        logger.info(
            "[MCPClientManager._close_impl] id={} closed={} started={} task={}",
            id(self),
            self._closed,
            self._started,
            asyncio.current_task().get_name() if asyncio.current_task() else None,
        )

        if self._closed:
            return None

        close_error: Exception | None = None

        # 1) session_cm 정리
        if self._session_cm is not None:
            try:
                await self._session_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(
                    "[MCPClientManager._close_impl] session_cm.__aexit__ error: {}",
                    e,
                )
                if close_error is None:
                    close_error = e

        self.session = None
        self._session_cm = None

        # 2) streams_cm 정리
        if self._streams_cm is not None:
            try:
                await self._streams_cm.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(
                    "[MCPClientManager._close_impl] streams_cm.__aexit__ error: {}",
                    e,
                )
                if close_error is None:
                    close_error = e

        self.streams = None
        self._streams_cm = None

        # 3) 상태 플래그 정리
        self._closed = True
        self._started = False

        return close_error

    async def _ensure_started(self) -> None:
        """외부에서 사용할 수 있는 ensure_started 래퍼.
        라이프사이클 락 안에서 실제 구현을 호출한다.
        """
        async with self._lifecycle_lock:
            await self._ensure_started_impl()

    async def check_alive(self, timeout: float = 3.0) -> bool:
        if not self.session:
            return False
        try:
            # 가벼운 호출. 라이브러리마다 다르면 다른 lightweight RPC 사용
            await asyncio.wait_for(self.session.list_prompts(), timeout=timeout)
            return True
        except Exception:
            return False

    async def reconnect(self) -> None:
        """세션 재연결.
        - close_impl + ensure_started_impl 을 동일 락 영역에서 실행.
        """
        async with self._lifecycle_lock:
            close_error = await self._close_impl()
            if close_error is not None:
                # 여기서 바로 raise 할지, 로그만 남길지 정책에 따라 조정 가능
                logger.warning(
                    "[MCPClientManager.reconnect] close_impl error on id={}: {}",
                    id(self),
                    close_error,
                )
            await self._ensure_started_impl()

    async def close(self) -> None:
        """명시적 종료. _lifecycle_lock 안에서 close_impl 실행."""
        async with self._lifecycle_lock:
            close_error = await self._close_impl()
            if close_error is not None:
                raise close_error
