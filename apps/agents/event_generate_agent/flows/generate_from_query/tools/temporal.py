"""근거 사실의 시점 정합성을 날짜 비교로 판정하는 툴(LLM 없음).

LLM 은 근거에서 시점(as_of / valid_from / valid_to)과 상태(asset_status)를 뽑기만 하고,
"시나리오 기준일에 이 프로젝트·계약·설비가 실제로 유효한가"는 여기서 결정적으로 판정한다.
날짜는 정밀도가 제각각이라(YYYY / YYYY-MM / YYYY-MM-DD) 기간으로 바꿔 비교한다.
"""

from __future__ import annotations

import calendar
from datetime import date
import re

from apps.agents.event_generate_agent.flows.generate_from_query.schema import (
    AssetStatus,
    EvidencedFact,
    FactKind,
    FactTimelineEntry,
    TemporalStatus,
)


_DATE_PATTERN = re.compile(r"(\d{4})(?:\D{1,3}(\d{1,2}))?(?:\D{1,3}(\d{1,2}))?")

# 한번 시작되면 별도 종료 근거가 없는 한 계속되는 상태(가동). 시작 시점이 없을 때 상태만으로 판정한다.
_DURABLE_STATUSES = {AssetStatus.OPERATING, AssetStatus.RAMP_UP}
_NOT_STARTED_STATUSES = {AssetStatus.PLANNED, AssetStatus.UNDER_CONSTRUCTION}


def parse_period(text: str) -> tuple[date, date] | None:
    """날짜 문자열을 (기간 시작일, 기간 종료일)로 바꾼다. 해석할 수 없으면 None.

    "2028" → (2028-01-01, 2028-12-31), "2027-03" → (2027-03-01, 2027-03-31), "2027-03-15" → 같은 날.
    """
    match = _DATE_PATTERN.search(text or "")
    if match is None:
        return None
    year = int(match.group(1))
    month = int(match.group(2)) if match.group(2) else None
    day = int(match.group(3)) if match.group(3) else None
    try:
        if month is None:
            return date(year, 1, 1), date(year, 12, 31)
        if day is None:
            return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])
        point = date(year, month, day)
    except ValueError:
        return None
    return point, point


def parse_target_date(text: str) -> date | None:
    """시나리오 기준일을 하루로 고정한다. 기간이면 그 시작일을 쓴다."""
    period = parse_period(text)
    return period[0] if period else None


def _is_transient(fact: EvidencedFact) -> bool:
    """관측 시점 이후 저절로 끝날 수 있는 일시적 상태인지(설비 중단, 해협 봉쇄·한파 같은 상황).

    이런 상태는 종료 시점이 없다고 해서 미래 기준일까지 계속된다고 볼 수 없다.
    """
    if fact.asset_status is AssetStatus.OUTAGE:
        return True
    return fact.fact_kind is FactKind.STATUS and fact.asset_status is AssetStatus.NOT_APPLICABLE


def _is_one_off_event(fact: EvidencedFact) -> bool:
    """이미 일어난 일회성 사건·실적인지(예: 2021-01 JKM 사상 최고치). 설비·계약처럼 지속되는 상태가 아니다."""
    return fact.fact_kind is FactKind.ACTUAL and fact.asset_status is AssetStatus.NOT_APPLICABLE


def _one_off_event(
    entry: FactTimelineEntry,
    fact: EvidencedFact,
    occurred: tuple[date, date] | None,
    target: date,
) -> FactTimelineEntry:
    """일회성 사건은 발생 시점이 기준일 전이면 과거 사례(PAST_EVENT)다. 시작 시점만으로 기준일까지 유효하다고 보지 않는다."""
    if occurred is None:
        return _entry(entry, TemporalStatus.UNKNOWN, "일회성 사건이나 발생 시점 없음")
    if occurred[1] < target:
        return _entry(
            entry,
            TemporalStatus.PAST_EVENT,
            f"{fact.valid_from or fact.as_of} 에 일어난 과거 사건(기준일 {target} 의 현재 상태 아님)",
        )
    return _entry(
        entry, TemporalStatus.UNCERTAIN, f"사건 발생 시점 {fact.valid_from or fact.as_of} 이 기준일 {target} 과 겹침"
    )


def _entry(entry: FactTimelineEntry, status: TemporalStatus, reason: str) -> FactTimelineEntry:
    return entry.model_copy(update={"status": status, "reason": reason})


