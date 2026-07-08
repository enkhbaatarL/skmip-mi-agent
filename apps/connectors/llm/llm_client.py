#   apps/connectors/llm/llm_client.py
#   kmj20260423목,    주석문 추가
"""LLM 호출 공통 클라이언트 모듈.

역할:
- 외부 LLM API(A.X Platform Gateway)를 호출하는 공통 인터페이스를 제공한다.
- 단순 텍스트 응답 호출과 structured output(JSON 기반) 호출을 모두 지원한다.
- 모델 선택(속도/품질), 타임아웃, 동시성 제어 등을 일관된 방식으로 처리한다.

주요 기능:
- invoke_llm: 일반 텍스트 기반 LLM 호출
- invoke_llm_structured_output: Pydantic 스키마 기반 structured output 호출
- 모델 선택 로직 (ModelPreference 기반)
- LLM 사용량(토큰) 추적 및 누적 (usage_context 연동)

입력:
- 프롬프트 (system/user)
- 모델 선호도 (speed / quality)
- 출력 스키마 (structured output 시)
- 기타 LLM 호출 옵션

출력:
- 텍스트 응답 또는 구조화된 객체 (Pydantic model)

설계 의도:
- 서비스 계층에서 LLM 호출 로직을 직접 구현하지 않도록 추상화
- 다양한 LLM 호출 패턴(텍스트/구조화)을 하나의 인터페이스로 통합
- 향후 모델 교체, 멀티 모델 전략, fallback 전략 등을 쉽게 확장 가능
- 공통 로깅, 에러 처리, 타임아웃, 세마포어 제어를 중앙에서 관리

아키텍처 위치:
- connectors 계층에 위치하여 외부 LLM API와 직접 통신
- services → llm_client → 외부 LLM 구조로 의존성 방향 유지
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import asynccontextmanager, contextmanager, nullcontext
from inspect import isawaitable
from typing import Any, TypeVar

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, LLMResult
from openai import AsyncOpenAI
from pydantic import BaseModel

from apps.common.configs.config import BaseSettings, get_settings
from apps.common.exceptions.custom import MIBaseError
from apps.common.logging.decorators import log_connector
from apps.common.logging.logger_config import logger
from apps.common.runtime.runtime import (
    ensure_runtime_context_ready,
    get_http_semaphore,
    get_llm_semaphore,
)
from apps.common.runtime.usage_context import accumulate_usage
from apps.common.tracing.context import TraceContext, build_aip_headers, get_current_langchain_callbacks
from apps.common.values.enums import ModelPreference
from apps.common.values.error_codes import ErrorCode
from apps.common.values.llm_usage import LLMUsageModel


T = TypeVar("T", bound=BaseModel)


class _LLMTraceRun:
    def __init__(
        self,
        *,
        mlflow_span: object | None = None,
        langchain_run_manager: object | None = None,
        openai_span: object | None = None,
    ) -> None:
        self.mlflow_span = mlflow_span
        self.langchain_run_manager = langchain_run_manager
        self.openai_span = openai_span
        self.completed = False


class LLMStructuredResult[T: BaseModel](BaseModel):
    """Structured output 결과와 usage 정보를 함께 반환하는 모델."""

    result: T
    usage: LLMUsageModel | None = None
    model: str | None = None


def _create_openai_client(max_retries: int) -> tuple[AsyncOpenAI, httpx.AsyncClient]:
    cfg = get_settings()
    http_client = httpx.AsyncClient(
        verify=cfg.http_verify,
        http2=cfg.http2,
        timeout=httpx.Timeout(
            timeout=cfg.llm_timeout_sec,
            connect=cfg.http_connect_timeout,
        ),
        limits=httpx.Limits(
            max_connections=cfg.http_max_connection,
            max_keepalive_connections=cfg.http_max_keepalive,
        ),
    )
    return (
        AsyncOpenAI(
            base_url=cfg.model_endpoint,
            api_key=cfg.model_api_key,
            http_client=http_client,
            max_retries=max_retries,
        ),
        http_client,
    )


def _resolve_model_name(
    model_name: str | None,
    preference: ModelPreference | None,
) -> str:
    settings: BaseSettings = get_settings()
    if model_name:
        return model_name
    if preference is ModelPreference.QUALITY:
        return settings.deeply_thinking_model_api_deployment_name or settings.model_api_deployment_name
    if preference is ModelPreference.SPEED:
        return settings.lightly_thinking_model_api_deployment_name or settings.model_api_deployment_name
    return settings.model_api_deployment_name


def _require_content(content: str | None) -> str:
    if not content:
        message = "LLM 응답 content가 비어 있습니다."
        raise ValueError(message)
    return content


def _extra_headers(trace_context: TraceContext | None) -> dict[str, str] | None:
    if trace_context is None:
        return None
    return build_aip_headers(trace_context)


def _is_mlflow_tracing_enabled(trace_context: TraceContext | None = None) -> bool:
    if trace_context is None:
        return False
    try:
        cfg = get_settings()
        is_enabled = getattr(cfg, "is_mlflow_tracing_enabled", None)
        if callable(is_enabled):
            return bool(is_enabled(agent_name=trace_context.agent_name))
        return bool(getattr(cfg, "mlflow_tracing_enabled", False))
    except Exception as exc:
        logger.warning("MLflow LLM span disabled because settings lookup failed | error={!r}", exc)
        return False


@contextmanager
def _mlflow_llm_span(
    *,
    name: str,
    model: str,
    messages: list[dict[str, str]],
    trace_context: TraceContext | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[Any | None]:
    if not _is_mlflow_tracing_enabled(trace_context):
        with nullcontext(None) as span:
            yield span
        return

    try:
        import mlflow
    except Exception as exc:
        logger.warning("MLflow LLM span disabled because mlflow import failed | error={!r}", exc)
        with nullcontext(None) as span:
            yield span
        return

    span_attributes = {"model": model, **_mlflow_trace_attributes(trace_context), **(attributes or {})}
    try:
        manager = mlflow.start_span(name=name, span_type="CHAT_MODEL", attributes=span_attributes)
    except Exception as exc:
        logger.warning("MLflow LLM span failed, continuing without manual span | error={!r}", exc)
        with nullcontext(None) as span:
            yield span
        return

    try:
        span = manager.__enter__()
    except Exception as exc:
        logger.warning("MLflow LLM span enter failed, continuing without manual span | error={!r}", exc)
        with nullcontext(None) as span:
            yield span
        return

    _set_mlflow_span_inputs(span, {"messages": messages})
    try:
        yield span
    except BaseException as exc:
        try:
            manager.__exit__(type(exc), exc, exc.__traceback__)
        except Exception as exit_exc:
            logger.warning("MLflow LLM span exit failed, continuing original exception | error={!r}", exit_exc)
        raise
    else:
        try:
            manager.__exit__(None, None, None)
        except Exception as exc:
            logger.warning("MLflow LLM span exit failed, continuing without manual span close | error={!r}", exc)


def _set_mlflow_span_inputs(span: Any | None, inputs: Any) -> None:  # noqa: ANN401
    if span is None:
        return
    try:
        span.set_inputs(inputs)
    except Exception as exc:
        logger.warning("MLflow LLM span input logging failed | error={!r}", exc)


def _set_mlflow_span_outputs(span: Any | None, outputs: Any) -> None:  # noqa: ANN401
    if span is None:
        return
    try:
        span.set_outputs(outputs)
    except Exception as exc:
        logger.warning("MLflow LLM span output logging failed | error={!r}", exc)


def _mlflow_trace_attributes(trace_context: TraceContext | None) -> dict[str, str]:
    if trace_context is None:
        return {}

    attributes = {
        "aip.transaction_id": trace_context.transaction_id,
        "aip.app_id": trace_context.app_identifier,
    }
    if trace_context.scenario_group_id:
        attributes["scenario_group_id"] = trace_context.scenario_group_id
    return attributes


def _to_langchain_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
    langchain_messages: list[BaseMessage] = []
    for message in messages:
        role = message.get("role", "")
        content = message.get("content") or ""
        if role == "system":
            langchain_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            langchain_messages.append(AIMessage(content=content))
        else:
            langchain_messages.append(HumanMessage(content=content))
    return langchain_messages


def _get_langchain_llm_callback_manager() -> Any | None:  # noqa: ANN401
    callbacks = get_current_langchain_callbacks()
    if callbacks is None:
        return None
    if hasattr(callbacks, "on_chat_model_start"):
        return callbacks
    if hasattr(callbacks, "get_child"):
        child = callbacks.get_child("llm")
        if hasattr(child, "on_chat_model_start"):
            return child
    return None


def _get_mlflow_span_from_langchain_run(run_manager: object) -> object | None:
    run_id = getattr(run_manager, "run_id", None)
    handlers = getattr(run_manager, "handlers", [])
    if run_id is None:
        return None

    for handler in handlers:
        get_span = getattr(handler, "_get_span_by_run_id", None)
        if get_span is None:
            continue
        try:
            span = get_span(run_id)
        except Exception as exc:
            logger.warning("MLflow span lookup from LangChain run failed | error={!r}", exc)
            continue
        if span is not None:
            return span
    return None


def _start_openai_child_span(
    *,
    parent_span: object | None,
    model: str,
    messages: list[dict[str, str]],
    trace_context: TraceContext | None = None,
) -> object | None:
    if parent_span is None or not _is_mlflow_tracing_enabled(trace_context):
        return None

    try:
        import mlflow
    except Exception as exc:
        logger.warning("OpenAI child span disabled because mlflow import failed | error={!r}", exc)
        return None

    try:
        return mlflow.start_span_no_context(
            name="AsyncCompletions",
            span_type="CHAT_MODEL",
            parent_span=parent_span,
            inputs={"messages": messages},
            attributes={
                "model": model,
                "mlflow.spanType": "CHAT_MODEL",
                "mlflow.chat.message_format": "openai",
            },
        )
    except Exception as exc:
        logger.warning("OpenAI child span start failed | error={!r}", exc)
        return None


def _end_openai_child_span(span: object | None, outputs: Any, *, error: BaseException | None = None) -> None:  # noqa: ANN401
    if span is None:
        return
    try:
        if error is not None:
            span.end(outputs=outputs, status="ERROR")
        else:
            span.end(outputs=outputs)
    except Exception as exc:
        logger.warning("OpenAI child span end failed | error={!r}", exc)


async def _maybe_await(value: Any) -> Any:  # noqa: ANN401
    if isawaitable(value):
        return await value
    return value


async def _start_langchain_llm_run(
    *,
    name: str,
    model: str,
    messages: list[dict[str, str]],
    trace_context: TraceContext | None,
    attributes: dict[str, Any] | None,
) -> Any | None:  # noqa: ANN401
    callback_manager = _get_langchain_llm_callback_manager()
    if callback_manager is None:
        return None

    span_attributes = {**_mlflow_trace_attributes(trace_context), **(attributes or {})}
    try:
        managers = await _maybe_await(
            callback_manager.on_chat_model_start(
                {"name": name, "id": ["apps", "connectors", "llm", name]},
                [_to_langchain_messages(messages)],
                name=name,
                invocation_params={
                    "model": model,
                    "_type": "openai-chat",
                },
                **span_attributes,
            ),
        )
    except Exception as exc:
        logger.warning("LangChain LLM callback start failed, falling back to MLflow span | error={!r}", exc)
        return None

    if not managers:
        return None
    return managers[0]


def _usage_metadata(usage: LLMUsageModel | None) -> dict[str, int] | None:
    if usage is None:
        return None
    return {
        "input_tokens": usage.prompt_tokens,
        "output_tokens": usage.completion_tokens,
        "total_tokens": usage.total_tokens,
    }


async def _end_langchain_llm_run(
    run_manager: Any,  # noqa: ANN401
    *,
    content: str | None,
    model: str,
    usage: LLMUsageModel | None,
) -> None:
    generation = ChatGeneration(
        message=AIMessage(
            content=content or "",
            response_metadata={"model": model},
            usage_metadata=_usage_metadata(usage),
        ),
    )
    response = LLMResult(
        generations=[[generation]],
        llm_output={"model_name": model, "token_usage": usage.model_dump() if usage else None},
    )
    await _maybe_await(run_manager.on_llm_end(response))


async def _error_langchain_llm_run(run_manager: Any, error: BaseException) -> None:  # noqa: ANN401
    await _maybe_await(run_manager.on_llm_error(error))


@asynccontextmanager
async def _llm_trace_span(
    *,
    name: str,
    model: str,
    messages: list[dict[str, str]],
    trace_context: TraceContext | None = None,
    attributes: dict[str, Any] | None = None,
) -> Iterator[_LLMTraceRun]:
    langchain_run_manager = await _start_langchain_llm_run(
        name=name,
        model=model,
        messages=messages,
        trace_context=trace_context,
        attributes=attributes,
    )
    if langchain_run_manager is not None:
        openai_span = _start_openai_child_span(
            parent_span=_get_mlflow_span_from_langchain_run(langchain_run_manager),
            model=model,
            messages=messages,
            trace_context=trace_context,
        )
        trace_run = _LLMTraceRun(langchain_run_manager=langchain_run_manager, openai_span=openai_span)
        try:
            yield trace_run
        except BaseException as exc:
            _end_openai_child_span(openai_span, {"error": str(exc)}, error=exc)
            try:
                await _error_langchain_llm_run(langchain_run_manager, exc)
            except Exception as error_exc:
                logger.warning("LangChain LLM callback error logging failed | error={!r}", error_exc)
            raise
        return

    with _mlflow_llm_span(
        name=name,
        model=model,
        messages=messages,
        trace_context=trace_context,
        attributes=attributes,
    ) as mlflow_span:
        yield _LLMTraceRun(mlflow_span=mlflow_span)


async def _set_llm_trace_outputs(
    trace_run: _LLMTraceRun,
    outputs: Any,  # noqa: ANN401
    *,
    content: str | None,
    model: str,
    usage: LLMUsageModel | None,
) -> None:
    if trace_run.langchain_run_manager is not None:
        _end_openai_child_span(trace_run.openai_span, outputs)
        try:
            await _end_langchain_llm_run(
                trace_run.langchain_run_manager,
                content=content,
                model=model,
                usage=usage,
            )
            trace_run.completed = True
        except Exception as exc:
            logger.warning("LangChain LLM callback end failed | error={!r}", exc)
        return

    _set_mlflow_span_outputs(trace_run.mlflow_span, outputs)
    trace_run.completed = True


@log_connector(connector_type="LLM", log_input=False, log_output=False, log_retry=False)
async def invoke_llm_function_call(
    messages: list[dict[str, str]],
    model_name: str | None = None,
    *,
    preference: ModelPreference | None = None,
    functions: list | None = None,
    function_call: dict | None = None,
    temperature: float = 0.7,
    max_retries: int = 2,
    trace_context: TraceContext | None = None,
) -> dict[str, Any]:
    await ensure_runtime_context_ready()
    client, http_client = _create_openai_client(max_retries=max_retries)
    model = _resolve_model_name(model_name, preference)
    llm_sem = get_llm_semaphore()
    http_sem = get_http_semaphore()

    try:
        async with (
            llm_sem,
            http_sem,
            _llm_trace_span(
                name="llm.function_call",
                model=model,
                messages=messages,
                trace_context=trace_context,
                attributes={"llm.call_type": "function_call"},
            ) as trace_run,
        ):
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                functions=functions,
                function_call=function_call,
                extra_headers=_extra_headers(trace_context),
                # temperature=temperature,
            )
            choice = resp.choices[0]
            usage = LLMUsageModel.model_validate(resp.usage.model_dump()) if resp.usage else None
            accumulate_usage(usage)
            result = {
                "id": resp.id,
                "content": choice.message.content,
                "finish_reason": choice.finish_reason,
                "usage": usage.model_dump() if usage else None,
                "model": model,
            }
            await _set_llm_trace_outputs(
                trace_run,
                result,
                content=choice.message.content,
                model=model,
                usage=usage,
            )
            return result
    except Exception as ex:
        raise MIBaseError(ErrorCode.LLM_INVOCATION_ERROR, detail=str(ex)) from ex
    finally:
        await http_client.aclose()


@log_connector(connector_type="LLM", log_input=False, log_output=False, log_retry=False)
async def invoke_llm_structured_output[T: BaseModel](
    output_schema: type[T],
    prompt: str | None = None,
    *,
    messages: list[dict[str, str]] | None = None,
    model_name: str | None = None,
    preference: ModelPreference | None = None,
    temperature: float = 0.0,
    max_retries: int = 2,
    trace_context: TraceContext | None = None,
) -> LLMStructuredResult[T]:
    """Structured output LLM 호출. 결과와 usage 정보를 함께 반환."""
    await ensure_runtime_context_ready()
    client, http_client = _create_openai_client(max_retries=max_retries)

    model = _resolve_model_name(model_name, preference)
    llm_sem = get_llm_semaphore()
    http_sem = get_http_semaphore()

    if messages is None:
        messages = [{"role": "user", "content": prompt}]

    try:
        async with (
            llm_sem,
            http_sem,
            _llm_trace_span(
                name=f"llm.structured_output.{output_schema.__name__}",
                model=model,
                messages=messages,
                trace_context=trace_context,
                attributes={
                    "llm.call_type": "structured_output",
                    "llm.output_schema": output_schema.__name__,
                },
            ) as trace_run,
        ):
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                extra_headers=_extra_headers(trace_context),
                # temperature=temperature,
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": output_schema.__name__,
                        "schema": output_schema.model_json_schema(),
                        "strict": False,
                    },
                },
            )
            content = resp.choices[0].message.content
            parsed_result = output_schema.model_validate_json(content)
            usage = LLMUsageModel.model_validate(resp.usage.model_dump()) if resp.usage else None
            accumulate_usage(usage)
            result = LLMStructuredResult[T](result=parsed_result, usage=usage, model=model)
            await _set_llm_trace_outputs(
                trace_run,
                {
                    "content": content,
                    "parsed": parsed_result.model_dump(),
                    "usage": usage.model_dump() if usage else None,
                    "model": model,
                },
                content=content,
                model=model,
                usage=usage,
            )
            return result
    except Exception as ex:
        raise MIBaseError(ErrorCode.LLM_INVOCATION_ERROR, detail=str(ex)) from ex
    finally:
        await http_client.aclose()


@log_connector(connector_type="LLM", log_input=False, log_output=False, log_retry=False)
async def invoke_llm_text(
    messages: list[dict[str, str]],
    model_name: str | None = None,
    *,
    preference: ModelPreference | None = None,
    temperature: float = 0.0,
    max_retries: int = 2,
    trace_context: TraceContext | None = None,
) -> dict[str, Any]:
    await ensure_runtime_context_ready()
    client, http_client = _create_openai_client(max_retries=max_retries)

    model = _resolve_model_name(model_name, preference)
    llm_sem = get_llm_semaphore()
    http_sem = get_http_semaphore()

    try:
        async with (
            llm_sem,
            http_sem,
            _llm_trace_span(
                name="llm.text",
                model=model,
                messages=messages,
                trace_context=trace_context,
                attributes={"llm.call_type": "text"},
            ) as trace_run,
        ):
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                extra_headers=_extra_headers(trace_context),
            )

            content = _require_content(resp.choices[0].message.content)

            usage = LLMUsageModel.model_validate(resp.usage.model_dump()) if resp.usage else None
            accumulate_usage(usage)

            result = {
                "id": resp.id,
                "content": content.strip(),
                "usage": usage.model_dump() if usage else None,
                "model": model,
            }
            await _set_llm_trace_outputs(
                trace_run,
                result,
                content=result["content"],
                model=model,
                usage=usage,
            )
            return result
    except Exception as ex:
        raise MIBaseError(ErrorCode.LLM_INVOCATION_ERROR, detail=str(ex)) from ex
    finally:
        await http_client.aclose()
