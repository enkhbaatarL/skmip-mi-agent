from __future__ import annotations

from typing import TypeVar

from apps.agents.mi_agent.components.context import set_search_policies
from apps.agents.mi_agent.components.policies import build_search_policy_set
from apps.common.runtime.runtime import ensure_mcp_pool, ensure_runtime_context_ready
from apps.common.runtime.usage_context import reset_usage


T = TypeVar("T")


async def ensure_runtime[T](x: T, **_: object) -> T:
    await ensure_runtime_context_ready()
    reset_usage()
    company_code = getattr(x, "company_code", None)
    await ensure_mcp_pool(company_code)
    search_sources = getattr(x, "search_sources", None)
    if search_sources is not None:
        set_search_policies(build_search_policy_set(search_sources=search_sources))
    return x
