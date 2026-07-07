# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-07T23:26:01
- 실행 종료: 2026-07-07T23:26:01
- 총 소요시간: 00:00.001 (0.001s)
- 대상 event_type_l2_ids: [21]
- 대상 parameters: ['GDP']
- concurrency: 1
- retries: 0
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=21 국가별 경기: scenario_group 1개, scenario 0개

## 호출 결과

### Parameter: GDP

#### event_type_l2_id=21 국가별 경기

##### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 21,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 60,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 국가별 경기 추가 검증"
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

- 대상 scenario_ids: []
- scenario_count: 0
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: PASS

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"60": true}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.
