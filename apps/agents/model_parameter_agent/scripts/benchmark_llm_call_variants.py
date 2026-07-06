from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel


ROOT_DIR = Path(__file__).resolve().parents[4]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))
DEFAULT_APP_CONFIG = ROOT_DIR / "envs" / "config.yaml"
DEFAULT_DOTENV = ROOT_DIR / "envs" / ".env"
if DEFAULT_DOTENV.exists():
    from dotenv import load_dotenv

    load_dotenv(DEFAULT_DOTENV, override=False)
if "APP_CONFIG" not in os.environ and DEFAULT_APP_CONFIG.exists():
    os.environ["APP_CONFIG"] = str(DEFAULT_APP_CONFIG)

from apps.agents.model_parameter_agent.flows.propose_parameters import nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.api_schema import (
    LLMCandidateValidationResponse,
    LLMSlotProposalResponse,
    LLMValueProposalResponse,
)
from apps.agents.model_parameter_agent.scripts.evaluate_proposals import (
    _evaluate_scenario,
)
from apps.common.configs.config import get_settings
from apps.common.runtime.runtime import (
    ensure_runtime_context_ready,
    get_http_semaphore,
    get_llm_semaphore,
)
from apps.common.runtime.usage_context import accumulate_usage
from apps.common.values.enums import ModelPreference
from apps.common.values.llm_usage import LLMUsageModel
from apps.connectors.llm.llm_client import (
    LLMStructuredResult,
    _create_openai_client,
    _resolve_model_name,
)


REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
STEP_NAMES = {
    LLMCandidateValidationResponse: "Step1.5 candidate validation",
    LLMSlotProposalResponse: "Step2 slot proposal",
    LLMValueProposalResponse: "Step3 value proposal",
}
SCHEMA_BY_STEP = {step: schema for schema, step in STEP_NAMES.items()}
SENSITIVE_HEADER_PARTS = (
    "authorization",
    "api-key",
    "cookie",
    "set-cookie",
    "token",
    "secret",
    "key",
)

ApiKind = Literal["chat", "responses"]
StreamMode = Literal["nonstream", "stream"]


@dataclass(frozen=True)
class Variant:
    name: str
    api: ApiKind
    stream: StreamMode
    reasoning: str | None
    cache_key: bool


DEFAULT_VARIANTS: tuple[Variant, ...] = (
    Variant("chat_nonstream_default_no_cache_key", "chat", "nonstream", None, False),
    Variant("chat_stream_default_no_cache_key", "chat", "stream", None, False),
    Variant("chat_nonstream_reasoning_none_cache_key", "chat", "nonstream", "none", True),
    Variant("chat_nonstream_reasoning_low_cache_key", "chat", "nonstream", "low", True),
    Variant("chat_stream_reasoning_none_cache_key", "chat", "stream", "none", True),
    Variant("responses_nonstream_default_no_cache_key", "responses", "nonstream", None, False),
    Variant("responses_nonstream_reasoning_none_cache_key", "responses", "nonstream", "none", True),
    Variant("responses_stream_reasoning_none_cache_key", "responses", "stream", "none", True),
)


def _json_default(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return str(value)


def _model_dump(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value


def _redact_headers(headers: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in dict(headers).items():
        lowered = str(key).lower()
        if any(part in lowered for part in SENSITIVE_HEADER_PARTS):
            result[str(key)] = "<redacted>"
        else:
            result[str(key)] = str(value)
    return result


def _normalize_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "role": str(message.get("role") or "user"),
            "content": str(message.get("content") or ""),
        }
        for message in messages
    ]


def _response_text_config(output_schema: type[BaseModel]) -> dict[str, Any]:
    return {
        "format": {
            "type": "json_schema",
            "name": output_schema.__name__,
            "schema": output_schema.model_json_schema(),
            "strict": False,
        },
    }


def _chat_response_format(output_schema: type[BaseModel]) -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": output_schema.__name__,
            "schema": output_schema.model_json_schema(),
            "strict": False,
        },
    }


