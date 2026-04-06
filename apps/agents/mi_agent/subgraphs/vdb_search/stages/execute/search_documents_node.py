from __future__ import annotations

from apps.agents.mi_agent.subgraphs.vdb_search.state import VDBSearchState
from apps.agents.mi_agent.subgraphs.vdb_search.tools.search_documents import search_documents_tool
from apps.common.logging.decorators import log_node


@log_node
async def search_documents_node(state: VDBSearchState) -> VDBSearchState:
    state.vector_sources = await search_documents_tool(
        content_provider_accesses=state.content_provider_vdb_accesses,
        rewritten_query=state.rewritten_query,
        vdb_structured_queries=state.vdb_structured_queries,
    )
    return state
