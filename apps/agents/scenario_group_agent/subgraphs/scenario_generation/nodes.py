"""Scenario generation stages used by the scenario group agent."""

from __future__ import annotations

import asyncio
from itertools import product
import json
import os
import random
import re
from typing import Any, Dict, List, Tuple
import uuid

from langgraph.runtime import Runtime
from pydantic import BaseModel

from apps.agents.scenario_group_agent.prompts.scenario_generation import (
    SCENARIO_GROUP_METADATA_HARD_CONSTRAINTS,
    SCENARIO_GROUP_METADATA_SYSTEM_PROMPT,
    STAGE2_HARD_CONSTRAINTS,
    STAGE2_SYSTEM_PROMPT,
    STAGE3_HARD_CONSTRAINTS,
    STAGE3_SYSTEM_PROMPT,
    STAGE4_HARD_CONSTRAINTS,
    STAGE4_SYSTEM_PROMPT,
    STAGE6_HARD_CONSTRAINTS,
    STAGE6_SYSTEM_PROMPT,
    NarrativeOnly,
    ScenarioGroupMetadataStructuredOutput,
    Stage2StructuredOutput,
    Stage3StructuredOutput,
    Stage4StructuredOutput,
    Stage6StructuredOutput,
    build_scenario_group_metadata_user_prompt,
    build_stage2_user_prompt,
    build_stage3_user_prompt,
    build_stage4_fixed_user_prompt,
    build_stage4_user_prompt,
    build_stage6_user_prompt,
)
from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    COMPAT_SYSTEM_PROMPT,
    CompatibilityItem,
    CompatibilityStructuredOutput,
)
from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import (
    LIKELIHOOD_TIERS,
    PRICE_TIERS,
    C1BaseEvent,
    C2LinkedRecords,
    DimensionValueMap,
    ExcludedDimension,
    MECECheck,
    PerDimensionValue,
    PriceDirection,
    Scenario,
    ScenarioGroupMetadata,
    ScenarioTemplate,
    SelectedDimension,
    Stage1ContextPack,
    Stage2DimensionSelection,
    Stage3ValueSelection,
    Stage4ScenarioSynthesis,
    Stage5RepairInstruction,
    Stage5Validation,
)
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.common.tracing.context import TraceContext
from apps.persistence.scenario.baseline_contrast import (
    check_baseline_contrast_coverage,
)


