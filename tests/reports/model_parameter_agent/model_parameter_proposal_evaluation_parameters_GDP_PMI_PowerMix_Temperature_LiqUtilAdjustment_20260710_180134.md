# Model Parameter Proposal Evaluation - Parameters

- 실행 시작: 2026-07-10T18:01:34
- 실행 종료: 2026-07-10T18:03:48
- 총 소요시간: 02:13.374 (133.374s)
- 대상 event_type_l2_ids: [2, 5, 6, 21]
- 대상 parameters: ['GDP', 'PMI', 'PowerMix', 'Temperature', 'LiqUtilAdjustment']
- concurrency: 2
- retries: 1
- parameter_scenarios: {'GDP': 305, 'PMI': 306, 'PowerMix': 287, 'Temperature': 289, 'LiqUtilAdjustment': 105}
- planned scenario executions: 5
- 대상 수집 방식: 명시적 parameter=scenario_id를 검증하고 midb에서 event/group context 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=2 터미널 Utilization 변동: scenario_group 1개, scenario 1개
- event_type_l2_id=5 발전소 Utilization 변동: scenario_group 1개, scenario 1개
- event_type_l2_id=6 겨울 한파: scenario_group 1개, scenario 1개
- event_type_l2_id=21 국가별 경기: scenario_group 1개, scenario 2개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 2 | 18 | 105 | OK | 1 | 00:33.604 | 33.604s |
| 5 | 51 | 287 | OK | 1 | 00:26.060 | 26.060s |
| 6 | 52 | 289 | OK | 1 | 01:06.735 | 66.735s |
| 21 | 60 | 305 | OK | 1 | 00:40.562 | 40.562s |
| 21 | 60 | 306 | OK | 1 | 01:18.006 | 78.006s |

## Reference Runtime Summary

```json
[
  {
    "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
    "reference_diagnostics": {
      "cell_validation": {
        "by_candidate": {
          "21|economicintensity|gdp|demand|gdppopulationadjustment": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 4,
            "selected_cell_count": 4,
            "valid_cell_count": 4
          },
          "21|economicintensity|pmi|demand|pmiadjustment": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 2,
            "selected_cell_count": 2,
            "valid_cell_count": 2
          }
        },
        "invalid_cell_count": 0,
        "missing_cell_count": 0,
        "returned_cell_count": 6,
        "selected_cell_count": 6,
        "valid_cell_count": 6
      },
      "selected_references": {
        "basecase_and_lut_count": 5,
        "effective_source_counts": {
          "basecase": 5,
          "lut": 1
        },
        "lut_only_count": 1,
        "references": [
          {
            "actual_basecase_value": 49.5,
            "axes": {
              "Country": "China",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": "Demand:PMIAdjustment:R31C6",
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 49.5,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:44:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:8:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": 0.042,
            "axes": {
              "Country": "China",
              "Year": 2026
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R21C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2025"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.042,
            "lut_default_value": 0.0407034661186183,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1441",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          },
          {
            "actual_basecase_value": 0.042,
            "axes": {
              "Country": "China",
              "Year": 2027
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R22C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2026"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.042,
            "lut_default_value": 0.03663353294341154,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1610",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          },
          {
            "actual_basecase_value": 0.019,
            "axes": {
              "Country": "United States",
              "Year": 2026
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R13C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2025"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.019,
            "lut_default_value": 0.020638022790823607,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1405",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          },
          {
            "actual_basecase_value": 0.02,
            "axes": {
              "Country": "United States",
              "Year": 2027
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R14C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2026"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.02,
            "lut_default_value": 0.021203349036498675,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1574",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          }
        ],
        "rejected_exact_slot_count": 0,
        "selected_reference_count": 6
      },
      "source": {
        "basecase_record_count": 96,
        "basecase_record_count_by_candidate": {
          "21|economicintensity|gdp|demand|gdppopulationadjustment": 60,
          "21|economicintensity|pmi|demand|pmiadjustment": 36
        },
        "lut_record_count": 5855,
        "lut_record_count_by_parameter": {
          "GDP": 815,
          "PMI": 5040
        },
        "slot_leaf_count": 247,
        "slot_leaf_count_by_candidate": {
          "21|economicintensity|gdp|demand|gdppopulationadjustment": 163,
          "21|economicintensity|pmi|demand|pmiadjustment": 84
        }
      }
    },
    "resolved_config": {
      "model_parameter_llm_reasoning_effort": "default",
      "model_parameter_llm_stream_enabled": false,
      "model_parameter_lut_enabled": true,
      "model_parameter_lut_horizon_end_year": 2030,
      "model_parameter_lut_horizon_start_year": 2026,
      "model_parameter_max_parameter_slots": 100,
      "model_parameter_max_value_prompt_basecase_records": 100
    },
    "scenario_id": 305,
    "target_parameter": "GDP"
  },
  {
    "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
    "reference_diagnostics": {
      "cell_validation": {
        "by_candidate": {
          "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 5,
            "selected_cell_count": 5,
            "valid_cell_count": 5
          }
        },
        "invalid_cell_count": 0,
        "missing_cell_count": 0,
        "returned_cell_count": 5,
        "selected_cell_count": 5,
        "valid_cell_count": 5
      },
      "selected_references": {
        "basecase_and_lut_count": 5,
        "effective_source_counts": {
          "basecase": 5,
          "lut": 0
        },
        "lut_only_count": 0,
        "references": [
          {
            "actual_basecase_value": 0.8971397151184897,
            "axes": {
              "Country": "United States",
              "LNG Plant": "Cameron LNG",
              "LNG Plant Train": "Cameron LNG T1",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": "Supply:LiqUtilAdjustment:R155C40",
            "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "capacity_transform=mtpm_x_12"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.8971397151184897,
            "lut_default_value": 0.8966636468390256,
            "lut_reference_id": "lut:BCLiquefaction.csv:row:19213",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {
              "Life Cycle Category": "Operational",
              "Nameplate Capacity (MTPA)": 4.5,
              "Period": 103
            },
            "parameter_name": "LiqUtilAdjustment"
          },
          {
            "actual_basecase_value": 0.8971397151184897,
            "axes": {
              "Country": "United States",
              "LNG Plant": "Cameron LNG",
              "LNG Plant Train": "Cameron LNG T2",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": "Supply:LiqUtilAdjustment:R156C40",
            "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "capacity_transform=mtpm_x_12"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.8971397151184897,
            "lut_default_value": 0.8966636468390256,
            "lut_reference_id": "lut:BCLiquefaction.csv:row:19225",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {
              "Life Cycle Category": "Operational",
              "Nameplate Capacity (MTPA)": 4.5,
              "Period": 103
            },
            "parameter_name": "LiqUtilAdjustment"
          },
          {
            "actual_basecase_value": 0.8971397151184897,
            "axes": {
              "Country": "United States",
              "LNG Plant": "Cameron LNG",
              "LNG Plant Train": "Cameron LNG T3",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": "Supply:LiqUtilAdjustment:R157C40",
            "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "capacity_transform=mtpm_x_12"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.8971397151184897,
            "lut_default_value": 0.8966636468390256,
            "lut_reference_id": "lut:BCLiquefaction.csv:row:19237",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {
              "Life Cycle Category": "Operational",
              "Nameplate Capacity (MTPA)": 4.5,
              "Period": 103
            },
            "parameter_name": "LiqUtilAdjustment"
          },
          {
            "actual_basecase_value": 0.0,
            "axes": {
              "Country": "United States",
              "LNG Plant": "Cameron LNG",
              "LNG Plant Train": "Cameron LNG T4",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": "Supply:LiqUtilAdjustment:R158C40",
            "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "capacity_transform=mtpm_x_12"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.0,
            "lut_default_value": 0.0,
            "lut_reference_id": "lut:BCLiquefaction.csv:row:29317",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {
              "Life Cycle Category": "Planned",
              "Nameplate Capacity (MTPA)": 6,
              "Period": 103
            },
            "parameter_name": "LiqUtilAdjustment"
          },
          {
            "actual_basecase_value": 0.0,
            "axes": {
              "Country": "United States",
              "LNG Plant": "Cameron LNG",
              "LNG Plant Train": "Cameron LNG T5",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": "Supply:LiqUtilAdjustment:R267C40",
            "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "capacity_transform=mtpm_x_12"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.0,
            "lut_default_value": 0.0,
            "lut_reference_id": "lut:BCLiquefaction.csv:row:32339",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {
              "Life Cycle Category": "Speculative",
              "Nameplate Capacity (MTPA)": 4.99,
              "Period": 103
            },
            "parameter_name": "LiqUtilAdjustment"
          }
        ],
        "rejected_exact_slot_count": 0,
        "selected_reference_count": 5
      },
      "source": {
        "basecase_record_count": 14411,
        "basecase_record_count_by_candidate": {
          "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": 14411
        },
        "lut_record_count": 19366,
        "lut_record_count_by_parameter": {
          "LiqUtilAdjustment": 19366
        },
        "slot_leaf_count": 347,
        "slot_leaf_count_by_candidate": {
          "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": 347
        }
      }
    },
    "resolved_config": {
      "model_parameter_llm_reasoning_effort": "default",
      "model_parameter_llm_stream_enabled": false,
      "model_parameter_lut_enabled": true,
      "model_parameter_lut_horizon_end_year": 2030,
      "model_parameter_lut_horizon_start_year": 2026,
      "model_parameter_max_parameter_slots": 100,
      "model_parameter_max_value_prompt_basecase_records": 100
    },
    "scenario_id": 105,
    "target_parameter": "LiqUtilAdjustment"
  },
  {
    "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
    "reference_diagnostics": {
      "cell_validation": {
        "by_candidate": {
          "21|economicintensity|gdp|demand|gdppopulationadjustment": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 4,
            "selected_cell_count": 4,
            "valid_cell_count": 4
          },
          "21|economicintensity|pmi|demand|pmiadjustment": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 24,
            "selected_cell_count": 24,
            "valid_cell_count": 24
          }
        },
        "invalid_cell_count": 0,
        "missing_cell_count": 0,
        "returned_cell_count": 28,
        "selected_cell_count": 28,
        "valid_cell_count": 28
      },
      "selected_references": {
        "basecase_and_lut_count": 10,
        "effective_source_counts": {
          "basecase": 10,
          "lut": 18
        },
        "lut_only_count": 18,
        "references": [
          {
            "actual_basecase_value": 49.5,
            "axes": {
              "Country": "China",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": "Demand:PMIAdjustment:R31C6",
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 49.5,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:44:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": 49.5,
            "axes": {
              "Country": "China",
              "Month": 8,
              "Year": 2026
            },
            "basecase_reference_id": "Demand:PMIAdjustment:R32C6",
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 49.5,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:45:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": 49.5,
            "axes": {
              "Country": "China",
              "Month": 9,
              "Year": 2026
            },
            "basecase_reference_id": "Demand:PMIAdjustment:R33C6",
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 49.5,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:46:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": 49.5,
            "axes": {
              "Country": "China",
              "Month": 10,
              "Year": 2026
            },
            "basecase_reference_id": "Demand:PMIAdjustment:R34C6",
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 49.5,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:47:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": 49.5,
            "axes": {
              "Country": "China",
              "Month": 11,
              "Year": 2026
            },
            "basecase_reference_id": "Demand:PMIAdjustment:R35C6",
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 49.5,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:48:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": 49.5,
            "axes": {
              "Country": "China",
              "Month": 12,
              "Year": 2026
            },
            "basecase_reference_id": "Demand:PMIAdjustment:R36C6",
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 49.5,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:49:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "China",
              "Month": 1,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:38:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "China",
              "Month": 2,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:39:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "China",
              "Month": 3,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:40:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "China",
              "Month": 4,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:41:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "China",
              "Month": 5,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:42:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "China",
              "Month": 6,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:43:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 7,
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:8:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 8,
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:9:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 9,
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:10:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 10,
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:11:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 11,
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:12:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 12,
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:13:year:2026",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 1,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:2:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 2,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:3:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 3,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:4:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 4,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:5:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 5,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:6:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 6,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 50.0,
            "lut_default_value": 50.0,
            "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:7:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PMI"
          },
          {
            "actual_basecase_value": 0.042,
            "axes": {
              "Country": "China",
              "Year": 2026
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R21C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2025"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.042,
            "lut_default_value": 0.0407034661186183,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1441",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          },
          {
            "actual_basecase_value": 0.042,
            "axes": {
              "Country": "China",
              "Year": 2027
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R22C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2026"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.042,
            "lut_default_value": 0.03663353294341154,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1610",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          },
          {
            "actual_basecase_value": 0.019,
            "axes": {
              "Country": "United States",
              "Year": 2026
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R13C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2025"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.019,
            "lut_default_value": 0.020638022790823607,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1405",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          },
          {
            "actual_basecase_value": 0.02,
            "axes": {
              "Country": "United States",
              "Year": 2027
            },
            "basecase_reference_id": "Demand:GDPPopulationAdjustment:R14C6",
            "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
            "diagnostics": [
              "actual_basecase_overrides_lut_default",
              "exact_year_minus_one=2026"
            ],
            "effective_source": "basecase",
            "llm_reference_value": 0.02,
            "lut_default_value": 0.021203349036498675,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1574",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "GDP"
          }
        ],
        "rejected_exact_slot_count": 0,
        "selected_reference_count": 28
      },
      "source": {
        "basecase_record_count": 96,
        "basecase_record_count_by_candidate": {
          "21|economicintensity|gdp|demand|gdppopulationadjustment": 60,
          "21|economicintensity|pmi|demand|pmiadjustment": 36
        },
        "lut_record_count": 5855,
        "lut_record_count_by_parameter": {
          "GDP": 815,
          "PMI": 5040
        },
        "slot_leaf_count": 247,
        "slot_leaf_count_by_candidate": {
          "21|economicintensity|gdp|demand|gdppopulationadjustment": 163,
          "21|economicintensity|pmi|demand|pmiadjustment": 84
        }
      }
    },
    "resolved_config": {
      "model_parameter_llm_reasoning_effort": "default",
      "model_parameter_llm_stream_enabled": false,
      "model_parameter_lut_enabled": true,
      "model_parameter_lut_horizon_end_year": 2030,
      "model_parameter_lut_horizon_start_year": 2026,
      "model_parameter_max_parameter_slots": 100,
      "model_parameter_max_value_prompt_basecase_records": 100
    },
    "scenario_id": 306,
    "target_parameter": "PMI"
  },
  {
    "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
    "reference_diagnostics": {
      "cell_validation": {
        "by_candidate": {
          "parameter|5|demand|powermixadjustment|powermix": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 1,
            "selected_cell_count": 1,
            "valid_cell_count": 1
          }
        },
        "invalid_cell_count": 0,
        "missing_cell_count": 0,
        "returned_cell_count": 1,
        "selected_cell_count": 1,
        "valid_cell_count": 1
      },
      "selected_references": {
        "basecase_and_lut_count": 0,
        "effective_source_counts": {
          "basecase": 0,
          "lut": 1
        },
        "lut_only_count": 1,
        "references": [
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Energy Source": "Gas",
              "Year": 2026
            },
            "basecase_reference_id": null,
            "candidate_key": "parameter|5|demand|powermixadjustment|powermix",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 0.36505,
            "lut_default_value": 0.36505,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:4166",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PowerMix"
          }
        ],
        "rejected_exact_slot_count": 0,
        "selected_reference_count": 1
      },
      "source": {
        "basecase_record_count": 55,
        "basecase_record_count_by_candidate": {
          "parameter|5|demand|powermixadjustment|powermix": 55
        },
        "lut_record_count": 4200,
        "lut_record_count_by_parameter": {
          "PowerMix": 4200
        },
        "slot_leaf_count": 840,
        "slot_leaf_count_by_candidate": {
          "parameter|5|demand|powermixadjustment|powermix": 840
        }
      }
    },
    "resolved_config": {
      "model_parameter_llm_reasoning_effort": "default",
      "model_parameter_llm_stream_enabled": false,
      "model_parameter_lut_enabled": true,
      "model_parameter_lut_horizon_end_year": 2030,
      "model_parameter_lut_horizon_start_year": 2026,
      "model_parameter_max_parameter_slots": 100,
      "model_parameter_max_value_prompt_basecase_records": 100
    },
    "scenario_id": 287,
    "target_parameter": "PowerMix"
  },
  {
    "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
    "reference_diagnostics": {
      "cell_validation": {
        "by_candidate": {
          "6|altenergyabsorption|powermix|demand|powermixadjustment": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 3,
            "selected_cell_count": 3,
            "valid_cell_count": 3
          },
          "6|coldwaveintensity|temperature|demand|weatheradjustment": {
            "invalid_cell_count": 0,
            "missing_cell_count": 0,
            "returned_cell_count": 1,
            "selected_cell_count": 1,
            "valid_cell_count": 1
          }
        },
        "invalid_cell_count": 0,
        "missing_cell_count": 0,
        "returned_cell_count": 4,
        "selected_cell_count": 4,
        "valid_cell_count": 4
      },
      "selected_references": {
        "basecase_and_lut_count": 0,
        "effective_source_counts": {
          "basecase": 0,
          "lut": 4
        },
        "lut_only_count": 4,
        "references": [
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Month": 3,
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "6|coldwaveintensity|temperature|demand|weatheradjustment",
            "diagnostics": [
              "lut_only",
              "degree_days_branch=hdd"
            ],
            "effective_source": "lut",
            "llm_reference_value": 5.401235615921525,
            "lut_default_value": 5.401235615921525,
            "lut_reference_id": "lut:Demand_Model_Input_WeatherInput_value_based_t1.csv:row:4:year:2027",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "Temperature"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Energy Source": "Gas",
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "6|altenergyabsorption|powermix|demand|powermixadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 0.35812716254325083,
            "lut_default_value": 0.35812716254325083,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:5006",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PowerMix"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Energy Source": "Coal",
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "6|altenergyabsorption|powermix|demand|powermixadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 0.15884317686353724,
            "lut_default_value": 0.15884317686353724,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:5007",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PowerMix"
          },
          {
            "actual_basecase_value": null,
            "axes": {
              "Country": "United States",
              "Energy Source": "Liquids",
              "Year": 2027
            },
            "basecase_reference_id": null,
            "candidate_key": "6|altenergyabsorption|powermix|demand|powermixadjustment",
            "diagnostics": [
              "lut_only"
            ],
            "effective_source": "lut",
            "llm_reference_value": 0.0035100702014040277,
            "lut_default_value": 0.0035100702014040277,
            "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:5001",
            "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
            "metadata": {},
            "parameter_name": "PowerMix"
          }
        ],
        "rejected_exact_slot_count": 0,
        "selected_reference_count": 4
      },
      "source": {
        "basecase_record_count": 205,
        "basecase_record_count_by_candidate": {
          "6|altenergyabsorption|powermix|demand|powermixadjustment": 55,
          "6|coldwaveintensity|temperature|demand|weatheradjustment": 150
        },
        "lut_record_count": 9240,
        "lut_record_count_by_parameter": {
          "PowerMix": 4200,
          "Temperature": 5040
        },
        "slot_leaf_count": 924,
        "slot_leaf_count_by_candidate": {
          "6|altenergyabsorption|powermix|demand|powermixadjustment": 840,
          "6|coldwaveintensity|temperature|demand|weatheradjustment": 84
        }
      }
    },
    "resolved_config": {
      "model_parameter_llm_reasoning_effort": "default",
      "model_parameter_llm_stream_enabled": false,
      "model_parameter_lut_enabled": true,
      "model_parameter_lut_horizon_end_year": 2030,
      "model_parameter_lut_horizon_start_year": 2026,
      "model_parameter_max_parameter_slots": 100,
      "model_parameter_max_value_prompt_basecase_records": 100
    },
    "scenario_id": 289,
    "target_parameter": "Temperature"
  }
]
```

