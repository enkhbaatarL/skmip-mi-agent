from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from backoffice.backend.agent_client import AgentClient
from backoffice.backend.schemas import (
    AgentHttpError,
    CallbackType,
    ConfirmationRunIn,
    CreateRunIn,
    DeleteScenarioGroupIn,
    DeleteScenarioGroupOut,
    EventDetailOut,
    EventListMeta,
    EventListOut,
    EventListRow,
    EventPagination,
    JsonObject,
    OAuthTokenOut,
    RunLifecycleState,
    RunOut,
    RunRecord,
    ScenarioGroupListMeta,
    ScenarioGroupListOut,
    ScenarioGroupListRow,
    SignpostsRunIn,
    ValidationRunIn,
)
from backoffice.backend.store import BackofficeStore


app = FastAPI(title="MI Agent Backoffice", version="0.1.0")
store = BackofficeStore()


@app.post("/backoffice/api/runs/scenario-groups", response_model=RunOut)
async def create_scenario_group_run(payload: CreateRunIn) -> RunOut:
    run = await store.create_run(
        mi_event_id=payload.mi_event_id,
        user_id=payload.user_id,
        agent_base_url=payload.agent_base_url,
    )
    request_body = {"miEventId": payload.mi_event_id, "userId": payload.user_id}
    await store.record_request(
        run.run_id,
        "create",
        _request_envelope(run, "create", request_body),
        RunLifecycleState.CREATING,
        agent_payload=request_body,
    )
    try:
        accepted = await AgentClient(payload.agent_base_url).create_scenario_group(request_body)
    except AgentHttpError as exc:
        existing_scenario_group_id = _already_created_scenario_group_id(exc.body)
        if exc.status_code == 400 and existing_scenario_group_id is not None:
            accepted = {
                "status": "accepted",
                "message": "Scenario group already exists; attached existing group for Backoffice QA.",
                "data": {
                    "scenarioGroupId": existing_scenario_group_id,
                    "status": "created",
                    "stage": "completed",
                },
            }
            run = await store.bind_accepted(run.run_id, "create", accepted)
            try:
                detail = await AgentClient(payload.agent_base_url).get_scenario_group(existing_scenario_group_id, include_deleted=True)
            except (AgentHttpError, httpx.HTTPError):
                return RunOut(run=run)
            run = await store.record_detail(run.run_id, detail)
            return RunOut(run=run)
        run = await store.record_error(run.run_id, exc.step, str(exc), status_code=exc.status_code, body=exc.body)
        raise HTTPException(status_code=exc.status_code, detail=exc.body) from exc
    except httpx.HTTPError as exc:
        run = await store.record_error(run.run_id, "create", str(exc))
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    run = await store.bind_accepted(run.run_id, "create", accepted)
    return RunOut(run=run)


@app.get("/backoffice/api/runs/{run_id}", response_model=RunOut)
async def get_run(run_id: str) -> RunOut:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunOut(run=run)


