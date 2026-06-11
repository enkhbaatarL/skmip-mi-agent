"""
HITL Full Flow Orchestrator (Stage A: Scenario → Stage B: Signpost)
─────────────────────────────────────────────────────────────────
한 번의 명령으로 ``generate draft → Stage A (scenario HITL) → Stage B (signpost HITL)``
까지 일괄 실행하는 CLI.

Stage A 와 Stage B 는 동일한 구조의 두 모듈에서 노출된 두 단일 진입점을 호출한다:
    - Stage A : ``stage_scenario_hitl.run_scenario_hitl_resume``
    - Stage B : ``stage_signpost_hitl.run_signpost_hitl_resume``
"""

from __future__ import annotations

import argparse
import json
import shutil
from functools import partial
from pathlib import Path
from typing import Any, Callable, Dict

from domains.interfaces.http.api.v1.generator import run_generator
from stage_scenario_hitl import (
    run_scenario_hitl_postprocess,
    run_scenario_hitl_resume,
)
from stage_signpost_hitl import (
    prepare_signpost_edit_payload,
    run_signpost_hitl_resume,
)


# ══════════════════════════════════════════════════════════════
# File I/O helpers
# ══════════════════════════════════════════════════════════════

def _resolve_path(raw_path: str, *, must_exist: bool = False) -> Path:
    p = Path(raw_path)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    else:
        p = p.resolve()
    if must_exist and not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return p


def _read_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# ══════════════════════════════════════════════════════════════
# CLI arguments
# ══════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run full HITL flow in one command: "
            "generate draft → Stage A (scenario HITL: apply edit + audit + refine + signposts) "
            "→ Stage B (signpost HITL: label/strength/keywords edit + rationale + "
            "likelihood normalize)."
        )
    )
    parser.add_argument(
        "--event-input-path",
        "-i",
        required=True,
        help="Input event JSON path (for draft generation).",
    )
    parser.add_argument(
        "--thread-id",
        "-t",
        required=True,
        help="Thread ID (e.g., thr_lng_demo_002).",
    )
    parser.add_argument(
        "--storage-root",
        "-s",
        default="data",
        help="Storage root directory containing thread outputs. Default: data",
    )
    parser.add_argument(
        "--edited-payload-path",
        "-e",
        default="",
        help=(
            "Stage A edited payload path. "
            "Default: <storage-root>/<thread-id>/scenarios_human_edited.json"
        ),
    )
    parser.add_argument(
        "--signpost-edited-path",
        default="",
        help=(
            "Stage B signpost edited payload path. "
            "Default: <storage-root>/<thread-id>/scenarios_signpost_edited.json"
        ),
    )
    parser.add_argument(
        "--audit-log-path",
        default="",
        help=(
            "Stage A audit log file path. "
            "Default: <storage-root>/<thread-id>/scenarios_audit.log"
        ),
    )
    parser.add_argument(
        "--initial-final-backup-path",
        default="",
        help=(
            "Stage A 결과(`scenarios_final.json`)의 백업 경로. "
            "Stage B 가 scenarios_final.json 을 덮어쓰기 전에 이 경로로 복사한다. "
            "Default: <storage-root>/<thread-id>/scenarios_final_initial.json"
        ),
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip draft generation and use existing draft/human-edited files.",
    )
    parser.add_argument(
        "--auto-resume",
        action="store_true",
        help="Resume immediately without waiting for Enter key confirmation.",
    )
    parser.add_argument(
        "--skip-narrative-refine",
        action="store_true",
        help=(
            "Skip LLM-based narrative refine step in Stage A. Audit log is still saved."
        ),
    )
    parser.add_argument(
        "--skip-signpost-hitl",
        action="store_true",
        help=(
            "Skip Stage B entirely (no edit pause, no rationale refresh, "
            "no likelihood normalization)."
        ),
    )
    parser.add_argument(
        "--skip-rationale-refresh",
        action="store_true",
        help=(
            "Within Stage B, skip LLM-based rationale_ko regeneration. "
            "Likelihood normalization still runs."
        ),
    )
    return parser.parse_args()


# ══════════════════════════════════════════════════════════════
# Stage helpers (parallel handlers for Stage A / Stage B)
# ══════════════════════════════════════════════════════════════

def _pause_for_manual_edit(
    *,
    title: str,
    description: str,
    edited_path: Path,
    auto_resume: bool,
) -> None:
    """편집 대상 파일 경로를 안내하고 사용자의 Enter 입력을 대기."""
    print(f"== {title} ==")
    print(f"  · 편집 파일 : {edited_path}")
    print(description)
    if not auto_resume:
        input("After finishing manual edits, press Enter to continue...")


