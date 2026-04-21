#   apps/connectors/mcp/mcp_client_pool.py

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from anyio import ClosedResourceError
import httpx
from loguru import logger

from apps.connectors.mcp.mcp_client_manager import MCPClientManager


Fn = Callable[[object], Awaitable[object]]


def _flatten_exceptions(ex: BaseException) -> list[BaseException]:
    # Python 3.11+: ExceptionGroup / BaseExceptionGroup
    if isinstance(ex, BaseExceptionGroup):  # type: ignore[name-defined]
        out: list[BaseException] = []
        for sub in ex.exceptions:  # type: ignore[attr-defined]
            out.extend(_flatten_exceptions(sub))
        return out
    return [ex]


def _is_retriable_mcp_exception(ex: BaseException) -> bool:
    """MCP 연결/세션 계열의 '재시도 가능한' 오류를 분류한다.
    - anyio.ClosedResourceError: 스트림/리소스 닫힘
    - httpx Connect/Read/ConnectError: 연결 실패/타임아웃
    - ExceptionGroup 내부에 위 예외가 포함된 경우도 True.
    """
    for e in _flatten_exceptions(ex):
        if isinstance(
            e,
            (
                ClosedResourceError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.ReadError,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
            ),
        ):
            return True
    return False


class MCPClientPool:
    def __init__(
        self,
        url: str,
        size: int = 3,
        per_session_limit: int = 1,
        client_timeout: float = 5.0,
        client_sse_read_timeout=250.0,
        *,
        warmup_size: int = 8,
        warmup_concurrency: int = 2,
    ) -> None:
        self.url = url
        self.size = size
        self.per_session_limit = per_session_limit
        self.client_timeout = client_timeout
        self.client_sse_read_timeout = client_sse_read_timeout
        self.managers: list[MCPClientManager] = []
        self.semaphores: list[asyncio.Semaphore] = []
        self.dead: set[int] = set()
        self.rr: int = 0

        # 전체 동시 MCP 호출 제한(세션 수 * 세션별 동시 호출)
        self.global_sem = asyncio.Semaphore(size * per_session_limit)
        self.reconnect_sem = asyncio.Semaphore(1)

        # start 시, 세션을 몇 개까지 미리 연결해 둘지 (너무 많이 열면 서버/OS에 부담)
        self.warmup_size = max(0, warmup_size)
        self.warmup_concurrency = max(1, warmup_concurrency)

        self._started = False
        self._start_lock = asyncio.Lock()

    async def start(self) -> None:
        """풀 구조를 준비하고, warmup_size 만큼만 제한된 동시성으로 세션을 미리 연결한다.
        (lazy-start 폭주를 줄이기 위한 목적).
        """
        if self._started:
            return

        async with self._start_lock:
            if self._started:
                return

            for _ in range(self.size):
                mgr = await MCPClientManager.get(
                    self.url,
                    force_new=True,
                    client_timeout=self.client_timeout,
                    client_sse_read_timeout=self.client_sse_read_timeout,
                )
                self.managers.append(mgr)
                self.semaphores.append(asyncio.Semaphore(self.per_session_limit))

            self._started = True

            if self.warmup_size > 0:
                await self._warmup_sessions()

    async def _warmup_sessions(self) -> None:
        """warmup_size(기본 8)까지만 미리 SSE 세션을 올려 둔다.
        - 동시에 너무 많이 connect 하지 않도록 warmup_concurrency로 제한.
        """
        target = min(self.warmup_size, len(self.managers))
        if target <= 0:
            return

        sem = asyncio.Semaphore(self.warmup_concurrency)

        async def _one(idx: int) -> None:
            async with sem:
                mgr = self.managers[idx]
                try:
                    if mgr.session is None:
                        await mgr._ensure_started()
                except Exception as ex:
                    self.dead.add(idx)
                    logger.warning(
                        "[MCPClientPool._warmup_sessions] warmup failed idx={} ex={!r}",
                        idx,
                        ex,
                    )

        await asyncio.gather(*(_one(i) for i in range(target)))

        # warmup이 전부 실패하면, 이후 call()도 계속 fail 확률이 높으니 조기 감지
        alive_started = sum(1 for i in range(target) if i not in self.dead and self.managers[i].session is not None)
        if alive_started == 0:
            msg = "MCP warmup failed: no sessions could be established"
            raise RuntimeError(msg)

    async def close(self) -> None:
        if not self._started:
            return
        await asyncio.gather(
            *(mgr.close() for mgr in self.managers),
            return_exceptions=True,
        )
        self.managers.clear()
        self.semaphores.clear()
        self.dead.clear()
        self._started = False

    async def _pick_fast(self) -> tuple[int, MCPClientManager]:
        """1) dead가 아니고 session이 이미 떠 있는 manager를 우선 선택
        2) 없으면 dead가 아닌 manager를 선택(필요 시 lazy-start)
        3) 전부 dead면 revive 후 사용.
        """
        n = len(self.managers)
        if n == 0:
            msg = "MCPClientPool has no managers. Did you call start()?"
            raise RuntimeError(msg)

        # 1) already-started 우선
        for _ in range(n):
            i = self.rr % n
            self.rr += 1
            if i in self.dead:
                continue
            if self.managers[i].session is None:
                continue
            return i, self.managers[i]

        # 2) not-dead 아무거나
        for _ in range(n):
            i = self.rr % n
            self.rr += 1
            if i in self.dead:
                continue
            return i, self.managers[i]

        # 3) 전부 dead → 0번 revive 시도
        i = 0
        await self._revive_manager(i)
        self.dead.clear()
        return i, self.managers[i]

    async def _revive_manager(self, idx: int) -> None:
        async with self.reconnect_sem:
            try:
                await self.managers[idx].reconnect()
                self.dead.discard(idx)
            except Exception as ex:
                self.dead.add(idx)
                logger.warning("[MCPClientPool._revive_manager] error idx={} ex={!r}", idx, ex)

    async def call(self, fn: Fn):
        """MCP 세션 풀을 통해 fn(session)을 실행.
        - global_sem으로 전체 동시 호출 수 제한
        - 각 manager별 sem으로 per_session_limit 제한
        - 재시도 가능한 오류(ClosedResourceError, ConnectTimeout 등)는 dead 처리 후 revive.
        """
        if not self._started:
            msg = "MCPClientPool not started. Call start() at app boot."
            raise RuntimeError(msg)

        async with self.global_sem:
            last_exc: Exception | None = None

            for attempt in range(len(self.managers) + 1):
                i, mgr = await self._pick_fast()
                sem = self.semaphores[i]

                async with sem:
                    try:
                        # 세션이 아직 준비되지 않았다면 여기서 시작
                        if mgr.session is None:
                            await mgr._ensure_started()

                        return await fn(mgr.session)

                    except Exception as ex:
                        if _is_retriable_mcp_exception(ex):
                            logger.warning(
                                "[MCPClientPool.call] retriable error mgr={} attempt={} ex={!r}",
                                i,
                                attempt,
                                ex,
                            )
                            self.dead.add(i)
                            last_exc = ex
                            await self._revive_manager(i)
                            continue

                        logger.error(
                            "[MCPClientPool.call] non-retriable error mgr={} ex={!r}",
                            i,
                            ex,
                        )
                        raise

            if last_exc is not None:
                raise last_exc
            msg = "All MCP sessions failed"
            raise RuntimeError(msg)
