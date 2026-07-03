# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-03T21:53:41
- 실행 종료: 2026-07-03T22:00:51
- 총 소요시간: 07:10.112 (430.112s)
- 대상 event_type_l2_ids: [1]
- concurrency: 2
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=1 Upstream Utilization 변동: scenario_group 1개, scenario 2개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 1 | 49 | 283 | OK | 1 | 04:49.648 | 289.648s |
| 1 | 49 | 284 | OK | 1 | 07:02.111 | 422.111s |

## 호출 결과

### event_type_l2_id=1 Upstream Utilization 변동

- scenario_group_id: 49
- group_title: [model_parameter_agent_test] Upstream Utilization 변동 추가 검증
- 대상 scenario_ids: [283, 284]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=283 [model_parameter_agent_test] 단기 미세 감산과 대체 공급 충분

- 소요시간: 04:49.648 (289.648s)
- attempt: 1
- db_loaded_context: `{"dimension_template": [{"dim_key": "period", "label": "기간", "required": true, "value_count": 7}, {"dim_key": "utilization_change_amount", "label": "Utilization 변화 폭", "required": true, "value_count": 5}, {"dim_key": "onset_pattern", "label": "발생 패턴", "required": false, "value_count": 2}, {"dim_key": "recovery_pattern", "label": "회복 패턴", "required": false, "value_count": 3}, {"dim_key": "alt_gas_supply_availability", "label": "대체 가스 공급 가능성", "required": false, "value_count": 5}], "event": {"created_at": "2026-06-19T23:00:44.261593", "detail_analysis_chars": 1057, "detail_analysis_preview": "사건 요약:\n노르웨이 석유업계와 Styrke, Lederne, Safe 등 3개 노조가 오슬로에서 이틀간 국가 중재 임금 협상에 들어가며 파업 방지에 나선 상황임. 오프쇼어 노르웨이는 6월 3일 협상 결렬 시 6월 5일부터 해상 석유·가스 생산이 하루 약 4만5,500배럴(석유환산 기준), 초기 약 1% 감소할 수 있다고 밝힘. 노조 자료 기준 협상 대상 약 8,100명 중 617명이 1차 파업에 참여할 예정이며 전체 해상 석유·가스 노동자의 약 8% 수준임. 이번 업데이트는 파업 위협이 유지되는 가운데 잠재 생산 감소 규모와 초기 영향 자산이 구체화된 상태임.\n\n영향 경로:\n초기 영향 대상으로 스타트피오르 A, 울라, 드라우겐, 에코피스크 등이 제시됨. 파업이 실행될 경우 노르웨이 해상 upstream 생산 감소가 발생하고, 이는 유럽향 파이프라인 가스 공급 안정성에 대한 리스크로 연결될 수 있음. 현재 제시된 감소 규모는 하루 약 4만5,500배럴(석유환산 기준), 초기 약 1%", "event_title_ko": "노르웨이 해상 파업 시 생산 1% 감소 위험", "event_type_l2_id": 1, "key_bullet_count": 0, "key_bullets": [], "latest_record_first_created": "2026-06-03T08:55:57", "mi_event_id": "1117", "occurred_at": "", "oldest_record_first_created": "", "one_line_summary": "[노르웨이 가스 공급] 6월 5일 파업 위협 지속 → 유럽...`
- dimension_values: `{"alt_gas_supply_availability": "100%", "onset_pattern": "점진", "period": "1개월 이하", "recovery_pattern": "급격", "utilization_change_amount": "<5%"}`
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
| Step2 selected slot | 32 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=14, basecaseValue_present=13 | FAIL |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:11.560 | 11.560 | 3746 | 639 | 4385 |
| Step2 slot proposal | True |  | 02:21.852 | 141.852 | 13633 | 14372 | 28005 |
| Step3 value proposal | True |  | 01:44.237 | 104.237 | 24083 | 7126 | 31209 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1117,
    "modelParamProposalId": 43,
    "proposalParameters": [
      {
        "modelTarget": {
          "modelFile": "Supply",
          "modelSheet": "VolumeAdjustment",
          "slotAxesFieldNames": [
            "Year",
            "Province"
          ],
          "tableName": "table1",
          "valueFieldNames": [
            "SupplyDisruption"
          ]
        },
        "parameterName": "SupplyDisruption",
        "rationale": "노르웨이 upstream 설비 파업 위험으로 생산 감소가 발생할 수 있고, 시나리오의 Utilization 변화 폭이 단기 소폭 감소로 제시되어 Province 단위 공급 차질 입력인 SupplyDisruption이 적합합니다.",
        "values": [
          {
            "Province": "Norway",
            "Year": 2026,
            "basecaseValue": null,
            "proposedValue": 0.0008333333,
            "rationale": "이벤트의 영향 대상이 노르웨이 해상 upstream 생산이며, 선택된 입력 축이 2026년 Norway입니다. 이벤트에 제시된 초기 생산 감소 1%를 사용하고, 기간이 1개월 이하이므로 연간 입력값으로 1%의 1/12인 0.0833%를 소수 비율 0.0008333333으로 반영했습니다. 대체 가스 공급 가능성 100%는 별도의 대체 공급 가동률 상향 후보에서 반영합니다."
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
        "rationale": "대체 가스 공급 가능성이 100%로 제시되어 있고, 노르웨이 파이프라인 가스 차질 시 LNG 대체 조달로 일부 전이될 수 있으므로 운영 중 액화설비 가동률 override 입력인 LiqUtilAdjustment가 적합합니다.",
        "values": [
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL1Z",
            "LNG Plant Train": "Arzew GL1Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 7.9,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.20018404907975457,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL2Z",
            "LNG Plant Train": "Arzew GL2Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 8.4,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.20018404907975457,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.81,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.01,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.01,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
          },
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
            "proposedValue": 0.9071397151184897,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
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
            "proposedValue": 0.9071397151184897,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
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
            "proposedValue": 0.9071397151184897,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Freeport LNG",
            "LNG Plant Train": "Freeport LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 5.1,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.9887457459032463,
            "proposedValue": 0.9987457459032463,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
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
            "proposedValue": 0.9967723949850288,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
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
            "proposedValue": 0.994798850195059,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
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
            "proposedValue": 0.988,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
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
            "basecaseValue": 0.9886406459054535,
            "proposedValue": 0.9986406459054535,
            "rationale": "선택된 대체 LNG 공급 설비 중 2026년 7월 basecase 가동률이 1 미만인 운영 중 설비입니다. 대체 가스 공급 가능성 100%와 단기 소폭 차질을 반영해 basecase 가동률에 0.01을 더한 override 값으로 산정했습니다."
          }
        ]
      }
    ],
    "scenarioGroupId": 49,
    "scenarioId": 283
  },
  "message": "model parameter proposal completed",
  "status": "success"
}
```

</details>

#### scenario_id=284 [model_parameter_agent_test] 6개월 큰 감산과 대체 공급 제한

- 소요시간: 07:02.111 (422.111s)
- attempt: 1
- db_loaded_context: `{"dimension_template": [{"dim_key": "period", "label": "기간", "required": true, "value_count": 7}, {"dim_key": "utilization_change_amount", "label": "Utilization 변화 폭", "required": true, "value_count": 5}, {"dim_key": "onset_pattern", "label": "발생 패턴", "required": false, "value_count": 2}, {"dim_key": "recovery_pattern", "label": "회복 패턴", "required": false, "value_count": 3}, {"dim_key": "alt_gas_supply_availability", "label": "대체 가스 공급 가능성", "required": false, "value_count": 5}], "event": {"created_at": "2026-06-19T23:00:44.261593", "detail_analysis_chars": 1057, "detail_analysis_preview": "사건 요약:\n노르웨이 석유업계와 Styrke, Lederne, Safe 등 3개 노조가 오슬로에서 이틀간 국가 중재 임금 협상에 들어가며 파업 방지에 나선 상황임. 오프쇼어 노르웨이는 6월 3일 협상 결렬 시 6월 5일부터 해상 석유·가스 생산이 하루 약 4만5,500배럴(석유환산 기준), 초기 약 1% 감소할 수 있다고 밝힘. 노조 자료 기준 협상 대상 약 8,100명 중 617명이 1차 파업에 참여할 예정이며 전체 해상 석유·가스 노동자의 약 8% 수준임. 이번 업데이트는 파업 위협이 유지되는 가운데 잠재 생산 감소 규모와 초기 영향 자산이 구체화된 상태임.\n\n영향 경로:\n초기 영향 대상으로 스타트피오르 A, 울라, 드라우겐, 에코피스크 등이 제시됨. 파업이 실행될 경우 노르웨이 해상 upstream 생산 감소가 발생하고, 이는 유럽향 파이프라인 가스 공급 안정성에 대한 리스크로 연결될 수 있음. 현재 제시된 감소 규모는 하루 약 4만5,500배럴(석유환산 기준), 초기 약 1%", "event_title_ko": "노르웨이 해상 파업 시 생산 1% 감소 위험", "event_type_l2_id": 1, "key_bullet_count": 0, "key_bullets": [], "latest_record_first_created": "2026-06-03T08:55:57", "mi_event_id": "1117", "occurred_at": "", "oldest_record_first_created": "", "one_line_summary": "[노르웨이 가스 공급] 6월 5일 파업 위협 지속 → 유럽...`
- dimension_values: `{"alt_gas_supply_availability": "25%", "onset_pattern": "급격", "period": "6개월", "recovery_pattern": "점진", "utilization_change_amount": "60%"}`
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
| Step2 selected slot | 79 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=77, basecaseValue_present=76 | FAIL |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:08.790 | 8.790 | 3745 | 458 | 4203 |
| Step2 slot proposal | True |  | 03:22.790 | 202.790 | 13464 | 21823 | 35287 |
| Step3 value proposal | True |  | 03:02.764 | 182.764 | 28532 | 17447 | 45979 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1117,
    "modelParamProposalId": 44,
    "proposalParameters": [
      {
        "modelTarget": {
          "modelFile": "Supply",
          "modelSheet": "VolumeAdjustment",
          "slotAxesFieldNames": [
            "Year",
            "Province"
          ],
          "tableName": "table1",
          "valueFieldNames": [
            "SupplyDisruption"
          ]
        },
        "parameterName": "SupplyDisruption",
        "rationale": "공급 이벤트가 노르웨이 upstream utilization 감소이며, 시나리오가 생산 차질 폭과 대체 공급 제한을 명시하므로 Province 단위 공급 차질 입력인 SupplyDisruption을 선택했습니다.",
        "values": [
          {
            "Province": "Norway",
            "Year": 2026,
            "basecaseValue": null,
            "proposedValue": 0.1125,
            "rationale": "노르웨이 upstream 생산 차질이 2026년 7월부터 6개월간 이어지는 시나리오이므로 2026년 Norway 연간 좌표를 선택했습니다. Utilization 변화 폭 60%에 대체 가스 공급 가능성 25%를 차감한 순차질 45%를 적용했습니다. 급격 발생 후 6개월간 점진 회복되는 월별 강도를 평균 50%로 보고, 6개월 영향기간을 연간 값으로 환산해 45% × 50% × 6/12 = 11.25%로 산정했습니다."
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
        "rationale": "노르웨이 파이프라인 가스 차질이 유럽의 LNG 대체 조달 수요로 전이될 수 있고, 시나리오가 대체 가스 공급 가능성을 25%로 명시하므로 연결 가능한 액화설비 가동률 override 입력인 LiqUtilAdjustment를 선택했습니다.",
        "values": [
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL1Z",
            "LNG Plant Train": "Arzew GL1Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 7.9,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.39263803681,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL1Z",
            "LNG Plant Train": "Arzew GL1Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 7.9,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.352147239264,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL1Z",
            "LNG Plant Train": "Arzew GL1Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 7.9,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.311656441718,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL1Z",
            "LNG Plant Train": "Arzew GL1Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 7.9,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.271165644172,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL1Z",
            "LNG Plant Train": "Arzew GL1Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 7.9,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.230674846626,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL1Z",
            "LNG Plant Train": "Arzew GL1Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 7.9,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.19018404908,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL2Z",
            "LNG Plant Train": "Arzew GL2Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 8.4,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.39263803681,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL2Z",
            "LNG Plant Train": "Arzew GL2Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 8.4,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.352147239264,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL2Z",
            "LNG Plant Train": "Arzew GL2Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 8.4,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.311656441718,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL2Z",
            "LNG Plant Train": "Arzew GL2Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 8.4,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.271165644172,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL2Z",
            "LNG Plant Train": "Arzew GL2Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 8.4,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.230674846626,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL2Z",
            "LNG Plant Train": "Arzew GL2Z T1-T6",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 8.4,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.19018404907975456,
            "proposedValue": 0.19018404908,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. basecase가 이미 100% 수준이므로 대체 공급 강도를 적용해도 상한 100%로 제한했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. basecase가 이미 100% 수준이므로 대체 공급 강도를 적용해도 상한 100%로 제한했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. basecase가 이미 100% 수준이므로 대체 공급 강도를 적용해도 상한 100%로 제한했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. basecase가 이미 100% 수준이므로 대체 공급 강도를 적용해도 상한 100%로 제한했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. basecase가 이미 100% 수준이므로 대체 공급 강도를 적용해도 상한 100%로 제한했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. basecase가 이미 100% 수준이므로 상한 100%를 유지했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.85,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.84,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.83,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.82,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.25,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 25% 가동률로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.2,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도 20%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.15,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도 15%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.1,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도 10%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.05,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도 5%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.25,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 25% 가동률로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.2,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도 20%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.15,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도 15%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.1,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도 10%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.05,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도 5%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.25,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 25% 가동률로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.2,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도 20%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.15,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도 15%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.1,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도 10%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.05,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도 5%를 가동률 override로 산정했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7420234122042342,
            "proposedValue": 0.806517559153,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T1",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.7359392278953923,
            "proposedValue": 0.788751382316,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T1",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.7718854296388543,
            "proposedValue": 0.806102615193,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T1",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.7344876712328768,
            "proposedValue": 0.76103890411,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T1",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.7270535491905354,
            "proposedValue": 0.740700871731,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T1",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.7808448318804485,
            "proposedValue": 0.78084483188,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T2",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7420234122042342,
            "proposedValue": 0.806517559153,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T2",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.7359392278953923,
            "proposedValue": 0.788751382316,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T2",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.7718854296388543,
            "proposedValue": 0.806102615193,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T2",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.7344876712328768,
            "proposedValue": 0.76103890411,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T2",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.7270535491905354,
            "proposedValue": 0.740700871731,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T2",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.7808448318804485,
            "proposedValue": 0.78084483188,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T3",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7282220743697789,
            "proposedValue": 0.796166555777,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T3",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.7222510534486581,
            "proposedValue": 0.777800842759,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T3",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.7827796259333183,
            "proposedValue": 0.815362682043,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T3",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.7208264951578326,
            "proposedValue": 0.748743845642,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T3",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.7373149996303687,
            "proposedValue": 0.750449249649,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T3",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.7663214312116507,
            "proposedValue": 0.766321431212,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T4",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7193333333333335,
            "proposedValue": 0.7895,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T4",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.713456790123457,
            "proposedValue": 0.770765432099,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T4",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.7732345679012347,
            "proposedValue": 0.807249382716,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T4",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.7120493827160495,
            "proposedValue": 0.740844444444,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T4",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.7283209876543211,
            "proposedValue": 0.741904938272,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T4",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.7569876543209877,
            "proposedValue": 0.756987654321,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T5",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7193333333333335,
            "proposedValue": 0.7895,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T5",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.713456790123457,
            "proposedValue": 0.770765432099,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T5",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.7732345679012347,
            "proposedValue": 0.807249382716,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T5",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.7120493827160495,
            "proposedValue": 0.740844444444,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T5",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.7283209876543211,
            "proposedValue": 0.741904938272,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T5",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.7569876543209877,
            "proposedValue": 0.756987654321,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T6",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 0.7193333333333335,
            "proposedValue": 0.7895,
            "rationale": "2026년 7월 해당 액화설비 basecase record가 제공되어 선택했습니다. 대체 공급 가능성 25%를 7월 가동률 여유분에 적용해 basecase + 25% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T6",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 104,
            "Year": 2026,
            "basecaseValue": 0.713456790123457,
            "proposedValue": 0.770765432099,
            "rationale": "2026년 8월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 8월 대체 공급 강도를 20%로 낮추고 basecase + 20% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T6",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 105,
            "Year": 2026,
            "basecaseValue": 0.7732345679012347,
            "proposedValue": 0.807249382716,
            "rationale": "2026년 9월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 9월 대체 공급 강도를 15%로 낮추고 basecase + 15% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T6",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 106,
            "Year": 2026,
            "basecaseValue": 0.7120493827160495,
            "proposedValue": 0.740844444444,
            "rationale": "2026년 10월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 10월 대체 공급 강도를 10%로 낮추고 basecase + 10% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T6",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 107,
            "Year": 2026,
            "basecaseValue": 0.7283209876543211,
            "proposedValue": 0.741904938272,
            "rationale": "2026년 11월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복을 반영해 11월 대체 공급 강도를 5%로 낮추고 basecase + 5% × (1-basecase)로 산정했습니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T6",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 108,
            "Year": 2026,
            "basecaseValue": 0.7569876543209877,
            "proposedValue": 0.756987654321,
            "rationale": "2026년 12월 해당 액화설비 basecase record가 제공되어 선택했습니다. 점진 회복의 마지막 월로 대체 공급 추가 강도를 0%로 두어 basecase 수준을 유지했습니다."
          }
        ]
      }
    ],
    "scenarioGroupId": 49,
    "scenarioId": 284
  },
  "message": "model parameter proposal completed",
  "status": "success"
}
```

</details>

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"49": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.
