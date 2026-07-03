# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-04T01:29:57
- 실행 종료: 2026-07-04T01:33:37
- 총 소요시간: 03:40.115 (220.115s)
- 대상 event_type_l2_ids: [1]
- concurrency: 1
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=1 Upstream Utilization 변동: scenario_group 1개, scenario 1개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 1 | 49 | 283 | OK | 1 | 03:39.965 | 219.965s |

## 호출 결과

### event_type_l2_id=1 Upstream Utilization 변동

- scenario_group_id: 49
- group_title: [model_parameter_agent_test] Upstream Utilization 변동 추가 검증
- 대상 scenario_ids: [283]
- scenario_count: 1
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: PASS

#### scenario_id=283 [model_parameter_agent_test] 단기 미세 감산과 대체 공급 충분

- 소요시간: 03:39.965 (219.965s)
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
| Step2 selected slot | 28 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=28, basecaseValue_present=27 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:05.547 | 5.547 | 1906 | 166 | 2072 |
| Step2 slot proposal | True |  | 00:58.553 | 58.553 | 10997 | 5916 | 16913 |
| Step3 value proposal | True |  | 02:19.135 | 139.135 | 12645 | 9762 | 22407 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1117,
    "modelParamProposalId": 47,
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
        "rationale": "노르웨이 해상 파업 위협은 upstream 생산 차질로 연결되는 사건이며, 기사에 초기 생산 감소 폭이 약 1%로 명시되어 있습니다. 기간은 1개월 이하이고 선택된 입력 축은 연 단위이므로, 1개월 차질을 연간 입력값으로 환산해 1% × 1/12의 연간 차질률을 적용합니다. 대체 가스 공급 가능성 100%는 별도 대체 공급 슬롯의 상향으로 반영하고, 노르웨이 자체 생산 차질은 양(+)의 SupplyDisruption으로 유지합니다.",
        "values": [
          {
            "Province": "Norway",
            "Year": 2027,
            "basecaseValue": null,
            "proposedValue": 0.0008333333333333334,
            "rationale": "사건의 발생 월이 6월로 제시되어 현재 기준월 이후의 가장 가까운 6월인 2027년을 적용했습니다. 초기 생산 감소 1%가 1개월 이하 지속되는 조건이므로 연간 축에는 1/12만 반영한 0.0833% 차질률을 제안합니다."
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
        "rationale": "대체 가스 공급 가능성이 100%로 제시되어 노르웨이의 단기 upstream 감소분을 LNG 전환 대체 공급으로 상쇄하는 구조를 반영합니다. 기사에 제시된 4만5,500boe/d 규모를 1개월 LNG 물량으로 환산하면 약 0.152Mt 수준이며, 선택된 2027년 6월 운영 중 액화설비 중 기준 가동률이 100% 미만인 설비의 월간 여유능력에 비례해 가동률을 상향했습니다. 이미 기준 가동률이 100% 내외 또는 초과인 설비는 추가 상향 여지가 없다고 보고 기준 수준을 유지합니다.",
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
            "basecaseValue": 0.18404907975460122,
            "proposedValue": 0.2299844,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.1840에서 선택 설비 전체 여유능력 대비 동일 비율로 대체 물량을 배분해 0.2300으로 상향합니다."
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
            "basecaseValue": 0.18404907975460122,
            "proposedValue": 0.2299844,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.1840에서 선택 설비 전체 여유능력 대비 동일 비율로 대체 물량을 배분해 0.2300으로 상향합니다."
          },
          {
            "Country": "Algeria",
            "LNG Plant": "Arzew GL3Z (Gassi Touil)",
            "LNG Plant Train": "Arzew GL3Z (Gassi Touil) T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0000000000000002,
            "proposedValue": 1.0000000000000002,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100% 수준이어서 추가 대체 물량 배분 여지가 없다고 보고 기준 수준을 유지합니다."
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
            "proposedValue": 0.4044183,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.3689에서 선택 설비 전체 여유능력 대비 동일 비율로 대체 물량을 배분해 0.4044로 상향합니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Damietta LNG",
            "LNG Plant Train": "Damietta LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0,
            "proposedValue": 0.0562967,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 0으로 제시되어 여유능력이 큽니다. 대체 물량을 선택 설비의 여유능력에 비례 배분해 0.0563의 가동률을 제안합니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0,
            "proposedValue": 0.0562967,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 0으로 제시되어 여유능력이 큽니다. 대체 물량을 선택 설비의 여유능력에 비례 배분해 0.0563의 가동률을 제안합니다."
          },
          {
            "Country": "Egypt",
            "LNG Plant": "Egyptian LNG (Idku)",
            "LNG Plant Train": "Egyptian LNG (Idku) T2",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.6,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0,
            "proposedValue": 0.0562967,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 0으로 제시되어 여유능력이 큽니다. 대체 물량을 선택 설비의 여유능력에 비례 배분해 0.0563의 가동률을 제안합니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.7343626705975042,
            "proposedValue": 0.7493172,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.7344에서 여유능력 비례 배분을 적용해 0.7493으로 상향합니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T2",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.7343626705975042,
            "proposedValue": 0.7493172,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.7344에서 여유능력 비례 배분을 적용해 0.7493으로 상향합니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T3",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.7155222887558216,
            "proposedValue": 0.7315374,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.7155에서 여유능력 비례 배분을 적용해 0.7315로 상향합니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T4",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.7293853719265485,
            "proposedValue": 0.7446201,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.7294에서 여유능력 비례 배분을 적용해 0.7446으로 상향합니다."
          },
          {
            "Country": "Nigeria",
            "LNG Plant": "NLNG",
            "LNG Plant Train": "NLNG T5",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.1,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.7293853719265485,
            "proposedValue": 0.7446201,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.7294에서 여유능력 비례 배분을 적용해 0.7446으로 상향합니다."
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
            "proposedValue": 0.7233202,
            "rationale": "선택된 2027년 6월 운영 설비이며 기준 가동률이 100% 미만입니다. 기준 가동률 0.7068에서 여유능력 비례 배분을 적용해 0.7233으로 상향합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Qatargas 1 T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.2,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0097245902976564,
            "proposedValue": 1.0097245902976564,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Qatargas 1 T2",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.2,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0097245902976564,
            "proposedValue": 1.0097245902976564,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Qatargas 1 T3",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.2,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0097245902976564,
            "proposedValue": 1.0097245902976564,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Qatargas 2 T4",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 7.8,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0095932896883497,
            "proposedValue": 1.0095932896883497,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Qatargas 2 T5",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 7.8,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0095932896883497,
            "proposedValue": 1.0095932896883497,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Qatargas 3 T6",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 7.8,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0095280855796953,
            "proposedValue": 1.0095280855796953,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Qatargas 4 T7",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 7.8,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0095928137459507,
            "proposedValue": 1.0095928137459507,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Rasgas 1 T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0090042114544358,
            "proposedValue": 1.0090042114544358,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Rasgas 1 T2",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 3.3,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0090042114544358,
            "proposedValue": 1.0090042114544358,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Rasgas 2 T3",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0077136513848695,
            "proposedValue": 1.0077136513848695,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Rasgas 2 T4",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0077136513848695,
            "proposedValue": 1.0077136513848695,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Rasgas 2 T5",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.7,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0077136513848695,
            "proposedValue": 1.0077136513848695,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Rasgas 3 T6",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 7.8,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0095932896883497,
            "proposedValue": 1.0095932896883497,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
          },
          {
            "Country": "Qatar",
            "LNG Plant": "QatarGas LNG",
            "LNG Plant Train": "Rasgas 3 T7",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 7.8,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0095932896883497,
            "proposedValue": 1.0095932896883497,
            "rationale": "선택된 2027년 6월 운영 설비이나 기준 가동률이 이미 100%를 초과해 추가 상향 배분 여지가 없다고 보고 기준 수준을 유지합니다."
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

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"49": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.
