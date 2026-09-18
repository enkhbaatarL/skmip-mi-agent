from __future__ import annotations

from typing import Any

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_budget import (
    event_open_question_budgets,
    interaction_count_target,
    interaction_question_budget,
)
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.v4_enums import (
    StateDirection,
)
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
각 Impact의 leverStates 안에서는 같은 Lever code를 두 번 이상 사용하지 마십시오. 하나의 Lever가 여러 역할이나
시점에 걸쳐 작동하더라도 가장 대표적인 role·direction·scope·timing 하나로 통합하십시오.
Fact 후보 문장은 그대로 복사하십시오. 중요한 수치·기간과 분석 기준일을 함께 해석한 판단 근거는
자연어 decisionBasis 문장으로 최대 3개 작성하고, 결과를 바꿀 열린 질문은 중요도에 따라 선택하십시오.
Interaction, Dimension, Scenario는 만들지 마십시오."""
)


V4_INTERACTION_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + """
검증된 서로 다른 Event의 영향 문장 사이에서 중요한 Interaction만 최대 3개 선택하십시오.
두 경로가 결합될 때 생기는 추가 효과, JKM 순방향과 영향 기간을 완결된 한국어 문장으로 설명하십시오.
Interaction과 연결 질문은 Scenario 분기 기여도가 높은 순서로 출력하고, Interaction마다 가장 중요한
열린 질문을 최대 1개만 작성하십시오.
중요한 관계가 없으면 빈 배열을 반환하고 Dimension과 Scenario는 만들지 마십시오."""
)


V4_DIMENSION_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + """

현재 단계에서는 검증된 열린 질문만 사용해 Dimension 3~6개와 각 선택지 2~4개를 설계하십시오.
각 Dimension은 화면용 이름과 사용자가 답할 질문을 함께 가져야 합니다. 새 Fact, Path, Interaction 또는
Lever를 만들지 말고, 선택지에는 비교 가능한 시장·운영 상태와 그 상태가 JKM 압력을 바꾸는 이유를 작성하십시오.
Dimension rationale은 question의 구체적인 관측 시점·수치·신호·대상·영향 경로를 빠짐없이 유지하고,
질문 어미만 `...하는지에 따라 ...가 달라짐` 형태로 바꾼 최대 200자의 근거 문장으로 작성하십시오. 각 Choice의 why는
답이나 응답이 아니라 `관측된 사실 → Choice가 나타내는 미래 상태 → JKM 영향`을 자연스럽게 연결하고
문장 끝의 `가정`으로 불확실성을 표시하는 간결한 문장입니다. `상태를 ... 가정`처럼 가정이라는
뜻을 한 문장 안에서 반복하지 마십시오.
Dimension rationale에서 구체적 근거를 생략하거나 Choice why를 `답`, `응답`, `선택`으로 부르면 잘못된 출력입니다.
"""
)


V4_ADDITIONAL_DIMENSION_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + f"""
검증됐지만 초기 Scenario 생성에서 사용하지 않은 열린 질문만 Additional Dimension 후보로 변환하십시오.
후보 수를 맞추지 말고 의미 있는 질문만 사용하며, 변환할 후보가 없으면 빈 dimensions 배열을 반환하십시오.
새 Fact, Path, Interaction 또는 Lever를 만들지 말고 하나의 열린 질문을 여러 후보에 중복 사용하지 마십시오.
각 후보는 화면용 이름, 원본 질문, 최대 200자의 구체적인 선정 근거와 비교 가능한 선택지 2~4개를 가집니다.
Choice의 pressure는 Dimension value의 `bearish`, `balanced`, `bullish`만 사용하십시오. Choice가 2개면
`bearish / bullish`, 3개면 `bearish / balanced / bullish`, 4개면 세 방향을 모두 포함하고 그중 의미상 필요한
한 방향을 추가하십시오. `strong_bearish`와 `strong_bullish`는 Scenario 합산 pressure band이므로 쓰지 마십시오.
각 Choice의 states 항목은 정확히 `lever|direction|level|scope|timeWindow` 다섯 부분으로 작성하십시오.
direction은 {StateDirection.prompt_values()} 중 하나만 사용하십시오. 첫 번째 state의 lever는 반드시 Dimension의
source Lever와 같아야 하며, 한 Choice 안에서 같은 Lever code를 두 번 사용하지 마십시오.
올바른 예시는
`liquefaction_utilization|increase|feedgas 유입이 설비 가동으로 전환|미국 LNG 수출설비|2026-08-20 이후 단기`입니다.
Group 441에서 생성된 `LNG 수출 설비로의 가스 유입 증가가 실제 액화설비 가동률과 수출 가능 물량 증가로 이어지는 상태`처럼
구분자 없이 자연어 문장만 넣은 states는 잘못된 출력입니다."""
)


V4_SCENARIO_SYSTEM_PROMPT = (
    MODEL_LEVER_SYSTEM_PROMPT
    + """

