from __future__ import annotations

# ruff: noqa: CPY001, S101
import json
from pathlib import Path

import httpx
import pytest

from tests.manual.test_sse_scenario_group_api import (
    SSEFrame,
    StreamContractState,
    _fetch_and_validate_presentation,
    parse_sse_lines,
    validate_presentation,
)


OPERATION_ID = "01KZQNK7AJTV5DAA49G7ZE9ZZE"


def _event(sequence: int, event_type: str, *, revision: int = 0, **extra: object) -> SSEFrame:
    return SSEFrame(
        event_id=sequence,
        event_type=event_type,
        data={
            "operationId": OPERATION_ID,
            "scenarioGroupId": 366,
            "sequence": sequence,
            "eventType": event_type,
            "phase": None if event_type == "accepted" else "event_analysis",
            "title": event_type,
            "messageMarkdown": event_type,
            "snapshotRevision": revision,
            "mlflowTraceId": None,
            "createdAt": "2026-08-11T04:51:47Z",
            **extra,
        },
    )


def _presentation() -> dict[str, object]:
    dimensions = [
        {
            "dimensionId": f"d{index}",
            "label": f"Dimension {index}",
            "description": f"Dimension {index}은 어떻게 변하는가?",
            "rationale": "이 불확실성은 JKM 가격 결과를 구분하는 핵심 기준이다.",
            "sourceEventIds": [101],
            "modelSupportStatus": "full",
            "source": None,
            "values": [],
        }
        for index in range(1, 4)
    ]
    rows = [
        {
            "scenarioId": index,
            "title": f"Scenario {index}",
            "cells": {},
        }
        for index in range(1, 4)
    ]
    return {
        "schemaVersion": "v1",
        "rendererVersion": "v2",
        "scenarioGroupId": 366,
        "engineVersion": "v4",
        "legacy": False,
        "warnings": [],
        "operation": {
            "operationId": OPERATION_ID,
            "status": "succeeded",
            "currentPhase": "persistence",
            "latestSequence": 4,
            "snapshotRevision": 2,
        },
        "sections": {
            "eventAnalysis": {
                "status": "ready",
                "evidenceLevel": "full",
                "contentType": "text/markdown",
                "markdown": "Event analysis",
            },
            "scenarioDesign": {
                "status": "ready",
                "evidenceLevel": "full",
                "dimensionDefinitions": {"status": "ready", "items": dimensions},
                "scenarioTable": {"status": "ready", "headers": [], "rows": rows},
            },
            "roleSelectionRationale": {
                "status": "ready",
                "evidenceLevel": "full",
                "contentType": "text/markdown",
                "markdown": "Role rationale",
            },
        },
    }


def test_parse_sse_lines_ignores_keepalive_and_parses_frames() -> None:
    accepted = _event(1, "accepted", status="queued", engineVersion="v4")
    completed = _event(2, "completed", revision=1, status="succeeded")
    lines = [
        ": keep-alive",
        "",
        "id: 1",
        "event: accepted",
        f"data: {json.dumps(accepted.data)}",
        "",
        "id: 2",
        "event: completed",
        f"data: {json.dumps(completed.data)}",
        "",
    ]

    frames = list(parse_sse_lines(lines))

    assert frames == [accepted, completed]


def test_stream_contract_requires_contiguous_identity_stable_events() -> None:
    state = StreamContractState()

    assert state.accept(_event(1, "accepted", status="queued", engineVersion="v4")) is False
    assert state.accept(_event(2, "phase_started")) is False
    assert state.accept(_event(3, "section_ready", revision=1)) is True
    assert state.accept(_event(4, "completed", revision=2, status="succeeded")) is False

    assert state.scenario_group_id == 366
    assert state.operation_id == OPERATION_ID
    assert state.last_sequence == 4
    assert state.snapshot_revision == 2
    assert state.terminal_event == "completed"


def test_section_ready_refresh_is_compared_with_last_ready_revision() -> None:
    state = StreamContractState()

    state.accept(_event(1, "accepted", status="queued", engineVersion="v4"))
    state.accept(_event(2, "validated", revision=1))

    assert state.accept(_event(3, "section_ready", revision=1)) is True
    assert state.accept(_event(4, "section_ready", revision=1)) is False


def test_stream_contract_rejects_sequence_gap() -> None:
    state = StreamContractState()
    state.accept(_event(1, "accepted", status="queued", engineVersion="v4"))

    with pytest.raises(ValueError, match="sequence gap"):
        state.accept(_event(3, "phase_started"))


def test_validate_final_presentation_checks_v4_ready_contract() -> None:
    validate_presentation(
        _presentation(),
        scenario_group_id=366,
        operation_id=OPERATION_ID,
        minimum_sequence=4,
        minimum_revision=2,
        final=True,
    )


def test_validate_final_presentation_rejects_missing_dimension_rationale() -> None:
    payload = _presentation()
    sections = payload["sections"]
    assert isinstance(sections, dict)
    design = sections["scenarioDesign"]
    assert isinstance(design, dict)
    definitions = design["dimensionDefinitions"]
    assert isinstance(definitions, dict)
    items = definitions["items"]
    assert isinstance(items, list)
    items[0]["rationale"] = None

    with pytest.raises(TypeError, match="rationale"):
        validate_presentation(
            payload,
            scenario_group_id=366,
            operation_id=OPERATION_ID,
            minimum_sequence=4,
            minimum_revision=2,
            final=True,
        )


def test_validate_final_presentation_accepts_200_character_dimension_rationale() -> None:
    payload = _presentation()
    sections = payload["sections"]
    assert isinstance(sections, dict)
    design = sections["scenarioDesign"]
    assert isinstance(design, dict)
    definitions = design["dimensionDefinitions"]
    assert isinstance(definitions, dict)
    items = definitions["items"]
    assert isinstance(items, list)
    items[0]["rationale"] = "가" * 200

    validate_presentation(
        payload,
        scenario_group_id=366,
        operation_id=OPERATION_ID,
        minimum_sequence=4,
        minimum_revision=2,
        final=True,
    )


def test_validate_final_presentation_rejects_201_character_dimension_rationale() -> None:
    payload = _presentation()
    sections = payload["sections"]
    assert isinstance(sections, dict)
    design = sections["scenarioDesign"]
    assert isinstance(design, dict)
    definitions = design["dimensionDefinitions"]
    assert isinstance(definitions, dict)
    items = definitions["items"]
    assert isinstance(items, list)
    items[0]["rationale"] = "가" * 201

    with pytest.raises(ValueError, match=r"10\.\.200"):
        validate_presentation(
            payload,
            scenario_group_id=366,
            operation_id=OPERATION_ID,
            minimum_sequence=4,
            minimum_revision=2,
            final=True,
        )


def test_presentation_fetch_validates_etag_conditional_get(tmp_path: Path) -> None:
    etag = '"presentation-etag"'

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["operationId"] == OPERATION_ID
        if request.headers.get("if-none-match") == etag:
            return httpx.Response(304, headers={"ETag": etag})
        return httpx.Response(200, headers={"ETag": etag}, json=_presentation())

    state = StreamContractState(
        last_sequence=4,
        scenario_group_id=366,
        operation_id=OPERATION_ID,
        snapshot_revision=2,
        terminal_event="completed",
    )
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = _fetch_and_validate_presentation(
            client,
            base_url="http://testserver",
            state=state,
            artifact_dir=tmp_path,
            final=True,
        )

    assert result["conditionalStatus"] == 304
    assert result["etag"] == etag
    assert (tmp_path / "presentations" / "presentation_final.json").is_file()
