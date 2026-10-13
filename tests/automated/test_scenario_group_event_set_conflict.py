from __future__ import annotations

import json
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, call, patch

from pydantic import ValidationError
import pytest
from sqlalchemy.dialects import mysql

from apps.agents.scenario_group_agent.flows.create_multi_event_scenarios.api_schema import (
    V4MultiEventCreateScenariosIn,
)
from apps.agents.scenario_group_agent.persistence import (
    scenario_group_operation_service as operation_service_module,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.common.exceptions.custom import MIBaseError
from apps.common.middleware.exception_handler import _mi_error_response
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.scenario_group.event_set import canonical_event_set, event_set_hash
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


def test_event_set_hash_is_order_independent_and_versioned() -> None:
    assert canonical_event_set([3, 1, 2]) == "v1:[1,2,3]"
    assert event_set_hash([1, 2, 3]) == event_set_hash([3, 2, 1])
    assert event_set_hash([1, 2, 3]) != event_set_hash([3, 4, 5])
    assert event_set_hash([1, 2, 3]) == "9038e0c75ab758fb490d1606657919ada48a1bd1aad982420ec0c643cf31b6a3"


@pytest.mark.parametrize("event_ids", [[1, 1], [0], [-1, 2]])
def test_request_validation_rejects_duplicate_or_non_positive_event_ids(event_ids: list[int]) -> None:
    with pytest.raises(ValidationError):
        V4MultiEventCreateScenariosIn(miEventIds=event_ids, userId=7)


def test_event_lock_query_is_sorted_and_uses_for_update() -> None:
    session = Mock()
    session.execute.return_value.scalars.return_value.all.return_value = [1, 2, 3]

    assert EventRepository(session=session).lock_events([3, 1, 2]) == [1, 2, 3]

    statement = session.execute.call_args.args[0]
    sql = str(
        statement.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "IN (1, 2, 3)" in sql
    assert "ORDER BY tmm_mi_mievent_m.mi_event_id" in sql
    assert "FOR UPDATE" in sql


def test_candidate_query_excludes_soft_deleted_parent_and_locks_matches() -> None:
    session = Mock()
    session.execute.return_value.scalars.return_value.all.return_value = []

    ScenarioGroupRepository(session=session).fetch_event_set_candidates(
        engine_version="v4",
        event_set_hash="a" * 64,
        for_update=True,
    )

    statement = session.execute.call_args.args[0]
    sql = str(
        statement.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )
    assert "tmm_mi_scenario_group_m.api_version = 'v4'" in sql
    assert "tmm_mi_scenario_group_m.event_set_hash =" in sql
    assert "tmm_mi_scenario_group_m.del_yn = 'N'" in sql
    assert "FOR UPDATE" in sql


def test_conflict_response_merges_existing_resource_identifiers() -> None:
    error = MIBaseError(
        ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT,
        context={"scenarioGroupId": 407, "operationId": "op-running"},
    )

    body = json.loads(_mi_error_response(error).body)

    assert body["data"] == {
        "scenarioGroupId": 407,
        "operationId": "op-running",
        "error_code": -1005,
        "error_name": "SCENARIO_GROUP_OPERATION_CONFLICT",
    }


def test_matching_event_set_does_not_block_new_group_creation() -> None:
    session = Mock()
    group_repository = Mock()
    group_repository.insert_group.return_value = 408
    group_repository.fetch_by_id.return_value = SimpleNamespace(scenario_group_id=408)
    event_repository = Mock()
    event_repository.lock_events.return_value = [1, 2, 3]
    event_repository.fetch_latest_snapshot_id.return_value = None
    operation_service = Mock()
    expected = ScenarioGroupPayload(scenario_group_id=408)
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]

    with (
        patch.dict(sys.modules, {"apps.common.configs.database.sync_database.connection": connection_module}),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.EventRepository",
            return_value=event_repository,
        ),
        patch.object(
            operation_service_module,
            "ScenarioGroupOperationService",
            return_value=operation_service,
        ),
        patch.object(ScenarioGroupPayload, "from_model", return_value=expected),
    ):
        result = ScenarioGroupService().prepare_v4_multi_event_group(
            events=[
                {"mi_event_id": 3, "event_type_l2_id": 30},
                {"mi_event_id": 1, "event_type_l2_id": 10},
                {"mi_event_id": 2, "event_type_l2_id": 20},
            ],
            impact_catalog_version="catalog-v1",
            impact_catalog_checksum="c" * 64,
            user_id=7,
            operation_id="op-new",
        )

    assert result is expected
    group_repository.fetch_event_set_candidates.assert_not_called()
    group_repository.fetch_event_ids_by_group_ids.assert_not_called()
    group_repository.insert_group.assert_called_once()
    operation_service.create_accepted_in_session.assert_called_once_with(
        session,
        scenario_group_id=408,
        operation_id="op-new",
        operation_type="create",
        engine_version="v4",
        user_id=7,
    )
    session.commit.assert_called_once_with()
    session.rollback.assert_not_called()


