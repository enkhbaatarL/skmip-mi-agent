from __future__ import annotations

# ruff: noqa: CPY001, S101, ANN001, ANN201, ANN202, PT011
import asyncio
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest
from sqlalchemy import Column, DefaultClause, Integer, MetaData, Table, create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.scenario_group_agent.flows.evaluate_scenarios import flow
from apps.agents.scenario_group_agent.persistence import (
    scenario_group_operation_service as operations,
    scenario_quality_evaluation_service as persistence,
)
from apps.agents.scenario_group_agent.prompts.scenario_quality_evaluation import summarize, validate_targets
from apps.agents.scenario_group_agent.routers import scenario_groups
from apps.common.exceptions.custom import MIBaseError
from apps.persistence.scenario_group_operation.models import (
    MiScenarioGroupOperationEventModel,
    MiScenarioGroupOperationModel,
)
from apps.persistence.scenario_quality_evaluation.models import MiScenarioQualityEvaluationModel
from apps.persistence.scenario_quality_evaluation.schema import JUDGE_IDS, ScenarioQualityJudgment


SNAPSHOT = {
    "schemaVersion": 1,
    "group": {"scenario_group_id": 103},
    "scenarios": [{"scenario_id": 415, "narrative": "한파 심화"}, {"scenario_id": 417, "narrative": "기준 경로"}],
    "events": [{"eventId": 59, "eventSnapshotId": 9}],
}


def judgment(*, fact=False):
    data = {
        "summary": "평가 결과",
        "items": [{"judgeId": key, "score": 4, "verdict": "PASS", "violations": []} for key in JUDGE_IDS],
    }
    if fact:
        data["items"][1].update(
            score=3,
            verdict="WARN",
            violations=[
                {
                    "scenarioIds": [417],
                    "evidencePath": "/scenarios/1/narrative",
                    "evidence": "기준 경로",
                    "reason": "기준 경로 근거 확인 필요",
                    "suggestedFix": "근거 보완",
                    "factDependency": "EXTERNAL_FACT_REQUIRED",
                },
            ],
        )
    return ScenarioQualityJudgment.model_validate(data)


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def collation(connection, record):
        connection.create_collation("utf8mb4_bin", lambda a, b: (a > b) - (a < b))

    metadata = MetaData()
    Table("tmm_mi_scenario_group_m", metadata, Column("scenario_group_id", Integer, primary_key=True))
    for model in (MiScenarioGroupOperationModel, MiScenarioGroupOperationEventModel, MiScenarioQualityEvaluationModel):
        table = model.__table__.to_metadata(metadata)
        for column in table.c:
            column.type = column.type.as_generic()
            if column.name == "operation_event_id":
                column.type = Integer()
            if column.name in {"crt_dtm", "mod_dtm"}:
                column.server_default = DefaultClause(text("CURRENT_TIMESTAMP"))
            elif column.server_default is not None and "JSON_OBJECT" in str(column.server_default.arg):
                column.server_default = DefaultClause(text("'{}'"))
    metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(persistence, "get_sync_session", factory)
    from apps.common.configs.database.sync_database import connection

    monkeypatch.setattr(connection, "get_sync_session", factory)
    group = SimpleNamespace(scenario_group_id=103, request_usr_id=42, api_version="v4", stage="scenario_created")
    monkeypatch.setattr(
        persistence.ScenarioGroupRepository,
        "fetch_by_id",
        lambda self, group_id, **kw: group if group_id == 103 else None,
    )
    monkeypatch.setattr(
        persistence.ScenarioQualityEvaluationService, "build_snapshot", lambda *args: deepcopy(SNAPSHOT),
    )
    yield SimpleNamespace(service=persistence.ScenarioQualityEvaluationService(), factory=factory, group=group)
    engine.dispose()


def prepare(db, request_id=None):
    return db.service.prepare(103, 42, request_id or str(uuid4()))


def test_prepare_is_idempotent_and_busy_group_blocks_edit_and_new_evaluation(db):
    request_id = str(uuid4())
    first, created = prepare(db, request_id)
    assert created
    second, created = prepare(db, request_id)
    assert not created
    assert first.operation_id == second.operation_id
    with pytest.raises(MIBaseError) as busy:
        prepare(db)
    assert busy.value.status_code == 409
    assert operations.ScenarioGroupOperationService().get_active(103).operation_id == first.operation_id
    with pytest.raises(MIBaseError):
        operations.ScenarioGroupOperationService().create_validation_operation(scenario_group_id=103, user_id=42)


