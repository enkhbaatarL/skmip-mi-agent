# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-07T21:06:41
- 실행 종료: 2026-07-07T21:24:06
- 총 소요시간: 17:24.417 (1044.417s)
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
| 1 | 49 | 283 | OK | 1 | 03:44.847 | 224.847s |
| 1 | 49 | 284 | OK | 1 | 04:19.610 | 259.610s |
| 2 | 18 | 105 | OK | 1 | 02:41.086 | 161.086s |
| 2 | 18 | 106 | OK | 1 | 02:15.734 | 135.734s |
| 4 | 50 | 285 | OK | 1 | 02:33.798 | 153.798s |
| 4 | 50 | 286 | OK | 1 | 03:53.188 | 233.188s |
| 5 | 51 | 287 | OK | 1 | 00:53.472 | 53.472s |
| 5 | 51 | 288 | OK | 1 | 01:02.483 | 62.483s |
| 6 | 52 | 289 | OK | 1 | 01:17.925 | 77.925s |
| 6 | 52 | 290 | OK | 1 | 01:54.240 | 114.240s |
| 7 | 53 | 291 | OK | 1 | 01:43.473 | 103.473s |
| 7 | 53 | 292 | OK | 1 | 01:32.969 | 92.969s |
| 8 | 54 | 293 | OK | 1 | 01:03.851 | 63.851s |
| 8 | 54 | 294 | OK | 1 | 01:12.652 | 72.652s |
| 9 | 44 | 261 | OK | 1 | 01:11.493 | 71.493s |
| 9 | 44 | 262 | OK | 1 | 01:13.234 | 73.234s |
| 10 | 45 | 267 | OK | 1 | 01:01.267 | 61.267s |
| 10 | 45 | 268 | OK | 1 | 01:00.274 | 60.274s |
| 11 | 47 | 279 | OK | 1 | 03:10.669 | 190.669s |
| 11 | 47 | 280 | OK | 1 | 03:39.030 | 219.030s |
| 17 | 16 | 92 | OK | 1 | 03:07.702 | 187.702s |
| 17 | 16 | 93 | OK | 1 | 03:54.417 | 234.417s |
| 18 | 22 | 129 | OK | 1 | 02:46.275 | 166.275s |
| 18 | 22 | 130 | OK | 1 | 04:36.758 | 276.758s |
| 19 | 48 | 281 | OK | 1 | 00:56.577 | 56.577s |
| 19 | 48 | 282 | OK | 1 | 01:51.456 | 111.456s |
| 21 | 60 | 305 | OK | 1 | 01:34.841 | 94.841s |
| 21 | 60 | 306 | OK | 1 | 03:03.817 | 183.817s |

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

- 소요시간: 03:44.847 (224.847s)
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
| Step2 selected slot | 48 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=4, basecaseValue_present=3 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 1 | Utilization 변화 폭이 <5%로 제시되어 노르웨이 upstream 생산 차질을 월간 Bcm 단위의 SupplyDisruption으로 반영할 수 있으며, 대체 가스 공급 가능성 100%는 시장 영향이 중립적이고 차질이 단기에 그친다는 완화 조건으로 해석했다. 따라서 노르웨이의 1개월 이하 소폭 차질만 보수적으로 반영하고, 점진 발생·급격 회복 특성을 감안해 단일 월에 한정한다. |
| 2 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 3 | 대체 가스 공급 가능성 100%는 노르웨이 upstream 차질이 유럽 시장에서 인접·연결 공급원의 LNG 전환 공급으로 완화될 수 있음을 의미하므로 LiqUtilAdjustment 상향 후보와 직접 연결된다. 기간은 1개월 이하이고 발생은 점진·회복은 급격으로 제시되어, 유럽 접근성이 높고 기준 가동률 여유가 있는 일부 알제리 액화설비에 한 달만 보수적으로 상향 배분한다. |

##### Proposed Parameter Values

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Norway", "Month": 6, "Year": 2027}` | null | 0.22 | 선택된 좌표는 기사상 6월 5일 파업 위험이 언급된 노르웨이의 가장 가까운 향후 6월 슬롯이다. 제시된 초기 감소 규모 4만5,500boe/d를 1개월 이하 기간으로 보수적으로 30일 적용하고 가스 환산 기준을 사용해 약 0.22Bcm의 월간 차질로 산정했으며, 대체 공급 100% 조건 때문에 추가 확대분은 반영하지 않았다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 7.9, "Period": 123, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | 유럽 인접 대체 공급원 중 기준 가동률이 낮아 단기 상향 여력이 있는 슬롯을 선택했다. 기준 가동률 0.18404907975460122에 1개월 이하의 소규모 대체 물량 배분을 위해 0.10p를 더해 최종 가동률을 0.2840490797546012로 제안한다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 8.4, "Period": 123, "Year": 2027}` | 0.1840490797546012 | 0.2840490797546012 | Arzew 내 동일 권역의 저가동 대형 설비로서 단기 대체 공급 배분에 적합한 슬롯을 선택했다. 기준 가동률 0.18404907975460122에 0.10p의 보수적 상향을 적용해 최종 가동률을 0.2840490797546012로 산정했다. |
| 3 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 4.5, "Period": 123, "Year": 2027}` | 0.3688888888888889 | 0.4688888888888889 | 기준 가동률이 1.0에 도달하지 않은 알제리 운영 설비로, 동일한 1개월 대체 공급 상향 배분 대상에 포함했다. 기준 가동률 0.3688888888888889에 0.10p를 더해 최종 가동률을 0.4688888888888889로 제안한다. |

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
  "model_param_proposal_id": 60,
  "proposal_completed_dtm": "2026-07-07 21:10:26.654078",
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
      "rationale": "Utilization 변화 폭이 <5%로 제시되어 노르웨이 upstream 생산 차질을 월간 Bcm 단위의 SupplyDisruption으로 반영할 수 있으며, 대체 가스 공급 가능성 100%는 시장 영향이 중립적이고 차질이 단기에 그친다는 완화 조건으로 해석했다. 따라서 노르웨이의 1개월 이하 소폭 차질만 보수적으로 반영하고, 점진 발생·급격 회복 특성을 감안해 단일 월에 한정한다.",
      "values": [
        {
          "Country": "Norway",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0.22,
          "rationale": "선택된 좌표는 기사상 6월 5일 파업 위험이 언급된 노르웨이의 가장 가까운 향후 6월 슬롯이다. 제시된 초기 감소 규모 4만5,500boe/d를 1개월 이하 기간으로 보수적으로 30일 적용하고 가스 환산 기준을 사용해 약 0.22Bcm의 월간 차질로 산정했으며, 대체 공급 100% 조건 때문에 추가 확대분은 반영하지 않았다."
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
      "rationale": "대체 가스 공급 가능성 100%는 노르웨이 upstream 차질이 유럽 시장에서 인접·연결 공급원의 LNG 전환 공급으로 완화될 수 있음을 의미하므로 LiqUtilAdjustment 상향 후보와 직접 연결된다. 기간은 1개월 이하이고 발생은 점진·회복은 급격으로 제시되어, 유럽 접근성이 높고 기준 가동률 여유가 있는 일부 알제리 액화설비에 한 달만 보수적으로 상향 배분한다.",
      "values": [
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.1840490797546012,
          "proposedValue": 0.2840490797546012,
          "rationale": "유럽 인접 대체 공급원 중 기준 가동률이 낮아 단기 상향 여력이 있는 슬롯을 선택했다. 기준 가동률 0.18404907975460122에 1개월 이하의 소규모 대체 물량 배분을 위해 0.10p를 더해 최종 가동률을 0.2840490797546012로 제안한다."
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
          "rationale": "Arzew 내 동일 권역의 저가동 대형 설비로서 단기 대체 공급 배분에 적합한 슬롯을 선택했다. 기준 가동률 0.18404907975460122에 0.10p의 보수적 상향을 적용해 최종 가동률을 0.2840490797546012로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.3688888888888889,
          "proposedValue": 0.4688888888888889,
          "rationale": "기준 가동률이 1.0에 도달하지 않은 알제리 운영 설비로, 동일한 1개월 대체 공급 상향 배분 대상에 포함했다. 기준 가동률 0.3688888888888889에 0.10p를 더해 최종 가동률을 0.4688888888888889로 제안한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.872 | 4.872 | 2542 | 149 | 2691 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:26.067 | 86.067 | 11906 | 9174 | 21080 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:16.419 | 76.419 | 18157 | 4107 | 22264 |

#### scenario_id=284 [model_parameter_agent_test] 6개월 큰 감산과 대체 공급 제한

- 소요시간: 04:19.610 (259.610s)
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
| Step2 selected slot | 84 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=18, basecaseValue_present=12 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 6 | Utilization 변화 폭 60%는 노르웨이 upstream 생산 차질의 직접 규모를 정하는 축이고, 대체 가스 공급 가능성 25%는 차질 중 일부만 상쇄 가능하다는 완화 조건으로 연결된다. 6개월 기간, 급격한 발생, 점진적 회복을 반영해 초기에는 순차질을 즉시 반영하고 후반으로 갈수록 차질량을 단계적으로 축소하는 월별 Bcm 최종 입력값으로 제안한다. |
| 2 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 12 | 대체 가스 공급 가능성 25%는 노르웨이 공급 차질 중 제한적인 일부만 LNG 전환 대체로 보완 가능하다는 의미이며, LiqUtilAdjustment는 이 대체 공급을 인접·시장연결 공급국의 가용 액화설비 가동률 상향으로 반영하는 직접 parameter이다. 6개월 동안 가동 여력이 확인되는 알제리 설비에 제한적으로 배분하고, 급격한 발생 후 점진적 회복에 맞춰 초기 상향폭을 크게 두고 후반에는 축소하는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Norway", "Month": 7, "Year": 2026}` | null | 0.098 | 2026년 7월은 6개월 차질의 첫 달로, 급격한 발생 조건에 따라 초기 순차질을 즉시 반영했다. 기준 record가 없어 기사에 제시된 초기 생산 차질량을 월간 Bcm 형식으로 보수 환산한 뒤 60% 차질 강도와 25% 대체 공급 가능성을 반영해 0.098 Bcm로 산정했다. |
| 2 | `{"Country": "Norway", "Month": 8, "Year": 2026}` | null | 0.098 | 2026년 8월은 차질 지속 구간의 초반부로 보아 7월과 같은 순차질 강도를 유지했다. 기준 record가 없어 동일한 월간 환산 기준에 60% 차질 강도와 25% 대체 공급 가능성을 반영해 0.098 Bcm로 산정했다. |
| 3 | `{"Country": "Norway", "Month": 9, "Year": 2026}` | null | 0.078 | 2026년 9월은 6개월 차질의 중반으로, 점진적 회복 조건을 반영해 초기 순차질의 약 80% 수준으로 낮췄다. 기준 record가 없어 앞선 월간 순차질 산정값에 회복 보정을 적용해 0.078 Bcm로 산정했다. |
| 4 | `{"Country": "Norway", "Month": 10, "Year": 2026}` | null | 0.059 | 2026년 10월은 회복이 진행되는 구간으로 보아 초기 순차질의 약 60% 수준을 적용했다. 기준 record가 없어 월간 순차질 산정값에 점진 회복 보정을 적용해 0.059 Bcm로 산정했다. |
| 5 | `{"Country": "Norway", "Month": 11, "Year": 2026}` | null | 0.039 | 2026년 11월은 차질 후반부로, 복구가 추가 진행된 것으로 보고 초기 순차질의 약 40% 수준을 반영했다. 기준 record가 없어 동일한 환산 기준에 후반 회복 보정을 적용해 0.039 Bcm로 산정했다. |
| 6 | `{"Country": "Norway", "Month": 12, "Year": 2026}` | null | 0.02 | 2026년 12월은 6개월 차질의 마지막 달로, 점진적 회복에 따라 초기 순차질의 약 20%만 잔존하는 것으로 보수 적용했다. 기준 record가 없어 월간 순차질 산정값에 말기 회복 보정을 적용해 0.020 Bcm로 산정했다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.9, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.24018404907975455 | 해당 설비는 기준 가동률 0.19018404907975456으로 상향 여력이 있어 2026년 7월 대체 LNG 공급의 초기 대응 대상으로 선택했다. 제한적 대체 공급 조건을 반영해 가동률을 0.05p 상향하되 1.0 상한 이내인 0.24018404907975455로 산정했다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.9, "Period": 113, "Year": 2026}` | 0.19018404907975456 | 0.24018404907975455 | 2026년 8월은 차질 지속 초반부로, 동일 설비의 기준 가동률 0.19018404907975456에 초기 대응 상향폭을 유지했다. 대체 공급 여력이 제한적이므로 0.05p만 상향해 0.24018404907975455로 산정했다. |
| 3 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.9, "Period": 114, "Year": 2026}` | 0.19018404907975456 | 0.23018404907975457 | 2026년 9월은 점진 회복이 시작되는 중반부로 보아 상향폭을 초기보다 낮췄다. 기준 가동률 0.19018404907975456에 0.04p를 더해 최종 가동률 0.23018404907975457로 산정했다. |
| 4 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 7.9, "Period": 115, "Year": 2026}` | 0.19018404907975456 | 0.22018404907975456 | 2026년 10월은 회복 진행에 따라 대체 LNG 필요량이 더 줄어드는 구간으로 보았다. 기준 가동률 0.19018404907975456에 0.03p를 더해 0.22018404907975456으로 산정했다. |
| 5 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 7.9, "Period": 116, "Year": 2026}` | 0.19018404907975456 | 0.21018404907975455 | 2026년 11월은 차질 후반부로, 잔여 대체 수요만 반영하기 위해 상향폭을 축소했다. 기준 가동률 0.19018404907975456에 0.02p를 더해 0.21018404907975455로 산정했다. |
| 6 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 7.9, "Period": 117, "Year": 2026}` | 0.19018404907975456 | 0.20018404907975457 | 2026년 12월은 6개월 차질의 마지막 달로, 점진적 회복에 따라 최소한의 대체 LNG 상향만 남겼다. 기준 가동률 0.19018404907975456에 0.01p를 더해 0.20018404907975457로 산정했다. |
| 7 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 8.4, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.24018404907975455 | 해당 설비는 기준 가동률 0.19018404907975456으로 상향 여력이 충분해 2026년 7월 대체 LNG 공급 대상으로 함께 선택했다. 제한적 대체 공급 조건을 고려해 0.05p 상향한 0.24018404907975455로 산정했다. |
| 8 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 8.4, "Period": 113, "Year": 2026}` | 0.19018404907975456 | 0.24018404907975455 | 2026년 8월은 차질 지속 초반부로, 7월과 같은 대체 LNG 대응 강도를 유지했다. 기준 가동률 0.19018404907975456에 0.05p를 더해 0.24018404907975455로 산정했다. |
| 9 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 8.4, "Period": 114, "Year": 2026}` | 0.19018404907975456 | 0.23018404907975457 | 2026년 9월은 노르웨이 차질의 점진 회복을 반영해 대체 액화 가동률 상향폭을 낮춘 구간이다. 기준 가동률 0.19018404907975456에 0.04p를 더해 0.23018404907975457로 산정했다. |
| 10 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 8.4, "Period": 115, "Year": 2026}` | 0.19018404907975456 | 0.22018404907975456 | 2026년 10월은 회복 진행에 따라 필요한 대체 공급량이 줄어드는 시점으로 보았다. 기준 가동률 0.19018404907975456에 0.03p만 추가해 0.22018404907975456으로 산정했다. |
| 11 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 8.4, "Period": 116, "Year": 2026}` | 0.19018404907975456 | 0.21018404907975455 | 2026년 11월은 차질 후반부로, 제한적 잔여 대체 수요만 반영했다. 기준 가동률 0.19018404907975456에 0.02p를 더해 0.21018404907975455로 산정했다. |
| 12 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 8.4, "Period": 117, "Year": 2026}` | 0.19018404907975456 | 0.20018404907975457 | 2026년 12월은 6개월 영향의 마지막 달로, 점진 회복에 따른 최소 상향만 반영했다. 기준 가동률 0.19018404907975456에 0.01p를 더해 0.20018404907975457로 산정했다. |

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
  "model_param_proposal_id": 61,
  "proposal_completed_dtm": "2026-07-07 21:11:07.850782",
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
      "rationale": "Utilization 변화 폭 60%는 노르웨이 upstream 생산 차질의 직접 규모를 정하는 축이고, 대체 가스 공급 가능성 25%는 차질 중 일부만 상쇄 가능하다는 완화 조건으로 연결된다. 6개월 기간, 급격한 발생, 점진적 회복을 반영해 초기에는 순차질을 즉시 반영하고 후반으로 갈수록 차질량을 단계적으로 축소하는 월별 Bcm 최종 입력값으로 제안한다.",
      "values": [
        {
          "Country": "Norway",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.098,
          "rationale": "2026년 7월은 6개월 차질의 첫 달로, 급격한 발생 조건에 따라 초기 순차질을 즉시 반영했다. 기준 record가 없어 기사에 제시된 초기 생산 차질량을 월간 Bcm 형식으로 보수 환산한 뒤 60% 차질 강도와 25% 대체 공급 가능성을 반영해 0.098 Bcm로 산정했다."
        },
        {
          "Country": "Norway",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.098,
          "rationale": "2026년 8월은 차질 지속 구간의 초반부로 보아 7월과 같은 순차질 강도를 유지했다. 기준 record가 없어 동일한 월간 환산 기준에 60% 차질 강도와 25% 대체 공급 가능성을 반영해 0.098 Bcm로 산정했다."
        },
        {
          "Country": "Norway",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.078,
          "rationale": "2026년 9월은 6개월 차질의 중반으로, 점진적 회복 조건을 반영해 초기 순차질의 약 80% 수준으로 낮췄다. 기준 record가 없어 앞선 월간 순차질 산정값에 회복 보정을 적용해 0.078 Bcm로 산정했다."
        },
        {
          "Country": "Norway",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.059,
          "rationale": "2026년 10월은 회복이 진행되는 구간으로 보아 초기 순차질의 약 60% 수준을 적용했다. 기준 record가 없어 월간 순차질 산정값에 점진 회복 보정을 적용해 0.059 Bcm로 산정했다."
        },
        {
          "Country": "Norway",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.039,
          "rationale": "2026년 11월은 차질 후반부로, 복구가 추가 진행된 것으로 보고 초기 순차질의 약 40% 수준을 반영했다. 기준 record가 없어 동일한 환산 기준에 후반 회복 보정을 적용해 0.039 Bcm로 산정했다."
        },
        {
          "Country": "Norway",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.02,
          "rationale": "2026년 12월은 6개월 차질의 마지막 달로, 점진적 회복에 따라 초기 순차질의 약 20%만 잔존하는 것으로 보수 적용했다. 기준 record가 없어 월간 순차질 산정값에 말기 회복 보정을 적용해 0.020 Bcm로 산정했다."
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
      "rationale": "대체 가스 공급 가능성 25%는 노르웨이 공급 차질 중 제한적인 일부만 LNG 전환 대체로 보완 가능하다는 의미이며, LiqUtilAdjustment는 이 대체 공급을 인접·시장연결 공급국의 가용 액화설비 가동률 상향으로 반영하는 직접 parameter이다. 6개월 동안 가동 여력이 확인되는 알제리 설비에 제한적으로 배분하고, 급격한 발생 후 점진적 회복에 맞춰 초기 상향폭을 크게 두고 후반에는 축소하는 구조로 제안한다.",
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
          "proposedValue": 0.24018404907975455,
          "rationale": "해당 설비는 기준 가동률 0.19018404907975456으로 상향 여력이 있어 2026년 7월 대체 LNG 공급의 초기 대응 대상으로 선택했다. 제한적 대체 공급 조건을 반영해 가동률을 0.05p 상향하되 1.0 상한 이내인 0.24018404907975455로 산정했다."
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
          "proposedValue": 0.24018404907975455,
          "rationale": "2026년 8월은 차질 지속 초반부로, 동일 설비의 기준 가동률 0.19018404907975456에 초기 대응 상향폭을 유지했다. 대체 공급 여력이 제한적이므로 0.05p만 상향해 0.24018404907975455로 산정했다."
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
          "proposedValue": 0.23018404907975457,
          "rationale": "2026년 9월은 점진 회복이 시작되는 중반부로 보아 상향폭을 초기보다 낮췄다. 기준 가동률 0.19018404907975456에 0.04p를 더해 최종 가동률 0.23018404907975457로 산정했다."
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
          "proposedValue": 0.22018404907975456,
          "rationale": "2026년 10월은 회복 진행에 따라 대체 LNG 필요량이 더 줄어드는 구간으로 보았다. 기준 가동률 0.19018404907975456에 0.03p를 더해 0.22018404907975456으로 산정했다."
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
          "proposedValue": 0.21018404907975455,
          "rationale": "2026년 11월은 차질 후반부로, 잔여 대체 수요만 반영하기 위해 상향폭을 축소했다. 기준 가동률 0.19018404907975456에 0.02p를 더해 0.21018404907975455로 산정했다."
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
          "proposedValue": 0.20018404907975457,
          "rationale": "2026년 12월은 6개월 차질의 마지막 달로, 점진적 회복에 따라 최소한의 대체 LNG 상향만 남겼다. 기준 가동률 0.19018404907975456에 0.01p를 더해 0.20018404907975457로 산정했다."
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
          "proposedValue": 0.24018404907975455,
          "rationale": "해당 설비는 기준 가동률 0.19018404907975456으로 상향 여력이 충분해 2026년 7월 대체 LNG 공급 대상으로 함께 선택했다. 제한적 대체 공급 조건을 고려해 0.05p 상향한 0.24018404907975455로 산정했다."
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
          "proposedValue": 0.24018404907975455,
          "rationale": "2026년 8월은 차질 지속 초반부로, 7월과 같은 대체 LNG 대응 강도를 유지했다. 기준 가동률 0.19018404907975456에 0.05p를 더해 0.24018404907975455로 산정했다."
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
          "proposedValue": 0.23018404907975457,
          "rationale": "2026년 9월은 노르웨이 차질의 점진 회복을 반영해 대체 액화 가동률 상향폭을 낮춘 구간이다. 기준 가동률 0.19018404907975456에 0.04p를 더해 0.23018404907975457로 산정했다."
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
          "proposedValue": 0.22018404907975456,
          "rationale": "2026년 10월은 회복 진행에 따라 필요한 대체 공급량이 줄어드는 시점으로 보았다. 기준 가동률 0.19018404907975456에 0.03p만 추가해 0.22018404907975456으로 산정했다."
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
          "proposedValue": 0.21018404907975455,
          "rationale": "2026년 11월은 차질 후반부로, 제한적 잔여 대체 수요만 반영했다. 기준 가동률 0.19018404907975456에 0.02p를 더해 0.21018404907975455로 산정했다."
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
          "proposedValue": 0.20018404907975457,
          "rationale": "2026년 12월은 6개월 영향의 마지막 달로, 점진 회복에 따른 최소 상향만 반영했다. 기준 가동률 0.19018404907975456에 0.01p를 더해 0.20018404907975457로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.107 | 4.107 | 2543 | 170 | 2713 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:44.227 | 104.227 | 11903 | 12833 | 24736 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:36.948 | 96.948 | 19421 | 6633 | 26054 |

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

- 소요시간: 02:41.086 (161.086s)
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
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 3 | Utilization 변화량이 <5%로 제시되어 차질 대상 액화 Train의 월별 가동률을 직접 조정하는 LiqUtilAdjustment와 연결된다. 기간은 1개월 이하이고 회복 패턴은 급격하므로, Cameron LNG의 정상가동 기조를 유지하되 2026년 7월에만 미세 감산을 반영하고 이후 기간으로는 확장하지 않는다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 3 | Utilization 변화량이 <5%로 제한되어 생산량 자체의 구조적 손실보다는 단기·소폭 생산 감소를 표현하는 보조적 생산량 override와 연결된다. 기간은 1개월 이하이고 회복은 급격하므로, Cameron LNG의 정상가동 유지라는 전제 아래 2026년 7월 Train별 월간 생산량에만 제한적으로 하향 조정을 반영한다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.870225523664935 | 해당 좌표는 Cameron LNG T1의 2026년 7월 입력 record이며, 시나리오 기간이 1개월 이하로 제한되어 현재 기준월 슬롯만 조정했다. 기준값 0.8971397151184897에 미세 감산 성격을 반영해 <5% 범위 안의 보수적 3% 하향을 적용하여 최종 가동률 0.870225523664935로 산정했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.870225523664935 | 해당 좌표는 Cameron LNG T2의 2026년 7월 입력 record이며, 단기 운영 조정 후 급격히 정상화되는 시나리오이므로 같은 월 슬롯에만 조정을 적용했다. 기준값 0.8971397151184897에 <5% 미만의 제한적 감산을 보수적으로 3% 반영하여 최종 가동률 0.870225523664935로 산정했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 0.870225523664935 | 해당 좌표는 Cameron LNG T3의 2026년 7월 입력 record이며, Cameron LNG 전체의 짧은 운영 조정 성격에 맞춰 동일한 월별 Train 조정을 적용했다. 기준값 0.8971397151184897에 <5% 감소 범위 내 보수적 3% 하향을 적용하여 최종 가동률 0.870225523664935로 산정했다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | null | 0.36375 | 해당 좌표는 Cameron LNG T1의 2026년 7월 슬롯이며, 생산량 기준값이 제공되지 않아 선택 슬롯의 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산했다. <5% 미만의 미세 감산을 보수적으로 3% 하향으로 적용하여 최종 생산량을 0.36375 Mt LNG/month로 산정했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | null | 0.36375 | 해당 좌표는 Cameron LNG T2의 2026년 7월 슬롯이며, 생산량 기준값이 없어 Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 사용했다. 단기·부분 감산 시나리오에 맞춰 3% 하향을 반영하여 최종 생산량을 0.36375 Mt LNG/month로 산정했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | null | 0.36375 | 해당 좌표는 Cameron LNG T3의 2026년 7월 슬롯이며, 생산량 기준값이 제공되지 않아 동일 Train 명목용량 4.5 MTPA의 월간 환산치 0.375 Mt/month를 기준으로 삼았다. <5% 감소 및 급격한 정상화 조건을 반영해 3%만 하향하여 최종 생산량을 0.36375 Mt LNG/month로 산정했다. |

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
  "model_param_proposal_id": 59,
  "proposal_completed_dtm": "2026-07-07 21:09:35.575057",
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
      "rationale": "Utilization 변화량이 <5%로 제시되어 차질 대상 액화 Train의 월별 가동률을 직접 조정하는 LiqUtilAdjustment와 연결된다. 기간은 1개월 이하이고 회복 패턴은 급격하므로, Cameron LNG의 정상가동 기조를 유지하되 2026년 7월에만 미세 감산을 반영하고 이후 기간으로는 확장하지 않는다.",
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
          "proposedValue": 0.870225523664935,
          "rationale": "해당 좌표는 Cameron LNG T1의 2026년 7월 입력 record이며, 시나리오 기간이 1개월 이하로 제한되어 현재 기준월 슬롯만 조정했다. 기준값 0.8971397151184897에 미세 감산 성격을 반영해 <5% 범위 안의 보수적 3% 하향을 적용하여 최종 가동률 0.870225523664935로 산정했다."
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
          "proposedValue": 0.870225523664935,
          "rationale": "해당 좌표는 Cameron LNG T2의 2026년 7월 입력 record이며, 단기 운영 조정 후 급격히 정상화되는 시나리오이므로 같은 월 슬롯에만 조정을 적용했다. 기준값 0.8971397151184897에 <5% 미만의 제한적 감산을 보수적으로 3% 반영하여 최종 가동률 0.870225523664935로 산정했다."
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
          "proposedValue": 0.870225523664935,
          "rationale": "해당 좌표는 Cameron LNG T3의 2026년 7월 입력 record이며, Cameron LNG 전체의 짧은 운영 조정 성격에 맞춰 동일한 월별 Train 조정을 적용했다. 기준값 0.8971397151184897에 <5% 감소 범위 내 보수적 3% 하향을 적용하여 최종 가동률 0.870225523664935로 산정했다."
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
      "rationale": "Utilization 변화량이 <5%로 제한되어 생산량 자체의 구조적 손실보다는 단기·소폭 생산 감소를 표현하는 보조적 생산량 override와 연결된다. 기간은 1개월 이하이고 회복은 급격하므로, Cameron LNG의 정상가동 유지라는 전제 아래 2026년 7월 Train별 월간 생산량에만 제한적으로 하향 조정을 반영한다.",
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
          "proposedValue": 0.36375,
          "rationale": "해당 좌표는 Cameron LNG T1의 2026년 7월 슬롯이며, 생산량 기준값이 제공되지 않아 선택 슬롯의 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 환산했다. <5% 미만의 미세 감산을 보수적으로 3% 하향으로 적용하여 최종 생산량을 0.36375 Mt LNG/month로 산정했다."
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
          "proposedValue": 0.36375,
          "rationale": "해당 좌표는 Cameron LNG T2의 2026년 7월 슬롯이며, 생산량 기준값이 없어 Train 명목용량 4.5 MTPA를 월간 기준 0.375 Mt/month로 사용했다. 단기·부분 감산 시나리오에 맞춰 3% 하향을 반영하여 최종 생산량을 0.36375 Mt LNG/month로 산정했다."
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
          "proposedValue": 0.36375,
          "rationale": "해당 좌표는 Cameron LNG T3의 2026년 7월 슬롯이며, 생산량 기준값이 제공되지 않아 동일 Train 명목용량 4.5 MTPA의 월간 환산치 0.375 Mt/month를 기준으로 삼았다. <5% 감소 및 급격한 정상화 조건을 반영해 3%만 하향하여 최종 생산량을 0.36375 Mt LNG/month로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.914 | 4.914 | 2889 | 142 | 3031 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:05.267 | 65.267 | 12132 | 4471 | 16603 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:49.115 | 49.115 | 10809 | 2397 | 13206 |

#### scenario_id=106 3개월간 완전 증산 반영

- 소요시간: 02:15.734 (135.734s)
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
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 9 | Utilization 변화량 100%는 Cameron LNG의 정비 후 완전 생산 재개를 Train별 액화 가동률 override로 직접 반영하는 조건입니다. 기간 3개월은 적용 월 범위를 정하고, 회복 패턴상 추가 ramp-up 없이 정상가동 상태가 지속되는 구조로 해석하여 선택된 모든 Train에 동일한 상향 방향을 적용하되 가동률 상한에 맞춰 보수적으로 반영합니다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 3 | Utilization 변화량 100%는 Cameron LNG의 완전 생산 재개를 생산량 절대값 override로도 해석할 수 있는 직접 조건입니다. 기간 3개월은 적용 월을 한정하고, 회복 패턴상 별도 ramp-up 없이 정상 생산 수준이 지속되는 것으로 보아 Plant 월별 생산량을 동일한 full-rate 기준으로 제안합니다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 1.0 | 2026년 7월 Cameron LNG T1은 선택된 3개월 정상가동 반영 구간의 첫 월입니다. 기준 가동률 0.8971397151184897에서 완전 생산 재개 조건을 반영하되 ratio 입력 상한에 맞춰 최종 가동률을 1.0으로 제안합니다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 104, "Year": 2026}` | 0.9091015779867364 | 1.0 | 2026년 8월 Cameron LNG T1은 3개월 정상가동 유지 구간에 포함됩니다. 기준 가동률 0.9091015779867364에서 추가 ramp-up 없이 완전 가동 상태를 반영하여 최종 가동률을 1.0으로 제안합니다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 105, "Year": 2026}` | 0.8993102144292602 | 1.0 | 2026년 9월 Cameron LNG T1은 3개월 적용 기간의 마지막 월입니다. 기준 가동률 0.8993102144292602 대비 정상가동 유지 조건을 반영해 최종 가동률을 1.0으로 제안합니다. |
| 4 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 1.0 | 2026년 7월 Cameron LNG T2는 동일 Plant의 정상가동 반영 대상 Train입니다. 기준 가동률 0.8971397151184897에서 완전 생산 재개 조건을 반영하되 ratio 입력 상한에 맞춰 최종 가동률을 1.0으로 제안합니다. |
| 5 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 104, "Year": 2026}` | 0.9091015779867364 | 1.0 | 2026년 8월 Cameron LNG T2는 3개월 정상가동 유지 구간에 포함됩니다. 기준 가동률 0.9091015779867364에서 추가 단계적 회복 없이 완전 가동 상태를 반영하여 최종 가동률을 1.0으로 제안합니다. |
| 6 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 105, "Year": 2026}` | 0.8993102144292602 | 1.0 | 2026년 9월 Cameron LNG T2는 3개월 적용 기간의 마지막 월입니다. 기준 가동률 0.8993102144292602 대비 정상가동 유지 조건을 반영해 최종 가동률을 1.0으로 제안합니다. |
| 7 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 103, "Year": 2026}` | 0.8971397151184897 | 1.0 | 2026년 7월 Cameron LNG T3는 동일 Plant의 정상가동 반영 대상 Train입니다. 기준 가동률 0.8971397151184897에서 완전 생산 재개 조건을 반영하되 ratio 입력 상한에 맞춰 최종 가동률을 1.0으로 제안합니다. |
| 8 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 104, "Year": 2026}` | 0.9091015779867364 | 1.0 | 2026년 8월 Cameron LNG T3는 3개월 정상가동 유지 구간에 포함됩니다. 기준 가동률 0.9091015779867364에서 추가 단계적 회복 없이 완전 가동 상태를 반영하여 최종 가동률을 1.0으로 제안합니다. |
| 9 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 105, "Year": 2026}` | 0.8993102144292602 | 1.0 | 2026년 9월 Cameron LNG T3는 3개월 적용 기간의 마지막 월입니다. 기준 가동률 0.8993102144292602 대비 정상가동 유지 조건을 반영해 최종 가동률을 1.0으로 제안합니다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "Month": 7, "Period": 103, "Year": 2026}` | null | 1.125 | 2026년 7월은 3개월 완전 생산 반영 구간의 첫 월입니다. 해당 생산량 기준값이 제공되지 않았으므로 선택된 Cameron LNG 3개 Train의 명목용량 4.5 MTPA씩 총 13.5 MTPA를 월 단위로 환산해 13.5/12 = 1.125 Mt LNG/month를 최종 생산량으로 제안합니다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "Month": 8, "Period": 104, "Year": 2026}` | null | 1.125 | 2026년 8월은 정상가동 유지 기간에 포함되며 추가 ramp-up이 없는 월입니다. 생산량 기준값이 제공되지 않아 Cameron LNG 총 명목용량 13.5 MTPA의 월 환산값인 1.125 Mt LNG/month를 최종 생산량으로 제안합니다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "Month": 9, "Period": 105, "Year": 2026}` | null | 1.125 | 2026년 9월은 3개월 적용 기간의 마지막 월로, 정상 생산 수준이 지속되는 것으로 반영합니다. 생산량 기준값이 제공되지 않았으므로 Cameron LNG 총 명목용량 13.5 MTPA를 월 단위로 환산한 1.125 Mt LNG/month를 최종 생산량으로 제안합니다. |

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
  "model_param_proposal_id": 58,
  "proposal_completed_dtm": "2026-07-07 21:09:16.426059",
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
      "rationale": "Utilization 변화량 100%는 Cameron LNG의 정비 후 완전 생산 재개를 Train별 액화 가동률 override로 직접 반영하는 조건입니다. 기간 3개월은 적용 월 범위를 정하고, 회복 패턴상 추가 ramp-up 없이 정상가동 상태가 지속되는 구조로 해석하여 선택된 모든 Train에 동일한 상향 방향을 적용하되 가동률 상한에 맞춰 보수적으로 반영합니다.",
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
          "proposedValue": 1.0,
          "rationale": "2026년 7월 Cameron LNG T1은 선택된 3개월 정상가동 반영 구간의 첫 월입니다. 기준 가동률 0.8971397151184897에서 완전 생산 재개 조건을 반영하되 ratio 입력 상한에 맞춰 최종 가동률을 1.0으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.9091015779867364,
          "proposedValue": 1.0,
          "rationale": "2026년 8월 Cameron LNG T1은 3개월 정상가동 유지 구간에 포함됩니다. 기준 가동률 0.9091015779867364에서 추가 ramp-up 없이 완전 가동 상태를 반영하여 최종 가동률을 1.0으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 0.8993102144292602,
          "proposedValue": 1.0,
          "rationale": "2026년 9월 Cameron LNG T1은 3개월 적용 기간의 마지막 월입니다. 기준 가동률 0.8993102144292602 대비 정상가동 유지 조건을 반영해 최종 가동률을 1.0으로 제안합니다."
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
          "proposedValue": 1.0,
          "rationale": "2026년 7월 Cameron LNG T2는 동일 Plant의 정상가동 반영 대상 Train입니다. 기준 가동률 0.8971397151184897에서 완전 생산 재개 조건을 반영하되 ratio 입력 상한에 맞춰 최종 가동률을 1.0으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.9091015779867364,
          "proposedValue": 1.0,
          "rationale": "2026년 8월 Cameron LNG T2는 3개월 정상가동 유지 구간에 포함됩니다. 기준 가동률 0.9091015779867364에서 추가 단계적 회복 없이 완전 가동 상태를 반영하여 최종 가동률을 1.0으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 0.8993102144292602,
          "proposedValue": 1.0,
          "rationale": "2026년 9월 Cameron LNG T2는 3개월 적용 기간의 마지막 월입니다. 기준 가동률 0.8993102144292602 대비 정상가동 유지 조건을 반영해 최종 가동률을 1.0으로 제안합니다."
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
          "proposedValue": 1.0,
          "rationale": "2026년 7월 Cameron LNG T3는 동일 Plant의 정상가동 반영 대상 Train입니다. 기준 가동률 0.8971397151184897에서 완전 생산 재개 조건을 반영하되 ratio 입력 상한에 맞춰 최종 가동률을 1.0으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.9091015779867364,
          "proposedValue": 1.0,
          "rationale": "2026년 8월 Cameron LNG T3는 3개월 정상가동 유지 구간에 포함됩니다. 기준 가동률 0.9091015779867364에서 추가 단계적 회복 없이 완전 가동 상태를 반영하여 최종 가동률을 1.0으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "LNG Plant Train": "Cameron LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 0.8993102144292602,
          "proposedValue": 1.0,
          "rationale": "2026년 9월 Cameron LNG T3는 3개월 적용 기간의 마지막 월입니다. 기준 가동률 0.8993102144292602 대비 정상가동 유지 조건을 반영해 최종 가동률을 1.0으로 제안합니다."
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
      "rationale": "Utilization 변화량 100%는 Cameron LNG의 완전 생산 재개를 생산량 절대값 override로도 해석할 수 있는 직접 조건입니다. 기간 3개월은 적용 월을 한정하고, 회복 패턴상 별도 ramp-up 없이 정상 생산 수준이 지속되는 것으로 보아 Plant 월별 생산량을 동일한 full-rate 기준으로 제안합니다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "Month": 7,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.125,
          "rationale": "2026년 7월은 3개월 완전 생산 반영 구간의 첫 월입니다. 해당 생산량 기준값이 제공되지 않았으므로 선택된 Cameron LNG 3개 Train의 명목용량 4.5 MTPA씩 총 13.5 MTPA를 월 단위로 환산해 13.5/12 = 1.125 Mt LNG/month를 최종 생산량으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "Month": 8,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.125,
          "rationale": "2026년 8월은 정상가동 유지 기간에 포함되며 추가 ramp-up이 없는 월입니다. 생산량 기준값이 제공되지 않아 Cameron LNG 총 명목용량 13.5 MTPA의 월 환산값인 1.125 Mt LNG/month를 최종 생산량으로 제안합니다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Cameron LNG",
          "Month": 9,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.125,
          "rationale": "2026년 9월은 3개월 적용 기간의 마지막 월로, 정상 생산 수준이 지속되는 것으로 반영합니다. 생산량 기준값이 제공되지 않았으므로 Cameron LNG 총 명목용량 13.5 MTPA를 월 단위로 환산한 1.125 Mt LNG/month를 최종 생산량으로 제안합니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 18,
  "scenario_id": 106,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.162 | 4.162 | 2895 | 123 | 3018 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:52.379 | 52.379 | 12158 | 4062 | 16220 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:42.210 | 42.210 | 11336 | 3436 | 14772 |

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

