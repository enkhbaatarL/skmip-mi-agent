"""validate_claims 노드 — 생성된 초안의 claim 을 근거와 대조해 검증하고, 저장 차단·재작성 여부를 정한다.

- LLM: claim 마다 근거 지지·시점 성립을 다시 판정하고, 누락 claim·수치 불일치·가정 표시 누락을 찾는다.
- 코드: 판정 결과에 규칙을 적용해 error/warning, 시나리오 강도, 성립성을 정한다(tools/claim_rules.py).
- 고칠 수 있는 error 가 있고 재작성 횟수가 남았으면 draft_events 로 돌려보낸다(pending_revision).
- 재작성 후에도 error 가 남은 초안은 persist_events 가 저장하지 않는다.
"""

from __future__ import annotations

from typing import Any

from langgraph.runtime import Runtime

from apps.agents.event_generate_agent.constants import MAX_DRAFT_REVISIONS, MAX_EVIDENCE_ITEMS
from apps.agents.event_generate_agent.flows.generate_from_query.schema import FactTimeline, TopicEvidenceGroup
from apps.agents.event_generate_agent.flows.generate_from_query.state import GenerateFromQueryState
from apps.agents.event_generate_agent.flows.generate_from_query.tools.claim_rules import apply_claim_rules
from apps.agents.event_generate_agent.flows.generate_from_query.tools.evidence import (
    group_prompt_evidences,
    known_links,
)
from apps.agents.event_generate_agent.flows.generate_from_query.tools.temporal import build_timeline, parse_target_date
from apps.agents.event_generate_agent.prompts import claim_verification as verify_prompt
from apps.agents.event_generate_agent.schemas.domain import (
    EventClaim,
    EventDraft,
    EventValidation,
    IssueSeverity,
)
from apps.common.configs.config import get_settings
from apps.common.logging.decorators import log_node
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.common.values.enums import ModelPreference


def _timeline_at(state: GenerateFromQueryState, target_date: str) -> FactTimeline | None:
    """초안의 발생 시점이 생성 전 시점표의 기준일과 다르면 시점표를 그 날짜로 다시 계산한다."""
    timeline = state.fact_timeline
    target = parse_target_date(target_date)
    if target is None or (timeline is not None and timeline.target_date == target.isoformat()):
        return timeline
    facts = [fact for brief in state.topic_briefs for fact in brief.facts]
    return FactTimeline(target_date=target.isoformat(), entries=build_timeline(facts, target))


async def _verify_draft(
    state: GenerateFromQueryState,
    draft: EventDraft,
    groups: list[TopicEvidenceGroup],
    timeline: FactTimeline | None,
    *,
    trace_context: TraceContext | None,
) -> EventValidation:
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    known_keys = {evidence.evidence_key for group in groups for evidence in group.evidences}

    try:
        result = await invoke_llm_structured_output(
            output_schema=verify_prompt.ClaimVerificationLLMOutput,
            messages=verify_prompt.build_messages(
                state.user_query,
                draft,
                groups,
                fact_timeline=timeline,
            ),
            preference=ModelPreference.QUALITY,
            temperature=0.0,
            trace_context=trace_context,
            stream=get_settings().llm_stream_enabled,
            reasoning_effort=get_settings().llm_reasoning_effort,
        )
    except Exception:
        # 검증하지 못한 초안은 근거 정합성을 보장할 수 없으므로 규칙 엔진이 error(VALIDATION_FAILED)로 막는다.
        logger.exception("[NODE][validate_claims] FAILED")
        return apply_claim_rules(draft, verdicts=None, untracked=[], quantitative_issues=[], unmarked_assumptions=[])

    output = result.result
    declared = {claim.claim_id: claim for claim in draft.claims}
    verdicts: dict[str, EventClaim] = {}
    for item in output.claims:
        claim = declared.get(item.claim_id.strip())
        if claim is None:
            logger.warning(f"[NODE][validate_claims] UNKNOWN_CLAIM | claim={item.claim_id!r}")
            continue
        verdicts[claim.claim_id] = claim.model_copy(
            update={
                "support": item.support,
                "plausibility": item.plausibility,
                "hard_conflict": item.hard_conflict,
                "evidence": known_links(item.evidence, known_keys) or claim.evidence,
                "temporal_ok": item.temporal_ok,
                "reason": item.reason.strip(),
            },
        )
    untracked = [
        EventClaim(
            claim_id=f"U{index}",
            text=item.text.strip(),
            claim_type=item.claim_type,
            support=item.support,
            plausibility=item.plausibility,
            hard_conflict=item.hard_conflict,
            evidence=known_links(item.evidence, known_keys),
            temporal_ok=item.temporal_ok,
            reason=item.reason.strip(),
        )
        for index, item in enumerate((item for item in output.untracked_claims if item.text.strip()), start=1)
    ]
    return apply_claim_rules(
        draft,
        verdicts=verdicts,
        untracked=untracked,
        quantitative_issues=output.quantitative_issues,
        unmarked_assumptions=output.unmarked_assumptions,
        reasoning_issues=output.reasoning_issues,
    )


