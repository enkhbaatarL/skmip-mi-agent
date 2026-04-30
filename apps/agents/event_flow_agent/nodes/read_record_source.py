# apps/agents/event_flow_agent/nodes/read_record_source.py
#   kmj20260421화 수정
"""
원천 record 조회 노드

역할:
- event_flow_agent 실행의 시작점으로서, 분석 대상이 되는 원천 뉴스/레코드를 DB에서 조회한다.
- market_category, 기간, limit 조건을 바탕으로 source record 목록을 가져와 state에 적재한다.

입력:
- EventFlowState의 market_category, from_first_created, to_first_created, limit

출력:
- state.source_records 에 원천 record 목록 저장

설계 의도:
- 이후 LLM 분석 및 event 추출의 입력 데이터를 준비하는 단계
- node는 조회 흐름만 담당하고, 실제 DB 접근은 service/repository에 위임
"""

from __future__ import annotations

from apps.agents.event_flow_agent.services.record_source_service import RecordSourceService
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState
from apps.common.logging.decorators import log_node
import json

@log_node
def read_record_source_node(state: EventFlowState) -> EventFlowState:
    state.current_node = "read_record_source"
    state.executed_nodes.append("read_record_source")

    try:
        records = RecordSourceService().fetch_news_records(
            market_category=state.market_category,
            limit=state.limit,
            from_first_created=state.from_first_created,
            to_first_created=state.to_first_created,
        )
        state.source_records = records

        # Save analysis result to demo file
        with open('./docs/demos/record_read.json', 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        print('Saved read record to ./docs/demos/record_read.json')      

        return state

    except Exception as exc:
        state.source_records = []
        state.errors.append(f"원천 record 조회 실패: {exc}")
        return state