## 호출 결과

### Parameter: GDP

#### event_type_l2_id=21 국가별 경기

##### Scenario Group

```json
{
  "description": "국가별 경기 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
  "dimension_selected": [
    "period",
    "economic_intensity",
    "demand_impact"
  ],
  "event_type": {
    "event_type_l1_id": 4,
    "event_type_l2_id": 21,
    "level_1_code": "exogenous_shock",
    "level_1_label": "외생충격",
    "level_2_code": "country_economic_condition",
    "level_2_label": "국가별 경기"
  },
  "event_type_l2_id": 21,
  "mi_event_id": 1132,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 60,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 국가별 경기 scenario_group",
  "title": "[model_parameter_agent_test] 국가별 경기 추가 검증"
}
```

##### Dimension Template

```json
[
  {
    "dim_key": "period",
    "display_order": 1,
    "label": "기간",
    "required": true,
    "value_enums": [
      "1개월 이하",
      "3개월",
      "6개월",
      "1년",
      "1년 초과",
      "구조적/영구",
      "종료 미정"
    ]
  },
  {
    "dim_key": "economic_intensity",
    "display_order": 2,
    "label": "강도",
    "required": true,
    "value_enums": [
      "경미",
      "보통",
      "강함",
      "경기 충격"
    ]
  },
  {
    "dim_key": "demand_impact",
    "display_order": 3,
    "label": "LNG 수요 영향 규모",
    "required": false,
    "value_enums": [
      "100%",
      "75%",
      "50%",
      "25%",
      "0%"
    ]
  }
]
```

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": null,
      "dimension": "demand_impact (LNG 수요 영향 규모)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "event에 명시된 국가별 GDP 성장률 전망, 전망치 수정폭, 하방/상방 시나리오를 우선 사용해 해당 Country/Year의 최종 성장률을 산정한다. 성장률 전망이 정량으로 제시되지 않으면 경기 둔화/회복 강도와 기간을 근거로 basecase 대비 보수적으로 조정한다. LNG 수요 영향률이나 가격 영향률을 GDP 성장률 multiplier로 사용하지 않는다.",
      "dimension": "economic_intensity (강도)",
      "mapping_method": "direct",
      "parameter": "GDP"
    },
    {
      "comment": "event에 명시된 제조업/서비스업 경기, 생산활동 증가·감소, 산업활동 둔화·회복, 단기 경기 강도를 근거로 해당 Country/Year/Month의 PMI 지수 최종값을 산정한다. basecase가 있으면 기존 PMI 수준과 이벤트 방향을 비교해 보수적으로 조정한다. basecase가 없으면 다른 국가의 PMI 수준을 기준값으로 삼지 않고, 이벤트에 제시된 해당 국가의 경기 방향과 PMI 기준값 50을 중심으로 산정한다.",
      "dimension": "economic_intensity (강도)",
      "mapping_method": "direct",
      "parameter": "PMI"
    },
    {
      "comment": "파라미터의 시간축으로 사용될 수 있다(PMI:Year/Month, GDP:Year)",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    }
  ],
  "event_type_l2_id": 21,
  "mapping_count": 4,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

##### Event

```json
{
  "created_at": "2026-06-19T23:05:32.528198",
  "detail_analysis": "사건 요약:\nOECD가 6월 3일 파리에서 세계 경제 전망을 갱신한 사건임. 기본 시나리오에서 세계 GDP 성장률은 2025년 3.4%, 2026년 2.8%, 2027년 3.1%로 제시됨. 2026년 전망은 기존 2.9%에서 2.8%로 하향 조정됨. 2027년 전망은 기존 3.0%에서 3.1%로 상향 조정됨. 미국 성장률은 2026년 2.0%, 2027년 1.8%로 제시됨. 중국 성장률은 2026년 4.5%로 기존 4.4% 대비 상향됐고 2027년은 4.3%로 유지됨.\n\n영향 경로:\nOECD는 중동 전쟁의 지속 기간과 에너지 공급 차질 장기화를 세계 경제 전망의 주요 변수로 지목함. 에너지 공급 차질이 2027년까지 이어질 경우 세계 성장률이 2026년 2.1%, 2027년 1.8%까지 낮아질 수 있다는 하방 시나리오 제시됨. 성장 둔화는 산업활동, 전력소비, 연료 수요를 통해 천연가스 및 LNG 수요 기대를 낮추는 간접 경로임. 반대로 에너지 공급 차질 장기화는 물리 공급 불확실성, 운송 리스크, 인플레이션 압력을 통해 에너지 가격 프리미엄을 지지하는 경로임.\n\n시장 반응:\n신규 기사에 JKM, TTF, Henry Hub 등 구체적 LNG·가스 가격 수치나 선물곡선 변화는 제시되지 않음. 가격 방향은 거시 수요 둔화 우려와 공급 차질 리스크가 병존하는 혼재 구도임. 경기 둔화 시나리오는 LNG 수요 기대와 가격에 하방 압력으로 작용 가능함. 중동 전쟁 장기화와 에너지 공급 차질 가능성은 리스크 프리미엄과 인플레이션 압력을 높이는 상방 요인임.\n\nLNG 시장 관점:\n해당 Event는 LNG 설비나 물동량 자체의 변화가 아니라 국가별 경기 및 글로벌 성장 전망 조정에 해당하는 간접 변수임. 중국 2026년 4.5%, 2027년 4.3% 성장 전망은 아시아 LNG 수요 기대의 거시 전제 중 하나임. 미국 성장률 둔화 전망은 에너지 소비와 산업 수요 측면의 배경 변수임. Event 경계상 핵심은 OECD의 성장률 전망 재조정이며, 중동 전쟁과 에너지 공급 차질은 원인 및 리스크 요인으로 반영하는 것이 적절함.",
  "event_title_ko": "OECD 세계 성장률 전망 재조정",
  "event_type_l2_id": 21,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-03T09:07:07",
  "mi_event_id": "1132",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[글로벌 경기] OECD가 2026·2027년 성장률 전망 갱신 → LNG 수요 둔화·리스크 프리미엄 병존",
  "source_mi_record_ids": [
    2334,
    2335,
    2342
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [305]
- scenario_count: 1
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: PASS

##### scenario_id=305 [model_parameter_agent_test] 경미한 경기 둔화와 수요 영향 제한

- target_parameter: `GDP`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 00:40.562 (40.562s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "demand_impact": "100%",
    "economic_intensity": "경미",
    "period": "1개월 이하"
  },
  "impact": {
    "hh": "중립",
    "jkm": "중립",
    "ttf": "중립"
  },
  "narrative": "경기 영향이 경미하고 LNG 수요 영향은 거의 흡수된다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 60,
  "scenario_id": 305,
  "status": "created",
  "title": "[model_parameter_agent_test] 경미한 경기 둔화와 수요 영향 제한"
}
```

###### Validation Summary

