# TODO: rewrite queries
from __future__ import annotations

import json
from typing import Any

from apps.agents.mi_agent.prompts.rdb_search_rewrite_queries import (
    build_rdb_search_queries_prompt,
)
from apps.agents.mi_agent.prompts.rewrite_queries import build_extract_similarity_query_params_prompt
from apps.agents.mi_agent.schemas.schemas import SearchQuery
from apps.agents.mi_agent.subgraphs.rdb_search.schemas import (
    RDBSearchQuery,
    SimilarityPatternQueryParams,
    SimilarityRdbQueryTexts,
)
from apps.agents.mi_agent.tools.search_queries import generate_search_queries
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.common.logging.decorators import log_tool
from apps.common.utils.time_utils import prior_year_period
from apps.common.values.enums import ModelPreference
from apps.connectors.llm.llm_client import invoke_llm_function_call


RDB_SEARCH_QUERY_OUTPUT_EXAMPLE = """
[
    {
    "query": "<정제된 자연어 질의>",
    "search_text": "<검색용 키워드 문자열>"
    }
]
""".strip()


@log_tool
async def prepare_rdb_search_queries(
    rewritten_query: str,
) -> list[RDBSearchQuery]:
    prompt: str = build_rdb_search_queries_prompt(
        rewritten_query=rewritten_query,
        output_example=RDB_SEARCH_QUERY_OUTPUT_EXAMPLE,
    )
    search_queries: list[SearchQuery] = await generate_search_queries(prompt)
    return [RDBSearchQuery(query=sq.query, search_text=sq.search_text) for sq in search_queries]


@log_tool
async def prepare_rdb_search_similarity_pattern_queries(
    rewritten_query: str,
) -> SimilarityRdbQueryTexts:
    similarity_query_params_prompt: str = build_extract_similarity_query_params_prompt(rewritten_query)
    response: dict[str, Any] = await invoke_llm_function_call(
        messages=[{"role": "user", "content": similarity_query_params_prompt}],
        preference=ModelPreference.QUALITY,
        temperature=0.0,
    )
    context = response.get("content")
    if len(context) < 1:
        raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail=f"prompt:{similarity_query_params_prompt}, return context:{context}")

    similarity_query_params: SimilarityPatternQueryParams = _parse_llm_similarity_query_params(
        rewritten_query,
        response,
    )
    metrics_subject: str = similarity_query_params.metric_subject
    current_start = similarity_query_params.start_date
    current_end = similarity_query_params.end_date
    current_query_text = f"{metrics_subject}의 {current_start}부터 {current_end}까지의 데이터를 조회해주세요."

    past_start, past_end = prior_year_period(current_start)
    historical_query_text = f"{metrics_subject}의 {past_start}부터 {past_end}까지의 데이터를 조회해주세요."

    return SimilarityRdbQueryTexts(
        metric_subject=metrics_subject,
        current_query_text=current_query_text,
        historical_query_text=historical_query_text,
    )

@log_tool
def _parse_llm_similarity_query_params(rewritten_query: str, response: dict[str, Any]) -> SimilarityPatternQueryParams:
    try:
        content = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        cleaned_response = content.strip().replace("```json", "").replace("```", "")
        result = json.loads(cleaned_response)
    except Exception:
        return {"metric_subject": rewritten_query, "start_date": None, "end_date": None}
    else:
        if "metric_subject" in result:
            return result
        return {"metric_subject": rewritten_query, "start_date": None, "end_date": None}
