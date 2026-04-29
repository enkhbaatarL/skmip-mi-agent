"""
MI Record Analysis Pipeline
────────────────────────────
LangChain + Claude 기반으로 LNG 시장 **리포트**(JSON)에서 record_analysis 태그를
섹션 단위로 일괄 추출합니다.
스키마: mi_record.schema.yaml > MIRecord > record_analysis

입력:
    리포트_샘플_1.json ~ 리포트_샘플_3.json  (LNG 시장 일일 리포트 N건, JSON 구조)
    - 각 리포트는 news_headlines / market_commentaries / price_assessments /
      detailed_news 등 여러 섹션으로 구성되며, 각 섹션을 1개의 Record 로 분할하여
      기존 뉴스 단위 파이프라인과 동일한 형태(Record 리스트)로 LLM 분석에 투입합니다.
    - 여러 리포트를 한 번에 처리할 때는 리포트 간 순서를 유지하며 모든 섹션을
      이어 붙여 Record 리스트를 구성하고, mi_record_id 는 전역 순차로 재부여합니다.

Usage:
    ANTHROPIC_API_KEY=sk-ant-xxx python mi_record_analysis.py

Output:
    mi_record_analysis_results.json  ← IDE에서 바로 열기 가능
"""

import asyncio
import json
import os
import random
import re
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Set, Tuple

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field, model_validator


# ══════════════════════════════════════════════════════════════
# 1. Pydantic Models  (스키마 mi_record.schema.yaml 정합)
# ══════════════════════════════════════════════════════════════

class EntityType(str, Enum):
    country      = "country"
    company      = "company"
    facility     = "facility"
    organization = "organization"
    other        = "other"

class Entity(BaseModel):
    name:        str        = Field(description="엔티티 정규 명칭 (한국어 또는 영어)")
    entity_type: EntityType = Field(description="엔티티 유형")

class OccurrencePrecision(str, Enum):
    exact   = "exact"
    day     = "day"
    month   = "month"
    quarter = "quarter"
    year    = "year"
    unknown = "unknown"

class EventTiming(BaseModel):
    occurrence_time: str = Field(
        default="",
        description="이벤트 실제 발생 시점. ISO-8601 또는 빈 문자열. 예: '2026-03-03T00:00:00Z'",
    )
    occurrence_time_precision: OccurrencePrecision = Field(
        default=OccurrencePrecision.unknown,
        description="occurrence_time 정밀도",
    )

class ImpactIndex(str, Enum):
    JKM  = "JKM"
    HH   = "HH"
    TTF  = "TTF"
    NBP  = "NBP"
    NONE = "None"

class ImpactDirection(str, Enum):
    bullish = "bullish"
    bearish = "bearish"
    neutral = "neutral"
    unclear = "unclear"

class SupplyDemandSide(str, Enum):
    supply  = "supply"
    demand  = "demand"
    both    = "both"
    none    = "none"
    unclear = "unclear"

