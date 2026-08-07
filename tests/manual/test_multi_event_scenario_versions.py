from __future__ import annotations

# ruff: noqa: CPY001
import argparse
import asyncio
from datetime import UTC, datetime
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any
import uuid

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tests.manual.multi_event_comparison.llm import (  # noqa: E402
    build_agent_judge_input,
    load_agent_judgment,
    write_agent_judge_input,
)
from tests.manual.multi_event_comparison.models import (  # noqa: E402
    ApiVersion,
    ComparisonJudgment,
)
from tests.manual.multi_event_comparison.quality import run_deterministic_checks  # noqa: E402
from tests.manual.multi_event_comparison.report import render_report  # noqa: E402
from tests.manual.quality_eval.runtime_config import AGENT_ALIASES, load_runtime_target  # noqa: E402


OUTPUT_ROOT = Path("local/output/multi_event_scenario_comparison")
LOGGER = logging.getLogger("multi_event_scenario_versions")
ALL_VERSIONS: tuple[ApiVersion, ...] = ("v2", "v3", "v4")
V4_ONLY_VERSIONS: tuple[ApiVersion, ...] = ("v4",)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare, run, and report a v2/v3/v4 comparison or standalone v4 multi-event Scenario API run.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser("prepare", help="Select 2..5 Events and write the immutable run manifest.")
    _add_target_arguments(prepare)
    selection = prepare.add_mutually_exclusive_group(required=True)
    selection.add_argument("--event-ids", type=int, nargs="+", help="Explicit, unique Event IDs (2..5).")
    selection.add_argument("--event-count", type=int, help="Select this many Events (2..5) through GET /events.")
    prepare.add_argument("--event-sort", choices=["latest", "oldest"], default="latest")
    prepare.add_argument("--keyword", help="Optional GET /events keyword, only with --event-count.")
    prepare.add_argument("--event-page-size", type=int, default=100)
    prepare.add_argument("--comparison-run-id", help="Defaults to a unique generated ID.")
    prepare.add_argument("--batch-id", help="Defaults to timestamp plus a random suffix.")
    prepare.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    prepare.add_argument(
        "--v4-only",
        action="store_true",
        help="Prepare a standalone v4 run that does not require or allow v2/v3 execution.",
    )
    prepare.add_argument(
        "--delete-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Soft delete every active Scenario Group related to the selected Events before version execution "
            "(default: enabled; use --no-delete-existing to preserve them)."
        ),
    )
    prepare.add_argument(
        "--admin-token",
        help="Soft delete API Bearer token; defaults to SCENARIO_GROUP_ADMIN_TOKEN.",
    )

    run_version = subparsers.add_parser("run-version", help="Call exactly one versioned sync POST without retry.")
    run_version.add_argument("--manifest", type=Path, required=True)
    run_version.add_argument("--version", choices=["v2", "v3", "v4"], required=True)
    run_version.add_argument("--timeout", type=float, default=1200)

    orchestrate = subparsers.add_parser(
        "orchestrate",
        help="Fallback without subagents: run v2/v3 concurrently, then v4.",
    )
    orchestrate.add_argument("--manifest", type=Path, required=True)
    orchestrate.add_argument("--timeout", type=float, default=1200)

    report = subparsers.add_parser("report", help="Render completed version artifacts as Markdown.")
    report.add_argument("--manifest", type=Path, required=True)
    report.add_argument("--quality-check", type=_parse_bool, default=True, metavar="true|false")
    report.add_argument(
        "--judge-input",
        type=Path,
        help="agent judge request path; defaults beside comparison_judge.json",
    )
    report.add_argument(
        "--judge-result",
        type=Path,
        help="agent-produced result path; defaults to manifest artifacts.judge",
    )
    report.add_argument(
        "--prepare-judge-only",
        action="store_true",
        help="write the agent judge request and exit before rendering the final report",
    )
    return parser.parse_args()


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent", choices=sorted(AGENT_ALIASES))
    parser.add_argument("--base-url", help="Takes precedence over --agent and test_info.local.")
    parser.add_argument("--user-id", type=int)
    parser.add_argument("--test-info", type=Path)
    parser.add_argument("--timeout", type=float, default=120)


