"""
MI Event Extraction Pipeline
────────────────────────────
LangChain + Claude 기반으로 Record 분석 결과(`mi_record_analysis_results.json`)를
입력받아, LNG 관련 Event들을 정의합니다.

관계 구조:
    MIRecord ──(N:M)──> MIEvent
    - 하나의 Event는 여러 Record에서 참조될 수 있음 (_extra.evidence_record_ids)
    - 하나의 Record는 여러 Event의 근거가 될 수 있음
    - Event는 단 하나의 event_type (l1_code + l2_code)만 가짐

출력 스키마: DB 테이블 `tmm_mi_mieventm` 와 정합.
    - 내부 LLM 산출물(one_line_summary / key_bullets / detail_analysis /
      market_and_institution_view / evidence_record_ids / tags / label_ko) 중
      DB 컬럼으로 1:1 매핑되지 않는 항목은 `_extra` 서브 블록으로 분리.
    - `mi_event_summary_ko` (text) 는 `detail_analysis` 본문으로 매핑.
    - 본 파이프라인 범위 밖 컬럼(estimated_impact_id, merged_into_mi_event_id,
      signal_noise_label, signal_noise_confidence)은 기본값으로 출력.

Usage:
    ANTHROPIC_API_KEY=sk-ant-xxx python mi_event_extraction.py

Output:
    mi_event_extraction_results.json  ← IDE에서 바로 열기 가능
"""

import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Set, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, conlist, model_validator


# ══════════════════════════════════════════════════════════════
# 1. Taxonomy Loader  (event_type_taxonomy.json)
# ══════════════════════════════════════════════════════════════

def _load_category_pairs_and_guide() -> Tuple[Set[Tuple[str, str]], str, dict]:
    """event_type_taxonomy.json 에서 허용 (level_1, level_2) 조합과 한국어 라벨을 로드."""
    base_dir = Path(__file__).parent
    candidates = [
        base_dir / "event_type_taxnomy.json",   # 오타 버전 우선 시도(기존 호환)
        base_dir / "event_type_taxonomy.json",
    ]
    taxonomy_path = next((p for p in candidates if p.exists()), None)
    if taxonomy_path is None:
        raise FileNotFoundError(
            "event_type_taxnomy.json 또는 event_type_taxonomy.json 파일을 찾을 수 없습니다."
        )

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pairs: Set[Tuple[str, str]] = set()
    guide_lines: List[str] = []
    label_map: dict = {}  # (l1, l2) -> "한국어 라벨"
    for node in data.get("taxonomy", []):
        level_1 = node.get("level_1_code", "")
        l1_label = node.get("label_ko", "")
        level_2_codes: List[str] = []
        for child in node.get("children", []):
            level_2 = child.get("level_2_code", "")
            l2_label = child.get("label_ko", "")
            if level_1 and level_2:
                pairs.add((level_1, level_2))
                label_map[(level_1, level_2)] = f"{l1_label} / {l2_label}"
                level_2_codes.append(level_2)
        if level_1 and level_2_codes:
            guide_lines.append(f"- {level_1} ({l1_label}): {', '.join(level_2_codes)}")

    return pairs, "\n".join(guide_lines), label_map


ALLOWED_CATEGORY_PAIRS, CATEGORY_GUIDE, CATEGORY_LABEL_MAP = _load_category_pairs_and_guide()


# ══════════════════════════════════════════════════════════════
# 2. Pydantic Models  (mi_event.schema.yaml 정합 + 일부 수정)
# ══════════════════════════════════════════════════════════════

class EventTypeRef(BaseModel):
    """Event Type 참조 (level_1 + level_2 조합만 허용)."""
    level_1: str = Field(description="event_type_taxonomy 기준 level_1_code")
    level_2: str = Field(description="event_type_taxonomy 기준 level_2_code")

    @model_validator(mode="after")
    def validate_pair(self):
        if (self.level_1, self.level_2) not in ALLOWED_CATEGORY_PAIRS:
            raise ValueError(
                f"유효하지 않은 event_type 조합: ({self.level_1}, {self.level_2}). "
                "event_type_taxonomy.json 의 level_1_code + level_2_code 조합만 허용됩니다."
            )
        return self