현재 단계에서는 공통 영향, Interaction, Dimension 질문과 선택지를 변경하지 말고 대표 Scenario
3~5개를 합성하십시오. 각 Scenario는 모든 질문에 정확히 하나씩 답하고, 서로 구분되는 핵심 전제 조합과
결과 전달 경로를 가져야 합니다. narrative는 주요 조건과 최종 JKM 전달 경로를 두 문장으로 설명하십시오.
루트 그룹 title·description은 원본 이벤트와 검증된 분석을 대표하는 한국어 메타데이터로 작성하십시오.
영문 Event·Scenario를 사용하지 말고 description에는 `입력 사실`과 `JKM`을 사용하지 마십시오.
probability는 0~100 정수 백분율로 작성하고 모든 Scenario probability의 합계를 정확히 100으로 맞추십시오.
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
    selected_event_count: int = 1,
    open_question_budget: int | None = None,
    validation_feedback: str | None = None,
) -> str:
    """Compatibility wrapper for the first v4 analysis prompt."""
    return build_v4_event_impact_analysis_user_prompt(
        events=events,
        impact_levers=impact_levers,
        catalog_version=catalog_version,
        analysis_as_of=analysis_as_of,
        selected_event_count=selected_event_count,
        open_question_budget=open_question_budget,
        validation_feedback=validation_feedback,
    )


def event_open_question_recommendations(event_count: int) -> list[int]:
    """Compatibility name for the deterministic numeric Event question budgets."""
    return event_open_question_budgets(event_count)


