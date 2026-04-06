from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from functools import wraps
import time
from typing import Any, TypeAlias

from apps.agents.mi_agent.components.context import get_search_policies
from apps.agents.mi_agent.components.policies import ExecutionPolicy
from apps.common.values.enums import SearchSource


PolicyCallable: TypeAlias = Callable[..., Awaitable[Any]]


async def _run_with_policy(
    fn: PolicyCallable,
    state: Any,
    resource: SearchSource,
    step: str,
    policy_getter: Callable[[], ExecutionPolicy] | None,
    *args: Any,
    **kwargs: Any,
) -> Any:
    bundle = get_search_policies()
    policy = policy_getter() if policy_getter is not None else bundle.get(resource.value)

    attempt: int = 0
    last_exc: Exception | None = None
    start_total = time.perf_counter()

    while attempt <= policy.retry.retries:
        start = time.perf_counter()
        try:
            res = await _bounded_call(
                fn(state, *args, **kwargs),
                policy,
            )
        except asyncio.CancelledError:
            # 취소 케이스 Metrics
            raise
        except Exception as exc:
            last_exc = exc
            if not isinstance(exc, policy.retry.retry_on):
                # 재시도 대상이 아니면 루프 종료
                break

            await asyncio.sleep(0.5)
            attempt += 1
        else:
            # 성공 케이스 Metrics (TRY300 대응: 성공 경로는 else에서 처리)
            return res

    if last_exc is None:
        # 이론상 도달하지 않아야 하지만 타입/안정성 방어용
        raise RuntimeError("with_policy: execution failed without captured exception")

    raise last_exc


def with_policy(
    resource: SearchSource,
    step: str,
    policy_getter: Callable[[], ExecutionPolicy] | None = None,
) -> Callable[[PolicyCallable], PolicyCallable]:
    def deco(fn: PolicyCallable) -> PolicyCallable:
        @wraps(fn)
        async def _wrap(state: Any, *args: Any, **kwargs: Any) -> Any:
            return await _run_with_policy(
                fn,
                state,
                resource,
                step,
                policy_getter,
                *args,
                **kwargs,
            )

        return _wrap

    return deco


async def _bounded_call(
    call: Awaitable[Any],
    policy: ExecutionPolicy,
) -> Any:
    return await asyncio.wait_for(call, timeout=policy.exec_timeout_sec)