def _responses_prompt(messages: list[dict[str, str]]) -> tuple[str | None, Any]:
    normalized = _normalize_messages(messages)
    system_parts = [item["content"] for item in normalized if item["role"] == "system"]
    instructions = "\n\n".join(part for part in system_parts if part) or None
    input_items = [
        {
            "role": item["role"] if item["role"] != "system" else "developer",
            "content": item["content"],
        }
        for item in normalized
        if item["role"] != "system"
    ]
    if len(input_items) == 1 and input_items[0]["role"] == "user":
        return instructions, input_items[0]["content"]
    return instructions, input_items


def _usage_summary(usage: dict[str, Any] | None) -> dict[str, Any]:
    usage = usage or {}
    prompt_details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
    completion_details = (
        usage.get("completion_tokens_details")
        or usage.get("output_tokens_details")
        or {}
    )
    return {
        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "total_tokens": usage.get("total_tokens"),
        "cached_tokens": prompt_details.get("cached_tokens"),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "latency_checkpoint": usage.get("latency_checkpoint"),
    }


def _mean(values: list[float]) -> float | None:
    if not values:
        return None
    return round(statistics.mean(values), 3)


def _sum_numbers(values: list[Any]) -> int:
    total = 0
    for value in values:
        if isinstance(value, int | float):
            total += int(value)
    return total


def _format_seconds(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.3f}"


def _format_int(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)


async def _capture_scenario_prompts(
    scenario_id: int,
    *,
    max_candidates: int,
    max_retries: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    captured: list[dict[str, Any]] = []

    async def capture_invoke_structured(
        *,
        output_schema: type[Any],
        messages: list[dict[str, str]],
        model_name: str | None,
    ) -> Any:
        await ensure_runtime_context_ready()
        client, http_client = _create_openai_client(max_retries=max_retries)
        model = _resolve_model_name(model_name, ModelPreference.QUALITY)
        step = STEP_NAMES.get(output_schema, output_schema.__name__)
        started = time.perf_counter()
        try:
            async with get_llm_semaphore(), get_http_semaphore():
                raw_response = await client.chat.completions.with_raw_response.create(
                    model=model,
                    messages=messages,
                    response_format=_chat_response_format(output_schema),
                )
                parsed_response = raw_response.parse()
            elapsed = round(time.perf_counter() - started, 3)
            content = parsed_response.choices[0].message.content
            parsed_result = output_schema.model_validate_json(content)
            usage = (
                LLMUsageModel.model_validate(parsed_response.usage.model_dump())
                if parsed_response.usage
                else None
            )
            accumulate_usage(usage)
            usage_json = usage.model_dump(mode="json") if usage else None
            captured.append(
                {
                    "scenario_id": scenario_id,
                    "step": step,
                    "schema_name": output_schema.__name__,
                    "messages": _normalize_messages(messages),
                    "capture_call": {
                        "variant": "chat_nonstream_default_no_cache_key",
                        "elapsed_seconds": elapsed,
                        "status_code": raw_response.status_code,
                        "headers": _redact_headers(raw_response.headers),
                        "usage": usage_json,
                        "usage_summary": _usage_summary(usage_json),
                    },
                },
            )
            print(
                "CAPTURED_PROMPT",
                f"scenario={scenario_id}",
                f"step={step}",
                f"elapsed={elapsed}",
                f"total_tokens={_usage_summary(usage_json).get('total_tokens')}",
                flush=True,
            )
            return LLMStructuredResult(result=parsed_result, usage=usage)
        finally:
            await http_client.aclose()

    original = nodes._invoke_structured
    nodes._invoke_structured = capture_invoke_structured
    try:
        result = await _evaluate_scenario(
            scenario_id,
            max_candidates=max_candidates,
            allow_llm_fallback=False,
        )
    finally:
        nodes._invoke_structured = original
    return result, captured


async def _invoke_chat_nonstream(
    *,
    output_schema: type[BaseModel],
    messages: list[dict[str, str]],
    variant: Variant,
    model: str,
    max_retries: int,
    cache_key_prefix: str,
) -> dict[str, Any]:
    client, http_client = _create_openai_client(max_retries=max_retries)
    started = time.perf_counter()
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "response_format": _chat_response_format(output_schema),
        }
        if variant.reasoning is not None:
            kwargs["reasoning_effort"] = variant.reasoning
        if variant.cache_key:
            kwargs["prompt_cache_key"] = cache_key_prefix
            kwargs["prompt_cache_retention"] = "24h"
        async with get_llm_semaphore(), get_http_semaphore():
            raw_response = await client.chat.completions.with_raw_response.create(**kwargs)
            response = raw_response.parse()
        elapsed = round(time.perf_counter() - started, 3)
        content = response.choices[0].message.content
        parsed = output_schema.model_validate_json(content)
        usage = _model_dump(response.usage)
        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "ttft_seconds": None,
            "content_chars": len(content or ""),
            "parsed_type": parsed.__class__.__name__,
            "structured_result_json": parsed.model_dump(mode="json"),
            "usage": usage,
            "usage_summary": _usage_summary(usage),
            "http_meta": {
                "status_code": raw_response.status_code,
                "headers": _redact_headers(raw_response.headers),
            },
            "finish_reason": response.choices[0].finish_reason,
        }
    finally:
        await http_client.aclose()


