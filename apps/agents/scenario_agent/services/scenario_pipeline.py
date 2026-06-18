"""
Scenario Generation Pipeline Stages

Proper implementation of the 5-stage scenario generation pipeline
with proper LLM client injection support.
"""
import asyncio
import json
import os
import random
import time
from itertools import product
from pathlib import Path
from typing import Dict, List, Literal, Tuple

from pydantic import BaseModel, Field, conlist, model_validator

from apps.common.logging.decorators import log_tool
from apps.connectors.llm.llm_client import invoke_llm_structured_output


# ==============================================
# 1. Enums and Constants
# ==============================================

PRICE_TIERS: Tuple[str, ...] = (
    "strong_bull", "bull", "mild_bull", "neutral", "mild_bear", "bear", "strong_bear",
)
LIKELIHOOD_TIERS: Tuple[str, ...] = (
    "very_low", "low", "medium", "high", "very_high",
)

PriceTier = Literal[
    "strong_bull", "bull", "mild_bull", "neutral", "mild_bear", "bear", "strong_bear",
]
LikelihoodTier = Literal["very_low", "low", "medium", "high", "very_high"]

# --- LLM config constants (from env) ---
REF_MAX_RETRIES: int = int(os.getenv("REF_MAX_RETRIES", "5"))
REF_TARGET_SCENARIOS: int = int(os.getenv("REF_TARGET_SCENARIOS", "6"))
REF_TEMPERATURE: float = float(os.getenv("REF_TEMPERATURE", "0.0"))


# ==============================================
# 2. Pydantic Models
# ==============================================

class C1BaseEvent(BaseModel):
    event_id: str = Field(default="", description="MIEvent 고유 ID (mi_event_id)")
    title: str = Field(default="", description="이벤트 한글 제목")
    event_type_l1_l2: str = Field(default="", description="'l1_code::l2_code' 형태")
    summary: str = Field(default="", description="이벤트 한 줄 요약 (one_line_summary)")
    driver: str = Field(default="", description="핵심 드라이버 (자유 서술)")


class C2LinkedRecords(BaseModel):
    window_days: int = Field(default=30, description="연관 Record 조회 시간창 (일)")
    records: List[Dict] = Field(default_factory=list, description="연관 Record 요약 리스트(stub)")


class C3HistoricalAnalog(BaseModel):
    analog_event_id: str = Field(default="", description="과거 유사 이벤트 ID")
    trajectory: List[str] = Field(default_factory=list, description="전개 단계 라벨 시퀀스")


class Stage1ContextPack(BaseModel):
    C1_base_event: C1BaseEvent = Field(description="필수 — 단일 Base Event")
    C2_linked_records: C2LinkedRecords = Field(
        default_factory=C2LinkedRecords,
        description="형식적 stub — 실제 구현은 본 파이프라인 범위 밖.",
    )
    C3_historical_analogs: List[C3HistoricalAnalog] = Field(
        default_factory=list,
        description="형식적 stub — RAG 미연결.",
    )
    C4_related_events: List[Dict] = Field(
        default_factory=list,
        description="형식적 stub — Graph 미연결.",
    )


class SelectedDimension(BaseModel):
    dimension_id: str = Field(description="템플릿의 dimension_id")
    rationale: str = Field(
        description=(
            "선택 근거. 반드시 '(a)' 또는 '(c)' 또는 '(a)(c)' 코드로 시작하고, "
            "한국어 근거문을 1줄로 부연."
        )
    )


class ExcludedDimension(BaseModel):
    dimension_id: str = Field(description="제외된 템플릿 dimension_id")
    reason: str = Field(description="제외 사유 한국어 1줄.")


class Stage2DimensionSelection(BaseModel):
    template_id: str = Field(description="event_type_l1_l2 형태의 템플릿 키")
    template_dimensions_total: int = Field(description="템플릿 전체 Dim 수 (보통 8)")
    selected_dimensions: conlist(SelectedDimension, min_length=3, max_length=5) = Field(  # type: ignore[valid-type]
        description="선택된 Dim 3~5개. (b) 기준 사용 금지.",
    )
    excluded_dimensions: List[ExcludedDimension] = Field(
        default_factory=list,
        description="선택되지 않은 Dim + 사유.",
    )


class PerDimensionValue(BaseModel):
    dimension_id: str = Field(description="템플릿의 dimension_id")
    template_enum_full: List[str] = Field(
        default_factory=list,
        description="해당 Dim 의 원본 5단계 Enum ID 전체.",
    )
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택한 Enum ID 2~4개. 인접 병합 금지.",
    )
    tail_risk_kept: str = Field(
        default="",
        description="Tail Risk 로 보존된 Enum ID 1개 이상 (selected_enum 내 포함).",
    )


class Stage3ValueSelection(BaseModel):
    per_dimension: List[PerDimensionValue] = Field(
        default_factory=list,
        description="Dim 별 Value 축소 결과 리스트.",
    )


class PriceDirection(BaseModel):
    brent: PriceTier = Field(description="Brent 방향성 7단계")
    jkm: PriceTier = Field(description="JKM 방향성 7단계")
    ttf: PriceTier = Field(description="TTF 방향성 7단계")


class Scenario(BaseModel):
    scenario_id: str = Field(description="S_01 형태")
    title: str = Field(description="시장 참여자 관점 한 줄 요약")
    dimension_values: Dict[str, str] = Field(
        description="dim_id -> enum_id 의 1:1 매핑.",
    )
    description: str = Field(
        description="3~5줄. 주요 Dim 가정치 조합 + 전개 양상 서술.",
    )
    derivation_rationale: str = Field(
        description="이 시나리오를 도출한 근거.",
    )
    price_direction: PriceDirection = Field(description="Brent/JKM/TTF 7단계 방향성.")
    compatibility_passed: bool = Field(
        default=True,
        description="Compat Rule 통과 여부",
    )


