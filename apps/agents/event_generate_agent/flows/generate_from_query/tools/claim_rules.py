"""claim 검증 판정을 저장 차단 여부·시나리오 강도·성립성으로 바꾸는 규칙 엔진(LLM 없음).

LLM 검증기는 claim 마다 근거 지지·시점 성립만 판정하고, 무엇을 error 로 막을지는 여기서 결정적으로 정한다.
- error 가 하나라도 있으면 그 초안은 저장하지 않는다(EventValidation.blocked).
- claim_type 마다 기준이 다르다. 근거 사실은 직접 지지, 모델 추론은 경제적·물리적 타당성,
  사용자 가정은 명백한 모순 여부만 본다(근거 없는 시나리오 조건은 정상).
- fixable 인 error 는 초안 재작성으로 고칠 수 있다. 사용자 가정 자체가 명백히 모순인 경우는 재작성해도
  사용자 요청이 바뀌지 않으므로 fixable 이 아니다.
- 시나리오 강도(일어나기 어려운 정도)와 성립성(근거와 모순 없음)은 별개 축으로 판정한다.
"""

from __future__ import annotations

from apps.agents.event_generate_agent.constants import SEVERE_STRESS_MIN_SHOCK_CLUSTERS
from apps.agents.event_generate_agent.schemas.domain import (
    ClaimType,
    EventClaim,
    EventDraft,
    EventValidation,
    FeasibilityStatus,
    InferencePlausibility,
    IssueSeverity,
    ScenarioSeverity,
    SupportStatus,
    ValidationIssue,
)


_SEVERITY_ORDER = [
    ScenarioSeverity.BASE,
    ScenarioSeverity.PLAUSIBLE_STRESS,
    ScenarioSeverity.SEVERE_STRESS,
    ScenarioSeverity.TAIL_RISK,
]


def _issue(
    code: str,
    message: str,
    *,
    error: bool,
    fixable: bool,
    claim_id: str = "",
) -> ValidationIssue:
    return ValidationIssue(
        severity=IssueSeverity.ERROR if error else IssueSeverity.WARNING,
        code=code,
        message=message,
        claim_id=claim_id,
        fixable=fixable,
    )


def _fact_issues(claim: EventClaim, detail: str) -> list[ValidationIssue]:
    """EVIDENCED_FACT: 근거가 직접 지지해야 한다. 근거 없음·충돌·시점 불일치는 error."""
    issues: list[ValidationIssue] = []
    if claim.support is SupportStatus.CONTRADICTED:
        issues.append(
            _issue(
                "CONTRADICTS_EVIDENCE",
                f"근거와 충돌하는 사실 서술: {detail}",
                error=True,
                fixable=True,
                claim_id=claim.claim_id,
            ),
        )
    elif claim.support is SupportStatus.UNSUPPORTED:
        issues.append(
            _issue(
                "MISLABELED_FACT",
                f"근거 사실로 표시했으나 근거가 없음: {detail}",
                error=True,
                fixable=True,
                claim_id=claim.claim_id,
            ),
        )
    elif claim.support is SupportStatus.PARTIAL:
        issues.append(
            _issue(
                "PARTIAL_SUPPORT",
                f"근거가 일부만 지지함: {detail}",
                error=False,
                fixable=True,
                claim_id=claim.claim_id,
            ),
        )
    if not claim.temporal_ok:
        issues.append(
            _issue(
                "TEMPORAL_MISMATCH",
                f"기준일 시점에 성립하지 않는 사실 서술: {detail}",
                error=True,
                fixable=True,
                claim_id=claim.claim_id,
            ),
        )
    return issues


