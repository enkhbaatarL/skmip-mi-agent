# ruff: noqa: I001, S101

from __future__ import annotations

import unittest
from unittest.mock import patch

from apps.agents.scenario_group_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
)
from apps.agents.scenario_group_agent.persistence.signpost.models import MiSignpostModel
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.agents.scenario_group_agent.schemas.confirm_generation import (
    ConfirmGenerationIn,
)
from apps.agents.scenario_group_agent.schemas.create_scenarios import CreateScenariosIn
from apps.agents.scenario_group_agent.schemas.validate_scenarios import (
    ValidateScenariosData,
    ValidateScenariosIn,
)

SCENARIO_GROUP = {
    "scenarioGroupId": 10,
    "miEventId": 20,
    "eventTypeL2Id": 30,
    "title": "group",
    "summary": None,
    "description": None,
}
TABLE = {
    "headers": [{"key": "period", "label": "기간", "displayOrder": 1}],
    "rows": [{"scenarioId": 100, "cells": {"period": "단기"}}],
}


class ScenarioGroupAgentContractTest(unittest.TestCase):
    def test_create_request_accepts_camel_case(self) -> None:
        payload = CreateScenariosIn.model_validate(
            {"miEventId": 20, "userId": "tester"},
        )

        assert payload.mi_event_id == 20
        assert payload.user_id == "tester"

    def test_create_request_also_accepts_internal_snake_case(self) -> None:
        payload = CreateScenariosIn.model_validate(
            {"mi_event_id": 20, "user_id": "tester"},
        )

        assert payload.mi_event_id == 20
        assert payload.user_id == "tester"

    def test_validation_request_accepts_document_shape(self) -> None:
        payload = ValidateScenariosIn.model_validate(
            {
                "userId": "tester",
                "scenarioGroup": SCENARIO_GROUP,
                "table": TABLE,
            },
        )

        assert payload.scenario_group.scenario_group_id == 10
        assert payload.table.rows[0].scenario_id == 100

    def test_confirmation_request_accepts_document_shape(self) -> None:
        payload = ConfirmGenerationIn.model_validate(
            {
                "scenarioGroup": SCENARIO_GROUP,
                "table": TABLE,
            },
        )

        assert payload.scenario_group.mi_event_id == 20

    def test_confirmation_exclude_unset_preserves_partial_update(self) -> None:
        payload = ConfirmGenerationIn.model_validate(
            {
                "scenarioGroup": SCENARIO_GROUP,
                "table": TABLE,
            },
        )

        serialized = payload.model_dump(exclude_unset=True)
        assert "dimension_selected" not in serialized["scenario_group"]
        assert "metrics" not in serialized["table"]["rows"][0]
        assert "impact" not in serialized["table"]["rows"][0]

    def test_response_serializes_camel_case(self) -> None:
        payload = ValidateScenariosData(
            scenario_group_id=10,
            is_valid=True,
            reason="ok",
            status="creating",
            stage="scenario_validated",
        )

        serialized = payload.model_dump(by_alias=True)
        assert serialized["scenarioGroupId"] == 10
        assert serialized["isValid"]
        assert "scenario_group_id" not in serialized

    def test_scenario_insert_payload_matches_orm(self) -> None:
        payload = {
            "scenario_group_id": 10,
            "title": "scenario",
            "narrative": "narrative",
            "status": "created",
            "dimension_values": [{"dimension_id": "period", "value": "period_v1"}],
            "probability_score": 75,
            "probability_delta": None,
            "impact_jkm": "up",
            "impact_ttf": "flat",
            "impact_hh": "down",
            "display_order": 1,
            "baseline_yn": "Y",
            "crt_usr_logn_id": "tester",
            "mod_usr_logn_id": "tester",
        }

        scenario = MiScenarioModel(**payload)
        assert scenario.status == "created"

    def test_scenario_group_insert_payload_matches_orm(self) -> None:
        payload = {
            "mi_event_id": 20,
            "event_type_l2_id": 30,
            "title": "group",
            "summary": "summary",
            "description": "description",
            "dimension_selected": ["period"],
            "scenario_count": 1,
            "status": "creating",
            "stage": "ready",
            "crt_usr_logn_id": "tester",
            "mod_usr_logn_id": "tester",
        }

        group = MiScenarioGroupModel(**payload)
        assert group.stage == "ready"

    def test_signpost_insert_payload_matches_orm(self) -> None:
        payload = {
            "scenario_id": 100,
            "label": "signal",
            "probability_direction_code": "SUP",
            "probability_impact_score": 1,
            "signpost_reason": "reason",
            "display_order": 1,
            "crt_usr_logn_id": "tester",
            "mod_usr_logn_id": "tester",
        }

        signpost = MiSignpostModel(**payload)
        assert signpost.label == "signal"

    def test_dimension_label_conversion_and_response_table(self) -> None:
        template = [
            {
                "dim_key": "period",
                "label": "기간",
                "display_order": 1,
                "value_enums": ["단기", "장기"],
            },
        ]
        group = {
            "scenario_group_id": 10,
            "mi_event_id": 20,
            "event_type_l2_id": 30,
            "title": "group",
            "summary": None,
            "description": None,
            "dimension_selected": ["period"],
            "scenario_count": 1,
            "status": "creating",
            "stage": "scenario_created",
        }
        scenarios = [
            {
                "scenario_id": 100,
                "title": "scenario",
                "narrative": "narrative",
                "dimension_values": {"period": "period_v1"},
                "display_order": 1,
                "baseline_yn": "Y",
            },
        ]

        with patch.object(
            ScenarioService,
            "_load_template_json_from_db",
            return_value=template,
        ):
            result = build_scenario_group_table_data(group, scenarios)

        serialized = result.model_dump(by_alias=True)
        assert serialized["table"]["headers"][0]["label"] == "기간"
        assert serialized["table"]["rows"][0]["cells"]["period"] == "단기"


if __name__ == "__main__":
    unittest.main()
