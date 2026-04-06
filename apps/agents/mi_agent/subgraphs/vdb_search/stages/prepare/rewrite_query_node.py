from apps.agents.mi_agent.subgraphs.vdb_search.state import VDBSearchState
from apps.agents.mi_agent.subgraphs.vdb_search.tools.search_queries import prepare_vdb_search_queries


async def rewrite_query_node(state: VDBSearchState) -> VDBSearchState:
    state.vdb_structured_queries = await prepare_vdb_search_queries(
        rewritten_query=state.rewritten_query,
        content_provider_accesses=state.content_provider_vdb_accesses,
    )
    return state
