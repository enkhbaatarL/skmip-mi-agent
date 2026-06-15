"""검색 질의 생성 공통 모듈.

LLM을 이용해 사용자 질의를 단일 질의들로 분리하고 키워드를 추출하는 공통 로직을 제공한다.
RDB 및 VDB 검색 모두 이 모듈을 통해 LLM 호출 및 JSON 파싱 처리를 공유한다.
"""
from __future__ import annotations

import json
import re
from typing import Any

from apps.agents.mi_agent.schemas.schemas import SearchQuery
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.common.values.enums import ModelPreference
from apps.connectors.llm.llm_client import invoke_llm_function_call


async def generate_search_queries(prompt: str) -> list[SearchQuery]:
    """LLM 프롬프트로 검색 질의 목록을 생성한다."""
    response: dict[str, Any] = await invoke_llm_function_call(
        messages=[{"role": "user", "content": prompt}],
        preference=ModelPreference.QUALITY,
        temperature=0.0,
    )

    context = response.get("content")
    if len(context) < 1:
        raise MIBaseError(ErrorCode.LLM_INVALID_RESPONSE_ERROR, detail=f"prompt:{prompt}, return context:{context}")

    return _parse_query_items(str(context))


def _parse_query_items(raw_text: str) -> list[SearchQuery]:
    cleaned_text: str = strip_code_fence(raw_text.strip())

    try:
        data: Any = json.loads(cleaned_text)
    except json.JSONDecodeError:
        match = re.search(r"\[.*\]", cleaned_text, flags=re.DOTALL)
        data = json.loads(match.group(0)) if match else []

    if not isinstance(data, list):
        data = [data]

    search_queries: list[SearchQuery] = []
    for item in data:
        if not isinstance(item, dict):
            item = {"query": str(item), "search_text": ""}

        q: str = (item.get("query") or "").strip()
        st_raw: str = item.get("search_text") or ""
        st: str = normalize_search_text_tokens(st_raw)

        if q and st:
            search_queries.append(SearchQuery(query=q, search_text=st))

    return search_queries


def strip_code_fence(text: str) -> str:
    """``` 또는 ```json 코드 펜스를 제거한다."""
    return re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        text,
        flags=re.IGNORECASE | re.MULTILINE,
    )


def normalize_search_text_tokens(
    search_text: str,
    max_tokens: int = 12,
) -> str:
    """search_text를 벡터/풀텍스트 검색에 적합하도록 정제한다.

    - 구두점/괄호 제거 및 공백 정리
    - 날짜 토큰 제거
    - 대소문자 무시 중복 제거
    - 토큰 수를 max_tokens 이하로 보정
    """
    normalized: str = search_text.replace(",", " ")
    normalized = normalized.replace('"', " ").replace("'", " ")
    normalized = re.sub(r"[(){}\[\]]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    tokens: list[str] = normalized.split()

    date_patterns: tuple[str, ...] = (
        r"\b\d{4}[-/.]\d{2}[-/.]\d{2}\b",
        r"\b\d{4}[-/.]\d{2}\b",
        r"\b\d{4}년\s*\d{1,2}월(\s*\d{1,2}일)?\b",
    )

    def is_date_token(token: str) -> bool:
        return any(re.search(pattern, token.strip()) for pattern in date_patterns)

    tokens_without_date: list[str] = [t for t in tokens if t and not is_date_token(t)]

    seen: set[str] = set()
    deduplicated_tokens: list[str] = []
    for token in tokens_without_date:
        key = token.lower()
        if key not in seen:
            seen.add(key)
            deduplicated_tokens.append(token)

    if len(deduplicated_tokens) > max_tokens:
        deduplicated_tokens = deduplicated_tokens[:max_tokens]

    return " ".join(deduplicated_tokens)
