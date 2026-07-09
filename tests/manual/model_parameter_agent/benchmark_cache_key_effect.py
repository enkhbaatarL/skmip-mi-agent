from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
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

from tests.manual.model_parameter_agent.benchmark_llm_call_variants import (
    Variant,
)
from tests.manual.model_parameter_agent.benchmark_reasoning_quality import (
    RunSpec,
    _mean,
    _run_spec,
    _usage_summary,
)
from apps.common.configs.config import get_settings


REPORT_DIR = ROOT_DIR / "tests" / "reports" / "model_parameter_agent"
CACHE_KEY_VARIANTS: tuple[Variant, ...] = (
    Variant("chat_nonstream_reasoning_low_no_cache_key", "chat", "nonstream", "low", False),
    Variant("chat_nonstream_reasoning_low_cache_key", "chat", "nonstream", "low", True),
)


def _cache_label(cache_key: bool) -> str:
    return "cache_key=true" if cache_key else "cache_key=false"


def _step_usage_totals(records: list[dict[str, Any]]) -> dict[str, int]:
    step_records = [step for record in records for step in record.get("step_records") or []]
    return {
        "step_calls": len(step_records),
        "cache_hit_steps": sum(
            1
            for step in step_records
            if int(_usage_summary(step.get("usage")).get("cached_tokens") or 0) > 0
        ),
        "cached_tokens": sum(
            int(_usage_summary(step.get("usage")).get("cached_tokens") or 0)
            for step in step_records
        ),
        "reasoning_tokens": sum(
            int(_usage_summary(step.get("usage")).get("reasoning_tokens") or 0)
            for step in step_records
        ),
        "total_tokens": sum(
            int(_usage_summary(step.get("usage")).get("total_tokens") or 0)
            for step in step_records
        ),
    }


