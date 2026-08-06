from __future__ import annotations

import json
from typing import Any

from apps.agents.scenario_group_agent.prompts.event_context import (
    format_compact_event_context,
)


V2_SYSTEM_PROMPT = """\
당신은 복수의 MI Event에서 원본 Template dimension을 선택해 LNG 가격 시나리오를 설계하는 전문가입니다.

전략 v2 — 원본 Template dimension 선택:
- Event Context는 현재 사실이고 Template은 dimension 의미를 설명하는 참고 지식입니다.
- 전체 Template dimension 중 Event 사실에 직접 연결되는 direct_event_fact, LNG 가격·수급·물동량
  경로에 연결되는 lng_impact_path, 또는 둘 다인 both에 해당하는 3~6개만 선택합니다.
- dimension을 합성하거나 이름을 바꾸지 말고 dimensionId를 e{eventId}__{dimKey}로 작성합니다.
- 각 선택은 입력에 존재하는 단일 sourceRef만 사용합니다.
- 모든 Event를 최소 하나의 선택 dimension sourceRef.eventId로 연결합니다.
- Event Context에서 이미 발생·시작·완료된 사실은 모든 value와 Scenario에서 유지합니다.
  이미 시작된 정비를 취소·미착수로 되돌리는 등 관측 사실을 역전하지 마십시오.
- value는 아직 결정되지 않은 기간, 규모, 회복 속도와 파급 범위만 변화시킵니다.
- 각 dimension에 3~4개의 자연스러운 value를 만들고 bullish, balanced, bearish 기여 방향을 지정합니다.
- Cartesian product를 만들지 말고 3~5개의 서로 다른 Scenario 조합을 직접 설계합니다.
- globalPressureBand는 strong_bullish, bullish, balanced, bearish, strong_bearish 중 중복 없이 사용합니다.
- value 기여를 bullish=+1, balanced=0, bearish=-1로 합산했을 때 strong_bearish에서
  strong_bullish로 갈수록 합계가 감소하지 않아야 합니다. strong_bearish는 생성 Scenario 중
  최솟값, strong_bullish는 최댓값이어야 하며 인접 pressure band의 합계 순서를 뒤집지 마십시오.
- 상승·하락 value를 함께 포함하는 내부 Scenario를 최소 하나 만들고 probabilityScore는 0~100 정수로 작성합니다.
- 위에서 명시한 선택 항목 외의 상세 lineage, interaction 및 제외 진단 필드는 출력하지 않습니다.
"""


COMMON_V3_SYSTEM_PROMPT = """\
당신은 복수의 MI Event를 공동 전제로 LNG 시장 시나리오를 설계하는 전문가입니다.

공통 원칙:
- 입력의 Event Context는 현재 사건의 사실이며 모든 최종 Scenario에 반영합니다.
- Template Domain Knowledge는 사건 해석과 dimension/value 표현을 돕는 참고 지식입니다.
  대표 사례나 value_enums 예시를 현재 Event의 사실, 계산식, 허용값 목록으로 취급하지 마십시오.
- Template 예시와 Event 사실이 충돌하면 Event 사실을 우선합니다.
- Event에 맞는 자연스러운 신규 value를 생성할 수 있습니다.
- Cartesian product를 만들지 말고 다섯 가격 압력 목표 후보별 조합을 직접 설계합니다.
- 후보는 strong_bullish, bullish, balanced, bearish, strong_bearish입니다.
- 지나치게 낮은 발생 가능성, 사실 불일치, 요소 모순, 독립 검토 가치 부족 후보는 제외하고
  reasonCode와 구체적인 한국어 reason을 남깁니다.
- 생성 후보와 제외 후보를 합쳐 다섯 목표 구간을 정확히 한 번씩 다룹니다.
- 최종 Scenario는 3~5개이며 dimension 조합이 모두 달라야 합니다.
- 가격 상승·하락 요인이 실제로 함께 작용하는 내부 후보 정확히 하나를 mixedFactors=true로 표시합니다.
  mixed Scenario는 floor와 ceiling이 아닌 non-extreme 후보여야 합니다.
- probabilityScore는 후보 간 상대적 발생 가능성 점수이며 0~100 정수입니다.
"""


V3_SYSTEM_CONTRACT = """\
- EventShock은 eventId와 자연어 한 문장의 shockSummary만 출력합니다.
- dimension에는 dimensionId, label, description, rationale, sourceEventIds, sourceRefs, values만 출력합니다.
- rationale에는 관련 Event 사실과 예상 글로벌 LNG 가격 영향 방향을 자연어로 설명합니다.
- sourceEventIds는 dimension이 근거로 삼은 입력 Event ID만 중복 없이 포함합니다.
- sourceRefs는 입력 Template의 scenarioDimensionTemplateId와 dimKey만 포함합니다.
- value에는 valueId, label, globalPressureContribution만 출력합니다.
- sourceFactIds, sourceAssignments, leverRefs, impactLeverRefs, modelSupportStatus,
  Template checksum, source별 rationale은 출력하지 않습니다.
"""


