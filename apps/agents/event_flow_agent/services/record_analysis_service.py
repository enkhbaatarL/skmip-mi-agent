# apps/agents/event_flow_agent/services/record_analysis_service.py

from __future__ import annotations
import asyncio
from datetime import datetime, timezone
import httpx
from openai import OpenAI
from apps.agents.event_flow_agent.schemas.record_analysis import RecordAnalysis
from apps.common.configs.settings import get_settings


SYSTEM_PROMPT = """\
당신은 LNG 시장 분석 전문가이다.
주어진 뉴스 기사/요약을 분석하여 LNG 가격 예측에 활용할 구조화된 분석 태그를 추출해라.

반드시 아래 규칙을 지켜라.
- categories는 반드시 1개 이상이어야 한다.
- 각 category마다 level_1, level_2, entities, event_timing, regions, supply_demand_side, score, reason을 채워라.
- score는 0~10 범위이다.
- JSON schema를 반드시 준수해라.
- 빈 리스트([])를 반환하지 마라.
- 가장 관련도 높은 카테고리 1개라도 반드시 포함해라.
"""

USER_TEMPLATE = """\
다음 record를 분석하여 RecordAnalysis를 생성해라.

## 제목
{title}

## 본문
{body}
"""


class RecordAnalysisService:
    def __init__(self) -> None:
        settings = get_settings()
        self._model_endpoint = settings.model_endpoint
        self._api_key = settings.api_key
        self._model_name = settings.model_api_deployment_name

    async def analyze(self, title: str, body: str) -> RecordAnalysis:
        prompt = USER_TEMPLATE.format(title=title, body=body)

        def _call_llm() -> RecordAnalysis:
            client = OpenAI(
                base_url=self._model_endpoint,
                api_key=self._api_key,
                http_client=httpx.Client(
                    verify=False,
                    timeout=30.0,
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
                        "name": "RecordAnalysis",
                        "schema": RecordAnalysis.model_json_schema(),
                        "strict": False,
                    },
                },
            )

            content = resp.choices[0].message.content
            if not content:
                raise ValueError("LLM 응답 content가 비어 있습니다.")

            parsed = RecordAnalysis.model_validate_json(content)
            parsed.analysis_time = datetime.now(timezone.utc).isoformat()
            return parsed

        return await asyncio.to_thread(_call_llm)