from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import hashlib
import json
from time import perf_counter
from typing import get_args

from pydantic import JsonValue, ValidationError

from apps.agents.scenario_group_agent.persistence.event_verification_service import (
    EventVerificationService,
    VerificationEvidence,
    VerificationSource,
)
from apps.agents.scenario_group_agent.prompts.event_verification_update import (
    EVENT_UPDATE_SYSTEM_PROMPT,
    EventFieldUpdate,
    EventUpdateProposal,
)
from apps.agents.scenario_group_agent.schemas.api.event_verification_updates import (
    EventContentChange,
    EventVerificationUpdateIn,
    EventVerificationUpdateOut,
)
from apps.agents.scenario_group_agent.schemas.api.event_verifications import EventVerificationItem, VerificationAspect
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.llm.llm_client import invoke_llm_structured_output
from apps.persistence.event.schema import EventSearchSource, EventUpdateContext
from apps.persistence.event.service import EventService


def _validate_citations(change: EventFieldUpdate, sources: dict[int, VerificationSource]) -> None:
    for citation in change.evidence:
        source = sources.get(citation.source_id)
        if source is None or not citation.quote.strip() or citation.quote not in source.content:
            raise MIBaseError(
                ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                detail="수정 근거가 실제 검색 인용 문맥과 다릅니다.",
            )


def _validated_changes(
    context: EventUpdateContext,
    proposal: EventUpdateProposal,
    evidence: VerificationEvidence,
) -> tuple[dict[str, str | list[str]], list[EventContentChange]]:
    sources = {source.id: source for source in evidence.sources}
    values: dict[str, str | list[str]] = {}
    changes: list[EventContentChange] = []
    seen: set[str] = set()
    limits = {"one_line_summary": 300, "search_text": 500, "institution_view_synthesis": 1000}
    for change in proposal.changes:
        name, value = change.field, change.value
        if name not in context.content or name in seen:
            raise MIBaseError(
                ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                detail="수정 컬럼이 중복되었거나 존재하지 않습니다.",
            )
        seen.add(name)
        _validate_citations(change, sources)
        before = context.content[name]
        after: JsonValue = value
        if name == "key_bullets_json":
            if not isinstance(value, list) or not value or any(not text.strip() for text in value):
                raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail="핵심 bullet 수정 값이 잘못되었습니다.")
            if isinstance(before, dict):
                if "bullets" not in before:
                    raise MIBaseError(
                        ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                        detail="지원하지 않는 핵심 bullet 구조입니다.",
                    )
                after = {**before, "bullets": value}
        elif not isinstance(value, str) or not value.strip() or len(value) > limits.get(name, 100000):
            raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail=f"수정 값의 형식·길이 오류: {name}")
        if before == after:
            continue
        values[name] = value
        changes.append(
            EventContentChange(
                field=name,
                before=before,
                after=after,
                reason=change.reason,
                source_urls=list(dict.fromkeys(sources[item.source_id].url for item in change.evidence)),
            ),
        )
    return values, changes


def _candidate(context: EventUpdateContext, changes: list[EventContentChange]) -> EventSearchSource:
    content = {**context.content, **{change.field: change.after for change in changes}}
    data = {**context.source.model_dump(), **content}
    return EventSearchSource.model_validate(data)


def _content_hash(value: JsonValue) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def _allows_update(
    original: EventVerificationItem,
    post: EventVerificationItem,
    candidate: EventSearchSource,
) -> bool:
    if post.status == "pass":
        return True
    if post.status != "warning" or post.reason_code != "review_required":
        return False
    checks = {item.aspect: item for item in post.checks}
    if len(post.checks) != 6 or set(checks) != set(get_args(VerificationAspect)):
        return False
    freshness = checks["freshness"]
    quote = freshness.qualification_quote or ""
    if not (
        freshness.verdict == "caution"
        and freshness.caution_reason == "as_of_limitation"
        and freshness.source_urls
        and quote.strip()
        and quote in candidate.detail_analysis
    ):
        return False
    if any(item.verdict not in {"matched", "not_applicable"} for key, item in checks.items() if key != "freshness"):
        return False
    # A previously contradicted claim must be checked, not merely disappear into not_applicable.
    return all(
        checks[item.aspect].verdict == "matched"
        for item in original.checks
        if item.aspect != "freshness" and item.verdict in {"contradicted", "outdated"}
    )


