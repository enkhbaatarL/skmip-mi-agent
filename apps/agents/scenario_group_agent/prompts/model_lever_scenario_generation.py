from __future__ import annotations

import json
from typing import Any


MODEL_LEVER_SYSTEM_PROMPT = """\
당신은 복수의 MI Event를 공동 전제로 LNG 가격 시나리오를 설계하는 전문가입니다.

입력 Event는 현재 사건에 관한 권위 있는 사실입니다. Event Type은 분류 정보일 뿐,
Template이나 dimension을 선택하는 키로 사용하지 마십시오.

Model Impact Lever Catalog는 시나리오가 참조할 수 있는 영향 경로의 폐쇄 목록입니다.
카탈로그에 없는 leverCode나 모델 파라미터를 만들지 마십시오. parameterBindings는 모델
연결 가능성을 설명하는 참고 정보이며, 시나리오에 모델 파라미터 값을 직접 만들지 마십시오.

작업 순서:
1. 각 Event의 사실이 demand, supply, trade 또는 price_only lever에 미치는 방향과 근거를
   EventImpactFact로 정리합니다. 선택한 모든 Event를 빠짐없이 다룹니다.
2. Event 간 증폭, 상쇄, 인과 연결, 지역 결합 또는 독립 관계를 식별합니다.
3. Catalog의 모든 lever를 검토한 뒤, LNG 가격 결과를 실질적으로 바꾸고 사용자가 확인할
   가치가 있는 불확실성만 3~6개의 dimension으로 만듭니다. 관련 없는 lever나 확정 사실
   자체는 dimension으로 만들지 않습니다.
4. dimension마다 2~4개의 상호 배타적 value를 만듭니다. value는 magnitude, scope,
   timing, recovery, mitigation, interaction 중 하나의 불확실성을 구체적으로 나타냅니다.
5. Cartesian product 대신 글로벌 LNG 가격 압력이 서로 다른 3~5개의 대표 Scenario를
   직접 설계합니다.

모든 dimension은 sourceEventIds와 leverRefs를 가져야 합니다. 선택한 Event는 적어도 하나의
dimension에 연결되어야 합니다. 모델 연결이 없는 price_only 또는 known_unsupported lever도
가격 시나리오에 중요하면 사용할 수 있으며, 이를 숨기거나 실행 가능한 파라미터로 꾸미지 마십시오.
단, 전체 dimension 중 적어도 하나는 supportStatus가 executable인 parameterBinding을 가진
lever를 참조해야 합니다. executable 경로와 가격 설명용 비입력 경로를 함께 사용할 수 있습니다.

Scenario는 strong_bullish, bullish, balanced, bearish, strong_bearish 중 서로 다른 구간을
사용합니다. 생성하지 않은 구간은 excludedScenarios에 이유를 남겨, 생성 및 제외 결과를 합쳐
다섯 구간을 정확히 한 번씩 다룹니다. 최저 구간은 floor, 최고 구간은 ceiling이 되며, 내부 구간
중 하나는 상승·하락 요인이 함께 있는 mixed Scenario여야 합니다. probabilityScore는 선택된
Event가 모두 발생한다는 전제하에서 Scenario 전개의 상대적 개연성입니다.

relatedMarkets는 글로벌 압력과 별개의 가격 방향 또는 Scenario role이 아닙니다. 해당 Scenario의
dimension 조합이 JKM, TTF, HH 중 특정 지역 가격 허브와 특별히 관련될 때만 market과 한국어
rationale을 추가하십시오. 글로벌 영향만 있거나 지역 특이성이 명확하지 않으면 빈 배열로 두고,
단순히 가능한 모든 시장을 채우지 마십시오.

모든 설명, 근거, label은 한국어로 작성하십시오.
"""


def build_model_lever_user_prompt(
    *,
    events: list[dict[str, Any]],
    impact_levers: list[dict[str, Any]],
    catalog_version: str,
    validation_feedback: str | None = None,
) -> str:
    event_context = [
        {
            "eventId": event.get("mi_event_id"),
            "eventTypeL2Id": event.get("event_type_l2_id"),
            "title": event.get("event_title_ko"),
            "summary": event.get("one_line_summary"),
            "occurredAt": event.get("occurred_at"),
            "keyFacts": event.get("key_bullets") or [],
            "detailAnalysis": event.get("detail_analysis"),
            "tags": event.get("tags") or [],
        }
        for event in events
    ]
    catalog = [
        {
            "leverCode": lever.get("lever_code"),
            "domain": lever.get("domain"),
            "label": lever.get("label"),
            "description": lever.get("description"),
            "applicabilityHint": lever.get("applicability_hint"),
            "parentLeverCode": lever.get("parent_lever_code"),
            "parameterBindings": [
                {
                    "parameterName": binding.get("parameter_name"),
                    "role": binding.get("role"),
                    "applicability": binding.get("applicability"),
                    "supportStatus": binding.get("support_status"),
                    "unsupportedReasonCode": binding.get(
                        "unsupported_reason_code",
                    ),
                }
                for binding in lever.get("parameter_bindings") or []
            ],
        }
        for lever in impact_levers
    ]
    feedback = (
        f"\n## 이전 의미 검증 실패\n- {validation_feedback}\n- 계약 위반을 수정한 전체 결과를 다시 작성하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        f"## Impact Catalog Version\n{catalog_version}\n\n"
        "## Event Context\n"
        f"{json.dumps(event_context, ensure_ascii=False, indent=2)}\n\n"
        "## Model Impact Lever Catalog\n"
        f"{json.dumps(catalog, ensure_ascii=False, indent=2)}\n\n"
        "## 출력 세부 규칙\n"
        "- dimensionId는 영문 snake_case로 작성하십시오.\n"
        "- displayOrder는 1부터 순서대로 부여하십시오.\n"
        "- required는 사용자 확인이 필요한 dimension이면 true로 설정하십시오.\n"
        "- valueKind와 dimensionType을 반드시 지정하십시오.\n"
        "- sourceRefs는 비워 두고 sourceEventIds와 leverRefs로 출처를 표현하십시오.\n"
        "- modelSupportStatus는 비워 두십시오. 서버가 카탈로그로 계산합니다.\n"
        "- 적어도 하나의 dimension은 executable parameterBinding이 있는 lever를 참조하십시오.\n"
        "- dimensionValues의 key는 모든 dimensionId와 정확히 일치해야 합니다.\n"
        "- 각 선택값은 해당 dimension의 valueId 또는 label 중 하나여야 합니다.\n"
        "- globalPressureRationale은 Event→lever→글로벌 LNG 가격 압력을 설명하십시오.\n"
        "- relatedMarkets는 해당 Scenario에서 지역 특이성이 명확한 시장만 포함하십시오.\n"
        "- relatedMarkets에는 시장별 bullish/bearish 또는 floor/ceiling을 만들지 마십시오.\n"
        "- mixedFactors에는 상쇄되는 상승·하락 요인을 모두 적으십시오.\n"
        f"{feedback}"
    )


__all__ = ["MODEL_LEVER_SYSTEM_PROMPT", "build_model_lever_user_prompt"]
