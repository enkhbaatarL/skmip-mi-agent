# 전체 이벤트타입 2개 시나리오 평가 분석 리포트

- 원본 실행 리포트: `apps/agents/model_parameter_agent/reports/model_parameter_proposal_evaluation_event_types_1_2_3_4_5_6_7_8_9_10_11_12_13_14_15_16_17_18_19_20_21_20260704_015532.md`
- 실행 범위: event_type_l2_id 1~21, 이벤트타입별 scenario_group 1개, 그룹별 scenario 2개
- 실행 시간: 2026-07-04 01:55:32 ~ 02:17:40, 총 1327.346초
- 실행 옵션: concurrency=4, retries=1, max_candidates=30

## 요약

| 항목 | 결과 |
|---|---:|
| 전체 시나리오 | 42 |
| 전체 그룹 | 21 |
| ERROR_COUNT | 0 |
| 그룹 종합 PASS | 21/21 |
| mapping_candidate_coverage PASS | 42/42 |
| selected_result PASS | 42/42 |
| routing_result REVIEW | 1 |
| 빈 추천 | 14/42 |
| proposal 생성 | 28/42 |
| 그룹 내 value 차이 PASS | 14/21 |
| 그룹 내 value 차이 N/A | 7/21 |

전체 실행은 오류 없이 완료됐다. 현재 DB 매핑 기준으로 직접 조정 대상이 없는 이벤트는 빈 추천으로 종료됐고, 이는 실패로 보지 않는 것이 맞다. 빈 추천 그룹은 재고 수준, 해상 운임, 공급망/화물 흐름, 거래 분쟁/헷징, 인덱스 Spread, 정책/규제 변화, 금리/통화다.

## 정확도 평가

자동 판정 기준으로는 모든 시나리오가 mapping 후보 커버리지와 selected 결과를 통과했다. 비어 있지 않은 14개 그룹은 모두 두 시나리오 간 proposal signature가 달라졌고, dimension value 변화에 따라 슬롯 수 또는 값이 달라졌다.

주요 긍정 사례:

| event_type | 비교 | 관찰 |
|---:|---|---|
| 1 Upstream Utilization | 283 -> 284 | `<5%, 1개월, 대체공급 100%`에서 `60%, 6개월, 대체공급 25%`로 바뀌며 slot 48 -> 97, value cell 24 -> 97로 확대. SupplyDisruption도 0.01 -> 0.225로 커짐. |
| 2 터미널 Utilization | 105 -> 106 | slot 6 -> 18, LiqProdAdjustment 추가. 큰/영구 차질에서 파라미터 범위가 확대됨. |
| 4 파이프라인 Utilization | 285 -> 286 | 단기 송출 증가와 장기 송출 차질이 부호/범위 차이로 반영되고 slot 46 -> 96으로 확대. |
| 6 겨울 한파 | 289 -> 290 | 약한 단발 한파 대비 강한 3개월 한파에서 Temperature -2.5 -> -5.0, slot 2 -> 4. |
| 7 여름 폭염 | 291 -> 292 | 약한 단발 폭염 대비 강한 3개월 폭염에서 Temperature +2.0 -> +3.0, slot 4 -> 12. |
| 17 지정학 긴장 | 92 -> 93 | 낮은/단기 차질 대비 중간/3개월 차질에서 slot 17 -> 99, value cell 17 -> 99. |
| 18 경제 제재 | 129 -> 130 | 3개월/낮음 대비 1년/중간으로 바뀌며 slot 19 -> 50. |
| 21 국가별 경기 | 305 -> 306 | 경미/단기에서는 GDP만, 경기 충격/1년에서는 PMI+GDP로 확대되고 slot 3 -> 48. |

검토 필요:

| 항목 | 내용 |
|---|---|
| event_type 11 scenario 280 | expected가 RegasAdjustment+LiqUtilAdjustment였지만 최종 selected는 LiqUtilAdjustment만 남아 routing_result=REVIEW. Step2 slot option에는 RegasAdjustment 축이 있었으나 Step3 최종 응답에서 빠졌다. |
| Step1/1.5 후보 FAIL 표기 | IMO 운송 규제 281/282는 기대값이 빈 추천이라 그룹/selected는 PASS지만, 단계 표에서는 `rule=3, validated=0`이라 FAIL로 보인다. 실패라기보다 "후보가 있었으나 검증으로 제거" 상태다. |
| 값 스케일 점검 | event_type 10, 11, 17 일부 값에서 -50, -20, -14.96 같은 큰 절대값이 관찰된다. 모델/시트의 단위가 ratio인지 percentage point인지 업무 기준으로 확인이 필요하다. |
| basecase warning | VolumeAdjustment, LiqProdAdjustment, PipelineAdjustment 일부는 basecase record 없음 경고가 반복된다. 사용자가 언급한 것처럼 basecase 부재 자체는 오류가 아니지만, 값 산정 근거가 LLM 제안 중심으로 이동한다. |

