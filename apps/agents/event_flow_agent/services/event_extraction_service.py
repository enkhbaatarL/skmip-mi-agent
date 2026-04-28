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
import os
from datetime import datetime, timedelta, timezone
from typing import List

from apps.agents.event_flow_agent.configs.event_type_taxonomy import CATEGORY_GUIDE
from apps.agents.event_flow_agent.schemas.mi_event_models import MIEvent, MIEventList
from apps.connectors.llm.llm_client import invoke_llm_structured_output
from apps.common.logging.logger_config import logger
from apps.common.logging.decorators import log_tool


# MAX_PAST_DAYS 값은 최신성 필터 기준과 함께 프롬프트에도 주입한다.
MAX_PAST_DAYS: int = int(os.getenv("MI_EVENT_MAX_PAST_DAYS", "90"))


def _parse_datetime_loose(s) -> datetime | None:
    """Query 원본(`YYYY-MM-DD HH:MM:SS`) / ISO-8601 / Z 접미 등 다양한 포맷을 느슨하게 파싱.

    파싱 실패 시 None. tz-aware/naive 혼재 가능하므로 비교 시 naive 화하여 사용한다.
    """
    if not isinstance(s, str):
        return None
    s = s.strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _as_naive(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def _compute_reference_time(records: List[dict]) -> str:
    """입력 Record 들의 `first_created` 중 가장 최근 값을 "현재 시점"으로 채택.

    - 파싱 가능한 값 중 최댓값을 원본 문자열 그대로 반환(프롬프트/로그에 그대로 노출).
    - 파싱 가능한 값이 하나도 없으면 실행 시점(UTC)을 ISO-8601 로 반환.
    """
    best_dt: datetime | None = None
    best_raw: str = ""
    for r in records:
        raw = r.get("first_created", "")
        dt = _parse_datetime_loose(raw)
        if dt is None:
            continue
        dt_n = _as_naive(dt)
        if best_dt is None or dt_n > best_dt:
            best_dt = dt_n
            best_raw = str(raw)
    if best_raw:
        return best_raw
    return datetime.now(timezone.utc).isoformat()


def _filter_outdated_events(
    result: MIEventList,
    reference_time: str,
    max_past_days: int,
) -> MIEventList:
    """reference_time 대비 `occurred_at` 이 max_past_days 초과 과거인 Event 를 제거.

    - occurred_at 이 비어있거나 파싱 불가능하면 보존(판단 유보).
    - 모든 이벤트가 제거되면 하나도 남지 않는 불안정 상태가 되므로, 이 경우 원본을 유지한다.
    """
    logger.debug(f"[SERVICE][_filter_outdated_events] START | reference_time={reference_time} max_past_days={max_past_days} input_events={len(result.events)}")

    if max_past_days <= 0:
        logger.debug(f"[SERVICE][_filter_outdated_events] SKIP | max_past_days <= 0")
        return result
    
    ref = _parse_datetime_loose(reference_time)
    if ref is None:
        logger.warning(f"[SERVICE][_filter_outdated_events] WARN | reference_time 파싱 실패 value={reference_time!r}")
        return result
    
    threshold = _as_naive(ref) - timedelta(days=max_past_days)

    kept: List[MIEvent] = []
    dropped: List[MIEvent] = []
    
    for ev in result.events:
        occ = _parse_datetime_loose(ev.occurred_at)
        if occ is not None:
            occ_naive = _as_naive(occ)
            if occ_naive < threshold:
                logger.debug(f"[SERVICE][_filter_outdated_events] DROP | occurred_at={ev.occurred_at} title={ev.event_title_ko[:60]!r}")
                dropped.append(ev)
            else:
                logger.debug(f"[SERVICE][_filter_outdated_events] KEEP | occurred_at={ev.occurred_at} title={ev.event_title_ko[:60]!r}")
                kept.append(ev)
        else:
            logger.debug(f"[SERVICE][_filter_outdated_events] KEEP | occurred_at=null title={ev.event_title_ko[:60]!r}")
            kept.append(ev)

    logger.info(f"[SERVICE][_filter_outdated_events] COMPLETE | kept={len(kept)} dropped={len(dropped)} total={len(result.events)}")

    if not kept:
        logger.warning(f"[SERVICE][_filter_outdated_events] FALLBACK | 모든 이벤트 필터링 되어 원본 유지")
        return result

    result.events = kept
    return result


SYSTEM_PROMPT = f"""\
당신은 LNG(액화천연가스) 시장 이벤트 추출 전문가이다.
이미 AI로 1차 분석된 Record 결과들을 입력받아,
LNG 가격(JKM/TTF/HH/NBP) 예측에 유의미한 **Event** 단위로 재구성해라.

## 가장 중요한 원칙
1. Record ↔ Event 는 N:M 관계이다.
   - 여러 Record에 공통으로 등장하는 동일 사건은 하나의 Event로 병합하고,
     evidence_record_ids 에 해당 Record들의 mi_record_id 를 모두 포함해라.
   - 하나의 Record가 여러 Event의 근거가 될 수 있다.
2. 각 Event는 정확히 하나의 event_type(level_1 + level_2)만 가진다.
3. 이벤트의 범위는 "동일한 핵심 사건"을 기준으로 정의합니다.
   - 같은 이슈라도 기사마다 각도가 다르면 evidence 로 모두 묶어 하나의 Event로.
   - 서로 다른 실물 사건은 별도 Event로.
4. **"현재 시점(reference_time)" 기준 최신성 원칙**
   - USER 프롬프트에 주어지는 reference_time 은 입력 Record 들의 `first_created`(뉴스 보도 시점)
     중 가장 최근 값이며, 이를 "현재"로 간주합니다.
   - reference_time 기준 **{MAX_PAST_DAYS}일 이상 과거**의 사건이 핵심인 Event 는 생성하지 마세요.
   - 과거 사건이 "현재 진행 중인 더 큰 사건"의 배경/전개 일부로만 언급되는 경우에는,
     그 사건의 **현재(reference_time 근처) 에피소드**를 중심 Event 로 삼고 과거는
     detail_analysis 본문에서 맥락으로만 언급하세요.
   - 각 Event 의 `occurred_at` 은 해당 이벤트의 **가장 최근(=현재 시점에 가까운) 전개 시점**을
     기준으로 기재하세요. 오래 전 촉발 시점을 적지 마세요.
   - 근거 Record(evidence_record_ids) 는 가능한 한 reference_time 에 가까운 `first_created` 의
     Record 를 우선 선택하세요.

## event_type taxonomy (허용된 level_1 → level_2)
{CATEGORY_GUIDE}

## 각 필드 작성 가이드

### detail_analysis
- key_bullets 를 풀어쓴 상세 설명.
- 정량 수치·고유명사·가정·출처를 최대한 포함.
- **Record 에 언급되지 않은 숫자는 임의로 생성하지 말 것.**
- **문체 규칙 (반드시 준수)**: 개조식(명사형 종결)으로만 작성.
  - 모든 문장은 `...함.`, `...임.`, `...됨.`, `...음.` 과 같은 명사형 어미로 끝낼 것.
  - `...한다.`, `...이다.`, `...있다.`, `...했다.`, `...된다.`, `...이었다.` 등
    서술형(종결어미) 문장은 **절대 사용 금지**.

### market_and_institution_view  (선택)
- Record에 스팟/선물 가격 또는 기관 전망이 언급된 경우에만 작성.
- 근거가 없으면 빈 문자열("")로 두세요.

### occurred_at
- 이벤트 실제 발생 시점이 특정 가능한 경우 ISO-8601 문자열, 아니면 빈 문자열.
- 이벤트가 여러 시점에 걸쳐 전개된 경우, **가장 최근 전개 시점**(reference_time 에 가까운 시점)을
  기준으로 기재하세요. reference_time 기준 {MAX_PAST_DAYS}일 이상 과거가 되면 해당 Event 자체를
  만들지 마세요.

## 출력 가짓수 가이드
- 입력 Record 10건 기준, 통상 4~8개의 Event 가 추출됩니다.

## 강제 제약 조건
- 각 event 의 evidence_record_ids 는 1개 이상이어야 하며, 입력된 mi_record_id 범위 안이어야 합니다.
- key_bullets 는 반드시 3~5개이며, (A)/(B)/(C) 관점이 모두 포함되어야 합니다.
- market_and_institution_view 는 Record에 근거가 없으면 빈 문자열("")로 두세요.
- detail_analysis 는 반드시 개조식(명사형 종결) 문체로 작성하세요.
  모든 문장은 '...함.', '...임.', '...됨.', '...음.' 으로 끝나야 하며,
  '...한다.', '...이다.', '...했다.', '...된다.' 등 서술형 종결어미는 금지합니다.
""".format(CATEGORY_GUIDE=CATEGORY_GUIDE, MAX_PAST_DAYS=MAX_PAST_DAYS)

USER_TEMPLATE = """\
아래는 총 {n_records}개의 Record 분석 결과입니다.
이를 기반으로 LNG 시장 Event 들을 추출하여 MIEventList 로 반환하세요.

## 현재 시점 (reference_time)
- reference_time: {reference_time}
- 이는 입력 Record 들의 `first_created`(뉴스 보도 시점) 중 가장 최근 값이며, "지금"으로 간주합니다.
- 이 시점 기준 너무 과거의 일들을 중심으로 하는 Event 는 만들지 마세요.

## Record 분석 결과 (JSON)
- 각 Record 에는 `first_created`(뉴스 보도 시점) 가 포함되어 있습니다.
- reference_time 에 가까운 Record 들을 우선적으로 참조해 Event 를 구성하세요.

{records_json}
"""


class EventExtractionService:
    def _compact_records(self, records: list[dict]) -> str:
        compact = []
        for record in records:
            compact.append(
                {
                    "mi_record_id": record.get("mi_record_id"),
                    "first_created": record.get("first_created", ""),
                    "record_type": record.get("record_type"),
                    "title": record.get("title", ""),
                    "record_analysis": record.get("record_analysis", {}),
                }
            )
        return json.dumps(compact, ensure_ascii=False, indent=2)

    @log_tool
    async def extract(self, records: list[dict]) -> MIEventList:
        records_json = self._compact_records(records)
        reference_time = _compute_reference_time(records)
        
        logger.info(f"[SERVICE][EventExtractionService.extract] START | records={len(records)} reference_time={reference_time}")
        
        prompt = USER_TEMPLATE.format(
            n_records=len(records),
            reference_time=reference_time,
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
        
        result = llm_result.result
        
        # reference_time 기준 최신성 필터 (너무 과거의 Event 제거)
        result = _filter_outdated_events(result, reference_time, MAX_PAST_DAYS)

        logger.info(f"[SERVICE][EventExtractionService.extract] COMPLETE | events={len(result.events)}")
        
        return result
