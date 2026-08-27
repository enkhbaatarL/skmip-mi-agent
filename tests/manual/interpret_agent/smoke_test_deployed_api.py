"""배포된 Interpret Agent의 읽기 전용 preview와 plain-text 계약을 검증한다."""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

import httpx


EXPECTED_PATHS = {
    "/scenario-groups/{scenario_group_id}/price-interpretations/preview",
    "/scenario-groups/{scenario_group_id}/price-interpretations",
}
FORBIDDEN_LITERALS = ("**", "__", "`", "<strong", "<b>", "<em", "<i>")
MARKDOWN_HEADING_RE = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+")
MARKDOWN_LINK_RE = re.compile(r"!?\[[^\]\n]+\]\([^)\n]+\)")
HTML_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>\n]*?)?\s*/?>")
MARKDOWN_UNORDERED_LIST_RE = re.compile(r"(?m)^[ \t]{0,3}[-+*][ \t]+")
MARKDOWN_ORDERED_LIST_RE = re.compile(r"(?m)^[ \t]{0,3}\d{1,3}\.[ \t]+")
MARKDOWN_INDENTED_CODE_RE = re.compile(r"(?m)^(?: {4,}|\t+)\S")
MARKDOWN_HORIZONTAL_RULE_RE = re.compile(r"(?m)^[ \t]{0,3}(?:[-*_][ \t]*){3,}$")
LENGTH_LIMITS = {
    "identity": 45,
    "driverPhase": 220,
    "priceCharacter": 220,
    "summary": 260,
    "overallMessage": 600,
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Interpret 배포 API의 문서·route 격리·validation·preview plain-text를 검증합니다. "
            "외부 callback을 발생시키는 비동기 endpoint는 호출하지 않습니다."
        ),
    )
    parser.add_argument("--base-url", default="http://40.82.137.178:8003")
    parser.add_argument("--scenario-group-id", type=int, default=183)
    parser.add_argument(
        "--scenario-id",
        action="append",
        type=int,
        dest="scenario_ids",
        help="검증할 scenario ID. 여러 번 지정할 수 있으며 기본값은 1077입니다.",
    )
    parser.add_argument("--timeout-sec", type=float, default=900.0)
    parser.add_argument("--output", type=Path)
    return parser


def _check(checks: list[dict[str, Any]], name: str, passed: bool, detail: object) -> None:
    checks.append({"name": name, "passed": passed, "detail": detail})


def _format_markers(value: str) -> list[str]:
    markers = [marker for marker in FORBIDDEN_LITERALS if marker.lower() in value.lower()]
    if MARKDOWN_HEADING_RE.search(value):
        markers.append("markdown_heading")
    if MARKDOWN_LINK_RE.search(value):
        markers.append("markdown_link")
    if HTML_TAG_RE.search(value):
        markers.append("html_tag")
    if MARKDOWN_UNORDERED_LIST_RE.search(value):
        markers.append("markdown_unordered_list")
    if MARKDOWN_ORDERED_LIST_RE.search(value):
        markers.append("markdown_ordered_list")
    if MARKDOWN_INDENTED_CODE_RE.search(value):
        markers.append("markdown_indented_code")
    if MARKDOWN_HORIZONTAL_RULE_RE.search(value):
        markers.append("markdown_horizontal_rule")
    return markers


def _visible_fields(payload: dict[str, Any]) -> list[tuple[str, str]]:
    data = payload.get("data") or {}
    fields: list[tuple[str, str]] = []
    for index, scenario in enumerate(data.get("scenarios") or []):
        for field in ("identity", "driverPhase", "priceCharacter", "summary"):
            fields.append((f"data.scenarios[{index}].{field}", str(scenario.get(field) or "")))
    synthesis = data.get("synthesis") or {}
    fields.append(("data.synthesis.overallMessage", str(synthesis.get("overallMessage") or "")))
    return fields


