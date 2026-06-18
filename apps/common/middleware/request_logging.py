from __future__ import annotations

import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.common.logging.decorators import serialize
from apps.common.logging.logger_config import logger

_MAX_BODY_LOG_LEN = 2000


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """들어오는 HTTP 요청과 나가는 응답을 INFO 레벨로 기록한다."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        start = time.perf_counter()

        body_bytes = await request.body()
        body_str = serialize(
            body_bytes.decode("utf-8", errors="replace"),
            max_length=_MAX_BODY_LOG_LEN,
        )
        logger.info(
            f"[REQUEST] {request.method} {request.url.path}"
            f" | client={request.client.host if request.client else '-'}"
            f" | body={body_str}"
        )

        response = await call_next(request)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            f"[RESPONSE] {response.status_code} {request.method} {request.url.path}"
            f" | elapsed={elapsed_ms}ms"
        )
        return response
