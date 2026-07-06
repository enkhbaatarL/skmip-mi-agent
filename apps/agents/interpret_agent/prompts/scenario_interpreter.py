"""시나리오별 '동일 구조' 해석 프롬프트 및 structured output schema.

여러 입력 feature(기온·전원믹스 등)의 움직임과 예측 가격을 종합해,
입력 국면 → 가격 성격 → 지역 반응 → base 복귀 → 신뢰도 → 실무 대응의
동일한 논리 전개로 서술한다. 지역별 특징은 별도 섹션이 아니라 해석 안에 녹인다.
MI Base 자체 수치는 단독 나열하지 않고 항상 'base 대비' 관점으로만 언급한다.

지수(price)는 항상 clean하므로 INDEX_ORDER 순서로 지수별 근거를 구성한다. 반면
feature는 코드가 지수 버킷으로 강제 편입하지 않고 각자의 geo 라벨과 함께 flat하게
나열하며, geo↔지수 연결은 프롬프트의 소프트 힌트로 LLM 추론에 위임한다.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field

from apps.agents.interpret_agent.flows.interpret_price.schema import (
    FeatureDiffMetric,
    PriceDiffMetric,
)
from apps.agents.interpret_agent.utils.region_index import (
    INDEX_GROUPS,
    INDEX_MARKET_LABEL,
    INDEX_ORDER,
    market_label,
)


class ScenarioComparisonLLMOutput(BaseModel):
    identity: str = Field(
        description="굵게 표기되는 시나리오 헤드라인 한 문장(예: '2023년 말 극단 온난 뒤 2024년 한파와 가스발전 비중 확대가 겹친 급반전')"
    )
    driver_phase: str = Field(
        description="동인 및 국면. 여러 feature 움직임을 시장(아시아·유럽/미국)별로 종합하고 수렴 시점을 포함"
    )
    price_character: str = Field(
        description="가격 특성. 지역별 가격 반응과 정상화 시점, 평균 착시 여부를 포함"
    )
    summary: str = Field(
        description="시나리오 요약 한 단락. 신뢰도(데이터 품질)와 실무 대응 권고를 포함"
    )


SYSTEM_PROMPT = (
    "당신은 LNG 시장 애널리스트입니다. 수급모델의 여러 입력 feature(기온, 전원믹스 등) "
    "변화가 예측 가격에 어떻게 이어지는지 종합적으로 해석합니다. 항상 'MI Base 대비' "
    "관점으로 서술하고, Base 자체 절대 수치를 단독 나열하지 않습니다."
)


def _feature_evidence(m: FeatureDiffMetric) -> dict:
    return {
        "granularity": m.granularity,
        "unit": m.unit,
        "mean_diff": m.mean_diff,
        "max_pos": m.max_pos.model_dump() if m.max_pos else None,
        "max_neg": m.max_neg.model_dump() if m.max_neg else None,
        "notable_segments": [s.model_dump() for s in m.notable_segments],
        "convergence_from": m.convergence_from,
        "anomalies": [a.model_dump() for a in m.anomalies],
        "summary": m.auto_summary,
    }


def _price_evidence(m: PriceDiffMetric) -> dict:
    return {
        "mean_base": m.mean_base,
        "mean_scenario": m.mean_scenario,
        "mean_diff": m.mean_diff,
        "max_pos": m.max_pos.model_dump() if m.max_pos else None,
        "max_neg": m.max_neg.model_dump() if m.max_neg else None,
        "convergence_from": m.convergence_from,
        "anomalies": [a.model_dump() for a in m.anomalies],
        "summary": m.auto_summary,
    }


def _prices_by_index(price_metrics: list[PriceDiffMetric]) -> list[dict]:
    """지수는 항상 clean하므로 INDEX_ORDER 순서로 지수별 price 근거를 구성."""
    by_index = {m.index: m for m in price_metrics}
    ordered = [ix for ix in INDEX_ORDER if ix in by_index]
    ordered += [ix for ix in by_index if ix not in INDEX_ORDER]
    return [
        {
            "index": ix,
            "market_hint": market_label(ix),
            **_price_evidence(by_index[ix]),
        }
        for ix in ordered
    ]


def _features_flat(feature_metrics: list[FeatureDiffMetric]) -> list[dict]:
    """feature를 지수로 그룹핑하지 않고 각자의 geo 라벨과 함께 flat하게 나열."""
    return [
        {
            "feature": fm.label,
            "geo_label": fm.region or "지역 미상",
            "geo_level": fm.geo_level,
            # 상류가 명시적으로 지수를 준 경우만 존재. 없으면 None(코드가 매핑 안 함).
            "index_hint": fm.index,
            **_feature_evidence(fm),
        }
        for fm in feature_metrics
    ]


def build_user_prompt(
    scenario_id: str,
    feature_metrics: list[FeatureDiffMetric],
    price_metrics: list[PriceDiffMetric],
    data_quality: list[str],
) -> str:
    prices = _prices_by_index(price_metrics)
    features = _features_flat(feature_metrics)
    group_labels = [g["label"] for g in INDEX_GROUPS]

    return f"""[대상 시나리오] {scenario_id} (MI Base 대비 해석)

