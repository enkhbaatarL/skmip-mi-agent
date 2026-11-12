from __future__ import annotations

import json
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from apps.common.logging.console import full_console_logs, full_payloads_enabled
from apps.common.logging.logger_config import logger


_MAX_BODY_LOG_LEN = 2000


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """들어오는 HTTP 요청/응답을 로깅한다.

    - INFO: 메서드, 경로, 클라이언트, 응답 시간
    - DEBUG: 요청 바디(pretty JSON, multiline)
    """

    def __init__(self, app: ASGIApp, *, full_payloads: bool = False) -> None:
        super().__init__(app)
        self.full_payloads = full_payloads

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        with full_console_logs(enabled=self.full_payloads):
            start = time.perf_counter()

            body_bytes = await request.body()
            logger.info(
                f"[REQUEST] {request.method} {request.url.path}"
                f" | client={request.client.host if request.client else '-'}"
            )
            body_str = body_bytes.decode("utf-8", errors="replace")
            logger.debug(f"[REQUEST] BODY\n{_format_body_for_debug(body_str)}")

            response = await call_next(request)

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                f"[RESPONSE] {response.status_code} {request.method} {request.url.path} | elapsed={elapsed_ms}ms"
            )
            return response


def _format_body_for_debug(body_str: str) -> str:
    if not body_str.strip():
        return "null"
    try:
        parsed = json.loads(body_str)
        pretty = json.dumps(parsed, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pretty = json.dumps({"raw": body_str}, ensure_ascii=False, indent=2, default=str)
    if not full_payloads_enabled() and len(pretty) > _MAX_BODY_LOG_LEN:
        return pretty[:_MAX_BODY_LOG_LEN] + f"... [truncated, total {len(pretty)} chars]"
    return pretty
