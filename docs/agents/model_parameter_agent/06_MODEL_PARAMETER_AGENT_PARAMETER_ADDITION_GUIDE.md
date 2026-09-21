# Model Parameter 추가·활성화 가이드

## 1. 체크인 기준선

현재 저장소의 runtime 판정 기준은 `model-parameter-canonical-v4-0030`과
`model-impact-lever-canonical-v4-0030` successor다. 기존 이름의 canonical은 0029 역사 릴리스로 보존한다.
아래 개수는 live DB 조회 결과가 아니라 체크인된 canonical 기준선이다. 실제 적용 상태는 runner preflight와
적용 후 DB read-back으로 확인한다.

- master 21행, 활성 14개: GDP, PMI, PowerMix, Temperature, Population, User-Adjusted Gas Demand, HurricaneIntensity, LiqProdAdjustment, LiqUtilAdjustment, PipelineAdjustment, RegasAdjustment, SupplyDisruption, PNG Contract Volume, ShippingCost
- LUT-backed 활성 10개와 Basecase-only 활성 4개: User-Adjusted Gas Demand, RegasAdjustment, PNG Contract Volume, ShippingCost
- v4 active Lever 18개, binding occurrence 16개, effective executable occurrence/고유 Parameter 14개
- legacy dimension mapping 129행은 v4가 읽거나 변경하지 않는 보호 대상 invariant다.
- v1/v3 신규 proposal 이름 allow-list 5개: GDP, PMI, PowerMix, Temperature, LiqUtilAdjustment
- v4 extend7 capability 7개: 위 5개 + PipelineAdjustment(ID 15), SupplyDisruption(ID 17)
- extend7 7개의 v4 `multi_event_model_lever_dimensions` 기준값은 하나의 `read_only_proposal` contract
  `model-parameter-workbook-contract-v2.json`을 사용한다. 변경되지 않은 Excel artifact는
  `resources/basecase_v4/new-bc-v1/`의 digest를 재사용하고, v1/v3는 기존 `resources/basecase/`를 유지한다.
- 추가 2개도 기존 5개와 같은 contract reference→exact LUT fallback→slot/evidence/value 절차를 사용하며,
  v4에는 별도 legacy Basecase reference mode를 두지 않는다.
- source matching 뒤 LLM과 proposal persistence 전에 version별 capability gate를 적용한다. v4는 Step1.5를 호출하지 않는다.
- 공개 proposal/confirmation API와 payload, confirmation 동작은 변경하지 않는다.
- DB migration 정본은 sibling mgmt revision `a378b54ef997`이며, Agent fixture는
  `scripts/model_parameter/model-parameter-canonical-v4-0030.json`과
  `scripts/model_parameter/model-impact-lever-canonical-v4-0030.json`이다.
- 260813 workbook과 `resources/Model_Parameter_Base_Case_Mapping.md`는 0029 역사 기준선이다. 0030 적용 입력이나
  현재 binding 판정에 사용하지 않는다.

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
5. 신규 proposal을 허용할 parameter인지 별도 승인하고 ID 기반 capability contract 변경 범위와 회귀 테스트를 확정한다.
6. 동일 Lever의 primary/alternative가 raw 후보가 되는 것이 의도인지 확인한다. v4는 Step1.5 없이 lineage를
   모두 보존하고 exact slot/evidence 단계에서 applicability와 Scenario/Event/Lever 맥락을 판정한다.
7. 대규모 시설 catalog가 slot·prompt byte 상한 안에 들어오는지 측정한다.
8. v4 workbook contract 대상이면 authoritative source와 write target을 분리하고, digest·sheet·header·range,
   expected record 수, exact-key 오류 차단, fallback·evidence·atomic 정책을 함께 확정한다.

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

## 4. LUT와 v4 workbook resource 변경

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

runtime proposal 범위를 제한하기 위해 DB, canonical JSON/SQL, config, LUT, Basecase workbook을 축소하지 않는다.
v4 runtime은 active parameter definition과 catalog binding에 필요한 resource를 사용한다. 기존 v1/v3 Basecase
preload의 누락·파싱 오류·0건은 warning으로 남기며, 활성 14개 capability 전체는 자동화·release
acceptance에서 별도로 검증한다. v4 `new-bc-v2` startup은 contract schema/path와 contract에 고정된
Workbook path/digest만 경량 검증한다. sheet·header·range·변환·고정 record count는 최초 exact v4 materialization에서
fail closed하고 성공 결과를 process cache한다.

### versioned workbook 계약을 변경하거나 확장할 때

현재 extend7의 v4-only reference는 `resources/contracts/model-parameter-workbook-contract-v2.json`이 소유한다.
변경되지 않은 workbook은 `resources/basecase_v4/new-bc-v1/` digest를 재사용할 수 있지만, 계약 coverage·parser·hash가
바뀌면 새 release ID와 새 contract 파일을 만든다. 기존 `resources/basecase/` 파일을 덮어쓰거나
`new_resources/`를 runtime path로 연결하지 않는다.