- target_expected_parameters: `["GDP"]`
- target_selected_parameters: `["GDP"]`
- expected_parameters: `["PMI", "GDP"]`
- selected_parameters: `["PMI", "GDP"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

###### Reference Runtime Diagnostics

```json
{
  "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
  "reference_diagnostics": {
    "cell_validation": {
      "by_candidate": {
        "21|economicintensity|gdp|demand|gdppopulationadjustment": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 4,
          "selected_cell_count": 4,
          "valid_cell_count": 4
        },
        "21|economicintensity|pmi|demand|pmiadjustment": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 2,
          "selected_cell_count": 2,
          "valid_cell_count": 2
        }
      },
      "invalid_cell_count": 0,
      "missing_cell_count": 0,
      "returned_cell_count": 6,
      "selected_cell_count": 6,
      "valid_cell_count": 6
    },
    "selected_references": {
      "basecase_and_lut_count": 5,
      "effective_source_counts": {
        "basecase": 5,
        "lut": 1
      },
      "lut_only_count": 1,
      "references": [
        {
          "actual_basecase_value": 49.5,
          "axes": {
            "Country": "China",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": "Demand:PMIAdjustment:R31C6",
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 49.5,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:44:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:8:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": 0.042,
          "axes": {
            "Country": "China",
            "Year": 2026
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R21C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2025"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.042,
          "lut_default_value": 0.0407034661186183,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1441",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        },
        {
          "actual_basecase_value": 0.042,
          "axes": {
            "Country": "China",
            "Year": 2027
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R22C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2026"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.042,
          "lut_default_value": 0.03663353294341154,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1610",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        },
        {
          "actual_basecase_value": 0.019,
          "axes": {
            "Country": "United States",
            "Year": 2026
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R13C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2025"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.019,
          "lut_default_value": 0.020638022790823607,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1405",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        },
        {
          "actual_basecase_value": 0.02,
          "axes": {
            "Country": "United States",
            "Year": 2027
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R14C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2026"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.02,
          "lut_default_value": 0.021203349036498675,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1574",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        }
      ],
      "rejected_exact_slot_count": 0,
      "selected_reference_count": 6
    },
    "source": {
      "basecase_record_count": 96,
      "basecase_record_count_by_candidate": {
        "21|economicintensity|gdp|demand|gdppopulationadjustment": 60,
        "21|economicintensity|pmi|demand|pmiadjustment": 36
      },
      "lut_record_count": 5855,
      "lut_record_count_by_parameter": {
        "GDP": 815,
        "PMI": 5040
      },
      "slot_leaf_count": 247,
      "slot_leaf_count_by_candidate": {
        "21|economicintensity|gdp|demand|gdppopulationadjustment": 163,
        "21|economicintensity|pmi|demand|pmiadjustment": 84
      }
    }
  },
  "resolved_config": {
    "model_parameter_llm_reasoning_effort": "default",
    "model_parameter_llm_stream_enabled": false,
    "model_parameter_lut_enabled": true,
    "model_parameter_lut_horizon_end_year": 2030,
    "model_parameter_lut_horizon_start_year": 2026,
    "model_parameter_max_parameter_slots": 100,
    "model_parameter_max_value_prompt_basecase_records": 100
  }
}
```


##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=141 | REVIEW |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=24 | REVIEW |
| Step2 selected slot | 6 | REVIEW |
| Step3 exact reference | references=6, limit_per_candidate=100, per_candidate=`{"21|economicintensity|gdp|demand|gdppopulationadjustment": 4, "21|economicintensity|pmi|demand|pmiadjustment": 2}` | PASS |
| Step3 value 결과 | value_cells=6, basecaseValue_present=5 | PASS |
| Step2 slot axis value 수 | `{"21|economicintensity|gdp|demand|gdppopulationadjustment": {"Year": 8}, "21|economicintensity|pmi|demand|pmiadjustment": {"Month": 12, "Year": 4}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 4 | 강도 차원은 국가·연도별 실질 GDP 성장률 전망과 수정폭을 GDP 최종 입력값으로 반영하는 직접 근거이며, 기간 차원의 1개월 이하 조건은 LNG 수요 충격이 제한적이라는 보수적 해석에 사용된다. 이벤트에 국가별 성장률 전망이 명시되어 있으므로, 정량 전망이 있는 연도는 기준값 대비 증감폭이 아니라 해당 연도의 최종 성장률 자체로 입력한다. |

###### Proposed Parameter Values

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.045 | 해당 좌표의 기준 GDP 성장률은 0.042이다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 명시되어 있고 기존 전망 대비 상향된 것으로 제시되므로, 최종 입력값은 전망치 자체인 0.045로 반영한다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.043 | 해당 좌표의 기준 GDP 성장률은 0.042이다. 이벤트에서 중국 2027년 성장률 전망이 4.3%로 유지된다고 명시되어 있으므로, 최종 입력값은 해당 전망치 자체인 0.043으로 반영한다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.02 | 해당 좌표의 기준 GDP 성장률은 0.019이다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어 있으므로, 경미한 시나리오하에서도 정량 전망을 우선하여 최종 입력값을 0.020으로 반영한다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.018 | 해당 좌표의 기준 GDP 성장률은 0.020이다. 이벤트에서 미국 2027년 성장률 전망이 1.8%로 제시되어 완만한 둔화를 반영하므로, 최종 입력값은 전망치 자체인 0.018로 반영한다. |

###### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1132,
  "model_param_proposal_id": 395,
  "proposal_completed_dtm": "2026-07-10 18:02:15.520741",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PMIAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Year",
          "Month"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "PMI"
        ]
      },
      "parameterName": "PMI",
      "rationale": "강도 차원은 국가·월별 산업활동의 경기 민감도를 PMI 최종값으로 반영하는 직접 근거이며, 기간 차원의 1개월 이하 조건은 조정이 단기 월 단위에 국한됨을 의미한다. 시나리오가 경미한 경기 둔화와 수요 영향 제한을 전제하고 가격 영향도 중립으로 제시하므로, 명시적인 PMI 수치가 없는 범위에서는 기준 PMI를 크게 훼손하지 않는 보수적 유지 또는 소폭 하향으로 반영한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.5,
          "rationale": "해당 좌표의 기준 PMI는 이미 50을 소폭 하회해 약한 위축 상태를 반영한다. 시나리오는 1개월 이하의 경미한 둔화이고, 이벤트상 중국의 2026년 성장 전망은 오히려 상향되어 추가적인 PMI 하향 근거가 제한적이므로 기준값 49.5를 유지한다."
        },
        {
          "Country": "United States",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 49.9,
          "rationale": "해당 좌표의 기준 PMI는 중립 수준인 50.0이다. 이벤트상 미국 성장률 전망은 완만한 둔화 배경에 놓여 있고, 시나리오도 경미하며 기간이 1개월 이하로 제한되므로 산업활동 영향은 중립선 바로 아래의 소폭 둔화 수준인 49.9로 반영한다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "GDPPopulationAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% change (+/-)"
        ]
      },
      "parameterName": "GDP",
      "rationale": "강도 차원은 국가·연도별 실질 GDP 성장률 전망과 수정폭을 GDP 최종 입력값으로 반영하는 직접 근거이며, 기간 차원의 1개월 이하 조건은 LNG 수요 충격이 제한적이라는 보수적 해석에 사용된다. 이벤트에 국가별 성장률 전망이 명시되어 있으므로, 정량 전망이 있는 연도는 기준값 대비 증감폭이 아니라 해당 연도의 최종 성장률 자체로 입력한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.045,
          "rationale": "해당 좌표의 기준 GDP 성장률은 0.042이다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 명시되어 있고 기존 전망 대비 상향된 것으로 제시되므로, 최종 입력값은 전망치 자체인 0.045로 반영한다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.043,
          "rationale": "해당 좌표의 기준 GDP 성장률은 0.042이다. 이벤트에서 중국 2027년 성장률 전망이 4.3%로 유지된다고 명시되어 있으므로, 최종 입력값은 해당 전망치 자체인 0.043으로 반영한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.02,
          "rationale": "해당 좌표의 기준 GDP 성장률은 0.019이다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어 있으므로, 경미한 시나리오하에서도 정량 전망을 우선하여 최종 입력값을 0.020으로 반영한다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.018,
          "rationale": "해당 좌표의 기준 GDP 성장률은 0.020이다. 이벤트에서 미국 2027년 성장률 전망이 1.8%로 제시되어 완만한 둔화를 반영하므로, 최종 입력값은 전망치 자체인 0.018로 반영한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 60,
  "scenario_id": 305,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.253 | 4.253 | 2815 | 113 | 2928 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:10.736 | 10.736 | 27509 | 750 | 28259 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:17.987 | 17.987 | 6334 | 1520 | 7854 |

### Parameter: PMI

#### event_type_l2_id=21 국가별 경기

##### Scenario Group

```json
{
  "description": "국가별 경기 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
  "dimension_selected": [
    "period",
    "economic_intensity",
    "demand_impact"
  ],
  "event_type": {
    "event_type_l1_id": 4,
    "event_type_l2_id": 21,
    "level_1_code": "exogenous_shock",
    "level_1_label": "외생충격",
    "level_2_code": "country_economic_condition",
    "level_2_label": "국가별 경기"
  },
  "event_type_l2_id": 21,
  "mi_event_id": 1132,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 60,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 국가별 경기 scenario_group",
  "title": "[model_parameter_agent_test] 국가별 경기 추가 검증"
}
```

##### Dimension Template

```json
[
  {
    "dim_key": "period",
    "display_order": 1,
    "label": "기간",
    "required": true,
    "value_enums": [
      "1개월 이하",
      "3개월",
      "6개월",
      "1년",
      "1년 초과",
      "구조적/영구",
      "종료 미정"
    ]
  },
  {
    "dim_key": "economic_intensity",
    "display_order": 2,
    "label": "강도",
    "required": true,
    "value_enums": [
      "경미",
      "보통",
      "강함",
      "경기 충격"
    ]
  },
  {
    "dim_key": "demand_impact",
    "display_order": 3,
    "label": "LNG 수요 영향 규모",
    "required": false,
    "value_enums": [
      "100%",
      "75%",
      "50%",
      "25%",
      "0%"
    ]
  }
]
```

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": null,
      "dimension": "demand_impact (LNG 수요 영향 규모)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "event에 명시된 국가별 GDP 성장률 전망, 전망치 수정폭, 하방/상방 시나리오를 우선 사용해 해당 Country/Year의 최종 성장률을 산정한다. 성장률 전망이 정량으로 제시되지 않으면 경기 둔화/회복 강도와 기간을 근거로 basecase 대비 보수적으로 조정한다. LNG 수요 영향률이나 가격 영향률을 GDP 성장률 multiplier로 사용하지 않는다.",
      "dimension": "economic_intensity (강도)",
      "mapping_method": "direct",
      "parameter": "GDP"
    },
    {
      "comment": "event에 명시된 제조업/서비스업 경기, 생산활동 증가·감소, 산업활동 둔화·회복, 단기 경기 강도를 근거로 해당 Country/Year/Month의 PMI 지수 최종값을 산정한다. basecase가 있으면 기존 PMI 수준과 이벤트 방향을 비교해 보수적으로 조정한다. basecase가 없으면 다른 국가의 PMI 수준을 기준값으로 삼지 않고, 이벤트에 제시된 해당 국가의 경기 방향과 PMI 기준값 50을 중심으로 산정한다.",
      "dimension": "economic_intensity (강도)",
      "mapping_method": "direct",
      "parameter": "PMI"
    },
    {
      "comment": "파라미터의 시간축으로 사용될 수 있다(PMI:Year/Month, GDP:Year)",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    }
  ],
  "event_type_l2_id": 21,
  "mapping_count": 4,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

##### Event

```json
{
  "created_at": "2026-06-19T23:05:32.528198",
  "detail_analysis": "사건 요약:\nOECD가 6월 3일 파리에서 세계 경제 전망을 갱신한 사건임. 기본 시나리오에서 세계 GDP 성장률은 2025년 3.4%, 2026년 2.8%, 2027년 3.1%로 제시됨. 2026년 전망은 기존 2.9%에서 2.8%로 하향 조정됨. 2027년 전망은 기존 3.0%에서 3.1%로 상향 조정됨. 미국 성장률은 2026년 2.0%, 2027년 1.8%로 제시됨. 중국 성장률은 2026년 4.5%로 기존 4.4% 대비 상향됐고 2027년은 4.3%로 유지됨.\n\n영향 경로:\nOECD는 중동 전쟁의 지속 기간과 에너지 공급 차질 장기화를 세계 경제 전망의 주요 변수로 지목함. 에너지 공급 차질이 2027년까지 이어질 경우 세계 성장률이 2026년 2.1%, 2027년 1.8%까지 낮아질 수 있다는 하방 시나리오 제시됨. 성장 둔화는 산업활동, 전력소비, 연료 수요를 통해 천연가스 및 LNG 수요 기대를 낮추는 간접 경로임. 반대로 에너지 공급 차질 장기화는 물리 공급 불확실성, 운송 리스크, 인플레이션 압력을 통해 에너지 가격 프리미엄을 지지하는 경로임.\n\n시장 반응:\n신규 기사에 JKM, TTF, Henry Hub 등 구체적 LNG·가스 가격 수치나 선물곡선 변화는 제시되지 않음. 가격 방향은 거시 수요 둔화 우려와 공급 차질 리스크가 병존하는 혼재 구도임. 경기 둔화 시나리오는 LNG 수요 기대와 가격에 하방 압력으로 작용 가능함. 중동 전쟁 장기화와 에너지 공급 차질 가능성은 리스크 프리미엄과 인플레이션 압력을 높이는 상방 요인임.\n\nLNG 시장 관점:\n해당 Event는 LNG 설비나 물동량 자체의 변화가 아니라 국가별 경기 및 글로벌 성장 전망 조정에 해당하는 간접 변수임. 중국 2026년 4.5%, 2027년 4.3% 성장 전망은 아시아 LNG 수요 기대의 거시 전제 중 하나임. 미국 성장률 둔화 전망은 에너지 소비와 산업 수요 측면의 배경 변수임. Event 경계상 핵심은 OECD의 성장률 전망 재조정이며, 중동 전쟁과 에너지 공급 차질은 원인 및 리스크 요인으로 반영하는 것이 적절함.",
  "event_title_ko": "OECD 세계 성장률 전망 재조정",
  "event_type_l2_id": 21,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-03T09:07:07",
  "mi_event_id": "1132",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[글로벌 경기] OECD가 2026·2027년 성장률 전망 갱신 → LNG 수요 둔화·리스크 프리미엄 병존",
  "source_mi_record_ids": [
    2334,
    2335,
    2342
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [306]
- scenario_count: 1
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: PASS

##### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- target_parameter: `PMI`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:18.006 (78.006s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "demand_impact": "25%",
    "economic_intensity": "경기 충격",
    "period": "1년"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "국가별 경기 충격이 1년 지속되어 GDP/PMI 및 가스 수요 조정이 필요하다.",
  "probability_delta": 4.0,
  "probability_score": 40.0,
  "scenario_group_id": 60,
  "scenario_id": 306,
  "status": "created",
  "title": "[model_parameter_agent_test] 1년 경기 충격과 수요 감소"
}
```

###### Validation Summary

- target_expected_parameters: `["PMI"]`
- target_selected_parameters: `["PMI"]`
- expected_parameters: `["PMI", "GDP"]`
- selected_parameters: `["PMI", "GDP"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

###### Reference Runtime Diagnostics

```json
{
  "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
  "reference_diagnostics": {
    "cell_validation": {
      "by_candidate": {
        "21|economicintensity|gdp|demand|gdppopulationadjustment": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 4,
          "selected_cell_count": 4,
          "valid_cell_count": 4
        },
        "21|economicintensity|pmi|demand|pmiadjustment": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 24,
          "selected_cell_count": 24,
          "valid_cell_count": 24
        }
      },
      "invalid_cell_count": 0,
      "missing_cell_count": 0,
      "returned_cell_count": 28,
      "selected_cell_count": 28,
      "valid_cell_count": 28
    },
    "selected_references": {
      "basecase_and_lut_count": 10,
      "effective_source_counts": {
        "basecase": 10,
        "lut": 18
      },
      "lut_only_count": 18,
      "references": [
        {
          "actual_basecase_value": 49.5,
          "axes": {
            "Country": "China",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": "Demand:PMIAdjustment:R31C6",
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 49.5,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:44:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": 49.5,
          "axes": {
            "Country": "China",
            "Month": 8,
            "Year": 2026
          },
          "basecase_reference_id": "Demand:PMIAdjustment:R32C6",
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 49.5,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:45:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": 49.5,
          "axes": {
            "Country": "China",
            "Month": 9,
            "Year": 2026
          },
          "basecase_reference_id": "Demand:PMIAdjustment:R33C6",
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 49.5,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:46:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": 49.5,
          "axes": {
            "Country": "China",
            "Month": 10,
            "Year": 2026
          },
          "basecase_reference_id": "Demand:PMIAdjustment:R34C6",
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 49.5,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:47:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": 49.5,
          "axes": {
            "Country": "China",
            "Month": 11,
            "Year": 2026
          },
          "basecase_reference_id": "Demand:PMIAdjustment:R35C6",
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 49.5,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:48:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": 49.5,
          "axes": {
            "Country": "China",
            "Month": 12,
            "Year": 2026
          },
          "basecase_reference_id": "Demand:PMIAdjustment:R36C6",
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 49.5,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:49:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "China",
            "Month": 1,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:38:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "China",
            "Month": 2,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:39:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "China",
            "Month": 3,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:40:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "China",
            "Month": 4,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:41:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "China",
            "Month": 5,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:42:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "China",
            "Month": 6,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:43:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:8:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 8,
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:9:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 9,
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:10:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 10,
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:11:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 11,
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:12:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 12,
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:13:year:2026",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 1,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:2:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 2,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:3:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 3,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:4:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 4,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:5:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 5,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:6:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 6,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "21|economicintensity|pmi|demand|pmiadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 50.0,
          "lut_default_value": 50.0,
          "lut_reference_id": "lut:Demand_Model_Input_PMIInput_value_based_t2.csv:row:7:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PMI"
        },
        {
          "actual_basecase_value": 0.042,
          "axes": {
            "Country": "China",
            "Year": 2026
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R21C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2025"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.042,
          "lut_default_value": 0.0407034661186183,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1441",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        },
        {
          "actual_basecase_value": 0.042,
          "axes": {
            "Country": "China",
            "Year": 2027
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R22C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2026"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.042,
          "lut_default_value": 0.03663353294341154,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1610",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        },
        {
          "actual_basecase_value": 0.019,
          "axes": {
            "Country": "United States",
            "Year": 2026
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R13C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2025"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.019,
          "lut_default_value": 0.020638022790823607,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1405",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        },
        {
          "actual_basecase_value": 0.02,
          "axes": {
            "Country": "United States",
            "Year": 2027
          },
          "basecase_reference_id": "Demand:GDPPopulationAdjustment:R14C6",
          "candidate_key": "21|economicintensity|gdp|demand|gdppopulationadjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "exact_year_minus_one=2026"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.02,
          "lut_default_value": 0.021203349036498675,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:1574",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "GDP"
        }
      ],
      "rejected_exact_slot_count": 0,
      "selected_reference_count": 28
    },
    "source": {
      "basecase_record_count": 96,
      "basecase_record_count_by_candidate": {
        "21|economicintensity|gdp|demand|gdppopulationadjustment": 60,
        "21|economicintensity|pmi|demand|pmiadjustment": 36
      },
      "lut_record_count": 5855,
      "lut_record_count_by_parameter": {
        "GDP": 815,
        "PMI": 5040
      },
      "slot_leaf_count": 247,
      "slot_leaf_count_by_candidate": {
        "21|economicintensity|gdp|demand|gdppopulationadjustment": 163,
        "21|economicintensity|pmi|demand|pmiadjustment": 84
      }
    }
  },
  "resolved_config": {
    "model_parameter_llm_reasoning_effort": "default",
    "model_parameter_llm_stream_enabled": false,
    "model_parameter_lut_enabled": true,
    "model_parameter_lut_horizon_end_year": 2030,
    "model_parameter_lut_horizon_start_year": 2026,
    "model_parameter_max_parameter_slots": 100,
    "model_parameter_max_value_prompt_basecase_records": 100
  }
}
```


##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=141 | REVIEW |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=24 | REVIEW |
| Step2 selected slot | 28 | REVIEW |
| Step3 exact reference | references=28, limit_per_candidate=100, per_candidate=`{"21|economicintensity|gdp|demand|gdppopulationadjustment": 4, "21|economicintensity|pmi|demand|pmiadjustment": 24}` | PASS |
| Step3 value 결과 | value_cells=28, basecaseValue_present=10 | PASS |
| Step2 slot axis value 수 | `{"21|economicintensity|gdp|demand|gdppopulationadjustment": {"Year": 8}, "21|economicintensity|pmi|demand|pmiadjustment": {"Month": 12, "Year": 4}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 24 | 강도 dimension의 '경기 충격'은 PMI가 나타내는 생산활동·산업용 가스 수요 둔화와 직접 연결되므로 이 파라미터를 통해 국가별 월간 경기 위축을 반영한다. 기간 dimension의 '1년'은 월별 PMI 적용 범위를 현재 이후 12개월로 해석하는 보조 기준이며, 제안값은 기준 PMI보다 낮은 위축 구간을 1년 동안 유지하되 국가별 성장 전망의 차이를 감안해 보수적으로 배분했다. |

###### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 48.5 | 해당 좌표의 기준 PMI는 49.5로 이미 소폭 위축 구간이다. 1년 경기 충격 시나리오에 따라 산업활동 둔화가 추가된 것으로 보아 기준값에서 1.0pt 낮춘 48.5를 최종 입력값으로 제안한다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 49.5 | 48.5 | 해당 좌표의 기준 PMI는 49.5이다. 경기 충격이 단월 이벤트가 아니라 1년 지속되는 설정이므로 전월과 같은 위축 강도를 적용해 48.5로 산정했다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 49.5 | 48.5 | 해당 좌표의 기준 PMI는 49.5이다. 수요 감소를 동반한 경기 충격을 반영하되 중국 성장 전망의 상대적 견조함을 감안해 과도한 하향은 피하고 48.5를 적용한다. |
| 4 | `{"Country": "China", "Month": 10, "Year": 2026}` | 49.5 | 48.5 | 해당 좌표의 기준 PMI는 49.5이다. 1년 충격 기간 내 동일한 산업활동 둔화가 이어지는 것으로 보고 기준 대비 1.0pt 하향한 48.5를 제안한다. |
| 5 | `{"Country": "China", "Month": 11, "Year": 2026}` | 49.5 | 48.5 | 해당 좌표의 기준 PMI는 49.5이다. 경기 충격으로 PMI가 50 미만 위축권에 더 깊게 머무는 것으로 해석해 48.5로 조정한다. |
| 6 | `{"Country": "China", "Month": 12, "Year": 2026}` | 49.5 | 48.5 | 해당 좌표의 기준 PMI는 49.5이다. 연말까지 경기 충격이 지속되는 1년 시나리오이므로 기준보다 낮은 48.5를 최종값으로 둔다. |
| 7 | `{"Country": "China", "Month": 1, "Year": 2027}` | null | 49.0 | 해당 좌표의 기준 PMI는 중립 수준인 50.0이다. 1년 충격이 다음 해 상반기까지 이어지므로 50 아래의 완만한 위축값인 49.0으로 산정했다. |
| 8 | `{"Country": "China", "Month": 2, "Year": 2027}` | null | 49.0 | 해당 좌표의 기준 PMI는 50.0이다. 충격 지속 기간 내 산업 수요 둔화를 반영해 중립보다 1.0pt 낮은 49.0을 적용한다. |
| 9 | `{"Country": "China", "Month": 3, "Year": 2027}` | null | 49.0 | 해당 좌표의 기준 PMI는 50.0이다. 경기 충격이 아직 해소되지 않은 구간으로 보아 확장 중립선을 하회하는 49.0을 제안한다. |
| 10 | `{"Country": "China", "Month": 4, "Year": 2027}` | null | 49.0 | 해당 좌표의 기준 PMI는 50.0이다. 수요 감소 시나리오를 반영하되 중국의 상대적 경기 방어력을 감안해 완만한 하향값인 49.0을 적용한다. |
| 11 | `{"Country": "China", "Month": 5, "Year": 2027}` | null | 49.0 | 해당 좌표의 기준 PMI는 50.0이다. 1년 충격 기간 중 산업활동 둔화가 지속되는 것으로 해석해 49.0으로 산정한다. |
| 12 | `{"Country": "China", "Month": 6, "Year": 2027}` | null | 49.0 | 해당 좌표의 기준 PMI는 50.0이다. 충격 기간의 마지막 월까지 중립을 하회하는 위축을 반영해 49.0을 최종 입력값으로 제안한다. |
| 13 | `{"Country": "United States", "Month": 7, "Year": 2026}` | null | 48.7 | 해당 좌표의 기준 PMI는 50.0이다. 경기 충격에 따른 산업 수요 둔화를 반영해 중립선보다 1.3pt 낮은 48.7로 산정했다. |
| 14 | `{"Country": "United States", "Month": 8, "Year": 2026}` | null | 48.7 | 해당 좌표의 기준 PMI는 50.0이다. 1년 동안 지속되는 충격의 초기 구간으로 보아 48.7을 적용한다. |
| 15 | `{"Country": "United States", "Month": 9, "Year": 2026}` | null | 48.7 | 해당 좌표의 기준 PMI는 50.0이다. 산업활동 둔화와 가스 수요 감소 방향을 반영해 기준보다 낮은 48.7을 제안한다. |
| 16 | `{"Country": "United States", "Month": 10, "Year": 2026}` | null | 48.7 | 해당 좌표의 기준 PMI는 50.0이다. 경기 충격이 연중 지속되는 것으로 보고 중립 아래의 48.7을 적용한다. |
| 17 | `{"Country": "United States", "Month": 11, "Year": 2026}` | null | 48.7 | 해당 좌표의 기준 PMI는 50.0이다. 제조업·서비스업 활동 둔화가 수요 감소로 이어지는 설정을 반영해 48.7로 산정한다. |
| 18 | `{"Country": "United States", "Month": 12, "Year": 2026}` | null | 48.7 | 해당 좌표의 기준 PMI는 50.0이다. 연말까지 충격이 지속되는 것으로 보아 기준 대비 하향된 48.7을 최종값으로 둔다. |
| 19 | `{"Country": "United States", "Month": 1, "Year": 2027}` | null | 48.5 | 해당 좌표의 기준 PMI는 50.0이다. 2027년 성장 전망 둔화와 1년 충격의 잔존 효과를 반영해 48.5로 산정했다. |
| 20 | `{"Country": "United States", "Month": 2, "Year": 2027}` | null | 48.5 | 해당 좌표의 기준 PMI는 50.0이다. 경기 충격이 다음 해 상반기까지 이어지는 설정이므로 중립보다 1.5pt 낮은 48.5를 적용한다. |
| 21 | `{"Country": "United States", "Month": 3, "Year": 2027}` | null | 48.5 | 해당 좌표의 기준 PMI는 50.0이다. 성장 둔화가 산업용 수요를 누르는 구간으로 해석해 48.5를 최종 입력값으로 제안한다. |
| 22 | `{"Country": "United States", "Month": 4, "Year": 2027}` | null | 48.5 | 해당 좌표의 기준 PMI는 50.0이다. 1년 충격의 후반부에도 위축권이 유지되는 것으로 보아 48.5로 산정한다. |
| 23 | `{"Country": "United States", "Month": 5, "Year": 2027}` | null | 48.5 | 해당 좌표의 기준 PMI는 50.0이다. 수요 감소 방향을 유지하되 과도한 침체값은 피하는 보수적 위축 수준으로 48.5를 적용한다. |
| 24 | `{"Country": "United States", "Month": 6, "Year": 2027}` | null | 48.5 | 해당 좌표의 기준 PMI는 50.0이다. 1년 충격 기간의 마지막 월까지 산업활동 둔화가 남아 있는 것으로 보고 48.5를 제안한다. |

###### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1132,
  "model_param_proposal_id": 397,
  "proposal_completed_dtm": "2026-07-10 18:02:54.137958",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PMIAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Year",
          "Month"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "PMI"
        ]
      },
      "parameterName": "PMI",
      "rationale": "강도 dimension의 '경기 충격'은 PMI가 나타내는 생산활동·산업용 가스 수요 둔화와 직접 연결되므로 이 파라미터를 통해 국가별 월간 경기 위축을 반영한다. 기간 dimension의 '1년'은 월별 PMI 적용 범위를 현재 이후 12개월로 해석하는 보조 기준이며, 제안값은 기준 PMI보다 낮은 위축 구간을 1년 동안 유지하되 국가별 성장 전망의 차이를 감안해 보수적으로 배분했다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 49.5로 이미 소폭 위축 구간이다. 1년 경기 충격 시나리오에 따라 산업활동 둔화가 추가된 것으로 보아 기준값에서 1.0pt 낮춘 48.5를 최종 입력값으로 제안한다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 49.5이다. 경기 충격이 단월 이벤트가 아니라 1년 지속되는 설정이므로 전월과 같은 위축 강도를 적용해 48.5로 산정했다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 49.5이다. 수요 감소를 동반한 경기 충격을 반영하되 중국 성장 전망의 상대적 견조함을 감안해 과도한 하향은 피하고 48.5를 적용한다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 49.5이다. 1년 충격 기간 내 동일한 산업활동 둔화가 이어지는 것으로 보고 기준 대비 1.0pt 하향한 48.5를 제안한다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 49.5이다. 경기 충격으로 PMI가 50 미만 위축권에 더 깊게 머무는 것으로 해석해 48.5로 조정한다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 49.5이다. 연말까지 경기 충격이 지속되는 1년 시나리오이므로 기준보다 낮은 48.5를 최종값으로 둔다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 49.0,
          "rationale": "해당 좌표의 기준 PMI는 중립 수준인 50.0이다. 1년 충격이 다음 해 상반기까지 이어지므로 50 아래의 완만한 위축값인 49.0으로 산정했다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 49.0,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 충격 지속 기간 내 산업 수요 둔화를 반영해 중립보다 1.0pt 낮은 49.0을 적용한다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 49.0,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 경기 충격이 아직 해소되지 않은 구간으로 보아 확장 중립선을 하회하는 49.0을 제안한다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 49.0,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 수요 감소 시나리오를 반영하되 중국의 상대적 경기 방어력을 감안해 완만한 하향값인 49.0을 적용한다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 49.0,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 1년 충격 기간 중 산업활동 둔화가 지속되는 것으로 해석해 49.0으로 산정한다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 49.0,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 충격 기간의 마지막 월까지 중립을 하회하는 위축을 반영해 49.0을 최종 입력값으로 제안한다."
        },
        {
          "Country": "United States",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 48.7,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 경기 충격에 따른 산업 수요 둔화를 반영해 중립선보다 1.3pt 낮은 48.7로 산정했다."
        },
        {
          "Country": "United States",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 48.7,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 1년 동안 지속되는 충격의 초기 구간으로 보아 48.7을 적용한다."
        },
        {
          "Country": "United States",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 48.7,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 산업활동 둔화와 가스 수요 감소 방향을 반영해 기준보다 낮은 48.7을 제안한다."
        },
        {
          "Country": "United States",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 48.7,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 경기 충격이 연중 지속되는 것으로 보고 중립 아래의 48.7을 적용한다."
        },
        {
          "Country": "United States",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 48.7,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 제조업·서비스업 활동 둔화가 수요 감소로 이어지는 설정을 반영해 48.7로 산정한다."
        },
        {
          "Country": "United States",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 48.7,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 연말까지 충격이 지속되는 것으로 보아 기준 대비 하향된 48.7을 최종값으로 둔다."
        },
        {
          "Country": "United States",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 2027년 성장 전망 둔화와 1년 충격의 잔존 효과를 반영해 48.5로 산정했다."
        },
        {
          "Country": "United States",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 경기 충격이 다음 해 상반기까지 이어지는 설정이므로 중립보다 1.5pt 낮은 48.5를 적용한다."
        },
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 성장 둔화가 산업용 수요를 누르는 구간으로 해석해 48.5를 최종 입력값으로 제안한다."
        },
        {
          "Country": "United States",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 1년 충격의 후반부에도 위축권이 유지되는 것으로 보아 48.5로 산정한다."
        },
        {
          "Country": "United States",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 수요 감소 방향을 유지하되 과도한 침체값은 피하는 보수적 위축 수준으로 48.5를 적용한다."
        },
        {
          "Country": "United States",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 48.5,
          "rationale": "해당 좌표의 기준 PMI는 50.0이다. 1년 충격 기간의 마지막 월까지 산업활동 둔화가 남아 있는 것으로 보고 48.5를 제안한다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "GDPPopulationAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% change (+/-)"
        ]
      },
      "parameterName": "GDP",
      "rationale": "강도 dimension의 '경기 충격'은 국가별 GDP 성장률을 통해 산업·전력·가스 수요 전제를 낮추는 직접 근거가 된다. 기간 dimension의 '1년'은 현재 이후 충격이 두 개 연도에 걸쳐 반영될 수 있음을 의미하므로, 국가별 성장 전망과 기준 성장률을 비교해 최종 성장률 자체를 보수적으로 하향 제안했다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04,
          "rationale": "해당 좌표의 기준 성장률은 0.042이다. 이벤트의 중국 전망은 상대적으로 견조하지만 시나리오가 1년 경기 충격과 수요 감소를 전제하므로, 기준보다 소폭 낮은 0.040을 최종 성장률로 적용한다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.039,
          "rationale": "해당 좌표의 기준 성장률은 0.042이다. 1년 충격이 2027년 상반기까지 이어지는 점을 반영하고, 수요 둔화 방향을 유지하기 위해 0.039로 보수적으로 하향 산정했다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.017,
          "rationale": "해당 좌표의 기준 성장률은 0.019이다. 경기 충격으로 산업활동과 에너지 수요가 둔화되는 효과를 반영해 기준보다 낮은 0.017을 최종 성장률로 제안한다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.016,
          "rationale": "해당 좌표의 기준 성장률은 0.020이다. 이벤트에서 2027년 미국 성장률 둔화가 제시되고 1년 충격의 잔존 효과도 포함되므로 0.016으로 하향 적용한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 60,
  "scenario_id": 306,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.239 | 4.239 | 2828 | 119 | 2947 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:19.440 | 19.440 | 27518 | 2197 | 29715 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:47.848 | 47.848 | 8423 | 4690 | 13113 |

### Parameter: PowerMix

#### event_type_l2_id=5 발전소 Utilization 변동

##### Scenario Group

```json
{
  "description": "발전소 Utilization 변동 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
  "dimension_selected": [
    "affected_period",
    "capacity_change_scale",
    "structural_change_yn",
    "alt_energy_absorption",
    "onset_pattern",
    "recovery_pattern"
  ],
  "event_type": {
    "event_type_l1_id": 2,
    "event_type_l2_id": 5,
    "level_1_code": "demand",
    "level_1_label": "수요",
    "level_2_code": "power_plant_utilization_change",
    "level_2_label": "발전소 Utilization 변동"
  },
  "event_type_l2_id": 5,
  "mi_event_id": 1125,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 51,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 발전소 Utilization 변동 scenario_group",
  "title": "[model_parameter_agent_test] 발전소 Utilization 변동 추가 검증"
}
```

##### Dimension Template

```json
[
  {
    "dim_key": "affected_period",
    "display_order": 1,
    "label": "영향 기간",
    "required": true,
    "value_enums": [
      "1개월 이하",
      "3개월",
      "6개월",
      "1년",
      "1년 초과",
      "영구 (회복 불가)",
      "종료 미정"
    ]
  },
  {
    "dim_key": "capacity_change_scale",
    "display_order": 2,
    "label": "Capacity 변화 규모",
    "required": true,
    "value_enums": [
      "1 GW 미만",
      "1~3 GW",
      "3~5 GW",
      "5 GW 이상"
    ]
  },
  {
    "dim_key": "structural_change_yn",
    "display_order": 3,
    "label": "구조적 변동 여부",
    "required": false,
    "value_enums": [
      "단발적",
      "구조적"
    ]
  },
  {
    "dim_key": "alt_energy_absorption",
    "display_order": 4,
    "label": "타 에너지원 흡수 가능성",
    "required": false,
    "value_enums": [
      "100%",
      "75%",
      "50%",
      "25%",
      "0%"
    ]
  },
  {
    "dim_key": "onset_pattern",
    "display_order": 5,
    "label": "발생 패턴",
    "required": false,
    "value_enums": [
      "급격",
      "점진"
    ]
  },
  {
    "dim_key": "recovery_pattern",
    "display_order": 6,
    "label": "회복 패턴",
    "required": false,
    "value_enums": [
      "급격",
      "점진",
      "없음 (영구)"
    ]
  }
]
```

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "시간축",
      "dimension": "affected_period (영향 기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "발전소 용량·가동 변화로 발생한 전력 공백 또는 증분을 타 에너지원이 얼마나 흡수하는지 반영해 Gas PowerMix 최종 비중을 산정한다. alt_energy_absorption이 낮을수록 Gas 비중 변화를 크게 반영하고, 높을수록 Gas 비중 변화는 작게 둔다.",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "발전소 용량·가동 변화 규모를 근거로 해당 Country/Year의 Gas PowerMix 최종 비중을 산정한다. capacity_change_scale은 조정폭의 주된 근거로 사용하고, affected_period와 structural_change_yn은 적용 연도와 지속성 판단에 반영한다.",
      "dimension": "capacity_change_scale (Capacity 변화 규모)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": null,
      "dimension": "capacity_change_scale (Capacity 변화 규모)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "급격/점진",
      "dimension": "onset_pattern (발생 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "원상복귀 속도",
      "dimension": "recovery_pattern (회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "단발(정비·사고)/구조적(COD·폐쇄)",
      "dimension": "structural_change_yn (구조적 변동 여부)",
      "mapping_method": "indirect",
      "parameter": null
    }
  ],
  "event_type_l2_id": 5,
  "mapping_count": 7,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

##### Event

```json
{
  "created_at": "2026-06-19T23:02:46.707523",
  "detail_analysis": {
    "text_chars": 1757,
    "text_excerpt": "사건 요약:\n미국 본토 48개 주의 수출 포함 총수요 전망 하향이 미국 천연가스 선물 약세의 핵심 배경으로 반복 확인된 사안임. 6월 1일 NYMEX 7월물 미국 천연가스 선물은 LSEG가 이번 주 수요 전망을 낮춘 영향으로 3.4% 하락해 mmBtu당 3.177~3.179달러 수준을 기록함. 6월 3일에는 다음 주 수요 전망 하향과 로어 48 생산 감소가 맞물리며 선물이 1주일 저점 부근에서 큰 변동 없이 거래됨. 4월 9일 신규 연결된 WoodMac weekly summary는 4월 7일 미·이란 2주 조건부 휴전, TTF 5월물 US$15.7/mmBtu, 동북아 DES 5월물 US$16.0/mmBtu, 호르무즈 재개와 카타르/UAE 재가동 지연, Wheatstone·Arctic LNG-2 차질을 다룬 별도 글로벌 LNG 이슈 성격임. Event Type상 발전소 utilization 변동에 배정됐으나, 기존 Record 기준 핵심 지표는 발전용 단독 수요가 아니라 수출을 포함한 로어 48 총수요 전망임.\n\n영향 경로:\nLSEG는 수출을 포함한 미국 본토 48개 주 총수요가 이번 주 하루 평균 98.4bcfd이고 다음 주 101.4bcfd로 증가할 것으로 예상했으나, 금요일 전망 등 이전 전망보다 낮아진 수치임. 수요 전망 하향은 미국 내 소비와 LNG 수출 관련 가스 수요 기대를 낮춰 재고 부담과 Henry Hub 계열 가격 약세로 연결되는 경로임. 로이터가 인용한 LSEG 자료 기준 로어 48의 6월 평균 생산량은 하루 109.0bcfd로 5월 109.7bcfd보다 감소해 수요 하향의 일부 가격 약세 압력을 상쇄한 요인임. 여러 LNG 수출 시설의 봄철 정비로 5월 LNG 수출용 가스 흐름도 감소한 점이 실물 수요 둔화에 포함됨. 신규 WoodMac 내용의 호르무즈, 카타르/UAE, Wheatstone, Arctic LNG-2 변수는 글로벌 LNG 공급·물류 리스크 경로이나, 미국 발전소 utilization 변동 Event의 직접 Fundamental 업데이트로 보기에는 제한적임.\n\n시장 반응:\n6월 1일 NYMEX 7월물 미국 천연가스 선물은 mmBtu당 11.1센트, 3.4% 내린 3.179달러에 마감했다는 보도와 3.4% 하락한 mmBtu당 3.177달러를 기록했다는 보도가 함께 제시됨. 6월 3일 선물은 낮아진 다음 주 수요 전망과 생산 감소의 상쇄 효과 속에 1주일 저점 부근에서 큰 변동 없이 거래됨. 5월 29일 종료 주간 재고가 5년 평균보다 5.9% 높은 수준으로 추정된 점도 가격 반등을 제한하는 약세 요인임. 신규 WoodMac summary에서는 미·이란 조건부 휴전으로 TTF 5월물 US$15.7/mmBtu 및 동북아 DES 5월물 US$16.0/mmBtu까지 하락했으나, 이는 별도 지정학·글로벌 LNG 공급 리스크에 따른 가격 반응임.\n\nLNG 시장 관점:\n이번 Event는 미국 LNG 직접 수입 수요가 아니라 미국 내 가스 수요 전망과 발전·수출 포함 총수요 조정이 Henry Hub 가격에 미치는 사안임. 여러 LNG 수출 시설의 봄철 정비로 5월 LNG 수출용 가스 흐름이 감소한 점은 미국 가스 흡수 수요를 낮추는 직접적 Fundamental 요인임. 미국 가스 가격 약세는 LN"
  },
  "event_title_ko": "미국 가스 수요 전망 하향 지속",
  "event_type_l2_id": 5,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-03T13:20:40",
  "mi_event_id": "1125",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[미국 가스 수요] LSEG 전망 하향 지속·신규 글로벌 이슈 별도 → 가격 약세 압력",
  "source_mi_record_ids": [
    2230,
    2288,
    2289,
    2351
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [287]
- scenario_count: 1
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: PASS

##### scenario_id=287 [model_parameter_agent_test] 단기 소규모 발전 차질 흡수

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 00:26.060 (26.060s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "affected_period": "1개월 이하",
    "alt_energy_absorption": "100%",
    "capacity_change_scale": "1 GW 미만",
    "onset_pattern": "점진",
    "recovery_pattern": "급격",
    "structural_change_yn": "단발적"
  },
  "impact": {
    "hh": "중립",
    "jkm": "중립",
    "ttf": "중립"
  },
  "narrative": "발전소 이용률 변화가 작고 다른 전원이 모두 흡수해 가스 수요 전이는 제한적이다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 51,
  "scenario_id": 287,
  "status": "created",
  "title": "[model_parameter_agent_test] 단기 소규모 발전 차질 흡수"
}
```

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

###### Reference Runtime Diagnostics

```json
{
  "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
  "reference_diagnostics": {
    "cell_validation": {
      "by_candidate": {
        "parameter|5|demand|powermixadjustment|powermix": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 1,
          "selected_cell_count": 1,
          "valid_cell_count": 1
        }
      },
      "invalid_cell_count": 0,
      "missing_cell_count": 0,
      "returned_cell_count": 1,
      "selected_cell_count": 1,
      "valid_cell_count": 1
    },
    "selected_references": {
      "basecase_and_lut_count": 0,
      "effective_source_counts": {
        "basecase": 0,
        "lut": 1
      },
      "lut_only_count": 1,
      "references": [
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Energy Source": "Gas",
            "Year": 2026
          },
          "basecase_reference_id": null,
          "candidate_key": "parameter|5|demand|powermixadjustment|powermix",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 0.36505,
          "lut_default_value": 0.36505,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:4166",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PowerMix"
        }
      ],
      "rejected_exact_slot_count": 0,
      "selected_reference_count": 1
    },
    "source": {
      "basecase_record_count": 55,
      "basecase_record_count_by_candidate": {
        "parameter|5|demand|powermixadjustment|powermix": 55
      },
      "lut_record_count": 4200,
      "lut_record_count_by_parameter": {
        "PowerMix": 4200
      },
      "slot_leaf_count": 840,
      "slot_leaf_count_by_candidate": {
        "parameter|5|demand|powermixadjustment|powermix": 840
      }
    }
  },
  "resolved_config": {
    "model_parameter_llm_reasoning_effort": "default",
    "model_parameter_llm_stream_enabled": false,
    "model_parameter_lut_enabled": true,
    "model_parameter_lut_horizon_end_year": 2030,
    "model_parameter_lut_horizon_start_year": 2026,
    "model_parameter_max_parameter_slots": 100,
    "model_parameter_max_value_prompt_basecase_records": 100
  }
}
```


##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 1 | PASS |
| Step3 exact reference | references=1, limit_per_candidate=100, per_candidate=`{"parameter|5|demand|powermixadjustment|powermix": 1}` | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"parameter|5|demand|powermixadjustment|powermix": {"Year": 6}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Year", "Energy Source"]` | `["% Power Mix"]` | 1 | capacity_change_scale가 1GW 미만으로 작아 해당 국가·연도의 Gas 발전 믹스 비중 조정 필요성이 제한적이며, alt_energy_absorption이 100%로 제시되어 발전 차질 또는 증분이 타 에너지원에서 흡수되는 구조입니다. 영향 기간도 1개월 이하이고 단발적·점진 발생 후 급격 회복되는 성격이므로, 2026년 미국 Gas PowerMix는 연간 최종 비중 기준으로 기준값을 유지하는 방식이 적절합니다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.36505 | 해당 좌표의 기준 Gas 발전 믹스 비중은 0.36505입니다. 1GW 미만의 단기 차질이고 타 에너지원 흡수 가능성이 100%로 제시되어 연간 미국 Gas 비중에 유의미한 순변화를 반영하지 않고 최종 입력값을 0.36505로 유지합니다. |

###### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1125,
  "model_param_proposal_id": 396,
  "proposal_completed_dtm": "2026-07-10 18:02:41.593001",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Year",
          "Energy Source"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "capacity_change_scale가 1GW 미만으로 작아 해당 국가·연도의 Gas 발전 믹스 비중 조정 필요성이 제한적이며, alt_energy_absorption이 100%로 제시되어 발전 차질 또는 증분이 타 에너지원에서 흡수되는 구조입니다. 영향 기간도 1개월 이하이고 단발적·점진 발생 후 급격 회복되는 성격이므로, 2026년 미국 Gas PowerMix는 연간 최종 비중 기준으로 기준값을 유지하는 방식이 적절합니다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.36505,
          "rationale": "해당 좌표의 기준 Gas 발전 믹스 비중은 0.36505입니다. 1GW 미만의 단기 차질이고 타 에너지원 흡수 가능성이 100%로 제시되어 연간 미국 Gas 비중에 유의미한 순변화를 반영하지 않고 최종 입력값을 0.36505로 유지합니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 51,
  "scenario_id": 287,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.048 | 3.048 | 3040 | 111 | 3151 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:06.137 | 6.137 | 44811 | 262 | 45073 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:12.890 | 12.890 | 6351 | 515 | 6866 |

### Parameter: Temperature

#### event_type_l2_id=6 겨울 한파

##### Scenario Group

```json
{
  "description": "겨울 한파 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
  "dimension_selected": [
    "period",
    "cold_wave_intensity",
    "entry_gas_inventory",
    "alt_energy_absorption",
    "peak_timing_pattern"
  ],
  "event_type": {
    "event_type_l1_id": 2,
    "event_type_l2_id": 6,
    "level_1_code": "demand",
    "level_1_label": "수요",
    "level_2_code": "winter_cold_wave",
    "level_2_label": "겨울 한파"
  },
  "event_type_l2_id": 6,
  "mi_event_id": 1281,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 52,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 겨울 한파 scenario_group",
  "title": "[model_parameter_agent_test] 겨울 한파 추가 검증"
}
```

##### Dimension Template

```json
[
  {
    "dim_key": "period",
    "display_order": 1,
    "label": "기간",
    "required": true,
    "value_enums": [
      "1개월 이하",
      "3개월",
      "6개월",
      "1년",
      "1년 초과",
      "영구 (회복 불가)",
      "종료 미정"
    ]
  },
  {
    "dim_key": "cold_wave_intensity",
    "display_order": 2,
    "label": "한파 강도",
    "required": true,
    "value_enums": [
      "-2~-3℃: 약",
      "-3~-5℃: 중",
      "-5℃ 이하: 강",
      "기록적(-8℃ 이하·기록 경신)"
    ]
  },
  {
    "dim_key": "entry_gas_inventory",
    "display_order": 3,
    "label": "진입 시점 가스 재고 (평년 대비)",
    "required": false,
    "value_enums": [
      "+20%↑ (매우 여유)",
      "+5%~+20% (여유)",
      "±5% (정상)",
      "-5%~-20% (긴장)",
      "-20%↓ (위험)"
    ]
  },
  {
    "dim_key": "alt_energy_absorption",
    "display_order": 4,
    "label": "타 에너지원 흡수 가능성",
    "required": false,
    "value_enums": [
      "100%",
      "75%",
      "50%",
      "25%",
      "0%"
    ]
  },
  {
    "dim_key": "peak_timing_pattern",
    "display_order": 5,
    "label": "Peak 시점, 패턴",
    "required": false,
    "value_enums": [
      "전체 균등",
      "12월 Peak",
      "1월 Peak",
      "2월 Peak"
    ]
  }
]
```

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "석탄·석유 등 흡수 비율",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "event에 명시된 한파 강도와 적용 기간을 근거로 해당 Country/Year/Month의 Temperature 최종값을 산정한다. 한파는 정상 기온 대비 하향 방향으로 반영하고, 해당 국가 기준 겨울 또는 한파가 발생 가능한 계절의 월을 선택한다. cold_wave_intensity의 온도 편차 범위와 peak_timing_pattern을 참고해 월별 조정폭을 차등 적용한다.",
      "dimension": "cold_wave_intensity (한파 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": null,
      "dimension": "cold_wave_intensity (한파 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "재고는 수급모델 input 아님(Annual Balancing) — 영향 증폭/완화 해석 맥락",
      "dimension": "entry_gas_inventory (진입 시점 가스 재고 (평년 대비))",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "월별 수요 분배",
      "dimension": "peak_timing_pattern (Peak 시점, 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "동절기 월 슬롯",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    }
  ],
  "event_type_l2_id": 6,
  "mapping_count": 6,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

