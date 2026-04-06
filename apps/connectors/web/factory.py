"""Factory for creating web search provider instances."""

from typing import Any

from pydantic_settings import BaseSettings

from apps.common.configs.settings import get_settings
from apps.connectors.web.base import WebSearchProvider
from apps.connectors.web.tavily_provider import TavilySearchProvider


class WebSearchProviderFactory:
    _providers: dict[str, type[WebSearchProvider]] = {
        "tavily": TavilySearchProvider,
        # Future providers can be added here:
        # "bing": BingSearchProvider,
        # "google": GoogleSearchProvider,
    }

    @classmethod
    def register(cls, name: str, provider_class: type[WebSearchProvider]) -> None:
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, provider_type: str, config: dict[str, Any]) -> WebSearchProvider:
        if provider_type not in cls._providers:
            msg = f"Unknown provider type: {provider_type}. Available providers: {list(cls._providers.keys())}"
            raise ValueError(
                msg,
            )

        provider_class = cls._providers[provider_type]
        return provider_class(**config)

    @classmethod
    def create_from_settings(cls) -> WebSearchProvider:
        settings: BaseSettings = get_settings()
        provider_type = settings.web_search_provider.lower()

        # Map settings to provider-specific configuration
        if provider_type == "tavily":
            config = {
                "api_key": settings.tavily_api_key,
                "search_depth": settings.tavily_search_depth,
                "max_results": settings.tavily_max_results,
                "include_domains": settings.tavily_include_domains,
                "exclude_domains": settings.tavily_exclude_domains,
                "score_threshold": settings.tavily_score_threshold,
            }
        else:
            msg = (
                f"No configuration mapping for provider: {provider_type}. "
                f"Please add configuration in WebSearchProviderFactory.create_from_settings()"
            )
            raise ValueError(
                msg,
            )

        return cls.create(provider_type, config)