def _load_category_pairs_and_guide() -> Tuple[Set[Tuple[str, str]], str]:
    base_dir = Path(__file__).parent
    candidates = [
        base_dir / "event_type_taxnomy.json",   # 요청된 파일명(오타 포함) 우선 시도
        base_dir / "event_type_taxonomy.json",  # 실제 파일명
    ]
    taxonomy_path = next((p for p in candidates if p.exists()), None)
    if taxonomy_path is None:
        raise FileNotFoundError("event_type_taxnomy.json 또는 event_type_taxonomy.json 파일을 찾을 수 없습니다.")

    with open(taxonomy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    pairs: Set[Tuple[str, str]] = set()
    guide_lines: List[str] = []
    for node in data.get("taxonomy", []):
        level_1 = node.get("level_1_code", "")
        children = node.get("children", [])
        level_2_codes: List[str] = []
        for child in children:
            level_2 = child.get("level_2_code", "")
            if level_1 and level_2:
                pairs.add((level_1, level_2))
                level_2_codes.append(level_2)
        if level_1 and level_2_codes:
            guide_lines.append(f"- {level_1}: {', '.join(level_2_codes)}")

    return pairs, "\n".join(guide_lines)

ALLOWED_CATEGORY_PAIRS, CATEGORY_GUIDE = _load_category_pairs_and_guide()

class CategoryAnalysis(BaseModel):
    level_1: str = Field(description="event_type_taxnomy(event_type_taxonomy) 기준 level_1_code")
    level_2: str = Field(description="event_type_taxnomy(event_type_taxonomy) 기준 level_2_code")
    entities: List[Entity] = Field(default_factory=list)
    event_timing: EventTiming = Field(default_factory=EventTiming)
    regions: List[str] = Field(default_factory=list)
    supply_demand_side: SupplyDemandSide = Field(default=SupplyDemandSide.unclear)
    score: float = Field(ge=0, le=10, description="해당 record가 이 카테고리에 부합하는 정도 (0~10)")
    reason: str = Field(default="", description="score 근거")

    @model_validator(mode="after")
    def validate_category_pair(self):
        if (self.level_1, self.level_2) not in ALLOWED_CATEGORY_PAIRS:
            raise ValueError(
                f"유효하지 않은 category 조합: ({self.level_1}, {self.level_2}). "
                "event_type_taxnomy/event_type_taxonomy의 level_1_code+level_2_code 조합만 허용됩니다."
            )
        return self

class RecordAnalysis(BaseModel):
    """MI Record LNG 가격 분석 태그 세트"""
    categories:    List[CategoryAnalysis] = Field(
        default_factory=list,
        description="반드시 1개 이상의 category를 포함해야 함",
    )
    analysis_time: str = Field(default="")

    @model_validator(mode="after")
    def validate_categories(self):
        # 중복 조합은 에러 대신 점수가 높은 항목만 남겨 자동 정리
        dedup = {}
        for c in self.categories:
            key = (c.level_1, c.level_2)
            if key not in dedup or c.score > dedup[key].score:
                dedup[key] = c
        self.categories = list(dedup.values())
        return self


# ══════════════════════════════════════════════════════════════
# 2. Prompt
# ══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """\
당신은 LNG(액화천연가스) 시장 분석 전문가입니다.
주어진 **LNG 시장 리포트의 한 섹션**을 분석하여, LNG 가격(JKM, HH, TTF, NBP) 예측에
활용할 구조화된 분석 태그를 추출합니다.

## 입력 특성 (중요)
- 하나의 Record 는 일일 LNG 시장 리포트에서 분할된 **특정 섹션**입니다.
  (예: 뉴스 헤드라인, 시장 코멘터리(JKM/TTF/대서양/차익거래·운임),
   가격 평가(벤치마크·스프레드), 상세 뉴스(국가/테마별 이슈) 등)
- 섹션 본문(smry)에는 JSON-like 구조로 다음이 혼재될 수 있습니다:
  (1) 사실 기반 정보 — 가격 수치, 거래, 재고/입찰/가동 상태, 법·제도 변화 등
  (2) 시장 해석·기관 전망 — Bullish/Bearish 진단, 타깃 가격, 리서치/트레이더 코멘터리
- 하나의 섹션은 **여러 카테고리를 동시에 내포**할 수 있습니다.
  (예: 인도 수요 섹션 → supply_demand_balance + macroeconomy_policy 동시 해당)

## 분석 지침

### categories (리스트)
- 하나의 record(=리포트 한 섹션)에 대해 복수 category를 추출할 수 있습니다.
- categories는 반드시 1개 이상이어야 하며, 빈 리스트([])는 절대 허용되지 않습니다.
- 동일 level_1+level_2 조합 중복은 금지합니다.
- 각 category 원소마다 아래 필드를 채우세요:
  - level_1, level_2 (반드시 아래 taxonomy 조합 중 하나)
  - entities (리스트)
  - event_timing (단일)
  - regions (리스트)
  - supply_demand_side (단일: supply / demand / both / none / unclear)
  - score (0~10) — 해당 섹션이 이 카테고리와 얼마나 강하게 관련되는지
  - reason (score 근거) — 섹션 본문의 수치·사실·기관 전망을 가능한 한 구체적으로 인용

### category taxonomy (level_1 -> allowed level_2)
{CATEGORY_GUIDE}

### entities
- category별로 이벤트를 일으키거나 직접 영향을 받는 주체만 포함합니다.
- entity_type: country(국가) / company(기업) / facility(설비·터미널) / organization(기관·단체) / other
- 리포트 섹션에 등장하는 **트레이딩 카운터파티(Engie, BP, PetroChina 등)**,
  국영·민간 바이어(IOCL, BPCL, GAIL, Enarsa 등), 터미널·가스전·원전(Ras Laffan,
  Golden Pass LNG, 가시와자키-가리와 등) 등이 해당되면 빠짐없이 수집합니다.

### event_timing
- category별 이벤트 실제 발생 시점. ISO-8601("2026-03-03T00:00:00Z") 또는 빈 문자열("").
- 섹션에 특정 일자(예: "4월 16일", "5월 21~23일")나 리포트 발행일(report_date)이
  명시되어 있으면 이를 근거로 정밀도를 함께 채우세요.
- occurrence_time_precision: exact / day / month / quarter / year / unknown

### regions
- category별 이벤트와 직접 관련된 지역. 예: "중동", "동북아", "유럽", "북미", "호주",
  "남아시아", "중남미" 등.

### 기관·시장 전망 (reason 작성 시 유의)
- 섹션에 Bullish / Bearish / Weakness 등 **시장 톤 진단**이 명시되거나,
  타깃 가격(예: China target $8–8.50/MMBtu), 벤치마크 스프레드, 기관(은행·리서치·
  트레이더) 전망이 포함된 경우, 해당 근거를 `reason` 에 명시하여 이벤트 추출 단계
  (mi_event_extraction) 가 `market_and_institution_view` 를 채울 수 있도록 하세요.
"""

USER_PROMPT = """\
다음은 LNG 시장 일일 리포트에서 추출된 **1개 섹션**입니다.
이 섹션을 분석하여 RecordAnalysis 태그를 추출하세요.

## 섹션 제목
{title}

## 섹션 본문(리포트 원문 요약/구조)
{smry}
"""

PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT.format(CATEGORY_GUIDE=CATEGORY_GUIDE)),
    ("human",  USER_PROMPT),
])

HARD_OUTPUT_CONSTRAINTS = """\

[중요한 출력 제약]
- categories 리스트는 반드시 1개 이상 채우세요.
- 빈 리스트([])를 절대 반환하지 마세요.
- taxonomy에 있는 level_1/level_2 조합만 사용하세요.
- 가장 관련도 높은 카테고리 1개라도 반드시 포함하세요.
"""


# ══════════════════════════════════════════════════════════════
# 3. Input Loader  (리포트_샘플_*.json)
#     LNG 시장 일일 리포트 N건(JSON) 을 로드하여, 섹션별 Record 리스트로 분할한다.
#     각 Record 는 DB 테이블 `tmd_mi_record` 의 컬럼 네이밍을 그대로 따른다:
#       - mi_record_id    : int unsigned       (섹션별 synthetic id; 전역 순차)
#       - first_created   : datetime           (리포트 발행일(report_date) 기준)
#       - record_type     : varchar(20)        (REPORT)
#       - origin_source_id: int unsigned       (입력 리포트 파일명 기반 원문 소스 id)
#       - gds_no          : int                (상품 번호; 리포트에 없으므로 0)
#       - title           : 섹션 제목(한국어)   (LLM 입력용)
#       - smry            : 섹션 본문(JSON-like 원문 직렬화)
#
#     NOTE: 입력 리포트 JSON 은 중첩 dict 구조이며, 본 로더는 뉴스 단위 파이프라인과
#     호환되도록 상위/중간 키를 기준으로 **리포트를 여러 Record 로 평탄화**한다.
#     여러 리포트를 한 번에 처리하는 경우, 리포트 간 Record 는 단순 concat 되고
#     mi_record_id 는 main() 에서 전역 순차로 재부여되며, origin_source_id 는
#     입력 리포트 파일명(예: 리포트_샘플_1.json → 1)에서 파싱한 값이 유지된다.
# ══════════════════════════════════════════════════════════════

INPUT_JSON_FILENAMES: Tuple[str, ...] = (
    "리포트_샘플_Final1.json",
)

# 복수 입력 파일을 결과 메타에 표기할 때 사용하는 단일 문자열 표현.
INPUT_JSON_FILENAME = ", ".join(INPUT_JSON_FILENAMES)


# 섹션 경로 → 한국어 표시 제목. 샘플 리포트에 등장하는 키들을 우선 매핑하고,
# 알 수 없는 키는 자동 포맷으로 fallback 한다.
_SECTION_LABELS_KO: dict = {
    "news_headlines":                         "뉴스 헤드라인 요약",
    "market_commentaries.asia_jkm":           "시장 코멘터리 — 아시아 JKM",
    "market_commentaries.india_demand":       "시장 코멘터리 — 인도 수요",
    "market_commentaries.atlantic_market":    "시장 코멘터리 — 대서양 시장",
    "market_commentaries.arbitrage_and_freight": "시장 코멘터리 — 차익거래 및 해상운임",
    "price_assessments":                      "가격 평가 — 벤치마크 및 스프레드",
    "detailed_news.argentina_enarsa":         "상세 뉴스 — 아르헨티나 ENARSA 입찰",
    "detailed_news.china_import_stats":       "상세 뉴스 — 중국 수입 통계",
    "detailed_news.taiwan_import_stats":      "상세 뉴스 — 대만 수입 통계",
    "detailed_news.uk_summer_outlook":        "상세 뉴스 — 영국 여름 전망",
    "detailed_news.japan_nuclear_impact":     "상세 뉴스 — 일본 원전 영향",
    "detailed_news.sustainability":           "상세 뉴스 — 지속가능성(Sustainability)",
    "detailed_news.us_weekly_trends":         "상세 뉴스 — 미국 주간 동향",
    "detailed_news.italy_russian_lng":        "상세 뉴스 — 이탈리아·러시아 LNG",
    "detailed_news.eu_russian_lng_phaseout":  "상세 뉴스 — EU 러시아 LNG 단계적 금지",
}

# 신규 포맷(리포트_샘플_Final1.json) 의 최상위 키를 한국어 제목으로 매핑.
# sub-key 가 한국어인 경우 `<top_label> — <sub_key>` 형태의 fallback 제목을 자동 생성.
_TOP_LEVEL_LABELS_KO: dict = {
    "overall_storyline":               "전체 스토리라인",
    "market_commentaries":             "시장 코멘터리",
    "assessment_rationale":            "가격 평가 근거",
    "news_summary":                    "뉴스 요약",
    "regional_supply_demand_snapshot": "지역별 수급 스냅샷",
}


def _section_title_ko(section_path: str) -> str:
    """섹션 경로(dot-joined key)에 대응되는 한국어 제목을 반환. 미매핑 시 자동 포맷."""
    if section_path in _SECTION_LABELS_KO:
        return _SECTION_LABELS_KO[section_path]
    parts = section_path.split(".", 1)
    top_label = _TOP_LEVEL_LABELS_KO.get(parts[0])
    if top_label is None:
        pretty = " / ".join(p.replace("_", " ") for p in section_path.split("."))
        return f"[리포트 섹션] {pretty}"
    if len(parts) == 1:
        return top_label
    return f"{top_label} — {parts[1]}"


def _report_first_created(report_date: str) -> str:
    """리포트의 first_created(=보도 시점) 를 `YYYY-MM-DD HH:MM:SS` 형태로 생성.

    Query 원본과의 파싱 호환을 위해 naive datetime 문자열 포맷을 사용한다.
    """
    if report_date and isinstance(report_date, str):
        return f"{report_date.strip()} 00:00:00"
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# market_commentaries / detailed_news 처럼 내부를 **sub-key 단위로 더 쪼갤** 상위 키 목록.
# 여기에 해당하는 상위 키는 각 sub-key 마다 별도의 Record 로 분할한다.
_SPLIT_BY_SUBKEY: Tuple[str, ...] = (
    "market_commentaries",
    "detailed_news",
    "assessment_rationale",
    "news_summary",
    "regional_supply_demand_snapshot",
)


def _parse_origin_source_id_from_filename(json_path: Path) -> int:
    """파일명(예: 리포트_샘플_1.json) 끝의 정수를 origin_source_id 로 파싱."""
    m = re.search(r"(\d+)(?=\.[^.]+$)", json_path.name)
    if not m:
        raise ValueError(f"파일명에서 origin_source_id 를 찾을 수 없습니다: {json_path.name}")
    return int(m.group(1))


def load_records_from_report_json(json_path: Path) -> List[dict]:
    """리포트 JSON 1건을 로드하여 섹션 단위 Record 리스트로 변환.

    분할 규칙:
      - 최상위 dict 의 각 key 에 대해,
        * key 가 `_SPLIT_BY_SUBKEY` 에 포함된 경우: 하위 dict 의 각 sub-key 별로
          별도 Record 를 생성.
        * 그 외의 경우: 해당 key 의 value 를 하나의 Record 로 묶어 생성.
      - `report_date` 같은 메타 필드는 Record 로 만들지 않고 first_created 로만 활용.

    반환 Record 포맷은 뉴스 파이프라인과 동일한 dict 형태:
      mi_record_id / first_created / record_type / origin_source_id / gds_no / title / smry
    """
    with open(json_path, "r", encoding="utf-8") as f:
        report = json.load(f)

    if not isinstance(report, dict):
        raise ValueError(f"{json_path.name} 최상위는 dict 이어야 합니다. (실제: {type(report).__name__})")

    report_date  = str(report.get("report_date", "")).strip()
    first_created = _report_first_created(report_date)
    origin_source_id = _parse_origin_source_id_from_filename(json_path)

    META_KEYS = {"report_date"}  # Record 로 전환하지 않는 메타 필드

    records: List[dict] = []

    def _push(section_path: str, content) -> None:
        idx = len(records) + 1
        title = _section_title_ko(section_path)
        if isinstance(content, (dict, list)):
            smry_body = json.dumps(content, ensure_ascii=False, indent=2)
        else:
            smry_body = str(content)
        smry = (
            f"[리포트 섹션: {section_path}]\n"
            f"[리포트 발행일: {report_date or 'unknown'}]\n\n"
            f"{smry_body}"
        )
        records.append({
            "mi_record_id":  idx,
            "first_created": first_created,
            "record_type":   "REPORT",
            "origin_source_id": origin_source_id,
            "gds_no":        0,
            "title":         title,
            "smry":          smry,
        })

    for top_key, top_val in report.items():
        if top_key in META_KEYS:
            continue
        if top_key in _SPLIT_BY_SUBKEY and isinstance(top_val, dict) and top_val:
            for sub_key, sub_val in top_val.items():
                _push(f"{top_key}.{sub_key}", sub_val)
        else:
            _push(top_key, top_val)

    if not records:
        raise ValueError(f"{json_path.name} 에서 분할 가능한 섹션을 찾을 수 없습니다.")

    return records


# 기존 호출부(뉴스 단위) 호환을 위한 별칭.
load_articles_from_query_json = load_records_from_report_json


# ══════════════════════════════════════════════════════════════
# 4. Chain  &  Async Batch Runner
# ══════════════════════════════════════════════════════════════

def build_chain():
    # 기본 모델을 상향(최신 고성능 계열)하고, 필요 시 환경변수로 오버라이드 가능
    model_name = os.getenv("MI_ANALYSIS_MODEL", "claude-opus-4-1-20250805")
    max_tokens = int(os.getenv("MI_ANALYSIS_MAX_TOKENS", "8192"))
    llm = ChatAnthropic(model=model_name, temperature=0, max_tokens=max_tokens)
    return PROMPT | llm.with_structured_output(RecordAnalysis)

def _is_retryable_api_error(exc: Exception) -> bool:
    """Anthropic 과부하/레이트리밋 계열(429/529)만 재시도."""
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 529}:
        return True

    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    retry_keywords = ("overloaded", "rate limit", "too many requests")
    return any(k in name or k in msg for k in retry_keywords)

def _is_retryable_schema_error(exc: Exception) -> bool:
    """Structured output/Pydantic 검증 실패 계열은 재시도로 보정."""
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    schema_keywords = (
        "validationerror",
        "structured",
        "categories",
        "min_length",
        "json",
        "output parsing",
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

def _shorten_text_for_retry(text: str, attempt: int) -> str:
    """max_tokens 실패 시 재시도할수록 본문을 점진적으로 축약."""
    if attempt <= 1:
        return text

    ratio_by_attempt = {2: 0.8, 3: 0.65, 4: 0.5}
    ratio = ratio_by_attempt.get(attempt, 0.4)
    keep_chars = max(1200, int(len(text) * ratio))
    shortened = text[:keep_chars].rstrip()
    if len(shortened) < len(text):
        shortened += "\n\n[알림] 출력 안정성을 위해 본문을 핵심 위주로 축약했습니다."
    return shortened

def _build_smry_for_attempt(smry: str, attempt: int, last_exc: Exception | None) -> str:
    """재시도 시 출력 제약을 점진 강화."""
    smry_for_attempt = smry
    if last_exc is not None and _is_max_tokens_incomplete_error(last_exc):
        smry_for_attempt = _shorten_text_for_retry(smry_for_attempt, attempt)

    hint = HARD_OUTPUT_CONSTRAINTS
    if last_exc is not None and attempt >= 3:
        hint += f"\n[직전 실패 원인]\n- {str(last_exc)[:240]}\n"
    return f"{smry_for_attempt}\n\n{hint}"

def _guess_fallback_category_pair(article: dict) -> Tuple[str, str]:
    """기사 텍스트와 taxonomy 코드 토큰 겹침으로 최선의 fallback 카테고리 선택."""
    text = f"{article.get('title', '')} {article.get('smry', '')}".lower()
    words = set(re.findall(r"[a-z0-9_]{3,}", text))
    sorted_pairs = sorted(ALLOWED_CATEGORY_PAIRS)
    if not sorted_pairs:
        raise RuntimeError("허용 category taxonomy가 비어 있습니다.")

    best_pair = sorted_pairs[0]
    best_score = -1
    for pair in sorted_pairs:
        tokens = set(re.findall(r"[a-z0-9]{3,}", f"{pair[0]} {pair[1]}".lower()))
        overlap = len(tokens & words)
        if overlap > best_score:
            best_pair = pair
            best_score = overlap
    return best_pair

def _build_fallback_result(article: dict, last_exc: Exception | None) -> RecordAnalysis:
    """LLM 호출이 끝내 실패해도 categories 비어있지 않은 안전 결과를 생성."""
    level_1, level_2 = _guess_fallback_category_pair(article)
    reason = "LLM 분석 실패로 taxonomy 기반 fallback category를 할당했습니다."
    if last_exc is not None:
        reason += f" (error: {str(last_exc)[:160]})"

    return RecordAnalysis(
        categories=[
            CategoryAnalysis(
                level_1=level_1,
                level_2=level_2,
                entities=[],
                event_timing=EventTiming(),
                regions=[],
                supply_demand_side=SupplyDemandSide.unclear,
                score=0.1,
                reason=reason,
            )
        ]
    )

async def analyze_one(chain, article: dict, idx: int, total: int) -> dict:
    mi_id = _mi_record_id_from_article(article, idx - 1)
    title = article.get("title", "")
    print(f"  [{idx:02d}/{total}] 분석 중 (mi_record_id={mi_id}): {str(title)[:50]}...")
    max_retries = 9
    last_exc: Exception | None = None
    result: RecordAnalysis | None = None

    for attempt in range(1, max_retries + 1):
        try:
            smry = _build_smry_for_attempt(article.get("smry", ""), attempt, last_exc)
            result: RecordAnalysis = await chain.ainvoke({
                "title": title,
                "smry":  smry,
            })
            if not result.categories:
                raise ValueError("LLM 출력에서 categories가 비어 있음")
            break
        except Exception as exc:
            last_exc = exc
            is_api_error = _is_retryable_api_error(exc)
            is_schema_error = _is_retryable_schema_error(exc)
            is_max_tokens_error = _is_max_tokens_incomplete_error(exc)
            should_retry = (is_api_error or is_schema_error) and attempt < max_retries

            if not should_retry:
                break

            # Exponential backoff + jitter로 동시 재시도 충돌 완화
            wait_sec = min(20.0, 1.5 ** (attempt - 1)) + random.uniform(0, 0.7)
            if is_api_error:
                reason = "API 과부하/레이트리밋"
            elif is_max_tokens_error:
                reason = "max_tokens 출력 잘림"
            else:
                reason = "출력 파싱/스키마 불일치"
            print(
                f"    ↳ 재시도 사유: {reason} ({attempt}/{max_retries}). "
                f"{wait_sec:.1f}s 후 재시도..."
            )
            await asyncio.sleep(wait_sec)

    if result is None:
        print(
            "    ↳ 경고: 재시도 소진. fallback category로 결과를 생성합니다."
        )
        result = _build_fallback_result(article, last_exc)

    result.analysis_time = datetime.now(timezone.utc).isoformat()
    # Enum 등을 순수 scalar 로 변환해 JSON 직렬화 호환성 유지
    return result.model_dump(mode="json")

async def run_batch(articles: list) -> list:
    """전체 기사 병렬 분석 (Semaphore로 동시 호출 최대 3개 제한)"""
    chain = build_chain()
    sem   = asyncio.Semaphore(3)

    async def safe_analyze(article, idx):
        async with sem:
            return await analyze_one(chain, article, idx, len(articles))

    tasks = [safe_analyze(a, i + 1) for i, a in enumerate(articles)]
    return await asyncio.gather(*tasks)


# ══════════════════════════════════════════════════════════════
# 5. JSON 결과 저장
# ══════════════════════════════════════════════════════════════

def _mi_record_id_from_article(article: dict, index: int) -> int:
    """Article dict → tmd_mi_record.mi_record_id 정수."""
    raw = article.get("mi_record_id")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.isdigit():
        return int(raw)
    # 하위호환: 과거 "record_01" 형태의 id 도 허용
    m = re.match(r"(?i)record_0*(\d+)", str(article.get("id", "")))
    if m:
        return int(m.group(1))
    return index + 1


def build_result_doc(articles: list, analyses: list) -> dict:
    """record_analysis 중간 결과 문서를 조립 (JSON 직렬화 대상).

    records[] 구성:
      1) tmd_mi_record 관련 컬럼 (mi_record_id / first_created / record_type /
         origin_source_id / gds_no) — Query_샘플_260417.json 값 보존
      2) title / smry — tmd_mi_record 에는 없지만 본 파이프라인이 실제로 활용하는
         핵심 입력 데이터이므로 1급 필드로 함께 출력한다.
         (운영 환경에서는 origin_source_id 가 가리키는 별도 소스 객체 테이블에서 조회됨)
      3) analysis_time, categories — LLM 분석 결과. 다음 단계(mi_event_extraction.py)
         입력으로 사용되는 본 파이프라인 산출물.
    """
    records = []
    for i, (art, ana) in enumerate(zip(articles, analyses)):
        mi_id = _mi_record_id_from_article(art, i)
        records.append({
            # ── tmd_mi_record 관련 컬럼 ──────────────────────────
            "mi_record_id":      mi_id,
            "first_created":     art.get("first_created", ""),
            "record_type":       art.get("record_type", "REPORT"),
            "origin_source_id":  art.get("origin_source_id", mi_id),
            "gds_no":            art.get("gds_no", ""),
            # ── 원문 소스 객체 데이터 (스키마 외, LLM 분석 입력으로 활용) ──
            "title":             art.get("title", ""),
            "smry":              art.get("smry", ""),
            # ── LLM 분석 결과 (다음 단계 입력) ──────────────────
            "analysis_time":     ana.get("analysis_time", ""),
            "categories":        ana.get("categories", []),
        })

    summary = []
    for i, (art, ana) in enumerate(zip(articles, analyses)):
        cat_items = ana.get("categories", [])
        summary.append({
            "mi_record_id": _mi_record_id_from_article(art, i),
            "record_type":  art.get("record_type", ""),
            "title":        art.get("title", ""),
            "categories": [
                {
                    "level_1": c["level_1"],
                    "level_2": c["level_2"],
                    "score": c["score"],
                }
                for c in cat_items
            ],
        })

    return {
        "_meta": {
            "description":  "MI Record 배치 분석 결과 — LNG 시장 리포트 섹션 단위 태그",
            "input_table":  "tmd_mi_record",
            "input_file":   INPUT_JSON_FILENAME,
            "input_files":  list(INPUT_JSON_FILENAMES),
            "schema_note":  "records[].mi_record_id..origin_source_id 컬럼은 tmd_mi_record 스키마 정합. "
                            "title/smry 는 스키마 외 원문(리포트 섹션) 데이터 (LLM 입력으로 활용). "
                            "analysis_time/categories 는 본 파이프라인 중간 산출물(DB 미저장). "
                            "여러 건의 리포트(JSON)를 한 번에 처리할 경우, Record 들은 리포트별 섹션 "
                            "단위로 분할된 뒤 리포트 순서를 유지하며 이어붙고 mi_record_id 는 전역 순차로 재부여됨.",
            "generated":    datetime.now(timezone.utc).isoformat(),
            "total":        len(records),
        },
        "summary": summary,
        "records": records,
    }


def save_json(doc: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"\n  => 저장 완료: {path.resolve()}")


# ══════════════════════════════════════════════════════════════
# 6. 터미널 요약 출력
# ══════════════════════════════════════════════════════════════

def print_summary(articles: list, analyses: list) -> None:
    W = 120
    print("\n" + "═" * W)
    print(f"  {'#':<4} {'mi_record_id':<14} {'record_type':<10} {'카테고리(상위/하위)':<72} {'개수':<6}")
    print("─" * W)
    for i, (art, ana) in enumerate(zip(articles, analyses), 1):
        categories = ana.get("categories", [])
        cat_text = ", ".join(f"{c['level_1']}/{c['level_2']}({c['score']})" for c in categories) or "-"
        mi_id = _mi_record_id_from_article(art, i - 1)
        rtype = str(art.get("record_type", ""))
        print(
            f"  {i:<4} {mi_id:<14} {rtype:<10} {cat_text:<72} {len(categories):<6}"
        )
    print("═" * W)


# ══════════════════════════════════════════════════════════════
# 7. Main
# ══════════════════════════════════════════════════════════════

async def main():
    base_dir    = Path(__file__).parent
    input_paths = [base_dir / name for name in INPUT_JSON_FILENAMES]
    output_path = base_dir / "mi_record_analysis_results.json"

    missing = [p for p in input_paths if not p.exists()]
    if missing:
        missing_names = ", ".join(p.name for p in missing)
        raise FileNotFoundError(f"입력 리포트 JSON 을 찾을 수 없습니다: {missing_names}")

    articles: List[dict] = []
    per_file_counts: List[Tuple[str, int]] = []
    for input_path in input_paths:
        loaded = load_records_from_report_json(input_path)
        per_file_counts.append((input_path.name, len(loaded)))
        articles.extend(loaded)

    # 복수 파일 합산 시 mi_record_id 는 전역 순차로 재부여.
    # origin_source_id 는 입력 리포트 파일명(예: 리포트_샘플_1.json → 1) 기준으로 보존.
    for new_id, art in enumerate(articles, start=1):
        art["mi_record_id"]  = new_id

    print("═" * 65)
    print("  MI Record Batch Analysis  —  LNG Report Section Tag Extraction")
    print(f"  inputs: {len(input_paths)}개 리포트")
    for name, cnt in per_file_counts:
        print(f"    - {name}  (sections={cnt})")
    print(f"  total sections: {len(articles)}")
    print(f"  output: {output_path.name}")
    print("═" * 65)

    t0       = time.time()
    analyses = await run_batch(articles)
    elapsed  = time.time() - t0

    print(f"\n✅ 분석 완료  ({elapsed:.1f}s / {len(articles)}건)")

    print_summary(articles, analyses)

    doc = build_result_doc(articles, analyses)
    save_json(doc, output_path)
    print(f"  IDE에서 {output_path.name} 파일을 여세요.\n")


if __name__ == "__main__":
    asyncio.run(main())
