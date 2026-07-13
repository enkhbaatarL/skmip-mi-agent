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
from typing import Any, Dict, List

from langgraph.runtime import Runtime
from pydantic import BaseModel

from apps.agents.scenario_group_agent.prompts.signpost_generation import (
    KEYWORD_HINTS_MAX,
    KEYWORD_HINTS_MIN,
    STAGE2_SYSTEM_PROMPT,
    STAGE5_HARD_CONSTRAINTS,
    STAGE5_SYSTEM_PROMPT,
    Stage45BatchStructuredOutput,
    Stage45StructuredOutput,
    Stage2BatchStructuredOutput,
    Stage2StructuredOutput,
    Stage4StructuredOutput,
    Stage5StructuredOutput,
    build_stage45_batch_user_prompt,
    build_stage45_hard_constraints,
    build_stage45_system_prompt,
    build_stage45_user_prompt,
    build_stage2_batch_user_prompt,
    build_stage2_hard_constraints,
    build_stage2_user_prompt,
    build_stage4_hard_constraints,
    build_stage4_system_prompt,
    build_stage4_user_prompt,
    build_stage5_user_prompt,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import GeneratedSignpost
from apps.common.logging.logger_config import logger as app_logger
from apps.common.tracing.context import TraceContext
from apps.persistence.enums import (
    DirectionCode,
    SignpostStrength,
)


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

# Retry
REF_MAX_RETRIES: int = int(os.getenv("REF_MAX_RETRIES", "5"))

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
    trace_context: TraceContext | None = None,
) -> BaseModel | None:
    """Async structured output LLM call via the project's invoke_llm_structured_output connector."""
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    result = await invoke_llm_structured_output(
        output_schema=schema_cls,
        messages=messages,
        temperature=temperature,
        max_retries=2,
        trace_context=trace_context,
    )
    return result.result


async def _ainvoke_with_retry(
    stage_label: str,
    schema_cls: type[BaseModel],
    system_prompt: str,
    user_prompt: str,
    validate_fn,
    hard_constraints: str = "",
    temperature: float = 0.0,
    trace_context: TraceContext | None = None,
) -> BaseModel | None:
    """LLM 호출 with retry + validation + fallback.

    Returns parsed Pydantic model on success, None on all retries exhausted.
    """
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
            result = await _invoke_structured(
                schema_cls,
                messages,
                temperature=temperature,
                trace_context=trace_context,
            )
            if result is None:
                raise ValueError("LLM returned None result")
            validate_fn(result)
            return result

        except Exception as exc:  # noqa: BLE001
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

def _shorten(text: str, n: int) -> str:
    text = (text or "").strip()
    if len(text) <= n:
        return text
    return text[:n] + " …(생략)"


async def stage2_observability_filter(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    trace_context: TraceContext | None = None,
) -> List[str]:
    """Stage 2 진입점 — 시나리오 1건 → 통과 label_ko 리스트 반환."""
    scenario_id = scenario.get("scenario_id", "S_??")
    user_prompt = build_stage2_user_prompt(
        scenario=scenario,
        base_event_summary=base_event_summary,
        scenario_description=_shorten(scenario.get("description", ""), 600),
        min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
        max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
    )
    hard = build_stage2_hard_constraints(
        min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
        max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
    )

    def _validate(out: Stage2StructuredOutput) -> None:
        candidate_count = len(out.candidates)
        if not (REF_SIGNPOSTS_PER_SCENARIO_MIN <= candidate_count <= REF_SIGNPOSTS_PER_SCENARIO_MAX):
            raise ValueError(
                f"후보 수 {candidate_count} 이 허용 범위 "
                f"[{REF_SIGNPOSTS_PER_SCENARIO_MIN}, {REF_SIGNPOSTS_PER_SCENARIO_MAX}] 밖."
            )

    out = await _ainvoke_with_retry(
        stage_label="Stage 2",
        schema_cls=Stage2StructuredOutput,
        system_prompt=STAGE2_SYSTEM_PROMPT.format(
            min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
            max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
        ),
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=hard,
        trace_context=trace_context,
    )

    if out is None:
        labels = _stage2_fallback(scenario)
        app_logger.info("[{}] Stage 2 fallback labels={}", scenario_id, len(labels))
        return labels

    candidates = out.candidates[:REF_SIGNPOSTS_PER_SCENARIO_MAX]
    app_logger.info(
        "[{}] Stage 2 passed_labels={}",
        scenario_id,
        len(candidates),
    )
    return [c.label_ko.strip() for c in candidates]


