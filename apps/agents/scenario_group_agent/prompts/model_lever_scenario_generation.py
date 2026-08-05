from __future__ import annotations

import json
from typing import Any

from apps.agents.scenario_group_agent.prompts.event_context import (
    format_compact_event_context,
)


MODEL_LEVER_SYSTEM_PROMPT = """\
당신은 복수의 MI Event를 공동 전제로 글로벌 LNG 가격 시나리오를 설계하는 전문가입니다.

입력 Event는 현재 사건에 관한 권위 있는 사실입니다. Event Type은 분류 정보일 뿐,
Template이나 dimension을 선택하는 키로 사용하지 마십시오.

Model Impact Lever Catalog는 시나리오가 참조할 수 있는 영향 경로의 폐쇄 목록입니다.
카탈로그에 없는 leverCode나 모델 파라미터를 만들지 마십시오. 시나리오에 모델 파라미터
값을 직접 만들지 마십시오.

Dimension은 근거 추적의 정본입니다.
1. 모든 Event를 함께 읽고 LNG 가격 결과를 실질적으로 바꾸는 잔여 불확실성만 3~6개의
   dimension으로 설계합니다. 확정 사실 자체나 가격 변별력이 없는 정보는 dimension으로
   만들지 않습니다.
2. 각 dimension의 eventGroundings에 근거 Event의 observedBasis와 아직 결정되지 않은
   uncertainty를 짧게 기록합니다. 별도의 EventImpactFact나 sourceFactId를 만들지 않습니다.
3. Event 간 증폭, 상쇄, 인과 연결, 지역 결합 또는 독립 관계는 interactions에 기록합니다.
4. leverMappings에는 Catalog의 leverCode와 mappingRationale만 생성합니다. impactLeverId는
   생략할 수 있으며 서버가 Catalog 기준으로 확정합니다.
5. 각 dimension에 2~4개의 상호 배타적 value를 만들고, value마다 글로벌 가격 압력 기여와
   분기를 성립시키는 assumptionRationale을 기록합니다.
6. Cartesian product 대신 글로벌 LNG 가격 압력이 서로 다른 3~5개의 대표 Scenario를
   직접 설계합니다.

모든 Event가 반드시 별도 dimension을 가질 필요는 없습니다. 다만 만들어진 dimension의
eventGroundings에는 실제 입력 Event만 사용해야 합니다. 모델 지원 상태는 dimension 선택의
우선순위가 아닙니다. price_only 또는 현재 모델 미지원 경로도 중요한 불확실성이면 사용할 수
있으며, 이를 실행 가능한 파라미터로 꾸미지 마십시오.

Scenario는 strong_bullish, bullish, balanced, bearish, strong_bearish 중 서로 다른 구간을
사용합니다. 생성하지 않은 구간은 excludedScenarios에 이유를 남겨, 생성 및 제외 결과를 합쳐
다섯 구간을 정확히 한 번씩 다룹니다. 최저 구간은 floor, 최고 구간은 ceiling이 됩니다. 상승·하락
요인이 실제로 함께 있는 내부 구간만 mixed Scenario로 표시하며 mixed는 선택 사항입니다.
probabilityScore는 선택된 Event가 모두 발생한다는 전제하에서 Scenario 전개의 상대적 개연성입니다.

relatedMarkets는 글로벌 압력과 별개의 가격 방향 또는 Scenario role이 아닙니다. 해당 Scenario의
dimension 조합이 JKM, TTF, HH 중 특정 지역 가격 허브와 특별히 관련될 때만 market과 한국어
rationale을 추가하십시오. 글로벌 영향만 있거나 지역 특이성이 명확하지 않으면 빈 배열로 두십시오.

모든 설명, 근거, label은 한국어로 작성하십시오.
"""


def _compact_impact_catalog(impact_levers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "impactLeverId": lever.get("impact_lever_id"),
            "leverCode": lever.get("lever_code"),
            "domain": lever.get("domain"),
            "label": lever.get("label"),
            "description": lever.get("description"),
        }
        for lever in impact_levers
    ]


def build_model_lever_user_prompt(
    *,
    events: list[dict[str, Any]],
    impact_levers: list[dict[str, Any]],
    catalog_version: str,
    validation_feedback: str | None = None,
) -> str:
    """Compatibility wrapper for the compact v4 dimension-design prompt."""
    return build_v4_dimension_design_user_prompt(
        events=events,
        impact_levers=impact_levers,
        catalog_version=catalog_version,
        validation_feedback=validation_feedback,
    )


