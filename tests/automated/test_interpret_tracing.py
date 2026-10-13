# ruff: noqa: PT009

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.callbacks.base import BaseCallbackHandler
import yaml


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.agents.interpret_agent.constants import (  # noqa: E402
    AGENT_NAME,
    INTERPRET_AGENT_VERSION,
)
from apps.agents.interpret_agent.flows.interpret_price import flow, nodes  # noqa: E402
from apps.agents.interpret_agent.flows.interpret_price.api_schema import (  # noqa: E402
    GroupSynthesisOut,
    PriceInterpretationMetaOut,
    PriceInterpretationResult,
)
from apps.agents.interpret_agent.flows.interpret_price.schema import (  # noqa: E402
    InterpretInput,
    ScenarioFeatures,
    ScenarioPrices,
)
from apps.agents.interpret_agent.flows.interpret_price.state import (  # noqa: E402
    InterpretPriceState,
)
from apps.common.tracing.context import (  # noqa: E402
    TraceContext,
    build_langgraph_config,
    get_current_langchain_callbacks,
)
import interpret as interpret_entrypoint  # noqa: E402


REPO_ROOT = Path(__file__).resolve().parents[2]


class InterpretTracingConfigTest(unittest.TestCase):
    def test_public_vm_profile_and_credentials_follow_tracing_guide(self) -> None:
        config = yaml.safe_load((REPO_ROOT / "envs" / "config.yaml").read_text(encoding="utf-8"))

        self.assertEqual(
            config["agents"][AGENT_NAME],
            {
                "mlflow_experiment_name": "interpret_agent_local",
                "aip_app_id": "interpret_agent",
                "mlflow_tracing_enabled": True,
            },
        )
        self.assertEqual(config["mlflow_tracking_username"], "${MLFLOW_TRACKING_USERNAME}")
        self.assertEqual(config["mlflow_tracking_password"], "${MLFLOW_TRACKING_PASSWORD}")

    def test_graph_declares_trace_context_schema(self) -> None:
        flow.get_compiled_graph.cache_clear()
        try:
            graph = flow.get_compiled_graph()
            self.assertIs(graph.context_schema, TraceContext)
        finally:
            flow.get_compiled_graph.cache_clear()


class InterpretEntrypointTracingTest(unittest.IsolatedAsyncioTestCase):
    def test_openapi_uses_interpret_agent_version(self) -> None:
        self.assertEqual(interpret_entrypoint.app.version, INTERPRET_AGENT_VERSION)
        self.assertEqual(
            interpret_entrypoint.app.openapi()["info"]["version"],
            "v4.1.7",
        )

    async def test_lifespan_initializes_interpret_agent_mlflow_profile(self) -> None:
        cfg = SimpleNamespace(
            log_level="INFO",
            callback_oauth2_token_url="",
        )
        setup_mlflow_tracing = MagicMock()

        with (
            patch("apps.common.configs.config.get_settings", return_value=cfg),
            patch(
                "apps.connectors.mlflow.tracing.setup_mlflow_tracing",
                setup_mlflow_tracing,
            ),
            patch.object(interpret_entrypoint, "setup_logging"),
            patch.object(interpret_entrypoint, "get_sync_engine", return_value=object()),
            patch.object(interpret_entrypoint, "validate_schema"),
        ):
            async with interpret_entrypoint.lifespan(interpret_entrypoint.app):
                pass

        setup_mlflow_tracing.assert_called_once_with(cfg, agent_name=AGENT_NAME)


