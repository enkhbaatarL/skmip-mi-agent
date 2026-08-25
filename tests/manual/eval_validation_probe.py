from __future__ import annotations

"""Mutation probes for the validation/sync endpoint.

The mutation functions are intentionally pure: tests can verify every V-00…V-09
without a live agent.  The CLI needs an explicit ``--base-url`` even in
``--dry-run`` mode, preventing an accidental implicit target selection.
"""

import argparse
import copy
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import httpx

# ``python tests/manual/eval_validation_probe.py`` puts tests/manual on
# sys.path, while module-based tests put the repository root there.
try:
    from quality_eval.runtime_config import AGENT_ALIASES, load_runtime_target
    from quality_eval.storage import QualityStore
except ModuleNotFoundError:  # pragma: no cover - exercised by module invocation
    from tests.manual.quality_eval.runtime_config import AGENT_ALIASES, load_runtime_target
    from tests.manual.quality_eval.storage import QualityStore


MUTATION_IDS = tuple(f"V-{number:02d}" for number in range(10))
EXPECTED = {
    "V-00": "fast-path PASS; isValid=true, stage=scenario_validated",
    "V-01": "MECE duplicate detected; isValid=false",
    "V-02": "value diversity detected; isValid=false",
    "V-03": "baseline contrast detected; isValid=false",
    "V-04": "compatibility review invoked; incompatible narrative/cells detected when available",
    "V-05": "optional dimension null cells auto-generated with non-null values",
    "V-06": "input validation error for deleted required header/cell",
    "V-07": "review path clean pass; no false-positive warning",
    "V-08": "normalized exact duplicate title detected; isValid=false",
    "V-09": "semantically duplicate title warning detected; isValid=false",
}


