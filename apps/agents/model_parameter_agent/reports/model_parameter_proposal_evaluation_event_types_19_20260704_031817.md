# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-04T03:18:17
- 실행 종료: 2026-07-04T03:20:04
- 총 소요시간: 01:46.959 (106.959s)
- 대상 event_type_l2_ids: [19]
- concurrency: 2
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=19 정책/규제 변화: scenario_group 1개, scenario 2개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 19 | 48 | 281 | OK | 1 | 01:13.070 | 73.070s |
| 19 | 48 | 282 | OK | 1 | 01:40.510 | 100.510s |

## 호출 결과

### event_type_l2_id=19 정책/규제 변화

- scenario_group_id: 48
- group_title: [model_parameter_agent_test] 정책/규제 routing 검증
- 대상 scenario_ids: [281, 282]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: PASS
- scenario별 value 차이: PASS
- 그룹 종합: PASS

#### scenario_id=281 [model_parameter_agent_test] IMO 운송 규제 보통 강도

- 소요시간: 01:13.070 (73.070s)
- attempt: 1
- db_loaded_context: `{"dimension_template": [{"dim_key": "period", "label": "기간", "required": true, "value_count": 7}, {"dim_key": "implementation_stage", "label": "시행 확실성·단계", "required": true, "value_count": 4}, {"dim_key": "impact_intensity", "label": "영향 강도", "required": false, "value_count": 3}, {"dim_key": "structural_change_yn", "label": "구조적 변동 여부", "required": false, "value_count": 2}], "event": {"created_at": "2026-06-19T23:18:59.770700", "detail_analysis_chars": 1374, "detail_analysis_preview": "사건 요약:\nIMO Net-Zero Framework의 채택 일정과 회원국별 입장 차이가 기존 핵심 사건으로 유지됨. 그리스의 회의적 입장, EU·미국·사우디 등 회원국 간 견해 차이, 향후 결정 회의의 불확실성이 주요 내용임. 2026-06-01 Platts Daily Report는 호르무즈발 공급 제약, 강한 운임, 타이트한 LNG-TTF basis, EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달, 아시아와 유럽의 카고 경쟁을 당일 LNG 시장 요인으로 제시함. 신규 연결 Record는 기존 요약에 이미 반영된 2026-06-01 시장 환경 업데이트와 동일한 내용으로, IMO Net-Zero Framework 정책 논의 자체의 추가 상태 변경은 확인되지 않음.\n\n영향 경로:\n국제 해운 온실가스 배출 비용 부과와 저탄소 연료 전환 유도는 선박 운항비 구조에 영향을 주는 정책 변수임. LNG선 연료 선택과 bio-LNG 등 저탄소 ", "event_title_ko": "IMO Net-Zero Framework 논의", "event_type_l2_id": 19, "key_bullet_count": 0, "key_bullets": [], "latest_record_first_created": "2026-06-01T00:00:00", "mi_event_id": "1155", "occurred_at": "", "oldest_record_first_created": "", "one_line_summary": "[해운 규제] IMO 탄소비용 논의 지속 → LNG 운송비·연료비 변수 유지", "source_mi_record_ids": [2271], "tag_count": 0}, "event_type": {"event_type_l1_id": 4, "even...`
- dimension_values: `{"impact_intensity": "보통", "implementation_stage": "시행 확정", "period": "3개월", "structural_change_yn": "단발적/한시"}`
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

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:07.151 | 7.151 | 2020 | 333 | 2353 |
| Step2 slot proposal | True |  | 00:16.871 | 16.871 | 4584 | 876 | 5460 |
| Step3 value proposal | True |  | 00:20.256 | 20.256 | 4231 | 1309 | 5540 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1155,
    "modelParamProposalId": 95,
    "proposalParameters": [
      {
        "modelTarget": {
          "modelFile": "Demand",
          "modelSheet": "CoalGasAdjustment",
          "slotAxesFieldNames": [
            "Month-Year",
            "Region"
          ],
          "tableName": "table1",
          "valueFieldNames": [
            "Gas Futures Price"
          ]
        },
        "parameterName": "Gas Futures Price",
        "rationale": "영향 강도가 '보통'이고, mapping_comment상 가스·LNG 비용 변화가 Gas↔Coal 전환 유인으로 연결될 때 Gas Futures Price가 해당 가격 신호를 반영하는 입력으로 사용됩니다. IMO 운송 규제는 직접 물량 차질보다는 LNG 운송비·선박 연료비 프리미엄을 통해 JKM/TTF 선물가격에 상방 압력을 주는 성격이며, 기간은 3개월이고 구조적 변화가 아닌 한시적 충격으로 해석했습니다. 제안값은 2026년 7~9월에 한정해 Asia JKM과 Europe TTF에 보수적인 소폭 상향 percent_change를 적용하되, 운송비 민감도가 더 큰 Asia에 더 높은 조정률을 배분했습니다.",
        "values": [
          {
            "Month-Year": "2026-07",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 2.0,
            "rationale": "3개월 영향 기간의 첫 달에 해당하는 Asia JKM 슬롯입니다. 기준값 record가 제공되지 않았으므로 보통 강도의 운송비·연료비 프리미엄을 보수적으로 가격 strip에 반영해 2.0% 상향 조정으로 산정했습니다."
          },
          {
            "Month-Year": "2026-08",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 2.0,
            "rationale": "3개월 영향 기간의 두 번째 달에 해당하는 Asia JKM 슬롯입니다. 한시적 규제 비용 프리미엄이 단기간 유지되는 것으로 보고 7월과 동일하게 2.0% 상향 조정했습니다."
          },
          {
            "Month-Year": "2026-09",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 1.5,
            "rationale": "3개월 영향 기간의 마지막 달에 해당하는 Asia JKM 슬롯입니다. 단발적·한시 충격의 후반부로 갈수록 반영 강도가 완화된다고 보아 1.5% 상향 조정했습니다."
          },
          {
            "Month-Year": "2026-07",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 1.5,
            "rationale": "3개월 영향 기간의 첫 달에 해당하는 Europe TTF 슬롯입니다. 운송 규제 비용이 유럽 가스 선물에도 상방 요인이지만 JKM 대비 운송비 민감도를 낮게 보아 1.5% 상향 조정했습니다."
          },
          {
            "Month-Year": "2026-08",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 1.5,
            "rationale": "3개월 영향 기간의 두 번째 달에 해당하는 Europe TTF 슬롯입니다. 규제 비용 프리미엄이 단기적으로 유지되는 것으로 보고 7월과 동일하게 1.5% 상향 조정했습니다."
          },
          {
            "Month-Year": "2026-09",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 1.0,
            "rationale": "3개월 영향 기간의 마지막 달에 해당하는 Europe TTF 슬롯입니다. 한시적 충격의 후반 완화를 반영해 유럽 가격 조정률을 1.0% 상향으로 낮춰 산정했습니다."
          }
        ]
      }
    ],
    "scenarioGroupId": 48,
    "scenarioId": 281
  },
  "message": "model parameter proposal completed",
  "status": "success"
}
```

</details>

#### scenario_id=282 [model_parameter_agent_test] IMO 운송 규제 큰 강도

- 소요시간: 01:40.510 (100.510s)
- attempt: 1
- db_loaded_context: `{"dimension_template": [{"dim_key": "period", "label": "기간", "required": true, "value_count": 7}, {"dim_key": "implementation_stage", "label": "시행 확실성·단계", "required": true, "value_count": 4}, {"dim_key": "impact_intensity", "label": "영향 강도", "required": false, "value_count": 3}, {"dim_key": "structural_change_yn", "label": "구조적 변동 여부", "required": false, "value_count": 2}], "event": {"created_at": "2026-06-19T23:18:59.770700", "detail_analysis_chars": 1374, "detail_analysis_preview": "사건 요약:\nIMO Net-Zero Framework의 채택 일정과 회원국별 입장 차이가 기존 핵심 사건으로 유지됨. 그리스의 회의적 입장, EU·미국·사우디 등 회원국 간 견해 차이, 향후 결정 회의의 불확실성이 주요 내용임. 2026-06-01 Platts Daily Report는 호르무즈발 공급 제약, 강한 운임, 타이트한 LNG-TTF basis, EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달, 아시아와 유럽의 카고 경쟁을 당일 LNG 시장 요인으로 제시함. 신규 연결 Record는 기존 요약에 이미 반영된 2026-06-01 시장 환경 업데이트와 동일한 내용으로, IMO Net-Zero Framework 정책 논의 자체의 추가 상태 변경은 확인되지 않음.\n\n영향 경로:\n국제 해운 온실가스 배출 비용 부과와 저탄소 연료 전환 유도는 선박 운항비 구조에 영향을 주는 정책 변수임. LNG선 연료 선택과 bio-LNG 등 저탄소 ", "event_title_ko": "IMO Net-Zero Framework 논의", "event_type_l2_id": 19, "key_bullet_count": 0, "key_bullets": [], "latest_record_first_created": "2026-06-01T00:00:00", "mi_event_id": "1155", "occurred_at": "", "oldest_record_first_created": "", "one_line_summary": "[해운 규제] IMO 탄소비용 논의 지속 → LNG 운송비·연료비 변수 유지", "source_mi_record_ids": [2271], "tag_count": 0}, "event_type": {"event_type_l1_id": 4, "even...`
- dimension_values: `{"impact_intensity": "큼", "implementation_stage": "시행 확정", "period": "1년", "structural_change_yn": "구조적/영구"}`
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

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:07.831 | 7.831 | 2015 | 276 | 2291 |
| Step2 slot proposal | True |  | 00:24.458 | 24.458 | 4578 | 2084 | 6662 |
| Step3 value proposal | True |  | 00:46.453 | 46.453 | 4765 | 2726 | 7491 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1155,
    "modelParamProposalId": 96,
    "proposalParameters": [
      {
        "modelTarget": {
          "modelFile": "Demand",
          "modelSheet": "CoalGasAdjustment",
          "slotAxesFieldNames": [
            "Month-Year",
            "Region"
          ],
          "tableName": "table1",
          "valueFieldNames": [
            "Gas Futures Price"
          ]
        },
        "parameterName": "Gas Futures Price",
        "rationale": "영향 강도 dimension의 값이 ‘큼’이고, mapping_comment가 가스/LNG 가격 변화로 Gas↔Coal 전환 유인이 생기는 경우 Gas Futures Price를 조정 대상으로 연결하고 있습니다. 기간은 1년이며 시행 확정·구조적 변동으로 제시되어 있어, Asia는 JKM, Europe은 TTF 선물가격 strip에 대해 선택된 1년 구간 전반에 상향 충격을 반영합니다. 운송 규제의 직접 입력 항목이 아니므로 가격 충격은 보수적으로 percent_change 방식으로 적용하되, LNG 운송비 민감도가 더 큰 Asia에 더 높은 상향률을 둡니다.",
        "values": [
          {
            "Month-Year": "2026-07",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "해당 월의 Asia JKM strip은 IMO 운송 규제에 따른 LNG 운송·연료비 프리미엄이 가장 직접적으로 반영될 수 있는 구간입니다. 기준값 record가 제공되지 않았으므로 현재 입력값 대비 5% 상향 조정으로 제안합니다."
          },
          {
            "Month-Year": "2026-07",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "해당 월의 Europe TTF strip은 LNG 수입 한계가격을 통해 운송비 상승 영향을 일부 반영할 수 있습니다. 기준값 record가 제공되지 않았으므로 현재 입력값 대비 4% 상향 조정으로 제안합니다."
          },
          {
            "Month-Year": "2026-08",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "1년 영향 기간 내 초기 구간의 Asia JKM strip으로, 구조적 운송비 프리미엄이 지속된다고 보아 현재 입력값 대비 5% 상향 조정합니다."
          },
          {
            "Month-Year": "2026-08",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "1년 영향 기간 내 초기 구간의 Europe TTF strip으로, LNG 운송비 상승이 유럽 가스 가격에 간접 반영되는 정도를 고려해 현재 입력값 대비 4% 상향 조정합니다."
          },
          {
            "Month-Year": "2026-09",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "해당 월은 선택된 1년 규제 영향 구간에 포함되며, Asia JKM은 LNG 해상 운송비 변화에 민감한 지역 가격입니다. 기준값 미제공 상태에서 현재 입력값 대비 5% 상향을 적용합니다."
          },
          {
            "Month-Year": "2026-09",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "해당 월은 선택된 1년 규제 영향 구간에 포함되며, Europe TTF는 LNG 수입가격 경로를 통해 비용 상승 영향을 받는 것으로 보아 현재 입력값 대비 4% 상향을 적용합니다."
          },
          {
            "Month-Year": "2026-10",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "구조적 운송 규제 충격이 지속되는 구간으로 보고, Asia JKM 선물가격에 현재 입력값 대비 5% 상향 충격을 유지합니다."
          },
          {
            "Month-Year": "2026-10",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "구조적 운송 규제 충격이 지속되는 구간으로 보고, Europe TTF 선물가격에는 LNG 운송비 전가 정도를 보수적으로 반영해 현재 입력값 대비 4% 상향 충격을 유지합니다."
          },
          {
            "Month-Year": "2026-11",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "1년 영향 기간 중 동절기 진입 전 구간으로, LNG 운송비 프리미엄이 JKM에 반영될 수 있어 현재 입력값 대비 5% 상향 조정합니다."
          },
          {
            "Month-Year": "2026-11",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "1년 영향 기간 중 동절기 진입 전 구간으로, TTF에 대한 운송비 전가를 간접 충격으로 반영하여 현재 입력값 대비 4% 상향 조정합니다."
          },
          {
            "Month-Year": "2026-12",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "선택된 영향 기간 내 동절기 LNG 가격 민감도가 높은 월로, Asia JKM에 현재 입력값 대비 5% 상향 충격을 적용합니다."
          },
          {
            "Month-Year": "2026-12",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "선택된 영향 기간 내 동절기 가스 가격 민감도가 높은 월로, Europe TTF에는 LNG 운송비 상승의 간접 영향을 반영해 현재 입력값 대비 4% 상향 충격을 적용합니다."
          },
          {
            "Month-Year": "2027-01",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "1년 영향 기간의 동절기 구간에 해당하며, JKM은 해상 LNG 비용 프리미엄에 대한 민감도가 높으므로 현재 입력값 대비 5% 상향 조정합니다."
          },
          {
            "Month-Year": "2027-01",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "1년 영향 기간의 동절기 구간에 해당하며, TTF는 LNG 수입 한계가격을 통해 일부 영향을 받는 것으로 보아 현재 입력값 대비 4% 상향 조정합니다."
          },
          {
            "Month-Year": "2027-02",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "규제 충격이 구조적으로 지속된다는 전제에서, Asia JKM의 운송비 프리미엄을 현재 입력값 대비 5% 상향으로 유지합니다."
          },
          {
            "Month-Year": "2027-02",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "규제 충격이 구조적으로 지속된다는 전제에서, Europe TTF에는 간접 운송비 전가분을 현재 입력값 대비 4% 상향으로 유지합니다."
          },
          {
            "Month-Year": "2027-03",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "선택된 1년 기간 중 후반부에 해당하지만 구조적 변동으로 제시되어 충격을 감쇠하지 않고, Asia JKM에 현재 입력값 대비 5% 상향을 적용합니다."
          },
          {
            "Month-Year": "2027-03",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "선택된 1년 기간 중 후반부에 해당하지만 구조적 변동으로 제시되어 충격을 감쇠하지 않고, Europe TTF에 현재 입력값 대비 4% 상향을 적용합니다."
          },
          {
            "Month-Year": "2027-04",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "해당 월은 1년 적용 기간에 포함되며, Asia JKM은 LNG 운송 규제 비용 반영도가 높은 가격 strip이므로 현재 입력값 대비 5% 상향 조정합니다."
          },
          {
            "Month-Year": "2027-04",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "해당 월은 1년 적용 기간에 포함되며, Europe TTF는 LNG 운송비 상승의 간접 영향만 반영해 현재 입력값 대비 4% 상향 조정합니다."
          },
          {
            "Month-Year": "2027-05",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "영향 기간 말기에 가까운 월이나 구조적 운송비 상승 요인이 유지된다고 보아, Asia JKM에 현재 입력값 대비 5% 상향 충격을 둡니다."
          },
          {
            "Month-Year": "2027-05",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "영향 기간 말기에 가까운 월이나 구조적 운송비 상승 요인이 유지된다고 보아, Europe TTF에는 현재 입력값 대비 4% 상향 충격을 둡니다."
          },
          {
            "Month-Year": "2027-06",
            "Region": "Asia",
            "basecaseValue": null,
            "proposedValue": 5,
            "rationale": "선택된 1년 기간의 마지막 월로, 구조적 규제 비용이 계속 반영되는 것으로 보아 Asia JKM에 현재 입력값 대비 5% 상향 조정을 적용합니다."
          },
          {
            "Month-Year": "2027-06",
            "Region": "Europe",
            "basecaseValue": null,
            "proposedValue": 4,
            "rationale": "선택된 1년 기간의 마지막 월로, 구조적 규제 비용이 계속 반영되는 것으로 보아 Europe TTF에 현재 입력값 대비 4% 상향 조정을 적용합니다."
          }
        ]
      }
    ],
    "scenarioGroupId": 48,
    "scenarioId": 282
  },
  "message": "model parameter proposal completed",
  "status": "success"
}
```

</details>

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"48": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.