def _update_reason(
    proposal: EventUpdateProposal,
    changes: list[EventContentChange],
    evidence: VerificationEvidence,
    checked_at: datetime,
    post: EventVerificationItem,
) -> str:
    """Bound TEXT audit size; full old content is in the snapshot, full diff is in the response."""
    by_field = {change.field: change for change in proposal.changes}
    first_quote = {}
    for change in proposal.changes:
        for citation in change.evidence:
            first_quote.setdefault(citation.source_id, citation.quote)
    return json.dumps(
        {
            "reason": proposal.reason[:1000],
            "checked_at": checked_at.isoformat(),
            "verification_review": evidence.verification.review,
            "post_verification_status": post.status,
            "remaining_cautions": [
                {
                    "aspect": item.aspect,
                    "reason": item.caution_reason,
                    "finding": item.finding[:500],
                    "qualification_quote": (item.qualification_quote or "")[:1000],
                }
                for item in post.checks
                if item.verdict == "caution"
            ],
            "changes": [
                {
                    "field": change.field,
                    "reason": change.reason[:500],
                    "before_hash": _content_hash(change.before),
                    "after_hash": _content_hash(change.after),
                    "source_ids": sorted({citation.source_id for citation in by_field[change.field].evidence}),
                }
                for change in changes
            ],
            "sources": [
                {
                    "id": source.id,
                    "url": source.url,
                    "quote_excerpt": first_quote[source.id][:300],
                }
                for source in evidence.sources
                if source.id in first_quote
            ],
        },
        ensure_ascii=False,
    )


