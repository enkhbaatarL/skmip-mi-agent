"""Interpret Agent 출력의 표현용 서식 문법을 일반 텍스트로 정규화한다."""

from __future__ import annotations

import html
import re


_FENCED_CODE_LINE_RE = re.compile(r"(?m)^[ \t]*(?:```+|~~~+)[^\n]*$")
_HEADING_PREFIX_RE = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+")
_BLOCKQUOTE_PREFIX_RE = re.compile(r"(?m)^[ \t]{0,3}>[ \t]?")
_UNORDERED_LIST_PREFIX_RE = re.compile(r"(?m)^[ \t]{0,3}[-+*][ \t]+")
_ORDERED_LIST_PREFIX_RE = re.compile(r"(?m)^[ \t]{0,3}(\d{1,3})\.[ \t]+")
_INDENTED_CODE_PREFIX_RE = re.compile(r"(?m)^(?: {4,}|\t+)(?=\S)")
_HORIZONTAL_RULE_RE = re.compile(r"(?m)^[ \t]{0,3}(?:[-*_][ \t]*){3,}$")
_MARKDOWN_LINK_RE = re.compile(r"!?\[([^\]\n]+)\]\(([^)\n]+)\)")
_HTML_BREAK_RE = re.compile(r"(?i)<br\s*/?>")
_HTML_BLOCK_END_RE = re.compile(r"(?i)</(?:p|div|li|h[1-6])\s*>")
_HTML_TAG_RE = re.compile(
    r"<(/?)([A-Za-z][A-Za-z0-9-]*)(?:\s+[^<>\n]*?)?\s*/?>",
)
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_SINGLE_ASTERISK_EMPHASIS_RE = re.compile(
    r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])",
    re.DOTALL,
)
_SINGLE_UNDERSCORE_EMPHASIS_RE = re.compile(
    r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])",
    re.DOTALL,
)
_KNOWN_HTML_TAGS = frozenset(
    {
        "a",
        "b",
        "blockquote",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "i",
        "li",
        "mark",
        "ol",
        "p",
        "pre",
        "script",
        "span",
        "strong",
        "style",
        "u",
        "ul",
    },
)


def _replace_html_tag(match: re.Match[str]) -> str:
    """알려진 HTML 태그는 제거하고, `<JKM>` 같은 도메인 토큰의 이름은 보존한다."""
    closing, tag_name = match.groups()
    if closing or tag_name.lower() in _KNOWN_HTML_TAGS:
        return ""
    return tag_name


def to_plain_text(value: str) -> str:
    """LLM이 덧붙인 Markdown/HTML 표현 서식을 제거하고 의미 있는 본문을 보존한다."""
    normalized = html.unescape(value).replace("\r\n", "\n").replace("\r", "\n")
    normalized = _MARKDOWN_LINK_RE.sub(r"\1 (\2)", normalized)
    normalized = _HTML_BREAK_RE.sub("\n", normalized)
    normalized = _HTML_BLOCK_END_RE.sub("\n", normalized)
    normalized = _HTML_COMMENT_RE.sub("", normalized)
    normalized = _HTML_TAG_RE.sub(_replace_html_tag, normalized)
    normalized = _FENCED_CODE_LINE_RE.sub("", normalized)
    normalized = _HEADING_PREFIX_RE.sub("", normalized)
    normalized = _BLOCKQUOTE_PREFIX_RE.sub("", normalized)
    normalized = _HORIZONTAL_RULE_RE.sub("", normalized)
    normalized = _UNORDERED_LIST_PREFIX_RE.sub("• ", normalized)
    normalized = _ORDERED_LIST_PREFIX_RE.sub(r"\1) ", normalized)
    normalized = _INDENTED_CODE_PREFIX_RE.sub("", normalized)

    # 불완전한 강조 표식도 최종 응답에 남지 않게 이중 표식은 모두 제거한다.
    normalized = normalized.replace("**", "").replace("__", "").replace("~~", "")
    normalized = _SINGLE_ASTERISK_EMPHASIS_RE.sub(r"\1", normalized)
    normalized = _SINGLE_UNDERSCORE_EMPHASIS_RE.sub(r"\1", normalized)
    normalized = normalized.replace("`", "")

    return "\n".join(line.rstrip() for line in normalized.split("\n")).strip()
