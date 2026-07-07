# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-07T15:30:50
- 실행 종료: 2026-07-07T15:32:42
- 총 소요시간: 01:51.759 (111.759s)
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
| 21 | 60 | 305 | OK | 1 | 01:13.458 | 73.458s |
| 21 | 60 | 306 | OK | 1 | 01:45.022 | 105.022s |

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

- 소요시간: 01:13.458 (73.458s)
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
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 1 | 강도 차원의 '경미'는 산업 수요의 단기 심리·제조업 변동을 PMI로 반영하는 parameter 성격과 직접 연결된다. 기간은 '1개월 이하'로 매우 짧아 월별 PMI에 한정하고, 수요 영향은 거의 흡수되는 시나리오이므로 큰 하향 조정보다는 제한적인 단기 둔화만 반영한다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 2 | 강도 차원의 '경미'는 국가별 경기 경로를 GDP 변화율로 반영하는 parameter 성격과 연결된다. 다만 기간이 '1개월 이하'이고 시나리오상 LNG 수요 영향이 제한적이므로 구조적 성장률을 크게 훼손하기보다는, 이벤트에 명시된 국가별 2026년 성장률 전망을 보수적으로 반영하는 방식으로 제안한다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 49.3 | 해당 좌표는 선택된 중국 2026년 7월 PMI 입력값이다. 기준 PMI 49.5가 이미 확장·위축 기준선 아래에 있고 시나리오가 1개월 이하의 경미한 둔화를 전제하므로, 추가 충격은 제한적으로 반영해 최종 PMI를 49.3으로 낮춘다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.045 | 해당 좌표는 선택된 중국 2026년 GDP 변화율 입력값이다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 제시되어 있어, 기준값 0.042 대신 동일한 소수 비율 형식의 최종 입력값 0.045를 적용한다. |
| 2 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.02 | 해당 좌표는 선택된 미국 2026년 GDP 변화율 입력값이다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어 있어, 기준값 0.019에서 소폭 상향한 동일 형식의 최종 입력값 0.02를 적용한다. |

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
  "model_param_proposal_id": 27,
  "proposal_completed_dtm": "2026-07-07 15:32:03.730114",
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
      "rationale": "강도 차원의 '경미'는 산업 수요의 단기 심리·제조업 변동을 PMI로 반영하는 parameter 성격과 직접 연결된다. 기간은 '1개월 이하'로 매우 짧아 월별 PMI에 한정하고, 수요 영향은 거의 흡수되는 시나리오이므로 큰 하향 조정보다는 제한적인 단기 둔화만 반영한다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 49.3,
          "rationale": "해당 좌표는 선택된 중국 2026년 7월 PMI 입력값이다. 기준 PMI 49.5가 이미 확장·위축 기준선 아래에 있고 시나리오가 1개월 이하의 경미한 둔화를 전제하므로, 추가 충격은 제한적으로 반영해 최종 PMI를 49.3으로 낮춘다."
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
      "rationale": "강도 차원의 '경미'는 국가별 경기 경로를 GDP 변화율로 반영하는 parameter 성격과 연결된다. 다만 기간이 '1개월 이하'이고 시나리오상 LNG 수요 영향이 제한적이므로 구조적 성장률을 크게 훼손하기보다는, 이벤트에 명시된 국가별 2026년 성장률 전망을 보수적으로 반영하는 방식으로 제안한다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.045,
          "rationale": "해당 좌표는 선택된 중국 2026년 GDP 변화율 입력값이다. 이벤트에서 중국 2026년 성장률 전망이 4.5%로 제시되어 있어, 기준값 0.042 대신 동일한 소수 비율 형식의 최종 입력값 0.045를 적용한다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.02,
          "rationale": "해당 좌표는 선택된 미국 2026년 GDP 변화율 입력값이다. 이벤트에서 미국 2026년 성장률 전망이 2.0%로 제시되어 있어, 기준값 0.019에서 소폭 상향한 동일 형식의 최종 입력값 0.02를 적용한다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:04.323 | 4.323 | 2432 | 122 | 2554 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:20.771 | 20.771 | 5364 | 1220 | 6584 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:15.839 | 15.839 | 6185 | 1135 | 7320 |

#### scenario_id=306 [model_parameter_agent_test] 1년 경기 충격과 수요 감소

