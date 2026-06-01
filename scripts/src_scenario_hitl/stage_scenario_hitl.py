"""
Scenario HITL Postprocess (Apply Human Edit + Audit + Narrative Refine + Signpost Attach)
─────────────────────────────────────────────────────────────────
시나리오(Draft) → 사용자 편집(Human Edited) → 머지 → Audit → Narrative refine →
Signpost 생성까지의 Stage A HITL 후속 처리 모음.

후속 단계 4가지:
1) ``apply_human_edit`` : 드래프트 + 사용자 편집본 머지 (delete/add scenario 반영).
2) Audit : compatibility(=forbid 규칙) + MECE(=중복 dimension_values) 검사 후
   .log 텍스트 파일을 항상 저장.
3) Narrative refine : LLM 으로 ``description`` / ``derivation_rationale`` 을 자연
   언어로 재작성 (기계적 표현 ``dimension_id=enum_id`` 금지).
4) ``attach_signposts`` : 시나리오별 Signpost 자동 생성·부착 (LangGraph 노드 또는
   직접 호출 fallback).

진입점 (Stage B 의 ``stage_signpost_hitl`` 와 대칭):
    ``run_scenario_hitl_resume(*, thread_id, storage_root, edited_payload_path, ...)``
        → 디스크 I/O + LangGraph runtime 까지 포함한 Stage A 단일 진입점.
    ``run_scenario_hitl_postprocess(state, *, thread_id, log_path, refine_enabled=True)``
        → 메모리 단계 후처리만 수행 (audit + narrative refine).
"""

from __future__ import annotations

import os
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from _openai_client import (
    get_default_model,
    get_openai_client,
    parse_structured_sync,
)
from domains.interfaces.http.api.v1._runtime import get_runtime
from modules.hitl_manager import apply_human_edit, validate_human_edit_payload
from modules.signpost_binder import attach_signposts


# ══════════════════════════════════════════════════════════════
# Env / Constants
# ══════════════════════════════════════════════════════════════

# Signpost 단계와 동일한 env 그룹을 재사용 (REF_*) — Gateway/모델 관리 일원화.
_REFINE_MODEL: str = os.getenv("REF_MODEL", get_default_model())
_REFINE_MAX_TOKENS: int = int(os.getenv("REF_MAX_TOKENS", "4096"))


# ══════════════════════════════════════════════════════════════
# Template registry loader (stage_integrated_scenario 와 동일 라우팅 사용)
# ══════════════════════════════════════════════════════════════

