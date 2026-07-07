# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-08T01:39:47
- 실행 종료: 2026-07-08T01:42:24
- 총 소요시간: 02:37.503 (157.503s)
- 대상 event_type_l2_ids: [21]
- 대상 parameters: []
- concurrency: 1
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=21 국가별 경기: scenario_group 1개, scenario 2개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 21 | 60 | 305 | OK | 1 | 01:07.512 | 67.512s |
| 21 | 60 | 306 | OK | 1 | 01:29.985 | 89.985s |

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
      "comment": "수요 영향분 직접 조정(또는 PMI 강도로 반영) : User-Adjusted Gas Demand는 직접 쓰지 않고, 단기 수요 충격은 PMI, 구조적 수요 변화는 GDP 또는 PowerMix proxy로 우회 반영",
      "dimension": "demand_impact (LNG 수요 영향 규모)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "구조적 경기(GDP) 변동 : 장기·구조적 경기 변화는 국가별 GDP 경로를 조정하고, 일시적 심리·제조업 충격은 PMI를 우선 사용",
      "dimension": "economic_intensity (강도)",
      "mapping_method": "direct",
      "parameter": "GDP"
    },
    {
      "comment": "산업 수요 단기 변동(PMI 탭) : 단기 경기 충격은 영향 국가의 PMI 조정으로 반영하고, 구조적 장기 성장 변화는 GDP 경로를 우선 검토",
      "dimension": "economic_intensity (강도)",
      "mapping_method": "direct",
      "parameter": "PMI"
    },
    {
      "comment": "시간축",
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

- 소요시간: 01:07.512 (67.512s)
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
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 1 | 강도 차원의 '경미'는 산업 수요의 단기 심리·제조업 활동 변화로 해석되어 국가·월별 PMI 입력과 직접 연결된다. 기간 차원은 1개월 이하이므로 적용 범위는 단기 월간 조정으로 제한하며, 가격 영향도 중립으로 제시되어 기준 대비 소폭 하향에 그치는 보수적 구조로 제안한다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 2 | 강도 차원의 '경미'는 국가별 경기 경로 점검과 연결되어 GDP 입력 후보를 선택하게 하지만, 기간 차원이 1개월 이하로 매우 짧아 연간 실질 GDP 경로를 구조적으로 바꿀 근거는 약하다. 따라서 단기 수요 영향은 PMI 쪽에서 제한적으로 반영하고, GDP는 선택된 국가의 연간 기준 경로를 유지하는 구조로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 49.3 | 2026년 7월 중국 PMI 기준값은 49.5이며, 시나리오가 1개월 이하의 경미한 경기 둔화를 전제로 하므로 해당 월에만 제한적으로 0.2포인트 낮춘 49.3을 최종 입력값으로 적용한다. 수요 영향이 거의 흡수되고 가격 영향도 중립으로 제시되어 추가적인 큰 폭 조정은 반영하지 않았다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.042 | 2026년 중국 GDP 변화율 기준값은 0.042이다. 시나리오의 경기 영향은 1개월 이하의 경미한 둔화로 제시되어 연간 성장률 입력을 조정할 정도의 구조적 변화로 보지 않고, 기준값 0.042를 그대로 최종 입력값으로 유지한다. |
| 2 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.019 | 2026년 미국 GDP 변화율 기준값은 0.019이다. 단기적이고 경미한 경기 둔화는 연간 GDP 경로보다 월간 산업활동 지표에 우선 반영하는 것이 적절하므로, 해당 연간 입력은 기준값 0.019를 최종 입력값으로 유지한다. |

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
  "model_param_proposal_id": 120,
  "proposal_completed_dtm": "2026-07-08 01:40:54.666935",
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
      "rationale": "강도 차원의 '경미'는 산업 수요의 단기 심리·제조업 활동 변화로 해석되어 국가·월별 PMI 입력과 직접 연결된다. 기간 차원은 1개월 이하이므로 적용 범위는 단기 월간 조정으로 제한하며, 가격 영향도 중립으로 제시되어 기준 대비 소폭 하향에 그치는 보수적 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.3,
          "rationale": "2026년 7월 중국 PMI 기준값은 49.5이며, 시나리오가 1개월 이하의 경미한 경기 둔화를 전제로 하므로 해당 월에만 제한적으로 0.2포인트 낮춘 49.3을 최종 입력값으로 적용한다. 수요 영향이 거의 흡수되고 가격 영향도 중립으로 제시되어 추가적인 큰 폭 조정은 반영하지 않았다."
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
      "rationale": "강도 차원의 '경미'는 국가별 경기 경로 점검과 연결되어 GDP 입력 후보를 선택하게 하지만, 기간 차원이 1개월 이하로 매우 짧아 연간 실질 GDP 경로를 구조적으로 바꿀 근거는 약하다. 따라서 단기 수요 영향은 PMI 쪽에서 제한적으로 반영하고, GDP는 선택된 국가의 연간 기준 경로를 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "2026년 중국 GDP 변화율 기준값은 0.042이다. 시나리오의 경기 영향은 1개월 이하의 경미한 둔화로 제시되어 연간 성장률 입력을 조정할 정도의 구조적 변화로 보지 않고, 기준값 0.042를 그대로 최종 입력값으로 유지한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.019,
          "rationale": "2026년 미국 GDP 변화율 기준값은 0.019이다. 단기적이고 경미한 경기 둔화는 연간 GDP 경로보다 월간 산업활동 지표에 우선 반영하는 것이 적절하므로, 해당 연간 입력은 기준값 0.019를 최종 입력값으로 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.643 | 3.643 | 2334 | 70 | 2404 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:28.204 | 28.204 | 5295 | 1220 | 6515 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:22.223 | 22.223 | 6260 | 1342 | 7602 |

#### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- 소요시간: 01:29.985 (89.985s)
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
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Year", "Month", "Country"]` | `["PMI"]` | 12 | 강도 차원의 '경기 충격'은 산업 수요의 단기 위축을 제조업 PMI 조정으로 반영한다는 parameter 의미와 직접 연결됩니다. 기간 차원의 '1년'은 공통 시간 맥락으로 사용하여 현재 기준월부터 12개월 동안 같은 방향의 하향 조정을 적용하되, 월별 회복 패턴이 별도로 제시되지 않았으므로 균등한 충격으로 제안합니다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Year", "Country"]` | `["% change (+/-)"]` | 4 | 강도 차원의 '경기 충격'은 국가별 실질 GDP 성장률 경로를 하향 조정해 수요 둔화를 반영한다는 parameter 의미와 직접 연결됩니다. 기간 차원의 '1년'은 현재 기준월 이후 12개월에 걸친 충격으로 해석하되, GDP 입력이 연 단위이므로 2026년과 2027년 연간 슬롯에 나누어 보수적으로 반영합니다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 47.5 | 해당 월·국가의 기준 PMI 49.5가 확인되며, 1년 경기 충격에 따른 산업활동 둔화를 반영해 기준보다 2.0pt 낮은 47.5로 산정했습니다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 49.5 | 47.5 | 해당 월·국가의 기준 PMI 49.5가 확인되며, 충격 지속 기간 내 동일한 수요 둔화 강도를 적용해 47.5로 산정했습니다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 49.5 | 47.5 | 해당 월·국가의 기준 PMI 49.5가 확인되며, 1년 경기 충격 구간의 제조업 위축을 반영해 47.5로 산정했습니다. |
| 4 | `{"Country": "China", "Month": 10, "Year": 2026}` | 49.5 | 47.5 | 해당 월·국가의 기준 PMI 49.5가 확인되며, 별도 완화 경로가 없으므로 같은 충격 강도를 유지해 47.5로 산정했습니다. |
| 5 | `{"Country": "China", "Month": 11, "Year": 2026}` | 49.5 | 47.5 | 해당 월·국가의 기준 PMI 49.5가 확인되며, 경기 충격에 따른 단기 산업 수요 둔화를 반영해 47.5로 산정했습니다. |
| 6 | `{"Country": "China", "Month": 12, "Year": 2026}` | 49.5 | 47.5 | 해당 월·국가의 기준 PMI 49.5가 확인되며, 1년 지속 충격의 연말 구간에도 동일한 하향 조정을 적용해 47.5로 산정했습니다. |
| 7 | `{"Country": "China", "Month": 1, "Year": 2027}` | null | 47.5 | 해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 중국 월별 기준값이 49.5로 일관되어 있어 이를 형식·수준 참고값으로 보았습니다. 1년 충격이 계속되는 구간이므로 2.0pt 하향한 47.5로 산정했습니다. |
| 8 | `{"Country": "China", "Month": 2, "Year": 2027}` | null | 47.5 | 해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 중국 월별 기준값 49.5를 참고했습니다. 충격 지속 구간 내 동일한 제조업 위축 강도를 적용해 47.5로 산정했습니다. |
| 9 | `{"Country": "China", "Month": 3, "Year": 2027}` | null | 47.5 | 해당 월의 직접 기준 record는 제공되지 않았으나 제공된 중국 PMI 기준값이 모두 49.5인 점을 참고했습니다. 1년 경기 충격에 따른 수요 둔화를 반영해 47.5로 산정했습니다. |
| 10 | `{"Country": "China", "Month": 4, "Year": 2027}` | null | 47.5 | 해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 기준 수준 49.5를 보수적 참고값으로 사용했습니다. 충격 기간 내 동일 하향 강도를 적용해 47.5로 산정했습니다. |
| 11 | `{"Country": "China", "Month": 5, "Year": 2027}` | null | 47.5 | 해당 월의 직접 기준 record는 제공되지 않았으나 중국 PMI의 제공 기준값 49.5와 같은 형식으로 산정했습니다. 1년 경기 충격이 이어지는 월로 보아 47.5를 제안했습니다. |
| 12 | `{"Country": "China", "Month": 6, "Year": 2027}` | null | 47.5 | 해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 중국 기준 수준 49.5를 참고했습니다. 1년 충격의 마지막 월까지 수요 둔화가 유지된다고 보고 47.5로 산정했습니다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.0395 | 해당 연도·국가의 기준 GDP 변화율은 0.042입니다. 충격이 2026년 하반기부터 시작되는 1년 구간이라는 점을 반영해 연간 성장률을 0.0025 낮춘 0.0395로 산정했습니다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.0395 | 해당 연도·국가의 기준 GDP 변화율은 0.042입니다. 충격이 2027년 상반기까지 이어지는 것으로 보아 연간 성장률을 0.0025 낮춘 0.0395로 산정했습니다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.0165 | 해당 연도·국가의 기준 GDP 변화율은 0.019입니다. 2026년 하반기에 반영되는 경기 충격을 고려해 연간 성장률을 0.0025 낮춘 0.0165로 산정했습니다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.0175 | 해당 연도·국가의 기준 GDP 변화율은 0.02입니다. 2027년 상반기까지 충격이 지속되는 점을 반영해 연간 성장률을 0.0025 낮춘 0.0175로 산정했습니다. |

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
  "model_param_proposal_id": 121,
  "proposal_completed_dtm": "2026-07-08 01:42:24.647679",
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
      "rationale": "강도 차원의 '경기 충격'은 산업 수요의 단기 위축을 제조업 PMI 조정으로 반영한다는 parameter 의미와 직접 연결됩니다. 기간 차원의 '1년'은 공통 시간 맥락으로 사용하여 현재 기준월부터 12개월 동안 같은 방향의 하향 조정을 적용하되, 월별 회복 패턴이 별도로 제시되지 않았으므로 균등한 충격으로 제안합니다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월·국가의 기준 PMI 49.5가 확인되며, 1년 경기 충격에 따른 산업활동 둔화를 반영해 기준보다 2.0pt 낮은 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월·국가의 기준 PMI 49.5가 확인되며, 충격 지속 기간 내 동일한 수요 둔화 강도를 적용해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월·국가의 기준 PMI 49.5가 확인되며, 1년 경기 충격 구간의 제조업 위축을 반영해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월·국가의 기준 PMI 49.5가 확인되며, 별도 완화 경로가 없으므로 같은 충격 강도를 유지해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월·국가의 기준 PMI 49.5가 확인되며, 경기 충격에 따른 단기 산업 수요 둔화를 반영해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월·국가의 기준 PMI 49.5가 확인되며, 1년 지속 충격의 연말 구간에도 동일한 하향 조정을 적용해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 중국 월별 기준값이 49.5로 일관되어 있어 이를 형식·수준 참고값으로 보았습니다. 1년 충격이 계속되는 구간이므로 2.0pt 하향한 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 중국 월별 기준값 49.5를 참고했습니다. 충격 지속 구간 내 동일한 제조업 위축 강도를 적용해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월의 직접 기준 record는 제공되지 않았으나 제공된 중국 PMI 기준값이 모두 49.5인 점을 참고했습니다. 1년 경기 충격에 따른 수요 둔화를 반영해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 기준 수준 49.5를 보수적 참고값으로 사용했습니다. 충격 기간 내 동일 하향 강도를 적용해 47.5로 산정했습니다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월의 직접 기준 record는 제공되지 않았으나 중국 PMI의 제공 기준값 49.5와 같은 형식으로 산정했습니다. 1년 경기 충격이 이어지는 월로 보아 47.5를 제안했습니다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월의 직접 기준 record는 제공되지 않았으나 같은 parameter의 중국 기준 수준 49.5를 참고했습니다. 1년 충격의 마지막 월까지 수요 둔화가 유지된다고 보고 47.5로 산정했습니다."
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
      "rationale": "강도 차원의 '경기 충격'은 국가별 실질 GDP 성장률 경로를 하향 조정해 수요 둔화를 반영한다는 parameter 의미와 직접 연결됩니다. 기간 차원의 '1년'은 현재 기준월 이후 12개월에 걸친 충격으로 해석하되, GDP 입력이 연 단위이므로 2026년과 2027년 연간 슬롯에 나누어 보수적으로 반영합니다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.0395,
          "rationale": "해당 연도·국가의 기준 GDP 변화율은 0.042입니다. 충격이 2026년 하반기부터 시작되는 1년 구간이라는 점을 반영해 연간 성장률을 0.0025 낮춘 0.0395로 산정했습니다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.0395,
          "rationale": "해당 연도·국가의 기준 GDP 변화율은 0.042입니다. 충격이 2027년 상반기까지 이어지는 것으로 보아 연간 성장률을 0.0025 낮춘 0.0395로 산정했습니다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.0165,
          "rationale": "해당 연도·국가의 기준 GDP 변화율은 0.019입니다. 2026년 하반기에 반영되는 경기 충격을 고려해 연간 성장률을 0.0025 낮춘 0.0165로 산정했습니다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.0175,
          "rationale": "해당 연도·국가의 기준 GDP 변화율은 0.02입니다. 2027년 상반기까지 충격이 지속되는 점을 반영해 연간 성장률을 0.0025 낮춘 0.0175로 산정했습니다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.292 | 4.292 | 2347 | 119 | 2466 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:27.617 | 27.617 | 5304 | 1998 | 7302 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:44.847 | 44.847 | 7113 | 3343 | 10456 |

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"60": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.
