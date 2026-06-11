"""SKT AI Gateway OpenAI Client Helper
─────────────────────────────────────
`event_generation_news` 폴더의 모든 LLM 호출이 공유하는 OpenAI 호환 클라이언트 빌더 +
구조화 출력 호출(파싱/폴백) 유틸.

## 환경변수
| 변수명                             | 필수 | 기본값                                                | 설명                                                                                          |
| ---------------------------------- | ---- | ----------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| `SKT_AI_API_KEY`                   | O    | -                                                     | SKT AI Gateway API 키 (`sk-...`)                                                              |
| `SKT_AI_BASE_URL`                  |      | `https://aip-stg.sktai.io/api/v1/gateway`             | Gateway base URL (보통 변경 불필요)                                                            |
| `MI_LLM_MODEL`                     |      | `skmidev-gpt-5.5-20260424`                            | 호출 모델명 기본값                                                                            |
| `MI_LLM_TEMPERATURE`               |      | (omit)                                                | 명시 시에만 `temperature` 파라미터 사용. GPT-5 reasoning 계열은 기본 omit 권장.                |
| `MI_LLM_FORCE_JSON_OBJECT`         |      | `0`                                                   | `1` 이면 처음부터 `response_format={"type":"json_object"}` 모드를 사용 (parse 시도 안 함).    |

`SKT_AI_API_KEY` 가 비어있으면 하위 호환으로 `OPENAI_API_KEY` 도 함께 조회한다.

## 사용 예
```bash
export SKT_AI_API_KEY="sk-xxxx..."
python mi_record_analysis.py --input ... --output ...
```
"""

from __future__ import annotations

import json
import os
from typing import Any, List, Type

from openai import AsyncOpenAI, OpenAI
from pydantic import BaseModel

DEFAULT_BASE_URL = "https://aip-stg.sktai.io/api/v1/gateway"
DEFAULT_MODEL    = "skmidev-gpt-5.5-20260424"


# ══════════════════════════════════════════════════════════════
# Client builders
# ══════════════════════════════════════════════════════════════

def _resolve_credentials() -> tuple[str, str]:
    """API key / base URL 을 환경변수에서 해석. 키 누락 시 RuntimeError."""
    api_key = os.getenv("SKT_AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "SKT AI Gateway API 키가 설정되지 않았습니다.\n"
            "  export SKT_AI_API_KEY=\"sk-...\"  형식으로 환경변수를 설정한 후 다시 실행하세요."
        )
    base_url = os.getenv("SKT_AI_BASE_URL", DEFAULT_BASE_URL)
    return api_key, base_url


def get_default_model() -> str:
    """파이프라인 공통 기본 모델명."""
    return os.getenv("MI_LLM_MODEL", DEFAULT_MODEL)


def get_openai_client() -> OpenAI:
    """동기 OpenAI 호환 클라이언트."""
    api_key, base_url = _resolve_credentials()
    return OpenAI(api_key=api_key, base_url=base_url)


def get_async_openai_client() -> AsyncOpenAI:
    """비동기 OpenAI 호환 클라이언트."""
    api_key, base_url = _resolve_credentials()
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


# ══════════════════════════════════════════════════════════════
# Completion kwargs builder & feature flags
# ══════════════════════════════════════════════════════════════

def _resolve_temperature(env_prefix: str) -> float | None:
    """`{env_prefix}_TEMPERATURE` 환경변수를 해석.

    값이 비었거나 `skip`/`default`/`none` 이면 None 반환(=파라미터 omit).
    GPT-5 reasoning 계열은 `temperature` 파라미터 자체를 거부하므로 기본은 omit.
    """
    raw = (
        os.getenv(f"{env_prefix}_TEMPERATURE")
        if env_prefix
        else None
    )
    if raw is None:
        raw = os.getenv("MI_LLM_TEMPERATURE")
    if raw is None:
        return None
    raw = raw.strip()
    if raw == "" or raw.lower() in {"skip", "default", "none", "omit"}:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def build_completion_kwargs(
    model: str,
    messages: List[dict],
    *,
    response_format: Any = None,
    max_completion_tokens: int | None = None,
    env_prefix: str = "MI_LLM",
) -> dict:
    """OpenAI `chat.completions.*` 호출 kwargs 구성.

    - `temperature`: `{env_prefix}_TEMPERATURE` 또는 `MI_LLM_TEMPERATURE` 가 설정된
      경우에만 추가. SKT Gateway 의 GPT-5 계열은 `temperature` 변경을 거부할 수
      있으므로 기본 omit 한다.
    - `max_completion_tokens`: 양수일 때만 추가.
    - `response_format`: 그대로 전달.
    """
    kwargs: dict = {"model": model, "messages": messages}
    if response_format is not None:
        kwargs["response_format"] = response_format

    temperature = _resolve_temperature(env_prefix)
    if temperature is not None:
        kwargs["temperature"] = temperature

    if max_completion_tokens is not None and max_completion_tokens > 0:
        kwargs["max_completion_tokens"] = max_completion_tokens

    return kwargs


