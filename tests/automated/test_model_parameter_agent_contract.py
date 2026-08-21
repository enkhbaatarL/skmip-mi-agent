# ruff: noqa: S101

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import types
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from fastapi.routing import APIRoute
import pytest

from apps.agents.model_parameter_agent.api import router as model_parameter_router
from apps.agents.model_parameter_agent.constants import (
    MODEL_PARAMETER_PROPOSAL_ALLOWLIST,
    PROPOSAL_SCOPE_EXCLUDED_REASON_CODE,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.api_schema import (
    ConfirmParametersIn,
)
from apps.agents.model_parameter_agent.flows.confirm_parameters.validation import (
    validate_confirmation_parameters,
)
from apps.agents.model_parameter_agent.flows.propose_parameters import flow as propose_flow, nodes as proposal_nodes
from apps.agents.model_parameter_agent.flows.propose_parameters.api_schema import (
    ProposeParametersAcceptedOut,
    ProposeParametersData,
    ProposeParametersIn,
    ProposeParametersRequest,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.flow import (
    _callback_error_output,
    _callback_success_output,
    _route_after_candidate_validation,
    build_graph,
    prepare_propose_parameters_callback,
    to_output,
)
from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _build_basecase_slot_options,
    _coordinate_issues,
    _partition_candidate_validation_work,
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
from apps.agents.model_parameter_agent.flows.propose_parameters.state import ModelParameterProposalState
from apps.agents.model_parameter_agent.flows.propose_parameters.validation import (
    _has_mapping_candidates_from_db_rows,
    _raise_v4_semantic_empty_if_applicable,
)
from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
    ModelParameterService,
)
from apps.agents.model_parameter_agent.schemas.api.parameters import (
    ModelParameterTarget,
    ProposalParameter,
)
from apps.agents.model_parameter_agent.schemas.model_parameter_proposal import (
    LLMCandidateValidationResponse,
    LLMSlotAxis,
    LLMSlotProposal,
    LLMSlotProposalResponse,
    LLMValueAdjustment,
    LLMValueCell,
    LLMValueProposalResponse,
    ParameterSlotAxis,
    ParameterValueCell,
    RoutingDecision,
)
from apps.agents.model_parameter_agent.utils import parameter_mapping as parameter_mapping_utils
from apps.agents.model_parameter_agent.utils.basecase import build_basecase_records
from apps.agents.model_parameter_agent.utils.lut import (
    ReferenceLoadPolicy,
    build_basecase_index,
    build_slot_catalog,
    get_lut_catalog,
    get_parameter_spec_registry,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    DEFAULT_BASECASE_DIR,
    DEFAULT_INPUT_DIR,
    BasecaseProfile,
    ParameterKnowledgeBase,
    get_parameter_knowledge_base,
    get_parameter_knowledge_base_from_resources,
    match_parameter_candidates,
    normalize_parameter_name,
    partition_proposal_parameter_candidates,
)
from apps.common.exceptions.custom import MIBaseError
from apps.common.values.error_codes import ErrorCode


core_contract = pytest.mark.model_parameter_core
V4_GENERATION_STRATEGY = "multi_event_model_lever_dimensions"
V4_NO_CHANGE_TITLE = "파라미터로 반영할 변경 항목이 없습니다."
V4_NO_MODEL_INPUT_TITLE = "파라미터를 적용할 모델 입력 위치를 찾지 못했습니다."
V4_NO_PARAMETER_VALUE_TITLE = "적용할 파라미터 값을 생성하지 못했습니다."


def _assert_v4_semantic_empty_error(
    error: MIBaseError,
    *,
    expected_title: str,
) -> None:
    assert error.error_code is ErrorCode.INVALID_REQUEST
    assert error.code == -202
    assert error.status_code == 400
    assert str(error) == error.error_message
    assert error.error_message.count("\n") == 1
    title, detail = error.error_message.split("\n")
    assert title == expected_title
    assert 0 < len(detail) <= 300
    forbidden_fragments = (
        "[INVALID_REQUEST]",
        "요청이 유효하지 않습니다",
        "scenario_id",
        "scenarioId",
        "event_id",
        "eventId",
        "candidate_key",
        "candidateKey",
        "candidate=",
        "slot_key",
        "slotKey",
        "slot-1",
        "exclusion_reason_codes",
        "재요청",
        "다시 요청",
        "재호출",
        "retry",
    )
    for fragment in forbidden_fragments:
        assert fragment.lower() not in error.error_message.lower()
    for internal_id in ("501", "701", "101"):
        assert internal_id not in error.error_message


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
        basecase_column_roles=("B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity"),
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
        basecase_column_roles=("B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity"),
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
            "B:Continent,C:Region,D:Country,E:Regasification plant,F:Life Cycle Category,G:Nameplate capacity"
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
    _mapping_row(
        10,
        "lng_demand_impact_intensity",
        "LNG 수요 영향 강도",
        "direct",
        "Coal Futures Price",
        "가격기반 석탄-가스 스위칭",
    ),
    _mapping_row(
        10,
        "lng_demand_impact_intensity",
        "LNG 수요 영향 강도",
        "direct",
        "Gas Futures Price",
        "가격기반 석탄-가스 스위칭",
    ),
    _mapping_row(10, "lng_demand_impact_intensity", "LNG 수요 영향 강도", "direct", "PowerMix", "구조적 비중 변화"),
    _mapping_row(10, "alt_energy_absorption", "타 에너지원 흡수 가능성", "direct", "PowerMix", "원전·재생E 등 흡수"),
    _mapping_row(11, "period", "기간", "indirect", None, "시간축"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "SupplyDisruption", "생산 시설 피해 시"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "LiqUtilAdjustment", "수출 시설 피해 시"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "LiqProdAdjustment", "수출 시설 피해 시"),
    _mapping_row(11, "affected_facility_type", "영향 시설 유형", "routing", "RegasAdjustment", "수입 시설 피해 시"),
    _mapping_row(
        11, "affected_facility_type", "영향 시설 유형", "routing", "HurricaneIntensity", "미국 액화시설 허리케인"
    ),
    _mapping_row(11, "supply_disruption_intensity", "공급 차질 강도", "direct", None, "시설 가동률 감소율로 변환"),
    _mapping_row(17, "period", "기간", "indirect", None, "시간축"),
    _mapping_row(17, "transport_disruption", "운송 차질", "direct", "ShippingCost", "용선료·보험료 상승"),
    _mapping_row(
        17, "supply_disruption_intensity", "공급 차질 - 강도", "direct", "LiqUtilAdjustment", "액화시설 가동률 감소"
    ),
    _mapping_row(
        17, "supply_disruption_intensity", "공급 차질 - 강도", "direct", "LiqProdAdjustment", "생산량 직접 감소"
    ),
    _mapping_row(
        17,
        "supply_disruption_intensity",
        "공급 차질 - 강도",
        "direct",
        "SupplyDisruption",
        "upstream 생산 차질 동반 시",
    ),
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
    @core_contract
    def test_llm_scalar_response_fields_have_explicit_json_schema_types(self) -> None:
        slot_schema = LLMSlotProposalResponse.model_json_schema(by_alias=True)
        slot_axis_schema = slot_schema["$defs"]["LLMSlotAxis"]["properties"]["axisValue"]
        value_schema = LLMValueProposalResponse.model_json_schema(by_alias=True)
        proposed_value_schema = value_schema["$defs"]["LLMValueCell"]["properties"]["proposedValue"]

        assert slot_axis_schema != {}
        assert {item["type"] for item in slot_axis_schema["anyOf"]} == {
            "string",
            "integer",
            "number",
            "boolean",
            "null",
        }
        assert proposed_value_schema != {}
        assert {item["type"] for item in proposed_value_schema["anyOf"]} == {
            "string",
            "integer",
            "number",
            "null",
        }

    @core_contract
    def test_db_payload_uses_independent_basecase_and_proposed_precision(self) -> None:
        from apps.agents.model_parameter_agent.persistence import (
            model_parameter_service,
        )

        settings = SimpleNamespace(
            model_parameter_basecase_value_max_decimal_places=2,
            model_parameter_basecase_value_precision_mode="trunc",
            model_parameter_proposed_value_max_decimal_places=3,
            model_parameter_proposed_value_precision_mode="ceil",
        )
        with patch.object(
            model_parameter_service,
            "get_settings",
            return_value=settings,
        ):
            payload = model_parameter_service._parameter_json_payload(
                {
                    "values": [
                        {
                            "basecaseValue": -1.2399,
                            "proposedValue": -1.2341,
                        },
                    ],
                },
            )

        assert payload["values"][0] == {
            "basecaseValue": -1.23,
            "proposedValue": -1.234,
        }

    def test_parameter_name_normalization_does_not_apply_code_aliases(self) -> None:
        assert normalize_parameter_name("Gas Demand [BCM/Mt]") == "Gas Demand [BCM/Mt]"
        assert normalize_parameter_name(" ShippingCost ") == "ShippingCost"

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

    def test_to_state_preserves_sync_user_id(self) -> None:
        camel_state = propose_flow.to_state(
            {
                "scenario_id": 100,
                "userId": 101,
            },
        )
        snake_state = propose_flow.to_state(
            {
                "scenario_id": 100,
                "user_id": 102,
            },
        )

        assert camel_state.user_id == 101
        assert snake_state.user_id == 102

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

    @core_contract
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
        assert "No model parameter mapping candidates found" in (state_error.exception.error_message)

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

    def test_model_param_entrypoint_registers_router_and_lut_startup(self) -> None:
        main_source = Path("model_param.py").read_text()

        assert "model_parameter_router" in main_source
        assert "app.include_router(" in main_source
        assert "validate_lut_startup" in main_source
        assert "preload_basecase_runtime_cache" in main_source
        assert "preload_parameter_knowledge_base" not in main_source

    @core_contract
    def test_model_parameter_endpoint_accepts_optional_request_body(self) -> None:
        route = next(
            route
            for route in model_parameter_router.routes
            if isinstance(route, APIRoute) and route.path == "/model-parameters/scenarios/{scenario_id}/proposals"
        )

        assert route.body_field is not None
        assert route.body_field.required is False
        assert route.response_model is ProposeParametersAcceptedOut
        assert [param.name for param in route.dependant.path_params] == ["scenario_id"]

    def test_model_parameter_sync_endpoint_accepts_optional_request_body(self) -> None:
        route = next(
            route
            for route in model_parameter_router.routes
            if isinstance(route, APIRoute) and route.path == "/model-parameters/scenarios/{scenario_id}/proposals/sync"
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

    def test_runtime_proposal_allowlist_is_exact(self) -> None:
        assert MODEL_PARAMETER_PROPOSAL_ALLOWLIST == {
            "GDP",
            "PMI",
            "PowerMix",
            "Temperature",
            "LiqUtilAdjustment",
        }

    def test_runtime_proposal_scope_partitions_raw_candidates(self) -> None:
        allowed, excluded = partition_proposal_parameter_candidates(
            [
                {"canonical_parameter_name": name, "candidate_key": name}
                for name in [
                    "GDP",
                    "PMI",
                    "PowerMix",
                    "Temperature",
                    "LiqUtilAdjustment",
                    "ShippingCost",
                ]
            ],
        )

        assert [candidate["canonical_parameter_name"] for candidate in allowed] == [
            "GDP",
            "PMI",
            "PowerMix",
            "Temperature",
            "LiqUtilAdjustment",
        ]
        assert excluded == [
            {
                "canonical_parameter_name": "ShippingCost",
                "candidate_key": "ShippingCost",
                "reason_code": PROPOSAL_SCOPE_EXCLUDED_REASON_CODE,
                "reason": "ShippingCost is outside the runtime model-parameter proposal allow-list.",
            },
        ]

    def test_select_parameter_candidates_excludes_out_of_scope_mapping(self) -> None:
        knowledge_base = ParameterKnowledgeBase(
            mapping_source="test",
            basecase_dir_path="",
            parameter_definitions={},
            mapping_rules=[],
            basecase_profiles={},
        )
        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.nodes.match_parameter_candidates",
            return_value=(
                [
                    {
                        "candidate_key": "shipping",
                        "canonical_parameter_name": "ShippingCost",
                    },
                ],
                [],
                [],
            ),
        ):
            selected = select_parameter_candidates(
                ModelParameterProposalState(
                    scenario_id=100,
                    scenario_context={"scenario": {"scenario_id": 100}},
                    parameter_knowledge_base=knowledge_base,
                ),
            )

        assert selected["candidate_mappings"] == []
        assert selected["non_input_items"][0]["reason_code"] == PROPOSAL_SCOPE_EXCLUDED_REASON_CODE
        assert "ShippingCost" in selected["validation_warnings"][0]

    def test_mapping_precheck_applies_runtime_scope_to_v1_and_v3(self) -> None:
        for strategy in ("single_event_template_dimensions", "multi_event_composite_dimensions"):
            for parameter_name, expected in (("GDP", True), ("ShippingCost", False)):
                context: dict[str, Any] = {
                    "scenario": {
                        "scenario_id": 100,
                        "dimension_values": {"economic_intensity": "downside"},
                    },
                    "scenario_group": {
                        "event_type_l2_id": 17,
                        "generation_strategy": strategy,
                    },
                    "parameter_mapping_resources": {
                        "mapping_rules": [
                            {
                                "event_type_l2_id": 17,
                                "dimension_key": "economic_intensity",
                                "canonical_parameter_name": parameter_name,
                                "mapping_method": "direct",
                            },
                        ],
                        "parameter_definitions": [
                            {
                                "canonical_parameter_name": parameter_name,
                                "parameter_name": parameter_name,
                                "model_file": "Demand",
                                "model_sheet": "Demand Model Input",
                            },
                        ],
                    },
                }
                if strategy == "multi_event_composite_dimensions":
                    context["dimension_lineage"] = [
                        {
                            "mapped_sources": [
                                {
                                    "event_type_l2_id": 17,
                                    "mapping_dimension_key": "economic_intensity",
                                },
                            ],
                        },
                    ]

                with self.subTest(strategy=strategy, parameter_name=parameter_name):
                    assert _has_mapping_candidates_from_db_rows(
                        scenario_context=context,
                    ) is expected

    def test_prepare_v4_callback_applies_runtime_scope_before_processing_row(self) -> None:
        context = {
            "scenario": {"scenario_id": 100, "scenario_group_id": 20},
            "scenario_group": {
                "scenario_group_id": 20,
                "generation_strategy": V4_GENERATION_STRATEGY,
            },
            "parameter_mapping_resources": {
                "parameter_definitions": [
                    {
                        "canonical_parameter_name": "GDP",
                        "parameter_name": "GDP",
                        "model_file": "Demand",
                        "model_sheet": "Demand Model Input",
                    },
                    {
                        "canonical_parameter_name": "ShippingCost",
                        "parameter_name": "ShippingCost",
                        "model_file": "Trade",
                        "model_sheet": "ShippingCostInput",
                    },
                ],
            },
        }
        matcher_target = (
            "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
            "match_v4_parameter_candidates_from_rows"
        )
        with (
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
            ) as service_cls,
            patch(
                matcher_target,
                return_value=([{"canonical_parameter_name": "ShippingCost"}], [], []),
            ),
        ):
            service_cls.return_value.load_context.return_value = context

            with self.assertRaises(MIBaseError):
                prepare_propose_parameters_callback(100)

            service_cls.return_value.create_processing_proposal.assert_not_called()

        with (
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
            ) as service_cls,
            patch(
                matcher_target,
                return_value=(
                    [
                        {"canonical_parameter_name": "GDP"},
                        {"canonical_parameter_name": "ShippingCost"},
                    ],
                    [],
                    [],
                ),
            ),
        ):
            service_cls.return_value.load_context.return_value = context
            service_cls.return_value.create_processing_proposal.return_value = 901

            result = prepare_propose_parameters_callback(100)

            assert result["model_param_proposal_id"] == 901
            service_cls.return_value.create_processing_proposal.assert_called_once_with(
                scenario_context=context,
                user_id=None,
            )

    @core_contract
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

    def test_parameter_matching_requires_dimension_values_object(self) -> None:
        kb = get_parameter_knowledge_base_from_resources(
            mapping_rows=[
                _mapping_row(
                    17,
                    "transport_disruption",
                    "운송 차질",
                    "direct",
                    "ShippingCost",
                    "운송 차질은 ShippingCost에 직접 반영",
                ),
            ],
            parameter_rows=[row for row in TEST_PARAMETER_ROWS if row["canonical_parameter_name"] == "ShippingCost"],
        )

        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            {
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": [
                        {"dim_key": "transport_disruption", "value": "높음"},
                    ],
                },
                "scenario_group": {"event_type_l2_id": 17},
                "dimension_template": [
                    {"dim_key": "transport_disruption", "label": "운송 차질"},
                ],
            },
        )

        assert candidates == []
        assert non_inputs == []
        assert warnings == [
            "scenario.dimension_values가 JSON object가 아니어서 DB dimension-parameter 매핑을 수행하지 않았습니다.",
        ]

    def test_mapping_precheck_requires_dimension_values_object(self) -> None:
        assert not _has_mapping_candidates_from_db_rows(
            scenario_context={
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": [
                        {"dim_key": "transport_disruption", "value": "높음"},
                    ],
                },
                "scenario_group": {"event_type_l2_id": 17},
                "dimension_template": [
                    {"dim_key": "transport_disruption", "label": "운송 차질"},
                ],
                "parameter_mapping_resources": {
                    "mapping_rules": [
                        _mapping_row(
                            17,
                            "transport_disruption",
                            "운송 차질",
                            "direct",
                            "ShippingCost",
                            "운송 차질은 ShippingCost에 직접 반영",
                        ),
                    ],
                    "parameter_definitions": [
                        row for row in TEST_PARAMETER_ROWS if row["canonical_parameter_name"] == "ShippingCost"
                    ],
                },
            },
        )

    def test_parameter_matching_does_not_use_template_as_mapping_source(self) -> None:
        kb = get_parameter_knowledge_base_from_resources(
            mapping_rows=[
                _mapping_row(
                    17,
                    "transport_disruption",
                    "운송 차질",
                    "direct",
                    "ShippingCost",
                    "운송 차질은 ShippingCost에 직접 반영",
                ),
            ],
            parameter_rows=[row for row in TEST_PARAMETER_ROWS if row["canonical_parameter_name"] == "ShippingCost"],
        )

        candidates, non_inputs, warnings = match_parameter_candidates(
            kb,
            {
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": {},
                },
                "scenario_group": {"event_type_l2_id": 17},
                "dimension_template": [
                    {"dim_key": "transport_disruption", "label": "운송 차질"},
                ],
            },
        )

        assert candidates == []
        assert non_inputs == []
        assert warnings == [
            "시나리오 dimension key가 없어 DB dimension-parameter 매핑을 수행하지 않았습니다.",
        ]

    def test_mapping_precheck_does_not_use_template_as_mapping_source(self) -> None:
        assert not _has_mapping_candidates_from_db_rows(
            scenario_context={
                "scenario": {
                    "scenario_id": 100,
                    "dimension_values": {},
                },
                "scenario_group": {"event_type_l2_id": 17},
                "dimension_template": [
                    {"dim_key": "transport_disruption", "label": "운송 차질"},
                ],
                "parameter_mapping_resources": {
                    "mapping_rules": [
                        _mapping_row(
                            17,
                            "transport_disruption",
                            "운송 차질",
                            "direct",
                            "ShippingCost",
                            "운송 차질은 ShippingCost에 직접 반영",
                        ),
                    ],
                    "parameter_definitions": [
                        row for row in TEST_PARAMETER_ROWS if row["canonical_parameter_name"] == "ShippingCost"
                    ],
                },
            },
        )

    @core_contract
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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
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
                request_usr_id=40,
                title="group",
                summary="",
                description="",
                dimension_selected=[],
                scenario_count=1,
                status="READY",
                stage="DONE",
            )
            group_repository_cls.return_value.fetch_single_active_group_event.return_value = SimpleNamespace(
                mi_event_id=30,
                event_type_l2_id=17,
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
        group_repository_cls.return_value.fetch_single_active_group_event.assert_called_once_with(
            20,
        )
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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
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

            mapping_rules, parameter_definitions = ModelParameterService().load_parameter_mapping_resources()

        assert mapping_rules == [{"dimension_key": "period"}]
        assert parameter_definitions == [{"parameter_name": "ShippingCost"}]
        repository_cls.return_value.fetch_parameter_mapping_resources.assert_called_once_with()

    def test_request_load_context_builds_knowledge_base_from_loaded_db_resources(self) -> None:
        scenario_context = {
            "scenario": {
                "scenario_id": 100,
                "title": "economic slowdown",
                "dimension_values": {"economic_intensity": "하락"},
            },
            "scenario_group": {"event_type_l2_id": 17, "mi_event_id": 30},
            "dimension_template": [
                {"dim_key": "economic_intensity", "label": "경제 강도"},
            ],
            "parameter_mapping_resources": {
                "mapping_rules": [
                    {
                        "event_type_l2_id": 17,
                        "dimension_key": "economic_intensity",
                        "dimension_label": "경제 강도",
                        "canonical_parameter_name": "GDP",
                        "mapping_method": "direct",
                        "comment": "경제 강도는 GDP에 직접 반영",
                    },
                ],
                "parameter_definitions": [
                    {
                        "canonical_parameter_name": "GDP",
                        "parameter_name": "GDP",
                        "parameter_hint": "경제 성장률 입력값",
                        "model_file": "Demand",
                        "model_sheet": "Demand Model Input",
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
                "apps.agents.model_parameter_agent.flows.propose_parameters.nodes.ModelParameterService",
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

        assert kb.definition_for("GDP") is not None
        assert selected["candidate_mappings"][0]["canonical_parameter_name"] == "GDP"

    @core_contract
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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
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
                                "basecaseValue": 1.23456789,
                                "proposedValue": 2.98765999,
                                "rationale": "수에즈 운송 차질",
                            },
                            {
                                "Route": "Hormuz",
                                "basecaseValue": -1.23456789,
                                "proposedValue": -2.98765999,
                                "rationale": "음수 정밀도 제한",
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
        saved_payload = repository_cls.return_value.create_model_param_proposal.call_args.kwargs["proposal_parameters"]
        assert saved_payload[0]["parameterName"] == "ShippingCost"
        assert saved_payload[0]["modelTarget"]["modelFile"] == "Trade"
        assert saved_payload[0]["modelTarget"]["tableName"] == "Table1"
        assert saved_payload[0]["values"][0]["basecaseValue"] == 1.23456
        assert saved_payload[0]["values"][0]["proposedValue"] == 2.98765
        assert saved_payload[0]["values"][1]["basecaseValue"] == -1.23456
        assert saved_payload[0]["values"][1]["proposedValue"] == -2.98765
        assert repository_cls.return_value.create_model_param_proposal.call_args.kwargs["request_usr_id"] == 40

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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
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
        assert repository_cls.return_value.create_model_param_proposal.call_args.kwargs["request_usr_id"] is None

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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.fetch_model_param_proposal_for_update.return_value = {
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

    @core_contract
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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.fetch_model_param_proposal_for_update.return_value = {
                "model_param_proposal_id": 901,
                "status": "CONFIRMED",
            }

            result = ModelParameterService().confirm_proposal_result(
                model_param_proposal_id=901,
                user_id=56,
                confirmation_parameters=[
                    {
                        "parameterName": "PowerMix",
                        "values": [
                            {
                                "basecaseValue": 0.123456789,
                                "proposedValue": 0.500009999,
                            },
                            {
                                "basecaseValue": -0.123456789,
                                "proposedValue": -0.500009999,
                            },
                        ],
                    },
                ],
            )

        assert result == {
            "model_param_proposal_id": 901,
            "status": "CONFIRMED",
        }
        repository_cls.return_value.confirm_model_param_proposal.assert_called_once_with(
            model_param_proposal_id=901,
            user_id=56,
            confirmation_parameters=[
                {
                    "parameterName": "PowerMix",
                    "values": [
                        {
                            "basecaseValue": 0.12345,
                            "proposedValue": 0.5,
                        },
                        {
                            "basecaseValue": -0.12345,
                            "proposedValue": -0.5,
                        },
                    ],
                },
            ],
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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            from apps.agents.model_parameter_agent.persistence.model_parameter_service import (
                ModelParameterService,
            )

            repository_cls.return_value.fetch_model_param_proposal_for_update.return_value = {
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

    def test_model_parameter_service_completes_only_locked_processing_row(self) -> None:
        fake_session = SimpleNamespace(commit=Mock(), rollback=Mock(), close=Mock())
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            repository = repository_cls.return_value
            repository.fetch_model_param_proposal_for_update.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROCESSING",
            }
            repository.complete_model_param_proposal.return_value = True

            ModelParameterService().complete_proposal_result(
                model_param_proposal_id=901,
                proposal_parameters=[{"parameterName": "GDP"}],
            )

        repository.fetch_model_param_proposal_for_update.assert_called_once_with(901)
        repository.complete_model_param_proposal.assert_called_once()
        fake_session.commit.assert_called_once()
        fake_session.rollback.assert_not_called()

    def test_model_parameter_service_rejects_completion_from_proposed_status(self) -> None:
        fake_session = SimpleNamespace(commit=Mock(), rollback=Mock(), close=Mock())
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            repository = repository_cls.return_value
            repository.fetch_model_param_proposal_for_update.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROPOSED",
            }

            with self.assertRaises(MIBaseError) as error:
                ModelParameterService().complete_proposal_result(
                    model_param_proposal_id=901,
                    proposal_parameters=[],
                )

        assert "must be PROCESSING before completion" in error.exception.error_message
        repository.complete_model_param_proposal.assert_not_called()
        fake_session.commit.assert_not_called()
        fake_session.rollback.assert_called_once()

    def test_model_parameter_service_rejects_missing_transition_row(self) -> None:
        fake_session = SimpleNamespace(commit=Mock(), rollback=Mock(), close=Mock())
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            repository_cls.return_value.fetch_model_param_proposal_for_update.return_value = None

            with self.assertRaises(MIBaseError) as error:
                ModelParameterService().fail_proposal_result(
                    model_param_proposal_id=901,
                    error_code="INVALID_REQUEST",
                    error_message="failed",
                )

        assert error.exception.error_code.name == "ENTITY_NOT_FOUND"
        fake_session.commit.assert_not_called()
        fake_session.rollback.assert_called_once()

    def test_model_parameter_service_fails_only_locked_processing_row(self) -> None:
        fake_session = SimpleNamespace(commit=Mock(), rollback=Mock(), close=Mock())
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            repository = repository_cls.return_value
            repository.fetch_model_param_proposal_for_update.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROCESSING",
            }
            repository.fail_model_param_proposal.return_value = True

            ModelParameterService().fail_proposal_result(
                model_param_proposal_id=901,
                error_code="INVALID_REQUEST",
                error_message="failed",
            )

        repository.fail_model_param_proposal.assert_called_once()
        fake_session.commit.assert_called_once()
        fake_session.rollback.assert_not_called()

    def test_model_parameter_service_rejects_zero_row_transition_update(self) -> None:
        fake_session = SimpleNamespace(commit=Mock(), rollback=Mock(), close=Mock())
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            repository = repository_cls.return_value
            repository.fetch_model_param_proposal_for_update.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROCESSING",
            }
            repository.complete_model_param_proposal.return_value = False

            with self.assertRaises(MIBaseError) as error:
                ModelParameterService().complete_proposal_result(
                    model_param_proposal_id=901,
                    proposal_parameters=[],
                )

        assert error.exception.error_code.name == "ENTITY_NOT_FOUND"
        fake_session.commit.assert_not_called()
        fake_session.rollback.assert_called_once()

    def test_model_parameter_service_checks_callback_pending_state(self) -> None:
        fake_session = SimpleNamespace(commit=Mock(), rollback=Mock(), close=Mock())
        fake_connection_module = types.ModuleType(
            "apps.common.configs.database.sync_database.connection",
        )
        fake_connection_module.get_sync_session = lambda: fake_session

        with (
            patch.dict(
                sys.modules,
                {
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            repository = repository_cls.return_value
            repository.fetch_model_param_proposal_for_update.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROPOSED",
                "callback_status": "SUCCEEDED",
            }

            with self.assertRaises(MIBaseError) as error:
                ModelParameterService().update_callback_status(
                    model_param_proposal_id=901,
                    callback_status="FAILED",
                )

        assert "must be PENDING" in error.exception.error_message
        repository.update_model_param_callback_status.assert_not_called()
        fake_session.commit.assert_not_called()
        fake_session.rollback.assert_called_once()

    def test_model_parameter_persistence_write_scope_is_proposal_only(self) -> None:
        source = (
            Path(
                "apps/persistence/model_parameter/repository.py",
            )
            .read_text()
            .lower()
        )

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
        existing_profiles = [profile for profile in kb.basecase_profiles.values() if profile.sheet_exists]

        assert existing_profiles
        assert kb.basecase_profiles["trade::shippingcostinput"].row_count > 18000
        for profile in existing_profiles:
            assert profile.workbook_path
            assert profile.sheet_name

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    @core_contract
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
            kb.profile_for(candidate.get("model_file"), candidate.get("model_sheet")) for candidate in candidates
        )

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    @core_contract
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
        assert {candidate["canonical_parameter_name"] for candidate in candidates} == {
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
        parameter_rows = [row for row in TEST_PARAMETER_ROWS if row["canonical_parameter_name"] == "ShippingCost"]
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

    def test_basecase_records_reuse_and_close_workbook_per_request(self) -> None:
        class FakeWorksheet:
            max_row = 2
            max_column = 3

            def iter_rows(self, **kwargs):  # noqa: ANN003
                min_row = int(kwargs.get("min_row") or 1)
                max_row = int(kwargs.get("max_row") or self.max_row)
                max_col = int(kwargs.get("max_col") or self.max_column)
                rows = {
                    1: ("Japan", 1.0, 2.0),
                    2: ("Korea", 3.0, 4.0),
                }
                for row_idx in range(min_row, max_row + 1):
                    yield rows[row_idx][:max_col]

        class FakeWorkbook:
            sheetnames = ["Sheet1"]

            def __init__(self) -> None:
                self.close_count = 0
                self.sheet = FakeWorksheet()

            def __getitem__(self, sheet_name: str) -> FakeWorksheet:
                assert sheet_name == "Sheet1"
                return self.sheet

            def close(self) -> None:
                self.close_count += 1

        workbook = FakeWorkbook()
        load_calls: list[Path] = []

        def fake_loader(path: Path, **kwargs):  # noqa: ANN003
            assert kwargs == {
                "read_only": True,
                "data_only": True,
                "keep_vba": False,
            }
            load_calls.append(path)
            return workbook

        kb = ParameterKnowledgeBase(
            mapping_source="test",
            basecase_dir_path="/tmp",
            parameter_definitions={},
            mapping_rules=[],
            basecase_profiles={
                "demand::sheet1": BasecaseProfile(
                    model_file="Demand",
                    workbook_path="/tmp/Demand Model_Input.xlsm",
                    sheet_name="Sheet1",
                    sheet_exists=True,
                ),
            },
        )
        candidates = [
            {
                "candidate_key": "c1",
                "model_file": "Demand",
                "model_sheet": "Sheet1",
                "parameter_name": "ParamA",
                "canonical_parameter_name": "ParamA",
                "basecase_read_mode": "fixed_columns",
                "basecase_data_start_row": 1,
                "basecase_column_roles": "A:Country,B:ParamA",
            },
            {
                "candidate_key": "c2",
                "model_file": "Demand",
                "model_sheet": "Sheet1",
                "parameter_name": "ParamB",
                "canonical_parameter_name": "ParamB",
                "basecase_read_mode": "fixed_columns",
                "basecase_data_start_row": 1,
                "basecase_column_roles": "A:Country,C:ParamB",
            },
        ]

        with patch(
            "apps.agents.model_parameter_agent.utils.parameter_mapping._require_workbook_loader",
            return_value=fake_loader,
        ):
            records, warnings = build_basecase_records(kb, candidates, {})

        assert not warnings
        assert len(load_calls) == 1
        assert workbook.close_count == 1
        assert [record["candidate_key"] for record in records] == [
            "c1",
            "c1",
            "c2",
            "c2",
        ]
        assert [record["value"] for record in records] == [1.0, 3.0, 2.0, 4.0]

    def test_auto_matrix_excel_error_preserves_only_metadata_enabled_axes(self) -> None:
        profile = BasecaseProfile(
            model_file="Supply",
            workbook_path="/tmp/Auto Matrix Error.xlsm",
            sheet_name="LiqUtilAdjustment",
            sheet_exists=True,
        )
        block = parameter_mapping_utils.BasecaseMatrixBlock(
            header_row=3,
            start_col=2,
            time_label_col=1,
            time_start_col=7,
            year_row=1,
            month_row=2,
            period_row=3,
            axis_columns={
                2: "Country",
                3: "LNG Plant",
                4: "LNG Plant Train",
                5: "Life Cycle Category",
                6: "Nameplate Capacity (MTPA)",
            },
            value_name="LiqUtilAdjustment",
            section="basecase",
            time_descriptors={
                7: {"Year": 2026, "Month": 7, "Period": 1},
            },
        )
        values = [
            None,
            "Qatar",
            "QatarGas LNG",
            "QatarGas LNG T12",
            "Operating",
            7.8,
            "#REF!",
        ]
        candidate = {
            "candidate_key": "liq",
            "canonical_parameter_name": "LiqUtilAdjustment",
            parameter_mapping_utils.PRESERVE_BASECASE_AXES_WITHOUT_VALUE_FIELD: True,
        }

        records: list[dict[str, Any]] = []
        parameter_mapping_utils._append_matrix_records_for_row(  # noqa: SLF001
            records=records,
            values=values,
            row_idx=4,
            block=block,
            candidate=candidate,
            profile=profile,
        )

        assert len(records) == 1
        assert records[0]["value"] is None
        assert records[0]["axes"]["Nameplate Capacity (MTPA)"] == 7.8

        records_without_metadata: list[dict[str, Any]] = []
        parameter_mapping_utils._append_matrix_records_for_row(  # noqa: SLF001
            records=records_without_metadata,
            values=values,
            row_idx=4,
            block=block,
            candidate={
                "candidate_key": "other",
                "canonical_parameter_name": "OtherParameter",
            },
            profile=profile,
        )
        assert records_without_metadata == []

    def test_explicit_matrix_preserves_metadata_for_all_excel_error_values(self) -> None:
        error_values = ("#REF!", "#N/A", "#VALUE!", "#DIV/0!")

        class FakeWorksheet:
            max_row = 7
            max_column = 7

            def iter_rows(self, **kwargs):  # noqa: ANN003
                min_row = int(kwargs.get("min_row") or 1)
                max_row = int(kwargs.get("max_row") or self.max_row)
                max_col = int(kwargs.get("max_col") or self.max_column)
                rows = {
                    1: (None, None, None, None, None, None, 2026),
                    2: (None, None, None, None, None, None, 7),
                    3: (None, None, None, None, None, None, 1),
                    **{
                        row_idx: (
                            None,
                            "Qatar",
                            "QatarGas LNG",
                            f"QatarGas LNG T{row_idx - 3}",
                            "Operating",
                            7.8,
                            error_value,
                        )
                        for row_idx, error_value in enumerate(error_values, start=4)
                    },
                }
                for row_idx in range(min_row, max_row + 1):
                    yield rows[row_idx][:max_col]

        class FakeWorkbook:
            sheetnames = ["LiqUtilAdjustment"]

            def __init__(self) -> None:
                self.sheet = FakeWorksheet()

            def __getitem__(self, sheet_name: str) -> FakeWorksheet:
                assert sheet_name == "LiqUtilAdjustment"
                return self.sheet

            def close(self) -> None:
                return None

        kb = ParameterKnowledgeBase(
            mapping_source="test",
            basecase_dir_path="/tmp",
            parameter_definitions={},
            mapping_rules=[],
            basecase_profiles={
                "supply::liqutiladjustment": BasecaseProfile(
                    model_file="Supply",
                    workbook_path="/tmp/Explicit Matrix Error.xlsm",
                    sheet_name="LiqUtilAdjustment",
                    sheet_exists=True,
                ),
            },
        )
        candidate = {
            "candidate_key": "liq-error",
            "model_file": "Supply",
            "model_sheet": "LiqUtilAdjustment",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
            "basecase_read_mode": "matrix_time_columns",
            "basecase_data_start_row": 4,
            "basecase_column_roles": (
                "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)"
            ),
            "basecase_year_row": 1,
            "basecase_month_row": 2,
            "basecase_period_row": 3,
            "basecase_value_start_col": "G",
            "basecase_value_end_col": "G",
        }

        with patch(
            "apps.agents.model_parameter_agent.utils.parameter_mapping._require_workbook_loader",
            return_value=lambda *_args, **_kwargs: FakeWorkbook(),
        ):
            records, warnings = build_basecase_records(kb, [candidate], {})

        assert warnings == []
        assert len(records) == len(error_values)
        assert all(record["value"] is None for record in records)
        assert all(record["axes"]["Nameplate Capacity (MTPA)"] == 7.8 for record in records)
        assert {record["source_row"] for record in records} == {4, 5, 6, 7}

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
    @core_contract
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
            candidate for candidate in candidates if candidate["canonical_parameter_name"] == "LiqUtilAdjustment"
        )
        assert liq_candidate["basecase_column_roles"] == (
            "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity"
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

        arctic_t3_axis_reference = _record_with(
            records,
            axes={
                "Country": "Russia",
                "LNG Plant": "Arctic LNG 2",
                "LNG Plant Train": "Arctic LNG 2 T3",
                "Year": 2026,
                "Month": 1,
                "Period": 97,
            },
            source_row=110,
            source_col=34,
        )
        assert arctic_t3_axis_reference["value"] is None
        assert arctic_t3_axis_reference["axes"]["Nameplate Capacity"] == 6.599999

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
            candidate for candidate in candidates if candidate["canonical_parameter_name"] == "LiqProdAdjustment"
        )
        assert liq_candidate["basecase_column_roles"] == (
            "B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity"
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
        assert all(record["value"] is None for record in records)
        assert min(record["source_row"] for record in records) == 11
        assert max(record["source_row"] for record in records) == 358

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_pipeline_incomplete_workbook_axes_fall_back_to_exact_lut(self) -> None:
        parameter_rows = [
            _parameter_row(
                "PipelineAdjustment",
                model_file="Supply",
                model_sheet="PipelineAdjustment",
                semantic_axes="파이프라인 용량 - 노선·출발국·도착국·연·월",
                basecase_read_mode="fixed_columns",
                basecase_header_row=7,
                basecase_data_start_row=13,
                basecase_column_roles=("B:Year,C:Month,D:Pipeline name,H:PipelineAdjustment"),
            ),
        ]
        mapping_rows = [
            _mapping_row(
                4,
                "pipeline_capacity",
                "파이프라인 용량",
                "direct",
                "PipelineAdjustment",
                "파이프라인 용량 직접 조정",
            ),
        ]
        kb = get_parameter_knowledge_base_from_resources(
            mapping_rows=mapping_rows,
            parameter_rows=parameter_rows,
            basecase_dir_path=str(_default_basecase_dir()),
        )
        context = {
            "scenario": {
                "scenario_id": 100,
                "dimension_values": {"pipeline_capacity": "감소"},
            },
            "scenario_group": {"event_type_l2_id": 4},
            "dimension_template": [
                {"dim_key": "pipeline_capacity", "label": "파이프라인 용량"},
            ],
        }
        candidates, _, candidate_warnings = match_parameter_candidates(kb, context)
        assert not candidate_warnings
        registry = get_parameter_spec_registry()
        records, record_warnings = build_basecase_records(
            kb,
            candidates,
            context,
            registry=registry,
        )

        assert records == []
        assert any(
            "missing_key_axes=['Pipeline Name', 'From Country', 'To Country']" in warning for warning in record_warnings
        )
        policy = ReferenceLoadPolicy(2026, 2030)
        basecase_index = build_basecase_index(
            records,
            candidates,
            policy=policy,
            registry=registry,
        )
        slot_catalog = build_slot_catalog(
            basecase_index,
            get_lut_catalog(policy, registry=registry),
        )
        assert len(slot_catalog.candidates) == 1
        assert len(slot_catalog.candidates[0].leaves) == 6
        assert sum(len(leaf.available_periods) for leaf in slot_catalog.candidates[0].leaves) == 360

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
            candidate for candidate in candidates if candidate["canonical_parameter_name"] == "RegasAdjustment"
        )
        assert regas_candidate["basecase_column_roles"] == (
            "B:Continent,C:Region,D:Country,E:Regasification plant,F:Life Cycle Category,G:Nameplate capacity"
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
            candidate for candidate in candidates if candidate["canonical_parameter_name"] == "Temperature"
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
            candidate for candidate in candidates if candidate["canonical_parameter_name"] == "PowerMix"
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
            candidate = next(item for item in candidates if item["canonical_parameter_name"] == parameter_name)
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
            row for row in TEST_MAPPING_ROWS if row["canonical_parameter_name"] == "Temperature"
        ]
        temperature_parameter_rows = [
            row for row in TEST_PARAMETER_ROWS if row["canonical_parameter_name"] == "Temperature"
        ]

        assert all("basecase_column_roles" not in row for row in temperature_dimension_rows)
        assert len(temperature_dimension_rows) == 2
        assert len(temperature_parameter_rows) == 1
        assert temperature_parameter_rows[0]["basecase_column_roles"] == "K:Year,L:Month,M:Country,O:Temperature"

    @unittest.skipUnless(_basecase_available(), "model parameter basecase files are not available")
    def test_coal_and_gas_futures_are_split_parameters(self) -> None:
        dimension_canonicals = [
            row["canonical_parameter_name"]
            for row in TEST_MAPPING_ROWS
            if row["event_type_l2_id"] == 10 and row["dimension_key"] == "lng_demand_impact_intensity"
        ]
        parameter_canonicals = {row["canonical_parameter_name"] for row in TEST_PARAMETER_ROWS}

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
        assert {candidate["canonical_parameter_name"] for candidate in candidates} >= {
            "Coal Futures Price",
            "Gas Futures Price",
        }

    @core_contract
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
        assert service_cls.return_value.save_proposal_result.call_args.kwargs["user_id"] == 101
        assert "validationWarnings" not in dumped
        assert "scenarioContext" not in dumped
        assert "candidateMappings" not in dumped
        assert "basecaseSamples" not in dumped
        assert "basecaseRecords" not in dumped
        assert "parameterSlots" not in dumped
        assert "llmUsage" not in dumped

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
                            "basecase_column_roles": ("B:Year,C:Country,F:Scenario Metric"),
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

        proposal_parameter = output.model_dump(by_alias=True)["data"]["proposalParameters"][0]
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

        assert "No model parameter mapping candidates found" in (error.exception.error_message)

    def test_prepare_callback_rejects_empty_mapping_before_processing_row(self) -> None:
        scenario_context = {
            "scenario": {
                "scenario_id": 100,
                "scenario_group_id": 20,
                "dimension_values": {"transport_disruption": "Suez disruption"},
            },
            "scenario_group": {
                "scenario_group_id": 20,
                "mi_event_id": 30,
                "event_type_l2_id": 17,
            },
            "event": {"mi_event_id": 30},
            "parameter_mapping_resources": {
                "mapping_rules": [
                    {
                        "event_type_l2_id": 17,
                        "dimension_key": "unmapped",
                        "canonical_parameter_name": "ShippingCost",
                        "mapping_method": "direct",
                    },
                ],
                "parameter_definitions": [
                    {
                        "parameter_name": "ShippingCost",
                        "model_file": "Trade",
                        "model_sheet": "ShippingCostInput",
                    },
                ],
            },
        }

        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
            service_cls.return_value.load_context.return_value = scenario_context

            with self.assertRaises(MIBaseError) as error:
                prepare_propose_parameters_callback(100)

        assert "No model parameter mapping candidates found" in (error.exception.error_message)
        service_cls.return_value.create_processing_proposal.assert_not_called()

    def test_prepare_callback_rejects_out_of_scope_mapping_before_processing_row(self) -> None:
        scenario_context = {
            "scenario": {
                "scenario_id": 100,
                "scenario_group_id": 20,
                "dimension_values": {"transport_disruption": "Suez disruption"},
            },
            "scenario_group": {
                "scenario_group_id": 20,
                "mi_event_id": 30,
                "event_type_l2_id": 17,
            },
            "event": {"mi_event_id": 30},
            "parameter_mapping_resources": {
                "mapping_rules": [
                    {
                        "event_type_l2_id": 17,
                        "dimension_key": "transport_disruption",
                        "canonical_parameter_name": "ShippingCost",
                        "mapping_method": "direct",
                    },
                ],
                "parameter_definitions": [
                    {
                        "parameter_name": "ShippingCost",
                        "model_file": "Trade",
                        "model_sheet": "ShippingCostInput",
                    },
                ],
            },
        }

        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
            service_cls.return_value.load_context.return_value = scenario_context

            with self.assertRaises(MIBaseError) as error:
                prepare_propose_parameters_callback(100)

        assert "No model parameter mapping candidates found" in error.exception.error_message
        service_cls.return_value.create_processing_proposal.assert_not_called()

    def test_v4_candidate_generation_failure_uses_two_line_public_message(self) -> None:
        scenario_context = {
            "scenario": {
                "scenario_id": 501,
                "scenario_group_id": 701,
                "title": "선적 미확대 속 냉방 타이트닝 재부각 심화",
                "dimension_values": {"liquefaction_path": "변화 없음"},
            },
            "scenario_group": {
                "scenario_group_id": 701,
                "generation_strategy": V4_GENERATION_STRATEGY,
            },
            "events": [
                {
                    "mi_event_id": 101,
                    "event_title_ko": "미국 Lower 48 폭염과 가스선물 반등",
                },
            ],
            "parameter_mapping_resources": {
                "mapping_rules": [],
                "parameter_definitions": [
                    {
                        "canonical_parameter_name": "LiqUtilAdjustment",
                        "parameter_name": "LiqUtilAdjustment",
                        "model_file": "Supply",
                        "model_sheet": "LiqUtilAdjustment",
                    },
                ],
            },
        }
        non_input_items = [
            {
                "reason_code": "UNCHANGED_LEVER_STATE",
                "lever_label": ("액화시설 가용성 " * 30) + "\n내부 진단",
            },
        ]

        with (
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
            ) as service_cls,
            patch(
                "apps.agents.model_parameter_agent.flows.propose_parameters.validation."
                "match_v4_parameter_candidates_from_rows",
                return_value=([], non_input_items, []),
            ),
        ):
            service_cls.return_value.load_context.return_value = scenario_context

            with self.assertRaises(MIBaseError) as error:
                prepare_propose_parameters_callback(501)

        _assert_v4_semantic_empty_error(
            error.exception,
            expected_title=V4_NO_CHANGE_TITLE,
        )
        assert "변화 없음" in error.exception.error_message
        service_cls.return_value.create_processing_proposal.assert_not_called()

    def test_prepare_callback_creates_processing_row_when_mapping_exists(self) -> None:
        scenario_context = {
            "scenario": {
                "scenario_id": 100,
                "scenario_group_id": 20,
                "dimension_values": {"economic_intensity": "downside"},
            },
            "scenario_group": {
                "scenario_group_id": 20,
                "mi_event_id": 30,
                "event_type_l2_id": 17,
            },
            "event": {"mi_event_id": 30},
            "parameter_mapping_resources": {
                "mapping_rules": [
                    {
                        "event_type_l2_id": 17,
                        "dimension_key": "economic_intensity",
                        "canonical_parameter_name": "GDP",
                        "mapping_method": "direct",
                    },
                ],
                "parameter_definitions": [
                    {
                        "parameter_name": "GDP",
                        "model_file": "Demand",
                        "model_sheet": "Demand Model Input",
                    },
                ],
            },
        }

        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
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
            "scenario": {
                "scenario_id": 100,
                "scenario_group_id": 20,
                "dimension_values": {"economic_intensity": "downside"},
            },
            "scenario_group": {
                "scenario_group_id": 20,
                "mi_event_id": 30,
                "event_type_l2_id": 17,
                "request_usr_id": 40,
            },
            "event": {"mi_event_id": 30},
            "parameter_mapping_resources": {
                "mapping_rules": [
                    {
                        "event_type_l2_id": 17,
                        "dimension_key": "economic_intensity",
                        "canonical_parameter_name": "GDP",
                        "mapping_method": "direct",
                    },
                ],
                "parameter_definitions": [
                    {
                        "parameter_name": "GDP",
                        "model_file": "Demand",
                        "model_sheet": "Demand Model Input",
                    },
                ],
            },
        }

        with patch(
            "apps.agents.model_parameter_agent.flows.propose_parameters.flow.ModelParameterService",
        ) as service_cls:
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
                                    "lut_value": 2.5,
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
                "lutValue": 2.5,
                "proposedValue": 3,
                "rationale": "Norway 2026 row 3% 차질",
            },
            {
                "Province Country": "Europe",
                "Year": 2026,
                "basecaseValue": None,
                "lutValue": None,
                "proposedValue": 0,
                "rationale": "Europe 2026 row 대체 공급 반영",
            },
        ]
        stored_parameters = service_cls.return_value.save_proposal_result.call_args.kwargs["proposal_parameters"]
        stored_payload = [parameter.model_dump(mode="json", by_alias=True) for parameter in stored_parameters]
        assert all("lutValue" not in value for parameter in stored_payload for value in parameter["values"])

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

        assert "No valid model parameter proposal parameters generated" in (error.exception.error_message)
        service_cls.return_value.save_proposal_result.assert_not_called()


class ModelParameterEntrypointTest(unittest.IsolatedAsyncioTestCase):
    async def test_lifespan_uses_configured_reference_precision(self) -> None:
        from apps.common.configs.config import get_settings
        import model_param as model_param_entrypoint

        cfg = get_settings().model_copy(
            update={
                "log_level": "INFO",
                "callback_oauth2_token_url": "",
                "model_parameter_lut_horizon_start_year": 2027,
                "model_parameter_lut_horizon_end_year": 2029,
                "model_parameter_basecase_value_max_decimal_places": 2,
                "model_parameter_basecase_value_precision_mode": "round",
                "model_parameter_lut_enabled": True,
            },
        )
        lut_registry = object()
        resource_paths = SimpleNamespace(
            source="packaged",
            resource_fingerprint=None,
            fallback_reason=None,
            resource_config_path=Path("config.yaml"),
            lut_registry=lut_registry,
            lut_root=Path("resources/model_parameter_lut"),
            basecase_dir=Path("resources/basecase"),
        )
        basecase_summary = SimpleNamespace(
            parameter_count=1,
            profile_count=1,
            sheet_available_count=1,
            record_count=1,
            warning_count=0,
            warnings=(),
        )
        ensure_runtime = AsyncMock(return_value=resource_paths)
        validate_lut_startup = MagicMock(return_value=(object(), None))
        preload_basecase = MagicMock(return_value=basecase_summary)

        with (
            patch(
                "apps.common.configs.config.get_settings",
                return_value=cfg,
            ),
            patch(
                "apps.connectors.mlflow.tracing.setup_mlflow_tracing",
            ),
            patch(
                "apps.agents.model_parameter_agent.utils.resource_bootstrap.ensure_model_parameter_resource_runtime",
                ensure_runtime,
            ),
            patch(
                "apps.agents.model_parameter_agent.utils.lut.validate_lut_startup",
                validate_lut_startup,
            ),
            patch(
                "apps.agents.model_parameter_agent.utils.basecase.preload_basecase_runtime_cache",
                preload_basecase,
            ),
            patch(
                "apps.agents.model_parameter_agent.utils.resource_runtime.clear_model_parameter_resource_runtime",
            ),
            patch.object(model_param_entrypoint, "setup_logging"),
            patch.object(model_param_entrypoint, "get_sync_engine"),
            patch.object(model_param_entrypoint, "validate_schema"),
        ):
            async with model_param_entrypoint.lifespan(model_param_entrypoint.app):
                pass

        policy = ensure_runtime.await_args.kwargs["lut_policy"]
        self.assertEqual(policy.start_year, 2027)
        self.assertEqual(policy.end_year, 2029)
        self.assertEqual(policy.value_max_decimal_places, 2)
        self.assertEqual(policy.value_precision_mode, "round")
        validate_lut_startup.assert_called_once_with(
            True,
            policy,
            registry=lut_registry,
        )
        preload_basecase.assert_called_once_with(
            str(resource_paths.basecase_dir),
            registry=lut_registry,
        )


class ModelParameterAgentLLMTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._settings_patch = patch.object(
            proposal_nodes,
            "get_settings",
            return_value=SimpleNamespace(
                llm_max_retries=1,
                llm_stream_enabled=False,
                llm_reasoning_effort="default",
                model_parameter_max_parameter_slots=100,
                model_parameter_max_value_prompt_basecase_records=100,
                model_parameter_max_routing_candidates_per_dimension=2,
                model_parameter_proposed_value_max_decimal_places=5,
                model_parameter_proposed_value_precision_mode="trunc",
            ),
        )
        self._settings_patch.start()
        self.addCleanup(self._settings_patch.stop)

    async def test_llm_call_logs_and_passes_stream_and_reasoning_options(self) -> None:
        captured_kwargs: dict[str, object] = {}

        async def fake_invoke(**kwargs):  # noqa: ANN003
            captured_kwargs.update(kwargs)
            return SimpleNamespace(result=None, usage=None)

        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        logger = Mock()
        settings = SimpleNamespace(
            llm_max_retries=3,
            llm_stream_enabled=True,
            llm_reasoning_effort="high",
            llm_timeout_sec=310,
            http_connect_timeout=10,
        )
        with (
            patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}),
            patch.object(proposal_nodes, "get_settings", return_value=settings),
            patch.object(proposal_nodes, "logger", logger),
        ):
            await proposal_nodes._invoke_structured(
                output_schema=LLMValueProposalResponse,
                messages=[{"role": "user", "content": "test"}],
                model_name="test-model",
            )

        assert captured_kwargs["stream"] is True
        assert captured_kwargs["reasoning_effort"] == "high"
        assert captured_kwargs["max_retries"] == 3
        log_args = logger.debug.call_args.args
        assert log_args[1:] == (
            "LLMValueProposalResponse",
            "test-model",
            True,
            "high",
            310,
            10,
            3,
        )

    async def test_single_population_route_can_be_excluded_by_candidate_validation(self) -> None:
        direct_candidate = {
            "candidate_key": "direct",
            "mapping_method": "direct",
            "source_dimension_id": "economic_intensity",
            "source_dimension_label": "경제 영향 강도",
            "source_dimension_value": "보통",
            "model_file": "Demand",
            "model_sheet": "GDP",
            "model_table": "Table1",
            "parameter_name": "GDP",
            "canonical_parameter_name": "GDP",
            "parameter_hint": "GDP 성장률 입력값입니다.",
            "semantic_axes": "Country, Year",
        }
        routing_candidate = {
            "candidate_key": "routing",
            "mapping_method": "routing",
            "event_type_l2_id": 21,
            "dimension_key": "economic_intensity",
            "source_dimension_id": "economic_intensity",
            "source_dimension_label": "경제 영향 강도",
            "source_dimension_value": "보통",
            "mapping_comment": ("이벤트에 인구·이민·인구전망 변화가 명시된 경우만 선택"),
            "model_file": "Demand",
            "model_sheet": "GDP",
            "model_table": "Table2",
            "parameter_name": "Population",
            "canonical_parameter_name": "Population",
            "parameter_hint": "국가별 인구 전망 입력값입니다.",
        }
        candidate_response = LLMCandidateValidationResponse(
            routing_decisions=[
                RoutingDecision(
                    dimension_key="economic_intensity",
                    selected_candidate_keys=[],
                ),
            ],
        )
        captured_messages: list[list[dict[str, str]]] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            captured_messages.append(kwargs["messages"])
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={
                "event": {
                    "event_title": "독일 제조업 둔화",
                    "event_summary": "주문 감소로 경기 하방 압력이 확대됐다.",
                },
                "scenario": {
                    "scenario_id": 100,
                    "scenario_title": "독일 경기 부진 지속",
                    "dimension_values": {"economic_intensity": "보통"},
                },
            },
            candidate_mappings=[direct_candidate, routing_candidate],
        )
        with (
            patch.object(proposal_nodes, "_invoke_structured", side_effect=fake_invoke),
            patch.object(proposal_nodes, "_debug_stage_payload") as debug_stage,
        ):
            result = await validate_parameter_candidates(state)

        assert [candidate["candidate_key"] for candidate in result["candidate_mappings"]] == ["direct"]
        assert result["validation_warnings"] == []
        assert len(captured_messages) == 1
        system_prompt = captured_messages[0][0]["content"]
        assert "0개부터 최대 2개" in system_prompt
        assert "명시적으로 확인할 수 없으면" in system_prompt
        payload = json.loads(captured_messages[0][1]["content"].split("\n", 1)[1])
        assert len(payload["routing_tasks"]) == 1
        assert payload["routing_tasks"][0]["dimension_key"] == "economic_intensity"
        assert [candidate["candidate_key"] for candidate in payload["routing_tasks"][0]["candidates"]] == ["routing"]
        debug_stage.assert_called_once_with(
            "step1.5.result",
            100,
            {
                "selection_method": "llm",
                "selected_parameters": ["GDP"],
            },
        )

    async def test_v4_step1_5_empty_routing_result_uses_two_line_public_message(self) -> None:
        candidate = {
            "candidate_key": "candidate_key-internal",
            "mapping_strategy": "v4",
            "mapping_method": "routing",
            "binding_role": "alternative",
            "scenario_dimension_key": "liquefaction_path",
            "source_dimension_id": "liquefaction_path",
            "source_dimension_label": "액화 경로",
            "source_dimension_value": "단기 회복",
            "source_dimension_value_id": "short_recovery",
            "lever_code": "liquefaction_availability",
            "lever_label": "액화시설 가용성",
            "model_file": "Supply",
            "model_sheet": "LiqProdAdjustment",
            "model_table": "table1",
            "parameter_name": "LiqProdAdjustment",
            "canonical_parameter_name": "LiqProdAdjustment",
        }
        _, routing_tasks = _partition_candidate_validation_work([candidate])
        candidate_response = LLMCandidateValidationResponse(
            routing_decisions=[
                RoutingDecision(
                    dimension_key=str(routing_tasks[0]["dimension_key"]),
                    selected_candidate_keys=[],
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=501,
            scenario_context={
                "scenario": {"scenario_id": 501, "scenario_group_id": 701},
                "scenario_group": {
                    "scenario_group_id": 701,
                    "generation_strategy": V4_GENERATION_STRATEGY,
                },
                "events": [{"mi_event_id": 101}],
            },
            candidate_mappings=[candidate],
        )
        with (
            patch.object(proposal_nodes, "_invoke_structured", side_effect=fake_invoke),
            patch.object(proposal_nodes, "_debug_stage_payload"),
        ):
            with self.assertRaises(MIBaseError) as error:
                await validate_parameter_candidates(state)

        _assert_v4_semantic_empty_error(
            error.exception,
            expected_title=V4_NO_CHANGE_TITLE,
        )
        assert "액화설비 생산량 파라미터 후보" in error.exception.error_message

    @core_contract
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

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("direct 후보는 LLM을 호출하지 않아야 합니다")

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
        assert result["validation_warnings"] == []

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

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            raise AssertionError("direct 후보는 LLM을 호출하지 않아야 합니다")

        state = ModelParameterProposalState(
            scenario_id=283,
            scenario_context={"scenario": {"scenario_id": 283}},
            candidate_mappings=candidates,
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with (
            patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}),
            patch.object(proposal_nodes, "_debug_stage_payload"),
        ):
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

    @core_contract
    async def test_llm_candidate_validation_omitted_routing_candidate_is_excluded(self) -> None:
        candidates = [
            {
                "candidate_key": "c1",
                "mapping_method": "routing",
                "dimension_key": "affected_facility_type",
                "source_dimension_id": "affected_facility_type",
                "source_dimension_value": "수입 시설",
                "mapping_comment": "수입 시설이면 발전 믹스 검토",
                "model_file": "Demand",
                "model_sheet": "PowerMixAdjustment",
                "parameter_name": "PowerMix",
                "canonical_parameter_name": "PowerMix",
            },
            {
                "candidate_key": "c2",
                "mapping_method": "routing",
                "dimension_key": "affected_facility_type",
                "source_dimension_id": "affected_facility_type",
                "source_dimension_value": "수입 시설",
                "mapping_comment": "수입 시설이면 운송비 검토",
                "model_file": "Trade",
                "model_sheet": "ShippingCostInput",
                "parameter_name": "ShippingCost",
                "canonical_parameter_name": "ShippingCost",
            },
        ]
        candidate_response = LLMCandidateValidationResponse(
            routing_decisions=[
                RoutingDecision(
                    dimension_key="affected_facility_type",
                    selected_candidate_keys=["c1"],
                ),
            ],
        )
        captured_messages: list[list[dict[str, str]]] = []

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMCandidateValidationResponse
            captured_messages.append(kwargs["messages"])
            return SimpleNamespace(result=candidate_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=100,
            scenario_context={"scenario": {"scenario_id": 100}},
            candidate_mappings=candidates,
        )
        with (
            patch.object(
                proposal_nodes,
                "get_settings",
                return_value=SimpleNamespace(
                    model_parameter_max_routing_candidates_per_dimension=3,
                ),
            ),
            patch.object(proposal_nodes, "_invoke_structured", side_effect=fake_invoke),
            patch.object(proposal_nodes, "_debug_stage_payload") as debug_stage,
        ):
            result = await validate_parameter_candidates(state)

        assert [candidate["candidate_key"] for candidate in result["candidate_mappings"]] == ["c1"]
        assert result["validation_warnings"] == []
        assert len(captured_messages) == 1
        debug_stage.assert_called_once_with(
            "step1.5.result",
            100,
            {
                "selection_method": "llm",
                "selected_parameters": ["PowerMix"],
            },
        )
        system_prompt = captured_messages[0][0]["content"]
        assert "각 task에서 0개부터 최대 3개" in system_prompt
        assert "direct parameter는 서버에서 이미 처리" in system_prompt
        payload = json.loads(captured_messages[0][1]["content"].split("\n", 1)[1])
        assert len(payload["routing_tasks"]) == 1
        assert payload["routing_tasks"][0]["dimension_key"] == "affected_facility_type"
        assert [candidate["mapping_comment"] for candidate in payload["routing_tasks"][0]["candidates"]] == [
            "수입 시설이면 발전 믹스 검토",
            "수입 시설이면 운송비 검토",
        ]
        assert "model_file" not in json.dumps(payload, ensure_ascii=False)

    async def test_routing_decision_limit_is_enforced_per_unique_dimension(self) -> None:
        candidates = [{"candidate_key": f"c{index}"} for index in range(1, 5)]
        routing_tasks = [
            {
                "dimension_key": "affected_facility_type",
                "candidates": candidates,
            },
        ]

        selected, warnings = proposal_nodes._sanitize_routing_decisions(
            [
                RoutingDecision(
                    dimension_key="affected_facility_type",
                    selected_candidate_keys=["c1", "c2", "c3", "c4"],
                ),
            ],
            routing_tasks,
            max_candidates_per_dimension=2,
        )

        assert [candidate["candidate_key"] for candidate in selected] == ["c1", "c2"]
        assert len(warnings) == 2
        assert all("선택 상한을 초과" in warning for warning in warnings)

        selected, warnings = proposal_nodes._sanitize_routing_decisions(
            [
                RoutingDecision(
                    dimension_key="affected_facility_type",
                    selected_candidate_keys=["c1"],
                ),
                RoutingDecision(
                    dimension_key="affected_facility_type",
                    selected_candidate_keys=["c2", "c3"],
                ),
            ],
            routing_tasks,
            max_candidates_per_dimension=2,
        )

        assert [candidate["candidate_key"] for candidate in selected] == ["c1"]
        assert len(warnings) == 1
        assert "중복 dimension task" in warnings[0]

    async def test_routing_decision_is_not_overridden_by_server_comment_logic(self) -> None:
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
            routing_decisions=[
                RoutingDecision(
                    dimension_key="affected_facility_type",
                    selected_candidate_keys=[liq_candidate["candidate_key"]],
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
            liq_candidate["candidate_key"],
        ]
        assert result["validation_warnings"] == []

    @core_contract
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
                    slot_axes=[
                        LLMSlotAxis(
                            axis_name="Year",
                            axis_value=2026,
                        ),
                    ],
                ),
            ],
        )
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                LLMValueAdjustment(
                    candidate_key="c1",
                    slot_values=[
                        LLMValueCell(
                            slot_key="slot-1",
                            proposed_value=1.2,
                            rationale_ko=(
                                "2026년 ShippingCost basecase record를 선택했고, "
                                "운송 차질 scenario dimension을 반영해 최종 입력값을 1.2로 산정했습니다."
                            ),
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
            slot_catalog=[
                {
                    "candidate_key": "c1",
                    "parameter_name": "ShippingCost",
                    "key_axes": ["Year"],
                    "fixed_axis_names": [],
                    "time_axis_names": ["Year"],
                    "leaves": [
                        {
                            "fixed_axes": {},
                            "available_periods": [{"Year": 2026}],
                        },
                    ],
                },
            ],
            effective_references=[
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
        assert "slots[].slot_key" in captured_value_system_contents[0]
        task = value_payload["parameter_value_tasks"][0]
        assert task["parameter"] == {
            "candidate_key": "c1",
            "parameter_name": "ShippingCost",
            "parameter_hint": "운송 차질 시 비용 입력값을 조정합니다.",
        }
        assert "model_file" not in task
        assert "model_sheet" not in task
        assert "model_table" not in json.dumps(value_payload, ensure_ascii=False)
        assert "slot_rationale_ko" not in json.dumps(value_payload, ensure_ascii=False)
        assert task["slots"] == [
            {
                "slot_key": "slot-1",
                "coordinates": {"Year": 2026},
                "reference_value": 1.0,
            },
        ]
        assert adjustment["model_file"] == "Trade"
        assert adjustment["model_sheet"] == "ShippingCostInput"
        assert adjustment["parameter_name"] == "ShippingCost"
        assert adjustment["slot_axes"][0]["axis_name"] == "Year"
        assert adjustment["parameter_selection_rationale_ko"].startswith("운송 차질")
        assert adjustment["value_grid"][0]["basecase_value"] == 1.0
        assert adjustment["value_grid"][0]["basecase_reference_ids"] == ["ref1"]
        assert "2026년 ShippingCost" in adjustment["value_grid"][0]["rationale_ko"]
        assert "value_selection_rationale_ko" not in adjustment["value_grid"][0]
        assert "proposed_value_rationale_ko" not in adjustment["value_grid"][0]
        assert len(result["parameter_adjustments"]) == 1

    @core_contract
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
        slot_response = LLMSlotProposalResponse(
            parameter_slots=[
                LLMSlotProposal(
                    candidate_key="c1",
                    slot_axes=[
                        LLMSlotAxis(
                            axis_name="Plant",
                            axis_value="Plant-42",
                        ),
                    ],
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
            slot_catalog=[
                {
                    "candidate_key": "c1",
                    "parameter_name": "LiqUtilAdjustment",
                    "key_axes": ["Plant", "Year"],
                    "fixed_axis_names": ["Plant"],
                    "time_axis_names": ["Year"],
                    "leaves": [
                        {
                            "fixed_axes": {"Plant": "Cameron"},
                            "available_periods": [{"Year": 2026}],
                        },
                        {
                            "fixed_axes": {"Plant": "Sabine"},
                            "available_periods": [{"Year": 2027}],
                        },
                    ],
                },
            ],
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_slots(state)

        assert result["parameter_slots"][0]["candidate_key"] == "c1"
        assert "rationale_ko" not in result["parameter_slots"][0]
        assert "rationale_ko" not in LLMSlotProposal.model_json_schema()["properties"]
        assert captured_contents
        assert captured_system_contents
        system_prompt = captured_system_contents[0]
        assert "Basecase 또는 LUT value가 존재하는" in system_prompt
        assert "value, 변경 방향, 변경 폭, 기준값을 판단하지 않습니다" in system_prompt
        assert "parameter별 최대 100개" in system_prompt
        assert "100개는 hard maximum이며 목표 개수나 권장 개수가 아닙니다" in system_prompt
        assert "연관된 slot이 하나 이상 있으면 해당 parameter에서 최소 1개" in system_prompt
        assert "Cartesian product를 만들지 마십시오" in system_prompt
        assert "axis_name이 Year, Month, Period이면 axis_value를 JSON integer" in system_prompt
        assert "각 항목에는 candidate_key와 slot_axes만 반환하십시오" in system_prompt
        assert "rationale_ko, selected, metadata, warning 필드는 반환하지 마십시오" in system_prompt
        assert "rationale_ko에는" not in system_prompt
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
            "allowed_slot_axes_field_names": ["Plant", "Year"],
        }
        assert "model_file" not in json.dumps(payload, ensure_ascii=False)
        assert "model_sheet" not in json.dumps(payload, ensure_ascii=False)
        assert "model_table" not in json.dumps(payload, ensure_ascii=False)
        assert task["slot_catalog"] == {
            "parameter_name": "LiqUtilAdjustment",
            "key_axes": ["Plant", "Year"],
            "fixed_axis_names": ["Plant"],
            "time_axis_names": ["Year"],
            "leaves": [
                {
                    "fixed_axes": {"Plant": "Cameron"},
                    "available_periods": [{"Year": 2026}],
                },
                {
                    "fixed_axes": {"Plant": "Sabine"},
                    "available_periods": [{"Year": 2027}],
                },
            ],
        }
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

    @core_contract
    def test_value_tasks_use_one_reference_value_per_server_slot_key(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
        }
        slots = [
            {
                "candidate_key": "c1",
                "slot_axes": [
                    {"axis_name": "Country", "axis_value": "Russia"},
                    {"axis_name": "Year", "axis_value": 2026},
                    {"axis_name": "Month", "axis_value": 7},
                ],
            },
        ]
        references = [
            {
                "candidate_key": "c1",
                "reference_id": "r1",
                "axes": {"Country": "Russia", "Year": 2026, "Month": 7},
                "value": 0.45,
            },
        ]

        tasks = proposal_nodes._build_parameter_value_tasks(
            [candidate],
            slots,
            references,
            [],
        )

        assert tasks[0]["slots"] == [
            {
                "slot_key": "slot-1",
                "coordinates": {"Country": "Russia", "Year": 2026, "Month": 7},
                "reference_value": 0.45,
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
                LLMSlotProposal(
                    candidate_key="temperature-direct",
                    slot_axes=[
                        LLMSlotAxis(axis_name="Country", axis_value="Japan"),
                        LLMSlotAxis(axis_name="Year", axis_value="2026"),
                        LLMSlotAxis(axis_name="Month", axis_value="8"),
                    ],
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
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_slots(state)

        assert requested_schemas == ["LLMSlotProposalResponse"]
        assert result["parameter_slots"][0]["candidate_key"] == "temperature-direct"
        assert result["parameter_slots"][0]["slot_axes"][0]["axis_value"] == "Japan"

    @core_contract
    def test_exact_slot_filter_requires_basecase_index(self) -> None:
        state = ModelParameterProposalState(
            scenario_id=100,
            parameter_slots=[
                {
                    "candidate_key": "c1",
                    "slot_axes": [
                        {"axis_name": "Plant", "axis_value": "Cameron"},
                    ],
                },
            ],
        )

        with self.assertRaises(MIBaseError) as error:
            filter_basecase_records_by_slots(state)

        assert "BasecaseIndex is required" in error.exception.error_message

    def test_v4_step2_empty_slots_use_two_line_public_message(self) -> None:
        utilization_candidate = {
            "candidate_key": "candidate_key-internal",
            "mapping_strategy": "v4",
            "mapping_method": "routing",
            "lever_label": "액화시설 가용성",
            "model_file": "Supply",
            "model_sheet": "LiqUtilAdjustment",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
        }
        production_candidate = {
            **utilization_candidate,
            "candidate_key": "candidate_key-production-internal",
            "model_sheet": "LiqProdAdjustment",
            "parameter_name": "LiqProdAdjustment",
            "canonical_parameter_name": "LiqProdAdjustment",
        }
        state = ModelParameterProposalState(
            scenario_id=501,
            scenario_context={
                "scenario": {"scenario_id": 501, "scenario_group_id": 701},
                "scenario_group": {
                    "scenario_group_id": 701,
                    "generation_strategy": V4_GENERATION_STRATEGY,
                },
                "events": [{"mi_event_id": 101}],
            },
            candidate_mappings=[utilization_candidate, production_candidate],
            parameter_slots=[],
        )

        with self.assertRaises(MIBaseError) as error:
            finalize_empty_parameter_values(state)

        _assert_v4_semantic_empty_error(
            error.exception,
            expected_title=V4_NO_MODEL_INPUT_TITLE,
        )
        assert "액화설비 가동률과 생산량 파라미터" in error.exception.error_message
        assert "대상과 적용 기간" in error.exception.error_message

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
                LLMSlotProposal(
                    candidate_key="c1",
                    slot_axes=[
                        LLMSlotAxis(
                            axis_name="Year",
                            axis_value="미정(후보: 2024)",
                        ),
                    ],
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
        )
        fake_module = types.ModuleType("apps.connectors.llm.llm_client")
        fake_module.invoke_llm_structured_output = fake_invoke
        with patch.dict(sys.modules, {"apps.connectors.llm.llm_client": fake_module}):
            result = await propose_parameter_slots(state)

        assert result["parameter_slots"] == []
        assert any("모호한 slot" in warning for warning in result["validation_warnings"])

    async def test_llm_value_sanitizer_rejects_unknown_slot_key(self) -> None:
        candidate = {
            "candidate_key": "c1",
            "model_file": "Supply",
            "model_sheet": "VolumeAdjustment",
            "parameter_name": "SupplyDisruption",
            "canonical_parameter_name": "SupplyDisruption",
        }
        slots = [
            {
                "candidate_key": "c1",
                "slot_key": "slot-1",
                "slot_axes": [
                    {"axis_name": "Province Country", "axis_value": "Norway"},
                    {"axis_name": "Year", "axis_value": 2026},
                ],
            },
        ]
        references = [
            {
                "candidate_key": "c1",
                "slot_key": "slot-1",
                "axes": {"Province Country": "Norway", "Year": 2026},
                "value": 0.02,
                "reference_id": "ref-1",
            },
        ]
        adjustment = LLMValueAdjustment(
            candidate_key="c1",
            slot_values=[
                LLMValueCell(
                    slot_key="slot-unknown",
                    proposed_value=0.01,
                    rationale_ko="알 수 없는 slot",
                ),
            ],
            rationale_ko="공급 차질 조정이 필요합니다.",
        )

        sanitized, warnings = proposal_nodes._sanitize_llm_adjustments(
            [adjustment],
            [candidate],
            slots,
            references,
        )

        assert sanitized == []
        assert any("slotKey가 요청 목록에 없어" in warning for warning in warnings)

    async def test_v4_step3_empty_values_use_two_line_public_message(self) -> None:
        candidate = {
            "candidate_key": "candidate_key-internal",
            "mapping_strategy": "v4",
            "mapping_method": "routing",
            "lever_label": "액화시설 가용성",
            "model_file": "Supply",
            "model_sheet": "LiqUtilAdjustment",
            "parameter_name": "LiqUtilAdjustment",
            "canonical_parameter_name": "LiqUtilAdjustment",
        }
        slots = [
            {
                "candidate_key": "candidate_key-internal",
                "slot_key": "slot-1",
                "slot_axes": [
                    {"axis_name": "LNG Plant Train", "axis_value": "Corpus Christi Stage 3 T1"},
                    {"axis_name": "Year", "axis_value": 2026},
                    {"axis_name": "Month", "axis_value": 8},
                ],
            },
        ]
        references = [
            {
                "candidate_key": "candidate_key-internal",
                "slot_key": "slot-1",
                "axes": {
                    "LNG Plant Train": "Corpus Christi Stage 3 T1",
                    "Year": 2026,
                    "Month": 8,
                },
                "actual_basecase_value": 0.90738,
                "lut_default_value": 0.90738,
                "llm_reference_value": 0.90738,
                "basecase_reference_id": "basecase-reference-internal",
            },
        ]
        value_response = LLMValueProposalResponse(
            parameter_adjustments=[
                LLMValueAdjustment(
                    candidate_key="candidate_key-internal",
                    slot_values=[
                        LLMValueCell(
                            slot_key="slot-1",
                            proposed_value=None,
                            rationale_ko="적용 수치를 확정할 근거가 부족합니다.",
                        ),
                    ],
                    rationale_ko="액화시설 가동률을 검토했습니다.",
                ),
            ],
        )

        async def fake_invoke(*args, **kwargs):  # noqa: ANN002, ANN003
            assert kwargs["output_schema"] is LLMValueProposalResponse
            return SimpleNamespace(result=value_response, usage=None)

        state = ModelParameterProposalState(
            scenario_id=501,
            scenario_context={
                "scenario": {"scenario_id": 501, "scenario_group_id": 701},
                "scenario_group": {
                    "scenario_group_id": 701,
                    "generation_strategy": V4_GENERATION_STRATEGY,
                },
                "events": [{"mi_event_id": 101}],
            },
            candidate_mappings=[candidate],
            slot_candidate_mappings=[candidate],
            parameter_slots=slots,
            effective_references=references,
        )
        with (
            patch.object(
                proposal_nodes,
                "_build_value_proposal_prompt_packet",
                return_value={"parameter_value_tasks": [{}]},
            ),
            patch.object(proposal_nodes, "_invoke_structured", side_effect=fake_invoke),
            patch.object(proposal_nodes, "_debug_stage_payload"),
        ):
            with self.assertRaises(MIBaseError) as error:
                await propose_parameter_values(state)

        _assert_v4_semantic_empty_error(
            error.exception,
            expected_title=V4_NO_PARAMETER_VALUE_TITLE,
        )
        assert "액화설비 가동률 파라미터와 모델 입력 위치" in error.exception.error_message
        assert "기준값" in error.exception.error_message

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

    @core_contract
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

    def test_model_parameter_service_persists_unknown_parameter_metadata(self) -> None:
        confirmation_parameters = [
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
        ]
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
                    "apps.common.configs.database.sync_database.connection": (fake_connection_module),
                },
            ),
            patch(
                "apps.agents.model_parameter_agent.persistence.model_parameter_service.ModelParameterRepository",
            ) as repository_cls,
        ):
            repository = repository_cls.return_value
            repository.fetch_model_param_proposal_for_update.return_value = {
                "model_param_proposal_id": 901,
                "status": "PROPOSED",
            }

            result = ModelParameterService().confirm_proposal_result(
                model_param_proposal_id=901,
                user_id=56,
                confirmation_parameters=confirmation_parameters,
            )

        persisted = repository.confirm_model_param_proposal.call_args.kwargs["confirmation_parameters"]
        assert result["status"] == "CONFIRMED"
        assert persisted[0]["parameterName"] == "UserCustomParameter"
        assert persisted[0]["modelTarget"]["modelFile"] == "Custom"
        assert persisted[0]["values"][0]["CustomSlot"] == "A"
        fake_session.commit.assert_called_once()
        fake_session.rollback.assert_not_called()

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

        assert parsed.data.confirmation_parameters[0].model_target.model_sheet == ("PowerMixAdjustment")

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

        assert "modelTarget.modelSheet must be 'PowerMixAdjustment'" in (error.exception.error_message)
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
            if isinstance(route, APIRoute) and route.path == "/model-parameters/scenarios/{scenario_id}/proposals"
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

    def test_proposal_callback_error_payload_includes_failed_context(self) -> None:
        payload = _callback_error_output(
            message="insufficient dimension mapping for event 1378",
            model_param_proposal_id=10001,
            scenario_id=309,
            scenario_group_id=61,
            event_id=1378,
        )

        assert payload.model_dump(by_alias=True) == {
            "status": "error",
            "message": "insufficient dimension mapping for event 1378",
            "data": {
                "modelParamProposalId": 10001,
                "scenarioId": 309,
                "scenarioGroupId": 61,
                "eventId": 1378,
                "status": "FAILED",
            },
        }

    async def test_async_proposal_accept_offloads_sync_prepare(self) -> None:
        from apps.agents.model_parameter_agent import api as model_parameter_api

        scheduled: list[tuple[object, dict[str, object]]] = []

        class FakeBackgroundTasks:
            def add_task(self, func: object, **kwargs: object) -> None:
                scheduled.append((func, kwargs))

        offloaded: list[tuple[object, tuple[object, ...], dict[str, object]]] = []

        async def fake_to_thread(func: object, *args: object, **kwargs: object) -> object:
            offloaded.append((func, args, kwargs))
            return func(*args, **kwargs)  # type: ignore[operator]

        prepared = {
            "model_param_proposal_id": 10001,
            "scenario_id": 309,
            "scenario_group_id": 61,
            "event_id": 1378,
        }
        with (
            patch.object(
                model_parameter_api,
                "prepare_propose_parameters_callback",
                return_value=prepared,
            ) as prepare,
            patch.object(
                model_parameter_api.asyncio,
                "to_thread",
                side_effect=fake_to_thread,
            ),
        ):
            response = await model_parameter_api.propose_parameters(
                309,
                FakeBackgroundTasks(),  # type: ignore[arg-type]
                ProposeParametersRequest(user_id=77),
            )

        assert offloaded == [(prepare, (309,), {"user_id": 77})]
        assert response.data.model_param_proposal_id == 10001
        assert len(scheduled) == 1

    @core_contract
    async def test_background_failure_callback_contains_failed_context(self) -> None:
        class FakeGraph:
            async def ainvoke(self, state: ModelParameterProposalState, **kwargs: object) -> dict[str, object]:
                assert state.scenario_id == 309
                raise ValueError("value proposal failed")

        class FakeModelParameterService:
            def __init__(self) -> None:
                self.failures: list[dict[str, object]] = []
                self.callback_statuses: list[str] = []

            def complete_proposal_result(self, **kwargs: object) -> None:
                raise AssertionError(f"unexpected proposal completion: {kwargs}")

            def fail_proposal_result(self, **kwargs: object) -> None:
                self.failures.append(kwargs)

            def update_callback_status(
                self,
                *,
                model_param_proposal_id: int,
                callback_status: str,
            ) -> None:
                assert model_param_proposal_id == 10001
                self.callback_statuses.append(callback_status)

        service = FakeModelParameterService()
        sent_payloads: list[dict[str, object]] = []

        async def fake_send_callback(_url: str, payload: object) -> None:
            sent_payloads.append(payload.model_dump(by_alias=True))  # type: ignore[attr-defined]

        settings = SimpleNamespace(
            callback_base_url="https://callback.example",
            callback_model_parameter_proposals_path="/scenarios/{scenario_id}/callback",
            skip_callback=False,
        )
        fake_config_module = types.ModuleType("apps.common.configs.config")
        fake_config_module.get_settings = lambda: settings

        with (
            patch.dict(sys.modules, {"apps.common.configs.config": fake_config_module}),
            patch.object(propose_flow, "build_graph", return_value=FakeGraph()),
            patch.object(propose_flow, "ModelParameterService", return_value=service),
            patch.object(propose_flow, "send_callback", side_effect=fake_send_callback),
        ):
            await propose_flow.run_propose_parameters_background(
                model_param_proposal_id=10001,
                scenario_id=309,
                scenario_group_id=61,
                event_id=1378,
            )

        assert service.failures == [
            {
                "model_param_proposal_id": 10001,
                "error_code": "ValueError",
                "error_message": "value proposal failed",
            },
        ]
        assert service.callback_statuses == ["SUCCEEDED"]
        assert sent_payloads == [
            {
                "status": "error",
                "message": "value proposal failed",
                "data": {
                    "modelParamProposalId": 10001,
                    "scenarioId": 309,
                    "scenarioGroupId": 61,
                    "eventId": 1378,
                    "status": "FAILED",
                },
            },
        ]

    async def test_v4_semantic_failure_uses_same_clean_message_for_db_and_callback(self) -> None:
        with pytest.raises(MIBaseError) as caught:
            _raise_v4_semantic_empty_if_applicable(
                stage="step2",
                scenario_context={
                    "scenario": {"scenario_id": 501, "scenario_group_id": 701},
                    "scenario_group": {
                        "scenario_group_id": 701,
                        "generation_strategy": V4_GENERATION_STRATEGY,
                    },
                    "events": [{"mi_event_id": 101}],
                },
                candidates=[{"lever_label": "액화시설 가용성"}],
            )
        semantic_error = caught.value
        _assert_v4_semantic_empty_error(
            semantic_error,
            expected_title=V4_NO_MODEL_INPUT_TITLE,
        )

        class FakeGraph:
            async def ainvoke(self, state: ModelParameterProposalState, **kwargs: object) -> dict[str, object]:
                assert state.scenario_id == 501
                raise semantic_error

        class FakeModelParameterService:
            def __init__(self) -> None:
                self.failures: list[dict[str, object]] = []

            def complete_proposal_result(self, **kwargs: object) -> None:
                raise AssertionError(f"unexpected proposal completion: {kwargs}")

            def fail_proposal_result(self, **kwargs: object) -> None:
                self.failures.append(kwargs)

            def update_callback_status(self, **kwargs: object) -> None:
                assert kwargs == {
                    "model_param_proposal_id": 10001,
                    "callback_status": "SUCCEEDED",
                }

        service = FakeModelParameterService()
        sent_payloads: list[dict[str, object]] = []

        async def fake_send_callback(_url: str, payload: object) -> None:
            sent_payloads.append(payload.model_dump(by_alias=True))  # type: ignore[attr-defined]

        settings = SimpleNamespace(
            callback_base_url="https://callback.example",
            callback_model_parameter_proposals_path="/scenarios/{scenario_id}/callback",
            skip_callback=False,
        )
        fake_config_module = types.ModuleType("apps.common.configs.config")
        fake_config_module.get_settings = lambda: settings

        with (
            patch.dict(sys.modules, {"apps.common.configs.config": fake_config_module}),
            patch.object(propose_flow, "build_graph", return_value=FakeGraph()),
            patch.object(propose_flow, "ModelParameterService", return_value=service),
            patch.object(propose_flow, "send_callback", side_effect=fake_send_callback),
        ):
            await propose_flow.run_propose_parameters_background(
                model_param_proposal_id=10001,
                scenario_id=501,
                scenario_group_id=701,
                event_id=None,
            )

        assert service.failures == [
            {
                "model_param_proposal_id": 10001,
                "error_code": "INVALID_REQUEST",
                "error_message": semantic_error.error_message,
            },
        ]
        assert sent_payloads[0]["message"] == semantic_error.error_message
        assert sent_payloads[0]["data"] == {
            "modelParamProposalId": 10001,
            "scenarioId": 501,
            "scenarioGroupId": 701,
            "eventId": None,
            "status": "FAILED",
        }

    async def test_background_marks_callback_skipped_when_skip_callback_enabled(self) -> None:
        class FakeGraph:
            async def ainvoke(self, state: ModelParameterProposalState, **kwargs: object) -> dict[str, object]:
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
            async def ainvoke(self, state: ModelParameterProposalState, **kwargs: object) -> dict[str, object]:
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
