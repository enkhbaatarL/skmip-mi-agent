"""분석 프롬프트 빌더.

시계열 판정 로직과 프롬프트 조립을 담당합니다.
"""
from __future__ import annotations

import ast
import json
import re
from datetime import datetime
from typing import Any

from apps.agents.mi_agent.prompts.loader import load_prompt
from apps.agents.mi_agent.prompts.language_translation import (
    build_language_translation_prompt_block,
)
from apps.common.utils.time_utils import today


_DATE_YYYYMMDD_RE = re.compile(r"^\d{8}$")
_DATE_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_SLASH_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")
_DATE_DOT_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2}$")


def _parse_metric_data_loose(raw: str) -> Any:
    """metric_data는 JSON 문자열 또는 Python repr 문자열일 수 있으므로 느슨하게 파싱."""
    raw = (raw or "").strip()
    if not raw:
        return None

    # 1) JSON
    try:
        return json.loads(raw)
    except Exception:
        pass

    # 2) 따옴표로 감싸진 JSON
    stripped = raw.strip().strip("'\"")
    if stripped and stripped != raw:
        try:
            return json.loads(stripped)
        except Exception:
            pass

    # 3) Python repr
    return ast.literal_eval(raw)


def _coerce_metric_data(metric_data: Any) -> Any:
    """metric_data가 문자열이면 느슨하게 파싱하고, 아니면 그대로 반환."""
    if metric_data is None:
        return None
    if isinstance(metric_data, str):
        raw = metric_data.strip()
        if not raw:
            return None
        try:
            return _parse_metric_data_loose(raw)
        except Exception:
            return None
    return metric_data


def _stringify_metric_source(metric_data: Any) -> str:
    """프롬프트에 넣기 위한 문자열 변환."""
    if metric_data is None:
        return ""
    if isinstance(metric_data, str):
        return metric_data
    try:
        return json.dumps(metric_data, ensure_ascii=False)
    except Exception:
        return repr(metric_data)


def _coerce_obj(item: Any) -> Any:
    """List 원소가 dict일 수도, JSON 문자열일 수도, python repr 문자열일 수도 있음."""
    if isinstance(item, dict):
        return item
    if isinstance(item, str):
        s = item.strip()
        if not s:
            return None
        try:
            return json.loads(s)
        except Exception:
            return ast.literal_eval(s)
    return None


def _try_parse_date_value(v: Any) -> str | None:
    """값 기반 날짜 탐지.

    - ISO date/datetime: 2026-01-23, 2026-01-23 00:00:00 등
    - 슬래시/닷: 2026/01/23, 2026.01.23
    - YYYYMMDD: 20260123
    - epoch seconds/ms: 1700000000 / 1700000000000

    반환: YYYY-MM-DD 문자열(정규화) 또는 None.
    """
    if v is None:
        return None

    # 숫자형 epoch seconds/ms
    if isinstance(v, (int, float)):
        n = int(v)
        if 1_000_000_000 <= n <= 2_500_000_000:  # seconds
            try:
                dt = datetime.utcfromtimestamp(n)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return None
        if 1_000_000_000_000 <= n <= 2_500_000_000_000:  # milliseconds
            try:
                dt = datetime.utcfromtimestamp(n / 1000)
                return dt.strftime("%Y-%m-%d")
            except Exception:
                return None
        return None

    # 문자열 날짜
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None

        if _DATE_ISO_DATE_RE.match(s):
            return s
        if _DATE_SLASH_RE.match(s):
            y, m, d = s.split("/")
            return f"{y}-{m}-{d}"
        if _DATE_DOT_RE.match(s):
            y, m, d = s.split(".")
            return f"{y}-{m}-{d}"
        if _DATE_YYYYMMDD_RE.match(s):
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"

        # ISO datetime 계열
        try:
            iso = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(iso)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return None

    return None


def _try_parse_numeric_value(v: Any) -> float | None:
    """숫자/숫자문자열이면 float로 변환, 아니면 None."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        try:
            return float(s.replace(",", ""))
        except Exception:
            return None
    return None


def _find_date_key_and_value(row: dict[str, Any]) -> tuple[str | None, str | None]:
    """row에서 날짜로 해석 가능한 (key, normalized_date)을 찾는다."""
    for k, v in row.items():
        normalized = _try_parse_date_value(v)
        if normalized:
            return k, normalized
    return None, None


def _row_has_date_and_numeric_value(row: Any) -> bool:
    if not isinstance(row, dict):
        return False

    date_key, _ = _find_date_key_and_value(row)
    if not date_key:
        return False

    for k, v in row.items():
        if k == date_key:
            continue
        if _try_parse_numeric_value(v) is not None:
            return True
    return False


def _is_timeseries_metric_data(metric_data: Any) -> bool:
    """시계열 판단(보수적).

    - result가 list
    - 각 row에서 날짜로 해석 가능한 값이 존재하고
    - 그 row에 숫자 값(날짜 제외)이 존재하는 경우가 2개 이상.
    """
    parsed = _coerce_metric_data(metric_data)
    if parsed is None:
        return False

    items: list[Any]
    if isinstance(parsed, dict):
        items = [parsed]
    elif isinstance(parsed, list):
        items = parsed
    else:
        return False

    for item in items:
        obj = _coerce_obj(item)
        if not isinstance(obj, dict):
            continue

        result = obj.get("result")
        if not isinstance(result, list) or len(result) < 2:
            continue

        valid_rows = 0
        for row in result:
            if _row_has_date_and_numeric_value(row):
                valid_rows += 1
                if valid_rows >= 2:
                    return True

    return False


def build_analysis_prompt(
    metric_data: Any,
    web_results: list[str] | str | None,
    user_query_language: str | None,
    rewrite: str,
    vdb_sources: str = "",
) -> str:
    """분석 프롬프트를 조립합니다."""
    is_timeseries_metric: bool = _is_timeseries_metric_data(metric_data)
    metric_source = _stringify_metric_source(metric_data)

    if isinstance(web_results, list):
        is_fallback = (
            len(web_results) == 1
            and "검색 결과가 존재하지 않습니다." in web_results[0]
        )
        web_source = "" if is_fallback else "\n\n".join(web_results)
    elif isinstance(web_results, str):
        web_source = web_results
    else:
        web_source = ""

    lang_block: str = build_language_translation_prompt_block(
        target_lang=user_query_language,
    )

    today_ymd: str = today()

    timeseries_flag_line = load_prompt(
        "analysis",
        key="timeseries_flag",
        is_timeseries=str(is_timeseries_metric).lower(),
    )

    system_prompt = load_prompt("analysis", key="system")
    user_prompt = load_prompt(
        "analysis",
        key="user",
        today_ymd=today_ymd,
        rewrite=rewrite,
        metric_source=metric_source,
        web_source=web_source,
        vdb_source=vdb_sources,
        timeseries_flag_line=timeseries_flag_line.strip(),
        lang_block=lang_block,
    )

    return system_prompt + "\n\n" + user_prompt
