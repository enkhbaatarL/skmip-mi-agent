# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-04T00:05:04
- 실행 종료: 2026-07-04T00:09:58
- 총 소요시간: 04:53.932 (293.932s)
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
| 1 | 49 | 283 | OK | 1 | 04:33.162 | 273.162s |
| 1 | 49 | 284 | OK | 1 | 04:47.064 | 287.064s |

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

- 소요시간: 04:33.162 (273.162s)
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
| Step2 selected slot | 31 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=31, basecaseValue_present=30 | FAIL |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:10.278 | 10.278 | 3746 | 582 | 4328 |
| Step2 slot proposal | True |  | 01:57.926 | 117.926 | 13343 | 11487 | 24830 |
| Step3 value proposal | True |  | 01:54.218 | 114.218 | 14719 | 10924 | 25643 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1117,
    "modelParamProposalId": 45,
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
        "rationale": "노르웨이 해상 upstream 생산 감소가 발생할 수 있어 province 단위 공급 차질을 반영하는 SupplyDisruption이 적합합니다.",
        "values": [
          {
            "Province": "Norway",
            "Year": 2026,
            "basecaseValue": null,
            "proposedValue": 0.01,
            "rationale": "노르웨이 해상 생산 감소 위험이 제시되어 2026년 Norway 좌표를 사용했습니다. 이벤트에 초기 생산 감소가 약 1%로 명시되어 SupplyDisruption 값을 0.01로 설정했습니다. Utilization 변화 폭 '<5%'는 미세 차질 범위로 해석했습니다."
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
        "rationale": "대체 가스 공급 가능성이 100%로 제시되어 인접·시장연결 대체 LNG 공급국의 액화설비 가동률 상향을 반영하는 LiqUtilAdjustment가 적합합니다.",
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
            "rationale": "대체 공급 후보로 선택된 Algeria Arzew GL1Z의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 Algeria Arzew GL2Z의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 1.0100000000000002,
            "rationale": "대체 공급 후보로 선택된 Algeria Arzew GL3Z의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.8099999999999999,
            "rationale": "대체 공급 후보로 선택된 Algeria Skikda GL1K의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 Egypt Damietta LNG의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 Egypt Egyptian LNG (Idku) T1의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.01,
            "rationale": "대체 공급 후보로 선택된 Egypt Egyptian LNG (Idku) T2의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.7520234122042342,
            "rationale": "대체 공급 후보로 선택된 Nigeria NLNG T1의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.7520234122042342,
            "rationale": "대체 공급 후보로 선택된 Nigeria NLNG T2의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.7382220743697789,
            "rationale": "대체 공급 후보로 선택된 Nigeria NLNG T3의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.7293333333333335,
            "rationale": "대체 공급 후보로 선택된 Nigeria NLNG T4의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.7293333333333335,
            "rationale": "대체 공급 후보로 선택된 Nigeria NLNG T5의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 0.7293333333333335,
            "rationale": "대체 공급 후보로 선택된 Nigeria NLNG T6의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
          },
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
            "proposedValue": 1.0577010309278352,
            "rationale": "대체 공급 후보로 선택된 Qatar Qatargas 1 T1의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 1.0577010309278352,
            "rationale": "대체 공급 후보로 선택된 Qatar Qatargas 1 T2의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 1.0577010309278352,
            "rationale": "대체 공급 후보로 선택된 Qatar Qatargas 1 T3의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 1.0576962025316454,
            "rationale": "대체 공급 후보로 선택된 Qatar Qatargas 2 T4의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 1.0576962025316454,
            "rationale": "대체 공급 후보로 선택된 Qatar Qatargas 2 T5의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 1.0576962025316454,
            "rationale": "대체 공급 후보로 선택된 Qatar Qatargas 3 T6의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "proposedValue": 1.0576962025316454,
            "rationale": "대체 공급 후보로 선택된 Qatar Qatargas 4 T7의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Cameron LNG T1의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Cameron LNG T2의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Cameron LNG T3의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Freeport LNG T1의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Freeport LNG T2의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Freeport LNG T3의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Sabine Pass T1-T2의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Sabine Pass LNG",
            "LNG Plant Train": "Sabine Pass T3-T4",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 10,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 1.0065076455302508,
            "proposedValue": 1.0165076455302509,
            "rationale": "대체 공급 후보로 선택된 United States Sabine Pass T3-T4의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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
            "rationale": "대체 공급 후보로 선택된 United States Sabine Pass T5의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Sabine Pass LNG",
            "LNG Plant Train": "Sabine Pass T6",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 5,
            "Period": 103,
            "Year": 2026,
            "basecaseValue": 1.0044946302391904,
            "proposedValue": 1.0144946302391904,
            "rationale": "대체 공급 후보로 선택된 United States Sabine Pass T6의 2026년 7월 basecase record를 사용했습니다. 대체 가스 공급 가능성이 100%로 제시되고 노르웨이 생산 감소가 약 1%로 명시되어 기준 가동률에 0.01을 더한 절대 가동률로 설정했습니다."
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

- 소요시간: 04:47.064 (287.064s)
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
| Step2 selected slot | 43 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=43, basecaseValue_present=42 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:08.964 | 8.964 | 3745 | 537 | 4282 |
| Step2 slot proposal | True |  | 02:14.998 | 134.998 | 13272 | 15185 | 28457 |
| Step3 value proposal | True |  | 01:56.205 | 116.205 | 15004 | 12645 | 27649 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1117,
    "modelParamProposalId": 46,
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
        "rationale": "노르웨이 upstream 생산 감소가 직접적인 공급 차질로 제시되었고, 선택 dimension에 차질 강도와 대체 공급 완화율이 명시되어 Province/Year 단위 SupplyDisruption 입력으로 반영할 수 있습니다.",
        "values": [
          {
            "Province": "Norway",
            "Year": 2026,
            "basecaseValue": null,
            "proposedValue": 0.13125,
            "rationale": "노르웨이 해상 생산 차질이 2026년 7~12월 영향기간에 발생하는 연간 Province 단위 입력 슬롯입니다. Utilization 감소 60%를 급격 발생 후 6개월간 점진 회복으로 적용해 3.5개월 상당의 연간 영향으로 환산하고, 대체 가스 공급 가능성 25%를 차감하여 순차질률 13.125%를 적용했습니다."
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
        "rationale": "대체 가스 공급 가능성 25%가 명시되어 있고, 선택된 인접·시장연결 공급국의 가용 LNG 액화설비 utilization을 상향하는 입력으로 LiqUtilAdjustment가 직접 대응됩니다.",
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
            "rationale": "2026년 7월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 대체 공급 가능성 25%를 잔여 가동 여력에 적용하고, 급격 발생 첫 달로 100% 강도를 반영해 기준값을 0.3926380368098159로 상향했습니다."
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
            "proposedValue": 0.3588957055214723,
            "rationale": "2026년 8월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 5/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.3251533742331288,
            "rationale": "2026년 9월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 4/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.29141104294478526,
            "rationale": "2026년 10월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 3/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.2576687116564417,
            "rationale": "2026년 11월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 2/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.2239263803680981,
            "rationale": "2026년 12월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 1/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "rationale": "2026년 7월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 대체 공급 가능성 25%를 잔여 가동 여력에 적용하고, 급격 발생 첫 달로 100% 강도를 반영해 기준값을 0.3926380368098159로 상향했습니다."
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
            "proposedValue": 0.3588957055214723,
            "rationale": "2026년 8월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 5/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.3251533742331288,
            "rationale": "2026년 9월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 4/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.29141104294478526,
            "rationale": "2026년 10월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 3/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.2576687116564417,
            "rationale": "2026년 11월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 2/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
            "proposedValue": 0.2239263803680981,
            "rationale": "2026년 12월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 1/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 112,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 7월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 이미 100% 수준이므로 추가 가동 여력이 없어 상한 1.0을 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 113,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 8월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 이미 100% 수준이므로 추가 가동 여력이 없어 상한 1.0을 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 114,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 9월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 이미 100% 수준이므로 추가 가동 여력이 없어 상한 1.0을 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 115,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 10월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 이미 100% 수준이므로 추가 가동 여력이 없어 상한 1.0을 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 116,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 11월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 이미 100% 수준이므로 추가 가동 여력이 없어 상한 1.0을 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 117,
            "Year": 2026,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1,
            "rationale": "2026년 12월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 이미 100% 수준이므로 추가 가동 여력이 없어 상한 1.0을 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 112,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.85,
            "rationale": "2026년 7월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 대체 공급 가능성 25%를 잔여 가동 여력에 적용하고, 급격 발생 첫 달로 100% 강도를 반영해 기준값을 0.85로 상향했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 113,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.8416666667,
            "rationale": "2026년 8월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 5/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 114,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.8333333333,
            "rationale": "2026년 9월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 4/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 115,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.825,
            "rationale": "2026년 10월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 3/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 116,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.8166666667,
            "rationale": "2026년 11월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 2/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Skikda GL1K",
            "LNG Plant Train": "Skikda GL1K T1 (rebuild)",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 117,
            "Year": 2026,
            "basecaseValue": 0.7999999999999999,
            "proposedValue": 0.8083333333,
            "rationale": "2026년 12월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 1/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 112,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.25,
            "rationale": "2026년 7월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 0이므로 대체 공급 가능성 25%를 잔여 가동 여력에 적용하고, 급격 발생 첫 달로 100% 강도를 반영했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 113,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.2083333333,
            "rationale": "2026년 8월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 5/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 114,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.1666666667,
            "rationale": "2026년 9월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 4/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 115,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.125,
            "rationale": "2026년 10월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 3/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 116,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.0833333333,
            "rationale": "2026년 11월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 2/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 117,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.0416666667,
            "rationale": "2026년 12월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 1/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 112,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.25,
            "rationale": "2026년 7월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 0이므로 대체 공급 가능성 25%를 잔여 가동 여력에 적용하고, 급격 발생 첫 달로 100% 강도를 반영했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 113,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.2083333333,
            "rationale": "2026년 8월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 5/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 114,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.1666666667,
            "rationale": "2026년 9월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 4/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 115,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.125,
            "rationale": "2026년 10월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 3/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 116,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.0833333333,
            "rationale": "2026년 11월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 2/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 117,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.0416666667,
            "rationale": "2026년 12월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 1/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 7,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 112,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.25,
            "rationale": "2026년 7월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 기준 utilisation이 0이므로 대체 공급 가능성 25%를 잔여 가동 여력에 적용하고, 급격 발생 첫 달로 100% 강도를 반영했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 8,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 113,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.2083333333,
            "rationale": "2026년 8월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 5/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 9,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 114,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.1666666667,
            "rationale": "2026년 9월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 4/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 10,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 115,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.125,
            "rationale": "2026년 10월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 3/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 11,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 116,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.0833333333,
            "rationale": "2026년 11월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 2/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 12,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 117,
            "Year": 2026,
            "basecaseValue": 0,
            "proposedValue": 0.0416666667,
            "rationale": "2026년 12월은 6개월 대체 공급 반영기간에 포함되며 해당 액화설비의 기준 utilisation record가 존재합니다. 점진 회복을 반영해 1/6 강도로 대체 공급 가능성 25%를 잔여 가동 여력에 적용했습니다."
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
