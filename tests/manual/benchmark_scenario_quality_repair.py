from __future__ import annotations

# ruff: noqa: CPY001, T201, S603, ANN001, ANN202
import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from unittest.mock import patch
from uuid import uuid4

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def save(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def digest(data: object) -> str:
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()


def export_samples(output: Path, count: int, seed: int) -> dict:
    from sqlalchemy import Engine, event, text

    from apps.agents.scenario_group_agent.persistence.scenario_quality_evaluation_service import (
        ScenarioQualityEvaluationService,
    )
    from apps.agents.scenario_group_agent.prompts.scenario_quality_evaluation import PROMPT_VERSION, SYSTEM_PROMPT
    from apps.agents.scenario_group_agent.prompts.scenario_quality_repair import REPAIR_PROMPT_VERSION
    from apps.common.configs.config import get_settings
    from apps.common.configs.database.sync_database.connection import get_sync_session
    from apps.persistence.scenario_group.repository import ScenarioGroupRepository

    def read_only(_conn, _cursor, statement, *_args: object):
        sql = statement.lstrip().upper()
        if not sql.startswith(("SELECT", "SET TRANSACTION READ ONLY")):
            msg = "Sample export allows SELECT only"
            raise RuntimeError(msg)

    event.listen(Engine, "before_cursor_execute", read_only)
    exported, excluded = [], []
    try:
        with get_sync_session() as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            candidates = (
                session.execute(
                    text("""
                SELECT g.scenario_group_id, g.title, g.stage,
                  (SELECT COUNT(*) FROM tmm_mi_scenario_m s
                   WHERE s.scenario_group_id=g.scenario_group_id AND s.del_yn='N') AS scenario_count
                FROM tmm_mi_scenario_group_m g
                WHERE g.del_yn='N' AND g.api_version='v4'
                  AND g.generation_strategy='multi_event_model_lever_dimensions'
                  AND g.stage IN ('scenario_validated','signpost_created','completed')
                  AND NOT EXISTS (SELECT 1 FROM tmm_mi_scenario_group_operation_m o
                    WHERE o.scenario_group_id=g.scenario_group_id AND o.del_yn='N'
                      AND o.status IN ('queued','running'))
                ORDER BY g.scenario_group_id
            """),
                )
                .mappings()
                .all()
            )
            for candidate in candidates:
                meta = dict(candidate)
                if any(word in meta["title"] for word in ("검증용", "화성")) or not 3 <= meta["scenario_count"] <= 8:
                    excluded.append({**meta, "reason": "explicit synthetic/test title or unsupported scenario count"})
                    continue
                group = ScenarioGroupRepository(session=session).fetch_by_id(meta["scenario_group_id"])
                try:
                    snapshot = ScenarioQualityEvaluationService.build_snapshot(session, group)
                except Exception as exc:
                    excluded.append({**meta, "reason": type(exc).__name__})
                    continue
                exported.append(
                    {
                        "source": meta,
                        "inputSnapshot": snapshot,
                        "diagnostics": dict(group.generation_diagnostics or {}),
                        "inputHash": digest(snapshot),
                    },
                )
            session.rollback()
    finally:
        event.remove(Engine, "before_cursor_execute", read_only)
    if len(exported) < count:
        msg = f"Only {len(exported)} eligible groups for requested {count}"
        raise RuntimeError(msg)
    sampler = random.Random(seed)  # noqa: S311 - reproducible sampling, not security
    selected = sorted(sampler.sample(exported, count), key=lambda item: item["source"]["scenario_group_id"])
    (output / "inputs").mkdir()
    for item in selected:
        save(output / "inputs" / f"group_{item['source']['scenario_group_id']}.json", item)
    cfg = get_settings()
    manifest = {
        "createdAtUtc": datetime.now(UTC).isoformat(),
        "seed": seed,
        "sampleUnit": "scenario_group",
        "sampleCount": count,
        "eligibleCount": len(exported),
        "candidateCount": len(candidates),
        "eligibleGroups": [item["source"] for item in exported],
        "excluded": excluded,
        "selectedGroups": [item["source"] for item in selected],
        "selection": "uniform random without replacement, frozen before new judgments; no verdict filtering",
        "scenarioCount": sum(item["source"]["scenario_count"] for item in selected),
        "productionDbWrites": False,
        "executionDb": "isolated in-memory SQLite per worker process",
        "stageReplay": "copies replayed as scenario_validated before Signpost; source stage/data untouched",
        "promptVersion": PROMPT_VERSION,
        "promptHash": digest(SYSTEM_PROMPT),
        "repairPromptVersion": REPAIR_PROMPT_VERSION,
        "configuredDeployment": cfg.model_api_deployment_name,
        "reasoningEffort": cfg.llm_reasoning_effort,
        "maxRepairAttempts": 1,
    }
    save(output / "manifest.json", manifest)
    return manifest


def run_worker(input_file: Path, output: Path) -> None:
    from sqlalchemy import Engine, event, select

    from apps.agents.scenario_group_agent.flows.evaluate_scenarios import flow
    from apps.agents.scenario_group_agent.runtime import (
        get_scenario_group_operation_event_hub,
        get_scenario_group_operation_task_runner,
    )
    from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationModel
    from apps.persistence.scenario_quality_evaluation.models import MiScenarioQualityEvaluationModel
    from tests.manual.quality_eval.repair_sandbox import repair_sandbox

    @event.listens_for(Engine, "before_cursor_execute")
    def isolated_sql_only(conn, *_args: object):
        if conn.dialect.name != "sqlite":
            msg = "Evaluation worker cannot access the production DB"
            raise RuntimeError(msg)

    exported = json.loads(input_file.read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    trace = []
    invoke = flow.invoke_llm_structured_output
    validate_repair = flow.build_repaired_snapshot

    def recorded_validation(*args: object, **kwargs: object):
        try:
            return validate_repair(*args, **kwargs)
        except Exception as exc:
            save(output / "failure_detail.json", {
                "source": "live deterministic repair validation",
                "errorType": type(exc).__name__, "reason": str(exc),
            })
            raise

    async def recorded_invoke(**kwargs: object):
        start = time.perf_counter()
        entry = {"label": kwargs["log_label"], "schema": kwargs["output_schema"].__name__}
        try:
            response = await invoke(**kwargs)
            entry.update(
                {
                    "model": response.model,
                    "result": response.result.model_dump(mode="json", by_alias=True),
                    "usage": response.usage.model_dump(mode="json") if response.usage else None,
                },
            )
        except Exception as exc:
            entry["errorType"] = type(exc).__name__
            raise
        else:
            return response
        finally:
            entry["seconds"] = round(time.perf_counter() - start, 3)
            trace.append(entry)
            save(output / "llm_trace.json", trace)

    async def execute(group_id: int, operation_id: str) -> None:
        runner = get_scenario_group_operation_task_runner()
        hub = get_scenario_group_operation_event_hub()
        await hub.start()
        await runner.start()
        try:
            await runner.run_with_heartbeat(group_id, operation_id, flow.run_quality_evaluation(group_id, operation_id))
        finally:
            await runner.shutdown()
            await hub.shutdown()

    start = time.perf_counter()
    with repair_sandbox(exported["inputSnapshot"], diagnostics=exported["diagnostics"]) as db:
        record, _ = db.service.prepare(db.group_id, 42, str(uuid4()))
        with (
            patch.object(flow, "invoke_llm_structured_output", recorded_invoke),
            patch.object(flow, "build_repaired_snapshot", recorded_validation),
        ):
            asyncio.run(execute(db.group_id, record.operation_id))
        with db.factory() as session:
            ids = session.scalars(
                select(MiScenarioQualityEvaluationModel.operation_id).order_by(
                    MiScenarioQualityEvaluationModel.operation_id,
                ),
            ).all()
            operations = [
                {
                    "operationId": row.operation_id,
                    "type": row.operation_type,
                    "status": row.status,
                    "phase": row.current_phase,
                    "retrySummary": row.retry_summary,
                    "resultPayload": row.result_payload,
                    "lastError": row.last_error,
                }
                for row in session.scalars(select(MiScenarioGroupOperationModel)).all()
            ]
        evaluations = [db.service.get(db.group_id, key).model_dump(mode="json", by_alias=True) for key in ids]
        for index, result in enumerate(evaluations, 1):
            save(output / f"evaluation_{index}.json", result)
        save(output / "operations.json", operations)
        summary = {
            "groupId": db.group_id,
            "source": exported["source"],
            "seconds": round(time.perf_counter() - start, 3),
            "productionDbWrites": False,
            "evaluations": [
                {
                    key: row.get(key)
                    for key in ("operationId", "status", "verdict", "averageScore", "promptVersion", "lastError")
                }
                for row in evaluations
            ],
            "llmCalls": len(trace),
        }
        save(output / "summary.json", summary)
        print(json.dumps(summary, ensure_ascii=False), flush=True)


def run_samples(output: Path, manifest: dict, workers: int) -> None:
    def launch(meta):
        group_id = meta["scenario_group_id"]
        case = output / f"group_{group_id}"
        case.mkdir(exist_ok=True)
        if (case / "summary.json").exists():
            return group_id, "preserved existing run"
        with (case / "execution.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [
                    sys.executable,
                    "-X",
                    "utf8",
                    str(Path(__file__).resolve()),
                    "--worker",
                    str(output / "inputs" / f"group_{group_id}.json"),
                    "--output-dir",
                    str(case),
                ],
                cwd=ROOT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        return group_id, result.returncode

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(launch, meta) for meta in manifest["selectedGroups"]]
        for future in as_completed(futures):
            group_id, status = future.result()
            print(json.dumps({"groupId": group_id, "workerExit": status}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sample groups, real LLM repair once, report; production DB is read-only.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-count", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20261110)
    parser.add_argument("--workers", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--worker", type=Path)
    parser.add_argument("--export-only", action="store_true")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.sample_count < 1:
        parser.error("--sample-count must be positive")
    load_dotenv(ROOT / "envs" / ".env", override=True)
    os.environ["DEBUG"] = "false"
    output = args.output_dir.resolve()
    if args.worker:
        run_worker(args.worker.resolve(), output)
        return
    if args.report_only:
        from tests.manual.quality_eval.repair_report import write_report

        write_report(output)
        return
    if args.resume:
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        from apps.agents.scenario_group_agent.prompts.scenario_quality_evaluation import PROMPT_VERSION, SYSTEM_PROMPT
        from apps.agents.scenario_group_agent.prompts.scenario_quality_repair import REPAIR_PROMPT_VERSION

        if (manifest["promptVersion"], manifest["promptHash"], manifest["repairPromptVersion"]) != (
            PROMPT_VERSION, digest(SYSTEM_PROMPT), REPAIR_PROMPT_VERSION,
        ):
            parser.error("Prompt changed: start a new output directory instead of mixing evaluation criteria")
    else:
        output.mkdir(parents=True, exist_ok=False)
        manifest = export_samples(output, args.sample_count, args.seed)
    print(
        json.dumps(
            {
                "selectedGroups": [g["scenario_group_id"] for g in manifest["selectedGroups"]],
                "scenarioCount": manifest["scenarioCount"],
                "configuredDeployment": manifest["configuredDeployment"],
            },
        ),
        flush=True,
    )
    if args.export_only:
        return
    run_samples(output, manifest, args.workers)
    from tests.manual.quality_eval.repair_report import write_report

    write_report(output)


if __name__ == "__main__":
    main()
