from __future__ import annotations

# ruff: noqa: CPY001
import argparse
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
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

from tests.manual.quality_eval.runtime_config import AGENT_ALIASES, load_runtime_target  # noqa: E402


OUTPUT_ROOT = Path("local/output/sse_scenario_group_api_test")
LOGGER = logging.getLogger("sse_scenario_group_api")
ALLOWED_EVENT_TYPES = {
    "accepted",
    "phase_started",
    "retrying",
    "validated",
    "section_ready",
    "completed",
    "failed",
    "interrupted",
}
TERMINAL_EVENT_TYPES = {"completed", "failed", "interrupted"}
PRESENTATION_STATUSES = {"pending", "partial", "ready", "unavailable"}
EVIDENCE_LEVELS = {"full", "limited", "none"}


@dataclass(frozen=True)
class SSEFrame:
    event_id: int
    event_type: str
    data: dict[str, Any]


@dataclass
class StreamContractState:
    last_sequence: int = 0
    scenario_group_id: int | None = None
    operation_id: str | None = None
    snapshot_revision: int = 0
    last_section_ready_revision: int = 0
    terminal_event: str | None = None
    event_types: list[str] = field(default_factory=list)

    def accept(self, frame: SSEFrame) -> bool:  # noqa: C901
        if self.terminal_event is not None:
            msg = f"SSE event received after terminal event {self.terminal_event}"
            raise ValueError(msg)
        if frame.event_type not in ALLOWED_EVENT_TYPES:
            msg = f"Unsupported SSE event type: {frame.event_type}"
            raise ValueError(msg)
        expected_sequence = self.last_sequence + 1
        if frame.event_id != expected_sequence:
            msg = f"SSE sequence gap or duplicate: expected={expected_sequence}, actual={frame.event_id}"
            raise ValueError(msg)
        if _required_int(frame.data, "sequence") != frame.event_id:
            msg = f"SSE id/data.sequence mismatch at sequence {frame.event_id}"
            raise ValueError(msg)
        if _required_str(frame.data, "eventType") != frame.event_type:
            msg = f"SSE event/data.eventType mismatch at sequence {frame.event_id}"
            raise ValueError(msg)

        group_id = _required_int(frame.data, "scenarioGroupId")
        operation_id = _required_str(frame.data, "operationId")
        revision = _required_int(frame.data, "snapshotRevision")
        if revision < self.snapshot_revision:
            msg = f"snapshotRevision decreased: previous={self.snapshot_revision}, actual={revision}"
            raise ValueError(msg)

        if self.last_sequence == 0:
            if frame.event_type != "accepted":
                msg = f"The first SSE event must be accepted, got {frame.event_type}"
                raise ValueError(msg)
            if frame.data.get("engineVersion") != "v4":
                msg = f"accepted.engineVersion must be v4, got {frame.data.get('engineVersion')!r}"
                raise ValueError(msg)
            self.scenario_group_id = group_id
            self.operation_id = operation_id
        elif group_id != self.scenario_group_id or operation_id != self.operation_id:
            msg = (
                "SSE resource identity changed: "
                f"expected=({self.scenario_group_id}, {self.operation_id}), actual=({group_id}, {operation_id})"
            )
            raise ValueError(msg)

        if frame.event_type == "completed" and frame.data.get("status") != "succeeded":
            msg = f"completed.status must be succeeded, got {frame.data.get('status')!r}"
            raise ValueError(msg)
        if frame.event_type in TERMINAL_EVENT_TYPES:
            self.terminal_event = frame.event_type

        should_refresh = frame.event_type == "section_ready" and revision > self.last_section_ready_revision
        if should_refresh:
            self.last_section_ready_revision = revision
        self.last_sequence = frame.event_id
        self.snapshot_revision = revision
        self.event_types.append(frame.event_type)
        return should_refresh