향후 7→10→14처럼 proposal 범위를 확대할 때는 기존 5개가 사용하는 방식을 기본 불변 조건으로 삼는다.

1. 새 Parameter를 현재 versioned workbook contract에 선언하고 authoritative source, write target, exact axes,
   변환, record count, constraints를 고정한다.
2. capability `reference_mode`는 공통 `v4_workbook_then_lut`를 사용한다. 새 Parameter만 legacy Basecase parser로
   우회하는 mode를 추가하지 않는다.
3. 공통 candidate→contract reference→same-exact-key LUT fallback→Step2 exact slot→evidence→Step3 value→persistence
   순서를 그대로 사용한다. 파라미터별 차이는 contract parser·축·제약에만 둔다.
4. authoritative source가 현재 workbook에 없으면 먼저 versioned workbook/auxiliary source 계약을 준비한다.
   이를 생략하고 LUT-only 또는 legacy-only로 활성화하려면 별도 설계 승인과 문서화가 필요하다.
5. 기존 5개와 새 Parameter를 함께 parameterized regression으로 검증하며 public API와 proposal JSON은 유지한다.

- 계약 capability는 writer/engine 승인 전까지 `read_only_proposal`로 유지한다.
- authoritative source와 기존 DB write target, key/metadata axes, 단위·absolute-value 의미를 분리해 선언한다.
- 신규 source가 정상적으로 없는 exact key에만 기존 LUT fallback을 허용한다. non-finite·cached error·상충
  duplicate key는 명시적으로 차단해 LUT로 복구하지 않는다.
- PowerMix는 authoritative raw source fraction의 원본 정밀도를 보존하고 재정규화하지 않는다. Country/Year별
  승인된 10-member 완전성·중복·유한성·0~1·합 1로 atomic 검증하며, Basecase/LUT 결합 effective vector와
  Step3 proposed vector에도 합 1과 `1e-6` 허용오차를 다시 적용한다.
- LiqUtilAdjustment는 한 Lever provenance 안에서 exact Plant와 exact Train 둘 모두, slot과 일치하는
  Year/Month, Group에 실제로 연결된 source Event와 직접 운영 근거가 있어야 하며, 음수만 차단하고
  1 초과값을 보존한다. lifecycle 공란은 exact record를 제외하지 않고 metadata/applicability에서만 생략한다.
- contract schema/hash 또는 workbook digest가 달라지면 같은 release ID를 재사용하지 않고 version을 올린다.

현재 고정 source 회귀 수는 GDP 815, PMI 5,040, PowerMix 4,200, Temperature 5,040,
LiqUtilAdjustment 23,820, PipelineAdjustment 420, SupplyDisruption 4,908이다. 변경 release에서는 새 digest와 실제 count를 함께 검토하되, count를 맞추기 위해
invalid key를 임의 보간하거나 nearest/fuzzy fallback하지 않는다.

## 5. LiqProdAdjustment 적용 사례

LiqProdAdjustment는 체크인 canonical/resource capability에서 활성이고 미지원 항목이 아니다. live DB 활성 여부는 read-back으로 확인해야 한다. 다만 현재 runtime proposal allow-list 밖이므로 신규 proposal에서는 차단된다.

- master ID 13, use_yn=Y
- adapter liq_prod
- source BCLiquefaction.csv
- key Country, LNG Plant, LNG Plant Train, Year, Month
- value 월 생산능력 × LNG plant utilisation
- Closed 시설 제외
- v4 `liquefaction_production_override` Lever의 primary binding으로 capability를 보존

v4에서는 `liquefaction_utilization`과 `liquefaction_production_override`를 분리한다. source matching 직후 gate가
LiqProdAdjustment를 제외하므로 현재는 LiqUtilAdjustment만 이후 단계에 진입한다. legacy mapping은 후보 source나
fallback으로 사용하지 않는다.

## 6. 0030 v4 raw Lever binding과 extend7 밖 활성 7개의 핵심 규칙

| Lever | Parameter binding |
|---|---|
| `weather_demand` | Temperature primary; HDD/CDD alternative(비활성 진단) |
| `power_generation_mix` | PowerMix primary |
| `population_demographics` | Population primary |
| `economic_activity` | GDP primary; PMI alternative |
| `direct_gas_demand` | User-Adjusted Gas Demand primary |
| `upstream_production` | SupplyDisruption primary |
| `liquefaction_utilization` | LiqUtilAdjustment primary |
| `liquefaction_production_override` | LiqProdAdjustment primary |
| `regasification_capacity` | RegasAdjustment primary |
| `us_gom_hurricane_disruption` | HurricaneIntensity primary |
| `pipeline_capacity` | PipelineAdjustment primary |
| `lng_charter_rate` | ShippingCost primary |
| `png_contract_volume` | PNG Contract Volume primary |
| `route_disruption`, `trade_restriction` | binding 없음 |

`price_only` Lever는 binding을 두지 않는다. CDD/HDD binding은 capability로 보존하지만 master가 비활성이므로 executable candidate가 아니다.

