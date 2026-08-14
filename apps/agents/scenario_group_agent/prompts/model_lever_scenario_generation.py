from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.prompts.event_context import CompactEventContext


MODEL_LEVER_SYSTEM_PROMPT = """하나 이상의 MI Event로 JKM 시나리오를 설계합니다. 입력 사실과 가정을 구분하고,
Catalog 밖 Lever를 만들지 마십시오. 모든 설명과 label은 한국어로 작성하고 단계별 출력 규칙의 길이와
정보 밀도를 따르십시오."""


V4_EVENT_IMPACT_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + """
Event 한 건에서 LNG 시장에 필요한 핵심 사실 문장을 최대 3개 선택하고, 그 사실이 LNG 수급과
JKM 가격에 전달되는 영향 문장을 최대 3개 작성하십시오. eventFacts[0]과 impacts[0]에는 Event 제목과
요약의 핵심 주제·상태·변화를 직접 반영하십시오. 영향 문장에는 JKM 방향과 기간을 포함하십시오.
eventFacts와 impacts는 가급적 1~2개만 작성하고 의미적으로 필요한 경우에만 세 번째 항목을 추가하십시오.
각 Impact의 evidence도 가급적 1~2개만 포함하고, 같은 경로에 중요한 세 Fact가 모두 필요할 때만 3개를
사용하십시오. 별도 전달 경로를 만드는 Fact는 다른 Impact로 분리하십시오.
Fact 후보 문장은 그대로 복사하십시오. 중요한 수치·기간과 분석 기준일을 함께 해석한 판단 근거는
자연어 decisionBasis 문장으로 최대 3개 작성하고, 결과를 바꿀 열린 질문은 최대 2개만 선택하십시오.
Interaction, Dimension, Scenario는 만들지 마십시오."""
)


V4_INTERACTION_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + """
검증된 서로 다른 Event의 영향 문장 사이에서 중요한 Interaction만 최대 3개 선택하십시오.
두 경로가 결합될 때 생기는 추가 효과, JKM 순방향과 영향 기간을 완결된 한국어 문장으로 설명하십시오.
중요한 관계가 없으면 빈 배열을 반환하고 Dimension과 Scenario는 만들지 마십시오."""
)


V4_DIMENSION_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + """

현재 단계에서는 검증된 열린 질문만 사용해 Dimension 3~6개와 각 선택지 2~4개를 설계하십시오.
각 Dimension은 화면용 이름과 사용자가 답할 질문을 함께 가져야 합니다. 새 Fact, Path, Interaction 또는
Lever를 만들지 말고, 선택지에는 비교 가능한 시장·운영 상태와 그 상태가 JKM 압력을 바꾸는 이유를 작성하십시오.
"""
)


V4_SCENARIO_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + """

현재 단계에서는 공통 영향, Interaction, Dimension 질문과 선택지를 변경하지 말고 대표 Scenario
3~5개를 합성하십시오. 각 Scenario는 모든 질문에 정확히 하나씩 답하고, 서로 구분되는 핵심 전제 조합과
결과 전달 경로를 가져야 합니다. narrative는 주요 조건과 최종 JKM 전달 경로를 두 문장으로 설명하십시오.
"""
)


_IMPACT_DOMAINS = ("demand", "supply", "trade", "price_only")


def _render_impact_catalog(impact_levers: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[str]] = {domain: [] for domain in _IMPACT_DOMAINS}
    for lever in sorted(
        impact_levers,
        key=lambda item: (str(item.get("domain") or ""), str(item.get("lever_code") or "")),
    ):
        domain = str(lever.get("domain") or "")
        if domain not in grouped:
            continue
        description = str(lever.get("description") or "").strip()
        hint = str(lever.get("applicability_hint") or "").strip() or description
        grouped[domain].append(f"- {lever.get('lever_code')}: {hint[:120]}")
    sections = []
    for domain in _IMPACT_DOMAINS:
        if grouped[domain]:
            sections.append(f"### {domain}\n" + "\n".join(grouped[domain]))
    return "\n".join(sections)


