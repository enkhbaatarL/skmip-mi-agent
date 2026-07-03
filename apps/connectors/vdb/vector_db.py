from __future__ import annotations

from typing import Any
from uuid import UUID

from apps.common.configs.config import get_settings
from apps.common.logging.decorators import log_connector
from apps.common.runtime.runtime import ensure_runtime_context_ready
from apps.connectors.http.http_client import http_post
from apps.connectors.vdb.constants import AX_PLATFORM_ADVANCED_QUERY_URI
from apps.connectors.vdb.enums import RetrievalMode
from apps.connectors.vdb.schemas import (
    RetrievalAdvancedQuery,
    RetrievalOptions,
    RetrievalResult,
)


class AipKnowledgeRetriever:
    def __init__(self) -> None:
        cfg = get_settings()
        self.base_url: str = cfg.ai_platform_host_url
        self.api_key: str = cfg.api_key
        self.uri: str = AX_PLATFORM_ADVANCED_QUERY_URI

    async def _retrieval(self, query: RetrievalAdvancedQuery) -> list[RetrievalResult]:
        await ensure_runtime_context_ready()

        body = {
            "query_text": query.query_text,
            "repo_id": str(query.repo_id),
            "retrieval_options": getattr(
                query.retrieval_options,
                "model_dump",
                lambda: None,
            )(),
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        resp = await http_post(
            url=f"{self.base_url.rstrip('/')}{self.uri}",
            headers=headers,
            json=body,
        )
        datas = resp.json().get("data")
        retrieval_results: list[RetrievalResult] = []
        for data in datas:
            retrieval_result: RetrievalResult = RetrievalResult(
                content=data.get("content"),
                metadata=data.get("metadata"),
                score=data.get("score"),
            )
            retrieval_results.append(retrieval_result)
        return retrieval_results

    @log_connector(connector_type="VDB", log_input=True, log_output=True)
    async def retrieve(
        self,
        repo_id: UUID,
        query: str,
        retrieval_mode: RetrievalMode = RetrievalMode.DENSE,
        top_k: int = 10,
        query_keywords: list[str] | None = None,
        text_search_fields: list[str] | None = None,
        filter_expn: dict[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        retrieval_options = RetrievalOptions(
            retrieval_mode=retrieval_mode,
            top_k=top_k,
            query_keywords=query_keywords,
            text_search_fields=text_search_fields,
            filter=filter_expn,
        )
        retrieval_query = RetrievalAdvancedQuery(
            repo_id=repo_id,
            query_text=query,
            retrieval_options=retrieval_options,
        )
        return await self._retrieval(retrieval_query)
