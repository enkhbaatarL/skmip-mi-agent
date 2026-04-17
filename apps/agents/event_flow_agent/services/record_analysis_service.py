# apps/agents/event_flow_agent/services/record_analysis_service.py

from __future__ import annotations
from datetime import datetime, timezone
from apps.agents.event_flow_agent.schemas.record_analysis import RecordAnalysis
from apps.connectors.llm.llm_client import invoke_llm_structured_output


SYSTEM_PROMPT = """\
당신은 LNG 시장 분석 전문가이다.
주어진 뉴스 기사/요약을 분석하여 LNG 가격 예측에 활용할 구조화된 분석 태그를 추출해라.

반드시 아래 규칙을 지켜라.
- categories는 반드시 1개 이상이어야 한다.
- 각 category마다 level_1, level_2, entities, event_timing, regions, supply_demand_side, score, reason을 채워라.
- score는 0~10 범위이다.
- JSON schema를 반드시 준수해라.
"""

USER_TEMPLATE = """\
다음 record를 분석하여 RecordAnalysis를 생성해라.

## 제목
{title}

## 본문
{body}
"""


class RecordAnalysisService:
    async def analyze(self, title: str, body: str) -> RecordAnalysis:
        prompt = USER_TEMPLATE.format(title=title, body=body)

        result = await invoke_llm_structured_output(
            output_schema=RecordAnalysis,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )

        parsed = result.result
        parsed.analysis_time = datetime.now(timezone.utc).isoformat()

        return parsed