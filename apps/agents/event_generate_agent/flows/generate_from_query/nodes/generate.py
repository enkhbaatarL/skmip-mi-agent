"""근거 → 이벤트 초안 생성 뒷단 노드."""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from apps.agents.event_generate_agent.constants import (
    FALLBACK_EVENT_TYPE_L2_ID,
    LIGHT_REASONING_EFFORT,
    MAX_EVENT_DRAFTS,
    MAX_EVIDENCE_ITEMS,
)
from apps.agents.event_generate_agent.flows.generate_from_query.api_schema import (
    GeneratedEventEvidenceOut,
    GeneratedFromQueryEventOut,
    GenerateFromQueryMetaOut,
    GenerateFromQueryResult,
)
from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    EvidenceItem,
    EvidenceOrigin,
    SearchRoute,
)
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.flows.generate_from_query.tools.event_type_catalog import (
    load_event_type_catalog,
)
from apps.agents.event_generate_agent.flows.generate_from_query.tools.evidence import (
    UNKNOWN_EVENT_SOURCE_NAME,
    group_prompt_evidences,
    known_links,
)
from apps.agents.event_generate_agent.prompts import (
    event_draft as draft_prompt,
    event_type_classification as type_prompt,
    existing_event_edit as edit_prompt,
)
from apps.agents.event_generate_agent.schemas.domain import (
    DraftEvidenceUsage,
    EventClaim,
    EventDraft,
    EventTypeAssignment,
    EventTypeCatalogItem,
    ExistingEventOperation,
    IssueSeverity,
)
from apps.common.configs.config import get_settings
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.common.utils.time_utils import today as today_str
from apps.common.values.enums import ModelPreference


_MIN_MERGE_SOURCES = 2


def _normalize_title(title: str) -> str:
    return " ".join(title.split()).casefold()


def _to_evidence_usages(
    refs: list[draft_prompt.EvidenceRefLLMItem],
    evidences: list[EvidenceItem],
) -> list[DraftEvidenceUsage]:
    """LLM이 밝힌 근거 참조를 실제 입력 근거와 짝지어 남긴다(같은 근거는 첫 항목 유지).

    key 로 먼저 찾고, key 가 틀렸으면 제목 일치로 한 번 더 찾는다. 둘 다 실패하면
    응답에서 원본 제목/URL을 채울 수 없으므로 버린다.
    """
    key_set = {evidence.evidence_key for evidence in evidences}
    key_by_title = {_normalize_title(evidence.title): evidence.evidence_key for evidence in evidences if evidence.title}

    usages: list[DraftEvidenceUsage] = []
    seen: set[str] = set()
    for ref in refs:
        key = ref.evidence_key.strip().strip("[]")
        if key not in key_set:
            key = key_by_title.get(_normalize_title(ref.evidence_title), "")
        if not key:
            logger.warning(
                f"[NODE][draft_events] UNKNOWN_EVIDENCE | key={ref.evidence_key!r} | title={ref.evidence_title!r}",
            )
            continue
        if key in seen:
            continue
        seen.add(key)
        usages.append(
            DraftEvidenceUsage(
                evidence_key=key,
                referenced_content=ref.referenced_content.strip(),
                usage=ref.usage.strip(),
            ),
        )
    return usages


def _to_source_event_ids(item: edit_prompt.ExistingEventEditLLMItem, evidences: list[EvidenceItem]) -> list[int]:
    """LLM 이 밝힌 원본 이벤트 ID 중 실제 입력 근거에 있는 것만 남긴다(순서 유지, 중복 제거)."""
    known_ids = {evidence.ref_id for evidence in evidences if evidence.ref_id is not None}
    source_ids: list[int] = []
    for mi_event_id in item.source_mi_event_ids:
        if mi_event_id not in known_ids:
            logger.warning(f"[NODE][draft_events] UNKNOWN_SOURCE_EVENT | mi_event_id={mi_event_id}")
            continue
        if mi_event_id not in source_ids:
            source_ids.append(mi_event_id)

    # modify 는 원본 1건, merge 는 원본 2건 이상이어야 한다. 어긋나도 초안은 살리고 로그로만 남긴다.
    if item.operation is ExistingEventOperation.MODIFY:
        count_ok = len(source_ids) == 1
    else:
        count_ok = len(source_ids) >= _MIN_MERGE_SOURCES
    if not count_ok:
        logger.warning(
            f"[NODE][draft_events] SOURCE_COUNT_MISMATCH | operation={item.operation.value} | source_ids={source_ids}",
        )
    return source_ids


