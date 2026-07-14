from __future__ import annotations

"""Structured LLM-as-judge calls for scenario-quality evaluation.

This module intentionally uses the application connector instead of a separate
manual-script OpenAI client.  That preserves the model selection, retry, usage,
and tracing conventions used by the scenario agent itself.
"""

import json
from typing import Any, Literal

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from .artifacts import RunArtifacts


PROMPT_VERSION = "v1"


class Violation(BaseModel):
    """An evidence-backed quality issue found by a judge rubric item."""

    target_type: str
    target_id: str
    evidence: str
    reason: str
    suggested_fix: str
    fact_dependency: Literal["NONE", "EVENT_PAYLOAD_ONLY", "EXTERNAL_FACT_REQUIRED"]


class JudgeItemScore(BaseModel):
    """Score and violations for one rubric item."""

    judge_id: str
    score: int = Field(ge=1, le=5)
    verdict: Literal["PASS", "WARN", "FAIL"]
    violations: list[Violation] = Field(default_factory=list)


class JudgeResult(BaseModel):
    """The result of one of the two bounded judge calls for a run."""

    items: list[JudgeItemScore]
    model: str
    prompt_version: str


class _JudgeResponse(BaseModel):
    """LLM connector output schema, kept separate from persisted metadata."""

    items: list[JudgeItemScore]


_SCENARIO_JUDGE_IDS = ("J-01", "J-02", "J-03", "J-04", "J-05", "J-06", "J-11")
_SIGNPOST_JUDGE_IDS = ("J-07", "J-08", "J-09", "J-10")


def _json_payload(value: dict[str, Any] | None) -> str:
    """Serialize artifact payloads deterministically without leaking Python reprs."""
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) if value else "null"


def _build_evidence_bundle(run: RunArtifacts) -> str:
    return "\n\n".join(
        (
            f"miEventId: {run.mi_event_id}",
            f"scenarioGroupId: {run.scenario_group_id}",
            "## Event detail\n" + _json_payload(run.event_detail),
            "## Step 1 scenario table\n" + _json_payload(run.step1),
            "## Step 2 validation table\n" + _json_payload(run.step2),
            "## Step 3 signpost table\n" + _json_payload(run.step3),
        )
    )


def _build_prompt(*, rubric: str, judge_ids: tuple[str, ...], run: RunArtifacts) -> str:
    return f"""You are a strict quality evaluator for a market scenario-group agent.
Prompt version: {PROMPT_VERSION}

Evaluate only the supplied evidence. Do not browse or use outside facts. A missing
event detail is missing evidence, not permission to invent facts. Use
EXTERNAL_FACT_REQUIRED when a conclusion would require external verification; such
violations must be specific but are not hard failures based on this payload alone.

Return exactly one item for each required judge ID: {", ".join(judge_ids)}.
For each item, score 1-5 and use PASS, WARN, or FAIL. Every non-pass finding must
include target_type, target_id, a short direct evidence quote or precise payload
reference, reason, suggested_fix, and fact_dependency. Do not claim facts absent
from the evidence.

Rubric:
{rubric}

Evidence bundle:
{_build_evidence_bundle(run)}
"""


async def _invoke_judge(prompt: str) -> tuple[_JudgeResponse, str]:
    """Initialize script runtime then make the project-standard structured call.

    The connector itself performs the same readiness check. Calling it here makes
    failure location explicit for manual evaluation and avoids an uninitialized
    semaphore registry in script entry points. If that script bootstrap fails, a
    tightly scoped standalone client retains the configured endpoint/model while
    intentionally foregoing connector semaphores, tracing, and usage accounting.
    """
    # These imports are intentionally deferred. Manual parser/schema inspection
    # must not instantiate the application's environment-bound Settings object.
    from apps.common.runtime.runtime import ensure_runtime_context_ready
    from apps.common.values.enums import ModelPreference
    from apps.connectors.llm.llm_client import invoke_llm_structured_output

    try:
        await ensure_runtime_context_ready()
    except Exception:
        return await _invoke_standalone_fallback(prompt)
    response = await invoke_llm_structured_output(
        _JudgeResponse,
        prompt=prompt,
        preference=ModelPreference.QUALITY,
        temperature=0,
    )
    return response.result, response.model or "unknown"


