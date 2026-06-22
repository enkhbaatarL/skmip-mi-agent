"""Scenario generation stages used by the scenario group agent."""

import asyncio
import os
import random
import re
import time
from itertools import product
from typing import Any, Dict, List, Literal, Tuple

from pydantic import BaseModel, Field, conlist, model_validator

from apps.agents.scenario_group_agent.baseline_contrast import (
    check_baseline_contrast_coverage,
)
from apps.common.logging.decorators import log_tool


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
DimensionValueMap = Dict[str, str]

# --- LLM config constants (from env) ---
REF_MAX_RETRIES: int = int(os.getenv("REF_MAX_RETRIES", "5"))
REF_TARGET_SCENARIOS: int = int(os.getenv("REF_TARGET_SCENARIOS", "6"))
REF_TEMPERATURE: float = float(os.getenv("REF_TEMPERATURE", "0.0"))
REF_QUICK_VALIDATE_MAX_RETRIES: int = int(os.getenv("REF_QUICK_VALIDATE_MAX_RETRIES", "2"))


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


class TemplateDimension(BaseModel):
    label: str = Field(description="Dimension 표시명")
    dim_key: str = Field(description="Dimension key")
    required: bool = Field(default=False, description="필수 여부")
    value_enums: List[str] = Field(
        default_factory=list,
        description="Dimension 값 후보 목록",
    )
    display_order: int = Field(default=999999, description="표시 순서")

    @model_validator(mode="after")
    def _validate_template_dimension(self):
        dim_key = str(self.dim_key).strip()
        if not dim_key:
            raise ValueError("dim_key is required.")
        enums = [str(value).strip() for value in self.value_enums if str(value).strip()]
        if len(enums) < 2:
            raise ValueError(f"value_enums must include at least two values: dim_key={dim_key}")
        if len(set(enums)) != len(enums):
            raise ValueError(f"value_enums contains duplicates: dim_key={dim_key}")
        self.dim_key = dim_key
        self.label = str(self.label).strip() or dim_key
        self.value_enums = enums
        return self

    def enum_items(self) -> list[dict[str, Any]]:
        return [
            {
                "id": enum_label,
                "label": enum_label,
                "tail": False,
            }
            for enum_label in self.value_enums
        ]

    def to_runtime_dimension(self) -> dict[str, Any]:
        return {
            "dim_key": self.dim_key,
            "label_ko": self.label,
            "description": self.label,
            "enum": self.enum_items(),
        }


class ScenarioTemplate(BaseModel):
    label_ko: str = Field(default="", description="템플릿 라벨")
    template_dimensions_total: int | None = Field(
        default=None,
        description="템플릿 전체 Dimension 수",
    )
    dimensions: List[TemplateDimension] = Field(
        default_factory=list,
        description="Dimension 템플릿 정의",
    )
    compatibility_rules: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="조합 호환성 규칙",
    )

    @model_validator(mode="after")
    def _validate_template(self):
        ordered = self.ordered_dimensions()
        if len(ordered) < 3:
            raise ValueError("template must include at least three dimensions.")
        dim_keys = [dimension.dim_key for dimension in ordered]
        if len(set(dim_keys)) != len(dim_keys):
            raise ValueError("template contains duplicate dim_key.")
        return self

    def ordered_dimensions(self) -> list[TemplateDimension]:
        return sorted(
            self.dimensions,
            key=lambda dimension: (dimension.display_order, dimension.dim_key),
        )

    def resolved_total(self) -> int:
        return self.template_dimensions_total or len(self.dimensions)


class SelectedDimension(BaseModel):
    dim_key: str = Field(description="템플릿의 dim_key")
    rationale: str = Field(
        description=(
            "선택 근거. 반드시 '(a)' 또는 '(c)' 또는 '(a)(c)' 코드로 시작하고, "
            "한국어 근거문을 1줄로 부연."
        )
    )


class ExcludedDimension(BaseModel):
    dim_key: str = Field(description="제외된 템플릿 dim_key")
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
    dim_key: str = Field(description="템플릿의 dim_key")
    template_enum_full: List[str] = Field(
        default_factory=list,
        description="해당 Dim 의 원본 value_enums 전체.",
    )
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택한 Enum ID 2~4개. 인접 병합 금지.",
    )


class Stage3ValueSelection(BaseModel):
    per_dimension: List[PerDimensionValue] = Field(
        default_factory=list,
        description="Dim 별 Value 축소 결과 리스트.",
    )


class PriceDirection(BaseModel):
    jkm: PriceTier = Field(description="JKM 방향성 7단계")
    ttf: PriceTier = Field(description="TTF 방향성 7단계")
    hh: PriceTier = Field(description="Henry Hub 방향성 7단계")


class Scenario(BaseModel):
    scenario_id: str = Field(description="S_01 형태")
    title: str = Field(description="시장 참여자 관점 한 줄 요약. 공백과 문장부호를 포함해 100자 이내.")
    dimension_values: Dict[str, str] = Field(
        description="dim_key -> value 의 1:1 매핑.",
    )
    description: str = Field(
        description="3~5줄. 주요 Dim 가정치 조합 + 전개 양상 서술. 공백과 문장부호를 포함해 300~500자.",
    )
    derivation_rationale: str = Field(
        description="이 시나리오를 도출한 근거.",
    )
    price_direction: PriceDirection = Field(description="JKM/TTF/HH 7단계 방향성.")
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


