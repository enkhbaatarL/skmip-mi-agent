from __future__ import annotations

# ruff: noqa: COM812, CPY001, S101
import asyncio
from collections.abc import Callable
from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call, patch

import pytest

from apps.agents.scenario_group_agent.flows.validate_scenarios.flow import (
    _bg_to_output,
    _validation_table_for_output,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import _run_v4_scenario_validation
from apps.agents.scenario_group_agent.flows.validate_scenarios.state import ValidateScenariosState
from apps.agents.scenario_group_agent.flows.validate_scenarios.v4_validation import (
    V4ValidationAnalysis,
    analyze_v4_validation_request,
    scenario_fingerprint,
)
from apps.agents.scenario_group_agent.persistence.scenario_group_operation_service import (
    ScenarioGroupOperationService,
)
from apps.agents.scenario_group_agent.persistence.scenario_service import ScenarioService
from apps.agents.scenario_group_agent.prompts.scenario_validation import (
    V4ValidationGeneratedScenario,
    V4ValidationGeneratedScenariosOutput,
)
from apps.agents.scenario_group_agent.schemas.endpoint import CreateSignpostsIn
from apps.agents.scenario_group_agent.schemas.state import ScenarioTableState
from apps.agents.scenario_group_agent.subgraphs.scenario_review.schema import ReviewReport
from apps.agents.scenario_group_agent.subgraphs.scenario_review.state import ScenarioReviewState
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode
from apps.persistence.scenario.schema import ScenarioPayload, ScenarioTemplateDimension, ScenarioTemplateEnum
from apps.persistence.scenario_group.schema import ScenarioGroupPayload
from apps.persistence.scenario_group_operation.models import MiScenarioGroupOperationModel
from apps.persistence.scenario_group_operation.schema import (
    ValidationGeneratedFieldsPayload,
    ValidationOperationResultPayload,
    ValidationResultPayload,
    ValidationScenarioChangeSetPayload,
    ValidationScenarioUpsertPayload,
)


DEFINITIONS = [
    {
        "dimension_id": "demand",
        "label": "수요",
        "display_order": 1,
        "values": [
            {"value_id": "demand_low", "label": "낮은 수요", "pressure_contribution": "bearish"},
            {"value_id": "demand_high", "label": "높은 수요", "pressure_contribution": "bullish"},
        ],
    },
    {
        "dimension_id": "supply",
        "label": "공급",
        "display_order": 2,
        "values": [
            {"value_id": "supply_low", "label": "낮은 공급", "pressure_contribution": "bullish"},
            {"value_id": "supply_high", "label": "높은 공급", "pressure_contribution": "bearish"},
        ],
    },
]


def test_result_payload_has_orm_column_and_deployment_migration() -> None:
    assert MiScenarioGroupOperationModel.__table__.c.result_payload.nullable is True

    repository_root = Path(__file__).resolve().parents[2]
    migration = repository_root / "scripts/migrations/20260814_add_scenario_group_operation_result_payload.sql"
    migration_sql = migration.read_text(encoding="utf-8")
    assert "ALTER TABLE `tmm_mi_scenario_group_operation_m`" in migration_sql
    assert "ADD COLUMN `result_payload` JSON NULL" in migration_sql


def _scenarios() -> list[dict[str, object]]:
    combinations = [
        ("상방", "demand_high", "supply_low", "strong_bullish", 30),
        ("혼합", "demand_high", "supply_high", "balanced", 50),
        ("하방", "demand_low", "supply_high", "strong_bearish", 20),
    ]
    return [
        {
            "scenario_id": index,
            "scenario_group_id": 10,
            "display_order": index,
            "title": title,
            "narrative": f"{title} narrative",
            "dimension_values": {"demand": demand, "supply": supply},
            "probability_score": score,
            "probability_delta": 0,
            "baseline_yn": "Y" if score == 50 else "N",
            "global_pressure_band": band,
            "scenario_role": "ceiling" if index == 1 else "floor" if index == 3 else "mixed",
            "global_pressure_rationale": f"{title} pressure",
            "related_markets": [],
            "status": "creating",
        }
        for index, (title, demand, supply, band, score) in enumerate(combinations, start=1)
    ]


def _table(*, labels: bool = False) -> dict[str, object]:
    value_labels = {
        "demand_low": "낮은 수요",
        "demand_high": "높은 수요",
        "supply_low": "낮은 공급",
        "supply_high": "높은 공급",
    }
    return {
        "headers": [
            {"key": "demand", "label": "수요", "display_order": 1},
            {"key": "supply", "label": "공급", "display_order": 2},
        ],
        "rows": [
            {
                "scenario_id": scenario["scenario_id"],
                "display_order": scenario["display_order"],
                "title": scenario["title"],
                "cells": {
                    key: value_labels[str(value)] if labels else value
                    for key, value in scenario["dimension_values"].items()
                },
            }
            for scenario in _scenarios()
        ],
    }


def _analyze(
    table: dict[str, object],
    diagnostics: dict[str, object] | None = None,
) -> V4ValidationAnalysis:
    return analyze_v4_validation_request(
        request_table=table,
        persisted_scenarios=_scenarios(),
        dimension_definitions=DEFINITIONS,
        generation_diagnostics=diagnostics or {},
        stored_header_order=["demand", "supply"],
    )


def test_label_and_value_id_normalize_to_unchanged_fast_path() -> None:
    table = _table(labels=True)
    table["rows"][0]["title"] = "상 방!!"
    analysis = _analyze(table)

    assert analysis.unchanged is True
    assert analysis.blocking is False
    assert analysis.changed_rows == []


def test_ready_additional_candidate_extends_effective_validation_catalog() -> None:
    candidate = {
        "dimension_id": "duration",
        "label": "지속 기간",
        "display_order": 3,
        "source_uncertainty_ids": ["u_duration"],
        "values": [
            {"value_id": "duration_short", "label": "단기", "pressure_contribution": "balanced"},
            {"value_id": "duration_long", "label": "장기", "pressure_contribution": "bullish"},
        ],
    }
    table = _table()
    table["headers"].append({"key": "duration", "label": "지속 기간", "display_order": 3})
    for index, row in enumerate(table["rows"]):
        row["cells"]["duration"] = "duration_short" if index == 0 else "duration_long"

    analysis = _analyze(
        table,
        diagnostics={
            "additional_dimension_generation": {
                "status": "ready",
                "source_fingerprint": "sha256:candidate-source",
            },
            "additional_dimension_candidates": [candidate],
        },
    )

    assert analysis.blocking is False
    assert analysis.canonical_headers == ["demand", "supply", "duration"]
    assert analysis.promoted_dimension_ids == ["duration"]
    assert analysis.candidate_source_fingerprint == "sha256:candidate-source"
    assert analysis.requested_dimension_definitions[-1]["dimension_id"] == "duration"
    assert all("duration" in row.dimension_values for row in analysis.canonical_rows)


def test_scenario_fingerprint_ignores_workflow_status_but_detects_content_changes() -> None:
    scenarios = _scenarios()
    original = scenario_fingerprint(scenarios)
    status_changed = deepcopy(scenarios)
    status_changed[0]["status"] = "created"
    title_changed = deepcopy(scenarios)
    title_changed[0]["title"] = "외부 수정"

    assert scenario_fingerprint(status_changed) == original
    assert scenario_fingerprint(title_changed) != original


def test_changed_validation_refreshes_decimals_before_signpost_stale_check() -> None:
    analysis = _analyze(_table())
    result_payload = ValidationOperationResultPayload(
        mode="changed",
        base_scenario_fingerprint=analysis.base_scenario_fingerprint,
        dimension_definition_fingerprint=analysis.dimension_definition_fingerprint,
        validation_result=ValidationResultPayload(
            verdict="PASS",
            is_valid=True,
            can_proceed=True,
            reason_markdown="변경 통과",
        ),
        scenario_change_set=ValidationScenarioChangeSetPayload(
            upserts=[
                ValidationScenarioUpsertPayload(
                    scenario_id=1,
                    client_row_key="scenario:1",
                    change_type="TITLE_CHANGED",
                    display_order=1,
                    title="상방 수정",
                    dimension_values={"demand": "demand_high", "supply": "supply_low"},
                    generated_fields=ValidationGeneratedFieldsPayload(
                        narrative="상방 수정 narrative",
                        probability_score=23.0,
                        probability_delta=0,
                        pressure_band="strong_bullish",
                        pressure_rationale="상방 수정 pressure",
                        related_markets=[],
                    ),
                ),
            ],
        ),
    )
    group = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=101,
        stage="scenario_created",
        status="creating",
        api_version="v4",
        dimension_selected=["demand", "supply"],
        dimension_definitions=deepcopy(DEFINITIONS),
    )
    scenarios = [SimpleNamespace(**deepcopy(item)) for item in _scenarios()]
    validation_operation = SimpleNamespace(
        operation_id="validation-op",
        operation_type="validation",
        status="running",
        result_payload=None,
    )
    signpost_operation = SimpleNamespace(result_payload=None)
    session = Mock()
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.side_effect = [scenarios, scenarios]

    def model_to_dict(target: SimpleNamespace) -> dict[str, object]:
        return {
            key: getattr(target, key)
            for key in (
                "scenario_id",
                "scenario_group_id",
                "display_order",
                "title",
                "narrative",
                "dimension_values",
                "probability_score",
                "probability_delta",
                "baseline_yn",
                "global_pressure_band",
                "scenario_role",
                "global_pressure_rationale",
                "related_markets",
                "status",
            )
        }

    def update_model(target: SimpleNamespace, payload: dict[str, object]) -> None:
        for key, value in payload.items():
            setattr(target, key, value)

    def refresh_decimal_columns(target: SimpleNamespace) -> None:
        target.probability_score = Decimal(str(target.probability_score)).quantize(Decimal("0.00"))
        target.probability_delta = Decimal(str(target.probability_delta)).quantize(Decimal("0.00"))

    scenario_repository.model_to_dict.side_effect = model_to_dict
    scenario_repository.update_from_payload.side_effect = update_model
    session.refresh.side_effect = refresh_decimal_columns
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "creating",
        "stage": "scenario_validated",
    }
    group_repository.update_group.side_effect = update_model
    signpost_repository = Mock()
    operation_repository = Mock()
    operation_repository.fetch_by_id.return_value = validation_operation

    def complete_event(target: SimpleNamespace, **kwargs: object) -> None:
        target.status = kwargs["status"]

    operation_repository.append_event.side_effect = complete_event

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service."
            "ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.SignpostRepository",
            return_value=signpost_repository,
        ),
    ):
        ScenarioGroupOperationService().complete_validation(
            scenario_group_id=10,
            operation_id="validation-op",
            result_payload=result_payload,
            user_id=101,
        )

    stored = ValidationOperationResultPayload.model_validate(validation_operation.result_payload)
    assert stored.application is not None
    assert scenarios[0].probability_score == Decimal("23.00")
    assert scenarios[0].probability_delta == Decimal("0.00")
    assert stored.application.applied_scenario_fingerprint == scenario_fingerprint(
        [model_to_dict(item) for item in scenarios]
    )
    assert session.method_calls[:4] == [
        call.flush(),
        *(call.refresh(scenario) for scenario in scenarios),
    ]

    scenario_repository.fetch_models_by_group_id.side_effect = None
    scenario_repository.fetch_models_by_group_id.return_value = scenarios
    operation_repository.fetch_active.return_value = None
    operation_repository.fetch_latest_by_type.return_value = validation_operation
    operation_repository.fetch_by_id.return_value = signpost_operation

    def accept_change_set() -> dict[str, object]:
        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                        get_sync_session=lambda: session,
                    ),
                },
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
                return_value=scenario_repository,
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
                return_value=group_repository,
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
                return_value=signpost_repository,
            ),
            patch(
                "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
                return_value=operation_repository,
            ),
            patch.object(ScenarioGroupOperationService, "create_accepted_in_session", return_value=Mock()),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.new_operation_id",
                return_value="signpost-op",
            ),
        ):
            return ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    accepted = accept_change_set()

    assert accepted["validation_operation_id"] == "validation-op"
    assert signpost_operation.result_payload["validationOperationId"] == "validation-op"

    scenarios[0].title = "validation 이후 외부 변경"
    group.stage = "scenario_validated"
    with pytest.raises(MIBaseError) as error:
        accept_change_set()

    assert error.value.error_code is ErrorCode.SCENARIO_VALIDATION_STALE


