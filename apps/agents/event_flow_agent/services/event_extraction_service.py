# apps/agents/event_flow_agent/services/event_extraction_service.py

from __future__ import annotations

import asyncio
import json

import httpx
from openai import OpenAI

from apps.agents.event_flow_agent.schemas.mi_event_models import MIEventList
from apps.common.configs.settings import get_settings
from apps.agents.event_flow_agent.configs.event_type_taxonomy import CATEGORY_GUIDE


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
    def __init__(self) -> None:
        settings = get_settings()
        self._model_endpoint = settings.model_endpoint
        self._api_key = settings.api_key
        self._model_name = settings.model_api_deployment_name

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

        def _call_llm() -> MIEventList:
            client = OpenAI(
                base_url=self._model_endpoint,
                api_key=self._api_key,
                http_client=httpx.Client(
                    verify=False,
                    timeout=60.0,
                ),
                max_retries=2,
            )

            resp = client.chat.completions.create(
                model=self._model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.0,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "MIEventList",
                        "schema": MIEventList.model_json_schema(),
                        "strict": False,
                    },
                },
            )

            content = resp.choices[0].message.content
            if not content:
                raise ValueError("LLM 응답 content가 비어 있습니다.")

            parsed = MIEventList.model_validate_json(content)
            return parsed

        return await asyncio.to_thread(_call_llm)