#   apps/agents/event_flow_agent/nodes/read_rdb.py
#   kmj20260421화 수정
"""
저장된 event 재조회 노드

역할:
- DB에 저장된 event 데이터를 다시 조회하여 후속 요약/분석 단계의 입력으로 사용한다.
- 최신 event 목록을 읽어 state.rdb_result 에 적재한다.

입력:
- state.limit

출력:
- state.rdb_result 에 DB 조회 결과 저장
- state.summary 에 조회 건수 요약 저장 가능

설계 의도:
- 저장 직후의 event 결과를 기준으로 최종 요약을 수행하기 위한 조회 단계
- DB 적재 결과를 다시 읽어 후속 LLM 요약과 연결
"""

from __future__ import annotations

from apps.agents.event_flow_agent.services.event_service import EventService
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


async def read_rdb_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "read_rdb"
    state.executed_nodes.append("read_rdb")

    try:
        rows = EventService().get_events(limit=state.limit)
        state.rdb_result = rows
        state.summary = f"midb 에서 {len(rows)}건 조회했습니다."
        return state

    except Exception as e:
        msg = f"RDB 조회 중 오류가 발생했습니다: {e!s}"
        state.rdb_result = []
        state.summary = msg
        state.errors.append(msg)
        return state