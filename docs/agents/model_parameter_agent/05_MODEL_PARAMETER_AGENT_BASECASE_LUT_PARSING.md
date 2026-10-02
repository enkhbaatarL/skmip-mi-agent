# Basecase와 LUT를 읽고 사용하는 방법

> 현재 핵심 Skill은 v4 multi-event proposal에 사용되는 Basecase/LUT와 Impact Lever binding만
> release 대상으로 판정한다. legacy mapping 수치는 비변경 증적일 뿐 v4 resource 선택 기준이 아니다.

## 1. 기준 범위

0032 canonical v4 runtime fixture 기준선은 master 21행 중 활성 14개이며, active resource capability는
LUT-backed 10개와 Basecase-only 4개로 나뉜다. 체크인 v1/v3 shared dimension mapping 129행의
direct/routing 전역 합집합은 LUT-backed parameter 10개에 도달한다. v4는 active Lever 18개에 raw
binding 16개를 가지며, 비활성 CDD/HDD를 제외한 effective executable 전역 합집합은 14개다. 이 수치는
live DB나 요청 하나의 후보 수가 아니다. 실제 신규 proposal은 v1/v3에서 기존 `GDP`, `PMI`, `PowerMix`,
`Temperature`, `LiqUtilAdjustment` 5종을 유지하고, v4 extend14는 LUT-backed 10종에
`User-Adjusted Gas Demand`, `RegasAdjustment`, `PNG Contract Volume`, `ShippingCost`를 더한 ID 기반 14종
capability를 사용한다.

Model Parameter Agent는 source matching으로 raw 후보를 만든 직후, Step1.5·Step2·Step3 LLM과 proposal
persistence 전에 allow-list gate를 적용하고 통과한 파라미터에 대해서만 요청별 Basecase/LUT exact slot을
만든다. runtime 시작 시 resource release와 mapping-reachable definition을 준비하지만, 활성 14개와
Basecase-only 활성 4개의 exact slot을 모두 검증해 0건이면 기동을 실패시키는 구조는 아니다. 체크인 mapping
기준으로 KB/preload 대상은 도달 가능한 10개 정의이며, Basecase preload의 누락·파싱 오류·0건은 warning을
남기고 계속한다. 공개 API payload와 confirmation 동작은 바뀌지 않는다.

Basecase는 Demand·Supply·Trade workbook의 모델 입력값이고, LUT는 Basecase가 없는 exact slot의 기준값을
제공한다. 둘 다 후보 파라미터를 새로 만들지는 않는다. 다만 정확히 v4
`multi_event_model_lever_dimensions`인 요청은 아래 `new-bc-v6` 계약의 authoritative reference를
Basecase로 사용하고, v1/v3는 기존 `resources/basecase/`와 DB `basecase_*` 파서를 그대로 사용한다.

### 1.1 v4 `new-bc-v6` read-only proposal 계약

계약 파일은
`apps/agents/model_parameter_agent/resources/contracts/model-parameter-workbook-contract-v6.json`이며, 변경되지 않은
세 workbook은 `resources/basecase_v4/new-bc-v1/`의 고정 digest를 재사용한다. v6는 v5 계약을 상속한 뒤
Basecase-only 4종의 exact source와 write target을 추가한다. 기존
`resources/basecase/{Demand,Supply,Trade} Model_Input.xlsm`을 교체하지 않으므로 v1/v3 Basecase 파싱은
영향받지 않는다. `new_resources/`는 incoming staging일 뿐 runtime이 탐색하지 않는다.

계약의 capability는 `read_only_proposal`이다. read-only는 Workbook/reference 경계이며 기존 proposal
persistence를 비활성화한다는 뜻이 아니다. startup은 contract schema/path와 contract에 고정된
Workbook path/digest만 경량 검증한다. 최초 exact v4 기준값 조회가 authoritative source를 materialize할 때
sheet·header·range·변환과 아래 2026~2030 record 수를 전체 검증하고 결과를 process cache한다.

