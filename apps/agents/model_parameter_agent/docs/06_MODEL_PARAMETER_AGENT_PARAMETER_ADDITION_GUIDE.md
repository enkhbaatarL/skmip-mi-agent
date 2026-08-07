# Model Parameter 추가·활성화 가이드

## 1. 현재 기준

현재 실행 기준은 model-parameter-canonical-v1이다.

- master 21행, 활성 10개: GDP, PMI, PowerMix, Temperature, Population, HurricaneIntensity, LiqProdAdjustment, LiqUtilAdjustment, PipelineAdjustment, SupplyDisruption
- dimension mapping 129행: direct 35, routing 6, indirect 55, na 33
- 공개 proposal/confirmation API와 payload는 변경하지 않는다.
- 정확한 DB 값은 scripts/model_parameter/model-parameter-canonical-v1.json, 사람이 읽는 표는 resources/Model_Parameter_Base_Case_Mapping.md를 따른다.
- 업무용 현재 표는 resources/mapping/260807_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v1.xlsx이며, archive의 이전 Excel은 실행 기준으로 사용하지 않는다.

새 파라미터 활성화는 이름이나 use_yn 하나만 바꾸는 작업이 아니다. master, 승인 mapping, Basecase/LUT, resource manifest, prompt 크기, proposal/confirmation 검증을 한 단위로 다룬다.

반복 가능한 전체 구현은 `$rollout-model-parameters`, DB 안전성·자동화·실제 proposal/confirmation·통합 리포트 검증은 `$verify-model-parameter-release`를 사용한다. 단일 시나리오 실행만 필요하면 `$model-parameter-agent-test`를 사용한다.

## 2. 변경 전 확인

1. parameter_name과 모델 target이 수급모델 workbook에 실제로 존재하는지 확인한다.
2. 값의 단위·절대값/증감값 의미·허용 범위를 parameter_hint로 확정한다.
3. exact key axes와 horizon 2026~2030의 기준값이 있는지 확인한다.
4. event type·dimension 연결이 승인되었는지, direct/routing/indirect/na 중 어떤 방식인지 확정한다.
5. 동일 dimension의 기존 후보와 동시에 통과하는 것이 의도인지 확인한다. direct끼리는 LLM이 하나를 골라 제거하지 않는다.
6. 대규모 시설 catalog가 slot·prompt byte 상한 안에 들어오는지 측정한다.

자료가 부족하면 master use_yn=N 또는 LUT enabled=false로 두며 과거값을 임의 이월하지 않는다.

## 3. DB canonical 변경

tmm_mi_model_param_m에는 다음을 모두 명시한다.

- use_yn, parameter_name, parameter_hint
- model_file, model_sheet, model_table, semantic_axes
- basecase_read_mode와 모든 basecase_* 컬럼
- 수정 감사 컬럼과 del_yn

기본키와 생성 감사 컬럼은 변경하지 않는다. tmm_mi_model_param_dimension_map은 event_type_l2_id + dimension_key + model_param_id natural key로 대상을 식별하고, mapping_method·comment를 함께 승인한다. Flow/node에서 직접 SQL을 작성하지 않고 persistence service를 사용한다.

적용 전 snapshot을 남기고 기본 dry-run runner를 실행한다.

    poetry run python scripts/model_parameter/apply_canonical.py

검증된 변경만 다음 명령으로 commit한다.

    poetry run python scripts/model_parameter/apply_canonical.py --apply

runner는 행 잠금 뒤 snapshot-or-final precondition, 활성 이름, mapping method count, FK, scenario template key, model_param_id가 있는 natural key 중복과 read-back을 검사한다. MySQL 8 명시 실행용 동일 DML은 scripts/model_parameter/apply_model_parameter_canonical_v1.sql이다. 정적 SQL procedure는 `tests/manual/model_parameter_agent/verify_canonical_sql_mysql.py`로 격리 DB에서 2회 적용과 precondition/post-invariant rollback을 검증한다.

canonical Excel은 다음 명령으로 JSON·config·archive와 정합성을 다시 확인한다.

    poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only

