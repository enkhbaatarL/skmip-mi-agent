from __future__ import annotations

# ruff: noqa: CPY001
import json
from typing import Any

from pydantic import BaseModel

from tests.manual.multi_event_comparison.models import (
    ComparisonJudgment,
)


async def invoke_structured(output_schema: type[BaseModel], prompt: str) -> BaseModel:
    """Use the application runtime and connector for a deterministic structured call."""
    from apps.common.runtime.runtime import ensure_runtime_context_ready
    from apps.common.values.enums import ModelPreference
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    await ensure_runtime_context_ready()
    response = await invoke_llm_structured_output(
        output_schema,
        prompt=prompt,
        preference=ModelPreference.QUALITY,
        temperature=0,
    )
    return response.result


async def judge_comparison(evidence: dict[str, Any]) -> ComparisonJudgment:
    prompt = f"""You are a strict judge comparing v2, v3, and v4 multi-event LNG
scenario-generation API outputs. Use only the supplied Event and API evidence.
Do not browse and do not add outside facts.

For every successful version, return exactly these four criteria once:
- event_consistency: no contradiction with supplied events and causal grounding.
- lng_dimension_quality: LNG-price-relevant supply, demand, trade, timing, recovery,
  mitigation, and interaction drivers are represented as useful dimensions.
- floor_ceiling_quality: floor and ceiling are coherent extrema of the actual cells
  and pressure rationale, not merely labels.
- mixed_quality: mixed scenarios exist only where opposing drivers need combination,
  and the offset/interaction is coherent.

Score each criterion from 1 to 5. Provide evidence using actual payload values or
precise paths. Also assess every scenario row once, preserving scenario ID, title,
and global pressure band. Select the version(s) with the highest simple average of
the four criterion scores; exact ties are joint winners.

Evidence:
{json.dumps(evidence, ensure_ascii=False, indent=2, default=str)}
"""
    result = await invoke_structured(ComparisonJudgment, prompt)
    return ComparisonJudgment.model_validate(result)
