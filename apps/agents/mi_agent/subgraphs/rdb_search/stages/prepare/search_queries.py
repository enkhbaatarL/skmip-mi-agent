# TODO: prepare_rdb_search_queries_node부분 병렬 처리 또는 prepare_rdb_search_queries한번만 호출하게 개선 검토

from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSearchQuery, SimilarityRdbQueryTexts
from apps.agents.mi_agent.subgraphs.rdb_search.state import RDBSearchState
from apps.agents.mi_agent.subgraphs.rdb_search.tools.search_queries import (
    prepare_rdb_search_queries,
    prepare_rdb_search_similarity_pattern_queries,
)
from apps.common.logging.decorators import log_node
from apps.common.values.enums import AnalysisType


@log_node
async def prepare_rdb_search_queries_node(
    state: RDBSearchState,
) -> list[RDBSearchQuery]:
    if state.analysis_type == AnalysisType.SIMILARITY_PATTERN:
        similarity_rdb_query_texts: SimilarityRdbQueryTexts = prepare_rdb_search_similarity_pattern_queries(
            state.rewritten_query,
        )
        state.rdb_search_queries = await prepare_rdb_search_queries(similarity_rdb_query_texts.current_query_text)
        state.rdb_search_queries_historical = await prepare_rdb_search_queries(
            similarity_rdb_query_texts.historical_query_text,
        )
    else:
        state.rdb_search_queries = await prepare_rdb_search_queries(state.rewritten_query)
    return state