@app.get("/backoffice/api/runs/{run_id}/events")
async def stream_run_events(run_id: str, request: Request) -> StreamingResponse:
    try:
        queue = await store.subscribe(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc

    async def event_stream() -> AsyncIterator[str]:
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                message = await queue.get()
                yield _format_sse(message["event"], message["data"])
        finally:
            await store.unsubscribe(run_id, queue)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.get("/backoffice/api/events", response_model=EventListOut)
async def list_events(
    agent_base_url: str | None = Query(default=None, alias="agentBaseUrl"),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    event_type_l1_id: int | None = Query(default=None, alias="eventTypeL1Id"),
    event_type_l2_id: int | None = Query(default=None, alias="eventTypeL2Id"),
    recommended_only: bool = Query(default=False, alias="recommendedOnly"),
    date_from: str | None = Query(default=None, alias="dateFrom"),
    date_to: str | None = Query(default=None, alias="dateTo"),
    sort: str = Query(default="latest"),
    page: int = Query(default=1),
    page_size: int = Query(default=20, alias="pageSize"),
) -> EventListOut:
    if not agent_base_url:
        return _empty_event_list(page=page, page_size=page_size, fallback_reason="agentBaseUrl is required for Agent event data")

    params: JsonObject = {
        "keyword": keyword,
        "status": status,
        "eventTypeL1Id": event_type_l1_id,
        "eventTypeL2Id": event_type_l2_id,
        "recommendedOnly": str(recommended_only).lower(),
        "dateFrom": date_from,
        "dateTo": date_to,
        "sort": sort,
        "page": page,
        "pageSize": page_size,
    }
    params = {key: value for key, value in params.items() if value is not None and value != ""}
    try:
        raw_source = await AgentClient(agent_base_url).list_events(params)
    except (AgentHttpError, httpx.HTTPError) as exc:
        return _empty_event_list(page=page, page_size=page_size, fallback_reason=str(exc))
    return _normalize_event_list(raw_source)


@app.get("/backoffice/api/events/{mi_event_id}", response_model=EventDetailOut)
async def get_event_detail(
    mi_event_id: int,
    agent_base_url: str | None = Query(default=None, alias="agentBaseUrl"),
) -> EventDetailOut:
    if not agent_base_url:
        raise HTTPException(status_code=400, detail="agentBaseUrl is required")
    try:
        raw_source = await AgentClient(agent_base_url).get_event(mi_event_id)
    except AgentHttpError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.body) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    event = EventListRow.model_validate(_event_row_payload(raw_source.get("event") or {}))
    return EventDetailOut(
        event=event,
        scenario_template=raw_source.get("scenarioTemplate") or raw_source.get("scenario_template") or {},
        meta=EventListMeta(source=str((raw_source.get("source") or {}).get("type") or "agent_proxy")),
        raw_source=raw_source,
    )


@app.get("/backoffice/api/scenario-groups", response_model=ScenarioGroupListOut)
async def list_scenario_groups(
    agent_base_url: str | None = Query(default=None, alias="agentBaseUrl"),
    include_deleted: bool = Query(default=False, alias="includeDeleted"),
    mi_event_id: int | None = Query(default=None, alias="miEventId"),
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    sort: str = Query(default="latest"),
) -> ScenarioGroupListOut:
    params: JsonObject = {
        "includeDeleted": str(include_deleted).lower(),
        "sort": sort,
    }
    if mi_event_id is not None:
        params["miEventId"] = mi_event_id
    if keyword:
        params["keyword"] = keyword
    if status:
        params["status"] = status
    if stage:
        params["stage"] = stage

    raw_source: JsonObject | None = None
    fallback_reason: str | None = None
    rows: list[ScenarioGroupListRow]
    source = "backoffice_memory"
    if agent_base_url:
        try:
            raw_source = await AgentClient(agent_base_url).list_scenario_groups(params)
            rows = _normalize_list_rows(raw_source, source="agent_proxy")
            source = "agent_proxy"
        except (AgentHttpError, httpx.HTTPError) as exc:
            fallback_reason = str(exc)
            rows = await store.list_scenario_groups(
                include_deleted=include_deleted,
                keyword=keyword,
                status=status,
                stage=stage,
                mi_event_id=mi_event_id,
                sort=sort,
            )
    else:
        rows = await store.list_scenario_groups(
            include_deleted=include_deleted,
            keyword=keyword,
            status=status,
            stage=stage,
            mi_event_id=mi_event_id,
            sort=sort,
        )
    if source == "agent_proxy":
        rows = _filter_rows(rows, include_deleted=include_deleted, keyword=keyword, status=status, stage=stage, mi_event_id=mi_event_id, sort=sort)
    return ScenarioGroupListOut(
        rows=rows,
        meta=ScenarioGroupListMeta(
            source=source,
            total=len(rows),
            returned=len(rows),
            include_deleted=include_deleted,
            fallback_reason=fallback_reason,
        ),
        raw_source=raw_source,
    )