def test_scope_owner_and_snapshot_are_preserved(db):
    record, _ = prepare(db)
    record.input_snapshot["group"]["scenario_group_id"] = 999
    assert db.service.get(103, record.operation_id).input_snapshot == SNAPSHOT
    with pytest.raises(MIBaseError):
        db.service.get(104, record.operation_id)
    with pytest.raises(MIBaseError) as forbidden:
        db.service.prepare(103, 7, str(uuid4()))
    assert forbidden.value.status_code == 403


def test_completion_and_late_result_guard(db):
    record, _ = prepare(db)
    result = judgment(fact=True)
    verdict, score = summarize(result)
    db.service.complete(
        103, record.operation_id, result=result, verdict=verdict, average_score=score, llm_metadata={"model": "test"},
    )
    saved = db.service.get(103, record.operation_id)
    assert saved.status == "succeeded"
    assert saved.verdict == "NEEDS_FACT"
    assert saved.result.items[1].violations[0].scenario_ids == [417]
    with pytest.raises(operations.OperationAlreadyTerminalError):
        db.service.complete(
            103, record.operation_id, result=judgment(), verdict="PASS", average_score=4, llm_metadata={},
        )


def test_automatic_prepare_uses_source_operation_once(db):
    source_id = operations.new_operation_id()
    with db.factory.begin() as session:
        operations.ScenarioGroupOperationService().create_accepted_in_session(
            session,
            scenario_group_id=103,
            operation_id=source_id,
            user_id=42,
        )
    operations.ScenarioGroupOperationService().append_event(
        103,
        source_id,
        event_type="completed",
        title="완료",
        message_markdown="생성 완료",
        status="succeeded",
    )
    child_id = db.service.automatic_operation_id(103, source_id)
    assert child_id != source_id
    assert child_id is not None
    child = db.service.get(103, child_id)
    assert child.input_snapshot["sourceOperationId"] == source_id
    assert child.source == "automatic"
    operations.ScenarioGroupOperationService().append_event(
        103,
        source_id,
        event_type="completed",
        title="완료",
        message_markdown="생성 완료",
        status="succeeded",
    )
    assert db.service.automatic_operation_id(103, source_id) == child_id


def test_seven_rubrics_and_evidence_required():
    data = judgment().model_dump()
    data["items"][0]["judge_id"] = "J-02"
    with pytest.raises(ValidationError):
        ScenarioQualityJudgment.model_validate(data)
    data = judgment().model_dump()
    data["items"][0]["verdict"] = "WARN"
    with pytest.raises(ValidationError):
        ScenarioQualityJudgment.model_validate(data)


@pytest.mark.parametrize(
    ("ids", "path"), [([999], "/scenarios/1"), ([417, 417], "/scenarios/1"), ([417], "/signposts/0")],
)
def test_unknown_ids_and_evidence_rejected(ids, path):
    result = judgment(fact=True)
    issue = result.items[1].violations[0]
    issue.scenario_ids = ids
    issue.evidence_path = path
    with pytest.raises(ValueError):
        validate_targets(result, SNAPSHOT)


@pytest.mark.parametrize("failure", [None, TimeoutError(), asyncio.CancelledError()])
def test_worker_persists_result_failure_and_interruption(db, monkeypatch, failure):
    record, _ = prepare(db)
    invocation = AsyncMock(
        return_value=SimpleNamespace(result=judgment(), model="test-model", usage=None), side_effect=failure,
    )
    monkeypatch.setattr(flow, "invoke_llm_structured_output", invocation)
    if isinstance(failure, asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(flow.run_quality_evaluation(103, record.operation_id))
    else:
        asyncio.run(flow.run_quality_evaluation(103, record.operation_id))
    saved = db.service.get(103, record.operation_id)
    assert saved.status == (
        "interrupted" if isinstance(failure, asyncio.CancelledError) else "failed" if failure else "succeeded"
    )
    if failure:
        assert saved.result is None


def test_api_202_get_and_retry_do_not_submit_twice(db, monkeypatch):
    submitted = []
    monkeypatch.setattr(scenario_groups, "submit_quality_evaluation", lambda group_id, op_id: submitted.append(op_id))
    app = FastAPI()
    app.include_router(scenario_groups.router)
    with TestClient(app) as client:
        path = "/scenario-groups/103/quality-evaluations"
        body = {"userId": 42, "requestId": str(uuid4())}
        response = client.post(path, json=body)
        assert response.status_code == 202
        operation_id = response.json()["data"]["operationId"]
        assert client.post(path, json=body).json()["data"]["operationId"] == operation_id
        assert submitted == [operation_id]
        assert client.get(f"{path}/{operation_id}").json()["data"]["status"] == "queued"
        assert client.post(path, json={"userId": 42}).status_code == 422
