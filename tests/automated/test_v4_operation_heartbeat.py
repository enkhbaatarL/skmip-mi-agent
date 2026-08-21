# ruff: noqa: CPY001, S101

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from contextlib import nullcontext
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from apps.agents.scenario_group_agent.flows.create_signposts import flow as signpost_flow
from apps.agents.scenario_group_agent.flows.validate_scenarios import flow as validation_flow


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="test-app"),
    )


def test_v4_validation_inline_runs_inside_shared_heartbeat_wrapper() -> None:
    async def exercise() -> tuple[object, Mock, Mock]:
        output = object()
        service = Mock()
        graph = SimpleNamespace(ainvoke=AsyncMock(return_value={"status": "success"}))
        runner = Mock()

        async def run_with_heartbeat(
            scenario_group_id: int,
            operation_id: str,
            operation: Awaitable[object],
        ) -> object:
            assert scenario_group_id == 120
            assert operation_id == "validation-op"
            result = await operation
            assert service.start_operation.called
            return result

        runner.run_with_heartbeat = AsyncMock(side_effect=run_with_heartbeat)
        with (
            patch.dict(
                sys.modules,
                {"apps.common.configs.config": SimpleNamespace(get_settings=_settings)},
            ),
            patch.object(validation_flow, "get_compiled_graph", return_value=graph),
            patch.object(validation_flow, "_bg_to_output", return_value=output),
            patch.object(validation_flow, "mlflow_trace_context", return_value=nullcontext()),
            patch.object(validation_flow, "build_langgraph_config", return_value={}),
            patch.object(validation_flow, "ScenarioGroupOperationService", return_value=service),
            patch.object(validation_flow, "get_scenario_group_operation_task_runner", return_value=runner),
        ):
            result = await validation_flow.run_validate_scenarios_inline(
                scenario_group_id=120,
                user_id=101,
                request_table={"headers": [], "rows": []},
                operation_id="validation-op",
            )
        return result, runner, service

    result, runner, service = asyncio.run(exercise())

    assert result is not None
    runner.run_with_heartbeat.assert_awaited_once()
    service.start_operation.assert_called_once_with(120, "validation-op", phase="validation")


def test_v4_signpost_inline_keeps_heartbeat_through_terminal_completion() -> None:
    async def exercise() -> tuple[object, Mock, Mock]:
        output = object()
        service = Mock()
        graph = SimpleNamespace(ainvoke=AsyncMock(return_value={"status": "success"}))
        runner = Mock()

        async def run_with_heartbeat(
            scenario_group_id: int,
            operation_id: str,
            operation: Awaitable[object],
        ) -> object:
            assert scenario_group_id == 120
            assert operation_id == "signpost-op"
            result = await operation
            assert service.complete_operation.called
            return result

        runner.run_with_heartbeat = AsyncMock(side_effect=run_with_heartbeat)
        with (
            patch.dict(
                sys.modules,
                {"apps.common.configs.config": SimpleNamespace(get_settings=_settings)},
            ),
            patch.object(signpost_flow, "get_compiled_graph", return_value=graph),
            patch.object(signpost_flow, "_bg_to_output", return_value=output),
            patch.object(signpost_flow, "mlflow_trace_context", return_value=nullcontext()),
            patch.object(signpost_flow, "build_langgraph_config", return_value={}),
            patch.object(signpost_flow, "ScenarioGroupOperationService", return_value=service),
            patch.object(signpost_flow, "get_scenario_group_operation_task_runner", return_value=runner),
        ):
            result = await signpost_flow.run_create_signposts_inline(
                scenario_group_id=120,
                user_id=101,
                request_table=None,
                operation_id="signpost-op",
            )
        return result, runner, service

    result, runner, service = asyncio.run(exercise())

    assert result is not None
    runner.run_with_heartbeat.assert_awaited_once()
    service.start_operation.assert_called_once_with(120, "signpost-op", phase="signpost")
    service.complete_operation.assert_called_once_with(
        scenario_group_id=120,
        operation_id="signpost-op",
        phase="signpost",
        message_markdown="Signpost 생성을 완료했습니다.",
    )
