# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-04T02:58:23
- 실행 종료: 2026-07-04T02:59:33
- 총 소요시간: 01:09.667 (69.667s)
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
| 19 | 48 | 281 | OK | 1 | 00:58.190 | 58.190s |
| 19 | 48 | 282 | OK | 1 | 01:03.042 | 63.042s |

## 호출 결과

### event_type_l2_id=19 정책/규제 변화

- scenario_group_id: 48
- group_title: [model_parameter_agent_test] 정책/규제 routing 검증
- 대상 scenario_ids: [281, 282]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: REVIEW
- scenario별 value 차이: N/A
- 그룹 종합: PASS

#### scenario_id=281 [model_parameter_agent_test] IMO 운송 규제 보통 강도

- 소요시간: 00:58.190 (58.190s)
- attempt: 1
- db_loaded_context: `{"dimension_template": [{"dim_key": "period", "label": "기간", "required": true, "value_count": 7}, {"dim_key": "implementation_stage", "label": "시행 확실성·단계", "required": true, "value_count": 4}, {"dim_key": "impact_intensity", "label": "영향 강도", "required": false, "value_count": 3}, {"dim_key": "structural_change_yn", "label": "구조적 변동 여부", "required": false, "value_count": 2}], "event": {"created_at": "2026-06-19T23:18:59.770700", "detail_analysis_chars": 1374, "detail_analysis_preview": "사건 요약:\nIMO Net-Zero Framework의 채택 일정과 회원국별 입장 차이가 기존 핵심 사건으로 유지됨. 그리스의 회의적 입장, EU·미국·사우디 등 회원국 간 견해 차이, 향후 결정 회의의 불확실성이 주요 내용임. 2026-06-01 Platts Daily Report는 호르무즈발 공급 제약, 강한 운임, 타이트한 LNG-TTF basis, EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달, 아시아와 유럽의 카고 경쟁을 당일 LNG 시장 요인으로 제시함. 신규 연결 Record는 기존 요약에 이미 반영된 2026-06-01 시장 환경 업데이트와 동일한 내용으로, IMO Net-Zero Framework 정책 논의 자체의 추가 상태 변경은 확인되지 않음.\n\n영향 경로:\n국제 해운 온실가스 배출 비용 부과와 저탄소 연료 전환 유도는 선박 운항비 구조에 영향을 주는 정책 변수임. LNG선 연료 선택과 bio-LNG 등 저탄소 ", "event_title_ko": "IMO Net-Zero Framework 논의", "event_type_l2_id": 19, "key_bullet_count": 0, "key_bullets": [], "latest_record_first_created": "2026-06-01T00:00:00", "mi_event_id": "1155", "occurred_at": "", "oldest_record_first_created": "", "one_line_summary": "[해운 규제] IMO 탄소비용 논의 지속 → LNG 운송비·연료비 변수 유지", "source_mi_record_ids": [2271], "tag_count": 0}, "event_type": {"event_type_l1_id": 4, "even...`
- dimension_values: `{"impact_intensity": "보통", "implementation_stage": "시행 확정", "period": "3개월", "structural_change_yn": "단발적/한시"}`
- expected_parameters: `["Gas Futures Price"]`
- selected_parameters: `[]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: REVIEW
- selected_messages: `["final recommendation이 없습니다. 후보는 검증됐지만 slot/value를 명확히 확정하지 못한 케이스로 기록합니다."]`
- routing_messages: `["routing 후보 중 selected parameter가 없습니다."]`
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=19|impactintensity|gasfuturesprice|demand|coalgasadjustment, sheet=CoalGasAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=1, final_selected=0, proposalParameters=0 | REVIEW |
| Step2 basecase raw rows | raw_records=0 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=0, distinct_axis_values=0 | PASS |
| Step2 selected slot | 6 | PASS |
| Step3 basecase 샘플 | prompt_records=0, limit=100 | PASS |
| Step3 value 결과 | value_cells=0, basecaseValue_present=0 | EMPTY |
| Step2 slot axis value 수 | `{}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:06.792 | 6.792 | 2020 | 300 | 2320 |
| Step2 slot proposal | True |  | 00:13.976 | 13.976 | 4584 | 839 | 5423 |
| Step3 value proposal | True |  | 00:08.773 | 8.773 | 4022 | 449 | 4471 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1155,
    "modelParamProposalId": 91,
    "proposalParameters": [],
    "scenarioGroupId": 48,
    "scenarioId": 281
  },
  "message": "model parameter proposal completed",
  "status": "success"
}
```

</details>

#### scenario_id=282 [model_parameter_agent_test] IMO 운송 규제 큰 강도

- 소요시간: 01:03.042 (63.042s)
- attempt: 1
- db_loaded_context: `{"dimension_template": [{"dim_key": "period", "label": "기간", "required": true, "value_count": 7}, {"dim_key": "implementation_stage", "label": "시행 확실성·단계", "required": true, "value_count": 4}, {"dim_key": "impact_intensity", "label": "영향 강도", "required": false, "value_count": 3}, {"dim_key": "structural_change_yn", "label": "구조적 변동 여부", "required": false, "value_count": 2}], "event": {"created_at": "2026-06-19T23:18:59.770700", "detail_analysis_chars": 1374, "detail_analysis_preview": "사건 요약:\nIMO Net-Zero Framework의 채택 일정과 회원국별 입장 차이가 기존 핵심 사건으로 유지됨. 그리스의 회의적 입장, EU·미국·사우디 등 회원국 간 견해 차이, 향후 결정 회의의 불확실성이 주요 내용임. 2026-06-01 Platts Daily Report는 호르무즈발 공급 제약, 강한 운임, 타이트한 LNG-TTF basis, EU 저장률 40.09%, Golden Pass 시운전 차질, Bulgargaz·Enarsa 조달, 아시아와 유럽의 카고 경쟁을 당일 LNG 시장 요인으로 제시함. 신규 연결 Record는 기존 요약에 이미 반영된 2026-06-01 시장 환경 업데이트와 동일한 내용으로, IMO Net-Zero Framework 정책 논의 자체의 추가 상태 변경은 확인되지 않음.\n\n영향 경로:\n국제 해운 온실가스 배출 비용 부과와 저탄소 연료 전환 유도는 선박 운항비 구조에 영향을 주는 정책 변수임. LNG선 연료 선택과 bio-LNG 등 저탄소 ", "event_title_ko": "IMO Net-Zero Framework 논의", "event_type_l2_id": 19, "key_bullet_count": 0, "key_bullets": [], "latest_record_first_created": "2026-06-01T00:00:00", "mi_event_id": "1155", "occurred_at": "", "oldest_record_first_created": "", "one_line_summary": "[해운 규제] IMO 탄소비용 논의 지속 → LNG 운송비·연료비 변수 유지", "source_mi_record_ids": [2271], "tag_count": 0}, "event_type": {"event_type_l1_id": 4, "even...`
- dimension_values: `{"impact_intensity": "큼", "implementation_stage": "시행 확정", "period": "1년", "structural_change_yn": "구조적/영구"}`
- expected_parameters: `["Gas Futures Price"]`
- selected_parameters: `[]`
- mapping_candidate_coverage: PASS
- selected_result: PASS
- routing_result: REVIEW
- selected_messages: `["final recommendation이 없습니다. 후보는 검증됐지만 slot/value를 명확히 확정하지 못한 케이스로 기록합니다."]`
- routing_messages: `["routing 후보 중 selected parameter가 없습니다."]`
- basecase_warnings: `["basecase record를 추출하지 못했습니다: candidate_key=19|impactintensity|gasfuturesprice|demand|coalgasadjustment, sheet=CoalGasAdjustment"]`

##### 단계별 실행 요약

| 항목 | 값 | 판정 |
|---|---:|---|
| 종료 단계 | Step3 완료 - value proposal 산정 | |
| Step1/1.5 parameter 후보 | rule=3, validated=1, final_selected=0, proposalParameters=0 | REVIEW |
| Step2 basecase raw rows | raw_records=0 | PASS |
| Step2 distinct slot axis values | slot_option_candidates=0, distinct_axis_values=0 | PASS |
| Step2 selected slot | 24 | PASS |
| Step3 basecase 샘플 | prompt_records=0, limit=100 | PASS |
| Step3 value 결과 | value_cells=0, basecaseValue_present=0 | EMPTY |
| Step2 slot axis value 수 | `{}` | |

##### 모델 호출별 소요시간

| step | success | model_name | 소요시간 | elapsed_seconds | prompt_tokens | completion_tokens | total_tokens |
|---|---|---|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | True |  | 00:08.665 | 8.665 | 2015 | 340 | 2355 |
| Step2 slot proposal | True |  | 00:22.380 | 22.380 | 4578 | 1902 | 6480 |
| Step3 value proposal | True |  | 00:10.536 | 10.536 | 4556 | 517 | 5073 |
<details>
<summary>final response JSON</summary>

```json
{
  "data": {
    "eventId": 1155,
    "modelParamProposalId": 92,
    "proposalParameters": [],
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
- EMPTY_RECOMMENDATIONS: 2
- EMPTY_RECOMMENDATION_SCENARIOS: `[{"scenario_group_id": 48, "scenario_id": 281, "title": "[model_parameter_agent_test] IMO 운송 규제 보통 강도"}, {"scenario_group_id": 48, "scenario_id": 282, "title": "[model_parameter_agent_test] IMO 운송 규제 큰 강도"}]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.