def force_json_object_mode() -> bool:
    """`MI_LLM_FORCE_JSON_OBJECT=1` 이면 처음부터 json_object 모드 사용."""
    return os.getenv("MI_LLM_FORCE_JSON_OBJECT", "0").strip().lower() in {"1", "true", "yes"}


def is_structured_outputs_unsupported(exc: Exception) -> bool:
    """`parse()` 실패가 SKT Gateway의 strict structured outputs 미지원 신호인지 판정.

    Gateway/모델이 `response_format={"type":"json_schema",...}` 을 거부할 때 자동으로
    `response_format={"type":"json_object"}` 모드로 폴백하기 위한 휴리스틱.
    """
    status = getattr(exc, "status_code", None)
    if status is not None and status not in (400, 404, 415, 422, 501):
        return False
    name = exc.__class__.__name__.lower()
    msg = str(exc).lower()
    triggers = (
        "response_format",
        "json_schema",
        "json schema",
        "structured outputs",
        "structured output",
        "unsupported parameter",
        "is not supported",
        "not supported",
        "unrecognized",
        "unknown parameter",
        "invalid_request",
        "invalid request",
    )
    if any(t in msg for t in triggers):
        return True
    # parse() 자체가 못 만든 케이스 (예: openai SDK 가 응답을 schema 로 못 맞춤)
    if "lengthfinishreasonerror" in name or "contentfilterfinishreasonerror" in name:
        return False
    return False


# ══════════════════════════════════════════════════════════════
# JSON-Object fallback (response_format = json_object)
# ══════════════════════════════════════════════════════════════

JSON_OBJECT_HINT_HEADER = (
    "\n\n[출력 형식 (반드시 준수)]\n"
    "아래 JSON Schema 에 정합하는 JSON 객체만 반환하세요. "
    "마크다운 코드블록(```)이나 설명 텍스트 없이, 첫 글자가 `{` 인 순수 JSON 만 출력하세요.\n"
)


def _schema_block(response_model: Type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    return (
        JSON_OBJECT_HINT_HEADER
        + "```json\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n```"
    )


def _augment_messages_with_schema(
    messages: List[dict], response_model: Type[BaseModel]
) -> List[dict]:
    """첫 system 메시지에 JSON Schema 안내 블록을 덧붙여 새 리스트 반환."""
    block = _schema_block(response_model)
    out: List[dict] = []
    appended = False
    for m in messages:
        if m.get("role") == "system" and not appended:
            out.append({**m, "content": (m.get("content") or "") + block})
            appended = True
        else:
            out.append(m)
    if not appended:
        out.insert(0, {"role": "system", "content": block})
    return out


def _strip_code_fence(text: str) -> str:
    """LLM이 가끔 감싸는 ```json ... ``` 코드펜스를 제거."""
    s = text.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1] if "\n" in s else ""
        if s.rstrip().endswith("```"):
            s = s.rstrip()[: -3]
    return s.strip()


def parse_via_json_object_sync(
    client: OpenAI,
    model: str,
    messages: List[dict],
    response_model: Type[BaseModel],
    max_completion_tokens: int | None = None,
    env_prefix: str = "MI_LLM",
) -> BaseModel:
    """동기 — `response_format=json_object` 모드 + 수동 Pydantic 검증."""
    augmented = _augment_messages_with_schema(messages, response_model)
    kwargs = build_completion_kwargs(
        model,
        augmented,
        response_format={"type": "json_object"},
        max_completion_tokens=max_completion_tokens,
        env_prefix=env_prefix,
    )
    completion = client.chat.completions.create(**kwargs)
    raw = (completion.choices[0].message.content or "").strip()
    if not raw:
        raise ValueError("json_object 모드: 응답 content 가 비어 있음.")
    data = json.loads(_strip_code_fence(raw))
    return response_model.model_validate(data)