##### Event

```json
{
  "created_at": "2026-06-21T00:14:38.947818",
  "detail_analysis": "사건 요약:\n미국 Northern Plains, Upper Midwest, Great Lakes 지역의 3월 중순 급격한 저온 가능성이 제시된 기존 Event임. National Weather Service 전망을 기반으로 Midwest와 Northeast 난방수요 확대가 예상됨. 2026-03-04 Platts Daily Report는 아시아·대서양 LNG 가격 조정 하락, 미국의 걸프 선박 보험·해군 호위 언급, 카타르 불가항력, 호르무즈 통항 리스크, EU 저장률 29.89%, 고운임을 다룬 내용임. 해당 신규 Record는 미국 중북부 한파 전망에 대한 직접 업데이트가 제한적인 별도 LNG 시장 이슈 성격임.\n\n영향 경로:\n한파 전망은 난방용 천연가스 수요 증가와 저장가스 인출 확대를 통해 미국 내 가스 밸런스를 타이트하게 만드는 경로임. Midwest와 Northeast의 난방수요 확대는 미국 내 수요 측면에서 NYMEX 가스 가격을 지지할 수 있는 요인임. 신규 Platts Report의 EU 저장률 29.89%, 호르무즈 통항 리스크, 카타르 불가항력, 고운임은 글로벌 LNG 수급·물류 리스크에 해당하나 본 Event의 미국 겨울 한파 수요 경로와는 구분 필요함.\n\n시장 반응:\n기존 Event 관점에서 난방수요 확대 기대와 EIA 재고 인출 전망은 NYMEX 천연가스 선물 가격 지지 요인임. 신규 Platts Report에서는 3월 4일 아시아·대서양 LNG 가격이 미국의 걸프 선박 보험·해군 호위 언급 이후 조정 하락한 것으로 언급됨. 다만 해당 가격 조정은 호르무즈·카타르·운임 등 LNG 물류·공급 리스크 관련 반응으로, 미국 중북부 한파 전망의 직접 가격 반응으로 보기는 어려움.\n\nLNG 시장 관점:\n본 Event는 LNG 직접 이슈가 아니라 미국 천연가스 난방수요 이벤트임. 미국 내 한파가 현실화될 경우 내수 가스 수요와 재고 인출을 통해 Henry Hub 및 NYMEX 가격, feedgas 경제성, 미국 LNG 수출 여건에 간접 영향 가능함. 신규 Platts Report의 글로벌 LNG 가격·물류 내용은 참고 정보이나 Event Type인 수요 > 겨울 한파의 경계상 핵심 사건으로 확장하지 않는 것이 적절함.",
  "event_title_ko": "미국 중북부 3월 중순 한파 전망",
  "event_type_l2_id": 6,
  "key_bullets": [],
  "latest_record_first_created": "2026-03-04T00:00:00",
  "mi_event_id": "1281",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[미국 한파] 신규 Platts는 직접 한파 업데이트 제한 → 기존 난방수요·NYMEX 지지 유지",
  "source_mi_record_ids": [
    2417
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [289]
- scenario_count: 1
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: PASS

##### scenario_id=289 [model_parameter_agent_test] 짧은 약한 한파와 전원 흡수

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:06.735 (66.735s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "100%",
    "cold_wave_intensity": "-2~-3℃: 약",
    "entry_gas_inventory": "+20%↑ (매우 여유)",
    "peak_timing_pattern": "단발 피크",
    "period": "1개월 이하"
  },
  "impact": {
    "hh": "중립",
    "jkm": "중립",
    "ttf": "중립"
  },
  "narrative": "짧고 약한 한파가 발생하지만 재고와 대체 전원이 충분해 가스 수요 충격은 제한적이다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 52,
  "scenario_id": 289,
  "status": "created",
  "title": "[model_parameter_agent_test] 짧은 약한 한파와 전원 흡수"
}
```

