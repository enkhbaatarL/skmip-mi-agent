#   agents/event_flow_agent/schemas/event_flow_output.py
#   kmj20260421화 수정
"""
Event Flow 출력 스키마 모듈

역할:
- event_flow_agent 실행 결과를 외부 응답 형식으로 정의한다.
- 최종 요약, LLM 결과, DB 조회 결과 등 사용자에게 반환할 필드를 관리한다.

출력 정보:
- 최종 summary
- llm_result
- rdb_result
- 필요 시 디버깅/관측용 메타 정보

설계 의도:
- 내부 실행 상태(EventFlowState)를 그대로 노출하지 않고,
  외부 인터페이스에 필요한 정보만 선별하여 제공
- API 응답 계약을 명확히 정의하여 변경 영향을 통제
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class EventFlowOutput(BaseModel):
    summary: str = Field(default="", description="최종 요약")
    llm_result: str = Field(default="", description="LLM 분석 결과")
    rdb_result: list[dict[str, Any]] = Field(default_factory=list, description="RDB 조회 결과")

    errors: list[str] = Field(default_factory=list, description="실행 중 발생한 오류")
    executed_nodes: list[str] = Field(default_factory=list, description="실행된 노드")
    saved_event_ids: list[int] = Field(default_factory=list,description="저장된 event id 목록")

    source_records_count: int = Field(default=0)
    record_analyses_count: int = Field(default=0)
    extracted_events_count: int = Field(default=0)