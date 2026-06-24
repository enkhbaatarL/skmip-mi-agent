"""
Signpost Generation Pipeline Stages

Proper implementation of the signpost generation pipeline (Stages 2~5)
with proper LLM client injection support using the project's invoke_llm_structured_output.

Reference: ./tmp/stage_integrated_signpost_openai.py
"""
from __future__ import annotations

import asyncio
import os
import random
import re
from typing import Any, Dict, List, Literal, Tuple

from pydantic import BaseModel, Field, conlist, model_validator

from apps.agents.scenario_group_agent.schemas.graph.generation import GeneratedSignpost
from apps.agents.scenario_group_agent.schemas.enums import (
    DirectionCode,
    SignpostStrength,
)
from apps.common.logging.logger_config import logger as app_logger
from apps.connectors.llm.llm_client import invoke_llm_structured_output


# ==============================================
# 1. Constants (from environment)
# ==============================================

# Signpost count per scenario
REF_SIGNPOSTS_PER_SCENARIO_MIN: int = int(os.getenv("REF_SIGNPOSTS_PER_SCENARIO_MIN", "3"))
REF_SIGNPOSTS_PER_SCENARIO_MAX: int = int(os.getenv("REF_SIGNPOSTS_PER_SCENARIO_MAX", "6"))

# Stage 4 strength quotas
REF_STRONG_QUOTA_MIN: int = int(os.getenv("REF_STRONG_QUOTA_MIN", "1"))
REF_STRONG_QUOTA_MAX: int = int(os.getenv("REF_STRONG_QUOTA_MAX", "3"))
REF_EARLY_QUOTA_MIN: int = int(os.getenv("REF_EARLY_QUOTA_MIN", "1"))
REF_EARLY_QUOTA_MAX: int = int(os.getenv("REF_EARLY_QUOTA_MAX", "3"))

# Stage 5 keyword length
KEYWORD_HINTS_MIN: int = 3
KEYWORD_HINTS_MAX: int = 5

# Retry
REF_MAX_RETRIES: int = int(os.getenv("REF_MAX_RETRIES", "5"))

# Type aliases
SignpostClass = Literal["observation"]
SignpostSource = Literal["mi_record"]
Direction = Literal["SUP", "REF"]
Strength = SignpostStrength


# ==============================================
# 2. LLM Output Models
# ==============================================

class _Stage2Candidate(BaseModel):
    label_ko: str = Field(description="관측 가능한 신호 한 줄 (한국어).")
    passes_filter: bool = Field(
        description="3-필터 (소스 가용성 / Binary / 시나리오 결합도) 통과 여부.",
    )
    filter_reason: str = Field(
        default="",
        description="통과/탈락 사유 한국어 1줄. 통과 시도 사유를 명기.",
    )


class _Stage2LLMOutput(BaseModel):
    candidates: conlist(_Stage2Candidate, min_length=5, max_length=10) = Field(  # type: ignore[valid-type]
        description=(
            "Observability 후보 5~10개. 그 중 passes_filter=True 가 "
            f"{REF_SIGNPOSTS_PER_SCENARIO_MIN}~{REF_SIGNPOSTS_PER_SCENARIO_MAX}개 이어야 함."
        ),
    )

    @model_validator(mode="after")
    def _validate_unique_labels(self):
        seen: set = set()
        for c in self.candidates:
            key = c.label_ko.strip()
            if not key:
                raise ValueError("label_ko 가 빈 문자열인 후보 존재.")
            if key in seen:
                raise ValueError(f"label_ko 중복: '{key}'")
            seen.add(key)
        return self


class _Stage4Assignment(BaseModel):
    label_ko: str = Field(description="입력 signpost 의 label_ko (echo).")
    strength: Strength = Field(
        description="SignpostStrength enum 값 (VERYSTRONG/STRONG/MEDIUM/WEAK/VERYWEAK)."
    )
    rationale_ko: str = Field(
        description="이 strength 부여 + 시나리오 검증 측면의 한국어 1~2줄 근거.",
    )


class _Stage4LLMOutput(BaseModel):
    assignments: List[_Stage4Assignment] = Field(
        description="입력 signpost 수와 동일 길이 + label_ko 순서 일치.",
    )


