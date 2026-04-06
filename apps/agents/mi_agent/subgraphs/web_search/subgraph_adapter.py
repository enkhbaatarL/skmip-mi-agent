"""Adapters for converting between MariAgentState and WebSearchState."""

import re
from collections.abc import Mapping
from datetime import datetime, timedelta

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.subgraphs.web_search.schemas import WebSearchOutput
from apps.agents.mi_agent.subgraphs.web_search.state import WebSearchState


def to_state(agent_state: MariAgentState | Mapping) -> WebSearchState:
    """Convert MariAgentState to WebSearchState.

    Args:
        agent_state: Main agent state or mapping

    Returns:
        WebSearchState for subgraph execution

    """
    if isinstance(agent_state, Mapping):
        rewritten_query = agent_state.get("rewritten_query", "")
        histories = agent_state.get("histories", [])
    else:
        rewritten_query = agent_state.rewritten_query or ""
        histories = agent_state.histories or []

    # Extract search periods from rewritten_query
    search_periods = _extract_search_periods(rewritten_query, histories)

    # 날짜가 있으면 쿼리에서 날짜 부분 제거 (기간 필터링은 periods로 처리)
    search_query = rewritten_query
    if search_periods:
        search_query = _remove_dates_from_query(rewritten_query)

    return WebSearchState(
        rewritten_query=search_query,  # 날짜 제거된 쿼리
        search_periods=search_periods,
    )


def to_output(web_state: WebSearchState | Mapping) -> WebSearchOutput:
    if isinstance(web_state, Mapping):
        web_search_results = web_state.get("web_search_results", [])
        total_results = web_state.get("total_results", 0)
        search_duration_ms = web_state.get("search_duration_ms", 0.0)
    else:
        web_search_results = web_state.web_search_results
        total_results = web_state.total_results
        search_duration_ms = web_state.search_duration_ms

    # Convert results to web_sources for backward compatibility
    web_sources = []
    for result in web_search_results:
        # Format: "title - content (url)"
        source_text = f"{result.title}\n{result.content}\nURL: {result.url}"
        web_sources.append(source_text)

    return WebSearchOutput(
        web_results=web_search_results,
        web_sources=web_sources,
        total_results=total_results,
        search_metadata={
            "search_duration_ms": search_duration_ms,
        },
    )


def _extract_search_periods(
    rewritten_query: str,
    histories: list[dict],
) -> list[dict[str, str]]:
    """Extract search periods from rewritten_query or conversation histories.

    Args:
        rewritten_query: Rewritten user query with date information
        histories: List of conversation history items

    Returns:
        - 날짜가 있으면: [{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}]
        - 날짜가 없으면: [] (빈 리스트 - 기간 필터링 없음)

    """
    # rewritten_query에서 날짜 패턴 추출 (YYYY-MM-DD)
    date_pattern = r"\d{4}-\d{2}-\d{2}"
    dates = re.findall(date_pattern, rewritten_query)

    if dates:
        # 날짜 문자열을 datetime으로 변환
        parsed_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
        start_date = min(parsed_dates)
        end_date = max(parsed_dates)

        # 미래 날짜 처리: end_date가 오늘보다 미래면 오늘로 조정
        today = datetime.now().date()
        if end_date > today:
            end_date = today
        if start_date > today:
            start_date = today - timedelta(days=7)

        return [
            {
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
            },
        ]

    # 날짜가 없으면 빈 리스트 반환 (기간 필터링 없음)
    return []


def _remove_dates_from_query(query: str) -> str:
    """Remove date patterns and related connectors from query.

    예시:
    - "2024-07-15부터 2025-01-14까지 달러지수 동향" → "달러지수 동향"
    - "2024-12-01 ~ 2025-01-01 기간의 금리" → "금리"

    """
    # 날짜 패턴과 연결어 제거
    # 패턴: YYYY-MM-DD + 연결어(부터, 까지, ~, 기간, 의, 에서, 사이 등)
    patterns = [
        r"\d{4}-\d{2}-\d{2}\s*부터\s*",
        r"\d{4}-\d{2}-\d{2}\s*까지\s*",
        r"\d{4}-\d{2}-\d{2}\s*~\s*",
        r"\d{4}-\d{2}-\d{2}\s*에서\s*",
        r"\d{4}-\d{2}-\d{2}\s*사이\s*",
        r"\d{4}-\d{2}-\d{2}\s*기간의?\s*",
        r"\d{4}-\d{2}-\d{2}\s*",  # 단독 날짜
    ]

    result = query
    for pattern in patterns:
        result = re.sub(pattern, "", result)

    # 정리: 연속 공백 제거, 앞뒤 공백 제거
    result = re.sub(r"\s+", " ", result).strip()

    return result