- 소요시간: 02:33.798 (153.798s)
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
| Step2 selected slot | 9 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=9, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"4|altsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}, "parameter|4|supply|pipelineadjustment|pipelineadjustment": {"Month": 12, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PipelineAdjustment | `{"modelFile": "Supply", "modelSheet": "PipelineAdjustment", "tableName": "table1"}` | `["Year", "Month", "Pipeline name"]` | `["User adjusted capacity (Bcm/y)"]` | 1 | Utilization 변화 폭이 송출용량 대비 5% 미만으로 제시되어 PipelineAdjustment의 노선별 송출 capacity 조정과 직접 연결된다. 대체 공급원 가능성 100%는 부족분 보전보다는 TurkStream의 단기 소폭 송출 증가를 해당 노선에 한정해 반영하는 근거이며, 기간은 1개월 이하·단발적·급격 회복으로 해석되어 한시 적용한다. 제안값은 명시된 5월 TurkStream 송출 수준을 Bcm/y 형식의 최종 입력값으로 환산해 적용하고, 추가 기간으로 확장하지 않는다. |
| 2 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 8 | 대체 공급원 가능성 100%는 PNG 변동을 LNG 전환 또는 타 공급원 여력으로 흡수할 수 있음을 나타내며, LiqUtilAdjustment는 이 경우 가용 액화설비 가동률 배분 여부를 표현하는 parameter와 연결된다. 다만 이번 시나리오는 TurkStream 송출이 단기 소폭 증가하고 가격 영향도 중립으로 제시되어 LNG 대체 조달을 추가로 늘릴 필요가 작으므로, 선택된 액화설비의 가동률은 기준 수준을 유지하는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PipelineAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month": 5, "Pipeline name": "TurkStream", "Year": 2026}` | null | 17.3 | 선택된 좌표는 이벤트에서 명시된 5월 TurkStream 유럽행 송출 증가에 직접 대응한다. 기준 record가 없어 5월 일평균 4,740만 입방미터를 연율화해 0.0474 Bcm/d × 365 = 약 17.3 Bcm/y의 최종 송출 capacity override 값으로 산정했으며, 변화 폭이 5% 미만이고 단기 이벤트인 점을 반영해 별도 추가 상향은 적용하지 않았다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비의 2026년 기준 가동률 수준과 형식을 참고했다. 이벤트가 유럽 PNG 공급 증가로 LNG 대체수요를 완화하는 성격이고 대체 공급도 충분하므로, 추가 액화 가동률 상향 없이 보수적으로 0.9282를 유지값으로 적용한다. |
| 2 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T10", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 단기 소폭 PNG 송출 증가로 LNG 추가 조달 압력이 커지지 않는 시나리오이므로, 선택 train에 대해 0.9282의 유지값을 적용한다. |
| 3 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T11", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 영향 기간이 1개월 이하이고 LNG 전환 필요성이 제한적인 중립 시나리오이므로, 추가 조정 없이 0.9282를 최종 입력값으로 둔다. |
| 4 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T12", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. TurkStream 공급 증가는 LNG 대체수요를 낮추는 방향이나 규모가 작고 단발적이므로, 선택 train의 가동률은 0.9282로 유지한다. |
| 5 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T13", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 대체 공급이 충분하고 가격 영향이 중립인 조건에서는 LNG 액화 가동률 상향 배분을 적용하지 않는 것이 적절해 0.9282를 제안한다. |
| 6 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T14", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 시나리오상 PNG 공급 증가가 단기적이고 LNG 수급 충격으로 확대되지 않으므로, 해당 train은 0.9282의 유지값을 적용한다. |
| 7 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T15", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 대체 공급원 가능성이 충분해도 이번 경우는 LNG로 추가 대체할 차질이 아니라 소폭 PNG 송출 증가이므로, 가동률은 0.9282로 유지한다. |
| 8 | `{"Country": "United States", "LNG Plant": "Calcasieu Pass LNG", "LNG Plant Train": "Calcasieu Pass LNG T16", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 0.626, "Period": 110, "Year": 2026}` | null | 0.9282 | 해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 단기·단발적 PNG 송출 증가와 중립적 LNG 가격 영향을 고려해 추가 액화 가동률 조정 없이 0.9282를 최종 입력값으로 제안한다. |

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
  "model_param_proposal_id": 63,
  "proposal_completed_dtm": "2026-07-07 21:11:50.235494",
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
      "rationale": "Utilization 변화 폭이 송출용량 대비 5% 미만으로 제시되어 PipelineAdjustment의 노선별 송출 capacity 조정과 직접 연결된다. 대체 공급원 가능성 100%는 부족분 보전보다는 TurkStream의 단기 소폭 송출 증가를 해당 노선에 한정해 반영하는 근거이며, 기간은 1개월 이하·단발적·급격 회복으로 해석되어 한시 적용한다. 제안값은 명시된 5월 TurkStream 송출 수준을 Bcm/y 형식의 최종 입력값으로 환산해 적용하고, 추가 기간으로 확장하지 않는다.",
      "values": [
        {
          "Month": 5,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 17.3,
          "rationale": "선택된 좌표는 이벤트에서 명시된 5월 TurkStream 유럽행 송출 증가에 직접 대응한다. 기준 record가 없어 5월 일평균 4,740만 입방미터를 연율화해 0.0474 Bcm/d × 365 = 약 17.3 Bcm/y의 최종 송출 capacity override 값으로 산정했으며, 변화 폭이 5% 미만이고 단기 이벤트인 점을 반영해 별도 추가 상향은 적용하지 않았다."
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
      "rationale": "대체 공급원 가능성 100%는 PNG 변동을 LNG 전환 또는 타 공급원 여력으로 흡수할 수 있음을 나타내며, LiqUtilAdjustment는 이 경우 가용 액화설비 가동률 배분 여부를 표현하는 parameter와 연결된다. 다만 이번 시나리오는 TurkStream 송출이 단기 소폭 증가하고 가격 영향도 중립으로 제시되어 LNG 대체 조달을 추가로 늘릴 필요가 작으므로, 선택된 액화설비의 가동률은 기준 수준을 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비의 2026년 기준 가동률 수준과 형식을 참고했다. 이벤트가 유럽 PNG 공급 증가로 LNG 대체수요를 완화하는 성격이고 대체 공급도 충분하므로, 추가 액화 가동률 상향 없이 보수적으로 0.9282를 유지값으로 적용한다."
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
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 단기 소폭 PNG 송출 증가로 LNG 추가 조달 압력이 커지지 않는 시나리오이므로, 선택 train에 대해 0.9282의 유지값을 적용한다."
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
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 영향 기간이 1개월 이하이고 LNG 전환 필요성이 제한적인 중립 시나리오이므로, 추가 조정 없이 0.9282를 최종 입력값으로 둔다."
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
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. TurkStream 공급 증가는 LNG 대체수요를 낮추는 방향이나 규모가 작고 단발적이므로, 선택 train의 가동률은 0.9282로 유지한다."
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
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 대체 공급이 충분하고 가격 영향이 중립인 조건에서는 LNG 액화 가동률 상향 배분을 적용하지 않는 것이 적절해 0.9282를 제안한다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T14",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 시나리오상 PNG 공급 증가가 단기적이고 LNG 수급 충격으로 확대되지 않으므로, 해당 train은 0.9282의 유지값을 적용한다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T15",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 대체 공급원 가능성이 충분해도 이번 경우는 LNG로 추가 대체할 차질이 아니라 소폭 PNG 송출 증가이므로, 가동률은 0.9282로 유지한다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Calcasieu Pass LNG",
          "LNG Plant Train": "Calcasieu Pass LNG T16",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 0.626,
          "Period": 110,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.9282,
          "rationale": "해당 선택 좌표에는 직접 일치하는 기준 record가 없으므로, 동일 설비군의 2026년 기준 가동률 수준과 형식을 참고했다. 단기·단발적 PNG 송출 증가와 중립적 LNG 가격 영향을 고려해 추가 액화 가동률 조정 없이 0.9282를 최종 입력값으로 제안한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:07.725 | 7.725 | 2780 | 171 | 2951 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:49.326 | 49.326 | 12426 | 3431 | 15857 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:14.499 | 74.499 | 11251 | 3339 | 14590 |

#### scenario_id=286 [model_parameter_agent_test] 장기 송출 차질과 대체 공급 부족

- 소요시간: 03:53.188 (233.188s)
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
| Step3 value 결과 | value_cells=24, basecaseValue_present=12 | PASS |
| Step2 slot axis value 수 | `{"4|altsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}, "parameter|4|supply|pipelineadjustment|pipelineadjustment": {"Month": 12, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PipelineAdjustment | `{"modelFile": "Supply", "modelSheet": "PipelineAdjustment", "tableName": "table1"}` | `["Year", "Month", "Pipeline name"]` | `["User adjusted capacity (Bcm/y)"]` | 12 | Utilization 변화 폭 60%는 TurkStream 송출능력 자체를 낮추는 PipelineAdjustment와 직접 연결되며, 대체 공급원 가능성 25%는 차질분 중 일부만 완화될 수 있음을 의미한다. 기간 1년, 급격한 발생, 점진적 회복, 구조적 성격을 반영해 초기에는 큰 폭의 하향 조정을 적용하고 이후 12개월에 걸쳐 제한적으로 회복되는 절대 송출 capacity 값을 제안한다. |
| 2 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 12 | 대체 공급원 가능성 25%는 PNG 차질분 중 일부만 LNG 전환으로 보완되는 상황을 뜻하며, 이는 가용 액화설비의 utilization ratio를 상향 조정하는 LiqUtilAdjustment와 직접 연결된다. selected slot 중 대형 운영 설비인 미국 Sabine Pass T1-T2에 제한적으로 보완 물량을 배분하고, ratio 입력 형식의 상한 1.0을 넘지 않도록 1년 기간에 걸쳐 보수적으로 상향했다. |

##### Proposed Parameter Values

###### Proposed Values - PipelineAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month": 7, "Pipeline name": "TurkStream", "Year": 2026}` | null | 6.92 | TurkStream의 5월 일평균 공급 4,740만㎥/d를 연율화한 약 17.30 Bcm/y를 기준 규모로 보고, 급격한 60% 송출 차질을 즉시 반영해 40% 수준인 6.92 Bcm/y로 산정했다. |
| 2 | `{"Month": 8, "Pipeline name": "TurkStream", "Year": 2026}` | null | 7.16 | 1년 차질 기간 중 점진 회복을 반영해 초기 40% 수준에서 소폭 상향된 41.4% 수준을 적용했다. 대체 공급 가능성이 낮아 회복 폭은 제한적으로 두었다. |
| 3 | `{"Month": 9, "Pipeline name": "TurkStream", "Year": 2026}` | null | 7.39 | 동일한 연율화 기준 규모에 대해 점진 회복 경로를 이어 적용했다. 구조적 차질 시나리오이므로 정상 수준으로 빠르게 복귀하지 않고 약 42.7% 수준으로 제한했다. |
| 4 | `{"Month": 10, "Pipeline name": "TurkStream", "Year": 2026}` | null | 7.63 | 차질 발생 후 4개월차로 보아 회복 경로를 일부 반영하되, 대체 공급 부족을 고려해 약 44.1% 수준의 송출 capacity로 산정했다. |
| 5 | `{"Month": 11, "Pipeline name": "TurkStream", "Year": 2026}` | null | 7.86 | 점진 회복을 반영해 전월보다 소폭 높은 수준을 적용했다. 다만 60% 차질과 구조적 성격을 유지해 기준 규모의 약 45.5%에 그치도록 했다. |
| 6 | `{"Month": 12, "Pipeline name": "TurkStream", "Year": 2026}` | null | 8.1 | 연말까지도 대체 공급이 충분하지 않은 조건을 반영해 정상화가 아닌 제한적 회복만 적용했다. 기준 규모의 약 46.8% 수준으로 계산했다. |
| 7 | `{"Month": 1, "Pipeline name": "TurkStream", "Year": 2027}` | null | 8.34 | 1년 영향 기간의 후반부 진입에 따라 점진 회복을 이어 적용했다. 낮은 대체 공급 가능성을 감안해 약 48.2% 수준으로 제한했다. |
| 8 | `{"Month": 2, "Pipeline name": "TurkStream", "Year": 2027}` | null | 8.57 | 동일한 TurkStream 기준 규모에서 선형적인 제한 회복 경로를 적용했다. 정상 송출의 절반에 가까운 수준이나 완전 회복은 반영하지 않았다. |
| 9 | `{"Month": 3, "Pipeline name": "TurkStream", "Year": 2027}` | null | 8.81 | 점진 회복 패턴에 따라 전월보다 소폭 높은 capacity를 적용했다. 구조적 차질과 대체 공급 부족을 고려해 약 50.9% 수준으로 산정했다. |
| 10 | `{"Month": 4, "Pipeline name": "TurkStream", "Year": 2027}` | null | 9.04 | 차질 10개월차로 보아 회복 여지를 일부 반영했다. 그러나 60% 차질의 상당 부분이 유지되는 조건으로 약 52.3% 수준에 머물도록 했다. |
| 11 | `{"Month": 5, "Pipeline name": "TurkStream", "Year": 2027}` | null | 9.28 | 점진 회복 경로상 후반부 값을 적용했다. 대체 공급 가능성이 25%에 그치므로 기준 규모의 약 53.6% 수준으로 보수적으로 산정했다. |
| 12 | `{"Month": 6, "Pipeline name": "TurkStream", "Year": 2027}` | null | 9.52 | 1년 영향 기간의 마지막 월에도 구조적 차질이 남는 것으로 보고 완전 정상화 대신 약 55.0% 수준까지만 회복시켰다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 10, "Period": 112, "Year": 2026}` | 0.978 | 1 | 동일 설비의 해당 연월 기준 가동률 0.978에 제한적 LNG 전환 여지를 반영했다. 25% 대체 가능성에 따른 소폭 상향은 상한을 초과하므로 최종 입력값은 1.0으로 제한했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 10, "Period": 113, "Year": 2026}` | 0.978 | 1 | 기준 가동률 0.978에서 PNG 차질 보완을 위한 소폭 상향을 적용했다. ratio 상한을 고려해 1.0으로 캡핑했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 10, "Period": 114, "Year": 2026}` | 0.978 | 1 | 기준 가동률 0.978에 제한적 대체 LNG 공급 대응을 반영했다. 상향 후 값이 1.0을 넘지 않도록 최종값은 1.0으로 산정했다. |
| 4 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 10, "Period": 115, "Year": 2026}` | 0.978 | 1 | 기준 가동률 0.978에서 1년 차질 기간의 LNG 전환 수요를 반영했다. 설비 utilization ratio의 입력 상한을 적용해 1.0으로 제한했다. |
| 5 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 10, "Period": 116, "Year": 2026}` | 0.978 | 1 | 해당 월 기준값이 이미 높은 수준이므로 대체 공급 반영 후 상한에 도달하는 것으로 보았다. 최종 ratio 입력값은 1.0이다. |
| 6 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 10, "Period": 117, "Year": 2026}` | 0.978 | 1 | 기준 가동률 0.978에 PNG 차질 보완 목적의 제한적 상향을 적용했다. ratio 상한 때문에 최종값은 1.0으로 산정했다. |
| 7 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 10, "Period": 118, "Year": 2027}` | 0.9532752352743732 | 0.9782752352743732 | 기준 가동률 0.9532752352743733에 낮은 대체 가능성을 반영한 0.025p 상향을 적용했다. 상한 1.0 이내이므로 0.9782752352743733을 최종값으로 사용한다. |
| 8 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 10, "Period": 119, "Year": 2027}` | 0.9586746813514612 | 0.9836746813514614 | 기준 가동률 0.9586746813514613에 제한적 LNG 전환 대응분 0.025p를 더했다. 최종값은 0.9836746813514614이다. |
| 9 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 10, "Period": 120, "Year": 2027}` | 0.965192084044823 | 0.990192084044823 | 기준 가동률 0.965192084044823에 대체 LNG 공급 가능분을 보수적으로 0.025p 반영했다. 상한 이하이므로 0.990192084044823을 제안한다. |
| 10 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 10, "Period": 121, "Year": 2027}` | 0.9663020188579584 | 0.9913020188579584 | 기준 가동률 0.9663020188579585에 제한적 대체 공급 대응분 0.025p를 적용했다. 최종 입력값은 0.9913020188579585이다. |
| 11 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 10, "Period": 122, "Year": 2027}` | 0.9728194215513204 | 0.9978194215513204 | 기준 가동률 0.9728194215513204에 0.025p 상향을 적용했다. 1.0 상한에 근접하지만 초과하지 않아 0.9978194215513204를 최종값으로 둔다. |
| 12 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 10, "Period": 123, "Year": 2027}` | 0.9789641720392572 | 1 | 기준 가동률 0.9789641720392571에 제한적 LNG 전환분을 반영하면 상한을 초과하므로 최종 ratio는 1.0으로 캡핑했다. |

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
  "model_param_proposal_id": 66,
  "proposal_completed_dtm": "2026-07-07 21:13:28.763855",
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
      "rationale": "Utilization 변화 폭 60%는 TurkStream 송출능력 자체를 낮추는 PipelineAdjustment와 직접 연결되며, 대체 공급원 가능성 25%는 차질분 중 일부만 완화될 수 있음을 의미한다. 기간 1년, 급격한 발생, 점진적 회복, 구조적 성격을 반영해 초기에는 큰 폭의 하향 조정을 적용하고 이후 12개월에 걸쳐 제한적으로 회복되는 절대 송출 capacity 값을 제안한다.",
      "values": [
        {
          "Month": 7,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 6.92,
          "rationale": "TurkStream의 5월 일평균 공급 4,740만㎥/d를 연율화한 약 17.30 Bcm/y를 기준 규모로 보고, 급격한 60% 송출 차질을 즉시 반영해 40% 수준인 6.92 Bcm/y로 산정했다."
        },
        {
          "Month": 8,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 7.16,
          "rationale": "1년 차질 기간 중 점진 회복을 반영해 초기 40% 수준에서 소폭 상향된 41.4% 수준을 적용했다. 대체 공급 가능성이 낮아 회복 폭은 제한적으로 두었다."
        },
        {
          "Month": 9,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 7.39,
          "rationale": "동일한 연율화 기준 규모에 대해 점진 회복 경로를 이어 적용했다. 구조적 차질 시나리오이므로 정상 수준으로 빠르게 복귀하지 않고 약 42.7% 수준으로 제한했다."
        },
        {
          "Month": 10,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 7.63,
          "rationale": "차질 발생 후 4개월차로 보아 회복 경로를 일부 반영하되, 대체 공급 부족을 고려해 약 44.1% 수준의 송출 capacity로 산정했다."
        },
        {
          "Month": 11,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 7.86,
          "rationale": "점진 회복을 반영해 전월보다 소폭 높은 수준을 적용했다. 다만 60% 차질과 구조적 성격을 유지해 기준 규모의 약 45.5%에 그치도록 했다."
        },
        {
          "Month": 12,
          "Pipeline name": "TurkStream",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 8.1,
          "rationale": "연말까지도 대체 공급이 충분하지 않은 조건을 반영해 정상화가 아닌 제한적 회복만 적용했다. 기준 규모의 약 46.8% 수준으로 계산했다."
        },
        {
          "Month": 1,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 8.34,
          "rationale": "1년 영향 기간의 후반부 진입에 따라 점진 회복을 이어 적용했다. 낮은 대체 공급 가능성을 감안해 약 48.2% 수준으로 제한했다."
        },
        {
          "Month": 2,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 8.57,
          "rationale": "동일한 TurkStream 기준 규모에서 선형적인 제한 회복 경로를 적용했다. 정상 송출의 절반에 가까운 수준이나 완전 회복은 반영하지 않았다."
        },
        {
          "Month": 3,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 8.81,
          "rationale": "점진 회복 패턴에 따라 전월보다 소폭 높은 capacity를 적용했다. 구조적 차질과 대체 공급 부족을 고려해 약 50.9% 수준으로 산정했다."
        },
        {
          "Month": 4,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 9.04,
          "rationale": "차질 10개월차로 보아 회복 여지를 일부 반영했다. 그러나 60% 차질의 상당 부분이 유지되는 조건으로 약 52.3% 수준에 머물도록 했다."
        },
        {
          "Month": 5,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 9.28,
          "rationale": "점진 회복 경로상 후반부 값을 적용했다. 대체 공급 가능성이 25%에 그치므로 기준 규모의 약 53.6% 수준으로 보수적으로 산정했다."
        },
        {
          "Month": 6,
          "Pipeline name": "TurkStream",
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 9.52,
          "rationale": "1년 영향 기간의 마지막 월에도 구조적 차질이 남는 것으로 보고 완전 정상화 대신 약 55.0% 수준까지만 회복시켰다."
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
      "rationale": "대체 공급원 가능성 25%는 PNG 차질분 중 일부만 LNG 전환으로 보완되는 상황을 뜻하며, 이는 가용 액화설비의 utilization ratio를 상향 조정하는 LiqUtilAdjustment와 직접 연결된다. selected slot 중 대형 운영 설비인 미국 Sabine Pass T1-T2에 제한적으로 보완 물량을 배분하고, ratio 입력 형식의 상한 1.0을 넘지 않도록 1년 기간에 걸쳐 보수적으로 상향했다.",
      "values": [
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
          "proposedValue": 1,
          "rationale": "동일 설비의 해당 연월 기준 가동률 0.978에 제한적 LNG 전환 여지를 반영했다. 25% 대체 가능성에 따른 소폭 상향은 상한을 초과하므로 최종 입력값은 1.0으로 제한했다."
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
          "proposedValue": 1,
          "rationale": "기준 가동률 0.978에서 PNG 차질 보완을 위한 소폭 상향을 적용했다. ratio 상한을 고려해 1.0으로 캡핑했다."
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
          "proposedValue": 1,
          "rationale": "기준 가동률 0.978에 제한적 대체 LNG 공급 대응을 반영했다. 상향 후 값이 1.0을 넘지 않도록 최종값은 1.0으로 산정했다."
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
          "proposedValue": 1,
          "rationale": "기준 가동률 0.978에서 1년 차질 기간의 LNG 전환 수요를 반영했다. 설비 utilization ratio의 입력 상한을 적용해 1.0으로 제한했다."
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
          "proposedValue": 1,
          "rationale": "해당 월 기준값이 이미 높은 수준이므로 대체 공급 반영 후 상한에 도달하는 것으로 보았다. 최종 ratio 입력값은 1.0이다."
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
          "proposedValue": 1,
          "rationale": "기준 가동률 0.978에 PNG 차질 보완 목적의 제한적 상향을 적용했다. ratio 상한 때문에 최종값은 1.0으로 산정했다."
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
          "proposedValue": 0.9782752352743732,
          "rationale": "기준 가동률 0.9532752352743733에 낮은 대체 가능성을 반영한 0.025p 상향을 적용했다. 상한 1.0 이내이므로 0.9782752352743733을 최종값으로 사용한다."
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
          "proposedValue": 0.9836746813514614,
          "rationale": "기준 가동률 0.9586746813514613에 제한적 LNG 전환 대응분 0.025p를 더했다. 최종값은 0.9836746813514614이다."
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
          "proposedValue": 0.990192084044823,
          "rationale": "기준 가동률 0.965192084044823에 대체 LNG 공급 가능분을 보수적으로 0.025p 반영했다. 상한 이하이므로 0.990192084044823을 제안한다."
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
          "proposedValue": 0.9913020188579584,
          "rationale": "기준 가동률 0.9663020188579585에 제한적 대체 공급 대응분 0.025p를 적용했다. 최종 입력값은 0.9913020188579585이다."
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
          "proposedValue": 0.9978194215513204,
          "rationale": "기준 가동률 0.9728194215513204에 0.025p 상향을 적용했다. 1.0 상한에 근접하지만 초과하지 않아 0.9978194215513204를 최종값으로 둔다."
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
          "proposedValue": 1,
          "rationale": "기준 가동률 0.9789641720392571에 제한적 LNG 전환분을 반영하면 상한을 초과하므로 최종 ratio는 1.0으로 캡핑했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:05.608 | 5.608 | 2781 | 134 | 2915 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:42.211 | 102.211 | 12423 | 13679 | 26102 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:40.140 | 100.140 | 20205 | 7103 | 27308 |

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
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1개월 이하",
          "scenario_id": 287,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "6개월",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
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
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "100%",
          "scenario_id": 287,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "50%",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
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
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1 GW 미만",
          "scenario_id": 287,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3~5 GW",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "발전부문 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영",
      "dimension_key": "capacity_change_scale",
      "dimension_label": "Capacity 변화 규모",
      "mapping_method": "na",
      "model_target": null,
      "prompt_usage_policy": "excluded_from_parameter_slot_value_prompt",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "1 GW 미만",
          "scenario_id": 287,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "3~5 GW",
          "scenario_id": 288,
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
          "scenario_id": 287,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "급격",
          "scenario_id": 288,
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
          "scenario_id": 287,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "점진",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
    },
    {
      "canonical_parameter_name": null,
      "comment": "단발(정비·사고)/구조적(COD·폐쇄)",
      "dimension_key": "structural_change_yn",
      "dimension_label": "구조적 변동 여부",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": null,
      "scenario_dimension_values_by_scenario": [
        {
          "dimension_value": "단발적",
          "scenario_id": 287,
          "selected_in_scenario": true
        },
        {
          "dimension_value": "구조적",
          "scenario_id": 288,
          "selected_in_scenario": true
        }
      ],
      "selected_in_any_scenario": true,
      "selected_in_scenario": null
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
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=287 [model_parameter_agent_test] 단기 소규모 발전 차질 흡수

- 소요시간: 00:53.472 (53.472s)
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
  "narrative": "발전소 이용률 변화가 작고 다른 전원이 모두 흡수해 가스 수요 전이는 제한적이다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 51,
  "scenario_id": 287,
  "status": "created",
  "title": "[model_parameter_agent_test] 단기 소규모 발전 차질 흡수"
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
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모가 1GW 미만으로 제시되어 발전부문 가스 비중 조정이 필요한 경우에도 PowerMix의 Gas 비중 변화로 환산되는 폭은 제한적입니다. 타 에너지원 흡수 가능성이 100%로 제시되어 감소한 발전 이용률이 다른 전원으로 흡수되는 구조이므로, 가스 발전 비중에는 실질적인 전이 충격을 반영하지 않는 보수적 유지 방식이 적절합니다. 영향 기간은 1개월 이하이고 단발적이며 회복이 빠른 성격이므로 연간 PowerMix 입력에는 중립에 가까운 단기 조정만 반영합니다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.3 | 선택된 좌표는 2026년 United States의 Gas 발전 비중입니다. 해당 좌표에 직접 일치하는 기준값이 제공되지 않아, 제공된 동일 parameter의 2026년 Gas 비중들이 대체로 소수 비율 형식으로 입력된 점을 참고했습니다. 단기·소규모 차질이고 타 전원이 100% 흡수해 연간 가스 발전 비중 변화가 중립에 가까운 조건이므로, 기존 범위 내의 보수적 유지 수준으로 0.3을 제안합니다. |

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
  "model_param_proposal_id": 62,
  "proposal_completed_dtm": "2026-07-07 21:11:20.137979",
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
      "rationale": "Capacity 변화 규모가 1GW 미만으로 제시되어 발전부문 가스 비중 조정이 필요한 경우에도 PowerMix의 Gas 비중 변화로 환산되는 폭은 제한적입니다. 타 에너지원 흡수 가능성이 100%로 제시되어 감소한 발전 이용률이 다른 전원으로 흡수되는 구조이므로, 가스 발전 비중에는 실질적인 전이 충격을 반영하지 않는 보수적 유지 방식이 적절합니다. 영향 기간은 1개월 이하이고 단발적이며 회복이 빠른 성격이므로 연간 PowerMix 입력에는 중립에 가까운 단기 조정만 반영합니다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.3,
          "rationale": "선택된 좌표는 2026년 United States의 Gas 발전 비중입니다. 해당 좌표에 직접 일치하는 기준값이 제공되지 않아, 제공된 동일 parameter의 2026년 Gas 비중들이 대체로 소수 비율 형식으로 입력된 점을 참고했습니다. 단기·소규모 차질이고 타 전원이 100% 흡수해 연간 가스 발전 비중 변화가 중립에 가까운 조건이므로, 기존 범위 내의 보수적 유지 수준으로 0.3을 제안합니다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.259 | 3.259 | 2778 | 121 | 2899 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:17.435 | 17.435 | 6020 | 988 | 7008 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:16.248 | 16.248 | 7776 | 869 | 8645 |

#### scenario_id=288 [model_parameter_agent_test] 6개월 대규모 발전 차질 절반만 흡수

- 소요시간: 01:02.483 (62.483s)
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
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모는 발전부문 가동률·용량 차질을 Gas 발전 비중 조정으로 환산해야 하므로 PowerMix와 직접 연결된다. 타 에너지원 흡수 가능성은 차질분 중 대체 전원으로 이전되는 정도를 정해 Gas 비중의 하향 폭을 완화하는 역할을 하며, 6개월·급격 발생·점진 회복이라는 공통 맥락을 반영해 연간 입력값에는 보수적인 하향 조정으로 반영한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.397 | 선택 좌표에 일치하는 미국 Gas 2026 기준값이 없어 같은 PowerMix 입력의 2026년 Gas 비중 범위와 소수 형식을 참고했다. 가스 비중이 높은 발전 믹스의 보수적 기준을 0.400으로 두고, 3~5GW 차질은 중간값 기준의 대규모이나 50%가 타 에너지원으로 흡수되고 영향 기간이 연간 축의 절반인 6개월인 점을 반영해 약 0.3%p 하향한 최종 입력값으로 산정했다. |

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
  "model_param_proposal_id": 64,
  "proposal_completed_dtm": "2026-07-07 21:12:10.341528",
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
      "rationale": "Capacity 변화 규모는 발전부문 가동률·용량 차질을 Gas 발전 비중 조정으로 환산해야 하므로 PowerMix와 직접 연결된다. 타 에너지원 흡수 가능성은 차질분 중 대체 전원으로 이전되는 정도를 정해 Gas 비중의 하향 폭을 완화하는 역할을 하며, 6개월·급격 발생·점진 회복이라는 공통 맥락을 반영해 연간 입력값에는 보수적인 하향 조정으로 반영한다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.397,
          "rationale": "선택 좌표에 일치하는 미국 Gas 2026 기준값이 없어 같은 PowerMix 입력의 2026년 Gas 비중 범위와 소수 형식을 참고했다. 가스 비중이 높은 발전 믹스의 보수적 기준을 0.400으로 두고, 3~5GW 차질은 중간값 기준의 대규모이나 50%가 타 에너지원으로 흡수되고 영향 기간이 연간 축의 절반인 6개월인 점을 반영해 약 0.3%p 하향한 최종 입력값으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.508 | 3.508 | 2796 | 107 | 2903 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:11.927 | 11.927 | 6035 | 477 | 6512 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:24.493 | 24.493 | 7791 | 1366 | 9157 |

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

- 소요시간: 01:17.925 (77.925s)
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
| Step2 selected slot | 2 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=2, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 1 | 한파 강도 dimension이 기온 직접 입력 parameter와 연결되며, 약한 한파는 영향 국가·월의 Temperature를 하향 조정하는 근거가 된다. 기간은 1개월 이하이고 단발 피크 성격이므로 미국 3월 한 달에만 제한적으로 반영하되, 재고 여유와 가격 영향 중립성을 감안해 보수적인 하향 폭으로 제안한다. |
| 2 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 dimension이 발전 에너지원 비중 parameter와 직접 연결되며, 100% 흡수는 한파로 인한 추가 전력 수요가 가스 발전비중 상승으로 이어지지 않는다는 의미다. 짧고 약한 한파, 매우 여유로운 재고, 중립적 가격 영향과 정합되도록 Gas 비중은 상승 조정하지 않고 정상 수준의 보수적 값으로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Month": 3, "Year": 2026}` | null | 3.0 | 선택된 좌표는 사건에서 언급된 미국 중북부 3월 중순 한파와 직접 대응되는 미국 2026년 3월 월별 기온 입력이다. 미국 일치 기준값은 없으므로 동일 parameter의 2026년 3월 주요국 기온 형식과 범위를 참고했고, 약한 한파의 -2~-3℃ 편차가 단기·지역성에 그친다는 점을 반영해 월평균 국가값은 보수적으로 3.0℃로 설정했다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.42 | 선택된 좌표는 미국 2026년 Gas 발전비중 입력으로, 한파의 전력 수요 경로를 반영하는 가장 직접적인 슬롯이다. 미국 일치 기준값은 없으므로 동일 parameter의 2026년 Gas 발전비중 입력 형식과 주요 가스 발전 의존국의 범위를 참고했고, 대체 전원이 추가 수요를 모두 흡수한다는 조건에 따라 가스 비중을 상향하지 않는 정상 수준인 0.42로 설정했다. |

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
  "model_param_proposal_id": 65,
  "proposal_completed_dtm": "2026-07-07 21:12:38.072048",
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
      "rationale": "한파 강도 dimension이 기온 직접 입력 parameter와 연결되며, 약한 한파는 영향 국가·월의 Temperature를 하향 조정하는 근거가 된다. 기간은 1개월 이하이고 단발 피크 성격이므로 미국 3월 한 달에만 제한적으로 반영하되, 재고 여유와 가격 영향 중립성을 감안해 보수적인 하향 폭으로 제안한다.",
      "values": [
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 3.0,
          "rationale": "선택된 좌표는 사건에서 언급된 미국 중북부 3월 중순 한파와 직접 대응되는 미국 2026년 3월 월별 기온 입력이다. 미국 일치 기준값은 없으므로 동일 parameter의 2026년 3월 주요국 기온 형식과 범위를 참고했고, 약한 한파의 -2~-3℃ 편차가 단기·지역성에 그친다는 점을 반영해 월평균 국가값은 보수적으로 3.0℃로 설정했다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension이 발전 에너지원 비중 parameter와 직접 연결되며, 100% 흡수는 한파로 인한 추가 전력 수요가 가스 발전비중 상승으로 이어지지 않는다는 의미다. 짧고 약한 한파, 매우 여유로운 재고, 중립적 가격 영향과 정합되도록 Gas 비중은 상승 조정하지 않고 정상 수준의 보수적 값으로 제안한다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.42,
          "rationale": "선택된 좌표는 미국 2026년 Gas 발전비중 입력으로, 한파의 전력 수요 경로를 반영하는 가장 직접적인 슬롯이다. 미국 일치 기준값은 없으므로 동일 parameter의 2026년 Gas 발전비중 입력 형식과 주요 가스 발전 의존국의 범위를 참고했고, 대체 전원이 추가 수요를 모두 흡수한다는 조건에 따라 가스 비중을 상향하지 않는 정상 수준인 0.42로 설정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.631 | 3.631 | 2396 | 121 | 2517 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:13.184 | 13.184 | 5917 | 661 | 6578 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:39.535 | 39.535 | 7572 | 1603 | 9175 |

#### scenario_id=290 [model_parameter_agent_test] 3개월 강한 한파와 대체 제한

- 소요시간: 01:54.240 (114.240s)
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
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 3 | 한파 강도 dimension이 기온 직접 입력 parameter와 연결되며, ‘-5℃ 이하: 강’은 영향 국가·월의 Temperature를 하향 조정해야 하는 근거다. 기간과 지속 피크 정보는 적용 월 범위와 월별 배분을 정하는 공통 맥락으로 사용했으며, 미국 3개월 슬롯에 강한 한파가 지속되는 구조로 제안값을 설정했다. |
| 2 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 dimension이 발전 에너지원 비중 parameter와 직접 연결되며, 25% 흡수 가능성은 석탄·석유 등 대체 전원의 완충력이 제한되어 Gas 비중을 상향해야 함을 의미한다. 기간과 재고 부족, 지속 피크 정보는 연간 PowerMix에 반영되는 수요 압력의 지속성과 보수적 강도를 판단하는 공통 맥락으로 사용했다. |

##### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Month": 7, "Year": 2026}` | null | -5 | 해당 좌표에는 일치하는 미국 기준 기온값이 없어 제공된 다른 국가의 월별 기온 입력 형식과 한파 강도 구간을 참고했다. 강한 한파의 하한 경계인 -5℃를 최종 월 기온 입력값으로 적용하되, 지속 피크 조건이므로 첫 달부터 완화 없이 반영했다. |
| 2 | `{"Country": "United States", "Month": 8, "Year": 2026}` | null | -5 | 해당 좌표에는 일치하는 미국 기준 기온값이 없어 제공된 다른 국가의 월별 기온 입력 형식과 한파 강도 구간을 참고했다. 3개월 지속 및 지속 피크 조건에 맞춰 전월과 동일하게 강한 한파 경계값인 -5℃를 최종 월 기온 입력값으로 적용했다. |
| 3 | `{"Country": "United States", "Month": 9, "Year": 2026}` | null | -5 | 해당 좌표에는 일치하는 미국 기준 기온값이 없어 제공된 다른 국가의 월별 기온 입력 형식과 한파 강도 구간을 참고했다. 영향 기간의 마지막 달에도 지속 피크가 유지되는 설정이므로 강한 한파 경계값인 -5℃를 최종 월 기온 입력값으로 유지했다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.45 | 해당 좌표에는 일치하는 미국 기준 발전용 가스 비중값이 없어 제공된 다른 국가의 가스 발전 비중 범위와 소수 형식을 참고했다. 타 에너지원 흡수 가능성이 25%로 제한되어 발전용 가스 의존도가 높아지는 방향이지만, 3개월 영향이 연간 PowerMix 입력에 반영되는 점을 감안해 상단 범위에 가깝되 최대치보다는 보수적인 0.45를 최종 입력값으로 산정했다. |

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
  "model_param_proposal_id": 67,
  "proposal_completed_dtm": "2026-07-07 21:13:44.480646",
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
      "rationale": "한파 강도 dimension이 기온 직접 입력 parameter와 연결되며, ‘-5℃ 이하: 강’은 영향 국가·월의 Temperature를 하향 조정해야 하는 근거다. 기간과 지속 피크 정보는 적용 월 범위와 월별 배분을 정하는 공통 맥락으로 사용했으며, 미국 3개월 슬롯에 강한 한파가 지속되는 구조로 제안값을 설정했다.",
      "values": [
        {
          "Country": "United States",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -5,
          "rationale": "해당 좌표에는 일치하는 미국 기준 기온값이 없어 제공된 다른 국가의 월별 기온 입력 형식과 한파 강도 구간을 참고했다. 강한 한파의 하한 경계인 -5℃를 최종 월 기온 입력값으로 적용하되, 지속 피크 조건이므로 첫 달부터 완화 없이 반영했다."
        },
        {
          "Country": "United States",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -5,
          "rationale": "해당 좌표에는 일치하는 미국 기준 기온값이 없어 제공된 다른 국가의 월별 기온 입력 형식과 한파 강도 구간을 참고했다. 3개월 지속 및 지속 피크 조건에 맞춰 전월과 동일하게 강한 한파 경계값인 -5℃를 최종 월 기온 입력값으로 적용했다."
        },
        {
          "Country": "United States",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -5,
          "rationale": "해당 좌표에는 일치하는 미국 기준 기온값이 없어 제공된 다른 국가의 월별 기온 입력 형식과 한파 강도 구간을 참고했다. 영향 기간의 마지막 달에도 지속 피크가 유지되는 설정이므로 강한 한파 경계값인 -5℃를 최종 월 기온 입력값으로 유지했다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension이 발전 에너지원 비중 parameter와 직접 연결되며, 25% 흡수 가능성은 석탄·석유 등 대체 전원의 완충력이 제한되어 Gas 비중을 상향해야 함을 의미한다. 기간과 재고 부족, 지속 피크 정보는 연간 PowerMix에 반영되는 수요 압력의 지속성과 보수적 강도를 판단하는 공통 맥락으로 사용했다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 좌표에는 일치하는 미국 기준 발전용 가스 비중값이 없어 제공된 다른 국가의 가스 발전 비중 범위와 소수 형식을 참고했다. 타 에너지원 흡수 가능성이 25%로 제한되어 발전용 가스 의존도가 높아지는 방향이지만, 3개월 영향이 연간 PowerMix 입력에 반영되는 점을 감안해 상단 범위에 가깝되 최대치보다는 보수적인 0.45를 최종 입력값으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.246 | 3.246 | 2389 | 113 | 2502 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:53.434 | 53.434 | 5906 | 3271 | 9177 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:41.047 | 41.047 | 7637 | 1804 | 9441 |

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

- 소요시간: 01:43.473 (103.473s)
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
| Step3 value 결과 | value_cells=4, basecaseValue_present=4 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 2 | 폭염 강도 차원이 기온 직접 입력 파라미터와 연결되며, 약한 폭염은 Temperature를 소폭 상향하는 근거가 된다. 기간은 1개월 이하이고 피크가 단발성인 점을 반영해 선택된 하절기 슬롯에만 보수적인 1℃ 상향을 적용하며, 재고 여유와 전원 흡수 가능성은 기온 자체가 아니라 수요 반응 완화 맥락으로만 보았다. |
| 2 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 2 | 타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 파라미터와 직접 연결되며, 100% 흡수는 추가 냉방 전력 수요가 가스 발전 비중 확대로 이어지지 않는다는 의미로 해석된다. 약한 단기 폭염과 중립적 가격 영향에 맞춰 선택된 가스 발전 비중은 기준 수준을 유지하는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 10.4 | 11.4 | 해당 좌표의 일치 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 가장 최근·상단에 해당하는 값을 형식과 보수적 기준 수준으로 참고했다. 약한 폭염 범위(+1~+2℃)와 1개월 이하 단발 피크를 반영해 하단부인 +1.0℃만 더해 11.4℃를 최종 입력값으로 제안한다. |
| 2 | `{"Country": "Japan", "Month": 7, "Year": 2026}` | 9.2 | 10.2 | 해당 좌표의 일치 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 가장 최근·상단에 해당하는 값을 형식과 보수적 기준 수준으로 참고했다. 약한 폭염 범위(+1~+2℃)와 1개월 이하 단발 피크를 반영해 하단부인 +1.0℃만 더해 10.2℃를 최종 입력값으로 제안한다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0346 | 해당 좌표에는 2026년 가스 발전 비중 기준값이 존재한다. 타 에너지원이 추가 전력 수요를 100% 흡수하는 설정이므로 가스 비중을 상향하지 않고 기준값 0.0346을 그대로 최종 입력값으로 유지한다. |
| 2 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.323 | 해당 좌표에는 2026년 가스 발전 비중 기준값이 존재한다. 타 에너지원이 추가 전력 수요를 100% 흡수하는 설정이므로 가스 비중을 상향하지 않고 기준값 0.323을 그대로 최종 입력값으로 유지한다. |

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
  "model_param_proposal_id": 68,
  "proposal_completed_dtm": "2026-07-07 21:13:53.762600",
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
      "rationale": "폭염 강도 차원이 기온 직접 입력 파라미터와 연결되며, 약한 폭염은 Temperature를 소폭 상향하는 근거가 된다. 기간은 1개월 이하이고 피크가 단발성인 점을 반영해 선택된 하절기 슬롯에만 보수적인 1℃ 상향을 적용하며, 재고 여유와 전원 흡수 가능성은 기온 자체가 아니라 수요 반응 완화 맥락으로만 보았다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 10.4,
          "proposedValue": 11.4,
          "rationale": "해당 좌표의 일치 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 가장 최근·상단에 해당하는 값을 형식과 보수적 기준 수준으로 참고했다. 약한 폭염 범위(+1~+2℃)와 1개월 이하 단발 피크를 반영해 하단부인 +1.0℃만 더해 11.4℃를 최종 입력값으로 제안한다."
        },
        {
          "Country": "Japan",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 9.2,
          "proposedValue": 10.2,
          "rationale": "해당 좌표의 일치 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 가장 최근·상단에 해당하는 값을 형식과 보수적 기준 수준으로 참고했다. 약한 폭염 범위(+1~+2℃)와 1개월 이하 단발 피크를 반영해 하단부인 +1.0℃만 더해 10.2℃를 최종 입력값으로 제안한다."
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
      "rationale": "타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 파라미터와 직접 연결되며, 100% 흡수는 추가 냉방 전력 수요가 가스 발전 비중 확대로 이어지지 않는다는 의미로 해석된다. 약한 단기 폭염과 중립적 가격 영향에 맞춰 선택된 가스 발전 비중은 기준 수준을 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0346,
          "rationale": "해당 좌표에는 2026년 가스 발전 비중 기준값이 존재한다. 타 에너지원이 추가 전력 수요를 100% 흡수하는 설정이므로 가스 비중을 상향하지 않고 기준값 0.0346을 그대로 최종 입력값으로 유지한다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.323,
          "rationale": "해당 좌표에는 2026년 가스 발전 비중 기준값이 존재한다. 타 에너지원이 추가 전력 수요를 100% 흡수하는 설정이므로 가스 비중을 상향하지 않고 기준값 0.323을 그대로 최종 입력값으로 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.018 | 4.018 | 2623 | 124 | 2747 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:18.797 | 18.797 | 6331 | 1176 | 7507 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:02.932 | 62.932 | 8059 | 1818 | 9877 |

#### scenario_id=292 [model_parameter_agent_test] 3개월 강한 폭염과 전원 흡수 부족

- 소요시간: 01:32.969 (92.969s)
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
| Step2 selected slot | 8 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=8, basecaseValue_present=2 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 6 | 폭염 강도 차원이 기온 직접 입력 파라미터와 연결되며, '+3℃ 이상: 강'은 영향 국가·월의 Temperature를 상향 조정하는 근거다. 기간은 3개월, 피크 패턴은 지속 피크로 해석하여 2026년 7~9월 중국·일본에 같은 방향의 상향 조정을 적용하되, 월별 단일 피크보다는 기간 전반의 지속적인 고온을 반영했다. |
| 2 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 2 | 타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 파라미터와 직접 연결되며, 25%는 재생에너지·원전 등 비가스 전원의 흡수 여력이 낮아 냉방 및 발전 수요 증가분 중 상당 부분이 가스 발전 비중 상승으로 이어질 수 있음을 의미한다. 다만 PowerMix는 연간 비중 입력이므로 3개월 폭염 효과를 연간값에 보수적으로 희석하여 Gas 비중을 소폭 상향하는 구조로 제안했다. |

##### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | null | 13.4 | 선택 좌표는 2026년 7월 중국이다. 해당 월의 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 고점인 10.4℃를 형식·스케일 참고용 보수적 기준으로 사용하고, 강한 폭염의 최소 직접 조정폭인 +3.0℃를 더해 13.4℃로 제안했다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | null | 13.4 | 선택 좌표는 2026년 8월 중국이다. 해당 월 기준값이 없어 같은 국가의 제공 기준값 고점 10.4℃를 보수적 기준으로 두고, 지속 피크 조건상 7~9월에 동일한 강도인 +3.0℃를 적용해 13.4℃로 산정했다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | null | 13.4 | 선택 좌표는 2026년 9월 중국이다. 해당 월 기준값이 제공되지 않았으므로 같은 국가의 제공 기준값 고점 10.4℃를 참고 기준으로 사용했으며, 3개월 지속 폭염의 후반부도 피크가 유지되는 조건으로 보아 +3.0℃를 반영한 13.4℃를 제안했다. |
| 4 | `{"Country": "Japan", "Month": 7, "Year": 2026}` | null | 12.2 | 선택 좌표는 2026년 7월 일본이다. 해당 월 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 고점인 9.2℃를 형식·스케일 참고용 보수적 기준으로 사용하고, 강한 폭염의 최소 직접 조정폭 +3.0℃를 더해 12.2℃로 제안했다. |
| 5 | `{"Country": "Japan", "Month": 8, "Year": 2026}` | null | 12.2 | 선택 좌표는 2026년 8월 일본이다. 해당 월 기준값이 없어 같은 국가의 제공 기준값 고점 9.2℃를 보수적 기준으로 두고, 지속 피크 조건상 단일 월 집중이 아니라 동일한 +3.0℃ 상향을 적용해 12.2℃로 산정했다. |
| 6 | `{"Country": "Japan", "Month": 9, "Year": 2026}` | null | 12.2 | 선택 좌표는 2026년 9월 일본이다. 해당 월 기준값이 제공되지 않았으므로 같은 국가의 제공 기준값 고점 9.2℃를 참고 기준으로 사용했으며, 3개월 지속 폭염 조건을 반영해 +3.0℃를 더한 12.2℃를 제안했다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0363 | 선택 좌표는 2026년 중국 Gas 발전 비중이며 기준값은 0.0346이다. 비가스 전원의 흡수 가능성이 25%로 낮아 잔여 발전 수요가 가스에 일부 전가된다고 보되, 연간 PowerMix 입력인 점을 반영해 기준값에 보수적 5% 상대 상향을 적용하여 0.0363으로 산정했다. |
| 2 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.3392 | 선택 좌표는 2026년 일본 Gas 발전 비중이며 기준값은 0.323이다. 3개월 강한 폭염과 낮은 타 전원 흡수 여력을 반영하되 연간 비중의 과도한 변화를 피하기 위해 기준값에 보수적 5% 상대 상향을 적용하여 0.3392로 제안했다. |

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
  "model_param_proposal_id": 69,
  "proposal_completed_dtm": "2026-07-07 21:14:11.047057",
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
      "rationale": "폭염 강도 차원이 기온 직접 입력 파라미터와 연결되며, '+3℃ 이상: 강'은 영향 국가·월의 Temperature를 상향 조정하는 근거다. 기간은 3개월, 피크 패턴은 지속 피크로 해석하여 2026년 7~9월 중국·일본에 같은 방향의 상향 조정을 적용하되, 월별 단일 피크보다는 기간 전반의 지속적인 고온을 반영했다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 13.4,
          "rationale": "선택 좌표는 2026년 7월 중국이다. 해당 월의 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 고점인 10.4℃를 형식·스케일 참고용 보수적 기준으로 사용하고, 강한 폭염의 최소 직접 조정폭인 +3.0℃를 더해 13.4℃로 제안했다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 13.4,
          "rationale": "선택 좌표는 2026년 8월 중국이다. 해당 월 기준값이 없어 같은 국가의 제공 기준값 고점 10.4℃를 보수적 기준으로 두고, 지속 피크 조건상 7~9월에 동일한 강도인 +3.0℃를 적용해 13.4℃로 산정했다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 13.4,
          "rationale": "선택 좌표는 2026년 9월 중국이다. 해당 월 기준값이 제공되지 않았으므로 같은 국가의 제공 기준값 고점 10.4℃를 참고 기준으로 사용했으며, 3개월 지속 폭염의 후반부도 피크가 유지되는 조건으로 보아 +3.0℃를 반영한 13.4℃를 제안했다."
        },
        {
          "Country": "Japan",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 12.2,
          "rationale": "선택 좌표는 2026년 7월 일본이다. 해당 월 기준값이 제공되지 않아 같은 국가의 제공 기준값 중 고점인 9.2℃를 형식·스케일 참고용 보수적 기준으로 사용하고, 강한 폭염의 최소 직접 조정폭 +3.0℃를 더해 12.2℃로 제안했다."
        },
        {
          "Country": "Japan",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 12.2,
          "rationale": "선택 좌표는 2026년 8월 일본이다. 해당 월 기준값이 없어 같은 국가의 제공 기준값 고점 9.2℃를 보수적 기준으로 두고, 지속 피크 조건상 단일 월 집중이 아니라 동일한 +3.0℃ 상향을 적용해 12.2℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 12.2,
          "rationale": "선택 좌표는 2026년 9월 일본이다. 해당 월 기준값이 제공되지 않았으므로 같은 국가의 제공 기준값 고점 9.2℃를 참고 기준으로 사용했으며, 3개월 지속 폭염 조건을 반영해 +3.0℃를 더한 12.2℃를 제안했다."
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
      "rationale": "타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 파라미터와 직접 연결되며, 25%는 재생에너지·원전 등 비가스 전원의 흡수 여력이 낮아 냉방 및 발전 수요 증가분 중 상당 부분이 가스 발전 비중 상승으로 이어질 수 있음을 의미한다. 다만 PowerMix는 연간 비중 입력이므로 3개월 폭염 효과를 연간값에 보수적으로 희석하여 Gas 비중을 소폭 상향하는 구조로 제안했다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0363,
          "rationale": "선택 좌표는 2026년 중국 Gas 발전 비중이며 기준값은 0.0346이다. 비가스 전원의 흡수 가능성이 25%로 낮아 잔여 발전 수요가 가스에 일부 전가된다고 보되, 연간 PowerMix 입력인 점을 반영해 기준값에 보수적 5% 상대 상향을 적용하여 0.0363으로 산정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.3392,
          "rationale": "선택 좌표는 2026년 일본 Gas 발전 비중이며 기준값은 0.323이다. 3개월 강한 폭염과 낮은 타 전원 흡수 여력을 반영하되 연간 비중의 과도한 변화를 피하기 위해 기준값에 보수적 5% 상대 상향을 적용하여 0.3392로 제안했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.716 | 3.716 | 2618 | 111 | 2729 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:18.726 | 18.726 | 6322 | 1024 | 7346 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:52.474 | 52.474 | 8198 | 3234 | 11432 |

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

- 소요시간: 01:03.851 (63.851s)
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
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 1 | 원전 이용률 저하에 따른 발전 공백은 전력믹스 내 에너지원 비중 조정으로 반영될 수 있어 PowerMix가 선택된다. 다만 Capacity 변화 규모가 1GW 미만으로 작고, 타 에너지원 흡수 가능성이 100%로 제시되어 가스 비중으로의 직접 대체보다는 기존 가스 발전 비중을 유지하는 보수적 적용이 적절하다. 영향 기간도 1개월 이하의 단발적 차질이므로 연간 전력믹스 입력에는 추가 상향을 반영하지 않는다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.285 | 해당 좌표는 선택된 한국 2026년 가스 발전 비중 입력이며, 기준값 0.285가 현재 연간 전력믹스의 가스 비중이다. 원전 차질은 1GW 미만·1개월 이하이고 다른 전원이 전량 흡수하는 조건이므로, 가스 비중 추가 상승 없이 기준값과 동일한 0.285를 최종 입력값으로 유지한다. |

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
  "model_param_proposal_id": 70,
  "proposal_completed_dtm": "2026-07-07 21:14:32.625937",
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
      "rationale": "원전 이용률 저하에 따른 발전 공백은 전력믹스 내 에너지원 비중 조정으로 반영될 수 있어 PowerMix가 선택된다. 다만 Capacity 변화 규모가 1GW 미만으로 작고, 타 에너지원 흡수 가능성이 100%로 제시되어 가스 비중으로의 직접 대체보다는 기존 가스 발전 비중을 유지하는 보수적 적용이 적절하다. 영향 기간도 1개월 이하의 단발적 차질이므로 연간 전력믹스 입력에는 추가 상향을 반영하지 않는다.",
      "values": [
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.285,
          "rationale": "해당 좌표는 선택된 한국 2026년 가스 발전 비중 입력이며, 기준값 0.285가 현재 연간 전력믹스의 가스 비중이다. 원전 차질은 1GW 미만·1개월 이하이고 다른 전원이 전량 흡수하는 조건이므로, 가스 비중 추가 상승 없이 기준값과 동일한 0.285를 최종 입력값으로 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:09.347 | 9.347 | 2183 | 112 | 2295 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:13.818 | 13.818 | 5466 | 391 | 5857 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:10.732 | 10.732 | 7222 | 576 | 7798 |

#### scenario_id=294 [model_parameter_agent_test] 6개월 원전 차질과 LNG 대체수요

- 소요시간: 01:12.652 (72.652s)
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
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모 3~5 GW는 원전 출력 공백이 전력믹스 내 원전 비중 하락과 가스 대체 발전 확대를 유발한다는 점에서 PowerMix 조정과 직접 연결된다. 타 에너지원 흡수 가능성 50%는 재생에너지·석탄 등이 일부 공백을 흡수해 가스 비중 상향 폭을 완화하는 역할이며, 영향 기간 6개월과 점진적 회복은 연간 비중에 반영될 충격을 제한한다. 이에 한국의 가스 발전 비중을 2026년에 한해 보수적으로 상향 조정한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.3 | 2026년 South Korea Gas의 기준 PowerMix 값은 0.285이다. 원전 차질 3~5 GW의 중간값인 약 4 GW가 6개월 지속되고, 그중 50%만 가스 발전으로 대체된다고 보아 연간 발전믹스 기준 약 1.5%p 내외의 가스 비중 증가를 반영해 최종 입력값을 0.300으로 산정했다. |

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
  "model_param_proposal_id": 71,
  "proposal_completed_dtm": "2026-07-07 21:14:57.144278",
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
      "rationale": "Capacity 변화 규모 3~5 GW는 원전 출력 공백이 전력믹스 내 원전 비중 하락과 가스 대체 발전 확대를 유발한다는 점에서 PowerMix 조정과 직접 연결된다. 타 에너지원 흡수 가능성 50%는 재생에너지·석탄 등이 일부 공백을 흡수해 가스 비중 상향 폭을 완화하는 역할이며, 영향 기간 6개월과 점진적 회복은 연간 비중에 반영될 충격을 제한한다. 이에 한국의 가스 발전 비중을 2026년에 한해 보수적으로 상향 조정한다.",
      "values": [
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.3,
          "rationale": "2026년 South Korea Gas의 기준 PowerMix 값은 0.285이다. 원전 차질 3~5 GW의 중간값인 약 4 GW가 6개월 지속되고, 그중 50%만 가스 발전으로 대체된다고 보아 연간 발전믹스 기준 약 1.5%p 내외의 가스 비중 증가를 반영해 최종 입력값을 0.300으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:15.520 | 15.520 | 2189 | 93 | 2282 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:05.951 | 5.951 | 5469 | 242 | 5711 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:27.509 | 27.509 | 7225 | 854 | 8079 |

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

- 소요시간: 01:11.493 (71.493s)
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
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 7 | Capacity 변화 규모가 1GW 미만으로 제한되어 재생 출력 약세가 발전 믹스 내 가스 비중에 미칠 수 있는 직접 변수로 연결되지만, 타 에너지원 흡수 가능성이 100%로 제시되어 석탄·원전·수입전력 등이 추가 전력수요를 흡수하는 구조입니다. 영향 기간도 1개월 이하의 단기 요인에 그쳐 연간 PowerMix 입력에서는 유럽 주요국 가스 비중을 기준 수준으로 유지하는 보수적 적용이 적절합니다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.19 | 해당 좌표는 2026년 Belgium의 Gas 발전비중 record입니다. 기준값 0.19에 대해 영향 기간이 짧고 대체 전원이 100% 흡수하는 시나리오이므로 연간 가스 발전비중을 추가 상향하지 않고 0.19로 유지합니다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.042 | 해당 좌표는 2026년 France의 Gas 발전비중 record입니다. 기준값 0.042에 대해 단기 재생 출력 약세가 있더라도 원전 등 대체 전원이 흡수하는 설정이므로 연간 가스 발전비중을 0.042로 유지합니다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.135 | 해당 좌표는 2026년 Germany의 Gas 발전비중 record입니다. 기준값 0.135에 대해 변화 규모가 1GW 미만이고 1개월 이하로 제한되며 대체 전원 흡수율이 100%이므로 연간 비중 조정 없이 0.135를 적용합니다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.434 | 해당 좌표는 2026년 Italy의 Gas 발전비중 record입니다. 기준값 0.434에 대해 폭염·재생 약세에 따른 단기 전력수요 압력이 있어도 다른 전원이 전부 흡수하는 케이스이므로 연간 가스 비중은 0.434로 유지합니다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.31818965517241377 | 해당 좌표는 2026년 Netherlands의 Gas 발전비중 record입니다. 기준값 0.31818965517241377에 대해 추가 가스발전 호출이 짧고 대체 전원으로 흡수되는 조건을 반영해 연간 입력값을 0.31818965517241377로 유지합니다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.213 | 해당 좌표는 2026년 Spain의 Gas 발전비중 record입니다. 기준값 0.213에 대해 재생 출력 부진의 영향이 소규모·단기에 그치고 대체 전원이 모두 흡수하므로 연간 가스 비중을 0.213으로 유지합니다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.29 | 해당 좌표는 2026년 United Kingdom의 Gas 발전비중 record입니다. 기준값 0.29에 대해 1개월 이하의 제한적 전력수급 변수와 100% 대체 흡수 조건을 반영해 연간 Gas 비중을 0.29로 유지합니다. |

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
  "model_param_proposal_id": 72,
  "proposal_completed_dtm": "2026-07-07 21:15:05.422931",
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
      "rationale": "Capacity 변화 규모가 1GW 미만으로 제한되어 재생 출력 약세가 발전 믹스 내 가스 비중에 미칠 수 있는 직접 변수로 연결되지만, 타 에너지원 흡수 가능성이 100%로 제시되어 석탄·원전·수입전력 등이 추가 전력수요를 흡수하는 구조입니다. 영향 기간도 1개월 이하의 단기 요인에 그쳐 연간 PowerMix 입력에서는 유럽 주요국 가스 비중을 기준 수준으로 유지하는 보수적 적용이 적절합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19,
          "rationale": "해당 좌표는 2026년 Belgium의 Gas 발전비중 record입니다. 기준값 0.19에 대해 영향 기간이 짧고 대체 전원이 100% 흡수하는 시나리오이므로 연간 가스 발전비중을 추가 상향하지 않고 0.19로 유지합니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "해당 좌표는 2026년 France의 Gas 발전비중 record입니다. 기준값 0.042에 대해 단기 재생 출력 약세가 있더라도 원전 등 대체 전원이 흡수하는 설정이므로 연간 가스 발전비중을 0.042로 유지합니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.135,
          "rationale": "해당 좌표는 2026년 Germany의 Gas 발전비중 record입니다. 기준값 0.135에 대해 변화 규모가 1GW 미만이고 1개월 이하로 제한되며 대체 전원 흡수율이 100%이므로 연간 비중 조정 없이 0.135를 적용합니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.434,
          "rationale": "해당 좌표는 2026년 Italy의 Gas 발전비중 record입니다. 기준값 0.434에 대해 폭염·재생 약세에 따른 단기 전력수요 압력이 있어도 다른 전원이 전부 흡수하는 케이스이므로 연간 가스 비중은 0.434로 유지합니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.31818965517241377,
          "rationale": "해당 좌표는 2026년 Netherlands의 Gas 발전비중 record입니다. 기준값 0.31818965517241377에 대해 추가 가스발전 호출이 짧고 대체 전원으로 흡수되는 조건을 반영해 연간 입력값을 0.31818965517241377로 유지합니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.213,
          "rationale": "해당 좌표는 2026년 Spain의 Gas 발전비중 record입니다. 기준값 0.213에 대해 재생 출력 부진의 영향이 소규모·단기에 그치고 대체 전원이 모두 흡수하므로 연간 가스 비중을 0.213으로 유지합니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29,
          "rationale": "해당 좌표는 2026년 United Kingdom의 Gas 발전비중 record입니다. 기준값 0.29에 대해 1개월 이하의 제한적 전력수급 변수와 100% 대체 흡수 조건을 반영해 연간 Gas 비중을 0.29로 유지합니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 44,
  "scenario_id": 261,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.297 | 4.297 | 2579 | 122 | 2701 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:14.074 | 14.074 | 5473 | 971 | 6444 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:23.023 | 23.023 | 7459 | 1292 | 8751 |

#### scenario_id=262 석 달간 절반만 흡수되는 유럽 가스발전 수요

- 소요시간: 01:13.234 (73.234s)
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
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 7 | 재생 출력 약세에 따른 Capacity 변화 규모는 재생 전용 입력이 아닌 발전원별 비중 조정으로 반영되므로 가스 발전 비중 상향이 직접 연결됩니다. 타 에너지원 흡수 가능성 50%는 석탄·원전 등 다른 전원이 절반을 흡수하고 남은 공백만 가스가 담당한다는 완화 조건으로 적용했습니다. 영향 기간은 3개월로 제한되므로 연간 PowerMix 입력에는 단기 충격을 연율화해 보수적인 소폭 상향으로 반영합니다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.192 | 해당 좌표의 기준 가스 발전 비중 0.19를 현재 기준값으로 사용했습니다. 3개월 지속 충격을 연간 비중에 반영하고, 대체 전원이 절반을 흡수한다는 조건을 감안해 상대적으로 작은 +0.002를 더한 0.192를 최종 입력값으로 제안합니다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.043 | 해당 좌표의 기준 가스 발전 비중 0.042를 현재 기준값으로 사용했습니다. 프랑스는 기준 가스 비중이 낮고 타 전원의 흡수 여지가 큰 편이므로, 3개월 영향과 50% 흡수 조건을 반영해 보수적으로 +0.001만 상향한 0.043을 제안합니다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.138 | 해당 좌표의 기준 가스 발전 비중 0.135를 현재 기준값으로 사용했습니다. 풍력 약세가 가스발전 호출로 이어질 수 있는 직접성이 높지만 영향 기간이 3개월이고 절반은 타 전원이 흡수하므로, 연간 입력에는 +0.003을 반영해 0.138로 산정했습니다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.438 | 해당 좌표의 기준 가스 발전 비중 0.434를 현재 기준값으로 사용했습니다. 기준 가스 의존도가 높아 재생·수력 약세 시 가스발전 대체가 비교적 크게 나타날 수 있으므로, 3개월 연율화와 50% 흡수 조건을 적용하되 선택 국가 중 큰 폭인 +0.004를 반영해 0.438을 제안합니다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.32168965517241377 | 해당 좌표의 기준 가스 발전 비중 0.31818965517241377을 현재 기준값으로 사용했습니다. 기준 가스 비중이 높고 단기 전력수급 변동에 가스발전이 반응할 여지가 있어, 3개월 충격과 50% 흡수 조건을 반영한 +0.0035를 더해 0.32168965517241375로 산정했습니다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.2155 | 해당 좌표의 기준 가스 발전 비중 0.213을 현재 기준값으로 사용했습니다. 수력 약세와 냉방 수요가 겹칠 때 가스발전 보강이 필요할 수 있으나, 영향 기간이 3개월이고 절반은 다른 전원이 흡수한다는 조건을 감안해 +0.0025를 반영한 0.2155를 제안합니다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.293 | 해당 좌표의 기준 가스 발전 비중 0.29를 현재 기준값으로 사용했습니다. 풍황 약세가 전력 부문 가스 수요를 지지할 수 있으나 단기 3개월 영향이며 대체 전원 흡수가 절반 존재하므로, 연간 비중에는 보수적인 +0.003을 반영해 0.293으로 제안합니다. |

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
  "model_param_proposal_id": 73,
  "proposal_completed_dtm": "2026-07-07 21:15:24.293542",
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
      "rationale": "재생 출력 약세에 따른 Capacity 변화 규모는 재생 전용 입력이 아닌 발전원별 비중 조정으로 반영되므로 가스 발전 비중 상향이 직접 연결됩니다. 타 에너지원 흡수 가능성 50%는 석탄·원전 등 다른 전원이 절반을 흡수하고 남은 공백만 가스가 담당한다는 완화 조건으로 적용했습니다. 영향 기간은 3개월로 제한되므로 연간 PowerMix 입력에는 단기 충격을 연율화해 보수적인 소폭 상향으로 반영합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.192,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.19를 현재 기준값으로 사용했습니다. 3개월 지속 충격을 연간 비중에 반영하고, 대체 전원이 절반을 흡수한다는 조건을 감안해 상대적으로 작은 +0.002를 더한 0.192를 최종 입력값으로 제안합니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.043,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.042를 현재 기준값으로 사용했습니다. 프랑스는 기준 가스 비중이 낮고 타 전원의 흡수 여지가 큰 편이므로, 3개월 영향과 50% 흡수 조건을 반영해 보수적으로 +0.001만 상향한 0.043을 제안합니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.138,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.135를 현재 기준값으로 사용했습니다. 풍력 약세가 가스발전 호출로 이어질 수 있는 직접성이 높지만 영향 기간이 3개월이고 절반은 타 전원이 흡수하므로, 연간 입력에는 +0.003을 반영해 0.138로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.438,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.434를 현재 기준값으로 사용했습니다. 기준 가스 의존도가 높아 재생·수력 약세 시 가스발전 대체가 비교적 크게 나타날 수 있으므로, 3개월 연율화와 50% 흡수 조건을 적용하되 선택 국가 중 큰 폭인 +0.004를 반영해 0.438을 제안합니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.32168965517241377,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.31818965517241377을 현재 기준값으로 사용했습니다. 기준 가스 비중이 높고 단기 전력수급 변동에 가스발전이 반응할 여지가 있어, 3개월 충격과 50% 흡수 조건을 반영한 +0.0035를 더해 0.32168965517241375로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.2155,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.213을 현재 기준값으로 사용했습니다. 수력 약세와 냉방 수요가 겹칠 때 가스발전 보강이 필요할 수 있으나, 영향 기간이 3개월이고 절반은 다른 전원이 흡수한다는 조건을 감안해 +0.0025를 반영한 0.2155를 제안합니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.293,
          "rationale": "해당 좌표의 기준 가스 발전 비중 0.29를 현재 기준값으로 사용했습니다. 풍황 약세가 전력 부문 가스 수요를 지지할 수 있으나 단기 3개월 영향이며 대체 전원 흡수가 절반 존재하므로, 연간 비중에는 보수적인 +0.003을 반영해 0.293으로 제안합니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 44,
  "scenario_id": 262,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:09.753 | 9.753 | 2587 | 121 | 2708 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:10.509 | 10.509 | 5478 | 842 | 6320 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:31.605 | 31.605 | 7464 | 2160 | 9624 |

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

- 소요시간: 01:01.267 (61.267s)
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
| Step2 selected slot | 1 | PASS |
| Step3 basecase 샘플 | prompt_records=57, limit=100 | PASS |
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"10|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 100%는 Haramachi 차질로 생길 수 있는 발전 부족분이 LNG 발전이 아니라 기존 석탄 운용 및 다른 전원으로 흡수되는 경우를 의미하므로, 일본 Gas 발전 비중을 조정 대상으로 확인한다. 영향 기간이 1개월 이하이고 구조적 변동도 단발적이어서 연간 전원 믹스의 구조적 상향 조정 근거는 약하므로, 2026년 일본 Gas 비중은 기준 전원 믹스를 유지하는 방식으로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.323 | 해당 좌표는 선택된 일본 2026년 Gas 전원 비중이며, 기준값 0.323이 존재한다. 차질 기간이 짧고 대체 흡수율이 100%로 제시되어 LNG 발전 비중을 추가로 높일 필요가 없으므로 기준값과 동일한 0.323을 최종 입력값으로 유지한다. |

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
  "model_param_proposal_id": 74,
  "proposal_completed_dtm": "2026-07-07 21:15:33.891432",
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
      "rationale": "타 에너지원 흡수 가능성 100%는 Haramachi 차질로 생길 수 있는 발전 부족분이 LNG 발전이 아니라 기존 석탄 운용 및 다른 전원으로 흡수되는 경우를 의미하므로, 일본 Gas 발전 비중을 조정 대상으로 확인한다. 영향 기간이 1개월 이하이고 구조적 변동도 단발적이어서 연간 전원 믹스의 구조적 상향 조정 근거는 약하므로, 2026년 일본 Gas 비중은 기준 전원 믹스를 유지하는 방식으로 제안한다.",
      "values": [
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.323,
          "rationale": "해당 좌표는 선택된 일본 2026년 Gas 전원 비중이며, 기준값 0.323이 존재한다. 차질 기간이 짧고 대체 흡수율이 100%로 제시되어 LNG 발전 비중을 추가로 높일 필요가 없으므로 기준값과 동일한 0.323을 최종 입력값으로 유지한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 45,
  "scenario_id": 267,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:02.751 | 2.751 | 2308 | 83 | 2391 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:13.494 | 13.494 | 5365 | 599 | 5964 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:28.438 | 28.438 | 7120 | 633 | 7753 |

#### scenario_id=268 6개월 공백에 고가 석유 대체 한계, LNG 보강 매수 부상

- 소요시간: 01:00.274 (60.274s)
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
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 50%는 원전·재생에너지 등 비가스 전원이 전력 공백의 일부만 흡수하고 잔여분은 가스발전 비중 상승으로 이어질 수 있음을 의미하므로 PowerMix의 Gas 비중 조정과 직접 연결된다. 구조적 변동이라는 보조 조건은 단순 단기 가격 반응보다 연간 발전 믹스에 반영될 수 있는 설정을 지지하며, 6개월 영향 기간을 고려해 2026년 일본 Gas 비중을 제한적으로 상향한다. |

##### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.327 | 해당 좌표는 선택된 일본 2026년 Gas 발전 믹스이며, 기준값 0.323을 현재 연간 가스 발전 비중으로 사용했다. Haramachi 석탄발전 차질이 6개월 지속되고 타 전원이 50%를 흡수하는 설정이므로, 잔여 전력 공백의 일부가 가스화력 이용률 상승으로 전환된다고 보아 연간 비중을 보수적으로 약 0.4%p 높인 0.327로 산정했다. |

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
  "model_param_proposal_id": 75,
  "proposal_completed_dtm": "2026-07-07 21:15:57.423631",
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
      "rationale": "타 에너지원 흡수 가능성 50%는 원전·재생에너지 등 비가스 전원이 전력 공백의 일부만 흡수하고 잔여분은 가스발전 비중 상승으로 이어질 수 있음을 의미하므로 PowerMix의 Gas 비중 조정과 직접 연결된다. 구조적 변동이라는 보조 조건은 단순 단기 가격 반응보다 연간 발전 믹스에 반영될 수 있는 설정을 지지하며, 6개월 영향 기간을 고려해 2026년 일본 Gas 비중을 제한적으로 상향한다.",
      "values": [
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.327,
          "rationale": "해당 좌표는 선택된 일본 2026년 Gas 발전 믹스이며, 기준값 0.323을 현재 연간 가스 발전 비중으로 사용했다. Haramachi 석탄발전 차질이 6개월 지속되고 타 전원이 50%를 흡수하는 설정이므로, 잔여 전력 공백의 일부가 가스화력 이용률 상승으로 전환된다고 보아 연간 비중을 보수적으로 약 0.4%p 높인 0.327로 산정했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 45,
  "scenario_id": 268,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.348 | 3.348 | 2364 | 84 | 2448 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:09.766 | 9.766 | 5418 | 255 | 5673 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:10.706 | 10.706 | 7173 | 659 | 7832 |

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

- 소요시간: 03:10.669 (190.669s)
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
| Step2 selected slot | 9 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=9, basecaseValue_present=3 | PASS |
| Step2 slot axis value 수 | `{"11|altlngsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 3 | 영향 시설 유형이 생산 시설로 선택되어 해당 국가의 공급 차질 물량을 직접 반영하는 SupplyDisruption이 선택된다. 기간 3개월과 급손상-단기수리 패턴을 시간 범위와 회복 형태로 반영해, 호주 공급 차질을 초기 크게 반영한 뒤 월별로 점진 완화하는 절대 물량 입력값으로 제안한다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 3 | 영향 시설 유형이 생산 시설이고 시나리오 서술에서 액화 생산 차질이 명시되어, Wheatstone의 월별 LNG 생산 가능량 자체를 조정하는 LiqProdAdjustment가 연결된다. 3개월 단기수리형 손상이므로 생산량은 첫 달에 가장 낮고 이후 단계적으로 회복되는 절대 생산량 경로로 제안한다. |
| 3 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 3 | 대체 LNG 공급 가능성이 50%로 선택되어 피해로 감소한 공급 중 일부를 다른 공급국의 가용 액화설비 가동률 상향으로 보완하는 LiqUtilAdjustment가 직접 연결된다. 선택된 QatarGas LNG Train의 3개월 구간에 대해 대체 공급 여력을 반영해 기준 가동률보다 소폭 상향하되, 단기수리 진행에 따라 마지막 달의 상향 폭은 축소한다. |

##### Proposed Parameter Values

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "Month": 7, "Year": 2026}` | null | 1.8 | 2026년 7월 호주 생산 시설 피해의 첫 달로, 기준값 record가 없어 현재 기준을 0으로 간주하지 않고 이벤트의 호주 서부 LNG 설비 차질 및 높은 차질 강도를 반영해 보수적인 월간 절대 공급 차질 물량을 1.8 Bcm로 설정했다. |
| 2 | `{"Country": "Australia", "Month": 8, "Year": 2026}` | null | 1.2 | 2026년 8월은 3개월 차질의 두 번째 달로, 단기수리 패턴에 따라 첫 달보다 차질이 일부 완화되는 것으로 보아 월간 절대 공급 차질 물량을 1.2 Bcm로 낮춰 설정했다. |
| 3 | `{"Country": "Australia", "Month": 9, "Year": 2026}` | null | 0.6 | 2026년 9월은 3개월 차질의 마지막 달로, 급손상 이후 단기수리 진행에 따른 회복을 반영해 잔여 차질만 남는 보수적 수준인 0.6 Bcm를 적용했다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "LNG Plant": "Wheatstone", "Month": 7, "Period": 112, "Year": 2026}` | null | 0.2 | Wheatstone이 명시적으로 차질 대상에 포함된 첫 달이며 기준 생산량 record가 없어, 높은 피해 강도를 반영하되 완전 영구손실은 아닌 단기수리 조건을 고려해 월간 LNG 생산량을 0.2 Mt LNG/month로 설정했다. |
| 2 | `{"Country": "Australia", "LNG Plant": "Wheatstone", "Month": 8, "Period": 113, "Year": 2026}` | null | 0.35 | 차질 두 번째 달은 수리 진행으로 첫 달보다 일부 생산 회복이 가능한 구간으로 보아, 기준값 부재하에서 보수적인 부분 회복 수준인 0.35 Mt LNG/month를 적용했다. |
| 3 | `{"Country": "Australia", "LNG Plant": "Wheatstone", "Month": 9, "Period": 114, "Year": 2026}` | null | 0.55 | 3개월 단기수리 기간의 마지막 달로, 설비 복구가 진전되지만 완전 정상화 전이라는 전제를 반영해 월간 LNG 생산량을 0.55 Mt LNG/month로 제안했다. |

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0977010309278352 | 선택된 QatarGas LNG T1의 2026년 7월 대체 공급 슬롯으로, 같은 연월 기준 가동률 1.0477010309278352에 대체 LNG 공급 가능성 50%를 반영한 보수적 상향분 0.05를 더해 최종 가동률을 1.0977010309278352로 설정했다. |
| 2 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 113, "Year": 2026}` | 1.002484536082474 | 1.0524845360824742 | 2026년 8월은 호주 차질이 지속되는 두 번째 달이므로 같은 연월 기준 가동률 1.0024845360824741에 0.05의 대체 공급용 가동률 상향을 적용해 1.0524845360824742로 제안했다. |
| 3 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 114, "Year": 2026}` | 1.0294432989690725 | 1.0594432989690723 | 2026년 9월은 단기수리 패턴상 호주 공급 차질이 완화되는 마지막 달로, 같은 연월 기준 가동률 1.0294432989690723에 축소된 대체 공급 상향분 0.03을 더해 최종 가동률을 1.0594432989690723으로 산정했다. |

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
  "model_param_proposal_id": 76,
  "proposal_completed_dtm": "2026-07-07 21:18:16.108016",
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
      "rationale": "영향 시설 유형이 생산 시설로 선택되어 해당 국가의 공급 차질 물량을 직접 반영하는 SupplyDisruption이 선택된다. 기간 3개월과 급손상-단기수리 패턴을 시간 범위와 회복 형태로 반영해, 호주 공급 차질을 초기 크게 반영한 뒤 월별로 점진 완화하는 절대 물량 입력값으로 제안한다.",
      "values": [
        {
          "Country": "Australia",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.8,
          "rationale": "2026년 7월 호주 생산 시설 피해의 첫 달로, 기준값 record가 없어 현재 기준을 0으로 간주하지 않고 이벤트의 호주 서부 LNG 설비 차질 및 높은 차질 강도를 반영해 보수적인 월간 절대 공급 차질 물량을 1.8 Bcm로 설정했다."
        },
        {
          "Country": "Australia",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 1.2,
          "rationale": "2026년 8월은 3개월 차질의 두 번째 달로, 단기수리 패턴에 따라 첫 달보다 차질이 일부 완화되는 것으로 보아 월간 절대 공급 차질 물량을 1.2 Bcm로 낮춰 설정했다."
        },
        {
          "Country": "Australia",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.6,
          "rationale": "2026년 9월은 3개월 차질의 마지막 달로, 급손상 이후 단기수리 진행에 따른 회복을 반영해 잔여 차질만 남는 보수적 수준인 0.6 Bcm를 적용했다."
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
      "rationale": "영향 시설 유형이 생산 시설이고 시나리오 서술에서 액화 생산 차질이 명시되어, Wheatstone의 월별 LNG 생산 가능량 자체를 조정하는 LiqProdAdjustment가 연결된다. 3개월 단기수리형 손상이므로 생산량은 첫 달에 가장 낮고 이후 단계적으로 회복되는 절대 생산량 경로로 제안한다.",
      "values": [
        {
          "Country": "Australia",
          "LNG Plant": "Wheatstone",
          "Month": 7,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.2,
          "rationale": "Wheatstone이 명시적으로 차질 대상에 포함된 첫 달이며 기준 생산량 record가 없어, 높은 피해 강도를 반영하되 완전 영구손실은 아닌 단기수리 조건을 고려해 월간 LNG 생산량을 0.2 Mt LNG/month로 설정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Wheatstone",
          "Month": 8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.35,
          "rationale": "차질 두 번째 달은 수리 진행으로 첫 달보다 일부 생산 회복이 가능한 구간으로 보아, 기준값 부재하에서 보수적인 부분 회복 수준인 0.35 Mt LNG/month를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Wheatstone",
          "Month": 9,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.55,
          "rationale": "3개월 단기수리 기간의 마지막 달로, 설비 복구가 진전되지만 완전 정상화 전이라는 전제를 반영해 월간 LNG 생산량을 0.55 Mt LNG/month로 제안했다."
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
      "rationale": "대체 LNG 공급 가능성이 50%로 선택되어 피해로 감소한 공급 중 일부를 다른 공급국의 가용 액화설비 가동률 상향으로 보완하는 LiqUtilAdjustment가 직접 연결된다. 선택된 QatarGas LNG Train의 3개월 구간에 대해 대체 공급 여력을 반영해 기준 가동률보다 소폭 상향하되, 단기수리 진행에 따라 마지막 달의 상향 폭은 축소한다.",
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
          "proposedValue": 1.0977010309278352,
          "rationale": "선택된 QatarGas LNG T1의 2026년 7월 대체 공급 슬롯으로, 같은 연월 기준 가동률 1.0477010309278352에 대체 LNG 공급 가능성 50%를 반영한 보수적 상향분 0.05를 더해 최종 가동률을 1.0977010309278352로 설정했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.002484536082474,
          "proposedValue": 1.0524845360824742,
          "rationale": "2026년 8월은 호주 차질이 지속되는 두 번째 달이므로 같은 연월 기준 가동률 1.0024845360824741에 0.05의 대체 공급용 가동률 상향을 적용해 1.0524845360824742로 제안했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294432989690725,
          "proposedValue": 1.0594432989690723,
          "rationale": "2026년 9월은 단기수리 패턴상 호주 공급 차질이 완화되는 마지막 달로, 같은 연월 기준 가동률 1.0294432989690723에 축소된 대체 공급 상향분 0.03을 더해 최종 가동률을 1.0594432989690723으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:20.628 | 20.628 | 3054 | 1180 | 4234 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:57.805 | 57.805 | 12631 | 3853 | 16484 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:07.105 | 67.105 | 11197 | 4571 | 15768 |

#### scenario_id=280 [model_parameter_agent_test] 수입 시설 피해

- 소요시간: 03:39.030 (219.030s)
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
| Step3 value 결과 | value_cells=54, basecaseValue_present=54 | PASS |
| Step2 slot axis value 수 | `{"parameter|11|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 54 | 영향 시설 유형은 LNG 처리 인프라의 물리적 처리 여력 저하를 가리키며, 제공된 작업은 호주 LNG train별 월별 이용률을 조정하는 LiqUtilAdjustment로 확정되어 있다. 대체 LNG 공급 가능성이 25%로 제한되어 차질 완충이 충분하지 않으므로 6개월 영향 구간에 하향 조정을 적용하되, 급손상 이후 장기 재건 패턴을 반영해 초기 하향폭을 크게 두고 후반으로 갈수록 단계적으로 회복시키는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 112, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 해당 train의 2026년 7월 기준값 1.0384615384615388에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 2 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 113, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 해당 train의 2026년 8월 기준값 1.0384615384615388에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 3 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 114, "Year": 2026}` | 1.0384615384615388 | 0.8307692307692311 | 해당 train의 2026년 9월 기준값 1.0384615384615388에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 4 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 5.2, "Period": 115, "Year": 2026}` | 1.0384615384615388 | 0.8307692307692311 | 해당 train의 2026년 10월 기준값 1.0384615384615388에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 5 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 5.2, "Period": 116, "Year": 2026}` | 1.0384615384615388 | 0.8826923076923079 | 해당 train의 2026년 11월 기준값 1.0384615384615388에 후반부 복구 진전 배율 0.85를 적용했다. |
| 6 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 5.2, "Period": 117, "Year": 2026}` | 1.0384615384615388 | 0.934615384615385 | 해당 train의 2026년 12월 기준값 1.0384615384615388에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 7 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 112, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 해당 train의 2026년 7월 기준값 1.0384615384615388에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 8 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 113, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 해당 train의 2026년 8월 기준값 1.0384615384615388에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 9 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 114, "Year": 2026}` | 1.0384615384615388 | 0.8307692307692311 | 해당 train의 2026년 9월 기준값 1.0384615384615388에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 10 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 5.2, "Period": 115, "Year": 2026}` | 1.0384615384615388 | 0.8307692307692311 | 해당 train의 2026년 10월 기준값 1.0384615384615388에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 11 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 5.2, "Period": 116, "Year": 2026}` | 1.0384615384615388 | 0.8826923076923079 | 해당 train의 2026년 11월 기준값 1.0384615384615388에 후반부 복구 진전 배율 0.85를 적용했다. |
| 12 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 5.2, "Period": 117, "Year": 2026}` | 1.0384615384615388 | 0.934615384615385 | 해당 train의 2026년 12월 기준값 1.0384615384615388에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 13 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 112, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 해당 train의 2026년 7월 기준값 1.0384615384615388에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 14 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 113, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 해당 train의 2026년 8월 기준값 1.0384615384615388에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 15 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 114, "Year": 2026}` | 1.0384615384615388 | 0.8307692307692311 | 해당 train의 2026년 9월 기준값 1.0384615384615388에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 16 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 5.2, "Period": 115, "Year": 2026}` | 1.0384615384615388 | 0.8307692307692311 | 해당 train의 2026년 10월 기준값 1.0384615384615388에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 17 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 5.2, "Period": 116, "Year": 2026}` | 1.0384615384615388 | 0.8826923076923079 | 해당 train의 2026년 11월 기준값 1.0384615384615388에 후반부 복구 진전 배율 0.85를 적용했다. |
| 18 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 5.2, "Period": 117, "Year": 2026}` | 1.0384615384615388 | 0.934615384615385 | 해당 train의 2026년 12월 기준값 1.0384615384615388에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 19 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 2.50025, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 20 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 2.50025, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 21 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 2.50025, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 22 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 2.50025, "Period": 115, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 23 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 2.50025, "Period": 116, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474702 | 해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다. |
| 24 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 2.50025, "Period": 117, "Year": 2026}` | 0.6881772329970237 | 0.6193595096973215 | 해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 25 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 2.50025, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 26 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 2.50025, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 27 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 2.50025, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 28 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 2.50025, "Period": 115, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 29 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 2.50025, "Period": 116, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474702 | 해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다. |
| 30 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 2.50025, "Period": 117, "Year": 2026}` | 0.6881772329970237 | 0.6193595096973215 | 해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 31 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 2.50025, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 32 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 2.50025, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 33 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 2.50025, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 34 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 2.50025, "Period": 115, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 35 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 2.50025, "Period": 116, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474702 | 해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다. |
| 36 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 2.50025, "Period": 117, "Year": 2026}` | 0.6881772329970237 | 0.6193595096973215 | 해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 37 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.60046, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 38 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.60046, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 39 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.60046, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 40 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.60046, "Period": 115, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 41 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.60046, "Period": 116, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474702 | 해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다. |
| 42 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.60046, "Period": 117, "Year": 2026}` | 0.6881772329970237 | 0.6193595096973215 | 해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 43 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.60046, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 44 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.60046, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 45 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.60046, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 46 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.60046, "Period": 115, "Year": 2026}` | 0.6881772329970237 | 0.550541786397619 | 해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 47 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.60046, "Period": 116, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474702 | 해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다. |
| 48 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.60046, "Period": 117, "Year": 2026}` | 0.6881772329970237 | 0.6193595096973215 | 해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |
| 49 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.9, "Period": 112, "Year": 2026}` | 1.0329681103448276 | 0.7747260827586206 | 해당 train의 2026년 7월 기준값 1.0329681103448276에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다. |
| 50 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.9, "Period": 113, "Year": 2026}` | 1.0329681103448276 | 0.7747260827586206 | 해당 train의 2026년 8월 기준값 1.0329681103448276에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다. |
| 51 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.9, "Period": 114, "Year": 2026}` | 1.0329681103448276 | 0.8263744882758621 | 해당 train의 2026년 9월 기준값 1.0329681103448276에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다. |
| 52 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.9, "Period": 115, "Year": 2026}` | 1.0329681103448276 | 0.8263744882758621 | 해당 train의 2026년 10월 기준값 1.0329681103448276에 장기 재건 중간 구간의 배율 0.80을 적용했다. |
| 53 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.9, "Period": 116, "Year": 2026}` | 1.0329681103448276 | 0.8780228937931035 | 해당 train의 2026년 11월 기준값 1.0329681103448276에 후반부 복구 진전 배율 0.85를 적용했다. |
| 54 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.9, "Period": 117, "Year": 2026}` | 1.0329681103448276 | 0.9296712993103448 | 해당 train의 2026년 12월 기준값 1.0329681103448276에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다. |

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
  "model_param_proposal_id": 78,
  "proposal_completed_dtm": "2026-07-07 21:19:03.341992",
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
      "rationale": "영향 시설 유형은 LNG 처리 인프라의 물리적 처리 여력 저하를 가리키며, 제공된 작업은 호주 LNG train별 월별 이용률을 조정하는 LiqUtilAdjustment로 확정되어 있다. 대체 LNG 공급 가능성이 25%로 제한되어 차질 완충이 충분하지 않으므로 6개월 영향 구간에 하향 조정을 적용하되, 급손상 이후 장기 재건 패턴을 반영해 초기 하향폭을 크게 두고 후반으로 갈수록 단계적으로 회복시키는 구조로 제안한다.",
      "values": [
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.7788461538461541,
          "rationale": "해당 train의 2026년 7월 기준값 1.0384615384615388에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.7788461538461541,
          "rationale": "해당 train의 2026년 8월 기준값 1.0384615384615388에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8307692307692311,
          "rationale": "해당 train의 2026년 9월 기준값 1.0384615384615388에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8307692307692311,
          "rationale": "해당 train의 2026년 10월 기준값 1.0384615384615388에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8826923076923079,
          "rationale": "해당 train의 2026년 11월 기준값 1.0384615384615388에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.934615384615385,
          "rationale": "해당 train의 2026년 12월 기준값 1.0384615384615388에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.7788461538461541,
          "rationale": "해당 train의 2026년 7월 기준값 1.0384615384615388에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.7788461538461541,
          "rationale": "해당 train의 2026년 8월 기준값 1.0384615384615388에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8307692307692311,
          "rationale": "해당 train의 2026년 9월 기준값 1.0384615384615388에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8307692307692311,
          "rationale": "해당 train의 2026년 10월 기준값 1.0384615384615388에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8826923076923079,
          "rationale": "해당 train의 2026년 11월 기준값 1.0384615384615388에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.934615384615385,
          "rationale": "해당 train의 2026년 12월 기준값 1.0384615384615388에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.7788461538461541,
          "rationale": "해당 train의 2026년 7월 기준값 1.0384615384615388에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.7788461538461541,
          "rationale": "해당 train의 2026년 8월 기준값 1.0384615384615388에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8307692307692311,
          "rationale": "해당 train의 2026년 9월 기준값 1.0384615384615388에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8307692307692311,
          "rationale": "해당 train의 2026년 10월 기준값 1.0384615384615388에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.8826923076923079,
          "rationale": "해당 train의 2026년 11월 기준값 1.0384615384615388에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Gorgon LNG",
          "LNG Plant Train": "Gorgon LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 1.0384615384615388,
          "proposedValue": 0.934615384615385,
          "rationale": "해당 train의 2026년 12월 기준값 1.0384615384615388에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5849506480474702,
          "rationale": "해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.6193595096973215,
          "rationale": "해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5849506480474702,
          "rationale": "해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.6193595096973215,
          "rationale": "해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5849506480474702,
          "rationale": "해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 2.50025,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.6193595096973215,
          "rationale": "해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T4",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T4",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5849506480474702,
          "rationale": "해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T4",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.6193595096973215,
          "rationale": "해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 7월 기준값 0.6881772329970237에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5161329247477678,
          "rationale": "해당 train의 2026년 8월 기준값 0.6881772329970237에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 9월 기준값 0.6881772329970237에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T5",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.550541786397619,
          "rationale": "해당 train의 2026년 10월 기준값 0.6881772329970237에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T5",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.5849506480474702,
          "rationale": "해당 train의 2026년 11월 기준값 0.6881772329970237에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "North West Shelf LNG",
          "LNG Plant Train": "North West Shelf LNG T5",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.60046,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.6881772329970237,
          "proposedValue": 0.6193595096973215,
          "rationale": "해당 train의 2026년 12월 기준값 0.6881772329970237에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Pluto LNG",
          "LNG Plant Train": "Pluto LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.9,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0329681103448276,
          "proposedValue": 0.7747260827586206,
          "rationale": "해당 train의 2026년 7월 기준값 1.0329681103448276에 급손상 초기 구간의 보수적 하향 배율 0.75를 적용해 최종 이용률을 산정했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Pluto LNG",
          "LNG Plant Train": "Pluto LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.9,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0329681103448276,
          "proposedValue": 0.7747260827586206,
          "rationale": "해당 train의 2026년 8월 기준값 1.0329681103448276에 초기 피해 지속 구간의 하향 배율 0.75를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Pluto LNG",
          "LNG Plant Train": "Pluto LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.9,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0329681103448276,
          "proposedValue": 0.8263744882758621,
          "rationale": "해당 train의 2026년 9월 기준값 1.0329681103448276에 부분 복구가 시작되는 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Pluto LNG",
          "LNG Plant Train": "Pluto LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.9,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 1.0329681103448276,
          "proposedValue": 0.8263744882758621,
          "rationale": "해당 train의 2026년 10월 기준값 1.0329681103448276에 장기 재건 중간 구간의 배율 0.80을 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Pluto LNG",
          "LNG Plant Train": "Pluto LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.9,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 1.0329681103448276,
          "proposedValue": 0.8780228937931035,
          "rationale": "해당 train의 2026년 11월 기준값 1.0329681103448276에 후반부 복구 진전 배율 0.85를 적용했다."
        },
        {
          "Country": "Australia",
          "LNG Plant": "Pluto LNG",
          "LNG Plant Train": "Pluto LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.9,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 1.0329681103448276,
          "proposedValue": 0.9296712993103448,
          "rationale": "해당 train의 2026년 12월 기준값 1.0329681103448276에 6개월 영향 구간 말기의 부분 정상화 배율 0.90을 적용했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:19.696 | 19.696 | 3057 | 1180 | 4237 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:19.341 | 79.341 | 11970 | 9233 | 21203 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:32.091 | 92.091 | 16281 | 9933 | 26214 |

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

- 소요시간: 03:07.702 (187.702s)
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
| Step2 selected slot | 54 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=17, basecaseValue_present=17 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 17 | 공급 차질 강도가 낮다는 차원은 영향권 액화시설의 단기 이용률 조정 필요성과 연결되며, 타 공급원 경유 LNG 확보량 100%는 부족분이 수요 측에서 사실상 흡수되어 액화시설 이용률 하향 압력이 제한됨을 의미합니다. 기간도 1개월 이하로 짧고 호르무즈 통항 재개로 물리적 LNG 생산 차질이 확인되지 않아, 중동 영향권 설비는 기준 이용률을 유지하는 보수적 구조로 제안합니다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 해당 좌표는 호르무즈 항로 리스크의 직접 영향권인 카타르 2026년 7월 운전 설비입니다. 최신 사건에서 통항 재개와 물리적 액화설비 차질 부재가 확인되고, 시나리오상 낮은 차질 및 100% 대체 확보가 반영되므로 동일 설비의 7월 기준 입력값을 유지했습니다. |
| 2 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 해당 좌표는 호르무즈 항로 리스크의 직접 영향권인 카타르 2026년 7월 운전 설비입니다. 물류 프리미엄은 단기적으로 흡수되고 생산 차질은 낮게 설정되어 있어 동일 설비의 7월 기준 입력값을 유지했습니다. |
| 3 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 해당 좌표는 호르무즈 항로 리스크의 직접 영향권인 카타르 2026년 7월 운전 설비입니다. 선적·통항 지연이 제한적이고 대체 LNG 확보가 100%로 제시되어 기준 이용률에서 추가 하향 조정하지 않았습니다. |
| 4 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 호르무즈 재개방으로 운송 리스크가 완화되었고 설비 중단 근거가 없어 동일 설비의 7월 기준 입력값을 유지했습니다. |
| 5 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 시나리오의 차질 강도가 낮고 기간이 1개월 이하이므로 생산 이용률을 기준값 수준으로 유지했습니다. |
| 6 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 최신 사건상 LNG 터미널 가동 중단이나 화물 취소가 확인되지 않아 동일 설비의 7월 기준 입력값을 적용했습니다. |
| 7 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 항로 리스크는 잔존하나 물리적 공급 제약이 확인되지 않았으므로 7월 기준 이용률을 그대로 유지했습니다. |
| 8 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 1.0476969696969696 | 해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 호르무즈 통항 재개와 낮은 차질 강도를 반영해 기준 이용률에서 하향 조정하지 않았습니다. |
| 9 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 1.0476969696969696 | 해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 단기 물류 프리미엄은 흡수되는 시나리오이므로 동일 설비의 7월 기준 입력값을 유지했습니다. |
| 10 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 공급 차질이 낮고 대체 확보가 충분해 실제 생산 이용률 하락을 반영하지 않고 기준값을 유지했습니다. |
| 11 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. LNG 선적·통항 지연이 제한적이라는 시나리오를 반영해 동일 설비 기준값을 유지했습니다. |
| 12 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 최신 사건에서 물동량 정상화 신호가 확인되어 7월 기준 이용률을 보수적으로 유지했습니다. |
| 13 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 항로 리스크는 완전히 소멸하지 않았지만 생산 차질 확정 근거가 없어 동일 설비의 기준 입력값을 적용했습니다. |
| 14 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 1개월 이하의 낮은 차질 시나리오와 100% 대체 확보 조건을 반영해 기준 이용률을 유지했습니다. |
| 15 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0956424079065634 | 해당 좌표는 걸프 항로 리스크 영향권인 UAE 2026년 7월 운전 설비입니다. 호르무즈 통항 재개와 물리적 LNG 설비 차질 부재를 반영하여 동일 설비의 7월 기준 입력값을 유지했습니다. |
| 16 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0956424079065634 | 해당 좌표는 걸프 항로 리스크 영향권인 UAE 2026년 7월 운전 설비입니다. 시나리오상 운송 차질 강도가 낮고 기간도 짧아 액화 이용률을 기준값에서 조정하지 않았습니다. |
| 17 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0956424079065634 | 해당 좌표는 걸프 항로 리스크 영향권인 UAE 2026년 7월 운전 설비입니다. 부족분은 타 공급원 경유 LNG로 흡수되는 설정이며 설비 가동 중단 근거가 없어 기준 이용률을 유지했습니다. |

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
  "model_param_proposal_id": 77,
  "proposal_completed_dtm": "2026-07-07 21:18:41.599813",
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
      "rationale": "공급 차질 강도가 낮다는 차원은 영향권 액화시설의 단기 이용률 조정 필요성과 연결되며, 타 공급원 경유 LNG 확보량 100%는 부족분이 수요 측에서 사실상 흡수되어 액화시설 이용률 하향 압력이 제한됨을 의미합니다. 기간도 1개월 이하로 짧고 호르무즈 통항 재개로 물리적 LNG 생산 차질이 확인되지 않아, 중동 영향권 설비는 기준 이용률을 유지하는 보수적 구조로 제안합니다.",
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
          "rationale": "해당 좌표는 호르무즈 항로 리스크의 직접 영향권인 카타르 2026년 7월 운전 설비입니다. 최신 사건에서 통항 재개와 물리적 액화설비 차질 부재가 확인되고, 시나리오상 낮은 차질 및 100% 대체 확보가 반영되므로 동일 설비의 7월 기준 입력값을 유지했습니다."
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
          "rationale": "해당 좌표는 호르무즈 항로 리스크의 직접 영향권인 카타르 2026년 7월 운전 설비입니다. 물류 프리미엄은 단기적으로 흡수되고 생산 차질은 낮게 설정되어 있어 동일 설비의 7월 기준 입력값을 유지했습니다."
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
          "rationale": "해당 좌표는 호르무즈 항로 리스크의 직접 영향권인 카타르 2026년 7월 운전 설비입니다. 선적·통항 지연이 제한적이고 대체 LNG 확보가 100%로 제시되어 기준 이용률에서 추가 하향 조정하지 않았습니다."
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
          "rationale": "해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 호르무즈 재개방으로 운송 리스크가 완화되었고 설비 중단 근거가 없어 동일 설비의 7월 기준 입력값을 유지했습니다."
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
          "rationale": "해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 시나리오의 차질 강도가 낮고 기간이 1개월 이하이므로 생산 이용률을 기준값 수준으로 유지했습니다."
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
          "rationale": "해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 최신 사건상 LNG 터미널 가동 중단이나 화물 취소가 확인되지 않아 동일 설비의 7월 기준 입력값을 적용했습니다."
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
          "rationale": "해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 항로 리스크는 잔존하나 물리적 공급 제약이 확인되지 않았으므로 7월 기준 이용률을 그대로 유지했습니다."
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
          "rationale": "해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 호르무즈 통항 재개와 낮은 차질 강도를 반영해 기준 이용률에서 하향 조정하지 않았습니다."
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
          "rationale": "해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 단기 물류 프리미엄은 흡수되는 시나리오이므로 동일 설비의 7월 기준 입력값을 유지했습니다."
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
          "rationale": "해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 공급 차질이 낮고 대체 확보가 충분해 실제 생산 이용률 하락을 반영하지 않고 기준값을 유지했습니다."
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
          "rationale": "해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. LNG 선적·통항 지연이 제한적이라는 시나리오를 반영해 동일 설비 기준값을 유지했습니다."
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
          "rationale": "해당 좌표는 카타르 Rasgas 계열 2026년 7월 운전 설비입니다. 최신 사건에서 물동량 정상화 신호가 확인되어 7월 기준 이용률을 보수적으로 유지했습니다."
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
          "rationale": "해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 항로 리스크는 완전히 소멸하지 않았지만 생산 차질 확정 근거가 없어 동일 설비의 기준 입력값을 적용했습니다."
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
          "rationale": "해당 좌표는 카타르 대형 액화 트레인의 2026년 7월 입력 슬롯입니다. 1개월 이하의 낮은 차질 시나리오와 100% 대체 확보 조건을 반영해 기준 이용률을 유지했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0956424079065634,
          "rationale": "해당 좌표는 걸프 항로 리스크 영향권인 UAE 2026년 7월 운전 설비입니다. 호르무즈 통항 재개와 물리적 LNG 설비 차질 부재를 반영하여 동일 설비의 7월 기준 입력값을 유지했습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0956424079065634,
          "rationale": "해당 좌표는 걸프 항로 리스크 영향권인 UAE 2026년 7월 운전 설비입니다. 시나리오상 운송 차질 강도가 낮고 기간도 짧아 액화 이용률을 기준값에서 조정하지 않았습니다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0956424079065634,
          "rationale": "해당 좌표는 걸프 항로 리스크 영향권인 UAE 2026년 7월 운전 설비입니다. 부족분은 타 공급원 경유 LNG로 흡수되는 설정이며 설비 가동 중단 근거가 없어 기준 이용률을 유지했습니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 16,
  "scenario_id": 92,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:11.720 | 11.720 | 3670 | 200 | 3870 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:33.566 | 93.566 | 12800 | 10113 | 22913 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:53.142 | 53.142 | 19898 | 4577 | 24475 |

#### scenario_id=93 3개월 부분 차질과 절반 대체 조달

- 소요시간: 03:54.417 (234.417s)
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
| Step2 selected slot | 60 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=60, basecaseValue_present=60 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 60 | 공급 차질 강도 ‘중간’은 영향권 액화시설의 단기 이용률을 낮추는 LiqUtilAdjustment와 직접 연결되며, 타 공급원 경유 LNG 확보량 50%는 차질의 절반을 상쇄하는 완화 요인으로 반영된다. 기간 3개월은 시간 범위만 정하는 공통 맥락으로 사용하여, 중동 항로 리스크가 남아 있는 초기 3개월 동안 전면 중단이 아닌 보수적 순하향 조정을 적용한다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 해당 월의 기준 이용률 1.0477010309278352에 중간 강도 차질을 총 10% 하향 요인으로 보고, 대체 조달 50%를 반영해 순 5%만 하향하여 1.0477010309278352×0.95로 산정했다. |
| 2 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 113, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 3개월 영향 범위의 두 번째 월로 동일한 순 5% 하향률을 적용했으며, 기준 이용률 1.0024845360824741×0.95로 산정했다. |
| 3 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 114, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206187 | 3개월 영향 범위의 마지막 월로 동일한 순 5% 하향률을 적용했으며, 기준 이용률 1.0294432989690723×0.95로 산정했다. |
| 4 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 해당 월의 기준 이용률 1.0477010309278352에 중간 강도 차질과 50% 대체 조달을 함께 반영한 순 5% 하향률을 적용했다. |
| 5 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 113, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 3개월 영향 범위의 두 번째 월로 기준 이용률 1.0024845360824741에 순 5% 하향률을 적용했다. |
| 6 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 114, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206187 | 3개월 영향 범위의 마지막 월로 기준 이용률 1.0294432989690723에 순 5% 하향률을 적용했다. |
| 7 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 해당 월 기준 이용률 1.0477010309278352에 순 5% 하향률을 적용해 부분 운송 차질을 반영했다. |
| 8 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 113, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 해당 월 기준 이용률 1.0024845360824741에 순 5% 하향률을 적용했다. |
| 9 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 114, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206187 | 해당 월 기준 이용률 1.0294432989690723에 순 5% 하향률을 적용했다. |
| 10 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 기준 이용률 1.0476962025316454에 총 차질의 절반을 대체 조달로 상쇄한 순 5% 하향률을 적용했다. |
| 11 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 3개월 영향 범위의 두 번째 월로 기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다. |
| 12 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 3개월 영향 범위의 마지막 월로 기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다. |
| 13 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 기준 이용률 1.0476962025316454에 순 5% 하향률을 적용해 부분 차질을 반영했다. |
| 14 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다. |
| 15 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다. |
| 16 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 기준 이용률 1.0476962025316454에 중간 차질의 순영향 5%를 하향 반영했다. |
| 17 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다. |
| 18 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다. |
| 19 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 기준 이용률 1.0476962025316454에 순 5% 하향률을 적용해 3개월 부분 차질의 첫 월을 반영했다. |
| 20 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다. |
| 21 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다. |
| 22 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 0.9953121212121212 | 기준 이용률 1.0476969696969696에 순 5% 하향률을 적용했다. |
| 23 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 113, "Year": 2026}` | 1.0024848484848483 | 0.952360606060606 | 기준 이용률 1.0024848484848485에 순 5% 하향률을 적용했다. |
| 24 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 114, "Year": 2026}` | 1.0294545454545456 | 0.9779818181818184 | 기준 이용률 1.0294545454545456에 순 5% 하향률을 적용했다. |
| 25 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 0.9953121212121212 | 기준 이용률 1.0476969696969696에 순 5% 하향률을 적용했다. |
| 26 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 113, "Year": 2026}` | 1.0024848484848483 | 0.952360606060606 | 기준 이용률 1.0024848484848485에 순 5% 하향률을 적용했다. |
| 27 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 114, "Year": 2026}` | 1.0294545454545456 | 0.9779818181818184 | 기준 이용률 1.0294545454545456에 순 5% 하향률을 적용했다. |
| 28 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 0.995317021276596 | 기준 이용률 1.0477021276595746에 순 5% 하향률을 적용했다. |
| 29 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 113, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170211 | 기준 이용률 1.0024893617021278에 순 5% 하향률을 적용했다. |
| 30 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 114, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 기준 이용률 1.029446808510638에 순 5% 하향률을 적용했다. |
| 31 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 0.995317021276596 | 기준 이용률 1.0477021276595746에 순 5% 하향률을 적용했다. |
| 32 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 113, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170211 | 기준 이용률 1.0024893617021278에 순 5% 하향률을 적용했다. |
| 33 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 114, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 기준 이용률 1.029446808510638에 순 5% 하향률을 적용했다. |
| 34 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 0.995317021276596 | 기준 이용률 1.0477021276595746에 순 5% 하향률을 적용했다. |
| 35 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 113, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170211 | 기준 이용률 1.0024893617021278에 순 5% 하향률을 적용했다. |
| 36 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 114, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 기준 이용률 1.029446808510638에 순 5% 하향률을 적용했다. |
| 37 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 기준 이용률 1.0476962025316454에 순 5% 하향률을 적용했다. |
| 38 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다. |
| 39 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다. |
| 40 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 기준 이용률 1.0476962025316454에 순 5% 하향률을 적용했다. |
| 41 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다. |
| 42 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.9779708860759492 | 기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다. |
| 43 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 기준 이용률 1.0956424079065634에 중동 항로 부분 차질과 대체 조달 완화 효과를 반영한 순 5% 하향률을 적용했다. |
| 44 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 1.15, "Period": 113, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 3개월 영향 범위의 두 번째 월로 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 45 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 1.15, "Period": 114, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 3개월 영향 범위의 마지막 월로 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 46 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 47 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 1.15, "Period": 113, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 48 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 1.15, "Period": 114, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 49 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 50 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3, "Period": 113, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 51 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3, "Period": 114, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112352 | 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다. |
| 52 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.55, "Period": 112, "Year": 2026}` | 1.1814275778125545 | 1.1223561989219266 | 기준 이용률 1.1814275778125545에 중간 차질과 대체 조달 50%를 함께 반영한 순 5% 하향률을 적용했다. |
| 53 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.55, "Period": 113, "Year": 2026}` | 1.179121891844897 | 1.1201657972526518 | 3개월 영향 범위의 두 번째 월로 기준 이용률 1.1791218918448967에 순 5% 하향률을 적용했다. |
| 54 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.55, "Period": 114, "Year": 2026}` | 0.951361502347418 | 0.9037934272300472 | 3개월 영향 범위의 마지막 월로 기준 이용률 0.951361502347418에 순 5% 하향률을 적용했다. |
| 55 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.55, "Period": 112, "Year": 2026}` | 1.1814275778125545 | 1.1223561989219266 | 기준 이용률 1.1814275778125545에 순 5% 하향률을 적용했다. |
| 56 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.55, "Period": 113, "Year": 2026}` | 1.179121891844897 | 1.1201657972526518 | 기준 이용률 1.1791218918448967에 순 5% 하향률을 적용했다. |
| 57 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.55, "Period": 114, "Year": 2026}` | 0.951361502347418 | 0.9037934272300472 | 기준 이용률 0.951361502347418에 순 5% 하향률을 적용했다. |
| 58 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T3 (Qalhat)", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 0.9179166666666668 | 0.8720208333333332 | 기준 이용률 0.9179166666666667에 순 5% 하향률을 적용해 부분 차질을 반영했다. |
| 59 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T3 (Qalhat)", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 113, "Year": 2026}` | 0.9940277777777776 | 0.9443263888888888 | 기준 이용률 0.9940277777777777에 순 5% 하향률을 적용했다. |
| 60 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T3 (Qalhat)", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 114, "Year": 2026}` | 0.9876111111111112 | 0.9382305555555556 | 기준 이용률 0.9876111111111111에 순 5% 하향률을 적용했다. |

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
  "model_param_proposal_id": 79,
  "proposal_completed_dtm": "2026-07-07 21:19:51.831218",
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
      "rationale": "공급 차질 강도 ‘중간’은 영향권 액화시설의 단기 이용률을 낮추는 LiqUtilAdjustment와 직접 연결되며, 타 공급원 경유 LNG 확보량 50%는 차질의 절반을 상쇄하는 완화 요인으로 반영된다. 기간 3개월은 시간 범위만 정하는 공통 맥락으로 사용하여, 중동 항로 리스크가 남아 있는 초기 3개월 동안 전면 중단이 아닌 보수적 순하향 조정을 적용한다.",
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
          "proposedValue": 0.9953159793814434,
          "rationale": "해당 월의 기준 이용률 1.0477010309278352에 중간 강도 차질을 총 10% 하향 요인으로 보고, 대체 조달 50%를 반영해 순 5%만 하향하여 1.0477010309278352×0.95로 산정했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.002484536082474,
          "proposedValue": 0.9523603092783504,
          "rationale": "3개월 영향 범위의 두 번째 월로 동일한 순 5% 하향률을 적용했으며, 기준 이용률 1.0024845360824741×0.95로 산정했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294432989690725,
          "proposedValue": 0.9779711340206187,
          "rationale": "3개월 영향 범위의 마지막 월로 동일한 순 5% 하향률을 적용했으며, 기준 이용률 1.0294432989690723×0.95로 산정했다."
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
          "proposedValue": 0.9953159793814434,
          "rationale": "해당 월의 기준 이용률 1.0477010309278352에 중간 강도 차질과 50% 대체 조달을 함께 반영한 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.002484536082474,
          "proposedValue": 0.9523603092783504,
          "rationale": "3개월 영향 범위의 두 번째 월로 기준 이용률 1.0024845360824741에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294432989690725,
          "proposedValue": 0.9779711340206187,
          "rationale": "3개월 영향 범위의 마지막 월로 기준 이용률 1.0294432989690723에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953159793814434,
          "rationale": "해당 월 기준 이용률 1.0477010309278352에 순 5% 하향률을 적용해 부분 운송 차질을 반영했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.002484536082474,
          "proposedValue": 0.9523603092783504,
          "rationale": "해당 월 기준 이용률 1.0024845360824741에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 1 T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.2,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294432989690725,
          "proposedValue": 0.9779711340206187,
          "rationale": "해당 월 기준 이용률 1.0294432989690723에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953113924050632,
          "rationale": "기준 이용률 1.0476962025316454에 총 차질의 절반을 대체 조달로 상쇄한 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "3개월 영향 범위의 두 번째 월로 기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "3개월 영향 범위의 마지막 월로 기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953113924050632,
          "rationale": "기준 이용률 1.0476962025316454에 순 5% 하향률을 적용해 부분 차질을 반영했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953113924050632,
          "rationale": "기준 이용률 1.0476962025316454에 중간 차질의 순영향 5%를 하향 반영했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953113924050632,
          "rationale": "기준 이용률 1.0476962025316454에 순 5% 하향률을 적용해 3개월 부분 차질의 첫 월을 반영했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 4 T7",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Qatargas 4 T7",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953121212121212,
          "rationale": "기준 이용률 1.0476969696969696에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024848484848483,
          "proposedValue": 0.952360606060606,
          "rationale": "기준 이용률 1.0024848484848485에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294545454545456,
          "proposedValue": 0.9779818181818184,
          "rationale": "기준 이용률 1.0294545454545456에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953121212121212,
          "rationale": "기준 이용률 1.0476969696969696에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024848484848483,
          "proposedValue": 0.952360606060606,
          "rationale": "기준 이용률 1.0024848484848485에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 1 T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294545454545456,
          "proposedValue": 0.9779818181818184,
          "rationale": "기준 이용률 1.0294545454545456에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.995317021276596,
          "rationale": "기준 이용률 1.0477021276595746에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024893617021278,
          "proposedValue": 0.9523648936170211,
          "rationale": "기준 이용률 1.0024893617021278에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.029446808510638,
          "proposedValue": 0.977974468085106,
          "rationale": "기준 이용률 1.029446808510638에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.995317021276596,
          "rationale": "기준 이용률 1.0477021276595746에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024893617021278,
          "proposedValue": 0.9523648936170211,
          "rationale": "기준 이용률 1.0024893617021278에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.029446808510638,
          "proposedValue": 0.977974468085106,
          "rationale": "기준 이용률 1.029446808510638에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.995317021276596,
          "rationale": "기준 이용률 1.0477021276595746에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024893617021278,
          "proposedValue": 0.9523648936170211,
          "rationale": "기준 이용률 1.0024893617021278에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 2 T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.029446808510638,
          "proposedValue": 0.977974468085106,
          "rationale": "기준 이용률 1.029446808510638에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953113924050632,
          "rationale": "기준 이용률 1.0476962025316454에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다."
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
          "proposedValue": 0.9953113924050632,
          "rationale": "기준 이용률 1.0476962025316454에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T7",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0024810126582275,
          "proposedValue": 0.952356962025316,
          "rationale": "기준 이용률 1.0024810126582275에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Qatar",
          "LNG Plant": "QatarGas LNG",
          "LNG Plant Train": "Rasgas 3 T7",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.8,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0294430379746833,
          "proposedValue": 0.9779708860759492,
          "rationale": "기준 이용률 1.0294430379746833에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "기준 이용률 1.0956424079065634에 중동 항로 부분 차질과 대체 조달 완화 효과를 반영한 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "3개월 영향 범위의 두 번째 월로 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "3개월 영향 범위의 마지막 월로 기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 1.15,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "UAE",
          "LNG Plant": "Adgas LNG",
          "LNG Plant Train": "Adgas LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0956424079065634,
          "proposedValue": 1.0408602875112352,
          "rationale": "기준 이용률 1.0956424079065634에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.55,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.1814275778125545,
          "proposedValue": 1.1223561989219266,
          "rationale": "기준 이용률 1.1814275778125545에 중간 차질과 대체 조달 50%를 함께 반영한 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.55,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.179121891844897,
          "proposedValue": 1.1201657972526518,
          "rationale": "3개월 영향 범위의 두 번째 월로 기준 이용률 1.1791218918448967에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.55,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.951361502347418,
          "proposedValue": 0.9037934272300472,
          "rationale": "3개월 영향 범위의 마지막 월로 기준 이용률 0.951361502347418에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.55,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.1814275778125545,
          "proposedValue": 1.1223561989219266,
          "rationale": "기준 이용률 1.1814275778125545에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.55,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.179121891844897,
          "proposedValue": 1.1201657972526518,
          "rationale": "기준 이용률 1.1791218918448967에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.55,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.951361502347418,
          "proposedValue": 0.9037934272300472,
          "rationale": "기준 이용률 0.951361502347418에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T3 (Qalhat)",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9179166666666668,
          "proposedValue": 0.8720208333333332,
          "rationale": "기준 이용률 0.9179166666666667에 순 5% 하향률을 적용해 부분 차질을 반영했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T3 (Qalhat)",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9940277777777776,
          "proposedValue": 0.9443263888888888,
          "rationale": "기준 이용률 0.9940277777777777에 순 5% 하향률을 적용했다."
        },
        {
          "Country": "Oman",
          "LNG Plant": "Oman LNG",
          "LNG Plant Train": "Oman LNG T3 (Qalhat)",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.9876111111111112,
          "proposedValue": 0.9382305555555556,
          "rationale": "기준 이용률 0.9876111111111111에 순 5% 하향률을 적용했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 16,
  "scenario_id": 93,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.964 | 4.964 | 3667 | 218 | 3885 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:22.739 | 82.739 | 12792 | 10054 | 22846 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 02:01.923 | 121.923 | 18627 | 9589 | 28216 |

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

- 소요시간: 02:46.275 (166.275s)
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
| Step2 selected slot | 10 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=9, basecaseValue_present=4 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 3 | 공급 차질 강도 ‘낮음’은 Arctic LNG 2 T1의 액화 가동률을 제한적으로 낮추는 요인으로 연결된다. 타 공급원 경유 LNG 확보가 100% 가능하다는 점은 실물 부족을 완화하므로 가동률 조정 폭은 작게 두고, 3개월·지연발생-단계적 회복 맥락에 맞춰 초기에는 유지 후 후반으로 갈수록 소폭 하향하는 구조로 제안한다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 3 | 공급 차질 강도 ‘낮음’은 생산량 직접 감소로 연결되지만, 제재 이슈의 성격이 설비 손상보다 거래·선박·구매자 접근 제약에 가깝기 때문에 생산량 감소 폭은 제한적이다. 3개월·지연발생-단계적 회복 패턴을 반영해 Arctic LNG 2 T1의 월별 절대 생산량을 초기 유지, 이후 소폭 하향하는 방식으로 제안한다. |
| 3 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 2 | 공급 차질 강도 ‘낮음’은 러시아 공급 차질 가능성과 연결되지만, 이번 사건은 러시아 전체 upstream 생산 중단보다는 Arctic LNG 2 관련 제재·무역 흐름 제약이 핵심이다. 따라서 국가 단위 공급 차질 값은 넓게 적용하지 않고, 3개월·지연발생 패턴상 후반부에만 LNG 생산 차질의 가스 등가 수준을 보수적으로 반영한다. |
| 4 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | PowerMix 조정을 통한 LNG 수요 감소량이 100% 가능하다는 설정은 가스 발전 비중을 낮춰 부족분을 흡수할 수 있음을 의미한다. 다만 기간이 3개월이고 공급 차질 강도도 낮아 연간 전원 비중에는 매우 제한적인 하향만 반영하며, 중국의 Gas 비중을 소폭 낮추는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.45 | 2026년 7월은 3개월 영향 구간의 시작월이며 지연발생 패턴상 실제 물량 영향이 아직 제한적인 구간으로 보았다. 기준 가동률 0.45를 유지해 최종 입력값을 0.45로 제안한다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.44 | 2026년 8월은 제재·선박 확인 절차의 영향이 일부 나타나기 시작하는 중간월로 보았다. 기준 가동률 0.45에서 낮은 강도의 차질만 반영해 최종 입력값을 0.44로 소폭 낮춘다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.43 | 2026년 9월은 3개월 구간 후반으로, 지연된 제재 관련 물류 차질이 가장 직접적으로 반영되는 월로 보았다. 다만 차질 강도가 낮고 대체 LNG 확보가 가능하므로 기준 가동률 0.45에서 제한적으로 낮춰 최종 입력값을 0.43으로 제안한다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | null | 0.2475 | 2026년 7월은 지연발생 구간의 시작월로 생산 차질이 아직 제한적이라고 보았다. 명목용량 6.599999 MTPA를 월 환산한 약 0.55 Mt/month에 보수적 기준 가동 수준 0.45를 적용해 최종 생산량을 0.2475 Mt LNG/month로 제안한다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | null | 0.242 | 2026년 8월은 제재 관련 확인 절차와 물류 제약이 일부 생산 운용에 반영되는 월로 보았다. 월 환산 명목용량 약 0.55 Mt/month에 소폭 낮춘 운용 수준 0.44를 적용해 최종 생산량을 0.2420 Mt LNG/month로 산정한다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | null | 0.2365 | 2026년 9월은 3개월 구간 후반으로 지연된 물류·거래 제약이 가장 크게 반영되는 월로 보았다. 낮은 강도의 차질만 반영해 월 환산 명목용량 약 0.55 Mt/month에 운용 수준 0.43을 적용하고, 최종 생산량을 0.2365 Mt LNG/month로 제안한다. |

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "Month": 8, "Year": 2026}` | null | 0.01 | 2026년 8월은 지연된 차질이 일부 나타나는 첫 구간으로 보았다. Arctic LNG 2 T1의 낮은 강도 생산 감소분만 러시아 공급 차질의 가스 등가량으로 반영해 최종 입력값을 0.01 Bcm으로 제안한다. |
| 2 | `{"Country": "Russia", "Month": 9, "Year": 2026}` | null | 0.02 | 2026년 9월은 3개월 구간 후반으로 물류·거래 제약의 물량 영향이 상대적으로 커지는 월로 보았다. 다만 러시아 전체 upstream 차질로 확대되었다는 근거는 약하므로 Arctic LNG 2 관련 소규모 차질만 반영해 최종 입력값을 0.02 Bcm으로 제안한다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0345 | 2026년 중국 Gas 전원 비중은 기준값 0.0346을 출발점으로 삼았다. 3개월짜리 낮은 강도의 LNG 차질을 PowerMix 조정으로 상쇄하는 경우이므로 연간 비중 조정은 작게 제한해 최종 입력값을 0.0345로 제안한다. |

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
  "model_param_proposal_id": 81,
  "proposal_completed_dtm": "2026-07-07 21:21:02.383485",
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
      "rationale": "공급 차질 강도 ‘낮음’은 Arctic LNG 2 T1의 액화 가동률을 제한적으로 낮추는 요인으로 연결된다. 타 공급원 경유 LNG 확보가 100% 가능하다는 점은 실물 부족을 완화하므로 가동률 조정 폭은 작게 두고, 3개월·지연발생-단계적 회복 맥락에 맞춰 초기에는 유지 후 후반으로 갈수록 소폭 하향하는 구조로 제안한다.",
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
          "rationale": "2026년 7월은 3개월 영향 구간의 시작월이며 지연발생 패턴상 실제 물량 영향이 아직 제한적인 구간으로 보았다. 기준 가동률 0.45를 유지해 최종 입력값을 0.45로 제안한다."
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
          "proposedValue": 0.44,
          "rationale": "2026년 8월은 제재·선박 확인 절차의 영향이 일부 나타나기 시작하는 중간월로 보았다. 기준 가동률 0.45에서 낮은 강도의 차질만 반영해 최종 입력값을 0.44로 소폭 낮춘다."
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
          "proposedValue": 0.43,
          "rationale": "2026년 9월은 3개월 구간 후반으로, 지연된 제재 관련 물류 차질이 가장 직접적으로 반영되는 월로 보았다. 다만 차질 강도가 낮고 대체 LNG 확보가 가능하므로 기준 가동률 0.45에서 제한적으로 낮춰 최종 입력값을 0.43으로 제안한다."
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
      "rationale": "공급 차질 강도 ‘낮음’은 생산량 직접 감소로 연결되지만, 제재 이슈의 성격이 설비 손상보다 거래·선박·구매자 접근 제약에 가깝기 때문에 생산량 감소 폭은 제한적이다. 3개월·지연발생-단계적 회복 패턴을 반영해 Arctic LNG 2 T1의 월별 절대 생산량을 초기 유지, 이후 소폭 하향하는 방식으로 제안한다.",
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
          "basecaseValue": null,
          "proposedValue": 0.2475,
          "rationale": "2026년 7월은 지연발생 구간의 시작월로 생산 차질이 아직 제한적이라고 보았다. 명목용량 6.599999 MTPA를 월 환산한 약 0.55 Mt/month에 보수적 기준 가동 수준 0.45를 적용해 최종 생산량을 0.2475 Mt LNG/month로 제안한다."
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
          "basecaseValue": null,
          "proposedValue": 0.242,
          "rationale": "2026년 8월은 제재 관련 확인 절차와 물류 제약이 일부 생산 운용에 반영되는 월로 보았다. 월 환산 명목용량 약 0.55 Mt/month에 소폭 낮춘 운용 수준 0.44를 적용해 최종 생산량을 0.2420 Mt LNG/month로 산정한다."
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
          "basecaseValue": null,
          "proposedValue": 0.2365,
          "rationale": "2026년 9월은 3개월 구간 후반으로 지연된 물류·거래 제약이 가장 크게 반영되는 월로 보았다. 낮은 강도의 차질만 반영해 월 환산 명목용량 약 0.55 Mt/month에 운용 수준 0.43을 적용하고, 최종 생산량을 0.2365 Mt LNG/month로 제안한다."
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
      "rationale": "공급 차질 강도 ‘낮음’은 러시아 공급 차질 가능성과 연결되지만, 이번 사건은 러시아 전체 upstream 생산 중단보다는 Arctic LNG 2 관련 제재·무역 흐름 제약이 핵심이다. 따라서 국가 단위 공급 차질 값은 넓게 적용하지 않고, 3개월·지연발생 패턴상 후반부에만 LNG 생산 차질의 가스 등가 수준을 보수적으로 반영한다.",
      "values": [
        {
          "Country": "Russia",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.01,
          "rationale": "2026년 8월은 지연된 차질이 일부 나타나는 첫 구간으로 보았다. Arctic LNG 2 T1의 낮은 강도 생산 감소분만 러시아 공급 차질의 가스 등가량으로 반영해 최종 입력값을 0.01 Bcm으로 제안한다."
        },
        {
          "Country": "Russia",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.02,
          "rationale": "2026년 9월은 3개월 구간 후반으로 물류·거래 제약의 물량 영향이 상대적으로 커지는 월로 보았다. 다만 러시아 전체 upstream 차질로 확대되었다는 근거는 약하므로 Arctic LNG 2 관련 소규모 차질만 반영해 최종 입력값을 0.02 Bcm으로 제안한다."
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
      "rationale": "PowerMix 조정을 통한 LNG 수요 감소량이 100% 가능하다는 설정은 가스 발전 비중을 낮춰 부족분을 흡수할 수 있음을 의미한다. 다만 기간이 3개월이고 공급 차질 강도도 낮아 연간 전원 비중에는 매우 제한적인 하향만 반영하며, 중국의 Gas 비중을 소폭 낮추는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0345,
          "rationale": "2026년 중국 Gas 전원 비중은 기준값 0.0346을 출발점으로 삼았다. 3개월짜리 낮은 강도의 LNG 차질을 PowerMix 조정으로 상쇄하는 경우이므로 연간 비중 조정은 작게 제한해 최종 입력값을 0.0345로 제안한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 22,
  "scenario_id": 129,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.146 | 4.146 | 2857 | 222 | 3079 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:09.098 | 69.098 | 12604 | 4743 | 17347 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:15.996 | 75.996 | 10675 | 4996 | 15671 |

#### scenario_id=130 1년 중반까지 완만한 조달 긴장 후 해소

- 소요시간: 04:36.758 (276.758s)
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
| Step2 selected slot | 58 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=49, basecaseValue_present=34 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 12 | 공급 차질 강도 ‘중간’은 Arctic LNG 2 T1의 액화시설 가동률 하향 조정과 직접 연결되며, 대체 LNG 확보 50%는 조달 압력을 일부 완화하지만 대체 공급 형성 지연으로 완전한 상쇄는 어렵다는 의미로 반영했다. ‘지연발생-즉시 해소’ 패턴과 1년 기간을 고려해 초기에는 유지, 누적 제약이 나타나는 구간은 보수적으로 하향, 해소 이후에는 기준 수준으로 복귀시키는 구조로 제안한다. |
| 2 | LiqProdAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqProdAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqProdAdjustment"]` | 12 | 공급 차질 강도 ‘중간’은 Arctic LNG 2 T1의 월별 LNG 생산량 절대값 하향과 직접 연결된다. 지연발생 후 즉시 해소되는 패턴에 맞춰 초기와 해소 구간은 정상 램프업 수준을 두고, 제재·운송 제약이 누적되는 구간만 보수적으로 낮춘 월별 절대 생산량을 제안한다. |
| 3 | SupplyDisruption | `{"modelFile": "Supply", "modelSheet": "VolumeAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Volumes (Bcm)"]` | 3 | 공급 차질 강도 ‘중간’은 러시아 관련 공급 차질 물량 설정과 연결되지만, 이번 사건의 핵심은 upstream 생산 설비 손상보다 Arctic LNG 2의 제재·선박·거래 제약이다. 따라서 upstream 전체 생산 차질로 확대하지 않고, 지연발생 후 제약이 누적되는 직접 영향 구간에 한해 Arctic LNG 2 T1 관련 월별 절대 차질 물량을 보수적으로 반영한다. |
| 4 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 22 | PowerMix 조정을 통한 LNG 수요 감소량 50%는 가스발전 비중 하향을 통해 일부 LNG 수요를 줄이는 직접 요인이다. 다만 가격 영향이 mild_bull이고 기간이 2026년 하반기와 2027년 상반기에 걸친 1년이므로, 연간 Gas share에는 절반 연도 효과를 반영한 보수적 하향 조정 구조를 적용한다. |

##### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 103, "Year": 2026}` | 0.45 | 0.45 | 해당 월은 지연발생 패턴의 초기 구간으로 보아 제재·선박 제약이 아직 가동률에 본격 반영되기 전으로 처리했다. 기준값 0.45를 그대로 유지해 최종 가동률을 0.45로 제안한다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 104, "Year": 2026}` | 0.45 | 0.45 | 해당 월은 지연발생 초기 구간으로, 조달 긴장은 커지지만 생산 가동률 override에는 아직 추가 하향을 적용하지 않는 보수적 처리로 보았다. 기준값 0.45를 유지한다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 105, "Year": 2026}` | 0.45 | 0.36 | 해당 월은 제재 집행과 선박 운항 제약이 누적되는 구간으로 보아 중간 강도의 가동 차질을 반영했다. 기준값 0.45에 20% 상대 하향을 적용해 최종 가동률을 0.36으로 산정했다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 106, "Year": 2026}` | 0.45 | 0.36 | 해당 월은 누적된 제재·운송 제약의 영향이 지속되는 중심 구간으로 보았다. 기준값 0.45를 중간 강도 차질에 맞춰 20% 상대 하향하여 0.36으로 제안한다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 107, "Year": 2026}` | 0.45 | 0.36 | 해당 월은 즉시 해소 전까지 제재 관련 운송·거래 제약이 남아 있는 구간으로 처리했다. 기준값 0.45에 동일한 20% 상대 하향을 적용해 0.36을 최종값으로 둔다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 6.599999, "Period": 108, "Year": 2026}` | 0 | 0 | 해당 월의 기준 가동률이 이미 0으로 설정되어 있어 추가 하향 여지가 없다. 차질 시나리오를 반영하더라도 최종 가동률은 0으로 유지한다. |
| 7 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 6.599999, "Period": 109, "Year": 2027}` | 0 | 0 | 해당 월의 기준값이 0이므로 제재 차질을 별도 가동률 하향으로 추가 반영하지 않는다. 최종 입력값은 기준과 동일한 0이다. |
| 8 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 6.599999, "Period": 110, "Year": 2027}` | 0 | 0 | 해당 월은 기준 가동률이 0으로 설정된 구간이므로 중간 강도 차질에도 음수 조정은 적용하지 않는다. 최종값은 0으로 유지한다. |
| 9 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 6.599999, "Period": 111, "Year": 2027}` | 0 | 0 | 해당 월의 기준값이 0이므로 추가적인 가동률 감소를 적용하지 않는다. 최종 모델 입력값은 0이다. |
| 10 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2027}` | 0 | 0 | 해당 월은 기준 가동률이 이미 0인 구간으로, 시나리오상 차질을 추가해도 하한 0을 벗어날 수 없다. 최종값은 0으로 둔다. |
| 11 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2027}` | 0 | 0 | 해당 월의 기준 가동률이 0이므로 별도 하향 조정 없이 기준값을 유지한다. 최종 입력값은 0이다. |
| 12 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2027}` | 0.45 | 0.45 | 해당 월은 지연 발생 후 즉시 해소되는 패턴의 복귀 구간으로 보아 추가 차질을 종료했다. 기준값 0.45를 유지해 최종 가동률을 0.45로 제안한다. |