def build_v4_event_fact_candidates(event: dict[str, Any]) -> dict[str, str]:
    """Create stable source sentences that the LLM can select without rephrasing."""
    compact = CompactEventContext.from_event(event)
    raw_facts = [
        text for item in event.get("key_facts") or event.get("key_bullets") or [] if (text := str(item).strip())
    ]
    if not raw_facts:
        raw_facts = [compact.summary or compact.title]
    unique_facts = list(dict.fromkeys(fact for fact in raw_facts if fact))[:5]
    return {f"f{index}": fact for index, fact in enumerate(unique_facts, start=1)}


def _feedback(title: str, validation_feedback: str | None, instruction: str) -> str:
    if not validation_feedback:
        return ""
    return (
        f"\n## 이전 {title} 검증 실패\n"
        f"- 검증 오류: {validation_feedback[:600]}\n"
        "- 이전 시도의 오류가 발생한 필드 또는 조합을 수정하고 동일한 실수를 반복하지 마십시오.\n"
        f"- {instruction}\n"
    )


def build_model_lever_user_prompt(
    *,
    events: list[dict[str, Any]],
    impact_levers: list[dict[str, Any]],
    catalog_version: str,
    analysis_as_of: str,
    validation_feedback: str | None = None,
) -> str:
    """Compatibility wrapper for the first v4 analysis prompt."""
    return build_v4_event_impact_analysis_user_prompt(
        events=events,
        impact_levers=impact_levers,
        catalog_version=catalog_version,
        analysis_as_of=analysis_as_of,
        validation_feedback=validation_feedback,
    )