def parse_sse_lines(lines: Iterable[str]) -> Iterator[SSEFrame]:  # noqa: C901
    event_id: str | None = None
    event_type: str | None = None
    data_lines: list[str] = []

    def build_frame() -> SSEFrame | None:
        if event_id is None and event_type is None and not data_lines:
            return None
        if event_id is None or event_type is None or not data_lines:
            msg = "Incomplete SSE frame; id, event, and data are required"
            raise ValueError(msg)
        try:
            parsed_id = int(event_id)
        except ValueError as exc:
            msg = f"SSE id must be an integer, got {event_id!r}"
            raise ValueError(msg) from exc
        try:
            payload = json.loads("\n".join(data_lines))
        except json.JSONDecodeError as exc:
            msg = f"SSE data is not valid JSON at id {parsed_id}: {exc}"
            raise ValueError(msg) from exc
        if not isinstance(payload, dict):
            msg = f"SSE data must be a JSON object at id {parsed_id}"
            raise TypeError(msg)
        return SSEFrame(event_id=parsed_id, event_type=event_type, data=payload)

    for raw_line in lines:
        line = raw_line.rstrip("\r\n")
        if not line:
            frame = build_frame()
            if frame is not None:
                yield frame
            event_id = None
            event_type = None
            data_lines = []
            continue
        if line.startswith(":"):
            continue
        field_name, separator, value = line.partition(":")
        if separator and value.startswith(" "):
            value = value[1:]
        if field_name == "id":
            event_id = value
        elif field_name == "event":
            event_type = value
        elif field_name == "data":
            data_lines.append(value)

    frame = build_frame()
    if frame is not None:
        yield frame


def validate_presentation(  # noqa: C901
    payload: dict[str, Any],
    *,
    scenario_group_id: int,
    operation_id: str,
    minimum_sequence: int,
    minimum_revision: int,
    final: bool,
) -> None:
    if payload.get("schemaVersion") != "v1":
        msg = f"Presentation schemaVersion must be v1, got {payload.get('schemaVersion')!r}"
        raise ValueError(msg)
    if _required_int(payload, "scenarioGroupId") != scenario_group_id:
        msg = "Presentation scenarioGroupId does not match the SSE resource"
        raise ValueError(msg)
    if payload.get("engineVersion") != "v4":
        msg = f"Presentation engineVersion must be v4, got {payload.get('engineVersion')!r}"
        raise ValueError(msg)

    operation = _required_dict(payload, "operation")
    if _required_str(operation, "operationId") != operation_id:
        msg = "Presentation operationId does not match the SSE resource"
        raise ValueError(msg)
    if _required_int(operation, "latestSequence") < minimum_sequence:
        msg = "Presentation latestSequence is behind the triggering SSE event"
        raise ValueError(msg)
    if _required_int(operation, "snapshotRevision") < minimum_revision:
        msg = "Presentation snapshotRevision is behind the triggering SSE event"
        raise ValueError(msg)

    sections = _required_dict(payload, "sections")
    event_analysis = _validate_markdown_section(sections, "eventAnalysis")
    role_rationale = _validate_markdown_section(sections, "roleSelectionRationale")
    scenario_design = _required_dict(sections, "scenarioDesign")
    _validate_status_and_evidence(scenario_design, "scenarioDesign")
    definitions = _required_dict(scenario_design, "dimensionDefinitions")
    table = _required_dict(scenario_design, "scenarioTable")
    _validate_status(definitions, "scenarioDesign.dimensionDefinitions")
    _validate_status(table, "scenarioDesign.scenarioTable")

    if not final:
        return
    if operation.get("status") != "succeeded":
        msg = f"Final Presentation operation.status must be succeeded, got {operation.get('status')!r}"
        raise ValueError(msg)
    final_statuses = {
        "eventAnalysis": event_analysis.get("status"),
        "scenarioDesign": scenario_design.get("status"),
        "dimensionDefinitions": definitions.get("status"),
        "scenarioTable": table.get("status"),
        "roleSelectionRationale": role_rationale.get("status"),
    }
    not_ready = {name: status for name, status in final_statuses.items() if status != "ready"}
    if not_ready:
        msg = f"Final Presentation sections must be ready: {not_ready}"
        raise ValueError(msg)

    items = definitions.get("items")
    if not isinstance(items, list) or not 3 <= len(items) <= 6:
        actual_count = len(items) if isinstance(items, list) else None
        msg = f"Final v4 Presentation must contain 3..6 dimensions, got {actual_count}"
        raise ValueError(msg)
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            msg = f"dimensionDefinitions.items[{index}] must be an object"
            raise TypeError(msg)
        rationale = _required_str(item, "rationale").strip()
        if not 10 <= len(rationale) <= 100:
            msg = f"dimensionDefinitions.items[{index}].rationale must contain 10..100 characters"
            raise ValueError(msg)

    rows = table.get("rows")
    if not isinstance(rows, list) or not 3 <= len(rows) <= 5:
        actual_count = len(rows) if isinstance(rows, list) else None
        msg = f"Final v4 Presentation must contain 3..5 Scenario rows, got {actual_count}"
        raise ValueError(msg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test canonical POST /scenario-groups SSE creation and the Presentation read model.",
    )
    parser.add_argument("--agent", choices=sorted(AGENT_ALIASES))
    parser.add_argument("--base-url", help="Takes precedence over --agent and test_info.local.")
    parser.add_argument("--user-id", type=int)
    parser.add_argument("--test-info", type=Path)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--event-ids", type=int, nargs="+", help="Explicit, unique Event IDs (1..5).")
    selection.add_argument("--event-count", type=int, help="Select this many Events (1..5) through GET /events.")
    parser.add_argument("--event-sort", choices=["latest", "oldest"], default="latest")
    parser.add_argument("--keyword", help="Optional GET /events keyword, only with --event-count.")
    parser.add_argument("--event-page-size", type=int, default=100)
    parser.add_argument("--timeout", type=float, default=1200)
    parser.add_argument("--batch-id", help="Defaults to timestamp plus a random suffix.")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument(
        "--delete-existing",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Soft delete active Scenario Groups related to the selected Events before creation.",
    )
    parser.add_argument("--admin-token", help="Defaults to SCENARIO_GROUP_ADMIN_TOKEN.")
    return parser.parse_args()