class Stage4ScenarioSynthesis(BaseModel):
    cartesian_total: int = Field(description="Stage3 결과 기준 Dim Cartesian 조합 수.")
    filtered_by_compatibility: int = Field(
        description="Compat Rule 통과 후 남은 조합 수",
    )
    scenarios: conlist(Scenario, min_length=1, max_length=10) = Field(  # type: ignore[valid-type]
        description="최종 시나리오 5~7건 권장.",
    )


class MECECheck(BaseModel):
    mutually_exclusive: bool = Field(
        description="시나리오 간 동시 성립 사례 부재 시 True.",
    )


class Stage5Validation(BaseModel):
    mece_check: MECECheck = Field(default_factory=lambda: MECECheck(mutually_exclusive=True))
    likelihood_prior: Dict[str, LikelihoodTier] = Field(
        default_factory=dict,
        description="scenario_id -> 5단계 카테고리.",
    )


# ==============================================
# 3. LLM Output Models (internal, not part of state)
# ==============================================

class _Stage2LLMOutput(BaseModel):
    selected_dimensions: conlist(SelectedDimension, min_length=3, max_length=5) = Field(  # type: ignore[valid-type]
        description="선택된 Dim 3~5개.",
    )
    excluded_dimensions: List[ExcludedDimension] = Field(
        default_factory=list,
        description="제외된 Dim 목록.",
    )

    @model_validator(mode="after")
    def _validate_no_dup(self):
        sel = {d.dimension_id for d in self.selected_dimensions}
        exc = {d.dimension_id for d in self.excluded_dimensions}
        if sel & exc:
            raise ValueError(f"selected_dimensions 와 excluded_dimensions 가 중복: {sel & exc}")
        return self


class _Stage3SingleDimOutput(BaseModel):
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택 enum_id 2~4개. 반드시 template_enum_full 의 부분집합.",
    )
    tail_risk_kept: str = Field(
        description="유지된 Tail Risk enum_id (selected_enum 안에 포함).",
    )


class _NarrativeOnly(BaseModel):
    title: str = Field(description="시장 참여자 관점 한 줄 요약")
    description: str = Field(description="3~5줄 시나리오 서술")
    derivation_rationale: str = Field(description="도출 근거")
    price_direction: PriceDirection


class _Stage4LLMOutput(BaseModel):
    narratives: List[_NarrativeOnly] = Field(
        description="입력된 dim 조합 순서와 1:1 동일 길이.",
    )


class _Stage5LLMOutput(BaseModel):
    mutually_exclusive: bool = Field(description="MECE 동시성립 부재 여부")
    rationale: str = Field(default="", description="MECE 판정 근거 1~2줄")
    likelihood_prior: Dict[str, LikelihoodTier] = Field(
        description="scenario_id -> 5단계 Prior",
    )


# ==============================================
# 3. Helper Functions
# ==============================================

def _dim_index(template: Dict) -> Dict[str, Dict]:
    """dimension_id -> dimension dict 인덱스."""
    return {d["dimension_id"]: d for d in template["dimensions"]}


def _enum_id_set(dimension: Dict) -> List[str]:
    return [e["id"] for e in dimension["enum"]]


def _tail_id_set(dimension: Dict) -> List[str]:
    return [e["id"] for e in dimension["enum"] if e.get("tail")]


def _shorten(text: str, max_len: int) -> str:
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def _extract_driver_hint(event: Dict) -> str:
    """Driver 힌트 — detail_analysis 첫 문장 또는 첫 key_bullet 으로 대체."""
    bullets = event.get("key_bullets") or []
    if bullets:
        first = str(bullets[0]).strip()
        return first[:160]
    detail = str(event.get("detail_analysis", "")).strip()
    if not detail:
        return ""
    head = detail.split(".")[0].strip()
    return head[:160]


def _build_c1_base_event(event: Dict) -> C1BaseEvent:
    """단일 Base Event JSON 으로부터 C1 슬롯을 채움."""
    et = event.get("event_type", {}) or {}
    l1 = et.get("level_1_code", "")
    l2 = et.get("level_2_code", "")
    et_key = f"{l1}::{l2}" if l1 and l2 else ""

    return C1BaseEvent(
        event_id=event.get("mi_event_id", ""),
        title=event.get("event_title_ko", ""),
        event_type_l1_l2=et_key,
        summary=event.get("one_line_summary", ""),
        driver=_extract_driver_hint(event),
    )


def _resolve_template_registry_paths() -> List[Path]:
    """우선순위: 환경변수(디렉터리 경로, 하위 'template_registry*.json' 전체) > 모듈 옆 'template_registry*.json' 전체.

    REF_TEMPLATE_REGISTRY_PATH 가 디렉터리면 하위 모든 'template_registry*.json' 파일을 수집.
    """
    import os
    REF_TEMPLATE_REGISTRY_PATH = os.getenv("REF_TEMPLATE_REGISTRY_PATH", "")
    
    if REF_TEMPLATE_REGISTRY_PATH:
        items = [
            s.strip()
            for s in REF_TEMPLATE_REGISTRY_PATH.replace(os.pathsep, ",").split(",")
            if s.strip()
        ]
        paths = []
        for s in items:
            p = Path(s)
            if not p.exists():
                raise FileNotFoundError(f"REF_TEMPLATE_REGISTRY_PATH 가 가리키는 경로 없음: {p}")
            if p.is_dir():
                # 디렉터리면 template_registry*.json 패턴 매칭
                paths.extend(sorted(p.glob("template_registry*.json")))
            elif p.is_file():
                # 특정 파일이 직접 지정된 경우 그대로 사용
                paths.append(p)
        if not paths:
            raise FileNotFoundError(
                f"REF_TEMPLATE_REGISTRY_PATH 에서 template_registry*.json 을 찾지 못함: {REF_TEMPLATE_REGISTRY_PATH}"
            )
        return paths
    
    fallback_dir = Path("apps/common/configs/")
    paths = []
    paths.extend(sorted(fallback_dir.glob("template_registry*.json")))
    
    if not paths:
        raise FileNotFoundError(
            "template_registry*.json 을 찾지 못함. "
            "REF_TEMPLATE_REGISTRY_PATH 환경변수 또는 config 디렉터리 배치 필요."
        )
    return paths


