"""유사 패턴 차트 프롬프트 모듈."""
from __future__ import annotations

from apps.agents.mi_agent.prompts.loader import load_prompt
from apps.agents.mi_agent.schemas.schemas import TimeSeriesInsights


def build_similarity_chart_prompt(
    message: str,
    current_data: dict,
    historical_data: list,
) -> str:
    """유사 패턴 차트 인사이트 생성 프롬프트를 생성합니다."""
    schema = TimeSeriesInsights.model_json_schema()

    return load_prompt(
        "chart",
        key="similarity",
        message=message,
        current_data=current_data,
        historical_data=historical_data,
        schema=schema,
    )