## 4. LUT와 resource manifest 변경

envs/config.yaml과 devops/k8s/configmap.yaml을 같이 수정한다.

- 활성 parameter: enabled=true, adapter, files, required_columns, key_axes, 필요 시 metadata_axes
- 보류 parameter: enabled=false로 다운로드·구조 검증만 수행
- 보조 파일: references에 등록하고 독립 parameter catalog를 만들지 않음
- object key: fundamental_model_artifact/LUT/demand/... 또는 supply/supply_bc/...
- adapter 동작 변경: ADAPTER_SCHEMA_VERSION을 올려 runtime cache 분리

adapter는 필수 header, horizon, 숫자 형식, 빈 값, exact-key 충돌, join 누락, 시설 상태와 정밀도 정책을 검증해야 한다. 모든 packaged CSV가 활성·보류·reference 중 하나로 분류되어야 한다.

## 5. LiqProdAdjustment 적용 사례

LiqProdAdjustment는 더 이상 미지원 항목이 아니다.

- master ID 13, use_yn=Y
- adapter liq_prod
- source BCLiquefaction.csv
- key Country, LNG Plant, LNG Plant Train, Year, Month
- value 월 생산능력 × LNG plant utilisation
- Closed 시설 제외
- event 2·3·17·18 direct 4건과 event 11 affected_facility_type routing 1건 복구

같은 event 2·17·18의 LiqUtilAdjustment direct도 유지된다. 단기·부분 가동률 변화는 LiqUtil, 대폭·영구 손실이나 생산량 직접 override는 LiqProd라는 hint/comment로 의미를 구분하되, direct 후보가 둘 다 생성될 수 있음을 테스트한다.

## 6. 신규 활성 5개의 핵심 규칙

| Parameter | 기준값 | mapping |
|---|---|---|
| Population | GDP/Population CSV의 Population (thousands) | event 21 economic_intensity 제한 routing; 인구·이민·인구전망이 명시된 경우만 |
| HurricaneIntensity | 승인 강도표와 GoM 시설 검증 후 Year/Month 기준 0 | event 11 affected_facility_type routing |
| LiqProdAdjustment | 월 생산능력 × 이용률 | direct 4 + routing 1 |
| PipelineAdjustment | 연간 capacity를 12개월 확장 | direct 2 |
| SupplyDisruption | 연간 production × 원본 seasonality 후 국가별 합산 | direct 4 + routing 1 |

## 7. prompt·token 보호

전체 LUT record는 서버 cache/index에 보관한다. Step2는 period_groups와 fixed_axis_hierarchy만 전송하고, Step3는 exact 검증된 slot의 단일 effective reference만 전송한다.

- 파라미터별 반환 상한: model_parameter_max_parameter_slots=100
- 요청 전체 선택 slot 상한: model_parameter_max_total_selected_slots
- 직렬화 상한: model_parameter_max_step2_prompt_bytes, model_parameter_max_step3_prompt_bytes
- 상한 초과: LLM 호출 전 actual/limit과 parameter별 크기를 포함해 실패

## 8. 완료 판정

1. canonical consistency와 LUT adapter/startup 자동화 테스트가 통과한다.
2. config.yaml과 ConfigMap manifest가 같다.
3. master 21행·mapping 129행 read-back과 활성 10개·method count 35/6/55/33을 확인한다.
4. canonical Excel의 Parameter 21행, Dimension Mapping 129행, LUT manifest와 archive 상태를 확인한다.
5. 활성 10개 각각 selectable LUT slot이 1개 이상이고 비활성 11개가 후보·confirmation allow-list에 없다.
6. target parameter mode로 proposal, 빈 confirmation rollback, 정상 confirmation, reconfirmation, DB read-back을 수행한다.
7. 실제 리포트에 parameter, candidate, slot, effective reference, proposal, token, 시간·retry와 confirmation ID를 남긴다.

Coal/Gas Futures는 실제 2026년 이후 strip이 제공될 때, ElectrificationRate는 국가·연·Drive Train LUT와 승인 mapping이 준비될 때 같은 절차로 활성화한다.
