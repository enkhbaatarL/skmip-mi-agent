# apps/agents/event_flow_agent/schemas/mi_event_models.py
#   kmj20260423목
"""
추출 event 구조 스키마 모듈

역할:
- LLM이 생성하는 event 단위 결과의 구조를 정의한다.
- event 제목, 한 줄 요약, 상세 분석, event type, 근거 record ID 등
  저장 가능한 event 데이터 모델을 표준화한다.

포함 정보:
- 개별 event(MIEvent)
- event type 참조(EventTypeRef)
- event 목록(MIEventList)

설계 의도:
- event 추출 단계의 structured output 스키마로 사용
- LLM 응답을 저장 가능한 도메인 객체 형태로 강제
- event 저장/후처리 단계에서 일관된 데이터 구조 보장
"""

from __future__ import annotations
from typing import Annotated, List
from pydantic import BaseModel, Field

class EventTypeRef(BaseModel):
    level_1: str
    level_2: str

KeyBullets = Annotated[list[str], Field(min_length=3, max_length=5)]
EvidenceRecordIds = Annotated[list[int], Field(min_length=1)]

class MIEvent(BaseModel):
    event_title_ko: str = Field(default="")
    one_line_summary: str = Field(default="")
    key_bullets: KeyBullets = Field(default_factory=list)
    detail_analysis: str = Field(
        default="",
        description=(
            "key_bullets를 풀어쓴 상세 설명. 정량 수치·고유명사·가정·출처를 포함하여 작성."
            " 기사/Record에 언급되지 않은 숫자는 임의로 생성하지 말 것."
            " 반드시 개조식(명사형 종결) 문체로 작성: 모든 문장은 '...함', '...임', '...됨',"
            " '...음' 등으로 끝내야 하며, '...한다.', '...이다.', '...했다.' 와 같은"
            " 서술형(종결어미) 문장은 사용 금지."
        )
    )
    market_and_institution_view: str = Field(default="")
    event_type: EventTypeRef
    evidence_record_ids: EvidenceRecordIds = Field(default_factory=list)
    occurred_at: str = Field(default="")
    tags: List[str] = Field(default_factory=list)

Events = Annotated[list[MIEvent], Field(min_length=1)]

class MIEventList(BaseModel):
    events: Events = Field(default_factory=list)