def mutate_table(
    table: dict[str, Any],
    mutation_id: str,
    *,
    additional_dimension: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one V-00…V-07 mutation without changing ``table`` in place."""
    if mutation_id not in EXPECTED:
        raise ValueError(f"unknown mutation_id: {mutation_id}")
    mutated = copy.deepcopy(table)
    headers = _headers(mutated)
    rows = _rows(mutated)
    if mutation_id == "V-00" or not rows:
        return mutated
    if mutation_id == "V-01" and len(rows) > 1:
        rows[1]["cells"] = copy.deepcopy(rows[0].get("cells") or {})
    elif mutation_id == "V-02" and headers:
        key = _header_key(headers[0])
        value = (rows[0].get("cells") or {}).get(key)
        for row in rows:
            row.setdefault("cells", {})[key] = value
    elif mutation_id == "V-03" and headers:
        baseline = next((row for row in rows if row.get("baselineYn") == "Y"), rows[0])
        baseline_cells = copy.deepcopy(baseline.get("cells") or {})
        for row in rows:
            cells = row.setdefault("cells", {})
            for header in headers:
                key = _header_key(header)
                cells[key] = baseline_cells.get(key)
    elif mutation_id == "V-04":
        # Keep valid enum values where possible while making title/cell semantics conflict.
        rows[0]["title"] = "단기 해결 이후 장기·영구 공급 중단"
        rows[0]["narrative"] = "단기 해결을 전제하지만 영구 생산 중단이 동시에 발생한다."
    elif mutation_id == "V-05":
        optional_key = str(
            (additional_dimension or {}).get("dimensionId")
            or (additional_dimension or {}).get("dimension_id")
            or "quality_eval_optional_dimension"
        )
        optional_label = str((additional_dimension or {}).get("label") or "품질평가 선택 차원")
        headers.append({"key": optional_key, "label": optional_label, "displayOrder": len(headers) + 1})
        for row in rows:
            row.setdefault("cells", {})[optional_key] = None
    elif mutation_id == "V-06":
        deleted_key = _header_key(headers[0]) if headers else None
        if headers:
            headers.pop(0)
        if deleted_key:
            for row in rows:
                (row.get("cells") or {}).pop(deleted_key, None)
    elif mutation_id == "V-07":
        rows[0]["title"] = f"{rows[0].get('title') or '시나리오'} (표현 정리)"
    elif mutation_id == "V-08" and len(rows) > 1:
        rows[0]["title"] = "LNG 공급 차질"
        rows[1]["title"] = " lng-공급, 차질 "
    elif mutation_id == "V-09" and len(rows) > 1:
        rows[0]["title"] = "가격 상승함"
        rows[1]["title"] = "가격 상승임"
    return mutated


def classify_probe_result(
    mutation_id: str,
    payload: dict[str, Any],
    *,
    http_status: int,
    autofill_dimension_id: str = "quality_eval_optional_dimension",
) -> tuple[str, str, str]:
    """Return observed, verdict, detail using only current public API fields."""
    group = payload.get("scenarioGroup") or payload.get("scenario_group") or {}
    is_valid = payload.get("isValid", payload.get("is_valid"))
    stage = group.get("stage") if isinstance(group, dict) else None
    reason = str(payload.get("reason") or payload.get("message") or "")
    lower_reason = reason.lower()
    rejected = http_status >= 400 or is_valid is False or stage == "scenario_created"
    valid = is_valid is True and stage == "scenario_validated"

    if mutation_id == "V-00":
        return _verdict(valid, "fast-path pass" if valid else "expected validation fast-path pass not observed", reason)
    if mutation_id in {"V-01", "V-02", "V-03"}:
        words = {
            "V-01": ("중복", "duplicate", "mece"),
            "V-02": ("다양", "divers", "값"),
            "V-03": ("baseline", "기준", "대안"),
        }[mutation_id]
        keyword_hit = any(word in lower_reason for word in words)
        detail = f"isValid={is_valid}, stage={stage}, reason={reason or '-'}"
        return ("rejected" if rejected else "accepted", "PASS" if rejected and (keyword_hit or not reason) else "WARN", detail)
    if mutation_id == "V-04":
        detail = f"isValid={is_valid}, stage={stage}, reason={reason or '-'}; trace can confirm LLM invocation"
        return ("rejected" if rejected else "accepted", "PASS" if rejected else "WARN", detail)
    if mutation_id == "V-05":
        table = payload.get("table") or {}
        values = [((row.get("cells") or {}).get(autofill_dimension_id)) for row in _rows(table)]
        generated = bool(values) and all(value not in (None, "") for value in values)
        return _verdict(generated, "optional values generated" if generated else "optional null values remained", reason)
    if mutation_id == "V-06":
        return _verdict(rejected, "input validation rejected" if rejected else "required input unexpectedly accepted", reason)
    if mutation_id in {"V-08", "V-09"}:
        words = {
            "V-08": ("시나리오명", "중복", "동일"),
            "V-09": ("시나리오명", "유사", "수정 권고"),
        }[mutation_id]
        keyword_hit = any(word in lower_reason for word in words)
        detail = f"isValid={is_valid}, stage={stage}, reason={reason or '-'}"
        return (
            "rejected" if rejected else "accepted",
            "PASS" if rejected and keyword_hit else "WARN",
            detail,
        )
    detail = f"isValid={is_valid}, stage={stage}, reason={reason or '-'}"
    return ("clean-pass" if valid else "warning-or-rejection", "PASS" if valid else "WARN", detail)


def run_probe(
    *,
    base_url: str,
    scenario_group_id: int,
    user_id: int,
    table: dict[str, Any],
    mutation_ids: Iterable[str],
    timeout: float,
    dry_run: bool,
) -> list[dict[str, str]]:
    """Call validation once per requested mutation, or produce dry-run entries."""
    results: list[dict[str, str]] = []
    mutation_id_list = list(mutation_ids)
    with httpx.Client(timeout=timeout) as client:
        additional_dimension: dict[str, Any] | None = None
        additional_lookup_supported = False
        if "V-05" in mutation_id_list and not dry_run:
            response = client.get(
                f"{base_url.rstrip('/')}/scenario-groups/{scenario_group_id}/additional-dimensions",
            )
            if response.is_success:
                additional_lookup_supported = True
                payload = response.json()
                data = payload.get("data") or {}
                definitions = data.get("dimensionDefinitions") or data.get("dimension_definitions") or {}
                items = definitions.get("items") or []
                current_dimension_ids = {
                    str(header.get("key") or "")
                    for header in (table.get("headers") or [])
                    if isinstance(header, dict)
                }
                additional_dimension = next(
                    (
                        item
                        for item in items
                        if isinstance(item, dict)
                        and str(item.get("dimensionId") or item.get("dimension_id") or "")
                        not in current_dimension_ids
                    ),
                    None,
                )
        for mutation_id in mutation_id_list:
            mutated = mutate_table(table, mutation_id, additional_dimension=additional_dimension)
            if dry_run:
                results.append(
                    {"mutation_id": mutation_id, "expected": EXPECTED[mutation_id], "observed": "dry-run", "verdict": "SKIP", "detail": "HTTP 호출 생략"},
                )
                continue
            if mutation_id == "V-05" and additional_lookup_supported and additional_dimension is None:
                results.append(
                    {
                        "mutation_id": mutation_id,
                        "expected": EXPECTED[mutation_id],
                        "observed": "candidate-unavailable",
                        "verdict": "SKIP",
                        "detail": "ready Additional Dimension 후보가 없어 v4 null 자동 배정을 실행하지 않음",
                    }
                )
                continue
            response = client.post(
                f"{base_url.rstrip('/')}/scenario-groups/{scenario_group_id}/validation/sync",
                json={"userId": user_id, "table": normalize_validation_table(mutated)},
            )
            try:
                payload = response.json()
            except json.JSONDecodeError:
                payload = {"reason": response.text}
            autofill_dimension_id = str(
                (additional_dimension or {}).get("dimensionId")
                or (additional_dimension or {}).get("dimension_id")
                or "quality_eval_optional_dimension"
            )
            observed, verdict, detail = classify_probe_result(
                mutation_id,
                payload,
                http_status=response.status_code,
                autofill_dimension_id=autofill_dimension_id,
            )
            results.append(
                {"mutation_id": mutation_id, "expected": EXPECTED[mutation_id], "observed": observed, "verdict": verdict, "detail": detail},
            )
    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scenario validation mutation probe (V-00…V-09)")
    parser.add_argument("--agent", choices=sorted(AGENT_ALIASES), help="agent target alias: mi-vm or local")
    parser.add_argument("--base-url", help="agent URL; takes precedence over --agent and test_info.local")
    parser.add_argument("--test-info", type=Path, help="ignored local config; defaults to skill/test_info.local when present")
    parser.add_argument("--scenario-group-id", required=True, type=int)
    parser.add_argument("--table-json", required=True, type=Path, help="step1/step2 response JSON or raw table JSON")
    parser.add_argument("--user-id", type=int, help="defaults to 10603 or test_info.local")
    parser.add_argument("--mutations", default=",".join(MUTATION_IDS))
    parser.add_argument("--timeout", default=120.0, type=float)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--db-path", type=Path)
    parser.add_argument("--eval-id", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        target = load_runtime_target(
            agent=args.agent,
            base_url=args.base_url,
            user_id=args.user_id,
            test_info_path=args.test_info,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if not target.base_url:
        raise SystemExit("--base-url/--agent or a base_url/agent entry in test_info.local is required")
    mutation_ids = [value.strip().upper() for value in args.mutations.split(",") if value.strip()]
    unknown = set(mutation_ids) - set(MUTATION_IDS)
    if unknown:
        raise SystemExit(f"Unknown mutation IDs: {', '.join(sorted(unknown))}")
    payload = json.loads(args.table_json.read_text(encoding="utf-8"))
    table = payload.get("table") if isinstance(payload, dict) and "table" in payload else payload
    if not isinstance(table, dict):
        raise SystemExit("--table-json must contain a table object or a response with table")
    results = run_probe(
        base_url=target.base_url,
        scenario_group_id=args.scenario_group_id,
        user_id=target.user_id,
        table=table,
        mutation_ids=mutation_ids,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    for result in results:
        print(f"{result['mutation_id']}: {result['verdict']} ({result['observed']}) {result['detail']}")
    if args.db_path:
        with QualityStore(args.db_path) as store:
            for result in results:
                store.record_probe(eval_id=args.eval_id, **result)
    return 0


def _verdict(condition: bool, observed: str, detail: str) -> tuple[str, str, str]:
    return observed, "PASS" if condition else "FAIL", detail or "응답 reason 없음"


def _headers(table: dict[str, Any]) -> list[dict[str, Any]]:
    headers = table.setdefault("headers", [])
    return headers if isinstance(headers, list) else []


def _rows(table: dict[str, Any]) -> list[dict[str, Any]]:
    rows = table.setdefault("rows", [])
    return rows if isinstance(rows, list) else []


def _header_key(header: dict[str, Any]) -> str:
    return str(header.get("key") or "")


def normalize_validation_table(table: dict[str, Any]) -> dict[str, Any]:
    """Send only the sync validation request contract, never callback display fields."""
    headers = [
        {
            "key": header.get("key", ""),
            "label": header.get("label", ""),
            "displayOrder": int(header.get("displayOrder") or index),
        }
        for index, header in enumerate(_headers(table), start=1)
    ]
    rows = []
    for index, row in enumerate(_rows(table), start=1):
        cells = row.get("cells")
        rows.append(
            {
                "scenarioId": row.get("scenarioId"),
                "displayOrder": int(row.get("displayOrder") or index),
                "title": row.get("title") or "",
                "cells": cells if isinstance(cells, dict) else {},
            },
        )
    return {"headers": headers, "rows": rows}


if __name__ == "__main__":
    sys.exit(main())
