# ruff: noqa: S101

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import os
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import BaseModel, ValidationError
import pytest

from apps.common.exceptions.custom import MIBaseError


os.environ.setdefault("METADATA_DB_PORT", "3306")

from apps.connectors.llm import llm_client


class _StructuredOutput(BaseModel):
    value: int


class _Usage:
    def __init__(self, *, prompt_tokens: int = 3, completion_tokens: int = 2) -> None:
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def model_dump(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.prompt_tokens + self.completion_tokens,
        }


class _FakeStream:
    def __init__(self, chunks: list[object], *, final_error: Exception | None = None) -> None:
        self._chunks = chunks
        self._final_error = final_error

    def __aiter__(self) -> AsyncIterator[object]:
        return self._iterate()

    async def _iterate(self) -> AsyncIterator[object]:
        for chunk in self._chunks:
            yield chunk
        if self._final_error is not None:
            raise self._final_error


class _FakeStrictStream:
    def __init__(self, response: object) -> None:
        self._response = response

    async def __aenter__(self) -> _FakeStrictStream:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def get_final_completion(self) -> object:
        return self._response


def _content_chunk(content: str) -> object:
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=SimpleNamespace(content=content))],
        usage=None,
    )


def _usage_chunk(usage: _Usage) -> object:
    return SimpleNamespace(choices=[], usage=usage)


def _nonstream_response(
    content: str | None,
    usage: _Usage | None = None,
    *,
    parsed: BaseModel | None = None,
    refusal: str | None = None,
) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    parsed=parsed,
                    refusal=refusal,
                ),
            ),
        ],
        usage=usage,
    )