class ScenarioGroupMetadata(BaseModel):
    title: str = Field(description="시나리오 그룹명. 공백과 문장부호를 포함해 100자 이내.")
    description: str = Field(description="시나리오 그룹 설명. 공백과 문장부호를 포함해 300~400자.")


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
        sel = {d.dim_key for d in self.selected_dimensions}
        exc = {d.dim_key for d in self.excluded_dimensions}
        if sel & exc:
            raise ValueError(f"selected_dimensions 와 excluded_dimensions 가 중복: {sel & exc}")
        return self


class _Stage3SingleDimOutput(BaseModel):
    selected_enum: conlist(str, min_length=2, max_length=4) = Field(  # type: ignore[valid-type]
        description="채택 값 2~4개. 반드시 value_enums 의 부분집합.",
    )


class _NarrativeOnly(BaseModel):
    title: str = Field(description="시장 참여자 관점 한 줄 요약. 공백과 문장부호를 포함해 100자 이내.")
    description: str = Field(description="3~5줄 시나리오 서술. 공백과 문장부호를 포함해 300~500자.")
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


class _ScenarioGroupMetadataOutput(BaseModel):
    title: str = Field(description="시나리오 그룹명. 공백과 문장부호를 포함해 100자 이내.")
    description: str = Field(description="시나리오 그룹 설명. 공백과 문장부호를 포함해 300~400자.")


# ==============================================
# 3. Helper Functions
# ==============================================

def _dim_index(template: ScenarioTemplate) -> Dict[str, Dict]:
    """dim_key -> dimension dict 인덱스."""
    return {
        dimension.dim_key: dimension.to_runtime_dimension()
        for dimension in template.ordered_dimensions()
    }


def _enum_id_set(dimension: Dict) -> List[str]:
    return [e["id"] for e in dimension["enum"]]


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
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

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
# 6. Stage 2 — Dimension Selector (LLM)
# ==============================================