| Parameter | authoritative source | exact key·변환 | record 수 |
|---|---|---|---:|
| `GDP` | Demand `BCInput` Q:U | Country, Year; GDP level의 전년 대비 성장률 | 815 |
| `PMI` | Demand `PMIInput` V:AL | Country, Year, Month; Base Case year columns | 5,040 |
| `PowerMix` | Demand `BCInput` Z:AF | Country, Year, Energy Source; 월별 반복 annual 값이 모두 같을 때 dedupe | 4,200 |
| `Temperature` | Demand `WeatherInput` EI:EY | Country, Year, Month; Base Case year columns | 5,040 |
| `Population` | Demand `BCInput` Q:V | Country, Year; Population (thousands) 절대값 | 845 |
| `HurricaneIntensity` | Supply `BCHurricanes` B:K | Year, Month; 강도 1~4와 승인 영향 시설 검증 후 no-hurricane 0 기준선 | 60 |
| `LiqProdAdjustment` | Supply `BCLiquefaction` B:N | Country, Plant, Train, Year, Month; capacity × utilization 후 write target exact 정렬 | 23,820 |
| `LiqUtilAdjustment` | Supply `BCLiquefaction` B:N | Country, LNG Plant, LNG Plant Train, Year, Month; Period/lifecycle/nameplate는 metadata이며 lifecycle 공란은 허용 | 23,820 |
| `PipelineAdjustment` | Supply `BCPipeline` B:F | Pipeline Name, From/To Country, Year, Month; 연간 capacity를 12개월로 확장 | 420 |
| `SupplyDisruption` | Supply `BCProduction` C:K + `SeasonalityLogic.csv` | Country, Year, Month; 원본 Mt 연간값에 월 계수를 적용해 집계 | 4,908 |
| `User-Adjusted Gas Demand` | Demand `DemandOutputOverwrite` D:H | Country, Year, Month, Demand Sub-Sector; BCM 최종 절대값 | 12 |
| `RegasAdjustment` | Supply `RegasAdjustment` B:DK | Continent, Region, Country, Plant, Lifecycle, Nameplate, Year, Month; Mt LNG/month matrix | 22,320 |
| `PNG Contract Volume` | Trade `MidstreamContractInput` A:D | Year, From Country, To Country; Mt LNG 최종 절대값 | 684 |
| `ShippingCost` | Trade `ShippingCostInput` B:F | Year; $/d 최종 절대값 | 5 |

위 표는 값을 읽는 `reference_source`이며 결과를 쓸 `write_target` 표가 아니다. 두 역할은 별도로 검증한다.

| Parameter | reference source | write target |
|---|---|---|
| `Population` | Demand `BCInput` | Demand `GDPPopulationAdjustment` / `table2` |
| `HurricaneIntensity` | Supply `BCHurricanes` | Supply `{USA}Hurricanes` / `table1` |
| `LiqProdAdjustment` | Supply `BCLiquefaction` | Supply `LiqProdAdjustment` / `table1` |
| `PipelineAdjustment` | Supply `BCPipeline` | Supply `PipelineAdjustment` / `table1` |
| `SupplyDisruption` | Supply `BCProduction` + `SeasonalityLogic.csv` | Supply `ProductionAdjustment` / `table2` |
| `User-Adjusted Gas Demand` | Demand `DemandOutputOverwrite` | Demand `DemandOutputOverwrite` / `table1` |
| `RegasAdjustment` | Supply `RegasAdjustment` | Supply `RegasAdjustment` / `table1` |
| `PNG Contract Volume` | Trade `MidstreamContractInput` | Trade `MidstreamContractInput` / `table1` |
| `ShippingCost` | Trade `ShippingCostInput` | Trade `ShippingCostInput` / `table1` |

`BCProduction`이 존재한다는 사실만으로 `ProductionAdjustment`가 검증되는 것은 아니다. 반대로 과거 workbook에
있던 `VolumeAdjustment` 같은 이름을 현재 write target의 별칭으로 추정해서도 안 된다. contract, DB/canonical,
capability와 실제 workbook의 sheet/table/header가 exact match하지 않으면 해당 파라미터 release는 실패다. LUT는
동일 exact key의 기준값 fallback일 뿐, 없는 write target이나 잘못된 DB target을 대체하지 않는다.

