"""Factory for creating web search provider instances."""

from __future__ import annotations

from typing import Any

from apps.common.configs.config import BaseSettings, get_settings
from apps.common.logging.logger_config import logger
from apps.connectors.web.base import WebSearchProvider
from apps.connectors.web.provider import ResponsesWebSearchProvider
from apps.connectors.web.tavily_provider import TavilySearchProvider


class WebSearchProviderFactory:
    _providers: dict[str, type[WebSearchProvider]] = {
        # "tavily": TavilySearchProvider,
        "responses": ResponsesWebSearchProvider,
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
    def parse_provider_names(cls, raw: str) -> list[str]:
        """``"responses,tavily"`` 형태의 설정값을 provider 키 목록으로 정규화한다.

        나열 순서가 곧 검색 결과 병합 우선순위다.
        """
        names: list[str] = []
        for token in raw.split(","):
            name = token.strip().lower()
            if not name or name in names:
                continue
            names.append(name)
        return names

    @classmethod
    def build_config(cls, provider_type: str, settings: BaseSettings) -> dict[str, Any]:
        """Provider 별 생성자 인자를 Settings 에서 뽑아낸다."""
        if provider_type == "responses":
            return {
                "api_key": settings.web_search_api_key or None,
                "base_url": settings.web_search_base_url or None,
                "model": settings.web_search_model or None,
                "search_context_size": settings.web_search_context_size,
                "max_results": settings.web_search_max_results,
                "include_domains": settings.web_search_include_domains,
                "exclude_domains": settings.web_search_exclude_domains,
                "score_threshold": settings.web_search_score_threshold,
                "reasoning_effort": settings.web_search_reasoning_effort,
                "tool_choice": settings.web_search_tool_choice,
                "max_tool_calls": settings.web_search_max_tool_calls,
                "timeout_sec": settings.web_search_timeout_sec,
                "max_retries": settings.web_search_max_retries,
            }
        # if provider_type == "tavily":
        #     if not settings.tavily_api_key:
        #         msg = "tavily provider 를 사용하려면 TAVILY_API_KEY 가 필요합니다."
        #         raise ValueError(msg)
        #     return {
        #         "api_key": settings.tavily_api_key,
        #         "search_depth": settings.tavily_search_depth,
        #         "max_results": settings.tavily_max_results,
        #         "include_domains": settings.tavily_include_domains,
        #         "exclude_domains": settings.tavily_exclude_domains,
        #         "score_threshold": settings.tavily_score_threshold,
        #     }

        msg = (
            f"No configuration mapping for provider: {provider_type}. "
            f"Please add configuration in WebSearchProviderFactory.build_config()"
        )
        raise ValueError(
            msg,
        )

    @classmethod
    def create_all_from_settings(cls) -> list[tuple[str, WebSearchProvider]]:
        """``web_search_provider`` 에 나열된 provider 를 모두 생성한다.

        Returns:
            ``(provider 키, provider 인스턴스)`` 목록. 설정 나열 순서를 유지한다.

        Raises:
            ValueError: 설정이 비었거나 모든 provider 생성에 실패한 경우.

        """
        settings: BaseSettings = get_settings()
        names = cls.parse_provider_names(settings.web_search_provider)
        if not names:
            msg = "web_search_provider 가 비어 있습니다. 최소 1개 provider 를 지정해야 합니다."
            raise ValueError(msg)

        providers: list[tuple[str, WebSearchProvider]] = []
        errors: list[str] = []
        for name in names:
            try:
                providers.append((name, cls.create(name, cls.build_config(name, settings))))
            except Exception as exc:
                # provider 1개의 설정 오류로 나머지 provider 까지 죽이지 않는다.
                logger.error(f"[CONNECTOR][WEB][factory] PROVIDER_INIT_FAILED | provider={name} | error={exc!r}")
                errors.append(f"{name}: {exc}")

        if not providers:
            msg = f"사용 가능한 web search provider 가 없습니다. {' / '.join(errors)}"
            raise ValueError(msg)

        logger.info(f"[CONNECTOR][WEB][factory] PROVIDERS_READY | providers={[name for name, _ in providers]}")
        return providers

    @classmethod
    def create_from_settings(cls) -> WebSearchProvider:
        """단일 provider 만 필요한 호출부용. 설정에 나열된 첫 provider 를 돌려준다."""
        _, provider = cls.create_all_from_settings()[0]
        return provider
