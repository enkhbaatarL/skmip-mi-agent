# ruff: noqa: CPY001, S101

from __future__ import annotations

import asyncio
from contextlib import nullcontext
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from apps.agents.scenario_group_agent.flows import callback_delivery
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import v4_flow
from apps.agents.scenario_group_agent.flows.create_signposts import flow as signpost_flow
from apps.agents.scenario_group_agent.flows.validate_scenarios import flow as validation_flow
from apps.agents.scenario_group_agent.persistence import scenario_group_operation_service as operation_service
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.connectors.callback import callback_client


CALLBACK_URL = "https://callback.test/scenario-groups/14/validation/callback"


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        get_agent_config=lambda _agent_name: SimpleNamespace(aip_app_id="test-app"),
        callback_base_url="https://callback.test",
        callback_create_scenarios_path="/scenario-groups/{scenario_group_id}/generation/callback",
        callback_validate_scenarios_path="/scenario-groups/{scenario_group_id}/validation/callback",
        callback_create_signposts_path="/scenario-groups/{scenario_group_id}/signposts/callback",
        skip_callback=False,
        http_verify=True,
    )


def _patched_settings() -> patch:
    return patch.dict(sys.modules, {"apps.common.configs.config": SimpleNamespace(get_settings=_settings)})


def _client_factory(transport: httpx.MockTransport) -> object:
    real_client = httpx.AsyncClient

    def build(*_args: object, **_kwargs: object) -> httpx.AsyncClient:
        return real_client(transport=transport)

    return build


def _send(token_manager: Mock, transport: httpx.MockTransport) -> None:
    async def exercise() -> None:
        with (
            _patched_settings(),
            patch.object(callback_client, "get_token_manager", return_value=token_manager),
            patch.object(callback_client.httpx, "AsyncClient", new=_client_factory(transport)),
        ):
            await callback_client.send_callback(CALLBACK_URL, SimpleNamespace(model_dump=lambda **_: {}))

    asyncio.run(exercise())


def test_send_callback_wraps_token_failure_with_stage() -> None:
    token_error = httpx.HTTPStatusError(
        "Server error '530'",
        request=httpx.Request("POST", "https://callback.test/api/v1/oauth2/token"),
        response=httpx.Response(530),
    )
    token_manager = Mock(get_token=AsyncMock(side_effect=token_error))
    transport = httpx.MockTransport(lambda _request: httpx.Response(200))

    with pytest.raises(MIBaseError) as exc_info:
        _send(token_manager, transport)

    assert exc_info.value.error_code is ErrorCode.CALLBACK_DELIVERY_FAILED
    assert exc_info.value.context == {"stage": "token", "url": CALLBACK_URL, "status_code": 530}
    assert exc_info.value.__cause__ is token_error


def test_send_callback_wraps_post_status_failure_with_stage() -> None:
    token_manager = Mock(get_token=AsyncMock(return_value="token"))
    transport = httpx.MockTransport(lambda _request: httpx.Response(500))

    with pytest.raises(MIBaseError) as exc_info:
        _send(token_manager, transport)

    assert exc_info.value.error_code is ErrorCode.CALLBACK_DELIVERY_FAILED
    assert exc_info.value.context["stage"] == "post"
    assert exc_info.value.context["status_code"] == 500


def test_send_callback_wraps_post_transport_failure_with_stage() -> None:
    def raise_connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    token_manager = Mock(get_token=AsyncMock(return_value="token"))

    with pytest.raises(MIBaseError) as exc_info:
        _send(token_manager, httpx.MockTransport(raise_connect_error))

    assert exc_info.value.context["stage"] == "post"
    assert exc_info.value.context["status_code"] is None


def test_send_callback_refreshes_token_once_on_401() -> None:
    responses = iter([httpx.Response(401), httpx.Response(200)])
    token_manager = Mock(
        get_token=AsyncMock(return_value="stale"),
        refresh_token=AsyncMock(return_value="fresh"),
    )

    _send(token_manager, httpx.MockTransport(lambda _request: next(responses)))

    token_manager.refresh_token.assert_awaited_once()


OPERATION_IDS = {"validation": "validation-op", "signpost": "signpost-op", "v4_create": "create-op"}


async def _run_background(flow_kind: str, *, work_error: Exception | None, send_callback: AsyncMock) -> Mock:
    success_payload = SimpleNamespace(result="success")
    work = AsyncMock(side_effect=work_error) if work_error else AsyncMock(return_value=success_payload)
    service = Mock()
    with (
        _patched_settings(),
        patch.object(callback_delivery, "send_callback", new=send_callback),
        patch.object(callback_delivery, "ScenarioGroupOperationService", return_value=service),
    ):
        if flow_kind == "validation":
            with patch.object(validation_flow, "run_validate_scenarios_inline", new=work):
                await validation_flow.run_validate_scenarios_background(
                    scenario_group_id=14,
                    user_id=101,
                    request_table={"headers": [], "rows": []},
                    operation_id=OPERATION_IDS[flow_kind],
                )
        elif flow_kind == "signpost":
            with patch.object(signpost_flow, "run_create_signposts_inline", new=work):
                await signpost_flow.run_create_signposts_background(
                    scenario_group_id=14,
                    user_id=101,
                    request_table=None,
                    operation_id=OPERATION_IDS[flow_kind],
                )
        else:
            with (
                patch.object(v4_flow, "run_v4_multi_event_scenarios_inline", new=work),
                patch.object(
                    v4_flow,
                    "_require_output_data",
                    return_value=SimpleNamespace(scenario_group=None, table=None),
                ),
                patch.object(
                    v4_flow,
                    "ScenarioGroupPayload",
                    new=Mock(model_validate=Mock(return_value=SimpleNamespace(scenario_group_id=14))),
                ),
                patch.object(v4_flow, "CreateScenariosOut", new=Mock(return_value=success_payload)),
                patch.object(v4_flow, "mlflow_trace_context", return_value=nullcontext()),
            ):
                await v4_flow.run_v4_multi_event_scenarios_background(
                    {"scenario_group": {}, "operation_id": OPERATION_IDS[flow_kind]},
                )
    return service


