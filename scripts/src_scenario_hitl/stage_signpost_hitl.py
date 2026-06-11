"""
Signpost HITL Postprocess (Signpost 편집 + rationale 재생성 + likelihood 정규화)
─────────────────────────────────────────────────────────────────
시나리오 HITL + Signpost 생성(`scenarios_final.json`)이 끝난 이후 단 한 번 호출되는
Signpost 단계 HITL 후속 처리 모음.

후속 단계 4가지:
1) Signpost 의 ``label_ko`` / ``strength`` / ``keyword_hints`` 수정 (HITL)
   - 사용자가 ``scenarios_signpost_edited.json`` 을 직접 수정.
2) 수정된 항목을 바탕으로 ``rationale_ko`` 를 LLM 으로 재생성.
   - 시나리오 본문, 새 strength, 새 keyword_hints 를 컨텍스트로 사용.
3) 시나리오 가능성(``stage5_validation.likelihood_prior``) 수정 (HITL)
   - 사용자가 텍스트 5단계(very_low/low/medium/high/very_high) 또는 임의의
     수치(가중치)를 직접 기입.
4) Rule-based 정규화 : 모든 시나리오의 prior ≥ 0 + 합 = 1.

진입점 (Stage A 의 ``stage_scenario_hitl`` 과 대칭):
    ``run_signpost_hitl_resume(*, final_state_path, edited_payload_path, ...)``
        → 디스크 I/O 까지 포함한 Stage B 단일 진입점.
    ``run_signpost_hitl_postprocess(final_state, edited_state, *, refresh_enabled=True)``
        → 메모리 단계 후처리만 수행:
          1) signpost edit 머지 → 2) rationale 재생성 → 3+4) likelihood_prior 정규화.
"""

from __future__ import annotations

import json
import os
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from _openai_client import (
    get_default_model,
    get_openai_client,
    parse_structured_sync,
)


# ══════════════════════════════════════════════════════════════
# Env / Constants
# ══════════════════════════════════════════════════════════════

# Signpost / refine 단계와 동일한 env 그룹(REF_*)을 재사용.
_REFINE_MODEL: str = os.getenv("REF_MODEL", get_default_model())
_REFINE_MAX_TOKENS: int = int(os.getenv("REF_MAX_TOKENS", "2048"))

# stage_integrated_scenario.LikelihoodTier 와 동일 키. 텍스트 prior 를 수치
# 가중치로 환산할 때 사용 (정규화 전 단계의 디폴트 값).
_TIER_TO_WEIGHT: Dict[str, float] = {
    "very_low": 0.05,
    "low": 0.10,
    "medium": 0.30,
    "high": 0.50,
    "very_high": 0.70,
}

# 정규화 결과 소수점 자릿수.
_NORMALIZE_DECIMALS: int = int(os.getenv("REF_LIKELIHOOD_DECIMALS", "4"))


# ══════════════════════════════════════════════════════════════
# Step 1) Apply Signpost human edits (label_ko / strength / keyword_hints)
# ══════════════════════════════════════════════════════════════

_EDITABLE_FIELDS: Tuple[str, ...] = ("label_ko", "strength", "keyword_hints")
_ALLOWED_STRENGTHS: frozenset = frozenset({"STRONG", "MEDIUM", "WEAK"})


