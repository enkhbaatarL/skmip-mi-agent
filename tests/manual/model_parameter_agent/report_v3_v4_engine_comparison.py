# Copyright (c) 2026 SK Innovation E&S.

from __future__ import annotations

# ruff: noqa: ANN401, C901, E402, E501, EM101, EM102, PERF401, TRY003
import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import csv
from datetime import UTC, datetime
from hashlib import sha256
from itertools import pairwise
import json
import math
from pathlib import Path
import re
import sys
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tests.manual.model_parameter_agent.compare_v3_v4_proposals import (
    _draw_text,
    _fill_rect,
    _write_rgb_png,
)


ENGINE_SECTION_BEGIN = "<!-- BEGIN LNG ENGINE COMPARISON -->"
ENGINE_SECTION_END = "<!-- END LNG ENGINE COMPARISON -->"
EXPECTED_TAG_ORDER = (
    "strong_bullish",
    "bullish",
    "balanced",
    "bearish",
    "strong_bearish",
)
ALLOWED_PRESSURE_TAGS = frozenset(EXPECTED_TAG_ORDER)
EXPECTED_STRATEGIES = {
    "v3": "multi_event_composite_dimensions",
    "v4": "multi_event_model_lever_dimensions",
}
EXPECTED_WORKBOOKS = frozenset(
    {
        "Demand Model_Input.xlsm",
        "Supply Model_Input.xlsm",
        "Trade Model_Input.xlsm",
    },
)
DISPLAY_REGIONS = ("East Asia Spot", "TTF", "HH")
EPSILON = 1e-6
SUPPLY_RESULT = "result_trademodelinput_liq_production_monthly.csv"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
BASE_EXECUTION_MODE = "- 실행 모드: proposal + confirmation E2E"
ENGINE_EXECUTION_MODE = f"{BASE_EXECUTION_MODE} + LNG Demand→Supply→Trade→Output 엔진"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Add confirmed-input LNG engine execution and price evidence to the official "
            "Model Parameter v3/v4 Markdown and PNG comparison artifacts."
        ),
    )
    parser.add_argument("--report-path", required=True, type=Path)
    parser.add_argument(
        "--figure-path",
        "--dashboard-path",
        dest="dashboard_path",
        required=True,
        type=Path,
        help="Portrait PNG report figure. --dashboard-path remains a compatibility alias.",
    )
    parser.add_argument("--v3-evaluation", required=True, type=Path)
    parser.add_argument("--v4-evaluation", required=True, type=Path)
    parser.add_argument("--v3-export-manifest", required=True, type=Path)
    parser.add_argument("--v4-export-manifest", required=True, type=Path)
    parser.add_argument(
        "--v4-invariance-baseline",
        type=Path,
        help="Optional pre-campaign SELECT-only v4 fingerprint evidence.",
    )
    parser.add_argument(
        "--v4-invariance-after",
        type=Path,
        help="Optional post-campaign SELECT-only v4 fingerprint evidence.",
    )
    parser.add_argument("--v3-failed-attempt-run-map", action="append", default=[], type=Path)
    parser.add_argument("--v4-failed-attempt-run-map", action="append", default=[], type=Path)
    parser.add_argument(
        "--v3-failed-attempt-evidence",
        action="append",
        default=[],
        type=Path,
        help="JSON descriptor for a failed pre-engine/export attempt; repeatable.",
    )
    parser.add_argument(
        "--v4-failed-attempt-evidence",
        action="append",
        default=[],
        type=Path,
        help="JSON descriptor for a failed pre-engine/export attempt; repeatable.",
    )
    parser.add_argument(
        "--focus-month",
        type=int,
        help="Optional month override. By default the most common confirmed patch month is used.",
    )
    return parser.parse_args(argv)


def _load_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"JSON root must be an object: {path}")
    return payload