def run(args: argparse.Namespace) -> int:
    _validate_args(args)
    target = load_runtime_target(
        agent=args.agent,
        base_url=args.base_url,
        user_id=args.user_id,
        test_info_path=args.test_info,
    )
    base_url = target.base_url or "http://localhost:8000"
    batch_id = args.batch_id or f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
    artifact_dir = (args.output_root / batch_id).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=False)
    started_at = _now()
    started = time.perf_counter()
    events: list[dict[str, Any]] = []
    presentations: list[dict[str, Any]] = []
    state = StreamContractState()
    result: dict[str, Any] = {
        "schemaVersion": 1,
        "batchId": batch_id,
        "startedAt": started_at,
        "baseUrl": base_url,
        "userId": target.user_id,
        "status": "running",
        "artifacts": {},
    }
    exit_code = 1

    timeout = httpx.Timeout(args.timeout, connect=min(args.timeout, 30.0))
    try:
        with httpx.Client(timeout=timeout) as client:
            event_ids = _select_event_ids(client, base_url, args)
            event_details = [_fetch_event_detail(client, base_url, event_id) for event_id in event_ids]
            _validate_event_details(event_ids, event_details)
            cleanup_results = (
                _soft_delete_existing_groups(
                    client,
                    base_url=base_url,
                    event_ids=event_ids,
                    user_id=target.user_id,
                    admin_token=args.admin_token or os.environ.get("SCENARIO_GROUP_ADMIN_TOKEN"),
                )
                if args.delete_existing
                else []
            )
            _write_json(artifact_dir / "selected_events.json", event_details)
            _write_json(
                artifact_dir / "existing_groups_soft_delete.json",
                {
                    "requested": args.delete_existing,
                    "deletedGroupCount": len(cleanup_results),
                    "groups": cleanup_results,
                },
            )
            result["eventIds"] = event_ids
            result["preRunCleanup"] = {
                "requested": args.delete_existing,
                "deletedGroupCount": len(cleanup_results),
            }

            request_body = {"miEventIds": event_ids, "userId": target.user_id}
            result["request"] = request_body
            create_url = f"{base_url}/scenario-groups"
            with client.stream("POST", create_url, json=request_body) as response:
                result["createResponse"] = {
                    "httpStatus": response.status_code,
                    "contentType": response.headers.get("content-type"),
                    "cacheControl": response.headers.get("cache-control"),
                    "xAccelBuffering": response.headers.get("x-accel-buffering"),
                }
                _validate_sse_response(response)
                for frame in parse_sse_lines(response.iter_lines()):
                    should_refresh = state.accept(frame)
                    events.append(
                        {
                            "id": frame.event_id,
                            "event": frame.event_type,
                            "data": frame.data,
                        },
                    )
                    LOGGER.info(
                        "SSE sequence=%s event=%s phase=%s revision=%s",
                        frame.event_id,
                        frame.event_type,
                        frame.data.get("phase"),
                        frame.data.get("snapshotRevision"),
                    )
                    if should_refresh:
                        presentations.append(
                            _fetch_and_validate_presentation(
                                client,
                                base_url=base_url,
                                state=state,
                                artifact_dir=artifact_dir,
                                final=False,
                            ),
                        )
                    if frame.event_type == "completed":
                        presentations.append(
                            _fetch_and_validate_presentation(
                                client,
                                base_url=base_url,
                                state=state,
                                artifact_dir=artifact_dir,
                                final=True,
                            ),
                        )
                    if frame.event_type in TERMINAL_EVENT_TYPES:
                        break

            _validate_terminal_event(state.terminal_event)
            result["status"] = "success"
            exit_code = 0
    except (OSError, TypeError, ValueError, httpx.HTTPError) as exc:
        result["status"] = "failure"
        result["error"] = f"{type(exc).__name__}: {exc}"
        LOGGER.exception("SSE Scenario Group API test failed")
    finally:
        result["finishedAt"] = _now()
        result["elapsedMs"] = round((time.perf_counter() - started) * 1000)
        result["scenarioGroupId"] = state.scenario_group_id
        result["operationId"] = state.operation_id
        result["lastSequence"] = state.last_sequence
        result["snapshotRevision"] = state.snapshot_revision
        result["terminalEvent"] = state.terminal_event
        result["eventTypes"] = state.event_types
        result["presentationFetchCount"] = len(presentations)
        result["artifacts"] = {
            "selectedEvents": str(artifact_dir / "selected_events.json"),
            "preRunCleanup": str(artifact_dir / "existing_groups_soft_delete.json"),
            "events": str(artifact_dir / "sse_events.json"),
            "presentations": str(artifact_dir / "presentations"),
            "presentationRequests": str(artifact_dir / "presentation_requests.json"),
            "result": str(artifact_dir / "result.json"),
            "report": str(artifact_dir / "report.md"),
        }
        _write_json(artifact_dir / "sse_events.json", events)
        _write_json(artifact_dir / "presentation_requests.json", presentations)
        _write_json(artifact_dir / "result.json", result)
        (artifact_dir / "report.md").write_text(_render_report(result, presentations), encoding="utf-8")
        LOGGER.info("Artifacts written: %s", artifact_dir)
    return exit_code