def _to_claims(
    items: list[draft_prompt.DraftClaimLLMItem],
    evidences: list[EvidenceItem],
    state: GenerateFromQueryState,
) -> list[EventClaim]:
    """LLM 이 밝힌 claim 을 옮긴다. 입력에 없는 근거 키·사실 ID는 버리고, claim_id 가 겹치면 다시 매긴다.

    support 는 비워 둔다(미검증). 근거 지지 판정은 validate_claims 가 한다.
    """
    known_keys = {evidence.evidence_key for evidence in evidences}
    known_facts = {fact.fact_id for brief in state.topic_briefs for fact in brief.facts}
    claims: list[EventClaim] = []
    seen: set[str] = set()
    for item in items:
        text = item.text.strip()
        if not text:
            continue
        claim_id = item.claim_id.strip() or f"C{len(claims) + 1}"
        if claim_id in seen:
            claim_id = f"C{len(claims) + 1}-{len(seen)}"
        seen.add(claim_id)
        claims.append(
            EventClaim(
                claim_id=claim_id,
                text=text,
                claim_type=item.claim_type,
                evidence=known_links(item.evidence, known_keys),
                fact_ids=[fact_id for fact_id in item.fact_ids if fact_id in known_facts],
                shock_cluster=item.shock_cluster.strip(),
            ),
        )
    return claims


def _to_draft(
    item: draft_prompt.EventDraftLLMItem,
    evidences: list[EvidenceItem],
    state: GenerateFromQueryState,
) -> EventDraft:
    """LLM 산출물 1건을 EventDraft 로 옮긴다.

    generation_rationale / evidence_usages 는 응답 설명용이며 저장 대상이 아니다.
    기존 이벤트 편집 산출물이면 편집 방식과 원본 이벤트 ID 를 함께 옮긴다.
    """
    is_edit = isinstance(item, edit_prompt.ExistingEventEditLLMItem)
    return EventDraft(
        one_line_summary=item.one_line_summary.strip(),
        detail_analysis=item.detail_analysis.strip(),
        key_bullets=[bullet.strip() for bullet in item.key_bullets if bullet.strip()],
        tags=[tag.strip() for tag in item.tags if tag.strip()],
        occurred_at=item.occurred_at.strip(),
        generation_rationale=item.generation_rationale.strip(),
        evidence_usages=_to_evidence_usages(item.evidence_refs, evidences),
        operation=item.operation if is_edit else None,
        source_mi_event_ids=_to_source_event_ids(item, evidences) if is_edit else [],
        claims=_to_claims(item.claims, evidences, state),
        scenario_severity=item.scenario_severity,
    )


def _uses_existing_event_edit(state: GenerateFromQueryState) -> bool:
    """기존 이벤트 편집(병합·수치 수정) 프롬프트를 쓸지 정한다.

    classify_route 가 처음부터 existing_event 를 골랐고 모든 토픽이 그 분기에서 관련 근거를 얻은 경우만 해당한다.
    한 토픽이라도 웹으로 폴백했다면 원본 이벤트만으로 편집할 수 없으므로 새 이벤트 생성 프롬프트를 쓴다.
    """
    return (
        state.route is SearchRoute.EXISTING_EVENT
        and not state.fallback_used
        and any(evidence.origin is EvidenceOrigin.EXISTING_EVENT for evidence in state.evidences)
    )


def _to_evidence_out(
    usages: list[DraftEvidenceUsage],
    evidences: list[EvidenceItem],
) -> list[GeneratedEventEvidenceOut]:
    """초안의 근거 키를 state 의 EvidenceItem 과 짝지어 응답용 근거 목록을 만든다.

    제목/URL/ID 는 LLM 출력이 아닌 수집 단계의 원본 값을 쓴다.
    """
    evidence_by_key = {evidence.evidence_key: evidence for evidence in evidences}
    outs: list[GeneratedEventEvidenceOut] = []
    for usage in usages:
        evidence = evidence_by_key.get(usage.evidence_key)
        if evidence is None:
            continue
        outs.append(
            GeneratedEventEvidenceOut(
                evidence_key=evidence.evidence_key,
                origin=evidence.origin.value,
                title=evidence.title,
                source_name=evidence.source_name,
                published_at=evidence.published_at,
                url=evidence.url,
                provider=evidence.provider,
                ref_id=evidence.ref_id,
                referenced_content=usage.referenced_content,
                usage=usage.usage,
            ),
        )
    return outs