@log_node
async def validate_claims(
    state: GenerateFromQueryState,
    runtime: Runtime[TraceContext] | None = None,
) -> dict[str, Any]:
    """초안의 claim 을 검증하고, 고칠 수 있는 error 가 있으면 재작성을 예약한다."""
    if state.draft is None:
        return {"validation": None, "pending_revision": False}

    groups = group_prompt_evidences(state.topic_briefs, state.evidences, max_total=MAX_EVIDENCE_ITEMS)
    trace_context = runtime.context if runtime is not None else None
    base_date = state.fact_timeline.target_date if state.fact_timeline else ""
    timeline = _timeline_at(state, state.draft.occurred_at or base_date)
    validation = await _verify_draft(state, state.draft, groups, timeline, trace_context=trace_context)

    errors = [issue for issue in validation.issues if issue.severity is IssueSeverity.ERROR]
    logger.info(
        f"[NODE][validate_claims] RESULT | pass={state.revision_count} "
        f"| severity={validation.scenario_severity.value} | feasibility={validation.feasibility_status.value} "
        f"| clusters={validation.shock_clusters} | claims={len(validation.claims)} | errors={[i.code for i in errors]} "
        f"| warnings={len(validation.issues) - len(errors)}",
    )

    fixable = any(issue.fixable for issue in errors)
    if fixable and state.revision_count < MAX_DRAFT_REVISIONS:
        logger.warning(f"[NODE][validate_claims] REVISE | pass={state.revision_count} → {state.revision_count + 1}")
        return {
            "validation": validation,
            "fact_timeline": timeline,
            "pending_revision": True,
            "revision_count": state.revision_count + 1,
        }
    # 검증에 실제로 쓴 시점표(초안 발생 시점 기준)로 덮어써, 재작성·응답이 같은 시점표를 보게 한다.
    return {"validation": validation, "fact_timeline": timeline, "pending_revision": False}


@log_node
async def join_draft_review(state: GenerateFromQueryState) -> dict[str, Any]:
    """validate_claims 와 classify_event_type 이 모두 끝나기를 기다리는 합류 노드(상태 변경 없음).

    두 노드는 초안만 있으면 서로 독립이라 같은 superstep 에서 병렬로 돈다.
    재작성 여부(route_after_validation)는 둘이 모두 끝난 뒤 여기서 판단한다.
    재작성되면 분류 결과는 새 초안 기준으로 다시 덮어쓴다.
    """
    logger.debug(
        f"[NODE][join_draft_review] JOINED | validated={state.validation is not None} "
        f"| typed={state.type_assignment is not None} | pending_revision={state.pending_revision}",
    )
    return {}
