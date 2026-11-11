from __future__ import annotations

from collections.abc import Iterable, Sequence
import re
from typing import Literal


ClaimKind = Literal["observed", "plan", "forecast"]

# "할 것으로 예상됐다"처럼 미래형(ㄹ 받침) 관형어 뒤의 "것으로/것이라고"만 전망으로 본다.
# "감소한 것으로 제시됨"처럼 과거형 관형어는 관측 보도이므로 제외한다.
_FUTURE_THAT_PATTERN = re.compile(r"([가-힣])\s*것(?:으로|이라고|이란|이라는)")
_FORECAST_PREDICATE_PATTERN = re.compile(
    r"(?:전망|예상|예측)(?:되|된|됐|됨|했|하였|한다|하며|하고)"
    r"|[가-힣]\s*전망(?:이다|임|이며|이고|이어서|이므로)"
    r"|전망\s*[.。]?\s*$"
    r"|(?:[가-힣])\s*수\s*있(?:다|음|으나|지만)"
    r"|가능성(?:이|을)?\s*(?:있|크|높|제기|우세|제시)"
    r"|전망(?:은|에서|에\s*따르면)\s.{0,80}?(?:제시|가정|예상|예측)(?:했|됐|됨|함|하였)",
)
_PLAN_PREDICATE_PATTERN = re.compile(
    r"(?:할|될)\s*예정"
    r"|(?:예정|계획)(?:이다|임|이며|이고|이었다|이었음)"
    r"|(?:추진|검토)\s*(?:한다|하고\s*있|중이|중임)"
    r"|하기로\s*(?:했|함|결정)"
    r"|목표로\s*(?:한다|함|하고)",
)
# 전망·계획이 배경으로만 언급되고 문장의 서술은 관측인 경우("…것이라는 전망 속에 하락 마감했다").
_BACKGROUND_FORECAST_PATTERN = re.compile(r"전망\s*(?:속|하에|아래)")
# 미래 가능성이 아니라 계약·설비 조건을 설명하는 "~할 수 있는 조건이었다".
_CONDITION_PATTERN = re.compile(r"수\s*있는\s*조건")

# 사실 칸·서술에서 전망임을 밝히는 표현. 이 표현이 있으면 전망 수치를 사실처럼 쓴 것으로 보지 않는다.
FORECAST_ATTRIBUTION_PATTERN = re.compile(r"전망|예상|예측|추정|제시|계획|예정|가능성|수\s*있|전제")

_UNIT = r"(?:bcfd|bcf/d|bcm|tcf|TWh|GWh|mtpa|MTPA|Mt|만\s*톤|%|MMBtu|척|카고|b/d|bpd|GW|MW)"
# "2026년 312 TWh에서 2032년 284 TWh로"의 출발값(…에서)은 비교 기준이므로 전망값에서 뺀다.
_YEAR_VALUE_PATTERN = re.compile(rf"(20\d{{2}})년(?:에는|에도|에|까지)?\s*(\d+(?:\.\d+)?)\s*{_UNIT}(?!\s*에서)")
_TARGET_VALUE_PATTERN = re.compile(rf"(\d+(?:\.\d+)?)\s*{_UNIT}\s*(?:로|으로|까지|에\s*달|수준으로)")
# 한 문장에 관측 절과 전망 절이 섞인 경우("73.61%로 집계됐고, … 75~78%로 예상") 전망 절에서만 값을 뽑는다.
# "2025년 91.9, 2026년 92.4"처럼 값을 나열하는 쉼표에서는 나누지 않고 연결어미에서만 나눈다.
_CLAUSE_SPLIT_PATTERN = re.compile(
    r"(?:(?<=[됐했였었]고)|(?<=[됐했였었]으며)|(?<=[됐했였었]며)|(?<=으나)|(?<=지만))\s*,?\s+",
)
_FIELD_LABEL_PATTERN = re.compile(r"(사실|전망|파생|가정|영향)\s*:\s*")
# A quantitative anchor such as 11 GW must not match the month in 2026-11-10.
# Mask complete dates only; standalone quantities and ranges remain eligible.
_CALENDAR_DATE_PATTERN = re.compile(
    r"(?<!\d)(?:\d{4}(?P<separator>[-/.])\d{1,2}(?P=separator)\d{1,2}"
    r"|\d{4}년\s*\d{1,2}월\s*\d{1,2}일)(?!\d)",
)


