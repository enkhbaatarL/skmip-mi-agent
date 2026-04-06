"""Base interface for web search providers."""

from abc import ABC, abstractmethod
from typing import Any


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
        **kwargs: Any,
    ) -> dict[str, Any]:
        """
        Search the web for content.

        Args:
            query: Search query string
            start_date: Start date for filtering results (YYYY-MM-DD)
            end_date: End date for filtering results (YYYY-MM-DD)
            **kwargs: Additional provider-specific parameters

        Returns:
            Dictionary containing search results and metadata
        """
        pass