- 소요시간: 01:45.022 (105.022s)
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
| 1 | PMI | `{"modelFile": "Demand", "modelSheet": "PMIAdjustment", "tableName": "table1"}` | `["Country", "Year", "Month"]` | `["PMI"]` | 12 | 강도 차원의 '경기 충격'은 parameter_hint상 국가·연월별 제조업 PMI를 통해 산업 수요의 단기 변동을 반영하는 입력과 직접 연결된다. 기간 차원의 '1년'은 적용 월 범위를 정하는 보조 축으로 사용하고, LNG 수요 영향 규모 '25%'는 직접 수요 조정 대신 PMI 하향 강도를 정하는 보조 근거로 반영했다. 제안값은 1년 충격 기간의 중국 월별 PMI를 경기 위축 국면으로 하향 조정하되, 동일 기간 내 월별 충격 강도는 균등하게 적용하는 구조다. |
| 2 | GDP | `{"modelFile": "Demand", "modelSheet": "GDPPopulationAdjustment", "tableName": "table1"}` | `["Country", "Year"]` | `["% change (+/-)"]` | 4 | 강도 차원의 '경기 충격'은 parameter_hint상 국가·연도별 실질 GDP 변화율 조정과 직접 연결되며, 산업심리보다 구조적인 경기 경로 변화를 반영하는 입력으로 사용된다. 기간 차원의 '1년'은 연간 GDP 슬롯에 충격을 배분하는 기준으로 사용하고, LNG 수요 영향 규모 '25%'는 직접 수요 조정 대신 GDP 성장률 하향 강도의 보조 근거로 반영했다. 제안값은 2026년 7월부터 2027년 6월까지의 1년 충격이 두 개의 연간 입력에 걸쳐 나타나는 점을 고려해, 선택된 국가·연도별 성장률을 부분 연도 가중 방식으로 하향 조정하는 구조다. |

##### Proposed Parameter Values

###### Proposed Values - PMI

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Month": 7, "Year": 2026}` | 49.5 | 37.125 | 해당 좌표는 1년 경기 충격이 시작되는 2026년 7월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 LNG 수요 영향 규모 25%를 단기 산업심리 충격 강도로 적용해 49.5 × (1 - 0.25) = 37.125로 산정했다. |
| 2 | `{"Country": "China", "Month": 8, "Year": 2026}` | 49.5 | 37.125 | 해당 좌표는 충격 기간 내 2026년 8월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 25% 하향 충격을 동일하게 적용해 최종 입력값을 37.125로 산정했다. |
| 3 | `{"Country": "China", "Month": 9, "Year": 2026}` | 49.5 | 37.125 | 해당 좌표는 충격 기간 내 2026년 9월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 25% 하향 충격을 적용해 49.5 × 0.75 = 37.125로 산정했다. |
| 4 | `{"Country": "China", "Month": 10, "Year": 2026}` | 49.5 | 37.125 | 해당 좌표는 충격 기간 내 2026년 10월 중국 PMI 입력에 해당한다. 기준 PMI 49.5를 수요 둔화 강도 25%만큼 낮춰 최종 입력값을 37.125로 산정했다. |
| 5 | `{"Country": "China", "Month": 11, "Year": 2026}` | 49.5 | 37.125 | 해당 좌표는 충격 기간 내 2026년 11월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 경기 충격 강도를 반영한 25% 하향을 적용해 37.125로 산정했다. |
| 6 | `{"Country": "China", "Month": 12, "Year": 2026}` | 49.5 | 37.125 | 해당 좌표는 충격 기간 내 2026년 12월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 1년 수요 둔화 시나리오의 월별 충격을 반영해 최종 입력값을 37.125로 산정했다. |
| 7 | `{"Country": "China", "Month": 1, "Year": 2027}` | null | 37.125 | 해당 좌표는 2026년 7월부터 이어지는 1년 충격 기간에 포함되는 2027년 1월 중국 PMI 입력이다. 선택된 기간 내 월별 충격 강도를 동일하게 유지하기 위해 2026년 충격 월의 산정 방식과 같은 PMI 37.125를 최종 입력값으로 제안했다. |
| 8 | `{"Country": "China", "Month": 2, "Year": 2027}` | null | 37.125 | 해당 좌표는 충격 기간 내 2027년 2월 중국 PMI 입력이다. 1년 경기 충격이 지속되는 월로 보아 25% 수요 둔화 강도를 월별 PMI 하향 수준으로 동일 적용해 37.125로 산정했다. |
| 9 | `{"Country": "China", "Month": 3, "Year": 2027}` | null | 37.125 | 해당 좌표는 충격 기간 내 2027년 3월 중국 PMI 입력이다. 충격이 완화됐다는 별도 근거가 없으므로 1년 기간 중 동일한 경기 위축 수준을 적용해 최종 입력값을 37.125로 제안했다. |
| 10 | `{"Country": "China", "Month": 4, "Year": 2027}` | null | 37.125 | 해당 좌표는 충격 기간 내 2027년 4월 중국 PMI 입력이다. 1년 지속 시나리오에 맞춰 월별 PMI 하향 강도를 유지하고, 25% 수요 영향 규모를 반영한 37.125를 최종 입력값으로 산정했다. |
| 11 | `{"Country": "China", "Month": 5, "Year": 2027}` | null | 37.125 | 해당 좌표는 충격 기간 내 2027년 5월 중국 PMI 입력이다. 기간 중 충격 강도를 균등하게 적용하는 원칙에 따라 PMI를 37.125로 제안했다. |
| 12 | `{"Country": "China", "Month": 6, "Year": 2027}` | null | 37.125 | 해당 좌표는 1년 경기 충격의 마지막 월에 해당하는 2027년 6월 중국 PMI 입력이다. 충격 종료 전까지 동일한 월별 수요 둔화 강도를 유지해 최종 입력값을 37.125로 산정했다. |