def test_v4_signpost_request_accepts_user_id_without_table() -> None:
    request = CreateSignpostsIn.model_validate({"userId": 101})

    assert request.user_id == 101
    assert request.table is None


def test_v4_validation_callback_table_preserves_value_ids() -> None:
    source = _table()
    projected = _validation_table_for_output(
        source,
        {
            "generation_strategy": "multi_event_model_lever_dimensions",
            "dimension_definitions": DEFINITIONS,
        },
    )

    assert projected is not None
    assert projected["rows"][0]["cells"] == {"demand": "demand_high", "supply": "supply_low"}
    assert source["rows"][0]["cells"] == {"demand": "demand_high", "supply": "supply_low"}


def test_v4_validation_callback_accepts_nested_scenario_table_state() -> None:
    group = ScenarioGroupPayload(
        scenario_group_id=10,
        generation_strategy="multi_event_model_lever_dimensions",
        dimension_definitions=DEFINITIONS,
    )
    request_table = ScenarioTableState.model_validate(_table())

    output = _bg_to_output(
        {
            "scenario_group_id": 10,
            "scenario_group": group,
            "request_table": request_table,
            "operation_result": {
                "validation_result": {
                    "verdict": "PASS",
                    "is_valid": True,
                    "can_proceed": True,
                },
            },
        },
    )

    assert output.table is not None
    assert output.table.rows[0].cells == {"demand": "demand_high", "supply": "supply_low"}


