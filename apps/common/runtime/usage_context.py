#   apps/common/runtime/usage_context.py

"""요청별로 격리된 LLM 토큰 사용량 관리를 위한 contextvars 기반 모듈."""

from __future__ import annotations

from contextvars import ContextVar

from apps.common.values.llm_usage import LLMUsageModel


# 요청별 격리된 usage 컨텍스트
_usage_context: ContextVar[LLMUsageModel | None] = ContextVar("usage_context", default=None)


def reset_usage() -> None:
    """새 요청 시작 시 usage 초기화."""
    _usage_context.set(LLMUsageModel())


def accumulate_usage(usage: LLMUsageModel | None) -> None:
    """LLM 호출 시 토큰 사용량 누적."""
    if usage is None:
        return

    current = _usage_context.get()
    if current is None:
        current = LLMUsageModel()
        _usage_context.set(current)

    current.prompt_tokens += usage.prompt_tokens
    current.completion_tokens += usage.completion_tokens
    current.total_tokens += usage.total_tokens


def get_accumulated_usage() -> LLMUsageModel:
    """현재 요청의 누적 토큰 사용량 반환."""
    current = _usage_context.get()
    return current if current else LLMUsageModel()