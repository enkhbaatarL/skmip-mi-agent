"""Interpret Agent 출력의 표현용 서식 문법을 일반 텍스트로 정규화한다."""

from __future__ import annotations

import html
from html.parser import HTMLParser
import re


_FENCED_CODE_LINE_RE = re.compile(r"(?m)^[ \t]*(?:```+|~~~+)[^\n]*$")
_HEADING_PREFIX_RE = re.compile(r"(?m)^[ \t]{0,3}#{1,6}(?:[ \t]+|$)")
_SETEXT_HEADING_RE = re.compile(r"(?m)^[ \t]{0,3}(?:=+|-+)[ \t]*$")
_BLOCKQUOTE_PREFIX_RE = re.compile(r"(?m)^[ \t]{0,3}(?:>[ \t]*)+")
_UNORDERED_LIST_PREFIX_RE = re.compile(r"(?m)^[ \t]*[-+*][ \t]+")
_ORDERED_LIST_PREFIX_RE = re.compile(r"(?m)^[ \t]*(\d{1,9})[.)][ \t]+")
_TASK_LIST_PREFIX_RE = re.compile(r"(?im)^(•[ \t]+)\[[ x]\][ \t]+")
_INDENTED_CODE_PREFIX_RE = re.compile(r"(?m)^(?: {4,}|\t+)(?=\S)")
_HORIZONTAL_RULE_RE = re.compile(r"(?m)^[ \t]{0,3}(?:[-*_][ \t]*){3,}$")
_TABLE_SEPARATOR_RE = re.compile(
    r"(?m)^[ \t]*\|?[ \t]*:?-{3,}:?(?:[ \t]*\|[ \t]*:?-{3,}:?)+[ \t]*\|?[ \t]*$",
)
_INLINE_LINK_RE = re.compile(r"!?\[([^\]\n]*)\]\(\s*([^\n)]*?)\s*\)")
_REFERENCE_LINK_RE = re.compile(r"!?\[([^\]\n]*)\]\[([^\]\n]*)\]")
_SHORTCUT_REFERENCE_RE = re.compile(r"!?\[([^\]\n]+)\]")
_REFERENCE_DEFINITION_RE = re.compile(
    r"(?m)^[ \t]{0,3}\[([^\]\n]+)\]:[ \t]*<?([^>\s]+)>?(?:[ \t]+.*)?$",
)
_AUTOLINK_RE = re.compile(r"<((?:https?://|mailto:)[^<>\s]+)>", re.IGNORECASE)
_EMAIL_AUTOLINK_RE = re.compile(r"<([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})>", re.IGNORECASE)
_DOMAIN_ANGLE_TOKEN_RE = re.compile(r"<(JKM|TTF|HH|Base|MI[ \t]+Base)>", re.IGNORECASE)
_HTML_COMMENT_RE = re.compile(r"<!--.*?(?:-->|$)", re.DOTALL)
_HTML_LIKE_RE = re.compile(r"(?is)<\s*/?\s*[A-Za-z][^<>\n]*(?:>|$)")
_MARKDOWN_ESCAPE_RE = re.compile(r"\\([\\`*{}\[\]()#+.!_>~-])")
_SINGLE_ASTERISK_EMPHASIS_RE = re.compile(
    r"(?<![\w*])\*(?=\S)(.+?)(?<=\S)\*(?![\w*])",
    re.DOTALL,
)
_SINGLE_UNDERSCORE_EMPHASIS_RE = re.compile(
    r"(?<![\w_])_(?=\S)(.+?)(?<=\S)_(?![\w_])",
    re.DOTALL,
)
_MULTIPLE_BLANK_LINES_RE = re.compile(r"\n{3,}")

_SUPPRESSED_HTML_TAGS = frozenset({"script", "style", "template", "noscript"})
_BLOCK_HTML_TAGS = frozenset(
    {
        "address",
        "article",
        "aside",
        "blockquote",
        "dd",
        "div",
        "dl",
        "dt",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tbody",
        "td",
        "tfoot",
        "th",
        "thead",
        "tr",
        "ul",
    },
)