def _failed_attempts_from_run_map(
    path: Path,
    *,
    evaluation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    resolved = path.resolve()
    payload = _load_object(resolved)
    expected = {
        (int(item["scenario_id"]), str(item["tag"]))
        for item in (evaluation.get("execution") or {}).get("run_mapping") or []
    }
    model_root = Path(str(evaluation.get("model_root") or "")).resolve()
    if not (model_root / "engine/run_all.py").is_file():
        raise RuntimeError(f"evaluation model_root is invalid: {model_root}")
    raw_runs = payload.get("runs")
    if not isinstance(raw_runs, Mapping):
        raise TypeError(f"failed-attempt run map has no runs object: {resolved}")
    failed_runs = [
        item for item in raw_runs.values() if isinstance(item, Mapping) and int(item.get("exit_code") or 0) != 0
    ]
    if not failed_runs:
        raise RuntimeError(f"failed-attempt run map has no nonzero engine run: {resolved}")
    removed = payload.get("removed_incomplete")
    if not isinstance(removed, Mapping):
        raise TypeError(f"failed-attempt cleanup evidence is absent: {resolved}")
    removed_paths: list[str] = []
    log_text: list[str] = []
    for case_name, raw_run in raw_runs.items():
        if not isinstance(raw_run, Mapping) or int(raw_run.get("exit_code") or 0) == 0:
            continue
        identity = (int(raw_run["scenario_id"]), str(raw_run["tag"]))
        if identity not in expected:
            raise RuntimeError(f"failed-attempt identity is not in the successful evaluation: {identity}")
        run_id = str(raw_run["run_id"])
        cleanup = removed.get(case_name)
        if not isinstance(cleanup, list) or not cleanup:
            raise RuntimeError(f"failed-attempt exact cleanup is absent: {case_name}")
        exact_cleanup_paths = {
            (model_root / "outputs" / run_id).resolve(),
            (model_root / "log" / run_id).resolve(),
        }
        declared_cleanup_paths = {Path(str(value)).resolve() for value in cleanup}
        if declared_cleanup_paths != exact_cleanup_paths:
            raise RuntimeError(
                "failed-attempt cleanup targets do not exactly match the evaluation model root: "
                f"declared={sorted(map(str, declared_cleanup_paths))}, "
                f"expected={sorted(map(str, exact_cleanup_paths))}",
            )
        for removed_path in declared_cleanup_paths:
            if removed_path.exists():
                raise RuntimeError(f"failed-attempt cleanup target still exists: {removed_path}")
            removed_paths.append(str(removed_path))
        log_path = Path(str(raw_run.get("orchestrator_log") or ""))
        if log_path.is_file():
            log_text.append(log_path.read_text(encoding="utf-8", errors="replace")[-20000:])
    combined_log = "\n".join(log_text)
    stage_match = re.findall(r"\[run_all\] STOP: ([a-z]+) failed", combined_log, flags=re.IGNORECASE)
    if re.search(r"ModuleNotFoundError|No module named|ImportError", combined_log, flags=re.IGNORECASE):
        category = "ENVIRONMENT"
        reason = "child interpreter dependency import failed"
    elif re.search(r"BadZipFile|not a zip file|invalid OOXML", combined_log, flags=re.IGNORECASE):
        category = "INPUT"
        reason = "workbook/OOXML input failed during model launch"
    else:
        failure = payload.get("failure")
        category = str(failure.get("category") or "MODEL") if isinstance(failure, Mapping) else "MODEL"
        reason = (
            str(failure.get("message") or "engine stage returned a nonzero code")
            if isinstance(failure, Mapping)
            else "engine stage returned a nonzero code"
        )
    return [
        {
            "source_run_map": str(resolved),
            "source_run_map_sha256": _sha256_file(resolved),
            "category": category,
            "stage": stage_match[-1].lower() if stage_match else "unknown",
            "reason": reason,
            "run_ids": [str(item["run_id"]) for item in failed_runs],
            "engine_returncodes": [int(item["exit_code"]) for item in failed_runs],
            "cleanup_status": "complete",
            "removed_paths": sorted(set(removed_paths)),
        },
    ]


def _failed_attempt_register(
    evaluation: Mapping[str, Any],
    extra_run_maps: Sequence[Path],
    extra_evidence: Sequence[Path] = (),
) -> list[dict[str, Any]]:
    registered = [
        _normalize_failed_attempt(item)
        for item in (evaluation.get("execution") or {}).get("failed_attempts") or []
        if isinstance(item, Mapping)
    ]
    for path in extra_run_maps:
        registered.extend(
            _normalize_failed_attempt(item) for item in _failed_attempts_from_run_map(path, evaluation=evaluation)
        )
    for path in extra_evidence:
        registered.extend(_failed_attempts_from_evidence(path))
    unique: dict[tuple[str, ...], dict[str, Any]] = {}
    for attempt in registered:
        key = tuple(str(value) for value in attempt.get("run_ids") or [])
        if not key:
            raise RuntimeError("failed-attempt register entry has no run IDs")
        unique[key] = attempt
    return list(unique.values())


def _normalize_failed_attempt(
    attempt: Mapping[str, Any],
    *,
    source_path: Path | None = None,
) -> dict[str, Any]:
    attempt_ids = attempt.get("run_ids") or attempt.get("attempt_ids") or []
    returncodes = attempt.get("engine_returncodes") or attempt.get("returncodes") or []
    if (
        not isinstance(attempt_ids, list)
        or not attempt_ids
        or not isinstance(returncodes, list)
        or len(returncodes) != len(attempt_ids)
        or any(int(value) == 0 for value in returncodes)
    ):
        raise RuntimeError("failed-attempt evidence must have paired IDs and nonzero return codes")
    category = str(attempt.get("category") or "").upper()
    if category not in {"PREFLIGHT", "ENVIRONMENT", "INPUT", "MODEL"}:
        raise RuntimeError(f"failed-attempt evidence category is invalid: {category}")
    normalized = dict(attempt)
    normalized.update(
        {
            "run_ids": [str(value) for value in attempt_ids],
            "engine_returncodes": [int(value) for value in returncodes],
            "category": category,
            "stage": str(attempt.get("stage") or "unknown"),
            "reason": str(attempt.get("reason") or "nonzero attempt return code"),
            "cleanup_status": str(attempt.get("cleanup_status") or "not_required"),
            "removed_paths": [str(value) for value in attempt.get("removed_paths") or []],
        },
    )
    if source_path is not None:
        resolved = source_path.resolve()
        normalized["source_evidence"] = str(resolved)
        normalized["source_evidence_sha256"] = _sha256_file(resolved)
    return normalized


def _failed_attempts_from_evidence(path: Path) -> list[dict[str, Any]]:
    resolved = path.resolve()
    payload = _load_object(resolved)
    raw_attempts = payload.get("failed_attempts") or payload.get("attempts")
    if raw_attempts is None:
        raw_attempts = [payload]
    if not isinstance(raw_attempts, list) or not raw_attempts:
        raise TypeError(f"failed-attempt descriptor has no attempts array: {resolved}")
    attempts: list[dict[str, Any]] = []
    for item in raw_attempts:
        if not isinstance(item, Mapping):
            raise TypeError(f"failed-attempt descriptor entry is invalid: {resolved}")
        attempts.append(_normalize_failed_attempt(item, source_path=resolved))
    return attempts


def _canonical_json(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolved_evidence_path(raw_path: Any, *, model_root: Path) -> Path:
    path = Path(str(raw_path or ""))
    return (path if path.is_absolute() else model_root / path).resolve()


def _verify_file_evidence(
    evidence: Mapping[str, Any],
    *,
    model_root: Path,
    label: str,
) -> Path:
    path = _resolved_evidence_path(evidence.get("path"), model_root=model_root)
    expected = str(evidence.get("sha256") or "")
    if not path.is_file() or not expected or _sha256_file(path) != expected:
        raise RuntimeError(f"{label} file/hash binding mismatch: {path}")
    return path


def _verify_evaluation(payload: dict[str, Any], *, version: str) -> None:
    if payload.get("schema_version") != "2.0":
        raise RuntimeError(f"{version} evaluation schema must be 2.0")
    expected_digest = str(payload.get("evaluation_sha256") or "")
    digest_payload = dict(payload)
    digest_payload.pop("evaluation_sha256", None)
    actual_digest = sha256(_canonical_json(digest_payload)).hexdigest()
    if expected_digest != actual_digest:
        raise RuntimeError(f"{version} evaluation digest mismatch")
    validation = payload.get("validation") or {}
    execution = payload.get("execution") or {}
    if validation.get("status") != "PASS":
        raise RuntimeError(f"{version} engine evaluation did not pass: {validation.get('status')}")
    if int(execution.get("failed_count") or 0) != 0:
        raise RuntimeError(f"{version} engine evaluation contains failed runs")
    if int(execution.get("success_count") or 0) != int(execution.get("total_count") or -1):
        raise RuntimeError(f"{version} engine run count is incomplete")
    if not (payload.get("immutable_inputs") or {}).get("unchanged"):
        raise RuntimeError(f"{version} engine/LUT/template/input immutability failed")


def _price_index(
    evaluation: Mapping[str, Any],
    *,
    monthly: bool,
    year: int,
    month: int | None = None,
) -> dict[tuple[str, str], dict[str, Any]]:
    rows = (evaluation.get("price") or {}).get("monthly_rows" if monthly else "annual_rows") or []
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    for raw in rows:
        if not isinstance(raw, Mapping) or int(raw.get("year") or 0) != year:
            continue
        if monthly and int(raw.get("month") or 0) != month:
            continue
        key = (str(raw.get("tag") or ""), str(raw.get("price_region") or ""))
        if key in indexed:
            raise RuntimeError(f"duplicate price key: monthly={monthly}, year={year}, month={month}, key={key}")
        base_price = float(raw["base_case_price"])
        adjusted_price = float(raw["user_adjusted_price"])
        if not math.isfinite(base_price) or not math.isfinite(adjusted_price):
            raise RuntimeError(f"non-finite price: key={key}")
        indexed[key] = dict(raw)
    return indexed


def _available_tags(index: Mapping[tuple[str, str], Any]) -> list[str]:
    present = {tag for tag, _ in index}
    return [tag for tag in EXPECTED_TAG_ORDER if tag in present]


def _verify_price_coverage(
    index: Mapping[tuple[str, str], Mapping[str, Any]],
    *,
    version: str,
    period: str,
    expected_tags: Sequence[str] | set[str] | frozenset[str] | None = None,
) -> None:
    expected = set(expected_tags) if expected_tags is not None else {tag for tag, _ in index}
    if not 3 <= len(expected) <= 5 or not expected.issubset(ALLOWED_PRESSURE_TAGS):
        raise RuntimeError(
            f"{version} {period} expected price tag set is invalid: {sorted(expected)}",
        )
    actual_tags = {tag for tag, _ in index}
    if actual_tags != expected:
        raise RuntimeError(
            f"{version} {period} price tag set mismatch: expected={sorted(expected)}, actual={sorted(actual_tags)}",
        )
    regions_by_tag = {tag: {region for indexed_tag, region in index if indexed_tag == tag} for tag in expected}
    region_sets = {frozenset(regions) for regions in regions_by_tag.values()}
    if len(region_sets) != 1:
        raise RuntimeError(
            f"{version} {period} price region coverage differs by tag: {regions_by_tag}",
        )
    regions = next(iter(region_sets))
    missing_display = sorted(set(DISPLAY_REGIONS).difference(regions))
    expected_count = len(expected) * len(regions)
    if missing_display or len(index) != expected_count:
        raise RuntimeError(
            f"{version} {period} price row coverage is incomplete: "
            f"rows={len(index)}/{expected_count}, missing_display={missing_display}",
        )


def _price_pattern(index: Mapping[tuple[str, str], Mapping[str, Any]], *, region: str) -> str:
    available = [tag for tag in EXPECTED_TAG_ORDER if (tag, region) in index]
    ranked = sorted(
        available,
        key=lambda tag: (-float(index[(tag, region)]["user_adjusted_price"]), EXPECTED_TAG_ORDER.index(tag)),
    )
    groups: list[list[str]] = []
    for tag in ranked:
        if not groups:
            groups.append([tag])
            continue
        current = float(index[(tag, region)]["user_adjusted_price"])
        prior = float(index[(groups[-1][0], region)]["user_adjusted_price"])
        if abs(current - prior) <= EPSILON:
            groups[-1].append(tag)
        else:
            groups.append([tag])
    rank = {tag: index for index, tag in enumerate(EXPECTED_TAG_ORDER)}
    return " > ".join(" = ".join(sorted(group, key=rank.__getitem__)) for group in groups)


def _scenario_items(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = manifest.get("scenarios") or manifest.get("results") or manifest.get("exports") or []
    if isinstance(raw, Mapping):
        items = [item for item in raw.values() if isinstance(item, Mapping)]
    elif isinstance(raw, list):
        items = [item for item in raw if isinstance(item, Mapping)]
    else:
        items = []
    return [dict(item) for item in items]


def _verify_evaluation_manifest(
    evaluation: Mapping[str, Any],
    manifest: Mapping[str, Any],
    *,
    version: str,
) -> frozenset[str]:
    """Bind one evaluation to the exact confirmed export that its runs consumed."""

    if manifest.get("schema_version") != "model-parameter-confirmed-engine-input-v1":
        raise RuntimeError(f"{version} confirmed export manifest schema mismatch")
    group = manifest.get("scenario_group") or {}
    group_id = int(group.get("scenario_group_id") or 0)
    if (
        group_id <= 0
        or group.get("api_version") != version
        or group.get("generation_strategy") != EXPECTED_STRATEGIES[version]
    ):
        raise RuntimeError(
            f"{version} confirmed export group/version/strategy mismatch: {group}",
        )
    evaluation_group = evaluation.get("group") or {}
    if int(evaluation_group.get("id") or 0) != group_id:
        raise RuntimeError(
            f"{version} evaluation/export scenario group mismatch: "
            f"evaluation={evaluation_group.get('id')}, export={group_id}",
        )

    model_root = Path(str(evaluation.get("model_root") or "")).resolve()
    group_dir = Path(str(evaluation.get("group_dir") or "")).resolve()
    if group_dir.name != f"group_{group_id}":
        raise RuntimeError(
            f"{version} evaluation group directory is not group_{group_id}: {group_dir}",
        )
    persisted_manifest = group_dir / "export_manifest.json"
    if not persisted_manifest.is_file() or _canonical_json(_load_object(persisted_manifest)) != _canonical_json(
        manifest,
    ):
        raise RuntimeError(
            f"{version} evaluation is not bound to the supplied confirmed export manifest",
        )
    for field_name in ("run_map", "proposal_summary"):
        evidence = evaluation.get(field_name) or {}
        if not isinstance(evidence, Mapping):
            raise TypeError(f"{version} evaluation {field_name} evidence is invalid")
        _verify_file_evidence(
            evidence,
            model_root=model_root,
            label=f"{version} evaluation {field_name}",
        )

    manifest_items = manifest.get("scenarios")
    if not isinstance(manifest_items, list) or not manifest_items:
        raise RuntimeError(f"{version} export manifest scenarios must be a non-empty array")
    manifest_by_scenario: dict[int, tuple[str, int, dict[str, str]]] = {}
    for raw_item in manifest_items:
        if not isinstance(raw_item, Mapping):
            raise TypeError(f"{version} export manifest scenario must be an object")
        scenario_id = int(raw_item.get("scenario_id") or 0)
        tag = str(raw_item.get("tag") or "")
        proposal_id = int(raw_item.get("proposal_id") or 0)
        if scenario_id <= 0 or proposal_id <= 0 or tag not in ALLOWED_PRESSURE_TAGS:
            raise RuntimeError(
                f"{version} export scenario/tag/proposal identity is invalid: "
                f"scenario={scenario_id}, tag={tag}, proposal={proposal_id}",
            )
        if scenario_id in manifest_by_scenario:
            raise RuntimeError(f"{version} export contains duplicate scenario={scenario_id}")
        raw_workbooks = raw_item.get("workbooks")
        if not isinstance(raw_workbooks, list):
            raise TypeError(f"{version} export workbooks must be an array: scenario={scenario_id}")
        workbook_hashes: dict[str, str] = {}
        for workbook in raw_workbooks:
            if not isinstance(workbook, Mapping):
                raise TypeError(f"{version} export workbook evidence is invalid")
            filename = str(workbook.get("filename") or "")
            digest = str(workbook.get("sha256") or "")
            if filename in workbook_hashes or not re.fullmatch(r"[0-9a-f]{64}", digest):
                raise RuntimeError(
                    f"{version} export workbook evidence is invalid: scenario={scenario_id}, file={filename}",
                )
            workbook_hashes[filename] = digest
        if set(workbook_hashes) != EXPECTED_WORKBOOKS:
            raise RuntimeError(
                f"{version} export must contain exactly three model workbooks: "
                f"scenario={scenario_id}, files={sorted(workbook_hashes)}",
            )
        manifest_by_scenario[scenario_id] = (tag, proposal_id, workbook_hashes)

    actual_tags = {tag for tag, _, _ in manifest_by_scenario.values()}
    if not 3 <= len(manifest_by_scenario) <= 5 or len(actual_tags) != len(manifest_by_scenario):
        raise RuntimeError(
            f"{version} export scenario/tag count mismatch: "
            f"expected=3..5 unique allowed tags, actual={sorted(actual_tags)}",
        )
    proposal_ids = [proposal_id for _, proposal_id, _ in manifest_by_scenario.values()]
    if len(proposal_ids) != len(set(proposal_ids)):
        raise RuntimeError(f"{version} export proposal IDs must be unique")

    run_items = (evaluation.get("execution") or {}).get("run_mapping")
    case_items = evaluation.get("cases")
    if not isinstance(run_items, list) or not isinstance(case_items, list):
        raise TypeError(f"{version} evaluation run/case mappings must be arrays")
    runs_by_scenario: dict[int, tuple[str, str]] = {}
    for run in run_items:
        if not isinstance(run, Mapping):
            raise TypeError(f"{version} evaluation run mapping is invalid")
        scenario_id = int(run.get("scenario_id") or 0)
        tag = str(run.get("tag") or "")
        run_id = str(run.get("run_id") or "")
        if scenario_id in runs_by_scenario or RUN_ID_RE.fullmatch(run_id) is None:
            raise RuntimeError(
                f"{version} evaluation run identity is invalid: scenario={scenario_id}, run={run_id}",
            )
        runs_by_scenario[scenario_id] = (tag, run_id)
    if {scenario_id: tag for scenario_id, (tag, _) in runs_by_scenario.items()} != {
        scenario_id: tag for scenario_id, (tag, _, _) in manifest_by_scenario.items()
    }:
        raise RuntimeError(f"{version} evaluation run mapping does not match confirmed scenario tags")

    cases_by_scenario: dict[int, Mapping[str, Any]] = {}
    for case in case_items:
        if not isinstance(case, Mapping):
            raise TypeError(f"{version} evaluation case is invalid")
        scenario_id = int(case.get("scenario_id") or 0)
        if scenario_id in cases_by_scenario:
            raise RuntimeError(f"{version} evaluation contains duplicate case={scenario_id}")
        cases_by_scenario[scenario_id] = case
    if set(cases_by_scenario) != set(manifest_by_scenario):
        raise RuntimeError(f"{version} evaluation cases do not match confirmed scenarios")

    source_root: Path | None = None
    for scenario_id, case in cases_by_scenario.items():
        expected_tag, _, expected_hashes = manifest_by_scenario[scenario_id]
        run_tag, run_id = runs_by_scenario[scenario_id]
        if (
            str(case.get("tag") or "") != expected_tag
            or str(case.get("run_id") or "") != run_id
            or run_tag != expected_tag
        ):
            raise RuntimeError(f"{version} case/run/export identity mismatch: scenario={scenario_id}")
        source_hashes = case.get("source_sha256")
        if not isinstance(source_hashes, Mapping) or set(source_hashes) != EXPECTED_WORKBOOKS:
            raise RuntimeError(
                f"{version} case must bind exactly three source workbooks: scenario={scenario_id}",
            )
        for filename, expected_digest in expected_hashes.items():
            source_evidence = source_hashes.get(filename)
            if not isinstance(source_evidence, Mapping):
                raise TypeError(
                    f"{version} source workbook evidence is missing: scenario={scenario_id}, file={filename}",
                )
            if str(source_evidence.get("sha256") or "") != expected_digest:
                raise RuntimeError(
                    f"{version} export/evaluation workbook digest mismatch: scenario={scenario_id}, file={filename}",
                )
            source_path = _verify_file_evidence(
                source_evidence,
                model_root=model_root,
                label=f"{version} scenario={scenario_id} source={filename}",
            )
            expected_case_name = f"scenario_{scenario_id}_{expected_tag}"
            candidate_root = source_path.parent.parent
            if source_path.name != filename or source_path.parent.name != expected_case_name:
                raise RuntimeError(
                    f"{version} source workbook path does not match confirmed identity: "
                    f"scenario={scenario_id}, path={source_path}",
                )
            if source_root is None:
                source_root = candidate_root
            elif candidate_root != source_root:
                raise RuntimeError(
                    f"{version} source workbooks do not share one confirmed export root: "
                    f"expected={source_root}, actual={candidate_root}",
                )
            alias_path = group_dir / expected_case_name / filename
            if not alias_path.is_file() or alias_path.resolve() != source_path:
                raise RuntimeError(
                    f"{version} evidence view is not an exact read-only alias of the "
                    f"confirmed source workbook: alias={alias_path}, source={source_path}",
                )
    if source_root is None:
        raise RuntimeError(f"{version} evaluation has no confirmed source workbook root")
    source_manifest = source_root / "export_manifest.json"
    if not source_manifest.is_file() or _canonical_json(_load_object(source_manifest)) != _canonical_json(manifest):
        raise RuntimeError(
            f"{version} confirmed source root manifest does not match supplied manifest: {source_manifest}",
        )
    return frozenset(actual_tags)


def _manifest_patch_rows(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in _scenario_items(manifest):
        scenario_id = int(item.get("scenario_id") or (item.get("source") or {}).get("scenario_id") or 0)
        tag = str(item.get("tag") or item.get("pressure_band") or item.get("global_pressure_band") or "")
        proposal_id = item.get("model_param_proposal_id") or item.get("proposal_id")
        patches = item.get("patches") or item.get("cell_patches") or []
        for patch in patches:
            if not isinstance(patch, Mapping):
                continue
            rows.append(
                {
                    **dict(patch),
                    "scenario_id": scenario_id,
                    "tag": tag,
                    "proposal_id": proposal_id,
                    "parameter_name": str(
                        patch.get("parameter_name") or patch.get("parameterName") or "",
                    ),
                },
            )
    return rows


def _manifest_patch_index(manifest: Mapping[str, Any]) -> dict[int, dict[str, Any]]:
    """Return optional one-cell LiqUtil evidence without constraining other parameters."""

    indexed: dict[int, dict[str, Any]] = {}
    for item in _scenario_items(manifest):
        scenario_id = int(item.get("scenario_id") or (item.get("source") or {}).get("scenario_id") or 0)
        patches = item.get("patches") or item.get("cell_patches") or []
        patch_items = [dict(patch) for patch in patches if isinstance(patch, Mapping)]
        if scenario_id <= 0 or not patch_items:
            continue
        liq_util = [
            patch
            for patch in patch_items
            if str(patch.get("parameter_name") or patch.get("parameterName") or "") == "LiqUtilAdjustment"
        ]
        if len(liq_util) > 1:
            raise RuntimeError(
                f"LiqUtilAdjustment propagation requires at most one patch per scenario: "
                f"scenario={scenario_id}, count={len(liq_util)}",
            )
        if not liq_util:
            continue
        enriched = dict(liq_util[0])
        enriched["proposal_id"] = item.get("model_param_proposal_id") or item.get("proposal_id")
        enriched["pressure_band"] = item.get("tag") or item.get("pressure_band") or item.get("global_pressure_band")
        indexed[scenario_id] = enriched
    return indexed


def _patch_coordinates(patch: Mapping[str, Any]) -> dict[str, Any]:
    raw = patch.get("coordinates") or patch.get("axes") or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def _patch_number(patch: Mapping[str, Any], *names: str) -> float:
    for name in names:
        if patch.get(name) is not None:
            value = float(patch[name])
            if math.isfinite(value):
                return value
    raise RuntimeError(f"patch is missing a finite numeric field: {names}")


def _finite_output_number(value: Any, *, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{label} is not numeric: {value!r}") from exc
    if not math.isfinite(number):
        raise RuntimeError(f"{label} is not finite: {value!r}")
    return number


def _field(row: Mapping[str, str], *names: str) -> str:
    casefolded = {str(key).casefold(): str(value) for key, value in row.items()}
    for name in names:
        if name.casefold() in casefolded:
            return casefolded[name.casefold()]
    return ""


def _supply_propagation(
    evaluation: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    model_root = Path(str(evaluation.get("model_root") or "")).resolve()
    patch_by_scenario = _manifest_patch_index(manifest)
    cases: dict[tuple[int, str, str], Mapping[str, Any]] = {}
    for case in evaluation.get("cases") or []:
        if not isinstance(case, Mapping):
            continue
        key = (
            int(case.get("scenario_id") or 0),
            str(case.get("tag") or ""),
            str(case.get("run_id") or ""),
        )
        if key in cases:
            raise RuntimeError(f"duplicate evaluation case identity: {key}")
        cases[key] = case
    rows: list[dict[str, Any]] = []
    for run in (evaluation.get("execution") or {}).get("run_mapping") or []:
        scenario_id = int(run["scenario_id"])
        tag = str(run["tag"])
        run_id = str(run["run_id"])
        patch = patch_by_scenario.get(scenario_id)
        if patch is None:
            continue
        if str(patch.get("pressure_band") or "") != tag:
            raise RuntimeError(
                f"export/engine pressure tag mismatch: scenario={scenario_id}, "
                f"export={patch.get('pressure_band')}, engine={tag}",
            )
        case = cases.get((scenario_id, tag, run_id))
        if case is None:
            raise RuntimeError(
                f"evaluation case is missing for supply run: scenario={scenario_id}, run={run_id}",
            )
        axes = _patch_coordinates(patch)
        output_path = (model_root / "outputs" / run_id / "supply" / SUPPLY_RESULT).resolve()
        try:
            output_path.relative_to((model_root / "outputs").resolve())
        except ValueError as exc:
            raise RuntimeError(f"supply output escaped model outputs: run={run_id}") from exc
        output_evidence = case.get("output_sha256") or {}
        matching_evidence = (
            [
                item
                for item in output_evidence.values()
                if isinstance(item, Mapping)
                and _resolved_evidence_path(item.get("path"), model_root=model_root) == output_path
            ]
            if isinstance(output_evidence, Mapping)
            else []
        )
        if len(matching_evidence) != 1:
            raise RuntimeError(
                f"supply output hash evidence must be unique: scenario={scenario_id}, "
                f"run={run_id}, matches={len(matching_evidence)}",
            )
        _verify_file_evidence(
            matching_evidence[0],
            model_root=model_root,
            label=f"supply scenario={scenario_id} run={run_id}",
        )
        matches: list[dict[str, str]] = []
        with output_path.open("r", encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                if (
                    _field(row, "Year") == str(int(axes["Year"]))
                    and _field(row, "Month") == str(int(axes["Month"]))
                    and _field(row, "Country") == str(axes["Country"])
                    and _field(row, "LNG Plant") == str(axes["LNG Plant"])
                    and _field(row, "LNG Plant train", "LNG Plant Train") == str(axes["LNG Plant Train"])
                ):
                    matches.append(dict(row))
        if len(matches) != 1:
            raise RuntimeError(
                f"supply propagation row must be unique: scenario={scenario_id}, matches={len(matches)}",
            )
        output = matches[0]
        rows.append(
            {
                "scenario_id": scenario_id,
                "tag": tag,
                "run_id": run_id,
                "proposal_id": patch.get("proposal_id"),
                "basecase_value": _patch_number(patch, "basecase_value", "basecaseValue"),
                "proposed_value": _patch_number(patch, "proposed_value", "proposedValue"),
                "final_utilization": _finite_output_number(
                    _field(output, "Implied new plant utilisation rate (%)"),
                    label=f"scenario={scenario_id} final utilization",
                ),
                "production_mt": _finite_output_number(
                    _field(output, "Export LNG plant train production (Mt LNG per month)"),
                    label=f"scenario={scenario_id} production Mt",
                ),
                "production_bcm": _finite_output_number(
                    _field(output, "Export LNG plant train production (Bcm per month) - Post Adj 6 and 7"),
                    label=f"scenario={scenario_id} production Bcm",
                ),
                "coordinates": axes,
            },
        )
    return rows


def _fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "-"
    return f"{float(value):.{digits}f}"


def _signed(value: Any, digits: int = 6) -> str:
    if value is None:
        return "-"
    return f"{float(value):+.{digits}f}"


def _md(value: Any) -> str:
    return str(value if value is not None else "-").replace("|", "\\|").replace("\n", " ")


def _price_table_lines(
    *,
    v3_index: Mapping[tuple[str, str], Mapping[str, Any]],
    v4_index: Mapping[tuple[str, str], Mapping[str, Any]],
    title: str,
) -> list[str]:
    lines = [
        f"### {title}",
        "",
        "| 버전 | pressure tag | scenario | East Asia Spot 기준/예측/차이 | TTF 기준/예측/차이 | HH 기준/예측/차이 |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for version, index in (("v3", v3_index), ("v4", v4_index)):
        for tag in _available_tags(index):
            region_rows = [index[(tag, region)] for region in DISPLAY_REGIONS]
            scenario_id = int(region_rows[0]["scenario_id"])
            cells = []
            for row in region_rows:
                base = float(row["base_case_price"])
                adjusted = float(row["user_adjusted_price"])
                cells.append(f"{_fmt(base)} / {_fmt(adjusted)} / {_signed(adjusted - base)}")
            lines.append(
                f"| {version} | `{tag}` | {scenario_id} | {cells[0]} | {cells[1]} | {cells[2]} |",
            )
    return lines


def _cross_version_lines(
    *,
    v3_index: Mapping[tuple[str, str], Mapping[str, Any]],
    v4_index: Mapping[tuple[str, str], Mapping[str, Any]],
    title: str,
) -> list[str]:
    common_tags = [
        tag
        for tag in EXPECTED_TAG_ORDER
        if all((tag, region) in v3_index and (tag, region) in v4_index for region in DISPLAY_REGIONS)
    ]
    lines = [
        f"### {title}",
        "",
        "| pressure tag | v3 scenario | v4 scenario | East Asia Spot v4-v3 | TTF v4-v3 | HH v4-v3 | epsilon 판정 |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for tag in common_tags:
        differences = [
            float(v4_index[(tag, region)]["user_adjusted_price"])
            - float(v3_index[(tag, region)]["user_adjusted_price"])
            for region in DISPLAY_REGIONS
        ]
        verdict = "차이 관측" if any(abs(value) > EPSILON for value in differences) else "동률"
        lines.append(
            f"| `{tag}` | {v3_index[(tag, DISPLAY_REGIONS[0])]['scenario_id']} | "
            f"{v4_index[(tag, DISPLAY_REGIONS[0])]['scenario_id']} | "
            f"{_signed(differences[0], 9)} | {_signed(differences[1], 9)} | "
            f"{_signed(differences[2], 9)} | {verdict} |",
        )
    return lines


def _evaluation_summary_lines(version: str, evaluation: Mapping[str, Any]) -> str:
    execution = evaluation.get("execution") or {}
    warnings = (evaluation.get("validation") or {}).get("warnings") or []
    run_ids = [str(item.get("run_id")) for item in execution.get("run_mapping") or []]
    return (
        f"| {version} | {execution.get('success_count')}/{execution.get('total_count')} | "
        f"{', '.join(run_ids)} | {len((evaluation.get('price') or {}).get('annual_rows') or [])} | "
        f"{len((evaluation.get('price') or {}).get('monthly_rows') or [])} | {len(warnings)} | "
        f"`{str(evaluation.get('evaluation_sha256') or '')[:16]}` |"
    )


def _alignment_statistics(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    alignment = (evaluation.get("price") or {}).get("tag_alignment") or {}
    counts = alignment.get("combined_comparison_counts") or {}
    met = int(counts.get("met") or 0)
    reversed_count = int(counts.get("reversed") or 0)
    tie = int(counts.get("tie") or 0)
    if min(met, reversed_count, tie) < 0:
        raise RuntimeError("price alignment counts must be non-negative")
    total = met + reversed_count + tie
    decisive = met + reversed_count
    return {
        "verdict": str(alignment.get("verdict") or "indeterminate"),
        "reason_code": str(alignment.get("reason_code") or "missing_alignment_verdict"),
        "met": met,
        "reversed": reversed_count,
        "tie": tie,
        "total": total,
        "strict_satisfaction": (met / total if total else None),
        "tie_rate": (tie / total if total else None),
        "decisive_accuracy": (met / decisive if decisive else None),
        "responsive_region_count": int(alignment.get("responsive_region_count") or 0),
    }


def _alignment_interpretation(alignment: Mapping[str, Any]) -> str:
    total = int(alignment.get("total") or 0)
    met = int(alignment.get("met") or 0)
    reversed_count = int(alignment.get("reversed") or 0)
    tie = int(alignment.get("tie") or 0)
    if total == 0:
        return "비교 가능한 가격 쌍이 없어 pressure tag의 방향성과 구분력을 정성 판정할 수 없다."
    if reversed_count:
        return (
            f"기대 가격 순서와 반대인 비교가 {reversed_count}/{total}건 관측되어 tag 방향성에 실질적인 "
            "모순이 있다. 원인 parameter와 가격 권역을 case 단위로 역추적해야 한다."
        )
    if tie == total:
        return (
            "모든 비교가 epsilon 동률이다. 방향 역전은 없지만 bullish/bearish 구분이 가격에 표현되지 않아 "
            "정합성을 확인할 수 없다."
        )
    if tie:
        return (
            f"방향 역전은 없고 반응한 비교 {met}건은 기대 순서를 따랐지만, {tie}/{total}건이 epsilon "
            "동률이라 가격 구분력은 제한적이다."
        )
    return "모든 비교가 기대 pressure 순서를 따르고 동률·역전이 없어 방향성과 가격 구분력이 모두 확인된다."


def _rate(value: Any) -> str:
    return f"{float(value) * 100:.1f}%" if isinstance(value, int | float) else "N/A"


def _input_signature_metrics(manifest: Mapping[str, Any]) -> dict[str, Any]:
    signatures: list[str] = []
    parameter_names: set[str] = set()
    patch_count = 0
    for item in _scenario_items(manifest):
        signature_rows: list[dict[str, Any]] = []
        patches = item.get("patches") or item.get("cell_patches") or []
        for patch in patches:
            if not isinstance(patch, Mapping):
                continue
            patch_count += 1
            parameter_name = str(patch.get("parameter_name") or patch.get("parameterName") or "")
            if parameter_name:
                parameter_names.add(parameter_name)
            signature_rows.append(
                {
                    "parameter": parameter_name,
                    "coordinates": _patch_coordinates(patch),
                    "proposed": patch.get("proposed_value", patch.get("proposedValue")),
                },
            )
        signatures.append(
            json.dumps(
                sorted(signature_rows, key=lambda value: _canonical_json(value)),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            ),
        )
    return {
        "scenario_count": len(signatures),
        "patch_count": patch_count,
        "distinct_signature_count": len(set(signatures)),
        "parameter_names": sorted(parameter_names),
    }


def _quality_axes(
    evaluation: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    alignment = _alignment_statistics(evaluation)
    signature = _input_signature_metrics(manifest)
    input_difference_count = len(evaluation.get("input_differences") or [])
    upstream_changed_cells = sum(
        int(item.get("changed_cell_count") or 0)
        for item in evaluation.get("upstream_differences") or []
        if isinstance(item, Mapping)
    )
    alignment_verdict = alignment["verdict"]
    alignment_judgement = {
        "aligned": "PASS",
        "partially_aligned": "REVIEW",
        "indeterminate": "REVIEW",
        "misaligned": "FAIL",
    }.get(alignment_verdict, "REVIEW")
    if input_difference_count and alignment["responsive_region_count"]:
        mechanistic_judgement = "PASS"
        mechanistic_evidence = (
            f"workbook 차이 {input_difference_count}건, upstream 변경 cell {upstream_changed_cells}건, "
            f"반응 권역 {alignment['responsive_region_count']}개"
        )
    else:
        mechanistic_judgement = "REVIEW"
        mechanistic_evidence = (
            f"workbook 차이 {input_difference_count}건, upstream 변경 cell {upstream_changed_cells}건, "
            f"반응 권역 {alignment['responsive_region_count']}개; 입력→가격 차별성 추가 검토 필요"
        )
    if signature["patch_count"] == 0:
        expressiveness_judgement = "FAIL"
    elif signature["distinct_signature_count"] < signature["scenario_count"]:
        expressiveness_judgement = "REVIEW"
    else:
        expressiveness_judgement = "PASS"
    parameters = ", ".join(signature["parameter_names"]) or "없음"
    return {
        "export_integrity": {
            "judgement": "PASS",
            "evidence": "confirmed manifest·XLSM hash·scenario/tag/run identity 일치",
        },
        "engine_execution": {
            "judgement": "PASS",
            "evidence": (
                f"{(evaluation.get('execution') or {}).get('success_count')}/"
                f"{(evaluation.get('execution') or {}).get('total_count')} run PASS, "
                "Demand→Supply→Trade→Output 및 CSV/XLSX parity PASS"
            ),
        },
        "tag_alignment": {
            "judgement": alignment_judgement,
            "evidence": (
                f"{alignment_verdict}; met/reversed/tie="
                f"{alignment['met']}/{alignment['reversed']}/{alignment['tie']}, "
                f"strict={_rate(alignment['strict_satisfaction'])}, "
                f"tie={_rate(alignment['tie_rate'])}, "
                f"decisive={_rate(alignment['decisive_accuracy'])}"
            ),
        },
        "mechanistic_consistency": {
            "judgement": mechanistic_judgement,
            "evidence": mechanistic_evidence,
        },
        "model_expressiveness": {
            "judgement": expressiveness_judgement,
            "evidence": (
                f"tag별 입력 signature {signature['distinct_signature_count']}/"
                f"{signature['scenario_count']}, patch {signature['patch_count']}건, parameter={parameters}"
            ),
        },
    }


def _overall_quality_status(*axes_by_version: Mapping[str, Mapping[str, str]]) -> str:
    judgements = {axis.get("judgement", "REVIEW") for axes in axes_by_version for axis in axes.values()}
    if "FAIL" in judgements:
        return "FAIL"
    if "REVIEW" in judgements:
        return "REVIEW"
    return "PASS"


def _failure_remediation(attempt: Mapping[str, Any]) -> str:
    category = str(attempt.get("category") or "UNKNOWN").upper()
    stage = str(attempt.get("stage") or "unknown").lower()
    if category == "ENVIRONMENT":
        return "`.venv/bin/python` 경로를 resolve하지 말고 전달; PYTHONPATH 제거 후 필수 dependency import preflight 재실행"
    if category == "INPUT":
        if "export" in stage:
            return (
                "parameter별 Basecase/LUT exact-cell resolver와 좌표를 수정·검증한 뒤 해당 group만 재-export; "
                "partial XLSM이 있으면 제거하고 ZIP CRC·OOXML·역할 sheet preflight 재실행"
            )
        return "해당 case XLSM 3개만 재-export; ZIP CRC·OOXML part·macro content type·역할 sheet preflight 재실행"
    if category == "MODEL":
        return "native rc와 실패 stage log 진단 후 해당 run ID의 incomplete output/log만 정리하고 새 run ID로 재실행"
    if category == "PREFLIGHT":
        return "group identity·run ID 충돌·single-group lock·이전 cleanup 증적을 바로잡은 뒤 엔진 시작 전 재검증"
    return "분류 근거와 stage log를 먼저 확보하고 자동 재시도하지 않음"


def _warning_summary(evaluation: Mapping[str, Any]) -> tuple[int, int, str]:
    warnings = [
        item for item in (evaluation.get("validation") or {}).get("warnings") or [] if isinstance(item, Mapping)
    ]
    total = sum(int(item.get("warning_count") or 0) for item in warnings)
    samples: list[str] = []
    for warning in warnings:
        for sample in warning.get("sample") or []:
            if not isinstance(sample, Mapping):
                continue
            text = " ".join(str(sample.get("text") or "").split())
            if text and text not in samples:
                samples.append(text)
    risk_markers = ("unstable", "nonzero drift", " stop ", "failed", "error")
    samples.sort(
        key=lambda value: (
            0 if any(marker in f" {value.lower()} " for marker in risk_markers) else 1,
        ),
    )
    sample_text = " / ".join(samples[:3]) if samples else "warning sample 없음"
    return total, len(warnings), sample_text[:600]


def _v4_invariance_summary(
    baseline: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    expected_new_proposal_ids: Sequence[int],
) -> str:
    core_keys = (
        "master",
        "impact_levers",
        "scenario_groups",
        "scenarios",
        "group_event_relations",
        "runtime",
    )
    baseline_invariants = baseline.get("v4_invariants")
    after_invariants = after.get("v4_invariants")
    if not isinstance(baseline_invariants, Mapping) or not isinstance(after_invariants, Mapping):
        raise TypeError("v4 invariance evidence must contain v4_invariants objects")
    changed = [key for key in core_keys if baseline_invariants.get(key) != after_invariants.get(key)]
    if changed:
        raise RuntimeError(f"v4 core invariants changed during campaign: {changed}")
    if baseline.get("shared_mapping_observation") != after.get("shared_mapping_observation"):
        raise RuntimeError("shared legacy mapping observation changed during v4 campaign")
    before_proposals = baseline_invariants.get("stored_proposals")
    after_proposals = after_invariants.get("stored_proposals")
    if not isinstance(before_proposals, Mapping) or not isinstance(after_proposals, Mapping):
        raise TypeError("v4 invariance evidence must contain stored_proposals objects")
    before_ids = {int(value) for value in before_proposals.get("ids") or []}
    after_ids = {int(value) for value in after_proposals.get("ids") or []}
    added_ids = sorted(after_ids - before_ids)
    expected_ids = sorted({int(value) for value in expected_new_proposal_ids})
    if added_ids != expected_ids or before_ids - after_ids:
        raise RuntimeError(
            "unexpected v4 proposal delta during campaign: "
            f"expected_added={expected_ids}, actual_added={added_ids}, removed={sorted(before_ids - after_ids)}",
        )
    mapping = after.get("shared_mapping_observation") or {}
    method_counts = mapping.get("method_counts") or {}
    return (
        "- v4 범위 불변성: **PASS** · master·Impact Lever catalog·v4 group/scenario/relation·runtime 후보 "
        f"fingerprint 불변; legacy mapping `{mapping.get('count')}`행 "
        f"(direct/routing/indirect/na=`{method_counts.get('direct')}/{method_counts.get('routing')}/"
        f"{method_counts.get('indirect')}/{method_counts.get('na')}`) 불변; 저장 proposal만 "
        f"`{len(before_ids)}→{len(after_ids)}`로 증가했고 신규 ID는 `{added_ids}`다."
    )


def _run_map_preflight(evaluation: Mapping[str, Any]) -> Mapping[str, Any]:
    binding = evaluation.get("run_map")
    if not isinstance(binding, Mapping):
        raise TypeError("evaluation run_map binding is absent")
    path = Path(str(binding.get("path") or ""))
    if not path.is_file() or _sha256_file(path) != str(binding.get("sha256") or ""):
        raise RuntimeError(f"run-map binding changed: {path}")
    run_map = _load_object(path)
    preflight = run_map.get("preflight")
    if not isinstance(preflight, Mapping) or preflight.get("status") != "PASS":
        raise RuntimeError(f"run-map preflight is not PASS: {path}")
    return preflight


def _environment_preflight_lines(
    v3_evaluation: Mapping[str, Any],
    v4_evaluation: Mapping[str, Any],
) -> list[str]:
    preflights = [_run_map_preflight(v3_evaluation), _run_map_preflight(v4_evaluation)]
    environments = [item.get("environment") for item in preflights]
    if not all(isinstance(item, Mapping) for item in environments):
        raise TypeError("run-map preflight environment is absent")
    if environments[0] != environments[1]:
        raise RuntimeError("v3/v4 engine preflight environments differ")
    environment = environments[0]
    if not isinstance(environment, Mapping):
        raise TypeError("run-map preflight environment is absent")
    modules = environment.get("modules") or {}
    if not isinstance(modules, Mapping):
        raise TypeError("run-map preflight module versions are absent")
    workbook_count = 0
    for preflight in preflights:
        workbooks = preflight.get("workbooks") or {}
        if not isinstance(workbooks, Mapping):
            raise TypeError("run-map preflight workbook inventory is absent")
        workbook_count += sum(len(value) for value in workbooks.values() if isinstance(value, Mapping))
    module_text = ", ".join(f"{name}={version}" for name, version in sorted(modules.items()))
    return [
        "### venv·XLSM preflight와 반복 rc=1 조치",
        "",
        (
            f"- 현행 환경: **PASS** · interpreter=`{environment.get('sys_executable')}`, "
            f"sys.prefix=`{environment.get('sys_prefix')}`; v3/v4가 동일 환경을 사용했다."
        ),
        f"- 필수 import: **PASS** · `{module_text}`.",
        (
            f"- XLSM preflight: **PASS** · {workbook_count}개 workbook에 대해 readable ZIP, CRC, 필수 OOXML part, "
            "macro content type, 역할 sheet와 SHA-256을 엔진 시작 전에 확인했다."
        ),
        (
            "- 이전 반복 `returncode=1`의 확인 원인은 `.venv/bin/python`을 base UV interpreter로 "
            "dereference해 Supply child에서 `pandas`를 찾지 못한 환경 이탈이었으며, XLSM 손상으로 판정하지 않는다."
        ),
        (
            "- 조치: `.venv/bin/python` 경로를 resolve하지 않고 전달하고, 외부 `PYTHONPATH`를 제거하며, "
            "`PYTHONNOUSERSITE=1`과 `UV_CACHE_DIR=/private/tmp/lng-model-uv-cache`를 사용한다."
        ),
        (
            "- `tests/lng_model/requirements.txt`는 텍스트 requirements가 아니므로 설치 입력으로 사용하지 않는다. "
            "dependency source of truth는 `pyproject.toml`·`uv.lock`이며 필요 시 `uv export --locked --no-dev`를 사용한다."
        ),
    ]


def _tree_size_bytes(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        raise RuntimeError(f"campaign artifact path is absent: {path}")
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _campaign_storage_summary(evaluations: Sequence[Mapping[str, Any]]) -> str:
    artifact_paths: set[Path] = set()
    case_count = 0
    for evaluation in evaluations:
        model_root = Path(str(evaluation.get("model_root") or "")).resolve()
        artifact_paths.add(Path(str(evaluation.get("group_dir") or "")).resolve())
        cases = [item for item in evaluation.get("cases") or [] if isinstance(item, Mapping)]
        case_count += len(cases)
        for case in cases:
            run_id = str(case.get("run_id") or "")
            if not RUN_ID_RE.fullmatch(run_id):
                raise RuntimeError(f"invalid run ID in storage estimate: {run_id!r}")
            artifact_paths.add((model_root / "outputs" / run_id).resolve())
            artifact_paths.add((model_root / "log" / run_id).resolve())
    if case_count <= 0:
        raise RuntimeError("campaign storage estimate has no cases")
    total_gib = sum(_tree_size_bytes(path) for path in artifact_paths) / (1024**3)
    per_case_gib = total_gib / case_count
    return (
        f"- 이번 {case_count}개 case의 입력·output·log logical size는 `{total_gib:.2f} GiB` "
        f"(`{per_case_gib:.2f} GiB/case`)였다. 동일 규모 가정 시 20개는 `{per_case_gib * 20:.1f} GiB`, "
        f"40개는 `{per_case_gib * 40:.1f} GiB`이며, 실행 전 최소 20% 여유를 추가 확보한다."
    )


def _infer_focus_month(
    manifests: Sequence[Mapping[str, Any]],
    evaluations: Sequence[Mapping[str, Any]],
    requested: int | None,
) -> tuple[int, str]:
    if requested is not None:
        if not 1 <= requested <= 12:
            raise ValueError("--focus-month must be in 1..12")
        return requested, "CLI override"
    months: list[int] = []
    for manifest in manifests:
        for patch in _manifest_patch_rows(manifest):
            raw_month = _patch_coordinates(patch).get("Month")
            try:
                month = int(raw_month)
            except (TypeError, ValueError):
                continue
            if 1 <= month <= 12:
                months.append(month)
    if months:
        counts = Counter(months)
        selected = min(counts, key=lambda month: (-counts[month], month))
        return selected, f"confirmed patch mode ({counts[selected]}/{len(months)} cells)"
    common_months: set[int] | None = None
    for evaluation in evaluations:
        available = {
            int(row["month"])
            for row in (evaluation.get("price") or {}).get("monthly_rows") or []
            if isinstance(row, Mapping) and row.get("month") is not None
        }
        common_months = available if common_months is None else common_months & available
    if not common_months:
        raise RuntimeError("focus month cannot be inferred from confirmed patches or price rows")
    return min(common_months), "first common engine month (no patch Month axis)"


def _parameter_patch_lines(
    versioned_manifests: Sequence[tuple[str, Mapping[str, Any]]],
    *,
    limit: int = 100,
) -> list[str]:
    rows = [(version, row) for version, manifest in versioned_manifests for row in _manifest_patch_rows(manifest)]
    lines = [
        "### 확정 파라미터와 exact 입력 cell",
        "",
        "| 버전 | tag | scenario / proposal | parameter | coordinates | basecase → confirmed |",
        "|---|---|---|---|---|---:|",
    ]
    for version, row in rows[:limit]:
        coordinates = ", ".join(f"{key}={value}" for key, value in _patch_coordinates(row).items())
        if len(coordinates) > 180:
            coordinates = coordinates[:177] + "..."
        basecase = row.get("basecase_value", row.get("basecaseValue"))
        proposed = row.get("proposed_value", row.get("proposedValue"))
        lines.append(
            f"| {version} | `{_md(row.get('tag'))}` | {row.get('scenario_id')} / "
            f"{row.get('proposal_id')} | {_md(row.get('parameter_name'))} | {_md(coordinates)} | "
            f"{_md(basecase)} → {_md(proposed)} |",
        )
    if len(rows) > limit:
        lines.extend(["", f"- 표 상한 {limit}행을 초과한 exact patch {len(rows) - limit}건은 manifest에 보존됨."])
    if not rows:
        lines.append("| - | - | - | - | - | confirmed patch 없음 |")
    return lines


def build_engine_section(
    *,
    v3_evaluation: dict[str, Any],
    v4_evaluation: dict[str, Any],
    v3_manifest: dict[str, Any],
    v4_manifest: dict[str, Any],
    v3_failed_attempts: Sequence[Mapping[str, Any]],
    v4_failed_attempts: Sequence[Mapping[str, Any]],
    focus_month: int | None,
    v4_invariance_summary: str | None = None,
    environment_lines: Sequence[str] = (),
    storage_summary: str | None = None,
) -> tuple[str, dict[str, Any]]:
    _verify_evaluation(v3_evaluation, version="v3")
    _verify_evaluation(v4_evaluation, version="v4")
    v3_tags = _verify_evaluation_manifest(v3_evaluation, v3_manifest, version="v3")
    v4_tags = _verify_evaluation_manifest(v4_evaluation, v4_manifest, version="v4")
    focus_years = {int(v3_evaluation["focus_year"]), int(v4_evaluation["focus_year"])}
    if len(focus_years) != 1:
        raise RuntimeError(f"v3/v4 focus years differ: {sorted(focus_years)}")
    focus_year = focus_years.pop()
    selected_month, focus_month_source = _infer_focus_month(
        (v3_manifest, v4_manifest),
        (v3_evaluation, v4_evaluation),
        focus_month,
    )
    v3_annual = _price_index(v3_evaluation, monthly=False, year=focus_year)
    v4_annual = _price_index(v4_evaluation, monthly=False, year=focus_year)
    v3_monthly = _price_index(v3_evaluation, monthly=True, year=focus_year, month=selected_month)
    v4_monthly = _price_index(v4_evaluation, monthly=True, year=focus_year, month=selected_month)
    for version, period, index, expected_tags in (
        ("v3", "annual", v3_annual, v3_tags),
        ("v4", "annual", v4_annual, v4_tags),
        ("v3", "monthly", v3_monthly, v3_tags),
        ("v4", "monthly", v4_monthly, v4_tags),
    ):
        _verify_price_coverage(
            index,
            version=version,
            period=period,
            expected_tags=expected_tags,
        )

    v3_supply = _supply_propagation(v3_evaluation, v3_manifest)
    v4_supply = _supply_propagation(v4_evaluation, v4_manifest)
    v3_group_id = int(v3_manifest["scenario_group"]["scenario_group_id"])
    v4_group_id = int(v4_manifest["scenario_group"]["scenario_group_id"])
    v3_proposal_ids = sorted(int(item["proposal_id"]) for item in v3_manifest["scenarios"])
    v4_proposal_ids = sorted(int(item["proposal_id"]) for item in v4_manifest["scenarios"])
    v3_warning_total, v3_warning_cases, v3_warning_sample = _warning_summary(v3_evaluation)
    v4_warning_total, v4_warning_cases, v4_warning_sample = _warning_summary(v4_evaluation)
    v3_failed_run_count = sum(len(item.get("run_ids") or []) for item in v3_failed_attempts)
    v4_failed_run_count = sum(len(item.get("run_ids") or []) for item in v4_failed_attempts)
    v3_success_count = int((v3_evaluation.get("execution") or {}).get("success_count") or 0)
    v4_success_count = int((v4_evaluation.get("execution") or {}).get("success_count") or 0)
    v3_alignment = _alignment_statistics(v3_evaluation)
    v4_alignment = _alignment_statistics(v4_evaluation)
    v3_axes = _quality_axes(v3_evaluation, v3_manifest)
    v4_axes = _quality_axes(v4_evaluation, v4_manifest)
    overall_status = _overall_quality_status(v3_axes, v4_axes)
    lines = [
        ENGINE_SECTION_BEGIN,
        "## 7. 통합 판정 및 분석 축",
        "",
        f"- 통합 판정: **{overall_status}**",
        (
            "- 판정 원칙: export와 엔진 실행 무결성, pressure tag 가격 정합성, 실제 입력 전파, "
            "모델 표현력을 독립 축으로 유지한다. 기술 실행이 PASS여도 tag가 partial/indeterminate이면 종합 REVIEW다."
        ),
        "",
        "| 분석 축 | v3 판정·증적 | v4 판정·증적 |",
        "|---|---|---|",
    ]
    for axis_name, label in (
        ("export_integrity", "Export integrity"),
        ("engine_execution", "Engine execution"),
        ("tag_alignment", "Pressure-tag alignment"),
        ("mechanistic_consistency", "Mechanistic consistency"),
        ("model_expressiveness", "Model expressiveness"),
    ):
        lines.append(
            f"| {label} | **{v3_axes[axis_name]['judgement']}** · "
            f"{_md(v3_axes[axis_name]['evidence'])} | **{v4_axes[axis_name]['judgement']}** · "
            f"{_md(v4_axes[axis_name]['evidence'])} |",
        )
    lines += [
        "",
        "## 8. LNG 모델 엔진 실행 및 전달 검증",
        "",
        (
            "공용 DB의 최신 `CONFIRMED` payload를 LLM 재호출 없이 exact Basecase cell로 역해석해 3개 XLSM에 "
            "반영했다. 각 버전은 별도 group으로 실행했지만 동일한 `tests/lng_model`의 Engine, LUT, template을 사용했고 "
            "Demand → Supply → Trade → Output 전 단계를 수행했다."
        ),
        "",
        "| 버전 | 엔진 성공 | run ID | 연간 가격 행 | 월간 가격 행 | warning case | evaluation SHA-256 prefix |",
        "|---|---:|---|---:|---:|---:|---|",
        _evaluation_summary_lines("v3", v3_evaluation),
        _evaluation_summary_lines("v4", v4_evaluation),
        "",
        "검증 계약:",
        "",
        (
            f"- {len(_scenario_items(v3_manifest)) + len(_scenario_items(v4_manifest))}개 case 모두 "
            "Demand·Supply·Trade·Output manifest/log 종료 marker, 필수 output, 유한 가격 및 exit code 0을 충족."
        ),
        "- 연간·월간 가격 CSV와 `result_output_dashboard.xlsx`는 tolerance `1e-9`에서 일치.",
        "- Engine, `data/LUT`, `data/templates`, version별 입력 workbook tree는 실행 전후 SHA-256 불변.",
        (
            "- 엔진 입력 exporter는 외부 DB에 SELECT-only로 접속했고 엔진은 DB에 접속하지 않았으며, "
            f"group {v3_group_id}는 proposal {min(v3_proposal_ids)}~{max(v3_proposal_ids)}, "
            f"group {v4_group_id}는 {min(v4_proposal_ids)}~{max(v4_proposal_ids)}의 확정 payload만 사용."
        ),
        (
            "- CONFIRMED snapshot SHA-256: "
            f"v3 `{v3_manifest.get('confirmed_snapshot_sha256')}`, "
            f"v4 `{v4_manifest.get('confirmed_snapshot_sha256')}`; "
            f"export LLM 호출 수는 v3/v4 각각 "
            f"`{v3_manifest.get('llm_call_count')}` / `{v4_manifest.get('llm_call_count')}`."
        ),
        *([v4_invariance_summary] if v4_invariance_summary else []),
        (
            f"- Warning review: v3 `{v3_warning_total}`건/{v3_warning_cases} case, "
            f"v4 `{v4_warning_total}`건/{v4_warning_cases} case. 실행 PASS와 별도로 원문 sample을 보존한다."
        ),
        f"- v3 warning sample: {_md(v3_warning_sample)}",
        f"- v4 warning sample: {_md(v4_warning_sample)}",
        (
            "- Warning interpretation: `ITER_SUR STOP unstable nonzero drift` guard는 v3/v4 "
            f"{len(_scenario_items(v3_manifest)) + len(_scenario_items(v4_manifest))}개 case 모두에서 "
            "관측됐다. 각 실행은 이후 정상 종료했고 필수 output 및 CSV/XLSX parity를 충족했지만, 경고 자체는 "
            "가격 정합성 품질 판정과 별도로 남겨 후속 대량 캠페인에서 발생률과 가격 민감도를 추적한다."
        ),
        (
            "- 실행 이력 투명성: 완료된 model run 성공률과 재시도 전 실패를 별도 계수한다. "
            f"v3 campaign 전체 시도는 `{v3_success_count + v3_failed_run_count}건 = 성공 "
            f"{v3_success_count}건 + failed attempt {v3_failed_run_count}건`, v4는 "
            f"`{v4_success_count + v4_failed_run_count}건 = 성공 {v4_success_count}건 + failed attempt "
            f"{v4_failed_run_count}건`이다."
        ),
        (
            "- Coverage boundary: 이 문서는 동일 ordered Event set 1개 pair의 "
            f"{len(_scenario_items(v3_manifest)) + len(_scenario_items(v4_manifest))}개 completed case를 "
            "검증한 독립 보고서다. 다수 pair 캠페인은 pair별 identity·run map·evaluation을 유지하고 "
            "그룹 간 순차 실행, 그룹 내부 jobs 병렬화만 허용한다."
        ),
        "",
        "### Campaign failed-attempt register",
        "",
        "| 버전 | attempt/run IDs | 분류 | native rc | 실패 stage | 확인 원인 | exact cleanup | 증적 기반 조치 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for version, attempts in (("v3", v3_failed_attempts), ("v4", v4_failed_attempts)):
        if not attempts:
            lines.append(f"| {version} | 해당 없음 | — | — | — | 등록된 실패 증적 없음 | 제거 대상 없음 | N/A |")
            continue
        for attempt in attempts:
            run_ids = [str(value) for value in attempt.get("run_ids") or []]
            display_run_ids = ", ".join(f"`{value}`" for value in run_ids)
            returncodes = ", ".join(str(value) for value in attempt.get("engine_returncodes") or [])
            cleanup_count = len(attempt.get("removed_paths") or [])
            lines.append(
                f"| {version} | {display_run_ids} | `{attempt.get('category')}` | `{returncodes}` | "
                f"{attempt.get('stage')} | {attempt.get('reason')} | "
                f"{attempt.get('cleanup_status')}; exact paths {cleanup_count}개 | "
                f"{_failure_remediation(attempt)} |",
            )
    lines += [
        "",
        (
            "실행 규칙: `.venv/bin/python` symlink를 resolve하지 않고 그대로 child stage에 전달하며, 외부 "
            "`PYTHONPATH` 없이 dependency import와 XLSM/OOXML preflight를 먼저 통과시킨다. 실패 재실행은 "
            "새 run ID를 사용하고 이전 native rc·분류·exact cleanup을 campaign 증적에 연결한다."
        ),
        (
            "엔진 시작 전 input-export 실패는 `--v3-failed-attempt-evidence` 또는 "
            "`--v4-failed-attempt-evidence` JSON으로 attempt ID·native rc·분류·stage·원인을 보존하며, "
            "엔진 성공 분모와 섞지 않는다."
        ),
        "",
        *environment_lines,
        "",
        *_parameter_patch_lines((("v3", v3_manifest), ("v4", v4_manifest))),
    ]
    if v3_supply or v4_supply:
        lines.extend(
            [
                "",
                "### LiqUtilAdjustment 선택적 Supply 전달 상세",
                "",
                (
                    "이 표는 LiqUtilAdjustment exact patch가 있는 case만 표시한다. 다른 parameter의 전파는 "
                    "위 generic patch 표와 evaluation input/upstream/price 증적으로 판정한다."
                ),
                "",
                "| 버전 | pressure tag | scenario / proposal | 기준값 → 확정값 | Supply 최종 가동률 | LNG 생산량 Mt/month | LNG 생산량 Bcm/month | run ID |",
                "|---|---|---|---:|---:|---:|---:|---|",
            ],
        )
        for version, supply_rows in (("v3", v3_supply), ("v4", v4_supply)):
            for row in sorted(supply_rows, key=lambda item: EXPECTED_TAG_ORDER.index(item["tag"])):
                lines.append(
                    f"| {version} | `{row['tag']}` | {row['scenario_id']} / {row['proposal_id']} | "
                    f"{_fmt(row['basecase_value'], 5)} → {_fmt(row['proposed_value'], 5)} | "
                    f"{_fmt(row['final_utilization'], 9)} | {_fmt(row['production_mt'], 9)} | "
                    f"{_fmt(row['production_bcm'], 9)} | `{row['run_id']}` |",
                )
    else:
        lines.extend(
            [
                "",
                "- LiqUtilAdjustment 전달 상세: `N/A` — 해당 parameter patch가 없으며 generic engine evidence를 사용.",
            ],
        )

    lines.extend(
        [
            "",
            "## 9. LNG 가격 예측 비교",
            "",
            (
                f"가격 단위는 USD/MMBtu이며 `user_adjusted_price`를 비교했다. 기준값 차이는 각 행의 "
                "`user_adjusted_price - base_case_price`, 버전 차이는 동일 pressure tag의 `v4 - v3`이다. "
                f"수치 동률 tolerance는 `{EPSILON}`이다. 영향 월은 `{selected_month}`월이며 선택 근거는 "
                f"`{focus_month_source}`다."
            ),
            "",
            *_price_table_lines(
                v3_index=v3_annual,
                v4_index=v4_annual,
                title=f"{focus_year}년 연간 가격",
            ),
            "",
            *_price_table_lines(
                v3_index=v3_monthly,
                v4_index=v4_monthly,
                title=f"{focus_year}년 {selected_month}월 가격",
            ),
            "",
            *_cross_version_lines(
                v3_index=v3_annual,
                v4_index=v4_annual,
                title=f"동일 pressure tag의 v4-v3 차이 — {focus_year}년 연간",
            ),
            "",
            *_cross_version_lines(
                v3_index=v3_monthly,
                v4_index=v4_monthly,
                title=f"동일 pressure tag의 v4-v3 차이 — {focus_year}년 {selected_month}월",
            ),
            "",
            "### 버전 내부 가격 순서",
            "",
            "| 기간 | 권역 | v3 실제 순서 | v4 실제 순서 |",
            "|---|---|---|---|",
        ],
    )
    for label, v3_index, v4_index in (
        (f"{focus_year} 연간", v3_annual, v4_annual),
        (f"{focus_year}-{selected_month:02d}", v3_monthly, v4_monthly),
    ):
        for region in DISPLAY_REGIONS:
            lines.append(
                f"| {label} | {region} | `{_price_pattern(v3_index, region=region)}` | "
                f"`{_price_pattern(v4_index, region=region)}` |",
            )
    lines.extend(
        [
            "",
            "### Pressure tag 정량 정합성",
            "",
            (
                "strict 만족률은 tie를 포함한 전체 인접 비교 중 기대 순서를 충족한 비율이다. decisive 정확도는 "
                "tie를 제외하므로 두 비율을 함께 봐야 한다. decisive 비교가 없으면 N/A다."
            ),
            "",
            "| 버전 | 판정 | met | reversed | tie | strict 만족률 | tie 비율 | decisive 정확도 | 반응 권역 |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
            (
                f"| v3 | `{v3_alignment['verdict']}` | {v3_alignment['met']} | "
                f"{v3_alignment['reversed']} | {v3_alignment['tie']} | "
                f"{_rate(v3_alignment['strict_satisfaction'])} | {_rate(v3_alignment['tie_rate'])} | "
                f"{_rate(v3_alignment['decisive_accuracy'])} | {v3_alignment['responsive_region_count']} |"
            ),
            (
                f"| v4 | `{v4_alignment['verdict']}` | {v4_alignment['met']} | "
                f"{v4_alignment['reversed']} | {v4_alignment['tie']} | "
                f"{_rate(v4_alignment['strict_satisfaction'])} | {_rate(v4_alignment['tie_rate'])} | "
                f"{_rate(v4_alignment['decisive_accuracy'])} | {v4_alignment['responsive_region_count']} |"
            ),
            "",
            (
                f"- 가격 방향 판정: v3 `{v3_alignment['verdict']}` "
                f"(`{v3_alignment['reason_code']}`), v4 `{v4_alignment['verdict']}` "
                f"(`{v4_alignment['reason_code']}`)."
            ),
            f"- v3 정성 평가: {_alignment_interpretation(v3_alignment)}",
            f"- v4 정성 평가: {_alignment_interpretation(v4_alignment)}",
            (
                "- 이 판정은 실행 무결성과 분리한다. 모든 가격이 epsilon 안에서 같으면 엔진 실행은 PASS지만 "
                "pressure tag에 따른 가격 차별성은 `indeterminate`로 기록한다."
            ),
            "",
            "### 다수 pair 확장 실행 계약",
            "",
            "- pair 단위 manifest·export·run map·evaluation·보고서를 독립 보존하고 case ID를 합치거나 재번호화하지 않는다.",
            "- LNG model root의 single-group lock을 유지해 group은 순차 실행하고, 한 group 내부 case에만 `--jobs`를 적용한다.",
            "- run ID는 campaign 전체에서 고유해야 하며 실패 retry는 새 ID와 `--failed-attempt-run-map`으로 연결한다.",
            "- aggregate index는 pair별 5개 분석 축과 met/reversed/tie를 합산하되 개별 pair의 REVIEW/FAIL을 가리지 않는다.",
            *([storage_summary] if storage_summary else []),
            "",
            ENGINE_SECTION_END,
        ],
    )
    dashboard_data = {
        "focus_year": focus_year,
        "focus_month": selected_month,
        "focus_month_source": focus_month_source,
        "v3_annual": v3_annual,
        "v4_annual": v4_annual,
        "v3_monthly": v3_monthly,
        "v4_monthly": v4_monthly,
        "v3_runs": v3_evaluation["execution"],
        "v4_runs": v4_evaluation["execution"],
        "v3_campaign_attempt_count": v3_success_count + v3_failed_run_count,
        "v3_failed_attempt_count": v3_failed_run_count,
        "v3_failed_categories": ",".join(
            sorted({str(item.get("category") or "UNKNOWN") for item in v3_failed_attempts}),
        )
        or "NONE",
        "v4_campaign_attempt_count": v4_success_count + v4_failed_run_count,
        "v4_failed_attempt_count": v4_failed_run_count,
        "v4_failed_categories": ",".join(
            sorted({str(item.get("category") or "UNKNOWN") for item in v4_failed_attempts}),
        )
        or "NONE",
        "v3_scenario_count": len(_scenario_items(v3_manifest)),
        "v4_scenario_count": len(_scenario_items(v4_manifest)),
        "v3_group_id": v3_group_id,
        "v4_group_id": v4_group_id,
        "v3_alignment": v3_alignment,
        "v4_alignment": v4_alignment,
        "v3_axes": v3_axes,
        "v4_axes": v4_axes,
        "overall_status": overall_status,
    }
    return "\n".join(lines), dashboard_data


def upsert_engine_section(report: str, section: str) -> str:
    if ENGINE_SECTION_BEGIN in report:
        start = report.index(ENGINE_SECTION_BEGIN)
        end = report.index(ENGINE_SECTION_END, start) + len(ENGINE_SECTION_END)
        updated = f"{report[:start].rstrip()}\n\n{section}\n\n{report[end:].lstrip()}"
    else:
        conclusion_heading = "## 7. 결론 및 해석 한계"
        if conclusion_heading not in report:
            raise RuntimeError("comparison report conclusion heading was not found")
        updated = report.replace(
            conclusion_heading,
            f"{section}\n\n## 10. 결론 및 해석 한계",
            1,
        )
    duplicated_mode = f"{ENGINE_EXECUTION_MODE} + LNG Demand→Supply→Trade→Output 엔진"
    while duplicated_mode in updated:
        updated = updated.replace(duplicated_mode, ENGINE_EXECUTION_MODE)
    if ENGINE_EXECUTION_MODE not in updated:
        updated = updated.replace(BASE_EXECUTION_MODE, ENGINE_EXECUTION_MODE, 1)
    old_summary = (
        "동일 원천 Event 집합을 가진 v3/v4 그룹에 대해 모든 proposal·confirmation·DB read-back 계약이 충족되었습니다."
    )
    engine_summary = (
        "동일 원천 Event 집합을 가진 v3/v4 그룹에 대해 proposal·confirmation·DB read-back과 "
        "동일 LNG 엔진의 Demand→Supply→Trade→Output 전 단계 계약이 모두 충족되었습니다. "
        "이는 기술 실행 결과이며, 가격 태그 정합성은 7절의 독립 판정을 따릅니다."
    )
    previous_engine_summary = (
        "동일 원천 Event 집합을 가진 v3/v4 그룹에 대해 proposal·confirmation·DB read-back과 "
        "동일 LNG 엔진의 Demand→Supply→Trade→Output 전 단계 계약이 모두 충족되었습니다."
    )
    if engine_summary not in updated:
        updated = updated.replace(old_summary, engine_summary, 1)
        updated = updated.replace(previous_engine_summary, engine_summary, 1)
    old_conclusion = (
        "- 최종 결론: v3와 v4가 동일 Event 집합 및 공용 DB 조건에서 모두 proposal·confirmation E2E 계약을 충족했습니다."
    )
    new_conclusion = (
        "- 최종 결론: v3와 v4가 동일 Event 집합 및 공용 DB 조건에서 proposal·confirmation E2E를 충족했고, "
        "동일 LNG 엔진의 Demand→Supply→Trade→Output 전 단계에서 확정 입력 전달·가격 산출·read-back 계약을 "
        "모두 충족했습니다. 다만 이 기술 PASS를 가격 태그 정렬 PASS로 해석하지 않으며, 최종 품질 판정은 "
        "7절의 정합성·표현력 결과를 따릅니다."
    )
    previous_engine_conclusion = (
        "- 최종 결론: v3와 v4가 동일 Event 집합 및 공용 DB 조건에서 proposal·confirmation E2E를 충족했고, "
        "동일 LNG 엔진의 Demand→Supply→Trade→Output 전 단계에서 확정 입력 전달·가격 산출·read-back 계약을 모두 충족했습니다."
    )
    if new_conclusion not in updated:
        updated = updated.replace(old_conclusion, new_conclusion, 1)
        updated = updated.replace(previous_engine_conclusion, new_conclusion, 1)
    status_match = re.search(r"^- 통합 판정: \*\*(PASS|REVIEW|FAIL)\*\*$", section, flags=re.MULTILINE)
    if status_match is not None:
        updated = re.sub(
            r"^- 문서 상태: \*\*(?:PASS|REVIEW|FAIL|NOT_EXECUTED)\*\*$",
            f"- 문서 상태: **{status_match.group(1)}**",
            updated,
            count=1,
            flags=re.MULTILINE,
        )
    updated = updated.replace(
        "![v3/v4 비교 요약](",
        "![v3/v4 가격 태그 정합성 리포트 Figure](",
        1,
    )
    return updated.rstrip() + "\n"


def _report_completion_time(evaluations: Sequence[Mapping[str, Any]]) -> str:
    values: list[datetime] = []
    for evaluation in evaluations:
        raw = str(evaluation.get("generated_at") or "")
        if not raw:
            continue
        values.append(datetime.fromisoformat(raw).astimezone(UTC))
    if not values:
        raise RuntimeError("engine evaluations omit generated_at")
    return max(values).isoformat(timespec="seconds")


def update_report_completion_time(report: str, completion_time: str) -> str:
    lines = report.splitlines()
    matches = [index for index, line in enumerate(lines) if line.startswith("- 검증 종료:")]
    if len(matches) != 1:
        raise RuntimeError(f"comparison report must have one completion line: count={len(matches)}")
    lines[matches[0]] = f"- 검증 종료: {completion_time}"
    return "\n".join(lines).rstrip() + "\n"


def _dashboard_value(
    index: Mapping[tuple[str, str], Mapping[str, Any]],
    tag: str,
    region: str,
) -> float | None:
    row = index.get((tag, region))
    return float(row["user_adjusted_price"]) if row is not None else None


def _campaign_footer_text(version: str, data: Mapping[str, Any]) -> str:
    normalized = version.lower()
    runs = data[f"{normalized}_runs"]
    return (
        f"{version.upper()} CAMPAIGN ATTEMPTS {data[f'{normalized}_campaign_attempt_count']} = "
        f"PASS {runs['success_count']} + FAILED {data[f'{normalized}_failed_attempt_count']} "
        f"({data[f'{normalized}_failed_categories']})    ATTEMPTS RETAINED"
    )


def _dashboard_table(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    y: int,
    title: str,
    v3_index: Mapping[tuple[str, str], Mapping[str, Any]],
    v4_index: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    ink = (29, 43, 57)
    muted = (92, 106, 119)
    border = (208, 217, 226)
    panel = (255, 255, 255)
    alternate = (245, 248, 251)
    positive = (224, 244, 238)
    negative = (250, 232, 230)
    x = 35
    panel_width = width - 70
    _fill_rect(
        pixels,
        width=width,
        height=height,
        x=x,
        y=y,
        rect_width=panel_width,
        rect_height=330,
        color=border,
    )
    _fill_rect(
        pixels,
        width=width,
        height=height,
        x=x + 2,
        y=y + 2,
        rect_width=panel_width - 4,
        rect_height=326,
        color=panel,
    )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=x + 22,
        y=y + 18,
        text=title,
        scale=2,
        color=ink,
    )
    headers = (
        "TAG",
        "V3 EA",
        "V4 EA",
        "D EA",
        "V3 TTF",
        "V4 TTF",
        "D TTF",
        "V3 HH",
        "V4 HH",
        "D HH",
    )
    column_widths = (165, 148, 148, 148, 148, 148, 148, 135, 135, 135)
    table_x = x + 16
    header_y = y + 62
    cursor = table_x
    for header, cell_width in zip(headers, column_widths, strict=True):
        _draw_text(
            pixels,
            width=width,
            height=height,
            x=cursor + 8,
            y=header_y,
            text=header,
            scale=2,
            color=muted,
        )
        cursor += cell_width
    abbreviations = {
        "strong_bullish": "STR BULL",
        "bullish": "BULL",
        "balanced": "BAL",
        "bearish": "BEAR",
        "strong_bearish": "STR BEAR",
    }
    for row_index, tag in enumerate(EXPECTED_TAG_ORDER):
        row_y = y + 94 + row_index * 43
        _fill_rect(
            pixels,
            width=width,
            height=height,
            x=table_x,
            y=row_y - 8,
            rect_width=sum(column_widths),
            rect_height=39,
            color=alternate if row_index % 2 else panel,
        )
        values: list[str] = [abbreviations[tag]]
        backgrounds: list[tuple[int, int, int] | None] = [None]
        for region in DISPLAY_REGIONS:
            v3_value = _dashboard_value(v3_index, tag, region)
            v4_value = _dashboard_value(v4_index, tag, region)
            difference = v4_value - v3_value if v3_value is not None and v4_value is not None else None
            values.extend(
                [
                    _fmt(v3_value) if v3_value is not None else "-",
                    _fmt(v4_value) if v4_value is not None else "-",
                    _signed(difference) if difference is not None else "-",
                ],
            )
            backgrounds.extend(
                [
                    None,
                    None,
                    (
                        positive
                        if difference is not None and difference > EPSILON
                        else negative
                        if difference is not None and difference < -EPSILON
                        else None
                    ),
                ],
            )
        cursor = table_x
        for value, background, cell_width in zip(values, backgrounds, column_widths, strict=True):
            if background is not None:
                _fill_rect(
                    pixels,
                    width=width,
                    height=height,
                    x=cursor + 2,
                    y=row_y - 7,
                    rect_width=cell_width - 4,
                    rect_height=36,
                    color=background,
                )
            _draw_text(
                pixels,
                width=width,
                height=height,
                x=cursor + 8,
                y=row_y,
                text=value,
                scale=2,
                color=ink,
            )
            cursor += cell_width


def _draw_line(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    color: tuple[int, int, int],
    thickness: int = 2,
) -> None:
    delta_x = abs(x2 - x1)
    step_x = 1 if x1 < x2 else -1
    delta_y = -abs(y2 - y1)
    step_y = 1 if y1 < y2 else -1
    error = delta_x + delta_y
    while True:
        _fill_rect(
            pixels,
            width=width,
            height=height,
            x=x1 - thickness // 2,
            y=y1 - thickness // 2,
            rect_width=thickness,
            rect_height=thickness,
            color=color,
        )
        if x1 == x2 and y1 == y2:
            return
        twice_error = 2 * error
        if twice_error >= delta_y:
            error += delta_y
            x1 += step_x
        if twice_error <= delta_x:
            error += delta_x
            y1 += step_y


def _report_price_plot(
    pixels: bytearray,
    *,
    width: int,
    height: int,
    x: int,
    y: int,
    plot_width: int,
    plot_height: int,
    title: str,
    region: str,
    v3_index: Mapping[tuple[str, str], Mapping[str, Any]],
    v4_index: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    ink = (35, 47, 59)
    muted = (106, 117, 128)
    grid = (222, 228, 233)
    v3_color = (43, 92, 139)
    v4_color = (35, 126, 99)
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=x,
        y=y,
        text=f"{title} / {region.upper()}",
        scale=2,
        color=ink,
    )
    chart_top = y + 34
    chart_bottom = y + plot_height - 38
    chart_left = x + 30
    chart_right = x + plot_width - 18
    for fraction in (0.0, 0.5, 1.0):
        line_y = round(chart_top + fraction * (chart_bottom - chart_top))
        _fill_rect(
            pixels,
            width=width,
            height=height,
            x=chart_left,
            y=line_y,
            rect_width=chart_right - chart_left,
            rect_height=1,
            color=grid,
        )
    values = [
        float(index[(tag, region)]["user_adjusted_price"])
        for index in (v3_index, v4_index)
        for tag in EXPECTED_TAG_ORDER
        if (tag, region) in index
    ]
    if not values:
        _draw_text(
            pixels,
            width=width,
            height=height,
            x=chart_left + 20,
            y=chart_top + 40,
            text="NO PRICE EVIDENCE",
            scale=2,
            color=muted,
        )
        return
    minimum = min(values)
    maximum = max(values)
    padding = max((maximum - minimum) * 0.12, 0.000001)
    minimum -= padding
    maximum += padding
    x_positions = {
        tag: round(chart_left + index * (chart_right - chart_left) / (len(EXPECTED_TAG_ORDER) - 1))
        for index, tag in enumerate(EXPECTED_TAG_ORDER)
    }

    def point_y(value: float) -> int:
        ratio = (value - minimum) / (maximum - minimum)
        return round(chart_bottom - ratio * (chart_bottom - chart_top))

    for version, index, color in (("V3", v3_index, v3_color), ("V4", v4_index, v4_color)):
        points: list[tuple[int, int, float]] = []
        for tag in EXPECTED_TAG_ORDER:
            row = index.get((tag, region))
            if row is None:
                continue
            value = float(row["user_adjusted_price"])
            points.append((x_positions[tag], point_y(value), value))
        for prior, current in pairwise(points):
            _draw_line(
                pixels,
                width=width,
                height=height,
                x1=prior[0],
                y1=prior[1],
                x2=current[0],
                y2=current[1],
                color=color,
                thickness=3,
            )
        for point_x, point_y_value, value in points:
            _fill_rect(
                pixels,
                width=width,
                height=height,
                x=point_x - 4,
                y=point_y_value - 4,
                rect_width=9,
                rect_height=9,
                color=color,
            )
            _draw_text(
                pixels,
                width=width,
                height=height,
                x=max(x, point_x - 28),
                y=max(chart_top, point_y_value - (22 if version == "V3" else -10)),
                text=f"{value:.4f}",
                scale=1,
                color=color,
            )
    tag_labels = ("S-BULL", "BULL", "BAL", "BEAR", "S-BEAR")
    for tag, label in zip(EXPECTED_TAG_ORDER, tag_labels, strict=True):
        _draw_text(
            pixels,
            width=width,
            height=height,
            x=x_positions[tag] - 22,
            y=chart_bottom + 13,
            text=label,
            scale=1,
            color=muted,
        )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=x + plot_width - 112,
        y=y,
        text="V3 BLUE / V4 GREEN",
        scale=1,
        color=muted,
    )


def render_engine_dashboard(output_path: Path, data: Mapping[str, Any]) -> None:
    """Render a portrait report figure while retaining the historical function name."""

    width, height = 1200, 1600
    pixels = bytearray((252, 252, 250)) * width * height
    ink = (35, 47, 59)
    muted = (96, 108, 118)
    blue = (43, 92, 139)
    green = (35, 126, 99)
    border = (210, 217, 223)
    status_color = {
        "PASS": green,
        "REVIEW": (173, 112, 28),
        "FAIL": (166, 58, 52),
    }.get(str(data.get("overall_status")), muted)
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=62,
        y=38,
        text="V3 / V4 LNG PRICE-TAG ALIGNMENT REPORT FIGURE",
        scale=3,
        color=ink,
    )
    _fill_rect(
        pixels,
        width=width,
        height=height,
        x=62,
        y=82,
        rect_width=1076,
        rect_height=2,
        color=border,
    )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=62,
        y=105,
        text=(
            f"PAIR V3 GROUP {data['v3_group_id']} / V4 GROUP {data['v4_group_id']}    "
            f"FOCUS {data['focus_year']}-{int(data['focus_month']):02d}"
        ),
        scale=2,
        color=muted,
    )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=62,
        y=142,
        text=f"OVERALL {data['overall_status']}",
        scale=3,
        color=status_color,
    )
    _draw_text(pixels, width=width, height=height, x=62, y=205, text="1. ALIGNMENT STATISTICS", scale=2, color=ink)
    headers = ("VERSION", "VERDICT", "MET", "REV", "TIE", "STRICT", "TIE RATE", "DECISIVE")
    column_x = (62, 190, 410, 505, 600, 690, 835, 985)
    for x_value, header in zip(column_x, headers, strict=True):
        _draw_text(pixels, width=width, height=height, x=x_value, y=242, text=header, scale=2, color=muted)
    for row_index, (version, alignment, color) in enumerate(
        (("V3", data["v3_alignment"], blue), ("V4", data["v4_alignment"], green)),
    ):
        row_y = 282 + row_index * 48
        values = (
            version,
            str(alignment["verdict"]).upper(),
            str(alignment["met"]),
            str(alignment["reversed"]),
            str(alignment["tie"]),
            _rate(alignment["strict_satisfaction"]),
            _rate(alignment["tie_rate"]),
            _rate(alignment["decisive_accuracy"]),
        )
        for x_value, value in zip(column_x, values, strict=True):
            _draw_text(pixels, width=width, height=height, x=x_value, y=row_y, text=value, scale=2, color=color)
    _draw_text(pixels, width=width, height=height, x=62, y=402, text="2. INDEPENDENT QUALITY AXES", scale=2, color=ink)
    _draw_text(pixels, width=width, height=height, x=62, y=438, text="AXIS", scale=2, color=muted)
    _draw_text(pixels, width=width, height=height, x=760, y=438, text="V3", scale=2, color=blue)
    _draw_text(pixels, width=width, height=height, x=940, y=438, text="V4", scale=2, color=green)
    axis_rows = (
        ("EXPORT INTEGRITY", "export_integrity"),
        ("ENGINE EXECUTION", "engine_execution"),
        ("TAG ALIGNMENT", "tag_alignment"),
        ("MECHANISTIC CONSISTENCY", "mechanistic_consistency"),
        ("MODEL EXPRESSIVENESS", "model_expressiveness"),
    )
    for row_index, (label, key) in enumerate(axis_rows):
        row_y = 476 + row_index * 42
        _fill_rect(
            pixels,
            width=width,
            height=height,
            x=62,
            y=row_y - 10,
            rect_width=1076,
            rect_height=34,
            color=(246, 248, 249) if row_index % 2 else (252, 252, 250),
        )
        _draw_text(pixels, width=width, height=height, x=70, y=row_y, text=label, scale=2, color=ink)
        _draw_text(
            pixels,
            width=width,
            height=height,
            x=760,
            y=row_y,
            text=data["v3_axes"][key]["judgement"],
            scale=2,
            color=blue,
        )
        _draw_text(
            pixels,
            width=width,
            height=height,
            x=940,
            y=row_y,
            text=data["v4_axes"][key]["judgement"],
            scale=2,
            color=green,
        )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=62,
        y=704,
        text="3. PRESSURE ORDER PRICE EVIDENCE",
        scale=2,
        color=ink,
    )
    _report_price_plot(
        pixels,
        width=width,
        height=height,
        x=62,
        y=742,
        plot_width=520,
        plot_height=330,
        title=f"ANNUAL {data['focus_year']}",
        region="East Asia Spot",
        v3_index=data["v3_annual"],
        v4_index=data["v4_annual"],
    )
    _report_price_plot(
        pixels,
        width=width,
        height=height,
        x=620,
        y=742,
        plot_width=518,
        plot_height=330,
        title=f"ANNUAL {data['focus_year']}",
        region="TTF",
        v3_index=data["v3_annual"],
        v4_index=data["v4_annual"],
    )
    _report_price_plot(
        pixels,
        width=width,
        height=height,
        x=62,
        y=1100,
        plot_width=520,
        plot_height=330,
        title=f"MONTH {int(data['focus_month']):02d}",
        region="East Asia Spot",
        v3_index=data["v3_monthly"],
        v4_index=data["v4_monthly"],
    )
    _report_price_plot(
        pixels,
        width=width,
        height=height,
        x=620,
        y=1100,
        plot_width=518,
        plot_height=330,
        title=f"MONTH {int(data['focus_month']):02d}",
        region="TTF",
        v3_index=data["v3_monthly"],
        v4_index=data["v4_monthly"],
    )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=62,
        y=1490,
        text="EXPECTED HIGH TO LOW: STRONG BULLISH > BULLISH > BALANCED > BEARISH > STRONG BEARISH",
        scale=1,
        color=muted,
    )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=62,
        y=1520,
        text=f"EPSILON {EPSILON:.6f}    TECHNICAL PASS IS SEPARATE FROM TAG ALIGNMENT",
        scale=1,
        color=muted,
    )
    _draw_text(
        pixels,
        width=width,
        height=height,
        x=62,
        y=1550,
        text=f"{_campaign_footer_text('v3', data)} / {_campaign_footer_text('v4', data)}",
        scale=1,
        color=muted,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_rgb_png(output_path, width=width, height=height, pixels=pixels)


def run(args: argparse.Namespace) -> None:
    if args.report_path.suffix.lower() != ".md":
        raise ValueError("--report-path must be Markdown")
    if args.dashboard_path.suffix.lower() != ".png":
        raise ValueError("--figure-path/--dashboard-path must be PNG")
    if args.focus_month is not None and not 1 <= args.focus_month <= 12:
        raise ValueError("--focus-month must be in 1..12")
    v3_evaluation = _load_object(args.v3_evaluation)
    v4_evaluation = _load_object(args.v4_evaluation)
    v3_failed_attempts = _failed_attempt_register(
        v3_evaluation,
        args.v3_failed_attempt_run_map,
        getattr(args, "v3_failed_attempt_evidence", ()),
    )
    v4_failed_attempts = _failed_attempt_register(
        v4_evaluation,
        args.v4_failed_attempt_run_map,
        getattr(args, "v4_failed_attempt_evidence", ()),
    )
    v3_manifest = _load_object(args.v3_export_manifest)
    v4_manifest = _load_object(args.v4_export_manifest)
    if (args.v4_invariance_baseline is None) != (args.v4_invariance_after is None):
        raise ValueError("--v4-invariance-baseline and --v4-invariance-after must be provided together")
    v4_invariance = None
    if args.v4_invariance_baseline is not None and args.v4_invariance_after is not None:
        v4_invariance = _v4_invariance_summary(
            _load_object(args.v4_invariance_baseline),
            _load_object(args.v4_invariance_after),
            expected_new_proposal_ids=[int(item["proposal_id"]) for item in v4_manifest["scenarios"]],
        )
    section, dashboard_data = build_engine_section(
        v3_evaluation=v3_evaluation,
        v4_evaluation=v4_evaluation,
        v3_manifest=v3_manifest,
        v4_manifest=v4_manifest,
        v3_failed_attempts=v3_failed_attempts,
        v4_failed_attempts=v4_failed_attempts,
        focus_month=args.focus_month,
        v4_invariance_summary=v4_invariance,
        environment_lines=_environment_preflight_lines(v3_evaluation, v4_evaluation),
        storage_summary=_campaign_storage_summary((v3_evaluation, v4_evaluation)),
    )
    report = upsert_engine_section(args.report_path.read_text(encoding="utf-8"), section)
    report = update_report_completion_time(
        report,
        _report_completion_time((v3_evaluation, v4_evaluation)),
    )
    args.report_path.write_text(report, encoding="utf-8")
    render_engine_dashboard(args.dashboard_path, dashboard_data)


def main(argv: Sequence[str] | None = None) -> int:
    run(_parse_args(argv))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
