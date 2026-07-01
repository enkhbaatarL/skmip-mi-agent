# ruff: noqa: S101

from __future__ import annotations

import json
import sys
import types
from datetime import date
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch

from fastapi.routing import APIRoute
from openpyxl import Workbook, load_workbook

from apps.agents.model_parameter_agent.api import router as model_parameter_router
from apps.agents.model_parameter_agent.flows.propose_parameters.flow import (
    build_graph,
    to_output,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _coordinate_issues,
    _period_start_year_month,
    filter_basecase_records_by_slots,
    load_scenario_context,
    propose_parameter_slots,
    propose_parameter_values,
    select_parameter_candidates,
    validate_parameter_candidates,
)
from apps.agents.model_parameter_agent.mapping import (
    DEFAULT_INPUT_DIR,
    DIMENSION_PARAMETER_MAPPING_SHEET,
    PARAMETER_EXCEL_MAPPING_SHEET,
    build_basecase_records,
    get_parameter_knowledge_base,
    match_parameter_candidates,
)
from apps.agents.model_parameter_agent.schemas.propose_parameters import (
    LLMCandidateValidationResponse,
    LLMSlotProposalResponse,
    LLMValueProposalResponse,
    ModelParameterTarget,
    ParameterCandidateDecision,
    ParameterSlotAxis,
    ParameterSlotProposal,
    ParameterAdjustment,
    ParameterValueCell,
    ProposalParameter,
    ProposeParametersIn,
)
from apps.agents.model_parameter_agent.state import ModelParameterProposalState
from apps.common.exceptions.custom import MIBaseError


def _excel_available() -> bool:
    return DEFAULT_INPUT_DIR.exists() and any(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))


def _default_mapping_excel_path() -> Path:
    return next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))


def _get_excel_kb(
    *,
    max_sample_rows: int = 1,
    max_sample_cols: int = 8,
):
    return get_parameter_knowledge_base(
        mapping_excel_path=str(_default_mapping_excel_path()),
        max_sample_rows=max_sample_rows,
        max_sample_cols=max_sample_cols,
    )


def _record_with(
    records: list[dict],
    *,
    axes: dict | None = None,
    source_row: int | None = None,
    source_col: int | None = None,
) -> dict:
    for record in records:
        record_axes = record.get("axes") or {}
        if axes and any(record_axes.get(key) != value for key, value in axes.items()):
            continue
        if source_row is not None and record.get("source_row") != source_row:
            continue
        if source_col is not None and record.get("source_col") != source_col:
            continue
        return record
    raise AssertionError(f"record not found: axes={axes}, source_row={source_row}, source_col={source_col}")