@app.get("/backoffice/api/scenario-groups/{scenario_group_id}", response_model=RunOut)
async def get_scenario_group_detail(
    scenario_group_id: int,
    agent_base_url: str | None = Query(default=None, alias="agentBaseUrl"),
    include_deleted: bool = Query(default=False, alias="includeDeleted"),
) -> RunOut:
    run = await store.find_run_by_scenario_group_id(scenario_group_id)
    if run is None and agent_base_url is None:
        raise HTTPException(status_code=404, detail="No run is bound to this scenarioGroupId; pass agentBaseUrl to fetch it")
    if run is None:
        run = await store.create_run(mi_event_id=0, user_id=0, agent_base_url=agent_base_url or "")
        run = await store.bind_accepted(
            run.run_id,
            "detail_attach",
            {"data": {"scenarioGroupId": scenario_group_id, "status": None, "stage": None}},
        )
    base_url = agent_base_url.rstrip("/") if agent_base_url is not None else run.agent_base_url
    try:
        detail = await AgentClient(base_url).get_scenario_group(scenario_group_id, include_deleted=include_deleted)
    except AgentHttpError as exc:
        run = await store.record_error(run.run_id, exc.step, str(exc), status_code=exc.status_code, body=exc.body)
        raise HTTPException(status_code=exc.status_code, detail=exc.body) from exc
    except httpx.HTTPError as exc:
        run = await store.record_error(run.run_id, "detail", str(exc))
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    run = await store.record_detail(run.run_id, detail)
    return RunOut(run=run)


@app.delete("/backoffice/api/scenario-groups/{scenario_group_id}", response_model=DeleteScenarioGroupOut)
async def delete_scenario_group(scenario_group_id: int, payload: DeleteScenarioGroupIn) -> DeleteScenarioGroupOut:
    try:
        response = await AgentClient(payload.agent_base_url).soft_delete_scenario_group(
            scenario_group_id=scenario_group_id,
            user_id=payload.user_id,
            delete_authorization=payload.delete_authorization,
        )
    except AgentHttpError as exc:
        run = await store.find_run_by_scenario_group_id(scenario_group_id)
        if run is not None:
            await store.record_error(run.run_id, exc.step, str(exc), status_code=exc.status_code, body=exc.body)
        raise HTTPException(status_code=exc.status_code, detail=exc.body) from exc
    except httpx.HTTPError as exc:
        run = await store.find_run_by_scenario_group_id(scenario_group_id)
        if run is not None:
            await store.record_error(run.run_id, "soft_delete", str(exc))
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    await store.mark_scenario_group_deleted(scenario_group_id, payload.user_id, response)
    return DeleteScenarioGroupOut(scenario_group_id=scenario_group_id, deleted=True, raw_response=response)


@app.post("/backoffice/api/runs/{run_id}/validation", response_model=RunOut)
async def validate_run(run_id: str, payload: ValidationRunIn) -> RunOut:
    run = await _require_run_with_scenario_group(run_id)
    request_body = {"table": _branch_table_body(payload.table.model_dump(by_alias=True, exclude_none=True))}
    request_body["userId"] = payload.user_id if payload.user_id is not None else run.user_id
    await store.record_request(
        run_id,
        "validation",
        _request_envelope(run, "validation", request_body),
        RunLifecycleState.VALIDATING,
        agent_payload=request_body,
    )
    try:
        accepted = await AgentClient(run.agent_base_url).validate_scenarios(run.scenario_group_id or 0, request_body)
    except AgentHttpError as exc:
        run = await store.record_error(run_id, exc.step, str(exc), status_code=exc.status_code, body=exc.body)
        raise HTTPException(status_code=exc.status_code, detail=exc.body) from exc
    except httpx.HTTPError as exc:
        run = await store.record_error(run_id, "validation", str(exc))
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    run = await store.bind_accepted(run_id, "validation", accepted)
    return RunOut(run=run)