@log_node
async def draft_events(
    state: GenerateFromQueryState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, Any]:
    """사용자 요청과 토픽별 근거 정리(TopicBrief + 관련 근거)를 묶어 이벤트 초안을 생성한다.

    existing_event 분기는 기존 이벤트의 병합·수치 수정 프롬프트를, 그 외 분기는
    새 이벤트(가상 시나리오 포함) 생성 프롬프트를 쓴다.
    validate_claims 가 재작성을 예약했으면(pending_revision) 이전 초안과 검증 이슈를 함께 넣어 다시 쓴다.
    """
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    cfg = get_settings()
    is_edit = _uses_existing_event_edit(state)
    groups = group_prompt_evidences(state.topic_briefs, state.evidences, max_total=MAX_EVIDENCE_ITEMS)
    # 프롬프트에 실제로 넣은 근거(토픽별 관련 근거, 상한 적용 후)만 참조 대상으로 인정한다.
    prompt_evidences = [evidence for group in groups for evidence in group.evidences]
    revision = ""
    if state.pending_revision and state.validation is not None:
        revision = draft_prompt.format_revision(state.draft, state.validation.issues)
    output_schema: type[draft_prompt.EventDraftLLMOutput] | type[edit_prompt.ExistingEventEditLLMOutput]
    if is_edit:
        output_schema = edit_prompt.ExistingEventEditLLMOutput
        messages = edit_prompt.build_messages(
            state.user_query,
            groups,
            today=today_str(),
            language=state.language,
            max_events=MAX_EVENT_DRAFTS,
            fact_timeline=state.fact_timeline,
            revision=revision,
        )
    else:
        output_schema = draft_prompt.EventDraftLLMOutput
        messages = draft_prompt.build_messages(
            state.user_query,
            groups,
            today=today_str(),
            language=state.language,
            max_events=MAX_EVENT_DRAFTS,
            impact_chain=state.query_plan.impact_chain if state.query_plan else None,
            fact_timeline=state.fact_timeline,
            revision=revision,
        )

    try:
        result = await invoke_llm_structured_output(
            output_schema=output_schema,
            messages=messages,
            preference=ModelPreference.QUALITY,
            temperature=0.0,
            trace_context=runtime.context if runtime is not None else None,
            stream=cfg.llm_stream_enabled,
            reasoning_effort=cfg.llm_reasoning_effort,
        )
    except Exception as exc:
        # 외부 의존(LLM) 실패로 수집한 근거까지 잃지 않도록 경고로만 남긴다.
        logger.exception(f"[NODE][draft_events] FAILED | evidences={len(state.evidences)} | revision={bool(revision)}")
        if revision:
            # 재작성 실패면 이전 초안을 유지한다. 재검증에서 남은 error 로 저장이 막힌다.
            return {"warnings": [f"검증 이슈를 반영한 초안 재작성에 실패했습니다: {exc!r}"]}
        return {"draft": None, "warnings": [f"이벤트 초안 생성에 실패했습니다: {exc!r}"]}

    # 한 줄 요약이 비면 뒷단이 쓸 수 없는 껍데기라 여기서 버린다. 출력이 여러 건이어도 첫 건만 쓴다.
    items = [item for item in result.result.events if item.one_line_summary.strip()]
    draft = _to_draft(items[0], prompt_evidences, state) if items else None

    logger.info(
        f"[NODE][draft_events] DONE | mode={'edit' if is_edit else 'generate'} | revision={bool(revision)} "
        f"| evidences={len(state.evidences)} "
        f"| prompt_evidences={len(prompt_evidences)} "
        f"| topics_found={sum(group.brief.found for group in groups)}/{len(groups)} "
        f"| generated={len(result.result.events)}",
    )
    if draft is not None:
        logger.debug(
            f"[NODE][draft_events] DRAFT | occurred_at={draft.occurred_at!r} "
            f"| operation={draft.operation.value if draft.operation else None} | sources={draft.source_mi_event_ids} "
            f"| bullets={len(draft.key_bullets)} | evidences={[u.evidence_key for u in draft.evidence_usages]} "
            f"| claims={len(draft.claims)} | severity={draft.scenario_severity.value if draft.scenario_severity else None} "
            f"| summary={draft.one_line_summary!r}",
        )

    if draft is None:
        return {"draft": None, "warnings": ["LLM이 이벤트 초안을 생성하지 못했습니다."]}
    return {"draft": draft}