## 성능 평가

| 구간 | 건수 | 평균 | 중앙값 | 최대 |
|---|---:|---:|---:|---:|
| 전체 시나리오 | 42 | 118.169s | 84.660s | 377.821s |
| proposal 생성 시나리오 | 28 | 165.227s | 116.188s | 377.821s |
| 빈 추천 시나리오 | 14 | 24.051s | 27.608s | 29.217s |

LLM 호출별 성능:

| step | 호출 | 평균 시간 | 최대 시간 | 평균 토큰 | 총 토큰 | 최대 토큰 |
|---|---:|---:|---:|---:|---:|---:|
| Step1.5 candidate validation | 30 | 5.984s | 29.103s | 2,037.7 | 61,132 | 3,997 |
| Step2 slot proposal | 28 | 57.645s | 139.215s | 13,157.6 | 368,412 | 33,086 |
| Step3 value proposal | 28 | 68.853s | 175.442s | 16,259.3 | 455,260 | 39,979 |
| 합계 | 86 | - | - | - | 884,804 | - |

가장 느린 시나리오:

| event_type | scenario | elapsed | slot | value cell | 파라미터 |
|---:|---:|---:|---:|---:|---|
| 11 | 279 | 377.821s | 100 | 100 | SupplyDisruption, LiqUtilAdjustment |
| 1 | 284 | 357.484s | 97 | 97 | SupplyDisruption, LiqUtilAdjustment |
| 17 | 93 | 334.897s | 99 | 99 | LiqUtilAdjustment |
| 11 | 280 | 329.951s | 96 | 96 | LiqUtilAdjustment |
| 4 | 286 | 323.315s | 96 | 96 | PipelineAdjustment, LiqUtilAdjustment |
| 18 | 130 | 302.132s | 50 | 50 | LiqUtilAdjustment, LiqProdAdjustment, PowerMix |

성능 병목은 Step2/Step3이며, 특히 basecase raw row가 21,656~62,912개까지 올라간 뒤 100개 prompt record로 제한되는 supply 계열 이벤트에서 두드러진다. Step2가 슬롯을 90개 이상 고르는 경우 Step3 completion token도 크게 증가한다.

## IMO 운송 규제 후보 원인

ShippingCost는 Step1 후보가 아니었다.

- `tmm_mi_model_param_m` 기준 ShippingCost: `use_yn=N`, `del_yn=N`
- event_type 19의 ShippingCost 관련 매핑: `mapping_method=na`, `model_param_id=NULL`

IMO 281/282의 실제 흐름:

| scenario | Step1 후보 | Step1.5 validated | final selected |
|---:|---:|---:|---:|
| 281 | 3 | 0 | 0 |
| 282 | 3 | 0 | 0 |

Step1에서 잡힌 3개는 `impact_intensity`의 routing 매핑인 PowerMix, Coal Futures Price, Gas Futures Price다. 각 mapping comment는 "정책 영향이 발전/수요 전환이면 PowerMix 또는 CoalGasAdjustment로 라우팅하고, 무역/운송 규제는 수급모델 input 대상에서 제외"라는 조건문 성격이다. Step1은 comment를 해석하지 않고 event_type/dimension/routing/활성 파라미터 기준으로 후보를 올리고, Step1.5가 IMO 이벤트가 운송 규제임을 해석해 3개를 모두 제거했다.

## 결론

현재 기준으로 전체 테스트는 안정적으로 완료됐고, DB 매핑을 하드코딩 없이 반영한다. 같은 그룹 내 시나리오 차등 추천은 proposal이 있는 14개 그룹에서는 모두 발생했다. 다만 정확도 측면에서는 event_type 11 scenario 280의 RegasAdjustment 누락, 일부 대형 절대값의 단위/스케일, 대량 basecase 후보에서 Step2/Step3 토큰이 커지는 문제를 후속 개선 대상으로 보는 것이 좋다.
