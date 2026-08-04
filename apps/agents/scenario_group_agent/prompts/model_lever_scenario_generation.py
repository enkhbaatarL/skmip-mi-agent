from __future__ import annotations

import json
from typing import Any

from apps.agents.scenario_group_agent.prompts.event_context import (
    format_compact_event_context,
)


MODEL_LEVER_SYSTEM_PROMPT = """\
당신은 복수의 MI Event를 공동 전제로 LNG 가격 시나리오를 설계하는 전문가입니다.

입력 Event는 현재 사건에 관한 권위 있는 사실입니다. Event Type은 분류 정보일 뿐,
Template이나 dimension을 선택하는 키로 사용하지 마십시오.

Model Impact Lever Catalog는 시나리오가 참조할 수 있는 영향 경로의 폐쇄 목록입니다.
카탈로그에 없는 leverCode나 모델 파라미터를 만들지 마십시오. parameterBindings는 모델
연결 가능성을 설명하는 참고 정보이며, 시나리오에 모델 파라미터 값을 직접 만들지 마십시오.

작업 순서:
1. Lever 선택보다 먼저 각 Event의 수요·공급·거래·가격 관련 사실을 EventImpactFact로 추출합니다.
   각 사실에 고유한 factId를 부여하고 선택한 모든 Event를 빠짐없이 다룹니다. EventImpactFact에는
   일반 leverCode 필드가 없으므로 사실 추출 단계에서 lever를 미리 고정하지 않습니다.
2. Event 간 증폭, 상쇄, 인과 연결, 지역 결합 또는 독립 관계를 식별합니다.
3. 추출한 사실 중 LNG 가격 결과를 실질적으로 바꾸고 사용자가 확인할 가치가 있는 잔여 불확실성만
   3~6개의 dimension으로 만듭니다. 관련 없는 경로나 확정 사실 자체는 dimension으로 만들지 않습니다.
4. 각 dimension의 sourceFactIds로 근거 사실을 연결하고, impactLeverRefs로 Catalog lever에 매핑합니다.
   각 impactLeverRef는 leverCode, sourceFactIds, mappingRationale을 포함하며 impactLeverId는 선택 사항입니다.
5. dimension마다 2~4개의 상호 배타적 value를 만듭니다. value는 magnitude, scope,
   timing, recovery, mitigation, interaction 중 하나의 불확실성을 구체적으로 나타냅니다.
6. dimension에 사용되지 않은 모든 사실의 공통 가격 영향 경로를
   EventImpactFact.commonImpactLeverRefs에 기록합니다. dimension sourceFactIds에 사용된 사실에는
   commonImpactLeverRefs를 만들지 않습니다.
7. 모든 Event를 eventDimensionCoverage에 정확히 한 번 포함해 dimension 연결 여부와 근거를 설명합니다.
8. Cartesian product 대신 글로벌 LNG 가격 압력이 서로 다른 3~5개의 대표 Scenario를
   직접 설계합니다.

모든 dimension은 비어 있지 않은 sourceFactIds와 impactLeverRefs를 가져야 합니다. 모든 Event가
dimension을 가질 필요는 없습니다. 잔여 불확실성이 없는 Event는 dimension 없이 공동 사실로 유지하고
eventDimensionCoverage.noDimensionReason과 rationale로 설명합니다. 모델 지원 상태는 dimension 선택의
우선순위가 아닙니다. price_only 또는 known_unsupported 경로도 시나리오 구분에 중요하면 사용할 수 있고,
이를 실행 가능한 파라미터로 꾸미지 마십시오. 단, 전체 dimension 중 적어도 하나는 supportStatus가
executable인 parameterBinding을 가진 lever를 참조해야 합니다.

Scenario는 strong_bullish, bullish, balanced, bearish, strong_bearish 중 서로 다른 구간을
사용합니다. 생성하지 않은 구간은 excludedScenarios에 이유를 남겨, 생성 및 제외 결과를 합쳐
다섯 구간을 정확히 한 번씩 다룹니다. 최저 구간은 floor, 최고 구간은 ceiling이 됩니다. 상승·하락
요인이 실제로 함께 있는 내부 구간만 mixed Scenario로 표시하며 mixed는 선택 사항입니다.
probabilityScore는 선택된 Event가 모두 발생한다는 전제하에서 Scenario 전개의 상대적 개연성입니다.

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
    event_context = format_compact_event_context(events)
    catalog = [
        {
            "impactLeverId": lever.get("impact_lever_id"),
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
        f"{event_context}\n\n"
        "## Model Impact Lever Catalog\n"
        f"{json.dumps(catalog, ensure_ascii=False, indent=2)}\n\n"
        "## 출력 세부 규칙\n"
        "- eventImpactFacts의 factId는 결과 전체에서 고유해야 하며, 각 Event를 하나 이상의 사실로 다루십시오.\n"
        "- eventImpactFacts에는 일반 leverCode를 출력하지 마십시오.\n"
        "- commonImpactLeverRefs는 어떤 dimension의 sourceFactIds에도 쓰이지 않은 사실에만 작성하십시오.\n"
        "- dimension에 쓰이지 않은 모든 EventImpactFact에는 비어 있지 않은 commonImpactLeverRefs를 "
        "작성하십시오.\n"
        "- dimensionId는 영문 snake_case로 작성하십시오.\n"
        "- displayOrder는 1부터 순서대로 부여하십시오.\n"
        "- required는 true로 설정하십시오.\n"
        "- valueKind와 dimensionType을 반드시 지정하십시오.\n"
        "- 각 dimension은 비어 있지 않은 sourceFactIds와 impactLeverRefs를 포함해야 합니다.\n"
        "- impactLeverRefs 각 항목은 leverCode, sourceFactIds, mappingRationale을 채우고, "
        "impactLeverId는 생략하거나 Catalog 값과 정확히 일치시킬 수 있습니다.\n"
        "- 한 dimension의 impactLeverRefs 전체 sourceFactIds 합집합은 소유 "
        "dimension.sourceFactIds와 정확히 일치해야 하며 사실 domain과 lever domain이 "
        "일치해야 합니다.\n"
        "- sourceRefs, sourceEventIds, leverRefs는 비우고 modelSupportStatus는 null로 두십시오. "
        "서버가 검증된 fact/lever 관계로 계산합니다.\n"
        "- 모델 지원 상태만으로 dimension의 선택 우선순위를 정하지 마십시오.\n"
        "- 적어도 하나의 dimension은 executable parameterBinding이 있는 lever를 참조하십시오.\n"
        "- eventDimensionCoverage는 입력 Event를 정확히 한 번씩 포함하고 eventId, dimensionIds, "
        "noDimensionReason, rationale을 채우십시오.\n"
        "- dimensionIds가 있으면 noDimensionReason은 null, 없으면 noDimensionReason과 구체적인 "
        "rationale이 필수입니다.\n"
        "- noDimensionReason은 NO_EXECUTABLE_UNCERTAINTY, PRICE_ONLY_OR_UNSUPPORTED, "
        "COMMON_FACT_NO_SCENARIO_DELTA 중 하나만 사용하십시오. 이는 Event별 dimension 부재를 "
        "설명할 뿐 dimension의 선택 우선순위를 결정하지 않습니다.\n"
        "- dimensionValues는 {dimensionId, valueId} 객체 배열이며, dimensionId 집합은 모든 "
        "dimensionId와 정확히 일치해야 합니다.\n"
        "- 각 선택값은 해당 dimension의 valueId 또는 label 중 하나여야 합니다.\n"
        "- globalPressureRationale은 Event→lever→글로벌 LNG 가격 압력을 설명하십시오.\n"
        "- relatedMarkets는 해당 Scenario에서 지역 특이성이 명확한 시장만 포함하십시오.\n"
        "- relatedMarkets에는 시장별 bullish/bearish 또는 floor/ceiling을 만들지 마십시오.\n"
        "- mixedFactors에는 상쇄되는 상승·하락 요인을 모두 적으십시오.\n"
        f"{feedback}"
    )


def build_v4_event_analysis_user_prompt(
    *,
    event: dict[str, Any],
    validation_feedback: str | None = None,
) -> str:
    """Extract facts for one Event before exposing the impact lever catalog."""
    feedback = (
        f"\n## 이전 Event fact 검증 실패\n- {validation_feedback[:300]}\n- 이 Event의 fact만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        "## Event Context\n"
        f"{format_compact_event_context([event])}\n\n"
        "## 출력\n"
        "- eventImpactFacts에 이 Event의 수요·공급·거래·price_only 사실을 1개 이상 추출하십시오.\n"
        "- 각 factId는 e{eventId}_ 접두사를 사용해 전체 실행에서 고유하게 만드십시오.\n"
        "- 아직 lever를 선택하지 말고 commonImpactLeverRefs는 빈 배열로 두십시오.\n"
        "- 모든 fact의 eventId는 입력 Event ID와 같아야 합니다.\n"
        f"{feedback}"
    )


def _compact_impact_catalog(impact_levers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "impactLeverId": lever.get("impact_lever_id"),
            "leverCode": lever.get("lever_code"),
            "domain": lever.get("domain"),
            "label": lever.get("label"),
            "description": lever.get("description"),
            "applicabilityHint": lever.get("applicability_hint"),
            "parameterBindings": [
                {
                    "parameterName": binding.get("parameter_name"),
                    "supportStatus": binding.get("support_status"),
                    "unsupportedReasonCode": binding.get("unsupported_reason_code"),
                }
                for binding in lever.get("parameter_bindings") or []
            ],
        }
        for lever in impact_levers
    ]


def build_v4_dimension_design_user_prompt(
    *,
    event_impact_facts: list[dict[str, Any]],
    impact_levers: list[dict[str, Any]],
    catalog_version: str,
    validation_feedback: str | None = None,
) -> str:
    """Map validated facts to catalog levers and dimensions without Scenario output."""
    fact_domains = {str(fact.get("domain")) for fact in event_impact_facts}
    relevant_levers = [lever for lever in impact_levers if str(lever.get("domain")) in fact_domains]
    feedback = (
        f"\n## 이전 dimension 검증 실패\n- {validation_feedback[:300]}\n"
        "- fact는 유지하고 dimension 매핑만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        f"## Impact Catalog Version\n{catalog_version}\n\n"
        "## Validated Event Impact Facts\n"
        f"{json.dumps(event_impact_facts, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Relevant Model Impact Lever Catalog\n"
        f"{json.dumps(_compact_impact_catalog(relevant_levers), ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 출력\n"
        "- interactions, dimensionDefinitions 3~6개, eventDimensionCoverage, commonFactLeverMappings를 작성하십시오.\n"
        "- dimension의 sourceFactIds와 impactLeverRefs는 정확히 대응하고 fact domain과 lever domain이 같아야 합니다.\n"
        "- dimension에 사용하지 않은 모든 fact만 commonFactLeverMappings에 정확히 한 번 포함하십시오.\n"
        "- 적어도 하나의 dimension은 executable parameter binding을 가진 lever를 참조해야 합니다.\n"
        "- Scenario와 그룹 메타데이터는 아직 출력하지 마십시오.\n"
        f"{feedback}"
    )


def build_v4_scenario_synthesis_user_prompt(
    *,
    event_impact_facts: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
    dimension_definitions: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    """Generate v4 Scenarios from already validated fact/lever dimensions."""
    feedback = (
        f"\n## 이전 Scenario 검증 실패\n- {validation_feedback[:300]}\n"
        "- fact와 dimension은 유지하고 Scenario만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        "## Validated Event Impact Facts\n"
        f"{json.dumps(event_impact_facts, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Validated Interactions\n"
        f"{json.dumps(interactions, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Validated Dimensions\n"
        f"{json.dumps(dimension_definitions, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## 출력\n"
        "- groupTitle, groupDescription, scenarios 3~5개와 excludedScenarios를 작성하십시오.\n"
        "- 생성 및 제외 결과를 합쳐 다섯 globalPressureBand를 정확히 한 번씩 다루십시오.\n"
        "- Scenario는 모든 dimension을 정확히 한 번 사용하며 조합이 서로 달라야 합니다.\n"
        "- 상승·하락 요인이 실제로 함께 있는 내부 Scenario만 mixedFactors에 두 요인을 설명하십시오.\n"
        "- mixed Scenario는 선택 사항이며 없다는 이유로 억지로 만들지 마십시오.\n"
        "- relatedMarkets는 지역 특이성이 명확할 때만 포함하십시오.\n"
        f"{feedback}"
    )


__all__ = [
    "MODEL_LEVER_SYSTEM_PROMPT",
    "build_model_lever_user_prompt",
    "build_v4_dimension_design_user_prompt",
    "build_v4_event_analysis_user_prompt",
    "build_v4_scenario_synthesis_user_prompt",
]
