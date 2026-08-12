from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import json

from fastapi import APIRouter, Header, Request
from fastapi.responses import StreamingResponse

from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
)
from apps.agents.scenario_group_agent.runtime import (
    ScenarioGroupOperationEventHub,
    get_scenario_group_operation_event_hub,
)
from apps.agents.scenario_group_agent.schemas.api.manage_scenario_groups import ScenarioGroupOperationStatusOut
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.logger_config import logger
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario_group_operation.schema import TERMINAL_EVENT_TYPES, TERMINAL_OPERATION_STATUSES


router = APIRouter(tags=["scenario-groups"])


def _parse_last_event_id(value: str | None) -> int:
    if value is None or not value.strip():
        return 0
    try:
        sequence = int(value)
    except ValueError as exc:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Last-Event-ID must be a non-negative integer") from exc
    if sequence < 0:
        raise MIBaseError(ErrorCode.INVALID_REQUEST, detail="Last-Event-ID must be a non-negative integer")
    return sequence


def _serialize_sse_event(event: object) -> str:
    data = event.model_dump(mode="json", by_alias=True)
    payload = data.pop("payload", {})
    if isinstance(payload, dict):
        data.update(payload)
    event_type = str(data["eventType"])
    sequence = int(data["sequence"])
    encoded = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"id: {sequence}\nevent: {event_type}\ndata: {encoded}\n\n"


async def stream_operation_events(
    request: Request,
    scenario_group_id: int,
    operation_id: str,
    *,
    after_sequence: int,
    event_hub: ScenarioGroupOperationEventHub | None = None,
    keepalive_interval_seconds: float = 15.0,
) -> AsyncIterator[str]:
    if await request.is_disconnected():
        return
    service = ScenarioGroupOperationService()
    operation = await asyncio.to_thread(service.get_operation, scenario_group_id, operation_id)
    hub = event_hub or get_scenario_group_operation_event_hub()
    cursor = after_sequence
    target_sequence = max(cursor, operation.latest_sequence)
    async with hub.subscribe(
        scenario_group_id,
        operation_id,
        known_latest_sequence=operation.latest_sequence,
    ) as wakeups:
        while True:
            if await request.is_disconnected():
                return
            if target_sequence > cursor:
                events = await asyncio.to_thread(
                    service.list_events_after,
                    scenario_group_id,
                    operation_id,
                    cursor,
                )
                if events and events[0].sequence != cursor + 1:
                    logger.error(
                        "Scenario Group operation event gap detected; replaying DB range | "
                        "operation_id={} | cursor={} | first_sequence={}",
                        operation_id,
                        cursor,
                        events[0].sequence,
                    )
                for event in events:
                    if event.sequence <= cursor:
                        continue
                    cursor = event.sequence
                    yield _serialize_sse_event(event)
                    if event.event_type in TERMINAL_EVENT_TYPES:
                        return
                if cursor < target_sequence:
                    continue
            if operation.status in TERMINAL_OPERATION_STATUSES and cursor >= operation.latest_sequence:
                return
            try:
                wakeup = await asyncio.wait_for(
                    wakeups.get(),
                    timeout=keepalive_interval_seconds,
                )
            except TimeoutError:
                yield ": keep-alive\n\n"
                continue
            if wakeup is None:
                return
            target_sequence = max(target_sequence, wakeup.latest_sequence)
            if wakeup.terminal and cursor >= wakeup.latest_sequence:
                return


@router.get(
    "/scenario-groups/{scenario_group_id}/operations/{operation_id}",
    response_model=ScenarioGroupOperationStatusOut,
    summary="Scenario Group operation 상태 조회",
)
async def get_operation_status(scenario_group_id: int, operation_id: str) -> ScenarioGroupOperationStatusOut:
    service = ScenarioGroupOperationService()
    operation = await asyncio.to_thread(service.get_operation, scenario_group_id, operation_id)
    last_event = await asyncio.to_thread(service.get_last_event, operation_id)
    return ScenarioGroupOperationStatusOut(
        scenario_group_id=scenario_group_id,
        operation=operation,
        last_event=last_event,
        last_error=operation.last_error,
    )


@router.get(
    "/scenario-groups/{scenario_group_id}/operations/{operation_id}/stream",
    summary="Scenario Group operation SSE 재연결",
    response_class=StreamingResponse,
)
async def reconnect_operation_stream(
    request: Request,
    scenario_group_id: int,
    operation_id: str,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
) -> StreamingResponse:
    sequence = _parse_last_event_id(last_event_id)
    await asyncio.to_thread(
        ScenarioGroupOperationService().get_operation,
        scenario_group_id,
        operation_id,
    )
    return StreamingResponse(
        stream_operation_events(
            request,
            scenario_group_id,
            operation_id,
            after_sequence=sequence,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
