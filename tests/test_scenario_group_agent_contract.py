# ruff: noqa: I001, S101, SLF001

from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import ValidationError

from apps.agents.scenario_group_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
)
from apps.agents.scenario_group_agent.persistence.signpost.models import MiSignpostModel
from apps.agents.scenario_group_agent.flows.create_scenarios.nodes import (
    save_scenario_group,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    load_scenario_group as load_validation_scenario_group,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.flow import build_graph
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.agents.scenario_group_agent.schemas.confirm_generation import (
    ConfirmGenerationIn,
)
from apps.agents.scenario_group_agent.schemas.create_scenarios import CreateScenariosIn
from apps.agents.scenario_group_agent.schemas.create_signposts import CreateSignpostsIn
from apps.agents.scenario_group_agent.schemas.validate_scenarios import (
    ValidateScenariosCallBackScenarioGroup,
    ValidateScenariosIn,
    ValidateScenariosOut,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.subgraph_adapter import (
    to_output as scenario_generation_to_output,
    to_state as scenario_generation_to_state,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.pipeline import (
    ScenarioTemplate,
    TemplateDimension,
)
from apps.common.exceptions.custom import MIBaseError

SCENARIO_GROUP = {
    "scenarioGroupId": 10,
    "miEventId": 20,
    "eventTypeL2Id": 30,
    "title": "group",
    "summary": None,
    "description": None,
}
CONFIRM_SCENARIO_GROUP = {
    "title": "group",
    "summary": None,
    "description": None,
}
TABLE = {
    "headers": [{"key": "period", "label": "기간", "displayOrder": 1}],
    "rows": [{"scenarioId": 100, "cells": {"period": "단기"}}],
}
class ScenarioGroupAgentContractTest(unittest.TestCase):
    def test_create_scenarios_graph_registers_generation_subgraph(self) -> None:
        graph = build_graph().get_graph()

        assert "run_scenario_generation" in graph.nodes

    def test_generation_subgraph_adapter_loads_db_template(self) -> None:
        state = ScenarioDesignState(
            event_data={"mi_event_id": "20", "event_type_l2_id": 30},
        )
        template = ScenarioTemplate(
            template_dimensions_total=3,
            dimensions=[
                TemplateDimension(
                    label="기간",
                    dim_key="period",
                    value_enums=["단기", "장기"],
                    display_order=1,
                ),
                TemplateDimension(
                    label="강도",
                    dim_key="intensity",
                    value_enums=["낮음", "높음"],
                    display_order=2,
                ),
                TemplateDimension(
                    label="회복",
                    dim_key="recovery",
                    value_enums=["빠름", "느림"],
                    display_order=3,
                ),
            ],
            compatibility_rules=[],
        )

        with patch(
            "apps.agents.scenario_group_agent.subgraphs.scenario_generation."
            "subgraph_adapter.ScenarioService.load_pipeline_template",
            return_value=template,
        ) as load_template:
            subgraph_state = scenario_generation_to_state(state)

        load_template.assert_called_once_with(30)
        assert subgraph_state.event_data == state.event_data
        assert subgraph_state.template == template

    def test_generation_subgraph_skips_existing_group(self) -> None:
        subgraph_state = scenario_generation_to_state(
            ScenarioDesignState(status="already_exist"),
        )

        assert subgraph_state.skip_generation
        assert scenario_generation_to_output(subgraph_state) == {}

    def test_db_template_maps_to_pipeline_shape(self) -> None:
        template = [
            {
                "dim_key": "third",
                "label": "세 번째",
                "display_order": 3,
                "value_enums": ["낮음", "중간", "높음"],
            },
            {
                "dim_key": "first",
                "label": "첫 번째",
                "display_order": 1,
                "value_enums": ["A", "B", "C", "D", "E"],
            },
            {
                "dim_key": "second",
                "label": "두 번째",
                "display_order": 2,
                "value_enums": ["켜짐", "꺼짐"],
            },
        ]

        result = ScenarioService()._map_template_json_to_pipeline_template(
            template,
            event_type_l2_id=30,
        )

        ordered = result.ordered_dimensions()
        assert [item.dim_key for item in ordered] == [
            "first",
            "second",
            "third",
        ]
        assert [item["id"] for item in ordered[0].enum_items()] == [
            "A",
            "B",
            "C",
            "D",
            "E",
        ]
        assert [item["tail"] for item in ordered[0].enum_items()] == [
            False,
            False,
            False,
            True,
            True,
        ]
        assert [item["tail"] for item in ordered[1].enum_items()] == [False, True]
        assert result.compatibility_rules == []

    def test_db_template_requires_three_dimensions(self) -> None:
        template = [
            {
                "dim_key": "period",
                "label": "기간",
                "display_order": 1,
                "value_enums": ["단기", "장기"],
            },
        ]

        with self.assertRaisesRegex(ValueError, "at least three dimensions"):
            ScenarioService()._map_template_json_to_pipeline_template(
                template,
                event_type_l2_id=30,
            )

    def test_db_template_rejects_duplicate_dimension_keys(self) -> None:
        template = [
            {
                "dim_key": "period",
                "label": "기간",
                "display_order": index,
                "value_enums": ["단기", "장기"],
            }
            for index in range(1, 4)
        ]

        with self.assertRaisesRegex(ValueError, "duplicate dim_key"):
            ScenarioService()._map_template_json_to_pipeline_template(
                template,
                event_type_l2_id=30,
            )

    def test_create_request_accepts_camel_case(self) -> None:
        payload = CreateScenariosIn.model_validate(
            {"miEventId": 20, "userId": 101},
        )

        assert payload.mi_event_id == 20
        assert payload.user_id == 101

    def test_create_request_also_accepts_internal_snake_case(self) -> None:
        payload = CreateScenariosIn.model_validate(
            {"mi_event_id": 20, "user_id": 101},
        )

        assert payload.mi_event_id == 20
        assert payload.user_id == 101

    def test_create_signposts_request_uses_integer_user_id(self) -> None:
        payload = CreateSignpostsIn.model_validate({"userId": 101, "table": TABLE})

        assert payload.user_id == 101

    def test_validation_request_accepts_document_shape(self) -> None:
        payload = ValidateScenariosIn.model_validate(
            {
                "userId": 101,
                "table": TABLE,
            },
        )

        assert payload.table.rows[0].scenario_id == 100
        assert payload.user_id == 101

    def test_scenario_group_insert_uses_integer_user_id_for_audit_fields(
        self,
    ) -> None:
        state = ScenarioDesignState(
            user_id=101,
            event_data={
                "mi_event_id": "20",
                "event_type_l2_id": 30,
                "event_title_ko": "event",
            },
            scenario_result={
                "stage2_dimension_selection": {
                    "selected_dimensions": [{"dim_key": "period"}],
                },
                "stage4_scenario_synthesis": {"scenarios": []},
            },
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
            "ScenarioGroupService.create_group",
            return_value=10,
        ) as create_group:
            save_scenario_group(state)

        payload = create_group.call_args.args[0]
        assert payload["request_usr_id"] == 101
        assert payload["crt_usr_logn_id"] == 101
        assert payload["mod_usr_logn_id"] == 101

    def test_confirmation_request_accepts_document_shape(self) -> None:
        payload = ConfirmGenerationIn.model_validate(
            {
                "userId": 101,
                "scenarioGroup": CONFIRM_SCENARIO_GROUP,
                "table": TABLE,
            },
        )

        assert payload.scenario_group.title == "group"

    def test_confirmation_exclude_unset_preserves_partial_update(self) -> None:
        payload = ConfirmGenerationIn.model_validate(
            {
                "userId": 101,
                "scenarioGroup": CONFIRM_SCENARIO_GROUP,
                "table": TABLE,
            },
        )

        serialized = payload.model_dump(exclude_unset=True)
        assert "dimension_selected" not in serialized["scenario_group"]
        assert "metrics" not in serialized["table"]["rows"][0]
        assert "impact" not in serialized["table"]["rows"][0]

    def test_confirmation_request_requires_user_id(self) -> None:
        with self.assertRaises(ValidationError):
            ConfirmGenerationIn.model_validate(
                {
                    "scenarioGroup": CONFIRM_SCENARIO_GROUP,
                    "table": TABLE,
                },
            )

    def test_validation_rejects_scenario_group_owned_by_other_user(self) -> None:
        with patch(
            "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
            "ScenarioGroupService.load_by_id",
            return_value={"scenario_group_id": 10, "request_usr_id": 202},
        ):
            with self.assertRaises(MIBaseError) as context:
                load_validation_scenario_group(
                    ScenarioDesignState(scenario_group_id=10, user_id=101),
                )

        assert context.exception.status_code == 401

    def test_baseline_uses_highest_probability_and_all_ties(self) -> None:
        scenarios = [
            MiScenarioModel(
                scenario_group_id=10,
                title="low",
                narrative="",
                status="creating",
                dimension_values={},
                probability_score=50,
                display_order=1,
            ),
            MiScenarioModel(
                scenario_group_id=10,
                title="high-a",
                narrative="",
                status="creating",
                dimension_values={},
                probability_score=75,
                display_order=2,
            ),
            MiScenarioModel(
                scenario_group_id=10,
                title="high-b",
                narrative="",
                status="creating",
                dimension_values={},
                probability_score=75,
                display_order=3,
            ),
        ]

        ScenarioService().apply_baseline_by_probability(scenarios, user_id=101)

        assert [scenario.baseline_yn for scenario in scenarios] == ["N", "Y", "Y"]

    def test_baseline_all_null_probability_sets_all_non_baseline(self) -> None:
        scenarios = [
            MiScenarioModel(
                scenario_group_id=10,
                title="a",
                narrative="",
                status="creating",
                dimension_values={},
                probability_score=None,
                display_order=1,
            ),
            MiScenarioModel(
                scenario_group_id=10,
                title="b",
                narrative="",
                status="creating",
                dimension_values={},
                probability_score=None,
                display_order=2,
            ),
        ]

        ScenarioService().apply_baseline_by_probability(scenarios, user_id=101)

        assert [scenario.baseline_yn for scenario in scenarios] == ["N", "N"]

    def test_response_serializes_camel_case(self) -> None:
        payload = ValidateScenariosOut(
            result="success",
            is_valid=True,
            reason="ok",
            scenario_group=ValidateScenariosCallBackScenarioGroup(
                scenario_group_id=10,
                status="creating",
                stage="scenario_validated",
            ),
            table=None,
        )

        serialized = payload.model_dump(by_alias=True)
        assert serialized["result"] == "success"
        assert serialized["isValid"]
        assert serialized["scenarioGroup"]["scenarioGroupId"] == 10
        assert serialized["scenarioGroup"]["stage"] == "scenario_validated"

    def test_scenario_insert_payload_matches_orm(self) -> None:
        payload = {
            "scenario_group_id": 10,
            "title": "scenario",
            "narrative": "narrative",
            "status": "created",
            "dimension_values": {"period": "period_v1"},
            "probability_score": 75,
            "probability_delta": None,
            "impact_jkm": "up",
            "impact_ttf": "flat",
            "impact_hh": "down",
            "display_order": 1,
            "baseline_yn": "Y",
            "crt_usr_logn_id": 101,
            "mod_usr_logn_id": 101,
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
            "crt_usr_logn_id": 101,
            "mod_usr_logn_id": 101,
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
            "crt_usr_logn_id": 101,
            "mod_usr_logn_id": 101,
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
