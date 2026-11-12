from __future__ import annotations

# ruff: noqa: CPY001, S101, ANN001, ANN201, ANN202
import asyncio
from contextlib import contextmanager
from copy import deepcopy
from io import StringIO
import json
from types import SimpleNamespace

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from apps.agents.scenario_group_agent.utils.execution_log import execution_event, logged_run
from apps.common.logging.console import format_console_record, full_console_logs, full_payloads_enabled
from apps.common.logging.decorators import log_connector, serialize
from apps.common.logging.logger_config import logger
from apps.common.middleware.request_logging import RequestLoggingMiddleware, _format_body_for_debug


FEATURES = ["event_recommendation", "event_verification", "event_update", "scenario_design", "quality_evaluation"]
STATUSES = ["started", "completed", "failed", "interrupted", "skipped", "warning"]


@contextmanager
def captured_logs(*, colorize=False):
    output = StringIO()
    records = []

    def match(record):
        return record["extra"].get("console_format_test") is True

    console_id = logger.add(output, format=format_console_record, colorize=colorize, level="DEBUG", filter=match)
    raw_id = logger.add(lambda message: records.append(message.record.copy()), format="{message}", filter=match)
    try:
        with logger.contextualize(console_format_test=True):
            yield output, records
    finally:
        logger.remove(console_id)
        logger.remove(raw_id)


def parse_event_blocks(text):
    events = []
    while "{\n" in text:
        start = text.index("{\n")
        event, end = json.JSONDecoder().raw_decode(text[start:])
        events.append(event)
        text = text[start + end :]
    return events


@pytest.mark.parametrize("feature", FEATURES)
@pytest.mark.parametrize("status", STATUSES)
def test_every_field_and_value_survives_pretty_print(feature, status):
    long_text = ("한글 English 🌏 <red>{message}</red> \n줄바꿈\t탭 \\n 리터럴 " * 500) + "END_OF_LONG_TEXT"
    event = {
        "runId": "complete-uuid-must-not-be-shortened",
        "parentRunId": None,
        "sequence": 19,
        "feature": feature,
        "phase": "selection",
        "status": status,
        "summary": long_text,
        "occurredAt": "2026-11-12T01:02:27.598907Z",
        "elapsedMs": 99237,
        "details": {
            "before": long_text,
            "after": long_text + "changed",
            "durationMs": 24873,
            "candidates": [
                {"id": index, "url": "https://example.test/?a=1&b=2", "reason": long_text[:80]} for index in range(150)
            ],
            "planning": {"A": {"score": 4.75, "feasible": True}, "B": {"score": 3, "feasible": False}},
        },
        "futureField": {"mustBePreserved": [None, False, 0, "", [], {}]},
    }
    before = deepcopy(event)
    raw = "[AGENT_EXECUTION] selection | " + long_text + " | " + json.dumps(event, ensure_ascii=False)
    with captured_logs() as (output, records):
        logger.bind(agent_execution=event).info("{}", raw)
    assert parse_event_blocks(output.getvalue()) == [event]
    assert records[-1]["message"] == raw
    assert records[-1]["extra"]["agent_execution"] == before
    assert event == before
    assert "[truncated" not in output.getvalue()
    assert "END_OF_LONG_TEXT" in output.getvalue()
    assert "[AGENT_EXECUTION]" in output.getvalue()
    assert feature + " | selection | " + status in output.getvalue()
    assert str(records[-1]["line"]) in output.getvalue()
    assert records[-1]["function"] in output.getvalue()


def test_plain_start_end_debug_and_exception_are_preserved():
    messages = [
        "[CONNECTOR][LLM] START",
        "[CONNECTOR][LLM] END | elapsed=1234ms",
        "[DEBUG] " + "긴 내용\n" * 1000 + "LAST_LINE",
    ]
    with captured_logs() as (output, records), full_console_logs():
        logger.info(messages[0])
        logger.info(messages[1])
        logger.debug(messages[2])
        try:
            msg = "EXCEPTION_END_MARKER"
            raise ValueError(msg)  # noqa: TRY301 - verify traceback rendering
        except ValueError:
            logger.exception("[CONNECTOR] FAILED")
    rendered = output.getvalue()
    assert all(message in rendered for message in messages)
    assert "ValueError: EXCEPTION_END_MARKER" in rendered
    assert len(records) == 4


