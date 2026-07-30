from __future__ import annotations

from apps.agents.model_parameter_agent.flows.propose_parameters.nodes import (
    _match_v4_lever_candidates,
)
from apps.agents.model_parameter_agent.utils.parameter_mapping import (
    ParameterDefinition,
    ParameterKnowledgeBase,
)


def _knowledge_base() -> ParameterKnowledgeBase:
    definition = ParameterDefinition(
        canonical_parameter_name="Temperature",
        parameter_hint="국가별 기온",
        model_file="Demand",
        model_sheet="WeatherAdjustment",
        model_table="Weather",
        parameter_name="Temperature",
        semantic_axes="Country,Year,Month",
        basecase_read_mode="fixed_columns",
        basecase_header_row=6,
        basecase_data_start_row=7,
        basecase_column_roles="K:Year,L:Month,M:Country,O:Temperature",
        basecase_row_filter=None,
        basecase_year_row=None,
        basecase_month_row=None,
        basecase_period_row=None,
        basecase_value_start_col=None,
        basecase_value_end_col=None,
        basecase_stop_rule="blank",
    )
    return ParameterKnowledgeBase(
        mapping_source="test",
        basecase_dir_path="/tmp",
        parameter_definitions={"Temperature": definition},
        mapping_rules=[],
        basecase_profiles={},
    )


def test_v4_mapping_uses_executable_bindings_and_preserves_unsupported_items() -> None:
    context = {
        "scenario": {
            "dimension_values": {
                "cold_wave_intensity": "strong",
                "contract_flexibility": "restricted",
                "risk_premium": "high",
            },
        },
        "scenario_group": {
            "generation_strategy": "multi_event_model_lever_dimensions",
            "dimension_definitions": [
                {
                    "dimension_id": "cold_wave_intensity",
                    "label": "한파 강도",
                    "source_event_ids": [101],
                    "lever_refs": ["weather_demand"],
                },
                {
                    "dimension_id": "contract_flexibility",
                    "label": "계약 유연성",
                    "source_event_ids": [202],
                    "lever_refs": ["contract_volume"],
                },
                {
                    "dimension_id": "risk_premium",
                    "label": "위험 프리미엄",
                    "source_event_ids": [101, 202],
                    "lever_refs": ["financial_market_sentiment"],
                },
            ],
        },
        "impact_lever_catalog": [
            {
                "lever_code": "weather_demand",
                "domain": "demand",
                "parameter_bindings": [
                    {
                        "parameter_name": "Temperature",
                        "support_status": "executable",
                        "applicability": "국가·연·월 기온",
                    },
                ],
            },
            {
                "lever_code": "contract_volume",
                "domain": "trade",
                "parameter_bindings": [],
            },
            {
                "lever_code": "financial_market_sentiment",
                "domain": "price_only",
                "parameter_bindings": [],
            },
        ],
    }

    candidates, non_inputs, warnings = _match_v4_lever_candidates(
        _knowledge_base(),
        context,
    )

    assert warnings == []
    assert len(candidates) == 1
    assert candidates[0]["canonical_parameter_name"] == "Temperature"
    assert candidates[0]["mapping_method"] == "direct"
    assert candidates[0]["source_event_ids"] == [101]
    assert non_inputs == [
        {
            "source_dimension_id": "contract_flexibility",
            "source_dimension_label": "계약 유연성",
            "source_dimension_value": "restricted",
            "lever_code": "contract_volume",
            "mapping_method": "known_unsupported",
            "unsupported_reason_code": "NO_PARAMETER_BINDING",
            "reason": "현재 수급모델 parameter master에 직접 연결할 파라미터가 정의되지 않았습니다.",
        },
        {
            "source_dimension_id": "risk_premium",
            "source_dimension_label": "위험 프리미엄",
            "source_dimension_value": "high",
            "lever_code": "financial_market_sentiment",
            "mapping_method": "price_only",
            "unsupported_reason_code": "PRICE_ONLY",
            "reason": ("LNG 가격 시나리오에는 반영되지만 현재 수급모델 입력 파라미터로 직접 연결되지 않습니다."),
        },
    ]


def test_v4_mapping_distinguishes_inactive_parameter_from_missing_binding() -> None:
    context = {
        "scenario": {
            "dimension_values": {
                "cold_wave_intensity": "strong",
            },
        },
        "scenario_group": {
            "generation_strategy": "multi_event_model_lever_dimensions",
            "dimension_definitions": [
                {
                    "dimension_id": "cold_wave_intensity",
                    "label": "한파 강도",
                    "source_event_ids": [101],
                    "lever_refs": ["weather_demand"],
                },
            ],
        },
        "impact_lever_catalog": [
            {
                "lever_code": "weather_demand",
                "domain": "demand",
                "parameter_bindings": [
                    {
                        "parameter_name": "HDD",
                        "support_status": "known_unsupported",
                        "unsupported_reason_code": "INACTIVE_MODEL_PARAMETER",
                        "applicability": "난방도일",
                    },
                ],
            },
        ],
    }

    candidates, non_inputs, warnings = _match_v4_lever_candidates(
        _knowledge_base(),
        context,
    )

    assert candidates == []
    assert warnings == [
        "v4 impact lever catalog에서 실행 가능한 모델 파라미터 후보를 찾지 못했습니다.",
    ]
    assert non_inputs == [
        {
            "source_dimension_id": "cold_wave_intensity",
            "source_dimension_label": "한파 강도",
            "source_dimension_value": "strong",
            "lever_code": "weather_demand",
            "parameter_name": "HDD",
            "mapping_method": "known_unsupported",
            "unsupported_reason_code": "INACTIVE_MODEL_PARAMETER",
            "reason": "난방도일",
        },
    ]