async def _invoke_chat_stream(
    *,
    output_schema: type[BaseModel],
    messages: list[dict[str, str]],
    variant: Variant,
    model: str,
    max_retries: int,
    cache_key_prefix: str,
) -> dict[str, Any]:
    client, http_client = _create_openai_client(max_retries=max_retries)
    started = time.perf_counter()
    first_delta_at: float | None = None
    try:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "response_format": _chat_response_format(output_schema),
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if variant.reasoning is not None:
            kwargs["reasoning_effort"] = variant.reasoning
        if variant.cache_key:
            kwargs["prompt_cache_key"] = cache_key_prefix
            kwargs["prompt_cache_retention"] = "24h"
        chunks: list[str] = []
        usage: dict[str, Any] | None = None
        finish_reason: str | None = None
        async with get_llm_semaphore(), get_http_semaphore():
            stream = await client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if getattr(chunk, "usage", None) is not None:
                    usage = chunk.usage.model_dump(mode="json")
                if not chunk.choices:
                    continue
                choice = chunk.choices[0]
                if choice.finish_reason:
                    finish_reason = choice.finish_reason
                delta = choice.delta.content or ""
                if delta:
                    if first_delta_at is None:
                        first_delta_at = time.perf_counter()
                    chunks.append(delta)
        elapsed = round(time.perf_counter() - started, 3)
        content = "".join(chunks)
        parsed = output_schema.model_validate_json(content)
        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "ttft_seconds": (
                round(first_delta_at - started, 3) if first_delta_at is not None else None
            ),
            "content_chars": len(content),
            "parsed_type": parsed.__class__.__name__,
            "structured_result_json": parsed.model_dump(mode="json"),
            "usage": usage,
            "usage_summary": _usage_summary(usage),
            "http_meta": None,
            "finish_reason": finish_reason,
        }
    finally:
        await http_client.aclose()


async def _invoke_responses_nonstream(
    *,
    output_schema: type[BaseModel],
    messages: list[dict[str, str]],
    variant: Variant,
    model: str,
    max_retries: int,
    cache_key_prefix: str,
) -> dict[str, Any]:
    client, http_client = _create_openai_client(max_retries=max_retries)
    started = time.perf_counter()
    try:
        instructions, response_input = _responses_prompt(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "input": response_input,
            "text": _response_text_config(output_schema),
        }
        if variant.reasoning is not None:
            kwargs["reasoning"] = {"effort": variant.reasoning}
        if variant.cache_key:
            kwargs["prompt_cache_key"] = cache_key_prefix
            kwargs["prompt_cache_retention"] = "24h"
        async with get_llm_semaphore(), get_http_semaphore():
            raw_response = await client.responses.with_raw_response.create(**kwargs)
            response = raw_response.parse()
        elapsed = round(time.perf_counter() - started, 3)
        content = getattr(response, "output_text", None) or ""
        parsed = output_schema.model_validate_json(content)
        usage = _model_dump(response.usage)
        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "ttft_seconds": None,
            "content_chars": len(content),
            "parsed_type": parsed.__class__.__name__,
            "structured_result_json": parsed.model_dump(mode="json"),
            "usage": usage,
            "usage_summary": _usage_summary(usage),
            "http_meta": {
                "status_code": raw_response.status_code,
                "headers": _redact_headers(raw_response.headers),
            },
            "finish_reason": None,
        }
    finally:
        await http_client.aclose()


