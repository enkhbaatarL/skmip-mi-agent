from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[3]
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
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMCandidateValidationResponse,
    LLMSlotProposalResponse,
    LLMValueProposalResponse,
)
from tests.manual.model_parameter_agent.benchmark_llm_call_variants import (
    Variant,
    _invoke_variant,
    _usage_summary,
)
from tests.manual.model_parameter_agent.evaluate_proposals import (
    _evaluate_scenario,
)
from apps.common.configs.config import get_settings
from apps.connectors.llm.llm_client import LLMStructuredResult


REPORT_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"
STEP_NAMES = {
    LLMCandidateValidationResponse: "Step1.5 candidate validation",
    LLMSlotProposalResponse: "Step2 slot proposal",
    LLMValueProposalResponse: "Step3 value proposal",
}
QUALITY_VARIANTS: tuple[Variant, ...] = (
    Variant("chat_nonstream_default_no_cache_key", "chat", "nonstream", None, False),
    Variant("chat_nonstream_reasoning_none_cache_key", "chat", "nonstream", "none", True),
    Variant("chat_nonstream_reasoning_low_cache_key", "chat", "nonstream", "low", True),
    Variant("responses_stream_reasoning_none_cache_key", "responses", "stream", "none", True),
)


@dataclass(frozen=True)
class RunTarget:
    scenario_id: int
    variant: Variant


def _selected_adjustments(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in result.get("parameter_adjustments") or []
        if item.get("selected", True) is not False
    ]


