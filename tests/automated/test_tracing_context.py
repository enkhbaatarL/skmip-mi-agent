# ruff: noqa: PT009

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from contextlib import contextmanager
import os
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.common.tracing.context import (
    TraceContext,
    build_aip_headers,
    build_langgraph_config,
    get_current_langchain_callbacks,
    mlflow_trace_context,
    new_transaction_id,
)
from apps.connectors.mlflow.tracing import setup_mlflow_tracing


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.connectors.llm.llm_client import (
    _extra_headers,
    _mlflow_llm_span,
    _set_mlflow_span_outputs,
    _start_langchain_llm_run,
    _start_openai_child_span,
)


class TracingContextTest(unittest.TestCase):
    def test_new_transaction_id_returns_uuid4_string(self) -> None:
        transaction_id = new_transaction_id()

        self.assertRegex(
            transaction_id,
            re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"),
        )

    def test_aip_headers_omit_chat_id_without_scenario_group(self) -> None:
        context = TraceContext(transaction_id="tx-1", app_identifier="scenario-group-agent")

        self.assertEqual(
            build_aip_headers(context),
            {
                "aip-transaction-id": "tx-1",
                "aip-app-id": "scenario-group-agent",
            },
        )

    def test_aip_headers_map_scenario_group_to_chat_id(self) -> None:
        context = TraceContext(
            transaction_id="tx-1",
            app_identifier="scenario-group-agent",
            scenario_group_id="42",
        )

        self.assertEqual(
            build_aip_headers(context),
            {
                "aip-transaction-id": "tx-1",
                "aip-app-id": "scenario-group-agent",
                "aip-chat-id": "42",
            },
        )

    def test_langgraph_thread_id_uses_transaction_id_without_scenario_group(self) -> None:
        context = TraceContext(transaction_id="tx-1", app_identifier="scenario-group-agent")

        self.assertEqual(
            build_langgraph_config(context),
            {"configurable": {"thread_id": "tx-1", "transaction_id": "tx-1"}},
        )

    def test_langgraph_thread_id_uses_scenario_group_when_available(self) -> None:
        context = TraceContext(
            transaction_id="tx-1",
            app_identifier="scenario-group-agent",
            scenario_group_id="77",
        )

        self.assertEqual(
            build_langgraph_config(context),
            {
                "configurable": {
                    "thread_id": "77",
                    "scenario_group_id": "77",
                    "transaction_id": "tx-1",
                },
            },
        )

    def test_llm_extra_headers_is_none_without_trace_context(self) -> None:
        self.assertIsNone(_extra_headers(None))

    def test_llm_extra_headers_uses_aip_mapping(self) -> None:
        context = TraceContext(
            transaction_id="tx-1",
            app_identifier="scenario-group-agent",
            scenario_group_id="42",
        )

        self.assertEqual(_extra_headers(context), build_aip_headers(context))

    def test_mlflow_trace_context_sets_metadata_tags_and_session(self) -> None:
        captured: dict[str, object] = {}

        @contextmanager
        def fake_context(**kwargs: object) -> Iterator[None]:
            captured.update(kwargs)
            yield

        previous = sys.modules.get("mlflow")
        sys.modules["mlflow"] = SimpleNamespace(tracing=SimpleNamespace(context=fake_context))
        try:
            context = TraceContext(
                transaction_id="tx-1",
                app_identifier="scenario-group-agent",
                scenario_group_id="42",
            )
            with patch(
                "apps.common.configs.config.get_settings",
                return_value=SimpleNamespace(mlflow_tracing_enabled=True),
            ), mlflow_trace_context(context):
                pass
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

        self.assertEqual(captured["session_id"], "42")
        self.assertEqual(
            captured["metadata"],
            {
                "aip.transaction_id": "tx-1",
                "aip.app_id": "scenario-group-agent",
                "scenario_group_id": "42",
            },
        )
        self.assertEqual(captured["tags"], {"app_id": "scenario-group-agent", "scenario_group_id": "42"})

    def test_mlflow_trace_context_skips_mlflow_when_disabled(self) -> None:
        captured: dict[str, object] = {}

        @contextmanager
        def fake_context(**kwargs: object) -> Iterator[None]:
            captured.update(kwargs)
            yield

        previous = sys.modules.get("mlflow")
        sys.modules["mlflow"] = SimpleNamespace(tracing=SimpleNamespace(context=fake_context))
        try:
            context = TraceContext(transaction_id="tx-1", app_identifier="scenario-group-agent")
            body_executed = False
            with patch(
                "apps.common.configs.config.get_settings",
                return_value=SimpleNamespace(mlflow_tracing_enabled=False),
            ), mlflow_trace_context(context):
                body_executed = True
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

        self.assertTrue(body_executed)
        self.assertEqual(captured, {})

    def test_mlflow_trace_context_continues_when_context_enter_fails(self) -> None:
        class FailingManager:
            def __enter__(self) -> None:
                message = "trace unavailable"
                raise RuntimeError(message)

            def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
                return None

        previous = sys.modules.get("mlflow")
        sys.modules["mlflow"] = SimpleNamespace(
            tracing=SimpleNamespace(context=lambda **_: FailingManager()),
        )
        try:
            context = TraceContext(transaction_id="tx-1", app_identifier="scenario-group-agent")
            body_executed = False
            with patch(
                "apps.common.configs.config.get_settings",
                return_value=SimpleNamespace(mlflow_tracing_enabled=True),
            ), mlflow_trace_context(context):
                body_executed = True
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

        self.assertTrue(body_executed)

    def test_setup_mlflow_tracing_enables_langchain_autolog_only(self) -> None:
        calls: list[tuple[str, object]] = []

        fake_mlflow = SimpleNamespace(
            set_tracking_uri=lambda uri: calls.append(("tracking_uri", uri)),
            set_experiment=lambda name: calls.append(("experiment", name)),
            langchain=SimpleNamespace(autolog=lambda **kwargs: calls.append(("langchain_autolog", kwargs))),
            openai=SimpleNamespace(autolog=lambda: calls.append(("openai_autolog", None))),
        )

        previous = sys.modules.get("mlflow")
        sys.modules["mlflow"] = fake_mlflow
        try:
            setup_mlflow_tracing(
                SimpleNamespace(
                    mlflow_tracing_enabled=True,
                    mlflow_tracking_uri="http://mlflow.example",
                    mlflow_experiment_name="mi-agent-test",
                    mlflow_tracking_username="",
                    mlflow_tracking_password="",
                    mlflow_langchain_run_tracer_inline=False,
                ),
            )
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

        self.assertIn(("tracking_uri", "http://mlflow.example"), calls)
        self.assertIn(("experiment", "mi-agent-test"), calls)
        self.assertIn(("langchain_autolog", {"run_tracer_inline": False}), calls)
        self.assertNotIn(("openai_autolog", None), calls)

    def test_mlflow_llm_span_sets_inputs_and_outputs(self) -> None:
        class FakeSpan:
            def __init__(self) -> None:
                self.inputs: object | None = None
                self.outputs: object | None = None

            def set_inputs(self, inputs: object) -> None:
                self.inputs = inputs

            def set_outputs(self, outputs: object) -> None:
                self.outputs = outputs

        class FakeManager:
            def __init__(self, span: FakeSpan) -> None:
                self.span = span
                self.exited = False

            def __enter__(self) -> FakeSpan:
                return self.span

            def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
                self.exited = True

        captured: dict[str, object] = {}
        fake_span = FakeSpan()
        fake_manager = FakeManager(fake_span)

        def fake_start_span(**kwargs: object) -> FakeManager:
            captured.update(kwargs)
            return fake_manager

        previous = sys.modules.get("mlflow")
        sys.modules["mlflow"] = SimpleNamespace(start_span=fake_start_span)
        try:
            messages = [{"role": "user", "content": "hello"}]
            trace_context = TraceContext(
                transaction_id="tx-1",
                app_identifier="scenario-group-agent",
                scenario_group_id="42",
            )
            with patch(
                "apps.connectors.llm.llm_client.get_settings",
                return_value=SimpleNamespace(mlflow_tracing_enabled=True),
            ), _mlflow_llm_span(
                name="llm.test",
                model="model-a",
                messages=messages,
                trace_context=trace_context,
            ) as span:
                _set_mlflow_span_outputs(span, {"content": "world"})
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

        self.assertEqual(captured["name"], "llm.test")
        self.assertEqual(captured["span_type"], "CHAT_MODEL")
        self.assertEqual(
            captured["attributes"],
            {
                "model": "model-a",
                "aip.transaction_id": "tx-1",
                "aip.app_id": "scenario-group-agent",
                "scenario_group_id": "42",
            },
        )
        self.assertEqual(fake_span.inputs, {"messages": [{"role": "user", "content": "hello"}]})
        self.assertEqual(fake_span.outputs, {"content": "world"})
        self.assertTrue(fake_manager.exited)

    def test_mlflow_llm_span_preserves_body_exception(self) -> None:
        def raise_body_failed() -> None:
            message = "body failed"
            raise ValueError(message)

        class FakeManager:
            def __enter__(self) -> object:
                return SimpleNamespace(set_inputs=lambda _: None)

            def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
                return None

        previous = sys.modules.get("mlflow")
        sys.modules["mlflow"] = SimpleNamespace(start_span=lambda **_: FakeManager())
        try:
            with patch(
                "apps.connectors.llm.llm_client.get_settings",
                return_value=SimpleNamespace(mlflow_tracing_enabled=True),
            ):
                try:
                    with _mlflow_llm_span(name="llm.test", model="model-a", messages=[]):
                        raise_body_failed()
                except ValueError as exc:
                    self.assertEqual(str(exc), "body failed")
                else:
                    self.fail("ValueError was not raised")
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

    def test_langgraph_runtime_context_exposes_trace_context_to_node(self) -> None:
        class RuntimeState(TypedDict, total=False):
            input: str
            transaction_id: str

        class RuntimeAwareNode(BaseNode):
            async def run(
                self,
                state: RuntimeState,
                runtime: Runtime[TraceContext] | None = None,
            ) -> dict[str, str]:
                if runtime is None:
                    return {"transaction_id": ""}
                return {"transaction_id": runtime.context.transaction_id}

        context = TraceContext(transaction_id="tx-1", app_identifier="scenario-group-agent")
        builder = StateGraph(RuntimeState, context_schema=TraceContext)
        builder.add_node("runtime_node", RuntimeAwareNode())
        builder.set_entry_point("runtime_node")
        builder.set_finish_point("runtime_node")

        result = asyncio.run(
            builder.compile().ainvoke(
                {"input": "hello"},
                config=build_langgraph_config(context),
                context=context,
            ),
        )

        self.assertEqual(result["transaction_id"], "tx-1")

    def test_base_node_exposes_runnable_config_callbacks_during_run(self) -> None:
        expected_callbacks = SimpleNamespace(name="callbacks")

        class CallbackAwareNode(BaseNode):
            async def run(self, state: dict[str, str]) -> dict[str, object]:
                return {"callbacks": get_current_langchain_callbacks()}

        result = asyncio.run(CallbackAwareNode()({}, config={"callbacks": expected_callbacks}))

        self.assertIs(result["callbacks"], expected_callbacks)

    def test_langchain_llm_run_start_does_not_pass_duplicate_metadata(self) -> None:
        captured: dict[str, object] = {}
        expected_manager = SimpleNamespace(run_id="llm-run")

        class FakeCallbacks:
            async def on_chat_model_start(
                self,
                serialized: dict[str, object],
                messages: list[object],
                **kwargs: object,
            ) -> list[object]:
                captured["serialized"] = serialized
                captured["messages"] = messages
                captured["kwargs"] = kwargs
                return [expected_manager]

        trace_context = TraceContext(
            transaction_id="tx-1",
            app_identifier="scenario-group-agent",
            scenario_group_id="42",
        )

        async def run_case() -> object:
            with patch(
                "apps.connectors.llm.llm_client.get_current_langchain_callbacks",
                return_value=FakeCallbacks(),
            ):
                return await _start_langchain_llm_run(
                    name="llm.test",
                    model="model-a",
                    messages=[{"role": "user", "content": "hello"}],
                    trace_context=trace_context,
                    attributes={"llm.call_type": "structured_output"},
                )

        manager = asyncio.run(run_case())

        self.assertIs(manager, expected_manager)
        self.assertNotIn("metadata", captured["kwargs"])
        self.assertEqual(captured["kwargs"]["aip.transaction_id"], "tx-1")
        self.assertEqual(captured["kwargs"]["aip.app_id"], "scenario-group-agent")
        self.assertEqual(captured["kwargs"]["scenario_group_id"], "42")
        self.assertEqual(captured["kwargs"]["llm.call_type"], "structured_output")

    def test_openai_child_span_uses_langchain_llm_span_as_parent(self) -> None:
        captured: dict[str, object] = {}
        parent_span = SimpleNamespace(span_id="parent")
        child_span = SimpleNamespace(end=lambda **_: None)

        def fake_start_span_no_context(**kwargs: object) -> object:
            captured.update(kwargs)
            return child_span

        previous = sys.modules.get("mlflow")
        sys.modules["mlflow"] = SimpleNamespace(start_span_no_context=fake_start_span_no_context)
        try:
            with patch(
                "apps.connectors.llm.llm_client.get_settings",
                return_value=SimpleNamespace(mlflow_tracing_enabled=True),
            ):
                span = _start_openai_child_span(
                    parent_span=parent_span,
                    model="model-a",
                    messages=[{"role": "user", "content": "hello"}],
                )
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

        self.assertIs(span, child_span)
        self.assertEqual(captured["name"], "AsyncCompletions")
        self.assertIs(captured["parent_span"], parent_span)
        self.assertEqual(captured["inputs"], {"messages": [{"role": "user", "content": "hello"}]})


if __name__ == "__main__":
    unittest.main()
