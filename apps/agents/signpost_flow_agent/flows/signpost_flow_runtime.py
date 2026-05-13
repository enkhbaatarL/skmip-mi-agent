"""
Signpost Flow Runtime 초기화 모듈

역할:
- signpost_flow_agent 실행에 필요한 runtime 리소스를 사전에 준비한다.
- MCP pool, HTTP client, semaphore, API KEY 환경변수 등 공용 리소스 초기화를 담당한다.

설계 의도:
- 각 node/service에서 runtime 초기화 여부를 신경쓰지 않도록
  runnable 진입 시점에서 한 번만 초기화
- 공용 리소스를 중앙에서 관리하여 중복 생성 및 비용 방지
"""
from __future__ import annotations

from typing import TypeVar

from apps.common.runtime.runtime import ensure_runtime_context_ready
from apps.common.runtime.usage_context import reset_usage

T = TypeVar("T")


async def ensure_runtime(x: T, **_: object) -> T:
    await ensure_runtime_context_ready()
    reset_usage()
    return x