def _selected_slots(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [slot for slot in slots if slot.get("selected", True) is not False]


def _proposal_parameters(final_response: dict[str, Any]) -> list[dict[str, Any]]:
    return ((final_response.get("data") or {}).get("proposalParameters") or [])


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _slot_signature(slot: dict[str, Any]) -> str:
    return _compact_json(
        {
            "candidate_key": slot.get("candidate_key"),
            "slot_axes": sorted(
                [
                    {
                        "axis_name": axis.get("axis_name"),
                        "axis_value": axis.get("axis_value"),
                    }
                    for axis in slot.get("slot_axes") or []
                ],
                key=lambda item: str(item.get("axis_name") or ""),
            ),
        },
    )


def _value_signature(adjustment: dict[str, Any], cell: dict[str, Any]) -> str:
    return _compact_json(
        {
            "candidate_key": adjustment.get("candidate_key"),
            "coordinates": cell.get("coordinates") or {},
            "operation": cell.get("operation"),
        },
    )


def _value_records(result: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for adjustment in _selected_adjustments(result):
        for cell in adjustment.get("value_grid") or []:
            signature = _value_signature(adjustment, cell)
            records[signature] = {
                "candidate_key": adjustment.get("candidate_key"),
                "parameter_name": adjustment.get("parameter_name"),
                "coordinates": cell.get("coordinates") or {},
                "operation": cell.get("operation"),
                "proposed_value": cell.get("proposed_value"),
                "basecase_value": cell.get("basecase_value"),
                "rationale_ko": cell.get("rationale_ko") or "",
            }
    return records


def _rationale_text(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for adjustment in _selected_adjustments(record.get("result") or {}):
        parts.append(str(adjustment.get("parameter_selection_rationale_ko") or ""))
        for cell in adjustment.get("value_grid") or []:
            parts.append(str(cell.get("rationale_ko") or ""))
    return "\n".join(part for part in parts if part)


def _output_summary(record: dict[str, Any]) -> dict[str, Any]:
    final_response = record.get("final_response") or {}
    result = record.get("result") or {}
    slots = record.get("parameter_slots") or []
    selected_adjustments = _selected_adjustments(result)
    selected_slots = _selected_slots(slots)
    proposal_parameters = _proposal_parameters(final_response)
    value_cell_count = sum(len(item.get("value_grid") or []) for item in selected_adjustments)
    return {
        "scenario_id": record.get("scenario_id"),
        "variant": record.get("variant"),
        "mapping_ok": record.get("mapping_ok"),
        "selected_ok": record.get("selected_ok"),
        "routing_status": record.get("routing_status"),
        "parameter_status": (record.get("step_summary") or {}).get("parameter_status"),
        "slot_status": (record.get("step_summary") or {}).get("slot_status"),
        "basecase_status": (record.get("step_summary") or {}).get("basecase_status"),
        "value_status": (record.get("step_summary") or {}).get("value_status"),
        "proposal_id": (final_response.get("data") or {}).get("modelParamProposalId"),
        "proposal_parameter_names": [
            item.get("parameterName") for item in proposal_parameters
        ],
        "selected_candidate_keys": [
            item.get("candidate_key") for item in selected_adjustments
        ],
        "selected_parameter_names": [
            item.get("parameter_name") for item in selected_adjustments
        ],
        "selected_slot_count": len(selected_slots),
        "value_cell_count": value_cell_count,
        "warning_count": len((result.get("validation_warnings") or [])),
        "value_signature": record.get("value_signature"),
    }


def _compare_to_baseline(
    *,
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    baseline_result = baseline.get("result") or {}
    current_result = current.get("result") or {}
    baseline_slots = {_slot_signature(slot) for slot in _selected_slots(baseline.get("parameter_slots") or [])}
    current_slots = {_slot_signature(slot) for slot in _selected_slots(current.get("parameter_slots") or [])}
    baseline_values = _value_records(baseline_result)
    current_values = _value_records(current_result)

    baseline_keys = {
        str(item.get("candidate_key") or "")
        for item in _selected_adjustments(baseline_result)
    }
    current_keys = {
        str(item.get("candidate_key") or "")
        for item in _selected_adjustments(current_result)
    }
    baseline_parameters = {
        str(item.get("parameter_name") or "")
        for item in _selected_adjustments(baseline_result)
    }
    current_parameters = {
        str(item.get("parameter_name") or "")
        for item in _selected_adjustments(current_result)
    }

    common_value_keys = sorted(set(baseline_values) & set(current_values))
    changed_values: list[dict[str, Any]] = []
    changed_rationales = 0
    rationale_similarities: list[float] = []
    for key in common_value_keys:
        left = baseline_values[key]
        right = current_values[key]
        if left.get("proposed_value") != right.get("proposed_value"):
            changed_values.append(
                {
                    "signature": key,
                    "baseline_value": left.get("proposed_value"),
                    "current_value": right.get("proposed_value"),
                    "coordinates": right.get("coordinates"),
                    "parameter_name": right.get("parameter_name"),
                },
            )
        left_rationale = str(left.get("rationale_ko") or "")
        right_rationale = str(right.get("rationale_ko") or "")
        if left_rationale != right_rationale:
            changed_rationales += 1
        if left_rationale or right_rationale:
            rationale_similarities.append(
                SequenceMatcher(None, left_rationale, right_rationale).ratio(),
            )

    full_rationale_similarity = SequenceMatcher(
        None,
        _rationale_text(baseline),
        _rationale_text(current),
    ).ratio()

    return {
        "scenario_id": current.get("scenario_id"),
        "baseline_variant": baseline.get("variant"),
        "variant": current.get("variant"),
        "same_selected_candidate_keys": baseline_keys == current_keys,
        "added_candidate_keys": sorted(current_keys - baseline_keys),
        "removed_candidate_keys": sorted(baseline_keys - current_keys),
        "same_selected_parameter_names": baseline_parameters == current_parameters,
        "added_parameter_names": sorted(current_parameters - baseline_parameters),
        "removed_parameter_names": sorted(baseline_parameters - current_parameters),
        "same_selected_slots": baseline_slots == current_slots,
        "added_slot_count": len(current_slots - baseline_slots),
        "removed_slot_count": len(baseline_slots - current_slots),
        "same_value_cells": set(baseline_values) == set(current_values),
        "added_value_cell_count": len(set(current_values) - set(baseline_values)),
        "removed_value_cell_count": len(set(baseline_values) - set(current_values)),
        "common_value_cell_count": len(common_value_keys),
        "changed_proposed_value_count": len(changed_values),
        "changed_proposed_value_examples": changed_values[:5],
        "changed_cell_rationale_count": changed_rationales,
        "avg_cell_rationale_similarity": (
            round(sum(rationale_similarities) / len(rationale_similarities), 3)
            if rationale_similarities
            else None
        ),
        "full_rationale_similarity": round(full_rationale_similarity, 3),
        "same_value_signature": baseline.get("value_signature") == current.get("value_signature"),
    }


async def _run_target(
    target: RunTarget,
    *,
    max_retries: int,
) -> dict[str, Any]:
    step_records: list[dict[str, Any]] = []

    async def invoke_structured(
        *,
        output_schema: type[Any],
        messages: list[dict[str, str]],
        model_name: str | None,
    ) -> LLMStructuredResult[Any]:
        step = STEP_NAMES.get(output_schema, output_schema.__name__)
        captured_step = {
            "scenario_id": target.scenario_id,
            "step": step,
            "messages": messages,
        }
        record = await _invoke_variant(
            captured_step=captured_step,
            variant=target.variant,
            repeat_index=1,
            max_retries=max_retries,
        )
        step_records.append(record)
        if not record.get("success"):
            message = (
                f"{target.variant.name} {target.scenario_id} {step} failed: "
                f"{record.get('error_type')} {record.get('error')}"
            )
            raise RuntimeError(message)
        structured_result = output_schema.model_validate(record["structured_result_json"])
        return LLMStructuredResult(result=structured_result, usage=None)

    original = nodes._invoke_structured
    nodes._invoke_structured = invoke_structured
    started = time.perf_counter()
    try:
        result = await _evaluate_scenario(target.scenario_id)
    finally:
        nodes._invoke_structured = original
    result["variant"] = target.variant.name
    result["variant_config"] = target.variant.__dict__
    result["elapsed_seconds"] = round(time.perf_counter() - started, 3)
    result["step_records"] = step_records
    result["output_summary"] = _output_summary(result)
    print(
        "QUALITY_RUN",
        f"scenario={target.scenario_id}",
        f"variant={target.variant.name}",
        f"elapsed={result['elapsed_seconds']}",
        f"mapping_ok={result.get('mapping_ok')}",
        f"selected_ok={result.get('selected_ok')}",
        f"value_status={(result.get('step_summary') or {}).get('value_status')}",
        f"selected_params={result['output_summary'].get('selected_parameter_names')}",
        f"value_cells={result['output_summary'].get('value_cell_count')}",
        flush=True,
    )
    return result


def _write_markdown(
    *,
    path: Path,
    metadata: dict[str, Any],
    records: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Model Parameter Agent Reasoning Output Comparison",
        "",
        f"- generated_at: `{metadata['generated_at']}`",
        f"- scenario_ids: `{metadata['scenario_ids']}`",
        f"- variants: `{[item['name'] for item in metadata['variants']]}`",
        f"- llm_timeout_sec: `{metadata['llm_timeout_sec']}`",
        "- note: 각 variant를 실제 agent graph에 적용해 Step1.5/Step2/Step3 전체 pipeline 결과를 비교했습니다.",
        "",
        "## Output Quality Summary",
        "",
        "| scenario_id | variant | elapsed_s | mapping_ok | selected_ok | routing | parameter | slot | value | selected_params | slot_count | value_cells | warnings |",
        "|---:|---|---:|---|---|---|---|---|---|---|---:|---:|---:|",
    ]
    for record in records:
        summary = record["output_summary"]
        step_summary = record.get("step_summary") or {}
        lines.append(
            "| {scenario_id} | {variant} | {elapsed:.3f} | {mapping_ok} | {selected_ok} | {routing} | {parameter_status} | {slot_status} | {value_status} | {params} | {slots} | {cells} | {warnings} |".format(
                scenario_id=record.get("scenario_id"),
                variant=record.get("variant"),
                elapsed=float(record.get("elapsed_seconds") or 0.0),
                mapping_ok=record.get("mapping_ok"),
                selected_ok=record.get("selected_ok"),
                routing=record.get("routing_status"),
                parameter_status=step_summary.get("parameter_status"),
                slot_status=step_summary.get("slot_status"),
                value_status=step_summary.get("value_status"),
                params=", ".join(summary.get("selected_parameter_names") or []),
                slots=summary.get("selected_slot_count"),
                cells=summary.get("value_cell_count"),
                warnings=summary.get("warning_count"),
            ),
        )

    lines.extend(
        [
            "",
            "## Diff Against Current Baseline",
            "",
            "| scenario_id | variant | same_params | same_slots | same_value_cells | changed_values | added_cells | removed_cells | cell_rationale_changed | avg_cell_rationale_similarity | full_rationale_similarity |",
            "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|",
        ],
    )
    for comparison in comparisons:
        lines.append(
            "| {scenario_id} | {variant} | {same_params} | {same_slots} | {same_cells} | {changed_values} | {added_cells} | {removed_cells} | {changed_rationale} | {avg_cell} | {full} |".format(
                scenario_id=comparison["scenario_id"],
                variant=comparison["variant"],
                same_params=comparison["same_selected_parameter_names"],
                same_slots=comparison["same_selected_slots"],
                same_cells=comparison["same_value_cells"],
                changed_values=comparison["changed_proposed_value_count"],
                added_cells=comparison["added_value_cell_count"],
                removed_cells=comparison["removed_value_cell_count"],
                changed_rationale=comparison["changed_cell_rationale_count"],
                avg_cell=comparison["avg_cell_rationale_similarity"],
                full=comparison["full_rationale_similarity"],
            ),
        )

    lines.extend(["", "## Changed Proposed Value Examples", ""])
    examples_found = False
    for comparison in comparisons:
        examples = comparison.get("changed_proposed_value_examples") or []
        if not examples:
            continue
        examples_found = True
        lines.append(
            f"### scenario_id={comparison['scenario_id']} `{comparison['variant']}`",
        )
        lines.append("")
        lines.append("| parameter | coordinates | baseline | current |")
        lines.append("|---|---|---:|---:|")
        for example in examples:
            lines.append(
                "| {parameter} | `{coordinates}` | {baseline} | {current} |".format(
                    parameter=example.get("parameter_name"),
                    coordinates=_compact_json(example.get("coordinates") or {}),
                    baseline=example.get("baseline_value"),
                    current=example.get("current_value"),
                ),
            )
        lines.append("")
    if not examples_found:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Step Call Summary",
            "",
            "| scenario_id | variant | step | elapsed_s | cached_tokens | reasoning_tokens | total_tokens |",
            "|---:|---|---|---:|---:|---:|---:|",
        ],
    )
    for record in records:
        for step_record in record.get("step_records") or []:
            usage = _usage_summary(step_record.get("usage"))
            lines.append(
                "| {scenario_id} | {variant} | {step} | {elapsed} | {cached} | {reasoning} | {total} |".format(
                    scenario_id=record.get("scenario_id"),
                    variant=record.get("variant"),
                    step=step_record.get("step"),
                    elapsed=step_record.get("elapsed_seconds"),
                    cached=usage.get("cached_tokens"),
                    reasoning=usage.get("reasoning_tokens"),
                    total=usage.get("total_tokens"),
                ),
            )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run(args: argparse.Namespace) -> tuple[Path, Path]:
    settings = get_settings()
    scenario_ids = tuple(args.scenario_ids)
    records: list[dict[str, Any]] = []
    for scenario_id in scenario_ids:
        for variant in QUALITY_VARIANTS:
            records.append(
                await _run_target(
                    RunTarget(scenario_id=scenario_id, variant=variant),
                    max_retries=args.max_retries,
                ),
            )

    baseline_by_scenario = {
        record["scenario_id"]: record
        for record in records
        if record["variant"] == "chat_nonstream_default_no_cache_key"
    }
    comparisons: list[dict[str, Any]] = []
    for record in records:
        if record["variant"] == "chat_nonstream_default_no_cache_key":
            continue
        baseline = baseline_by_scenario.get(record["scenario_id"])
        if baseline is None:
            continue
        comparisons.append(_compare_to_baseline(baseline=baseline, current=record))

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    metadata = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scenario_ids": list(scenario_ids),
        "max_retries": args.max_retries,
        "llm_timeout_sec": settings.llm_timeout_sec,
        "variants": [variant.__dict__ for variant in QUALITY_VARIANTS],
    }
    report = {
        "metadata": metadata,
        "records": records,
        "comparisons_against_baseline": comparisons,
    }
    json_path = REPORT_DIR / f"model_parameter_reasoning_output_comparison_{generated_at}.json"
    md_path = REPORT_DIR / f"model_parameter_reasoning_output_comparison_{generated_at}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _write_markdown(
        path=md_path,
        metadata=metadata,
        records=records,
        comparisons=comparisons,
    )
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare model_parameter_agent final outputs across reasoning variants.",
    )
    parser.add_argument("--scenario-ids", nargs="+", type=int, default=[129, 130])
    parser.add_argument("--max-retries", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    json_path, md_path = asyncio.run(run(parse_args()))
    print(f"JSON_REPORT {json_path}")
    print(f"MD_REPORT {md_path}")


if __name__ == "__main__":
    main()
