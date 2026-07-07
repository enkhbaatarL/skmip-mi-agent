# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-07T21:04:02
- 실행 종료: 2026-07-07T21:04:02
- 총 소요시간: 00:00.000 (0.000s)
- 대상 event_type_l2_ids: [1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 17, 18, 19, 21]
- concurrency: 4
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=1 Upstream Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=2 터미널 Utilization 변동: scenario_group 2개, scenario 12개
- event_type_l2_id=4 파이프라인 Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=5 발전소 Utilization 변동: scenario_group 1개, scenario 2개
- event_type_l2_id=6 겨울 한파: scenario_group 4개, scenario 12개
- event_type_l2_id=7 여름 폭염: scenario_group 5개, scenario 12개
- event_type_l2_id=8 원자력 발전: scenario_group 1개, scenario 2개
- event_type_l2_id=9 재생에너지: scenario_group 1개, scenario 6개
- event_type_l2_id=10 석탄 발전: scenario_group 1개, scenario 6개
- event_type_l2_id=11 자연재해: scenario_group 1개, scenario 2개
- event_type_l2_id=17 지정학적 긴장 및 전쟁·군사분쟁: scenario_group 1개, scenario 7개
- event_type_l2_id=18 경제 제재 및 무역 제한: scenario_group 2개, scenario 12개
- event_type_l2_id=19 정책/규제 변화: scenario_group 1개, scenario 2개
- event_type_l2_id=21 국가별 경기: scenario_group 1개, scenario 2개

## 호출 결과

### event_type_l2_id=1 Upstream Utilization 변동

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 1,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 49,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] Upstream Utilization 변동 추가 검증"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [283, 284]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=2 터미널 Utilization 변동

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 2,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 18,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "Cameron LNG 정비 후 정상가동 유지"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [105, 106, 107, 108, 109, 110]
- scenario_count: 6
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=2 터미널 Utilization 변동

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 2,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 46,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "Golden Pass feedgas 변화와 미국 LNG 공급 여력 시나리오"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [273, 274, 275, 276, 277, 278]
- scenario_count: 6
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=4 파이프라인 Utilization 변동

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 4,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 50,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 파이프라인 Utilization 변동 추가 검증"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [285, 286]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=5 발전소 Utilization 변동

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 5,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 51,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 발전소 Utilization 변동 추가 검증"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [287, 288]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=6 겨울 한파

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 6,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 52,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 겨울 한파 추가 검증"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [289, 290]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=6 겨울 한파

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 6,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 61,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_weather_ext_20260630] 한파 이벤트 1378 수급모델 파라미터 테스트"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [307, 308, 309, 310]
- scenario_count: 4
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=6 겨울 한파

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 6,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 62,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_weather_ext_20260630] 한파 이벤트 1363 수급모델 파라미터 테스트"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [311, 312, 313]
- scenario_count: 3
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=6 겨울 한파

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 6,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 63,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_weather_ext_20260630] 한파 이벤트 1281 수급모델 파라미터 테스트"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [314, 315, 316]
- scenario_count: 3
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=7 여름 폭염

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 7,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 53,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 여름 폭염 추가 검증"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [291, 292]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=7 여름 폭염

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 7,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 64,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_weather_ext_20260630] 폭염 이벤트 1345 수급모델 파라미터 테스트"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [317, 318, 319]
- scenario_count: 3
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=7 여름 폭염

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 7,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 65,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_weather_ext_20260630] 폭염 이벤트 1228 수급모델 파라미터 테스트"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [320, 321, 322]
- scenario_count: 3
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=7 여름 폭염

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 7,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 66,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_weather_ext_20260630] 폭염 이벤트 1144 수급모델 파라미터 테스트"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [323, 324]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=7 여름 폭염

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 7,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 67,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_weather_ext_20260630] 폭염 이벤트 1148 수급모델 파라미터 테스트"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [325, 326]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=8 원자력 발전

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 8,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 54,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 원자력 발전 추가 검증"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [293, 294]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=9 재생에너지

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 9,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 44,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "유럽 재생에너지 약세발 가스발전·LNG 수요 시나리오"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [261, 262, 263, 264, 265, 266]
- scenario_count: 6
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=10 석탄 발전

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 10,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 45,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "Haramachi 석탄발전 차질에 따른 일본 LNG 대체수요"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [267, 268, 269, 270, 271, 272]
- scenario_count: 6
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=11 자연재해

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 11,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 47,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "[model_parameter_agent_test] 자연재해 routing 검증"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [279, 280]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=17 지정학적 긴장 및 전쟁·군사분쟁

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 17,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 16,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "중동 군사충돌 재격화 에너지 리스크"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [92, 93, 94, 95, 96, 97, 98]
- scenario_count: 7
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=18 경제 제재 및 무역 제한

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 18,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 22,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "러시아 Arctic LNG 2 제재 이슈"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [129, 130, 131, 132, 133, 134]
- scenario_count: 6
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=18 경제 제재 및 무역 제한

#### Scenario Group

```json
{
  "description": "",
  "dimension_selected": [],
  "event_type": {},
  "event_type_l2_id": 18,
  "mi_event_id": null,
  "request_usr_id": null,
  "scenario_count": null,
  "scenario_group_id": 23,
  "stage": null,
  "status": null,
  "summary": "",
  "title": "러시아 Arctic LNG 2 제재 이슈"
}
```

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [135, 136, 137, 138, 139, 140]
- scenario_count: 6
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=19 정책/규제 변화

#### Scenario Group

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

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [281, 282]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

### event_type_l2_id=21 국가별 경기

#### Scenario Group

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

#### Dimension Template

```json
[]
```

#### Dimension -> Parameter Mapping

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

#### Event

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

#### Group Test Summary

- 대상 scenario_ids: [305, 306]
- scenario_count: 2
- 매핑 후보 검증: PASS
- LLM selected 검증: PASS
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

## 최종 요약

- ERROR_COUNT: 0
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"16": false, "18": false, "22": false, "23": false, "44": false, "45": false, "46": false, "47": false, "48": false, "49": false, "50": false, "51": false, "52": false, "53": false, "54": false, "60": false, "61": false, "62": false, "63": false, "64": false, "65": false, "66": false, "67": false}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- 오류 없음. 1회 실행으로 완료.