def test_color_markup_and_braces_in_values_are_literal():
    event = {
        "feature": "quality_evaluation",
        "phase": "planning",
        "status": "started",
        "summary": '<red>NOT_MARKUP</red> {extra[secret]} "quoted"',
    }
    with captured_logs(colorize=True) as (output, _):
        logger.bind(agent_execution=event).info("original")
    assert parse_event_blocks(output.getvalue()) == [event]


def test_malformed_payload_falls_back_to_original_message():
    with captured_logs() as (output, _):
        logger.bind(agent_execution={"unserializable": object()}).info("ORIGINAL_TAIL")
    assert "ORIGINAL_TAIL" in output.getvalue()


def test_five_features_parallel_keep_all_events_and_restore_context():
    async def check():
        gate = asyncio.Event()

        async def perform():
            assert full_payloads_enabled()
            execution_event("call", "START")
            await gate.wait()
            execution_event("call", "END", sourceUrls=["https://example.test"])
            return SimpleNamespace(execution_log=[])

        tasks = [asyncio.create_task(logged_run(feature)(perform)()) for feature in FEATURES]
        gate.set()
        results = await asyncio.gather(*tasks)
        assert not full_payloads_enabled()
        return results

    with captured_logs() as (output, _):
        results = asyncio.run(check())
    rendered = parse_event_blocks(output.getvalue())
    expected = [event.model_dump(mode="json", by_alias=True) for result in results for event in result.execution_log]

    def key(event):
        return event["runId"], event["sequence"]

    assert sorted(rendered, key=key) == sorted(expected, key=key)
    assert len(rendered) == 20
    assert len({event["runId"] for event in rendered}) == 5


def test_scope_restored_after_failure_and_cancellation():
    @logged_run("quality_evaluation")
    async def fail(*, cancel):
        assert full_payloads_enabled()
        if cancel:
            raise asyncio.CancelledError
        raise ValueError

    async def check():
        for cancel in (False, True):
            with pytest.raises(asyncio.CancelledError if cancel else ValueError):
                await fail(cancel=cancel)
            assert not full_payloads_enabled()

    asyncio.run(check())


def test_connector_payload_is_unabridged_but_sensitive_keys_remain_masked():
    long_text = "근거\n" * 2000 + "PAYLOAD_END"

    @log_connector(connector_type="WEB", log_input=True, log_output=True)
    async def tool(**kwargs: object):
        return {"result": kwargs["content"]}

    @logged_run("event_verification")
    async def run():
        return await tool(content=long_text, api_key="DO_NOT_PRINT_THIS")

    with captured_logs() as (output, records):
        asyncio.run(run())
    request = next(row["message"] for row in records if "REQUEST | kwargs=" in row["message"])
    response = next(row["message"] for row in records if "RESPONSE | result=" in row["message"])
    assert json.loads(request.split("kwargs=", 1)[1]) == {"content": long_text, "api_key": "***"}
    assert json.loads(response.split("result=", 1)[1]) == {"result": long_text}
    assert "DO_NOT_PRINT_THIS" not in output.getvalue()
    assert "[truncated" not in output.getvalue()
    # Other applications retain their established length policy.
    assert "[truncated" in serialize({"text": long_text})


def test_http_request_body_is_complete_and_response_unchanged():
    app = FastAPI()
    app.add_middleware(RequestLoggingMiddleware, full_payloads=True)

    @app.post("/events/verifications")
    async def endpoint(request: Request):
        return await request.json()

    body = {"text": "검증 본문\n" * 1000 + "REQUEST_TAIL"}
    with captured_logs() as (_, records), TestClient(app) as client:
        response = client.post("/events/verifications", json=body)
    message = next(row["message"] for row in records if "[REQUEST] BODY\n" in row["message"])
    assert json.loads(message.split("[REQUEST] BODY\n", 1)[1]) == body
    assert response.json() == body
    assert "[truncated" in _format_body_for_debug(json.dumps(body))