def _get_scenarios(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    s4 = state.get("stage4_scenario_synthesis")
    if not isinstance(s4, dict):
        return []
    scenarios = s4.get("scenarios")
    if not isinstance(scenarios, list):
        return []
    return scenarios


def _index_signposts(state: Dict[str, Any]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    """(scenario_id, signpost_id) → signpost dict."""
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for scenario in _get_scenarios(state):
        sid = str(scenario.get("scenario_id", "")).strip()
        for sp in scenario.get("signposts") or []:
            if not isinstance(sp, dict):
                continue
            spid = str(sp.get("signpost_id", "")).strip()
            if not sid or not spid:
                continue
            out[(sid, spid)] = sp
    return out


def _normalize_strength(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    val = str(raw).strip().upper()
    if val in _ALLOWED_STRENGTHS:
        return val
    return None


def _normalize_keyword_hints(raw: Any) -> Optional[List[str]]:
    if raw is None:
        return None
    if not isinstance(raw, list):
        return None
    out: List[str] = []
    for item in raw:
        s = str(item).strip()
        if s:
            out.append(s)
    return out


def apply_signpost_human_edit(
    current_state: Dict[str, Any],
    edited_state: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Tuple[str, str]]]:
    """``edited_state`` 의 signpost 수정 사항을 ``current_state`` 에 머지.

    수정 가능 필드: ``label_ko`` / ``strength`` / ``keyword_hints``.
    그 외 필드(``rationale_ko``/``signpost_class``/``direction`` 등)는 항상 원본 유지.
    매칭은 (scenario_id, signpost_id) 페어로 수행하며, 신규 항목 추가/삭제는 미지원.

    반환:
        - 머지된 새 state (deepcopy)
        - ``[(scenario_id, signpost_id), ...]`` — label_ko / strength / keyword_hints
          중 하나라도 실제로 변경된 signpost 목록(rationale 재생성 대상).
    """
    new_state = deepcopy(current_state)
    current_index = _index_signposts(new_state)
    edited_index = _index_signposts(edited_state)

    changed: List[Tuple[str, str]] = []

    for key, current_sp in current_index.items():
        edited_sp = edited_index.get(key)
        if edited_sp is None:
            continue

        new_label = str(edited_sp.get("label_ko", current_sp.get("label_ko", ""))).strip()
        new_strength = _normalize_strength(edited_sp.get("strength")) or current_sp.get(
            "strength"
        )
        kh = _normalize_keyword_hints(edited_sp.get("keyword_hints"))
        new_keywords = kh if kh is not None else current_sp.get("keyword_hints")

        is_changed = False
        if new_label and new_label != str(current_sp.get("label_ko", "")).strip():
            current_sp["label_ko"] = new_label
            is_changed = True
        if new_strength and new_strength != current_sp.get("strength"):
            current_sp["strength"] = new_strength
            is_changed = True
        if isinstance(new_keywords, list) and new_keywords != current_sp.get("keyword_hints"):
            current_sp["keyword_hints"] = new_keywords
            is_changed = True

        if is_changed:
            changed.append(key)

    return new_state, changed


# ══════════════════════════════════════════════════════════════
# Step 2) Refresh rationale_ko via LLM (only for changed signposts)
# ══════════════════════════════════════════════════════════════


class _RefreshedRationale(BaseModel):
    """단일 signpost 의 재작성된 rationale_ko."""

    rationale_ko: str = Field(
        description=(
            "한국어 1~2문장. 이 signpost 가 시나리오를 어떻게 검증/보강하는지와 "
            "부여된 strength(STRONG/MEDIUM/WEAK)의 근거를 함께 서술. "
            "기계적 표현(dimension_id=enum_id 등) 금지."
        )
    )


_RATIONALE_SYSTEM = (
    "당신은 LNG 멀티시나리오 Signpost 의 'rationale_ko' 편집자다.\n\n"
    "[작성 원칙]\n"
    "- 항상 한국어 1~2문장으로 작성.\n"
    "- 첫째, 이 signpost 가 시나리오(가설)를 어떻게 검증/보강하는지 명시.\n"
    "- 둘째, 부여된 strength(STRONG/MEDIUM/WEAK) 의 근거를 함께 설명.\n"
    "  · STRONG = 'realized' 신호: 시나리오가 사실상 실현됐음을 직접 증명.\n"
    "  · MEDIUM = 'early' 신호 (강): 분명한 초기 신호, 확정은 아님.\n"
    "  · WEAK   = 'early' 신호 (약): 정황적·간접적 초기 신호.\n"
    "- 절대 금지: 'dimension_id=enum_id', 코드/JSON 스니펫, 영문 enum id 직접 노출, "
    "  시스템 필드명(예: dimension_values) 그대로 출력.\n"
    "- 출력은 반드시 'rationale_ko' 단일 필드만 포함.\n"
)


_RATIONALE_USER_TEMPLATE = (
    "[Base Event]\n"
    "{base_event_block}\n\n"
    "[Scenario]\n"
    "- scenario_id: {scenario_id}\n"
    "- title: {title}\n"
    "- description: {description}\n\n"
    "[Signpost (HITL 반영본)]\n"
    "- signpost_id: {signpost_id}\n"
    "- label_ko  : {label_ko}\n"
    "- direction : SUP\n"
    "- strength  : {strength}\n"
    "- keyword_hints: {keyword_hints}\n\n"
    "위 정보를 바탕으로 이 signpost 의 ``rationale_ko`` 를 한국어 1~2문장으로 "
    "재작성하라. label_ko / strength / keyword_hints 가 사람이 수정한 결과이므로, "
    "그에 정합하는 검증·보강 논리와 strength 근거를 함께 담아야 한다."
)


def _base_event_block(state: Dict[str, Any]) -> str:
    s1 = state.get("stage1_context_pack")
    c1 = (s1 or {}).get("C1_base_event") if isinstance(s1, dict) else None
    if not isinstance(c1, dict):
        return "(없음)"
    return (
        f"- title  : {c1.get('title', '')}\n"
        f"- summary: {c1.get('summary', '')}\n"
        f"- driver : {c1.get('driver', '')}"
    )


def _shorten(text: str, limit: int = 600) -> str:
    if not isinstance(text, str):
        return ""
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _refresh_single_rationale(
    scenario: Dict[str, Any],
    signpost: Dict[str, Any],
    *,
    base_block: str,
) -> Optional[str]:
    keyword_hints = signpost.get("keyword_hints") or []
    if not isinstance(keyword_hints, list):
        keyword_hints = []
    user_prompt = _RATIONALE_USER_TEMPLATE.format(
        base_event_block=base_block,
        scenario_id=scenario.get("scenario_id", ""),
        title=scenario.get("title", ""),
        description=_shorten(str(scenario.get("description", "")), 600),
        signpost_id=signpost.get("signpost_id", ""),
        label_ko=str(signpost.get("label_ko", "")).strip(),
        strength=str(signpost.get("strength", "")).strip() or "MEDIUM",
        keyword_hints=", ".join(str(k) for k in keyword_hints) or "(없음)",
    )
    try:
        parsed = parse_structured_sync(
            client=get_openai_client(),
            model=_REFINE_MODEL,
            messages=[
                {"role": "system", "content": _RATIONALE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_model=_RefreshedRationale,
            max_completion_tokens=_REFINE_MAX_TOKENS,
            env_prefix="REF",
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"    ↳ rationale 재생성 실패 ({scenario.get('scenario_id', '?')} / "
            f"{signpost.get('signpost_id', '?')}): "
            f"{exc.__class__.__name__}: {str(exc)[:160]}"
        )
        return None
    obj = parsed if isinstance(parsed, _RefreshedRationale) else _RefreshedRationale.model_validate(
        parsed.model_dump()
    )
    return (obj.rationale_ko or "").strip() or None


def refresh_rationales(
    state: Dict[str, Any],
    *,
    changed_signposts: List[Tuple[str, str]],
) -> Dict[str, Any]:
    """변경된 signpost 들의 ``rationale_ko`` 를 LLM 으로 재생성한다."""
    if not changed_signposts:
        print("  ▸ rationale 재생성: 대상 없음 (변경된 signpost 0건)")
        return state

    new_state = deepcopy(state)
    base_block = _base_event_block(new_state)
    index = _index_signposts(new_state)
    scenario_by_id: Dict[str, Dict[str, Any]] = {
        str(s.get("scenario_id", "")).strip(): s for s in _get_scenarios(new_state)
    }

    refreshed = 0
    failed = 0
    for sid, spid in changed_signposts:
        scenario = scenario_by_id.get(sid)
        sp = index.get((sid, spid))
        if scenario is None or sp is None:
            failed += 1
            continue
        new_rationale = _refresh_single_rationale(scenario, sp, base_block=base_block)
        if new_rationale:
            sp["rationale_ko"] = new_rationale
            refreshed += 1
        else:
            failed += 1
    print(
        f"  ▸ rationale 재생성: 성공 {refreshed}건 / 실패(원본 유지) {failed}건 / "
        f"대상 {len(changed_signposts)}건"
    )
    return new_state


# ══════════════════════════════════════════════════════════════
# Step 3+4) Likelihood prior 수정 + Rule-based 정규화
# ══════════════════════════════════════════════════════════════


def _coerce_prior_value(raw: Any) -> Optional[float]:
    """단일 prior 값을 비음수 float 으로 환산. 실패 시 None.

    - bool 은 거부 (실수로 True/False 가 들어온 경우 방지).
    - 숫자(int/float) 는 그대로 사용 (음수는 0 으로 클립).
    - 문자열은 텍스트 tier 매핑 또는 숫자 문자열 파싱.
    """
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return max(0.0, float(raw))
    if isinstance(raw, str):
        s = raw.strip().lower()
        if not s:
            return None
        if s in _TIER_TO_WEIGHT:
            return _TIER_TO_WEIGHT[s]
        try:
            return max(0.0, float(s))
        except ValueError:
            return None
    return None


def normalize_likelihood_prior(state: Dict[str, Any]) -> Dict[str, Any]:
    """``stage5_validation.likelihood_prior`` 를 rule-based 로 정규화.

    규칙:
        1. 모든 값 ≥ 0 (음수는 0 으로 클립).
        2. 모든 값의 합 = 1 (각 값을 합으로 나눔).
        3. 유효한 prior 가 하나도 없으면 N 개 시나리오에 균등 분배.
        4. 결과는 ``REF_LIKELIHOOD_DECIMALS`` 자릿수로 반올림하되, 누적 반올림 오차는
           마지막 항목에 흡수시켜 합 = 1 을 보장.
    """
    new_state = deepcopy(state)
    s5 = new_state.get("stage5_validation")
    if not isinstance(s5, dict):
        s5 = {}
        new_state["stage5_validation"] = s5

    scenarios = _get_scenarios(new_state)
    scenario_ids = [
        str(s.get("scenario_id", "")).strip()
        for s in scenarios
        if str(s.get("scenario_id", "")).strip()
    ]
    if not scenario_ids:
        print("  ▸ likelihood 정규화: 시나리오가 없어 건너뜀")
        return new_state

    raw_prior = s5.get("likelihood_prior")
    if not isinstance(raw_prior, dict):
        raw_prior = {}

    weights: Dict[str, float] = {}
    for sid in scenario_ids:
        coerced = _coerce_prior_value(raw_prior.get(sid))
        weights[sid] = coerced if coerced is not None else 0.0

    unknown_keys = sorted(k for k in raw_prior.keys() if k not in set(scenario_ids))
    if unknown_keys:
        print(
            f"  ▸ likelihood 정규화: 알 수 없는 시나리오 ID {unknown_keys} 는 무시"
        )

    total = sum(weights.values())
    if total <= 0.0:
        share = 1.0 / len(scenario_ids)
        normalized = {sid: share for sid in scenario_ids}
        print(
            f"  ▸ likelihood 정규화: 유효 prior 없음 → 균등 분배 ({share:.4f} × "
            f"{len(scenario_ids)})"
        )
    else:
        normalized = {sid: w / total for sid, w in weights.items()}

    rounded: Dict[str, float] = {}
    running = 0.0
    last_sid = scenario_ids[-1]
    for sid in scenario_ids[:-1]:
        val = round(normalized[sid], _NORMALIZE_DECIMALS)
        if val < 0.0:
            val = 0.0
        rounded[sid] = val
        running += val
    rounded[last_sid] = round(max(0.0, 1.0 - running), _NORMALIZE_DECIMALS)

    s5["likelihood_prior"] = rounded
    summary = ", ".join(f"{sid}={rounded[sid]:.4f}" for sid in scenario_ids)
    print(f"  ▸ likelihood 정규화 결과: {summary} (합={sum(rounded.values()):.4f})")
    return new_state


def prepare_signpost_edit_payload(state: Dict[str, Any]) -> Dict[str, Any]:
    """``scenarios_signpost_edited.json`` 으로 복사할 사전 가공 페이로드.

    텍스트 형태의 ``likelihood_prior`` 를 수치 기본값으로 미리 변환하여
    사용자가 곧바로 가중치/확률을 조정할 수 있게 한다 (정규화는 최종 단계에서 수행).
    """
    new_state = deepcopy(state)
    s5 = new_state.get("stage5_validation")
    if not isinstance(s5, dict):
        return new_state
    prior = s5.get("likelihood_prior")
    if not isinstance(prior, dict) or not prior:
        return new_state

    coerced: Dict[str, float] = {}
    for sid, val in prior.items():
        c = _coerce_prior_value(val)
        coerced[str(sid)] = round(c, _NORMALIZE_DECIMALS) if c is not None else 0.0
    s5["likelihood_prior"] = coerced
    return new_state


# ══════════════════════════════════════════════════════════════
# Combined Entry Point (in-memory: merge + refresh + normalize)
# ══════════════════════════════════════════════════════════════


def run_signpost_hitl_postprocess(
    final_state: Dict[str, Any],
    edited_state: Dict[str, Any],
    *,
    refresh_enabled: bool = True,
) -> Dict[str, Any]:
    """Stage B 후처리 in-memory 진입점 (signpost 편집 머지 + rationale + 정규화).

    1) Signpost 수정 머지(``label_ko``/``strength``/``keyword_hints``).
    2) 변경된 signpost 의 ``rationale_ko`` 를 LLM 으로 재생성
       (``refresh_enabled=False`` 시 생략).
    3) edited_state 의 ``likelihood_prior`` 가 final_state 의 그것을 덮어쓰며
       이어서 4) rule-based 정규화 (합=1, 모두 ≥ 0).

    반환: 후처리된 새 state (deepcopy 본).
    """
    print("== [signpost-hitl] 1) Signpost edit merge ==")
    merged_state, changed = apply_signpost_human_edit(final_state, edited_state)
    print(
        f"  ▸ 변경된 signpost: {len(changed)}건 "
        f"({[f'{s}/{p}' for s, p in changed][:8]}{'…' if len(changed) > 8 else ''})"
    )

    print("== [signpost-hitl] 2) Rationale 재생성 (LLM) ==")
    if refresh_enabled:
        merged_state = refresh_rationales(merged_state, changed_signposts=changed)
    else:
        print("  ▸ 비활성화(--skip-rationale-refresh) — 원본 rationale 유지")

    print("== [signpost-hitl] 3) Likelihood prior 수정 머지 ==")
    edited_s5 = edited_state.get("stage5_validation") if isinstance(edited_state, dict) else None
    if isinstance(edited_s5, dict) and isinstance(edited_s5.get("likelihood_prior"), dict):
        merged_s5 = merged_state.setdefault("stage5_validation", {})
        merged_s5["likelihood_prior"] = deepcopy(edited_s5["likelihood_prior"])
        print("  ▸ edited_state.likelihood_prior 적용 완료")
    else:
        print("  ▸ edited_state 에 likelihood_prior 없음 — 기존 값 유지")

    print("== [signpost-hitl] 4) Likelihood prior 정규화 (합=1, 모두 ≥ 0) ==")
    merged_state = normalize_likelihood_prior(merged_state)
    return merged_state


# ══════════════════════════════════════════════════════════════
# Disk-aware Single Entry Point (Stage A 의 run_scenario_hitl_resume 와 대칭)
# ══════════════════════════════════════════════════════════════


def _read_json_file(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _write_json_file(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def run_signpost_hitl_resume(
    *,
    final_state_path: str | Path,
    edited_payload: Optional[Dict[str, Any]] = None,
    edited_payload_path: Optional[str | Path] = None,
    refresh_enabled: bool = True,
    backup_path: Optional[str | Path] = None,
    output_path: Optional[str | Path] = None,
) -> Dict[str, Any]:
    """Stage B (Signpost HITL) 단일 진입점.

    Stage A (시나리오 HITL + Signpost 생성) 까지 완료되어 ``scenarios_final.json`` 이
    저장된 상태에서, 사용자가 ``scenarios_signpost_edited.json`` 을 수정한 결과를
    반영해 4단계 후처리(merge → rationale 재생성 → likelihood 머지 → 정규화)를
    실행하고 결과를 디스크에 저장한다. Stage A 의 ``run_scenario_hitl_resume`` 와
    짝을 이루는 Stage B 의 단일 진입점.

    Args:
        final_state_path: 현 ``scenarios_final.json`` (Stage A 결과) 경로.
        edited_payload: 메모리 상의 수정된 state. 미지정 시 ``edited_payload_path``
            로부터 로드한다.
        edited_payload_path: 수정된 state JSON 파일 경로.
        refresh_enabled: ``False`` 면 LLM 기반 ``rationale_ko`` 재생성을 건너뛴다.
        backup_path: 지정 시 후처리 직전의 ``final_state`` 를 해당 경로로 백업한다
            (1차 저장본 보존).
        output_path: 결과 저장 경로. 미지정 시 ``final_state_path`` 를 덮어쓴다.

    Returns:
        ``{"status", "final_path", "backup_path", "output_path"}``
    """
    final_path_obj = Path(final_state_path).resolve()
    if not final_path_obj.exists():
        raise FileNotFoundError(
            f"scenarios_final.json not found at {final_path_obj}. "
            "Signpost HITL stage cannot proceed."
        )

    final_state = _read_json_file(final_path_obj)

    backup_path_obj: Optional[Path] = None
    if backup_path is not None:
        backup_path_obj = Path(backup_path).resolve()
        if backup_path_obj == final_path_obj:
            raise ValueError(
                "backup_path must differ from final_state_path "
                "(otherwise the 1차 저장본 would be overwritten)."
            )
        backup_path_obj.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(final_path_obj, backup_path_obj)
        print(f"  ▸ Stage A 결과 백업 저장 (1차 저장본): {backup_path_obj}")

    if edited_payload is None:
        if not edited_payload_path:
            raise ValueError(
                "Provide edited_payload or edited_payload_path."
            )
        edited_payload = _read_json_file(Path(edited_payload_path).resolve())

    new_state = run_signpost_hitl_postprocess(
        final_state,
        edited_payload,
        refresh_enabled=refresh_enabled,
    )

    out_path_obj = (
        Path(output_path).resolve() if output_path is not None else final_path_obj
    )
    _write_json_file(out_path_obj, new_state)
    print(f"  ▸ Stage B 결과 저장 (scenarios_final.json 갱신): {out_path_obj}")

    return {
        "status": "completed",
        "final_path": str(out_path_obj),
        "output_path": str(out_path_obj),
        "backup_path": str(backup_path_obj) if backup_path_obj else None,
    }