class _Stage5Hint(BaseModel):
    label_ko: str = Field(description="입력 signpost 의 label_ko (echo).")
    keyword_hints: conlist(str, min_length=KEYWORD_HINTS_MIN, max_length=KEYWORD_HINTS_MAX) = Field(  # type: ignore[valid-type]
        description="3~5개 키워드. 고유명사 + 동사/상태어 혼합 권장.",
    )


class _Stage5LLMOutput(BaseModel):
    hints: List[_Stage5Hint] = Field(
        description="입력 signpost 수와 동일 길이 + label_ko 순서 일치.",
    )


# ==============================================
# 3. LLM Infrastructure
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


async def _invoke_structured(
    schema_cls: type[BaseModel],
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
) -> BaseModel | None:
    """Async structured output LLM call via the project's invoke_llm_structured_output connector."""
    result = await invoke_llm_structured_output(
        output_schema=schema_cls,
        messages=messages,
        temperature=temperature,
        max_retries=2,
    )
    return result.result


async def _invoke_with_retry(
    stage_label: str,
    schema_cls: type[BaseModel],
    system_prompt: str,
    user_prompt: str,
    validate_fn,
    hard_constraints: str = "",
    temperature: float = 0.0,
) -> BaseModel | None:
    """LLM 호출 with retry + validation + fallback.

    Returns parsed Pydantic model on success, None on all retries exhausted.
    """
    last_exc: Exception | None = None
    last_validation_exc: Exception | None = None
    accumulated_hint = hard_constraints

    for attempt in range(1, REF_MAX_RETRIES + 1):
        try:
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
            result = await _invoke_structured(schema_cls, messages, temperature=temperature)
            if result is None:
                raise ValueError("LLM returned None result")
            validate_fn(result)
            return result

        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            is_api = _is_retryable_api_error(exc)
            is_schema = _is_retryable_schema_error(exc)
            is_validation = isinstance(exc, (ValueError, TypeError))
            should_retry = (is_api or is_schema or is_validation) and attempt < REF_MAX_RETRIES

            if not should_retry:
                app_logger.warning(
                    "[{}] 재시도 불가 — {}: {}",
                    stage_label,
                    exc.__class__.__name__,
                    str(exc)[:160],
                )
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
            app_logger.info("[{}] 재시도 ({}/{}) — {}, {:.1f}s 후", stage_label, attempt, REF_MAX_RETRIES, reason, wait_sec)
            await asyncio.sleep(wait_sec)

    app_logger.warning("[{}] 재시도 소진 — fallback 진입", stage_label)
    return None


# ==============================================
# 4. Stage 2 — Observability Filter
# ==============================================

STAGE2_SYSTEM = """\
당신은 LNG 멀티시나리오 'Observability Filter' 입니다.
입력으로 시나리오 1건의 가정치 조합(dimension_values + 서술)을 받아, **이 시나리오가
참이라면 향후 관측 가능한 신호** 후보를 생성한 뒤, 아래 3개 필터로 self-filter 하십시오.

## 후보 생성 가이드 (5~10개)
- 각 후보는 한국어 한 줄로 작성 (예: 'Ras Laffan 재가동 공식 발표').
- 고유명사(시설/기관/지명) 1개 이상 + 동사·상태어 1개 이상 포함.
- '관측 가능한 사실 명제' 여야 함. 의견/감정/모호 표현 금지.

## 3-필터 (모두 통과해야 passes_filter=True)
1. 소스 가용성: Reuters / Platts / Bloomberg / WSJ / FT 등 주요 매체 또는 정부·기관
   공식 채널에서 보도될 가능성이 높아야 함.
2. Binary 판정: 모호한 해석 없이 '관측됨 / 미관측'을 결정 가능해야 함.
   ('분위기', '전망', '기대감' 류 모호어는 탈락)
3. 시나리오 결합도: 일반 뉴스가 아니라 입력된 시나리오 가정치(특정 지명/봉쇄 단계/
   리스크 프리미엄 수준 등)와 직접 연결되어야 함.

## passes_filter=True 후보 수 — **시나리오 결합도에 비례**
- 허용 범위: {min_n}~{max_n} 개.
- **MAX 를 채우는 것이 목표가 아닙니다.** 시나리오 가정치(dimension_values)와
  직접 연결되는 결합도 높은 후보가 적다면 MIN({min_n})만 통과시키고, 가정치 조합이
  풍부해 강한 결합 후보가 많다면 MAX({max_n})까지 통과시키세요.
- 즉 시나리오마다 통과 수가 달라지는 것이 정상이며 자연스러운 결과입니다.
- 결합도가 불확실하거나 '일반 뉴스'에 가까운 후보는 통과 0표 처리하세요.

## filter_reason
- 통과 시: '소스 가용성+Binary+결합도 모두 충족' 식으로 간결히.
- 탈락 시: 어느 필터에서 탈락했는지(예: 'Binary 판정 불가 — 분위기 표현') 명기.
"""

