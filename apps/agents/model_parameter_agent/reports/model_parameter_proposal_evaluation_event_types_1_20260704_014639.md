# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-04T01:46:39
- 실행 종료: 2026-07-04T01:50:49
- 총 소요시간: 04:10.556 (250.556s)
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
| 1 | 49 | 283 | OK | 1 | 04:10.559 | 250.559s |

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

- 소요시간: 04:10.559 (250.559s)
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
| Step2 selected slot | 34 | PASS |
| Step3 basecase 샘플 | prompt_records=100, limit=100 | PASS |
| Step3 value 결과 | value_cells=34, basecaseValue_present=33 | PASS |
| Step2 slot axis value 수 | `{"1|altgassupplyavailability|liqutiladjustment|supply|liqutiladjustment": {"Month": 12, "Period": 99, "Year": 9}}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:04.573 | 4.573 | 1906 | 161 | 2067 |
| Step2 slot proposal | True |  | 01:58.591 | 118.591 | 10997 | 7855 | 18852 |
| Step3 value proposal | True |  | 01:50.126 | 110.126 | 13973 | 10134 | 24107 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1117,
    "modelParamProposalId": 48,
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
        "rationale": "Utilization 변화 폭이 <5%로 제시되고 이벤트 본문에 노르웨이 해상 생산의 초기 약 1% 감소 위험이 명시되어 있어, Province 단위 upstream 생산 차질을 연간 축으로 반영하는 SupplyDisruption이 해당된다. 대체 가스 공급 가능성 100%는 순수급 부족을 완화하는 조건이지만, 원천 생산 차질 자체는 노르웨이 슬롯에 반영하고 대체 공급은 별도 가동률 상향 구조로 보완한다. 기간은 1개월 이하이므로 연간 입력에는 1개월 영향만 희석해 반영한다.",
        "values": [
          {
            "Province": "Norway",
            "Year": 2027,
            "basecaseValue": null,
            "proposedValue": 0.0008333333333333334,
            "rationale": "연도 없이 6월 5일이 언급되어 현재 기준월 이후 가장 가까운 2027년 6월 충격으로 해석하고, 선택된 연간 Norway 슬롯에 반영했다. 이벤트의 초기 생산 감소 1%를 1개월 이하 기간으로 연간화하여 0.01×1/12=0.0008333333의 생산 차질률로 산정했다."
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
        "rationale": "대체 가스 공급 가능성 100%는 노르웨이 upstream 감산으로 발생하는 부족분을 LNG 전환 대체 공급으로 충당할 수 있음을 의미하며, LiqUtilAdjustment는 선택된 대체 공급국 액화설비의 월별 가동률 override를 통해 이를 직접 반영할 수 있는 parameter이다. 기간은 1개월 이하이고 발생은 점진, 회복은 급격으로 제시되어 단일 월에만 소폭 상향을 적용하며, 기준 가동률이 이미 높은 설비는 추가 상향 여지를 제한하고 여유가 있는 설비의 잔여 가동률 여력에 비례해 배분한다.",
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
            "proposedValue": 0.22713108872739868,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.18404907975460122를 사용했다. 1개월 노르웨이 감산분을 대체 LNG 공급으로 충당하기 위해 잔여 가동률 여력의 약 5.28%만 활용하여 0.18404907975460122+(1-0.18404907975460122)×0.0528로 산정했다."
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
            "proposedValue": 0.22713108872739868,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.18404907975460122를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.18404907975460122+(1-0.18404907975460122)×0.0528로 산정했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0000000000000002로 이미 사실상 최대 수준이므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "proposedValue": 0.40221155555555554,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.3688888888888889를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.3688888888888889+(1-0.3688888888888889)×0.0528로 산정했다."
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
            "proposedValue": 0.0528,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률은 0이다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0+(1-0)×0.0528로 산정했다."
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
            "proposedValue": 0.0528,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률은 0이다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0+(1-0)×0.0528로 산정했다."
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
            "proposedValue": 0.0528,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률은 0이다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0+(1-0)×0.0528로 산정했다."
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
            "proposedValue": 0.7483883211895559,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.7343626705975042를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.7343626705975042+(1-0.7343626705975042)×0.0528로 산정했다."
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
            "proposedValue": 0.7483883211895559,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.7343626705975042를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.7343626705975042+(1-0.7343626705975042)×0.0528로 산정했다."
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
            "proposedValue": 0.7305427111095142,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.7155222887558216를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.7155222887558216+(1-0.7155222887558216)×0.0528로 산정했다."
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
            "proposedValue": 0.7436742241248263,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.7293853719265485를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.7293853719265485+(1-0.7293853719265485)×0.0528로 산정했다."
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
            "proposedValue": 0.7436742241248263,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.7293853719265485를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.7293853719265485+(1-0.7293853719265485)×0.0528로 산정했다."
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
            "proposedValue": 0.7222937925925926,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.7068148148148149를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.7068148148148149+(1-0.7068148148148149)×0.0528로 산정했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0097245902976564로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0097245902976564로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0097245902976564로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0095932896883497로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0095932896883497로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0095280855796953로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0095928137459507로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.9100611955377459,
            "proposedValue": 0.9148103642629529,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.9100611955377459를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.9100611955377459+(1-0.9100611955377459)×0.0528로 산정했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T2",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.9100611955377459,
            "proposedValue": 0.9148103642629529,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.9100611955377459를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.9100611955377459+(1-0.9100611955377459)×0.0528로 산정했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Cameron LNG",
            "LNG Plant Train": "Cameron LNG T3",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.5,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.9100611955377459,
            "proposedValue": 0.9148103642629529,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.9100611955377459를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.9100611955377459+(1-0.9100611955377459)×0.0528로 산정했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Corpus Christi LNG",
            "LNG Plant Train": "Corpus Christi T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.52,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.1211813100844745,
            "proposedValue": 1.1211813100844745,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.1211813100844745로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Corpus Christi LNG",
            "LNG Plant Train": "Corpus Christi T2",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.52,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.1211813100844745,
            "proposedValue": 1.1211813100844745,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.1211813100844745로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Corpus Christi LNG",
            "LNG Plant Train": "Corpus Christi T3",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 4.52,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.106194690265487,
            "proposedValue": 1.106194690265487,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.106194690265487로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Freeport LNG",
            "LNG Plant Train": "Freeport LNG T1",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 5.1,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0576652133208428,
            "proposedValue": 1.0576652133208428,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0576652133208428로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Freeport LNG",
            "LNG Plant Train": "Freeport LNG T2",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 5.099999,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.0557458827376056,
            "proposedValue": 1.0557458827376056,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.0557458827376056로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Freeport LNG",
            "LNG Plant Train": "Freeport LNG T3",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 5.099999,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 1.053826344768992,
            "proposedValue": 1.053826344768992,
            "rationale": "선택된 2027년 6월 슬롯의 기준 가동률이 1.053826344768992로 이미 1.0을 초과하므로 추가 상향 여력이 없다고 보아 기준값을 유지했다."
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
            "basecaseValue": 0.9789641720392571,
            "proposedValue": 0.9800748637555843,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.9789641720392571를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.9789641720392571+(1-0.9789641720392571)×0.0528로 산정했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Sabine Pass LNG",
            "LNG Plant Train": "Sabine Pass T3-T4",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 10,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.9789641720392571,
            "proposedValue": 0.9800748637555843,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.9789641720392571를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.9789641720392571+(1-0.9789641720392571)×0.0528로 산정했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Sabine Pass LNG",
            "LNG Plant Train": "Sabine Pass T5",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 5,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.9261001067491373,
            "proposedValue": 0.9300020215120529,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.9261001067491373를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.9261001067491373+(1-0.9261001067491373)×0.0528로 산정했다."
          },
          {
            "Country": "United States",
            "LNG Plant": "Sabine Pass LNG",
            "LNG Plant Train": "Sabine Pass T6",
            "Life Cycle Category": "Operational",
            "Month": 6,
            "Nameplate Capacity (MTPA)": 5,
            "Period": 123,
            "Year": 2027,
            "basecaseValue": 0.9789641720392571,
            "proposedValue": 0.9800748637555843,
            "rationale": "선택된 2027년 6월 슬롯에 대해 기준 가동률 0.9789641720392571를 사용했다. 대체 공급 필요량을 잔여 여력 비례로 배분하여 0.9789641720392571+(1-0.9789641720392571)×0.0528로 산정했다."
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
