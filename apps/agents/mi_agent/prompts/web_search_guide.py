"""웹 검색 가이드 프롬프트 모듈."""
from __future__ import annotations

from apps.agents.mi_agent.prompts.loader import load_prompt


def build_web_search_guide_prompt_block() -> str:
    """웹 검색 비활성화 안내 블록을 생성합니다."""
    return load_prompt("web_search", key="guide_disabled")