STAGE2_HARD = """\
[중요한 출력 제약 — Stage 2]
- candidates 길이는 5~10.
- passes_filter=True 후보의 수는 반드시 {min_n}~{max_n} 사이.
- MAX({max_n}) 채우기를 목표로 삼지 말 것. 시나리오 결합도가 높은 후보가 적다면
  MIN({min_n})만 통과시키는 것이 정답.
- 모든 label_ko 는 서로 달라야 함 (중복 금지).
- 'observation' class 만 생성. 의견/감정/모호 표현 금지.
"""


def _shorten(text: str, n: int) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n] + " …(생략)"


async def stage2_observability_filter(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
) -> List[str]:
    """Stage 2 진입점 — 시나리오 1건 → 통과 label_ko 리스트 반환."""
    scenario_id = scenario.get("scenario_id", "S_??")

    base_payload = {
        "base_title": base_event_summary.get("title", ""),
        "base_summary": base_event_summary.get("summary", ""),
        "base_driver": base_event_summary.get("driver", ""),
        "scenario_id": scenario_id,
        "scenario_title": scenario.get("title", ""),
        "scenario_description": _shorten(scenario.get("description", ""), 600),
        "dim_values_block": ", ".join(
            f"{k}={v}" for k, v in (scenario.get("dimension_values") or {}).items()
        ) or "(없음)",
        "price_block": ", ".join(
            f"{k}={v}" for k, v in (scenario.get("price_direction") or {}).items()
        ) or "(없음)",
        "min_n": REF_SIGNPOSTS_PER_SCENARIO_MIN,
        "max_n": REF_SIGNPOSTS_PER_SCENARIO_MAX,
    }

    user_prompt = f"""\
## Base Event 요약
- title: {base_payload['base_title']}
- summary: {base_payload['base_summary']}
- driver: {base_payload['base_driver']}

## 대상 시나리오
- scenario_id: {base_payload['scenario_id']}
- title: {base_payload['scenario_title']}
- description: {base_payload['scenario_description']}
- dimension_values: {base_payload['dim_values_block']}
- price_direction: {base_payload['price_block']}

## 산출
- candidates: 5~10개 (각 label_ko + passes_filter + filter_reason).
- 통과 후보 수: {base_payload['min_n']}~{base_payload['max_n']} 개. **MAX 를 채우지 말 것** — 결합도 강한 만큼만 통과.
"""

    hard = STAGE2_HARD.format(
        min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
        max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
    )

    def _validate(out: _Stage2LLMOutput) -> None:
        passing = [c for c in out.candidates if c.passes_filter]
        if not (REF_SIGNPOSTS_PER_SCENARIO_MIN <= len(passing) <= REF_SIGNPOSTS_PER_SCENARIO_MAX):
            raise ValueError(
                f"통과 후보 수 {len(passing)} 이 허용 범위 "
                f"[{REF_SIGNPOSTS_PER_SCENARIO_MIN}, {REF_SIGNPOSTS_PER_SCENARIO_MAX}] 밖."
            )

    out = await _invoke_with_retry(
        stage_label="Stage 2",
        schema_cls=_Stage2LLMOutput,
        system_prompt=STAGE2_SYSTEM,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=hard,
    )

    if out is None:
        labels = _stage2_fallback(scenario)
        app_logger.info("[{}] Stage 2 fallback labels={}", scenario_id, len(labels))
        return labels

    passing = [c for c in out.candidates if c.passes_filter]
    passing = passing[:REF_SIGNPOSTS_PER_SCENARIO_MAX]
    app_logger.info(
        "[{}] Stage 2 candidates={} passed={}",
        scenario_id,
        len(out.candidates),
        len(passing),
    )
    return [c.label_ko.strip() for c in passing]


