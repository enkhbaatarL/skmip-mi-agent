from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import json
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, HttpUrl, TypeAdapter, ValidationError

from apps.agents.scenario_group_agent.prompts.event_verification import (
    EVENT_VERIFICATION_SEARCH_INSTRUCTIONS,
    EVENT_VERIFICATION_SYSTEM_PROMPT,
    EventVerificationOutput,
)
from apps.agents.scenario_group_agent.schemas.api.event_verifications import (
    EventVerificationCheck,
    EventVerificationItem,
    EventVerificationsOut,
    VerificationReason,
)
from apps.common.configs.config import get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.connectors.llm.llm_client import invoke_llm_structured_output
from apps.connectors.web.base import WebSearchProvider
from apps.connectors.web.factory import WebSearchProviderFactory
from apps.persistence.event.schema import EventSearchSource, EventVerificationRecord
from apps.persistence.event.service import EventService


MAX_SOURCES = 8
MAX_CONCURRENT_EVENTS = 3


class VerificationSource(BaseModel):
    id: int
    url: str
    title: str
    content: str


class VerificationEvidence(BaseModel):
    verification: EventVerificationItem
    sources: list[VerificationSource]


def _search_sources(response: dict[str, Any]) -> list[VerificationSource]:
    """Accept only usable HTTP(S) citations returned by the search connector."""
    sources: list[VerificationSource] = []
    seen: set[str] = set()
    for row in response.get("results") or []:
        if not isinstance(row, dict):
            continue
        url = row.get("url")
        content = row.get("content")
        if not isinstance(url, str) or not isinstance(content, str) or not content.strip():
            continue
        try:
            parsed = TypeAdapter(HttpUrl).validate_python(url)
        except ValidationError:
            continue
        if parsed.username or parsed.password:
            continue
        normalized_url = str(parsed)
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        sources.append(
            VerificationSource(
                id=len(sources) + 1,
                url=normalized_url,
                title=str(row.get("title") or "")[:500],
                content=content.strip()[:12000],
            ),
        )
        if len(sources) == MAX_SOURCES:
            break
    return sources


def _warning(
    event: EventSearchSource,
    reason: VerificationReason,
    review: str,
    sources: list[VerificationSource] | None = None,
) -> EventVerificationItem:
    return EventVerificationItem(
        mi_event_id=event.mi_event_id,
        title=event.one_line_summary,
        source_updated_at=event.mod_dtm,
        status="warning",
        reason_code=reason,
        review=review,
        links=[source.url for source in sources or []],
        checks=[],
    )


def _verified_item(
    event: EventSearchSource,
    output: EventVerificationOutput,
    sources: list[VerificationSource],
) -> EventVerificationItem:
    source_by_id = {source.id: source for source in sources}
    checks: list[EventVerificationCheck] = []
    for check in output.checks:
        if any(source_id not in source_by_id for source_id in check.source_ids) or (
            check.verdict in {"matched", "contradicted", "outdated"} and not check.source_ids
        ):
            raise MIBaseError(
                ErrorCode.LLM_INVALID_RESPONSE_ERROR,
                detail="검증 결과의 출처 ID 또는 근거가 유효하지 않습니다.",
            )
        checks.append(
            EventVerificationCheck(
                aspect=check.aspect,
                verdict=check.verdict,
                event_claim=check.event_claim,
                finding=check.finding,
                source_urls=list(dict.fromkeys(source_by_id[source_id].url for source_id in check.source_ids)),
                caution_reason=check.caution_reason,
                qualification_quote=check.qualification_quote,
            ),
        )
    verdicts = {check.verdict for check in checks}
    status = "warning"
    reason: VerificationReason = "review_required"
    if "contradicted" in verdicts:
        status, reason = "fail", "contradicted"
    elif "outdated" in verdicts:
        status, reason = "fail", "outdated"
    elif verdicts <= {"matched", "not_applicable"} and "matched" in verdicts:
        status, reason = "pass", "verified"
    return EventVerificationItem(
        mi_event_id=event.mi_event_id,
        title=event.one_line_summary,
        source_updated_at=event.mod_dtm,
        status=status,
        reason_code=reason,
        review=output.review,
        links=list(dict.fromkeys(url for check in checks for url in check.source_urls)),
        checks=checks,
    )


def public_verification_result(verification: EventVerificationItem) -> EventVerificationItem:
    """Share the API and candidate-save grade without mutating the original comparison evidence."""
    if (
        verification.status == "warning"
        and verification.reason_code == "review_required"
        and any(check.verdict == "matched" for check in verification.checks)
        and all(check.verdict not in {"contradicted", "outdated"} for check in verification.checks)
    ):
        return verification.model_copy(update={"status": "pass", "reason_code": "no_contradiction"})
    return verification