class MIEvent(BaseModel):
    """MI Event — Record에서 추출한 LNG 시장 이벤트 단위."""

    # --- AI가 생성할 본문 필드 ---
    event_title_ko: str = Field(
        description="이벤트를 한 줄로 요약하는 한국어 제목. 핵심 사실 + 시장 방향성을 포함."
    )
    one_line_summary: str = Field(
        description=(
            "'[토픽] 최근 에피소드 → 시장 영향/방향' 형태의 한 문장(100자 이내)."
            " 토픽은 큰 틀(예: 미국-이란 전쟁), 에피소드는 최근 새 사실, 시장 영향은 LNG 수급 또는 JKM/TTF 가격 방향성."
        )
    )
    key_bullets: conlist(str, min_length=3, max_length=5) = Field(  # type: ignore[valid-type]
        description=(
            "3~5개 핵심 포인트. 전체적으로 다음 3가지 관점을 모두 포함해야 함:\n"
            "  (A) 사건의 최근 상태·업데이트 (예: '6/23 휴전 합의')\n"
            "  (B) Fundamental 영향 — 실물 수급·설비·물동량 (예: '카타르 수출 영향 없음')\n"
            "  (C) 가격 방향 — Premium, Forward 변화, 가격 Band"
        )
    )
    detail_analysis: str = Field(
        description=(
            "key_bullets를 풀어쓴 상세 설명. 정량 수치·고유명사·가정·출처를 포함하여 작성."
            " 기사/Record에 언급되지 않은 숫자는 임의로 생성하지 말 것."
            " 반드시 개조식(명사형 종결) 문체로 작성: 모든 문장은 '...함', '...임', '...됨',"
            " '...음' 등으로 끝내야 하며, '...한다.', '...이다.', '...했다.' 와 같은"
            " 서술형(종결어미) 문장은 사용 금지."
        )
    )
    market_and_institution_view: str = Field(
        default="",
        description=(
            "기사에 스팟/선물 가격 또는 기관(은행/리서치) 전망이 언급된 경우에만 작성."
            " 언급이 없으면 빈 문자열."
        ),
    )

    # --- 이벤트 분류 ---
    event_type: EventTypeRef = Field(
        description="이벤트의 유일한 분류 (level_1 + level_2 조합)."
    )

    # --- Record 근거 (N:M) ---
    evidence_record_ids: conlist(int, min_length=1) = Field(  # type: ignore[valid-type]
        description="이 이벤트의 근거가 되는 mi_record_id 목록. 최소 1개."
    )

    # --- 실제 발생 시점 (알려진 경우) ---
    occurred_at: str = Field(
        default="",
        description="이벤트 실제 발생 시점. ISO-8601 또는 빈 문자열.",
    )

    # --- 자유 태그 ---
    tags: List[str] = Field(
        default_factory=list,
        description="추가 분류용 자유 태그 (선택).",
    )


class MIEventList(BaseModel):
    """LLM이 반환하는 최상위 컨테이너."""
    events: conlist(MIEvent, min_length=1) = Field(  # type: ignore[valid-type]
        description="Record들로부터 추출한 이벤트 목록. 최소 1개."
    )

    @model_validator(mode="after")
    def validate_unique_events(self):
        # 제목 중복만 간단히 경고성 정리 (event_type은 이벤트마다 독립적이므로 중복 허용)
        seen_titles: Set[str] = set()
        deduped: List[MIEvent] = []
        for ev in self.events:
            key = ev.event_title_ko.strip()
            if key and key in seen_titles:
                continue
            seen_titles.add(key)
            deduped.append(ev)
        self.events = deduped
        return self


# ══════════════════════════════════════════════════════════════
# 3. Prompt
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
당신은 LNG(액화천연가스) 시장 이벤트 추출 전문가입니다.
이미 AI로 1차 분석된 뉴스 기사(Record) 분석 결과들을 입력받아,
LNG 가격(JKM/TTF/HH/NBP) 예측에 유의미한 **Event** 단위로 재구성합니다.

## 용어 정의
- Record = 개별 뉴스 기사의 분석 결과 (mi_record_id로 식별).
- Event = 여러 Record에 걸쳐 동일하게 언급될 수 있는 하나의 LNG 시장 사건/토픽
         (예: "카타르 Ras Laffan 공습에 따른 가동 중단", "호르무즈 해협 폐쇄", "호주 사이클론 LNG 차질").

