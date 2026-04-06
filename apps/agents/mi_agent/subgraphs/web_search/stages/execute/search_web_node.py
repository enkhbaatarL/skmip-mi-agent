# TODO: strict모드 여부에 따라서 exception처리 다르게 검토
"""Web search execution node."""

from apps.agents.mi_agent.subgraphs.web_search.state import WebSearchState
from apps.agents.mi_agent.subgraphs.web_search.tools.web_search import web_search_tool
from apps.common.logging.logger_config import logger


async def search_web_node(state: WebSearchState) -> WebSearchState:
    try:
        results, metadata = await web_search_tool(
            query=state.rewritten_query,
            periods=state.search_periods,
        )

        state.web_search_results = results
        state.total_results = metadata.get("total_results", len(results))
        state.search_duration_ms = metadata.get("search_duration_ms", 0.0)

        logger.info(
            f"Web search completed: {state.total_results} results, {state.search_duration_ms:.2f}ms",
        )

    except Exception as e:
        logger.error(f"Web search failed: {e}", exc_info=True)
        state.web_search_results = []
        state.total_results = 0

    return state
