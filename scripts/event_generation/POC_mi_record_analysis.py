"""
MI Record Analysis Pipeline
────────────────────────────
LangChain + Claude 기반으로 LNG 뉴스 기사에서 record_analysis 태그를 일괄 추출합니다.
스키마: mi_record.schema.yaml > MIRecord > record_analysis

입력:
    Query_샘플_260417.json  (DB 쿼리 결과 샘플 — tmd_mi_record JOIN 결과)

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
주어진 뉴스 기사를 분석하여 LNG 가격(JKM, HH, TTF, NBP) 예측에 활용할 구조화된 분석 태그를 추출합니다.

## 분석 지침

### categories (리스트)
- 하나의 record에 대해 복수 category를 추출할 수 있습니다.
- categories는 반드시 1개 이상이어야 하며, 빈 리스트([])는 절대 허용되지 않습니다.
- 동일 level_1+level_2 조합 중복은 금지합니다.
- 각 category 원소마다 아래 필드를 채우세요:
  - level_1, level_2 (반드시 아래 taxonomy 조합 중 하나)
  - entities (리스트)
  - event_timing (단일)
  - regions (리스트)
  - supply_demand_side (단일: supply / demand / both / none / unclear)
  - score (0~10)
  - reason (score 근거)

### category taxonomy (level_1 -> allowed level_2)
{CATEGORY_GUIDE}

### entities
- category별로 이벤트를 일으키거나 직접 영향을 받는 주체만 포함합니다.
- entity_type: country(국가) / company(기업) / facility(설비·터미널) / organization(기관·단체) / other

### event_timing
- category별 이벤트 실제 발생 시점. ISO-8601("2026-03-03T00:00:00Z") 또는 빈 문자열("").
- occurrence_time_precision: exact / day / month / quarter / year / unknown

### regions
- category별 이벤트와 직접 관련된 지역. 예: "중동", "동북아", "유럽", "북미", "호주", "남아시아"
"""

USER_PROMPT = """\
다음 뉴스 기사를 분석하여 RecordAnalysis 태그를 추출하세요.

## 기사 제목
{title}

## 기사 본문(요약)
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
# 3. Input Loader  (Query_샘플_260417.json)
#     DB 테이블 `tmd_mi_record` 관련 JOIN 쿼리 결과를 로드한다.
#     JSON 최상위는 단일 SQL 쿼리 문자열을 키로 갖는 dict 이며,
#     값은 아래 필드들의 레코드 배열이다.
#       - mi_record_id    : int unsigned
#       - first_created   : datetime (Record 최초생성일시)
#       - record_type     : varchar(20)  (NEWS / REPORT / EMAIL)
#       - source_obj_id   : int unsigned (원문 소스 객체 FK)
#       - gds_no          : int (상품 번호)
#       - title           : 기사 제목
#       - smry            : 기사 본문(한국어 요약)  ← 과거 `body` 를 대체
#
#     NOTE: `title`, `smry` 는 `tmd_mi_record` 컬럼에는 존재하지 않으며,
#     실제 운영에서는 `source_obj_id` 가 가리키는 별도 소스 객체 테이블
#     (tmd_nws_smry 등) 에서 조회된다. 여기서는 LLM 분석 입력으로 활용한다.
# ══════════════════════════════════════════════════════════════

INPUT_JSON_FILENAME = "Query_샘플_260417.json"


def load_articles_from_query_json(json_path: Path) -> List[dict]:
    """Query_샘플_260417.json 을 로드하여 파이프라인 입력용 article dict 리스트로 변환.

    최상위는 `{SQL 쿼리: [record, ...]}` 구조이므로 값(리스트)을 모두 평탄화해 반환한다.
    각 record 는 DB JOIN 결과 컬럼(mi_record_id / first_created / record_type /
    source_obj_id / gds_no / title / smry) 을 그대로 보존한다.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"{json_path.name} 최상위는 dict 이어야 합니다. (실제: {type(data).__name__})")

    articles: List[dict] = []
    for _query, rows in data.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            articles.append(row)

    if not articles:
        raise ValueError(f"{json_path.name} 에서 Record를 찾을 수 없습니다.")

    return articles


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
         source_obj_id / gds_no) — Query_샘플_260417.json 값 보존
      2) title / smry — tmd_mi_record 에는 없지만 본 파이프라인이 실제로 활용하는
         핵심 입력 데이터이므로 1급 필드로 함께 출력한다.
         (운영 환경에서는 source_obj_id 가 가리키는 별도 소스 객체 테이블에서 조회됨)
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
            "record_type":       art.get("record_type", "NEWS"),
            "source_obj_id":     art.get("source_obj_id", mi_id),
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
            "description":  "MI Record 배치 분석 결과 — LNG(JKM/HH) 가격 예측용 태그",
            "input_table":  "tmd_mi_record",
            "input_file":   INPUT_JSON_FILENAME,
            "schema_note":  "records[].mi_record_id..source_obj_id 컬럼은 tmd_mi_record 스키마 정합. "
                            "title/smry 는 스키마 외 원문 소스 객체 데이터 (LLM 입력으로 활용). "
                            "analysis_time/categories 는 본 파이프라인 중간 산출물(DB 미저장).",
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
    input_path  = base_dir / INPUT_JSON_FILENAME
    output_path = base_dir / "mi_record_analysis_results.json"

    articles = load_articles_from_query_json(input_path)

    print("═" * 65)
    print("  MI Record Batch Analysis  —  LNG Price Tag Extraction")
    print(f"  input:  {input_path.name}  (records={len(articles)})")
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
