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

from apps.agents.model_parameter_agent.api import router as model_parameter_router
from apps.agents.model_parameter_agent.flows.confirm_parameters.api_schema import (
    ConfirmParametersIn,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.validation import (
    validate_confirmation_parameters,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.flow import (
    _callback_error_output,
    _callback_success_output,
    _route_after_candidate_validation,
    build_graph,
    prepare_propose_parameters_callback,
    to_output,
)
from apps.agents.model_parameter_agent.flows.propose_parameters import flow as propose_flow
from apps.agents.model_parameter_agent.flows.propose_parameters import nodes as proposal_nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _build_basecase_slot_options,
    _build_basecase_value_groups,
    _coordinate_issues,
    _period_start_year_month,
    _scenario_brief_for_value_prompt,
    filter_basecase_records_by_slots,
    finalize_empty_parameter_values,
    load_scenario_context,
    propose_parameter_slots,
    propose_parameter_values,
    select_parameter_candidates,
    validate_parameter_candidates,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    DEFAULT_BASECASE_DIR,
    DEFAULT_INPUT_DIR,
    get_parameter_knowledge_base,
    get_parameter_knowledge_base_from_resources,
    match_parameter_candidates,
)
from apps.agents.model_parameter_agent.utils.basecase import build_basecase_records
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMCandidateValidationResponse,
    LLMSlotAxis,
    LLMSlotProposal,
    LLMSlotProposalResponse,
    LLMValueAdjustment,
    LLMValueCell,
    LLMValueProposalResponse,
    ParameterCandidateGroupDecision,
    ParameterSlotAxis,
    ParameterSlotProposal,
    ParameterAdjustment,
    ParameterValueCell,
)
from apps.agents.model_parameter_agent.schemas.api.parameters import (
    ModelParameterTarget,
    ProposalParameter,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.api_schema import (
    ProposeParametersData,
    ProposeParametersAcceptedOut,
    ProposeParametersIn,
    ProposeParametersRequest,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.common.exceptions.custom import MIBaseError


def _default_basecase_dir_or_none() -> Path | None:
    return DEFAULT_BASECASE_DIR if DEFAULT_BASECASE_DIR.is_dir() else None


def _basecase_available() -> bool:
    return _default_basecase_dir_or_none() is not None


def _default_basecase_dir() -> Path:
    path = _default_basecase_dir_or_none()
    if path is None:
        raise AssertionError("model parameter basecase directory is not available")
    return path


def _parameter_row(
    name: str,
    *,
    model_file: str,
    model_sheet: str,
    semantic_axes: str,
    basecase_read_mode: str,
    basecase_header_row: int,
    basecase_data_start_row: int,
    basecase_column_roles: str,
    basecase_row_filter: str | None = None,
    basecase_year_row: int | None = None,
    basecase_month_row: int | None = None,
    basecase_period_row: int | None = None,
    basecase_value_start_col: str | None = None,
    basecase_value_end_col: str | None = None,
) -> dict[str, object]:
    return {
        "enabled": True,
        "canonical_parameter_name": name,
        "parameter_name": name,
        "parameter_hint": semantic_axes,
        "model_file": model_file,
        "model_sheet": model_sheet,
        "model_table": None,
        "semantic_axes": semantic_axes,
        "basecase_read_mode": basecase_read_mode,
        "basecase_header_row": basecase_header_row,
        "basecase_data_start_row": basecase_data_start_row,
        "basecase_column_roles": basecase_column_roles,
        "basecase_row_filter": basecase_row_filter,
        "basecase_year_row": basecase_year_row,
        "basecase_month_row": basecase_month_row,
        "basecase_period_row": basecase_period_row,
        "basecase_value_start_col": basecase_value_start_col,
        "basecase_value_end_col": basecase_value_end_col,
        "basecase_stop_rule": "stop_when_all_key_columns_empty",
    }


def _mapping_row(
    event_type_l2_id: int,
    dimension_key: str,
    dimension_label: str,
    mapping_method: str,
    canonical_parameter_name: str | None,
    comment: str,
    *,
    enabled: bool = True,
) -> dict[str, object]:
    return {
        "enabled": enabled,
        "event_type_l2_id": event_type_l2_id,
        "dimension_key": dimension_key,
        "dimension_label": dimension_label,
        "mapping_method": mapping_method,
        "canonical_parameter_name": canonical_parameter_name,
        "parameter_name": canonical_parameter_name,
        "comment": comment,
    }


TEST_PARAMETER_ROWS: list[dict[str, object]] = [
    _parameter_row(
        "CDD",
        model_file="Demand",
        model_sheet="WeatherAdjustment",
        semantic_axes="평년 대비 기온편차 변환 - 국가·연·월",
        basecase_read_mode="fixed_columns",
        basecase_header_row=6,
        basecase_data_start_row=7,
        basecase_column_roles="B:Year,C:Month,D:Country,E:DegreeDayType,G:CDD",
        basecase_row_filter="E=CDD",
    ),
    _parameter_row(
        "Coal Futures Price",
        model_file="Demand",
        model_sheet="CoalGasAdjustment",
        semantic_axes="석탄 선물가격 strip - 지역·월",
        basecase_read_mode="fixed_columns",
        basecase_header_row=6,
        basecase_data_start_row=7,
        basecase_column_roles="B:Month-Year,C:Region,E:Coal Futures Price",
    ),
    _parameter_row(
        "Gas Futures Price",
        model_file="Demand",
        model_sheet="CoalGasAdjustment",
        semantic_axes="가스 선물가격 strip - 지역·월",
        basecase_read_mode="fixed_columns",
        basecase_header_row=6,
        basecase_data_start_row=7,
        basecase_column_roles="H:Month-Year,I:Region,K:Gas Futures Price",
    ),
    _parameter_row(
        "HDD",
        model_file="Demand",
        model_sheet="WeatherAdjustment",
        semantic_axes="평년 대비 기온편차 변환 - 국가·연·월",
        basecase_read_mode="fixed_columns",
        basecase_header_row=6,
        basecase_data_start_row=7,
        basecase_column_roles="B:Year,C:Month,D:Country,E:DegreeDayType,G:HDD",
        basecase_row_filter="E=HDD",
    ),
    _parameter_row(
        "HurricaneIntensity",
        model_file="Supply",
        model_sheet="{USA}Hurricanes",
        semantic_axes="미국 액화시설 허리케인 차질 - 연·월",
        basecase_read_mode="fixed_columns",
        basecase_header_row=7,
        basecase_data_start_row=8,
        basecase_column_roles="B:Year,C:Month,D:HurricaneIntensity",
    ),
    _parameter_row(
        "LiqProdAdjustment",
        model_file="Supply",
        model_sheet="LiqProdAdjustment",
        semantic_axes="액화시설 생산량 override - Country>Plant>Train·연·월",
        basecase_read_mode="matrix_time_columns",
        basecase_header_row=10,
        basecase_data_start_row=11,
        basecase_column_roles=(
            "B:Country,C:LNG Plant,D:LNG Plant Train,"
            "E:Life Cycle Category,F:Nameplate Capacity"
        ),
        basecase_year_row=7,
        basecase_month_row=8,
        basecase_period_row=9,
        basecase_value_start_col="G",
        basecase_value_end_col="DA",
    ),
    _parameter_row(
        "LiqUtilAdjustment",
        model_file="Supply",
        model_sheet="LiqUtilAdjustment",
        semantic_axes="액화시설 가동률 override - Country>Plant>Train·연·월",
        basecase_read_mode="matrix_time_columns",
        basecase_header_row=10,
        basecase_data_start_row=11,
        basecase_column_roles=(
            "B:Country,C:LNG Plant,D:LNG Plant Train,"
            "E:Life Cycle Category,F:Nameplate Capacity"
        ),
        basecase_year_row=7,
        basecase_month_row=8,
        basecase_period_row=9,
        basecase_value_start_col="G",
        basecase_value_end_col="DA",
    ),
    _parameter_row(
        "PowerMix",
        model_file="Demand",
        model_sheet="PowerMixAdjustment",
        semantic_axes="발전 에너지원 비중 - 국가·에너지원·연",
        basecase_read_mode="fixed_columns",
        basecase_header_row=6,
        basecase_data_start_row=12,
        basecase_column_roles="B:Year,C:Country,D:Energy Source,F:PowerMix",
    ),
    _parameter_row(
        "RegasAdjustment",
        model_file="Supply",
        model_sheet="RegasAdjustment",
        semantic_axes="재기화 설비 capa override - Continent>Region>Country>Plant·연·월",
        basecase_read_mode="matrix_time_columns",
        basecase_header_row=10,
        basecase_data_start_row=11,
        basecase_column_roles=(
            "B:Continent,C:Region,D:Country,E:Regasification plant,"
            "F:Life Cycle Category,G:Nameplate capacity"
        ),
        basecase_year_row=9,
        basecase_month_row=10,
        basecase_value_start_col="H",
        basecase_value_end_col="DK",
    ),
    _parameter_row(
        "ShippingCost",
        model_file="Trade",
        model_sheet="ShippingCostInput",
        semantic_axes="Charter/Fuel/Suez/Panama 비용 - impact_scope·연",
        basecase_read_mode="fixed_columns",
        basecase_header_row=5,
        basecase_data_start_row=6,
        basecase_column_roles="B:Year,F:ShippingCost",
    ),
    _parameter_row(
        "SupplyDisruption",
        model_file="Supply",
        model_sheet="VolumeAdjustment",
        semantic_axes="Upstream 생산 차질 - Province·연",
        basecase_read_mode="fixed_columns",
        basecase_header_row=7,
        basecase_data_start_row=8,
        basecase_column_roles="B:Year,C:Province Country,E:SupplyDisruption",
    ),
    _parameter_row(
        "Temperature",
        model_file="Demand",
        model_sheet="WeatherAdjustment",
        semantic_axes="기온 직접 - 국가·연·월",
        basecase_read_mode="fixed_columns",
        basecase_header_row=6,
        basecase_data_start_row=7,
        basecase_column_roles="K:Year,L:Month,M:Country,O:Temperature",
    ),
]


TEST_MAPPING_ROWS: list[dict[str, object]] = [
    _mapping_row(6, "period", "기간", "indirect", None, "동절기 월 슬롯"),
    _mapping_row(6, "cold_wave_intensity", "한파 강도", "direct", "HDD", "평년 대비 -℃ -> HDD 변환 입력"),
    _mapping_row(6, "cold_wave_intensity", "한파 강도", "direct", "Temperature", "기온 직접 입력"),
    _mapping_row(7, "period", "기간", "indirect", None, "하절기 월 슬롯"),
    _mapping_row(7, "heatwave_intensity", "폭염 강도", "direct", "CDD", "평년 대비 +℃ -> CDD 변환 입력"),
    _mapping_row(7, "heatwave_intensity", "폭염 강도", "direct", "Temperature", "기온 직접 입력"),
    _mapping_row(10, "lng_demand_impact_intensity", "LNG 수요 영향 강도", "direct", "Coal Futures Price", "가격기반 석탄-가스 스위칭"),
    _mapping_row(10, "lng_demand_impact_intensity", "LNG 수요 영향 강도", "direct", "Gas Futures Price", "가격기반 석탄-가스 스위칭"),
    _mapping_row(10, "lng_demand_impact_intensity", "LNG 수요 영향 강도", "direct", "PowerMix", "구조적 비중 변화"),
    _mapping_row(10, "alt_energy_absorption", "타 에너지원 흡수 가능성", "direct", "PowerMix", "원전·재생E 등 흡수"),
    _mapping_row(11, "period", "기간", "indirect", None, "시간축"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "SupplyDisruption", "생산 시설 피해 시"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "LiqUtilAdjustment", "수출 시설 피해 시"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "LiqProdAdjustment", "수출 시설 피해 시"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "RegasAdjustment", "수입 시설 피해 시"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "HurricaneIntensity", "미국 액화시설 허리케인"),
    _mapping_row(11, "supply_disruption_intensity", "공급 차질 강도", "direct", None, "시설 가동률 감소율로 변환"),
    _mapping_row(17, "period", "기간", "indirect", None, "시간축"),
    _mapping_row(17, "transport_disruption", "운송 차질", "direct", "ShippingCost", "용선료·보험료 상승"),
    _mapping_row(17, "supply_disruption_intensity", "공급 차질 - 강도", "direct", "LiqUtilAdjustment", "액화시설 가동률 감소"),
    _mapping_row(17, "supply_disruption_intensity", "공급 차질 - 강도", "direct", "LiqProdAdjustment", "생산량 직접 감소"),
    _mapping_row(17, "supply_disruption_intensity", "공급 차질 - 강도", "direct", "SupplyDisruption", "upstream 생산 차질 동반 시"),
]


def _get_db_fixture_kb():
    return get_parameter_knowledge_base_from_resources(
        mapping_rows=TEST_MAPPING_ROWS,
        parameter_rows=TEST_PARAMETER_ROWS,
        basecase_dir_path=str(_default_basecase_dir()),
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
    def test_schema_ignores_removed_local_tuning_options(self) -> None:
        payload = ProposeParametersIn.model_validate(
            {
                "maxCandidates": 3,
                "maxBasecaseSampleRows": 2,
                "allowLlmFallback": True,
                "basecaseDirPath": "/tmp/basecase",
                "modelName": "custom-model",
                "unknownOption": "ignored",
            },
        )

        assert payload.model_name == "custom-model"
        assert not hasattr(payload, "max_candidates")
        assert not hasattr(payload, "max_basecase_sample_rows")
        assert not hasattr(payload, "allow_llm_fallback")
        assert not hasattr(payload, "basecase_dir_path")
        assert not hasattr(payload, "unknown_option")

    def test_proposal_request_accepts_optional_user_id(self) -> None:
        assert ProposeParametersRequest().user_id is None
        assert (
            ProposeParametersRequest.model_validate(
                {"userId": 101},
            ).user_id
            == 101
        )
        assert (
            ProposeParametersRequest.model_validate(
                {"user_id": 102},
            ).user_id
            == 102
        )

    def test_graph_registers_expected_nodes(self) -> None:
        graph = build_graph().get_graph()

        assert "load_scenario_context" in graph.nodes
        assert "select_parameter_candidates" in graph.nodes
        assert "validate_parameter_candidates" in graph.nodes
        assert "load_basecase_samples" in graph.nodes
        assert "propose_parameter_slots" in graph.nodes
        assert "filter_basecase_records_by_slots" in graph.nodes
        assert "propose_parameter_values" in graph.nodes
        assert "finalize_empty_parameter_values" in graph.nodes

    def test_scenario_brief_includes_requested_source_table_columns(self) -> None:
        brief = _scenario_brief_for_value_prompt(
            {
                "scenario_group": {
                    "title": "중동 리스크",
                    "summary": "공급 리스크 요약",
                    "description": "시나리오 그룹 상세 설명",
                    "dimension_selected": ["period", "supply_intensity"],
                },
                "scenario": {
                    "scenario_id": 100,
                    "title": "단기 차질",
                    "narrative": "차질이 1개월 내 완화되는 경로",
                    "dimension_values": {
                        "period": "1개월 이하",
                        "supply_intensity": "낮음",
                    },
                    "impact": {
                        "jkm": 1.2,
                        "ttf": -0.3,
                        "hh": 0.1,
                    },
                },
                "dimension_template": [
                    {
                        "dim_key": "period",
                        "label": "기간",
                        "required": True,
                    },
                    {
                        "dim_key": "supply_intensity",
                        "label": "공급 차질 강도",
                    },
                ],
                "event": {
                    "event_title_ko": "호르무즈 통항 재개",
                    "one_line_summary": "운송 리스크가 완화됨",
                    "key_bullets": ["합의 서명", "통항 재개"],
                    "detail_analysis": "상세 분석 본문",
                    "tags": ["geopolitics", "lng"],
                },
            },
        )

        assert brief["scenario_group"] == {
            "title": "중동 리스크",
            "summary": "공급 리스크 요약",
            "description": "시나리오 그룹 상세 설명",
            "dimension_selected": ["period", "supply_intensity"],
        }
        assert brief["scenario"] == {
            "title": "단기 차질",
            "narrative": "차질이 1개월 내 완화되는 경로",
            "dimension_values": {
                "period": "1개월 이하",
                "supply_intensity": "낮음",
            },
            "impact_jkm": 1.2,
            "impact_ttf": -0.3,
            "impact_hh": 0.1,
        }
        assert brief["dimension_template"]["template_json"][0]["dim_key"] == "period"
        assert brief["event"] == {
            "event_title": "호르무즈 통항 재개",
            "one_line_summary": "운송 리스크가 완화됨",
            "key_bullets_json": ["합의 서명", "통항 재개"],
            "detail_analysis": "상세 분석 본문",
            "tag_json": ["geopolitics", "lng"],
        }
        assert brief["selected_dimensions"] == [
            {
                "dimension_key": "period",
                "dimension_label": "기간",
                "dimension_value": "1개월 이하",
            },
            {
                "dimension_key": "supply_intensity",
                "dimension_label": "공급 차질 강도",
                "dimension_value": "낮음",
            },
        ]

    def test_scenario_brief_filters_dimension_context_when_keys_are_restricted(self) -> None:
        brief = _scenario_brief_for_value_prompt(
            {
                "scenario_group": {
                    "dimension_selected": [
                        "period",
                        "economic_intensity",
                        "demand_impact",
                    ],
                },
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": {
                        "period": "1년",
                        "economic_intensity": "경기 충격",
                        "demand_impact": "25%",
                    },
                },
                "dimension_template": [
                    {"dim_key": "period", "label": "기간"},
                    {"dim_key": "economic_intensity", "label": "강도"},
                    {"dim_key": "demand_impact", "label": "LNG 수요 영향 규모"},
                ],
            },
            allowed_dimension_keys={"period", "economic_intensity"},
        )

        assert brief["scenario_group"]["dimension_selected"] == [
            "period",
            "economic_intensity",
        ]
        assert brief["scenario"]["dimension_values"] == {
            "period": "1년",
            "economic_intensity": "경기 충격",
        }
        assert brief["selected_dimensions"] == [
            {
                "dimension_key": "period",
                "dimension_label": "기간",
                "dimension_value": "1년",
            },
            {
                "dimension_key": "economic_intensity",
                "dimension_label": "강도",
                "dimension_value": "경기 충격",
            },
        ]
        assert brief["dimension_template"]["template_json"] == [
            {"dim_key": "period", "label": "기간"},
            {"dim_key": "economic_intensity", "label": "강도"},
        ]
        assert "demand_impact" not in json.dumps(brief, ensure_ascii=False)

    def test_graph_rejects_empty_candidates(self) -> None:
        state = ModelParameterProposalState(
            scenario_id=100,
            candidate_mappings=[],
        )

        with self.assertRaises(MIBaseError) as state_error:
            _route_after_candidate_validation(state)
        assert "No model parameter mapping candidates found" in (
            state_error.exception.error_message
        )

        with self.assertRaises(MIBaseError) as dict_error:
            _route_after_candidate_validation(
                {"scenario_id": 100, "candidate_mappings": []},
            )
        assert "scenario_id=100" in dict_error.exception.error_message
        assert (
            _route_after_candidate_validation(
                {"candidate_mappings": [{"candidate_key": "c1"}]},
            )
            == "load_basecase_samples"
        )

    def test_empty_candidate_finalizer_returns_empty_adjustments(self) -> None:
        state = ModelParameterProposalState(
            scenario_id=100,
            candidate_mappings=[],
        )

        result = finalize_empty_parameter_values(state)

        assert result["parameter_adjustments"] == []
        assert "Step1/Step1.5 candidate 결과가 없어" in result["validation_warnings"][0]
        assert "Step2 selected slot" not in result["validation_warnings"][0]

    def test_main_registers_model_parameter_router(self) -> None:
        main_source = Path("main.py").read_text()

        assert "model_parameter_router" in main_source
        assert "app.include_router(" in main_source
        assert "preload_parameter_knowledge_base" not in main_source

    def test_model_parameter_endpoint_accepts_optional_request_body(self) -> None:
        route = next(
            route
            for route in model_parameter_router.routes
            if isinstance(route, APIRoute)
            and route.path == "/model-parameters/scenarios/{scenario_id}/proposals"
        )

        assert route.body_field is not None
        assert route.body_field.required is False
        assert route.response_model is ProposeParametersAcceptedOut
        assert [param.name for param in route.dependant.path_params] == ["scenario_id"]

    def test_model_parameter_sync_endpoint_accepts_optional_request_body(self) -> None:
        route = next(
            route
            for route in model_parameter_router.routes
            if isinstance(route, APIRoute)
            and route.path == "/model-parameters/scenarios/{scenario_id}/proposals/sync"
        )

        assert route.body_field is not None
        assert route.body_field.required is False
        assert [param.name for param in route.dependant.path_params] == ["scenario_id"]

    def test_llm_schema_describes_temporal_slot_values_as_integer_numbers(self) -> None:
        slot_schema = ParameterSlotAxis.model_json_schema()
        value_schema = ParameterValueCell.model_json_schema()

        assert "integer JSON number" in slot_schema["properties"]["axisValue"]["description"]
        assert "not a string" in slot_schema["properties"]["axisValue"]["description"]
        assert "integer JSON numbers" in value_schema["properties"]["coordinates"]["description"]
        assert "not strings" in value_schema["properties"]["coordinates"]["description"]

    def test_default_basecase_resources_are_packaged_with_agent(self) -> None:
        assert DEFAULT_INPUT_DIR.name == "resources"
        assert DEFAULT_INPUT_DIR.parent.name == "model_parameter_agent"
        assert "gen_model_param" not in DEFAULT_INPUT_DIR.parts
        assert DEFAULT_BASECASE_DIR.parent == DEFAULT_INPUT_DIR
        assert _default_basecase_dir().name == "basecase"

    def test_default_knowledge_base_loads_mapping_from_db(self) -> None:
        from apps.agents.model_parameter_agent.utils import parameter_mapping as mapping_module

        mapping_rows = [
            {
                "event_type_l2_id": 17,
                "dimension_key": "transport_disruption",
                "dimension_label": "운송 차질",
                "canonical_parameter_name": "ShippingCost",
                "mapping_method": "direct",
                "comment": "운송 차질은 ShippingCost에 직접 반영",
            },
        ]
        parameter_rows = [
            {
                "canonical_parameter_name": "ShippingCost",
                "parameter_name": "ShippingCost",
                "parameter_hint": "운송 비용 입력값",
                "model_file": "Trade",
                "model_sheet": "ShippingCostInput",
                "model_table": "Table1",
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
                "basecase_stop_rule": "blank_axis",
            },
        ]

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service."
                "ModelParameterService.load_parameter_mapping_resources",
                return_value=(mapping_rows, parameter_rows),
            ) as load_resources,
        ):
            kb = get_parameter_knowledge_base(
                basecase_dir_path=tmpdir,
            )
            get_parameter_knowledge_base(
                basecase_dir_path=tmpdir,
            )

        assert load_resources.call_count == 2
        assert kb.mapping_source == mapping_module.DB_MAPPING_SOURCE
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
        )

        assert not non_inputs
        assert not warnings
        assert candidates[0]["canonical_parameter_name"] == "ShippingCost"
        assert candidates[0]["model_file"] == "Trade"

    def test_dimension_mapping_query_excludes_inactive_parameter_refs(self) -> None:
        from sqlalchemy.dialects import mysql

        from apps.persistence.model_parameter.repository import (
            ModelParameterRepository,
        )

        session = Mock()
        session.execute.return_value.all.return_value = []

        ModelParameterRepository(session=session)._fetch_dimension_mapping_rules()

        stmt = session.execute.call_args.args[0]
        compiled = str(
            stmt.compile(
                dialect=mysql.dialect(),
                compile_kwargs={"literal_binds": True},
            ),
        )

        assert "tmm_mi_model_param_dimension_map.model_param_id IS NULL" in compiled
        assert "tmm_mi_model_param_m.model_param_id IS NOT NULL" in compiled
        assert "mapping_status" not in compiled

    def test_model_parameter_service_loads_context_with_parameter_mapping_resources(self) -> None:
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
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ScenarioRepository",
            ) as scenario_repository_cls,
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ScenarioGroupRepository",
            ) as group_repository_cls,
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.EventRepository",
            ) as event_repository_cls,
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as model_parameter_repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            scenario_repository_cls.return_value.fetch_model_by_id.return_value = SimpleNamespace(
                scenario_id=100,
                scenario_group_id=20,
                title="scenario",
                narrative="",
                status="READY",
                dimension_values={},
                probability_score=None,
                probability_delta=None,
                impact_jkm=None,
                impact_ttf=None,
                impact_hh=None,
                baseline_yn="N",
            )
            scenario_repository_cls.return_value.fetch_dimension_template.return_value = [
                {"dim_key": "transport_disruption"},
            ]
            group_repository_cls.return_value.fetch_by_id.return_value = SimpleNamespace(
                scenario_group_id=20,
                mi_event_id=30,
                event_type_l2_id=17,
                request_usr_id=40,
                title="group",
                summary="",
                description="",
                dimension_selected=[],
                scenario_count=1,
                status="READY",
                stage="DONE",
            )
            event_repository_cls.return_value.fetch_event_by_id.return_value = {
                "mi_event_id": 30,
            }
            event_repository_cls.return_value.fetch_event_type_by_l2_id.return_value = {
                "event_type_l2_id": 17,
            }
            model_parameter_repository_cls.return_value.fetch_parameter_mapping_resources.return_value = (
                [{"dimension_key": "transport_disruption"}],
                [{"parameter_name": "ShippingCost"}],
            )

            result = ModelParameterService().load_context(100)

        assert result["scenario"]["scenario_id"] == 100
        assert result["parameter_mapping_resources"] == {
            "mapping_rules": [{"dimension_key": "transport_disruption"}],
            "parameter_definitions": [{"parameter_name": "ShippingCost"}],
        }
        scenario_repository_cls.return_value.fetch_model_by_id.assert_called_once_with(100)
        group_repository_cls.return_value.fetch_by_id.assert_called_once_with(20)
        event_repository_cls.return_value.fetch_event_by_id.assert_called_once_with(30)
        event_repository_cls.return_value.fetch_event_type_by_l2_id.assert_called_once_with(17)
        scenario_repository_cls.return_value.fetch_dimension_template.assert_called_once_with(17)
        model_parameter_repository_cls.return_value.fetch_parameter_mapping_resources.assert_called_once_with()

    def test_model_parameter_service_loads_parameter_mapping_resources(self) -> None:
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
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.fetch_parameter_mapping_resources.return_value = (
                [{"dimension_key": "period"}],
                [{"parameter_name": "ShippingCost"}],
            )

            mapping_rules, parameter_definitions = (
                ModelParameterService().load_parameter_mapping_resources()
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
                        "canonical_parameter_name": "ShippingCost",
                        "mapping_method": "direct",
                        "comment": "운송 차질은 ShippingCost에 직접 반영",
                    },
                ],
                "parameter_definitions": [
                    {
                        "canonical_parameter_name": "ShippingCost",
                        "parameter_name": "ShippingCost",
                        "parameter_hint": "운송 비용 입력값",
                        "model_file": "Trade",
                        "model_sheet": "ShippingCostInput",
                        "model_table": "Table1",
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
                        "basecase_stop_rule": "blank_axis",
                    },
                ],
            },
        }
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.nodes."
                "ModelParameterService",
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

    def test_model_parameter_service_saves_proposal_result(self) -> None:
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
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.create_model_param_proposal.return_value = 901

            result = ModelParameterService().save_proposal_result(
                scenario_context={
                    "scenario": {"scenario_id": 100, "scenario_group_id": 20},
                    "scenario_group": {
                        "scenario_group_id": 20,
                        "mi_event_id": 30,
                    },
                    "event": {"mi_event_id": 30},
                },
                user_id=40,
                proposal_parameters=[
                    ProposalParameter(
                        parameter_name="ShippingCost",
                        model_target=ModelParameterTarget(
                            model_file="Trade",
                            model_sheet="ShippingCostInput",
                            table_name="Table1",
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
        assert saved_payload[0]["modelTarget"]["tableName"] == "Table1"
        assert (
            repository_cls.return_value.create_model_param_proposal.call_args.kwargs[
                "request_usr_id"
            ]
            == 40
        )

    def test_model_parameter_service_does_not_fallback_to_scenario_group_request_user(
        self,
    ) -> None:
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
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.create_model_param_proposal.return_value = 902

            result = ModelParameterService().save_proposal_result(
                scenario_context={
                    "scenario": {"scenario_id": 100, "scenario_group_id": 20},
                    "scenario_group": {
                        "scenario_group_id": 20,
                        "mi_event_id": 30,
                        "request_usr_id": 40,
                    },
                    "event": {"mi_event_id": 30},
                },
                proposal_parameters=[],
            )

        assert result == 902
        assert (
            repository_cls.return_value.create_model_param_proposal.call_args.kwargs[
                "request_usr_id"
            ]
            is None
        )

    def test_model_parameter_repository_sets_proposal_user_audit_fields(self) -> None:
        from apps.persistence.model_parameter.repository import ModelParameterRepository

        class FakeSession:
            def __init__(self) -> None:
                self.added = None

            def add(self, value) -> None:
                self.added = value

            def flush(self) -> None:
                self.added.model_param_proposal_id = 901

        fake_session = FakeSession()

        result = ModelParameterRepository(session=fake_session).create_model_param_proposal(
            scenario_id=100,
            scenario_group_id=20,
            mi_event_id=30,
            request_usr_id=40,
            proposal_parameters=[],
        )

        assert result == 901
        assert fake_session.added.request_usr_id == 40
        assert fake_session.added.crt_usr_logn_id == 40
        assert fake_session.added.mod_usr_logn_id == 40

    def test_model_parameter_repository_sets_processing_user_audit_fields(self) -> None:
        from apps.persistence.model_parameter.repository import ModelParameterRepository

        class FakeSession:
            def __init__(self) -> None:
                self.added = None

            def add(self, value) -> None:
                self.added = value

            def flush(self) -> None:
                self.added.model_param_proposal_id = 901

        fake_session = FakeSession()

        result = ModelParameterRepository(session=fake_session).create_processing_model_param_proposal(
            scenario_id=100,
            scenario_group_id=20,
            mi_event_id=30,
            request_usr_id=40,
        )

        assert result == 901
        assert fake_session.added.request_usr_id == 40
        assert fake_session.added.crt_usr_logn_id == 40
        assert fake_session.added.mod_usr_logn_id == 40

    def test_model_parameter_repository_sets_confirm_user_as_modifier(self) -> None:
        from apps.persistence.model_parameter.repository import ModelParameterRepository

        proposal = SimpleNamespace(
            confirmation_parameters=None,
            status="PROPOSED",
            confirmed_dtm=None,
            mod_usr_logn_id=40,
        )

        class FakeScalarResult:
            def one_or_none(self):
                return proposal

        class FakeExecuteResult:
            def scalars(self):
                return FakeScalarResult()

        fake_session = SimpleNamespace(execute=Mock(return_value=FakeExecuteResult()))

        ModelParameterRepository(session=fake_session).confirm_model_param_proposal(
            model_param_proposal_id=901,
            user_id=55,
            confirmation_parameters=[{"parameterName": "PowerMix"}],
        )

        assert proposal.confirmation_parameters == [{"parameterName": "PowerMix"}]
        assert proposal.status == "CONFIRMED"
        assert proposal.confirmed_dtm is not None
        assert proposal.mod_usr_logn_id == 55

    def test_model_parameter_service_passes_confirm_user_id_to_repository(self) -> None:
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
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.fetch_model_param_proposal.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROPOSED",
            }

            result = ModelParameterService().confirm_proposal_result(
                model_param_proposal_id=901,
                user_id=55,
                confirmation_parameters=[],
            )

        assert result == {
            "model_param_proposal_id": 901,
            "status": "CONFIRMED",
        }
        repository_cls.return_value.confirm_model_param_proposal.assert_called_once_with(
            model_param_proposal_id=901,
            user_id=55,
            confirmation_parameters=[],
        )

    def test_model_parameter_service_allows_reconfirming_confirmed_proposal(self) -> None:
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
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.fetch_model_param_proposal.return_value = {
                "model_param_proposal_id": 901,
                "status": "CONFIRMED",
            }

            result = ModelParameterService().confirm_proposal_result(
                model_param_proposal_id=901,
                user_id=56,
                confirmation_parameters=[{"parameterName": "PowerMix"}],
            )

        assert result == {
            "model_param_proposal_id": 901,
            "status": "CONFIRMED",
        }
        repository_cls.return_value.confirm_model_param_proposal.assert_called_once_with(
            model_param_proposal_id=901,
            user_id=56,
            confirmation_parameters=[{"parameterName": "PowerMix"}],
        )
        fake_session.commit.assert_called_once()
        fake_session.rollback.assert_not_called()

    def test_model_parameter_service_rejects_processing_confirmation_without_status_change(
        self,
    ) -> None:
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
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.fetch_model_param_proposal.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROCESSING",
            }

            with self.assertRaises(MIBaseError) as error:
                ModelParameterService().confirm_proposal_result(
                    model_param_proposal_id=901,
                    user_id=56,
                    confirmation_parameters=[{"parameterName": "PowerMix"}],
                )

        assert "must be PROPOSED or CONFIRMED" in error.exception.error_message
        repository_cls.return_value.confirm_model_param_proposal.assert_not_called()
        fake_session.commit.assert_not_called()
        fake_session.rollback.assert_called_once()

    def test_model_parameter_persistence_write_scope_is_proposal_only(self) -> None:
        source = Path(
            "apps/persistence/model_parameter/repository.py",
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

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_knowledge_base_profiles_resolve_mapped_basecase_sheet(self) -> None:
        kb = _get_db_fixture_kb()
        existing_profiles = [
            profile
            for profile in kb.basecase_profiles.values()
            if profile.sheet_exists
        ]

        assert existing_profiles
        assert kb.basecase_profiles["trade::shippingcostinput"].row_count > 18000
        for profile in existing_profiles:
            assert profile.workbook_path
            assert profile.sheet_name

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_match_candidates_uses_bridge_event_id_and_dimension_key(self) -> None:
        kb = _get_db_fixture_kb()
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
        )
        assert not warnings
        assert any(candidate["canonical_parameter_name"] == "ShippingCost" for candidate in candidates)
        assert all(candidate["event_type_l2_id"] == 17 for candidate in candidates)
        assert any(item["mapping_method"] == "indirect" for item in non_inputs)
        assert any(
            kb.profile_for(candidate.get("model_file"), candidate.get("model_sheet"))
            for candidate in candidates
        )

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_match_candidates_does_not_fallback_when_bridge_key_is_missing(self) -> None:
        kb = _get_db_fixture_kb()
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
        )

        assert candidates == []
        assert non_inputs == []
        assert any("DB dimension-parameter 매핑" in warning for warning in warnings)

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_bridge_mapping_preserves_multiple_routing_targets(self) -> None:
        kb = _get_db_fixture_kb()
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

    def test_disabled_db_mapping_rows_are_not_mapped(self) -> None:
        mapping_rows = [
            _mapping_row(
                17,
                "transport_disruption",
                "운송 차질",
                "direct",
                "ShippingCost",
                "disabled row",
                enabled=False,
            ),
            _mapping_row(
                999,
                "transport_disruption",
                "운송 차질",
                "direct",
                "ShippingCost",
                "active unrelated row",
            ),
        ]
        parameter_rows = [
            row
            for row in TEST_PARAMETER_ROWS
            if row["canonical_parameter_name"] == "ShippingCost"
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            kb = get_parameter_knowledge_base_from_resources(
                mapping_rows=mapping_rows,
                parameter_rows=parameter_rows,
                basecase_dir_path=temp_dir,
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
        )

        assert candidates == []
        assert non_inputs == []
        assert any("DB dimension-parameter 매핑" in warning for warning in warnings)

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_bridge_direct_row_without_target_becomes_non_input(self) -> None:
        kb = _get_db_fixture_kb()
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
        )

        assert candidates == []
        assert any("target 정보" in item["reason"] for item in non_inputs)
        assert any("parameter 후보를 찾지 못했습니다" in warning for warning in warnings)

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_basecase_records_flatten_mapped_matrix_sheet(self) -> None:
        kb = _get_db_fixture_kb()
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
        for debug_key in ("workbook_path", "row_count", "column_count"):
            assert debug_key not in first

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_basecase_records_use_matrix_time_column_spec_when_available(self) -> None:
        kb = _get_db_fixture_kb()
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

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_basecase_records_do_not_read_second_liq_prod_matrix_section(self) -> None:
        kb = _get_db_fixture_kb()
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

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_basecase_records_use_regas_first_matrix_section_only(self) -> None:
        kb = _get_db_fixture_kb()
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

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_basecase_records_use_fixed_column_spec_when_available(self) -> None:
        kb = _get_db_fixture_kb()
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

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_powermix_basecase_records_skip_ref_rows_and_start_at_real_data(self) -> None:
        kb = _get_db_fixture_kb()
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

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_degree_day_parameters_use_weather_hdd_cdd_table_with_row_filter(self) -> None:
        kb = _get_db_fixture_kb()
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

    def test_fixed_column_spec_is_defined_once_per_parameter(self) -> None:
        temperature_dimension_rows = [
            row
            for row in TEST_MAPPING_ROWS
            if row["canonical_parameter_name"] == "Temperature"
        ]
        temperature_parameter_rows = [
            row
            for row in TEST_PARAMETER_ROWS
            if row["canonical_parameter_name"] == "Temperature"
        ]

        assert all("basecase_column_roles" not in row for row in temperature_dimension_rows)
        assert len(temperature_dimension_rows) == 2
        assert len(temperature_parameter_rows) == 1
        assert (
            temperature_parameter_rows[0]["basecase_column_roles"]
            == "K:Year,L:Month,M:Country,O:Temperature"
        )

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_coal_and_gas_futures_are_split_parameters(self) -> None:
        dimension_canonicals = [
            row["canonical_parameter_name"]
            for row in TEST_MAPPING_ROWS
            if row["event_type_l2_id"] == 10
            and row["dimension_key"] == "lng_demand_impact_intensity"
        ]
        parameter_canonicals = {
            row["canonical_parameter_name"]
            for row in TEST_PARAMETER_ROWS
        }

        assert "Coal/Gas Futures Price" not in dimension_canonicals
        assert {"Coal Futures Price", "Gas Futures Price"} <= set(dimension_canonicals)
        assert "Coal/Gas Futures Price" not in parameter_canonicals
        assert {"Coal Futures Price", "Gas Futures Price"} <= parameter_canonicals

        kb = _get_db_fixture_kb()
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
        )

        assert not warnings
        assert non_inputs == []
        assert {
            candidate["canonical_parameter_name"]
            for candidate in candidates
        } >= {"Coal Futures Price", "Gas Futures Price"}

    def test_to_output_returns_key_content_only(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
            service_cls.return_value.save_proposal_result.return_value = 777
            output = to_output(
                {
                    "scenario_id": 100,
                    "user_id": 101,
                    "scenario_context": {
                        "scenario": {"scenario_id": 100, "scenario_group_id": 20},
                        "scenario_group": {"scenario_group_id": 20, "mi_event_id": 30},
                        "event": {"mi_event_id": 30},
                    },
                    "candidate_mappings": [
                        {
                            "candidate_key": "selected",
                            "parameter_name": "PowerMix",
                            "model_table": "Table2",
                        },
                        {
                            "candidate_key": "rejected",
                            "parameter_name": "ShippingCost",
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
            "tableName": "Table2",
            "valueFieldNames": ["PowerMix"],
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
        service_cls.return_value.save_proposal_result.assert_called_once()
        assert (
            service_cls.return_value.save_proposal_result.call_args.kwargs[
                "user_id"
            ]
            == 101
        )
        assert "validationWarnings" not in dumped
        assert "scenarioContext" not in dumped
        assert "candidateMappings" not in dumped
        assert "basecaseSamples" not in dumped
        assert "basecaseRecords" not in dumped
        assert "parameterSlots" not in dumped
        assert "llmUsage" not in dumped
        service_cls.return_value.save_proposal_result.assert_called_once()

    def test_to_output_uses_basecase_value_column_role_for_value_field(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
            service_cls.return_value.save_proposal_result.return_value = 778
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
                            "model_file": "Demand",
                            "model_sheet": "PowerMixAdjustment",
                            "model_table": "Table2",
                            "basecase_read_mode": "fixed_columns",
                            "basecase_column_roles": (
                                "B:Year,C:Country,F:Scenario Metric"
                            ),
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
                                    "basecase_value": 0.323,
                                    "proposed_value": 0.35,
                                    "proposed_value_rationale_ko": "DB value 컬럼명을 사용합니다.",
                                },
                            ],
                            "parameter_selection_rationale_ko": "사용자 지정 value field",
                        },
                    ],
                },
            )

        proposal_parameter = output.model_dump(by_alias=True)["data"][
            "proposalParameters"
        ][0]
        assert proposal_parameter["parameterName"] == "PowerMix"
        assert proposal_parameter["modelTarget"]["valueFieldNames"] == [
            "Scenario Metric",
        ]
        assert proposal_parameter["modelTarget"]["slotAxesFieldNames"] == [
            "Country",
            "Year",
        ]

    def test_to_output_rejects_empty_mapping_candidates(self) -> None:
        with self.assertRaises(MIBaseError) as error:
            to_output(
                {
                    "scenario_id": 100,
                    "scenario_context": {
                        "scenario": {"scenario_id": 100, "scenario_group_id": 20},
                        "scenario_group": {"scenario_group_id": 20, "mi_event_id": 30},
                        "event": {"mi_event_id": 30},
                    },
                    "candidate_mappings": [],
                    "parameter_adjustments": [],
                },
            )

        assert "No model parameter mapping candidates found" in (
            error.exception.error_message
        )

    def test_prepare_callback_rejects_empty_mapping_before_processing_row(self) -> None:
        scenario_context = {
            "scenario": {"scenario_id": 100, "scenario_group_id": 20},
            "scenario_group": {"scenario_group_id": 20, "mi_event_id": 30},
            "event": {"mi_event_id": 30},
            "parameter_mapping_resources": {
                "mapping_rules": [{"dimension_key": "unmapped"}],
                "parameter_definitions": [{"parameter_name": "ShippingCost"}],
            },
        }

        with (
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
            ) as service_cls,
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
                "get_parameter_knowledge_base_from_resources",
            ),
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
                "match_parameter_candidates",
                return_value=([], [], ["no mapped parameter"]),
            ),
        ):
            service_cls.return_value.load_context.return_value = scenario_context

            with self.assertRaises(MIBaseError) as error:
                prepare_propose_parameters_callback(100)

        assert "No model parameter mapping candidates found" in (
            error.exception.error_message
        )
        service_cls.return_value.create_processing_proposal.assert_not_called()

    def test_prepare_callback_creates_processing_row_when_mapping_exists(self) -> None:
        scenario_context = {
            "scenario": {"scenario_id": 100, "scenario_group_id": 20},
            "scenario_group": {"scenario_group_id": 20, "mi_event_id": 30},
            "event": {"mi_event_id": 30},
            "parameter_mapping_resources": {
                "mapping_rules": [{"dimension_key": "transport_disruption"}],
                "parameter_definitions": [{"parameter_name": "ShippingCost"}],
            },
        }

        with (
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
            ) as service_cls,
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
                "get_parameter_knowledge_base_from_resources",
            ),
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
                "match_parameter_candidates",
                return_value=([{"candidate_key": "c1"}], [], []),
            ),
        ):
            service_cls.return_value.load_context.return_value = scenario_context
            service_cls.return_value.create_processing_proposal.return_value = 901

            result = prepare_propose_parameters_callback(100)

        assert result == {
            "model_param_proposal_id": 901,
            "scenario_id": 100,
            "scenario_group_id": 20,
            "event_id": 30,
        }
        service_cls.return_value.create_processing_proposal.assert_called_once_with(
            scenario_context=scenario_context,
            user_id=None,
        )

    def test_prepare_callback_passes_explicit_user_id(self) -> None:
        scenario_context = {
            "scenario": {"scenario_id": 100, "scenario_group_id": 20},
            "scenario_group": {
                "scenario_group_id": 20,
                "mi_event_id": 30,
                "request_usr_id": 40,
            },
            "event": {"mi_event_id": 30},
            "parameter_mapping_resources": {
                "mapping_rules": [{"dimension_key": "transport_disruption"}],
                "parameter_definitions": [{"parameter_name": "ShippingCost"}],
            },
        }

        with (
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
            ) as service_cls,
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
                "get_parameter_knowledge_base_from_resources",
            ),
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
                "match_parameter_candidates",
                return_value=([{"candidate_key": "c1"}], [], []),
            ),
        ):
            service_cls.return_value.load_context.return_value = scenario_context
            service_cls.return_value.create_processing_proposal.return_value = 901

            result = prepare_propose_parameters_callback(
                100,
                user_id=101,
            )

        assert result["model_param_proposal_id"] == 901
        service_cls.return_value.create_processing_proposal.assert_called_once_with(
            scenario_context=scenario_context,
            user_id=101,
        )

    def test_to_output_normalizes_slot_axis_fields_for_same_parameter(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
            service_cls.return_value.save_proposal_result.return_value = 780
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
                            "candidate_key": "c1",
                            "parameter_name": "SupplyDisruption",
                            "canonical_parameter_name": "SupplyDisruption",
                            "basecase_read_mode": "fixed_columns",
                            "basecase_column_roles": "B:Year,C:Province Country,E:SupplyDisruption",
                        },
                        {
                            "candidate_key": "c2",
                            "parameter_name": "SupplyDisruption",
                            "canonical_parameter_name": "SupplyDisruption",
                            "basecase_read_mode": "fixed_columns",
                            "basecase_column_roles": "B:Year,C:Province Country,E:SupplyDisruption",
                        },
                    ],
                    "parameter_adjustments": [
                        {
                            "candidate_key": "c1",
                            "model_file": "Supply",
                            "model_sheet": "VolumeAdjustment",
                            "parameter_name": "SupplyDisruption",
                            "selected": True,
                            "slot_axes": [],
                            "value_grid": [
                                {
                                    "coordinates": {
                                        "Province": "Norway",
                                        "Year": 2026,
                                        "Month": 6,
                                    },
                                    "basecase_value": None,
                                    "proposed_value": 3,
                                    "value_selection_rationale_ko": "Norway 2026 row",
                                    "proposed_value_rationale_ko": "3% 차질",
                                },
                            ],
                            "parameter_selection_rationale_ko": "upstream 차질",
                            "confidence_overall": 0.8,
                        },
                        {
                            "candidate_key": "c2",
                            "model_file": "Supply",
                            "model_sheet": "VolumeAdjustment",
                            "parameter_name": "SupplyDisruption",
                            "selected": True,
                            "slot_axes": [],
                            "value_grid": [
                                {
                                    "coordinates": {
                                        "Province Country": "Norway",
                                        "Year": "2026",
                                    },
                                    "basecase_value": None,
                                    "proposed_value": -0.0,
                                    "value_selection_rationale_ko": "Norway 2026 duplicate row",
                                    "proposed_value_rationale_ko": "대체 공급 반영",
                                },
                                {
                                    "coordinates": {
                                        "Province Country": "Europe",
                                        "Year": 2026,
                                    },
                                    "basecase_value": None,
                                    "proposed_value": 0,
                                    "value_selection_rationale_ko": "Europe 2026 row",
                                    "proposed_value_rationale_ko": "대체 공급 반영",
                                },
                            ],
                            "parameter_selection_rationale_ko": "대체 공급 반영",
                            "confidence_overall": 0.8,
                        },
                    ],
                },
            )

        proposal = output.model_dump(by_alias=True)["data"]["proposalParameters"][0]
        assert proposal["parameterName"] == "SupplyDisruption"
        assert proposal["modelTarget"]["slotAxesFieldNames"] == [
            "Province Country",
            "Year",
        ]
        for value in proposal["values"]:
            assert "Province Country" in value
            assert "Year" in value
            assert "Province" not in value
            assert "Month" not in value
        assert proposal["values"] == [
            {
                "Province Country": "Norway",
                "Year": 2026,
                "basecaseValue": None,
                "proposedValue": 3,
                "rationale": "Norway 2026 row 3% 차질",
            },
            {
                "Province Country": "Europe",
                "Year": 2026,
                "basecaseValue": None,
                "proposedValue": 0,
                "rationale": "Europe 2026 row 대체 공급 반영",
            },
        ]

    def test_event_type_is_not_forcibly_suppressed(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
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

    def test_to_output_rejects_empty_final_proposal_parameters(self) -> None:
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
            service_cls.return_value.save_proposal_result.return_value = 779
            with self.assertRaises(MIBaseError) as error:
                to_output(
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
                            },
                            {
                                "candidate_key": "null_value_2",
                                "parameter_name": "GDP",
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
                                        "value_selection_rationale_ko": "China 2026 row",
                                        "proposed_value_rationale_ko": "정량 근거 없음",
                                    },
                                ],
                                "parameter_selection_rationale_ko": "PMI 조정 후보",
                                "confidence_overall": 0.5,
                            },
                            {
                                "candidate_key": "null_value_2",
                                "model_file": "Demand",
                                "model_sheet": "GDPPopulationAdjustment",
                                "parameter_name": "GDP",
                                "selected": True,
                                "slot_axes": [],
                                "value_grid": [
                                    {
                                        "coordinates": {"Country": "China", "Year": 2026},
                                        "basecase_value": 0.04,
                                        "proposed_value": None,
                                        "unit": "%",
                                        "value_selection_rationale_ko": "China 2026 row",
                                        "proposed_value_rationale_ko": "정량 근거 없음",
                                    },
                                ],
                                "parameter_selection_rationale_ko": "GDP 조정 후보",
                                "confidence_overall": 0.5,
                            },
                        ],
                    },
                )

        assert "No valid model parameter proposal parameters generated" in (
            error.exception.error_message
        )
        service_cls.return_value.save_proposal_result.assert_not_called()


class ModelParameterAgentLLMTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._settings_patch = patch.object(
            proposal_nodes,
            "get_settings",
            return_value=SimpleNamespace(
                llm_max_retries=1,
                model_parameter_max_parameter_slots=100,
                model_parameter_max_value_prompt_basecase_records=100,
                model_parameter_max_routing_candidates_per_dimension=2,
            ),
        )
        self._settings_patch.start()
        self.addCleanup(self._settings_patch.stop)

    async def test_llm_candidate_validation_keeps_direct_and_filters_routing_candidates(self) -> None:
        direct_candidate = {
            "candidate_key": "direct",
            "mapping_method": "direct",
            "source_dimension_id": "affected_facility_type",
            "source_dimension_label": "피해 시설 유형",
            "source_dimension_value": "수입 시설",
            "model_file": "Demand",
            "model_sheet": "PowerMixAdjustment",
            "model_table": "Table1",
            "parameter_name": "PowerMix",
            "canonical_parameter_name": "PowerMix",
            "parameter_hint": "발전 믹스 조정 입력값입니다.",
            "semantic_axes": "Country, Year",
        }
        routing_candidate = {
            "candidate_key": "routing",
            "mapping_method": "routing",
            "source_dimension_id": "affected_facility_type",
            "source_dimension_label": "피해 시설 유형",
            "source_dimension_value": "수입 시설",
            "mapping_comment": "수입 시설 피해 시",
            "model_file": "Supply",
            "model_sheet": "RegasAdjustment",
            "model_table": "Table2",
            "parameter_name": "RegasAdjustment",
            "canonical_parameter_name": "RegasAdjustment",
            "parameter_hint": "재기화 차질 조정 입력값입니다.",
        }
        candidate_response = LLMCandidateValidationResponse(
            parameter_candidate_groups=[
                ParameterCandidateGroupDecision(
                    candidate_keys=["direct"],
                    selected=False,
                ),
                ParameterCandidateGroupDecision(
                    candidate_keys=["routing"],
                    selected=True,
                ),
            ],
        )
        captured_system_contents: list[str] = []
        captured_contents: list[str] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            captured_system_contents.append(kwargs["messages"][0]["content"])
            captured_contents.append(kwargs["messages"][1]["content"])
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
        assert "candidate_validation_rationale_ko" not in result["candidate_mappings"][0]
        assert "candidate_validation_rationale_ko" not in result["candidate_mappings"][1]
        assert any(
            "direct 후보는 LLM parameter group selected=false" in warning
            for warning in result["validation_warnings"]
        )
        assert (
            "candidate_validation_tasks는 Step1.5에서 검증할 parameter별 작업 단위"
            in captured_system_contents[0]
        )
        assert (
            "parameter_hint는 해당 parameter 세팅을 위한 설명/참고사항/제약사항"
            in captured_system_contents[0]
        )
        assert (
            "mapping_comment는 해당 scenario dimension에 의해 parameter가 선택된 경우의 추가 참고사항"
            in captured_system_contents[0]
        )
        assert "scenario_brief.scenario_group의 title/summary/description/dimension_selected" in (
            captured_system_contents[0]
        )
        assert "scenario_brief.event의 event_title/one_line_summary/key_bullets_json/detail_analysis/tag_json" in (
            captured_system_contents[0]
        )
        assert (
            "특정 dimension에 routing parameter 후보가 하나 이상 있으면"
            in captured_system_contents[0]
        )
        payload = json.loads(captured_contents[0].split("\n", 1)[1])
        assert "scenario_context" not in payload
        assert "dimension_template" not in json.dumps(payload, ensure_ascii=False)
        assert "candidate_mappings" not in payload
        assert "parameter_candidate_groups" not in payload
        assert "candidate_validation_tasks" in payload
        assert "model_file" not in json.dumps(payload, ensure_ascii=False)
        assert "model_sheet" not in json.dumps(payload, ensure_ascii=False)
        assert "model_table" not in json.dumps(payload, ensure_ascii=False)
        assert payload["candidate_validation_tasks"][0] == {
            "parameter": {
                "parameter_name": "PowerMix",
                "parameter_hint": "발전 믹스 조정 입력값입니다.",
                "semantic_axes": "Country, Year",
            },
            "candidate_keys": ["direct"],
            "selection_dimensions": [
                {
                    "dimension_key": "affected_facility_type",
                    "dimension_label": "피해 시설 유형",
                    "dimension_value": "수입 시설",
                    "mapping_method": "direct",
                },
            ],
        }
        assert payload["candidate_validation_tasks"][1] == {
            "parameter": {
                "parameter_name": "RegasAdjustment",
                "parameter_hint": "재기화 차질 조정 입력값입니다.",
            },
            "candidate_keys": ["routing"],
            "selection_dimensions": [
                {
                    "dimension_key": "affected_facility_type",
                    "dimension_label": "피해 시설 유형",
                    "dimension_value": "수입 시설",
                    "mapping_method": "routing",
                    "mapping_comment": "수입 시설 피해 시",
                },
            ],
        }

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
            parameter_candidate_groups=[
                ParameterCandidateGroupDecision(
                    candidate_keys=["c1"],
                    selected=True,
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

    async def test_llm_candidate_validation_group_merges_same_parameter_candidates(self) -> None:
        candidates = [
            {
                "candidate_key": "utilization",
                "event_type_l2_id": 1,
                "dimension_key": "utilization_change_amount",
                "source_dimension_id": "utilization_change_amount",
                "source_dimension_label": "가동률 변화 폭",
                "source_dimension_value": "<5%",
                "mapping_method": "direct",
                "mapping_comment": "차질 규모",
                "model_file": "Supply",
                "model_sheet": "VolumeAdjustment",
                "parameter_name": "SupplyDisruption",
                "canonical_parameter_name": "SupplyDisruption",
            },
            {
                "candidate_key": "alternative",
                "event_type_l2_id": 1,
                "dimension_key": "alt_gas_supply_availability",
                "source_dimension_id": "alt_gas_supply_availability",
                "source_dimension_label": "대체 가스 공급 가능성",
                "source_dimension_value": "100%",
                "mapping_method": "direct",
                "mapping_comment": "대체 공급 완화율",
                "model_file": "Supply",
                "model_sheet": "VolumeAdjustment",
                "parameter_name": "SupplyDisruption",
                "canonical_parameter_name": "SupplyDisruption",
            },
        ]
        candidate_response = LLMCandidateValidationResponse(
            parameter_candidate_groups=[
                ParameterCandidateGroupDecision(
                    candidate_keys=["utilization", "alternative"],
                    selected=True,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=283,
            scenario_context={"scenario": {"scenario_id": 283}},
            candidate_mappings=candidates,
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await validate_parameter_candidates(state)

        assert len(result["candidate_mappings"]) == 1
        merged = result["candidate_mappings"][0]
        assert merged["candidate_key"] == "parameter|1|supply|volumeadjustment|supplydisruption"
        assert merged["merged_candidate_keys"] == ["utilization", "alternative"]
        assert [item["dimension_key"] for item in merged["source_dimensions"]] == [
            "utilization_change_amount",
            "alt_gas_supply_availability",
        ]
        assert "candidate_validation_rationale_ko" not in merged

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
            parameter_candidate_groups=[
                ParameterCandidateGroupDecision(
                    candidate_keys=["c1"],
                    selected=True,
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
            "basecase_read_mode": "matrix_time_columns",
            "basecase_column_roles": "B:Country,C:LNG Plant,D:LNG Plant Train",
        }
        candidate_response = LLMCandidateValidationResponse(
            parameter_candidate_groups=[
                ParameterCandidateGroupDecision(
                    candidate_keys=[liq_candidate["candidate_key"]],
                    selected=True,
                ),
                ParameterCandidateGroupDecision(
                    candidate_keys=[supply_candidate["candidate_key"]],
                    selected=False,
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
            "model_table": "Table1",
            "parameter_name": "ShippingCost",
            "canonical_parameter_name": "ShippingCost",
            "parameter_hint": "운송 차질 시 비용 입력값을 조정합니다.",
        }
        omitted_candidate = {
            "candidate_key": "c2",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "model_table": "Table1",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
            "parameter_hint": "Upstream 공급 차질량을 조정합니다.",
        }
        slot_response = LLMSlotProposalResponse(
            parameter_slots=[
                LLMSlotProposal(
                    candidate_key="c1",
                    selected=True,
                    slot_axes=[
                        LLMSlotAxis(
                            axis_name="Year",
                            axis_value=2026,
                        ),
                    ],
                    rationale_ko="운송 차질이 높아 ShippingCost slot 조정이 필요합니다.",
                ),
            ],
        )
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                LLMValueAdjustment(
                    candidate_key="c1",
                    value_grid=[
                        LLMValueCell(
                            coordinates={"Year": 2026},
                            proposed_value=1.2,
                            rationale_ko=(
                                "2026년 ShippingCost basecase record를 선택했고, "
                                "운송 차질 scenario dimension을 반영해 최종 입력값을 1.2로 산정했습니다."
                            ),
                            basecase_reference_ids=["ref1"],
                        ),
                    ],
                    rationale_ko="운송 차질이 높아 ShippingCost 조정이 필요합니다.",
                ),
            ],
        )
        requested_schemas: list[str] = []
        captured_value_system_contents: list[str] = []
        captured_value_contents: list[str] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            output_schema = kwargs["output_schema"]
            requested_schemas.append(output_schema.__name__)
            if output_schema is LLMSlotProposalResponse:
                return SimpleNamespace(result=slot_response, usage=None)
            if output_schema is LLMValueProposalResponse:
                captured_value_system_contents.append(kwargs["messages"][0]["content"])
                captured_value_contents.append(kwargs["messages"][1]["content"])
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
        value_payload = json.loads(captured_value_contents[0].split("\n", 1)[1])
        assert "basecase_records" not in value_payload
        assert "candidate_mappings" not in value_payload
        assert "parameter_candidate_groups" not in value_payload
        assert "parameter_slots" not in value_payload
        assert "basecase_value_groups" not in value_payload
        assert "basecase_value_groups" in captured_value_system_contents[0]
        task = value_payload["parameter_value_tasks"][0]
        assert task["parameter"] == {
            "candidate_key": "c1",
            "parameter_name": "ShippingCost",
            "parameter_hint": "운송 차질 시 비용 입력값을 조정합니다.",
        }
        assert "model_file" not in task
        assert "model_sheet" not in task
        assert "model_table" not in json.dumps(value_payload, ensure_ascii=False)
        assert task["basecase_value_groups"] == [
            {
                "value_name": None,
                "fixed_axes": {},
                "variable_axis_names": ["Year"],
                "cells": [
                    {
                        "reference_id": "ref1",
                        "axes": {"Year": 2026},
                        "basecase_value": 1.0,
                    },
                ],
            },
        ]
        assert adjustment["model_file"] == "Trade"
        assert adjustment["model_sheet"] == "ShippingCostInput"
        assert adjustment["parameter_name"] == "ShippingCost"
        assert adjustment["slot_axes"][0]["axis_name"] == "Year"
        assert adjustment["parameter_selection_rationale_ko"].startswith("운송 차질")
        assert adjustment["value_grid"][0]["basecase_value"] == 1.0
        assert adjustment["value_grid"][0]["basecase_reference_ids"] == ["ref1"]
        assert "2026년 ShippingCost basecase record" in adjustment["value_grid"][0]["rationale_ko"]
        assert "value_selection_rationale_ko" not in adjustment["value_grid"][0]
        assert "proposed_value_rationale_ko" not in adjustment["value_grid"][0]
        patched = result["parameter_adjustments"][1]
        assert patched["candidate_key"] == "c2"
        assert patched["selected"] is False
        assert "needs_user_review" not in patched
        assert "누락" in patched["parameter_selection_rationale_ko"]

    async def test_slot_prompt_uses_time_values_and_non_time_hierarchy(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Supply",
            "model_sheet": "LiqUtilAdjustment",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
            "basecase_read_mode": "matrix_time_columns",
            "basecase_column_roles": "B:Country,C:LNG Plant,D:LNG Plant Train",
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
                LLMSlotProposal(
                    candidate_key="c1",
                    selected=True,
                    slot_axes=[
                        LLMSlotAxis(
                            axis_name="Plant",
                            axis_value="Plant-42",
                        ),
                    ],
                    rationale_ko="설비 차질 event를 반영했습니다.",
                ),
            ],
        )
        captured_contents: list[str] = []
        captured_system_contents: list[str] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMSlotProposalResponse
            captured_system_contents.append(kwargs["messages"][0]["content"])
            captured_contents.append(kwargs["messages"][1]["content"])
            return SimpleNamespace(result=slot_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate],
            non_input_items=[
                {
                    "source_dimension_id": "alternative_supply_route",
                    "source_dimension_label": "대체 공급 경로",
                    "source_dimension_value": "미국 Gulf Coast LNG",
                    "mapping_method": "indirect",
                    "reason": "slot 판단 보조 정보",
                },
            ],
            basecase_records=records,
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_slots(state)

        assert result["parameter_slots"][0]["candidate_key"] == "c1"
        assert captured_contents
        assert captured_system_contents
        assert "basecase_slot_options는 충분한 후보 pool" in captured_system_contents[0]
        assert "axis_values에는 Year/Month/Period 같은 시간축 후보 값만" in captured_system_contents[0]
        assert "slot_hierarchy에는 시간축이 아닌 축들의 현재 Base Case 유효 path" in captured_system_contents[0]
        assert "slot 수를 줄이기 위해 누락하지 말고 모두 포함" in captured_system_contents[0]
        assert "두 조건 중 어느 것도 확인되지 않으면 basecase에 있더라도 포함하지 마십시오" in captured_system_contents[0]
        assert "단순 전수 열거하지는 마십시오" in captured_system_contents[0]
        assert "Cartesian product를 자동 전개하지 말고" in captured_system_contents[0]
        assert "서로 다른 path의 Country/Plant/Train/Region/Contract 같은 값을 섞어" in captured_system_contents[0]
        assert '"타 공급국", "대체 공급", "인접 공급국"' in captured_system_contents[0]
        assert "slot_hierarchy leaf path" in captured_system_contents[0]
        assert "Life Cycle Category/Nameplate Capacity 같은 path 속성" in captured_system_contents[0]
        assert "선택한 leaf path의 모든 축 값을 slot_axes에 포함" in captured_system_contents[0]
        assert "해당 월에 대응되는 Period도 slot_axes에 포함" in captured_system_contents[0]
        assert "axis_combinations" not in captured_system_contents[0]
        assert "기간 길이를 명시하면" in captured_system_contents[0]
        assert "기간 밖의 future year" in captured_system_contents[0]
        assert "axis_value는 반드시 JSON number integer" in captured_system_contents[0]
        assert '"2026" 같은 문자열은 금지' in captured_system_contents[0]
        assert "mapping_method=indirect dimension만 포함" in captured_system_contents[0]
        assert "parameter_hint는 해당 parameter 세팅을 위한 설명/참고사항/제약사항" in captured_system_contents[0]
        assert "mapping_comment는 해당 scenario dimension에 의해 parameter가 선택된 경우의 추가 참고사항" in captured_system_contents[0]
        assert "scenario_brief.scenario_group은 그룹 범위와 dimension_selected" in captured_system_contents[0]
        assert "slot으로 옮길 수 있는 실제 국가, 시설, 항로, 기간, 계약" in captured_system_contents[0]
        payload = json.loads(captured_contents[0].split("\n", 1)[1])
        assert "basecase_records" not in payload
        assert "basecase_record_summaries" not in payload
        assert "candidate_mappings" not in payload
        assert "parameter_candidate_groups" not in payload
        assert "supporting_dimensions" not in payload
        assert "basecase_slot_options" not in payload
        assert payload["scenario_brief"] == {"scenario_id": 100}
        task = payload["parameter_slot_tasks"][0]
        assert "selection_dimensions" not in task
        assert task["supporting_dimensions"] == [
            {
                "dimension_key": "alternative_supply_route",
                "dimension_label": "대체 공급 경로",
                "dimension_value": "미국 Gulf Coast LNG",
                "mapping_method": "indirect",
                "usage_policy": "common_context_only",
                "reason": "slot 판단 보조 정보",
            },
        ]
        assert task["parameter"] == {
            "candidate_key": "c1",
            "parameter_name": "LiqUtilAdjustment",
            "allowed_slot_axes_field_names": [
                "Country",
                "LNG Plant",
                "LNG Plant Train",
                "Year",
                "Month",
                "Period",
            ],
        }
        assert "model_file" not in json.dumps(payload, ensure_ascii=False)
        assert "model_sheet" not in json.dumps(payload, ensure_ascii=False)
        assert "model_table" not in json.dumps(payload, ensure_ascii=False)
        assert task["basecase_slot_options"] == [
            {
                "axis_names": ["Plant", "Year"],
                "axis_values": {
                    "Year": [2026, 2027],
                },
                "slot_hierarchy_axes": ["Plant"],
                "slot_hierarchy": ["Cameron", "Sabine"],
            },
        ]
        assert "cameron-2026-a" not in captured_contents[0]
        assert "sabine-2027" not in captured_contents[0]
        assert "axis_combinations" not in captured_contents[0]

    def test_basecase_slot_options_dedupes_time_values_and_non_time_hierarchy(self) -> None:
        records = [
            {
                "candidate_key": "c1",
                "axes": {"Country": "Germany", "Year": 2026},
            },
            {
                "candidate_key": "c1",
                "axes": {"Country": "Germany", "Year": 2026},
            },
            {
                "candidate_key": "c1",
                "axes": {"Country": "France", "Year": 2026},
            },
            {
                "candidate_key": "c1",
                "axes": {"Country": "Italy", "Year": 2027},
            },
        ]

        options = _build_basecase_slot_options(records)

        assert options == [
            {
                "candidate_key": "c1",
                "axis_names": ["Country", "Year"],
                "axis_values": {
                    "Year": [2026, 2027],
                },
                "slot_hierarchy_axes": ["Country"],
                "slot_hierarchy": ["France", "Germany", "Italy"],
            },
        ]

    def test_basecase_slot_options_preserves_non_time_hierarchy_paths(self) -> None:
        records = [
            {
                "candidate_key": "c1",
                "axes": {
                    "Country": "Russia",
                    "LNG Plant": "Yamal LNG",
                    "LNG Plant Train": "Yamal LNG T1",
                    "Year": 2026,
                },
            },
            {
                "candidate_key": "c1",
                "axes": {
                    "Country": "Russia",
                    "LNG Plant": "Yamal LNG",
                    "LNG Plant Train": "Yamal LNG T2",
                    "Year": 2026,
                },
            },
            {
                "candidate_key": "c1",
                "axes": {
                    "Country": "Norway",
                    "LNG Plant": "Snohvit LNG",
                    "LNG Plant Train": "Snohvit LNG T1",
                    "Year": 2026,
                },
            },
        ]

        options = _build_basecase_slot_options(records)

        assert options == [
            {
                "candidate_key": "c1",
                "axis_names": [
                    "Country",
                    "LNG Plant",
                    "LNG Plant Train",
                    "Year",
                ],
                "axis_values": {"Year": [2026]},
                "slot_hierarchy_axes": [
                    "Country",
                    "LNG Plant",
                    "LNG Plant Train",
                ],
                "slot_hierarchy": [
                    ["Norway", [["Snohvit LNG", ["Snohvit LNG T1"]]]],
                    [
                        "Russia",
                        [
                            [
                                "Yamal LNG",
                                ["Yamal LNG T1", "Yamal LNG T2"],
                            ],
                        ],
                    ],
                ],
            },
        ]

    def test_basecase_value_groups_compress_fixed_axes_and_keep_value_cells(self) -> None:
        records = [
            {
                "candidate_key": "c1",
                "reference_id": "r1",
                "axes": {
                    "Country": "Russia",
                    "LNG Plant": "Yamal LNG",
                    "Year": 2026,
                    "Month": 7,
                    "Period": 103,
                },
                "value_name": "LiqUtilAdjustment",
                "value": 0.45,
                "unit": "%",
            },
            {
                "candidate_key": "c1",
                "reference_id": "r2",
                "axes": {
                    "Country": "Russia",
                    "LNG Plant": "Yamal LNG",
                    "Year": 2026,
                    "Month": 8,
                    "Period": 104,
                },
                "value_name": "LiqUtilAdjustment",
                "value": 0.5,
                "unit": "%",
            },
            {
                "candidate_key": "c1",
                "reference_id": "r3",
                "axes": {
                    "Country": "Norway",
                    "LNG Plant": "Snohvit LNG",
                    "Year": 2026,
                    "Month": 7,
                    "Period": 103,
                },
                "value_name": "LiqUtilAdjustment",
                "value": 0.7,
                "unit": "%",
            },
        ]

        groups = _build_basecase_value_groups(records)

        assert groups == [
            {
                "candidate_key": "c1",
                "value_name": "LiqUtilAdjustment",
                "fixed_axes": {
                    "Country": "Russia",
                    "LNG Plant": "Yamal LNG",
                },
                "variable_axis_names": ["Year", "Month", "Period"],
                "cells": [
                    {
                        "reference_id": "r1",
                        "axes": {"Year": 2026, "Month": 7, "Period": 103},
                        "basecase_value": 0.45,
                    },
                    {
                        "reference_id": "r2",
                        "axes": {"Year": 2026, "Month": 8, "Period": 104},
                        "basecase_value": 0.5,
                    },
                ],
            },
            {
                "candidate_key": "c1",
                "value_name": "LiqUtilAdjustment",
                "fixed_axes": {
                    "Country": "Norway",
                    "LNG Plant": "Snohvit LNG",
                },
                "variable_axis_names": ["Year", "Month", "Period"],
                "cells": [
                    {
                        "reference_id": "r3",
                        "axes": {"Year": 2026, "Month": 7, "Period": 103},
                        "basecase_value": 0.7,
                    },
                ],
            },
        ]

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

    def test_basecase_records_under_limit_are_not_filtered_for_value_prompt(self) -> None:
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
            "sabine-2026",
            "other-2026",
        ]

    def test_basecase_records_without_selected_slots_are_filtered_out(self) -> None:
        records = [
            {
                "candidate_key": "c1",
                "reference_id": "norway-2026",
                "axes": {"Country": "Norway", "Year": 2026},
                "value": 1.0,
            },
            {
                "candidate_key": "c1",
                "reference_id": "us-2026",
                "axes": {"Country": "United States", "Year": 2026},
                "value": 2.0,
            },
        ]
        state = ModelParameterProposalState(
            scenario_id=100,
            basecase_records=records,
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": False,
                    "slot_axes": [
                        {"axis_name": "Country", "axis_value": "Norway"},
                    ],
                },
            ],
        )

        result = filter_basecase_records_by_slots(state)

        assert result["basecase_records"] == []

    def test_large_basecase_records_prioritize_deeper_prefix_matches(self) -> None:
        records = [
            {
                "candidate_key": "c1",
                "reference_id": "month-only-first",
                "axes": {"Country": "China", "Year": 2025, "Month": 8},
                "value": 10,
            },
            {
                "candidate_key": "c1",
                "reference_id": "full-1",
                "axes": {"Country": "Japan", "Year": 2026, "Month": 8},
                "value": 11,
            },
            {
                "candidate_key": "c1",
                "reference_id": "country-1",
                "axes": {"Country": "Japan", "Year": 2025, "Month": 1},
                "value": 12,
            },
            {
                "candidate_key": "c1",
                "reference_id": "country-year-late",
                "axes": {"Country": "Japan", "Year": 2026, "Month": 9},
                "value": 12.5,
            },
            {
                "candidate_key": "c1",
                "reference_id": "year-1",
                "axes": {"Country": "Korea", "Year": 2026, "Month": 3},
                "value": 13,
            },
            {
                "candidate_key": "c1",
                "reference_id": "full-2",
                "axes": {"Country": "Japan", "Year": 2026, "Month": 8},
                "value": 14,
            },
            {
                "candidate_key": "c1",
                "reference_id": "country-2",
                "axes": {"Country": "Japan", "Year": 2027, "Month": 2},
                "value": 15,
            },
            {
                "candidate_key": "c2",
                "reference_id": "other-candidate-full",
                "axes": {"Country": "Japan", "Year": 2026, "Month": 8},
                "value": 16,
            },
            {
                "candidate_key": "c1",
                "reference_id": "unrelated",
                "axes": {"Country": "China", "Year": 2025, "Month": 9},
                "value": 17,
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
                        {"axis_name": "Country", "axis_value": "Japan"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 8},
                    ],
                },
            ],
        )

        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.nodes.get_settings",
            return_value=SimpleNamespace(model_parameter_max_value_prompt_basecase_records=5),
        ):
            result = filter_basecase_records_by_slots(state)

        assert [record["reference_id"] for record in result["basecase_records"]] == [
            "full-1",
            "full-2",
            "country-year-late",
            "country-1",
            "country-2",
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
        assert "needs_user_review" not in slot
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
        assert "needs_user_review" not in adjustment
        assert any("coordinates에 모호한 값" in warning for warning in result["validation_warnings"])

    async def test_value_prompt_includes_slot_axis_contract(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "source_dimension_id": "utilization_change_amount",
            "source_dimension_label": "가동률 변화 폭",
            "source_dimension_value": "<5%",
            "mapping_method": "direct",
            "mapping_comment": "차질 규모",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
            "basecase_read_mode": "fixed_columns",
            "basecase_column_roles": "B:Year,C:Province Country,E:SupplyDisruption",
        }
        sibling_candidate = {
            "candidate_key": "c2",
            "source_dimension_id": "alt_gas_supply_availability",
            "source_dimension_label": "대체 가스 공급 가능성",
            "source_dimension_value": "100%",
            "mapping_method": "direct",
            "mapping_comment": "대체 공급 완화율",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
            "basecase_read_mode": "fixed_columns",
            "basecase_column_roles": "B:Year,C:Province Country,E:SupplyDisruption",
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
                        ),
                        ParameterSlotAxis(axis_name="Year", axis_value="2026"),
                    ],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={
                                "Province Country": "Norway",
                                "Year": 2026,
                            },
                            basecase_value=None,
                            proposed_value=3,
                            value_selection_rationale_ko="Norway 2026 row",
                            proposed_value_rationale_ko="3% 차질",
                        ),
                    ],
                    parameter_selection_rationale_ko="공급 차질 조정",
                    confidence_overall=0.8,
                ),
            ],
        )
        captured_contents: list[str] = []
        captured_system_contents: list[str] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            captured_system_contents.append(kwargs["messages"][0]["content"])
            captured_contents.append(kwargs["messages"][1]["content"])
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=[candidate, sibling_candidate],
            non_input_items=[
                {
                    "source_dimension_id": "alternative_supply_route",
                    "source_dimension_label": "대체 공급 경로",
                    "source_dimension_value": "미국 Gulf Coast LNG",
                    "mapping_method": "indirect",
                    "reason": "value 산정 보조 정보",
                },
                {
                    "source_dimension_id": "demand_impact",
                    "source_dimension_label": "LNG 수요 영향 규모",
                    "source_dimension_value": "25%",
                    "mapping_method": "na",
                    "reason": "na 정보는 value 산정에서 제외되어야 합니다.",
                },
            ],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {
                            "axis_name": "Province Country",
                            "axis_value": "Norway",
                        },
                        {"axis_name": "Year", "axis_value": 2026},
                    ],
                },
            ],
            basecase_records=[],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            await propose_parameter_values(state)

        assert captured_system_contents
        assert (
            "value_grid.coordinates의 Year, Month, Period 값은 반드시 JSON number integer"
            in captured_system_contents[0]
        )
        assert (
            "slot_axes.axis_name이 Year, Month, Period 중 하나이면 axis_value도 반드시 JSON number integer"
            in captured_system_contents[0]
        )
        assert (
            "Step3 value 산정은 기존과 같이 scenario/event/dimension, Step2 slot 축"
            in captured_system_contents[0]
        )
        assert (
            "parameter_hint는 해당 parameter 세팅을 위한 설명/참고사항/제약사항"
            in captured_system_contents[0]
        )
        assert (
            "mapping_comment는 해당 scenario dimension에 의해 parameter가 선택된 경우의 추가 참고사항"
            in captured_system_contents[0]
        )
        assert (
            "parameter-level 근거는 값 산정 상세가 아니라 parameter 선정 근거와 값 제안 구조 요약"
            in captured_system_contents[0]
        )
        assert (
            "scenario dimension이 이 parameter와 연결되는 관계를 먼저"
            in captured_system_contents[0]
        )
        assert (
            "Step3는 slot을 평가, 선택, 변경하거나 새 slot을 만들지 않습니다"
            in captured_system_contents[0]
        )
        assert (
            "selected_slots가 1개 이상 있는 parameter_value_task는 모든 selected_slots"
            in captured_system_contents[0]
        )
        assert (
            "각 selected_slot에 대해 basecase와 같은 형식의"
            in captured_system_contents[0]
        )
        assert "보수적인 최종 입력값을 산정" in captured_system_contents[0]
        assert (
            "scenario/event/dimension value의 방향·강도·기간에 따라 그 기준값을 높이거나 낮춰"
            in captured_system_contents[0]
        )
        assert (
            "basecase 부재를 0으로 해석하지 마십시오"
            in captured_system_contents[0]
        )
        assert (
            "단위·스케일·소수 자리·형식 확인용으로만 사용"
            in captured_system_contents[0]
        )
        assert (
            "수치 수준(level) 기준값으로 삼지 마십시오"
            in captured_system_contents[0]
        )
        assert (
            "개별 slot/설비/국가/월/record명, basecase_value, proposed_value"
            in captured_system_contents[0]
        )
        assert (
            "해당 요청 slot 좌표와 참조 record를 해석한 기준"
            in captured_system_contents[0]
        )
        assert "parameter_value_tasks는 Step3에서 값을 산정해야 하는 parameter별 작업 단위" in captured_system_contents[0]
        assert "supporting_dimensions의 indirect 정보도 usage_policy에 맞는 value 방향" in captured_system_contents[0]
        assert "event는 현재 확인된 사건/사실관계" in captured_system_contents[0]
        assert "각 scenario는 같은 event/scenario_group 아래에서 앞으로 전개될 수 있는 개별 미래 케이스" in captured_system_contents[0]
        assert "최종 방향, 강도, 기간, 대상은 해당 scenario의 narrative와 필터링된 dimension_values를 우선 기준" in captured_system_contents[0]
        assert "scenario_brief.scenario_group은 그룹 수준의 범위와 dimension_selected" in captured_system_contents[0]
        assert "실제 사건의 강도, 기간, 영향 경로, 완화/대체 공급 근거" in captured_system_contents[0]
        payload = json.loads(captured_contents[0].split("\n", 1)[1])
        assert "scenario_context" not in payload
        assert "dimension_template" not in json.dumps(payload, ensure_ascii=False)
        assert "candidate_mappings" not in payload
        assert "parameter_candidate_groups" not in payload
        assert "parameter_slots" not in payload
        assert "basecase_value_groups" not in payload
        assert payload["scenario_brief"] == {"scenario_id": 100}
        assert payload["parameter_value_tasks"][0]["parameter"] == {
            "candidate_key": "c1",
            "parameter_name": "SupplyDisruption",
            "allowed_slot_axes_field_names": [
                "Year",
                "Province Country",
            ],
        }
        assert payload["parameter_value_tasks"][0]["selection_dimensions"] == [
            {
                "dimension_key": "utilization_change_amount",
                "dimension_label": "가동률 변화 폭",
                "dimension_value": "<5%",
                "mapping_method": "direct",
                "mapping_comment": "차질 규모",
            },
        ]
        assert payload["parameter_value_tasks"][0]["supporting_dimensions"] == [
            {
                "dimension_key": "alternative_supply_route",
                "dimension_label": "대체 공급 경로",
                "dimension_value": "미국 Gulf Coast LNG",
                "mapping_method": "indirect",
                "usage_policy": "common_context_only",
                "reason": "value 산정 보조 정보",
            },
        ]
        assert "demand_impact" not in json.dumps(payload, ensure_ascii=False)
        assert payload["parameter_value_tasks"][0]["selected_slot_axes_field_names"] == [
            "Province Country",
            "Year",
        ]
        assert payload["parameter_value_tasks"][0]["selected_slots"] == [
            {
                "slot_axes": [
                    {
                        "axis_name": "Province Country",
                        "axis_value": "Norway",
                    },
                    {"axis_name": "Year", "axis_value": 2026},
                ],
            },
        ]
        assert payload["parameter_value_tasks"][0].get("model_file") is None
        assert payload["parameter_value_tasks"][0].get("model_sheet") is None

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

    async def test_llm_value_sanitizer_keeps_values_for_all_requested_slots(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Demand",
            "model_sheet": "CoalGasAdjustment",
            "parameter_name": "Gas Futures Price",
            "canonical_parameter_name": "Gas Futures Price",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Demand",
                    model_sheet="CoalGasAdjustment",
                    parameter_name="Gas Futures Price",
                    selected=True,
                    slot_axes=[],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={
                                "Region": "Asia",
                                "Year": 2026,
                                "Month": 7,
                            },
                            basecase_value=None,
                            proposed_value=0.1,
                            unit="USD/mmbtu",
                            value_selection_rationale_ko=(
                                "선택된 네 개 slot 중 가장 이른 Asia 2026년 7월 좌표입니다."
                            ),
                            proposed_value_rationale_ko=(
                                "정량 근거가 약해 보수적인 최종 입력값을 적용했습니다."
                            ),
                        ),
                        ParameterValueCell(
                            coordinates={
                                "Region": "Asia",
                                "Year": 2026,
                                "Month": 8,
                            },
                            basecase_value=None,
                            proposed_value=0.08,
                            unit="USD/mmbtu",
                            value_selection_rationale_ko="Asia 2026년 8월 요청 slot입니다.",
                            proposed_value_rationale_ko=(
                                "정량 근거가 약해 보수적인 최종 입력값을 적용했습니다."
                            ),
                        ),
                        ParameterValueCell(
                            coordinates={
                                "Region": "Europe",
                                "Year": 2026,
                                "Month": 7,
                            },
                            basecase_value=None,
                            proposed_value=0.07,
                            unit="USD/mmbtu",
                            value_selection_rationale_ko="Europe 2026년 7월 요청 slot입니다.",
                            proposed_value_rationale_ko=(
                                "정량 근거가 약해 보수적인 최종 입력값을 적용했습니다."
                            ),
                        ),
                        ParameterValueCell(
                            coordinates={
                                "Region": "Europe",
                                "Year": 2026,
                                "Month": 8,
                            },
                            basecase_value=None,
                            proposed_value=0.06,
                            unit="USD/mmbtu",
                            value_selection_rationale_ko="Europe 2026년 8월 요청 slot입니다.",
                            proposed_value_rationale_ko=(
                                "정량 근거가 약해 보수적인 최종 입력값을 적용했습니다."
                            ),
                        ),
                    ],
                    parameter_selection_rationale_ko=(
                        "운송 규제 영향이 가스 가격 변수와 연결됩니다."
                    ),
                    confidence_overall=0.5,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=281,
            scenario_context={"scenario": {"scenario_id": 281}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Asia"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 7},
                    ],
                },
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Asia"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 8},
                    ],
                },
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Europe"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 7},
                    ],
                },
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Europe"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 8},
                    ],
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
        assert len(adjustment["value_grid"]) == 4
        assert [cell["coordinates"] for cell in adjustment["value_grid"]] == [
            {
                "Region": "Asia",
                "Year": 2026,
                "Month": 7,
            },
            {
                "Region": "Asia",
                "Year": 2026,
                "Month": 8,
            },
            {
                "Region": "Europe",
                "Year": 2026,
                "Month": 7,
            },
            {
                "Region": "Europe",
                "Year": 2026,
                "Month": 8,
            },
        ]
        assert [cell["proposed_value"] for cell in adjustment["value_grid"]] == [
            0.1,
            0.08,
            0.07,
            0.06,
        ]
        assert not any("요청 selected_slot 좌표가 누락" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_rejects_cell_missing_requested_slot_axis(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Demand",
            "model_sheet": "CoalGasAdjustment",
            "parameter_name": "Gas Futures Price",
            "canonical_parameter_name": "Gas Futures Price",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Demand",
                    model_sheet="CoalGasAdjustment",
                    parameter_name="Gas Futures Price",
                    selected=True,
                    slot_axes=[],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={
                                "Region": "Asia",
                                "Year": 2026,
                            },
                            basecase_value=None,
                            proposed_value=0.1,
                            unit="USD/mmbtu",
                            value_selection_rationale_ko="Month 좌표가 누락된 응답입니다.",
                            proposed_value_rationale_ko=(
                                "정량 근거가 약해 보수적인 최종 입력값을 적용했습니다."
                            ),
                        ),
                    ],
                    parameter_selection_rationale_ko=(
                        "운송 규제 영향이 가스 가격 변수와 연결됩니다."
                    ),
                    confidence_overall=0.5,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=281,
            scenario_context={"scenario": {"scenario_id": 281}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Asia"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 7},
                    ],
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
        assert any("요청 slot axis 누락: Month" in warning for warning in result["validation_warnings"])
        assert any("요청 selected_slot 좌표가 누락" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_rejects_coordinates_outside_requested_slots(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Demand",
            "model_sheet": "CoalGasAdjustment",
            "parameter_name": "Gas Futures Price",
            "canonical_parameter_name": "Gas Futures Price",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Demand",
                    model_sheet="CoalGasAdjustment",
                    parameter_name="Gas Futures Price",
                    selected=True,
                    slot_axes=[],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={
                                "Region": "Asia",
                                "Year": 2026,
                                "Month": 9,
                            },
                            basecase_value=None,
                            proposed_value=0.1,
                            unit="USD/mmbtu",
                            value_selection_rationale_ko="요청되지 않은 9월 좌표입니다.",
                            proposed_value_rationale_ko=(
                                "정량 근거가 약해 보수적인 최종 입력값을 적용했습니다."
                            ),
                        ),
                    ],
                    parameter_selection_rationale_ko=(
                        "운송 규제 영향이 가스 가격 변수와 연결됩니다."
                    ),
                    confidence_overall=0.5,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=281,
            scenario_context={"scenario": {"scenario_id": 281}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Asia"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 7},
                    ],
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
        assert any("요청 selected_slots에 없는 좌표" in warning for warning in result["validation_warnings"])
        assert any("요청 selected_slot 좌표가 누락" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_rejects_partial_response_missing_requested_slots(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Demand",
            "model_sheet": "CoalGasAdjustment",
            "parameter_name": "Gas Futures Price",
            "canonical_parameter_name": "Gas Futures Price",
        }
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                ParameterAdjustment(
                    candidate_key="c1",
                    model_file="Demand",
                    model_sheet="CoalGasAdjustment",
                    parameter_name="Gas Futures Price",
                    selected=True,
                    slot_axes=[],
                    value_grid=[
                        ParameterValueCell(
                            coordinates={
                                "Region": "Asia",
                                "Year": 2026,
                                "Month": 7,
                            },
                            basecase_value=None,
                            proposed_value=0.1,
                            unit="USD/mmbtu",
                            value_selection_rationale_ko="Asia 2026년 7월 요청 slot입니다.",
                            proposed_value_rationale_ko=(
                                "정량 근거가 약해 보수적인 최종 입력값을 적용했습니다."
                            ),
                        ),
                    ],
                    parameter_selection_rationale_ko=(
                        "운송 규제 영향이 가스 가격 변수와 연결됩니다."
                    ),
                    confidence_overall=0.5,
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=281,
            scenario_context={"scenario": {"scenario_id": 281}},
            candidate_mappings=[candidate],
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Asia"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 7},
                    ],
                },
                {
                    "candidate_key": "c1",
                    "selected": True,
                    "slot_axes": [
                        {"axis_name": "Region", "axis_value": "Asia"},
                        {"axis_name": "Year", "axis_value": 2026},
                        {"axis_name": "Month", "axis_value": 8},
                    ],
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
        assert any("요청 selected_slot 좌표가 누락" in warning for warning in result["validation_warnings"])

    async def test_empty_llm_value_is_not_rule_backfilled(self) -> None:
        candidate = {
            "candidate_key": "routing-regas",
            "mapping_method": "routing",
            "model_file": "Supply",
            "model_sheet": "RegasAdjustment",
            "parameter_name": "RegasAdjustment",
            "canonical_parameter_name": "RegasAdjustment",
        }
        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("Step3 LLM should not be called without selected slots")

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
        assert adjustment["selected"] is False
        assert adjustment["parameter_name"] == "RegasAdjustment"
        assert adjustment["value_grid"] == []
        assert "needs_user_review" not in adjustment
        assert any("Step2 selected slot" in warning for warning in result["validation_warnings"])
        assert not any("규칙 보정값" in warning for warning in result["validation_warnings"])

    async def test_empty_llm_value_with_step2_slots_is_not_rule_backfilled(self) -> None:
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
                LLMValueAdjustment(
                    candidate_key="routing-regas",
                    value_grid=[],
                    rationale_ko="LLM이 정량 값을 확정하지 못했습니다.",
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
        assert adjustment["selected"] is False
        assert adjustment["value_grid"] == []
        assert "needs_user_review" not in adjustment
        assert not any("규칙 보정값" in warning for warning in result["validation_warnings"])

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
                            value_selection_rationale_ko="China 2026 row",
                            proposed_value_rationale_ko="정량 근거 없음",
                        ),
                        ParameterValueCell(
                            coordinates={"Country": "China", "Year": 2026},
                            basecase_value=49.5,
                            proposed_value=None,
                            unit="index",
                            value_selection_rationale_ko="China 2026 row",
                            proposed_value_rationale_ko="정량 근거 없음",
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
        assert "needs_user_review" not in adjustment
        assert any("proposed_value가 null" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_keeps_first_duplicate_slot_value_conflict(self) -> None:
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
                            value_selection_rationale_ko="Germany 2026년 12월 slot입니다.",
                            proposed_value_rationale_ko="한파 강도를 최종 입력값 -5로 산정했습니다.",
                        ),
                        ParameterValueCell(
                            coordinates={"Country": "Germany", "Year": "2026", "Month": "12"},
                            basecase_value=None,
                            proposed_value=-4,
                            unit="C",
                            value_selection_rationale_ko="Germany 2026년 12월 slot입니다.",
                            proposed_value_rationale_ko="한파 강도를 최종 입력값 -4로 산정했습니다.",
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
        assert adjustment["selected"] is True
        assert len(adjustment["value_grid"]) == 1
        assert adjustment["value_grid"][0]["proposed_value"] == -5
        assert "needs_user_review" not in adjustment
        assert any("동일 slot 좌표" in warning for warning in result["validation_warnings"])

    def test_confirmation_schema_accepts_valid_parameter_payload(self) -> None:
        payload = {
            "userId": 55,
            "data": {
                "confirmationParameters": [
                    {
                        "parameterName": "PowerMix",
                        "modelTarget": {
                            "modelFile": "Demand",
                            "modelSheet": "PowerMix",
                            "tableName": "table1",
                            "valueFieldNames": ["PowerMix"],
                            "slotAxesFieldNames": ["Country", "Year", "Month"],
                        },
                        "rationale": "사용자 확정",
                        "values": [
                            {
                                "Country": "Korea",
                                "Year": 2026,
                                "Month": 7,
                                "basecaseValue": 0.0346,
                                "proposedValue": 0.0173,
                                "rationale": "사용자 검토 후 확정",
                            },
                        ],
                    },
                ],
            },
        }

        parsed = ConfirmParametersIn.model_validate(payload)
        validate_confirmation_parameters(parsed.data.confirmation_parameters)

        assert parsed.user_id == 55
        assert parsed.data.confirmation_parameters[0].parameter_name == "PowerMix"

    def test_confirmation_validation_rejects_empty_parameter_payload(self) -> None:
        payload = {
            "data": {
                "confirmationParameters": [],
            },
        }

        parsed = ConfirmParametersIn.model_validate(payload)
        with self.assertRaises(MIBaseError) as error:
            validate_confirmation_parameters(parsed.data.confirmation_parameters)

        assert "must contain at least one parameter" in error.exception.error_message

    def test_confirmation_validation_rejects_duplicate_slots(self) -> None:
        payload = {
            "data": {
                "confirmationParameters": [
                    {
                        "parameterName": "PowerMix",
                        "modelTarget": {
                            "modelFile": "Demand",
                            "modelSheet": "PowerMix",
                            "tableName": "table1",
                            "valueFieldNames": ["PowerMix"],
                            "slotAxesFieldNames": ["Country", "Year", "Month"],
                        },
                        "rationale": "사용자 확정",
                        "values": [
                            {
                                "Country": "Korea",
                                "Year": 2026,
                                "Month": 7,
                                "basecaseValue": 0.0346,
                                "proposedValue": 0.0173,
                                "rationale": "사용자 검토 후 확정",
                            },
                            {
                                "Country": "Korea",
                                "Year": 2026,
                                "Month": 7,
                                "basecaseValue": 0.0346,
                                "proposedValue": 0.02,
                                "rationale": "중복 slot",
                            },
                        ],
                    },
                ],
            },
        }

        parsed = ConfirmParametersIn.model_validate(payload)
        with self.assertRaises(MIBaseError) as error:
            validate_confirmation_parameters(parsed.data.confirmation_parameters)

        assert "duplicates slot coordinates" in error.exception.error_message

    def test_confirmation_validation_accepts_unknown_parameter_metadata(self) -> None:
        payload = {
            "data": {
                "confirmationParameters": [
                    {
                        "parameterName": "UserCustomParameter",
                        "modelTarget": {
                            "modelFile": "Custom",
                            "modelSheet": "CustomSheet",
                            "tableName": "table9",
                            "valueFieldNames": ["CustomValue"],
                            "slotAxesFieldNames": ["CustomSlot"],
                        },
                        "rationale": "사용자 추가 파라미터",
                        "values": [
                            {
                                "CustomSlot": "A",
                                "basecaseValue": None,
                                "proposedValue": 1,
                                "rationale": "사용자 입력",
                            },
                        ],
                    },
                ],
            },
        }
        parameter_definitions = [
            {
                "parameter_name": "PowerMix",
                "model_file": "Demand",
                "model_sheet": "PowerMixAdjustment",
                "model_table": "table1",
                "basecase_read_mode": "fixed_columns",
                "basecase_column_roles": "B:Year,C:Country,F:% Power Mix",
            },
        ]

        parsed = ConfirmParametersIn.model_validate(payload)
        validate_confirmation_parameters(
            parsed.data.confirmation_parameters,
            parameter_definitions=parameter_definitions,
        )

        assert parsed.data.confirmation_parameters[0].parameter_name == "UserCustomParameter"

    def test_confirmation_validation_accepts_known_parameter_metadata(self) -> None:
        payload = {
            "data": {
                "confirmationParameters": [
                    {
                        "parameterName": "PowerMix",
                        "modelTarget": {
                            "modelFile": "Demand",
                            "modelSheet": "PowerMixAdjustment",
                            "tableName": "table1",
                            "valueFieldNames": ["PowerMix"],
                            "slotAxesFieldNames": ["Year", "Country"],
                        },
                        "rationale": "사용자 확정",
                        "values": [
                            {
                                "Year": 2026,
                                "Country": "Korea",
                                "basecaseValue": 0.0346,
                                "proposedValue": 0.0173,
                                "rationale": "사용자 검토 후 확정",
                            },
                        ],
                    },
                ],
            },
        }
        parameter_definitions = [
            {
                "parameter_name": "PowerMix",
                "model_file": "Demand",
                "model_sheet": "PowerMixAdjustment",
                "model_table": "table1",
                "basecase_read_mode": "fixed_columns",
                "basecase_column_roles": "B:Year,C:Country,F:% Power Mix",
            },
        ]

        parsed = ConfirmParametersIn.model_validate(payload)
        validate_confirmation_parameters(
            parsed.data.confirmation_parameters,
            parameter_definitions=parameter_definitions,
        )

        assert parsed.data.confirmation_parameters[0].model_target.model_sheet == (
            "PowerMixAdjustment"
        )

    def test_confirmation_validation_accepts_db_value_column_role(self) -> None:
        payload = {
            "data": {
                "confirmationParameters": [
                    {
                        "parameterName": "PowerMix",
                        "modelTarget": {
                            "modelFile": "Demand",
                            "modelSheet": "PowerMixAdjustment",
                            "tableName": "table1",
                            "valueFieldNames": ["Scenario Metric"],
                            "slotAxesFieldNames": ["Year", "Country"],
                        },
                        "rationale": "사용자 확정",
                        "values": [
                            {
                                "Year": 2026,
                                "Country": "Korea",
                                "basecaseValue": 0.0346,
                                "proposedValue": 0.0173,
                                "rationale": "사용자 검토 후 확정",
                            },
                        ],
                    },
                ],
            },
        }
        parameter_definitions = [
            {
                "parameter_name": "PowerMix",
                "model_file": "Demand",
                "model_sheet": "PowerMixAdjustment",
                "model_table": "table1",
                "basecase_read_mode": "fixed_columns",
                "basecase_column_roles": "B:Year,C:Country,F:Scenario Metric",
            },
        ]

        parsed = ConfirmParametersIn.model_validate(payload)
        validate_confirmation_parameters(
            parsed.data.confirmation_parameters,
            parameter_definitions=parameter_definitions,
        )

        assert parsed.data.confirmation_parameters[0].model_target.value_field_names == [
            "Scenario Metric",
        ]

    def test_confirmation_validation_rejects_known_parameter_wrong_fields(self) -> None:
        payload = {
            "data": {
                "confirmationParameters": [
                    {
                        "parameterName": "PowerMix",
                        "modelTarget": {
                            "modelFile": "Demand",
                            "modelSheet": "WrongSheet",
                            "tableName": "table1",
                            "valueFieldNames": ["WrongValue"],
                            "slotAxesFieldNames": ["Year", "WrongAxis"],
                        },
                        "rationale": "사용자 확정",
                        "values": [
                            {
                                "Year": 2026,
                                "WrongAxis": "Korea",
                                "basecaseValue": 0.0346,
                                "proposedValue": 0.0173,
                                "rationale": "사용자 검토 후 확정",
                            },
                        ],
                    },
                ],
            },
        }
        parameter_definitions = [
            {
                "parameter_name": "PowerMix",
                "model_file": "Demand",
                "model_sheet": "PowerMixAdjustment",
                "model_table": "table1",
                "basecase_read_mode": "fixed_columns",
                "basecase_column_roles": "B:Year,C:Country,F:% Power Mix",
            },
        ]

        parsed = ConfirmParametersIn.model_validate(payload)
        with self.assertRaises(MIBaseError) as error:
            validate_confirmation_parameters(
                parsed.data.confirmation_parameters,
                parameter_definitions=parameter_definitions,
            )

        assert "modelTarget.modelSheet must be 'PowerMixAdjustment'" in (
            error.exception.error_message
        )
        assert "valueFieldNames has invalid fields" in error.exception.error_message
        assert "slotAxesFieldNames has invalid fields" in error.exception.error_message

    def test_confirmation_validation_rejects_parameter_without_values(self) -> None:
        payload = {
            "data": {
                "confirmationParameters": [
                    {
                        "parameterName": "PowerMix",
                        "modelTarget": {
                            "modelFile": "Demand",
                            "modelSheet": "PowerMixAdjustment",
                            "tableName": "table1",
                            "valueFieldNames": ["PowerMix"],
                            "slotAxesFieldNames": ["Year", "Country"],
                        },
                        "rationale": "사용자 확정",
                        "values": [],
                    },
                ],
            },
        }

        parsed = ConfirmParametersIn.model_validate(payload)
        with self.assertRaises(MIBaseError) as error:
            validate_confirmation_parameters(parsed.data.confirmation_parameters)

        assert "values must not be empty" in error.exception.error_message

    def test_confirmation_endpoint_is_registered(self) -> None:
        route = next(
            route
            for route in model_parameter_router.routes
            if isinstance(route, APIRoute)
            and route.path == "/model-parameters/proposals/{modelParamProposalId}/confirmation"
        )

        assert [param.alias for param in route.dependant.path_params] == [
            "modelParamProposalId",
        ]

    def test_proposal_callback_endpoint_is_registered(self) -> None:
        route = next(
            route
            for route in model_parameter_router.routes
            if isinstance(route, APIRoute)
            and route.path == "/model-parameters/scenarios/{scenario_id}/proposals"
        )

        assert [param.alias for param in route.dependant.path_params] == [
            "scenario_id",
        ]

    def test_proposal_callback_accepted_schema_uses_camel_case(self) -> None:
        payload = ProposeParametersAcceptedOut.model_validate(
            {
                "data": {
                    "modelParamProposalId": 10001,
                    "status": "PROCESSING",
                },
            },
        )

        assert payload.model_dump(by_alias=True)["data"] == {
            "modelParamProposalId": 10001,
            "status": "PROCESSING",
        }

    def test_proposal_callback_success_payload_is_signal_only(self) -> None:
        payload = _callback_success_output(
            ProposeParametersData(
                model_param_proposal_id=10001,
                scenario_id=309,
                scenario_group_id=61,
                event_id=1378,
                proposal_parameters=[
                    ProposalParameter(
                        parameter_name="PowerMix",
                        model_target=ModelParameterTarget(
                            model_file="Demand",
                            model_sheet="PowerMixAdjustment",
                            table_name="Table2",
                            value_field_names=["PowerMix"],
                            slot_axes_field_names=["Country", "Year"],
                        ),
                        rationale="제안 근거",
                        values=[
                            {
                                "Country": "Japan",
                                "Year": 2026,
                                "basecaseValue": 0.3,
                                "proposedValue": 0.4,
                                "rationale": "값 근거",
                            },
                        ],
                    ),
                ],
            ),
        )

        assert payload.model_dump(by_alias=True) == {
            "status": "success",
            "message": "model parameter proposal completed",
            "data": {
                "modelParamProposalId": 10001,
                "scenarioId": 309,
                "scenarioGroupId": 61,
                "eventId": 1378,
                "status": "PROPOSED",
            },
        }

    def test_proposal_callback_error_payload_allows_null_data(self) -> None:
        payload = _callback_error_output(
            message="insufficient dimension mapping for event 1378",
        )

        assert payload.model_dump(by_alias=True) == {
            "status": "error",
            "message": "insufficient dimension mapping for event 1378",
            "data": None,
        }

    async def test_background_marks_callback_skipped_when_skip_callback_enabled(self) -> None:
        class FakeGraph:
            async def ainvoke(self, state: ModelParameterProposalState) -> dict[str, object]:
                assert state.scenario_id == 309
                return {}

        class FakeModelParameterService:
            def __init__(self) -> None:
                self.callback_statuses: list[str] = []

            def complete_proposal_result(
                self,
                *,
                model_param_proposal_id: int,
                proposal_parameters: list[object],
            ) -> None:
                assert model_param_proposal_id == 10001
                assert proposal_parameters == []

            def fail_proposal_result(self, **kwargs: object) -> None:
                raise AssertionError(f"unexpected proposal failure: {kwargs}")

            def update_callback_status(
                self,
                *,
                model_param_proposal_id: int,
                callback_status: str,
            ) -> None:
                assert model_param_proposal_id == 10001
                self.callback_statuses.append(callback_status)

        service = FakeModelParameterService()
        sent_urls: list[str] = []

        async def fake_send_callback(url: str, payload: object) -> None:
            sent_urls.append(url)

        response_data = ProposeParametersData(
            model_param_proposal_id=10001,
            scenario_id=309,
            scenario_group_id=61,
            event_id=1378,
            proposal_parameters=[],
        )
        settings = SimpleNamespace(
            callback_base_url="https://callback.example",
            callback_model_parameter_proposals_path="/scenarios/{scenario_id}/callback",
            skip_callback=True,
        )
        fake_config_module = types.ModuleType("apps.common.configs.config")
        fake_config_module.get_settings = lambda: settings

        with (
            patch.dict(sys.modules, {"apps.common.configs.config": fake_config_module}),
            patch.object(propose_flow, "build_graph", return_value=FakeGraph()),
            patch.object(propose_flow, "ModelParameterService", return_value=service),
            patch.object(propose_flow, "send_callback", side_effect=fake_send_callback),
            patch.object(propose_flow, "_ensure_mapping_candidates"),
            patch.object(propose_flow, "_proposal_parameters_from_state", return_value=[]),
            patch.object(propose_flow, "_ensure_proposal_parameters"),
            patch.object(propose_flow, "_to_response_data", return_value=response_data),
        ):
            await propose_flow.run_propose_parameters_background(
                model_param_proposal_id=10001,
                scenario_id=309,
                scenario_group_id=61,
                event_id=1378,
            )

        assert sent_urls == ["https://callback.example/scenarios/309/callback"]
        assert service.callback_statuses == ["SKIPPED"]

    async def test_background_marks_callback_failed_when_callback_path_format_fails(self) -> None:
        class FakeGraph:
            async def ainvoke(self, state: ModelParameterProposalState) -> dict[str, object]:
                assert state.scenario_id == 309
                return {}

        class FakeModelParameterService:
            def __init__(self) -> None:
                self.completed = False
                self.callback_statuses: list[str] = []

            def complete_proposal_result(
                self,
                *,
                model_param_proposal_id: int,
                proposal_parameters: list[object],
            ) -> None:
                assert model_param_proposal_id == 10001
                assert proposal_parameters == []
                self.completed = True

            def fail_proposal_result(self, **kwargs: object) -> None:
                raise AssertionError(f"callback path formatting must not fail proposal: {kwargs}")

            def update_callback_status(
                self,
                *,
                model_param_proposal_id: int,
                callback_status: str,
            ) -> None:
                assert model_param_proposal_id == 10001
                self.callback_statuses.append(callback_status)

        service = FakeModelParameterService()

        async def fake_send_callback(url: str, payload: object) -> None:
            raise AssertionError(f"send_callback should not run when URL format fails: {url}")

        response_data = ProposeParametersData(
            model_param_proposal_id=10001,
            scenario_id=309,
            scenario_group_id=61,
            event_id=1378,
            proposal_parameters=[],
        )
        settings = SimpleNamespace(
            callback_base_url="https://callback.example",
            callback_model_parameter_proposals_path="/scenarios/{scenarioId}/callback",
            skip_callback=False,
        )
        fake_config_module = types.ModuleType("apps.common.configs.config")
        fake_config_module.get_settings = lambda: settings

        with (
            patch.dict(sys.modules, {"apps.common.configs.config": fake_config_module}),
            patch.object(propose_flow, "build_graph", return_value=FakeGraph()),
            patch.object(propose_flow, "ModelParameterService", return_value=service),
            patch.object(propose_flow, "send_callback", side_effect=fake_send_callback),
            patch.object(propose_flow, "_ensure_mapping_candidates"),
            patch.object(propose_flow, "_proposal_parameters_from_state", return_value=[]),
            patch.object(propose_flow, "_ensure_proposal_parameters"),
            patch.object(propose_flow, "_to_response_data", return_value=response_data),
        ):
            await propose_flow.run_propose_parameters_background(
                model_param_proposal_id=10001,
                scenario_id=309,
                scenario_group_id=61,
                event_id=1378,
            )

        assert service.completed is True
        assert service.callback_statuses == ["FAILED"]


if __name__ == "__main__":
    unittest.main()
