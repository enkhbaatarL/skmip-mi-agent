from __future__ import annotations

# ruff: noqa: CPY001, E402, ANN401, SLF001
import argparse
import asyncio
from collections import defaultdict
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
from statistics import median
import sys
from time import perf_counter
from typing import Any
from unittest.mock import patch

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / "envs/.env", override=False)
os.environ.setdefault("METADATA_DB_PORT", "3306")
os.environ["DEBUG"] = "false"

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios import v4_flow, v4_nodes
from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.state import V4MultiEventGenerationState
from apps.common.configs.config import get_settings
from apps.common.logging.logger_config import logger
from apps.common.runtime.runtime import ensure_runtime_context_ready


def save(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


async def replay_call(kwargs: dict[str, Any], reference: dict[str, Any], prompt_hash: str, scale: float) -> Any:
    if reference["prompt_hash"] != prompt_hash or "result" not in reference:
        message = f"Replay prompt mismatch or failed recorded call: {kwargs['stage']}"
        raise ValueError(message)
    await asyncio.sleep(reference["elapsed_seconds"] * scale)
    return kwargs["output_schema"].model_validate(reference["result"])


def result_fields(output: dict[str, Any]) -> dict[str, Any]:
    final = V4MultiEventGenerationState.model_validate(output)
    if final.finalized_result is None:
        message = "Graph did not produce finalized scenarios"
        raise ValueError(message)
    result = final.finalized_result.model_dump(mode="json")
    return {
        "status": "succeeded",
        "result": result,
        "result_hash": hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest(),
        "scenario_count": len(final.finalized_result.scenarios),
    }


async def run_trial(  # noqa: C901 -- Keep all timing/patch state local to an isolated trial.
    state: V4MultiEventGenerationState,
    *,
    parallel: bool,
    recording: dict[str, Any] | None,
    replay_scale: float,
    deadline_seconds: float,
) -> dict[str, Any]:
    """Run the real v4 graph, replacing only persistence and optional LLM replay.

    Sequential mode gates whole Event analysis tasks, including their own retries.
    It does not patch asyncio.gather globally or change prompts/model parameters.
    """
    invoke = v4_nodes.invoke_stage_structured_output
    analyze = v4_nodes._analyze_event_with_retries
    gate = asyncio.Semaphore(len(state.events) if parallel else 1)
    calls: list[dict[str, Any]] = []
    node_times: list[dict[str, Any]] = []
    event_times: list[dict[str, Any]] = []
    validation_feedback: list[dict[str, Any]] = []
    recorded: dict[str, list[dict[str, Any]]] = defaultdict(list)
    offsets: dict[str, int] = defaultdict(int)
    for call in (recording or {}).get("calls", []):
        recorded[call["stage"]].append(call)
    started = perf_counter()

    async def measured_call(**kwargs: Any) -> Any:
        stage = kwargs["stage"]
        prompt_hash = hashlib.sha256(
            (kwargs["system_prompt"] + "\n" + kwargs["user_prompt"]).encode(),
        ).hexdigest()
        call: dict[str, Any] = {"stage": stage, "prompt_hash": prompt_hash, "start_seconds": perf_counter() - started}
        calls.append(call)
        call_started = perf_counter()
        try:
            if recording is None:
                result = await invoke(**kwargs)
            else:
                reference = recorded[stage][offsets[stage]]
                offsets[stage] += 1
                result = await replay_call(kwargs, reference, prompt_hash, replay_scale)
        except Exception as exc:
            call["error_type"] = type(exc).__name__
            raise
        else:
            call["result"] = result.model_dump(mode="json")
            return result
        finally:
            call["elapsed_seconds"] = perf_counter() - call_started

    async def measured_event(**kwargs: Any) -> Any:
        async with gate:
            event_started = perf_counter()
            outcome = await analyze(**kwargs)
            event_times.append(
                {
                    "event_id": outcome.event_id,
                    "elapsed_seconds": perf_counter() - event_started,
                    "attempts": outcome.attempts,
                    "success": outcome.result is not None,
                },
            )
            return outcome

    def timed_node(node_type: type) -> Any:
        original = node_type.run

        async def run(self: Any, *args: Any, **kwargs: Any) -> Any:
            node_started = perf_counter()
            try:
                return await original(self, *args, **kwargs)
            finally:
                node_times.append({"node": node_type.__name__, "seconds": perf_counter() - node_started})

        return run

    def measured_validation(name: str) -> Any:
        original = getattr(v4_flow, name)

        def validate(state: V4MultiEventGenerationState) -> dict[str, Any]:
            update = original(state)
            errors = {key: value for key, value in update.items() if key.endswith("_error") and value}
            if errors:
                validation_feedback.append({"node": name, "errors": errors})
            return update

        return validate

    report: dict[str, Any] = {"mode": "parallel" if parallel else "sequential", "status": "failed"}
    with ExitStack() as stack:
        stack.enter_context(patch.object(v4_nodes, "invoke_stage_structured_output", measured_call))
        stack.enter_context(patch.object(v4_nodes, "_analyze_event_with_retries", measured_event))
        # No group creation, Scenario INSERT/UPDATE, callback or Additional Dimension task.
        stack.enter_context(patch.object(v4_flow, "persist_v4_generation", lambda state: {}))
        for name in (
            "validate_v4_event_impacts",
            "validate_v4_event_interactions",
            "validate_v4_dimensions",
            "finalize_v4_scenarios",
        ):
            stack.enter_context(patch.object(v4_flow, name, measured_validation(name)))
        for node_type in (
            v4_nodes.AnalyzeEventImpactsNode,
            v4_nodes.AnalyzeEventInteractionsNode,
            v4_nodes.DesignModelLeverDimensionsNode,
            v4_nodes.SynthesizeV4ScenariosNode,
            v4_nodes.GenerateV4GroupTitleNode,
        ):
            stack.enter_context(patch.object(node_type, "run", timed_node(node_type)))
        try:
            async with asyncio.timeout(deadline_seconds):
                output = await v4_flow._build_graph().ainvoke(state.model_copy(deep=True))
            report.update(result_fields(output))
        except Exception as exc:
            report["error_type"] = type(exc).__name__
            if hasattr(exc, "error_code"):
                report["error_code"] = exc.error_code.name
    report.update(
        elapsed_seconds=perf_counter() - started,
        calls=calls,
        nodes=node_times,
        events=event_times,
        validation_feedback=validation_feedback,
    )
    return report


async def main(args: argparse.Namespace) -> None:
    args.output.mkdir(parents=True, exist_ok=False)
    logger.remove()
    logger.add(args.output / "execution.log", level="INFO", encoding="utf-8")
    state = V4MultiEventGenerationState.model_validate_json(args.input.read_text(encoding="utf-8"))
    recording = json.loads(args.recording.read_text(encoding="utf-8")) if args.recording else None
    if recording is not None and recording["status"] != "succeeded":
        message = "Replay requires a successful live trial"
        raise ValueError(message)
    cfg = get_settings()
    runtime = await ensure_runtime_context_ready() if recording is None else None
    summary: dict[str, Any] = {
        "kind": "recorded_response_replay" if recording else "live_llm",
        "scope": "v4 graph through title; DB preparation/persistence, SSE and background tasks excluded",
        "event_ids": [int(event.mi_event_id) for event in state.events],
        "input_hash": hashlib.sha256(state.model_dump_json().encode()).hexdigest(),
        "settings": {
            name: getattr(cfg, name)
            for name in (
                "llm_concurrency",
                "llm_reasoning_effort",
                "llm_v4_analysis_reasoning_effort",
                "llm_v4_group_title_reasoning_effort",
                "llm_stream_enabled",
                "model_api_deployment_name",
            )
        },
        "replay_scale": args.replay_scale if recording else None,
        "recording_source": str(args.recording) if args.recording else None,
        "recording_hash": hashlib.sha256(args.recording.read_bytes()).hexdigest() if args.recording else None,
        "trials": [],
    }
    save(args.output / "input.json", state.model_dump(mode="json"))
    save(args.output / "summary.json", summary)
    try:
        for round_no in range(1, args.rounds + 1):
            for parallel in [False, True] if round_no % 2 else [True, False]:
                name = f"round_{round_no}_{'parallel' if parallel else 'sequential'}"
                logger.info("BENCHMARK START | {}", name)
                trial = await run_trial(
                    state,
                    parallel=parallel,
                    recording=recording,
                    replay_scale=args.replay_scale,
                    deadline_seconds=args.timeout,
                )
                save(args.output / f"{name}.json", trial)
                summary["trials"].append(
                    {"name": name, **{key: value for key, value in trial.items() if key not in {"result", "calls"}}},
                )
                save(args.output / "summary.json", summary)
                logger.info(
                    "BENCHMARK DONE | {} | status={} | elapsed={:.3f}s",
                    name,
                    trial["status"],
                    trial["elapsed_seconds"],
                )
                if trial["status"] != "succeeded":
                    message = f"Benchmark failed: {name}; inspect the saved trial JSON"
                    raise RuntimeError(message)
        for mode in ("sequential", "parallel"):
            summary[f"{mode}_median_seconds"] = median(
                t["elapsed_seconds"] for t in summary["trials"] if t["mode"] == mode
            )
        summary["reduction_percent"] = 100 * (
            1 - summary["parallel_median_seconds"] / summary["sequential_median_seconds"]
        )
        summary["identical_outputs"] = len({t["result_hash"] for t in summary["trials"]}) == 1
        save(args.output / "summary.json", summary)
    finally:
        if runtime is not None:
            await runtime.close_all()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Compare sequential and asyncio-parallel Event analysis in the v4 graph.",
    )
    parser.add_argument("--input", type=Path, required=True, help="Frozen V4MultiEventGenerationState JSON")
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--recording", type=Path, help="Replay a successful live trial instead of calling the LLM")
    parser.add_argument("--replay-scale", type=float, default=0.01)
    parser.add_argument("--timeout", type=float, default=900)
    arguments = parser.parse_args()
    if arguments.rounds < 1 or arguments.replay_scale <= 0 or arguments.timeout <= 0:
        parser.error("rounds, replay-scale and timeout must be positive")
    asyncio.run(main(arguments))
