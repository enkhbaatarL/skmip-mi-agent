from __future__ import annotations

from uuid import UUID

from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSearchCandidate, RDBSearchQuery, VDBSearchCandidate
from apps.common.configs.settings import get_settings
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.connectors.vdb.enums import RetrievalMode
from apps.connectors.vdb.schemas import RetrievalResult
from apps.connectors.vdb.vector_db import AipKnowledgeRetriever


@log_tool
async def retrieve_rdb_search_candidates(
    rdb_search_queries: list[RDBSearchQuery],
    authorized_product_nums: list[int],
    company_code: str | None,
    rdb_search_metadata_repo_id: UUID | None = None,
) -> list[RDBSearchCandidate]:
    return await _retrieve_candidate_data(
        rdb_search_queries=rdb_search_queries,
        authorized_product_nums=authorized_product_nums,
        company_code=company_code,
        rdb_search_metadata_repo_id=rdb_search_metadata_repo_id,
    )

@log_tool
async def _retrieve_candidate_data(
    rdb_search_queries: list[RDBSearchQuery],
    authorized_product_nums: list[int],
    company_code: str | None,
    rdb_search_metadata_repo_id: UUID | None = None,
) -> list[RDBSearchCandidate]:
    effective_repo_id: UUID = rdb_search_metadata_repo_id or get_settings().rdb_search_metadata_repo_id

    retriever = AipKnowledgeRetriever()
    rdb_search_candidates: list[RDBSearchCandidate] = []

    if not authorized_product_nums:
        return rdb_search_candidates

    nums = ", ".join(str(num) for num in sorted(set(authorized_product_nums)))
    filter_expr: str = f"src_del_yn eq 'N' and del_yn eq 'N' and gds_no in [{nums}]"

    for rdb_search_query in rdb_search_queries:
        rewrite_query: str = rdb_search_query.query
        query_text: str = rdb_search_query.search_text

        retrieval_results: list[RetrievalResult] = await retriever.retrieve(
            repo_id=effective_repo_id,
            query=rewrite_query,
            retrieval_mode=RetrievalMode.SPARSE,
            top_k=10,
            query_keywords=query_text,
            text_search_fields=["content", "keywords"],
            filter_expn=filter_expr,
        )
        vdb_candidates: list[VDBSearchCandidate] = []

        for item in retrieval_results:
            metadata = item.metadata

            vdb_candidate = VDBSearchCandidate(
                tbl_expn=item.content,
                agtmtm_id=metadata.get("agtmtm_id"),
            )
            vdb_candidates.append(vdb_candidate)

        rdb_search_candidate: RDBSearchCandidate = RDBSearchCandidate(
            query=rewrite_query,
            company_code=company_code,
            vdb_search_candidates=vdb_candidates,
        )
        rdb_search_candidates.append(rdb_search_candidate)

    logger.debug(f"[_retrieve_candidate_data] OUTPUT | candidates={rdb_search_candidates!r}")
    return rdb_search_candidates
