"""가격지수(index) 고정 상수와 해석용 LLM 소프트 힌트.

지수(JKM/TTF/HH)와 그 순서(INDEX_ORDER)는 절대 바뀌지 않는 안전한 index-keyed
상수이므로 코드에 고정한다. 반면 지역(country/region/continent) → 지수의 하드 매핑은
입력 geo 라벨의 종류가 다양해 정확일치가 조용히 실패(index=None)하고 feature가
엉뚱한 버킷으로 새는 리스크가 있어 코드에서 제거했다.

feature의 시장(지수) 연결은 더 이상 코드가 결정하지 않고, feature에 실린 geo
라벨을 그대로 LLM에 넘겨 추론에 위임한다. 아래 INDEX_MARKET_LABEL / INDEX_GROUPS /
market_label()은 '코드 로직 분기'가 아니라 프롬프트에 넣는 'LLM 소프트 힌트 텍스트'
용도로만 사용한다.
"""

from __future__ import annotations

BASE_SCENARIO_ID = "MI Base"

# 해석 대상 가격지수 순서(출력 정렬 기준). 절대 변경 금지.
INDEX_ORDER: tuple[str, ...] = ("JKM", "TTF", "HH")

# 지수 → 사람이 읽는 시장 라벨. LLM 소프트 힌트 전용(코드 분기 아님).
INDEX_MARKET_LABEL: dict[str, str] = {
    "JKM": "아시아(한국)",
    "TTF": "유럽(네덜란드)",
    "HH": "미국",
}

# 지수 → 모델 실행 결과(tmd_mdl_scnrcaseprcl.prc_rgn_nm) 조회 키.
# index-keyed 안전 상수(가격 결과는 항상 monthly, perd_unit_spt_cd='M').
INDEX_PRICE_REGION: dict[str, str] = {
    "JKM": "East Asia Spot",
    "TTF": "TTF",
    "HH": "HH",
}

# 시장 반응 성격 묶음. LLM 소프트 힌트 전용(코드 분기 아님).
# 수입 파리티 시장(아시아·유럽)과 미국 내수 시장의 반응 성격이 달라 분리한다.
INDEX_GROUPS: list[dict[str, object]] = [
    {"label": "아시아·유럽 (JKM·TTF)", "indices": ["JKM", "TTF"]},
    {"label": "미국 (HH)", "indices": ["HH"]},
]

PRICE_UNIT = "$/MMBtu"


def market_label(index: str) -> str:
    """지수의 사람이 읽는 시장 라벨(LLM 소프트 힌트 전용)."""
    return INDEX_MARKET_LABEL.get(index, index)
