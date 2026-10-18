"""검증 단계 산출물(근거 사실·사실 시점표·claim)을 프롬프트 텍스트로 만드는 공용 포매터.

초안 생성·claim 검증 프롬프트가 같은 표기를 쓰도록 한곳에 둔다.
모두 순수 함수(I/O 없음)다.
"""

from __future__ import annotations

from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    AssetStatus,
    EvidencedFact,
    FactTimeline,
    TemporalStatus,
)
from apps.agents.event_generate_agent.schemas.domain import EventClaim


def format_fact(fact: EvidencedFact) -> str:
    """근거 사실 1건. 예: "[T1-F2] (PLAN | NFS | PLANNED | 시작 2028) NFS 2028년 가동 개시 예정 ← T1-W2"."""
    meta = [fact.fact_kind.value]
    if fact.entity:
        meta.append(fact.entity)
    if fact.asset_status is not AssetStatus.NOT_APPLICABLE:
        meta.append(fact.asset_status.value)
    if fact.as_of:
        meta.append(f"기준 {fact.as_of}")
    if fact.valid_from:
        meta.append(f"시작 {fact.valid_from}")
    if fact.valid_to:
        meta.append(f"종료 {fact.valid_to}")
    return f"[{fact.fact_id}] ({' | '.join(meta)}) {fact.statement} ← {', '.join(fact.evidence_keys)}"


_TEMPORAL_LABEL = {
    TemporalStatus.ACTIVE: "기준일에 유효",
    TemporalStatus.NOT_YET: "기준일에 아직 시작 전(공급·계약 효과 없음)",
    TemporalStatus.ENDED: "기준일 전에 종료",
    TemporalStatus.UNCERTAIN: "기준일 전후 판정 불가",
    TemporalStatus.STALE: "과거 관측 상태, 기준일까지 지속 여부 미확인(근거 사실로 지속을 단정할 수 없음)",
    TemporalStatus.PAST_EVENT: "기준일 전에 일어난 사건·실적(과거 사례. 그 상태가 기준일까지 이어진다고 단정하지 말 것)",
    TemporalStatus.UNKNOWN: "시점 정보 없음",
}


def format_timeline(timeline: FactTimeline | None) -> str:
    target = timeline.target_date if timeline else ""
    if timeline is None or not timeline.entries:
        return f"기준일: {target or '미정'}\n(시점 판정 대상 사실이 없습니다.)"
    lines = [f"기준일: {target}"]
    for entry in timeline.entries:
        entity = f" {entry.entity}" if entry.entity else ""
        lines.append(f"- [{entry.fact_id}]{entity}: {_TEMPORAL_LABEL[entry.status]} ({entry.reason})")
    return "\n".join(lines)


def format_claims(claims: list[EventClaim]) -> str:
    if not claims:
        return "(초안이 밝힌 claim 이 없습니다.)"
    lines: list[str] = []
    for claim in claims:
        parts = [f"[{claim.claim_id}] {claim.claim_type.value}", claim.text]
        if claim.fact_ids:
            parts.append(f"사실={', '.join(claim.fact_ids)}")
        if claim.evidence:
            parts.append(f"근거={', '.join(f'{link.evidence_key}:{link.relation.value}' for link in claim.evidence)}")
        lines.append(" | ".join(parts))
    return "\n".join(lines)
