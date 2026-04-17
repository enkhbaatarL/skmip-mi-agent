# apps/agents/event_flow_agent/services/event_extraction_service.py

from __future__ import annotations

import json

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

from apps.agents.event_flow_agent.schemas.mi_event_models import MIEventList

SYSTEM_PROMPT = """\
당신은 LNG 시장 이벤트 추출 전문가입니다.
여러 record 분석 결과를 입력받아 동일 사건을 Event 단위로 병합하세요.
각 Event는 하나의 event_type만 가집니다.
"""

USER_PROMPT = """\
총 {n_records}개의 record 분석 결과입니다.

{records_json}
"""

PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", USER_PROMPT),
    ]
)


class EventExtractionService:
    def __init__(self, model_name: str, max_tokens: int = 8192) -> None:
        self._llm = ChatAnthropic(
            model=model_name,
            temperature=0,
            max_tokens=max_tokens,
        )
        self._chain = PROMPT | self._llm.with_structured_output(MIEventList)

    def _compact_records(self, records: list[dict]) -> str:
        compact = []
        for record in records:
            compact.append(
                {
                    "mi_record_id": record.get("mi_record_id"),
                    "record_analysis": record.get("record_analysis", {}),
                }
            )
        return json.dumps(compact, ensure_ascii=False)

    async def extract(self, records: list[dict]) -> MIEventList:
        return await self._chain.ainvoke(
            {
                "n_records": len(records),
                "records_json": self._compact_records(records),
            }
        )