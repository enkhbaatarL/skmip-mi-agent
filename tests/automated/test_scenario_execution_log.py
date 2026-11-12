from __future__ import annotations

# ruff: noqa: CPY001, S101, ANN001, ANN201, ANN202
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.operation import V4OperationProgressRecorder
from apps.agents.scenario_group_agent.utils.execution_log import (
    execution_event,
    execution_events,
    logged_run,
    traced_call,
)
from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationEventModel
from tests.automated.test_scenario_quality_repair import comparison, judgment, plan, snapshot, strategies
from tests.manual.quality_eval.repair_sandbox import repair_sandbox


def test_concurrent_runs_are_isolated_and_child_work_shares_the_run():
    @logged_run("test")
    async def run(index):
        async def child():
            await asyncio.sleep(0)
            execution_event("child", "병렬 작업", eventId=index)

        await asyncio.gather(child(), child())
        return SimpleNamespace(execution_log=[])

    async def check():
        first, second = await asyncio.gather(run(1), run(2))
        assert first.execution_log[0].run_id != second.execution_log[0].run_id
        for index, result in enumerate([first, second], 1):
            assert [event.sequence for event in result.execution_log] == list(range(1, 5))
            assert all(event.details["eventId"] == index for event in result.execution_log if event.phase == "child")
        assert execution_events() == []

    asyncio.run(check())


def test_nested_run_has_parent_and_restores_context():
    @logged_run("child")
    async def child():
        return SimpleNamespace(execution_log=[])

    @logged_run("parent")
    async def parent():
        result = await child()
        parent_id = execution_events()[0].run_id
        assert result.execution_log[0].parent_run_id == parent_id
        assert execution_events()[0].feature == "parent"

    asyncio.run(parent())
    assert execution_events() == []


@pytest.mark.parametrize("cancelled", [False, True])
def test_call_failure_is_not_success_and_exception_content_is_not_logged(cancelled):
    observed = []

    @logged_run("failure")
    async def run():
        async def external():
            if cancelled:
                raise asyncio.CancelledError
            msg = "PRIVATE_PROMPT_OR_CREDENTIAL"
            raise RuntimeError(msg)

        try:
            await traced_call("tool", "search", external)
        except (RuntimeError, asyncio.CancelledError):
            observed.extend(execution_events())
            raise

    with pytest.raises(asyncio.CancelledError if cancelled else RuntimeError):
        asyncio.run(run())
    calls = [event for event in observed if event.phase == "call"]
    assert [event.status for event in calls] == ["started", "interrupted" if cancelled else "failed"]
    assert calls[0].details["callId"] == calls[1].details["callId"]
    assert "PRIVATE_PROMPT_OR_CREDENTIAL" not in str(observed)
    assert execution_events() == []


def test_design_retry_logs_are_attached_without_payload_keyword_collision(monkeypatch):
    from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import operation

    append = AsyncMock()
    monkeypatch.setattr(operation.asyncio, "to_thread", append)

    @logged_run("scenario_design")
    async def run():
        recorder = V4OperationProgressRecorder(1, "operation-1", "trace-1")
        await recorder.on_node_update(
            "__custom__",
            {
                "kind": "stage_retry",
                "phase": "dimension_design",
                "stage": "dimension_design",
                "attempt": 2,
                "validationCode": "UNKNOWN_SOURCE_REFERENCE",
                "referenceIds": ["D2"],
                "draft": {"private": "do not log failed draft"},
            },
            None,
        )

    asyncio.run(run())
    payload = append.call_args.kwargs["payload"]
    assert payload["phase"] == "dimension_design"
    assert payload["executionLog"][-1]["phase"] == "retry"
    assert "do not log failed draft" not in str(append.call_args_list)


def test_quality_planning_and_post_save_evaluation_are_in_operation_history(monkeypatch):
    from uuid import uuid4

    from apps.agents.scenario_group_agent.flows.evaluate_scenarios import flow
    from apps.agents.scenario_group_agent.prompts.scenario_quality_repair import QualityRepairReview

    with repair_sandbox(snapshot()) as db:
        first, _ = db.service.prepare(130, 42, str(uuid4()))
        responses = iter(
            [
                judgment(),
                strategies(),
                comparison(),
                plan(),
                QualityRepairReview(can_proceed=True, reason="근거 보존"),
                judgment("FAIL"),
            ],
        )

        async def invoke(**kwargs: object):
            return SimpleNamespace(result=next(responses), model="mock", usage=None)

        monkeypatch.setattr(flow, "invoke_llm_structured_output", invoke)
        asyncio.run(flow.run_quality_evaluation(130, first.operation_id))
        with db.factory() as session:
            rows = session.scalars(select(MiScenarioGroupOperationEventModel)).all()
            events = [event for row in rows for event in (row.payload or {}).get("executionLog", [])]
        phases = [event["phase"] for event in events]
        assert phases.index("planning") < phases.index("selection") < phases.index("application")
        assert any(event["phase"] == "evaluation" and event["details"].get("afterApplication") for event in events)
        last = next(event for event in events if event["phase"] == "comparison")
        assert last["details"]["scoreChange"] == "declined"
        assert last["details"]["reviewRequired"] is True
        assert any(event["details"].get("selectedCandidateId") == "A" for event in events)