async def prepare(args: argparse.Namespace) -> Path:
    _validate_prepare_args(args)
    target = load_runtime_target(
        agent=args.agent,
        base_url=args.base_url,
        user_id=args.user_id,
        test_info_path=args.test_info,
    )
    base_url = target.base_url or "http://localhost:8000"
    timeout = httpx.Timeout(args.timeout)
    async with httpx.AsyncClient(timeout=timeout) as client:
        if args.event_ids:
            event_ids = list(args.event_ids)
            selection_description = f"명시 Event IDs: {event_ids}"
        else:
            event_ids = await _select_event_ids(
                client,
                base_url=base_url,
                count=args.event_count,
                sort=args.event_sort,
                keyword=args.keyword,
                page_size=args.event_page_size,
            )
            keyword_text = f", keyword={args.keyword!r}" if args.keyword else ""
            selection_description = f"{args.event_sort} {args.event_count}개{keyword_text}"
        event_details = await asyncio.gather(
            *(_fetch_event_detail(client, base_url, event_id) for event_id in event_ids),
        )
        cleanup_results = (
            await _soft_delete_existing_groups(
                client,
                base_url=base_url,
                event_ids=event_ids,
                user_id=target.user_id,
                admin_token=args.admin_token or os.environ.get("SCENARIO_GROUP_ADMIN_TOKEN"),
            )
            if args.delete_existing
            else []
        )

    available = {_event_id(detail) for detail in event_details}
    if available != set(event_ids):
        msg = f"Event detail IDs do not match selection: selected={event_ids}, detail={sorted(available)}"
        raise ValueError(msg)

    batch_id = args.batch_id or f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    versions = V4_ONLY_VERSIONS if args.v4_only else ALL_VERSIONS
    comparison_run_prefix = "v4-only" if args.v4_only else "multi-event"
    comparison_run_id = args.comparison_run_id or f"{comparison_run_prefix}-{batch_id}"
    artifact_dir = (args.output_root / batch_id).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=False)
    selected_events_path = artifact_dir / "selected_events.json"
    cleanup_path = artifact_dir / "existing_groups_soft_delete.json"
    manifest_path = artifact_dir / "manifest.json"
    _write_json(selected_events_path, event_details)
    _write_json(
        cleanup_path,
        {
            "requested": args.delete_existing,
            "deletedGroupCount": len(cleanup_results),
            "groups": cleanup_results,
        },
    )
    manifest = {
        "schemaVersion": 1,
        "batchId": batch_id,
        "createdAt": _now(),
        "baseUrl": base_url,
        "userId": target.user_id,
        "comparisonRunId": comparison_run_id,
        "versions": list(versions),
        "eventIds": event_ids,
        "events": event_details,
        "preRunCleanup": {
            "requested": args.delete_existing,
            "deletedGroupCount": len(cleanup_results),
            "groups": cleanup_results,
        },
        "selection": {
            "mode": "explicit" if args.event_ids else "query",
            "description": selection_description,
            "sort": args.event_sort,
            "keyword": args.keyword,
        },
        "artifactDir": str(artifact_dir),
        "artifacts": {
            "selectedEvents": str(selected_events_path),
            "preRunCleanup": str(cleanup_path),
            **{version: str(artifact_dir / f"{version}_create_response.json") for version in versions},
            "orchestration": str(artifact_dir / "orchestration.json"),
            "judgeInput": str(artifact_dir / "comparison_judge_input.json"),
            "judge": str(artifact_dir / "comparison_judge.json"),
            "report": str(artifact_dir / "comparison_report.md"),
        },
        **({"executionMode": "v4-only"} if args.v4_only else {}),
    }
    _write_json(manifest_path, manifest)
    LOGGER.info("Prepared manifest: %s", manifest_path)
    return manifest_path