class ModelParameterAgentContractTest(unittest.TestCase):
    def test_schema_accepts_camel_case_options(self) -> None:
        payload = ProposeParametersIn.model_validate(
            {
                "maxCandidates": 3,
                "maxBasecaseSampleRows": 2,
                "allowLlmFallback": True,
            },
        )

        assert payload.max_candidates == 3
        assert payload.max_basecase_sample_rows == 2
        assert payload.allow_llm_fallback is True

    def test_graph_registers_expected_nodes(self) -> None:
        graph = build_graph().get_graph()

        assert "load_scenario_context" in graph.nodes
        assert "select_parameter_candidates" in graph.nodes
        assert "validate_parameter_candidates" in graph.nodes
        assert "load_basecase_samples" in graph.nodes
        assert "propose_parameter_slots" in graph.nodes
        assert "filter_basecase_records_by_slots" in graph.nodes
        assert "propose_parameter_values" in graph.nodes

    def test_main_registers_model_parameter_router(self) -> None:
        main_source = Path("main.py").read_text()

        assert "model_parameter_router" in main_source
        assert "app.include_router(" in main_source
        assert "preload_parameter_knowledge_base" not in main_source

    def test_model_parameter_endpoint_requires_only_scenario_id(self) -> None:
        route = next(
            route
            for route in model_parameter_router.routes
            if isinstance(route, APIRoute)
            and route.path == "/model-parameters/scenarios/{scenario_id}/proposals"
        )

        assert route.body_field is None
        assert [param.name for param in route.dependant.path_params] == ["scenario_id"]

    def test_default_excel_resources_are_packaged_with_agent(self) -> None:
        assert DEFAULT_INPUT_DIR.name == "resources"
        assert DEFAULT_INPUT_DIR.parent.name == "model_parameter_agent"
        assert "gen_model_param" not in DEFAULT_INPUT_DIR.parts
        assert any(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        mapping_path = next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        workbook = load_workbook(mapping_path, read_only=True, data_only=True)
        assert DIMENSION_PARAMETER_MAPPING_SHEET in workbook.sheetnames
        assert PARAMETER_EXCEL_MAPPING_SHEET in workbook.sheetnames
        assert any(
            child.is_dir() and "Basecase_20260610" in child.name
            for child in DEFAULT_INPUT_DIR.iterdir()
        )

    def test_default_knowledge_base_loads_mapping_from_db(self) -> None:
        from apps.agents.model_parameter_agent import mapping as mapping_module

        mapping_rows = [
            {
                "event_type_l2_id": 17,
                "dimension_key": "transport_disruption",
                "dimension_label": "운송 차질",
                "mapping_status": "exact",
                "canonical_parameter_name": "ShippingCost",
                "mapping_method": "direct",
                "comment": "운송 차질은 ShippingCost에 직접 반영",
            },
        ]
        parameter_rows = [
            {
                "canonical_parameter_name": "ShippingCost",
                "parameter_name": "ShippingCost",
                "model_file": "Trade",
                "model_sheet": "ShippingCostInput",
                "unit": "USD",
                "semantic_axes": "Route",
                "basecase_read_mode": "fixed_columns",
                "basecase_header_row": 1,
                "basecase_data_start_row": 2,
                "basecase_column_roles": "1=Route,2=value",
                "basecase_row_filter": None,
                "basecase_year_row": None,
                "basecase_month_row": None,
                "basecase_period_row": None,
                "basecase_value_start_col": None,
                "basecase_value_end_col": None,
                "basecase_value_name": "ShippingCost",
                "basecase_stop_rule": "blank_axis",
            },
        ]

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch(
                "apps.agents.model_parameter_agent.persistence.model_input.service."
                "ModelInputService.load_parameter_mapping_resources",
                return_value=(mapping_rows, parameter_rows),
            ) as load_resources,
        ):
            kb = get_parameter_knowledge_base(
                basecase_dir_path=tmpdir,
                max_sample_rows=1,
                max_sample_cols=8,
            )
            get_parameter_knowledge_base(
                basecase_dir_path=tmpdir,
                max_sample_rows=1,
                max_sample_cols=8,
            )

        assert load_resources.call_count == 2
        assert kb.mapping_excel_path == mapping_module.DB_MAPPING_SOURCE
        assert kb.definition_for("ShippingCost") is not None
        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            {
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": {"transport_disruption": "높음"},
                },
                "scenario_group": {"event_type_l2_id": 17},
                "dimension_template": [
                    {"dim_key": "transport_disruption", "label": "운송 차질"},
                ],
            },
            max_candidates=10,
        )

        assert not non_inputs
        assert not warnings
        assert candidates[0]["canonical_parameter_name"] == "ShippingCost"
        assert candidates[0]["model_file"] == "Trade"

    def test_model_input_service_loads_context_with_parameter_mapping_resources(self) -> None:
        fake_session = SimpleNamespace(close=lambda: None)
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (
                        fake_connection_module
                    ),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_input.service.ModelInputRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_input.service import (
                ModelInputService,
            )

            repository_cls.return_value.fetch_context_by_scenario_id.return_value = {
                "scenario": {"scenario_id": 100},
            }
            repository_cls.return_value.fetch_parameter_mapping_resources.return_value = (
                [{"dimension_key": "transport_disruption"}],
                [{"parameter_name": "ShippingCost"}],
            )

            result = ModelInputService().load_context(100)

        assert result["scenario"]["scenario_id"] == 100
        assert result["parameter_mapping_resources"] == {
            "mapping_rules": [{"dimension_key": "transport_disruption"}],
            "parameter_definitions": [{"parameter_name": "ShippingCost"}],
        }
        repository_cls.return_value.fetch_context_by_scenario_id.assert_called_once_with(100)
        repository_cls.return_value.fetch_parameter_mapping_resources.assert_called_once_with()

    def test_model_input_service_loads_parameter_mapping_resources(self) -> None:
        fake_session = SimpleNamespace(close=lambda: None)
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (
                        fake_connection_module
                    ),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_input.service.ModelInputRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_input.service import (
                ModelInputService,
            )

            repository_cls.return_value.fetch_parameter_mapping_resources.return_value = (
                [{"dimension_key": "period"}],
                [{"parameter_name": "ShippingCost"}],
            )

            mapping_rules, parameter_definitions = (
                ModelInputService().load_parameter_mapping_resources()
            )

        assert mapping_rules == [{"dimension_key": "period"}]
        assert parameter_definitions == [{"parameter_name": "ShippingCost"}]
        repository_cls.return_value.fetch_parameter_mapping_resources.assert_called_once_with()

    def test_request_load_context_builds_knowledge_base_from_loaded_db_resources(self) -> None:
        scenario_context = {
            "scenario": {
                "scenario_id": 100,
                "title": "transport disruption",
                "dimension_values": {"transport_disruption": "높음"},
            },
            "scenario_group": {"event_type_l2_id": 17, "mi_event_id": 30},
            "dimension_template": [
                {"dim_key": "transport_disruption", "label": "운송 차질"},
            ],
            "parameter_mapping_resources": {
                "mapping_rules": [
                    {
                        "event_type_l2_id": 17,
                        "dimension_key": "transport_disruption",
                        "dimension_label": "운송 차질",
                        "mapping_status": "exact",
                        "canonical_parameter_name": "ShippingCost",
                        "mapping_method": "direct",
                        "comment": "운송 차질은 ShippingCost에 직접 반영",
                    },
                ],
                "parameter_definitions": [
                    {
                        "canonical_parameter_name": "ShippingCost",
                        "parameter_name": "ShippingCost",
                        "model_file": "Trade",
                        "model_sheet": "ShippingCostInput",
                        "unit": "USD",
                        "semantic_axes": "Route",
                        "basecase_read_mode": "fixed_columns",
                        "basecase_header_row": 1,
                        "basecase_data_start_row": 2,
                        "basecase_column_roles": "1=Route,2=value",
                        "basecase_row_filter": None,
                        "basecase_year_row": None,
                        "basecase_month_row": None,
                        "basecase_period_row": None,
                        "basecase_value_start_col": None,
                        "basecase_value_end_col": None,
                        "basecase_value_name": "ShippingCost",
                        "basecase_stop_rule": "blank_axis",
                    },
                ],
            },
        }
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.nodes."
                "ModelInputService",
            ) as service_cls,
        ):
            state = ModelParameterProposalState(
                scenario_id=100,
                basecase_dir_path=tmpdir,
            )
            service_cls.return_value.load_context.return_value = scenario_context
            loaded = load_scenario_context(state)

            kb = loaded["parameter_knowledge_base"]
            selected = select_parameter_candidates(
                state.model_copy(
                    update={
                        "scenario_context": loaded["scenario_context"],
                        "parameter_knowledge_base": kb,
                    },
                ),
            )

        assert kb.definition_for("ShippingCost") is not None
        assert selected["candidate_mappings"][0]["canonical_parameter_name"] == "ShippingCost"

    def test_model_input_service_saves_proposal_result(self) -> None:
        fake_session = SimpleNamespace(
            commit=Mock(),
            rollback=Mock(),
            close=Mock(),
        )
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (
                        fake_connection_module
                    ),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_input.service.ModelInputRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_input.service import (
                ModelInputService,
            )

            repository_cls.return_value.create_model_param_proposal.return_value = 901

            result = ModelInputService().save_proposal_result(
                scenario_context={
                    "scenario": {"scenario_id": 100, "scenario_group_id": 20},
                    "scenario_group": {
                        "scenario_group_id": 20,
                        "mi_event_id": 30,
                        "request_usr_id": 40,
                    },
                    "event": {"mi_event_id": 30},
                },
                proposal_parameters=[
                    ProposalParameter(
                        parameter_name="ShippingCost",
                        model_target=ModelParameterTarget(
                            model_file="Trade",
                            model_sheet="ShippingCostInput",
                            value_field_names=["ShippingCost"],
                            slot_axes_field_names=["Route"],
                        ),
                        rationale="운송 차질 근거",
                        values=[
                            {
                                "Route": "Suez",
                                "basecaseValue": 1,
                                "proposedValue": 2,
                                "rationale": "수에즈 운송 차질",
                            },
                        ],
                    ),
                ],
            )

        assert result == 901
        fake_session.commit.assert_called_once_with()
        fake_session.rollback.assert_not_called()
        fake_session.close.assert_called_once_with()
        repository_cls.return_value.create_model_param_proposal.assert_called_once()
        saved_payload = (
            repository_cls.return_value.create_model_param_proposal.call_args.kwargs[
                "proposal_parameters"
            ]
        )
        assert saved_payload[0]["parameterName"] == "ShippingCost"
        assert saved_payload[0]["modelTarget"]["modelFile"] == "Trade"

    def test_model_input_persistence_write_scope_is_proposal_only(self) -> None:
        source = Path(
            "apps/agents/model_parameter_agent/persistence/model_input/repository.py",
        ).read_text().lower()

        forbidden_tokens = [
            ".commit(",
            " insert(",
            " update(",
            " delete(",
        ]
        for token in forbidden_tokens:
            assert token not in source
        assert "mimodelparamproposalmodel(" in source

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_knowledge_base_profiles_scan_entire_mapped_basecase_sheet(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        existing_profiles = [
            profile
            for profile in kb.basecase_profiles.values()
            if profile.sheet_exists
        ]

        assert existing_profiles
        assert kb.basecase_profiles["trade::shippingcostinput"].row_count > 18000
        for profile in existing_profiles:
            assert profile.rows_scanned == profile.row_count
            assert len(profile.sample_rows) <= 1

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_match_candidates_uses_bridge_event_id_and_dimension_key(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "title": "geo",
                "dimension_values": {
                    "period": "2026-07~2026-09",
                    "transport_disruption": "높음",
                    "supply_disruption_intensity": "중간",
                },
            },
            "scenario_group": {"event_type_l2_id": 17, "mi_event_id": 20},
            "event_type": {
                "level_2_code": "war_military_conflict",
                "level_2_label": "지정학적 긴장 및 전쟁·군사분쟁",
            },
            "event": {"event_title_ko": "호르무즈 분쟁"},
            "dimension_template": [
                {"dim_key": "period", "label": "기간"},
                {"dim_key": "transport_disruption", "label": "운송 차질"},
                {"dim_key": "supply_disruption_intensity", "label": "공급 차질 - 강도"},
            ],
        }

        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )
        assert not warnings
        assert any(candidate["canonical_parameter_name"] == "ShippingCost" for candidate in candidates)
        assert all(candidate["event_type_l2_id"] == 17 for candidate in candidates)
        assert any(item["mapping_method"] == "indirect" for item in non_inputs)
        assert any(
            kb.profile_for(candidate.get("model_file"), candidate.get("model_sheet"))
            for candidate in candidates
        )

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_match_candidates_does_not_fallback_when_bridge_key_is_missing(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "dimension_values": {"transport_disruption": "높음"},
            },
            "scenario_group": {"event_type_l2_id": 999, "mi_event_id": 20},
            "event_type": {
                "level_2_code": "geopolitical_tension_war",
                "level_2_label": "지정학적 긴장 및 전쟁·군사분쟁",
            },
            "dimension_template": [
                {"dim_key": "transport_disruption", "label": "운송 차질"},
            ],
        }

        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )

        assert candidates == []
        assert non_inputs == []
        assert any("DB dimension-parameter 매핑" in warning for warning in warnings)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_bridge_mapping_preserves_multiple_routing_targets(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "dimension_values": {"affected_facility_type": "수출 시설"},
            },
            "scenario_group": {"event_type_l2_id": 11},
            "dimension_template": [
                {"dim_key": "affected_facility_type", "label": "영향 시설 유형"},
            ],
        }

        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )

        assert not warnings
        assert non_inputs == []
        assert {
            candidate["canonical_parameter_name"]
            for candidate in candidates
        } == {
            "SupplyDisruption",
            "LiqUtilAdjustment",
            "LiqProdAdjustment",
            "RegasAdjustment",
            "HurricaneIntensity",
        }
        assert all(candidate["mapping_method"] == "routing" for candidate in candidates)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_knowledge_base_accepts_workbook_with_only_mapping_sheets(self) -> None:
        source_mapping_path = next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        source_workbook = load_workbook(source_mapping_path, read_only=True, data_only=True)
        source_dimension_sheet = source_workbook[DIMENSION_PARAMETER_MAPPING_SHEET]
        source_parameter_sheet = source_workbook[PARAMETER_EXCEL_MAPPING_SHEET]
        basecase_dir = next(
            child
            for child in DEFAULT_INPUT_DIR.iterdir()
            if child.is_dir() and "Basecase_20260610" in child.name
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "mapping_only.xlsx"
            workbook = Workbook()
            target_dimension_sheet = workbook.active
            target_dimension_sheet.title = DIMENSION_PARAMETER_MAPPING_SHEET
            for row in source_dimension_sheet.iter_rows(values_only=True):
                target_dimension_sheet.append(row)
            target_parameter_sheet = workbook.create_sheet(PARAMETER_EXCEL_MAPPING_SHEET)
            for row in source_parameter_sheet.iter_rows(values_only=True):
                target_parameter_sheet.append(row)
            workbook.save(target_path)

            kb = get_parameter_knowledge_base(
                mapping_excel_path=str(target_path),
                basecase_dir_path=str(basecase_dir),
                max_sample_rows=1,
                max_sample_cols=8,
            )

        assert kb.mapping_rules
        assert kb.parameter_definitions
        assert kb.profile_for("Trade", "ShippingCostInput") is not None

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_bridge_mapping_sheet_required_columns_fail_fast(self) -> None:
        source_mapping_path = next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        source_workbook = load_workbook(source_mapping_path, read_only=True, data_only=True)
        source_sheet = source_workbook[DIMENSION_PARAMETER_MAPPING_SHEET]
        source_parameter_sheet = source_workbook[PARAMETER_EXCEL_MAPPING_SHEET]
        basecase_dir = next(
            child
            for child in DEFAULT_INPUT_DIR.iterdir()
            if child.is_dir() and "Basecase_20260610" in child.name
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "bridge_missing_column.xlsx"
            workbook = Workbook()
            target_sheet = workbook.active
            target_sheet.title = DIMENSION_PARAMETER_MAPPING_SHEET
            rows = list(source_sheet.iter_rows(values_only=True))
            headers = list(rows[0])
            drop_index = headers.index("canonical_parameter_name")
            target_sheet.append([
                value for index, value in enumerate(headers)
                if index != drop_index
            ])
            for row in rows[1:4]:
                target_sheet.append([
                    value for index, value in enumerate(row)
                    if index != drop_index
                ])
            target_parameter_sheet = workbook.create_sheet(PARAMETER_EXCEL_MAPPING_SHEET)
            for row in source_parameter_sheet.iter_rows(values_only=True):
                target_parameter_sheet.append(row)
            workbook.save(target_path)

            with self.assertRaises(MIBaseError) as raised:
                get_parameter_knowledge_base(
                    mapping_excel_path=str(target_path),
                    basecase_dir_path=str(basecase_dir),
                    max_sample_rows=1,
                    max_sample_cols=8,
                )

        assert "canonical_parameter_name" in str(raised.exception)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_parameter_excel_mapping_sheet_is_required(self) -> None:
        source_mapping_path = next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        source_workbook = load_workbook(source_mapping_path, read_only=True, data_only=True)
        source_dimension_sheet = source_workbook[DIMENSION_PARAMETER_MAPPING_SHEET]
        basecase_dir = next(
            child
            for child in DEFAULT_INPUT_DIR.iterdir()
            if child.is_dir() and "Basecase_20260610" in child.name
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "parameter_sheet_missing.xlsx"
            workbook = Workbook()
            target_dimension_sheet = workbook.active
            target_dimension_sheet.title = DIMENSION_PARAMETER_MAPPING_SHEET
            for row in source_dimension_sheet.iter_rows(values_only=True):
                target_dimension_sheet.append(row)
            workbook.save(target_path)

            with self.assertRaises(MIBaseError) as raised:
                get_parameter_knowledge_base(
                    mapping_excel_path=str(target_path),
                    basecase_dir_path=str(basecase_dir),
                    max_sample_rows=1,
                    max_sample_cols=8,
                )

        assert PARAMETER_EXCEL_MAPPING_SHEET in str(raised.exception)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_bridge_disabled_rows_are_not_mapped(self) -> None:
        source_mapping_path = next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        source_workbook = load_workbook(source_mapping_path, read_only=True, data_only=True)
        source_sheet = source_workbook[DIMENSION_PARAMETER_MAPPING_SHEET]
        rows = list(source_sheet.iter_rows(values_only=True))
        headers = list(rows[0])
        index_by_header = {header: index for index, header in enumerate(headers)}
        transport_row = next(
            row for row in rows[1:]
            if row[index_by_header["event_type_l2_id"]] == 17
            and row[index_by_header["dimension_key"]] == "transport_disruption"
        )
        disabled_row = list(transport_row)
        disabled_row[index_by_header["enabled"]] = False
        basecase_dir = next(
            child
            for child in DEFAULT_INPUT_DIR.iterdir()
            if child.is_dir() and "Basecase_20260610" in child.name
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = Path(temp_dir) / "bridge_disabled.xlsx"
            workbook = Workbook()
            target_sheet = workbook.active
            target_sheet.title = DIMENSION_PARAMETER_MAPPING_SHEET
            target_sheet.append(headers)
            target_sheet.append(disabled_row)
            target_parameter_sheet = workbook.create_sheet(PARAMETER_EXCEL_MAPPING_SHEET)
            source_parameter_sheet = source_workbook[PARAMETER_EXCEL_MAPPING_SHEET]
            for row in source_parameter_sheet.iter_rows(values_only=True):
                target_parameter_sheet.append(row)
            workbook.save(target_path)
            kb = get_parameter_knowledge_base(
                mapping_excel_path=str(target_path),
                basecase_dir_path=str(basecase_dir),
                max_sample_rows=1,
                max_sample_cols=8,
            )

        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            {
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": {"transport_disruption": "높음"},
                },
                "scenario_group": {"event_type_l2_id": 17},
                "dimension_template": [
                    {"dim_key": "transport_disruption", "label": "운송 차질"},
                ],
            },
            max_candidates=10,
        )

        assert candidates == []
        assert non_inputs == []
        assert any("DB dimension-parameter 매핑" in warning for warning in warnings)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_bridge_direct_row_without_target_becomes_non_input(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "dimension_values": {"supply_disruption_intensity": "높음"},
            },
            "scenario_group": {"event_type_l2_id": 11},
            "dimension_template": [
                {"dim_key": "supply_disruption_intensity", "label": "공급 차질 강도"},
            ],
        }

        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )

        assert candidates == []
        assert any("target 정보" in item["reason"] for item in non_inputs)
        assert any("parameter 후보를 찾지 못했습니다" in warning for warning in warnings)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_basecase_records_flatten_mapped_matrix_sheet(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        candidate = {
            "candidate_key": "c1",
            "model_file": "Supply",
            "model_sheet": "LiqUtilAdjustment",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
            "unit": "%",
        }
        context = {
            "scenario": {
                "scenario_id": 278,
                "title": "Golden Pass 미국 2026",
                "narrative": "Golden Pass feedgas 반등으로 미국 LNG 수출 여력 확대. 2026년 6개월",
                "dimension_values": {},
            },
        }

        records, warnings = build_basecase_records(
            kb,
            [candidate],
            context,
        )

        assert not warnings
        assert records
        first = _record_with(
            records,
            axes={
                "Country": "United States",
                "LNG Plant": "Golden Pass LNG",
                "Year": 2026,
            },
        )
        assert first["candidate_key"] == "c1"
        assert first["axes"]["Country"] == "United States"
        assert first["axes"]["LNG Plant"] == "Golden Pass LNG"
        assert first["axes"]["Year"] == 2026
        assert "Period" in first["axes"]
        assert "value" in first
        for debug_key in ("workbook_path", "header_rows", "sample_rows", "distinct_values", "numeric_summary"):
            assert debug_key not in first

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_basecase_records_use_matrix_time_column_spec_when_available(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "title": "Algeria Arzew GL1Z 2026 utilization",
                "narrative": "Algeria Arzew GL1Z 2026 utilization disruption",
                "dimension_values": {"affected_facility_type": "수출 시설"},
            },
            "scenario_group": {"event_type_l2_id": 11},
            "dimension_template": [
                {"dim_key": "affected_facility_type", "label": "영향 시설 유형"},
            ],
        }
        candidates, _, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )
        assert not warnings
        liq_candidate = next(
            candidate
            for candidate in candidates
            if candidate["canonical_parameter_name"] == "LiqUtilAdjustment"
        )
        assert liq_candidate["basecase_column_roles"] == (
            "B:Country,C:LNG Plant,D:LNG Plant Train,"
            "E:Life Cycle Category,F:Nameplate Capacity"
        )
        assert liq_candidate["basecase_value_start_col"] == "G"
        assert liq_candidate["basecase_value_end_col"] == "DA"

        records, record_warnings = build_basecase_records(
            kb,
            [liq_candidate],
            context,
        )

        assert not record_warnings
        assert records
        first = _record_with(
            records,
            axes={
                "Country": "Algeria",
                "LNG Plant": "Arzew GL1Z",
                "LNG Plant Train": "Arzew GL1Z T1-T6",
                "Year": 2026,
                "Month": 1,
                "Period": 97,
            },
            source_row=11,
            source_col=34,
        )
        assert first["parameter_name"] == "LiqUtilAdjustment"
        assert first["axes"]["Country"] == "Algeria"
        assert first["axes"]["LNG Plant"] == "Arzew GL1Z"
        assert first["axes"]["LNG Plant Train"] == "Arzew GL1Z T1-T6"
        assert first["axes"]["Year"] == 2026
        assert first["axes"]["Month"] == 1
        assert first["axes"]["Period"] == 97
        assert first["source_row"] == 11
        assert first["source_col"] == 34
        assert first["value_name"] == "LiqUtilAdjustment"
        assert first["value"] == 0.19018404907975456

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_basecase_records_do_not_read_second_liq_prod_matrix_section(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "title": "Algeria Arzew GL1Z 2026 production",
                "narrative": "Algeria Arzew GL1Z 2026 production disruption",
                "dimension_values": {"affected_facility_type": "수출 시설"},
            },
            "scenario_group": {"event_type_l2_id": 11},
            "dimension_template": [
                {"dim_key": "affected_facility_type", "label": "영향 시설 유형"},
            ],
        }
        candidates, _, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )
        assert not warnings
        liq_candidate = next(
            candidate
            for candidate in candidates
            if candidate["canonical_parameter_name"] == "LiqProdAdjustment"
        )
        assert liq_candidate["basecase_column_roles"] == (
            "B:Country,C:LNG Plant,D:LNG Plant Train,"
            "E:Life Cycle Category,F:Nameplate Capacity"
        )
        assert liq_candidate["basecase_value_start_col"] == "G"
        assert liq_candidate["basecase_value_end_col"] == "DA"

        records, record_warnings = build_basecase_records(
            kb,
            [liq_candidate],
            context,
        )

        assert records == []
        assert any("basecase record를 추출하지 못했습니다" in warning for warning in record_warnings)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_basecase_records_use_regas_first_matrix_section_only(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "title": "Japan 2026 regasification plant disruption",
                "narrative": "Japan 2026 Regasification plant disruption Negishi",
                "dimension_values": {"affected_facility_type": "수입 시설"},
            },
            "scenario_group": {"event_type_l2_id": 11},
            "dimension_template": [
                {"dim_key": "affected_facility_type", "label": "영향 시설 유형"},
            ],
        }
        candidates, _, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )
        assert not warnings
        regas_candidate = next(
            candidate
            for candidate in candidates
            if candidate["canonical_parameter_name"] == "RegasAdjustment"
        )
        assert regas_candidate["basecase_column_roles"] == (
            "B:Continent,C:Region,D:Country,E:Regasification plant,"
            "F:Life Cycle Category,G:Nameplate capacity"
        )
        assert regas_candidate["basecase_year_row"] == 9
        assert regas_candidate["basecase_month_row"] == 10
        assert regas_candidate["basecase_period_row"] is None
        assert regas_candidate["basecase_value_start_col"] == "H"
        assert regas_candidate["basecase_value_end_col"] == "DK"

        records, record_warnings = build_basecase_records(
            kb,
            [regas_candidate],
            context,
        )

        assert not record_warnings
        assert records
        first = _record_with(
            records,
            axes={
                "Continent": "Asia",
                "Region": "East Asia",
                "Country": "Japan",
                "Regasification plant": "Negishi",
                "Year": 2026,
                "Month": 1,
            },
            source_row=14,
            source_col=44,
        )
        assert first["parameter_name"] == "RegasAdjustment"
        assert first["axes"]["Continent"] == "Asia"
        assert first["axes"]["Region"] == "East Asia"
        assert first["axes"]["Country"] == "Japan"
        assert first["axes"]["Regasification plant"] == "Negishi"
        assert first["axes"]["Year"] == 2026
        assert first["axes"]["Month"] == 1
        assert "Period" not in first["axes"]
        assert first["source_row"] == 14
        assert first["source_col"] == 44
        assert first["value_name"] == "RegasAdjustment"
        assert first["value"] == 1

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_basecase_records_use_fixed_column_spec_when_available(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "title": "Japan 2026 폭염 Temperature",
                "narrative": "Japan 2026 heat wave",
                "dimension_values": {"heatwave_intensity": "강"},
            },
            "scenario_group": {"event_type_l2_id": 7},
            "dimension_template": [
                {"dim_key": "heatwave_intensity", "label": "폭염 강도"},
            ],
        }
        candidates, _, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )
        assert not warnings
        temperature_candidate = next(
            candidate
            for candidate in candidates
            if candidate["canonical_parameter_name"] == "Temperature"
        )

        records, record_warnings = build_basecase_records(
            kb,
            [temperature_candidate],
            context,
        )

        assert not record_warnings
        assert records
        first = _record_with(
            records,
            axes={"Year": 2026, "Month": 1, "Country": "Japan"},
            source_col=15,
        )
        assert first["parameter_name"] == "Temperature"
        assert first["axes"] == {"Year": 2026, "Month": 1, "Country": "Japan"}
        assert first["source_col"] == 15
        assert first["value_name"] == "Temperature"
        assert first["value"] == 5.5

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_powermix_basecase_records_skip_ref_rows_and_start_at_real_data(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        context = {
            "scenario": {
                "scenario_id": 100,
                "title": "Japan coal power gap",
                "narrative": "Japan 2026 coal outage increases gas power generation",
                "dimension_values": {"alt_energy_absorption": "50%"},
            },
            "scenario_group": {"event_type_l2_id": 10},
            "dimension_template": [
                {"dim_key": "alt_energy_absorption", "label": "타 에너지원 흡수 가능성"},
            ],
        }
        candidates, _, warnings = match_parameter_candidates(
            kb,
            context,
            max_candidates=10,
        )
        assert not warnings
        powermix_candidate = next(
            candidate
            for candidate in candidates
            if candidate["canonical_parameter_name"] == "PowerMix"
        )
        assert powermix_candidate["basecase_data_start_row"] == 12

        records, record_warnings = build_basecase_records(
            kb,
            [powermix_candidate],
            context,
        )

        assert not record_warnings
        assert records
        first = _record_with(
            records,
            axes={"Year": 2026, "Country": "Japan", "Energy Source": "Gas"},
            source_row=19,
            source_col=6,
        )
        assert first["parameter_name"] == "PowerMix"
        assert first["axes"] == {"Year": 2026, "Country": "Japan", "Energy Source": "Gas"}
        assert first["source_row"] == 19
        assert first["source_col"] == 6
        assert first["value_name"] == "PowerMix"
        assert first["value"] == 0.323

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_degree_day_parameters_use_weather_hdd_cdd_table_with_row_filter(self) -> None:
        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        cases = [
            (
                "CDD",
                {
                    "scenario": {
                        "scenario_id": 100,
                        "title": "Japan 2026 heatwave CDD",
                        "narrative": "Japan 2026 heatwave CDD increase",
                        "dimension_values": {"heatwave_intensity": "강"},
                    },
                    "scenario_group": {"event_type_l2_id": 7},
                    "dimension_template": [
                        {"dim_key": "heatwave_intensity", "label": "폭염 강도"},
                    ],
                },
                "E=CDD",
                "7|heatwaveintensity|cdd|demand|weatheradjustment",
            ),
            (
                "HDD",
                {
                    "scenario": {
                        "scenario_id": 101,
                        "title": "Japan 2026 cold wave HDD",
                        "narrative": "Japan 2026 cold wave HDD increase",
                        "dimension_values": {"cold_wave_intensity": "강"},
                    },
                    "scenario_group": {"event_type_l2_id": 6},
                    "dimension_template": [
                        {"dim_key": "cold_wave_intensity", "label": "한파 강도"},
                    ],
                },
                "E=HDD",
                "6|coldwaveintensity|hdd|demand|weatheradjustment",
            ),
        ]

        for parameter_name, context, row_filter, candidate_key in cases:
            candidates, _, warnings = match_parameter_candidates(
                kb,
                context,
                max_candidates=10,
            )
            assert not warnings
            candidate = next(
                item
                for item in candidates
                if item["canonical_parameter_name"] == parameter_name
            )
            assert candidate["basecase_column_roles"] == (
                f"B:Year,C:Month,D:Country,E:DegreeDayType,G:{parameter_name}"
            )
            assert candidate["basecase_row_filter"] == row_filter

            records, record_warnings = build_basecase_records(
                kb,
                [candidate],
                context,
            )

            assert records == []
            assert any(candidate_key in warning for warning in record_warnings)

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_fixed_column_spec_is_defined_once_per_parameter(self) -> None:
        mapping_path = next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        workbook = load_workbook(mapping_path, read_only=True, data_only=True)
        dimension_sheet = workbook[DIMENSION_PARAMETER_MAPPING_SHEET]
        parameter_sheet = workbook[PARAMETER_EXCEL_MAPPING_SHEET]
        dimension_headers = [cell.value for cell in dimension_sheet[1]]
        parameter_headers = [cell.value for cell in parameter_sheet[1]]
        dimension_index = {header: index for index, header in enumerate(dimension_headers)}
        parameter_index = {header: index for index, header in enumerate(parameter_headers)}

        assert "basecase_column_roles" not in dimension_headers
        temperature_dimension_rows = [
            row for row in dimension_sheet.iter_rows(min_row=2, values_only=True)
            if row[dimension_index["canonical_parameter_name"]] == "Temperature"
        ]
        temperature_parameter_rows = [
            row for row in parameter_sheet.iter_rows(min_row=2, values_only=True)
            if row[parameter_index["canonical_parameter_name"]] == "Temperature"
        ]

        assert len(temperature_dimension_rows) == 2
        assert len(temperature_parameter_rows) == 1
        assert (
            temperature_parameter_rows[0][parameter_index["basecase_column_roles"]]
            == "K:Year,L:Month,M:Country,O:Temperature"
        )

    @unittest.skipUnless(_excel_available(), "model parameter Excel files are not available")
    def test_coal_and_gas_futures_are_split_parameters(self) -> None:
        mapping_path = next(DEFAULT_INPUT_DIR.glob("260625*.xlsx"))
        workbook = load_workbook(mapping_path, read_only=True, data_only=True)
        dimension_sheet = workbook[DIMENSION_PARAMETER_MAPPING_SHEET]
        parameter_sheet = workbook[PARAMETER_EXCEL_MAPPING_SHEET]
        dimension_headers = [cell.value for cell in dimension_sheet[1]]
        parameter_headers = [cell.value for cell in parameter_sheet[1]]
        dimension_index = {header: index for index, header in enumerate(dimension_headers)}
        parameter_index = {header: index for index, header in enumerate(parameter_headers)}

        dimension_canonicals = [
            row[dimension_index["canonical_parameter_name"]]
            for row in dimension_sheet.iter_rows(min_row=2, values_only=True)
            if row[dimension_index["event_type_l2_id"]] == 10
            and row[dimension_index["dimension_key"]] == "lng_demand_impact_intensity"
        ]
        parameter_canonicals = {
            row[parameter_index["canonical_parameter_name"]]
            for row in parameter_sheet.iter_rows(min_row=2, values_only=True)
        }

        assert "Coal/Gas Futures Price" not in dimension_canonicals
        assert {"Coal Futures Price", "Gas Futures Price"} <= set(dimension_canonicals)
        assert "Coal/Gas Futures Price" not in parameter_canonicals
        assert {"Coal Futures Price", "Gas Futures Price"} <= parameter_canonicals

        kb = _get_excel_kb(max_sample_rows=1, max_sample_cols=8)
        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            {
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": {"lng_demand_impact_intensity": "높음"},
                },
                "scenario_group": {"event_type_l2_id": 10},
                "dimension_template": [
                    {"dim_key": "lng_demand_impact_intensity", "label": "LNG 수요 영향 강도"},
                ],
            },
            max_candidates=10,
        )

        assert not warnings
        assert non_inputs == []
        assert {
            candidate["canonical_parameter_name"]
            for candidate in candidates
        } >= {"Coal Futures Price", "Gas Futures Price"}

    def test_to_output_returns_key_content_only(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelInputService",
        ) as service_cls:
            service_cls.return_value.save_proposal_result.return_value = 777
            output = to_output(
                {
                    "scenario_id": 100,
                    "scenario_context": {
                        "scenario": {"scenario_id": 100, "scenario_group_id": 20},
                        "scenario_group": {"scenario_group_id": 20, "mi_event_id": 30},
                        "event": {"mi_event_id": 30},
                    },
                    "candidate_mappings": [
                        {
                            "candidate_key": "selected",
                            "parameter_name": "PowerMix",
                            "basecase_value_name": "PowerMixAdjust",
                        },
                        {
                            "candidate_key": "rejected",
                            "parameter_name": "ShippingCost",
                            "basecase_value_name": "ShippingCost",
                        },
                    ],
                    "basecase_records": [{"candidate_key": "debug"}],
                    "parameter_slots": [{"candidate_key": "debug"}],
                    "parameter_adjustments": [
                        {
                            "candidate_key": "selected",
                            "model_file": "Demand",
                            "model_sheet": "PowerMixAdjustment",
                            "parameter_name": "PowerMix",
                            "selected": True,
                            "slot_axes": [
                                {"axis_name": "Country", "axis_value": "Japan"},
                            ],
                            "value_grid": [
                                {
                                    "coordinates": {
                                        "Country": "Japan",
                                        "Energy Source": "Gas",
                                        "Year": 2026,
                                    },
                                    "basecase_value": 0.323,
                                    "proposed_value": 0.35,
                                    "unit": "%",
                                    "operation": "absolute",
                                    "value_selection_rationale_ko": "Japan Gas 2026 row를 선택했습니다.",
                                    "proposed_value_rationale_ko": "석탄 발전 차질을 반영했습니다.",
                                    "basecase_reference_ids": ["ref1"],
                                },
                            ],
                            "parameter_selection_rationale_ko": "가스발전 비중 조정이 필요합니다.",
                            "confidence_overall": 0.8,
                        },
                        {
                            "candidate_key": "rejected",
                            "model_file": "Trade",
                            "model_sheet": "ShippingCostInput",
                            "parameter_name": "ShippingCost",
                            "selected": False,
                            "slot_axes": [],
                            "value_grid": [],
                            "parameter_selection_rationale_ko": "운송 영향이 직접적이지 않습니다.",
                            "confidence_overall": 0.7,
                        },
                    ],
                    "non_input_items": [],
                    "validation_warnings": ["w1"],
                    "llm_usage": {"debug": True},
                },
            )

        dumped = output.model_dump(by_alias=True)
        assert dumped["status"] == "success"
        assert dumped["message"] == "model parameter proposal completed"
        data = dumped["data"]
        assert data["modelParamProposalId"] == 777
        assert data["scenarioId"] == 100
        assert data["scenarioGroupId"] == 20
        assert data["eventId"] == 30
        assert len(data["proposalParameters"]) == 1
        proposal_parameter = data["proposalParameters"][0]
        assert proposal_parameter["parameterName"] == "PowerMix"
        assert proposal_parameter["modelTarget"] == {
            "modelFile": "Demand",
            "modelSheet": "PowerMixAdjustment",
            "valueFieldNames": ["PowerMixAdjust"],
            "slotAxesFieldNames": ["Country", "Energy Source", "Year"],
        }
        assert proposal_parameter["rationale"] == "가스발전 비중 조정이 필요합니다."
        assert proposal_parameter["values"][0]["Country"] == "Japan"
        assert proposal_parameter["values"][0]["Energy Source"] == "Gas"
        assert proposal_parameter["values"][0]["Year"] == 2026
        assert proposal_parameter["values"][0]["basecaseValue"] == 0.323
        assert proposal_parameter["values"][0]["proposedValue"] == 0.35
        assert "Japan Gas 2026 row" in proposal_parameter["values"][0]["rationale"]
        assert "slot" not in proposal_parameter["values"][0]
        assert "operation" not in proposal_parameter["values"][0]
        assert "unit" not in proposal_parameter["values"][0]
        assert "warnings" not in proposal_parameter
        assert "warnings" not in dumped
        assert "needsUserReview" not in proposal_parameter
        assert "needsUserReview" not in str(dumped)
        assert "parameterAdjustments" not in dumped
        assert "nonInputItems" not in dumped
        assert "validationWarnings" not in dumped
        assert "scenarioContext" not in dumped
        assert "candidateMappings" not in dumped
        assert "basecaseSamples" not in dumped
        assert "basecaseRecords" not in dumped
        assert "parameterSlots" not in dumped
        assert "llmUsage" not in dumped
        service_cls.return_value.save_proposal_result.assert_called_once()

    def test_event_type_is_not_forcibly_suppressed(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelInputService",
        ) as service_cls:
            service_cls.return_value.save_proposal_result.return_value = 778
            for event_type_l2_id in (6, 10):
                output = to_output(
                    {
                        "scenario_id": 100,
                        "scenario_context": {
                            "scenario": {
                                "scenario_id": 100,
                                "scenario_group_id": 20,
                            },
                            "scenario_group": {
                                "scenario_group_id": 20,
                                "mi_event_id": 30,
                                "event_type_l2_id": event_type_l2_id,
                            },
                            "event": {"mi_event_id": 30},
                        },
                        "candidate_mappings": [
                            {
                                "candidate_key": "selected",
                                "parameter_name": "PowerMix",
                                "basecase_value_name": "PowerMixAdjust",
                            },
                        ],
                        "parameter_adjustments": [
                            {
                                "candidate_key": "selected",
                                "model_file": "Demand",
                                "model_sheet": "PowerMixAdjustment",
                                "parameter_name": "PowerMix",
                                "selected": True,
                                "slot_axes": [],
                                "value_grid": [
                                    {
                                        "coordinates": {
                                            "Country": "Japan",
                                            "Year": 2026,
                                        },
                                        "basecase_value": 0.1,
                                        "proposed_value": 0.2,
                                        "unit": "%",
                                        "operation": "absolute",
                                        "value_selection_rationale_ko": "명확한 축",
                                        "proposed_value_rationale_ko": "명확한 값",
                                    },
                                ],
                                "parameter_selection_rationale_ko": "중간 결과",
                            },
                        ],
                    },
                )
                assert output.model_dump(by_alias=True)["data"]["proposalParameters"]

    def test_period_start_uses_explicit_year_month_as_is(self) -> None:
        year, month, basis = _period_start_year_month(
            {"period": "3개월"},
            {
                "scenario": {"title": "겨울 한파"},
                "event": {
                    "occurred_at": "",
                    "latest_record_first_created": "2026-03-04T00:00:00",
                    "event_title_ko": "미국 중북부 3월 중순 한파 전망",
                },
            },
        )

        assert (year, month) == (2026, 3)
        assert "명시된 연월" in basis

    def test_period_start_maps_month_only_to_current_or_future_year(self) -> None:
        today = date.today()
        previous_month = 12 if today.month == 1 else today.month - 1
        expected_year = today.year if previous_month >= today.month else today.year + 1

        year, month, basis = _period_start_year_month(
            {"period": "1개월 이하", "peak_timing_pattern": f"{previous_month}월 Peak"},
            {
                "scenario": {"title": "월만 지정된 시나리오"},
                "event": {"event_title_ko": "연도 없는 월 기준 이벤트"},
            },
        )

        assert (year, month) == (expected_year, previous_month)
        assert "월-only" in basis

    def test_year_month_coordinate_allows_explicit_past_month(self) -> None:
        assert _coordinate_issues({"Year": 2026, "Month": 3, "Country": "United States"}) == []

    def test_to_output_excludes_unusable_values(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelInputService",
        ) as service_cls:
            service_cls.return_value.save_proposal_result.return_value = 779
            output = to_output(
                {
                    "scenario_id": 100,
                    "scenario_context": {
                        "scenario": {
                            "scenario_id": 100,
                            "scenario_group_id": 20,
                        },
                        "scenario_group": {
                            "scenario_group_id": 20,
                            "mi_event_id": 30,
                        },
                        "event": {"mi_event_id": 30},
                    },
                    "candidate_mappings": [
                        {
                            "candidate_key": "null_value",
                            "parameter_name": "PMI",
                            "basecase_value_name": "PMI",
                        },
                        {
                            "candidate_key": "unknown_operation",
                            "parameter_name": "GDP",
                            "basecase_value_name": "GDP",
                        },
                    ],
                    "parameter_adjustments": [
                        {
                            "candidate_key": "null_value",
                            "model_file": "Demand",
                            "model_sheet": "PMIAdjustment",
                            "parameter_name": "PMI",
                            "selected": True,
                            "slot_axes": [],
                            "value_grid": [
                                {
                                    "coordinates": {"Country": "China", "Year": 2026},
                                    "basecase_value": 49.5,
                                    "proposed_value": None,
                                    "unit": "index",
                                    "operation": "absolute",
                                    "value_selection_rationale_ko": "China 2026 row",
                                    "proposed_value_rationale_ko": "정량 근거 없음",
                                },
                            ],
                            "parameter_selection_rationale_ko": "PMI 조정 후보",
                            "confidence_overall": 0.5,
                        },
                        {
                            "candidate_key": "unknown_operation",
                            "model_file": "Demand",
                            "model_sheet": "GDPPopulationAdjustment",
                            "parameter_name": "GDP",
                            "selected": True,
                            "slot_axes": [],
                            "value_grid": [
                                {
                                    "coordinates": {"Country": "China", "Year": 2026},
                                    "basecase_value": 0.04,
                                    "proposed_value": 0.045,
                                    "unit": "%",
                                    "operation": "unknown",
                                    "value_selection_rationale_ko": "China 2026 row",
                                    "proposed_value_rationale_ko": "성장률 전망 반영",
                                },
                            ],
                            "parameter_selection_rationale_ko": "GDP 조정 후보",
                            "confidence_overall": 0.5,
                        },
                    ],
                },
            )

        dumped = output.model_dump(by_alias=True, exclude_none=True)
        assert dumped["data"]["scenarioId"] == 100
        assert dumped["data"]["modelParamProposalId"] == 779
        assert dumped["data"]["proposalParameters"] == []


