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
from typing import Any, Dict, List

from langgraph.runtime import Runtime
from pydantic import BaseModel

from apps.agents.scenario_group_agent.prompts.signpost_generation import (
    KEYWORD_HINTS_MAX,
    KEYWORD_HINTS_MIN,
    STAGE2_SYSTEM_PROMPT,
    STAGE5_HARD_CONSTRAINTS,
    STAGE5_SYSTEM_PROMPT,
    Stage45StructuredOutput,
    Stage2StructuredOutput,
    Stage4StructuredOutput,
    Stage5StructuredOutput,
    build_stage45_hard_constraints,
    build_stage45_system_prompt,
    build_stage45_user_prompt,
    build_stage2_hard_constraints,
    build_stage2_user_prompt,
    build_stage4_hard_constraints,
    build_stage4_system_prompt,
    build_stage4_user_prompt,
    build_stage5_user_prompt,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.agents.scenario_group_agent.subgraphs.signpost_generation.schema import GeneratedSignpost
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger as app_logger
from apps.common.tracing.context import TraceContext
from apps.common.values.error_codes import ErrorCode
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

def _exception_chain(exc: Exception) -> list[BaseException]:
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and current not in chain:
        chain.append(current)
        current = current.__cause__ or current.__context__
    return chain


def _is_retryable_api_error(exc: Exception) -> bool:
    chain = _exception_chain(exc)
    status_codes = {getattr(item, "status_code", None) for item in chain[1:] or chain}
    if status_codes & {408, 429, 500, 502, 503, 504, 529}:
        return True
    name = " ".join(item.__class__.__name__.lower() for item in chain)
    msg = " ".join(str(item).lower() for item in chain)
    keywords = ("overloaded", "rate limit", "too many requests", "timeout", "connection")
    return any(k in name or k in msg for k in keywords)


def _is_retryable_schema_error(exc: Exception) -> bool:
    chain = _exception_chain(exc)
    name = " ".join(item.__class__.__name__.lower() for item in chain)
    msg = " ".join(str(item).lower() for item in chain)
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
        max_retries=0,
        trace_context=trace_context,
    )
    return result.result


def _raise_llm_failure(stage_label: str, exc: Exception | None) -> None:
    if exc is None:
        raise MIBaseError(
            ErrorCode.LLM_INVOCATION_ERROR,
            detail=f"{stage_label} LLM 호출 결과가 없습니다.",
        )
    combined = " ".join(
        f"{item.__class__.__name__}: {item}".lower()
        for item in _exception_chain(exc)
    )
    if "timeout" in combined or "timed out" in combined:
        error_code = ErrorCode.LLM_RESPONSE_TIMEOUT
    elif _is_retryable_schema_error(exc) or any(
        isinstance(item, (TypeError, ValueError)) for item in _exception_chain(exc)
    ):
        error_code = ErrorCode.LLM_INVALID_RESPONSE_ERROR
    else:
        error_code = ErrorCode.LLM_INVOCATION_ERROR
    raise MIBaseError(
        error_code,
        detail=f"{stage_label} LLM 호출이 {REF_MAX_RETRIES}회 시도 후 실패했습니다.",
    ) from exc


async def _ainvoke_with_retry(
    stage_label: str,
    schema_cls: type[BaseModel],
    system_prompt: str,
    user_prompt: str,
    validate_fn,
    hard_constraints: str = "",
    temperature: float = 0.0,
    trace_context: TraceContext | None = None,
) -> BaseModel:
    """Invoke the LLM with bounded retries and fail closed."""
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
            result = await _invoke_structured(
                schema_cls,
                messages,
                temperature=temperature,
                trace_context=trace_context,
            )
            if result is None:
                raise ValueError("LLM returned None result")
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
            app_logger.info(
                "[{}] 재시도 ({}/{}) — {}, {:.1f}s 후",
                stage_label,
                attempt,
                REF_MAX_RETRIES,
                reason,
                wait_sec,
            )
            await asyncio.sleep(wait_sec)

    app_logger.warning("[{}] 재시도 소진", stage_label)
    _raise_llm_failure(stage_label, last_exc)


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
        _raise_llm_failure("Stage 2", None)

    candidates = out.candidates[:REF_SIGNPOSTS_PER_SCENARIO_MAX]
    app_logger.info(
        "[{}] Stage 2 passed_labels={}",
        scenario_id,
        len(candidates),
    )
    return [c.label_ko.strip() for c in candidates]


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
        _raise_llm_failure("Stage 4", None)

    return [
        {
            "label_ko": a.label_ko.strip(),
            "strength": a.strength.to_string(),
            "rationale_ko": a.rationale_ko,
        }
        for a in out.assignments
    ]


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
        _raise_llm_failure("Stage 4+5", None)

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


# ==============================================
# 7. Stage 5 — Keyword Hint Mint
# ==============================================

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
        _raise_llm_failure("Stage 5", None)

    return [[kw.strip() for kw in h.keyword_hints] for h in out.hints]


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