def _inference_issues(claim: EventClaim, detail: str) -> list[ValidationIssue]:
    """MODEL_INFERENCE: 직접 인용 근거가 아니라 경제적·물리적 타당성으로 본다.

    표준적인 시장 전달 경로는 근거 문구가 없어도 PLAUSIBLE 이며 이슈가 아니다.
    근거·물리 제약과 모순(CONTRADICTED)이거나, 기준일에 가동 전인 설비를 공급원으로 쓰는 등 시점이 맞지 않으면 error.
    """
    issues: list[ValidationIssue] = []
    if claim.plausibility is InferencePlausibility.CONTRADICTED:
        issues.append(
            _issue(
                "CONTRADICTS_EVIDENCE",
                f"근거·물리 제약과 모순되는 추론: {detail}",
                error=True,
                fixable=True,
                claim_id=claim.claim_id,
            ),
        )
    elif claim.plausibility is InferencePlausibility.WEAK:
        issues.append(
            _issue(
                "WEAK_INFERENCE",
                f"인과가 약하거나 과장된 추론: {detail}",
                error=False,
                fixable=True,
                claim_id=claim.claim_id,
            ),
        )
    if not claim.temporal_ok:
        issues.append(
            _issue(
                "TEMPORAL_MISMATCH",
                f"기준일 시점에 성립하지 않는 추론: {detail}",
                error=True,
                fixable=True,
                claim_id=claim.claim_id,
            ),
        )
    return issues


def _assumption_issues(claim: EventClaim, detail: str) -> list[ValidationIssue]:
    """USER_ASSUMPTION: 시나리오 조건이므로 근거 없음은 정상이다.

    근거 사실·물리·계약 제약과 명백히 양립할 수 없을 때(hard_conflict)만 error 로 막는다.
    사용자 요청 자체의 문제이므로 재작성으로 고칠 수 없다(fixable=False).
    시점이 어긋나지만 명백한 모순은 아닌 경우(예: 개시 예정 프로젝트의 조기 가동 가정)는 warning 이다.
    """
    if claim.hard_conflict:
        return [
            _issue(
                "USER_ASSUMPTION_CONFLICT",
                f"사용자 가정이 근거·물리·계약 제약과 명백히 모순됨: {detail}",
                error=True,
                fixable=False,
                claim_id=claim.claim_id,
            ),
        ]
    if not claim.temporal_ok:
        return [
            _issue(
                "ASSUMPTION_TIMING",
                f"사용자 가정이 근거상 일정과 다름(시나리오 조건으로 허용): {detail}",
                error=False,
                fixable=False,
                claim_id=claim.claim_id,
            ),
        ]
    return []


def _claim_issues(claim: EventClaim) -> list[ValidationIssue]:
    """검증된 claim 1건에 claim_type 별 기준을 적용한다."""
    detail = f"'{claim.text}'" + (f" — {claim.reason}" if claim.reason else "")
    if claim.claim_type is ClaimType.EVIDENCED_FACT:
        return _fact_issues(claim, detail)
    if claim.claim_type is ClaimType.MODEL_INFERENCE:
        return _inference_issues(claim, detail)
    return _assumption_issues(claim, detail)


def _conflicts_with_evidence(claim: EventClaim) -> bool:
    """Claim 이 근거와 모순되는지(성립성 판정용). 사용자 가정의 일정 차이는 시나리오 조건이라 모순으로 보지 않는다."""
    if claim.claim_type is ClaimType.EVIDENCED_FACT:
        return claim.support is SupportStatus.CONTRADICTED or not claim.temporal_ok
    if claim.claim_type is ClaimType.MODEL_INFERENCE:
        return claim.plausibility is InferencePlausibility.CONTRADICTED or not claim.temporal_ok
    return claim.hard_conflict


def _shock_clusters(claims: list[EventClaim]) -> list[str]:
    """근거로 확인되지 않은 충격 claim 의 독립 충격 묶음(이름 정규화 후 중복 제거, 첫 표기 유지).

    근거로 이미 확인된 사실(EVIDENCED_FACT 이면서 SUPPORTED)은 가정된 충격이 아니므로 세지 않는다.
    """
    clusters: dict[str, str] = {}
    for claim in claims:
        name = claim.shock_cluster.strip()
        confirmed = claim.claim_type is ClaimType.EVIDENCED_FACT and claim.support is SupportStatus.SUPPORTED
        if not name or confirmed:
            continue
        clusters.setdefault(" ".join(name.split()).casefold(), name)
    return list(clusters.values())