@app.post("/backoffice/api/runs/{run_id}/signposts", response_model=RunOut)
async def create_signposts(run_id: str, payload: SignpostsRunIn) -> RunOut:
    run = await _require_run_with_scenario_group(run_id)
    request_body = {"table": _branch_table_body(payload.table.model_dump(by_alias=True, exclude_none=True))}
    request_body["userId"] = payload.user_id if payload.user_id is not None else run.user_id
    await store.record_request(
        run_id,
        "signposts",
        _request_envelope(run, "signposts", request_body),
        RunLifecycleState.CREATING_SIGNPOSTS,
        agent_payload=request_body,
    )
    try:
        accepted = await AgentClient(run.agent_base_url).create_signposts(run.scenario_group_id or 0, request_body)
    except AgentHttpError as exc:
        run = await store.record_error(run_id, exc.step, str(exc), status_code=exc.status_code, body=exc.body)
        raise HTTPException(status_code=exc.status_code, detail=exc.body) from exc
    except httpx.HTTPError as exc:
        run = await store.record_error(run_id, "signposts", str(exc))
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    run = await store.bind_accepted(run_id, "signposts", accepted)
    return RunOut(run=run)


@app.post("/backoffice/api/runs/{run_id}/confirmation", response_model=RunOut)
async def confirm_run(run_id: str, payload: ConfirmationRunIn) -> RunOut:
    run = await _require_run_with_scenario_group(run_id)
    request_body = payload.model_dump(by_alias=True, exclude_none=True)
    await store.record_request(
        run_id,
        "confirmation",
        _request_envelope(run, "confirmation", request_body),
        RunLifecycleState.CONFIRMING,
        agent_payload=request_body,
    )
    try:
        accepted = await AgentClient(run.agent_base_url).confirm_generation(run.scenario_group_id or 0, request_body)
    except AgentHttpError as exc:
        run = await store.record_error(run_id, exc.step, str(exc), status_code=exc.status_code, body=exc.body)
        raise HTTPException(status_code=exc.status_code, detail=exc.body) from exc
    except httpx.HTTPError as exc:
        run = await store.record_error(run_id, "confirmation", str(exc))
        raise HTTPException(status_code=502, detail={"message": str(exc)}) from exc
    run = await store.bind_accepted(run_id, "confirmation", accepted)
    return RunOut(run=run)


@app.post("/api/v1/oauth2/token", response_model=OAuthTokenOut)
async def oauth2_token(_: Request) -> OAuthTokenOut:
    return OAuthTokenOut()


@app.post("/api/v1/mi/next-gen/scenario-groups/{scenario_group_id}/generation/callback", response_model=RunOut | dict[str, str])
async def generation_callback(scenario_group_id: int, payload: JsonObject) -> RunOut | dict[str, str]:
    return await _record_callback(scenario_group_id, CallbackType.GENERATION, payload)


@app.post("/api/v1/mi/next-gen/scenario-groups/{scenario_group_id}/validation/callback", response_model=RunOut | dict[str, str])
async def validation_callback(scenario_group_id: int, payload: JsonObject) -> RunOut | dict[str, str]:
    return await _record_callback(scenario_group_id, CallbackType.VALIDATION, payload)


@app.post("/api/v1/mi/next-gen/scenario-groups/{scenario_group_id}/signposts/callback", response_model=RunOut | dict[str, str])
async def signposts_callback(scenario_group_id: int, payload: JsonObject) -> RunOut | dict[str, str]:
    return await _record_callback(scenario_group_id, CallbackType.SIGNPOSTS, payload)