V3_STRATEGY_PROMPT = """\
전략 v3 — 다중 Event의 합성 Dimension:
- Event별 핵심 충격과 예상 LNG 가격 방향을 shockSummary 한 문장으로 요약합니다.
- 시간·지역·시설·수급 경로가 실제로 관련된 Event만 증폭, 상쇄, 인과 연결, 지역 결합으로 연결합니다.
- 상호작용이 없는 Event는 relation=independent로 보존하고 억지로 한 dimension에 합치지 않습니다.
- 해석 충돌은 실패가 아니라 relation=interpretation_conflict와 resolutionDimensionId로 표현합니다.
- resolutionDimensionId가 있으면 해당 dimension의 sourceEventIds가 interaction의 모든 eventId를 포함해야 합니다.
- interaction 하나는 실제로 같은 관계에 참여하는 서로 다른 Event를 2개 이상 포함할 수 있습니다.
- eventIds를 정확히 2개로 제한하지 않습니다.
- 모든 Event pair를 기계적으로 만들지 말고 실제 상호작용 단위로 묶습니다.
- 모든 Event가 sourceEventIds로 하나 이상의 dimension에 연결되도록 3~6개의 직관적인 합성 dimension을 만듭니다.
- 공급, 저장·주입, 수요, 지역 spread·차익거래처럼 인과 경로와 시장 변수가 다른 driver는
  단순 압축을 위해 하나의 포괄적인 위험 dimension으로 합치지 말고 독립 dimension으로 보존합니다.
- relation=independent인 Event는 각 Event를 단독 sourceEventIds로 갖는 dimension을 최소 하나씩 만듭니다.
- 개별 지역 Event를 더 넓은 권역 충격으로 확장하려면 다른 Event와의 연결 근거를 rationale에 명시합니다.
- sourceRefs는 합성 근거가 된 입력 Template의 ID와 dimKey 조합만 중복 없이 기록합니다.
- excludedDimensions는 v2 전용 필드이므로 빈 배열로 출력합니다.
"""


V3_ANALYSIS_SYSTEM_PROMPT = (
    """\
당신은 복수의 MI Event를 함께 분석해 LNG 가격 시나리오의 합성 Dimension을 설계하는 전문가입니다.

- Event Context는 현재 사건의 권위 있는 사실이며 Template은 해석을 돕는 참고 지식입니다.
- Event별 핵심 충격과 예상 글로벌 LNG 가격 방향을 eventShock 한 문장으로 요약합니다.
- 실제로 관련된 Event만 증폭, 상쇄, 인과 연결, 지역 결합 또는 해석 충돌로 연결합니다.
- 모든 Event를 적어도 하나의 합성 Dimension에 연결하고 직관적이며 중복이 적은 Dimension 3~6개를 만듭니다.
- 이 단계에서는 Scenario, 그룹 메타데이터와 제외 pressure band를 생성하지 않습니다.
"""
    + V3_SYSTEM_CONTRACT
)


V3_SCENARIO_SYSTEM_PROMPT = """\
당신은 검증된 Event Shock, Event Interaction과 합성 Dimension을 사용해 LNG 가격 Scenario를 설계하는 전문가입니다.

- 입력은 검증 완료된 정본이므로 Event Shock, Interaction과 Dimension을 변경하거나 새로 만들지 않습니다.
- Cartesian product 대신 서로 다른 대표 Scenario 3~5개를 직접 설계합니다.
- 생성·제외 후보를 합쳐 strong_bullish, bullish, balanced, bearish, strong_bearish를 정확히 한 번씩 다룹니다.
- 생성 Scenario 중 최저 pressure band는 floor, 최고 pressure band는 ceiling이 됩니다.
- 상승·하락 요인이 실제로 함께 작용하는 내부 Scenario 정확히 하나를 mixedFactors=true로 표시합니다.
  mixed Scenario는 floor와 ceiling이 아닌 non-extreme 후보여야 합니다.
- Event 사실을 취소해야만 만들 수 있는 pressure band는 생성하지 말고 제외 이유를 기록합니다.
- probabilityScore는 Event 관측 사실에 가깝고 추가 가정이 적을수록 높게 부여하는 0~100 상대 점수입니다.
"""


def multi_event_system_prompt(api_version: str) -> str:
    if api_version == "v2":
        return V2_SYSTEM_PROMPT
    if api_version == "v3":
        return COMMON_V3_SYSTEM_PROMPT + V3_SYSTEM_CONTRACT
    raise ValueError(f"Unsupported multi-event API version: {api_version}")


