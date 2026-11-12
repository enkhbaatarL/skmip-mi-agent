from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import json
from time import perf_counter
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
from apps.agents.scenario_group_agent.utils.execution_log import (
    execution_event,
    logged_run,
    traced_call,
    traced_llm_call,
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

    @logged_run("event_verification")
    async def verify(self, event_ids: list[int], actor: str) -> EventVerificationsOut:
        execution_event(
            "workflow",
            "Event별 웹 검색 → 6개 기준 비교 → 판정·근거 저장 순서로 진행합니다.",
            status="started",
            planningMode="fixed_workflow",
            eventIds=event_ids,
            maxConcurrentEvents=MAX_CONCURRENT_EVENTS,
        )
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
            execution_event("search", "검색 서비스를 초기화하지 못해 검증 불가로 처리합니다.", status="warning")
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
            comparison_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EVENTS)
            evidence_items = await asyncio.gather(
                *(
                    self._verify_evidence(event, provider, checked_at, semaphore, comparison_semaphore)
                    for event in events
                ),
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
        execution_event(
            "outcome",
            "검증 결과와 재사용할 검색 근거를 저장했습니다.",
            results=[
                {
                    "eventId": item.mi_event_id,
                    "verificationId": str(item.verification_id),
                    "status": item.status,
                    "reason": item.reason_code,
                }
                for item in items
            ],
        )
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
        execution_event(
            "comparison",
            "대상·지역·시점·수치·최신성·출처 귀속을 검색 근거와 비교합니다.",
            status="started",
            eventId=event.mi_event_id,
            sourceUrls=[source.url for source in sources],
        )
        cfg = get_settings()
        result = await traced_llm_call(
            invoke_llm_structured_output,
            output_schema=EventVerificationOutput,
            call_name=f"event_verification:event:{event.mi_event_id}",
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
        verified = _verified_item(event, output, sources)
        public = public_verification_result(verified)
        execution_event(
            "verification",
            verified.review,
            eventId=event.mi_event_id,
            rawStatus=verified.status,
            statusForDisplay=public.status,
            reason=public.reason_code,
            checks=[check.model_dump(mode="json", by_alias=True) for check in verified.checks],
        )
        return verified

    async def _verify_evidence(
        self,
        event: EventSearchSource,
        provider: WebSearchProvider,
        checked_at: datetime,
        semaphore: asyncio.Semaphore,
        comparison_semaphore: asyncio.Semaphore | None = None,
    ) -> VerificationEvidence:
        cfg = get_settings()
        sources: list[VerificationSource] = []
        stage = "search"
        started = perf_counter()
        # Includes queue time, retries and both external calls; all items share a bounded request lifetime.
        try:
            async with asyncio.timeout(cfg.event_verification_timeout_sec):
                payload = event.model_dump(mode="json", exclude={"publish_status", "del_yn"})
                context = json.dumps({"as_of": checked_at.isoformat(), "event": payload}, ensure_ascii=False)
                async with semaphore:
                    search_started = perf_counter()
                    logger.info(
                        "[EVENT_VERIFICATION] TIMING | event_id={} | stage=search_queue | elapsed_ms={}",
                        event.mi_event_id,
                        round((search_started - started) * 1000),
                    )
                    execution_event(
                        "search",
                        "사건 확인과 후속 변경·정정 근거를 검색합니다.",
                        status="started",
                        eventId=event.mi_event_id,
                        asOf=checked_at.isoformat(),
                    )
                    response = await traced_call(
                        "tool",
                        f"web_search:event:{event.mi_event_id}",
                        provider.search,
                        query=f"{event.one_line_summary}: 사건 사실 확인 및 최신 후속 뉴스·정정·변경 검색",
                        end_date=checked_at.date().isoformat(),
                        context=context,
                        instructions=EVENT_VERIFICATION_SEARCH_INSTRUCTIONS,
                        max_results=MAX_SOURCES,
                        tool_choice="required",
                    )
                    logger.info(
                        "[EVENT_VERIFICATION] TIMING | event_id={} | stage=search | elapsed_ms={}",
                        event.mi_event_id,
                        round((perf_counter() - search_started) * 1000),
                    )
                if response.get("status") not in {None, "completed"}:
                    execution_event(
                        "search",
                        "검색이 완료되지 않아 사실 여부를 판단하지 않습니다.",
                        status="warning",
                        eventId=event.mi_event_id,
                    )
                    return VerificationEvidence(
                        verification=_warning(event, "search_error", "웹 검색이 완료되지 않아 검증하지 못했습니다."),
                        sources=[],
                    )
                sources = _search_sources(response)
                execution_event(
                    "evidence",
                    "비교 가능한 검색 근거를 정리했습니다.",
                    eventId=event.mi_event_id,
                    sourceCount=len(sources),
                    sourceUrls=[source.url for source in sources],
                )
                if not sources:
                    execution_event(
                        "verification",
                        "비교 가능한 근거가 없어 검증 불가로 처리합니다.",
                        status="warning",
                        eventId=event.mi_event_id,
                    )
                    return VerificationEvidence(
                        verification=_warning(
                            event,
                            "no_evidence",
                            "비교 가능한 웹 근거를 찾지 못해 사실과 최신성을 확인할 수 없습니다.",
                        ),
                        sources=[],
                    )
                stage = "verification"
                queued_at = perf_counter()
                async with comparison_semaphore or semaphore:
                    comparison_started = perf_counter()
                    logger.info(
                        "[EVENT_VERIFICATION] TIMING | event_id={} | stage=comparison_queue | elapsed_ms={}",
                        event.mi_event_id,
                        round((comparison_started - queued_at) * 1000),
                    )
                    verification = await self.compare_evidence(event, sources, checked_at)
                    logger.info(
                        "[EVENT_VERIFICATION] TIMING | event_id={} | stage=comparison | elapsed_ms={}",
                        event.mi_event_id,
                        round((perf_counter() - comparison_started) * 1000),
                    )
                    return VerificationEvidence(verification=verification, sources=sources)
        except Exception:
            # External failures are inconclusive, never evidence that the Event is false.
            # CancelledError is intentionally not caught so disconnect/shutdown can cancel work.
            execution_event(
                "verification",
                "외부 호출 실패로 검증을 완료하지 못했습니다. 사실이 거짓이라는 의미는 아닙니다.",
                status="warning",
                eventId=event.mi_event_id,
                failedStage=stage,
            )
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
        finally:
            logger.info(
                "[EVENT_VERIFICATION] TIMING | event_id={} | stage=total | last_stage={} | elapsed_ms={}",
                event.mi_event_id,
                stage,
                round((perf_counter() - started) * 1000),
            )
