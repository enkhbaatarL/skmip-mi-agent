"""MI Base 대비 결정적(deterministic) 차이 지표 계산.

LLM 호출 이전에, 입력 feature(기온 등)와 예측 가격의 'base 대비 차이'를 수치로
확정한다. LLM은 이 수치를 근거로 narrative만 작성하므로 수치 환각을 방지한다.

pure-python 구현으로 외부 수치 라이브러리 의존이 없다(시계열 길이가 짧음).
"""

from __future__ import annotations

from apps.agents.interpret_agent.flows.interpret_price.schema import (
    AnomalyPoint,
    DiffPoint,
    DiffSegment,
    FeatureDiffMetric,
    FeatureSeries,
    PriceDiffMetric,
    PriceSeries,
)

# feature별 고정 임계값(단위는 해당 feature 단위).
# 등록되지 않은 신규 feature는 diff 분포에서 임계값을 자동 산출한다(최소 하드코딩).
FEATURE_THRESHOLDS: dict[str, dict[str, float]] = {
    "Temperature": {"notable": 2.0, "extreme": 6.0, "convergence": 1.0},
    "PowerMix": {"notable": 1.0, "extreme": 3.0, "convergence": 0.5},
}

# 가격 이상치/수렴 판정 기준
PRICE_SPIKE_PCT = 25.0  # base 대비 |차이|가 이 비율 이상이면 급등/급락 후보
PRICE_CONVERGENCE_PCT = 5.0  # 이후 전 구간 |차이|가 base의 이 비율 이내면 수렴으로 간주
PRICE_MIN_ABS_MOVE = 1.0  # 절대 $ 최소 이동폭(작은 base에서 과민 반응 방지)


def _fmt(value: float) -> str:
    """값 크기에 맞춰 유효 자리를 유지하는 표시 문자열.

    소수점 1자리 고정 시 GDP(0.003)·전원믹스 등 작은 값이 '0.0'으로 뭉개지는
    문제를 막는다. |값|<1 이면 3자리, <100 이면 1자리, 그 이상은 정수로 표기하고
    불필요한 0을 제거한다.
    """
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude < 1:
        text = f"{value:.3f}"
    elif magnitude < 100:
        text = f"{value:.1f}"
    else:
        text = f"{value:.0f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _fmt_signed(value: float) -> str:
    text = _fmt(value)
    return text if text.startswith("-") else f"+{text}"


def _resolve_thresholds(feature: str, diffs: list[float]) -> dict[str, float]:
    """등록된 feature는 고정 임계값을, 미등록 feature는 diff 분포 기반 적응 임계값을 사용."""
    if feature in FEATURE_THRESHOLDS:
        return FEATURE_THRESHOLDS[feature]
    absmax = max((abs(d) for d in diffs), default=0.0)
    if absmax <= 0.0:
        return {"notable": 0.1, "extreme": 1.0, "convergence": 0.05}
    return {
        "notable": round(absmax * 0.3, 3),
        "extreme": round(absmax * 0.8, 3),
        "convergence": round(absmax * 0.15, 3),
    }


def _align(
    base_months: list[str],
    base_values: list[float],
    months: list[str],
    values: list[float],
) -> tuple[list[str], list[float], list[float]]:
    """공통 월 기준으로 base/scenario 값을 정렬해 반환."""
    base_map = dict(zip(base_months, base_values))
    scen_map = dict(zip(months, values))
    common = [m for m in months if m in base_map]
    return (
        common,
        [base_map[m] for m in common],
        [scen_map[m] for m in common],
    )


def _find_segments(
    months: list[str],
    diffs: list[float],
    notable: float,
) -> list[DiffSegment]:
    """|diff| >= notable 이고 부호가 같은 연속 구간을 추출."""
    segments: list[DiffSegment] = []
    start: int | None = None
    sign = 0
    for i, d in enumerate(diffs):
        cur_sign = 1 if d > 0 else (-1 if d < 0 else 0)
        active = abs(d) >= notable and cur_sign != 0
        if active and (start is None or cur_sign == sign):
            if start is None:
                start = i
                sign = cur_sign
        else:
            if start is not None:
                segments.append(_build_segment(months, diffs, start, i - 1))
            if active:
                start = i
                sign = cur_sign
            else:
                start = None
                sign = 0
    if start is not None:
        segments.append(_build_segment(months, diffs, start, len(diffs) - 1))
    return segments


def _build_segment(
    months: list[str], diffs: list[float], s: int, e: int
) -> DiffSegment:
    window = diffs[s : e + 1]
    peak_rel = max(range(len(window)), key=lambda k: abs(window[k]))
    peak_idx = s + peak_rel
    return DiffSegment(
        start=months[s],
        end=months[e],
        direction="above" if diffs[peak_idx] > 0 else "below",
        peak_month=months[peak_idx],
        peak_diff=round(diffs[peak_idx], 3),
    )


def _convergence_month(
    months: list[str], diffs: list[float], tol: float
) -> str | None:
    """이후 전 구간의 |diff|가 tol 이내로 유지되기 시작하는 최초 월."""
    n = len(diffs)
    for i in range(n):
        if all(abs(d) <= tol for d in diffs[i:]):
            # 시작(i=0)부터 이미 작으면 '수렴'이라 부르지 않음
            return months[i] if i > 0 else None
    return None


def _diff_point(months: list[str], base: list[float], scen: list[float], i: int) -> DiffPoint:
    return DiffPoint(
        month=months[i],
        diff=round(scen[i] - base[i], 3),
        base_value=round(base[i], 3),
        scenario_value=round(scen[i], 3),
    )


