"""질의 리라이트 프롬프트 모듈."""
from __future__ import annotations

from dateutil.relativedelta import relativedelta

from apps.agents.mi_agent.prompts.loader import load_prompt
from apps.common.utils.time_utils import today


def build_queries_rewrite_prompt(histories: str, message: str) -> str:
    """멀티턴 대화 질의 리라이트 프롬프트를 생성합니다."""
    current_date = today()
    return load_prompt(
        "rewrite_queries",
        key="queries_rewrite",
        current_date=current_date,
        histories=histories,
        message=message,
    )


def build_queries_rewrite_prompt_with_rdb(rewrite: str) -> str:
    """RDB 검색용 질의 분리 프롬프트를 생성합니다."""
    return load_prompt(
        "rdb_queries",
        key="rewrite",
        output_example='[{"query": "...", "search_text": "..."}]',
        rewritten_query=rewrite,
    )


def build_extract_similarity_query_params_prompt(rewritten_query: str) -> str:
    """유사 패턴 검색 파라미터 추출 프롬프트를 생성합니다."""
    today_str = today()
    example_start = (
        relativedelta(months=3).__class__(months=3)
    )  # 3개월 전 예시용

    return load_prompt(
        "rewrite_queries",
        key="similarity_query_params",
        today=today_str,
        example_start_date="(3개월 전 날짜)",
        rewritten_query=rewritten_query,
    )
