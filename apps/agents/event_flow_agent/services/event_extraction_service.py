# apps/agents/event_flow_agent/services/event_extraction_service.py
#   kmj20260421화 수정
"""
event 추출 서비스 모듈

역할:
- record별 분석 결과를 입력받아,
  서로 연관된 분석 결과를 통합하여 event 단위 결과를 생성한다.
- 여러 record를 하나 이상의 시장 event로 재구성한다.

입력:
- record 분석 결과 목록

출력:
- MIEventList 객체

설계 의도:
- record 단위 분석을 실제 저장 가능한 event 단위 데이터로 변환
- 동일 사건을 여러 record에서 감지했을 때 하나의 event로 통합할 수 있도록 설계
- LLM 호출은 connector를 사용하고, service는 입력 정리와 프롬프트 책임만 담당
"""

from __future__ import annotations

import json

from apps.agents.event_flow_agent.configs.event_type_taxonomy import CATEGORY_GUIDE
from apps.agents.event_flow_agent.schemas.mi_event_models import MIEventList
from apps.connectors.llm.llm_client import invoke_llm_structured_output


SYSTEM_PROMPT = f"""\
당신은 LNG(액화천연가스) 시장 이벤트 추출 전문가이다.
이미 AI로 1차 분석된 Record 결과들을 입력받아, LNG 관련 Event들을 정의해라.

## 가장 중요한 원칙
1. Record ↔ Event 는 N:M 관계이다.
   - 여러 Record에 공통으로 등장하는 동일 사건은 하나의 Event로 병합하고,
     evidence_record_ids 에 해당 Record들의 mi_record_id 를 모두 포함해라.
   - 하나의 Record가 여러 Event의 근거가 될 수 있다.
2. 각 Event는 정확히 하나의 event_type(level_1 + level_2)만 가진다.
3. event_type은 아래 taxonomy 조합만 사용해야 한다.
4. 임의의 분류명은 만들지 마라.
5. JSON schema를 반드시 준수해라.

## 허용 taxonomy
{CATEGORY_GUIDE}

## 출력 규칙
- events는 반드시 1개 이상이어야 한다.
- event_title_ko는 한국어 한 줄 제목이다.
- one_line_summary는 100자 이내로 작성한다.
- key_bullets는 3~5개이다.
- detail_analysis는 key_bullets를 풀어쓴 상세 설명이다.
- market_and_institution_view는 기사/record에 근거가 없으면 빈 문자열로 둔다.
- evidence_record_ids는 반드시 1개 이상이어야 한다.
- occurred_at은 특정 가능하면 ISO-8601, 아니면 빈 문자열이다.
"""

USER_TEMPLATE = """\
아래는 총 {n_records}개의 Record 분석 결과이다.
이를 기반으로 LNG 시장 Event 들을 추출하여 MIEventList 로 반환해라.

## Record 분석 결과 (JSON)
{records_json}
"""


class EventExtractionService:
    def _compact_records(self, records: list[dict]) -> str:
        compact = []
        for record in records:
            compact.append(
                {
                    "mi_record_id": record.get("mi_record_id"),
                    "record_type": record.get("record_type"),
                    "title": record.get("title", ""),
                    "record_analysis": record.get("record_analysis", {}),
                }
            )
        return json.dumps(compact, ensure_ascii=False, indent=2)

    async def extract(self, records: list[dict]) -> MIEventList:
        records_json = self._compact_records(records)
        prompt = USER_TEMPLATE.format(
            n_records=len(records),
            records_json=records_json,
        )

        llm_result = await invoke_llm_structured_output(
            output_schema=MIEventList,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        return llm_result.result