@pytest.mark.parametrize("flow_kind", ["validation", "signpost", "v4_create"])
def test_success_callback_delivery_failure_is_recorded_without_failure_callback(flow_kind: str) -> None:
    delivery_error = MIBaseError(ErrorCode.CALLBACK_DELIVERY_FAILED, detail="stage=token")
    send_callback = AsyncMock(side_effect=delivery_error)

    service = asyncio.run(_run_background(flow_kind, work_error=None, send_callback=send_callback))

    send_callback.assert_awaited_once()
    assert send_callback.await_args.args[1].result == "success"
    service.record_callback_delivery.assert_called_once_with(
        14,
        OPERATION_IDS[flow_kind],
        callback_status="FAILED",
        result="success",
        error=delivery_error,
    )


@pytest.mark.parametrize("flow_kind", ["validation", "signpost", "v4_create"])
def test_work_failure_sends_single_failure_callback_and_records_delivery(flow_kind: str) -> None:
    send_callback = AsyncMock()

    service = asyncio.run(
        _run_background(flow_kind, work_error=RuntimeError("graph failed"), send_callback=send_callback),
    )

    send_callback.assert_awaited_once()
    payload = send_callback.await_args.args[1]
    assert payload.result == "failure"
    assert payload.reason == "graph failed"
    service.record_callback_delivery.assert_called_once_with(
        14,
        OPERATION_IDS[flow_kind],
        callback_status="SUCCEEDED",
        result="failure",
        error=None,
    )


def _deliver(*, skip_callback: bool, operation_id: str | None, service: Mock) -> None:
    async def exercise() -> None:
        settings = SimpleNamespace(skip_callback=skip_callback)
        with (
            patch.dict(sys.modules, {"apps.common.configs.config": SimpleNamespace(get_settings=lambda: settings)}),
            patch.object(callback_delivery, "send_callback", new=AsyncMock()),
            patch.object(callback_delivery, "ScenarioGroupOperationService", return_value=service),
        ):
            await callback_delivery.deliver_operation_callback(
                log_tag="test",
                callback_url=CALLBACK_URL,
                payload=SimpleNamespace(result="success"),
                scenario_group_id=14,
                operation_id=operation_id,
            )

    asyncio.run(exercise())


def test_deliver_records_skipped_when_callback_is_disabled() -> None:
    service = Mock()

    _deliver(skip_callback=True, operation_id="op", service=service)

    assert service.record_callback_delivery.call_args.kwargs["callback_status"] == "SKIPPED"


def test_deliver_without_operation_does_not_record() -> None:
    service = Mock()

    _deliver(skip_callback=False, operation_id=None, service=service)

    service.record_callback_delivery.assert_not_called()


def test_deliver_swallows_record_failure() -> None:
    service = Mock(record_callback_delivery=Mock(side_effect=RuntimeError("db down")))

    _deliver(skip_callback=False, operation_id="op", service=service)

    service.record_callback_delivery.assert_called_once()


def test_record_callback_delivery_appends_event_without_changing_terminal_status() -> None:
    operation = SimpleNamespace(status="succeeded")
    repository = Mock(fetch_by_id=Mock(return_value=operation))
    session = Mock()
    token_error = httpx.HTTPStatusError(
        "Server error '530'",
        request=httpx.Request("POST", "https://callback.test/api/v1/oauth2/token"),
        response=httpx.Response(530),
    )
    error = MIBaseError(
        ErrorCode.CALLBACK_DELIVERY_FAILED,
        detail="stage=token",
        context={"stage": "token", "url": CALLBACK_URL, "status_code": 530},
    )
    error.__cause__ = token_error

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch.object(operation_service, "ScenarioGroupOperationRepository", return_value=repository),
    ):
        operation_service.ScenarioGroupOperationService().record_callback_delivery(
            14,
            "validation-op",
            callback_status="FAILED",
            result="success",
            error=error,
        )

    kwargs = repository.append_event.call_args.kwargs
    assert repository.append_event.call_args.args == (operation,)
    assert kwargs["event_type"] == "callback_failed"
    assert "status" not in kwargs
    assert kwargs["payload"] == {
        "callbackStatus": "FAILED",
        "result": "success",
        "stage": "token",
        "url": CALLBACK_URL,
        "statusCode": 530,
        "error": repr(token_error),
    }
    session.commit.assert_called_once()
    session.close.assert_called_once()