async def _invoke_standalone_fallback(prompt: str) -> tuple[_JudgeResponse, str]:
    """Manual-script-only fallback when the shared runtime cannot initialize.

    This is deliberately private and only reached before the application connector
    call. Application flows must never bypass runtime lifecycle management.
    """
    from apps.common.configs.config import get_settings

    settings = get_settings()
    model = settings.deeply_thinking_model_api_deployment_name or settings.model_api_deployment_name
    http_client = httpx.AsyncClient(
        verify=settings.http_verify,
        http2=settings.http2,
        timeout=httpx.Timeout(timeout=settings.llm_timeout_sec, connect=settings.http_connect_timeout),
        limits=httpx.Limits(
            max_connections=settings.http_max_connection,
            max_keepalive_connections=settings.http_max_keepalive,
        ),
    )
    client = AsyncOpenAI(
        base_url=settings.model_endpoint,
        api_key=settings.model_api_key,
        http_client=http_client,
        max_retries=2,
    )
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": _JudgeResponse.__name__,
                    "schema": _JudgeResponse.model_json_schema(),
                    "strict": False,
                },
            },
        )
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Standalone judge fallback returned empty content")
        return _JudgeResponse.model_validate_json(content), model
    finally:
        await http_client.aclose()


def _validate_required_items(
    response: _JudgeResponse,
    required_ids: tuple[str, ...],
) -> list[JudgeItemScore]:
    """Reject incomplete/extra rubric output instead of silently skewing averages."""
    by_id = {item.judge_id: item for item in response.items}
    expected = set(required_ids)
    actual = set(by_id)
    if actual != expected or len(by_id) != len(response.items):
        raise ValueError(
            "Judge returned an invalid rubric set: "
            f"expected={sorted(expected)}, actual={sorted(actual)}"
        )
    return [by_id[judge_id] for judge_id in required_ids]


async def judge_scenario_set(run: RunArtifacts) -> JudgeResult:
    """Run Call A for J-01~J-06 and J-11 (one bounded LLM request)."""
    rubric = """- J-01 Event grounding: core event drivers, numbers, and geography are reflected without invention.
- J-02 Baseline validity: the baseline is the most plausible path, not an edge case.
- J-03 Scenario spectrum: covers plausible optimistic/pessimistic and high-impact edge paths without duplicate narratives.
- J-04 Dimension quality: dimensions and values express event-driven branch logic.
- J-05 Internal consistency: find contradictions and scenarios that are not mutually exclusive.
- J-06 Domain/geography/market consistency: market, geography, and product context match the event.
- J-11 Clarity: a market participant can follow the stated causal chain."""
    response, model = await _invoke_judge(_build_prompt(rubric=rubric, judge_ids=_SCENARIO_JUDGE_IDS, run=run))
    return JudgeResult(
        items=_validate_required_items(response, _SCENARIO_JUDGE_IDS),
        model=model,
        prompt_version=PROMPT_VERSION,
    )


async def judge_signposts(run: RunArtifacts) -> JudgeResult:
    """Run Call B for J-07~J-10 (one bounded LLM request)."""
    rubric = """- J-07 Signpost relevance: each signpost directly connects to its event and owning scenario.
- J-08 Signpost discriminativeness: signposts distinguish the owning scenario from alternatives.
- J-09 Observability/temporal relevance: wording is observable via news, indicators, or official releases and fits the horizon.
- J-10 Causal direction/strength: direction, strength, and reason coherently affect scenario probability."""
    response, model = await _invoke_judge(_build_prompt(rubric=rubric, judge_ids=_SIGNPOST_JUDGE_IDS, run=run))
    return JudgeResult(
        items=_validate_required_items(response, _SIGNPOST_JUDGE_IDS),
        model=model,
        prompt_version=PROMPT_VERSION,
    )
