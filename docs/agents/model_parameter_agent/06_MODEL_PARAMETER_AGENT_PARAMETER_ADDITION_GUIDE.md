# Model Parameter 추가·활성화 가이드

## 1. 체크인 기준선

저장소의 변경·release 판정 기준은 `model-parameter-canonical-v4`와 `model-impact-lever-canonical-v4`다.
아래 개수는 live DB 조회 결과가 아니라 체크인된 canonical 기준선이다. 실제 적용 상태는 runner preflight와
적용 후 DB read-back으로 확인한다.

- master 21행, 활성 16개: GDP, PMI, PowerMix, Temperature, Population, User-Adjusted Gas Demand, HurricaneIntensity, LiqProdAdjustment, LiqUtilAdjustment, PipelineAdjustment, RegasAdjustment, SupplyDisruption, PNG Contract Volume, RemainingUnrestrictedAmount, ShippingCost, VolumeCancelled
- LUT-backed 10개와 Basecase-only 6개: User-Adjusted Gas Demand, RegasAdjustment, PNG Contract Volume, RemainingUnrestrictedAmount, ShippingCost, VolumeCancelled
- v4 Lever 16개, binding occurrence 20개, effective executable occurrence 18개, 전역 고유 활성 raw parameter 16개
- legacy dimension mapping 129행은 v4가 읽거나 변경하지 않는 보호 대상 invariant다.
- 신규 proposal runtime allow-list 5개: GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment
- source matching 뒤 Step1.5·Step2·Step3 LLM과 proposal persistence 전에 allow-list gate를 적용한다.
- 공개 proposal/confirmation API와 payload, confirmation 동작은 변경하지 않는다.
- DB에 적용할 canonical 목표값은 `scripts/model_parameter/model-parameter-canonical-v4.json`과 `scripts/model_parameter/model-impact-lever-canonical-v4.json`, 사람이 읽는 표는 `resources/Model_Parameter_Base_Case_Mapping.md`를 따른다.
- 체크인 업무용 표는 `resources/mapping/260813_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.xlsx`다. workbook의 legacy mapping sheet는 변경하지 않는 참고 상태이며 v4 Lever binding의 기계 판정 기준은 v4 JSON이다. 2026-08-13 snapshot은 해당 release의 변경 전 증적이다.

새 파라미터의 DB/canonical/resource capability 활성화는 이름이나 `use_yn` 하나만 바꾸는 작업이 아니다. master, v4 Lever binding, Basecase/LUT capability, resource manifest, prompt 크기, proposal/confirmation 검증을 한 단위로 다룬다. legacy mapping은 신규 v4 rollout의 입력이나 fallback으로 사용하지 않는다. capability를 활성화해도 runtime proposal allow-list에 자동으로 추가되지 않으며, 신규 proposal 허용은 별도 정책 변경과 검증이 필요하다.

반복 가능한 전체 구현은 `$rollout-model-parameters`, release 전체 승인은
`$verify-model-parameter-release`, v4 multi-event proposal·Confirmation 품질 확인은
`$model-parameter-multi-event-quality`를 사용한다. 핵심 Skill은 v4
`multi_event_model_lever_dimensions` 경로만 지원한다.

## 2. 변경 전 확인

1. parameter_name과 모델 target이 수급모델 workbook에 실제로 존재하는지 확인한다.
2. 값의 단위·절대값/증감값 의미·허용 범위를 parameter_hint로 확정한다.
3. exact key axes와 horizon 2026~2030의 기준값이 있는지 확인한다.
4. v4 Lever code와 parameter binding role(primary/alternative), applicability가 승인되었는지 확인한다. legacy direct/routing/indirect/na mapping은 변경하지 않는다.
5. 신규 proposal을 허용할 parameter인지 별도 승인하고 runtime allow-list 변경 범위와 회귀 테스트를 확정한다.
6. 동일 Lever의 primary/alternative가 raw 후보가 되는 것이 의도인지 확인한다. allow-list gate를 통과한 후보 안에서만 Step1.5가 applicability와 Scenario/Event/Lever 맥락으로 primary, alternative 또는 양쪽을 선택할 수 있다.
7. 대규모 시설 catalog가 slot·prompt byte 상한 안에 들어오는지 측정한다.