def _format_dimensions_block(template: ScenarioTemplate) -> str:
    lines: List[str] = []
    for dimension in template.ordered_dimensions():
        value_enums = ", ".join(dimension.value_enums)
        required_mark = "Y" if dimension.required else "N"
        lines.append(
            f"- {dimension.dim_key} (label={dimension.label}, required={required_mark}): value_enums=[{value_enums}]"
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
- 모든 dim_key 는 입력된 Template 의 dim_key 안에 있어야 함.
- selected ∪ excluded = template 전체 Dim 집합 (누락 금지, 중복 금지).
- rationale 은 (a) / (c) / (a)(c) 중 하나로 시작. (b) 코드 포함 금지.
"""


@log_tool
def stage2_select_dimensions(
    pack: Stage1ContextPack,
    event: Dict,
    template: ScenarioTemplate,
    llm_client=None,
) -> Stage2DimensionSelection:
    """Stage 2 진입점 — 8개 Dim 중 3~5개 선택 (LLM)."""
    template_dim_ids = [dimension.dim_key for dimension in template.ordered_dimensions()]
    required_dim_ids = [
        dimension.dim_key
        for dimension in template.ordered_dimensions()
        if dimension.required
    ]
    if len(required_dim_ids) > 5:
        raise ValueError(
            "required=true 인 dim_key 가 5개를 초과하여 Stage2(3~5개 선택) 규칙과 충돌합니다. "
            f"required_dim_keys={required_dim_ids}"
        )
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
- template_dimensions_total: {template.resolved_total()}
- dimensions: 아래 리스트의 dim_key 만 선택 가능.
{_format_dimensions_block(template)}
- required=true 인 dim_key: {required_dim_ids if required_dim_ids else '없음'}

## 산출 규칙
- 선택 Dim: 3~5개.
- required=true 인 dim_key 는 반드시 selected_dimensions 에 모두 포함.
- 모든 미선택 Dim 은 excluded_dimensions 에 사유와 함께 기재.
"""

    def _validate(out: _Stage2LLMOutput) -> None:
        sel_ids = {d.dim_key for d in out.selected_dimensions}
        exc_ids = {d.dim_key for d in out.excluded_dimensions}
        unknown = (sel_ids | exc_ids) - set(template_dim_ids)
        if unknown:
            raise ValueError(f"Template 외 dim_key 사용: {unknown}")
        missing_required = set(required_dim_ids) - sel_ids
        if missing_required:
            raise ValueError(f"required=true dim_key 누락: {sorted(missing_required)}")
        for d in out.selected_dimensions:
            if "(b)" in d.rationale:
                raise ValueError(f"(b) 기준 rationale 검출: {d.dim_key}")

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
    selected_dimensions = list(out.selected_dimensions)
    sel_ids = {d.dim_key for d in selected_dimensions}
    # required=true dim 누락 시 자동 추가
    for required_dim in required_dim_ids:
        if required_dim not in sel_ids:
            selected_dimensions.append(
                SelectedDimension(
                    dim_key=required_dim,
                    rationale="(a) required=true 규칙으로 자동 포함.",
                )
            )
            sel_ids.add(required_dim)
    # 5개 초과면 required를 우선 유지하고 비required를 잘라서 5개로 맞춤
    if len(selected_dimensions) > 5:
        required_set = set(required_dim_ids)
        kept_required = [d for d in selected_dimensions if d.dim_key in required_set]
        non_required = [d for d in selected_dimensions if d.dim_key not in required_set]
        slots_left = max(0, 5 - len(kept_required))
        selected_dimensions = kept_required + non_required[:slots_left]
        sel_ids = {d.dim_key for d in selected_dimensions}

    # 3개 미만이면 템플릿에서 순서대로 채워서 최소 3개 보장
    if len(selected_dimensions) < 3:
        for dim_id in template_dim_ids:
            if dim_id not in sel_ids:
                selected_dimensions.append(
                    SelectedDimension(
                        dim_key=dim_id,
                        rationale="(a) 최소 선택 개수(3개) 충족을 위한 자동 보강.",
                    )
                )
                sel_ids.add(dim_id)
            if len(selected_dimensions) >= 3:
                break

    given_exc_ids = {d.dim_key for d in out.excluded_dimensions}
    auto_excluded = [
        ExcludedDimension(dim_key=did, reason="LLM 미언급 — 자동 제외 처리")
        for did in template_dim_ids
        if did not in sel_ids and did not in given_exc_ids
    ]
    excluded = list(out.excluded_dimensions) + auto_excluded

    return Stage2DimensionSelection(
        template_id=pack.C1_base_event.event_type_l1_l2,
        template_dimensions_total=template.resolved_total(),
        selected_dimensions=selected_dimensions,
        excluded_dimensions=excluded,
    )


def _stage2_fallback(template_dim_ids: List[str]) -> _Stage2LLMOutput:
    """LLM 실패 시 — 템플릿 앞 4개 Dim 을 (a) 코드로 안전 채택."""
    print("  ↳ Stage 2 fallback: 템플릿 앞 4개 Dim 안전 선택")
    selected = [
        SelectedDimension(
            dim_key=did,
            rationale="(a) Fallback 안전 선택 — Base Event 와 잠재적 관련성 가정.",
        )
        for did in template_dim_ids[:4]
    ]
    excluded = [
        ExcludedDimension(dim_key=did, reason="Fallback 자동 제외")
        for did in template_dim_ids[4:]
    ]
    return _Stage2LLMOutput(selected_dimensions=selected, excluded_dimensions=excluded)


# ==============================================
# 8. Stage 3 — Value Reducer (LLM per-dimension)
# ==============================================

STAGE3_SYSTEM = """\
당신은 멀티시나리오 생성을 위한 'Value Reducer' 입니다.
하나의 Dimension 의 value_enums 중에서 **2~4개 값만** 채택하십시오.

## 선택 규칙 (반드시 준수)
- 최종 수: 2~4개.
- 이후 Stage 4 에서 baseline 대비 대안값 coverage 를 만들 수 있도록, 의미가 서로 다른 값을 선택하십시오.

## 절대 금지
- (a) 인접 병합(시장 영향이 유사하다는 이유로 인접 Enum 을 합쳐 1개로 대체) **사용 금지**.
  → '인접 영향 유사', '비슷한 강도여서 통합' 같은 사유로 인접 Enum 을 한꺼번에 제거하지 말 것.
- 입력 value_enums 외의 값 사용 금지.

## "영향 없음(none)" 류 enum 채택 가이드
- Base Event 가 이미 발생·진행 중이고 해당 Dim 영역에서 영향이 관측되고 있다면,
  '영향 없음/정상(보통 enum_id='none')' 류 enum 은 **원칙적으로 selected_enum 에서 제외**하십시오.
- 단, 해당 Dim 이 '단기 종전 후 정상화 baseline' 시나리오 분기를 위해 꼭 필요할 때만
  예외적으로 채택하고, rationale 성격(=baseline 표현 의도)을 description 에 명시하십시오.

## 이 단계에서 즉시 충족해야 하는 로컬 규칙
- (R02-local) 각 Dim 의 selected_enum 에는 서로 다른 값이 최소 2개 포함되어야 함.

## 참고 (다음 단계와의 연결 맥락)
- 위 로컬 규칙은 Stage 4 조합 생성 시 baseline contrast coverage 와 값 다양성 확보를 위한 최소 조건이다.
"""

STAGE3_HARD = """\
[중요한 출력 제약 — Stage 3]
- selected_enum 길이는 반드시 2~4.
- selected_enum 의 모든 값은 입력된 value_enums 안에 있어야 함.
- 인접 병합 사유로 Enum 제거 금지.
"""


@log_tool
def stage3_reduce_values(
    pack: Stage1ContextPack,
    selected: Stage2DimensionSelection,
    template: ScenarioTemplate,
    llm_client=None,
) -> Stage3ValueSelection:
    """Stage 3 진입점 — 선택된 Dim 별로 LLM 호출하여 Enum 축소."""
    dim_idx = _dim_index(template)

    per_dim: List[PerDimensionValue] = []
    for sd in selected.selected_dimensions:
        dim = dim_idx.get(sd.dim_key)
        if dim is None:
            print(f"  ↳ 경고: Stage3 — '{sd.dim_key}' 템플릿 누락. 스킵.")
            continue

        enum_full = _enum_id_set(dim)
        # Format enum block with labels only. Enum order and tail flags are not probability signals.
        enum_full_block = ", ".join(
            f"{e['id']}({e.get('label','')})"
            for e in dim["enum"]
        )

        user_prompt = f"""\
## Base Event 요약
- title: {pack.C1_base_event.title}
- summary: {pack.C1_base_event.summary}
- driver: {pack.C1_base_event.driver}

## Dimension 정보
- dim_key: {dim["dim_key"]}
- label_ko: {dim.get("label_ko", "")}
- description: {dim.get("description", "")}
- value_enums(=선택 가능한 값): {enum_full_block}

## 산출
- 채택 값 2~4개.
"""

        def _validate(out: _Stage3SingleDimOutput) -> None:
            unknown = set(out.selected_enum) - set(enum_full)
            if unknown:
                raise ValueError(f"value_enums 외 값 사용: {unknown}")

        out = _invoke_with_retry(
            stage_label=f"Stage 3 [{dim['dim_key']}]",
            schema_cls=_Stage3SingleDimOutput,
            system_prompt=STAGE3_SYSTEM,
            user_prompt=user_prompt,
            validate_fn=_validate,
            hard_constraints=STAGE3_HARD,
        )

        if out is None:
            out = _stage3_fallback(dim)

        per_dim.append(PerDimensionValue(
            dim_key=dim["dim_key"],
            template_enum_full=enum_full,
            selected_enum=out.selected_enum,
        ))

    return Stage3ValueSelection(per_dimension=per_dim)


def _stage3_fallback(dim: Dict) -> _Stage3SingleDimOutput:
    """LLM 실패 시 — 첫 1개 + 중간 1개 + 마지막 1개 안전 채택."""
    print(f"  ↳ Stage 3 fallback ({dim['dim_key']}): 안전 3개 Enum 선택")
    enum_full = _enum_id_set(dim)
    base = enum_full[0]
    mid = enum_full[len(enum_full) // 2] if len(enum_full) >= 2 else enum_full[0]
    last = enum_full[-1]
    selected = []
    for cand in (base, mid, last):
        if cand and cand not in selected:
            selected.append(cand)
    while len(selected) < 2 and enum_full:
        for cand in enum_full:
            if cand not in selected:
                selected.append(cand)
                break
        else:
            break
    return _Stage3SingleDimOutput(selected_enum=selected[:4])


# ==============================================
# 9. Stage 4 — Scenario Synthesis (Compat + Narrative LLM)
# ==============================================

def _cartesian_combos(stage3: Stage3ValueSelection) -> List[Dict[str, str]]:
    """Stage3 결과를 Dim×Enum Cartesian 으로 펼침."""
    dim_ids = [pd.dim_key for pd in stage3.per_dimension]
    enum_lists = [list(pd.selected_enum) for pd in stage3.per_dimension]
    combos: List[Dict[str, str]] = []
    for tup in product(*enum_lists):
        combos.append({did: eid for did, eid in zip(dim_ids, tup)})
    return combos


def _apply_compat_rules(
    combos: List[Dict[str, str]],
    template: ScenarioTemplate,
) -> Tuple[List[Dict[str, str]], List[Tuple[Dict[str, str], str]]]:
    """Compatibility Rule Engine — 통과/탈락 분리.

    forbid 정의: 모든 forbid 키의 값이 forbid 리스트 안에 들어있으면 탈락.
    """
    rules = template.compatibility_rules or []
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
    template: ScenarioTemplate,
    validation_feedback: str | None = None,
) -> List[Dict[str, str]]:
    """Compat 통과 조합 중 target_n개 추출 — 다양성/커버리지 기반 선정.

    1) 첫 compat 통과 조합을 baseline anchor 로 둔다.
    2) 이후 조합은 baseline 과 다른 값을 아직 커버하지 못한 Dim 을 우선 보강한다.
    3) 나머지는 값 다양성 + 피드백 힌트 + Farthest-First 순으로 선정한다.
    """
    if len(passed) <= target_n:
        return list(passed)

    feedback_hints = _extract_feedback_value_hints(validation_feedback, stage3)
    dim_keys = [pd.dim_key for pd in stage3.per_dimension]

    def _feedback_score(combo: Dict[str, str]) -> int:
        return sum(
            1
            for dim_key, preferred_values in feedback_hints.items()
            if combo.get(dim_key) in preferred_values
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

    baseline_idx = 0
    baseline_combo = passed[baseline_idx]
    chosen_idx: List[int] = [baseline_idx]

    pool = [i for i in range(len(passed)) if i not in chosen_idx]
    seen_by_dim: Dict[str, set[str]] = {key: set() for key in dim_keys}
    for idx in chosen_idx:
        for key in dim_keys:
            if key in passed[idx]:
                seen_by_dim[key].add(passed[idx][key])

    def _uncovered_contrast_dims() -> set[str]:
        uncovered: set[str] = set()
        for key in dim_keys:
            baseline_value = baseline_combo.get(key)
            if not any(
                val != baseline_value
                for val in seen_by_dim.get(key, set())
            ):
                uncovered.add(key)
        return uncovered

    while len(chosen_idx) < target_n and pool:
        uncovered_contrast = _uncovered_contrast_dims()

        def _candidate_rank(i: int) -> Tuple[int, int, int, int, int]:
            combo = passed[i]
            gain_contrast = sum(
                1
                for key in uncovered_contrast
                if combo.get(key) != baseline_combo.get(key)
            )
            gain_diversity = sum(
                1
                for key in dim_keys
                if len(seen_by_dim.get(key, set())) < 2
                and combo.get(key) not in seen_by_dim.get(key, set())
            )
            d_min = (
                min(_hamming(combo, passed[a]) for a in chosen_idx)
                if chosen_idx
                else 0
            )
            return (
                gain_contrast,
                gain_diversity,
                _feedback_score(combo),
                d_min,
                _hamming(combo, baseline_combo),
            )

        nxt = max(pool, key=_candidate_rank)
        chosen_idx.append(nxt)
        for key in dim_keys:
            if key in passed[nxt]:
                seen_by_dim[key].add(passed[nxt][key])
        pool.remove(nxt)

    return [passed[i] for i in chosen_idx[:target_n]]


def _extract_feedback_value_hints(
    validation_feedback: str | None,
    stage3: Stage3ValueSelection,
) -> Dict[str, set[str]]:
    """경량 검증 피드백 문자열에서 dim_key별 value 힌트를 추출한다.

    - dim_key=value 형태를 우선 탐지
    - selected_enum 값이 전체에서 유일할 때는 value 단독 출현도 힌트로 허용
    """
    if not validation_feedback:
        return {}

    text = validation_feedback
    hints: Dict[str, set[str]] = {}
    enum_freq: Dict[str, int] = {}
    for pd in stage3.per_dimension:
        for value in pd.selected_enum:
            enum_freq[value] = enum_freq.get(value, 0) + 1

    for pd in stage3.per_dimension:
        matched: set[str] = set()
        for value in pd.selected_enum:
            explicit = re.search(
                rf"{re.escape(pd.dim_key)}\s*[:=]\s*{re.escape(value)}",
                text,
            )
            scoped = pd.dim_key in text and value in text
            unique_value_hint = enum_freq.get(value, 0) == 1 and value in text
            if explicit or scoped or unique_value_hint:
                matched.add(value)
        if matched:
            hints[pd.dim_key] = matched
    return hints


STAGE4_SYSTEM = """\
당신은 LNG 멀티시나리오 'Narrative Writer' 입니다.
이미 Compatibility Rule 을 통과한 'Dim 조합' 리스트를 입력받아, 각 조합에 대해
시장 참여자 관점의 시나리오 서사를 작성하십시오.

## 작성 가이드라인 (반드시 준수)
- title (1줄): 시장 참여자 관점의 한 줄 요약. 공백과 문장부호를 포함해 100자 이내. 예: '1개월 내 정상화'.
- description (3~5줄): 각 시나리오의 가정치 조합(주요 Dim 값)을 자연스러운 한국어 문장으로 풀어 서술 + 전개 양상. 공백과 문장부호를 포함해 300~500자. 'A=B' 같은 key=value 표기 금지.
- derivation_rationale: 이 시나리오가 왜 도출되는지 — 어떤 Dim 조합·맥락 단서로부터 왔는지.
- price_direction.jkm / ttf / hh: 7단계(strong_bull|bull|mild_bull|neutral|mild_bear|bear|strong_bear) 중 1개.
- 입력 조합은 항상 dim_key -> value의 flat object(JSON object) 의미로 해석.
## Price Benchmark 해석 가이드

price_direction은 Base Event와 Dim 조합이 각 가격 지표에 미치는 상대적 방향성과 강도를 판단한다.
세 지표는 동일한 글로벌 LNG 이벤트에 노출되더라도 시장 구조가 다르므로, 특별한 근거 없이 동일한 방향/강도로 설정하지 않는다.

### JKM
- 동북아 LNG 현물 가격 benchmark로, 일본·한국·중국·대만향 LNG cargo 수급을 반영한다.
- 해상 운송 차질, 중동/카타르 LNG 물동량 리스크, spot cargo 경쟁, 아시아 구매자 재고 수준에 민감하다.
- 호르무즈 해협 긴장, LNG 선박 우회, 물류 지연, 아시아 재고 부족은 JKM에 bullish 요인이다.
- 아시아 재고가 높거나 수요가 약하거나 대체 공급이 충분하면 상승 강도는 제한된다.

### TTF
- 유럽 천연가스 허브 가격 benchmark로, LNG 유입, 파이프라인 공급, 저장 재고, 계절 수요의 영향을 함께 받는다.
- 글로벌 LNG cargo 경쟁이 심화되면 TTF도 상승 압력을 받지만, 유럽 재고 수준이 높으면 완충된다.
- 유럽 저장 재고가 낮고 LNG 유입 차질이 예상되면 bullish 강도가 커진다.
- 재고가 높거나 파이프라인 공급이 안정적이면 JKM보다 반응 강도가 낮을 수 있다.

### HH
- 미국 Henry Hub 천연가스 가격 benchmark로, 미국 내 생산량, 재고, 날씨, 전력 수요, LNG export feedgas 수요가 핵심 변수다.
- 호르무즈 해협 리스크의 직접 영향은 JKM/TTF보다 약하다.
- 글로벌 LNG 가격 상승이 미국 LNG 수출 가동률 증가 또는 feedgas 수요 증가로 연결될 때 HH에 bullish 압력이 생긴다.
- 미국 내 재고가 높거나 생산 증가가 충분하면 HH는 neutral 또는 mild_bull에 그칠 수 있다.

## 방향성 판단 원칙
- 호르무즈/중동 해상 물류 리스크는 일반적으로 JKM이 가장 직접적으로 반응하고, TTF는 LNG cargo 경쟁을 통해 간접 반응하며, HH는 미국 LNG 수출 수요를 통해 가장 간접적으로 반응한다.
- 따라서 기본 민감도는 대체로 JKM > TTF > HH 순서로 보되, storage_level, period, utilization_change_direction 조합에 따라 강도를 조정한다.
- 같은 방향일 수는 있지만, 특별한 근거 없이 JKM/TTF/HH를 모두 동일 enum으로 설정하지 않는다.
- HH는 글로벌 LNG 이벤트만으로 strong_bull 또는 bull을 부여하지 말고, 미국 내 수급 타이트화 또는 LNG export feedgas 증가 근거가 있을 때만 상승 강도를 높인다.

## 형식 예시
- 올바른 형식 예시: {"period":"3개월","utilization_change_direction":"감소"}
- 금지 형식 예시: [{"dim_key":"period","value":"3개월"}], [{"dimension_id":"period","value":"3개월"}]

## 절대 금지
- '결과(가격 방향)가 동일하므로 두 조합을 합쳐서 1개로 만든다' 같은 통합/생략 행위.
  → 입력으로 들어온 조합 개수와 출력 narratives 개수는 **반드시 일치**.
- title·description 안에 '분기기준=값', 'dim_key=값', '항목명=값', '항목: 값' 같은
  key=value/표·코드 형태의 표기를 노출하는 것.
  → 분기 기준 값은 반드시 자연스러운 한국어 문장으로 녹여 서술한다.
    (예: '기간=3개월' (X) → '기간은 3개월이며' (O) / 'utilization_change_direction=증가' (X)
     → 'Cameron LNG 가동률은 증가하며' (O))
  → 입력 조합의 dim_key 나 등호(=)를 결과 문장에 그대로 드러내지 마십시오.

## 최종 검증에서 반드시 통과해야 할 조건
- (R03) 각 시나리오의 Dim 값 조합이 물리적·논리적으로 모순 없이 양립해야 함.
  → Compat Rule 필터 외에도, 개별 시나리오 서술이 조합 의도를 명확히 설명해야 함.
  → '이런 상황에서 이 값이 어떻게 나타나는가'를 description 에 명시하면 모순 판정 방지.
- (R04) 모든 시나리오의 dimension_values 조합(dim_key → value 집합)이 서로 유일해야 함.
  → 동일한 Dim 조합을 가진 두 시나리오가 존재하면 MECE 위반으로 탈락.
"""

STAGE4_HARD = """\
[중요한 출력 제약 — Stage 4]
- narratives 길이는 입력 조합 수와 정확히 일치.
- price_direction.jkm / ttf / hh 는 반드시 7단계 enum 중 정확히 1개.
- title 은 1줄이며, 공백과 문장부호를 포함해 100자 이내.
- description 은 3~5줄이며, 공백과 문장부호를 포함해 300~500자.
- '결과 동일 조합 통합' 금지 — 출력 길이를 줄이지 마십시오.
- 입력 조합을 ARRAY 형태로 재해석/치환하지 마십시오(항상 flat object 가정).
- 입력 조합의 key 집합은 selected dim_key 와 정확히 일치해야 함(누락/여분 금지).
- title·description 에 'key=value' / '항목명=값' / 표·코드 형태의 나열식 표기 금지.
  분기 기준 값은 자연어 문장으로만 서술하며 등호(=)·dim_key 를 노출하지 마십시오.
"""


@log_tool
def stage4_synthesize_scenarios(
    pack: Stage1ContextPack,
    stage3: Stage3ValueSelection,
    template: ScenarioTemplate,
    validation_feedback: str | None = None,
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

    target = _select_target_combos(
        passed,
        stage3,
        REF_TARGET_SCENARIOS,
        template,
        validation_feedback=validation_feedback,
    )
    if not target:
        print("  ↳ 경고: Compat 통과 조합 0건 — Cartesian 전체 중 1건 강제 채택.")
        target = combos_all[:1] or [{}]

    dim_idx = _dim_index(template)
    dim_label_block = "\n".join(
        f"- {pd.dim_key} ({dim_idx.get(pd.dim_key, {}).get('label_ko', '')})"
        for pd in stage3.per_dimension
    )
    combos_block = "\n".join(
        f"  [{i+1}] " + ", ".join(f"{k}={v}" for k, v in combo.items())
        for i, combo in enumerate(target)
    )

    feedback_block = (
        f"\n[이전 출력에 대한 자동 규칙 검증 피드백 — 아래 항목을 모두 반영해 전체 narratives를 다시 작성하십시오]\n{validation_feedback}\n"
        if validation_feedback
        else ""
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
- 각 narrative 의 title 은 한 줄이며, 공백과 문장부호를 포함해 100자 이내.
- 각 narrative 의 description 은 3~5줄이며, 공백과 문장부호를 포함해 300~500자.
{feedback_block}"""

    def _validate(out: _Stage4LLMOutput) -> None:
        if len(out.narratives) != len(target):
            raise ValueError(
                f"narratives 길이 불일치: {len(out.narratives)} != {len(target)}"
            )
        for n in out.narratives:
            for v in (
                n.price_direction.jkm,
                n.price_direction.ttf,
                n.price_direction.hh,
            ):
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
        scenarios.append(
            Scenario(
                scenario_id=f"S_{i:02d}",
                title=narr.title,
                dimension_values=combo,
                description=narr.description,
                derivation_rationale=narr.derivation_rationale,
                price_direction=narr.price_direction,
                compatibility_passed=True,
            )
        )

    return Stage4ScenarioSynthesis(
        cartesian_total=len(combos_all),
        filtered_by_compatibility=len(passed),
        scenarios=scenarios,
    )


def _stage4_fallback(target: List[DimensionValueMap]) -> _Stage4LLMOutput:
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
            price_direction=PriceDirection(jkm="neutral", ttf="neutral", hh="neutral"),
        )
        for i, combo in enumerate(target)
    ]
    return _Stage4LLMOutput(narratives=narratives)


@log_tool
def stage4_synthesize_fixed_scenarios(
    pack: Stage1ContextPack,
    dimension_values_list: List[DimensionValueMap],
    llm_client=None,
) -> Stage4ScenarioSynthesis:
    """Generate narratives for caller-provided Dim combinations without reselecting them."""
    target = [
        {str(key): str(value) for key, value in values.items()}
        for values in dimension_values_list
    ]
    if not target:
        raise ValueError("dimension_values_list is required")

    dim_keys = sorted({key for values in target for key in values})
    dim_label_block = "\n".join(f"- {key}" for key in dim_keys)
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

## 작성 대상 조합 ({len(target)}개) — 입력 순서를 그대로 유지하여 narratives 출력
{combos_block}

## 산출 규칙
- narratives 길이 = {len(target)}.
- 각 narrative 의 title 은 한 줄이며, 공백과 문장부호를 포함해 100자 이내.
- 각 narrative 의 description 은 3~5줄이며, 공백과 문장부호를 포함해 300~500자.
"""

    def _validate(out: _Stage4LLMOutput) -> None:
        if len(out.narratives) != len(target):
            raise ValueError(
                f"narratives 길이 불일치: {len(out.narratives)} != {len(target)}"
            )
        for n in out.narratives:
            for v in (n.price_direction.jkm, n.price_direction.ttf, n.price_direction.hh):
                if v not in PRICE_TIERS:
                    raise ValueError(f"price_direction 범위 밖 값: {v}")

    out = _invoke_with_retry(
        stage_label="Stage 4 fixed",
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
        cartesian_total=len(target),
        filtered_by_compatibility=len(target),
        scenarios=scenarios,
    )


# ==============================================
# 10. Scenario Group Metadata (LLM)
# ==============================================

SCENARIO_GROUP_METADATA_SYSTEM = """\
당신은 LNG 멀티시나리오 결과를 사용자 화면에 표시할 'Scenario Group Metadata Writer' 입니다.
Base Event와 생성된 시나리오 목록을 입력받아 시나리오 그룹명과 그룹 설명을 작성하십시오.
"""

SCENARIO_GROUP_METADATA_RULES = """\
[중요한 출력 제약 — Scenario Group Metadata]
- title 은 공백과 문장부호를 포함해 100자 이내.
- description 은 공백과 문장부호를 포함해 300~400자.
- description은 기존 detail_analysis를 그대로 복사하지 말고, 시나리오 그룹의 목적과 주요 분기 축을 압축 요약하십시오.
- 새 수치나 근거 없는 사실을 만들지 마십시오.
"""


@log_tool
def stage_generate_scenario_group_metadata(
    pack: Stage1ContextPack,
    event: Dict,
    stage4: Stage4ScenarioSynthesis,
    llm_client=None,
) -> ScenarioGroupMetadata:
    """Generate scenario group title/description for UI display."""
    detail_excerpt = _shorten(event.get("detail_analysis", ""), 1200)
    scenarios_block = "\n".join(
        f"- {scenario.scenario_id}: {scenario.title} | "
        f"dims={', '.join(f'{key}={value}' for key, value in scenario.dimension_values.items())}"
        for scenario in stage4.scenarios
    )
    user_prompt = f"""\
## Base Event
- title: {pack.C1_base_event.title}
- summary: {pack.C1_base_event.summary}
- driver: {pack.C1_base_event.driver}
- detail_analysis(참고용 발췌): {detail_excerpt}

## 생성된 시나리오 목록 ({len(stage4.scenarios)}건)
{scenarios_block}
"""

    out = _invoke_with_retry(
        stage_label="Scenario Group Metadata",
        schema_cls=_ScenarioGroupMetadataOutput,
        system_prompt=SCENARIO_GROUP_METADATA_SYSTEM,
        user_prompt=user_prompt,
        validate_fn=None,
        hard_constraints=SCENARIO_GROUP_METADATA_RULES,
    )

    if out is None:
        return ScenarioGroupMetadata(
            title=pack.C1_base_event.title or f"Scenario group {pack.C1_base_event.event_id}",
            description=pack.C1_base_event.summary or "",
        )

    return ScenarioGroupMetadata(title=out.title, description=out.description)


# ==============================================
# 11. Stage 5 — Validation (MECE + Likelihood LLM)
# ==============================================

STAGE5_SYSTEM = """\
당신은 멀티시나리오 'MECE Validator + Likelihood Calibrator' 입니다.

## 검사 항목 (반드시 이 둘만)
1. mutually_exclusive (M): 동일 시점에 정확히 한 시나리오만 참이 될 수 있는가?
   - 본 파이프라인의 시나리오는 모두 (dim_key → value) 단일 조합으로 정의됨.
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
- 시설 영구 손상·전면 봉쇄 등 발생 가능성이 낮은 강한 충격 조합은 통상 'low' 또는 'very_low'.
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
        f"    price: jkm={s.price_direction.jkm}, ttf={s.price_direction.ttf}, hh={s.price_direction.hh}"
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


# ==============================================
# 11. Stage 6 — Quick Validation (LLM 1회 경량 검증)
# ==============================================

STAGE6_SYSTEM = """\
당신은 LNG 멀티시나리오의 'Quick Validator' 입니다.
생성된 시나리오 세트가 4가지 핵심 검증 기준을 통과하는지 1회 판정하십시오.

## 검사 항목

### R03 — 조합 호환성
각 시나리오의 Dimension 값 조합이 물리적·논리적으로 모순 없이 양립해야 함.
→ 명백한 모순(동시 성립 불가)이 있는 시나리오가 1개 이상이면 passed=false.
→ 단지 드물거나 극단적인 조합이라는 이유만으로 false 를 반환하지 않음.

### R04 — MECE(조합 유일성)
모든 시나리오의 dimension_values 조합(dim_key → value 집합)이 서로 유일해야 함.
→ 완전히 동일한 조합을 가진 시나리오 쌍이 있으면 passed=false.

## 이미 코드로 결정론적 검증된 항목
- R01 baseline contrast coverage 와 R02 값 다양성은 LLM 호출 전에 코드로 검사한다.
- baseline 대비 대안값 coverage 여부를 다시 판정하거나 실패 사유로 언급하지 마십시오.

## 출력 규칙
- passed=true: 위 2가지 모두 통과. issues=[], improvement_suggestions="".
- passed=false: 실패 항목별로 issues 에 한국어 1줄씩 기술.
  improvement_suggestions: Stage 4 재생성 시 반드시 따라야 할 구체적 지시.
  → 어떤 Dim 에서 어떤 값을 변경/추가/제거해야 하는지 dim_key·value 명시.
  → 단순 나열이 아닌, 재생성에 바로 활용 가능한 지시 형태로 작성.
"""


class _Stage6LLMOutput(BaseModel):
    passed: bool
    issues: List[str] = Field(default_factory=list)
    improvement_suggestions: str = Field(default="")


def _missing_baseline_contrast_coverage(
    stage3: Stage3ValueSelection,
    stage4: Stage4ScenarioSynthesis,
    template: ScenarioTemplate,
) -> list[tuple[str, str]]:
    """Return selected dimensions without non-baseline values in the scenario set."""
    result = check_baseline_contrast_coverage(
        stage4.scenarios,
        [pd.dim_key for pd in stage3.per_dimension],
        baseline_index=0,
    )
    baseline_values = result.baseline_values
    return [
        (dim_key, str(baseline_values.get(dim_key)))
        for dim_key in result.missing_dimensions
    ]


@log_tool
def stage6_quick_validate(
    pack: Stage1ContextPack,
    stage3: Stage3ValueSelection,
    stage4: Stage4ScenarioSynthesis,
    template: ScenarioTemplate,
) -> tuple[bool, str | None]:
    """Stage 6 진입점 — LLM 1회 경량 검증.

    반환: (passed, improvement_suggestions)
    - passed=True  → (True, None)
    - passed=False → (False, "<피드백 문자열>")
    """
    selected_dim_keys = [pd.dim_key for pd in stage3.per_dimension]
    contrast = check_baseline_contrast_coverage(
        stage4.scenarios,
        selected_dim_keys,
        baseline_index=0,
    )
    if contrast.baseline_issue or contrast.missing_dimensions:
        missing = contrast.missing_dimensions
        issues = "\n".join(
            f"- R01 baseline 대비 대안값 누락: {dim_key} "
            f"(baseline={contrast.baseline_values.get(dim_key)})"
            for dim_key in missing
        )
        suggestions = "; ".join(
            f"{dim_key} 값이 baseline '{contrast.baseline_values.get(dim_key)}'와 다른 조합을 최소 1개 포함"
            for dim_key in missing
        )
        return (
            False,
            "[검증 실패/ 재생성 필요]\n"
            f"{issues or contrast.baseline_issue}\n\n"
            "[개선 지시]\n"
            f"{suggestions}하도록 Stage 4 조합을 재선정하십시오.",
        )

    # Dim별 선택 값 목록
    dim_idx = _dim_index(template)
    dimension_block_lines: List[str] = []
    for pd in stage3.per_dimension:
        dim = dim_idx.get(pd.dim_key, {})
        dimension_block_lines.append(
            f"- {pd.dim_key} ({dim.get('label_ko', '')}): "
            f"전체 enum={pd.template_enum_full}, "
            f"선택된 enum={pd.selected_enum}, "
            f"baseline={contrast.baseline_values.get(pd.dim_key)}, "
            f"대안값={sorted(contrast.observed_non_baseline_values.get(pd.dim_key, set()))}"
        )

    # 시나리오 목록
    scenario_lines: List[str] = []
    for s in stage4.scenarios:
        dim_vals = ", ".join(f"{k}={v}" for k, v in s.dimension_values.items())
        scenario_lines.append(
            f"- {s.scenario_id} [{s.title}]\n"
            f"  dimension_values: {dim_vals}\n"
            f"  description: {_shorten(s.description, 200)}"
        )

    user_prompt = f"""\
## Base Event 요약
- title: {pack.C1_base_event.title}
- summary: {pack.C1_base_event.summary}

## 선택된 Dimension 및 Enum 정보
{chr(10).join(dimension_block_lines)}

## 생성된 시나리오 ({len(stage4.scenarios)}건)
{chr(10).join(scenario_lines)}

## 판정 요청
R01 baseline contrast coverage 와 R02 값 다양성은 이미 코드로 통과했습니다.
위 2가지 검사 항목(R03 조합 호환성, R04 MECE)을 적용하여 passed 여부를 결정하십시오.
passed=false 인 경우, improvement_suggestions 에 Stage 4 재생성을 위한 구체적 지시를 작성하십시오.
"""

    out = _invoke_with_retry(
        stage_label="Stage 6",
        schema_cls=_Stage6LLMOutput,
        system_prompt=STAGE6_SYSTEM,
        user_prompt=user_prompt,
        validate_fn=None,
        hard_constraints="",
    )

    if out is None:
        print("  ↳ Stage 6 fallback: LLM 호출 실패 — 검증 통과로 처리")
        return True, None

    if out.passed:
        return True, None

    issues_text = "\n".join(f"- {issue}" for issue in out.issues) if out.issues else "(상세 없음)"
    feedback = f"[검증 실패/ 재생성 필요]\n{issues_text}\n\n[개선 지시]\n{out.improvement_suggestions}"
    return False, feedback