class EventVerificationService:
    """Verify the published Event and persist the exact evidence for subsequent updates."""

    async def verify(self, event_ids: list[int], actor: str) -> EventVerificationsOut:
        persistence = EventService()
        contexts = await asyncio.to_thread(persistence.prepare_verifications, event_ids)
        by_id = {context.source.mi_event_id: context for context in contexts}
        if set(by_id) != set(event_ids):
            raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="선택한 Event가 없거나 게시 상태가 아닙니다.")
        checked_at = datetime.now(UTC)
        events = [by_id[event_id].source for event_id in event_ids]
        expires_at = checked_at + timedelta(seconds=get_settings().event_verification_reuse_ttl_sec)
        try:
            provider = WebSearchProviderFactory.create_from_settings()
        except Exception:
            logger.exception("[EVENT_VERIFICATION] SEARCH_PROVIDER_INIT_FAILED")
            evidence_items = [
                VerificationEvidence(
                    verification=_warning(
                        event,
                        "search_error",
                        "웹 검색 서비스를 사용할 수 없어 검증하지 못했습니다.",
                    ),
                    sources=[],
                )
                for event in events
            ]
        else:
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_EVENTS)
            evidence_items = await asyncio.gather(
                *(self._verify_evidence(event, provider, checked_at, semaphore) for event in events),
            )
        records = [
            EventVerificationRecord(
                mi_event_verification_id=str(uuid4()),
                mi_event_id=event.mi_event_id,
                event_fingerprint=by_id[event.mi_event_id].fingerprint,
                verification_result_json=evidence.verification.model_dump(mode="json"),
                search_evidence_json=[source.model_dump(mode="json") for source in evidence.sources],
                checked_at=checked_at,
                expires_at=expires_at,
            )
            for event, evidence in zip(events, evidence_items, strict=True)
        ]
        await asyncio.to_thread(persistence.store_verifications, records, actor)
        items = []
        for record, evidence in zip(records, evidence_items, strict=True):
            item = public_verification_result(evidence.verification).model_copy(
                update={
                    "verification_id": UUID(record.mi_event_verification_id),
                    "expires_at": expires_at,
                },
            )
            items.append(item)
        return EventVerificationsOut(checked_at=checked_at, items=items)

    async def _verify_one(
        self,
        event: EventSearchSource,
        provider: WebSearchProvider,
        checked_at: datetime,
        semaphore: asyncio.Semaphore,
    ) -> EventVerificationItem:
        evidence = await self._verify_evidence(event, provider, checked_at, semaphore)
        return public_verification_result(evidence.verification)

    async def verify_with_evidence(self, event: EventSearchSource, checked_at: datetime) -> VerificationEvidence:
        """Keep server-owned citations for a subsequent update; never accept client-supplied verdicts."""
        try:
            provider = WebSearchProviderFactory.create_from_settings()
        except ValueError as exc:
            raise MIBaseError(ErrorCode.LLM_INVOCATION_ERROR, detail="웹 검색 provider 초기화 실패") from exc
        return await self._verify_evidence(event, provider, checked_at, asyncio.Semaphore(1))

    async def compare_evidence(
        self,
        event: EventSearchSource,
        sources: list[VerificationSource],
        checked_at: datetime,
    ) -> EventVerificationItem:
        cfg = get_settings()
        result = await invoke_llm_structured_output(
            output_schema=EventVerificationOutput,
            messages=[
                {"role": "system", "content": EVENT_VERIFICATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "as_of": checked_at.isoformat(),
                            "event": event.model_dump(mode="json", exclude={"publish_status", "del_yn"}),
                            "sources": [source.model_dump() for source in sources],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=0.0,
            max_retries=0,
            stream=cfg.llm_stream_enabled,
            reasoning_effort=cfg.llm_reasoning_effort,
            log_label="event_verification",
        )
        output = EventVerificationOutput.model_validate(result.result)
        return _verified_item(event, output, sources)

    async def _verify_evidence(
        self,
        event: EventSearchSource,
        provider: WebSearchProvider,
        checked_at: datetime,
        semaphore: asyncio.Semaphore,
    ) -> VerificationEvidence:
        cfg = get_settings()
        sources: list[VerificationSource] = []
        stage = "search"
        # Includes queue time, retries and both external calls; all items share a bounded request lifetime.
        try:
            async with asyncio.timeout(cfg.event_verification_timeout_sec), semaphore:
                payload = event.model_dump(mode="json", exclude={"publish_status", "del_yn"})
                context = json.dumps({"as_of": checked_at.isoformat(), "event": payload}, ensure_ascii=False)
                response = await provider.search(
                    query=f"{event.one_line_summary}: 사건 사실 확인 및 최신 후속 뉴스·정정·변경 검색",
                    end_date=checked_at.date().isoformat(),
                    context=context,
                    instructions=EVENT_VERIFICATION_SEARCH_INSTRUCTIONS,
                    max_results=MAX_SOURCES,
                    tool_choice="required",
                )
                if response.get("status") not in {None, "completed"}:
                    return VerificationEvidence(
                        verification=_warning(event, "search_error", "웹 검색이 완료되지 않아 검증하지 못했습니다."),
                        sources=[],
                    )
                sources = _search_sources(response)
                if not sources:
                    return VerificationEvidence(
                        verification=_warning(
                            event,
                            "no_evidence",
                            "비교 가능한 웹 근거를 찾지 못해 사실과 최신성을 확인할 수 없습니다.",
                        ),
                        sources=[],
                    )
                stage = "verification"
                return VerificationEvidence(
                    verification=await self.compare_evidence(event, sources, checked_at),
                    sources=sources,
                )
        except Exception:
            # External failures are inconclusive, never evidence that the Event is false.
            # CancelledError is intentionally not caught so disconnect/shutdown can cancel work.
            logger.exception("[EVENT_VERIFICATION] ITEM_FAILED | event_id={} | stage={}", event.mi_event_id, stage)
            if stage == "search":
                return VerificationEvidence(
                    verification=_warning(event, "search_error", "웹 검색 오류 또는 시간 초과로 검증하지 못했습니다."),
                    sources=[],
                )
            return VerificationEvidence(
                verification=_warning(
                    event,
                    "verification_error",
                    "검색 근거의 비교 검증을 완료하지 못해 재검증이 필요합니다.",
                    sources,
                ),
                sources=sources,
            )
