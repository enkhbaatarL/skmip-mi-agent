from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
import json
import logging
from pathlib import Path
import re
import sys
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import SQLAlchemyError


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from apps.agents.scenario_group_agent.utils.event_search_document import (  # noqa: E402
    DEFAULT_MAX_CONTENT_CHARS,
    EVENT_SEARCH_DOCUMENT_VERSION,
    build_event_search_documents,
    build_event_search_text,
    normalize_event_text,
)
from apps.common.exceptions.custom import MIBaseError  # noqa: E402
from apps.common.values.error_codes import ErrorCode  # noqa: E402
from apps.persistence.event.schema import EventSearchSource  # noqa: E402


LOGGER = logging.getLogger("event_search_export")


def select_sample_events(sources: Sequence[EventSearchSource], limit: int) -> list[EventSearchSource]:
    """Include shortest/longest bodies and a forecast marker, then fill in repository order."""
    if not sources:
        return []
    priorities = [
        min(sources, key=lambda event: len(event.detail_analysis)),
        max(sources, key=lambda event: len(event.detail_analysis)),
    ]
    forecast = next(
        (event for event in sources if re.search(r"전망|예상|forecast|outlook", event.detail_analysis, re.IGNORECASE)),
        None,
    )
    if forecast is not None:
        priorities.append(forecast)
    chosen: dict[int, EventSearchSource] = {}
    for event in [*priorities, *sources]:
        chosen.setdefault(event.mi_event_id, event)
        if len(chosen) >= limit:
            break
    return list(chosen.values())


