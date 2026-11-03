from __future__ import annotations

# ruff: noqa: CPY001, S101, TRY301
import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import json
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create separate groups and retain real factCheck evaluation evidence.",
    )
    parser.add_argument("--event-ids", type=int, nargs="+", required=True)
    parser.add_argument("--user-id", type=int, default=10603)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(ROOT / "envs" / ".env", override=True)
    os.environ["DEBUG"] = "false"

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
        ScenarioGroupOperationService,
    )
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
    from apps.common.configs.database.sync_database.connection import get_sync_session
    from apps.common.logging.logger_config import logger
    from apps.common.middleware.exception_handler import register_exception_handlers
    from apps.persistence.event.service import EventService
    from apps.persistence.scenario_quality_evaluation.repository import ScenarioQualityEvaluationRepository

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, object]] = []

    def save(path: Path, value: object) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")

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
        return None

    app = FastAPI(lifespan=lifespan)
    app.include_router(router)
    register_exception_handlers(app)
    with (
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.flow.deliver_operation_callback",
            new=omit_frontend_callback,
        ),
        TestClient(app) as client,
    ):
        for event_id in args.event_ids:
            case_dir = output / f"event_{event_id}"
            case_dir.mkdir(exist_ok=True)
            result: dict[str, object] = {"eventId": event_id, "status": "running", "retained": True}
            results.append(result)
            save(output / "summary.json", results)
            try:
                save(case_dir / "event.json", EventService().get_event_detail(event_id))
                body = {"miEventIds": [event_id], "userId": args.user_id}
                save(case_dir / "create_request.json", body)
                logger.info(f"Creating factCheck test group for event={event_id}")
                response = client.post("/scenario-groups", json=body)
                response.raise_for_status()
                (case_dir / "create.sse").write_text(response.text, encoding="utf-8")
                messages = [
                    json.loads(line[5:].strip()) for line in response.text.splitlines() if line.startswith("data:")
                ]
                group_id = int(messages[0]["scenarioGroupId"])
                result["scenarioGroupId"] = group_id
                save(output / "summary.json", results)
                assert any(item.get("eventType") == "completed" for item in messages), "Creation did not complete"
                detail = ScenarioGroupService().load_detail(group_id)
                save(case_dir / "generated_group.json", detail)
                definitions = detail["group"]["dimension_definitions"]
                table = {
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
                validated = client.post(
                    f"/scenario-groups/{group_id}/validation",
                    json={"userId": args.user_id, "table": table},
                )
                validated.raise_for_status()
                save(case_dir / "validation_response.json", validated.json())
                validation = ScenarioGroupOperationService().get_latest_internal_by_type(group_id, "validation")
                assert validation is not None
                save(case_dir / "validation.json", validation.model_dump(mode="json", by_alias=True))
                operation_id = ScenarioQualityEvaluationService().automatic_operation_id(
                    group_id, validation.operation_id,
                )
                assert operation_id is not None, "Validation did not prepare evaluation"
                result["evaluationOperationId"] = operation_id
                save(output / "summary.json", results)
                deadline = time.monotonic() + 900
                while time.monotonic() < deadline:
                    response = client.get(f"/scenario-groups/{group_id}/quality-evaluations/{operation_id}")
                    response.raise_for_status()
                    data = response.json()["data"]
                    save(case_dir / "evaluation.json", data)
                    if data["status"] in {"succeeded", "failed", "interrupted"}:
                        break
                    time.sleep(3)
                else:
                    msg = "Quality evaluation timed out; rows retained"
                    raise TimeoutError(msg)
                assert data["status"] == "succeeded", f"Evaluation failed: {data['lastError']}"
                with get_sync_session() as session:
                    row = ScenarioQualityEvaluationRepository(session=session).fetch_by_operation_id(operation_id)
                    assert row is not None
                    save(case_dir / "db_result_payload.json", row.result_payload)
                    assert row.result_payload == data["result"]
                targets = [
                    {"judgeId": item["judgeId"], **issue}
                    for item in data["result"]["items"]
                    for issue in item["violations"]
                    if issue["factDependency"] == "EXTERNAL_FACT_REQUIRED"
                ]
                assert all(item.get("factCheck") for item in targets)
                save(case_dir / "fact_check_targets.json", targets)
                result.update(status="succeeded", verdict=data["verdict"], factCheckCount=len(targets))
                logger.info(json.dumps(result, ensure_ascii=False))
            except Exception as exc:
                result.update(status="failed", errorType=type(exc).__name__, error=str(exc))
                logger.error(json.dumps(result, ensure_ascii=False))
            save(output / "summary.json", results)


if __name__ == "__main__":
    main()