def build_v4_event_impact_analysis_user_prompt(
    *,
    events: list[dict[str, Any]],
    impact_levers: list[dict[str, Any]],
    catalog_version: str,
    analysis_as_of: str,
    selected_event_count: int = 1,
    open_question_budget: int | None = None,
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
    question_budget = open_question_budget or event_open_question_budgets(selected_event_count)[0]
    return (
        "## 목적\n"
        "Event에서 LNG 시장에 중요한 사실을 고르고, 그 사실이 JKM까지 전달되는 경로와 열린 질문을 설명합니다.\n\n"
        "## Event\n"
        f"- ID: {compact.event_id}\n"
        f"- 제목: {compact.title[:120]}\n"
        f"- 요약: {compact.summary[:240]}\n"
        f"- 발생시각: {compact.occurred_at or '미제공'}\n"
        f"- 분석 기준일: {analysis_as_of}\n\n"
        f"- 전체 선택 Event 수: {selected_event_count}\n\n"
        f"- 이번 Event openQuestions 목표·상한: {question_budget}개\n\n"
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
        "- 동일 Event 안의 원인 → 전달 → 결과 관계는 별도 Impact로 쪼개지 말고 하나의 Impact 안에서\n"
        "  driver → transmission → primary Lever step으로 표현합니다. JKM 방향·영향 기간·Lever 경로가\n"
        "  독립적으로 달라 하나의 전달 경로로 설명할 수 있을 때만 추가 Impact를 만듭니다.\n"
        "- leverStates는 Impact마다 가급적 1~2개만 작성하며 `lever|role|direction|scope|timing` 형식입니다.\n"
        "  driver·transmission·primary 세 단계가 모두 중요한 전달 경로일 때만 최대 3개를 작성합니다.\n"
        "  3개를 초과하는 후보가 있으면 실제 전달 경로를 가장 잘 설명하는 중요한 3개만 선택하고,\n"
        "  배열을 채우기 위해 불필요한 Lever를 추가하지 않습니다.\n"
        "  같은 Impact의 leverStates 안에서 `lever` code는 반드시 서로 달라야 합니다. 동일 Lever code를\n"
        "  driver·transmission·primary 등 다른 role로 반복하거나 direction·scope·timing만 바꿔 중복 작성하지\n"
        "  않습니다. 하나의 Lever가 여러 역할·범위·시점에 걸치면 전달 경로를 가장 잘 대표하는 하나의 step으로\n"
        "  통합합니다. 서로 다른 Impact에서는 같은 Lever code를 다시 사용할 수 있습니다.\n"
        "  출력 전에 각 Impact의 `lever|role|direction|scope|timing` 값에서 첫 번째 `lever` code를 비교해\n"
        "  중복이 없는지 반드시 확인합니다.\n"
        "  role은 primary(핵심 변화), driver(선행 원인), transmission(전달 경로) 중 하나입니다.\n"
        f"  direction은 {StateDirection.prompt_values()} 중 하나입니다.\n"
        "- balance는 `domain|direction` 또는 `none` 형식입니다.\n"
        "  domain은 demand, supply, trade이고 direction은 increase, decrease, mixed, unchanged 중 하나입니다.\n"
        "  선택한 Lever가 모두 price_only domain이면 balance는 반드시 none입니다.\n"
        "  demand, supply, trade domain Lever가 하나라도 있으면 balance에 none을 사용할 수 없습니다.\n"
        "  물리 수급 Lever의 domain이 하나뿐이면 balance에 그 domain을 사용합니다. 여러 물리 domain이 있으면\n"
        "  JKM 전달 경로를 지배하는 domain 하나를 선택하고, 지배적인 domain을 정할 수 없으면 Impact를 나눕니다.\n"
        "  별도의 price 필드는 만들지 않습니다.\n"
        f"- openQuestions는 Event별 열린 질문 배열이며 이번 Event의 목표이자 상한은 {question_budget}개입니다.\n"
        "  Scenario 분기 기여도가 높은 중요한 질문부터 출력합니다. 목표보다 적더라도 의미가 중복되거나 분기력이\n"
        "  낮은 질문으로 개수를 억지로 채우지 않습니다. Impact 번호는 1부터 참조합니다.\n"
        "- high importance Impact는 결과를 실제로 다르게 만드는 판단 축이 여러 개면 복수 질문을 허용합니다.\n"
        "  특히 Primary Impact의 규모·기간·회복 시점 중 실제 Scenario 분기를 만드는 축을 우선 검토합니다.\n"
        "  medium은 일반적으로 1~2개, low는 독립적인 Scenario 분기를 만들 때만 0~1개를 작성합니다.\n"
        "  Primary Impact와 high importance Impact를 우선하되 같은 불확실성을 magnitude·timing·duration으로\n"
        "  기계적으로 나누지 않습니다. 상한을 넘는 질문은 서버가 출력 순서대로 제거합니다.\n"
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
    event_question_count: int = 0,
    event_count: int | None = None,
    events: list[dict[str, Any]] | None = None,
    validation_feedback: str | None = None,
) -> str:
    feedback = _feedback(
        "Interaction",
        validation_feedback,
        "검증된 Path ID는 유지하고 잘못된 관계만 수정하십시오.",
    )
    path_cards_by_event: dict[int, list[str]] = {}
    event_order: list[int] = []
    event_path_counts: dict[int, int] = {}
    seen_event_ids: set[object] = set()
    for path in impact_paths:
        event_id = int(path.get("event_id"))
        if event_id not in event_path_counts:
            event_path_counts[event_id] = 0
            event_order.append(event_id)
        event_path_counts[event_id] += 1
        alias = f"E{event_id}-P{event_path_counts[event_id]}"
        lever_steps = path.get("lever_steps") or []
        path_role = (
            "Primary Impact"
            if any(step.get("path_role") == "primary" for step in lever_steps)
            or (not lever_steps and event_id not in seen_event_ids)
            else "Supporting Impact"
        )
        seen_event_ids.add(event_id)
        lever_text = ", ".join(
            f"{step.get('lever_code')} {step.get('state_direction')} ({step.get('scope')}, {step.get('timing')})"
            for step in path.get("lever_steps") or []
        )
        path_cards_by_event.setdefault(event_id, []).append(
            "\n".join(
                [
                    f"### [{alias}]",
                    f"- 역할: {path_role}",
                    f"- 영향: {str(path.get('mechanism') or '')[:240]}",
                    f"- Lever: {lever_text}",
                    f"- 중요도: {path.get('materiality')}",
                ],
            ),
        )
    event_details = {int(item.get("mi_event_id")): item for item in events or [] if item.get("mi_event_id") is not None}
    path_sections: list[str] = []
    for event_id in event_order:
        event = event_details.get(event_id, {})
        title = str(event.get("event_title_ko") or event.get("title") or "제목 미제공")
        summary = str(event.get("one_line_summary") or event.get("summary") or "요약 미제공")
        path_sections.append(
            f"## Event {event_id} · {title[:120]}\n"
            f"- 요약: {summary[:240]}\n\n" + "\n\n".join(path_cards_by_event[event_id]),
        )
    selected_event_count = event_count if event_count is not None else len(event_order)
    interaction_minimum, interaction_maximum = interaction_count_target(selected_event_count)
    question_budget = interaction_question_budget(
        retained_interaction_count=interaction_maximum,
        retained_event_question_count=event_question_count,
    )
    interaction_target = (
        str(interaction_maximum)
        if interaction_minimum == interaction_maximum
        else f"{interaction_minimum}~{interaction_maximum}"
    )
    return (
        "## 목적\n"
        "서로 다른 Event의 영향 경로가 결합될 때 생기는 추가 효과와 열린 질문을 찾습니다.\n\n"
        "## 검증된 영향 경로\n"
        f"{'\n\n'.join(path_sections)}\n\n"
        "## Interaction 개수 목표\n"
        f"- 의미 있는 Interaction 목표: {interaction_target}개\n"
        f"- Interaction 상한: {interaction_maximum}개\n\n"
        "## 기존 Event 열린 질문\n"
        f"- 실제 Event openQuestions 수: {event_question_count}개\n"
        f"- Interaction openQuestions 전체 상한: {question_budget}개\n\n"
        "## 이번 단계의 질문\n"
        "- 두 경로가 단순히 같은 방향입니까, 아니면 증폭·상쇄·인과 연결 같은 추가 효과가 있습니까?\n"
        "- 결합 효과의 크기나 기간을 바꾸는 미결정 변수는 무엇입니까?\n\n"
        "## 출력 규칙\n"
        "- paths에는 위 E{Event ID}-P{번호} 별칭만 사용하고 서로 다른 Event의 경로만 연결합니다.\n"
        "- 각 Event의 Primary Impact가 포함된 결합을 먼저 검토합니다. 다만 실제 추가 효과가 있을 때만\n"
        "  Interaction을 만들며, 단순히 Primary라는 이유로 관계를 만들어내지 않습니다.\n"
        "- analysis는 결합으로 새로 생기는 시장 효과와 JKM의 순방향·영향 기간을 한 문장으로 설명합니다.\n"
        "- 별도의 price 필드는 만들지 않습니다.\n"
        "- interactions는 Scenario 분기 기여도가 높은 순서로 출력합니다. 상한을 넘는 Interaction은 서버가\n"
        "  출력 순서대로 제거하며, 목표보다 적더라도 의미 없는 관계를 만들어 채우지 않습니다.\n"
        "- 중요한 Interaction이 없으면 interactions와 openQuestions를 빈 배열로 둡니다.\n"
        f"- Interaction openQuestions는 전체 최대 {question_budget}개이며 각 Interaction에는 가장 중요한 질문을\n"
        "  최대 1개만 작성합니다. 질문도 연결된 Interaction의 중요도 순서에 맞춰 출력합니다. Interaction 질문은\n"
        "  교차 Event 효과가 새로운 Scenario 분기를 만들 때만 작성하고 relation=independent에는 작성하지 않습니다.\n"
        "  목표보다 적더라도 의미가 중복되거나 분기력이 낮은 질문을 추가하지 않습니다. 상한을 넘는 질문은\n"
        "  서버가 출력 순서대로 제거합니다.\n"
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
    question_count = len(impact_analysis.get("path_uncertainties") or []) + len(
        impact_analysis.get("interaction_uncertainties") or []
    )
    if question_count == 3:
        dimension_recommendation = "3개"
        unused_recommendation = "세 질문을 모두 초기 Dimension에 사용해 unused question이 없어도 정상입니다."
    elif question_count == 4:
        dimension_recommendation = "3개"
        unused_recommendation = "unused question을 최소 1개 남기기를 권장합니다."
    elif question_count >= 5:
        dimension_recommendation = "3~4개"
        unused_recommendation = "unused question을 최소 1개 남기기를 권장합니다."
    else:
        dimension_recommendation = "3~4개"
        unused_recommendation = "의미 있는 질문을 우선 사용합니다."
    return (
        "## 목적\n"
        "검증된 열린 질문을 사용자가 비교할 수 있는 Scenario 판단 축과 선택지로 바꿉니다.\n\n"
        f"## 분석 기준일\n- {analysis_as_of}\n\n"
        "## 숫자·시점 판단 근거\n"
        f"{_render_decision_basis(impact_analysis)}\n\n"
        "## Dimension 후보가 되는 열린 질문\n"
        f"{_render_uncertainty_cards(impact_analysis)}\n\n"
        "## 개수 권장\n"
        f"- 실제 open question 수: {question_count}개\n"
        f"- 초기 Dimension 권장 범위: {dimension_recommendation}\n"
        f"- {unused_recommendation}\n"
        "- 구조적으로는 Dimension 3~6개를 허용하며 권장 범위 위반만으로 실패하지 않습니다.\n\n"
        "## 검증 참고사항\n"
        f"{_render_validation_warnings(validation_warnings)}\n\n"
        "## 이번 단계의 질문\n"
        "1. 어떤 열린 질문이 JKM 결과를 실질적으로 구분합니까?\n"
        "2. 사용자가 비교할 수 있는 상호 배타적인 미래 가정은 무엇입니까?\n"
        "3. 각 가정은 Lever 상태와 JKM 압력을 어떻게 바꿉니까?\n\n"
        "## 출력 규칙\n"
        "- from에는 위 U 번호만 사용합니다. Dimension ID와 Value ID는 서버가 부여합니다.\n"
        "- label은 핵심 대상과 변화 축을 담되 30자를 넘지 않습니다.\n"
        "- question은 필요한 관측 정보와 판단 대상을 충분히 포함하며 글자 수 제한이 없습니다.\n"
        "- rationale은 최대 200자의 구체적인 한국어 한 문장입니다. question의 관측일·분석 기준일·수치·시장 "
        "신호·대상·영향 경로를 생략하지 않고, 질문 어미만 `...하는지에 따라` 형태로 바꿔 Scenario와 JKM "
        "결과가 구분되는 이유를 설명합니다. 최소 글자 수는 강제하지 않습니다.\n"
        "- lever와 axis는 source 질문에 표시된 값을 그대로 사용합니다.\n"
        "- 각 Dimension에는 같은 판단 축·단위를 사용하는 선택지 2~4개를 만듭니다.\n"
        "- Choice label은 비교 가능한 하나의 시장·운영 상태를 30자 이내로 작성합니다.\n"
        "  낮음·중간·높음, 단기·중기·장기, 거의 없음·일부 감소·큰 감소처럼 강도만 쓰지 않습니다.\n"
        "- 숫자·시점 판단 근거에 현재 판단에 유효한 수치·기간·잔여일이 있으면 question과 Choice에 반영합니다.\n"
        "  과거 목표일은 미래 가능성처럼 되돌리지 말고 현재 상태의 전제로 사용합니다. 새로운 수치 경계는\n"
        "  제공된 판단 근거가 실제 기준을 줄 때만 만들며, 근거가 없으면 비교 가능한 운영 상태로 표현합니다.\n"
        "- states는 `lever|direction|level|scope|timeWindow` 형식입니다.\n"
        f"  direction은 {StateDirection.prompt_values()} 중 하나이며 나머지는 짧은 자연어입니다.\n"
        "- why는 Choice의 간결한 가정 근거입니다. 반드시 `관측된 사실 → 미래 상태 → JKM 영향` 순서의 한 문장으로 "
        "쓰고, 문장 끝의 `가정`으로 미래 상태가 확정 사실이 아님을 표시합니다. 가정이라는 메타 표현은 문장 끝에서 "
        "한 번만 사용하며 `상태를 가정하면`, `상황을 가정하면`, `나타나는 가정이다`처럼 반복하지 않습니다. "
        "`Event 배경으로 제시된 사실` 같은 출처 메타 설명 없이 관측 사실을 바로 서술하고, `답`, `응답`, `선택`, "
        "`선택한 값`이라는 말도 사용하지 않습니다. 제공된 Event 사실과 숫자·시점 판단 근거만 사용하고 별도 Anchor "
        "참조 ID나 새 사실을 만들지 않습니다.\n"
        "  권장 형식: `[관측된 과거·현재 사실]을 기반으로, [분석 기준일 이후 Choice의 미래 상태가 발생·유지·완화되고], "
        "[시장 전달 경로를 거쳐 JKM 영향이 나타나는] 가정.`\n"
        "  예: `2026년 6월 30일 유럽 저장률이 49.1%로 관측되고 겨울 주입 기대가 있었던 사실을 기반으로, "
        "분석 기준일 이후 주입 부담이 완화되고 NWE 가격 지지와 글로벌 LNG 가격 지지력이 약해져 JKM 하방 "
        "압력이 우세해지는 가정.`\n"
        "  예: `2026년 7월 2일 JKM-NWE 계절물 스프레드의 약화·폐쇄 신호가 관측된 사실을 기반으로, 9월 "
        "이후물에서 JKM-NWE 스프레드가 다시 벌어지고 아시아가 대서양 화물을 끌어올 가격 신호를 회복해 JKM "
        "상승 압력이 커지는 가정.`\n"
        "- 사용하지 않은 질문은 notUsed에 자연어 이유를 남깁니다.\n"
        f"{feedback}"
    )


def build_v4_additional_dimension_user_prompt(
    *,
    impact_analysis: dict[str, Any],
    impact_levers: list[dict[str, Any]],
    selected_definitions: list[dict[str, Any]],
    validation_feedback: str | None = None,
) -> str:
    selected = (
        "\n".join(
            f"- {item.get('label') or item.get('dimension_id')}: {', '.join(item.get('source_uncertainty_ids') or [])}"
            for item in selected_definitions
        )
        or "- 없음"
    )
    used_levers = {
        str(item.get("affected_lever_code") or "")
        for item in [
            *(impact_analysis.get("path_uncertainties") or []),
            *(impact_analysis.get("interaction_uncertainties") or []),
        ]
    }
    compact_catalog = [item for item in impact_levers if str(item.get("lever_code") or "") in used_levers]
    unused_question_count = len(impact_analysis.get("path_uncertainties") or []) + len(
        impact_analysis.get("interaction_uncertainties") or []
    )
    candidate_recommendation = f"1~{unused_question_count}개" if unused_question_count else "0개"
    feedback = _feedback(
        "Additional Dimension 후보",
        validation_feedback,
        "탈락 reason code별로 states wire 형식, source alias, Lever lineage, Value 중복과 pressure coverage를 "
        "모두 수정하십시오.",
    )
    return (
        "## 목적\n"
        "초기 Scenario 생성에서 선택되지 않은 열린 질문을 추가 Dimension 후보로 일괄 변환합니다.\n"
        "의미 있는 질문만 후보로 만들며 후보 개수를 맞추기 위해 약한 질문을 사용하지 않습니다.\n\n"
        "## 아직 사용되지 않은 열린 질문\n"
        f"{_render_uncertainty_cards(impact_analysis)}\n\n"
        "## 개수 권장\n"
        f"- 실제 unused question 수: {unused_question_count}개\n"
        f"- Additional Dimension 후보 권장 범위: {candidate_recommendation}\n"
        "- 의미 있는 후보가 없으면 빈 dimensions도 정상 결과입니다.\n\n"
        "## 관련 Lever catalog\n"
        f"{_render_impact_catalog(compact_catalog)}\n\n"
        "## 이미 선택된 Dimension\n"
        f"{selected}\n\n"
        "## 출력 규칙\n"
        "- dimensions에는 위 U 번호만 from으로 참조합니다. 하나의 U는 후보 간 중복 사용하지 않습니다.\n"
        "- 초기 Dimension과 의미가 겹치는 후보는 만들지 않습니다. 변환할 가치가 없으면 빈 dimensions를 반환합니다.\n"
        "- label은 핵심 대상과 변화 축을 담되 30자를 넘지 않습니다.\n"
        "- question은 필요한 관측 정보와 판단 대상을 충분히 포함하며 글자 수 제한이 없습니다.\n"
        "- rationale은 최대 200자의 구체적인 한국어 한 문장입니다. question의 관측일·분석 기준일·수치·시장 "
        "신호·대상·영향 경로를 생략하지 않고, 질문 어미만 `...하는지에 따라` 형태로 바꿔 Scenario와 JKM "
        "결과가 구분되는 이유를 설명합니다. 최소 글자 수는 강제하지 않습니다.\n"
        "- Choice label은 비교 가능한 하나의 시장·운영 상태를 30자 이내로 작성합니다.\n"
        "- lever와 axis는 source 질문의 값을 그대로 사용하고 Choice는 2~4개를 만듭니다.\n"
        "- pressure coverage 예시: Choice 2개는 `bearish / bullish`, 3개는 `bearish / balanced / bullish`, "
        "4개는 `bearish / balanced / bullish / bullish`처럼 세 방향을 모두 포함하고 의미상 필요한 한 방향을 "
        "추가합니다.\n"
        "- pressure는 `bearish`, `balanced`, `bullish`만 사용합니다. `strong_bearish`와 `strong_bullish`는 "
        "Scenario 합산 pressure band이며 Dimension value에 사용하지 않습니다.\n"
        "- 각 Choice의 states 항목은 정확히 `lever|direction|level|scope|timeWindow` 형식입니다. 다섯 부분을 `|`로 "
        "구분하고 빈 부분을 만들지 않습니다.\n"
        f"- direction은 {StateDirection.prompt_values()} 중 하나만 사용합니다.\n"
        "- 첫 번째 state의 lever는 반드시 Dimension의 source Lever와 같아야 합니다. 한 Choice 안에서 같은 Lever "
        "code를 중복하지 않습니다.\n"
        "- 올바른 states 예시: `liquefaction_utilization|increase|feedgas 유입이 설비 가동으로 전환|미국 LNG "
        "수출설비|2026-08-20 이후 단기`\n"
        "- 잘못된 Group 441 형태: `LNG 수출 설비로의 가스 유입 증가가 실제 액화설비 가동률과 수출 가능 물량 "
        "증가로 이어지는 상태`처럼 자연어 문장만 작성하면 안 됩니다.\n"
        "- 서로 다른 Choice는 label과 states 조합이 중복되면 안 됩니다.\n"
        "- why는 제공된 관측 사실을 기반으로 `관측된 사실 → 미래 상태 → JKM 영향`을 한 문장으로 연결하고, "
        "문장 끝의 `가정`으로만 불확실성을 표시합니다. `답`, `응답`, `선택`이라는 말이나 새 사실을 만들지 않습니다.\n"
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


def _render_group_metadata_event_cards(events: list[dict[str, Any]]) -> str:
    cards = []
    for index, event in enumerate(events, start=1):
        compact = CompactEventContext.from_event(event)
        facts = "\n".join(f"  - {fact}" for fact in compact.key_facts) or "  - 없음"
        tags = ", ".join(compact.tags) or "없음"
        cards.append(
            f"### [이벤트 {index}]\n"
            f"- ID: {compact.event_id or '없음'}\n"
            f"- 제목: {compact.title[:120] or '없음'}\n"
            f"- 요약: {compact.summary[:240] or '없음'}\n"
            f"- 발생시각: {compact.occurred_at or '없음'}\n"
            f"- 핵심 사실:\n{facts}\n"
            f"- 태그: {tags}"
        )
    return "\n\n".join(cards) or "- 없음"


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
    events: list[dict[str, Any]],
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
        "## 그룹 제목·설명의 근거가 되는 이벤트\n"
        f"{_render_group_metadata_event_cards(events)}\n\n"
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
        "- 루트 title과 description은 개별 시나리오가 아니라 시나리오 그룹의 화면용 메타데이터입니다.\n"
        "- 루트 title은 20~60자의 한국어로 작성합니다. 여러 이벤트이면 위 이벤트에서 사용자가 검색할 만한\n"
        "  구체적인 대상·지역·지표·변화 2~3개를, 단일 이벤트이면 대표 요소 1개를 제목에 직접 반영합니다.\n"
        "  `JKM 대표 전개`, `합성 초안`, `복수 이벤트 시나리오`처럼 생성 목적만 표현하지 않습니다.\n"
        "  `선택 MI Event`, `모델 영향 레버`, `복수 이벤트 시나리오`처럼 생성 방식 중심의 일반 문구를 쓰지 않습니다.\n"
        "- 루트 description은 정확히 두 문장으로 작성합니다. 첫 문장은 관측된 이벤트 사실을 직접 서술하고\n"
        "  `반영한다`, `바탕으로 한다`, `정리한다` 같은 메타 표현을 쓰지 않습니다. 둘째 문장은 Dimension 이름을\n"
        "  나열하지 않고 충격의 지속·전달·증폭과 대체·회복·상쇄 같은 인과 묶음으로 핵심 분기를 설명합니다.\n"
        "- description의 인과 관계는 검증된 Event fact, impact path, interaction, Dimension에 있는 내용만 사용합니다.\n"
        "  독립 이벤트에는 임의의 상호작용을 만들지 않습니다. 발생한 사건은 `이벤트`, 미래 분기는 `시나리오`로\n"
        "  지칭합니다. 영문 `Event`, `Scenario`를 쓰지 않습니다. 이 규칙은 루트 title과 description에\n"
        "  모두 적용합니다. description에는\n"
        "  `입력 사실`과 `JKM`을 쓰지 않습니다.\n"
        "- Scenario 3~5개를 만들고 생성·제외 결과를 합쳐 다섯 pressure band를 한 번씩 다룹니다.\n"
        "- choices에는 각 D의 V를 정확히 하나씩 `D1.V1` 형식으로 선택합니다.\n"
        "- 제외 후보도 choices에 각 D의 V를 정확히 하나씩 선택해, 제외된 실제 조합을 보존합니다.\n"
        "- 발생 가능성이 낮아 제외하면 reasonCode는 LOW_PROBABILITY로 작성합니다. 조합이 독립적인 검토 가치가\n"
        "  없어 제외하는 경우에는 NOT_INDEPENDENT를 사용합니다.\n"
        "- interactions에는 실제로 추가 효과를 적용한 I 번호만 넣습니다.\n"
        "- 각 Scenario는 다른 Scenario와 구분되는 핵심 전제 조합과 결과 전달 경로를 가져야 합니다.\n"
        "- 공급·수요·운송·회복 같은 미리 정한 유형에 맞추지 말고, 입력된 Dimension과 Interaction에서\n"
        "  Scenario별 구분 요인을 선택합니다. pressure 단계만 한 칸씩 바꾼 유사 조합을 반복하지 않습니다.\n"
        "- title은 핵심 조건이나 메커니즘을 40자 이내로 표현합니다.\n"
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
        "- probability는 공통 사실에 가깝고 추가 가정이 적을수록 높게 부여하는 0~100 정수 백분율입니다. "
        "모든 Scenario probability의 합계를 정확히 100으로 맞춥니다.\n"
        "- relatedMarkets는 `TTF|이유` 또는 `HH|이유` 형식이며 특별한 영향이 있을 때만 씁니다. "
        "한 Scenario 안에서 TTF와 HH는 각각 최대 한 번만 작성하고 같은 시장을 중복하지 마십시오.\n"
        f"{feedback}"
    )


__all__ = [
    "MODEL_LEVER_SYSTEM_PROMPT",
    "V4_ADDITIONAL_DIMENSION_SYSTEM_PROMPT",
    "V4_DIMENSION_SYSTEM_PROMPT",
    "V4_EVENT_IMPACT_SYSTEM_PROMPT",
    "V4_INTERACTION_SYSTEM_PROMPT",
    "V4_SCENARIO_SYSTEM_PROMPT",
    "build_model_lever_user_prompt",
    "build_v4_dimension_design_user_prompt",
    "build_v4_additional_dimension_user_prompt",
    "build_v4_event_fact_candidates",
    "build_v4_event_impact_analysis_user_prompt",
    "event_open_question_budgets",
    "event_open_question_recommendations",
    "build_v4_interaction_analysis_user_prompt",
    "build_v4_scenario_synthesis_user_prompt",
]