def _write_jsonl(path: Path, rows: Sequence[BaseModel]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(row.model_dump_json() + "\n")


def export_sample(
    sources: Sequence[EventSearchSource],
    *,
    output_dir: Path,
    max_content_chars: int = DEFAULT_MAX_CONTENT_CHARS,
    source_origin: str = "input_jsonl",
    pool_count: int | None = None,
) -> dict[str, object]:
    if not sources or len({source.mi_event_id for source in sources}) != len(sources):
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="샘플은 중복 없는 Event를 1개 이상 포함해야 합니다.")
    documents = []
    event_reports = []
    warning_counts: Counter[str] = Counter()
    scalar_fields = (
        "one_line_summary",
        "search_text",
        "detail_analysis",
        "numeric_facts_md",
        "institution_view_synthesis",
    )
    missing_fields: Counter[str] = Counter()
    for source in sources:
        canonical_text, _, warnings = build_event_search_text(source)
        chunks = build_event_search_documents(source, max_content_chars=max_content_chars)
        reconstructed = "".join(chunk.content for chunk in chunks)
        preserved_fields = all(
            normalize_event_text(getattr(source, field)) in canonical_text for field in scalar_fields
        )
        coverage_passed = (
            reconstructed == canonical_text
            and preserved_fields
            and all(
                chunk.content == canonical_text[chunk.metadata.content_start : chunk.metadata.content_end]
                and chunk.text.endswith(chunk.content)
                for chunk in chunks
            )
        )
        if not coverage_passed:
            raise MIBaseError(ErrorCode.INVALID_REQUEST, detail=f"원문 보존 검증 실패: Event {source.mi_event_id}")
        for field in scalar_fields:
            if not normalize_event_text(getattr(source, field)):
                missing_fields[field] += 1
        if source.occurred_at is None:
            missing_fields["occurred_at"] += 1
        if "missing_key_bullets" in warnings:
            missing_fields["key_bullets_json"] += 1
        if "missing_tags" in warnings:
            missing_fields["tags_json"] += 1
        warning_counts.update(warnings)
        event_reports.append(
            {
                "event_id": source.mi_event_id,
                "title": source.one_line_summary,
                "body_chars": len(source.detail_analysis),
                "canonical_chars": len(canonical_text),
                "chunk_count": len(chunks),
                "coverage_passed": coverage_passed,
                "warnings": warnings,
            },
        )
        documents.extend(chunks)
    report: dict[str, object] = {
        "document_version": EVENT_SEARCH_DOCUMENT_VERSION,
        "generated_at": datetime.now(ZoneInfo("Asia/Seoul")).isoformat(),
        "source_origin": source_origin,
        "selection_pool_count": pool_count if pool_count is not None else len(sources),
        "event_count": len(sources),
        "document_count": len(documents),
        "max_content_chars": max_content_chars,
        "coverage_passed": True,
        "missing_field_counts": dict(missing_fields),
        "warning_counts": dict(warning_counts),
        "access_scope": "internal_sample_only; end-user authorization not evaluated",
        "events": event_reports,
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(output_dir / "source_events.jsonl", sources)
    _write_jsonl(output_dir / "documents.jsonl", documents)
    (output_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    preview = [
        "# Event 검색 문서 샘플 검토",
        f"\n- Event {len(sources)}개 → 검색 문서 {len(documents)}개",
        "- 정규화된 원문 재구성 및 텍스트 필드 보존 검증: 통과",
        "- source_events.jsonl: DB 조회 원본 DTO / documents.jsonl: 임베딩 전 검색 문서",
        "- report.json: Event별 길이·누락 필드·경고·검증 결과",
        "- 가정/테스트 표식은 단순 문자열 탐지이며 사실 여부 판정이 아닙니다.",
        "\n## Event별 결과\n",
        "| Event ID | 본문 글자 수 | 문서 수 | 경고 |",
        "| --- | --- | --- | --- |",
    ]
    preview.extend(
        f"| {item['event_id']} | {item['body_chars']} | {item['chunk_count']} | {', '.join(item['warnings']) or '-'} |"
        for item in event_reports
    )
    for source in sources[:3]:
        text, _, _ = build_event_search_text(source)
        preview.extend([f"\n## Event {source.mi_event_id}\n", text])
    (output_dir / "preview.md").write_text("\n".join(preview) + "\n", encoding="utf-8")
    return report


def _load_sources(args: argparse.Namespace) -> list[EventSearchSource]:
    if args.input_jsonl:
        sources = [
            EventSearchSource.model_validate_json(line)
            for line in args.input_jsonl.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if args.event_ids:
            sources = [source for source in sources if source.mi_event_id in args.event_ids]
    else:
        load_dotenv(args.env_file, override=True)
        from apps.persistence.event.service import EventService

        sources = EventService().load_search_sources(limit=200, event_ids=args.event_ids)
    if args.event_ids and set(args.event_ids) - {source.mi_event_id for source in sources}:
        raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="요청 Event 중 조회할 수 없는 ID가 있습니다.")
    return sources


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Export published Event search documents without embeddings or DB writes.",
    )
    parser.add_argument("--env-file", type=Path, default=ROOT_DIR / "envs" / ".env")
    parser.add_argument("--input-jsonl", type=Path, help="Replay source_events.jsonl without connecting to the DB")
    parser.add_argument("--event-ids", type=int, nargs="+")
    parser.add_argument("--sample-size", type=int, default=30)
    parser.add_argument("--max-content-chars", type=int, default=DEFAULT_MAX_CONTENT_CHARS)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if not 1 <= args.sample_size <= 200 or args.max_content_chars < 128:
        parser.error("sample-size must be 1..200 and max-content-chars must be >=128")
    if args.event_ids and (
        len(set(args.event_ids)) > args.sample_size or any(event_id <= 0 for event_id in args.event_ids)
    ):
        parser.error("event-ids must be positive and fit within sample-size")
    output_dir = args.output_dir or ROOT_DIR / "local/output/event_search_documents" / datetime.now(
        ZoneInfo("Asia/Seoul"),
    ).strftime("%Y%m%d_%H%M%S_%f")
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        sources = _load_sources(args)
        report = export_sample(
            select_sample_events(sources, args.sample_size),
            output_dir=output_dir,
            max_content_chars=args.max_content_chars,
            source_origin="input_jsonl" if args.input_jsonl else "configured_mysql",
            pool_count=len(sources),
        )
    except (MIBaseError, SQLAlchemyError, ValidationError, OSError) as exc:
        # Config/DB exception tracebacks may contain credentials; report the error type only.
        LOGGER.error(  # noqa: TRY400
            "Export failed (%s). Check configuration, connection, input and output directory.",
            type(exc).__name__,
        )
        return 1
    LOGGER.info("Exported %s events / %s documents: %s", report["event_count"], report["document_count"], output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
