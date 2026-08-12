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
from apps.agents.scenario_group_agent.persistence.scenario_group_service import ScenarioGroupService
from apps.common.exceptions.custom import MIBaseError
from apps.common.middleware.exception_handler import _mi_error_response
from apps.common.values.error_codes import ErrorCode
from apps.persistence.event.repository import EventRepository
from apps.persistence.scenario_group.event_set import canonical_event_set, event_set_hash
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


def _group(
    scenario_group_id: int,
    *,
    owner_id: int = 7,
    stage: str = "scenario_created",
) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_id=scenario_group_id,
        request_usr_id=owner_id,
        stage=stage,
    )


def _operation(scenario_group_id: int, status: str) -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_id=scenario_group_id,
        operation_id=f"op-{scenario_group_id}-{status}",
        status=status,
    )


def _check_conflict(
    *,
    groups: list[SimpleNamespace],
    event_ids_by_group_id: dict[int, list[int]],
    latest_operations: dict[int, SimpleNamespace] | None = None,
    active_operations: dict[int, SimpleNamespace] | None = None,
    user_id: int = 7,
) -> None:
    ScenarioGroupService._raise_for_event_set_conflict(
        groups=groups,
        event_ids_by_group_id=event_ids_by_group_id,
        latest_operations=latest_operations or {},
        active_operations=active_operations or {},
        requested_event_ids=[3, 1, 2],
        user_id=user_id,
    )


def test_event_set_hash_is_order_independent_and_versioned() -> None:
    assert canonical_event_set([3, 1, 2]) == "v1:[1,2,3]"
    assert event_set_hash([1, 2, 3]) == event_set_hash([3, 2, 1])
    assert event_set_hash([1, 2, 3]) != event_set_hash([3, 4, 5])
    assert event_set_hash([1, 2, 3]) == "9038e0c75ab758fb490d1606657919ada48a1bd1aad982420ec0c643cf31b6a3"


@pytest.mark.parametrize("event_ids", [[1, 1], [0], [-1, 2]])
def test_request_validation_rejects_duplicate_or_non_positive_event_ids(event_ids: list[int]) -> None:
    with pytest.raises(ValidationError):
        V4MultiEventCreateScenariosIn(miEventIds=event_ids, userId=7)


@pytest.mark.parametrize("status", ["queued", "running"])
def test_active_operation_blocks_same_owner_with_operation_context(status: str) -> None:
    group = _group(407)
    operation = _operation(407, status)

    with pytest.raises(MIBaseError) as caught:
        _check_conflict(
            groups=[group],
            event_ids_by_group_id={407: [1, 2, 3]},
            latest_operations={407: operation},
            active_operations={407: operation},
        )

    assert caught.value.error_code is ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT
    assert caught.value.status_code == 409
    assert caught.value.context == {
        "scenarioGroupId": 407,
        "operationId": operation.operation_id,
    }


@pytest.mark.parametrize("status", ["queued", "running", "succeeded"])
def test_blocking_group_owned_by_another_user_returns_ownership_conflict(status: str) -> None:
    group = _group(407, owner_id=8)
    operation = _operation(407, status)
    active = {407: operation} if status in {"queued", "running"} else {}

    with pytest.raises(MIBaseError) as caught:
        _check_conflict(
            groups=[group],
            event_ids_by_group_id={407: [1, 2, 3]},
            latest_operations={407: operation},
            active_operations=active,
            user_id=7,
        )

    assert caught.value.error_code is ErrorCode.SCENARIO_GROUP_OWNERSHIP_CONFLICT
    assert caught.value.status_code == 403
    assert caught.value.context["scenarioGroupId"] == 407
    assert caught.value.context["operationId"] == operation.operation_id


@pytest.mark.parametrize("latest_status", [None, "succeeded"])
def test_unconfirmed_group_blocks_same_owner(latest_status: str | None) -> None:
    group = _group(407)
    operation = _operation(407, latest_status) if latest_status is not None else None

    with pytest.raises(MIBaseError) as caught:
        _check_conflict(
            groups=[group],
            event_ids_by_group_id={407: [1, 2, 3]},
            latest_operations={407: operation} if operation is not None else {},
        )

    assert caught.value.error_code is ErrorCode.SCENARIO_GROUP_ALREADY_CREATED
    assert caught.value.context["scenarioGroupId"] == 407
    assert caught.value.context.get("operationId") == (operation.operation_id if operation else None)


@pytest.mark.parametrize("latest_status", ["failed", "interrupted"])
def test_failed_or_interrupted_latest_operation_allows_recreation(latest_status: str) -> None:
    group = _group(407)
    operation = _operation(407, latest_status)

    _check_conflict(
        groups=[group],
        event_ids_by_group_id={407: [1, 2, 3]},
        latest_operations={407: operation},
    )


def test_completed_group_allows_recreation_without_operation_history() -> None:
    _check_conflict(
        groups=[_group(407, stage="completed")],
        event_ids_by_group_id={407: [1, 2, 3]},
    )


def test_hash_collision_candidate_with_different_linked_event_set_is_ignored() -> None:
    _check_conflict(
        groups=[_group(407)],
        event_ids_by_group_id={407: [3, 4, 5]},
        latest_operations={407: _operation(407, "succeeded")},
    )


def test_active_operation_has_precedence_over_unconfirmed_history() -> None:
    active_group = _group(406)
    unconfirmed_group = _group(407)
    active_operation = _operation(406, "running")

    with pytest.raises(MIBaseError) as caught:
        _check_conflict(
            groups=[unconfirmed_group, active_group],
            event_ids_by_group_id={406: [1, 2, 3], 407: [1, 2, 3]},
            latest_operations={
                406: active_operation,
                407: _operation(407, "succeeded"),
            },
            active_operations={406: active_operation},
        )

    assert caught.value.error_code is ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT
    assert caught.value.context["scenarioGroupId"] == 406


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


def test_loser_transaction_rolls_back_before_inserting_temporary_group() -> None:
    session = Mock()
    group_repository = Mock()
    group_repository.fetch_event_set_candidates.return_value = [_group(407)]
    group_repository.fetch_event_ids_by_group_ids.return_value = {407: [1, 2, 3]}
    event_repository = Mock()
    event_repository.lock_events.return_value = [1, 2, 3]
    operation = _operation(407, "running")
    operation_repository = Mock()
    operation_repository.fetch_latest_by_group_ids.return_value = {407: operation}
    operation_repository.fetch_active_by_group_ids.return_value = {407: operation}
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
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
    ):
        with pytest.raises(MIBaseError) as caught:
            ScenarioGroupService().prepare_v4_multi_event_group(
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

    assert caught.value.error_code is ErrorCode.SCENARIO_GROUP_OPERATION_CONFLICT
    group_repository.insert_group.assert_not_called()
    group_repository.insert_group_event.assert_not_called()
    session.rollback.assert_called_once_with()
    session.commit.assert_not_called()


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
    operation_repository = Mock()
    operation_repository.fetch_latest_by_group_ids.return_value = {}
    operation_repository.fetch_active_by_group_ids.return_value = {}
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
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.ScenarioGroupOperationService",
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
