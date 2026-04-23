#   apps/agents/event_flow_agent/nodes/analyze_with_llm.py
#   kmj20260421화 수정, RDB에서 조회된 이벤트 데이터를 LLM으로 분석하는 노드
"""
최종 event 요약/분석 노드

역할:
- DB에서 조회한 event 목록을 바탕으로 최종 요약문을 생성한다.
- 전체 event 흐름을 한국어 summary와 llm_result 형태로 정리한다.

입력:
- state.rdb_result

출력:
- state.summary
- state.llm_result
- state.llm_prompt

설계 의도:
- 개별 event 저장 결과를 사람이 읽기 쉬운 최종 요약으로 변환
- API 응답에서 사용자에게 직접 제공되는 최종 분석 단계
"""

from __future__ import annotations

from datetime import datetime, timezone

from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState
from apps.connectors.llm.llm_client import invoke_llm_text

#  kmj20260423, 프롬프트는 명령문으로 작성하세요. 질문문이 아니라, "다음 이벤트들을 분석해라"와 같이 지시문 형태로 작성하는 것이 좋습니다.
SYSTEM_PROMPT = """\
너는 데이터 분석 전문가다.
주어진 이벤트 목록을 바탕으로 아래 형식으로 한국어 요약을 작성해라.

1. 전체 요약 (3줄)
2. 핵심 키워드 3개
3. 중요한 이벤트 2개

반드시 평문 문자열로만 답하고, JSON으로 답하지 마라.
"""

USER_TEMPLATE = """\
다음 이벤트들을 분석해라.

{events_text}
"""

def _build_events_text(rows: list[dict]) -> str:
    if not rows:
        return "이벤트 없음"

    lines: list[str] = []
    for idx, row in enumerate(rows, start=1):
        title = row.get("event_title_ko") or ""
        summary = row.get("detail_analysis") or row.get("one_line_summary") or ""
        occurred_at = row.get("occurred_at") or ""
        level_1 = row.get("level_1_code") or ""
        level_2 = row.get("level_2_code") or ""

        lines.append(
            f"[이벤트 {idx}]\n"
            f"- 발생시각: {occurred_at}\n"
            f"- 유형: {level_1} / {level_2}\n"
            f"- 제목: {title}\n"
            f"- 내용: {summary}\n"
        )

    return "\n".join(lines)

async def analyze_with_llm_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "analyze_with_llm"
    state.executed_nodes.append("analyze_with_llm")

    try:
        if not state.rdb_result:
            state.llm_result = ""
            state.summary = "분석할 데이터가 없습니다."
            return state

        events_text = _build_events_text(state.rdb_result)
        user_prompt = USER_TEMPLATE.format(events_text=events_text)

        result = await invoke_llm_text(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
        )

        state.llm_prompt = user_prompt
        state.llm_result = result["content"]
        state.summary = result["content"]

        if state.usage is None:
            state.usage = {}
        state.usage["analyze_with_llm_completed_at"] = datetime.now(
            timezone.utc
        ).isoformat()
        state.usage["analyze_with_llm_usage"] = result.get("usage")

        return state

    except Exception as exc:
        state.llm_result = ""
        state.summary = f"LLM 호출 실패: {exc}"
        state.errors.append(f"LLM 호출 실패: {exc}")
        return state