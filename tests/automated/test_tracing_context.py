# ruff: noqa: PT009

from __future__ import annotations

import asyncio
from contextlib import contextmanager
import os
import re
import sys
from types import SimpleNamespace
import unittest

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from typing_extensions import TypedDict

from apps.agents.scenario_group_agent.schemas.base import BaseNode
from apps.common.tracing.context import (
    TraceContext,
    build_aip_headers,
    build_langgraph_config,
    mlflow_trace_context,
    new_transaction_id,
)


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.connectors.llm.llm_client import _extra_headers


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

    def test_langgraph_thread_id_uses_transaction_id(self) -> None:
        context = TraceContext(transaction_id="tx-1", app_identifier="scenario-group-agent")

        self.assertEqual(build_langgraph_config(context), {"configurable": {"thread_id": "tx-1"}})

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
        def fake_context(**kwargs: object):
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
            with mlflow_trace_context(context):
                pass
        finally:
            if previous is None:
                sys.modules.pop("mlflow", None)
            else:
                sys.modules["mlflow"] = previous

        self.assertEqual(captured["client_request_id"], "tx-1")
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
            )
        )

        self.assertEqual(result["transaction_id"], "tx-1")


if __name__ == "__main__":
    unittest.main()