def _has_rieul_final(char: str) -> bool:
    code = ord(char) - 0xAC00
    return 0 <= code <= 11171 and code % 28 == 8


def _normalize(text: str) -> str:
    return re.sub(r"\*\*", "", text or "").strip()


def classify_claim_kind(text: str) -> ClaimKind:
    """Classify an Event sentence by its predicate, not by forecast nouns used as background."""
    sentence = _normalize(text)
    if not sentence:
        return "observed"
    if any(_has_rieul_final(match.group(1)) for match in _FUTURE_THAT_PATTERN.finditer(sentence)):
        tail = sentence[sentence.find("것") :]
        if not _BACKGROUND_FORECAST_PATTERN.search(tail[:20]):
            return "forecast"
    forecast_match = _FORECAST_PREDICATE_PATTERN.search(sentence)
    if forecast_match and not _CONDITION_PATTERN.search(sentence[forecast_match.start() : forecast_match.end() + 6]):
        return "forecast"
    if _PLAN_PREDICATE_PATTERN.search(sentence):
        return "plan"
    return "observed"


def extract_forecast_anchors(
    text: str,
    *,
    analysis_year: int,
    observed_texts: Iterable[str] = (),
) -> list[str]:
    """Return forecast values (e.g. '93.8') that are not past-year baselines or observed values of the Event."""
    sentence = _normalize(text)
    clauses = [clause for clause in _CLAUSE_SPLIT_PATTERN.split(sentence) if clause.strip()]
    forecast_clauses = [clause for clause in clauses if classify_claim_kind(clause) == "forecast"]
    # 전망 서술어가 절 경계에 걸쳐 절 단위로 판정되지 않으면 문장 전체를 전망 절로 본다.
    scope = " ".join(forecast_clauses) if forecast_clauses else sentence
    past_values = {value for year, value in _YEAR_VALUE_PATTERN.findall(sentence) if int(year) < analysis_year}
    candidates = [value for year, value in _YEAR_VALUE_PATTERN.findall(scope) if int(year) >= analysis_year]
    candidates.extend(_TARGET_VALUE_PATTERN.findall(scope))
    observed_blob = " ".join(_normalize(item) for item in observed_texts)
    anchors: list[str] = []
    for value in candidates:
        if value in past_values or value in anchors:
            continue
        # 같은 Event의 관측 문장에도 나오는 값(예: 9월 실적 112.2 bcfd)은 전망 고유값으로 볼 수 없다.
        if _contains_value(observed_blob, value):
            continue
        anchors.append(value)
    return anchors


def _contains_value(text: str, value: str) -> bool:
    quantitative_text = _CALENDAR_DATE_PATTERN.sub(" ", text)
    return bool(re.search(rf"(?<![\d.]){re.escape(value)}(?![\d])", quantitative_text))


def split_rationale_fields(text: str) -> dict[str, str]:
    """Split a Choice why written as '사실: … | 전망: … | 가정: …' into labelled fields."""
    fields: dict[str, str] = {}
    for part in (text or "").split("|"):
        match = _FIELD_LABEL_PATTERN.match(part.strip())
        if match:
            fields[match.group(1)] = part.strip()[match.end() :].strip()
    return fields


def forecast_values_stated_as_fact(text: str, anchors: Sequence[str]) -> list[str]:
    """Return forecast anchors that appear in text without any forecast attribution."""
    if not text or FORECAST_ATTRIBUTION_PATTERN.search(text):
        return []
    return [anchor for anchor in anchors if _contains_value(text, anchor)]


__all__ = [
    "FORECAST_ATTRIBUTION_PATTERN",
    "ClaimKind",
    "classify_claim_kind",
    "extract_forecast_anchors",
    "forecast_values_stated_as_fact",
    "split_rationale_fields",
]
