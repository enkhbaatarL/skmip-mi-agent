"""Web search tool for executing web searches with period splitting and async execution."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from dateutil import parser as date_parser

from apps.agents.mi_agent.subgraphs.web_search.schemas import WebSearchResult
from apps.common.logging.logger_config import logger
from apps.connectors.web.base import WebSearchProvider


async def web_search_tool(
    query: str,
    periods: list[dict[str, str]],
) -> tuple[list[WebSearchResult], dict[str, Any]]:
    from apps.common.runtime.runtime import get_web_search_provider, get_web_semaphore

    start_time = datetime.now()

    # Get resources from RuntimeContext
    provider = await get_web_search_provider()
    semaphore = get_web_semaphore()
    score_threshold = provider.score_threshold

    # periods가 비어있으면 기간 필터링 없이 검색
    if not periods:
        logger.info("No periods specified, searching without date filter")
        async with semaphore:
            response = await provider.search(
                query=query,
                start_date=None,
                end_date=None,
            )

        raw_results = response.get("results", [])
        filtered_results = [r for r in raw_results if r.get("score", 0.0) >= score_threshold]

        unique_results = [
            WebSearchResult(
                query=query,
                period="no_filter",
                score=r.get("score", 0.0),
                title=r.get("title", ""),
                url=r.get("url", ""),
                content=r.get("content", ""),
                published_date=r.get("published_date"),
                raw_content=r.get("raw_content"),
            )
            for r in filtered_results
            if isinstance(r, dict)
        ]

        duration_ms = (datetime.now() - start_time).total_seconds() * 1000
        metadata = {
            "total_periods": 0,
            "total_results": len(unique_results),
            "search_duration_ms": duration_ms,
            "query": query,
        }

        logger.info(
            f"Web search completed (no date filter): query={query}, results={len(unique_results)}, duration={duration_ms:.2f}ms",
        )

        return unique_results, metadata

    # periods가 있으면 기간별 검색
    split_periods = []
    for period in periods:
        split_periods.extend(_split_period_by_duration(period))

    logger.info(f"Split {len(periods)} periods into {len(split_periods)} chunks")

    # Execute searches in parallel with semaphore control
    tasks = [
        _search_single_period(
            query=query,
            period=period,
            provider=provider,
            score_threshold=score_threshold,
            semaphore=semaphore,
        )
        for period in split_periods
    ]

    period_results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect and process results
    all_results: list[WebSearchResult] = []
    for i, result in enumerate(period_results):
        if isinstance(result, Exception):
            logger.error(f"Period search task {i} failed: {result}")
        elif isinstance(result, list):
            all_results.extend(result)

    # Remove duplicates by URL
    unique_results = _deduplicate_by_url(all_results)

    # Calculate metadata
    duration_ms = (datetime.now() - start_time).total_seconds() * 1000
    metadata = {
        "total_periods": len(split_periods),
        "total_results": len(unique_results),
        "search_duration_ms": duration_ms,
        "query": query,
    }

    logger.info(
        f"Web search completed: query={query}, results={len(unique_results)}, duration={duration_ms:.2f}ms",
    )

    return unique_results, metadata


async def _search_single_period(
    query: str,
    period: dict[str, str],
    provider: WebSearchProvider,
    score_threshold: float,
    semaphore: asyncio.Semaphore,
) -> list[WebSearchResult]:
    """Execute search for a single period with semaphore control."""
    start_date = period.get("start", "")
    end_date = period.get("end", "")

    # Handle single date or no date case
    if not start_date or start_date == end_date:
        start_date, end_date = _get_published_date_range(start_date)

    # Execute with semaphore control
    async with semaphore:
        response = await provider.search(
            query=query,
            start_date=start_date,
            end_date=end_date,
        )

    # Filter and convert results
    raw_results = response.get("results", [])
    filtered_results = [r for r in raw_results if r.get("score", 0.0) >= score_threshold]

    period_str = f"{start_date}_{end_date}"
    web_results = []

    for result in filtered_results:
        if not isinstance(result, dict):
            continue

        web_results.append(
            WebSearchResult(
                query=query,
                period=period_str,
                score=result.get("score", 0.0),
                title=result.get("title", ""),
                url=result.get("url", ""),
                content=result.get("content", ""),
                published_date=result.get("published_date"),
                raw_content=result.get("raw_content"),
            ),
        )

    logger.debug(
        f"Period [{period_str}] search: {len(web_results)} results (filtered from {len(raw_results)})",
    )

    return web_results


def _split_period_by_duration(period: dict[str, str]) -> list[dict[str, str]]:
    start_date = datetime.strptime(period["start"], "%Y-%m-%d")
    end_date = datetime.strptime(period["end"], "%Y-%m-%d")

    # Adjust dates to not exceed today
    today = datetime.now().date()
    if start_date.date() >= today:
        yesterday = today - timedelta(days=1)
        start_date = datetime.combine(yesterday, datetime.min.time())

    if end_date.date() > today:
        end_date = datetime.combine(today, datetime.min.time())

    total_days = (end_date - start_date).days + 1
    chunk_days = _get_chunk_size(total_days)

    periods = []
    current_date = start_date

    while current_date <= end_date:
        chunk_end = min(current_date + timedelta(days=chunk_days - 1), end_date)
        periods.append(
            {
                "start": current_date.strftime("%Y-%m-%d"),
                "end": chunk_end.strftime("%Y-%m-%d"),
            },
        )
        current_date = chunk_end + timedelta(days=1)

    return periods


def _get_chunk_size(total_days: int) -> int:
    """Determine chunk size based on total period duration."""
    if total_days <= 7:
        return 3
    if total_days <= 15:
        return 5
    if total_days <= 30:
        return 7
    if total_days <= 90:
        return 10
    if total_days <= 180:
        return 15
    return 30


def _get_published_date_range(
    base_date: str,
    window_days: int = 1,
) -> tuple[str, str]:
    """Get date range around a base date."""
    base = datetime.now().date() if not base_date else date_parser.parse(base_date.strip()).date()

    start_date = base - timedelta(days=window_days)
    end_date = base + timedelta(days=window_days)

    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")


def _deduplicate_by_url(results: list[WebSearchResult]) -> list[WebSearchResult]:
    """Remove duplicate results by URL, keeping the highest score."""
    seen_urls: dict[str, WebSearchResult] = {}

    for result in results:
        url = result.url
        if url not in seen_urls or result.score > seen_urls[url].score:
            seen_urls[url] = result

    return list(seen_urls.values())
