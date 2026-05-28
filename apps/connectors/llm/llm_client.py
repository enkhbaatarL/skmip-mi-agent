#   apps/connectors/llm/llm_client.py
#   kmj20260423목,    주석문 추가
"""
LLM 호출 공통 클라이언트 모듈

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

import asyncio
from typing import Any, TypeVar

import httpx
from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

from apps.common.configs.settings import BaseSettings, get_settings
from apps.common.exceptions.custom import LLMInvocationError
from apps.common.logging.decorators import log_connector
from apps.common.runtime.runtime import (
    ensure_runtime_context_ready,
    get_http_client,
    get_http_semaphore,
    get_llm_semaphore,
)
from apps.common.runtime.usage_context import accumulate_usage
from apps.common.values.enums import ModelPreference
from apps.common.values.llm_usage import LLMUsageModel


_openai_client: AsyncOpenAI | None = None
_client_init_lock = asyncio.Lock()

T = TypeVar("T", bound=BaseModel)


class LLMStructuredResult[T: BaseModel](BaseModel):
    """Structured output 결과와 usage 정보를 함께 반환하는 모델."""

    result: T
    usage: LLMUsageModel | None = None


async def _ensure_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client:
        return _openai_client

    async with _client_init_lock:
        if _openai_client:
            return _openai_client

        cfg = get_settings()
        http_client = await get_http_client(base_url=cfg.model_endpoint)
        _openai_client = AsyncOpenAI(
            base_url=cfg.model_endpoint,
            api_key=cfg.model_api_key,
            http_client=http_client,
        )

        return _openai_client


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
) -> dict[str, Any]:
    await ensure_runtime_context_ready()
    client = await _ensure_openai_client()
    settings: BaseSettings = get_settings()
    client = OpenAI(
        base_url=settings.model_endpoint,
        api_key=settings.api_key,
        # http_client=httpx.Client(verify=False, timeout=settings.llm_timeout_sec),
        http_client=httpx.Client(verify=False),
        max_retries=max_retries,
    )
    model = _resolve_model_name(model_name, preference)
    llm_sem = get_llm_semaphore()
    http_sem = get_http_semaphore()

    try:
        async with llm_sem, http_sem:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                functions=functions,
                function_call=function_call,
                # temperature=temperature,
            )
            choice = resp.choices[0]
            usage = LLMUsageModel.model_validate(resp.usage.model_dump()) if resp.usage else None
            accumulate_usage(usage)
            return {
                "id": resp.id,
                "content": choice.message.content,
                "finish_reason": choice.finish_reason,
                "usage": usage.model_dump() if usage else None,
                "model": model,
            }
    except Exception as ex:
        raise LLMInvocationError(detail=str(ex)) from ex


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
) -> LLMStructuredResult[T]:
    """Structured output LLM 호출. 결과와 usage 정보를 함께 반환."""
    await ensure_runtime_context_ready()
    await _ensure_openai_client()

    settings: BaseSettings = get_settings()
    client = OpenAI(
        base_url=settings.model_endpoint,
        api_key=settings.api_key,
        http_client=httpx.Client(verify=False),  # TODO: verify= True로 변경
        max_retries=max_retries,
    )

    model = _resolve_model_name(model_name, preference)
    llm_sem = get_llm_semaphore()
    http_sem = get_http_semaphore()

    if messages is None:
        messages = [{"role": "user", "content": prompt}]

    try:
        async with llm_sem, http_sem:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
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
            return LLMStructuredResult[T](result=parsed_result, usage=usage)
    except Exception as ex:
        raise LLMInvocationError(detail=str(ex)) from ex

@log_connector(connector_type="LLM", log_input=False, log_output=False, log_retry=False)
async def invoke_llm_text(
    messages: list[dict[str, str]],
    model_name: str | None = None,
    *,
    preference: ModelPreference | None = None,
    temperature: float = 0.0,
    max_retries: int = 2,
) -> dict[str, Any]:
    await ensure_runtime_context_ready()

    settings: BaseSettings = get_settings()
    client = OpenAI(
        base_url=settings.model_endpoint,
        api_key=settings.api_key,
        http_client=httpx.Client(verify=False),
        max_retries=max_retries,
    )

    model = _resolve_model_name(model_name, preference)
    llm_sem = get_llm_semaphore()
    http_sem = get_http_semaphore()

    try:
        async with llm_sem, http_sem:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
            )

            content = resp.choices[0].message.content
            if not content:
                raise ValueError("LLM 응답 content가 비어 있습니다.")

            usage = LLMUsageModel.model_validate(resp.usage.model_dump()) if resp.usage else None
            accumulate_usage(usage)

            return {
                "id": resp.id,
                "content": content.strip(),
                "usage": usage.model_dump() if usage else None,
                "model": model,
            }
    except Exception as ex:
        raise LLMInvocationError(detail=str(ex)) from ex