def _run(args: argparse.Namespace) -> dict[str, Any]:
    base_url = str(args.base_url).rstrip("/")
    scenario_ids = list(args.scenario_ids or [1077])
    checks: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    evidence: dict[str, Any] = {
        "startedAt": datetime.now(UTC).isoformat(),
        "baseUrl": base_url,
        "scenarioGroupId": args.scenario_group_id,
        "scenarioIds": scenario_ids,
        "safety": "preview only; async callback endpoint not invoked",
        "checks": checks,
        "qualityWarnings": warnings,
    }

    timeout = httpx.Timeout(args.timeout_sec, connect=min(args.timeout_sec, 30.0))
    with httpx.Client(base_url=base_url, timeout=timeout, follow_redirects=True) as client:
        docs_response = client.get("/docs")
        _check(checks, "INT-DOCS-001", docs_response.status_code == 200, docs_response.status_code)

        openapi_response = client.get("/openapi.json")
        openapi_ok = openapi_response.status_code == 200
        _check(checks, "INT-OPENAPI-002", openapi_ok, openapi_response.status_code)
        if openapi_ok:
            openapi_bytes = openapi_response.content
            openapi = openapi_response.json()
            actual_paths = set(openapi.get("paths") or {})
            evidence["openapiSha256"] = hashlib.sha256(openapi_bytes).hexdigest()
            evidence["openapiPaths"] = sorted(actual_paths)
            _check(
                checks,
                "INT-ROUTE-ISOLATION-003",
                actual_paths == EXPECTED_PATHS,
                {"expected": sorted(EXPECTED_PATHS), "actual": sorted(actual_paths)},
            )

        invalid_response = client.post(
            f"/scenario-groups/{args.scenario_group_id}/price-interpretations/preview",
            json={"scenarioIds": ["not-an-int"]},
        )
        _check(
            checks,
            "INT-VALIDATION-004",
            invalid_response.status_code == 422,
            invalid_response.status_code,
        )

        started = time.perf_counter()
        preview_response = client.post(
            f"/scenario-groups/{args.scenario_group_id}/price-interpretations/preview",
            json={"scenarioIds": scenario_ids},
        )
        elapsed_seconds = round(time.perf_counter() - started, 3)
        evidence["previewElapsedSeconds"] = elapsed_seconds
        evidence["previewHttpStatus"] = preview_response.status_code
        preview_ok = preview_response.status_code == 200
        _check(
            checks,
            "INT-PREVIEW-HTTP-005",
            preview_ok,
            {
                "status": preview_response.status_code,
                "elapsedSeconds": elapsed_seconds,
                "body": preview_response.text[:2000] if not preview_ok else None,
            },
        )

        if preview_ok:
            payload = preview_response.json()
            evidence["previewResponse"] = payload
            data = payload.get("data") or {}
            scenarios = data.get("scenarios") or []
            returned_ids = {int(item["scenarioId"]) for item in scenarios}
            _check(
                checks,
                "INT-PREVIEW-SCENARIOS-006",
                payload.get("status") == "success" and returned_ids == set(scenario_ids),
                {"status": payload.get("status"), "returnedScenarioIds": sorted(returned_ids)},
            )

            meta = data.get("meta") or {}
            _check(
                checks,
                "INT-PREVIEW-META-007",
                meta.get("baseScenarioId") == "MI Base" and meta.get("indices") == ["JKM", "TTF", "HH"],
                {
                    "baseScenarioId": meta.get("baseScenarioId"),
                    "indices": meta.get("indices"),
                    "periodStart": meta.get("periodStart"),
                    "periodEnd": meta.get("periodEnd"),
                },
            )

            visible_fields = _visible_fields(payload)
            marker_failures: dict[str, list[str]] = {}
            for path, value in visible_fields:
                markers = _format_markers(value)
                if markers:
                    marker_failures[path] = markers
            empty_fields = [path for path, value in visible_fields if not value.strip()]
            _check(
                checks,
                "INT-PLAIN-TEXT-008",
                not marker_failures and not empty_fields,
                {"markerFailures": marker_failures, "emptyFields": empty_fields},
            )

            for path, value in visible_fields:
                field_name = path.rsplit(".", maxsplit=1)[-1]
                limit = LENGTH_LIMITS.get(field_name)
                if limit is not None and len(value) > limit:
                    warnings.append(
                        {
                            "path": path,
                            "length": len(value),
                            "promptLimit": limit,
                        },
                    )

    evidence["finishedAt"] = datetime.now(UTC).isoformat()
    evidence["passed"] = all(check["passed"] for check in checks)
    return evidence


def main() -> int:
    args = _parser().parse_args()
    evidence = _run(args)
    serialized = json.dumps(evidence, ensure_ascii=False, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    sys.stdout.write(serialized + "\n")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
