from __future__ import annotations

import asyncio
import json

from apps.agents.mi_agent.schemas.mari_agent_input import ContentProvider, ContentProviderAccess
from apps.agents.mi_agent.subgraphs.vdb_search.schemas import VDBSearchItem, VdbStructuredQuery, VectorSourceModel
from apps.common.configs.settings import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.connectors.vdb.config_loader import get_retrieval_options
from apps.connectors.vdb.enums import RetrievalMode
from apps.connectors.vdb.schemas import RetrievalResult
from apps.connectors.vdb.vector_db import AipKnowledgeRetriever


@log_tool
def _get_meta_repo_id(content_provider: str) -> str:
    entry = get_settings().vdb_document_repo_ids_by_provider.get(content_provider)
    if not entry:
        raise MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=f"VDB repo mapping이 없습니다: content_provider={content_provider}")
    repo_id = entry.get("meta_repo_id") if isinstance(entry, dict) else entry
    if not repo_id:
        raise MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=f"VDB meta_repo_id가 없습니다: content_provider={content_provider}")
    return repo_id

@log_tool
def _get_chunk_repo_id(content_provider: str) -> str:
    entry = get_settings().vdb_document_repo_ids_by_provider.get(content_provider)
    if not entry or not isinstance(entry, dict):
        raise MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=f"VDB repo mapping이 없습니다: content_provider={content_provider}")
    repo_id = entry.get("chunk_repo_id")
    if not repo_id:
        raise MIBaseError(ErrorCode.DATA_RETRIEVAL_FAILED, detail=f"VDB chunk_repo_id가 없습니다: content_provider={content_provider}")
    return repo_id



@log_tool
def _build_access_filter(access: ContentProviderAccess) -> str | None:
    return (
        f"gds_no in [{', '.join(str(n) for n in access.authorized_product_nums)}]"
        if access.authorized_product_nums
        else None
    )

@log_tool
def _combine_filters(*filters: str | None) -> str | None:
    active = [f for f in filters if f]
    return " and ".join(active) if active else None

@log_tool
def _build_content_id_filter(gds_data_no: int) -> str:
    return f"content_id eq {gds_data_no}"

@log_tool
def _build_period_filter(vdb_structured_queries: list[VdbStructuredQuery]) -> str | None:
    filters = [
        f"period_start_at lte {sq.period_end_at} and period_end_at gte {sq.period_start_at}"
        for sq in vdb_structured_queries
        if sq.period_start_at and sq.period_end_at
    ]
    if not filters:
        logger.debug("[_build_period_filter] OUTPUT | result=None")
        return None
    return " or ".join(f"({f})" for f in filters) if len(filters) > 1 else filters[0]


# ── 쿼리 키워드 빌더 ──────────────────────────────────────────────────────────

@log_tool
def _build_query_keywords(vdb_structured_queries: list[VdbStructuredQuery]) -> str | None:
    all_keywords = [kw for sq in vdb_structured_queries for kw in sq.keywords if kw]
    if not all_keywords:
        logger.debug("[_build_query_keywords] OUTPUT | result=None")
        return None
    seen: set[str] = set()
    merged: list[str] = []
    for kw in all_keywords:
        key = kw.lower()
        if key not in seen:
            seen.add(key)
            merged.append(kw)
    return " ".join(merged) if merged else None



@log_tool
def _extract_gds_data_nos(results: list[RetrievalResult]) -> list[int]:
    seen: set[int] = set()
    nos: list[int] = []
    for doc in results:
        metadata = getattr(doc, "metadata", {}) or {}
        raw = metadata.get("gds_data_no")
        if raw is not None:
            val = int(raw)
            if val not in seen:
                seen.add(val)
                nos.append(val)
    return nos



@log_tool
async def _search_omdia_access(
    access: ContentProviderAccess,
    access_filter: str,
    rewritten_query: str,
    retriever: AipKnowledgeRetriever,
    query_keywords: str | None,
    period_filter: str | None,
) -> list[RetrievalResult]:

    opts = get_retrieval_options(access.content_provider)

    # 1단계 — 메타 인덱스 검색으로 관련 문서 식별
    phase1_results = await retriever.retrieve(
        repo_id=_get_meta_repo_id(access.content_provider),
        query=rewritten_query,
        retrieval_mode=opts.retrieval_mode,
        top_k=opts.top_k,
        query_keywords=query_keywords,
        text_search_fields=opts.text_search_fields,
        filter_expn=_combine_filters(access_filter, period_filter),
    )
    if not phase1_results:
        logger.debug("[_search_omdia_access] OUTPUT | result=[] (phase1 empty)")
        return []

    # 1단계 결과에서 gds_data_no 추출
    gds_data_nos = _extract_gds_data_nos(phase1_results)
    if not gds_data_nos:
        logger.debug("[_search_omdia_access] OUTPUT | result=[] (no gds_data_nos)")
        return []

    # 2단계 — gds_data_no별로 chunk 인덱스에서 rewritten_query 기준 dense 검색 (병렬)
    chunk_repo_id = _get_chunk_repo_id(access.content_provider)
    phase2_results: list[list[RetrievalResult]] = await asyncio.gather(
        *[
            retriever.retrieve(
                repo_id=chunk_repo_id,
                query=rewritten_query,
                retrieval_mode=RetrievalMode.DENSE,
                top_k=opts.top_k,
                filter_expn=_combine_filters(access_filter, _build_content_id_filter(gds_data_no)),
            )
            for gds_data_no in gds_data_nos
        ],
    )
    return [doc for results in phase2_results for doc in results]


