"""LLM 출력에서 Markdown/HTML 서식을 제거해 일반 텍스트로 정규화한다.

TODO: interpret_agent/utils/plain_text.py 와 동일 로직이면 apps/common 으로 승격해
      중복을 없앤다.
"""

from __future__ import annotations


def to_plain_text(value: str) -> str:
    raise NotImplementedError("plain text 정규화 구현 필요")