자료가 부족하면 master `use_yn=N`, binding 미등록 또는 LUT `enabled=false`로 두며 과거값을 임의 이월하지 않는다. Basecase-only는 검증된 exact Basecase slot이 없으면 executable하지 않다.

## 3. DB canonical 변경

tmm_mi_model_param_m에는 다음을 모두 명시한다.

- use_yn, parameter_name, parameter_hint
- model_file, model_sheet, model_table, semantic_axes
- basecase_read_mode와 모든 basecase_* 컬럼
- 수정 감사 컬럼과 del_yn

기본키와 생성 감사 컬럼은 변경하지 않는다. v4 binding은 active Impact Lever catalog가 parameter name, role과 applicability를 소유한다. legacy mapping 전체는 transaction 전후 digest가 같은지 확인하는 invariant로만 취급한다. Flow/node에서 직접 SQL을 작성하지 않고 persistence service를 사용한다.

다음 명령은 128행 snapshot을 사용한 **역사적 v4 canonical rollout 예시**다. 현재 runtime allow-list-only
v0.2.4 작업이나 129행 기준선이 적용된 DB에서는 실행하지 않는다. 이후 DB/canonical 변경이 별도로 승인되고 새
snapshot-compatible versioned runner가 준비된 경우에만 그 runner로 dry-run과 apply를 수행한다.

    poetry run python scripts/model_parameter/apply_model_parameter_v4.py

역사적 release에서 검증된 변경을 commit한 명령은 다음과 같다.

    poetry run python scripts/model_parameter/apply_model_parameter_v4.py --apply

위 v4 runner는 기존 snapshot과 함께 보존하는 역사적 release replay다. 현재 live baseline과 다르면 실행하지 않으며, 이후 master/Lever 변경에는 새 snapshot과 versioned runner가 필요하다. allow-list-only 변경에서는 어떤 DB runner도 실행하지 않고 SELECT-only fingerprint 또는 repository diff로 DB 비변경을 확인한다.

workbook은 다음 명령으로 v4 canonical·config·archive와 보호 대상 legacy mapping의 비변경 상태를 확인한다. 이 검사는 v4 Lever canonical 검증을 대신하지 않는다.

    poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only

## 4. LUT와 resource manifest 변경

`apps/agents/model_parameter_agent/new_resources/`는 신규 Basecase/LUT를 받는 staging 경로다. 현재처럼
`new_resources/lut/`가 없거나 LUT가 아직 들어오지 않은 상태는 정상이다. runtime과 manifest는 이 경로를
직접 읽지 않는다. 신규 LUT가 도착하면 `.DS_Store`, `~$*` 같은 임시 파일을 제외하고 파일명·크기·digest와
기존 `resources/lut/` 충돌을 먼저 확인한다. 검증·승인이 끝난 파일만 canonical `resources/lut/`로 승격하고
adapter, manifest, config/ConfigMap, canonical/workbook/docs/tests를 함께 갱신한다. staging 원본은 사용자가
별도로 요청하지 않는 한 이동·삭제·덮어쓰기하지 않는다.

envs/config.yaml과 devops/k8s/configmap.yaml을 같이 수정한다.

- 활성 parameter: enabled=true, adapter, files, required_columns, key_axes, 필요 시 metadata_axes
- 보류 parameter: enabled=false로 다운로드·구조 검증만 수행
- 보조 파일: references에 등록하고 독립 parameter catalog를 만들지 않음
- object key: fundamental_model_artifact/LUT/demand/... 또는 supply/supply_bc/...
- adapter 동작 변경: ADAPTER_SCHEMA_VERSION을 올려 runtime cache 분리

