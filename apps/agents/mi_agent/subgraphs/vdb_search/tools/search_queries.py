from __future__ import annotations

import json
import re
from typing import Any

from apps.agents.mi_agent.prompts.vdb_search_rewrite_queries import (
    build_omdia_vdb_search_queries_prompt,
    build_vdb_search_queries_prompt,
)
from apps.agents.mi_agent.schemas.mari_agent_input import ContentProvider, ContentProviderAccess
from apps.agents.mi_agent.subgraphs.vdb_search.schemas import VdbStructuredQuery
from apps.agents.mi_agent.tools.search_queries import generate_search_queries, strip_code_fence
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.common.values.enums import ModelPreference
from apps.connectors.llm.llm_client import invoke_llm_function_call


VDB_SEARCH_QUERY_OUTPUT_EXAMPLE = """
[
    {
    "query": "<정제된 자연어 질의>",
    "search_text": "<검색용 키워드 문자열>"
    }
]
""".strip()

OMDIA_VDB_SEARCH_QUERY_OUTPUT_EXAMPLE = """
[
    {
        "rewritten_query": "<정제된 자연어 질의>",
        "keywords": ["<영문 키워드1>", "<영문 키워드2>", "<영문 키워드3>", "<영문 키워드4>"],
        "keywords_kr": ["<한글 키워드1>", "<한글 키워드2>", "<한글 키워드3>", "<한글 키워드4>"],
        "year": null,
        "years": [],
        "period_key": null,
        "period_start_at": null,
        "period_end_at": null,
        "period_aliases": []
    }
]
""".strip()


@log_tool
async def prepare_vdb_search_queries(
    rewritten_query: str,
    content_provider_accesses: list[ContentProviderAccess] | None = None,
) -> list[VdbStructuredQuery]:
    if _has_omdia(content_provider_accesses):
        return await _prepare_omdia_vdb_search_queries(rewritten_query)
    return await _prepare_default_vdb_search_queries(rewritten_query)

@log_tool
def _has_omdia(content_provider_accesses: list[ContentProviderAccess] | None) -> bool:
    return bool(content_provider_accesses) and any(
        a.content_provider == ContentProvider.OMDIA for a in content_provider_accesses
    )

@log_tool
async def _prepare_default_vdb_search_queries(rewritten_query: str) -> list[VdbStructuredQuery]:
    prompt = build_vdb_search_queries_prompt(
        rewritten_query=rewritten_query,
        output_example=VDB_SEARCH_QUERY_OUTPUT_EXAMPLE,
    )
    search_queries = await generate_search_queries(prompt)
    return [
        VdbStructuredQuery(
            rewritten_query=sq.query,
            keywords=(sq.search_text.split() if sq.search_text else [])[:10],
            keywords_kr=[],
            year=None,
            years=[],
            period_key=None,
            period_start_at=None,
            period_end_at=None,
            period_aliases=[],
        )
        for sq in search_queries
    ]


@log_tool
async def _prepare_omdia_vdb_search_queries(rewritten_query: str) -> list[VdbStructuredQuery]:
    prompt = build_omdia_vdb_search_queries_prompt(
        rewritten_query=rewritten_query,
        output_example=OMDIA_VDB_SEARCH_QUERY_OUTPUT_EXAMPLE,
    )
    response: dict[str, Any] = await invoke_llm_function_call(
        messages=[{"role": "user", "content": prompt}],
        preference=ModelPreference.QUALITY,
        temperature=0.0,
    )
    context = response.get("content")
    if not context:
        raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail=f"prompt:{prompt}, return context:{context}")
    return _parse_omdia_query_items(str(context))


@log_tool
def _parse_omdia_query_items(raw_text: str) -> list[VdbStructuredQuery]:
    cleaned = strip_code_fence(raw_text.strip())
    try:
        data: Any = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
        data = json.loads(match.group(0)) if match else []

    if not isinstance(data, list):
        data = [data]

    result: list[VdbStructuredQuery] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            result.append(VdbStructuredQuery.model_validate(item))
        except Exception as e:
            logger.warning(f"[TOOL][prepare_vdb_search_queries] omdia 항목 파싱 실패 | item={item!r} | error={e!r}")
    return result