def _aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[bool, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[bool(record["cache_key"])].append(record)

    rows: list[dict[str, Any]] = []
    for cache_key, items in sorted(groups.items()):
        elapsed = [float(item["elapsed_seconds"]) for item in items]
        scores = [float((item.get("quality") or {}).get("score") or 0) for item in items]
        usage = _step_usage_totals(items)
        rows.append(
            {
                "cache_key": cache_key,
                "label": _cache_label(cache_key),
                "runs": len(items),
                "avg_elapsed_seconds": _mean(elapsed),
                "min_elapsed_seconds": round(min(elapsed), 3),
                "max_elapsed_seconds": round(max(elapsed), 3),
                "avg_quality_score": _mean(scores),
                "min_quality_score": round(min(scores), 3),
                "max_quality_score": round(max(scores), 3),
                "unique_value_signature_count": len({item.get("value_signature") for item in items}),
                **usage,
            },
        )
    return rows


def _aggregate_steps(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[bool, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        for step in record.get("step_records") or []:
            groups[(bool(record["cache_key"]), str(step.get("step")))].append(step)

    rows: list[dict[str, Any]] = []
    for (cache_key, step_name), items in sorted(groups.items()):
        elapsed = [
            float(item["elapsed_seconds"])
            for item in items
            if isinstance(item.get("elapsed_seconds"), int | float)
        ]
        rows.append(
            {
                "cache_key": cache_key,
                "label": _cache_label(cache_key),
                "step": step_name,
                "calls": len(items),
                "avg_elapsed_seconds": _mean(elapsed),
                "min_elapsed_seconds": round(min(elapsed), 3),
                "max_elapsed_seconds": round(max(elapsed), 3),
                "cache_hit_calls": sum(
                    1
                    for item in items
                    if int(_usage_summary(item.get("usage")).get("cached_tokens") or 0) > 0
                ),
                "cached_tokens": sum(
                    int(_usage_summary(item.get("usage")).get("cached_tokens") or 0)
                    for item in items
                ),
                "reasoning_tokens": sum(
                    int(_usage_summary(item.get("usage")).get("reasoning_tokens") or 0)
                    for item in items
                ),
            },
        )
    return rows


def _write_markdown(
    *,
    path: Path,
    metadata: dict[str, Any],
    summary: list[dict[str, Any]],
    step_summary: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> None:
    lines: list[str] = [
        "# Model Parameter Agent Cache Key Benchmark",
        "",
        f"- generated_at: `{metadata['generated_at']}`",
        f"- scenario_id: `{metadata['scenario_id']}`",
        f"- repeats_per_cache_key: `{metadata['repeats']}`",
        "- fixed_api: `chat.completions`",
        "- fixed_stream: `nonstream`",
        "- fixed_reasoning: `low`",
        f"- max_retries: `{metadata['max_retries']}`",
        f"- llm_timeout_sec: `{metadata['llm_timeout_sec']}`",
        "- note: Azure prompt cache is not disabled by omitting `prompt_cache_key`; the test compares key unspecified vs explicit key.",
        "- note: Quality score is a heuristic based on scenario dimensions and final proposal parameter/value/rationale fields.",
        "",
        "## Summary",
        "",
        "| cache_key | runs | avg_elapsed_s | min_s | max_s | avg_quality | min_quality | max_quality | unique_value_signatures | step_calls | cache_hit_steps | cached_tokens | reasoning_tokens | total_tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            "| {label} | {runs} | {avg_elapsed} | {min_elapsed} | {max_elapsed} | {avg_quality} | {min_quality} | {max_quality} | {unique} | {step_calls} | {cache_hit_steps} | {cached_tokens} | {reasoning_tokens} | {total_tokens} |".format(
                label=row["label"],
                runs=row["runs"],
                avg_elapsed=row["avg_elapsed_seconds"],
                min_elapsed=row["min_elapsed_seconds"],
                max_elapsed=row["max_elapsed_seconds"],
                avg_quality=row["avg_quality_score"],
                min_quality=row["min_quality_score"],
                max_quality=row["max_quality_score"],
                unique=row["unique_value_signature_count"],
                step_calls=row["step_calls"],
                cache_hit_steps=row["cache_hit_steps"],
                cached_tokens=row["cached_tokens"],
                reasoning_tokens=row["reasoning_tokens"],
                total_tokens=row["total_tokens"],
            ),
        )

    lines.extend(
        [
            "",
            "## Step Summary",
            "",
            "| cache_key | step | calls | avg_elapsed_s | min_s | max_s | cache_hit_calls | cached_tokens | reasoning_tokens |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ],
    )
    for row in step_summary:
        lines.append(
            "| {label} | {step} | {calls} | {avg_elapsed} | {min_elapsed} | {max_elapsed} | {hit_calls} | {cached_tokens} | {reasoning_tokens} |".format(
                label=row["label"],
                step=row["step"],
                calls=row["calls"],
                avg_elapsed=row["avg_elapsed_seconds"],
                min_elapsed=row["min_elapsed_seconds"],
                max_elapsed=row["max_elapsed_seconds"],
                hit_calls=row["cache_hit_calls"],
                cached_tokens=row["cached_tokens"],
                reasoning_tokens=row["reasoning_tokens"],
            ),
        )

    lines.extend(
        [
            "",
            "## Run Detail",
            "",
            "| repeat | cache_key | elapsed_s | quality | selected_params | value_counts | issues |",
            "|---:|---|---:|---:|---|---|---|",
        ],
    )
    for record in records:
        quality = record.get("quality") or {}
        value_summary = record.get("parameter_value_summary") or {}
        lines.append(
            "| {repeat} | {cache_key} | {elapsed} | {quality_score} | {params} | `{value_counts}` | {issues} |".format(
                repeat=record.get("repeat_index"),
                cache_key=_cache_label(bool(record.get("cache_key"))),
                elapsed=record.get("elapsed_seconds"),
                quality_score=quality.get("score"),
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
            "| repeat | cache_key | parameter | value_count | avg_proposed | min_proposed | max_proposed |",
            "|---:|---|---|---:|---:|---:|---:|",
        ],
    )
    for record in records:
        for parameter_name, item in sorted((record.get("parameter_value_summary") or {}).items()):
            lines.append(
                "| {repeat} | {cache_key} | {parameter} | {count} | {avg} | {min_value} | {max_value} |".format(
                    repeat=record.get("repeat_index"),
                    cache_key=_cache_label(bool(record.get("cache_key"))),
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
            "| repeat | cache_key | step | elapsed_s | cached_tokens | reasoning_tokens | total_tokens |",
            "|---:|---|---|---:|---:|---:|---:|",
        ],
    )
    for record in records:
        for step in record.get("step_records") or []:
            usage = _usage_summary(step.get("usage"))
            lines.append(
                "| {repeat} | {cache_key} | {step} | {elapsed} | {cached} | {reasoning_tokens} | {total} |".format(
                    repeat=record.get("repeat_index"),
                    cache_key=_cache_label(bool(record.get("cache_key"))),
                    step=step.get("step"),
                    elapsed=step.get("elapsed_seconds"),
                    cached=usage.get("cached_tokens"),
                    reasoning_tokens=usage.get("reasoning_tokens"),
                    total=usage.get("total_tokens"),
                ),
            )

    lines.extend(["", "## Final Response JSON"])
    for record in records:
        lines.extend(
            [
                "",
                f"### repeat={record.get('repeat_index')} cache_key={_cache_label(bool(record.get('cache_key')))}",
                "",
                "```json",
                json.dumps(record.get("final_response"), ensure_ascii=False, indent=2, default=str),
                "```",
            ],
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run(args: argparse.Namespace) -> tuple[Path, Path]:
    settings = get_settings()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now().strftime("%Y%m%d_%H%M%S")
    partial_path = REPORT_DIR / f"model_parameter_cache_key_benchmark_{generated_at}.partial.json"
    records: list[dict[str, Any]] = []

    for repeat_index in range(1, args.repeats + 1):
        variants = CACHE_KEY_VARIANTS if repeat_index % 2 else tuple(reversed(CACHE_KEY_VARIANTS))
        for variant in variants:
            record = await _run_spec(
                RunSpec(
                    scenario_id=args.scenario_id,
                    repeat_index=repeat_index,
                    variant=variant,
                ),
                max_retries=args.max_retries,
            )
            record["cache_key"] = variant.cache_key
            record["cache_key_label"] = _cache_label(variant.cache_key)
            records.append(record)
            partial_path.write_text(
                json.dumps(records, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )

    summary = _aggregate(records)
    step_summary = _aggregate_steps(records)
    metadata = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "scenario_id": args.scenario_id,
        "repeats": args.repeats,
        "max_retries": args.max_retries,
        "llm_timeout_sec": settings.llm_timeout_sec,
        "variants": [variant.__dict__ for variant in CACHE_KEY_VARIANTS],
    }
    report = {
        "metadata": metadata,
        "summary": summary,
        "step_summary": step_summary,
        "records": records,
    }
    json_path = REPORT_DIR / f"model_parameter_cache_key_benchmark_{generated_at}.json"
    md_path = REPORT_DIR / f"model_parameter_cache_key_benchmark_{generated_at}.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    _write_markdown(
        path=md_path,
        metadata=metadata,
        summary=summary,
        step_summary=step_summary,
        records=records,
    )
    partial_path.unlink(missing_ok=True)
    return json_path, md_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark explicit prompt cache key effect while keeping scenario, API, stream, and reasoning fixed.",
    )
    parser.add_argument("--scenario-id", type=int, default=130)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-retries", type=int, default=1)
    return parser.parse_args()


def main() -> None:
    json_path, md_path = asyncio.run(run(parse_args()))
    print(f"JSON_REPORT {json_path}")
    print(f"MD_REPORT {md_path}")


if __name__ == "__main__":
    main()
