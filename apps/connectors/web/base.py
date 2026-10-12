"""Base interface for web search providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from apps.common.tracing.context import TraceContext


class WebSearchProvider(ABC):
    """Abstract base class for web search providers."""

    @property
    @abstractmethod
    def score_threshold(self) -> float:
        """Get the score threshold for filtering search results.

        Returns:
            Minimum score value for including results

        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        *,
        trace_context: TraceContext | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Search the web for content.

        ``trace_context`` 는 커넥터 공통 인자라 provider 마다 처리 방식이 다르다.
        ``**kwargs`` 에 섞여 들어가면 provider 요청 바디로 새어 나가므로
        (Pydantic 객체는 JSON 직렬화가 안 된다) 반드시 명시적 인자로 받는다.
        지원하지 않는 provider 는 받아서 버리면 된다.

        Args:
            query: Search query string
            start_date: Start date for filtering results (YYYY-MM-DD)
            end_date: End date for filtering results (YYYY-MM-DD)
            trace_context: 요청 단위 trace context. provider 가 지원하면 추적 헤더로 쓴다.
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing search results and metadata

        """