## 가장 중요한 원칙 (반드시 지킬 것)
1. Record ↔ Event 는 **N:M 관계**입니다.
   - 여러 Record에 공통으로 등장하는 동일 사건은 **하나의 Event로 병합**하고,
     evidence_record_ids 에 해당 Record들의 mi_record_id 를 모두 포함하세요.
   - 하나의 Record가 복수 Event의 근거가 될 수 있습니다.
2. 각 Event는 **단 하나의 event_type (level_1 + level_2 조합)** 만 가질 수 있습니다.
   - 아래 taxonomy 의 조합 중 정확히 하나를 고르세요.
3. 이벤트의 범위는 "동일한 핵심 사건"을 기준으로 정의합니다.
   - 같은 이슈라도 기사마다 각도가 다르면 evidence 로 모두 묶어 하나의 Event로.
   - 서로 다른 실물 사건(예: 카타르 공습 vs 호주 사이클론)은 별도 Event로.
4. **"현재 시점(reference_time)" 기준 최신성 원칙**
   - USER 프롬프트에 주어지는 reference_time 은 입력 Record 들의 `first_created`(뉴스 보도 시점)
     중 가장 최근 값이며, 이를 "현재"로 간주합니다.
   - reference_time 기준 **{MAX_PAST_DAYS}일 이상 과거**의 사건이 핵심인 Event 는 생성하지 마세요.
     (예: reference_time 이 2026-04-14 인데 2024년 사건을 중심으로 하는 Event 는 제외)
   - 과거 사건이 "현재 진행 중인 더 큰 사건"의 배경/전개 일부로만 언급되는 경우에는,
     그 사건의 **현재(reference_time 근처) 에피소드**를 중심 Event 로 삼고 과거는
     detail_analysis 본문에서 맥락으로만 언급하세요.
   - 각 Event 의 `occurred_at` 은 해당 이벤트의 **가장 최근(=현재 시점에 가까운) 전개 시점**을
     기준으로 기재하세요. 오래 전 촉발 시점(예: 몇 년 전 사건 발생일)을 적지 마세요.
   - 근거 Record(evidence_record_ids) 는 가능한 한 reference_time 에 가까운 `first_created` 의
     Record 를 우선 선택하세요.

## event_type taxonomy (허용된 level_1 → level_2)
{CATEGORY_GUIDE}

## 필드 작성 가이드

### event_title_ko
- 한국어 한 줄 제목. 핵심 사실 + 시장 방향성을 함께 담습니다.

### one_line_summary  (100자 이내)
- 형태: `[토픽] 최근 에피소드 → 시장 영향/방향`
- 토픽: 시간이 지나도 잘 변하지 않는 큰 틀 (예: "미국-이란 전쟁")
- 에피소드: 최근 Record들에서 새로 확인된 사실 (예: "미국 호르무즈 역봉쇄")
- 시장 영향: LNG 수급 또는 JKM/TTF 가격에 미치는 방향성 (bullish/bearish/neutral 뉘앙스)

### key_bullets  (3~5 항목)
- 각 항목은 아래 3가지 관점 중 최소 1가지를 포함해야 합니다.
- 전체 3~5개 항목 안에 (A), (B), (C) **세 관점이 모두 포함**되도록 작성하십시오.
  (A) 사건의 최근 상태·업데이트           (예: "6/23 휴전 합의")
  (B) Fundamental 영향 — 실물 수급·설비·물동량 (예: "카타르 수출 영향 없음")
  (C) 가격 방향 — Premium, Forward 변화, 가격 Band

### detail_analysis
- key_bullets 를 풀어쓴 상세 설명.
- 정량 수치·고유명사·가정·출처를 최대한 포함.
- **Record 에 언급되지 않은 숫자는 임의로 생성하지 말 것.**
- **문체 규칙 (반드시 준수)**: 개조식(명사형 종결)으로만 작성.
  - 모든 문장은 `...함.`, `...임.`, `...됨.`, `...음.` 과 같은 명사형 어미로 끝낼 것.
  - `...한다.`, `...이다.`, `...있다.`, `...했다.`, `...된다.`, `...이었다.` 등
    서술형(종결어미) 문장은 **절대 사용 금지**.
  - 예) (X) "카타르 수출은 영향이 없다." → (O) "카타르 수출은 영향 없음."
  - 예) (X) "JKM 가격이 상승했다." → (O) "JKM 가격 상승함."

