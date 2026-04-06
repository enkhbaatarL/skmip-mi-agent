"""VDB 검색 질의 분리 프롬프트 모듈."""
from __future__ import annotations

from apps.agents.mi_agent.prompts.loader import load_prompt


def build_vdb_search_queries_prompt(rewritten_query: str, output_example: str) -> str:
    """VDB 검색용 질의 분리 프롬프트를 생성합니다."""
    return load_prompt(
        "vdb_queries",
        key="rewrite",
        output_example=output_example,
        rewritten_query=rewritten_query,
    )


def build_omdia_vdb_search_queries_prompt(rewritten_query: str, output_example: str) -> str:
    """Omdia 전용 VDB 검색 메타데이터 추출 프롬프트를 생성합니다."""
    return load_prompt(
        "vdb_queries",
        key="omdia_rewrite",
        output_example=output_example,
        rewritten_query=rewritten_query,
    )
