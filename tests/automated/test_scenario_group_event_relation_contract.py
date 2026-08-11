from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from apps.persistence.scenario_group.models import MiScenarioGroupModel
from apps.persistence.scenario_group.repository import ScenarioGroupRepository
from apps.persistence.scenario_group.schema import ScenarioGroupPayload


def _group() -> SimpleNamespace:
    return SimpleNamespace(
        scenario_group_id=10,
        request_usr_id=101,
        title="group",
        summary=None,
        description=None,
        dimension_selected=[],
        scenario_count=0,
        status="creating",
        stage="ready",
        api_version="v1",
        generation_strategy="single_event_template_dimensions",
        impact_catalog_version=None,
        impact_catalog_checksum=None,
        template_checksum="checksum",
        parameter_mapping_ready=False,
        dimension_definitions=[],
        generation_diagnostics={},
    )


def test_scenario_group_master_has_no_direct_event_columns() -> None:
    assert "mi_event_id" not in MiScenarioGroupModel.__table__.columns
    assert "event_type_l2_id" not in MiScenarioGroupModel.__table__.columns
    assert "idx_tmm_mi_scenario_group_m_01" not in {index.name for index in MiScenarioGroupModel.__table__.indexes}
    assert "idx_tmm_mi_scenario_group_m_02" not in {index.name for index in MiScenarioGroupModel.__table__.indexes}


def test_single_active_relation_populates_compatibility_fields() -> None:
    relation = SimpleNamespace(mi_event_id=20, event_type_l2_id=30)

    payload = ScenarioGroupPayload.from_model(_group(), relation)

    assert payload.mi_event_id == 20
    assert payload.event_type_l2_id == 30


def test_multiple_active_relations_do_not_create_representative_event() -> None:
    repository = ScenarioGroupRepository(session=Mock())
    repository.fetch_group_events = Mock(
        return_value=[
            SimpleNamespace(mi_event_id=20, event_type_l2_id=30),
            SimpleNamespace(mi_event_id=21, event_type_l2_id=31),
        ]
    )

    relation = repository.fetch_single_active_group_event(10)
    payload = ScenarioGroupPayload.from_model(_group(), relation)

    assert relation is None
    assert payload.mi_event_id is None
    assert payload.event_type_l2_id is None