# --- LLM config constants (from env) ---
REF_MAX_RETRIES: int = int(os.getenv("REF_MAX_RETRIES", "5"))
REF_TARGET_SCENARIOS: int = int(os.getenv("REF_TARGET_SCENARIOS", "6"))
REF_TEMPERATURE: float = float(os.getenv("REF_TEMPERATURE", "0.0"))
REF_QUICK_VALIDATE_MAX_RETRIES: int = int(os.getenv("REF_QUICK_VALIDATE_MAX_RETRIES", "2"))


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
# 4. LLM Infrastructure
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
) -> BaseModel:
    """Structured output LLM call via the project's async connector."""
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    result = await invoke_llm_structured_output(
        output_schema=schema_cls,
        messages=messages,
        temperature=temperature or REF_TEMPERATURE,
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
    trace_context: TraceContext | None = None,
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
            result = await _invoke_structured(
                schema_cls,
                messages,
                temperature=REF_TEMPERATURE,
                trace_context=trace_context,
            )
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
                logger.warning(
                    "{} retry disabled | error_type={} | error={}",
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
            err_summary = f"{exc.__class__.__name__}: {str(exc)[:200]}"
            logger.warning(
                "{} retry scheduled | attempt={}/{} | reason={} | wait_sec={:.1f} | error={}",
                stage_label,
                attempt,
                REF_MAX_RETRIES,
                reason,
                wait_sec,
                err_summary,
            )
            await asyncio.sleep(wait_sec)

    logger.warning("{} retry exhausted; fallback starts | last_error={}", stage_label, type(last_exc).__name__)
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

@log_tool
async def stage2_select_dimensions(
    pack: Stage1ContextPack,
    event: Dict,
    template: ScenarioTemplate,
    llm_client=None,
    trace_context: TraceContext | None = None,
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

    user_prompt = build_stage2_user_prompt(
        pack=pack,
        template=template,
        detail_excerpt=detail_excerpt,
        required_dim_ids=required_dim_ids,
    )

    def _validate(out: Stage2StructuredOutput) -> None:
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

    out = await _ainvoke_with_retry(
        stage_label="Stage 2",
        schema_cls=Stage2StructuredOutput,
        system_prompt=STAGE2_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE2_HARD_CONSTRAINTS,
        trace_context=trace_context,
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


def _stage2_fallback(template_dim_ids: List[str]) -> Stage2StructuredOutput:
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
    return Stage2StructuredOutput(selected_dimensions=selected, excluded_dimensions=excluded)


# ==============================================
# 8. Stage 3 — Value Reducer (LLM per-dimension)
# ==============================================

@log_tool
async def stage3_reduce_values(
    pack: Stage1ContextPack,
    selected: Stage2DimensionSelection,
    template: ScenarioTemplate,
    llm_client=None,
    trace_context: TraceContext | None = None,
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

        user_prompt = build_stage3_user_prompt(
            pack=pack,
            dim=dim,
            enum_full_block=enum_full_block,
        )

        def _validate(out: Stage3StructuredOutput) -> None:
            unknown = set(out.selected_enum) - set(enum_full)
            if unknown:
                raise ValueError(f"value_enums 외 값 사용: {unknown}")

        out = await _ainvoke_with_retry(
            stage_label=f"Stage 3 [{dim['dim_key']}]",
            schema_cls=Stage3StructuredOutput,
            system_prompt=STAGE3_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            validate_fn=_validate,
            hard_constraints=STAGE3_HARD_CONSTRAINTS,
            trace_context=trace_context,
        )

        if out is None:
            out = _stage3_fallback(dim)

        per_dim.append(PerDimensionValue(
            dim_key=dim["dim_key"],
            template_enum_full=enum_full,
            selected_enum=out.selected_enum,
        ))

    return Stage3ValueSelection(per_dimension=per_dim)


def _stage3_fallback(dim: Dict) -> Stage3StructuredOutput:
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
    return Stage3StructuredOutput(selected_enum=selected[:4])


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


def _combo_key(combo: Dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(combo.items()))


def _parse_scenario_ref_index(scenario_ref: str) -> int | None:
    match = re.fullmatch(r"S_(\d+)", str(scenario_ref).strip())
    if not match:
        return None
    return int(match.group(1)) - 1


def _selected_enum_map(stage3: Stage3ValueSelection) -> dict[str, set[str]]:
    return {
        pd.dim_key: {str(value) for value in pd.selected_enum}
        for pd in stage3.per_dimension
    }


def _template_enum_map(template: ScenarioTemplate) -> dict[str, set[str]]:
    return {
        dimension.dim_key: {str(value) for value in dimension.value_enums}
        for dimension in template.ordered_dimensions()
    }


def _valid_stage4_overrides(
    repairs: list[Stage5RepairInstruction] | None,
    template: ScenarioTemplate,
) -> list[Stage5RepairInstruction]:
    if not repairs:
        return []
    enum_map = _template_enum_map(template)
    valid: list[Stage5RepairInstruction] = []
    for repair in repairs:
        allowed = enum_map.get(repair.dim_key)
        if not allowed:
            continue
        if repair.recommended_value not in allowed:
            continue
        if repair.recommended_value == repair.current_value:
            continue
        if _parse_scenario_ref_index(repair.scenario_ref) is None:
            continue
        valid.append(repair)
    return valid


def _apply_stage4_regeneration_overrides(
    target: list[Dict[str, str]],
    *,
    previous_stage4: Stage4ScenarioSynthesis | None,
    validation_repairs: list[Stage5RepairInstruction] | None,
    template: ScenarioTemplate,
) -> list[Dict[str, str]]:
    valid_repairs = _valid_stage4_overrides(validation_repairs, template)
    if not target or previous_stage4 is None or not valid_repairs:
        return target

    regenerated = [dict(combo) for combo in target]
    for repair in valid_repairs:
        index = _parse_scenario_ref_index(repair.scenario_ref)
        if index is None or index >= len(regenerated) or index >= len(previous_stage4.scenarios):
            continue

        previous = previous_stage4.scenarios[index]
        if previous.dimension_values.get(repair.dim_key) != repair.current_value:
            continue

        combo = dict(previous.dimension_values)
        combo[repair.dim_key] = repair.recommended_value
        regenerated[index] = combo
    return regenerated


def _previous_stage4_block(stage4: Stage4ScenarioSynthesis | None) -> str | None:
    if stage4 is None:
        return None
    lines: list[str] = []
    for scenario in stage4.scenarios:
        dims = ", ".join(f"{key}={value}" for key, value in scenario.dimension_values.items())
        lines.append(
            f"- {scenario.scenario_id} | {scenario.title}\n"
            f"  dims: {dims}\n"
            f"  description: {scenario.description}",
        )
    return "\n".join(lines)


@log_tool
async def stage4_synthesize_scenarios(
    pack: Stage1ContextPack,
    stage3: Stage3ValueSelection,
    template: ScenarioTemplate,
    validation_feedback: str | None = None,
    validation_repairs: list[Stage5RepairInstruction] | None = None,
    previous_stage4: Stage4ScenarioSynthesis | None = None,
    llm_client=None,
    trace_context: TraceContext | None = None,
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
    target = _apply_stage4_regeneration_overrides(
        target,
        previous_stage4=previous_stage4,
        validation_repairs=validation_repairs,
        template=template,
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

    user_prompt = build_stage4_user_prompt(
        pack=pack,
        dim_label_block=dim_label_block,
        combos_block=combos_block,
        target_count=len(target),
        validation_feedback=validation_feedback,
        previous_scenarios_block=_previous_stage4_block(previous_stage4)
        if validation_feedback
        else None,
    )

    def _validate(out: Stage4StructuredOutput) -> None:
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

    out = await _ainvoke_with_retry(
        stage_label="Stage 4",
        schema_cls=Stage4StructuredOutput,
        system_prompt=STAGE4_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE4_HARD_CONSTRAINTS,
        trace_context=trace_context,
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


def _stage4_fallback(target: List[DimensionValueMap]) -> Stage4StructuredOutput:
    """LLM 실패 시 — 모든 조합에 대해 중립 시나리오 narrative 생성."""
    print(f"  ↳ Stage 4 fallback: {len(target)}개 중립 narrative 생성")
    narratives = [
        NarrativeOnly(
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
    return Stage4StructuredOutput(narratives=narratives)


@log_tool
async def stage4_synthesize_fixed_scenarios(
    pack: Stage1ContextPack,
    dimension_values_list: List[DimensionValueMap],
    llm_client=None,
    trace_context: TraceContext | None = None,
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
    user_prompt = build_stage4_fixed_user_prompt(
        pack=pack,
        dim_label_block=dim_label_block,
        combos_block=combos_block,
        target_count=len(target),
    )

    def _validate(out: Stage4StructuredOutput) -> None:
        if len(out.narratives) != len(target):
            raise ValueError(
                f"narratives 길이 불일치: {len(out.narratives)} != {len(target)}"
            )
        for n in out.narratives:
            for v in (n.price_direction.jkm, n.price_direction.ttf, n.price_direction.hh):
                if v not in PRICE_TIERS:
                    raise ValueError(f"price_direction 범위 밖 값: {v}")

    out = await _ainvoke_with_retry(
        stage_label="Stage 4 fixed",
        schema_cls=Stage4StructuredOutput,
        system_prompt=STAGE4_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE4_HARD_CONSTRAINTS,
        trace_context=trace_context,
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

@log_tool
async def stage_generate_scenario_group_metadata(
    pack: Stage1ContextPack,
    event: Dict,
    stage4: Stage4ScenarioSynthesis,
    llm_client=None,
    trace_context: TraceContext | None = None,
) -> ScenarioGroupMetadata:
    """Generate scenario group title/description for UI display."""
    detail_excerpt = _shorten(event.get("detail_analysis", ""), 1200)
    user_prompt = build_scenario_group_metadata_user_prompt(
        pack=pack,
        detail_excerpt=detail_excerpt,
        scenarios=stage4.scenarios,
    )

    out = await _ainvoke_with_retry(
        stage_label="Scenario Group Metadata",
        schema_cls=ScenarioGroupMetadataStructuredOutput,
        system_prompt=SCENARIO_GROUP_METADATA_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        validate_fn=None,
        hard_constraints=SCENARIO_GROUP_METADATA_HARD_CONSTRAINTS,
        trace_context=trace_context,
    )

    if out is None:
        return ScenarioGroupMetadata(
            title=pack.C1_base_event.title or f"Scenario group {pack.C1_base_event.event_id}",
            description=pack.C1_base_event.summary or "",
        )

    return ScenarioGroupMetadata(title=out.title, description=out.description)


# ==============================================
# 12. Stage 6 — Validation (MECE + Likelihood LLM)
# ==============================================

@log_tool
async def stage6_validate(
    pack: Stage1ContextPack,
    stage4: Stage4ScenarioSynthesis,
    llm_client=None,
    trace_context: TraceContext | None = None,
) -> Stage5Validation:
    """Stage 6 진입점 — MECE 통과 여부 + 5단계 Prior 부여."""
    sc_ids = [s.scenario_id for s in stage4.scenarios]

    user_prompt = build_stage6_user_prompt(pack=pack, scenarios=stage4.scenarios)

    def _validate(out: Stage6StructuredOutput) -> None:
        keys = set(out.likelihood_prior.keys())
        wanted = set(sc_ids)
        if keys != wanted:
            raise ValueError(
                f"likelihood_prior 키 집합 불일치: 누락={wanted - keys}, 여분={keys - wanted}"
            )
        for v in out.likelihood_prior.values():
            if v not in LIKELIHOOD_TIERS:
                raise ValueError(f"5단계 외 Prior 값: {v}")

    out = await _ainvoke_with_retry(
        stage_label="Stage 6",
        schema_cls=Stage6StructuredOutput,
        system_prompt=STAGE6_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        validate_fn=_validate,
        hard_constraints=STAGE6_HARD_CONSTRAINTS,
        trace_context=trace_context,
    )

    if out is None:
        out = _stage6_fallback(sc_ids)

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
            f"  ↳ Stage 6 — LLM 판정({out.mutually_exclusive}) 과 코드 결정론 판정"
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


def _stage6_fallback(sc_ids: List[str]) -> Stage6StructuredOutput:
    """LLM 실패 시 — 모두 'medium' 으로 안전 부여."""
    print("  ↳ Stage 6 fallback: 전체 'medium' Prior 안전 부여")
    return Stage6StructuredOutput(
        mutually_exclusive=True,
        rationale="Fallback — Prior 카테고리 정밀 판정 보류.",
        likelihood_prior={sid: "medium" for sid in sc_ids},
    )


# ==============================================
# 11. Stage 5 — Quick Validation (LLM 1회 경량 검증)
# ==============================================

def _build_baseline_contrast_feedback(
    *,
    stage3: Stage3ValueSelection,
    missing_dim_keys: list[str],
    baseline_values: dict[str, object],
    baseline_issue: str | None,
) -> str:
    enum_map = _selected_enum_map(stage3)
    issues: list[str] = []
    instructions: list[str] = []
    for dim_key in missing_dim_keys:
        baseline_value = baseline_values.get(dim_key)
        candidate_values = [
            value
            for value in sorted(enum_map.get(dim_key, set()))
            if value != baseline_value
        ]
        candidate_text = ", ".join(candidate_values) if candidate_values else "baseline과 다른 허용 값"
        issues.append(
            f"- R01 baseline 대비 대안값 누락: {dim_key} "
            f"(baseline={baseline_value})",
        )
        instructions.append(
            f"- 최소 1개 이상의 비-baseline 시나리오에서 {dim_key}={candidate_text} 중 하나를 사용하십시오.",
        )
    issue_text = "\n".join(issues) if issues else f"- {baseline_issue or 'baseline 대비 coverage 검사 실패'}"
    instruction_text = "\n".join(instructions)
    return (
        "[검증 실패/ 재생성 필요: baseline_contrast]\n"
        f"{issue_text}\n\n"
        "[Stage4 재생성 지시]\n"
        f"{instruction_text}\n"
        "- 변경된 dimension 조합에 맞춰 title, description, derivation_rationale, "
        "price_direction을 모두 다시 작성하십시오."
    )


def _stage5_duplicate_feedback(
    stage4: Stage4ScenarioSynthesis,
) -> str | None:
    seen: dict[tuple[tuple[str, str], ...], Scenario] = {}
    issues: list[str] = []
    for scenario in stage4.scenarios:
        combo_key = _combo_key(scenario.dimension_values)
        original = seen.get(combo_key)
        if original is None:
            seen[combo_key] = scenario
            continue

        issues.append(
            f"- {scenario.scenario_id} [{scenario.title}]가 "
            f"{original.scenario_id} [{original.title}]와 동일한 Dimension 값 조합을 사용함.",
        )

    if not issues:
        return None
    return (
        "[검증 실패/ 재생성 필요: duplicate]\n"
        + "\n".join(issues)
        + "\n\n[Stage4 재생성 지시]\n"
        + "중복된 시나리오 중 최소 1개의 Dimension 값 조합을 기존 시나리오와 달라지도록 재선정하십시오.\n"
        + "변경된 dimension 조합에 맞춰 title, description, derivation_rationale, "
        + "price_direction을 모두 다시 작성하십시오."
    )


def _stage5_dimension_label_maps(
    template: ScenarioTemplate,
) -> tuple[dict[str, str], dict[str, str]]:
    label_by_key: dict[str, str] = {}
    key_by_label: dict[str, str] = {}
    for dimension in template.ordered_dimensions():
        label = dimension.label or dimension.dim_key
        label_by_key[dimension.dim_key] = label
        key_by_label[label] = dimension.dim_key
    return label_by_key, key_by_label


def _stage5_compatibility_user_prompt(
    stage4: Stage4ScenarioSynthesis,
    template: ScenarioTemplate,
) -> str:
    label_by_key, _ = _stage5_dimension_label_maps(template)
    enum_lines = [
        f"- {dimension.label or dimension.dim_key} ({dimension.dim_key}): "
        f"{', '.join(str(value) for value in dimension.value_enums)}"
        for dimension in template.ordered_dimensions()
    ]
    lines: list[str] = []
    for index, scenario in enumerate(stage4.scenarios, start=1):
        pairs = ", ".join(
            f"{label_by_key.get(key, key)} ({key})='{value}'"
            for key, value in scenario.dimension_values.items()
        )
        lines.append(
            f"- {index} [{scenario.scenario_id} | {scenario.title}]: {pairs}\n"
            f"  narrative: {scenario.description}",
        )
    return (
        "다음 시나리오 조합을 판정하십시오.\n\n"
        "## Dimension enum\n"
        + "\n".join(enum_lines)
        + "\n\n## Scenarios\n"
        + "\n".join(lines)
    )


def _validate_stage5_compatibility_output(
    out: CompatibilityStructuredOutput,
    expected_ids: set[int],
) -> None:
    actual_ids = {item.scenario_id for item in out.items}
    if len(out.items) != len(actual_ids) or actual_ids != expected_ids:
        raise ValueError(
            "compatibility scenario_id 집합 불일치: "
            f"누락={expected_ids - actual_ids}, 여분={actual_ids - expected_ids}",
        )


def _resolve_stage5_dim_key(
    raw_dim: str | None,
    *,
    label_by_key: dict[str, str],
    key_by_label: dict[str, str],
) -> str | None:
    if not raw_dim:
        return None
    text = str(raw_dim).strip()
    if text in label_by_key:
        return text
    if text in key_by_label:
        return key_by_label[text]
    for key, label in label_by_key.items():
        if key in text or label in text:
            return key
    return None


def _stage5_compatibility_overrides(
    out: CompatibilityStructuredOutput,
    stage4: Stage4ScenarioSynthesis,
    template: ScenarioTemplate,
) -> list[Stage5RepairInstruction]:
    label_by_key, key_by_label = _stage5_dimension_label_maps(template)
    repairs: list[Stage5RepairInstruction] = []
    for item in out.items:
        if item.compatible or item.recommended_value_b is None:
            continue
        index = item.scenario_id - 1
        if not 0 <= index < len(stage4.scenarios):
            continue
        scenario = stage4.scenarios[index]
        dim_key = _resolve_stage5_dim_key(
            item.conflict_dim_b,
            label_by_key=label_by_key,
            key_by_label=key_by_label,
        )
        if dim_key is None:
            continue
        current_value = scenario.dimension_values.get(dim_key)
        if current_value is None:
            continue
        repairs.append(
            Stage5RepairInstruction(
                scenario_ref=scenario.scenario_id,
                issue_type="compatibility",
                dim_key=dim_key,
                current_value=str(current_value),
                recommended_value=str(item.recommended_value_b),
                reason=item.reason,
            ),
        )
    return _valid_stage4_overrides(repairs, template)


def _stage5_has_only_unusable_enum_recommendations(
    incompatible: list[CompatibilityItem],
    stage4: Stage4ScenarioSynthesis,
    template: ScenarioTemplate,
) -> bool:
    label_by_key, key_by_label = _stage5_dimension_label_maps(template)
    enum_map = _template_enum_map(template)
    for item in incompatible:
        if item.recommended_value_b is None:
            return False
        index = item.scenario_id - 1
        if not 0 <= index < len(stage4.scenarios):
            return False
        dim_key = _resolve_stage5_dim_key(
            item.conflict_dim_b,
            label_by_key=label_by_key,
            key_by_label=key_by_label,
        )
        if dim_key is None:
            return False
        current_value = stage4.scenarios[index].dimension_values.get(dim_key)
        if current_value is None or str(current_value) != str(item.conflict_value_b):
            return False
        if str(item.recommended_value_b) in enum_map.get(dim_key, set()):
            return False
    return True


def _stage5_compatibility_advice(item: CompatibilityItem, scenario_title: str) -> str:
    prefix = f"[{scenario_title}]: " if scenario_title else ""
    has_pair = bool(
        item.conflict_dim_a
        and item.conflict_value_a
        and item.conflict_dim_b
        and item.conflict_value_b
    )
    if not has_pair:
        return f"{prefix}값 조합이 서로 맞지 않습니다 — {item.reason}".rstrip(" —")

    advice = (
        f"{prefix}'{item.conflict_dim_a}'의 '{item.conflict_value_a}' 값과 "
        f"'{item.conflict_dim_b}'의 '{item.conflict_value_b}' 값은 동시에 가질 수 없습니다."
    )
    if item.reason:
        advice += f" 사유: {item.reason}."
    if item.recommended_value_b:
        advice += (
            f" '{item.conflict_value_b}'을(를) "
            f"'{item.recommended_value_b}'(으)로 바꾸는 것을 권장합니다."
        )
    return advice


def _stage5_compatibility_feedback(
    out: CompatibilityStructuredOutput,
    stage4: Stage4ScenarioSynthesis,
) -> str:
    lines: list[str] = []
    for item in out.items:
        if item.compatible:
            continue
        scenario_title = ""
        index = item.scenario_id - 1
        if 0 <= index < len(stage4.scenarios):
            scenario_title = stage4.scenarios[index].title
        scenario_ref = f"S_{item.scenario_id:02d}"
        lines.append(
            f"- {scenario_ref} {_stage5_compatibility_advice(item, scenario_title)}",
        )
    issues = "\n".join(lines) if lines else "- 조합 호환성 실패"
    return (
        "[검증 실패/ 재생성 필요: compatibility]\n"
        f"{issues}\n\n"
        "[Stage4 재생성 지시]\n"
        "위 권장 변경을 반영해 모순되는 Dimension 값 조합을 재선정하십시오.\n"
        "변경된 dimension 조합에 맞춰 title, description, derivation_rationale, "
        "price_direction을 모두 다시 작성하십시오."
    )


async def _stage5_check_compatibility(
    stage4: Stage4ScenarioSynthesis,
    template: ScenarioTemplate,
    trace_context: TraceContext | None = None,
) -> tuple[bool, str | None, list[Stage5RepairInstruction]]:
    expected_ids = set(range(1, len(stage4.scenarios) + 1))

    def _validate(out: CompatibilityStructuredOutput) -> None:
        _validate_stage5_compatibility_output(out, expected_ids)

    out = await _ainvoke_with_retry(
        stage_label="Stage 5 Compatibility",
        schema_cls=CompatibilityStructuredOutput,
        system_prompt=COMPAT_SYSTEM_PROMPT,
        user_prompt=_stage5_compatibility_user_prompt(stage4, template),
        validate_fn=_validate,
        hard_constraints="",
        trace_context=trace_context,
    )
    if out is None:
        print("  ↳ Stage 5 compatibility fallback: LLM 호출 실패 — 검증 통과로 처리")
        return True, None, []

    incompatible = [item for item in out.items if not item.compatible]
    if not incompatible:
        return True, None, []

    overrides = _stage5_compatibility_overrides(out, stage4, template)
    if not overrides and _stage5_has_only_unusable_enum_recommendations(incompatible, stage4, template):
        # The judge found a contradiction, but its only concrete fixes are outside the template enum.
        # Retrying Stage 4 with text feedback alone tends to loop, so treat this as the best allowed enum choice.
        logger.info(
            "[SCENARIO_GENERATION][stage5] compatibility passed because no enum-actionable repair exists",
        )
        return True, None, []

    return (
        False,
        _stage5_compatibility_feedback(out, stage4),
        overrides,
    )


@log_tool
async def stage5_quick_validate(
    pack: Stage1ContextPack,
    stage3: Stage3ValueSelection,
    stage4: Stage4ScenarioSynthesis,
    template: ScenarioTemplate,
    trace_context: TraceContext | None = None,
) -> tuple[bool, str | None, list[Stage5RepairInstruction]]:
    """Stage 5 진입점 — 빠른 규칙 검증.

    반환: (passed, improvement_suggestions)
    - passed=True  → (True, None, [])
    - passed=False → (False, "<Stage4 재생성 피드백 문자열>", regeneration_overrides)
    """
    selected_dim_keys = [pd.dim_key for pd in stage3.per_dimension]
    contrast = check_baseline_contrast_coverage(
        stage4.scenarios,
        selected_dim_keys,
        baseline_index=0,
    )
    if contrast.baseline_issue or contrast.missing_dimensions:
        feedback = _build_baseline_contrast_feedback(
            stage3=stage3,
            missing_dim_keys=contrast.missing_dimensions,
            baseline_values=contrast.baseline_values,
            baseline_issue=contrast.baseline_issue,
        )
        return False, feedback, []

    duplicate_feedback = _stage5_duplicate_feedback(stage4)
    if duplicate_feedback is not None:
        return False, duplicate_feedback, []

    return await _stage5_check_compatibility(stage4, template, trace_context=trace_context)

# ==============================================
# LangGraph Node Classes
# ==============================================

from apps.agents.scenario_group_agent.subgraphs.scenario_generation.schema import (
    ScenarioGenerationResult,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.state import (
    ScenarioGenerationState,
)


class BuildContextNode(BaseNode):
    async def run(self, state: ScenarioGenerationState) -> dict[str, Any]:
        if state.skip_generation:
            return {}
        if state.event_data is None:
            return {"error": "event_data is required"}
        return {"stage1_context_pack": stage1_build_context_pack(state.event_data)}


class SelectDimensionsNode(BaseNode):
    async def run(
        self,
        state: ScenarioGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error:
            return {}
        if state.event_data is None or state.template is None or state.stage1_context_pack is None:
            return {"error": "scenario generation input is incomplete"}
        return {
            "stage2_dimension_selection": await stage2_select_dimensions(
                state.stage1_context_pack,
                state.event_data,
                state.template,
                trace_context=runtime.context if runtime is not None else None,
            ),
        }


class ReduceValuesNode(BaseNode):
    async def run(
        self,
        state: ScenarioGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error:
            return {}
        if state.template is None or state.stage1_context_pack is None or state.stage2_dimension_selection is None:
            return {"error": "scenario generation stage 2 output is missing"}
        return {
            "stage3_value_selection": await stage3_reduce_values(
                state.stage1_context_pack,
                state.stage2_dimension_selection,
                state.template,
                trace_context=runtime.context if runtime is not None else None,
            ),
        }


class SynthesizeScenariosNode(BaseNode):
    async def run(
        self,
        state: ScenarioGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error:
            return {}
        if state.template is None or state.stage1_context_pack is None or state.stage3_value_selection is None:
            return {"error": "scenario generation stage 3 output is missing"}
        return {
            "stage4_scenario_synthesis": await stage4_synthesize_scenarios(
                state.stage1_context_pack,
                state.stage3_value_selection,
                state.template,
                validation_feedback=state.validation_feedback,
                validation_repairs=state.validation_repairs,
                previous_stage4=state.stage4_scenario_synthesis,
                trace_context=runtime.context if runtime is not None else None,
            ),
        }


class QuickValidateNode(BaseNode):
    async def run(
        self,
        state: ScenarioGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error:
            return {}
        if (
            state.stage1_context_pack is None
            or state.stage3_value_selection is None
            or state.stage4_scenario_synthesis is None
            or state.template is None
        ):
            return {"error": "quick_validate 입력 누락"}

        passed, feedback, repairs = await stage5_quick_validate(
            state.stage1_context_pack,
            state.stage3_value_selection,
            state.stage4_scenario_synthesis,
            state.template,
            trace_context=runtime.context if runtime is not None else None,
        )
        if passed:
            if state.quick_validate_retry_count > 0:
                logger.info(
                    "[SCENARIO_GENERATION][stage5] quick validate passed after retry "
                    f"| retry_count={state.quick_validate_retry_count}",
                )
            return {"validation_feedback": None, "validation_repairs": []}
        next_retry_count = state.quick_validate_retry_count + 1
        logger.info(
            "[SCENARIO_GENERATION][stage5] quick validate failed "
            f"| retry_count={next_retry_count} | feedback={_shorten(feedback or '', 600)}",
        )
        if repairs:
            logger.info(
                "[SCENARIO_GENERATION][stage5] stage4 regeneration recommendations "
                f"| repairs={json.dumps([repair.model_dump(mode='json') for repair in repairs], ensure_ascii=False)}",
            )
        return {
            "validation_feedback": feedback,
            "validation_repairs": repairs,
            "quick_validate_retry_count": next_retry_count,
        }

class ValidateScenariosNode(BaseNode):
    async def run(
        self,
        state: ScenarioGenerationState,
        runtime: Runtime[TraceContext] | None = None,
    ) -> dict[str, Any]:
        if state.skip_generation or state.error:
            return {}
        if (
            state.event_data is None
            or state.stage1_context_pack is None
            or state.stage2_dimension_selection is None
            or state.stage3_value_selection is None
            or state.stage4_scenario_synthesis is None
        ):
            return {"error": "scenario generation stage output is incomplete"}

        stage6 = await stage6_validate(
            state.stage1_context_pack,
            state.stage4_scenario_synthesis,
            trace_context=runtime.context if runtime is not None else None,
        )
        scenario_group_metadata = await stage_generate_scenario_group_metadata(
            state.stage1_context_pack,
            state.event_data,
            state.stage4_scenario_synthesis,
            trace_context=runtime.context if runtime is not None else None,
        )
        event_type_l2_id = int(state.event_data.get("event_type_l2_id") or 0)
        stage4 = state.stage4_scenario_synthesis
        return ScenarioGenerationState(
            scenario_result=ScenarioGenerationResult(
                scenario_group_id=f"scg_{uuid.uuid4().hex[:10]}",
                stage1_context_pack=state.stage1_context_pack,
                stage2_dimension_selection=state.stage2_dimension_selection,
                stage3_value_selection=state.stage3_value_selection,
                stage4_scenario_synthesis=stage4,
                stage5_validation=stage6,
                scenario_group_metadata=scenario_group_metadata,
                cartesian_total=stage4.cartesian_total,
                filtered_by_compatibility=stage4.filtered_by_compatibility,
                scenario_count=len(stage4.scenarios),
                mece_passed=stage6.mece_check.mutually_exclusive,
                mi_event_id=state.event_data.get("mi_event_id"),
                event_type_l1_l2=state.stage1_context_pack.C1_base_event.event_type_l1_l2,
                template_id=str(event_type_l2_id),
            ),
        ).model_dump(include={"scenario_result"}, exclude_none=True, exclude_unset=True)


async def quick_validate_node(state: ScenarioGenerationState) -> dict[str, Any]:
    return await QuickValidateNode()(state)
