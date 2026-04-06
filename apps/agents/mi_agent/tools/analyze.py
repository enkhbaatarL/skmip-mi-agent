"""Analysis tool for processing search results and generating insights."""

from __future__ import annotations

import json
import re
from typing import Any

from apps.agents.mi_agent.prompts.analysis_search_result import build_analysis_prompt
from apps.agents.mi_agent.prompts.language_translation import build_query_langguage_out_prompt
from apps.agents.mi_agent.schemas.schemas import AnalysisOutput
from apps.agents.mi_agent.schemas.search_output import SearchOutput
from apps.common.logging.decorators import log_tool
from apps.common.logging.logger_config import logger
from apps.common.values.enums import ModelPreference
from apps.connectors.llm.llm_client import invoke_llm_function_call


@log_tool
async def analyze_search_results(
    rewritten_query: str,
    user_query_language: str,
    search_output: SearchOutput,
) -> AnalysisOutput:
    # TODO: 유사패턴 관련 내용 추가
    analysis_text = await _generate_analysis(
        rewritten_query=rewritten_query,
        user_query_language=user_query_language,
        search_output=search_output,
    )

    # JSON 블록 파싱 (구조화된 데이터 추출)
    text_without_json, structured_data = _parse_structured_output(analysis_text)

    # 추가 질문 파싱 및 분리
    content, suggested_questions = _parse_suggested_questions(text_without_json)

    final_content = await _translate_to_user_language(
        text=content,
        target_language=user_query_language,
    )

    # 구조화된 데이터에서 analysis_summary 추출
    analysis_summary = structured_data.get("analysis_summary", "")

    return AnalysisOutput(
        content=final_content,
        suggested_questions=suggested_questions,
        analysis_summary=analysis_summary,
    )


def _parse_suggested_questions(text: str) -> tuple[str, list[str]]:
    """분석 텍스트에서 '추가로 궁금하실 수 있는 질문들' 섹션을 분리합니다.

    Returns:
        tuple: (질문 섹션을 제외한 분석 내용, 추가 질문 리스트)

    """
    # "### 추가로 궁금하실 수 있는 질문들:" 패턴으로 분리
    pattern = r"---\s*\n+###\s*추가로 궁금하실 수 있는 질문들:\s*\n"
    parts = re.split(pattern, text, maxsplit=1)

    if len(parts) == 1:
        # 패턴을 찾지 못한 경우
        return text.strip(), []

    content = parts[0].strip()
    questions_section = parts[1] if len(parts) > 1 else ""

    # 번호가 붙은 질문들을 추출 (1. 2. 3. 형식)
    question_pattern = r"^\d+\.\s*(.+?)$"
    questions = re.findall(question_pattern, questions_section, re.MULTILINE)

    # 대괄호 제거 (예: [질문내용] -> 질문내용)
    cleaned_questions = []
    for q in questions:
        q = q.strip()
        if q.startswith("[") and q.endswith("]"):
            q = q[1:-1]
        cleaned_questions.append(q)

    return content, cleaned_questions


async def _generate_analysis(
    rewritten_query: str,
    user_query_language: str,
    search_output: SearchOutput,
) -> str:
    # TODO: 유사 패턴 추가
    metric_data = (
        search_output.rdb_search_output.metric_data
        if search_output.rdb_search_output and search_output.rdb_search_output.metric_data
        else ""
    )

    web_sources = (
        "\n\n".join(search_output.web_search_output.web_sources)
        if search_output.web_search_output and search_output.web_search_output.web_sources
        else ""
    )

    vdb_sources = ""
    if search_output.vdb_search_output and search_output.vdb_search_output.vector_sources:
        vdb_sources = "\n\n".join(
            f"[제목] {doc.metadata.title}\n[본문] {doc.content}"
            for doc in search_output.vdb_search_output.vector_sources
        )

    analysis_prompt = build_analysis_prompt(
        metric_data=metric_data,
        web_results=web_sources,
        vdb_sources=vdb_sources,
        user_query_language=user_query_language,
        rewrite=rewritten_query,
    )

    response = await invoke_llm_function_call(
        messages=[{"role": "user", "content": analysis_prompt}],
        preference=ModelPreference.QUALITY,
        temperature=0.0,
    )

    return response["content"]


async def _translate_to_user_language(
    text: str,
    target_language: str,
) -> str:
    translation_prompt = build_query_langguage_out_prompt(
        target_lang=target_language,
        answer=text,
    )

    response = await invoke_llm_function_call(
        messages=[{"role": "user", "content": translation_prompt}],
        preference=ModelPreference.QUALITY,
    )

    return response["content"]


def _parse_structured_output(text: str) -> tuple[str, dict[str, Any]]:
    """분석 텍스트에서 JSON 블록을 추출하고 파싱합니다.

    Returns:
        tuple: (JSON 블록을 제외한 텍스트, 파싱된 구조화 데이터)

    """
    # ```json ... ``` 블록 추출
    pattern = r"```json\s*\n(.*?)\n```"
    match = re.search(pattern, text, re.DOTALL)

    if not match:
        return text, {}

    json_str = match.group(1)
    # JSON 블록 이전의 텍스트만 유지
    content = text[: match.start()].strip()

    # JSON 블록과 추가 질문 섹션 사이의 구분선 제거
    if content.endswith("---"):
        content = content[:-3].strip()

    try:
        structured_data = json.loads(json_str)
        return content, structured_data
    except json.JSONDecodeError as e:
        logger.warning("Failed to parse structured output JSON: %s", e)
        return text, {}

