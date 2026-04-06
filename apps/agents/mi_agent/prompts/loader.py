"""프롬프트 템플릿 로더.

YAML 파일에서 프롬프트 템플릿을 로드하고 변수를 치환합니다.
"""
from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Any

import yaml


_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_yaml(name: str) -> dict[str, Any]:
    """YAML 파일을 로드합니다."""
    path = _TEMPLATES_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_prompt(
    name: str,
    key: str | None = None,
    **kwargs: Any,
) -> str:
    """YAML에서 프롬프트를 로드하고 변수를 치환합니다.

    Args:
        name: YAML 파일명 (확장자 제외)
        key: YAML 내 특정 키 (None이면 전체 content 사용)
        **kwargs: Template 치환 변수

    Returns:
        변수가 치환된 프롬프트 문자열
    """
    data = _load_yaml(name)

    if key:
        template_str = data.get(key, "")
    else:
        template_str = data.get("content", "") or data.get("template", "")

    if not template_str:
        raise ValueError(f"No template found in {name}.yaml for key={key}")

    if kwargs:
        return Template(template_str).safe_substitute(**kwargs)
    return template_str


def load_prompt_parts(name: str) -> dict[str, str]:
    """YAML에서 모든 프롬프트 파트를 로드합니다.

    Args:
        name: YAML 파일명 (확장자 제외)

    Returns:
        프롬프트 파트 딕셔너리
    """
    return _load_yaml(name)
