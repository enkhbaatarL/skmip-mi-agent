from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


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
from apps.agents.model_parameter_agent.scripts.benchmark_llm_call_variants import (
    Variant,
    _invoke_variant,
    _usage_summary,
)
from apps.agents.model_parameter_agent.scripts.evaluate_proposals import (
    _evaluate_scenario,
)
from apps.common.configs.config import get_settings
from apps.connectors.llm.llm_client import LLMStructuredResult


REPORT_DIR = Path(__file__).resolve().parents[1] / "reports"
STEP_NAMES = {
    LLMCandidateValidationResponse: "Step1.5 candidate validation",
    LLMSlotProposalResponse: "Step2 slot proposal",
    LLMValueProposalResponse: "Step3 value proposal",
}
REASONING_VARIANTS: tuple[Variant, ...] = (
    Variant("chat_nonstream_reasoning_default_cache_key", "chat", "nonstream", None, True),
    Variant("chat_nonstream_reasoning_low_cache_key", "chat", "nonstream", "low", True),
    Variant("chat_nonstream_reasoning_none_cache_key", "chat", "nonstream", "none", True),
)
EXPECTED_PARAMETER_NAMES = {"LiqUtilAdjustment", "LiqProdAdjustment", "PowerMix"}


@dataclass(frozen=True)
class RunSpec:
    scenario_id: int
    repeat_index: int
    variant: Variant


def _mean(values: list[float]) -> float | None:
    return round(statistics.mean(values), 3) if values else None


def _safe_float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _final_data(record: dict[str, Any]) -> dict[str, Any]:
    return (record.get("final_response") or {}).get("data") or {}


def _proposal_parameters(record: dict[str, Any]) -> list[dict[str, Any]]:
    return _final_data(record).get("proposalParameters") or []


def _values_for_parameter(record: dict[str, Any], parameter_name: str) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for parameter in _proposal_parameters(record):
        if parameter.get("parameterName") == parameter_name:
            values.extend(parameter.get("values") or [])
    return values


