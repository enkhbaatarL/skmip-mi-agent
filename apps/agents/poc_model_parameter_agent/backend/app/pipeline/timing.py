from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

FULL_RANGE = re.compile(r"(?P<sy>\d{4})년\s*(?P<sm>\d{1,2})월부터\s*(?:(?P<ey>\d{4})년\s*)?(?P<em>\d{1,2})월")
SINGLE_MONTH = re.compile(r"(?P<y>\d{4})년\s*(?P<m>\d{1,2})월")
ISO_RANGE = re.compile(r"(?P<sy>\d{4})-(?P<sm>\d{2})\s*(?:to|:|~)\s*(?P<ey>\d{4})-(?P<em>\d{2})")


@dataclass(frozen=True)
class MonthRange:
    start: date
    end: date

    @property
    def start_key(self) -> str:
        return self.start.strftime("%Y-%m")

    @property
    def end_key(self) -> str:
        return self.end.strftime("%Y-%m")


def month_date(year: int, month: int) -> date:
    if not 1 <= month <= 12:
        raise ValueError("월은 1부터 12 사이여야 합니다.")
    return date(year, month, 1)


def add_months(value: date, offset: int) -> date:
    month_index = value.year * 12 + value.month - 1 + offset
    return date(month_index // 12, month_index % 12 + 1, 1)


def months_between(start: date, end: date) -> list[date]:
    if end < start:
        raise ValueError("종료 월이 시작 월보다 빠릅니다.")
    result: list[date] = []
    current = start
    while current <= end:
        result.append(current)
        current = add_months(current, 1)
    return result


def parse_month_range(text: str) -> MonthRange | None:
    try:
        normalized = text.strip()
        match = FULL_RANGE.search(normalized)
        if match:
            start_year = int(match.group("sy"))
            end_year = int(match.group("ey") or start_year)
            start = month_date(start_year, int(match.group("sm")))
            end = month_date(end_year, int(match.group("em")))
            if end < start and match.group("ey") is None:
                end = month_date(start_year + 1, int(match.group("em")))
            if end < start:
                return None
            return MonthRange(start, end)
        match = ISO_RANGE.search(normalized)
        if match:
            start = month_date(int(match.group("sy")), int(match.group("sm")))
            end = month_date(int(match.group("ey")), int(match.group("em")))
            return MonthRange(start, end) if end >= start else None
        match = SINGLE_MONTH.search(normalized)
        if match:
            value = month_date(int(match.group("y")), int(match.group("m")))
            return MonthRange(value, value)
    except ValueError:
        return None
    return None


def ramp_factor(month_index: int, total_months: int) -> float:
    if total_months <= 1:
        return 1.0
    if month_index == 0:
        return 0.5
    if month_index == total_months - 1:
        return 0.75
    return 1.0


def recovery_factor(recovery_index: int, recovery_months: int) -> float:
    if recovery_months <= 0 or recovery_index < 1 or recovery_index > recovery_months:
        return 0.0
    return (recovery_months - recovery_index + 1) / (recovery_months + 1)


def month_label(value: date) -> str:
    return f"{value.year}년 {value.month}월"


def days_in_month(value: date) -> int:
    return calendar.monthrange(value.year, value.month)[1]