def test_group_links_operation_and_accepted_event_are_committed_atomically() -> None:
    session = Mock()
    group_repository = Mock()
    group_repository.fetch_event_set_candidates.return_value = []
    group_repository.fetch_event_ids_by_group_ids.return_value = {}
    group_repository.insert_group.return_value = 408
    created_model = SimpleNamespace(scenario_group_id=408)
    group_repository.fetch_by_id.return_value = created_model
    event_repository = Mock()
    event_repository.lock_events.return_value = [1, 2, 3]
    event_repository.fetch_latest_snapshot_id.return_value = None
    operation_service = Mock()
    expected = ScenarioGroupPayload(scenario_group_id=408)
    connection_module = ModuleType("apps.common.configs.database.sync_database.connection")
    connection_module.get_sync_session = Mock(return_value=session)  # type: ignore[attr-defined]

    with (
        patch.dict(sys.modules, {"apps.common.configs.database.sync_database.connection": connection_module}),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_service.EventRepository",
            return_value=event_repository,
        ),
        patch.object(
            operation_service_module,
            "ScenarioGroupOperationService",
            return_value=operation_service,
        ),
        patch.object(ScenarioGroupPayload, "from_model", return_value=expected),
    ):
        result = ScenarioGroupService().prepare_v4_multi_event_group(
            events=[
                {"mi_event_id": 3, "event_type_l2_id": 30},
                {"mi_event_id": 1, "event_type_l2_id": 10},
                {"mi_event_id": 2, "event_type_l2_id": 20},
            ],
            impact_catalog_version="catalog-v1",
            impact_catalog_checksum="c" * 64,
            user_id=7,
            operation_id="op-new",
        )

    assert result is expected
    inserted_group = group_repository.insert_group.call_args.args[0]
    assert inserted_group["event_set_hash"] == event_set_hash([3, 1, 2])
    assert group_repository.insert_group_event.call_args_list == [
        call(
            {
                "scenario_group_id": 408,
                "mi_event_id": 3,
                "mi_event_snapshot_id": None,
                "event_type_l2_id": 30,
                "scenario_dimension_template_id": None,
                "template_checksum": None,
                "display_order": 1,
                "crt_usr_logn_id": 7,
                "mod_usr_logn_id": 7,
            }
        ),
        call(
            {
                "scenario_group_id": 408,
                "mi_event_id": 1,
                "mi_event_snapshot_id": None,
                "event_type_l2_id": 10,
                "scenario_dimension_template_id": None,
                "template_checksum": None,
                "display_order": 2,
                "crt_usr_logn_id": 7,
                "mod_usr_logn_id": 7,
            }
        ),
        call(
            {
                "scenario_group_id": 408,
                "mi_event_id": 2,
                "mi_event_snapshot_id": None,
                "event_type_l2_id": 20,
                "scenario_dimension_template_id": None,
                "template_checksum": None,
                "display_order": 3,
                "crt_usr_logn_id": 7,
                "mod_usr_logn_id": 7,
            }
        ),
    ]
    operation_service.create_accepted_in_session.assert_called_once_with(
        session,
        scenario_group_id=408,
        operation_id="op-new",
        operation_type="create",
        engine_version="v4",
        user_id=7,
    )
    session.commit.assert_called_once_with()