def _stage2_fallback(scenario: Dict[str, Any]) -> List[str]:
    """LLM 실패 시 — 시나리오 description / dimension_values 키워드로 안전 라벨 생성."""
    sid = scenario.get("scenario_id", "S_??")
    dims = scenario.get("dimension_values") or {}
    dim_pairs = [(k, v) for k, v in dims.items()]
    base = (scenario.get("title") or "").strip() or "시나리오 관측 신호"

    fallbacks = [
        f"{base} — 관련 공식 발표 보도 ({sid})",
        f"{base} — 주요 매체의 가격 영향 분석 보도 ({sid})",
    ]
    for k, v in dim_pairs[:2]:
        fallbacks.append(f"{base} — {k}={v} 공식 확인 보도")

    seen: set = set()
    out: List[str] = []
    for lbl in fallbacks:
        if lbl in seen:
            continue
        seen.add(lbl)
        out.append(lbl)
        if len(out) >= REF_SIGNPOSTS_PER_SCENARIO_MAX:
            break
    while len(out) < REF_SIGNPOSTS_PER_SCENARIO_MIN:
        out.append(f"{base} — 추가 관측 #{len(out)+1}")
    return out


# ==============================================
# 5. Stage 3 — Axis Classifier (deterministic)
# ==============================================

def stage3_assign_axes() -> Dict[str, Any]:
    """단일 label에 대한 Axis 부여. Phase1: 무조건 mi_record / actor_nature=None."""
    return {
        "signpost_source": "mi_record",
    }


# ==============================================
# 6. Stage 4 — Direction & Strength Assignment
# ==============================================

STAGE4_SYSTEM = """\
당신은 LNG 멀티시나리오 'Direction & Strength Assignment' 입니다.
입력으로 시나리오 1건과 그에 귀속된 Signpost label 리스트(이미 Stage2 통과)
를 받습니다. **direction 은 'SUP' 로 이미 고정**되었으므로 결정/출력하지 않습니다.

## 당신이 결정할 것 (signpost 별로)
{stage4_strength_guide}
2. rationale_ko : 위 strength 부여 근거 + 이 signpost 가 시나리오를 어떻게
   검증/보강하는지 한국어 1~2줄.

## 역할 쿼터 (반드시 준수)
- 입력 signpost 가 N 개(=3~6)일 때, 다음을 모두 만족해야 함:
  - REALIZED_BUCKET(VERYSTRONG+STRONG) 개수 ∈ [{strong_min}, {strong_max}]
  - EARLY_BUCKET(MEDIUM+WEAK+VERYWEAK) 개수 ∈ [{early_min}, {early_max}]
- 위 폭 내에서 **시나리오 확정성에 비례해 분포가 달라지는 것이 정상**:
  - tail-risk/극단 시나리오 → STRONG 비중을 키우고 EARLY 작게.
  - 단기/완화 시나리오    → STRONG 작게, EARLY(MED/WEAK) 비중 크게.
- 모두 STRONG 또는 모두 MEDIUM 같은 편향 출력은 여전히 금지.

## 절대 금지
- direction / weight / role_tag 출력 금지 (downstream 에서 자동 부여).
- STRONG 을 {strong_max} 개 초과 부여 금지.
- EARLY(MED+WEAK) 를 {early_max} 개 초과 부여 금지.
"""

STAGE4_HARD = """\
[중요한 출력 제약 — Stage 4]
- assignments 길이는 입력 signpost 수와 정확히 일치.
- 각 항목의 label_ko 는 입력 label 과 정확히 일치 (echo).
- strength 는 SignpostStrength enum 값 중 정확히 1개.
- 쿼터: (VERYSTRONG∪STRONG) {strong_min}~{strong_max} + (MEDIUM∪WEAK∪VERYWEAK) {early_min}~{early_max}. 위반 시 재시도.
"""