###### Proposed Values - LiqProdAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 103, "Year": 2026}` | null | 0.2475 | 해당 월은 지연발생 초기로 보아 명판용량 6.599999 MTPA의 월 환산치에 정상 램프업 가동률 0.45를 적용했다. 최종 생산량은 약 0.2475 Mt LNG/month로 산정했다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 104, "Year": 2026}` | null | 0.2475 | 해당 월은 아직 본격 차질 전 단계로 처리하여 월 환산 명판용량에 가동률 0.45를 적용했다. 최종 생산량은 0.2475 Mt LNG/month로 제안한다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 105, "Year": 2026}` | null | 0.198 | 해당 월은 누적된 제재·선박 제약이 생산에 반영되는 구간으로 보았다. 월 환산 명판용량에 중간 강도 차질을 반영한 가동률 0.36을 적용해 0.198 Mt LNG/month로 산정했다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 106, "Year": 2026}` | null | 0.198 | 해당 월은 차질의 중심 구간으로 보아 같은 중간 강도 생산 하향을 적용했다. 6.599999 MTPA를 월 단위로 환산한 뒤 가동률 0.36을 적용해 0.198 Mt LNG/month로 둔다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 107, "Year": 2026}` | null | 0.198 | 해당 월은 해소 전 제약 지속 구간으로 보아 전월과 동일한 차질 강도를 적용했다. 최종 월 생산량은 0.198 Mt LNG/month로 산정했다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 6.599999, "Period": 108, "Year": 2026}` | null | 0 | 해당 월은 가동률 override 구조상 생산을 두지 않는 구간으로 맞추어 보수적으로 0 Mt LNG/month를 적용했다. 차질 반영으로 음수 생산량을 만들지 않는다. |
| 7 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 6.599999, "Period": 109, "Year": 2027}` | null | 0 | 해당 월은 생산 override를 두지 않는 구간으로 처리했다. 최종 월 생산량은 0 Mt LNG/month로 제안한다. |
| 8 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 6.599999, "Period": 110, "Year": 2027}` | null | 0 | 해당 월은 생산 미반영 구간으로 보아 0 Mt LNG/month를 적용한다. 제안값은 하한 제약에 맞춰 0으로 둔다. |
| 9 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 6.599999, "Period": 111, "Year": 2027}` | null | 0 | 해당 월은 생산량 override를 추가하지 않는 구간으로 처리했다. 최종 입력값은 0 Mt LNG/month이다. |
| 10 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2027}` | null | 0 | 해당 월은 생산 미반영 구간으로 보수적으로 0 Mt LNG/month를 적용했다. 추가 차질로 음수 값을 만들지 않는다. |
| 11 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2027}` | null | 0 | 해당 월은 해소 전후 전환 구간이지만 생산 override 기준상 월 생산량을 0으로 둔다. 최종값은 0 Mt LNG/month이다. |
| 12 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2027}` | null | 0.2475 | 해당 월은 즉시 해소 후 정상 램프업 수준으로 복귀하는 구간으로 보았다. 월 환산 명판용량에 가동률 0.45를 적용해 0.2475 Mt LNG/month로 산정했다. |

