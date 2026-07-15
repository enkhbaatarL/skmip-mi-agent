from __future__ import annotations

import re


_ESCAPED_LINE_BREAK_PATTERN = re.compile(r"\\r\\n|\\n|\\r")


def normalize_yaml_text(yaml_text: str) -> str:
    """Normalize real line breaks and single-line escaped YAML blobs."""
    normalized = yaml_text.replace("\r\n", "\n").replace("\r", "\n")
    if "\n" not in normalized.strip():
        # A single-line escaped blob means its YAML line breaks were stored as text.
        normalized = _ESCAPED_LINE_BREAK_PATTERN.sub("\n", normalized)
    return normalized