기존 adjustment write target에서 관찰된 GDP/PMI/PowerMix/Temperature 좌표 수 93/48/57/150은 append 가능한
`fixed_columns` 대상의 source slot whitelist로 사용하지 않는다. GDP는 2026년 값을 만들기 위해 2025년 level도
읽는다. 반면 LiqUtilAdjustment는 기존 행에 월별 열을 찾아 쓰는 `matrix_time_columns` 대상이므로 예외다.
`new-bc-v6`는 `LiqUtilAdjustment`와 `LiqProdAdjustment` 각각의 33,348개 전체 대상 좌표 중 2026~2030의 23,820개를 읽어 authoritative
source와 exact key가 일치하는지 확인한다. 반환하는 Country/Plant/Train/Lifecycle/Nameplate/Period는 대상 행의
표기를 정본으로 사용한다. 따라서 과거 LUT에만 있는 시설명이나 월간 용량의 단순 12배 값은 공개 slot metadata로
사용하지 않는다. DB의 model target은 write-target identity 검증과 공개 응답 조립에 계속 사용한다.
LiqProd LUT 자체의 2026~2030 record는 19,366개지만 workbook authoritative source와 exact target 교집합은
23,820개다. workbook 우선 정책에서는 23,820개를 정본으로 사용하고, LUT는 workbook에 정상적으로 없는 exact
key만 보충하며 target 밖 시설을 새로 열지 않는다.

### 1.2 S3 호환 Object Storage에서 파일을 준비하는 구조

애플리케이션 시작 시 APP_CONFIG의 model_parameter_resources를 읽어 다음 순서로 immutable resource release를 준비한다.

1. basecase 3개와 LUT·reference의 object key, local path, header 요구사항을 manifest로 만든다.
2. Object Storage가 켜져 있으면 release 임시 폴더로 내려받고 크기·remote identity·필수 header를 검사한다.
3. 원격 준비가 실패하면 packaged resource를 같은 manifest로 검증해 fallback한다.
4. 활성 LUT는 horizon record와 catalog를 만들고, disabled LUT와 references는 구조만 검증한다.
5. 검증된 release만 current로 전환하고 worker runtime에는 immutable 경로를 등록한다.

모든 LUT object key는 fundamental_model_artifact/LUT/demand/... 또는 fundamental_model_artifact/LUT/supply/supply_bc/... 규칙을 사용한다. 같은 BCLiquefaction.csv를 LiqProd와 LiqUtil이 공유해도 한 번만 동기화한다.

## 2. 설정의 역할

### 2.1 DB와 config.yaml은 각각 무엇을 정하나

| 기준 | 정하는 내용 |
|---|---|
| tmm_mi_model_param_dimension_map | v1/v3 event type·dimension에서 허용되는 direct/routing 후보와 comment, indirect 보조정보 |
| tmm_mi_model_impact_lever_m | v4 selected Lever state에서 허용되는 primary/alternative parameter binding과 applicability |
| tmm_mi_model_param_m | parameter 이름·hint, 모델 target, Basecase Sheet·행·열 규칙 |
| proposal capability gate | raw source matching 뒤 실제 신규 proposal에 전달할 v1/v3 5종 또는 v4 extend14 14종 |
| config.yaml > model_parameter_resources.basecase | workbook local path와 Object Storage key |
| config.yaml > model_parameter_resources.workbook_contract | v4 `new-bc-v6` repo-side contract path |
| config.yaml > model_parameter_resources.lut | enabled, adapter, files, required header, key_axes, metadata_axes |
| config.yaml > model_parameter_resources.references | runtime 보조 CSV; 독립 parameter record는 만들지 않음 |
| 공통 설정 | 2026~2030 horizon, Basecase/LUT 기준값 숫자 정밀도(v4 PowerMix raw fraction 제외), 파라미터별/요청 전체 slot 상한, Step2·Step3 byte 상한 |

envs/config.yaml과 devops/k8s/configmap.yaml의 model_parameter_resources 및 관련 limit은 동일해야 한다.
resource schema v6의 semantic hash에는 workbook contract hash와 고정 digest가 포함된다. Workbook reference
cache는 contract hash와 실제 파일 signature를 포함해 다른 release를 재사용하지 않는다. 기존 LUT adapter
schema `model-parameter-lut-adapters-v3`과 Impact Lever hydrated catalog checksum은 각각 별도 authority다.