### market_and_institution_view  (선택)
- Record에 스팟/선물 가격 또는 기관 전망(Morgan Stanley, Wood Mackenzie, ING 등)이 언급된 경우에만 작성.
- 언급이 없으면 빈 문자열("").

### evidence_record_ids
- 이 이벤트의 근거가 되는 Record의 `mi_record_id` (정수) 목록.
- 최소 1개 이상. 동일 이슈를 다룬 Record들은 모두 포함.

### occurred_at
- 이벤트 실제 발생 시점이 특정 가능한 경우 ISO-8601 문자열, 아니면 빈 문자열.
- 이벤트가 여러 시점에 걸쳐 전개된 경우, **가장 최근 전개 시점**(reference_time 에 가까운 시점)을
  기준으로 기재하세요. reference_time 기준 {MAX_PAST_DAYS}일 이상 과거가 되면 해당 Event 자체를
  만들지 마세요.

## 출력 가짓수 가이드
- 입력 Record 10건 기준, 통상 4~8개의 Event 가 추출됩니다.
- 무리하게 쪼개거나(=같은 사건 중복 생성) 과도하게 합치지(=서로 다른 사건 병합) 마세요.
"""

USER_PROMPT = """\
아래는 총 {n_records}개의 Record 분석 결과입니다.
이를 기반으로 LNG 시장 Event 들을 추출하여 MIEventList 로 반환하세요.

## 현재 시점 (reference_time)
- reference_time: {reference_time}
- 이는 입력 Record 들의 `first_created`(뉴스 보도 시점) 중 가장 최근 값이며, "지금"으로 간주합니다.
- 이 시점 기준 너무 과거의 일들을 중심으로 하는 Event 는 만들지 마세요. (시스템 프롬프트 원칙 4 참조)

## Record 분석 결과 (JSON)
- 각 Record 에는 `first_created`(뉴스 보도 시점) 가 포함되어 있습니다.
- reference_time 에 가까운 Record 들을 우선적으로 참조해 Event 를 구성하세요.

{records_json}
"""

# MAX_PAST_DAYS 값은 최신성 필터 기준과 함께 프롬프트에도 주입한다.
MAX_PAST_DAYS: int = int(os.getenv("MI_EVENT_MAX_PAST_DAYS", "90"))

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT.format(CATEGORY_GUIDE=CATEGORY_GUIDE, MAX_PAST_DAYS=MAX_PAST_DAYS)),
    ("human",  USER_PROMPT),
])

HARD_OUTPUT_CONSTRAINTS = """\

[중요한 출력 제약]
- events 리스트는 반드시 1개 이상 채우세요.
- 각 event는 정확히 하나의 event_type (level_1+level_2) 만 가지며,
  반드시 제공된 taxonomy 조합 중 하나여야 합니다.
- 각 event 의 evidence_record_ids 는 1개 이상이어야 하며, 입력된 mi_record_id 범위 안이어야 합니다.
- key_bullets 는 반드시 3~5개이며, (A)/(B)/(C) 관점이 모두 포함되어야 합니다.
- market_and_institution_view 는 Record에 근거가 없으면 빈 문자열("")로 두세요.
- detail_analysis 는 반드시 개조식(명사형 종결) 문체로 작성하세요.
  모든 문장은 '...함.', '...임.', '...됨.', '...음.' 으로 끝나야 하며,
  '...한다.', '...이다.', '...했다.', '...된다.' 등 서술형 종결어미는 금지합니다.