def test_public_operation_payload_does_not_expose_internal_result_payload() -> None:
    operation = SimpleNamespace(
        operation_id="01JVALIDATION0000000000000",
        scenario_group_id=10,
        operation_type="validation",
        engine_version="v4",
        source="api",
        status="succeeded",
        current_phase="validation",
        retry_summary={},
        presentation_snapshot={},
        result_payload={"scenarioChangeSet": {"secret": True}},
        snapshot_revision=0,
        latest_sequence=1,
        last_error=None,
        mlflow_trace_id=None,
        started_at=None,
        completed_at=None,
        heartbeat_at=None,
        crt_dtm=datetime(2026, 8, 13, tzinfo=UTC),
        mod_dtm=datetime(2026, 8, 13, tzinfo=UTC),
    )

    public = ScenarioGroupOperationService.operation_payload_from_model(operation)

    assert "result_payload" not in public.model_dump()
    assert "resultPayload" not in public.model_dump(by_alias=True)


def _acceptance_fixture(
    *,
    base_fingerprint: str | None = None,
) -> tuple[Mock, Mock, Mock, Mock, Mock, SimpleNamespace]:
    analysis = _analyze(_table())
    result_payload = ValidationOperationResultPayload(
        mode="unchanged",
        base_scenario_fingerprint=base_fingerprint or analysis.base_scenario_fingerprint,
        dimension_definition_fingerprint=analysis.dimension_definition_fingerprint,
        validation_result=ValidationResultPayload(
            verdict="PASS",
            is_valid=True,
            can_proceed=True,
            review_skipped=True,
            reason_markdown="변경 없음",
        ),
        scenario_change_set=None,
    )
    group = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=101,
        stage="scenario_validated",
        api_version="v4",
        dimension_definitions=deepcopy(DEFINITIONS),
    )
    scenario_models = [SimpleNamespace(scenario_id=item["scenario_id"]) for item in _scenarios()]
    scenario_by_id = {int(item["scenario_id"]): item for item in _scenarios()}
    validation_operation = SimpleNamespace(
        operation_id="validation-op",
        operation_type="validation",
        status="succeeded",
        result_payload=result_payload.model_dump(mode="json", by_alias=True),
    )
    signpost_operation = SimpleNamespace(result_payload=None)
    session = Mock()
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.return_value = scenario_models
    scenario_repository.model_to_dict.side_effect = lambda model: scenario_by_id[int(model.scenario_id)]
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "creating",
        "stage": "scenario_validated",
    }
    signpost_repository = Mock()
    operation_repository = Mock()
    operation_repository.fetch_active.return_value = None
    operation_repository.fetch_latest_by_type.return_value = validation_operation
    operation_repository.fetch_by_id.return_value = signpost_operation
    return (
        session,
        scenario_repository,
        group_repository,
        signpost_repository,
        operation_repository,
        signpost_operation,
    )


