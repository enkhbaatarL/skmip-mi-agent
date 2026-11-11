from __future__ import annotations

# ruff: noqa: CPY001, ANN001, ANN201, ANN202
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.encoders import jsonable_encoder
from sqlalchemy import DefaultClause, Integer, MetaData, create_engine, event, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.agents.scenario_group_agent.persistence import (
    scenario_quality_evaluation_service as evaluations,
    scenario_quality_repair_service as repairs,
)
from apps.common.configs.database.sync_database import connection
from apps.persistence.scenario.models import MiScenarioModel
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group_operation.models import (
    MiScenarioGroupOperationEventModel,
    MiScenarioGroupOperationModel,
)
from apps.persistence.scenario_quality_evaluation.models import MiScenarioQualityEvaluationModel
from apps.persistence.signpost.models import MiSignpostModel


@contextmanager
def repair_sandbox(snapshot, *, diagnostics=None):  # noqa: C901
    """Real repositories/transactions on isolated SQLite; never open a production DB connection."""
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def configure(dbapi, _record):
        dbapi.create_collation("utf8mb4_bin", lambda a, b: (a > b) - (a < b))
        dbapi.create_function(
            "JSON_TYPE", 1, lambda value: "ARRAY" if isinstance(json.loads(value), list) else "OBJECT",
        )

    metadata = MetaData()
    for model in (
        MiScenarioGroupModel,
        MiScenarioModel,
        MiSignpostModel,
        MiScenarioGroupOperationModel,
        MiScenarioGroupOperationEventModel,
        MiScenarioQualityEvaluationModel,
    ):
        table = model.__table__.to_metadata(metadata)
        for column in table.c:
            column.type = column.type.as_generic()
            if column.primary_key and "INT" in str(column.type).upper():
                column.type = Integer()
            default = str(column.server_default.arg) if column.server_default else ""
            if column.name in {"crt_dtm", "mod_dtm"}:
                column.server_default = DefaultClause(text("CURRENT_TIMESTAMP"))
            elif "JSON_OBJECT" in default:
                column.server_default = DefaultClause(text("'{}'"))
            elif "JSON_ARRAY" in default:
                column.server_default = DefaultClause(text("'[]'"))
    metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    group_id = snapshot["group"]["scenario_group_id"]
    with factory.begin() as session:
        session.add(
            MiScenarioGroupModel(
                **deepcopy(snapshot["group"]),
                request_usr_id=42,
                api_version="v4",
                stage="scenario_validated",
                status="creating",
                generation_strategy="multi_event_model_lever_dimensions",
                generation_diagnostics=deepcopy(diagnostics or {}),
                scenario_count=len(snapshot["scenarios"]),
            ),
        )
        allowed = {column.name for column in MiScenarioModel.__table__.columns}
        for row in snapshot["scenarios"]:
            values = {key: deepcopy(value) for key, value in row.items() if key in allowed}
            for key in ("crt_dtm", "mod_dtm"):
                values.pop(key, None)
            values.update(scenario_group_id=group_id, status="creating")
            session.add(MiScenarioModel(**values))

    def build_snapshot(session, group):
        raw = ScenarioGroupRepository(session=session).model_to_dict(group)
        return jsonable_encoder(
            {
                "schemaVersion": 1,
                "group": {key: raw.get(key) for key in snapshot["group"]},
                "scenarios": [
                    {
                        key: value
                        for key, value in ScenarioRepository(session=session).model_to_dict(row).items()
                        if key != "status"
                    }
                    for row in ScenarioRepository(session=session).fetch_models_by_group_id(group_id)
                ],
                "events": deepcopy(snapshot["events"]),
            },
        )

    try:
        with ExitStack() as stack:
            stack.enter_context(
                patch.object(ScenarioGroupRepository, "fetch_single_active_group_event", return_value=None),
            )
            for module in (evaluations, repairs, connection):
                stack.enter_context(patch.object(module, "get_sync_session", factory))
            stack.enter_context(patch.object(connection, "get_sync_engine", lambda: engine))
            stack.enter_context(patch.object(connection, "get_sync_session_factory", lambda: factory))
            stack.enter_context(
                patch.object(
                    evaluations.ScenarioQualityEvaluationService,
                    "build_snapshot",
                    staticmethod(build_snapshot),
                ),
            )
            yield SimpleNamespace(
                factory=factory, group_id=group_id, service=evaluations.ScenarioQualityEvaluationService(),
            )
    finally:
        engine.dispose()