def severity_floor(cluster_count: int) -> ScenarioSeverity:
    """독립 충격 묶음 수로 정한 최소 시나리오 강도."""
    if cluster_count >= SEVERE_STRESS_MIN_SHOCK_CLUSTERS:
        return ScenarioSeverity.SEVERE_STRESS
    if cluster_count >= 1:
        return ScenarioSeverity.PLAUSIBLE_STRESS
    return ScenarioSeverity.BASE


def apply_claim_rules(
    draft: EventDraft,
    *,
    verdicts: dict[str, EventClaim] | None,
    untracked: list[EventClaim],
    quantitative_issues: list[str],
    unmarked_assumptions: list[str],
    reasoning_issues: list[str] | None = None,
) -> EventValidation:
    """초안 1건의 검증 판정에 규칙을 적용해 최종 EventValidation 을 만든다(I/O 없음).

    Args:
        draft: 생성 LLM 이 밝힌 claims·scenario_severity 를 담은 초안.
        verdicts: claim_id → 검증기가 다시 판정한 claim. None 이면 검증 자체가 실패한 것이다.
        untracked: 본문에 있으나 claim 목록에 빠져 검증기가 따로 판정한 claim.
        quantitative_issues: 검증기가 찾은 수치 간 산술 불일치.
        unmarked_assumptions: 검증기가 찾은, 가정인데 본문에 가정 표시가 없는 서술.
        reasoning_issues: 검증기가 찾은, claim 사이의 추론 연결이 성립하지 않는 곳(재작성 대상 error).

    """
    declared = draft.scenario_severity

    if verdicts is None:
        return EventValidation(
            scenario_severity=declared or ScenarioSeverity.BASE,
            feasibility_status=FeasibilityStatus.UNVERIFIED,
            claims=list(draft.claims),
            issues=[
                _issue(
                    "VALIDATION_FAILED",
                    "claim 검증에 실패해 근거와의 정합성을 확인하지 못함",
                    error=True,
                    fixable=False,
                ),
            ],
        )

    claims: list[EventClaim] = []
    issues: list[ValidationIssue] = []
    for claim in draft.claims:
        verdict = verdicts.get(claim.claim_id)
        if verdict is None:
            claims.append(claim)
            issues.append(
                _issue(
                    "UNVERIFIED_CLAIM",
                    f"검증 판정이 없는 claim: '{claim.text}'",
                    error=False,
                    fixable=False,
                    claim_id=claim.claim_id,
                ),
            )
            continue
        claims.append(verdict)
        issues.extend(_claim_issues(verdict))
    for claim in untracked:
        claims.append(claim)
        issues.extend(_claim_issues(claim))

    issues.extend(
        _issue("QUANT_INCONSISTENT", f"수치 간 산술 불일치: {message}", error=True, fixable=True)
        for message in quantitative_issues
        if message.strip()
    )
    issues.extend(
        _issue("UNMARKED_ASSUMPTION", f"가정인데 본문에 가정 표시가 없음: {message}", error=False, fixable=True)
        for message in unmarked_assumptions
        if message.strip()
    )
    # 개별 claim 의 WEAK 판정은 warning 이라 재작성을 일으키지 않으므로,
    # claim 간 연결 문제는 고칠 수 있는 error 로 막아 재작성을 유도한다.
    issues.extend(
        _issue("REASONING_GAP", f"추론 연결이 결론을 뒷받침하지 못함: {message}", error=True, fixable=True)
        for message in reasoning_issues or []
        if message.strip()
    )

    clusters = _shock_clusters(claims)
    floor = severity_floor(len(clusters))
    severity = declared or floor
    if _SEVERITY_ORDER.index(severity) < _SEVERITY_ORDER.index(floor):
        issues.append(
            _issue(
                "SEVERITY_RAISED",
                f"독립 충격 묶음 {len(clusters)}개({', '.join(clusters)})로 시나리오 강도를 "
                f"{severity.value} → {floor.value} 로 올림",
                error=False,
                fixable=False,
            ),
        )
        severity = floor

    conflicted = any(_conflicts_with_evidence(claim) for claim in claims)
    return EventValidation(
        scenario_severity=severity,
        feasibility_status=FeasibilityStatus.CONFLICTS_WITH_EVIDENCE if conflicted else FeasibilityStatus.CONSISTENT,
        shock_clusters=clusters,
        claims=claims,
        issues=issues,
    )