[예측 가격 근거 — 지수별(clean), 수치는 그대로만 인용]
{json.dumps(prices, ensure_ascii=False, indent=2)}

[입력 feature 근거 — 각 feature의 지역 라벨(geo_label) 동반, 수치는 그대로만 인용]
{json.dumps(features, ensure_ascii=False, indent=2)}

[지역↔시장(지수) 연결 지침 — 코드가 강제하지 않으니 아래를 참고해 직접 추론]
- 지수별 시장: {json.dumps(INDEX_MARKET_LABEL, ensure_ascii=False)} (JKM=아시아, TTF=유럽, HH=미국).
- 각 feature의 geo_label(예: South Korea/Asia/한국)을 보고 가장 적절한 지수와 연결해 해석하세요.
- 라벨이 모호하거나 특정 지수로 귀속하기 어려우면 무리하지 말고 '시장 공통 영향'으로 서술하세요.
- geo_label이 '지역 미상'이면 지역 미상으로 두고 시장 공통 영향으로 서술하세요.
- index_hint가 있으면 해당 지수를 우선 존중하세요.

[시스템 사전 감지 데이터 품질 신호]
{json.dumps(data_quality, ensure_ascii=False)}

[해석에 반영할 시장 묶음(아시아·유럽 / 미국의 반응 차이를 서술에 녹일 것)]
{json.dumps(group_labels, ensure_ascii=False)}

[작성 규칙 — 아래 톤/구성의 애널리스트 보고서 문체]
- driver_phase/price_character/summary의 모든 문장은 친절하고 정중한 '-합니다/-됩니다'체로
  끝맺습니다(개조식·명사종결·반말 금지). identity는 예외로 헤드라인 명사구로 둡니다.
- 모든 서술은 'MI Base 대비' 관점. Base 절대값 단독 나열 금지.
- identity: 시나리오를 규정하는 굵은 헤드라인 한 문장(원인→결과가 드러나게).
- driver_phase(동인 및 국면):
  * 여러 feature(기온, 전원믹스 등)의 움직임을 '함께' 엮어 수요·가격 방향을 설명한다.
  * 아시아·유럽과 미국을 나눠 서술하고, 각 시장의 수렴 시점(있으면 월, 없으면 '명시적 수렴 시점 없음')을 포함한다.
  * 핵심 수치는 근거 값만 인용(예: +8.0°C, -5.3°C, 가스 전원믹스 +2.0%).
- price_character(가격 특성):
  * 아시아·유럽 vs 미국의 가격 반응 차이를 드러낸다(예: JKM +6.6달러, TTF +6.5달러, HH 소폭).
  * 음수·급등이 상쇄되어 평균 차이가 착시로 보이는 경우 명시하고, 정상화(수렴) 시점을 언급한다.
- summary(시나리오 요약): 한 단락으로 (1) 시나리오 성격 재확인, (2) 신뢰도(이상치 있으면 낮음/참고용,
  물리적으로 설명되면 높음/즉시 활용), (3) 실무 대응(무엇을 점검/헤지/채택할지)을 자연스럽게 녹인다.
- 수치는 소수점 1자리까지. 과도한 나열보다 '두 자릿수 급등', '소폭', '음수' 같은 성격 위주로.

[분량 제한 — 반드시 준수]
- identity: 공백 포함 45자 이내의 헤드라인 한 문장.
- driver_phase: 2~3문장, 공백 포함 220자 이내.
- price_character: 2~3문장, 공백 포함 220자 이내.
- summary: 2~3문장, 공백 포함 260자 이내.

[출력 JSON 필드] identity, driver_phase, price_character, summary
순수 JSON 객체만 반환하세요."""
