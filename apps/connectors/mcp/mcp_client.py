"""MI MCP 서버(streamable HTTP) 커넥터.

`mi-next-gen-mcp-server` 는 MI Platform 의 next-gen REST API 를 MCP tool 로 감싼 서버다.
tool 응답은 JSON 문자열 1건을 text content 에 담아 오므로, 이 층에서 dict 로 풀어
호출자가 MCP 프로토콜 타입을 몰라도 되게 한다.

서버는 세션 상태를 유지하지 않지만(Mcp-Session-Id 미발급) 연결·initialize 왕복 비용은
호출마다 발생한다. 그래서 세션 열기(`mi_mcp_session`)와 tool 호출(`call_mcp_tool`)을
분리해, 한 노드에서 tool 을 여러 번 부를 때 연결 하나를 재사용하게 한다.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import CallToolResult, TextContent

from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.decorators import log_connector
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode


def _first_text(result: CallToolResult) -> str:
    """Tool 응답에서 첫 text content 를 꺼낸다(이 서버는 항상 text 1건을 준다)."""
    for block in result.content:
        if isinstance(block, TextContent):
            return block.text
    return ""


@asynccontextmanager
async def mi_mcp_session(
    *,
    base_url: str | None = None,
    timeout_sec: float | None = None,
) -> AsyncIterator[ClientSession]:
    """MI MCP 서버에 연결해 initialize 까지 끝난 세션을 넘긴다.

    Args:
        base_url: MCP 엔드포인트. 미지정 시 `Settings.mi_mcp_base_url`.
        timeout_sec: 연결/응답 타임아웃. 미지정 시 `Settings.mi_mcp_timeout_sec`.

    """
    cfg = get_settings()
    url = (base_url or cfg.mi_mcp_base_url).strip()
    if not url:
        raise MIBaseError(
            ErrorCode.INVALID_REQUEST,
            detail="mi_mcp_base_url 설정이 비어 있어 MI MCP 서버를 호출할 수 없습니다.",
        )
    timeout = timeout_sec if timeout_sec is not None else cfg.mi_mcp_timeout_sec

    logger.info(f"[CONNECTOR][MCP][mi_mcp_session] CONNECT | url={url} | timeout={timeout}s")
    connected = False
    try:
        async with (
            streamablehttp_client(url, timeout=timeout, sse_read_timeout=timeout) as (read, write, _),
            ClientSession(read, write) as session,
        ):
            await session.initialize()
            connected = True
            yield session
    except Exception as exc:
        # 세션 본문(tool 호출)에서 난 오류는 그대로 올린다. 연결 단계 실패만 래핑한다.
        if connected:
            raise
        logger.error(f"[CONNECTOR][MCP][mi_mcp_session] CONNECT_FAILED | url={url} | error={exc!r}")
        raise MIBaseError(
            ErrorCode.HTTP_CONNECTION_ERROR,
            detail=f"MI MCP 서버({url}) 연결에 실패했습니다.",
        ) from exc
    finally:
        if connected:
            logger.info(f"[CONNECTOR][MCP][mi_mcp_session] CLOSE | url={url}")


@log_connector(connector_type="MCP", log_output=False)
async def call_mcp_tool(
    session: ClientSession,
    tool_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """MCP tool 1건을 호출하고 응답 JSON 을 dict 로 돌려준다.

    응답 페이로드(이벤트 상세 등)가 매우 크므로 DEBUG 본문 로그는 끈다.
    """
    result = await session.call_tool(tool_name, arguments)
    payload_text = _first_text(result)

    if result.isError:
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=f"MCP tool '{tool_name}' 호출이 실패했습니다: {payload_text[:500]}",
        )
    if not payload_text:
        logger.warning(f"[CONNECTOR][MCP][call_mcp_tool] EMPTY_CONTENT | tool={tool_name}")
        return {}

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise MIBaseError(
            ErrorCode.DATA_RETRIEVAL_FAILED,
            detail=f"MCP tool '{tool_name}' 응답을 JSON 으로 읽지 못했습니다.",
        ) from exc

    if not isinstance(payload, dict):
        # 이 서버의 tool 은 모두 object 를 주지만, 스키마가 바뀌어도 호출자가 깨지지 않게 감싼다.
        logger.warning(f"[CONNECTOR][MCP][call_mcp_tool] NON_OBJECT_PAYLOAD | tool={tool_name}")
        return {"result": payload}
    return payload
