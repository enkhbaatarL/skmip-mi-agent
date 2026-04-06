"""테이블 선택 프롬프트 모듈."""
from __future__ import annotations

from apps.agents.mi_agent.prompts.loader import load_prompt


def build_select_table_prompt(query: str, table: str) -> str:
    """테이블 선택 프롬프트를 생성합니다."""
    data_section = f"# Table\n{table}\n```" if table else ""

    return load_prompt(
        "rdb_search",
        key="select_table",
        query=query,
        data_section=data_section,
    )
