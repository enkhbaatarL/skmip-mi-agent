from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from dateutil.relativedelta import relativedelta

from apps.common.configs.config import Settings, get_settings


def now(*, timespec: str = "auto") -> str:
    settings: Settings = get_settings()
    return datetime.now(ZoneInfo(settings.time_zone)).isoformat(timespec=timespec)


def today(*, fmt: str = "%Y-%m-%d") -> str:
    settings: Settings = get_settings()
    return datetime.now(ZoneInfo(settings.time_zone)).strftime(fmt)


def prior_year_period(
    current_start: str,
    *,
    fmt: str = "%Y-%m-%d",
) -> tuple[str, str]:
    curr_start = datetime.strptime(current_start, fmt)
    past_end = curr_start - timedelta(days=1)
    past_start = past_end - relativedelta(years=1)
    return past_start.strftime(fmt), past_end.strftime(fmt)