async def parse_via_json_object_async(
    client: AsyncOpenAI,
    model: str,
    messages: List[dict],
    response_model: Type[BaseModel],
    max_completion_tokens: int | None = None,
    env_prefix: str = "MI_LLM",
) -> BaseModel:
    """비동기 — `response_format=json_object` 모드 + 수동 Pydantic 검증."""
    augmented = _augment_messages_with_schema(messages, response_model)
    kwargs = build_completion_kwargs(
        model,
        augmented,
        response_format={"type": "json_object"},
        max_completion_tokens=max_completion_tokens,
        env_prefix=env_prefix,
    )
    completion = await client.chat.completions.create(**kwargs)
    raw = (completion.choices[0].message.content or "").strip()
    if not raw:
        raise ValueError("json_object 모드: 응답 content 가 비어 있음.")
    data = json.loads(_strip_code_fence(raw))
    return response_model.model_validate(data)


# ══════════════════════════════════════════════════════════════
# Strict parse + auto-fallback wrappers
# ══════════════════════════════════════════════════════════════

def parse_structured_sync(
    client: OpenAI,
    model: str,
    messages: List[dict],
    response_model: Type[BaseModel],
    max_completion_tokens: int | None = None,
    env_prefix: str = "MI_LLM",
) -> BaseModel:
    """동기 — 1) `client.beta.chat.completions.parse(...)` 우선 시도,
    2) Gateway 가 strict structured outputs(json_schema)을 지원하지 않으면
       자동으로 `response_format={"type":"json_object"}` 모드로 폴백.
    """
    if force_json_object_mode():
        return parse_via_json_object_sync(
            client, model, messages, response_model,
            max_completion_tokens=max_completion_tokens,
            env_prefix=env_prefix,
        )

    kwargs = build_completion_kwargs(
        model, messages,
        response_format=response_model,
        max_completion_tokens=max_completion_tokens,
        env_prefix=env_prefix,
    )
    try:
        completion = client.beta.chat.completions.parse(**kwargs)
    except Exception as exc:  # noqa: BLE001
        if is_structured_outputs_unsupported(exc):
            print(
                "    ↳ structured outputs 미지원 감지 → json_object 모드로 폴백 "
                f"({exc.__class__.__name__}: {str(exc)[:160]})"
            )
            return parse_via_json_object_sync(
                client, model, messages, response_model,
                max_completion_tokens=max_completion_tokens,
                env_prefix=env_prefix,
            )
        raise
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("OpenAI parse() 결과가 비어 있음.")
    return parsed


async def parse_structured_async(
    client: AsyncOpenAI,
    model: str,
    messages: List[dict],
    response_model: Type[BaseModel],
    max_completion_tokens: int | None = None,
    env_prefix: str = "MI_LLM",
) -> BaseModel:
    """비동기 버전. (위 `parse_structured_sync` 와 동일한 폴백 로직)"""
    if force_json_object_mode():
        return await parse_via_json_object_async(
            client, model, messages, response_model,
            max_completion_tokens=max_completion_tokens,
            env_prefix=env_prefix,
        )

    kwargs = build_completion_kwargs(
        model, messages,
        response_format=response_model,
        max_completion_tokens=max_completion_tokens,
        env_prefix=env_prefix,
    )
    try:
        completion = await client.beta.chat.completions.parse(**kwargs)
    except Exception as exc:  # noqa: BLE001
        if is_structured_outputs_unsupported(exc):
            print(
                "    ↳ structured outputs 미지원 감지 → json_object 모드로 폴백 "
                f"({exc.__class__.__name__}: {str(exc)[:160]})"
            )
            return await parse_via_json_object_async(
                client, model, messages, response_model,
                max_completion_tokens=max_completion_tokens,
                env_prefix=env_prefix,
            )
        raise
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("OpenAI parse() 결과가 비어 있음.")
    return parsed