async def stage2_observability_filter_batch(
    scenarios: list[dict[str, Any]],
    base_event_summary: Dict[str, str],
    trace_context: TraceContext | None = None,
) -> dict[int, list[str]]:
    """Stage 2 batch — 시나리오 목록 전체의 통과 label_ko 를 한 번에 생성."""
    if not scenarios:
        return {}

    scenario_ids = {int(scenario["scenario_id"]) for scenario in scenarios}
    user_prompt = build_stage2_batch_user_prompt(
        scenarios=scenarios,
        base_event_summary=base_event_summary,
        min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
        max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
    )
    hard = build_stage2_hard_constraints(
        min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
        max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
    )

    out = await _ainvoke_with_retry(
        stage_label="Stage 2 batch",
        schema_cls=Stage2BatchStructuredOutput,
        system_prompt=STAGE2_SYSTEM_PROMPT.format(
            min_n=REF_SIGNPOSTS_PER_SCENARIO_MIN,
            max_n=REF_SIGNPOSTS_PER_SCENARIO_MAX,
        ),
        user_prompt=user_prompt,
        validate_fn=None,
        hard_constraints=hard,
        trace_context=trace_context,
    )

    scenario_by_id = {int(scenario["scenario_id"]): scenario for scenario in scenarios}
    labels_by_id: dict[int, list[str]] = {}
    seen_ids: set[int] = set()
    if out is not None:
        for item in out.scenarios:
            if item.scenario_id not in scenario_ids or item.scenario_id in seen_ids:
                continue
            seen_ids.add(item.scenario_id)
            candidate_count = len(item.candidates)
            if not (REF_SIGNPOSTS_PER_SCENARIO_MIN <= candidate_count <= REF_SIGNPOSTS_PER_SCENARIO_MAX):
                app_logger.info(
                    "[{}] Stage 2 batch partial fallback: candidate_count={}",
                    item.scenario_id,
                    candidate_count,
                )
                continue
            labels_by_id[item.scenario_id] = [
                candidate.label_ko.strip()
                for candidate in item.candidates[:REF_SIGNPOSTS_PER_SCENARIO_MAX]
            ]

    for scenario_id, scenario in scenario_by_id.items():
        labels_by_id.setdefault(scenario_id, _stage2_fallback(scenario))
    return labels_by_id


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
# 6. Stage 4 — Direction & Strength Assignment
# ==============================================

