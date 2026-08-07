# Basecase와 LUT를 읽고 사용하는 방법

## 1. 기준 범위

Model Parameter Agent는 DB mapping이 허용한 활성 파라미터에 대해서만 Basecase와 LUT exact slot을 만든다. 현재 canonical 기준은 master 21행 중 10개 활성, dimension mapping 129행이며 공개 API payload는 바뀌지 않는다.

Basecase는 Demand·Supply·Trade workbook의 현재 모델 입력값이고, LUT는 Basecase가 없는 exact slot의 기준값을 제공한다. 둘 다 후보 파라미터를 새로 만들지는 않는다.

### 1.1 S3 호환 Object Storage에서 파일을 준비하는 구조

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
| tmm_mi_model_param_dimension_map | event type·dimension에서 허용되는 direct/routing 후보와 comment, indirect 보조정보 |
| tmm_mi_model_param_m | parameter 이름·hint, 모델 target, Basecase Sheet·행·열 규칙 |
| config.yaml > model_parameter_resources.basecase | workbook local path와 Object Storage key |
| config.yaml > model_parameter_resources.lut | enabled, adapter, files, required header, key_axes, metadata_axes |
| config.yaml > model_parameter_resources.references | runtime 보조 CSV; 독립 parameter record는 만들지 않음 |
| 공통 설정 | 2026~2030 horizon, 숫자 정밀도, 파라미터별/요청 전체 slot 상한, Step2·Step3 byte 상한 |

envs/config.yaml과 devops/k8s/configmap.yaml의 model_parameter_resources 및 관련 limit은 동일해야 한다. adapter schema는 model-parameter-lut-adapters-v3으로 catalog hash에 포함되어 이전 cache와 분리된다.

## 3. 활성 LUT 10개

| Parameter | Adapter | exact key axes | 값 또는 계산 |
|---|---|---|---|
| GDP | gdp_growth | Country, Year | GDP 성장률 |
| PMI | pmi_reference | Country, Year, Month | 수요 국가를 reference country에 연결한 PMI 절대값 |
| PowerMix | tabular(row) | Country, Year, Energy Source | 발전 비중 |
| Temperature | temperature_degree_days | Country, Year, Month | HDD>0: 18-HDD/30, CDD>0: 18+CDD/30, 둘 다 0: 18°C |
| Population | population | Country, Year | Population (thousands) 절대값 |
| HurricaneIntensity | hurricane_intensity | Year, Month | 강도표·GoM 영향 시설을 검증하고 무허리케인 기준 0 |
| LiqProdAdjustment | liq_prod | Country, LNG Plant, LNG Plant Train, Year, Month | 월 생산능력 × 이용률 |
| LiqUtilAdjustment | liq_util | Country, LNG Plant, LNG Plant Train, Year, Month | 월 이용률 0~1 |
| PipelineAdjustment | pipeline | Pipeline Name, From Country, To Country, Year, Month | 연간 capacity를 12개월로 확장 |
| SupplyDisruption | supply_disruption | Country, Year, Month | 연간 공급량 × 원본 월 계수 후 Country별 합산 |

LiqProd와 LiqUtil은 BCLiquefaction.csv를 공유한다. Closed 시설은 제외하며 생산능력·이용률의 숫자/결측을 검증한다. SupplyDisruption은 Seasonality 값을 재정규화하지 않고 동일 Country/Year/Month로 귀결되는 생산 row는 합산한다.

## 4. 보류 LUT와 보조 reference

- Coal Futures Price와 Gas Futures Price는 futures_price adapter, enabled=false다. CSV 다운로드와 header 검증은 하지만 2026년 이후 strip이 없으므로 catalog record를 만들지 않는다.
- ElectrificationRate는 유효 Basecase·국가/연/Drive Train LUT·승인 mapping이 없어 LUT spec 자체를 만들지 않는다.
- demand_general_country_list는 Demand_Model_LUT_General_value_based_t6.csv를 검증·동기화하는 reference다.
- resources/lut의 모든 CSV는 활성 spec, disabled spec 또는 reference 중 하나에 선언되어야 한다.

## 5. Basecase와 LUT 중 무엇을 선택하나

1. direct/routing mapping과 활성 master로 후보를 확정한다.
2. master의 basecase_* 규칙으로 workbook record를 읽고 config adapter로 LUT record를 읽는다.
3. key_axes 전체가 같은 exact slot끼리만 결합한다. nearest·부분 key·서로 다른 시설의 축 조합은 금지한다.
4. 같은 slot에 Basecase 값이 있으면 그것을 effective reference로 쓴다.
5. Basecase가 없고 LUT만 있으면 LUT를 쓰며 저장되는 basecaseValue는 null이다.
6. 둘 다 없으면 그 slot은 제외한다.

Step2에는 값·source·원본 record를 보내지 않는다. 동일 기간을 period_groups로 묶고 Country→Plant→Train 고정축을 fixed_axis_hierarchy로 중첩한다. Step3에는 exact 검증된 slot의 좌표와 단일 effective reference만 전달한다.

## 6. 검증 규칙

startup과 자동화 테스트는 다음을 실패로 처리한다.

- horizon 밖 값만 존재하거나 활성 parameter record가 0개
- 필수 header 누락, 숫자 형식 오류, 필수 key/value 빈 값
- 같은 exact key의 상충 값, join 누락, 허용되지 않은 시설 상태
- config.yaml/ConfigMap 차이, 선언되지 않은 packaged CSV, 잘못된 object prefix
- 파라미터별 100개, 요청 전체 slot 상한, Step2·Step3 compact JSON byte 상한 초과

byte 상한을 넘으면 LLM을 호출하지 않고 actual/limit byte와 parameter별 byte를 포함한 INVALID_REQUEST를 반환한다. LiqUtil 단독 평면 catalog 약 129KB·약 40K input token을 기준선으로 삼고, 실제 테스트 리포트에는 provider input/output/total token과 실행시간을 기록한다.

정확한 파일명·header·object key는 envs/config.yaml, 최종 master·mapping·공식은 resources/Model_Parameter_Base_Case_Mapping.md가 canonical 기준이다.
