from __future__ import annotations

import asyncio

import httpx

from apps.common.configs.settings import Settings
from apps.common.logging.logger_config import logger


class HttpClientManager:
    def __init__(self, cfg: Settings) -> None:
        self._cfg: Settings = cfg
        self._clients: dict[tuple[str, bool, bool], httpx.AsyncClient] = {}
        self._lock: asyncio.Lock = asyncio.Lock()

    async def get_http_client(
        self,
        *,
        base_url: str = "",
        verify: bool | None = None,
        http2: bool | None = None,
    ) -> httpx.AsyncClient:
        cfg = self._cfg

        ssl_verify: bool = cfg.http_verify if verify is None else verify
        http2_enabled: bool = cfg.http2 if http2 is None else http2
        key: tuple[str, bool, bool] = (base_url, bool(ssl_verify), bool(http2_enabled))

        client = self._clients.get(key)
        if client is not None:
            return client

        async with self._lock:
            client = self._clients.get(key)
            if client is not None:
                return client

            client = httpx.AsyncClient(
                base_url=base_url or None,
                timeout=httpx.Timeout(
                    timeout=cfg.http_timeout,
                    connect=cfg.http_connect_timeout,
                ),
                verify=bool(ssl_verify),
                http2=bool(http2_enabled),
                limits=httpx.Limits(
                    max_connections=cfg.http_max_connection,
                    max_keepalive_connections=cfg.http_max_keepalive,
                ),
            )
            self._clients[key] = client
            return client

    async def close_http_clients(self) -> None:
        async with self._lock:
            clients = list(self._clients.values())
            self._clients.clear()

        for client in clients:
            try:
                await client.aclose()
            except Exception as ex:
                logger.warning(
                    "[http] HTTP client close failed (type={}, msg={}): {!r}",
                    type(ex).__name__,
                    str(ex),
                    ex,
                )