async def stage4_assign_direction_strength(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    labels: List[str],
    trace_context: TraceContext | None = None,
) -> List[Dict[str, str]]:
    """Stage 4 진입점 — labels → [{label_ko, strength, rationale_ko}, ...]."""
    if not labels:
        return []

    user_prompt = build_stage4_user_prompt(
        scenario=scenario,
        base_event_summary=base_event_summary,
        scenario_description=_shorten(scenario.get("description", ""), 600),
        labels=labels,
    )

    label_set = [lbl.strip() for lbl in labels]
    hard = build_stage4_hard_constraints(
        strong_min=REF_STRONG_QUOTA_MIN,
        strong_max=REF_STRONG_QUOTA_MAX,
        early_min=REF_EARLY_QUOTA_MIN,
        early_max=REF_EARLY_QUOTA_MAX,
    )

    def _validate(out: Stage4StructuredOutput) -> None:
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

    out = await _ainvoke_with_retry(
        stage_label="Stage 4",
        schema_cls=Stage4StructuredOutput,
        system_prompt=build_stage4_system_prompt(
            stage4_strength_guide=SignpostStrength.stage4_prompt_guide_text(),
            strong_min=REF_STRONG_QUOTA_MIN,
            strong_max=REF_STRONG_QUOTA_MAX,
            early_min=REF_EARLY_QUOTA_MIN,
            early_max=REF_EARLY_QUOTA_MAX,
        ),
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=hard,
        trace_context=trace_context,
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


async def stage45_enrich_signposts(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    labels: List[str],
    trace_context: TraceContext | None = None,
) -> tuple[List[Dict[str, str]], List[List[str]]]:
    """Stage 4+5 진입점 — strength/rationale/keyword_hints 를 한 번에 생성."""
    if not labels:
        return [], []

    user_prompt = build_stage45_user_prompt(
        scenario=scenario,
        base_event_summary=base_event_summary,
        scenario_description=_shorten(scenario.get("description", ""), 600),
        labels=labels,
    )
    label_set = [lbl.strip() for lbl in labels]
    hard = build_stage45_hard_constraints(
        strong_min=REF_STRONG_QUOTA_MIN,
        strong_max=REF_STRONG_QUOTA_MAX,
        early_min=REF_EARLY_QUOTA_MIN,
        early_max=REF_EARLY_QUOTA_MAX,
    )

    def _validate(out: Stage45StructuredOutput) -> None:
        if len(out.signposts) != len(labels):
            raise ValueError(
                f"signposts 길이 불일치: {len(out.signposts)} != {len(labels)}"
            )
        out_labels = [item.label_ko.strip() for item in out.signposts]
        if out_labels != label_set:
            raise ValueError(
                "signposts 의 label_ko 순서가 입력과 다름. "
                f"expected={label_set}, got={out_labels}"
            )
        n_strong = sum(
            1
            for item in out.signposts
            if item.strength in (SignpostStrength.VERYSTRONG, SignpostStrength.STRONG)
        )
        n_early = sum(
            1
            for item in out.signposts
            if item.strength
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
        for item in out.signposts:
            if not (KEYWORD_HINTS_MIN <= len(item.keyword_hints) <= KEYWORD_HINTS_MAX):
                raise ValueError(
                    f"keyword_hints 길이 위반 ({len(item.keyword_hints)}): "
                    f"허용 {KEYWORD_HINTS_MIN}~{KEYWORD_HINTS_MAX}"
                )
            if any(not str(kw).strip() for kw in item.keyword_hints):
                raise ValueError("keyword_hints 안에 빈 문자열 존재.")

    out = await _ainvoke_with_retry(
        stage_label="Stage 4+5",
        schema_cls=Stage45StructuredOutput,
        system_prompt=build_stage45_system_prompt(
            stage4_strength_guide=SignpostStrength.stage4_prompt_guide_text(),
            strong_min=REF_STRONG_QUOTA_MIN,
            strong_max=REF_STRONG_QUOTA_MAX,
            early_min=REF_EARLY_QUOTA_MIN,
            early_max=REF_EARLY_QUOTA_MAX,
        ),
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=hard,
        trace_context=trace_context,
    )

    if out is None:
        return _stage4_fallback(labels), [_stage5_fallback_keywords(label) for label in labels]

    assignments = [
        {
            "label_ko": item.label_ko.strip(),
            "strength": item.strength.to_string(),
            "rationale_ko": item.rationale_ko,
        }
        for item in out.signposts
    ]
    keyword_hints = [[kw.strip() for kw in item.keyword_hints] for item in out.signposts]
    return assignments, keyword_hints


async def stage45_enrich_signposts_batch(
    scenarios: list[dict[str, Any]],
    base_event_summary: Dict[str, str],
    labels_by_scenario_id: dict[int, list[str]],
    trace_context: TraceContext | None = None,
) -> dict[int, tuple[List[Dict[str, str]], List[List[str]]]]:
    """Stage 4+5 batch — scenario 목록 전체의 상세 signpost를 한 번에 생성."""
    scenarios_with_labels = [
        scenario for scenario in scenarios if labels_by_scenario_id.get(int(scenario["scenario_id"]))
    ]
    if not scenarios_with_labels:
        return {}

    scenario_ids = {int(scenario["scenario_id"]) for scenario in scenarios_with_labels}
    hard = build_stage45_hard_constraints(
        strong_min=REF_STRONG_QUOTA_MIN,
        strong_max=REF_STRONG_QUOTA_MAX,
        early_min=REF_EARLY_QUOTA_MIN,
        early_max=REF_EARLY_QUOTA_MAX,
    )
    label_sets = {
        scenario_id: [label.strip() for label in labels]
        for scenario_id, labels in labels_by_scenario_id.items()
    }

    out = await _ainvoke_with_retry(
        stage_label="Stage 4+5 batch",
        schema_cls=Stage45BatchStructuredOutput,
        system_prompt=build_stage45_system_prompt(
            stage4_strength_guide=SignpostStrength.stage4_prompt_guide_text(),
            strong_min=REF_STRONG_QUOTA_MIN,
            strong_max=REF_STRONG_QUOTA_MAX,
            early_min=REF_EARLY_QUOTA_MIN,
            early_max=REF_EARLY_QUOTA_MAX,
        ),
        user_prompt=build_stage45_batch_user_prompt(
            scenarios=scenarios_with_labels,
            base_event_summary=base_event_summary,
            labels_by_scenario_id=label_sets,
        ),
        validate_fn=None,
        hard_constraints=hard,
        trace_context=trace_context,
    )

    result: dict[int, tuple[List[Dict[str, str]], List[List[str]]]] = {}
    seen_ids: set[int] = set()
    for scenario_out in out.scenarios if out is not None else []:
        if scenario_out.scenario_id not in scenario_ids or scenario_out.scenario_id in seen_ids:
            continue
        seen_ids.add(scenario_out.scenario_id)
        labels = label_sets[scenario_out.scenario_id]
        if len(scenario_out.signposts) != len(labels):
            app_logger.info(
                "[{}] Stage 4+5 batch partial fallback: signpost_count={} expected={}",
                scenario_out.scenario_id,
                len(scenario_out.signposts),
                len(labels),
            )
            continue
        out_labels = [item.label_ko.strip() for item in scenario_out.signposts]
        if out_labels != labels:
            app_logger.info(
                "[{}] Stage 4+5 batch partial fallback: label order mismatch",
                scenario_out.scenario_id,
            )
            continue
        n_strong = sum(
            1
            for item in scenario_out.signposts
            if item.strength in (SignpostStrength.VERYSTRONG, SignpostStrength.STRONG)
        )
        n_early = sum(
            1
            for item in scenario_out.signposts
            if item.strength
            in (
                SignpostStrength.MEDIUM,
                SignpostStrength.WEAK,
                SignpostStrength.VERYWEAK,
            )
        )
        if not (REF_STRONG_QUOTA_MIN <= n_strong <= REF_STRONG_QUOTA_MAX):
            app_logger.info(
                "[{}] Stage 4+5 batch partial fallback: strong_quota={}",
                scenario_out.scenario_id,
                n_strong,
            )
            continue
        if not (REF_EARLY_QUOTA_MIN <= n_early <= REF_EARLY_QUOTA_MAX):
            app_logger.info(
                "[{}] Stage 4+5 batch partial fallback: early_quota={}",
                scenario_out.scenario_id,
                n_early,
            )
            continue
        has_bad_hints = any(
            not (KEYWORD_HINTS_MIN <= len(item.keyword_hints) <= KEYWORD_HINTS_MAX)
            or any(not str(kw).strip() for kw in item.keyword_hints)
            for item in scenario_out.signposts
        )
        if has_bad_hints:
            app_logger.info(
                "[{}] Stage 4+5 batch partial fallback: invalid keyword_hints",
                scenario_out.scenario_id,
            )
            continue
        assignments = [
            {
                "label_ko": item.label_ko.strip(),
                "strength": item.strength.to_string(),
                "rationale_ko": item.rationale_ko,
            }
            for item in scenario_out.signposts
        ]
        keyword_hints = [[kw.strip() for kw in item.keyword_hints] for item in scenario_out.signposts]
        result[scenario_out.scenario_id] = (assignments, keyword_hints)
    for scenario in scenarios_with_labels:
        scenario_id = int(scenario["scenario_id"])
        if scenario_id in result:
            continue
        labels = label_sets[scenario_id]
        result[scenario_id] = (
            _stage4_fallback(labels),
            [_stage5_fallback_keywords(label) for label in labels],
        )
    return result


# ==============================================
# 7. Stage 5 — Keyword Hint Mint
# ==============================================

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\-]+|[가-힣]+")


async def stage5_mint_keywords(
    scenario: Dict[str, Any],
    base_event_summary: Dict[str, str],
    labels: List[str],
    trace_context: TraceContext | None = None,
) -> List[List[str]]:
    """Stage 5 진입점 — labels → [keyword_hints, ...] (signpost 별 3~5개)."""
    if not labels:
        return []

    user_prompt = build_stage5_user_prompt(
        scenario=scenario,
        base_event_summary=base_event_summary,
        scenario_description=_shorten(scenario.get("description", ""), 400),
        labels=labels,
    )

    label_set = [lbl.strip() for lbl in labels]

    def _validate(out: Stage5StructuredOutput) -> None:
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

    out = await _ainvoke_with_retry(
        stage_label="Stage 5",
        schema_cls=Stage5StructuredOutput,
        system_prompt=STAGE5_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE5_HARD_CONSTRAINTS,
        trace_context=trace_context,
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
# LangGraph Node Classes
# ==============================================

from apps.agents.scenario_group_agent.subgraphs.signpost_generation.state import (
    SignpostGenerationState,
)


def _scenario_pk(scenario: dict[str, Any]) -> int:
    scenario_id = scenario.get("scenario_id", 0)
    if isinstance(scenario_id, (int, str)) and str(scenario_id).isdigit():
        return int(scenario_id)
    return 0


class ObservabilityFilterNode(BaseNode):
    async def run(
        self,
        state: SignpostGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error:
            return {}
        if state.scenario is None:
            return {"error": "scenario is required"}
        trace_context = runtime.context if runtime is not None else None
        if trace_context is None:
            labels = await stage2_observability_filter(state.scenario, state.base_event_summary)
        else:
            labels = await stage2_observability_filter(
                state.scenario,
                state.base_event_summary,
                trace_context=trace_context,
            )
        if not labels:
            app_logger.info("[{}] Stage 2 통과 0건 - signposts 비어있음", _scenario_pk(state.scenario))
        return {"labels": labels}


class DirectionStrengthNode(BaseNode):
    async def run(
        self,
        state: SignpostGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error or not state.labels:
            return {}
        if state.scenario is None:
            return {"error": "scenario is required"}
        trace_context = runtime.context if runtime is not None else None
        if trace_context is None:
            assignments = await stage4_assign_direction_strength(
                state.scenario,
                state.base_event_summary,
                state.labels,
            )
        else:
            assignments = await stage4_assign_direction_strength(
                state.scenario,
                state.base_event_summary,
                state.labels,
                trace_context=trace_context,
            )
        strengths = [
            SignpostStrength.from_string_or_default(
                assignment.get("strength"),
                default=SignpostStrength.MEDIUM,
            )
            for assignment in assignments
        ]
        app_logger.info(
            "[{}] Stage 4 vs={} s={} m={} w={} vw={}",
            _scenario_pk(state.scenario),
            sum(1 for strength in strengths if strength == SignpostStrength.VERYSTRONG),
            sum(1 for strength in strengths if strength == SignpostStrength.STRONG),
            sum(1 for strength in strengths if strength == SignpostStrength.MEDIUM),
            sum(1 for strength in strengths if strength == SignpostStrength.WEAK),
            sum(1 for strength in strengths if strength == SignpostStrength.VERYWEAK),
        )
        return {"stage4_assignments": assignments}


class EnrichSignpostsNode(BaseNode):
    async def run(
        self,
        state: SignpostGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error or not state.labels:
            return {}
        if state.scenario is None:
            return {"error": "scenario is required"}
        trace_context = runtime.context if runtime is not None else None
        if trace_context is None:
            assignments, keyword_hints = await stage45_enrich_signposts(
                state.scenario,
                state.base_event_summary,
                state.labels,
            )
        else:
            assignments, keyword_hints = await stage45_enrich_signposts(
                state.scenario,
                state.base_event_summary,
                state.labels,
                trace_context=trace_context,
            )
        strengths = [
            SignpostStrength.from_string_or_default(
                assignment.get("strength"),
                default=SignpostStrength.MEDIUM,
            )
            for assignment in assignments
        ]
        app_logger.info(
            "[{}] Stage 4+5 vs={} s={} m={} w={} vw={} hints={}",
            _scenario_pk(state.scenario),
            sum(1 for strength in strengths if strength == SignpostStrength.VERYSTRONG),
            sum(1 for strength in strengths if strength == SignpostStrength.STRONG),
            sum(1 for strength in strengths if strength == SignpostStrength.MEDIUM),
            sum(1 for strength in strengths if strength == SignpostStrength.WEAK),
            sum(1 for strength in strengths if strength == SignpostStrength.VERYWEAK),
            len(keyword_hints),
        )
        return {"stage4_assignments": assignments, "stage5_keyword_hints": keyword_hints}


class KeywordHintsNode(BaseNode):
    async def run(
        self,
        state: SignpostGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error or not state.labels:
            return {}
        if state.scenario is None:
            return {"error": "scenario is required"}
        trace_context = runtime.context if runtime is not None else None
        if trace_context is None:
            keyword_hints = await stage5_mint_keywords(
                state.scenario,
                state.base_event_summary,
                state.labels,
            )
        else:
            keyword_hints = await stage5_mint_keywords(
                state.scenario,
                state.base_event_summary,
                state.labels,
                trace_context=trace_context,
            )
        return {"stage5_keyword_hints": keyword_hints}


class AssembleSignpostsNode(BaseNode):
    async def run(self, state: SignpostGenerationState) -> dict[str, Any]:
        if state.skip_generation or state.error or state.scenario is None:
            return {}
        axes = {
            "signpost_class": "observation",
            "signpost_source": "mi_record",
        }
        scenario_pk = _scenario_pk(state.scenario)
        signposts: list[GeneratedSignpost] = []
        for label, assignment, keyword_hints in zip(
            state.labels,
            state.stage4_assignments,
            state.stage5_keyword_hints,
            strict=False,
        ):
            signposts.append(
                GeneratedSignpost(
                    scenario_id=scenario_pk,
                    signpost_class="observation",
                    label=label,
                    signpost_source=axes["signpost_source"],
                    direction=DirectionCode.SUP,
                    strength=SignpostStrength.from_string_or_default(
                        assignment.get("strength"),
                        default=SignpostStrength.MEDIUM,
                    ),
                    rationale_ko=assignment.get("rationale_ko", ""),
                    keyword_hints=keyword_hints,
                ),
            )
        return {"signposts": signposts}