class StructuredOutputConnectorTest(unittest.IsolatedAsyncioTestCase):
    async def _invoke(
        self,
        create: AsyncMock,
        *,
        output_schema: type[BaseModel] = _StructuredOutput,
        parse: AsyncMock | None = None,
        strict_stream: MagicMock | None = None,
        stream: bool = False,
        reasoning_effort: llm_client.ReasoningEffortOption | None = None,
        max_retries: int = 2,
        strict: bool = False,
    ) -> tuple[
        llm_client.LLMStructuredResult[BaseModel],
        MagicMock,
        MagicMock,
        AsyncMock,
    ]:
        parse = parse or AsyncMock()
        strict_stream = strict_stream or MagicMock()
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=create,
                    parse=parse,
                    stream=strict_stream,
                ),
            ),
        )
        close = AsyncMock()
        http_client = SimpleNamespace(aclose=close)
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
                return_value=SimpleNamespace(llm_structured_output_strict=strict),
            ),
        ):
            result = await llm_client.invoke_llm_structured_output(
                output_schema=output_schema,
                messages=[{"role": "user", "content": "return json"}],
                model_name="test-model",
                max_retries=max_retries,
                stream=stream,
                reasoning_effort=reasoning_effort,
            )

        return result, create_client, accumulate_usage, close

    async def test_strict_nonstream_uses_sdk_parse_with_same_pydantic_schema(self) -> None:
        create = AsyncMock()
        parsed = _StructuredOutput(value=10)
        parse = AsyncMock(
            return_value=_nonstream_response(
                '{"value":10}',
                _Usage(),
                parsed=parsed,
            ),
        )

        result, _, _, _ = await self._invoke(
            create,
            parse=parse,
            strict=True,
        )

        assert result.result is parsed
        assert parse.await_args.kwargs["response_format"] is _StructuredOutput
        assert "stream" not in parse.await_args.kwargs
        create.assert_not_awaited()

    async def test_pydantic_validation_error_is_classified_as_invalid_response(self) -> None:
        create = AsyncMock()
        with pytest.raises(ValidationError) as caught:
            _StructuredOutput.model_validate({"value": "not-an-integer"})
        parse = AsyncMock(side_effect=caught.value)

        with pytest.raises(MIBaseError) as error:
            await self._invoke(
                create,
                parse=parse,
                strict=True,
            )

        assert error.value.error_code is llm_client.ErrorCode.LLM_INVALID_RESPONSE_ERROR
        create.assert_not_awaited()

    async def test_strict_stream_uses_sdk_parser_without_raw_stream_flag(self) -> None:
        create = AsyncMock()
        parse = AsyncMock()
        parsed = _StructuredOutput(value=19)
        strict_stream = MagicMock(
            return_value=_FakeStrictStream(
                _nonstream_response(
                    '{"value":19}',
                    _Usage(),
                    parsed=parsed,
                ),
            ),
        )

        result, _, _, _ = await self._invoke(
            create,
            parse=parse,
            strict_stream=strict_stream,
            stream=True,
            strict=True,
        )

        assert result.result is parsed
        request = strict_stream.call_args.kwargs
        assert request["response_format"] is _StructuredOutput
        assert request["stream_options"] == {"include_usage": True}
        assert "stream" not in request
        create.assert_not_awaited()
        parse.assert_not_awaited()

    async def test_nonstream_returns_parsed_result_and_usage_without_stream_options(self) -> None:
        create = AsyncMock(return_value=_nonstream_response('{"value":11}', _Usage()))

        result, create_client, accumulate_usage, close = await self._invoke(create)

        assert result.result.value == 11
        assert result.model == "test-model"
        assert result.usage is not None
        assert result.usage.total_tokens == 5
        request = create.await_args.kwargs
        assert "stream" not in request
        assert "stream_options" not in request
        assert "reasoning_effort" not in request
        assert request["response_format"]["json_schema"]["strict"] is False
        create_client.assert_called_once_with(max_retries=2)
        accumulate_usage.assert_called_once_with(result.usage)
        close.assert_awaited_once()

    async def test_stream_combines_content_and_collects_usage_only_chunk(self) -> None:
        create = AsyncMock(
            return_value=_FakeStream(
                [
                    _content_chunk('{"val'),
                    _content_chunk('ue":12}'),
                    _usage_chunk(_Usage(prompt_tokens=7, completion_tokens=4)),
                ],
            ),
        )

        result, create_client, accumulate_usage, close = await self._invoke(create, stream=True)

        assert result.result.value == 12
        assert result.usage is not None
        assert result.usage.total_tokens == 11
        request = create.await_args.kwargs
        assert request["stream"] is True
        assert request["stream_options"] == {"include_usage": True}
        create_client.assert_called_once_with(max_retries=0)
        accumulate_usage.assert_called_once_with(result.usage)
        close.assert_awaited_once()

    async def test_stream_keeps_nullable_usage_when_provider_omits_it(self) -> None:
        create = AsyncMock(return_value=_FakeStream([_content_chunk('{"value":13}')]))

        result, _, accumulate_usage, _ = await self._invoke(create, stream=True)

        assert result.result.value == 13
        assert result.usage is None
        accumulate_usage.assert_called_once_with(None)

    async def test_empty_stream_retries_complete_request_then_fails(self) -> None:
        create = AsyncMock(side_effect=[_FakeStream([]), _FakeStream([])])

        with pytest.raises(MIBaseError) as error:
            await self._invoke(create, stream=True, max_retries=1)

        assert "content" in str(error.value)
        assert create.await_count == 2

    async def test_interrupted_stream_retries_with_fresh_content_buffer(self) -> None:
        create = AsyncMock(
            side_effect=[
                _FakeStream(
                    [_content_chunk('{"value":999')],
                    final_error=ConnectionError("stream interrupted"),
                ),
                _FakeStream([_content_chunk('{"value":14}')]),
            ],
        )

        result, _, _, _ = await self._invoke(create, stream=True, max_retries=1)

        assert result.result.value == 14
        assert create.await_count == 2

    async def test_partial_json_retries_complete_stream(self) -> None:
        create = AsyncMock(
            side_effect=[
                _FakeStream([_content_chunk('{"value":')]),
                _FakeStream([_content_chunk('{"value":15}')]),
            ],
        )

        result, _, _, _ = await self._invoke(create, stream=True, max_retries=1)

        assert result.result.value == 15
        assert create.await_count == 2

    async def test_stream_schema_validation_is_not_retried_by_connector(self) -> None:
        create = AsyncMock(
            return_value=_FakeStream(
                [_content_chunk('{"value":"not-an-integer"}')],
            ),
        )

        with pytest.raises(MIBaseError) as error:
            await self._invoke(create, stream=True, max_retries=2)

        assert error.value.error_code is llm_client.ErrorCode.LLM_INVALID_RESPONSE_ERROR
        assert create.await_count == 1

    async def test_reasoning_default_and_none_omit_request_key(self) -> None:
        for reasoning_effort in (None, "default"):
            with self.subTest(reasoning_effort=reasoning_effort):
                create = AsyncMock(return_value=_nonstream_response('{"value":16}'))

                await self._invoke(create, reasoning_effort=reasoning_effort)

                assert "reasoning_effort" not in create.await_args.kwargs

    async def test_supported_reasoning_values_are_forwarded_unchanged(self) -> None:
        supported_values: tuple[llm_client.ReasoningEffortOption, ...] = (
            "none",
            "minimal",
            "low",
            "medium",
            "high",
            "xhigh",
        )
        for reasoning_effort in supported_values:
            with self.subTest(reasoning_effort=reasoning_effort):
                create = AsyncMock(return_value=_nonstream_response('{"value":17}'))

                await self._invoke(create, reasoning_effort=reasoning_effort)

                assert create.await_args.kwargs["reasoning_effort"] == reasoning_effort

    async def test_reasoning_is_forwarded_in_stream_mode(self) -> None:
        create = AsyncMock(return_value=_FakeStream([_content_chunk('{"value":18}')]))

        await self._invoke(create, stream=True, reasoning_effort="low")

        assert create.await_args.kwargs["reasoning_effort"] == "low"
        assert create.await_args.kwargs["stream"] is True

    async def test_provider_reasoning_rejection_is_not_retried_without_value(self) -> None:
        create = AsyncMock(side_effect=RuntimeError("reasoning effort unsupported"))

        with pytest.raises(MIBaseError) as error:
            await self._invoke(
                create,
                stream=True,
                reasoning_effort="xhigh",
                max_retries=1,
            )

        assert "reasoning effort unsupported" in str(error.value)
        assert create.await_count == 2
        for call in create.await_args_list:
            assert call.kwargs.get("reasoning_effort") == "xhigh"


if __name__ == "__main__":
    unittest.main()