async def run_version(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.manifest)
    version: ApiVersion = args.version
    _validate_version_scope(manifest, version)
    artifact_path = Path(manifest["artifacts"][version])
    if artifact_path.exists():  # noqa: ASYNC240
        msg = (
            f"{artifact_path} already exists; refusing to repeat a non-idempotent POST. "
            "Use a new prepare batch after checking server state."
        )
        raise FileExistsError(
            msg,
        )
    claim_path = artifact_path.with_suffix(".running.lock")
    _claim_version(claim_path, version)
    request_body: dict[str, Any] = {
        "miEventIds": manifest["eventIds"],
        "userId": manifest["userId"],
        "comparisonRunId": manifest["comparisonRunId"],
    }
    url = f"{manifest['baseUrl']}/{version}/scenario-groups/sync"
    started_at = _now()
    started = time.perf_counter()
    artifact: dict[str, Any] = {
        "apiVersion": version,
        "url": url,
        "request": request_body,
        "startedAt": started_at,
        "attemptCount": 1,
        "retryPolicy": "disabled",
    }
    exit_code = 1
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(args.timeout)) as client:
            response = await client.post(url, json=request_body)
        artifact["httpStatus"] = response.status_code
        try:
            payload = response.json()
        except json.JSONDecodeError:
            payload = {"rawText": response.text}
        artifact["response"] = payload
        artifact["transportStatus"] = "success" if response.is_success else "error"
        if response.is_success and isinstance(payload, dict) and payload.get("status") == "success":
            try:
                _validate_version_response(payload, manifest, version)
            except (TypeError, ValueError) as exc:
                artifact["outcome"] = "invalid_response"
                artifact["error"] = str(exc)
            else:
                artifact["outcome"] = "success"
                exit_code = 0
        elif isinstance(payload, dict):
            artifact["outcome"] = "failure"
            artifact["error"] = payload.get("message") or f"HTTP {response.status_code}"
        else:
            artifact["outcome"] = "failure"
            artifact["error"] = f"HTTP {response.status_code}"
    except (httpx.TimeoutException, TimeoutError) as exc:
        artifact["transportStatus"] = "unknown"
        artifact["outcome"] = "unknown"
        artifact["error"] = (
            f"{type(exc).__name__}: {exc}. POST 결과가 불명확하므로 동일 version을 재호출하지 말고 "
            "API/DB에서 comparisonRunId 상태를 확인해야 합니다."
        )
    except httpx.HTTPError as exc:
        artifact["transportStatus"] = "error"
        artifact["outcome"] = "failure"
        artifact["error"] = f"{type(exc).__name__}: {exc}"
    artifact["finishedAt"] = _now()
    artifact["elapsedMs"] = round((time.perf_counter() - started) * 1000)
    _write_json(artifact_path, artifact)
    claim_path.unlink()
    LOGGER.info("%s result written: %s", version, artifact_path)
    return exit_code


async def orchestrate(args: argparse.Namespace) -> int:
    manifest = _load_manifest(args.manifest)
    if _manifest_versions(manifest) != ALL_VERSIONS:
        msg = "orchestrate is only available for the v2/v3/v4 comparison scope; run v4 directly for v4-only"
        raise ValueError(msg)
    manifest_path = args.manifest.resolve()
    started_at = _now()
    phase_one = await asyncio.gather(
        run_version(argparse.Namespace(manifest=manifest_path, version="v2", timeout=args.timeout)),
        run_version(argparse.Namespace(manifest=manifest_path, version="v3", timeout=args.timeout)),
        return_exceptions=True,
    )
    phase_one_results = [
        {"version": version, "exitCode": result if isinstance(result, int) else None, "error": None}
        if isinstance(result, int)
        else {"version": version, "exitCode": None, "error": f"{type(result).__name__}: {result}"}
        for version, result in zip(("v2", "v3"), phase_one, strict=True)
    ]
    if not all(Path(manifest["artifacts"][version]).is_file() for version in ("v2", "v3")):  # noqa: ASYNC240
        v4_result: int | None = None
        v4_error = "v2/v3 artifact barrier not satisfied; v4 was not called."
    else:
        try:
            v4_result = await run_version(
                argparse.Namespace(manifest=manifest_path, version="v4", timeout=args.timeout),
            )
            v4_error = None
        except (TypeError, ValueError, FileNotFoundError, FileExistsError, httpx.HTTPError) as exc:
            v4_result = None
            v4_error = f"{type(exc).__name__}: {exc}"
    orchestration = {
        "mode": "async_fallback",
        "startedAt": started_at,
        "finishedAt": _now(),
        "phaseOne": phase_one_results,
        "phaseTwo": {"version": "v4", "exitCode": v4_result, "error": v4_error},
    }
    orchestration_path = Path(
        manifest["artifacts"].get(
            "orchestration",
            Path(manifest["artifacts"]["report"]).with_name("orchestration.json"),
        ),
    )
    _write_json(orchestration_path, orchestration)
    return 0 if all(item["exitCode"] == 0 for item in phase_one_results) and v4_result == 0 else 1