@log_tool
async def _search_default_access(
    access: ContentProviderAccess,
    access_filter: str,
    rewritten_query: str,
    retriever: AipKnowledgeRetriever,
    query_keywords: str | None,
) -> list[RetrievalResult]:
    opts = get_retrieval_options(access.content_provider)
    result = await retriever.retrieve(
        repo_id=_get_meta_repo_id(access.content_provider),
        query=rewritten_query,
        retrieval_mode=opts.retrieval_mode,
        top_k=opts.top_k,
        query_keywords=query_keywords,
        text_search_fields=opts.text_search_fields,
        filter_expn=access_filter,
    )
    # logger.debug(f"[_search_default_access] OUTPUT | result={result!r}")
    return result


@log_tool
async def _search_for_access(
    access: ContentProviderAccess,
    rewritten_query: str,
    retriever: AipKnowledgeRetriever,
    query_keywords: str | None,
    period_filter: str | None,
) -> list[RetrievalResult]:
    if access.content_provider not in (ContentProvider.OMDIA, ContentProvider.LSEG):
        return []
    access_filter = _build_access_filter(access)
    if not access_filter or len(access_filter) < 1:
        return []
    if access.content_provider == ContentProvider.OMDIA:
        result = await _search_omdia_access(
            access, access_filter, rewritten_query, retriever, query_keywords, period_filter,
        )
    else:
        result = await _search_default_access(
            access, access_filter, rewritten_query, retriever, query_keywords,
        )
    return result


@log_tool
def dedupe_retrieval_results(
    results_per_repo: list[list[RetrievalResult]],
) -> list[RetrievalResult]:
    dedup_map: dict[str, RetrievalResult] = {}

    for repo_results in results_per_repo:
        for doc in repo_results:
            metadata = getattr(doc, "metadata", {}) or {}
            doc_id = metadata.get("document_id")

            if doc_id:
                key = f"document_id:{doc_id}"
            else:
                key = "metadata:" + json.dumps(
                    metadata,
                    sort_keys=True,
                    ensure_ascii=False,
                )

            dedup_map.setdefault(key, doc)

    return list(dedup_map.values())

@log_tool
def refine_retrieval_results(
    retrieval_results: list[RetrievalResult],
) -> list[VDBSearchItem]:
    sorted_results = sorted(
        retrieval_results,
        key=lambda doc: float(getattr(doc, "score", 0.0) or 0.0),
        reverse=True,
    )[:3]

    items: list[VDBSearchItem] = []
    for doc in sorted_results:
        content: str = getattr(doc, "content", "") or ""
        metadata = getattr(doc, "metadata", {}) or {}
        score: float = float(getattr(doc, "score", 0.0) or 0.0)

        title = metadata.get("title") if metadata.get("title") else metadata.get("headline") #TODO: LSEG 재인덱싱 하면 다시 보기
        gds_no = metadata.get("gds_no")
        document_id = metadata.get("document_id")
        gds_data_no = metadata.get("content_id") #TODO: LSEG 재인덱싱 하면 다시 보기

        _checks = [
            ("title", title),
            ("product_num", gds_no),
        ]
        missing = [f for f, v in _checks if v is None]
        if missing:
            raise MIBaseError(
                ErrorCode.DATA_RETRIEVAL_FAILED,
                detail=f"VDB 검색 결과 문서에 필수 메타데이터가 없습니다: {', '.join(missing)}",
            )

        items.append(
            VDBSearchItem(
                content=content,
                metadata=VectorSourceModel(
                    source=metadata.get("contributor", metadata.get("source", "")),
                    title=title,
                    product_num=gds_no,
                    product_data_num=gds_data_no,
                    document_id=document_id,
                ),
                score=score,
            ),
        )

    return items



@log_tool
async def search_documents_tool(
    content_provider_accesses: list[ContentProviderAccess],
    rewritten_query: str,
    vdb_structured_queries: list[VdbStructuredQuery] | None = None,
) -> list[VDBSearchItem]:
    if not content_provider_accesses:
        return []

    query_keywords = _build_query_keywords(vdb_structured_queries or [])
    period_filter = _build_period_filter(vdb_structured_queries or [])
    retriever = AipKnowledgeRetriever()

    results_per_access: list[list[RetrievalResult]] = await asyncio.gather(
        *[
            _search_for_access(access, rewritten_query, retriever, query_keywords, period_filter)
            for access in content_provider_accesses
        ],
    )

    all_results = dedupe_retrieval_results(list(results_per_access))
    if not all_results:
        return []

    return refine_retrieval_results(all_results)