adapter는 필수 header, horizon, 숫자 형식, 빈 값, exact-key 충돌, join 누락, 시설 상태와 정밀도 정책을 검증해야 한다. 모든 packaged CSV가 활성·보류·reference 중 하나로 분류되어야 한다.

runtime proposal 범위를 제한하기 위해 DB, canonical JSON/SQL, config, LUT, Basecase workbook을 축소하지 않는다. v4 runtime은 active parameter definition과 catalog binding에 필요한 resource를 사용한다. Basecase 누락·파싱 오류·0건은 현재 runtime 정책에 따라 warning으로 남기며, 활성 16개 capability 전체는 자동화·release acceptance에서 별도로 검증한다.

## 5. LiqProdAdjustment 적용 사례

LiqProdAdjustment는 체크인 canonical/resource capability에서 활성이고 미지원 항목이 아니다. live DB 활성 여부는 read-back으로 확인해야 한다. 다만 현재 runtime proposal allow-list 밖이므로 신규 proposal에서는 차단된다.

- master ID 13, use_yn=Y
- adapter liq_prod
- source BCLiquefaction.csv
- key Country, LNG Plant, LNG Plant Train, Year, Month
- value 월 생산능력 × LNG plant utilisation
- Closed 시설 제외
- v4 `liquefaction_availability` Lever의 alternative binding으로 capability를 보존

v4에서는 `liquefaction_availability` Lever가 LiqUtilAdjustment primary와 LiqProdAdjustment alternative의 raw binding을 유지한다. source matching 직후 gate가 LiqProdAdjustment를 제외하므로 Step1.5에는 현재 LiqUtilAdjustment만 진입한다. legacy mapping은 후보 source나 fallback으로 사용하지 않으며, runtime 제한을 이유로 DB/config/canonical/workbook을 축소하지 않는다.

## 6. v4 raw Lever binding과 신규 활성 6개의 핵심 규칙

| Lever | Parameter binding |
|---|---|
| `weather_demand` | Temperature primary; HDD/CDD alternative(비활성 진단) |
| `power_generation_mix` | PowerMix primary |
| `economic_activity` | GDP primary; PMI alternative; Population alternative(인구·이민·인구전망이 명시된 경우만) |
| `direct_gas_demand` | User-Adjusted Gas Demand primary |
| `upstream_production` | SupplyDisruption primary |
| `liquefaction_availability` | LiqUtilAdjustment primary; LiqProdAdjustment alternative |
| `regasification_capacity` | RegasAdjustment primary |
| `natural_disaster_disruption` | HurricaneIntensity primary |
| `pipeline_capacity` | PipelineAdjustment primary |
| `shipping_cost`, `route_disruption` | ShippingCost primary |
| `contract_volume` | VolumeCancelled primary; PNG Contract Volume alternative |
| `trade_restriction` | RemainingUnrestrictedAmount primary; VolumeCancelled alternative |

`price_only` Lever는 binding을 두지 않는다. CDD/HDD binding은 capability로 보존하지만 master가 비활성이므로 executable candidate가 아니다.

위 표는 canonical/resource capability의 raw Lever binding이다. 현재 신규 proposal에서는 이 binding으로 source matching한 뒤 runtime allow-list gate를 통과한 GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment만 Step1.5 이후 단계로 전달한다. 나머지 활성 11개는 capability와 provenance를 유지하지만 `PROPOSAL_SCOPE_EXCLUDED`로 제외한다.

### Basecase-only 6개

| Parameter | 기준값 | v4 Lever binding |
|---|---|---|
| User-Adjusted Gas Demand | 검증된 Basecase exact slot | `direct_gas_demand` primary |
| RegasAdjustment | 검증된 Basecase exact slot | `regasification_capacity` primary |
| PNG Contract Volume | 검증된 Basecase exact slot | `contract_volume` alternative |
| RemainingUnrestrictedAmount | 검증된 Basecase exact slot | `trade_restriction` primary |
| ShippingCost | 검증된 Basecase exact slot | `shipping_cost`, `route_disruption` primary |
| VolumeCancelled | 검증된 Basecase exact slot | `contract_volume` primary, `trade_restriction` alternative |