###### Proposed Values - GDP

| No | slot coordinates | basecaseValue | proposedValue | rationale |
|---:|---|---:|---:|---|
| 1 | `{"Country": "China", "Year": 2026}` | 0.042 | 0.03675 | 해당 좌표는 2026년 중국 GDP 변화율 입력이며, 충격 기간 중 2026년에 해당하는 하반기 6개월만 반영되는 연간 슬롯이다. 기준값 0.042에 25% 충격의 절반인 12.5% 하향을 적용해 0.042 × (1 - 0.125) = 0.03675로 산정했다. |
| 2 | `{"Country": "China", "Year": 2027}` | 0.042 | 0.03675 | 해당 좌표는 2027년 중국 GDP 변화율 입력이며, 충격 기간 중 2027년에 해당하는 상반기 6개월만 반영되는 연간 슬롯이다. 기준값 0.042에 반년 가중 충격 12.5%를 적용해 최종 입력값을 0.03675로 산정했다. |
| 3 | `{"Country": "United States", "Year": 2026}` | 0.019 | 0.016625 | 해당 좌표는 2026년 미국 GDP 변화율 입력이며, 1년 충격 중 2026년 하반기만 연간 값에 반영되는 슬롯이다. 기준값 0.019에 25% 충격을 반년만 반영한 12.5% 하향을 적용해 0.019 × (1 - 0.125) = 0.016625로 산정했다. |
| 4 | `{"Country": "United States", "Year": 2027}` | 0.02 | 0.0175 | 해당 좌표는 2027년 미국 GDP 변화율 입력이며, 충격 기간 중 2027년 상반기만 연간 값에 포함되는 슬롯이다. 기준값 0.02에 반년 가중 충격 12.5%를 적용해 0.02 × 0.875 = 0.0175로 산정했다. |

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
  "model_param_proposal_id": 28,
  "proposal_completed_dtm": "2026-07-07 15:32:42.028836",
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
      "rationale": "강도 차원의 '경기 충격'은 parameter_hint상 국가·연월별 제조업 PMI를 통해 산업 수요의 단기 변동을 반영하는 입력과 직접 연결된다. 기간 차원의 '1년'은 적용 월 범위를 정하는 보조 축으로 사용하고, LNG 수요 영향 규모 '25%'는 직접 수요 조정 대신 PMI 하향 강도를 정하는 보조 근거로 반영했다. 제안값은 1년 충격 기간의 중국 월별 PMI를 경기 위축 국면으로 하향 조정하되, 동일 기간 내 월별 충격 강도는 균등하게 적용하는 구조다.",
      "values": [
        {
          "Country": "China",
          "Month": 7,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 1년 경기 충격이 시작되는 2026년 7월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 LNG 수요 영향 규모 25%를 단기 산업심리 충격 강도로 적용해 49.5 × (1 - 0.25) = 37.125로 산정했다."
        },
        {
          "Country": "China",
          "Month": 8,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2026년 8월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 25% 하향 충격을 동일하게 적용해 최종 입력값을 37.125로 산정했다."
        },
        {
          "Country": "China",
          "Month": 9,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2026년 9월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 25% 하향 충격을 적용해 49.5 × 0.75 = 37.125로 산정했다."
        },
        {
          "Country": "China",
          "Month": 10,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2026년 10월 중국 PMI 입력에 해당한다. 기준 PMI 49.5를 수요 둔화 강도 25%만큼 낮춰 최종 입력값을 37.125로 산정했다."
        },
        {
          "Country": "China",
          "Month": 11,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2026년 11월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 경기 충격 강도를 반영한 25% 하향을 적용해 37.125로 산정했다."
        },
        {
          "Country": "China",
          "Month": 12,
          "Year": 2026,
          "basecaseValue": 49.5,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2026년 12월 중국 PMI 입력에 해당한다. 기준 PMI 49.5에 1년 수요 둔화 시나리오의 월별 충격을 반영해 최종 입력값을 37.125로 산정했다."
        },
        {
          "Country": "China",
          "Month": 1,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 2026년 7월부터 이어지는 1년 충격 기간에 포함되는 2027년 1월 중국 PMI 입력이다. 선택된 기간 내 월별 충격 강도를 동일하게 유지하기 위해 2026년 충격 월의 산정 방식과 같은 PMI 37.125를 최종 입력값으로 제안했다."
        },
        {
          "Country": "China",
          "Month": 2,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2027년 2월 중국 PMI 입력이다. 1년 경기 충격이 지속되는 월로 보아 25% 수요 둔화 강도를 월별 PMI 하향 수준으로 동일 적용해 37.125로 산정했다."
        },
        {
          "Country": "China",
          "Month": 3,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2027년 3월 중국 PMI 입력이다. 충격이 완화됐다는 별도 근거가 없으므로 1년 기간 중 동일한 경기 위축 수준을 적용해 최종 입력값을 37.125로 제안했다."
        },
        {
          "Country": "China",
          "Month": 4,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2027년 4월 중국 PMI 입력이다. 1년 지속 시나리오에 맞춰 월별 PMI 하향 강도를 유지하고, 25% 수요 영향 규모를 반영한 37.125를 최종 입력값으로 산정했다."
        },
        {
          "Country": "China",
          "Month": 5,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 충격 기간 내 2027년 5월 중국 PMI 입력이다. 기간 중 충격 강도를 균등하게 적용하는 원칙에 따라 PMI를 37.125로 제안했다."
        },
        {
          "Country": "China",
          "Month": 6,
          "Year": 2027,
          "basecaseValue": null,
          "proposedValue": 37.125,
          "rationale": "해당 좌표는 1년 경기 충격의 마지막 월에 해당하는 2027년 6월 중국 PMI 입력이다. 충격 종료 전까지 동일한 월별 수요 둔화 강도를 유지해 최종 입력값을 37.125로 산정했다."
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
      "rationale": "강도 차원의 '경기 충격'은 parameter_hint상 국가·연도별 실질 GDP 변화율 조정과 직접 연결되며, 산업심리보다 구조적인 경기 경로 변화를 반영하는 입력으로 사용된다. 기간 차원의 '1년'은 연간 GDP 슬롯에 충격을 배분하는 기준으로 사용하고, LNG 수요 영향 규모 '25%'는 직접 수요 조정 대신 GDP 성장률 하향 강도의 보조 근거로 반영했다. 제안값은 2026년 7월부터 2027년 6월까지의 1년 충격이 두 개의 연간 입력에 걸쳐 나타나는 점을 고려해, 선택된 국가·연도별 성장률을 부분 연도 가중 방식으로 하향 조정하는 구조다.",
      "values": [
        {
          "Country": "China",
          "Year": 2026,
          "basecaseValue": 0.042,
          "proposedValue": 0.03675,
          "rationale": "해당 좌표는 2026년 중국 GDP 변화율 입력이며, 충격 기간 중 2026년에 해당하는 하반기 6개월만 반영되는 연간 슬롯이다. 기준값 0.042에 25% 충격의 절반인 12.5% 하향을 적용해 0.042 × (1 - 0.125) = 0.03675로 산정했다."
        },
        {
          "Country": "China",
          "Year": 2027,
          "basecaseValue": 0.042,
          "proposedValue": 0.03675,
          "rationale": "해당 좌표는 2027년 중국 GDP 변화율 입력이며, 충격 기간 중 2027년에 해당하는 상반기 6개월만 반영되는 연간 슬롯이다. 기준값 0.042에 반년 가중 충격 12.5%를 적용해 최종 입력값을 0.03675로 산정했다."
        },
        {
          "Country": "United States",
          "Year": 2026,
          "basecaseValue": 0.019,
          "proposedValue": 0.016625,
          "rationale": "해당 좌표는 2026년 미국 GDP 변화율 입력이며, 1년 충격 중 2026년 하반기만 연간 값에 반영되는 슬롯이다. 기준값 0.019에 25% 충격을 반년만 반영한 12.5% 하향을 적용해 0.019 × (1 - 0.125) = 0.016625로 산정했다."
        },
        {
          "Country": "United States",
          "Year": 2027,
          "basecaseValue": 0.02,
          "proposedValue": 0.0175,
          "rationale": "해당 좌표는 2027년 미국 GDP 변화율 입력이며, 충격 기간 중 2027년 상반기만 연간 값에 포함되는 슬롯이다. 기준값 0.02에 반년 가중 충격 12.5%를 적용해 0.02 × 0.875 = 0.0175로 산정했다."
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
| Step1.5 candidate validation | True | skmidev-gpt-5.5-20260424 | 00:03.702 | 3.702 | 2443 | 135 | 2578 |
| Step2 slot proposal | True | skmidev-gpt-5.5-20260424 | 00:24.647 | 24.647 | 5373 | 1990 | 7363 |
| Step3 value proposal | True | skmidev-gpt-5.5-20260424 | 00:50.288 | 50.288 | 7038 | 3696 | 10734 |

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"60": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.

## GDP Parameter Quality Evaluation

### Evaluation Scope

- target_parameter: `GDP`
- event_type_l2_id: `21` 국가별 경기
- scenario_group_id: `60`
- scenario_ids: `[305, 306]`
- proposal_ids: `[27, 28]`
- DB mapping: `economic_intensity -> GDP`, `mapping_method=direct`
- model target: `Demand / GDPPopulationAdjustment / table1`
- slot axes: `Country`, `Year`
- value field: `% change (+/-)`
- final proposal source: `tmm_mi_model_param_proposal_m.proposal_parameters`

### Criteria Table

| No | Criteria | Judgement | Evidence | Improvement |
|---:|---|---|---|---|
| 1 | 파라미터가 정확히 선정되었나. direct는 필수 선정, route는 반드시 1개 이상 선정 | PASS | scenario 305, 306 모두 expected/selected parameter에 `GDP`가 포함됨. candidate key는 `21\|economicintensity\|gdp\|demand\|gdppopulationadjustment`, mapping은 `direct`. 최종 DB row 27, 28에도 `parameterName=GDP`가 저장됨. | 없음. |
| 2 | slot이 정확히 선정되고 slot의 값이나 범위가 유효한 값인가 | REVIEW | GDP slot 축은 `Country`, `Year`로 맞고, 선택된 국가는 이벤트에 명시된 `China`, `United States`라 유효함. scenario 305는 `2026`만 선택했고, scenario 306은 `2026/2027`을 선택함. scenario 306의 `period=1년`을 `2026년 하반기 + 2027년 상반기`로 해석한 것은 합리적이나 DB dimension 자체에는 시작월 기준이 명시되지 않음. | period 해석 기준을 명시한다. 예: latest record date 또는 이벤트 기준월 이후 12개월을 `1년`으로 보고 연도 슬롯에 배분한다고 prompt/report 규칙화. |
| 3 | slot이 basecase 기반으로 선정된 경우 개연성이 있는가 | PASS | 모든 GDP value에 `basecaseValue`가 있음. scenario 305는 `China 2026`, `United States 2026`, scenario 306은 `China/United States 2026/2027`을 사용했고 모두 GDP basecase 축과 일치함. | 없음. |
| 4 | slot이 basecase에 없지만 시나리오/이벤트 정보를 활용해 추가 선정된 경우 개연성이 있는가 | N/A | GDP 결과는 모두 basecase 기반 value임. basecase 밖 GDP slot은 추가하지 않음. | 없음. |
| 5 | slot이 basecase에 없는 경우를 선정하지 못했다면 선정해도 될 가능성이 없었는가 | PASS | 이벤트에는 글로벌 GDP 전망도 있으나 GDP model target의 slot은 `Country`, `Year`이며 report에는 `China`, `United States` 중심의 국가별 전망이 직접 제시됨. 글로벌/세계 slot이 최종 DB row에 없는 것은 적절함. | 글로벌 GDP를 모델 입력으로 사용하려면 basecase에 `World` 또는 별도 글로벌 GDP parameter/slot을 정의해야 함. |
| 6 | value가 지정된 범위나 형식으로 선정되었나. 시나리오/이벤트 정보와 value 추천 사이에 개연성이 있는가 | REVIEW | value 형식은 decimal growth rate로 적절함. scenario 305는 `China 2026: 0.042 -> 0.045`, `United States 2026: 0.019 -> 0.02`로 이벤트의 2026 국가별 전망과 일치함. scenario 306은 `0.875` multiplier를 적용해 `China 2026/2027: 0.03675`, `US 2026: 0.016625`, `US 2027: 0.0175`로 낮춤. 방향성은 맞지만 `demand_impact=25%`를 GDP 성장률 하향 강도로 직접 해석한 점은 경제적 의미가 불명확함. | GDP value 산정에서 `demand_impact`를 직접 multiplier로 사용하지 말고, GDP 전용 shock table 또는 capped delta 규칙을 둔다. 이벤트에 명시된 국가별 GDP 전망치를 anchor로 삼고 scenario intensity는 보정 계수로 제한 적용한다. |
| 7 | value가 basecase에 있는 경우 적절하게 변경되었나 | REVIEW | scenario 305는 경미/단기 시나리오이지만 2026 이벤트 전망치를 반영한 소폭 상향이라 근거가 명확함. scenario 306은 경기 충격/1년 시나리오에 맞게 모든 GDP value를 하향했으나, 하향 폭이 `basecaseValue * 0.875`로 기계 산정되어 이벤트의 명시 전망치보다 `demand_impact` 차원을 우선한 것으로 보임. | value prompt에 `demand_impact`를 GDP 성장률에 직접 곱하지 말라는 제약을 추가하고, GDP 변경폭 산정 기준을 별도 규칙으로 제공한다. |
| 8 | value가 basecase에 없었던 경우 개연성 있게 선정되었나 | N/A | GDP value는 scenario 305, 306 모두 `basecaseValue`가 존재함. | 없음. |
| 9 | 동일 그룹의 시나리오 사이에 dimension value에 따라 해당 value가 적절한 차이를 보이는가 | PASS | scenario 305 `경미/1개월 이하`는 2026년의 소폭 조정만 제안했고, scenario 306 `경기 충격/1년/25%`는 2026/2027 모두 더 낮은 값을 제안함. 예: China 2026 `0.045 -> 0.03675`, US 2026 `0.02 -> 0.016625`. 강도와 기간 차이에 따른 방향성 차이는 적절함. | 차이의 방향은 적절하나, scenario 306의 수치 산정은 criteria 6, 7 개선사항을 따른다. |

### Findings

- GDP parameter 선정과 DB 저장은 정상 동작했다.
- 새 리포트는 `Final DB Proposal Row`만 남기고 raw API response 중복 JSON은 포함하지 않는다.
- scenario 305는 단기/경미 시나리오에 맞게 2026년 중국/미국 GDP만 제안해 이전보다 더 좁은 slot 선정이 되었고, 이벤트 수치와 직접 연결된다.
- scenario 306은 시나리오 강도에 따라 2026/2027 값을 모두 낮춘 점은 타당하지만, `demand_impact=25%`를 GDP 성장률 multiplier로 쓰는 산식은 개선 대상이다.
