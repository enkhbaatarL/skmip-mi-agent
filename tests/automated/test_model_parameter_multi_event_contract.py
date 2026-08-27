# ruff: noqa: S101, SLF001

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy.dialects import mysql

from apps.common.configs.database.application_tables import APPLICATION_TABLES
from apps.persistence.model_parameter.models import MiModelParamProposalModel
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.model_parameter.schema import ModelParameterProposalPayload
from apps.persistence.scenario.models import MiDimensionValueMappingModel
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
)
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


class _ScalarResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def all(self) -> list[object]:
        return self._rows


class _ExecuteResult:
    def __init__(self, rows: list[object]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._rows)


def test_multi_event_persistence_tables_are_registered_for_startup_validation() -> None:
    table_names = {table.name for table in APPLICATION_TABLES}

    assert MiScenarioGroupEventModel.__tablename__ in table_names
    assert MiDimensionValueMappingModel.__tablename__ in table_names


def test_scenario_group_uses_event_relations_and_proposal_event_is_nullable() -> None:
    assert "mi_event_id" not in MiScenarioGroupModel.__table__.c
    assert "event_type_l2_id" not in MiScenarioGroupModel.__table__.c
    assert MiModelParamProposalModel.__table__.c.mi_event_id.nullable is True

    expected_group_columns = {
        "api_version",
        "generation_strategy",
        "comparison_run_id",
        "impact_catalog_version",
        "impact_catalog_checksum",
        "template_checksum",
        "parameter_mapping_ready",
        "dimension_definitions",
        "generation_diagnostics",
    }
    assert expected_group_columns <= set(MiScenarioGroupModel.__table__.c.keys())


def test_scenario_group_payload_and_serializer_preserve_optional_event_ids() -> None:
    group = SimpleNamespace(
        scenario_group_id=20,
        request_usr_id=40,
        title="multi-event",
        summary="summary",
        description="description",
        dimension_selected=["composite_pressure"],
        scenario_count=1,
        status="creating",
        stage="scenario_created",
        api_version="v3",
        generation_strategy="multi_event_composite_dimensions",
        comparison_run_id="comparison-1",
        impact_catalog_version=None,
        impact_catalog_checksum=None,
        template_checksum="checksum",
        parameter_mapping_ready=False,
        dimension_definitions=[{"dimension_id": "composite_pressure"}],
        generation_diagnostics={"validation_warnings": []},
        del_yn="N",
        mod_dtm=None,
    )

    payload = ScenarioGroupPayload.from_model(group)
    repository = ScenarioGroupRepository(session=Mock())
    repository.fetch_single_active_group_event = Mock(return_value=None)
    serialized = repository.model_to_dict(group)

    assert payload.mi_event_id is None
    assert payload.event_type_l2_id is None
    assert payload.api_version == "v3"
    assert payload.dimension_definitions == [{"dimension_id": "composite_pressure"}]
    assert serialized["mi_event_id"] is None
    assert serialized["event_type_l2_id"] is None
    assert serialized["generation_strategy"] == "multi_event_composite_dimensions"


def test_group_event_query_preserves_display_order_contract() -> None:
    session = Mock()
    relations = [SimpleNamespace(scenario_group_event_id=1)]
    session.execute.return_value = _ExecuteResult(relations)

    result = ScenarioGroupRepository(session=session).fetch_group_events(20)
    stmt = session.execute.call_args.args[0]
    compiled = str(
        stmt.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        ),
    )

    assert result == relations
    assert "tmm_mi_scenario_group_event_m.del_yn = 'N'" in compiled
    assert "ORDER BY tmm_mi_scenario_group_event_m.display_order" in compiled
    assert "tmm_mi_scenario_group_event_m.scenario_group_event_id" in compiled


def test_dimension_value_mapping_query_returns_active_rows_in_stable_order() -> None:
    session = Mock()
    mappings = [SimpleNamespace(dimension_value_mapping_id=1)]
    session.execute.return_value = _ExecuteResult(mappings)

    result = ScenarioRepository(session=session).fetch_mappings_by_group_id(20)
    stmt = session.execute.call_args.args[0]
    compiled = str(
        stmt.compile(
            dialect=mysql.dialect(),
            compile_kwargs={"literal_binds": True},
        ),
    )

    assert result == mappings
    assert "tmm_mi_dimension_value_mapping_m.del_yn = 'N'" in compiled
    assert "ORDER BY tmm_mi_dimension_value_mapping_m.dimension_id" in compiled
    assert "tmm_mi_dimension_value_mapping_m.dimension_value_id" in compiled


def test_model_parameter_proposal_creation_accepts_null_event_id() -> None:
    class FakeSession:
        def __init__(self) -> None:
            self.added: MiModelParamProposalModel | None = None

        def add(self, value: MiModelParamProposalModel) -> None:
            self.added = value

        def flush(self) -> None:
            assert self.added is not None
            self.added.model_param_proposal_id = 901

    session = FakeSession()
    proposal_id = ModelParameterRepository(session=session).create_processing_model_param_proposal(
        scenario_id=100,
        scenario_group_id=20,
        mi_event_id=None,
        request_usr_id=40,
    )

    assert proposal_id == 901
    assert session.added is not None
    assert session.added.mi_event_id is None


def test_model_parameter_proposal_serializers_preserve_null_event_id() -> None:
    proposal = SimpleNamespace(
        model_param_proposal_id=901,
        scenario_id=100,
        scenario_group_id=20,
        mi_event_id=None,
        status="PROPOSED",
        callback_status="SKIPPED",
        proposal_parameters=[{"parameterName": "PowerMix"}],
        confirmation_parameters=None,
    )
    direct = ModelParameterRepository._proposal_to_dict(proposal)

    session = Mock()
    session.execute.return_value = _ExecuteResult([proposal])
    by_group = ModelParameterRepository(session=session).fetch_proposals_by_group(20)
    payload = ModelParameterProposalPayload(
        model_param_proposal_id=901,
        scenario_id=100,
        scenario_group_id=20,
        status="PROPOSED",
    )

    assert direct is not None
    assert direct["mi_event_id"] is None
    assert by_group[0]["mi_event_id"] is None
    assert payload.mi_event_id is None
    assert payload.model_dump(by_alias=True)["miEventId"] is None