def _load_template_registry() -> Dict:
    """Template Registry 들을 단 1회 로드/병합해 모듈 상수화 (불변 데이터).

    실패/경계 조건:
        - 동일 키('l1::l2')가 두 파일에 존재 시 명시적 ValueError → 조용한 덮어쓰기 방지.
    """
    paths = _resolve_template_registry_paths()
    merged: Dict = {}
    for p in paths:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Support both formats: with/without "templates" wrapper
        if "templates" in data:
            templates = data["templates"]
        else:
            # Direct template mapping format
            templates = data
            
        for k, v in templates.items():
            if k in merged:
                raise ValueError(f"중복 템플릿 키 '{k}' (파일: {p})")
            merged[k] = v
    return merged


# Global template registry cache
TEMPLATE_REGISTRY = _load_template_registry()


# ==============================================
# 4. LLM Infrastructure (sync wrapper around async connector)
# ==============================================

def _is_retryable_api_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in {429, 500, 502, 503, 529}:
        return True
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    keywords = ("overloaded", "rate limit", "too many requests", "timeout", "connection")
    return any(k in name or k in msg for k in keywords)


def _is_retryable_schema_error(exc: Exception) -> bool:
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    keywords = (
        "validationerror", "validation error", "structured", "min_length",
        "max_length", "json", "output parsing", "literal", "enum",
    )
    return "validation" in name or any(k in msg for k in keywords)


def _invoke_structured(schema_cls: type[BaseModel], messages: List[Dict[str, str]],
                       temperature: float = 0.0) -> BaseModel:
    """Synchronous structured output LLM call via the project's invoke_llm_structured_output connector.

    Uses asyncio.run() to bridge from sync context to the async connector,
    exactly as event_flow_agent patterns do.
    """
    async def _call():
        result = await invoke_llm_structured_output(
            output_schema=schema_cls,
            messages=messages,
            temperature=temperature or REF_TEMPERATURE,
            max_retries=2,
        )
        return result.result

    return asyncio.run(_call())


def _invoke_with_retry(
    stage_label: str,
    schema_cls: type[BaseModel],
    system_prompt: str,
    user_prompt: str,
    validate_fn,
    hard_constraints: str = "",
) -> BaseModel | None:
    """LLM 호출 with retry + validation + fallback.

    Returns parsed Pydantic model on success, None on all retries exhausted.
    """
    last_exc: Exception | None = None
    last_validation_exc: Exception | None = None
    accumulated_hint = hard_constraints

    for attempt in range(1, REF_MAX_RETRIES + 1):
        try:
            # Build user message with accumulated constraints
            user_text = user_prompt
            if accumulated_hint:
                user_text = user_text + "\n\n" + accumulated_hint.strip()
            if last_validation_exc is not None and attempt >= 2:
                user_text = user_text + (
                    f"\n[직전 실패 사유]\n- {str(last_validation_exc)[:240]}"
                )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ]
            result = _invoke_structured(schema_cls, messages, temperature=REF_TEMPERATURE)
            if validate_fn:
                validate_fn(result)
            return result

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            is_api = _is_retryable_api_error(exc)
            is_schema = _is_retryable_schema_error(exc)
            is_validation = isinstance(exc, (ValueError, TypeError))
            should_retry = (is_api or is_schema or is_validation) and attempt < REF_MAX_RETRIES

            if not should_retry:
                print(f"  ↳ {stage_label} 재시도 불가 — {exc.__class__.__name__}: {str(exc)[:160]}")
                break

            if is_validation or is_schema:
                last_validation_exc = exc
                accumulated_hint = hard_constraints + (
                    f"\n[직전 실패 원인 — {stage_label}]\n- {str(exc)[:240]}\n"
                )
                reason = "출력 검증/스키마 불일치"
            elif is_api:
                reason = "API 과부하/레이트리밋"
            else:
                reason = "기타 재시도"

            wait_sec = min(20.0, 1.5 ** (attempt - 1)) + random.uniform(0, 0.7)
            err_summary = f"{exc.__class__.__name__}: {str(exc)[:200]}"
            print(
                f"  ↳ {stage_label} 재시도 ({attempt}/{REF_MAX_RETRIES}) — "
                f"{reason}, {wait_sec:.1f}s 후 | 원인: {err_summary}"
            )
            time.sleep(wait_sec)

    print(f"  ↳ {stage_label} 재시도 소진 — fallback 진입 (last_error={type(last_exc).__name__})")
    return None


# ==============================================
# 5. Stage 1 — Context Retriever
# ==============================================

@log_tool
def stage1_build_context_pack(event: Dict) -> Stage1ContextPack:
    """Stage 1 진입점 — Single Base Event → Stage1ContextPack."""
    return Stage1ContextPack(
        C1_base_event=_build_c1_base_event(event),
        C2_linked_records=C2LinkedRecords(window_days=30, records=[]),
        C3_historical_analogs=[],
        C4_related_events=[],
    )