###### Validation Summary

- target_expected_parameters: `["Temperature"]`
- target_selected_parameters: `["Temperature"]`
- expected_parameters: `["Temperature", "PowerMix"]`
- selected_parameters: `["Temperature", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

###### Reference Runtime Diagnostics

```json
{
  "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
  "reference_diagnostics": {
    "cell_validation": {
      "by_candidate": {
        "6|altenergyabsorption|powermix|demand|powermixadjustment": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 3,
          "selected_cell_count": 3,
          "valid_cell_count": 3
        },
        "6|coldwaveintensity|temperature|demand|weatheradjustment": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 1,
          "selected_cell_count": 1,
          "valid_cell_count": 1
        }
      },
      "invalid_cell_count": 0,
      "missing_cell_count": 0,
      "returned_cell_count": 4,
      "selected_cell_count": 4,
      "valid_cell_count": 4
    },
    "selected_references": {
      "basecase_and_lut_count": 0,
      "effective_source_counts": {
        "basecase": 0,
        "lut": 4
      },
      "lut_only_count": 4,
      "references": [
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Month": 3,
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "6|coldwaveintensity|temperature|demand|weatheradjustment",
          "diagnostics": [
            "lut_only",
            "degree_days_branch=hdd"
          ],
          "effective_source": "lut",
          "llm_reference_value": 5.401235615921525,
          "lut_default_value": 5.401235615921525,
          "lut_reference_id": "lut:Demand_Model_Input_WeatherInput_value_based_t1.csv:row:4:year:2027",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "Temperature"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Energy Source": "Gas",
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "6|altenergyabsorption|powermix|demand|powermixadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 0.35812716254325083,
          "lut_default_value": 0.35812716254325083,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:5006",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PowerMix"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Energy Source": "Coal",
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "6|altenergyabsorption|powermix|demand|powermixadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 0.15884317686353724,
          "lut_default_value": 0.15884317686353724,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:5007",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PowerMix"
        },
        {
          "actual_basecase_value": null,
          "axes": {
            "Country": "United States",
            "Energy Source": "Liquids",
            "Year": 2027
          },
          "basecase_reference_id": null,
          "candidate_key": "6|altenergyabsorption|powermix|demand|powermixadjustment",
          "diagnostics": [
            "lut_only"
          ],
          "effective_source": "lut",
          "llm_reference_value": 0.0035100702014040277,
          "lut_default_value": 0.0035100702014040277,
          "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t3.csv:row:5001",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {},
          "parameter_name": "PowerMix"
        }
      ],
      "rejected_exact_slot_count": 0,
      "selected_reference_count": 4
    },
    "source": {
      "basecase_record_count": 205,
      "basecase_record_count_by_candidate": {
        "6|altenergyabsorption|powermix|demand|powermixadjustment": 55,
        "6|coldwaveintensity|temperature|demand|weatheradjustment": 150
      },
      "lut_record_count": 9240,
      "lut_record_count_by_parameter": {
        "PowerMix": 4200,
        "Temperature": 5040
      },
      "slot_leaf_count": 924,
      "slot_leaf_count_by_candidate": {
        "6|altenergyabsorption|powermix|demand|powermixadjustment": 840,
        "6|coldwaveintensity|temperature|demand|weatheradjustment": 84
      }
    }
  },
  "resolved_config": {
    "model_parameter_llm_reasoning_effort": "default",
    "model_parameter_llm_stream_enabled": false,
    "model_parameter_lut_enabled": true,
    "model_parameter_lut_horizon_end_year": 2030,
    "model_parameter_lut_horizon_start_year": 2026,
    "model_parameter_max_parameter_slots": 100,
    "model_parameter_max_value_prompt_basecase_records": 100
  }
}
```


##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 4 | PASS |
| Step3 exact reference | references=4, limit_per_candidate=100, per_candidate=`{"6|altenergyabsorption|powermix|demand|powermixadjustment": 3, "6|coldwaveintensity|temperature|demand|weatheradjustment": 1}` | PASS |
| Step3 value 결과 | value_cells=4, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Country", "Year", "Month"]` | `["Temperature (°C)"]` | 1 | 한파 강도 dimension이 국가·연월별 평균 기온 입력값과 직접 연결되며, 약한 한파 범위는 정상 기온 대비 하향 조정으로 해석된다. 기간은 1개월 이하이고 피크는 단발이므로 선택된 한파 발생 월에만 보수적으로 기온 하향을 적용하며, 재고 여유는 기온 자체가 아니라 수급 충격 완화 맥락으로만 반영한다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Month": 3, "Year": 2027}` | null | 2.901235615921525 | 해당 좌표의 기준 기온 5.401235615921525°C를 미국 3월 평균 기온 기준으로 해석했다. 약한 한파 범위가 -2~-3°C이고 단발 피크인 점을 반영해 중간 수준인 2.5°C를 하향 조정하여 최종 기온을 2.901235615921525°C로 산정했다. |

###### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1281,
  "model_param_proposal_id": 399,
  "proposal_completed_dtm": "2026-07-10 18:03:48.346246",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "WeatherAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Year",
          "Month"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Temperature (°C)"
        ]
      },
      "parameterName": "Temperature",
      "rationale": "한파 강도 dimension이 국가·연월별 평균 기온 입력값과 직접 연결되며, 약한 한파 범위는 정상 기온 대비 하향 조정으로 해석된다. 기간은 1개월 이하이고 피크는 단발이므로 선택된 한파 발생 월에만 보수적으로 기온 하향을 적용하며, 재고 여유는 기온 자체가 아니라 수급 충격 완화 맥락으로만 반영한다.",
      "values": [
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 2.901235615921525,
          "rationale": "해당 좌표의 기준 기온 5.401235615921525°C를 미국 3월 평균 기온 기준으로 해석했다. 약한 한파 범위가 -2~-3°C이고 단발 피크인 점을 반영해 중간 수준인 2.5°C를 하향 조정하여 최종 기온을 2.901235615921525°C로 산정했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Year",
          "Energy Source"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "타 에너지원 흡수 가능성 dimension이 발전 믹스 비중 입력값과 직접 연결되며, 100% 흡수는 한파로 인한 전력 측 추가 수요가 가스 비중 상승으로 이어지지 않고 석탄·석유 등 대체 전원으로 흡수되는 구조로 해석된다. 다만 기간이 짧고 한파가 약하며 재고가 매우 여유로운 중립 시나리오이므로 연간 발전 믹스에는 매우 작은 재배분만 적용하고, 가스는 하향, 대체 전원은 상향하는 방식으로 제안한다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0.35562716254325083,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.35812716254325083을 연간 비중으로 해석했다. 한파가 1개월 이하의 약한 단발 이벤트이고 대체 전원 흡수가 100% 가능하므로 가스 비중 상승은 배제하되, 전력 측 흡수 효과를 반영해 0.0025포인트만 하향하여 0.35562716254325083으로 산정했다."
        },
        {
          "Country": "United States",
          "Energy Source": "Coal",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0.16109317686353725,
          "rationale": "해당 좌표의 기준 석탄 발전 비중 0.15884317686353724를 연간 비중으로 해석했다. 대체 전원 흡수의 대부분을 석탄이 담당하는 보수적 배분으로 보고, 가스에서 줄인 비중 중 0.00225포인트를 석탄에 배분해 0.16109317686353724로 산정했다."
        },
        {
          "Country": "United States",
          "Energy Source": "Liquids",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0.003760070201404028,
          "rationale": "해당 좌표의 기준 석유계 발전 비중 0.0035100702014040277을 연간 비중으로 해석했다. 석유계 발전은 기준 비중이 작으므로 대체 전원 흡수분 중 제한적인 보조 역할만 반영해 0.00025포인트를 상향하고, 최종 비중을 0.0037600702014040277로 산정했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 52,
  "scenario_id": 289,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.127 | 3.127 | 2847 | 129 | 2976 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:20.868 | 20.868 | 59568 | 1311 | 60879 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:38.847 | 38.847 | 6791 | 2658 | 9449 |

### Parameter: LiqUtilAdjustment

#### event_type_l2_id=2 터미널 Utilization 변동

##### Scenario Group

```json
{
  "description": "사건 요약:\n미국 Louisiana Cameron LNG 터미널의 계획 정비 후 완전 생산 재개가 본 Event의 핵심 사건임. 직전 요약 기준 약 2.1 Bcf/d 피드가스 수령과 미국 전체 LNG feedgas 회복 기여가 확인됨. 2026-06-04 Platts Daily Report에는 Cameron LNG의 추가 가동률 변화나 신규 차질 언급이 없어, Event 상태는 정비 종료 후 정상가동 유지로 판단됨.\n\n영향 경로:\nCameron LNG 가동률 회복은 미국 Gulf Coast발 LNG 수출 가능 물량 증가와 cargo 공급 안정성 개선으로 연결됨. 약 2.1 Bcf/d 피드가스 수령은 미국 LNG feedgas 회복을 뒷받침하는 Fundamental 요인임. 신규 Record의 중동 전쟁에 따른 글로벌 LNG 공급 약 20% 제약, 아시아 수요, JKM/TTF 스프레드 확대는 광역 수급 배경이나 Cameron 터미널 Utilization 변동 자체와는 구분 필요함.\n\n시장 반응:\nCameron LNG 정상가동 유지는 단기 미국 LNG 공급 감소 프리미엄을 완화하는 방향의 재료임. 2026-06-04 Platts Daily Report는 글로벌 LNG 공급 제약에도 JKM과 NWE가 소폭 하락했다고 전함. EU 저장률 41.03%, 유럽 LNG 수입 둔화, 투자펀드 순매수 축소가 가격 약세 심리에 함께 작용함.\n\nLNG 시장 관점:\n본 Event의 경계는 Cameron LNG의 정비 후 생산 정상화와 터미널 Utilization 회복임. 신규 Platts Daily Report는 중동 전쟁과 유럽·아시아 가격 배경을 제공하지만, Cameron LNG의 운영 상태를 변경하는 직접 업데이트는 아님. 따라서 Event title은 미국 특정 터미널 정상가동 유지로 유지하고, 글로벌 공급 제약과 JKM/NWE 약세는 시장 배경 및 파생 가격 영향으로만 반영함.",
  "dimension_selected": [
    "period",
    "utilization_change_amount",
    "recovery_pattern"
  ],
  "event_type": {
    "event_type_l1_id": 1,
    "event_type_l2_id": 2,
    "level_1_code": "supply",
    "level_1_label": "공급",
    "level_2_code": "terminal_utilization_change",
    "level_2_label": "터미널 Utilization 변동"
  },
  "event_type_l2_id": 2,
  "mi_event_id": 1175,
  "request_usr_id": 1000085,
  "scenario_count": 6,
  "scenario_group_id": 18,
  "stage": "scenario_created",
  "status": "creating",
  "summary": "[미국 LNG 공급] Cameron 정상가동 지속, JKM·NWE 소폭 하락 → 공급차질 프리미엄 완화",
  "title": "Cameron LNG 정비 후 정상가동 유지"
}
```

##### Dimension Template

```json
[
  {
    "dim_key": "period",
    "display_order": 1,
    "label": "기간",
    "required": true,
    "value_enums": [
      "1개월 이하",
      "3개월",
      "6개월",
      "1년",
      "1년 초과",
      "영구 (회복 불가)",
      "종료 미정"
    ]
  },
  {
    "dim_key": "utilization_change_amount",
    "display_order": 2,
    "label": "Utilization 변화량",
    "required": true,
    "value_enums": [
      "<5%",
      "15%",
      "30%",
      "60%",
      "100%"
    ]
  },
  {
    "dim_key": "onset_pattern",
    "display_order": 3,
    "label": "발생 패턴",
    "required": false,
    "value_enums": [
      "급격",
      "점진"
    ]
  },
  {
    "dim_key": "recovery_pattern",
    "display_order": 4,
    "label": "회복 패턴",
    "required": false,
    "value_enums": [
      "급격",
      "점진",
      "없음 (영구 손실)"
    ]
  },
  {
    "dim_key": "alt_lng_supply_availability",
    "display_order": 5,
    "label": "대체 LNG 공급 가능성",
    "required": false,
    "value_enums": [
      "100%",
      "75%",
      "50%",
      "25%",
      "0%"
    ]
  }
]
```

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "차질로 감소한 LNG 공급을 대체 가능한 다른 공급국/Plant Train의 가동률 상향으로 일부 상쇄한다. alt_lng_supply_availability는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다.",
      "dimension": "alt_lng_supply_availability (대체 LNG 공급 가능성)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.",
      "dimension": "onset_pattern (발생 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "가동률이 basecase 수준으로 회복되는 시점과 월별 회복 경로 판단에 사용한다.",
      "dimension": "recovery_pattern (회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "차질 또는 회복 대상 LNG Plant Train의 가동률 최종값을 산정한다. utilization_change_amount는 basecase 대비 가동률 하향·상향 조정폭의 주된 근거로 사용하고, period/onset_pattern/recovery_pattern은 적용 월과 월별 변화 경로에 반영한다. 단기·부분 차질은 생산량 직접 입력보다 Train 가동률 조정을 우선한다.",
      "dimension": "utilization_change_amount (Utilization 변화량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": null,
      "dimension": "utilization_change_amount (Utilization 변화량)",
      "mapping_method": "na",
      "parameter": null
    }
  ],
  "event_type_l2_id": 2,
  "mapping_count": 6,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