def _fetch_and_validate_presentation(
    client: httpx.Client,
    *,
    base_url: str,
    state: StreamContractState,
    artifact_dir: Path,
    final: bool,
) -> dict[str, Any]:
    if state.scenario_group_id is None or state.operation_id is None:
        msg = "Cannot fetch Presentation before accepted"
        raise ValueError(msg)
    url = f"{base_url}/scenario-groups/{state.scenario_group_id}/presentation"
    params = {"operationId": state.operation_id}
    response = client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        msg = "Presentation response must be a JSON object"
        raise TypeError(msg)
    validate_presentation(
        payload,
        scenario_group_id=state.scenario_group_id,
        operation_id=state.operation_id,
        minimum_sequence=state.last_sequence,
        minimum_revision=state.snapshot_revision,
        final=final,
    )
    etag = response.headers.get("etag")
    if not etag:
        msg = "Presentation response is missing ETag"
        raise ValueError(msg)
    cached = client.get(url, params=params, headers={"If-None-Match": etag})
    if cached.status_code != 304 or cached.content:
        msg = f"Presentation conditional GET must return empty HTTP 304, got HTTP {cached.status_code}"
        raise ValueError(msg)
    if cached.headers.get("etag") != etag:
        msg = "Presentation HTTP 304 must preserve the ETag"
        raise ValueError(msg)

    suffix = "final" if final else f"revision_{state.snapshot_revision}_sequence_{state.last_sequence}"
    path = artifact_dir / "presentations" / f"presentation_{suffix}.json"
    _write_json(path, payload)
    return {
        "trigger": "completed" if final else "section_ready",
        "sequence": state.last_sequence,
        "snapshotRevision": state.snapshot_revision,
        "etag": etag,
        "conditionalStatus": cached.status_code,
        "artifact": str(path),
    }


