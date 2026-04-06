from __future__ import annotations

from collections.abc import Callable
from typing import Any

from apps.common.runtime.runtime import (
    ensure_mcp_pool,
    ensure_mcp_pool_by_key,
    ensure_runtime_context_ready,
    get_default_mcp_pool,
    get_mcp_pool,
    get_mcp_semaphore,
)


async def mcp_call(op: Callable[[Any], Any]):
    """Default MCP 풀을 통해 op를 실행한다 (company_code와 무관)."""
    await ensure_runtime_context_ready()
    pool = get_default_mcp_pool()
    mcp_sem = get_mcp_semaphore()

    async with mcp_sem:
        return await pool.call(op)


async def mcp_read_resource(uri: str):
    return await mcp_call(lambda s: s.read_resource(uri))




async def mcp_get_prompt(name: str, params: dict):
    return await mcp_call(lambda s: s.get_prompt(name, params))


async def mcp_call_tool_by_pool_key(name: str, args: dict, pool_key: str) -> object:
    """pool_key(예: database_name)로 직접 MCP 풀을 결정해 tool을 호출한다.

    MCP_POOL_URLS에 pool_key가 있으면 해당 URL의 풀을 사용하고,
    없으면 default 풀로 fallback한다.
    """
    await ensure_runtime_context_ready()
    await ensure_mcp_pool_by_key(pool_key)
    pool = get_mcp_pool()
    mcp_sem = get_mcp_semaphore()

    async with mcp_sem:
        return await pool.call(lambda s: s.call_tool(name, args))


async def mcp_call_tool(name: str, args: dict, company_code: str | None = None):
    """Company_code 기반으로 MCP 풀을 결정해 tool을 호출한다.

    company_code → company_mcp_map → mcp_pool_urls 순으로 URL을 결정한다.
    company_code가 없거나 매핑이 없으면 default 풀을 사용한다.
    """
    await ensure_runtime_context_ready()
    await ensure_mcp_pool(company_code)
    pool = get_mcp_pool()
    mcp_sem = get_mcp_semaphore()

    async with mcp_sem:
        return await pool.call(lambda s: s.call_tool(name, args))
