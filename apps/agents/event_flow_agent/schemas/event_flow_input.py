#   agents/event_flow_agent/schemas/event_flow_input.py
#   kmj20260414화
"""
Event Flow 입력 스키마 모듈

역할:
- event_flow_agent 외부 입력 형식을 정의한다.
- API 또는 runnable 진입점에서 전달되는 입력값의 기본 검증을 담당한다.

입력 정보:
- limit: 조회/처리 건수 제한

설계 의도:
- 외부 입력과 내부 상태를 분리
- 최소 입력 계약을 명확히 정의하여 graph 진입 전 검증 수행
- 이후 필요 시 입력 파라미터를 확장하기 쉬운 구조 제공
"""

from __future__ import annotations

from pydantic import BaseModel, Field

class EventFlowInput(BaseModel):
    limit: int = Field(
        default=20,
        description="RDB 조회 건수 제한",
    )