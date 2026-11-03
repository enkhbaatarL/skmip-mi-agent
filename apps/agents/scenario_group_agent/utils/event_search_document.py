from __future__ import annotations

import hashlib
import json
import re

from pydantic import JsonValue

from apps.agents.scenario_group_agent.schemas.event_search_document import EventSearchDocument, EventSearchMetadata
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.schema import EventSearchSource


EVENT_SEARCH_DOCUMENT_VERSION = "event-search-v1"
DEFAULT_MAX_CONTENT_CHARS = 2400


def normalize_event_text(value: str | None) -> str:
    """Preserve Markdown, numbers, URLs and internal spacing; normalize only newlines and outer space."""
    return (value or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _json_text(value: JsonValue) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _list_text(value: JsonValue, *, field: str, wrapper: str) -> tuple[str, list[str], list[str]]:
    if value is None:
        return "", [], []
    if isinstance(value, str):
        if not value.strip():
            return "", [], []
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return normalize_event_text(value), [], [f"invalid_json:{field}"]
    else:
        parsed = value
    if isinstance(parsed, dict) and set(parsed) == {wrapper}:
        parsed = parsed[wrapper]
    if not isinstance(parsed, list):
        return _json_text(parsed), [], [f"unexpected_json_shape:{field}"]
    warnings = [] if all(isinstance(item, str) for item in parsed) else [f"non_string_items:{field}"]
    rendered = [normalize_event_text(item) if isinstance(item, str) else _json_text(item) for item in parsed]
    strings = [normalize_event_text(item) for item in parsed if isinstance(item, str) and item.strip()]
    return "\n".join(f"- {item}" for item in rendered if item), strings, warnings


def build_event_search_text(source: EventSearchSource) -> tuple[str, list[str], list[str]]:
    bullets, _, bullet_warnings = _list_text(source.key_bullets_json, field="key_bullets_json", wrapper="bullets")
    tags_text, tags, tag_warnings = _list_text(source.tags_json, field="tags_json", wrapper="tags")
    sections = (
        ("제목", source.one_line_summary),
        ("요약", source.search_text),
        ("핵심 내용", bullets),
        ("태그", tags_text),
        ("상세 분석", source.detail_analysis),
        ("정량 근거", source.numeric_facts_md),
        ("기관 전망", source.institution_view_synthesis),
    )
    text = "\n\n".join(
        f"{label}:\n{normalized}" for label, value in sections if (normalized := normalize_event_text(value))
    )
    warnings = [*bullet_warnings, *tag_warnings]
    if not normalize_event_text(source.one_line_summary):
        warnings.append("missing_title")
    if not normalize_event_text(source.detail_analysis):
        warnings.append("missing_detail_analysis")
    if not bullets:
        warnings.append("missing_key_bullets")
    if not tags_text:
        warnings.append("missing_tags")
    if source.occurred_at is None:
        warnings.append("missing_occurred_at")
    if re.search(r"가정|가상|hypothetical|test\s+event|테스트", text, re.IGNORECASE):
        warnings.append("contains_assumption_or_test_marker")
    if not text:
        warnings.append("empty_content")
    return text, tags, warnings


def _chunk_spans(text: str, max_chars: int) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            lower = start + max_chars // 2
            for separator in ("\n\n", "\n", ". ", " "):
                boundary = text.rfind(separator, lower, end)
                if boundary >= 0:
                    end = boundary + len(separator)
                    break
        spans.append((start, end))
        start = end
    return spans


def build_event_search_documents(
    source: EventSearchSource,
    *,
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
) -> list[EventSearchDocument]:
    if source.del_yn != "N" or source.publish_status != "PUBLISHED":
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="게시 완료된 활성 Event만 검색 문서로 변환할 수 있습니다.")
    if max_content_chars < 128:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="max_content_chars는 128 이상이어야 합니다.")
    text, tags, warnings = build_event_search_text(source)
    spans = _chunk_spans(text, max_content_chars)
    source_json = json.dumps(source.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_hash = hashlib.sha256(source_json.encode("utf-8")).hexdigest()
    title = normalize_event_text(source.one_line_summary)
    documents: list[EventSearchDocument] = []
    for index, (start, end) in enumerate(spans):
        content = text[start:end]
        embedding_text = f"제목: {title}\n\n{content}" if index > 0 and title else content
        documents.append(
            EventSearchDocument(
                document_id=f"event:{source.mi_event_id}:{EVENT_SEARCH_DOCUMENT_VERSION}:{max_content_chars}:{index:04d}",
                text=embedding_text,
                content=content,
                metadata=EventSearchMetadata(
                    event_id=source.mi_event_id,
                    event_type_l2_id=source.event_type_l2_id,
                    document_version=EVENT_SEARCH_DOCUMENT_VERSION,
                    source_hash=source_hash,
                    text_hash=hashlib.sha256(embedding_text.encode("utf-8")).hexdigest(),
                    title=title,
                    tags=tags,
                    occurred_at=source.occurred_at,
                    source_created_at=source.crt_dtm,
                    source_updated_at=source.mod_dtm,
                    source_record_ids=sorted(set(source.source_record_ids)),
                    chunk_index=index,
                    chunk_count=len(spans),
                    content_start=start,
                    content_end=end,
                    max_content_chars=max_content_chars,
                    warnings=warnings,
                ),
            ),
        )
    return documents