class EventVerificationUpdateService:
    async def update(self, event_id: int, body: EventVerificationUpdateIn) -> EventVerificationUpdateOut:
        started = perf_counter()
        logger.info("[EVENT_VERIFICATION_UPDATE] START | event_id={}", event_id)
        try:
            response = await self._update(event_id, body)
        except Exception as exc:
            # Do not log exception text: DB/LLM errors may contain SQL parameters or Event content.
            logger.error(
                "[EVENT_VERIFICATION_UPDATE] FAILED | event_id={} | error_type={} | error_name={} | elapsed_ms={}",
                event_id,
                type(exc).__name__,
                exc.error_code.name if isinstance(exc, MIBaseError) else "UNKNOWN_ERROR",
                round((perf_counter() - started) * 1000),
            )
            raise
        post = response.post_verification
        logger.info(
            "[EVENT_VERIFICATION_UPDATE] RESULT | {}",
            json.dumps(
                {
                    "event_id": event_id,
                    "update_status": response.update_status,
                    "message": response.message,
                    "verification_status": response.verification.status,
                    "verification_reason": response.verification.reason_code,
                    "verification_checks": {item.aspect: item.verdict for item in response.verification.checks},
                    "post_verification_status": post.status if post else None,
                    "post_verification_reason": post.reason_code if post else None,
                    "post_verification_checks": {item.aspect: item.verdict for item in post.checks} if post else None,
                    "post_caution_reasons": {
                        item.aspect: item.caution_reason for item in post.checks if item.verdict == "caution"
                    }
                    if post
                    else None,
                    "snapshot_id": response.mi_event_snapshot_id,
                    "snapshot_version_no": response.snapshot_version_no,
                    "changed_fields": response.changed_fields,
                    "updated_at": response.updated_at.isoformat() if response.updated_at else None,
                    "elapsed_ms": round((perf_counter() - started) * 1000),
                },
                ensure_ascii=False,
            ),
        )
        return response

    async def _update(self, event_id: int, body: EventVerificationUpdateIn) -> EventVerificationUpdateOut:
        persistence = EventService()
        context = await asyncio.to_thread(persistence.prepare_verification_update, event_id, body.expected_updated_at)
        checked_at = datetime.now(UTC)
        verifier = EventVerificationService()
        cfg = get_settings()
        try:
            # Only external analysis is cancellable by this timeout; never timeout a transaction in a worker thread.
            async with asyncio.timeout(cfg.event_verification_update_timeout_sec):
                evidence = await verifier.verify_with_evidence(context.source, checked_at)
                response = EventVerificationUpdateOut(
                    mi_event_id=event_id,
                    checked_at=checked_at,
                    update_status="skipped",
                    message="검증 근거가 충분하지 않아 업데이트하지 않았습니다.",
                    verification=evidence.verification,
                    updated_at=context.source.mod_dtm,
                )
                if evidence.verification.status == "pass":
                    response.update_status = "unchanged"
                    response.message = "검증 결과 수정할 내용이 없습니다."
                    return response
                if evidence.verification.status != "fail" or not evidence.sources:
                    return response
                result = await invoke_llm_structured_output(
                    output_schema=EventUpdateProposal,
                    messages=[
                        {"role": "system", "content": EVENT_UPDATE_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(
                                {
                                    "as_of": checked_at.isoformat(),
                                    "content": context.content,
                                    "verification": evidence.verification.model_dump(mode="json"),
                                    "sources": [source.model_dump() for source in evidence.sources],
                                },
                                ensure_ascii=False,
                            ),
                        },
                    ],
                    temperature=0.0,
                    max_retries=0,
                    stream=cfg.llm_stream_enabled,
                    reasoning_effort=cfg.llm_reasoning_effort,
                    log_label="event_verification_update",
                )
                proposal = EventUpdateProposal.model_validate(result.result)
                values, changes = _validated_changes(context, proposal, evidence)
                if not changes:
                    response.message = "검증된 수정안을 만들지 못해 업데이트하지 않았습니다."
                    return response
                candidate = _candidate(context, changes)
                response.post_verification = await verifier.compare_evidence(
                    candidate,
                    evidence.sources,
                    checked_at,
                )
                if not _allows_update(evidence.verification, response.post_verification, candidate):
                    response.message = (
                        "수정안에 저장 허용 조건을 충족하지 못한 주의 사항이 남아 업데이트하지 않았습니다."
                        if response.post_verification.status == "warning"
                        else "수정안이 재검증을 통과하지 못해 업데이트하지 않았습니다."
                    )
                    return response
        except TimeoutError as exc:
            raise MIBaseError(ErrorCode.LLM_RESPONSE_TIMEOUT, detail="Event 검증·수정안 생성 시간 초과") from exc
        except ValidationError as exc:
            raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail="Event 수정안 형식 오류") from exc
        reason = _update_reason(proposal, changes, evidence, checked_at, response.post_verification)
        applied = await asyncio.to_thread(
            persistence.apply_verification_update,
            event_id,
            context.fingerprint,
            values,
            body.actor_usr_logn_id,
            reason,
        )
        response.update_status = "updated" if applied.changed_fields else "unchanged"
        response.message = (
            "변경 전 Snapshot 저장 후 Event를 업데이트했습니다." if applied.changed_fields else "변경 사항이 없습니다."
        )
        if applied.changed_fields and response.post_verification.status == "warning":
            response.message = (
                "변경 전 Snapshot 저장 후 확인된 오류를 수정했습니다. "
                "확인 기준 시점 이후의 최신성 주의가 남아 있습니다."
            )
        response.mi_event_snapshot_id = applied.snapshot_id
        response.snapshot_version_no = applied.snapshot_version_no
        response.previous_mi_event_snapshot_id = applied.previous_snapshot_id
        response.updated_at = applied.updated_at
        response.changed_fields = applied.changed_fields
        response.changes = [change for change in changes if change.field in applied.changed_fields]
        return response