def _by_bounds(
    entry: FactTimelineEntry,
    fact: EvidencedFact,
    start: tuple[date, date] | None,
    end: tuple[date, date] | None,
    target: date,
) -> FactTimelineEntry | None:
    """시작·종료 시점으로 판정이 끝나면 결과를, 종료 시점이 없어 더 봐야 하면 None 을 돌려준다."""
    if start is not None:
        if start[0] > target:
            return _entry(entry, TemporalStatus.NOT_YET, f"시작 시점 {fact.valid_from} > 기준일 {target}")
        if start[1] > target:
            return _entry(
                entry,
                TemporalStatus.UNCERTAIN,
                f"시작 시점 {fact.valid_from} 이 기준일 {target} 과 같은 기간에 걸침",
            )
    if end is None:
        return None
    if end[1] < target:
        return _entry(entry, TemporalStatus.ENDED, f"종료 시점 {fact.valid_to} < 기준일 {target}")
    if end[0] <= target:
        return _entry(
            entry,
            TemporalStatus.UNCERTAIN,
            f"종료 시점 {fact.valid_to} 이 기준일 {target} 과 같은 기간에 걸침",
        )
    return _entry(entry, TemporalStatus.ACTIVE, f"종료 시점 {fact.valid_to} > 기준일 {target}")


def _transient_without_end(
    entry: FactTimelineEntry,
    fact: EvidencedFact,
    start: tuple[date, date] | None,
    as_of: tuple[date, date] | None,
    target: date,
) -> FactTimelineEntry:
    """종료 시점이 없는 일시적 상태: 관측 시점까지만 확인된 것으로 보고 그 뒤 기준일은 STALE."""
    observed = as_of or start
    if observed is None:
        return _entry(entry, TemporalStatus.UNKNOWN, "일시적 상태이나 관측 시점·종료 시점 없음")
    if observed[1] < target:
        return _entry(
            entry,
            TemporalStatus.STALE,
            f"{fact.as_of or fact.valid_from} 기준 상태이며 종료 시점이 없어 기준일 {target} 까지 지속 여부 미확인",
        )
    if start is None and observed[0] > target:
        return _entry(entry, TemporalStatus.UNCERTAIN, f"상태 관측 시점 {fact.as_of} 이 기준일 {target} 이후")
    return _entry(entry, TemporalStatus.ACTIVE, f"{fact.as_of or fact.valid_from} 기준 상태가 기준일을 포함")


def evaluate_fact(fact: EvidencedFact, target: date) -> FactTimelineEntry:
    """사실 1건이 기준일에 유효한지 판정한다(I/O 없음).

    - 시작 시점이 기준일 이후면 NOT_YET, 종료 시점이 기준일 전이면 ENDED.
    - 종료 시점이 없는 일시적 상태(OUTAGE, 상황 STATUS)는 관측 시점(as_of, 없으면 시작 시점)까지만 확인된 것으로 보고,
      기준일이 그 뒤면 STALE 로 둔다. 종료 시점이 없다는 이유로 기준일까지 자동 연장하지 않는다.
    - 이미 일어난 일회성 사건·실적(ACTUAL, 설비 상태 없음)은 기준일 전이면 PAST_EVENT(과거 사례)로 둔다.
    - 가동(OPERATING / RAMP_UP)처럼 지속되는 상태와 시작 시점이 있는 계약은 종료 근거가 없으면 ACTIVE.
    """
    entry = FactTimelineEntry(fact_id=fact.fact_id, entity=fact.entity, asset_status=fact.asset_status)
    start = parse_period(fact.valid_from)
    as_of = parse_period(fact.as_of)

    decided = _by_bounds(entry, fact, start, parse_period(fact.valid_to), target)
    if decided is not None:
        return decided
    if _is_transient(fact):
        return _transient_without_end(entry, fact, start, as_of, target)
    if _is_one_off_event(fact):
        return _one_off_event(entry, fact, start or as_of, target)
    if start is not None:
        return _entry(entry, TemporalStatus.ACTIVE, f"시작 시점 {fact.valid_from} ≤ 기준일 {target}")
    if fact.asset_status in _DURABLE_STATUSES:
        if as_of is not None and as_of[0] > target:
            return _entry(entry, TemporalStatus.UNCERTAIN, f"상태 기준 시점 {fact.as_of} 이 기준일 {target} 이후")
        return _entry(entry, TemporalStatus.ACTIVE, f"{fact.asset_status.value} 상태(시작 시점 미상)")
    if fact.asset_status in _NOT_STARTED_STATUSES:
        return _entry(entry, TemporalStatus.UNCERTAIN, f"{fact.asset_status.value} 상태이나 개시 시점 미상")
    return _entry(entry, TemporalStatus.UNKNOWN, "시점 정보 없음")


def build_timeline(facts: list[EvidencedFact], target: date) -> list[FactTimelineEntry]:
    """시점 판정이 의미 있는 사실(시점·설비 상태가 있거나 상황 STATUS 인 사실)만 기준일 시점표로 만든다."""
    return [
        evaluate_fact(fact, target)
        for fact in facts
        if fact.valid_from
        or fact.valid_to
        or fact.asset_status is not AssetStatus.NOT_APPLICABLE
        or fact.fact_kind is FactKind.STATUS
    ]