기존 `model_parameter_proposed_value_max_decimal_places`와 `model_parameter_proposed_value_precision_mode` 설정 키는 배포 설정 호환을 위해 남아 있지만 신규 proposal과 confirmation의 `proposedValue`에는 적용하지 않는다. proposal Step3 값은 유한 숫자여야 한다. Confirmation은 `proposedValue` key를 요구하지만 값은 `null`일 수 있고, non-null 값만 persistence 경계에서 엄격한 유한 숫자로 정규화한다. 두 경로 모두 설정 기반 소수 자릿수 round/trunc/ceil을 하지 않는다.

## 3. LUT-backed 활성 10개

| Parameter | Adapter | exact key axes | 값 또는 계산 |
|---|---|---|---|
| GDP | gdp_growth | Country, Year | GDP 성장률 |
| PMI | pmi_reference | Country, Year, Month | 수요 국가를 reference country에 연결한 PMI 절대값 |
| PowerMix | tabular(row) | Country, Year, Energy Source | 발전 비중 |
| Temperature | temperature_degree_days | Country, Year, Month | HDD>0: 18-HDD/30, CDD>0: 18+CDD/30, 둘 다 0: 18°C |
| Population | population | Country, Year | Population (thousands) 절대값 |
| HurricaneIntensity | hurricane_intensity | Year, Month | 강도표·GoM 영향 시설을 검증하고 무허리케인 기준 0 |
| LiqProdAdjustment | liq_prod | Country, LNG Plant, LNG Plant Train, Year, Month | 월 생산능력 × 이용률 |
| LiqUtilAdjustment | liq_util | Country, LNG Plant, LNG Plant Train, Year, Month | 0 이상의 월 이용률; 관측된 1 초과값도 보존 |
| PipelineAdjustment | pipeline | Pipeline Name, From Country, To Country, Year, Month | 연간 capacity를 12개월로 확장 |
| SupplyDisruption | supply_disruption | Country, Year, Month | 연간 공급량 × 원본 월 계수 후 Country별 합산 |

LiqProd와 LiqUtil은 BCLiquefaction.csv를 공유한다. Closed 시설은 제외하며 생산능력·이용률의 숫자/결측을 검증한다. SupplyDisruption은 Seasonality 값을 재정규화하지 않고 동일 Country/Year/Month로 귀결되는 생산 row는 합산한다.

extend14의 LUT-backed ID 11·12·13·15·17도 `new-bc-v6` workbook contract에서 authoritative source를 먼저 materialize하고, 정상적으로
없는 exact key에만 위 Pipeline 또는 production×seasonality LUT를 사용한다. Pipeline은
`Pipeline Name/From Country/To Country/Year/Month`, Supply는 `Country/Year/Month`가 모두 일치해야 하며
nearest·부분 key fallback은 허용하지 않는다. v4 capability에는 별도 legacy Basecase reference mode가 없다.

이 표의 10개는 체크인 resource/LUT이면서 v4 extend14 proposal capability의 LUT-backed 부분이다. 요청별 selected Lever,
applicability, exact slot과 evidence gate를 통과한 하위 집합만 Step2·Step3에 들어간다. 액화 가용성에서는
단기·부분 차질은 `LiqUtilAdjustment`, 생산량 직접 override·대폭/영구 손실·신규 Train ramp-up은
`LiqProdAdjustment`를 사용한다.

## 4. Basecase-only 활성 4개

`User-Adjusted Gas Demand`, `RegasAdjustment`, `PNG Contract Volume`, `ShippingCost`는 별도 LUT adapter를
만들지 않는다. master의 Basecase 읽기 규칙으로 검증된 exact slot이 있을 때만 executable하다. Basecase
record가 없거나 key/value 검증을 통과하지 못한 slot에는 LUT·유사 시설·부분 key fallback을 적용하지 않고
그 slot을 제외한다.