async def stage4_assign_direction_strength(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    labels: List[str],
) -> List[Dict[str, str]]:
    """Stage 4 진입점 — labels → [{label_ko, strength, rationale_ko}, ...]."""
    scenario_id = scenario.get("scenario_id", "S_??")
    if not labels:
        return []

    signpost_block = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(labels))

    user_prompt = f"""\
## Base Event 요약
- title: {base_event_summary.get('title', '')}
- summary: {base_event_summary.get('summary', '')}

## 대상 시나리오
- scenario_id: {scenario_id}
- title: {scenario.get('title', '')}
- description: {_shorten(scenario.get('description', ''), 600)}
- dimension_values: {', '.join(f"{k}={v}" for k, v in (scenario.get('dimension_values') or {}).items()) or '(없음)'}

## 입력 Signpost ({len(labels)}개)
{signpost_block}

## 산출
- assignments 길이 = {len(labels)}, label_ko 순서 유지.
- 각 항목에 strength + rationale_ko (1~2줄).
"""

    label_set = [lbl.strip() for lbl in labels]
    hard = STAGE4_HARD.format(
        strong_min=REF_STRONG_QUOTA_MIN,
        strong_max=REF_STRONG_QUOTA_MAX,
        early_min=REF_EARLY_QUOTA_MIN,
        early_max=REF_EARLY_QUOTA_MAX,
    )

    def _validate(out: _Stage4LLMOutput) -> None:
        if len(out.assignments) != len(labels):
            raise ValueError(
                f"assignments 길이 불일치: {len(out.assignments)} != {len(labels)}"
            )
        out_labels = [a.label_ko.strip() for a in out.assignments]
        if out_labels != label_set:
            raise ValueError(
                "assignments 의 label_ko 순서가 입력과 다름. "
                f"expected={label_set}, got={out_labels}"
            )
        n_strong = sum(
            1
            for a in out.assignments
            if a.strength in (SignpostStrength.VERYSTRONG, SignpostStrength.STRONG)
        )
        n_early = sum(
            1
            for a in out.assignments
            if a.strength
            in (
                SignpostStrength.MEDIUM,
                SignpostStrength.WEAK,
                SignpostStrength.VERYWEAK,
            )
        )
        if not (REF_STRONG_QUOTA_MIN <= n_strong <= REF_STRONG_QUOTA_MAX):
            raise ValueError(
                f"STRONG 쿼터 위반: {n_strong} "
                f"(허용 {REF_STRONG_QUOTA_MIN}~{REF_STRONG_QUOTA_MAX})"
            )
        if not (REF_EARLY_QUOTA_MIN <= n_early <= REF_EARLY_QUOTA_MAX):
            raise ValueError(
                f"MEDIUM+WEAK 쿼터 위반: {n_early} "
                f"(허용 {REF_EARLY_QUOTA_MIN}~{REF_EARLY_QUOTA_MAX})"
            )

    out = await _invoke_with_retry(
        stage_label="Stage 4",
        schema_cls=_Stage4LLMOutput,
        system_prompt=STAGE4_SYSTEM.format(
            stage4_strength_guide=SignpostStrength.stage4_prompt_guide_text(),
            strong_min=REF_STRONG_QUOTA_MIN,
            strong_max=REF_STRONG_QUOTA_MAX,
            early_min=REF_EARLY_QUOTA_MIN,
            early_max=REF_EARLY_QUOTA_MAX,
        ),
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=hard,
    )

    if out is None:
        return _stage4_fallback(labels)

    return [
        {
            "label_ko": a.label_ko.strip(),
            "strength": a.strength.to_string(),
            "rationale_ko": a.rationale_ko,
        }
        for a in out.assignments
    ]