def _sample_value_examples(values: list[object]) -> list[str]:
    normalized = [str(value).strip()[:120] for value in values if str(value).strip()]
    if len(normalized) <= 3:
        return normalized
    sampled = [normalized[0], normalized[len(normalized) // 2], normalized[-1]]
    return list(dict.fromkeys(sampled))


def _compact_v2_template_knowledge(
    events: list[dict[str, Any]],
    templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for event, template in zip(events, templates, strict=True):
        impact_lines = [
            line.strip()[:200]
            for line in str(template.get("lng_price_impact_examples") or "").splitlines()
            if line.strip()
        ][:3]
        result.append(
            {
                "eventId": event.get("mi_event_id"),
                "scenarioDimensionTemplateId": template.get("scenario_dimension_template_id"),
                "eventTypeDefinition": str(template.get("event_type_definition") or "")[:600],
                "lngPriceImpactExamples": impact_lines,
                "dimensions": [
                    {
                        "dimKey": dimension.get("dim_key"),
                        "label": dimension.get("label"),
                        "description": str(dimension.get("description") or "")[:240],
                        "required": bool(dimension.get("required", False)),
                        "valueExamples": _sample_value_examples(dimension.get("value_enums") or []),
                    }
                    for dimension in template.get("dimensions") or []
                ],
            },
        )
    return result


def _v3_template_knowledge(
    events: list[dict[str, Any]],
    templates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [
        {
            "eventId": event.get("mi_event_id"),
            "eventTypeL2Id": event.get("event_type_l2_id"),
            "scenarioDimensionTemplateId": template.get("scenario_dimension_template_id"),
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
        for event, template in zip(events, templates, strict=True)
    ]


def build_multi_event_user_prompt(
    *,
    api_version: str,
    events: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    event_context = format_compact_event_context(events)
    feedback = (
        "\n## Previous validation failure\n"
        f"- {validation_feedback[:300]}\n"
        "- 계약 위반을 수정해 전체 결과를 다시 작성하십시오.\n"
        if validation_feedback
        else ""
    )
    if api_version == "v2":
        template_knowledge = _compact_v2_template_knowledge(events, templates)
        return (
            "## Event Context (authoritative current facts)\n"
            f"{event_context}\n\n"
            "## Compact Template Candidates (reference only)\n"
            f"{json.dumps(template_knowledge, ensure_ascii=False, separators=(',', ':'))}\n\n"
            "## Output\n"
            "- 모든 설명과 근거는 한국어로 작성하십시오.\n"
            "- selectedDimensions에는 dimensionId, sourceRef, selectionCriterion, "
            "selectionRationale, values만 출력하십시오.\n"
            "- selectionCriterion은 direct_event_fact, lng_impact_path, both 중 하나입니다.\n"
            "- 각 Scenario의 dimensionValues는 선택한 모든 dimensionId를 정확히 한 번 포함하십시오.\n"
            "- Scenario title·narrative·globalPressureBand·probabilityScore·globalPressureRationale를 출력하십시오.\n"
            f"{feedback}"
        )
    if api_version != "v3":
        raise ValueError(f"Unsupported multi-event API version: {api_version}")

    template_knowledge = _v3_template_knowledge(events, templates)
    return (
        f"## Generation Strategy\n{V3_STRATEGY_PROMPT}\n\n"
        "## Event Context (authoritative current facts)\n"
        f"{event_context}\n\n"
        "## Template Domain Knowledge (reference examples, not current facts or closed enums)\n"
        f"{json.dumps(template_knowledge, ensure_ascii=False, indent=2)}\n\n"
        "## Output\n"
        "- 모든 문자열 설명과 근거는 한국어로 작성하십시오.\n"
        "- 각 dimension에는 의미 있는 value를 3~5개 정의하고 globalPressureContribution을 "
        "bullish, balanced, bearish 중 하나로 지정하십시오.\n"
        "- v3 value에는 sourceAssignments를 출력하지 마십시오.\n"
        "- dimensionDefinitions.values에는 최종 Scenario에서 실제 사용하는 value를 모두 정의하십시오.\n"
        "- 각 Scenario의 dimensionValues는 dimensionDefinitions의 dimensionId 전체와 정확히 일치해야 합니다.\n"
        "- mixedFactors=true인 Scenario는 bullish와 bearish contribution을 모두 포함해야 합니다.\n"
        f"{feedback}"
    )


def build_dimension_design_user_prompt(
    *,
    api_version: str,
    events: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    event_shocks: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    """Build the cross-Event dimension stage prompt without Scenario output."""
    feedback = (
        "\n## Previous dimension validation failure\n"
        f"- {validation_feedback[:300]}\n"
        "- Event 분석은 유지하고 dimension 설계만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    if api_version != "v2":
        raise ValueError(f"Unsupported multi-event API version: {api_version}")
    template_knowledge = _compact_v2_template_knowledge(events, templates)
    output_contract = (
        "- selectedDimensions 3~6개만 출력하십시오.\n"
        "- 각 dimension은 입력 Template의 단일 sourceRef를 사용하고 "
        "dimensionId는 e{eventId}__{dimKey} 형식이어야 합니다.\n"
        "- 각 dimension에 상호 구분되는 value 3~4개와 globalPressureContribution을 작성하십시오.\n"
    )
    return (
        f"## Strategy\n{V2_SYSTEM_PROMPT}\n\n"
        "## Event Context (authoritative current facts)\n"
        f"{format_compact_event_context(events)}\n\n"
        "## Deterministic Event Grounding\n"
        f"{json.dumps(event_shocks, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Template Candidates\n"
        f"{json.dumps(template_knowledge, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Output\n"
        f"{output_contract}"
        "- 모든 입력 Event를 최소 하나의 selectedDimensions.sourceRef.eventId로 연결하십시오.\n"
        "- 이미 발생·시작·완료된 사실을 취소·미발생 상태로 되돌리는 value를 만들지 마십시오.\n"
        "- 관측 사실은 고정하고 아직 결정되지 않은 기간·규모·회복·파급 범위만 분기하십시오.\n"
        "- Scenario, 그룹 제목과 그룹 설명은 아직 출력하지 마십시오.\n"
        f"{feedback}"
    )


def build_v3_analysis_design_user_prompt(
    *,
    events: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    """Build the single v3 cross-Event analysis and dimension-design prompt."""
    feedback = (
        "\n## Previous analysis validation failure\n"
        f"- {validation_feedback[:300]}\n"
        "- Event Shock, Interaction과 Dimension 설계만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    return (
        f"## Strategy\n{V3_STRATEGY_PROMPT}\n\n"
        "## Event Context (authoritative current facts)\n"
        f"{format_compact_event_context(events)}\n\n"
        "## Template Domain Knowledge (reference only)\n"
        f"{json.dumps(_v3_template_knowledge(events, templates), ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Output\n"
        "- 입력 Event마다 eventShock을 정확히 하나씩 출력하십시오.\n"
        "- interactions와 dimensionDefinitions 3~6개를 출력하십시오.\n"
        "- 모든 입력 Event가 하나 이상의 dimension.sourceEventIds에 포함되어야 합니다.\n"
        "- 각 dimension은 입력 Template에 존재하는 sourceRefs와 value 3~5개를 포함해야 합니다.\n"
        "- Scenario, 그룹 제목·설명과 제외 pressure band는 출력하지 마십시오.\n"
        f"{feedback}"
    )


def build_scenario_synthesis_user_prompt(
    *,
    api_version: str,
    event_shocks: list[dict[str, Any]],
    dimension_definitions: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    """Build the final small prompt from validated dimensions only."""
    feedback = (
        "\n## Previous Scenario validation failure\n"
        f"- {validation_feedback[:300]}\n"
        "- Event 분석과 dimension 정의는 유지하고 Scenario만 수정하십시오.\n"
        if validation_feedback
        else ""
    )
    pressure_partition = (
        "- v3는 생성하지 않은 pressure band를 excludedCandidates에 이유와 함께 기록하십시오.\n"
        if api_version == "v3"
        else "- v2는 생성할 3~5개 pressure band만 중복 없이 선택하십시오.\n"
    )
    mixed_contract = (
        "- bullish와 bearish value가 실제로 함께 있는 non-extreme Scenario 정확히 하나를 "
        "mixedFactors=true로 표시하십시오.\n"
        if api_version == "v3"
        else "- v2 Scenario는 관측 사실을 유지하면서 상승·하락 value가 함께 있는 내부 조합을 포함하십시오.\n"
    )
    return (
        "## Validated Event Shocks\n"
        f"{json.dumps(event_shocks, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Validated Dimensions\n"
        f"{json.dumps(dimension_definitions, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Validated Interactions\n"
        f"{json.dumps(interactions, ensure_ascii=False, separators=(',', ':'))}\n\n"
        "## Output\n"
        "- scenarioGroupTitle, scenarioGroupDescription과 Scenario 3~5개를 한국어로 작성하십시오.\n"
        "- 각 Scenario는 모든 dimensionId를 정확히 한 번 사용하고 서로 다른 조합이어야 합니다.\n"
        "- globalPressureBand는 중복 없이 사용하며 probabilityScore와 globalPressureRationale을 작성하십시오.\n"
        f"{mixed_contract}"
        "- probabilityScore는 관측 사실에 가깝고 추가 가정이 적을수록 높게 부여하십시오.\n"
        f"{pressure_partition}"
        f"{feedback}"
    )