이 4개 capability는 0032 canonical fixture와 release 검증 기준선에 유지되고 `extend14-v6` 신규 proposal에
진입한다. 단, 등록 LUT가 없으므로 검증된 existing-exact Basecase slot과 직접 증적이 없는 좌표는 abstain한다.
runtime startup은 네 종류의 exact Basecase slot을 모두 미리 materialize하지 않고 최초 v4 조회에서 fail closed한다.
`RemainingUnrestrictedAmount`와 `VolumeCancelled`의 과거 Basecase 좌표는 남아 있어도
0032 canonical master 비활성·active binding 없음 상태이므로 future 계약 전에는 executable하지 않다.

## 5. 보류 LUT와 보조 reference

- Coal Futures Price와 Gas Futures Price는 futures_price adapter, enabled=false다. CSV 다운로드와 header 검증은 하지만 2026년 이후 strip이 없으므로 catalog record를 만들지 않는다.
- ElectrificationRate는 유효 Basecase·국가/연/Drive Train LUT·승인 mapping이 없어 LUT spec 자체를 만들지 않는다.
- demand_general_country_list는 Demand_Model_LUT_General_value_based_t6.csv를 검증·동기화하는 reference다.
- resources/lut의 모든 CSV는 활성 spec, disabled spec 또는 reference 중 하나에 선언되어야 한다.

## 6. Basecase와 LUT 중 무엇을 선택하나

1. v1/v3는 direct/routing mapping, v4는 선택 value의 executable Lever binding과 활성 master로 raw 후보를 만든다.
2. source matching 직후 v1/v3 5종 또는 v4 extend14 14종 capability만 남긴다.
3. v4 contract context는 `new-bc-v6` authoritative record를, v1/v3는 기존 master `basecase_*` record를 읽는다.
4. key_axes 전체가 같은 exact slot끼리만 결합한다. nearest·부분 key·서로 다른 시설의 축 조합은 금지한다.
   `existing_exact` 대상은 최종 workbook에 같은 exact slot이 있어야 하며, 대상에 없는 LUT-only key는 후보에서
   제거한다. `appendable` 대상은 header·axis·unit 계약을 검증한 뒤 새 행을 추가할 수 있으므로 기존 행 존재를
   whitelist로 사용하지 않는다.
5. 같은 slot에 authoritative Basecase 값이 있으면 그것을 effective reference로 쓴다.
6. authoritative source에 exact key가 정상적으로 없을 때만 기존 LUT의 동일 exact key를 fallback으로 쓴다.
7. source cached-value 오류, non-finite 값이나 상충 duplicate로 차단된 exact key는 slot union에서 빼며,
   LUT에 같은 key가 있어도 되살리지 않는다.
8. Basecase-only parameter는 Basecase가 없으면 slot을 제외하고, 양쪽에 값이 없으면 해당 slot을 제외한다.

Step2에는 값·source·원본 record를 보내지 않는다. 동일 기간을 period_groups로 묶고
Country→Plant→Train 고정축을 fixed_axis_hierarchy로 중첩한다. v4에는 상위 branch 과확장을 막기 위해
non-time leaf별 값이 있는 `Life Cycle Category`만 판단 전용 `applicability_attributes`로 추가하며 v1/v3와
반환 `slot_axes`에는 넣지 않는다. lifecycle 공란은 exact key/value가 유효한 record를 제외하지 않고 해당
metadata와 applicability만 생략한다. Step3에는 exact 검증된 slot의 좌표와 단일 effective reference만 전달한다.

PowerMix는 authoritative materialization에서 월별 반복 annual row가 일치할 때만 dedupe하고, 각
`(Country, Year)` raw source group의 승인된 10-member 완전성·중복·유한성·0~1 범위·합 1을 atomic하게
검증한다. source fraction은 기존 Basecase 5자리 정밀도 변환을 건너뛰어 원본 정밀도를 보존하고 재정규화하지
않는다. 유효한 source group에서 Step2가 고른 한 member를 seed로 다음 10개 member 전체를 결정론적으로
확장한다: `Liquids`, `Hydro`, `Solar`, `Wind`, `Bioenergy`, `Gas`, `Coal`, `Nuclear`, `Geothermal`,
`Other`. Basecase 우선·동일 exact LUT fallback을 적용한 effective vector와 Step3의 10개 proposed value도
완전성·중복·0~1 범위와 합이 절대오차 `1e-6` 이내에서 1인지 다시 검증한다. source·effective exact 검증·
slot limit 또는 Step3 응답에서 하나라도 실패하면 vector 전체를 제외한다.

