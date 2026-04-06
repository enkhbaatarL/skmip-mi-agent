"""시계열 차트 프롬프트 모듈."""
from __future__ import annotations

from apps.agents.mi_agent.prompts.loader import load_prompt
from apps.agents.mi_agent.schemas.schemas import TimeSeriesInsights


def build_timeseries_chart_prompt(
    message: str,
    main_source: str,
    sub_source: str,
    source: str,
) -> str:
    """시계열 차트 인사이트 생성 프롬프트를 생성합니다."""
    schema = TimeSeriesInsights.model_json_schema()

    return load_prompt(
        "chart",
        key="timeseries",
        message=message,
        main_source=main_source,
        sub_source=sub_source,
        source=source,
        schema=schema,
    )