def build_v4_event_impact_analysis_user_prompt(
    *,
    events: list[dict[str, Any]],
    impact_levers: list[dict[str, Any]],
    catalog_version: str,
    analysis_as_of: str,
    validation_feedback: str | None = None,
) -> str:
    if len(events) != 1:
        detail = "v4 Event analysis requires exactly one Event"
        raise ValueError(detail)
    feedback = _feedback(
        "Event Impact Analysis",
        validation_feedback,
        "제공된 Fact 후보 문장은 바꾸지 말고 잘못된 영향 경로·Lever·balance·열린 질문만 수정하십시오.",
    )
    compact = CompactEventContext.from_event(events[0])
    fact_candidates = build_v4_event_fact_candidates(events[0])
    fact_lines = "\n".join(f"{index}. {fact}" for index, fact in enumerate(fact_candidates.values(), start=1))
    return (
        "## 목적\n"
        "Event에서 LNG 시장에 중요한 사실을 고르고, 그 사실이 JKM까지 전달되는 경로와 열린 질문을 설명합니다.\n\n"
        "## Event\n"
        f"- ID: {compact.event_id}\n"
        f"- 제목: {compact.title[:120]}\n"
        f"- 요약: {compact.summary[:240]}\n"
        f"- 발생시각: {compact.occurred_at or '미제공'}\n"
        f"- 분석 기준일: {analysis_as_of}\n\n"
        "## 핵심 사실 후보\n"
        f"{fact_lines}\n\n"
        f"## 사용할 수 있는 Lever · catalog {catalog_version}\n"
        f"{_render_impact_catalog(impact_levers)}\n\n"
        "## 이번 단계의 질문\n"
        "1. LNG 시장에 실질적인 영향을 주는 후보 문장은 무엇입니까?\n"
        "2. 그 사실은 어떤 Lever와 수급 경로를 거쳐 JKM에 영향을 줍니까?\n"
        "3. 사실을 인정한 뒤에도 결과를 바꿀 열린 질문은 무엇입니까?\n\n"
        "## 출력 규칙\n"
        "- eventFacts에는 위 후보 문장을 글자까지 그대로 복사합니다. 새 사실을 작성하지 않습니다.\n"
        "- eventFacts[0]은 Primary Fact입니다. Event 제목과 요약의 핵심 주체·지표·상태·변화를 가장 직접적으로\n"
        "  담은 후보를 선택합니다. 배경 사실이 JKM과 더 직접 연결되더라도 Primary Fact를 밀어내지 않습니다.\n"
        "- eventFacts는 가급적 1~2개만 선택하고, 세 번째 Fact는 앞의 Fact와 중복되지 않는 중요한 근거가\n"
        "  시나리오 결과를 실질적으로 바꿀 때만 추가합니다.\n"
        "- eventFacts[1]과 eventFacts[2]는 서로 다른 Lever·방향·기간을 추가하거나 Primary Fact의 영향을\n"
        "  실질적으로 증폭·상쇄할 때만 선택합니다. 같은 주제를 반복하거나 배열을 채우기 위해 선택하지 않습니다.\n"
        "- decisionBasis에는 시나리오를 구분하는 중요한 수치·비율·가격·용량·기간·목표일과 분석 기준일을\n"
        "  함께 해석한 완결된 한국어 판단 근거를 최대 3개 작성합니다. 문장만 읽어도 어느 Event의 어떤\n"
        "  사실을 근거로 했는지 알 수 있게 쓰고, 별도 ID나 Fact 참조 필드는 만들지 않습니다.\n"
        "  eventFacts에 선택되지 않았더라도 위 후보에 있는 중요한 수치·일정은\n"
        "  decisionBasis에 보존할 수 있습니다.\n"
        "  단, decisionBasis는 Primary Fact나 Primary Impact를 대신할 수 없습니다.\n"
        "  48시간 사전 요청처럼 반복되는 운영 조건은 남은 기간으로 계산하지 않습니다. 30일 내 복구 목표나\n"
        "  60일 협상 기간처럼 시작점이 있는 기간은 원문에서 시작점을 확인한 경우에만 분석 기준일 현재\n"
        "  기한 경과·잔여 기간을 설명합니다. Event 발생시각을 근거 없이 기간 시작점으로 간주하지 않습니다.\n"
        "  시작점을 확정할 수 없으면 잔여일을 만들지 말고 현재 잔여 기간을 확정할 수 없다고 작성합니다.\n"
        "  과거 관측 수치는 현재 수치처럼 쓰지 말고 관측 시점과 현재 지속 여부의 불확실성을 구분합니다.\n"
        "- impacts.analysis는 사실 → Lever → LNG 수급·거래 → JKM을 잇는 완결된 한국어 문장입니다.\n"
        "  JKM의 상승·하락·혼조 방향과 단기·중기·장기 중 영향 기간을 반드시 문장 안에 포함합니다.\n"
        "- impacts[0]은 Primary Impact입니다. evidence에 eventFacts[0]을 반드시 포함하고, analysis에 Primary Fact의\n"
        "  핵심 주체·지표를 보존해 해당 변화가 Lever와 JKM으로 전달되는 대표 경로를 설명합니다.\n"
        "- impacts[].evidence에는 선택한 eventFacts를 1~3개 포함하되 가급적 1~2개만 사용합니다. 같은 경로의\n"
        "  중요한 근거가 세 Fact 모두에 있고 하나를 빼면 전달 경로가 불완전해질 때만 3개를 사용합니다.\n"
        "- impacts는 가급적 1~2개만 작성합니다. 세 번째 Impact는 서로 다른 Lever·방향·기간 또는 실질적인\n"
        "  증폭·상쇄 경로를 앞의 Impact로 설명할 수 없을 때만 추가합니다.\n"
        "  세 번째 Fact가 별도 주요 Lever, 반대 방향, 구분되는 기간 또는 독립 원인을 나타내면 별도 Impact로\n"
        "  분리합니다. 선택한 모든 eventFact는 적어도 하나의 Impact evidence에 사용합니다.\n"
        "- leverStates는 Impact마다 가급적 1~2개만 작성하며 `lever|role|direction|scope|timing` 형식입니다.\n"
        "  driver·transmission·primary 세 단계가 모두 중요한 전달 경로일 때만 최대 3개를 작성합니다.\n"
        "  3개를 초과하는 후보가 있으면 실제 전달 경로를 가장 잘 설명하는 중요한 3개만 선택하고,\n"
        "  배열을 채우기 위해 불필요한 Lever를 추가하지 않습니다.\n"
        "  role은 primary(핵심 변화), driver(선행 원인), transmission(전달 경로) 중 하나입니다.\n"
        "  direction은 increase, decrease, disrupt, recover, unchanged 중 하나입니다.\n"
        "- balance는 `domain|direction` 또는 `none` 형식입니다.\n"
        "  domain은 demand, supply, trade이고 direction은 increase, decrease, mixed, unchanged 중 하나입니다.\n"
        "  선택한 Lever가 모두 price_only domain이면 balance는 반드시 none입니다.\n"
        "  demand, supply, trade domain Lever가 하나라도 있으면 balance에 none을 사용할 수 없습니다.\n"
        "  물리 수급 Lever의 domain이 하나뿐이면 balance에 그 domain을 사용합니다. 여러 물리 domain이 있으면\n"
        "  JKM 전달 경로를 지배하는 domain 하나를 선택하고, 지배적인 domain을 정할 수 없으면 Impact를 나눕니다.\n"
        "  별도의 price 필드는 만들지 않습니다.\n"
        "- openQuestions는 결과를 가장 크게 바꿀 서로 다른 핵심 질문 최대 2개를 작성하며,\n"
        "  Impact 번호를 1부터 참조합니다.\n"
        "  Primary Impact의 규모·기간·회복 시점이 Scenario 결과를 바꾼다면 그 질문을 우선합니다.\n"
        "  이미 확인된 사실을 다시 질문하지 않습니다.\n"
        "  분석 기준일에 이미 지난 목표는 미래 선택지처럼 묻지 말고, 현재 남은 제약과 앞으로의 해소 시점을 묻습니다.\n"
        "  lever는 반드시 해당 Impact의 leverStates에 실제로 쓴 Lever code 중 하나를 글자까지 그대로 복사합니다.\n"
        "  질문에 필요한 Lever가 해당 Impact에 없으면 다른 Lever로 바꾸지 말고 그 질문을 생략합니다.\n"
        "- 사용할 사실이 없거나 중요한 영향이 없을 때만 excludedBecause를 작성합니다.\n"
        f"{feedback}"
    )


