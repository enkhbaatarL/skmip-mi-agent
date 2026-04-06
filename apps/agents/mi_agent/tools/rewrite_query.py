import json

from apps.agents.mi_agent.prompts.rewrite_queries import (
    build_queries_rewrite_prompt,
)
from apps.agents.mi_agent.schemas.schemas import RewriteQueryResult
from apps.common.logging.decorators import log_tool
from apps.common.values.enums import ModelPreference
from apps.connectors.llm.llm_client import invoke_llm_function_call


@log_tool
async def rewrite_query(histories: list[dict], message: str) -> RewriteQueryResult:
    prompt = build_queries_rewrite_prompt(
        histories=histories,
        message=message,
    )
    response = await invoke_llm_function_call(
        messages=[{"role": "user", "content": prompt}],
        preference=ModelPreference.QUALITY,
        temperature=0.0,
    )

    raw = response["content"]
    payload = json.loads(raw)
    return RewriteQueryResult.model_validate(payload)