# ==============================================
# 6. Template Resolution
# ==============================================

def _resolve_template(event_type_l1_l2: str) -> Dict:
    """event_type_l1_l2('l1::l2') 키로 템플릿을 조회."""
    tmpl = TEMPLATE_REGISTRY.get(event_type_l1_l2)
    if tmpl is None:
        available = ", ".join(sorted(TEMPLATE_REGISTRY.keys()))
        raise KeyError(
            f"template_registry 에 '{event_type_l1_l2}' 키 없음. 사용 가능: [{available}]"
        )
    return tmpl


# ==============================================
# 7. Stage 2 — Dimension Selector (LLM)
# ==============================================

def _format_dimensions_block(template: Dict) -> str:
    lines: List[str] = []
    for d in template["dimensions"]:
        enum_ids = ", ".join(_enum_id_set(d))
        lines.append(
            f"- {d['dimension_id']} ({d.get('label_ko','')}): enum=[{enum_ids}] / {d.get('description','')}"
        )
    return "\n".join(lines)


STAGE2_SYSTEM = """\
당신은 LNG 시장 멀티시나리오 생성을 위한 'Dimension Selector' 입니다.
주어진 Base Event 와 Template(8개 Dim)을 입력받아, 이번 Event 를 분기시키는 데
유의미한 Dim 을 **3~5개만** 선택하고, 나머지는 제외 사유를 기록하십시오.

## 선택 기준 (반드시 (a) 또는 (c) 만 사용)
- (a) Base Event 본문/요약/드라이버에 직접 언급되거나 명백히 암시됨.
- (c) Driver Tree 상 Impact 경로(가격/수급/물동량)로 강하게 연결됨.

## 절대 금지
- (b) Historical Analog 분기(과거 유사 사례에서 분기 패턴 발견) 기준 **사용 금지**.
  rationale 에 '(b)' 코드를 포함하지 마십시오.

## rationale 작성 규칙
- 반드시 '(a)', '(c)', '(a)(c)' 중 하나로 시작.
- 그 다음 한국어 한 문장으로 근거 부연.
- 예: "(a)(c) 본문 '호르무즈 봉쇄' 직접 언급 + Driver Tree 통항 경로 핵심."

## 제외 사유 작성 규칙
- 'Base Event 와 직접 관련 부재', '현 단계 시그널 없음' 등 한국어 한 줄.
"""

STAGE2_HARD = """\
[중요한 출력 제약 — Stage 2]
- selected_dimensions 길이는 반드시 3~5.
- 모든 dimension_id 는 입력된 Template 의 dimension_id 안에 있어야 함.
- selected ∪ excluded = template 전체 Dim 집합 (누락 금지, 중복 금지).
- rationale 은 (a) / (c) / (a)(c) 중 하나로 시작. (b) 코드 포함 금지.
"""


@log_tool
def stage2_select_dimensions(
    pack: Stage1ContextPack,
    event: Dict,
    template: Dict,
    llm_client=None,
) -> Stage2DimensionSelection:
    """Stage 2 진입점 — 8개 Dim 중 3~5개 선택 (LLM)."""
    template_dim_ids = [d["dimension_id"] for d in template["dimensions"]]
    detail_excerpt = _shorten(event.get("detail_analysis", ""), 600)

    user_prompt = f"""\
## Base Event
- event_id: {pack.C1_base_event.event_id}
- title: {pack.C1_base_event.title}
- event_type_l1_l2: {pack.C1_base_event.event_type_l1_l2}
- summary: {pack.C1_base_event.summary}
- driver: {pack.C1_base_event.driver}
- detail_analysis(요약): {detail_excerpt}

## Template (event_type_l1_l2 = {pack.C1_base_event.event_type_l1_l2})
- template_dimensions_total: {template["template_dimensions_total"]}
- dimensions: 아래 리스트의 dimension_id 만 선택 가능.
{_format_dimensions_block(template)}

## 산출 규칙
- 선택 Dim: 3~5개.
- 모든 미선택 Dim 은 excluded_dimensions 에 사유와 함께 기재.
"""

    def _validate(out: _Stage2LLMOutput) -> None:
        sel_ids = {d.dimension_id for d in out.selected_dimensions}
        exc_ids = {d.dimension_id for d in out.excluded_dimensions}
        unknown = (sel_ids | exc_ids) - set(template_dim_ids)
        if unknown:
            raise ValueError(f"Template 외 dimension_id 사용: {unknown}")
        for d in out.selected_dimensions:
            if "(b)" in d.rationale:
                raise ValueError(f"(b) 기준 rationale 검출: {d.dimension_id}")

    out = _invoke_with_retry(
        stage_label="Stage 2",
        schema_cls=_Stage2LLMOutput,
        system_prompt=STAGE2_SYSTEM,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE2_HARD,
    )

    if out is None:
        out = _stage2_fallback(template_dim_ids)

    # excluded 보강: LLM 이 빠뜨린 미선택 Dim 자동 채움
    sel_ids = {d.dimension_id for d in out.selected_dimensions}
    given_exc_ids = {d.dimension_id for d in out.excluded_dimensions}
    auto_excluded = [
        ExcludedDimension(dimension_id=did, reason="LLM 미언급 — 자동 제외 처리")
        for did in template_dim_ids
        if did not in sel_ids and did not in given_exc_ids
    ]
    excluded = list(out.excluded_dimensions) + auto_excluded

    return Stage2DimensionSelection(
        template_id=pack.C1_base_event.event_type_l1_l2,
        template_dimensions_total=template.get("template_dimensions_total", len(template_dim_ids)),
        selected_dimensions=out.selected_dimensions,
        excluded_dimensions=excluded,
    )