def test_signpost_accepts_unchanged_validation_without_scenario_write() -> None:
    fixture = _acceptance_fixture()
    session, scenarios, groups, signposts, operations, signpost_operation = fixture
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
            return_value=signposts,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operations,
        ),
        patch.object(
            ScenarioGroupOperationService,
            "create_accepted_in_session",
            return_value=Mock(),
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.new_operation_id",
            return_value="signpost-op",
        ),
    ):
        accepted = ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    assert accepted["validation_operation_id"] == "validation-op"
    assert accepted["signpost_target_scenario_ids"] == []
    assert signpost_operation.result_payload["validationOperationId"] == "validation-op"
    scenarios.insert_scenario.assert_not_called()
    scenarios.update_from_payload.assert_not_called()
    scenarios.soft_delete_by_ids.assert_not_called()
    session.commit.assert_called_once()


def test_signpost_rejects_stale_validation_and_resets_stage() -> None:
    fixture = _acceptance_fixture(base_fingerprint="stale")
    session, scenarios, groups, signposts, operations, _signpost_operation = fixture
    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=scenarios,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
            return_value=groups,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
            return_value=signposts,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operations,
        ),
        pytest.raises(MIBaseError) as error,
    ):
        ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    assert error.value.error_code is ErrorCode.SCENARIO_VALIDATION_STALE
    groups.update_group.assert_called_once()
    assert groups.update_group.call_args.args[1]["stage"] == "scenario_created"
    scenarios.insert_scenario.assert_not_called()
    session.commit.assert_called_once()