"""


# ══════════════════════════════════════════════════════════════
# 4. Input Loader  (mi_record_analysis_results.json)
# ══════════════════════════════════════════════════════════════

def load_records(json_path: Path) -> List[dict]:
    """mi_record_analysis_results.json 의 records 블록을 로드."""
    with open(json_path, "r", encoding="utf-8") as f:
        doc = json.load(f)

    records = doc.get("records", [])
    if not records:
        raise ValueError(f"{json_path} 에 records 블록이 비어 있습니다.")

    # 정렬(안정성)
    records.sort(key=lambda r: r.get("mi_record_id", 0))
    return records


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
    if max_past_days <= 0:
        return result
    ref = _parse_datetime_loose(reference_time)
    if ref is None:
        return result
    threshold = _as_naive(ref) - timedelta(days=max_past_days)

    kept: List[MIEvent] = []
    dropped: List[MIEvent] = []
    for ev in result.events:
        occ = _parse_datetime_loose(ev.occurred_at)
        if occ is not None and _as_naive(occ) < threshold:
            dropped.append(ev)
        else:
            kept.append(ev)

    if dropped:
        print(
            f"  ↳ 최신성 필터: reference_time={reference_time}, max_past_days={max_past_days}일 "
            f"기준으로 {len(dropped)}건의 과거 Event 제거"
        )
        for ev in dropped:
            print(f"    - drop (occurred_at={ev.occurred_at}): {ev.event_title_ko}")

    if not kept:
        # 필터로 전부 날아가면 다음 단계가 실패하므로 원본 유지.
        print("  ↳ 경고: 최신성 필터 결과 남는 Event 가 없어 필터를 건너뜁니다.")
        return result

    result.events = kept
    return result


def _compact_records_for_prompt(records: List[dict]) -> str:
    """토큰 절약을 위해 프롬프트에 들어갈 records 를 간결 포맷으로 JSON 직렬화."""
    compact = []
    for r in records:
        compact.append({
            "mi_record_id": r.get("mi_record_id"),
            # first_created: Record(뉴스) 보도 시점. "현재 시점" 기준의 근거로 사용.
            "first_created": r.get("first_created", ""),
            "analysis_time": r.get("analysis_time", ""),
            "categories": [
                {
                    "level_1": c.get("level_1"),
                    "level_2": c.get("level_2"),
                    "entities": [
                        {"name": e.get("name"), "entity_type": e.get("entity_type")}
                        for e in c.get("entities", []) or []
                    ],
                    "event_timing": c.get("event_timing", {}),
                    "regions": c.get("regions", []),
                    "supply_demand_side": c.get("supply_demand_side", "unclear"),
                    "score": c.get("score"),
                    "reason": c.get("reason", ""),
                }
                for c in r.get("categories", []) or []
            ],
        })
    return json.dumps(compact, ensure_ascii=False, indent=2)


# ══════════════════════════════════════════════════════════════
# 5. Chain & Error Handling
# ══════════════════════════════════════════════════════════════

def build_chain():
    model_name = os.getenv("MI_EVENT_MODEL", "claude-opus-4-1-20250805")
    max_tokens = int(os.getenv("MI_EVENT_MAX_TOKENS", "8192"))
    llm = ChatAnthropic(model=model_name, temperature=0, max_tokens=max_tokens)
    return PROMPT | llm.with_structured_output(MIEventList)


def _is_retryable_api_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 529}:
        return True
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    retry_keywords = ("overloaded", "rate limit", "too many requests")
    return any(k in name or k in msg for k in retry_keywords)


def _is_retryable_schema_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    schema_keywords = (
        "validationerror",
        "structured",
        "events",
        "min_length",
        "max_length",
        "json",
        "output parsing",
        "event_type",
    )
    return "validation" in name or any(k in msg for k in schema_keywords)


def _is_max_tokens_incomplete_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    keywords = (
        "max_tokens",
        "stop reason",
        "output is likely incomplete",
        "incomplete",
    )
    return all(k in msg for k in ("max_tokens", "stop reason")) or any(k in msg for k in keywords)


def _build_records_payload(records_json: str, attempt: int, last_exc: Exception | None) -> str:
    """재시도 시 출력 제약을 점진 강화."""
    hint = HARD_OUTPUT_CONSTRAINTS
    if last_exc is not None and attempt >= 3:
        hint += f"\n[직전 실패 원인]\n- {str(last_exc)[:240]}\n"
    return f"{records_json}\n\n{hint}"


def _guess_fallback_category_pair(records: List[dict]) -> Tuple[str, str]:
    """LLM 실패 시, Record 들의 점수 합산으로 대표 카테고리 선정."""
    pair_score: dict = {}
    for r in records:
        for c in r.get("categories", []) or []:
            key = (c.get("level_1", ""), c.get("level_2", ""))
            if key in ALLOWED_CATEGORY_PAIRS:
                pair_score[key] = pair_score.get(key, 0.0) + float(c.get("score", 0) or 0)
    if not pair_score:
        return next(iter(sorted(ALLOWED_CATEGORY_PAIRS)))
    return max(pair_score.items(), key=lambda kv: kv[1])[0]


def _build_fallback_result(records: List[dict], last_exc: Exception | None) -> MIEventList:
    """LLM 호출이 실패해도 최소한의 Event 1건을 안전하게 생성."""
    level_1, level_2 = _guess_fallback_category_pair(records)
    all_ids = [r["mi_record_id"] for r in records if "mi_record_id" in r]
    reason = "LLM 이벤트 추출 실패로 fallback Event 를 생성했습니다."
    if last_exc is not None:
        reason += f" (error: {str(last_exc)[:160]})"

    return MIEventList(
        events=[
            MIEvent(
                event_title_ko="[Fallback] LNG 시장 이벤트 추출 실패",
                one_line_summary="[Fallback] LLM 호출 실패 → 이벤트 재생성 필요",
                key_bullets=[
                    "(A) LLM 호출 실패로 이벤트 추출이 정상 완료되지 않음",
                    "(B) Fundamental 영향 판단 보류 — Record 원문/분석 결과 재확인 필요",
                    "(C) 가격 방향성 판단 보류",
                ],
                detail_analysis=reason,
                market_and_institution_view="",
                event_type=EventTypeRef(level_1=level_1, level_2=level_2),
                evidence_record_ids=all_ids or [0],
                occurred_at="",
                tags=["fallback"],
            )
        ]
    )


def extract_events(records: List[dict]) -> MIEventList:
    """전체를 한 번의 LLM 호출로 Event 리스트 추출 (N:M 병합 자연 처리)."""
    chain = build_chain()
    records_json = _compact_records_for_prompt(records)
    reference_time = _compute_reference_time(records)
    print(f"  ▸ reference_time(현재 시점 기준): {reference_time}  (max_past_days={MAX_PAST_DAYS})")

    max_retries = 6
    last_exc: Exception | None = None
    result: MIEventList | None = None

    for attempt in range(1, max_retries + 1):
        try:
            payload = _build_records_payload(records_json, attempt, last_exc)
            result = chain.invoke({
                "n_records": len(records),
                "reference_time": reference_time,
                "records_json": payload,
            })
            if not result.events:
                raise ValueError("LLM 출력에서 events 가 비어 있음")
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            is_api_error = _is_retryable_api_error(exc)
            is_schema_error = _is_retryable_schema_error(exc)
            is_max_tokens_error = _is_max_tokens_incomplete_error(exc)
            should_retry = (is_api_error or is_schema_error) and attempt < max_retries
            if not should_retry:
                break

            wait_sec = min(20.0, 1.5 ** (attempt - 1)) + random.uniform(0, 0.7)
            if is_api_error:
                reason = "API 과부하/레이트리밋"
            elif is_max_tokens_error:
                reason = "max_tokens 출력 잘림"
            else:
                reason = "출력 파싱/스키마 불일치"
            print(
                f"  ↳ 재시도 사유: {reason} ({attempt}/{max_retries}). "
                f"{wait_sec:.1f}s 후 재시도..."
            )
            time.sleep(wait_sec)

    if result is None:
        print("  ↳ 경고: 재시도 소진. fallback Event 로 결과를 생성합니다.")
        result = _build_fallback_result(records, last_exc)

    # 입력 Record ID 범위 밖 값 제거 (LLM hallucination 방어)
    valid_ids = {r["mi_record_id"] for r in records if "mi_record_id" in r}
    for ev in result.events:
        ev.evidence_record_ids = [i for i in ev.evidence_record_ids if i in valid_ids]  # type: ignore[assignment]
        if not ev.evidence_record_ids:
            ev.evidence_record_ids = [min(valid_ids)] if valid_ids else [0]

    # reference_time 기준 최신성 필터 (너무 과거의 Event 제거)
    result = _filter_outdated_events(result, reference_time, MAX_PAST_DAYS)

    return result


# ══════════════════════════════════════════════════════════════
# 6. Event Record 조립 (DB 친화 형태)
# ══════════════════════════════════════════════════════════════

def _new_event_id() -> str:
    """tmm_mi_mieventm.mi_event_id 패턴 ^ev_[a-f0-9]{12}$ 에 맞는 ID 생성."""
    return f"ev_{uuid.uuid4().hex[:12]}"


# tmm_mi_mieventm 스키마 중, 본 파이프라인의 LLM 로직만으로는 값을 채울 수 없어
# 기본값으로 내보내는 컬럼 목록. 실제 운영 시 후속 프로세스(영향도 산정, 중복 병합,
# Signal/Noise 분류 등)에서 갱신되어야 한다.
UNFILLED_COLUMNS_DEFAULT: dict = {
    # FK. 별도 Impact Assessment 프로세스에서 채워짐.
    "estimated_impact_id":      "",
    # Dedup(머지) 단계에서 대상 이벤트로 합쳐질 때만 세팅.
    "merged_into_mi_event_id":  "",
    # Signal/Noise 분류 모델 결과. 본 추출 파이프라인 범위 밖.
    "signal_noise_label":       "",
    "signal_noise_confidence":  0,
}


def build_event_document(
    events: MIEventList,
    records: List[dict],
) -> dict:
    """YAML 출력용 문서 구조 조립.

    `mi_events[]` 의 키는 DB 테이블 `tmm_mi_mieventm` 컬럼명과 1:1 로 정합된다.
    본 파이프라인의 로직만으로 채울 수 없는 컬럼은 `UNFILLED_COLUMNS_DEFAULT` 기본값으로 출력된다.

    또한 스키마에 없는 부가 산출물(one_line_summary, key_bullets, detail_analysis,
    market_and_institution_view, evidence_record_ids, tags, event_type_label_ko)은
    별도 `_extra` 서브 블록으로 분리하여 DB 컬럼과 혼동되지 않도록 한다.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # Record → Event 역매핑 (요약용)
    record_to_events: dict = {r["mi_record_id"]: [] for r in records if "mi_record_id" in r}

    mi_events: List[dict] = []
    for ev in events.events:
        mi_event_id = _new_event_id()
        pair = (ev.event_type.level_1, ev.event_type.level_2)
        type_label = CATEGORY_LABEL_MAP.get(pair, "")

        mi_events.append({
            # ── tmm_mi_mieventm 컬럼 (스키마 순서 유지) ─────────────────────
            "mi_event_id":               mi_event_id,
            "crt_user_id":               "system",
            "crt_dtm":                   now_iso,
            "mod_user_id":               "system",
            "mod_dtm":                   now_iso,
            "del_yn":                    "N",
            "mi_event_title_ko":         ev.event_title_ko,
            # mi_event_summary_ko (text) ← detail_analysis 본문으로 매핑
            "mi_event_summary_ko":       ev.detail_analysis,
            "estimated_impact_id":       UNFILLED_COLUMNS_DEFAULT["estimated_impact_id"],
            "occurred_at":               ev.occurred_at,
            "updated_at":                now_iso,
            "probability":               0,
            "language":                  "ko",
            "dedup_state":               "raw",
            "merged_into_mi_event_id":   UNFILLED_COLUMNS_DEFAULT["merged_into_mi_event_id"],
            "mi_event_type_l1_code":     ev.event_type.level_1,
            "mi_event_type_l2_code":     ev.event_type.level_2,
            "mi_event_status_code":      "raw",
            "signal_noise_label":        UNFILLED_COLUMNS_DEFAULT["signal_noise_label"],
            "signal_noise_confidence":   UNFILLED_COLUMNS_DEFAULT["signal_noise_confidence"],
            # ── 스키마 외 보조 정보 (DB 저장 X, 분석/디버깅용) ─────────────
            "_extra": {
                "one_line_summary":            ev.one_line_summary,
                "key_bullets":                 list(ev.key_bullets),
                "detail_analysis":             ev.detail_analysis,
                "market_and_institution_view": ev.market_and_institution_view,
                "evidence_record_ids":         list(ev.evidence_record_ids),
                "event_type_label_ko":         type_label,
                "tags":                        list(ev.tags),
            },
        })

        for rid in ev.evidence_record_ids:
            record_to_events.setdefault(rid, []).append(mi_event_id)

    # 요약: Record → Events 매핑
    record_event_summary = [
        {"mi_record_id": rid, "mi_event_ids": record_to_events.get(rid, [])}
        for rid in sorted(record_to_events.keys())
    ]

    return {
        "_meta": {
            "description":   "MI Event 추출 결과 — Record(N:M)Event 매핑",
            "output_table":  "tmm_mi_mieventm",
            "schema_note":   (
                "mi_events[] 의 key 는 tmm_mi_mieventm 컬럼명과 정합. "
                "estimated_impact_id / merged_into_mi_event_id / signal_noise_label / "
                "signal_noise_confidence 는 본 파이프라인 범위 밖이라 기본값으로 출력됨."
            ),
            "source":        "mi_record_analysis_results.json (← tmd_mi_record)",
            "generated":     now_iso,
            "total_events":  len(mi_events),
            "total_records": len(records),
        },
        "schema_ref": {
            "schema_id":          "tmm_mi_mieventm",
            "definition_version": "0.3.0",
        },
        "unfilled_columns": [
            "estimated_impact_id",
            "merged_into_mi_event_id",
            "signal_noise_label",
            "signal_noise_confidence",
        ],
        "record_event_summary": record_event_summary,
        "mi_events":             mi_events,
    }


