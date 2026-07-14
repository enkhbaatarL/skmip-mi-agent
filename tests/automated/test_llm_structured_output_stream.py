from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import os
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.agents.interpret_agent.flows.interpret_price import nodes  # noqa: E402
from apps.agents.interpret_agent.flows.interpret_price.api_schema import (  # noqa: E402
    ScenarioComparisonOut,
)
from apps.agents.interpret_agent.flows.interpret_price.schema import (  # noqa: E402
    ScenarioDiffBundle,
)
from apps.agents.interpret_agent.flows.interpret_price.state import (  # noqa: E402
    InterpretPriceState,
)
from apps.connectors.llm import llm_client  # noqa: E402


class _StructuredOutput(BaseModel):
    value: int


class _Usage:
    def model_dump(self) -> dict[str, int]:
        return {
            "prompt_tokens": 7,
            "completion_tokens": 4,
            "total_tokens": 11,
        }


class _FakeStream:
    def __init__(self, chunks: list[object]) -> None:
        self._chunks = chunks

    def __aiter__(self) -> AsyncIterator[object]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[object]:
        for chunk in self._chunks:
            yield chunk


def _content_chunk(content: str) -> object:
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content))],
        usage=None,
    )


def _usage_chunk() -> object:
    return SimpleNamespace(choices=[], usage=_Usage())


def _nonstream_response(content: str) -> object:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
        usage=_Usage(),
    )


class StructuredOutputStreamTest(unittest.IsolatedAsyncioTestCase):
    async def _invoke(self, create: AsyncMock, *, stream: bool = False) -> tuple[object, MagicMock, MagicMock]:
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create),
            ),
        )
        http_client = SimpleNamespace(aclose=AsyncMock())
        create_client = MagicMock(return_value=(client, http_client))
        accumulate_usage = MagicMock()

        with (
            patch.object(llm_client, "ensure_runtime_context_ready", new=AsyncMock()),
            patch.object(llm_client, "_create_openai_client", create_client),
            patch.object(llm_client, "get_llm_semaphore", return_value=asyncio.Semaphore(1)),
            patch.object(llm_client, "get_http_semaphore", return_value=asyncio.Semaphore(1)),
            patch.object(llm_client, "get_current_langchain_callbacks", return_value=None),
            patch.object(llm_client, "accumulate_usage", accumulate_usage),
        ):
            result = await llm_client.invoke_llm_structured_output(
                output_schema=_StructuredOutput,
                messages=[{"role": "user", "content": "return json"}],
                model_name="test-model",
                stream=stream,
            )

        return result, create_client, accumulate_usage

    async def test_nonstream_keeps_existing_request_shape(self) -> None:
        create = AsyncMock(return_value=_nonstream_response('{"value":11}'))

        result, _, _ = await self._invoke(create)

        self.assertEqual(result.result.value, 11)
        self.assertNotIn("stream", create.await_args.kwargs)
        self.assertNotIn("stream_options", create.await_args.kwargs)

    async def test_stream_combines_json_chunks_and_collects_usage(self) -> None:
        create = AsyncMock(
            return_value=_FakeStream(
                [
                    _content_chunk('{"val'),
                    _content_chunk('ue":12}'),
                    _usage_chunk(),
                ],
            ),
        )

        result, _, accumulate_usage = await self._invoke(create, stream=True)

        self.assertEqual(result.result.value, 12)
        self.assertIsNotNone(result.usage)
        self.assertEqual(result.usage.total_tokens, 11)
        self.assertIs(create.await_args.kwargs["stream"], True)
        self.assertEqual(create.await_args.kwargs["stream_options"], {"include_usage": True})
        accumulate_usage.assert_called_once_with(result.usage)

    async def test_interpret_llm_calls_use_shared_settings(self) -> None:
        calls: list[dict[str, object]] = []

        async def fake_invoke_llm_structured_output(**kwargs: object) -> object:
            calls.append(kwargs)
            output_schema = kwargs["output_schema"]
            if output_schema is nodes.si_prompt.ScenarioComparisonLLMOutput:
                result = output_schema(
                    identity="identity",
                    driver_phase="driver",
                    price_character="price",
                    summary="summary",
                )
            else:
                result = output_schema(overall_message="overall")
            return SimpleNamespace(result=result)

        fake_llm_client = ModuleType("apps.connectors.llm.llm_client")
        fake_llm_client.invoke_llm_structured_output = fake_invoke_llm_structured_output

        settings = SimpleNamespace(llm_stream_enabled=False, llm_reasoning_effort="high")
        with (
            patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_llm_client}),
            patch.object(nodes, "get_settings", return_value=settings),
        ):
            await nodes._interpret_one("305", ScenarioDiffBundle(scenario_id="305"))
            await nodes.synthesize_group(
                InterpretPriceState(
                    interpretations=[
                        ScenarioComparisonOut(
                            scenario_id="305",
                            identity="identity",
                            driver_phase="driver",
                            price_character="price",
                            summary="summary",
                        ),
                    ],
                ),
            )

        self.assertEqual([call["stream"] for call in calls], [False, False])
        self.assertEqual([call["reasoning_effort"] for call in calls], ["high", "high"])


if __name__ == "__main__":
    unittest.main()
