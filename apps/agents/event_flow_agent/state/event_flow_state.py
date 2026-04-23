#   agents/event_flow_agent/state/event_flow_state.py
#   kmj20260423목
"""
Event Flow 실행 상태(State) 정의 모듈

역할:
- event_flow_agent가 실행되는 동안 단계별 데이터를 누적/전달하는 공용 상태 객체를 정의한다.
- 각 node는 이 상태 객체를 입력받아 필요한 값을 읽고, 처리 결과를 다시 상태에 반영한다.

포함 정보:
- 입력 파라미터(limit, market_category, 기간 등)
- 원천 record 조회 결과
- record별 LLM 분석 결과
- 추출된 event 목록
- 저장된 event ID 목록
- DB 재조회 결과
- 최종 요약/LLM 결과
- 실행 중 오류 및 실행 노드 추적 정보

설계 의도:
- graph 기반 파이프라인에서 노드 간 데이터를 명시적으로 공유
- 입력 스키마(EventFlowInput)를 확장하여 실행 중간 결과까지 함께 관리
- 디버깅, 관측, 후속 응답 변환에 필요한 메타정보를 한 곳에 집약
"""

from __future__ import annotations
from typing import Any
from pydantic import Field
from apps.agents.event_flow_agent.schemas.event_flow_input import EventFlowInput

class EventFlowState(EventFlowInput):
    rdb_result: list[dict[str, Any]] = Field(
        default_factory=list,
        description="RDB에서 조회한 원본 결과",
    )
    summary: str | None = Field(
        default=None,
        description="RDB 조회 결과 요약",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="실행 중 발생한 에러 메시지 목록",
    )
    current_node: str | None = Field(
        default=None,
        description="현재 실행 중인 노드",
    )
    executed_nodes: list[str] = Field(
        default_factory=list,
        description="실행된 노드 목록",
    )
    usage: dict | None = Field(
        default=None,
        description="향후 LLM 사용량 정보 저장용",
    )

    # kmj20260417, record -> event 확장 필드
    market_category: str = Field(
        default="LNG",
        description="원천 record 조회용 시장 구분",
    )
    from_first_created: str | None = Field(
        default=None,
        description="원천 record 조회 시작 시각",
    )
    to_first_created: str | None = Field(
        default=None,
        description="원천 record 조회 종료 시각",
    )
    limit: int = Field(
        default=50,
        description="원천 record 조회 최대 건수",
    )

    source_records: list[dict[str, Any]] = Field(
        default_factory=list,
        description="tmd_mi_record 기준으로 resolve한 원천 record 목록",
    )
    record_analyses: list[dict[str, Any]] = Field(
        default_factory=list,
        description="record별 LLM 분석 결과 목록",
    )
    extracted_events: list[dict[str, Any]] = Field(
        default_factory=list,
        description="record 분석 결과로부터 추출한 event 목록",
    )
    saved_event_ids: list[int] = Field(
        default_factory=list,
        description="DB에 저장한 mi_event_id 목록",
    )
    
    llm_result: str | None = Field(
        default=None,
        description="LLM 요약 결과 원문",
    )
    llm_prompt: str | None = Field(
        default=None,
        description="LLM 호출에 사용한 프롬프트",
    )