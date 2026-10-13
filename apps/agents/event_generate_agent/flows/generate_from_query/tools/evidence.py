"""검색 결과를 공통 근거(EvidenceItem)로 정규화하고 토픽별로 묶는 툴.

검색 노드가 결과를 곧바로 EvidenceItem 으로 바꿔 state.evidences 에 덧붙인다. 여기서 출처 차이를
흡수해 두면 뒷단(근거 정리/초안 생성/리뷰)은 근거가 웹에서 왔는지 기존 이벤트에서 왔는지 몰라도 된다.

근거 키는 토픽·출처 안에서만 번호를 매긴다(`T1-W1`, `T2-E3`). 폴백 패스는 재검색 토픽의 결과만
이어지는 번호로 덧붙이므로, 이미 있는 근거의 키는 그대로 유지되어 앞서 만든 근거 정리가 그대로 유효하다.
"""

from __future__ import annotations

from collections import Counter

from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    EvidenceItem,
    EvidenceOrigin,
    ExistingEventHit,
    TopicBrief,
    TopicEvidenceGroup,
    WebDocument,
)
from apps.agents.event_generate_agent.schemas.domain import EvidenceLink


# 기존 이벤트 근거의 source_name 은 이벤트 유형 이름이고, 유형을 모르면 이 값을 쓴다.
UNKNOWN_EVENT_SOURCE_NAME = "MI Event"


def _next_index(existing: list[EvidenceItem], origin: EvidenceOrigin) -> Counter[str]:
    """토픽별로 이 출처의 근거가 이미 몇 건 있는지 센다(새 근거 번호의 시작점)."""
    return Counter(evidence.topic_key for evidence in existing if evidence.origin is origin)


def web_documents_to_evidences(documents: list[WebDocument], existing: list[EvidenceItem]) -> list[EvidenceItem]:
    """웹 문서를 EvidenceItem 으로 바꾼다. 키는 토픽마다 기존 웹 근거 다음 번호부터 매긴다(I/O 없음)."""
    counts = _next_index(existing, EvidenceOrigin.WEB)
    evidences: list[EvidenceItem] = []
    for document in documents:
        counts[document.topic_key] += 1
        evidences.append(
            EvidenceItem(
                evidence_key=f"{document.topic_key}-W{counts[document.topic_key]}",
                origin=EvidenceOrigin.WEB,
                topic_key=document.topic_key,
                title=document.title,
                content=document.content,
                published_at=document.published_at,
                source_name=document.source_name,
                url=document.url,
                provider=document.provider,
            ),
        )
    return evidences


def event_hits_to_evidences(hits: list[ExistingEventHit], existing: list[EvidenceItem]) -> list[EvidenceItem]:
    """기존 이벤트를 EvidenceItem 으로 바꾼다. 키는 토픽마다 기존 이벤트 근거 다음 번호부터 매긴다(I/O 없음)."""
    counts = _next_index(existing, EvidenceOrigin.EXISTING_EVENT)
    evidences: list[EvidenceItem] = []
    for hit in hits:
        counts[hit.topic_key] += 1
        body_parts = [hit.detail_analysis] if hit.detail_analysis else []
        body_parts.extend(hit.key_bullets)
        evidences.append(
            EvidenceItem(
                evidence_key=f"{hit.topic_key}-E{counts[hit.topic_key]}",
                origin=EvidenceOrigin.EXISTING_EVENT,
                topic_key=hit.topic_key,
                title=hit.one_line_summary,
                content="\n".join(body_parts),
                published_at=hit.occurred_at,
                source_name=hit.event_type_l2_name or UNKNOWN_EVENT_SOURCE_NAME,
                ref_id=hit.mi_event_id,
            ),
        )
    return evidences


def group_prompt_evidences(
    briefs: list[TopicBrief],
    evidences: list[EvidenceItem],
    *,
    max_total: int,
) -> list[TopicEvidenceGroup]:
    """토픽별 근거 정리 결과에 따라 초안 프롬프트에 넣을 근거를 토픽마다 고른다(I/O 없음).

    정리 단계가 관련 있다고 고른 근거만, 고른 순서대로 넣는다. 토픽마다 같은 몫
    (max_total // 토픽 수, 최소 1)까지만 넣어 한 토픽이 프롬프트를 독점하지 않게 한다.
    관련 근거가 없는 토픽도 정리 결과(근거 없음 사유)는 남겨 초안이 그 사실을 알게 한다.
    """
    if not briefs:
        return []
    per_topic = max(1, max_total // len(briefs))
    evidence_by_key = {evidence.evidence_key: evidence for evidence in evidences}
    groups: list[TopicEvidenceGroup] = []
    for brief in briefs:
        selected = [evidence_by_key[key] for key in brief.evidence_keys if key in evidence_by_key]
        groups.append(TopicEvidenceGroup(brief=brief, evidences=selected[:per_topic]))
    return groups


def known_links(links: list[EvidenceLink], known_keys: set[str]) -> list[EvidenceLink]:
    """입력에 있는 근거 키의 링크만 남긴다(괄호 제거, 키 중복 제거)."""
    cleaned: list[EvidenceLink] = []
    seen: set[str] = set()
    for link in links:
        key = link.evidence_key.strip().strip("[]")
        if key in known_keys and key not in seen:
            seen.add(key)
            cleaned.append(link.model_copy(update={"evidence_key": key}))
    return cleaned