def _all_rationale_text(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for parameter in _proposal_parameters(record):
        parts.append(str(parameter.get("rationale") or ""))
        for value in parameter.get("values") or []:
            parts.append(str(value.get("rationale") or ""))
    return "\n".join(part for part in parts if part)


def _parameter_value_summary(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for parameter in _proposal_parameters(record):
        name = str(parameter.get("parameterName") or "")
        values = parameter.get("values") or []
        proposed_values = [
            number
            for number in (_safe_float(value.get("proposedValue")) for value in values)
            if number is not None
        ]
        summary[name] = {
            "value_count": len(values),
            "avg_proposed_value": _mean(proposed_values),
            "min_proposed_value": round(min(proposed_values), 6) if proposed_values else None,
            "max_proposed_value": round(max(proposed_values), 6) if proposed_values else None,
        }
    return summary


def _signature(record: dict[str, Any]) -> str:
    comparable: list[dict[str, Any]] = []
    for parameter in _proposal_parameters(record):
        comparable.append(
            {
                "parameterName": parameter.get("parameterName"),
                "values": [
                    {
                        "coordinates": {
                            key: value
                            for key, value in cell.items()
                            if key not in {"basecaseValue", "proposedValue", "rationale"}
                        },
                        "basecaseValue": cell.get("basecaseValue"),
                        "proposedValue": cell.get("proposedValue"),
                    }
                    for cell in parameter.get("values") or []
                ],
            },
        )
    return json.dumps(comparable, ensure_ascii=False, sort_keys=True, default=str)


def _keyword_coverage(text: str, keywords: list[tuple[str, ...]]) -> tuple[int, list[str]]:
    matched = 0
    missing: list[str] = []
    lowered = text.lower()
    for group in keywords:
        if any(keyword.lower() in lowered for keyword in group):
            matched += 1
        else:
            missing.append("/".join(group))
    return matched, missing


def _quality_assessment(record: dict[str, Any]) -> dict[str, Any]:
    scenario_id = int(record["scenario_id"])
    parameter_names = {str(item.get("parameterName") or "") for item in _proposal_parameters(record)}
    issues: list[str] = []
    score = 0

    if parameter_names == EXPECTED_PARAMETER_NAMES:
        score += 25
    else:
        missing = sorted(EXPECTED_PARAMETER_NAMES - parameter_names)
        extra = sorted(parameter_names - EXPECTED_PARAMETER_NAMES)
        issues.append(f"parameter mismatch missing={missing} extra={extra}")

    liq_util_values = _values_for_parameter(record, "LiqUtilAdjustment")
    util_ratios: list[float] = []
    util_direction_ok = bool(liq_util_values)
    for value in liq_util_values:
        proposed = _safe_float(value.get("proposedValue"))
        basecase = _safe_float(value.get("basecaseValue"))
        if proposed is None or basecase is None or basecase <= 0:
            continue
        util_ratios.append(proposed / basecase)
        if not (0 <= proposed < basecase):
            util_direction_ok = False
    if util_direction_ok and util_ratios:
        score += 15
    else:
        issues.append("LiqUtilAdjustment should reduce positive basecase utilization")

    liq_prod_values = _values_for_parameter(record, "LiqProdAdjustment")
    prod_values = [
        number
        for number in (_safe_float(value.get("proposedValue")) for value in liq_prod_values)
        if number is not None
    ]
    if prod_values and all(0 < value < 1.0 for value in prod_values):
        score += 15
    else:
        issues.append("LiqProdAdjustment proposed values should be positive monthly Mt-scale values under 1.0")

    power_values = _values_for_parameter(record, "PowerMix")
    power_ok = False
    if scenario_id == 129:
        power_numbers = [
            number
            for number in (_safe_float(value.get("proposedValue")) for value in power_values)
            if number is not None
        ]
        power_ok = bool(power_numbers) and all(abs(value) <= 0.005 for value in power_numbers)
        if not power_ok:
            issues.append("scenario 129 PowerMix should reflect 100% reduction toward zero")
    elif scenario_id == 130:
        ratios: list[float] = []
        for value in power_values:
            proposed = _safe_float(value.get("proposedValue"))
            basecase = _safe_float(value.get("basecaseValue"))
            if proposed is not None and basecase and basecase > 0:
                ratios.append(proposed / basecase)
        power_ok = bool(ratios) and all(0.35 <= ratio <= 0.65 for ratio in ratios)
        if not power_ok:
            issues.append("scenario 130 PowerMix should reflect about 50% reduction")
    if power_ok:
        score += 15

    if scenario_id == 129:
        value_count_ok = (
            len(liq_util_values) >= 1
            and len(liq_prod_values) >= 1
            and len(power_values) >= 1
            and len(power_values) <= 2
        )
        keywords = [
            ("낮", "low"),
            ("100", "전량", "완전"),
            ("대체", "alternative"),
            ("3개월", "제한", "단계", "회복"),
        ]
    else:
        value_count_ok = (
            len(liq_util_values) >= 4
            and len(liq_prod_values) >= 4
            and len(power_values) >= 1
        )
        keywords = [
            ("중간", "medium"),
            ("50", "절반"),
            ("대체", "alternative"),
            ("완만", "1년", "해소", "하반기"),
        ]
    if value_count_ok:
        score += 15
    else:
        issues.append(
            "value cell coverage does not match expected scenario duration/intensity pattern",
        )

    rationale_text = _all_rationale_text(record)
    keyword_score, missing_keywords = _keyword_coverage(rationale_text, keywords)
    rationale_nonempty = len(rationale_text) >= 200
    if rationale_nonempty:
        score += 5
    else:
        issues.append("rationale text is too short")
    score += round(10 * keyword_score / len(keywords))
    if missing_keywords:
        issues.append(f"rationale missing expected context keywords={missing_keywords}")

    return {
        "score": min(score, 100),
        "issues": issues,
        "parameter_names": sorted(parameter_names),
        "value_counts": {
            "LiqUtilAdjustment": len(liq_util_values),
            "LiqProdAdjustment": len(liq_prod_values),
            "PowerMix": len(power_values),
        },
        "util_ratio_avg": _mean(util_ratios),
        "rationale_chars": len(rationale_text),
        "rationale_keyword_matched": keyword_score,
        "rationale_keyword_total": len(keywords),
    }


async def _run_spec(spec: RunSpec, *, max_candidates: int, max_retries: int) -> dict[str, Any]:
    step_records: list[dict[str, Any]] = []

    async def invoke_structured(
        *,
        output_schema: type[Any],
        messages: list[dict[str, str]],
        model_name: str | None,
    ) -> LLMStructuredResult[Any]:
        step = STEP_NAMES.get(output_schema, output_schema.__name__)
        captured_step = {
            "scenario_id": spec.scenario_id,
            "step": step,
            "messages": messages,
        }
        record = await _invoke_variant(
            captured_step=captured_step,
            variant=spec.variant,
            repeat_index=spec.repeat_index,
            max_retries=max_retries,
        )
        step_records.append(record)
        if not record.get("success"):
            message = (
                f"{spec.variant.name} scenario={spec.scenario_id} step={step} failed: "
                f"{record.get('error_type')} {record.get('error')}"
            )
            raise RuntimeError(message)
        return LLMStructuredResult(
            result=output_schema.model_validate(record["structured_result_json"]),
            usage=None,
        )

    original = nodes._invoke_structured
    nodes._invoke_structured = invoke_structured
    started = time.perf_counter()
    try:
        result = await _evaluate_scenario(
            spec.scenario_id,
            max_candidates=max_candidates,
            allow_llm_fallback=False,
        )
    finally:
        nodes._invoke_structured = original

    result["variant"] = spec.variant.name
    result["reasoning"] = spec.variant.reasoning or "default"
    result["repeat_index"] = spec.repeat_index
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    result["step_records"] = step_records
    result["quality"] = _quality_assessment(result)
    result["parameter_value_summary"] = _parameter_value_summary(result)
    result["value_signature"] = _signature(result)
    quality = result["quality"]
    print(
        "REASONING_QUALITY_RUN",
        f"scenario={spec.scenario_id}",
        f"repeat={spec.repeat_index}",
        f"reasoning={result['reasoning']}",
        f"elapsed={result['elapsed_seconds']}",
        f"score={quality['score']}",
        f"issues={len(quality['issues'])}",
        flush=True,
    )
    return result


def _aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(int(record["scenario_id"]), str(record["reasoning"]))].append(record)
    rows: list[dict[str, Any]] = []
    for (scenario_id, reasoning), items in sorted(groups.items()):
        elapsed = [float(item["elapsed_seconds"]) for item in items]
        scores = [float((item.get("quality") or {}).get("score") or 0) for item in items]
        step_records = [
            step
            for item in items
            for step in item.get("step_records") or []
        ]
        cached_tokens = sum(
            int((_usage_summary(step.get("usage")).get("cached_tokens") or 0))
            for step in step_records
        )
        reasoning_tokens = sum(
            int((_usage_summary(step.get("usage")).get("reasoning_tokens") or 0))
            for step in step_records
        )
        rows.append(
            {
                "scenario_id": scenario_id,
                "reasoning": reasoning,
                "runs": len(items),
                "avg_elapsed_seconds": _mean(elapsed),
                "min_elapsed_seconds": round(min(elapsed), 3),
                "max_elapsed_seconds": round(max(elapsed), 3),
                "avg_quality_score": _mean(scores),
                "min_quality_score": round(min(scores), 3),
                "max_quality_score": round(max(scores), 3),
                "unique_value_signature_count": len({item.get("value_signature") for item in items}),
                "total_cached_tokens": cached_tokens,
                "total_reasoning_tokens": reasoning_tokens,
            },
        )
    return rows


def _write_markdown(
    *,
    path: Path,
    metadata: dict[str, Any],
    records: list[dict[str, Any]],
    summary: list[dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Model Parameter Agent Reasoning Quality Benchmark",
        "",
        f"- generated_at: `{metadata['generated_at']}`",
        f"- scenario_ids: `{metadata['scenario_ids']}`",
        f"- repeats_per_reasoning: `{metadata['repeats']}`",
        f"- fixed_api: `chat.completions`",
        f"- fixed_stream: `nonstream`",
        f"- fixed_cache_key: `true`",
        f"- max_retries: `{metadata['max_retries']}`",
        f"- llm_timeout_sec: `{metadata['llm_timeout_sec']}`",
        "- note: API/stream/cache 조건을 고정하고 reasoning만 default/low/none으로 변경했습니다.",
        "- note: 품질 점수는 scenario dimension과 최종 proposal의 parameter/value/rationale을 대조한 휴리스틱입니다. 자동 점수이므로 도메인 최종 판정은 사람이 확인해야 합니다.",
        "",
        "## Summary By Scenario And Reasoning",
        "",
        "| scenario_id | reasoning | runs | avg_elapsed_s | min_s | max_s | avg_quality | min_quality | max_quality | unique_value_signatures | cached_tokens | reasoning_tokens |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            "| {scenario_id} | {reasoning} | {runs} | {avg_elapsed} | {min_elapsed} | {max_elapsed} | {avg_quality} | {min_quality} | {max_quality} | {unique} | {cached} | {reasoning_tokens} |".format(
                scenario_id=row["scenario_id"],
                reasoning=row["reasoning"],
                runs=row["runs"],
                avg_elapsed=row["avg_elapsed_seconds"],
                min_elapsed=row["min_elapsed_seconds"],
                max_elapsed=row["max_elapsed_seconds"],
                avg_quality=row["avg_quality_score"],
                min_quality=row["min_quality_score"],
                max_quality=row["max_quality_score"],
                unique=row["unique_value_signature_count"],
                cached=row["total_cached_tokens"],
                reasoning_tokens=row["total_reasoning_tokens"],
            ),
        )

    lines.extend(
        [
            "",
            "## Run Detail",
            "",
            "| scenario_id | repeat | reasoning | elapsed_s | quality | mapping_ok | selected_ok | routing | parameter | slot | value | selected_params | value_counts | issues |",
            "|---:|---:|---|---:|---:|---|---|---|---|---|---|---|---|---|",
        ],
    )
    for record in records:
        quality = record.get("quality") or {}
        step_summary = record.get("step_summary") or {}
        value_summary = record.get("parameter_value_summary") or {}
        lines.append(
            "| {scenario_id} | {repeat} | {reasoning} | {elapsed} | {quality_score} | {mapping_ok} | {selected_ok} | {routing} | {parameter_status} | {slot_status} | {value_status} | {params} | `{value_counts}` | {issues} |".format(
                scenario_id=record.get("scenario_id"),
                repeat=record.get("repeat_index"),
                reasoning=record.get("reasoning"),
                elapsed=record.get("elapsed_seconds"),
                quality_score=quality.get("score"),
                mapping_ok=record.get("mapping_ok"),
                selected_ok=record.get("selected_ok"),
                routing=record.get("routing_status"),
                parameter_status=step_summary.get("parameter_status"),
                slot_status=step_summary.get("slot_status"),
                value_status=step_summary.get("value_status"),
                params=", ".join(quality.get("parameter_names") or []),
                value_counts=json.dumps(
                    {
                        name: item.get("value_count")
                        for name, item in value_summary.items()
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                issues="<br>".join(quality.get("issues") or []),
            ),
        )

    lines.extend(
        [
            "",
            "## Parameter Value Summary",
            "",
            "| scenario_id | repeat | reasoning | parameter | value_count | avg_proposed | min_proposed | max_proposed |",
            "|---:|---:|---|---|---:|---:|---:|---:|",
        ],
    )
    for record in records:
        for parameter_name, item in sorted((record.get("parameter_value_summary") or {}).items()):
            lines.append(
                "| {scenario_id} | {repeat} | {reasoning} | {parameter} | {count} | {avg} | {min_value} | {max_value} |".format(
                    scenario_id=record.get("scenario_id"),
                    repeat=record.get("repeat_index"),
                    reasoning=record.get("reasoning"),
                    parameter=parameter_name,
                    count=item.get("value_count"),
                    avg=item.get("avg_proposed_value"),
                    min_value=item.get("min_proposed_value"),
                    max_value=item.get("max_proposed_value"),
                ),
            )

    lines.extend(
        [
            "",
            "## Step Call Detail",
            "",
            "| scenario_id | repeat | reasoning | step | elapsed_s | cached_tokens | reasoning_tokens | total_tokens |",
            "|---:|---:|---|---|---:|---:|---:|---:|",
        ],
    )
    for record in records:
        for step in record.get("step_records") or []:
            usage = _usage_summary(step.get("usage"))
            lines.append(
                "| {scenario_id} | {repeat} | {reasoning} | {step} | {elapsed} | {cached} | {reasoning_tokens} | {total} |".format(
                    scenario_id=record.get("scenario_id"),
                    repeat=record.get("repeat_index"),
                    reasoning=record.get("reasoning"),
                    step=step.get("step"),
                    elapsed=step.get("elapsed_seconds"),
                    cached=usage.get("cached_tokens"),
                    reasoning_tokens=usage.get("reasoning_tokens"),
                    total=usage.get("total_tokens"),
                ),
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run(args: argparse.Namespace) -> tuple[Path, Path]:
    settings = get_settings()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    partial_path = REPORT_DIR / f"model_parameter_reasoning_quality_benchmark_{generated_at}.partial.json"
    records: list[dict[str, Any]] = []

    for repeat_index in range(1, args.repeats + 1):
        for scenario_id in args.scenario_ids:
            for variant in REASONING_VARIANTS:
                record = await _run_spec(
                    RunSpec(
                        scenario_id=int(scenario_id),
                        repeat_index=repeat_index,
                        variant=variant,
                    ),
                    max_candidates=args.max_candidates,
                    max_retries=args.max_retries,
                )
                records.append(record)
                partial_path.write_text(
                    json.dumps(records, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )

    summary = _aggregate(records)
    metadata = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scenario_ids": [int(item) for item in args.scenario_ids],
        "repeats": args.repeats,
        "max_candidates": args.max_candidates,
        "max_retries": args.max_retries,
        "llm_timeout_sec": settings.llm_timeout_sec,
        "variants": [variant.__dict__ for variant in REASONING_VARIANTS],
    }
    report = {
        "metadata": metadata,
        "summary": summary,
        "records": records,
    }
    json_path = REPORT_DIR / f"model_parameter_reasoning_quality_benchmark_{generated_at}.json"
    md_path = REPORT_DIR / f"model_parameter_reasoning_quality_benchmark_{generated_at}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _write_markdown(
        path=md_path,
        metadata=metadata,
        records=records,
        summary=summary,
    )
    partial_path.unlink(missing_ok=True)
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark reasoning default/low/none for speed and final proposal quality.",
    )
    parser.add_argument("--scenario-ids", nargs="+", type=int, default=[129, 130])
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-candidates", type=int, default=30)
    parser.add_argument("--max-retries", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    json_path, md_path = asyncio.run(run(parse_args()))
    print(f"JSON_REPORT {json_path}")
    print(f"MD_REPORT {md_path}")


if __name__ == "__main__":
    main()
