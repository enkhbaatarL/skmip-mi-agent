from __future__ import annotations

from collections.abc import Iterable


def merge_and_dedupe(*sources: Iterable[dict]) -> list[dict]:
    out: list[dict] = []
    for stream in sources:
        if not stream:
            continue
        for item in stream:
            if isinstance(item, dict):
                out.append(item)
    return out