async def _invoke_responses_stream(
    *,
    output_schema: type[BaseModel],
    messages: list[dict[str, str]],
    variant: Variant,
    model: str,
    max_retries: int,
    cache_key_prefix: str,
) -> dict[str, Any]:
    client, http_client = _create_openai_client(max_retries=max_retries)
    started = time.perf_counter()
    first_delta_at: float | None = None
    try:
        instructions, response_input = _responses_prompt(messages)
        kwargs: dict[str, Any] = {
            "model": model,
            "instructions": instructions,
            "input": response_input,
            "text": _response_text_config(output_schema),
            "stream": True,
        }
        if variant.reasoning is not None:
            kwargs["reasoning"] = {"effort": variant.reasoning}
        if variant.cache_key:
            kwargs["prompt_cache_key"] = cache_key_prefix
            kwargs["prompt_cache_retention"] = "24h"
        chunks: list[str] = []
        usage: dict[str, Any] | None = None
        event_types: set[str] = set()
        async with get_llm_semaphore(), get_http_semaphore():
            stream = await client.responses.create(**kwargs)
            async for event in stream:
                event_type = str(getattr(event, "type", ""))
                event_types.add(event_type)
                if event_type == "response.output_text.delta":
                    delta = str(getattr(event, "delta", "") or "")
                    if delta:
                        if first_delta_at is None:
                            first_delta_at = time.perf_counter()
                        chunks.append(delta)
                elif event_type == "response.completed":
                    completed = getattr(event, "response", None)
                    usage = _model_dump(getattr(completed, "usage", None))
        elapsed = round(time.perf_counter() - started, 3)
        content = "".join(chunks)
        parsed = output_schema.model_validate_json(content)
        return {
            "success": True,
            "elapsed_seconds": elapsed,
            "ttft_seconds": (
                round(first_delta_at - started, 3) if first_delta_at is not None else None
            ),
            "content_chars": len(content),
            "parsed_type": parsed.__class__.__name__,
            "structured_result_json": parsed.model_dump(mode="json"),
            "usage": usage,
            "usage_summary": _usage_summary(usage),
            "http_meta": None,
            "finish_reason": None,
            "stream_event_types": sorted(event_types),
        }
    finally:
        await http_client.aclose()


async def _invoke_variant(
    *,
    captured_step: dict[str, Any],
    variant: Variant,
    repeat_index: int,
    max_retries: int,
) -> dict[str, Any]:
    output_schema = SCHEMA_BY_STEP[captured_step["step"]]
    messages = captured_step["messages"]
    model = _resolve_model_name(None, ModelPreference.QUALITY)
    cache_key_prefix = (
        "model-parameter-agent:"
        f"{captured_step['step'].lower().replace(' ', '-').replace('.', '')}:"
        "benchmark-v1"
    )
    started_at = datetime.now().isoformat(timespec="seconds")
    try:
        await ensure_runtime_context_ready()
        if variant.api == "chat" and variant.stream == "nonstream":
            outcome = await _invoke_chat_nonstream(
                output_schema=output_schema,
                messages=messages,
                variant=variant,
                model=model,
                max_retries=max_retries,
                cache_key_prefix=cache_key_prefix,
            )
        elif variant.api == "chat" and variant.stream == "stream":
            outcome = await _invoke_chat_stream(
                output_schema=output_schema,
                messages=messages,
                variant=variant,
                model=model,
                max_retries=max_retries,
                cache_key_prefix=cache_key_prefix,
            )
        elif variant.api == "responses" and variant.stream == "nonstream":
            outcome = await _invoke_responses_nonstream(
                output_schema=output_schema,
                messages=messages,
                variant=variant,
                model=model,
                max_retries=max_retries,
                cache_key_prefix=cache_key_prefix,
            )
        else:
            outcome = await _invoke_responses_stream(
                output_schema=output_schema,
                messages=messages,
                variant=variant,
                model=model,
                max_retries=max_retries,
                cache_key_prefix=cache_key_prefix,
            )
        return {
            "scenario_id": captured_step["scenario_id"],
            "step": captured_step["step"],
            "variant": variant.name,
            "api": variant.api,
            "stream": variant.stream,
            "reasoning": variant.reasoning,
            "cache_key": variant.cache_key,
            "repeat_index": repeat_index,
            "started_at": started_at,
            **outcome,
        }
    except Exception as ex:
        return {
            "scenario_id": captured_step["scenario_id"],
            "step": captured_step["step"],
            "variant": variant.name,
            "api": variant.api,
            "stream": variant.stream,
            "reasoning": variant.reasoning,
            "cache_key": variant.cache_key,
            "repeat_index": repeat_index,
            "started_at": started_at,
            "success": False,
            "error_type": type(ex).__name__,
            "error": str(ex),
        }