##### Event

```json
{
  "created_at": "2026-06-19T23:24:46.208920",
  "detail_analysis": "사건 요약:\n미국 Louisiana Cameron LNG 터미널의 계획 정비 후 완전 생산 재개와 이후 정상가동 유지가 본 Event의 핵심임. 직전 요약 기준 약 2.1 Bcf/d 피드가스 수령이 확인됨. 이번 신규 Record 1~3에는 Cameron LNG의 추가 가동률 변화나 신규 차질 언급 없음. 2026-06-04 Platts Daily Report가 가장 최신 Record이며, Event 상태는 정비 종료 후 정상가동 유지로 판단됨.\n\n영향 경로:\nCameron LNG 가동률 회복은 미국 Gulf Coast발 LNG 수출 가능 물량 증가와 cargo 공급 안정성 개선으로 연결됨. 약 2.1 Bcf/d 피드가스 수령은 미국 LNG feedgas 회복을 뒷받침하는 Fundamental 요인임. 2026-03-03 QatarEnergy 생산 중단과 호르무즈 통항·보험 차질, 2026-03-04 카타르 불가항력과 고운임, 2026-06-04 중동 전쟁에 따른 글로벌 LNG 공급 약 20% 제약은 광역 공급 리스크 배경임. 해당 요소들은 Cameron 터미널 Utilization 변동 자체와는 구분됨.\n\n시장 반응:\nCameron LNG 정상가동 유지는 단기 미국 LNG 공급 감소 프리미엄을 완화하는 방향의 재료임. 2026-03-03 Platts Daily Report는 QatarEnergy 생산 중단과 호르무즈 통항·보험 차질로 JKM이 3년여 최고치로 급등하고 NWE·GCM·운임도 동반 상승했다고 전함. 2026-03-04에는 미국의 걸프 선박 보험·해군 호위 언급 이후 아시아·대서양 LNG 가격이 조정 하락했으나 카타르 불가항력, 호르무즈 통항 리스크, EU 저장률 29.89%, 고운임으로 실물 동서 차익은 닫힘. 2026-06-04에는 글로벌 LNG 공급 약 20% 제약에도 JKM과 NWE가 소폭 하락했고, EU 저장률 41.03%, 유럽 LNG 수입 둔화, 투자펀드 순매수 축소가 약세 심리에 작용함.\n\nLNG 시장 관점:\n본 Event의 경계는 Cameron LNG의 정비 후 생산 정상화와 터미널 Utilization 회복임. 신규 Platts Daily Report들은 카타르 불가항력, QatarEnergy 생산 중단, 호르무즈 통항·보험 차질, 중동 전쟁, 유럽·아시아 가격 흐름을 제공하나 Cameron LNG의 운영 상태를 변경하는 직접 업데이트는 아님. 따라서 Event title은 미국 특정 터미널 정상가동 유지로 유지하고, JKM 급등 후 조정 및 NWE 변동은 시장 배경과 파생 가격 영향으로만 반영함.",
  "event_title_ko": "Cameron LNG 정상가동 유지",
  "event_type_l2_id": 2,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-04T00:00:00",
  "mi_event_id": "1175",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[미국 LNG 공급] Cameron 정상가동 유지, 광역 리스크에도 JKM·NWE 조정 → 차질 프리미엄 완화",
  "source_mi_record_ids": [
    2393,
    2416,
    2417
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [105]
- scenario_count: 1
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: PASS

##### scenario_id=105 1개월 내 미세 감산 후 정상화

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 00:33.604 (33.604s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "period": "1개월 이하",
    "recovery_pattern": "급격",
    "utilization_change_amount": "<5%"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "neutral",
    "ttf": "neutral"
  },
  "narrative": "기간은 1개월 이하이며 Cameron LNG의 Utilization 변화는 <5% 감소로 제한된다.\nRamp-up은 Step 형태로, 짧은 운영 조정 이후 한 번에 정상 수준으로 복귀하는 흐름이다.\n시장 참여자는 정비 후 정상가동 기조는 유지되지만, 단기 선적 스케줄에는 작은 지연 프리미엄을 반영한다.",
  "probability_delta": 0.0,
  "probability_score": 15.0,
  "scenario_group_id": 18,
  "scenario_id": 105,
  "status": "creating",
  "title": "1개월 내 미세 감산 후 정상화"
}
```

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

###### Reference Runtime Diagnostics

```json
{
  "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
  "reference_diagnostics": {
    "cell_validation": {
      "by_candidate": {
        "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {
          "invalid_cell_count": 0,
          "missing_cell_count": 0,
          "returned_cell_count": 5,
          "selected_cell_count": 5,
          "valid_cell_count": 5
        }
      },
      "invalid_cell_count": 0,
      "missing_cell_count": 0,
      "returned_cell_count": 5,
      "selected_cell_count": 5,
      "valid_cell_count": 5
    },
    "selected_references": {
      "basecase_and_lut_count": 5,
      "effective_source_counts": {
        "basecase": 5,
        "lut": 0
      },
      "lut_only_count": 0,
      "references": [
        {
          "actual_basecase_value": 0.8971397151184897,
          "axes": {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T1",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": "Supply:LiqUtilAdjustment:R155C40",
          "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "capacity_transform=mtpm_x_12"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.8971397151184897,
          "lut_default_value": 0.8966636468390256,
          "lut_reference_id": "lut:BCLiquefaction.csv:row:19213",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {
            "Life Cycle Category": "Operational",
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 103
          },
          "parameter_name": "LiqUtilAdjustment"
        },
        {
          "actual_basecase_value": 0.8971397151184897,
          "axes": {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T2",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": "Supply:LiqUtilAdjustment:R156C40",
          "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "capacity_transform=mtpm_x_12"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.8971397151184897,
          "lut_default_value": 0.8966636468390256,
          "lut_reference_id": "lut:BCLiquefaction.csv:row:19225",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {
            "Life Cycle Category": "Operational",
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 103
          },
          "parameter_name": "LiqUtilAdjustment"
        },
        {
          "actual_basecase_value": 0.8971397151184897,
          "axes": {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T3",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": "Supply:LiqUtilAdjustment:R157C40",
          "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "capacity_transform=mtpm_x_12"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.8971397151184897,
          "lut_default_value": 0.8966636468390256,
          "lut_reference_id": "lut:BCLiquefaction.csv:row:19237",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {
            "Life Cycle Category": "Operational",
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 103
          },
          "parameter_name": "LiqUtilAdjustment"
        },
        {
          "actual_basecase_value": 0.0,
          "axes": {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T4",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": "Supply:LiqUtilAdjustment:R158C40",
          "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "capacity_transform=mtpm_x_12"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.0,
          "lut_default_value": 0.0,
          "lut_reference_id": "lut:BCLiquefaction.csv:row:29317",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {
            "Life Cycle Category": "Planned",
            "Nameplate Capacity (MTPA)": 6,
            "Period": 103
          },
          "parameter_name": "LiqUtilAdjustment"
        },
        {
          "actual_basecase_value": 0.0,
          "axes": {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T5",
            "Month": 7,
            "Year": 2026
          },
          "basecase_reference_id": "Supply:LiqUtilAdjustment:R267C40",
          "candidate_key": "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment",
          "diagnostics": [
            "actual_basecase_overrides_lut_default",
            "capacity_transform=mtpm_x_12"
          ],
          "effective_source": "basecase",
          "llm_reference_value": 0.0,
          "lut_default_value": 0.0,
          "lut_reference_id": "lut:BCLiquefaction.csv:row:32339",
          "lut_version": "e1e19f78d71b32c49d1a3b205e876d644b7d1e225aac91c8e0f3b81709b47809",
          "metadata": {
            "Life Cycle Category": "Speculative",
            "Nameplate Capacity (MTPA)": 4.99,
            "Period": 103
          },
          "parameter_name": "LiqUtilAdjustment"
        }
      ],
      "rejected_exact_slot_count": 0,
      "selected_reference_count": 5
    },
    "source": {
      "basecase_record_count": 14411,
      "basecase_record_count_by_candidate": {
        "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": 14411
      },
      "lut_record_count": 19366,
      "lut_record_count_by_parameter": {
        "LiqUtilAdjustment": 19366
      },
      "slot_leaf_count": 347,
      "slot_leaf_count_by_candidate": {
        "2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": 347
      }
    }
  },
  "resolved_config": {
    "model_parameter_llm_reasoning_effort": "default",
    "model_parameter_llm_stream_enabled": false,
    "model_parameter_lut_enabled": true,
    "model_parameter_lut_horizon_end_year": 2030,
    "model_parameter_lut_horizon_start_year": 2026,
    "model_parameter_max_parameter_slots": 100,
    "model_parameter_max_value_prompt_basecase_records": 100
  }
}
```


##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 5 | PASS |
| Step3 exact reference | references=5, limit_per_candidate=100, per_candidate=`{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": 5}` | PASS |
| Step3 value 결과 | value_cells=5, basecaseValue_present=5 | PASS |
| Step2 slot axis value 수 | `{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Year", "Month", "Period", "Life Cycle Category", "Nameplate Capacity (MTPA)"]` | `["LiqUtilAdjustment"]` | 5 | Utilization 변화량이 '<5%'로 제시되어 Cameron LNG의 단기·부분 감산을 Train별 최종 가동률에 직접 반영하는 parameter이다. 기간은 '1개월 이하'로 2026년 7월 한 달에만 적용하고, 회복 패턴은 급격한 정상화이므로 해당 월에 미세 하향 후 이후 정상 수준으로 복귀하는 구조로 해석한다. 제안값은 정상가동 유지와 가격 영향 중립성을 감안해 기준 가동률에서 5% 미만의 보수적 하향만 반영하며, 이미 기준값이 0인 Train은 하한 제약상 유지한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.8671397151184898 | 해당 좌표의 기준 가동률 0.8971397151184897에 대해, 1개월 이하의 미세 감산 시나리오와 '<5%' 변화 조건을 반영해 3%p 하향한 최종 가동률 0.8671397151184897을 적용한다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.8671397151184898 | 해당 좌표의 기준 가동률 0.8971397151184897에 대해, 동일한 Cameron LNG 단기 운영 조정이 Train 전반에 균등하게 나타나는 것으로 보고 3%p 하향한 최종 가동률 0.8671397151184897을 적용한다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.8671397151184898 | 해당 좌표의 기준 가동률 0.8971397151184897에 대해, '<5%' 감산 범위 안에서 가격 영향이 중립적인 수준의 미세 조정으로 해석하여 3%p 하향한 최종 가동률 0.8671397151184897을 적용한다. |
| 4 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T4", "Life Cycle Category": "Planned", "Month": 7, "Nameplate Capacity (MTPA)": 6, "Period": 103, "Year": 2026}` | 0.0 | 0.0 | 해당 좌표의 기준 가동률이 0.0이므로 미세 감산을 추가로 반영해도 0~1 입력 범위의 하한을 밑돌 수 없다. 따라서 최종 가동률은 기준값과 동일한 0.0으로 유지한다. |
| 5 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T5", "Life Cycle Category": "Speculative", "Month": 7, "Nameplate Capacity (MTPA)": 4.99, "Period": 103, "Year": 2026}` | 0.0 | 0.0 | 해당 좌표의 기준 가동률이 0.0인 상태이므로 '<5%'의 단기 감산 시나리오를 적용하더라도 음수 가동률은 허용되지 않는다. 이에 따라 최종 가동률은 0.0으로 유지한다. |

###### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1175,
  "model_param_proposal_id": 398,
  "proposal_completed_dtm": "2026-07-10 18:03:27.747524",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Year",
          "Month",
          "Period",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "Utilization 변화량이 '<5%'로 제시되어 Cameron LNG의 단기·부분 감산을 Train별 최종 가동률에 직접 반영하는 parameter이다. 기간은 '1개월 이하'로 2026년 7월 한 달에만 적용하고, 회복 패턴은 급격한 정상화이므로 해당 월에 미세 하향 후 이후 정상 수준으로 복귀하는 구조로 해석한다. 제안값은 정상가동 유지와 가격 영향 중립성을 감안해 기준 가동률에서 5% 미만의 보수적 하향만 반영하며, 이미 기준값이 0인 Train은 하한 제약상 유지한다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.8971397151184897,
          "proposedValue": 0.8671397151184898,
          "rationale": "해당 좌표의 기준 가동률 0.8971397151184897에 대해, 1개월 이하의 미세 감산 시나리오와 '<5%' 변화 조건을 반영해 3%p 하향한 최종 가동률 0.8671397151184897을 적용한다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.8971397151184897,
          "proposedValue": 0.8671397151184898,
          "rationale": "해당 좌표의 기준 가동률 0.8971397151184897에 대해, 동일한 Cameron LNG 단기 운영 조정이 Train 전반에 균등하게 나타나는 것으로 보고 3%p 하향한 최종 가동률 0.8671397151184897을 적용한다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.8971397151184897,
          "proposedValue": 0.8671397151184898,
          "rationale": "해당 좌표의 기준 가동률 0.8971397151184897에 대해, '<5%' 감산 범위 안에서 가격 영향이 중립적인 수준의 미세 조정으로 해석하여 3%p 하향한 최종 가동률 0.8671397151184897을 적용한다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T4",
          "Life Cycle Category": "Planned",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.0,
          "proposedValue": 0.0,
          "rationale": "해당 좌표의 기준 가동률이 0.0이므로 미세 감산을 추가로 반영해도 0~1 입력 범위의 하한을 밑돌 수 없다. 따라서 최종 가동률은 기준값과 동일한 0.0으로 유지한다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T5",
          "Life Cycle Category": "Speculative",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.99,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.0,
          "proposedValue": 0.0,
          "rationale": "해당 좌표의 기준 가동률이 0.0인 상태이므로 '<5%'의 단기 감산 시나리오를 적용하더라도 음수 가동률은 허용되지 않는다. 이에 따라 최종 가동률은 0.0으로 유지한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 18,
  "scenario_id": 105,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.169 | 3.169 | 3074 | 78 | 3152 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:09.045 | 9.045 | 70765 | 681 | 71446 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:18.183 | 18.183 | 6998 | 1394 | 8392 |

## 최종 요약

- ERROR_COUNT: 0
- PLANNED_SCENARIO_EXECUTIONS: 5
- COMPLETED_SCENARIO_EXECUTIONS: 5
- PARAMETER_SCENARIOS: `{"GDP": 305, "LiqUtilAdjustment": 105, "PMI": 306, "PowerMix": 287, "Temperature": 289}`
- PARAMETER_SCENARIO_STATUS: `{"GDP=305": true, "LiqUtilAdjustment=105": true, "PMI=306": true, "PowerMix=287": true, "Temperature=289": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.

## Claude Actual Result Review

- 검토 방식: Claude Code CLI read-only feedback (`fc23336b-5578-4f90-876f-0f96cba0ae6e`)
- 검토 범위: 최종 명세 D-01~D-11, 5개 scenario의 context/mapping/reference diagnostics/value/DB row, 아래 9개 품질 기준
- 결론: 필수 코드 수정 또는 재실행이 필요한 finding 없음
- 계약 확인: `ERROR_COUNT=0`, 5/5 PASS, invalid/missing/rejected exact cell 0, LUT-only `basecaseValue=null`, LiqUtil authoritative metadata 복원, resolved config와 LUT version 일치
- 품질 REVIEW 1: Temperature의 2027-03 선택은 실행일 기준 가장 가까운 미래의 같은 월로 이월한 정책상 유효하지만, “차기 동절기 재발” 가정이 rationale에 명시되지 않았다.
- 품질 REVIEW 2: PowerMix LUT-only no-change는 D-03/D-05에 맞지만 운영 JSON의 `null -> 0.36505`만 보면 신규값 제안으로 오독할 수 있다. 내부 LUT provenance와 rationale을 함께 봐야 한다.
- 품질 REVIEW 3: LiqUtil T4 Planned/T5 Speculative의 `0 -> 0`은 exact/Closed 제외/no-change 계약상 유효하지만 운영 중인 T1~T3 감산 시나리오에는 불필요한 리뷰 노이즈다. 서버 필터링은 D-05를 위반할 수 있어 적용하지 않았고, 향후 prompt 품질 개선 후보로 남긴다.

## Parameter Quality Evaluation

### GDP — scenario_id=305, proposal_id=395

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | DB direct mapping 후보에 GDP가 있고 `target_expected_present=YES`, `target_selected_present=YES`, final DB row에도 GDP가 저장됐다. | - |
| 2 | slot 선정과 좌표/범위가 유효한가 | PASS | China/United States × 2026/2027의 4개 exact key가 선택됐고 GDP cell은 selected=returned=valid=4, missing/invalid/rejected=0이다. | - |
| 3 | basecase 기반 slot 선정이 개연성 있는가 | PASS | 4개 모두 actual basecase가 있으며 이벤트의 국가별 2026/2027 정량 성장 전망과 직접 대응한다. | - |
| 4 | basecase에 없는 slot의 추가 선정이 개연성 있는가 | N/A | 대상 GDP의 4개 selected slot은 모두 actual basecase가 존재한다. | - |
| 5 | basecase에 없는 slot을 미선정한 것이 타당한가 | PASS | 이벤트가 수치로 지목한 국가는 China/United States, 연도는 2026/2027이며 이 4개 좌표가 모두 선택됐다. 추가 LUT-only GDP 좌표가 필요하다는 근거는 없다. | - |
| 6 | value 범위·형식과 시나리오 정합성이 유효한가 | PASS | 소수 성장률 형식으로 China 0.045/0.043, United States 0.020/0.018을 제안했고 이벤트의 4.5%/4.3%/2.0%/1.8% 전망과 일치한다. | - |
| 7 | basecase value를 적절히 변경했나 | PASS | China 0.042→0.045/0.043, United States 0.019→0.020 및 0.020→0.018로 정량 전망을 최종값에 반영했다. | - |
| 8 | basecase가 없던 value를 개연성 있게 선정했나 | N/A | 대상 GDP value에는 `basecaseValue=null`인 cell이 없다. | - |
| 9 | 동일 그룹 dimension에 따라 value 차이가 적절한가 | PASS | 같은 group 60의 경기 충격·1년 scenario 306은 GDP를 0.040/0.039/0.017/0.016으로 더 낮췄다. 경미·1개월 이하인 305와 방향·폭이 명확히 다르다. | - |

### PMI — scenario_id=306, proposal_id=397

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | DB direct mapping 후보에 PMI가 있고 expected/selected target가 모두 YES이며 final DB row에 PMI가 저장됐다. | - |
| 2 | slot 선정과 좌표/범위가 유효한가 | PASS | China/United States의 2026-07~2027-06, 정확히 12개월씩 총 24개 exact cell이다. selected=returned=valid=24, missing/invalid=0이다. | - |
| 3 | basecase 기반 slot 선정이 개연성 있는가 | PASS | China 2026-07~12의 6개 actual basecase 49.5는 경기 충격이 시작되는 1년 기간의 첫 반기와 직접 대응한다. | - |
| 4 | basecase에 없는 slot의 추가 선정이 개연성 있는가 | PASS | 나머지 18개 LUT-only cell은 두 국가의 1년 전체 기간을 끊김 없이 채우며, 2027-06까지라는 기간 해석과 일치한다. | - |
| 5 | basecase에 없는 slot을 미선정한 것이 타당한가 | N/A | 필요한 1년 구간의 basecase 부재 좌표를 LUT-only로 실제 선택했다. | - |
| 6 | value 범위·형식과 시나리오 정합성이 유효한가 | PASS | PMI 숫자 형식이며 모두 48.5~49.0의 위축 구간이다. “경기 충격·1년·수요 감소” 방향과 일치한다. | - |
| 7 | basecase value를 적절히 변경했나 | PASS | China의 actual basecase 49.5를 2026-07~12 동안 48.5로 1.0pt 낮춰 지속 충격을 반영했다. | - |
| 8 | basecase가 없던 value를 개연성 있게 선정했나 | PASS | LUT 기준 50.0에서 China 49.0, United States 48.7/48.5로 낮췄고 국가·연도별 성장 둔화 차이를 rationale에 설명했다. | - |
| 9 | 동일 그룹 dimension에 따라 value 차이가 적절한가 | PASS | 같은 group 60의 경미·1개월 이하 scenario 305는 PMI 2개만 49.5/49.9로 제안했다. 306은 24개로 기간을 확대하고 하향 폭도 키웠다. | - |

### PowerMix — scenario_id=287, proposal_id=396

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | 두 direct mapping이 하나의 PowerMix candidate로 merge됐고 expected/selected target가 모두 YES, DB row에도 저장됐다. | - |
| 2 | slot 선정과 좌표/범위가 유효한가 | PASS | `United States + Gas + 2026` 한 개가 LUT exact key이며 selected=returned=valid=1, missing/invalid/rejected=0이다. | - |
| 3 | basecase 기반 slot 선정이 개연성 있는가 | N/A | 대상 slot은 LUT-only이며 actual basecase가 없다. | - |
| 4 | basecase에 없는 slot의 추가 선정이 개연성 있는가 | PASS | 이벤트의 미국 가스 발전 맥락과 scenario의 1GW 미만·대체전원 100% 흡수 조건에 직접 대응하는 단일 LUT-only slot이다. | - |
| 5 | basecase에 없는 slot을 미선정한 것이 타당한가 | N/A | 관련 LUT-only slot을 실제 선택했다. | - |
| 6 | value 범위·형식과 시나리오 정합성이 유효한가 | PASS | 0~1 비중 범위의 0.36505이며, 짧고 작은 차질을 대체 전원이 전부 흡수하므로 연간 Gas mix를 유지한다는 rationale이 있다. | - |
| 7 | basecase value를 적절히 변경했나 | N/A | actual basecase가 없어 운영 `basecaseValue`는 null이다. | - |
| 8 | basecase가 없던 value를 개연성 있게 선정했나 | REVIEW | 내부 LUT reference 0.36505와 동일한 explicit no-change로 D-03/D-05에는 맞다. 다만 운영 JSON만 보면 `null→0.36505` 신규값으로 오독할 수 있다. | 리뷰 UI/가이드에서 LUT provenance와 `llm_reference_value`를 함께 표시한다. 운영 schema에는 LUT 값을 basecase로 투영하지 않는다. |
| 9 | 동일 그룹 dimension에 따라 value 차이가 적절한가 | N/A | group 51에서는 이번 요청으로 한 scenario만 실행했다. | 같은 그룹의 강한/장기 시나리오를 별도 회귀 세트로 비교할 수 있다. |

### Temperature — scenario_id=289, proposal_id=399

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | Temperature direct mapping이 expected/selected target에 모두 존재하고 final DB row에도 저장됐다. | - |
| 2 | slot 선정과 좌표/범위가 유효한가 | REVIEW | `United States + 2027-03`은 catalog exact key이고 cell validation도 전부 PASS다. 다만 이벤트의 2026-03 맥락을 실행일 이후 가장 가까운 같은 월로 이월한 “재발” 가정이 rationale에 명시되지 않았다. | 과거 명시 월을 미래 동일 월로 이월할 때 rationale에 이월 사유와 재발 가정을 명시하도록 prompt를 보강한다. |
| 3 | basecase 기반 slot 선정이 개연성 있는가 | N/A | 대상 Temperature slot은 LUT-only다. | - |
| 4 | basecase에 없는 slot의 추가 선정이 개연성 있는가 | PASS | 미국 3월 한 개만 선택해 “1개월 이하·단발 피크”를 반영했고 `degree_days_branch=hdd` exact LUT 근거가 있다. | - |
| 5 | basecase에 없는 slot을 미선정한 것이 타당한가 | N/A | 시나리오 관련 LUT-only slot을 실제 선택했다. | - |
| 6 | value 범위·형식과 시나리오 정합성이 유효한가 | PASS | LUT 기준 5.4012356°C에서 약한 한파 범위 -2~-3°C의 중간인 2.5°C를 내려 2.9012356°C로 제안했다. | - |
| 7 | basecase value를 적절히 변경했나 | N/A | actual basecase가 없어 운영 `basecaseValue`는 null이다. | - |
| 8 | basecase가 없던 value를 개연성 있게 선정했나 | PASS | LUT reference와 cold_wave_intensity를 수치적으로 연결했고 단일 월만 변경해 기간을 과도하게 확대하지 않았다. | - |
| 9 | 동일 그룹 dimension에 따라 value 차이가 적절한가 | N/A | group 52에서는 이번 요청으로 한 scenario만 실행했다. | 같은 그룹의 강한/장기 한파 scenario를 별도 회귀 세트로 비교할 수 있다. |

### LiqUtilAdjustment — scenario_id=105, proposal_id=398

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | LiqUtilAdjustment direct mapping이 expected/selected target에 모두 존재하며 final DB row에 저장됐다. | - |
| 2 | slot 선정과 좌표/범위가 유효한가 | PASS | Cameron LNG T1~T5의 2026-07 exact key 5개이며 selected=returned=valid=5, missing/invalid/rejected=0이다. Period 103, lifecycle, MTPA metadata도 authoritative reference에서 복원됐다. | - |
| 3 | basecase 기반 slot 선정이 개연성 있는가 | REVIEW | Operational T1~T3은 단기 미세 감산과 직접 관련된다. 반면 Planned T4와 Speculative T5는 basecase 0이고 0→0이라 현재 가동 설비 감산의 영향 대상이라고 보기 어렵다. | 서버 필터링은 하지 않는다. 향후 Step2 prompt에서 “영향이 없음을 표시하기 위한 무관 slot 선택”을 줄이는 품질 회귀를 검토한다. |
| 4 | basecase에 없는 slot의 추가 선정이 개연성 있는가 | N/A | 선택된 5개 slot 모두 actual basecase가 존재한다. | - |
| 5 | basecase에 없는 slot을 미선정한 것이 타당한가 | N/A | Cameron LNG의 선택 Train이 모두 basecase에 존재하며 추가 LUT-only Train 필요성은 확인되지 않았다. | - |
| 6 | value 범위·형식과 시나리오 정합성이 유효한가 | PASS | 모든 값이 0~1 범위다. T1~T3은 0.8971397→0.8671397로 3%p 하향해 `<5%` 조건을 지켰고 T4/T5는 하한 0을 유지했다. | - |
| 7 | basecase value를 적절히 변경했나 | PASS | Operational T1~T3의 동일한 단기 운영 조정은 균등 -3%p, basecase가 0인 T4/T5는 음수 방지를 위해 0으로 유지했다. | - |
| 8 | basecase가 없던 value를 개연성 있게 선정했나 | N/A | 대상 value 중 `basecaseValue=null`인 cell이 없다. | - |
| 9 | 동일 그룹 dimension에 따라 value 차이가 적절한가 | N/A | group 18에서는 이번 요청으로 한 scenario만 실행했다. | 같은 그룹의 더 큰 감산/장기 회복 scenario를 별도 회귀 세트로 비교할 수 있다. |
