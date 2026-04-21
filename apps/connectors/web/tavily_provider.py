#   apps/connectors/web/tavily_provider.py

"""Tavily web search provider with async support."""

import asyncio
import functools
from typing import Any

import requests
from tavily import TavilyClient
import urllib3

from apps.common.logging.decorators import log_connector
from apps.common.logging.logger_config import logger
from apps.connectors.web.base import WebSearchProvider


# ============================================
# SSL 검증 비활성화 (Fortinet SSL Inspection 환경 대응)
# Tavily API 호출에만 verify=False 적용
# ============================================
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_original_request = requests.Session.request


def _patched_request(self, method, url, **kwargs):
    if "tavily.com" in str(url):
        kwargs["verify"] = False
    return _original_request(self, method, url, **kwargs)


requests.Session.request = _patched_request
# ============================================


class TavilySearchProvider(WebSearchProvider):
    def __init__(
        self,
        api_key: str,
        search_depth: str = "advanced",
        max_results: int = 5,
        include_domains: list[str] | None = None,
        exclude_domains: list[str] | None = None,
        score_threshold: float = 0.5,
    ) -> None:
        self.client = TavilyClient(api_key=api_key)
        self.search_depth = search_depth
        self.max_results = max_results
        self.include_domains = include_domains or []
        self.exclude_domains = exclude_domains or []
        self._score_threshold = score_threshold

    @property
    def score_threshold(self) -> float:
        return self._score_threshold

    @log_connector(connector_type="WEB", log_input=True, log_output=True)
    async def search(
        self,
        query: str,
        start_date: str | None = None,
        end_date: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        search_params = {
            "search_depth": kwargs.get("search_depth", self.search_depth),
            "max_results": kwargs.get("max_results", self.max_results),
        }

        if start_date:
            search_params["start_date"] = start_date
        if end_date:
            search_params["end_date"] = end_date
        if self.include_domains:
            search_params["include_domains"] = self.include_domains
        if self.exclude_domains:
            search_params["exclude_domains"] = self.exclude_domains

        # Override with any additional kwargs
        search_params.update(kwargs)

        # Run sync Tavily client in thread pool for async execution
        loop = asyncio.get_running_loop()
        search_func = functools.partial(
            self.client.search,
            query,
            **search_params,
        )

        response = await loop.run_in_executor(None, search_func)

        logger.debug(
            f"Tavily search completed: query={query}, "
            f"results={len(response.get('results', []))}, "
            f"response_time={response.get('response_time', 0)}ms",
        )

        return response
