# Model Parameter Proposal Evaluation - Parameters

- 실행 시작: 2026-07-07T23:28:08
- 실행 종료: 2026-07-07T23:51:18
- 총 소요시간: 23:09.538 (1389.538s)
- 대상 event_type_l2_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 17, 18, 19, 21]
- 대상 parameters: ['GDP', 'PMI', 'PowerMix', 'Temperature', 'LiqUtilAdjustment']
- concurrency: 4
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=1 Upstream Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=2 터미널 Utilization 변동: scenario_group 2개, scenario 4개
- event_type_l2_id=4 파이프라인 Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=5 발전소 Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=6 겨울 한파: scenario_group 2개, scenario 4개
- event_type_l2_id=7 여름 폭염: scenario_group 2개, scenario 4개
- event_type_l2_id=8 원자력 발전: scenario_group 1개, scenario 2개
- event_type_l2_id=9 재생에너지: scenario_group 1개, scenario 2개
- event_type_l2_id=10 석탄 발전: scenario_group 1개, scenario 2개
- event_type_l2_id=11 자연재해: scenario_group 1개, scenario 2개
- event_type_l2_id=17 지정학적 긴장 및 전쟁·군사분쟁: scenario_group 1개, scenario 2개
- event_type_l2_id=18 경제 제재 및 무역 제한: scenario_group 2개, scenario 4개
- event_type_l2_id=19 정책/규제 변화: scenario_group 1개, scenario 2개
- event_type_l2_id=21 국가별 경기: scenario_group 1개, scenario 2개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 1 | 49 | 283 | OK | 1 | 04:07.088 | 247.088s |
| 1 | 49 | 284 | OK | 1 | 05:08.001 | 308.001s |
| 2 | 18 | 105 | OK | 1 | 01:35.623 | 95.623s |
| 2 | 18 | 106 | OK | 1 | 01:21.334 | 81.334s |
| 2 | 46 | 273 | OK | 1 | 01:26.262 | 86.262s |
| 2 | 46 | 274 | OK | 1 | 02:49.876 | 169.876s |
| 4 | 50 | 285 | OK | 1 | 02:47.237 | 167.237s |
| 4 | 50 | 286 | OK | 1 | 04:44.528 | 284.528s |
| 5 | 51 | 287 | OK | 1 | 01:33.478 | 93.478s |
| 5 | 51 | 288 | OK | 1 | 01:11.043 | 71.043s |
| 6 | 52 | 289 | OK | 1 | 01:49.127 | 109.127s |
| 6 | 52 | 290 | OK | 1 | 03:00.635 | 180.635s |
| 6 | 61 | 307 | OK | 1 | 01:56.326 | 116.326s |
| 6 | 61 | 308 | OK | 1 | 02:18.354 | 138.354s |
| 7 | 53 | 291 | OK | 1 | 01:44.862 | 104.862s |
| 7 | 53 | 292 | OK | 1 | 01:58.668 | 118.668s |
| 7 | 64 | 317 | OK | 1 | 01:52.281 | 112.281s |
| 7 | 64 | 318 | OK | 1 | 01:56.503 | 116.503s |
| 8 | 54 | 293 | OK | 1 | 00:37.399 | 37.399s |
| 8 | 54 | 294 | OK | 1 | 01:02.568 | 62.568s |
| 9 | 44 | 261 | OK | 1 | 01:13.087 | 73.087s |
| 9 | 44 | 262 | OK | 1 | 01:20.910 | 80.910s |
| 10 | 45 | 267 | OK | 1 | 00:52.748 | 52.748s |
| 10 | 45 | 268 | OK | 1 | 00:58.036 | 58.036s |
| 11 | 47 | 279 | OK | 1 | 03:31.281 | 211.281s |
| 11 | 47 | 280 | OK | 1 | 04:31.625 | 271.625s |
| 17 | 16 | 92 | OK | 1 | 03:44.984 | 224.984s |
| 17 | 16 | 93 | OK | 1 | 06:07.484 | 367.484s |
| 18 | 22 | 129 | OK | 1 | 02:16.716 | 136.716s |
| 18 | 22 | 130 | OK | 1 | 04:42.747 | 282.747s |
| 18 | 23 | 135 | OK | 1 | 02:49.706 | 169.706s |
| 18 | 23 | 136 | OK | 1 | 05:18.011 | 318.011s |
| 19 | 48 | 281 | ERROR | 2 | 00:56.958 | 56.958s |
| 19 | 48 | 282 | ERROR | 2 | 00:56.764 | 56.764s |
| 21 | 60 | 305 | OK | 1 | 01:32.129 | 92.129s |
| 21 | 60 | 306 | OK | 1 | 02:09.082 | 129.082s |

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

- 대상 scenario_ids: [305, 306]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=305 [model_parameter_agent_test] 경미한 경기 둔화와 수요 영향 제한

- target_parameter: `GDP`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:32.129 (92.129s)
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 2 | 강도 차원의 값이 ‘경미’로 제시되어 국가별 거시 성장률 경로가 LNG 수요 전제에 미치는 영향을 GDP 입력으로 확인하는 대상이다. 다만 기간은 1개월 이하로 구조적 충격보다는 제한적 조정에 가까우므로, 이벤트에 명시된 국가별 2026년 성장 전망을 반영하되 변화 폭은 보수적으로 현재 연도·국가 슬롯에만 적용한다. |

###### Proposed Parameter Values

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.045 | 해당 좌표는 선택된 중국 2026년 GDP 입력 record와 직접 일치한다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 제시되어, 기준값 0.042 대신 동일한 소수 비율 형식의 최종 입력값 0.045를 적용한다. |
| 2 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.02 | 해당 좌표는 선택된 미국 2026년 GDP 입력 record와 직접 일치한다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어, 기준값 0.019에서 제한적으로 상향한 동일 형식의 최종 입력값 0.02를 적용한다. |

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
  "model_param_proposal_id": 117,
  "proposal_completed_dtm": "2026-07-07 23:49:36.992290",
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
      "rationale": "강도 차원의 값이 ‘경미’로 제시되어 산업 수요의 단기 심리·제조업 변동을 PMI 입력으로 점검하는 대상이다. 기간은 1개월 이하로 짧고 시나리오상 LNG 수요 영향이 거의 흡수되며 가격 영향도 중립으로 제시되어, 적용 대상 월의 PMI는 추가 충격을 크게 반영하지 않고 현 기준 경로를 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.5,
          "rationale": "해당 좌표는 선택된 중국 2026년 7월 PMI 입력 record와 직접 일치한다. 기준값 49.5에 대해 경미한 경기 영향과 1개월 이하의 짧은 기간, 수요 영향 제한 및 중립적 가격 영향을 반영하여 추가 하향 조정 없이 최종 입력값을 49.5로 유지한다."
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
      "rationale": "강도 차원의 값이 ‘경미’로 제시되어 국가별 거시 성장률 경로가 LNG 수요 전제에 미치는 영향을 GDP 입력으로 확인하는 대상이다. 다만 기간은 1개월 이하로 구조적 충격보다는 제한적 조정에 가까우므로, 이벤트에 명시된 국가별 2026년 성장 전망을 반영하되 변화 폭은 보수적으로 현재 연도·국가 슬롯에만 적용한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.045,
          "rationale": "해당 좌표는 선택된 중국 2026년 GDP 입력 record와 직접 일치한다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 제시되어, 기준값 0.042 대신 동일한 소수 비율 형식의 최종 입력값 0.045를 적용한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.02,
          "rationale": "해당 좌표는 선택된 미국 2026년 GDP 입력 record와 직접 일치한다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어, 기준값 0.019에서 제한적으로 상향한 동일 형식의 최종 입력값 0.02를 적용한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:07.818 | 7.818 | 2334 | 70 | 2404 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:27.691 | 27.691 | 5295 | 1738 | 7033 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:37.567 | 37.567 | 6260 | 1665 | 7925 |

##### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- target_parameter: `GDP`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:09.082 (129.082s)
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

- target_expected_parameters: `["GDP"]`
- target_selected_parameters: `["GDP"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Year", "Country"]` | `["% change (+/-)"]` | 4 | 강도 dimension의 ‘경기 충격’은 국가별 실질 GDP 성장률 경로를 조정해 산업·전력·가스 수요의 거시 전제를 낮추는 parameter 의미와 직접 연결된다. 기간 dimension의 ‘1년’은 2026년 하반기부터 2027년 상반기까지의 시간 범위로 해석해 연간 GDP 입력값에는 2026년과 2027년에 나누어 하방 충격을 반영하고, 국가별 기준 성장률에서 보수적으로 하향한 최종 성장률을 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.0385 | 중국 2026년 기준 성장률 0.042에 대해 2026년 하반기 경기 충격을 연간값에 반영했다. OECD 하방 시나리오의 2026년 글로벌 성장 둔화 폭을 반년 적용하는 보수적 방식으로 0.0035를 차감해 최종 입력값을 0.0385로 산정한다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.0355 | 중국 2027년 기준 성장률 0.042에 대해 2027년 상반기까지 충격이 이어지는 것으로 반영했다. 2027년 하방 시나리오의 더 큰 글로벌 성장 둔화 폭을 반년 적용해 0.0065를 차감하고, 최종 입력값을 0.0355로 산정한다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.0155 | 미국 2026년 기준 성장률 0.019에 대해 2026년 하반기 경기 충격을 연간값에 부분 반영했다. 글로벌 하방 충격을 반년 적용한 0.0035 하향 조정으로 최종 입력값을 0.0155로 산정한다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.0135 | 미국 2027년 기준 성장률 0.02에 대해 2027년 상반기 충격 지속을 반영했다. 2027년 글로벌 하방 시나리오의 성장 둔화 폭을 반년 적용해 0.0065를 차감하고, 최종 입력값을 0.0135로 산정한다. |

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
  "model_param_proposal_id": 118,
  "proposal_completed_dtm": "2026-07-07 23:50:58.781118",
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
      "rationale": "강도 dimension의 ‘경기 충격’은 제조업 심리와 산업 수요의 단기 둔화를 PMI 조정으로 반영하는 parameter 의미와 직접 연결된다. 기간 dimension의 ‘1년’은 공통 시간 맥락으로 사용해 2026년 7월부터 2027년 6월까지 중국 PMI를 일관되게 하향 조정하되, 기준값이 이미 위축 국면에 가까운 점을 감안해 보수적인 추가 하락으로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5는 이미 50을 하회하는 약한 제조업 환경을 나타내므로, 1년 경기 충격에 따른 추가 수요 둔화를 반영해 2.0포인트 낮춘 47.5를 최종 입력값으로 적용한다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에 대해 경기 충격이 지속되는 구간으로 보아 전월과 동일한 충격 강도를 적용하고, 최종 PMI 입력값을 47.5로 산정한다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에서 1년 지속 충격의 제조업 수요 둔화 효과를 반영해 2.0포인트 낮추고, 최종 입력값을 47.5로 적용한다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5가 동일하게 유지되어 있으므로, 경기 충격 기간 중 동일한 하향 폭을 적용해 47.5를 최종 입력값으로 산정한다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에 대해 경기 충격에 따른 산업 수요 약화를 반영하고, 기준 대비 2.0포인트 낮은 47.5를 최종 입력값으로 적용한다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에서 연말까지 충격이 지속되는 것으로 보아 동일한 하향 조정을 적용하고, 최종 PMI를 47.5로 산정한다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 2027년 월에는 직접 일치하는 기준 record가 없으므로, 같은 parameter의 중국 PMI 기준값 범위가 49.5로 형성된 점을 형식과 수준의 기준으로 삼고, 충격 지속 구간에 해당해 47.5를 보수적 최종 입력값으로 적용한다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "직접 기준 record는 없지만 동일 parameter의 관측 기준값 49.5를 참고하면, 1년 경기 충격이 이어지는 월로서 추가 위축을 반영한 47.5가 적절한 최종 입력값이다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "직접 일치 기준값이 없는 2027년 월이므로 같은 중국 PMI 입력값의 스케일을 참고하고, 충격 지속 기간 중 동일한 제조업 둔화 강도를 적용해 47.5로 산정한다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "기준 record가 없는 월이지만, 동일 parameter의 49.5 수준을 기준 형식으로 사용하고 경기 충격이 아직 지속되는 구간으로 보아 최종 PMI를 47.5로 적용한다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월은 1년 충격 기간에 포함되며 직접 기준 record가 없으므로 동일 parameter의 기준 수준을 참고해 2.0포인트 하향한 47.5를 최종 입력값으로 산정한다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "1년 경기 충격의 마지막 적용 월로 보고, 직접 기준 record 부재 시에도 동일 parameter의 중국 PMI 기준 수준을 참고해 최종 입력값을 47.5로 제안한다."
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
      "rationale": "강도 dimension의 ‘경기 충격’은 국가별 실질 GDP 성장률 경로를 조정해 산업·전력·가스 수요의 거시 전제를 낮추는 parameter 의미와 직접 연결된다. 기간 dimension의 ‘1년’은 2026년 하반기부터 2027년 상반기까지의 시간 범위로 해석해 연간 GDP 입력값에는 2026년과 2027년에 나누어 하방 충격을 반영하고, 국가별 기준 성장률에서 보수적으로 하향한 최종 성장률을 제안한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.0385,
          "rationale": "중국 2026년 기준 성장률 0.042에 대해 2026년 하반기 경기 충격을 연간값에 반영했다. OECD 하방 시나리오의 2026년 글로벌 성장 둔화 폭을 반년 적용하는 보수적 방식으로 0.0035를 차감해 최종 입력값을 0.0385로 산정한다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.0355,
          "rationale": "중국 2027년 기준 성장률 0.042에 대해 2027년 상반기까지 충격이 이어지는 것으로 반영했다. 2027년 하방 시나리오의 더 큰 글로벌 성장 둔화 폭을 반년 적용해 0.0065를 차감하고, 최종 입력값을 0.0355로 산정한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.0155,
          "rationale": "미국 2026년 기준 성장률 0.019에 대해 2026년 하반기 경기 충격을 연간값에 부분 반영했다. 글로벌 하방 충격을 반년 적용한 0.0035 하향 조정으로 최종 입력값을 0.0155로 산정한다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.0135,
          "rationale": "미국 2027년 기준 성장률 0.02에 대해 2027년 상반기 충격 지속을 반영했다. 2027년 글로벌 하방 시나리오의 성장 둔화 폭을 반년 적용해 0.0065를 차감하고, 최종 입력값을 0.0135로 산정한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.676 | 3.676 | 2347 | 120 | 2467 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:53.225 | 53.225 | 5304 | 3722 | 9026 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:58.810 | 58.810 | 7113 | 4001 | 11114 |

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

- 대상 scenario_ids: [305, 306]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=305 [model_parameter_agent_test] 경미한 경기 둔화와 수요 영향 제한

- target_parameter: `PMI`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:32.129 (92.129s)
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

- target_expected_parameters: `["PMI"]`
- target_selected_parameters: `["PMI"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 1 | 강도 차원의 값이 ‘경미’로 제시되어 산업 수요의 단기 심리·제조업 변동을 PMI 입력으로 점검하는 대상이다. 기간은 1개월 이하로 짧고 시나리오상 LNG 수요 영향이 거의 흡수되며 가격 영향도 중립으로 제시되어, 적용 대상 월의 PMI는 추가 충격을 크게 반영하지 않고 현 기준 경로를 유지하는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 49.5 | 해당 좌표는 선택된 중국 2026년 7월 PMI 입력 record와 직접 일치한다. 기준값 49.5에 대해 경미한 경기 영향과 1개월 이하의 짧은 기간, 수요 영향 제한 및 중립적 가격 영향을 반영하여 추가 하향 조정 없이 최종 입력값을 49.5로 유지한다. |

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
  "model_param_proposal_id": 117,
  "proposal_completed_dtm": "2026-07-07 23:49:36.992290",
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
      "rationale": "강도 차원의 값이 ‘경미’로 제시되어 산업 수요의 단기 심리·제조업 변동을 PMI 입력으로 점검하는 대상이다. 기간은 1개월 이하로 짧고 시나리오상 LNG 수요 영향이 거의 흡수되며 가격 영향도 중립으로 제시되어, 적용 대상 월의 PMI는 추가 충격을 크게 반영하지 않고 현 기준 경로를 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.5,
          "rationale": "해당 좌표는 선택된 중국 2026년 7월 PMI 입력 record와 직접 일치한다. 기준값 49.5에 대해 경미한 경기 영향과 1개월 이하의 짧은 기간, 수요 영향 제한 및 중립적 가격 영향을 반영하여 추가 하향 조정 없이 최종 입력값을 49.5로 유지한다."
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
      "rationale": "강도 차원의 값이 ‘경미’로 제시되어 국가별 거시 성장률 경로가 LNG 수요 전제에 미치는 영향을 GDP 입력으로 확인하는 대상이다. 다만 기간은 1개월 이하로 구조적 충격보다는 제한적 조정에 가까우므로, 이벤트에 명시된 국가별 2026년 성장 전망을 반영하되 변화 폭은 보수적으로 현재 연도·국가 슬롯에만 적용한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.045,
          "rationale": "해당 좌표는 선택된 중국 2026년 GDP 입력 record와 직접 일치한다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 제시되어, 기준값 0.042 대신 동일한 소수 비율 형식의 최종 입력값 0.045를 적용한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.02,
          "rationale": "해당 좌표는 선택된 미국 2026년 GDP 입력 record와 직접 일치한다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어, 기준값 0.019에서 제한적으로 상향한 동일 형식의 최종 입력값 0.02를 적용한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:07.818 | 7.818 | 2334 | 70 | 2404 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:27.691 | 27.691 | 5295 | 1738 | 7033 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:37.567 | 37.567 | 6260 | 1665 | 7925 |

##### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- target_parameter: `PMI`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:09.082 (129.082s)
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Year", "Month", "Country"]` | `["PMI"]` | 12 | 강도 dimension의 ‘경기 충격’은 제조업 심리와 산업 수요의 단기 둔화를 PMI 조정으로 반영하는 parameter 의미와 직접 연결된다. 기간 dimension의 ‘1년’은 공통 시간 맥락으로 사용해 2026년 7월부터 2027년 6월까지 중국 PMI를 일관되게 하향 조정하되, 기준값이 이미 위축 국면에 가까운 점을 감안해 보수적인 추가 하락으로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 47.5 | 해당 월 중국 PMI 기준값 49.5는 이미 50을 하회하는 약한 제조업 환경을 나타내므로, 1년 경기 충격에 따른 추가 수요 둔화를 반영해 2.0포인트 낮춘 47.5를 최종 입력값으로 적용한다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 49.5 | 47.5 | 해당 월 중국 PMI 기준값 49.5에 대해 경기 충격이 지속되는 구간으로 보아 전월과 동일한 충격 강도를 적용하고, 최종 PMI 입력값을 47.5로 산정한다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 49.5 | 47.5 | 해당 월 중국 PMI 기준값 49.5에서 1년 지속 충격의 제조업 수요 둔화 효과를 반영해 2.0포인트 낮추고, 최종 입력값을 47.5로 적용한다. |
| 4 | `{"Country": "China", "Month": 10, "Year": 2026}` | 49.5 | 47.5 | 해당 월 중국 PMI 기준값 49.5가 동일하게 유지되어 있으므로, 경기 충격 기간 중 동일한 하향 폭을 적용해 47.5를 최종 입력값으로 산정한다. |
| 5 | `{"Country": "China", "Month": 11, "Year": 2026}` | 49.5 | 47.5 | 해당 월 중국 PMI 기준값 49.5에 대해 경기 충격에 따른 산업 수요 약화를 반영하고, 기준 대비 2.0포인트 낮은 47.5를 최종 입력값으로 적용한다. |
| 6 | `{"Country": "China", "Month": 12, "Year": 2026}` | 49.5 | 47.5 | 해당 월 중국 PMI 기준값 49.5에서 연말까지 충격이 지속되는 것으로 보아 동일한 하향 조정을 적용하고, 최종 PMI를 47.5로 산정한다. |
| 7 | `{"Country": "China", "Month": 1, "Year": 2027}` | null | 47.5 | 해당 2027년 월에는 직접 일치하는 기준 record가 없으므로, 같은 parameter의 중국 PMI 기준값 범위가 49.5로 형성된 점을 형식과 수준의 기준으로 삼고, 충격 지속 구간에 해당해 47.5를 보수적 최종 입력값으로 적용한다. |
| 8 | `{"Country": "China", "Month": 2, "Year": 2027}` | null | 47.5 | 직접 기준 record는 없지만 동일 parameter의 관측 기준값 49.5를 참고하면, 1년 경기 충격이 이어지는 월로서 추가 위축을 반영한 47.5가 적절한 최종 입력값이다. |
| 9 | `{"Country": "China", "Month": 3, "Year": 2027}` | null | 47.5 | 직접 일치 기준값이 없는 2027년 월이므로 같은 중국 PMI 입력값의 스케일을 참고하고, 충격 지속 기간 중 동일한 제조업 둔화 강도를 적용해 47.5로 산정한다. |
| 10 | `{"Country": "China", "Month": 4, "Year": 2027}` | null | 47.5 | 기준 record가 없는 월이지만, 동일 parameter의 49.5 수준을 기준 형식으로 사용하고 경기 충격이 아직 지속되는 구간으로 보아 최종 PMI를 47.5로 적용한다. |
| 11 | `{"Country": "China", "Month": 5, "Year": 2027}` | null | 47.5 | 해당 월은 1년 충격 기간에 포함되며 직접 기준 record가 없으므로 동일 parameter의 기준 수준을 참고해 2.0포인트 하향한 47.5를 최종 입력값으로 산정한다. |
| 12 | `{"Country": "China", "Month": 6, "Year": 2027}` | null | 47.5 | 1년 경기 충격의 마지막 적용 월로 보고, 직접 기준 record 부재 시에도 동일 parameter의 중국 PMI 기준 수준을 참고해 최종 입력값을 47.5로 제안한다. |

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
  "model_param_proposal_id": 118,
  "proposal_completed_dtm": "2026-07-07 23:50:58.781118",
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
      "rationale": "강도 dimension의 ‘경기 충격’은 제조업 심리와 산업 수요의 단기 둔화를 PMI 조정으로 반영하는 parameter 의미와 직접 연결된다. 기간 dimension의 ‘1년’은 공통 시간 맥락으로 사용해 2026년 7월부터 2027년 6월까지 중국 PMI를 일관되게 하향 조정하되, 기준값이 이미 위축 국면에 가까운 점을 감안해 보수적인 추가 하락으로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5는 이미 50을 하회하는 약한 제조업 환경을 나타내므로, 1년 경기 충격에 따른 추가 수요 둔화를 반영해 2.0포인트 낮춘 47.5를 최종 입력값으로 적용한다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에 대해 경기 충격이 지속되는 구간으로 보아 전월과 동일한 충격 강도를 적용하고, 최종 PMI 입력값을 47.5로 산정한다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에서 1년 지속 충격의 제조업 수요 둔화 효과를 반영해 2.0포인트 낮추고, 최종 입력값을 47.5로 적용한다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5가 동일하게 유지되어 있으므로, 경기 충격 기간 중 동일한 하향 폭을 적용해 47.5를 최종 입력값으로 산정한다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에 대해 경기 충격에 따른 산업 수요 약화를 반영하고, 기준 대비 2.0포인트 낮은 47.5를 최종 입력값으로 적용한다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 47.5,
          "rationale": "해당 월 중국 PMI 기준값 49.5에서 연말까지 충격이 지속되는 것으로 보아 동일한 하향 조정을 적용하고, 최종 PMI를 47.5로 산정한다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 2027년 월에는 직접 일치하는 기준 record가 없으므로, 같은 parameter의 중국 PMI 기준값 범위가 49.5로 형성된 점을 형식과 수준의 기준으로 삼고, 충격 지속 구간에 해당해 47.5를 보수적 최종 입력값으로 적용한다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "직접 기준 record는 없지만 동일 parameter의 관측 기준값 49.5를 참고하면, 1년 경기 충격이 이어지는 월로서 추가 위축을 반영한 47.5가 적절한 최종 입력값이다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "직접 일치 기준값이 없는 2027년 월이므로 같은 중국 PMI 입력값의 스케일을 참고하고, 충격 지속 기간 중 동일한 제조업 둔화 강도를 적용해 47.5로 산정한다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "기준 record가 없는 월이지만, 동일 parameter의 49.5 수준을 기준 형식으로 사용하고 경기 충격이 아직 지속되는 구간으로 보아 최종 PMI를 47.5로 적용한다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "해당 월은 1년 충격 기간에 포함되며 직접 기준 record가 없으므로 동일 parameter의 기준 수준을 참고해 2.0포인트 하향한 47.5를 최종 입력값으로 산정한다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 47.5,
          "rationale": "1년 경기 충격의 마지막 적용 월로 보고, 직접 기준 record 부재 시에도 동일 parameter의 중국 PMI 기준 수준을 참고해 최종 입력값을 47.5로 제안한다."
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
      "rationale": "강도 dimension의 ‘경기 충격’은 국가별 실질 GDP 성장률 경로를 조정해 산업·전력·가스 수요의 거시 전제를 낮추는 parameter 의미와 직접 연결된다. 기간 dimension의 ‘1년’은 2026년 하반기부터 2027년 상반기까지의 시간 범위로 해석해 연간 GDP 입력값에는 2026년과 2027년에 나누어 하방 충격을 반영하고, 국가별 기준 성장률에서 보수적으로 하향한 최종 성장률을 제안한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.0385,
          "rationale": "중국 2026년 기준 성장률 0.042에 대해 2026년 하반기 경기 충격을 연간값에 반영했다. OECD 하방 시나리오의 2026년 글로벌 성장 둔화 폭을 반년 적용하는 보수적 방식으로 0.0035를 차감해 최종 입력값을 0.0385로 산정한다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.0355,
          "rationale": "중국 2027년 기준 성장률 0.042에 대해 2027년 상반기까지 충격이 이어지는 것으로 반영했다. 2027년 하방 시나리오의 더 큰 글로벌 성장 둔화 폭을 반년 적용해 0.0065를 차감하고, 최종 입력값을 0.0355로 산정한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.0155,
          "rationale": "미국 2026년 기준 성장률 0.019에 대해 2026년 하반기 경기 충격을 연간값에 부분 반영했다. 글로벌 하방 충격을 반년 적용한 0.0035 하향 조정으로 최종 입력값을 0.0155로 산정한다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.0135,
          "rationale": "미국 2027년 기준 성장률 0.02에 대해 2027년 상반기 충격 지속을 반영했다. 2027년 글로벌 하방 시나리오의 성장 둔화 폭을 반년 적용해 0.0065를 차감하고, 최종 입력값을 0.0135로 산정한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.676 | 3.676 | 2347 | 120 | 2467 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:53.225 | 53.225 | 5304 | 3722 | 9026 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:58.810 | 58.810 | 7113 | 4001 | 11114 |

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
      "comment": "흡수분만큼 타 source 비중으로 이전 : 감소한 발전원을 대체 가능한 전원 믹스의 정책·가용성 제약에 따라 Gas/Coal/Renewable/Nuclear 비중에 재배분",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "발전부문 가스 비중 조정(capa GW→비중 환산) : 발전소 가동률·용량 변화가 LNG 수요에 미치는 영향을 PowerMix의 Gas 비중 변화로 환산",
      "dimension": "capacity_change_scale (Capacity 변화 규모)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "발전부문 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영",
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

- 대상 scenario_ids: [287, 288]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=287 [model_parameter_agent_test] 단기 소규모 발전 차질 흡수

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:33.478 (93.478s)
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
| Step2 slot axis value 수 | `{"parameter|5|demand|powermixadjustment|powermix": {"Year": 6}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모가 1 GW 미만이므로 발전부문 가스 비중 조정 대상이 되지만, 타 에너지원 흡수 가능성이 100%로 제시되어 감소·변동분이 가스 수요로 전이될 여지가 제한적입니다. 영향 기간도 1개월 이하의 단발적 사건이고 회복이 급격하므로 연간 PowerMix에는 구조적 조정보다는 중립적 유지 방향을 적용합니다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | [0.0346, 0.323, 0.285, 0.474, 0.135, 0.042, 0.434, 0.213, 0.31818965517241377, 0.19, 0.29] | 0.285 | 해당 좌표에 직접 일치하는 기준값이 없어 같은 PowerMix Gas 항목의 2026년 국가별 입력값들을 단위와 스케일 참고용으로 사용했습니다. 2026년 제공 값들의 중앙값인 0.285를 보수적 기준값으로 두고, 1개월 이하·1 GW 미만·100% 대체 흡수로 연간 가스 비중에 추가 충격을 반영하지 않아 최종값도 0.285로 유지했습니다. |

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
  "model_param_proposal_id": 93,
  "proposal_completed_dtm": "2026-07-07 23:34:17.534183",
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
      "rationale": "Capacity 변화 규모가 1 GW 미만이므로 발전부문 가스 비중 조정 대상이 되지만, 타 에너지원 흡수 가능성이 100%로 제시되어 감소·변동분이 가스 수요로 전이될 여지가 제한적입니다. 영향 기간도 1개월 이하의 단발적 사건이고 회복이 급격하므로 연간 PowerMix에는 구조적 조정보다는 중립적 유지 방향을 적용합니다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": [
            0.0346,
            0.323,
            0.285,
            0.474,
            0.135,
            0.042,
            0.434,
            0.213,
            0.31818965517241377,
            0.19,
            0.29
          ],
          "proposedValue": 0.285,
          "rationale": "해당 좌표에 직접 일치하는 기준값이 없어 같은 PowerMix Gas 항목의 2026년 국가별 입력값들을 단위와 스케일 참고용으로 사용했습니다. 2026년 제공 값들의 중앙값인 0.285를 보수적 기준값으로 두고, 1개월 이하·1 GW 미만·100% 대체 흡수로 연간 가스 비중에 추가 충격을 반영하지 않아 최종값도 0.285로 유지했습니다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.487 | 3.487 | 2778 | 117 | 2895 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:15.659 | 15.659 | 6020 | 848 | 6868 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:02.821 | 62.821 | 7776 | 1878 | 9654 |

##### scenario_id=288 [model_parameter_agent_test] 6개월 대규모 발전 차질 절반만 흡수

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:11.043 (71.043s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모는 발전부문 용량·이용률 변동을 Gas 발전 비중으로 환산해야 하는 직접 근거이며, 타 에너지원 흡수 가능성은 차질분 중 비가스 전원이 흡수하는 몫을 제한해 Gas 비중 조정폭을 완화하는 역할을 한다. 6개월 영향과 급격한 발생, 점진적 회복은 2026년 연간 입력에 보수적으로 반영하되, 대체 흡수가 절반에 그치는 점을 고려해 Gas 비중을 소폭 상향하는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.44 | 선택된 입력 좌표는 2026년 미국 Gas PowerMix이다. 해당 좌표의 기준값은 제공되지 않아 같은 PowerMix 입력의 Gas 비중 범위와 소수 형식을 참고했고, 3~5GW 규모 차질 중 50%가 타 에너지원으로 흡수되는 조건을 6개월 연간화 영향으로 보수적으로 축소해 약 0.5%p 수준의 Gas 비중 상향을 반영한 최종 입력값 0.44로 산정했다. |

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
  "model_param_proposal_id": 94,
  "proposal_completed_dtm": "2026-07-07 23:34:32.669850",
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
      "rationale": "Capacity 변화 규모는 발전부문 용량·이용률 변동을 Gas 발전 비중으로 환산해야 하는 직접 근거이며, 타 에너지원 흡수 가능성은 차질분 중 비가스 전원이 흡수하는 몫을 제한해 Gas 비중 조정폭을 완화하는 역할을 한다. 6개월 영향과 급격한 발생, 점진적 회복은 2026년 연간 입력에 보수적으로 반영하되, 대체 흡수가 절반에 그치는 점을 고려해 Gas 비중을 소폭 상향하는 구조로 제안한다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.44,
          "rationale": "선택된 입력 좌표는 2026년 미국 Gas PowerMix이다. 해당 좌표의 기준값은 제공되지 않아 같은 PowerMix 입력의 Gas 비중 범위와 소수 형식을 참고했고, 3~5GW 규모 차질 중 50%가 타 에너지원으로 흡수되는 조건을 6개월 연간화 영향으로 보수적으로 축소해 약 0.5%p 수준의 Gas 비중 상향을 반영한 최종 입력값 0.44로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.543 | 3.543 | 2796 | 102 | 2898 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:10.877 | 10.877 | 6035 | 572 | 6607 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:43.883 | 43.883 | 7791 | 2403 | 10194 |

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
      "comment": "기온 직접 입력(대안 경로) : 한파 영향 국가·월의 Temperature를 하향 조정하고, 강도에 따라 평년 대비 온도 편차를 월별로 차등 적용",
      "dimension": "cold_wave_intensity (한파 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 -℃ → HDD(난방도일) 변환 입력 : HDD는 미대상 파라미터이므로 직접 조정하지 않고, 한파 강도는 Temperature 하향 또는 강도·월 분배 판단 근거로만 사용",
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

- 대상 scenario_ids: [289, 290]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=289 [model_parameter_agent_test] 짧은 약한 한파와 전원 흡수

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: NO
- 소요시간: 01:49.127 (109.127s)
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

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `[]`
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
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

- 제안 파라미터 없음.

###### Proposed Parameter Values

- 제안 value 없음.

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
  "model_param_proposal_id": 95,
  "proposal_completed_dtm": "2026-07-07 23:35:47.339484",
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
      "rationale": "한파 강도 dimension이 기온 직접 입력의 하향 조정과 연결되므로, 영향 국가·월의 Temperature를 낮추는 방식으로 반영한다. 기간은 1개월 이하이고 단발 피크 성격이므로 적용 범위는 이벤트가 명시된 월의 미국 월간 기온 슬롯으로 제한하며, 재고 여유는 수급 완화 맥락으로만 보아 기온 입력 자체를 추가로 보정하지 않는다.",
      "values": [
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2026,
          "basecaseValue": [
            10.4,
            9.2,
            5.4,
            4.9,
            8.5,
            6.4,
            11.3,
            10.2,
            6.7,
            6.7
          ],
          "proposedValue": 5.5,
          "rationale": "선택 좌표에 미국 2026년 3월 직접 기준값이 없어 제공된 2026년 3월 국가별 Temperature 기준값의 평균 수준인 약 8.0℃를 같은 형식의 보수적 기준으로 사용했다. 약한 한파 강도인 -2~-3℃ 범위의 중앙값 2.5℃ 하향을 적용해 최종 월간 기온 입력값을 5.5℃로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.456 | 4.456 | 2396 | 121 | 2517 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:11.763 | 11.763 | 5917 | 661 | 6578 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:19.532 | 79.532 | 7572 | 2716 | 10288 |

##### scenario_id=290 [model_parameter_agent_test] 3개월 강한 한파와 대체 제한

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 03:00.635 (180.635s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 dimension은 발전 믹스에서 가스 외 에너지원이 추가 전력 수요를 얼마나 대체할 수 있는지를 나타내므로 PowerMix의 Gas 비중 조정과 직접 연결된다. 흡수 가능성이 낮은 편이어서 한파에 따른 전력 수요 증가분의 상당 부분이 가스 발전으로 남는 방향을 반영하되, 3개월 충격이 연간 비중 입력에 반영되는 점을 고려해 연간 Gas share는 제한적으로 상향 조정한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Energy Source": "Gas", "Year": 2026}` | null | 0.45 | 해당 미국 Gas 발전 비중 좌표에는 일치하는 기준값이 없어, 제공된 다른 국가의 Gas share 값은 단위가 0~1 비율 형식임을 확인하는 용도로만 참고했다. 타 에너지원 흡수 가능성이 25%로 낮아 추가 전력 수요의 대부분이 가스 발전에 남는다고 보되, 3개월 한파가 연간 발전 믹스에 미치는 효과를 연간화하여 최종 Gas 비중을 0.45로 제안한다. |

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
  "model_param_proposal_id": 98,
  "proposal_completed_dtm": "2026-07-07 23:37:18.182425",
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
      "rationale": "한파 강도 dimension은 국가·월별 기온 입력값을 직접 낮추는 parameter 의미와 연결되며, 강한 한파는 난방 수요 확대를 반영하기 위해 Temperature 하향 조정으로 해석된다. 기간과 지속 피크 정보는 선택된 3개월 구간에 한파 영향이 완만히 분산되지 않고 지속 적용되는 구조로 반영하되, 재고 부족 정보는 수치 강도 산정이 아니라 수급 긴장 맥락으로만 참고했다.",
      "values": [
        {
          "Country": "United States",
          "Month": 1,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -4.5,
          "rationale": "해당 미국 월 좌표에는 일치하는 기준값이 없어, 제공된 다른 국가들의 월별 °C 입력 형식과 계절 패턴만 참고했다. 강한 한파를 평년 대비 약 5℃ 내외의 하향 충격으로 보수적으로 반영하되 겨울철 계절성을 유지하여 최종 기온을 -4.5℃로 제안한다."
        },
        {
          "Country": "United States",
          "Month": 2,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -3,
          "rationale": "해당 미국 월 좌표에는 일치하는 기준값이 없어, 제공된 월별 기온 값의 스케일과 소수 형식만 참고했다. 3개월 지속 피크 조건에 따라 전월과 유사한 강한 하향 충격을 유지하되 월별 계절 상승을 일부 반영하여 최종 기온을 -3.0℃로 제안한다."
        },
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.5,
          "rationale": "해당 미국 월 좌표에는 일치하는 기준값이 없어, 다른 국가의 3월 기온 범위는 형식과 계절성 참고용으로만 사용했다. 이벤트가 3월 중순 한파 전망을 포함하고 시나리오가 3개월 지속을 가정하므로 강한 하향 충격을 계속 적용하되 봄철 전환 효과를 일부 남겨 최종 기온을 0.5℃로 제안한다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension은 발전 믹스에서 가스 외 에너지원이 추가 전력 수요를 얼마나 대체할 수 있는지를 나타내므로 PowerMix의 Gas 비중 조정과 직접 연결된다. 흡수 가능성이 낮은 편이어서 한파에 따른 전력 수요 증가분의 상당 부분이 가스 발전으로 남는 방향을 반영하되, 3개월 충격이 연간 비중 입력에 반영되는 점을 고려해 연간 Gas share는 제한적으로 상향 조정한다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 미국 Gas 발전 비중 좌표에는 일치하는 기준값이 없어, 제공된 다른 국가의 Gas share 값은 단위가 0~1 비율 형식임을 확인하는 용도로만 참고했다. 타 에너지원 흡수 가능성이 25%로 낮아 추가 전력 수요의 대부분이 가스 발전에 남는다고 보되, 3개월 한파가 연간 발전 믹스에 미치는 효과를 연간화하여 최종 Gas 비중을 0.45로 제안한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:17.123 | 17.123 | 2389 | 109 | 2498 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:55.057 | 55.057 | 5906 | 3167 | 9073 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:34.112 | 94.112 | 7637 | 3223 | 10860 |

#### event_type_l2_id=6 겨울 한파

##### Scenario Group

```json
{
  "description": "유럽 한파 이벤트에 대해 기간/강도/재고/대체 흡수 조합을 확장해 생성한 테스트 scenario group",
  "dimension_selected": [
    "period",
    "cold_wave_intensity",
    "entry_gas_inventory",
    "peak_timing_pattern",
    "alt_energy_absorption"
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
  "mi_event_id": 1378,
  "request_usr_id": null,
  "scenario_count": 4,
  "scenario_group_id": 61,
  "stage": "scenario_created",
  "status": "created",
  "summary": "최근 한파/폭염 이벤트 기반 수급모델 파라미터 제안 확장 테스트",
  "title": "[model_parameter_agent_weather_ext_20260630] 한파 이벤트 1378 수급모델 파라미터 테스트"
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
      "comment": "기온 직접 입력(대안 경로) : 한파 영향 국가·월의 Temperature를 하향 조정하고, 강도에 따라 평년 대비 온도 편차를 월별로 차등 적용",
      "dimension": "cold_wave_intensity (한파 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 -℃ → HDD(난방도일) 변환 입력 : HDD는 미대상 파라미터이므로 직접 조정하지 않고, 한파 강도는 Temperature 하향 또는 강도·월 분배 판단 근거로만 사용",
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
  "created_at": "2026-06-21T00:42:17.070147",
  "detail_analysis": "사건 요약:\nWoodMac weekly summary가 2026년 5월 14일 글로벌 가스·LNG 시장에서 유럽 한파에 따른 수요 증가를 가격 상승 요인으로 언급함. 직전 요약의 유럽 전역 이례적 한파에 따른 난방 수요 증가 흐름이 신규 리포트에서도 재확인됨. 신규 Record에는 아시아 현물 조달 확대와 북미 LNG 설비 정비도 함께 언급됐으나, 본 Event Type은 수요 > 겨울 한파이므로 핵심 사건은 유럽 한파 수요 증가로 한정됨.\n\n영향 경로:\n유럽 한파는 주거·상업 난방 수요를 확대해 천연가스 소비 증가로 연결되는 요인임. 가스 수요 증가는 저장 재고 소진 속도와 LNG 수입 필요성을 높이는 경로로 작용할 수 있음. 신규 리포트상 글로벌 가격 상승 구도에는 아시아 현물 조달 확대와 북미 LNG 설비 정비도 포함되나, 이는 본 Event의 직접 원인이 아니라 동시 발생한 별도 수급 요인임.\n\n시장 반응:\nWoodMac weekly summary는 2026년 5월 14일 유럽 한파 수요 증가와 다른 수급 요인이 동시에 가격을 끌어올리는 구도라고 평가함. 유럽 가스 수요 증가는 TTF 계약 가격 상승 압력과 겨울 프리미엄 지지 요인으로 반영됨. Record에 구체적인 가격 Band나 Forward 수치는 제시되지 않음.\n\nLNG 시장 관점:\n유럽 한파는 LNG 설비 이슈가 아니라 가스 소비 증가를 통한 수요 측 Event임. 난방 수요 확대는 유럽의 LNG 현물 흡수 여력과 조달 필요성을 높일 수 있음. 같은 시점의 아시아 현물 조달 확대와 결합될 경우 유럽과 아시아 간 카고 경쟁 및 글로벌 LNG 가격 지지 압력으로 연결될 수 있음.",
  "event_title_ko": "유럽 한파로 가스 수요 증가",
  "event_type_l2_id": 6,
  "key_bullets": [],
  "latest_record_first_created": "2026-05-14T00:00:00",
  "mi_event_id": "1378",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[유럽 난방수요] 5월 14일 WoodMac이 한파 수요 증가 언급 → TTF 가격 지지",
  "source_mi_record_ids": [
    2235
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [307, 308]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=307 [model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 한파

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:56.326 (116.326s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "alt_energy_absorption": "100%",
    "cold_wave_intensity": "-2~-3℃: 약",
    "entry_gas_inventory": "+20%↑ (매우 여유)",
    "peak_timing_pattern": "12월 Peak",
    "period": "1개월 이하"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "neutral",
    "ttf": "up"
  },
  "narrative": "이벤트 1378 기반 확장 테스트 시나리오입니다. 기간=1개월 이하, 강도=-2~-3℃: 약, 대체흡수=100% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 25.0,
  "scenario_group_id": 61,
  "scenario_id": 307,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 한파"
}
```

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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
| Step2 selected slot | 14 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=14, basecaseValue_present=14 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 7 | 타 에너지원 흡수 가능성 dimension은 발전 믹스에서 가스 발전 비중을 조정할 수 있는 경로와 직접 연결된다. 흡수 가능성이 100%로 제시되어 단기 한파에 따른 추가 에너지 수요가 비가스 전원으로 완전히 흡수되는 설정이므로, 연간 Gas 발전 비중은 기준값을 유지하는 방식으로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.19 | Belgium 2026년 Gas 발전 비중의 기준값은 0.19이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.19를 최종 입력값으로 유지했다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.042 | France 2026년 Gas 발전 비중의 기준값은 0.042이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.042를 최종 입력값으로 유지했다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.135 | Germany 2026년 Gas 발전 비중의 기준값은 0.135이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.135를 최종 입력값으로 유지했다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.434 | Italy 2026년 Gas 발전 비중의 기준값은 0.434이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.434를 최종 입력값으로 유지했다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.31818965517241377 | Netherlands 2026년 Gas 발전 비중의 기준값은 0.31818965517241377이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.31818965517241377을 최종 입력값으로 유지했다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.213 | Spain 2026년 Gas 발전 비중의 기준값은 0.213이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.213을 최종 입력값으로 유지했다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.29 | United Kingdom 2026년 Gas 발전 비중의 기준값은 0.29이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.29를 최종 입력값으로 유지했다. |

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
  "mi_event_id": 1378,
  "model_param_proposal_id": 96,
  "proposal_completed_dtm": "2026-07-07 23:36:29.197548",
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
      "rationale": "한파 강도 dimension이 국가·월별 기온 입력값을 직접 낮추는 경로와 연결되므로 Temperature 조정 대상으로 선택한다. 기간은 1개월 이하이고 피크 패턴은 12월로 제시되어 2026년 12월의 선택 국가에 한정해 약한 한파에 해당하는 보수적 하향 편차를 적용한다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 3.5,
          "proposedValue": 1,
          "rationale": "Belgium 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 3.5°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 1.0°C로 산정했다."
        },
        {
          "Country": "France",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 5.1,
          "proposedValue": 2.6,
          "rationale": "France 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 5.1°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 2.6°C로 산정했다."
        },
        {
          "Country": "Germany",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 1.2,
          "proposedValue": -1.3,
          "rationale": "Germany 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 1.2°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 -1.3°C로 산정했다."
        },
        {
          "Country": "Italy",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 6.8,
          "proposedValue": 4.3,
          "rationale": "Italy 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 6.8°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 4.3°C로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 3.7,
          "proposedValue": 1.2,
          "rationale": "Netherlands 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 3.7°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 1.2°C로 산정했다."
        },
        {
          "Country": "Spain",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 7.9,
          "proposedValue": 5.4,
          "rationale": "Spain 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 7.9°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 5.4°C로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 4.8,
          "proposedValue": 2.3,
          "rationale": "United Kingdom 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 4.8°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 2.3°C로 산정했다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension은 발전 믹스에서 가스 발전 비중을 조정할 수 있는 경로와 직접 연결된다. 흡수 가능성이 100%로 제시되어 단기 한파에 따른 추가 에너지 수요가 비가스 전원으로 완전히 흡수되는 설정이므로, 연간 Gas 발전 비중은 기준값을 유지하는 방식으로 제안한다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19,
          "rationale": "Belgium 2026년 Gas 발전 비중의 기준값은 0.19이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.19를 최종 입력값으로 유지했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "France 2026년 Gas 발전 비중의 기준값은 0.042이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.042를 최종 입력값으로 유지했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.135,
          "rationale": "Germany 2026년 Gas 발전 비중의 기준값은 0.135이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.135를 최종 입력값으로 유지했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.434,
          "rationale": "Italy 2026년 Gas 발전 비중의 기준값은 0.434이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.434를 최종 입력값으로 유지했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.31818965517241377,
          "rationale": "Netherlands 2026년 Gas 발전 비중의 기준값은 0.31818965517241377이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.31818965517241377을 최종 입력값으로 유지했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.213,
          "rationale": "Spain 2026년 Gas 발전 비중의 기준값은 0.213이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.213을 최종 입력값으로 유지했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29,
          "rationale": "United Kingdom 2026년 Gas 발전 비중의 기준값은 0.29이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.29를 최종 입력값으로 유지했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 61,
  "scenario_id": 307,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.723 | 3.723 | 2313 | 126 | 2439 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:24.394 | 24.394 | 5830 | 1831 | 7661 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:06.499 | 66.499 | 7939 | 3057 | 10996 |

##### scenario_id=308 [model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 한파

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:18.354 (138.354s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "50%",
    "cold_wave_intensity": "-3~-5℃: 중",
    "entry_gas_inventory": "±5% (정상)",
    "peak_timing_pattern": "1월 Peak",
    "period": "3개월"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "up",
    "ttf": "up"
  },
  "narrative": "이벤트 1378 기반 확장 테스트 시나리오입니다. 기간=3개월, 강도=-3~-5℃: 중, 대체흡수=50% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 25.0,
  "scenario_group_id": 61,
  "scenario_id": 308,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 한파"
}
```

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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
| Step2 selected slot | 28 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=28, basecaseValue_present=28 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 7 | 타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 입력과 직접 연결되며, 50% 흡수 조건은 한파로 늘어나는 전력·난방 관련 부담 중 일부가 석탄·석유 등 비가스 에너지원으로 완화됨을 의미합니다. 다만 한파 이벤트는 TTF 상승 방향의 가스 수요 요인이므로, 3개월 충격을 연간 Gas 발전 비중에 보수적으로 반영해 기준 Gas share를 소폭 상향하는 구조로 제안합니다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2027}` | 0.18 | 0.1845 | 2027년 Belgium Gas 발전 비중 기준값 0.18에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.1845로 산정했습니다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2027}` | 0.034 | 0.03485 | 2027년 France Gas 발전 비중 기준값 0.034에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.03485로 산정했습니다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2027}` | 0.13 | 0.13325 | 2027년 Germany Gas 발전 비중 기준값 0.13에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.13325로 산정했습니다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2027}` | 0.422 | 0.43255 | 2027년 Italy Gas 발전 비중 기준값 0.422에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.43255로 산정했습니다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2027}` | 0.33707317073170734 | 0.3455 | 2027년 Netherlands Gas 발전 비중 기준값 0.33707317073170734에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.3455로 산정했습니다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2027}` | 0.211 | 0.216275 | 2027년 Spain Gas 발전 비중 기준값 0.211에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.216275로 산정했습니다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2027}` | 0.29 | 0.29725 | 2027년 United Kingdom Gas 발전 비중 기준값 0.29에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.29725로 산정했습니다. |

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
  "mi_event_id": 1378,
  "model_param_proposal_id": 99,
  "proposal_completed_dtm": "2026-07-07 23:38:05.691792",
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
      "rationale": "한파 강도 차원이 Temperature의 국가·월별 기온 직접 입력과 연결되므로, 유럽 한파에 따른 난방수요 증가를 기온 하향 조정으로 반영합니다. 기간은 3개월이고 1월 Peak 패턴이므로 2027년 1~3월에 적용하되 1월에 가장 큰 하향, 이후 점진 완화로 배분하며, 재고는 정상 범위이므로 추가 증폭은 적용하지 않습니다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 3.5,
          "proposedValue": -1.5,
          "rationale": "2027년 1월 Belgium 기준 기온 3.5°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -1.5°C로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 4.3,
          "proposedValue": 0.3,
          "rationale": "2027년 2월 Belgium 기준 기온 4.3°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 0.3°C로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 6.7,
          "proposedValue": 3.7,
          "rationale": "2027년 3월 Belgium 기준 기온 6.7°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.7°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 5.1,
          "proposedValue": 0.1,
          "rationale": "2027년 1월 France 기준 기온 5.1°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 0.1°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 5.9,
          "proposedValue": 1.9,
          "rationale": "2027년 2월 France 기준 기온 5.9°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 1.9°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 8.5,
          "proposedValue": 5.5,
          "rationale": "2027년 3월 France 기준 기온 8.5°C에 3개월 한파의 말월 편차 -3°C를 적용해 5.5°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 1.2,
          "proposedValue": -3.8,
          "rationale": "2027년 1월 Germany 기준 기온 1.2°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -3.8°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 2.3,
          "proposedValue": -1.7,
          "rationale": "2027년 2월 Germany 기준 기온 2.3°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 -1.7°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 4.9,
          "proposedValue": 1.9,
          "rationale": "2027년 3월 Germany 기준 기온 4.9°C에 3개월 한파의 말월 편차 -3°C를 적용해 1.9°C로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 6.8,
          "proposedValue": 1.8,
          "rationale": "2027년 1월 Italy 기준 기온 6.8°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 1.8°C로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 7.7,
          "proposedValue": 3.7,
          "rationale": "2027년 2월 Italy 기준 기온 7.7°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 3.7°C로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 10.2,
          "proposedValue": 7.2,
          "rationale": "2027년 3월 Italy 기준 기온 10.2°C에 3개월 한파의 말월 편차 -3°C를 적용해 7.2°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 3.7,
          "proposedValue": -1.3,
          "rationale": "2027년 1월 Netherlands 기준 기온 3.7°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -1.3°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 4.4,
          "proposedValue": 0.4,
          "rationale": "2027년 2월 Netherlands 기준 기온 4.4°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 0.4°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 6.4,
          "proposedValue": 3.4,
          "rationale": "2027년 3월 Netherlands 기준 기온 6.4°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.4°C로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 7.9,
          "proposedValue": 2.9,
          "rationale": "2027년 1월 Spain 기준 기온 7.9°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 2.9°C로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 9,
          "proposedValue": 5,
          "rationale": "2027년 2월 Spain 기준 기온 9.0°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 5.0°C로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 11.3,
          "proposedValue": 8.3,
          "rationale": "2027년 3월 Spain 기준 기온 11.3°C에 3개월 한파의 말월 편차 -3°C를 적용해 8.3°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 4.8,
          "proposedValue": -0.2,
          "rationale": "2027년 1월 United Kingdom 기준 기온 4.8°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -0.2°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 5.2,
          "proposedValue": 1.2,
          "rationale": "2027년 2월 United Kingdom 기준 기온 5.2°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 1.2°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 6.7,
          "proposedValue": 3.7,
          "rationale": "2027년 3월 United Kingdom 기준 기온 6.7°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.7°C로 산정했습니다."
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
      "rationale": "타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 입력과 직접 연결되며, 50% 흡수 조건은 한파로 늘어나는 전력·난방 관련 부담 중 일부가 석탄·석유 등 비가스 에너지원으로 완화됨을 의미합니다. 다만 한파 이벤트는 TTF 상승 방향의 가스 수요 요인이므로, 3개월 충격을 연간 Gas 발전 비중에 보수적으로 반영해 기준 Gas share를 소폭 상향하는 구조로 제안합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1845,
          "rationale": "2027년 Belgium Gas 발전 비중 기준값 0.18에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.1845로 산정했습니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03485,
          "rationale": "2027년 France Gas 발전 비중 기준값 0.034에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.03485로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.13325,
          "rationale": "2027년 Germany Gas 발전 비중 기준값 0.13에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.13325로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.43255,
          "rationale": "2027년 Italy Gas 발전 비중 기준값 0.422에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.43255로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.3455,
          "rationale": "2027년 Netherlands Gas 발전 비중 기준값 0.33707317073170734에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.3455로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.216275,
          "rationale": "2027년 Spain Gas 발전 비중 기준값 0.211에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.216275로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.29725,
          "rationale": "2027년 United Kingdom Gas 발전 비중 기준값 0.29에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.29725로 산정했습니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 61,
  "scenario_id": 308,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.619 | 3.619 | 2314 | 124 | 2438 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:33.520 | 33.520 | 5819 | 3013 | 8832 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:28.032 | 88.032 | 8452 | 4668 | 13120 |

#### event_type_l2_id=7 여름 폭염

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "재생E·원전 등 흡수",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "재고는 수급모델 input 아님 — 해석 맥락",
      "dimension": "entry_gas_inventory (진입 시점 가스 재고 (평년 대비))",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "기온 직접 입력(대안 경로) : 폭염 영향 국가·월의 Temperature를 상향 조정하고, 냉방 수요 피크 월에 더 큰 조정폭을 적용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 +℃ → CDD(냉방도일) 변환 입력 : CDD는 미대상 파라미터이므로 직접 조정하지 않고, 폭염 강도는 Temperature 상향 또는 강도·월 분배 판단 근거로만 사용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "재고 회복 속도 = 재고 개념 — 수급모델 input 아님(맥락)",
      "dimension": "injection_pattern (Injection 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "월별 분배",
      "dimension": "peak_timing_pattern (Peak 시점, 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "하절기 월 슬롯(동남아·인도 4~5월 포함)",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [291, 292]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=291 [model_parameter_agent_test] 짧은 약한 폭염과 전원 흡수

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:44.862 (104.862s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 2 | 타 에너지원 흡수 가능성 dimension의 '100%'는 재생에너지·원전 등 비가스 전원이 냉방 수요 증가분을 흡수할 수 있음을 의미하며, PowerMix의 Gas 발전 비중 조정 여부와 직접 연결됩니다. 약한 단기 폭염과 충분한 전원 흡수, 중립적 가격 영향이 함께 제시되어 Gas 비중은 상향하지 않고 선택된 국가·에너지원의 기준 발전 믹스를 유지하는 구조로 제안합니다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0346 | 해당 좌표의 기준 Gas 발전 비중은 0.0346이며, 타 에너지원 흡수 가능성이 100%로 제시되어 폭염에 따른 추가 전력 수요가 Gas 비중 상승으로 전이되지 않는 것으로 해석했다. 따라서 발전원 비중 합계 제약을 흔들지 않도록 기준값을 그대로 최종 입력값으로 유지했다. |
| 2 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.323 | 해당 좌표의 기준 Gas 발전 비중은 0.323이며, 단기·약한 폭염과 타 에너지원 100% 흡수 조건으로 인해 Gas 발전 비중을 추가 상향할 근거가 제한적이다. 따라서 기존 발전 믹스의 Gas 비중을 유지해 최종 입력값을 0.323으로 산정했다. |

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
  "mi_event_id": 1144,
  "model_param_proposal_id": 100,
  "proposal_completed_dtm": "2026-07-07 23:38:14.064441",
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
      "rationale": "폭염 강도 dimension의 '+1~+2℃: 약'은 국가·월별 Temperature 직접 입력값을 상향 조정하는 근거이며, mapping_comment상 냉방 수요 피크 월에 조정폭을 반영하는 parameter입니다. 기간이 짧고 단발 피크이며 가격 영향도 중립으로 제시되어, 선택된 월·국가 범위에 한해 약한 폭염 구간의 하단에 가까운 보수적 상향값을 최종 기온 입력값으로 제안합니다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": [
            2.3,
            5,
            10.4
          ],
          "proposedValue": 27.6,
          "rationale": "해당 좌표의 2026년 7월 기준값은 제공되지 않아, 동일 국가의 2026년 1~3월 Temperature 기록 2.3, 5.0, 10.4℃를 이용해 월별 증가 추세를 보수적 계절 기준으로 추정했다. 1~3월 평균 증가폭 4.05℃/월을 3월부터 7월까지 연장해 26.6℃를 기준으로 잡고, 약한 폭염 범위의 하단인 +1.0℃를 반영해 최종 입력값을 27.6℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": [
            5.5,
            6.1,
            9.2
          ],
          "proposedValue": 17.6,
          "rationale": "해당 좌표의 2026년 7월 기준값은 제공되지 않아, 동일 국가의 2026년 1~3월 Temperature 기록 5.5, 6.1, 9.2℃를 이용해 월별 증가 추세를 보수적 계절 기준으로 추정했다. 1~3월 평균 증가폭 1.85℃/월을 3월부터 7월까지 연장해 16.6℃를 기준으로 잡고, 약한 폭염 범위의 하단인 +1.0℃를 반영해 최종 입력값을 17.6℃로 산정했다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension의 '100%'는 재생에너지·원전 등 비가스 전원이 냉방 수요 증가분을 흡수할 수 있음을 의미하며, PowerMix의 Gas 발전 비중 조정 여부와 직접 연결됩니다. 약한 단기 폭염과 충분한 전원 흡수, 중립적 가격 영향이 함께 제시되어 Gas 비중은 상향하지 않고 선택된 국가·에너지원의 기준 발전 믹스를 유지하는 구조로 제안합니다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0346,
          "rationale": "해당 좌표의 기준 Gas 발전 비중은 0.0346이며, 타 에너지원 흡수 가능성이 100%로 제시되어 폭염에 따른 추가 전력 수요가 Gas 비중 상승으로 전이되지 않는 것으로 해석했다. 따라서 발전원 비중 합계 제약을 흔들지 않도록 기준값을 그대로 최종 입력값으로 유지했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.323,
          "rationale": "해당 좌표의 기준 Gas 발전 비중은 0.323이며, 단기·약한 폭염과 타 에너지원 100% 흡수 조건으로 인해 Gas 발전 비중을 추가 상향할 근거가 제한적이다. 따라서 기존 발전 믹스의 Gas 비중을 유지해 최종 입력값을 0.323으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.942 | 3.942 | 2623 | 120 | 2743 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:12.017 | 12.017 | 6331 | 784 | 7115 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:14.587 | 74.587 | 8059 | 2805 | 10864 |

##### scenario_id=292 [model_parameter_agent_test] 3개월 강한 폭염과 전원 흡수 부족

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:58.668 (118.668s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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
| Step3 value 결과 | value_cells=8, basecaseValue_present=8 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 2 | 타 에너지원 흡수 가능성 25% dimension은 발전 수요 증가분 중 재생에너지·원전 등 비가스 전원이 흡수하지 못하는 몫이 가스 발전 비중으로 전이되는 경로와 연결된다. 3개월 지속되는 냉방·발전 수요 증가를 연간 PowerMix 입력에 반영하되, 연간 비중 변수인 점을 고려해 기간 효과를 제한적으로 반영하고 Gas 슬롯만 상향 조정한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0410875 | 중국 Gas 2026년 기준 비중 0.0346에 대해, 3개월 지속 효과를 연간 기준으로 3/12만 반영하고 타 에너지원 흡수 25%를 제외한 75%를 가스 전이분으로 보았다. 이에 따라 상대 상향 계수 1.1875를 적용해 최종 Gas 비중을 0.0410875로 산정했다. |
| 2 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.3835625 | 일본 Gas 2026년 기준 비중 0.323에 대해, 3개월 지속 효과를 연간 기준으로 3/12만 반영하고 타 에너지원 흡수 25%를 제외한 75%를 가스 전이분으로 보았다. 이에 따라 상대 상향 계수 1.1875를 적용해 최종 Gas 비중을 0.3835625로 산정했다. |

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
  "mi_event_id": 1144,
  "model_param_proposal_id": 102,
  "proposal_completed_dtm": "2026-07-07 23:38:58.990186",
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
      "rationale": "폭염 강도 dimension의 '+3℃ 이상: 강'은 국가·연월별 Temperature를 직접 상향 조정하는 입력과 연결된다. 기간 3개월 및 지속 피크 맥락에 따라 2026년 7~9월 중국·일본 슬롯에 동일한 강도 하한을 적용하며, 선택 월의 기준값이 제공되지 않은 경우에는 동일 국가의 제공 기준값 형식과 범위를 참고해 보수적인 최종 기온 값을 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 10.4,
          "proposedValue": 13.4,
          "rationale": "선택된 중국 2026년 7월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 강한 폭염의 하한인 +3℃를 더해 최종 입력 기온을 13.4℃로 산정했다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 10.4,
          "proposedValue": 13.4,
          "rationale": "선택된 중국 2026년 8월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 지속 피크 조건이므로 7월과 같은 +3℃ 강폭염 하한을 반영해 최종 입력 기온을 13.4℃로 산정했다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 10.4,
          "proposedValue": 13.4,
          "rationale": "선택된 중국 2026년 9월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 3개월 지속 폭염 구간의 마지막 월에도 동일한 +3℃ 하한을 적용해 최종 입력 기온을 13.4℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 9.2,
          "proposedValue": 12.2,
          "rationale": "선택된 일본 2026년 7월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 강한 폭염의 하한인 +3℃를 더해 최종 입력 기온을 12.2℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 9.2,
          "proposedValue": 12.2,
          "rationale": "선택된 일본 2026년 8월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 지속 피크 조건이므로 7월과 같은 +3℃ 강폭염 하한을 반영해 최종 입력 기온을 12.2℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 9.2,
          "proposedValue": 12.2,
          "rationale": "선택된 일본 2026년 9월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 3개월 지속 폭염 구간의 마지막 월에도 동일한 +3℃ 하한을 적용해 최종 입력 기온을 12.2℃로 산정했다."
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
      "rationale": "타 에너지원 흡수 가능성 25% dimension은 발전 수요 증가분 중 재생에너지·원전 등 비가스 전원이 흡수하지 못하는 몫이 가스 발전 비중으로 전이되는 경로와 연결된다. 3개월 지속되는 냉방·발전 수요 증가를 연간 PowerMix 입력에 반영하되, 연간 비중 변수인 점을 고려해 기간 효과를 제한적으로 반영하고 Gas 슬롯만 상향 조정한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0410875,
          "rationale": "중국 Gas 2026년 기준 비중 0.0346에 대해, 3개월 지속 효과를 연간 기준으로 3/12만 반영하고 타 에너지원 흡수 25%를 제외한 75%를 가스 전이분으로 보았다. 이에 따라 상대 상향 계수 1.1875를 적용해 최종 Gas 비중을 0.0410875로 산정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.3835625,
          "rationale": "일본 Gas 2026년 기준 비중 0.323에 대해, 3개월 지속 효과를 연간 기준으로 3/12만 반영하고 타 에너지원 흡수 25%를 제외한 75%를 가스 전이분으로 보았다. 이에 따라 상대 상향 계수 1.1875를 적용해 최종 Gas 비중을 0.3835625로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.566 | 3.566 | 2618 | 120 | 2738 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:13.841 | 13.841 | 6322 | 1024 | 7346 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:27.150 | 87.150 | 8198 | 4376 | 12574 |

#### event_type_l2_id=7 여름 폭염

##### Scenario Group

```json
{
  "description": "유럽 조기 폭염 이벤트에 대해 기간/강도/재고/injection/대체 흡수 조합을 확장해 생성한 테스트 scenario group",
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
  "mi_event_id": 1345,
  "request_usr_id": null,
  "scenario_count": 3,
  "scenario_group_id": 64,
  "stage": "scenario_created",
  "status": "created",
  "summary": "최근 한파/폭염 이벤트 기반 수급모델 파라미터 제안 확장 테스트",
  "title": "[model_parameter_agent_weather_ext_20260630] 폭염 이벤트 1345 수급모델 파라미터 테스트"
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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "재생E·원전 등 흡수",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "재고는 수급모델 input 아님 — 해석 맥락",
      "dimension": "entry_gas_inventory (진입 시점 가스 재고 (평년 대비))",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "기온 직접 입력(대안 경로) : 폭염 영향 국가·월의 Temperature를 상향 조정하고, 냉방 수요 피크 월에 더 큰 조정폭을 적용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 +℃ → CDD(냉방도일) 변환 입력 : CDD는 미대상 파라미터이므로 직접 조정하지 않고, 폭염 강도는 Temperature 상향 또는 강도·월 분배 판단 근거로만 사용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "재고 회복 속도 = 재고 개념 — 수급모델 input 아님(맥락)",
      "dimension": "injection_pattern (Injection 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "월별 분배",
      "dimension": "peak_timing_pattern (Peak 시점, 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "하절기 월 슬롯(동남아·인도 4~5월 포함)",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

```json
{
  "created_at": "2026-06-21T00:31:52.561657",
  "detail_analysis": "사건 요약:\n2026년 5월 유럽의 이례적 고온 전환과 초기 intense heatwave가 EU 가스소비 증가 배경으로 제시된 뒤, 2026년 5월 28일 WoodMac은 서유럽 조기 폭염을 단기 수급 변동 요인으로 재확인함. 2026년 6월 18일 WoodMac은 유럽 폭염을 카타르 LNG 정상화 시점, Tangguh 화재, Freeport 재가동과 함께 단기 수급을 좌우하는 변수로 제시함. 핵심 Event 경계는 유럽 조기 폭염에 따른 냉방 및 가스발전 수요 지지임.\n\n영향 경로:\n폭염은 냉방 전력수요를 높이고 전력 믹스에서 가스발전 필요성을 키우는 경로임. 이 경로는 유럽 천연가스 소비와 단기 LNG 수입 필요량을 지지하는 Fundamental 요인임. 다만 신규 Record들은 호르무즈, 카타르 LNG, Tangguh 화재, Freeport 재가동 등 별도 공급·물류 이슈도 함께 언급하고 있어 본 Event의 직접 영향은 유럽 폭염발 수요 측면으로 한정됨.\n\n시장 반응:\n폭염 자체는 프롬프트 가스수요와 TTF·유럽 LNG 도착 프리미엄을 지지하는 요인임. 2026년 5월 28일 WoodMac은 중동 긴장 완화 가능성 속 TTF 6월물 US$15.8/mmbtu와 동북아 DES 7월물 US$18.4/mmbtu 하락을 전하면서 서유럽 조기 폭염이 단기 수급 변동을 키우는 구도라고 제시함. 2026년 6월 18일 WoodMac은 미국과 이란의 호르무즈 해협 재개방 임시 합의로 TTF 7월물 US$13.7/mmbtu, 동북아 DES 8월물 US$15.4/mmbtu까지 하락했으나 유럽 폭염이 단기 수급을 좌우한다고 평가함. 2026년 6월 19일 Platts는 EU 저장률 45.56%와 7월 프롬프트 타이트에도 8월 이후 대서양 복귀 물량 기대가 NWE/TTF 할인 확대를 이끌었다고 전함.\n\nLNG 시장 관점:\n유럽 폭염은 LNG 설비 사건은 아니지만 유럽 가스 수요와 LNG 수입 경쟁에 영향을 주는 수요 Event임. 6월 중순 가격 하락은 주로 호르무즈 재개방 임시 합의와 8월 이후 대서양 복귀 물량 기대에 따른 시장 심리 완화와 연결됨. 따라서 본 Event는 유럽 폭염이 냉방·가스발전 수요를 통해 프롬프트 수급을 지지하되, 공급·물류 변수와 저장률 변화가 가격 방향을 상쇄할 수 있는 구조로 정리됨.",
  "event_title_ko": "유럽 조기 폭염 수요 지지",
  "event_type_l2_id": 7,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-19T00:00:00",
  "mi_event_id": "1345",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[유럽 가스수요] 5월 서유럽 조기 폭염 후 6월 폭염 지속 → 냉방·가스발전 수요 지지",
  "source_mi_record_ids": [
    2236,
    2462,
    3175,
    3315
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [317, 318]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=317 [model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 폭염

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:52.281 (112.281s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "alt_energy_absorption": "100%",
    "entry_gas_inventory": "+20%↑ (매우 여유)",
    "heatwave_intensity": "+1~+2℃: 약",
    "injection_pattern": "적극",
    "peak_timing_pattern": "6월 Peak",
    "period": "1개월 이하"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "neutral",
    "ttf": "up"
  },
  "narrative": "이벤트 1345 기반 확장 테스트 시나리오입니다. 기간=1개월 이하, 강도=+1~+2℃: 약, 대체흡수=100% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 34.0,
  "scenario_group_id": 64,
  "scenario_id": 317,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 폭염"
}
```

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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
| Step2 selected slot | 14 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=14, basecaseValue_present=14 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 7 | 타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 파라미터와 직접 연결되며, '100%'는 폭염에 따른 추가 전력수요를 재생에너지·원전 등 비가스 전원이 전부 흡수한다는 의미입니다. 따라서 선택된 가스 발전 비중 슬롯은 폭염으로 인한 상향 조정을 적용하지 않고, 연간 전원 믹스 합계 제약을 고려해 기존 가스 비중을 유지하는 구조로 제안했습니다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.19 | 해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.19가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.042 | 해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.042가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.135 | 해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.135가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.434 | 해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.434가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.31818965517241377 | 해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.31818965517241377이 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.213 | 해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.213이 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.29 | 해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.29가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다. |

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
  "mi_event_id": 1345,
  "model_param_proposal_id": 103,
  "proposal_completed_dtm": "2026-07-07 23:39:10.467026",
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
      "rationale": "폭염 강도 차원이 기온 직접 입력 파라미터와 연결되며, '+1~+2℃: 약'은 영향 국가·월의 Temperature를 제한적으로 상향하는 근거입니다. 기간은 1개월 이하이고 Peak가 6월로 제시되어 2026년 6월 서유럽 슬롯에만 보수적으로 반영하되, 국가별 기존 계절 상승 흐름을 기준으로 약한 폭염의 중간 강도 상향을 적용했습니다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            3.5,
            4.3,
            6.7
          ],
          "proposedValue": 13.0,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 3.5, 4.3, 6.7°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 11.5°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 13.0°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            5.1,
            5.9,
            8.5
          ],
          "proposedValue": 15.1,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 5.1, 5.9, 8.5°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 13.6°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 15.1°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            1.2,
            2.3,
            4.9
          ],
          "proposedValue": 12.0,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 1.2, 2.3, 4.9°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 10.45°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 12.0°C로 반올림했습니다."
        },
        {
          "Country": "Italy",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            6.8,
            7.7,
            10.2
          ],
          "proposedValue": 16.8,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 6.8, 7.7, 10.2°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 15.3°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 16.8°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            3.7,
            4.4,
            6.4
          ],
          "proposedValue": 12.0,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 3.7, 4.4, 6.4°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 10.45°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 12.0°C로 반올림했습니다."
        },
        {
          "Country": "Spain",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            7.9,
            9,
            11.3
          ],
          "proposedValue": 17.9,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 7.9, 9.0, 11.3°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 16.4°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 17.9°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            4.8,
            5.2,
            6.7
          ],
          "proposedValue": 11.1,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 4.8, 5.2, 6.7°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 9.55°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 11.1°C로 반올림했습니다."
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
      "rationale": "타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 파라미터와 직접 연결되며, '100%'는 폭염에 따른 추가 전력수요를 재생에너지·원전 등 비가스 전원이 전부 흡수한다는 의미입니다. 따라서 선택된 가스 발전 비중 슬롯은 폭염으로 인한 상향 조정을 적용하지 않고, 연간 전원 믹스 합계 제약을 고려해 기존 가스 비중을 유지하는 구조로 제안했습니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.19가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.042가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.135,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.135가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.434,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.434가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.31818965517241377,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.31818965517241377이 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.213,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.213이 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.29가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 64,
  "scenario_id": 317,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.684 | 3.684 | 2572 | 121 | 2693 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:16.185 | 16.185 | 6276 | 1415 | 7691 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:18.181 | 78.181 | 8385 | 3967 | 12352 |

##### scenario_id=318 [model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 폭염

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:56.503 (116.503s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "50%",
    "entry_gas_inventory": "±5% (정상)",
    "heatwave_intensity": "+2~+3℃: 중",
    "injection_pattern": "정상",
    "peak_timing_pattern": "7월 Peak",
    "period": "3개월"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "up",
    "ttf": "up"
  },
  "narrative": "이벤트 1345 기반 확장 테스트 시나리오입니다. 기간=3개월, 강도=+2~+3℃: 중, 대체흡수=50% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 33.0,
  "scenario_group_id": 64,
  "scenario_id": 318,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 폭염"
}
```

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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
| Step2 selected slot | 28 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=28, basecaseValue_present=28 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 7 | 타 에너지원 흡수 가능성 dimension의 '50%'는 재생에너지·원전 등 비가스 전원이 냉방 전력수요 증가분의 일부를 흡수하고 나머지가 가스발전 비중을 지지한다는 PowerMix 입력과 연결됩니다. 3개월 중간 폭염이 연간 발전믹스에 미치는 영향은 제한적으로 보되, 흡수되지 않는 절반의 수요가 가스 비중을 소폭 상향시키는 구조로 제안합니다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.19475 | Belgium Gas 2026년 기준 발전믹스 0.19에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.19 × 1.025 = 0.19475입니다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.04305 | France Gas 2026년 기준 발전믹스 0.042에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.042 × 1.025 = 0.04305입니다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.138375 | Germany Gas 2026년 기준 발전믹스 0.135에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.135 × 1.025 = 0.138375입니다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.44485 | Italy Gas 2026년 기준 발전믹스 0.434에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.434 × 1.025 = 0.44485입니다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.3261443965517241 | Netherlands Gas 2026년 기준 발전믹스 0.31818965517241377에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.31818965517241377 × 1.025 = 0.3261443965517241입니다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.218325 | Spain Gas 2026년 기준 발전믹스 0.213에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.213 × 1.025 = 0.218325입니다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.29725 | United Kingdom Gas 2026년 기준 발전믹스 0.29에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.29 × 1.025 = 0.29725입니다. |

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
  "mi_event_id": 1345,
  "model_param_proposal_id": 105,
  "proposal_completed_dtm": "2026-07-07 23:40:02.150900",
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
      "rationale": "폭염 강도 dimension의 '+2~+3℃: 중'은 국가·월별 Temperature를 직접 상향 조정하는 입력과 연결되며, mapping_comment에 따라 냉방 수요 피크 월에 더 큰 조정폭을 적용합니다. 기간 3개월과 7월 Peak 맥락을 반영해 2026년 7~9월 유럽 대상국에 7월 최대, 이후 완만히 낮아지는 절대 기온 값을 제안합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.7,
          "rationale": "2026년 7월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.7℃로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.2,
          "rationale": "2026년 8월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 9.2℃로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 8.7,
          "rationale": "2026년 9월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.7℃로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 8.5,
          "proposedValue": 11.5,
          "rationale": "2026년 7월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 11.5℃로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 8.5,
          "proposedValue": 11,
          "rationale": "2026년 8월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 11.0℃로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 8.5,
          "proposedValue": 10.5,
          "rationale": "2026년 9월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 10.5℃로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 4.9,
          "proposedValue": 7.9,
          "rationale": "2026년 7월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 7.9℃로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 4.9,
          "proposedValue": 7.4,
          "rationale": "2026년 8월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 7.4℃로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 4.9,
          "proposedValue": 6.9,
          "rationale": "2026년 9월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 6.9℃로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 10.2,
          "proposedValue": 13.2,
          "rationale": "2026년 7월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 13.2℃로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 10.2,
          "proposedValue": 12.7,
          "rationale": "2026년 8월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 12.7℃로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 10.2,
          "proposedValue": 12.2,
          "rationale": "2026년 9월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 12.2℃로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 6.4,
          "proposedValue": 9.4,
          "rationale": "2026년 7월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.4℃로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 6.4,
          "proposedValue": 8.9,
          "rationale": "2026년 8월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 8.9℃로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 6.4,
          "proposedValue": 8.4,
          "rationale": "2026년 9월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.4℃로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 11.3,
          "proposedValue": 14.3,
          "rationale": "2026년 7월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 14.3℃로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 11.3,
          "proposedValue": 13.8,
          "rationale": "2026년 8월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 13.8℃로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 11.3,
          "proposedValue": 13.3,
          "rationale": "2026년 9월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 13.3℃로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.7,
          "rationale": "2026년 7월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.7℃로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.2,
          "rationale": "2026년 8월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 9.2℃로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 8.7,
          "rationale": "2026년 9월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.7℃로 산정했습니다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension의 '50%'는 재생에너지·원전 등 비가스 전원이 냉방 전력수요 증가분의 일부를 흡수하고 나머지가 가스발전 비중을 지지한다는 PowerMix 입력과 연결됩니다. 3개월 중간 폭염이 연간 발전믹스에 미치는 영향은 제한적으로 보되, 흡수되지 않는 절반의 수요가 가스 비중을 소폭 상향시키는 구조로 제안합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19475,
          "rationale": "Belgium Gas 2026년 기준 발전믹스 0.19에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.19 × 1.025 = 0.19475입니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04305,
          "rationale": "France Gas 2026년 기준 발전믹스 0.042에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.042 × 1.025 = 0.04305입니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.138375,
          "rationale": "Germany Gas 2026년 기준 발전믹스 0.135에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.135 × 1.025 = 0.138375입니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.44485,
          "rationale": "Italy Gas 2026년 기준 발전믹스 0.434에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.434 × 1.025 = 0.44485입니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3261443965517241,
          "rationale": "Netherlands Gas 2026년 기준 발전믹스 0.31818965517241377에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.31818965517241377 × 1.025 = 0.3261443965517241입니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.218325,
          "rationale": "Spain Gas 2026년 기준 발전믹스 0.213에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.213 × 1.025 = 0.218325입니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29725,
          "rationale": "United Kingdom Gas 2026년 기준 발전믹스 0.29에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.29 × 1.025 = 0.29725입니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 64,
  "scenario_id": 318,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.251 | 3.251 | 2573 | 114 | 2687 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:20.614 | 20.614 | 6265 | 2261 | 8526 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:10.695 | 70.695 | 8898 | 5845 | 14743 |

#### event_type_l2_id=8 원자력 발전

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "정비=Shoulder/사고·정책=단발 OR 영구",
      "dimension": "affected_period (영향 기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "재생E·석탄 등 흡수",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "원전 비중 변동→가스 비중 대체(원전 전용 input 없음)",
      "dimension": "capacity_change_scale (Capacity 변화 규모)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "발전 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영",
      "dimension": "capacity_change_scale (Capacity 변화 규모)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "급격(사고)/점진(정비)",
      "dimension": "onset_pattern (발생 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "급격(재가동)/점진(COD)",
      "dimension": "recovery_pattern (회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "단발(정비)/구조적(COD·폐쇄·수명연장)",
      "dimension": "structural_change_yn (구조적 변동 여부)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [293, 294]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=293 [model_parameter_agent_test] 단기 소규모 원전 차질 흡수

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 00:37.399 (37.399s)
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
  "narrative": "원전 이용률 저하가 작고 단기에 그쳐 다른 전원이 모두 흡수한다.",
  "probability_delta": 2.0,
  "probability_score": 30.0,
  "scenario_group_id": 54,
  "scenario_id": 293,
  "status": "created",
  "title": "[model_parameter_agent_test] 단기 소규모 원전 차질 흡수"
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | Capacity 변화 규모가 1 GW 미만인 원전 이용률 저하는 발전믹스 내 원전 비중 변동을 통해 대체 전원 비중 조정으로 연결되며, 이 parameter는 국가·에너지원·연도별 발전 비중을 입력하는 항목이다. 다만 타 에너지원 흡수 가능성이 100%로 제시되어 가스가 직접 대체 부담을 지는 구조가 아니고, 영향 기간도 단기·단발적이므로 한국 가스 발전 비중은 기준 수준을 유지하는 방향으로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.285 | 선택된 좌표는 한국의 2026년 가스 발전 비중이며, 해당 기준값은 0.285이다. 원전 차질 규모가 작고 1개월 이하로 짧으며 타 에너지원이 100% 흡수하는 조건이므로 연간 가스 발전 비중에 추가 상향 조정을 적용하지 않고 0.285로 유지한다. |

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
  "mi_event_id": 1173,
  "model_param_proposal_id": 101,
  "proposal_completed_dtm": "2026-07-07 23:38:51.479755",
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
      "rationale": "Capacity 변화 규모가 1 GW 미만인 원전 이용률 저하는 발전믹스 내 원전 비중 변동을 통해 대체 전원 비중 조정으로 연결되며, 이 parameter는 국가·에너지원·연도별 발전 비중을 입력하는 항목이다. 다만 타 에너지원 흡수 가능성이 100%로 제시되어 가스가 직접 대체 부담을 지는 구조가 아니고, 영향 기간도 단기·단발적이므로 한국 가스 발전 비중은 기준 수준을 유지하는 방향으로 제안한다.",
      "values": [
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.285,
          "rationale": "선택된 좌표는 한국의 2026년 가스 발전 비중이며, 해당 기준값은 0.285이다. 원전 차질 규모가 작고 1개월 이하로 짧으며 타 에너지원이 100% 흡수하는 조건이므로 연간 가스 발전 비중에 추가 상향 조정을 적용하지 않고 0.285로 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:02.921 | 2.921 | 2183 | 124 | 2307 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:09.376 | 9.376 | 5466 | 465 | 5931 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:08.935 | 8.935 | 7222 | 509 | 7731 |

##### scenario_id=294 [model_parameter_agent_test] 6개월 원전 차질과 LNG 대체수요

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:02.568 (62.568s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | 원전 차질 규모를 나타내는 capacity_change_scale은 원전 전용 입력이 없는 발전믹스 설정에서 가스 발전 비중 상향으로 연결된다. alt_energy_absorption 50%는 재생에너지·석탄 등 다른 전원이 절반을 흡수한다는 의미이므로 가스 대체분을 제한해 반영하며, 6개월 영향과 점진적 회복을 고려해 2026년 한국 Gas 비중을 보수적으로 상향 조정한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.297 | 해당 좌표의 기준 Gas 발전비중은 0.285이다. 원전 차질 3~5GW의 중간 수준을 6개월 연간 영향으로 환산하고, 타 에너지원 흡수 50%를 제외한 잔여분만 가스가 대체한다고 보아 약 1.2%p를 더해 최종 입력값을 0.297로 제안한다. |

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
  "mi_event_id": 1173,
  "model_param_proposal_id": 104,
  "proposal_completed_dtm": "2026-07-07 23:39:54.061047",
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
      "rationale": "원전 차질 규모를 나타내는 capacity_change_scale은 원전 전용 입력이 없는 발전믹스 설정에서 가스 발전 비중 상향으로 연결된다. alt_energy_absorption 50%는 재생에너지·석탄 등 다른 전원이 절반을 흡수한다는 의미이므로 가스 대체분을 제한해 반영하며, 6개월 영향과 점진적 회복을 고려해 2026년 한국 Gas 비중을 보수적으로 상향 조정한다.",
      "values": [
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.297,
          "rationale": "해당 좌표의 기준 Gas 발전비중은 0.285이다. 원전 차질 3~5GW의 중간 수준을 6개월 연간 영향으로 환산하고, 타 에너지원 흡수 50%를 제외한 잔여분만 가스가 대체한다고 보아 약 1.2%p를 더해 최종 입력값을 0.297로 제안한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.567 | 3.567 | 2189 | 116 | 2305 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:10.498 | 10.498 | 5469 | 582 | 6051 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:18.422 | 18.422 | 7225 | 814 | 8039 |

#### event_type_l2_id=9 재생에너지

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "동절기 둔켈플라우테/하절기 열파 풍력 약화",
      "dimension": "affected_period (영향 기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "석탄·원전 등 흡수",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "재생 출력 변동→가스 비중 대체(재생 전용 input 없음)",
      "dimension": "capacity_change_scale (Capacity 변화 규모)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "발전 가스 수요 직접 강제 시 : User-Adjusted Gas Demand는 미대상 수동 overwrite이므로 직접 쓰지 말고, 발전 설비 변화는 PowerMix의 Gas 비중 조정으로 반영",
      "dimension": "capacity_change_scale (Capacity 변화 규모)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "급격(무풍)/점진(정책 phase-out)",
      "dimension": "onset_pattern (발생 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "급격(기상)/점진(COD)",
      "dimension": "recovery_pattern (회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "단발(기상)/구조적(신규 Farm·정책)",
      "dimension": "structural_change_yn (구조적 변동 여부)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [261, 262]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=261 대체 전원이 흡수한 단기 가스발전 지지

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:13.087 (73.087s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 7 | Capacity 변화 규모가 1GW 미만으로 제한되어 재생 출력 약세가 가스 발전 비중에 미칠 수 있는 직접 경로는 작고, 타 에너지원 흡수 가능성이 100%로 제시되어 원전·석탄·수입전력 등이 추가 전력수요를 흡수하는 구조입니다. 영향 기간도 1개월 이하의 단기 요인에 그치므로 연간 PowerMix 입력에는 유의미한 상향 조정보다는 2026년 가스 발전 비중을 기준 수준으로 유지하는 보수적 적용이 적절합니다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.19 | 해당 좌표는 2026년 벨기에 Gas 발전 비중 입력값입니다. 기준값 0.19에 대해 영향 기간이 1개월 이하이고 대체 전원이 전부 흡수하는 설정이므로 연간 발전 믹스 조정은 적용하지 않고 제안값을 0.19로 유지했습니다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.042 | 해당 좌표는 2026년 프랑스 Gas 발전 비중 입력값입니다. 기준값 0.042에 대해 단기 재생 출력 약세가 있더라도 대체 전원 흡수가 100%로 설정되어 가스 비중 추가 상승을 반영하지 않고 제안값을 0.042로 유지했습니다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.135 | 해당 좌표는 2026년 독일 Gas 발전 비중 입력값입니다. 기준값 0.135에 대해 변화 규모가 1GW 미만이고 단기 영향으로 제한되므로 연간 Gas 비중을 상향하지 않고 제안값을 0.135로 유지했습니다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.434 | 해당 좌표는 2026년 이탈리아 Gas 발전 비중 입력값입니다. 기준값 0.434에 대해 폭염과 재생 약세의 가스발전 지지 효과가 짧고 타 전원이 전부 흡수하는 조건이므로 연간 입력값은 0.434로 유지했습니다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.31818965517241377 | 해당 좌표는 2026년 네덜란드 Gas 발전 비중 입력값입니다. 기준값 0.31818965517241377에 대해 영향 기간이 1개월 이하이고 대체 전원 흡수가 완전하므로 연간 발전 믹스에는 별도 조정을 두지 않고 제안값을 0.31818965517241377로 유지했습니다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.213 | 해당 좌표는 2026년 스페인 Gas 발전 비중 입력값입니다. 기준값 0.213에 대해 재생 출력 약세가 단발적이고 1GW 미만으로 제한되며 대체 전원 흡수가 100%이므로 제안값을 0.213으로 유지했습니다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.29 | 해당 좌표는 2026년 영국 Gas 발전 비중 입력값입니다. 기준값 0.29에 대해 단기적인 전력수요·재생 약세 요인이 가스발전 호출을 일부 지지할 수 있으나, 다른 전원이 전부 흡수하는 설정이므로 연간 Gas 비중은 0.29로 유지했습니다. |

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
  "mi_event_id": 1348,
  "model_param_proposal_id": 106,
  "proposal_completed_dtm": "2026-07-07 23:40:12.032702",
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
      "rationale": "Capacity 변화 규모가 1GW 미만으로 제한되어 재생 출력 약세가 가스 발전 비중에 미칠 수 있는 직접 경로는 작고, 타 에너지원 흡수 가능성이 100%로 제시되어 원전·석탄·수입전력 등이 추가 전력수요를 흡수하는 구조입니다. 영향 기간도 1개월 이하의 단기 요인에 그치므로 연간 PowerMix 입력에는 유의미한 상향 조정보다는 2026년 가스 발전 비중을 기준 수준으로 유지하는 보수적 적용이 적절합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19,
          "rationale": "해당 좌표는 2026년 벨기에 Gas 발전 비중 입력값입니다. 기준값 0.19에 대해 영향 기간이 1개월 이하이고 대체 전원이 전부 흡수하는 설정이므로 연간 발전 믹스 조정은 적용하지 않고 제안값을 0.19로 유지했습니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "해당 좌표는 2026년 프랑스 Gas 발전 비중 입력값입니다. 기준값 0.042에 대해 단기 재생 출력 약세가 있더라도 대체 전원 흡수가 100%로 설정되어 가스 비중 추가 상승을 반영하지 않고 제안값을 0.042로 유지했습니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.135,
          "rationale": "해당 좌표는 2026년 독일 Gas 발전 비중 입력값입니다. 기준값 0.135에 대해 변화 규모가 1GW 미만이고 단기 영향으로 제한되므로 연간 Gas 비중을 상향하지 않고 제안값을 0.135로 유지했습니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.434,
          "rationale": "해당 좌표는 2026년 이탈리아 Gas 발전 비중 입력값입니다. 기준값 0.434에 대해 폭염과 재생 약세의 가스발전 지지 효과가 짧고 타 전원이 전부 흡수하는 조건이므로 연간 입력값은 0.434로 유지했습니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.31818965517241377,
          "rationale": "해당 좌표는 2026년 네덜란드 Gas 발전 비중 입력값입니다. 기준값 0.31818965517241377에 대해 영향 기간이 1개월 이하이고 대체 전원 흡수가 완전하므로 연간 발전 믹스에는 별도 조정을 두지 않고 제안값을 0.31818965517241377로 유지했습니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.213,
          "rationale": "해당 좌표는 2026년 스페인 Gas 발전 비중 입력값입니다. 기준값 0.213에 대해 재생 출력 약세가 단발적이고 1GW 미만으로 제한되며 대체 전원 흡수가 100%이므로 제안값을 0.213으로 유지했습니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29,
          "rationale": "해당 좌표는 2026년 영국 Gas 발전 비중 입력값입니다. 기준값 0.29에 대해 단기적인 전력수요·재생 약세 요인이 가스발전 호출을 일부 지지할 수 있으나, 다른 전원이 전부 흡수하는 설정이므로 연간 Gas 비중은 0.29로 유지했습니다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.939 | 4.939 | 2579 | 120 | 2699 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:17.154 | 17.154 | 5473 | 971 | 6444 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:28.003 | 28.003 | 7459 | 1363 | 8822 |

##### scenario_id=262 석 달간 절반만 흡수되는 유럽 가스발전 수요

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:20.910 (80.910s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 7 | Capacity 변화 규모는 재생에너지 출력 약세가 가스발전 비중을 대체적으로 높이는 경로와 직접 연결되며, 타 에너지원 흡수 가능성 50%는 석탄·원전 등 다른 전원이 일부 공백을 메워 가스 비중 증가폭을 제한하는 조건으로 반영했다. 영향 기간 3개월은 연간 발전 믹스 입력에 반영될 때 단기 충격이 연간 평균으로 희석되는 맥락으로만 사용했으며, 2026년 유럽 주요국의 Gas 발전 비중을 기준 대비 보수적으로 소폭 상향했다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.1957 | 해당 좌표는 2026년 Belgium의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 재생에너지 약세가 3개월에 그치고 타 전원이 절반을 흡수하는 조건을 반영해 기준값 0.19에 약 3%의 보수적 상대 상향을 적용하여 0.1957로 산정했다. |
| 2 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.04326 | 해당 좌표는 2026년 France의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 낮은 가스 비중 국가인 점을 유지하되, 3개월간 남는 전력 공백 일부를 가스가 담당하는 효과를 기준값 0.042에 약 3% 상대 상향으로 반영하여 0.04326으로 산정했다. |
| 3 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.13905 | 해당 좌표는 2026년 Germany의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 풍력·수력 약세와 냉방 수요가 가스발전 호출을 높이는 효과를 반영하되, 타 전원 50% 흡수와 3개월 지속 조건을 감안해 기준값 0.135에 약 3% 상대 상향을 적용하여 0.13905로 산정했다. |
| 4 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.44702 | 해당 좌표는 2026년 Italy의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 기존 가스 의존도가 높은 전력 믹스에서 재생 출력 약세가 가스발전 비중을 추가로 높이는 방향을 반영하되, 단기·부분 흡수 조건을 감안해 기준값 0.434에 약 3% 상대 상향을 적용하여 0.44702로 산정했다. |
| 5 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.3277353448275862 | 해당 좌표는 2026년 Netherlands의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 가스발전 대체수요 증가 방향은 반영하되, 영향 기간이 3개월이고 다른 전원이 절반을 흡수한다는 점을 고려해 기준값 0.31818965517241377에 약 3% 상대 상향을 적용하여 0.3277353448275862로 산정했다. |
| 6 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.21939 | 해당 좌표는 2026년 Spain의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 재생 출력 약세에 따른 가스발전 보완 수요를 반영하되, 타 에너지원 흡수율 50%와 연간 입력상 희석 효과를 감안해 기준값 0.213에 약 3% 상대 상향을 적용하여 0.21939로 산정했다. |
| 7 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.2987 | 해당 좌표는 2026년 United Kingdom의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 풍력 약세 시 가스발전 호출이 늘어나는 구조를 반영하되, 3개월 지속과 50% 대체 흡수를 고려해 기준값 0.29에 약 3% 상대 상향을 적용하여 0.2987로 산정했다. |

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
  "mi_event_id": 1348,
  "model_param_proposal_id": 107,
  "proposal_completed_dtm": "2026-07-07 23:40:31.541346",
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
      "rationale": "Capacity 변화 규모는 재생에너지 출력 약세가 가스발전 비중을 대체적으로 높이는 경로와 직접 연결되며, 타 에너지원 흡수 가능성 50%는 석탄·원전 등 다른 전원이 일부 공백을 메워 가스 비중 증가폭을 제한하는 조건으로 반영했다. 영향 기간 3개월은 연간 발전 믹스 입력에 반영될 때 단기 충격이 연간 평균으로 희석되는 맥락으로만 사용했으며, 2026년 유럽 주요국의 Gas 발전 비중을 기준 대비 보수적으로 소폭 상향했다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.1957,
          "rationale": "해당 좌표는 2026년 Belgium의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 재생에너지 약세가 3개월에 그치고 타 전원이 절반을 흡수하는 조건을 반영해 기준값 0.19에 약 3%의 보수적 상대 상향을 적용하여 0.1957로 산정했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04326,
          "rationale": "해당 좌표는 2026년 France의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 낮은 가스 비중 국가인 점을 유지하되, 3개월간 남는 전력 공백 일부를 가스가 담당하는 효과를 기준값 0.042에 약 3% 상대 상향으로 반영하여 0.04326으로 산정했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.13905,
          "rationale": "해당 좌표는 2026년 Germany의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 풍력·수력 약세와 냉방 수요가 가스발전 호출을 높이는 효과를 반영하되, 타 전원 50% 흡수와 3개월 지속 조건을 감안해 기준값 0.135에 약 3% 상대 상향을 적용하여 0.13905로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.44702,
          "rationale": "해당 좌표는 2026년 Italy의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 기존 가스 의존도가 높은 전력 믹스에서 재생 출력 약세가 가스발전 비중을 추가로 높이는 방향을 반영하되, 단기·부분 흡수 조건을 감안해 기준값 0.434에 약 3% 상대 상향을 적용하여 0.44702로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3277353448275862,
          "rationale": "해당 좌표는 2026년 Netherlands의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 가스발전 대체수요 증가 방향은 반영하되, 영향 기간이 3개월이고 다른 전원이 절반을 흡수한다는 점을 고려해 기준값 0.31818965517241377에 약 3% 상대 상향을 적용하여 0.3277353448275862로 산정했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.21939,
          "rationale": "해당 좌표는 2026년 Spain의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 재생 출력 약세에 따른 가스발전 보완 수요를 반영하되, 타 에너지원 흡수율 50%와 연간 입력상 희석 효과를 감안해 기준값 0.213에 약 3% 상대 상향을 적용하여 0.21939로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.2987,
          "rationale": "해당 좌표는 2026년 United Kingdom의 Gas 발전 믹스 기준값이 있는 직접 선택 슬롯이다. 풍력 약세 시 가스발전 호출이 늘어나는 구조를 반영하되, 3개월 지속과 50% 대체 흡수를 고려해 기준값 0.29에 약 3% 상대 상향을 적용하여 0.2987로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:05.343 | 5.343 | 2587 | 117 | 2704 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:11.888 | 11.888 | 5478 | 753 | 6231 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:46.616 | 46.616 | 7464 | 1886 | 9350 |

#### event_type_l2_id=10 석탄 발전

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "단발(가격)/중기(계약)/장기(정책)",
      "dimension": "affected_period (영향 기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "원전·재생E 등 흡수",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "구조적 비중 변화(정책·폐쇄) : 정책·폐쇄·설비 변화처럼 구조적 전환이면 PowerMix에서 Gas/Coal 비중을 연 단위로 조정",
      "dimension": "lng_demand_impact_intensity (LNG 수요 영향 강도)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "가격기반 석탄↔가스 스위칭(Asia=Newcastle/JKM, EU=ARA/TTF) : 지역별 기준 가격쌍을 사용해 석탄-가스 전환 유인을 판단하고, 단기 가격 이벤트는 CoalGasAdjustment를 우선 사용",
      "dimension": "lng_demand_impact_intensity (LNG 수요 영향 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "가격기반 석탄↔가스 스위칭(Asia=Newcastle/JKM, EU=ARA/TTF) : 지역별 기준 가격쌍을 사용해 석탄-가스 전환 유인을 판단하고, 단기 가격 이벤트는 CoalGasAdjustment를 우선 사용",
      "dimension": "lng_demand_impact_intensity (LNG 수요 영향 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "단발(가격→CoalGas)/구조적(정책→PowerMix) 결정",
      "dimension": "structural_change_yn (구조적 변동 여부)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [267, 268]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=267 단기 복구와 석탄 경쟁력으로 LNG 대체수요 소멸

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 00:52.748 (52.748s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 100%는 발전 믹스 내에서 가스발전 비중을 조정할지 판단하는 직접 근거이며, PowerMix는 국가·에너지원·연도별 발전 비중을 입력하는 parameter이므로 해당 차원을 반영한다. 구조적 변동 여부가 단발적이고 영향 기간도 1개월 이하로 제한되어 장기적인 가스 발전비중 상향 필요는 낮으므로, 일본 2026년 Gas 비중은 기준 수준을 유지하는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.323 | 해당 좌표는 선택된 일본 2026년 Gas 발전 믹스 입력이며, 현재 기준값은 0.323이다. Haramachi 차질이 1개월 이하이고 부족분을 기존 석탄 운용 및 다른 전원으로 100% 흡수하는 시나리오이므로 가스발전 비중을 추가 상향하지 않고 최종 입력값을 기준값과 동일한 0.323으로 유지한다. |

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
  "mi_event_id": 1156,
  "model_param_proposal_id": 108,
  "proposal_completed_dtm": "2026-07-07 23:40:46.822273",
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
      "rationale": "타 에너지원 흡수 가능성 100%는 발전 믹스 내에서 가스발전 비중을 조정할지 판단하는 직접 근거이며, PowerMix는 국가·에너지원·연도별 발전 비중을 입력하는 parameter이므로 해당 차원을 반영한다. 구조적 변동 여부가 단발적이고 영향 기간도 1개월 이하로 제한되어 장기적인 가스 발전비중 상향 필요는 낮으므로, 일본 2026년 Gas 비중은 기준 수준을 유지하는 구조로 제안한다.",
      "values": [
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.323,
          "rationale": "해당 좌표는 선택된 일본 2026년 Gas 발전 믹스 입력이며, 현재 기준값은 0.323이다. Haramachi 차질이 1개월 이하이고 부족분을 기존 석탄 운용 및 다른 전원으로 100% 흡수하는 시나리오이므로 가스발전 비중을 추가 상향하지 않고 최종 입력값을 기준값과 동일한 0.323으로 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.849 | 4.849 | 2308 | 71 | 2379 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:09.502 | 9.502 | 5365 | 452 | 5817 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:09.478 | 9.478 | 7120 | 540 | 7660 |

##### scenario_id=268 6개월 공백에 고가 석유 대체 한계, LNG 보강 매수 부상

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 00:58.036 (58.036s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Country", "Energy Source", "Year"]` | `["% Power Mix"]` | 1 | 타 에너지원 흡수 가능성 50%는 석탄발전 차질분 중 원전·재생에너지 등 비가스 전원이 일부만 흡수하고 잔여 공백은 가스발전 비중 상승으로 연결된다는 점에서 PowerMix 조정과 직접 연결된다. 구조적 변동으로 분류된 점은 단순 일시 가격 조정보다 2026년 일본 발전 믹스의 가스 비중 상향 반영을 뒷받침하며, 6개월 영향 기간을 고려해 연간 비중에는 제한적인 폭으로 반영한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.326 | 해당 좌표는 일본의 2026년 Gas 발전 비중 기준값 0.323에 대응한다. Haramachi 1·2호기 총 2GW 석탄 차질이 6개월 지속되고 타 전원이 50% 흡수하는 조건이므로, 연간 발전 믹스 기준으로는 잔여 공백의 일부만 가스 비중에 반영해 약 0.3%p 상향한 0.326을 최종 입력값으로 제안한다. |

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
  "mi_event_id": 1156,
  "model_param_proposal_id": 109,
  "proposal_completed_dtm": "2026-07-07 23:41:00.376781",
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
      "rationale": "타 에너지원 흡수 가능성 50%는 석탄발전 차질분 중 원전·재생에너지 등 비가스 전원이 일부만 흡수하고 잔여 공백은 가스발전 비중 상승으로 연결된다는 점에서 PowerMix 조정과 직접 연결된다. 구조적 변동으로 분류된 점은 단순 일시 가격 조정보다 2026년 일본 발전 믹스의 가스 비중 상향 반영을 뒷받침하며, 6개월 영향 기간을 고려해 연간 비중에는 제한적인 폭으로 반영한다.",
      "values": [
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.326,
          "rationale": "해당 좌표는 일본의 2026년 Gas 발전 비중 기준값 0.323에 대응한다. Haramachi 1·2호기 총 2GW 석탄 차질이 6개월 지속되고 타 전원이 50% 흡수하는 조건이므로, 연간 발전 믹스 기준으로는 잔여 공백의 일부만 가스 비중에 반영해 약 0.3%p 상향한 0.326을 최종 입력값으로 제안한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.643 | 3.643 | 2364 | 86 | 2450 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:10.133 | 10.133 | 5418 | 299 | 5717 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:22.977 | 22.977 | 7173 | 743 | 7916 |

#### event_type_l2_id=17 지정학적 긴장 및 전쟁·군사분쟁

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "타 공급국 상향으로 상쇄",
      "dimension": "demand_response_alternative_lng (수요측 대응 - 타 공급원 경유 LNG 확보량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "자체 PowerMix 조정으로 LNG 수요 감소(SPR/대체 효과 포함) : 수요국의 정책·비상 대응으로 LNG 발전 수요가 줄면 PowerMix의 Gas 비중을 낮추고 대체 전원 비중을 조정",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "장기화 시 종료 N/A — 시간축",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "액화시설 가동률 감소 : 영향권 액화시설의 이용률을 하향 조정하고, 단기 제약은 LiqUtilAdjustment를 우선 사용",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "생산량 직접 감소(대폭/영구) : 전쟁·제재로 장기 또는 영구 생산 손실이 명확할 때 생산량 자체를 하향 조정",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "upstream(가스전) 생산 차질 동반 시",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "Ref. 공급 차질 패턴 — 시계열",
      "dimension": "supply_disruption_pattern (공급 차질 - 발생/회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "From-To 계약 물량 취소 : 계약 취소는 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 가능량 감소가 확인될 때 Supply 계열 파라미터로 우회 반영",
      "dimension": "trade_restriction (거래 제한 (계약 취소 등))",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "용선료·보험료 상승 : 운송비·보험료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 선적 차질이 있으면 공급 차질 기간·강도 판단에만 사용",
      "dimension": "transport_disruption (운송 차질)",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [92, 93]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=92 1개월 내 물류 프리미엄 흡수

- target_parameter: `PowerMix`
- target_expected_present: NO
- target_selected_present: NO
- 소요시간: 03:44.984 (224.984s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `[]`
- target_selected_parameters: `[]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 20 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=20, basecaseValue_present=20 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

- 제안 파라미터 없음.

###### Proposed Parameter Values

- 제안 value 없음.

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
  "mi_event_id": 1133,
  "model_param_proposal_id": 111,
  "proposal_completed_dtm": "2026-07-07 23:44:31.815177",
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
      "rationale": "공급 차질 강도는 낮음으로 제시되어 영향권 액화시설의 단기 이용률 조정이 가능한 LiqUtilAdjustment와 직접 연결된다. 다만 타 공급원 경유 LNG 확보량이 100%로 제시되고, 이벤트상 호르무즈 통항 재개와 특정 LNG 터미널·화물 차질 부재가 확인되므로 설비 가동률 자체의 물리적 하향은 반영하지 않고 1개월 이하 기간의 선택 슬롯에 대해 현행 기준 수준을 유지한다.",
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 주요 액화 트레인으로 항로 리스크 영향권에 있으나, 설비 중단이나 선적 취소가 확인되지 않았고 대체 LNG 확보가 전량 가능하므로 기준값 1.0477010309278352를 그대로 최종 입력값으로 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 동일 플랜트 내 운전 트레인으로 단기 물류 리스크는 남아 있으나 물리적 액화 차질 근거가 없으므로 기준값 1.0477010309278352를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 중동 항로 리스크 노출 설비이나 호르무즈 재개방 이후 확인된 공급 차질이 낮고 대체 확보가 충분하므로 기준값 1.0477010309278352를 최종 입력값으로 둔다."
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
          "rationale": "해당 2026년 7월 대형 트레인은 영향권에 포함되지만 LNG 설비 가동 중단이 확인되지 않았고 시나리오 기간도 1개월 이하이므로 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 동일 설비군의 운전 트레인으로, 낮은 차질 강도와 전량 대체 확보 조건을 반영해 기준값 1.0476962025316454를 변경하지 않는다."
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 수출 설비로 지정학 리스크 대상이지만, 이벤트상 실제 LNG 생산 차질은 확인되지 않아 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 호르무즈 경유 물류 프리미엄에 노출될 수 있으나, 재개방과 낮은 차질 강도를 감안하면 설비 이용률 하향 근거가 약해 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 내 영향권 트레인이지만 공급 차질 강도가 낮고 부족분 대체가 가능하므로 기준값 1.0476969696969696을 그대로 적용한다."
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
          "rationale": "해당 2026년 7월 슬롯은 단기 항로 리스크의 간접 영향권이나 물리적 액화 감소가 확인되지 않았으므로 기준값 1.0476969696969696을 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 운전 트레인으로 선택되었으나, 시나리오가 물류 프리미엄 흡수와 전량 대체 확보를 전제하므로 기준값 1.0477021276595746을 최종값으로 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 영향권에 있으나 호르무즈 통항 재개 이후 실제 가동률 저하 근거가 없어 기준값 1.0477021276595746을 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 낮은 차질 강도만 반영 가능한 대상이며, 대체 확보 100%와 특정 설비 차질 부재를 반영해 기준값 1.0477021276595746을 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 대형 카타르 트레인이지만, 이번 케이스는 가격·물류 프리미엄 중심이고 생산 차질은 낮으므로 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 동일 영향권 내 운전 트레인이나, 통항 재개와 전량 대체 확보 조건으로 액화 이용률 하향을 적용하지 않고 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 UAE 슬롯은 걸프 항로 리스크 영향권이나, 이벤트상 통항 정상화 신호가 있고 LNG 설비 차질이 확인되지 않아 기준값 1.0956424079065634를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 단기 물류 리스크 대상이나 공급 차질 강도가 낮고 대체 LNG가 전량 확보되는 조건이므로 기준값 1.0956424079065634를 변경하지 않는다."
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
          "rationale": "해당 2026년 7월 슬롯은 UAE 운전 트레인으로 영향권에 포함되지만, 실제 생산 감소 근거가 없고 시나리오가 단기 프리미엄 흡수를 전제하므로 기준값 1.0956424079065634를 유지한다."
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
          "proposedValue": 1.1814275778125545,
          "rationale": "해당 2026년 7월 오만 슬롯은 중동 해상 물류 리스크와 관련될 수 있으나, 낮은 차질 강도와 호르무즈 재개방을 반영하면 액화 이용률 조정 필요가 제한적이므로 기준값 1.1814275778125545를 유지한다."
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
          "proposedValue": 1.1814275778125545,
          "rationale": "해당 2026년 7월 슬롯은 오만 LNG 운전 트레인으로 선택되었으나, 실제 설비 중단이 없고 대체 조달이 충분한 케이스이므로 기준값 1.1814275778125545를 그대로 적용한다."
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
          "proposedValue": 0.9179166666666668,
          "rationale": "해당 2026년 7월 슬롯은 오만 LNG 내 별도 트레인 기준값이 낮게 설정된 운전 슬롯이며, 이번 시나리오에서 추가 생산 차질을 뒷받침할 근거가 없어 기준값 0.9179166666666667을 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:08.724 | 8.724 | 3385 | 142 | 3527 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:50.647 | 110.647 | 12371 | 5361 | 17732 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:32.326 | 92.326 | 13755 | 4797 | 18552 |

##### scenario_id=93 3개월 부분 차질과 절반 대체 조달

- target_parameter: `PowerMix`
- target_expected_present: NO
- target_selected_present: NO
- 소요시간: 06:07.484 (367.484s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `[]`
- target_selected_parameters: `[]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 99 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=99, basecaseValue_present=99 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

- 제안 파라미터 없음.

###### Proposed Parameter Values

- 제안 value 없음.

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
  "mi_event_id": 1133,
  "model_param_proposal_id": 114,
  "proposal_completed_dtm": "2026-07-07 23:47:07.848202",
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
      "rationale": "공급 차질 강도 ‘중간’은 영향권 액화시설의 단기 이용률 하향 조정과 직접 연결되며, LiqUtilAdjustment는 train/month 단위 가동률 override이므로 3개월 부분 차질을 반영하기에 적합하다. 동시에 타 공급원 경유 LNG 확보량 50%는 부족분의 절반을 대체 조달로 흡수한다는 의미이므로 중동 영향권 설비는 보수적으로 순 5% 하향하고, 대체 조달 후보인 미국 설비는 같은 기간 제한적인 2.5% 상향으로 배분했다.",
      "values": [
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
          "rationale": "2026년 7월 해당 train 기준값 1.1814275778125545에 3개월 중간 차질과 50% 대체 조달을 반영한 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.1791218918448967에 동일한 3개월 순 차질 효과 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 0.951361502347418에 동일한 3개월 순 차질 효과 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.1814275778125545에 순 5% 하향(×0.95)을 적용해 중간 수준의 운송·공급 제약을 반영했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.1791218918448967에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 0.951361502347418에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 0.9179166666666667에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 0.9940277777777777에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 0.9876111111111111에 순 5% 하향(×0.95)을 적용했다."
        },
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
          "rationale": "2026년 7월 해당 train 기준값 1.0477010309278352에 호르무즈 관련 중간 차질의 순효과로 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779711340206186,
          "rationale": "2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0477010309278352에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779711340206186,
          "rationale": "2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0477010309278352에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779711340206186,
          "rationale": "2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476969696969696에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024848484848485에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779818181818182,
          "rationale": "2026년 9월 해당 train 기준값 1.0294545454545456에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476969696969696에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024848484848485에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779818181818182,
          "rationale": "2026년 9월 해당 train 기준값 1.0294545454545456에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9953170212765958,
          "rationale": "2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9953170212765958,
          "rationale": "2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9953170212765958,
          "rationale": "2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train 기준값 1.0956424079065634에 중동 항로 차질의 순효과 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
        },
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
          "proposedValue": 0.919568207996452,
          "rationale": "2026년 7월 해당 train 기준값 0.8971397151184897에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9318291174364048,
          "rationale": "2026년 8월 해당 train 기준값 0.9091015779867364에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9217929697899916,
          "rationale": "2026년 9월 해당 train 기준값 0.8993102144292602에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.919568207996452,
          "rationale": "2026년 7월 해당 train 기준값 0.8971397151184897에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9318291174364048,
          "rationale": "2026년 8월 해당 train 기준값 0.9091015779867364에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9217929697899916,
          "rationale": "2026년 9월 해당 train 기준값 0.8993102144292602에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.919568207996452,
          "rationale": "2026년 7월 해당 train 기준값 0.8971397151184897에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9318291174364048,
          "rationale": "2026년 8월 해당 train 기준값 0.9091015779867364에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9217929697899916,
          "rationale": "2026년 9월 해당 train 기준값 0.8993102144292602에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.053352130574862,
          "proposedValue": 1.0796859338392335,
          "rationale": "2026년 7월 해당 train 기준값 1.053352130574862에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.078634161835613,
          "proposedValue": 1.1056000158815034,
          "rationale": "2026년 8월 해당 train 기준값 1.078634161835613에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.107493424950098,
          "proposedValue": 1.1351807605738502,
          "rationale": "2026년 9월 해당 train 기준값 1.107493424950098에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.053352130574862,
          "proposedValue": 1.0796859338392335,
          "rationale": "2026년 7월 해당 train 기준값 1.053352130574862에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.078634161835613,
          "proposedValue": 1.1056000158815034,
          "rationale": "2026년 8월 해당 train 기준값 1.078634161835613에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.107493424950098,
          "proposedValue": 1.1351807605738502,
          "rationale": "2026년 9월 해당 train 기준값 1.107493424950098에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.106194690265487,
          "proposedValue": 1.133849557522124,
          "rationale": "2026년 7월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.106194690265487,
          "proposedValue": 1.133849557522124,
          "rationale": "2026년 8월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.106194690265487,
          "proposedValue": 1.133849557522124,
          "rationale": "2026년 9월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9887457459032464,
          "proposedValue": 1.0134643895508273,
          "rationale": "2026년 7월 해당 train 기준값 0.9887457459032463에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9964982077836354,
          "proposedValue": 1.0214106629782262,
          "rationale": "2026년 8월 해당 train 기준값 0.9964982077836354에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0039763425364874,
          "proposedValue": 1.0290757510998996,
          "rationale": "2026년 9월 해당 train 기준값 1.0039763425364874에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9867723949850288,
          "proposedValue": 1.0114417048596545,
          "rationale": "2026년 7월 해당 train 기준값 0.9867723949850288에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9945093844066656,
          "proposedValue": 1.0193721190168323,
          "rationale": "2026년 8월 해당 train 기준값 0.9945093844066657에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0019725942062196,
          "proposedValue": 1.027021909061375,
          "rationale": "2026년 9월 해당 train 기준값 1.0019725942062196에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.984798850195059,
          "proposedValue": 1.009418821449935,
          "rationale": "2026년 7월 해당 train 기준값 0.984798850195059에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9925203656378526,
          "proposedValue": 1.017333374778799,
          "rationale": "2026년 8월 해당 train 기준값 0.9925203656378526에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.9999686490178076,
          "proposedValue": 1.0249678652432528,
          "rationale": "2026년 9월 해당 train 기준값 0.9999686490178075에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 1.00245,
          "rationale": "2026년 7월 해당 train 기준값 0.978에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 1.00245,
          "rationale": "2026년 8월 해당 train 기준값 0.978에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 1.00245,
          "rationale": "2026년 9월 해당 train 기준값 0.978에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0065076455302508,
          "proposedValue": 1.031670336668507,
          "rationale": "2026년 7월 해당 train 기준값 1.0065076455302508에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0143993731929224,
          "proposedValue": 1.0397593575227455,
          "rationale": "2026년 8월 해당 train 기준값 1.0143993731929224에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0220118456958256,
          "proposedValue": 1.0475621418382213,
          "rationale": "2026년 9월 해당 train 기준값 1.0220118456958256에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9886406459054536,
          "proposedValue": 1.0133566620530896,
          "rationale": "2026년 7월 해당 train 기준값 0.9886406459054535에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9963922837279592,
          "proposedValue": 1.0213020908211583,
          "rationale": "2026년 8월 해당 train 기준값 0.9963922837279593에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.003869623582882,
          "proposedValue": 1.028966364172454,
          "rationale": "2026년 9월 해당 train 기준값 1.003869623582882에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0044946302391904,
          "proposedValue": 1.0296079959951705,
          "rationale": "2026년 7월 해당 train 기준값 1.0044946302391904에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0123705744465366,
          "proposedValue": 1.0376798388077,
          "rationale": "2026년 8월 해당 train 기준값 1.0123705744465366에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.019967822004434,
          "proposedValue": 1.0454670175545449,
          "rationale": "2026년 9월 해당 train 기준값 1.019967822004434에 2.5% 상향(×1.025)을 적용했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.772 | 3.772 | 3384 | 127 | 3511 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 02:15.632 | 135.632 | 12367 | 15323 | 27690 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:27.197 | 207.197 | 23341 | 15385 | 38726 |

#### event_type_l2_id=18 경제 제재 및 무역 제한

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "대체 공급 형성 time delay 존재",
      "dimension": "demand_response_alternative_lng (수요측 대응 - 타 공급원 경유 LNG 확보량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "자체 PowerMix 조정 수요 감소",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "영구 제재 시 종료 N/A",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "액화시설 가동률 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "생산량 직접 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "upstream 생산 차질 동반 시",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "Ref. 공급 차질 패턴",
      "dimension": "supply_disruption_pattern (공급 차질 - 발생/회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "제재 대상 계약 취소(partial→full) : 계약 취소·제재 물량은 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 차질로 확인되는 경우 Supply 계열 파라미터로 우회 반영",
      "dimension": "trade_restriction (거래 제한 (계약 취소 등))",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "그림자 선단 등 운송료 상승 : 운송료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 운송 제약이 공급량에 연결될 때만 기간·강도 판단에 사용",
      "dimension": "transport_disruption (운송 차질)",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [129, 130]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=129 3개월 내 제재 프리미엄은 제한적

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:16.716 (136.716s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 10 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=10, basecaseValue_present=7 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | PowerMix 조정 수요 감소 ‘100%’는 LNG 수요를 낮추기 위해 가스 발전 비중을 조정할 수 있음을 직접 의미하므로 이 parameter와 연결된다. 다만 기간은 3개월이고 공급 차질 강도도 낮아 연간 발전 믹스 입력값에는 제한적인 하향만 반영한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.0337 | 2026년 중국 Gas 발전 비중 기준값 0.0346에 대해, 3개월 동안의 낮은 강도 수급 리스크와 100% PowerMix 대응 가능성을 연간 값으로 희석해 반영했다. 단기 조정 효과만 보수적으로 적용해 최종 입력값은 0.0337로 산정한다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 113,
  "proposal_completed_dtm": "2026-07-07 23:46:00.185494",
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
      "rationale": "공급 차질 강도 ‘낮음’은 Arctic LNG 2의 액화시설 가동률을 직접 낮추는 요인이고, 타 공급원 경유 LNG 확보 ‘100%’는 부족분을 시장에서 상당 부분 상쇄해 가동률 하향 폭을 제한하는 요인으로 반영했다. 기간 3개월과 지연발생-단계적 회복 패턴을 공통 맥락으로 보아 초기에는 기준 수준을 유지하고 이후 월별로 완만하게 낮추는 구조로 제안한다.",
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
          "rationale": "2026년 7월은 3개월 시나리오의 첫 달이고 지연발생 패턴상 실제 물량 영향이 아직 본격화되기 전으로 보았다. 동일 연월 기준값 0.45를 유지해 최종 가동률 입력값을 0.45로 둔다."
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
          "rationale": "2026년 8월은 제재·선박 확인 절차에 따른 지연 영향이 일부 나타나는 구간으로 보되 차질 강도는 낮고 대체 LNG 확보가 가능하므로 기준값 0.45에서 소폭만 낮췄다. 최종 가동률 입력값은 0.44로 산정한다."
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
          "rationale": "2026년 9월은 3개월 범위 내에서 지연된 제재 영향이 가장 분명해질 수 있는 달로 보았다. 다만 낮은 차질 강도와 100% 대체 조달 가능성을 감안해 기준값 0.45에서 완만하게 낮춘 0.43을 최종 입력값으로 제안한다."
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
          "rationale": "2026년 7월은 지연발생 패턴의 초기 구간이므로 즉각적인 가동률 하향을 적용하지 않는다. 동일 연월 기준값 0.45를 유지해 최종 입력값을 0.45로 둔다."
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
          "proposedValue": 0.44,
          "rationale": "2026년 8월은 제재 관련 절차 지연이 일부 반영될 수 있는 시점이지만, 차질 강도가 낮고 대체 LNG 확보가 충분한 설정이다. 기준값 0.45에서 제한적으로 낮춘 0.44를 최종 입력값으로 산정한다."
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
          "proposedValue": 0.43,
          "rationale": "2026년 9월은 지연된 제재 영향이 가장 크게 반영될 수 있는 달로 보되, 실물 수급 압박은 제한적인 시나리오다. 기준값 0.45 대비 완만한 하향만 적용해 최종 입력값을 0.43으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 좌표에 일치하는 기준 레코드가 제공되지 않아 같은 프로젝트·동일 용량 train의 2026년 여름 기준 수준 0.45를 형식과 스케일 참고값으로 사용했다. 7월은 지연발생 초기 구간이므로 하향 조정 없이 최종 입력값을 0.45로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.44,
          "rationale": "해당 좌표의 직접 기준 레코드는 없으므로 같은 프로젝트 내 다른 train의 기준 수준 0.45를 참고했다. 8월에는 낮은 강도의 지연 영향만 반영해 0.44를 최종 입력값으로 제안한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.43,
          "rationale": "해당 좌표의 직접 기준 레코드는 없으므로 같은 프로젝트 내 다른 train의 0.45 수준을 보수적 기준으로 삼았다. 9월은 지연된 제재 영향이 가장 뚜렷할 수 있는 구간이지만 차질 강도와 시장 상쇄 여건을 감안해 최종 입력값을 0.43으로 낮춘다."
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
      "rationale": "PowerMix 조정 수요 감소 ‘100%’는 LNG 수요를 낮추기 위해 가스 발전 비중을 조정할 수 있음을 직접 의미하므로 이 parameter와 연결된다. 다만 기간은 3개월이고 공급 차질 강도도 낮아 연간 발전 믹스 입력값에는 제한적인 하향만 반영한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0337,
          "rationale": "2026년 중국 Gas 발전 비중 기준값 0.0346에 대해, 3개월 동안의 낮은 강도 수급 리스크와 100% PowerMix 대응 가능성을 연간 값으로 희석해 반영했다. 단기 조정 효과만 보수적으로 적용해 최종 입력값은 0.0337로 산정한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.140 | 4.140 | 2612 | 158 | 2770 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:46.632 | 46.632 | 12099 | 3384 | 15483 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:12.386 | 72.386 | 10357 | 4409 | 14766 |

##### scenario_id=130 1년 중반까지 완만한 조달 긴장 후 해소

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 04:42.747 (282.747s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 58 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=34, basecaseValue_present=34 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 22 | 수요측 대응 중 PowerMix 조정을 통한 LNG 수요 감소 50%는 가스 발전 비중을 낮춰 LNG 구매 필요량을 줄이는 방향으로 직접 연결되므로 PowerMix의 Gas 비중을 조정한다. 1년 기간이 연도 중간부터 다음 해 중반까지 걸쳐 있고 차질이 지연발생 후 해소되는 구조이므로, 연간 입력값에는 2026년에 더 완만한 하향, 2027년에 잔여 긴장을 반영한 소폭 추가 하향을 적용했다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.1862 | 2026년 Belgium Gas 기준 비중 0.19에 연중 부분적으로 나타나는 PowerMix 수요 절감 효과를 반영해 2% 하향한 0.1862로 산정했다. |
| 2 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2027}` | 0.18 | 0.1746 | 2027년 Belgium Gas 기준 비중 0.18에 해소 전 잔여 긴장을 반영해 3% 하향한 0.1746을 적용했다. |
| 3 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.033908 | 2026년 China Gas 기준 비중 0.0346에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.033908로 산정했다. |
| 4 | `{"Country": "China", "Energy Source": "Gas", "Year": 2027}` | 0.0365 | 0.035405 | 2027년 China Gas 기준 비중 0.0365에 해소 전까지의 잔여 PowerMix 조정 효과를 반영해 3% 낮춘 0.035405를 적용했다. |
| 5 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.04116 | 2026년 France Gas 기준 비중 0.042에 연중 부분적 조정 효과를 반영해 2% 하향한 0.04116으로 산정했다. |
| 6 | `{"Country": "France", "Energy Source": "Gas", "Year": 2027}` | 0.034 | 0.03298 | 2027년 France Gas 기준 비중 0.034에 잔여 긴장에 따른 PowerMix 조정 효과를 반영해 3% 하향한 0.03298을 적용했다. |
| 7 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.1323 | 2026년 Germany Gas 기준 비중 0.135에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.1323으로 산정했다. |
| 8 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2027}` | 0.13 | 0.1261 | 2027년 Germany Gas 기준 비중 0.13에 해소 전 잔여 조정 효과를 반영해 3% 낮춘 0.1261을 적용했다. |
| 9 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.42532 | 2026년 Italy Gas 기준 비중 0.434에 연중 부분적 PowerMix 조정 효과를 반영해 2% 하향한 0.42532로 산정했다. |
| 10 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2027}` | 0.422 | 0.40934 | 2027년 Italy Gas 기준 비중 0.422에 잔여 긴장 구간의 조정 효과를 반영해 3% 하향한 0.40934를 적용했다. |
| 11 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.31654 | 2026년 Japan Gas 기준 비중 0.323에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.31654로 산정했다. |
| 12 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2027}` | 0.318 | 0.30846 | 2027년 Japan Gas 기준 비중 0.318에 해소 전 잔여 PowerMix 조정 효과를 반영해 3% 낮춘 0.30846을 적용했다. |
| 13 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.3118258620689655 | 2026년 Netherlands Gas 기준 비중 0.31818965517241377에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.3118258620689655로 산정했다. |
| 14 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2027}` | 0.33707317073170734 | 0.3269609756097561 | 2027년 Netherlands Gas 기준 비중 0.33707317073170734에 잔여 긴장에 따른 조정 효과를 반영해 3% 낮춘 0.32696097560975613을 적용했다. |
| 15 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.2793 | 2026년 South Korea Gas 기준 비중 0.285에 연중 부분적인 PowerMix 수요 절감 효과를 반영해 2% 하향한 0.2793으로 산정했다. |
| 16 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2027}` | 0.265 | 0.25705 | 2027년 South Korea Gas 기준 비중 0.265에 해소 전 잔여 조정 효과를 반영해 3% 하향한 0.25705를 적용했다. |
| 17 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.20874 | 2026년 Spain Gas 기준 비중 0.213에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.20874로 산정했다. |
| 18 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2027}` | 0.211 | 0.20467 | 2027년 Spain Gas 기준 비중 0.211에 잔여 긴장 구간의 PowerMix 조정 효과를 반영해 3% 낮춘 0.20467을 적용했다. |
| 19 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2026}` | 0.474 | 0.46452 | 2026년 Taiwan (China) Gas 기준 비중 0.474에 연중 부분적인 수요 절감 효과를 반영해 2% 하향한 0.46452로 산정했다. |
| 20 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2027}` | 0.495 | 0.48015 | 2027년 Taiwan (China) Gas 기준 비중 0.495에 해소 전 잔여 조정 효과를 반영해 3% 하향한 0.48015를 적용했다. |
| 21 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.2842 | 2026년 United Kingdom Gas 기준 비중 0.29에 부분적인 연중 PowerMix 조정 효과를 반영해 2% 하향한 0.2842로 산정했다. |
| 22 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2027}` | 0.29 | 0.2813 | 2027년 United Kingdom Gas 기준 비중 0.29에 잔여 긴장 구간의 조정 효과를 반영해 3% 하향한 0.2813을 적용했다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 116,
  "proposal_completed_dtm": "2026-07-07 23:49:14.562382",
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
      "rationale": "공급 차질 강도 '중간'은 Arctic LNG 2의 제재·선박 운항 제약이 액화시설의 실제 가동률을 낮추는 방향으로 연결되므로 LiqUtilAdjustment를 조정한다. 대체 LNG 확보 50%는 수급 긴장을 일부 완화하지만 해당 러시아 프로젝트의 제재 리스크 자체를 제거하지는 못하므로, 1년 기간의 지연발생-즉시 해소 패턴에 맞춰 초기에는 제한적으로 낮추고 중반에 더 낮춘 뒤 해소 시점에는 기준 수준으로 복귀시키는 구조로 제안한다.",
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
          "rationale": "해당 월은 시나리오 시작 직후로 지연발생 패턴상 제재·운항 제약이 아직 누적되기 전이라고 보아 기준 가동률 0.45를 유지했다."
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
          "proposedValue": 0.4275,
          "rationale": "제재 집행과 선박 운항 제약이 누적되기 시작하는 구간으로 보아 기준 가동률 0.45에서 보수적으로 5% 낮춘 0.4275를 적용했다."
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
          "proposedValue": 0.3825,
          "rationale": "지연발생형 차질이 본격화되는 월로 보아 기준 가동률 0.45에서 중간 강도의 일부 반영치인 15% 하향을 적용해 0.3825로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "제재와 결제·보험·선박 제약의 누적 영향이 가장 뚜렷한 구간으로 보아 기준 가동률 0.45에서 25% 하향한 0.3375를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "해소 전까지 조달 긴장이 유지되는 월로 보아 직전 월과 같은 중간 강도 조정치를 유지해 기준 가동률 0.45 대비 25% 낮은 0.3375로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "시나리오상 허가·우회 조달 확인 후 즉시 해소되는 말기 구간으로 보아 기준 가동률 0.45를 회복하는 값을 적용했다."
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
          "rationale": "해당 월은 지연발생 패턴의 초기 구간이므로 기준 가동률 0.45를 유지했다."
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
          "proposedValue": 0.4275,
          "rationale": "건설·상업화 단계의 트레인도 제재 대상 프로젝트의 출하·거래 제약을 받는다고 보아 기준 가동률 0.45에서 5% 하향한 0.4275를 적용했다."
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
          "proposedValue": 0.3825,
          "rationale": "제재 영향이 누적되는 구간으로 보아 기준 가동률 0.45에서 15% 하향한 0.3825를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "중간 강도 차질이 가장 뚜렷하게 반영되는 월로 보아 기준 가동률 0.45에서 25% 하향한 0.3375를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "해소 전까지 운송·거래 제약이 유지되는 구간으로 보아 기준 가동률 0.45 대비 25% 낮춘 0.3375를 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "1년 시나리오의 말기에는 우회 조달과 허가 확인으로 차질이 즉시 해소되는 것으로 보아 기준 가동률 0.45를 회복시켰다."
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
      "rationale": "수요측 대응 중 PowerMix 조정을 통한 LNG 수요 감소 50%는 가스 발전 비중을 낮춰 LNG 구매 필요량을 줄이는 방향으로 직접 연결되므로 PowerMix의 Gas 비중을 조정한다. 1년 기간이 연도 중간부터 다음 해 중반까지 걸쳐 있고 차질이 지연발생 후 해소되는 구조이므로, 연간 입력값에는 2026년에 더 완만한 하향, 2027년에 잔여 긴장을 반영한 소폭 추가 하향을 적용했다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.1862,
          "rationale": "2026년 Belgium Gas 기준 비중 0.19에 연중 부분적으로 나타나는 PowerMix 수요 절감 효과를 반영해 2% 하향한 0.1862로 산정했다."
        },
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1746,
          "rationale": "2027년 Belgium Gas 기준 비중 0.18에 해소 전 잔여 긴장을 반영해 3% 하향한 0.1746을 적용했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.033908,
          "rationale": "2026년 China Gas 기준 비중 0.0346에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.033908로 산정했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.0365,
          "proposedValue": 0.035405,
          "rationale": "2027년 China Gas 기준 비중 0.0365에 해소 전까지의 잔여 PowerMix 조정 효과를 반영해 3% 낮춘 0.035405를 적용했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04116,
          "rationale": "2026년 France Gas 기준 비중 0.042에 연중 부분적 조정 효과를 반영해 2% 하향한 0.04116으로 산정했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03298,
          "rationale": "2027년 France Gas 기준 비중 0.034에 잔여 긴장에 따른 PowerMix 조정 효과를 반영해 3% 하향한 0.03298을 적용했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.1323,
          "rationale": "2026년 Germany Gas 기준 비중 0.135에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.1323으로 산정했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.1261,
          "rationale": "2027년 Germany Gas 기준 비중 0.13에 해소 전 잔여 조정 효과를 반영해 3% 낮춘 0.1261을 적용했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.42532,
          "rationale": "2026년 Italy Gas 기준 비중 0.434에 연중 부분적 PowerMix 조정 효과를 반영해 2% 하향한 0.42532로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.40934,
          "rationale": "2027년 Italy Gas 기준 비중 0.422에 잔여 긴장 구간의 조정 효과를 반영해 3% 하향한 0.40934를 적용했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.31654,
          "rationale": "2026년 Japan Gas 기준 비중 0.323에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.31654로 산정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.318,
          "proposedValue": 0.30846,
          "rationale": "2027년 Japan Gas 기준 비중 0.318에 해소 전 잔여 PowerMix 조정 효과를 반영해 3% 낮춘 0.30846을 적용했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3118258620689655,
          "rationale": "2026년 Netherlands Gas 기준 비중 0.31818965517241377에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.3118258620689655로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.3269609756097561,
          "rationale": "2027년 Netherlands Gas 기준 비중 0.33707317073170734에 잔여 긴장에 따른 조정 효과를 반영해 3% 낮춘 0.32696097560975613을 적용했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.2793,
          "rationale": "2026년 South Korea Gas 기준 비중 0.285에 연중 부분적인 PowerMix 수요 절감 효과를 반영해 2% 하향한 0.2793으로 산정했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.265,
          "proposedValue": 0.25705,
          "rationale": "2027년 South Korea Gas 기준 비중 0.265에 해소 전 잔여 조정 효과를 반영해 3% 하향한 0.25705를 적용했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.20874,
          "rationale": "2026년 Spain Gas 기준 비중 0.213에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.20874로 산정했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.20467,
          "rationale": "2027년 Spain Gas 기준 비중 0.211에 잔여 긴장 구간의 PowerMix 조정 효과를 반영해 3% 낮춘 0.20467을 적용했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.474,
          "proposedValue": 0.46452,
          "rationale": "2026년 Taiwan (China) Gas 기준 비중 0.474에 연중 부분적인 수요 절감 효과를 반영해 2% 하향한 0.46452로 산정했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.495,
          "proposedValue": 0.48015,
          "rationale": "2027년 Taiwan (China) Gas 기준 비중 0.495에 해소 전 잔여 조정 효과를 반영해 3% 하향한 0.48015를 적용했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.2842,
          "rationale": "2026년 United Kingdom Gas 기준 비중 0.29에 부분적인 연중 PowerMix 조정 효과를 반영해 2% 하향한 0.2842로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.2813,
          "rationale": "2027년 United Kingdom Gas 기준 비중 0.29에 잔여 긴장 구간의 조정 효과를 반영해 3% 하향한 0.2813을 적용했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.534 | 4.534 | 2623 | 171 | 2794 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:19.287 | 79.287 | 12110 | 8476 | 20586 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:01.082 | 181.082 | 14432 | 7189 | 21621 |

#### event_type_l2_id=18 경제 제재 및 무역 제한

##### Scenario Group

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
  "scenario_group_id": 23,
  "stage": "scenario_created",
  "status": "creating",
  "summary": "[러시아 LNG 제재] Arctic LNG 2 제재·지분 매각 허가 언급 → 무역 흐름 제약",
  "title": "러시아 Arctic LNG 2 제재 이슈"
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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "대체 공급 형성 time delay 존재",
      "dimension": "demand_response_alternative_lng (수요측 대응 - 타 공급원 경유 LNG 확보량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "자체 PowerMix 조정 수요 감소",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "영구 제재 시 종료 N/A",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "액화시설 가동률 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "생산량 직접 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "upstream 생산 차질 동반 시",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "Ref. 공급 차질 패턴",
      "dimension": "supply_disruption_pattern (공급 차질 - 발생/회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "제재 대상 계약 취소(partial→full) : 계약 취소·제재 물량은 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 차질로 확인되는 경우 Supply 계열 파라미터로 우회 반영",
      "dimension": "trade_restriction (거래 제한 (계약 취소 등))",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "그림자 선단 등 운송료 상승 : 운송료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 운송 제약이 공급량에 연결될 때만 기간·강도 판단에 사용",
      "dimension": "transport_disruption (운송 차질)",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [135, 136]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=135 3개월 내 제재 소음 흡수

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:49.706 (169.706s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "demand_response_alternative_lng": "100%",
    "demand_response_powermix_reduction": "100%",
    "period": "3개월",
    "supply_disruption_intensity": "낮음",
    "supply_disruption_pattern": "급차질-급회복"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "neutral"
  },
  "narrative": "기간은 3개월, 공급 차질 강도는 낮음으로 가정한다.\n패턴은 P1: Quick disrupt - Quick recover로, 제재 대상 선박·출하 이슈가 단기 지연 후 빠르게 정상화된다.\n타 공급원 경유 LNG 확보가 100%, PowerMix 조정에 따른 LNG 수요 감소도 100%로 작동해 물량 공백은 대부분 상쇄된다.\n시장 참여자는 Arctic LNG 2 헤드라인을 리스크 프리미엄으로 반영하지만, 실제 현물 조달 압박은 제한적으로 본다.",
  "probability_delta": 0.0,
  "probability_score": 35.0,
  "scenario_group_id": 23,
  "scenario_id": 135,
  "status": "creating",
  "title": "3개월 내 제재 소음 흡수"
}
```

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 10 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=10, basecaseValue_present=7 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 1 | PowerMix 조정을 통한 LNG 수요 감소량이 100%로 제시되어 중국의 가스 발전 비중을 낮추는 방향의 수요측 대응으로 연결된다. 다만 공급 차질 강도는 낮고 기간은 3개월의 단기 이벤트이므로 연간 PowerMix 입력에는 제한적인 하향 조정만 반영한다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.034 | 선택된 좌표는 2026년 중국 Gas 발전 비중으로, 기준값 0.0346에 3개월 단기 대응 효과를 연간 평균에 보수적으로 반영했다. 공급 차질 강도가 낮고 빠른 회복을 전제로 하므로 하향 폭은 작게 두어 최종 비중 0.0340을 적용한다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 115,
  "proposal_completed_dtm": "2026-07-07 23:47:52.893925",
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
      "rationale": "공급 차질 강도는 낮음으로 제시되어 Arctic LNG 2 액화시설 가동률에 제한적인 하향 조정으로 연결된다. 타 공급원 경유 LNG 확보가 100%로 작동하므로 시장 물량 공백은 완화되지만, 제재 대상 선박·출하 이슈에 따른 단기 운항 지연은 가동률 입력에 일부 반영한다. 기간은 3개월이고 급차질-급회복 패턴이므로 초기 월에 가장 큰 하향, 이후 빠른 회복 구조로 제안한다.",
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
          "proposedValue": 0.4,
          "rationale": "해당 월은 3개월 영향 구간의 첫 달로, 제재 대상 선박·출하 지연이 즉시 반영되는 구간이다. 기준 가동률 0.45에서 낮은 강도의 단기 차질을 보수적으로 반영해 약 0.05p 낮춘 최종 가동률 0.40을 적용한다."
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
          "proposedValue": 0.425,
          "rationale": "두 번째 달은 급차질 이후 회복이 시작되는 구간으로 본다. 기준 가동률 0.45 대비 하향 폭을 절반 수준으로 축소해 최종 가동률 0.425를 적용한다."
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
          "proposedValue": 0.45,
          "rationale": "세 번째 달은 빠른 회복이 마무리되는 구간으로, 낮은 차질 강도와 대체 조달 100% 전제를 감안해 추가 하향을 두지 않는다. 기준 가동률 0.45를 최종 입력값으로 유지한다."
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
          "proposedValue": 0.4,
          "rationale": "해당 월은 3개월 영향 구간의 첫 달이며, 같은 프로젝트 내 제재 관련 출하·거래 제약이 신규 train의 초기 가동에도 단기적으로 반영될 수 있는 구간이다. 기준 가동률 0.45에서 낮은 강도의 차질을 반영해 최종 가동률 0.40을 적용한다."
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
          "proposedValue": 0.425,
          "rationale": "두 번째 달은 급차질 이후 회복 단계로, 제재 소음의 실물 제약이 약화되는 것으로 본다. 기준 가동률 0.45 대비 하향 폭을 축소해 최종 가동률 0.425를 적용한다."
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
          "proposedValue": 0.45,
          "rationale": "세 번째 달은 빠른 회복 패턴에 따라 제재 관련 단기 지연이 대부분 흡수되는 구간으로 본다. 기준 가동률 0.45를 유지해 최종 입력값으로 적용한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.4,
          "rationale": "해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train에서 확인되는 0.45 수준을 형식과 스케일의 기준으로 삼았다. 영향 구간의 첫 달에는 낮은 강도의 단기 제재 차질을 반영해 최종 가동률 0.40을 적용한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.425,
          "rationale": "해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train 기준 수준을 참고했다. 두 번째 달은 빠른 회복 단계로 보아 첫 달보다 하향 폭을 줄인 최종 가동률 0.425를 적용한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train 기준 수준을 참고했다. 세 번째 달은 급회복 후 정상화 구간으로 보아 최종 가동률 0.45를 적용한다."
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
      "rationale": "PowerMix 조정을 통한 LNG 수요 감소량이 100%로 제시되어 중국의 가스 발전 비중을 낮추는 방향의 수요측 대응으로 연결된다. 다만 공급 차질 강도는 낮고 기간은 3개월의 단기 이벤트이므로 연간 PowerMix 입력에는 제한적인 하향 조정만 반영한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.034,
          "rationale": "선택된 좌표는 2026년 중국 Gas 발전 비중으로, 기준값 0.0346에 3개월 단기 대응 효과를 연간 평균에 보수적으로 반영했다. 공급 차질 강도가 낮고 빠른 회복을 전제로 하므로 하향 폭은 작게 두어 최종 비중 0.0340을 적용한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 23,
  "scenario_id": 135,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.590 | 4.590 | 2617 | 165 | 2782 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:19.412 | 79.412 | 12092 | 4950 | 17042 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:12.245 | 72.245 | 10350 | 3318 | 13668 |

##### scenario_id=136 1년짜리 구조적 결손을 절반씩 상쇄

- target_parameter: `PowerMix`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 05:18.011 (318.011s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "demand_response_alternative_lng": "50%",
    "demand_response_powermix_reduction": "50%",
    "period": "1년",
    "supply_disruption_intensity": "중간",
    "supply_disruption_pattern": "영구 손실"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "mild_bull"
  },
  "narrative": "기간은 1년, 공급 차질 강도는 중간으로 설정된다.\n패턴은 P4: Permanent loss로, Arctic LNG 2 관련 제재·지분 매각·선박 제약이 해당 기간 내 구조적 공급 손실처럼 작동한다.\n수요 측은 타 공급원 경유 LNG 50%와 PowerMix 조정 50%로 대응해 결손을 절반씩 나눠 흡수한다.\n다만 영구 손실 인식이 남아 아시아와 유럽 구매자는 장기 커버 물량 확보를 서두른다.",
  "probability_delta": 0.0,
  "probability_score": 20.0,
  "scenario_group_id": 23,
  "scenario_id": 136,
  "status": "creating",
  "title": "1년짜리 구조적 결손을 절반씩 상쇄"
}
```

###### Validation Summary

- target_expected_parameters: `["PowerMix"]`
- target_selected_parameters: `["PowerMix"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 58 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=58, basecaseValue_present=46 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | PowerMix | `{"modelFile": "Demand", "modelSheet": "PowerMixAdjustment", "tableName": "table1"}` | `["Year", "Country", "Energy Source"]` | `["% Power Mix"]` | 22 | PowerMix 조정을 통한 LNG 수요 감소 50%는 발전 부문에서 가스 의존도를 낮춰 공급 결손을 흡수하는 직접 경로이므로 Gas 발전 비중 조정 parameter와 연결된다. 기간이 1년이고 연간 입력값만 선택되어 있어 2026년과 2027년에 분산 반영하되, 아시아·유럽 구매국 전반의 mild bullish 수급 긴장을 해치지 않도록 각 연도 가스 비중을 보수적으로 소폭 하향했다. |

###### Proposed Parameter Values

###### Proposed Values - PowerMix

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2026}` | 0.19 | 0.18525 | 선택된 유럽 수요국의 2026년 Gas 발전 비중 기준값 0.19에 대해, 1년 영향이 연중 절반만 걸치는 점을 고려해 2.5% 상대 하향을 적용했다. |
| 2 | `{"Country": "Belgium", "Energy Source": "Gas", "Year": 2027}` | 0.18 | 0.1755 | 2027년은 영향 기간의 잔여 절반이 반영되는 연간 슬롯이다. 기준값 0.18을 2.5% 상대 하향해 0.1755로 산정했다. |
| 3 | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | 0.0346 | 0.033735 | 아시아 수요국의 2026년 Gas 발전 비중 기준값 0.0346에 대해, PowerMix 조정을 통한 수요 완화를 연간 기준 2.5% 상대 하향으로 반영했다. |
| 4 | `{"Country": "China", "Energy Source": "Gas", "Year": 2027}` | 0.0365 | 0.0355875 | 2027년 기준 Gas 비중 0.0365에 대해 1년 영향의 잔여 기간을 반영해 2.5% 상대 하향한 0.0355875를 적용했다. |
| 5 | `{"Country": "France", "Energy Source": "Gas", "Year": 2026}` | 0.042 | 0.04095 | 2026년 France Gas 발전 비중 기준값 0.042를 대상으로, 공급 결손 흡수용 PowerMix 조정분을 보수적 2.5% 상대 하향으로 반영했다. |
| 6 | `{"Country": "France", "Energy Source": "Gas", "Year": 2027}` | 0.034 | 0.03315 | 2027년 기준값 0.034에 대해 잔여 영향 기간의 수요 감축 효과를 반영해 0.03315로 낮췄다. |
| 7 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2026}` | 0.135 | 0.131625 | 2026년 Germany Gas 비중 기준값 0.135에 연간 절반 노출을 감안한 2.5% 상대 하향을 적용했다. |
| 8 | `{"Country": "Germany", "Energy Source": "Gas", "Year": 2027}` | 0.13 | 0.12675 | 2027년 기준값 0.13을 대상으로 PowerMix 수요 감축 효과를 2.5% 상대 하향으로 반영해 0.12675로 산정했다. |
| 9 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2026}` | 0.434 | 0.42315 | Italy는 Gas 발전 비중이 높은 유럽 수요국이므로 선택 슬롯을 직접 조정했다. 2026년 기준 0.434에 2.5% 상대 하향을 적용해 0.42315로 제안했다. |
| 10 | `{"Country": "Italy", "Energy Source": "Gas", "Year": 2027}` | 0.422 | 0.41145 | 2027년 Gas 비중 기준값 0.422에 대해 1년 영향의 잔여 절반을 반영한 2.5% 상대 하향으로 0.41145를 산정했다. |
| 11 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | 0.323 | 0.314925 | 아시아 LNG 구매국의 2026년 Gas 발전 비중 기준값 0.323에 대해 PowerMix 조정 수요 감소를 보수적으로 2.5% 상대 하향 반영했다. |
| 12 | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2027}` | 0.318 | 0.31005 | 2027년 기준값 0.318에 잔여 영향 기간의 가스 발전 축소를 적용해 0.31005로 낮췄다. |
| 13 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2026}` | 0.31818965517241377 | 0.3102349137931034 | 2026년 Netherlands Gas 비중 기준값 0.31818965517241377에 대해 연간 절반 노출에 해당하는 2.5% 상대 하향을 적용했다. |
| 14 | `{"Country": "Netherlands", "Energy Source": "Gas", "Year": 2027}` | 0.33707317073170734 | 0.32864634146341465 | 2027년 기준값 0.33707317073170734를 대상으로 잔여 영향 기간의 PowerMix 조정을 반영해 0.32864634146341466으로 산정했다. |
| 15 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2026}` | 0.285 | 0.277875 | 아시아 LNG 구매국인 South Korea의 2026년 Gas 비중 기준값 0.285에 2.5% 상대 하향을 적용해 수요 완화 효과를 반영했다. |
| 16 | `{"Country": "South Korea", "Energy Source": "Gas", "Year": 2027}` | 0.265 | 0.258375 | 2027년 기준 Gas 비중 0.265에 대해 1년 영향의 잔여 기간을 반영하여 0.258375로 조정했다. |
| 17 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2026}` | 0.213 | 0.207675 | 2026년 Spain Gas 발전 비중 기준값 0.213을 대상으로, PowerMix 조정에 따른 가스 수요 감소를 2.5% 상대 하향으로 반영했다. |
| 18 | `{"Country": "Spain", "Energy Source": "Gas", "Year": 2027}` | 0.211 | 0.205725 | 2027년 기준값 0.211에 대해 잔여 영향 기간의 수요 감축 효과를 적용해 0.205725로 낮췄다. |
| 19 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2026}` | 0.474 | 0.46215 | Taiwan (China)는 Gas 발전 비중이 높은 아시아 수요국으로, 2026년 기준값 0.474에 2.5% 상대 하향을 적용했다. |
| 20 | `{"Country": "Taiwan (China)", "Energy Source": "Gas", "Year": 2027}` | 0.495 | 0.482625 | 2027년 Gas 비중 기준값 0.495에 대해 1년 영향의 잔여 절반을 반영해 0.482625로 산정했다. |
| 21 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2026}` | 0.29 | 0.28275 | 2026년 United Kingdom Gas 비중 기준값 0.29에 대해 PowerMix 조정에 따른 가스 발전 축소를 2.5% 상대 하향으로 반영했다. |
| 22 | `{"Country": "United Kingdom", "Energy Source": "Gas", "Year": 2027}` | 0.29 | 0.28275 | 2027년 기준값도 0.29로 동일하며, 잔여 영향 기간의 수요 감축 효과를 같은 방식으로 반영해 0.28275를 적용했다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 119,
  "proposal_completed_dtm": "2026-07-07 23:51:18.195906",
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
      "rationale": "공급 차질 강도 ‘중간’은 Arctic LNG 2 액화설비의 가동률 하향 조정과 직접 연결되며, 타 공급원 경유 LNG 50%는 시장 결손을 일부 완화하지만 제재 대상 설비 자체의 생산 제약을 제거하지는 않는 것으로 해석했다. 기간 1년과 영구 손실 패턴은 2026년 7월부터 2027년 6월까지 구조적 가동 제약을 유지하는 방식으로 반영하고, 가동 중이거나 동일 프로젝트 내 선택된 train에 대해 보수적으로 중간 강도의 하향 값을 적용했다.",
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
          "proposedValue": 0.225,
          "rationale": "해당 월은 1년 제재 영향이 시작되는 Arctic LNG 2 T1의 직접 대상 구간이다. 기준 가동률 0.45에 중간 강도의 구조적 공급 제약을 50% 하향으로 반영해 최종 가동률을 0.225로 산정했다."
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
          "proposedValue": 0.225,
          "rationale": "제재에 따른 1년 구조적 제약이 지속되는 월로 보았다. 기준 가동률 0.45에 동일한 중간 강도 50% 하향을 적용해 0.225로 제안했다."
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
          "proposedValue": 0.225,
          "rationale": "Arctic LNG 2 T1의 제재 영향 지속 구간으로, 기준 가동률 0.45를 중간 차질 강도에 맞춰 절반 수준으로 낮췄다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "선박·거래 제약이 해소되지 않는 구조적 손실 구간으로 처리했다. 기준 0.45에서 50% 하향한 0.225를 최종 입력값으로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "1년 제재 시나리오의 연속 적용 월이며 기준 가동률이 존재한다. 중간 강도 공급 차질을 기준값의 50% 하향으로 반영해 0.225로 제안했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월의 기준 가동률이 이미 0이므로 추가 하향 여지가 없다. 제재 영향은 유지하되 최종 입력값은 기준과 같은 0으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "1년 영향 기간 안에 포함되지만 기준 가동률이 0이다. 공급 제약 반영 후에도 최종 가동률은 0으로 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준값이 0인 비가동 월이므로 제재 차질을 별도 음수 조정으로 표현하지 않았다. 최종 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 이미 0으로 설정된 월이다. 구조적 제재 리스크가 지속되더라도 최종 모델 입력은 0으로 유지한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월은 기준 가동률이 0이므로 중간 차질을 추가로 수치화하지 않았다. 최종 가동률은 0으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 0인 구간으로, 제재 영향은 유지되지만 입력값은 기준 형식과 동일하게 0을 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "1년 영향 기간의 마지막 월로 기준 가동률이 0.45로 회복되는 구간이다. 영구 손실 성격이 남는 중간 강도 제약을 반영해 50% 하향한 0.225를 적용했다."
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
          "proposedValue": 0.225,
          "rationale": "동일 프로젝트 내 T2도 제재·선박 제약의 직접 대상 train으로 보았다. 기준 가동률 0.45에 중간 강도의 구조적 제약을 50% 반영해 0.225로 낮췄다."
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
          "proposedValue": 0.225,
          "rationale": "제재 영향이 지속되는 월로, 기준 0.45의 절반 수준만 실현되는 것으로 보수적으로 산정했다."
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
          "proposedValue": 0.225,
          "rationale": "T2의 선택 슬롯 중 기준 가동률이 존재하는 월이다. 중간 공급 차질을 기준값의 50% 하향으로 반영해 0.225를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "무역·선박 제한이 이어지는 구조적 제약 구간이다. 기준 0.45에서 중간 강도 하향을 적용해 최종 0.225로 제안했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "해당 월의 기준 가동률 0.45를 제재에 따른 중간 수준의 구조적 손실로 절반 낮춰 0.225로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 0인 월이므로 제재 영향을 추가 감산 수치로 표현하지 않고 0을 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "영향 기간 안의 월이지만 기준 가동률이 0이다. 최종 입력값은 기준과 동일한 0으로 설정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준값이 0인 비가동 구간으로 판단해 추가적인 하향 조정 없이 0을 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 0으로 설정되어 있어 제재 영향 반영 후에도 최종 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월은 기준 가동률이 없는 수준이므로 중간 차질을 별도 감산으로 더하지 않고 0을 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준값 0인 구간으로, 최종 모델 입력도 0으로 설정해 과도한 임의 조정을 피했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "1년 영향 기간의 말월에 기준 가동률 0.45가 존재한다. 제재의 영구 손실 성격을 반영해 절반 수준인 0.225로 낮췄다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "T3의 직접 기준 record는 없지만 동일 Arctic LNG 2 프로젝트와 동일 용량의 선택 슬롯이므로 T1·T2의 기준 패턴을 형식 참고로 사용했다. 제재 영향이 시작되는 월에는 보수적으로 0.45 상당 기준의 50%인 0.225를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "동일 프로젝트 내 train으로 제재의 적용 대상에 포함된다고 보았다. 직접 기준값 부재로 T1·T2의 같은 계절 패턴을 참고해 중간 차질 반영 후 0.225를 제안했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "T3는 기준 record가 없으므로 같은 프로젝트 train의 0.45 가동 구간을 보수적 기준으로 삼았다. 중간 강도 제재 영향으로 절반 수준인 0.225를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "동일 프로젝트의 제재 지속 월로, 직접 기준값이 없어 T1·T2의 같은 월 기준 수준을 참고했다. 구조적 중간 차질을 반영해 0.225로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "T3도 선박·거래 제약의 프로젝트 단위 영향권으로 보았다. 같은 프로젝트의 기준 패턴을 참고해 0.45 상당의 절반인 0.225를 최종값으로 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "직접 기준 record는 없지만 같은 프로젝트 train의 해당 월 기준 패턴이 0인 구간이다. 보수적으로 비가동 유지값 0을 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "T1·T2의 같은 계절 구간이 0으로 설정되어 있어 T3도 직접 기준 부재하에서 0을 보수적 유지값으로 사용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "직접 기준값은 없지만 같은 프로젝트의 기준 패턴상 비가동 구간으로 보았다. 최종 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "동일 프로젝트 train의 참고 패턴상 기준값이 0인 구간이므로, 제재 영향 반영 후에도 0으로 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "직접 record가 없는 T3에 대해 같은 프로젝트의 비가동 월 패턴을 참고했다. 불확실성을 고려해 0을 보수적 최종값으로 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "같은 프로젝트 train의 기준 패턴상 0인 구간으로 보아 T3도 0으로 두었다. 직접 기준값 부재에 따른 임의 증액은 적용하지 않았다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "1년 영향 기간의 마지막 월이며 같은 프로젝트 train의 참고 기준 패턴은 가동 재개 수준을 보인다. 직접 기준값이 없어 0.45 상당을 보수적 기준으로 삼고 중간 차질 50%를 반영해 0.225로 산정했다."
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
      "rationale": "PowerMix 조정을 통한 LNG 수요 감소 50%는 발전 부문에서 가스 의존도를 낮춰 공급 결손을 흡수하는 직접 경로이므로 Gas 발전 비중 조정 parameter와 연결된다. 기간이 1년이고 연간 입력값만 선택되어 있어 2026년과 2027년에 분산 반영하되, 아시아·유럽 구매국 전반의 mild bullish 수급 긴장을 해치지 않도록 각 연도 가스 비중을 보수적으로 소폭 하향했다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.18525,
          "rationale": "선택된 유럽 수요국의 2026년 Gas 발전 비중 기준값 0.19에 대해, 1년 영향이 연중 절반만 걸치는 점을 고려해 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1755,
          "rationale": "2027년은 영향 기간의 잔여 절반이 반영되는 연간 슬롯이다. 기준값 0.18을 2.5% 상대 하향해 0.1755로 산정했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.033735,
          "rationale": "아시아 수요국의 2026년 Gas 발전 비중 기준값 0.0346에 대해, PowerMix 조정을 통한 수요 완화를 연간 기준 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.0365,
          "proposedValue": 0.0355875,
          "rationale": "2027년 기준 Gas 비중 0.0365에 대해 1년 영향의 잔여 기간을 반영해 2.5% 상대 하향한 0.0355875를 적용했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04095,
          "rationale": "2026년 France Gas 발전 비중 기준값 0.042를 대상으로, 공급 결손 흡수용 PowerMix 조정분을 보수적 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03315,
          "rationale": "2027년 기준값 0.034에 대해 잔여 영향 기간의 수요 감축 효과를 반영해 0.03315로 낮췄다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.131625,
          "rationale": "2026년 Germany Gas 비중 기준값 0.135에 연간 절반 노출을 감안한 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.12675,
          "rationale": "2027년 기준값 0.13을 대상으로 PowerMix 수요 감축 효과를 2.5% 상대 하향으로 반영해 0.12675로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.42315,
          "rationale": "Italy는 Gas 발전 비중이 높은 유럽 수요국이므로 선택 슬롯을 직접 조정했다. 2026년 기준 0.434에 2.5% 상대 하향을 적용해 0.42315로 제안했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.41145,
          "rationale": "2027년 Gas 비중 기준값 0.422에 대해 1년 영향의 잔여 절반을 반영한 2.5% 상대 하향으로 0.41145를 산정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.314925,
          "rationale": "아시아 LNG 구매국의 2026년 Gas 발전 비중 기준값 0.323에 대해 PowerMix 조정 수요 감소를 보수적으로 2.5% 상대 하향 반영했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.318,
          "proposedValue": 0.31005,
          "rationale": "2027년 기준값 0.318에 잔여 영향 기간의 가스 발전 축소를 적용해 0.31005로 낮췄다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3102349137931034,
          "rationale": "2026년 Netherlands Gas 비중 기준값 0.31818965517241377에 대해 연간 절반 노출에 해당하는 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.32864634146341465,
          "rationale": "2027년 기준값 0.33707317073170734를 대상으로 잔여 영향 기간의 PowerMix 조정을 반영해 0.32864634146341466으로 산정했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.277875,
          "rationale": "아시아 LNG 구매국인 South Korea의 2026년 Gas 비중 기준값 0.285에 2.5% 상대 하향을 적용해 수요 완화 효과를 반영했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.265,
          "proposedValue": 0.258375,
          "rationale": "2027년 기준 Gas 비중 0.265에 대해 1년 영향의 잔여 기간을 반영하여 0.258375로 조정했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.207675,
          "rationale": "2026년 Spain Gas 발전 비중 기준값 0.213을 대상으로, PowerMix 조정에 따른 가스 수요 감소를 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.205725,
          "rationale": "2027년 기준값 0.211에 대해 잔여 영향 기간의 수요 감축 효과를 적용해 0.205725로 낮췄다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.474,
          "proposedValue": 0.46215,
          "rationale": "Taiwan (China)는 Gas 발전 비중이 높은 아시아 수요국으로, 2026년 기준값 0.474에 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.495,
          "proposedValue": 0.482625,
          "rationale": "2027년 Gas 비중 기준값 0.495에 대해 1년 영향의 잔여 절반을 반영해 0.482625로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "2026년 United Kingdom Gas 비중 기준값 0.29에 대해 PowerMix 조정에 따른 가스 발전 축소를 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "2027년 기준값도 0.29로 동일하며, 잔여 영향 기간의 수요 감축 효과를 같은 방식으로 반영해 0.28275를 적용했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 23,
  "scenario_id": 136,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.876 | 3.876 | 2625 | 166 | 2791 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:50.766 | 110.766 | 12088 | 9573 | 21661 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:00.542 | 180.542 | 14410 | 9905 | 24315 |

#### event_type_l2_id=19 정책/규제 변화

##### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 19,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 48,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 정책/규제 routing 검증"
}
```

##### Dimension Template

```json
[]
```

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [],
  "event_type_l2_id": null,
  "mapping_count": 0,
  "source_tables": [
    "tmm_mi_model_param_dimension_map",
    "tmm_mi_model_param_m"
  ]
}
```

##### Event

```json
{
  "created_at": null,
  "detail_analysis": "",
  "event_title_ko": null,
  "event_type_l2_id": null,
  "key_bullets": [],
  "latest_record_first_created": null,
  "mi_event_id": null,
  "occurred_at": null,
  "oldest_record_first_created": null,
  "one_line_summary": null,
  "source_mi_record_ids": null,
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [281, 282]
- scenario_count: 2
- 매핑 후보 검증: FAIL
- LLM selected 검증: FAIL
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

- ERROR scenario_id=281 elapsed=00:56.958 (56.958s): `MIBaseError('[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id=281: Step2 selected slot이 없어 Step3 value proposal LLM 호출을 생략했습니다.')`
- ERROR scenario_id=282 elapsed=00:56.764 (56.764s): `MIBaseError('[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id=282: Step2 selected slot이 없어 Step3 value proposal LLM 호출을 생략했습니다.')`

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
      "comment": "기온 직접 입력(대안 경로) : 한파 영향 국가·월의 Temperature를 하향 조정하고, 강도에 따라 평년 대비 온도 편차를 월별로 차등 적용",
      "dimension": "cold_wave_intensity (한파 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 -℃ → HDD(난방도일) 변환 입력 : HDD는 미대상 파라미터이므로 직접 조정하지 않고, 한파 강도는 Temperature 하향 또는 강도·월 분배 판단 근거로만 사용",
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

- 대상 scenario_ids: [289, 290]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=289 [model_parameter_agent_test] 짧은 약한 한파와 전원 흡수

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:49.127 (109.127s)
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
| Step3 value 결과 | value_cells=1, basecaseValue_present=1 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 1 | 한파 강도 dimension이 기온 직접 입력의 하향 조정과 연결되므로, 영향 국가·월의 Temperature를 낮추는 방식으로 반영한다. 기간은 1개월 이하이고 단발 피크 성격이므로 적용 범위는 이벤트가 명시된 월의 미국 월간 기온 슬롯으로 제한하며, 재고 여유는 수급 완화 맥락으로만 보아 기온 입력 자체를 추가로 보정하지 않는다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Month": 3, "Year": 2026}` | [10.4, 9.2, 5.4, 4.9, 8.5, 6.4, 11.3, 10.2, 6.7, 6.7] | 5.5 | 선택 좌표에 미국 2026년 3월 직접 기준값이 없어 제공된 2026년 3월 국가별 Temperature 기준값의 평균 수준인 약 8.0℃를 같은 형식의 보수적 기준으로 사용했다. 약한 한파 강도인 -2~-3℃ 범위의 중앙값 2.5℃ 하향을 적용해 최종 월간 기온 입력값을 5.5℃로 산정했다. |

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
  "model_param_proposal_id": 95,
  "proposal_completed_dtm": "2026-07-07 23:35:47.339484",
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
      "rationale": "한파 강도 dimension이 기온 직접 입력의 하향 조정과 연결되므로, 영향 국가·월의 Temperature를 낮추는 방식으로 반영한다. 기간은 1개월 이하이고 단발 피크 성격이므로 적용 범위는 이벤트가 명시된 월의 미국 월간 기온 슬롯으로 제한하며, 재고 여유는 수급 완화 맥락으로만 보아 기온 입력 자체를 추가로 보정하지 않는다.",
      "values": [
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2026,
          "basecaseValue": [
            10.4,
            9.2,
            5.4,
            4.9,
            8.5,
            6.4,
            11.3,
            10.2,
            6.7,
            6.7
          ],
          "proposedValue": 5.5,
          "rationale": "선택 좌표에 미국 2026년 3월 직접 기준값이 없어 제공된 2026년 3월 국가별 Temperature 기준값의 평균 수준인 약 8.0℃를 같은 형식의 보수적 기준으로 사용했다. 약한 한파 강도인 -2~-3℃ 범위의 중앙값 2.5℃ 하향을 적용해 최종 월간 기온 입력값을 5.5℃로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.456 | 4.456 | 2396 | 121 | 2517 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:11.763 | 11.763 | 5917 | 661 | 6578 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:19.532 | 79.532 | 7572 | 2716 | 10288 |

##### scenario_id=290 [model_parameter_agent_test] 3개월 강한 한파와 대체 제한

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 03:00.635 (180.635s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["Temperature"]`
- target_selected_parameters: `["Temperature"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 3 | 한파 강도 dimension은 국가·월별 기온 입력값을 직접 낮추는 parameter 의미와 연결되며, 강한 한파는 난방 수요 확대를 반영하기 위해 Temperature 하향 조정으로 해석된다. 기간과 지속 피크 정보는 선택된 3개월 구간에 한파 영향이 완만히 분산되지 않고 지속 적용되는 구조로 반영하되, 재고 부족 정보는 수치 강도 산정이 아니라 수급 긴장 맥락으로만 참고했다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "Month": 1, "Year": 2026}` | null | -4.5 | 해당 미국 월 좌표에는 일치하는 기준값이 없어, 제공된 다른 국가들의 월별 °C 입력 형식과 계절 패턴만 참고했다. 강한 한파를 평년 대비 약 5℃ 내외의 하향 충격으로 보수적으로 반영하되 겨울철 계절성을 유지하여 최종 기온을 -4.5℃로 제안한다. |
| 2 | `{"Country": "United States", "Month": 2, "Year": 2026}` | null | -3 | 해당 미국 월 좌표에는 일치하는 기준값이 없어, 제공된 월별 기온 값의 스케일과 소수 형식만 참고했다. 3개월 지속 피크 조건에 따라 전월과 유사한 강한 하향 충격을 유지하되 월별 계절 상승을 일부 반영하여 최종 기온을 -3.0℃로 제안한다. |
| 3 | `{"Country": "United States", "Month": 3, "Year": 2026}` | null | 0.5 | 해당 미국 월 좌표에는 일치하는 기준값이 없어, 다른 국가의 3월 기온 범위는 형식과 계절성 참고용으로만 사용했다. 이벤트가 3월 중순 한파 전망을 포함하고 시나리오가 3개월 지속을 가정하므로 강한 하향 충격을 계속 적용하되 봄철 전환 효과를 일부 남겨 최종 기온을 0.5℃로 제안한다. |

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
  "model_param_proposal_id": 98,
  "proposal_completed_dtm": "2026-07-07 23:37:18.182425",
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
      "rationale": "한파 강도 dimension은 국가·월별 기온 입력값을 직접 낮추는 parameter 의미와 연결되며, 강한 한파는 난방 수요 확대를 반영하기 위해 Temperature 하향 조정으로 해석된다. 기간과 지속 피크 정보는 선택된 3개월 구간에 한파 영향이 완만히 분산되지 않고 지속 적용되는 구조로 반영하되, 재고 부족 정보는 수치 강도 산정이 아니라 수급 긴장 맥락으로만 참고했다.",
      "values": [
        {
          "Country": "United States",
          "Month": 1,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -4.5,
          "rationale": "해당 미국 월 좌표에는 일치하는 기준값이 없어, 제공된 다른 국가들의 월별 °C 입력 형식과 계절 패턴만 참고했다. 강한 한파를 평년 대비 약 5℃ 내외의 하향 충격으로 보수적으로 반영하되 겨울철 계절성을 유지하여 최종 기온을 -4.5℃로 제안한다."
        },
        {
          "Country": "United States",
          "Month": 2,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": -3,
          "rationale": "해당 미국 월 좌표에는 일치하는 기준값이 없어, 제공된 월별 기온 값의 스케일과 소수 형식만 참고했다. 3개월 지속 피크 조건에 따라 전월과 유사한 강한 하향 충격을 유지하되 월별 계절 상승을 일부 반영하여 최종 기온을 -3.0℃로 제안한다."
        },
        {
          "Country": "United States",
          "Month": 3,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.5,
          "rationale": "해당 미국 월 좌표에는 일치하는 기준값이 없어, 다른 국가의 3월 기온 범위는 형식과 계절성 참고용으로만 사용했다. 이벤트가 3월 중순 한파 전망을 포함하고 시나리오가 3개월 지속을 가정하므로 강한 하향 충격을 계속 적용하되 봄철 전환 효과를 일부 남겨 최종 기온을 0.5℃로 제안한다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension은 발전 믹스에서 가스 외 에너지원이 추가 전력 수요를 얼마나 대체할 수 있는지를 나타내므로 PowerMix의 Gas 비중 조정과 직접 연결된다. 흡수 가능성이 낮은 편이어서 한파에 따른 전력 수요 증가분의 상당 부분이 가스 발전으로 남는 방향을 반영하되, 3개월 충격이 연간 비중 입력에 반영되는 점을 고려해 연간 Gas share는 제한적으로 상향 조정한다.",
      "values": [
        {
          "Country": "United States",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 미국 Gas 발전 비중 좌표에는 일치하는 기준값이 없어, 제공된 다른 국가의 Gas share 값은 단위가 0~1 비율 형식임을 확인하는 용도로만 참고했다. 타 에너지원 흡수 가능성이 25%로 낮아 추가 전력 수요의 대부분이 가스 발전에 남는다고 보되, 3개월 한파가 연간 발전 믹스에 미치는 효과를 연간화하여 최종 Gas 비중을 0.45로 제안한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:17.123 | 17.123 | 2389 | 109 | 2498 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:55.057 | 55.057 | 5906 | 3167 | 9073 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:34.112 | 94.112 | 7637 | 3223 | 10860 |

#### event_type_l2_id=6 겨울 한파

##### Scenario Group

```json
{
  "description": "유럽 한파 이벤트에 대해 기간/강도/재고/대체 흡수 조합을 확장해 생성한 테스트 scenario group",
  "dimension_selected": [
    "period",
    "cold_wave_intensity",
    "entry_gas_inventory",
    "peak_timing_pattern",
    "alt_energy_absorption"
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
  "mi_event_id": 1378,
  "request_usr_id": null,
  "scenario_count": 4,
  "scenario_group_id": 61,
  "stage": "scenario_created",
  "status": "created",
  "summary": "최근 한파/폭염 이벤트 기반 수급모델 파라미터 제안 확장 테스트",
  "title": "[model_parameter_agent_weather_ext_20260630] 한파 이벤트 1378 수급모델 파라미터 테스트"
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
      "comment": "기온 직접 입력(대안 경로) : 한파 영향 국가·월의 Temperature를 하향 조정하고, 강도에 따라 평년 대비 온도 편차를 월별로 차등 적용",
      "dimension": "cold_wave_intensity (한파 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 -℃ → HDD(난방도일) 변환 입력 : HDD는 미대상 파라미터이므로 직접 조정하지 않고, 한파 강도는 Temperature 하향 또는 강도·월 분배 판단 근거로만 사용",
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
  "created_at": "2026-06-21T00:42:17.070147",
  "detail_analysis": "사건 요약:\nWoodMac weekly summary가 2026년 5월 14일 글로벌 가스·LNG 시장에서 유럽 한파에 따른 수요 증가를 가격 상승 요인으로 언급함. 직전 요약의 유럽 전역 이례적 한파에 따른 난방 수요 증가 흐름이 신규 리포트에서도 재확인됨. 신규 Record에는 아시아 현물 조달 확대와 북미 LNG 설비 정비도 함께 언급됐으나, 본 Event Type은 수요 > 겨울 한파이므로 핵심 사건은 유럽 한파 수요 증가로 한정됨.\n\n영향 경로:\n유럽 한파는 주거·상업 난방 수요를 확대해 천연가스 소비 증가로 연결되는 요인임. 가스 수요 증가는 저장 재고 소진 속도와 LNG 수입 필요성을 높이는 경로로 작용할 수 있음. 신규 리포트상 글로벌 가격 상승 구도에는 아시아 현물 조달 확대와 북미 LNG 설비 정비도 포함되나, 이는 본 Event의 직접 원인이 아니라 동시 발생한 별도 수급 요인임.\n\n시장 반응:\nWoodMac weekly summary는 2026년 5월 14일 유럽 한파 수요 증가와 다른 수급 요인이 동시에 가격을 끌어올리는 구도라고 평가함. 유럽 가스 수요 증가는 TTF 계약 가격 상승 압력과 겨울 프리미엄 지지 요인으로 반영됨. Record에 구체적인 가격 Band나 Forward 수치는 제시되지 않음.\n\nLNG 시장 관점:\n유럽 한파는 LNG 설비 이슈가 아니라 가스 소비 증가를 통한 수요 측 Event임. 난방 수요 확대는 유럽의 LNG 현물 흡수 여력과 조달 필요성을 높일 수 있음. 같은 시점의 아시아 현물 조달 확대와 결합될 경우 유럽과 아시아 간 카고 경쟁 및 글로벌 LNG 가격 지지 압력으로 연결될 수 있음.",
  "event_title_ko": "유럽 한파로 가스 수요 증가",
  "event_type_l2_id": 6,
  "key_bullets": [],
  "latest_record_first_created": "2026-05-14T00:00:00",
  "mi_event_id": "1378",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[유럽 난방수요] 5월 14일 WoodMac이 한파 수요 증가 언급 → TTF 가격 지지",
  "source_mi_record_ids": [
    2235
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [307, 308]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=307 [model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 한파

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:56.326 (116.326s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "alt_energy_absorption": "100%",
    "cold_wave_intensity": "-2~-3℃: 약",
    "entry_gas_inventory": "+20%↑ (매우 여유)",
    "peak_timing_pattern": "12월 Peak",
    "period": "1개월 이하"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "neutral",
    "ttf": "up"
  },
  "narrative": "이벤트 1378 기반 확장 테스트 시나리오입니다. 기간=1개월 이하, 강도=-2~-3℃: 약, 대체흡수=100% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 25.0,
  "scenario_group_id": 61,
  "scenario_id": 307,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 한파"
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

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 14 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=14, basecaseValue_present=14 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 7 | 한파 강도 dimension이 국가·월별 기온 입력값을 직접 낮추는 경로와 연결되므로 Temperature 조정 대상으로 선택한다. 기간은 1개월 이하이고 피크 패턴은 12월로 제시되어 2026년 12월의 선택 국가에 한정해 약한 한파에 해당하는 보수적 하향 편차를 적용한다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Month": 12, "Year": 2026}` | 3.5 | 1 | Belgium 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 3.5°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 1.0°C로 산정했다. |
| 2 | `{"Country": "France", "Month": 12, "Year": 2026}` | 5.1 | 2.6 | France 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 5.1°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 2.6°C로 산정했다. |
| 3 | `{"Country": "Germany", "Month": 12, "Year": 2026}` | 1.2 | -1.3 | Germany 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 1.2°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 -1.3°C로 산정했다. |
| 4 | `{"Country": "Italy", "Month": 12, "Year": 2026}` | 6.8 | 4.3 | Italy 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 6.8°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 4.3°C로 산정했다. |
| 5 | `{"Country": "Netherlands", "Month": 12, "Year": 2026}` | 3.7 | 1.2 | Netherlands 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 3.7°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 1.2°C로 산정했다. |
| 6 | `{"Country": "Spain", "Month": 12, "Year": 2026}` | 7.9 | 5.4 | Spain 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 7.9°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 5.4°C로 산정했다. |
| 7 | `{"Country": "United Kingdom", "Month": 12, "Year": 2026}` | 4.8 | 2.3 | United Kingdom 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 4.8°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 2.3°C로 산정했다. |

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
  "mi_event_id": 1378,
  "model_param_proposal_id": 96,
  "proposal_completed_dtm": "2026-07-07 23:36:29.197548",
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
      "rationale": "한파 강도 dimension이 국가·월별 기온 입력값을 직접 낮추는 경로와 연결되므로 Temperature 조정 대상으로 선택한다. 기간은 1개월 이하이고 피크 패턴은 12월로 제시되어 2026년 12월의 선택 국가에 한정해 약한 한파에 해당하는 보수적 하향 편차를 적용한다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 3.5,
          "proposedValue": 1,
          "rationale": "Belgium 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 3.5°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 1.0°C로 산정했다."
        },
        {
          "Country": "France",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 5.1,
          "proposedValue": 2.6,
          "rationale": "France 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 5.1°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 2.6°C로 산정했다."
        },
        {
          "Country": "Germany",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 1.2,
          "proposedValue": -1.3,
          "rationale": "Germany 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 1.2°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 -1.3°C로 산정했다."
        },
        {
          "Country": "Italy",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 6.8,
          "proposedValue": 4.3,
          "rationale": "Italy 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 6.8°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 4.3°C로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 3.7,
          "proposedValue": 1.2,
          "rationale": "Netherlands 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 3.7°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 1.2°C로 산정했다."
        },
        {
          "Country": "Spain",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 7.9,
          "proposedValue": 5.4,
          "rationale": "Spain 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 7.9°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 5.4°C로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 4.8,
          "proposedValue": 2.3,
          "rationale": "United Kingdom 2026년 12월 선택 슬롯에는 직접 기준값이 없어 같은 국가의 겨울 기준으로 제공된 2026년 1월 4.8°C를 형식·스케일 기준으로 사용했다. 약한 한파 강도 -2~-3°C의 중간값인 2.5°C 하향을 적용해 최종 입력값을 2.3°C로 산정했다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension은 발전 믹스에서 가스 발전 비중을 조정할 수 있는 경로와 직접 연결된다. 흡수 가능성이 100%로 제시되어 단기 한파에 따른 추가 에너지 수요가 비가스 전원으로 완전히 흡수되는 설정이므로, 연간 Gas 발전 비중은 기준값을 유지하는 방식으로 제안한다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19,
          "rationale": "Belgium 2026년 Gas 발전 비중의 기준값은 0.19이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.19를 최종 입력값으로 유지했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "France 2026년 Gas 발전 비중의 기준값은 0.042이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.042를 최종 입력값으로 유지했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.135,
          "rationale": "Germany 2026년 Gas 발전 비중의 기준값은 0.135이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.135를 최종 입력값으로 유지했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.434,
          "rationale": "Italy 2026년 Gas 발전 비중의 기준값은 0.434이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.434를 최종 입력값으로 유지했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.31818965517241377,
          "rationale": "Netherlands 2026년 Gas 발전 비중의 기준값은 0.31818965517241377이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.31818965517241377을 최종 입력값으로 유지했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.213,
          "rationale": "Spain 2026년 Gas 발전 비중의 기준값은 0.213이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.213을 최종 입력값으로 유지했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29,
          "rationale": "United Kingdom 2026년 Gas 발전 비중의 기준값은 0.29이다. 대체 에너지원 흡수 가능성이 100%이고 이벤트가 1개월 이하 단기이므로 연간 Gas 비중을 추가 상향하지 않고 기준값 0.29를 최종 입력값으로 유지했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 61,
  "scenario_id": 307,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.723 | 3.723 | 2313 | 126 | 2439 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:24.394 | 24.394 | 5830 | 1831 | 7661 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:06.499 | 66.499 | 7939 | 3057 | 10996 |

##### scenario_id=308 [model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 한파

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:18.354 (138.354s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "50%",
    "cold_wave_intensity": "-3~-5℃: 중",
    "entry_gas_inventory": "±5% (정상)",
    "peak_timing_pattern": "1월 Peak",
    "period": "3개월"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "up",
    "ttf": "up"
  },
  "narrative": "이벤트 1378 기반 확장 테스트 시나리오입니다. 기간=3개월, 강도=-3~-5℃: 중, 대체흡수=50% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 25.0,
  "scenario_group_id": 61,
  "scenario_id": 308,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 한파"
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

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 28 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=28, basecaseValue_present=28 | PASS |
| Step2 slot axis value 수 | `{"6|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "6|coldwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 21 | 한파 강도 차원이 Temperature의 국가·월별 기온 직접 입력과 연결되므로, 유럽 한파에 따른 난방수요 증가를 기온 하향 조정으로 반영합니다. 기간은 3개월이고 1월 Peak 패턴이므로 2027년 1~3월에 적용하되 1월에 가장 큰 하향, 이후 점진 완화로 배분하며, 재고는 정상 범위이므로 추가 증폭은 적용하지 않습니다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Month": 1, "Year": 2027}` | 3.5 | -1.5 | 2027년 1월 Belgium 기준 기온 3.5°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -1.5°C로 산정했습니다. |
| 2 | `{"Country": "Belgium", "Month": 2, "Year": 2027}` | 4.3 | 0.3 | 2027년 2월 Belgium 기준 기온 4.3°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 0.3°C로 산정했습니다. |
| 3 | `{"Country": "Belgium", "Month": 3, "Year": 2027}` | 6.7 | 3.7 | 2027년 3월 Belgium 기준 기온 6.7°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.7°C로 산정했습니다. |
| 4 | `{"Country": "France", "Month": 1, "Year": 2027}` | 5.1 | 0.1 | 2027년 1월 France 기준 기온 5.1°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 0.1°C로 산정했습니다. |
| 5 | `{"Country": "France", "Month": 2, "Year": 2027}` | 5.9 | 1.9 | 2027년 2월 France 기준 기온 5.9°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 1.9°C로 산정했습니다. |
| 6 | `{"Country": "France", "Month": 3, "Year": 2027}` | 8.5 | 5.5 | 2027년 3월 France 기준 기온 8.5°C에 3개월 한파의 말월 편차 -3°C를 적용해 5.5°C로 산정했습니다. |
| 7 | `{"Country": "Germany", "Month": 1, "Year": 2027}` | 1.2 | -3.8 | 2027년 1월 Germany 기준 기온 1.2°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -3.8°C로 산정했습니다. |
| 8 | `{"Country": "Germany", "Month": 2, "Year": 2027}` | 2.3 | -1.7 | 2027년 2월 Germany 기준 기온 2.3°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 -1.7°C로 산정했습니다. |
| 9 | `{"Country": "Germany", "Month": 3, "Year": 2027}` | 4.9 | 1.9 | 2027년 3월 Germany 기준 기온 4.9°C에 3개월 한파의 말월 편차 -3°C를 적용해 1.9°C로 산정했습니다. |
| 10 | `{"Country": "Italy", "Month": 1, "Year": 2027}` | 6.8 | 1.8 | 2027년 1월 Italy 기준 기온 6.8°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 1.8°C로 산정했습니다. |
| 11 | `{"Country": "Italy", "Month": 2, "Year": 2027}` | 7.7 | 3.7 | 2027년 2월 Italy 기준 기온 7.7°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 3.7°C로 산정했습니다. |
| 12 | `{"Country": "Italy", "Month": 3, "Year": 2027}` | 10.2 | 7.2 | 2027년 3월 Italy 기준 기온 10.2°C에 3개월 한파의 말월 편차 -3°C를 적용해 7.2°C로 산정했습니다. |
| 13 | `{"Country": "Netherlands", "Month": 1, "Year": 2027}` | 3.7 | -1.3 | 2027년 1월 Netherlands 기준 기온 3.7°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -1.3°C로 산정했습니다. |
| 14 | `{"Country": "Netherlands", "Month": 2, "Year": 2027}` | 4.4 | 0.4 | 2027년 2월 Netherlands 기준 기온 4.4°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 0.4°C로 산정했습니다. |
| 15 | `{"Country": "Netherlands", "Month": 3, "Year": 2027}` | 6.4 | 3.4 | 2027년 3월 Netherlands 기준 기온 6.4°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.4°C로 산정했습니다. |
| 16 | `{"Country": "Spain", "Month": 1, "Year": 2027}` | 7.9 | 2.9 | 2027년 1월 Spain 기준 기온 7.9°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 2.9°C로 산정했습니다. |
| 17 | `{"Country": "Spain", "Month": 2, "Year": 2027}` | 9 | 5 | 2027년 2월 Spain 기준 기온 9.0°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 5.0°C로 산정했습니다. |
| 18 | `{"Country": "Spain", "Month": 3, "Year": 2027}` | 11.3 | 8.3 | 2027년 3월 Spain 기준 기온 11.3°C에 3개월 한파의 말월 편차 -3°C를 적용해 8.3°C로 산정했습니다. |
| 19 | `{"Country": "United Kingdom", "Month": 1, "Year": 2027}` | 4.8 | -0.2 | 2027년 1월 United Kingdom 기준 기온 4.8°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -0.2°C로 산정했습니다. |
| 20 | `{"Country": "United Kingdom", "Month": 2, "Year": 2027}` | 5.2 | 1.2 | 2027년 2월 United Kingdom 기준 기온 5.2°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 1.2°C로 산정했습니다. |
| 21 | `{"Country": "United Kingdom", "Month": 3, "Year": 2027}` | 6.7 | 3.7 | 2027년 3월 United Kingdom 기준 기온 6.7°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.7°C로 산정했습니다. |

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
  "mi_event_id": 1378,
  "model_param_proposal_id": 99,
  "proposal_completed_dtm": "2026-07-07 23:38:05.691792",
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
      "rationale": "한파 강도 차원이 Temperature의 국가·월별 기온 직접 입력과 연결되므로, 유럽 한파에 따른 난방수요 증가를 기온 하향 조정으로 반영합니다. 기간은 3개월이고 1월 Peak 패턴이므로 2027년 1~3월에 적용하되 1월에 가장 큰 하향, 이후 점진 완화로 배분하며, 재고는 정상 범위이므로 추가 증폭은 적용하지 않습니다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 3.5,
          "proposedValue": -1.5,
          "rationale": "2027년 1월 Belgium 기준 기온 3.5°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -1.5°C로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 4.3,
          "proposedValue": 0.3,
          "rationale": "2027년 2월 Belgium 기준 기온 4.3°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 0.3°C로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 6.7,
          "proposedValue": 3.7,
          "rationale": "2027년 3월 Belgium 기준 기온 6.7°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.7°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 5.1,
          "proposedValue": 0.1,
          "rationale": "2027년 1월 France 기준 기온 5.1°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 0.1°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 5.9,
          "proposedValue": 1.9,
          "rationale": "2027년 2월 France 기준 기온 5.9°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 1.9°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 8.5,
          "proposedValue": 5.5,
          "rationale": "2027년 3월 France 기준 기온 8.5°C에 3개월 한파의 말월 편차 -3°C를 적용해 5.5°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 1.2,
          "proposedValue": -3.8,
          "rationale": "2027년 1월 Germany 기준 기온 1.2°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -3.8°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 2.3,
          "proposedValue": -1.7,
          "rationale": "2027년 2월 Germany 기준 기온 2.3°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 -1.7°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 4.9,
          "proposedValue": 1.9,
          "rationale": "2027년 3월 Germany 기준 기온 4.9°C에 3개월 한파의 말월 편차 -3°C를 적용해 1.9°C로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 6.8,
          "proposedValue": 1.8,
          "rationale": "2027년 1월 Italy 기준 기온 6.8°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 1.8°C로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 7.7,
          "proposedValue": 3.7,
          "rationale": "2027년 2월 Italy 기준 기온 7.7°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 3.7°C로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 10.2,
          "proposedValue": 7.2,
          "rationale": "2027년 3월 Italy 기준 기온 10.2°C에 3개월 한파의 말월 편차 -3°C를 적용해 7.2°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 3.7,
          "proposedValue": -1.3,
          "rationale": "2027년 1월 Netherlands 기준 기온 3.7°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -1.3°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 4.4,
          "proposedValue": 0.4,
          "rationale": "2027년 2월 Netherlands 기준 기온 4.4°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 0.4°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 6.4,
          "proposedValue": 3.4,
          "rationale": "2027년 3월 Netherlands 기준 기온 6.4°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.4°C로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 7.9,
          "proposedValue": 2.9,
          "rationale": "2027년 1월 Spain 기준 기온 7.9°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 2.9°C로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 9,
          "proposedValue": 5,
          "rationale": "2027년 2월 Spain 기준 기온 9.0°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 5.0°C로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 11.3,
          "proposedValue": 8.3,
          "rationale": "2027년 3월 Spain 기준 기온 11.3°C에 3개월 한파의 말월 편차 -3°C를 적용해 8.3°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": 4.8,
          "proposedValue": -0.2,
          "rationale": "2027년 1월 United Kingdom 기준 기온 4.8°C에 1월 Peak 중간 한파의 최대 편차 -5°C를 적용해 -0.2°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": 5.2,
          "proposedValue": 1.2,
          "rationale": "2027년 2월 United Kingdom 기준 기온 5.2°C에 Peak 이후 완화된 중간 한파 편차 -4°C를 적용해 1.2°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": 6.7,
          "proposedValue": 3.7,
          "rationale": "2027년 3월 United Kingdom 기준 기온 6.7°C에 3개월 한파의 말월 편차 -3°C를 적용해 3.7°C로 산정했습니다."
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
      "rationale": "타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 입력과 직접 연결되며, 50% 흡수 조건은 한파로 늘어나는 전력·난방 관련 부담 중 일부가 석탄·석유 등 비가스 에너지원으로 완화됨을 의미합니다. 다만 한파 이벤트는 TTF 상승 방향의 가스 수요 요인이므로, 3개월 충격을 연간 Gas 발전 비중에 보수적으로 반영해 기준 Gas share를 소폭 상향하는 구조로 제안합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1845,
          "rationale": "2027년 Belgium Gas 발전 비중 기준값 0.18에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.1845로 산정했습니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03485,
          "rationale": "2027년 France Gas 발전 비중 기준값 0.034에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.03485로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.13325,
          "rationale": "2027년 Germany Gas 발전 비중 기준값 0.13에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.13325로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.43255,
          "rationale": "2027년 Italy Gas 발전 비중 기준값 0.422에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.43255로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.3455,
          "rationale": "2027년 Netherlands Gas 발전 비중 기준값 0.33707317073170734에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.3455로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.216275,
          "rationale": "2027년 Spain Gas 발전 비중 기준값 0.211에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.216275로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.29725,
          "rationale": "2027년 United Kingdom Gas 발전 비중 기준값 0.29에 3개월 중간 한파와 50% 대체 흡수를 반영한 연간 보수 조정률 +2.5%를 적용해 0.29725로 산정했습니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 61,
  "scenario_id": 308,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.619 | 3.619 | 2314 | 124 | 2438 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:33.520 | 33.520 | 5819 | 3013 | 8832 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:28.032 | 88.032 | 8452 | 4668 | 13120 |

#### event_type_l2_id=7 여름 폭염

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "재생E·원전 등 흡수",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "재고는 수급모델 input 아님 — 해석 맥락",
      "dimension": "entry_gas_inventory (진입 시점 가스 재고 (평년 대비))",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "기온 직접 입력(대안 경로) : 폭염 영향 국가·월의 Temperature를 상향 조정하고, 냉방 수요 피크 월에 더 큰 조정폭을 적용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 +℃ → CDD(냉방도일) 변환 입력 : CDD는 미대상 파라미터이므로 직접 조정하지 않고, 폭염 강도는 Temperature 상향 또는 강도·월 분배 판단 근거로만 사용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "재고 회복 속도 = 재고 개념 — 수급모델 input 아님(맥락)",
      "dimension": "injection_pattern (Injection 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "월별 분배",
      "dimension": "peak_timing_pattern (Peak 시점, 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "하절기 월 슬롯(동남아·인도 4~5월 포함)",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [291, 292]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=291 [model_parameter_agent_test] 짧은 약한 폭염과 전원 흡수

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:44.862 (104.862s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["Temperature"]`
- target_selected_parameters: `["Temperature"]`
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

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 2 | 폭염 강도 dimension의 '+1~+2℃: 약'은 국가·월별 Temperature 직접 입력값을 상향 조정하는 근거이며, mapping_comment상 냉방 수요 피크 월에 조정폭을 반영하는 parameter입니다. 기간이 짧고 단발 피크이며 가격 영향도 중립으로 제시되어, 선택된 월·국가 범위에 한해 약한 폭염 구간의 하단에 가까운 보수적 상향값을 최종 기온 입력값으로 제안합니다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | [2.3, 5, 10.4] | 27.6 | 해당 좌표의 2026년 7월 기준값은 제공되지 않아, 동일 국가의 2026년 1~3월 Temperature 기록 2.3, 5.0, 10.4℃를 이용해 월별 증가 추세를 보수적 계절 기준으로 추정했다. 1~3월 평균 증가폭 4.05℃/월을 3월부터 7월까지 연장해 26.6℃를 기준으로 잡고, 약한 폭염 범위의 하단인 +1.0℃를 반영해 최종 입력값을 27.6℃로 산정했다. |
| 2 | `{"Country": "Japan", "Month": 7, "Year": 2026}` | [5.5, 6.1, 9.2] | 17.6 | 해당 좌표의 2026년 7월 기준값은 제공되지 않아, 동일 국가의 2026년 1~3월 Temperature 기록 5.5, 6.1, 9.2℃를 이용해 월별 증가 추세를 보수적 계절 기준으로 추정했다. 1~3월 평균 증가폭 1.85℃/월을 3월부터 7월까지 연장해 16.6℃를 기준으로 잡고, 약한 폭염 범위의 하단인 +1.0℃를 반영해 최종 입력값을 17.6℃로 산정했다. |

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
  "mi_event_id": 1144,
  "model_param_proposal_id": 100,
  "proposal_completed_dtm": "2026-07-07 23:38:14.064441",
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
      "rationale": "폭염 강도 dimension의 '+1~+2℃: 약'은 국가·월별 Temperature 직접 입력값을 상향 조정하는 근거이며, mapping_comment상 냉방 수요 피크 월에 조정폭을 반영하는 parameter입니다. 기간이 짧고 단발 피크이며 가격 영향도 중립으로 제시되어, 선택된 월·국가 범위에 한해 약한 폭염 구간의 하단에 가까운 보수적 상향값을 최종 기온 입력값으로 제안합니다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": [
            2.3,
            5,
            10.4
          ],
          "proposedValue": 27.6,
          "rationale": "해당 좌표의 2026년 7월 기준값은 제공되지 않아, 동일 국가의 2026년 1~3월 Temperature 기록 2.3, 5.0, 10.4℃를 이용해 월별 증가 추세를 보수적 계절 기준으로 추정했다. 1~3월 평균 증가폭 4.05℃/월을 3월부터 7월까지 연장해 26.6℃를 기준으로 잡고, 약한 폭염 범위의 하단인 +1.0℃를 반영해 최종 입력값을 27.6℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": [
            5.5,
            6.1,
            9.2
          ],
          "proposedValue": 17.6,
          "rationale": "해당 좌표의 2026년 7월 기준값은 제공되지 않아, 동일 국가의 2026년 1~3월 Temperature 기록 5.5, 6.1, 9.2℃를 이용해 월별 증가 추세를 보수적 계절 기준으로 추정했다. 1~3월 평균 증가폭 1.85℃/월을 3월부터 7월까지 연장해 16.6℃를 기준으로 잡고, 약한 폭염 범위의 하단인 +1.0℃를 반영해 최종 입력값을 17.6℃로 산정했다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension의 '100%'는 재생에너지·원전 등 비가스 전원이 냉방 수요 증가분을 흡수할 수 있음을 의미하며, PowerMix의 Gas 발전 비중 조정 여부와 직접 연결됩니다. 약한 단기 폭염과 충분한 전원 흡수, 중립적 가격 영향이 함께 제시되어 Gas 비중은 상향하지 않고 선택된 국가·에너지원의 기준 발전 믹스를 유지하는 구조로 제안합니다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0346,
          "rationale": "해당 좌표의 기준 Gas 발전 비중은 0.0346이며, 타 에너지원 흡수 가능성이 100%로 제시되어 폭염에 따른 추가 전력 수요가 Gas 비중 상승으로 전이되지 않는 것으로 해석했다. 따라서 발전원 비중 합계 제약을 흔들지 않도록 기준값을 그대로 최종 입력값으로 유지했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.323,
          "rationale": "해당 좌표의 기준 Gas 발전 비중은 0.323이며, 단기·약한 폭염과 타 에너지원 100% 흡수 조건으로 인해 Gas 발전 비중을 추가 상향할 근거가 제한적이다. 따라서 기존 발전 믹스의 Gas 비중을 유지해 최종 입력값을 0.323으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.942 | 3.942 | 2623 | 120 | 2743 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:12.017 | 12.017 | 6331 | 784 | 7115 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:14.587 | 74.587 | 8059 | 2805 | 10864 |

##### scenario_id=292 [model_parameter_agent_test] 3개월 강한 폭염과 전원 흡수 부족

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:58.668 (118.668s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["Temperature"]`
- target_selected_parameters: `["Temperature"]`
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
| Step3 value 결과 | value_cells=8, basecaseValue_present=8 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 6 | 폭염 강도 dimension의 '+3℃ 이상: 강'은 국가·연월별 Temperature를 직접 상향 조정하는 입력과 연결된다. 기간 3개월 및 지속 피크 맥락에 따라 2026년 7~9월 중국·일본 슬롯에 동일한 강도 하한을 적용하며, 선택 월의 기준값이 제공되지 않은 경우에는 동일 국가의 제공 기준값 형식과 범위를 참고해 보수적인 최종 기온 값을 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 10.4 | 13.4 | 선택된 중국 2026년 7월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 강한 폭염의 하한인 +3℃를 더해 최종 입력 기온을 13.4℃로 산정했다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 10.4 | 13.4 | 선택된 중국 2026년 8월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 지속 피크 조건이므로 7월과 같은 +3℃ 강폭염 하한을 반영해 최종 입력 기온을 13.4℃로 산정했다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 10.4 | 13.4 | 선택된 중국 2026년 9월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 3개월 지속 폭염 구간의 마지막 월에도 동일한 +3℃ 하한을 적용해 최종 입력 기온을 13.4℃로 산정했다. |
| 4 | `{"Country": "Japan", "Month": 7, "Year": 2026}` | 9.2 | 12.2 | 선택된 일본 2026년 7월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 강한 폭염의 하한인 +3℃를 더해 최종 입력 기온을 12.2℃로 산정했다. |
| 5 | `{"Country": "Japan", "Month": 8, "Year": 2026}` | 9.2 | 12.2 | 선택된 일본 2026년 8월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 지속 피크 조건이므로 7월과 같은 +3℃ 강폭염 하한을 반영해 최종 입력 기온을 12.2℃로 산정했다. |
| 6 | `{"Country": "Japan", "Month": 9, "Year": 2026}` | 9.2 | 12.2 | 선택된 일본 2026년 9월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 3개월 지속 폭염 구간의 마지막 월에도 동일한 +3℃ 하한을 적용해 최종 입력 기온을 12.2℃로 산정했다. |

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
  "mi_event_id": 1144,
  "model_param_proposal_id": 102,
  "proposal_completed_dtm": "2026-07-07 23:38:58.990186",
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
      "rationale": "폭염 강도 dimension의 '+3℃ 이상: 강'은 국가·연월별 Temperature를 직접 상향 조정하는 입력과 연결된다. 기간 3개월 및 지속 피크 맥락에 따라 2026년 7~9월 중국·일본 슬롯에 동일한 강도 하한을 적용하며, 선택 월의 기준값이 제공되지 않은 경우에는 동일 국가의 제공 기준값 형식과 범위를 참고해 보수적인 최종 기온 값을 제안한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 10.4,
          "proposedValue": 13.4,
          "rationale": "선택된 중국 2026년 7월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 강한 폭염의 하한인 +3℃를 더해 최종 입력 기온을 13.4℃로 산정했다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 10.4,
          "proposedValue": 13.4,
          "rationale": "선택된 중국 2026년 8월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 지속 피크 조건이므로 7월과 같은 +3℃ 강폭염 하한을 반영해 최종 입력 기온을 13.4℃로 산정했다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 10.4,
          "proposedValue": 13.4,
          "rationale": "선택된 중국 2026년 9월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 3개월 지속 폭염 구간의 마지막 월에도 동일한 +3℃ 하한을 적용해 최종 입력 기온을 13.4℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 9.2,
          "proposedValue": 12.2,
          "rationale": "선택된 일본 2026년 7월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 강한 폭염의 하한인 +3℃를 더해 최종 입력 기온을 12.2℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 9.2,
          "proposedValue": 12.2,
          "rationale": "선택된 일본 2026년 8월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 지속 피크 조건이므로 7월과 같은 +3℃ 강폭염 하한을 반영해 최종 입력 기온을 12.2℃로 산정했다."
        },
        {
          "Country": "Japan",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 9.2,
          "proposedValue": 12.2,
          "rationale": "선택된 일본 2026년 9월 기준값은 제공되지 않아, 동일 국가에서 제공된 가장 최근 기준월 값을 보수적 기준으로 사용했다. 3개월 지속 폭염 구간의 마지막 월에도 동일한 +3℃ 하한을 적용해 최종 입력 기온을 12.2℃로 산정했다."
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
      "rationale": "타 에너지원 흡수 가능성 25% dimension은 발전 수요 증가분 중 재생에너지·원전 등 비가스 전원이 흡수하지 못하는 몫이 가스 발전 비중으로 전이되는 경로와 연결된다. 3개월 지속되는 냉방·발전 수요 증가를 연간 PowerMix 입력에 반영하되, 연간 비중 변수인 점을 고려해 기간 효과를 제한적으로 반영하고 Gas 슬롯만 상향 조정한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0410875,
          "rationale": "중국 Gas 2026년 기준 비중 0.0346에 대해, 3개월 지속 효과를 연간 기준으로 3/12만 반영하고 타 에너지원 흡수 25%를 제외한 75%를 가스 전이분으로 보았다. 이에 따라 상대 상향 계수 1.1875를 적용해 최종 Gas 비중을 0.0410875로 산정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.3835625,
          "rationale": "일본 Gas 2026년 기준 비중 0.323에 대해, 3개월 지속 효과를 연간 기준으로 3/12만 반영하고 타 에너지원 흡수 25%를 제외한 75%를 가스 전이분으로 보았다. 이에 따라 상대 상향 계수 1.1875를 적용해 최종 Gas 비중을 0.3835625로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.566 | 3.566 | 2618 | 120 | 2738 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:13.841 | 13.841 | 6322 | 1024 | 7346 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:27.150 | 87.150 | 8198 | 4376 | 12574 |

#### event_type_l2_id=7 여름 폭염

##### Scenario Group

```json
{
  "description": "유럽 조기 폭염 이벤트에 대해 기간/강도/재고/injection/대체 흡수 조합을 확장해 생성한 테스트 scenario group",
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
  "mi_event_id": 1345,
  "request_usr_id": null,
  "scenario_count": 3,
  "scenario_group_id": 64,
  "stage": "scenario_created",
  "status": "created",
  "summary": "최근 한파/폭염 이벤트 기반 수급모델 파라미터 제안 확장 테스트",
  "title": "[model_parameter_agent_weather_ext_20260630] 폭염 이벤트 1345 수급모델 파라미터 테스트"
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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "재생E·원전 등 흡수",
      "dimension": "alt_energy_absorption (타 에너지원 흡수 가능성)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "재고는 수급모델 input 아님 — 해석 맥락",
      "dimension": "entry_gas_inventory (진입 시점 가스 재고 (평년 대비))",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "기온 직접 입력(대안 경로) : 폭염 영향 국가·월의 Temperature를 상향 조정하고, 냉방 수요 피크 월에 더 큰 조정폭을 적용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "direct",
      "parameter": "Temperature"
    },
    {
      "comment": "평년 대비 +℃ → CDD(냉방도일) 변환 입력 : CDD는 미대상 파라미터이므로 직접 조정하지 않고, 폭염 강도는 Temperature 상향 또는 강도·월 분배 판단 근거로만 사용",
      "dimension": "heatwave_intensity (폭염 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "재고 회복 속도 = 재고 개념 — 수급모델 input 아님(맥락)",
      "dimension": "injection_pattern (Injection 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "월별 분배",
      "dimension": "peak_timing_pattern (Peak 시점, 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "하절기 월 슬롯(동남아·인도 4~5월 포함)",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

```json
{
  "created_at": "2026-06-21T00:31:52.561657",
  "detail_analysis": "사건 요약:\n2026년 5월 유럽의 이례적 고온 전환과 초기 intense heatwave가 EU 가스소비 증가 배경으로 제시된 뒤, 2026년 5월 28일 WoodMac은 서유럽 조기 폭염을 단기 수급 변동 요인으로 재확인함. 2026년 6월 18일 WoodMac은 유럽 폭염을 카타르 LNG 정상화 시점, Tangguh 화재, Freeport 재가동과 함께 단기 수급을 좌우하는 변수로 제시함. 핵심 Event 경계는 유럽 조기 폭염에 따른 냉방 및 가스발전 수요 지지임.\n\n영향 경로:\n폭염은 냉방 전력수요를 높이고 전력 믹스에서 가스발전 필요성을 키우는 경로임. 이 경로는 유럽 천연가스 소비와 단기 LNG 수입 필요량을 지지하는 Fundamental 요인임. 다만 신규 Record들은 호르무즈, 카타르 LNG, Tangguh 화재, Freeport 재가동 등 별도 공급·물류 이슈도 함께 언급하고 있어 본 Event의 직접 영향은 유럽 폭염발 수요 측면으로 한정됨.\n\n시장 반응:\n폭염 자체는 프롬프트 가스수요와 TTF·유럽 LNG 도착 프리미엄을 지지하는 요인임. 2026년 5월 28일 WoodMac은 중동 긴장 완화 가능성 속 TTF 6월물 US$15.8/mmbtu와 동북아 DES 7월물 US$18.4/mmbtu 하락을 전하면서 서유럽 조기 폭염이 단기 수급 변동을 키우는 구도라고 제시함. 2026년 6월 18일 WoodMac은 미국과 이란의 호르무즈 해협 재개방 임시 합의로 TTF 7월물 US$13.7/mmbtu, 동북아 DES 8월물 US$15.4/mmbtu까지 하락했으나 유럽 폭염이 단기 수급을 좌우한다고 평가함. 2026년 6월 19일 Platts는 EU 저장률 45.56%와 7월 프롬프트 타이트에도 8월 이후 대서양 복귀 물량 기대가 NWE/TTF 할인 확대를 이끌었다고 전함.\n\nLNG 시장 관점:\n유럽 폭염은 LNG 설비 사건은 아니지만 유럽 가스 수요와 LNG 수입 경쟁에 영향을 주는 수요 Event임. 6월 중순 가격 하락은 주로 호르무즈 재개방 임시 합의와 8월 이후 대서양 복귀 물량 기대에 따른 시장 심리 완화와 연결됨. 따라서 본 Event는 유럽 폭염이 냉방·가스발전 수요를 통해 프롬프트 수급을 지지하되, 공급·물류 변수와 저장률 변화가 가격 방향을 상쇄할 수 있는 구조로 정리됨.",
  "event_title_ko": "유럽 조기 폭염 수요 지지",
  "event_type_l2_id": 7,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-19T00:00:00",
  "mi_event_id": "1345",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[유럽 가스수요] 5월 서유럽 조기 폭염 후 6월 폭염 지속 → 냉방·가스발전 수요 지지",
  "source_mi_record_ids": [
    2236,
    2462,
    3175,
    3315
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [317, 318]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=317 [model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 폭염

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:52.281 (112.281s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "alt_energy_absorption": "100%",
    "entry_gas_inventory": "+20%↑ (매우 여유)",
    "heatwave_intensity": "+1~+2℃: 약",
    "injection_pattern": "적극",
    "peak_timing_pattern": "6월 Peak",
    "period": "1개월 이하"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "neutral",
    "ttf": "up"
  },
  "narrative": "이벤트 1345 기반 확장 테스트 시나리오입니다. 기간=1개월 이하, 강도=+1~+2℃: 약, 대체흡수=100% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 34.0,
  "scenario_group_id": 64,
  "scenario_id": 317,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 단기 약한 폭염"
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

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 14 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=14, basecaseValue_present=14 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 7 | 폭염 강도 차원이 기온 직접 입력 파라미터와 연결되며, '+1~+2℃: 약'은 영향 국가·월의 Temperature를 제한적으로 상향하는 근거입니다. 기간은 1개월 이하이고 Peak가 6월로 제시되어 2026년 6월 서유럽 슬롯에만 보수적으로 반영하되, 국가별 기존 계절 상승 흐름을 기준으로 약한 폭염의 중간 강도 상향을 적용했습니다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Month": 6, "Year": 2026}` | [3.5, 4.3, 6.7] | 13.0 | 해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 3.5, 4.3, 6.7°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 11.5°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 13.0°C로 산정했습니다. |
| 2 | `{"Country": "France", "Month": 6, "Year": 2026}` | [5.1, 5.9, 8.5] | 15.1 | 해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 5.1, 5.9, 8.5°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 13.6°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 15.1°C로 산정했습니다. |
| 3 | `{"Country": "Germany", "Month": 6, "Year": 2026}` | [1.2, 2.3, 4.9] | 12.0 | 해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 1.2, 2.3, 4.9°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 10.45°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 12.0°C로 반올림했습니다. |
| 4 | `{"Country": "Italy", "Month": 6, "Year": 2026}` | [6.8, 7.7, 10.2] | 16.8 | 해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 6.8, 7.7, 10.2°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 15.3°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 16.8°C로 산정했습니다. |
| 5 | `{"Country": "Netherlands", "Month": 6, "Year": 2026}` | [3.7, 4.4, 6.4] | 12.0 | 해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 3.7, 4.4, 6.4°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 10.45°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 12.0°C로 반올림했습니다. |
| 6 | `{"Country": "Spain", "Month": 6, "Year": 2026}` | [7.9, 9, 11.3] | 17.9 | 해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 7.9, 9.0, 11.3°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 16.4°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 17.9°C로 산정했습니다. |
| 7 | `{"Country": "United Kingdom", "Month": 6, "Year": 2026}` | [4.8, 5.2, 6.7] | 11.1 | 해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 4.8, 5.2, 6.7°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 9.55°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 11.1°C로 반올림했습니다. |

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
  "mi_event_id": 1345,
  "model_param_proposal_id": 103,
  "proposal_completed_dtm": "2026-07-07 23:39:10.467026",
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
      "rationale": "폭염 강도 차원이 기온 직접 입력 파라미터와 연결되며, '+1~+2℃: 약'은 영향 국가·월의 Temperature를 제한적으로 상향하는 근거입니다. 기간은 1개월 이하이고 Peak가 6월로 제시되어 2026년 6월 서유럽 슬롯에만 보수적으로 반영하되, 국가별 기존 계절 상승 흐름을 기준으로 약한 폭염의 중간 강도 상향을 적용했습니다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            3.5,
            4.3,
            6.7
          ],
          "proposedValue": 13.0,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 3.5, 4.3, 6.7°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 11.5°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 13.0°C로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            5.1,
            5.9,
            8.5
          ],
          "proposedValue": 15.1,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 5.1, 5.9, 8.5°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 13.6°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 15.1°C로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            1.2,
            2.3,
            4.9
          ],
          "proposedValue": 12.0,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 1.2, 2.3, 4.9°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 10.45°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 12.0°C로 반올림했습니다."
        },
        {
          "Country": "Italy",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            6.8,
            7.7,
            10.2
          ],
          "proposedValue": 16.8,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 6.8, 7.7, 10.2°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 15.3°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 16.8°C로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            3.7,
            4.4,
            6.4
          ],
          "proposedValue": 12.0,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 3.7, 4.4, 6.4°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 10.45°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 12.0°C로 반올림했습니다."
        },
        {
          "Country": "Spain",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            7.9,
            9,
            11.3
          ],
          "proposedValue": 17.9,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 7.9, 9.0, 11.3°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 16.4°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 17.9°C로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 6,
          "Year": 2026,
          "basecaseValue": [
            4.8,
            5.2,
            6.7
          ],
          "proposedValue": 11.1,
          "rationale": "해당 2026년 6월 국가 슬롯의 직접 기준값은 제공되지 않아, 같은 국가의 2026년 1~3월 기준값 4.8, 5.2, 6.7°C를 사용했습니다. 1~3월 증가 추세로 6월 기준을 약 9.55°C로 보수 추정한 뒤, 약한 폭염 및 6월 Peak 조건의 중간값인 +1.5°C를 더해 11.1°C로 반올림했습니다."
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
      "rationale": "타 에너지원 흡수 가능성 차원이 발전 에너지원 비중 파라미터와 직접 연결되며, '100%'는 폭염에 따른 추가 전력수요를 재생에너지·원전 등 비가스 전원이 전부 흡수한다는 의미입니다. 따라서 선택된 가스 발전 비중 슬롯은 폭염으로 인한 상향 조정을 적용하지 않고, 연간 전원 믹스 합계 제약을 고려해 기존 가스 비중을 유지하는 구조로 제안했습니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.19가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.042,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.042가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.135,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.135가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.434,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.434가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.31818965517241377,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.31818965517241377이 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.213,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.213이 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29,
          "rationale": "해당 국가·연도·에너지원 슬롯에는 기준 가스 발전 비중 0.29가 존재합니다. 대체 에너지원 흡수율 100% 조건에서는 폭염으로 인한 추가 전력수요가 가스 비중을 높이지 않는 것으로 보아 기준값을 그대로 유지했습니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 64,
  "scenario_id": 317,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.684 | 3.684 | 2572 | 121 | 2693 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:16.185 | 16.185 | 6276 | 1415 | 7691 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:18.181 | 78.181 | 8385 | 3967 | 12352 |

##### scenario_id=318 [model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 폭염

- target_parameter: `Temperature`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:56.503 (116.503s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "alt_energy_absorption": "50%",
    "entry_gas_inventory": "±5% (정상)",
    "heatwave_intensity": "+2~+3℃: 중",
    "injection_pattern": "정상",
    "peak_timing_pattern": "7월 Peak",
    "period": "3개월"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "up",
    "ttf": "up"
  },
  "narrative": "이벤트 1345 기반 확장 테스트 시나리오입니다. 기간=3개월, 강도=+2~+3℃: 중, 대체흡수=50% 조건을 사용합니다.",
  "probability_delta": 0.0,
  "probability_score": 33.0,
  "scenario_group_id": 64,
  "scenario_id": 318,
  "status": "created",
  "title": "[model_parameter_agent_weather_ext_20260630] 유럽 3개월 중간 폭염"
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

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=207 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=14 | PASS |
| Step2 selected slot | 28 | PASS |
| Step3 basecase 샘플 | prompt_records=41, limit=100 | PASS |
| Step3 value 결과 | value_cells=28, basecaseValue_present=28 | PASS |
| Step2 slot axis value 수 | `{"7|altenergyabsorption|powermix|demand|powermixadjustment": {"Year": 6}, "7|heatwaveintensity|temperature|demand|weatheradjustment": {"Month": 3, "Year": 5}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | Temperature | `{"modelFile": "Demand", "modelSheet": "WeatherAdjustment", "tableName": "table2"}` | `["Year", "Month", "Country"]` | `["Temperature (°C)"]` | 21 | 폭염 강도 dimension의 '+2~+3℃: 중'은 국가·월별 Temperature를 직접 상향 조정하는 입력과 연결되며, mapping_comment에 따라 냉방 수요 피크 월에 더 큰 조정폭을 적용합니다. 기간 3개월과 7월 Peak 맥락을 반영해 2026년 7~9월 유럽 대상국에 7월 최대, 이후 완만히 낮아지는 절대 기온 값을 제안합니다. |

###### Proposed Parameter Values

###### Proposed Values - Temperature

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Belgium", "Month": 7, "Year": 2026}` | 6.7 | 9.7 | 2026년 7월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.7℃로 산정했습니다. |
| 2 | `{"Country": "Belgium", "Month": 8, "Year": 2026}` | 6.7 | 9.2 | 2026년 8월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 9.2℃로 산정했습니다. |
| 3 | `{"Country": "Belgium", "Month": 9, "Year": 2026}` | 6.7 | 8.7 | 2026년 9월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.7℃로 산정했습니다. |
| 4 | `{"Country": "France", "Month": 7, "Year": 2026}` | 8.5 | 11.5 | 2026년 7월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 11.5℃로 산정했습니다. |
| 5 | `{"Country": "France", "Month": 8, "Year": 2026}` | 8.5 | 11 | 2026년 8월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 11.0℃로 산정했습니다. |
| 6 | `{"Country": "France", "Month": 9, "Year": 2026}` | 8.5 | 10.5 | 2026년 9월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 10.5℃로 산정했습니다. |
| 7 | `{"Country": "Germany", "Month": 7, "Year": 2026}` | 4.9 | 7.9 | 2026년 7월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 7.9℃로 산정했습니다. |
| 8 | `{"Country": "Germany", "Month": 8, "Year": 2026}` | 4.9 | 7.4 | 2026년 8월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 7.4℃로 산정했습니다. |
| 9 | `{"Country": "Germany", "Month": 9, "Year": 2026}` | 4.9 | 6.9 | 2026년 9월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 6.9℃로 산정했습니다. |
| 10 | `{"Country": "Italy", "Month": 7, "Year": 2026}` | 10.2 | 13.2 | 2026년 7월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 13.2℃로 산정했습니다. |
| 11 | `{"Country": "Italy", "Month": 8, "Year": 2026}` | 10.2 | 12.7 | 2026년 8월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 12.7℃로 산정했습니다. |
| 12 | `{"Country": "Italy", "Month": 9, "Year": 2026}` | 10.2 | 12.2 | 2026년 9월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 12.2℃로 산정했습니다. |
| 13 | `{"Country": "Netherlands", "Month": 7, "Year": 2026}` | 6.4 | 9.4 | 2026년 7월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.4℃로 산정했습니다. |
| 14 | `{"Country": "Netherlands", "Month": 8, "Year": 2026}` | 6.4 | 8.9 | 2026년 8월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 8.9℃로 산정했습니다. |
| 15 | `{"Country": "Netherlands", "Month": 9, "Year": 2026}` | 6.4 | 8.4 | 2026년 9월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.4℃로 산정했습니다. |
| 16 | `{"Country": "Spain", "Month": 7, "Year": 2026}` | 11.3 | 14.3 | 2026년 7월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 14.3℃로 산정했습니다. |
| 17 | `{"Country": "Spain", "Month": 8, "Year": 2026}` | 11.3 | 13.8 | 2026년 8월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 13.8℃로 산정했습니다. |
| 18 | `{"Country": "Spain", "Month": 9, "Year": 2026}` | 11.3 | 13.3 | 2026년 9월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 13.3℃로 산정했습니다. |
| 19 | `{"Country": "United Kingdom", "Month": 7, "Year": 2026}` | 6.7 | 9.7 | 2026년 7월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.7℃로 산정했습니다. |
| 20 | `{"Country": "United Kingdom", "Month": 8, "Year": 2026}` | 6.7 | 9.2 | 2026년 8월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 9.2℃로 산정했습니다. |
| 21 | `{"Country": "United Kingdom", "Month": 9, "Year": 2026}` | 6.7 | 8.7 | 2026년 9월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.7℃로 산정했습니다. |

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
  "mi_event_id": 1345,
  "model_param_proposal_id": 105,
  "proposal_completed_dtm": "2026-07-07 23:40:02.150900",
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
      "rationale": "폭염 강도 dimension의 '+2~+3℃: 중'은 국가·월별 Temperature를 직접 상향 조정하는 입력과 연결되며, mapping_comment에 따라 냉방 수요 피크 월에 더 큰 조정폭을 적용합니다. 기간 3개월과 7월 Peak 맥락을 반영해 2026년 7~9월 유럽 대상국에 7월 최대, 이후 완만히 낮아지는 절대 기온 값을 제안합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.7,
          "rationale": "2026년 7월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.7℃로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.2,
          "rationale": "2026년 8월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 9.2℃로 산정했습니다."
        },
        {
          "Country": "Belgium",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 8.7,
          "rationale": "2026년 9월 Belgium selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.7℃로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 8.5,
          "proposedValue": 11.5,
          "rationale": "2026년 7월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 11.5℃로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 8.5,
          "proposedValue": 11,
          "rationale": "2026년 8월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 11.0℃로 산정했습니다."
        },
        {
          "Country": "France",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 8.5,
          "proposedValue": 10.5,
          "rationale": "2026년 9월 France selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 8.5℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 10.5℃로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 4.9,
          "proposedValue": 7.9,
          "rationale": "2026년 7월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 7.9℃로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 4.9,
          "proposedValue": 7.4,
          "rationale": "2026년 8월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 7.4℃로 산정했습니다."
        },
        {
          "Country": "Germany",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 4.9,
          "proposedValue": 6.9,
          "rationale": "2026년 9월 Germany selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 4.9℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 6.9℃로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 10.2,
          "proposedValue": 13.2,
          "rationale": "2026년 7월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 13.2℃로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 10.2,
          "proposedValue": 12.7,
          "rationale": "2026년 8월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 12.7℃로 산정했습니다."
        },
        {
          "Country": "Italy",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 10.2,
          "proposedValue": 12.2,
          "rationale": "2026년 9월 Italy selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 10.2℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 12.2℃로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 6.4,
          "proposedValue": 9.4,
          "rationale": "2026년 7월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.4℃로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 6.4,
          "proposedValue": 8.9,
          "rationale": "2026년 8월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 8.9℃로 산정했습니다."
        },
        {
          "Country": "Netherlands",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 6.4,
          "proposedValue": 8.4,
          "rationale": "2026년 9월 Netherlands selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.4℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.4℃로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 11.3,
          "proposedValue": 14.3,
          "rationale": "2026년 7월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 14.3℃로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 11.3,
          "proposedValue": 13.8,
          "rationale": "2026년 8월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 13.8℃로 산정했습니다."
        },
        {
          "Country": "Spain",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 11.3,
          "proposedValue": 13.3,
          "rationale": "2026년 9월 Spain selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 11.3℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 13.3℃로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.7,
          "rationale": "2026년 7월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 Peak와 중간 폭염 강도 상단을 반영해 +3.0℃를 더한 최종 기온 9.7℃로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 9.2,
          "rationale": "2026년 8월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 7월 이후에도 폭염이 지속되지만 피크는 지난 것으로 보아 +2.5℃를 더한 최종 기온 9.2℃로 산정했습니다."
        },
        {
          "Country": "United Kingdom",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 6.7,
          "proposedValue": 8.7,
          "rationale": "2026년 9월 United Kingdom selected 월 기준값이 없어 동일 국가의 최신 가용 2026년 3월 값 6.7℃를 보수 기준으로 사용했습니다. 3개월 영향의 후반부로 강도를 낮춰 +2.0℃를 더한 최종 기온 8.7℃로 산정했습니다."
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
      "rationale": "타 에너지원 흡수 가능성 dimension의 '50%'는 재생에너지·원전 등 비가스 전원이 냉방 전력수요 증가분의 일부를 흡수하고 나머지가 가스발전 비중을 지지한다는 PowerMix 입력과 연결됩니다. 3개월 중간 폭염이 연간 발전믹스에 미치는 영향은 제한적으로 보되, 흡수되지 않는 절반의 수요가 가스 비중을 소폭 상향시키는 구조로 제안합니다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.19475,
          "rationale": "Belgium Gas 2026년 기준 발전믹스 0.19에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.19 × 1.025 = 0.19475입니다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04305,
          "rationale": "France Gas 2026년 기준 발전믹스 0.042에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.042 × 1.025 = 0.04305입니다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.138375,
          "rationale": "Germany Gas 2026년 기준 발전믹스 0.135에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.135 × 1.025 = 0.138375입니다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.44485,
          "rationale": "Italy Gas 2026년 기준 발전믹스 0.434에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.434 × 1.025 = 0.44485입니다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3261443965517241,
          "rationale": "Netherlands Gas 2026년 기준 발전믹스 0.31818965517241377에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.31818965517241377 × 1.025 = 0.3261443965517241입니다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.218325,
          "rationale": "Spain Gas 2026년 기준 발전믹스 0.213에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.213 × 1.025 = 0.218325입니다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.29725,
          "rationale": "United Kingdom Gas 2026년 기준 발전믹스 0.29에 대해, 3개월 폭염의 연간 반영 효과와 50% 대체 흡수를 감안해 가스 비중을 2.5% 상대 상향했습니다. 최종 입력값은 0.29 × 1.025 = 0.29725입니다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 64,
  "scenario_id": 318,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.251 | 3.251 | 2573 | 114 | 2687 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:20.614 | 20.614 | 6265 | 2261 | 8526 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:10.695 | 70.695 | 8898 | 5845 | 14743 |

### Parameter: LiqUtilAdjustment

#### event_type_l2_id=1 Upstream Utilization 변동

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "LNG 전환 대체 시 타 공급국 액화 가동률 상향 : LNG 전환 대체 공급 경로가 설명 가능한 인접·시장연결 공급국의 가용 액화설비에 차등 배분",
      "dimension": "alt_gas_supply_availability (대체 가스 공급 가능성)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "타 가스전 증산(음의 disruption)으로 부족분 상쇄 : 차질 지역과 연결 가능한 동일 권역·시장 내 가스전의 증산 가능량을 음(-)의 SupplyDisruption으로 배분",
      "dimension": "alt_gas_supply_availability (대체 가스 공급 가능성)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "급격/점진 — 값의 시계열 형태",
      "dimension": "onset_pattern (발생 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "Parameter 변경 시간축 결정",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "원상복귀 시간축",
      "dimension": "recovery_pattern (회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "Province/Basin 생산 차질량(Bcm 또는 %); 증산은 음(-)",
      "dimension": "utilization_change_amount (Utilization 변화 폭)",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [283, 284]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=283 [model_parameter_agent_test] 단기 미세 감산과 대체 공급 충분

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 04:07.088 (247.088s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 53 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=2, basecaseValue_present=2 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 2 | 대체 가스 공급 가능성 100%는 노르웨이 upstream 소폭 감산을 시장연결 LNG 공급국의 액화 가동률 상향으로 흡수할 수 있다는 의미이므로 LiqUtilAdjustment와 직접 연결된다. 기간은 1개월 이하이고 발생은 점진, 회복은 급격으로 제시되어 2026년 7월 한 달에 한정한 미세 상향만 적용하며, 시장 영향이 중립인 점을 반영해 유럽 인접성과 기준 가동률 여유가 큰 설비에 보수적으로 배분한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.9, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.20018404907975457 | 유럽향 대체 공급 경로와 기준 가동률 여유를 고려해 해당 2026년 7월 슬롯을 우선 적용 대상으로 선택했다. 기준값 0.19018404907975456에 단기·미세 대체 공급분을 반영해 1.0%p만 상향한 최종 가동률 0.20018404907975456으로 산정했다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 8.4, "Period": 112, "Year": 2026}` | 0.19018404907975456 | 0.20018404907975457 | 동일한 유럽 인접 대체 공급권역 내에서 기준 가동률 여유가 큰 2026년 7월 슬롯을 추가 적용 대상으로 선택했다. 기준값 0.19018404907975456에 단기·미세 대체 공급분을 반영해 1.0%p만 상향한 최종 가동률 0.20018404907975456으로 산정했다. |

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
  "mi_event_id": 1117,
  "model_param_proposal_id": 89,
  "proposal_completed_dtm": "2026-07-07 23:32:15.781406",
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
      "rationale": "대체 가스 공급 가능성 100%는 노르웨이 upstream 소폭 감산을 시장연결 LNG 공급국의 액화 가동률 상향으로 흡수할 수 있다는 의미이므로 LiqUtilAdjustment와 직접 연결된다. 기간은 1개월 이하이고 발생은 점진, 회복은 급격으로 제시되어 2026년 7월 한 달에 한정한 미세 상향만 적용하며, 시장 영향이 중립인 점을 반영해 유럽 인접성과 기준 가동률 여유가 큰 설비에 보수적으로 배분한다.",
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
          "proposedValue": 0.20018404907975457,
          "rationale": "유럽향 대체 공급 경로와 기준 가동률 여유를 고려해 해당 2026년 7월 슬롯을 우선 적용 대상으로 선택했다. 기준값 0.19018404907975456에 단기·미세 대체 공급분을 반영해 1.0%p만 상향한 최종 가동률 0.20018404907975456으로 산정했다."
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
          "proposedValue": 0.20018404907975457,
          "rationale": "동일한 유럽 인접 대체 공급권역 내에서 기준 가동률 여유가 큰 2026년 7월 슬롯을 추가 적용 대상으로 선택했다. 기준값 0.19018404907975456에 단기·미세 대체 공급분을 반영해 1.0%p만 상향한 최종 가동률 0.20018404907975456으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.733 | 4.733 | 2232 | 80 | 2312 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 02:32.539 | 152.539 | 11472 | 9708 | 21180 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:45.502 | 45.502 | 18693 | 2629 | 21322 |

##### scenario_id=284 [model_parameter_agent_test] 6개월 큰 감산과 대체 공급 제한

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 05:08.001 (308.001s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 90 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=90, basecaseValue_present=90 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 90 | 대체 가스 공급 가능성 25%는 노르웨이 upstream 차질을 LNG로 일부 전환할 때 인접·시장연결 공급국의 액화설비 가동률을 조정하는 LiqUtilAdjustment와 직접 연결된다. 6개월 기간, 급격한 발생, 점진적 회복은 적용 시간축을 2026년 7~12월로 잡는 보조 맥락으로 반영했으며, 제한적인 대체 가능성을 고려해 잔여 가동 여력 중 일부만 상향하고 이미 상한에 근접한 설비는 1.0을 넘지 않도록 제안했다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.9, "Period": 115, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 7월 선택 슬롯의 기준 가동률 0.19018404907975456에 대체 공급 가능성 25%를 잔여 여력에 적용해 0.19018404907975456 + 0.25 × (1 - 0.19018404907975456) = 0.3926380368098159로 산정했다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.9, "Period": 116, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 8월은 6개월 영향 구간 내 선택 슬롯이므로 기준 가동률 0.19018404907975456의 잔여 여력 중 25%를 반영해 0.3926380368098159로 산정했다. |
| 3 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.9, "Period": 117, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 9월 기준 가동률 0.19018404907975456에 제한적 대체 공급 강도 25%를 잔여 여력 기준으로 적용해 0.3926380368098159로 산정했다. |
| 4 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 7.9, "Period": 118, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 10월 선택 슬롯은 영향 기간 중간 구간이므로 기준 가동률 0.19018404907975456에서 잔여 여력의 25%만 상향해 0.3926380368098159로 산정했다. |
| 5 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 7.9, "Period": 119, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 11월 기준 가동률 0.19018404907975456에 25% 대체 가능성을 잔여 여력 보정으로 반영해 최종 가동률 0.3926380368098159를 적용했다. |
| 6 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 7.9, "Period": 120, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 12월은 6개월 영향 구간의 마지막 선택 슬롯으로, 기준 가동률 0.19018404907975456에 잔여 여력의 25%를 더해 0.3926380368098159로 산정했다. |
| 7 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 8.4, "Period": 115, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 7월 기준 가동률 0.19018404907975456에 제한적 대체 공급 25%를 잔여 여력에 적용해 0.3926380368098159로 산정했다. |
| 8 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 8.4, "Period": 116, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 8월 기준 가동률 0.19018404907975456의 잔여 여력 중 25%를 활용하는 보수적 상향으로 0.3926380368098159를 적용했다. |
| 9 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 8.4, "Period": 117, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 9월 선택 슬롯은 영향 기간에 포함되므로 기준 가동률 0.19018404907975456에서 잔여 여력의 25%만 상향해 0.3926380368098159로 산정했다. |
| 10 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 8.4, "Period": 118, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 10월 기준 가동률 0.19018404907975456에 대체 가능성 25%를 잔여 여력 기준으로 반영해 0.3926380368098159로 산정했다. |
| 11 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 8.4, "Period": 119, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 11월 기준 가동률 0.19018404907975456에 잔여 가동 여력의 25%를 더해 0.3926380368098159로 제안했다. |
| 12 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 8.4, "Period": 120, "Year": 2026}` | 0.19018404907975456 | 0.3926380368098159 | 2026년 12월 기준 가동률 0.19018404907975456에서 25% 대체 가능성을 잔여 여력에만 적용해 0.3926380368098159로 산정했다. |
| 13 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 115, "Year": 2026}` | 1.0000000000000002 | 1 | 2026년 7월 기준 가동률이 1.0000000000000002로 이미 상한 수준이므로 추가 대체 공급 여력은 없다고 보고 입력 상한 1.0을 적용했다. |
| 14 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 116, "Year": 2026}` | 1.0000000000000002 | 1 | 2026년 8월 기준 가동률이 상한 수준이어서 잔여 여력 보정 후에도 1.0을 초과하지 않도록 1.0으로 제한했다. |
| 15 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 117, "Year": 2026}` | 1.0000000000000002 | 1 | 2026년 9월 기준 가동률이 1.0000000000000002로 이미 최대 수준이므로 대체 공급 상향은 상한에 의해 1.0으로 적용했다. |
| 16 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.7, "Period": 118, "Year": 2026}` | 1.0000000000000002 | 1 | 2026년 10월 기준 가동률이 이미 상한 수준이므로 추가 상승 여력을 인정하지 않고 최종 입력값을 1.0으로 제한했다. |
| 17 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.7, "Period": 119, "Year": 2026}` | 1.0000000000000002 | 1 | 2026년 11월 기준 가동률이 최대치에 있어 대체 공급 가능성 25%를 반영해도 최종 값은 입력 상한 1.0으로 유지했다. |
| 18 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.7, "Period": 120, "Year": 2026}` | 1.0000000000000002 | 1 | 2026년 12월 기준 가동률이 상한 수준이므로 6개월 영향 구간 내에서도 추가 상향 없이 1.0을 적용했다. |
| 19 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 115, "Year": 2026}` | 0.7999999999999999 | 0.85 | 2026년 7월 기준 가동률 0.7999999999999999에 잔여 여력 0.2000000000000001의 25%를 더해 0.85로 산정했다. |
| 20 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 116, "Year": 2026}` | 0.7999999999999999 | 0.85 | 2026년 8월 기준 가동률 0.7999999999999999의 잔여 여력 중 25%를 활용해 최종 가동률 0.85를 적용했다. |
| 21 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 117, "Year": 2026}` | 0.7999999999999999 | 0.85 | 2026년 9월 선택 슬롯에 기준 가동률 0.7999999999999999와 대체 가능성 25%를 반영해 0.85로 산정했다. |
| 22 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.5, "Period": 118, "Year": 2026}` | 0.7999999999999999 | 0.85 | 2026년 10월 기준 가동률 0.7999999999999999에서 잔여 가동 여력의 25%를 더해 0.85를 적용했다. |
| 23 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.5, "Period": 119, "Year": 2026}` | 0.7999999999999999 | 0.85 | 2026년 11월 기준 가동률 0.7999999999999999에 제한적 대체 공급분을 잔여 여력 기준으로 반영해 0.85로 산정했다. |
| 24 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.5, "Period": 120, "Year": 2026}` | 0.7999999999999999 | 0.85 | 2026년 12월 기준 가동률 0.7999999999999999의 잔여 여력 25%만 상향해 최종 입력값 0.85를 적용했다. |
| 25 | `{"Country": "Egypt", "LNG Plant": "Damietta LNG", "LNG Plant Train": "Damietta LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3, "Period": 115, "Year": 2026}` | 0 | 0.25 | 2026년 7월 기준 가동률은 0이나 선택된 운영 설비이므로 대체 공급 가능성 25%를 보수적 재가동 수준으로 해석해 최종 가동률 0.25를 적용했다. |
| 26 | `{"Country": "Egypt", "LNG Plant": "Damietta LNG", "LNG Plant Train": "Damietta LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3, "Period": 116, "Year": 2026}` | 0 | 0.25 | 2026년 8월 기준 가동률 0에서 제한적 대체 가능성 25%를 직접 반영해 보수적 가동률 0.25로 산정했다. |
| 27 | `{"Country": "Egypt", "LNG Plant": "Damietta LNG", "LNG Plant Train": "Damietta LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3, "Period": 117, "Year": 2026}` | 0 | 0.25 | 2026년 9월 선택 슬롯은 6개월 영향 구간에 포함되며, 기준 가동률 0의 운영 설비에 대체 가능성 25%를 적용해 0.25로 산정했다. |
| 28 | `{"Country": "Egypt", "LNG Plant": "Damietta LNG", "LNG Plant Train": "Damietta LNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 3, "Period": 118, "Year": 2026}` | 0 | 0.25 | 2026년 10월 기준 가동률 0에서 선택된 대체 공급 가능성 25%만큼의 제한적 운전을 가정해 0.25를 적용했다. |
| 29 | `{"Country": "Egypt", "LNG Plant": "Damietta LNG", "LNG Plant Train": "Damietta LNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 3, "Period": 119, "Year": 2026}` | 0 | 0.25 | 2026년 11월 기준 가동률 0에 대해 대체 공급 가능성이 25%로 제한된 점을 반영해 최종 가동률 0.25로 산정했다. |
| 30 | `{"Country": "Egypt", "LNG Plant": "Damietta LNG", "LNG Plant Train": "Damietta LNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 3, "Period": 120, "Year": 2026}` | 0 | 0.25 | 2026년 12월 기준 가동률 0인 운영 설비에 6개월 영향 구간의 제한적 대체 공급 가능성 25%를 반영해 0.25로 산정했다. |
| 31 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.6, "Period": 115, "Year": 2026}` | 0 | 0.25 | 2026년 7월 기준 가동률 0에서 대체 공급 가능성 25%를 보수적 운전 수준으로 적용해 0.25로 산정했다. |
| 32 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.6, "Period": 116, "Year": 2026}` | 0 | 0.25 | 2026년 8월 선택 슬롯은 기준 가동률 0이나 운영 상태 설비이므로 제한적 대체 공급 25%를 반영해 0.25를 적용했다. |
| 33 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.6, "Period": 117, "Year": 2026}` | 0 | 0.25 | 2026년 9월 기준 가동률 0에 대해 대체 공급 가능성이 25%로 제한된 점을 최종 가동률 0.25로 반영했다. |
| 34 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 3.6, "Period": 118, "Year": 2026}` | 0 | 0.25 | 2026년 10월 기준 가동률 0인 선택 슬롯에 제한적 대체 가능성 25%를 적용해 보수적 최종 입력값 0.25를 산정했다. |
| 35 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 3.6, "Period": 119, "Year": 2026}` | 0 | 0.25 | 2026년 11월 선택 슬롯의 기준 가동률 0에서 25% 대체 공급 가능성을 반영해 최종 가동률 0.25로 산정했다. |
| 36 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 3.6, "Period": 120, "Year": 2026}` | 0 | 0.25 | 2026년 12월 기준 가동률 0에 대해 6개월 영향 구간 내 제한적 운전 가능성을 25%로 반영해 0.25를 적용했다. |
| 37 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.6, "Period": 115, "Year": 2026}` | 0 | 0.25 | 2026년 7월 기준 가동률 0인 선택 슬롯에 대체 공급 가능성 25%를 보수적으로 적용해 최종 가동률 0.25로 산정했다. |
| 38 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.6, "Period": 116, "Year": 2026}` | 0 | 0.25 | 2026년 8월 기준 가동률 0에서 선택된 대체 공급 가능성 25%만큼의 제한적 가동을 반영해 0.25를 적용했다. |
| 39 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.6, "Period": 117, "Year": 2026}` | 0 | 0.25 | 2026년 9월 기준 가동률 0에 6개월 영향 구간의 대체 가능성 25%를 반영해 최종 입력값 0.25를 산정했다. |
| 40 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T2", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 3.6, "Period": 118, "Year": 2026}` | 0 | 0.25 | 2026년 10월 선택 슬롯은 기준 가동률 0이나 운영 설비로 분류되어 있어 제한적 대체 공급 25%를 최종 가동률 0.25로 반영했다. |
| 41 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T2", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 3.6, "Period": 119, "Year": 2026}` | 0 | 0.25 | 2026년 11월 기준 가동률 0에서 대체 공급 가능성 25%를 적용해 보수적 최종 가동률 0.25로 산정했다. |
| 42 | `{"Country": "Egypt", "LNG Plant": "Egyptian LNG (Idku)", "LNG Plant Train": "Egyptian LNG (Idku) T2", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 3.6, "Period": 120, "Year": 2026}` | 0 | 0.25 | 2026년 12월 기준 가동률 0인 선택 슬롯에 25% 대체 가능성을 반영해 0.25를 최종 입력값으로 적용했다. |
| 43 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 115, "Year": 2026}` | 0.7420234122042342 | 0.8065175591531756 | 2026년 7월 기준 가동률 0.7420234122042342에 잔여 여력의 25%를 더해 0.8065175591531756으로 산정했다. |
| 44 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 116, "Year": 2026}` | 0.7359392278953923 | 0.8019544209215442 | 2026년 8월 기준 가동률 0.7359392278953923에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.8019544209215442로 산정했다. |
| 45 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 117, "Year": 2026}` | 0.7718854296388543 | 0.8289140722291407 | 2026년 9월 기준 가동률 0.7718854296388543의 잔여 여력 중 25%를 상향 반영해 0.8289140722291407로 산정했다. |
| 46 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 3.3, "Period": 118, "Year": 2026}` | 0.7344876712328768 | 0.8008657534246576 | 2026년 10월 기준 가동률 0.7344876712328768에 잔여 여력 25% 활용을 반영해 0.8008657534246576으로 산정했다. |
| 47 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 3.3, "Period": 119, "Year": 2026}` | 0.7270535491905354 | 0.7952901618929016 | 2026년 11월 기준 가동률 0.7270535491905354에서 대체 가능성 25%를 잔여 여력에 적용해 0.7952901618929016으로 산정했다. |
| 48 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 3.3, "Period": 120, "Year": 2026}` | 0.7808448318804485 | 0.8356336239103364 | 2026년 12월 기준 가동률 0.7808448318804485의 잔여 여력 중 25%를 반영해 0.8356336239103364로 산정했다. |
| 49 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 115, "Year": 2026}` | 0.7420234122042342 | 0.8065175591531756 | 2026년 7월 기준 가동률 0.7420234122042342에 잔여 여력의 25%를 더해 최종 가동률 0.8065175591531756으로 산정했다. |
| 50 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 116, "Year": 2026}` | 0.7359392278953923 | 0.8019544209215442 | 2026년 8월 기준 가동률 0.7359392278953923에서 잔여 여력의 25%를 반영해 0.8019544209215442로 산정했다. |
| 51 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 117, "Year": 2026}` | 0.7718854296388543 | 0.8289140722291407 | 2026년 9월 기준 가동률 0.7718854296388543에 대체 가능성 25%를 잔여 여력 기준으로 적용해 0.8289140722291407로 산정했다. |
| 52 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T2", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 3.3, "Period": 118, "Year": 2026}` | 0.7344876712328768 | 0.8008657534246576 | 2026년 10월 기준 가동률 0.7344876712328768의 잔여 여력 중 25%를 상향해 0.8008657534246576으로 산정했다. |
| 53 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T2", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 3.3, "Period": 119, "Year": 2026}` | 0.7270535491905354 | 0.7952901618929016 | 2026년 11월 기준 가동률 0.7270535491905354에서 제한적 대체 공급 25%를 잔여 여력에 반영해 0.7952901618929016으로 산정했다. |
| 54 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T2", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 3.3, "Period": 120, "Year": 2026}` | 0.7808448318804485 | 0.8356336239103364 | 2026년 12월 기준 가동률 0.7808448318804485에 잔여 여력의 25%를 더해 0.8356336239103364로 산정했다. |
| 55 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 115, "Year": 2026}` | 0.7282220743697789 | 0.7961665557773342 | 2026년 7월 기준 가동률 0.7282220743697789에 잔여 여력의 25%를 반영해 0.7961665557773342로 산정했다. |
| 56 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 116, "Year": 2026}` | 0.7222510534486581 | 0.7916882900864936 | 2026년 8월 기준 가동률 0.7222510534486581의 잔여 여력 중 25%를 상향해 0.7916882900864936으로 산정했다. |
| 57 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 117, "Year": 2026}` | 0.7827796259333183 | 0.8370847194499887 | 2026년 9월 기준 가동률 0.7827796259333183에서 대체 가능성 25%를 잔여 여력에 적용해 0.8370847194499887로 산정했다. |
| 58 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T3", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 3.3, "Period": 118, "Year": 2026}` | 0.7208264951578326 | 0.7906198713683744 | 2026년 10월 기준 가동률 0.7208264951578326에 잔여 여력의 25%를 더해 0.7906198713683744로 산정했다. |
| 59 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T3", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 3.3, "Period": 119, "Year": 2026}` | 0.7373149996303687 | 0.8029862497227765 | 2026년 11월 기준 가동률 0.7373149996303687에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.8029862497227765로 산정했다. |
| 60 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T3", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 3.3, "Period": 120, "Year": 2026}` | 0.7663214312116507 | 0.824741073408738 | 2026년 12월 기준 가동률 0.7663214312116507에 잔여 여력의 25%를 반영해 0.824741073408738로 산정했다. |
| 61 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.1, "Period": 115, "Year": 2026}` | 0.7193333333333335 | 0.7895 | 2026년 7월 기준 가동률 0.7193333333333335에 잔여 여력의 25%를 더해 0.7895로 산정했다. |
| 62 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.1, "Period": 116, "Year": 2026}` | 0.713456790123457 | 0.7850925925925927 | 2026년 8월 기준 가동률 0.713456790123457에서 잔여 여력의 25%를 반영해 0.7850925925925927로 산정했다. |
| 63 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.1, "Period": 117, "Year": 2026}` | 0.7732345679012347 | 0.829925925925926 | 2026년 9월 기준 가동률 0.7732345679012347에 잔여 여력의 25%를 상향 반영해 0.829925925925926으로 산정했다. |
| 64 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T4", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.1, "Period": 118, "Year": 2026}` | 0.7120493827160495 | 0.7840370370370371 | 2026년 10월 기준 가동률 0.7120493827160495에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.7840370370370371로 산정했다. |
| 65 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T4", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.1, "Period": 119, "Year": 2026}` | 0.7283209876543211 | 0.7962407407407409 | 2026년 11월 기준 가동률 0.7283209876543211에 잔여 여력의 25%를 더해 0.7962407407407409로 산정했다. |
| 66 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T4", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.1, "Period": 120, "Year": 2026}` | 0.7569876543209877 | 0.8177407407407408 | 2026년 12월 기준 가동률 0.7569876543209877의 잔여 여력 중 25%를 반영해 0.8177407407407408로 산정했다. |
| 67 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.1, "Period": 115, "Year": 2026}` | 0.7193333333333335 | 0.7895 | 2026년 7월 기준 가동률 0.7193333333333335에 잔여 여력의 25%를 적용해 최종 가동률 0.7895로 산정했다. |
| 68 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.1, "Period": 116, "Year": 2026}` | 0.713456790123457 | 0.7850925925925927 | 2026년 8월 기준 가동률 0.713456790123457에서 잔여 여력 25% 활용을 반영해 0.7850925925925927로 산정했다. |
| 69 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.1, "Period": 117, "Year": 2026}` | 0.7732345679012347 | 0.829925925925926 | 2026년 9월 기준 가동률 0.7732345679012347에 대체 가능성 25%를 잔여 여력 기준으로 적용해 0.829925925925926으로 산정했다. |
| 70 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T5", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.1, "Period": 118, "Year": 2026}` | 0.7120493827160495 | 0.7840370370370371 | 2026년 10월 기준 가동률 0.7120493827160495에 잔여 여력의 25%를 반영해 0.7840370370370371로 산정했다. |
| 71 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T5", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.1, "Period": 119, "Year": 2026}` | 0.7283209876543211 | 0.7962407407407409 | 2026년 11월 기준 가동률 0.7283209876543211의 잔여 여력 중 25%를 상향해 0.7962407407407409로 산정했다. |
| 72 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T5", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.1, "Period": 120, "Year": 2026}` | 0.7569876543209877 | 0.8177407407407408 | 2026년 12월 기준 가동률 0.7569876543209877에서 제한적 대체 공급 25%를 잔여 여력에 적용해 0.8177407407407408로 산정했다. |
| 73 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.1, "Period": 115, "Year": 2026}` | 0.7193333333333335 | 0.7895 | 2026년 7월 기준 가동률 0.7193333333333335에 잔여 여력의 25%를 더해 0.7895로 산정했다. |
| 74 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.1, "Period": 116, "Year": 2026}` | 0.713456790123457 | 0.7850925925925927 | 2026년 8월 기준 가동률 0.713456790123457에서 대체 가능성 25%를 잔여 여력 기준으로 반영해 0.7850925925925927로 산정했다. |
| 75 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.1, "Period": 117, "Year": 2026}` | 0.7732345679012347 | 0.829925925925926 | 2026년 9월 기준 가동률 0.7732345679012347의 잔여 여력 중 25%를 반영해 0.829925925925926으로 산정했다. |
| 76 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 4.1, "Period": 118, "Year": 2026}` | 0.7120493827160495 | 0.7840370370370371 | 2026년 10월 기준 가동률 0.7120493827160495에 제한적 대체 공급 25%를 잔여 여력으로 적용해 0.7840370370370371로 산정했다. |
| 77 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 4.1, "Period": 119, "Year": 2026}` | 0.7283209876543211 | 0.7962407407407409 | 2026년 11월 기준 가동률 0.7283209876543211에서 잔여 여력의 25%를 더해 0.7962407407407409로 산정했다. |
| 78 | `{"Country": "Nigeria", "LNG Plant": "NLNG", "LNG Plant Train": "NLNG T6", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 4.1, "Period": 120, "Year": 2026}` | 0.7569876543209877 | 0.8177407407407408 | 2026년 12월 기준 가동률 0.7569876543209877에 잔여 여력 25% 활용을 반영해 0.8177407407407408로 산정했다. |
| 79 | `{"Country": "Angola", "LNG Plant": "Angola LNG", "LNG Plant Train": "Angola LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 115, "Year": 2026}` | 0.2840192307692308 | 0.4630144230769231 | 2026년 7월 기준 가동률 0.2840192307692308에 잔여 여력의 25%를 반영해 0.4630144230769231로 산정했다. |
| 80 | `{"Country": "Angola", "LNG Plant": "Angola LNG", "LNG Plant Train": "Angola LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 116, "Year": 2026}` | 0.9073846153846152 | 0.9305384615384616 | 2026년 8월 기준 가동률 0.9073846153846153은 이미 높으므로 잔여 여력의 25%만 보수적으로 추가해 0.9305384615384615로 산정했다. |
| 81 | `{"Country": "Angola", "LNG Plant": "Angola LNG", "LNG Plant Train": "Angola LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 117, "Year": 2026}` | 0.7088846153846153 | 0.7816634615384614 | 2026년 9월 기준 가동률 0.7088846153846153에서 대체 가능성 25%를 잔여 여력에 적용해 0.7816634615384615로 산정했다. |
| 82 | `{"Country": "Angola", "LNG Plant": "Angola LNG", "LNG Plant Train": "Angola LNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 5.2, "Period": 118, "Year": 2026}` | 0.6896346153846152 | 0.7672259615384615 | 2026년 10월 기준 가동률 0.6896346153846152에 잔여 여력의 25%를 더해 0.7672259615384614로 산정했다. |
| 83 | `{"Country": "Angola", "LNG Plant": "Angola LNG", "LNG Plant Train": "Angola LNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 5.2, "Period": 119, "Year": 2026}` | 0.7808076923076923 | 0.8356057692307692 | 2026년 11월 기준 가동률 0.7808076923076923에서 제한적 대체 공급 25%를 잔여 여력에 반영해 0.8356057692307692로 산정했다. |
| 84 | `{"Country": "Angola", "LNG Plant": "Angola LNG", "LNG Plant Train": "Angola LNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 5.2, "Period": 120, "Year": 2026}` | 0.9246153846153844 | 0.9434615384615384 | 2026년 12월 기준 가동률 0.9246153846153845가 높아 잔여 여력의 25%만 추가 반영하고 상한 1.0 이내인 0.9434615384615384로 산정했다. |
| 85 | `{"Country": "Equatorial Guinea", "LNG Plant": "EG LNG", "LNG Plant Train": "EG LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.7, "Period": 115, "Year": 2026}` | 0.6918918918918919 | 0.768918918918919 | 2026년 7월 기준 가동률 0.6918918918918919에 잔여 여력의 25%를 반영해 0.7689189189189189로 산정했다. |
| 86 | `{"Country": "Equatorial Guinea", "LNG Plant": "EG LNG", "LNG Plant Train": "EG LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.7, "Period": 116, "Year": 2026}` | 0.6918918918918919 | 0.768918918918919 | 2026년 8월 기준 가동률 0.6918918918918919에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.7689189189189189로 산정했다. |
| 87 | `{"Country": "Equatorial Guinea", "LNG Plant": "EG LNG", "LNG Plant Train": "EG LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.7, "Period": 117, "Year": 2026}` | 0.6918918918918919 | 0.768918918918919 | 2026년 9월 기준 가동률 0.6918918918918919에 잔여 여력의 25%를 더해 최종 가동률 0.7689189189189189를 적용했다. |
| 88 | `{"Country": "Equatorial Guinea", "LNG Plant": "EG LNG", "LNG Plant Train": "EG LNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 3.7, "Period": 118, "Year": 2026}` | 0.6918918918918919 | 0.768918918918919 | 2026년 10월 선택 슬롯은 영향 기간에 포함되므로 기준 가동률 0.6918918918918919의 잔여 여력 중 25%를 반영해 0.7689189189189189로 산정했다. |
| 89 | `{"Country": "Equatorial Guinea", "LNG Plant": "EG LNG", "LNG Plant Train": "EG LNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 3.7, "Period": 119, "Year": 2026}` | 0.6918918918918919 | 0.768918918918919 | 2026년 11월 기준 가동률 0.6918918918918919에서 제한적 대체 공급 가능성 25%를 잔여 여력 기준으로 적용해 0.7689189189189189로 산정했다. |
| 90 | `{"Country": "Equatorial Guinea", "LNG Plant": "EG LNG", "LNG Plant Train": "EG LNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 3.7, "Period": 120, "Year": 2026}` | 0.6918918918918919 | 0.768918918918919 | 2026년 12월 기준 가동률 0.6918918918918919에 잔여 여력의 25%를 반영해 0.7689189189189189를 최종 입력값으로 산정했다. |

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
  "mi_event_id": 1117,
  "model_param_proposal_id": 91,
  "proposal_completed_dtm": "2026-07-07 23:33:21.689833",
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
      "rationale": "대체 가스 공급 가능성 25%는 노르웨이 upstream 차질을 LNG로 일부 전환할 때 인접·시장연결 공급국의 액화설비 가동률을 조정하는 LiqUtilAdjustment와 직접 연결된다. 6개월 기간, 급격한 발생, 점진적 회복은 적용 시간축을 2026년 7~12월로 잡는 보조 맥락으로 반영했으며, 제한적인 대체 가능성을 고려해 잔여 가동 여력 중 일부만 상향하고 이미 상한에 근접한 설비는 1.0을 넘지 않도록 제안했다.",
      "values": [
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 7월 선택 슬롯의 기준 가동률 0.19018404907975456에 대체 공급 가능성 25%를 잔여 여력에 적용해 0.19018404907975456 + 0.25 × (1 - 0.19018404907975456) = 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 8월은 6개월 영향 구간 내 선택 슬롯이므로 기준 가동률 0.19018404907975456의 잔여 여력 중 25%를 반영해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 9월 기준 가동률 0.19018404907975456에 제한적 대체 공급 강도 25%를 잔여 여력 기준으로 적용해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 10월 선택 슬롯은 영향 기간 중간 구간이므로 기준 가동률 0.19018404907975456에서 잔여 여력의 25%만 상향해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 11월 기준 가동률 0.19018404907975456에 25% 대체 가능성을 잔여 여력 보정으로 반영해 최종 가동률 0.3926380368098159를 적용했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL1Z",
          "LNG Plant Train": "Arzew GL1Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 7.9,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 12월은 6개월 영향 구간의 마지막 선택 슬롯으로, 기준 가동률 0.19018404907975456에 잔여 여력의 25%를 더해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 7월 기준 가동률 0.19018404907975456에 제한적 대체 공급 25%를 잔여 여력에 적용해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 8월 기준 가동률 0.19018404907975456의 잔여 여력 중 25%를 활용하는 보수적 상향으로 0.3926380368098159를 적용했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 9월 선택 슬롯은 영향 기간에 포함되므로 기준 가동률 0.19018404907975456에서 잔여 여력의 25%만 상향해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 10월 기준 가동률 0.19018404907975456에 대체 가능성 25%를 잔여 여력 기준으로 반영해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 11월 기준 가동률 0.19018404907975456에 잔여 가동 여력의 25%를 더해 0.3926380368098159로 제안했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL2Z",
          "LNG Plant Train": "Arzew GL2Z T1-T6",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 8.4,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.19018404907975456,
          "proposedValue": 0.3926380368098159,
          "rationale": "2026년 12월 기준 가동률 0.19018404907975456에서 25% 대체 가능성을 잔여 여력에만 적용해 0.3926380368098159로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL3Z (Gassi Touil)",
          "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 1.0000000000000002,
          "proposedValue": 1,
          "rationale": "2026년 7월 기준 가동률이 1.0000000000000002로 이미 상한 수준이므로 추가 대체 공급 여력은 없다고 보고 입력 상한 1.0을 적용했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL3Z (Gassi Touil)",
          "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 1.0000000000000002,
          "proposedValue": 1,
          "rationale": "2026년 8월 기준 가동률이 상한 수준이어서 잔여 여력 보정 후에도 1.0을 초과하지 않도록 1.0으로 제한했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL3Z (Gassi Touil)",
          "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 1.0000000000000002,
          "proposedValue": 1,
          "rationale": "2026년 9월 기준 가동률이 1.0000000000000002로 이미 최대 수준이므로 대체 공급 상향은 상한에 의해 1.0으로 적용했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL3Z (Gassi Touil)",
          "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 1.0000000000000002,
          "proposedValue": 1,
          "rationale": "2026년 10월 기준 가동률이 이미 상한 수준이므로 추가 상승 여력을 인정하지 않고 최종 입력값을 1.0으로 제한했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL3Z (Gassi Touil)",
          "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 1.0000000000000002,
          "proposedValue": 1,
          "rationale": "2026년 11월 기준 가동률이 최대치에 있어 대체 공급 가능성 25%를 반영해도 최종 값은 입력 상한 1.0으로 유지했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Arzew GL3Z (Gassi Touil)",
          "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.7,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 1.0000000000000002,
          "proposedValue": 1,
          "rationale": "2026년 12월 기준 가동률이 상한 수준이므로 6개월 영향 구간 내에서도 추가 상향 없이 1.0을 적용했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7999999999999999,
          "proposedValue": 0.85,
          "rationale": "2026년 7월 기준 가동률 0.7999999999999999에 잔여 여력 0.2000000000000001의 25%를 더해 0.85로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.7999999999999999,
          "proposedValue": 0.85,
          "rationale": "2026년 8월 기준 가동률 0.7999999999999999의 잔여 여력 중 25%를 활용해 최종 가동률 0.85를 적용했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7999999999999999,
          "proposedValue": 0.85,
          "rationale": "2026년 9월 선택 슬롯에 기준 가동률 0.7999999999999999와 대체 가능성 25%를 반영해 0.85로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.7999999999999999,
          "proposedValue": 0.85,
          "rationale": "2026년 10월 기준 가동률 0.7999999999999999에서 잔여 가동 여력의 25%를 더해 0.85를 적용했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7999999999999999,
          "proposedValue": 0.85,
          "rationale": "2026년 11월 기준 가동률 0.7999999999999999에 제한적 대체 공급분을 잔여 여력 기준으로 반영해 0.85로 산정했다."
        },
        {
          "Country": "Algeria",
          "LNG Plant": "Skikda GL1K",
          "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.5,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.7999999999999999,
          "proposedValue": 0.85,
          "rationale": "2026년 12월 기준 가동률 0.7999999999999999의 잔여 여력 25%만 상향해 최종 입력값 0.85를 적용했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Damietta LNG",
          "LNG Plant Train": "Damietta LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 7월 기준 가동률은 0이나 선택된 운영 설비이므로 대체 공급 가능성 25%를 보수적 재가동 수준으로 해석해 최종 가동률 0.25를 적용했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Damietta LNG",
          "LNG Plant Train": "Damietta LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 8월 기준 가동률 0에서 제한적 대체 가능성 25%를 직접 반영해 보수적 가동률 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Damietta LNG",
          "LNG Plant Train": "Damietta LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 9월 선택 슬롯은 6개월 영향 구간에 포함되며, 기준 가동률 0의 운영 설비에 대체 가능성 25%를 적용해 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Damietta LNG",
          "LNG Plant Train": "Damietta LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 10월 기준 가동률 0에서 선택된 대체 공급 가능성 25%만큼의 제한적 운전을 가정해 0.25를 적용했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Damietta LNG",
          "LNG Plant Train": "Damietta LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 11월 기준 가동률 0에 대해 대체 공급 가능성이 25%로 제한된 점을 반영해 최종 가동률 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Damietta LNG",
          "LNG Plant Train": "Damietta LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 3,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 12월 기준 가동률 0인 운영 설비에 6개월 영향 구간의 제한적 대체 공급 가능성 25%를 반영해 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 7월 기준 가동률 0에서 대체 공급 가능성 25%를 보수적 운전 수준으로 적용해 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 8월 선택 슬롯은 기준 가동률 0이나 운영 상태 설비이므로 제한적 대체 공급 25%를 반영해 0.25를 적용했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 9월 기준 가동률 0에 대해 대체 공급 가능성이 25%로 제한된 점을 최종 가동률 0.25로 반영했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 10월 기준 가동률 0인 선택 슬롯에 제한적 대체 가능성 25%를 적용해 보수적 최종 입력값 0.25를 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 11월 선택 슬롯의 기준 가동률 0에서 25% 대체 공급 가능성을 반영해 최종 가동률 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 12월 기준 가동률 0에 대해 6개월 영향 구간 내 제한적 운전 가능성을 25%로 반영해 0.25를 적용했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 7월 기준 가동률 0인 선택 슬롯에 대체 공급 가능성 25%를 보수적으로 적용해 최종 가동률 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 8월 기준 가동률 0에서 선택된 대체 공급 가능성 25%만큼의 제한적 가동을 반영해 0.25를 적용했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 9월 기준 가동률 0에 6개월 영향 구간의 대체 가능성 25%를 반영해 최종 입력값 0.25를 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T2",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 10월 선택 슬롯은 기준 가동률 0이나 운영 설비로 분류되어 있어 제한적 대체 공급 25%를 최종 가동률 0.25로 반영했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T2",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 11월 기준 가동률 0에서 대체 공급 가능성 25%를 적용해 보수적 최종 가동률 0.25로 산정했다."
        },
        {
          "Country": "Egypt",
          "LNG Plant": "Egyptian LNG (Idku)",
          "LNG Plant Train": "Egyptian LNG (Idku) T2",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 3.6,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.25,
          "rationale": "2026년 12월 기준 가동률 0인 선택 슬롯에 25% 대체 가능성을 반영해 0.25를 최종 입력값으로 적용했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7420234122042342,
          "proposedValue": 0.8065175591531756,
          "rationale": "2026년 7월 기준 가동률 0.7420234122042342에 잔여 여력의 25%를 더해 0.8065175591531756으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.7359392278953923,
          "proposedValue": 0.8019544209215442,
          "rationale": "2026년 8월 기준 가동률 0.7359392278953923에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.8019544209215442로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7718854296388543,
          "proposedValue": 0.8289140722291407,
          "rationale": "2026년 9월 기준 가동률 0.7718854296388543의 잔여 여력 중 25%를 상향 반영해 0.8289140722291407로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.7344876712328768,
          "proposedValue": 0.8008657534246576,
          "rationale": "2026년 10월 기준 가동률 0.7344876712328768에 잔여 여력 25% 활용을 반영해 0.8008657534246576으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7270535491905354,
          "proposedValue": 0.7952901618929016,
          "rationale": "2026년 11월 기준 가동률 0.7270535491905354에서 대체 가능성 25%를 잔여 여력에 적용해 0.7952901618929016으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.7808448318804485,
          "proposedValue": 0.8356336239103364,
          "rationale": "2026년 12월 기준 가동률 0.7808448318804485의 잔여 여력 중 25%를 반영해 0.8356336239103364로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7420234122042342,
          "proposedValue": 0.8065175591531756,
          "rationale": "2026년 7월 기준 가동률 0.7420234122042342에 잔여 여력의 25%를 더해 최종 가동률 0.8065175591531756으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.7359392278953923,
          "proposedValue": 0.8019544209215442,
          "rationale": "2026년 8월 기준 가동률 0.7359392278953923에서 잔여 여력의 25%를 반영해 0.8019544209215442로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7718854296388543,
          "proposedValue": 0.8289140722291407,
          "rationale": "2026년 9월 기준 가동률 0.7718854296388543에 대체 가능성 25%를 잔여 여력 기준으로 적용해 0.8289140722291407로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T2",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.7344876712328768,
          "proposedValue": 0.8008657534246576,
          "rationale": "2026년 10월 기준 가동률 0.7344876712328768의 잔여 여력 중 25%를 상향해 0.8008657534246576으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T2",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7270535491905354,
          "proposedValue": 0.7952901618929016,
          "rationale": "2026년 11월 기준 가동률 0.7270535491905354에서 제한적 대체 공급 25%를 잔여 여력에 반영해 0.7952901618929016으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T2",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.7808448318804485,
          "proposedValue": 0.8356336239103364,
          "rationale": "2026년 12월 기준 가동률 0.7808448318804485에 잔여 여력의 25%를 더해 0.8356336239103364로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7282220743697789,
          "proposedValue": 0.7961665557773342,
          "rationale": "2026년 7월 기준 가동률 0.7282220743697789에 잔여 여력의 25%를 반영해 0.7961665557773342로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.7222510534486581,
          "proposedValue": 0.7916882900864936,
          "rationale": "2026년 8월 기준 가동률 0.7222510534486581의 잔여 여력 중 25%를 상향해 0.7916882900864936으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7827796259333183,
          "proposedValue": 0.8370847194499887,
          "rationale": "2026년 9월 기준 가동률 0.7827796259333183에서 대체 가능성 25%를 잔여 여력에 적용해 0.8370847194499887로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T3",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.7208264951578326,
          "proposedValue": 0.7906198713683744,
          "rationale": "2026년 10월 기준 가동률 0.7208264951578326에 잔여 여력의 25%를 더해 0.7906198713683744로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T3",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7373149996303687,
          "proposedValue": 0.8029862497227765,
          "rationale": "2026년 11월 기준 가동률 0.7373149996303687에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.8029862497227765로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T3",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 3.3,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.7663214312116507,
          "proposedValue": 0.824741073408738,
          "rationale": "2026년 12월 기준 가동률 0.7663214312116507에 잔여 여력의 25%를 반영해 0.824741073408738로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7193333333333335,
          "proposedValue": 0.7895,
          "rationale": "2026년 7월 기준 가동률 0.7193333333333335에 잔여 여력의 25%를 더해 0.7895로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.713456790123457,
          "proposedValue": 0.7850925925925927,
          "rationale": "2026년 8월 기준 가동률 0.713456790123457에서 잔여 여력의 25%를 반영해 0.7850925925925927로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7732345679012347,
          "proposedValue": 0.829925925925926,
          "rationale": "2026년 9월 기준 가동률 0.7732345679012347에 잔여 여력의 25%를 상향 반영해 0.829925925925926으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T4",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.7120493827160495,
          "proposedValue": 0.7840370370370371,
          "rationale": "2026년 10월 기준 가동률 0.7120493827160495에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.7840370370370371로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T4",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7283209876543211,
          "proposedValue": 0.7962407407407409,
          "rationale": "2026년 11월 기준 가동률 0.7283209876543211에 잔여 여력의 25%를 더해 0.7962407407407409로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T4",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.7569876543209877,
          "proposedValue": 0.8177407407407408,
          "rationale": "2026년 12월 기준 가동률 0.7569876543209877의 잔여 여력 중 25%를 반영해 0.8177407407407408로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7193333333333335,
          "proposedValue": 0.7895,
          "rationale": "2026년 7월 기준 가동률 0.7193333333333335에 잔여 여력의 25%를 적용해 최종 가동률 0.7895로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.713456790123457,
          "proposedValue": 0.7850925925925927,
          "rationale": "2026년 8월 기준 가동률 0.713456790123457에서 잔여 여력 25% 활용을 반영해 0.7850925925925927로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7732345679012347,
          "proposedValue": 0.829925925925926,
          "rationale": "2026년 9월 기준 가동률 0.7732345679012347에 대체 가능성 25%를 잔여 여력 기준으로 적용해 0.829925925925926으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T5",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.7120493827160495,
          "proposedValue": 0.7840370370370371,
          "rationale": "2026년 10월 기준 가동률 0.7120493827160495에 잔여 여력의 25%를 반영해 0.7840370370370371로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T5",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7283209876543211,
          "proposedValue": 0.7962407407407409,
          "rationale": "2026년 11월 기준 가동률 0.7283209876543211의 잔여 여력 중 25%를 상향해 0.7962407407407409로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T5",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.7569876543209877,
          "proposedValue": 0.8177407407407408,
          "rationale": "2026년 12월 기준 가동률 0.7569876543209877에서 제한적 대체 공급 25%를 잔여 여력에 적용해 0.8177407407407408로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.7193333333333335,
          "proposedValue": 0.7895,
          "rationale": "2026년 7월 기준 가동률 0.7193333333333335에 잔여 여력의 25%를 더해 0.7895로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.713456790123457,
          "proposedValue": 0.7850925925925927,
          "rationale": "2026년 8월 기준 가동률 0.713456790123457에서 대체 가능성 25%를 잔여 여력 기준으로 반영해 0.7850925925925927로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7732345679012347,
          "proposedValue": 0.829925925925926,
          "rationale": "2026년 9월 기준 가동률 0.7732345679012347의 잔여 여력 중 25%를 반영해 0.829925925925926으로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.7120493827160495,
          "proposedValue": 0.7840370370370371,
          "rationale": "2026년 10월 기준 가동률 0.7120493827160495에 제한적 대체 공급 25%를 잔여 여력으로 적용해 0.7840370370370371로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7283209876543211,
          "proposedValue": 0.7962407407407409,
          "rationale": "2026년 11월 기준 가동률 0.7283209876543211에서 잔여 여력의 25%를 더해 0.7962407407407409로 산정했다."
        },
        {
          "Country": "Nigeria",
          "LNG Plant": "NLNG",
          "LNG Plant Train": "NLNG T6",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 4.1,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.7569876543209877,
          "proposedValue": 0.8177407407407408,
          "rationale": "2026년 12월 기준 가동률 0.7569876543209877에 잔여 여력 25% 활용을 반영해 0.8177407407407408로 산정했다."
        },
        {
          "Country": "Angola",
          "LNG Plant": "Angola LNG",
          "LNG Plant Train": "Angola LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.2840192307692308,
          "proposedValue": 0.4630144230769231,
          "rationale": "2026년 7월 기준 가동률 0.2840192307692308에 잔여 여력의 25%를 반영해 0.4630144230769231로 산정했다."
        },
        {
          "Country": "Angola",
          "LNG Plant": "Angola LNG",
          "LNG Plant Train": "Angola LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.9073846153846152,
          "proposedValue": 0.9305384615384616,
          "rationale": "2026년 8월 기준 가동률 0.9073846153846153은 이미 높으므로 잔여 여력의 25%만 보수적으로 추가해 0.9305384615384615로 산정했다."
        },
        {
          "Country": "Angola",
          "LNG Plant": "Angola LNG",
          "LNG Plant Train": "Angola LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.7088846153846153,
          "proposedValue": 0.7816634615384614,
          "rationale": "2026년 9월 기준 가동률 0.7088846153846153에서 대체 가능성 25%를 잔여 여력에 적용해 0.7816634615384615로 산정했다."
        },
        {
          "Country": "Angola",
          "LNG Plant": "Angola LNG",
          "LNG Plant Train": "Angola LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.6896346153846152,
          "proposedValue": 0.7672259615384615,
          "rationale": "2026년 10월 기준 가동률 0.6896346153846152에 잔여 여력의 25%를 더해 0.7672259615384614로 산정했다."
        },
        {
          "Country": "Angola",
          "LNG Plant": "Angola LNG",
          "LNG Plant Train": "Angola LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.7808076923076923,
          "proposedValue": 0.8356057692307692,
          "rationale": "2026년 11월 기준 가동률 0.7808076923076923에서 제한적 대체 공급 25%를 잔여 여력에 반영해 0.8356057692307692로 산정했다."
        },
        {
          "Country": "Angola",
          "LNG Plant": "Angola LNG",
          "LNG Plant Train": "Angola LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 5.2,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.9246153846153844,
          "proposedValue": 0.9434615384615384,
          "rationale": "2026년 12월 기준 가동률 0.9246153846153845가 높아 잔여 여력의 25%만 추가 반영하고 상한 1.0 이내인 0.9434615384615384로 산정했다."
        },
        {
          "Country": "Equatorial Guinea",
          "LNG Plant": "EG LNG",
          "LNG Plant Train": "EG LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 3.7,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.6918918918918919,
          "proposedValue": 0.768918918918919,
          "rationale": "2026년 7월 기준 가동률 0.6918918918918919에 잔여 여력의 25%를 반영해 0.7689189189189189로 산정했다."
        },
        {
          "Country": "Equatorial Guinea",
          "LNG Plant": "EG LNG",
          "LNG Plant Train": "EG LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 3.7,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.6918918918918919,
          "proposedValue": 0.768918918918919,
          "rationale": "2026년 8월 기준 가동률 0.6918918918918919에서 제한적 대체 가능성 25%를 잔여 여력에 적용해 0.7689189189189189로 산정했다."
        },
        {
          "Country": "Equatorial Guinea",
          "LNG Plant": "EG LNG",
          "LNG Plant Train": "EG LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 3.7,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.6918918918918919,
          "proposedValue": 0.768918918918919,
          "rationale": "2026년 9월 기준 가동률 0.6918918918918919에 잔여 여력의 25%를 더해 최종 가동률 0.7689189189189189를 적용했다."
        },
        {
          "Country": "Equatorial Guinea",
          "LNG Plant": "EG LNG",
          "LNG Plant Train": "EG LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 3.7,
          "Period": 118,
          "Year": 2026,
          "basecaseValue": 0.6918918918918919,
          "proposedValue": 0.768918918918919,
          "rationale": "2026년 10월 선택 슬롯은 영향 기간에 포함되므로 기준 가동률 0.6918918918918919의 잔여 여력 중 25%를 반영해 0.7689189189189189로 산정했다."
        },
        {
          "Country": "Equatorial Guinea",
          "LNG Plant": "EG LNG",
          "LNG Plant Train": "EG LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 3.7,
          "Period": 119,
          "Year": 2026,
          "basecaseValue": 0.6918918918918919,
          "proposedValue": 0.768918918918919,
          "rationale": "2026년 11월 기준 가동률 0.6918918918918919에서 제한적 대체 공급 가능성 25%를 잔여 여력 기준으로 적용해 0.7689189189189189로 산정했다."
        },
        {
          "Country": "Equatorial Guinea",
          "LNG Plant": "EG LNG",
          "LNG Plant Train": "EG LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 3.7,
          "Period": 120,
          "Year": 2026,
          "basecaseValue": 0.6918918918918919,
          "proposedValue": 0.768918918918919,
          "rationale": "2026년 12월 기준 가동률 0.6918918918918919에 잔여 여력의 25%를 반영해 0.7689189189189189를 최종 입력값으로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.456 | 3.456 | 2236 | 83 | 2319 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:54.821 | 114.821 | 11473 | 14332 | 25805 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 02:27.824 | 147.824 | 20183 | 15127 | 35310 |

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
      "comment": "타 LNG 공급국 가동률 상향으로 상쇄 : 부족 LNG 물량을 대체 가능한 공급국의 잔여 액화 가동 여력에 배분하고, 이미 고가동 설비는 배분 제외",
      "dimension": "alt_lng_supply_availability (대체 LNG 공급 가능성)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "급격(사고)/점진(정비)",
      "dimension": "onset_pattern (발생 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "시간축",
      "dimension": "period (기간)",
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
      "comment": "Plant>Train 가동률(%) 조정 : 차질 대상 액화 Plant/Train의 이용률을 조정하고, 단기·부분 차질은 생산량보다 utilization 조정을 우선 사용",
      "dimension": "utilization_change_amount (Utilization 변화량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "대폭·영구 손실 시 생산량(Mt LNG) 직접 : 장기·영구 손실 또는 설비 폐쇄 수준이면 Plant/Train 생산량 자체를 하향 조정",
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

- 대상 scenario_ids: [105, 106]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=105 1개월 내 미세 감산 후 정상화

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:35.623 (95.623s)
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

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 3 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=3, basecaseValue_present=3 | PASS |
| Step2 slot axis value 수 | `{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 3 | Utilization 변화량이 '<5%'로 제시되어 Train/month 단위 액화시설 가동률 비율을 직접 조정하는 LiqUtilAdjustment와 연결된다. 기간은 1개월 이하이고 회복 패턴은 급격하므로 Cameron LNG의 선택된 2026년 7월 Train들에만 소폭 하향을 적용하고, 정상가동 유지 및 가격 영향 중립이라는 시나리오 성격을 반영해 단기·균등 감산 후 추가 지속 조정은 두지 않는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 0.870225523664935 | 선택된 Cameron LNG T1의 2026년 7월 slot에 대해, 동일 Train의 2026년 7월 기준값 0.8971397151184897을 기준 형식으로 사용했다. '<5%'의 미세 감산과 1개월 이하의 단기 조정을 반영해 기준값을 3% 하향하여 0.8971397151184897 × 0.97 = 0.870225523664935로 산정했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 0.870225523664935 | 선택된 Cameron LNG T2의 2026년 7월 slot에 대해, 동일 Train의 2026년 7월 기준값 0.8971397151184897을 기준 형식으로 사용했다. 터미널 전반의 짧은 운영 조정으로 해석해 T1과 동일한 3% 하향을 적용하여 0.8971397151184897 × 0.97 = 0.870225523664935로 산정했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 0.870225523664935 | 선택된 Cameron LNG T3의 2026년 7월 slot에 대해, 동일 Train의 2026년 7월 기준값 0.8971397151184897을 기준 형식으로 사용했다. '<5%' 감소 범위 내에서 정상가동 유지와 급격한 회복을 반영하기 위해 1개월 한정 3% 하향을 적용하여 0.8971397151184897 × 0.97 = 0.870225523664935로 산정했다. |

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
  "model_param_proposal_id": 87,
  "proposal_completed_dtm": "2026-07-07 23:29:54.163224",
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
      "rationale": "Utilization 변화량이 '<5%'로 제시되어 Train/month 단위 액화시설 가동률 비율을 직접 조정하는 LiqUtilAdjustment와 연결된다. 기간은 1개월 이하이고 회복 패턴은 급격하므로 Cameron LNG의 선택된 2026년 7월 Train들에만 소폭 하향을 적용하고, 정상가동 유지 및 가격 영향 중립이라는 시나리오 성격을 반영해 단기·균등 감산 후 추가 지속 조정은 두지 않는 구조로 제안한다.",
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
          "proposedValue": 0.870225523664935,
          "rationale": "선택된 Cameron LNG T1의 2026년 7월 slot에 대해, 동일 Train의 2026년 7월 기준값 0.8971397151184897을 기준 형식으로 사용했다. '<5%'의 미세 감산과 1개월 이하의 단기 조정을 반영해 기준값을 3% 하향하여 0.8971397151184897 × 0.97 = 0.870225523664935로 산정했다."
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
          "proposedValue": 0.870225523664935,
          "rationale": "선택된 Cameron LNG T2의 2026년 7월 slot에 대해, 동일 Train의 2026년 7월 기준값 0.8971397151184897을 기준 형식으로 사용했다. 터미널 전반의 짧은 운영 조정으로 해석해 T1과 동일한 3% 하향을 적용하여 0.8971397151184897 × 0.97 = 0.870225523664935로 산정했다."
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
          "proposedValue": 0.870225523664935,
          "rationale": "선택된 Cameron LNG T3의 2026년 7월 slot에 대해, 동일 Train의 2026년 7월 기준값 0.8971397151184897을 기준 형식으로 사용했다. '<5%' 감소 범위 내에서 정상가동 유지와 급격한 회복을 반영하기 위해 1개월 한정 3% 하향을 적용하여 0.8971397151184897 × 0.97 = 0.870225523664935로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.582 | 3.582 | 2736 | 91 | 2827 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:13.299 | 13.299 | 11860 | 949 | 12809 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:46.576 | 46.576 | 10162 | 2784 | 12946 |

##### scenario_id=106 3개월간 완전 증산 반영

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:21.334 (81.334s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 9 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=9, basecaseValue_present=0 | PASS |
| Step2 slot axis value 수 | `{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 9 | Utilization 변화량 100%는 Cameron LNG의 정비 종료 후 완전 생산 재개를 Train별 액화 가동률 override에 직접 반영하는 값이며, LiqUtilAdjustment의 1.0=100% 가동률 의미와 연결된다. 기간 3개월은 적용 월을 현재 기준월 이후 3개월로 한정하고, 회복 패턴상 추가 ramp-up 없이 해당 기간 동안 정상가동 수준을 유지하는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | null | 1.0 | 선택된 2026년 7월 T1 슬롯은 3개월 정상가동 반영 기간의 첫 달이다. 기준 자료의 동일 월·Train 가동률 수준은 1.0 미만이나 선택 슬롯의 Period가 기준 record와 정확히 일치하지 않아 직접 참조값으로 쓰지 않고, 완전 생산 재개를 100% 가동률인 1.0으로 보수적으로 적용했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | null | 1.0 | 선택된 2026년 8월 T1 슬롯은 3개월 정상가동 반영 기간의 두 번째 달이다. 추가 ramp-up 없이 정상가동이 지속되는 조건이므로 완전 생산 재개 수준을 그대로 반영해 최종 가동률 입력값을 1.0으로 설정했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | null | 1.0 | 선택된 2026년 9월 T1 슬롯은 3개월 정상가동 반영 기간의 마지막 달이다. 회복 지연이나 단계적 증산이 없는 시나리오이므로 100% 정상가동을 의미하는 1.0을 최종 입력값으로 적용했다. |
| 4 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | null | 1.0 | 선택된 2026년 7월 T2 슬롯은 Cameron LNG 전체 Train 정상가동 반영 대상이다. 동일 기간의 기준값 형식은 utilization ratio이므로 완전 생산 재개를 100% 가동률인 1.0으로 변환해 적용했다. |
| 5 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | null | 1.0 | 선택된 2026년 8월 T2 슬롯은 3개월 적용 기간 중 두 번째 월이며, 정비 후 정상가동 지속을 반영한다. 단계적 회복 조정 없이 100% 가동률 수준인 1.0을 최종 입력값으로 설정했다. |
| 6 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | null | 1.0 | 선택된 2026년 9월 T2 슬롯은 정상가동 반영 기간의 세 번째 월이다. 시나리오가 완전 생산 재개와 지속 가동을 전제하므로 최종 가동률을 상한적 정상가동 수준인 1.0으로 적용했다. |
| 7 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | null | 1.0 | 선택된 2026년 7월 T3 슬롯은 Cameron LNG Train별 반영 대상 중 첫 적용 월이다. 기준 자료의 값 형식과 동일한 ratio 입력으로, 완전 생산 재개를 100% utilization인 1.0으로 설정했다. |
| 8 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | null | 1.0 | 선택된 2026년 8월 T3 슬롯은 3개월 적용 기간의 중간 월이다. ramp-up이 없다는 조건에 따라 전월과 동일하게 정상가동 수준을 유지하며 최종 입력값을 1.0으로 제안했다. |
| 9 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | null | 1.0 | 선택된 2026년 9월 T3 슬롯은 3개월 정상가동 반영의 마지막 월이다. 영구적 차질이 해소되어 별도 회복 구간 없이 정상가동이 유지되는 조건을 반영해 가동률 ratio를 1.0으로 설정했다. |

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
  "model_param_proposal_id": 86,
  "proposal_completed_dtm": "2026-07-07 23:29:44.689103",
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
      "rationale": "Utilization 변화량 100%는 Cameron LNG의 정비 종료 후 완전 생산 재개를 Train별 액화 가동률 override에 직접 반영하는 값이며, LiqUtilAdjustment의 1.0=100% 가동률 의미와 연결된다. 기간 3개월은 적용 월을 현재 기준월 이후 3개월로 한정하고, 회복 패턴상 추가 ramp-up 없이 해당 기간 동안 정상가동 수준을 유지하는 구조로 제안한다.",
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 7월 T1 슬롯은 3개월 정상가동 반영 기간의 첫 달이다. 기준 자료의 동일 월·Train 가동률 수준은 1.0 미만이나 선택 슬롯의 Period가 기준 record와 정확히 일치하지 않아 직접 참조값으로 쓰지 않고, 완전 생산 재개를 100% 가동률인 1.0으로 보수적으로 적용했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 8월 T1 슬롯은 3개월 정상가동 반영 기간의 두 번째 달이다. 추가 ramp-up 없이 정상가동이 지속되는 조건이므로 완전 생산 재개 수준을 그대로 반영해 최종 가동률 입력값을 1.0으로 설정했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 9월 T1 슬롯은 3개월 정상가동 반영 기간의 마지막 달이다. 회복 지연이나 단계적 증산이 없는 시나리오이므로 100% 정상가동을 의미하는 1.0을 최종 입력값으로 적용했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 7월 T2 슬롯은 Cameron LNG 전체 Train 정상가동 반영 대상이다. 동일 기간의 기준값 형식은 utilization ratio이므로 완전 생산 재개를 100% 가동률인 1.0으로 변환해 적용했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 8월 T2 슬롯은 3개월 적용 기간 중 두 번째 월이며, 정비 후 정상가동 지속을 반영한다. 단계적 회복 조정 없이 100% 가동률 수준인 1.0을 최종 입력값으로 설정했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 9월 T2 슬롯은 정상가동 반영 기간의 세 번째 월이다. 시나리오가 완전 생산 재개와 지속 가동을 전제하므로 최종 가동률을 상한적 정상가동 수준인 1.0으로 적용했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 7월 T3 슬롯은 Cameron LNG Train별 반영 대상 중 첫 적용 월이다. 기준 자료의 값 형식과 동일한 ratio 입력으로, 완전 생산 재개를 100% utilization인 1.0으로 설정했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 8월 T3 슬롯은 3개월 적용 기간의 중간 월이다. ramp-up이 없다는 조건에 따라 전월과 동일하게 정상가동 수준을 유지하며 최종 입력값을 1.0으로 제안했다."
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
          "basecaseValue": null,
          "proposedValue": 1.0,
          "rationale": "선택된 2026년 9월 T3 슬롯은 3개월 정상가동 반영의 마지막 월이다. 영구적 차질이 해소되어 별도 회복 구간 없이 정상가동이 유지되는 조건을 반영해 가동률 ratio를 1.0으로 설정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.290 | 3.290 | 2743 | 70 | 2813 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:17.548 | 17.548 | 11882 | 1759 | 13641 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:33.060 | 33.060 | 10850 | 1981 | 12831 |

#### event_type_l2_id=2 터미널 Utilization 변동

##### Scenario Group

```json
{
  "description": "이 그룹은 Golden Pass feedgas 반등 이후 추가 설비 업데이트가 제한된 상황에서, 미국 LNG 공급 여력이 단기 가격과 지역 수급에 어떻게 반영될 수 있는지 비교하기 위한 시나리오 묶음입니다. 핵심 분기 축은 이용률 변화 방향(증가·감소), 변화 폭(15%·60%·100%), 기간(1개월 이하·6개월), 전개 방식(Step·Gradual·영구 손실)입니다. 공급 확대 사례는 미국 수출 여력과 대서양 완충 확대를, 축소 사례는 현물 프리미엄과 유럽 조달 경쟁 심화를 점검합니다. 다만 가격 영향은 호르무즈 및 미국·이란 협상 변수와 함께 해석됩니다.",
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
  "mi_event_id": 1326,
  "request_usr_id": 1000085,
  "scenario_count": 6,
  "scenario_group_id": 46,
  "stage": "scenario_created",
  "status": "creating",
  "summary": "[미국 LNG 공급] Golden Pass 인도량 반등 후 추가 설비 업데이트 제한 → 가격 영향은 호르무즈 변수에 종속",
  "title": "Golden Pass feedgas 변화와 미국 LNG 공급 여력 시나리오"
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
      "comment": "타 LNG 공급국 가동률 상향으로 상쇄 : 부족 LNG 물량을 대체 가능한 공급국의 잔여 액화 가동 여력에 배분하고, 이미 고가동 설비는 배분 제외",
      "dimension": "alt_lng_supply_availability (대체 LNG 공급 가능성)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "급격(사고)/점진(정비)",
      "dimension": "onset_pattern (발생 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "시간축",
      "dimension": "period (기간)",
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
      "comment": "Plant>Train 가동률(%) 조정 : 차질 대상 액화 Plant/Train의 이용률을 조정하고, 단기·부분 차질은 생산량보다 utilization 조정을 우선 사용",
      "dimension": "utilization_change_amount (Utilization 변화량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "대폭·영구 손실 시 생산량(Mt LNG) 직접 : 장기·영구 손실 또는 설비 폐쇄 수준이면 Plant/Train 생산량 자체를 하향 조정",
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
  "created_at": "2026-06-21T00:26:14.606890",
  "detail_analysis": "사건 요약:\n직전 업데이트에서 Golden Pass 수출터미널 feedgas 인도량 반등과 계절 정비 이후 다른 미국 LNG 설비 이용률 상승이 확인됨. 이번 신규 연결 자료 중 2026년 6월 15일 및 6월 19일 Platts Daily Report는 Golden Pass의 추가 가동률 변화보다 미국·이란 협상, 호르무즈 정상화 불확실성, 유럽 저장률과 수입 흐름을 중심으로 제시됨. WoodMac weekly summary는 2026년 4월 16일 미국 Lower 48 가스 시장에서 생산 반등에도 주거·상업 수요 급감과 LNG feedgas 정체가 주간 100 Bcf 및 80 Bcf 주입 전망과 함께 언급된 내용임.\n\n영향 경로:\nGolden Pass feedgas 반등은 미국 LNG 액화터미널 이용률 상승과 수출 가능 cargo 증가로 이어지는 직접 Fundamental 개선 요인임. 다만 신규 자료 기준으로 Golden Pass 램프업 지속, 정비 종료 후 안정 가동, 추가 cargo 선적 확대에 대한 새로운 수치 확인은 제한적임. 2026년 4월 16일 WoodMac의 LNG feedgas 정체 언급은 Lower 48 전체 가스 수급의 저장 주입 확대 배경으로 제시된 내용이며, 직전 요약의 4월 말 이후 Golden Pass 반등을 직접 부정하는 최신 설비 업데이트는 아님.\n\n시장 반응:\n가격 반응은 이번 배치에서 터미널 이용률보다 지정학 뉴스에 더 크게 연동됨. 2026년 6월 15일 Platts Daily Report에서는 미국·이란 합의와 6월 19일 서명 기대가 호르무즈 재개 가능성을 키우며 JKM·NWE·FOB GCM 급락으로 연결됨. 2026년 6월 19일 Platts Daily Report에서는 평화협상 지연과 호르무즈 정상화 불확실성 속에 JKM이 5거래일 하락을 끊고 4.4% 반등함. 유럽에서는 EU 저장률 44.34%~45.56%, 6월 LNG 수입 13% 감소, 7월 프롬프트 타이트, 8월 이후 대서양 복귀 물량 기대가 NWE/TTF 할인 확대 요인으로 언급됨.\n\nLNG 시장 관점:\nEvent 경계상 핵심은 Golden Pass를 포함한 미국 LNG 터미널 utilization 및 feedgas 흐름 변화임. 신규 6월 Platts 자료의 호르무즈·미국 이란 협상·유럽 저장률 이슈는 가격 방향을 설명하는 파생 또는 병행 변수이며, Golden Pass 가동률 변화 자체로 확대 해석하기 어려움. 따라서 미국 LNG 공급 가용성 개선이라는 기존 방향은 유지하되, 단기 가격 Band는 설비 utilization보다 호르무즈 리스크 프리미엄, 유럽 prompt 타이트, 대서양 물량 복귀 기대에 더 민감한 구도임.",
  "event_title_ko": "Golden Pass LNG feedgas 반등",
  "event_type_l2_id": 2,
  "key_bullets": [],
  "latest_record_first_created": "2026-06-19T00:00:00",
  "mi_event_id": "1326",
  "occurred_at": "",
  "oldest_record_first_created": "",
  "one_line_summary": "[미국 LNG 공급] Golden Pass 인도량 반등 후 추가 설비 업데이트 제한 → 가격 영향은 호르무즈 변수에 종속",
  "source_mi_record_ids": [
    2231,
    3066,
    3315
  ],
  "tags": []
}
```

##### Group Test Summary

- 대상 scenario_ids: [273, 274]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=273 단기 소폭 후퇴, 현물 프리미엄은 제한적

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 01:26.262 (86.262s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "period": "1개월 이하",
    "recovery_pattern": "급격",
    "utilization_change_amount": "15%"
  },
  "impact": {
    "hh": "mild_bear",
    "jkm": "mild_bull",
    "ttf": "neutral"
  },
  "narrative": "Golden Pass의 feedgas 반등이 확인됐지만, 한 달 안에 이용률이 15%가량 계단식으로 낮아지는 단기 조정이 뒤따르는 그림이다.\n시장 참여자는 계절 정비 후 정상화가 완전히 굳어지기 전 nominations 변동이나 설비 점검이 다시 나타난 것으로 해석한다.\n미국산 LNG 공급 감소 폭은 작고 짧아 호르무즈 긴장이 없다면 아시아와 유럽 현물에는 제한적 프리미엄만 붙지만, 미국 내 가스 수요는 소폭 덜어낸다.\n따라서 구매자는 긴급 조달보다 선적 일정 확인에 집중하고, 트레이더는 중동 물류 뉴스가 결합될 때만 상승 베팅을 키운다.",
  "probability_delta": 0.0,
  "probability_score": 20.0,
  "scenario_group_id": 46,
  "scenario_id": 273,
  "status": "creating",
  "title": "단기 소폭 후퇴, 현물 프리미엄은 제한적"
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

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 3 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=3, basecaseValue_present=3 | PASS |
| Step2 slot axis value 수 | `{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 3 | Utilization 변화량 15%는 Golden Pass Plant/Train의 액화 가동률 비율을 직접 조정하는 입력과 연결되므로 LiqUtilAdjustment에 반영한다. 기간은 1개월 이하이고 회복 패턴은 급격하므로 적용 범위는 현재 단기 월에 한정하며, feedgas 반등 이후의 단기 소폭 후퇴라는 시나리오에 맞춰 선택된 Golden Pass Train의 가동률을 기준 대비 15% 상대 하향하는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T1", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.03, "Period": 112, "Year": 2026}` | 0.6390547263681591 | 0.5431965174129353 | 선택된 2026년 7월 Golden Pass LNG T1 슬롯은 단기 조정 대상 Train으로 보았다. 제공된 동일 연월·동일 Train의 기준 가동률 0.6390547263681591에 단기 15% 상대 하향을 적용해 최종 가동률을 0.6390547263681591×0.85=0.5431965174129353으로 산정했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T2", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.03, "Period": 112, "Year": 2026}` | 0.7766334991708126 | 0.6601384742951907 | 선택된 2026년 7월 Golden Pass LNG T2 슬롯은 T1과 같은 Golden Pass 단기 이용률 후퇴 대상에 포함했다. 제공된 동일 연월·동일 Train의 기준 가동률 0.7766334991708126에 15% 상대 하향을 적용해 최종 가동률을 0.7766334991708126×0.85=0.6601384742951907로 산정했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T3", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.03, "Period": 112, "Year": 2026}` | 0 | 0 | 선택된 2026년 7월 Golden Pass LNG T3 슬롯은 같은 설비 내 Train이지만 제공된 동일 연월·동일 Train의 기준 가동률이 0으로 설정되어 있다. 단기 15% 하향 충격을 적용해도 운전 가동률의 최종 입력값은 0×0.85=0으로 유지하는 것이 보수적이다. |

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
  "mi_event_id": 1326,
  "model_param_proposal_id": 88,
  "proposal_completed_dtm": "2026-07-07 23:31:10.955184",
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
      "rationale": "Utilization 변화량 15%는 Golden Pass Plant/Train의 액화 가동률 비율을 직접 조정하는 입력과 연결되므로 LiqUtilAdjustment에 반영한다. 기간은 1개월 이하이고 회복 패턴은 급격하므로 적용 범위는 현재 단기 월에 한정하며, feedgas 반등 이후의 단기 소폭 후퇴라는 시나리오에 맞춰 선택된 Golden Pass Train의 가동률을 기준 대비 15% 상대 하향하는 구조로 제안한다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T1",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.6390547263681591,
          "proposedValue": 0.5431965174129353,
          "rationale": "선택된 2026년 7월 Golden Pass LNG T1 슬롯은 단기 조정 대상 Train으로 보았다. 제공된 동일 연월·동일 Train의 기준 가동률 0.6390547263681591에 단기 15% 상대 하향을 적용해 최종 가동률을 0.6390547263681591×0.85=0.5431965174129353으로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T2",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.7766334991708126,
          "proposedValue": 0.6601384742951907,
          "rationale": "선택된 2026년 7월 Golden Pass LNG T2 슬롯은 T1과 같은 Golden Pass 단기 이용률 후퇴 대상에 포함했다. 제공된 동일 연월·동일 Train의 기준 가동률 0.7766334991708126에 15% 상대 하향을 적용해 최종 가동률을 0.7766334991708126×0.85=0.6601384742951907로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "선택된 2026년 7월 Golden Pass LNG T3 슬롯은 같은 설비 내 Train이지만 제공된 동일 연월·동일 Train의 기준 가동률이 0으로 설정되어 있다. 단기 15% 하향 충격을 적용해도 운전 가동률의 최종 입력값은 0×0.85=0으로 유지하는 것이 보수적이다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 46,
  "scenario_id": 273,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.171 | 3.171 | 2576 | 68 | 2644 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:17.775 | 17.775 | 11700 | 1056 | 12756 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:48.037 | 48.037 | 9721 | 2722 | 12443 |

##### scenario_id=274 반년 점진 증산, 대서양 LNG 완충 확대

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:49.876 (169.876s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "period": "6개월",
    "recovery_pattern": "점진",
    "utilization_change_amount": "60%"
  },
  "impact": {
    "hh": "mild_bull",
    "jkm": "mild_bear",
    "ttf": "bear"
  },
  "narrative": "Golden Pass와 다른 미국 LNG 설비의 인도량 반등이 여섯 달에 걸쳐 60% 수준의 점진적 이용률 상승으로 이어지는 경로다.\n시장 참여자는 정비 종료 후 압축기와 액화트레인이 순차적으로 안정화되며, 추가 공시가 적어도 실제 선적 가능 물량은 꾸준히 늘어난다고 본다.\n대서양 Basin의 가용 카고가 늘어 유럽은 재고 보충 여지가 커지고, 아시아 구매자는 호르무즈 관련 위험 프리미엄을 일부 상쇄할 수 있다.\n다만 미국 내 feedgas 수요는 서서히 늘어 Henry Hub에는 완만한 지지 요인이 된다.",
  "probability_delta": 0.0,
  "probability_score": 35.0,
  "scenario_group_id": 46,
  "scenario_id": 274,
  "status": "creating",
  "title": "반년 점진 증산, 대서양 LNG 완충 확대"
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

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 18 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=18, basecaseValue_present=18 | PASS |
| Step2 slot axis value 수 | `{"2|utilizationchangeamount|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 18 | Utilization 변화량 60%는 액화 Train별 가동률 override에 직접 연결되며, Golden Pass feedgas 반등과 선적 가능 물량 확대를 모델의 LiqUtilAdjustment 상향으로 반영하는 근거다. 기간 6개월과 점진 회복 패턴은 공통 시간 맥락으로 사용해 2026년 7월부터 12월까지 월별로 증산 폭을 선형 확대하되, 가동률 입력 상한은 1.0으로 제한했다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T1", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.03, "Period": 112, "Year": 2026}` | 0.6390547263681591 | 0.739054726368159 | 해당 월은 6개월 점진 증산의 첫 달이므로 동월 기준값 0.6390547263681591에 0.10의 이용률 상향분을 더해 최종 입력값을 산정했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T1", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.03, "Period": 113, "Year": 2026}` | 0.6900165837479271 | 0.8900165837479271 | 해당 월은 점진 증산의 두 번째 달이므로 동월 기준값 0.6900165837479271에 0.20의 이용률 상향분을 더해 최종 입력값을 산정했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T1", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.03, "Period": 114, "Year": 2026}` | 0.7818739635157543 | 1.0 | 해당 월은 점진 증산의 세 번째 달로 동월 기준값 0.7818739635157543에 0.30의 상향분을 적용하면 1.0을 초과하므로, 가동률 입력 상한 1.0으로 제한했다. |
| 4 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T1", "Life Cycle Category": "Under Construction", "Month": 10, "Nameplate Capacity (MTPA)": 6.03, "Period": 115, "Year": 2026}` | 0.8327197346600332 | 1.0 | 해당 월은 점진 증산의 네 번째 달로 동월 기준값 0.8327197346600332에 0.40의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다. |
| 5 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T1", "Life Cycle Category": "Under Construction", "Month": 11, "Nameplate Capacity (MTPA)": 6.03, "Period": 116, "Year": 2026}` | 0.8868720392916679 | 1.0 | 해당 월은 점진 증산의 다섯 번째 달로 동월 기준값 0.8868720392916679에 0.50의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다. |
| 6 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T1", "Life Cycle Category": "Under Construction", "Month": 12, "Nameplate Capacity (MTPA)": 6.03, "Period": 117, "Year": 2026}` | 0.944545903428692 | 1.0 | 해당 월은 6개월 점진 증산의 마지막 달로 동월 기준값 0.9445459034286919에 최종 0.60의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다. |
| 7 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T2", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.03, "Period": 112, "Year": 2026}` | 0.7766334991708126 | 0.8766334991708125 | 해당 월은 6개월 점진 증산의 첫 달이므로 동월 기준값 0.7766334991708126에 0.10의 이용률 상향분을 더해 최종 입력값을 산정했다. |
| 8 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T2", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.03, "Period": 113, "Year": 2026}` | 0.7766334991708126 | 0.9766334991708124 | 해당 월은 점진 증산의 두 번째 달이므로 동월 기준값 0.7766334991708126에 0.20의 이용률 상향분을 더해 최종 입력값을 산정했다. |
| 9 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T2", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.03, "Period": 114, "Year": 2026}` | 0.6390547263681591 | 0.9390547263681592 | 해당 월은 점진 증산의 세 번째 달이므로 동월 기준값 0.6390547263681591에 0.30의 이용률 상향분을 더해 최종 입력값을 산정했다. |
| 10 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T2", "Life Cycle Category": "Under Construction", "Month": 10, "Nameplate Capacity (MTPA)": 6.03, "Period": 115, "Year": 2026}` | 0.6900165837479271 | 1.0 | 해당 월은 점진 증산의 네 번째 달로 동월 기준값 0.6900165837479271에 0.40의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다. |
| 11 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T2", "Life Cycle Category": "Under Construction", "Month": 11, "Nameplate Capacity (MTPA)": 6.03, "Period": 116, "Year": 2026}` | 0.7818739635157543 | 1.0 | 해당 월은 점진 증산의 다섯 번째 달로 동월 기준값 0.7818739635157543에 0.50의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다. |
| 12 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T2", "Life Cycle Category": "Under Construction", "Month": 12, "Nameplate Capacity (MTPA)": 6.03, "Period": 117, "Year": 2026}` | 0.8327197346600332 | 1.0 | 해당 월은 6개월 점진 증산의 마지막 달로 동월 기준값 0.8327197346600332에 최종 0.60의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다. |
| 13 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T3", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.03, "Period": 112, "Year": 2026}` | 0 | 0.1 | 해당 월은 6개월 점진 증산의 첫 달이며 동월 기준값이 0이므로, 초기 안정화 단계에 해당하는 0.10의 이용률을 최종 입력값으로 설정했다. |
| 14 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T3", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.03, "Period": 113, "Year": 2026}` | 0 | 0.2 | 해당 월은 점진 증산의 두 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.20의 이용률을 최종 입력값으로 설정했다. |
| 15 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T3", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.03, "Period": 114, "Year": 2026}` | 0 | 0.3 | 해당 월은 점진 증산의 세 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.30의 이용률을 최종 입력값으로 설정했다. |
| 16 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T3", "Life Cycle Category": "Under Construction", "Month": 10, "Nameplate Capacity (MTPA)": 6.03, "Period": 115, "Year": 2026}` | 0 | 0.4 | 해당 월은 점진 증산의 네 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.40의 이용률을 최종 입력값으로 설정했다. |
| 17 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T3", "Life Cycle Category": "Under Construction", "Month": 11, "Nameplate Capacity (MTPA)": 6.03, "Period": 116, "Year": 2026}` | 0 | 0.5 | 해당 월은 점진 증산의 다섯 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.50의 이용률을 최종 입력값으로 설정했다. |
| 18 | `{"Country": "United States", "LNG Plant": "Golden Pass LNG", "LNG Plant Train": "Golden Pass LNG T3", "Life Cycle Category": "Under Construction", "Month": 12, "Nameplate Capacity (MTPA)": 6.03, "Period": 117, "Year": 2026}` | 0 | 0.6 | 해당 월은 6개월 점진 증산의 마지막 달이며 동월 기준값이 0이므로, 시나리오의 최종 60% 이용률 상승 수준에 맞춰 0.60을 최종 입력값으로 설정했다. |

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
  "mi_event_id": 1326,
  "model_param_proposal_id": 90,
  "proposal_completed_dtm": "2026-07-07 23:32:44.054043",
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
      "rationale": "Utilization 변화량 60%는 액화 Train별 가동률 override에 직접 연결되며, Golden Pass feedgas 반등과 선적 가능 물량 확대를 모델의 LiqUtilAdjustment 상향으로 반영하는 근거다. 기간 6개월과 점진 회복 패턴은 공통 시간 맥락으로 사용해 2026년 7월부터 12월까지 월별로 증산 폭을 선형 확대하되, 가동률 입력 상한은 1.0으로 제한했다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T1",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.6390547263681591,
          "proposedValue": 0.739054726368159,
          "rationale": "해당 월은 6개월 점진 증산의 첫 달이므로 동월 기준값 0.6390547263681591에 0.10의 이용률 상향분을 더해 최종 입력값을 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T1",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.6900165837479271,
          "proposedValue": 0.8900165837479271,
          "rationale": "해당 월은 점진 증산의 두 번째 달이므로 동월 기준값 0.6900165837479271에 0.20의 이용률 상향분을 더해 최종 입력값을 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T1",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.7818739635157543,
          "proposedValue": 1.0,
          "rationale": "해당 월은 점진 증산의 세 번째 달로 동월 기준값 0.7818739635157543에 0.30의 상향분을 적용하면 1.0을 초과하므로, 가동률 입력 상한 1.0으로 제한했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T1",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.8327197346600332,
          "proposedValue": 1.0,
          "rationale": "해당 월은 점진 증산의 네 번째 달로 동월 기준값 0.8327197346600332에 0.40의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T1",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.8868720392916679,
          "proposedValue": 1.0,
          "rationale": "해당 월은 점진 증산의 다섯 번째 달로 동월 기준값 0.8868720392916679에 0.50의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T1",
          "Life Cycle Category": "Under Construction",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.944545903428692,
          "proposedValue": 1.0,
          "rationale": "해당 월은 6개월 점진 증산의 마지막 달로 동월 기준값 0.9445459034286919에 최종 0.60의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T2",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.7766334991708126,
          "proposedValue": 0.8766334991708125,
          "rationale": "해당 월은 6개월 점진 증산의 첫 달이므로 동월 기준값 0.7766334991708126에 0.10의 이용률 상향분을 더해 최종 입력값을 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T2",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.7766334991708126,
          "proposedValue": 0.9766334991708124,
          "rationale": "해당 월은 점진 증산의 두 번째 달이므로 동월 기준값 0.7766334991708126에 0.20의 이용률 상향분을 더해 최종 입력값을 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T2",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.6390547263681591,
          "proposedValue": 0.9390547263681592,
          "rationale": "해당 월은 점진 증산의 세 번째 달이므로 동월 기준값 0.6390547263681591에 0.30의 이용률 상향분을 더해 최종 입력값을 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T2",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.6900165837479271,
          "proposedValue": 1.0,
          "rationale": "해당 월은 점진 증산의 네 번째 달로 동월 기준값 0.6900165837479271에 0.40의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T2",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.7818739635157543,
          "proposedValue": 1.0,
          "rationale": "해당 월은 점진 증산의 다섯 번째 달로 동월 기준값 0.7818739635157543에 0.50의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T2",
          "Life Cycle Category": "Under Construction",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0.8327197346600332,
          "proposedValue": 1.0,
          "rationale": "해당 월은 6개월 점진 증산의 마지막 달로 동월 기준값 0.8327197346600332에 최종 0.60의 상향분을 적용하면 1.0을 초과하므로, 최종 입력값은 상한 1.0으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.1,
          "rationale": "해당 월은 6개월 점진 증산의 첫 달이며 동월 기준값이 0이므로, 초기 안정화 단계에 해당하는 0.10의 이용률을 최종 입력값으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T3",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.2,
          "rationale": "해당 월은 점진 증산의 두 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.20의 이용률을 최종 입력값으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T3",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.3,
          "rationale": "해당 월은 점진 증산의 세 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.30의 이용률을 최종 입력값으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T3",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.4,
          "rationale": "해당 월은 점진 증산의 네 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.40의 이용률을 최종 입력값으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T3",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.5,
          "rationale": "해당 월은 점진 증산의 다섯 번째 달이며 동월 기준값이 0이므로, 선형 램프업에 따라 0.50의 이용률을 최종 입력값으로 설정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Golden Pass LNG",
          "LNG Plant Train": "Golden Pass LNG T3",
          "Life Cycle Category": "Under Construction",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.03,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0.6,
          "rationale": "해당 월은 6개월 점진 증산의 마지막 달이며 동월 기준값이 0이므로, 시나리오의 최종 60% 이용률 상승 수준에 맞춰 0.60을 최종 입력값으로 설정했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 46,
  "scenario_id": 274,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:02.635 | 2.635 | 2558 | 77 | 2635 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:34.373 | 34.373 | 11679 | 3444 | 15123 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:58.478 | 118.478 | 11350 | 5861 | 17211 |

#### event_type_l2_id=4 파이프라인 Utilization 변동

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "LNG 전환(타 공급국 액화 가동률 상향) : PNG 대체가 LNG 전환으로 설명될 때 시장연결 공급국의 가용 액화설비에 대체 물량을 배분",
      "dimension": "alt_supply_availability (대체 공급원 가능성 (타 노선·LNG 전환))",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "타 노선 송출 증대 : 차질 노선과 연결 가능한 대체 파이프라인의 잔여 송출능력에 부족분을 차등 배분",
      "dimension": "alt_supply_availability (대체 공급원 가능성 (타 노선·LNG 전환))",
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
      "comment": "시간축",
      "dimension": "period (기간)",
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
      "comment": "단발=한시/구조적=영구 — 변경 범위",
      "dimension": "structural_change_yn (구조적 변동 여부)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "노선 capacity(Bcm/y) 조정 : 영향받은 파이프라인 노선의 송출 capacity를 조정하고, 기간·회복패턴에 따라 적용 월을 분배",
      "dimension": "utilization_change_amount (Utilization 변화 폭 (송출용량 대비))",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "계약기반 PNG 물량 변동(Nord Stream 재가동/Pipeline Disruption) : PNG 계약 물량 자체는 Trade 계열 미대상 파라미터이므로 직접 조정하지 않고, 실제 송출 가능량 변화가 있으면 PipelineAdjustment로 별도 반영",
      "dimension": "utilization_change_amount (Utilization 변화 폭 (송출용량 대비))",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [285, 286]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=285 [model_parameter_agent_test] 단기 송출 증가와 대체 공급 충분

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:47.237 (167.237s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 39 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=5, basecaseValue_present=5 | PASS |
| Step2 slot axis value 수 | `{"4|altsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 5 | 대체 공급원 가능성 100%는 파이프라인 물량 변화가 LNG 전환으로 흡수될 수 있는 경우 액화설비 가동률 조정과 직접 연결되는 dimension이다. 다만 이번 시나리오는 TurkStream 송출이 단기 소폭 증가하고 대체 공급도 충분해 가격 영향이 중립으로 제시되며, 기간도 1개월 이하·단발적·급격 회복으로 한정되어 추가적인 액화 가동률 상향 배분은 적용하지 않고 선정된 단기 슬롯의 기준 가동률을 유지한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 7.9, "Period": 110, "Year": 2026}` | 0.19018404907975456 | 0.19018404907975456 | 해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. TurkStream 송출 증가가 LNG 대체수요를 추가로 확대하는 사건이 아니고 시나리오 영향도 중립이므로, 기준 가동률 0.19018404907975456을 최종 입력값으로 유지한다. |
| 2 | `{"Country": "Algeria", "LNG Plant": "Arzew GL2Z", "LNG Plant Train": "Arzew GL2Z T1-T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 8.4, "Period": 110, "Year": 2026}` | 0.19018404907975456 | 0.19018404907975456 | 해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. 대체 공급 여력이 충분하더라도 이번 사건은 유럽 LNG 조달 압력을 완화하는 방향이며 추가 LNG 전환 수요가 명확하지 않으므로, 기준 가동률 0.19018404907975456을 그대로 적용한다. |
| 3 | `{"Country": "Algeria", "LNG Plant": "Arzew GL3Z (Gassi Touil)", "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.7, "Period": 110, "Year": 2026}` | 1.0000000000000002 | 1.0000000000000002 | 해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이며 기준값이 이미 정상 가동 수준이다. 시나리오가 중립적이고 단발적이므로 추가 상향 없이 기준 가동률 1.0000000000000002를 유지한다. |
| 4 | `{"Country": "Algeria", "LNG Plant": "Skikda GL1K", "LNG Plant Train": "Skikda GL1K T1 (rebuild)", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.5, "Period": 110, "Year": 2026}` | 0.7999999999999999 | 0.7999999999999999 | 해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. 단기 송출 증가와 충분한 대체 공급 조건은 액화설비 가동률을 추가로 끌어올릴 필요가 낮다는 의미로 해석되므로, 기준 가동률 0.7999999999999999를 최종 입력값으로 유지한다. |
| 5 | `{"Country": "Norway", "LNG Plant": "Snohvit LNG", "LNG Plant Train": "Snohvit LNG T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 4.3, "Period": 110, "Year": 2026}` | 1.0232558139534886 | 1.0232558139534886 | 해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. 이벤트가 유럽 파이프라인 공급 가용성 증가로 LNG 대체수요를 완화하는 성격이고 시나리오 충격도 작으므로, 기준 가동률 1.0232558139534886을 조정 없이 유지한다. |

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
  "mi_event_id": 1121,
  "model_param_proposal_id": 92,
  "proposal_completed_dtm": "2026-07-07 23:33:58.199353",
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
      "rationale": "대체 공급원 가능성 100%는 파이프라인 물량 변화가 LNG 전환으로 흡수될 수 있는 경우 액화설비 가동률 조정과 직접 연결되는 dimension이다. 다만 이번 시나리오는 TurkStream 송출이 단기 소폭 증가하고 대체 공급도 충분해 가격 영향이 중립으로 제시되며, 기간도 1개월 이하·단발적·급격 회복으로 한정되어 추가적인 액화 가동률 상향 배분은 적용하지 않고 선정된 단기 슬롯의 기준 가동률을 유지한다.",
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
          "rationale": "해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. TurkStream 송출 증가가 LNG 대체수요를 추가로 확대하는 사건이 아니고 시나리오 영향도 중립이므로, 기준 가동률 0.19018404907975456을 최종 입력값으로 유지한다."
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
          "rationale": "해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. 대체 공급 여력이 충분하더라도 이번 사건은 유럽 LNG 조달 압력을 완화하는 방향이며 추가 LNG 전환 수요가 명확하지 않으므로, 기준 가동률 0.19018404907975456을 그대로 적용한다."
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
          "rationale": "해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이며 기준값이 이미 정상 가동 수준이다. 시나리오가 중립적이고 단발적이므로 추가 상향 없이 기준 가동률 1.0000000000000002를 유지한다."
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
          "rationale": "해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. 단기 송출 증가와 충분한 대체 공급 조건은 액화설비 가동률을 추가로 끌어올릴 필요가 낮다는 의미로 해석되므로, 기준 가동률 0.7999999999999999를 최종 입력값으로 유지한다."
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
          "rationale": "해당 좌표는 2026년 5월 단기 적용 대상에 포함된 액화설비 슬롯이다. 이벤트가 유럽 파이프라인 공급 가용성 증가로 LNG 대체수요를 완화하는 성격이고 시나리오 충격도 작으므로, 기준 가동률 1.0232558139534886을 조정 없이 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.495 | 3.495 | 2430 | 82 | 2512 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:42.761 | 102.761 | 11800 | 8988 | 20788 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:47.268 | 47.268 | 16651 | 3021 | 19672 |

##### scenario_id=286 [model_parameter_agent_test] 장기 송출 차질과 대체 공급 부족

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 04:44.528 (284.528s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=1, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 96 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=39, basecaseValue_present=39 | PASS |
| Step2 slot axis value 수 | `{"4|altsupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 39 | 대체 공급원 가능성 25%는 PNG 차질을 LNG 전환으로 일부만 보완할 수 있음을 뜻하며, LiqUtilAdjustment는 선택된 액화설비의 월별 가동률을 직접 조정하는 입력값이므로 해당 dimension과 직접 연결됩니다. 기간 1년, 급격한 발생, 점진적 회복이라는 공통 맥락을 반영해 선택 기간 내 가동 여력이 있는 슬롯은 1.0까지의 잔여 여력 중 25%만 보수적으로 상향하고, 이미 기준 가동률이 높은 슬롯은 추가 상향 없이 기준 유지로 둡니다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.1, "Period": 103, "Year": 2026}` | 0.9887457459032464 | 0.9915593094274348 | 해당 월 기준값 0.9887457459032463이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9887457459032463 + 25% × (1.0 - 0.9887457459032463) = 0.9915593094274347로 산정했다. |
| 2 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.1, "Period": 104, "Year": 2026}` | 0.9964982077836354 | 0.9973736558377266 | 해당 월 기준값 0.9964982077836354가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9964982077836354 + 25% × (1.0 - 0.9964982077836354) = 0.9973736558377266로 산정했다. |
| 3 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.099999, "Period": 103, "Year": 2026}` | 0.9867723949850288 | 0.9900792962387716 | 해당 월 기준값 0.9867723949850288이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9867723949850288 + 25% × (1.0 - 0.9867723949850288) = 0.9900792962387716로 산정했다. |
| 4 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.099999, "Period": 104, "Year": 2026}` | 0.9945093844066656 | 0.9958820383049992 | 해당 월 기준값 0.9945093844066657이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9945093844066657 + 25% × (1.0 - 0.9945093844066657) = 0.9958820383049993로 산정했다. |
| 5 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.099999, "Period": 103, "Year": 2026}` | 0.984798850195059 | 0.9885991376462944 | 해당 월 기준값 0.984798850195059가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.984798850195059 + 25% × (1.0 - 0.984798850195059) = 0.9885991376462943로 산정했다. |
| 6 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.099999, "Period": 104, "Year": 2026}` | 0.9925203656378526 | 0.9943902742283895 | 해당 월 기준값 0.9925203656378526이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9925203656378526 + 25% × (1.0 - 0.9925203656378526) = 0.9943902742283895로 산정했다. |
| 7 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.099999, "Period": 105, "Year": 2026}` | 0.9999686490178076 | 0.9999764867633556 | 해당 월 기준값 0.9999686490178075가 1.0에 매우 근접하지만 미만이므로 제한적인 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9999686490178075 + 25% × (1.0 - 0.9999686490178075) = 0.9999764867633556로 산정했다. |
| 8 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 10, "Period": 103, "Year": 2026}` | 0.978 | 0.9835 | 해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다. |
| 9 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 10, "Period": 104, "Year": 2026}` | 0.978 | 0.9835 | 해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다. |
| 10 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 10, "Period": 105, "Year": 2026}` | 0.978 | 0.9835 | 해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다. |
| 11 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 10, "Period": 106, "Year": 2026}` | 0.978 | 0.9835 | 해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다. |
| 12 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 10, "Period": 107, "Year": 2026}` | 0.978 | 0.9835 | 해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다. |
| 13 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 10, "Period": 108, "Year": 2026}` | 0.978 | 0.9835 | 해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다. |
| 14 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 10, "Period": 109, "Year": 2027}` | 0.9532752352743732 | 0.96495642645578 | 해당 월 기준값 0.9532752352743733이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9532752352743733 + 25% × (1.0 - 0.9532752352743733) = 0.96495642645578로 산정했다. |
| 15 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 10, "Period": 110, "Year": 2027}` | 0.9586746813514612 | 0.969006011013596 | 해당 월 기준값 0.9586746813514613이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9586746813514613 + 25% × (1.0 - 0.9586746813514613) = 0.969006011013596로 산정했다. |
| 16 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 10, "Period": 111, "Year": 2027}` | 0.965192084044823 | 0.9738940630336173 | 해당 월 기준값 0.965192084044823이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.965192084044823 + 25% × (1.0 - 0.965192084044823) = 0.9738940630336173로 산정했다. |
| 17 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 10, "Period": 112, "Year": 2027}` | 0.9663020188579584 | 0.9747265141434688 | 해당 월 기준값 0.9663020188579585가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9663020188579585 + 25% × (1.0 - 0.9663020188579585) = 0.9747265141434688로 산정했다. |
| 18 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 10, "Period": 113, "Year": 2027}` | 0.9728194215513204 | 0.9796145661634904 | 해당 월 기준값 0.9728194215513204가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9728194215513204 + 25% × (1.0 - 0.9728194215513204) = 0.9796145661634903로 산정했다. |
| 19 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 10, "Period": 114, "Year": 2027}` | 0.9789641720392572 | 0.9842231290294428 | 해당 월 기준값 0.9789641720392571이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9789641720392571 + 25% × (1.0 - 0.9789641720392571) = 0.9842231290294428로 산정했다. |
| 20 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 10, "Period": 109, "Year": 2027}` | 0.9532752352743732 | 0.96495642645578 | 해당 월 기준값 0.9532752352743733이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9532752352743733 + 25% × (1.0 - 0.9532752352743733) = 0.96495642645578로 산정했다. |
| 21 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 10, "Period": 110, "Year": 2027}` | 0.9586746813514612 | 0.969006011013596 | 해당 월 기준값 0.9586746813514613이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9586746813514613 + 25% × (1.0 - 0.9586746813514613) = 0.969006011013596로 산정했다. |
| 22 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 10, "Period": 111, "Year": 2027}` | 0.965192084044823 | 0.9738940630336173 | 해당 월 기준값 0.965192084044823이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.965192084044823 + 25% × (1.0 - 0.965192084044823) = 0.9738940630336173로 산정했다. |
| 23 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 10, "Period": 112, "Year": 2027}` | 0.9663020188579584 | 0.9747265141434688 | 해당 월 기준값 0.9663020188579585가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9663020188579585 + 25% × (1.0 - 0.9663020188579585) = 0.9747265141434688로 산정했다. |
| 24 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 10, "Period": 113, "Year": 2027}` | 0.9728194215513204 | 0.9796145661634904 | 해당 월 기준값 0.9728194215513204가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9728194215513204 + 25% × (1.0 - 0.9728194215513204) = 0.9796145661634903로 산정했다. |
| 25 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 10, "Period": 114, "Year": 2027}` | 0.9789641720392572 | 0.9842231290294428 | 해당 월 기준값 0.9789641720392571이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9789641720392571 + 25% × (1.0 - 0.9789641720392571) = 0.9842231290294428로 산정했다. |
| 26 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5, "Period": 103, "Year": 2026}` | 0.9886406459054536 | 0.99148048442909 | 해당 월 기준값 0.9886406459054535가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9886406459054535 + 25% × (1.0 - 0.9886406459054535) = 0.99148048442909로 산정했다. |
| 27 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5, "Period": 104, "Year": 2026}` | 0.9963922837279592 | 0.9972942127959696 | 해당 월 기준값 0.9963922837279593이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9963922837279593 + 25% × (1.0 - 0.9963922837279593) = 0.9972942127959695로 산정했다. |
| 28 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 5, "Period": 109, "Year": 2027}` | 0.9017983725695572 | 0.926348779427168 | 해당 월 기준값 0.9017983725695572가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9017983725695572 + 25% × (1.0 - 0.9017983725695572) = 0.9263487794271679로 산정했다. |
| 29 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 5, "Period": 110, "Year": 2027}` | 0.9069062485584825 | 0.930179686418862 | 해당 월 기준값 0.9069062485584825가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9069062485584825 + 25% × (1.0 - 0.9069062485584825) = 0.9301796864188619로 산정했다. |
| 30 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 5, "Period": 111, "Year": 2027}` | 0.9130717115064028 | 0.934803783629802 | 해당 월 기준값 0.9130717115064027이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9130717115064027 + 25% × (1.0 - 0.9130717115064027) = 0.934803783629802로 산정했다. |
| 31 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 5, "Period": 112, "Year": 2027}` | 0.9141217098396288 | 0.9355912823797216 | 해당 월 기준값 0.9141217098396288이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9141217098396288 + 25% × (1.0 - 0.9141217098396288) = 0.9355912823797216로 산정했다. |
| 32 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 5, "Period": 113, "Year": 2027}` | 0.9202871727875492 | 0.940215379590662 | 해당 월 기준값 0.9202871727875491이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9202871727875491 + 25% × (1.0 - 0.9202871727875491) = 0.9402153795906619로 산정했다. |
| 33 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 5, "Period": 114, "Year": 2027}` | 0.9261001067491372 | 0.944575080061853 | 해당 월 기준값 0.9261001067491373이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9261001067491373 + 25% × (1.0 - 0.9261001067491373) = 0.944575080061853로 산정했다. |
| 34 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 5, "Period": 109, "Year": 2027}` | 0.9532752352743732 | 0.96495642645578 | 해당 월 기준값 0.9532752352743733이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9532752352743733 + 25% × (1.0 - 0.9532752352743733) = 0.96495642645578로 산정했다. |
| 35 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 5, "Period": 110, "Year": 2027}` | 0.9586746813514612 | 0.969006011013596 | 해당 월 기준값 0.9586746813514613이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9586746813514613 + 25% × (1.0 - 0.9586746813514613) = 0.969006011013596로 산정했다. |
| 36 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 5, "Period": 111, "Year": 2027}` | 0.965192084044823 | 0.9738940630336173 | 해당 월 기준값 0.965192084044823이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.965192084044823 + 25% × (1.0 - 0.965192084044823) = 0.9738940630336173로 산정했다. |
| 37 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 5, "Period": 112, "Year": 2027}` | 0.9663020188579584 | 0.9747265141434688 | 해당 월 기준값 0.9663020188579585가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9663020188579585 + 25% × (1.0 - 0.9663020188579585) = 0.9747265141434688로 산정했다. |
| 38 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 5, "Period": 113, "Year": 2027}` | 0.9728194215513204 | 0.9796145661634904 | 해당 월 기준값 0.9728194215513204가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9728194215513204 + 25% × (1.0 - 0.9728194215513204) = 0.9796145661634903로 산정했다. |
| 39 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 5, "Period": 114, "Year": 2027}` | 0.9789641720392572 | 0.9842231290294428 | 해당 월 기준값 0.9789641720392571이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9789641720392571 + 25% × (1.0 - 0.9789641720392571) = 0.9842231290294428로 산정했다. |

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
  "mi_event_id": 1121,
  "model_param_proposal_id": 97,
  "proposal_completed_dtm": "2026-07-07 23:37:00.309413",
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
      "rationale": "대체 공급원 가능성 25%는 PNG 차질을 LNG 전환으로 일부만 보완할 수 있음을 뜻하며, LiqUtilAdjustment는 선택된 액화설비의 월별 가동률을 직접 조정하는 입력값이므로 해당 dimension과 직접 연결됩니다. 기간 1년, 급격한 발생, 점진적 회복이라는 공통 맥락을 반영해 선택 기간 내 가동 여력이 있는 슬롯은 1.0까지의 잔여 여력 중 25%만 보수적으로 상향하고, 이미 기준 가동률이 높은 슬롯은 추가 상향 없이 기준 유지로 둡니다.",
      "values": [
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.9887457459032464,
          "proposedValue": 0.9915593094274348,
          "rationale": "해당 월 기준값 0.9887457459032463이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9887457459032463 + 25% × (1.0 - 0.9887457459032463) = 0.9915593094274347로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.9964982077836354,
          "proposedValue": 0.9973736558377266,
          "rationale": "해당 월 기준값 0.9964982077836354가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9964982077836354 + 25% × (1.0 - 0.9964982077836354) = 0.9973736558377266로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.9867723949850288,
          "proposedValue": 0.9900792962387716,
          "rationale": "해당 월 기준값 0.9867723949850288이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9867723949850288 + 25% × (1.0 - 0.9867723949850288) = 0.9900792962387716로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.9945093844066656,
          "proposedValue": 0.9958820383049992,
          "rationale": "해당 월 기준값 0.9945093844066657이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9945093844066657 + 25% × (1.0 - 0.9945093844066657) = 0.9958820383049993로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.984798850195059,
          "proposedValue": 0.9885991376462944,
          "rationale": "해당 월 기준값 0.984798850195059가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.984798850195059 + 25% × (1.0 - 0.984798850195059) = 0.9885991376462943로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.9925203656378526,
          "proposedValue": 0.9943902742283895,
          "rationale": "해당 월 기준값 0.9925203656378526이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9925203656378526 + 25% × (1.0 - 0.9925203656378526) = 0.9943902742283895로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 0.9999686490178076,
          "proposedValue": 0.9999764867633556,
          "rationale": "해당 월 기준값 0.9999686490178075가 1.0에 매우 근접하지만 미만이므로 제한적인 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9999686490178075 + 25% × (1.0 - 0.9999686490178075) = 0.9999764867633556로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.9835,
          "rationale": "해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.9835,
          "rationale": "해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 105,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.9835,
          "rationale": "해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 106,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.9835,
          "rationale": "해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 107,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.9835,
          "rationale": "해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 108,
          "Year": 2026,
          "basecaseValue": 0.978,
          "proposedValue": 0.9835,
          "rationale": "해당 월 기준값 0.978이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.978 + 25% × (1.0 - 0.978) = 0.9835로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 109,
          "Year": 2027,
          "basecaseValue": 0.9532752352743732,
          "proposedValue": 0.96495642645578,
          "rationale": "해당 월 기준값 0.9532752352743733이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9532752352743733 + 25% × (1.0 - 0.9532752352743733) = 0.96495642645578로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 110,
          "Year": 2027,
          "basecaseValue": 0.9586746813514612,
          "proposedValue": 0.969006011013596,
          "rationale": "해당 월 기준값 0.9586746813514613이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9586746813514613 + 25% × (1.0 - 0.9586746813514613) = 0.969006011013596로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 111,
          "Year": 2027,
          "basecaseValue": 0.965192084044823,
          "proposedValue": 0.9738940630336173,
          "rationale": "해당 월 기준값 0.965192084044823이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.965192084044823 + 25% × (1.0 - 0.965192084044823) = 0.9738940630336173로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 112,
          "Year": 2027,
          "basecaseValue": 0.9663020188579584,
          "proposedValue": 0.9747265141434688,
          "rationale": "해당 월 기준값 0.9663020188579585가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9663020188579585 + 25% × (1.0 - 0.9663020188579585) = 0.9747265141434688로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 113,
          "Year": 2027,
          "basecaseValue": 0.9728194215513204,
          "proposedValue": 0.9796145661634904,
          "rationale": "해당 월 기준값 0.9728194215513204가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9728194215513204 + 25% × (1.0 - 0.9728194215513204) = 0.9796145661634903로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T1-T2",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 114,
          "Year": 2027,
          "basecaseValue": 0.9789641720392572,
          "proposedValue": 0.9842231290294428,
          "rationale": "해당 월 기준값 0.9789641720392571이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9789641720392571 + 25% × (1.0 - 0.9789641720392571) = 0.9842231290294428로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 109,
          "Year": 2027,
          "basecaseValue": 0.9532752352743732,
          "proposedValue": 0.96495642645578,
          "rationale": "해당 월 기준값 0.9532752352743733이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9532752352743733 + 25% × (1.0 - 0.9532752352743733) = 0.96495642645578로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 110,
          "Year": 2027,
          "basecaseValue": 0.9586746813514612,
          "proposedValue": 0.969006011013596,
          "rationale": "해당 월 기준값 0.9586746813514613이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9586746813514613 + 25% × (1.0 - 0.9586746813514613) = 0.969006011013596로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 111,
          "Year": 2027,
          "basecaseValue": 0.965192084044823,
          "proposedValue": 0.9738940630336173,
          "rationale": "해당 월 기준값 0.965192084044823이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.965192084044823 + 25% × (1.0 - 0.965192084044823) = 0.9738940630336173로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 112,
          "Year": 2027,
          "basecaseValue": 0.9663020188579584,
          "proposedValue": 0.9747265141434688,
          "rationale": "해당 월 기준값 0.9663020188579585가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9663020188579585 + 25% × (1.0 - 0.9663020188579585) = 0.9747265141434688로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 113,
          "Year": 2027,
          "basecaseValue": 0.9728194215513204,
          "proposedValue": 0.9796145661634904,
          "rationale": "해당 월 기준값 0.9728194215513204가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9728194215513204 + 25% × (1.0 - 0.9728194215513204) = 0.9796145661634903로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 114,
          "Year": 2027,
          "basecaseValue": 0.9789641720392572,
          "proposedValue": 0.9842231290294428,
          "rationale": "해당 월 기준값 0.9789641720392571이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9789641720392571 + 25% × (1.0 - 0.9789641720392571) = 0.9842231290294428로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 103,
          "Year": 2026,
          "basecaseValue": 0.9886406459054536,
          "proposedValue": 0.99148048442909,
          "rationale": "해당 월 기준값 0.9886406459054535가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9886406459054535 + 25% × (1.0 - 0.9886406459054535) = 0.99148048442909로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 104,
          "Year": 2026,
          "basecaseValue": 0.9963922837279592,
          "proposedValue": 0.9972942127959696,
          "rationale": "해당 월 기준값 0.9963922837279593이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9963922837279593 + 25% × (1.0 - 0.9963922837279593) = 0.9972942127959695로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 109,
          "Year": 2027,
          "basecaseValue": 0.9017983725695572,
          "proposedValue": 0.926348779427168,
          "rationale": "해당 월 기준값 0.9017983725695572가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9017983725695572 + 25% × (1.0 - 0.9017983725695572) = 0.9263487794271679로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 110,
          "Year": 2027,
          "basecaseValue": 0.9069062485584825,
          "proposedValue": 0.930179686418862,
          "rationale": "해당 월 기준값 0.9069062485584825가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9069062485584825 + 25% × (1.0 - 0.9069062485584825) = 0.9301796864188619로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 111,
          "Year": 2027,
          "basecaseValue": 0.9130717115064028,
          "proposedValue": 0.934803783629802,
          "rationale": "해당 월 기준값 0.9130717115064027이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9130717115064027 + 25% × (1.0 - 0.9130717115064027) = 0.934803783629802로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 112,
          "Year": 2027,
          "basecaseValue": 0.9141217098396288,
          "proposedValue": 0.9355912823797216,
          "rationale": "해당 월 기준값 0.9141217098396288이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9141217098396288 + 25% × (1.0 - 0.9141217098396288) = 0.9355912823797216로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 113,
          "Year": 2027,
          "basecaseValue": 0.9202871727875492,
          "proposedValue": 0.940215379590662,
          "rationale": "해당 월 기준값 0.9202871727875491이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9202871727875491 + 25% × (1.0 - 0.9202871727875491) = 0.9402153795906619로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 114,
          "Year": 2027,
          "basecaseValue": 0.9261001067491372,
          "proposedValue": 0.944575080061853,
          "rationale": "해당 월 기준값 0.9261001067491373이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9261001067491373 + 25% × (1.0 - 0.9261001067491373) = 0.944575080061853로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 109,
          "Year": 2027,
          "basecaseValue": 0.9532752352743732,
          "proposedValue": 0.96495642645578,
          "rationale": "해당 월 기준값 0.9532752352743733이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9532752352743733 + 25% × (1.0 - 0.9532752352743733) = 0.96495642645578로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 110,
          "Year": 2027,
          "basecaseValue": 0.9586746813514612,
          "proposedValue": 0.969006011013596,
          "rationale": "해당 월 기준값 0.9586746813514613이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9586746813514613 + 25% × (1.0 - 0.9586746813514613) = 0.969006011013596로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 111,
          "Year": 2027,
          "basecaseValue": 0.965192084044823,
          "proposedValue": 0.9738940630336173,
          "rationale": "해당 월 기준값 0.965192084044823이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.965192084044823 + 25% × (1.0 - 0.965192084044823) = 0.9738940630336173로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 112,
          "Year": 2027,
          "basecaseValue": 0.9663020188579584,
          "proposedValue": 0.9747265141434688,
          "rationale": "해당 월 기준값 0.9663020188579585가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9663020188579585 + 25% × (1.0 - 0.9663020188579585) = 0.9747265141434688로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 113,
          "Year": 2027,
          "basecaseValue": 0.9728194215513204,
          "proposedValue": 0.9796145661634904,
          "rationale": "해당 월 기준값 0.9728194215513204가 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9728194215513204 + 25% × (1.0 - 0.9728194215513204) = 0.9796145661634903로 산정했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 114,
          "Year": 2027,
          "basecaseValue": 0.9789641720392572,
          "proposedValue": 0.9842231290294428,
          "rationale": "해당 월 기준값 0.9789641720392571이 1.0 미만이라 가동 여력이 있는 슬롯으로 보았다. 대체 LNG 가용성 25%를 1.0까지의 잔여 여력에만 적용해 0.9789641720392571 + 25% × (1.0 - 0.9789641720392571) = 0.9842231290294428로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.545 | 4.545 | 2434 | 87 | 2521 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:58.930 | 118.930 | 11801 | 14821 | 26622 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 02:15.468 | 135.468 | 20542 | 11455 | 31997 |

#### event_type_l2_id=11 자연재해

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "생산 시설 피해 시 : 생산시설 피해면 해당 국가·basin의 SupplyDisruption을 선택하고, 피해 강도는 별도 강도 dimension으로 산정",
      "dimension": "affected_facility_type (영향 시설 유형)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "수출(액화) 시설 피해 시 : 액화설비의 장기·영구 손상, 설비 폐쇄, 복구 지연 등으로 생산 가능량 자체를 낮춰야 하면 LiqProdAdjustment 선택. 단기 이용률 조정보다 구조적 생산량 감소가 명확한 경우에 사용",
      "dimension": "affected_facility_type (영향 시설 유형)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "수입(재기화) 시설 피해 시 : RegasAdjustment는 현재 수급모델 파라미터 제안 대상에서 제외",
      "dimension": "affected_facility_type (영향 시설 유형)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "美 액화시설 허리케인 — [1-4] 강도 : 미국 Gulf Coast 액화시설이 허리케인 영향권이고 강도 단계로 차질을 설명할 수 있으면 HurricaneIntensity 선택. 실제 설비별 outage 비율이 명확하면 LiqUtilAdjustment/LiqProdAdjustment로 보완 판단",
      "dimension": "affected_facility_type (영향 시설 유형)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "수출(액화) 시설 피해 시 : 기존 액화 Plant/Train의 단기·부분 가동 차질이면 LiqUtilAdjustment 선택. 설비 용량은 유지되지만 정전·침수·정비·운영 제약으로 이용률이 낮아지는 경우에 사용",
      "dimension": "affected_facility_type (영향 시설 유형)",
      "mapping_method": "routing",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "타 공급국 상향으로 상쇄 : 피해로 감소한 LNG 공급량 중 대체 가능한 물량만 시장연결 공급국의 가용 액화설비에 배분",
      "dimension": "alt_lng_supply_availability (대체 LNG 공급 가능성)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "시간축",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "시설 가동률 감소율로 변환 — 강도가 값 크기 결정 : routing으로 선택된 시설·파라미터의 감소율 또는 감소량을 결정하며, 강도 단계에 따라 조정폭을 차등 적용",
      "dimension": "supply_disruption_intensity (공급 차질 강도)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "Ref. 공급 차질 패턴 — 시계열 형태",
      "dimension": "supply_disruption_pattern (공급 차질 - 발생/회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [279, 280]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=279 [model_parameter_agent_test] 생산 시설 피해

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 03:31.281 (211.281s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 27 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=27, basecaseValue_present=27 | PASS |
| Step2 slot axis value 수 | `{"parameter|11|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 27 | 영향 시설 유형이 생산 시설이고, 설명상 액화 생산 설비의 단기·부분 가동 차질이므로 Train/month 액화 가동률을 조정하는 LiqUtilAdjustment가 적합하다. 대체 LNG 공급 가능성 50%는 피해로 인한 공급 감소가 절반만 완화되는 조건으로 반영하고, 3개월·급손상-단기수리 패턴에 맞춰 초기 하향 폭을 크게 두되 월별로 회복되는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 112, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 2026년 7월은 3개월 차질의 첫 달로 급손상 영향이 가장 크게 반영되는 구간이다. 기준값 1.0384615384615388에 높은 생산 차질을 적용하되 대체 LNG 공급 50%를 감안해 순 25% 하향하여 0.7788461538461541로 산정했다. |
| 2 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 113, "Year": 2026}` | 1.0384615384615388 | 0.882692307692308 | 2026년 8월은 단기수리 진행으로 첫 달보다 차질이 완화되는 구간이다. 기준값 1.0384615384615388에 순 15% 하향을 적용해 0.882692307692308로 산정했다. |
| 3 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 114, "Year": 2026}` | 1.0384615384615388 | 0.9865384615384618 | 2026년 9월은 3개월 차질의 마지막 달로 수리 후 회복이 상당 부분 진행되는 구간이다. 기준값 1.0384615384615388에 잔여 차질 순 5% 하향을 적용해 0.9865384615384618로 산정했다. |
| 4 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 112, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 2026년 7월은 급손상 발생 직후의 첫 달로 동일 설비군 내 직접 생산 차질을 반영했다. 기준값 1.0384615384615388에 순 25% 하향을 적용해 0.7788461538461541로 산정했다. |
| 5 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 113, "Year": 2026}` | 1.0384615384615388 | 0.882692307692308 | 2026년 8월은 단기수리로 차질이 일부 완화되는 중간 월이다. 기준값 1.0384615384615388에 순 15% 하향을 적용해 0.882692307692308로 산정했다. |
| 6 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 114, "Year": 2026}` | 1.0384615384615388 | 0.9865384615384618 | 2026년 9월은 수리 완료에 가까운 회복 월로 잔여 생산 제약만 반영했다. 기준값 1.0384615384615388에 순 5% 하향을 적용해 0.9865384615384618로 산정했다. |
| 7 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 112, "Year": 2026}` | 1.0384615384615388 | 0.7788461538461541 | 2026년 7월은 자연재해성 생산 차질의 초기 충격을 반영하는 월이다. 기준값 1.0384615384615388에 순 25% 하향을 적용해 0.7788461538461541로 산정했다. |
| 8 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 113, "Year": 2026}` | 1.0384615384615388 | 0.882692307692308 | 2026년 8월은 단기수리 진행에 따라 차질 강도를 낮춘 월이다. 기준값 1.0384615384615388에 순 15% 하향을 적용해 0.882692307692308로 산정했다. |
| 9 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 114, "Year": 2026}` | 1.0384615384615388 | 0.9865384615384618 | 2026년 9월은 3개월 차질의 회복 말기로 잔여 제약만 보수적으로 반영했다. 기준값 1.0384615384615388에 순 5% 하향을 적용해 0.9865384615384618로 산정했다. |
| 10 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 2.50025, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 2026년 7월은 서부 호주 생산 설비 차질의 초기 충격을 반영하는 월이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다. |
| 11 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 2.50025, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474701 | 2026년 8월은 단기수리로 가동 차질이 일부 완화되는 구간이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다. |
| 12 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 2.50025, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.6537683713471725 | 2026년 9월은 회복 말기로 생산 제약이 크게 축소되는 월이다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다. |
| 13 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 2.50025, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 2026년 7월은 급손상 직후 높은 생산 차질을 반영하는 월이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다. |
| 14 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 2.50025, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474701 | 2026년 8월은 수리 진행에 따른 부분 회복을 반영했다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다. |
| 15 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 2.50025, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.6537683713471725 | 2026년 9월은 차질 기간의 마지막 달로 잔여 영향만 반영했다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다. |
| 16 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 2.50025, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 2026년 7월은 생산 설비 직접 피해의 초기 하향 조정이 필요한 월이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다. |
| 17 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 2.50025, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474701 | 2026년 8월은 급손상 이후 단기수리로 차질이 완화되는 월이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다. |
| 18 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 2.50025, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.6537683713471725 | 2026년 9월은 회복이 진행된 마지막 영향 월이다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다. |
| 19 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.60046, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 2026년 7월은 높은 생산 차질이 가장 직접적으로 반영되는 첫 달이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다. |
| 20 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.60046, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474701 | 2026년 8월은 단기수리 과정에서 차질 폭을 줄여 반영하는 월이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다. |
| 21 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.60046, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.6537683713471725 | 2026년 9월은 복구가 상당 부분 반영된 월로 잔여 제약만 적용했다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다. |
| 22 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.60046, "Period": 112, "Year": 2026}` | 0.6881772329970237 | 0.5161329247477678 | 2026년 7월은 자연재해성 생산 차질 초기의 강한 하향 영향을 반영했다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다. |
| 23 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.60046, "Period": 113, "Year": 2026}` | 0.6881772329970237 | 0.5849506480474701 | 2026년 8월은 수리 진행에 따른 부분 회복을 반영하는 월이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다. |
| 24 | `{"Country": "Australia", "LNG Plant": "North West Shelf LNG", "LNG Plant Train": "North West Shelf LNG T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.60046, "Period": 114, "Year": 2026}` | 0.6881772329970237 | 0.6537683713471725 | 2026년 9월은 3개월 차질의 마지막 달로 회복 후 잔여 영향만 남는 것으로 보았다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다. |
| 25 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.9, "Period": 112, "Year": 2026}` | 1.0329681103448276 | 0.7747260827586206 | 2026년 7월은 생산 설비 피해가 즉시 반영되는 첫 달이다. 기준값 1.0329681103448276에 순 25% 하향을 적용해 0.7747260827586207로 산정했다. |
| 26 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.9, "Period": 113, "Year": 2026}` | 1.0329681103448276 | 0.8780228937931035 | 2026년 8월은 단기수리로 초기 충격 대비 차질 폭이 완화되는 월이다. 기준값 1.0329681103448276에 순 15% 하향을 적용해 0.8780228937931035로 산정했다. |
| 27 | `{"Country": "Australia", "LNG Plant": "Pluto LNG", "LNG Plant Train": "Pluto LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.9, "Period": 114, "Year": 2026}` | 1.0329681103448276 | 0.9813197048275862 | 2026년 9월은 회복 말기이므로 잔여 생산 제약만 반영했다. 기준값 1.0329681103448276에 순 5% 하향을 적용해 0.9813197048275862로 산정했다. |

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
  "mi_event_id": 1245,
  "model_param_proposal_id": 110,
  "proposal_completed_dtm": "2026-07-07 23:43:43.445883",
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
      "rationale": "영향 시설 유형이 생산 시설이고, 설명상 액화 생산 설비의 단기·부분 가동 차질이므로 Train/month 액화 가동률을 조정하는 LiqUtilAdjustment가 적합하다. 대체 LNG 공급 가능성 50%는 피해로 인한 공급 감소가 절반만 완화되는 조건으로 반영하고, 3개월·급손상-단기수리 패턴에 맞춰 초기 하향 폭을 크게 두되 월별로 회복되는 구조로 제안한다.",
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
          "rationale": "2026년 7월은 3개월 차질의 첫 달로 급손상 영향이 가장 크게 반영되는 구간이다. 기준값 1.0384615384615388에 높은 생산 차질을 적용하되 대체 LNG 공급 50%를 감안해 순 25% 하향하여 0.7788461538461541로 산정했다."
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
          "proposedValue": 0.882692307692308,
          "rationale": "2026년 8월은 단기수리 진행으로 첫 달보다 차질이 완화되는 구간이다. 기준값 1.0384615384615388에 순 15% 하향을 적용해 0.882692307692308로 산정했다."
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
          "proposedValue": 0.9865384615384618,
          "rationale": "2026년 9월은 3개월 차질의 마지막 달로 수리 후 회복이 상당 부분 진행되는 구간이다. 기준값 1.0384615384615388에 잔여 차질 순 5% 하향을 적용해 0.9865384615384618로 산정했다."
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
          "rationale": "2026년 7월은 급손상 발생 직후의 첫 달로 동일 설비군 내 직접 생산 차질을 반영했다. 기준값 1.0384615384615388에 순 25% 하향을 적용해 0.7788461538461541로 산정했다."
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
          "proposedValue": 0.882692307692308,
          "rationale": "2026년 8월은 단기수리로 차질이 일부 완화되는 중간 월이다. 기준값 1.0384615384615388에 순 15% 하향을 적용해 0.882692307692308로 산정했다."
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
          "proposedValue": 0.9865384615384618,
          "rationale": "2026년 9월은 수리 완료에 가까운 회복 월로 잔여 생산 제약만 반영했다. 기준값 1.0384615384615388에 순 5% 하향을 적용해 0.9865384615384618로 산정했다."
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
          "rationale": "2026년 7월은 자연재해성 생산 차질의 초기 충격을 반영하는 월이다. 기준값 1.0384615384615388에 순 25% 하향을 적용해 0.7788461538461541로 산정했다."
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
          "proposedValue": 0.882692307692308,
          "rationale": "2026년 8월은 단기수리 진행에 따라 차질 강도를 낮춘 월이다. 기준값 1.0384615384615388에 순 15% 하향을 적용해 0.882692307692308로 산정했다."
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
          "proposedValue": 0.9865384615384618,
          "rationale": "2026년 9월은 3개월 차질의 회복 말기로 잔여 제약만 보수적으로 반영했다. 기준값 1.0384615384615388에 순 5% 하향을 적용해 0.9865384615384618로 산정했다."
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
          "rationale": "2026년 7월은 서부 호주 생산 설비 차질의 초기 충격을 반영하는 월이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다."
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
          "proposedValue": 0.5849506480474701,
          "rationale": "2026년 8월은 단기수리로 가동 차질이 일부 완화되는 구간이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다."
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
          "proposedValue": 0.6537683713471725,
          "rationale": "2026년 9월은 회복 말기로 생산 제약이 크게 축소되는 월이다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다."
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
          "rationale": "2026년 7월은 급손상 직후 높은 생산 차질을 반영하는 월이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다."
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
          "proposedValue": 0.5849506480474701,
          "rationale": "2026년 8월은 수리 진행에 따른 부분 회복을 반영했다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다."
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
          "proposedValue": 0.6537683713471725,
          "rationale": "2026년 9월은 차질 기간의 마지막 달로 잔여 영향만 반영했다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다."
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
          "rationale": "2026년 7월은 생산 설비 직접 피해의 초기 하향 조정이 필요한 월이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다."
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
          "proposedValue": 0.5849506480474701,
          "rationale": "2026년 8월은 급손상 이후 단기수리로 차질이 완화되는 월이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다."
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
          "proposedValue": 0.6537683713471725,
          "rationale": "2026년 9월은 회복이 진행된 마지막 영향 월이다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다."
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
          "rationale": "2026년 7월은 높은 생산 차질이 가장 직접적으로 반영되는 첫 달이다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다."
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
          "proposedValue": 0.5849506480474701,
          "rationale": "2026년 8월은 단기수리 과정에서 차질 폭을 줄여 반영하는 월이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다."
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
          "proposedValue": 0.6537683713471725,
          "rationale": "2026년 9월은 복구가 상당 부분 반영된 월로 잔여 제약만 적용했다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다."
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
          "rationale": "2026년 7월은 자연재해성 생산 차질 초기의 강한 하향 영향을 반영했다. 기준값 0.6881772329970237에 순 25% 하향을 적용해 0.5161329247477678로 산정했다."
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
          "proposedValue": 0.5849506480474701,
          "rationale": "2026년 8월은 수리 진행에 따른 부분 회복을 반영하는 월이다. 기준값 0.6881772329970237에 순 15% 하향을 적용해 0.5849506480474701로 산정했다."
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
          "proposedValue": 0.6537683713471725,
          "rationale": "2026년 9월은 3개월 차질의 마지막 달로 회복 후 잔여 영향만 남는 것으로 보았다. 기준값 0.6881772329970237에 순 5% 하향을 적용해 0.6537683713471725로 산정했다."
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
          "rationale": "2026년 7월은 생산 설비 피해가 즉시 반영되는 첫 달이다. 기준값 1.0329681103448276에 순 25% 하향을 적용해 0.7747260827586207로 산정했다."
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
          "proposedValue": 0.8780228937931035,
          "rationale": "2026년 8월은 단기수리로 초기 충격 대비 차질 폭이 완화되는 월이다. 기준값 1.0329681103448276에 순 15% 하향을 적용해 0.8780228937931035로 산정했다."
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
          "proposedValue": 0.9813197048275862,
          "rationale": "2026년 9월은 회복 말기이므로 잔여 생산 제약만 반영했다. 기준값 1.0329681103448276에 순 5% 하향을 적용해 0.9813197048275862로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:08.804 | 8.804 | 2557 | 161 | 2718 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:45.390 | 105.390 | 11967 | 8270 | 20237 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:17.905 | 77.905 | 13317 | 6447 | 19764 |

##### scenario_id=280 [model_parameter_agent_test] 수입 시설 피해

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 04:31.625 (271.625s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 84 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=6, basecaseValue_present=6 | PASS |
| Step2 slot axis value 수 | `{"parameter|11|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 6 | 영향 시설 유형이 수입 시설로 제시되어 수입 터미널·재기화 인프라 처리 여력 저하를 설명하므로, 액화 Train 월별 이용률을 조정하는 LiqUtilAdjustment에는 직접적인 감산 신호로 연결되지 않습니다. 대체 LNG 공급 가능성 25%는 공급국 액화설비 상향 배분 가능성을 시사하지만, 본 시나리오의 직접 피해 대상이 액화시설이 아니고 선택된 공급국별 증산 배분 근거가 제한적이므로, 해당 파라미터는 보수적으로 기준 가동률을 유지하는 구조로 제안합니다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.2, "Period": 112, "Year": 2026}` | 1.0384615384615388 | 1.0384615384615388 | 선택된 6개월 구간의 첫 월이자 호주 액화설비 대표 Train에 해당하나, 시나리오상 직접 피해가 수입 시설에 집중되어 액화 Train 이용률 하향 조정 근거는 제한적입니다. 기준값 1.0384615384615388을 최종 입력값으로 유지했습니다. |
| 2 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.2, "Period": 113, "Year": 2026}` | 1.0384615384615388 | 1.0384615384615388 | 6개월 영향 기간 내 두 번째 월로 선택된 동일 Train에 대해, 수입 시설 피해가 액화설비 가동률 저하로 직접 전이된다는 추가 근거가 없습니다. 기준값 1.0384615384615388을 유지했습니다. |
| 3 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.2, "Period": 114, "Year": 2026}` | 1.0384615384615388 | 1.0384615384615388 | 장기 재건 패턴은 기간상 지속성을 시사하지만, 해당 좌표의 액화 Train 자체 손상 또는 운영 제약으로 해석할 수 있는 직접 근거가 약합니다. 기준값 1.0384615384615388을 최종 입력값으로 적용했습니다. |
| 4 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 5.2, "Period": 115, "Year": 2026}` | 1.0384615384615388 | 1.0384615384615388 | 선택된 기간 중 네 번째 월이나, 수입 처리 여력 저하 시나리오를 액화 Train 이용률 감산으로 환산할 명확한 배분 기준이 없습니다. 기준값 1.0384615384615388을 그대로 유지했습니다. |
| 5 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 5.2, "Period": 116, "Year": 2026}` | 1.0384615384615388 | 1.0384615384615388 | 대체 LNG 공급 가능성은 제한적이지만, 이 좌표에서는 대체 공급 증감보다 액화 Train 자체 이용률 입력 여부가 핵심입니다. 직접 조정 근거가 없어 기준값 1.0384615384615388을 유지했습니다. |
| 6 | `{"Country": "Australia", "LNG Plant": "Gorgon LNG", "LNG Plant Train": "Gorgon LNG T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 5.2, "Period": 117, "Year": 2026}` | 1.0384615384615388 | 1.0384615384615388 | 6개월 영향 기간의 마지막 월로, 재건 지연 가능성은 존재하지만 피해 대상이 수입 인프라로 한정되어 액화 이용률 변경으로 직접 반영하지 않았습니다. 기준값 1.0384615384615388을 최종 입력값으로 유지했습니다. |

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
  "mi_event_id": 1245,
  "model_param_proposal_id": 112,
  "proposal_completed_dtm": "2026-07-07 23:45:03.175157",
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
      "rationale": "영향 시설 유형이 수입 시설로 제시되어 수입 터미널·재기화 인프라 처리 여력 저하를 설명하므로, 액화 Train 월별 이용률을 조정하는 LiqUtilAdjustment에는 직접적인 감산 신호로 연결되지 않습니다. 대체 LNG 공급 가능성 25%는 공급국 액화설비 상향 배분 가능성을 시사하지만, 본 시나리오의 직접 피해 대상이 액화시설이 아니고 선택된 공급국별 증산 배분 근거가 제한적이므로, 해당 파라미터는 보수적으로 기준 가동률을 유지하는 구조로 제안합니다.",
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
          "proposedValue": 1.0384615384615388,
          "rationale": "선택된 6개월 구간의 첫 월이자 호주 액화설비 대표 Train에 해당하나, 시나리오상 직접 피해가 수입 시설에 집중되어 액화 Train 이용률 하향 조정 근거는 제한적입니다. 기준값 1.0384615384615388을 최종 입력값으로 유지했습니다."
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
          "proposedValue": 1.0384615384615388,
          "rationale": "6개월 영향 기간 내 두 번째 월로 선택된 동일 Train에 대해, 수입 시설 피해가 액화설비 가동률 저하로 직접 전이된다는 추가 근거가 없습니다. 기준값 1.0384615384615388을 유지했습니다."
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
          "proposedValue": 1.0384615384615388,
          "rationale": "장기 재건 패턴은 기간상 지속성을 시사하지만, 해당 좌표의 액화 Train 자체 손상 또는 운영 제약으로 해석할 수 있는 직접 근거가 약합니다. 기준값 1.0384615384615388을 최종 입력값으로 적용했습니다."
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
          "proposedValue": 1.0384615384615388,
          "rationale": "선택된 기간 중 네 번째 월이나, 수입 처리 여력 저하 시나리오를 액화 Train 이용률 감산으로 환산할 명확한 배분 기준이 없습니다. 기준값 1.0384615384615388을 그대로 유지했습니다."
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
          "proposedValue": 1.0384615384615388,
          "rationale": "대체 LNG 공급 가능성은 제한적이지만, 이 좌표에서는 대체 공급 증감보다 액화 Train 자체 이용률 입력 여부가 핵심입니다. 직접 조정 근거가 없어 기준값 1.0384615384615388을 유지했습니다."
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
          "proposedValue": 1.0384615384615388,
          "rationale": "6개월 영향 기간의 마지막 월로, 재건 지연 가능성은 존재하지만 피해 대상이 수입 인프라로 한정되어 액화 이용률 변경으로 직접 반영하지 않았습니다. 기준값 1.0384615384615388을 최종 입력값으로 유지했습니다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:23.417 | 23.417 | 2560 | 1102 | 3662 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 02:19.813 | 139.813 | 11970 | 14615 | 26585 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:28.840 | 88.840 | 19709 | 4847 | 24556 |

#### event_type_l2_id=17 지정학적 긴장 및 전쟁·군사분쟁

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "타 공급국 상향으로 상쇄",
      "dimension": "demand_response_alternative_lng (수요측 대응 - 타 공급원 경유 LNG 확보량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "자체 PowerMix 조정으로 LNG 수요 감소(SPR/대체 효과 포함) : 수요국의 정책·비상 대응으로 LNG 발전 수요가 줄면 PowerMix의 Gas 비중을 낮추고 대체 전원 비중을 조정",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "장기화 시 종료 N/A — 시간축",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "액화시설 가동률 감소 : 영향권 액화시설의 이용률을 하향 조정하고, 단기 제약은 LiqUtilAdjustment를 우선 사용",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "생산량 직접 감소(대폭/영구) : 전쟁·제재로 장기 또는 영구 생산 손실이 명확할 때 생산량 자체를 하향 조정",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "upstream(가스전) 생산 차질 동반 시",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "Ref. 공급 차질 패턴 — 시계열",
      "dimension": "supply_disruption_pattern (공급 차질 - 발생/회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "From-To 계약 물량 취소 : 계약 취소는 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 가능량 감소가 확인될 때 Supply 계열 파라미터로 우회 반영",
      "dimension": "trade_restriction (거래 제한 (계약 취소 등))",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "용선료·보험료 상승 : 운송비·보험료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 선적 차질이 있으면 공급 차질 기간·강도 판단에만 사용",
      "dimension": "transport_disruption (운송 차질)",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [92, 93]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=92 1개월 내 물류 프리미엄 흡수

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 03:44.984 (224.984s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 20 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=20, basecaseValue_present=20 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 20 | 공급 차질 강도는 낮음으로 제시되어 영향권 액화시설의 단기 이용률 조정이 가능한 LiqUtilAdjustment와 직접 연결된다. 다만 타 공급원 경유 LNG 확보량이 100%로 제시되고, 이벤트상 호르무즈 통항 재개와 특정 LNG 터미널·화물 차질 부재가 확인되므로 설비 가동률 자체의 물리적 하향은 반영하지 않고 1개월 이하 기간의 선택 슬롯에 대해 현행 기준 수준을 유지한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 해당 2026년 7월 슬롯은 카타르 주요 액화 트레인으로 항로 리스크 영향권에 있으나, 설비 중단이나 선적 취소가 확인되지 않았고 대체 LNG 확보가 전량 가능하므로 기준값 1.0477010309278352를 그대로 최종 입력값으로 유지한다. |
| 2 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 해당 2026년 7월 슬롯은 동일 플랜트 내 운전 트레인으로 단기 물류 리스크는 남아 있으나 물리적 액화 차질 근거가 없으므로 기준값 1.0477010309278352를 유지한다. |
| 3 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 1.0477010309278352 | 해당 2026년 7월 슬롯은 중동 항로 리스크 노출 설비이나 호르무즈 재개방 이후 확인된 공급 차질이 낮고 대체 확보가 충분하므로 기준값 1.0477010309278352를 최종 입력값으로 둔다. |
| 4 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 2026년 7월 대형 트레인은 영향권에 포함되지만 LNG 설비 가동 중단이 확인되지 않았고 시나리오 기간도 1개월 이하이므로 기준값 1.0476962025316454를 유지한다. |
| 5 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 2026년 7월 슬롯은 동일 설비군의 운전 트레인으로, 낮은 차질 강도와 전량 대체 확보 조건을 반영해 기준값 1.0476962025316454를 변경하지 않는다. |
| 6 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 2026년 7월 슬롯은 카타르 수출 설비로 지정학 리스크 대상이지만, 이벤트상 실제 LNG 생산 차질은 확인되지 않아 기준값 1.0476962025316454를 유지한다. |
| 7 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 2026년 7월 슬롯은 호르무즈 경유 물류 프리미엄에 노출될 수 있으나, 재개방과 낮은 차질 강도를 감안하면 설비 이용률 하향 근거가 약해 기준값 1.0476962025316454를 유지한다. |
| 8 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 1.0476969696969696 | 해당 2026년 7월 슬롯은 카타르 내 영향권 트레인이지만 공급 차질 강도가 낮고 부족분 대체가 가능하므로 기준값 1.0476969696969696을 그대로 적용한다. |
| 9 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 1.0476969696969696 | 해당 2026년 7월 슬롯은 단기 항로 리스크의 간접 영향권이나 물리적 액화 감소가 확인되지 않았으므로 기준값 1.0476969696969696을 유지한다. |
| 10 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 해당 2026년 7월 슬롯은 카타르 운전 트레인으로 선택되었으나, 시나리오가 물류 프리미엄 흡수와 전량 대체 확보를 전제하므로 기준값 1.0477021276595746을 최종값으로 유지한다. |
| 11 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 해당 2026년 7월 슬롯은 영향권에 있으나 호르무즈 통항 재개 이후 실제 가동률 저하 근거가 없어 기준값 1.0477021276595746을 유지한다. |
| 12 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 1.0477021276595746 | 해당 2026년 7월 슬롯은 낮은 차질 강도만 반영 가능한 대상이며, 대체 확보 100%와 특정 설비 차질 부재를 반영해 기준값 1.0477021276595746을 유지한다. |
| 13 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 2026년 7월 슬롯은 대형 카타르 트레인이지만, 이번 케이스는 가격·물류 프리미엄 중심이고 생산 차질은 낮으므로 기준값 1.0476962025316454를 유지한다. |
| 14 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 1.0476962025316454 | 해당 2026년 7월 슬롯은 동일 영향권 내 운전 트레인이나, 통항 재개와 전량 대체 확보 조건으로 액화 이용률 하향을 적용하지 않고 기준값 1.0476962025316454를 유지한다. |
| 15 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0956424079065634 | 해당 2026년 7월 UAE 슬롯은 걸프 항로 리스크 영향권이나, 이벤트상 통항 정상화 신호가 있고 LNG 설비 차질이 확인되지 않아 기준값 1.0956424079065634를 유지한다. |
| 16 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0956424079065634 | 해당 2026년 7월 슬롯은 단기 물류 리스크 대상이나 공급 차질 강도가 낮고 대체 LNG가 전량 확보되는 조건이므로 기준값 1.0956424079065634를 변경하지 않는다. |
| 17 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0956424079065634 | 해당 2026년 7월 슬롯은 UAE 운전 트레인으로 영향권에 포함되지만, 실제 생산 감소 근거가 없고 시나리오가 단기 프리미엄 흡수를 전제하므로 기준값 1.0956424079065634를 유지한다. |
| 18 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.55, "Period": 112, "Year": 2026}` | 1.1814275778125545 | 1.1814275778125545 | 해당 2026년 7월 오만 슬롯은 중동 해상 물류 리스크와 관련될 수 있으나, 낮은 차질 강도와 호르무즈 재개방을 반영하면 액화 이용률 조정 필요가 제한적이므로 기준값 1.1814275778125545를 유지한다. |
| 19 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.55, "Period": 112, "Year": 2026}` | 1.1814275778125545 | 1.1814275778125545 | 해당 2026년 7월 슬롯은 오만 LNG 운전 트레인으로 선택되었으나, 실제 설비 중단이 없고 대체 조달이 충분한 케이스이므로 기준값 1.1814275778125545를 그대로 적용한다. |
| 20 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T3 (Qalhat)", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 0.9179166666666668 | 0.9179166666666668 | 해당 2026년 7월 슬롯은 오만 LNG 내 별도 트레인 기준값이 낮게 설정된 운전 슬롯이며, 이번 시나리오에서 추가 생산 차질을 뒷받침할 근거가 없어 기준값 0.9179166666666667을 유지한다. |

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
  "mi_event_id": 1133,
  "model_param_proposal_id": 111,
  "proposal_completed_dtm": "2026-07-07 23:44:31.815177",
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
      "rationale": "공급 차질 강도는 낮음으로 제시되어 영향권 액화시설의 단기 이용률 조정이 가능한 LiqUtilAdjustment와 직접 연결된다. 다만 타 공급원 경유 LNG 확보량이 100%로 제시되고, 이벤트상 호르무즈 통항 재개와 특정 LNG 터미널·화물 차질 부재가 확인되므로 설비 가동률 자체의 물리적 하향은 반영하지 않고 1개월 이하 기간의 선택 슬롯에 대해 현행 기준 수준을 유지한다.",
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 주요 액화 트레인으로 항로 리스크 영향권에 있으나, 설비 중단이나 선적 취소가 확인되지 않았고 대체 LNG 확보가 전량 가능하므로 기준값 1.0477010309278352를 그대로 최종 입력값으로 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 동일 플랜트 내 운전 트레인으로 단기 물류 리스크는 남아 있으나 물리적 액화 차질 근거가 없으므로 기준값 1.0477010309278352를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 중동 항로 리스크 노출 설비이나 호르무즈 재개방 이후 확인된 공급 차질이 낮고 대체 확보가 충분하므로 기준값 1.0477010309278352를 최종 입력값으로 둔다."
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
          "rationale": "해당 2026년 7월 대형 트레인은 영향권에 포함되지만 LNG 설비 가동 중단이 확인되지 않았고 시나리오 기간도 1개월 이하이므로 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 동일 설비군의 운전 트레인으로, 낮은 차질 강도와 전량 대체 확보 조건을 반영해 기준값 1.0476962025316454를 변경하지 않는다."
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 수출 설비로 지정학 리스크 대상이지만, 이벤트상 실제 LNG 생산 차질은 확인되지 않아 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 호르무즈 경유 물류 프리미엄에 노출될 수 있으나, 재개방과 낮은 차질 강도를 감안하면 설비 이용률 하향 근거가 약해 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 내 영향권 트레인이지만 공급 차질 강도가 낮고 부족분 대체가 가능하므로 기준값 1.0476969696969696을 그대로 적용한다."
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
          "rationale": "해당 2026년 7월 슬롯은 단기 항로 리스크의 간접 영향권이나 물리적 액화 감소가 확인되지 않았으므로 기준값 1.0476969696969696을 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 카타르 운전 트레인으로 선택되었으나, 시나리오가 물류 프리미엄 흡수와 전량 대체 확보를 전제하므로 기준값 1.0477021276595746을 최종값으로 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 영향권에 있으나 호르무즈 통항 재개 이후 실제 가동률 저하 근거가 없어 기준값 1.0477021276595746을 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 낮은 차질 강도만 반영 가능한 대상이며, 대체 확보 100%와 특정 설비 차질 부재를 반영해 기준값 1.0477021276595746을 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 대형 카타르 트레인이지만, 이번 케이스는 가격·물류 프리미엄 중심이고 생산 차질은 낮으므로 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 동일 영향권 내 운전 트레인이나, 통항 재개와 전량 대체 확보 조건으로 액화 이용률 하향을 적용하지 않고 기준값 1.0476962025316454를 유지한다."
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
          "rationale": "해당 2026년 7월 UAE 슬롯은 걸프 항로 리스크 영향권이나, 이벤트상 통항 정상화 신호가 있고 LNG 설비 차질이 확인되지 않아 기준값 1.0956424079065634를 유지한다."
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
          "rationale": "해당 2026년 7월 슬롯은 단기 물류 리스크 대상이나 공급 차질 강도가 낮고 대체 LNG가 전량 확보되는 조건이므로 기준값 1.0956424079065634를 변경하지 않는다."
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
          "rationale": "해당 2026년 7월 슬롯은 UAE 운전 트레인으로 영향권에 포함되지만, 실제 생산 감소 근거가 없고 시나리오가 단기 프리미엄 흡수를 전제하므로 기준값 1.0956424079065634를 유지한다."
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
          "proposedValue": 1.1814275778125545,
          "rationale": "해당 2026년 7월 오만 슬롯은 중동 해상 물류 리스크와 관련될 수 있으나, 낮은 차질 강도와 호르무즈 재개방을 반영하면 액화 이용률 조정 필요가 제한적이므로 기준값 1.1814275778125545를 유지한다."
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
          "proposedValue": 1.1814275778125545,
          "rationale": "해당 2026년 7월 슬롯은 오만 LNG 운전 트레인으로 선택되었으나, 실제 설비 중단이 없고 대체 조달이 충분한 케이스이므로 기준값 1.1814275778125545를 그대로 적용한다."
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
          "proposedValue": 0.9179166666666668,
          "rationale": "해당 2026년 7월 슬롯은 오만 LNG 내 별도 트레인 기준값이 낮게 설정된 운전 슬롯이며, 이번 시나리오에서 추가 생산 차질을 뒷받침할 근거가 없어 기준값 0.9179166666666667을 유지한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:08.724 | 8.724 | 3385 | 142 | 3527 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:50.647 | 110.647 | 12371 | 5361 | 17732 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:32.326 | 92.326 | 13755 | 4797 | 18552 |

##### scenario_id=93 3개월 부분 차질과 절반 대체 조달

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 06:07.484 (367.484s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment"]`
- selected_parameters: `["LiqUtilAdjustment"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=2, validated=1, final_selected=1, proposalParameters=1 | PASS |
| Step2 basecase raw rows | raw_records=21656 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=1, distinct_axis_values=120 | PASS |
| Step2 selected slot | 99 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=99, basecaseValue_present=99 | PASS |
| Step2 slot axis value 수 | `{"parameter|17|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 99 | 공급 차질 강도 ‘중간’은 영향권 액화시설의 단기 이용률 하향 조정과 직접 연결되며, LiqUtilAdjustment는 train/month 단위 가동률 override이므로 3개월 부분 차질을 반영하기에 적합하다. 동시에 타 공급원 경유 LNG 확보량 50%는 부족분의 절반을 대체 조달로 흡수한다는 의미이므로 중동 영향권 설비는 보수적으로 순 5% 하향하고, 대체 조달 후보인 미국 설비는 같은 기간 제한적인 2.5% 상향으로 배분했다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.55, "Period": 112, "Year": 2026}` | 1.1814275778125545 | 1.1223561989219266 | 2026년 7월 해당 train 기준값 1.1814275778125545에 3개월 중간 차질과 50% 대체 조달을 반영한 순 5% 하향(×0.95)을 적용했다. |
| 2 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.55, "Period": 113, "Year": 2026}` | 1.179121891844897 | 1.1201657972526518 | 2026년 8월 해당 train 기준값 1.1791218918448967에 동일한 3개월 순 차질 효과 5% 하향(×0.95)을 적용했다. |
| 3 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.55, "Period": 114, "Year": 2026}` | 0.951361502347418 | 0.9037934272300472 | 2026년 9월 해당 train 기준값 0.951361502347418에 동일한 3개월 순 차질 효과 5% 하향(×0.95)을 적용했다. |
| 4 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.55, "Period": 112, "Year": 2026}` | 1.1814275778125545 | 1.1223561989219266 | 2026년 7월 해당 train 기준값 1.1814275778125545에 순 5% 하향(×0.95)을 적용해 중간 수준의 운송·공급 제약을 반영했다. |
| 5 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.55, "Period": 113, "Year": 2026}` | 1.179121891844897 | 1.1201657972526518 | 2026년 8월 해당 train 기준값 1.1791218918448967에 순 5% 하향(×0.95)을 적용했다. |
| 6 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.55, "Period": 114, "Year": 2026}` | 0.951361502347418 | 0.9037934272300472 | 2026년 9월 해당 train 기준값 0.951361502347418에 순 5% 하향(×0.95)을 적용했다. |
| 7 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T3 (Qalhat)", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 0.9179166666666668 | 0.8720208333333332 | 2026년 7월 해당 train 기준값 0.9179166666666667에 순 5% 하향(×0.95)을 적용했다. |
| 8 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T3 (Qalhat)", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 113, "Year": 2026}` | 0.9940277777777776 | 0.9443263888888888 | 2026년 8월 해당 train 기준값 0.9940277777777777에 순 5% 하향(×0.95)을 적용했다. |
| 9 | `{"Country": "Oman", "LNG Plant": "Oman LNG", "LNG Plant Train": "Oman LNG T3 (Qalhat)", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 114, "Year": 2026}` | 0.9876111111111112 | 0.9382305555555556 | 2026년 9월 해당 train 기준값 0.9876111111111111에 순 5% 하향(×0.95)을 적용했다. |
| 10 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 2026년 7월 해당 train 기준값 1.0477010309278352에 호르무즈 관련 중간 차질의 순효과로 5% 하향(×0.95)을 적용했다. |
| 11 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 113, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다. |
| 12 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 114, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206186 | 2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다. |
| 13 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 2026년 7월 해당 train 기준값 1.0477010309278352에 순 5% 하향(×0.95)을 적용했다. |
| 14 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 113, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다. |
| 15 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 114, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206186 | 2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다. |
| 16 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.2, "Period": 112, "Year": 2026}` | 1.0477010309278352 | 0.9953159793814434 | 2026년 7월 해당 train 기준값 1.0477010309278352에 순 5% 하향(×0.95)을 적용했다. |
| 17 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.2, "Period": 113, "Year": 2026}` | 1.002484536082474 | 0.9523603092783504 | 2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다. |
| 18 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 1 T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.2, "Period": 114, "Year": 2026}` | 1.0294432989690725 | 0.9779711340206186 | 2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다. |
| 19 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다. |
| 20 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다. |
| 21 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.977970886075949 | 2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다. |
| 22 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다. |
| 23 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다. |
| 24 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 2 T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.977970886075949 | 2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다. |
| 25 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다. |
| 26 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다. |
| 27 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 3 T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.977970886075949 | 2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다. |
| 28 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다. |
| 29 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다. |
| 30 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Qatargas 4 T7", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.977970886075949 | 2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다. |
| 31 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 0.9953121212121212 | 2026년 7월 해당 train 기준값 1.0476969696969696에 순 5% 하향(×0.95)을 적용했다. |
| 32 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 113, "Year": 2026}` | 1.0024848484848483 | 0.952360606060606 | 2026년 8월 해당 train 기준값 1.0024848484848485에 순 5% 하향(×0.95)을 적용했다. |
| 33 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 114, "Year": 2026}` | 1.0294545454545456 | 0.9779818181818182 | 2026년 9월 해당 train 기준값 1.0294545454545456에 순 5% 하향(×0.95)을 적용했다. |
| 34 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3.3, "Period": 112, "Year": 2026}` | 1.0476969696969696 | 0.9953121212121212 | 2026년 7월 해당 train 기준값 1.0476969696969696에 순 5% 하향(×0.95)을 적용했다. |
| 35 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3.3, "Period": 113, "Year": 2026}` | 1.0024848484848483 | 0.952360606060606 | 2026년 8월 해당 train 기준값 1.0024848484848485에 순 5% 하향(×0.95)을 적용했다. |
| 36 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 1 T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3.3, "Period": 114, "Year": 2026}` | 1.0294545454545456 | 0.9779818181818182 | 2026년 9월 해당 train 기준값 1.0294545454545456에 순 5% 하향(×0.95)을 적용했다. |
| 37 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 0.9953170212765958 | 2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다. |
| 38 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 113, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170214 | 2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다. |
| 39 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 114, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다. |
| 40 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 0.9953170212765958 | 2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다. |
| 41 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 113, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170214 | 2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다. |
| 42 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 114, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다. |
| 43 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.7, "Period": 112, "Year": 2026}` | 1.0477021276595746 | 0.9953170212765958 | 2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다. |
| 44 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.7, "Period": 113, "Year": 2026}` | 1.0024893617021278 | 0.9523648936170214 | 2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다. |
| 45 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 2 T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.7, "Period": 114, "Year": 2026}` | 1.029446808510638 | 0.977974468085106 | 2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다. |
| 46 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다. |
| 47 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다. |
| 48 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.977970886075949 | 2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다. |
| 49 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 7.8, "Period": 112, "Year": 2026}` | 1.0476962025316454 | 0.9953113924050632 | 2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다. |
| 50 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 7.8, "Period": 113, "Year": 2026}` | 1.0024810126582275 | 0.952356962025316 | 2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다. |
| 51 | `{"Country": "Qatar", "LNG Plant": "QatarGas LNG", "LNG Plant Train": "Rasgas 3 T7", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 7.8, "Period": 114, "Year": 2026}` | 1.0294430379746833 | 0.977970886075949 | 2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다. |
| 52 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 7월 해당 train 기준값 1.0956424079065634에 중동 항로 차질의 순효과 5% 하향(×0.95)을 적용했다. |
| 53 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 1.15, "Period": 113, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 54 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 1.15, "Period": 114, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 55 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 1.15, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 7월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 56 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 1.15, "Period": 113, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 57 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 1.15, "Period": 114, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 58 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 3, "Period": 112, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 7월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 59 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 3, "Period": 113, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 60 | `{"Country": "UAE", "LNG Plant": "Adgas LNG", "LNG Plant Train": "Adgas LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 3, "Period": 114, "Year": 2026}` | 1.0956424079065634 | 1.0408602875112354 | 2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다. |
| 61 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 0.919568207996452 | 2026년 7월 해당 train 기준값 0.8971397151184897에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다. |
| 62 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | 0.9091015779867364 | 0.9318291174364048 | 2026년 8월 해당 train 기준값 0.9091015779867364에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다. |
| 63 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | 0.8993102144292602 | 0.9217929697899916 | 2026년 9월 해당 train 기준값 0.8993102144292602에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다. |
| 64 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 0.919568207996452 | 2026년 7월 해당 train 기준값 0.8971397151184897에 2.5% 상향(×1.025)을 적용했다. |
| 65 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | 0.9091015779867364 | 0.9318291174364048 | 2026년 8월 해당 train 기준값 0.9091015779867364에 2.5% 상향(×1.025)을 적용했다. |
| 66 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | 0.8993102144292602 | 0.9217929697899916 | 2026년 9월 해당 train 기준값 0.8993102144292602에 2.5% 상향(×1.025)을 적용했다. |
| 67 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.5, "Period": 112, "Year": 2026}` | 0.8971397151184897 | 0.919568207996452 | 2026년 7월 해당 train 기준값 0.8971397151184897에 2.5% 상향(×1.025)을 적용했다. |
| 68 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.5, "Period": 113, "Year": 2026}` | 0.9091015779867364 | 0.9318291174364048 | 2026년 8월 해당 train 기준값 0.9091015779867364에 2.5% 상향(×1.025)을 적용했다. |
| 69 | `{"Country": "United States", "LNG Plant": "Cameron LNG", "LNG Plant Train": "Cameron LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.5, "Period": 114, "Year": 2026}` | 0.8993102144292602 | 0.9217929697899916 | 2026년 9월 해당 train 기준값 0.8993102144292602에 2.5% 상향(×1.025)을 적용했다. |
| 70 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.52, "Period": 112, "Year": 2026}` | 1.053352130574862 | 1.0796859338392335 | 2026년 7월 해당 train 기준값 1.053352130574862에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다. |
| 71 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.52, "Period": 113, "Year": 2026}` | 1.078634161835613 | 1.1056000158815034 | 2026년 8월 해당 train 기준값 1.078634161835613에 2.5% 상향(×1.025)을 적용했다. |
| 72 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.52, "Period": 114, "Year": 2026}` | 1.107493424950098 | 1.1351807605738502 | 2026년 9월 해당 train 기준값 1.107493424950098에 2.5% 상향(×1.025)을 적용했다. |
| 73 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.52, "Period": 112, "Year": 2026}` | 1.053352130574862 | 1.0796859338392335 | 2026년 7월 해당 train 기준값 1.053352130574862에 2.5% 상향(×1.025)을 적용했다. |
| 74 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.52, "Period": 113, "Year": 2026}` | 1.078634161835613 | 1.1056000158815034 | 2026년 8월 해당 train 기준값 1.078634161835613에 2.5% 상향(×1.025)을 적용했다. |
| 75 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.52, "Period": 114, "Year": 2026}` | 1.107493424950098 | 1.1351807605738502 | 2026년 9월 해당 train 기준값 1.107493424950098에 2.5% 상향(×1.025)을 적용했다. |
| 76 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 4.52, "Period": 112, "Year": 2026}` | 1.106194690265487 | 1.133849557522124 | 2026년 7월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다. |
| 77 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 4.52, "Period": 113, "Year": 2026}` | 1.106194690265487 | 1.133849557522124 | 2026년 8월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다. |
| 78 | `{"Country": "United States", "LNG Plant": "Corpus Christi LNG", "LNG Plant Train": "Corpus Christi T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 4.52, "Period": 114, "Year": 2026}` | 1.106194690265487 | 1.133849557522124 | 2026년 9월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다. |
| 79 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.1, "Period": 112, "Year": 2026}` | 0.9887457459032464 | 1.0134643895508273 | 2026년 7월 해당 train 기준값 0.9887457459032463에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다. |
| 80 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.1, "Period": 113, "Year": 2026}` | 0.9964982077836354 | 1.0214106629782262 | 2026년 8월 해당 train 기준값 0.9964982077836354에 2.5% 상향(×1.025)을 적용했다. |
| 81 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.1, "Period": 114, "Year": 2026}` | 1.0039763425364874 | 1.0290757510998996 | 2026년 9월 해당 train 기준값 1.0039763425364874에 2.5% 상향(×1.025)을 적용했다. |
| 82 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.099999, "Period": 112, "Year": 2026}` | 0.9867723949850288 | 1.0114417048596545 | 2026년 7월 해당 train 기준값 0.9867723949850288에 2.5% 상향(×1.025)을 적용했다. |
| 83 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.099999, "Period": 113, "Year": 2026}` | 0.9945093844066656 | 1.0193721190168323 | 2026년 8월 해당 train 기준값 0.9945093844066657에 2.5% 상향(×1.025)을 적용했다. |
| 84 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.099999, "Period": 114, "Year": 2026}` | 1.0019725942062196 | 1.027021909061375 | 2026년 9월 해당 train 기준값 1.0019725942062196에 2.5% 상향(×1.025)을 적용했다. |
| 85 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T3", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5.099999, "Period": 112, "Year": 2026}` | 0.984798850195059 | 1.009418821449935 | 2026년 7월 해당 train 기준값 0.984798850195059에 2.5% 상향(×1.025)을 적용했다. |
| 86 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T3", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5.099999, "Period": 113, "Year": 2026}` | 0.9925203656378526 | 1.017333374778799 | 2026년 8월 해당 train 기준값 0.9925203656378526에 2.5% 상향(×1.025)을 적용했다. |
| 87 | `{"Country": "United States", "LNG Plant": "Freeport LNG", "LNG Plant Train": "Freeport LNG T3", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5.099999, "Period": 114, "Year": 2026}` | 0.9999686490178076 | 1.0249678652432528 | 2026년 9월 해당 train 기준값 0.9999686490178075에 2.5% 상향(×1.025)을 적용했다. |
| 88 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 10, "Period": 112, "Year": 2026}` | 0.978 | 1.00245 | 2026년 7월 해당 train 기준값 0.978에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다. |
| 89 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 10, "Period": 113, "Year": 2026}` | 0.978 | 1.00245 | 2026년 8월 해당 train 기준값 0.978에 2.5% 상향(×1.025)을 적용했다. |
| 90 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T1-T2", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 10, "Period": 114, "Year": 2026}` | 0.978 | 1.00245 | 2026년 9월 해당 train 기준값 0.978에 2.5% 상향(×1.025)을 적용했다. |
| 91 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 10, "Period": 112, "Year": 2026}` | 1.0065076455302508 | 1.031670336668507 | 2026년 7월 해당 train 기준값 1.0065076455302508에 2.5% 상향(×1.025)을 적용했다. |
| 92 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 10, "Period": 113, "Year": 2026}` | 1.0143993731929224 | 1.0397593575227455 | 2026년 8월 해당 train 기준값 1.0143993731929224에 2.5% 상향(×1.025)을 적용했다. |
| 93 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T3-T4", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 10, "Period": 114, "Year": 2026}` | 1.0220118456958256 | 1.0475621418382213 | 2026년 9월 해당 train 기준값 1.0220118456958256에 2.5% 상향(×1.025)을 적용했다. |
| 94 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5, "Period": 112, "Year": 2026}` | 0.9886406459054536 | 1.0133566620530896 | 2026년 7월 해당 train 기준값 0.9886406459054535에 2.5% 상향(×1.025)을 적용했다. |
| 95 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5, "Period": 113, "Year": 2026}` | 0.9963922837279592 | 1.0213020908211583 | 2026년 8월 해당 train 기준값 0.9963922837279593에 2.5% 상향(×1.025)을 적용했다. |
| 96 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T5", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5, "Period": 114, "Year": 2026}` | 1.003869623582882 | 1.028966364172454 | 2026년 9월 해당 train 기준값 1.003869623582882에 2.5% 상향(×1.025)을 적용했다. |
| 97 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 5, "Period": 112, "Year": 2026}` | 1.0044946302391904 | 1.0296079959951705 | 2026년 7월 해당 train 기준값 1.0044946302391904에 2.5% 상향(×1.025)을 적용했다. |
| 98 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 5, "Period": 113, "Year": 2026}` | 1.0123705744465366 | 1.0376798388077 | 2026년 8월 해당 train 기준값 1.0123705744465366에 2.5% 상향(×1.025)을 적용했다. |
| 99 | `{"Country": "United States", "LNG Plant": "Sabine Pass LNG", "LNG Plant Train": "Sabine Pass T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 5, "Period": 114, "Year": 2026}` | 1.019967822004434 | 1.0454670175545449 | 2026년 9월 해당 train 기준값 1.019967822004434에 2.5% 상향(×1.025)을 적용했다. |

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
  "mi_event_id": 1133,
  "model_param_proposal_id": 114,
  "proposal_completed_dtm": "2026-07-07 23:47:07.848202",
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
      "rationale": "공급 차질 강도 ‘중간’은 영향권 액화시설의 단기 이용률 하향 조정과 직접 연결되며, LiqUtilAdjustment는 train/month 단위 가동률 override이므로 3개월 부분 차질을 반영하기에 적합하다. 동시에 타 공급원 경유 LNG 확보량 50%는 부족분의 절반을 대체 조달로 흡수한다는 의미이므로 중동 영향권 설비는 보수적으로 순 5% 하향하고, 대체 조달 후보인 미국 설비는 같은 기간 제한적인 2.5% 상향으로 배분했다.",
      "values": [
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
          "rationale": "2026년 7월 해당 train 기준값 1.1814275778125545에 3개월 중간 차질과 50% 대체 조달을 반영한 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.1791218918448967에 동일한 3개월 순 차질 효과 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 0.951361502347418에 동일한 3개월 순 차질 효과 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.1814275778125545에 순 5% 하향(×0.95)을 적용해 중간 수준의 운송·공급 제약을 반영했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.1791218918448967에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 0.951361502347418에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 0.9179166666666667에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 0.9940277777777777에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 0.9876111111111111에 순 5% 하향(×0.95)을 적용했다."
        },
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
          "rationale": "2026년 7월 해당 train 기준값 1.0477010309278352에 호르무즈 관련 중간 차질의 순효과로 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779711340206186,
          "rationale": "2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0477010309278352에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779711340206186,
          "rationale": "2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0477010309278352에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024845360824741에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779711340206186,
          "rationale": "2026년 9월 해당 train 기준값 1.0294432989690723에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476969696969696에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024848484848485에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779818181818182,
          "rationale": "2026년 9월 해당 train 기준값 1.0294545454545456에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476969696969696에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024848484848485에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9779818181818182,
          "rationale": "2026년 9월 해당 train 기준값 1.0294545454545456에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9953170212765958,
          "rationale": "2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9953170212765958,
          "rationale": "2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9953170212765958,
          "rationale": "2026년 7월 해당 train 기준값 1.0477021276595746에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.9523648936170214,
          "rationale": "2026년 8월 해당 train 기준값 1.0024893617021278에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 9월 해당 train 기준값 1.029446808510638에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 7월 해당 train 기준값 1.0476962025316454에 순 5% 하향(×0.95)을 적용했다."
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
          "rationale": "2026년 8월 해당 train 기준값 1.0024810126582275에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 0.977970886075949,
          "rationale": "2026년 9월 해당 train 기준값 1.0294430379746833에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train 기준값 1.0956424079065634에 중동 항로 차질의 순효과 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 7월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 8월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
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
          "proposedValue": 1.0408602875112354,
          "rationale": "2026년 9월 해당 train 기준값 1.0956424079065634에 순 5% 하향(×0.95)을 적용했다."
        },
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
          "proposedValue": 0.919568207996452,
          "rationale": "2026년 7월 해당 train 기준값 0.8971397151184897에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9318291174364048,
          "rationale": "2026년 8월 해당 train 기준값 0.9091015779867364에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9217929697899916,
          "rationale": "2026년 9월 해당 train 기준값 0.8993102144292602에 대체 조달 반영을 위해 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.919568207996452,
          "rationale": "2026년 7월 해당 train 기준값 0.8971397151184897에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9318291174364048,
          "rationale": "2026년 8월 해당 train 기준값 0.9091015779867364에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9217929697899916,
          "rationale": "2026년 9월 해당 train 기준값 0.8993102144292602에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.919568207996452,
          "rationale": "2026년 7월 해당 train 기준값 0.8971397151184897에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9318291174364048,
          "rationale": "2026년 8월 해당 train 기준값 0.9091015779867364에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 0.9217929697899916,
          "rationale": "2026년 9월 해당 train 기준값 0.8993102144292602에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.053352130574862,
          "proposedValue": 1.0796859338392335,
          "rationale": "2026년 7월 해당 train 기준값 1.053352130574862에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.078634161835613,
          "proposedValue": 1.1056000158815034,
          "rationale": "2026년 8월 해당 train 기준값 1.078634161835613에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.107493424950098,
          "proposedValue": 1.1351807605738502,
          "rationale": "2026년 9월 해당 train 기준값 1.107493424950098에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.053352130574862,
          "proposedValue": 1.0796859338392335,
          "rationale": "2026년 7월 해당 train 기준값 1.053352130574862에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.078634161835613,
          "proposedValue": 1.1056000158815034,
          "rationale": "2026년 8월 해당 train 기준값 1.078634161835613에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.107493424950098,
          "proposedValue": 1.1351807605738502,
          "rationale": "2026년 9월 해당 train 기준값 1.107493424950098에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.106194690265487,
          "proposedValue": 1.133849557522124,
          "rationale": "2026년 7월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.106194690265487,
          "proposedValue": 1.133849557522124,
          "rationale": "2026년 8월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Corpus Christi LNG",
          "LNG Plant Train": "Corpus Christi T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 4.52,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.106194690265487,
          "proposedValue": 1.133849557522124,
          "rationale": "2026년 9월 해당 train 기준값 1.106194690265487에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9887457459032464,
          "proposedValue": 1.0134643895508273,
          "rationale": "2026년 7월 해당 train 기준값 0.9887457459032463에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9964982077836354,
          "proposedValue": 1.0214106629782262,
          "rationale": "2026년 8월 해당 train 기준값 0.9964982077836354에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T1",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.1,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0039763425364874,
          "proposedValue": 1.0290757510998996,
          "rationale": "2026년 9월 해당 train 기준값 1.0039763425364874에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9867723949850288,
          "proposedValue": 1.0114417048596545,
          "rationale": "2026년 7월 해당 train 기준값 0.9867723949850288에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9945093844066656,
          "proposedValue": 1.0193721190168323,
          "rationale": "2026년 8월 해당 train 기준값 0.9945093844066657에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T2",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0019725942062196,
          "proposedValue": 1.027021909061375,
          "rationale": "2026년 9월 해당 train 기준값 1.0019725942062196에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.984798850195059,
          "proposedValue": 1.009418821449935,
          "rationale": "2026년 7월 해당 train 기준값 0.984798850195059에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9925203656378526,
          "proposedValue": 1.017333374778799,
          "rationale": "2026년 8월 해당 train 기준값 0.9925203656378526에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Freeport LNG",
          "LNG Plant Train": "Freeport LNG T3",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5.099999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 0.9999686490178076,
          "proposedValue": 1.0249678652432528,
          "rationale": "2026년 9월 해당 train 기준값 0.9999686490178075에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 1.00245,
          "rationale": "2026년 7월 해당 train 기준값 0.978에 대체 조달 반영 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 1.00245,
          "rationale": "2026년 8월 해당 train 기준값 0.978에 2.5% 상향(×1.025)을 적용했다."
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
          "proposedValue": 1.00245,
          "rationale": "2026년 9월 해당 train 기준값 0.978에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0065076455302508,
          "proposedValue": 1.031670336668507,
          "rationale": "2026년 7월 해당 train 기준값 1.0065076455302508에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0143993731929224,
          "proposedValue": 1.0397593575227455,
          "rationale": "2026년 8월 해당 train 기준값 1.0143993731929224에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T3-T4",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 10,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.0220118456958256,
          "proposedValue": 1.0475621418382213,
          "rationale": "2026년 9월 해당 train 기준값 1.0220118456958256에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 0.9886406459054536,
          "proposedValue": 1.0133566620530896,
          "rationale": "2026년 7월 해당 train 기준값 0.9886406459054535에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 0.9963922837279592,
          "proposedValue": 1.0213020908211583,
          "rationale": "2026년 8월 해당 train 기준값 0.9963922837279593에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T5",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.003869623582882,
          "proposedValue": 1.028966364172454,
          "rationale": "2026년 9월 해당 train 기준값 1.003869623582882에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": 1.0044946302391904,
          "proposedValue": 1.0296079959951705,
          "rationale": "2026년 7월 해당 train 기준값 1.0044946302391904에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": 1.0123705744465366,
          "proposedValue": 1.0376798388077,
          "rationale": "2026년 8월 해당 train 기준값 1.0123705744465366에 2.5% 상향(×1.025)을 적용했다."
        },
        {
          "Country": "United States",
          "LNG Plant": "Sabine Pass LNG",
          "LNG Plant Train": "Sabine Pass T6",
          "Life Cycle Category": "Operational",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 5,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": 1.019967822004434,
          "proposedValue": 1.0454670175545449,
          "rationale": "2026년 9월 해당 train 기준값 1.019967822004434에 2.5% 상향(×1.025)을 적용했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.772 | 3.772 | 3384 | 127 | 3511 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 02:15.632 | 135.632 | 12367 | 15323 | 27690 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:27.197 | 207.197 | 23341 | 15385 | 38726 |

#### event_type_l2_id=18 경제 제재 및 무역 제한

##### Scenario Group

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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "대체 공급 형성 time delay 존재",
      "dimension": "demand_response_alternative_lng (수요측 대응 - 타 공급원 경유 LNG 확보량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "자체 PowerMix 조정 수요 감소",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "영구 제재 시 종료 N/A",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "액화시설 가동률 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "생산량 직접 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "upstream 생산 차질 동반 시",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "Ref. 공급 차질 패턴",
      "dimension": "supply_disruption_pattern (공급 차질 - 발생/회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "제재 대상 계약 취소(partial→full) : 계약 취소·제재 물량은 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 차질로 확인되는 경우 Supply 계열 파라미터로 우회 반영",
      "dimension": "trade_restriction (거래 제한 (계약 취소 등))",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "그림자 선단 등 운송료 상승 : 운송료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 운송 제약이 공급량에 연결될 때만 기간·강도 판단에 사용",
      "dimension": "transport_disruption (운송 차질)",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [129, 130]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=129 3개월 내 제재 프리미엄은 제한적

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:16.716 (136.716s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 10 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=10, basecaseValue_present=7 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 9 | 공급 차질 강도 ‘낮음’은 Arctic LNG 2의 액화시설 가동률을 직접 낮추는 요인이고, 타 공급원 경유 LNG 확보 ‘100%’는 부족분을 시장에서 상당 부분 상쇄해 가동률 하향 폭을 제한하는 요인으로 반영했다. 기간 3개월과 지연발생-단계적 회복 패턴을 공통 맥락으로 보아 초기에는 기준 수준을 유지하고 이후 월별로 완만하게 낮추는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.45 | 2026년 7월은 3개월 시나리오의 첫 달이고 지연발생 패턴상 실제 물량 영향이 아직 본격화되기 전으로 보았다. 동일 연월 기준값 0.45를 유지해 최종 가동률 입력값을 0.45로 둔다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.44 | 2026년 8월은 제재·선박 확인 절차에 따른 지연 영향이 일부 나타나는 구간으로 보되 차질 강도는 낮고 대체 LNG 확보가 가능하므로 기준값 0.45에서 소폭만 낮췄다. 최종 가동률 입력값은 0.44로 산정한다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.43 | 2026년 9월은 3개월 범위 내에서 지연된 제재 영향이 가장 분명해질 수 있는 달로 보았다. 다만 낮은 차질 강도와 100% 대체 조달 가능성을 감안해 기준값 0.45에서 완만하게 낮춘 0.43을 최종 입력값으로 제안한다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.45 | 2026년 7월은 지연발생 패턴의 초기 구간이므로 즉각적인 가동률 하향을 적용하지 않는다. 동일 연월 기준값 0.45를 유지해 최종 입력값을 0.45로 둔다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.44 | 2026년 8월은 제재 관련 절차 지연이 일부 반영될 수 있는 시점이지만, 차질 강도가 낮고 대체 LNG 확보가 충분한 설정이다. 기준값 0.45에서 제한적으로 낮춘 0.44를 최종 입력값으로 산정한다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.43 | 2026년 9월은 지연된 제재 영향이 가장 크게 반영될 수 있는 달로 보되, 실물 수급 압박은 제한적인 시나리오다. 기준값 0.45 대비 완만한 하향만 적용해 최종 입력값을 0.43으로 둔다. |
| 7 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | null | 0.45 | 해당 좌표에 일치하는 기준 레코드가 제공되지 않아 같은 프로젝트·동일 용량 train의 2026년 여름 기준 수준 0.45를 형식과 스케일 참고값으로 사용했다. 7월은 지연발생 초기 구간이므로 하향 조정 없이 최종 입력값을 0.45로 둔다. |
| 8 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | null | 0.44 | 해당 좌표의 직접 기준 레코드는 없으므로 같은 프로젝트 내 다른 train의 기준 수준 0.45를 참고했다. 8월에는 낮은 강도의 지연 영향만 반영해 0.44를 최종 입력값으로 제안한다. |
| 9 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | null | 0.43 | 해당 좌표의 직접 기준 레코드는 없으므로 같은 프로젝트 내 다른 train의 0.45 수준을 보수적 기준으로 삼았다. 9월은 지연된 제재 영향이 가장 뚜렷할 수 있는 구간이지만 차질 강도와 시장 상쇄 여건을 감안해 최종 입력값을 0.43으로 낮춘다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 113,
  "proposal_completed_dtm": "2026-07-07 23:46:00.185494",
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
      "rationale": "공급 차질 강도 ‘낮음’은 Arctic LNG 2의 액화시설 가동률을 직접 낮추는 요인이고, 타 공급원 경유 LNG 확보 ‘100%’는 부족분을 시장에서 상당 부분 상쇄해 가동률 하향 폭을 제한하는 요인으로 반영했다. 기간 3개월과 지연발생-단계적 회복 패턴을 공통 맥락으로 보아 초기에는 기준 수준을 유지하고 이후 월별로 완만하게 낮추는 구조로 제안한다.",
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
          "rationale": "2026년 7월은 3개월 시나리오의 첫 달이고 지연발생 패턴상 실제 물량 영향이 아직 본격화되기 전으로 보았다. 동일 연월 기준값 0.45를 유지해 최종 가동률 입력값을 0.45로 둔다."
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
          "rationale": "2026년 8월은 제재·선박 확인 절차에 따른 지연 영향이 일부 나타나는 구간으로 보되 차질 강도는 낮고 대체 LNG 확보가 가능하므로 기준값 0.45에서 소폭만 낮췄다. 최종 가동률 입력값은 0.44로 산정한다."
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
          "rationale": "2026년 9월은 3개월 범위 내에서 지연된 제재 영향이 가장 분명해질 수 있는 달로 보았다. 다만 낮은 차질 강도와 100% 대체 조달 가능성을 감안해 기준값 0.45에서 완만하게 낮춘 0.43을 최종 입력값으로 제안한다."
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
          "rationale": "2026년 7월은 지연발생 패턴의 초기 구간이므로 즉각적인 가동률 하향을 적용하지 않는다. 동일 연월 기준값 0.45를 유지해 최종 입력값을 0.45로 둔다."
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
          "proposedValue": 0.44,
          "rationale": "2026년 8월은 제재 관련 절차 지연이 일부 반영될 수 있는 시점이지만, 차질 강도가 낮고 대체 LNG 확보가 충분한 설정이다. 기준값 0.45에서 제한적으로 낮춘 0.44를 최종 입력값으로 산정한다."
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
          "proposedValue": 0.43,
          "rationale": "2026년 9월은 지연된 제재 영향이 가장 크게 반영될 수 있는 달로 보되, 실물 수급 압박은 제한적인 시나리오다. 기준값 0.45 대비 완만한 하향만 적용해 최종 입력값을 0.43으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 좌표에 일치하는 기준 레코드가 제공되지 않아 같은 프로젝트·동일 용량 train의 2026년 여름 기준 수준 0.45를 형식과 스케일 참고값으로 사용했다. 7월은 지연발생 초기 구간이므로 하향 조정 없이 최종 입력값을 0.45로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.44,
          "rationale": "해당 좌표의 직접 기준 레코드는 없으므로 같은 프로젝트 내 다른 train의 기준 수준 0.45를 참고했다. 8월에는 낮은 강도의 지연 영향만 반영해 0.44를 최종 입력값으로 제안한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.43,
          "rationale": "해당 좌표의 직접 기준 레코드는 없으므로 같은 프로젝트 내 다른 train의 0.45 수준을 보수적 기준으로 삼았다. 9월은 지연된 제재 영향이 가장 뚜렷할 수 있는 구간이지만 차질 강도와 시장 상쇄 여건을 감안해 최종 입력값을 0.43으로 낮춘다."
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
      "rationale": "PowerMix 조정 수요 감소 ‘100%’는 LNG 수요를 낮추기 위해 가스 발전 비중을 조정할 수 있음을 직접 의미하므로 이 parameter와 연결된다. 다만 기간은 3개월이고 공급 차질 강도도 낮아 연간 발전 믹스 입력값에는 제한적인 하향만 반영한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.0337,
          "rationale": "2026년 중국 Gas 발전 비중 기준값 0.0346에 대해, 3개월 동안의 낮은 강도 수급 리스크와 100% PowerMix 대응 가능성을 연간 값으로 희석해 반영했다. 단기 조정 효과만 보수적으로 적용해 최종 입력값은 0.0337로 산정한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.140 | 4.140 | 2612 | 158 | 2770 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:46.632 | 46.632 | 12099 | 3384 | 15483 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:12.386 | 72.386 | 10357 | 4409 | 14766 |

##### scenario_id=130 1년 중반까지 완만한 조달 긴장 후 해소

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 04:42.747 (282.747s)
- attempt: 1

###### Scenario Major Info

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

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 58 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=34, basecaseValue_present=34 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 12 | 공급 차질 강도 '중간'은 Arctic LNG 2의 제재·선박 운항 제약이 액화시설의 실제 가동률을 낮추는 방향으로 연결되므로 LiqUtilAdjustment를 조정한다. 대체 LNG 확보 50%는 수급 긴장을 일부 완화하지만 해당 러시아 프로젝트의 제재 리스크 자체를 제거하지는 못하므로, 1년 기간의 지연발생-즉시 해소 패턴에 맞춰 초기에는 제한적으로 낮추고 중반에 더 낮춘 뒤 해소 시점에는 기준 수준으로 복귀시키는 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.45 | 해당 월은 시나리오 시작 직후로 지연발생 패턴상 제재·운항 제약이 아직 누적되기 전이라고 보아 기준 가동률 0.45를 유지했다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.4275 | 제재 집행과 선박 운항 제약이 누적되기 시작하는 구간으로 보아 기준 가동률 0.45에서 보수적으로 5% 낮춘 0.4275를 적용했다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.3825 | 지연발생형 차질이 본격화되는 월로 보아 기준 가동률 0.45에서 중간 강도의 일부 반영치인 15% 하향을 적용해 0.3825로 산정했다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 115, "Year": 2026}` | 0.45 | 0.3375 | 제재와 결제·보험·선박 제약의 누적 영향이 가장 뚜렷한 구간으로 보아 기준 가동률 0.45에서 25% 하향한 0.3375를 적용했다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 116, "Year": 2026}` | 0.45 | 0.3375 | 해소 전까지 조달 긴장이 유지되는 월로 보아 직전 월과 같은 중간 강도 조정치를 유지해 기준 가동률 0.45 대비 25% 낮은 0.3375로 산정했다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 6.599999, "Period": 123, "Year": 2027}` | 0.45 | 0.45 | 시나리오상 허가·우회 조달 확인 후 즉시 해소되는 말기 구간으로 보아 기준 가동률 0.45를 회복하는 값을 적용했다. |
| 7 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.45 | 해당 월은 지연발생 패턴의 초기 구간이므로 기준 가동률 0.45를 유지했다. |
| 8 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.4275 | 건설·상업화 단계의 트레인도 제재 대상 프로젝트의 출하·거래 제약을 받는다고 보아 기준 가동률 0.45에서 5% 하향한 0.4275를 적용했다. |
| 9 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.3825 | 제재 영향이 누적되는 구간으로 보아 기준 가동률 0.45에서 15% 하향한 0.3825를 적용했다. |
| 10 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 115, "Year": 2026}` | 0.45 | 0.3375 | 중간 강도 차질이 가장 뚜렷하게 반영되는 월로 보아 기준 가동률 0.45에서 25% 하향한 0.3375를 적용했다. |
| 11 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 116, "Year": 2026}` | 0.45 | 0.3375 | 해소 전까지 운송·거래 제약이 유지되는 구간으로 보아 기준 가동률 0.45 대비 25% 낮춘 0.3375를 유지했다. |
| 12 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 6, "Nameplate Capacity (MTPA)": 6.599999, "Period": 123, "Year": 2027}` | 0.45 | 0.45 | 1년 시나리오의 말기에는 우회 조달과 허가 확인으로 차질이 즉시 해소되는 것으로 보아 기준 가동률 0.45를 회복시켰다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 116,
  "proposal_completed_dtm": "2026-07-07 23:49:14.562382",
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
      "rationale": "공급 차질 강도 '중간'은 Arctic LNG 2의 제재·선박 운항 제약이 액화시설의 실제 가동률을 낮추는 방향으로 연결되므로 LiqUtilAdjustment를 조정한다. 대체 LNG 확보 50%는 수급 긴장을 일부 완화하지만 해당 러시아 프로젝트의 제재 리스크 자체를 제거하지는 못하므로, 1년 기간의 지연발생-즉시 해소 패턴에 맞춰 초기에는 제한적으로 낮추고 중반에 더 낮춘 뒤 해소 시점에는 기준 수준으로 복귀시키는 구조로 제안한다.",
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
          "rationale": "해당 월은 시나리오 시작 직후로 지연발생 패턴상 제재·운항 제약이 아직 누적되기 전이라고 보아 기준 가동률 0.45를 유지했다."
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
          "proposedValue": 0.4275,
          "rationale": "제재 집행과 선박 운항 제약이 누적되기 시작하는 구간으로 보아 기준 가동률 0.45에서 보수적으로 5% 낮춘 0.4275를 적용했다."
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
          "proposedValue": 0.3825,
          "rationale": "지연발생형 차질이 본격화되는 월로 보아 기준 가동률 0.45에서 중간 강도의 일부 반영치인 15% 하향을 적용해 0.3825로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "제재와 결제·보험·선박 제약의 누적 영향이 가장 뚜렷한 구간으로 보아 기준 가동률 0.45에서 25% 하향한 0.3375를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "해소 전까지 조달 긴장이 유지되는 월로 보아 직전 월과 같은 중간 강도 조정치를 유지해 기준 가동률 0.45 대비 25% 낮은 0.3375로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "시나리오상 허가·우회 조달 확인 후 즉시 해소되는 말기 구간으로 보아 기준 가동률 0.45를 회복하는 값을 적용했다."
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
          "rationale": "해당 월은 지연발생 패턴의 초기 구간이므로 기준 가동률 0.45를 유지했다."
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
          "proposedValue": 0.4275,
          "rationale": "건설·상업화 단계의 트레인도 제재 대상 프로젝트의 출하·거래 제약을 받는다고 보아 기준 가동률 0.45에서 5% 하향한 0.4275를 적용했다."
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
          "proposedValue": 0.3825,
          "rationale": "제재 영향이 누적되는 구간으로 보아 기준 가동률 0.45에서 15% 하향한 0.3825를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "중간 강도 차질이 가장 뚜렷하게 반영되는 월로 보아 기준 가동률 0.45에서 25% 하향한 0.3375를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.3375,
          "rationale": "해소 전까지 운송·거래 제약이 유지되는 구간으로 보아 기준 가동률 0.45 대비 25% 낮춘 0.3375를 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.45,
          "rationale": "1년 시나리오의 말기에는 우회 조달과 허가 확인으로 차질이 즉시 해소되는 것으로 보아 기준 가동률 0.45를 회복시켰다."
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
      "rationale": "수요측 대응 중 PowerMix 조정을 통한 LNG 수요 감소 50%는 가스 발전 비중을 낮춰 LNG 구매 필요량을 줄이는 방향으로 직접 연결되므로 PowerMix의 Gas 비중을 조정한다. 1년 기간이 연도 중간부터 다음 해 중반까지 걸쳐 있고 차질이 지연발생 후 해소되는 구조이므로, 연간 입력값에는 2026년에 더 완만한 하향, 2027년에 잔여 긴장을 반영한 소폭 추가 하향을 적용했다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.1862,
          "rationale": "2026년 Belgium Gas 기준 비중 0.19에 연중 부분적으로 나타나는 PowerMix 수요 절감 효과를 반영해 2% 하향한 0.1862로 산정했다."
        },
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1746,
          "rationale": "2027년 Belgium Gas 기준 비중 0.18에 해소 전 잔여 긴장을 반영해 3% 하향한 0.1746을 적용했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.033908,
          "rationale": "2026년 China Gas 기준 비중 0.0346에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.033908로 산정했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.0365,
          "proposedValue": 0.035405,
          "rationale": "2027년 China Gas 기준 비중 0.0365에 해소 전까지의 잔여 PowerMix 조정 효과를 반영해 3% 낮춘 0.035405를 적용했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04116,
          "rationale": "2026년 France Gas 기준 비중 0.042에 연중 부분적 조정 효과를 반영해 2% 하향한 0.04116으로 산정했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03298,
          "rationale": "2027년 France Gas 기준 비중 0.034에 잔여 긴장에 따른 PowerMix 조정 효과를 반영해 3% 하향한 0.03298을 적용했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.1323,
          "rationale": "2026년 Germany Gas 기준 비중 0.135에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.1323으로 산정했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.1261,
          "rationale": "2027년 Germany Gas 기준 비중 0.13에 해소 전 잔여 조정 효과를 반영해 3% 낮춘 0.1261을 적용했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.42532,
          "rationale": "2026년 Italy Gas 기준 비중 0.434에 연중 부분적 PowerMix 조정 효과를 반영해 2% 하향한 0.42532로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.40934,
          "rationale": "2027년 Italy Gas 기준 비중 0.422에 잔여 긴장 구간의 조정 효과를 반영해 3% 하향한 0.40934를 적용했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.31654,
          "rationale": "2026년 Japan Gas 기준 비중 0.323에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.31654로 산정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.318,
          "proposedValue": 0.30846,
          "rationale": "2027년 Japan Gas 기준 비중 0.318에 해소 전 잔여 PowerMix 조정 효과를 반영해 3% 낮춘 0.30846을 적용했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3118258620689655,
          "rationale": "2026년 Netherlands Gas 기준 비중 0.31818965517241377에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.3118258620689655로 산정했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.3269609756097561,
          "rationale": "2027년 Netherlands Gas 기준 비중 0.33707317073170734에 잔여 긴장에 따른 조정 효과를 반영해 3% 낮춘 0.32696097560975613을 적용했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.2793,
          "rationale": "2026년 South Korea Gas 기준 비중 0.285에 연중 부분적인 PowerMix 수요 절감 효과를 반영해 2% 하향한 0.2793으로 산정했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.265,
          "proposedValue": 0.25705,
          "rationale": "2027년 South Korea Gas 기준 비중 0.265에 해소 전 잔여 조정 효과를 반영해 3% 하향한 0.25705를 적용했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.20874,
          "rationale": "2026년 Spain Gas 기준 비중 0.213에 부분적인 연중 수요 절감 효과를 적용해 2% 낮춘 0.20874로 산정했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.20467,
          "rationale": "2027년 Spain Gas 기준 비중 0.211에 잔여 긴장 구간의 PowerMix 조정 효과를 반영해 3% 낮춘 0.20467을 적용했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.474,
          "proposedValue": 0.46452,
          "rationale": "2026년 Taiwan (China) Gas 기준 비중 0.474에 연중 부분적인 수요 절감 효과를 반영해 2% 하향한 0.46452로 산정했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.495,
          "proposedValue": 0.48015,
          "rationale": "2027년 Taiwan (China) Gas 기준 비중 0.495에 해소 전 잔여 조정 효과를 반영해 3% 하향한 0.48015를 적용했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.2842,
          "rationale": "2026년 United Kingdom Gas 기준 비중 0.29에 부분적인 연중 PowerMix 조정 효과를 반영해 2% 하향한 0.2842로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.2813,
          "rationale": "2027년 United Kingdom Gas 기준 비중 0.29에 잔여 긴장 구간의 조정 효과를 반영해 3% 하향한 0.2813을 적용했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.534 | 4.534 | 2623 | 171 | 2794 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:19.287 | 79.287 | 12110 | 8476 | 20586 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:01.082 | 181.082 | 14432 | 7189 | 21621 |

#### event_type_l2_id=18 경제 제재 및 무역 제한

##### Scenario Group

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
  "scenario_group_id": 23,
  "stage": "scenario_created",
  "status": "creating",
  "summary": "[러시아 LNG 제재] Arctic LNG 2 제재·지분 매각 허가 언급 → 무역 흐름 제약",
  "title": "러시아 Arctic LNG 2 제재 이슈"
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

##### Dimension -> Parameter Mapping

```json
{
  "dimension_parameter_mappings": [
    {
      "comment": "대체 공급 형성 time delay 존재",
      "dimension": "demand_response_alternative_lng (수요측 대응 - 타 공급원 경유 LNG 확보량)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "자체 PowerMix 조정 수요 감소",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "direct",
      "parameter": "PowerMix"
    },
    {
      "comment": "해당 섹터 수요 직접 감소 강제 시 : User-Adjusted Gas Demand 미대상 수동 overwrite는 직접 쓰지 않고, 수요 감소는 PowerMix Gas 비중 또는 대상 섹터 proxy로 환산",
      "dimension": "demand_response_powermix_reduction (수요측 대응 - PowerMix 조정 등을 통한 LNG 수요 감소량)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "영구 제재 시 종료 N/A",
      "dimension": "period (기간)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "액화시설 가동률 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "direct",
      "parameter": "LiqUtilAdjustment"
    },
    {
      "comment": "생산량 직접 감소",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "upstream 생산 차질 동반 시",
      "dimension": "supply_disruption_intensity (공급 차질 - 강도)",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "Ref. 공급 차질 패턴",
      "dimension": "supply_disruption_pattern (공급 차질 - 발생/회복 패턴)",
      "mapping_method": "indirect",
      "parameter": null
    },
    {
      "comment": "제재 대상 계약 취소(partial→full) : 계약 취소·제재 물량은 TradeRestrictionInput 미대상으로 직접 반영하지 않고, 실제 공급 차질로 확인되는 경우 Supply 계열 파라미터로 우회 반영",
      "dimension": "trade_restriction (거래 제한 (계약 취소 등))",
      "mapping_method": "na",
      "parameter": null
    },
    {
      "comment": "그림자 선단 등 운송료 상승 : 운송료 상승은 ShippingCost 미대상으로 직접 반영하지 않고, 물리적 운송 제약이 공급량에 연결될 때만 기간·강도 판단에 사용",
      "dimension": "transport_disruption (운송 차질)",
      "mapping_method": "na",
      "parameter": null
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

##### Event

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

##### Group Test Summary

- 대상 scenario_ids: [135, 136]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

##### scenario_id=135 3개월 내 제재 소음 흡수

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 02:49.706 (169.706s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "Y",
  "dimension_values": {
    "demand_response_alternative_lng": "100%",
    "demand_response_powermix_reduction": "100%",
    "period": "3개월",
    "supply_disruption_intensity": "낮음",
    "supply_disruption_pattern": "급차질-급회복"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "neutral"
  },
  "narrative": "기간은 3개월, 공급 차질 강도는 낮음으로 가정한다.\n패턴은 P1: Quick disrupt - Quick recover로, 제재 대상 선박·출하 이슈가 단기 지연 후 빠르게 정상화된다.\n타 공급원 경유 LNG 확보가 100%, PowerMix 조정에 따른 LNG 수요 감소도 100%로 작동해 물량 공백은 대부분 상쇄된다.\n시장 참여자는 Arctic LNG 2 헤드라인을 리스크 프리미엄으로 반영하지만, 실제 현물 조달 압박은 제한적으로 본다.",
  "probability_delta": 0.0,
  "probability_score": 35.0,
  "scenario_group_id": 23,
  "scenario_id": 135,
  "status": "creating",
  "title": "3개월 내 제재 소음 흡수"
}
```

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 10 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=10, basecaseValue_present=7 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 9 | 공급 차질 강도는 낮음으로 제시되어 Arctic LNG 2 액화시설 가동률에 제한적인 하향 조정으로 연결된다. 타 공급원 경유 LNG 확보가 100%로 작동하므로 시장 물량 공백은 완화되지만, 제재 대상 선박·출하 이슈에 따른 단기 운항 지연은 가동률 입력에 일부 반영한다. 기간은 3개월이고 급차질-급회복 패턴이므로 초기 월에 가장 큰 하향, 이후 빠른 회복 구조로 제안한다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.4 | 해당 월은 3개월 영향 구간의 첫 달로, 제재 대상 선박·출하 지연이 즉시 반영되는 구간이다. 기준 가동률 0.45에서 낮은 강도의 단기 차질을 보수적으로 반영해 약 0.05p 낮춘 최종 가동률 0.40을 적용한다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.425 | 두 번째 달은 급차질 이후 회복이 시작되는 구간으로 본다. 기준 가동률 0.45 대비 하향 폭을 절반 수준으로 축소해 최종 가동률 0.425를 적용한다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.45 | 세 번째 달은 빠른 회복이 마무리되는 구간으로, 낮은 차질 강도와 대체 조달 100% 전제를 감안해 추가 하향을 두지 않는다. 기준 가동률 0.45를 최종 입력값으로 유지한다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.4 | 해당 월은 3개월 영향 구간의 첫 달이며, 같은 프로젝트 내 제재 관련 출하·거래 제약이 신규 train의 초기 가동에도 단기적으로 반영될 수 있는 구간이다. 기준 가동률 0.45에서 낮은 강도의 차질을 반영해 최종 가동률 0.40을 적용한다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.425 | 두 번째 달은 급차질 이후 회복 단계로, 제재 소음의 실물 제약이 약화되는 것으로 본다. 기준 가동률 0.45 대비 하향 폭을 축소해 최종 가동률 0.425를 적용한다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.45 | 세 번째 달은 빠른 회복 패턴에 따라 제재 관련 단기 지연이 대부분 흡수되는 구간으로 본다. 기준 가동률 0.45를 유지해 최종 입력값으로 적용한다. |
| 7 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | null | 0.4 | 해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train에서 확인되는 0.45 수준을 형식과 스케일의 기준으로 삼았다. 영향 구간의 첫 달에는 낮은 강도의 단기 제재 차질을 반영해 최종 가동률 0.40을 적용한다. |
| 8 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | null | 0.425 | 해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train 기준 수준을 참고했다. 두 번째 달은 빠른 회복 단계로 보아 첫 달보다 하향 폭을 줄인 최종 가동률 0.425를 적용한다. |
| 9 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | null | 0.45 | 해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train 기준 수준을 참고했다. 세 번째 달은 급회복 후 정상화 구간으로 보아 최종 가동률 0.45를 적용한다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 115,
  "proposal_completed_dtm": "2026-07-07 23:47:52.893925",
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
      "rationale": "공급 차질 강도는 낮음으로 제시되어 Arctic LNG 2 액화시설 가동률에 제한적인 하향 조정으로 연결된다. 타 공급원 경유 LNG 확보가 100%로 작동하므로 시장 물량 공백은 완화되지만, 제재 대상 선박·출하 이슈에 따른 단기 운항 지연은 가동률 입력에 일부 반영한다. 기간은 3개월이고 급차질-급회복 패턴이므로 초기 월에 가장 큰 하향, 이후 빠른 회복 구조로 제안한다.",
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
          "proposedValue": 0.4,
          "rationale": "해당 월은 3개월 영향 구간의 첫 달로, 제재 대상 선박·출하 지연이 즉시 반영되는 구간이다. 기준 가동률 0.45에서 낮은 강도의 단기 차질을 보수적으로 반영해 약 0.05p 낮춘 최종 가동률 0.40을 적용한다."
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
          "proposedValue": 0.425,
          "rationale": "두 번째 달은 급차질 이후 회복이 시작되는 구간으로 본다. 기준 가동률 0.45 대비 하향 폭을 절반 수준으로 축소해 최종 가동률 0.425를 적용한다."
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
          "proposedValue": 0.45,
          "rationale": "세 번째 달은 빠른 회복이 마무리되는 구간으로, 낮은 차질 강도와 대체 조달 100% 전제를 감안해 추가 하향을 두지 않는다. 기준 가동률 0.45를 최종 입력값으로 유지한다."
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
          "proposedValue": 0.4,
          "rationale": "해당 월은 3개월 영향 구간의 첫 달이며, 같은 프로젝트 내 제재 관련 출하·거래 제약이 신규 train의 초기 가동에도 단기적으로 반영될 수 있는 구간이다. 기준 가동률 0.45에서 낮은 강도의 차질을 반영해 최종 가동률 0.40을 적용한다."
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
          "proposedValue": 0.425,
          "rationale": "두 번째 달은 급차질 이후 회복 단계로, 제재 소음의 실물 제약이 약화되는 것으로 본다. 기준 가동률 0.45 대비 하향 폭을 축소해 최종 가동률 0.425를 적용한다."
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
          "proposedValue": 0.45,
          "rationale": "세 번째 달은 빠른 회복 패턴에 따라 제재 관련 단기 지연이 대부분 흡수되는 구간으로 본다. 기준 가동률 0.45를 유지해 최종 입력값으로 적용한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.4,
          "rationale": "해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train에서 확인되는 0.45 수준을 형식과 스케일의 기준으로 삼았다. 영향 구간의 첫 달에는 낮은 강도의 단기 제재 차질을 반영해 최종 가동률 0.40을 적용한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.425,
          "rationale": "해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train 기준 수준을 참고했다. 두 번째 달은 빠른 회복 단계로 보아 첫 달보다 하향 폭을 줄인 최종 가동률 0.425를 적용한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.45,
          "rationale": "해당 train의 동일 좌표 기준값은 제공되지 않아 같은 프로젝트의 다른 train 기준 수준을 참고했다. 세 번째 달은 급회복 후 정상화 구간으로 보아 최종 가동률 0.45를 적용한다."
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
      "rationale": "PowerMix 조정을 통한 LNG 수요 감소량이 100%로 제시되어 중국의 가스 발전 비중을 낮추는 방향의 수요측 대응으로 연결된다. 다만 공급 차질 강도는 낮고 기간은 3개월의 단기 이벤트이므로 연간 PowerMix 입력에는 제한적인 하향 조정만 반영한다.",
      "values": [
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.034,
          "rationale": "선택된 좌표는 2026년 중국 Gas 발전 비중으로, 기준값 0.0346에 3개월 단기 대응 효과를 연간 평균에 보수적으로 반영했다. 공급 차질 강도가 낮고 빠른 회복을 전제로 하므로 하향 폭은 작게 두어 최종 비중 0.0340을 적용한다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 23,
  "scenario_id": 135,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.590 | 4.590 | 2617 | 165 | 2782 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:19.412 | 79.412 | 12092 | 4950 | 17042 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 01:12.245 | 72.245 | 10350 | 3318 | 13668 |

##### scenario_id=136 1년짜리 구조적 결손을 절반씩 상쇄

- target_parameter: `LiqUtilAdjustment`
- target_expected_present: YES
- target_selected_present: YES
- 소요시간: 05:18.011 (318.011s)
- attempt: 1

###### Scenario Major Info

```json
{
  "baseline_yn": "N",
  "dimension_values": {
    "demand_response_alternative_lng": "50%",
    "demand_response_powermix_reduction": "50%",
    "period": "1년",
    "supply_disruption_intensity": "중간",
    "supply_disruption_pattern": "영구 손실"
  },
  "impact": {
    "hh": "neutral",
    "jkm": "mild_bull",
    "ttf": "mild_bull"
  },
  "narrative": "기간은 1년, 공급 차질 강도는 중간으로 설정된다.\n패턴은 P4: Permanent loss로, Arctic LNG 2 관련 제재·지분 매각·선박 제약이 해당 기간 내 구조적 공급 손실처럼 작동한다.\n수요 측은 타 공급원 경유 LNG 50%와 PowerMix 조정 50%로 대응해 결손을 절반씩 나눠 흡수한다.\n다만 영구 손실 인식이 남아 아시아와 유럽 구매자는 장기 커버 물량 확보를 서두른다.",
  "probability_delta": 0.0,
  "probability_score": 20.0,
  "scenario_group_id": 23,
  "scenario_id": 136,
  "status": "creating",
  "title": "1년짜리 구조적 결손을 절반씩 상쇄"
}
```

###### Validation Summary

- target_expected_parameters: `["LiqUtilAdjustment"]`
- target_selected_parameters: `["LiqUtilAdjustment"]`
- expected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- selected_parameters: `["LiqUtilAdjustment", "PowerMix"]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: N/A

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=2, final_selected=2, proposalParameters=2 | PASS |
| Step2 basecase raw rows | raw_records=21713 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=2, distinct_axis_values=126 | PASS |
| Step2 selected slot | 58 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=58, basecaseValue_present=46 | PASS |
| Step2 slot axis value 수 | `{"18|demandresponsepowermixreduction|powermix|demand|powermixadjustment": {"Year": 6}, "parameter|18|supply|liqutiladjustment|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

###### Proposed Parameter Summary

| No | parameterName | modelTarget | slot axes | value fields | values | rationale |
|---:|---|---|---|---|---:|---|
| 1 | LiqUtilAdjustment | `{"modelFile": "Supply", "modelSheet": "LiqUtilAdjustment", "tableName": "table1"}` | `["Country", "LNG Plant", "LNG Plant Train", "Life Cycle Category", "Nameplate Capacity (MTPA)", "Year", "Month", "Period"]` | `["LiqUtilAdjustment"]` | 36 | 공급 차질 강도 ‘중간’은 Arctic LNG 2 액화설비의 가동률 하향 조정과 직접 연결되며, 타 공급원 경유 LNG 50%는 시장 결손을 일부 완화하지만 제재 대상 설비 자체의 생산 제약을 제거하지는 않는 것으로 해석했다. 기간 1년과 영구 손실 패턴은 2026년 7월부터 2027년 6월까지 구조적 가동 제약을 유지하는 방식으로 반영하고, 가동 중이거나 동일 프로젝트 내 선택된 train에 대해 보수적으로 중간 강도의 하향 값을 적용했다. |

###### Proposed Parameter Values

###### Proposed Values - LiqUtilAdjustment

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.225 | 해당 월은 1년 제재 영향이 시작되는 Arctic LNG 2 T1의 직접 대상 구간이다. 기준 가동률 0.45에 중간 강도의 구조적 공급 제약을 50% 하향으로 반영해 최종 가동률을 0.225로 산정했다. |
| 2 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.225 | 제재에 따른 1년 구조적 제약이 지속되는 월로 보았다. 기준 가동률 0.45에 동일한 중간 강도 50% 하향을 적용해 0.225로 제안했다. |
| 3 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.225 | Arctic LNG 2 T1의 제재 영향 지속 구간으로, 기준 가동률 0.45를 중간 차질 강도에 맞춰 절반 수준으로 낮췄다. |
| 4 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 115, "Year": 2026}` | 0.45 | 0.225 | 선박·거래 제약이 해소되지 않는 구조적 손실 구간으로 처리했다. 기준 0.45에서 50% 하향한 0.225를 최종 입력값으로 산정했다. |
| 5 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 116, "Year": 2026}` | 0.45 | 0.225 | 1년 제재 시나리오의 연속 적용 월이며 기준 가동률이 존재한다. 중간 강도 공급 차질을 기준값의 50% 하향으로 반영해 0.225로 제안했다. |
| 6 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 12, "Nameplate Capacity (MTPA)": 6.599999, "Period": 117, "Year": 2026}` | 0 | 0 | 해당 월의 기준 가동률이 이미 0이므로 추가 하향 여지가 없다. 제재 영향은 유지하되 최종 입력값은 기준과 같은 0으로 둔다. |
| 7 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity (MTPA)": 6.599999, "Period": 118, "Year": 2027}` | 0 | 0 | 1년 영향 기간 안에 포함되지만 기준 가동률이 0이다. 공급 제약 반영 후에도 최종 가동률은 0으로 유지했다. |
| 8 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity (MTPA)": 6.599999, "Period": 119, "Year": 2027}` | 0 | 0 | 기준값이 0인 비가동 월이므로 제재 차질을 별도 음수 조정으로 표현하지 않았다. 최종 입력값은 0이다. |
| 9 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity (MTPA)": 6.599999, "Period": 120, "Year": 2027}` | 0 | 0 | 기준 가동률이 이미 0으로 설정된 월이다. 구조적 제재 리스크가 지속되더라도 최종 모델 입력은 0으로 유지한다. |
| 10 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity (MTPA)": 6.599999, "Period": 121, "Year": 2027}` | 0 | 0 | 해당 월은 기준 가동률이 0이므로 중간 차질을 추가로 수치화하지 않았다. 최종 가동률은 0으로 둔다. |
| 11 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity (MTPA)": 6.599999, "Period": 122, "Year": 2027}` | 0 | 0 | 기준 가동률이 0인 구간으로, 제재 영향은 유지되지만 입력값은 기준 형식과 동일하게 0을 적용했다. |
| 12 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T1", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity (MTPA)": 6.599999, "Period": 123, "Year": 2027}` | 0.45 | 0.225 | 1년 영향 기간의 마지막 월로 기준 가동률이 0.45로 회복되는 구간이다. 영구 손실 성격이 남는 중간 강도 제약을 반영해 50% 하향한 0.225를 적용했다. |
| 13 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | 0.45 | 0.225 | 동일 프로젝트 내 T2도 제재·선박 제약의 직접 대상 train으로 보았다. 기준 가동률 0.45에 중간 강도의 구조적 제약을 50% 반영해 0.225로 낮췄다. |
| 14 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | 0.45 | 0.225 | 제재 영향이 지속되는 월로, 기준 0.45의 절반 수준만 실현되는 것으로 보수적으로 산정했다. |
| 15 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | 0.45 | 0.225 | T2의 선택 슬롯 중 기준 가동률이 존재하는 월이다. 중간 공급 차질을 기준값의 50% 하향으로 반영해 0.225를 적용했다. |
| 16 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 115, "Year": 2026}` | 0.45 | 0.225 | 무역·선박 제한이 이어지는 구조적 제약 구간이다. 기준 0.45에서 중간 강도 하향을 적용해 최종 0.225로 제안했다. |
| 17 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 116, "Year": 2026}` | 0.45 | 0.225 | 해당 월의 기준 가동률 0.45를 제재에 따른 중간 수준의 구조적 손실로 절반 낮춰 0.225로 산정했다. |
| 18 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 12, "Nameplate Capacity (MTPA)": 6.599999, "Period": 117, "Year": 2026}` | 0 | 0 | 기준 가동률이 0인 월이므로 제재 영향을 추가 감산 수치로 표현하지 않고 0을 유지했다. |
| 19 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 1, "Nameplate Capacity (MTPA)": 6.599999, "Period": 118, "Year": 2027}` | 0 | 0 | 영향 기간 안의 월이지만 기준 가동률이 0이다. 최종 입력값은 기준과 동일한 0으로 설정했다. |
| 20 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 2, "Nameplate Capacity (MTPA)": 6.599999, "Period": 119, "Year": 2027}` | 0 | 0 | 기준값이 0인 비가동 구간으로 판단해 추가적인 하향 조정 없이 0을 적용했다. |
| 21 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 3, "Nameplate Capacity (MTPA)": 6.599999, "Period": 120, "Year": 2027}` | 0 | 0 | 기준 가동률이 0으로 설정되어 있어 제재 영향 반영 후에도 최종 입력값은 0이다. |
| 22 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 4, "Nameplate Capacity (MTPA)": 6.599999, "Period": 121, "Year": 2027}` | 0 | 0 | 해당 월은 기준 가동률이 없는 수준이므로 중간 차질을 별도 감산으로 더하지 않고 0을 유지했다. |
| 23 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 5, "Nameplate Capacity (MTPA)": 6.599999, "Period": 122, "Year": 2027}` | 0 | 0 | 기준값 0인 구간으로, 최종 모델 입력도 0으로 설정해 과도한 임의 조정을 피했다. |
| 24 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T2", "Life Cycle Category": "Under Construction", "Month": 6, "Nameplate Capacity (MTPA)": 6.599999, "Period": 123, "Year": 2027}` | 0.45 | 0.225 | 1년 영향 기간의 말월에 기준 가동률 0.45가 존재한다. 제재의 영구 손실 성격을 반영해 절반 수준인 0.225로 낮췄다. |
| 25 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 7, "Nameplate Capacity (MTPA)": 6.599999, "Period": 112, "Year": 2026}` | null | 0.225 | T3의 직접 기준 record는 없지만 동일 Arctic LNG 2 프로젝트와 동일 용량의 선택 슬롯이므로 T1·T2의 기준 패턴을 형식 참고로 사용했다. 제재 영향이 시작되는 월에는 보수적으로 0.45 상당 기준의 50%인 0.225를 적용했다. |
| 26 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 8, "Nameplate Capacity (MTPA)": 6.599999, "Period": 113, "Year": 2026}` | null | 0.225 | 동일 프로젝트 내 train으로 제재의 적용 대상에 포함된다고 보았다. 직접 기준값 부재로 T1·T2의 같은 계절 패턴을 참고해 중간 차질 반영 후 0.225를 제안했다. |
| 27 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 9, "Nameplate Capacity (MTPA)": 6.599999, "Period": 114, "Year": 2026}` | null | 0.225 | T3는 기준 record가 없으므로 같은 프로젝트 train의 0.45 가동 구간을 보수적 기준으로 삼았다. 중간 강도 제재 영향으로 절반 수준인 0.225를 적용했다. |
| 28 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 10, "Nameplate Capacity (MTPA)": 6.599999, "Period": 115, "Year": 2026}` | null | 0.225 | 동일 프로젝트의 제재 지속 월로, 직접 기준값이 없어 T1·T2의 같은 월 기준 수준을 참고했다. 구조적 중간 차질을 반영해 0.225로 산정했다. |
| 29 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 11, "Nameplate Capacity (MTPA)": 6.599999, "Period": 116, "Year": 2026}` | null | 0.225 | T3도 선박·거래 제약의 프로젝트 단위 영향권으로 보았다. 같은 프로젝트의 기준 패턴을 참고해 0.45 상당의 절반인 0.225를 최종값으로 적용했다. |
| 30 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 12, "Nameplate Capacity (MTPA)": 6.599999, "Period": 117, "Year": 2026}` | null | 0 | 직접 기준 record는 없지만 같은 프로젝트 train의 해당 월 기준 패턴이 0인 구간이다. 보수적으로 비가동 유지값 0을 적용했다. |
| 31 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 1, "Nameplate Capacity (MTPA)": 6.599999, "Period": 118, "Year": 2027}` | null | 0 | T1·T2의 같은 계절 구간이 0으로 설정되어 있어 T3도 직접 기준 부재하에서 0을 보수적 유지값으로 사용했다. |
| 32 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 2, "Nameplate Capacity (MTPA)": 6.599999, "Period": 119, "Year": 2027}` | null | 0 | 직접 기준값은 없지만 같은 프로젝트의 기준 패턴상 비가동 구간으로 보았다. 최종 입력값은 0이다. |
| 33 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 3, "Nameplate Capacity (MTPA)": 6.599999, "Period": 120, "Year": 2027}` | null | 0 | 동일 프로젝트 train의 참고 패턴상 기준값이 0인 구간이므로, 제재 영향 반영 후에도 0으로 유지했다. |
| 34 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 4, "Nameplate Capacity (MTPA)": 6.599999, "Period": 121, "Year": 2027}` | null | 0 | 직접 record가 없는 T3에 대해 같은 프로젝트의 비가동 월 패턴을 참고했다. 불확실성을 고려해 0을 보수적 최종값으로 적용했다. |
| 35 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 5, "Nameplate Capacity (MTPA)": 6.599999, "Period": 122, "Year": 2027}` | null | 0 | 같은 프로젝트 train의 기준 패턴상 0인 구간으로 보아 T3도 0으로 두었다. 직접 기준값 부재에 따른 임의 증액은 적용하지 않았다. |
| 36 | `{"Country": "Russia", "LNG Plant": "Arctic LNG 2", "LNG Plant Train": "Arctic LNG 2 T3", "Life Cycle Category": "Under Construction", "Month": 6, "Nameplate Capacity (MTPA)": 6.599999, "Period": 123, "Year": 2027}` | null | 0.225 | 1년 영향 기간의 마지막 월이며 같은 프로젝트 train의 참고 기준 패턴은 가동 재개 수준을 보인다. 직접 기준값이 없어 0.45 상당을 보수적 기준으로 삼고 중간 차질 50%를 반영해 0.225로 산정했다. |

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
  "mi_event_id": 1177,
  "model_param_proposal_id": 119,
  "proposal_completed_dtm": "2026-07-07 23:51:18.195906",
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
      "rationale": "공급 차질 강도 ‘중간’은 Arctic LNG 2 액화설비의 가동률 하향 조정과 직접 연결되며, 타 공급원 경유 LNG 50%는 시장 결손을 일부 완화하지만 제재 대상 설비 자체의 생산 제약을 제거하지는 않는 것으로 해석했다. 기간 1년과 영구 손실 패턴은 2026년 7월부터 2027년 6월까지 구조적 가동 제약을 유지하는 방식으로 반영하고, 가동 중이거나 동일 프로젝트 내 선택된 train에 대해 보수적으로 중간 강도의 하향 값을 적용했다.",
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
          "proposedValue": 0.225,
          "rationale": "해당 월은 1년 제재 영향이 시작되는 Arctic LNG 2 T1의 직접 대상 구간이다. 기준 가동률 0.45에 중간 강도의 구조적 공급 제약을 50% 하향으로 반영해 최종 가동률을 0.225로 산정했다."
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
          "proposedValue": 0.225,
          "rationale": "제재에 따른 1년 구조적 제약이 지속되는 월로 보았다. 기준 가동률 0.45에 동일한 중간 강도 50% 하향을 적용해 0.225로 제안했다."
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
          "proposedValue": 0.225,
          "rationale": "Arctic LNG 2 T1의 제재 영향 지속 구간으로, 기준 가동률 0.45를 중간 차질 강도에 맞춰 절반 수준으로 낮췄다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "선박·거래 제약이 해소되지 않는 구조적 손실 구간으로 처리했다. 기준 0.45에서 50% 하향한 0.225를 최종 입력값으로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "1년 제재 시나리오의 연속 적용 월이며 기준 가동률이 존재한다. 중간 강도 공급 차질을 기준값의 50% 하향으로 반영해 0.225로 제안했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월의 기준 가동률이 이미 0이므로 추가 하향 여지가 없다. 제재 영향은 유지하되 최종 입력값은 기준과 같은 0으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "1년 영향 기간 안에 포함되지만 기준 가동률이 0이다. 공급 제약 반영 후에도 최종 가동률은 0으로 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준값이 0인 비가동 월이므로 제재 차질을 별도 음수 조정으로 표현하지 않았다. 최종 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 이미 0으로 설정된 월이다. 구조적 제재 리스크가 지속되더라도 최종 모델 입력은 0으로 유지한다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월은 기준 가동률이 0이므로 중간 차질을 추가로 수치화하지 않았다. 최종 가동률은 0으로 둔다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 0인 구간으로, 제재 영향은 유지되지만 입력값은 기준 형식과 동일하게 0을 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T1",
          "Life Cycle Category": "Operational",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "1년 영향 기간의 마지막 월로 기준 가동률이 0.45로 회복되는 구간이다. 영구 손실 성격이 남는 중간 강도 제약을 반영해 50% 하향한 0.225를 적용했다."
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
          "proposedValue": 0.225,
          "rationale": "동일 프로젝트 내 T2도 제재·선박 제약의 직접 대상 train으로 보았다. 기준 가동률 0.45에 중간 강도의 구조적 제약을 50% 반영해 0.225로 낮췄다."
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
          "proposedValue": 0.225,
          "rationale": "제재 영향이 지속되는 월로, 기준 0.45의 절반 수준만 실현되는 것으로 보수적으로 산정했다."
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
          "proposedValue": 0.225,
          "rationale": "T2의 선택 슬롯 중 기준 가동률이 존재하는 월이다. 중간 공급 차질을 기준값의 50% 하향으로 반영해 0.225를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "무역·선박 제한이 이어지는 구조적 제약 구간이다. 기준 0.45에서 중간 강도 하향을 적용해 최종 0.225로 제안했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "해당 월의 기준 가동률 0.45를 제재에 따른 중간 수준의 구조적 손실로 절반 낮춰 0.225로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 0인 월이므로 제재 영향을 추가 감산 수치로 표현하지 않고 0을 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "영향 기간 안의 월이지만 기준 가동률이 0이다. 최종 입력값은 기준과 동일한 0으로 설정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준값이 0인 비가동 구간으로 판단해 추가적인 하향 조정 없이 0을 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준 가동률이 0으로 설정되어 있어 제재 영향 반영 후에도 최종 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "해당 월은 기준 가동률이 없는 수준이므로 중간 차질을 별도 감산으로 더하지 않고 0을 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": 0,
          "proposedValue": 0,
          "rationale": "기준값 0인 구간으로, 최종 모델 입력도 0으로 설정해 과도한 임의 조정을 피했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T2",
          "Life Cycle Category": "Under Construction",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": 0.45,
          "proposedValue": 0.225,
          "rationale": "1년 영향 기간의 말월에 기준 가동률 0.45가 존재한다. 제재의 영구 손실 성격을 반영해 절반 수준인 0.225로 낮췄다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 7,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 112,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "T3의 직접 기준 record는 없지만 동일 Arctic LNG 2 프로젝트와 동일 용량의 선택 슬롯이므로 T1·T2의 기준 패턴을 형식 참고로 사용했다. 제재 영향이 시작되는 월에는 보수적으로 0.45 상당 기준의 50%인 0.225를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 8,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 113,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "동일 프로젝트 내 train으로 제재의 적용 대상에 포함된다고 보았다. 직접 기준값 부재로 T1·T2의 같은 계절 패턴을 참고해 중간 차질 반영 후 0.225를 제안했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 9,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 114,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "T3는 기준 record가 없으므로 같은 프로젝트 train의 0.45 가동 구간을 보수적 기준으로 삼았다. 중간 강도 제재 영향으로 절반 수준인 0.225를 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 10,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 115,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "동일 프로젝트의 제재 지속 월로, 직접 기준값이 없어 T1·T2의 같은 월 기준 수준을 참고했다. 구조적 중간 차질을 반영해 0.225로 산정했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 11,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 116,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "T3도 선박·거래 제약의 프로젝트 단위 영향권으로 보았다. 같은 프로젝트의 기준 패턴을 참고해 0.45 상당의 절반인 0.225를 최종값으로 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 12,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 117,
          "Year": 2026,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "직접 기준 record는 없지만 같은 프로젝트 train의 해당 월 기준 패턴이 0인 구간이다. 보수적으로 비가동 유지값 0을 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 1,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 118,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "T1·T2의 같은 계절 구간이 0으로 설정되어 있어 T3도 직접 기준 부재하에서 0을 보수적 유지값으로 사용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 2,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 119,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "직접 기준값은 없지만 같은 프로젝트의 기준 패턴상 비가동 구간으로 보았다. 최종 입력값은 0이다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 3,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 120,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "동일 프로젝트 train의 참고 패턴상 기준값이 0인 구간이므로, 제재 영향 반영 후에도 0으로 유지했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 4,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 121,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "직접 record가 없는 T3에 대해 같은 프로젝트의 비가동 월 패턴을 참고했다. 불확실성을 고려해 0을 보수적 최종값으로 적용했다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 5,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 122,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0,
          "rationale": "같은 프로젝트 train의 기준 패턴상 0인 구간으로 보아 T3도 0으로 두었다. 직접 기준값 부재에 따른 임의 증액은 적용하지 않았다."
        },
        {
          "Country": "Russia",
          "LNG Plant": "Arctic LNG 2",
          "LNG Plant Train": "Arctic LNG 2 T3",
          "Life Cycle Category": "Under Construction",
          "Month": 6,
          "Nameplate Capacity (MTPA)": 6.599999,
          "Period": 123,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 0.225,
          "rationale": "1년 영향 기간의 마지막 월이며 같은 프로젝트 train의 참고 기준 패턴은 가동 재개 수준을 보인다. 직접 기준값이 없어 0.45 상당을 보수적 기준으로 삼고 중간 차질 50%를 반영해 0.225로 산정했다."
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
      "rationale": "PowerMix 조정을 통한 LNG 수요 감소 50%는 발전 부문에서 가스 의존도를 낮춰 공급 결손을 흡수하는 직접 경로이므로 Gas 발전 비중 조정 parameter와 연결된다. 기간이 1년이고 연간 입력값만 선택되어 있어 2026년과 2027년에 분산 반영하되, 아시아·유럽 구매국 전반의 mild bullish 수급 긴장을 해치지 않도록 각 연도 가스 비중을 보수적으로 소폭 하향했다.",
      "values": [
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.19,
          "proposedValue": 0.18525,
          "rationale": "선택된 유럽 수요국의 2026년 Gas 발전 비중 기준값 0.19에 대해, 1년 영향이 연중 절반만 걸치는 점을 고려해 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Belgium",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.18,
          "proposedValue": 0.1755,
          "rationale": "2027년은 영향 기간의 잔여 절반이 반영되는 연간 슬롯이다. 기준값 0.18을 2.5% 상대 하향해 0.1755로 산정했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.0346,
          "proposedValue": 0.033735,
          "rationale": "아시아 수요국의 2026년 Gas 발전 비중 기준값 0.0346에 대해, PowerMix 조정을 통한 수요 완화를 연간 기준 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "China",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.0365,
          "proposedValue": 0.0355875,
          "rationale": "2027년 기준 Gas 비중 0.0365에 대해 1년 영향의 잔여 기간을 반영해 2.5% 상대 하향한 0.0355875를 적용했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.04095,
          "rationale": "2026년 France Gas 발전 비중 기준값 0.042를 대상으로, 공급 결손 흡수용 PowerMix 조정분을 보수적 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "France",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.034,
          "proposedValue": 0.03315,
          "rationale": "2027년 기준값 0.034에 대해 잔여 영향 기간의 수요 감축 효과를 반영해 0.03315로 낮췄다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.135,
          "proposedValue": 0.131625,
          "rationale": "2026년 Germany Gas 비중 기준값 0.135에 연간 절반 노출을 감안한 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Germany",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.13,
          "proposedValue": 0.12675,
          "rationale": "2027년 기준값 0.13을 대상으로 PowerMix 수요 감축 효과를 2.5% 상대 하향으로 반영해 0.12675로 산정했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.434,
          "proposedValue": 0.42315,
          "rationale": "Italy는 Gas 발전 비중이 높은 유럽 수요국이므로 선택 슬롯을 직접 조정했다. 2026년 기준 0.434에 2.5% 상대 하향을 적용해 0.42315로 제안했다."
        },
        {
          "Country": "Italy",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.422,
          "proposedValue": 0.41145,
          "rationale": "2027년 Gas 비중 기준값 0.422에 대해 1년 영향의 잔여 절반을 반영한 2.5% 상대 하향으로 0.41145를 산정했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.323,
          "proposedValue": 0.314925,
          "rationale": "아시아 LNG 구매국의 2026년 Gas 발전 비중 기준값 0.323에 대해 PowerMix 조정 수요 감소를 보수적으로 2.5% 상대 하향 반영했다."
        },
        {
          "Country": "Japan",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.318,
          "proposedValue": 0.31005,
          "rationale": "2027년 기준값 0.318에 잔여 영향 기간의 가스 발전 축소를 적용해 0.31005로 낮췄다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.31818965517241377,
          "proposedValue": 0.3102349137931034,
          "rationale": "2026년 Netherlands Gas 비중 기준값 0.31818965517241377에 대해 연간 절반 노출에 해당하는 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Netherlands",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.33707317073170734,
          "proposedValue": 0.32864634146341465,
          "rationale": "2027년 기준값 0.33707317073170734를 대상으로 잔여 영향 기간의 PowerMix 조정을 반영해 0.32864634146341466으로 산정했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.285,
          "proposedValue": 0.277875,
          "rationale": "아시아 LNG 구매국인 South Korea의 2026년 Gas 비중 기준값 0.285에 2.5% 상대 하향을 적용해 수요 완화 효과를 반영했다."
        },
        {
          "Country": "South Korea",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.265,
          "proposedValue": 0.258375,
          "rationale": "2027년 기준 Gas 비중 0.265에 대해 1년 영향의 잔여 기간을 반영하여 0.258375로 조정했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.213,
          "proposedValue": 0.207675,
          "rationale": "2026년 Spain Gas 발전 비중 기준값 0.213을 대상으로, PowerMix 조정에 따른 가스 수요 감소를 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "Spain",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.211,
          "proposedValue": 0.205725,
          "rationale": "2027년 기준값 0.211에 대해 잔여 영향 기간의 수요 감축 효과를 적용해 0.205725로 낮췄다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.474,
          "proposedValue": 0.46215,
          "rationale": "Taiwan (China)는 Gas 발전 비중이 높은 아시아 수요국으로, 2026년 기준값 0.474에 2.5% 상대 하향을 적용했다."
        },
        {
          "Country": "Taiwan (China)",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.495,
          "proposedValue": 0.482625,
          "rationale": "2027년 Gas 비중 기준값 0.495에 대해 1년 영향의 잔여 절반을 반영해 0.482625로 산정했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2026,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "2026년 United Kingdom Gas 비중 기준값 0.29에 대해 PowerMix 조정에 따른 가스 발전 축소를 2.5% 상대 하향으로 반영했다."
        },
        {
          "Country": "United Kingdom",
          "Energy Source": "Gas",
          "Year": 2027,
          "basecaseValue": 0.29,
          "proposedValue": 0.28275,
          "rationale": "2027년 기준값도 0.29로 동일하며, 잔여 영향 기간의 수요 감축 효과를 같은 방식으로 반영해 0.28275를 적용했다."
        }
      ]
    }
  ],
  "request_usr_id": null,
  "scenario_group_id": 23,
  "scenario_id": 136,
  "status": "PROPOSED"
}
```


##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.876 | 3.876 | 2625 | 166 | 2791 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 01:50.766 | 110.766 | 12088 | 9573 | 21661 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 03:00.542 | 180.542 | 14410 | 9905 | 24315 |

## 최종 요약

- ERROR_COUNT: 2
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"16": true, "18": true, "22": true, "23": true, "44": true, "45": true, "46": true, "47": true, "48": false, "49": true, "50": true, "51": true, "52": true, "53": true, "54": true, "60": true, "61": true, "64": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- scenario_id=281 elapsed=00:56.958 (56.958s) attempts=2 error=`MIBaseError('[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id=281: Step2 selected slot이 없어 Step3 value proposal LLM 호출을 생략했습니다.')`
- scenario_id=282 elapsed=00:56.764 (56.764s) attempts=2 error=`MIBaseError('[INVALID_REQUEST] 요청이 유효하지 않습니다. - No valid model parameter proposal parameters generated for scenario_id=282: Step2 selected slot이 없어 Step3 value proposal LLM 호출을 생략했습니다.')`

## Parameter Quality Evaluation

### Overall Test Scope

- 대상 파라미터: `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment`
- DB direct/routing 매핑 기준 대상 event_type_l2_id: GDP=`[21]`, PMI=`[21]`, PowerMix=`[5,6,7,8,9,10,17,18,19]`, Temperature=`[6,7]`, LiqUtilAdjustment=`[1,2,4,11,17,18]`
- 샘플링: event_type별 scenario_group 최대 2개, group별 scenario 최대 2개
- 실행 결과: scenario 성공 34건, error 2건, empty recommendation 0건
- 실패 그룹: scenario_group_id=48, event_type_l2_id=19 정책/규제 변화, scenario_id=281/282
- 실패 원인 요약: PowerMix routing 후보는 검증됐지만 Step2에서 selected slot이 0개라 Step3 value proposal을 생략했고 최종 제안 row가 생성되지 않았다.
- 실패 시나리오 context: scenario_id=281은 period=`3개월`, impact_intensity=`보통`, implementation_stage=`시행 확정`, structural_change_yn=`단발적/한시`; scenario_id=282는 period=`1년`, impact_intensity=`큼`, implementation_stage=`시행 확정`, structural_change_yn=`구조적/영구`.
- 실패 매핑 context: event_type_l2_id=19의 PowerMix는 dimension=`impact_intensity (영향 강도)`, mapping_method=`routing`, comment=`전원믹스·탄소규제·발전설비·연료전환 정책처럼 Gas/Coal/원전/재생 비중이 구조적으로 바뀌면 PowerMix 선택`.

### GDP

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터 선정 | PASS | event_type_l2_id=21의 scenario_id=305,306 모두 target_expected_present=YES 및 target_selected_present=YES. | 없음 |
| 2 | slot 정확성 및 유효성 | PASS | GDP slot axis는 `Country`, `Year`; 305는 China/United States 2026, 306은 2026/2027 중심으로 선정. | 이벤트에 명시된 국가 범위가 넓어질 때는 국가 선택 근거를 더 명시하도록 hint 보강 가능 |
| 3 | basecase 기반 slot 개연성 | PASS | Step2 raw_records=141, GDP basecase axis value로 Year 8개가 제공되고 선택 slot에 basecaseValue가 존재. | 없음 |
| 4 | basecase 외 추가 slot 개연성 | N/A | 이번 GDP 제안은 basecase 기반 slot 중심이며 basecase 외 신규 slot 케이스가 보고되지 않음. | 없음 |
| 5 | basecase 외 slot 미선정 타당성 | N/A | 미선정된 basecase 외 slot 평가 대상이 명확히 없음. | 없음 |
| 6 | value 형식 및 추천 개연성 | PASS | GDP value는 소수 비율 형식. 305 China 2026은 0.042 -> 0.045, United States 2026은 0.019 -> 0.02로 이벤트 전망과 동일 형식. | 없음 |
| 7 | basecase 존재 value 변경 적절성 | PASS | basecaseValue가 있는 좌표에서 경기 강도와 전망치를 근거로 제한적 조정. | 없음 |
| 8 | basecase 없는 value 개연성 | N/A | GDP 결과에서 basecaseValue 없는 value는 확인되지 않음. | 없음 |
| 9 | 동일 그룹 dimension별 value 차이 | PASS | 305는 경미/1개월 이하로 제한적 조정, 306은 1년 경기 충격으로 더 넓은 GDP/PMI slot이 선택됨. | 없음 |

### PMI

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터 선정 | PASS | event_type_l2_id=21의 scenario_id=305,306 모두 target_expected_present=YES 및 target_selected_present=YES. | 없음 |
| 2 | slot 정확성 및 유효성 | PASS | PMI slot axis는 `Country`, `Year`, `Month`; 305는 단기 영향으로 1개 월, 306은 장기 충격으로 12개 월이 선택됨. | month 범위가 넓은 케이스는 period와 선택 월의 연결 설명을 더 요구 가능 |
| 3 | basecase 기반 slot 개연성 | PASS | Step2 raw_records=141, PMI basecase axis value로 Month 12개와 Year 4개가 제공됨. | 없음 |
| 4 | basecase 외 추가 slot 개연성 | N/A | PMI 결과는 basecase 기반 slot 중심. | 없음 |
| 5 | basecase 외 slot 미선정 타당성 | N/A | 미선정된 basecase 외 slot 평가 대상이 명확히 없음. | 없음 |
| 6 | value 형식 및 추천 개연성 | PASS | PMI는 지수값 형식. 305 China 2026-07은 경미/중립 영향으로 49.5 유지. | 없음 |
| 7 | basecase 존재 value 변경 적절성 | PASS | basecaseValue가 있는 PMI 좌표에서 단기 중립 시 유지, 장기 충격 시 다수 월 조정. | 없음 |
| 8 | basecase 없는 value 개연성 | N/A | PMI 결과에서 basecaseValue 없는 value는 확인되지 않음. | 없음 |
| 9 | 동일 그룹 dimension별 value 차이 | PASS | 305는 1개 PMI value, 306은 PMI 12개 value로 period/강도 차이가 반영됨. | 없음 |

### PowerMix

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터 선정 | FAIL | 대부분 event_type에서는 선정됐지만 scenario_id=289는 PowerMix target_expected_present=YES인데 target_selected_present=NO. event_type_l2_id=19의 scenario_id=281/282는 PowerMix routing 후보 검증 후 Step2 selected slot=0으로 최종 error. | Step2에서 direct/routing으로 선정된 후보는 최소 1개 slot을 선택하도록 prompt 및 validation 보강 필요 |
| 2 | slot 정확성 및 유효성 | REVIEW | 성공 케이스는 Year/Country/Energy Source 축이 유효하나, event_type 19는 basecase 후보 57건이 있었는데 slot을 전혀 고르지 못함. | 정책/규제 변화의 PowerMix mapping comment에 적용 Energy Source, 국가/연도 선택 기준을 추가 권장 |
| 3 | basecase 기반 slot 개연성 | REVIEW | PowerMix 성공 케이스는 basecase 기반으로 선정됐으나 281/282는 basecase가 있음에도 selected slot=0. | Step2 slot 미선정 시 candidate별 fallback slot 또는 conservative slot 선택 규칙 필요 |
| 4 | basecase 외 추가 slot 개연성 | N/A | 이번 PowerMix 결과는 대부분 basecase 기반 slot. | 없음 |
| 5 | basecase 외 slot 미선정 타당성 | N/A | 주요 실패는 basecase 외 slot 문제가 아니라 basecase 존재 후보에서 slot 미선정. | 없음 |
| 6 | value 형식 및 추천 개연성 | REVIEW | 성공 케이스는 비율형 PowerMix 값으로 생성됨. 다만 scenario_id=289는 alt_energy_absorption=100%라 PowerMix 조정 없음으로 볼 수 있지만, target_expected_present=YES인 후보가 최종 제안에서 빠짐. | 후보를 제외해야 하는 경우 Step2/Step3 rationale에 `변경 없음` 또는 `미제안 사유`를 남기도록 보강 |
| 7 | basecase 존재 value 변경 적절성 | PASS | event_type 5/7/8/9/10/18 성공 케이스에서 basecaseValue를 기준으로 상하 조정. | 없음 |
| 8 | basecase 없는 value 개연성 | N/A | PowerMix 결과에서 basecaseValue 없는 value는 주요 이슈로 확인되지 않음. | 없음 |
| 9 | 동일 그룹 dimension별 value 차이 | REVIEW | 다수 그룹은 강도/기간이 커질수록 slot/value 수와 변경 폭이 커짐. 단 event_type 19는 두 시나리오 모두 실패해 그룹 내 차이 평가 불가. | event_type 19 재테스트 전 Step2 slot 선정 실패 원인 개선 필요 |

### Temperature

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터 선정 | PASS | event_type_l2_id=6,7의 모든 테스트 시나리오에서 target_expected_present=YES 및 target_selected_present=YES. | 없음 |
| 2 | slot 정확성 및 유효성 | PASS | Temperature slot axis는 `Year`, `Month`, `Country`; 한파/폭염 intensity와 period에 따라 월/연도 slot이 선택됨. | 국가/월 추론 근거는 report evidence 검토가 쉽도록 rationale에 더 구조화 가능 |
| 3 | basecase 기반 slot 개연성 | PASS | Temperature basecase records가 제공되고 선택 slot에 basecaseValue가 존재. | 없음 |
| 4 | basecase 외 추가 slot 개연성 | N/A | 이번 Temperature 결과는 basecase 기반 slot 중심. | 없음 |
| 5 | basecase 외 slot 미선정 타당성 | N/A | 미선정된 basecase 외 slot 평가 대상이 명확히 없음. | 없음 |
| 6 | value 형식 및 추천 개연성 | PASS | value는 섭씨 온도 수치 형식이며 한파는 하향, 폭염은 상향 조정 방향으로 제안됨. | 없음 |
| 7 | basecase 존재 value 변경 적절성 | PASS | scenario_id=289,290,307,308,291,292,317,318에서 basecaseValue 기반으로 proposedValue가 생성됨. | 없음 |
| 8 | basecase 없는 value 개연성 | N/A | Temperature 결과에서 basecaseValue 없는 value는 확인되지 않음. | 없음 |
| 9 | 동일 그룹 dimension별 value 차이 | PASS | 약한/짧은 기상 이벤트보다 강한/장기 이벤트에서 선택 slot과 조정 범위가 확대됨. | 없음 |

### LiqUtilAdjustment

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터 선정 | PASS | event_type_l2_id=1,2,4,11,17,18의 대상 시나리오에서 target_expected_present=YES 및 target_selected_present=YES. | 없음 |
| 2 | slot 정확성 및 유효성 | REVIEW | 대부분 유효하나 slot 수가 큰 케이스가 많음. 예: scenario_id=284 selected slot 90, 286 selected slot 96, 93 selected slot 99. | slot_selection_limits 또는 mapping comment로 국가/시설/기간 선택 범위를 좁히는 기준 보강 권장 |
| 3 | basecase 기반 slot 개연성 | PASS | LiqUtilAdjustment basecase raw_records=21656 기반으로 slot을 선정하고 value 생성. | 없음 |
| 4 | basecase 외 추가 slot 개연성 | N/A | 이번 결과는 basecase 기반 slot 중심. | 없음 |
| 5 | basecase 외 slot 미선정 타당성 | N/A | 미선정된 basecase 외 slot 평가 대상이 명확히 없음. | 없음 |
| 6 | value 형식 및 추천 개연성 | REVIEW | 값은 수치형으로 생성됐으나 대량 slot 케이스에서 실제 영향 범위가 과도할 수 있음. scenario_id=280은 selected slot 84 대비 final value 6개로 축소됨. | Step2와 Step3 사이 value coverage 기준을 report와 validation에 추가 권장 |
| 7 | basecase 존재 value 변경 적절성 | PASS | successful rows에서 basecaseValue를 기준으로 utilization change 방향에 따라 proposedValue가 생성됨. | 없음 |
| 8 | basecase 없는 value 개연성 | N/A | LiqUtilAdjustment 결과에서 basecaseValue 없는 value는 주요 이슈로 확인되지 않음. | 없음 |
| 9 | 동일 그룹 dimension별 value 차이 | PASS | 단기/미세 케이스보다 장기/대규모 케이스에서 slot 및 value 수가 크게 증가함. | 없음 |

### Improvement Backlog

| Priority | Area | Finding | Suggested Change |
|---:|---|---|---|
| 1 | PowerMix Step2 slot selection | event_type_l2_id=19 scenario_id=281/282에서 routing 후보가 검증됐지만 selected slot=0으로 실패. | Step2 prompt에 direct/routing validated candidate는 최소 1개 slot 선택해야 한다는 규칙을 강화하고, value 변경이 어려우면 보수적 basecase 유지 slot을 선택하도록 명시. |
| 2 | PowerMix mapping comment | 정책/규제 변화 mapping은 PowerMix 선택 조건은 있으나 실제 slot 축 선택 기준이 부족함. | comment 또는 parameter hint에 정책/규제의 전원믹스 반영 시 `Energy Source=Gas`, 영향 국가/연도/기간 선정 기준을 추가. |
| 3 | No-change handling | scenario_id=289처럼 PowerMix 후보가 있으나 대체 전원 100% 흡수로 최종 제안이 빠질 수 있음. | 후보 제외가 의도라면 final proposal에 미제안 사유를 남기거나, selected=false 보정 사유를 report에 표시. |
| 4 | LiqUtilAdjustment scope control | selected slot이 80~99개까지 확대되는 케이스가 있음. | Step2 slot_selection_limits를 parameter별로 더 엄격하게 설정하거나, mapping comment에 시설/국가/기간 top-N 선택 기준 추가. |
| 5 | Report coverage | error scenario는 raw result가 없어 group-level mapping/context가 비어 보임. | 실패 시에도 DB-loaded scenario, event, dimension mapping context를 report에 남기도록 evaluate script 보강. |
