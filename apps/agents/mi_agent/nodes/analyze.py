from __future__ import annotations

import asyncio

from apps.agents.mi_agent.state.state import MariAgentState
from apps.agents.mi_agent.tools.analyze import analyze_search_results
from apps.agents.mi_agent.tools.generate_chart import generate_timeseries_insights
from apps.common.logging.decorators import log_node
from apps.common.streaming.decorators import stream_step
from apps.common.values.enums import AnalysisType


def _should_generate_timeseries_insights(state: MariAgentState) -> bool:
    """Timeseries insights 생성 조건 확인."""
    if state.analysis_type not in {AnalysisType.TIMESERIES_TREND, AnalysisType.SIMILARITY_PATTERN}:
        return False

    rdb = state.search_output.rdb_search_output
    return bool(rdb and rdb.metric_data and len(rdb.metric_data) > 0)


@stream_step(step_key="analysis")
@log_node
async def generate_analysis(state: MariAgentState) -> MariAgentState:
    """분석 결과 생성 노드.

    Timeseries insights가 필요한 경우 analysis와 병렬로 실행합니다.
    """
    # 분석 태스크 (항상 실행)
    analysis_task = analyze_search_results(
        rewritten_query=state.rewritten_query,
        user_query_language=state.user_query_language,
        search_output=state.search_output,
    )

    # Timeseries insights 필요 여부 확인
    need_timeseries = _should_generate_timeseries_insights(state)

    if need_timeseries:
        # 병렬 실행
        timeseries_task = generate_timeseries_insights(
            state.rewritten_query, state.analysis_type, state.search_output,
        )
        analysis_output, timeseries_result = await asyncio.gather(
            analysis_task, timeseries_task,
        )
        state.timeseries_insights = timeseries_result
    else:
        # 분석만 실행
        analysis_output = await analysis_task

    # 분석 결과 저장
    state.analysis_content = analysis_output.content
    state.suggested_questions = analysis_output.suggested_questions
    state.analysis_summary = analysis_output.analysis_summary

    return state
