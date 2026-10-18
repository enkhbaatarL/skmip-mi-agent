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
            patch.object(
                llm_client,
                "get_settings",
                return_value=SimpleNamespace(llm_structured_output_strict=False),
            ),
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


class _DelayedStream:
    """각 조각 앞에 지정한 시간만큼 기다리는 가짜 스트림."""

    def __init__(self, delayed_chunks: list[tuple[float, object]]) -> None:
        self._delayed_chunks = delayed_chunks

    def __aiter__(self) -> AsyncIterator[object]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[object]:
        for delay, chunk in self._delayed_chunks:
            await asyncio.sleep(delay)
            yield chunk


class StreamStallLimitsTest(unittest.IsolatedAsyncioTestCase):
    async def _request(
        self,
        stream: _DelayedStream,
        limits: llm_client.StreamStallLimits | None,
    ) -> tuple[str, BaseModel, object]:
        return await llm_client._request_structured_output_stream(
            create=AsyncMock(return_value=stream),
            output_schema=_StructuredOutput,
            request_kwargs={},
            retries_remaining=0,
            stall_limits=limits,
            log_label="test",
        )

    async def test_steady_chunks_are_not_cut_even_when_total_time_exceeds_the_idle_limit(self) -> None:
        stream = _DelayedStream(
            [(0.03, _content_chunk('{"val')), (0.03, _content_chunk('ue":')), (0.03, _content_chunk("1}"))],
        )

        _content, parsed, _usage = await self._request(
            stream,
            llm_client.StreamStallLimits(first_chunk_sec=0.5, idle_sec=0.05),
        )

        assert parsed.value == 1

    async def test_missing_first_chunk_is_reported_as_a_stalled_stream(self) -> None:
        stream = _DelayedStream([(0.3, _content_chunk('{"value":1}'))])

        with self.assertRaisesRegex(llm_client.LLMStreamStalledError, "first chunk not received within 0.05s"):
            await self._request(stream, llm_client.StreamStallLimits(first_chunk_sec=0.05))

    async def test_gap_between_chunks_is_reported_as_a_stalled_stream(self) -> None:
        stream = _DelayedStream([(0.0, _content_chunk('{"value":')), (0.3, _content_chunk("1}"))])

        with self.assertRaisesRegex(llm_client.LLMStreamStalledError, "no chunk for 0.05s after 1 chunks"):
            await self._request(stream, llm_client.StreamStallLimits(idle_sec=0.05))

    async def test_without_limits_a_slow_stream_completes(self) -> None:
        stream = _DelayedStream([(0.1, _content_chunk('{"value":')), (0.1, _content_chunk("2}"))])

        _content, parsed, _usage = await self._request(stream, None)

        assert parsed.value == 2



def test_stream_timing_reports_first_content_separately_from_first_chunk() -> None:
    timing = llm_client._StreamTiming(started_at=0.0)
    with patch.object(llm_client.time, "monotonic", side_effect=[1.0, 3.0, 10.0]):
        timing.record_chunk(has_content=False)
        timing.record_chunk(has_content=True)
        summary = timing.summary()

    assert summary == (
        "first_chunk_sec=1.0 | first_content_sec=3.0 | max_gap_sec=2.0 | chunks=2 | total_sec=10.0"
    )