###### Proposed Values - SupplyDisruption

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "Month": 9, "Year": 2026}` | null | 0.0673 | 해당 월은 지연발생 후 제재·운송 제약이 실제 공급 흐름에 반영되기 시작하는 직접 영향 구간으로 선택했다. Arctic LNG 2 T1의 정상 램프업 대비 중간 강도 하향분을 LNG 물량에서 가스 등가 Bcm으로 환산해 약 0.0673 Bcm를 최종 절대 차질 물량으로 산정했다. |
| 2 | `{"Country": "Russia", "Month": 10, "Year": 2026}` | null | 0.0673 | 해당 월은 제재와 선박 제약이 누적되는 중심 구간으로 보아 전월과 같은 월별 절대 차질 물량을 적용했다. 중간 강도의 생산·수출 제약을 Arctic LNG 2 T1 기준 가동 하향분으로 환산해 0.0673 Bcm로 제안한다. |
| 3 | `{"Country": "Russia", "Month": 11, "Year": 2026}` | null | 0.0673 | 해당 월은 즉시 해소 전 마지막 직접 영향 구간으로 처리했다. 제재 제약은 지속되지만 upstream 전체 생산 차질로 확대하지 않는 보수적 접근에 따라 0.0673 Bcm의 월별 절대 차질 물량을 적용한다. |

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.18525 | 해당 연도는 영향 기간의 하반기만 포함되는 연간 축이므로 기준 Gas share 0.19에 절반 연도 효과를 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.18525로 산정했다. |
| 2 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2027}` | 0.18 | 0.1755 | 해당 연도는 영향 기간의 상반기만 포함되는 연간 축으로 처리했다. 기준 Gas share 0.18에 2.5% 상대 하향을 적용해 0.1755를 제안한다. |
| 3 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.033735 | 해당 연도 Gas share 기준값 0.0346에 반년 영향에 해당하는 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.033735로 산정했다. |
| 4 | `{"Country": "China", "Energy Source": "Gas", "Year": 2027}` | 0.0365 | 0.0355875 | 해당 연도는 상반기 영향만 연간 값에 반영되는 것으로 보았다. 기준 Gas share 0.0365를 2.5% 상대 하향해 0.0355875로 제안한다. |
| 5 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.04095 | 해당 연도 기준 Gas share 0.042에 반년 효과를 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.04095이다. |
| 6 | `{"Country": "France", "Energy Source": "Gas", "Year": 2027}` | 0.034 | 0.03315 | 해당 연도 기준 Gas share 0.034에 영향 기간의 상반기 반영분으로 2.5% 상대 하향을 적용했다. 최종값은 0.03315로 둔다. |
| 7 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.131625 | 해당 연도 기준 Gas share 0.135에 연간 절반 수준의 수요 절감 반영분을 적용했다. 2.5% 상대 하향 후 최종값은 0.131625이다. |
| 8 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2027}` | 0.13 | 0.12675 | 해당 연도 기준 Gas share 0.13에 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종 Gas share는 0.12675로 산정했다. |
| 9 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.42315 | 해당 연도 기준 Gas share 0.434에 반년 영향에 해당하는 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.42315로 제안한다. |
| 10 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2027}` | 0.422 | 0.41145 | 해당 연도 기준 Gas share 0.422에 2027년 상반기 수요 절감 효과를 반영했다. 2.5% 상대 하향 후 최종값은 0.41145이다. |
| 11 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.314925 | 해당 연도 기준 Gas share 0.323에 영향 기간의 하반기 반영분으로 2.5% 상대 하향을 적용했다. 최종값은 0.314925이다. |
| 12 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2027}` | 0.318 | 0.31005 | 해당 연도 기준 Gas share 0.318에 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종 Gas share는 0.31005로 산정했다. |
| 13 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.3102349137931034 | 해당 연도 기준 Gas share 0.31818965517241377에 반년 영향분을 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.3102349137931034로 산정했다. |
| 14 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2027}` | 0.33707317073170734 | 0.32864634146341465 | 해당 연도 기준 Gas share 0.33707317073170734에 상반기 영향분으로 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.32864634146341464이다. |
| 15 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.277875 | 해당 연도 기준 Gas share 0.285에 하반기 수요 절감 효과를 반영해 2.5% 상대 하향했다. 최종값은 0.277875이다. |
| 16 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2027}` | 0.265 | 0.258375 | 해당 연도 기준 Gas share 0.265에 상반기 영향분을 반영했다. 2.5% 상대 하향 후 최종 Gas share는 0.258375이다. |
| 17 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.207675 | 해당 연도 기준 Gas share 0.213에 영향 기간의 하반기분으로 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.207675이다. |
| 18 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2027}` | 0.211 | 0.205725 | 해당 연도 기준 Gas share 0.211에 2027년 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종값은 0.205725로 제안한다. |
| 19 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2026}` | 0.474 | 0.46215 | 해당 연도 기준 Gas share 0.474에 반년 영향분을 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.46215로 산정했다. |
| 20 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2027}` | 0.495 | 0.482625 | 해당 연도 기준 Gas share 0.495에 상반기 수요 절감 효과를 반영했다. 2.5% 상대 하향 후 최종값은 0.482625이다. |
| 21 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.28275 | 해당 연도 기준 Gas share 0.29에 영향 기간의 하반기 반영분으로 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.28275이다. |
| 22 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2027}` | 0.29 | 0.28275 | 해당 연도 기준 Gas share 0.29에 2027년 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종 Gas share는 0.28275로 산정했다. |

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
  "model_param_proposal_id": 84,
  "proposal_completed_dtm": "2026-07-07 21:23:18.358208",
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
      "rationale": "공급 차질 강도 ‘중간’은 Arctic LNG 2 T1의 액화시설 가동률 하향 조정과 직접 연결되며, 대체 LNG 확보 50%는 조달 압력을 일부 완화하지만 대체 공급 형성 지연으로 완전한 상쇄는 어렵다는 의미로 반영했다. ‘지연발생-즉시 해소’ 패턴과 1년 기간을 고려해 초기에는 유지, 누적 제약이 나타나는 구간은 보수적으로 하향, 해소 이후에는 기준 수준으로 복귀시키는 구조로 제안한다.",
      "values": [
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "해당 월은 지연발생 패턴의 초기 구간으로 보아 제재·선박 제약이 아직 가동률에 본격 반영되기 전으로 처리했다. 기준값 0.45를 그대로 유지해 최종 가동률을 0.45로 제안한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "해당 월은 지연발생 초기 구간으로, 조달 긴장은 커지지만 생산 가동률 override에는 아직 추가 하향을 적용하지 않는 보수적 처리로 보았다. 기준값 0.45를 유지한다."
        },
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
          "proposedValue": 0.36,
          "rationale": "해당 월은 제재 집행과 선박 운항 제약이 누적되는 구간으로 보아 중간 강도의 가동 차질을 반영했다. 기준값 0.45에 20% 상대 하향을 적용해 최종 가동률을 0.36으로 산정했다."
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
          "proposedValue": 0.36,
          "rationale": "해당 월은 누적된 제재·운송 제약의 영향이 지속되는 중심 구간으로 보았다. 기준값 0.45를 중간 강도 차질에 맞춰 20% 상대 하향하여 0.36으로 제안한다."
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
          "proposedValue": 0.36,
          "rationale": "해당 월은 즉시 해소 전까지 제재 관련 운송·거래 제약이 남아 있는 구간으로 처리했다. 기준값 0.45에 동일한 20% 상대 하향을 적용해 0.36을 최종값으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 108,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월의 기준 가동률이 이미 0으로 설정되어 있어 추가 하향 여지가 없다. 차질 시나리오를 반영하더라도 최종 가동률은 0으로 유지한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 109,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월의 기준값이 0이므로 제재 차질을 별도 가동률 하향으로 추가 반영하지 않는다. 최종 입력값은 기준과 동일한 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 110,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월은 기준 가동률이 0으로 설정된 구간이므로 중간 강도 차질에도 음수 조정은 적용하지 않는다. 최종값은 0으로 유지한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 111,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월의 기준값이 0이므로 추가적인 가동률 감소를 적용하지 않는다. 최종 모델 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월은 기준 가동률이 이미 0인 구간으로, 시나리오상 차질을 추가해도 하한 0을 벗어날 수 없다. 최종값은 0으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월의 기준 가동률이 0이므로 별도 하향 조정 없이 기준값을 유지한다. 최종 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "해당 월은 지연 발생 후 즉시 해소되는 패턴의 복귀 구간으로 보아 추가 차질을 종료했다. 기준값 0.45를 유지해 최종 가동률을 0.45로 제안한다."
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
      "rationale": "공급 차질 강도 ‘중간’은 Arctic LNG 2 T1의 월별 LNG 생산량 절대값 하향과 직접 연결된다. 지연발생 후 즉시 해소되는 패턴에 맞춰 초기와 해소 구간은 정상 램프업 수준을 두고, 제재·운송 제약이 누적되는 구간만 보수적으로 낮춘 월별 절대 생산량을 제안한다.",
      "values": [
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.2475,
          "rationale": "해당 월은 지연발생 초기로 보아 명판용량 6.599999 MTPA의 월 환산치에 정상 램프업 가동률 0.45를 적용했다. 최종 생산량은 약 0.2475 Mt LNG/month로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.2475,
          "rationale": "해당 월은 아직 본격 차질 전 단계로 처리하여 월 환산 명판용량에 가동률 0.45를 적용했다. 최종 생산량은 0.2475 Mt LNG/month로 제안한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.198,
          "rationale": "해당 월은 누적된 제재·선박 제약이 생산에 반영되는 구간으로 보았다. 월 환산 명판용량에 중간 강도 차질을 반영한 가동률 0.36을 적용해 0.198 Mt LNG/month로 산정했다."
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
          "basecaseValue": null,
          "proposedValue": 0.198,
          "rationale": "해당 월은 차질의 중심 구간으로 보아 같은 중간 강도 생산 하향을 적용했다. 6.599999 MTPA를 월 단위로 환산한 뒤 가동률 0.36을 적용해 0.198 Mt LNG/month로 둔다."
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
          "basecaseValue": null,
          "proposedValue": 0.198,
          "rationale": "해당 월은 해소 전 제약 지속 구간으로 보아 전월과 동일한 차질 강도를 적용했다. 최종 월 생산량은 0.198 Mt LNG/month로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 108,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "해당 월은 가동률 override 구조상 생산을 두지 않는 구간으로 맞추어 보수적으로 0 Mt LNG/month를 적용했다. 차질 반영으로 음수 생산량을 만들지 않는다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 109,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "해당 월은 생산 override를 두지 않는 구간으로 처리했다. 최종 월 생산량은 0 Mt LNG/month로 제안한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 110,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "해당 월은 생산 미반영 구간으로 보아 0 Mt LNG/month를 적용한다. 제안값은 하한 제약에 맞춰 0으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 111,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "해당 월은 생산량 override를 추가하지 않는 구간으로 처리했다. 최종 입력값은 0 Mt LNG/month이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "해당 월은 생산 미반영 구간으로 보수적으로 0 Mt LNG/month를 적용했다. 추가 차질로 음수 값을 만들지 않는다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "해당 월은 해소 전후 전환 구간이지만 생산 override 기준상 월 생산량을 0으로 둔다. 최종값은 0 Mt LNG/month이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0.2475,
          "rationale": "해당 월은 즉시 해소 후 정상 램프업 수준으로 복귀하는 구간으로 보았다. 월 환산 명판용량에 가동률 0.45를 적용해 0.2475 Mt LNG/month로 산정했다."
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
      "rationale": "공급 차질 강도 ‘중간’은 러시아 관련 공급 차질 물량 설정과 연결되지만, 이번 사건의 핵심은 upstream 생산 설비 손상보다 Arctic LNG 2의 제재·선박·거래 제약이다. 따라서 upstream 전체 생산 차질로 확대하지 않고, 지연발생 후 제약이 누적되는 직접 영향 구간에 한해 Arctic LNG 2 T1 관련 월별 절대 차질 물량을 보수적으로 반영한다.",
      "values": [
        {
          "Country": "Russia",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.0673,
          "rationale": "해당 월은 지연발생 후 제재·운송 제약이 실제 공급 흐름에 반영되기 시작하는 직접 영향 구간으로 선택했다. Arctic LNG 2 T1의 정상 램프업 대비 중간 강도 하향분을 LNG 물량에서 가스 등가 Bcm으로 환산해 약 0.0673 Bcm를 최종 절대 차질 물량으로 산정했다."
        },
        {
          "Country": "Russia",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.0673,
          "rationale": "해당 월은 제재와 선박 제약이 누적되는 중심 구간으로 보아 전월과 같은 월별 절대 차질 물량을 적용했다. 중간 강도의 생산·수출 제약을 Arctic LNG 2 T1 기준 가동 하향분으로 환산해 0.0673 Bcm로 제안한다."
        },
        {
          "Country": "Russia",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.0673,
          "rationale": "해당 월은 즉시 해소 전 마지막 직접 영향 구간으로 처리했다. 제재 제약은 지속되지만 upstream 전체 생산 차질로 확대하지 않는 보수적 접근에 따라 0.0673 Bcm의 월별 절대 차질 물량을 적용한다."
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
      "rationale": "PowerMix 조정을 통한 LNG 수요 감소량 50%는 가스발전 비중 하향을 통해 일부 LNG 수요를 줄이는 직접 요인이다. 다만 가격 영향이 mild_bull이고 기간이 2026년 하반기와 2027년 상반기에 걸친 1년이므로, 연간 Gas share에는 절반 연도 효과를 반영한 보수적 하향 조정 구조를 적용한다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.18525,
          "rationale": "해당 연도는 영향 기간의 하반기만 포함되는 연간 축이므로 기준 Gas share 0.19에 절반 연도 효과를 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.18525로 산정했다."
        },
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1755,
          "rationale": "해당 연도는 영향 기간의 상반기만 포함되는 연간 축으로 처리했다. 기준 Gas share 0.18에 2.5% 상대 하향을 적용해 0.1755를 제안한다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.033735,
          "rationale": "해당 연도 Gas share 기준값 0.0346에 반년 영향에 해당하는 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.033735로 산정했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.0365,
          "proposedValue": 0.0355875,
          "rationale": "해당 연도는 상반기 영향만 연간 값에 반영되는 것으로 보았다. 기준 Gas share 0.0365를 2.5% 상대 하향해 0.0355875로 제안한다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04095,
          "rationale": "해당 연도 기준 Gas share 0.042에 반년 효과를 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.04095이다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03315,
          "rationale": "해당 연도 기준 Gas share 0.034에 영향 기간의 상반기 반영분으로 2.5% 상대 하향을 적용했다. 최종값은 0.03315로 둔다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.131625,
          "rationale": "해당 연도 기준 Gas share 0.135에 연간 절반 수준의 수요 절감 반영분을 적용했다. 2.5% 상대 하향 후 최종값은 0.131625이다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.12675,
          "rationale": "해당 연도 기준 Gas share 0.13에 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종 Gas share는 0.12675로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.42315,
          "rationale": "해당 연도 기준 Gas share 0.434에 반년 영향에 해당하는 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.42315로 제안한다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.41145,
          "rationale": "해당 연도 기준 Gas share 0.422에 2027년 상반기 수요 절감 효과를 반영했다. 2.5% 상대 하향 후 최종값은 0.41145이다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.314925,
          "rationale": "해당 연도 기준 Gas share 0.323에 영향 기간의 하반기 반영분으로 2.5% 상대 하향을 적용했다. 최종값은 0.314925이다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.318,
          "proposedValue": 0.31005,
          "rationale": "해당 연도 기준 Gas share 0.318에 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종 Gas share는 0.31005로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3102349137931034,
          "rationale": "해당 연도 기준 Gas share 0.31818965517241377에 반년 영향분을 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.3102349137931034로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.32864634146341465,
          "rationale": "해당 연도 기준 Gas share 0.33707317073170734에 상반기 영향분으로 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.32864634146341464이다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.277875,
          "rationale": "해당 연도 기준 Gas share 0.285에 하반기 수요 절감 효과를 반영해 2.5% 상대 하향했다. 최종값은 0.277875이다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.265,
          "proposedValue": 0.258375,
          "rationale": "해당 연도 기준 Gas share 0.265에 상반기 영향분을 반영했다. 2.5% 상대 하향 후 최종 Gas share는 0.258375이다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.207675,
          "rationale": "해당 연도 기준 Gas share 0.213에 영향 기간의 하반기분으로 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.207675이다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.205725,
          "rationale": "해당 연도 기준 Gas share 0.211에 2027년 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종값은 0.205725로 제안한다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.474,
          "proposedValue": 0.46215,
          "rationale": "해당 연도 기준 Gas share 0.474에 반년 영향분을 반영한 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.46215로 산정했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.495,
          "proposedValue": 0.482625,
          "rationale": "해당 연도 기준 Gas share 0.495에 상반기 수요 절감 효과를 반영했다. 2.5% 상대 하향 후 최종값은 0.482625이다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "해당 연도 기준 Gas share 0.29에 영향 기간의 하반기 반영분으로 2.5% 상대 하향을 적용했다. 최종 Gas share는 0.28275이다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "해당 연도 기준 Gas share 0.29에 2027년 상반기 영향분을 반영해 2.5% 상대 하향했다. 최종 Gas share는 0.28275로 산정했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 22,
  "scenario_id": 130,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.287 | 4.287 | 2866 | 236 | 3102 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:20.558 | 80.558 | 12613 | 8268 | 20881 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 02:53.228 | 173.228 | 13985 | 11005 | 24990 |

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

- 소요시간: 00:56.577 (56.577s)
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
| 1 | Gas Futures Price | `{"modelFile": "Demand", "modelSheet": "CoalGasAdjustment", "tableName": "table2"}` | `["Month-Year", "Region"]` | `["Gas Futures Price (USD/mmbtu)"]` | 6 | 영향 강도는 ‘보통’으로, IMO 운송 규제에 따른 LNG 운송비 프리미엄 확대가 지역별 가스 가격과 Gas↔Coal 전환 유인에 연결되므로 Gas Futures Price 조정 대상으로 해석한다. 기간은 3개월, 시행은 확정, 구조는 단발적/한시로 제시되어 2026년 7~9월 Asia와 EU 선물가격에만 보수적인 상승 압력을 반영하고, 구조적 장기 상향은 적용하지 않는다. |

##### Proposed Parameter Values

###### Proposed Values - Gas Futures Price

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month-Year": "2026-07", "Region": "Asia"}` | null | 12.8 | 2026-07 Asia 슬롯은 3개월 한시 영향의 시작월이자 JKM 상승 영향이 직접 반영되는 지역으로 선택했다. 기준값 record가 제공되지 않아 0으로 보지 않고 USD/mmbtu 형식의 보수적 절대 가격으로 산정했으며, 시행 확정과 보통 강도의 운송비 프리미엄을 반영해 12.8로 제안한다. |
| 2 | `{"Month-Year": "2026-08", "Region": "Asia"}` | null | 12.9 | 2026-08 Asia 슬롯은 3개월 영향 구간의 중간월로, 한시적 운송비 프리미엄이 유지되는 구간이다. 기준값 record가 없어 동일 단위의 보수적 절대 가격을 사용하되, 프리미엄 지속에 따른 소폭 높은 수준을 반영해 12.9로 제안한다. |
| 3 | `{"Month-Year": "2026-09", "Region": "Asia"}` | null | 12.7 | 2026-09 Asia 슬롯은 3개월 한시 영향의 마지막 월로 선택했다. 단발적 영향이 종료 방향으로 완만해진다는 점을 반영해 8월보다 낮지만 여전히 상승 프리미엄이 남아 있는 최종 입력값 12.7을 제안한다. |
| 4 | `{"Month-Year": "2026-07", "Region": "EU"}` | null | 11.1 | 2026-07 EU 슬롯은 TTF 상승 영향이 반영되는 첫 달로 선택했다. 기준값 record가 제공되지 않아 USD/mmbtu 절대 가격 형식으로 보수적으로 산정했으며, 운송비 프리미엄과 유럽 LNG basis 민감도를 반영해 11.1로 제안한다. |
| 5 | `{"Month-Year": "2026-08", "Region": "EU"}` | null | 11.2 | 2026-08 EU 슬롯은 한시적 규제 비용 전가가 지속되는 중간월이다. 기준값 부재를 0으로 해석하지 않고 같은 형식의 절대 가격을 적용했으며, 보통 강도의 프리미엄 지속을 반영해 11.2로 제안한다. |
| 6 | `{"Month-Year": "2026-09", "Region": "EU"}` | null | 11.0 | 2026-09 EU 슬롯은 3개월 적용 기간의 마지막 월이다. 단발적/한시 성격에 따라 프리미엄이 점차 약화되는 보수적 경로를 반영해 11.0으로 제안한다. |

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
  "model_param_proposal_id": 80,
  "proposal_completed_dtm": "2026-07-07 21:19:59.873048",
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
      "rationale": "영향 강도는 ‘보통’으로, IMO 운송 규제에 따른 LNG 운송비 프리미엄 확대가 지역별 가스 가격과 Gas↔Coal 전환 유인에 연결되므로 Gas Futures Price 조정 대상으로 해석한다. 기간은 3개월, 시행은 확정, 구조는 단발적/한시로 제시되어 2026년 7~9월 Asia와 EU 선물가격에만 보수적인 상승 압력을 반영하고, 구조적 장기 상향은 적용하지 않는다.",
      "values": [
        {
          "Month-Year": "2026-07",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 12.8,
          "rationale": "2026-07 Asia 슬롯은 3개월 한시 영향의 시작월이자 JKM 상승 영향이 직접 반영되는 지역으로 선택했다. 기준값 record가 제공되지 않아 0으로 보지 않고 USD/mmbtu 형식의 보수적 절대 가격으로 산정했으며, 시행 확정과 보통 강도의 운송비 프리미엄을 반영해 12.8로 제안한다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 12.9,
          "rationale": "2026-08 Asia 슬롯은 3개월 영향 구간의 중간월로, 한시적 운송비 프리미엄이 유지되는 구간이다. 기준값 record가 없어 동일 단위의 보수적 절대 가격을 사용하되, 프리미엄 지속에 따른 소폭 높은 수준을 반영해 12.9로 제안한다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 12.7,
          "rationale": "2026-09 Asia 슬롯은 3개월 한시 영향의 마지막 월로 선택했다. 단발적 영향이 종료 방향으로 완만해진다는 점을 반영해 8월보다 낮지만 여전히 상승 프리미엄이 남아 있는 최종 입력값 12.7을 제안한다."
        },
        {
          "Month-Year": "2026-07",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 11.1,
          "rationale": "2026-07 EU 슬롯은 TTF 상승 영향이 반영되는 첫 달로 선택했다. 기준값 record가 제공되지 않아 USD/mmbtu 절대 가격 형식으로 보수적으로 산정했으며, 운송비 프리미엄과 유럽 LNG basis 민감도를 반영해 11.1로 제안한다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 11.2,
          "rationale": "2026-08 EU 슬롯은 한시적 규제 비용 전가가 지속되는 중간월이다. 기준값 부재를 0으로 해석하지 않고 같은 형식의 절대 가격을 적용했으며, 보통 강도의 프리미엄 지속을 반영해 11.2로 제안한다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 11.0,
          "rationale": "2026-09 EU 슬롯은 3개월 적용 기간의 마지막 월이다. 단발적/한시 성격에 따라 프리미엄이 점차 약화되는 보수적 경로를 반영해 11.0으로 제안한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:07.438 | 7.438 | 2627 | 329 | 2956 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:09.171 | 9.171 | 5323 | 685 | 6008 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:24.352 | 24.352 | 5378 | 1326 | 6704 |

#### scenario_id=282 [model_parameter_agent_test] IMO 운송 규제 큰 강도

- 소요시간: 01:51.456 (111.456s)
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
| 1 | Gas Futures Price | `{"modelFile": "Demand", "modelSheet": "CoalGasAdjustment", "tableName": "table2"}` | `["Month-Year", "Region"]` | `["Gas Futures Price (USD/mmbtu)"]` | 24 | 영향 강도 차원이 ‘큼’으로 선택되어 LNG 운송비·항로 제약 확대가 JKM 및 TTF 계열 가스 선물가격 상승 압력으로 연결되는 후보 파라미터입니다. 기간은 1년, 시행은 확정, 구조적 성격은 공통 맥락으로 보아 2026-07부터 2027-06까지 Asia와 EU 모두 상향된 가격 레벨을 적용하되, 기준값이 제공되지 않아 지역별로 보수적인 고정 가격 레벨을 사용합니다. |

##### Proposed Parameter Values

###### Proposed Values - Gas Futures Price

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Month-Year": "2026-07", "Region": "Asia"}` | null | 14.5 | 해당 월은 1년 영향 기간의 시작월이며 Asia는 JKM 가격 축에 해당한다. 기준값이 제공되지 않았으므로 IMO 규제 확정과 큰 강도의 운송비 상승 압력을 반영하되, 별도 월별 계절성 근거가 없어 보수적인 상향 가격 레벨 14.5 USD/mmbtu를 최종 입력값으로 둔다. |
| 2 | `{"Month-Year": "2026-08", "Region": "Asia"}` | null | 14.5 | 1년 지속 시나리오의 연속 월로서 Asia JKM 가격에 동일한 규제 비용 상승 압력을 적용한다. 기준값 부재와 월별 차등 근거 부족을 고려해 2026-07과 같은 보수적 상향 레벨 14.5 USD/mmbtu를 사용한다. |
| 3 | `{"Month-Year": "2026-09", "Region": "Asia"}` | null | 14.5 | 해당 월도 규제 영향 기간에 포함되며, 운송비 상승이 LNG 도착가격을 통해 Asia 가스 선물가격에 반영되는 구간이다. 기준값이 없어 큰 강도의 방향성만 반영한 보수적 고정 레벨 14.5 USD/mmbtu를 적용한다. |
| 4 | `{"Month-Year": "2026-10", "Region": "Asia"}` | null | 14.5 | 구조적 규제가 지속되는 1년 구간 내 월로 선택되었다. 월별 기준값이나 별도 완화 근거가 없으므로 Asia 가격은 상향 상태를 유지하는 최종 입력값 14.5 USD/mmbtu로 설정한다. |
| 5 | `{"Month-Year": "2026-11", "Region": "Asia"}` | null | 14.5 | 1년 영향 범위 안에서 IMO 운송 규제에 따른 비용 상승이 계속 반영되는 월이다. 기준값이 제공되지 않아 월별 변동은 만들지 않고 Asia에 대한 보수적 상향 가격 14.5 USD/mmbtu를 입력한다. |
| 6 | `{"Month-Year": "2026-12", "Region": "Asia"}` | null | 14.5 | 해당 월은 규제 영향이 지속되는 기간에 포함된다. 명확한 월별 차등 근거가 없고 기준값도 없으므로 Asia JKM 축에는 14.5 USD/mmbtu의 동일한 상향 최종값을 적용한다. |
| 7 | `{"Month-Year": "2027-01", "Region": "Asia"}` | null | 14.5 | 2026-07부터 1년 기간을 전개할 때 포함되는 월이며, 시행 확정 규제의 운송비 상승 효과가 유지되는 구간이다. 기준값 부재를 고려해 보수적인 Asia 상향 레벨 14.5 USD/mmbtu를 유지한다. |
| 8 | `{"Month-Year": "2027-02", "Region": "Asia"}` | null | 14.5 | 해당 월은 1년 적용 기간 중 후반부에 해당한다. 구조적 규제라는 공통 맥락상 영향이 급격히 소멸하지 않는 것으로 보고, 기준값이 없으므로 Asia 가격을 14.5 USD/mmbtu로 유지한다. |
| 9 | `{"Month-Year": "2027-03", "Region": "Asia"}` | null | 14.5 | 규제 영향 기간 내 Asia JKM 가격 슬롯으로, 큰 강도의 운송비 상승 압력을 반영해야 한다. 기준값 및 월별 차등 근거가 없으므로 동일한 보수적 최종 가격 14.5 USD/mmbtu를 적용한다. |
| 10 | `{"Month-Year": "2027-04", "Region": "Asia"}` | null | 14.5 | 1년 지속 시나리오에 따라 해당 월도 영향 범위에 포함된다. 기준값이 제공되지 않아 규제 비용 상승의 방향성만 보수적으로 반영한 Asia 가격 14.5 USD/mmbtu를 사용한다. |
| 11 | `{"Month-Year": "2027-05", "Region": "Asia"}` | null | 14.5 | 영향 기간 종료 전 월로서 운송비 상승 압력이 계속 반영되는 슬롯이다. 별도 완화나 월별 조정 근거가 없어 Asia 최종 입력값은 14.5 USD/mmbtu로 둔다. |
| 12 | `{"Month-Year": "2027-06", "Region": "Asia"}` | null | 14.5 | 2026-07부터 1년 적용 범위의 마지막 월로 해석된다. 구조적 규제 성격상 상승 압력이 유지되는 것으로 보고, 기준값 부재하에 Asia 가격 14.5 USD/mmbtu를 최종 입력한다. |
| 13 | `{"Month-Year": "2026-07", "Region": "EU"}` | null | 12.5 | 해당 월은 1년 영향 기간의 시작월이며 EU는 TTF 가격 축에 해당한다. 기준값이 제공되지 않았으므로 IMO 규제 확정과 큰 강도의 운송비 상승 압력을 반영하되, Asia보다 낮은 보수적 상향 레벨 12.5 USD/mmbtu를 최종 입력값으로 둔다. |
| 14 | `{"Month-Year": "2026-08", "Region": "EU"}` | null | 12.5 | 1년 지속 시나리오의 연속 월로서 EU TTF 가격에 동일한 규제 비용 상승 압력을 적용한다. 기준값 부재와 월별 차등 근거 부족을 고려해 2026-07과 같은 보수적 상향 레벨 12.5 USD/mmbtu를 사용한다. |
| 15 | `{"Month-Year": "2026-09", "Region": "EU"}` | null | 12.5 | 해당 월도 규제 영향 기간에 포함되며, 운송비 상승이 LNG 조달비용을 통해 EU 가스 선물가격에 반영되는 구간이다. 기준값이 없어 큰 강도의 방향성만 반영한 보수적 고정 레벨 12.5 USD/mmbtu를 적용한다. |
| 16 | `{"Month-Year": "2026-10", "Region": "EU"}` | null | 12.5 | 구조적 규제가 지속되는 1년 구간 내 월로 선택되었다. 월별 기준값이나 별도 완화 근거가 없으므로 EU 가격은 상향 상태를 유지하는 최종 입력값 12.5 USD/mmbtu로 설정한다. |
| 17 | `{"Month-Year": "2026-11", "Region": "EU"}` | null | 12.5 | 1년 영향 범위 안에서 IMO 운송 규제에 따른 비용 상승이 계속 반영되는 월이다. 기준값이 제공되지 않아 월별 변동은 만들지 않고 EU에 대한 보수적 상향 가격 12.5 USD/mmbtu를 입력한다. |
| 18 | `{"Month-Year": "2026-12", "Region": "EU"}` | null | 12.5 | 해당 월은 규제 영향이 지속되는 기간에 포함된다. 명확한 월별 차등 근거가 없고 기준값도 없으므로 EU TTF 축에는 12.5 USD/mmbtu의 동일한 상향 최종값을 적용한다. |
| 19 | `{"Month-Year": "2027-01", "Region": "EU"}` | null | 12.5 | 2026-07부터 1년 기간을 전개할 때 포함되는 월이며, 시행 확정 규제의 운송비 상승 효과가 유지되는 구간이다. 기준값 부재를 고려해 보수적인 EU 상향 레벨 12.5 USD/mmbtu를 유지한다. |
| 20 | `{"Month-Year": "2027-02", "Region": "EU"}` | null | 12.5 | 해당 월은 1년 적용 기간 중 후반부에 해당한다. 구조적 규제라는 공통 맥락상 영향이 급격히 소멸하지 않는 것으로 보고, 기준값이 없으므로 EU 가격을 12.5 USD/mmbtu로 유지한다. |
| 21 | `{"Month-Year": "2027-03", "Region": "EU"}` | null | 12.5 | 규제 영향 기간 내 EU TTF 가격 슬롯으로, 큰 강도의 운송비 상승 압력을 반영해야 한다. 기준값 및 월별 차등 근거가 없으므로 동일한 보수적 최종 가격 12.5 USD/mmbtu를 적용한다. |
| 22 | `{"Month-Year": "2027-04", "Region": "EU"}` | null | 12.5 | 1년 지속 시나리오에 따라 해당 월도 영향 범위에 포함된다. 기준값이 제공되지 않아 규제 비용 상승의 방향성만 보수적으로 반영한 EU 가격 12.5 USD/mmbtu를 사용한다. |
| 23 | `{"Month-Year": "2027-05", "Region": "EU"}` | null | 12.5 | 영향 기간 종료 전 월로서 운송비 상승 압력이 계속 반영되는 슬롯이다. 별도 완화나 월별 조정 근거가 없어 EU 최종 입력값은 12.5 USD/mmbtu로 둔다. |
| 24 | `{"Month-Year": "2027-06", "Region": "EU"}` | null | 12.5 | 2026-07부터 1년 적용 범위의 마지막 월로 해석된다. 구조적 규제 성격상 상승 압력이 유지되는 것으로 보고, 기준값 부재하에 EU 가격 12.5 USD/mmbtu를 최종 입력한다. |

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
  "model_param_proposal_id": 83,
  "proposal_completed_dtm": "2026-07-07 21:21:43.311554",
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
      "rationale": "영향 강도 차원이 ‘큼’으로 선택되어 LNG 운송비·항로 제약 확대가 JKM 및 TTF 계열 가스 선물가격 상승 압력으로 연결되는 후보 파라미터입니다. 기간은 1년, 시행은 확정, 구조적 성격은 공통 맥락으로 보아 2026-07부터 2027-06까지 Asia와 EU 모두 상향된 가격 레벨을 적용하되, 기준값이 제공되지 않아 지역별로 보수적인 고정 가격 레벨을 사용합니다.",
      "values": [
        {
          "Month-Year": "2026-07",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "해당 월은 1년 영향 기간의 시작월이며 Asia는 JKM 가격 축에 해당한다. 기준값이 제공되지 않았으므로 IMO 규제 확정과 큰 강도의 운송비 상승 압력을 반영하되, 별도 월별 계절성 근거가 없어 보수적인 상향 가격 레벨 14.5 USD/mmbtu를 최종 입력값으로 둔다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "1년 지속 시나리오의 연속 월로서 Asia JKM 가격에 동일한 규제 비용 상승 압력을 적용한다. 기준값 부재와 월별 차등 근거 부족을 고려해 2026-07과 같은 보수적 상향 레벨 14.5 USD/mmbtu를 사용한다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "해당 월도 규제 영향 기간에 포함되며, 운송비 상승이 LNG 도착가격을 통해 Asia 가스 선물가격에 반영되는 구간이다. 기준값이 없어 큰 강도의 방향성만 반영한 보수적 고정 레벨 14.5 USD/mmbtu를 적용한다."
        },
        {
          "Month-Year": "2026-10",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "구조적 규제가 지속되는 1년 구간 내 월로 선택되었다. 월별 기준값이나 별도 완화 근거가 없으므로 Asia 가격은 상향 상태를 유지하는 최종 입력값 14.5 USD/mmbtu로 설정한다."
        },
        {
          "Month-Year": "2026-11",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "1년 영향 범위 안에서 IMO 운송 규제에 따른 비용 상승이 계속 반영되는 월이다. 기준값이 제공되지 않아 월별 변동은 만들지 않고 Asia에 대한 보수적 상향 가격 14.5 USD/mmbtu를 입력한다."
        },
        {
          "Month-Year": "2026-12",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "해당 월은 규제 영향이 지속되는 기간에 포함된다. 명확한 월별 차등 근거가 없고 기준값도 없으므로 Asia JKM 축에는 14.5 USD/mmbtu의 동일한 상향 최종값을 적용한다."
        },
        {
          "Month-Year": "2027-01",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "2026-07부터 1년 기간을 전개할 때 포함되는 월이며, 시행 확정 규제의 운송비 상승 효과가 유지되는 구간이다. 기준값 부재를 고려해 보수적인 Asia 상향 레벨 14.5 USD/mmbtu를 유지한다."
        },
        {
          "Month-Year": "2027-02",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "해당 월은 1년 적용 기간 중 후반부에 해당한다. 구조적 규제라는 공통 맥락상 영향이 급격히 소멸하지 않는 것으로 보고, 기준값이 없으므로 Asia 가격을 14.5 USD/mmbtu로 유지한다."
        },
        {
          "Month-Year": "2027-03",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "규제 영향 기간 내 Asia JKM 가격 슬롯으로, 큰 강도의 운송비 상승 압력을 반영해야 한다. 기준값 및 월별 차등 근거가 없으므로 동일한 보수적 최종 가격 14.5 USD/mmbtu를 적용한다."
        },
        {
          "Month-Year": "2027-04",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "1년 지속 시나리오에 따라 해당 월도 영향 범위에 포함된다. 기준값이 제공되지 않아 규제 비용 상승의 방향성만 보수적으로 반영한 Asia 가격 14.5 USD/mmbtu를 사용한다."
        },
        {
          "Month-Year": "2027-05",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "영향 기간 종료 전 월로서 운송비 상승 압력이 계속 반영되는 슬롯이다. 별도 완화나 월별 조정 근거가 없어 Asia 최종 입력값은 14.5 USD/mmbtu로 둔다."
        },
        {
          "Month-Year": "2027-06",
          "Region": "Asia",
          "basecaseValue": null,
          "proposedValue": 14.5,
          "rationale": "2026-07부터 1년 적용 범위의 마지막 월로 해석된다. 구조적 규제 성격상 상승 압력이 유지되는 것으로 보고, 기준값 부재하에 Asia 가격 14.5 USD/mmbtu를 최종 입력한다."
        },
        {
          "Month-Year": "2026-07",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "해당 월은 1년 영향 기간의 시작월이며 EU는 TTF 가격 축에 해당한다. 기준값이 제공되지 않았으므로 IMO 규제 확정과 큰 강도의 운송비 상승 압력을 반영하되, Asia보다 낮은 보수적 상향 레벨 12.5 USD/mmbtu를 최종 입력값으로 둔다."
        },
        {
          "Month-Year": "2026-08",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "1년 지속 시나리오의 연속 월로서 EU TTF 가격에 동일한 규제 비용 상승 압력을 적용한다. 기준값 부재와 월별 차등 근거 부족을 고려해 2026-07과 같은 보수적 상향 레벨 12.5 USD/mmbtu를 사용한다."
        },
        {
          "Month-Year": "2026-09",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "해당 월도 규제 영향 기간에 포함되며, 운송비 상승이 LNG 조달비용을 통해 EU 가스 선물가격에 반영되는 구간이다. 기준값이 없어 큰 강도의 방향성만 반영한 보수적 고정 레벨 12.5 USD/mmbtu를 적용한다."
        },
        {
          "Month-Year": "2026-10",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "구조적 규제가 지속되는 1년 구간 내 월로 선택되었다. 월별 기준값이나 별도 완화 근거가 없으므로 EU 가격은 상향 상태를 유지하는 최종 입력값 12.5 USD/mmbtu로 설정한다."
        },
        {
          "Month-Year": "2026-11",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "1년 영향 범위 안에서 IMO 운송 규제에 따른 비용 상승이 계속 반영되는 월이다. 기준값이 제공되지 않아 월별 변동은 만들지 않고 EU에 대한 보수적 상향 가격 12.5 USD/mmbtu를 입력한다."
        },
        {
          "Month-Year": "2026-12",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "해당 월은 규제 영향이 지속되는 기간에 포함된다. 명확한 월별 차등 근거가 없고 기준값도 없으므로 EU TTF 축에는 12.5 USD/mmbtu의 동일한 상향 최종값을 적용한다."
        },
        {
          "Month-Year": "2027-01",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "2026-07부터 1년 기간을 전개할 때 포함되는 월이며, 시행 확정 규제의 운송비 상승 효과가 유지되는 구간이다. 기준값 부재를 고려해 보수적인 EU 상향 레벨 12.5 USD/mmbtu를 유지한다."
        },
        {
          "Month-Year": "2027-02",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "해당 월은 1년 적용 기간 중 후반부에 해당한다. 구조적 규제라는 공통 맥락상 영향이 급격히 소멸하지 않는 것으로 보고, 기준값이 없으므로 EU 가격을 12.5 USD/mmbtu로 유지한다."
        },
        {
          "Month-Year": "2027-03",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "규제 영향 기간 내 EU TTF 가격 슬롯으로, 큰 강도의 운송비 상승 압력을 반영해야 한다. 기준값 및 월별 차등 근거가 없으므로 동일한 보수적 최종 가격 12.5 USD/mmbtu를 적용한다."
        },
        {
          "Month-Year": "2027-04",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "1년 지속 시나리오에 따라 해당 월도 영향 범위에 포함된다. 기준값이 제공되지 않아 규제 비용 상승의 방향성만 보수적으로 반영한 EU 가격 12.5 USD/mmbtu를 사용한다."
        },
        {
          "Month-Year": "2027-05",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "영향 기간 종료 전 월로서 운송비 상승 압력이 계속 반영되는 슬롯이다. 별도 완화나 월별 조정 근거가 없어 EU 최종 입력값은 12.5 USD/mmbtu로 둔다."
        },
        {
          "Month-Year": "2027-06",
          "Region": "EU",
          "basecaseValue": null,
          "proposedValue": 12.5,
          "rationale": "2026-07부터 1년 적용 범위의 마지막 월로 해석된다. 구조적 규제 성격상 상승 압력이 유지되는 것으로 보고, 기준값 부재하에 EU 가격 12.5 USD/mmbtu를 최종 입력한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:08.403 | 8.403 | 2612 | 391 | 3003 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:18.238 | 18.238 | 5310 | 1870 | 7180 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:02.544 | 62.544 | 5905 | 3513 | 9418 |

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

- 소요시간: 01:34.841 (94.841s)
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
| Step2 selected slot | 3 | PASS |
| Step3 basecase 샘플 | prompt_records=24, limit=100 | PASS |
| Step3 value 결과 | value_cells=3, basecaseValue_present=3 | PASS |
| Step2 slot axis value 수 | `{"21|economicintensity|gdp|demand|gdppopulationadjustment": {"Year": 8}, "21|economicintensity|pmi|demand|pmiadjustment": {"Month": 12, "Year": 4}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 1 | 강도 차원의 '경미'는 산업 수요의 단기 심리·제조업 변동을 PMI 입력으로 반영할 수 있다는 parameter 의미와 연결된다. 기간 차원은 공통 시간 맥락상 1개월 이하의 짧은 영향으로 해석되므로, 수요 영향이 거의 흡수되고 가격 영향도 중립인 시나리오에 맞춰 단기 PMI는 기준 경로를 유지하는 구조로 제안한다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 2 | 강도 차원의 '경미'는 국가별 경기 경로가 LNG 수요의 거시 전제로 작용한다는 GDP parameter 의미와 연결된다. 다만 기간 차원이 1개월 이하이고 수요 영향이 제한적인 시나리오이므로, 연간 GDP 값은 급격한 충격값이 아니라 이벤트에 제시된 완만한 국가별 성장 전망을 반영하는 보수적 최종 경로로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 49.5 | 현재 기준월부터 1개월 이하의 단기 영향에 해당하는 2026년 7월 China 좌표를 사용했다. 해당 좌표의 기준 PMI가 49.5이고, 시나리오가 경미한 경기 영향과 수요 흡수를 전제로 하며 별도 PMI 수치가 제시되지 않았으므로 추가 하향 없이 최종 입력값을 49.5로 유지했다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.045 | 2026년 China 연간 GDP 좌표는 이벤트에서 직접 제시된 국가별 2026년 성장 전망과 일치하는 대상이다. 기준값은 0.042이나, OECD 전망에서 2026년 China 성장률이 4.5%로 제시되어 있어 같은 소수 비율 형식의 최종 입력값 0.045로 반영했다. |
| 2 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.02 | 2026년 United States 연간 GDP 좌표는 이벤트에서 직접 제시된 국가별 2026년 성장 전망과 일치하는 대상이다. 기준값은 0.019이고 OECD 전망에서 2026년 United States 성장률이 2.0%로 제시되어 있어 같은 소수 비율 형식의 최종 입력값 0.020으로 반영했다. |

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
  "model_param_proposal_id": 82,
  "proposal_completed_dtm": "2026-07-07 21:21:34.853162",
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
      "rationale": "강도 차원의 '경미'는 산업 수요의 단기 심리·제조업 변동을 PMI 입력으로 반영할 수 있다는 parameter 의미와 연결된다. 기간 차원은 공통 시간 맥락상 1개월 이하의 짧은 영향으로 해석되므로, 수요 영향이 거의 흡수되고 가격 영향도 중립인 시나리오에 맞춰 단기 PMI는 기준 경로를 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.5,
          "rationale": "현재 기준월부터 1개월 이하의 단기 영향에 해당하는 2026년 7월 China 좌표를 사용했다. 해당 좌표의 기준 PMI가 49.5이고, 시나리오가 경미한 경기 영향과 수요 흡수를 전제로 하며 별도 PMI 수치가 제시되지 않았으므로 추가 하향 없이 최종 입력값을 49.5로 유지했다."
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
      "rationale": "강도 차원의 '경미'는 국가별 경기 경로가 LNG 수요의 거시 전제로 작용한다는 GDP parameter 의미와 연결된다. 다만 기간 차원이 1개월 이하이고 수요 영향이 제한적인 시나리오이므로, 연간 GDP 값은 급격한 충격값이 아니라 이벤트에 제시된 완만한 국가별 성장 전망을 반영하는 보수적 최종 경로로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.045,
          "rationale": "2026년 China 연간 GDP 좌표는 이벤트에서 직접 제시된 국가별 2026년 성장 전망과 일치하는 대상이다. 기준값은 0.042이나, OECD 전망에서 2026년 China 성장률이 4.5%로 제시되어 있어 같은 소수 비율 형식의 최종 입력값 0.045로 반영했다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.02,
          "rationale": "2026년 United States 연간 GDP 좌표는 이벤트에서 직접 제시된 국가별 2026년 성장 전망과 일치하는 대상이다. 기준값은 0.019이고 OECD 전망에서 2026년 United States 성장률이 2.0%로 제시되어 있어 같은 소수 비율 형식의 최종 입력값 0.020으로 반영했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.282 | 3.282 | 2334 | 114 | 2448 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:32.713 | 32.713 | 5295 | 2054 | 7349 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:35.923 | 35.923 | 6260 | 2110 | 8370 |

#### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- 소요시간: 03:03.817 (183.817s)
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
| Step2 selected slot | 28 | PASS |
| Step3 basecase 샘플 | prompt_records=36, limit=100 | PASS |
| Step3 value 결과 | value_cells=28, basecaseValue_present=10 | PASS |
| Step2 slot axis value 수 | `{"21|economicintensity|gdp|demand|gdppopulationadjustment": {"Year": 8}, "21|economicintensity|pmi|demand|pmiadjustment": {"Month": 12, "Year": 4}}` | |

##### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Year", "Month", "Country"]` | `["PMI"]` | 24 | 강도 차원의 '경기 충격'은 산업 수요 단기 변동을 제조업 PMI로 직접 반영하는 설정과 연결된다. 기간 차원의 '1년'은 수치 강도 산정에는 직접 쓰지 않고, 현재 기준월 이후 1년 동안의 월별 적용 범위를 정하는 공통 시간 맥락으로 반영했다. 제안값은 경기 충격에 따른 수요 둔화를 반영해 대상 국가의 월별 PMI를 하향 조정하되, 기준값이 없는 월·국가는 같은 PMI 지수 형식과 보수적 충격 수준을 유지했다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Year", "Country"]` | `["% change (+/-)"]` | 4 | 강도 차원의 '경기 충격'은 국가별 실질 GDP 성장 경로를 조정하는 변수와 직접 연결된다. 기간 차원의 '1년'은 연간 GDP 값에 대해 현재 기준월 이후 충격이 두 개 연도에 걸쳐 반영되는 시간 범위를 정하는 공통 맥락으로 사용했다. 제안값은 경기 충격에 따른 수요 둔화를 반영해 대상 국가의 연간 성장률을 하향 조정하되, 충격이 하반기와 다음 해 상반기에 걸친다는 점을 감안해 연도별로 부분 반영했다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 47.0 | 해당 월의 기준 PMI 49.5는 이미 확장 기준선에 근접한 약한 상태이므로, 1년 경기 충격에 따른 산업 수요 둔화를 반영해 2.5포인트 낮춘 47.0을 최종 입력값으로 적용했다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 49.5 | 47.0 | 해당 월의 기준 PMI 49.5에 동일한 경기 충격 강도를 적용해, 제조업 수요 위축을 반영한 47.0으로 하향 조정했다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 49.5 | 47.0 | 해당 월의 기준 PMI 49.5에서 1년 충격 구간의 수요 약화를 반영해 47.0을 최종 입력값으로 산정했다. |
| 4 | `{"Country": "China", "Month": 10, "Year": 2026}` | 49.5 | 47.0 | 해당 월은 충격 지속 기간 안에 포함되므로 기준 PMI 49.5를 경기 충격 수준만큼 낮춰 47.0으로 적용했다. |
| 5 | `{"Country": "China", "Month": 11, "Year": 2026}` | 49.5 | 47.0 | 기준 PMI 49.5에 대해 1년 경기 충격의 제조업 수요 둔화 효과를 반영하여 47.0으로 하향 조정했다. |
| 6 | `{"Country": "China", "Month": 12, "Year": 2026}` | 49.5 | 47.0 | 해당 월의 기준 PMI 49.5를 현재 충격 강도에 맞춰 2.5포인트 낮추고, 최종 PMI 입력값을 47.0으로 제안했다. |
| 7 | `{"Country": "China", "Month": 1, "Year": 2027}` | null | 47.0 | 해당 월의 직접 기준값은 없으나 1년 충격 구간에 포함되며, 같은 국가의 2026년 월별 PMI 기준 수준과 동일한 지수 형식을 참고해 보수적 충격값 47.0을 적용했다. |
| 8 | `{"Country": "China", "Month": 2, "Year": 2027}` | null | 47.0 | 직접 기준값이 없는 월이지만 충격 지속 기간 안에 있어, 확인 가능한 PMI 기준 범위와 같은 스케일로 경기 충격을 반영한 47.0을 최종 입력값으로 사용했다. |
| 9 | `{"Country": "China", "Month": 3, "Year": 2027}` | null | 47.0 | 직접 기준값은 없지만 1년 수요 둔화 구간에 해당하므로, 기존 PMI 수준을 참고한 보수적 하향 충격값 47.0을 적용했다. |
| 10 | `{"Country": "China", "Month": 4, "Year": 2027}` | null | 47.0 | 해당 월은 충격 기간 내 후반부에 해당하며, 직접 기준값 부재로 같은 PMI 스케일을 참고해 경기 충격을 반영한 47.0을 제안했다. |
| 11 | `{"Country": "China", "Month": 5, "Year": 2027}` | null | 47.0 | 직접 기준값은 없으나 1년 충격의 월별 적용 범위에 포함되므로, 제조업 수요 위축을 반영한 보수적 PMI 값 47.0을 적용했다. |
| 12 | `{"Country": "China", "Month": 6, "Year": 2027}` | null | 47.0 | 1년 충격 구간의 마지막 월로 보고, 직접 기준값이 없는 점을 감안해 확인 가능한 PMI 기준 수준과 동일 형식의 하향값 47.0을 최종 입력값으로 산정했다. |
| 13 | `{"Country": "United States", "Month": 7, "Year": 2026}` | null | 47.0 | 직접 기준값은 없지만 대상 국가의 충격 시작 월에 해당하므로, 확인 가능한 PMI 기준 스케일을 참고해 경기 충격에 따른 제조업 위축값 47.0을 적용했다. |
| 14 | `{"Country": "United States", "Month": 8, "Year": 2026}` | null | 47.0 | 해당 월은 1년 충격 구간 안에 있으며 직접 기준값이 없어, 같은 PMI 지수 형식에서 보수적 경기 충격 수준인 47.0을 최종 입력값으로 사용했다. |
| 15 | `{"Country": "United States", "Month": 9, "Year": 2026}` | null | 47.0 | 직접 기준값 부재를 0으로 보지 않고, 확인 가능한 PMI 범위와 충격 강도를 참고해 제조업 수요 둔화값 47.0을 적용했다. |
| 16 | `{"Country": "United States", "Month": 10, "Year": 2026}` | null | 47.0 | 충격 지속 기간에 포함되는 월이므로, 직접 기준값이 없는 경우에도 동일 PMI 스케일상 경기 충격을 반영한 47.0을 제안했다. |
| 17 | `{"Country": "United States", "Month": 11, "Year": 2026}` | null | 47.0 | 해당 월은 경기 충격의 월별 반영 대상이며, 기준값 부재 구간에 대해 보수적 하향 PMI 값 47.0을 최종 입력값으로 산정했다. |
| 18 | `{"Country": "United States", "Month": 12, "Year": 2026}` | null | 47.0 | 직접 기준값은 없으나 연말까지 충격이 지속되는 구간이므로, 제조업 심리 위축을 반영한 PMI 47.0을 적용했다. |
| 19 | `{"Country": "United States", "Month": 1, "Year": 2027}` | null | 47.0 | 1년 충격이 다음 해 초까지 이어지는 구간으로 보고, 직접 기준값이 없는 상태에서 같은 지수 형식의 보수적 충격값 47.0을 사용했다. |
| 20 | `{"Country": "United States", "Month": 2, "Year": 2027}` | null | 47.0 | 해당 월은 충격 지속 구간에 포함되며, 직접 기준값 부재로 확인 가능한 PMI 스케일을 참고해 47.0을 최종 입력값으로 제안했다. |
| 21 | `{"Country": "United States", "Month": 3, "Year": 2027}` | null | 47.0 | 직접 기준값은 없지만 경기 충격에 따른 수요 약화가 계속되는 월로 판단해, 보수적 PMI 하향값 47.0을 적용했다. |
| 22 | `{"Country": "United States", "Month": 4, "Year": 2027}` | null | 47.0 | 충격 구간 후반부의 월별 입력값으로, 기준값이 없는 점을 감안해 같은 PMI 형식의 안정적인 충격 반영값 47.0을 사용했다. |
| 23 | `{"Country": "United States", "Month": 5, "Year": 2027}` | null | 47.0 | 해당 월은 1년 경기 충격의 적용 범위에 포함되므로, 직접 기준값 없이도 보수적 제조업 위축 수준인 PMI 47.0을 제안했다. |
| 24 | `{"Country": "United States", "Month": 6, "Year": 2027}` | null | 47.0 | 1년 충격 구간의 마지막 월로, 직접 기준값이 없는 경우에도 PMI 지수 스케일과 경기 충격 강도를 반영해 47.0을 최종 입력값으로 산정했다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.0385 | 해당 연도의 기준 GDP 성장률 0.042에서, 2026년 하반기에 해당하는 1년 충격의 부분 영향을 반영해 0.0035를 차감한 0.0385를 최종 입력값으로 산정했다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.0355 | 해당 연도의 기준 GDP 성장률 0.042에 대해, 충격이 2027년 상반기까지 이어지는 점과 하방 성장 위험이 더 크게 남는 점을 반영해 0.0065를 차감한 0.0355를 적용했다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.0155 | 해당 연도의 기준 GDP 성장률 0.019에서, 2026년 하반기 경기 충격에 따른 산업·에너지 수요 둔화 영향을 0.0035만큼 반영해 0.0155를 최종 입력값으로 제안했다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.0135 | 해당 연도의 기준 GDP 성장률 0.02에 대해, 1년 충격이 2027년 상반기까지 지속되는 영향과 성장 하방 위험을 반영해 0.0065를 차감한 0.0135를 적용했다. |

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
  "model_param_proposal_id": 85,
  "proposal_completed_dtm": "2026-07-07 21:24:06.218466",
  "proposal_parameters": [
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "PMIAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Month",
          "Country"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "PMI"
        ]
      },
      "parameterName": "PMI",
      "rationale": "강도 차원의 '경기 충격'은 산업 수요 단기 변동을 제조업 PMI로 직접 반영하는 설정과 연결된다. 기간 차원의 '1년'은 수치 강도 산정에는 직접 쓰지 않고, 현재 기준월 이후 1년 동안의 월별 적용 범위를 정하는 공통 시간 맥락으로 반영했다. 제안값은 경기 충격에 따른 수요 둔화를 반영해 대상 국가의 월별 PMI를 하향 조정하되, 기준값이 없는 월·국가는 같은 PMI 지수 형식과 보수적 충격 수준을 유지했다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월의 기준 PMI 49.5는 이미 확장 기준선에 근접한 약한 상태이므로, 1년 경기 충격에 따른 산업 수요 둔화를 반영해 2.5포인트 낮춘 47.0을 최종 입력값으로 적용했다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월의 기준 PMI 49.5에 동일한 경기 충격 강도를 적용해, 제조업 수요 위축을 반영한 47.0으로 하향 조정했다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월의 기준 PMI 49.5에서 1년 충격 구간의 수요 약화를 반영해 47.0을 최종 입력값으로 산정했다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 지속 기간 안에 포함되므로 기준 PMI 49.5를 경기 충격 수준만큼 낮춰 47.0으로 적용했다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "기준 PMI 49.5에 대해 1년 경기 충격의 제조업 수요 둔화 효과를 반영하여 47.0으로 하향 조정했다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.0,
          "rationale": "해당 월의 기준 PMI 49.5를 현재 충격 강도에 맞춰 2.5포인트 낮추고, 최종 PMI 입력값을 47.0으로 제안했다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월의 직접 기준값은 없으나 1년 충격 구간에 포함되며, 같은 국가의 2026년 월별 PMI 기준 수준과 동일한 지수 형식을 참고해 보수적 충격값 47.0을 적용했다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "직접 기준값이 없는 월이지만 충격 지속 기간 안에 있어, 확인 가능한 PMI 기준 범위와 같은 스케일로 경기 충격을 반영한 47.0을 최종 입력값으로 사용했다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "직접 기준값은 없지만 1년 수요 둔화 구간에 해당하므로, 기존 PMI 수준을 참고한 보수적 하향 충격값 47.0을 적용했다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 기간 내 후반부에 해당하며, 직접 기준값 부재로 같은 PMI 스케일을 참고해 경기 충격을 반영한 47.0을 제안했다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "직접 기준값은 없으나 1년 충격의 월별 적용 범위에 포함되므로, 제조업 수요 위축을 반영한 보수적 PMI 값 47.0을 적용했다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "1년 충격 구간의 마지막 월로 보고, 직접 기준값이 없는 점을 감안해 확인 가능한 PMI 기준 수준과 동일 형식의 하향값 47.0을 최종 입력값으로 산정했다."
        },
        {
          "Country": "United States",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "직접 기준값은 없지만 대상 국가의 충격 시작 월에 해당하므로, 확인 가능한 PMI 기준 스케일을 참고해 경기 충격에 따른 제조업 위축값 47.0을 적용했다."
        },
        {
          "Country": "United States",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 1년 충격 구간 안에 있으며 직접 기준값이 없어, 같은 PMI 지수 형식에서 보수적 경기 충격 수준인 47.0을 최종 입력값으로 사용했다."
        },
        {
          "Country": "United States",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "직접 기준값 부재를 0으로 보지 않고, 확인 가능한 PMI 범위와 충격 강도를 참고해 제조업 수요 둔화값 47.0을 적용했다."
        },
        {
          "Country": "United States",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "충격 지속 기간에 포함되는 월이므로, 직접 기준값이 없는 경우에도 동일 PMI 스케일상 경기 충격을 반영한 47.0을 제안했다."
        },
        {
          "Country": "United States",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 경기 충격의 월별 반영 대상이며, 기준값 부재 구간에 대해 보수적 하향 PMI 값 47.0을 최종 입력값으로 산정했다."
        },
        {
          "Country": "United States",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "직접 기준값은 없으나 연말까지 충격이 지속되는 구간이므로, 제조업 심리 위축을 반영한 PMI 47.0을 적용했다."
        },
        {
          "Country": "United States",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "1년 충격이 다음 해 초까지 이어지는 구간으로 보고, 직접 기준값이 없는 상태에서 같은 지수 형식의 보수적 충격값 47.0을 사용했다."
        },
        {
          "Country": "United States",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 충격 지속 구간에 포함되며, 직접 기준값 부재로 확인 가능한 PMI 스케일을 참고해 47.0을 최종 입력값으로 제안했다."
        },
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "직접 기준값은 없지만 경기 충격에 따른 수요 약화가 계속되는 월로 판단해, 보수적 PMI 하향값 47.0을 적용했다."
        },
        {
          "Country": "United States",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "충격 구간 후반부의 월별 입력값으로, 기준값이 없는 점을 감안해 같은 PMI 형식의 안정적인 충격 반영값 47.0을 사용했다."
        },
        {
          "Country": "United States",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "해당 월은 1년 경기 충격의 적용 범위에 포함되므로, 직접 기준값 없이도 보수적 제조업 위축 수준인 PMI 47.0을 제안했다."
        },
        {
          "Country": "United States",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.0,
          "rationale": "1년 충격 구간의 마지막 월로, 직접 기준값이 없는 경우에도 PMI 지수 스케일과 경기 충격 강도를 반영해 47.0을 최종 입력값으로 산정했다."
        }
      ]
    },
    {
      "modelTarget": {
        "modelFile": "Demand",
        "modelSheet": "GDPPopulationAdjustment",
        "slotAxesFieldNames": [
          "Year",
          "Country"
        ],
        "tableName": "table1",
        "valueFieldNames": [
          "% change (+/-)"
        ]
      },
      "parameterName": "GDP",
      "rationale": "강도 차원의 '경기 충격'은 국가별 실질 GDP 성장 경로를 조정하는 변수와 직접 연결된다. 기간 차원의 '1년'은 연간 GDP 값에 대해 현재 기준월 이후 충격이 두 개 연도에 걸쳐 반영되는 시간 범위를 정하는 공통 맥락으로 사용했다. 제안값은 경기 충격에 따른 수요 둔화를 반영해 대상 국가의 연간 성장률을 하향 조정하되, 충격이 하반기와 다음 해 상반기에 걸친다는 점을 감안해 연도별로 부분 반영했다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.0385,
          "rationale": "해당 연도의 기준 GDP 성장률 0.042에서, 2026년 하반기에 해당하는 1년 충격의 부분 영향을 반영해 0.0035를 차감한 0.0385를 최종 입력값으로 산정했다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.0355,
          "rationale": "해당 연도의 기준 GDP 성장률 0.042에 대해, 충격이 2027년 상반기까지 이어지는 점과 하방 성장 위험이 더 크게 남는 점을 반영해 0.0065를 차감한 0.0355를 적용했다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.0155,
          "rationale": "해당 연도의 기준 GDP 성장률 0.019에서, 2026년 하반기 경기 충격에 따른 산업·에너지 수요 둔화 영향을 0.0035만큼 반영해 0.0155를 최종 입력값으로 제안했다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.0135,
          "rationale": "해당 연도의 기준 GDP 성장률 0.02에 대해, 1년 충격이 2027년 상반기까지 지속되는 영향과 성장 하방 위험을 반영해 0.0065를 차감한 0.0135를 적용했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.123 | 4.123 | 2347 | 70 | 2417 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:49.239 | 49.239 | 5304 | 3758 | 9062 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:54.007 | 114.007 | 7569 | 5543 | 13112 |

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"16": true, "18": true, "22": true, "44": true, "45": true, "47": true, "48": true, "49": true, "50": true, "51": true, "52": true, "53": true, "54": true, "60": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.

## 파라미터 기준 결과 요약

- 대상 범위: 현재 로컬 `midb` 기준 5개 파라미터(`GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment`)가 매핑된 event type별 scenario group 1개, group별 scenario 2개.
- 실행 규모: 14개 scenario group, 28개 scenario, proposal_id `58`-`85`.
- 실행 결과: `ERROR_COUNT=0`, `EMPTY_RECOMMENDATIONS=0`.
- 값 생성 결과: 5개 대상 파라미터 모두 Step3 `value_grid`가 생성됨. 이번 실행에서 대상 파라미터의 empty value로 인한 누락은 확인되지 않음.

| Parameter | 관련 event type | scenario_count | value_count | basecaseValue=null | 주요 결과 | 주요 검토 포인트 |
|---|---:|---:|---:|---:|---|---|
| GDP | 21 | 2 | 6 | 0 | 국가별 경기 scenario 305/306에서 모두 선정 및 값 생성 | 305의 경미한 둔화 scenario에서 China/US GDP가 basecase보다 소폭 상향된 점은 event 전망 반영인지, scenario 둔화 반영인지 검토 필요 |
| PMI | 21 | 2 | 25 | 18 | 305는 basecase 유지, 306은 1년 충격에 대해 월별 PMI 47.0 생성 | basecase 없는 US/2027 월까지 모두 47.0으로 단일값 적용됨. 국가/월 차등화 기준 보강 필요 |
| PowerMix | 5,6,7,8,9,10,18 | 14 | 49 | 4 | basecase 없는 US slot도 0이 아닌 0.3/0.397/0.42/0.45로 생성 | event type 19 routing에서는 PowerMix 대신 Gas Futures Price가 선택됨. PowerMix 자체가 필요하면 mapping comment 강화 필요 |
| Temperature | 6,7 | 4 | 12 | 10 | 한파/폭염 모두 value 생성 | 한파 290에서 7-9월에 `-5`를 제안해 계절 slot 해석 오류 가능성이 큼 |
| LiqUtilAdjustment | 1,2,4,11,17,18 | 12 | 196 | 8 | 모든 관련 event type에서 값 생성 | 일부 proposed/basecase가 1.0 초과. parameter hint의 0-1 ratio와 실제 basecase 범위가 충돌 |

### GDP

#### 실행 결과

| proposal_id | scenario_id | event type | scenario | value_count | basecase null | 대표 value |
|---:|---:|---|---|---:|---:|---|
| 82 | 305 | 21 국가별 경기 | [model_parameter_agent_test] 경미한 경기 둔화와 수요 영향 제한 | 2 | 0 | China 2026: 0.042 -> 0.045, United States 2026: 0.019 -> 0.020 |
| 85 | 306 | 21 국가별 경기 | [model_parameter_agent_test] 1년 경기 충격과 수요 감소 | 4 | 0 | China 2026: 0.042 -> 0.0385, China 2027: 0.042 -> 0.0355, US 2026: 0.019 -> 0.0155 |

#### Parameter Quality Evaluation

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나. direct는 필수선정, route는 반드시 1개 이상 선정 | PASS | event type 21의 `economic_intensity` direct mapping에서 GDP가 scenario 305/306 모두 선정됨 | 없음 |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | PASS | Country/Year 축으로 China, United States, 2026/2027이 선택됨. GDP model target 축과 일치 | 경기 event의 영향 국가 선정 기준을 mapping comment에 명시하면 더 안정적 |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가 | PASS | 6개 value 모두 basecaseValue 존재 | 없음 |
| 4 | slot이 basecase에 없지만 시나리오/이벤트 정보를 활용해 추가 선정된 경우 개연성이 있는가 | N/A | GDP는 이번 실행에서 basecase 없는 slot 없음 | 없음 |
| 5 | slot이 basecase에 없는 경우를 선정하지 못했다면 선정해도 될 가능성이 없었는가 | N/A | 해당 없음 | 없음 |
| 6 | value 형식과 추천 개연성이 적절한가 | REVIEW | 값은 0.045, 0.0385 등 basecase와 같은 decimal growth-rate 형식. 다만 305는 scenario title이 경미한 경기 둔화인데 GDP가 basecase보다 상향됨 | `economic_intensity=경미`일 때 event 전망을 우선할지, scenario 둔화 방향을 우선할지 mapping comment에 우선순위 명시 |
| 7 | value가 basecase에 있는 경우 적절하게 변경되었나 | REVIEW | 306은 경기 충격에 따라 GDP를 하향해 개연적. 305는 OECD 전망 반영으로 상향되어 scenario 둔화 문맥과 충돌 가능 | `경미한 둔화`는 basecase 유지 또는 소폭 하향, `전망 상향`은 상향 허용처럼 dimension label별 정책 필요 |
| 8 | value가 basecase에 없었던 경우 개연성 있게 선정되었나 | N/A | 해당 없음 | 없음 |
| 9 | 동일 그룹 scenario 사이 dimension value에 따라 value 차이가 적절한가 | PASS | 305는 0.045/0.020, 306은 0.0385/0.0155 등 강한 충격 scenario가 낮은 값 | 없음 |

### PMI

#### 실행 결과

| proposal_id | scenario_id | event type | scenario | value_count | basecase null | 대표 value |
|---:|---:|---|---|---:|---:|---|
| 82 | 305 | 21 국가별 경기 | [model_parameter_agent_test] 경미한 경기 둔화와 수요 영향 제한 | 1 | 0 | China 2026-07: 49.5 -> 49.5 |
| 85 | 306 | 21 국가별 경기 | [model_parameter_agent_test] 1년 경기 충격과 수요 감소 | 24 | 18 | China 2026-07: 49.5 -> 47.0, basecase 없는 US/2027 월도 47.0 |

#### Parameter Quality Evaluation

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | event type 21의 PMI direct mapping에서 scenario 305/306 모두 선정 | 없음 |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | REVIEW | 305는 China 2026-07 1개월, 306은 China/US 2026-07부터 2027-06까지 1년 월별 slot 선정 | 1년 period의 시작월 기준과 대상국 확장 기준을 prompt 또는 mapping comment에 명시 |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가 | PASS | China 2026 월별 basecase 49.5를 기반으로 값 생성 | 없음 |
| 4 | basecase에 없지만 시나리오/이벤트 정보를 활용해 추가 선정된 slot의 개연성 | REVIEW | US 및 2027 월은 basecaseValue null이나 경기 충격 기간 확장으로 선정됨 | basecase 없는 국가/월은 같은 국가 최근 월, 같은 권역, global default 순서로 fallback 기준 명시 |
| 5 | basecase에 없는 경우를 선정하지 못했다면 선정 가능성이 없었는가 | N/A | basecase 없는 월/국가도 선정됨 | 없음 |
| 6 | value 형식과 추천 개연성이 적절한가 | PASS | PMI index 형식으로 49.5 유지 또는 47.0 하향 제안 | 없음 |
| 7 | basecase가 있는 value 변경이 적절한가 | PASS | 305는 중립/경미 영향으로 49.5 유지, 306은 경기 충격으로 47.0 하향 | 없음 |
| 8 | basecase가 없는 value 선정이 개연성 있는가 | REVIEW | basecase 없는 US/2027 월까지 모두 47.0으로 통일. 0이 아닌 동일 형식 값 생성은 개선됐지만 차등 근거는 약함 | 국가별 PMI fallback 범위와 월별 회복/악화 profile을 hint에 추가 |
| 9 | 동일 그룹 scenario 사이 dimension value 차이가 적절한가 | PASS | 305는 49.5 유지, 306은 47.0 하향으로 강한 경기 충격이 더 낮음 | 없음 |

### PowerMix

#### 실행 결과

| event type | scenarios | value_count | basecase null | 대표 value |
|---|---:|---:|---:|---|
| 5 발전소 Utilization 변동 | 287, 288 | 2 | 2 | US/Gas/2026: 0.3, 0.397 |
| 6 겨울 한파 | 289, 290 | 2 | 2 | US/Gas/2026: 0.42, 0.45 |
| 7 여름 폭염 | 291, 292 | 4 | 0 | China/Gas/2026: 0.0346 유지 -> 0.0363, Japan/Gas/2026: 0.323 유지 -> 0.3392 |
| 8 원자력 발전 | 293, 294 | 2 | 0 | South Korea/Gas/2026: 0.285 유지 -> 0.300 |
| 9 재생에너지 | 261, 262 | 14 | 0 | Europe Gas share 유지 또는 소폭 상향 |
| 10 석탄 발전 | 267, 268 | 2 | 0 | Japan/Gas/2026: 0.323 유지 -> 0.327 |
| 18 경제 제재 및 무역 제한 | 129, 130 | 23 | 0 | China/Gas/2026: 0.0346 -> 0.0345, multi-country Gas share 하향 |

#### Parameter Quality Evaluation

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | REVIEW | direct mapping event type 5/6/7/8/9/10/18에서는 선정. event type 19 routing 후보에서는 Gas Futures Price가 선택되어 PowerMix 미선정 | 정책/규제 event에서 PowerMix가 필요한 케이스의 mapping comment를 `전원믹스/발전설비/연료전환` 등 더 강하게 작성 |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | PASS | Country/Year/Energy Source 축이 모델 축과 일치. US basecase가 없는 경우도 명시 좌표로 생성 | US처럼 basecase 없는 국가는 fallback 국가군 선택 기준 보강 |
| 3 | basecase 기반 slot 선정 개연성 | PASS | China, Japan, South Korea, Europe slot은 basecase record와 일치 | 없음 |
| 4 | basecase 없는 slot 추가 선정 개연성 | PASS | event/scenario가 US를 직접 가리키는 event type 5/6에서 US/Gas/2026 생성 | 없음 |
| 5 | basecase 없는 경우를 선정하지 못했다면 가능성이 없었는가 | N/A | basecase 없는 US slot도 선정됨 | 없음 |
| 6 | value 형식과 추천 개연성이 적절한가 | PASS | 0-1 share decimal 형식으로 생성. basecase 없음도 0이 아닌 범위 참고값 0.3/0.397/0.42/0.45 생성 | PowerMix hint에 `share fraction 0-1, no-change는 0이 아니라 기준/fallback 유지`를 DB에도 반영 권장 |
| 7 | basecase가 있는 value 변경이 적절한가 | PASS | 약한/흡수 scenario는 유지, 강한/흡수 부족 scenario는 상향 또는 정책 대응 scenario는 하향 | 없음 |
| 8 | basecase 없는 value 선정이 개연성 있는가 | REVIEW | US/Gas fallback이 0.3-0.45 범위로 생성되어 0 문제는 해소. 다만 US의 실제 gas share fallback 근거는 다른 국가 범위에 의존 | `basecase 없는 국가 fallback`: 같은 권역, 유사 발전 mix 국가, 외부 통계 default 순서 명시 |
| 9 | 동일 그룹 scenario 사이 dimension value 차이가 적절한가 | PASS | 287 0.3 vs 288 0.397, 289 0.42 vs 290 0.45, 291 유지 vs 292 상향 등 강한 scenario가 더 큰 변화 | 없음 |

### Temperature

#### 실행 결과

| proposal_id | scenario_id | event type | scenario | value_count | basecase null | 대표 value |
|---:|---:|---|---|---:|---:|---|
| 65 | 289 | 6 겨울 한파 | 짧은 약한 한파와 전원 흡수 | 1 | 1 | United States 2026-03: null -> 3.0 |
| 67 | 290 | 6 겨울 한파 | 3개월 강한 한파와 대체 제한 | 3 | 3 | United States 2026-07/08/09: null -> -5 |
| 68 | 291 | 7 여름 폭염 | 짧은 약한 폭염과 전원 흡수 | 2 | 0 | China 2026-07: 10.4 -> 11.4, Japan 2026-07: 9.2 -> 10.2 |
| 69 | 292 | 7 여름 폭염 | 3개월 강한 폭염과 전원 흡수 부족 | 6 | 6 | China/Japan 2026-07/08/09: null -> 13.4 등 |

#### Parameter Quality Evaluation

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | event type 6/7의 cold_wave_intensity/heatwave_intensity direct mapping에서 모두 선정 | 없음 |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | FAIL | scenario 290은 겨울 한파인데 2026-07/08/09에 -5를 제안. 계절과 월 해석이 충돌 | 한파 event type은 겨울 월 또는 event occurred_at/시나리오 명시월 우선 규칙 추가. 현재 기준월부터 3개월로 단순 전개 금지 |
| 3 | basecase 기반 slot 선정 개연성 | REVIEW | 291은 China/Japan 2026-07 basecase를 사용했으나 basecase 자체가 10.4/9.2로 실제 여름 절대기온처럼 보이지 않음 | Temperature basecase가 절대기온인지 anomaly인지 DB hint와 value_field에 명확히 정리 |
| 4 | basecase 없는 slot 추가 선정 개연성 | REVIEW | 289/290/292에서 basecase 없는 slot도 value 생성. 292의 여름 7-9월은 개연성 있으나 290의 한파 7-9월은 부적절 | 계절 이벤트별 month resolution policy 추가 |
| 5 | basecase 없는 경우를 선정하지 못했다면 가능성이 없었는가 | N/A | basecase 없는 slot도 선정됨 | 없음 |
| 6 | value 형식과 추천 개연성이 적절한가 | REVIEW | 숫자 °C 형식은 유지. 그러나 2026-07/08/09 US 한파 -5는 월/계절상 부적절 | Temperature proposed_value가 절대기온인지 편차인지 확정하고, 강도 dimension은 basecase 대비 delta로 적용하도록 DB hint 강화 |
| 7 | basecase가 있는 value 변경이 적절한가 | REVIEW | 291에서 +1℃ 하향/상향은 형식상 가능하지만 basecase 값이 여름 절대기온으로 낮아 해석 불안 | WeatherAdjustment basecase 열 의미 검증 필요 |
| 8 | basecase 없는 value 선정이 개연성 있는가 | REVIEW | 292는 여름 강한 폭염에 13.4 등으로 생성됐지만 절대기온으로는 낮고 anomaly로는 높음 | fallback 절대기온/편차 기준을 분리 |
| 9 | 동일 그룹 scenario 사이 dimension value 차이가 적절한가 | REVIEW | 약한 폭염 291보다 강한 폭염 292가 더 높은 값이지만, 한파 289/290은 월 해석 문제로 비교 신뢰도 낮음 | month policy 보완 후 재평가 |

### LiqUtilAdjustment

#### 실행 결과

| event type | scenarios | value_count | basecase null | 대표 value |
|---|---:|---:|---:|---|
| 1 Upstream Utilization 변동 | 283, 284 | 15 | 0 | Algeria trains basecase +0.05~+0.10 |
| 2 터미널 Utilization 변동 | 105, 106 | 12 | 0 | Cameron LNG: 0.897 -> 0.870, 0.897 -> 1.0 |
| 4 파이프라인 Utilization 변동 | 285, 286 | 20 | 8 | Calcasieu/Sabine Pass LNG utilization fallback or capped at 1.0 |
| 11 자연재해 | 279, 280 | 57 | 0 | Qatar/Australia trains adjusted |
| 17 지정학적 긴장 및 전쟁·군사분쟁 | 92, 93 | 77 | 0 | QatarGas trains 유지 또는 하향 |
| 18 경제 제재 및 무역 제한 | 129, 130 | 15 | 0 | Arctic LNG 2 monthly utilization 하향 |

#### Parameter Quality Evaluation

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나 | PASS | 6개 관련 event type에서 LiqUtilAdjustment가 모두 선정됨 | 없음 |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가 | REVIEW | scenario 280은 LiqUtilAdjustment 54개, scenario 93은 60개 value로 slot fanout이 큼 | 영향 시설/대체 공급국 선택 수 상한과 대표 train 선정 규칙 필요 |
| 3 | basecase 기반 slot 선정 개연성 | PASS | 대부분 Country/Plant/Train/Year/Month/Period basecase와 일치 | 없음 |
| 4 | basecase 없는 slot 추가 선정 개연성 | REVIEW | scenario 285의 8개 Calcasieu Pass slot은 basecase null 상태에서 fallback value 0.9282 생성 | basecase 없는 train fallback 기준을 같은 plant/train family, same country, same lifecycle 순서로 명시 |
| 5 | basecase 없는 경우를 선정하지 못했다면 가능성이 없었는가 | N/A | basecase 없는 slot도 선정됨 | 없음 |
| 6 | value 형식과 추천 개연성이 적절한가 | FAIL | parameter_hint는 0-1 ratio이나 일부 basecase/proposed가 1.0 초과. 예: 279 QatarGas T1 1.0477 -> 1.0977 | 실제 모델이 1 초과 utilization을 허용하는지 확인. 허용하지 않으면 sanitizer나 prompt에서 0-1 clamp. 허용하면 DB hint를 `ratio, may exceed 1 for model baseline`로 수정 |
| 7 | basecase가 있는 value 변경이 적절한가 | REVIEW | 많은 케이스에서 방향성은 맞지만 1.0 초과 상향, 54/60개 일괄 조정은 과대 가능 | 충격 강도별 max delta, cap, slot count limit 필요 |
| 8 | basecase 없는 value 선정이 개연성 있는가 | REVIEW | 285의 null basecase 8개가 0.9282로 생성되어 0 문제는 없지만 근거는 약함 | fallback hierarchy를 parameter_hint에 추가 |
| 9 | 동일 그룹 scenario 사이 dimension value 차이가 적절한가 | PASS | 105 미세 감산은 0.870, 106 완전 증산은 1.0, 92 유지 vs 93 하향 등 dimension 강도 차이가 반영됨 | 없음 |

## 파라미터 기준 개선 사항

1. `Temperature`의 month resolution을 보완해야 한다. 한파/폭염처럼 계절성이 강한 event type은 현재 기준월부터 period를 펼치는 방식보다 event 발생월, 시나리오 narrative의 계절, dimension label을 우선해야 한다.
2. `Temperature.parameter_hint`에 `Temperature (°C)`가 절대기온인지 anomaly인지 명시해야 한다. 현재 결과는 절대기온과 편차 해석이 섞일 여지가 있다.
3. `LiqUtilAdjustment.parameter_hint`의 `0-1` 제약과 실제 basecase의 1 초과 값이 충돌한다. 모델이 1 초과를 허용하는지 확인 후 hint 또는 sanitizer를 맞춰야 한다.
4. `LiqUtilAdjustment`는 slot fanout이 큰 케이스가 있어, event type별 max slot 수와 대표 train 선택 기준을 mapping comment에 추가하는 것이 좋다.
5. `PowerMix`는 basecase 없는 slot에서 0이 아닌 fallback share를 생성하도록 개선됐지만, 국가별 fallback 기준은 아직 넓다. 같은 권역/유사 전원믹스/대표 국가 순서를 hint에 추가하면 안정성이 높다.
6. `GDP/PMI`는 경기 강도별 방향성은 대체로 반영됐지만, `경미한 둔화`에서 GDP 상향처럼 event 전망과 scenario dimension 방향이 충돌할 때의 우선순위를 mapping comment에 명시해야 한다.
