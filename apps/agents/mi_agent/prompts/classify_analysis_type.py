"""분석 유형 분류 프롬프트 모듈."""
from __future__ import annotations

from apps.agents.mi_agent.prompts.loader import load_prompt
from apps.common.values.enums import AnalysisType


def build_classify_analysis_type_prompt(rewritten_query: str) -> str:
    """분석 유형 분류 프롬프트를 생성합니다."""
    allowed_types = "\n".join(f"- {t.value}" for t in AnalysisType)

    return load_prompt(
        "classify",
        key="analysis_type",
        general_request=AnalysisType.GENERAL_REQUEST.value,
        single_metric=AnalysisType.SINGLE_METRIC.value,
        timeseries_trend=AnalysisType.TIMESERIES_TREND.value,
        item_comparison=AnalysisType.ITEM_COMPARISON.value,
        similarity_pattern=AnalysisType.SIMILARITY_PATTERN.value,
        market_impact=AnalysisType.MARKET_IMPACT.value,
        event_impact=AnalysisType.EVENT_IMPACT.value,
        allowed_types=allowed_types,
        rewritten_query=rewritten_query,
    )