def test_signpost_applies_changed_validation_and_records_application() -> None:
    analysis = _analyze(_table())
    change_set = ValidationScenarioChangeSetPayload(
        upserts=[
            ValidationScenarioUpsertPayload(
                scenario_id=1,
                client_row_key="scenario:1",
                change_type="TITLE_CHANGED",
                display_order=1,
                title="상방 수정",
                dimension_values={"demand": "demand_high", "supply": "supply_low"},
                generated_fields=ValidationGeneratedFieldsPayload(
                    narrative="기존 상방 narrative",
                    probability_score=30,
                    probability_delta=0,
                    pressure_band="strong_bullish",
                    pressure_rationale="기존 상방 pressure",
                    related_markets=[],
                ),
            ),
            ValidationScenarioUpsertPayload(
                scenario_id=None,
                client_row_key="new:4",
                change_type="NEW",
                display_order=4,
                title="신규 약상방",
                dimension_values={"demand": "demand_low", "supply": "supply_low"},
                generated_fields=ValidationGeneratedFieldsPayload(
                    narrative="신규 narrative",
                    probability_score=10,
                    probability_delta=0,
                    pressure_band="bullish",
                    pressure_rationale="낮은 공급 우세",
                    related_markets=[],
                ),
            ),
        ],
        delete_scenario_ids=[3],
    )
    result_payload = ValidationOperationResultPayload(
        mode="changed",
        base_scenario_fingerprint=analysis.base_scenario_fingerprint,
        dimension_definition_fingerprint=analysis.dimension_definition_fingerprint,
        validation_result=ValidationResultPayload(
            verdict="PASS",
            is_valid=True,
            can_proceed=True,
            reason_markdown="변경 통과",
        ),
        scenario_change_set=change_set,
    )
    group = SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=101,
        stage="scenario_validated",
        api_version="v4",
        dimension_definitions=deepcopy(DEFINITIONS),
    )

    def model(item: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(**deepcopy(item))

    current_models = [model(item) for item in _scenarios()]
    new_model = model(
        {
            "scenario_id": 4,
            "scenario_group_id": 10,
            "display_order": 4,
            "title": "신규 약상방",
            "narrative": "신규 narrative",
            "dimension_values": {"demand": "demand_low", "supply": "supply_low"},
            "probability_score": 10,
            "probability_delta": 0,
            "baseline_yn": "N",
            "global_pressure_band": "bullish",
            "scenario_role": None,
            "global_pressure_rationale": "낮은 공급 우세",
            "related_markets": [],
            "status": "creating",
        }
    )
    active_models = [current_models[0], current_models[1], new_model]
    session = Mock()
    scenario_repository = Mock()
    scenario_repository.fetch_models_by_group_id.side_effect = [current_models, active_models]
    scenario_repository.insert_scenario.return_value = 4

    def update_from_payload(target: SimpleNamespace, payload: dict[str, object]) -> None:
        for key, value in payload.items():
            setattr(target, key, value)

    scenario_repository.update_from_payload.side_effect = update_from_payload
    scenario_repository.model_to_dict.side_effect = lambda target: {
        key: getattr(target, key)
        for key in (
            "scenario_id",
            "scenario_group_id",
            "display_order",
            "title",
            "narrative",
            "dimension_values",
            "probability_score",
            "probability_delta",
            "baseline_yn",
            "global_pressure_band",
            "scenario_role",
            "global_pressure_rationale",
            "related_markets",
            "status",
        )
    }
    group_repository = Mock()
    group_repository.fetch_by_id.return_value = group
    group_repository.model_to_dict.return_value = {
        "scenario_group_id": 10,
        "status": "creating",
        "stage": "scenario_validated",
    }
    signpost_repository = Mock()
    validation_operation = SimpleNamespace(
        operation_id="validation-op",
        status="succeeded",
        result_payload=result_payload.model_dump(mode="json", by_alias=True),
    )
    signpost_operation = SimpleNamespace(result_payload=None)
    operation_repository = Mock()
    operation_repository.fetch_active.return_value = None
    operation_repository.fetch_latest_by_type.return_value = validation_operation
    operation_repository.fetch_by_id.return_value = signpost_operation

    with (
        patch.dict(
            sys.modules,
            {
                "apps.common.configs.database.sync_database.connection": SimpleNamespace(
                    get_sync_session=lambda: session,
                ),
            },
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioRepository",
            return_value=scenario_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.ScenarioGroupRepository",
            return_value=group_repository,
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_service.SignpostRepository",
            return_value=signpost_repository,
        ),
        patch(
            "apps.persistence.scenario_group_operation.repository.ScenarioGroupOperationRepository",
            return_value=operation_repository,
        ),
        patch.object(
            ScenarioGroupOperationService,
            "create_accepted_in_session",
            return_value=Mock(),
        ),
        patch(
            "apps.agents.scenario_group_agent.persistence.scenario_group_operation_service.new_operation_id",
            return_value="signpost-op",
        ),
    ):
        accepted = ScenarioService().accept_validation_change_set(scenario_group_id=10, user_id=101)

    assert accepted["signpost_target_scenario_ids"] == [1, 4]
    scenario_repository.update_from_payload.assert_called_once()
    scenario_repository.insert_scenario.assert_called_once()
    scenario_repository.soft_delete_by_ids.assert_called_once_with([3], user_id=101)
    signpost_repository.soft_delete_by_scenario_ids.assert_called_once_with([1, 3], user_id=101)
    stored = ValidationOperationResultPayload.model_validate(validation_operation.result_payload)
    assert stored.application is not None
    assert stored.application.new_scenario_id_map == {"new:4": 4}
    assert signpost_operation.result_payload["validationOperationId"] == "validation-op"


def test_v4_role_recalculation_keeps_floor_and_ceiling_distinct_on_ties() -> None:
    scenarios = [
        SimpleNamespace(
            scenario_id=index,
            display_order=index,
            probability_score=30 if index == 2 else 20,
            dimension_values={"demand": "demand_low", "supply": "supply_high"},
            global_pressure_band="balanced",
            baseline_yn="N",
            scenario_role=None,
            mod_usr_logn_id=None,
        )
        for index in range(1, 4)
    ]
    balanced_definitions = deepcopy(DEFINITIONS)
    for definition in balanced_definitions:
        for value in definition["values"]:
            value["pressure_contribution"] = "balanced"

    ScenarioService()._apply_v4_baseline_and_roles(scenarios, balanced_definitions, user_id=101)

    assert scenarios[0].scenario_role == "floor"
    assert scenarios[-1].scenario_role == "ceiling"
    assert scenarios[1].baseline_yn == "Y"


@pytest.mark.parametrize(
    ("mutation", "check_id"),
    [
        (lambda table: table["rows"][0]["cells"].update({"demand": "outside"}), "V4_VALUE_ENUM"),
        (lambda table: table["rows"][0]["cells"].pop("supply"), "V4_INPUT_CELLS"),
        (lambda table: table["rows"][1].update({"title": "상 방!!"}), "V4_TITLE_DUPLICATE"),
        (
            lambda table: table["rows"][1].update({"cells": deepcopy(table["rows"][0]["cells"])}),
            "V4_COMBINATION_DUPLICATE",
        ),
    ],
)
def test_deterministic_v4_input_checks_block(
    mutation: Callable[[dict[str, object]], object],
    check_id: str,
) -> None:
    table = _table()
    mutation(table)

    analysis = _analyze(table)

    assert analysis.blocking is True
    assert any(check.check_id == check_id and check.blocking for check in analysis.checks)


@pytest.mark.parametrize(("row_count", "blocking"), [(1, True), (2, False), (7, False), (8, True)])
def test_v4_scenario_count_accepts_two_through_seven(row_count: int, blocking: bool) -> None:
    base_rows = _table()["rows"]
    rows = []
    for index in range(row_count):
        source = deepcopy(base_rows[index % len(base_rows)])
        source["scenarioId"] = None
        source["displayOrder"] = index + 1
        source["title"] = f"시나리오 {index + 1}"
        source["cells"] = {
            "demand": f"demand_{'high' if index % 2 == 0 else 'low'}",
            "supply": f"supply_{'low' if index // 2 % 2 == 0 else 'high'}",
        }
        rows.append(source)
    analysis = _analyze({"headers": _table()["headers"], "rows": rows})

    count_checks = [check for check in analysis.checks if check.check_id == "V4_SCENARIO_COUNT"]
    assert bool(count_checks) is blocking


def test_low_probability_excluded_combination_warns_but_can_proceed() -> None:
    table = _table()
    table["rows"][0]["title"] = "상방 수정"
    diagnostics = {
        "excludedCandidates": [
            {
                "reasonCode": "LOW_PROBABILITY",
                "reason": "관측 사실 대비 가능성이 낮습니다.",
                "dimensionValues": {"demand": "demand_high", "supply": "supply_low"},
            }
        ]
    }

    analysis = _analyze(table, diagnostics)

    warning = next(check for check in analysis.checks if check.check_id == "V4_LOW_PROBABILITY_REINTRODUCED")
    assert warning.status == "WARN"
    assert warning.blocking is False


def test_changed_v4_result_stores_only_changed_full_upsert() -> None:
    table = _table()
    table["rows"][0]["title"] = "상방 제목 수정"
    table["rows"][1]["cells"] = {"demand": "demand_low", "supply": "supply_low"}
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=101,
        operation_id="validation-op",
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            request_usr_id=101,
            dimension_selected=["demand", "supply"],
            generation_strategy="multi_event_model_lever_dimensions",
            api_version="v4",
            dimension_definitions=DEFINITIONS,
        ),
        scenarios=[ScenarioPayload.model_validate(item) for item in _scenarios()],
        dimension_template=[
            ScenarioTemplateDimension(
                dimension_id=definition["dimension_id"],
                label_ko=definition["label"],
                description=definition["label"],
                enum=[
                    ScenarioTemplateEnum(id=value["value_id"], label=value["label"]) for value in definition["values"]
                ],
            )
            for definition in DEFINITIONS
        ],
        request_table=table,
    )
    report = ReviewReport(
        verdict="PASS",
        is_valid=True,
        reason="통과",
        summary={"PASS": 1, "WARN": 0, "FAIL": 0, "INFO": 0},
        checks=[],
    )
    review_subgraph = SimpleNamespace(
        ainvoke=AsyncMock(return_value=ScenarioReviewState(report=report)),
    )
    generated = V4ValidationGeneratedScenariosOutput(
        items=[
            V4ValidationGeneratedScenario(
                client_row_key="scenario:2",
                narrative="변경 조합 narrative",
                probability_score=25,
                pressure_band="bearish",
                pressure_rationale="공급과 수요 조합의 하방 압력",
                related_markets=[],
            )
        ]
    )

    with (
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes.get_scenario_review_subgraph",
            return_value=review_subgraph,
        ),
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes._invoke_v4_generated_fields",
            new=AsyncMock(return_value=generated),
        ),
    ):
        result = asyncio.run(_run_v4_scenario_validation(state, runtime=None))

    operation_result = ValidationOperationResultPayload.model_validate(result["operation_result"])
    change_set = operation_result.scenario_change_set
    assert operation_result.mode == "changed"
    assert operation_result.validation_result.can_proceed is True
    assert change_set is not None
    assert [upsert.scenario_id for upsert in change_set.upserts] == [1, 2]
    assert all(upsert.generated_fields.narrative for upsert in change_set.upserts)
    assert change_set.upserts[0].generated_fields.narrative == "상방 narrative"
    assert change_set.upserts[1].generated_fields.probability_delta == 0
    assert not hasattr(change_set.upserts[1], "lever_state")


def test_unchanged_v4_skips_review_and_generation() -> None:
    state = ValidateScenariosState(
        scenario_group_id=10,
        user_id=101,
        operation_id="validation-op",
        scenario_group=ScenarioGroupPayload(
            scenario_group_id=10,
            request_usr_id=101,
            dimension_selected=["demand", "supply"],
            generation_strategy="multi_event_model_lever_dimensions",
            api_version="v4",
            dimension_definitions=DEFINITIONS,
        ),
        scenarios=[ScenarioPayload.model_validate(item) for item in _scenarios()],
        request_table=_table(labels=True),
    )

    with (
        patch("apps.agents.scenario_group_agent.flows.validate_scenarios.nodes.get_scenario_review_subgraph") as review,
        patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes._invoke_v4_generated_fields"
        ) as generate,
    ):
        result = asyncio.run(_run_v4_scenario_validation(state, runtime=None))

    operation_result = ValidationOperationResultPayload.model_validate(result["operation_result"])
    assert operation_result.mode == "unchanged"
    assert operation_result.scenario_change_set is None
    assert operation_result.validation_result.review_skipped is True
    review.assert_not_called()
    generate.assert_not_called()