별도 LUT fallback을 추가하지 않는다. Basecase와 LUT가 모두 없는 slot은 제외한다. 이 6개는 canonical과 release 검증의 resource capability에는 남아 있지만 runtime startup이 모든 exact slot의 존재를 강제하지 않는다. 현재 runtime proposal allow-list 밖이므로 신규 proposal에는 진입하지 않는다.

## 7. prompt·token 보호

resource release에서 준비된 LUT record는 서버 cache/index에 보관한다. v4 runtime은 active catalog binding으로 도달 가능한 definition을 사용하며, 활성 16개 capability 전체 검증은 자동화·release acceptance의 책임이다. runtime allow-list gate는 source matching 직후, Step1.5·Step2·Step3 LLM과 proposal persistence 전에 적용한다. Step2는 gate를 통과한 parameter의 period_groups와 fixed_axis_hierarchy만 전송하고, Step3는 exact 검증된 slot의 단일 effective reference만 전송한다.

- 파라미터별 반환 상한: model_parameter_max_parameter_slots=100
- 요청 전체 선택 slot 상한: model_parameter_max_total_selected_slots
- 직렬화 상한: model_parameter_max_step2_prompt_bytes, model_parameter_max_step3_prompt_bytes
- 상한 초과: LLM 호출 전 actual/limit과 parameter별 크기를 포함해 실패

proposal Step3의 `proposedValue`는 유한 숫자여야 한다. Confirmation은 `proposedValue` key가 필수지만 값은 `null`일 수 있고, non-null 값만 persistence 경계에서 엄격한 유한 숫자로 정규화한다. 원래 proposal과 같아야 한다는 비교는 없다. 두 경로 모두 설정 기반 소수 자릿수 round/trunc/ceil을 적용하지 않는다. Basecase/LUT 기준값의 adapter 정밀도 정책은 이와 별개로 유지한다. 기존 proposed precision 설정 키는 배포 설정 호환용이며 runtime 제안값을 변환하지 않는다.

## 8. 완료 판정

1. canonical consistency와 resource release·LUT adapter 자동화 테스트가 통과한다.
2. config.yaml과 ConfigMap manifest가 같다.
3. 체크인 기준선의 master 21행·활성 16개와 Lever 16개·binding 20/18/16을 확인하고, DB 적용 작업이면 같은 값과 hydrated checksum을 read-back한다.
4. v4 canonical JSON·SQL, LUT manifest, workbook/archive와 legacy mapping 비변경 digest를 확인한다.
5. resource capability 기준으로 LUT-backed 10개의 selectable LUT slot과 Basecase-only 6개의 검증된 exact Basecase slot을 확인한다. 별도로 신규 proposal 결과는 GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment 5개만 허용하고 나머지 활성 11개는 `PROPOSAL_SCOPE_EXCLUDED`, 비활성 5개는 후보 없음으로 검증한다.
6. v4 multi-event quality runner로 실제 선택 value에서 도달한 allow-list parameter를 proposal하고, 빈 confirmation rollback, 정상 confirmation, reconfirmation, DB read-back을 수행한다.
7. 실제 리포트에 parameter, candidate, slot, effective reference, proposal, token, 시간·retry와 confirmation ID를 남긴다.

검증 전후 DB/config/canonical/workbook fingerprint가 같아야 하며, runtime proposal 제한 때문에 이 산출물을 갱신하지 않는다.

catalog checksum이 바뀌면 master와 Lever catalog를 원자적으로 적용한 뒤 신규 v4 Scenario를 생성한다. 기존 v4 Scenario를 새 catalog로 조용히 재해석하지 않는다. Coal/Gas Futures는 실제 2026년 이후 strip이 제공될 때, ElectrificationRate는 국가·연·Drive Train LUT와 승인 binding·capability가 준비될 때 같은 절차로 활성화한다.
