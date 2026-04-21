#   agents/event_flow_agent/schemas/event_flow_output.py
#   kmj20260421화 수정

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class EventFlowOutput(BaseModel):
    summary: str = Field(default="", description="최종 요약")
    llm_result: str = Field(default="", description="LLM 분석 결과")
    rdb_result: list[dict[str, Any]] = Field(default_factory=list, description="RDB 조회 결과")

    errors: list[str] = Field(default_factory=list, description="실행 중 발생한 오류")
    executed_nodes: list[str] = Field(default_factory=list, description="실행된 노드")
    saved_event_ids: list[str] = Field(default_factory=list, description="저장된 event id 목록")

    source_records_count: int = Field(default=0)
    record_analyses_count: int = Field(default=0)
    extracted_events_count: int = Field(default=0)