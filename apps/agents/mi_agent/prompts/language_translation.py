"""언어 번역 프롬프트 모듈."""
from __future__ import annotations

from apps.agents.mi_agent.prompts.loader import load_prompt


def build_language_translation_prompt_block(target_lang: str | None) -> str:
    """언어 출력 지침 블록을 생성합니다."""
    t = target_lang or "ko"
    if t.lower() == "und":
        t = "ko"
    return load_prompt("language", key="translation_block", target_lang=t)


def build_query_langguage_out_prompt(target_lang: str, answer: str) -> str:
    """전체 번역 프롬프트를 생성합니다."""
    return load_prompt(
        "language",
        key="translation_full",
        target_lang=target_lang,
        answer=answer,
    )
