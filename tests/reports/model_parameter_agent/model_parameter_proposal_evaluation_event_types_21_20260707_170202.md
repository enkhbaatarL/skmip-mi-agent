# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-07T17:02:02
- 실행 종료: 2026-07-07T17:04:48
- 총 소요시간: 02:46.156 (166.156s)
- 대상 event_type_l2_ids: [21]
- concurrency: 2
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=21 국가별 경기: scenario_group 1개, scenario 2개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 21 | 60 | 305 | OK | 1 | 01:28.503 | 88.503s |
| 21 | 60 | 306 | OK | 1 | 02:39.284 | 159.284s |

## 호출 결과

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
      "scenario_dimension_value": "100%",
      "selected_in_scenario": true
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
      "scenario_dimension_value": "경미",
      "selected_in_scenario": true
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
      "scenario_dimension_value": "경미",
      "selected_in_scenario": true
    },
    {
      "canonical_parameter_name": null,
      "comment": "시간축",
      "dimension_key": "period",
      "dimension_label": "기간",
      "mapping_method": "indirect",
      "model_target": null,
      "prompt_usage_policy": "supporting_context_only_when_allowed",
      "scenario_dimension_value": "1개월 이하",
      "selected_in_scenario": true
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

- 소요시간: 01:28.503 (88.503s)
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
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 1 | 강도 차원의 '경미'는 단기 산업 수요 심리 변동을 PMI로 반영할 수 있다는 parameter 의미와 직접 연결됩니다. 기간 차원의 '1개월 이하'는 공통 시간축 힌트로 보아, 장기 GDP 경로보다는 해당 월의 PMI 입력에 한정하며, LNG 수요 영향이 거의 흡수되는 중립적 시나리오이므로 기존 PMI 수준을 유지하는 보수적 입력값을 제안합니다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 2 | 강도 차원의 '경미'는 국가별 경기 전제의 제한적 조정을 GDP 입력으로 반영할 수 있다는 parameter 의미와 연결됩니다. 다만 기간 차원이 '1개월 이하'이므로 구조적 충격으로 확대하지 않고, 이벤트에 명시된 2026년 국가별 성장 전망을 기준으로 연간 GDP 변화율을 소폭 보정하는 구조로 제안합니다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 49.5 | 해당 좌표는 선택된 2026년 7월 중국 PMI 입력 record와 일치한다. 기준값 49.5에 대해 시나리오가 1개월 이하의 경미한 경기 영향이고 가격 영향도 중립으로 제시되어 추가 하향 조정 없이 최종 입력값을 49.5로 유지한다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.045 | 해당 좌표는 선택된 2026년 중국 GDP 입력 record와 일치한다. 기준값 0.042에 대해 이벤트에서 제시된 중국 2026년 성장률 4.5%를 같은 형식의 최종 입력값으로 반영하여 0.045로 산정한다. |
| 2 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.02 | 해당 좌표는 선택된 2026년 미국 GDP 입력 record와 일치한다. 기준값 0.019에 대해 이벤트에서 제시된 미국 2026년 성장률 2.0%를 같은 형식의 최종 입력값으로 반영하여 0.02로 산정한다. |

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
  "model_param_proposal_id": 29,
  "proposal_completed_dtm": "2026-07-07 17:03:30.614367",
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
      "rationale": "강도 차원의 '경미'는 단기 산업 수요 심리 변동을 PMI로 반영할 수 있다는 parameter 의미와 직접 연결됩니다. 기간 차원의 '1개월 이하'는 공통 시간축 힌트로 보아, 장기 GDP 경로보다는 해당 월의 PMI 입력에 한정하며, LNG 수요 영향이 거의 흡수되는 중립적 시나리오이므로 기존 PMI 수준을 유지하는 보수적 입력값을 제안합니다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.5,
          "rationale": "해당 좌표는 선택된 2026년 7월 중국 PMI 입력 record와 일치한다. 기준값 49.5에 대해 시나리오가 1개월 이하의 경미한 경기 영향이고 가격 영향도 중립으로 제시되어 추가 하향 조정 없이 최종 입력값을 49.5로 유지한다."
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
      "rationale": "강도 차원의 '경미'는 국가별 경기 전제의 제한적 조정을 GDP 입력으로 반영할 수 있다는 parameter 의미와 연결됩니다. 다만 기간 차원이 '1개월 이하'이므로 구조적 충격으로 확대하지 않고, 이벤트에 명시된 2026년 국가별 성장 전망을 기준으로 연간 GDP 변화율을 소폭 보정하는 구조로 제안합니다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.045,
          "rationale": "해당 좌표는 선택된 2026년 중국 GDP 입력 record와 일치한다. 기준값 0.042에 대해 이벤트에서 제시된 중국 2026년 성장률 4.5%를 같은 형식의 최종 입력값으로 반영하여 0.045로 산정한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.02,
          "rationale": "해당 좌표는 선택된 2026년 미국 GDP 입력 record와 일치한다. 기준값 0.019에 대해 이벤트에서 제시된 미국 2026년 성장률 2.0%를 같은 형식의 최종 입력값으로 반영하여 0.02로 산정한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:05.016 | 5.016 | 2334 | 70 | 2404 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:21.934 | 21.934 | 5295 | 1220 | 6515 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:28.624 | 28.624 | 6138 | 1652 | 7790 |

#### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- 소요시간: 02:39.284 (159.284s)
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
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Year", "Month", "Country"]` | `["PMI"]` | 24 | 강도 차원의 '경기 충격'은 mapping_comment상 산업 수요의 단기 변동을 PMI로 반영하는 직접 요인입니다. 기간 차원의 '1년'은 공통 시간 맥락으로 사용해 월별 PMI 조정이 1년 구간에 걸쳐 지속되는 구조로 반영했습니다. 제안값은 제조업 심리 위축을 나타내도록 중립선 아래의 PMI 최종 지수로 하향 적용하되, 기준값이 있는 구간은 기준 PMI에서 보수적인 충격 폭을 차감하고 기준값이 없는 구간은 같은 형식의 월별 PMI 지수로 산정했습니다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Year", "Country"]` | `["% change (+/-)"]` | 4 | 강도 차원의 '경기 충격'은 mapping_comment상 국가별 GDP 경로를 조정해야 하는 구조적 경기 변수와 직접 연결됩니다. 기간 차원의 '1년'은 공통 시간 맥락으로 사용해 현재 기준 시점 이후 1년 충격이 연간 GDP 입력에 부분 반영되는 구조로 적용했습니다. 제안값은 OECD 하방 시나리오의 성장 둔화 방향과 시나리오의 수요 감소 서사를 반영해 연간 실질 GDP 변화율을 기준값보다 낮은 최종 입력값으로 산정했습니다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 47.5 | 해당 좌표는 1년 경기 충격이 시작되는 월별 PMI 입력 구간이며, 기준 PMI 49.5에서 경기 충격에 따른 제조업 위축 폭 2.0pt를 차감해 최종 PMI 지수 47.5로 산정했습니다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 49.5 | 47.5 | 해당 좌표는 1년 충격이 지속되는 월별 PMI 입력 구간이며, 기준 PMI 49.5에 동일한 제조업 위축 폭 2.0pt를 적용해 최종 PMI 지수 47.5로 산정했습니다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 49.5 | 47.5 | 해당 좌표는 경기 충격 지속 구간의 월별 PMI record이며, 기준 PMI 49.5에서 2.0pt 하향 조정을 반영해 최종 PMI 지수 47.5로 산정했습니다. |
| 4 | `{"Country": "China", "Month": 10, "Year": 2026}` | 49.5 | 47.5 | 해당 좌표는 충격 기간 내 월별 PMI 입력 구간이며, 기준 PMI 49.5를 경기 충격 수준에 맞춰 2.0pt 낮춰 최종 PMI 지수 47.5로 산정했습니다. |
| 5 | `{"Country": "China", "Month": 11, "Year": 2026}` | 49.5 | 47.5 | 해당 좌표는 1년 경기 충격이 이어지는 월별 PMI 구간이며, 기준 PMI 49.5에서 제조업 수요 둔화 폭 2.0pt를 반영해 최종 PMI 지수 47.5로 산정했습니다. |
| 6 | `{"Country": "China", "Month": 12, "Year": 2026}` | 49.5 | 47.5 | 해당 좌표는 연말까지 지속되는 경기 충격 구간의 PMI record이며, 기준 PMI 49.5에 2.0pt 하향 충격을 적용해 최종 PMI 지수 47.5로 산정했습니다. |
| 7 | `{"Country": "China", "Month": 1, "Year": 2027}` | null | 47.5 | 해당 좌표는 1년 충격의 후반부에 해당하는 월별 PMI 입력 구간입니다. 일치하는 기준 record는 제공되지 않았으나, 같은 충격 구간의 연속 월로 보아 최종 PMI 지수를 기준 구간과 동일한 위축 수준인 47.5로 산정했습니다. |
| 8 | `{"Country": "China", "Month": 2, "Year": 2027}` | null | 47.5 | 해당 좌표는 경기 충격 후반부의 월별 PMI 입력 구간입니다. 일치 기준값이 없으므로 별도 회복을 가정하지 않고, 1년 지속 충격에 맞춰 최종 PMI 지수 47.5를 적용했습니다. |
| 9 | `{"Country": "China", "Month": 3, "Year": 2027}` | null | 47.5 | 해당 좌표는 1년 경기 충격이 유지되는 월별 PMI 구간입니다. 제공된 기준 record가 없어도 기간 내 충격 강도를 동일하게 유지해 최종 PMI 지수 47.5로 산정했습니다. |
| 10 | `{"Country": "China", "Month": 4, "Year": 2027}` | null | 47.5 | 해당 좌표는 충격 기간 내 후반 월별 PMI 입력 구간입니다. 명확한 회복 근거가 없으므로 제조업 위축 상태가 유지되는 최종 PMI 지수 47.5를 적용했습니다. |
| 11 | `{"Country": "China", "Month": 5, "Year": 2027}` | null | 47.5 | 해당 좌표는 1년 경기 충격이 지속되는 월별 PMI 구간입니다. 일치 기준값은 없지만 같은 시나리오 충격 범위에 포함되므로 최종 PMI 지수 47.5로 산정했습니다. |
| 12 | `{"Country": "China", "Month": 6, "Year": 2027}` | null | 47.5 | 해당 좌표는 1년 충격 구간의 마지막 월별 PMI 입력 구간입니다. 회복 전환을 별도로 두지 않고 충격 지속 조건에 맞춰 최종 PMI 지수 47.5를 적용했습니다. |
| 13 | `{"Country": "United States", "Month": 7, "Year": 2026}` | null | 47.5 | 해당 좌표는 1년 경기 충격이 시작되는 월별 PMI 입력 구간입니다. 일치 기준 record는 제공되지 않았으나, 단기 산업 수요 위축을 반영할 수 있도록 최종 PMI 지수를 중립선 아래의 47.5로 산정했습니다. |
| 14 | `{"Country": "United States", "Month": 8, "Year": 2026}` | null | 47.5 | 해당 좌표는 경기 충격 지속 구간의 월별 PMI 입력 구간입니다. 기준값이 제공되지 않아도 동일한 1년 충격 강도를 유지해 최종 PMI 지수 47.5를 적용했습니다. |
| 15 | `{"Country": "United States", "Month": 9, "Year": 2026}` | null | 47.5 | 해당 좌표는 충격 기간 중 월별 PMI 입력 구간입니다. 제조업 심리와 산업 수요 둔화가 지속되는 전제로 최종 PMI 지수 47.5로 산정했습니다. |
| 16 | `{"Country": "United States", "Month": 10, "Year": 2026}` | null | 47.5 | 해당 좌표는 1년 경기 충격 내 월별 PMI 구간입니다. 일치 기준 record가 없어도 동일한 충격 구간의 입력값으로 중립선 아래 PMI 47.5를 적용했습니다. |
| 17 | `{"Country": "United States", "Month": 11, "Year": 2026}` | null | 47.5 | 해당 좌표는 경기 충격이 이어지는 월별 PMI 입력 구간입니다. 별도 완화 근거가 없으므로 최종 PMI 지수 47.5를 유지했습니다. |
| 18 | `{"Country": "United States", "Month": 12, "Year": 2026}` | null | 47.5 | 해당 좌표는 연말까지 지속되는 충격 구간의 월별 PMI 입력입니다. 산업 수요 위축을 반영해 최종 PMI 지수 47.5로 산정했습니다. |
| 19 | `{"Country": "United States", "Month": 1, "Year": 2027}` | null | 47.5 | 해당 좌표는 1년 경기 충격의 후반부 월별 PMI 구간입니다. 기준값은 제공되지 않았지만 충격이 지속되는 기간으로 보아 최종 PMI 지수 47.5를 적용했습니다. |
| 20 | `{"Country": "United States", "Month": 2, "Year": 2027}` | null | 47.5 | 해당 좌표는 경기 충격 후반부의 월별 PMI 입력 구간입니다. 회복 근거가 없으므로 동일한 위축 수준의 최종 PMI 지수 47.5로 산정했습니다. |
| 21 | `{"Country": "United States", "Month": 3, "Year": 2027}` | null | 47.5 | 해당 좌표는 충격 지속 기간 내 월별 PMI 입력입니다. 경기 충격에 따른 산업활동 둔화를 유지해 최종 PMI 지수 47.5를 적용했습니다. |
| 22 | `{"Country": "United States", "Month": 4, "Year": 2027}` | null | 47.5 | 해당 좌표는 1년 충격 구간 후반의 PMI 입력입니다. 별도 회복이나 완화가 제시되지 않아 최종 PMI 지수 47.5를 유지했습니다. |
| 23 | `{"Country": "United States", "Month": 5, "Year": 2027}` | null | 47.5 | 해당 좌표는 경기 충격 지속 구간의 월별 PMI 입력입니다. 기준 record 없이도 시나리오 강도와 기간에 맞춰 최종 PMI 지수 47.5로 산정했습니다. |
| 24 | `{"Country": "United States", "Month": 6, "Year": 2027}` | null | 47.5 | 해당 좌표는 1년 경기 충격 구간의 마지막 월별 PMI 입력입니다. 충격 종료 전까지 위축 수준을 유지하는 전제로 최종 PMI 지수 47.5를 적용했습니다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.0385 | 해당 좌표의 기준 GDP 변화율은 0.042입니다. 1년 충격이 2026년 하반기부터 반영되는 점을 고려해 OECD 하방 시나리오의 2026년 성장 둔화 폭을 절반 수준인 0.0035만큼 반영하여 최종 GDP 변화율을 0.0385로 산정했습니다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.0355 | 해당 좌표의 기준 GDP 변화율은 0.042입니다. 충격이 2027년 상반기까지 이어지는 구간으로 보아 OECD 하방 시나리오의 2027년 성장 둔화 폭을 절반 수준인 0.0065만큼 반영하여 최종 GDP 변화율을 0.0355로 산정했습니다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.0155 | 해당 좌표의 기준 GDP 변화율은 0.019입니다. 2026년 하반기부터 1년 경기 충격이 반영되는 구조이므로 2026년 성장 둔화 폭 0.0035를 적용해 최종 GDP 변화율을 0.0155로 산정했습니다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.0135 | 해당 좌표의 기준 GDP 변화율은 0.02입니다. 충격이 2027년 상반기까지 지속되는 점을 반영해 2027년 성장 둔화 폭 0.0065를 차감하고 최종 GDP 변화율을 0.0135로 산정했습니다. |

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
  "model_param_proposal_id": 30,
  "proposal_completed_dtm": "2026-07-07 17:04:48.259177",
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
      "rationale": "강도 차원의 '경기 충격'은 mapping_comment상 산업 수요의 단기 변동을 PMI로 반영하는 직접 요인입니다. 기간 차원의 '1년'은 공통 시간 맥락으로 사용해 월별 PMI 조정이 1년 구간에 걸쳐 지속되는 구조로 반영했습니다. 제안값은 제조업 심리 위축을 나타내도록 중립선 아래의 PMI 최종 지수로 하향 적용하되, 기준값이 있는 구간은 기준 PMI에서 보수적인 충격 폭을 차감하고 기준값이 없는 구간은 같은 형식의 월별 PMI 지수로 산정했습니다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격이 시작되는 월별 PMI 입력 구간이며, 기준 PMI 49.5에서 경기 충격에 따른 제조업 위축 폭 2.0pt를 차감해 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 충격이 지속되는 월별 PMI 입력 구간이며, 기준 PMI 49.5에 동일한 제조업 위축 폭 2.0pt를 적용해 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 경기 충격 지속 구간의 월별 PMI record이며, 기준 PMI 49.5에서 2.0pt 하향 조정을 반영해 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 충격 기간 내 월별 PMI 입력 구간이며, 기준 PMI 49.5를 경기 충격 수준에 맞춰 2.0pt 낮춰 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격이 이어지는 월별 PMI 구간이며, 기준 PMI 49.5에서 제조업 수요 둔화 폭 2.0pt를 반영해 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 연말까지 지속되는 경기 충격 구간의 PMI record이며, 기준 PMI 49.5에 2.0pt 하향 충격을 적용해 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 충격의 후반부에 해당하는 월별 PMI 입력 구간입니다. 일치하는 기준 record는 제공되지 않았으나, 같은 충격 구간의 연속 월로 보아 최종 PMI 지수를 기준 구간과 동일한 위축 수준인 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 경기 충격 후반부의 월별 PMI 입력 구간입니다. 일치 기준값이 없으므로 별도 회복을 가정하지 않고, 1년 지속 충격에 맞춰 최종 PMI 지수 47.5를 적용했습니다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격이 유지되는 월별 PMI 구간입니다. 제공된 기준 record가 없어도 기간 내 충격 강도를 동일하게 유지해 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 충격 기간 내 후반 월별 PMI 입력 구간입니다. 명확한 회복 근거가 없으므로 제조업 위축 상태가 유지되는 최종 PMI 지수 47.5를 적용했습니다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격이 지속되는 월별 PMI 구간입니다. 일치 기준값은 없지만 같은 시나리오 충격 범위에 포함되므로 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 충격 구간의 마지막 월별 PMI 입력 구간입니다. 회복 전환을 별도로 두지 않고 충격 지속 조건에 맞춰 최종 PMI 지수 47.5를 적용했습니다."
        },
        {
          "Country": "United States",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격이 시작되는 월별 PMI 입력 구간입니다. 일치 기준 record는 제공되지 않았으나, 단기 산업 수요 위축을 반영할 수 있도록 최종 PMI 지수를 중립선 아래의 47.5로 산정했습니다."
        },
        {
          "Country": "United States",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 경기 충격 지속 구간의 월별 PMI 입력 구간입니다. 기준값이 제공되지 않아도 동일한 1년 충격 강도를 유지해 최종 PMI 지수 47.5를 적용했습니다."
        },
        {
          "Country": "United States",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 충격 기간 중 월별 PMI 입력 구간입니다. 제조업 심리와 산업 수요 둔화가 지속되는 전제로 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "United States",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격 내 월별 PMI 구간입니다. 일치 기준 record가 없어도 동일한 충격 구간의 입력값으로 중립선 아래 PMI 47.5를 적용했습니다."
        },
        {
          "Country": "United States",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 경기 충격이 이어지는 월별 PMI 입력 구간입니다. 별도 완화 근거가 없으므로 최종 PMI 지수 47.5를 유지했습니다."
        },
        {
          "Country": "United States",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 연말까지 지속되는 충격 구간의 월별 PMI 입력입니다. 산업 수요 위축을 반영해 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "United States",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격의 후반부 월별 PMI 구간입니다. 기준값은 제공되지 않았지만 충격이 지속되는 기간으로 보아 최종 PMI 지수 47.5를 적용했습니다."
        },
        {
          "Country": "United States",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 경기 충격 후반부의 월별 PMI 입력 구간입니다. 회복 근거가 없으므로 동일한 위축 수준의 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 충격 지속 기간 내 월별 PMI 입력입니다. 경기 충격에 따른 산업활동 둔화를 유지해 최종 PMI 지수 47.5를 적용했습니다."
        },
        {
          "Country": "United States",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 충격 구간 후반의 PMI 입력입니다. 별도 회복이나 완화가 제시되지 않아 최종 PMI 지수 47.5를 유지했습니다."
        },
        {
          "Country": "United States",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 경기 충격 지속 구간의 월별 PMI 입력입니다. 기준 record 없이도 시나리오 강도와 기간에 맞춰 최종 PMI 지수 47.5로 산정했습니다."
        },
        {
          "Country": "United States",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 좌표는 1년 경기 충격 구간의 마지막 월별 PMI 입력입니다. 충격 종료 전까지 위축 수준을 유지하는 전제로 최종 PMI 지수 47.5를 적용했습니다."
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
      "rationale": "강도 차원의 '경기 충격'은 mapping_comment상 국가별 GDP 경로를 조정해야 하는 구조적 경기 변수와 직접 연결됩니다. 기간 차원의 '1년'은 공통 시간 맥락으로 사용해 현재 기준 시점 이후 1년 충격이 연간 GDP 입력에 부분 반영되는 구조로 적용했습니다. 제안값은 OECD 하방 시나리오의 성장 둔화 방향과 시나리오의 수요 감소 서사를 반영해 연간 실질 GDP 변화율을 기준값보다 낮은 최종 입력값으로 산정했습니다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.0385,
          "rationale": "해당 좌표의 기준 GDP 변화율은 0.042입니다. 1년 충격이 2026년 하반기부터 반영되는 점을 고려해 OECD 하방 시나리오의 2026년 성장 둔화 폭을 절반 수준인 0.0035만큼 반영하여 최종 GDP 변화율을 0.0385로 산정했습니다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.0355,
          "rationale": "해당 좌표의 기준 GDP 변화율은 0.042입니다. 충격이 2027년 상반기까지 이어지는 구간으로 보아 OECD 하방 시나리오의 2027년 성장 둔화 폭을 절반 수준인 0.0065만큼 반영하여 최종 GDP 변화율을 0.0355로 산정했습니다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.0155,
          "rationale": "해당 좌표의 기준 GDP 변화율은 0.019입니다. 2026년 하반기부터 1년 경기 충격이 반영되는 구조이므로 2026년 성장 둔화 폭 0.0035를 적용해 최종 GDP 변화율을 0.0155로 산정했습니다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.0135,
          "rationale": "해당 좌표의 기준 GDP 변화율은 0.02입니다. 충격이 2027년 상반기까지 지속되는 점을 반영해 2027년 성장 둔화 폭 0.0065를 차감하고 최종 GDP 변화율을 0.0135로 산정했습니다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:07.137 | 7.137 | 2347 | 117 | 2464 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:51.797 | 51.797 | 5304 | 3696 | 9000 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:15.246 | 75.246 | 7447 | 5444 | 12891 |

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"60": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.

## Parameter Quality Evaluation - GDP

### Evaluation Scope

- Target parameter: `GDP`
- event_type_l2_id: `21` 국가별 경기
- scenario_group_id: `60`
- scenarios: `305`, `306`
- DB mapping: `economic_intensity -> GDP`, `mapping_method=direct`
- Non-input mapping note: `demand_impact` is `mapping_method=na` and `prompt_usage_policy=excluded_from_parameter_slot_value_prompt`; scenario-specific values are `305=100%`, `306=25%`, but this dimension must not directly drive GDP slot/value calculation.

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나. `direct` mapping candidates must be selected. | PASS | `Dimension -> Parameter Mapping` shows `economic_intensity -> GDP` as `direct`. Both scenario 305 and 306 validation summaries show `expected_parameters=["PMI","GDP"]`, `selected_parameters=["PMI","GDP"]`, `mapping_candidate_coverage=PASS`, and `selected_result=PASS`. | 없음. |
| 2 | slot이 정확히 선정되고 slot 값/범위가 유효한가. | PASS | GDP model target uses slot axes `Country`, `Year`. Scenario 305 selected China/United States for 2026. Scenario 306 selected China/United States for 2026/2027. These countries and years are explicitly present in the event analysis: China 2026/2027 and United States 2026/2027 growth outlooks. | 향후 event에 국가별 전망이 없는 경우에는 국가 선택 근거를 더 보수적으로 제한하도록 slot rationale을 강화할 수 있음. |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가. | PASS | All GDP value rows have `basecaseValue`: scenario 305 China 2026 `0.042`, US 2026 `0.019`; scenario 306 China 2026/2027 `0.042/0.042`, US 2026/2027 `0.019/0.02`. Selected slots correspond to existing basecase rows. | 없음. |
| 4 | slot이 basecase에 없지만 시나리오/이벤트 정보를 활용해 추가 선정된 경우 개연성이 있는가. | N/A | GDP selected rows all have basecase values. No GDP slot was added without basecase. | 없음. |
| 5 | slot이 basecase에 없는 경우를 선정하지 못했다면 선정해도 될 가능성이 없었는가. | N/A | GDP 평가 대상에는 missing-basecase GDP slot이 없음. | 없음. |
| 6 | value가 지정된 범위/형식으로 선정되었고 시나리오/이벤트와 개연성이 있는가. | REVIEW | GDP values are decimal growth-rate inputs matching `% change (+/-)` format: `0.045`, `0.02`, `0.0385`, `0.0355`, `0.0155`, `0.0135`. Direction is broadly plausible: scenario 305 mild case applies explicit OECD China/US 2026 rates, scenario 306 shock case lowers GDP below basecase. However scenario 306 uses inferred half-year downside adjustments `0.0035/0.0065`; the report rationale does not fully tie those exact deltas to a deterministic source formula. | GDP value 산정식에 `event explicit forecast`, `basecase`, `shock duration`, `downside adjustment`의 우선순위와 환산식을 prompt 또는 post-validation 규칙으로 명확히 남기는 것이 좋음. |
| 7 | value가 basecase에 있는 경우 적절하게 변경되었나. | REVIEW | Scenario 305 changes China 2026 `0.042 -> 0.045` and US 2026 `0.019 -> 0.02`, matching event-stated 2026 country growth rates. Scenario 306 changes China 2026/2027 `0.042 -> 0.0385/0.0355` and US 2026/2027 `0.019/0.02 -> 0.0155/0.0135`, reflecting stronger and longer shock. The direction is plausible, but exact downside magnitude is model-inferred rather than directly evidenced. | 산정 근거를 "기준 성장률 대비 몇 bp 조정"으로 구조화하고, event에 국가별 downside가 없으면 보수적 범위와 이유를 명시하도록 개선. |
| 8 | value가 basecase에 없었던 경우 개연성 있게 선정되었나. | N/A | GDP value rows all include basecase values. | 없음. |
| 9 | 동일 그룹의 시나리오 사이에 dimension value에 따라 value 차이가 적절한가. | PASS | Scenario 305 has `economic_intensity=경미`, `period=1개월 이하` and GDP values are limited to 2026 with mild/direct forecast adjustments. Scenario 306 has `economic_intensity=경기 충격`, `period=1년` and GDP values cover 2026/2027 with lower proposed values. Group summary also reports `scenario별 value 차이: PASS`. | 없음. |

### GDP Findings

- `demand_impact` no longer appears as a GDP value driver in the mapping policy: it is shown as `na` with `excluded_from_parameter_slot_value_prompt`.
- GDP parameter selection is correct under current DB mapping because `economic_intensity` is a direct GDP mapping.
- Main review item is value magnitude traceability, not parameter or slot selection. Scenario 306 values are directionally reasonable, but the exact `0.0035` and `0.0065` downward adjustments should be made more auditable.