class _PlainTextHTMLParser(HTMLParser):
    """HTML markup을 버리고 화면에 표시할 text node만 수집한다."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.suppressed_tag: str | None = None
        self.suppressed_depth = 0

    def _append_break(self) -> None:
        if self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        normalized = tag.lower()
        if self.suppressed_depth:
            if normalized == self.suppressed_tag:
                self.suppressed_depth += 1
            return
        if normalized in _SUPPRESSED_HTML_TAGS:
            self.suppressed_tag = normalized
            self.suppressed_depth = 1
            return
        if normalized == "br" or normalized in _BLOCK_HTML_TAGS:
            self._append_break()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if self.suppressed_depth:
            if normalized == self.suppressed_tag:
                self.suppressed_depth -= 1
                if self.suppressed_depth == 0:
                    self.suppressed_tag = None
            return
        if normalized in _BLOCK_HTML_TAGS:
            self._append_break()

    def handle_data(self, data: str) -> None:
        if not self.suppressed_depth:
            self.parts.append(data)

    def handle_comment(self, data: str) -> None:
        del data

    def handle_decl(self, decl: str) -> None:
        del decl

    def unknown_decl(self, data: str) -> None:
        del data


def _decode_html_entities(value: str) -> str:
    decoded = value
    for _ in range(3):
        next_value = html.unescape(decoded)
        if next_value == decoded:
            break
        decoded = next_value
    return decoded


def _replace_reference_links(value: str) -> str:
    references = {
        match.group(1).strip().casefold(): match.group(2).strip() for match in _REFERENCE_DEFINITION_RE.finditer(value)
    }
    value = _REFERENCE_DEFINITION_RE.sub("", value)

    def replace_full(match: re.Match[str]) -> str:
        label = match.group(1).strip()
        reference = (match.group(2).strip() or label).casefold()
        target = references.get(reference)
        return f"{label} ({target})" if target else label

    value = _REFERENCE_LINK_RE.sub(replace_full, value)
    if references:
        value = _SHORTCUT_REFERENCE_RE.sub(
            lambda match: (
                f"{match.group(1).strip()} ({references[match.group(1).strip().casefold()]})"
                if match.group(1).strip().casefold() in references
                else match.group(0)
            ),
            value,
        )
    return value


def _strip_html(value: str) -> str:
    parser = _PlainTextHTMLParser()
    parser.feed(value)
    parser.close()
    parsed = "".join(parser.parts)
    # HTMLParser가 data로 돌려주는 불완전한 `<tag`도 최종 응답에는 남기지 않는다.
    return _HTML_LIKE_RE.sub("", parsed)


def find_rich_text_markers(value: str) -> list[str]:
    """플랫폼에서 서식으로 해석될 수 있는 잔여 marker 이름을 반환한다."""
    checks = (
        ("markdown_fence", _FENCED_CODE_LINE_RE),
        ("markdown_heading", _HEADING_PREFIX_RE),
        ("markdown_setext_heading", _SETEXT_HEADING_RE),
        ("markdown_blockquote", _BLOCKQUOTE_PREFIX_RE),
        ("markdown_unordered_list", _UNORDERED_LIST_PREFIX_RE),
        ("markdown_ordered_list", _ORDERED_LIST_PREFIX_RE),
        ("markdown_indented_code", _INDENTED_CODE_PREFIX_RE),
        ("markdown_horizontal_rule", _HORIZONTAL_RULE_RE),
        ("markdown_table", _TABLE_SEPARATOR_RE),
        ("markdown_link", _INLINE_LINK_RE),
        ("markdown_reference_link", _REFERENCE_LINK_RE),
        ("html_comment", _HTML_COMMENT_RE),
        ("html_tag", _HTML_LIKE_RE),
        ("markdown_emphasis", _SINGLE_ASTERISK_EMPHASIS_RE),
        ("markdown_emphasis", _SINGLE_UNDERSCORE_EMPHASIS_RE),
    )
    markers = [name for name, pattern in checks if pattern.search(value)]
    for literal, name in (
        ("**", "markdown_bold"),
        ("__", "markdown_bold"),
        ("~~", "markdown_strikethrough"),
        ("`", "markdown_inline_code"),
    ):
        if literal in value:
            markers.append(name)
    return list(dict.fromkeys(markers))


def to_plain_text(value: str) -> str:
    """Markdown/HTML 표현 서식을 제거하고 의미 있는 일반 텍스트만 보존한다."""
    normalized = _decode_html_entities(value).replace("\r\n", "\n").replace("\r", "\n")
    normalized = _MARKDOWN_ESCAPE_RE.sub(r"\1", normalized)
    normalized = _AUTOLINK_RE.sub(lambda match: match.group(1).removeprefix("mailto:"), normalized)
    normalized = _EMAIL_AUTOLINK_RE.sub(r"\1", normalized)
    normalized = _DOMAIN_ANGLE_TOKEN_RE.sub(r"\1", normalized)
    normalized = _replace_reference_links(normalized)
    normalized = _INLINE_LINK_RE.sub(
        lambda match: (
            f"{match.group(1).strip()} ({match.group(2).strip()})" if match.group(2).strip() else match.group(1).strip()
        ),
        normalized,
    )
    normalized = _HTML_COMMENT_RE.sub("", normalized)
    normalized = _strip_html(normalized)

    normalized = _FENCED_CODE_LINE_RE.sub("", normalized)
    normalized = _HEADING_PREFIX_RE.sub("", normalized)
    normalized = _BLOCKQUOTE_PREFIX_RE.sub("", normalized)
    normalized = _TABLE_SEPARATOR_RE.sub("", normalized)
    normalized = _HORIZONTAL_RULE_RE.sub("", normalized)
    normalized = _SETEXT_HEADING_RE.sub("", normalized)
    normalized = _UNORDERED_LIST_PREFIX_RE.sub("• ", normalized)
    normalized = _TASK_LIST_PREFIX_RE.sub(r"\1", normalized)
    normalized = _ORDERED_LIST_PREFIX_RE.sub(r"\1: ", normalized)
    normalized = _INDENTED_CODE_PREFIX_RE.sub("", normalized)

    # 불완전한 이중 강조 표식도 최종 응답에 남지 않게 제거한다.
    normalized = normalized.replace("**", "").replace("__", "").replace("~~", "")
    normalized = _SINGLE_ASTERISK_EMPHASIS_RE.sub(r"\1", normalized)
    normalized = _SINGLE_UNDERSCORE_EMPHASIS_RE.sub(r"\1", normalized)
    normalized = normalized.replace("`", "")

    lines: list[str] = []
    for line in normalized.split("\n"):
        stripped = line.strip() if "|" in line else line.rstrip()
        if "|" in stripped:
            stripped = " · ".join(part.strip() for part in stripped.strip("|").split("|"))
        lines.append(stripped)
    return _MULTIPLE_BLANK_LINES_RE.sub("\n\n", "\n".join(lines)).strip()
