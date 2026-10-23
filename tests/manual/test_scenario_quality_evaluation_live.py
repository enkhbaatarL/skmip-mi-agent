from __future__ import annotations

# ruff: noqa: CPY001, C901, TRY301, S101
import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
from uuid import uuid4

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(description="Live create/edit + quality evaluation test. Keeps all DB rows.")
    parser.add_argument("--event-ids", type=int, nargs="+", required=True)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / "envs" / ".env", override=True)
    os.environ["DEBUG"] = "false"

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
    from apps.agents.scenario_group_agent.persistence.scenario_quality_evaluation_service import (
        ScenarioQualityEvaluationService,
    )
    from apps.agents.scenario_group_agent.routers.scenario_groups import router
    from apps.agents.scenario_group_agent.runtime import (
        get_additional_dimension_task_runner,
        get_scenario_group_operation_event_hub,
        get_scenario_group_operation_task_runner,
    )
    from apps.common.configs.database.application_tables import APPLICATION_TABLES
    from apps.common.configs.database.schema_validation import validate_schema
    from apps.common.configs.database.sync_database.connection import get_sync_engine
    from apps.common.middleware.exception_handler import register_exception_handlers

    validate_schema(get_sync_engine(), APPLICATION_TABLES)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    summary: dict[str, object] = {"eventIds": args.event_ids, "userId": args.user_id, "rollback": False}

    def save(name: str, data: object) -> None:
        (output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

    def checkpoint() -> None:
        save("summary.json", summary)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        hub = get_scenario_group_operation_event_hub()
        runner = get_scenario_group_operation_task_runner()
        additional = get_additional_dimension_task_runner()
        await hub.start()
        await runner.start()
        await additional.start()
        try:
            yield
        finally:
            await runner.shutdown()
            await additional.shutdown()
            await hub.shutdown()

    async def omit_frontend_callback(**kwargs: object) -> None:
        # Core DB/LLM/API execution is real; this test does not notify an external frontend.
        return None

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    register_exception_handlers(app)

    def request_table(group_id: int) -> dict[str, object]:
        detail = ScenarioGroupService().load_detail(group_id)
        definitions = detail["group"]["dimension_definitions"]
        return {
            "headers": [
                {
                    "key": item.get("dimension_id", item.get("dimensionId")),
                    "label": item["label"],
                    "displayOrder": index,
                }
                for index, item in enumerate(definitions)
            ],
            "rows": [
                {
                    "scenarioId": row["scenario_id"],
                    "displayOrder": row["display_order"],
                    "title": row["title"],
                    "cells": row["dimension_values"],
                }
                for row in detail["scenarios"]
            ],
        }

    def wait_quality(client: TestClient, group_id: int, source_id: str, name: str) -> dict[str, object]:
        operation_id = ScenarioQualityEvaluationService().automatic_operation_id(group_id, source_id)
        if operation_id is None:
            msg = "Automatic evaluation was not prepared"
            raise RuntimeError(msg)
        summary[f"{name}EvaluationOperationId"] = operation_id
        checkpoint()
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            response = client.get(f"/scenario-groups/{group_id}/quality-evaluations/{operation_id}")
            response.raise_for_status()
            data = response.json()["data"]
            save(f"{name}_evaluation.json", data)
            if data["status"] in {"succeeded", "failed", "interrupted"}:
                summary[f"{name}EvaluationStatus"] = data["status"]
                summary[f"{name}Verdict"] = data["verdict"]
                checkpoint()
                if data["status"] != "succeeded":
                    msg = f"{name} evaluation did not succeed: {data['lastError']}"
                    raise RuntimeError(msg)
                return data
            time.sleep(3)
        msg = "Evaluation polling timed out; DB rows have been retained"
        raise TimeoutError(msg)

    try:
        with (
            patch(
                "apps.agents.scenario_group_agent.flows.validate_scenarios.flow.deliver_operation_callback",
                new=omit_frontend_callback,
            ),
            TestClient(app) as client,
        ):
            body = {"miEventIds": args.event_ids, "userId": args.user_id}
            save("create_request.json", body)
            response = client.post("/scenario-groups", json=body)
            response.raise_for_status()
            (output / "create.sse").write_text(response.text, encoding="utf-8")
            messages = [json.loads(line[5:].strip()) for line in response.text.splitlines() if line.startswith("data:")]
            if not messages:
                msg = "SSE did not return events"
                raise RuntimeError(msg)
            first = messages[0]
            group_id = int(first["scenarioGroupId"])
            source_id = str(first["operationId"])
            summary.update(scenarioGroupId=group_id, createOperationId=source_id)
            checkpoint()
            if not any(message.get("eventType") == "completed" for message in messages):
                msg = "Create operation did not complete; inspect create.sse"
                raise RuntimeError(msg)
            table = request_table(group_id)
            blocked = client.post(
                f"/scenario-groups/{group_id}/validation", json={"userId": args.user_id, "table": table},
            )
            save("edit_while_evaluating.json", {"httpStatus": blocked.status_code, "body": blocked.json()})
            summary["editWhileEvaluatingHttpStatus"] = blocked.status_code
            if blocked.status_code != 409:
                msg = "Edit was not blocked while evaluation was active"
                raise RuntimeError(msg)
            created = wait_quality(client, group_id, source_id, "create")
            presentation = client.get(f"/scenario-groups/{group_id}/presentation")
            presentation.raise_for_status()
            save("presentation_after_create.json", presentation.json())

            table = request_table(group_id)
            old_title = table["rows"][0]["title"]
            table["rows"][0]["title"] = old_title + " 전개"
            save("edit_request.json", {"userId": args.user_id, "table": table})
            edited = client.post(
                f"/scenario-groups/{group_id}/validation", json={"userId": args.user_id, "table": table},
            )
            edited.raise_for_status()
            save("edit_response.json", edited.json())
            with get_sync_engine().connect() as connection:
                from sqlalchemy import text

                validation_id = connection.execute(
                    text(
                        "SELECT operation_id FROM tmm_mi_scenario_group_operation_m "
                        "WHERE scenario_group_id=:gid AND operation_type='validation' "
                        "ORDER BY crt_dtm DESC,operation_id DESC LIMIT 1",
                    ),
                    {"gid": group_id},
                ).scalar_one()
            summary["editOperationId"] = validation_id
            checkpoint()
            modified = wait_quality(client, group_id, validation_id, "edit")
            assert created["inputHash"] != modified["inputHash"], "Edit must change the evaluated snapshot"
            detail = ScenarioGroupService().load_detail(group_id)
            save("final_group_snapshot.json", detail)
            assert any(row["title"] == old_title + " 전개" for row in detail["scenarios"])

            manual_body = {"userId": args.user_id, "requestId": str(uuid4())}
            manual = client.post(f"/scenario-groups/{group_id}/quality-evaluations", json=manual_body)
            assert manual.status_code == 202
            save("manual_evaluation_post.json", manual.json())
            retry = client.post(f"/scenario-groups/{group_id}/quality-evaluations", json=manual_body)
            assert retry.json()["data"]["operationId"] == manual.json()["data"]["operationId"]
            manual_id = manual.json()["data"]["operationId"]
            summary["manualEvaluationOperationId"] = manual_id
            deadline = time.monotonic() + 900
            while time.monotonic() < deadline:
                data = client.get(f"/scenario-groups/{group_id}/quality-evaluations/{manual_id}").json()["data"]
                save("manual_evaluation.json", data)
                if data["status"] in {"succeeded", "failed", "interrupted"}:
                    assert data["status"] == "succeeded"
                    break
                time.sleep(3)
            else:
                msg = "Manual evaluation timed out"
                raise TimeoutError(msg)
            summary["status"] = "passed"
            summary["callback"] = "External frontend callback omitted; DB, LLM and API execution real"
            checkpoint()
    except Exception as exc:
        summary.update(status="failed", errorType=type(exc).__name__, error=str(exc))
        checkpoint()
        raise


if __name__ == "__main__":
    main()
