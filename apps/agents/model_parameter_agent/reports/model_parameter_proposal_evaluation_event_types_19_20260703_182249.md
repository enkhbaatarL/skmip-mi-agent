# Model Parameter Proposal Evaluation - Event Types

- 실행 시작: 2026-07-03T18:22:49
- 실행 종료: 2026-07-03T18:25:12
- 총 소요시간: 02:22.606 (142.606s)
- 대상 event_type_l2_ids: [19]
- concurrency: 1
- retries: 1
- 대상 수집 방식: midb의 scenario_group/scenario를 event_type_l2_id 기준으로 동적 조회
- 호출 방식: 내부 raw graph 실행 후 `to_output()`으로 final response 생성

## 대상 요약

- event_type_l2_id=19 정책/규제 변화: scenario_group 1개, scenario 1개

## 시나리오별 소요시간

| event_type_l2_id | scenario_group_id | scenario_id | status | attempts | 소요시간 | elapsed_seconds |
|---:|---:|---:|---|---:|---:|---:|
| 19 | 48 | 281 | ERROR | 2 | 02:22.610 | 142.610s |

## 호출 결과

### event_type_l2_id=19 정책/규제 변화

- scenario_group_id: 48
- group_title: [model_parameter_agent_test] 정책/규제 routing 검증
- 대상 scenario_ids: [281]
- scenario_count: 1
- 매핑 후보 검증: FAIL
- LLM selected 검증: FAIL
- 라우팅 선택 검증: N/A
- scenario별 value 차이: N/A
- 그룹 종합: FAIL

- ERROR scenario_id=281 elapsed=02:22.610 (142.610s): `MIBaseError('[LLM_INVOCATION_ERROR] LLM 호출 후 비정상 오류가 발생했습니다. - Connection error.')`

## 최종 요약

- ERROR_COUNT: 1
- GROUP_STATUS_BY_SCENARIO_GROUP: `{"48": false}`
- EMPTY_RECOMMENDATIONS: 0
- EMPTY_RECOMMENDATION_SCENARIOS: `[]`

## 오류 및 반복 이력

- scenario_id=281 elapsed=02:22.610 (142.610s) attempts=2 error=`MIBaseError('[LLM_INVOCATION_ERROR] LLM 호출 후 비정상 오류가 발생했습니다. - Connection error.')`
