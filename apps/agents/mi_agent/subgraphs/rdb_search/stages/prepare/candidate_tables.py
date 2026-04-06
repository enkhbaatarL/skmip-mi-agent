# TODO: 병렬 처리 또는 중복 처리 제거
from apps.agents.mi_agent.subgraphs.rdb_search.state import RDBSearchState
from apps.agents.mi_agent.subgraphs.rdb_search.tools.search_candidates import retrieve_rdb_search_candidates
from apps.common.values.enums import AnalysisType


async def select_candidate_tables_node(state: RDBSearchState) -> RDBSearchState:
    state.candidate_items = await retrieve_rdb_search_candidates(
        rdb_search_queries=state.rdb_search_queries,
        authorized_product_nums=state.content_provider_rdb_accesses.authorized_product_nums,
        company_code=state.company_code,
        rdb_search_metadata_repo_id=state.rdb_search_metadata_repo_id,
    )

    if state.analysis_type == AnalysisType.SIMILARITY_PATTERN:
        state.candidate_items_historical = await retrieve_rdb_search_candidates(
            rdb_search_queries=state.rdb_search_queries_historical,
            authorized_product_nums=state.content_provider_rdb_accesses.authorized_product_nums,
            company_code=state.company_code,
            rdb_search_metadata_repo_id=state.rdb_search_metadata_repo_id,
        )

    return state