def _summarize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault((record["variant"], record["step"]), []).append(record)

    rows: list[dict[str, Any]] = []
    for (variant, step), items in sorted(grouped.items()):
        successes = [item for item in items if item.get("success")]
        elapsed_values = [
            float(item["elapsed_seconds"])
            for item in successes
            if isinstance(item.get("elapsed_seconds"), int | float)
        ]
        ttft_values = [
            float(item["ttft_seconds"])
            for item in successes
            if isinstance(item.get("ttft_seconds"), int | float)
        ]
        usage_summaries = [item.get("usage_summary") or {} for item in successes]
        rows.append(
            {
                "variant": variant,
                "step": step,
                "count": len(items),
                "success_count": len(successes),
                "error_count": len(items) - len(successes),
                "avg_elapsed_seconds": _mean(elapsed_values),
                "min_elapsed_seconds": round(min(elapsed_values), 3) if elapsed_values else None,
                "max_elapsed_seconds": round(max(elapsed_values), 3) if elapsed_values else None,
                "avg_ttft_seconds": _mean(ttft_values),
                "total_cached_tokens": _sum_numbers(
                    [summary.get("cached_tokens") for summary in usage_summaries],
                ),
                "total_reasoning_tokens": _sum_numbers(
                    [summary.get("reasoning_tokens") for summary in usage_summaries],
                ),
                "avg_total_tokens": _mean(
                    [
                        float(summary["total_tokens"])
                        for summary in usage_summaries
                        if isinstance(summary.get("total_tokens"), int | float)
                    ],
                ),
            },
        )
    return rows


def _summarize_variants(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["variant"], []).append(record)
    rows: list[dict[str, Any]] = []
    for variant, items in sorted(grouped.items()):
        successes = [item for item in items if item.get("success")]
        elapsed_values = [
            float(item["elapsed_seconds"])
            for item in successes
            if isinstance(item.get("elapsed_seconds"), int | float)
        ]
        ttft_values = [
            float(item["ttft_seconds"])
            for item in successes
            if isinstance(item.get("ttft_seconds"), int | float)
        ]
        usage_summaries = [item.get("usage_summary") or {} for item in successes]
        rows.append(
            {
                "variant": variant,
                "count": len(items),
                "success_count": len(successes),
                "error_count": len(items) - len(successes),
                "avg_elapsed_seconds": _mean(elapsed_values),
                "avg_ttft_seconds": _mean(ttft_values),
                "total_cached_tokens": _sum_numbers(
                    [summary.get("cached_tokens") for summary in usage_summaries],
                ),
                "total_reasoning_tokens": _sum_numbers(
                    [summary.get("reasoning_tokens") for summary in usage_summaries],
                ),
                "avg_total_tokens": _mean(
                    [
                        float(summary["total_tokens"])
                        for summary in usage_summaries
                        if isinstance(summary.get("total_tokens"), int | float)
                    ],
                ),
            },
        )
    return rows


