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


IDENTITY_MAX_CHARS = 70
DRIVER_PHASE_MAX_CHARS = 340
PRICE_CHARACTER_MAX_CHARS = 340
SUMMARY_MAX_CHARS = 420


class ScenarioComparisonLLMOutput(BaseModel):
    identity: str = Field(
        description=(
            "Markdown/HTML 서식 없는 일반 텍스트 시장 판단 헤드라인. 핵심 원인과 지수별 가격 방향을 한 문장으로 압축"
        )
    )
    driver_phase: str = Field(
        description=(
            "Markdown/HTML 서식 없는 일반 텍스트 동인 및 국면. "
            "입력 변화에서 물리적 수급과 지역별 가격으로 이어지는 전이 경로를 설명"
        )
    )
    price_character: str = Field(
        description=(
            "Markdown/HTML 서식 없는 일반 텍스트 가격 특성. "
            "지수별 상대 민감도, 최대·평균 변화, 비동조와 정상화 시점을 포함"
        )
    )
    summary: str = Field(
        description=(
            "Markdown/HTML 서식 없는 일반 텍스트 결론. 핵심 market call, 방향·수치 신뢰도, "
            "근거 기반 모니터링 항목과 조건부 실무 대응을 포함"
        )
    )


SYSTEM_PROMPT = (
    "당신은 LNG 실물·트레이딩·리스크 의사결정을 지원하는 시니어 시장 애널리스트입니다. "
    "수급모델의 입력 feature 변화가 물리적 공급·수요를 거쳐 JKM·TTF·HH 가격에 전달되는 경로를 "
    "근거 안에서 해석하고, 시장 구조와 실행 시사점을 선명하게 제시합니다. 항상 'MI Base 대비' "
    "관점으로 서술하고 Base 자체 절대 수치를 단독 나열하지 않습니다. 수치를 나열하는 데 그치지 말고 "
    "원인, 전이 경로, 가격 비동조 또는 수렴, 신뢰도, 조건부 대응이 이어지는 전문 리포트로 씁니다. "
    "근거에 없는 사건·회사·물량·확률은 만들지 않습니다. 모든 출력 필드 값은 서식 없는 일반 텍스트로 "
    "작성하며 Markdown, HTML, 굵게·기울임·코드 서식을 사용하지 않습니다."
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
- geo_label이 '지역 미상'이면 그 문구를 반복하거나 특정 시장 원인으로 단정하지 말고, 지역 귀속 근거가 없는
  시장 공통 요인으로만 다루세요.
- index_hint가 있으면 해당 지수를 우선 존중하세요.

[시스템 사전 감지 데이터 품질 신호]
{json.dumps(data_quality, ensure_ascii=False)}

[해석에 반영할 시장 묶음(아시아·유럽 / 미국의 반응 차이를 서술에 녹일 것)]
{json.dumps(group_labels, ensure_ascii=False)}

[작성 규칙 — 아래 톤/구성의 애널리스트 보고서 문체]
- driver_phase/price_character/summary의 모든 문장은 단정적이되 과장하지 않는 '-합니다/-됩니다'체로
  끝맺습니다(개조식·명사종결·반말 금지). 같은 결론이나 수치를 필드마다 반복하지 않습니다.
- 모든 서술은 'MI Base 대비' 관점. Base 절대값 단독 나열 금지.
- 제공된 feature·가격 근거와 데이터 품질 신호만 사용합니다. 근거에 없는 사건명·회사명·정책·재고·물량·확률을
  추가하지 않으며, 인과를 확정할 수 없으면 '연결되는 구조입니다'처럼 강도를 낮춰 씁니다.
- identity: 핵심 원인과 가격 구조를 '원인 — JKM·TTF 강세, HH 약세'처럼 압축한 서식 없는 시장 판단
  헤드라인으로 씁니다. 모든 지수 방향이 근거에 있을 때만 지수명을 넣고, 문장 끝에 마침표를 붙이지 않습니다.
- driver_phase(동인 및 국면):
  * 첫 문장에서 핵심 feature의 대상·시점·방향·크기를 MI Base 대비 명확히 규정합니다.
  * 이어서 입력 변화 → 물리적 공급·수요 변화 → 지역별 가격 반응의 전이 경로를 설명합니다.
  * 여러 feature는 함께 엮되 직접 영향과 간접 영향을 구분하고, 근거가 모호한 지역 연결은 단정하지 않습니다.
  * 국면의 시작·정점·소멸 또는 정상화 시점이 근거상 뚜렷할 때만 시간 순서로 설명합니다.
- price_character(가격 특성):
  * 첫 문장에서 지수 간 상대 민감도와 강세·약세·비동조 같은 가격 구조를 먼저 판단합니다.
  * 최대 변화와 기간 평균을 함께 사용해 충격 강도와 지속성을 구분하고, 숫자는 판단을 뒷받침하는 만큼만 씁니다.
  * max_pos·max_neg의 month는 동일한 최대 편차가 여러 달 이어져도 대표 한 점만 담을 수 있습니다. 별도 지속 구간
    근거가 없으면 해당 월에 충격이 집중됐다거나 계절적 정점·유일한 피크라고 단정하지 않습니다.
  * 지수별 정상화 시점이 다르면 선후 관계를 짚고, 수렴 근거가 없으면 임의의 복귀 시점을 만들지 않습니다.
  * 음수·급등이 평균에서 상쇄되면 그 착시를 설명합니다. 반응이 미미한 지수는 숫자보다 '중립에 가까움'처럼
    상대적 의미를 먼저 제시합니다.
- summary(시나리오 요약): 한 단락 안에서 다음 순서를 지킵니다.
  * 핵심 market call과 가장 중요한 가격 구조를 한 문장으로 재확인합니다.
  * 경제적 방향성의 신뢰도와 입력·가격 수치의 신뢰도를 분리해 평가합니다.
  * 데이터 품질 신호가 있으면 수치 신뢰도와 활용 범위를 낮추고, 어떤 입력이나 가격을 재검증해야 하는지 밝힙니다.
  * 제공된 feature 축과 가격 근거에서 직접 도출되는 모니터링 항목을 제시하고, 확인 결과에 따른 헤지·조달·검증
    대응을 조건부로 제안합니다. 근거에 없는 고유명사나 운영 사실을 새로 만들지 않습니다.
- 수치 표기: 근거에 실린 값의 자리수를 그대로 살려 인용한다(예: -0.5, +0.003, +0.06).
  값이 이미 소수 셋째 자리까지 있으면 그대로 쓰고, 억지로 반올림해 '+0.0'처럼 의미가 사라지는 표기는 절대 쓰지 않는다.
  변화가 사실상 없으면 '거의 변화 없음', 아주 작으면 '미미한 상향/하향'처럼 정성적으로 표현한다.
- 가격 비동조, 스프레드, 헤지, 조달 같은 시장 용어는 판단을 선명하게 할 때 사용하되 뜻 없이 장식적으로 쓰지 않습니다.
- feature 이름 뒤에 내용 없는 괄호를 붙이지 않습니다(예: 'ShippingCost()' 금지).
- 모든 JSON 문자열 값은 일반 텍스트로만 작성한다. Markdown/HTML 제목·링크·목록·강조·코드 서식을 금지하며,
  특히 **, __, backtick, #, <strong>, <b> 같은 표현용 표식을 넣지 않는다.

[분량 제한 — 반드시 준수]
- identity: 공백 포함 {IDENTITY_MAX_CHARS}자 이내의 헤드라인 한 문장.
- driver_phase: 3~4문장, 공백 포함 {DRIVER_PHASE_MAX_CHARS}자 이내.
- price_character: 3~4문장, 공백 포함 {PRICE_CHARACTER_MAX_CHARS}자 이내.
- summary: 4~5문장, 공백 포함 {SUMMARY_MAX_CHARS}자 이내.
- 근거가 부족하면 억지로 분량을 채우지 않되, 같은 말의 반복 없이 위 분석 순서를 충분히 완결합니다.

[출력 JSON 필드] identity, driver_phase, price_character, summary
각 필드 값에는 서식 문법을 넣지 말고, 순수 JSON 객체만 반환하세요."""