def _run_stage_a(
    *,
    args: argparse.Namespace,
    thread_dir: Path,
    storage_root: Path,
    draft_path: Path,
    edited_path: Path,
    audit_log_path: Path,
) -> Path:
    """Stage A — scenario draft → human edit → apply/audit/refine/signposts."""
    edited_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(draft_path, edited_path)
    print(f"Draft copied for editing:\n- draft : {draft_path}\n- edited: {edited_path}")

    _pause_for_manual_edit(
        title="2) Stage A — 시나리오 본문 수정 대기",
        description="  · 수정 가능: dimension_values / title / description / etc.",
        edited_path=edited_path,
        auto_resume=args.auto_resume,
    )

    delete_ids = input(
        "Delete scenario IDs (e.g., [S_01, S_02] or S_01,S_02; empty for none): "
    ).strip()
    add_yn = input("Add one scenario? (Y/N): ").strip()

    refine_enabled = not args.skip_narrative_refine
    post_merge_hook: Callable[[Dict[str, Any]], Dict[str, Any]] = partial(
        run_scenario_hitl_postprocess,
        thread_id=args.thread_id,
        log_path=audit_log_path,
        refine_enabled=refine_enabled,
    )

    print("== Stage A — Resume + Postprocess (audit + refine) + Signpost Generation ==")
    resume_result = run_scenario_hitl_resume(
        thread_id=args.thread_id,
        storage_root=str(storage_root),
        edited_payload_path=str(edited_path),
        delete_scenario_ids=delete_ids,
        add_scenario=add_yn,
        post_merge_hook=post_merge_hook,
    )
    print(resume_result)
    print(f"  · audit log    : {audit_log_path}")

    final_path = Path(
        resume_result.get("final_path") or (thread_dir / "scenarios_final.json")
    )
    print(f"  · final output : {final_path}")
    return final_path


def _prepare_signpost_edit_file(
    *,
    final_path: Path,
    signpost_edited_path: Path,
) -> None:
    """``scenarios_final.json`` 의 사본을 사용자 수정용 ``signpost_edited`` 로 작성.

    likelihood_prior 텍스트(very_low/low/...)는 사용자가 수치 조정을 하기 쉽도록
    수치 디폴트로 미리 변환해 둔다 (정규화는 Stage B 최종 단계에서 다시 수행).
    """
    final_state = _read_json(final_path)
    edit_seed = prepare_signpost_edit_payload(final_state)
    signpost_edited_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(signpost_edited_path, edit_seed)
    print(
        "Signpost edit file prepared:\n"
        f"- final  : {final_path}\n"
        f"- edited : {signpost_edited_path}"
    )


def _run_stage_b(
    *,
    args: argparse.Namespace,
    final_path: Path,
    signpost_edited_path: Path,
    initial_final_backup_path: Path,
) -> None:
    """Stage B — signpost human edit → apply/refresh/normalize, save back to final."""
    _prepare_signpost_edit_file(
        final_path=final_path,
        signpost_edited_path=signpost_edited_path,
    )
    _pause_for_manual_edit(
        title="3) Stage B — Signpost / Likelihood 수정 대기",
        description=(
            "  · Signpost 수정 가능 필드 : label_ko / strength / keyword_hints\n"
            "  · 시나리오 가능성 수정   : stage5_validation.likelihood_prior\n"
            "      (수치 또는 very_low/low/medium/high/very_high)"
        ),
        edited_path=signpost_edited_path,
        auto_resume=args.auto_resume,
    )

    print("== Stage B — Signpost edit merge + Rationale refresh + Likelihood normalize ==")
    signpost_result = run_signpost_hitl_resume(
        final_state_path=final_path,
        edited_payload_path=signpost_edited_path,
        refresh_enabled=not args.skip_rationale_refresh,
        backup_path=initial_final_backup_path,
    )
    print(signpost_result)


# ══════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════

def main() -> None:
    args = parse_args()

    storage_root = _resolve_path(args.storage_root, must_exist=False)
    thread_dir = storage_root / args.thread_id
    draft_path = thread_dir / "scenarios_draft.json"

    edited_path = (
        _resolve_path(args.edited_payload_path, must_exist=False)
        if args.edited_payload_path
        else thread_dir / "scenarios_human_edited.json"
    )
    signpost_edited_path = (
        _resolve_path(args.signpost_edited_path, must_exist=False)
        if args.signpost_edited_path
        else thread_dir / "scenarios_signpost_edited.json"
    )
    audit_log_path = (
        _resolve_path(args.audit_log_path, must_exist=False)
        if args.audit_log_path
        else thread_dir / "scenarios_audit.log"
    )
    initial_final_backup_path = (
        _resolve_path(args.initial_final_backup_path, must_exist=False)
        if args.initial_final_backup_path
        else thread_dir / "scenarios_final_initial.json"
    )

    # Step 1) Generate draft (LangGraph) → scenarios_draft.json
    if not args.skip_generate:
        event_input_path = _resolve_path(args.event_input_path, must_exist=True)
        print("== 1) Generate Draft ==")
        gen_result = run_generator(
            event_input_path=str(event_input_path),
            storage_root=str(storage_root),
            thread_id=args.thread_id,
        )
        print(gen_result)
    else:
        print("== 1) Generate Draft (skipped) ==")

    if not draft_path.exists():
        raise FileNotFoundError(
            f"Draft file does not exist: {draft_path}. "
            "Run without --skip-generate or verify thread_id/storage_root."
        )

    # Step 2) Stage A — Scenario HITL
    final_path = _run_stage_a(
        args=args,
        thread_dir=thread_dir,
        storage_root=storage_root,
        draft_path=draft_path,
        edited_path=edited_path,
        audit_log_path=audit_log_path,
    )

    # Step 3) Stage B — Signpost HITL
    if args.skip_signpost_hitl:
        print("== 3) Stage B — Signpost HITL (skipped) ==")
        return

    _run_stage_b(
        args=args,
        final_path=final_path,
        signpost_edited_path=signpost_edited_path,
        initial_final_backup_path=initial_final_backup_path,
    )


if __name__ == "__main__":
    main()