def _source_type_labels(state: GenerateFromQueryState, draft: EventDraft) -> list[str]:
    """편집 초안의 원본 기존 이벤트 유형 이름을 모은다(분류 프롬프트의 힌트).

    MCP 검색 결과는 유형을 정수 id 가 아닌 이름으로만 주므로 이름을 넘기고,
    카탈로그의 id 로 바꾸는 일은 분류 LLM 이 맡는다.
    """
    type_name_by_id = {
        evidence.ref_id: evidence.source_name
        for evidence in state.evidences
        if evidence.origin is EvidenceOrigin.EXISTING_EVENT and evidence.source_name != UNKNOWN_EVENT_SOURCE_NAME
    }
    names = [type_name_by_id.get(mi_event_id, "") for mi_event_id in draft.source_mi_event_ids]
    return list(dict.fromkeys(name for name in names if name))


def _to_assignment(
    output: type_prompt.EventTypeLLMOutput,
    draft: EventDraft,
    choices: dict[str, EventTypeCatalogItem],
) -> tuple[EventTypeAssignment, list[str]]:
    """LLM 이 고른 카테고리 이름을 event_type_l2_id 로 바꾼다.

    schema enum 이 카탈로그 이름만 허용하지만, strict 모드가 꺼져 있으면 벗어난 값이 올 수 있어
    매칭되지 않는 이름은 미분류(None)로 둔다.
    """
    chosen = (output.event_type or "").strip()
    catalog_item = choices.get(chosen)
    if chosen and catalog_item is None:
        logger.warning(f"[NODE][classify_event_type] UNKNOWN_TYPE | chosen={chosen!r}")
    event_type_l2_id = catalog_item.event_type_l2_id if catalog_item else None
    warnings = (
        []
        if event_type_l2_id is not None
        else [
            f"'{draft.one_line_summary}' 의 event type 을 카탈로그에서 특정하지 못했습니다.",
        ]
    )
    return EventTypeAssignment(event_type_l2_id=event_type_l2_id, rationale=output.rationale.strip()), warnings


@log_node
async def classify_event_type(
    state: GenerateFromQueryState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, Any]:
    """초안이 tmm_mi_event_type_l2_m 의 어느 카테고리에 해당하는지 LLM 이 판단해 고른다.

    병합·수정 초안은 원본 이벤트의 유형을 힌트로 함께 넘겨, 수정으로 사건 성격이
    바뀌었는지·병합된 사건을 어느 유형이 대표하는지를 판단하게 한다.

    카탈로그를 읽지 못하면(DB 미연결·빈 테이블) FALLBACK_EVENT_TYPE_L2_ID 로 채운다.
    event_type_l2_id 는 tmm_mi_mievent_m 의 NOT NULL FK라 None 이면 persist_events 가 저장하지 않는다.
    """
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    draft = state.draft
    if draft is None:
        return {"type_assignment": None}

    catalog = await load_event_type_catalog()
    if not catalog:
        logger.warning(f"[NODE][classify_event_type] NO_CATALOG | fallback={FALLBACK_EVENT_TYPE_L2_ID}")
        return {
            "type_assignment": EventTypeAssignment(
                event_type_l2_id=FALLBACK_EVENT_TYPE_L2_ID,
                rationale="event type 카탈로그 미연결로 기본값 적용",
            ),
            "warnings": ["event type 카탈로그를 불러오지 못해 기본 event type 을 적용했습니다."],
        }

    cfg = get_settings()
    choices = type_prompt.build_choices(catalog)
    try:
        result = await invoke_llm_structured_output(
            output_schema=type_prompt.build_output_schema(list(choices)),
            messages=type_prompt.build_messages(
                draft,
                choices,
                source_type_labels=_source_type_labels(state, draft),
            ),
            preference=ModelPreference.SPEED,
            temperature=0.0,
            trace_context=runtime.context if runtime is not None else None,
            stream=cfg.llm_stream_enabled,
            reasoning_effort=LIGHT_REASONING_EFFORT,
        )
    except Exception as exc:
        # 분류 실패로 생성된 초안까지 잃지 않도록, 미분류로 두고 경고만 남긴다.
        logger.exception("[NODE][classify_event_type] FAILED")
        return {
            "type_assignment": EventTypeAssignment(),
            "warnings": [f"event type 분류에 실패했습니다: {exc!r}"],
        }

    assignment, warnings = _to_assignment(result.result, draft, choices)
    logger.info(
        f"[NODE][classify_event_type] DONE | catalog={len(catalog)} | event_type_l2_id={assignment.event_type_l2_id}",
    )
    return {"type_assignment": assignment, "warnings": warnings}


