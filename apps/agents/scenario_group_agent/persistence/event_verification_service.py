from __future__ import annotations

import asyncio
from datetime import UTC, datetime
import json
from typing import Any

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
from apps.persistence.event.schema import EventSearchSource
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


class EventVerificationService:
    """Read-only, best-effort verification of the current published Event snapshot."""

    async def verify(self, event_ids: list[int]) -> EventVerificationsOut:
        rows = await asyncio.to_thread(EventService().load_search_sources, event_ids=event_ids)
        by_id = {row.mi_event_id: row for row in rows}
        if set(by_id) != set(event_ids):
            raise MIBaseError(ErrorCode.ENTITY_NOT_FOUND, detail="선택한 Event가 없거나 게시 상태가 아닙니다.")
        checked_at = datetime.now(UTC)
        events = [by_id[event_id] for event_id in event_ids]
        try:
            provider = WebSearchProviderFactory.create_from_settings()
        except Exception:
            logger.exception("[EVENT_VERIFICATION] SEARCH_PROVIDER_INIT_FAILED")
            return EventVerificationsOut(
                checked_at=checked_at,
                items=[
                    _warning(event, "search_error", "웹 검색 서비스를 사용할 수 없어 검증하지 못했습니다.")
                    for event in events
                ],
            )
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_EVENTS)
        items = await asyncio.gather(*(self._verify_one(event, provider, checked_at, semaphore) for event in events))
        return EventVerificationsOut(checked_at=checked_at, items=list(items))

    async def _verify_one(
        self,
        event: EventSearchSource,
        provider: WebSearchProvider,
        checked_at: datetime,
        semaphore: asyncio.Semaphore,
    ) -> EventVerificationItem:
        evidence = await self._verify_evidence(event, provider, checked_at, semaphore)
        return evidence.verification

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
