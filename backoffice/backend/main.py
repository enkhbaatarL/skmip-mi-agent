from __future__ import annotations

import json
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
    JsonObject,
    OAuthTokenOut,
    RunLifecycleState,
    RunOut,
    RunRecord,
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