async def report(args: argparse.Namespace) -> Path:
    manifest = _load_manifest(args.manifest)
    versions = _manifest_versions(manifest)
    artifacts: dict[str, dict[str, Any]] = {}
    for version in versions:
        path = Path(manifest["artifacts"][version])
        artifacts[version] = (
            _read_json(path)
            if path.is_file()  # noqa: ASYNC240
            else {
                "transportStatus": "not_run",
                "error": f"artifact missing: {path}",
            }
        )

    checks: dict[str, list[Any]] = {}
    successful_responses: dict[str, dict[str, Any]] = {}
    if args.quality_check:
        for version in versions:
            artifact = artifacts[version]
            response = artifact.get("response")
            if (
                artifact.get("transportStatus") == "success"
                and artifact.get("outcome", "success") == "success"
                and isinstance(response, dict)
                and response.get("status") == "success"
                and isinstance(response.get("data"), dict)
            ):
                checks[version] = run_deterministic_checks(version, response, manifest["eventIds"])
                successful_responses[version] = response

    judge: ComparisonJudgment | None = None
    judge_error: str | None = None
    if args.quality_check and len(successful_responses) >= 2:
        evidence = {
            "eventIds": manifest["eventIds"],
            "events": manifest["events"],
            "versions": {
                version: _normalize_response_for_judge(response) for version, response in successful_responses.items()
            },
            "deterministicChecks": {
                version: [item.model_dump(mode="json") for item in version_checks]
                for version, version_checks in checks.items()
            },
            "performance": {
                version: {
                    "elapsedMs": artifacts[version].get("elapsedMs"),
                    "totalTokens": _field(
                        successful_responses[version]["data"].get("usage", {}),
                        "totalTokens",
                        "total_tokens",
                    ),
                }
                for version in successful_responses
            },
        }
        default_judge_path = Path(manifest["artifacts"]["judge"])
        judge_input_path = getattr(args, "judge_input", None) or Path(
            manifest["artifacts"].get("judgeInput", default_judge_path.with_name("comparison_judge_input.json")),
        )
        judge_result_path = getattr(args, "judge_result", None) or default_judge_path
        write_agent_judge_input(judge_input_path, build_agent_judge_input(evidence))
        LOGGER.info("Agent judge input written: %s", judge_input_path)
        LOGGER.info("Agent judge result expected: %s", judge_result_path)
        if getattr(args, "prepare_judge_only", False):
            return judge_input_path
        if judge_result_path.is_file():
            try:
                judge = load_agent_judgment(judge_result_path)
                _validate_judge(judge, successful_responses)
            except (OSError, ValueError) as exc:
                judge_error = f"agent judge result validation failure: {exc}"
                judge = None
        else:
            judge_error = (
                "agent judge pending: skill runtime model must evaluate "
                f"{judge_input_path} and write {judge_result_path}"
            )

    markdown = render_report(
        manifest,
        artifacts,
        checks,
        judge,
        quality_check=args.quality_check,
        judge_error=judge_error,
    )
    report_path = Path(manifest["artifacts"]["report"])
    report_path.write_text(markdown, encoding="utf-8")  # noqa: ASYNC240
    LOGGER.info("Report written: %s", report_path)
    return report_path


async def _select_event_ids(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    count: int,
    sort: str,
    keyword: str | None,
    page_size: int,
) -> list[int]:
    selected: list[int] = []
    page = 1
    while len(selected) < count:
        response = await client.get(
            f"{base_url}/events",
            params={
                "page": page,
                "pageSize": min(page_size, 100),
                "sort": sort,
                **({"keyword": keyword} if keyword else {}),
            },
        )
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            msg = "GET /events response does not contain rows[]"
            raise TypeError(msg)
        for row in rows:
            if not isinstance(row, dict):
                continue
            value = row.get("miEventId") or row.get("mi_event_id")
            if value is not None and int(value) not in selected:
                selected.append(int(value))
                if len(selected) == count:
                    break
        pagination = payload.get("pagination") if isinstance(payload.get("pagination"), dict) else {}
        has_next = pagination.get("hasNext", pagination.get("has_next", False))
        if len(selected) == count or not rows or not has_next:
            break
        page += 1
    if len(selected) != count:
        msg = f"Only {len(selected)} Events matched; requested {count}"
        raise ValueError(msg)
    return selected