class InterpretFlowTracingTest(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _result() -> PriceInterpretationResult:
        return PriceInterpretationResult(
            meta=PriceInterpretationMetaOut(
                scenario_group_id=52,
                base_scenario_id="MI Base",
            ),
            scenarios=[],
            synthesis=GroupSynthesisOut(overall_message="summary"),
        )

    async def test_top_level_invoke_reuses_one_configured_trace_context(self) -> None:
        expected_result = self._result()
        graph = SimpleNamespace(ainvoke=AsyncMock(return_value={"result": expected_result}))
        cfg = SimpleNamespace(
            get_agent_config=lambda agent_name: SimpleNamespace(
                aip_app_id=f"configured-{agent_name}",
            ),
        )
        entered_contexts: list[TraceContext] = []

        @contextmanager
        def capture_trace_context(context: TraceContext) -> Iterator[None]:
            entered_contexts.append(context)
            yield

        with (
            patch("apps.common.configs.config.get_settings", return_value=cfg),
            patch.object(flow, "new_transaction_id", return_value="tx-interpret-1"),
            patch.object(flow, "mlflow_trace_context", side_effect=capture_trace_context),
            patch.object(flow, "get_compiled_graph", return_value=graph),
        ):
            result = await flow.run_interpret_price(52, [101, 102])

        self.assertEqual(result, expected_result)
        graph.ainvoke.assert_awaited_once()
        state = graph.ainvoke.await_args.args[0]
        trace_context = graph.ainvoke.await_args.kwargs["context"]

        self.assertEqual(state.scenario_group_id, 52)
        self.assertEqual(state.scenario_ids, [101, 102])
        self.assertEqual(trace_context.transaction_id, "tx-interpret-1")
        self.assertEqual(trace_context.app_identifier, "configured-interpret_agent")
        self.assertEqual(trace_context.agent_name, AGENT_NAME)
        self.assertEqual(trace_context.api_identifier, "interpret_price")
        self.assertEqual(trace_context.session_id, "52")
        self.assertEqual(
            trace_context.tags,
            {"interpret_agent_version": INTERPRET_AGENT_VERSION},
        )
        self.assertEqual(graph.ainvoke.await_args.kwargs["config"], build_langgraph_config(trace_context))
        self.assertEqual(entered_contexts, [trace_context])

    async def test_all_llm_calls_receive_trace_context_and_graph_callbacks(self) -> None:
        trace_context = TraceContext(
            transaction_id="tx-interpret-2",
            app_identifier="interpret_agent",
            agent_name=AGENT_NAME,
            session_id="52",
        )
        callback_handler = BaseCallbackHandler()
        calls: list[tuple[TraceContext | None, object | None, bool]] = []

        async def fake_invoke_llm_structured_output(**kwargs: object) -> object:
            calls.append(
                (
                    kwargs.get("trace_context"),
                    get_current_langchain_callbacks(),
                    bool(kwargs.get("stream")),
                ),
            )
            output_schema = kwargs["output_schema"]
            if output_schema is nodes.si_prompt.ScenarioComparisonLLMOutput:
                result = output_schema(
                    identity="**identity**",
                    driver_phase="## __driver__",
                    price_character="<strong>price</strong>",
                    summary="`summary`",
                )
            else:
                result = output_schema(overall_message="**overall**")
            return SimpleNamespace(result=result)

        scenario_ids = ("101", "102")
        interpret_input = InterpretInput(
            scenario_group_id=52,
            base_scenario_id="MI Base",
            mi_base_case_id=15,
            mi_base_price_run_seq=501,
            scenario_ids=list(scenario_ids),
            scenario_features={
                "MI Base": ScenarioFeatures(scenario_id="MI Base"),
                **{scenario_id: ScenarioFeatures(scenario_id=scenario_id) for scenario_id in scenario_ids},
            },
            scenario_prices={
                "MI Base": ScenarioPrices(scenario_id="MI Base"),
                **{scenario_id: ScenarioPrices(scenario_id=scenario_id) for scenario_id in scenario_ids},
            },
        )
        config = build_langgraph_config(trace_context)
        config["callbacks"] = [callback_handler]
        flow.get_compiled_graph.cache_clear()

        with (
            patch.object(
                nodes.ProposalParameterService,
                "load_interpret_input",
                return_value=interpret_input,
            ),
            patch.object(
                nodes,
                "get_settings",
                return_value=SimpleNamespace(
                    llm_stream_enabled=True,
                    llm_reasoning_effort="default",
                ),
            ),
            patch(
                "apps.connectors.llm.llm_client.invoke_llm_structured_output",
                new=fake_invoke_llm_structured_output,
            ),
        ):
            final_state = await flow.get_compiled_graph().ainvoke(
                InterpretPriceState(scenario_group_id=52, scenario_ids=[101, 102]),
                config=config,
                context=trace_context,
            )

        self.assertEqual(len(final_state["result"].scenarios), 2)
        for scenario in final_state["result"].scenarios:
            self.assertEqual(scenario.identity, "identity")
            self.assertEqual(scenario.driver_phase, "driver")
            self.assertEqual(scenario.price_character, "price")
            self.assertEqual(scenario.summary, "summary")
        self.assertEqual(final_state["result"].synthesis.overall_message, "overall")
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(call_trace_context is trace_context for call_trace_context, _, _ in calls))
        self.assertTrue(
            all(callback_handler in getattr(call_callbacks, "handlers", []) for _, call_callbacks, _ in calls),
        )
        self.assertTrue(all(stream for _, _, stream in calls))


if __name__ == "__main__":
    unittest.main()