def _write_markdown_report(
    *,
    path: Path,
    metadata: dict[str, Any],
    scenario_results: list[dict[str, Any]],
    records: list[dict[str, Any]],
    by_variant: list[dict[str, Any]],
    by_variant_step: list[dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Model Parameter Agent LLM Call Variant Benchmark",
        "",
        f"- generated_at: `{metadata['generated_at']}`",
        f"- scenario_ids: `{metadata['scenario_ids']}`",
        f"- repeats: `{metadata['repeats']}`",
        f"- max_retries: `{metadata['max_retries']}`",
        f"- llm_timeout_sec: `{metadata['llm_timeout_sec']}`",
        f"- deployment_model: `{metadata['deployment_model']}`",
        "- note: 각 scenario의 실제 agent prompt를 먼저 캡처한 뒤, 같은 step prompt를 각 조합에 반복 호출해 비교했습니다.",
        "- note: cache off가 아니라 cache_key 미지정입니다. Azure prompt caching 자체는 opt-out이 없습니다.",
        "",
        "## Scenario Capture",
        "",
        "| scenario_id | status | proposal_id | prompt_steps | final_parameter_count |",
        "|---:|---|---:|---:|---:|",
    ]
    for result in scenario_results:
        final_response = result.get("final_response") or {}
        data = final_response.get("data") or {}
        lines.append(
            "| {scenario_id} | {status} | {proposal_id} | {prompt_steps} | {param_count} |".format(
                scenario_id=result.get("scenario_id"),
                status=final_response.get("status"),
                proposal_id=data.get("modelParamProposalId", ""),
                prompt_steps=len(result.get("captured_steps") or []),
                param_count=len(data.get("proposalParameters") or []),
            ),
        )

    lines.extend(
        [
            "",
            "## Variant Summary",
            "",
            "| variant | calls | success | errors | avg_elapsed_s | avg_ttft_s | avg_total_tokens | total_cached_tokens | total_reasoning_tokens |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ],
    )
    for row in by_variant:
        lines.append(
            "| {variant} | {count} | {success_count} | {error_count} | {elapsed} | {ttft} | {tokens} | {cached} | {reasoning} |".format(
                variant=row["variant"],
                count=row["count"],
                success_count=row["success_count"],
                error_count=row["error_count"],
                elapsed=_format_seconds(row.get("avg_elapsed_seconds")),
                ttft=_format_seconds(row.get("avg_ttft_seconds")),
                tokens=_format_seconds(row.get("avg_total_tokens")),
                cached=_format_int(row.get("total_cached_tokens")),
                reasoning=_format_int(row.get("total_reasoning_tokens")),
            ),
        )

    lines.extend(
        [
            "",
            "## Variant Step Summary",
            "",
            "| variant | step | calls | success | errors | avg_elapsed_s | min_s | max_s | avg_ttft_s | avg_total_tokens | total_cached_tokens | total_reasoning_tokens |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ],
    )
    for row in by_variant_step:
        lines.append(
            "| {variant} | {step} | {count} | {success_count} | {error_count} | {elapsed} | {min_elapsed} | {max_elapsed} | {ttft} | {tokens} | {cached} | {reasoning} |".format(
                variant=row["variant"],
                step=row["step"],
                count=row["count"],
                success_count=row["success_count"],
                error_count=row["error_count"],
                elapsed=_format_seconds(row.get("avg_elapsed_seconds")),
                min_elapsed=_format_seconds(row.get("min_elapsed_seconds")),
                max_elapsed=_format_seconds(row.get("max_elapsed_seconds")),
                ttft=_format_seconds(row.get("avg_ttft_seconds")),
                tokens=_format_seconds(row.get("avg_total_tokens")),
                cached=_format_int(row.get("total_cached_tokens")),
                reasoning=_format_int(row.get("total_reasoning_tokens")),
            ),
        )

    errors = [record for record in records if not record.get("success")]
    lines.extend(["", "## Errors", ""])
    if not errors:
        lines.append("- none")
    else:
        for record in errors:
            lines.append(
                "- scenario={scenario_id}, step={step}, variant={variant}, repeat={repeat}: {error_type} {error}".format(
                    scenario_id=record.get("scenario_id"),
                    step=record.get("step"),
                    variant=record.get("variant"),
                    repeat=record.get("repeat_index"),
                    error_type=record.get("error_type"),
                    error=str(record.get("error") or "")[:500],
                ),
            )

    lines.extend(
        [
            "",
            "## Raw Record Fields",
            "",
            "- 전체 raw 결과는 같은 basename의 `.json` 파일에 저장했습니다.",
            "- 주요 필드: `elapsed_seconds`, `ttft_seconds`, `usage_summary.cached_tokens`, `usage_summary.reasoning_tokens`, `usage_summary.latency_checkpoint`.",
        ],
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_benchmark(args: argparse.Namespace) -> tuple[Path, Path]:
    settings = get_settings()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    partial_path = REPORT_DIR / f"model_parameter_llm_call_variant_benchmark_{generated_at}.partial.json"
    scenario_ids = tuple(int(item) for item in args.scenario_ids)
    variants = DEFAULT_VARIANTS

    scenario_results: list[dict[str, Any]] = []
    captured_steps: list[dict[str, Any]] = []
    for scenario_id in scenario_ids:
        result, steps = await _capture_scenario_prompts(
            scenario_id,
            max_candidates=args.max_candidates,
            max_retries=args.max_retries,
        )
        result_record = {
            "scenario_id": scenario_id,
            "final_response": result.get("final_response"),
            "step_summary": result.get("step_summary"),
            "captured_steps": [
                {
                    "step": step["step"],
                    "schema_name": step["schema_name"],
                    "message_char_counts": [
                        len(message.get("content") or "")
                        for message in step.get("messages") or []
                    ],
                    "capture_call": step.get("capture_call"),
                }
                for step in steps
            ],
        }
        scenario_results.append(result_record)
        captured_steps.extend(steps)

    records: list[dict[str, Any]] = []
    for repeat_index in range(1, args.repeats + 1):
        for variant in variants:
            for step in captured_steps:
                started = time.perf_counter()
                record = await _invoke_variant(
                    captured_step=step,
                    variant=variant,
                    repeat_index=repeat_index,
                    max_retries=args.max_retries,
                )
                records.append(record)
                partial_path.write_text(
                    json.dumps(
                        {
                            "generated_at": generated_at,
                            "scenario_ids": list(scenario_ids),
                            "repeats": args.repeats,
                            "records": records,
                        },
                        ensure_ascii=False,
                        indent=2,
                        default=_json_default,
                    ),
                    encoding="utf-8",
                )
                summary = record.get("usage_summary") or {}
                print(
                    "BENCHMARK_CALL",
                    f"repeat={repeat_index}",
                    f"scenario={record.get('scenario_id')}",
                    f"step={record.get('step')}",
                    f"variant={variant.name}",
                    f"success={record.get('success')}",
                    f"elapsed={record.get('elapsed_seconds')}",
                    f"ttft={record.get('ttft_seconds')}",
                    f"cached={summary.get('cached_tokens')}",
                    f"reasoning={summary.get('reasoning_tokens')}",
                    f"total_tokens={summary.get('total_tokens')}",
                    f"wall={round(time.perf_counter() - started, 3)}",
                    flush=True,
                )

    by_variant = _summarize_variants(records)
    by_variant_step = _summarize_records(records)
    metadata = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scenario_ids": list(scenario_ids),
        "repeats": args.repeats,
        "max_candidates": args.max_candidates,
        "max_retries": args.max_retries,
        "llm_timeout_sec": settings.llm_timeout_sec,
        "model_endpoint": settings.model_endpoint,
        "deployment_model": _resolve_model_name(None, ModelPreference.QUALITY),
        "variants": [variant.__dict__ for variant in variants],
    }
    report = {
        "metadata": metadata,
        "scenario_results": scenario_results,
        "records": records,
        "summary_by_variant": by_variant,
        "summary_by_variant_step": by_variant_step,
    }
    json_path = REPORT_DIR / f"model_parameter_llm_call_variant_benchmark_{generated_at}.json"
    md_path = REPORT_DIR / f"model_parameter_llm_call_variant_benchmark_{generated_at}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=_json_default),
        encoding="utf-8",
    )
    _write_markdown_report(
        path=md_path,
        metadata=metadata,
        scenario_results=scenario_results,
        records=records,
        by_variant=by_variant,
        by_variant_step=by_variant_step,
    )
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark model_parameter_agent LLM call API/stream/reasoning/cache variants.",
    )
    parser.add_argument("--scenario-ids", nargs="+", type=int, default=[129, 130])
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--max-retries", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    json_path, md_path = asyncio.run(run_benchmark(parse_args()))
    print(f"JSON_REPORT {json_path}")
    print(f"MD_REPORT {md_path}")


if __name__ == "__main__":
    main()
