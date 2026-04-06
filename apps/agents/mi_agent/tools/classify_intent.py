from apps.agents.mi_agent.prompts.classify_analysis_type import build_classify_analysis_type_prompt
from apps.common.logging.decorators import log_tool
from apps.common.values.enums import AnalysisType
from apps.connectors.llm.llm_client import invoke_llm_function_call


@log_tool
async def classify_intent(
    rewritten_query: str,
) -> AnalysisType:
    prompt: str = build_classify_analysis_type_prompt(rewritten_query)

    result = await invoke_llm_function_call(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )
    analysis_type: AnalysisType = result["content"]
    return analysis_type
