from __future__ import annotations

from typing import Any

from apps.agents.mi_agent.prompts.chart_similarity_prompt import (
    build_similarity_chart_prompt,
)
from apps.agents.mi_agent.prompts.chart_timeseries_prompt import build_timeseries_chart_prompt
from apps.agents.mi_agent.schemas.schemas import TimeSeriesInsights
from apps.agents.mi_agent.schemas.search_output import SearchOutput
from apps.agents.mi_agent.subgraphs.rdb_search.schemas import RDBSimilarityAnalysis
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.common.utils.timeseries_similarity_utils import analyze_similarity_patterns
from apps.common.values.enums import AnalysisType
from apps.connectors.llm.llm_client import invoke_llm_structured_output


@log_tool
async def generate_timeseries_insights(
    rewritten_query: str,
    analysis_type: AnalysisType,
    search_output: SearchOutput,
) -> TimeSeriesInsights | None:
    """차트 및 시계열 인사이트를 생성합니다.

    Returns:
        TimeSeriesInsights: 주요 지표, 시계열 하이라이트, 차트 데이터를 포함한 인사이트
    """
    prompt: str = _build_chart_prompt(rewritten_query, analysis_type, search_output)
    if not prompt:
        return None

    llm_response = await invoke_llm_structured_output(output_schema=TimeSeriesInsights, prompt=prompt)
    return llm_response.result


def _build_chart_prompt(rewritten_query: str, analysis_type: AnalysisType, search_output: SearchOutput) -> str:
    prompt: str = ""
    if analysis_type == AnalysisType.TIMESERIES_TREND:
        prompt = _build_timeseries_chart_prompt(rewritten_query, search_output)
    elif analysis_type == AnalysisType.SIMILARITY_PATTERN:
        metric_data = (
            search_output.rdb_search_output.metric_data
            if search_output.rdb_search_output and search_output.rdb_search_output.metric_data
            else []
        )
        rdb_similarity_analysis = get_similarity_patterns_analysis(metric_data, [], top_n=3)
        prompt = _build_similarity_chart_prompt_internal(rewritten_query, rdb_similarity_analysis)
    return prompt


def _build_timeseries_chart_prompt(
    rewritten_query: str,
    search_output: SearchOutput,
) -> str:
    vector_sources = (
        search_output.vdb_search_output.vector_sources
        if search_output.vdb_search_output and search_output.vdb_search_output.vector_sources
        else []
    )

    metric_data = (
        search_output.rdb_search_output.metric_data
        if search_output.rdb_search_output and search_output.rdb_search_output.metric_data
        else []
    )

    used_tables = (
        search_output.rdb_search_output.used_tables
        if search_output.rdb_search_output and search_output.rdb_search_output.used_tables
        else []
    )

    web_results = (
        search_output.web_search_output.web_results
        if search_output.web_search_output and search_output.web_search_output.web_results
        else []
    )

    # sub_source: vector_sources + web_results
    sub_source_parts = []
    if vector_sources:
        sub_source_parts.append(
            "\n\n".join(
                (
                    f"[VDB-{i}] {vs.metadata.title} | {vs.metadata.source}"
                    f" | product_num={vs.metadata.product_num} | product_data_num={vs.metadata.product_data_num}"
                )
                for i, vs in enumerate(vector_sources, start=1)
            )
        )
    if web_results:
        sub_source_parts.append(
            "\n\n".join(f"[WEB-{i}] {wr.title} | {wr.url}" for i, wr in enumerate(web_results, start=1))
        )

    return build_timeseries_chart_prompt(
        message=rewritten_query,
        main_source=metric_data,
        sub_source="\n\n".join(sub_source_parts),
        source=", ".join(
            [
                *(["mi_model"] if used_tables else []),
                *(["vector_db"] if vector_sources else []),
                *(["web_search"] if web_results else []),
            ],
        ),
    )


def get_similarity_patterns_analysis(
    metric_data: list[dict[str, Any]],
    historical_data: list,
    top_n: int = 3,
) -> RDBSimilarityAnalysis:
    current_data = metric_data

    current_df, historical_df, similar_patterns_df = analyze_similarity_patterns(
        current_data=current_data,
        historical_data=historical_data,
        top_n=top_n,
    )

    if similar_patterns_df.empty:
        logger.info("유사 구간이 없습니다. LLM 분석만 진행합니다.")
        return None

    similarity_pattern_analysis: RDBSimilarityAnalysis = RDBSimilarityAnalysis(
        similarity_current_data=[current_df.to_dict(orient="list")],
        similarity_historical_data=[historical_df.to_dict(orient="list")],
        similar_patterns=similar_patterns_df.to_dict(orient="records"),
    )
    return similarity_pattern_analysis


def _build_similarity_chart_prompt_internal(
    rewritten_query: str,
    rdb_similarity_analysis: RDBSimilarityAnalysis | None,
) -> str:
    """유사 패턴 분석용 차트 프롬프트 생성."""
    if rdb_similarity_analysis is None:
        return ""

    current_data = (
        rdb_similarity_analysis.similarity_current_data[0]
        if rdb_similarity_analysis.similarity_current_data
        else {}
    )

    logger.info(
        f"[유사 구간 추출 완료] 유사도 기반 유사 구간 수: {len(rdb_similarity_analysis.similar_patterns)}",
    )

    return build_similarity_chart_prompt(
        message=rewritten_query,
        current_data=current_data,
        historical_data=rdb_similarity_analysis.similar_patterns,
    )