def _stage2_fallback(template_dim_ids: List[str]) -> _Stage2LLMOutput:
    """LLM 실패 시 — 템플릿 앞 4개 Dim 을 (a) 코드로 안전 채택."""
    print("  ↳ Stage 2 fallback: 템플릿 앞 4개 Dim 안전 선택")
    selected = [
        SelectedDimension(
            dimension_id=did,
            rationale="(a) Fallback 안전 선택 — Base Event 와 잠재적 관련성 가정.",
        )
        for did in template_dim_ids[:4]
    ]
    excluded = [
        ExcludedDimension(dimension_id=did, reason="Fallback 자동 제외")
        for did in template_dim_ids[4:]
    ]
    return _Stage2LLMOutput(selected_dimensions=selected, excluded_dimensions=excluded)


# ==============================================
# 8. Stage 3 — Value Reducer (LLM per-dimension)
# ==============================================

STAGE3_SYSTEM = """\
당신은 멀티시나리오 생성을 위한 'Value Reducer' 입니다.
하나의 Dimension 의 5단계 Enum 중에서 **2~4개만** 채택하십시오.

## 선택 규칙 (반드시 준수)
- (b) 극단 보존: Tail Risk(=template 정의상 tail=true) 중 **최소 1개** 를 selected_enum 안에 포함.
- (c) 최종 수: 2~4개.

## 절대 금지
- (a) 인접 병합(시장 영향이 유사하다는 이유로 인접 Enum 을 합쳐 1개로 대체) **사용 금지**.
  → '인접 영향 유사', '비슷한 강도여서 통합' 같은 사유로 인접 Enum 을 한꺼번에 제거하지 말 것.
- 입력 template_enum_full 외의 enum_id 사용 금지.

## "영향 없음(none)" 류 enum 채택 가이드
- Base Event 가 이미 발생·진행 중이고 해당 Dim 영역에서 영향이 관측되고 있다면,
  '영향 없음/정상(보통 enum_id='none')' 류 enum 은 **원칙적으로 selected_enum 에서 제외**하십시오.
- 단, 해당 Dim 이 '단기 종전 후 정상화 baseline' 시나리오 분기를 위해 꼭 필요할 때만
  예외적으로 채택하고, rationale 성격(=baseline 표현 의도)을 description 에 명시하십시오.

## tail_risk_kept
- selected_enum 에 포함된 enum_id 중 tail=true 인 1개를 명시.
"""

STAGE3_HARD = """\
[중요한 출력 제약 — Stage 3]
- selected_enum 길이는 반드시 2~4.
- 모든 enum_id 는 입력된 template_enum_full 안에 있어야 함.
- tail_risk_kept 는 selected_enum 안의 값이며, tail=true 인 enum 이어야 함.
- 인접 병합 사유로 Enum 제거 금지.
"""


@log_tool
def stage3_reduce_values(
    pack: Stage1ContextPack,
    selected: Stage2DimensionSelection,
    template: Dict,
    llm_client=None,
) -> Stage3ValueSelection:
    """Stage 3 진입점 — 선택된 Dim 별로 LLM 호출하여 Enum 축소."""
    dim_idx = _dim_index(template)

    per_dim: List[PerDimensionValue] = []
    for sd in selected.selected_dimensions:
        dim = dim_idx.get(sd.dimension_id)
        if dim is None:
            print(f"  ↳ 경고: Stage3 — '{sd.dimension_id}' 템플릿 누락. 스킵.")
            continue

        enum_full = _enum_id_set(dim)
        tail_full = _tail_id_set(dim)

        # Format enum block with label and tail info
        enum_full_block = ", ".join(
            f"{e['id']}({e.get('label','')}, tail={'Y' if e.get('tail') else 'N'})"
            for e in dim["enum"]
        )
        tail_block = ", ".join(tail_full) if tail_full else "(없음)"

        user_prompt = f"""\
## Base Event 요약
- title: {pack.C1_base_event.title}
- summary: {pack.C1_base_event.summary}
- driver: {pack.C1_base_event.driver}

## Dimension 정보
- dimension_id: {dim["dimension_id"]}
- label_ko: {dim.get("label_ko", "")}
- description: {dim.get("description", "")}
- template_enum_full: {enum_full_block}
- tail enum 후보: {tail_block}

## 산출
- 채택 enum_id 2~4개 + tail_risk_kept 1개.
"""

        def _validate(out: _Stage3SingleDimOutput) -> None:
            unknown = set(out.selected_enum) - set(enum_full)
            if unknown:
                raise ValueError(f"template_enum_full 외 enum_id 사용: {unknown}")
            if out.tail_risk_kept not in out.selected_enum:
                raise ValueError("tail_risk_kept 가 selected_enum 안에 없음.")
            if tail_full and out.tail_risk_kept not in tail_full:
                raise ValueError(
                    f"tail_risk_kept='{out.tail_risk_kept}' 가 tail enum 집합에 없음. "
                    f"tail 후보: {tail_full}"
                )

        out = _invoke_with_retry(
            stage_label=f"Stage 3 [{dim['dimension_id']}]",
            schema_cls=_Stage3SingleDimOutput,
            system_prompt=STAGE3_SYSTEM,
            user_prompt=user_prompt,
            validate_fn=_validate,
            hard_constraints=STAGE3_HARD,
        )

        if out is None:
            out = _stage3_fallback(dim)

        per_dim.append(PerDimensionValue(
            dimension_id=dim["dimension_id"],
            template_enum_full=enum_full,
            selected_enum=out.selected_enum,
            tail_risk_kept=out.tail_risk_kept,
        ))

    return Stage3ValueSelection(per_dimension=per_dim)