def _stage4_fallback(labels: List[str]) -> List[Dict[str, str]]:
    """LLM 실패 시 — 쿼터 내에서 균형 분배."""
    n = len(labels)
    n_strong = max(REF_STRONG_QUOTA_MIN, min(REF_STRONG_QUOTA_MAX, round(n / 3) or 1))
    n_early = n - n_strong

    if n_early > REF_EARLY_QUOTA_MAX:
        overflow = n_early - REF_EARLY_QUOTA_MAX
        bump = min(overflow, REF_STRONG_QUOTA_MAX - n_strong)
        n_strong += bump
        n_early -= bump
    if n_early < REF_EARLY_QUOTA_MIN and n_strong > REF_STRONG_QUOTA_MIN:
        shift = min(REF_EARLY_QUOTA_MIN - n_early, n_strong - REF_STRONG_QUOTA_MIN)
        n_strong -= shift
        n_early += shift

    n_verystrong = 1 if n_strong >= 2 else 0
    n_strong_only = n_strong - n_verystrong
    n_med = (n_early + 1) // 2
    n_remaining_early = n_early - n_med
    n_weak = (n_remaining_early + 1) // 2
    n_veryweak = n_remaining_early - n_weak

    app_logger.info(
        "Stage 4 fallback: N={} → VS={} S={} M={} W={} VW={}",
        n,
        n_verystrong,
        n_strong_only,
        n_med,
        n_weak,
        n_veryweak,
    )

    sequence = (
        ([SignpostStrength.VERYSTRONG.to_string()] * n_verystrong)
        + ([SignpostStrength.STRONG.to_string()] * n_strong_only)
        + ([SignpostStrength.MEDIUM.to_string()] * n_med)
        + ([SignpostStrength.WEAK.to_string()] * n_weak)
        + ([SignpostStrength.VERYWEAK.to_string()] * n_veryweak)
    )
    out: List[Dict[str, str]] = []
    for lbl, strength in zip(labels, sequence):
        out.append({
            "label_ko": lbl,
            "strength": strength,
            "rationale_ko": (
                "Fallback — LLM 실패로 분포 기반 안전 strength 부여. "
                "후속 재실행을 통해 정밀 평가 필요."
            ),
        })
    return out


# ==============================================
# 7. Stage 5 — Keyword Hint Mint
# ==============================================

STAGE5_SYSTEM = """\
당신은 LNG 멀티시나리오 'Keyword Hint Mint' 입니다.
각 Signpost label_ko 에 대해 Record(기사) 인입 시 1차 Filter 로 쓰일
keyword_hints 3~5개를 부여하십시오.

## 작성 원칙
- 고유명사 우선: 시설명·기관명·지명·국가명을 최소 1개 포함.
  (예: 'Ras Laffan', 'QatarEnergy', '호르무즈', 'JKM', 'IMF')
- 동사·상태어 포함: 단순 명사 나열 금지. 최소 1개의 행위/상태어 포함.
  (예: '재가동', '선언', '타결', '교전', '공식화')
- 3~5개: 2개 이하면 recall 부족, 6개 이상이면 noise.
- 한국어/영문 혼용 가능. label_ko 의 핵심 토큰을 그대로 활용해도 좋음.
"""

STAGE5_HARD = """\
[중요한 출력 제약 — Stage 5]
- hints 길이는 입력 signpost 수와 정확히 일치.
- 각 항목의 label_ko 는 입력과 정확히 일치 (echo).
- keyword_hints 는 3~5개. 모든 항목 비어있지 않은 문자열.
- 고유명사 1개 이상 + 동사·상태어 1개 이상 포함 권장.
"""

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\-]+|[가-힣]+")


async def stage5_mint_keywords(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    labels: List[str],
) -> List[List[str]]:
    """Stage 5 진입점 — labels → [keyword_hints, ...] (signpost 별 3~5개)."""
    scenario_id = scenario.get("scenario_id", "S_??")
    if not labels:
        return []

    label_block = "\n".join(f"  [{i+1}] {lbl}" for i, lbl in enumerate(labels))

    user_prompt = f"""\
## Base Event 참고
- title: {base_event_summary.get('title', '')}

## 대상 시나리오 ({scenario_id})
- title: {scenario.get('title', '')}
- description: {_shorten(scenario.get('description', ''), 400)}

## 입력 Signpost label ({len(labels)}개) — 이 순서를 유지하여 hints 출력
{label_block}

## 산출
- hints 길이 = {len(labels)}.
- 각 항목의 keyword_hints 는 3~5개.
"""

    label_set = [lbl.strip() for lbl in labels]

    def _validate(out: _Stage5LLMOutput) -> None:
        if len(out.hints) != len(labels):
            raise ValueError(
                f"hints 길이 불일치: {len(out.hints)} != {len(labels)}"
            )
        out_labels = [h.label_ko.strip() for h in out.hints]
        if out_labels != label_set:
            raise ValueError(
                "hints 의 label_ko 순서가 입력과 다름. "
                f"expected={label_set}, got={out_labels}"
            )
        for h in out.hints:
            if not (KEYWORD_HINTS_MIN <= len(h.keyword_hints) <= KEYWORD_HINTS_MAX):
                raise ValueError(
                    f"keyword_hints 길이 위반 ({len(h.keyword_hints)}): "
                    f"허용 {KEYWORD_HINTS_MIN}~{KEYWORD_HINTS_MAX}"
                )
            if any(not str(kw).strip() for kw in h.keyword_hints):
                raise ValueError("keyword_hints 안에 빈 문자열 존재.")

    out = await _invoke_with_retry(
        stage_label="Stage 5",
        schema_cls=_Stage5LLMOutput,
        system_prompt=STAGE5_SYSTEM,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE5_HARD,
    )

    if out is None:
        return [_stage5_fallback_keywords(lbl) for lbl in labels]

    return [[kw.strip() for kw in h.keyword_hints] for h in out.hints]