LiqUtilAdjustment는 하나의 같은 v4 Lever provenance에서 액화설비 운영 변화 방향, exact Plant와 exact
Train 둘 모두, slot Year/Month와 일치하는 구체적 `time_window`, `source_event_ids`로 Group의 실제
Event에 연결된 직접 근거가 모두 확인된 slot만 Step3로 보낸다. 부족하면
`ABSTAINED_INSUFFICIENT_EVIDENCE`로 내부 진단하고 숫자를 생성하지 않는다. 값은 음수만 차단하며 1 초과
관측·제안값을 clamp하거나 거부하지 않는다.

## 7. 검증 규칙

runtime startup과 release 검증은 실패 경계가 다르다.

runtime은 resource manifest와 활성 LUT catalog의 파일·header·adapter 계약을 검증하고, DB mapping으로
도달 가능한 parameter definition을 중심으로 KB/cache를 준비한다. 체크인 mapping 기준으로 이 집합은
LUT-backed 10개다. Basecase workbook 누락, 개별 parser 오류 또는 preload record 0건은 warning에 남기고
기동을 계속한다. 따라서 “활성 14개 또는 Basecase-only 활성 4개의 모든 exact slot이 1개 이상이어야 startup
성공”이라고 해석하면 안 된다.

이 warning 정책은 기존 v1/v3 Basecase preload에 대한 설명이다. v4 `new-bc-v6` 계약 파일·Workbook 경로
누락 또는 digest 불일치는 startup에서 fail closed한다. sheet·header·range·변환과
위 14개 source의 고정 record 수 불일치는 최초 exact v4 materialization에서 fail closed하며, 성공 결과는
contract hash와 실제 파일 signature를 key로 process cache한다. 구조는 맞지만 개별 source cell이 잘못된
경우에는 계산 가능한 exact key만 남기고 오류 key는 차단해 내부 warning을 남긴다.

자동화·release acceptance에서는 runtime보다 넓은 체크인 기준선을 별도로 검증한다.

- 0032 canonical runtime fixture master 21행·활성 14개, LUT-backed 활성 10개·Basecase-only 활성 4개 정의의 일관성
- LUT-backed parameter의 horizon 내 selectable LUT record와 Basecase-only parameter의 검증된 exact Basecase slot
- 필수 header 누락, 숫자 형식 오류, 필수 key/value 빈 값
- 같은 exact key의 상충 값, join 누락, 허용되지 않은 시설 상태
- config.yaml/ConfigMap 차이, 선언되지 않은 packaged CSV, 잘못된 object prefix

요청 실행 중에는 파라미터별 100개, 요청 전체 slot 상한, Step2·Step3 compact JSON byte 상한을 적용한다.

byte 상한을 넘으면 LLM을 호출하지 않고 actual/limit byte와 parameter별 byte를 포함한 INVALID_REQUEST를
반환한다. catalog 크기와 token은 resource release와 선택 후보에 따라 달라지므로 실행마다 측정하고, 테스트
보고서에는 provider가 반환한 input/output/total token과 실행시간을 기록한다.

LUT 파일명·header·object key는 `envs/config.yaml`, v4 `new-bc-v6`의 workbook digest·sheet·header·range·record count는 `resources/contracts/model-parameter-workbook-contract-v6.json`이 기준이다. 신규 Scenario Group은 외부개발 DB catalog `v4.0` full pin을 사용하며, v1/v3 mapping은 `scripts/model_parameter/model-parameter-canonical-v1.json`의 `dimension_mappings`를 유지한다.

runtime proposal 제한을 위해 DB·canonical·기존 v1/v3 Basecase·업무용 mapping workbook을 축소하거나 다시 생성하지 않는다. v4 신규 기준값은 별도 versioned contract/workbook resource로만 materialize한다.
