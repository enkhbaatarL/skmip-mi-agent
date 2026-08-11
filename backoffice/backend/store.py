from __future__ import annotations

import asyncio
from collections import defaultdict
from copy import deepcopy
from typing import Any
from uuid import uuid4

from backoffice.backend.schemas import (
    CallbackType,
    ErrorRecord,
    JsonObject,
    NormalizedScenarioDesign,
    RunLifecycleState,
    RunRecord,
    ScenarioGroupModel,
    ScenarioGroupListRow,
    ScenarioHeader,
    ScenarioRow,
    ScenarioTable,
    SignpostModel,
    SseEventType,
    TimelineEvent,
)


class BackofficeStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._scenario_group_runs: dict[int, str] = {}
        self._orphan_callbacks: dict[int, list[tuple[CallbackType, JsonObject]]] = defaultdict(list)
        self._deleted_scenario_groups: dict[int, JsonObject] = {}
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def create_run(self, mi_event_id: int, user_id: int, agent_base_url: str) -> RunRecord:
        async with self._lock:
            run = RunRecord(
                run_id=uuid4().hex,
                mi_event_id=mi_event_id,
                user_id=user_id,
                agent_base_url=agent_base_url,
                lifecycle_state=RunLifecycleState.CREATING,
            )
            run.timeline.append(TimelineEvent(type="run_created", message="Run created"))
            self._runs[run.run_id] = run
            return deepcopy(run)

    async def get_run(self, run_id: str) -> RunRecord | None:
        async with self._lock:
            run = self._runs.get(run_id)
            return deepcopy(run) if run is not None else None

    async def find_run_by_scenario_group_id(self, scenario_group_id: int) -> RunRecord | None:
        async with self._lock:
            run_id = self._scenario_group_runs.get(scenario_group_id)
            run = self._runs.get(run_id) if run_id is not None else None
            return deepcopy(run) if run is not None else None

    async def list_scenario_groups(
        self,
        include_deleted: bool = False,
        keyword: str | None = None,
        status: str | None = None,
        stage: str | None = None,
        mi_event_id: int | None = None,
        sort: str = "latest",
    ) -> list[ScenarioGroupListRow]:
        async with self._lock:
            rows_by_group: dict[int, ScenarioGroupListRow] = {}
            for run in self._runs.values():
                if run.scenario_group_id is None:
                    continue
                row = self._row_from_run(run)
                if row is None:
                    continue
                previous = rows_by_group.get(row.scenario_group_id)
                if previous is None or (row.updated_at or row.created_at or 0) >= (previous.updated_at or previous.created_at or 0):
                    rows_by_group[row.scenario_group_id] = row
            rows = list(rows_by_group.values())
            for scenario_group_id, marker in self._deleted_scenario_groups.items():
                if any(row.scenario_group_id == scenario_group_id for row in rows):
                    continue
                rows.append(
                    ScenarioGroupListRow(
                        scenario_group_id=scenario_group_id,
                        title=str(marker.get("title") or f"Scenario Group {scenario_group_id}"),
                        base_event_title=marker.get("baseEventTitle"),
                        mi_event_id=marker.get("miEventId"),
                        status=marker.get("status"),
                        stage=marker.get("stage"),
                        deleted=True,
                        del_yn="Y",
                        source="backoffice_deleted_marker",
                        raw=deepcopy(marker),
                    )
                )
            filtered = [row for row in rows if include_deleted or not row.deleted]
            if mi_event_id is not None:
                filtered = [row for row in filtered if row.mi_event_id == mi_event_id]
            if status:
                filtered = [row for row in filtered if (row.status or "").lower() == status.lower()]
            if stage:
                filtered = [row for row in filtered if (row.stage or "").lower() == stage.lower()]
            if keyword:
                needle = keyword.lower()
                filtered = [
                    row
                    for row in filtered
                    if needle in str(row.scenario_group_id).lower()
                    or needle in row.title.lower()
                    or needle in (row.base_event_title or "").lower()
                ]
            reverse = sort != "oldest"
            filtered.sort(key=lambda row: row.updated_at or row.created_at or 0, reverse=reverse)
            return deepcopy(filtered)

    async def bind_accepted(self, run_id: str, action: str, accepted: JsonObject) -> RunRecord:
        events: list[tuple[SseEventType, JsonObject]] = []
        async with self._lock:
            run = self._require_run(run_id)
            run.accepted[action] = deepcopy(accepted)
            run.timeline.append(TimelineEvent(type="accepted", message=f"{action} accepted", data=accepted))
            self._apply_agent_status(run, accepted)
            run.lifecycle_state = _waiting_state_for_action(action)
            scenario_group_id = _extract_scenario_group_id(accepted)
            if scenario_group_id is not None:
                run.scenario_group_id = scenario_group_id
                self._scenario_group_runs[scenario_group_id] = run_id
                events.extend(self._attach_orphans_locked(run, scenario_group_id))
            event = {"runId": run_id, "action": action, "accepted": accepted, "run": run.model_dump(by_alias=True)}
            events.insert(0, (SseEventType.ACCEPTED, event))
            snapshot = deepcopy(run)
        await self._publish_many(run_id, events)
        return snapshot

    async def record_request(
        self,
        run_id: str,
        action: str,
        payload: JsonObject,
        state: RunLifecycleState,
        agent_payload: JsonObject | None = None,
    ) -> RunRecord:
        async with self._lock:
            run = self._require_run(run_id)
            run.latest_requests[action] = deepcopy(payload)
            if agent_payload is not None:
                run.latest_agent_requests[action] = deepcopy(agent_payload)
            run.lifecycle_state = state
            run.timeline.append(TimelineEvent(type="request", message=f"{action} requested", data=payload))
            return deepcopy(run)

    async def record_detail(self, run_id: str, detail: JsonObject) -> RunRecord:
        async with self._lock:
            run = self._require_run(run_id)
            run.detail = deepcopy(detail)
            run.timeline.append(TimelineEvent(type="detail_refreshed", message="Scenario group detail refreshed"))
            self._apply_agent_status(run, detail)
            run.normalized = normalize_payload(detail)
            snapshot = deepcopy(run)
        await self._publish(run_id, SseEventType.DETAIL_REFRESHED, {"runId": run_id, "detail": detail, "run": snapshot.model_dump(by_alias=True)})
        await self._publish(
            run_id,
            SseEventType.NORMALIZED_MODEL_UPDATED,
            {"runId": run_id, "normalized": snapshot.normalized.model_dump(by_alias=True)},
        )
        return snapshot

    async def mark_scenario_group_deleted(
        self,
        scenario_group_id: int,
        user_id: int,
        raw_response: JsonObject,
    ) -> RunRecord | None:
        async with self._lock:
            run_id = self._scenario_group_runs.get(scenario_group_id)
            run = self._runs.get(run_id) if run_id is not None else None
            marker = {"scenarioGroupId": scenario_group_id, "deletedBy": user_id, "rawResponse": deepcopy(raw_response)}
            if run is not None:
                row = self._row_from_run(run)
                if row is not None:
                    marker.update(row.model_dump(by_alias=True))
                run.timeline.append(TimelineEvent(type="soft_delete", message="Scenario group soft deleted", data=raw_response))
                run.detail = _mark_detail_deleted(run.detail)
                run.normalized.scenario_group_detail = _mark_detail_deleted(run.normalized.scenario_group_detail)
                snapshot = deepcopy(run)
            else:
                snapshot = None
            self._deleted_scenario_groups[scenario_group_id] = marker
        if snapshot is not None:
            await self._publish(
                snapshot.run_id,
                SseEventType.DETAIL_REFRESHED,
                {"runId": snapshot.run_id, "scenarioGroupId": scenario_group_id, "deleted": True, "run": snapshot.model_dump(by_alias=True)},
            )
        return snapshot

    async def record_callback(self, scenario_group_id: int, callback_type: CallbackType, payload: JsonObject) -> RunRecord | None:
        events: list[tuple[SseEventType, JsonObject]] = []
        async with self._lock:
            run_id = self._scenario_group_runs.get(scenario_group_id)
            if run_id is None:
                self._orphan_callbacks[scenario_group_id].append((callback_type, deepcopy(payload)))
                return None
            run = self._require_run(run_id)
            events.extend(self._apply_callback_locked(run, callback_type, payload))
            snapshot = deepcopy(run)
        await self._publish_many(run_id, events)
        return snapshot

    async def record_error(
        self,
        run_id: str,
        step: str,
        message: str,
        status_code: int | None = None,
        body: Any = None,
    ) -> RunRecord:
        async with self._lock:
            run = self._require_run(run_id)
            error = ErrorRecord(step=step, message=message, status_code=status_code, body=body)
            run.errors.append(error)
            run.timeline.append(TimelineEvent(type="error", message=message, data=error.model_dump(by_alias=True)))
            run.lifecycle_state = RunLifecycleState.FAILED
            snapshot = deepcopy(run)
        await self._publish(run_id, SseEventType.ERROR, {"runId": run_id, "error": error.model_dump(by_alias=True), "run": snapshot.model_dump(by_alias=True)})
        return snapshot

    async def subscribe(self, run_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        async with self._lock:
            self._require_run(run_id)
            self._subscribers[run_id].add(queue)
        return queue

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            self._subscribers[run_id].discard(queue)

    def _require_run(self, run_id: str) -> RunRecord:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(run_id)
        return run

    def _attach_orphans_locked(self, run: RunRecord, scenario_group_id: int) -> list[tuple[SseEventType, JsonObject]]:
        orphans = self._orphan_callbacks.pop(scenario_group_id, [])
        events: list[tuple[SseEventType, JsonObject]] = []
        for callback_type, payload in orphans:
            events.extend(self._apply_callback_locked(run, callback_type, payload))
        return events

    def _apply_callback_locked(
        self,
        run: RunRecord,
        callback_type: CallbackType,
        payload: JsonObject,
    ) -> list[tuple[SseEventType, JsonObject]]:
        run.callbacks[callback_type.value] = deepcopy(payload)
        run.timeline.append(TimelineEvent(type="callback", message=f"{callback_type.value} callback received", data=payload))
        self._apply_agent_status(run, payload)
        run.lifecycle_state = _callback_state(callback_type, payload)
        run.normalized = merge_normalized(run.normalized, normalize_payload(payload))
        event_payload = {"runId": run.run_id, "callbackType": callback_type.value, "payload": payload, "run": run.model_dump(by_alias=True)}
        events = [(SseEventType.CALLBACK, event_payload)]
        if callback_type == CallbackType.VALIDATION:
            events.append((SseEventType.VALIDATION_RESULT, event_payload))
        events.append(
            (
                SseEventType.NORMALIZED_MODEL_UPDATED,
                {"runId": run.run_id, "normalized": run.normalized.model_dump(by_alias=True)},
            )
        )
        return events

    def _apply_agent_status(self, run: RunRecord, payload: JsonObject) -> None:
        data = _payload_data(payload)
        scenario_group = _as_dict(data.get("scenarioGroup") or data.get("scenario_group") or data.get("scenarioGroupData"))
        if not scenario_group and "scenarioGroupId" in data:
            scenario_group = data
        run.agent_status = scenario_group.get("status") or data.get("status") or run.agent_status
        run.agent_stage = scenario_group.get("stage") or data.get("stage") or run.agent_stage

    def _row_from_run(self, run: RunRecord) -> ScenarioGroupListRow | None:
        if run.scenario_group_id is None:
            return None
        group = run.normalized.scenario_group
        title = group.title if group is not None else None
        if not title and run.normalized.one_view_draft:
            title = run.normalized.one_view_draft.get("scenarioGroupName")
        deleted = run.scenario_group_id in self._deleted_scenario_groups or _detail_deleted(run.detail)
        updated_at = run.timeline[-1].at if run.timeline else None
        return ScenarioGroupListRow(
            scenario_group_id=run.scenario_group_id,
            title=title or f"Scenario Group {run.scenario_group_id}",
            base_event_title=_base_event_title(run, group),
            mi_event_id=run.mi_event_id or (group.mi_event_id if group is not None else None),
            status=run.agent_status or (group.status if group is not None else None),
            stage=run.agent_stage or (group.stage if group is not None else None),
            scenario_count=len(run.normalized.table.rows),
            signpost_count=run.normalized.signpost_count,
            created_at=run.timeline[0].at if run.timeline else None,
            updated_at=updated_at,
            deleted=deleted,
            del_yn="Y" if deleted else "N",
            latest_run_id=run.run_id,
            raw=run.model_dump(by_alias=True),
        )

    async def _publish(self, run_id: str, event_type: SseEventType, payload: JsonObject) -> None:
        await self._publish_many(run_id, [(event_type, payload)])

    async def _publish_many(self, run_id: str, events: list[tuple[SseEventType, JsonObject]]) -> None:
        async with self._lock:
            subscribers = list(self._subscribers.get(run_id, set()))
        for event_type, payload in events:
            message = {"event": event_type.value, "data": payload}
            for queue in subscribers:
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    _ = queue.get_nowait()
                    queue.put_nowait(message)


def normalize_payload(payload: JsonObject) -> NormalizedScenarioDesign:
    data = _payload_data(payload)
    scenario_group_raw = _as_dict(data.get("scenarioGroup") or data.get("scenario_group"))
    table_raw = _as_dict(data.get("table"))
    if not scenario_group_raw and "scenarioGroup" in payload:
        scenario_group_raw = _as_dict(payload.get("scenarioGroup"))
    if not table_raw and "table" in payload:
        table_raw = _as_dict(payload.get("table"))

    group = _normalize_group(scenario_group_raw) if scenario_group_raw else None
    table = _normalize_table(table_raw)
    validation = None
    if "isValid" in data or "is_valid" in data or "reason" in data:
        validation = {
            "isValid": data.get("isValid", data.get("is_valid")),
            "reason": data.get("reason"),
            "result": data.get("result"),
        }
    signpost_count = sum(len(row.signposts) for row in table.rows)
    return NormalizedScenarioDesign(
        event_list=_build_event_list(group),
        branch_criteria_draft=_build_branch_criteria_draft(group, table, validation),
        one_view_draft=_build_one_view_draft(group, table),
        scenario_group_detail=_build_scenario_group_detail(group, table, signpost_count),
        scenario_group=group,
        table=table,
        validation=validation,
        signpost_count=signpost_count,
        raw_source=deepcopy(payload),
    )


def merge_normalized(current: NormalizedScenarioDesign, incoming: NormalizedScenarioDesign) -> NormalizedScenarioDesign:
    scenario_group = incoming.scenario_group or current.scenario_group
    table = _merge_table(current.table, incoming.table) if incoming.table.headers or incoming.table.rows else current.table
    validation = incoming.validation or current.validation
    signpost_count = incoming.signpost_count or current.signpost_count
    return NormalizedScenarioDesign(
        event_list=incoming.event_list if incoming.event_list.get("events") else current.event_list,
        branch_criteria_draft=incoming.branch_criteria_draft or current.branch_criteria_draft,
        one_view_draft=incoming.one_view_draft or current.one_view_draft,
        scenario_group_detail=incoming.scenario_group_detail or current.scenario_group_detail,
        scenario_group=scenario_group,
        table=table,
        validation=validation,
        signpost_count=signpost_count,
        raw_source=incoming.raw_source or current.raw_source,
    )


def _merge_table(current: ScenarioTable, incoming: ScenarioTable) -> ScenarioTable:
    if not incoming.headers and not incoming.rows:
        return current
    current_by_scenario_id = {row.scenario_id: row for row in current.rows if row.scenario_id is not None}
    current_by_order = {row.display_order: row for row in current.rows}
    rows: list[ScenarioRow] = []
    for row in incoming.rows:
        previous = current_by_scenario_id.get(row.scenario_id) if row.scenario_id is not None else None
        previous = previous or current_by_order.get(row.display_order)
        if previous is not None and not row.signposts and previous.signposts:
            row = row.model_copy(update={"signposts": previous.signposts})
        rows.append(row)
    return ScenarioTable(headers=incoming.headers or current.headers, rows=rows)


def _normalize_group(raw: JsonObject) -> ScenarioGroupModel:
    return ScenarioGroupModel(
        scenario_group_id=raw.get("scenarioGroupId") or raw.get("scenario_group_id"),
        mi_event_id=raw.get("miEventId") or raw.get("mi_event_id"),
        event_type_l2_id=raw.get("eventTypeL2Id") or raw.get("event_type_l2_id"),
        title=raw.get("title"),
        summary=raw.get("summary"),
        description=raw.get("description"),
        dimension_selected=list(raw.get("dimensionSelected") or raw.get("dimension_selected") or []),
        scenario_count=raw.get("scenarioCount") or raw.get("scenario_count"),
        status=raw.get("status"),
        stage=raw.get("stage"),
        raw=deepcopy(raw),
    )


def _normalize_table(raw: JsonObject) -> ScenarioTable:
    headers = [
        ScenarioHeader(
            key=str(header.get("key", "")),
            label=str(header.get("label", header.get("key", ""))),
            display_order=int(header.get("displayOrder", header.get("display_order", 0)) or 0),
        )
        for header in _as_list(raw.get("headers"))
        if isinstance(header, dict)
    ]
    rows = [_normalize_row(row) for row in _as_list(raw.get("rows")) if isinstance(row, dict)]
    return ScenarioTable(headers=headers, rows=rows)


def _normalize_row(raw: JsonObject) -> ScenarioRow:
    signposts = [_normalize_signpost(item) for item in _as_list(raw.get("signposts")) if isinstance(item, dict)]
    return ScenarioRow(
        scenario_id=raw.get("scenarioId") or raw.get("scenario_id"),
        display_order=int(raw.get("displayOrder", raw.get("display_order", 0)) or 0),
        title=str(raw.get("title") or ""),
        narrative=raw.get("narrative"),
        cells=_as_dict(raw.get("cells")),
        metrics=_as_dict(raw.get("metrics")) or None,
        impact=_as_dict(raw.get("impact")) or None,
        baseline_yn=raw.get("baselineYn") or raw.get("baseline_yn"),
        signposts=signposts,
        raw=deepcopy(raw),
    )


def _normalize_signpost(raw: JsonObject) -> SignpostModel:
    return SignpostModel(
        signpost_id=raw.get("signpostId") or raw.get("signpost_id"),
        label=str(raw.get("label") or ""),
        probability_direction_code=raw.get("probabilityDirectionCode") or raw.get("probability_direction_code"),
        probability_impact_score=raw.get("probabilityImpactScore") or raw.get("probability_impact_score"),
        signpost_reason=raw.get("signpostReason") or raw.get("signpost_reason"),
        display_order=int(raw.get("displayOrder", raw.get("display_order", 0)) or 0),
        strength=raw.get("strength"),
        use_yn=raw.get("useYn") or raw.get("use_yn"),
        keyword_hints=list(raw.get("keywordHints") or raw.get("keyword_hints") or []),
        evidence=raw.get("evidence") or raw.get("coreBasis") or raw.get("core_basis"),
        raw=deepcopy(raw),
    )


def _build_event_list(group: ScenarioGroupModel | None) -> JsonObject:
    if group is None or group.mi_event_id is None:
        return {"events": []}
    return {
        "events": [
            {
                "miEventId": group.mi_event_id,
                "title": group.title or f"MI Event {group.mi_event_id}",
                "eventTime": None,
                "category": group.event_type_l2_id,
                "status": "generated" if group.scenario_group_id is not None else "new",
                "recommended": False,
                "scenarioAction": {
                    "available": True,
                    "scenarioGroupId": group.scenario_group_id,
                    "stage": group.stage,
                },
            },
        ],
    }


def _build_branch_criteria_draft(
    group: ScenarioGroupModel | None,
    table: ScenarioTable,
    validation: JsonObject | None,
) -> JsonObject:
    return {
        "baseEvent": {
            "miEventId": group.mi_event_id if group is not None else None,
            "title": group.title if group is not None else None,
            "eventTime": None,
            "category": group.event_type_l2_id if group is not None else None,
        },
        "criteria": [header.model_dump(by_alias=True) for header in table.headers],
        "rows": [
            {
                **row.model_dump(by_alias=True),
                "rowKey": _row_key(row),
                "isBaseline": row.baseline_yn == "Y",
                "editState": "agent_generated",
            }
            for row in table.rows
        ],
        "validationResult": validation,
        "rawTable": table.model_dump(by_alias=True),
    }


def _build_one_view_draft(group: ScenarioGroupModel | None, table: ScenarioTable) -> JsonObject:
    title = group.title if group is not None else ""
    description = (group.description or group.summary) if group is not None else ""
    return {
        "scenarioGroupName": title or "",
        "scenarioGroupDescription": description or "",
        "characterCounts": {
            "scenarioGroupName": len(title or ""),
            "scenarioGroupDescription": len(description or ""),
        },
        "cards": [
            {
                "rowKey": _row_key(row),
                "scenarioId": row.scenario_id,
                "displayOrder": row.display_order,
                "title": row.title,
                "narrative": row.narrative or "",
                "narrativeCharacterCount": len(row.narrative or ""),
                "isBaseline": row.baseline_yn == "Y",
                "branchCriteria": row.cells,
                "probability": _probability(row),
                "signposts": [signpost.model_dump(by_alias=True) for signpost in row.signposts],
                "editState": "agent_generated",
            }
            for row in table.rows
        ],
        "rawTable": table.model_dump(by_alias=True),
    }


def _build_scenario_group_detail(group: ScenarioGroupModel | None, table: ScenarioTable, signpost_count: int) -> JsonObject:
    return {
        "summary": {
            "baseEvent": {
                "miEventId": group.mi_event_id if group is not None else None,
                "title": group.title if group is not None else None,
                "category": group.event_type_l2_id if group is not None else None,
            },
            "scenarioGroup": group.model_dump(by_alias=True) if group is not None else None,
            "scenarioCount": len(table.rows),
            "signpostCount": signpost_count,
        },
        "assumptionProbabilityRows": [
            {
                "rowKey": _row_key(row),
                "scenarioId": row.scenario_id,
                "title": row.title,
                "probability": _probability(row),
                "branchCriteria": row.cells,
            }
            for row in table.rows
        ],
        "scenarioList": [
            {
                "rowKey": _row_key(row),
                "scenarioId": row.scenario_id,
                "displayOrder": row.display_order,
                "title": row.title,
                "isBaseline": row.baseline_yn == "Y",
            }
            for row in table.rows
        ],
        "scenarioDetails": [
            {
                "rowKey": _row_key(row),
                "scenarioId": row.scenario_id,
                "title": row.title,
                "narrative": row.narrative,
                "probability": _probability(row),
                "majorAssumptions": row.cells,
                "signposts": [signpost.model_dump(by_alias=True) for signpost in row.signposts],
                "raw": row.raw,
            }
            for row in table.rows
        ],
        "rawDetailRef": "rawSource",
    }


def _row_key(row: ScenarioRow) -> str:
    if row.scenario_id is not None:
        return f"scenario:{row.scenario_id}"
    return f"local-order:{row.display_order}:{row.title}"


def _probability(row: ScenarioRow) -> Any:
    metrics = row.metrics or {}
    return metrics.get("probabilityScore") or metrics.get("probability_score")


def _payload_data(payload: JsonObject) -> JsonObject:
    data = payload.get("data")
    return _as_dict(data) if isinstance(data, dict) else payload


def _base_event_title(run: RunRecord, group: ScenarioGroupModel | None) -> str | None:
    event_list = run.normalized.event_list.get("events", [])
    if event_list and isinstance(event_list[0], dict):
        title = event_list[0].get("title")
        if title is not None:
            return str(title)
    if group is not None and group.mi_event_id is not None:
        return f"MI Event {group.mi_event_id}"
    if run.mi_event_id:
        return f"MI Event {run.mi_event_id}"
    return None


def _detail_deleted(detail: JsonObject | None) -> bool:
    data = _payload_data(detail or {})
    group = _as_dict(data.get("scenarioGroup") or data.get("scenario_group"))
    value = data.get("delYn") or data.get("del_yn") or data.get("deleted") or group.get("delYn") or group.get("del_yn") or group.get("deleted")
    return value is True or str(value).upper() == "Y"


def _mark_detail_deleted(detail: JsonObject | None) -> JsonObject | None:
    if detail is None:
        return None
    next_detail = deepcopy(detail)
    data = _payload_data(next_detail)
    data["deleted"] = True
    data["delYn"] = "Y"
    group = _as_dict(data.get("scenarioGroup") or data.get("scenario_group"))
    if group:
        group["deleted"] = True
        group["delYn"] = "Y"
    return next_detail


def _extract_scenario_group_id(payload: JsonObject) -> int | None:
    data = _payload_data(payload)
    scenario_group = _as_dict(data.get("scenarioGroup") or data.get("scenario_group"))
    value = data.get("scenarioGroupId") or data.get("scenario_group_id") or scenario_group.get("scenarioGroupId") or scenario_group.get("scenario_group_id")
    return int(value) if value is not None else None


def _waiting_state_for_action(action: str) -> RunLifecycleState:
    if action == "create":
        return RunLifecycleState.GENERATION_WAITING_CALLBACK
    if action == "validation":
        return RunLifecycleState.VALIDATION_WAITING_CALLBACK
    if action == "signposts":
        return RunLifecycleState.SIGNPOST_WAITING_CALLBACK
    if action == "confirmation":
        return RunLifecycleState.CONFIRMED
    return RunLifecycleState.IDLE


def _callback_state(callback_type: CallbackType, payload: JsonObject) -> RunLifecycleState:
    result = str(_payload_data(payload).get("result", "success")).lower()
    if result in {"failure", "failed", "error"}:
        return RunLifecycleState.FAILED
    if callback_type == CallbackType.GENERATION:
        return RunLifecycleState.SCENARIO_CREATED
    if callback_type == CallbackType.VALIDATION:
        return RunLifecycleState.SCENARIO_VALIDATED
    return RunLifecycleState.SIGNPOST_CREATED


def _as_dict(value: Any) -> JsonObject:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
