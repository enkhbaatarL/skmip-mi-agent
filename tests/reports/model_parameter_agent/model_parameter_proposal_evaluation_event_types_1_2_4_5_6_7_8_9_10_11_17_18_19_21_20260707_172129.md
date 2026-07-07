# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-07T17:21:29
- 실행 종료: 2026-07-07T17:41:20
- 총 소요시간: 19:51.567 (1191.567s)
- 대상 event_type_l2_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 17, 18, 19, 21]
- concurrency: 4
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=1 Upstream Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=2 터미널 Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=4 파이프라인 Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=5 발전소 Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=6 겨울 한파: scenario_group 1개, scenario 2개
- event_type_l2_id=7 여름 폭염: scenario_group 1개, scenario 2개
- event_type_l2_id=8 원자력 발전: scenario_group 1개, scenario 2개
- event_type_l2_id=9 재생에너지: scenario_group 1개, scenario 2개
- event_type_l2_id=10 석탄 발전: scenario_group 1개, scenario 2개
- event_type_l2_id=11 자연재해: scenario_group 1개, scenario 2개
- event_type_l2_id=17 지정학적 긴장 및 전쟁·군사분쟁: scenario_group 1개, scenario 2개
- event_type_l2_id=18 경제 제재 및 무역 제한: scenario_group 1개, scenario 2개
- event_type_l2_id=19 정책/규제 변화: scenario_group 1개, scenario 2개
- event_type_l2_id=21 국가별 경기: scenario_group 1개, scenario 2개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 1 | 49 | 283 | OK | 1 | 03:27.523 | 207.523s |
| 1 | 49 | 284 | OK | 1 | 04:49.480 | 289.480s |
| 2 | 18 | 105 | OK | 1 | 02:55.599 | 175.599s |
| 2 | 18 | 106 | OK | 1 | 02:04.519 | 124.519s |
| 4 | 50 | 285 | OK | 1 | 03:34.631 | 214.631s |
| 4 | 50 | 286 | OK | 1 | 05:47.232 | 347.232s |
| 5 | 51 | 287 | ERROR | 2 | 02:13.193 | 133.193s |
| 5 | 51 | 288 | OK | 1 | 01:22.029 | 82.029s |
| 6 | 52 | 289 | OK | 1 | 02:43.412 | 163.412s |
| 6 | 52 | 290 | OK | 1 | 03:06.916 | 186.916s |
| 7 | 53 | 291 | OK | 1 | 01:31.053 | 91.053s |
| 7 | 53 | 292 | OK | 1 | 02:21.171 | 141.171s |
| 8 | 54 | 293 | OK | 1 | 00:56.092 | 56.092s |
| 8 | 54 | 294 | OK | 1 | 01:22.659 | 82.659s |
| 9 | 44 | 261 | OK | 1 | 01:27.265 | 87.265s |
| 9 | 44 | 262 | OK | 1 | 01:31.142 | 91.142s |
| 10 | 45 | 267 | OK | 1 | 01:34.248 | 94.248s |
| 10 | 45 | 268 | OK | 1 | 01:04.946 | 64.946s |
| 11 | 47 | 279 | OK | 1 | 03:29.855 | 209.855s |
| 11 | 47 | 280 | OK | 1 | 03:27.569 | 207.569s |
| 17 | 16 | 92 | OK | 1 | 03:22.365 | 202.365s |
| 17 | 16 | 93 | OK | 1 | 06:20.772 | 380.772s |
| 18 | 22 | 129 | OK | 1 | 03:11.496 | 191.496s |
| 18 | 22 | 130 | OK | 1 | 05:29.765 | 329.765s |
| 19 | 48 | 281 | OK | 1 | 01:26.341 | 86.341s |
| 19 | 48 | 282 | OK | 1 | 01:26.022 | 86.022s |
| 21 | 60 | 305 | OK | 1 | 01:16.592 | 76.592s |
| 21 | 60 | 306 | OK | 1 | 02:12.735 | 132.735s |

## 호출 결과

### event_type_l2_id=1 Upstream Utilization 변동

#### Scenario Group

```json
{
  "description": "Upstream Utilization 변동 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
  "dimension_selected": [
    "period",
    "utilization_change_amount",
    "onset_pattern",
    "recovery_pattern",
    "alt_gas_supply_availability"
  ],
  "event_type": {
    "event_type_l1_id": 1,
    "event_type_l2_id": 1,
    "level_1_code": "supply",
    "level_1_label": "공급",
    "level_2_code": "upstream_utilization_change",
    "level_2_label": "Upstream Utilization 변동"
  },
  "event_type_l2_id": 1,
  "mi_event_id": 1117,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 49,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 Upstream Utilization 변동 scenario_group",
  "title": "[model_parameter_agent_test] Upstream Utilization 변동 추가 검증"
}
```

#### Dimension Template

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
    "label": "Utilization 변화 폭",
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
      "없음 (영구)"
    ]
  },
  {
    "dim_key": "alt_gas_supply_availability",
    "display_order": 5,
    "label": "대체 가스 공급 가능성",
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

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "LNG 전환 대체 시 타 공급국 액화 가동률 상향 : LNG 전환 대체 공급 경로가 설명 가능한 인접·시장연결 공급국의 가용 액화설비에 차등 배분",
      "dimension_key": "alt_gas_supply_availability",
      "dimension_label": "대체 가스 공급 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 283,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 284,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "SupplyDisruption",
      "comment": "타 가스전 증산(음의 disruption)으로 부족분 상쇄 : 차질 지역과 연결 가능한 동일 권역·시장 내 가스전의 증산 가능량을 음(-)의 SupplyDisruption으로 배분",
      "dimension_key": "alt_gas_supply_availability",
      "dimension_label": "대체 가스 공급 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "VolumeAdjustment",
        "model_table": "table2",
        "semantic_axes": "Upstream 공급량 override — Country·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 283,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 284,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격/점진 — 값의 시계열 형태",
      "dimension_key": "onset_pattern",
      "dimension_label": "발생 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "점진",
          "scenario_id": 283,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "급격",
          "scenario_id": 284,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "Parameter 변경 시간축 결정",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 283,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "6개월",
          "scenario_id": 284,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "원상복귀 시간축",
      "dimension_key": "recovery_pattern",
      "dimension_label": "회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "급격",
          "scenario_id": 283,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "점진",
          "scenario_id": 284,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "SupplyDisruption",
      "comment": "Province/Basin 생산 차질량(Bcm 또는 %); 증산은 음(-)",
      "dimension_key": "utilization_change_amount",
      "dimension_label": "Utilization 변화 폭",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "VolumeAdjustment",
        "model_table": "table2",
        "semantic_axes": "Upstream 공급량 override — Country·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "<5%",
          "scenario_id": 283,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "60%",
          "scenario_id": 284,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 1,
  "mapping_count": 6,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:00:44.261593",
  "detail_analysis": "사건 요약:\n노르웨이 석유업계와 Styrke, Lederne, Safe 등 3개 노조가 오슬로에서 이틀간 국가 중재 임금 협상에 들어가며 파업 방지에 나선 상황임. 오프쇼어 노르웨이는 6월 3일 협상 결렬 시 6월 5일부터 해상 석유·가스 생산이 하루 약 4만5,500배럴(석유환산 기준), 초기 약 1% 감소할 수 있다고 밝힘. 노조 자료 기준 협상 대상 약 8,100명 중 617명이 1차 파업에 참여할 예정이며 전체 해상 석유·가스 노동자의 약 8% 수준임. 이번 업데이트는 파업 위협이 유지되는 가운데 잠재 생산 감소 규모와 초기 영향 자산이 구체화된 상태임.\n\n영향 경로:\n초기 영향 대상으로 스타트피오르 A, 울라, 드라우겐, 에코피스크 등이 제시됨. 파업이 실행될 경우 노르웨이 해상 upstream 생산 감소가 발생하고, 이는 유럽향 파이프라인 가스 공급 안정성에 대한 리스크로 연결될 수 있음. 현재 제시된 감소 규모는 하루 약 4만5,500배럴(석유환산 기준), 초기 약 1%로 제한적이나, 노조가 이후 파업 확대 가능성을 언급한 점이 추가 수급 리스크 요인임. 노조 요구는 물가상승률을 웃도는 임금 인상과 계약 조건 변경임.\n\n시장 반응:\n신규 기사에는 TTF, JKM 등 구체적인 스팟·선물 가격 수준이나 Forward 변동 수치가 제시되지 않음. 다만 노르웨이가 유럽 주요 가스 공급원이라는 점에서 파업 실행 또는 확대 시 유럽 가스 가격에 공급 리스크 프리미엄이 반영될 가능성 있음. 현재 가격 방향은 실제 협상 결과, 6월 5일 파업 실행 여부, 초기 1% 감소가 확대되는지 여부에 민감한 구조임.\n\nLNG 시장 관점:\n이번 사건은 LNG 설비나 LNG cargo의 직접 차질이 아니라 노르웨이 해상 upstream utilization 변동 위험임. 그러나 노르웨이 파이프라인 가스 공급 차질이 발생하거나 확대될 경우 유럽의 대체 조달 수요가 LNG 시장으로 일부 전이될 수 있음. 초기 감소 규모가 제한적으로 제시된 만큼 단기 LNG 수요 영향은 잠재적 성격이나, 파업 확대 시 유럽 LNG 수입 수요와 아시아·유럽 간 가격 경쟁에 간접 영향을 줄 수 있음.",
  "event_title_ko": "노르웨이 해상 파업 시 생산 1% 감소 위험",
  "event_type_l2_id": 1,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-03T08:55:57",
  "mi_event_id": "1117",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[노르웨이 가스 공급] 6월 5일 파업 위협 지속 → 유럽 가스 공급 프리미엄 가능",
  "source_mi_record_ids": [
    2282,
    2339,
    2340,
    2341
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [283, 284]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=283 [model_parameter_agent_test] 단기 미세 감산과 대체 공급 충분

- 소요시간: 03:27.523 (207.523s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_gas_supply_availability": "100%",
    "onset_pattern": "점진",
    "period": "1개월 이하",
    "recovery_pattern": "급격",
    "utilization_change_amount": "<5%"
  },
  "impact": {
    "hh": "중립",
    "jkm": "중립",
    "ttf": "중립"
  },
  "narrative": "노르웨이 upstream 설비가 단기적으로 소폭 감산하지만 대체 가스 공급이 충분해 시장 영향은 제한적이다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 49,
  "scenario_id": 283,
  "status": "created",
  "title": "[model_parameter_agent_test] 단기 미세 감산과 대체 공급 충분"
}
```

##### Validation Summary

- expected_parameters: `["SupplyDisruption", "LiqUtilAdjustment"]`
- selected_parameters: `["SupplyDisruption", "LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=parameter|1|supply|volumeadjustment|supplydisruption, sheet=VolumeAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 41 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=3, basecaseValue_present=2 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 1 | Utilization 변화 폭이 '<5%'로 제시되어 upstream 공급량 차질을 직접 반영하는 SupplyDisruption이 선택되며, 대체 가스 공급 가능성 100%는 차질 자체를 제거하기보다 다른 공급 경로에서 상쇄될 수 있음을 의미한다. 기간은 1개월 이하이고 발생은 점진, 회복은 급격이므로 현재 기준월에 한정해 소규모 양의 공급 차질을 반영한다. |
| 2 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 2 | 대체 가스 공급 가능성 100%는 노르웨이 upstream 감산분을 시장 연결성이 있는 LNG 공급 경로의 액화 가동률 상향으로 상쇄할 수 있음을 의미하므로 LiqUtilAdjustment가 선택된다. 기간은 1개월 이하이고 시장 영향은 중립으로 제시되어, 유럽 인접성과 낮은 기준 가동률을 가진 대체 공급 슬롯에만 보수적으로 단기 상향을 배분한다. |

##### Proposed Parameter Values

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Norway", "Month": 7, "Year": 2026}` | null | 0.22 | 선택된 좌표는 노르웨이 해상 upstream 차질이 발생하는 직접 대상 국가와 현재 기준월의 1개월 이하 적용 기간에 해당한다. 기사상 초기 생산 감소가 하루 약 4만5,500boe, 약 1% 수준으로 제시되어 이를 30일 기준 가스량으로 환산해 약 0.22Bcm의 단기 공급 차질 최종 입력값으로 설정했다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.9, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.309 | 알제리 Arzew GL1Z는 유럽 인접 대체 LNG 공급원이며 해당 월 기준 가동률이 낮아 단기 상향 여력이 있는 슬롯으로 선택했다. 노르웨이의 약 0.22Bcm 단기 차질을 LNG 기준 약 0.16Mt로 환산한 뒤 Arzew GL1Z와 GL2Z의 월간 명목용량에 비례해 절반 수준으로 배분하여, 기준 가동률 0.19018404907975456에 약 0.119를 더한 최종 가동률 0.309로 설정했다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 8.4, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.309 | 알제리 Arzew GL2Z는 유럽향 대체 공급 경로로 설명 가능하고 해당 월 기준 가동률이 낮아 단기 증산을 배분하기 적합한 슬롯으로 선택했다. 노르웨이의 약 0.22Bcm 단기 차질을 LNG 기준 약 0.16Mt로 환산한 뒤 Arzew GL1Z와 GL2Z의 월간 명목용량에 비례해 나누어, 기준 가동률 0.19018404907975456에 약 0.119를 더한 최종 가동률 0.309로 설정했다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1117,
  "model_param_proposal_id": 33,
  "proposal_completed_dtm": "2026-07-07 17:24:56.571670",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "VolumeAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Volumes (Bcm)"
        ]
      },
      "parameterName": "SupplyDisruption",
      "rationale": "Utilization 변화 폭이 '<5%'로 제시되어 upstream 공급량 차질을 직접 반영하는 SupplyDisruption이 선택되며, 대체 가스 공급 가능성 100%는 차질 자체를 제거하기보다 다른 공급 경로에서 상쇄될 수 있음을 의미한다. 기간은 1개월 이하이고 발생은 점진, 회복은 급격이므로 현재 기준월에 한정해 소규모 양의 공급 차질을 반영한다.",
      "values": [
        {
          "Country": "Norway",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.22,
          "rationale": "선택된 좌표는 노르웨이 해상 upstream 차질이 발생하는 직접 대상 국가와 현재 기준월의 1개월 이하 적용 기간에 해당한다. 기사상 초기 생산 감소가 하루 약 4만5,500boe, 약 1% 수준으로 제시되어 이를 30일 기준 가스량으로 환산해 약 0.22Bcm의 단기 공급 차질 최종 입력값으로 설정했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "대체 가스 공급 가능성 100%는 노르웨이 upstream 감산분을 시장 연결성이 있는 LNG 공급 경로의 액화 가동률 상향으로 상쇄할 수 있음을 의미하므로 LiqUtilAdjustment가 선택된다. 기간은 1개월 이하이고 시장 영향은 중립으로 제시되어, 유럽 인접성과 낮은 기준 가동률을 가진 대체 공급 슬롯에만 보수적으로 단기 상향을 배분한다.",
      "values": [
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.309,
          "rationale": "알제리 Arzew GL1Z는 유럽 인접 대체 LNG 공급원이며 해당 월 기준 가동률이 낮아 단기 상향 여력이 있는 슬롯으로 선택했다. 노르웨이의 약 0.22Bcm 단기 차질을 LNG 기준 약 0.16Mt로 환산한 뒤 Arzew GL1Z와 GL2Z의 월간 명목용량에 비례해 절반 수준으로 배분하여, 기준 가동률 0.19018404907975456에 약 0.119를 더한 최종 가동률 0.309로 설정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.309,
          "rationale": "알제리 Arzew GL2Z는 유럽향 대체 공급 경로로 설명 가능하고 해당 월 기준 가동률이 낮아 단기 증산을 배분하기 적합한 슬롯으로 선택했다. 노르웨이의 약 0.22Bcm 단기 차질을 LNG 기준 약 0.16Mt로 환산한 뒤 Arzew GL1Z와 GL2Z의 월간 명목용량에 비례해 나누어, 기준 가동률 0.19018404907975456에 약 0.119를 더한 최종 가동률 0.309로 설정했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 49,
  "scenario_id": 283,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:06.633 | 6.633 | 2542 | 171 | 2713 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:21.069 | 81.069 | 11906 | 7712 | 19618 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:51.699 | 51.699 | 16712 | 2949 | 19661 |

#### scenario_id=284 [model_parameter_agent_test] 6개월 큰 감산과 대체 공급 제한

- 소요시간: 04:49.480 (289.480s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_gas_supply_availability": "25%",
    "onset_pattern": "급격",
    "period": "6개월",
    "recovery_pattern": "점진",
    "utilization_change_amount": "60%"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "노르웨이 upstream 생산 차질이 급격히 발생하고 6개월간 이어지며 대체 공급이 제한되어 공급 감소 반영이 필요하다.",
  "probability_delta": 4.0,
  "probability_score": 40.0,
  "scenario_group_id": 49,
  "scenario_id": 284,
  "status": "created",
  "title": "[model_parameter_agent_test] 6개월 큰 감산과 대체 공급 제한"
}
```

##### Validation Summary

- expected_parameters: `["SupplyDisruption", "LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=parameter|1|supply|volumeadjustment|supplydisruption, sheet=VolumeAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 96 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=12, basecaseValue_present=12 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 12 | 대체 가스 공급 가능성 25%는 Norway upstream 차질 중 일부가 LNG 전환 대체 공급으로 흡수될 수 있음을 뜻하며, LiqUtilAdjustment는 이 대체 공급 경로의 액화시설 가동률 상향을 직접 반영하는 parameter이다. 6개월 기간, 급격한 발생, 점진 회복 조건을 반영해 유럽 대체 조달과 연결성이 높은 Algeria의 여유 가동률이 큰 Arzew 설비에 우선 배분하고, 가동률은 1.0 상한 내에서 초기에 높인 뒤 후반으로 갈수록 단계적으로 낮췄다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.9, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 해당 월은 6개월 차질의 첫 달로 급격한 발생 구간에 해당하므로 대체 LNG 공급 필요가 가장 높다. 기준 가동률 0.19018404907975456에 대체 공급 가능성 25%를 여유 가동률에 반영해 0.19018404907975456 + (1 - 0.19018404907975456) × 0.25 = 0.3926380368098159로 산정했다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.9, "Period": 113, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 해당 월은 차질 초기의 높은 대체 조달 필요가 유지되는 구간이다. 기준 가동률 0.19018404907975456에 여유 가동률의 25%를 추가해 최종 가동률을 0.3926380368098159로 산정했다. |
| 3 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.9, "Period": 114, "Year": 2026}` | 0.19018404907975456 | 0.3521472392638037 | 점진 회복을 반영해 3개월 차부터 대체 공급 가동률 상향 강도를 초기의 80%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.8을 더해 0.3521472392638037로 산정했다. |
| 4 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 7.9, "Period": 115, "Year": 2026}` | 0.19018404907975456 | 0.31165644171779133 | 6개월 차질의 중후반부로 갈수록 점진 회복을 반영해 상향 강도를 초기의 60%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.6을 더해 0.31165644171779136으로 산정했다. |
| 5 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 7.9, "Period": 116, "Year": 2026}` | 0.19018404907975456 | 0.2711656441717791 | 회복 진행에 따라 대체 LNG 가동률 상향 강도를 초기의 40%로 축소했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.4를 더해 0.2711656441717791로 산정했다. |
| 6 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 7.9, "Period": 117, "Year": 2026}` | 0.19018404907975456 | 0.2306748466257668 | 6개월 적용 기간의 마지막 달로 점진 회복을 반영해 상향 강도를 초기의 20%만 유지했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.2를 더해 0.23067484662576683으로 산정했다. |
| 7 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 8.4, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 해당 월은 6개월 차질의 첫 달이며 Arzew GL2Z는 기준 가동률이 낮아 대체 LNG 공급 여지가 큰 슬롯이다. 기준 가동률 0.19018404907975456에 여유 가동률의 25%를 더해 0.3926380368098159로 산정했다. |
| 8 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 8.4, "Period": 113, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 차질 초기 구간의 대체 공급 필요가 유지되는 월로 보아 전월과 같은 상향 강도를 적용했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25를 더해 0.3926380368098159로 산정했다. |
| 9 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 8.4, "Period": 114, "Year": 2026}` | 0.19018404907975456 | 0.3521472392638037 | 점진 회복을 반영해 3개월 차의 가동률 상향 강도를 초기의 80%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.8을 더해 0.3521472392638037로 산정했다. |
| 10 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 8.4, "Period": 115, "Year": 2026}` | 0.19018404907975456 | 0.31165644171779133 | 차질 중후반부로 진입하면서 대체 LNG 필요가 낮아지는 흐름을 반영했다. 기준 가동률 0.19018404907975456에 여유 가동률의 25%를 초기 대비 60%만 반영해 0.31165644171779136으로 산정했다. |
| 11 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 8.4, "Period": 116, "Year": 2026}` | 0.19018404907975456 | 0.2711656441717791 | 회복 진행에 따라 상향 강도를 초기의 40%로 축소했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.4를 더해 0.2711656441717791로 산정했다. |
| 12 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 8.4, "Period": 117, "Year": 2026}` | 0.19018404907975456 | 0.2306748466257668 | 6개월 적용 기간의 마지막 월로, 점진 회복을 반영해 상향 강도를 초기의 20%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.2를 더해 0.23067484662576683으로 산정했다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1117,
  "model_param_proposal_id": 34,
  "proposal_completed_dtm": "2026-07-07 17:26:25.381128",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "대체 가스 공급 가능성 25%는 Norway upstream 차질 중 일부가 LNG 전환 대체 공급으로 흡수될 수 있음을 뜻하며, LiqUtilAdjustment는 이 대체 공급 경로의 액화시설 가동률 상향을 직접 반영하는 parameter이다. 6개월 기간, 급격한 발생, 점진 회복 조건을 반영해 유럽 대체 조달과 연결성이 높은 Algeria의 여유 가동률이 큰 Arzew 설비에 우선 배분하고, 가동률은 1.0 상한 내에서 초기에 높인 뒤 후반으로 갈수록 단계적으로 낮췄다.",
      "values": [
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "해당 월은 6개월 차질의 첫 달로 급격한 발생 구간에 해당하므로 대체 LNG 공급 필요가 가장 높다. 기준 가동률 0.19018404907975456에 대체 공급 가능성 25%를 여유 가동률에 반영해 0.19018404907975456 + (1 - 0.19018404907975456) × 0.25 = 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "해당 월은 차질 초기의 높은 대체 조달 필요가 유지되는 구간이다. 기준 가동률 0.19018404907975456에 여유 가동률의 25%를 추가해 최종 가동률을 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3521472392638037,
          "rationale": "점진 회복을 반영해 3개월 차부터 대체 공급 가동률 상향 강도를 초기의 80%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.8을 더해 0.3521472392638037로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.31165644171779133,
          "rationale": "6개월 차질의 중후반부로 갈수록 점진 회복을 반영해 상향 강도를 초기의 60%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.6을 더해 0.31165644171779136으로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.2711656441717791,
          "rationale": "회복 진행에 따라 대체 LNG 가동률 상향 강도를 초기의 40%로 축소했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.4를 더해 0.2711656441717791로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.2306748466257668,
          "rationale": "6개월 적용 기간의 마지막 달로 점진 회복을 반영해 상향 강도를 초기의 20%만 유지했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.2를 더해 0.23067484662576683으로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "해당 월은 6개월 차질의 첫 달이며 Arzew GL2Z는 기준 가동률이 낮아 대체 LNG 공급 여지가 큰 슬롯이다. 기준 가동률 0.19018404907975456에 여유 가동률의 25%를 더해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "차질 초기 구간의 대체 공급 필요가 유지되는 월로 보아 전월과 같은 상향 강도를 적용했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25를 더해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3521472392638037,
          "rationale": "점진 회복을 반영해 3개월 차의 가동률 상향 강도를 초기의 80%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.8을 더해 0.3521472392638037로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.31165644171779133,
          "rationale": "차질 중후반부로 진입하면서 대체 LNG 필요가 낮아지는 흐름을 반영했다. 기준 가동률 0.19018404907975456에 여유 가동률의 25%를 초기 대비 60%만 반영해 0.31165644171779136으로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.2711656441717791,
          "rationale": "회복 진행에 따라 상향 강도를 초기의 40%로 축소했다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.4를 더해 0.2711656441717791로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.2306748466257668,
          "rationale": "6개월 적용 기간의 마지막 월로, 점진 회복을 반영해 상향 강도를 초기의 20%로 낮췄다. 기준 가동률 0.19018404907975456에 (1 - 0.19018404907975456) × 0.25 × 0.2를 더해 0.23067484662576683으로 산정했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 49,
  "scenario_id": 284,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:05.433 | 5.433 | 2543 | 160 | 2703 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 02:00.645 | 120.645 | 11903 | 14251 | 26154 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:39.973 | 99.973 | 20736 | 7016 | 27752 |

### event_type_l2_id=2 터미널 Utilization 변동

#### Scenario Group

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

#### Dimension Template

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

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "타 LNG 공급국 가동률 상향으로 상쇄 : 부족 LNG 물량을 대체 가능한 공급국의 잔여 액화 가동 여력에 배분하고, 이미 고가동 설비는 배분 제외",
      "dimension_key": "alt_lng_supply_availability",
      "dimension_label": "대체 LNG 공급 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 105,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 106,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격(사고)/점진(정비)",
      "dimension_key": "onset_pattern",
      "dimension_label": "발생 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 105,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 106,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "시간축",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 105,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3개월",
          "scenario_id": 106,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "원상복귀 속도",
      "dimension_key": "recovery_pattern",
      "dimension_label": "회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "급격",
          "scenario_id": 105,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "없음 (영구 손실)",
          "scenario_id": 106,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqProdAdjustment",
      "comment": "대폭·영구 손실 시 생산량(Mt LNG) 직접 : 장기·영구 손실 또는 설비 폐쇄 수준이면 Plant/Train 생산량 자체를 하향 조정",
      "dimension_key": "utilization_change_amount",
      "dimension_label": "Utilization 변화량",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqProdAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 생산량 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "<5%",
          "scenario_id": 105,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "100%",
          "scenario_id": 106,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "Plant>Train 가동률(%) 조정 : 차질 대상 액화 Plant/Train의 이용률을 조정하고, 단기·부분 차질은 생산량보다 utilization 조정을 우선 사용",
      "dimension_key": "utilization_change_amount",
      "dimension_label": "Utilization 변화량",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "<5%",
          "scenario_id": 105,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "100%",
          "scenario_id": 106,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [105, 106]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=105 1개월 내 미세 감산 후 정상화

- 소요시간: 02:55.599 (175.599s)
- attempt: 1

##### Scenario Major Info

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

##### Validation Summary

- expected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=2|utilizationchangeamount|liqprodadjustment|supply|liqprodadjustment, sheet=LiqProdAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 6 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=6, basecaseValue_present=3 | PASS |
| Step2 slot axis value 수 | `{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 3 | Utilization 변화량이 '<5%'로 제시되어 Cameron LNG 각 Train의 월별 액화 가동률 조정 파라미터와 직접 연결됩니다. 기간은 1개월 이하이고 회복 패턴은 급격하므로, 2026년 7월에만 소폭 하향한 뒤 이후 기간은 정상화되는 구조로 제안합니다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 3 | Utilization 변화량이 '<5%'로 작고 기간도 1개월 이하이므로 생산량 직접 조정보다는 가동률 조정이 주된 해석입니다. 다만 선택된 Train·월 생산량 override 슬롯에 대해서는 급격한 정상화 조건을 반영해 2026년 7월 한 달의 보수적인 최종 월간 생산량만 제안합니다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.8791969208161199 | 2026년 7월 Cameron LNG T1의 기준 가동률 0.8971397151184897에 대해, '<5%' 미세 감산과 정상가동 유지·중립적 가격 영향에 맞춰 보수적으로 2%만 하향 적용했습니다. 최종 입력값은 0.8971397151184897 × 0.98 = 0.8791969208161199입니다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.8791969208161199 | 2026년 7월 Cameron LNG T2의 기준 가동률 0.8971397151184897에 대해, '<5%' 미세 감산과 1개월 이하의 단기 조정이라는 조건을 반영해 2% 하향했습니다. 최종 입력값은 0.8971397151184897 × 0.98 = 0.8791969208161199입니다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.8791969208161199 | 2026년 7월 Cameron LNG T3의 기준 가동률 0.8971397151184897에 대해, '<5%' 범위 내 단기 운영 조정을 보수적으로 2% 하향으로 반영했습니다. 최종 입력값은 0.8971397151184897 × 0.98 = 0.8791969208161199입니다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | null | 0.3675 | 2026년 7월 Cameron LNG T1에 대해 생산량 기준값은 제공되지 않았으므로, Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산하고 '<5%' 미세 감산을 보수적 2% 하향으로 적용했습니다. 최종 입력값은 0.375 × 0.98 = 0.3675 Mt/month입니다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | null | 0.3675 | 2026년 7월 Cameron LNG T2에 대해 생산량 기준값은 제공되지 않았으므로, Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산하고 단기 '<5%' 감산을 2% 하향으로 반영했습니다. 최종 입력값은 0.375 × 0.98 = 0.3675 Mt/month입니다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | null | 0.3675 | 2026년 7월 Cameron LNG T3에 대해 생산량 기준값은 제공되지 않았으므로, Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산하고 1개월 이하의 미세 감산을 2% 하향으로 적용했습니다. 최종 입력값은 0.375 × 0.98 = 0.3675 Mt/month입니다. |

##### Final DB Proposal Row

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
  "model_param_proposal_id": 32,
  "proposal_completed_dtm": "2026-07-07 17:24:38.182610",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "Utilization 변화량이 '<5%'로 제시되어 Cameron LNG 각 Train의 월별 액화 가동률 조정 파라미터와 직접 연결됩니다. 기간은 1개월 이하이고 회복 패턴은 급격하므로, 2026년 7월에만 소폭 하향한 뒤 이후 기간은 정상화되는 구조로 제안합니다.",
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
          "proposedValue": 0.8791969208161199,
          "rationale": "2026년 7월 Cameron LNG T1의 기준 가동률 0.8971397151184897에 대해, '<5%' 미세 감산과 정상가동 유지·중립적 가격 영향에 맞춰 보수적으로 2%만 하향 적용했습니다. 최종 입력값은 0.8971397151184897 × 0.98 = 0.8791969208161199입니다."
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
          "proposedValue": 0.8791969208161199,
          "rationale": "2026년 7월 Cameron LNG T2의 기준 가동률 0.8971397151184897에 대해, '<5%' 미세 감산과 1개월 이하의 단기 조정이라는 조건을 반영해 2% 하향했습니다. 최종 입력값은 0.8971397151184897 × 0.98 = 0.8791969208161199입니다."
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
          "proposedValue": 0.8791969208161199,
          "rationale": "2026년 7월 Cameron LNG T3의 기준 가동률 0.8971397151184897에 대해, '<5%' 범위 내 단기 운영 조정을 보수적으로 2% 하향으로 반영했습니다. 최종 입력값은 0.8971397151184897 × 0.98 = 0.8791969208161199입니다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqProdAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqProdAdjustment"
        ]
      },
      "parameterName": "LiqProdAdjustment",
      "rationale": "Utilization 변화량이 '<5%'로 작고 기간도 1개월 이하이므로 생산량 직접 조정보다는 가동률 조정이 주된 해석입니다. 다만 선택된 Train·월 생산량 override 슬롯에 대해서는 급격한 정상화 조건을 반영해 2026년 7월 한 달의 보수적인 최종 월간 생산량만 제안합니다.",
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
          "basecaseValue": null,
          "proposedValue": 0.3675,
          "rationale": "2026년 7월 Cameron LNG T1에 대해 생산량 기준값은 제공되지 않았으므로, Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산하고 '<5%' 미세 감산을 보수적 2% 하향으로 적용했습니다. 최종 입력값은 0.375 × 0.98 = 0.3675 Mt/month입니다."
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
          "basecaseValue": null,
          "proposedValue": 0.3675,
          "rationale": "2026년 7월 Cameron LNG T2에 대해 생산량 기준값은 제공되지 않았으므로, Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산하고 단기 '<5%' 감산을 2% 하향으로 반영했습니다. 최종 입력값은 0.375 × 0.98 = 0.3675 Mt/month입니다."
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
          "basecaseValue": null,
          "proposedValue": 0.3675,
          "rationale": "2026년 7월 Cameron LNG T3에 대해 생산량 기준값은 제공되지 않았으므로, Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산하고 1개월 이하의 미세 감산을 2% 하향으로 적용했습니다. 최종 입력값은 0.375 × 0.98 = 0.3675 Mt/month입니다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 18,
  "scenario_id": 105,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.272 | 4.272 | 2889 | 141 | 3030 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:00.624 | 60.624 | 12132 | 3633 | 15765 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:05.002 | 65.002 | 10687 | 2861 | 13548 |

#### scenario_id=106 3개월간 완전 증산 반영

- 소요시간: 02:04.519 (124.519s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "period": "3개월",
    "recovery_pattern": "없음 (영구 손실)",
    "utilization_change_amount": "100%"
  },
  "impact": {
    "hh": "mild_bull",
    "jkm": "bear",
    "ttf": "mild_bear"
  },
  "narrative": "기간은 3개월이며 Cameron LNG Utilization은 100% 증가로 완전 생산 재개가 시장에 반영된다.\nRamp-up은 None으로, 추가적인 단계적 회복 과정 없이 정상가동 상태가 지속되는 것으로 해석한다.\n‘영구 손실’로 보였던 정비 리스크가 해소되며, 유럽과 아시아 모두 미국 LNG 공급 안정성을 가격에 반영한다.",
  "probability_delta": 0.0,
  "probability_score": 14.0,
  "scenario_group_id": 18,
  "scenario_id": 106,
  "status": "creating",
  "title": "3개월간 완전 증산 반영"
}
```

##### Validation Summary

- expected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=2|utilizationchangeamount|liqprodadjustment|supply|liqprodadjustment, sheet=LiqProdAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 12 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=12, basecaseValue_present=9 | PASS |
| Step2 slot axis value 수 | `{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 9 | Utilization 변화량이 100%로 제시되어 Cameron LNG의 정비 후 완전 생산 재개를 Train별 가동률 입력값으로 직접 반영할 필요가 있습니다. 기간은 3개월로 제한되고 회복 패턴은 추가 ramp-up 없이 정상가동이 지속되는 구조이므로, 선택된 Cameron LNG 운영 Train의 해당 기간 가동률을 상향해 완전가동 수준으로 적용합니다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 3 | Utilization 변화량 100%는 Cameron LNG의 완전 생산 재개를 의미하므로, 절대 생산량 입력값에도 정상가동 물량을 직접 반영할 수 있습니다. 기간 dimension은 적용 범위를 3개월로 한정하고, 회복 패턴은 단계적 회복 없이 동일한 생산 수준이 유지되는 것으로 해석해 선택된 월별 Plant 생산량을 동일한 완전가동 기준으로 설정합니다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 1.0 | Cameron LNG T1의 2026년 7월 선택 슬롯에 대해 현재 기준 가동률 0.8971397151184897을 기준으로, 완전 생산 재개 및 추가 ramp-up 없음 가정을 반영해 최종 가동률을 1.0으로 설정했습니다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | 0.9091015779867364 | 1.0 | Cameron LNG T1의 2026년 8월 선택 슬롯에 대해 현재 기준 가동률 0.9091015779867364을 기준으로, 3개월 정상가동 지속 가정을 반영해 최종 가동률을 1.0으로 설정했습니다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | 0.8993102144292602 | 1.0 | Cameron LNG T1의 2026년 9월 선택 슬롯에 대해 현재 기준 가동률 0.8993102144292602을 기준으로, 3개월 적용 기간의 마지막 월도 완전가동 상태가 유지되는 것으로 보아 최종 가동률을 1.0으로 설정했습니다. |
| 4 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 1.0 | Cameron LNG T2의 2026년 7월 선택 슬롯에 대해 현재 기준 가동률 0.8971397151184897을 기준으로, 완전 생산 재개 및 추가 ramp-up 없음 가정을 반영해 최종 가동률을 1.0으로 설정했습니다. |
| 5 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | 0.9091015779867364 | 1.0 | Cameron LNG T2의 2026년 8월 선택 슬롯에 대해 현재 기준 가동률 0.9091015779867364을 기준으로, 3개월 정상가동 지속 가정을 반영해 최종 가동률을 1.0으로 설정했습니다. |
| 6 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | 0.8993102144292602 | 1.0 | Cameron LNG T2의 2026년 9월 선택 슬롯에 대해 현재 기준 가동률 0.8993102144292602을 기준으로, 3개월 적용 기간의 마지막 월도 완전가동 상태가 유지되는 것으로 보아 최종 가동률을 1.0으로 설정했습니다. |
| 7 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 1.0 | Cameron LNG T3의 2026년 7월 선택 슬롯에 대해 현재 기준 가동률 0.8971397151184897을 기준으로, 완전 생산 재개 및 추가 ramp-up 없음 가정을 반영해 최종 가동률을 1.0으로 설정했습니다. |
| 8 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | 0.9091015779867364 | 1.0 | Cameron LNG T3의 2026년 8월 선택 슬롯에 대해 현재 기준 가동률 0.9091015779867364을 기준으로, 3개월 정상가동 지속 가정을 반영해 최종 가동률을 1.0으로 설정했습니다. |
| 9 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | 0.8993102144292602 | 1.0 | Cameron LNG T3의 2026년 9월 선택 슬롯에 대해 현재 기준 가동률 0.8993102144292602을 기준으로, 3개월 적용 기간의 마지막 월도 완전가동 상태가 유지되는 것으로 보아 최종 가동률을 1.0으로 설정했습니다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "Month": 7, "Period": 112, "Year": 2026}` | null | 1.125 | 2026년 7월 Cameron LNG Plant 선택 슬롯에 대해, 4.5 MTPA Train 3기의 총 명목용량 13.5 MTPA를 완전가동 월간 생산량으로 환산하여 13.5/12 = 1.125 Mt LNG/month로 설정했습니다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "Month": 8, "Period": 113, "Year": 2026}` | null | 1.125 | 2026년 8월 Cameron LNG Plant 선택 슬롯에 대해, 추가 ramp-up 없이 정상가동이 지속되는 가정에 따라 총 명목용량 13.5 MTPA의 월간 완전가동 생산량인 1.125 Mt LNG/month를 적용했습니다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "Month": 9, "Period": 114, "Year": 2026}` | null | 1.125 | 2026년 9월 Cameron LNG Plant 선택 슬롯에 대해, 3개월 적용 기간의 마지막 월에도 완전 생산 재개 상태가 유지되는 것으로 보아 총 명목용량 13.5 MTPA 기준 월간 생산량 1.125 Mt LNG/month를 적용했습니다. |

##### Final DB Proposal Row

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
  "model_param_proposal_id": 31,
  "proposal_completed_dtm": "2026-07-07 17:23:53.726537",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "Utilization 변화량이 100%로 제시되어 Cameron LNG의 정비 후 완전 생산 재개를 Train별 가동률 입력값으로 직접 반영할 필요가 있습니다. 기간은 3개월로 제한되고 회복 패턴은 추가 ramp-up 없이 정상가동이 지속되는 구조이므로, 선택된 Cameron LNG 운영 Train의 해당 기간 가동률을 상향해 완전가동 수준으로 적용합니다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.8971397151184897,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T1의 2026년 7월 선택 슬롯에 대해 현재 기준 가동률 0.8971397151184897을 기준으로, 완전 생산 재개 및 추가 ramp-up 없음 가정을 반영해 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9091015779867364,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T1의 2026년 8월 선택 슬롯에 대해 현재 기준 가동률 0.9091015779867364을 기준으로, 3개월 정상가동 지속 가정을 반영해 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.8993102144292602,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T1의 2026년 9월 선택 슬롯에 대해 현재 기준 가동률 0.8993102144292602을 기준으로, 3개월 적용 기간의 마지막 월도 완전가동 상태가 유지되는 것으로 보아 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.8971397151184897,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T2의 2026년 7월 선택 슬롯에 대해 현재 기준 가동률 0.8971397151184897을 기준으로, 완전 생산 재개 및 추가 ramp-up 없음 가정을 반영해 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9091015779867364,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T2의 2026년 8월 선택 슬롯에 대해 현재 기준 가동률 0.9091015779867364을 기준으로, 3개월 정상가동 지속 가정을 반영해 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.8993102144292602,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T2의 2026년 9월 선택 슬롯에 대해 현재 기준 가동률 0.8993102144292602을 기준으로, 3개월 적용 기간의 마지막 월도 완전가동 상태가 유지되는 것으로 보아 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.8971397151184897,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T3의 2026년 7월 선택 슬롯에 대해 현재 기준 가동률 0.8971397151184897을 기준으로, 완전 생산 재개 및 추가 ramp-up 없음 가정을 반영해 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9091015779867364,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T3의 2026년 8월 선택 슬롯에 대해 현재 기준 가동률 0.9091015779867364을 기준으로, 3개월 정상가동 지속 가정을 반영해 최종 가동률을 1.0으로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.8993102144292602,
          "proposedValue": 1.0,
          "rationale": "Cameron LNG T3의 2026년 9월 선택 슬롯에 대해 현재 기준 가동률 0.8993102144292602을 기준으로, 3개월 적용 기간의 마지막 월도 완전가동 상태가 유지되는 것으로 보아 최종 가동률을 1.0으로 설정했습니다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqProdAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqProdAdjustment"
        ]
      },
      "parameterName": "LiqProdAdjustment",
      "rationale": "Utilization 변화량 100%는 Cameron LNG의 완전 생산 재개를 의미하므로, 절대 생산량 입력값에도 정상가동 물량을 직접 반영할 수 있습니다. 기간 dimension은 적용 범위를 3개월로 한정하고, 회복 패턴은 단계적 회복 없이 동일한 생산 수준이 유지되는 것으로 해석해 선택된 월별 Plant 생산량을 동일한 완전가동 기준으로 설정합니다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "Month": 7,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.125,
          "rationale": "2026년 7월 Cameron LNG Plant 선택 슬롯에 대해, 4.5 MTPA Train 3기의 총 명목용량 13.5 MTPA를 완전가동 월간 생산량으로 환산하여 13.5/12 = 1.125 Mt LNG/month로 설정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "Month": 8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.125,
          "rationale": "2026년 8월 Cameron LNG Plant 선택 슬롯에 대해, 추가 ramp-up 없이 정상가동이 지속되는 가정에 따라 총 명목용량 13.5 MTPA의 월간 완전가동 생산량인 1.125 Mt LNG/month를 적용했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "Month": 9,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.125,
          "rationale": "2026년 9월 Cameron LNG Plant 선택 슬롯에 대해, 3개월 적용 기간의 마지막 월에도 완전 생산 재개 상태가 유지되는 것으로 보아 총 명목용량 13.5 MTPA 기준 월간 생산량 1.125 Mt LNG/month를 적용했습니다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 18,
  "scenario_id": 106,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.291 | 3.291 | 2895 | 115 | 3010 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:39.096 | 39.096 | 12158 | 3080 | 15238 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:43.623 | 43.623 | 11214 | 3550 | 14764 |

### event_type_l2_id=4 파이프라인 Utilization 변동

#### Scenario Group

```json
{
  "description": "파이프라인 Utilization 변동 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
  "dimension_selected": [
    "period",
    "utilization_change_amount",
    "structural_change_yn",
    "onset_pattern",
    "recovery_pattern",
    "alt_supply_availability"
  ],
  "event_type": {
    "event_type_l1_id": 1,
    "event_type_l2_id": 4,
    "level_1_code": "supply",
    "level_1_label": "공급",
    "level_2_code": "pipeline_utilization_change",
    "level_2_label": "파이프라인 Utilization 변동"
  },
  "event_type_l2_id": 4,
  "mi_event_id": 1121,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 50,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 파이프라인 Utilization 변동 scenario_group",
  "title": "[model_parameter_agent_test] 파이프라인 Utilization 변동 추가 검증"
}
```

#### Dimension Template

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
    "label": "Utilization 변화 폭 (송출용량 대비)",
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
    "dim_key": "onset_pattern",
    "display_order": 4,
    "label": "발생 패턴",
    "required": false,
    "value_enums": [
      "급격",
      "점진"
    ]
  },
  {
    "dim_key": "recovery_pattern",
    "display_order": 5,
    "label": "회복 패턴",
    "required": false,
    "value_enums": [
      "급격",
      "점진",
      "없음 (영구)"
    ]
  },
  {
    "dim_key": "alt_supply_availability",
    "display_order": 6,
    "label": "대체 공급원 가능성 (타 노선·LNG 전환)",
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

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "LNG 전환(타 공급국 액화 가동률 상향) : PNG 대체가 LNG 전환으로 설명될 때 시장연결 공급국의 가용 액화설비에 대체 물량을 배분",
      "dimension_key": "alt_supply_availability",
      "dimension_label": "대체 공급원 가능성 (타 노선·LNG 전환)",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PipelineAdjustment",
      "comment": "타 노선 송출 증대 : 차질 노선과 연결 가능한 대체 파이프라인의 잔여 송출능력에 부족분을 차등 배분",
      "dimension_key": "alt_supply_availability",
      "dimension_label": "대체 공급원 가능성 (타 노선·LNG 전환)",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "PipelineAdjustment",
        "model_table": "table1",
        "semantic_axes": "PNG 송출 capa override — Pipeline·From·To·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격/점진",
      "dimension_key": "onset_pattern",
      "dimension_label": "발생 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "점진",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "급격",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "시간축",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "1년",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "원상복귀 속도",
      "dimension_key": "recovery_pattern",
      "dimension_label": "회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "급격",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "점진",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "단발=한시/구조적=영구 — 변경 범위",
      "dimension_key": "structural_change_yn",
      "dimension_label": "구조적 변동 여부",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "단발적",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "구조적",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PipelineAdjustment",
      "comment": "노선 capacity(Bcm/y) 조정 : 영향받은 파이프라인 노선의 송출 capacity를 조정하고, 기간·회복패턴에 따라 적용 월을 분배",
      "dimension_key": "utilization_change_amount",
      "dimension_label": "Utilization 변화 폭 (송출용량 대비)",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "PipelineAdjustment",
        "model_table": "table1",
        "semantic_axes": "PNG 송출 capa override — Pipeline·From·To·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "<5%",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "60%",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "계약기반 PNG 물량 변동(Nord Stream 재가동/Pipeline Disruption) : PNG 계약 물량 자체는 Trade 계열 미대상 파라미터이므로 직접 조정하지 않고, 실제 송출 가능량 변화가 있으면 PipelineAdjustment로 별도 반영",
      "dimension_key": "utilization_change_amount",
      "dimension_label": "Utilization 변화 폭 (송출용량 대비)",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "<5%",
          "scenario_id": 285,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "60%",
          "scenario_id": 286,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 4,
  "mapping_count": 8,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:01:58.224878",
  "detail_analysis": "사건 요약:\nEntsog 자료를 바탕으로 한 Reuters 계산 기준 Gazprom의 TurkStream 경유 유럽행 파이프라인 가스 공급이 5월 전년 동월 대비 증가한 것으로 보도됨. 5월 일평균 공급량은 4,740만 입방미터로 전년 동월 대비 3% 증가함. 5월 월간 총 공급량은 14억7천만 입방미터로 1년 전 14억3천만 입방미터보다 높은 수준임. 2026년 1~5월 누적 공급량은 약 77억6천만 입방미터로 집계됨. 이번 신규 연결 Record 중 2026년 6월 2일 Platts Daily Report는 직전 요약에 반영된 당일 LNG 시장 반응을 재확인하는 성격임. 2026년 3월 2일 Platts Daily Report의 중동 분쟁, 호르무즈 해협 통항 중단, QatarEnergy 생산 중단 내용은 별도 공급 차질 이슈로서 본 TurkStream 파이프라인 Utilization 변동 Event와 경계 구분 필요함.\n\n영향 경로:\nTurkStream 경유 물량 증가는 유럽 시장의 파이프라인 가스 공급 가용성을 높이는 직접적 Fundamental 요인임. LNG 터미널이나 LNG 화물의 물리적 변동은 아니지만, 유럽 수요처의 대체 LNG 조달 필요를 일부 낮출 수 있는 가스 수급 변수임. EU 저장률 40.48% 등 저장 상황과 함께 유럽 단기 조달 여건을 판단하는 배경 지표로 작용함. 반면 3월 2일 Record의 EU 가스 저장률 29.98%, 아시아·유럽 화물 경쟁, 운임 급등은 호르무즈 및 QatarEnergy 차질 관련 시장 환경으로, 본 Event의 원인 또는 직접 Fundamental 변화로 병합하지 않음.\n\n시장 반응:\nReuters 보도에는 TurkStream 공급 증가와 직접 연결된 TTF, JKM, 스팟 또는 선물 가격 수치 제시는 제한적임. 2026년 6월 2일 Platts Daily Report에서는 NWE가 전일 상승분을 반납했고 JKM은 Ichthys 파업과 아시아 폭염 영향으로 상승한 것으로 언급됨. 따라서 본 Event의 가격 방향은 유럽 파이프라인 공급 증가에 따른 TTF 프리미엄 및 유럽 LNG 현물 구매 압력의 하방 요인으로 해석됨. 2026년 3월 2일 Platts Daily Report의 JKM 하루 40.86% 급등과 NWE-TTF 50센트 프리미엄 전환은 중동 공급 차질에 따른 별도 가격 반응임.\n\nLNG 시장 관점:\n러시아 파이프라인 가스 유입 증가는 유럽 LNG 수입 경쟁을 완화할 수 있는 간접 경로임. 유럽의 대체 LNG 구매 필요가 줄어들 경우 대서양 물동량 배분과 미·아시아 차익 경쟁에도 완화 요인으로 작용할 수 있음. 다만 6월 2일 JKM 상승은 Ichthys 파업과 아시아 폭염 등 별도 LNG 수급 요인이 주도한 것으로 구분 필요함. 3월 2일 중동 분쟁 및 QatarEnergy 생산 중단 관련 Record는 LNG 시장 영향이 크지만 Event Type상 파이프라인 Utilization 변동 범위를 벗어나는 하위 사건으로 취급 필요함.",
  "event_title_ko": "TurkStream 유럽행 5월 공급 증가",
  "event_type_l2_id": 4,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-02T00:00:00",
  "mi_event_id": "1121",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[러시아 파이프라인 가스] 5월 TurkStream 공급 3% 증가 → 유럽 LNG 대체수요 완화",
  "source_mi_record_ids": [
    2286,
    2327,
    2415
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [285, 286]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=285 [model_parameter_agent_test] 단기 송출 증가와 대체 공급 충분

- 소요시간: 03:34.631 (214.631s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_supply_availability": "100%",
    "onset_pattern": "점진",
    "period": "1개월 이하",
    "recovery_pattern": "급격",
    "structural_change_yn": "단발적",
    "utilization_change_amount": "<5%"
  },
  "impact": {
    "hh": "중립",
    "jkm": "중립",
    "ttf": "중립"
  },
  "narrative": "TurkStream 유럽행 송출이 단기 소폭 증가하고 대체 공급도 충분해 영향이 작다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 50,
  "scenario_id": 285,
  "status": "created",
  "title": "[model_parameter_agent_test] 단기 송출 증가와 대체 공급 충분"
}
```

##### Validation Summary

- expected_parameters: `["PipelineAdjustment", "LiqUtilAdjustment"]`
- selected_parameters: `["PipelineAdjustment", "LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21716 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=137 | PASS |
| Step2 selected slot | 20 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=20, basecaseValue_present=19 | PASS |
| Step2 slot axis value 수 | `{"4|altsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}, "parameter|4|supply|pipelineadjustment|pipelineadjustment": {"Month": 12, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PipelineAdjustment | `{"modelFile": "Supply", "modelSheet": "PipelineAdjustment", "tableName": "table1"}` | `["Year", "Month", "Pipeline name"]` | `["User adjusted capacity (Bcm/y)"]` | 1 | Utilization 변화 폭이 <5%로 제시되어 TurkStream 노선의 송출 capacity override에 직접 연결되며, 대체 공급원 가능성 100%는 다른 노선이나 LNG 전환 압력이 충분히 흡수되는 낮은 강도의 조정으로 해석된다. 단발적이고 1개월 이하의 점진적 증가 후 급격히 회복되는 케이스이므로, 2026년 5월 TurkStream에 한정해 보수적인 단기 상향 절대값을 적용한다. |
| 2 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 19 | 대체 공급원 가능성 100%는 LNG 전환 여력이 충분하다는 조건으로 LiqUtilAdjustment와 연결되지만, 이번 시나리오는 TurkStream 송출 증가로 유럽 LNG 대체수요가 완화되는 방향이다. 따라서 선택된 2026년 5월 대체 공급 후보 액화설비에는 추가 가동률 상향을 적용하지 않고, 단기·단발 이벤트에 맞춰 기준 가동률을 유지하는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PipelineAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month": 5, "Pipeline name": "TurkStream", "Year": 2026}` | null | 17.301 | 2026년 5월 TurkStream 선택 좌표에 대해, 이벤트에서 제시된 5월 일평균 유럽행 송출량 4,740만 입방미터/일을 Bcm/y 형식으로 환산했다. 산정은 47.4 mcm/d × 365 ÷ 1000으로 수행했으며, 단기 소폭 증가 시나리오이므로 추가 확대 배율 없이 최종 입력값 17.301 Bcm/y를 적용한다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 7.9, "Period": 110, "Year": 2026}` | 0.19018404907975456 | 0.19018404907975456 | 선택된 2026년 5월 Arzew GL1Z 좌표는 대체 공급 후보이나, TurkStream 증가로 LNG 추가 조달 필요가 커지지 않는 케이스다. 해당 설비의 5월 기준 가동률을 그대로 유지해 최종 입력값을 0.19018404907975456으로 둔다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 8.4, "Period": 110, "Year": 2026}` | 0.19018404907975456 | 0.19018404907975456 | 선택된 2026년 5월 Arzew GL2Z 좌표는 대체 공급 후보이나, 단기 소폭 PNG 송출 증가로 LNG 가동률 상향 필요가 확인되지 않는다. 해당 설비의 5월 기준 가동률을 그대로 유지해 최종 입력값을 0.19018404907975456으로 둔다. |
| 3 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.7, "Period": 110, "Year": 2026}` | 1.0000000000000002 | 1.0000000000000002 | 선택된 2026년 5월 Arzew GL3Z 좌표는 이미 기준 가동률이 사실상 전량 가동 수준이므로, 대체 공급 충분 조건을 추가 상향으로 변환하지 않는다. 해당 설비의 5월 기준 가동률을 유지해 최종 입력값을 1.0000000000000002로 둔다. |
| 4 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.5, "Period": 110, "Year": 2026}` | 0.7999999999999999 | 0.7999999999999999 | 선택된 2026년 5월 Skikda GL1K 좌표는 LNG 대체 공급 후보이나, 이벤트 방향이 LNG 수요 완화에 가까워 추가 가동률 증가는 적용하지 않는다. 해당 설비의 5월 기준 가동률을 유지해 최종 입력값을 0.7999999999999999로 둔다. |
| 5 | `{"Country": "Egypt", "LNG Plant": "Damietta LNG", "LNG Plant Train": "Damietta LNG T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 3, "Period": 110, "Year": 2026}` | 0 | 0 | 선택된 2026년 5월 Damietta LNG 좌표는 기준 가동률이 0이며, 이번 시나리오에서 LNG 전환 물량을 실제로 증대시킬 필요가 명확하지 않다. 따라서 기준값을 유지해 최종 입력값을 0으로 둔다. |
| 6 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 3.6, "Period": 110, "Year": 2026}` | 0 | 0 | 선택된 2026년 5월 Egyptian LNG (Idku) T1 좌표는 기준 가동률이 0이며, TurkStream 송출 증가 이벤트로 LNG 추가 공급을 유발하는 근거가 제한적이다. 따라서 기준값을 유지해 최종 입력값을 0으로 둔다. |
| 7 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T2", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 3.6, "Period": 110, "Year": 2026}` | 0 | 0 | 선택된 2026년 5월 Egyptian LNG (Idku) T2 좌표는 기준 가동률이 0이며, 단기 PNG 송출 증가로 인해 LNG 대체 공급 확대가 필요하다고 보기 어렵다. 따라서 기준값을 유지해 최종 입력값을 0으로 둔다. |
| 8 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 3.3, "Period": 110, "Year": 2026}` | 0.7250988792029888 | 0.7250988792029888 | 선택된 2026년 5월 NLNG T1 좌표는 대체 공급 후보이나, 시나리오상 LNG 수급 충격이 중립이고 추가 상향 배분 근거가 약하다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7250988792029888로 둔다. |
| 9 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T2", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 3.3, "Period": 110, "Year": 2026}` | 0.7250988792029888 | 0.7250988792029888 | 선택된 2026년 5월 NLNG T2 좌표는 대체 공급 후보이나, TurkStream 증가가 LNG 전환 수요를 늘리는 방향이 아니므로 별도 조정을 적용하지 않는다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7250988792029888로 둔다. |
| 10 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T3", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 3.3, "Period": 110, "Year": 2026}` | 0.7116123308937679 | 0.7116123308937679 | 선택된 2026년 5월 NLNG T3 좌표는 대체 공급 후보이나, 단기 소폭 PNG 송출 증가 시나리오에서는 LNG 액화 가동률 확대가 필요하지 않다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7116123308937679로 둔다. |
| 11 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T4", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.1, "Period": 110, "Year": 2026}` | 0.7029382716049384 | 0.7029382716049384 | 선택된 2026년 5월 NLNG T4 좌표는 대체 공급 후보이나, 유럽 LNG 대체수요 완화 방향을 고려해 추가 가동률 상향을 배제한다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7029382716049384로 둔다. |
| 12 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T5", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.1, "Period": 110, "Year": 2026}` | 0.7029382716049384 | 0.7029382716049384 | 선택된 2026년 5월 NLNG T5 좌표는 대체 공급 후보이나, 가격 영향이 중립이고 LNG 공급 확대 필요가 명확하지 않다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7029382716049384로 둔다. |
| 13 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.1, "Period": 110, "Year": 2026}` | 0.7029382716049384 | 0.7029382716049384 | 선택된 2026년 5월 NLNG T6 좌표는 대체 공급 후보이나, TurkStream 공급 증가가 LNG 전환 수요 확대가 아닌 완화 요인으로 작용한다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7029382716049384로 둔다. |
| 14 | `{"Country": "Norway", "LNG Plant": "Snohvit LNG", "LNG Plant Train": "Snohvit LNG T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.3, "Period": 110, "Year": 2026}` | 1.0232558139534886 | 1.0232558139534886 | 선택된 2026년 5월 Snohvit LNG 좌표는 유럽 인접 대체 공급 후보이나, 이번 이벤트에서는 LNG 추가 공급을 유도할 정도의 수요 증가가 없다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 1.0232558139534886으로 둔다. |
| 15 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | 0.9282 | 0.9282 | 선택된 2026년 5월 Calcasieu Pass LNG T1 좌표는 대서양 LNG 대체 공급 후보이나, 단기 PNG 송출 증가로 추가 액화 가동률 상향은 필요하지 않다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다. |
| 16 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T10", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | 0.9282 | 0.9282 | 선택된 2026년 5월 Calcasieu Pass LNG T10 좌표는 대체 공급 후보이나, 시나리오상 LNG 수요 압력은 중립으로 유지된다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다. |
| 17 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T11", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | 0.9282 | 0.9282 | 선택된 2026년 5월 Calcasieu Pass LNG T11 좌표는 대체 공급 후보이나, TurkStream 공급 증가가 유럽 LNG 구매 압력을 낮추는 방향이라 추가 조정이 없다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다. |
| 18 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T12", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | 0.9282 | 0.9282 | 선택된 2026년 5월 Calcasieu Pass LNG T12 좌표는 대체 공급 후보이나, 대체 공급 충분 조건을 실제 증산으로 전환할 필요가 없는 낮은 충격 시나리오다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다. |
| 19 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T13", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | 0.9282 | 0.9282 | 선택된 2026년 5월 Calcasieu Pass LNG T13 좌표는 대체 공급 후보이나, 단기·단발 TurkStream 증가 이벤트에서는 LNG 액화 가동률을 높일 근거가 없다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1121,
  "model_param_proposal_id": 35,
  "proposal_completed_dtm": "2026-07-07 17:27:28.362477",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "PipelineAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Pipeline name"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "User adjusted capacity (Bcm/y)"
        ]
      },
      "parameterName": "PipelineAdjustment",
      "rationale": "Utilization 변화 폭이 <5%로 제시되어 TurkStream 노선의 송출 capacity override에 직접 연결되며, 대체 공급원 가능성 100%는 다른 노선이나 LNG 전환 압력이 충분히 흡수되는 낮은 강도의 조정으로 해석된다. 단발적이고 1개월 이하의 점진적 증가 후 급격히 회복되는 케이스이므로, 2026년 5월 TurkStream에 한정해 보수적인 단기 상향 절대값을 적용한다.",
      "values": [
        {
          "Month": 5,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 17.301,
          "rationale": "2026년 5월 TurkStream 선택 좌표에 대해, 이벤트에서 제시된 5월 일평균 유럽행 송출량 4,740만 입방미터/일을 Bcm/y 형식으로 환산했다. 산정은 47.4 mcm/d × 365 ÷ 1000으로 수행했으며, 단기 소폭 증가 시나리오이므로 추가 확대 배율 없이 최종 입력값 17.301 Bcm/y를 적용한다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "대체 공급원 가능성 100%는 LNG 전환 여력이 충분하다는 조건으로 LiqUtilAdjustment와 연결되지만, 이번 시나리오는 TurkStream 송출 증가로 유럽 LNG 대체수요가 완화되는 방향이다. 따라서 선택된 2026년 5월 대체 공급 후보 액화설비에는 추가 가동률 상향을 적용하지 않고, 단기·단발 이벤트에 맞춰 기준 가동률을 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.19018404907975456,
          "rationale": "선택된 2026년 5월 Arzew GL1Z 좌표는 대체 공급 후보이나, TurkStream 증가로 LNG 추가 조달 필요가 커지지 않는 케이스다. 해당 설비의 5월 기준 가동률을 그대로 유지해 최종 입력값을 0.19018404907975456으로 둔다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.19018404907975456,
          "rationale": "선택된 2026년 5월 Arzew GL2Z 좌표는 대체 공급 후보이나, 단기 소폭 PNG 송출 증가로 LNG 가동률 상향 필요가 확인되지 않는다. 해당 설비의 5월 기준 가동률을 그대로 유지해 최종 입력값을 0.19018404907975456으로 둔다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL3Z (Gassi Touil)",
          "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 1.0000000000000002,
          "proposedValue": 1.0000000000000002,
          "rationale": "선택된 2026년 5월 Arzew GL3Z 좌표는 이미 기준 가동률이 사실상 전량 가동 수준이므로, 대체 공급 충분 조건을 추가 상향으로 변환하지 않는다. 해당 설비의 5월 기준 가동률을 유지해 최종 입력값을 1.0000000000000002로 둔다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.7999999999999999,
          "proposedValue": 0.7999999999999999,
          "rationale": "선택된 2026년 5월 Skikda GL1K 좌표는 LNG 대체 공급 후보이나, 이벤트 방향이 LNG 수요 완화에 가까워 추가 가동률 증가는 적용하지 않는다. 해당 설비의 5월 기준 가동률을 유지해 최종 입력값을 0.7999999999999999로 둔다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Damietta LNG",
          "LNG Plant Train": "Damietta LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "선택된 2026년 5월 Damietta LNG 좌표는 기준 가동률이 0이며, 이번 시나리오에서 LNG 전환 물량을 실제로 증대시킬 필요가 명확하지 않다. 따라서 기준값을 유지해 최종 입력값을 0으로 둔다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "선택된 2026년 5월 Egyptian LNG (Idku) T1 좌표는 기준 가동률이 0이며, TurkStream 송출 증가 이벤트로 LNG 추가 공급을 유발하는 근거가 제한적이다. 따라서 기준값을 유지해 최종 입력값을 0으로 둔다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T2",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "선택된 2026년 5월 Egyptian LNG (Idku) T2 좌표는 기준 가동률이 0이며, 단기 PNG 송출 증가로 인해 LNG 대체 공급 확대가 필요하다고 보기 어렵다. 따라서 기준값을 유지해 최종 입력값을 0으로 둔다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.7250988792029888,
          "proposedValue": 0.7250988792029888,
          "rationale": "선택된 2026년 5월 NLNG T1 좌표는 대체 공급 후보이나, 시나리오상 LNG 수급 충격이 중립이고 추가 상향 배분 근거가 약하다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7250988792029888로 둔다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T2",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.7250988792029888,
          "proposedValue": 0.7250988792029888,
          "rationale": "선택된 2026년 5월 NLNG T2 좌표는 대체 공급 후보이나, TurkStream 증가가 LNG 전환 수요를 늘리는 방향이 아니므로 별도 조정을 적용하지 않는다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7250988792029888로 둔다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T3",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.7116123308937679,
          "proposedValue": 0.7116123308937679,
          "rationale": "선택된 2026년 5월 NLNG T3 좌표는 대체 공급 후보이나, 단기 소폭 PNG 송출 증가 시나리오에서는 LNG 액화 가동률 확대가 필요하지 않다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7116123308937679로 둔다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T4",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.7029382716049384,
          "proposedValue": 0.7029382716049384,
          "rationale": "선택된 2026년 5월 NLNG T4 좌표는 대체 공급 후보이나, 유럽 LNG 대체수요 완화 방향을 고려해 추가 가동률 상향을 배제한다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7029382716049384로 둔다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T5",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.7029382716049384,
          "proposedValue": 0.7029382716049384,
          "rationale": "선택된 2026년 5월 NLNG T5 좌표는 대체 공급 후보이나, 가격 영향이 중립이고 LNG 공급 확대 필요가 명확하지 않다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7029382716049384로 둔다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.7029382716049384,
          "proposedValue": 0.7029382716049384,
          "rationale": "선택된 2026년 5월 NLNG T6 좌표는 대체 공급 후보이나, TurkStream 공급 증가가 LNG 전환 수요 확대가 아닌 완화 요인으로 작용한다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.7029382716049384로 둔다."
        },
        {
          "Country": "Norway",
          "LNG Plant": "Snohvit LNG",
          "LNG Plant Train": "Snohvit LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 4.3,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 1.0232558139534886,
          "proposedValue": 1.0232558139534886,
          "rationale": "선택된 2026년 5월 Snohvit LNG 좌표는 유럽 인접 대체 공급 후보이나, 이번 이벤트에서는 LNG 추가 공급을 유도할 정도의 수요 증가가 없다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 1.0232558139534886으로 둔다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.9282,
          "proposedValue": 0.9282,
          "rationale": "선택된 2026년 5월 Calcasieu Pass LNG T1 좌표는 대서양 LNG 대체 공급 후보이나, 단기 PNG 송출 증가로 추가 액화 가동률 상향은 필요하지 않다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T10",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.9282,
          "proposedValue": 0.9282,
          "rationale": "선택된 2026년 5월 Calcasieu Pass LNG T10 좌표는 대체 공급 후보이나, 시나리오상 LNG 수요 압력은 중립으로 유지된다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T11",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.9282,
          "proposedValue": 0.9282,
          "rationale": "선택된 2026년 5월 Calcasieu Pass LNG T11 좌표는 대체 공급 후보이나, TurkStream 공급 증가가 유럽 LNG 구매 압력을 낮추는 방향이라 추가 조정이 없다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T12",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.9282,
          "proposedValue": 0.9282,
          "rationale": "선택된 2026년 5월 Calcasieu Pass LNG T12 좌표는 대체 공급 후보이나, 대체 공급 충분 조건을 실제 증산으로 전환할 필요가 없는 낮은 충격 시나리오다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T13",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": 0.9282,
          "proposedValue": 0.9282,
          "rationale": "선택된 2026년 5월 Calcasieu Pass LNG T13 좌표는 대체 공급 후보이나, 단기·단발 TurkStream 증가 이벤트에서는 LNG 액화 가동률을 높일 근거가 없다. 해당 train의 5월 기준 가동률을 유지해 최종 입력값을 0.9282로 둔다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 50,
  "scenario_id": 285,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.942 | 4.942 | 2780 | 179 | 2959 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:00.349 | 60.349 | 12426 | 4958 | 17384 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 02:08.947 | 128.947 | 13237 | 6221 | 19458 |

#### scenario_id=286 [model_parameter_agent_test] 장기 송출 차질과 대체 공급 부족

- 소요시간: 05:47.232 (347.232s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_supply_availability": "25%",
    "onset_pattern": "급격",
    "period": "1년",
    "recovery_pattern": "점진",
    "structural_change_yn": "구조적",
    "utilization_change_amount": "60%"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "파이프라인 송출 차질이 구조적으로 커지고 대체 공급이 부족해 PNG 및 pipeline 조정이 필요하다.",
  "probability_delta": 4.0,
  "probability_score": 40.0,
  "scenario_group_id": 50,
  "scenario_id": 286,
  "status": "created",
  "title": "[model_parameter_agent_test] 장기 송출 차질과 대체 공급 부족"
}
```

##### Validation Summary

- expected_parameters: `["PipelineAdjustment", "LiqUtilAdjustment"]`
- selected_parameters: `["PipelineAdjustment", "LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21716 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=137 | PASS |
| Step2 selected slot | 96 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=48, basecaseValue_present=36 | PASS |
| Step2 slot axis value 수 | `{"4|altsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}, "parameter|4|supply|pipelineadjustment|pipelineadjustment": {"Month": 12, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PipelineAdjustment | `{"modelFile": "Supply", "modelSheet": "PipelineAdjustment", "tableName": "table1"}` | `["Year", "Month", "Pipeline name"]` | `["User adjusted capacity (Bcm/y)"]` | 12 | Utilization 변화 폭 60%는 영향 노선의 송출 capacity를 직접 조정해야 하는 차질 규모로 연결되고, 대체 공급원 가능성 25%는 차질 일부만 완화되는 조건으로 반영됩니다. 기간 1년, 급격한 발생, 점진적 회복, 구조적 성격을 고려해 TurkStream에 대해 초기에는 큰 하향 조정을 적용하고 이후 12개월 동안 부분적으로만 회복되는 절대 송출능력 값을 제안합니다. |
| 2 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 36 | 대체 공급원 가능성 25%는 PNG 차질 중 일부만 LNG 전환으로 보완 가능한 조건이며, LiqUtilAdjustment는 이 LNG 전환 물량을 가용 액화설비의 월별 가동률 상향으로 반영하는 parameter입니다. 1년 기간과 급격한 발생을 고려해 즉시 적용하되, 이미 높은 가동률을 보이는 설비는 상향 여력을 제한하고 여유가 큰 설비에 더 보수적으로 배분했습니다. |

##### Proposed Parameter Values

###### Proposed Values - PipelineAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month": 7, "Pipeline name": "TurkStream", "Year": 2026}` | null | 9.52 | TurkStream의 직접 영향이 시작되는 첫 월로 선택했습니다. 이벤트에 제시된 일평균 4,740만 입방미터를 연율화한 약 17.30 Bcm/y를 기준 용량으로 보고, 60% 차질 중 대체 가능 25%를 제외한 순차질 45%를 반영해 55% 수준인 9.52 Bcm/y로 산정했습니다. |
| 2 | `{"Month": 8, "Pipeline name": "TurkStream", "Year": 2026}` | null | 9.87 | 1년 영향 구간의 두 번째 월로, 급격한 차질 이후 점진 회복을 반영했습니다. 초기 55% 수준에서 월별로 완만히 회복되는 경로를 적용해 9.87 Bcm/y로 산정했습니다. |
| 3 | `{"Month": 9, "Pipeline name": "TurkStream", "Year": 2026}` | null | 10.22 | 차질 지속 기간 내 TurkStream 월별 override 값으로 선택했습니다. 구조적 차질이 이어지지만 점진 회복이 진행되는 것으로 보아 기준 용량 대비 약 59.1% 수준인 10.22 Bcm/y를 적용했습니다. |
| 4 | `{"Month": 10, "Pipeline name": "TurkStream", "Year": 2026}` | null | 10.58 | 1년 차질 구간 중 회복 경로의 네 번째 월입니다. 순차질이 월별로 완만히 축소되는 전제를 적용해 10.58 Bcm/y로 산정했습니다. |
| 5 | `{"Month": 11, "Pipeline name": "TurkStream", "Year": 2026}` | null | 10.93 | TurkStream의 구조적 송출 차질이 계속되나 일부 회복이 누적되는 월로 선택했습니다. 기준 용량 대비 약 63.2% 수준을 적용해 10.93 Bcm/y로 제안했습니다. |
| 6 | `{"Month": 12, "Pipeline name": "TurkStream", "Year": 2026}` | null | 11.28 | 차질 발생 후 6개월차에 해당하는 월로, 대체 공급 부족으로 정상화는 제한적이라고 보았습니다. 점진 회복 경로상 11.28 Bcm/y를 적용했습니다. |
| 7 | `{"Month": 1, "Pipeline name": "TurkStream", "Year": 2027}` | null | 11.64 | 1년 영향 구간이 다음 해로 이어지는 첫 월입니다. 구조적 차질을 유지하되 회복 누적분을 반영해 11.64 Bcm/y로 산정했습니다. |
| 8 | `{"Month": 2, "Pipeline name": "TurkStream", "Year": 2027}` | null | 11.99 | TurkStream 차질이 지속되는 월로 선택했습니다. 대체 공급 부족 조건을 유지하면서 점진 회복 경로를 적용해 11.99 Bcm/y를 제안했습니다. |
| 9 | `{"Month": 3, "Pipeline name": "TurkStream", "Year": 2027}` | null | 12.35 | 회복 후반부에 접어드는 월이지만 구조적 차질로 완전 정상화는 배제했습니다. 기준 용량 대비 약 71.4% 수준인 12.35 Bcm/y로 산정했습니다. |
| 10 | `{"Month": 4, "Pipeline name": "TurkStream", "Year": 2027}` | null | 12.7 | 1년 영향 구간 내 점진 회복이 더 진행된 월입니다. 순차질의 일부만 축소되는 보수적 회복 경로를 반영해 12.70 Bcm/y를 적용했습니다. |
| 11 | `{"Month": 5, "Pipeline name": "TurkStream", "Year": 2027}` | null | 13.05 | 차질 종료 전월로, 회복이 상당히 진행되지만 대체 공급 부족과 구조적 변동을 고려해 정상 수준보다 낮게 유지했습니다. 제안값은 13.05 Bcm/y입니다. |
| 12 | `{"Month": 6, "Pipeline name": "TurkStream", "Year": 2027}` | null | 13.41 | 1년 영향 구간의 마지막 월로 선택했습니다. 점진 회복을 반영하되 구조적 차질이 남아 있는 것으로 보아 기준 용량의 약 77.5% 수준인 13.41 Bcm/y를 적용했습니다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 8.4, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.29018404907975454 | Arzew GL2Z는 기준 가동률 0.19018404907975456으로 상향 여력이 큰 설비입니다. 대체 LNG 보완분을 우선 배분해 0.10p 상향한 최종 가동률 0.29018404907975456을 적용했습니다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 8.4, "Period": 113, "Year": 2026}` | 0.19018404907975456 | 0.29018404907975454 | 동일 설비의 1년 대체 공급 적용 구간에 해당합니다. 기준 가동률 0.19018404907975456에 가용 여력 중심 배분을 반영해 0.29018404907975456으로 제안했습니다. |
| 3 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 8.4, "Period": 114, "Year": 2026}` | 0.19018404907975456 | 0.29018404907975454 | 기준값이 낮아 대체 LNG 공급 여력이 있는 월로 판단했습니다. 기준 0.19018404907975456에서 0.10p 상향한 0.29018404907975456을 적용했습니다. |
| 4 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 8.4, "Period": 115, "Year": 2026}` | 0.19018404907975456 | 0.29018404907975454 | 대체 공급 부족 조건에서 상향 여력이 큰 설비로 선택했습니다. 기준 0.19018404907975456에 보수적 상향폭을 더해 0.29018404907975456으로 산정했습니다. |
| 5 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 8.4, "Period": 116, "Year": 2026}` | 0.19018404907975456 | 0.29018404907975454 | 1년 적용 기간 중 동일한 대체 LNG 배분 원칙을 유지했습니다. 기준 가동률 0.19018404907975456에서 0.10p 상향해 0.29018404907975456으로 제안했습니다. |
| 6 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 8.4, "Period": 117, "Year": 2026}` | 0.19018404907975456 | 0.29018404907975454 | 차질 지속 구간의 월별 대체 LNG 공급원으로 선택했습니다. 낮은 기준 가동률 0.19018404907975456을 0.29018404907975456으로 상향했습니다. |
| 7 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 8.4, "Period": 118, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | 다음 해 적용 구간에서도 Arzew GL2Z의 기준 가동률이 0.18404907975460122로 낮아 상향 여력이 큽니다. 동일한 보수적 상향폭을 적용해 0.2840490797546012로 산정했습니다. |
| 8 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 8.4, "Period": 119, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | 1년 대체 공급 구간에 포함되는 월입니다. 기준 0.18404907975460122에 0.10p를 더해 최종 가동률 0.2840490797546012를 적용했습니다. |
| 9 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 8.4, "Period": 120, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | 상향 여력이 큰 액화설비로 계속 활용하는 월입니다. 기준값 0.18404907975460122에서 보수적으로 0.10p 상향한 0.2840490797546012를 제안했습니다. |
| 10 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 8.4, "Period": 121, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | 대체 LNG 보완이 필요한 기간 내 월별 적용값입니다. 기준 가동률 0.18404907975460122에 상향 여력을 반영해 0.2840490797546012로 산정했습니다. |
| 11 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 8.4, "Period": 122, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | 1년 영향 구간의 후반부에도 대체 공급 부족이 남아 있어 가동률 상향을 유지했습니다. 기준 0.18404907975460122에서 0.2840490797546012로 제안했습니다. |
| 12 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 8.4, "Period": 123, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | 1년 적용 기간의 마지막 월입니다. 기준 가동률 0.18404907975460122에 대체 LNG 배분을 반영해 0.2840490797546012를 적용했습니다. |
| 13 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.1, "Period": 112, "Year": 2026}` | 0.7193333333333335 | 0.7793333333333335 | NLNG T6는 기준 가동률 0.7193333333333335로 추가 상향 여력이 있습니다. 대체 LNG 전환 물량의 일부를 배분해 0.06p 상향한 0.7793333333333335로 산정했습니다. |
| 14 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.1, "Period": 113, "Year": 2026}` | 0.713456790123457 | 0.773456790123457 | 기준 가동률 0.713456790123457에 대해 대체 LNG 공급 보완분을 반영했습니다. 설비 여력을 감안해 0.06p 상향한 0.773456790123457을 적용했습니다. |
| 15 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.1, "Period": 114, "Year": 2026}` | 0.7732345679012347 | 0.8332345679012347 | NLNG T6의 해당 월 기준 가동률은 0.7732345679012347입니다. 25% 수준의 제한적 LNG 대체를 고려해 0.06p만 상향한 0.8332345679012347로 제안했습니다. |
| 16 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.1, "Period": 115, "Year": 2026}` | 0.7120493827160495 | 0.7720493827160495 | 기준 0.7120493827160495로 상향 여력이 있는 월입니다. 대체 LNG 보완분을 반영해 최종 가동률 0.7720493827160495로 산정했습니다. |
| 17 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.1, "Period": 116, "Year": 2026}` | 0.7283209876543211 | 0.7883209876543211 | 차질 기간 내 LNG 대체 공급 후보 월로 선택했습니다. 기준 0.7283209876543211에 0.06p 상향을 적용해 0.7883209876543211로 제안했습니다. |
| 18 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.1, "Period": 117, "Year": 2026}` | 0.7569876543209877 | 0.8169876543209877 | 기준 가동률 0.7569876543209877에서 추가 생산 여력이 남아 있다고 보았습니다. 제한적 대체 공급 조건을 반영해 0.8169876543209877로 산정했습니다. |
| 19 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 4.1, "Period": 118, "Year": 2027}` | 0.79320987654321 | 0.85320987654321 | 다음 해 1월 기준 가동률 0.79320987654321에 대해 동일한 대체 LNG 배분 원칙을 적용했습니다. 0.06p 상향해 0.85320987654321로 제안했습니다. |
| 20 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 4.1, "Period": 119, "Year": 2027}` | 0.7381234567901235 | 0.7981234567901235 | 기준값 0.7381234567901235에 제한적 LNG 대체 수요를 반영했습니다. 상향 여력을 고려해 0.7981234567901235로 산정했습니다. |
| 21 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 4.1, "Period": 120, "Year": 2027}` | 0.7349629629629632 | 0.7949629629629632 | 대체 공급 적용 기간 내 NLNG T6의 기준 가동률은 0.7349629629629632입니다. 0.06p 상향한 0.7949629629629632를 최종 입력값으로 제안했습니다. |
| 22 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 4.1, "Period": 121, "Year": 2027}` | 0.7433086419753088 | 0.8033086419753088 | 기준 가동률 0.7433086419753088에 대체 LNG 배분을 반영했습니다. 설비 가동률 상한에 여유가 있어 0.8033086419753088로 산정했습니다. |
| 23 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.1, "Period": 122, "Year": 2027}` | 0.7029382716049384 | 0.7629382716049384 | 기준 0.7029382716049384로 상향 여력이 충분한 월입니다. 제한적인 LNG 대체 가능성을 반영해 0.7629382716049384로 제안했습니다. |
| 24 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 4.1, "Period": 123, "Year": 2027}` | 0.7068148148148149 | 0.7668148148148148 | 1년 적용 기간의 마지막 월로, 기준 가동률 0.7068148148148149에 대체 LNG 공급분을 일부 배분했습니다. 최종 가동률은 0.7668148148148148입니다. |
| 25 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 10, "Period": 112, "Year": 2026}` | 0.978 | 0.998 | Sabine Pass T1-T2는 유럽 대체 LNG 공급에 연결성이 높은 설비이나 기준 가동률이 0.978로 이미 높습니다. 잔여 여력을 감안해 0.02p만 상향한 0.998로 제안했습니다. |
| 26 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 10, "Period": 113, "Year": 2026}` | 0.978 | 0.998 | 해당 월 기준 가동률 0.978에 대해 높은 기존 가동률을 고려해 제한적으로 상향했습니다. 최종 입력값은 0.998입니다. |
| 27 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 10, "Period": 114, "Year": 2026}` | 0.978 | 0.998 | 대체 LNG 전환 가능성이 있으나 기준 가동률이 높은 월입니다. 상한 접근을 고려해 0.978에서 0.998로 소폭 상향했습니다. |
| 28 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 10, "Period": 115, "Year": 2026}` | 0.978 | 0.998 | 기준값 0.978에 대체 LNG 보완분을 소폭 배분했습니다. 높은 기존 가동률을 감안해 0.998을 최종값으로 적용했습니다. |
| 29 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 10, "Period": 116, "Year": 2026}` | 0.978 | 0.998 | Sabine Pass T1-T2의 해당 월 기준값은 0.978입니다. 잔여 가동 여력을 거의 소진하는 수준으로 0.998을 제안했습니다. |
| 30 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 10, "Period": 117, "Year": 2026}` | 0.978 | 0.998 | 1년 차질 구간 내 미국 LNG의 보완 역할을 반영했습니다. 기준 0.978에서 0.998로 제한적 상향을 적용했습니다. |
| 31 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 10, "Period": 118, "Year": 2027}` | 0.9532752352743732 | 0.9732752352743732 | 다음 해 1월 기준 가동률 0.9532752352743733에 대해 미국 LNG의 대체 공급 역할을 반영했습니다. 0.02p 상향해 0.9732752352743733으로 산정했습니다. |
| 32 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 10, "Period": 119, "Year": 2027}` | 0.9586746813514612 | 0.9786746813514612 | 기준 가동률 0.9586746813514613에 제한적 대체 LNG 배분을 반영했습니다. 최종 가동률은 0.9786746813514613입니다. |
| 33 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 10, "Period": 120, "Year": 2027}` | 0.965192084044823 | 0.985192084044823 | 해당 월 기준값 0.965192084044823은 소폭 상향 여력이 있습니다. 상한에 근접하지 않도록 0.02p 상향한 0.985192084044823을 적용했습니다. |
| 34 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 10, "Period": 121, "Year": 2027}` | 0.9663020188579584 | 0.9863020188579584 | 기준 가동률 0.9663020188579585에 대체 LNG 공급 보완분을 배분했습니다. 높은 기존 가동률을 고려해 0.9863020188579585로 제안했습니다. |
| 35 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 10, "Period": 122, "Year": 2027}` | 0.9728194215513204 | 0.9928194215513204 | 기준값 0.9728194215513204에 대해 잔여 여력을 활용하되 1.0에 근접한 수준으로 제한했습니다. 최종값은 0.9928194215513204입니다. |
| 36 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 10, "Period": 123, "Year": 2027}` | 0.9789641720392572 | 0.9989641720392572 | 1년 적용 구간의 마지막 월로, 기준 가동률 0.9789641720392571에 소폭 상향을 적용했습니다. 상한에 매우 근접한 0.9989641720392571을 최종값으로 제안했습니다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1121,
  "model_param_proposal_id": 39,
  "proposal_completed_dtm": "2026-07-07 17:30:25.408070",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "PipelineAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Pipeline name"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "User adjusted capacity (Bcm/y)"
        ]
      },
      "parameterName": "PipelineAdjustment",
      "rationale": "Utilization 변화 폭 60%는 영향 노선의 송출 capacity를 직접 조정해야 하는 차질 규모로 연결되고, 대체 공급원 가능성 25%는 차질 일부만 완화되는 조건으로 반영됩니다. 기간 1년, 급격한 발생, 점진적 회복, 구조적 성격을 고려해 TurkStream에 대해 초기에는 큰 하향 조정을 적용하고 이후 12개월 동안 부분적으로만 회복되는 절대 송출능력 값을 제안합니다.",
      "values": [
        {
          "Month": 7,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 9.52,
          "rationale": "TurkStream의 직접 영향이 시작되는 첫 월로 선택했습니다. 이벤트에 제시된 일평균 4,740만 입방미터를 연율화한 약 17.30 Bcm/y를 기준 용량으로 보고, 60% 차질 중 대체 가능 25%를 제외한 순차질 45%를 반영해 55% 수준인 9.52 Bcm/y로 산정했습니다."
        },
        {
          "Month": 8,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 9.87,
          "rationale": "1년 영향 구간의 두 번째 월로, 급격한 차질 이후 점진 회복을 반영했습니다. 초기 55% 수준에서 월별로 완만히 회복되는 경로를 적용해 9.87 Bcm/y로 산정했습니다."
        },
        {
          "Month": 9,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 10.22,
          "rationale": "차질 지속 기간 내 TurkStream 월별 override 값으로 선택했습니다. 구조적 차질이 이어지지만 점진 회복이 진행되는 것으로 보아 기준 용량 대비 약 59.1% 수준인 10.22 Bcm/y를 적용했습니다."
        },
        {
          "Month": 10,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 10.58,
          "rationale": "1년 차질 구간 중 회복 경로의 네 번째 월입니다. 순차질이 월별로 완만히 축소되는 전제를 적용해 10.58 Bcm/y로 산정했습니다."
        },
        {
          "Month": 11,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 10.93,
          "rationale": "TurkStream의 구조적 송출 차질이 계속되나 일부 회복이 누적되는 월로 선택했습니다. 기준 용량 대비 약 63.2% 수준을 적용해 10.93 Bcm/y로 제안했습니다."
        },
        {
          "Month": 12,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 11.28,
          "rationale": "차질 발생 후 6개월차에 해당하는 월로, 대체 공급 부족으로 정상화는 제한적이라고 보았습니다. 점진 회복 경로상 11.28 Bcm/y를 적용했습니다."
        },
        {
          "Month": 1,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 11.64,
          "rationale": "1년 영향 구간이 다음 해로 이어지는 첫 월입니다. 구조적 차질을 유지하되 회복 누적분을 반영해 11.64 Bcm/y로 산정했습니다."
        },
        {
          "Month": 2,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 11.99,
          "rationale": "TurkStream 차질이 지속되는 월로 선택했습니다. 대체 공급 부족 조건을 유지하면서 점진 회복 경로를 적용해 11.99 Bcm/y를 제안했습니다."
        },
        {
          "Month": 3,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 12.35,
          "rationale": "회복 후반부에 접어드는 월이지만 구조적 차질로 완전 정상화는 배제했습니다. 기준 용량 대비 약 71.4% 수준인 12.35 Bcm/y로 산정했습니다."
        },
        {
          "Month": 4,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 12.7,
          "rationale": "1년 영향 구간 내 점진 회복이 더 진행된 월입니다. 순차질의 일부만 축소되는 보수적 회복 경로를 반영해 12.70 Bcm/y를 적용했습니다."
        },
        {
          "Month": 5,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 13.05,
          "rationale": "차질 종료 전월로, 회복이 상당히 진행되지만 대체 공급 부족과 구조적 변동을 고려해 정상 수준보다 낮게 유지했습니다. 제안값은 13.05 Bcm/y입니다."
        },
        {
          "Month": 6,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 13.41,
          "rationale": "1년 영향 구간의 마지막 월로 선택했습니다. 점진 회복을 반영하되 구조적 차질이 남아 있는 것으로 보아 기준 용량의 약 77.5% 수준인 13.41 Bcm/y를 적용했습니다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "대체 공급원 가능성 25%는 PNG 차질 중 일부만 LNG 전환으로 보완 가능한 조건이며, LiqUtilAdjustment는 이 LNG 전환 물량을 가용 액화설비의 월별 가동률 상향으로 반영하는 parameter입니다. 1년 기간과 급격한 발생을 고려해 즉시 적용하되, 이미 높은 가동률을 보이는 설비는 상향 여력을 제한하고 여유가 큰 설비에 더 보수적으로 배분했습니다.",
      "values": [
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.29018404907975454,
          "rationale": "Arzew GL2Z는 기준 가동률 0.19018404907975456으로 상향 여력이 큰 설비입니다. 대체 LNG 보완분을 우선 배분해 0.10p 상향한 최종 가동률 0.29018404907975456을 적용했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.29018404907975454,
          "rationale": "동일 설비의 1년 대체 공급 적용 구간에 해당합니다. 기준 가동률 0.19018404907975456에 가용 여력 중심 배분을 반영해 0.29018404907975456으로 제안했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.29018404907975454,
          "rationale": "기준값이 낮아 대체 LNG 공급 여력이 있는 월로 판단했습니다. 기준 0.19018404907975456에서 0.10p 상향한 0.29018404907975456을 적용했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.29018404907975454,
          "rationale": "대체 공급 부족 조건에서 상향 여력이 큰 설비로 선택했습니다. 기준 0.19018404907975456에 보수적 상향폭을 더해 0.29018404907975456으로 산정했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.29018404907975454,
          "rationale": "1년 적용 기간 중 동일한 대체 LNG 배분 원칙을 유지했습니다. 기준 가동률 0.19018404907975456에서 0.10p 상향해 0.29018404907975456으로 제안했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.29018404907975454,
          "rationale": "차질 지속 구간의 월별 대체 LNG 공급원으로 선택했습니다. 낮은 기준 가동률 0.19018404907975456을 0.29018404907975456으로 상향했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": 0.1840490797546012,
          "proposedValue": 0.2840490797546012,
          "rationale": "다음 해 적용 구간에서도 Arzew GL2Z의 기준 가동률이 0.18404907975460122로 낮아 상향 여력이 큽니다. 동일한 보수적 상향폭을 적용해 0.2840490797546012로 산정했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": 0.1840490797546012,
          "proposedValue": 0.2840490797546012,
          "rationale": "1년 대체 공급 구간에 포함되는 월입니다. 기준 0.18404907975460122에 0.10p를 더해 최종 가동률 0.2840490797546012를 적용했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": 0.1840490797546012,
          "proposedValue": 0.2840490797546012,
          "rationale": "상향 여력이 큰 액화설비로 계속 활용하는 월입니다. 기준값 0.18404907975460122에서 보수적으로 0.10p 상향한 0.2840490797546012를 제안했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": 0.1840490797546012,
          "proposedValue": 0.2840490797546012,
          "rationale": "대체 LNG 보완이 필요한 기간 내 월별 적용값입니다. 기준 가동률 0.18404907975460122에 상향 여력을 반영해 0.2840490797546012로 산정했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": 0.1840490797546012,
          "proposedValue": 0.2840490797546012,
          "rationale": "1년 영향 구간의 후반부에도 대체 공급 부족이 남아 있어 가동률 상향을 유지했습니다. 기준 0.18404907975460122에서 0.2840490797546012로 제안했습니다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.1840490797546012,
          "proposedValue": 0.2840490797546012,
          "rationale": "1년 적용 기간의 마지막 월입니다. 기준 가동률 0.18404907975460122에 대체 LNG 배분을 반영해 0.2840490797546012를 적용했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.7193333333333335,
          "proposedValue": 0.7793333333333335,
          "rationale": "NLNG T6는 기준 가동률 0.7193333333333335로 추가 상향 여력이 있습니다. 대체 LNG 전환 물량의 일부를 배분해 0.06p 상향한 0.7793333333333335로 산정했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.713456790123457,
          "proposedValue": 0.773456790123457,
          "rationale": "기준 가동률 0.713456790123457에 대해 대체 LNG 공급 보완분을 반영했습니다. 설비 여력을 감안해 0.06p 상향한 0.773456790123457을 적용했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.7732345679012347,
          "proposedValue": 0.8332345679012347,
          "rationale": "NLNG T6의 해당 월 기준 가동률은 0.7732345679012347입니다. 25% 수준의 제한적 LNG 대체를 고려해 0.06p만 상향한 0.8332345679012347로 제안했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7120493827160495,
          "proposedValue": 0.7720493827160495,
          "rationale": "기준 0.7120493827160495로 상향 여력이 있는 월입니다. 대체 LNG 보완분을 반영해 최종 가동률 0.7720493827160495로 산정했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.7283209876543211,
          "proposedValue": 0.7883209876543211,
          "rationale": "차질 기간 내 LNG 대체 공급 후보 월로 선택했습니다. 기준 0.7283209876543211에 0.06p 상향을 적용해 0.7883209876543211로 제안했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7569876543209877,
          "proposedValue": 0.8169876543209877,
          "rationale": "기준 가동률 0.7569876543209877에서 추가 생산 여력이 남아 있다고 보았습니다. 제한적 대체 공급 조건을 반영해 0.8169876543209877로 산정했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": 0.79320987654321,
          "proposedValue": 0.85320987654321,
          "rationale": "다음 해 1월 기준 가동률 0.79320987654321에 대해 동일한 대체 LNG 배분 원칙을 적용했습니다. 0.06p 상향해 0.85320987654321로 제안했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": 0.7381234567901235,
          "proposedValue": 0.7981234567901235,
          "rationale": "기준값 0.7381234567901235에 제한적 LNG 대체 수요를 반영했습니다. 상향 여력을 고려해 0.7981234567901235로 산정했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": 0.7349629629629632,
          "proposedValue": 0.7949629629629632,
          "rationale": "대체 공급 적용 기간 내 NLNG T6의 기준 가동률은 0.7349629629629632입니다. 0.06p 상향한 0.7949629629629632를 최종 입력값으로 제안했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": 0.7433086419753088,
          "proposedValue": 0.8033086419753088,
          "rationale": "기준 가동률 0.7433086419753088에 대체 LNG 배분을 반영했습니다. 설비 가동률 상한에 여유가 있어 0.8033086419753088로 산정했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": 0.7029382716049384,
          "proposedValue": 0.7629382716049384,
          "rationale": "기준 0.7029382716049384로 상향 여력이 충분한 월입니다. 제한적인 LNG 대체 가능성을 반영해 0.7629382716049384로 제안했습니다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.7068148148148149,
          "proposedValue": 0.7668148148148148,
          "rationale": "1년 적용 기간의 마지막 월로, 기준 가동률 0.7068148148148149에 대체 LNG 공급분을 일부 배분했습니다. 최종 가동률은 0.7668148148148148입니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.998,
          "rationale": "Sabine Pass T1-T2는 유럽 대체 LNG 공급에 연결성이 높은 설비이나 기준 가동률이 0.978로 이미 높습니다. 잔여 여력을 감안해 0.02p만 상향한 0.998로 제안했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.998,
          "rationale": "해당 월 기준 가동률 0.978에 대해 높은 기존 가동률을 고려해 제한적으로 상향했습니다. 최종 입력값은 0.998입니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.998,
          "rationale": "대체 LNG 전환 가능성이 있으나 기준 가동률이 높은 월입니다. 상한 접근을 고려해 0.978에서 0.998로 소폭 상향했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.998,
          "rationale": "기준값 0.978에 대체 LNG 보완분을 소폭 배분했습니다. 높은 기존 가동률을 감안해 0.998을 최종값으로 적용했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.998,
          "rationale": "Sabine Pass T1-T2의 해당 월 기준값은 0.978입니다. 잔여 가동 여력을 거의 소진하는 수준으로 0.998을 제안했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.998,
          "rationale": "1년 차질 구간 내 미국 LNG의 보완 역할을 반영했습니다. 기준 0.978에서 0.998로 제한적 상향을 적용했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": 0.9532752352743732,
          "proposedValue": 0.9732752352743732,
          "rationale": "다음 해 1월 기준 가동률 0.9532752352743733에 대해 미국 LNG의 대체 공급 역할을 반영했습니다. 0.02p 상향해 0.9732752352743733으로 산정했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": 0.9586746813514612,
          "proposedValue": 0.9786746813514612,
          "rationale": "기준 가동률 0.9586746813514613에 제한적 대체 LNG 배분을 반영했습니다. 최종 가동률은 0.9786746813514613입니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": 0.965192084044823,
          "proposedValue": 0.985192084044823,
          "rationale": "해당 월 기준값 0.965192084044823은 소폭 상향 여력이 있습니다. 상한에 근접하지 않도록 0.02p 상향한 0.985192084044823을 적용했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": 0.9663020188579584,
          "proposedValue": 0.9863020188579584,
          "rationale": "기준 가동률 0.9663020188579585에 대체 LNG 공급 보완분을 배분했습니다. 높은 기존 가동률을 고려해 0.9863020188579585로 제안했습니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": 0.9728194215513204,
          "proposedValue": 0.9928194215513204,
          "rationale": "기준값 0.9728194215513204에 대해 잔여 여력을 활용하되 1.0에 근접한 수준으로 제한했습니다. 최종값은 0.9928194215513204입니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.9789641720392572,
          "proposedValue": 0.9989641720392572,
          "rationale": "1년 적용 구간의 마지막 월로, 기준 가동률 0.9789641720392571에 소폭 상향을 적용했습니다. 상한에 매우 근접한 0.9989641720392571을 최종값으로 제안했습니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 50,
  "scenario_id": 286,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.534 | 3.534 | 2781 | 146 | 2927 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 02:11.366 | 131.366 | 12423 | 14859 | 27282 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:02.944 | 182.944 | 20247 | 9915 | 30162 |

### event_type_l2_id=5 발전소 Utilization 변동

#### Scenario Group

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

#### Dimension Template

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

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": null,
      "comment": "시간축",
      "dimension_key": "affected_period",
      "dimension_label": "영향 기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": "6개월",
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "6개월",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": true
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "흡수분만큼 타 source 비중으로 이전 : 감소한 발전원을 대체 가능한 전원 믹스의 정책·가용성 제약에 따라 Gas/Coal/Renewable/Nuclear 비중에 재배분",
      "dimension_key": "alt_energy_absorption",
      "dimension_label": "타 에너지원 흡수 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": "50%",
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "50%",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": true
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "발전부문 가스 비중 조정(capa GW→비중 환산) : 발전소 가동률·용량 변화가 LNG 수요에 미치는 영향을 PowerMix의 Gas 비중 변화로 환산",
      "dimension_key": "capacity_change_scale",
      "dimension_label": "Capacity 변화 규모",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": "3~5 GW",
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "3~5 GW",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": true
    },
    {
      "canonical_parameter_name": null,
      "comment": "발전부문 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영",
      "dimension_key": "capacity_change_scale",
      "dimension_label": "Capacity 변화 규모",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": "3~5 GW",
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "3~5 GW",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": true
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격/점진",
      "dimension_key": "onset_pattern",
      "dimension_label": "발생 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": "급격",
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "급격",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": true
    },
    {
      "canonical_parameter_name": null,
      "comment": "원상복귀 속도",
      "dimension_key": "recovery_pattern",
      "dimension_label": "회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": "점진",
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "점진",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": true
    },
    {
      "canonical_parameter_name": null,
      "comment": "단발(정비·사고)/구조적(COD·폐쇄)",
      "dimension_key": "structural_change_yn",
      "dimension_label": "구조적 변동 여부",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": "구조적",
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "구조적",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": true
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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [287, 288]
- scenario_count: 2
- 매핑 후보 검증: FAIL
- LLM selected 검증: FAIL
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

- ERROR scenario_id=287 elapsed=02:13.193 (133.193s): `MIBaseError('[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id=287')`

#### scenario_id=288 [model_parameter_agent_test] 6개월 대규모 발전 차질 절반만 흡수

- 소요시간: 01:22.029 (82.029s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "affected_period": "6개월",
    "alt_energy_absorption": "50%",
    "capacity_change_scale": "3~5 GW",
    "onset_pattern": "급격",
    "recovery_pattern": "점진",
    "structural_change_yn": "구조적"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "발전 설비 이용률 차질이 6개월 지속되고 절반만 대체 가능해 전력 믹스와 가스 수요 조정이 필요하다.",
  "probability_delta": 4.0,
  "probability_score": 40.0,
  "scenario_group_id": 51,
  "scenario_id": 288,
  "status": "created",
  "title": "[model_parameter_agent_test] 6개월 대규모 발전 차질 절반만 흡수"
}
```

##### Validation Summary

- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 1 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"parameter|5|demand|powermixadjustment|powermix": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모 3~5 GW는 발전부문 가동률·용량 변화가 Gas 발전 비중에 미치는 영향을 PowerMix 입력으로 반영해야 하므로 이 parameter와 직접 연결된다. 타 에너지원 흡수 가능성 50%는 차질분 중 절반만 다른 전원으로 이전되는 조건이어서 Gas 비중의 하향 조정 폭을 완화하는 역할을 하며, 6개월 영향과 점진 회복 조건을 감안해 2026년 연간 Gas 비중에 보수적으로 반영한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.39 | 선택된 좌표는 2026년 United States의 Gas PowerMix이며, 제공된 기준값 목록에는 동일 국가의 기준 record가 없어 reference id는 비워 둔다. 3~5 GW 규모의 급격한 발전 차질이 6개월 지속되지만 50%가 타 에너지원으로 흡수되는 조건을 반영해, 연간 Gas 발전 비중을 같은 분수 형식의 최종 입력값 0.39로 보수적으로 설정한다. |

##### Final DB Proposal Row

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
  "model_param_proposal_id": 36,
  "proposal_completed_dtm": "2026-07-07 17:27:47.417459",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Country",
          "Energy Source"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "Capacity 변화 규모 3~5 GW는 발전부문 가동률·용량 변화가 Gas 발전 비중에 미치는 영향을 PowerMix 입력으로 반영해야 하므로 이 parameter와 직접 연결된다. 타 에너지원 흡수 가능성 50%는 차질분 중 절반만 다른 전원으로 이전되는 조건이어서 Gas 비중의 하향 조정 폭을 완화하는 역할을 하며, 6개월 영향과 점진 회복 조건을 감안해 2026년 연간 Gas 비중에 보수적으로 반영한다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.39,
          "rationale": "선택된 좌표는 2026년 United States의 Gas PowerMix이며, 제공된 기준값 목록에는 동일 국가의 기준 record가 없어 reference id는 비워 둔다. 3~5 GW 규모의 급격한 발전 차질이 6개월 지속되지만 50%가 타 에너지원으로 흡수되는 조건을 반영해, 연간 Gas 발전 비중을 같은 분수 형식의 최종 입력값 0.39로 보수적으로 설정한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 51,
  "scenario_id": 288,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.056 | 4.056 | 2796 | 130 | 2926 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:11.584 | 11.584 | 6035 | 597 | 6632 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:49.980 | 49.980 | 7669 | 1870 | 9539 |

### event_type_l2_id=6 겨울 한파

#### Scenario Group

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

#### Dimension Template

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

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "석탄·석유 등 흡수 비율",
      "dimension_key": "alt_energy_absorption",
      "dimension_label": "타 에너지원 흡수 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 289,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 290,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "Temperature",
      "comment": "기온 직접 입력(대안 경로) : 한파 영향 국가·월의 Temperature를 하향 조정하고, 강도에 따라 평년 대비 온도 편차를 월별로 차등 적용",
      "dimension_key": "cold_wave_intensity",
      "dimension_label": "한파 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "WeatherAdjustment",
        "model_table": "table2",
        "semantic_axes": "기온 직접 — 국가·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "-2~-3℃: 약",
          "scenario_id": 289,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "-5℃ 이하: 강",
          "scenario_id": 290,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "평년 대비 -℃ → HDD(난방도일) 변환 입력 : HDD는 미대상 파라미터이므로 직접 조정하지 않고, 한파 강도는 Temperature 하향 또는 강도·월 분배 판단 근거로만 사용",
      "dimension_key": "cold_wave_intensity",
      "dimension_label": "한파 강도",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "-2~-3℃: 약",
          "scenario_id": 289,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "-5℃ 이하: 강",
          "scenario_id": 290,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "재고는 수급모델 input 아님(Annual Balancing) — 영향 증폭/완화 해석 맥락",
      "dimension_key": "entry_gas_inventory",
      "dimension_label": "진입 시점 가스 재고 (평년 대비)",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "+20%↑ (매우 여유)",
          "scenario_id": 289,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "-20%↓ (매우 부족)",
          "scenario_id": 290,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "월별 수요 분배",
      "dimension_key": "peak_timing_pattern",
      "dimension_label": "Peak 시점, 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "단발 피크",
          "scenario_id": 289,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "지속 피크",
          "scenario_id": 290,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "동절기 월 슬롯",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 289,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3개월",
          "scenario_id": 290,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [289, 290]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=289 [model_parameter_agent_test] 짧은 약한 한파와 전원 흡수

- 소요시간: 02:43.412 (163.412s)
- attempt: 1

##### Scenario Major Info

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

##### Validation Summary

- expected_parameters: `["Temperature", "PowerMix"]`
- selected_parameters: `["Temperature"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 2 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 1 | 한파 강도 dimension은 국가·연·월 Temperature 입력을 직접 하향 조정하는 근거이며, 이번 시나리오는 약한 한파로 해석된다. 기간은 1개월 이하이고 단발 피크 성격이므로 적용 범위는 이벤트가 명시한 미국 3월 한 달로 제한하며, 재고 여유와 가격 영향 중립성을 고려해 과도한 추가 하향은 피한다. |

##### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Month": 3, "Year": 2026}` | null | 2.5 | 선택된 좌표는 이벤트가 지목한 미국 3월 한파 슬롯이다. 해당 좌표의 일치 기준값은 제공되지 않았으므로 reference_id는 비워 두고, 약한 한파 강도 범위와 1개월 이하·단발 피크 조건을 반영해 월평균 기온 입력을 보수적으로 낮은 한자리수인 2.5°C로 설정했다. |

##### Final DB Proposal Row

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
  "model_param_proposal_id": 38,
  "proposal_completed_dtm": "2026-07-07 17:29:53.227234",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "WeatherAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Temperature (°C)"
        ]
      },
      "parameterName": "Temperature",
      "rationale": "한파 강도 dimension은 국가·연·월 Temperature 입력을 직접 하향 조정하는 근거이며, 이번 시나리오는 약한 한파로 해석된다. 기간은 1개월 이하이고 단발 피크 성격이므로 적용 범위는 이벤트가 명시한 미국 3월 한 달로 제한하며, 재고 여유와 가격 영향 중립성을 고려해 과도한 추가 하향은 피한다.",
      "values": [
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 2.5,
          "rationale": "선택된 좌표는 이벤트가 지목한 미국 3월 한파 슬롯이다. 해당 좌표의 일치 기준값은 제공되지 않았으므로 reference_id는 비워 두고, 약한 한파 강도 범위와 1개월 이하·단발 피크 조건을 반영해 월평균 기온 입력을 보수적으로 낮은 한자리수인 2.5°C로 설정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.726 | 3.726 | 2396 | 115 | 2511 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:22.615 | 22.615 | 5917 | 1179 | 7096 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:46.257 | 106.257 | 7450 | 3685 | 11135 |

#### scenario_id=290 [model_parameter_agent_test] 3개월 강한 한파와 대체 제한

- 소요시간: 03:06.916 (186.916s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "25%",
    "cold_wave_intensity": "-5℃ 이하: 강",
    "entry_gas_inventory": "-20%↓ (매우 부족)",
    "peak_timing_pattern": "지속 피크",
    "period": "3개월"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "강한 한파가 3개월 지속되고 재고가 부족해 난방 수요 및 발전용 가스 수요가 확대된다.",
  "probability_delta": 4.0,
  "probability_score": 40.0,
  "scenario_group_id": 52,
  "scenario_id": 290,
  "status": "created",
  "title": "[model_parameter_agent_test] 3개월 강한 한파와 대체 제한"
}
```

##### Validation Summary

- expected_parameters: `["Temperature", "PowerMix"]`
- selected_parameters: `["Temperature", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 4 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=4, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 3 | 한파 강도 dimension이 기온 직접 입력 parameter와 연결되며, mapping_comment상 한파 영향 국가·월의 Temperature를 하향 조정하는 용도이다. 기간과 지속 피크 정보는 공통 맥락으로 3개월 동안 같은 강도의 월별 기온 스트레스를 적용하는 구조로 반영했다. |
| 2 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 dimension이 PowerMix parameter와 직접 연결되며, 흡수 가능성이 25%로 낮아 석탄·석유 등 대체원이 발전 수요 증가를 충분히 흡수하지 못하고 Gas 비중이 높아지는 방향이다. 기간 정보는 연간 power mix 입력에 단기 충격을 과도하게 반영하지 않도록 보수적 상향 구조로만 반영했다. |

##### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Month": 1, "Year": 2026}` | null | -5.0 | 해당 좌표는 선택된 미국 3개월 한파 적용 월 중 첫 번째 월이다. 미국 기준 기온 record가 제공되지 않았으므로 기준값 참조 없이, ‘-5℃ 이하: 강’ 강도의 보수적 경계값을 월별 최종 기온 입력값으로 적용했다. |
| 2 | `{"Country": "United States", "Month": 2, "Year": 2026}` | null | -5.0 | 해당 좌표는 선택된 미국 3개월 한파 적용 월 중 두 번째 월이다. 지속 피크 패턴이므로 전월과 동일한 강도 유지로 해석하고, 미국 기준 기온 record가 없어 강한 한파의 경계값인 -5.0℃를 최종 입력값으로 적용했다. |
| 3 | `{"Country": "United States", "Month": 3, "Year": 2026}` | null | -5.0 | 해당 좌표는 선택된 미국 3개월 한파 적용 월 중 마지막 월이다. 이벤트의 중북부·오대호 한파 경로와 지속 피크 조건을 반영하되, 미국 기준 기온 record가 제공되지 않아 강한 한파 임계 수준인 -5.0℃를 최종 입력값으로 적용했다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.45 | 해당 좌표는 선택된 미국 2026년 Gas 발전 비중 입력이다. 미국 기준 power mix record가 제공되지 않았으므로 참조값 없이 산정했으며, 타 에너지원 흡수 가능성 25%는 가스 발전 의존도가 높아지는 조건이지만 3개월 이벤트가 연간 입력에 반영되는 점을 감안해 0.45의 보수적 최종 Gas share로 적용했다. |

##### Final DB Proposal Row

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
  "model_param_proposal_id": 40,
  "proposal_completed_dtm": "2026-07-07 17:30:35.263332",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "WeatherAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Temperature (°C)"
        ]
      },
      "parameterName": "Temperature",
      "rationale": "한파 강도 dimension이 기온 직접 입력 parameter와 연결되며, mapping_comment상 한파 영향 국가·월의 Temperature를 하향 조정하는 용도이다. 기간과 지속 피크 정보는 공통 맥락으로 3개월 동안 같은 강도의 월별 기온 스트레스를 적용하는 구조로 반영했다.",
      "values": [
        {
          "Country": "United States",
          "Month": 1,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -5.0,
          "rationale": "해당 좌표는 선택된 미국 3개월 한파 적용 월 중 첫 번째 월이다. 미국 기준 기온 record가 제공되지 않았으므로 기준값 참조 없이, ‘-5℃ 이하: 강’ 강도의 보수적 경계값을 월별 최종 기온 입력값으로 적용했다."
        },
        {
          "Country": "United States",
          "Month": 2,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -5.0,
          "rationale": "해당 좌표는 선택된 미국 3개월 한파 적용 월 중 두 번째 월이다. 지속 피크 패턴이므로 전월과 동일한 강도 유지로 해석하고, 미국 기준 기온 record가 없어 강한 한파의 경계값인 -5.0℃를 최종 입력값으로 적용했다."
        },
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -5.0,
          "rationale": "해당 좌표는 선택된 미국 3개월 한파 적용 월 중 마지막 월이다. 이벤트의 중북부·오대호 한파 경로와 지속 피크 조건을 반영하되, 미국 기준 기온 record가 제공되지 않아 강한 한파 임계 수준인 -5.0℃를 최종 입력값으로 적용했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Country",
          "Energy Source"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "타 에너지원 흡수 가능성 dimension이 PowerMix parameter와 직접 연결되며, 흡수 가능성이 25%로 낮아 석탄·석유 등 대체원이 발전 수요 증가를 충분히 흡수하지 못하고 Gas 비중이 높아지는 방향이다. 기간 정보는 연간 power mix 입력에 단기 충격을 과도하게 반영하지 않도록 보수적 상향 구조로만 반영했다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 좌표는 선택된 미국 2026년 Gas 발전 비중 입력이다. 미국 기준 power mix record가 제공되지 않았으므로 참조값 없이 산정했으며, 타 에너지원 흡수 가능성 25%는 가스 발전 의존도가 높아지는 조건이지만 3개월 이벤트가 연간 입력에 반영되는 점을 감안해 0.45의 보수적 최종 Gas share로 적용했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 52,
  "scenario_id": 290,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:09.350 | 9.350 | 2389 | 115 | 2504 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:27.540 | 87.540 | 5906 | 4650 | 10556 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:06.892 | 66.892 | 7515 | 3288 | 10803 |

### event_type_l2_id=7 여름 폭염

#### Scenario Group

```json
{
  "description": "여름 폭염 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
  "dimension_selected": [
    "period",
    "heatwave_intensity",
    "entry_gas_inventory",
    "injection_pattern",
    "alt_energy_absorption",
    "peak_timing_pattern"
  ],
  "event_type": {
    "event_type_l1_id": 2,
    "event_type_l2_id": 7,
    "level_1_code": "demand",
    "level_1_label": "수요",
    "level_2_code": "summer_heat_wave",
    "level_2_label": "여름 폭염"
  },
  "event_type_l2_id": 7,
  "mi_event_id": 1144,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 53,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 여름 폭염 scenario_group",
  "title": "[model_parameter_agent_test] 여름 폭염 추가 검증"
}
```

#### Dimension Template

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
    "dim_key": "heatwave_intensity",
    "display_order": 2,
    "label": "폭염 강도",
    "required": true,
    "value_enums": [
      "+1~+2℃: 약",
      "+2~+3℃: 중",
      "+3℃ 이상: 강",
      "기록적(+4℃ 이상·기록 경신)"
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
    "dim_key": "injection_pattern",
    "display_order": 4,
    "label": "Injection 패턴",
    "required": false,
    "value_enums": [
      "적극",
      "정상",
      "지연"
    ]
  },
  {
    "dim_key": "alt_energy_absorption",
    "display_order": 5,
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
    "display_order": 6,
    "label": "Peak 시점, 패턴",
    "required": false,
    "value_enums": [
      "전체 균등",
      "6월 Peak",
      "7월 Peak",
      "8월 Peak"
    ]
  }
]
```

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "재생E·원전 등 흡수",
      "dimension_key": "alt_energy_absorption",
      "dimension_label": "타 에너지원 흡수 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 291,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 292,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "재고는 수급모델 input 아님 — 해석 맥락",
      "dimension_key": "entry_gas_inventory",
      "dimension_label": "진입 시점 가스 재고 (평년 대비)",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "+20%↑ (매우 여유)",
          "scenario_id": 291,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "-20%↓ (매우 부족)",
          "scenario_id": 292,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "Temperature",
      "comment": "기온 직접 입력(대안 경로) : 폭염 영향 국가·월의 Temperature를 상향 조정하고, 냉방 수요 피크 월에 더 큰 조정폭을 적용",
      "dimension_key": "heatwave_intensity",
      "dimension_label": "폭염 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "WeatherAdjustment",
        "model_table": "table2",
        "semantic_axes": "기온 직접 — 국가·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "+1~+2℃: 약",
          "scenario_id": 291,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "+3℃ 이상: 강",
          "scenario_id": 292,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "평년 대비 +℃ → CDD(냉방도일) 변환 입력 : CDD는 미대상 파라미터이므로 직접 조정하지 않고, 폭염 강도는 Temperature 상향 또는 강도·월 분배 판단 근거로만 사용",
      "dimension_key": "heatwave_intensity",
      "dimension_label": "폭염 강도",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "+1~+2℃: 약",
          "scenario_id": 291,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "+3℃ 이상: 강",
          "scenario_id": 292,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "재고 회복 속도 = 재고 개념 — 수급모델 input 아님(맥락)",
      "dimension_key": "injection_pattern",
      "dimension_label": "Injection 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "정상",
          "scenario_id": 291,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "지연",
          "scenario_id": 292,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "월별 분배",
      "dimension_key": "peak_timing_pattern",
      "dimension_label": "Peak 시점, 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "단발 피크",
          "scenario_id": 291,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "지속 피크",
          "scenario_id": 292,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "하절기 월 슬롯(동남아·인도 4~5월 포함)",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 291,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3개월",
          "scenario_id": 292,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 7,
  "mapping_count": 7,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:13:57.374841",
  "detail_analysis": "사건 요약:\n6월 5일 Platts Daily Report에서 아시아 여름 수요와 중국·일본 수급 지지가 JKM 상승을 이끈 것으로 정리됨. 6월 9일 Platts Daily Report에서는 트럼프의 이란 휴전 언급과 이스라엘·이란 공격 중단으로 지정학 프리미엄이 일부 되돌려지며 JKM·유럽 LNG가 하락했으나, 아시아 여름 수요와 Ichthys 불확실성이 시장 긴장을 유지한 것으로 언급됨. 직전 요약의 6월 2일 아시아 폭염과 Ichthys 파업에 따른 JKM 상승 요인이 이후 6월 5일과 6월 9일에도 아시아 여름 수요 지지 요인으로 반복 확인됨.\n\n영향 경로:\n아시아 여름 수요는 냉방 전력 수요를 통해 발전용 LNG 수요를 지지하는 계절성 Fundamental 요인임. 6월 5일에는 중국·일본 수급 지지가 함께 언급되며 동북아 LNG 구매 여건을 뒷받침함. 6월 9일에는 동방향 차익거래 개방과 미국 LNG의 아시아 배분 확대가 언급되며, JKM/TTF 상대가격과 아시아 수요가 카고 흐름을 아시아 쪽으로 유도하는 경로가 유지됨. Ichthys 불확실성, 호르무즈 차질, 중동 전쟁, EU 저장률 41.25% 및 42.48%는 본 Event의 핵심인 여름 수요 충격의 가격 민감도를 높이는 배경임.\n\n시장 반응:\n6월 2일 Platts Daily Report에서는 Ichthys 파업과 아시아 폭염이 JKM을 끌어올린 것으로 언급됨. 6월 5일 Platts Daily Report에서는 아시아 여름 수요와 중국·일본 수급 지지가 JKM 상승을 견인한 것으로 평가됨. 6월 9일 Platts Daily Report에서는 지정학 프리미엄 일부 되돌림으로 JKM·유럽 LNG가 하락했으나, 아시아 여름 수요와 Ichthys 불확실성, EU 저장률 42.48%, 동방향 차익거래 개방, 미국 LNG의 아시아 배분 확대가 시장 긴장을 유지한 것으로 정리됨. 가격 방향은 단기적으로 지정학 프리미엄 축소에 따른 하락 압력과 아시아 여름 수요에 따른 JKM 지지 요인이 병존하는 구도임.\n\nLNG 시장 관점:\n이번 Event의 경계는 아시아 여름 폭염·냉방 수요가 발전용 LNG 수요와 JKM 프리미엄을 지지하는 수요 이벤트임. 신규 Record에는 중동 전쟁, 호르무즈, 미국 설비 변화, 신규 멕시코 공급, 유럽 저장률 등 여러 하위 이슈가 포함되나, 본 Event에서는 여름 수요의 가격 민감도와 카고 유입 유인을 설명하는 배경으로 한정됨. 최신 업데이트 기준 아시아 여름 수요는 JKM을 단독으로 계속 상승시키기보다는 지정학 프리미엄 되돌림 이후에도 하방을 제한하고 동방향 차익거래를 유지하는 요인으로 기능함. 후속 관찰 지표는 중국·일본 실제 스팟 구매, 미국 LNG의 아시아 배분 지속 여부, JKM/TTF 스프레드 변화임.",
  "event_title_ko": "아시아 여름 수요에 JKM 지지 지속",
  "event_type_l2_id": 7,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-11T00:00:00",
  "mi_event_id": "1144",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[아시아 LNG 수요] 여름 냉방 수요 재확인 → JKM 지지·차익거래 동방향 유지",
  "source_mi_record_ids": [
    2222,
    2230,
    2232,
    2271,
    2327,
    2353,
    2393,
    2415,
    2416,
    2461,
    2582,
    2712,
    2714
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [291, 292]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=291 [model_parameter_agent_test] 짧은 약한 폭염과 전원 흡수

- 소요시간: 01:31.053 (91.053s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "100%",
    "entry_gas_inventory": "+20%↑ (매우 여유)",
    "heatwave_intensity": "+1~+2℃: 약",
    "injection_pattern": "정상",
    "peak_timing_pattern": "단발 피크",
    "period": "1개월 이하"
  },
  "impact": {
    "hh": "중립",
    "jkm": "중립",
    "ttf": "중립"
  },
  "narrative": "약한 폭염이 단기에 그치고 전원 흡수가 충분해 추가 LNG 수요는 제한된다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 53,
  "scenario_id": 291,
  "status": "created",
  "title": "[model_parameter_agent_test] 짧은 약한 폭염과 전원 흡수"
}
```

##### Validation Summary

- expected_parameters: `["Temperature", "PowerMix"]`
- selected_parameters: `["Temperature", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 4 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=4, basecaseValue_present=2 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 2 | 폭염 강도 차원이 기온 직접 입력 parameter와 연결되며, 약한 폭염은 해당 국가·월의 Temperature를 소폭 상향하는 요인이다. 기간은 1개월 이하이고 피크가 단발이라는 보조 맥락을 반영해 적용 범위는 단기 월 슬롯으로 한정하며, 강도는 +1~+2℃ 범위의 하단에 가까운 보수적 상향 수준으로 최종 °C 입력값을 제안한다. |
| 2 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 2 | 타 에너지원 흡수 가능성 차원이 발전 믹스 parameter와 직접 연결되며, 100% 흡수는 폭염에 따른 추가 전력 수요가 가스 발전 비중 상승으로 전이되지 않는다는 의미로 해석된다. 기간도 짧고 재고·injection 맥락이 긴장을 키우지 않으므로 Gas 비중은 기준 발전 믹스를 유지하는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | null | 28.0 | 해당 좌표는 현재 기준월부터 1개월 이하의 단발 폭염이 적용되는 2026년 7월 중국 월간 기온 입력 슬롯이다. 제공된 기준값 그룹에는 이 좌표와 일치하는 7월 기준 record가 없어 reference는 비워 두며, 약한 폭염의 +1~+2℃ 범위 중 보수적인 하단 상향을 반영한 최종 월간 기온 수준으로 28.0℃를 제안한다. |
| 2 | `{"Country": "Japan", "Month": 7, "Year": 2026}` | null | 27.0 | 해당 좌표는 현재 기준월부터 1개월 이하의 단발 폭염이 적용되는 2026년 7월 일본 월간 기온 입력 슬롯이다. 제공된 기준값 그룹에는 이 좌표와 일치하는 7월 기준 record가 없어 reference는 비워 두며, 약한 폭염의 +1~+2℃ 범위 중 보수적인 하단 상향을 반영한 최종 월간 기온 수준으로 27.0℃를 제안한다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0346 | 해당 좌표의 기준 Gas 발전 비중은 0.0346이다. 타 에너지원 흡수 가능성이 100%로 제시되어 폭염 수요가 Gas 비중을 추가로 끌어올리지 않는다고 보아 최종 입력값은 기준값과 동일한 0.0346으로 유지한다. |
| 2 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.323 | 해당 좌표의 기준 Gas 발전 비중은 0.323이다. 타 에너지원 흡수 가능성이 100%로 제시되어 폭염 수요가 Gas 비중을 추가로 끌어올리지 않는다고 보아 최종 입력값은 기준값과 동일한 0.323으로 유지한다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1144,
  "model_param_proposal_id": 37,
  "proposal_completed_dtm": "2026-07-07 17:29:18.451036",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "WeatherAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Temperature (°C)"
        ]
      },
      "parameterName": "Temperature",
      "rationale": "폭염 강도 차원이 기온 직접 입력 parameter와 연결되며, 약한 폭염은 해당 국가·월의 Temperature를 소폭 상향하는 요인이다. 기간은 1개월 이하이고 피크가 단발이라는 보조 맥락을 반영해 적용 범위는 단기 월 슬롯으로 한정하며, 강도는 +1~+2℃ 범위의 하단에 가까운 보수적 상향 수준으로 최종 °C 입력값을 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 28.0,
          "rationale": "해당 좌표는 현재 기준월부터 1개월 이하의 단발 폭염이 적용되는 2026년 7월 중국 월간 기온 입력 슬롯이다. 제공된 기준값 그룹에는 이 좌표와 일치하는 7월 기준 record가 없어 reference는 비워 두며, 약한 폭염의 +1~+2℃ 범위 중 보수적인 하단 상향을 반영한 최종 월간 기온 수준으로 28.0℃를 제안한다."
        },
        {
          "Country": "Japan",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 27.0,
          "rationale": "해당 좌표는 현재 기준월부터 1개월 이하의 단발 폭염이 적용되는 2026년 7월 일본 월간 기온 입력 슬롯이다. 제공된 기준값 그룹에는 이 좌표와 일치하는 7월 기준 record가 없어 reference는 비워 두며, 약한 폭염의 +1~+2℃ 범위 중 보수적인 하단 상향을 반영한 최종 월간 기온 수준으로 27.0℃를 제안한다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Country",
          "Energy Source"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "타 에너지원 흡수 가능성 차원이 발전 믹스 parameter와 직접 연결되며, 100% 흡수는 폭염에 따른 추가 전력 수요가 가스 발전 비중 상승으로 전이되지 않는다는 의미로 해석된다. 기간도 짧고 재고·injection 맥락이 긴장을 키우지 않으므로 Gas 비중은 기준 발전 믹스를 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0346,
          "rationale": "해당 좌표의 기준 Gas 발전 비중은 0.0346이다. 타 에너지원 흡수 가능성이 100%로 제시되어 폭염 수요가 Gas 비중을 추가로 끌어올리지 않는다고 보아 최종 입력값은 기준값과 동일한 0.0346으로 유지한다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.323,
          "rationale": "해당 좌표의 기준 Gas 발전 비중은 0.323이다. 타 에너지원 흡수 가능성이 100%로 제시되어 폭염 수요가 Gas 비중을 추가로 끌어올리지 않는다고 보아 최종 입력값은 기준값과 동일한 0.323으로 유지한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 53,
  "scenario_id": 291,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.577 | 3.577 | 2623 | 122 | 2745 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:23.810 | 23.810 | 6331 | 1302 | 7633 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:44.534 | 44.534 | 7937 | 2344 | 10281 |

#### scenario_id=292 [model_parameter_agent_test] 3개월 강한 폭염과 전원 흡수 부족

- 소요시간: 02:21.171 (141.171s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "25%",
    "entry_gas_inventory": "-20%↓ (매우 부족)",
    "heatwave_intensity": "+3℃ 이상: 강",
    "injection_pattern": "지연",
    "peak_timing_pattern": "지속 피크",
    "period": "3개월"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "강한 폭염이 3개월 지속되어 냉방 및 발전용 가스 수요가 증가한다.",
  "probability_delta": 4.0,
  "probability_score": 40.0,
  "scenario_group_id": 53,
  "scenario_id": 292,
  "status": "created",
  "title": "[model_parameter_agent_test] 3개월 강한 폭염과 전원 흡수 부족"
}
```

##### Validation Summary

- expected_parameters: `["Temperature", "PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 8 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=2, basecaseValue_present=2 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 2 | 타 에너지원 흡수 가능성 dimension은 PowerMix에서 재생에너지·원전 등이 냉방 전력 증가를 얼마나 대체할 수 있는지를 직접 설명하며, 25%는 대체 흡수력이 낮아 Gas 비중 상향을 시사합니다. 기간 3개월과 지속 피크는 연중 일부 기간의 강한 수요 충격이라는 적용 구조를 제공하므로, 중국·일본의 2026년 Gas 발전 비중을 연간값 기준으로 보수적으로 상향 조정합니다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.036 | 중국 2026년 Gas 발전 비중 슬롯은 선택된 연간 PowerMix 입력이며 기준값 0.0346을 사용했다. 타 에너지원 흡수 가능성이 25%로 낮아 폭염기 추가 전력수요 중 가스 발전 부담이 커지는 방향이지만, 3개월 영향이 연간 비중에 반영되는 점을 고려해 보수적으로 약 4% 상대 상향하여 0.036으로 제안한다. |
| 2 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.336 | 일본 2026년 Gas 발전 비중 슬롯은 선택된 연간 PowerMix 입력이며 기준값 0.323을 사용했다. 타 에너지원 흡수 가능성이 25%에 그치는 조건에서 지속 피크 폭염의 냉방 전력 수요를 가스 발전이 일부 흡수한다고 보고, 연간 입력값이라는 제약을 반영해 보수적으로 약 4% 상대 상향하여 0.336으로 제안한다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1144,
  "model_param_proposal_id": 42,
  "proposal_completed_dtm": "2026-07-07 17:31:39.654875",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Country",
          "Energy Source"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "타 에너지원 흡수 가능성 dimension은 PowerMix에서 재생에너지·원전 등이 냉방 전력 증가를 얼마나 대체할 수 있는지를 직접 설명하며, 25%는 대체 흡수력이 낮아 Gas 비중 상향을 시사합니다. 기간 3개월과 지속 피크는 연중 일부 기간의 강한 수요 충격이라는 적용 구조를 제공하므로, 중국·일본의 2026년 Gas 발전 비중을 연간값 기준으로 보수적으로 상향 조정합니다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.036,
          "rationale": "중국 2026년 Gas 발전 비중 슬롯은 선택된 연간 PowerMix 입력이며 기준값 0.0346을 사용했다. 타 에너지원 흡수 가능성이 25%로 낮아 폭염기 추가 전력수요 중 가스 발전 부담이 커지는 방향이지만, 3개월 영향이 연간 비중에 반영되는 점을 고려해 보수적으로 약 4% 상대 상향하여 0.036으로 제안한다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.336,
          "rationale": "일본 2026년 Gas 발전 비중 슬롯은 선택된 연간 PowerMix 입력이며 기준값 0.323을 사용했다. 타 에너지원 흡수 가능성이 25%에 그치는 조건에서 지속 피크 폭염의 냉방 전력 수요를 가스 발전이 일부 흡수한다고 보고, 연간 입력값이라는 제약을 반영해 보수적으로 약 4% 상대 상향하여 0.336으로 제안한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 53,
  "scenario_id": 292,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.098 | 3.098 | 2618 | 122 | 2740 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:23.230 | 23.230 | 6322 | 1024 | 7346 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:37.839 | 97.839 | 8076 | 2711 | 10787 |

### event_type_l2_id=8 원자력 발전

#### Scenario Group

```json
{
  "description": "원자력 발전 event_type에 대해 낮은/높은 충격 scenario 2개로 parameter mapping 및 value 차이를 검증한다.",
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
    "event_type_l2_id": 8,
    "level_1_code": "demand",
    "level_1_label": "수요",
    "level_2_code": "nuclear_power",
    "level_2_label": "원자력 발전"
  },
  "event_type_l2_id": 8,
  "mi_event_id": 1173,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 54,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent 추가 event_type 검증용 원자력 발전 scenario_group",
  "title": "[model_parameter_agent_test] 원자력 발전 추가 검증"
}
```

#### Dimension Template

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
      "점진",
      "없음 (Capa 증가 시)"
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
      "없음 (회복 불가)"
    ]
  }
]
```

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": null,
      "comment": "정비=Shoulder/사고·정책=단발 OR 영구",
      "dimension_key": "affected_period",
      "dimension_label": "영향 기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 293,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "6개월",
          "scenario_id": 294,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "재생E·석탄 등 흡수",
      "dimension_key": "alt_energy_absorption",
      "dimension_label": "타 에너지원 흡수 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 293,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 294,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "원전 비중 변동→가스 비중 대체(원전 전용 input 없음)",
      "dimension_key": "capacity_change_scale",
      "dimension_label": "Capacity 변화 규모",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1 GW 미만",
          "scenario_id": 293,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3~5 GW",
          "scenario_id": 294,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "발전 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영",
      "dimension_key": "capacity_change_scale",
      "dimension_label": "Capacity 변화 규모",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1 GW 미만",
          "scenario_id": 293,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3~5 GW",
          "scenario_id": 294,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격(사고)/점진(정비)",
      "dimension_key": "onset_pattern",
      "dimension_label": "발생 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "점진",
          "scenario_id": 293,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "급격",
          "scenario_id": 294,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격(재가동)/점진(COD)",
      "dimension_key": "recovery_pattern",
      "dimension_label": "회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "급격",
          "scenario_id": 293,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "점진",
          "scenario_id": 294,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "단발(정비)/구조적(COD·폐쇄·수명연장)",
      "dimension_key": "structural_change_yn",
      "dimension_label": "구조적 변동 여부",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "단발적",
          "scenario_id": 293,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "구조적",
          "scenario_id": 294,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 8,
  "mapping_count": 7,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:22:52.424842",
  "detail_analysis": "사건 요약:\n한국의 낮은 원전 이용률이 LNG 수요를 지지하는 전력믹스 요인으로 유지되는 내용임. 2026-06-03 Platts Daily Report는 중동 전쟁과 호르무즈 통항 차질 속 JKM이 $19/MMBtu를 상회한 시장 환경을 제시함. 신규 Record는 직전 요약과 동일한 리포트 내용으로, 원전 이용률 자체의 신규 수치나 상태 변화는 추가 확인되지 않음.\n\n영향 경로:\n원전 이용률 저하는 전력 공급 공백을 가스·LNG 발전이 보완하게 만드는 수요 경로임. 한국 전력부문 LNG 소비와 한국향 현물 cargo 조달 관심을 지지할 수 있는 Fundamental 요인임. 신규 Record에서 언급된 아시아 수요 견인, 유럽 재고 40.76%, 좁아진 LNG-TTF 할인, 대서양-아시아 항해비 상승은 글로벌 물동량과 지역 간 유입 여력을 동시에 제약하는 주변 여건임.\n\n시장 반응:\n2026-06-03 Platts Daily Report에서 JKM이 $19/MMBtu를 상회한 것으로 제시됨. 가격 상승의 직접 배경은 중동 전쟁과 호르무즈 통항 차질임. 낮은 원전 이용률에 따른 한국향 LNG 수요 지지는 JKM 프리미엄과 DES Korea cargo 관심에 보조적 상방 압력으로 작용 가능함.\n\nLNG 시장 관점:\n한국은 아시아 LNG 핵심 수입국이므로 원전 이용률 변화가 단기 수입 수요 판단에 중요한 간접 변수임. 이번 업데이트는 원전 이용률 저하 자체의 신규 수치보다, JKM $19/MMBtu 상회와 아시아 수요 견인이 결합된 환경에서 한국 전력믹스 요인이 수요 지지 논리로 유지되는 점이 핵심임. Event 경계는 Event Type상 한국 원전 이용률 저하에 따른 LNG 발전 대체 수요로 한정됨.",
  "event_title_ko": "한국 원전 이용률 저하",
  "event_type_l2_id": 8,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-03T00:00:00",
  "mi_event_id": "1173",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[한국 전력믹스] 낮은 원전 이용률 지속·JKM $19 상회 → LNG 발전 수요 지지",
  "source_mi_record_ids": [
    2370
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [293, 294]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=293 [model_parameter_agent_test] 단기 소규모 원전 차질 흡수

- 소요시간: 00:56.092 (56.092s)
- attempt: 1

##### Scenario Major Info

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
  "narrative": "원전 이용률 저하가 작고 단기에 그쳐 다른 전원이 모두 흡수한다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 54,
  "scenario_id": 293,
  "status": "created",
  "title": "[model_parameter_agent_test] 단기 소규모 원전 차질 흡수"
}
```

##### Validation Summary

- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 1 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"parameter|8|demand|powermixadjustment|powermix": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모는 원전 비중 변동이 전력믹스 내 대체 전원 비중 조정으로 연결될 수 있음을 의미하므로 PowerMix 조정 대상이 된다. 다만 alt_energy_absorption이 100%로 제시되어 재생에너지·석탄 등 비가스 전원이 단기 소규모 원전 차질을 흡수하는 구조이며, 영향 기간도 1개월 이하의 단발적 충격이므로 한국 가스 발전 비중은 연간 기준에서 유지하는 방식으로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.285 | 선택된 좌표는 한국 2026년 가스 발전 비중으로, 현재 기준값 0.285가 존재한다. 원전 차질 규모가 1GW 미만이고 영향 기간이 1개월 이하인 데다 타 에너지원 흡수 가능성이 100%로 제시되어 가스 비중의 연간 입력값에는 추가 상향을 반영하지 않고 기준값을 유지한다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1173,
  "model_param_proposal_id": 41,
  "proposal_completed_dtm": "2026-07-07 17:30:49.323810",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Country",
          "Energy Source"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "Capacity 변화 규모는 원전 비중 변동이 전력믹스 내 대체 전원 비중 조정으로 연결될 수 있음을 의미하므로 PowerMix 조정 대상이 된다. 다만 alt_energy_absorption이 100%로 제시되어 재생에너지·석탄 등 비가스 전원이 단기 소규모 원전 차질을 흡수하는 구조이며, 영향 기간도 1개월 이하의 단발적 충격이므로 한국 가스 발전 비중은 연간 기준에서 유지하는 방식으로 제안한다.",
      "values": [
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.285,
          "rationale": "선택된 좌표는 한국 2026년 가스 발전 비중으로, 현재 기준값 0.285가 존재한다. 원전 차질 규모가 1GW 미만이고 영향 기간이 1개월 이하인 데다 타 에너지원 흡수 가능성이 100%로 제시되어 가스 비중의 연간 입력값에는 추가 상향을 반영하지 않고 기준값을 유지한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 54,
  "scenario_id": 293,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:02.982 | 2.982 | 2183 | 102 | 2285 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:07.257 | 7.257 | 5466 | 392 | 5858 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:29.715 | 29.715 | 7100 | 511 | 7611 |

#### scenario_id=294 [model_parameter_agent_test] 6개월 원전 차질과 LNG 대체수요

- 소요시간: 01:22.659 (82.659s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "affected_period": "6개월",
    "alt_energy_absorption": "50%",
    "capacity_change_scale": "3~5 GW",
    "onset_pattern": "급격",
    "recovery_pattern": "점진",
    "structural_change_yn": "구조적"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "원전 출력 공백이 6개월 이어지고 일부만 대체 가능해 가스발전 확대가 필요하다.",
  "probability_delta": 4.0,
  "probability_score": 40.0,
  "scenario_group_id": 54,
  "scenario_id": 294,
  "status": "created",
  "title": "[model_parameter_agent_test] 6개월 원전 차질과 LNG 대체수요"
}
```

##### Validation Summary

- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 1 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"parameter|8|demand|powermixadjustment|powermix": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모는 원전 출력 공백이 발전믹스 내 가스 비중으로 대체되는 경로와 직접 연결되며, 타 에너지원 흡수 가능성은 해당 공백 중 가스가 부담할 잔여 비중을 조정하는 역할을 한다. 영향 기간은 6개월이고 회복은 점진적이므로 2026년 한국 가스 발전 비중에 한정해 상향 조정하되, 흡수 가능성을 반영해 보수적인 연간 비중 상승으로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.3 | 선택된 좌표는 한국의 2026년 가스 발전 비중으로, 현재 기준값 0.285에 원전 출력 공백의 가스 대체분을 반영했다. 3~5GW 차질이 6개월 지속되고 타 에너지원이 50%를 흡수하는 조건을 연간 발전믹스 기준의 보수적 상승폭으로 환산해 약 1.5%p를 더한 최종 입력값 0.300으로 제안한다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1173,
  "model_param_proposal_id": 43,
  "proposal_completed_dtm": "2026-07-07 17:31:48.047369",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Energy Source",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "Capacity 변화 규모는 원전 출력 공백이 발전믹스 내 가스 비중으로 대체되는 경로와 직접 연결되며, 타 에너지원 흡수 가능성은 해당 공백 중 가스가 부담할 잔여 비중을 조정하는 역할을 한다. 영향 기간은 6개월이고 회복은 점진적이므로 2026년 한국 가스 발전 비중에 한정해 상향 조정하되, 흡수 가능성을 반영해 보수적인 연간 비중 상승으로 제안한다.",
      "values": [
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.3,
          "rationale": "선택된 좌표는 한국의 2026년 가스 발전 비중으로, 현재 기준값 0.285에 원전 출력 공백의 가스 대체분을 반영했다. 3~5GW 차질이 6개월 지속되고 타 에너지원이 50%를 흡수하는 조건을 연간 발전믹스 기준의 보수적 상승폭으로 환산해 약 1.5%p를 더한 최종 입력값 0.300으로 제안한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 54,
  "scenario_id": 294,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:05.030 | 5.030 | 2189 | 114 | 2303 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:05.025 | 5.025 | 5469 | 243 | 5712 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:32.886 | 32.886 | 7103 | 776 | 7879 |

### event_type_l2_id=9 재생에너지

#### Scenario Group

```json
{
  "description": "이 시나리오 그룹은 유럽의 풍력·수력 출력 약세와 조기 폭염이 전력수요를 통해 가스발전 호출을 얼마나 키우고, 그 결과 TTF와 LNG 유입 필요성에 어떤 압력을 줄 수 있는지 비교하기 위한 것이다. 분기 축은 영향 기간(1개월 이하, 3개월, 6개월, 종료 미정), 수요·용량 변화 규모(단발 ±20% 이내·±20~50%·±50% 초과, 구조적 ±1GW 이상), 대체 전원의 흡수율(100%, 50%, 0%)이다. 시장 반응보다 수급 민감도 차이를 보여주는 메타 비교에 초점을 둔다.",
  "dimension_selected": [
    "affected_period",
    "capacity_change_scale",
    "alt_energy_absorption"
  ],
  "event_type": {
    "event_type_l1_id": 2,
    "event_type_l2_id": 9,
    "level_1_code": "demand",
    "level_1_label": "수요",
    "level_2_code": "renewable_energy",
    "level_2_label": "재생에너지"
  },
  "event_type_l2_id": 9,
  "mi_event_id": 1348,
  "request_usr_id": 1000085,
  "scenario_count": 6,
  "scenario_group_id": 44,
  "stage": "signpost_created",
  "status": "creating",
  "summary": "[유럽 재생에너지] 풍력·수력 약세와 폭염 변수 → 가스발전 대체수요 지지",
  "title": "유럽 재생에너지 약세발 가스발전·LNG 수요 시나리오"
}
```

#### Dimension Template

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
      "점진",
      "없음 (Capa 증가 시)"
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
      "없음 (회복 불가)"
    ]
  }
]
```

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": null,
      "comment": "동절기 둔켈플라우테/하절기 열파 풍력 약화",
      "dimension_key": "affected_period",
      "dimension_label": "영향 기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 261,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3개월",
          "scenario_id": 262,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "석탄·원전 등 흡수",
      "dimension_key": "alt_energy_absorption",
      "dimension_label": "타 에너지원 흡수 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 261,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 262,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "재생 출력 변동→가스 비중 대체(재생 전용 input 없음)",
      "dimension_key": "capacity_change_scale",
      "dimension_label": "Capacity 변화 규모",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1 GW 미만",
          "scenario_id": 261,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "1~3 GW",
          "scenario_id": 262,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "발전 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영",
      "dimension_key": "capacity_change_scale",
      "dimension_label": "Capacity 변화 규모",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1 GW 미만",
          "scenario_id": 261,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "1~3 GW",
          "scenario_id": 262,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격(무풍)/점진(정책 phase-out)",
      "dimension_key": "onset_pattern",
      "dimension_label": "발생 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 261,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 262,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "급격(기상)/점진(COD)",
      "dimension_key": "recovery_pattern",
      "dimension_label": "회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 261,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 262,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "단발(기상)/구조적(신규 Farm·정책)",
      "dimension_key": "structural_change_yn",
      "dimension_label": "구조적 변동 여부",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 261,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 262,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 9,
  "mapping_count": 7,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-21T00:31:52.787121",
  "detail_analysis": "사건 요약:\n유럽에서 약한 풍황과 수력발전 감소가 EU 가스발전 증가의 배경으로 제시된 기존 Event임. 신규 연결 자료에서는 2026년 5월 28일 WoodMac weekly summary가 서유럽 조기 폭염을 단기 수급 변동 요인으로 언급함. 2026년 6월 19일 Platts Daily Report는 EU 저장률 45.56%, 7월 프롬프트 타이트, 8월 이후 대서양 복귀 물량 기대를 함께 제시함.\n\n영향 경로:\n풍력과 수력 발전 약세는 전력 믹스에서 가스발전 가동률을 높이는 경로로 작용함. 서유럽 조기 폭염은 냉방 전력수요를 통해 재생에너지 출력 부족 시 가스발전 대체수요를 확대할 수 있는 추가 Fundamental 변수임. 다만 신규 Record의 중심은 중동 리스크, 저장률, LNG 물량 복귀 등 복합 가스·LNG 시장 변수이며, 재생에너지 약세 자체에 대한 신규 정량 수치는 제한적임.\n\n시장 반응:\n2026년 5월 28일 WoodMac은 중동 긴장 완화 가능성으로 TTF 6월물 US$15.8/mmbtu와 동북아 DES 7월물 US$18.4/mmbtu가 하락했다고 제시함. 2026년 6월 19일 Platts는 JKM이 5거래일 하락을 끊고 4.4% 반등했다고 제시함. 같은 Platts 자료는 EU 저장률 45.56%와 7월 프롬프트 타이트에도 8월 이후 대서양 복귀 물량 기대가 NWE/TTF 할인 확대를 이끌었다고 설명함.\n\nLNG 시장 관점:\n이번 Event는 LNG 설비 자체 문제가 아니라 유럽 전력 믹스와 날씨를 통한 gas demand driver임. 재생에너지 출력 약세와 폭염성 전력수요는 유럽 가스발전 수요와 LNG 유입 필요성을 지지할 수 있음. 다만 신규 연결 Record에는 중동 긴장, 호르무즈 통항 제한, 미국 LNG 유지보수, 대서양 물량 복귀 등 별도 Event 성격의 요인이 함께 포함되어 있어 Event 경계상 재생에너지·전력수요 영향으로 범위를 제한함.",
  "event_title_ko": "유럽 재생에너지 약세와 가스발전 수요",
  "event_type_l2_id": 9,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-19T00:00:00",
  "mi_event_id": "1348",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[유럽 재생에너지] 풍력·수력 약세와 폭염 변수 → 가스발전 대체수요 지지",
  "source_mi_record_ids": [
    2235,
    2236,
    3315
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [261, 262]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=261 대체 전원이 흡수한 단기 가스발전 지지

- 소요시간: 01:27.265 (87.265s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "affected_period": "1개월 이하",
    "alt_energy_absorption": "100%",
    "capacity_change_scale": "1 GW 미만"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "neutral",
    "ttf": "mild_bull"
  },
  "narrative": "영향은 1개월 이하에 머물고, 풍력·수력 부진에 따른 발전 여건 변화도 단발적이며 20% 이내로 제한되는 그림이다.\n폭염이 일부 냉방 수요를 키우더라도 원전, 석탄, 수입전력 등 다른 전원이 전부 흡수하면서 가스발전 추가 호출은 짧게 끝난다.\n트레이더는 유럽 현물 프리미엄을 크게 쫓기보다 저장률과 기상 예보의 정상화 여부를 확인하는 방어적 대응에 그친다.\n아시아 LNG 시장과 미국 내 수급으로 전이될 여지는 작아, 가격 반응은 유럽 허브의 제한적 변동에 집중된다.",
  "probability_delta": 0.0,
  "probability_score": 33.0,
  "scenario_group_id": 44,
  "scenario_id": 261,
  "status": "created",
  "title": "대체 전원이 흡수한 단기 가스발전 지지"
}
```

##### Validation Summary

- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 7 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=7, basecaseValue_present=7 | PASS |
| Step2 slot axis value 수 | `{"parameter|9|demand|powermixadjustment|powermix": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 7 | Capacity 변화 규모가 1GW 미만으로 제한되어 재생 출력 약세가 발전 믹스의 가스 비중에 미치는 직접 충격은 작고, 타 에너지원 흡수 가능성이 100%로 제시되어 원전·석탄·수입전력 등이 추가 전력수요를 흡수하는 구조입니다. 영향 기간도 1개월 이하의 공통 맥락이므로 연간 발전원 비중 입력에서는 유럽 주요국의 가스 비중을 기준값 유지로 제안합니다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.19 | Belgium의 2026년 Gas 발전 비중 슬롯은 선택된 유럽 가스 발전 믹스 대상이며, 1개월 이하의 단기 영향과 100% 대체 전원 흡수 조건 때문에 연간 가스 비중을 기준값 0.19에서 조정하지 않고 0.19로 유지합니다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.042 | France의 2026년 Gas 발전 비중 슬롯은 선택된 유럽 가스 발전 믹스 대상이며, 원전 등 대체 전원이 추가 수요를 흡수하는 시나리오이므로 연간 가스 비중을 기준값 0.042에서 조정하지 않고 0.042로 유지합니다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.135 | Germany의 2026년 Gas 발전 비중 슬롯은 재생에너지 약세 영향이 나타날 수 있는 직접 대상이지만, 변화 규모가 1GW 미만이고 대체 전원 흡수율이 100%이므로 연간 가스 비중을 기준값 0.135에서 조정하지 않고 0.135로 유지합니다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.434 | Italy의 2026년 Gas 발전 비중 슬롯은 선택된 유럽 가스 발전 믹스 대상이나, 단기 폭염·재생 출력 약세가 다른 전원으로 흡수되는 설정이므로 연간 가스 비중을 기준값 0.434에서 조정하지 않고 0.434로 유지합니다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.31818965517241377 | Netherlands의 2026년 Gas 발전 비중 슬롯은 유럽 현물 프리미엄에 민감할 수 있는 대상이지만, 추가 가스발전 호출이 짧고 대체 전원이 전부 흡수하는 조건이므로 연간 가스 비중을 기준값 0.31818965517241377에서 조정하지 않고 0.31818965517241377로 유지합니다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.213 | Spain의 2026년 Gas 발전 비중 슬롯은 재생·수력 변동의 영향 대상에 포함되지만, 변화 규모가 작고 1개월 이하로 제한되며 대체 전원 흡수가 100%로 설정되어 연간 가스 비중을 기준값 0.213에서 조정하지 않고 0.213으로 유지합니다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.29 | United Kingdom의 2026년 Gas 발전 비중 슬롯은 선택된 서유럽 가스 발전 믹스 대상이나, 단기적 재생 약세가 다른 전원으로 흡수되는 시나리오이므로 연간 가스 비중을 기준값 0.29에서 조정하지 않고 0.29로 유지합니다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1348,
  "model_param_proposal_id": 44,
  "proposal_completed_dtm": "2026-07-07 17:32:02.625923",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Energy Source",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "Capacity 변화 규모가 1GW 미만으로 제한되어 재생 출력 약세가 발전 믹스의 가스 비중에 미치는 직접 충격은 작고, 타 에너지원 흡수 가능성이 100%로 제시되어 원전·석탄·수입전력 등이 추가 전력수요를 흡수하는 구조입니다. 영향 기간도 1개월 이하의 공통 맥락이므로 연간 발전원 비중 입력에서는 유럽 주요국의 가스 비중을 기준값 유지로 제안합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19,
          "rationale": "Belgium의 2026년 Gas 발전 비중 슬롯은 선택된 유럽 가스 발전 믹스 대상이며, 1개월 이하의 단기 영향과 100% 대체 전원 흡수 조건 때문에 연간 가스 비중을 기준값 0.19에서 조정하지 않고 0.19로 유지합니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "France의 2026년 Gas 발전 비중 슬롯은 선택된 유럽 가스 발전 믹스 대상이며, 원전 등 대체 전원이 추가 수요를 흡수하는 시나리오이므로 연간 가스 비중을 기준값 0.042에서 조정하지 않고 0.042로 유지합니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.135,
          "rationale": "Germany의 2026년 Gas 발전 비중 슬롯은 재생에너지 약세 영향이 나타날 수 있는 직접 대상이지만, 변화 규모가 1GW 미만이고 대체 전원 흡수율이 100%이므로 연간 가스 비중을 기준값 0.135에서 조정하지 않고 0.135로 유지합니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.434,
          "rationale": "Italy의 2026년 Gas 발전 비중 슬롯은 선택된 유럽 가스 발전 믹스 대상이나, 단기 폭염·재생 출력 약세가 다른 전원으로 흡수되는 설정이므로 연간 가스 비중을 기준값 0.434에서 조정하지 않고 0.434로 유지합니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.31818965517241377,
          "rationale": "Netherlands의 2026년 Gas 발전 비중 슬롯은 유럽 현물 프리미엄에 민감할 수 있는 대상이지만, 추가 가스발전 호출이 짧고 대체 전원이 전부 흡수하는 조건이므로 연간 가스 비중을 기준값 0.31818965517241377에서 조정하지 않고 0.31818965517241377로 유지합니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.213,
          "rationale": "Spain의 2026년 Gas 발전 비중 슬롯은 재생·수력 변동의 영향 대상에 포함되지만, 변화 규모가 작고 1개월 이하로 제한되며 대체 전원 흡수가 100%로 설정되어 연간 가스 비중을 기준값 0.213에서 조정하지 않고 0.213으로 유지합니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29,
          "rationale": "United Kingdom의 2026년 Gas 발전 비중 슬롯은 선택된 서유럽 가스 발전 믹스 대상이나, 단기적 재생 약세가 다른 전원으로 흡수되는 시나리오이므로 연간 가스 비중을 기준값 0.29에서 조정하지 않고 0.29로 유지합니다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 44,
  "scenario_id": 261,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.735 | 3.735 | 2579 | 113 | 2692 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:12.562 | 12.562 | 5473 | 895 | 6368 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:40.917 | 40.917 | 7337 | 1280 | 8617 |

#### scenario_id=262 석 달간 절반만 흡수되는 유럽 가스발전 수요

- 소요시간: 01:31.142 (91.142s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "affected_period": "3개월",
    "alt_energy_absorption": "50%",
    "capacity_change_scale": "1~3 GW"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "bull"
  },
  "narrative": "약한 풍황과 수력 감소가 3개월가량 이어지고, 단발적 발전 여건 변화가 20~50% 범위로 커지는 상황이다.\n다른 전원이 절반은 메워 주지만 남은 공백은 가스발전이 담당해 유럽 전력 부문 가스 소각량이 평년보다 높아진다.\n저장 재고가 충분하면 급등은 제한되지만, 냉방 수요가 겹치는 날에는 TTF 단기물과 전력 스파크 스프레드가 민감하게 반응한다.\n유럽의 LNG 구매가 조금 늘면서 JKM도 일부 지지를 받지만, 미국 가격으로의 파급은 수출 가동률 변화가 확인될 때만 제한적으로 나타난다.",
  "probability_delta": 0.0,
  "probability_score": 19.0,
  "scenario_group_id": 44,
  "scenario_id": 262,
  "status": "created",
  "title": "석 달간 절반만 흡수되는 유럽 가스발전 수요"
}
```

##### Validation Summary

- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 7 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=7, basecaseValue_present=7 | PASS |
| Step2 slot axis value 수 | `{"parameter|9|demand|powermixadjustment|powermix": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 7 | Capacity 변화 규모는 재생 출력 약세가 가스발전 비중으로 대체되는 경로와 직접 연결되며, 타 에너지원 흡수 가능성은 석탄·원전 등 다른 전원이 충격의 절반을 흡수해 가스 비중 상승폭을 제한한다는 의미로 반영했다. 영향 기간이 3개월로 제한되어 연간 PowerMix 입력에는 2026년 가스 발전 비중을 소폭 상향하는 구조로 제안하며, 각 국가는 기존 가스 비중을 기준으로 동일한 보수적 상대 강도를 적용했다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.19475 | 해당 좌표의 기준 가스 발전 비중 0.19에 대해, 3개월간 재생 출력 약세 중 절반만 가스가 담당하는 보수적 연간화 효과를 반영해 2.5% 상대 상향하여 0.19475로 산정했다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.04305 | 해당 좌표의 기준 가스 발전 비중 0.042에 대해, 3개월 영향과 50% 타 전원 흡수를 감안한 제한적 가스 대체 효과를 2.5% 상대 상향으로 반영해 0.04305로 산정했다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.138375 | 해당 좌표의 기준 가스 발전 비중 0.135에 대해, 풍력·수력 약세로 인한 잔여 전력 공백을 가스가 일부 메우는 효과를 3개월 연간화 및 50% 흡수 조건으로 제한해 2.5% 상대 상향한 0.138375로 산정했다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.44485 | 해당 좌표의 기준 가스 발전 비중 0.434에 대해, 가스발전이 재생 출력 약세의 잔여분을 담당하는 시나리오를 반영하되 기간과 대체 전원 흡수율을 감안해 2.5% 상대 상향하여 0.44485로 산정했다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.3261443965517241 | 해당 좌표의 기준 가스 발전 비중 0.31818965517241377에 대해, 3개월 동안의 제한적 가스발전 호출 증가를 연간 PowerMix에 반영하기 위해 2.5% 상대 상향하여 0.3261443965517241로 산정했다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.218325 | 해당 좌표의 기준 가스 발전 비중 0.213에 대해, 재생 출력 약세와 냉방 수요가 겹치는 기간의 가스 대체 수요를 반영하되 절반은 타 전원이 흡수하는 조건을 적용해 2.5% 상대 상향한 0.218325로 산정했다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.29725 | 해당 좌표의 기준 가스 발전 비중 0.29에 대해, 3개월간 풍황 약세에 따른 가스발전 보강 효과를 연간 비중으로 환산하고 50% 타 전원 흡수를 반영해 2.5% 상대 상향한 0.29725로 산정했다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1348,
  "model_param_proposal_id": 45,
  "proposal_completed_dtm": "2026-07-07 17:32:20.465312",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Energy Source",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "Capacity 변화 규모는 재생 출력 약세가 가스발전 비중으로 대체되는 경로와 직접 연결되며, 타 에너지원 흡수 가능성은 석탄·원전 등 다른 전원이 충격의 절반을 흡수해 가스 비중 상승폭을 제한한다는 의미로 반영했다. 영향 기간이 3개월로 제한되어 연간 PowerMix 입력에는 2026년 가스 발전 비중을 소폭 상향하는 구조로 제안하며, 각 국가는 기존 가스 비중을 기준으로 동일한 보수적 상대 강도를 적용했다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19475,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.19에 대해, 3개월간 재생 출력 약세 중 절반만 가스가 담당하는 보수적 연간화 효과를 반영해 2.5% 상대 상향하여 0.19475로 산정했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04305,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.042에 대해, 3개월 영향과 50% 타 전원 흡수를 감안한 제한적 가스 대체 효과를 2.5% 상대 상향으로 반영해 0.04305로 산정했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.138375,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.135에 대해, 풍력·수력 약세로 인한 잔여 전력 공백을 가스가 일부 메우는 효과를 3개월 연간화 및 50% 흡수 조건으로 제한해 2.5% 상대 상향한 0.138375로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.44485,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.434에 대해, 가스발전이 재생 출력 약세의 잔여분을 담당하는 시나리오를 반영하되 기간과 대체 전원 흡수율을 감안해 2.5% 상대 상향하여 0.44485로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3261443965517241,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.31818965517241377에 대해, 3개월 동안의 제한적 가스발전 호출 증가를 연간 PowerMix에 반영하기 위해 2.5% 상대 상향하여 0.3261443965517241로 산정했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.218325,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.213에 대해, 재생 출력 약세와 냉방 수요가 겹치는 기간의 가스 대체 수요를 반영하되 절반은 타 전원이 흡수하는 조건을 적용해 2.5% 상대 상향한 0.218325로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29725,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.29에 대해, 3개월간 풍황 약세에 따른 가스발전 보강 효과를 연간 비중으로 환산하고 50% 타 전원 흡수를 반영해 2.5% 상대 상향한 0.29725로 산정했다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 44,
  "scenario_id": 262,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.390 | 3.390 | 2587 | 115 | 2702 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:09.167 | 9.167 | 5478 | 717 | 6195 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:54.522 | 54.522 | 7342 | 2061 | 9403 |

### event_type_l2_id=10 석탄 발전

#### Scenario Group

```json
{
  "description": "본 그룹은 Tohoku Electric Haramachi 1·2호기 정지 이후 재가동 불확실성이 일본 전력 믹스와 LNG 발전용 수요로 전이되는 범위를 점검한다. 시나리오는 차질 기간(1개월 이하, 6개월, 1년 초과, 종료 미정), 대체 연료(석탄·석유·암모니아), 상대 가격 또는 공급 변화, 대체 흡수율(0·50·100%)을 축으로 구성했다. 단기 복구와 석탄 경쟁력 회복 시 LNG 수요는 제한되지만, 장기·미정 정지와 석유·암모니아 대체 한계가 겹치면 보강 매수 필요",
  "dimension_selected": [
    "affected_period",
    "structural_change_yn",
    "alt_energy_absorption"
  ],
  "event_type": {
    "event_type_l1_id": 2,
    "event_type_l2_id": 10,
    "level_1_code": "demand",
    "level_1_label": "수요",
    "level_2_code": "coal_power",
    "level_2_label": "석탄 발전"
  },
  "event_type_l2_id": 10,
  "mi_event_id": 1156,
  "request_usr_id": 1000085,
  "scenario_count": 6,
  "scenario_group_id": 45,
  "stage": "completed",
  "status": "created",
  "summary": "[일본 전력 믹스] Haramachi 추가 변경 미확인 → LNG 대체수요 변수 지속",
  "title": "Haramachi 석탄발전 차질에 따른 일본 LNG 대체수요"
}
```

#### Dimension Template

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
    "dim_key": "lng_demand_impact_intensity",
    "display_order": 2,
    "label": "LNG 수요 영향 강도",
    "required": true,
    "value_enums": [
      "소폭",
      "중간",
      "대폭"
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
  }
]
```

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": null,
      "comment": "단발(가격)/중기(계약)/장기(정책)",
      "dimension_key": "affected_period",
      "dimension_label": "영향 기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 267,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "6개월",
          "scenario_id": 268,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "원전·재생E 등 흡수",
      "dimension_key": "alt_energy_absorption",
      "dimension_label": "타 에너지원 흡수 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 267,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 268,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "Coal Futures Price",
      "comment": "가격기반 석탄↔가스 스위칭(Asia=Newcastle/JKM, EU=ARA/TTF) : 지역별 기준 가격쌍을 사용해 석탄-가스 전환 유인을 판단하고, 단기 가격 이벤트는 CoalGasAdjustment를 우선 사용",
      "dimension_key": "lng_demand_impact_intensity",
      "dimension_label": "LNG 수요 영향 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "CoalGasAdjustment",
        "model_table": "table1",
        "semantic_axes": "석탄 선물가격 strip — 지역·월 (Asia=Newcastle, EU=ARA)"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 267,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 268,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "Gas Futures Price",
      "comment": "가격기반 석탄↔가스 스위칭(Asia=Newcastle/JKM, EU=ARA/TTF) : 지역별 기준 가격쌍을 사용해 석탄-가스 전환 유인을 판단하고, 단기 가격 이벤트는 CoalGasAdjustment를 우선 사용",
      "dimension_key": "lng_demand_impact_intensity",
      "dimension_label": "LNG 수요 영향 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "CoalGasAdjustment",
        "model_table": "table2",
        "semantic_axes": "가스 선물가격 strip — 지역·월 (Asia=JKM, EU=TTF)"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 267,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 268,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "구조적 비중 변화(정책·폐쇄) : 정책·폐쇄·설비 변화처럼 구조적 전환이면 PowerMix에서 Gas/Coal 비중을 연 단위로 조정",
      "dimension_key": "lng_demand_impact_intensity",
      "dimension_label": "LNG 수요 영향 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 267,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 268,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "단발(가격→CoalGas)/구조적(정책→PowerMix) 결정",
      "dimension_key": "structural_change_yn",
      "dimension_label": "구조적 변동 여부",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "단발적",
          "scenario_id": 267,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "구조적",
          "scenario_id": 268,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 10,
  "mapping_count": 6,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:18:59.776386",
  "detail_analysis": "사건 요약:\nTohoku Electric의 Haramachi 석탄발전소 1호기와 2호기 각 1 GW가 고장 정지 후 재가동 계획을 제시한 상태임. 신규 연결된 2026-06-19 Platts Daily Report는 Haramachi 설비의 추가 상태 변경이나 재가동 일정 변경을 제시하지 않음. 따라서 본 Event의 핵심은 일본 석탄발전 설비 가동 차질과 그에 따른 대체 발전연료 수요 변수로 유지됨.\n\n영향 경로:\n석탄발전 가동 차질은 일본 전력 공급 믹스에서 기저 발전 출력 감소로 연결될 수 있음. 부족 전력을 가스발전이 일부 대체할 경우 발전용 LNG 소모 증가 경로가 형성됨. 2026-06-19 Platts Daily Report에 언급된 미국·이란 평화협상 지연, 호르무즈 정상화 불확실성, EU 저장률 45.56%, 8월 이후 대서양 복귀 물량 기대는 광범위한 LNG 시장 배경이며 Haramachi 사건의 직접 원인은 아님.\n\n시장 반응:\nHaramachi 차질 자체에 대한 직접 LNG 가격 수치나 JKM 변동 수치는 신규 Record에서 제시되지 않음. 다만 2026-06-19 Platts Daily Report는 미국·이란 평화협상 지연과 호르무즈 정상화 불확실성 속에 JKM이 5거래일 하락을 끊고 4.4% 반등했다고 언급함. 유럽에서는 EU 저장률 45.56%와 7월 프롬프트 타이트에도 8월 이후 대서양 복귀 물량 기대가 NWE/TTF 할인 확대를 이끈 것으로 제시됨.\n\nLNG 시장 관점:\n해당 Event는 LNG 설비나 계약 사건이 아니라 석탄발전 가동 차질을 통한 간접 수요 변수임. 일본 내 가스발전 대체 가동 여부와 실제 현물 LNG 조달 증가 여부가 핵심 후속 확인 사항임. 신규 Record의 JKM 4.4% 반등과 NWE/TTF 할인 확대는 시장 배경으로 반영하되, Event 제목과 경계는 Haramachi 석탄발전소 가동 차질로 유지함.",
  "event_title_ko": "Haramachi 석탄발전소 가동 차질",
  "event_type_l2_id": 10,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-19T00:00:00",
  "mi_event_id": "1156",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[일본 전력 믹스] Haramachi 추가 변경 미확인 → LNG 대체수요 변수 지속",
  "source_mi_record_ids": [
    2271,
    3315
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [267, 268]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=267 단기 복구와 석탄 경쟁력으로 LNG 대체수요 소멸

- 소요시간: 01:34.248 (94.248s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "affected_period": "1개월 이하",
    "alt_energy_absorption": "100%",
    "structural_change_yn": "단발적"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bear",
    "ttf": "neutral"
  },
  "narrative": "Haramachi 1·2호기의 차질은 한 달 이내로 제한되고, 석탄은 LNG보다 뚜렷하게 저렴해진 상황으로 본다.\n전력사는 보수 기간의 부족분을 기존 석탄 운용과 다른 전원으로 모두 흡수할 수 있어 LNG 현물 조달을 서두를 유인이 낮다.",
  "probability_delta": 0.0,
  "probability_score": 35.0,
  "scenario_group_id": 45,
  "scenario_id": 267,
  "status": "created",
  "title": "단기 복구와 석탄 경쟁력으로 LNG 대체수요 소멸"
}
```

##### Validation Summary

- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 2 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"10|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 100%는 Haramachi 석탄발전 차질로 생길 수 있는 전력 부족분이 LNG 발전 비중 상승으로 전이되지 않는다는 의미이므로 발전원별 PowerMix 조정 대상과 연결된다. 영향 기간은 1개월 이하이고 구조적 변동도 단발적으로 제시되어 연간 발전 믹스의 구조적 재배분보다는 일본 2026년 가스 발전 비중을 기준 수준으로 유지하는 보수적 제안으로 반영한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.323 | 해당 좌표는 선택된 일본 2026년 가스 발전 비중이며 기준값은 0.323이다. 차질 기간이 1개월 이하이고 타 에너지원 흡수 가능성이 100%로 제시되어 LNG 발전 비중을 추가 상향할 필요가 없으므로 최종 입력값을 기준값과 동일한 0.323으로 둔다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1156,
  "model_param_proposal_id": 47,
  "proposal_completed_dtm": "2026-07-07 17:33:13.911084",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Energy Source",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "타 에너지원 흡수 가능성 100%는 Haramachi 석탄발전 차질로 생길 수 있는 전력 부족분이 LNG 발전 비중 상승으로 전이되지 않는다는 의미이므로 발전원별 PowerMix 조정 대상과 연결된다. 영향 기간은 1개월 이하이고 구조적 변동도 단발적으로 제시되어 연간 발전 믹스의 구조적 재배분보다는 일본 2026년 가스 발전 비중을 기준 수준으로 유지하는 보수적 제안으로 반영한다.",
      "values": [
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.323,
          "rationale": "해당 좌표는 선택된 일본 2026년 가스 발전 비중이며 기준값은 0.323이다. 차질 기간이 1개월 이하이고 타 에너지원 흡수 가능성이 100%로 제시되어 LNG 발전 비중을 추가 상향할 필요가 없으므로 최종 입력값을 기준값과 동일한 0.323으로 둔다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 45,
  "scenario_id": 267,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:14.399 | 14.399 | 2308 | 82 | 2390 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:27.125 | 27.125 | 5365 | 1182 | 6547 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:13.139 | 13.139 | 7036 | 802 | 7838 |

#### scenario_id=268 6개월 공백에 고가 석유 대체 한계, LNG 보강 매수 부상

- 소요시간: 01:04.946 (64.946s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "affected_period": "6개월",
    "alt_energy_absorption": "50%",
    "structural_change_yn": "구조적"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "bull",
    "ttf": "mild_bull"
  },
  "narrative": "가동 차질이 6개월가량 이어지는 가운데, 난방유·디젤·중유 계열 대체 연료는 LNG보다 비싸져 경제성이 떨어지는 국면이다.\n다른 전원이 절반가량은 부담하지만 남은 전력 공백은 가스화력 이용률 상승과 LNG 조달로 메워질 가능성이 크다.\n일본 유틸리티의 계절별 현물 보강 매수가 늘며 JKM은 민감하게 반응하고, 유럽은 아시아와의 화물 경쟁을 통해 완만한 상승 압력을 받는다.",
  "probability_delta": 0.0,
  "probability_score": 20.0,
  "scenario_group_id": 45,
  "scenario_id": 268,
  "status": "created",
  "title": "6개월 공백에 고가 석유 대체 한계, LNG 보강 매수 부상"
}
```

##### Validation Summary

- expected_parameters: `["PowerMix"]`
- selected_parameters: `["PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=57 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=6 | PASS |
| Step2 selected slot | 1 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"10|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 50%는 원전·재생 등 비가스 전원이 일부 전력 공백을 부담하되 잔여분은 가스발전으로 전환될 수 있음을 의미하므로, 국가·에너지원별 발전 비중인 PowerMix 조정과 직접 연결된다. 구조적 변동으로 분류되어 단순 단기 가격 반응보다 전원 믹스 반영이 적절하며, 영향 기간은 6개월이므로 2026년 일본 Gas 비중에 한정해 보수적으로 상향한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.3265 | 해당 좌표는 2026년 일본 Gas 발전 비중 기준값이 존재하고 Haramachi 석탄발전 차질의 직접 영향 대상이다. 기준값 0.323에 대해 2GW급 석탄 설비의 6개월 공백 중 타 에너지원이 50% 흡수하고 남는 전력 공백을 가스발전이 보완한다고 보아, 연간 발전 믹스 기준 약 0.0035p를 가산한 최종 입력값 0.3265를 적용한다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1156,
  "model_param_proposal_id": 46,
  "proposal_completed_dtm": "2026-07-07 17:32:53.106317",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Energy Source",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "타 에너지원 흡수 가능성 50%는 원전·재생 등 비가스 전원이 일부 전력 공백을 부담하되 잔여분은 가스발전으로 전환될 수 있음을 의미하므로, 국가·에너지원별 발전 비중인 PowerMix 조정과 직접 연결된다. 구조적 변동으로 분류되어 단순 단기 가격 반응보다 전원 믹스 반영이 적절하며, 영향 기간은 6개월이므로 2026년 일본 Gas 비중에 한정해 보수적으로 상향한다.",
      "values": [
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.3265,
          "rationale": "해당 좌표는 2026년 일본 Gas 발전 비중 기준값이 존재하고 Haramachi 석탄발전 차질의 직접 영향 대상이다. 기준값 0.323에 대해 2GW급 석탄 설비의 6개월 공백 중 타 에너지원이 50% 흡수하고 남는 전력 공백을 가스발전이 보완한다고 보아, 연간 발전 믹스 기준 약 0.0035p를 가산한 최종 입력값 0.3265를 적용한다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 45,
  "scenario_id": 268,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:14.383 | 14.383 | 2364 | 101 | 2465 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:06.021 | 6.021 | 5418 | 280 | 5698 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:13.523 | 13.523 | 7051 | 798 | 7849 |

### event_type_l2_id=11 자연재해

#### Scenario Group

```json
{
  "description": "affected_facility_type에 따라 생산 시설 차질과 수입 시설 차질 중 적절한 모델 파라미터를 선택하는지 검증한다.",
  "dimension_selected": [
    "period",
    "affected_facility_type",
    "supply_disruption_intensity",
    "supply_disruption_pattern",
    "alt_lng_supply_availability"
  ],
  "event_type": {
    "event_type_l1_id": 1,
    "event_type_l2_id": 11,
    "level_1_code": "supply",
    "level_1_label": "공급",
    "level_2_code": "natural_disaster",
    "level_2_label": "자연재해"
  },
  "event_type_l2_id": 11,
  "mi_event_id": 1245,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 47,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent routing 검증용 자연재해 scenario_group",
  "title": "[model_parameter_agent_test] 자연재해 routing 검증"
}
```

#### Dimension Template

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
    "dim_key": "affected_facility_type",
    "display_order": 2,
    "label": "영향 시설 유형",
    "required": true,
    "value_enums": [
      "생산 시설",
      "수입 시설",
      "수출 시설"
    ]
  },
  {
    "dim_key": "supply_disruption_intensity",
    "display_order": 3,
    "label": "공급 차질 강도",
    "required": true,
    "value_enums": [
      "전혀 없음",
      "낮음",
      "중간",
      "높음",
      "매우 높음"
    ]
  },
  {
    "dim_key": "supply_disruption_pattern",
    "display_order": 4,
    "label": "공급 차질 - 발생/회복 패턴",
    "required": false,
    "value_enums": [
      "급차질-급회복",
      "급손상-단기수리",
      "급손상-장기재건",
      "영구 손실",
      "지연발생-단계적 회복",
      "지연발생-즉시 해소",
      "점진차질-단계적 회복",
      "점진차질-즉시 해소",
      "즉시발생-장기 잠식"
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

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": null,
      "comment": "수입(재기화) 시설 피해 시 : RegasAdjustment는 현재 수급모델 파라미터 제안 대상에서 제외",
      "dimension_key": "affected_facility_type",
      "dimension_label": "영향 시설 유형",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "생산 시설",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "수입 시설",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "HurricaneIntensity",
      "comment": "美 액화시설 허리케인 — [1-4] 강도 : 미국 Gulf Coast 액화시설이 허리케인 영향권이고 강도 단계로 차질을 설명할 수 있으면 HurricaneIntensity 선택. 실제 설비별 outage 비율이 명확하면 LiqUtilAdjustment/LiqProdAdjustment로 보완 판단",
      "dimension_key": "affected_facility_type",
      "dimension_label": "영향 시설 유형",
      "mapping_method": "routing",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "{USA}Hurricanes",
        "model_table": "table1",
        "semantic_axes": "美 액화시설 허리케인 차질 — 연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "생산 시설",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "수입 시설",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqProdAdjustment",
      "comment": "수출(액화) 시설 피해 시 : 액화설비의 장기·영구 손상, 설비 폐쇄, 복구 지연 등으로 생산 가능량 자체를 낮춰야 하면 LiqProdAdjustment 선택. 단기 이용률 조정보다 구조적 생산량 감소가 명확한 경우에 사용",
      "dimension_key": "affected_facility_type",
      "dimension_label": "영향 시설 유형",
      "mapping_method": "routing",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqProdAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 생산량 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "생산 시설",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "수입 시설",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "수출(액화) 시설 피해 시 : 기존 액화 Plant/Train의 단기·부분 가동 차질이면 LiqUtilAdjustment 선택. 설비 용량은 유지되지만 정전·침수·정비·운영 제약으로 이용률이 낮아지는 경우에 사용",
      "dimension_key": "affected_facility_type",
      "dimension_label": "영향 시설 유형",
      "mapping_method": "routing",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "생산 시설",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "수입 시설",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "SupplyDisruption",
      "comment": "생산 시설 피해 시 : 생산시설 피해면 해당 국가·basin의 SupplyDisruption을 선택하고, 피해 강도는 별도 강도 dimension으로 산정",
      "dimension_key": "affected_facility_type",
      "dimension_label": "영향 시설 유형",
      "mapping_method": "routing",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "VolumeAdjustment",
        "model_table": "table2",
        "semantic_axes": "Upstream 공급량 override — Country·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "생산 시설",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "수입 시설",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "타 공급국 상향으로 상쇄 : 피해로 감소한 LNG 공급량 중 대체 가능한 물량만 시장연결 공급국의 가용 액화설비에 배분",
      "dimension_key": "alt_lng_supply_availability",
      "dimension_label": "대체 LNG 공급 가능성",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "50%",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "시간축",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "3개월",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "6개월",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "시설 가동률 감소율로 변환 — 강도가 값 크기 결정 : routing으로 선택된 시설·파라미터의 감소율 또는 감소량을 결정하며, 강도 단계에 따라 조정폭을 차등 적용",
      "dimension_key": "supply_disruption_intensity",
      "dimension_label": "공급 차질 강도",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "높음",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "Ref. 공급 차질 패턴 — 시계열 형태",
      "dimension_key": "supply_disruption_pattern",
      "dimension_label": "공급 차질 - 발생/회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "급손상-단기수리",
          "scenario_id": 279,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "급손상-장기재건",
          "scenario_id": 280,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 11,
  "mapping_count": 9,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-21T00:05:12.294804",
  "detail_analysis": "사건 요약:\n호주 서부 LNG 공급 차질 Event는 기존 Cyclone Narelle 관련 설비 셧다운 리스크에서 최신 배치의 호주 서부 44 mmtpa 차질 및 Wheatstone 차질 언급으로 업데이트됨. 2026년 4월 2일 WoodMac은 호주 서부 44 mmtpa 차질이 중동 생산 중단과 함께 글로벌 가스·LNG 공급을 조이는 요인이라고 제시함. 2026년 4월 9일 WoodMac은 Wheatstone 차질이 Arctic LNG-2 차질, 카타르·UAE 재가동 지연과 함께 가격 하방을 제한하는 요인이라고 언급함. 신규 Record는 Cyclone Narelle 자체의 추가 경로나 피해 확대를 확인하지 않으며, Event 경계는 호주 서부 LNG 설비 차질에 한정됨.\n\n영향 경로:\n호주 서부 LNG 설비 차질은 아시아향 LNG 물리 카고 가용성을 낮추는 공급 측 Fundamental 요인임. 직전 요약의 Cyclone Narelle 관련 일부 플랜트 셧다운 언급은 중국의 호주 LNG 물량 감소와 연결된 배경으로 유지됨. 신규 Record의 44 mmtpa 차질 및 Wheatstone 차질은 공급 여력을 추가로 제약하는 업데이트임. 다만 같은 Record에 포함된 호르무즈, 중동 생산 중단, Arctic LNG-2, 카타르·UAE 재가동 지연은 별도 공급 리스크이며 본 Event의 직접 범위는 호주 서부 LNG 차질임.\n\n시장 반응:\n가격 반응은 공급 차질의 강세요인과 수요 부진·지정학 완화의 약세요인이 병존하는 구도임. 2026년 4월 9일 WoodMac은 4월 7일 미·이란 2주 조건부 휴전으로 TTF 5월물 US$15.7/mmBtu, 동북아 DES 5월물 US$16.0/mmBtu까지 가격 하락함을 제시함. 같은 요약에서 Wheatstone 차질은 하방을 제한하는 요인으로 분류됨. 2026년 4월 14일 Platts Daily Report는 미국·이란 평화협상 기대와 동북아 수요 부진으로 JKM·NWE 동반 하락함을 제시하되, 호르무즈·중동 전쟁 불확실성, EU 저장률 29.54%, 동서 차익거래 개방 신호와 유럽·아시아 여름 카고 경쟁이 원월 리스크를 유지함을 언급함.\n\nLNG 시장 관점:\n호주 서부 LNG는 아시아 시장의 핵심 공급원이며 설비 차질은 단기 아시아 카고 가용성과 리스크 프리미엄에 직접 연결됨. 신규 Record 기준 가격 방향은 즉각적인 상승보다 하락폭 제한 및 원월 리스크 유지로 정리됨. 동북아 수요 부진과 미·이란 협상 기대가 스팟 가격을 낮추는 가운데, Wheatstone 등 호주 서부 차질은 공급 측 완충 여력을 약화시키는 요인임. 본 Event는 자연재해성 또는 기상·설비 차질에 따른 호주 서부 LNG 공급 부담에 초점을 두며, 중동 지정학 및 유럽 저장률은 시장 반응 설명을 위한 외부 변수로만 취급함.",
  "event_title_ko": "호주 서부 LNG 자연재해성 차질",
  "event_type_l2_id": 11,
  "key_bullets": [],
  "latest_record_first_created": "2026-04-14T00:00:00",
  "mi_event_id": "1245",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[호주 자연재해] 서부 44 mmtpa·Wheatstone 차질 지속 → LNG 하방 제한",
  "source_mi_record_ids": [
    2214,
    2229,
    2230
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [279, 280]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A, REVIEW
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=279 [model_parameter_agent_test] 생산 시설 피해

- 소요시간: 03:29.855 (209.855s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "affected_facility_type": "생산 시설",
    "alt_lng_supply_availability": "50%",
    "period": "3개월",
    "supply_disruption_intensity": "높음",
    "supply_disruption_pattern": "급손상-단기수리"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "중립"
  },
  "narrative": "호주 서부 LNG 자연재해가 생산 시설에 직접 피해를 주어 3개월 동안 액화 생산 차질이 크고 대체 LNG 공급은 절반만 가능하다.",
  "probability_delta": 5.0,
  "probability_score": 35.0,
  "scenario_group_id": 47,
  "scenario_id": 279,
  "status": "created",
  "title": "[model_parameter_agent_test] 생산 시설 피해"
}
```

##### Validation Summary

- expected_parameters: `["SupplyDisruption", "LiqProdAdjustment", "LiqUtilAdjustment"]`
- selected_parameters: `["SupplyDisruption", "LiqProdAdjustment", "LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: REVIEW
- routing_messages: `["routing 후보가 모두 selected입니다. DB scenario dimension에 따른 선택/제외 사유 검토가 필요합니다."]`
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=11|affectedfacilitytype|supplydisruption|supply|volumeadjustment, sheet=VolumeAdjustment", "basecase record를 추출하지 못했습니다: candidate_key=11|affectedfacilitytype|liqprodadjustment|supply|liqprodadjustment, sheet=LiqProdAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=5, validated=3, final_selected=3, proposalParameters=3 | REVIEW |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 30 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=12, basecaseValue_present=6 | PASS |
| Step2 slot axis value 수 | `{"11|altlngsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 3 | 영향 시설 유형이 생산 시설로 지정되어 호주 생산 차질을 국가 단위 공급 차질 입력인 SupplyDisruption에 반영하는 것이 적절하다. 기간은 3개월이며 급손상-단기수리 패턴이므로 초기 2개월은 높은 차질을 유지하고 마지막 달은 수리 진행에 따른 부분 회복을 반영한 절대 Bcm 값으로 제안한다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 3 | 영향 시설 유형이 생산 시설이고 이벤트에서 Wheatstone 차질이 명시되어 있어 액화 생산 가능량 자체를 낮추는 LiqProdAdjustment가 선택된다. 3개월 단기 수리 기간 동안 Wheatstone 생산량을 보수적으로 하향 override하되, 명확한 기준 생산량이 없으므로 피해 기간의 직접 대상 설비에 대해 절대 생산량 하한을 적용한다. |
| 3 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 6 | 대체 LNG 공급 가능성이 50%로 주어져 피해 물량의 일부를 시장 연결 대체 공급국의 액화설비 가동률 상향으로 흡수하는 LiqUtilAdjustment가 직접 연결된다. 기간은 3개월이며, 기준 가동률에서 명확한 상향 여력이 있고 0~1 가동률 제약에 맞출 수 있는 대체 공급 설비를 우선적으로 1.0까지 상향한다. |

##### Proposed Parameter Values

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "Month": 7, "Year": 2026}` | null | 4.99 | 2026년 7월 호주 생산 차질 첫 달로, 이벤트의 서부 호주 44 mmtpa 차질을 월 단위 LNG 물량으로 나눈 뒤 가스 부피 기준으로 환산해 약 4.99 Bcm의 절대 차질 물량을 적용했다. |
| 2 | `{"Country": "Australia", "Month": 8, "Year": 2026}` | null | 4.99 | 2026년 8월은 3개월 차질 기간 중 복구 전 높은 차질이 지속되는 달로 보아, 7월과 동일하게 44 mmtpa 차질의 월간 환산치인 약 4.99 Bcm를 적용했다. |
| 3 | `{"Country": "Australia", "Month": 9, "Year": 2026}` | null | 2.5 | 2026년 9월은 급손상-단기수리 패턴의 마지막 달로 수리 진행에 따른 부분 회복을 반영하여, 초기 월간 차질 물량의 약 절반 수준인 2.50 Bcm를 절대 차질 물량으로 적용했다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "LNG Plant": "Wheatstone", "Month": 7, "Period": 112, "Year": 2026}` | null | 0 | Wheatstone이 직접 차질 설비로 언급된 첫 달이며, 생산 시설 급손상으로 즉시 생산 차질이 발생하는 구간이므로 2026년 7월 절대 LNG 생산량을 0 Mt/month로 설정했다. |
| 2 | `{"Country": "Australia", "LNG Plant": "Wheatstone", "Month": 8, "Period": 113, "Year": 2026}` | null | 0 | 2026년 8월은 3개월 수리 기간 중 높은 차질이 지속되는 중간 달로 보아, Wheatstone의 절대 LNG 생산량을 0 Mt/month로 유지했다. |
| 3 | `{"Country": "Australia", "LNG Plant": "Wheatstone", "Month": 9, "Period": 114, "Year": 2026}` | null | 0 | 2026년 9월은 단기 수리 기간의 마지막 달이나, 명확한 월중 복구 시점이 제시되지 않았으므로 피해 기간 전체에 대해 보수적으로 Wheatstone 절대 LNG 생산량을 0 Mt/month로 유지했다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Malaysia", "LNG Plant": "MLNG", "LNG Plant Train": "MLNG Dua T4-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 9.6, "Period": 112, "Year": 2026}` | 0.9250000000000002 | 1 | MLNG Dua T4-T6의 2026년 7월 기준 가동률은 0.925로 상향 여력이 있으며, 대체 LNG 공급 50% 가정에 따라 가용 설비를 우선 활용하되 가동률 상한을 고려해 1.0으로 설정했다. |
| 2 | `{"Country": "Malaysia", "LNG Plant": "MLNG", "LNG Plant Train": "MLNG Dua T4-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 9.6, "Period": 113, "Year": 2026}` | 0.9250000000000002 | 1 | MLNG Dua T4-T6의 2026년 8월 기준 가동률은 0.925로 7월과 동일한 상향 여력이 있어, 3개월 대체 공급 기간 중 해당 월도 1.0으로 상향했다. |
| 3 | `{"Country": "Malaysia", "LNG Plant": "MLNG", "LNG Plant Train": "MLNG Dua T4-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 9.6, "Period": 114, "Year": 2026}` | 0.9250000000000002 | 1 | MLNG Dua T4-T6의 2026년 9월 기준 가동률은 0.925이며, 대체 공급 적용 기간의 마지막 달에도 명확한 가동 여력이 확인되므로 1.0으로 상향했다. |
| 4 | `{"Country": "Malaysia", "LNG Plant": "MLNG", "LNG Plant Train": "MLNG Satu T1-T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 8.4, "Period": 112, "Year": 2026}` | 0.9249999999999998 | 1 | MLNG Satu T1-T3의 2026년 7월 기준 가동률은 0.925로 상한까지의 여력이 있어, 대체 공급 물량을 흡수하는 가용 액화설비로 보고 1.0을 적용했다. |
| 5 | `{"Country": "Malaysia", "LNG Plant": "MLNG", "LNG Plant Train": "MLNG Satu T1-T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 8.4, "Period": 113, "Year": 2026}` | 0.9249999999999998 | 1 | MLNG Satu T1-T3의 2026년 8월 기준 가동률은 0.925이며, 같은 대체 공급 기간 내 상향 가능한 설비로 판단해 가동률을 1.0으로 설정했다. |
| 6 | `{"Country": "Malaysia", "LNG Plant": "MLNG", "LNG Plant Train": "MLNG Satu T1-T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 8.4, "Period": 114, "Year": 2026}` | 0.9249999999999998 | 1 | MLNG Satu T1-T3의 2026년 9월 기준 가동률은 0.925로, 3개월 대체 공급 적용의 마지막 달에도 상한 내 상향 여력이 있어 1.0으로 제안했다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1245,
  "model_param_proposal_id": 48,
  "proposal_completed_dtm": "2026-07-07 17:35:32.533033",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "VolumeAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Volumes (Bcm)"
        ]
      },
      "parameterName": "SupplyDisruption",
      "rationale": "영향 시설 유형이 생산 시설로 지정되어 호주 생산 차질을 국가 단위 공급 차질 입력인 SupplyDisruption에 반영하는 것이 적절하다. 기간은 3개월이며 급손상-단기수리 패턴이므로 초기 2개월은 높은 차질을 유지하고 마지막 달은 수리 진행에 따른 부분 회복을 반영한 절대 Bcm 값으로 제안한다.",
      "values": [
        {
          "Country": "Australia",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 4.99,
          "rationale": "2026년 7월 호주 생산 차질 첫 달로, 이벤트의 서부 호주 44 mmtpa 차질을 월 단위 LNG 물량으로 나눈 뒤 가스 부피 기준으로 환산해 약 4.99 Bcm의 절대 차질 물량을 적용했다."
        },
        {
          "Country": "Australia",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 4.99,
          "rationale": "2026년 8월은 3개월 차질 기간 중 복구 전 높은 차질이 지속되는 달로 보아, 7월과 동일하게 44 mmtpa 차질의 월간 환산치인 약 4.99 Bcm를 적용했다."
        },
        {
          "Country": "Australia",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 2.5,
          "rationale": "2026년 9월은 급손상-단기수리 패턴의 마지막 달로 수리 진행에 따른 부분 회복을 반영하여, 초기 월간 차질 물량의 약 절반 수준인 2.50 Bcm를 절대 차질 물량으로 적용했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqProdAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqProdAdjustment"
        ]
      },
      "parameterName": "LiqProdAdjustment",
      "rationale": "영향 시설 유형이 생산 시설이고 이벤트에서 Wheatstone 차질이 명시되어 있어 액화 생산 가능량 자체를 낮추는 LiqProdAdjustment가 선택된다. 3개월 단기 수리 기간 동안 Wheatstone 생산량을 보수적으로 하향 override하되, 명확한 기준 생산량이 없으므로 피해 기간의 직접 대상 설비에 대해 절대 생산량 하한을 적용한다.",
      "values": [
        {
          "Country": "Australia",
          "LNG Plant": "Wheatstone",
          "Month": 7,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "Wheatstone이 직접 차질 설비로 언급된 첫 달이며, 생산 시설 급손상으로 즉시 생산 차질이 발생하는 구간이므로 2026년 7월 절대 LNG 생산량을 0 Mt/month로 설정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Wheatstone",
          "Month": 8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "2026년 8월은 3개월 수리 기간 중 높은 차질이 지속되는 중간 달로 보아, Wheatstone의 절대 LNG 생산량을 0 Mt/month로 유지했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Wheatstone",
          "Month": 9,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "2026년 9월은 단기 수리 기간의 마지막 달이나, 명확한 월중 복구 시점이 제시되지 않았으므로 피해 기간 전체에 대해 보수적으로 Wheatstone 절대 LNG 생산량을 0 Mt/month로 유지했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "대체 LNG 공급 가능성이 50%로 주어져 피해 물량의 일부를 시장 연결 대체 공급국의 액화설비 가동률 상향으로 흡수하는 LiqUtilAdjustment가 직접 연결된다. 기간은 3개월이며, 기준 가동률에서 명확한 상향 여력이 있고 0~1 가동률 제약에 맞출 수 있는 대체 공급 설비를 우선적으로 1.0까지 상향한다.",
      "values": [
        {
          "Country": "Malaysia",
          "LNG Plant": "MLNG",
          "LNG Plant Train": "MLNG Dua T4-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 9.6,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9250000000000002,
          "proposedValue": 1,
          "rationale": "MLNG Dua T4-T6의 2026년 7월 기준 가동률은 0.925로 상향 여력이 있으며, 대체 LNG 공급 50% 가정에 따라 가용 설비를 우선 활용하되 가동률 상한을 고려해 1.0으로 설정했다."
        },
        {
          "Country": "Malaysia",
          "LNG Plant": "MLNG",
          "LNG Plant Train": "MLNG Dua T4-T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 9.6,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9250000000000002,
          "proposedValue": 1,
          "rationale": "MLNG Dua T4-T6의 2026년 8월 기준 가동률은 0.925로 7월과 동일한 상향 여력이 있어, 3개월 대체 공급 기간 중 해당 월도 1.0으로 상향했다."
        },
        {
          "Country": "Malaysia",
          "LNG Plant": "MLNG",
          "LNG Plant Train": "MLNG Dua T4-T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 9.6,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.9250000000000002,
          "proposedValue": 1,
          "rationale": "MLNG Dua T4-T6의 2026년 9월 기준 가동률은 0.925이며, 대체 공급 적용 기간의 마지막 달에도 명확한 가동 여력이 확인되므로 1.0으로 상향했다."
        },
        {
          "Country": "Malaysia",
          "LNG Plant": "MLNG",
          "LNG Plant Train": "MLNG Satu T1-T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9249999999999998,
          "proposedValue": 1,
          "rationale": "MLNG Satu T1-T3의 2026년 7월 기준 가동률은 0.925로 상한까지의 여력이 있어, 대체 공급 물량을 흡수하는 가용 액화설비로 보고 1.0을 적용했다."
        },
        {
          "Country": "Malaysia",
          "LNG Plant": "MLNG",
          "LNG Plant Train": "MLNG Satu T1-T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9249999999999998,
          "proposedValue": 1,
          "rationale": "MLNG Satu T1-T3의 2026년 8월 기준 가동률은 0.925이며, 같은 대체 공급 기간 내 상향 가능한 설비로 판단해 가동률을 1.0으로 설정했다."
        },
        {
          "Country": "Malaysia",
          "LNG Plant": "MLNG",
          "LNG Plant Train": "MLNG Satu T1-T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.9249999999999998,
          "proposedValue": 1,
          "rationale": "MLNG Satu T1-T3의 2026년 9월 기준 가동률은 0.925로, 3개월 대체 공급 적용의 마지막 달에도 상한 내 상향 여력이 있어 1.0으로 제안했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 47,
  "scenario_id": 279,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:14.961 | 14.961 | 3054 | 755 | 3809 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:14.736 | 74.736 | 12631 | 6896 | 19527 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:25.112 | 85.112 | 13705 | 5467 | 19172 |

#### scenario_id=280 [model_parameter_agent_test] 수입 시설 피해

- 소요시간: 03:27.569 (207.569s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "affected_facility_type": "수입 시설",
    "alt_lng_supply_availability": "25%",
    "period": "6개월",
    "supply_disruption_intensity": "중간",
    "supply_disruption_pattern": "급손상-장기재건"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "자연재해 영향이 수입 터미널 및 재기화 인프라에 집중되어 6개월 동안 수입 처리 여력이 낮아지고 대체 조달도 제한된다.",
  "probability_delta": 3.0,
  "probability_score": 25.0,
  "scenario_group_id": 47,
  "scenario_id": 280,
  "status": "created",
  "title": "[model_parameter_agent_test] 수입 시설 피해"
}
```

##### Validation Summary

- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=5, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 54 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"parameter|11|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 1 | 영향 시설 유형은 수입 시설로 제시되어 액화시설 가동률을 직접 낮추는 LiqUtilAdjustment와의 연결은 제한적입니다. 대체 LNG 공급 가능성 25%는 공급 대체 여력이 낮다는 맥락을 주지만, 제공된 슬롯은 호주 액화 플랜트·트레인에 한정되어 있어 수입 터미널 피해를 해당 액화 트레인의 직접 가동률 하락으로 전환하지 않습니다. 따라서 가장 이른 적용 월의 대표 슬롯에 대해 기준 가동률을 유지하는 최종 입력값을 제안합니다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 103, "Year": 2026}` | 1.0384615384615388 | 1.0384615384615388 | 제공된 기준 record 중 호주 Gorgon LNG T1의 2026년 7월 값을 사용했다. 기준값은 1.0384615384615388이며, 시나리오의 직접 피해 대상이 수입 시설이므로 해당 액화 트레인의 직접 가동률 차감은 적용하지 않아 제안값도 1.0384615384615388로 유지했다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1245,
  "model_param_proposal_id": 49,
  "proposal_completed_dtm": "2026-07-07 17:35:48.054184",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "영향 시설 유형은 수입 시설로 제시되어 액화시설 가동률을 직접 낮추는 LiqUtilAdjustment와의 연결은 제한적입니다. 대체 LNG 공급 가능성 25%는 공급 대체 여력이 낮다는 맥락을 주지만, 제공된 슬롯은 호주 액화 플랜트·트레인에 한정되어 있어 수입 터미널 피해를 해당 액화 트레인의 직접 가동률 하락으로 전환하지 않습니다. 따라서 가장 이른 적용 월의 대표 슬롯에 대해 기준 가동률을 유지하는 최종 입력값을 제안합니다.",
      "values": [
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 1.0384615384615388,
          "rationale": "제공된 기준 record 중 호주 Gorgon LNG T1의 2026년 7월 값을 사용했다. 기준값은 1.0384615384615388이며, 시나리오의 직접 피해 대상이 수입 시설이므로 해당 액화 트레인의 직접 가동률 차감은 적용하지 않아 제안값도 1.0384615384615388로 유지했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 47,
  "scenario_id": 280,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:10.625 | 10.625 | 3057 | 593 | 3650 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:14.016 | 74.016 | 11970 | 8685 | 20655 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:39.946 | 99.946 | 16159 | 3430 | 19589 |

### event_type_l2_id=17 지정학적 긴장 및 전쟁·군사분쟁

#### Scenario Group

```json
{
  "description": "사건 요약:\n6월 3일 신규 Record들은 미국·이란 충돌 재격화, 이란의 쿠웨이트·바레인 방향 탄도미사일 발사, 미군의 이란 케슘섬 타격, 미·이란 협상 교착을 반복적으로 보도함. 미국·이스라엘·이란이 전쟁을 일시 중단하는 임시 합의에 가까워지고 있다는 로이터 보도도 함께 제시됨. 다만 양측의 잠정 휴전은 아직 공식 서명되지 않았고, 아바스 아락치 이란 외무장관은 미국과의 접촉은 유지되지만 협상 진전은 없다고 밝힘. 핵심 Event는 특정 LNG 설비 차질이 아니라 중동 전쟁·군사분쟁 확대에 따른 에너지 리스크 재부각임.\n\n영향 경로:\nIMF는 중동 전쟁으로 에너지 시설과 호르무즈 해협 항로가 타격을 받았지만 사우디아라비아가 동서 송유관과 홍해 항만을 활용해 원유 수출 경로를 우회하며 충격을 제한했다고 설명함. 이는 LNG 직접 수급 차질보다는 걸프 지역 에너지 운송 안정성, 항로 우회, 보험·리스크 비용을 통해 가스 시장에 간접 전이되는 구조임. 국제에너지기구가 현재와 같은 재고 감소가 이어질 경우 여름철 세계 원유 재고가 위험할 정도로 낮아질 수 있다고 언급한 점도 에너지 복합시장 경계감을 높이는 요인임. OECD는 에너지 공급 차질이 2027년까지 이어질 경우 세계 성장률이 2026년 2.1%, 2027년 1.8%까지 낮아질 수 있다고 경고함.\n\n시장 반응:\n6월 3일 중동 군사 긴장 재점화와 테헤란·워싱턴 간 외교 교착 속에 국제유가가 약 2% 상승함. 로이터는 미국과 이란 간 충돌 재격화 이후 가스 가격이 오르며 독일 연간 기저부하 선물이 95.88유로/MWh로 1.5% 상승했다고 보도함. 미국 국채시장에서는 유가 상승에 따른 인플레이션 우려가 재부각되며 10년물 수익률이 3.4bp 오른 4.489%를 기록함. 신규 Record에 JKM, TTF, LNG 운임, 전쟁위험보험료의 구체 수치는 제시되지 않음.\n\nLNG 시장 관점:\n해당 Event는 direct_lng가 아니라 energy_indirect 성격의 외생 충격임. 호르무즈 해협과 걸프 지역 항로 불안은 중동 LNG 및 에너지 화물의 운송 리스크 프리미엄을 지지할 수 있는 요인임. 다만 신규 Record 기준으로 특정 LNG 터미널 가동 중단, LNG 화물 취소, 카타르 등 LNG 수출 물량 감소는 확인되지 않음. 따라서 LNG 시장 해석은 실물 수급 차질 확정보다는 지정학적 리스크 프리미엄과 에너지 복합가격 강세를 통한 간접 영향 중심임.",
  "dimension_selected": [
    "period",
    "transport_disruption",
    "supply_disruption_intensity",
    "demand_response_alternative_lng"
  ],
  "event_type": {
    "event_type_l1_id": 4,
    "event_type_l2_id": 17,
    "level_1_code": "exogenous_shock",
    "level_1_label": "외생충격",
    "level_2_code": "geopolitical_tension_war",
    "level_2_label": "지정학적 긴장 및 전쟁·군사분쟁"
  },
  "event_type_l2_id": 17,
  "mi_event_id": 1133,
  "request_usr_id": 1000085,
  "scenario_count": 7,
  "scenario_group_id": 16,
  "stage": "completed",
  "status": "created",
  "summary": "[중동 지정학 리스크] 미·이란 충돌 재격화와 협상 교착 → 에너지 프리미엄 지지",
  "title": "중동 군사충돌 재격화 에너지 리스크"
}
```

#### Dimension Template

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
    "dim_key": "transport_disruption",
    "display_order": 2,
    "label": "운송 차질",
    "required": true,
    "value_enums": [
      "전혀 없음",
      "낮음",
      "중간",
      "높음",
      "매우 높음"
    ]
  },
  {
    "dim_key": "supply_disruption_intensity",
    "display_order": 3,
    "label": "공급 차질 - 강도",
    "required": false,
    "value_enums": [
      "전혀 없음",
      "낮음",
      "중간",
      "높음",
      "매우 높음"
    ]
  },
  {
    "dim_key": "supply_disruption_pattern",
    "display_order": 4,
    "label": "공급 차질 - 발생/회복 패턴",
    "required": false,
    "value_enums": [
      "급차질-급회복",
      "급손상-단기수리",
      "급손상-장기재건",
      "영구 손실",
      "지연발생-단계적 회복",
      "지연발생-즉시 해소",
      "점진차질-단계적 회복",
      "점진차질-즉시 해소",
      "즉시발생-장기 잠식"
    ]
  },
  {
    "dim_key": "demand_response_alternative_lng",
    "display_order": 5,
    "label": "수요측 대응 - 타 공급원 경유 LNG 확보량",
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
    "dim_key": "demand_response_powermix_reduction",
    "display_order": 6,
    "label": "수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량",
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
    "dim_key": "trade_restriction",
    "display_order": 7,
    "label": "거래 제한 (계약 취소 등)",
    "required": false,
    "value_enums": [
      "계약 유지 (취소 없음)",
      "일부 계약 취소",
      "전체 계약 취소"
    ]
  }
]
```

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "타 공급국 상향으로 상쇄",
      "dimension_key": "demand_response_alternative_lng",
      "dimension_label": "수요측 대응 - 타 공급원 경유 LNG 확보량",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 92,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 93,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "자체 PowerMix 조정으로 LNG 수요 감소(SPR/대체 효과 포함) : 수요국의 정책·비상 대응으로 LNG 발전 수요가 줄면 PowerMix의 Gas 비중을 낮추고 대체 전원 비중을 조정",
      "dimension_key": "demand_response_powermix_reduction",
      "dimension_label": "수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 92,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 93,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension_key": "demand_response_powermix_reduction",
      "dimension_label": "수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 92,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 93,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "장기화 시 종료 N/A — 시간축",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 92,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3개월",
          "scenario_id": 93,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqProdAdjustment",
      "comment": "생산량 직접 감소(대폭/영구) : 전쟁·제재로 장기 또는 영구 생산 손실이 명확할 때 생산량 자체를 하향 조정",
      "dimension_key": "supply_disruption_intensity",
      "dimension_label": "공급 차질 - 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqProdAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 생산량 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "낮음",
          "scenario_id": 92,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 93,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "액화시설 가동률 감소 : 영향권 액화시설의 이용률을 하향 조정하고, 단기 제약은 LiqUtilAdjustment를 우선 사용",
      "dimension_key": "supply_disruption_intensity",
      "dimension_label": "공급 차질 - 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "낮음",
          "scenario_id": 92,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 93,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "SupplyDisruption",
      "comment": "upstream(가스전) 생산 차질 동반 시",
      "dimension_key": "supply_disruption_intensity",
      "dimension_label": "공급 차질 - 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "VolumeAdjustment",
        "model_table": "table2",
        "semantic_axes": "Upstream 공급량 override — Country·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "낮음",
          "scenario_id": 92,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 93,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "Ref. 공급 차질 패턴 — 시계열",
      "dimension_key": "supply_disruption_pattern",
      "dimension_label": "공급 차질 - 발생/회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 92,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 93,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "From-To 계약 물량 취소 : 계약 취소는 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 가능량 감소가 확인될 때 Supply 계열 파라미터로 우회 반영",
      "dimension_key": "trade_restriction",
      "dimension_label": "거래 제한 (계약 취소 등)",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 92,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 93,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "용선료·보험료 상승 : 운송비·보험료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 선적 차질이 있으면 공급 차질 기간·강도 판단에만 사용",
      "dimension_key": "transport_disruption",
      "dimension_label": "운송 차질",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "낮음",
          "scenario_id": 92,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 93,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 17,
  "mapping_count": 10,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:05:32.534602",
  "detail_analysis": "사건 요약:\n6월 18일 신규 Record들은 도널드 트럼프 미국 대통령과 마수드 페제시키안 이란 대통령이 전쟁 종식과 호르무즈 해협 재개방을 위한 임시 양해각서에 서명한 전개를 반복적으로 보도함. 백악관은 트럼프 대통령이 전날 서명한 합의문을 미 의회에 전달했고, 해당 문서는 레바논을 포함한 모든 전선에서 군사 작전을 즉각적이고 영구적으로 중단한다고 명시한 것으로 보도됨. JD 밴스 미국 부통령은 합의에 따른 60일 기간이 6월 18일부터 시작됐고, 60일 이후 호르무즈 해협 운영 문제는 최종 협상에서 결정될 것이라고 설명함. 직전 요약의 핵심이 미·이란 충돌 재격화와 협상 교착이었다면, 최신 상태는 임시 합의 서명과 호르무즈 통항 재개로 전환됨.\n\n영향 경로:\n합의문에는 미국의 이란 항만 봉쇄 해제와 호르무즈 해협 해상 교통 복원이 포함된 것으로 보도됨. JD 밴스 부통령은 합의 이후 밤사이 원유 1,250만 배럴이 호르무즈 해협을 통과했다고 밝혔고, 별도 보도는 사우디 국적 초대형 유조선 3척이 합의 몇 시간 만에 해협을 통과했다고 전함. 이는 직전 단계의 호르무즈·걸프 항로 불안이 일부 완화되는 Fundamental 신호임. 다만 이스라엘군의 레바논 공습, 이스라엘 측 비판, 미국 공화당 인사들의 제재 완화·동결 자산 해제·60일 추가 협상 기간 비판이 병존해 합의 이행 불확실성 잔존함.\n\n시장 반응:\n신규 Record에는 JKM, TTF, LNG 운임, 전쟁위험보험료의 구체 가격 수치가 제시되지 않음. 직전 보도 기준 중동 군사 긴장 재점화와 외교 교착 속에 국제유가는 약 2% 상승했고, 가스 가격 상승을 따라 독일 연간 기저부하 선물은 95.88유로/MWh로 1.5% 상승함. 이번 임시 합의와 호르무즈 통항 재개는 에너지 운송 리스크 프리미엄을 낮추는 방향의 재료임. 그러나 합의 세부 조항에 대한 의회 비판과 레바논 전선 불확실성 때문에 프리미엄 해소는 완전하지 않은 상태임.\n\nLNG 시장 관점:\n해당 Event는 특정 LNG 설비 사고가 아니라 중동 전쟁·군사분쟁과 호르무즈 항로 리스크에 따른 외생충격 성격임. 신규 Record 기준 특정 LNG 터미널 가동 중단, LNG 화물 취소, 카타르 등 LNG 수출 물량 감소는 확인되지 않음. 호르무즈 해협 재개방과 원유 1,250만 배럴 통과는 중동 에너지 물동량 정상화 신호로 LNG 운송 리스크 프리미엄 완화 요인임. 다만 최종 합의까지 60일 협상 기간이 남아 있고 레바논 관련 조항 이행 의문이 제기돼 LNG 시장에는 물리적 차질 확정보다 잔존 지정학 리스크 관리가 핵심임.",
  "event_title_ko": "미·이란 임시합의로 호르무즈 재개방",
  "event_type_l2_id": 17,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-18T21:35:23",
  "mi_event_id": "1133",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[중동 지정학 리스크] 미·이란 임시합의와 호르무즈 통항 재개 → 운송 리스크 완화",
  "source_mi_record_ids": [
    2209,
    2220,
    2221,
    2230,
    2334,
    2335,
    2342,
    2343,
    2344,
    2345,
    2346,
    2347,
    2349,
    2358,
    2415,
    2416,
    2417,
    2720,
    3066,
    3178,
    3179,
    3180,
    3181,
    3182,
    3184,
    3185,
    3189,
    3190,
    3192,
    3194,
    3201,
    3202,
    3203,
    3204,
    3205,
    3208,
    3211,
    3212
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [92, 93]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=92 1개월 내 물류 프리미엄 흡수

- 소요시간: 03:22.365 (202.365s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "demand_response_alternative_lng": "100%",
    "period": "1개월 이하",
    "supply_disruption_intensity": "낮음",
    "transport_disruption": "낮음"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "neutral"
  },
  "narrative": "기간은 1개월 이하로 짧고, 운송 차질과 공급 차질 강도는 모두 낮게 유지되는 조합이다.\n중동 군사충돌 재격화에도 LNG 선적·통항 지연은 제한적이며, 시장은 리스크 프리미엄을 단기 이벤트로 반영한다.\n수요자는 타 공급원 경유 LNG를 100% 확보해 부족분을 사실상 대체하므로 현물 cargo 경쟁은 크게 확대되지 않는다.",
  "probability_delta": 0.0,
  "probability_score": 58.0,
  "scenario_group_id": 16,
  "scenario_id": 92,
  "status": "created",
  "title": "1개월 내 물류 프리미엄 흡수"
}
```

##### Validation Summary

- expected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment", "SupplyDisruption"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=17|supplydisruptionintensity|liqprodadjustment|supply|liqprodadjustment, sheet=LiqProdAdjustment", "basecase record를 추출하지 못했습니다: candidate_key=17|supplydisruptionintensity|supplydisruption|supply|volumeadjustment, sheet=VolumeAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=4, validated=3, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 14 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=14, basecaseValue_present=14 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 14 | 공급 차질 강도는 낮음으로 액화시설 이용률 하향 가능성을 점검해야 하는 축이지만, 타 공급원 경유 LNG 확보량이 100%로 제시되어 부족분이 수요 측에서 사실상 흡수되는 조합이다. 또한 기간은 1개월 이하이고 최신 사건은 호르무즈 통항 재개와 특정 LNG 터미널·카타르 수출 차질 부재를 가리키므로, 물리적 액화 가동률 감소보다는 단기 물류 프리미엄 완화에 가깝다. 따라서 선택된 단기 대상에 대해 이용률 override는 기준 입력값을 유지하는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477010309278352가 확인된다. 특정 액화설비 중단이나 선적 취소가 확인되지 않고 대체 확보가 100%인 시나리오이므로 추가 하향 없이 최종값을 1.0477010309278352로 유지한다. |
| 2 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477010309278352가 확인된다. 물리적 생산 차질이 아닌 운송 리스크 완화 국면으로 해석되므로 최종값을 기준 입력값과 같은 1.0477010309278352로 둔다. |
| 3 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477010309278352가 확인된다. 공급 차질 강도가 낮고 대체 LNG 확보가 100%로 제시되어 액화 이용률을 낮출 근거가 제한적이므로 최종값을 1.0477010309278352로 유지한다. |
| 4 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 호르무즈 재개방 이후 카타르 액화설비의 직접 가동 차질이 확인되지 않아 최종값을 기준 입력값과 같은 1.0476962025316454로 제안한다. |
| 5 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 시나리오가 낮은 차질과 100% 대체 확보를 전제하므로 액화 이용률 조정은 발생시키지 않고 최종값을 1.0476962025316454로 유지한다. |
| 6 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 단기 물류 프리미엄은 남을 수 있으나 설비 가동률을 낮출 물리적 장애가 확인되지 않아 최종값을 1.0476962025316454로 둔다. |
| 7 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 최신 사건이 통항 재개와 운송 리스크 완화를 나타내므로 생산 설비 이용률에는 추가 충격을 반영하지 않고 1.0476962025316454를 최종값으로 사용한다. |
| 8 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 1.0476969696969696 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476969696969696이 확인된다. 공급 차질이 낮고 대체 물량 확보가 완전한 조건이므로 이용률 override는 기준 수준을 유지하여 최종값을 1.0476969696969696으로 둔다. |
| 9 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 1.0476969696969696 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476969696969696이 확인된다. 특정 LNG 생산 차질이 확인되지 않는 단기 리스크 흡수 시나리오이므로 최종값은 기준 입력값과 같은 1.0476969696969696으로 제안한다. |
| 10 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477021276595746이 확인된다. 호르무즈 통항 재개와 100% 대체 확보 조건을 반영해 액화 이용률 하향 없이 최종값을 1.0477021276595746으로 유지한다. |
| 11 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477021276595746이 확인된다. 시나리오상 차질 강도가 낮고 기간도 1개월 이하이므로 설비 가동률을 변경하지 않고 최종값을 1.0477021276595746으로 둔다. |
| 12 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477021276595746이 확인된다. 물류 프리미엄은 단기적으로 흡수되는 조건이고 생산 차질은 확인되지 않아 최종값을 기준과 같은 1.0477021276595746으로 제안한다. |
| 13 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 최신 사건은 통항 정상화 신호가 우세하고 LNG 액화설비 장애가 확인되지 않으므로 최종값을 1.0476962025316454로 유지한다. |
| 14 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 낮은 공급 차질과 완전한 대체 확보를 반영해 이용률 하향 조정은 적용하지 않고 최종값을 1.0476962025316454로 둔다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1133,
  "model_param_proposal_id": 50,
  "proposal_completed_dtm": "2026-07-07 17:36:15.466174",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "공급 차질 강도는 낮음으로 액화시설 이용률 하향 가능성을 점검해야 하는 축이지만, 타 공급원 경유 LNG 확보량이 100%로 제시되어 부족분이 수요 측에서 사실상 흡수되는 조합이다. 또한 기간은 1개월 이하이고 최신 사건은 호르무즈 통항 재개와 특정 LNG 터미널·카타르 수출 차질 부재를 가리키므로, 물리적 액화 가동률 감소보다는 단기 물류 프리미엄 완화에 가깝다. 따라서 선택된 단기 대상에 대해 이용률 override는 기준 입력값을 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0477010309278352,
          "proposedValue": 1.0477010309278352,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477010309278352가 확인된다. 특정 액화설비 중단이나 선적 취소가 확인되지 않고 대체 확보가 100%인 시나리오이므로 추가 하향 없이 최종값을 1.0477010309278352로 유지한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0477010309278352,
          "proposedValue": 1.0477010309278352,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477010309278352가 확인된다. 물리적 생산 차질이 아닌 운송 리스크 완화 국면으로 해석되므로 최종값을 기준 입력값과 같은 1.0477010309278352로 둔다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0477010309278352,
          "proposedValue": 1.0477010309278352,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477010309278352가 확인된다. 공급 차질 강도가 낮고 대체 LNG 확보가 100%로 제시되어 액화 이용률을 낮출 근거가 제한적이므로 최종값을 1.0477010309278352로 유지한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 1.0476962025316454,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 호르무즈 재개방 이후 카타르 액화설비의 직접 가동 차질이 확인되지 않아 최종값을 기준 입력값과 같은 1.0476962025316454로 제안한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 1.0476962025316454,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 시나리오가 낮은 차질과 100% 대체 확보를 전제하므로 액화 이용률 조정은 발생시키지 않고 최종값을 1.0476962025316454로 유지한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 1.0476962025316454,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 단기 물류 프리미엄은 남을 수 있으나 설비 가동률을 낮출 물리적 장애가 확인되지 않아 최종값을 1.0476962025316454로 둔다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 4 T7",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 1.0476962025316454,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 최신 사건이 통항 재개와 운송 리스크 완화를 나타내므로 생산 설비 이용률에는 추가 충격을 반영하지 않고 1.0476962025316454를 최종값으로 사용한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476969696969696,
          "proposedValue": 1.0476969696969696,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476969696969696이 확인된다. 공급 차질이 낮고 대체 물량 확보가 완전한 조건이므로 이용률 override는 기준 수준을 유지하여 최종값을 1.0476969696969696으로 둔다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476969696969696,
          "proposedValue": 1.0476969696969696,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476969696969696이 확인된다. 특정 LNG 생산 차질이 확인되지 않는 단기 리스크 흡수 시나리오이므로 최종값은 기준 입력값과 같은 1.0476969696969696으로 제안한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0477021276595746,
          "proposedValue": 1.0477021276595746,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477021276595746이 확인된다. 호르무즈 통항 재개와 100% 대체 확보 조건을 반영해 액화 이용률 하향 없이 최종값을 1.0477021276595746으로 유지한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0477021276595746,
          "proposedValue": 1.0477021276595746,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477021276595746이 확인된다. 시나리오상 차질 강도가 낮고 기간도 1개월 이하이므로 설비 가동률을 변경하지 않고 최종값을 1.0477021276595746으로 둔다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0477021276595746,
          "proposedValue": 1.0477021276595746,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0477021276595746이 확인된다. 물류 프리미엄은 단기적으로 흡수되는 조건이고 생산 차질은 확인되지 않아 최종값을 기준과 같은 1.0477021276595746으로 제안한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 1.0476962025316454,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 최신 사건은 통항 정상화 신호가 우세하고 LNG 액화설비 장애가 확인되지 않으므로 최종값을 1.0476962025316454로 유지한다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T7",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 1.0476962025316454,
          "rationale": "선택된 2026년 7월 단기 구간의 해당 열차에 대해 기준 입력값 1.0476962025316454가 확인된다. 낮은 공급 차질과 완전한 대체 확보를 반영해 이용률 하향 조정은 적용하지 않고 최종값을 1.0476962025316454로 둔다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 16,
  "scenario_id": 92,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:14.195 | 14.195 | 3670 | 220 | 3890 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:38.427 | 98.427 | 12800 | 4574 | 17374 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:11.305 | 71.305 | 13000 | 4874 | 17874 |

#### scenario_id=93 3개월 부분 차질과 절반 대체 조달

- 소요시간: 06:20.772 (380.772s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "demand_response_alternative_lng": "50%",
    "period": "3개월",
    "supply_disruption_intensity": "중간",
    "transport_disruption": "중간"
  },
  "impact": {
    "hh": "mild_bull",
    "jkm": "bull",
    "ttf": "mild_bull"
  },
  "narrative": "기간은 3개월로 늘어나고, 운송 차질과 공급 차질 강도는 중간 수준까지 확대된다.\n중동 항로의 보험료·대기시간 상승과 일부 선적 조정이 반복되며 아시아와 유럽 구매자 간 spot cargo 경쟁이 나타난다.\n다만 수요자가 타 공급원 경유 LNG를 50% 확보해 부족분의 절반을 흡수하므로 전면적인 공급 공백은 피한다.",
  "probability_delta": 0.0,
  "probability_score": 32.0,
  "scenario_group_id": 16,
  "scenario_id": 93,
  "status": "created",
  "title": "3개월 부분 차질과 절반 대체 조달"
}
```

##### Validation Summary

- expected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment", "SupplyDisruption"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=17|supplydisruptionintensity|liqprodadjustment|supply|liqprodadjustment, sheet=LiqProdAdjustment", "basecase record를 추출하지 못했습니다: candidate_key=17|supplydisruptionintensity|supplydisruption|supply|volumeadjustment, sheet=VolumeAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=4, validated=3, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 90 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=51, basecaseValue_present=51 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 51 | 공급 차질 강도 '중간'은 영향권 액화시설의 단기 이용률 하향 조정과 직접 연결되며, LiqUtilAdjustment는 train/month 단위의 가동률 override이므로 해당 충격을 반영하기에 적합합니다. 타 공급원 경유 LNG 확보량 50%는 차질의 시장 반영 강도를 완화하는 요소로 적용하고, 기간 3개월은 2026년 7~9월 적용 범위로 사용했습니다. 최신 사건에서 호르무즈 통항 재개와 물리적 LNG 설비 중단 부재가 확인되므로, 중동 영향권 설비에 한해 기준 이용률을 보수적으로 하향 조정하고 대체 조달은 하향 폭을 절반 수준으로 완화하는 방식으로 제안합니다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 103, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 2026년 7월 해당 train의 기준 이용률 1.0477010309278352에 중간 수준의 부분 차질을 반영하되, 50% 대체 조달과 호르무즈 재개방에 따른 완화 요인을 반영해 5% 하향한 최종 이용률로 산정했습니다. |
| 2 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 104, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 2026년 8월 해당 train의 기준 이용률 1.0024845360824741에 3개월 부분 차질의 지속을 반영하고, 대체 조달 완화 후 순 하향 폭을 5%로 적용했습니다. |
| 3 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 105, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206187 | 2026년 9월은 3개월 적용 범위의 마지막 달로, 기준 이용률 1.0294432989690723에 동일한 순 5% 하향 조정을 적용했습니다. |
| 4 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 103, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 2026년 7월 해당 train의 기준 이용률 1.0477010309278352에 중간 수준의 부분 차질과 50% 대체 조달 완화를 함께 반영해 5% 하향했습니다. |
| 5 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 104, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 2026년 8월 해당 train의 기준 이용률 1.0024845360824741을 현재 기준값으로 두고, 3개월 부분 차질의 잔존 영향을 순 5% 하향으로 반영했습니다. |
| 6 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 105, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206187 | 2026년 9월 해당 train의 기준 이용률 1.0294432989690723에 동일한 3개월 차질 가정을 적용하되, 대체 조달을 감안해 5%만 하향했습니다. |
| 7 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 103, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 2026년 7월 해당 train의 기준 이용률 1.0477010309278352에 중간 강도 차질의 보수적 순효과인 5% 하향을 적용했습니다. |
| 8 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 104, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 2026년 8월 해당 train의 기준 이용률 1.0024845360824741에서 운송·선적 조정 반복에 따른 잔존 차질을 반영해 5% 하향했습니다. |
| 9 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 105, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206187 | 2026년 9월 해당 train의 기준 이용률 1.0294432989690723에 3개월 부분 차질의 마지막 달 효과를 순 5% 하향으로 반영했습니다. |
| 10 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 103, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 차질과 절반 대체 조달을 함께 반영해 최종 5% 하향했습니다. |
| 11 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 104, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질 지속과 대체 조달 완화를 반영해 5% 하향했습니다. |
| 12 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 105, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 동일한 순 5% 하향 조정을 적용했습니다. |
| 13 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 103, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 강도 차질을 반영하되 50% 대체 조달로 완화해 5% 하향했습니다. |
| 14 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 104, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 영향 기간의 중간 달 조정으로 순 5% 하향을 적용했습니다. |
| 15 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 105, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 잔존 부분 차질의 순효과를 5% 하향으로 반영했습니다. |
| 16 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 103, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train의 기준 이용률 1.0476962025316454를 기준으로, 부분 차질과 대체 조달 완화를 반영한 5% 하향 최종값을 적용했습니다. |
| 17 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 104, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질의 순 하향 조정 5%를 적용했습니다. |
| 18 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 105, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 2026년 9월 해당 train의 기준 이용률 1.0294430379746833에서 대체 조달을 반영한 잔존 차질을 5% 하향으로 산정했습니다. |
| 19 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 103, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 차질의 완화 후 순효과로 5% 하향을 적용했습니다. |
| 20 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 104, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질 지속을 반영해 5% 하향했습니다. |
| 21 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 105, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 동일한 순 5% 하향 조정을 적용했습니다. |
| 22 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 103, "Year": 2026}` | 1.0476969696969696 | 0.9953121212121212 | 2026년 7월 해당 train의 기준 이용률 1.0476969696969696에 중간 수준 부분 차질과 50% 대체 조달 완화를 반영해 5% 하향했습니다. |
| 23 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 104, "Year": 2026}` | 1.0024848484848483 | 0.952360606060606 | 2026년 8월 해당 train의 기준 이용률 1.0024848484848485에 3개월 영향 기간의 순효과를 5% 하향으로 적용했습니다. |
| 24 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 105, "Year": 2026}` | 1.0294545454545456 | 0.9779818181818184 | 2026년 9월 해당 train의 기준 이용률 1.0294545454545456에 잔존 부분 차질을 반영해 5% 하향했습니다. |
| 25 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 103, "Year": 2026}` | 1.0476969696969696 | 0.9953121212121212 | 2026년 7월 해당 train의 기준 이용률 1.0476969696969696에 대체 조달 완화를 반영한 순 5% 하향 조정을 적용했습니다. |
| 26 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 104, "Year": 2026}` | 1.0024848484848483 | 0.952360606060606 | 2026년 8월 해당 train의 기준 이용률 1.0024848484848485에 3개월 부분 차질 지속을 반영해 5% 하향했습니다. |
| 27 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 105, "Year": 2026}` | 1.0294545454545456 | 0.9779818181818184 | 2026년 9월 해당 train의 기준 이용률 1.0294545454545456에 동일한 순 5% 하향 조정을 적용했습니다. |
| 28 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 103, "Year": 2026}` | 1.0477021276595746 | 0.995317021276596 | 2026년 7월 해당 train의 기준 이용률 1.0477021276595746에 중간 강도 차질과 50% 대체 조달 완화를 반영해 5% 하향했습니다. |
| 29 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 104, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170214 | 2026년 8월 해당 train의 기준 이용률 1.0024893617021278에 3개월 부분 차질의 중간 달 영향을 순 5% 하향으로 반영했습니다. |
| 30 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 105, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 2026년 9월 해당 train의 기준 이용률 1.029446808510638에 3개월 부분 차질의 마지막 달 조정으로 5% 하향을 적용했습니다. |
| 31 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 103, "Year": 2026}` | 1.0477021276595746 | 0.995317021276596 | 2026년 7월 해당 train의 기준 이용률 1.0477021276595746에 완화 후 순 5% 하향 조정을 적용했습니다. |
| 32 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 104, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170214 | 2026년 8월 해당 train의 기준 이용률 1.0024893617021278에 3개월 부분 차질 지속을 반영해 5% 하향했습니다. |
| 33 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 105, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 2026년 9월 해당 train의 기준 이용률 1.029446808510638에 동일한 순 5% 하향 조정을 적용했습니다. |
| 34 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 103, "Year": 2026}` | 1.0477021276595746 | 0.995317021276596 | 2026년 7월 해당 train의 기준 이용률 1.0477021276595746에 중간 차질과 대체 조달 완화 후 순 5% 하향을 적용했습니다. |
| 35 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 104, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170214 | 2026년 8월 해당 train의 기준 이용률 1.0024893617021278을 기준으로 3개월 부분 차질의 순 5% 하향 효과를 반영했습니다. |
| 36 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 105, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 2026년 9월 해당 train의 기준 이용률 1.029446808510638에 3개월 영향의 마지막 달 조정을 5% 하향으로 적용했습니다. |
| 37 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 103, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 수준 부분 차질을 반영하되 50% 대체 조달로 완화해 5% 하향했습니다. |
| 38 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 104, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질 지속을 반영해 5% 하향했습니다. |
| 39 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 105, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 잔존 부분 차질의 순효과를 5% 하향으로 적용했습니다. |
| 40 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 103, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 차질과 대체 조달 완화를 반영해 5% 하향했습니다. |
| 41 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 104, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질의 순효과인 5% 하향을 적용했습니다. |
| 42 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 105, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 동일한 3개월 차질 조정을 적용해 5% 하향했습니다. |
| 43 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 103, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 7월 해당 train의 기준 이용률 1.0956424079065634에 걸프 항로 리스크에 따른 부분 차질을 반영하되, 대체 조달과 통항 재개 완화를 감안해 5% 하향했습니다. |
| 44 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 1.15, "Period": 104, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 8월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질 지속을 반영해 5% 하향했습니다. |
| 45 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 1.15, "Period": 105, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 9월 해당 train의 기준 이용률 1.0956424079065634에 3개월 적용 범위의 마지막 달 조정으로 5% 하향을 적용했습니다. |
| 46 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 103, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 7월 해당 train의 기준 이용률 1.0956424079065634에 중간 수준 부분 차질과 50% 대체 조달 완화를 함께 반영해 5% 하향했습니다. |
| 47 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 1.15, "Period": 104, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 8월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질의 순 5% 하향 효과를 반영했습니다. |
| 48 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 1.15, "Period": 105, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 9월 해당 train의 기준 이용률 1.0956424079065634에 동일한 순 5% 하향 조정을 적용했습니다. |
| 49 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3, "Period": 103, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 7월 해당 train의 기준 이용률 1.0956424079065634에 걸프 지역 부분 차질의 보수적 순효과를 5% 하향으로 반영했습니다. |
| 50 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3, "Period": 104, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 8월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질 지속을 반영해 5% 하향했습니다. |
| 51 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3, "Period": 105, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 9월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질의 마지막 달 영향을 5% 하향으로 적용했습니다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1133,
  "model_param_proposal_id": 54,
  "proposal_completed_dtm": "2026-07-07 17:39:34.671141",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "공급 차질 강도 '중간'은 영향권 액화시설의 단기 이용률 하향 조정과 직접 연결되며, LiqUtilAdjustment는 train/month 단위의 가동률 override이므로 해당 충격을 반영하기에 적합합니다. 타 공급원 경유 LNG 확보량 50%는 차질의 시장 반영 강도를 완화하는 요소로 적용하고, 기간 3개월은 2026년 7~9월 적용 범위로 사용했습니다. 최신 사건에서 호르무즈 통항 재개와 물리적 LNG 설비 중단 부재가 확인되므로, 중동 영향권 설비에 한해 기준 이용률을 보수적으로 하향 조정하고 대체 조달은 하향 폭을 절반 수준으로 완화하는 방식으로 제안합니다.",
      "values": [
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0477010309278352,
          "proposedValue": 0.9953159793814434,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0477010309278352에 중간 수준의 부분 차질을 반영하되, 50% 대체 조달과 호르무즈 재개방에 따른 완화 요인을 반영해 5% 하향한 최종 이용률로 산정했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.002484536082474,
          "proposedValue": 0.9523603092783504,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024845360824741에 3개월 부분 차질의 지속을 반영하고, 대체 조달 완화 후 순 하향 폭을 5%로 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294432989690725,
          "proposedValue": 0.9779711340206187,
          "rationale": "2026년 9월은 3개월 적용 범위의 마지막 달로, 기준 이용률 1.0294432989690723에 동일한 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0477010309278352,
          "proposedValue": 0.9953159793814434,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0477010309278352에 중간 수준의 부분 차질과 50% 대체 조달 완화를 함께 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.002484536082474,
          "proposedValue": 0.9523603092783504,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024845360824741을 현재 기준값으로 두고, 3개월 부분 차질의 잔존 영향을 순 5% 하향으로 반영했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294432989690725,
          "proposedValue": 0.9779711340206187,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294432989690723에 동일한 3개월 차질 가정을 적용하되, 대체 조달을 감안해 5%만 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0477010309278352,
          "proposedValue": 0.9953159793814434,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0477010309278352에 중간 강도 차질의 보수적 순효과인 5% 하향을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.002484536082474,
          "proposedValue": 0.9523603092783504,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024845360824741에서 운송·선적 조정 반복에 따른 잔존 차질을 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294432989690725,
          "proposedValue": 0.9779711340206187,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294432989690723에 3개월 부분 차질의 마지막 달 효과를 순 5% 하향으로 반영했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 0.9953113924050632,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 차질과 절반 대체 조달을 함께 반영해 최종 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질 지속과 대체 조달 완화를 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 동일한 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 0.9953113924050632,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 강도 차질을 반영하되 50% 대체 조달로 완화해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 영향 기간의 중간 달 조정으로 순 5% 하향을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 잔존 부분 차질의 순효과를 5% 하향으로 반영했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 0.9953113924050632,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476962025316454를 기준으로, 부분 차질과 대체 조달 완화를 반영한 5% 하향 최종값을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질의 순 하향 조정 5%를 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294430379746833에서 대체 조달을 반영한 잔존 차질을 5% 하향으로 산정했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 4 T7",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 0.9953113924050632,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 차질의 완화 후 순효과로 5% 하향을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 4 T7",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질 지속을 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 4 T7",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 동일한 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476969696969696,
          "proposedValue": 0.9953121212121212,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476969696969696에 중간 수준 부분 차질과 50% 대체 조달 완화를 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024848484848483,
          "proposedValue": 0.952360606060606,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024848484848485에 3개월 영향 기간의 순효과를 5% 하향으로 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294545454545456,
          "proposedValue": 0.9779818181818184,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294545454545456에 잔존 부분 차질을 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476969696969696,
          "proposedValue": 0.9953121212121212,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476969696969696에 대체 조달 완화를 반영한 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024848484848483,
          "proposedValue": 0.952360606060606,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024848484848485에 3개월 부분 차질 지속을 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294545454545456,
          "proposedValue": 0.9779818181818184,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294545454545456에 동일한 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0477021276595746,
          "proposedValue": 0.995317021276596,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0477021276595746에 중간 강도 차질과 50% 대체 조달 완화를 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024893617021278,
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024893617021278에 3개월 부분 차질의 중간 달 영향을 순 5% 하향으로 반영했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.029446808510638,
          "proposedValue": 0.977974468085106,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.029446808510638에 3개월 부분 차질의 마지막 달 조정으로 5% 하향을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0477021276595746,
          "proposedValue": 0.995317021276596,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0477021276595746에 완화 후 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024893617021278,
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024893617021278에 3개월 부분 차질 지속을 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.029446808510638,
          "proposedValue": 0.977974468085106,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.029446808510638에 동일한 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0477021276595746,
          "proposedValue": 0.995317021276596,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0477021276595746에 중간 차질과 대체 조달 완화 후 순 5% 하향을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024893617021278,
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024893617021278을 기준으로 3개월 부분 차질의 순 5% 하향 효과를 반영했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.029446808510638,
          "proposedValue": 0.977974468085106,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.029446808510638에 3개월 영향의 마지막 달 조정을 5% 하향으로 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 0.9953113924050632,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 수준 부분 차질을 반영하되 50% 대체 조달로 완화해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질 지속을 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 잔존 부분 차질의 순효과를 5% 하향으로 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T7",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0476962025316454,
          "proposedValue": 0.9953113924050632,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0476962025316454에 중간 차질과 대체 조달 완화를 반영해 5% 하향했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T7",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0024810126582275에 3개월 부분 차질의 순효과인 5% 하향을 적용했습니다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T7",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0294430379746833에 동일한 3개월 차질 조정을 적용해 5% 하향했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0956424079065634에 걸프 항로 리스크에 따른 부분 차질을 반영하되, 대체 조달과 통항 재개 완화를 감안해 5% 하향했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질 지속을 반영해 5% 하향했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0956424079065634에 3개월 적용 범위의 마지막 달 조정으로 5% 하향을 적용했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0956424079065634에 중간 수준 부분 차질과 50% 대체 조달 완화를 함께 반영해 5% 하향했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질의 순 5% 하향 효과를 반영했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0956424079065634에 동일한 순 5% 하향 조정을 적용했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train의 기준 이용률 1.0956424079065634에 걸프 지역 부분 차질의 보수적 순효과를 5% 하향으로 반영했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질 지속을 반영해 5% 하향했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train의 기준 이용률 1.0956424079065634에 3개월 부분 차질의 마지막 달 영향을 5% 하향으로 적용했습니다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 16,
  "scenario_id": 93,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.736 | 4.736 | 3667 | 202 | 3869 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:50.671 | 110.671 | 12792 | 13911 | 26703 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:54.308 | 234.308 | 22388 | 10651 | 33039 |

### event_type_l2_id=18 경제 제재 및 무역 제한

#### Scenario Group

```json
{
  "description": "사건 요약:\n러시아 Arctic LNG 2 프로젝트와 관련해 미국 제재 대상 시설이라는 점, TotalEnergies 지분 매각 허가 명령, 제재 대상 선박을 통한 출하가 언급됨. 생산 ramp-up보다 제재와 무역 제한의 시장 영향이 핵심임.\n\n영향 경로:\n제재는 선박 이용, 금융 결제, 보험, 구매자 접근성을 제약해 러시아 LNG 수출 경로를 복잡하게 만듦. 중국향 출하가 언급되더라도 제재 대상 cargo의 목적지와 거래 상대방은 제한될 수 있음.\n\n시장 반응:\n제재 관련 불확실성은 러시아 LNG 가격 할인과 대체 공급 프리미엄을 동시에 유발할 수 있음. Arctic LNG 2 물량이 시장에 유입되더라도 제재 리스크 때문에 투명한 가격 형성이 제한될 수 있음.\n\nLNG 시장 관점:\nArctic LNG 2는 러시아의 핵심 신규 LNG 프로젝트임. 기존 ramp-up Event와 같은 프로젝트이나 제재·무역 제한이라는 독립 시장 리스크로 별도 Event 생성이 적절함.",
  "dimension_selected": [
    "period",
    "supply_disruption_intensity",
    "supply_disruption_pattern",
    "demand_response_alternative_lng",
    "demand_response_powermix_reduction"
  ],
  "event_type": {
    "event_type_l1_id": 4,
    "event_type_l2_id": 18,
    "level_1_code": "exogenous_shock",
    "level_1_label": "외생충격",
    "level_2_code": "economic_sanctions_trade_restrictions",
    "level_2_label": "경제 제재 및 무역 제한"
  },
  "event_type_l2_id": 18,
  "mi_event_id": 1177,
  "request_usr_id": 1000085,
  "scenario_count": 6,
  "scenario_group_id": 22,
  "stage": "scenario_created",
  "status": "creating",
  "summary": "[러시아 LNG 제재] Arctic LNG 2 제재·지분 매각 허가 언급 → 무역 흐름 제약",
  "title": "러시아 Arctic LNG 2 제재 이슈"
}
```

#### Dimension Template

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
    "dim_key": "transport_disruption",
    "display_order": 2,
    "label": "운송 차질",
    "required": false,
    "value_enums": [
      "전혀 없음",
      "낮음",
      "중간",
      "높음",
      "매우 높음"
    ]
  },
  {
    "dim_key": "supply_disruption_intensity",
    "display_order": 3,
    "label": "공급 차질 - 강도",
    "required": true,
    "value_enums": [
      "전혀 없음",
      "낮음",
      "중간",
      "높음",
      "매우 높음"
    ]
  },
  {
    "dim_key": "supply_disruption_pattern",
    "display_order": 4,
    "label": "공급 차질 - 발생/회복 패턴",
    "required": true,
    "value_enums": [
      "급차질-급회복",
      "급손상-단기수리",
      "급손상-장기재건",
      "영구 손실",
      "지연발생-단계적 회복",
      "지연발생-즉시 해소",
      "점진차질-단계적 회복",
      "점진차질-즉시 해소",
      "즉시발생-장기 잠식"
    ]
  },
  {
    "dim_key": "demand_response_alternative_lng",
    "display_order": 5,
    "label": "수요측 대응 - 타 공급원 경유 LNG 확보량",
    "required": true,
    "value_enums": [
      "100%",
      "75%",
      "50%",
      "25%",
      "0%"
    ]
  },
  {
    "dim_key": "demand_response_powermix_reduction",
    "display_order": 6,
    "label": "수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량",
    "required": true,
    "value_enums": [
      "100%",
      "75%",
      "50%",
      "25%",
      "0%"
    ]
  },
  {
    "dim_key": "trade_restriction",
    "display_order": 7,
    "label": "거래 제한 (계약 취소 등)",
    "required": false,
    "value_enums": [
      "계약 유지 (취소 없음)",
      "일부 계약 취소",
      "전체 계약 취소"
    ]
  }
]
```

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "대체 공급 형성 time delay 존재",
      "dimension_key": "demand_response_alternative_lng",
      "dimension_label": "수요측 대응 - 타 공급원 경유 LNG 확보량",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "자체 PowerMix 조정 수요 감소",
      "dimension_key": "demand_response_powermix_reduction",
      "dimension_label": "수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension_key": "demand_response_powermix_reduction",
      "dimension_label": "수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "영구 제재 시 종료 N/A",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "3개월",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "1년",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqProdAdjustment",
      "comment": "생산량 직접 감소",
      "dimension_key": "supply_disruption_intensity",
      "dimension_label": "공급 차질 - 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqProdAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 생산량 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "낮음",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "LiqUtilAdjustment",
      "comment": "액화시설 가동률 감소",
      "dimension_key": "supply_disruption_intensity",
      "dimension_label": "공급 차질 - 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "LiqUtilAdjustment",
        "model_table": "table1",
        "semantic_axes": "액화시설 가동률 override — Country>Plant>Train·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "낮음",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "SupplyDisruption",
      "comment": "upstream 생산 차질 동반 시",
      "dimension_key": "supply_disruption_intensity",
      "dimension_label": "공급 차질 - 강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Supply",
        "model_sheet": "VolumeAdjustment",
        "model_table": "table2",
        "semantic_axes": "Upstream 공급량 override — Country·연·월"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "낮음",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "중간",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "Ref. 공급 차질 패턴",
      "dimension_key": "supply_disruption_pattern",
      "dimension_label": "공급 차질 - 발생/회복 패턴",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "지연발생-단계적 회복",
          "scenario_id": 129,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "지연발생-즉시 해소",
          "scenario_id": 130,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "제재 대상 계약 취소(partial→full) : 계약 취소·제재 물량은 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 차질로 확인되는 경우 Supply 계열 파라미터로 우회 반영",
      "dimension_key": "trade_restriction",
      "dimension_label": "거래 제한 (계약 취소 등)",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 129,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 130,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "그림자 선단 등 운송료 상승 : 운송료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 운송 제약이 공급량에 연결될 때만 기간·강도 판단에 사용",
      "dimension_key": "transport_disruption",
      "dimension_label": "운송 차질",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": null,
          "scenario_id": 129,
          "selected_in_scenario": false
        },
        {
          "dimension_value": null,
          "scenario_id": 130,
          "selected_in_scenario": false
        }
      ],
      "selected_in_any_scenario": false,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 18,
  "mapping_count": 10,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:24:46.245585",
  "detail_analysis": "사건 요약:\n러시아 Arctic LNG 2 프로젝트와 관련해 미국 제재 대상 시설이라는 점, TotalEnergies 지분 매각 허가 명령, 제재 대상 선박을 통한 출하가 언급됨. 생산 ramp-up보다 제재와 무역 제한의 시장 영향이 핵심임.\n\n영향 경로:\n제재는 선박 이용, 금융 결제, 보험, 구매자 접근성을 제약해 러시아 LNG 수출 경로를 복잡하게 만듦. 중국향 출하가 언급되더라도 제재 대상 cargo의 목적지와 거래 상대방은 제한될 수 있음.\n\n시장 반응:\n제재 관련 불확실성은 러시아 LNG 가격 할인과 대체 공급 프리미엄을 동시에 유발할 수 있음. Arctic LNG 2 물량이 시장에 유입되더라도 제재 리스크 때문에 투명한 가격 형성이 제한될 수 있음.\n\nLNG 시장 관점:\nArctic LNG 2는 러시아의 핵심 신규 LNG 프로젝트임. 기존 ramp-up Event와 같은 프로젝트이나 제재·무역 제한이라는 독립 시장 리스크로 별도 Event 생성이 적절함.",
  "event_title_ko": "러시아 Arctic LNG 2 제재 이슈",
  "event_type_l2_id": 18,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-05T00:00:00",
  "mi_event_id": "1177",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[러시아 LNG 제재] Arctic LNG 2 제재·지분 매각 허가 언급 → 무역 흐름 제약",
  "source_mi_record_ids": [
    2235,
    2393,
    2461,
    2462
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [129, 130]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=129 3개월 내 제재 프리미엄은 제한적

- 소요시간: 03:11.496 (191.496s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "demand_response_alternative_lng": "100%",
    "demand_response_powermix_reduction": "100%",
    "period": "3개월",
    "supply_disruption_intensity": "낮음",
    "supply_disruption_pattern": "지연발생-단계적 회복"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "neutral"
  },
  "narrative": "기간은 3개월, 공급 차질 강도는 낮음으로 가정한다.\n차질 패턴은 P5: Delayed onset - Slow recover로, 제재·선박 확인 절차가 지연되며 실제 물량 영향은 늦게 나타난다.\n대체 LNG 확보와 PowerMix 조정이 각각 100% 가능해 구매자는 부족분을 사실상 상쇄한다.\n시장 참여자는 Arctic LNG 2 관련 뉴스에는 반응하지만, 실물 수급 압박은 크지 않은 단기 리스크로 본다.",
  "probability_delta": 0.0,
  "probability_score": 39.0,
  "scenario_group_id": 22,
  "scenario_id": 129,
  "status": "creating",
  "title": "3개월 내 제재 프리미엄은 제한적"
}
```

##### Validation Summary

- expected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment", "SupplyDisruption", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment", "SupplyDisruption", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=18|supplydisruptionintensity|liqprodadjustment|supply|liqprodadjustment, sheet=LiqProdAdjustment", "basecase record를 추출하지 못했습니다: candidate_key=18|supplydisruptionintensity|supplydisruption|supply|volumeadjustment, sheet=VolumeAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=5, validated=4, final_selected=4, proposalParameters=4 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 22 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=11, basecaseValue_present=7 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 6 | 공급 차질 강도 ‘낮음’은 Arctic LNG 2 액화시설 가동률의 제한적 하향 요인으로 연결되며, 대체 LNG 확보 ‘100%’는 실물 부족을 완화하되 제재·선박 확인에 따른 가동 제약 자체를 완전히 제거하지는 않는 조건으로 해석했다. 기간은 3개월, 패턴은 지연발생-단계적 회복이므로 초기 월은 기준 가동률을 유지하고, 영향이 늦게 나타나는 후반 월에만 보수적으로 소폭 하향하는 구조로 제안한다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 1 | 공급 차질 강도 ‘낮음’은 Arctic LNG 2의 생산량 직접 감소 가능성과 연결되지만, 사건의 핵심은 생산설비 손상이 아니라 제재·무역 흐름 제약이다. 따라서 3개월 지연발생 패턴을 반영해 가장 직접적인 운영 트레인의 후반 월에만 소폭 생산량 하향을 적용하는 보수적 구조로 제안한다. |
| 3 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 3 | 공급 차질 강도 ‘낮음’은 러시아 공급 차질 파라미터와 연결되지만, 본 사건은 upstream 생산 손상보다는 Arctic LNG 2의 제재·선박·거래 제한이 중심이다. 따라서 3개월 동안 별도의 러시아 upstream 공급량 차질은 반영하지 않고, 선택된 국가·월 좌표에 0의 보수적 입력값을 적용한다. |
| 4 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 1 | PowerMix 조정 등을 통한 LNG 수요 감소량 ‘100%’는 필요 시 가스 발전 비중 조정을 통해 부족분을 흡수할 수 있음을 의미한다. 다만 이번 시나리오는 3개월의 낮은 강도·지연발생 리스크이고 대체 LNG 확보도 가능하므로, 연간 발전 믹스 입력에서는 중국 가스 비중을 기준 수준으로 유지하는 구조가 적절하다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.45 | 선택된 Arctic LNG 2 T1의 2026년 7월 좌표는 3개월 시나리오의 시작 월이며, 지연발생 조건상 즉시 가동률 저하를 반영하지 않았다. 기준값 0.45를 최종 입력값으로 유지한다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.45 | 2026년 8월은 지연발생 구간에 해당하고 공급 차질 강도도 낮으므로 기준 가동률을 변경하지 않았다. 기준값 0.45를 최종 입력값으로 유지한다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.4275 | 2026년 9월은 3개월 범위의 후반 월로, 제재·선박 확인 지연의 물량 영향이 일부 나타나는 시점으로 보았다. 낮은 강도 조건을 반영해 기준 가동률 0.45에서 5%만 하향하여 최종 입력값을 0.4275로 산정했다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.45 | 선택된 Arctic LNG 2 T2의 2026년 7월 좌표는 시나리오 초기 월이며, 지연발생 조건상 즉시 가동률 저하를 반영하지 않았다. 기준값 0.45를 최종 입력값으로 유지한다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.45 | 2026년 8월은 제재 영향이 아직 본격화되지 않는 지연발생 구간으로 보아 기준 가동률을 유지했다. 기준값 0.45를 최종 입력값으로 둔다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.4275 | 2026년 9월은 3개월 범위의 후반 월로, 낮은 수준의 제재·물류 제약이 가동률에 일부 반영되는 시점으로 보았다. 기준 가동률 0.45에 5% 하향을 적용해 최종 입력값을 0.4275로 산정했다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | null | 0.235125 | 운영 중인 Arctic LNG 2 T1의 2026년 9월은 지연발생 시나리오에서 생산 영향이 가장 먼저 반영될 수 있는 선택 좌표다. 명목능력 6.599999 MTPA를 월 환산하고 0.45 수준의 정상 가동을 기준으로 본 뒤, 낮은 강도의 후반 월 차질로 5%를 하향해 최종 생산량을 0.235125 Mt/month로 산정했다. |

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "Month": 7, "Year": 2026}` | null | 0 | 2026년 7월 러시아 좌표는 시나리오 시작 월이나, 사건 근거상 upstream 생산 차질이 확인되지 않고 지연발생 조건도 적용되므로 추가 공급 차질 입력을 0 Bcm로 둔다. |
| 2 | `{"Country": "Russia", "Month": 8, "Year": 2026}` | null | 0 | 2026년 8월 러시아 좌표는 3개월 범위의 중간 월이지만, 제재 이슈가 upstream 생산 손상으로 전이된 근거가 없으므로 추가 공급 차질 입력을 0 Bcm로 유지한다. |
| 3 | `{"Country": "Russia", "Month": 9, "Year": 2026}` | null | 0 | 2026년 9월은 후반 월이나, 낮은 강도와 대체 대응 가능성을 감안할 때 국가 단위 upstream 공급량 조정으로 반영할 만한 별도 차질은 명확하지 않다. 최종 입력값은 0 Bcm로 산정한다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0346 | 선택된 2026년 중국 Gas 발전 비중은 연간 좌표이며, 단기·낮은 강도의 제재 리스크는 연간 발전 믹스를 의미 있게 바꿀 정도로 크지 않다. 기준값 0.0346을 최종 입력값으로 유지한다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1177,
  "model_param_proposal_id": 52,
  "proposal_completed_dtm": "2026-07-07 17:38:44.044642",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "공급 차질 강도 ‘낮음’은 Arctic LNG 2 액화시설 가동률의 제한적 하향 요인으로 연결되며, 대체 LNG 확보 ‘100%’는 실물 부족을 완화하되 제재·선박 확인에 따른 가동 제약 자체를 완전히 제거하지는 않는 조건으로 해석했다. 기간은 3개월, 패턴은 지연발생-단계적 회복이므로 초기 월은 기준 가동률을 유지하고, 영향이 늦게 나타나는 후반 월에만 보수적으로 소폭 하향하는 구조로 제안한다.",
      "values": [
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "선택된 Arctic LNG 2 T1의 2026년 7월 좌표는 3개월 시나리오의 시작 월이며, 지연발생 조건상 즉시 가동률 저하를 반영하지 않았다. 기준값 0.45를 최종 입력값으로 유지한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "2026년 8월은 지연발생 구간에 해당하고 공급 차질 강도도 낮으므로 기준 가동률을 변경하지 않았다. 기준값 0.45를 최종 입력값으로 유지한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.4275,
          "rationale": "2026년 9월은 3개월 범위의 후반 월로, 제재·선박 확인 지연의 물량 영향이 일부 나타나는 시점으로 보았다. 낮은 강도 조건을 반영해 기준 가동률 0.45에서 5%만 하향하여 최종 입력값을 0.4275로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "선택된 Arctic LNG 2 T2의 2026년 7월 좌표는 시나리오 초기 월이며, 지연발생 조건상 즉시 가동률 저하를 반영하지 않았다. 기준값 0.45를 최종 입력값으로 유지한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "2026년 8월은 제재 영향이 아직 본격화되지 않는 지연발생 구간으로 보아 기준 가동률을 유지했다. 기준값 0.45를 최종 입력값으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.4275,
          "rationale": "2026년 9월은 3개월 범위의 후반 월로, 낮은 수준의 제재·물류 제약이 가동률에 일부 반영되는 시점으로 보았다. 기준 가동률 0.45에 5% 하향을 적용해 최종 입력값을 0.4275로 산정했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqProdAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqProdAdjustment"
        ]
      },
      "parameterName": "LiqProdAdjustment",
      "rationale": "공급 차질 강도 ‘낮음’은 Arctic LNG 2의 생산량 직접 감소 가능성과 연결되지만, 사건의 핵심은 생산설비 손상이 아니라 제재·무역 흐름 제약이다. 따라서 3개월 지연발생 패턴을 반영해 가장 직접적인 운영 트레인의 후반 월에만 소폭 생산량 하향을 적용하는 보수적 구조로 제안한다.",
      "values": [
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.235125,
          "rationale": "운영 중인 Arctic LNG 2 T1의 2026년 9월은 지연발생 시나리오에서 생산 영향이 가장 먼저 반영될 수 있는 선택 좌표다. 명목능력 6.599999 MTPA를 월 환산하고 0.45 수준의 정상 가동을 기준으로 본 뒤, 낮은 강도의 후반 월 차질로 5%를 하향해 최종 생산량을 0.235125 Mt/month로 산정했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "VolumeAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Volumes (Bcm)"
        ]
      },
      "parameterName": "SupplyDisruption",
      "rationale": "공급 차질 강도 ‘낮음’은 러시아 공급 차질 파라미터와 연결되지만, 본 사건은 upstream 생산 손상보다는 Arctic LNG 2의 제재·선박·거래 제한이 중심이다. 따라서 3개월 동안 별도의 러시아 upstream 공급량 차질은 반영하지 않고, 선택된 국가·월 좌표에 0의 보수적 입력값을 적용한다.",
      "values": [
        {
          "Country": "Russia",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "2026년 7월 러시아 좌표는 시나리오 시작 월이나, 사건 근거상 upstream 생산 차질이 확인되지 않고 지연발생 조건도 적용되므로 추가 공급 차질 입력을 0 Bcm로 둔다."
        },
        {
          "Country": "Russia",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "2026년 8월 러시아 좌표는 3개월 범위의 중간 월이지만, 제재 이슈가 upstream 생산 손상으로 전이된 근거가 없으므로 추가 공급 차질 입력을 0 Bcm로 유지한다."
        },
        {
          "Country": "Russia",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "2026년 9월은 후반 월이나, 낮은 강도와 대체 대응 가능성을 감안할 때 국가 단위 upstream 공급량 조정으로 반영할 만한 별도 차질은 명확하지 않다. 최종 입력값은 0 Bcm로 산정한다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Energy Source",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "PowerMix 조정 등을 통한 LNG 수요 감소량 ‘100%’는 필요 시 가스 발전 비중 조정을 통해 부족분을 흡수할 수 있음을 의미한다. 다만 이번 시나리오는 3개월의 낮은 강도·지연발생 리스크이고 대체 LNG 확보도 가능하므로, 연간 발전 믹스 입력에서는 중국 가스 비중을 기준 수준으로 유지하는 구조가 적절하다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0346,
          "rationale": "선택된 2026년 중국 Gas 발전 비중은 연간 좌표이며, 단기·낮은 강도의 제재 리스크는 연간 발전 믹스를 의미 있게 바꿀 정도로 크지 않다. 기준값 0.0346을 최종 입력값으로 유지한다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 22,
  "scenario_id": 129,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:08.518 | 8.518 | 2857 | 214 | 3071 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:12.506 | 72.506 | 12604 | 5773 | 18377 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:28.455 | 88.455 | 11933 | 5194 | 17127 |

#### scenario_id=130 1년 중반까지 완만한 조달 긴장 후 해소

- 소요시간: 05:29.765 (329.765s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "demand_response_alternative_lng": "50%",
    "demand_response_powermix_reduction": "50%",
    "period": "1년",
    "supply_disruption_intensity": "중간",
    "supply_disruption_pattern": "지연발생-즉시 해소"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "mild_bull"
  },
  "narrative": "기간은 1년, 공급 차질 강도는 중간으로 설정한다.\n패턴은 P6: Delayed onset - Sudden resolution으로, 제재 집행과 선박 운항 제약이 누적되다가 허가·우회 조달이 확인되며 급히 풀리는 흐름이다.\n대체 LNG 확보와 PowerMix 수요 절감은 각각 50%에 그쳐 구매자는 일부 현물 조달을 추가해야 한다.\n시장 참여자는 연중 일정 기간 아시아·유럽 간 카고 경쟁이 높아질 수 있다고 판단한다.",
  "probability_delta": 0.0,
  "probability_score": 22.0,
  "scenario_group_id": 22,
  "scenario_id": 130,
  "status": "creating",
  "title": "1년 중반까지 완만한 조달 긴장 후 해소"
}
```

##### Validation Summary

- expected_parameters: `["LiqUtilAdjustment", "LiqProdAdjustment", "SupplyDisruption", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "SupplyDisruption", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=18|supplydisruptionintensity|liqprodadjustment|supply|liqprodadjustment, sheet=LiqProdAdjustment", "basecase record를 추출하지 못했습니다: candidate_key=18|supplydisruptionintensity|supplydisruption|supply|volumeadjustment, sheet=VolumeAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=5, validated=4, final_selected=3, proposalParameters=3 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 70 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=29, basecaseValue_present=28 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 6 | 공급 차질 강도 '중간'은 액화시설 가동률 감소와 직접 연결되며, 타 공급원 경유 LNG 확보가 50%에 그쳐 제재에 따른 운항·거래 제약을 완전히 상쇄하지 못하는 조건이다. 기간과 패턴은 공통 맥락으로 반영해 초반 즉시 급락보다는 지연 발생 후 단기간 완화되는 구조로, 기준값이 확인되는 가동 구간에 보수적 하향 값을 적용한다. |
| 2 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 1 | 공급 차질 강도는 upstream 공급량 조정과 연결될 수 있지만, 사건의 핵심 경로는 upstream 생산 손실이 아니라 LNG 선박·결제·구매자 접근성 제약이다. 따라서 upstream 생산 차질은 별도로 확대하지 않는 보수적 구조로 두고, 명확한 직접 충격이 확인되는 최초 적용 구간에 무차질 값을 둔다. |
| 3 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 22 | PowerMix 조정을 통한 LNG 수요 감소 50%는 가스 발전 비중 하향과 직접 연결된다. 다만 공급 충격은 중간 강도이고 기간은 1년이며 가격 영향도 완만한 강세에 그치므로, 연간 gas share에는 과도한 절감이 아니라 절반 기간에 걸친 보수적 상대 하향을 적용한다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 105, "Year": 2026}` | 0.45 | 0.35 | 해당 좌표는 기준 가동률 0.45가 확인되는 2026년 9월 T1 가동 구간이다. 지연 발생 패턴을 반영해 7~8월 이후 제재·선박 제약이 누적되는 구간으로 보고, 중간 강도의 차질을 보수적으로 약 0.10p 하향해 최종 가동률을 0.35로 산정했다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 106, "Year": 2026}` | 0.45 | 0.35 | 해당 좌표는 기준 가동률 0.45가 확인되는 2026년 10월 T1 가동 구간이다. 대체 LNG 확보가 절반 수준에 머무르는 가운데 제재 집행과 운항 제약이 지속되는 구간으로 보아 기준 대비 약 0.10p 낮춘 0.35를 최종 입력값으로 적용했다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 107, "Year": 2026}` | 0.45 | 0.35 | 해당 좌표는 기준 가동률 0.45가 확인되는 2026년 11월 T1 가동 구간이다. 즉시 해소 전 마지막 제약 구간으로 해석해 중간 강도 차질을 반영하되, 완전 중단이 아닌 완만한 조달 긴장에 맞춰 최종 가동률을 0.35로 산정했다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 105, "Year": 2026}` | 0.45 | 0.35 | 해당 좌표는 기준 가동률 0.45가 확인되는 2026년 9월 T2 구간이다. 지연 발생 패턴에 따라 초반보다 이후 제약이 커지는 시점으로 보고, 중간 강도의 제재·운항 차질을 반영해 최종 가동률을 0.35로 하향했다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 106, "Year": 2026}` | 0.45 | 0.35 | 해당 좌표는 기준 가동률 0.45가 확인되는 2026년 10월 T2 구간이다. 대체 공급 확보가 부분적이고 제재 대상 화물의 거래 제약이 이어지는 구간으로 보아, 기준 대비 약 0.10p 낮춘 0.35를 최종 입력값으로 적용했다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 107, "Year": 2026}` | 0.45 | 0.35 | 해당 좌표는 기준 가동률 0.45가 확인되는 2026년 11월 T2 구간이다. sudden resolution 이전의 제약 지속 구간으로 해석하되 충격 강도는 중간이고 시장 가격 영향도 mild bullish에 그치므로, 완전 차질이 아닌 0.35의 보수적 하향 가동률을 적용했다. |

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "Month": 7, "Year": 2026}` | null | 0 | 해당 좌표는 1년 시나리오의 시작 월이자 러시아 upstream 공급 조정의 최초 적용 구간이다. 사건 설명상 물리적 upstream 생산 중단이 아니라 LNG 무역·운송 제약이 핵심이므로, upstream 공급 차질 물량은 추가 반영하지 않고 최종 입력값을 0 Bcm로 설정했다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.033735 | 해당 좌표는 2026년 중국 Gas 발전 비중 기준값 0.0346이 확인되는 연간 슬롯이다. 1년 충격이 하반기부터 시작되고 PowerMix 대응이 절반 수준인 점을 반영해 연간 gas share를 기준 대비 2.5% 상대 하향하여 0.033735로 산정했다. |
| 2 | `{"Country": "China", "Energy Source": "Gas", "Year": 2027}` | 0.0365 | 0.0355875 | 해당 좌표는 2027년 중국 Gas 발전 비중 기준값 0.0365가 확인되는 연간 슬롯이다. 충격이 상반기까지 이어진 뒤 해소되는 구조를 연간 기준으로 반영해 기준 대비 2.5% 상대 하향한 0.0355875를 적용했다. |
| 3 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.314925 | 해당 좌표는 2026년 일본 Gas 발전 비중 기준값 0.323이 확인되는 연간 슬롯이다. 일부 현물 조달 필요와 PowerMix 수요 절감 50%를 반영하되 완만한 충격으로 보아 기준 대비 2.5% 상대 하향한 0.314925를 최종값으로 설정했다. |
| 4 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2027}` | 0.318 | 0.31005 | 해당 좌표는 2027년 일본 Gas 발전 비중 기준값 0.318이 확인되는 연간 슬롯이다. 1년 시나리오의 잔여 상반기 영향과 즉시 해소 조건을 연간화해 기준 대비 2.5% 낮춘 0.31005를 적용했다. |
| 5 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.277875 | 해당 좌표는 2026년 한국 Gas 발전 비중 기준값 0.285가 확인되는 연간 슬롯이다. 대체 LNG와 PowerMix 절감이 각각 절반 수준이어서 일부 가스 발전 축소가 필요하다고 보고, 기준 대비 2.5% 상대 하향한 0.277875를 산정했다. |
| 6 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2027}` | 0.265 | 0.258375 | 해당 좌표는 2027년 한국 Gas 발전 비중 기준값 0.265가 확인되는 연간 슬롯이다. 시나리오가 상반기 내 해소되는 흐름이므로 연간 충격은 제한적으로 반영해 기준 대비 2.5% 낮춘 0.258375를 적용했다. |
| 7 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2026}` | 0.474 | 0.46215 | 해당 좌표는 2026년 Taiwan (China) Gas 발전 비중 기준값 0.474가 확인되는 연간 슬롯이다. LNG 조달 긴장에 따른 PowerMix 절감 필요를 반영하되 완만한 충격으로 보아 기준 대비 2.5% 상대 하향한 0.46215를 최종값으로 적용했다. |
| 8 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2027}` | 0.495 | 0.482625 | 해당 좌표는 2027년 Taiwan (China) Gas 발전 비중 기준값 0.495가 확인되는 연간 슬롯이다. 1년 충격의 잔여 영향과 빠른 해소를 함께 반영해 기준 대비 2.5% 낮춘 0.482625로 산정했다. |
| 9 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.131625 | 해당 좌표는 2026년 독일 Gas 발전 비중 기준값 0.135가 확인되는 연간 슬롯이다. 유럽 내 대체 공급 프리미엄과 카고 경쟁 가능성을 반영하되 mild bullish 수준에 맞춰 기준 대비 2.5% 상대 하향한 0.131625를 적용했다. |
| 10 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2027}` | 0.13 | 0.12675 | 해당 좌표는 2027년 독일 Gas 발전 비중 기준값 0.13이 확인되는 연간 슬롯이다. 상반기까지 제한적으로 이어지는 수요 절감 대응을 연간화해 기준 대비 2.5% 낮춘 0.12675를 최종 입력값으로 산정했다. |
| 11 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.04095 | 해당 좌표는 2026년 프랑스 Gas 발전 비중 기준값 0.042가 확인되는 연간 슬롯이다. PowerMix 조정에 따른 LNG 수요 절감을 반영하되 전체 충격은 완만하므로 기준 대비 2.5% 상대 하향한 0.04095를 적용했다. |
| 12 | `{"Country": "France", "Energy Source": "Gas", "Year": 2027}` | 0.034 | 0.03315 | 해당 좌표는 2027년 프랑스 Gas 발전 비중 기준값 0.034가 확인되는 연간 슬롯이다. 해소 전 잔여 기간의 제한적 조정만 반영해 기준 대비 2.5% 낮춘 0.03315를 최종값으로 산정했다. |
| 13 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.42315 | 해당 좌표는 2026년 이탈리아 Gas 발전 비중 기준값 0.434가 확인되는 연간 슬롯이다. 조달 긴장에 따른 가스 발전 축소 필요를 반영하되 충격 강도와 완화 수단을 감안해 기준 대비 2.5% 상대 하향한 0.42315를 적용했다. |
| 14 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2027}` | 0.422 | 0.41145 | 해당 좌표는 2027년 이탈리아 Gas 발전 비중 기준값 0.422가 확인되는 연간 슬롯이다. 시나리오의 상반기 잔여 영향을 연간 기준으로 보수적으로 반영해 기준 대비 2.5% 낮춘 0.41145를 산정했다. |
| 15 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.207675 | 해당 좌표는 2026년 스페인 Gas 발전 비중 기준값 0.213이 확인되는 연간 슬롯이다. 부분적인 PowerMix 절감 대응을 반영하되 과도한 수요 파괴는 가정하지 않아 기준 대비 2.5% 상대 하향한 0.207675를 적용했다. |
| 16 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2027}` | 0.211 | 0.205725 | 해당 좌표는 2027년 스페인 Gas 발전 비중 기준값 0.211이 확인되는 연간 슬롯이다. 충격이 즉시 해소되는 후반 구조를 감안해 제한적인 연간 조정만 반영하고, 기준 대비 2.5% 낮춘 0.205725를 산정했다. |
| 17 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.3102349137931034 | 해당 좌표는 2026년 네덜란드 Gas 발전 비중 기준값 0.31818965517241377이 확인되는 연간 슬롯이다. 유럽 내 LNG 조달 경쟁 심화 가능성을 반영하되 완만한 충격에 맞춰 기준 대비 2.5% 상대 하향한 0.31023491379310343을 적용했다. |
| 18 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2027}` | 0.33707317073170734 | 0.32864634146341465 | 해당 좌표는 2027년 네덜란드 Gas 발전 비중 기준값 0.33707317073170734가 확인되는 연간 슬롯이다. 상반기 잔여 영향과 해소 조건을 반영해 기준 대비 2.5% 낮춘 0.32864634146341466을 최종값으로 산정했다. |
| 19 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.18525 | 해당 좌표는 2026년 벨기에 Gas 발전 비중 기준값 0.19가 확인되는 연간 슬롯이다. PowerMix를 통한 LNG 수요 절감 50%를 반영하되 mild bullish 수준에 맞춰 기준 대비 2.5% 상대 하향한 0.18525를 적용했다. |
| 20 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2027}` | 0.18 | 0.1755 | 해당 좌표는 2027년 벨기에 Gas 발전 비중 기준값 0.18이 확인되는 연간 슬롯이다. 시나리오 종료 전 잔여 기간의 수요 절감만 제한적으로 반영해 기준 대비 2.5% 낮춘 0.1755를 산정했다. |
| 21 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.28275 | 해당 좌표는 2026년 영국 Gas 발전 비중 기준값 0.29가 확인되는 연간 슬롯이다. 유럽 가스·LNG 조달 긴장에 따른 발전용 가스 수요 절감을 반영하되, 중간 강도와 절반 수준 대응을 감안해 기준 대비 2.5% 상대 하향한 0.28275를 적용했다. |
| 22 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2027}` | 0.29 | 0.28275 | 해당 좌표는 2027년 영국 Gas 발전 비중 기준값 0.29가 확인되는 연간 슬롯이다. 상반기까지 남는 조달 긴장과 즉시 해소 조건을 연간화해 기준 대비 2.5% 낮춘 0.28275를 최종 입력값으로 산정했다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1177,
  "model_param_proposal_id": 56,
  "proposal_completed_dtm": "2026-07-07 17:41:17.819185",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "LiqUtilAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "LNG Plant",
          "LNG Plant Train",
          "Life Cycle Category",
          "Nameplate Capacity (MTPA)",
          "Year",
          "Month",
          "Period"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "LiqUtilAdjustment"
        ]
      },
      "parameterName": "LiqUtilAdjustment",
      "rationale": "공급 차질 강도 '중간'은 액화시설 가동률 감소와 직접 연결되며, 타 공급원 경유 LNG 확보가 50%에 그쳐 제재에 따른 운항·거래 제약을 완전히 상쇄하지 못하는 조건이다. 기간과 패턴은 공통 맥락으로 반영해 초반 즉시 급락보다는 지연 발생 후 단기간 완화되는 구조로, 기준값이 확인되는 가동 구간에 보수적 하향 값을 적용한다.",
      "values": [
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.35,
          "rationale": "해당 좌표는 기준 가동률 0.45가 확인되는 2026년 9월 T1 가동 구간이다. 지연 발생 패턴을 반영해 7~8월 이후 제재·선박 제약이 누적되는 구간으로 보고, 중간 강도의 차질을 보수적으로 약 0.10p 하향해 최종 가동률을 0.35로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 106,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.35,
          "rationale": "해당 좌표는 기준 가동률 0.45가 확인되는 2026년 10월 T1 가동 구간이다. 대체 LNG 확보가 절반 수준에 머무르는 가운데 제재 집행과 운항 제약이 지속되는 구간으로 보아 기준 대비 약 0.10p 낮춘 0.35를 최종 입력값으로 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 107,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.35,
          "rationale": "해당 좌표는 기준 가동률 0.45가 확인되는 2026년 11월 T1 가동 구간이다. 즉시 해소 전 마지막 제약 구간으로 해석해 중간 강도 차질을 반영하되, 완전 중단이 아닌 완만한 조달 긴장에 맞춰 최종 가동률을 0.35로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.35,
          "rationale": "해당 좌표는 기준 가동률 0.45가 확인되는 2026년 9월 T2 구간이다. 지연 발생 패턴에 따라 초반보다 이후 제약이 커지는 시점으로 보고, 중간 강도의 제재·운항 차질을 반영해 최종 가동률을 0.35로 하향했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 106,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.35,
          "rationale": "해당 좌표는 기준 가동률 0.45가 확인되는 2026년 10월 T2 구간이다. 대체 공급 확보가 부분적이고 제재 대상 화물의 거래 제약이 이어지는 구간으로 보아, 기준 대비 약 0.10p 낮춘 0.35를 최종 입력값으로 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 107,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.35,
          "rationale": "해당 좌표는 기준 가동률 0.45가 확인되는 2026년 11월 T2 구간이다. sudden resolution 이전의 제약 지속 구간으로 해석하되 충격 강도는 중간이고 시장 가격 영향도 mild bullish에 그치므로, 완전 차질이 아닌 0.35의 보수적 하향 가동률을 적용했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Supply",
        "modelSheet": "VolumeAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Volumes (Bcm)"
        ]
      },
      "parameterName": "SupplyDisruption",
      "rationale": "공급 차질 강도는 upstream 공급량 조정과 연결될 수 있지만, 사건의 핵심 경로는 upstream 생산 손실이 아니라 LNG 선박·결제·구매자 접근성 제약이다. 따라서 upstream 생산 차질은 별도로 확대하지 않는 보수적 구조로 두고, 명확한 직접 충격이 확인되는 최초 적용 구간에 무차질 값을 둔다.",
      "values": [
        {
          "Country": "Russia",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "해당 좌표는 1년 시나리오의 시작 월이자 러시아 upstream 공급 조정의 최초 적용 구간이다. 사건 설명상 물리적 upstream 생산 중단이 아니라 LNG 무역·운송 제약이 핵심이므로, upstream 공급 차질 물량은 추가 반영하지 않고 최종 입력값을 0 Bcm로 설정했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PowerMixAdjustment",
        "slotAxesFieldNames": [
          "Country",
          "Energy Source",
          "Year"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% Power Mix"
        ]
      },
      "parameterName": "PowerMix",
      "rationale": "PowerMix 조정을 통한 LNG 수요 감소 50%는 가스 발전 비중 하향과 직접 연결된다. 다만 공급 충격은 중간 강도이고 기간은 1년이며 가격 영향도 완만한 강세에 그치므로, 연간 gas share에는 과도한 절감이 아니라 절반 기간에 걸친 보수적 상대 하향을 적용한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.033735,
          "rationale": "해당 좌표는 2026년 중국 Gas 발전 비중 기준값 0.0346이 확인되는 연간 슬롯이다. 1년 충격이 하반기부터 시작되고 PowerMix 대응이 절반 수준인 점을 반영해 연간 gas share를 기준 대비 2.5% 상대 하향하여 0.033735로 산정했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.0365,
          "proposedValue": 0.0355875,
          "rationale": "해당 좌표는 2027년 중국 Gas 발전 비중 기준값 0.0365가 확인되는 연간 슬롯이다. 충격이 상반기까지 이어진 뒤 해소되는 구조를 연간 기준으로 반영해 기준 대비 2.5% 상대 하향한 0.0355875를 적용했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.314925,
          "rationale": "해당 좌표는 2026년 일본 Gas 발전 비중 기준값 0.323이 확인되는 연간 슬롯이다. 일부 현물 조달 필요와 PowerMix 수요 절감 50%를 반영하되 완만한 충격으로 보아 기준 대비 2.5% 상대 하향한 0.314925를 최종값으로 설정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.318,
          "proposedValue": 0.31005,
          "rationale": "해당 좌표는 2027년 일본 Gas 발전 비중 기준값 0.318이 확인되는 연간 슬롯이다. 1년 시나리오의 잔여 상반기 영향과 즉시 해소 조건을 연간화해 기준 대비 2.5% 낮춘 0.31005를 적용했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.277875,
          "rationale": "해당 좌표는 2026년 한국 Gas 발전 비중 기준값 0.285가 확인되는 연간 슬롯이다. 대체 LNG와 PowerMix 절감이 각각 절반 수준이어서 일부 가스 발전 축소가 필요하다고 보고, 기준 대비 2.5% 상대 하향한 0.277875를 산정했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.265,
          "proposedValue": 0.258375,
          "rationale": "해당 좌표는 2027년 한국 Gas 발전 비중 기준값 0.265가 확인되는 연간 슬롯이다. 시나리오가 상반기 내 해소되는 흐름이므로 연간 충격은 제한적으로 반영해 기준 대비 2.5% 낮춘 0.258375를 적용했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.474,
          "proposedValue": 0.46215,
          "rationale": "해당 좌표는 2026년 Taiwan (China) Gas 발전 비중 기준값 0.474가 확인되는 연간 슬롯이다. LNG 조달 긴장에 따른 PowerMix 절감 필요를 반영하되 완만한 충격으로 보아 기준 대비 2.5% 상대 하향한 0.46215를 최종값으로 적용했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.495,
          "proposedValue": 0.482625,
          "rationale": "해당 좌표는 2027년 Taiwan (China) Gas 발전 비중 기준값 0.495가 확인되는 연간 슬롯이다. 1년 충격의 잔여 영향과 빠른 해소를 함께 반영해 기준 대비 2.5% 낮춘 0.482625로 산정했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.131625,
          "rationale": "해당 좌표는 2026년 독일 Gas 발전 비중 기준값 0.135가 확인되는 연간 슬롯이다. 유럽 내 대체 공급 프리미엄과 카고 경쟁 가능성을 반영하되 mild bullish 수준에 맞춰 기준 대비 2.5% 상대 하향한 0.131625를 적용했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.12675,
          "rationale": "해당 좌표는 2027년 독일 Gas 발전 비중 기준값 0.13이 확인되는 연간 슬롯이다. 상반기까지 제한적으로 이어지는 수요 절감 대응을 연간화해 기준 대비 2.5% 낮춘 0.12675를 최종 입력값으로 산정했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04095,
          "rationale": "해당 좌표는 2026년 프랑스 Gas 발전 비중 기준값 0.042가 확인되는 연간 슬롯이다. PowerMix 조정에 따른 LNG 수요 절감을 반영하되 전체 충격은 완만하므로 기준 대비 2.5% 상대 하향한 0.04095를 적용했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03315,
          "rationale": "해당 좌표는 2027년 프랑스 Gas 발전 비중 기준값 0.034가 확인되는 연간 슬롯이다. 해소 전 잔여 기간의 제한적 조정만 반영해 기준 대비 2.5% 낮춘 0.03315를 최종값으로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.42315,
          "rationale": "해당 좌표는 2026년 이탈리아 Gas 발전 비중 기준값 0.434가 확인되는 연간 슬롯이다. 조달 긴장에 따른 가스 발전 축소 필요를 반영하되 충격 강도와 완화 수단을 감안해 기준 대비 2.5% 상대 하향한 0.42315를 적용했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.41145,
          "rationale": "해당 좌표는 2027년 이탈리아 Gas 발전 비중 기준값 0.422가 확인되는 연간 슬롯이다. 시나리오의 상반기 잔여 영향을 연간 기준으로 보수적으로 반영해 기준 대비 2.5% 낮춘 0.41145를 산정했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.207675,
          "rationale": "해당 좌표는 2026년 스페인 Gas 발전 비중 기준값 0.213이 확인되는 연간 슬롯이다. 부분적인 PowerMix 절감 대응을 반영하되 과도한 수요 파괴는 가정하지 않아 기준 대비 2.5% 상대 하향한 0.207675를 적용했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.205725,
          "rationale": "해당 좌표는 2027년 스페인 Gas 발전 비중 기준값 0.211이 확인되는 연간 슬롯이다. 충격이 즉시 해소되는 후반 구조를 감안해 제한적인 연간 조정만 반영하고, 기준 대비 2.5% 낮춘 0.205725를 산정했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3102349137931034,
          "rationale": "해당 좌표는 2026년 네덜란드 Gas 발전 비중 기준값 0.31818965517241377이 확인되는 연간 슬롯이다. 유럽 내 LNG 조달 경쟁 심화 가능성을 반영하되 완만한 충격에 맞춰 기준 대비 2.5% 상대 하향한 0.31023491379310343을 적용했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.32864634146341465,
          "rationale": "해당 좌표는 2027년 네덜란드 Gas 발전 비중 기준값 0.33707317073170734가 확인되는 연간 슬롯이다. 상반기 잔여 영향과 해소 조건을 반영해 기준 대비 2.5% 낮춘 0.32864634146341466을 최종값으로 산정했다."
        },
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.18525,
          "rationale": "해당 좌표는 2026년 벨기에 Gas 발전 비중 기준값 0.19가 확인되는 연간 슬롯이다. PowerMix를 통한 LNG 수요 절감 50%를 반영하되 mild bullish 수준에 맞춰 기준 대비 2.5% 상대 하향한 0.18525를 적용했다."
        },
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1755,
          "rationale": "해당 좌표는 2027년 벨기에 Gas 발전 비중 기준값 0.18이 확인되는 연간 슬롯이다. 시나리오 종료 전 잔여 기간의 수요 절감만 제한적으로 반영해 기준 대비 2.5% 낮춘 0.1755를 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "해당 좌표는 2026년 영국 Gas 발전 비중 기준값 0.29가 확인되는 연간 슬롯이다. 유럽 가스·LNG 조달 긴장에 따른 발전용 가스 수요 절감을 반영하되, 중간 강도와 절반 수준 대응을 감안해 기준 대비 2.5% 상대 하향한 0.28275를 적용했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "해당 좌표는 2027년 영국 Gas 발전 비중 기준값 0.29가 확인되는 연간 슬롯이다. 상반기까지 남는 조달 긴장과 즉시 해소 조건을 연간화해 기준 대비 2.5% 낮춘 0.28275를 최종 입력값으로 산정했다."
        }
      ]
    }
  ],
  "request_usr_id": 1000085,
  "scenario_group_id": 22,
  "scenario_id": 130,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.551 | 4.551 | 2866 | 217 | 3083 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:46.253 | 106.253 | 12613 | 10399 | 23012 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:15.320 | 195.320 | 15274 | 8006 | 23280 |

### event_type_l2_id=19 정책/규제 변화

#### Scenario Group

```json
{
  "description": "IMO 운송 규제 이벤트에서 ShippingCost 계열 파라미터가 선택되고 강도별 value가 달라지는지 검증한다.",
  "dimension_selected": [
    "period",
    "implementation_stage",
    "impact_intensity",
    "structural_change_yn"
  ],
  "event_type": {
    "event_type_l1_id": 4,
    "event_type_l2_id": 19,
    "level_1_code": "exogenous_shock",
    "level_1_label": "외생충격",
    "level_2_code": "policy_regulatory_change",
    "level_2_label": "정책/규제 변화"
  },
  "event_type_l2_id": 19,
  "mi_event_id": 1155,
  "request_usr_id": null,
  "scenario_count": 2,
  "scenario_group_id": 48,
  "stage": "scenario_created",
  "status": "created",
  "summary": "model_parameter_agent routing 검증용 정책/규제 scenario_group",
  "title": "[model_parameter_agent_test] 정책/규제 routing 검증"
}
```

#### Dimension Template

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
    "dim_key": "implementation_stage",
    "display_order": 2,
    "label": "시행 확실성·단계",
    "required": true,
    "value_enums": [
      "검토/루머",
      "발표",
      "시행 확정",
      "단계적 시행"
    ]
  },
  {
    "dim_key": "impact_intensity",
    "display_order": 3,
    "label": "영향 강도",
    "required": false,
    "value_enums": [
      "경미",
      "보통",
      "큼"
    ]
  },
  {
    "dim_key": "structural_change_yn",
    "display_order": 4,
    "label": "구조적 변동 여부",
    "required": false,
    "value_enums": [
      "단발적/한시",
      "구조적/영구"
    ]
  }
]
```

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": null,
      "comment": "발전·수요 정책 (탄소·전환 등) : User-Adjusted Gas Demand 미대상 수동 overwrite는 쓰지 않고, 발전·수요 정책은 PowerMix/CoalGasAdjustment 등 대상 파라미터로만 라우팅",
      "dimension_key": "impact_intensity",
      "dimension_label": "영향 강도",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "보통",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "큼",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "수출입 규제(관세·금수) : 관세·금수 등 TradeRestrictionInput 미대상 항목은 직접 반영하지 않고, 실제 물량 차질이 명확할 때 Supply 파라미터로 별도 반영",
      "dimension_key": "impact_intensity",
      "dimension_label": "영향 강도",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "보통",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "큼",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "운송 규제(FuelEU 등) : 운송 규제·비용은 ShippingCost 미대상이라 직접 반영하지 않고, 물리적 운송 지연·제약이 공급량에 연결될 때만 기간·강도 판단에 사용",
      "dimension_key": "impact_intensity",
      "dimension_label": "영향 강도",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "보통",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "큼",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "Coal Futures Price",
      "comment": "정책 영향 라우팅 후보(3개 중 선택) : 석탄 가격·세금·보조금·수입규제 등으로 석탄 발전 경제성이 변해 Gas↔Coal 전환 유인이 생기면 Coal Futures Price 선택",
      "dimension_key": "impact_intensity",
      "dimension_label": "영향 강도",
      "mapping_method": "routing",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "CoalGasAdjustment",
        "model_table": "table1",
        "semantic_axes": "석탄 선물가격 strip — 지역·월 (Asia=Newcastle, EU=ARA)"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "보통",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "큼",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "Gas Futures Price",
      "comment": "정책 영향 라우팅 후보(3개 중 선택) : 가스/LNG 가격·세금·보조금·구매규제 등으로 가스 발전 경제성이 변해 Gas↔Coal 전환 유인이 생기면 Gas Futures Price 선택",
      "dimension_key": "impact_intensity",
      "dimension_label": "영향 강도",
      "mapping_method": "routing",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "CoalGasAdjustment",
        "model_table": "table2",
        "semantic_axes": "가스 선물가격 strip — 지역·월 (Asia=JKM, EU=TTF)"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "보통",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "큼",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PowerMix",
      "comment": "정책 영향 라우팅 후보(3개 중 선택) : 전원믹스·탄소규제·발전설비·연료전환 정책처럼 Gas/Coal/원전/재생 비중이 구조적으로 바뀌면 PowerMix 선택",
      "dimension_key": "impact_intensity",
      "dimension_label": "영향 강도",
      "mapping_method": "routing",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PowerMixAdjustment",
        "model_table": "table1",
        "semantic_axes": "발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/…)·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "보통",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "큼",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "검토/루머~시행 — 반영 시점·확률 weighting",
      "dimension_key": "implementation_stage",
      "dimension_label": "시행 확실성·단계",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "시행 확정",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "시행 확정",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "시간축",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "3개월",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "1년",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "단발/한시 vs 구조적/영구",
      "dimension_key": "structural_change_yn",
      "dimension_label": "구조적 변동 여부",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "단발적/한시",
          "scenario_id": 281,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "구조적/영구",
          "scenario_id": 282,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    }
  ],
  "event_type_l2_id": 19,
  "mapping_count": 9,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

#### Event

```json
{
  "created_at": "2026-06-19T23:18:59.770700",
  "detail_analysis": "사건 요약:\nIMO Net-Zero Framework의 채택 일정과 회원국별 입장 차이가 기존 핵심 사건으로 유지됨. 그리스의 회의적 입장, EU·미국·사우디 등 회원국 간 견해 차이, 향후 결정 회의의 불확실성이 주요 내용임. 2026-06-01 Platts Daily Report는 호르무즈발 공급 제약, 강한 운임, 타이트한 LNG-TTF basis, EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달, 아시아와 유럽의 카고 경쟁을 당일 LNG 시장 요인으로 제시함. 신규 연결 Record는 기존 요약에 이미 반영된 2026-06-01 시장 환경 업데이트와 동일한 내용으로, IMO Net-Zero Framework 정책 논의 자체의 추가 상태 변경은 확인되지 않음.\n\n영향 경로:\n국제 해운 온실가스 배출 비용 부과와 저탄소 연료 전환 유도는 선박 운항비 구조에 영향을 주는 정책 변수임. LNG선 연료 선택과 bio-LNG 등 저탄소 연료 가격에도 영향을 줄 수 있음. 2026-06-01 보고서의 강한 운임은 LNG 운송비 민감도를 보여주는 배경 자료이나, 호르무즈발 공급 제약과 카고 경쟁이 함께 언급된 만큼 IMO 규제의 직접 효과로 해석하지 않는 것이 적절함. EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달은 물동량과 수급 경쟁을 통해 운임 및 basis에 영향을 줄 수 있는 별도 Fundamental 요인임.\n\n시장 반응:\n규제 불확실성은 단기 현물 LNG 가격보다 중장기 운임과 선박 연료비 프리미엄에 반영될 가능성이 큰 변수임. 2026-06-01 Platts Daily Report에서는 호르무즈발 공급 제약과 강한 운임, 타이트한 LNG-TTF basis가 대서양 LNG 가격을 끌어올린 것으로 언급됨. 이 가격 상승은 IMO Net-Zero Framework 논의의 직접 시장 반응이 아니라 공급 제약, 운임, basis, 저장률, 조달 경쟁이 결합된 당일 시장 움직임임. 정책 프레임워크 채택이 구체화될수록 중장기 운송비 상승 기대가 강화될 수 있음.\n\nLNG 시장 관점:\n해당 Event의 경계는 IMO Net-Zero Framework와 해운 탄소비용 논의에 있음. LNG 화물 자체보다 해운 규제와 운송비 경로를 통한 간접 영향이 핵심임. 2026-06-01 Platts Daily Report의 대서양 LNG 가격 상승, EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달은 LNG 수급·가격 환경 설명으로 유용하나, 본 Event의 정책·규제 변화 범위를 넘는 별도 하위 사건이 섞여 있음. 따라서 신규 내용은 운임과 가격 민감도 배경으로 제한 반영하는 것이 적절함.",
  "event_title_ko": "IMO Net-Zero Framework 논의",
  "event_type_l2_id": 19,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-01T00:00:00",
  "mi_event_id": "1155",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[해운 규제] IMO 탄소비용 논의 지속 → LNG 운송비·연료비 변수 유지",
  "source_mi_record_ids": [
    2271
  ],
  "tags": []
}
```

#### Group Test Summary

- 대상 scenario_ids: [281, 282]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: PASS
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=281 [model_parameter_agent_test] IMO 운송 규제 보통 강도

- 소요시간: 01:26.341 (86.341s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "impact_intensity": "보통",
    "implementation_stage": "시행 확정",
    "period": "3개월",
    "structural_change_yn": "단발적/한시"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "IMO Net-Zero Framework가 시행 확정되지만 한시적 비용 전가에 그쳐 3개월 동안 LNG 운송비 프리미엄이 보통 수준으로 확대된다.",
  "probability_delta": 4.0,
  "probability_score": 45.0,
  "scenario_group_id": 48,
  "scenario_id": 281,
  "status": "created",
  "title": "[model_parameter_agent_test] IMO 운송 규제 보통 강도"
}
```

##### Validation Summary

- expected_parameters: `["Gas Futures Price"]`
- selected_parameters: `["Gas Futures Price"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: PASS
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=19|impactintensity|gasfuturesprice|demand|coalgasadjustment, sheet=CoalGasAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=0 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=0, distinct_axis_values=0 | PASS |
| Step2 selected slot | 6 | PASS |
| Step3 basecase 샘플 | prompt_records=0, limit=100 | PASS |
| Step3 value 결과 | value_cells=6, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Gas Futures Price | `{"modelFile": "Demand", "modelSheet": "CoalGasAdjustment", "tableName": "table2"}` | `["Month-Year", "Region"]` | `["Gas Futures Price (USD/mmbtu)"]` | 6 | 영향 강도 차원이 '보통'으로 제시되어 정책·규제에 따른 LNG 운송비 프리미엄이 가스/LNG 가격 경로에 반영될 수 있고, 해당 parameter는 지역별 월간 가스 선물가격을 입력하는 항목이므로 선택된다. 기간은 3개월, 시행은 확정, 구조는 단발적/한시로 해석해 Asia와 EU의 2026년 7~9월 스트립에만 보수적인 상승 가격 레벨을 적용하고, HH는 대상 축에 없으므로 반영하지 않는다. |

##### Proposed Parameter Values

###### Proposed Values - Gas Futures Price

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month-Year": "2026-07", "Region": "Asia"}` | null | 12.0 | 2026-07 Asia 슬롯은 시나리오 적용 시작월이자 JKM 상승 영향 대상이다. 기준값 레코드가 제공되지 않았으므로, 보통 강도의 한시적 운송비 프리미엄이 포함된 보수적 최종 선물가격 레벨로 12.0 USD/mmbtu를 적용한다. |
| 2 | `{"Month-Year": "2026-08", "Region": "Asia"}` | null | 12.0 | 2026-08 Asia 슬롯은 3개월 영향 기간의 두 번째 월에 해당한다. 단발적 비용 전가가 지속되지만 추가 확대 근거는 없으므로 2026-07과 같은 보수적 최종 가격 레벨인 12.0 USD/mmbtu를 유지한다. |
| 3 | `{"Month-Year": "2026-09", "Region": "Asia"}` | null | 12.0 | 2026-09 Asia 슬롯은 3개월 한시 영향의 마지막 월이다. 영향 강도는 보통이나 구조적 변동은 아니므로 기간 말에도 추가 누적 상승 없이 12.0 USD/mmbtu의 최종 입력값을 적용한다. |
| 4 | `{"Month-Year": "2026-07", "Region": "EU"}` | null | 10.5 | 2026-07 EU 슬롯은 TTF 상승 영향 대상이며, 운송비 프리미엄과 타이트한 LNG-TTF basis 배경을 반영한다. 기준값 레코드가 없으므로 Asia보다 낮은 보수적 최종 선물가격 레벨로 10.5 USD/mmbtu를 적용한다. |
| 5 | `{"Month-Year": "2026-08", "Region": "EU"}` | null | 10.5 | 2026-08 EU 슬롯은 3개월 영향 기간 내에 포함된다. 시행 확정에 따른 운송비 프리미엄은 유지하되 추가 심화 근거가 없으므로 2026-07과 동일한 10.5 USD/mmbtu를 최종 입력값으로 둔다. |
| 6 | `{"Month-Year": "2026-09", "Region": "EU"}` | null | 10.5 | 2026-09 EU 슬롯은 한시적 규제 비용 전가 기간의 마지막 월이다. 구조적 가격 재평가가 아닌 단발적 영향으로 해석해 10.5 USD/mmbtu의 보수적 최종 가격 레벨을 유지한다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1155,
  "model_param_proposal_id": 51,
  "proposal_completed_dtm": "2026-07-07 17:37:41.832987",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "CoalGasAdjustment",
        "slotAxesFieldNames": [
          "Month-Year",
          "Region"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Gas Futures Price (USD/mmbtu)"
        ]
      },
      "parameterName": "Gas Futures Price",
      "rationale": "영향 강도 차원이 '보통'으로 제시되어 정책·규제에 따른 LNG 운송비 프리미엄이 가스/LNG 가격 경로에 반영될 수 있고, 해당 parameter는 지역별 월간 가스 선물가격을 입력하는 항목이므로 선택된다. 기간은 3개월, 시행은 확정, 구조는 단발적/한시로 해석해 Asia와 EU의 2026년 7~9월 스트립에만 보수적인 상승 가격 레벨을 적용하고, HH는 대상 축에 없으므로 반영하지 않는다.",
      "values": [
        {
          "Month-Year": "2026-07",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 12.0,
          "rationale": "2026-07 Asia 슬롯은 시나리오 적용 시작월이자 JKM 상승 영향 대상이다. 기준값 레코드가 제공되지 않았으므로, 보통 강도의 한시적 운송비 프리미엄이 포함된 보수적 최종 선물가격 레벨로 12.0 USD/mmbtu를 적용한다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 12.0,
          "rationale": "2026-08 Asia 슬롯은 3개월 영향 기간의 두 번째 월에 해당한다. 단발적 비용 전가가 지속되지만 추가 확대 근거는 없으므로 2026-07과 같은 보수적 최종 가격 레벨인 12.0 USD/mmbtu를 유지한다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 12.0,
          "rationale": "2026-09 Asia 슬롯은 3개월 한시 영향의 마지막 월이다. 영향 강도는 보통이나 구조적 변동은 아니므로 기간 말에도 추가 누적 상승 없이 12.0 USD/mmbtu의 최종 입력값을 적용한다."
        },
        {
          "Month-Year": "2026-07",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 10.5,
          "rationale": "2026-07 EU 슬롯은 TTF 상승 영향 대상이며, 운송비 프리미엄과 타이트한 LNG-TTF basis 배경을 반영한다. 기준값 레코드가 없으므로 Asia보다 낮은 보수적 최종 선물가격 레벨로 10.5 USD/mmbtu를 적용한다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 10.5,
          "rationale": "2026-08 EU 슬롯은 3개월 영향 기간 내에 포함된다. 시행 확정에 따른 운송비 프리미엄은 유지하되 추가 심화 근거가 없으므로 2026-07과 동일한 10.5 USD/mmbtu를 최종 입력값으로 둔다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 10.5,
          "rationale": "2026-09 EU 슬롯은 한시적 규제 비용 전가 기간의 마지막 월이다. 구조적 가격 재평가가 아닌 단발적 영향으로 해석해 10.5 USD/mmbtu의 보수적 최종 가격 레벨을 유지한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 48,
  "scenario_id": 281,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:07.255 | 7.255 | 2627 | 333 | 2960 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:13.001 | 13.001 | 5323 | 799 | 6122 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:50.544 | 50.544 | 5256 | 1818 | 7074 |

#### scenario_id=282 [model_parameter_agent_test] IMO 운송 규제 큰 강도

- 소요시간: 01:26.022 (86.022s)
- attempt: 1

##### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "impact_intensity": "큼",
    "implementation_stage": "시행 확정",
    "period": "1년",
    "structural_change_yn": "구조적/영구"
  },
  "impact": {
    "hh": "중립",
    "jkm": "상승",
    "ttf": "상승"
  },
  "narrative": "IMO Net-Zero Framework가 구조적 규제로 고착되며 1년 동안 LNG 운송비와 항로 제약이 크게 증가한다.",
  "probability_delta": 7.0,
  "probability_score": 30.0,
  "scenario_group_id": 48,
  "scenario_id": 282,
  "status": "created",
  "title": "[model_parameter_agent_test] IMO 운송 규제 큰 강도"
}
```

##### Validation Summary

- expected_parameters: `["Gas Futures Price"]`
- selected_parameters: `["Gas Futures Price"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: PASS
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=19|impactintensity|gasfuturesprice|demand|coalgasadjustment, sheet=CoalGasAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=0 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=0, distinct_axis_values=0 | PASS |
| Step2 selected slot | 24 | PASS |
| Step3 basecase 샘플 | prompt_records=0, limit=100 | PASS |
| Step3 value 결과 | value_cells=24, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Gas Futures Price | `{"modelFile": "Demand", "modelSheet": "CoalGasAdjustment", "tableName": "table2"}` | `["Month-Year", "Region"]` | `["Gas Futures Price (USD/mmbtu)"]` | 24 | 영향 강도 차원이 '큼'으로 지정되어 있고, 매핑 설명상 가스/LNG 가격 상승이 Gas↔Coal 전환 유인에 직접 연결되므로 Gas Futures Price 조정 대상으로 판단했다. 기간 1년, 시행 확정, 구조적/영구 성격은 공통 맥락으로 반영하여 2026년 7월부터 2027년 6월까지 Asia와 EU의 월별 선물가격을 상향된 절대 가격 수준으로 제안하되, HH는 선택 슬롯에 없으므로 반영하지 않았다. |

##### Proposed Parameter Values

###### Proposed Values - Gas Futures Price

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month-Year": "2026-07", "Region": "Asia"}` | null | 14.0 | 2026-07 Asia 슬롯은 1년 규제 영향의 시작 월로 선택했다. 기준값 레코드가 제공되지 않아 IMO 운송 규제의 큰 강도와 JKM 상승 방향을 반영한 보수적 절대 가격으로 14.0 USD/mmbtu를 제안했다. |
| 2 | `{"Month-Year": "2026-08", "Region": "Asia"}` | null | 14.2 | 2026-08 Asia 슬롯은 규제 영향이 지속되는 초기 월로 선택했다. 기준값 레코드가 제공되지 않아 운송비 상승이 JKM에 이어지는 흐름을 반영해 전월보다 소폭 높은 14.2 USD/mmbtu를 제안했다. |
| 3 | `{"Month-Year": "2026-09", "Region": "Asia"}` | null | 14.5 | 2026-09 Asia 슬롯은 1년 영향 기간 내 LNG 운송비 부담이 누적되는 구간으로 선택했다. 기준값 없이 큰 강도의 비용 상승을 월별 strip에 반영해 14.5 USD/mmbtu를 제안했다. |
| 4 | `{"Month-Year": "2026-10", "Region": "Asia"}` | null | 15.0 | 2026-10 Asia 슬롯은 겨울 수요기 진입 전 운송비 프리미엄이 가격에 더 반영될 수 있는 월로 선택했다. 기준값 레코드가 없어 상승 방향과 계절성을 함께 반영한 15.0 USD/mmbtu를 제안했다. |
| 5 | `{"Month-Year": "2026-11", "Region": "Asia"}` | null | 15.8 | 2026-11 Asia 슬롯은 동절기 수급 민감도가 커지는 월로 선택했다. IMO 규제에 따른 운송비 상승과 큰 영향 강도를 반영해 15.8 USD/mmbtu를 제안했다. |
| 6 | `{"Month-Year": "2026-12", "Region": "Asia"}` | null | 16.5 | 2026-12 Asia 슬롯은 동절기 LNG 수요와 운송 제약 영향이 가장 강하게 가격에 반영될 수 있는 월로 선택했다. 기준값 없이도 상승 충격이 뚜렷하므로 16.5 USD/mmbtu를 제안했다. |
| 7 | `{"Month-Year": "2027-01", "Region": "Asia"}` | null | 16.8 | 2027-01 Asia 슬롯은 1년 영향 기간 중 동절기 피크 구간으로 선택했다. 큰 강도의 운송비 상승과 JKM 상승 방향을 반영해 16.8 USD/mmbtu를 제안했다. |
| 8 | `{"Month-Year": "2027-02", "Region": "Asia"}` | null | 16.2 | 2027-02 Asia 슬롯은 동절기 영향이 지속되지만 피크 이후 완만히 낮아지는 월로 선택했다. 규제 비용 프리미엄을 유지하되 계절성 완화를 반영해 16.2 USD/mmbtu를 제안했다. |
| 9 | `{"Month-Year": "2027-03", "Region": "Asia"}` | null | 15.0 | 2027-03 Asia 슬롯은 겨울 이후 수요 압력이 완화되는 구간으로 선택했다. 운송비 상승 효과는 유지하되 계절적 하락을 반영해 15.0 USD/mmbtu를 제안했다. |
| 10 | `{"Month-Year": "2027-04", "Region": "Asia"}` | null | 14.0 | 2027-04 Asia 슬롯은 비수기 진입 구간으로 선택했다. IMO 규제에 따른 상향 압력은 유지하되 수요 계절성 완화를 반영해 14.0 USD/mmbtu를 제안했다. |
| 11 | `{"Month-Year": "2027-05", "Region": "Asia"}` | null | 13.5 | 2027-05 Asia 슬롯은 1년 영향 기간 후반의 비수기 월로 선택했다. 큰 강도의 규제 프리미엄을 완전히 제거하지 않고 보수적으로 낮춘 13.5 USD/mmbtu를 제안했다. |
| 12 | `{"Month-Year": "2027-06", "Region": "Asia"}` | null | 13.8 | 2027-06 Asia 슬롯은 1년 영향 기간의 마지막 월로 선택했다. 여름 수요와 운송비 상승 압력이 일부 재확대될 수 있어 13.8 USD/mmbtu를 제안했다. |
| 13 | `{"Month-Year": "2026-07", "Region": "EU"}` | null | 12.5 | 2026-07 EU 슬롯은 TTF 상승 방향이 반영되는 시작 월로 선택했다. 기준값 레코드가 제공되지 않아 운송 규제에 따른 LNG 조달비 상승을 반영한 보수적 절대 가격으로 12.5 USD/mmbtu를 제안했다. |
| 14 | `{"Month-Year": "2026-08", "Region": "EU"}` | null | 12.7 | 2026-08 EU 슬롯은 규제 영향이 지속되는 초기 월로 선택했다. TTF 상승 방향과 운송비 프리미엄을 반영해 12.7 USD/mmbtu를 제안했다. |
| 15 | `{"Month-Year": "2026-09", "Region": "EU"}` | null | 13.0 | 2026-09 EU 슬롯은 동절기 전 재고와 조달 민감도가 커지는 구간으로 선택했다. 기준값 없이 큰 강도 규제 충격을 반영해 13.0 USD/mmbtu를 제안했다. |
| 16 | `{"Month-Year": "2026-10", "Region": "EU"}` | null | 13.5 | 2026-10 EU 슬롯은 난방 수요기 진입 전 가격 민감도가 높아지는 월로 선택했다. 운송비 상승과 TTF 상승 방향을 반영해 13.5 USD/mmbtu를 제안했다. |
| 17 | `{"Month-Year": "2026-11", "Region": "EU"}` | null | 14.3 | 2026-11 EU 슬롯은 동절기 수급 압력이 커지는 월로 선택했다. LNG 운송비 상승이 유럽 가스 선물가격에 반영되는 것으로 보아 14.3 USD/mmbtu를 제안했다. |
| 18 | `{"Month-Year": "2026-12", "Region": "EU"}` | null | 15.0 | 2026-12 EU 슬롯은 동절기 가격 상승 압력이 강한 월로 선택했다. 큰 강도의 운송 규제 비용과 TTF 상승 방향을 반영해 15.0 USD/mmbtu를 제안했다. |
| 19 | `{"Month-Year": "2027-01", "Region": "EU"}` | null | 15.2 | 2027-01 EU 슬롯은 1년 영향 기간 중 동절기 피크 구간으로 선택했다. 운송비 상승과 계절적 수급 긴장을 함께 반영해 15.2 USD/mmbtu를 제안했다. |
| 20 | `{"Month-Year": "2027-02", "Region": "EU"}` | null | 14.8 | 2027-02 EU 슬롯은 동절기 영향이 이어지지만 피크 이후 일부 완화되는 월로 선택했다. 규제 프리미엄을 유지하되 계절적 완화를 반영해 14.8 USD/mmbtu를 제안했다. |
| 21 | `{"Month-Year": "2027-03", "Region": "EU"}` | null | 13.8 | 2027-03 EU 슬롯은 겨울 이후 수요 압력이 낮아지는 구간으로 선택했다. 운송비 상승 효과는 유지하되 동절기 프리미엄 축소를 반영해 13.8 USD/mmbtu를 제안했다. |
| 22 | `{"Month-Year": "2027-04", "Region": "EU"}` | null | 12.9 | 2027-04 EU 슬롯은 비수기 진입 월로 선택했다. 규제에 따른 상향 압력은 남기되 계절적 수요 완화를 반영해 12.9 USD/mmbtu를 제안했다. |
| 23 | `{"Month-Year": "2027-05", "Region": "EU"}` | null | 12.5 | 2027-05 EU 슬롯은 1년 영향 기간 후반의 비수기 월로 선택했다. 운송비 프리미엄을 보수적으로 유지하면서 낮은 계절 수요를 반영해 12.5 USD/mmbtu를 제안했다. |
| 24 | `{"Month-Year": "2027-06", "Region": "EU"}` | null | 12.7 | 2027-06 EU 슬롯은 영향 기간의 마지막 월로 선택했다. 여름철 LNG 조달과 운송비 상승 압력이 일부 남는 것으로 보아 12.7 USD/mmbtu를 제안했다. |

##### Final DB Proposal Row

- source_table: `tmm_mi_model_param_proposal_m`

```json
{
  "callback_sent_dtm": null,
  "callback_status": "SKIPPED",
  "confirmation_parameters": null,
  "confirmed_dtm": null,
  "error_code": null,
  "error_message": null,
  "mi_event_id": 1155,
  "model_param_proposal_id": 53,
  "proposal_completed_dtm": "2026-07-07 17:39:07.864836",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "CoalGasAdjustment",
        "slotAxesFieldNames": [
          "Month-Year",
          "Region"
        ],
        "tableName": "table2",
        "valueFieldNames": [
          "Gas Futures Price (USD/mmbtu)"
        ]
      },
      "parameterName": "Gas Futures Price",
      "rationale": "영향 강도 차원이 '큼'으로 지정되어 있고, 매핑 설명상 가스/LNG 가격 상승이 Gas↔Coal 전환 유인에 직접 연결되므로 Gas Futures Price 조정 대상으로 판단했다. 기간 1년, 시행 확정, 구조적/영구 성격은 공통 맥락으로 반영하여 2026년 7월부터 2027년 6월까지 Asia와 EU의 월별 선물가격을 상향된 절대 가격 수준으로 제안하되, HH는 선택 슬롯에 없으므로 반영하지 않았다.",
      "values": [
        {
          "Month-Year": "2026-07",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.0,
          "rationale": "2026-07 Asia 슬롯은 1년 규제 영향의 시작 월로 선택했다. 기준값 레코드가 제공되지 않아 IMO 운송 규제의 큰 강도와 JKM 상승 방향을 반영한 보수적 절대 가격으로 14.0 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.2,
          "rationale": "2026-08 Asia 슬롯은 규제 영향이 지속되는 초기 월로 선택했다. 기준값 레코드가 제공되지 않아 운송비 상승이 JKM에 이어지는 흐름을 반영해 전월보다 소폭 높은 14.2 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "2026-09 Asia 슬롯은 1년 영향 기간 내 LNG 운송비 부담이 누적되는 구간으로 선택했다. 기준값 없이 큰 강도의 비용 상승을 월별 strip에 반영해 14.5 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-10",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 15.0,
          "rationale": "2026-10 Asia 슬롯은 겨울 수요기 진입 전 운송비 프리미엄이 가격에 더 반영될 수 있는 월로 선택했다. 기준값 레코드가 없어 상승 방향과 계절성을 함께 반영한 15.0 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-11",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 15.8,
          "rationale": "2026-11 Asia 슬롯은 동절기 수급 민감도가 커지는 월로 선택했다. IMO 규제에 따른 운송비 상승과 큰 영향 강도를 반영해 15.8 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-12",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 16.5,
          "rationale": "2026-12 Asia 슬롯은 동절기 LNG 수요와 운송 제약 영향이 가장 강하게 가격에 반영될 수 있는 월로 선택했다. 기준값 없이도 상승 충격이 뚜렷하므로 16.5 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-01",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 16.8,
          "rationale": "2027-01 Asia 슬롯은 1년 영향 기간 중 동절기 피크 구간으로 선택했다. 큰 강도의 운송비 상승과 JKM 상승 방향을 반영해 16.8 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-02",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 16.2,
          "rationale": "2027-02 Asia 슬롯은 동절기 영향이 지속되지만 피크 이후 완만히 낮아지는 월로 선택했다. 규제 비용 프리미엄을 유지하되 계절성 완화를 반영해 16.2 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-03",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 15.0,
          "rationale": "2027-03 Asia 슬롯은 겨울 이후 수요 압력이 완화되는 구간으로 선택했다. 운송비 상승 효과는 유지하되 계절적 하락을 반영해 15.0 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-04",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.0,
          "rationale": "2027-04 Asia 슬롯은 비수기 진입 구간으로 선택했다. IMO 규제에 따른 상향 압력은 유지하되 수요 계절성 완화를 반영해 14.0 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-05",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 13.5,
          "rationale": "2027-05 Asia 슬롯은 1년 영향 기간 후반의 비수기 월로 선택했다. 큰 강도의 규제 프리미엄을 완전히 제거하지 않고 보수적으로 낮춘 13.5 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-06",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 13.8,
          "rationale": "2027-06 Asia 슬롯은 1년 영향 기간의 마지막 월로 선택했다. 여름 수요와 운송비 상승 압력이 일부 재확대될 수 있어 13.8 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-07",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "2026-07 EU 슬롯은 TTF 상승 방향이 반영되는 시작 월로 선택했다. 기준값 레코드가 제공되지 않아 운송 규제에 따른 LNG 조달비 상승을 반영한 보수적 절대 가격으로 12.5 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.7,
          "rationale": "2026-08 EU 슬롯은 규제 영향이 지속되는 초기 월로 선택했다. TTF 상승 방향과 운송비 프리미엄을 반영해 12.7 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 13.0,
          "rationale": "2026-09 EU 슬롯은 동절기 전 재고와 조달 민감도가 커지는 구간으로 선택했다. 기준값 없이 큰 강도 규제 충격을 반영해 13.0 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-10",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 13.5,
          "rationale": "2026-10 EU 슬롯은 난방 수요기 진입 전 가격 민감도가 높아지는 월로 선택했다. 운송비 상승과 TTF 상승 방향을 반영해 13.5 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-11",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 14.3,
          "rationale": "2026-11 EU 슬롯은 동절기 수급 압력이 커지는 월로 선택했다. LNG 운송비 상승이 유럽 가스 선물가격에 반영되는 것으로 보아 14.3 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2026-12",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 15.0,
          "rationale": "2026-12 EU 슬롯은 동절기 가격 상승 압력이 강한 월로 선택했다. 큰 강도의 운송 규제 비용과 TTF 상승 방향을 반영해 15.0 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-01",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 15.2,
          "rationale": "2027-01 EU 슬롯은 1년 영향 기간 중 동절기 피크 구간으로 선택했다. 운송비 상승과 계절적 수급 긴장을 함께 반영해 15.2 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-02",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 14.8,
          "rationale": "2027-02 EU 슬롯은 동절기 영향이 이어지지만 피크 이후 일부 완화되는 월로 선택했다. 규제 프리미엄을 유지하되 계절적 완화를 반영해 14.8 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-03",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 13.8,
          "rationale": "2027-03 EU 슬롯은 겨울 이후 수요 압력이 낮아지는 구간으로 선택했다. 운송비 상승 효과는 유지하되 동절기 프리미엄 축소를 반영해 13.8 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-04",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.9,
          "rationale": "2027-04 EU 슬롯은 비수기 진입 월로 선택했다. 규제에 따른 상향 압력은 남기되 계절적 수요 완화를 반영해 12.9 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-05",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "2027-05 EU 슬롯은 1년 영향 기간 후반의 비수기 월로 선택했다. 운송비 프리미엄을 보수적으로 유지하면서 낮은 계절 수요를 반영해 12.5 USD/mmbtu를 제안했다."
        },
        {
          "Month-Year": "2027-06",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.7,
          "rationale": "2027-06 EU 슬롯은 영향 기간의 마지막 월로 선택했다. 여름철 LNG 조달과 운송비 상승 압력이 일부 남는 것으로 보아 12.7 USD/mmbtu를 제안했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 48,
  "scenario_id": 282,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:08.081 | 8.081 | 2612 | 350 | 2962 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:17.787 | 17.787 | 5310 | 1843 | 7153 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:44.904 | 44.904 | 5783 | 3173 | 8956 |

### event_type_l2_id=21 국가별 경기

#### Scenario Group

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

#### Dimension Template

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

#### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "canonical_parameter_name": null,
      "comment": "수요 영향분 직접 조정(또는 PMI 강도로 반영) : User-Adjusted Gas Demand는 직접 쓰지 않고, 단기 수요 충격은 PMI, 구조적 수요 변화는 GDP 또는 PowerMix proxy로 우회 반영",
      "dimension_key": "demand_impact",
      "dimension_label": "LNG 수요 영향 규모",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 305,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "25%",
          "scenario_id": 306,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "GDP",
      "comment": "구조적 경기(GDP) 변동 : 장기·구조적 경기 변화는 국가별 GDP 경로를 조정하고, 일시적 심리·제조업 충격은 PMI를 우선 사용",
      "dimension_key": "economic_intensity",
      "dimension_label": "강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "GDPPopulationAdjustment",
        "model_table": "table1",
        "semantic_axes": "Real GDP(base 2019) — 국가·연"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "경미",
          "scenario_id": 305,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "경기 충격",
          "scenario_id": 306,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": "PMI",
      "comment": "산업 수요 단기 변동(PMI 탭) : 단기 경기 충격은 영향 국가의 PMI 조정으로 반영하고, 구조적 장기 성장 변화는 GDP 경로를 우선 검토",
      "dimension_key": "economic_intensity",
      "dimension_label": "강도",
      "mapping_method": "direct",
      "model_target": {
        "model_file": "Demand",
        "model_sheet": "PMIAdjustment",
        "model_table": "table1",
        "semantic_axes": "제조업 PMI — 국가·연·월 (산업 수요)"
      },
      "prompt_usage_policy": "direct_parameter_candidate_context",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "경미",
          "scenario_id": 305,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "경기 충격",
          "scenario_id": 306,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "시간축",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 305,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "1년",
          "scenario_id": 306,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [305, 306]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=305 [model_parameter_agent_test] 경미한 경기 둔화와 수요 영향 제한

- 소요시간: 01:16.592 (76.592s)
- attempt: 1

##### Scenario Major Info

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

##### Validation Summary

- expected_parameters: `["PMI", "GDP"]`
- selected_parameters: `["PMI", "GDP"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=141 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=24 | PASS |
| Step2 selected slot | 5 | PASS |
| Step3 basecase 샘플 | prompt_records=36, limit=100 | PASS |
| Step3 value 결과 | value_cells=5, basecaseValue_present=5 | PASS |
| Step2 slot axis value 수 | `{"21|economicintensity|gdp|demand|gdppopulationadjustment": {"Year": 8}, "21|economicintensity|pmi|demand|pmiadjustment": {"Month": 12, "Year": 4}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 1 | 강도 차원이 '경미'로 제시되어 산업 수요의 단기 심리·제조업 변동을 PMI 입력으로 반영할 수 있는 parameter이다. 기간 차원은 1개월 이하의 공통 시간 맥락으로 사용되며, 시나리오 narrative와 가격 영향이 모두 중립에 가까워 선택된 단기 월에 대해 기준 PMI를 유지하는 구조로 제안한다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 4 | 강도 차원이 '경미'로 제시되어 국가별 경기 경로를 GDP 입력으로 점검할 수 있으며, mapping 설명상 구조적 경기 변화는 GDP 경로 조정에 연결된다. 다만 시나리오가 단기·경미하고 가격 영향도 중립이므로, 선택된 국가·연도에 한해 이벤트에 명시된 국가별 성장률 전망을 같은 형식의 완만한 최종 GDP 성장률로 반영한다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 49.5 | 선택된 좌표는 현재 기준월에 해당하는 중국 PMI 입력 셀이다. 시나리오가 1개월 이하의 경미한 경기 영향이며 LNG 수요 영향이 거의 흡수되는 중립적 케이스이므로, 기준 PMI 49.5에 추가적인 하향 보정을 적용하지 않고 최종 입력값을 49.5로 유지한다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.045 | 선택된 좌표는 중국 2026년 GDP 성장률 입력 셀이다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 제시되어 기준값 0.042보다 소폭 높은 최종 성장률 0.045를 적용한다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.043 | 선택된 좌표는 중국 2027년 GDP 성장률 입력 셀이다. 이벤트에서 중국 2027년 성장률 전망이 4.3%로 유지된 것으로 제시되어 기준값 0.042를 해당 전망치와 같은 스케일의 최종 입력값 0.043으로 소폭 조정한다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.02 | 선택된 좌표는 미국 2026년 GDP 성장률 입력 셀이다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어 기준값 0.019 대비 소폭 높은 최종 성장률 0.020을 적용한다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.018 | 선택된 좌표는 미국 2027년 GDP 성장률 입력 셀이다. 이벤트에서 미국 2027년 성장률 전망이 1.8%로 제시되어 기준값 0.020에서 낮아진 최종 성장률 0.018을 적용한다. |

##### Final DB Proposal Row

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
  "model_param_proposal_id": 55,
  "proposal_completed_dtm": "2026-07-07 17:40:00.654447",
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
      "rationale": "강도 차원이 '경미'로 제시되어 산업 수요의 단기 심리·제조업 변동을 PMI 입력으로 반영할 수 있는 parameter이다. 기간 차원은 1개월 이하의 공통 시간 맥락으로 사용되며, 시나리오 narrative와 가격 영향이 모두 중립에 가까워 선택된 단기 월에 대해 기준 PMI를 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.5,
          "rationale": "선택된 좌표는 현재 기준월에 해당하는 중국 PMI 입력 셀이다. 시나리오가 1개월 이하의 경미한 경기 영향이며 LNG 수요 영향이 거의 흡수되는 중립적 케이스이므로, 기준 PMI 49.5에 추가적인 하향 보정을 적용하지 않고 최종 입력값을 49.5로 유지한다."
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
      "rationale": "강도 차원이 '경미'로 제시되어 국가별 경기 경로를 GDP 입력으로 점검할 수 있으며, mapping 설명상 구조적 경기 변화는 GDP 경로 조정에 연결된다. 다만 시나리오가 단기·경미하고 가격 영향도 중립이므로, 선택된 국가·연도에 한해 이벤트에 명시된 국가별 성장률 전망을 같은 형식의 완만한 최종 GDP 성장률로 반영한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.045,
          "rationale": "선택된 좌표는 중국 2026년 GDP 성장률 입력 셀이다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 제시되어 기준값 0.042보다 소폭 높은 최종 성장률 0.045를 적용한다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.043,
          "rationale": "선택된 좌표는 중국 2027년 GDP 성장률 입력 셀이다. 이벤트에서 중국 2027년 성장률 전망이 4.3%로 유지된 것으로 제시되어 기준값 0.042를 해당 전망치와 같은 스케일의 최종 입력값 0.043으로 소폭 조정한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.02,
          "rationale": "선택된 좌표는 미국 2026년 GDP 성장률 입력 셀이다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어 기준값 0.019 대비 소폭 높은 최종 성장률 0.020을 적용한다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.018,
          "rationale": "선택된 좌표는 미국 2027년 GDP 성장률 입력 셀이다. 이벤트에서 미국 2027년 성장률 전망이 1.8%로 제시되어 기준값 0.020에서 낮아진 최종 성장률 0.018을 적용한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:02.791 | 2.791 | 2334 | 70 | 2404 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:12.367 | 12.367 | 5295 | 809 | 6104 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:43.917 | 43.917 | 6575 | 1870 | 8445 |

#### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- 소요시간: 02:12.735 (132.735s)
- attempt: 1

##### Scenario Major Info

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

##### Validation Summary

- expected_parameters: `["PMI", "GDP"]`
- selected_parameters: `["PMI", "GDP"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=141 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=24 | PASS |
| Step2 selected slot | 16 | PASS |
| Step3 basecase 샘플 | prompt_records=36, limit=100 | PASS |
| Step3 value 결과 | value_cells=16, basecaseValue_present=10 | PASS |
| Step2 slot axis value 수 | `{"21|economicintensity|gdp|demand|gdppopulationadjustment": {"Year": 8}, "21|economicintensity|pmi|demand|pmiadjustment": {"Month": 12, "Year": 4}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 12 | 강도 차원의 ‘경기 충격’은 parameter_hint상 국가·연월별 제조업 PMI를 통해 산업 수요의 단기 둔화를 반영하는 입력과 직접 연결됩니다. 기간 차원의 ‘1년’은 공통 시간 맥락으로 사용해 현재 기준월부터 12개월 동안 중국 PMI를 경기 위축 국면으로 하향 적용하며, 충격이 지속되는 동안 동일한 보수적 둔화 수준을 유지했습니다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 4 | 강도 차원의 ‘경기 충격’은 parameter_hint상 국가·연도별 실질 GDP 증가율을 통해 구조적 경기 둔화를 반영하는 입력과 직접 연결됩니다. 기간 차원의 ‘1년’은 현재 기준월부터 12개월의 충격이 2026년 하반기와 2027년 상반기에 걸쳐 나타나는 시간 맥락으로 사용했으며, 중국과 미국의 연간 GDP 증가율을 하향 조정하되 기존 국가별 성장률 스케일을 유지했습니다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 47.0 | 해당 월은 1년 충격의 시작 월이며 기준 PMI 49.5가 이미 확장 기준선 50을 밑도는 수준입니다. 경기 충격에 따른 산업 수요 약화를 반영해 2.5포인트 낮춘 47.0을 최종 입력값으로 제안합니다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 49.5 | 47.0 | 해당 월은 충격 지속 구간에 포함되며 기준 PMI 49.5를 현재 기준값으로 사용했습니다. 1년 경기 충격이 제조업 심리와 산업 수요를 추가로 압박한다고 보고 47.0으로 하향 조정했습니다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 49.5 | 47.0 | 해당 월은 충격 지속 구간에 포함되며 기준 PMI 49.5를 현재 기준값으로 사용했습니다. 경기 충격 강도에 맞춰 수축 국면을 명확히 반영하되 과도한 급락은 피하기 위해 47.0을 적용했습니다. |
| 4 | `{"Country": "China", "Month": 10, "Year": 2026}` | 49.5 | 47.0 | 해당 월은 1년 경기 충격의 영향 기간에 해당합니다. 기준 PMI 49.5에서 경기 충격에 따른 산업활동 둔화를 반영해 2.5포인트 낮춘 47.0을 최종 입력값으로 산정했습니다. |
| 5 | `{"Country": "China", "Month": 11, "Year": 2026}` | 49.5 | 47.0 | 해당 월은 충격 지속 구간에 포함되며 기준 PMI 49.5를 현재 기준값으로 사용했습니다. 수요 감소 시나리오에 맞춰 제조업 PMI를 47.0으로 하향 반영했습니다. |
| 6 | `{"Country": "China", "Month": 12, "Year": 2026}` | 49.5 | 47.0 | 해당 월은 2026년 하반기 충격 구간의 마지막 월입니다. 기준 PMI 49.5에서 경기 충격에 따른 단기 산업 수요 둔화를 반영해 47.0을 적용했습니다. |
| 7 | `{"Country": "China", "Month": 1, "Year": 2027}` | null | 47.0 | 해당 월은 2026년 7월부터 1년간 이어지는 충격 구간에 포함됩니다. 일치하는 기준 record는 없지만 PMI index 형식이 명확하므로, 직전 충격 구간과 같은 둔화 수준인 47.0을 최종 입력값으로 제안합니다. |
| 8 | `{"Country": "China", "Month": 2, "Year": 2027}` | null | 47.0 | 해당 월은 1년 충격의 후반부에 해당합니다. 일치하는 기준 record는 없지만 동일한 국가·월별 PMI 입력 형식을 유지해, 수요 둔화가 지속되는 값으로 47.0을 적용했습니다. |
| 9 | `{"Country": "China", "Month": 3, "Year": 2027}` | null | 47.0 | 해당 월은 충격 지속 구간에 포함됩니다. 일치하는 기준 record는 없지만 시나리오상 회복 전환 근거가 없으므로 2026년 충격 월과 동일한 PMI 47.0을 유지했습니다. |
| 10 | `{"Country": "China", "Month": 4, "Year": 2027}` | null | 47.0 | 해당 월은 1년 경기 충격의 영향 기간 내에 있습니다. 일치하는 기준 record는 없지만 경기 충격에 따른 제조업 수축 국면을 같은 형식으로 반영해 47.0을 제안합니다. |
| 11 | `{"Country": "China", "Month": 5, "Year": 2027}` | null | 47.0 | 해당 월은 충격 종료 전 구간에 해당합니다. 일치하는 기준 record는 없지만 수요 감소가 지속되는 기간으로 해석해 PMI 47.0을 최종 입력값으로 적용했습니다. |
| 12 | `{"Country": "China", "Month": 6, "Year": 2027}` | null | 47.0 | 해당 월은 현재 기준월부터 12개월 영향 범위의 마지막 월입니다. 일치하는 기준 record는 없지만 1년 충격이 종료되기 전까지 같은 산업 수요 둔화 수준을 유지한다고 보고 47.0을 적용했습니다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.0385 | 해당 연도는 충격 시작 시점 이후 하반기가 영향권에 들어갑니다. 기준 GDP 증가율 0.042에서 1년 경기 충격의 반년 영향을 보수적으로 반영해 0.0035 낮춘 0.0385를 최종 입력값으로 제안합니다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.0355 | 해당 연도는 1년 충격의 후반부가 포함되는 연도입니다. 기준 GDP 증가율 0.042에 경기 충격의 잔여 영향과 성장 둔화 리스크를 반영해 0.0065 낮춘 0.0355를 적용했습니다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.0155 | 해당 연도는 충격 시작 후 하반기가 영향권에 포함됩니다. 기준 GDP 증가율 0.019에서 경기 충격에 따른 산업·소비 둔화의 반년 영향을 반영해 0.0035 낮춘 0.0155를 최종 입력값으로 산정했습니다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.0135 | 해당 연도는 충격 후반부가 포함되는 연도이며, 기준 GDP 증가율은 0.02입니다. 1년 경기 충격의 잔여 영향과 성장 둔화 리스크를 반영해 0.0065 낮춘 0.0135를 적용했습니다. |

##### Final DB Proposal Row

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
  "model_param_proposal_id": 57,
  "proposal_completed_dtm": "2026-07-07 17:41:20.608693",
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
      "rationale": "강도 차원의 ‘경기 충격’은 parameter_hint상 국가·연월별 제조업 PMI를 통해 산업 수요의 단기 둔화를 반영하는 입력과 직접 연결됩니다. 기간 차원의 ‘1년’은 공통 시간 맥락으로 사용해 현재 기준월부터 12개월 동안 중국 PMI를 경기 위축 국면으로 하향 적용하며, 충격이 지속되는 동안 동일한 보수적 둔화 수준을 유지했습니다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월은 1년 충격의 시작 월이며 기준 PMI 49.5가 이미 확장 기준선 50을 밑도는 수준입니다. 경기 충격에 따른 산업 수요 약화를 반영해 2.5포인트 낮춘 47.0을 최종 입력값으로 제안합니다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 지속 구간에 포함되며 기준 PMI 49.5를 현재 기준값으로 사용했습니다. 1년 경기 충격이 제조업 심리와 산업 수요를 추가로 압박한다고 보고 47.0으로 하향 조정했습니다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 지속 구간에 포함되며 기준 PMI 49.5를 현재 기준값으로 사용했습니다. 경기 충격 강도에 맞춰 수축 국면을 명확히 반영하되 과도한 급락은 피하기 위해 47.0을 적용했습니다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월은 1년 경기 충격의 영향 기간에 해당합니다. 기준 PMI 49.5에서 경기 충격에 따른 산업활동 둔화를 반영해 2.5포인트 낮춘 47.0을 최종 입력값으로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 지속 구간에 포함되며 기준 PMI 49.5를 현재 기준값으로 사용했습니다. 수요 감소 시나리오에 맞춰 제조업 PMI를 47.0으로 하향 반영했습니다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월은 2026년 하반기 충격 구간의 마지막 월입니다. 기준 PMI 49.5에서 경기 충격에 따른 단기 산업 수요 둔화를 반영해 47.0을 적용했습니다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 2026년 7월부터 1년간 이어지는 충격 구간에 포함됩니다. 일치하는 기준 record는 없지만 PMI index 형식이 명확하므로, 직전 충격 구간과 같은 둔화 수준인 47.0을 최종 입력값으로 제안합니다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 1년 충격의 후반부에 해당합니다. 일치하는 기준 record는 없지만 동일한 국가·월별 PMI 입력 형식을 유지해, 수요 둔화가 지속되는 값으로 47.0을 적용했습니다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 지속 구간에 포함됩니다. 일치하는 기준 record는 없지만 시나리오상 회복 전환 근거가 없으므로 2026년 충격 월과 동일한 PMI 47.0을 유지했습니다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 1년 경기 충격의 영향 기간 내에 있습니다. 일치하는 기준 record는 없지만 경기 충격에 따른 제조업 수축 국면을 같은 형식으로 반영해 47.0을 제안합니다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 종료 전 구간에 해당합니다. 일치하는 기준 record는 없지만 수요 감소가 지속되는 기간으로 해석해 PMI 47.0을 최종 입력값으로 적용했습니다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 현재 기준월부터 12개월 영향 범위의 마지막 월입니다. 일치하는 기준 record는 없지만 1년 충격이 종료되기 전까지 같은 산업 수요 둔화 수준을 유지한다고 보고 47.0을 적용했습니다."
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
      "rationale": "강도 차원의 ‘경기 충격’은 parameter_hint상 국가·연도별 실질 GDP 증가율을 통해 구조적 경기 둔화를 반영하는 입력과 직접 연결됩니다. 기간 차원의 ‘1년’은 현재 기준월부터 12개월의 충격이 2026년 하반기와 2027년 상반기에 걸쳐 나타나는 시간 맥락으로 사용했으며, 중국과 미국의 연간 GDP 증가율을 하향 조정하되 기존 국가별 성장률 스케일을 유지했습니다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.0385,
          "rationale": "해당 연도는 충격 시작 시점 이후 하반기가 영향권에 들어갑니다. 기준 GDP 증가율 0.042에서 1년 경기 충격의 반년 영향을 보수적으로 반영해 0.0035 낮춘 0.0385를 최종 입력값으로 제안합니다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.0355,
          "rationale": "해당 연도는 1년 충격의 후반부가 포함되는 연도입니다. 기준 GDP 증가율 0.042에 경기 충격의 잔여 영향과 성장 둔화 리스크를 반영해 0.0065 낮춘 0.0355를 적용했습니다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.0155,
          "rationale": "해당 연도는 충격 시작 후 하반기가 영향권에 포함됩니다. 기준 GDP 증가율 0.019에서 경기 충격에 따른 산업·소비 둔화의 반년 영향을 반영해 0.0035 낮춘 0.0155를 최종 입력값으로 산정했습니다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.0135,
          "rationale": "해당 연도는 충격 후반부가 포함되는 연도이며, 기준 GDP 증가율은 0.02입니다. 1년 경기 충격의 잔여 영향과 성장 둔화 리스크를 반영해 0.0065 낮춘 0.0135를 적용했습니다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.677 | 3.677 | 2347 | 127 | 2474 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:33.787 | 33.787 | 5304 | 2516 | 7820 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:18.040 | 78.040 | 6991 | 3462 | 10453 |

## 최종 요약

- ERROR_COUNT: 1
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"16": true, "18": true, "22": true, "44": true, "45": true, "47": true, "48": true, "49": true, "50": true, "51": false, "52": true, "53": true, "54": true, "60": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- scenario_id=287 elapsed=02:13.193 (133.193s) attempts=2 error=`MIBaseError('[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id=287')`

## Coverage Note

- 이번 실행 범위: 관련 event_type별 대표 scenario_group 1개, group별 scenario 2개. 총 14개 그룹/28개 시나리오 중 27개 저장 성공, 1개 오류.
- 같은 event_type 집합의 전수 후보 규모: 23개 그룹/81개 시나리오.
- 파라미터별 전수 후보 규모:
  - PMI: 1개 그룹/2개 시나리오
  - PowerMix: 17개 그룹/61개 시나리오
  - Temperature: 9개 그룹/24개 시나리오
  - LiqUtilAdjustment: 8개 그룹/37개 시나리오

## Direct/Route Drop Stage Check

추가 확인 방식: `to_output()`은 호출하지 않고 raw graph만 재실행하여 DB proposal row를 추가 저장하지 않은 상태에서 `candidate_mappings`, `parameter_slots`, `parameter_adjustments`를 확인했다.

| scenario_id | parameter | mapping_method | 원 실행 결과 | 추가 확인 결과 | drop stage 판단 |
|---:|---|---|---|---|---|
| 287 | PowerMix | direct | proposal row 생성 실패. `No valid model parameter proposal parameters generated` | Step1.5 candidate validation 통과, Step2 PowerMix slot 1개 selected, Step3 adjustment는 `selected=false`, value_count=0 | Step3 value proposal에서 탈락. 이후 `to_output()`의 proposal parameter 검증에서 전체 proposal이 실패 |
| 289 | PowerMix | direct | 원 레포트 Final DB row에는 Temperature만 저장되어 PowerMix 누락 | raw 재실행에서는 Step1.5 통과, Step2 Temperature/PowerMix slot 각 1개 selected, Step3에서도 Temperature/PowerMix 모두 selected | 원 실행의 누락은 Step1.5/Step2 deterministic 탈락이 아니라 Step3 LLM value selection 변동성으로 판단 |
| 292 | Temperature | direct | Final DB row에는 PowerMix만 저장되어 Temperature 누락 | Step1.5 candidate validation 통과, Step2 Temperature slot 9개와 PowerMix slot 4개 selected, Step3 adjustment는 Temperature `selected=false`, value_count=0, PowerMix만 selected | Step3 value proposal에서 탈락 |

Routing 확인: 현재 레포트에서 routing 후보가 전부 미제안된 케이스는 없다. event_type_l2_id=19는 routing 후보 중 Gas Futures Price가 선택되어 PASS이고, scenario_id=279의 `routing_result=REVIEW`는 routing 후보가 하나도 없는 문제가 아니라 routing 후보가 모두 selected된 케이스다.

## Parameter Quality Evaluation - PMI

대상 범위: event_type_l2_id=21, scenario_group_id=60, scenario_id=305/306. `economic_intensity -> PMI`는 `direct`, `demand_impact`는 `na`, `period`는 `indirect`로 로드됐다.

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나. direct는 필수선정, route는 1개 이상 선정 | PASS | scenario_id=305/306 모두 `expected_parameters=["PMI","GDP"]`, `selected_parameters=["PMI","GDP"]`. Final DB row 55/57에 `parameterName=PMI` 저장. | 없음. |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | PASS | PMI slot axes는 `Country, Year, Month`. scenario_id=305는 `China/2026/7` 1개월, scenario_id=306은 `China/2026/7~12` 및 `China/2027/1~6`으로 `period=1개월 이하`와 `period=1년` 차이를 반영. | PMI basecase가 사실상 China 중심으로 보이므로, country 후보가 제한되는 이유를 report에 명시하면 검토성이 좋아진다. |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가 | PASS | Step2 raw_records=141, PMI basecase candidate는 48건. scenario_id=305와 306의 2026년 7~12월은 `basecaseValue=49.5`를 읽어 같은 좌표에 제안. | 없음. |
| 4 | basecase에 없지만 시나리오/이벤트 정보로 추가 선정된 slot의 개연성이 있는가 | PASS | scenario_id=306의 `2027/1~6` PMI는 `basecaseValue=null`이지만 `period=1년`이 2026년 7월부터 12개월 지속되는 해석과 맞다. | 연도 경계를 넘는 월 확장 규칙을 prompt/report에 더 명시하면 재현성이 높아진다. |
| 5 | basecase에 없는 경우를 선정하지 못했다면 선정 가능성이 없었는가 | N/A | PMI에서 누락으로 판단되는 추가 slot은 확인되지 않았다. 1년 시나리오는 basecase가 없는 2027년 1~6월도 생성했다. | 없음. |
| 6 | value가 지정 범위/형식으로 선정되고 시나리오와 개연성이 있는가 | PASS | PMI 값은 index 형식으로 `49.5` 또는 `47.0`. 경미 시나리오 305는 기준 PMI 유지, 경기 충격 시나리오 306은 12개월 모두 `47.0`으로 하향. | 12개월 전체를 동일값으로 둘지, 월별 회복/악화 프로파일을 줄지 정책 선택지가 있으면 더 좋다. |
| 7 | value가 basecase에 있는 경우 적절하게 변경되었나 | PASS | scenario_id=305는 경미/중립이라 `49.5 -> 49.5`. scenario_id=306은 경기 충격이라 `49.5 -> 47.0`으로 하향. | 없음. |
| 8 | value가 basecase에 없었던 경우 개연성 있게 선정되었나 | REVIEW | scenario_id=306의 2027년 1~6월은 `basecaseValue=null`, `proposedValue=47.0`으로 직전 충격 월과 같은 수준을 유지. 방향은 타당하나 6개월 동일값의 산정 근거는 정성적이다. | basecase 미존재 월은 직전 월 유지, 선형 회복, 충격 지속 같은 선택 규칙을 명시하도록 prompt를 보강한다. |
| 9 | 동일 그룹 시나리오 사이에 dimension value에 따라 value 차이가 적절한가 | PASS | scenario_id=305는 `economic_intensity=경미`, `period=1개월 이하`로 1개 월 `49.5` 유지. scenario_id=306은 `economic_intensity=경기 충격`, `period=1년`으로 12개 월 `47.0` 하향. | 없음. |

## Parameter Quality Evaluation - PowerMix

대상 범위: event_type_l2_id=5/6/7/8/9/10/18/19. event_type_l2_id=19는 `impact_intensity`의 routing 후보군(`Coal Futures Price`, `Gas Futures Price`, `PowerMix`)이며, 최종 선택은 Gas Futures Price였다.

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나. direct는 필수선정, route는 1개 이상 선정 | FAIL | direct PowerMix mapping이 있는 scenario_id=288/290/291/292/293/294/261/262/267/268/129/130은 PowerMix가 저장됐다. 그러나 scenario_id=287은 direct PowerMix 대상인데 최종 제안 생성 실패, scenario_id=289는 `expected_parameters=["Temperature","PowerMix"]`이나 Final DB row에는 Temperature만 저장됐다. event_type_l2_id=19는 routing 후보 중 Gas Futures Price 선택이라 허용 가능. | direct 후보가 Step1.5 이후 Step3에서 빠질 때 사유를 구조화하고, direct mapping은 빈 value라도 검증 실패 전에 명확한 error/warning을 남기도록 한다. |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | REVIEW | 대부분 `Year, Country, Energy Source=Gas` 축으로 저장. 예: scenario_id=292는 China/Japan 2026 Gas, scenario_id=130은 China/Japan/South Korea 등 2026/2027 Gas. 다만 scenario_id=288/290은 `United States, 2026, Gas`가 `basecaseValue=null`인 상태에서 선택됐다. | basecase 없는 country/year/energy source를 선택할 때는 이벤트 본문에서 해당 국가가 직접 언급됐는지와 대체 가능한 basecase 후보가 없었는지 report에 남긴다. |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가 | PASS | scenario_id=291은 China `0.0346`, Japan `0.323` 기준값을 유지. scenario_id=292는 같은 slot을 각각 `0.036`, `0.336`으로 상향. scenario_id=261/262도 유럽 국가별 basecase를 읽고 동일 slot에서 조정. | 없음. |
| 4 | basecase에 없지만 시나리오/이벤트 정보로 추가 선정된 slot의 개연성이 있는가 | REVIEW | scenario_id=288은 발전 차질 3~5 GW와 50% 흡수를 근거로 United States Gas 2026 `0.39`를 생성했고, scenario_id=290은 강한 한파/대체 제한으로 United States Gas 2026 `0.45`를 생성했다. 방향은 맞지만 기준값 부재에서 절대값을 정한 근거가 약하다. | basecase 미존재 PowerMix는 동일 국가의 최근 연도, 유사 국가, 또는 이벤트 수치 기반 계산식 중 어떤 fallback을 썼는지 필수 출력하게 한다. |
| 5 | basecase에 없는 경우를 선정하지 못했다면 선정 가능성이 없었는가 | FAIL | scenario_id=287은 직접 PowerMix 대상인데 proposal 자체가 실패해 slot/value가 없다. scenario_id=289는 direct PowerMix 후보와 basecase option이 있었지만 최종 저장에서 누락됐다. | Step3에서 selected slot이 0개가 되거나 selected parameter가 사라지는 케이스를 자동 재시도 전에 원인별로 분류한다. |
| 6 | value가 지정 범위/형식으로 선정되고 시나리오와 개연성이 있는가 | REVIEW | 값은 PowerMix fraction 형식 `0~1`로 생성됐다. 100% 흡수 시나리오 291은 기준값 유지, 25% 흡수 시나리오 292는 약 4% 상대 상향, scenario_id=130은 제재 장기화로 Gas share를 하향. 다만 `0.39`, `0.45` 같은 basecase 없는 절대값은 산정식이 불투명하다. | 흡수율, 기간, capacity 변화 규모를 PowerMix 증감률로 변환하는 정량 가이드나 상한/하한을 prompt에 추가한다. |
| 7 | value가 basecase에 있는 경우 적절하게 변경되었나 | PASS | scenario_id=291은 `alt_energy_absorption=100%`라 China/Japan Gas share 유지. scenario_id=292는 `25%`라 `0.0346 -> 0.036`, `0.323 -> 0.336`. scenario_id=262는 scenario_id=261 대비 유럽 Gas share를 소폭 상향. | 없음. |
| 8 | value가 basecase에 없었던 경우 개연성 있게 선정되었나 | REVIEW | scenario_id=288 `basecaseValue=null -> 0.39`, scenario_id=290 `null -> 0.45`는 방향성은 타당하나 절대 수준의 근거가 부족하다. | null basecase value에는 `derived_from` 근거(유사 국가, 최근 연도, 이벤트 수치, default assumption)를 남기도록 schema/prompt를 확장한다. |
| 9 | 동일 그룹 시나리오 사이에 dimension value에 따라 value 차이가 적절한가 | REVIEW | 좋은 사례: group 53에서 100% 흡수 scenario_id=291은 유지, 25% 흡수 scenario_id=292는 상향. group 44도 261 유지, 262 상향. 그러나 group 51은 scenario_id=287 실패로 쌍 비교가 불가능하고 group 52는 scenario_id=289에서 PowerMix가 빠졌다. | 그룹 단위 평가에서 direct parameter 누락이 있으면 같은 그룹의 value 차이 판정도 자동 REVIEW/FAIL로 올린다. |

## Parameter Quality Evaluation - Temperature

대상 범위: event_type_l2_id=6/7. `cold_wave_intensity -> Temperature`, `heatwave_intensity -> Temperature`는 direct mapping이다.

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나. direct는 필수선정, route는 1개 이상 선정 | FAIL | scenario_id=289/290/291은 Temperature가 저장됐다. 그러나 scenario_id=292는 `expected_parameters=["Temperature","PowerMix"]`, direct heatwave mapping이 있는데 Final DB row에는 PowerMix만 저장됐다. | direct Temperature 후보는 Step3에서 값이 없더라도 누락 사유를 명확히 남기고 실패로 분류한다. |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | REVIEW | scenario_id=289는 United States 2026/3, scenario_id=290은 United States 2026/1~3, scenario_id=291은 China/Japan 2026/7을 선택했다. period와 월 해석은 대체로 맞지만 scenario_id=292의 3개월 강한 폭염 slot이 빠졌다. | heatwave/cold wave direct mapping에서는 기간이 3개월이면 최소 3개 월 slot을 요구하는 검증 규칙을 추가한다. |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가 | N/A | Temperature 결과는 모두 `basecaseValue=null`로 저장됐다. basecase 기반 slot 검증 대상이 없다. | basecase가 항상 비어 있다면 WeatherAdjustment basecase 로딩 가능 여부를 별도 점검한다. |
| 4 | basecase에 없지만 시나리오/이벤트 정보로 추가 선정된 slot의 개연성이 있는가 | PASS | scenario_id=289는 약한 한파와 1개월 이하 조건으로 US 3월 `2.5°C`, scenario_id=290은 강한 한파 3개월로 US 1~3월 `-5.0°C`, scenario_id=291은 약한 폭염으로 China/Japan 7월 `28.0/27.0°C`를 생성. | 없음. |
| 5 | basecase에 없는 경우를 선정하지 못했다면 선정 가능성이 없었는가 | FAIL | scenario_id=292는 `heatwave_intensity=+3℃ 이상: 강`, `period=3개월`, `peak_timing_pattern=지속 피크`라 Temperature를 선정할 가능성이 충분했지만 최종 제안에서 누락됐다. | direct Temperature가 누락되면 `selected_result`를 PASS로 두지 말고 target parameter 평가 기준에서는 FAIL로 표시한다. |
| 6 | value가 지정 범위/형식으로 선정되고 시나리오와 개연성이 있는가 | REVIEW | value field는 `Temperature (°C)`이고 값은 `2.5`, `-5.0`, `28.0`, `27.0`으로 숫자 형식이다. 다만 dimension 값은 `-2~-3℃`, `+1~+2℃`처럼 편차처럼 보이는데 결과는 절대 기온으로 해석되어 기준값 부재 시 의미가 애매하다. | WeatherAdjustment가 절대기온인지 평년대비 편차인지 prompt와 mapping comment에 명확히 고정한다. |
| 7 | value가 basecase에 있는 경우 적절하게 변경되었나 | N/A | 모든 Temperature value의 `basecaseValue`가 null이다. | 없음. |
| 8 | value가 basecase에 없었던 경우 개연성 있게 선정되었나 | REVIEW | `-5.0°C`는 강한 한파 임계값과 직접 맞지만, 약한 한파 `2.5°C` 및 약한 폭염 `28/27°C`는 이벤트 정보만으로 절대값을 정한 근거가 약하다. | 국가·월별 기후 정상값이 없으면 편차 기반 값으로 내거나, fallback 기준값 출처를 명시하게 한다. |
| 9 | 동일 그룹 시나리오 사이에 dimension value에 따라 value 차이가 적절한가 | REVIEW | 한파 group 52는 약한 1개월 `2.5°C`와 강한 3개월 `-5.0°C`로 차이가 분명하다. 폭염 group 53은 scenario_id=291만 Temperature가 있고 scenario_id=292가 누락되어 강도 차이를 평가할 수 없다. | 그룹 내 direct Temperature가 누락된 경우 group-level dimension comparison을 자동 REVIEW/FAIL 처리한다. |

## Parameter Quality Evaluation - LiqUtilAdjustment

대상 범위: event_type_l2_id=1/2/4/11/17/18. 모든 대상 그룹은 실행 완료됐고 group status는 PASS다.

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나. direct는 필수선정, route는 1개 이상 선정 | PASS | scenario_id=283/284/105/106/285/286/279/280/92/93/129/130 모두 Final DB row에 `parameterName=LiqUtilAdjustment`가 저장됐다. | scenario_id=279에 `routing_result: REVIEW`가 있으므로 routing 후보가 있는 event type에서는 선택 이유를 더 명확히 남긴다. |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | PASS | slot axes는 `Country, LNG Plant, LNG Plant Train, Life Cycle Category, Nameplate Capacity, Year, Month, Period`. 예: event_type_l2_id=2는 Cameron LNG T1~T3, event_type_l2_id=17은 QatarGas, event_type_l2_id=18은 Arctic LNG 2로 이벤트 맥락과 설비 축이 맞다. | Period 축 값(예: 103/112)이 Year/Month와 함께 어떤 기준월 offset인지 report에 설명하면 검토가 쉬워진다. |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가 | PASS | 대부분 `basecaseValue`가 존재한다. 예: Cameron LNG `0.8971/0.9091`, QatarGas `1.0477`, Arctic LNG 2 `0.45`를 읽고 동일 설비·월 slot에서 조정했다. | 없음. |
| 4 | basecase에 없지만 시나리오/이벤트 정보로 추가 선정된 slot의 개연성이 있는가 | N/A | 이번 LiqUtilAdjustment 결과에서 대표 value들은 모두 basecaseValue가 존재했다. | 없음. |
| 5 | basecase에 없는 경우를 선정하지 못했다면 선정 가능성이 없었는가 | N/A | 누락된 basecase-missing LiqUtilAdjustment slot은 확인되지 않았다. | 없음. |
| 6 | value가 지정 범위/형식으로 선정되고 시나리오와 개연성이 있는가 | REVIEW | 값은 utilization ratio 형식으로 저장됐다. 다만 일부 basecase/proposed 값이 1을 초과한다. 예: QatarGas `1.0477`, Gorgon LNG `1.0385`. basecase 자체가 1 초과라 agent 오류로 단정할 수는 없지만 허용 범위가 불명확하다. | LiqUtilAdjustment 허용 범위를 `0~1`인지, nameplate 대비 초과 가동을 허용하는 ratio인지 명시한다. |
| 7 | value가 basecase에 있는 경우 적절하게 변경되었나 | REVIEW | severity가 높은 케이스는 조정이 잘 나타난다. 예: scenario_id=93 QatarGas 약 `1.0477 -> 0.9953`, scenario_id=130 Arctic LNG 2 `0.45 -> 0.35`, scenario_id=106 Cameron LNG `~0.90 -> 1.0`. 반면 scenario_id=280 Gorgon LNG `1.0385 -> 1.0385`, scenario_id=92 QatarGas 유지처럼 영향 시나리오에서 변경이 없는 케이스는 추가 검토 필요. | 영향이 제한적이라 유지하는 케이스와 실제 누락을 구분하도록 `no_change_reason`을 별도 필드로 요구한다. |
| 8 | value가 basecase에 없었던 경우 개연성 있게 선정되었나 | N/A | 이번 LiqUtilAdjustment 대표 결과는 basecaseValue null 케이스가 확인되지 않았다. | 없음. |
| 9 | 동일 그룹 시나리오 사이에 dimension value에 따라 value 차이가 적절한가 | PASS | group 16은 단기/흡수 scenario_id=92가 유지, 3개월 부분 차질 scenario_id=93은 QatarGas를 약 5% 하향. group 18은 1개월 미세 감산 scenario_id=105가 소폭 하향, 3개월 완전 증산 scenario_id=106은 `1.0` 상향. group 22도 scenario_id=129보다 scenario_id=130에서 Arctic LNG 2 하향 폭이 크다. | 없음. |
