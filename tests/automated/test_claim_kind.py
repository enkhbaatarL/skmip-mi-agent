from __future__ import annotations

import pytest

from apps.agents.scenario_group_agent.utils.claim_kind import (
    classify_claim_kind,
    extract_forecast_anchors,
    forecast_values_stated_as_fact,
    split_rationale_fields,
)


# midb Event 32의 key_bullets. ①② 전망, ③④ 관측(④는 전망이 배경으로만 언급됨).
EVENT_32_PRODUCTION = (
    "10월 6일 공개된 단기 에너지 전망에서 미국 건식가스 생산은 2025년 107.6 bcfd에서 2026년 112.2 bcfd, "
    "2027년 116.1 bcfd로 증가할 것으로 제시됐다."
)
EVENT_32_CONSUMPTION = (
    "같은 전망에서 미국 국내 천연가스 소비는 2025년 91.9 bcfd에서 2026년 92.4 bcfd, 2027년 93.8 bcfd로 늘어 "
    "사상 최고치를 기록할 것으로 예상됐다."
)
EVENT_32_OBSERVED = (
    "9월 30일 기준 LSEG는 9월 미국 본토 48개 주 평균 생산이 112.2 bcfd였지만 최근 1주 평균은 약 109.4 bcfd로 "
    "낮아졌다고 제시했다."
)
EVENT_32_BACKGROUND = (
    "10월 1일 미국 천연가스 선물은 10월 중순까지 온화한 날씨가 이어질 것이라는 전망 속에 약 2% 하락해 "
    "$2.967/MMBtu로 마감했다."
)


@pytest.mark.parametrize(
    ("sentence", "expected"),
    [
        (EVENT_32_PRODUCTION, "forecast"),
        (EVENT_32_CONSUMPTION, "forecast"),
        (EVENT_32_OBSERVED, "observed"),
        (EVENT_32_BACKGROUND, "observed"),
        (
            "시장은 추가 연장 이후 지중해 공급이 감소할 것으로 예상했고 이탈리아 매수세가 회복됐다고 평가했다.",
            "forecast",
        ),
        ("전기화 확대 시 2032년 가스 수요가 259 TWh까지 낮아질 수 있다는 시나리오가 언급됨.", "forecast"),
        ("패키지를 승인했으며, 패키지는 입법원 통과 후 발효될 예정이다.", "plan"),
        ("에니와 파트너들이 개발하는 코랄 노르테는 연간 약 360만 톤의 LNG 생산을 목표로 한다.", "plan"),
        # 과거형 관형어 "감소한 것으로"는 관측 보도다.
        ("선박 운항 데이터상 해협 통과 선박 수가 2개월여 만에 최저로 감소한 것으로 제시됨.", "observed"),
        # "~할 수 있는 조건"은 미래 가능성이 아니라 계약 조건이다.
        ("낙찰 카고는 FSRU 2곳 중 한 곳에서 하역할 수 있는 조건이었다.", "observed"),
        ("**2026-10-18 독일·영국에서 풍력 절반 이하와 5℃ 한파가 겹친 상황임(가정).**", "observed"),
    ],
)
def test_classify_claim_kind_uses_predicate_not_forecast_nouns(sentence: str, expected: str) -> None:
    assert classify_claim_kind(sentence) == expected


def test_extract_forecast_anchors_excludes_past_baselines_and_observed_values() -> None:
    observed = [EVENT_32_OBSERVED, EVENT_32_BACKGROUND]

    # 2025년 값은 과거 기준값, 112.2는 같은 Event의 9월 실적과 겹치므로 전망 고유값이 아니다.
    assert extract_forecast_anchors(EVENT_32_PRODUCTION, analysis_year=2026, observed_texts=observed) == ["116.1"]
    assert extract_forecast_anchors(EVENT_32_CONSUMPTION, analysis_year=2026, observed_texts=observed) == [
        "92.4",
        "93.8",
    ]


def test_extract_forecast_anchors_skips_from_values_and_observed_clause() -> None:
    spain = "스페인 가스 수요가 2026년 312 TWh에서 2032년 284 TWh로 감소할 수 있다는 전망임."
    storage = (
        "유럽 가스 저장률은 73.61%로 통상적인 계절 수준보다 낮게 집계됐고, "
        "시장에서는 11월 1일 기준 유럽 가스 저장률이 75~78%로 예상되는 것으로 언급됨."
    )

    assert extract_forecast_anchors(spain, analysis_year=2026) == ["284"]
    assert extract_forecast_anchors(storage, analysis_year=2026) == ["78"]


def test_forecast_values_stated_as_fact_requires_missing_attribution() -> None:
    dropped = (
        "사실: 미국 국내 천연가스 소비도 2025년 91.9, 2026년 92.4, 2027년 93.8 bcfd로 증가해 생산 증가분 전부를 "
        "LNG 원료가스로 볼 수 없음 | 가정: 국내에서 흡수 | 영향: JKM 상승 압력"
    )
    attributed = "사실: 10월 6일 전망은 소비를 2027년 93.8 bcfd로 제시함 | 가정: 국내에서 흡수 | 영향: JKM 상승"
    moved = (
        "사실: 9월 평균 생산은 112.2 bcfd | 전망: 10월 6일 단기 에너지 전망은 2027년 소비를 93.8 bcfd로 제시 | "
        "가정: 국내에서 흡수 | 영향: JKM 상승"
    )
    anchors = ["92.4", "93.8", "116.1"]

    assert forecast_values_stated_as_fact(split_rationale_fields(dropped)["사실"], anchors) == ["92.4", "93.8"]
    assert forecast_values_stated_as_fact(split_rationale_fields(attributed)["사실"], anchors) == []
    assert forecast_values_stated_as_fact(split_rationale_fields(moved)["사실"], anchors) == []
    assert "93.8" in split_rationale_fields(moved)["전망"]


@pytest.mark.parametrize("date", ["2026-11-10", "2026/11/10", "2026.11.10", "2026년 11월 10일"])
def test_forecast_quantity_does_not_match_calendar_date(date: str) -> None:
    assert forecast_values_stated_as_fact(f"{date} 현재 LNG 화물 지연은 직접 확인되지 않음", ["11", "10"]) == []
    # A real quantitative occurrence in the same sentence must still be detected.
    assert forecast_values_stated_as_fact(f"{date} 독일 태양광 발전량은 11GW다", ["11"]) == ["11"]


def test_observed_date_does_not_remove_unobserved_forecast_quantity() -> None:
    assert extract_forecast_anchors(
        "독일 태양광이 11GW로 감소할 것으로 예상됐다.",
        analysis_year=2026,
        observed_texts=["2026-11-10 현재 현물가격을 확인했다."],
    ) == ["11"]


@pytest.mark.parametrize("text", ["태양광 발전량 10~11GW", "태양광 발전량 10-11GW", "발전량 11GW와 6.3GW"])
def test_forecast_quantity_ranges_remain_detectable(text: str) -> None:
    assert forecast_values_stated_as_fact(text, ["11"]) == ["11"]