def _stage3_fallback(dim: Dict) -> _Stage3SingleDimOutput:
    """LLM 실패 시 — 첫 1개 + 중간 1개 + Tail 1개 안전 채택."""
    print(f"  ↳ Stage 3 fallback ({dim['dimension_id']}): 안전 3개 Enum 선택")
    enum_full = _enum_id_set(dim)
    tail_full = _tail_id_set(dim)
    tail_pick = tail_full[0] if tail_full else enum_full[-1]
    base = enum_full[0]
    mid = enum_full[len(enum_full) // 2] if len(enum_full) >= 2 else enum_full[0]
    selected = []
    for cand in (base, mid, tail_pick):
        if cand and cand not in selected:
            selected.append(cand)
    while len(selected) < 2 and enum_full:
        for cand in enum_full:
            if cand not in selected:
                selected.append(cand)
                break
        else:
            break
    return _Stage3SingleDimOutput(selected_enum=selected[:4], tail_risk_kept=tail_pick)


# ==============================================
# 9. Stage 4 — Scenario Synthesis (Compat + Narrative LLM)
# ==============================================

def _cartesian_combos(stage3: Stage3ValueSelection) -> List[Dict[str, str]]:
    """Stage3 결과를 Dim×Enum Cartesian 으로 펼침."""
    dim_ids = [pd.dimension_id for pd in stage3.per_dimension]
    enum_lists = [list(pd.selected_enum) for pd in stage3.per_dimension]
    combos: List[Dict[str, str]] = []
    for tup in product(*enum_lists):
        combos.append({did: eid for did, eid in zip(dim_ids, tup)})
    return combos


def _apply_compat_rules(
    combos: List[Dict[str, str]],
    template: Dict,
) -> Tuple[List[Dict[str, str]], List[Tuple[Dict[str, str], str]]]:
    """Compatibility Rule Engine — 통과/탈락 분리.

    forbid 정의: 모든 forbid 키의 값이 forbid 리스트 안에 들어있으면 탈락.
    """
    rules = template.get("compatibility_rules", []) or []
    passed: List[Dict[str, str]] = []
    rejected: List[Tuple[Dict[str, str], str]] = []
    for combo in combos:
        violated_rule: str | None = None
        for rule in rules:
            forbid: Dict[str, List[str]] = rule.get("forbid", {})
            if not forbid:
                continue
            hit = True
            for k, vals in forbid.items():
                if combo.get(k) not in vals:
                    hit = False
                    break
            if hit:
                violated_rule = rule.get("rule_id", "UNKNOWN")
                break
        if violated_rule is None:
            passed.append(combo)
        else:
            rejected.append((combo, violated_rule))
    return passed, rejected


def _select_target_combos(
    passed: List[Dict[str, str]],
    stage3: Stage3ValueSelection,
    target_n: int,
    template: Dict,
) -> List[Dict[str, str]]:
    """Compat 통과 조합 중 5~7개 추출 — 다양성 기반 선정.

    1) Tail score = combo 내 enum_id 중 template.enum.tail=true 인 개수.
    2) Base anchor(score 최소): 가장 baseline 에 가까운 1건.
    3) Extreme anchor(score 최대): 가장 tail 쪽 1건.
    4) 나머지: Farthest-First 탐색으로 다양성 확보.
    """
    if len(passed) <= target_n:
        return list(passed)

    dim_idx = _dim_index(template)
    template_tail: Dict[str, set] = {
        pd.dimension_id: set(
            e["id"] for e in dim_idx.get(pd.dimension_id, {}).get("enum", [])
            if e.get("tail")
        )
        for pd in stage3.per_dimension
    }

    def _tail_score(combo: Dict[str, str]) -> int:
        return sum(
            1 for did, eid in combo.items() if eid in template_tail.get(did, set())
        )

    def _hamming(a: Dict[str, str], b: Dict[str, str]) -> int:
        return sum(1 for k in a if a.get(k) != b.get(k))

    def _farthest_idx(pool_idx: List[int], anchors: List[int]) -> int:
        best_i, best_d = pool_idx[0], -1
        for i in pool_idx:
            d_min = min(_hamming(passed[i], passed[a]) for a in anchors)
            if d_min > best_d:
                best_i, best_d = i, d_min
        return best_i

    scores = [_tail_score(c) for c in passed]
    min_s, max_s = min(scores), max(scores)
    base_idx = next(i for i, s in enumerate(scores) if s == min_s)

    chosen_idx: List[int] = [base_idx]

    if max_s != min_s:
        ext_pool = [i for i, s in enumerate(scores) if s == max_s]
        chosen_idx.append(_farthest_idx(ext_pool, chosen_idx))

    pool = [i for i in range(len(passed)) if i not in chosen_idx]
    while len(chosen_idx) < target_n and pool:
        nxt = _farthest_idx(pool, chosen_idx)
        chosen_idx.append(nxt)
        pool.remove(nxt)

    return [passed[i] for i in chosen_idx[:target_n]]


STAGE4_SYSTEM = """\
당신은 LNG 멀티시나리오 'Narrative Writer' 입니다.
이미 Compatibility Rule 을 통과한 'Dim 조합' 리스트를 입력받아, 각 조합에 대해
시장 참여자 관점의 시나리오 서사를 작성하십시오.

## 작성 가이드라인 (반드시 준수)
- title (1줄): 시장 참여자 관점의 한 줄 요약. 예: '1개월 내 정상화'.
- description (3~5줄): 각 시나리오의 가정치 조합(=주요 Dim 값) + 전개 양상.
- derivation_rationale: 이 시나리오가 왜 도출되는지 — 어떤 Dim 조합·맥락 단서로부터 왔는지.
- price_direction.brent / jkm / ttf: 7단계(strong_bull|bull|mild_bull|neutral|mild_bear|bear|strong_bear) 중 1개.
- 입력 조합은 항상 dim_key -> value의 flat object(JSON object) 의미로 해석.
- 올바른 형식 예시: {"period":"3개월","utilization_change_direction":"감소"}
- 금지 형식 예시: [{"dim_key":"period","value":"3개월"}], [{"dimension_id":"period","value":"3개월"}]

## 절대 금지
- '결과(가격 방향)가 동일하므로 두 조합을 합쳐서 1개로 만든다' 같은 통합/생략 행위.
  → 입력으로 들어온 조합 개수와 출력 narratives 개수는 **반드시 일치**.
"""

STAGE4_HARD = """\
[중요한 출력 제약 — Stage 4]
- narratives 길이는 입력 조합 수와 정확히 일치.
- price_direction.brent / jkm / ttf 는 반드시 7단계 enum 중 정확히 1개.
- description 은 3~5줄, title 은 1줄.
- '결과 동일 조합 통합' 금지 — 출력 길이를 줄이지 마십시오.
- 입력 조합을 ARRAY 형태로 재해석/치환하지 마십시오(항상 flat object 가정).
- 입력 조합의 key 집합은 selected dim_key 와 정확히 일치해야 함(누락/여분 금지).
"""


@log_tool
def stage4_synthesize_scenarios(
    pack: Stage1ContextPack,
    stage3: Stage3ValueSelection,
    template: Dict,
    llm_client=None,
) -> Stage4ScenarioSynthesis:
    """Stage 4 진입점 — Cartesian → Compat → 5~7건 선정 → Narrative LLM."""
    combos_all = _cartesian_combos(stage3)
    passed, rejected = _apply_compat_rules(combos_all, template)
    print(
        f"  ▸ Stage 4 — cartesian={len(combos_all)} / compat_passed={len(passed)} / "
        f"rejected={len(rejected)}"
    )
    for combo, rule in rejected[:5]:
        print(f"    - reject ({rule}): {combo}")

    target = _select_target_combos(passed, stage3, REF_TARGET_SCENARIOS, template)
    if not target:
        print("  ↳ 경고: Compat 통과 조합 0건 — Cartesian 전체 중 1건 강제 채택.")
        target = combos_all[:1] or [{}]

    dim_idx = _dim_index(template)
    dim_label_block = "\n".join(
        f"- {pd.dimension_id} ({dim_idx.get(pd.dimension_id, {}).get('label_ko', '')})"
        for pd in stage3.per_dimension
    )
    combos_block = "\n".join(
        f"  [{i+1}] " + ", ".join(f"{k}={v}" for k, v in combo.items())
        for i, combo in enumerate(target)
    )

    user_prompt = f"""\
## Base Event
- title: {pack.C1_base_event.title}
- summary: {pack.C1_base_event.summary}
- driver: {pack.C1_base_event.driver}

## Dimension 라벨 (참고)
{dim_label_block}

## 작성 대상 조합 ({len(target)}개)  — 입력 순서를 그대로 유지하여 narratives 출력
{combos_block}

## 산출 규칙
- narratives 길이 = {len(target)}.
- 각 narrative 의 description 은 3~5줄.
- title 은 한 줄.
"""

    def _validate(out: _Stage4LLMOutput) -> None:
        if len(out.narratives) != len(target):
            raise ValueError(
                f"narratives 길이 불일치: {len(out.narratives)} != {len(target)}"
            )
        for n in out.narratives:
            for v in (n.price_direction.brent, n.price_direction.jkm, n.price_direction.ttf):
                if v not in PRICE_TIERS:
                    raise ValueError(f"price_direction 범위 밖 값: {v}")

    out = _invoke_with_retry(
        stage_label="Stage 4",
        schema_cls=_Stage4LLMOutput,
        system_prompt=STAGE4_SYSTEM,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE4_HARD,
    )

    if out is None:
        out = _stage4_fallback(target)

    scenarios: List[Scenario] = []
    for i, (combo, narr) in enumerate(zip(target, out.narratives), start=1):
        scenarios.append(Scenario(
            scenario_id=f"S_{i:02d}",
            title=narr.title,
            dimension_values=combo,
            description=narr.description,
            derivation_rationale=narr.derivation_rationale,
            price_direction=narr.price_direction,
            compatibility_passed=True,
        ))

    return Stage4ScenarioSynthesis(
        cartesian_total=len(combos_all),
        filtered_by_compatibility=len(passed),
        scenarios=scenarios,
    )


def _stage4_fallback(target: List[Dict[str, str]]) -> _Stage4LLMOutput:
    """LLM 실패 시 — 모든 조합에 대해 중립 시나리오 narrative 생성."""
    print(f"  ↳ Stage 4 fallback: {len(target)}개 중립 narrative 생성")
    narratives = [
        _NarrativeOnly(
            title=f"[Fallback] 조합 #{i+1} 시나리오",
            description=(
                "LLM 호출 실패로 fallback 서사가 적용됨.\n"
                f"가정치 조합: {', '.join(f'{k}={v}' for k, v in combo.items())}\n"
                "전개 양상 판단 보류 — 후속 재실행 필요."
            ),
            derivation_rationale="LLM 실패 — 안전 기본값.",
            price_direction=PriceDirection(brent="neutral", jkm="neutral", ttf="neutral"),
        )
        for i, combo in enumerate(target)
    ]
    return _Stage4LLMOutput(narratives=narratives)


# ==============================================
# 10. Stage 5 — Validation (MECE + Likelihood LLM)
# ==============================================

STAGE5_SYSTEM = """\
당신은 멀티시나리오 'MECE Validator + Likelihood Calibrator' 입니다.

## 검사 항목 (반드시 이 둘만)
1. mutually_exclusive (M): 동일 시점에 정확히 한 시나리오만 참이 될 수 있는가?
   - 본 파이프라인의 시나리오는 모두 (dimension_id → enum_id) 단일 조합으로 정의됨.
   - 따라서 두 시나리오의 dimension_values 가 **하나라도 서로 다르면** 정의상 동시 성립 불가 → True.
   - 모든 시나리오의 dimension_values 조합이 서로 유일하면 True.
   - 동일한 dimension_values 조합을 가진 시나리오 쌍이 있을 때만 False.
   - narrative(서술 톤·결과 가격 방향)가 비슷하다는 이유로 False 를 반환하지 마십시오.
2. likelihood_prior: 각 시나리오마다 발생 가능성을 5단계 카테고리로 부여.
   very_low, low, medium, high, very_high 중 정확히 1개.

## 절대 금지
- 'Collective Coverage(≥80%)' 검사 금지.
- 'Likelihood Sum = 1.0' 검사/수치 정규화 금지.
- 수치 Prior(예: 0.4, 40%) 출력 금지 — 반드시 5단계 카테고리만.

## Prior 부여 가이드 (참고)
- Tail Risk(시설 영구 손상·전면 봉쇄 등 극단)는 통상 'low' 또는 'very_low'.
- Base case 성격(완화·정상화)은 'medium' 또는 'high'.
- 시장 충격 강한 중기 차질은 'medium' 부근.
"""

STAGE5_HARD = """\
[중요한 출력 제약 — Stage 5]
- likelihood_prior 키 집합은 입력된 scenario_id 와 정확히 일치 (누락·여분 금지).
- 값은 {very_low|low|medium|high|very_high} 중 정확히 1개.
- 수치 출력 금지. Coverage·Sum 검사 금지.
"""


@log_tool
def stage5_validate(
    pack: Stage1ContextPack,
    stage4: Stage4ScenarioSynthesis,
    llm_client=None,
) -> Stage5Validation:
    """Stage 5 진입점 — MECE 통과 여부 + 5단계 Prior 부여."""
    sc_ids = [s.scenario_id for s in stage4.scenarios]

    scenarios_block = "\n".join(
        f"- {s.scenario_id} | {s.title}\n"
        f"    dims: {', '.join(f'{k}={v}' for k,v in s.dimension_values.items())}\n"
        f"    price: brent={s.price_direction.brent}, jkm={s.price_direction.jkm}, ttf={s.price_direction.ttf}"
        for s in stage4.scenarios
    )

    user_prompt = f"""\
## Base Event 요약
- title: {pack.C1_base_event.title}
- summary: {pack.C1_base_event.summary}

## 시나리오 목록 ({len(sc_ids)}건)
{scenarios_block}

## 산출
- mutually_exclusive (bool) + rationale (1~2줄).
- likelihood_prior: 모든 scenario_id 에 대해 5단계 중 1개.
"""

    def _validate(out: _Stage5LLMOutput) -> None:
        keys = set(out.likelihood_prior.keys())
        wanted = set(sc_ids)
        if keys != wanted:
            raise ValueError(
                f"likelihood_prior 키 집합 불일치: 누락={wanted - keys}, 여분={keys - wanted}"
            )
        for v in out.likelihood_prior.values():
            if v not in LIKELIHOOD_TIERS:
                raise ValueError(f"5단계 외 Prior 값: {v}")

    out = _invoke_with_retry(
        stage_label="Stage 5",
        schema_cls=_Stage5LLMOutput,
        system_prompt=STAGE5_SYSTEM,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE5_HARD,
    )

    if out is None:
        out = _stage5_fallback(sc_ids)

    # 방어적 후처리: 입력 범위 밖 키/값 정리
    cleaned: Dict[str, str] = {}
    for k in sc_ids:
        v = out.likelihood_prior.get(k, "medium")
        if v not in LIKELIHOOD_TIERS:
            v = "medium"
        cleaned[k] = v

    # MECE 결정론적 판정 우선: dimension_values 조합이 모두 유일하면 ME=True
    deterministic_me = _all_dim_values_unique(stage4.scenarios)
    if bool(out.mutually_exclusive) != deterministic_me:
        print(
            f"  ↳ Stage 5 — LLM 판정({out.mutually_exclusive}) 과 코드 결정론 판정"
            f"({deterministic_me}) 불일치 → 코드 판정 우선 적용"
        )

    return Stage5Validation(
        mece_check=MECECheck(mutually_exclusive=deterministic_me),
        likelihood_prior=cleaned,  # type: ignore[arg-type]
    )


def _all_dim_values_unique(scenarios: List[Scenario]) -> bool:
    """모든 시나리오의 dimension_values 조합이 서로 유일한지 검사."""
    seen: set = set()
    for s in scenarios:
        key = tuple(sorted(s.dimension_values.items()))
        if key in seen:
            return False
        seen.add(key)
    return True


def _stage5_fallback(sc_ids: List[str]) -> _Stage5LLMOutput:
    """LLM 실패 시 — 모두 'medium' 으로 안전 부여."""
    print("  ↳ Stage 5 fallback: 전체 'medium' Prior 안전 부여")
    return _Stage5LLMOutput(
        mutually_exclusive=True,
        rationale="Fallback — Prior 카테고리 정밀 판정 보류.",
        likelihood_prior={sid: "medium" for sid in sc_ids},
    )