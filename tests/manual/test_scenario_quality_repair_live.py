from __future__ import annotations

# ruff: noqa: CPY001, T201
import argparse
import asyncio
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Real LLM, isolated SQLite only; no production DB reads or writes.")
    parser.add_argument("--evaluation-json", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / "envs" / ".env", override=True)
    os.environ["DEBUG"] = "false"
    payload = json.loads(args.evaluation_json.read_text(encoding="utf-8"))
    original = payload["inputSnapshot"]

    from sqlalchemy import Engine, event, select

    from apps.agents.scenario_group_agent.flows.evaluate_scenarios.flow import run_quality_evaluation
    from apps.agents.scenario_group_agent.runtime import (
        get_scenario_group_operation_event_hub,
        get_scenario_group_operation_task_runner,
    )
    from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationModel
    from apps.persistence.scenario_quality_evaluation.models import MiScenarioQualityEvaluationModel
    from tests.manual.quality_eval.repair_sandbox import repair_sandbox

    @event.listens_for(Engine, "before_cursor_execute")
    def reject_non_sqlite(conn, *_args: object) -> None:  # noqa: ANN001
        if conn.dialect.name != "sqlite":
            msg = "This test must never execute SQL outside its SQLite sandbox"
            raise RuntimeError(msg)

    async def execute(group_id: int, operation_id: str) -> None:
        runner = get_scenario_group_operation_task_runner()
        hub = get_scenario_group_operation_event_hub()
        await hub.start()
        await runner.start()
        try:
            await runner.run_with_heartbeat(group_id, operation_id, run_quality_evaluation(group_id, operation_id))
        finally:
            await runner.shutdown()
            await hub.shutdown()

    args.output_dir.mkdir(parents=True, exist_ok=False)
    summary = []
    for name in ("original_130", "injected_contradiction"):
        snapshot = deepcopy(original)
        if name == "injected_contradiction":
            # Local-only negative fixture: actual selected supply/demand states contradict this narrative.
            snapshot["scenarios"][1]["narrative"] = (
                "Adriatic LNG 인도 차질은 2026년 12월 전에 완전히 해소되고 남아시아 현물 구매도 발생하지 않는다. "
                "동시에 같은 기간 차질은 12월 이후 계속되고 남아시아 현물 구매가 발생한다고 확정한다."
            )
        case_dir = args.output_dir / name
        case_dir.mkdir()
        with repair_sandbox(snapshot) as db:
            first, _ = db.service.prepare(db.group_id, 42, str(uuid4()))
            print(
                json.dumps({"case": name, "operationId": first.operation_id, "productionDbWrites": False}), flush=True,
            )
            asyncio.run(execute(db.group_id, first.operation_id))
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
                        "retrySummary": row.retry_summary,
                        "resultPayload": row.result_payload,
                        "lastError": row.last_error,
                    }
                    for row in session.scalars(select(MiScenarioGroupOperationModel)).all()
                ]
            records = [db.service.get(db.group_id, key).model_dump(mode="json", by_alias=True) for key in ids]
            for index, record in enumerate(records, 1):
                (case_dir / f"evaluation_{index}.json").write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            (case_dir / "operations.json").write_text(
                json.dumps(operations, ensure_ascii=False, indent=2, default=str) + "\n",
                encoding="utf-8",
            )
            entry = {
                "case": name,
                "productionDbWrites": False,
                "evaluationCount": len(records),
                "evaluations": [
                    {key: row[key] for key in ("operationId", "status", "verdict", "averageScore", "promptVersion")}
                    for row in records
                ],
            }
            summary.append(entry)
            print(json.dumps(entry, ensure_ascii=False), flush=True)
        (args.output_dir / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