위 표는 0030 raw Lever binding이다. 현재 v4 신규 proposal에서는 capability gate를 통과한 GDP, PMI,
PowerMix, Temperature, LiqUtilAdjustment, PipelineAdjustment, SupplyDisruption만 이후 단계로 전달한다. 나머지 활성 7개는 capability와 provenance를
유지하지만 `PROPOSAL_SCOPE_EXCLUDED`로 제외한다.

### Basecase-only 활성 4개

| Parameter | 기준값 | v4 Lever binding |
|---|---|---|
| User-Adjusted Gas Demand | 검증된 Basecase exact slot | `direct_gas_demand` primary |
| RegasAdjustment | 검증된 Basecase exact slot | `regasification_capacity` primary |
| PNG Contract Volume | 검증된 Basecase exact slot | `png_contract_volume` primary |
| ShippingCost | 검증된 Basecase exact slot | `lng_charter_rate` primary |

별도 LUT fallback을 추가하지 않는다. Basecase와 LUT가 모두 없는 slot은 제외한다. 이 4개는 현재 runtime proposal
allow-list 밖이다. `RemainingUnrestrictedAmount`와 `VolumeCancelled`는 0030에서 inactive/unbound이므로 새 contract와
forward canonical release 없이 후보화하지 않는다.

## 7. prompt·token 보호

resource release에서 준비된 LUT record는 서버 cache/index에 보관한다. v4 runtime은 지정 version의 active catalog
binding으로 도달 가능한 definition을 사용하며, 활성 14개 capability 전체 검증은 자동화·release acceptance의
책임이다. runtime allow-list gate는 source matching 직후, Step1.5·Step2·Step3 LLM과 proposal persistence 전에 적용한다.

- 파라미터별 반환 상한: model_parameter_max_parameter_slots=100
- 요청 전체 선택 slot 상한: model_parameter_max_total_selected_slots
- 직렬화 상한: model_parameter_max_step2_prompt_bytes, model_parameter_max_step3_prompt_bytes
- 상한 초과: LLM 호출 전 actual/limit과 parameter별 크기를 포함해 실패

proposal Step3의 `proposedValue`는 유한 숫자여야 한다. Confirmation은 `proposedValue` key가 필수지만 값은 `null`일 수 있고, non-null 값만 persistence 경계에서 엄격한 유한 숫자로 정규화한다. 원래 proposal과 같아야 한다는 비교는 없다. 두 경로 모두 설정 기반 소수 자릿수 round/trunc/ceil을 적용하지 않는다. Basecase/LUT 기준값의 adapter 정밀도 정책은 이와 별개로 유지하되 v4 PowerMix source fraction은 atomic sum을 보존하도록 정밀도 변환에서 제외한다. 기존 proposed precision 설정 키는 배포 설정 호환용이며 runtime 제안값을 변환하지 않는다.

## 8. 완료 판정

1. canonical consistency와 resource release·LUT adapter 자동화 테스트가 통과한다.
2. config.yaml과 ConfigMap manifest가 같다.
3. 0030 기준선의 master 21행·활성 14개와 active Lever 18개·binding 16/14/14를 확인하고, DB 적용 작업이면
   hydrated checksum `835e6f2d…be51`을 read-back한다.
4. v4 canonical JSON·SQL, LUT manifest, workbook/archive와 legacy mapping 비변경 digest를 확인한다.
5. resource capability 기준으로 LUT-backed 활성 10개의 selectable LUT slot과 Basecase-only 활성 4개의 exact
   Basecase slot을 확인한다. v4 신규 proposal은 7개만 허용하고 나머지 활성 7개는 `PROPOSAL_SCOPE_EXCLUDED`,
   비활성 7개는 후보 없음으로 검증한다.
6. v4 `new-bc-v2` contract의 세 workbook·auxiliary digest/header와
   815/5,040/4,200/5,040/23,820/420/4,908 record를 확인하고,
   invalid exact-key LUT 차단, PowerMix atomic vector와 LiqUtil evidence/1 초과 보존 회귀를 통과한다.
7. v4 multi-event quality runner로 실제 선택 value에서 도달한 allow-list parameter를 proposal하고, 빈 confirmation rollback, 정상 confirmation, reconfirmation, DB read-back을 수행한다.
8. 실제 리포트에 parameter, candidate, slot, effective reference, proposal, token, 시간·retry와 confirmation ID를 남긴다.

검증 전후 DB·canonical·catalog와 기존 v1/v3 Basecase·업무용 mapping workbook fingerprint가 같아야 한다. 별도로 추가한 v4 contract/config path와 재사용한 `new-bc-v1` workbook artifact는 선언된 digest·header·record count와 일치해야 한다.

catalog checksum이 바뀌면 master와 Lever catalog를 원자적으로 적용한 뒤 신규 v4 Scenario를 생성한다. 기존 v4 Scenario를 새 catalog로 조용히 재해석하지 않는다. Coal/Gas Futures는 실제 2026년 이후 strip이 제공될 때, ElectrificationRate는 국가·연·Drive Train LUT와 승인 binding·capability가 준비될 때 같은 절차로 활성화한다.
