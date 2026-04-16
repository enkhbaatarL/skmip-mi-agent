#   agents/event_flow_agent/schemas/event_flow_output.py

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EventFlowOutput(BaseModel):
    summary: str = Field(
        default="",
        description="최종 요약",
    )
    llm_result: str = Field(
        default="",
        description="LLM 분석 결과",
    )
    rdb_result: list[dict[str, Any]] = Field(
        default_factory=list,
        description="RDB 조회 결과",
    )