def _stage5_fallback_keywords(label: str) -> List[str]:
    """LLM 실패 시 — label 의 명사 토큰 + 정형 행위어로 안전 3개 키워드 구성."""
    tokens = [t for t in _TOKEN_PATTERN.findall(label) if len(t) >= 2]
    seen: set = set()
    proper: List[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        proper.append(t)
        if len(proper) >= 2:
            break
    fallback_action = "보도"
    out = list(proper)
    if fallback_action not in out:
        out.append(fallback_action)
    while len(out) < KEYWORD_HINTS_MIN:
        out.append(f"신호{len(out)+1}")
    return out[:KEYWORD_HINTS_MAX]


# ==============================================
# 8. Pipeline Orchestration (per-scenario)
# ==============================================


async def build_signposts_for_scenario(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
) -> List[GeneratedSignpost]:
    """단일 시나리오에 대해 Stage 2→3→4→5 를 순차 실행하고 typed signposts 반환."""
    sid = scenario.get("scenario_id", 0)
    scenario_pk = int(sid) if isinstance(sid, (int, str)) and str(sid).isdigit() else 0

    # ── Stage 2 ────────────────────────────────────────────────
    labels = await stage2_observability_filter(scenario, base_event_summary)
    if not labels:
        app_logger.info("[{}] Stage 2 통과 0건 — signposts 비어있음", scenario_pk)
        return []

    # ── Stage 4 ────────────────────────────────────────────────
    s4_assigns = await stage4_assign_direction_strength(scenario, base_event_summary, labels)
    stage4_strengths = [
        SignpostStrength.from_string_or_default(
            a.get("strength"),
            default=SignpostStrength.MEDIUM,
        )
        for a in s4_assigns
    ]
    app_logger.info(
        "[{}] Stage 4 vs={} s={} m={} w={} vw={}",
        scenario_pk,
        sum(1 for s in stage4_strengths if s == SignpostStrength.VERYSTRONG),
        sum(1 for s in stage4_strengths if s == SignpostStrength.STRONG),
        sum(1 for s in stage4_strengths if s == SignpostStrength.MEDIUM),
        sum(1 for s in stage4_strengths if s == SignpostStrength.WEAK),
        sum(1 for s in stage4_strengths if s == SignpostStrength.VERYWEAK),
    )

    # ── Stage 5 ────────────────────────────────────────────────
    s5_keywords = await stage5_mint_keywords(scenario, base_event_summary, labels)

    # ── Stage 3 + 조립 ─────────────────────────────────────────
    signposts: List[GeneratedSignpost] = []
    for lbl, assign, kws in zip(labels, s4_assigns, s5_keywords):
        signposts.append(
            GeneratedSignpost(
                scenario_id=scenario_pk,
                signpost_class="observation",
                label=lbl,  # DB column name is 'label', not 'label_ko'
                signpost_source="mi_record",
                direction=DirectionCode.SUP,
                strength=SignpostStrength.from_string_or_default(
                    assign["strength"],
                    default=SignpostStrength.MEDIUM,
                ),
                rationale_ko=assign["rationale_ko"],
                keyword_hints=kws,
            )
        )
    return signposts