# ══════════════════════════════════════════════════════════════
# 7. JSON 결과 저장
# ══════════════════════════════════════════════════════════════

def save_json(doc: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"\n  => 저장 완료: {path.resolve()}")


# ══════════════════════════════════════════════════════════════
# 8. 터미널 요약 출력
# ══════════════════════════════════════════════════════════════

def print_summary(doc: dict) -> None:
    W = 120
    events = doc.get("mi_events", [])
    print("\n" + "═" * W)
    print(f"  {'#':<4} {'mi_event_id':<18} {'event_type (l1_code/l2_code)':<62} {'|evidences|':<12} {'title':<20}")
    print("─" * W)
    for i, ev in enumerate(events, 1):
        type_text = f"{ev['mi_event_type_l1_code']}/{ev['mi_event_type_l2_code']}"
        title = ev["mi_event_title_ko"]
        title_short = (title[:18] + "…") if len(title) > 19 else title
        evidence_cnt = len(ev.get("_extra", {}).get("evidence_record_ids", []))
        print(
            f"  {i:<4} {ev['mi_event_id']:<18} {type_text:<62} {evidence_cnt:<12} {title_short:<20}"
        )
    print("═" * W)

    # Record → Event 커버리지
    rec_sum = doc.get("record_event_summary", [])
    uncovered = [r["mi_record_id"] for r in rec_sum if not r["mi_event_ids"]]
    print(
        f"  추출 Event 수: {len(events)}  |  입력 Record 수: {len(rec_sum)}  "
        f"|  미커버 Record: {uncovered if uncovered else '없음'}"
    )

    unfilled = doc.get("unfilled_columns", [])
    if unfilled:
        print(
            f"  [알림] tmm_mi_mieventm 중 본 파이프라인이 채울 수 없어 기본값으로 출력된 컬럼: "
            f"{', '.join(unfilled)}"
        )


# ══════════════════════════════════════════════════════════════
# 9. Main
# ══════════════════════════════════════════════════════════════

def main():
    base_dir   = Path(__file__).parent
    input_path = base_dir / "mi_record_analysis_results.json"
    output_path = base_dir / "mi_event_extraction_results.json"

    print("═" * 65)
    print("  MI Event Extraction  —  Record → Event (N:M)")
    print(f"  input:  {input_path.name}")
    print(f"  output: {output_path.name}")
    print("═" * 65)

    records = load_records(input_path)
    print(f"  ▸ 입력 Record 수: {len(records)}")

    t0 = time.time()
    events = extract_events(records)
    elapsed = time.time() - t0
    print(f"\n✅ 이벤트 추출 완료  ({elapsed:.1f}s / {len(events.events)}건)")

    doc = build_event_document(events, records)
    print_summary(doc)
    save_json(doc, output_path)
    print(f"  IDE에서 {output_path.name} 파일을 여세요.\n")


if __name__ == "__main__":
    # 기본적으로 단일 LLM 호출이므로 asyncio 불필요.
    # 필요 시 MI_EVENT_MODEL / MI_EVENT_MAX_TOKENS 환경변수로 튜닝.
    main()
