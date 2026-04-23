#   apps/agents/event_flow_agent/flows/event_flow_graph.py
#   kmj20260423목

"""
Event Flow Graph 구성 모듈

역할:
- event_flow_agent의 전체 실행 흐름(StateGraph)을 정의한다.
- 각 노드의 실행 순서와 연결 관계를 명시한다.
- 최종적으로 LangGraph Runnable 객체를 생성하고 재사용 가능하게 제공한다.

전체 처리 흐름:
1. read_record_source
   - 원천 뉴스/레코드 조회
2. analyze_records_with_llm
   - 각 record를 LLM으로 분석하여 구조화된 category/tag 생성
3. extract_events_with_llm
   - record 분석 결과를 바탕으로 event 단위로 통합/추출
4. save_events
   - 추출된 event를 DB에 저장
5. read_rdb
   - 저장된 event를 DB에서 다시 조회
6. analyze_with_llm
   - 조회된 event 목록을 최종 요약/분석

설계 의도:
- node 단위 책임을 분리하고, graph에서는 오직 실행 순서와 연결만 관리한다.
- 상태(EventFlowState)는 각 node를 거치며 점진적으로 확장된다.
- graph 자체는 "무슨 순서로 실행할지"만 정의하고,
  각 단계의 상세 로직은 node/service/repository로 위임한다.

특징:
- 단일 선형 파이프라인 구조
- 조건 분기 없이 순차 실행
- 실행 종료 지점은 analyze_with_llm 이후 END
"""

from __future__ import annotations

from langchain_core.runnables import Runnable
from langgraph.graph import END, StateGraph

from apps.agents.event_flow_agent.nodes.analyze_records_with_llm import (
    analyze_records_with_llm_node,
)
from apps.agents.event_flow_agent.nodes.analyze_with_llm import analyze_with_llm_node
from apps.agents.event_flow_agent.nodes.extract_events_with_llm import (
    extract_events_with_llm_node,
)
from apps.agents.event_flow_agent.nodes.read_rdb import read_rdb_node
from apps.agents.event_flow_agent.nodes.read_record_source import (
    read_record_source_node,
)
from apps.agents.event_flow_agent.nodes.save_events import save_events_node
from apps.agents.event_flow_agent.state.event_flow_state import EventFlowState


def build_event_flow_agent() -> Runnable:
    graph = StateGraph(state_schema=EventFlowState)

    graph.add_node("read_record_source", read_record_source_node)
    graph.add_node("analyze_records_with_llm", analyze_records_with_llm_node)
    graph.add_node("extract_events_with_llm", extract_events_with_llm_node)
    graph.add_node("save_events", save_events_node)
    graph.add_node("read_rdb", read_rdb_node)
    graph.add_node("analyze_with_llm", analyze_with_llm_node)

    graph.set_entry_point("read_record_source")

    graph.add_edge("read_record_source", "analyze_records_with_llm")
    graph.add_edge("analyze_records_with_llm", "extract_events_with_llm")
    graph.add_edge("extract_events_with_llm", "save_events")
    graph.add_edge("save_events", "read_rdb")
    graph.add_edge("read_rdb", "analyze_with_llm")
    graph.add_edge("analyze_with_llm", END)

    return graph.compile()


_event_flow_agent = build_event_flow_agent()


def get_event_flow_agent() -> Runnable:
    return _event_flow_agent