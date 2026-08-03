from __future__ import annotations

import json
from typing import Any


MULTI_EVENT_SYSTEM_PROMPT = """\
당신은 복수의 MI Event를 공동 전제로 LNG 시장 시나리오를 설계하는 전문가입니다.

공통 원칙:
- 입력의 Event Context는 현재 사건의 사실이며 모든 최종 Scenario에 반영합니다.
- Template Domain Knowledge는 사건 해석과 dimension/value 표현을 돕는 참고 지식입니다.
  대표 사례나 value_enums 예시를 현재 Event의 사실, 계산식, 허용값 목록으로 취급하지 마십시오.
- Template 예시와 Event 사실이 충돌하면 Event 사실을 우선합니다.
- Event에 맞는 자연스러운 신규 value를 생성할 수 있습니다.
- Event 직접 근거가 없는 전개 가정만 sourceType=scenario_assumption,
  assumptionYn=Y로 표시합니다. 그 외 sourceType의 assumptionYn은 N입니다.
- Cartesian product를 만들지 말고 다섯 가격 압력 목표 후보별 조합을 직접 설계합니다.
- 후보는 strong_bullish, bullish, balanced, bearish, strong_bearish입니다.
- 지나치게 낮은 발생 가능성, 사실 불일치, 요소 모순, 독립 검토 가치 부족 후보는 제외하고
  reasonCode와 구체적인 한국어 reason을 남깁니다.
- 생성 후보와 제외 후보를 합쳐 다섯 목표 구간을 정확히 한 번씩 다룹니다.
- 최종 Scenario는 3~5개이며 dimension 조합이 모두 달라야 합니다.
- 가격 상승·하락 요인이 함께 작용하는 내부 구간 후보 하나 이상은 mixedFactors=true입니다.
- probabilityScore는 후보 간 상대적 발생 가능성 점수이며 0~100 정수입니다.
- 모든 lineage에 eventId, eventTypeL2Id, dimKey, sourceType, assumptionYn, rationale을 채웁니다.
"""


V2_STRATEGY_PROMPT = """\
전략 v2 — 다중 Event의 원본 Template Dimension:
- 모든 Template dimension 후보에서 LNG 가격 영향 관련성이 높은 3~6개를 선택합니다.
- 원본 dimension의 label, description, required 값을 그대로 보존하고 이름이나 의미를 합성하지 않습니다.
- dimensionId는 반드시 e{eventId}__{dimKey} 형식입니다.
- 각 dimension의 sourceRefs는 해당 원본 source 하나만 포함합니다.
- Event별 dimension을 강제하지 않으며, 관련 dimension이 없는 Event는 공동 사실 문맥에만 유지합니다.
- required 후보가 6개를 넘으면 관련성 기준으로 제외하고 excludedDimensions에 근거를 남깁니다.
"""


V3_STRATEGY_PROMPT = """\
전략 v3 — 다중 Event의 합성 Dimension:
- Event별 Supply, Demand, Trade 충격을 먼저 EventShock으로 정규화합니다.
- 시간·지역·시설·수급 경로가 실제로 관련된 Event만 증폭, 상쇄, 인과 연결, 지역 결합으로 연결합니다.
- 상호작용이 없는 Event는 relation=independent로 보존하고 억지로 한 dimension에 합치지 않습니다.
- 해석 충돌은 실패가 아니라 relation=interpretation_conflict와 resolutionDimensionId로 표현합니다.
- resolutionDimensionId가 있으면 해당 dimension의 sourceRefs가 interaction의 모든 eventId를 포함해야 합니다.
- 원본 source를 추적 가능한 3~6개의 직관적인 합성 dimension을 만듭니다.
- 합성 dimension은 관련된 경우 복수 sourceRefs를 가지며, 독립 Event용 dimension은 단일 sourceRef가 가능합니다.
"""


def build_multi_event_user_prompt(
    *,
    api_version: str,
    events: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    strategy = V2_STRATEGY_PROMPT if api_version == "v2" else V3_STRATEGY_PROMPT
    event_context = [
        {
            "eventId": event.get("mi_event_id"),
            "eventTypeL2Id": event.get("event_type_l2_id"),
            "eventType": event.get("event_type") or {},
            "title": event.get("event_title_ko"),
            "summary": event.get("one_line_summary"),
            "occurredAt": event.get("occurred_at"),
            "keyFacts": event.get("key_bullets") or [],
            "detailAnalysis": event.get("detail_analysis"),
            "tags": event.get("tags") or [],
        }
        for event in events
    ]
    template_knowledge = [
        {
            "eventId": event.get("mi_event_id"),
            "eventTypeL2Id": event.get("event_type_l2_id"),
            "templateId": template.get("scenario_dimension_template_id"),
            "templateChecksum": template.get("template_checksum"),
            "eventTypeDefinition": template.get("event_type_definition"),
            "lngPriceImpactExamples": template.get("lng_price_impact_examples"),
            "dimensions": [
                {
                    "dimKey": dimension.get("dim_key"),
                    "label": dimension.get("label"),
                    "description": dimension.get("description"),
                    "required": dimension.get("required"),
                    "valueEnumExamples": dimension.get("value_enums") or [],
                    "displayOrder": dimension.get("display_order"),
                }
                for dimension in template.get("dimensions") or []
            ],
        }
        for event, template in zip(events, templates)
    ]
    feedback = (
        "\n## Previous semantic validation failure\n"
        f"- {validation_feedback}\n"
        "- 이전 응답을 복사하지 말고 위 계약 위반을 수정해 전체 결과를 다시 작성하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        f"## Generation Strategy\n{strategy}\n\n"
        "## Event Context (authoritative current facts)\n"
        f"{json.dumps(event_context, ensure_ascii=False, indent=2)}\n\n"
        "## Template Domain Knowledge (reference examples, not current facts or closed enums)\n"
        f"{json.dumps(template_knowledge, ensure_ascii=False, indent=2)}\n\n"
        "## Output\n"
        "- 모든 문자열 설명과 근거는 한국어로 작성하십시오.\n"
        "- 각 dimension에는 의미 있는 value를 3~5개 정의하고 globalPressureContribution을 "
        "bullish, balanced, bearish 중 하나로 지정하십시오.\n"
        "- 각 value의 sourceAssignments는 해당 dimension의 모든 sourceRefs를 정확히 한 번씩 투영하십시오.\n"
        "- dimensionDefinitions.values에는 최종 Scenario에서 실제 사용하는 value를 모두 정의하십시오.\n"
        "- 각 Scenario의 dimensionValues key는 dimensionDefinitions의 dimensionId 전체와 정확히 일치해야 합니다.\n"
        "- mixedFactors=true인 Scenario는 bullish와 bearish contribution을 모두 포함해야 합니다.\n"
        f"{feedback}"
    )