async def _record_callback(scenario_group_id: int, callback_type: CallbackType, payload: JsonObject) -> RunOut | dict[str, str]:
    run = await store.record_callback(scenario_group_id, callback_type, payload)
    if run is None:
        return {"status": "accepted", "message": "Stored as orphan callback"}
    return RunOut(run=run)


async def _require_run_with_scenario_group(run_id: str) -> RunRecord:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.scenario_group_id is None:
        raise HTTPException(status_code=409, detail="Run is not bound to a scenarioGroupId yet")
    return run


def _format_sse(event: str, data: JsonObject) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


def _branch_table_body(table: JsonObject) -> JsonObject:
    headers = [
        {
            "key": header.get("key"),
            "label": header.get("label"),
            "displayOrder": header.get("displayOrder", 0),
        }
        for header in table.get("headers", [])
        if isinstance(header, dict)
    ]
    rows = [
        {
            "scenarioId": row.get("scenarioId"),
            "displayOrder": row.get("displayOrder", 0),
            "title": row.get("title", ""),
            "cells": row.get("cells", {}),
        }
        for row in table.get("rows", [])
        if isinstance(row, dict)
    ]
    return {"headers": headers, "rows": rows}


def _request_envelope(run: RunRecord, action: str, agent_payload: JsonObject) -> JsonObject:
    return {
        "action": action,
        "runId": run.run_id,
        "scenarioGroupId": run.scenario_group_id,
        "miEventId": run.mi_event_id,
        "userId": run.user_id,
        "agentBaseUrl": run.agent_base_url,
        "agentPayload": agent_payload,
    }


def _normalize_list_rows(payload: JsonObject, source: str) -> list[ScenarioGroupListRow]:
    rows_raw = payload.get("rows") or payload.get("items") or payload.get("data") or []
    if isinstance(rows_raw, dict):
        rows_raw = rows_raw.get("rows") or rows_raw.get("items") or rows_raw.get("scenarioGroups") or []
    if not isinstance(rows_raw, list):
        return []
    rows: list[ScenarioGroupListRow] = []
    for item in rows_raw:
        if not isinstance(item, dict):
            continue
        scenario_group_id = item.get("scenarioGroupId") or item.get("scenario_group_id") or item.get("id")
        if scenario_group_id is None:
            continue
        deleted_value = item.get("deleted") or item.get("delYn") or item.get("del_yn")
        deleted = deleted_value is True or str(deleted_value).upper() == "Y"
        rows.append(
            ScenarioGroupListRow(
                scenario_group_id=int(scenario_group_id),
                title=str(item.get("title") or item.get("name") or f"Scenario Group {scenario_group_id}"),
                base_event_title=item.get("baseEventTitle") or item.get("base_event_title") or item.get("eventTitle") or item.get("event_title"),
                mi_event_id=item.get("miEventId") or item.get("mi_event_id"),
                status=item.get("status"),
                stage=item.get("stage"),
                scenario_count=int(item.get("scenarioCount") or item.get("scenario_count") or 0),
                signpost_count=int(item.get("signpostCount") or item.get("signpost_count") or 0),
                created_at=item.get("createdAt") or item.get("created_at"),
                updated_at=item.get("updatedAt") or item.get("updated_at"),
                deleted=deleted,
                del_yn="Y" if deleted else "N",
                latest_run_id=item.get("latestRunId") or item.get("latest_run_id"),
                source=source,
                raw=item,
            )
        )
    return rows


def _empty_event_list(page: int, page_size: int, fallback_reason: str) -> EventListOut:
    return EventListOut(
        rows=[],
        pagination=EventPagination(page=page, page_size=page_size, total=0, has_previous=page > 1, has_next=False),
        meta=EventListMeta(source="backoffice_empty", fallback_reason=fallback_reason),
        raw_source={"source": "backoffice_empty", "fallbackReason": fallback_reason},
    )