def build_v4_dimension_design_user_prompt(
    *,
    events: list[dict[str, Any]],
    impact_levers: list[dict[str, Any]],
    catalog_version: str,
    validation_feedback: str | None = None,
) -> str:
    """Create grounded dimensions directly from all selected Events and the compact catalog."""
    feedback = (
        f"\n## 이전 dimension 검증 실패\n- {validation_feedback[:300]}\n"
        "- Event 근거는 유지하고 dimension 설계 계약만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        f"## Impact Catalog Version\n{catalog_version}\n\n"
        "## Event Context\n"
        f"{format_compact_event_context(events)}\n\n"
        "## Model Impact Lever Catalog\n"
        f"{json.dumps(_compact_impact_catalog(impact_levers), ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 출력\n"
        "- interactions, dimensionDefinitions 3~6개와 excludedDimensions만 작성하십시오.\n"
        "- dimensionId는 영문 snake_case로 작성하십시오.\n"
        "- dimensionType과 valueKind를 지정하십시오.\n"
        "- 각 dimension은 eventGroundings와 leverMappings를 하나 이상 포함하십시오.\n"
        "- eventGroundings는 eventId, 짧은 observedBasis, Scenario를 나누는 uncertainty만 포함하십시오.\n"
        "- leverMappings는 leverCode와 mappingRationale을 포함하고 impactLeverId는 생략할 수 있습니다.\n"
        "- 각 value는 valueId, label, globalPressureContribution, assumptionRationale을 포함하십시오.\n"
        "- sourceFactIds, sourceEventIds, sourceRefs, leverRefs, impactLeverRefs, "
        "commonFactLeverMappings, eventDimensionCoverage를 만들지 마십시오.\n"
        "- 모델 지원 상태만으로 dimension의 선택 우선순위를 정하지 마십시오.\n"
        "- Scenario와 그룹 메타데이터는 아직 출력하지 마십시오.\n"
        f"{feedback}"
    )


def _compact_dimensions(dimension_definitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "dimensionId": definition.get("dimension_id"),
            "label": definition.get("label"),
            "description": definition.get("description"),
            "dimensionType": definition.get("dimension_type"),
            "eventGroundings": [
                {
                    "eventId": grounding.get("event_id"),
                    "observedBasis": grounding.get("observed_basis"),
                    "uncertainty": grounding.get("uncertainty"),
                }
                for grounding in definition.get("event_groundings") or []
            ],
            "leverMappings": [
                {
                    "leverCode": mapping.get("lever_code"),
                    "mappingRationale": mapping.get("mapping_rationale"),
                }
                for mapping in definition.get("lever_mappings") or []
            ],
            "values": [
                {
                    "valueId": value.get("value_id"),
                    "label": value.get("label"),
                    "globalPressureContribution": value.get("global_pressure_contribution"),
                    "assumptionRationale": value.get("assumption_rationale"),
                }
                for value in definition.get("values") or []
            ],
        }
        for definition in dimension_definitions
    ]


def build_v4_scenario_synthesis_user_prompt(
    *,
    interactions: list[dict[str, Any]],
    dimension_definitions: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    """Generate v4 Scenarios from validated compact dimension grounding."""
    feedback = (
        f"\n## 이전 Scenario 검증 실패\n- {validation_feedback[:300]}\n"
        "- dimension은 유지하고 Scenario만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        "## Validated Interactions\n"
        f"{json.dumps(interactions, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Validated Dimensions\n"
        f"{json.dumps(_compact_dimensions(dimension_definitions), ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 출력\n"
        "- groupTitle, groupDescription, scenarios 3~5개와 excludedScenarios를 작성하십시오.\n"
        "- 생성 및 제외 결과를 합쳐 다섯 globalPressureBand를 정확히 한 번씩 다루십시오.\n"
        "- Scenario는 모든 dimension을 정확히 한 번 사용하며 조합이 서로 달라야 합니다.\n"
        "- globalPressureRationale은 선택한 value의 가격 기여와 lever 경로를 연결하십시오.\n"
        "- 상승·하락 요인이 실제로 함께 있는 내부 Scenario만 mixedFactors에 두 요인을 설명하십시오.\n"
        "- mixed Scenario는 선택 사항이며 없다는 이유로 억지로 만들지 마십시오.\n"
        "- relatedMarkets는 지역 특이성이 명확할 때만 포함하십시오.\n"
        f"{feedback}"
    )


__all__ = [
    "MODEL_LEVER_SYSTEM_PROMPT",
    "build_model_lever_user_prompt",
    "build_v4_dimension_design_user_prompt",
    "build_v4_scenario_synthesis_user_prompt",
]