class ModelParameterAgentLLMTest(unittest.IsolatedAsyncioTestCase):
    async def test_llm_candidate_validation_keeps_direct_and_filters_routing_candidates(self) -> None:
        direct_candidate = {
            "candidate_key": "direct",
            "mapping_method": "direct",
            "model_file": "Demand",
            "model_sheet": "PowerMixAdjustment",
            "parameter_name": "PowerMix",
            "canonical_parameter_name": "PowerMix",
        }
        routing_candidate = {
            "candidate_key": "routing",
            "mapping_method": "routing",
            "model_file": "Supply",
            "model_sheet": "RegasAdjustment",
            "parameter_name": "RegasAdjustment",
            "canonical_parameter_name": "RegasAdjustment",
        }
        candidate_response = LLMCandidateValidationResponse(
            candidate_decisions=[
                ParameterCandidateDecision(
                    candidate_key="direct",
                    selected=False,
                    rationale_ko="시나리오 문맥상 발전 믹스 조정은 직접 영향이 아닙니다.",
                    confidence_overall=0.8,
                ),
                ParameterCandidateDecision(
                    candidate_key="routing",
                    selected=True,
                    rationale_ko="수입 시설 피해이므로 재기화 조정 후보가 적합합니다.",
                    confidence_overall=0.9,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": {"affected_facility_type": "수입 시설"},
                },
            },
            candidate_mappings=[direct_candidate, routing_candidate],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await validate_parameter_candidates(state)

        assert [candidate["candidate_key"] for candidate in result["candidate_mappings"]] == [
            "direct",
            "routing",
        ]
        assert "direct로 지정된 모델 input" in result["candidate_mappings"][0][
            "candidate_validation_rationale_ko"
        ]
        assert result["candidate_mappings"][1]["candidate_validation_rationale_ko"].startswith(
            "수입 시설",
        )
        assert any("direct 후보는 LLM selected=false" in warning for warning in result["validation_warnings"])

    async def test_llm_candidate_validation_omitted_direct_candidate_is_kept(self) -> None:
        candidates = [
            {
                "candidate_key": "c1",
                "mapping_method": "direct",
                "model_file": "Demand",
                "model_sheet": "PowerMixAdjustment",
                "parameter_name": "PowerMix",
                "canonical_parameter_name": "PowerMix",
            },
            {
                "candidate_key": "c2",
                "mapping_method": "direct",
                "model_file": "Trade",
                "model_sheet": "ShippingCostInput",
                "parameter_name": "ShippingCost",
                "canonical_parameter_name": "ShippingCost",
            },
        ]
        candidate_response = LLMCandidateValidationResponse(
            candidate_decisions=[
                ParameterCandidateDecision(
                    candidate_key="c1",
                    selected=True,
                    rationale_ko="발전 믹스 조정 후보가 적합합니다.",
                    confidence_overall=0.8,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=candidates,
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await validate_parameter_candidates(state)

        assert [candidate["candidate_key"] for candidate in result["candidate_mappings"]] == ["c1", "c2"]
        assert any("누락된 direct candidate_key는 유지" in warning for warning in result["validation_warnings"])

    async def test_llm_candidate_validation_omitted_routing_candidate_is_excluded(self) -> None:
        candidates = [
            {
                "candidate_key": "c1",
                "mapping_method": "routing",
                "model_file": "Demand",
                "model_sheet": "PowerMixAdjustment",
                "parameter_name": "PowerMix",
                "canonical_parameter_name": "PowerMix",
            },
            {
                "candidate_key": "c2",
                "mapping_method": "routing",
                "model_file": "Trade",
                "model_sheet": "ShippingCostInput",
                "parameter_name": "ShippingCost",
                "canonical_parameter_name": "ShippingCost",
            },
        ]
        candidate_response = LLMCandidateValidationResponse(
            candidate_decisions=[
                ParameterCandidateDecision(
                    candidate_key="c1",
                    selected=True,
                    rationale_ko="발전 믹스 조정 후보가 적합합니다.",
                    confidence_overall=0.8,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=candidates,
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await validate_parameter_candidates(state)

        assert [candidate["candidate_key"] for candidate in result["candidate_mappings"]] == ["c1"]
        assert any("누락된 candidate_key" in warning for warning in result["validation_warnings"])

    async def test_routing_comment_overrides_llm_candidate_validation(self) -> None:
        supply_candidate = {
            "candidate_key": "11|affectedfacilitytype|supplydisruption|supply|volumeadjustment",
            "event_type_l2_id": 11,
            "dimension_key": "affected_facility_type",
            "source_dimension_id": "affected_facility_type",
            "source_dimension_value": "생산 시설",
            "mapping_method": "routing",
            "mapping_comment": "생산 시설 피해 시",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
        }
        liq_candidate = {
            "candidate_key": "11|affectedfacilitytype|liqutiladjustment|supply|liqutiladjustment",
            "event_type_l2_id": 11,
            "dimension_key": "affected_facility_type",
            "source_dimension_id": "affected_facility_type",
            "source_dimension_value": "생산 시설",
            "mapping_method": "routing",
            "mapping_comment": "수출(액화) 시설 피해 시",
            "model_file": "Supply",
            "model_sheet": "LiqUtilAdjustment",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
        }
        candidate_response = LLMCandidateValidationResponse(
            candidate_decisions=[
                ParameterCandidateDecision(
                    candidate_key=liq_candidate["candidate_key"],
                    selected=True,
                    rationale_ko="LLM은 액화시설로 판단했습니다.",
                    confidence_overall=0.7,
                ),
                ParameterCandidateDecision(
                    candidate_key=supply_candidate["candidate_key"],
                    selected=False,
                    rationale_ko="LLM은 생산 시설 후보를 제외했습니다.",
                    confidence_overall=0.6,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=279,
            scenario_context={"scenario": {"scenario_id": 279}},
            candidate_mappings=[supply_candidate, liq_candidate],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await validate_parameter_candidates(state)

        assert [candidate["candidate_key"] for candidate in result["candidate_mappings"]] == [
            supply_candidate["candidate_key"],
        ]
        assert any("routing 후보를 DB 매핑 comment 기준" in warning for warning in result["validation_warnings"])

    async def test_llm_structured_slot_and_value_calls_are_used_and_sanitized(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Trade",
            "model_sheet": "ShippingCostInput",
            "parameter_name": "ShippingCost",
            "canonical_parameter_name": "ShippingCost",
        }
        omitted_candidate = {
            "candidate_key": "c2",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
        }
        slot_response = LLMSlotProposalResponse(
            parameter_slots=[
                ParameterSlotProposal(
                    candidate_key="c1",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(
                            axis_name="Year",
                            axis_value="2026",
                            rationale="기간 dimension 근거",
                        ),
                    ],
                    rationale_ko_overall="운송 차질이 높아 ShippingCost slot 조정이 필요합니다.",
                    confidence_overall=0.7,
                ),
            ],
        )
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Invented",
                    model_sheet="Invented",
                    parameter_name="Invented",
                    slot_axes=[],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={"Year": 2026},
                            basecase_value=None,
                            proposed_value=1.2,
                            unit="ratio",
                            operation="percent_change",
                            value_selection_rationale_ko=(
                                "2026년 ShippingCost basecase record를 선택했습니다."
                            ),
                            proposed_value_rationale_ko=(
                                "운송 차질 scenario dimension을 반영해 basecase 대비 20% 상향했습니다."
                            ),
                            basecase_reference_ids=["ref1"],
                        ),
                    ],
                    parameter_selection_rationale_ko=(
                        "운송 차질이 높아 ShippingCost 조정이 필요합니다."
                    ),
                    confidence_overall=0.7,
                ),
            ],
        )
        requested_schemas: list[str] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            output_schema = kwargs["output_schema"]
            requested_schemas.append(output_schema.__name__)
            if output_schema is LLMSlotProposalResponse:
                return SimpleNamespace(result=slot_response, usage=None)
            if output_schema is LLMValueProposalResponse:
                return SimpleNamespace(result=value_response, usage=None)
            raise AssertionError(f"unexpected schema: {output_schema}")

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate, omitted_candidate],
            basecase_records=[
                {
                    "candidate_key": "c1",
                    "reference_id": "ref1",
                    "axes": {"Year": 2026},
                    "value": 1.0,
                },
            ],
        )

        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            slot_result = await propose_parameter_slots(state)
            value_state = state.model_copy(
                update={"parameter_slots": slot_result["parameter_slots"]},
            )
            result = await propose_parameter_values(value_state)

        adjustment = result["parameter_adjustments"][0]
        assert requested_schemas == [
            "LLMSlotProposalResponse",
            "LLMValueProposalResponse",
        ]
        assert adjustment["model_file"] == "Trade"
        assert adjustment["model_sheet"] == "ShippingCostInput"
        assert adjustment["parameter_name"] == "ShippingCost"
        assert adjustment["slot_axes"][0]["axis_name"] == "Year"
        assert adjustment["parameter_selection_rationale_ko"].startswith("운송 차질")
        assert adjustment["value_grid"][0]["basecase_value"] == 1.0
        assert adjustment["value_grid"][0]["basecase_reference_ids"] == ["ref1"]
        assert "value_selection_rationale_ko" in adjustment["value_grid"][0]
        assert "proposed_value_rationale_ko" in adjustment["value_grid"][0]
        patched = result["parameter_adjustments"][1]
        assert patched["candidate_key"] == "c2"
        assert patched["selected"] is False
        assert patched["needs_user_review"] is True
        assert "누락" in patched["parameter_selection_rationale_ko"]

    async def test_slot_prompt_uses_distinct_basecase_slot_options(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Supply",
            "model_sheet": "LiqUtilAdjustment",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
        }
        records = [
            {
                "candidate_key": "c1",
                "reference_id": "cameron-2026-a",
                "model_file": "Supply",
                "sheet_name": "LiqUtilAdjustment",
                "parameter_name": "LiqUtilAdjustment",
                "axes": {"Plant": "Cameron", "Year": 2026},
                "value_name": "LiqUtilAdjustment",
                "value": 1.0,
            },
            {
                "candidate_key": "c1",
                "reference_id": "cameron-2026-b",
                "model_file": "Supply",
                "sheet_name": "LiqUtilAdjustment",
                "parameter_name": "LiqUtilAdjustment",
                "axes": {"Plant": "Cameron", "Year": 2026},
                "value_name": "LiqUtilAdjustment",
                "value": 2.0,
            },
            {
                "candidate_key": "c1",
                "reference_id": "sabine-2027",
                "model_file": "Supply",
                "sheet_name": "LiqUtilAdjustment",
                "parameter_name": "LiqUtilAdjustment",
                "axes": {"Plant": "Sabine", "Year": 2027},
                "value_name": "LiqUtilAdjustment",
                "value": 3.0,
            },
        ]
        slot_response = LLMSlotProposalResponse(
            parameter_slots=[
                ParameterSlotProposal(
                    candidate_key="c1",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(
                            axis_name="Plant",
                            axis_value="Plant-42",
                            rationale="event에 명시된 설비",
                        ),
                    ],
                    rationale_ko_overall="설비 차질 event를 반영했습니다.",
                    confidence_overall=0.8,
                ),
            ],
        )
        captured_contents: list[str] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMSlotProposalResponse
            captured_contents.append(kwargs["messages"][1]["content"])
            return SimpleNamespace(result=slot_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate],
            basecase_records=records,
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_slots(state)

        assert result["parameter_slots"][0]["candidate_key"] == "c1"
        assert captured_contents
        payload = json.loads(captured_contents[0].split("\n", 1)[1])
        assert payload["basecase_records"] == []
        assert "basecase_record_summaries" not in payload
        assert payload["basecase_slot_options"] == [
            {
                "candidate_key": "c1",
                "model_file": "Supply",
                "sheet_name": "LiqUtilAdjustment",
                "parameter_name": "LiqUtilAdjustment",
                "record_count": 3,
                "axis_names": ["Plant", "Year"],
                "axis_values": {
                    "Plant": ["Cameron", "Sabine"],
                    "Year": [2026, 2027],
                },
                "value_names": ["LiqUtilAdjustment"],
            },
        ]
        assert "cameron-2026-a" not in captured_contents[0]
        assert "sabine-2027" not in captured_contents[0]

    async def test_weather_slot_selection_calls_llm_without_compact_bypass(self) -> None:
        candidate = {
            "candidate_key": "temperature-direct",
            "mapping_method": "direct",
            "event_type_l2_id": 7,
            "model_file": "Demand",
            "model_sheet": "TemperatureAdjustment",
            "parameter_name": "Temperature",
            "canonical_parameter_name": "Temperature",
        }
        slot_response = LLMSlotProposalResponse(
            parameter_slots=[
                ParameterSlotProposal(
                    candidate_key="temperature-direct",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(axis_name="Country", axis_value="Japan"),
                        ParameterSlotAxis(axis_name="Year", axis_value="2026"),
                        ParameterSlotAxis(axis_name="Month", axis_value="8"),
                    ],
                    rationale_ko_overall="basecase slot 후보와 폭염 scenario를 함께 검증했습니다.",
                    confidence_overall=0.9,
                ),
            ],
        )
        requested_schemas: list[str] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            requested_schemas.append(kwargs["output_schema"].__name__)
            return SimpleNamespace(result=slot_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=289,
            scenario_context={
                "scenario": {
                    "scenario_id": 289,
                    "dimension_values": {"temperature_delta": "+3C", "period": "1개월"},
                },
                "scenario_group": {"event_type_l2_id": 7},
                "event": {"event_type_l2_id": 7, "event_title_ko": "일본 폭염"},
            },
            candidate_mappings=[candidate],
            basecase_records=[
                {
                    "candidate_key": "temperature-direct",
                    "reference_id": "temp-jp-2026-8",
                    "model_file": "Demand",
                    "sheet_name": "TemperatureAdjustment",
                    "parameter_name": "Temperature",
                    "axes": {"Country": "Japan", "Year": 2026, "Month": 8},
                    "value_name": "Temperature",
                    "value": 27.5,
                },
            ],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_slots(state)

        assert requested_schemas == ["LLMSlotProposalResponse"]
        assert result["parameter_slots"][0]["candidate_key"] == "temperature-direct"
        assert result["parameter_slots"][0]["slot_axes"][0]["axis_value"] == "Japan"

    def test_basecase_records_are_filtered_by_selected_slots_for_value_prompt(self) -> None:
        records = [
            {
                "candidate_key": "c1",
                "reference_id": "cameron-2026-a",
                "axes": {"Plant": "Cameron", "Year": 2026},
                "value": 1.0,
            },
            {
                "candidate_key": "c1",
                "reference_id": "cameron-2026-b",
                "axes": {"Plant": "Cameron", "Year": 2026},
                "value": 2.0,
            },
            {
                "candidate_key": "c1",
                "reference_id": "sabine-2026",
                "axes": {"Plant": "Sabine", "Year": 2026},
                "value": 1.0,
            },
            {
                "candidate_key": "c2",
                "reference_id": "other-2026",
                "axes": {"Plant": "Cameron", "Year": 2026},
                "value": 1.0,
            },
        ]
        state = ModelParameterProposalState(
            scenario_id=100,
            basecase_records=records,
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {
                            "axis_name": "Plant",
                            "axis_value": "Cameron",
                            "rationale": "event에 명시된 설비",
                        },
                        {
                            "axis_name": "Year",
                            "axis_value": "2026",
                            "rationale": "event 발생 연도",
                        },
                    ],
                    "rationale_ko_overall": "명확한 설비와 연도",
                    "confidence_overall": 0.8,
                    "needs_user_review": False,
                    "warnings": [],
                },
            ],
        )

        result = filter_basecase_records_by_slots(state)

        assert [record["reference_id"] for record in result["basecase_records"]] == [
            "cameron-2026-a",
            "cameron-2026-b",
        ]

    async def test_llm_slot_sanitizer_rejects_ambiguous_axis_values(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
        }
        slot_response = LLMSlotProposalResponse(
            parameter_slots=[
                ParameterSlotProposal(
                    candidate_key="c1",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(
                            axis_name="Year",
                            axis_value="미정(후보: 2024)",
                            rationale="발생 연도 불명",
                        ),
                    ],
                    rationale_ko_overall="연도 후보를 제안했습니다.",
                    confidence_overall=0.4,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMSlotProposalResponse
            return SimpleNamespace(result=slot_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_slots(state)

        slot = result["parameter_slots"][0]
        assert slot["candidate_key"] == "c1"
        assert slot["selected"] is False
        assert slot["slot_axes"] == []
        assert slot["needs_user_review"] is True
        assert any("모호한 slot" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_rejects_ambiguous_coordinates(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Supply",
                    model_sheet="VolumeAdjustment",
                    parameter_name="SupplyDisruption",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(
                            axis_name="Province Country",
                            axis_value="Norway",
                            rationale="event 명시 국가",
                        ),
                    ],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={
                                "Province Country": "Norway 또는 대체 공급국",
                                "Year": 2026,
                            },
                            basecase_value=None,
                            proposed_value=0.01,
                            unit="%",
                            operation="absolute",
                            value_selection_rationale_ko="대체 공급국 후보를 함께 제시했습니다.",
                            proposed_value_rationale_ko="공급 차질을 반영했습니다.",
                        ),
                    ],
                    parameter_selection_rationale_ko="공급 차질 조정이 필요합니다.",
                    confidence_overall=0.5,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {
                            "axis_name": "Province Country",
                            "axis_value": "Norway",
                            "rationale": "event 명시 국가",
                        },
                    ],
                    "rationale_ko_overall": "명확한 국가 축",
                    "confidence_overall": 0.8,
                    "needs_user_review": False,
                    "warnings": [],
                },
            ],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_values(state)

        adjustment = result["parameter_adjustments"][0]
        assert adjustment["candidate_key"] == "c1"
        assert adjustment["selected"] is False
        assert adjustment["value_grid"] == []
        assert adjustment["needs_user_review"] is True
        assert any("coordinates에 모호한 값" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_allows_clear_value_without_basecase(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Supply",
                    model_sheet="VolumeAdjustment",
                    parameter_name="SupplyDisruption",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(
                            axis_name="Province Country",
                            axis_value="Norway",
                            rationale="event 명시 국가",
                        ),
                        ParameterSlotAxis(
                            axis_name="Year",
                            axis_value="2026",
                            rationale="event 명시 연도",
                        ),
                    ],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={"Province Country": "Norway", "Year": 2026},
                            basecase_value=None,
                            proposed_value=0.03,
                            unit="%",
                            operation="absolute",
                            value_selection_rationale_ko="event에 Norway 2026 차질이 명시되었습니다.",
                            proposed_value_rationale_ko="<5% 범위를 자동 변환해 3%로 산정했습니다.",
                        ),
                    ],
                    parameter_selection_rationale_ko="공급 차질 조정이 필요합니다.",
                    confidence_overall=0.8,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Province Country", "axis_value": "Norway"},
                        {"axis_name": "Year", "axis_value": "2026"},
                    ],
                    "rationale_ko_overall": "명확한 event 축",
                    "confidence_overall": 0.8,
                    "needs_user_review": False,
                    "warnings": [],
                },
            ],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_values(state)

        adjustment = result["parameter_adjustments"][0]
        assert adjustment["selected"] is True
        assert adjustment["value_grid"][0]["basecase_value"] is None
        assert adjustment["value_grid"][0]["proposed_value"] == 0.03
        assert adjustment["value_grid"][0]["operation"] == "absolute"

    async def test_regas_adjustment_is_backfilled_for_import_facility_damage(self) -> None:
        candidate = {
            "candidate_key": "routing-regas",
            "mapping_method": "routing",
            "model_file": "Supply",
            "model_sheet": "RegasAdjustment",
            "parameter_name": "RegasAdjustment",
            "canonical_parameter_name": "RegasAdjustment",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="routing-regas",
                    model_file="Supply",
                    model_sheet="RegasAdjustment",
                    parameter_name="RegasAdjustment",
                    selected=False,
                    slot_axes=[],
                    value_grid=[],
                    parameter_selection_rationale_ko="LLM이 정량 값을 확정하지 못했습니다.",
                    confidence_overall=0.2,
                    needs_user_review=True,
                    warnings=["정량 값 미확정"],
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=280,
            scenario_context={
                "scenario": {
                    "scenario_id": 280,
                    "title": "수입 시설 피해",
                    "dimension_values": {
                        "affected_facility_type": "수입 시설",
                        "alt_lng_supply_availability": "25%",
                        "supply_disruption_intensity": "중간",
                    },
                },
                "event": {
                    "event_title_ko": "호주 서부 LNG 자연재해성 차질",
                    "detail_analysis": "호주 서부 수입 터미널 및 재기화 인프라 피해",
                },
            },
            candidate_mappings=[candidate],
            parameter_slots=[],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_values(state)

        adjustment = result["parameter_adjustments"][0]
        assert adjustment["candidate_key"] == "routing-regas"
        assert adjustment["selected"] is True
        assert adjustment["parameter_name"] == "RegasAdjustment"
        value = adjustment["value_grid"][0]
        assert value["coordinates"]["Country"] == "Australia"
        assert value["coordinates"]["Year"] == 2026
        assert value["proposed_value"] == -11.25
        assert value["operation"] == "percent_change"

    async def test_rule_based_backfill_respects_multiple_step2_country_slots(self) -> None:
        candidate = {
            "candidate_key": "routing-regas",
            "mapping_method": "routing",
            "model_file": "Supply",
            "model_sheet": "RegasAdjustment",
            "parameter_name": "RegasAdjustment",
            "canonical_parameter_name": "RegasAdjustment",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="routing-regas",
                    model_file="Supply",
                    model_sheet="RegasAdjustment",
                    parameter_name="RegasAdjustment",
                    selected=False,
                    slot_axes=[],
                    value_grid=[],
                    parameter_selection_rationale_ko="LLM이 정량 값을 확정하지 못했습니다.",
                    confidence_overall=0.2,
                    needs_user_review=True,
                    warnings=["정량 값 미확정"],
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=281,
            scenario_context={
                "scenario": {
                    "scenario_id": 281,
                    "title": "복수 수입 시설 피해",
                    "dimension_values": {
                        "affected_facility_type": "수입 시설",
                        "alt_lng_supply_availability": "25%",
                        "supply_disruption_intensity": "중간",
                    },
                },
                "event": {
                    "event_title_ko": "수입 터미널 및 재기화 인프라 피해",
                    "detail_analysis": "국가는 Step2 slot에서 확정되었습니다.",
                },
            },
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "routing-regas",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Country", "axis_value": "Japan"},
                        {"axis_name": "Year", "axis_value": "2026"},
                    ],
                    "rationale_ko_overall": "Japan slot",
                    "confidence_overall": 0.8,
                    "needs_user_review": False,
                    "warnings": [],
                },
                {
                    "candidate_key": "routing-regas",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Country", "axis_value": "South Korea"},
                        {"axis_name": "Year", "axis_value": "2026"},
                    ],
                    "rationale_ko_overall": "South Korea slot",
                    "confidence_overall": 0.8,
                    "needs_user_review": False,
                    "warnings": [],
                },
            ],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_values(state)

        adjustment = result["parameter_adjustments"][0]
        assert adjustment["selected"] is True
        countries = [cell["coordinates"]["Country"] for cell in adjustment["value_grid"]]
        assert countries == ["Japan", "South Korea"]
        assert all(cell["coordinates"]["Year"] == 2026 for cell in adjustment["value_grid"])
        assert [cell["proposed_value"] for cell in adjustment["value_grid"]] == [-11.25, -11.25]
        assert all(
            "Step2에서 확정한 slot 좌표" not in cell["value_selection_rationale_ko"]
            for cell in adjustment["value_grid"]
        )

    async def test_llm_value_sanitizer_rejects_unusable_values(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Demand",
            "model_sheet": "PMIAdjustment",
            "parameter_name": "PMI",
            "canonical_parameter_name": "PMI",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Demand",
                    model_sheet="PMIAdjustment",
                    parameter_name="PMI",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(axis_name="Country", axis_value="China"),
                        ParameterSlotAxis(axis_name="Year", axis_value="2026"),
                    ],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={"Country": "China", "Year": 2026},
                            basecase_value=49.5,
                            proposed_value=None,
                            unit="index",
                            operation="absolute",
                            value_selection_rationale_ko="China 2026 row",
                            proposed_value_rationale_ko="정량 근거 없음",
                        ),
                        ParameterValueCell(
                            coordinates={"Country": "China", "Year": 2026},
                            basecase_value=49.5,
                            proposed_value=48.0,
                            unit="index",
                            operation="unknown",
                            value_selection_rationale_ko="China 2026 row",
                            proposed_value_rationale_ko="하락 방향만 제시",
                        ),
                    ],
                    parameter_selection_rationale_ko="PMI 조정 후보",
                    confidence_overall=0.5,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Country", "axis_value": "China"},
                        {"axis_name": "Year", "axis_value": "2026"},
                    ],
                    "rationale_ko_overall": "명확한 축",
                    "confidence_overall": 0.8,
                    "needs_user_review": False,
                    "warnings": [],
                },
            ],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_values(state)

        adjustment = result["parameter_adjustments"][0]
        assert adjustment["selected"] is False
        assert adjustment["value_grid"] == []
        assert adjustment["needs_user_review"] is True
        assert any("proposed_value가 null" in warning for warning in result["validation_warnings"])
        assert any("operation" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_rejects_duplicate_slot_value_conflicts(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Demand",
            "model_sheet": "WeatherAdjustment",
            "parameter_name": "Temperature",
            "canonical_parameter_name": "Temperature",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Demand",
                    model_sheet="WeatherAdjustment",
                    parameter_name="Temperature",
                    selected=True,
                    slot_axes=[
                        ParameterSlotAxis(axis_name="Country", axis_value="Germany"),
                        ParameterSlotAxis(axis_name="Year", axis_value="2026"),
                        ParameterSlotAxis(axis_name="Month", axis_value="12"),
                    ],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={"Country": "Germany", "Year": 2026, "Month": 12},
                            basecase_value=None,
                            proposed_value=-5,
                            unit="C",
                            operation="delta",
                            value_selection_rationale_ko="Germany 2026년 12월 slot입니다.",
                            proposed_value_rationale_ko="한파 강도를 delta로 산정했습니다.",
                        ),
                        ParameterValueCell(
                            coordinates={"Country": "Germany", "Year": "2026", "Month": "12"},
                            basecase_value=None,
                            proposed_value=-5,
                            unit="C",
                            operation="absolute",
                            value_selection_rationale_ko="Germany 2026년 12월 slot입니다.",
                            proposed_value_rationale_ko="한파 강도를 absolute로 산정했습니다.",
                        ),
                    ],
                    parameter_selection_rationale_ko="기온 조정이 필요합니다.",
                    confidence_overall=0.7,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Country", "axis_value": "Germany"},
                        {"axis_name": "Year", "axis_value": "2026"},
                        {"axis_name": "Month", "axis_value": "12"},
                    ],
                    "rationale_ko_overall": "명확한 월별 국가 slot",
                    "confidence_overall": 0.8,
                    "needs_user_review": False,
                    "warnings": [],
                },
            ],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_values(state)

        adjustment = result["parameter_adjustments"][0]
        assert adjustment["selected"] is False
        assert adjustment["value_grid"] == []
        assert adjustment["needs_user_review"] is True
        assert any("동일 slot 좌표" in warning for warning in result["validation_warnings"])


if __name__ == "__main__":
    unittest.main()
