#   apps/agents/event_flow_agent/nodes/analyze_with_llm.py
#   kmj20260420월 수정, RDB에서 조회된 이벤트 데이터를 LLM으로 분석하는 노드

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx
from openai import OpenAI

from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState
from apps.common.configs.settings import get_settings


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
        title = row.get("mi_event_title_ko") or ""
        summary = row.get("mi_event_summary_ko") or ""
        occurred_at = row.get("occurred_at") or ""
        level_1 = row.get("mi_event_type_l1_code") or ""
        level_2 = row.get("mi_event_type_l2_code") or ""

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

        settings = get_settings()
        client = OpenAI(
            base_url=settings.model_endpoint,
            api_key=settings.api_key,
            http_client=httpx.Client(
                verify=False,
                timeout=30.0,
            ),
            max_retries=2,
        )

        events_text = _build_events_text(state.rdb_result)
        user_prompt = USER_TEMPLATE.format(events_text=events_text)

        def _call_llm() -> str:
            resp = client.chat.completions.create(
                model=settings.model_api_deployment_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.0,
            )

            content = resp.choices[0].message.content
            if not content:
                raise ValueError("LLM 응답 content가 비어 있습니다.")
            return content.strip()

        result_text = await asyncio.to_thread(_call_llm)

        state.llm_prompt = user_prompt
        state.llm_result = result_text
        state.summary = result_text
        if state.usage is None:
            state.usage = {}
        state.usage["analyze_with_llm_completed_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        return state

    except Exception as exc:
        state.llm_result = ""
        state.summary = f"LLM 호출 실패: {exc}"
        state.errors.append(f"LLM 호출 실패: {exc}")
        return state