def analyze_feature_diff(
    feature_series: FeatureSeries,
    base_series: FeatureSeries,
) -> FeatureDiffMetric:
    months, base, scen = _align(
        base_series.periods, base_series.values,
        feature_series.periods, feature_series.values,
    )
    metric = FeatureDiffMetric(
        feature=feature_series.feature,
        region=feature_series.region,
        geo_level=feature_series.geo_level,
        index=feature_series.index,
        unit=feature_series.unit,
        granularity=feature_series.granularity,
        qualifier=feature_series.qualifier,
        group_keys=dict(feature_series.group_keys),
    )
    if not months:
        metric.auto_summary = "공통 구간 없음"
        return metric

    diffs = [scen[i] - base[i] for i in range(len(months))]
    thr = _resolve_thresholds(feature_series.feature, diffs)

    metric.mean_diff = round(sum(diffs) / len(diffs), 3)
    i_max = max(range(len(diffs)), key=lambda k: diffs[k])
    i_min = min(range(len(diffs)), key=lambda k: diffs[k])
    if diffs[i_max] > 0:
        metric.max_pos = _diff_point(months, base, scen, i_max)
    if diffs[i_min] < 0:
        metric.max_neg = _diff_point(months, base, scen, i_min)
    metric.notable_segments = _find_segments(months, diffs, thr["notable"])
    metric.convergence_from = _convergence_month(months, diffs, thr["convergence"])
    metric.anomalies = [
        AnomalyPoint(
            month=months[i],
            kind="extreme_diff",
            value=round(diffs[i], 3),
            detail=f"base 대비 {_fmt_signed(diffs[i])}{feature_series.unit} 극단 편차",
        )
        for i in range(len(months))
        if abs(diffs[i]) >= thr["extreme"]
    ]
    metric.auto_summary = _feature_summary(metric)
    return metric


def _feature_summary(m: FeatureDiffMetric) -> str:
    parts: list[str] = []
    if m.notable_segments:
        seg_txt = ", ".join(
            f"{s.start}~{s.end} {_fmt_signed(s.peak_diff)}{m.unit}"
            for s in m.notable_segments[:4]
        )
        parts.append(f"주요 편차 구간: {seg_txt}")
    else:
        parts.append("뚜렷한 편차 구간 없음(소폭 변동)")
    if m.convergence_from:
        parts.append(f"{m.convergence_from}부터 base 수렴")
    if m.anomalies:
        an_txt = ", ".join(f"{a.month} {_fmt_signed(a.value)}{m.unit}" for a in m.anomalies[:3])
        parts.append(f"극단 편차(이상치 후보): {an_txt}")
    return " / ".join(parts)


def analyze_price_diff(
    price_series: PriceSeries,
    base_series: PriceSeries,
) -> PriceDiffMetric:
    months, base, scen = _align(
        base_series.months, base_series.values,
        price_series.months, price_series.values,
    )
    metric = PriceDiffMetric(index=price_series.index)
    if not months:
        metric.auto_summary = "공통 구간 없음"
        return metric

    diffs = [scen[i] - base[i] for i in range(len(months))]
    metric.mean_base = round(sum(base) / len(base), 3)
    metric.mean_scenario = round(sum(scen) / len(scen), 3)
    metric.mean_diff = round(sum(diffs) / len(diffs), 3)

    i_max = max(range(len(diffs)), key=lambda k: diffs[k])
    i_min = min(range(len(diffs)), key=lambda k: diffs[k])
    if diffs[i_max] > 0:
        metric.max_pos = _diff_point(months, base, scen, i_max)
    if diffs[i_min] < 0:
        metric.max_neg = _diff_point(months, base, scen, i_min)

    # 수렴: 이후 전 구간 |diff|가 base 평균의 PRICE_CONVERGENCE_PCT% 이내
    tol = max(PRICE_MIN_ABS_MOVE, abs(metric.mean_base) * PRICE_CONVERGENCE_PCT / 100.0)
    metric.convergence_from = _convergence_month(months, diffs, tol)

    anomalies: list[AnomalyPoint] = []
    for i in range(len(months)):
        if scen[i] < 0:
            anomalies.append(
                AnomalyPoint(
                    month=months[i],
                    kind="negative_price",
                    value=round(scen[i], 3),
                    detail="예측 가격 음수(비정상)",
                )
            )
            continue
        base_ref = abs(base[i]) if base[i] != 0 else 1.0
        pct = (scen[i] - base[i]) / base_ref * 100.0
        if abs(pct) >= PRICE_SPIKE_PCT and abs(diffs[i]) >= PRICE_MIN_ABS_MOVE:
            anomalies.append(
                AnomalyPoint(
                    month=months[i],
                    kind="spike",
                    value=round(diffs[i], 3),
                    detail=f"base 대비 {pct:+.0f}% 급변",
                )
            )
    metric.anomalies = anomalies
    metric.auto_summary = _price_summary(metric)
    return metric


def _price_summary(m: PriceDiffMetric) -> str:
    parts = [
        f"평균 {_fmt(m.mean_scenario)} vs base {_fmt(m.mean_base)} ({_fmt_signed(m.mean_diff)})"
    ]
    if m.max_pos:
        parts.append(
            f"최대 상승 {m.max_pos.month} {_fmt(m.max_pos.scenario_value)} vs {_fmt(m.max_pos.base_value)}"
        )
    if m.max_neg:
        parts.append(
            f"최대 하락 {m.max_neg.month} {_fmt(m.max_neg.scenario_value)} vs {_fmt(m.max_neg.base_value)}"
        )
    if m.convergence_from:
        parts.append(f"{m.convergence_from}부터 수렴")
    if m.anomalies:
        an_txt = ", ".join(f"{a.month} {a.kind}" for a in m.anomalies[:3])
        parts.append(f"이상치: {an_txt}")
    return " / ".join(parts)
