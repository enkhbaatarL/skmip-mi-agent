import asyncio
from http import HTTPStatus
from typing import Any

import httpx

from apps.common.configs.settings import Settings, get_settings
from apps.common.exceptions.custom import HttpConnectionError
from apps.common.logging.decorators import log_connector
from apps.common.runtime.runtime import get_http_client, get_http_semaphore


RETRY_STATUS_CODES: tuple[HTTPStatus, ...] = (
    HTTPStatus.TOO_MANY_REQUESTS,
    HTTPStatus.REQUEST_TIMEOUT,
    HTTPStatus.BAD_GATEWAY,
    HTTPStatus.SERVICE_UNAVAILABLE,
    HTTPStatus.GATEWAY_TIMEOUT,
)


@log_connector(connector_type="HTTP", log_input=True, log_output=False)
async def http_request(
    method: str,
    url: str,
    *,
    verify: bool | None = None,
    **kwargs: Any,
) -> httpx.Response:
    cfg: Settings = get_settings()
    client: httpx.AsyncClient = await get_http_client(
        base_url=url,
        verify=verify if verify else cfg.http_verify,
        http2=cfg.http2,
    )
    sem = get_http_semaphore()

    max_retries: int = cfg.http_request_max_retries
    retry_backoff: float = cfg.http_retry_backoff_base

    async with sem:
        for i in range(max_retries + 1):
            try:
                resp = await client.request(method, url, **kwargs)
            except httpx.RequestError:
                if i < max_retries:
                    await asyncio.sleep(retry_backoff * (2**i))
                    continue
                raise
            else:
                if resp.status_code in RETRY_STATUS_CODES and i < max_retries:
                    await asyncio.sleep(retry_backoff * (2**i))
                    continue
                resp.raise_for_status()
                return resp

    msg = "http_request reached an unexpected fallthrough path."
    raise HttpConnectionError(msg)


async def http_get(url: str, **kw: Any) -> httpx.Response:
    return await http_request("GET", url, **kw)


async def http_post(url: str, **kw: Any) -> httpx.Response:
    return await http_request("POST", url, **kw)