def build_v4_interaction_analysis_user_prompt(
    *,
    impact_paths: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    feedback = _feedback(
        "Interaction",
        validation_feedback,
        "검증된 Path ID는 유지하고 잘못된 관계만 수정하십시오.",
    )
    path_cards = []
    seen_event_ids: set[object] = set()
    for index, path in enumerate(impact_paths, start=1):
        event_id = path.get("event_id")
        path_role = "Primary Impact" if event_id not in seen_event_ids else "Supporting Impact"
        seen_event_ids.add(event_id)
        lever_text = ", ".join(
            f"{step.get('lever_code')} {step.get('state_direction')} ({step.get('scope')}, {step.get('timing')})"
            for step in path.get("lever_steps") or []
        )
        path_cards.append(
            "\n".join(
                [
                    f"### [P{index}] Event {event_id}",
                    f"- 역할: {path_role}",
                    f"- 영향: {str(path.get('mechanism') or '')[:240]}",
                    f"- Lever: {lever_text}",
                    f"- 중요도: {path.get('materiality')}",
                ],
            ),
        )
    return (
        "## 목적\n"
        "서로 다른 Event의 영향 경로가 결합될 때 생기는 추가 효과와 열린 질문을 찾습니다.\n\n"
        "## 검증된 영향 경로\n"
        f"{'\n\n'.join(path_cards)}\n\n"
        "## 이번 단계의 질문\n"
        "- 두 경로가 단순히 같은 방향입니까, 아니면 증폭·상쇄·인과 연결 같은 추가 효과가 있습니까?\n"
        "- 결합 효과의 크기나 기간을 바꾸는 미결정 변수는 무엇입니까?\n\n"
        "## 출력 규칙\n"
        "- paths에는 위 P 번호만 사용하고 서로 다른 Event의 경로만 연결합니다.\n"
        "- 각 Event의 Primary Impact가 포함된 결합을 먼저 검토합니다. 다만 실제 추가 효과가 있을 때만\n"
        "  Interaction을 만들며, 단순히 Primary라는 이유로 관계를 만들어내지 않습니다.\n"
        "- analysis는 결합으로 새로 생기는 시장 효과와 JKM의 순방향·영향 기간을 한 문장으로 설명합니다.\n"
        "- 별도의 price 필드는 만들지 않습니다.\n"
        "- 중요한 Interaction이 없으면 interactions와 openQuestions를 빈 배열로 둡니다.\n"
        "- openQuestions는 전체 Interaction 중 결과를 가장 크게 바꿀 핵심 질문 최대 1개만 작성합니다.\n"
        "  interaction은 Interaction 배열의 1부터 시작하는 번호입니다.\n"
        "  lever는 해당 Interaction의 paths 카드에 표시된 Lever code 중 하나를 글자까지 그대로 복사합니다.\n"
        "  질문에 필요한 Lever가 그 paths에 없으면 다른 Lever로 바꾸지 말고 그 질문을 생략합니다.\n"
        f"{feedback}"
    )


def _render_validation_warnings(validation_warnings: list[dict[str, Any]]) -> str:
    if not validation_warnings:
        return "- 없음"
    return "\n".join(
        f"- [{warning.get('code')}] {warning.get('message')} (참조: {', '.join(warning.get('reference_ids') or [])})"
        for warning in validation_warnings
    )


def _render_uncertainty_cards(impact_analysis: dict[str, Any]) -> str:
    paths = {path.get("impact_path_id"): path for path in impact_analysis.get("impact_paths") or []}
    interactions = {
        interaction.get("interaction_id"): interaction for interaction in impact_analysis.get("interactions") or []
    }
    uncertainties = [
        *(impact_analysis.get("path_uncertainties") or []),
        *(impact_analysis.get("interaction_uncertainties") or []),
    ]
    cards = []
    for index, uncertainty in enumerate(uncertainties, start=1):
        path_ids = uncertainty.get("impact_path_ids") or []
        path_text = " / ".join(str((paths.get(path_id) or {}).get("mechanism") or path_id) for path_id in path_ids)
        interaction = interactions.get(uncertainty.get("interaction_id"))
        interaction_text = str(interaction.get("mechanism") or "") if interaction else ""
        lines = [
            f"### [U{index}] {uncertainty.get('subject')}",
            f"- 근거 영향: {path_text}",
        ]
        if interaction_text:
            lines.append(f"- 근거 Interaction: {interaction_text}")
        lines.extend(
            [
                f"- 영향 Lever: {uncertainty.get('affected_lever_code')}",
                f"- 판단 축: {uncertainty.get('axis_type')}",
                f"- 시장 의미: {uncertainty.get('reason')}",
            ],
        )
        cards.append("\n".join(lines))
    return "\n\n".join(cards) or "- Dimension으로 만들 수 있는 열린 질문이 없습니다."


def _render_decision_basis(impact_analysis: dict[str, Any]) -> str:
    basis = [str(item).strip() for item in impact_analysis.get("decision_basis") or [] if str(item).strip()]
    return "\n".join(f"- {item}" for item in basis) or "- 없음"


def build_v4_dimension_design_user_prompt(
    *,
    impact_analysis: dict[str, Any],
    validation_warnings: list[dict[str, Any]],
    analysis_as_of: str,
    validation_feedback: str | None = None,
) -> str:
    feedback = _feedback(
        "Dimension",
        validation_feedback,
        "검증된 열린 질문은 유지하고 Dimension 질문과 선택지만 수정하십시오.",
    )
    return (
        "## 목적\n"
        "검증된 열린 질문을 사용자가 비교할 수 있는 Scenario 판단 축과 선택지로 바꿉니다.\n\n"
        f"## 분석 기준일\n- {analysis_as_of}\n\n"
        "## 숫자·시점 판단 근거\n"
        f"{_render_decision_basis(impact_analysis)}\n\n"
        "## Dimension 후보가 되는 열린 질문\n"
        f"{_render_uncertainty_cards(impact_analysis)}\n\n"
        "## 검증 참고사항\n"
        f"{_render_validation_warnings(validation_warnings)}\n\n"
        "## 이번 단계의 질문\n"
        "1. 어떤 열린 질문이 JKM 결과를 실질적으로 구분합니까?\n"
        "2. 사용자가 비교할 수 있는 상호 배타적인 답은 무엇입니까?\n"
        "3. 각 답은 Lever 상태와 JKM 압력을 어떻게 바꿉니까?\n\n"
        "## 출력 규칙\n"
        "- from에는 위 U 번호만 사용합니다. Dimension ID와 Value ID는 서버가 부여합니다.\n"
        "- label은 화면 표에 표시할 10~40자의 이름입니다. 핵심 대상과 변화 축만 담고 전체 인과를 넣지 않습니다.\n"
        "- question은 사용자가 답할 수 있는 한국어 질문이며 상세 화면과 생성 근거에 사용합니다.\n"
        "- rationale은 이 불확실성이 Scenario와 JKM 결과를 구분하는 이유를 10~100자의 짧은 한국어 한 문장으로 "
        "작성합니다. question을 반복하지 말고 `운항 지연 범위에 따라 아시아 가용 화물과 JKM 리스크 프리미엄이 "
        "변화됨`처럼 핵심 인과만 설명합니다.\n"
        "- lever와 axis는 source 질문에 표시된 값을 그대로 사용합니다.\n"
        "- 각 Dimension에는 같은 판단 축·단위를 사용하는 선택지 2~4개를 만듭니다.\n"
        "- Choice label은 10~25자로 하나의 비교 가능한 시장·운영 상태만 표현합니다.\n"
        "  낮음·중간·높음, 단기·중기·장기, 거의 없음·일부 감소·큰 감소처럼 강도만 쓰지 않습니다.\n"
        "- 숫자·시점 판단 근거에 현재 판단에 유효한 수치·기간·잔여일이 있으면 question과 Choice에 반영합니다.\n"
        "  과거 목표일은 미래 가능성처럼 되돌리지 말고 현재 상태의 전제로 사용합니다. 새로운 수치 경계는\n"
        "  제공된 판단 근거가 실제 기준을 줄 때만 만들며, 근거가 없으면 비교 가능한 운영 상태로 표현합니다.\n"
        "- states는 `lever|direction|level|scope|timeWindow` 형식입니다.\n"
        "  direction은 increase, decrease, disrupt, recover, unchanged 중 하나이며 나머지는 짧은 자연어입니다.\n"
        "- why는 해당 답이 공통 영향 대비 JKM 압력을 바꾸는 이유와 어떤 Event 사실·현재 시점 판단을\n"
        "  바탕으로 만들었는지 문장 자체에서 알 수 있게 자연어로 설명합니다. 별도 Anchor 참조 ID는 작성하지 않습니다.\n"
        "- 사용하지 않은 질문은 notUsed에 자연어 이유를 남깁니다.\n"
        f"{feedback}"
    )


def _render_common_impact_cards(impact_analysis: dict[str, Any]) -> str:
    cards = [
        f"- [P{index}] {path.get('mechanism')}"
        for index, path in enumerate(impact_analysis.get("impact_paths") or [], start=1)
    ]
    return "\n".join(cards) or "- 없음"


def _render_interaction_cards(impact_analysis: dict[str, Any]) -> str:
    cards = [
        f"- [I{index}] {interaction.get('mechanism')} ({interaction.get('relation')})"
        for index, interaction in enumerate(impact_analysis.get("interactions") or [], start=1)
    ]
    return "\n".join(cards) or "- 없음"


def _render_dimension_matrix(dimension_definitions: list[dict[str, Any]]) -> str:
    cards = []
    for dimension_index, dimension in enumerate(dimension_definitions, start=1):
        lines = [
            f"### [D{dimension_index}] {dimension.get('description') or dimension.get('label')}",
            f"- Lever/축: {dimension.get('primary_lever_code')} / {dimension.get('dimension_type')}",
        ]
        for value_index, value in enumerate(dimension.get("values") or [], start=1):
            states = ", ".join(
                f"{state.get('lever_code')} {state.get('direction')} {state.get('level')} "
                f"({state.get('scope')}, {state.get('time_window')})"
                for state in value.get("lever_states") or []
            )
            lines.append(
                f"- [D{dimension_index}.V{value_index}] {value.get('label')} | {states} | "
                f"JKM {value.get('pressure_contribution')} | {value.get('assumption_rationale')}"
            )
        cards.append("\n".join(lines))
    return "\n\n".join(cards)


def build_v4_scenario_synthesis_user_prompt(
    *,
    impact_analysis: dict[str, Any],
    dimension_definitions: list[dict[str, Any]],
    validation_warnings: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    feedback = _feedback(
        "Scenario",
        validation_feedback,
        "공통 영향과 질문·선택지는 유지하고 Scenario 조합과 설명만 수정하십시오.",
    )
    return (
        "## 목적\n"
        "공통 영향에 모든 Dimension 질문의 답과 필요한 Interaction을 더해 대표 JKM Scenario를 만듭니다.\n\n"
        "## 모든 Scenario에 공통인 영향\n"
        f"{_render_common_impact_cards(impact_analysis)}\n\n"
        "## 적용 가능한 Interaction\n"
        f"{_render_interaction_cards(impact_analysis)}\n\n"
        "## Dimension 질문과 선택지\n"
        f"{_render_dimension_matrix(dimension_definitions)}\n\n"
        "## 검증 참고사항\n"
        f"{_render_validation_warnings(validation_warnings)}\n\n"
        "## 이번 단계의 질문\n"
        "- 어떤 선택지 조합이 서로 구분되는 대표 전개를 만듭니까?\n"
        "- 공통 영향, 선택지 효과, Interaction이 최종 JKM 압력에 각각 어떻게 기여합니까?\n\n"
        "## 출력 규칙\n"
        "- Scenario 3~5개를 만들고 생성·제외 결과를 합쳐 다섯 pressure band를 한 번씩 다룹니다.\n"
        "- choices에는 각 D의 V를 정확히 하나씩 `D1.V1` 형식으로 선택합니다.\n"
        "- 제외 후보도 choices에 각 D의 V를 정확히 하나씩 선택해, 제외된 실제 조합을 보존합니다.\n"
        "- 발생 가능성이 낮아 제외하면 reasonCode는 LOW_PROBABILITY로 작성합니다. 조합이 독립적인 검토 가치가\n"
        "  없어 제외하는 경우에는 NOT_INDEPENDENT를 사용합니다.\n"
        "- interactions에는 실제로 추가 효과를 적용한 I 번호만 넣습니다.\n"
        "- 각 Scenario는 다른 Scenario와 구분되는 핵심 전제 조합과 결과 전달 경로를 가져야 합니다.\n"
        "- 공급·수요·운송·회복 같은 미리 정한 유형에 맞추지 말고, 입력된 Dimension과 Interaction에서\n"
        "  Scenario별 구분 요인을 선택합니다. pressure 단계만 한 칸씩 바꾼 유사 조합을 반복하지 않습니다.\n"
        "- title은 20~40자로 Scenario를 구분하는 핵심 조건이나 메커니즘 1~2개를 표현합니다.\n"
        "  pressure 이름만 반복하지 않습니다. 상반된 효과가 중요할 때만 상쇄·우세 관계를 포함하고,\n"
        "  같은 방향이면 결합·증폭을, 단일 경로가 결정적이면 그 경로를 중심으로 작성합니다.\n"
        "- narrative는 80~300자의 한국어 두 문장입니다. 첫 문장은 주요 조건과 변화를, 둘째 문장은\n"
        "  영향 경로와 Interaction을 거친 최종 JKM 압력을 설명하며 선택값을 순서대로 나열하지 않습니다.\n"
        "  상반된 효과가 있으면 우세·상쇄를, 같은 방향이면 증폭을, Interaction이 없으면 결정적 경로를 설명합니다.\n"
        "- title, narrative, explanation에는 D1.V1·I1 같은 내부 참조 ID를 노출하지 말고, 해당 선택 상태와\n"
        "  상호작용 메커니즘을 자연어로 풀어 씁니다. ID는 choices와 interactions 필드에서만 사용합니다.\n"
        "- explanation은 공통 영향, 선택한 분기, 적용한 상호작용이 최종 JKM 압력을 만드는 과정을 "
        "자연스러운 한국어 문장으로 설명합니다.\n"
        "- 공통 영향은 분기 효과에 다시 더하지 않습니다.\n"
        "- probability는 공통 사실에 가깝고 추가 가정이 적을수록 높게 부여합니다.\n"
        "- relatedMarkets는 `TTF|이유` 또는 `HH|이유` 형식이며 특별한 영향이 있을 때만 씁니다. "
        "한 Scenario 안에서 TTF와 HH는 각각 최대 한 번만 작성하고 같은 시장을 중복하지 마십시오.\n"
        f"{feedback}"
    )


__all__ = [
    "MODEL_LEVER_SYSTEM_PROMPT",
    "V4_DIMENSION_SYSTEM_PROMPT",
    "V4_EVENT_IMPACT_SYSTEM_PROMPT",
    "V4_INTERACTION_SYSTEM_PROMPT",
    "V4_SCENARIO_SYSTEM_PROMPT",
    "build_model_lever_user_prompt",
    "build_v4_dimension_design_user_prompt",
    "build_v4_event_fact_candidates",
    "build_v4_event_impact_analysis_user_prompt",
    "build_v4_interaction_analysis_user_prompt",
    "build_v4_scenario_synthesis_user_prompt",
]