def _normalize_event_list(payload: JsonObject) -> EventListOut:
    rows_raw = payload.get("rows") or payload.get("data") or []
    if isinstance(rows_raw, dict):
        rows_raw = rows_raw.get("rows") or rows_raw.get("items") or []
    rows = [EventListRow.model_validate(_event_row_payload(item)) for item in rows_raw if isinstance(item, dict)]
    pagination_raw = payload.get("pagination") or {}
    source_raw = payload.get("source") or {}
    return EventListOut(
        rows=rows,
        pagination=EventPagination.model_validate(pagination_raw),
        meta=EventListMeta(source=str(source_raw.get("type") or "agent_proxy")),
        raw_source=payload,
    )


def _event_row_payload(item: JsonObject) -> JsonObject:
    title = item.get("title") or item.get("eventTitle") or item.get("event_title") or item.get("event_title_ko") or ""
    new_yn = str(item.get("newYn") or item.get("new_yn") or "Y")
    action = item.get("scenarioActionState") or item.get("scenario_action_state") or {}
    return {
        "miEventId": item.get("miEventId") or item.get("mi_event_id"),
        "title": title,
        "oneLineSummary": item.get("oneLineSummary") or item.get("one_line_summary") or "",
        "eventTime": item.get("eventTime") or item.get("event_time") or item.get("occurredAt") or item.get("occurred_at") or "",
        "occurredAt": item.get("occurredAt") or item.get("occurred_at") or "",
        "latestRecordFirstCreated": item.get("latestRecordFirstCreated") or item.get("latest_record_first_created") or "",
        "oldestRecordFirstCreated": item.get("oldestRecordFirstCreated") or item.get("oldest_record_first_created") or "",
        "category": item.get("category") or "",
        "eventTypeL1": item.get("eventTypeL1") or item.get("event_type_l1") or {},
        "eventTypeL2": item.get("eventTypeL2") or item.get("event_type_l2") or {},
        "newYn": new_yn,
        "signalYn": item.get("signalYn") or item.get("signal_yn") or "N",
        "signalConfidence": item.get("signalConfidence") or item.get("signal_confidence"),
        "signalReason": item.get("signalReason") or item.get("signal_reason"),
        "scenarioSuggestYn": item.get("scenarioSuggestYn") or item.get("scenario_suggest_yn") or "N",
        "scenarioSuggestReason": item.get("scenarioSuggestReason") or item.get("scenario_suggest_reason"),
        "tags": item.get("tags") or [],
        "marketImpacts": item.get("marketImpacts") or item.get("market_impacts") or {},
        "relatedScenarioGroup": item.get("relatedScenarioGroup") or item.get("related_scenario_group"),
        "scenarioActionState": action,
        "raw": item,
    }


def _already_created_scenario_group_id(body: object) -> int | None:
    if not isinstance(body, dict):
        return None
    data = body.get("data")
    error_name = data.get("error_name") if isinstance(data, dict) else None
    if error_name != "SCENARIO_GROUP_ALREADY_CREATED":
        return None
    message = str(body.get("message") or "")
    match = re.search(r"ID:\s*(\d+)", message)
    return int(match.group(1)) if match else None


def _filter_rows(
    rows: list[ScenarioGroupListRow],
    include_deleted: bool,
    keyword: str | None,
    status: str | None,
    stage: str | None,
    mi_event_id: int | None,
    sort: str,
) -> list[ScenarioGroupListRow]:
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
    filtered.sort(key=lambda row: row.updated_at or row.created_at or 0, reverse=sort != "oldest")
    return filtered


def _mount_static_dist(application: FastAPI) -> None:
    dist_dir = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if not dist_dir.exists():
        return
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        application.mount("/assets", StaticFiles(directory=assets_dir), name="backoffice-assets")

    @application.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str) -> FileResponse:
        requested = dist_dir / full_path
        if full_path and requested.is_file():
            return FileResponse(requested)
        return FileResponse(dist_dir / "index.html")


_mount_static_dist(app)