def _load_template_for_state(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """state 로부터 template 을 로드. 실패 시 None (audit 비활성).

    우선순위:
        1) state.stage2_dimension_selection.template_id
        2) state.stage1_context_pack.C1_base_event.event_type_l1_l2
    """
    template_id = ""
    s2 = state.get("stage2_dimension_selection")
    if isinstance(s2, dict):
        template_id = str(s2.get("template_id") or "").strip()
    if not template_id:
        s1 = state.get("stage1_context_pack")
        if isinstance(s1, dict):
            c1 = s1.get("C1_base_event")
            if isinstance(c1, dict):
                template_id = str(c1.get("event_type_l1_l2") or "").strip()
    if not template_id:
        return None

    try:
        from stage_integrated_scenario import _resolve_template
        return _resolve_template(template_id)
    except Exception:  # noqa: BLE001
        return None


def _dim_label_map(template: Dict[str, Any]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for d in template.get("dimensions", []) or []:
        did = str(d.get("dimension_id", "")).strip()
        if did:
            out[did] = str(d.get("label_ko") or did)
    return out


def _enum_label_map(template: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for d in template.get("dimensions", []) or []:
        did = str(d.get("dimension_id", "")).strip()
        if not did:
            continue
        inner: Dict[str, str] = {}
        for e in d.get("enum", []) or []:
            eid = str(e.get("id", "")).strip()
            if not eid:
                continue
            label = e.get("label") or e.get("label_ko") or eid
            inner[eid] = str(label)
        out[did] = inner
    return out


def _get_scenarios(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    s4 = state.get("stage4_scenario_synthesis")
    if not isinstance(s4, dict):
        return []
    scenarios = s4.get("scenarios")
    if not isinstance(scenarios, list):
        return []
    return scenarios


# ══════════════════════════════════════════════════════════════
# Step 2) Audit — Compatibility (분기 항목 모순) + MECE 위반
# ══════════════════════════════════════════════════════════════

def _scenario_violates_rule(
    dim_values: Dict[str, str], forbid: Dict[str, List[str]]
) -> bool:
    """forbid 의 모든 (dim_id, allowed_values) 쌍이 dim_values 에 매칭되면 위반.

    빈 forbid 는 위반으로 보지 않음(정의되지 않은 규칙).
    """
    if not forbid:
        return False
    for dim_id, forbidden_values in forbid.items():
        actual = dim_values.get(dim_id)
        if actual is None or actual not in (forbidden_values or []):
            return False
    return True


def _detect_compatibility_violations(
    scenarios: List[Dict[str, Any]], template: Dict[str, Any]
) -> List[Dict[str, Any]]:
    rules = template.get("compatibility_rules") or []
    violations: List[Dict[str, Any]] = []
    for scenario in scenarios:
        sid = str(scenario.get("scenario_id", "")).strip()
        dim_values = scenario.get("dimension_values") or {}
        if not isinstance(dim_values, dict):
            continue
        matched: List[Dict[str, Any]] = []
        for rule in rules:
            forbid = rule.get("forbid") or {}
            if _scenario_violates_rule(dim_values, forbid):
                matched.append(
                    {
                        "rule_id": str(rule.get("rule_id", "")),
                        "type": str(rule.get("type", "")),
                        "description": str(rule.get("description", "")),
                        "forbid": forbid,
                    }
                )
        if matched:
            violations.append({"scenario_id": sid, "rules": matched})
    return violations


def _detect_mece_violations(
    scenarios: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """동일 dimension_values 조합을 공유하는 시나리오 그룹 검출."""
    groups: Dict[Tuple[Tuple[str, str], ...], List[str]] = {}
    canonical_values: Dict[Tuple[Tuple[str, str], ...], Dict[str, str]] = {}
    for scenario in scenarios:
        sid = str(scenario.get("scenario_id", "")).strip()
        dim_values = scenario.get("dimension_values") or {}
        if not isinstance(dim_values, dict) or not dim_values:
            continue
        key = tuple(sorted((str(k), str(v)) for k, v in dim_values.items()))
        groups.setdefault(key, []).append(sid)
        canonical_values.setdefault(key, {str(k): str(v) for k, v in dim_values.items()})
    return [
        {
            "scenario_ids": ids,
            "dimension_values": canonical_values[key],
        }
        for key, ids in groups.items()
        if len(ids) >= 2
    ]


def _render_audit_log(
    *,
    thread_id: str,
    template_id: str,
    scenarios: List[Dict[str, Any]],
    template: Optional[Dict[str, Any]],
    compatibility_violations: List[Dict[str, Any]],
    mece_violations: List[Dict[str, Any]],
) -> str:
    """사람이 바로 읽을 수 있는 .log 텍스트 렌더링."""
    dim_label = _dim_label_map(template) if template else {}
    enum_label = _enum_label_map(template) if template else {}

    def _enum_label(dim_id: str, enum_id: str) -> str:
        return enum_label.get(dim_id, {}).get(enum_id, enum_id)

    lines: List[str] = []
    lines.append("=== HITL Scenario Audit Log ===")
    lines.append(f"Thread ID       : {thread_id}")
    lines.append(f"Template ID     : {template_id or '(unknown)'}")
    lines.append(
        f"Generated at    : {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    lines.append(f"Total scenarios : {len(scenarios)}")
    if template is None:
        lines.append(
            "Template load   : FAILED (compatibility 검사를 건너뜀; "
            "REF_TEMPLATE_REGISTRY_PATH 또는 event_type_l1_l2 확인 필요)"
        )
    lines.append("")

    lines.append("== [1] 분기 항목 모순 (Compatibility Violations) ==")
    if template is None:
        lines.append("[skip] 템플릿 로드 실패로 검사 미수행.")
    elif not compatibility_violations:
        lines.append("[ok] 위반 없음.")
    else:
        for item in compatibility_violations:
            sid = item["scenario_id"]
            for rule in item["rules"]:
                lines.append(
                    f"[warn] {sid} : {rule['rule_id']} ({rule['type']})"
                )
                lines.append(f"       사유 : {rule['description']}")
                lines.append("       금지 조합 :")
                for dim_id, values in rule["forbid"].items():
                    dim_kor = dim_label.get(dim_id, dim_id)
                    value_strs = [
                        f"{v} ({_enum_label(dim_id, v)})" for v in values
                    ]
                    lines.append(
                        f"         - {dim_id} ({dim_kor}) ∈ "
                        f"{{ {', '.join(value_strs)} }}"
                    )
                actual = next(
                    (s for s in scenarios if s.get("scenario_id") == sid),
                    {},
                ).get("dimension_values", {})
                lines.append("       시나리오 값 :")
                for dim_id in rule["forbid"].keys():
                    val = actual.get(dim_id, "?")
                    lines.append(
                        f"         - {dim_id}: {val} ({_enum_label(dim_id, val)})"
                    )
    lines.append("")

    lines.append("== [2] MECE 위반 (Duplicate dimension_values) ==")
    if not mece_violations:
        lines.append("[ok] 위반 없음.")
    else:
        for idx, grp in enumerate(mece_violations, start=1):
            ids = ", ".join(grp["scenario_ids"])
            lines.append(f"[warn] group #{idx}: {ids} (동일 조합 공유)")
            for dim_id, val in grp["dimension_values"].items():
                dim_kor = dim_label.get(dim_id, dim_id)
                lines.append(
                    f"         - {dim_id} ({dim_kor}): {val} "
                    f"({_enum_label(dim_id, val)})"
                )
    lines.append("")

    n_compat = sum(len(item["rules"]) for item in compatibility_violations)
    n_mece = len(mece_violations)
    lines.append("== Summary ==")
    lines.append(f"- compatibility violations : {n_compat}건")
    lines.append(f"- MECE violations          : {n_mece}건")
    lines.append("")
    return "\n".join(lines)


def audit_scenarios_and_log(
    state: Dict[str, Any],
    *,
    log_path: Path,
    thread_id: str,
) -> Dict[str, Any]:
    """state 의 시나리오 정합성을 검사하고 .log 파일을 저장한다."""
    scenarios = _get_scenarios(state)
    template = _load_template_for_state(state)
    template_id = ""
    s2 = state.get("stage2_dimension_selection")
    if isinstance(s2, dict):
        template_id = str(s2.get("template_id") or "").strip()

    compatibility_violations: List[Dict[str, Any]] = []
    if template is not None:
        compatibility_violations = _detect_compatibility_violations(
            scenarios, template
        )
    mece_violations = _detect_mece_violations(scenarios)

    log_text = _render_audit_log(
        thread_id=thread_id,
        template_id=template_id,
        scenarios=scenarios,
        template=template,
        compatibility_violations=compatibility_violations,
        mece_violations=mece_violations,
    )

    log_path = Path(log_path).resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(log_text, encoding="utf-8")

    return {
        "log_path": str(log_path),
        "compatibility_violations": compatibility_violations,
        "mece_violations": mece_violations,
        "n_compat_warnings": sum(
            len(item["rules"]) for item in compatibility_violations
        ),
        "n_mece_warnings": len(mece_violations),
    }


# ══════════════════════════════════════════════════════════════
# Step 3) Narrative Refine — LLM 기반 description / derivation_rationale 재작성
# ══════════════════════════════════════════════════════════════

# 명백히 기계적인 표현(예: conflict_duration=1M_under, key='value' 등)
_MACHINE_TOKEN_RE = re.compile(
    r"""[A-Za-z_][A-Za-z0-9_]*\s*=\s*['\"]?[A-Za-z0-9_+\-]+['\"]?"""
)


class _RefinedNarrative(BaseModel):
    """단일 시나리오의 재작성된 narrative."""

    description: str = Field(
        description=(
            "3~5문장의 자연스러운 한국어 시나리오 서술. "
            "절대 'dimension_id=enum_id' 같은 기계적 표현/영문 enum id 를 직접 포함하지 말 것."
        ),
    )
    derivation_rationale: str = Field(
        description=(
            "이 시나리오가 도출된 근거 (2~4문장). dimension/enum 의 한국어 라벨로만 서술. "
            "절대 'conflict_duration=1M_under' 같은 기계적 표현 포함 금지."
        ),
    )


def _stringify_dim_values(
    dim_values: Dict[str, str],
    dim_label: Dict[str, str],
    enum_label: Dict[str, Dict[str, str]],
) -> str:
    parts: List[str] = []
    for dim_id, enum_id in dim_values.items():
        dim_kor = dim_label.get(dim_id, dim_id)
        enum_kor = enum_label.get(dim_id, {}).get(enum_id, enum_id)
        parts.append(f"- {dim_kor}: {enum_kor}")
    return "\n".join(parts) if parts else "(없음)"


_REFINE_SYSTEM = (
    "당신은 멀티시나리오(Scenario Group) 결과의 narrative 를 자연스러운 한국어로 "
    "다듬는 편집자다.\n\n"
    "[절대 규칙]\n"
    "- 출력에는 반드시 'description' 과 'derivation_rationale' 두 필드만 포함하라.\n"
    "- 절대로 다음과 같은 기계적 표현을 출력에 포함하지 마라:\n"
    "  · dimension_id=enum_id (예: conflict_duration=1M_under)\n"
    "  · key='value' 같은 코드 표기, JSON 스니펫, 영문 enum 식별자 직접 노출, "
    "    파이프(|) 나열식 enum 토큰\n"
    "- 'dimension_values' 등 시스템 필드명도 본문에 노출하지 마라.\n"
    "- 영문 enum id 대신, 입력 'dimension_values_human' 에서 제공한 한국어 라벨/표현만 사용하라.\n"
    "- 기존 description 의 사실관계(가격 방향성, 통항/제재 수준 등)는 보존하되, "
    "  표현은 한국어로 자연스럽게 다듬는다.\n"
    "- description 은 3~5문장, derivation_rationale 은 2~4문장으로 작성한다.\n"
)


_REFINE_USER_TEMPLATE = (
    "[Base Event]\n"
    "{base_event_block}\n\n"
    "[Scenario]\n"
    "- scenario_id: {scenario_id}\n"
    "- title: {title}\n"
    "- price_direction: brent={brent}, jkm={jkm}, ttf={ttf}\n\n"
    "[dimension_values_human]  ← 본문에 사용할 한국어 라벨 (영문 id 금지)\n"
    "{dim_values_human}\n\n"
    "[기존 description (참고)]\n"
    "{old_description}\n\n"
    "[기존 derivation_rationale (참고)]\n"
    "{old_rationale}\n\n"
    "위 정보를 바탕으로, description 과 derivation_rationale 을 자연스러운 한국어로 "
    "재작성하라. 기계적 표현(예: conflict_duration=1M_under)을 절대 포함하지 말 것."
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


def _contains_machine_tokens(text: str) -> bool:
    """기계적 표현 잔존 여부(보호용 후처리 검사)."""
    if not text:
        return False
    return bool(_MACHINE_TOKEN_RE.search(text))


def _refine_single_scenario(
    scenario: Dict[str, Any],
    *,
    base_block: str,
    dim_label: Dict[str, str],
    enum_label: Dict[str, Dict[str, str]],
) -> Optional[_RefinedNarrative]:
    """단일 시나리오 narrative 재작성. 실패 시 None 반환(원본 유지)."""
    dim_values = scenario.get("dimension_values") or {}
    if not isinstance(dim_values, dict):
        return None
    price = scenario.get("price_direction") or {}
    user_prompt = _REFINE_USER_TEMPLATE.format(
        base_event_block=base_block,
        scenario_id=scenario.get("scenario_id", ""),
        title=scenario.get("title", ""),
        brent=price.get("brent", "neutral"),
        jkm=price.get("jkm", "neutral"),
        ttf=price.get("ttf", "neutral"),
        dim_values_human=_stringify_dim_values(dim_values, dim_label, enum_label),
        old_description=scenario.get("description", ""),
        old_rationale=scenario.get("derivation_rationale", ""),
    )
    try:
        parsed = parse_structured_sync(
            client=get_openai_client(),
            model=_REFINE_MODEL,
            messages=[
                {"role": "system", "content": _REFINE_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            response_model=_RefinedNarrative,
            max_completion_tokens=_REFINE_MAX_TOKENS,
            env_prefix="REF",
        )
    except Exception as exc:  # noqa: BLE001
        print(
            f"    ↳ refine 실패 ({scenario.get('scenario_id', '?')}): "
            f"{exc.__class__.__name__}: {str(exc)[:160]}"
        )
        return None
    if isinstance(parsed, _RefinedNarrative):
        return parsed
    return _RefinedNarrative.model_validate(parsed.model_dump())


def refine_narratives(state: Dict[str, Any]) -> Dict[str, Any]:
    """시나리오들의 description / derivation_rationale 을 LLM 으로 재작성."""
    new_state = deepcopy(state)
    scenarios = _get_scenarios(new_state)
    if not scenarios:
        return new_state

    template = _load_template_for_state(new_state)
    dim_label = _dim_label_map(template) if template else {}
    enum_label = _enum_label_map(template) if template else {}
    base_block = _base_event_block(new_state)

    refined_count = 0
    rejected_count = 0
    for scenario in scenarios:
        result = _refine_single_scenario(
            scenario,
            base_block=base_block,
            dim_label=dim_label,
            enum_label=enum_label,
        )
        if result is None:
            continue
        if _contains_machine_tokens(result.description) or _contains_machine_tokens(
            result.derivation_rationale
        ):
            rejected_count += 1
            print(
                f"    ↳ refine 결과에 기계적 표현이 잔존하여 원본 유지: "
                f"{scenario.get('scenario_id', '?')}"
            )
            continue
        scenario["description"] = result.description.strip()
        scenario["derivation_rationale"] = result.derivation_rationale.strip()
        refined_count += 1

    print(
        f"  ▸ narrative refine: 재작성 {refined_count}건, 원본 유지 "
        f"{len(scenarios) - refined_count}건 (그 중 기계적 표현 잔존 {rejected_count}건)"
    )
    return new_state


# ══════════════════════════════════════════════════════════════
# Combined Entry Point (in-memory: audit + narrative refine)
# ══════════════════════════════════════════════════════════════

def run_scenario_hitl_postprocess(
    state: Dict[str, Any],
    *,
    thread_id: str,
    log_path: Path,
    refine_enabled: bool = True,
) -> Dict[str, Any]:
    """Stage A 후처리 in-memory 진입점 (apply_human_edit 직후 호출).

    1) Audit : compatibility + MECE 검사 후 .log 저장.
    2) Narrative refine (``refine_enabled=False`` 시 생략).

    반환: 후처리된 state. refine 적용 시 deepcopy 본.
    """
    print("== [scenario-hitl] 1) Audit (compatibility + MECE) ==")
    audit_result = audit_scenarios_and_log(
        state, log_path=log_path, thread_id=thread_id
    )
    print(
        f"  ▸ compat warnings : {audit_result['n_compat_warnings']}, "
        f"MECE warnings : {audit_result['n_mece_warnings']}"
    )
    print(f"  ▸ log saved       : {audit_result['log_path']}")

    print("== [scenario-hitl] 2) Narrative refine (LLM) ==")
    if not refine_enabled:
        print("  ▸ 비활성화(--skip-narrative-refine) — 원본 narrative 유지")
        return state

    return refine_narratives(state)


# ══════════════════════════════════════════════════════════════
# Disk-aware Single Entry Point (Stage B 의 run_signpost_hitl_resume 와 대칭)
# ══════════════════════════════════════════════════════════════

# Post-merge hook signature: receives the merged final_state and returns the
# (possibly updated) final_state. Runs once between apply_human_edit and
# signpost generation, in both the graph-resume path and the fallback path.
PostMergeHook = Callable[[Dict[str, Any]], Dict[str, Any]]


def _normalize_delete_ids(raw: list[str] | str | None) -> set[str]:
    if raw is None:
        return set()
    if isinstance(raw, list):
        return {str(x).strip() for x in raw if str(x).strip()}
    text = str(raw).strip()
    if not text:
        return set()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return {item.strip() for item in text.split(",") if item.strip()}


def _normalize_add_scenario(raw: bool | str | None) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw is None:
        return False
    text = str(raw).strip().lower()
    if text in {"y", "yes", "true", "1"}:
        return True
    if text in {"n", "no", "false", "0", ""}:
        return False
    raise ValueError("add_scenario must be Y/N (or True/False).")


def _load_draft_state(runtime: Any, thread_id: str, snapshot_before: Any) -> Dict[str, Any]:
    """그래프 snapshot → 체크포인트 → 디스크 순으로 draft_state 를 로드."""
    draft_state: Optional[Dict[str, Any]] = None
    if snapshot_before is not None:
        draft_state = snapshot_before.values.get("draft_state")
    if draft_state is None:
        try:
            persisted = runtime.file_checkpointer.load_graph_state(thread_id)
            state = persisted.get("state", {}) if isinstance(persisted, dict) else {}
            draft_state = state.get("draft_state")
            if draft_state is None and state.get("draft_path"):
                draft_state = runtime.file_checkpointer.file_client.read_json(
                    state["draft_path"]
                )
        except Exception:  # noqa: BLE001
            draft_state = None
    if draft_state is None:
        draft_path = runtime.file_checkpointer.resolve_paths(thread_id).draft_path
        draft_state = runtime.file_checkpointer.file_client.read_json(draft_path)
    return draft_state


def run_scenario_hitl_resume(
    *,
    thread_id: str,
    storage_root: str,
    edited_payload: Optional[Dict[str, Any]] = None,
    edited_payload_path: Optional[str] = None,
    delete_scenario_ids: list[str] | str | None = None,
    add_scenario: bool | str | None = None,
    post_merge_hook: Optional[PostMergeHook] = None,
) -> Dict[str, Any]:
    """Stage A (Scenario HITL) 단일 진입점.

    드래프트(`scenarios_draft.json`) 와 사용자 편집본(`scenarios_human_edited.json`)
    을 머지하고, audit + narrative refine 후처리(`post_merge_hook`) 를 수행한 다음,
    LangGraph resume 으로 Signpost 생성을 거쳐 `scenarios_final.json` 까지 저장하는
    Stage A 의 단일 진입점. Stage B 의 ``run_signpost_hitl_resume`` 와 짝을 이룬다.

    Args:
        thread_id: 작업 thread id.
        storage_root: data storage root (``data`` 디렉터리).
        edited_payload: 메모리 상의 편집본 state. 미지정 시 ``edited_payload_path``
            로부터 로드한다.
        edited_payload_path: 편집본 JSON 파일 경로.
        delete_scenario_ids: 삭제할 시나리오 id 목록 (list 또는 "S_01,S_02" 형식).
        add_scenario: 시나리오 1개를 추가할지 여부 (bool 또는 "Y"/"N").
        post_merge_hook: ``apply_human_edit`` 직후·signpost 생성 직전에 1회 호출되는
            훅. 일반적으로 ``run_scenario_hitl_postprocess`` 를 부분 적용해 전달한다.

    Returns:
        ``{"thread_id", "status", "next_nodes", "final_path", "phase"}``
    """
    runtime = get_runtime(storage_root)
    if edited_payload is None:
        if not edited_payload_path:
            raise ValueError("Provide edited_payload or edited_payload_path.")
        edited_payload = runtime.file_checkpointer.file_client.read_json(
            Path(edited_payload_path).resolve()
        )

    validate_human_edit_payload(edited_payload)
    normalized_delete_ids = _normalize_delete_ids(delete_scenario_ids)
    normalized_add_scenario = _normalize_add_scenario(add_scenario)
    config = {"configurable": {"thread_id": thread_id}}
    snapshot_before = None
    try:
        snapshot_before = runtime.app.get_state(config)
    except Exception:  # noqa: BLE001
        snapshot_before = None

    draft_state = _load_draft_state(runtime, thread_id, snapshot_before)

    # Step 1) Apply human edit (draft + edited → merged final_state).
    final_state = apply_human_edit(
        draft_state,
        edited_payload,
        delete_scenario_ids=normalized_delete_ids,
        add_scenario=normalized_add_scenario,
    )

    # Step 2+3) Audit + Narrative refine via post_merge_hook
    #   (hook 은 보통 run_scenario_hitl_postprocess 를 부분 적용해 전달됨).
    if post_merge_hook is not None:
        hook_result = post_merge_hook(final_state)
        if isinstance(hook_result, dict):
            final_state = hook_result

    # Step 4) Signpost attach via LangGraph resume (with disk fallback)
    next_nodes: list[str] = []
    final_path = str(runtime.file_checkpointer.resolve_paths(thread_id).final_path)
    resumed_with_graph = False

    if snapshot_before is not None and getattr(snapshot_before, "next", None):
        try:
            runtime.app.update_state(
                config,
                {
                    "human_edited_state": edited_payload,
                    "delete_scenario_ids": sorted(normalized_delete_ids),
                    "add_scenario": normalized_add_scenario,
                    "final_state": final_state,
                    "phase": "apply_human_edit",
                },
                as_node="apply_human_edit",
            )
            runtime.app.invoke({}, config=config)
            snapshot = runtime.app.get_state(config)
            next_nodes = list(snapshot.next)
            resumed_with_graph = True
            try:
                checkpoint = runtime.file_checkpointer.load_graph_state(thread_id)
                final_path = checkpoint.get("state", {}).get("final_path") or final_path
            except Exception:  # noqa: BLE001
                pass
        except Exception:  # noqa: BLE001
            resumed_with_graph = False

    final_file = Path(final_path)
    if (not resumed_with_graph) or (not final_file.exists()):
        # Process-restart safe fallback when LangGraph in-memory checkpoint is unavailable.
        final_state_with_signposts = attach_signposts(final_state)
        saved = runtime.file_checkpointer.save_final(
            thread_id, final_state_with_signposts, final_path
        )
        runtime.file_checkpointer.save_graph_state(
            thread_id=thread_id,
            phase="completed",
            state={
                "thread_id": thread_id,
                "draft_path": str(
                    runtime.file_checkpointer.resolve_paths(thread_id).draft_path
                ),
                "final_path": str(saved),
                "final_state": final_state_with_signposts,
                "phase": "save_final",
            },
        )
        final_path = str(saved)
        next_nodes = []

    return {
        "thread_id": thread_id,
        "status": "completed",
        "next_nodes": next_nodes,
        "final_path": str(final_path),
        "phase": "completed",
    }
