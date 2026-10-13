# Copyright (c) 2026 SK Innovation E&S.
# ruff: noqa: S101

from __future__ import annotations

from collections.abc import Iterator
import os
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from apps.common.configs.database.schema_validation import (
    find_schema_validation_result,
)
from apps.persistence.event.models import (
    MiEventModel,
    MiEventTypeL1Model,
    MiEventTypeL2Model,
)
from apps.persistence.model_parameter.models import MiModelParamProposalModel
from apps.persistence.model_parameter.repository import ModelParameterRepository
from apps.persistence.scenario.models import (
    MiDimensionValueMappingModel,
    MiScenarioDimensionTemplateModel,
    MiScenarioModel,
)
from apps.persistence.scenario.repository import ScenarioRepository
from apps.persistence.scenario_group.models import (
    MiScenarioGroupEventModel,
    MiScenarioGroupModel,
)
from apps.persistence.scenario_group.repository import ScenarioGroupRepository


TEST_DATABASE_URL_ENV = "MODEL_PARAMETER_MULTI_EVENT_TEST_DATABASE_URL"
SAFE_DATABASE_PATTERN = re.compile(r"model_parameter_multi_event_test_[A-Za-z0-9_]+")
TEST_TABLES = (
    MiEventTypeL1Model.__table__,
    MiEventTypeL2Model.__table__,
    MiEventModel.__table__,
    MiScenarioGroupModel.__table__,
    MiScenarioDimensionTemplateModel.__table__,
    MiScenarioGroupEventModel.__table__,
    MiScenarioModel.__table__,
    MiDimensionValueMappingModel.__table__,
    MiModelParamProposalModel.__table__,
)


@pytest.fixture
def disposable_mysql_session() -> Iterator[Session]:
    database_url = os.getenv(TEST_DATABASE_URL_ENV)
    if not database_url:
        pytest.skip(f"{TEST_DATABASE_URL_ENV} is not configured")

    database_name = make_url(database_url).database or ""
    if SAFE_DATABASE_PATTERN.fullmatch(database_name) is None:
        pytest.fail(
            f"refusing destructive integration setup for unsafe database: {database_name!r}",
        )

    engine = create_engine(database_url, pool_pre_ping=True)
    session = Session(engine)
    try:
        for table in reversed(TEST_TABLES):
            table.drop(engine, checkfirst=True)
        for table in TEST_TABLES:
            table.create(engine, checkfirst=False)
        yield session
    finally:
        session.rollback()
        session.close()
        for table in reversed(TEST_TABLES):
            table.drop(engine, checkfirst=True)
        engine.dispose()


def test_nullable_proposal_and_v3_relations_round_trip_in_disposable_mysql(
    disposable_mysql_session: Session,
) -> None:
    session = disposable_mysql_session
    session.add(
        MiEventTypeL1Model(
            event_type_l1_id=1,
            level_1_code="SUPPLY",
            level_1_label="공급",
        ),
    )
    session.add_all(
        [
            MiEventTypeL2Model(
                event_type_l2_id=11,
                event_type_l1_id=1,
                level_2_code="SUPPLY_A",
                level_2_label="공급 A",
            ),
            MiEventTypeL2Model(
                event_type_l2_id=12,
                event_type_l1_id=1,
                level_2_code="SUPPLY_B",
                level_2_label="공급 B",
            ),
        ],
    )
    session.add_all(
        [
            MiEventModel(
                mi_event_id=101,
                event_type_l2_id=11,
                one_line_summary="이벤트 A",
                search_text="요약 A",
                key_bullets_json=["A"],
                detail_analysis="상세 A",
                tags_json=["supply"],
            ),
            MiEventModel(
                mi_event_id=102,
                event_type_l2_id=12,
                one_line_summary="이벤트 B",
                search_text="요약 B",
                key_bullets_json=["B"],
                detail_analysis="상세 B",
                tags_json=["supply"],
            ),
        ],
    )
    session.flush()

    definition = {
        "dimensionId": "composite_pressure",
        "label": "복합 압력",
        "sourceEventIds": [101, 102],
        "sourceRefs": [
            {"scenarioDimensionTemplateId": 1001, "dimKey": "source_a"},
            {"scenarioDimensionTemplateId": 1002, "dimKey": "source_b"},
        ],
        "values": [],
    }
    session.add(
        MiScenarioGroupModel(
            scenario_group_id=701,
            mi_event_id=None,
            event_type_l2_id=None,
            title="멀티 이벤트 그룹",
            dimension_selected=["composite_pressure"],
            scenario_count=1,
            status="created",
            stage="scenario_created",
            api_version="v3",
            generation_strategy="multi_event_composite_dimensions",
            parameter_mapping_ready=False,
            dimension_definitions=[definition],
            generation_diagnostics={},
        ),
    )
    session.add_all(
        [
            MiScenarioDimensionTemplateModel(
                scenario_dimension_template_id=1001,
                event_type_l2_id=11,
                template_json=[],
            ),
            MiScenarioDimensionTemplateModel(
                scenario_dimension_template_id=1002,
                event_type_l2_id=12,
                template_json=[],
            ),
        ],
    )
    session.flush()
    session.add_all(
        [
            MiScenarioGroupEventModel(
                scenario_group_id=701,
                mi_event_id=102,
                event_type_l2_id=12,
                scenario_dimension_template_id=1002,
                display_order=2,
            ),
            MiScenarioGroupEventModel(
                scenario_group_id=701,
                mi_event_id=101,
                event_type_l2_id=11,
                scenario_dimension_template_id=1001,
                display_order=1,
            ),
        ],
    )
    session.add(
        MiScenarioModel(
            scenario_id=501,
            scenario_group_id=701,
            title="복합 시나리오",
            narrative="두 이벤트를 함께 반영한다.",
            status="created",
            dimension_values={"composite_pressure": "사용자 압력"},
            display_order=1,
            baseline_yn="N",
        ),
    )
    session.add(
        MiDimensionValueMappingModel(
            scenario_group_id=701,
            dimension_value_id="dv-test",
            dimension_id="composite_pressure",
            display_value="사용자 압력",
            source_projections=[
                {
                    "scenario_dimension_template_id": 1001,
                    "dim_key": "source_a",
                    "value": "high",
                },
            ],
            mapping_proposal={"status": "approved"},
            mapping_version=1,
            status="approved",
        ),
    )
    session.flush()

    proposal_id = ModelParameterRepository(
        session=session,
    ).create_processing_model_param_proposal(
        scenario_id=501,
        scenario_group_id=701,
        mi_event_id=None,
        request_usr_id=None,
    )
    session.commit()

    relations = ScenarioGroupRepository(session=session).fetch_group_events(701)
    mappings = ScenarioRepository(session=session).fetch_mappings_by_group_id(701)
    proposal = ModelParameterRepository(session=session).fetch_model_param_proposal(
        proposal_id,
    )
    schema_result = find_schema_validation_result(session.get_bind(), TEST_TABLES)

    assert [int(item.mi_event_id) for item in relations] == [101, 102]
    assert mappings[0].status == "approved"
    assert proposal is not None
    assert proposal["scenario_group_id"] == 701
    assert proposal["mi_event_id"] is None
    assert schema_result.errors == []
