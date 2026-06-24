# ruff: noqa: I001, S101, SLF001

from __future__ import annotations

from decimal import Decimal
import unittest
import sys
import types
from unittest.mock import Mock, patch

from pydantic import ValidationError

from apps.agents.scenario_group_agent.baseline_contrast import (
    check_baseline_contrast_coverage,
)
from apps.agents.scenario_group_agent.persistence.scenario.models import MiScenarioModel
from apps.agents.scenario_group_agent.persistence.scenario.service import (
    NewScenarioGeneratedDetails,
    ScenarioService,
)
from apps.agents.scenario_group_agent.persistence.scenario_group.models import (
    MiScenarioGroupModel,
)
from apps.agents.scenario_group_agent.persistence.signpost.models import MiSignpostModel
from apps.agents.scenario_group_agent.flows.create_scenarios.nodes import (
    check_existing_scenario_group,
    create_group_record,
    save_scenario_group,
    save_scenarios,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.flow_async import (
    prepare_create_scenarios,
)
from apps.agents.scenario_group_agent.flows.validate_scenarios.nodes import (
    load_scenario_group as load_validation_scenario_group,
    save_validation_result,
)
from apps.agents.scenario_group_agent.flows.create_signposts.nodes import (
    save_signposts,
)
from apps.agents.scenario_group_agent.flows.create_scenarios.flow import build_graph
from apps.agents.scenario_group_agent.presentation import (
    build_scenario_group_table_data,
)
from apps.agents.scenario_group_agent.schemas.domain.scenario_group import (
    ScenarioGroupPayload,
)
from apps.agents.scenario_group_agent.schemas.api.confirm_generation import (
    ConfirmGenerationIn,
)
from apps.agents.scenario_group_agent.schemas.api.create_scenarios import CreateScenariosIn
from apps.agents.scenario_group_agent.schemas.api.create_signposts import (
    CreateSignpostsIn,
)
from apps.agents.scenario_group_agent.schemas.graph.generation import SignpostGenerationResult
from apps.agents.scenario_group_agent.schemas.api.manage_scenario_groups import (
    HardDeleteScenarioGroupIn,
    SoftDeleteScenarioGroupIn,
)
from apps.agents.scenario_group_agent.schemas.api.validate_scenarios import (
    ValidateScenariosCallBackScenarioGroup,
    ValidateScenariosIn,
    ValidateScenariosOut,
)
from apps.agents.scenario_group_agent.state import ScenarioDesignState
from apps.agents.scenario_group_agent.persistence.scenario_group.service import (
    ScenarioGroupService,
)
from apps.agents.scenario_group_agent.subgraphs.scenario_generation.subgraph_adapter import (
    to_output as scenario_generation_to_output,
    to_state as scenario_generation_to_state,
)
from apps.agents.scenario_group_agent.schemas.graph.generation import (
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


def scenario_generation_result_stub(
    *,
    scenario_group_metadata: dict[str, str] | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "stage2_dimension_selection": {
            "template_id": "template",
            "template_dimensions_total": 3,
            "selected_dimensions": [
                {"dim_key": "period", "rationale": "(a) period rationale"},
                {"dim_key": "supply", "rationale": "(a) supply rationale"},
                {"dim_key": "demand", "rationale": "(a) demand rationale"},
            ],
        },
        "stage4_scenario_synthesis": {
            "cartesian_total": 1,
            "filtered_by_compatibility": 1,
            "scenarios": [
                {
                    "scenario_id": "S_01",
                    "title": "scenario",
                    "dimension_values": {
                        "period": "short",
                        "supply": "tight",
                        "demand": "high",
                    },
                    "description": "scenario description",
                    "derivation_rationale": "scenario rationale",
                    "price_direction": {
                        "jkm": "neutral",
                        "ttf": "neutral",
                        "hh": "neutral",
                    },
                },
            ],
        },
    }
    if scenario_group_metadata is not None:
        result["scenario_group_metadata"] = scenario_group_metadata
    return result


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
            False,
            False,
        ]
        assert [item["tail"] for item in ordered[1].enum_items()] == [False, False]
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

    def test_ready_existing_group_is_reused_for_create_scenarios(self) -> None:
        state = ScenarioDesignState(mi_event_id=20, user_id=101)
        existing = ScenarioGroupPayload.model_validate({
            "scenario_group_id": 10,
            "mi_event_id": 20,
            "event_type_l2_id": 30,
            "request_usr_id": 101,
            "title": "group",
            "summary": None,
            "description": None,
            "dimension_selected": [],
            "scenario_count": 0,
            "status": "creating",
            "stage": "ready",
        })

        with patch(
            "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
            "ScenarioGroupService.load_by_mi_event_id",
            return_value=existing,
        ):
            result = check_existing_scenario_group(state)

        assert result["scenario_group_id"] == 10
        assert result["scenario_group"]["stage"] == "ready"

    def test_prepare_create_scenarios_reuses_ready_group_without_insert(
        self,
    ) -> None:
        event_data = {
            "mi_event_id": 20,
            "event_type_l2_id": 30,
            "event_title_ko": "event",
        }
        existing = ScenarioGroupPayload.model_validate({
            "scenario_group_id": 10,
            "mi_event_id": 20,
            "event_type_l2_id": 30,
            "request_usr_id": 101,
            "title": "group",
            "summary": None,
            "description": None,
            "dimension_selected": [],
            "scenario_count": 0,
            "status": "creating",
            "stage": "ready",
        })

        with (
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "EventService.load_event",
                return_value=event_data,
            ),
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "ScenarioGroupService.load_by_mi_event_id",
                return_value=existing,
            ),
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.flow_async."
                "create_group_record",
            ) as create_group_record_mock,
        ):
            result = prepare_create_scenarios(mi_event_id=20, user_id=101)

        create_group_record_mock.assert_not_called()
        assert result["scenario_group_id"] == 10
        assert result["status"] == "creating"
        assert result["stage"] == "ready"

    def test_create_signposts_request_uses_integer_user_id(self) -> None:
        payload = CreateSignpostsIn.model_validate({"userId": 101, "table": TABLE})

        assert payload.user_id == 101

    def test_create_signposts_request_rejects_non_request_row_fields(self) -> None:
        table = {
            "headers": [{"key": "period", "label": "기간", "displayOrder": 1}],
            "rows": [
                {
                    "scenarioId": 100,
                    "displayOrder": 1,
                    "title": "scenario",
                    "cells": {"period": "단기"},
                    "narrative": "must not be accepted",
                    "metrics": {"probabilityScore": 40},
                    "impact": {"jkm": "bull"},
                    "baselineYn": "Y",
                    "signposts": [],
                },
            ],
        }

        with self.assertRaises(ValidationError):
            CreateSignpostsIn.model_validate({"userId": 101, "table": table})

    def test_create_signposts_request_rejects_top_level_extra_fields(self) -> None:
        with self.assertRaises(ValidationError):
            CreateSignpostsIn.model_validate(
                {
                    "userId": 101,
                    "table": TABLE,
                    "unexpected": True,
                },
            )

    def test_create_signposts_request_accepts_documented_row_shape(self) -> None:
        table = {
            "headers": [{"key": "period", "label": "기간", "displayOrder": 1}],
            "rows": [
                {
                    "scenarioId": None,
                    "displayOrder": 1,
                    "title": "사용자 추가 시나리오",
                    "cells": {"period": "단기"},
                },
            ],
        }

        payload = CreateSignpostsIn.model_validate({"userId": 101, "table": table})

        assert payload.table.rows[0].scenario_id is None
        assert payload.table.rows[0].cells == {"period": "단기"}

    def test_existing_signpost_sync_payload_preserves_hidden_db_fields(self) -> None:
        payload = ScenarioService()._row_to_existing_scenario_payload(
            template_by_key={"period": {"dim_key": "period"}},
            row={
                "scenario_id": 100,
                "display_order": 2,
                "title": "updated",
                "cells": {"period": "단기", "ignored": "x"},
            },
            user_id=101,
        )

        assert payload == {
            "title": "updated",
            "dimension_values": {"period": "단기"},
            "display_order": 2,
            "mod_usr_logn_id": 101,
        }
        assert "narrative" not in payload
        assert "probability_score" not in payload
        assert "impact_jkm" not in payload
        assert "baseline_yn" not in payload

    def test_new_signpost_row_details_are_generated_from_pipeline_outputs(self) -> None:
        price_direction = types.SimpleNamespace(
            jkm="bull",
            ttf="neutral",
            hh="mild_bull",
        )
        generated = types.SimpleNamespace(
            scenario_id="S_01",
            description="generated narrative",
            price_direction=price_direction,
        )
        stage4 = types.SimpleNamespace(scenarios=[generated])
        stage5 = types.SimpleNamespace(likelihood_prior={"S_01": "medium"})

        with (
            patch(
                "apps.agents.scenario_group_agent.subgraphs.scenario_generation."
                "pipeline.stage1_build_context_pack",
                return_value=types.SimpleNamespace(),
            ),
            patch(
                "apps.agents.scenario_group_agent.subgraphs.scenario_generation."
                "pipeline.stage4_synthesize_fixed_scenarios",
                return_value=stage4,
            ) as synthesize,
            patch(
                "apps.agents.scenario_group_agent.subgraphs.scenario_generation."
                "pipeline.stage5_validate",
                return_value=stage5,
            ),
        ):
            details = ScenarioService()._generate_new_row_details(
                {"mi_event_id": 20},
                [{"period": "단기"}],
            )

        synthesize.assert_called_once()
        assert details == [
            NewScenarioGeneratedDetails(
                narrative="generated narrative",
                probability_weight=Decimal("20"),
                probability_delta=Decimal("0.0"),
                impact_jkm="bull",
                impact_ttf="neutral",
                impact_hh="mild_bull",
            ),
        ]

    def test_new_signpost_row_payload_uses_generated_hidden_fields(self) -> None:
        payload = ScenarioService()._row_to_new_scenario_payload(
            scenario_group_id=10,
            template_by_key={"period": {"dim_key": "period"}},
            row={
                "scenario_id": None,
                "display_order": 3,
                "title": "new scenario",
                "cells": {"period": "단기", "ignored": "x"},
            },
            user_id=101,
            generated_details=NewScenarioGeneratedDetails(
                narrative="generated narrative",
                probability_weight=Decimal("20"),
                probability_delta=Decimal("0.0"),
                impact_jkm="bull",
                impact_ttf="neutral",
                impact_hh="mild_bull",
            ),
        )

        assert payload == {
            "scenario_group_id": 10,
            "title": "new scenario",
            "narrative": "generated narrative",
            "status": "creating",
            "dimension_values": {"period": "단기"},
            "display_order": 3,
            "baseline_yn": "N",
            "crt_usr_logn_id": 101,
            "mod_usr_logn_id": 101,
            "probability_score": Decimal("20"),
            "probability_delta": Decimal("0.0"),
            "impact_jkm": "bull",
            "impact_ttf": "neutral",
            "impact_hh": "mild_bull",
        }

    def test_signpost_sync_normalizes_active_probability_scores(self) -> None:
        scenarios = [
            MiScenarioModel(
                scenario_group_id=10,
                title="existing",
                narrative="",
                status="creating",
                dimension_values={},
                probability_score=100,
                display_order=1,
            ),
            MiScenarioModel(
                scenario_group_id=10,
                title="new",
                narrative="",
                status="creating",
                dimension_values={},
                probability_score=20,
                display_order=2,
            ),
        ]

        ScenarioService()._normalize_active_probability_scores(
            scenarios,
            user_id=101,
        )

        assert scenarios[0].probability_score == Decimal("83")
        assert scenarios[1].probability_score == Decimal("17")
        assert scenarios[0].mod_usr_logn_id == 101
        assert scenarios[1].mod_usr_logn_id == 101

    def test_scenario_group_delete_requests_accept_camel_case(self) -> None:
        soft_payload = SoftDeleteScenarioGroupIn.model_validate({"userId": 101})
        hard_payload = HardDeleteScenarioGroupIn.model_validate(
            {"userId": 101, "confirm": True},
        )

        assert soft_payload.user_id == 101
        assert hard_payload.user_id == 101
        assert hard_payload.confirm is True

    def test_validation_request_accepts_document_shape(self) -> None:
        payload = ValidateScenariosIn.model_validate(
            {
                "userId": 101,
                "table": TABLE,
            },
        )

        assert payload.table.rows[0].scenario_id == 100
        assert payload.user_id == 101

    def test_validation_request_rejects_non_request_row_fields(self) -> None:
        table = {
            "headers": [{"key": "period", "label": "기간", "displayOrder": 1}],
            "rows": [
                {
                    "scenarioId": 100,
                    "displayOrder": 1,
                    "title": "scenario",
                    "cells": {"period": "단기"},
                    "narrative": "must not be accepted",
                    "metrics": {"probabilityScore": 40},
                    "impact": {"jkm": "bull"},
                    "baselineYn": "Y",
                    "signposts": [],
                },
            ],
        }

        with self.assertRaises(ValidationError):
            ValidateScenariosIn.model_validate({"userId": 101, "table": table})

    def test_validation_request_rejects_top_level_extra_fields(self) -> None:
        with self.assertRaises(ValidationError):
            ValidateScenariosIn.model_validate(
                {
                    "userId": 101,
                    "table": TABLE,
                    "unexpected": True,
                },
            )

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
            scenario_result=scenario_generation_result_stub(),
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

    def test_scenario_group_insert_uses_generated_group_metadata(self) -> None:
        state = ScenarioDesignState(
            user_id=101,
            event_data={
                "mi_event_id": "20",
                "event_type_l2_id": 30,
                "event_title_ko": "event title",
                "one_line_summary": "event summary",
                "detail_analysis": "event detail",
            },
            scenario_result=scenario_generation_result_stub(
                scenario_group_metadata={
                    "title": "generated group title",
                    "description": "generated group description",
                }
            ),
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
            "ScenarioGroupService.create_group",
            return_value=10,
        ) as create_group:
            save_scenario_group(state)

        payload = create_group.call_args.args[0]
        assert payload["title"] == "generated group title"
        assert payload["description"] == "generated group description"
        assert payload["summary"] == "event summary"

    def test_save_scenario_group_reuses_existing_group_id(self) -> None:
        state = ScenarioDesignState(
            scenario_group_id=10,
            user_id=101,
            event_data={
                "mi_event_id": "20",
                "event_type_l2_id": 30,
                "event_title_ko": "event title",
            },
            scenario_result=scenario_generation_result_stub(),
        )

        with patch(
            "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
            "ScenarioGroupService.create_group",
        ) as create_group:
            result = save_scenario_group(state)

        create_group.assert_not_called()
        assert result["scenario_group_id"] == 10
        assert result["scenario_result"]["scenario_group_id"] == 10

    def test_prepare_group_record_leaves_initial_description_empty(self) -> None:
        state = ScenarioDesignState(
            user_id=101,
            event_data={
                "mi_event_id": "20",
                "event_type_l2_id": 30,
                "event_title_ko": "event title",
                "one_line_summary": "event summary",
                "detail_analysis": "long event detail",
            },
        )

        with (
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "ScenarioGroupService.create_group",
                return_value=10,
            ) as create_group,
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "ScenarioGroupService.load_by_id",
                return_value={"scenario_group_id": 10},
            ),
        ):
            create_group_record(state)

        payload = create_group.call_args.args[0]
        assert payload["description"] is None

    def test_async_save_scenarios_updates_group_metadata(self) -> None:
        state = ScenarioDesignState(
            scenario_group_id=10,
            user_id=101,
            scenario_result=scenario_generation_result_stub(
                scenario_group_metadata={
                    "title": "generated group title",
                    "description": "generated group description",
                }
            ),
        )

        with (
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "ScenarioService.save_generated_scenarios",
                return_value=[],
            ),
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "ScenarioGroupService.update_scenario_count",
            ),
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "ScenarioGroupService.update_state",
                return_value={"scenario_group_id": 10},
            ) as update_state,
            patch(
                "apps.agents.scenario_group_agent.flows.create_scenarios.nodes."
                "ScenarioService.load_by_group_id",
                return_value=[],
            ),
        ):
            save_scenarios(state)

        assert update_state.call_args.kwargs["title"] == "generated group title"
        assert update_state.call_args.kwargs["description"] == "generated group description"

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

    def test_confirmation_request_allows_missing_user_id_temporarily(self) -> None:
        payload = ConfirmGenerationIn.model_validate(
            {
                "scenarioGroup": CONFIRM_SCENARIO_GROUP,
                "table": TABLE,
            },
        )

        assert payload.user_id is None

    def test_confirmation_updates_scenario_group_title_summary_description(
        self,
    ) -> None:
        session = Mock()
        group = types.SimpleNamespace(
            scenario_group_id=10,
            mi_event_id=20,
            event_type_l2_id=30,
            request_usr_id=101,
            title="old title",
            summary="old summary",
            description="old description",
            dimension_selected=["period"],
            scenario_count=1,
            status="creating",
            stage="ready",
            del_yn="N",
        )
        scenario = MiScenarioModel(
            scenario_id=100,
            scenario_group_id=10,
            title="scenario",
            narrative="narrative",
            status="creating",
            dimension_values={"period": "period_v1"},
            probability_score=50,
            display_order=1,
        )
        signpost = MiSignpostModel(
            signpost_id=1000,
            scenario_id=100,
            label="signal",
            probability_direction_code="SUP",
            display_order=1,
        )

        group_repository = Mock()
        group_repository.fetch_by_id.return_value = group
        group_repository.create_confirmation_snapshot.return_value = 500
        group_repository.model_to_dict.return_value = {
            "scenario_group_id": 10,
            "mi_event_id": 20,
            "event_type_l2_id": 30,
            "request_usr_id": 101,
            "title": "updated title",
            "summary": "updated summary",
            "description": "updated description",
            "dimension_selected": ["period"],
            "scenario_count": 1,
            "status": "created",
            "stage": "completed",
        }
        scenario_repository = Mock()
        scenario_repository.fetch_models_by_group_id.return_value = [scenario]
        signpost_repository = Mock()
        signpost_repository.fetch_models_by_scenario_ids.return_value = [signpost]
        connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        connection_module.get_sync_session = lambda: session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (
                        connection_module
                    ),
                },
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_group."
                "service.ScenarioGroupRepository",
                return_value=group_repository,
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_group."
                "service.ScenarioRepository",
                return_value=scenario_repository,
            ),
            patch(
                "apps.agents.scenario_group_agent.persistence.scenario_group."
                "service.SignpostRepository",
                return_value=signpost_repository,
            ),
            patch.object(
                ScenarioService,
                "cells_to_dimension_values",
                return_value={"period": "period_v1"},
            ),
        ):
            result = ScenarioGroupService().apply_confirmation(
                10,
                {
                    "title": "updated title",
                    "summary": "updated summary",
                    "description": "updated description",
                },
                {
                    "rows": [
                        {
                            "scenario_id": 100,
                            "cells": {"period": "단기"},
                            "signposts": [
                                {
                                    "signpost_id": 1000,
                                    "label": "signal",
                                    "display_order": 1,
                                },
                            ],
                        },
                    ],
                },
                user_id=101,
            )

        assert result["status"] == "success"
        group_update = group_repository.update_group.call_args_list[0].args[1]
        assert group_update["title"] == "updated title"
        assert group_update["summary"] == "updated summary"
        assert group_update["description"] == "updated description"
        assert group_update["status"] == "created"
        assert group_update["stage"] == "completed"

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

        assert context.exception.status_code == 403

    def test_validation_success_sets_group_stage_to_validated(self) -> None:
        with (
            patch(
                "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
                "ScenarioService.update_status",
                return_value=1,
            ),
            patch(
                "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
                "ScenarioGroupService.update_state",
                return_value={
                    "scenario_group_id": 10,
                    "status": "creating",
                    "stage": "scenario_validated",
                },
            ) as update_group_state,
        ):
            result = save_validation_result(
                ScenarioDesignState(
                    scenario_group_id=10,
                    user_id=101,
                    is_valid=True,
                ),
            )

        update_group_state.assert_called_once_with(
            10,
            status="creating",
            stage="scenario_validated",
            user_id=101,
        )
        assert result["scenario_group"]["stage"] == "scenario_validated"

    def test_validation_failure_keeps_group_stage_at_scenario_created(self) -> None:
        with (
            patch(
                "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
                "ScenarioService.update_status",
                return_value=1,
            ),
            patch(
                "apps.agents.scenario_group_agent.flows.validate_scenarios.nodes."
                "ScenarioGroupService.update_state",
                return_value={
                    "scenario_group_id": 10,
                    "status": "creating",
                    "stage": "scenario_created",
                },
            ) as update_group_state,
        ):
            result = save_validation_result(
                ScenarioDesignState(
                    scenario_group_id=10,
                    user_id=101,
                    is_valid=False,
                ),
            )

        update_group_state.assert_called_once_with(
            10,
            status="creating",
            stage="scenario_created",
            user_id=101,
        )
        assert result["scenario_group"]["stage"] == "scenario_created"

    def test_soft_delete_owner_check_matches_shared_policy(self) -> None:
        with self.assertRaises(MIBaseError) as context:
            ScenarioGroupService()._assert_group_owner(
                {"scenario_group_id": 10, "request_usr_id": 202},
                user_id=101,
            )

        assert context.exception.status_code == 403
        assert "이미 사용자 202" in context.exception.error_message

    def test_hard_delete_requires_confirm_before_db_access(self) -> None:
        with self.assertRaises(MIBaseError) as context:
            ScenarioGroupService().hard_delete_group(
                10,
                user_id=101,
                confirm=False,
                authorization="Bearer test-token",
            )

        assert context.exception.status_code == 400

    def test_delete_authorization_rejects_unknown_bearer_token(self) -> None:
        settings_module = types.SimpleNamespace(
            get_settings=lambda: types.SimpleNamespace(
                scenario_group_admin_bearer_tokens=["valid-token"],
            ),
        )
        with patch.dict(
            sys.modules,
            {"apps.common.configs.config": settings_module},
        ):

            with self.assertRaises(MIBaseError) as context:
                ScenarioGroupService()._assert_delete_authorization(
                    "Bearer wrong-token",
                )

        assert context.exception.status_code == 403

    def test_delete_authorization_rejects_non_bearer_header(self) -> None:
        settings_module = types.SimpleNamespace(
            get_settings=lambda: types.SimpleNamespace(
                scenario_group_admin_bearer_tokens=["valid-token"],
            ),
        )
        with patch.dict(
            sys.modules,
            {"apps.common.configs.config": settings_module},
        ):

            with self.assertRaises(MIBaseError) as context:
                ScenarioGroupService()._assert_delete_authorization(
                    "Basic valid-token",
                )

        assert context.exception.status_code == 403

    def test_delete_authorization_accepts_configured_bearer_token(self) -> None:
        settings_module = types.SimpleNamespace(
            get_settings=lambda: types.SimpleNamespace(
                scenario_group_admin_bearer_tokens=["valid-token"],
            ),
        )
        with patch.dict(
            sys.modules,
            {"apps.common.configs.config": settings_module},
        ):

            ScenarioGroupService()._assert_delete_authorization(
                "Bearer valid-token",
            )

    def test_signpost_save_sets_group_stage_to_signpost_created(self) -> None:
        state = ScenarioDesignState(
            scenario_group_id=10,
            user_id=101,
            scenarios=[{"scenario_id": 100}],
            signpost_result=SignpostGenerationResult(
                scenario_group_id=10,
                signposts=[],
            ),
        )

        with (
            patch(
                "apps.agents.scenario_group_agent.flows.create_signposts.nodes."
                "SignpostService.load_by_scenario_ids",
                return_value=[],
            ),
            patch(
                "apps.agents.scenario_group_agent.flows.create_signposts.nodes."
                "ScenarioService.update_status",
                return_value=1,
            ) as update_scenario_status,
            patch(
                "apps.agents.scenario_group_agent.flows.create_signposts.nodes."
                "ScenarioGroupService.update_state",
                return_value={
                    "scenario_group_id": 10,
                    "status": "creating",
                    "stage": "signpost_created",
                },
            ) as update_group_state,
        ):
            result = save_signposts(state)

        update_scenario_status.assert_called_once_with(10, "created")
        update_group_state.assert_called_once_with(
            10,
            status="creating",
            stage="signpost_created",
            user_id=101,
        )
        assert result["scenario_group"]["stage"] == "signpost_created"

    def test_baseline_uses_single_highest_probability_with_display_order_tiebreak(
        self,
    ) -> None:
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

        assert [scenario.baseline_yn for scenario in scenarios] == ["N", "Y", "N"]

    def test_baseline_contrast_coverage_allows_distributed_alternatives(
        self,
    ) -> None:
        scenarios = [
            {
                "dimension_values": {
                    "period": "단기",
                    "impact": "낮음",
                    "recovery": "빠름",
                },
                "probability_score": 70,
                "display_order": 1,
            },
            {
                "dimension_values": {
                    "period": "장기",
                    "impact": "낮음",
                    "recovery": "빠름",
                },
                "probability_score": 20,
                "display_order": 2,
            },
            {
                "dimension_values": {
                    "period": "단기",
                    "impact": "높음",
                    "recovery": "느림",
                },
                "probability_score": 10,
                "display_order": 3,
            },
        ]

        result = check_baseline_contrast_coverage(
            scenarios,
            ["period", "impact", "recovery"],
        )

        assert result.covered is True
        assert result.baseline_index == 0
        assert result.missing_dimensions == []

    def test_baseline_contrast_coverage_reports_missing_dimension(self) -> None:
        scenarios = [
            {
                "dimension_values": {"period": "단기", "impact": "낮음"},
                "probability_score": 70,
                "display_order": 1,
            },
            {
                "dimension_values": {"period": "장기", "impact": "낮음"},
                "probability_score": 30,
                "display_order": 2,
            },
        ]

        result = check_baseline_contrast_coverage(
            scenarios,
            ["period", "impact"],
        )

        assert result.covered is False
        assert result.missing_dimensions == ["impact"]

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

    def test_query_response_includes_delete_flags_and_counts(self) -> None:
        from apps.agents.scenario_group_agent.presentation import (
            build_scenario_group_query_data,
        )

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
            "scenario_count": 2,
            "status": "creating",
            "stage": "scenario_created",
            "del_yn": "N",
        }
        scenarios = [
            {
                "scenario_id": 100,
                "title": "active",
                "narrative": "narrative",
                "dimension_values": {"period": "period_v1"},
                "display_order": 1,
                "baseline_yn": "Y",
                "del_yn": "N",
            },
            {
                "scenario_id": 101,
                "title": "deleted",
                "narrative": "narrative",
                "dimension_values": {"period": "period_v2"},
                "display_order": 2,
                "baseline_yn": "N",
                "del_yn": "Y",
            },
        ]
        signposts = [
            {
                "signpost_id": 1000,
                "scenario_id": 100,
                "label": "active signpost",
                "display_order": 1,
                "del_yn": "N",
            },
            {
                "signpost_id": 1001,
                "scenario_id": 101,
                "label": "deleted signpost",
                "display_order": 1,
                "del_yn": "Y",
            },
        ]

        with patch.object(
            ScenarioService,
            "_load_template_json_from_db",
            return_value=template,
        ):
            result = build_scenario_group_query_data(group, scenarios, signposts)

        serialized = result.model_dump(by_alias=True)
        assert serialized["scenarioGroup"]["delYn"] == "N"
        assert serialized["table"]["rows"][1]["delYn"] == "Y"
        assert serialized["table"]["rows"][1]["signposts"][0]["delYn"] == "Y"
        assert serialized["scenarioCount"] == 1
        assert serialized["signpostCount"] == 1
        assert serialized["deletedScenarioCount"] == 1
        assert serialized["deletedSignpostCount"] == 1


if __name__ == "__main__":
    unittest.main()
