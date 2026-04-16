#   agents/event_flow_agent/state/event_flow_state.py
#   kmj20260414화

from __future__ import annotations

from typing import Any

from pydantic import Field

from apps.agents.event_flow_agent.schemas.event_flow_input import EventFlowInput


class EventFlowState(EventFlowInput):
    rdb_result: list[dict[str, Any]] = Field(
        default_factory=list,
        description="RDB에서 조회한 원본 결과",
    )
    llm_result: str | None = Field(
        default=None,
        description="LLM 호출 결과",
    )
    summary: str | None = Field(
        default=None,
        description="최종 요약 결과",
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
    usage: dict[str, Any] | None = Field(
        default=None,
        description="LLM 사용량 정보",
    )
    