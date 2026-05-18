# apps/agents/event_flow_agent/services/record_analysis_service.py
#   kmj20260421화 수정
"""
record 단위 LLM 분석 서비스 모듈

역할:
- 개별 뉴스/레코드의 제목과 본문을 입력받아
  LNG 시장 관점의 구조화된 분석 결과를 생성한다.
- category, entity, timing, region, score 등의 정보를 포함한 RecordAnalysis를 반환한다.

입력:
- record 제목
- record 본문

출력:
- RecordAnalysis 객체

설계 의도:
- 비정형 뉴스 텍스트를 event 추출에 적합한 구조화 데이터로 변환
- LLM 호출 구현은 connector 계층에 위임하고,
  service는 프롬프트 구성과 도메인 후처리에 집중
"""

from __future__ import annotations
import json

from datetime import datetime, timezone

from apps.agents.event_flow_agent.configs.event_type_taxonomy import CATEGORY_GUIDE
from apps.agents.event_flow_agent.schemas.record_analysis import RecordAnalysis
from apps.connectors.llm.llm_client import invoke_llm_structured_output
from apps.common.logging.decorators import log_tool


SYSTEM_PROMPT = f"""\
당신은 LNG 시장 분석 전문가이다.
주어진 뉴스 기사/요약을 분석하여 LNG 가격 예측에 활용할 구조화된 분석 태그를 추출해라.

반드시 아래 규칙을 지켜라.
- categories는 반드시 1개 이상이어야 한다.
- 각 category마다 level_1, level_2, entities, event_timing, regions, supply_demand_side, score, reason을 채워라.
- score는 0~10 범위이다.
- JSON schema를 반드시 준수해라.
- 빈 리스트([])를 반환하지 마라.
- 가장 관련도 높은 카테고리 1개라도 반드시 포함해라.
- level_1 / level_2는 아래 taxonomy 코드만 사용해야 한다.
- 한국어 라벨이 아니라 반드시 코드값을 사용해라.
- 아래에 없는 임의의 분류명은 절대 만들지 마라.

## 허용 taxonomy
{CATEGORY_GUIDE}

### entities
- category별로 이벤트를 일으키거나 직접 영향을 받는 주체만 포함합니다.
- entity_type: country(국가) / company(기업) / facility(설비·터미널) / organization(기관·단체) / other

### event_timing
- category별 이벤트 실제 발생 시점. ISO-8601("2026-03-03T00:00:00Z") 또는 빈 문자열("").
- occurrence_time_precision: exact / day / month / quarter / year / unknown
- **연도 결정 규칙 (반드시 준수)**
  - USER 프롬프트로 함께 전달되는 `first_created` (뉴스 보도 시점) 의 연도를 "현재 연도"로 간주합니다.
  - 본문/제목에 연도가 명시되지 않고 월/일만 언급된 경우 (예: "4월 16일", "지난주", "이번 달"), 반드시 `first_created` 의 연도를 사용하세요.
  - 본문에서 "지난해", "작년" 이라고 명시된 경우에 한해 `first_created.year - 1` 을 사용하세요.
  - 본문에 명확한 연도가 명시된 경우 그 연도를 우선합니다.
  - **절대 자신의 학습 데이터(과거 시점) 기준으로 연도를 추정하지 마세요.** 입력으로 주어진 `first_created` 만이 "지금" 의 기준입니다.
  - 시점이 모호하면 occurrence_time = "" 으로 두고 occurrence_time_precision = "unknown" 으로 표기하세요.

### regions
- category별 이벤트와 직접 관련된 지역. 예: "중동", "동북아", "유럽", "북미", "호주", "남아시아"
"""

USER_TEMPLATE = """\
다음 record를 분석하여 RecordAnalysis를 생성해라.

## 뉴스 보도 시점 (first_created)
- first_created: {first_created}
- 이 값을 "현재 시점"으로 간주하고, event_timing.occurrence_time 의 연도 결정에 활용하세요.
  (시스템 프롬프트의 "연도 결정 규칙" 참조)

## 제목
{title}

## 본문
{body}
"""


class RecordAnalysisService:
    @log_tool
    async def analyze(self, first_created:str, title: str, body: str) -> RecordAnalysis:
        prompt = USER_TEMPLATE.format(first_created=first_created, title=title, body=body)

        llm_result = await invoke_llm_structured_output(
            output_schema=RecordAnalysis,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        parsed = llm_result.result
        parsed.analysis_time = datetime.now(timezone.utc).isoformat()
        
        # Save analysis result to demo file
        with open('./docs/demos/record_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(parsed.model_dump(), f, ensure_ascii=False, indent=2)
        
        print('Saved record analysis to ./docs/demos/record_analysis.json')
        return parsed