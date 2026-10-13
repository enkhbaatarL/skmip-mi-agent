# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: INP001, T201

"""Compare Model Parameter Before/After evidence for an identical v4 cohort."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        message = f"Expected a JSON object: {path}"
        raise TypeError(message)
    return value


def _scenario_rows(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    rows = evidence.get("scenarios")
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        message = "Evidence must contain a scenarios object list"
        raise ValueError(message)
    return rows


def _ids(rows: list[dict[str, Any]]) -> set[int]:
    return {int(row["scenario_id"]) for row in rows}


def _candidate_ids(rows: list[dict[str, Any]]) -> set[int]:
    return {
        int(row["scenario_id"])
        for row in rows
        if int(row.get("runtime_candidate_count") or 0) > 0
    }


def _covered_ids(rows: list[dict[str, Any]]) -> set[int]:
    return {
        int(row["scenario_id"])
        for row in rows
        if row.get("classification") == "runtime_candidate_covered"
    }


def _group_ids(evidence: dict[str, Any], rows: list[dict[str, Any]]) -> set[int]:
    requested = (evidence.get("scope") or {}).get("requested_scenario_group_ids")
    if isinstance(requested, list):
        return {int(item) for item in requested}
    return {int(row["scenario_group_id"]) for row in rows}


def _scope_identity(evidence: dict[str, Any]) -> dict[str, Any]:
    scope = evidence.get("scope") or {}
    return {
        "api_version": scope.get("api_version"),
        "generation_strategy": scope.get("generation_strategy"),
        "impact_catalog_version": scope.get("impact_catalog_version"),
        "impact_catalog_checksum": scope.get("impact_catalog_checksum"),
    }


def _rate(numerator: int, denominator: int) -> float:
    return round(100 * numerator / denominator, 1) if denominator else 0.0


def _parameter_proposals(evidence: dict[str, Any]) -> dict[str, int]:
    return {
        str(row.get("parameter_name") or ""): int(row.get("proposal_scenarios") or 0)
        for row in evidence.get("parameter_summary") or []
        if isinstance(row, dict) and row.get("parameter_name")
    }


def _comparison(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_rows = _scenario_rows(before)
    after_rows = _scenario_rows(after)
    before_ids = _ids(before_rows)
    after_ids = _ids(after_rows)
    before_candidates = _candidate_ids(before_rows)
    after_candidates = _candidate_ids(after_rows)
    before_covered = _covered_ids(before_rows)
    after_covered = _covered_ids(after_rows)
    before_groups = _group_ids(before, before_rows)
    after_groups = _group_ids(after, after_rows)
    before_scope = _scope_identity(before)
    after_scope = _scope_identity(after)
    same_cohort_checks = {
        "scope_identity": before_scope == after_scope,
        "scenario_group_ids": before_groups == after_groups,
        "scenario_ids": before_ids == after_ids,
        "runtime_candidate_scenario_ids": before_candidates == after_candidates,
    }
    scenario_count = len(before_ids)
    candidate_count = len(before_candidates)
    before_parameters = _parameter_proposals(before)
    after_parameters = _parameter_proposals(after)
    parameter_names = sorted(before_parameters.keys() | after_parameters.keys())
    regressions = sorted(before_covered - after_covered)
    return {
        "schema_version": 1,
        "same_cohort": all(same_cohort_checks.values()),
        "same_cohort_checks": same_cohort_checks,
        "scope_identity": before_scope,
        "counts": {
            "scenario_groups": len(before_groups),
            "scenarios": scenario_count,
            "runtime_candidates": candidate_count,
        },
        "kpis": {
            "before": {
                "covered": len(before_covered),
                "proposal_coverage_percent": _rate(len(before_covered), scenario_count),
                "candidate_success_percent": _rate(len(before_covered), candidate_count),
            },
            "after": {
                "covered": len(after_covered),
                "proposal_coverage_percent": _rate(len(after_covered), scenario_count),
                "candidate_success_percent": _rate(len(after_covered), candidate_count),
            },
            "delta": {
                "covered": len(after_covered) - len(before_covered),
                "proposal_coverage_percentage_points": round(
                    _rate(len(after_covered), scenario_count)
                    - _rate(len(before_covered), scenario_count),
                    1,
                ),
                "candidate_success_percentage_points": round(
                    _rate(len(after_covered), candidate_count)
                    - _rate(len(before_covered), candidate_count),
                    1,
                ),
            },
        },
        "scenario_outcomes": {
            "newly_covered_ids": sorted(after_covered - before_covered),
            "remaining_uncovered_candidate_ids": sorted(after_candidates - after_covered),
            "regressed_covered_ids": regressions,
        },
        "proposal_history": {
            "before_rows": int((before.get("proposal_history") or {}).get("matched_row_count") or 0),
            "after_rows": int((after.get("proposal_history") or {}).get("matched_row_count") or 0),
            "before_identity_conflicts": int(
                (before.get("proposal_history") or {}).get("identity_conflict_scenario_count") or 0,
            ),
            "after_identity_conflicts": int(
                (after.get("proposal_history") or {}).get("identity_conflict_scenario_count") or 0,
            ),
        },
        "parameter_proposal_deltas": [
            {
                "parameter_name": name,
                "before": before_parameters.get(name, 0),
                "after": after_parameters.get(name, 0),
                "delta": after_parameters.get(name, 0) - before_parameters.get(name, 0),
            }
            for name in parameter_names
        ],
        "pass": all(same_cohort_checks.values()) and not regressions,
    }


def main() -> int:
    args = _parse_args()
    result = _comparison(_load(args.before), _load(args.after))
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        try:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(serialized)
        except FileExistsError:
            print(f"Refusing to overwrite existing output: {args.output}", file=sys.stderr)
            return 2
    print(serialized, end="")
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