def _validate_sse_response(response: httpx.Response) -> None:
    if response.status_code != 200:
        response.read()
        try:
            detail = response.json()
        except json.JSONDecodeError:
            detail = response.text
        msg = f"POST /scenario-groups returned HTTP {response.status_code}: {detail}"
        raise ValueError(msg)
    content_type = response.headers.get("content-type", "")
    if "text/event-stream" not in content_type.lower():
        msg = f"POST /scenario-groups must return text/event-stream, got {content_type!r}"
        raise ValueError(msg)
    if "no-cache" not in response.headers.get("cache-control", "").lower():
        msg = "POST /scenario-groups response is missing Cache-Control: no-cache"
        raise ValueError(msg)
    if response.headers.get("x-accel-buffering", "").lower() != "no":
        msg = "POST /scenario-groups response is missing X-Accel-Buffering: no"
        raise ValueError(msg)


def _select_event_ids(client: httpx.Client, base_url: str, args: argparse.Namespace) -> list[int]:
    if args.event_ids:
        return list(args.event_ids)
    selected: list[int] = []
    page = 1
    while len(selected) < args.event_count:
        response = client.get(
            f"{base_url}/events",
            params={
                "page": page,
                "pageSize": args.event_page_size,
                "sort": args.event_sort,
                **({"keyword": args.keyword} if args.keyword else {}),
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
            value = _field(row, "miEventId", "mi_event_id")
            if value is not None and int(value) not in selected:
                selected.append(int(value))
                if len(selected) == args.event_count:
                    break
        pagination = payload.get("pagination") if isinstance(payload, dict) else None
        has_next = bool(_field(pagination, "hasNext", "has_next")) if isinstance(pagination, dict) else False
        if len(selected) == args.event_count or not rows or not has_next:
            break
        page += 1
    if len(selected) != args.event_count:
        msg = f"Only {len(selected)} Events matched; requested {args.event_count}"
        raise ValueError(msg)
    return selected


def _fetch_event_detail(client: httpx.Client, base_url: str, event_id: int) -> dict[str, Any]:
    response = client.get(f"{base_url}/events/{event_id}")
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        msg = f"GET /events/{event_id} returned a non-object payload"
        raise TypeError(msg)
    return payload


def _soft_delete_existing_groups(
    client: httpx.Client,
    *,
    base_url: str,
    event_ids: list[int],
    user_id: int,
    admin_token: str | None,
) -> list[dict[str, Any]]:
    matched_event_ids_by_group: dict[int, set[int]] = {}
    for event_id in event_ids:
        response = client.get(
            f"{base_url}/scenario-groups",
            params={"includeDeleted": False, "miEventId": event_id, "sort": "latest"},
        )
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
        response = client.request(
            "DELETE",
            f"{base_url}/scenario-groups/{group_id}",
            json={"userId": user_id},
            headers=headers,
        )
        response.raise_for_status()
        payload = response.json()
        deleted_count = (
            _field(payload, "scenarioGroupDeleted", "scenario_group_deleted") if isinstance(payload, dict) else 0
        )
        if not isinstance(payload, dict) or int(deleted_count or 0) != 1:
            msg = f"Scenario Group {group_id} was not soft deleted: {payload}"
            raise ValueError(msg)
        results.append(
            {
                "scenarioGroupId": group_id,
                "matchedEventIds": sorted(matched_event_ids),
                "response": payload,
            },
        )
    return results


def _validate_args(args: argparse.Namespace) -> None:
    if args.timeout <= 0:
        msg = "--timeout must be positive"
        raise ValueError(msg)
    if args.event_ids:
        if args.keyword:
            msg = "--keyword can only be used with --event-count"
            raise ValueError(msg)
        if not 1 <= len(args.event_ids) <= 5:
            msg = "--event-ids must contain 1..5 IDs"
            raise ValueError(msg)
        if len(set(args.event_ids)) != len(args.event_ids) or any(value <= 0 for value in args.event_ids):
            msg = "--event-ids must contain unique positive IDs"
            raise ValueError(msg)
    elif args.event_count is None or not 1 <= args.event_count <= 5:
        msg = "--event-count must be between 1 and 5"
        raise ValueError(msg)
    if not 1 <= args.event_page_size <= 100:
        msg = "--event-page-size must be between 1 and 100"
        raise ValueError(msg)


def _validate_terminal_event(terminal_event: str | None) -> None:
    if terminal_event is None:
        msg = "SSE stream ended without a terminal event"
        raise ValueError(msg)
    if terminal_event != "completed":
        msg = f"Scenario Group creation ended with {terminal_event}"
        raise ValueError(msg)


def _validate_event_details(event_ids: list[int], details: list[dict[str, Any]]) -> None:
    actual_ids: list[int] = []
    for detail in details:
        event = detail.get("event") if isinstance(detail.get("event"), dict) else detail
        actual_ids.append(_required_int(event, "miEventId", "mi_event_id"))
    if actual_ids != event_ids:
        msg = f"Event detail order mismatch: expected={event_ids}, actual={actual_ids}"
        raise ValueError(msg)


def _validate_markdown_section(sections: dict[str, Any], name: str) -> dict[str, Any]:
    section = _required_dict(sections, name)
    _validate_status_and_evidence(section, name)
    if section.get("contentType") != "text/markdown":
        msg = f"Presentation {name}.contentType must be text/markdown"
        raise ValueError(msg)
    if not isinstance(section.get("markdown"), str):
        msg = f"Presentation {name}.markdown must be a string"
        raise TypeError(msg)
    return section


def _validate_status_and_evidence(section: dict[str, Any], name: str) -> None:
    _validate_status(section, name)
    if section.get("evidenceLevel") not in EVIDENCE_LEVELS:
        msg = f"Presentation {name}.evidenceLevel is invalid: {section.get('evidenceLevel')!r}"
        raise ValueError(msg)


def _validate_status(section: dict[str, Any], name: str) -> None:
    if section.get("status") not in PRESENTATION_STATUSES:
        msg = f"Presentation {name}.status is invalid: {section.get('status')!r}"
        raise ValueError(msg)


def _required_dict(payload: dict[str, Any], name: str) -> dict[str, Any]:
    value = payload.get(name)
    if not isinstance(value, dict):
        msg = f"{name} must be an object"
        raise TypeError(msg)
    return value


def _required_int(payload: dict[str, Any], *names: str) -> int:
    value = _field(payload, *names)
    if isinstance(value, bool):
        msg = f"{names[0]} must be an integer"
        raise TypeError(msg)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        msg = f"{names[0]} must be an integer"
        raise TypeError(msg) from exc


def _required_str(payload: dict[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str) or not value:
        msg = f"{name} must be a non-empty string"
        raise TypeError(msg)
    return value


def _field(payload: dict[str, Any] | None, *names: str) -> Any:  # noqa: ANN401
    if payload is None:
        return None
    return next((payload[name] for name in names if name in payload), None)


def _write_json(path: Path, payload: Any) -> None:  # noqa: ANN401
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def _render_report(result: dict[str, Any], presentations: list[dict[str, Any]]) -> str:
    event_types = " → ".join(result.get("eventTypes", [])) or "-"
    presentation_rows = (
        "\n".join(
            f"| {item['trigger']} | {item['sequence']} | {item['snapshotRevision']} | {item['conditionalStatus']} |"
            for item in presentations
        )
        or "| - | - | - | - |"
    )
    error = result.get("error") or "-"
    return f"""# SSE Scenario Group API 테스트 결과

- 상태: `{result.get("status")}`
- Event IDs: `{result.get("eventIds", [])}`
- Scenario Group ID: `{result.get("scenarioGroupId")}`
- Operation ID: `{result.get("operationId")}`
- Terminal event: `{result.get("terminalEvent")}`
- 마지막 sequence / snapshot revision: `{result.get("lastSequence")}` / `{result.get("snapshotRevision")}`
- 수행시간: `{result.get("elapsedMs")} ms`
- 오류: `{error}`

## SSE 이벤트 순서

{event_types}

## Presentation 조회

| Trigger | SSE sequence | Snapshot revision | ETag 재조회 HTTP |
| --- | ---: | ---: | ---: |
{presentation_rows}

## 판정 기준

- POST 응답의 HTTP 200, `text/event-stream`, no-cache/buffering 방지 header
- 첫 `accepted`, 연속 sequence, SSE id와 JSON sequence/event type 일치, resource ID 불변
- revision이 증가한 `section_ready` 및 `completed`에서 Presentation 조회
- Presentation의 v1 공통 schema, v4 engine, 공통 3-section, 최종 ready 상태
- 최종 Dimension 3~6개, rationale 10~100자, Scenario 3~5개
- 동일 ETag의 conditional GET이 빈 HTTP 304 반환
"""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        return run(parse_args())
    except (OSError, TypeError, ValueError, httpx.HTTPError):
        LOGGER.exception("SSE Scenario Group API test setup failed")
        return 2


if __name__ == "__main__":
    sys.exit(main())