async def _fetch_event_detail(client: httpx.AsyncClient, base_url: str, event_id: int) -> dict[str, Any]:
    response = await client.get(f"{base_url}/events/{event_id}")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        msg = f"GET /events/{event_id} returned a non-object payload"
        raise TypeError(msg)
    return payload


async def _soft_delete_existing_groups(
    client: httpx.AsyncClient,
    *,
    base_url: str,
    event_ids: list[int],
    user_id: int,
    admin_token: str | None,
) -> list[dict[str, Any]]:
    list_responses = await asyncio.gather(
        *(
            client.get(
                f"{base_url}/scenario-groups",
                params={
                    "includeDeleted": False,
                    "miEventId": event_id,
                    "sort": "latest",
                },
            )
            for event_id in event_ids
        ),
    )
    matched_event_ids_by_group: dict[int, set[int]] = {}
    for event_id, response in zip(event_ids, list_responses, strict=True):
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            msg = f"GET /scenario-groups response for Event {event_id} does not contain rows[]"
            raise TypeError(msg)
        for row in rows:
            if not isinstance(row, dict):
                continue
            group_id = _field(row, "scenarioGroupId", "scenario_group_id")
            if group_id is not None:
                matched_event_ids_by_group.setdefault(int(group_id), set()).add(event_id)

    if matched_event_ids_by_group and not admin_token:
        msg = (
            "Active Scenario Groups exist for the selected Events, but no admin token was provided. "
            "Use --admin-token or SCENARIO_GROUP_ADMIN_TOKEN."
        )
        raise ValueError(msg)

    headers = {"Authorization": f"Bearer {admin_token}"} if admin_token else None
    results: list[dict[str, Any]] = []
    for group_id, matched_event_ids in sorted(matched_event_ids_by_group.items()):
        response = await client.request(
            "DELETE",
            f"{base_url}/scenario-groups/{group_id}",
            json={"userId": user_id},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            msg = f"DELETE /scenario-groups/{group_id} returned a non-object payload"
            raise TypeError(msg)
        deleted_count = _field(payload, "scenarioGroupDeleted", "scenario_group_deleted")
        if int(deleted_count or 0) != 1:
            msg = f"Scenario Group {group_id} was not soft deleted: {payload}"
            raise ValueError(msg)
        results.append(
            {
                "scenarioGroupId": group_id,
                "matchedEventIds": sorted(matched_event_ids),
                "response": payload,
            },
        )
        LOGGER.info(
            "Soft deleted existing Scenario Group %s for Events %s",
            group_id,
            sorted(matched_event_ids),
        )
    return results


def _validate_prepare_args(args: argparse.Namespace) -> None:
    if args.event_ids:
        if args.keyword:
            msg = "--keyword can only be used with --event-count"
            raise ValueError(msg)
        if not 2 <= len(args.event_ids) <= 5:
            msg = "--event-ids must contain 2..5 IDs"
            raise ValueError(msg)
        if len(set(args.event_ids)) != len(args.event_ids):
            msg = "--event-ids must not contain duplicates"
            raise ValueError(msg)
        if any(value <= 0 for value in args.event_ids):
            msg = "--event-ids must contain positive IDs"
            raise ValueError(msg)
    elif not 2 <= args.event_count <= 5:
        msg = "--event-count must be between 2 and 5"
        raise ValueError(msg)
    if not 1 <= args.event_page_size <= 100:
        msg = "--event-page-size must be between 1 and 100"
        raise ValueError(msg)
    if args.comparison_run_id is not None and not args.comparison_run_id.strip():
        msg = "--comparison-run-id must not be blank"
        raise ValueError(msg)


def _load_manifest(path: Path) -> dict[str, Any]:
    manifest = _read_json(path.resolve())
    required = {
        "schemaVersion",
        "batchId",
        "baseUrl",
        "userId",
        "comparisonRunId",
        "eventIds",
        "artifacts",
    }
    missing = required - set(manifest)
    if missing:
        msg = f"Manifest is missing fields: {sorted(missing)}"
        raise ValueError(msg)
    if manifest["schemaVersion"] != 1:
        msg = f"Unsupported manifest schemaVersion={manifest['schemaVersion']}"
        raise ValueError(msg)
    _manifest_versions(manifest)
    event_ids = manifest["eventIds"]
    if not isinstance(event_ids, list) or not 2 <= len(event_ids) <= 5 or len(set(event_ids)) != len(event_ids):
        msg = "Manifest eventIds must contain 2..5 unique IDs"
        raise ValueError(msg)
    return manifest


def _manifest_versions(manifest: dict[str, Any]) -> tuple[ApiVersion, ...]:
    versions = manifest.get("versions")
    if versions is None:
        return ALL_VERSIONS
    if versions == list(ALL_VERSIONS):
        return ALL_VERSIONS
    if versions == list(V4_ONLY_VERSIONS):
        return V4_ONLY_VERSIONS
    msg = f"Manifest versions must be {list(ALL_VERSIONS)} or {list(V4_ONLY_VERSIONS)}: {versions}"
    raise ValueError(msg)


def _validate_version_scope(manifest: dict[str, Any], version: ApiVersion) -> None:
    versions = _manifest_versions(manifest)
    if version not in versions:
        msg = f"{version} is outside this manifest's execution scope: {list(versions)}"
        raise ValueError(msg)
    if version == "v4" and versions != V4_ONLY_VERSIONS:
        _require_v2_v3_barrier(manifest)


def _normalize_response_for_judge(response: dict[str, Any]) -> dict[str, Any]:
    data = response["data"]
    return {
        "apiVersion": data.get("apiVersion"),
        "generationStrategy": data.get("generationStrategy"),
        "scenarioGroup": data.get("scenarioGroup"),
        "dimensionDefinitions": data.get("dimensionDefinitions"),
        "table": data.get("table"),
        "generationDiagnostics": data.get("generationDiagnostics"),
    }


def _require_v2_v3_barrier(manifest: dict[str, Any]) -> None:
    missing = [version for version in ("v2", "v3") if not Path(manifest["artifacts"][version]).is_file()]
    if missing:
        msg = f"v4 requires completed v2/v3 artifacts; missing={missing}"
        raise ValueError(msg)


def _validate_version_response(
    response: dict[str, Any],
    manifest: dict[str, Any],
    version: ApiVersion,
) -> None:
    data = response.get("data")
    if not isinstance(data, dict):
        msg = "Successful response must contain data"
        raise TypeError(msg)
    if data.get("apiVersion") != version:
        msg = f"apiVersion mismatch: expected={version}, actual={data.get('apiVersion')}"
        raise ValueError(msg)
    if data.get("comparisonRunId") != manifest["comparisonRunId"]:
        msg = f"comparisonRunId mismatch: expected={manifest['comparisonRunId']}, actual={data.get('comparisonRunId')}"
        raise ValueError(msg)
    response_event_ids = {
        int(_field(event, "miEventId", "mi_event_id"))
        for event in data.get("events", [])
        if isinstance(event, dict) and _field(event, "miEventId", "mi_event_id") is not None
    }
    if response_event_ids != set(manifest["eventIds"]):
        msg = f"Event set mismatch: expected={sorted(manifest['eventIds'])}, actual={sorted(response_event_ids)}"
        raise ValueError(msg)


def _validate_judge(  # noqa: C901
    judge: ComparisonJudgment,
    responses: dict[str, dict[str, Any]],
) -> None:
    expected_versions = set(responses)
    actual_versions = [item.api_version for item in judge.versions]
    if set(actual_versions) != expected_versions or len(actual_versions) != len(set(actual_versions)):
        msg = f"Judge version set mismatch: expected={sorted(expected_versions)}, actual={actual_versions}"
        raise ValueError(msg)
    required_criteria = {
        "event_consistency",
        "lng_dimension_quality",
        "floor_ceiling_quality",
        "mixed_quality",
    }
    averages: dict[str, float] = {}
    for version in judge.versions:
        actual_criteria = [item.criterion for item in version.criteria]
        if set(actual_criteria) != required_criteria or len(actual_criteria) != 4:
            msg = f"Judge criteria mismatch for {version.api_version}: {actual_criteria}"
            raise ValueError(msg)
        rows = responses[version.api_version]["data"]["table"]["rows"]
        expected_ids = {str(row.get("scenarioId") or row.get("scenario_id")) for row in rows}
        actual_ids = [item.scenario_id for item in version.scenario_judgments]
        if set(actual_ids) != expected_ids or len(actual_ids) != len(set(actual_ids)):
            msg = (
                f"Judge scenario set mismatch for {version.api_version}: "
                f"expected={sorted(expected_ids)}, actual={actual_ids}"
            )
            raise ValueError(
                msg,
            )
        averages[version.api_version] = sum(item.score for item in version.criteria) / 4
    best_score = max(averages.values())
    expected_best = {version for version, score in averages.items() if score == best_score}
    if set(judge.best_versions) != expected_best:
        msg = f"Judge bestVersions mismatch: expected={sorted(expected_best)}, actual={judge.best_versions}"
        raise ValueError(msg)

    required_pairwise_criteria = {
        "event_grounding",
        "dimension_and_value_quality",
        "scenario_logic_and_explainability",
        "baseline_and_exclusion_quality",
        "user_comprehensibility",
    }
    expected_pairs = {
        frozenset((left, right))
        for index, left in enumerate(sorted(expected_versions))
        for right in sorted(expected_versions)[index + 1 :]
    }
    actual_pairs: list[frozenset[str]] = []
    for comparison in judge.pairwise_comparisons:
        pair = frozenset((comparison.left_version, comparison.right_version))
        if len(pair) != 2 or not pair.issubset(expected_versions):
            msg = f"Judge pairwise version mismatch: left={comparison.left_version}, right={comparison.right_version}"
            raise ValueError(msg)
        actual_pairs.append(pair)
        actual_criteria = [item.criterion for item in comparison.criteria]
        if set(actual_criteria) != required_pairwise_criteria or len(actual_criteria) != 5:
            msg = f"Judge pairwise criteria mismatch for {sorted(pair)}: {actual_criteria}"
            raise ValueError(msg)
        allowed_winners = {*pair, "tie"}
        invalid_winners = [item.winner for item in comparison.criteria if item.winner not in allowed_winners]
        if comparison.overall_winner not in allowed_winners:
            invalid_winners.append(comparison.overall_winner)
        if invalid_winners:
            msg = f"Judge pairwise winner mismatch for {sorted(pair)}: {invalid_winners}"
            raise ValueError(msg)
    if set(actual_pairs) != expected_pairs or len(actual_pairs) != len(set(actual_pairs)):
        msg = f"Judge pairwise set mismatch: expected={expected_pairs}, actual={actual_pairs}"
        raise ValueError(msg)

    for label, recommendation in (
        ("qualityRecommendation", judge.quality_recommendation),
        ("practicalRecommendation", judge.practical_recommendation),
    ):
        versions = recommendation.versions
        if not set(versions).issubset(expected_versions) or len(versions) != len(set(versions)):
            msg = f"Judge {label} version mismatch: expected subset of {sorted(expected_versions)}, actual={versions}"
            raise ValueError(msg)


def _event_id(detail: dict[str, Any]) -> int:
    event = detail.get("event") if isinstance(detail.get("event"), dict) else detail
    value = event.get("miEventId") or event.get("mi_event_id")
    if value is None:
        msg = "Event detail is missing miEventId"
        raise ValueError(msg)
    return int(value)


def _field(payload: dict[str, Any], *names: str) -> Any:  # noqa: ANN401
    return next((payload[name] for name in names if name in payload), None)


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    msg = "expected true or false"
    raise argparse.ArgumentTypeError(msg)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        msg = f"Expected JSON object: {path}"
        raise ValueError(msg)  # noqa: TRY004
    return payload


def _write_json(path: Path, payload: Any) -> None:  # noqa: ANN401
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def _claim_version(path: Path, version: ApiVersion) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        msg = (
            f"{version} is already claimed by another process or has uncertain prior state: {path}. "
            "Do not remove the claim until server state has been checked."
        )
        raise FileExistsError(msg) from exc
    claim = json.dumps(
        {"apiVersion": version, "pid": os.getpid(), "claimedAt": _now()},
        ensure_ascii=False,
    ).encode()
    try:
        os.write(descriptor, claim)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _now() -> str:
    return datetime.now(UTC).isoformat()


async def async_main() -> int:
    args = parse_args()
    if args.command == "prepare":
        await prepare(args)
        return 0
    if args.command == "run-version":
        return await run_version(args)
    if args.command == "orchestrate":
        return await orchestrate(args)
    if args.command == "report":
        await report(args)
        return 0
    msg = f"Unsupported command: {args.command}"
    raise ValueError(msg)


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        return asyncio.run(async_main())
    except (TypeError, ValueError, FileNotFoundError, FileExistsError, httpx.HTTPError):
        LOGGER.exception("Multi-event comparison command failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