def _blocked_warning(state: GenerateFromQueryState) -> list[str]:
    """검증 error 로 저장하지 않았으면 그 사실만 알린다. 이슈 내용은 로그에만 남긴다."""
    if state.draft is None or state.validation is None or not state.validation.blocked:
        return []
    return [f"'{state.draft.one_line_summary}' 는 검증 error 가 있어 저장하지 않았습니다."]


def _log_validation(state: GenerateFromQueryState) -> None:
    """최종 검증 결과와 이슈 내용을 로그로 남긴다(응답에는 담지 않는다)."""
    validation = state.validation
    if state.draft is None or validation is None:
        return
    logger.info(
        f"[NODE][finalize] VALIDATION | summary={state.draft.one_line_summary!r} | blocked={validation.blocked} "
        f"| severity={validation.scenario_severity.value} | feasibility={validation.feasibility_status.value} "
        f"| clusters={validation.shock_clusters} | claims={len(validation.claims)} | issues={len(validation.issues)}",
    )
    for issue in validation.issues:
        log = logger.warning if issue.severity is IssueSeverity.ERROR else logger.info
        log(
            f"[NODE][finalize] VALIDATION_ISSUE | severity={issue.severity.value} | code={issue.code} "
            f"| claim={issue.claim_id!r} | message={issue.message!r}",
        )


@log_node
async def finalize(state: GenerateFromQueryState) -> dict[str, Any]:
    """초안·참고 근거·분기·저장 결과·경고를 API 응답 shape으로 합친다. 검증 이슈 등 생성 과정 정보는 로그로만 남긴다."""

    events: list[GeneratedFromQueryEventOut] = []
    draft = state.draft
    if draft is not None:
        events.append(
            GeneratedFromQueryEventOut(
                one_line_summary=draft.one_line_summary,
                detail_analysis=draft.detail_analysis,
                key_bullets=list(draft.key_bullets),
                tags=list(draft.tags),
                occurred_at=draft.occurred_at,
                event_type_l2_id=state.type_assignment.event_type_l2_id if state.type_assignment else None,
                operation=draft.operation.value if draft.operation else None,
                source_mi_event_ids=list(draft.source_mi_event_ids),
                generation_rationale=draft.generation_rationale,
                evidences=_to_evidence_out(draft.evidence_usages, state.evidences),
                mi_event_id=state.saved_event_id,
            ),
        )

    # 재작성 패스가 있으면 병렬 실행되는 유형 분류가 같은 경고를 패스마다 남기므로 순서를 유지한 채 중복을 제거한다.
    warnings = list(
        dict.fromkeys(
            [
                *state.warnings,
                *(f"[{error.stage}] {error.message}" for error in state.branch_errors),
                *_blocked_warning(state),
            ],
        ),
    )
    result = GenerateFromQueryResult(
        meta=GenerateFromQueryMetaOut(
            route=state.route.value,
            route_reason=state.route_reason,
            persisted_count=int(state.saved_event_id is not None),
            warnings=warnings,
        ),
        events=events,
    )
    _log_validation(state)
    logger.info(
        f"[NODE][finalize] DONE | events={len(events)} | persisted={state.saved_event_id is not None} "
        f"| route={state.route.value} | fallback={state.fallback_used} | warnings={len(warnings)}",
    )
    return {"result": result}
