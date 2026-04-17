#   apps/agents/event_flow_agent/nodes/analyze_with_llm.py

from __future__ import annotations

from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState
from apps.connectors.llm.llm_client import invoke_llm_function_call


async def analyze_with_llm_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "analyze_with_llm"
    state.executed_nodes.append("analyze_with_llm")

    try:
        rows = state.rdb_result

        if not rows:
            state.llm_result = ""
            state.summary = "분석할 데이터가 없습니다."
            return state

        # 🔥 prompt 구성
        text = "\n\n".join(
            [
                f"- 제목: {row.get('title')}\n"
                f"  내용: {row.get('content')}"
                for row in rows
            ]
        )

        messages = [
            {
                "role": "system",
                "content": "너는 데이터 분석 전문가다.",
            },
            {
                "role": "user",
                "content": f"""
다음 이벤트들을 분석해서:

1. 전체 요약 (3줄)
2. 핵심 키워드 3개
3. 중요한 이벤트 2개

를 한국어로 작성해라.

{text}
""",
            },
        ]

        # 🔥 실제 LLM 호출
        resp = await invoke_llm_function_call(messages=messages)

        state.llm_result = resp["content"]
        state.summary = "RDB 조회 및 LLM 분석 완료"
        return state

    except Exception as e:
        msg = f"LLM 호출 실패: {e!s}"
        state.errors.append(msg)
        state.summary = msg
        state.llm_result = ""
        return state