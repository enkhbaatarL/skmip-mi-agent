# 수급모델 Parameter별 Basecase Load 결과

> 생성 기준: 2026-06-30 현재 `apps/agents/model_parameter_agent`의 기본 매핑 XLSX와 Basecase `.xlsm` 리소스.
> `Parameter Excel Mapping`의 canonical parameter 19개를 각각 후보로 구성해
> 실제 flow와 동일하게 Basecase 매핑 스펙 필드를 포함한 뒤 `build_basecase_records()`를 개별 호출한 결과다.

## 실행 기준

- 매핑 파일: `resources/260625_시나리오가정_MI수급모델_input_매핑_vfShare.xlsx`
- Basecase 폴더: `resources/LNG수급모델_운영버전_입력시트_Basecase_20260610`
- 로딩 함수: `get_parameter_knowledge_base()` + `build_basecase_records()`
- 대상: `Parameter Excel Mapping`에 정의된 canonical parameter 전체
- 후보 구성: 실제 flow처럼 `basecase_read_mode`, `basecase_column_roles`, `basecase_value_*`, `basecase_row_filter` 등 매핑 스펙을 후보 dict에 포함
- 주의: 실제 API 실행에서는 Step1/Step1.5를 통과한 후보만 Basecase를 로드한다. 이 문서는 진단 목적으로 전체 parameter 정의를 개별 로드한 결과다.

## Basecase record 유무 구분

현재 리소스 기준으로 매핑된 Basecase workbook/sheet 자체가 없는 parameter는 없다.
19개 parameter 모두 `model_file + model_sheet`에 해당하는 sheet profile은 존재한다.

다만 `build_basecase_records()`로 실제 값 record가 추출되는지는 다르다.

- Basecase record 있음: `GDP`, `LiqUtilAdjustment`, `PMI`, `PNG Contract Volume`, `PowerMix`, `RegasAdjustment`, `RemainingUnrestrictedAmount`, `ShippingCost`, `Temperature`, `User-Adjusted Gas Demand`, `VolumeCancelled`
- Basecase record 없음: `CDD`, `Coal Futures Price`, `Gas Futures Price`, `HDD`, `HurricaneIntensity`, `LiqProdAdjustment`, `PipelineAdjustment`, `SupplyDisruption`

| 구분 | Parameter | Records | 비고 |
|---|---|---:|---|
| Basecase record 있음 | GDP | 93 | `GDPPopulationAdjustment` |
| Basecase record 있음 | LiqUtilAdjustment | 21,656 | `LiqUtilAdjustment` matrix |
| Basecase record 있음 | PMI | 48 | `PMIAdjustment` |
| Basecase record 있음 | PNG Contract Volume | 1,100 | `MidstreamContractInput` |
| Basecase record 있음 | PowerMix | 57 | `PowerMixAdjustment` |
| Basecase record 있음 | RegasAdjustment | 41,256 | `RegasAdjustment` matrix |
| Basecase record 있음 | RemainingUnrestrictedAmount | 4 | `TradeRestrictionInput` |
| Basecase record 있음 | ShippingCost | 7 | `ShippingCostInput` |
| Basecase record 있음 | Temperature | 150 | `WeatherAdjustment` temperature block |
| Basecase record 있음 | User-Adjusted Gas Demand | 12 | `DemandOutputOverwrite` |
| Basecase record 있음 | VolumeCancelled | 4 | `TradeRestrictionInput` |
| Basecase record 없음 | CDD | 0 | sheet는 있으나 현재 `WeatherAdjustment` CDD block에 추출 값 없음 |
| Basecase record 없음 | Coal Futures Price | 0 | sheet는 있으나 현재 `CoalGasAdjustment` coal futures input block에 추출 값 없음 |
| Basecase record 없음 | Gas Futures Price | 0 | sheet는 있으나 현재 `CoalGasAdjustment` gas futures input block에 추출 값 없음 |
| Basecase record 없음 | HDD | 0 | sheet는 있으나 현재 `WeatherAdjustment` HDD block에 추출 값 없음 |
| Basecase record 없음 | HurricaneIntensity | 0 | sheet는 있으나 현재 `{USA}Hurricanes` 입력 block에 추출 값 없음 |
| Basecase record 없음 | LiqProdAdjustment | 0 | sheet와 matrix 구조는 있으나 현재 값 영역이 비어 있음 |
| Basecase record 없음 | PipelineAdjustment | 0 | sheet는 있으나 현재 user adjusted capacity 값이 비어 있고 From/To 축도 누락 |
| Basecase record 없음 | SupplyDisruption | 0 | 현재 매핑이 문서상 입력 대상인 `H:P` block이 아니라 왼쪽 block을 가리킴 |

정리하면 “Basecase 파일/시트 없음”이 아니라 “현재 Basecase에서 추출 가능한 값 record 없음”인 parameter가 8개다.

## 전체 건수

- canonical parameter 정의: 19개
- Basecase sheet profile: 15개
- 실제 sheet 확인 profile: 15개
- record 추출 성공 parameter: 11개
- record 0건 parameter: 8개
- 총 추출 record: 64,387건
- 전체 조회값 CSV: `reports/basecase_load_values_full_20260630.csv`

## Parameter별 건수

| Parameter | Model | Sheet | Read mode | Sheet size | Records | Axes | Value name | 상태 |
|---|---|---|---|---:|---:|---|---|---|
| CDD | Demand | WeatherAdjustment | fixed_columns | 7997 x 33 | 0 | - | - | WARN |
| Coal Futures Price | Demand | CoalGasAdjustment | fixed_columns | 2000 x 14 | 0 | - | - | WARN |
| Gas Futures Price | Demand | CoalGasAdjustment | fixed_columns | 2000 x 14 | 0 | - | - | WARN |
| GDP | Demand | GDPPopulationAdjustment | fixed_columns | 2000 x 15 | 93 | Year, Country | GDP | OK |
| HDD | Demand | WeatherAdjustment | fixed_columns | 7997 x 33 | 0 | - | - | WARN |
| HurricaneIntensity | Supply | {USA}Hurricanes | fixed_columns | 201 x 12 | 0 | - | - | WARN |
| LiqProdAdjustment | Supply | LiqProdAdjustment | matrix_time_columns | 358 x 213 | 0 | - | - | WARN |
| LiqUtilAdjustment | Supply | LiqUtilAdjustment | matrix_time_columns | 358 x 328 | 21,656 | Country, LNG Plant, LNG Plant Train, Life Cycle Category, Nameplate Capacity, Year, Month, Period | LiqUtilAdjustment | OK |
| PipelineAdjustment | Supply | PipelineAdjustment | fixed_columns | 202 x 28 | 0 | - | - | WARN |
| PMI | Demand | PMIAdjustment | fixed_columns | 8000 x 14 | 48 | Year, Month, Country | PMI | OK |
| PNG Contract Volume | Trade | MidstreamContractInput | fixed_columns | 2918 x 99 | 1,100 | Year, From Country, To Country | PNG Contract Volume | OK |
| PowerMix | Demand | PowerMixAdjustment | fixed_columns | 7989 x 14 | 57 | Year, Country, Energy Source | PowerMix | OK |
| RegasAdjustment | Supply | RegasAdjustment | matrix_time_columns | 776 x 128 | 41,256 | Continent, Region, Country, Regasification plant, Life Cycle Category, Nameplate capacity, Year, Month | RegasAdjustment | OK |
| RemainingUnrestrictedAmount | Trade | TradeRestrictionInput | fixed_columns | 499 x 11 | 4 | Year, From Country, To Country | RemainingUnrestrictedAmount | OK |
| ShippingCost | Trade | ShippingCostInput | fixed_columns | 18931 x 48 | 7 | Year | ShippingCost | OK |
| SupplyDisruption | Supply | VolumeAdjustment | fixed_columns | 201 x 17 | 0 | - | - | WARN |
| Temperature | Demand | WeatherAdjustment | fixed_columns | 7997 x 33 | 150 | Year, Month, Country | Temperature | OK |
| User-Adjusted Gas Demand | Demand | DemandOutputOverwrite | fixed_columns | 507 x 30 | 12 | Country, Year, Month, Demand Sub-Sector | User-Adjusted Gas Demand | OK |
| VolumeCancelled | Trade | TradeRestrictionInput | fixed_columns | 499 x 11 | 4 | Year, From Country, To Country | VolumeCancelled | OK |

## Parameter별 실제 조회값 샘플 10건

- 아래 표는 parameter별 실제 조회 record의 앞 10건이다.
- 10건 미만인 parameter는 전체 record를 모두 표시한다.
- 전체 값은 `reports/basecase_load_values_full_20260630.csv`에 64,387건 전체로 저장했다.

### CDD

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:CDD, sheet=WeatherAdjustment`

### Coal Futures Price

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:Coal Futures Price, sheet=CoalGasAdjustment`

### Gas Futures Price

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:Gas Futures Price, sheet=CoalGasAdjustment`

### GDP

- 전체 record: 93건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Demand:GDPPopulationAdjustment:R12C6` | `{"Country": "United States", "Year": 2025}` | `GDP=0.019` | `BUSD / %change` |
| 2 | `Demand:GDPPopulationAdjustment:R13C6` | `{"Country": "United States", "Year": 2026}` | `GDP=0.019` | `BUSD / %change` |
| 3 | `Demand:GDPPopulationAdjustment:R14C6` | `{"Country": "United States", "Year": 2027}` | `GDP=0.02` | `BUSD / %change` |
| 4 | `Demand:GDPPopulationAdjustment:R15C6` | `{"Country": "United States", "Year": 2028}` | `GDP=0.021214702031537414` | `BUSD / %change` |
| 5 | `Demand:GDPPopulationAdjustment:R16C6` | `{"Country": "United States", "Year": 2029}` | `GDP=0.014919039684140989` | `BUSD / %change` |
| 6 | `Demand:GDPPopulationAdjustment:R17C6` | `{"Country": "United States", "Year": 2030}` | `GDP=0.014859486964253987` | `BUSD / %change` |
| 7 | `Demand:GDPPopulationAdjustment:R18C6` | `{"Country": "United States", "Year": 2031}` | `GDP=0.014859486964253987` | `BUSD / %change` |
| 8 | `Demand:GDPPopulationAdjustment:R19C6` | `{"Country": "China", "Year": 2024}` | `GDP=0.05` | `BUSD / %change` |
| 9 | `Demand:GDPPopulationAdjustment:R20C6` | `{"Country": "China", "Year": 2025}` | `GDP=0.048` | `BUSD / %change` |
| 10 | `Demand:GDPPopulationAdjustment:R21C6` | `{"Country": "China", "Year": 2026}` | `GDP=0.042` | `BUSD / %change` |

### HDD

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:HDD, sheet=WeatherAdjustment`

### HurricaneIntensity

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:HurricaneIntensity, sheet={USA}Hurricanes`

### LiqProdAdjustment

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:LiqProdAdjustment, sheet=LiqProdAdjustment`

### LiqUtilAdjustment

- 전체 record: 21,656건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Supply:LiqUtilAdjustment:R11C10` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 1, "Nameplate Capacity": 7.9, "Period": 73, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 2 | `Supply:LiqUtilAdjustment:R11C11` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 2, "Nameplate Capacity": 7.9, "Period": 74, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 3 | `Supply:LiqUtilAdjustment:R11C12` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 3, "Nameplate Capacity": 7.9, "Period": 75, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 4 | `Supply:LiqUtilAdjustment:R11C13` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 4, "Nameplate Capacity": 7.9, "Period": 76, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 5 | `Supply:LiqUtilAdjustment:R11C14` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 5, "Nameplate Capacity": 7.9, "Period": 77, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 6 | `Supply:LiqUtilAdjustment:R11C15` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 6, "Nameplate Capacity": 7.9, "Period": 78, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 7 | `Supply:LiqUtilAdjustment:R11C16` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 7, "Nameplate Capacity": 7.9, "Period": 79, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 8 | `Supply:LiqUtilAdjustment:R11C17` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 8, "Nameplate Capacity": 7.9, "Period": 80, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 9 | `Supply:LiqUtilAdjustment:R11C18` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 9, "Nameplate Capacity": 7.9, "Period": 81, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |
| 10 | `Supply:LiqUtilAdjustment:R11C19` | `{"Country": "Algeria", "LNG Plant": "Arzew GL1Z", "LNG Plant Train": "Arzew GL1Z T1-T6", "Life Cycle Category": "Operational", "Month": 10, "Nameplate Capacity": 7.9, "Period": 82, "Year": 2024}` | `LiqUtilAdjustment=0.24438941108046752` | `%` |

### PipelineAdjustment

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:PipelineAdjustment, sheet=PipelineAdjustment`

### PMI

- 전체 record: 48건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Demand:PMIAdjustment:R13C6` | `{"Country": "China", "Month": 1, "Year": 2025}` | `PMI=49.1` | `index` |
| 2 | `Demand:PMIAdjustment:R14C6` | `{"Country": "China", "Month": 2, "Year": 2025}` | `PMI=50.2` | `index` |
| 3 | `Demand:PMIAdjustment:R15C6` | `{"Country": "China", "Month": 3, "Year": 2025}` | `PMI=50.5` | `index` |
| 4 | `Demand:PMIAdjustment:R16C6` | `{"Country": "China", "Month": 4, "Year": 2025}` | `PMI=49` | `index` |
| 5 | `Demand:PMIAdjustment:R17C6` | `{"Country": "China", "Month": 5, "Year": 2025}` | `PMI=49.5` | `index` |
| 6 | `Demand:PMIAdjustment:R18C6` | `{"Country": "China", "Month": 6, "Year": 2025}` | `PMI=49.7` | `index` |
| 7 | `Demand:PMIAdjustment:R19C6` | `{"Country": "China", "Month": 7, "Year": 2025}` | `PMI=49.3` | `index` |
| 8 | `Demand:PMIAdjustment:R20C6` | `{"Country": "China", "Month": 8, "Year": 2025}` | `PMI=49.4` | `index` |
| 9 | `Demand:PMIAdjustment:R21C6` | `{"Country": "China", "Month": 9, "Year": 2025}` | `PMI=49.6` | `index` |
| 10 | `Demand:PMIAdjustment:R22C6` | `{"Country": "China", "Month": 10, "Year": 2025}` | `PMI=49.6` | `index` |

### PNG Contract Volume

- 전체 record: 1,100건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Trade:MidstreamContractInput:R5C4` | `{"From Country": "Algeria", "To Country": "Italy", "Year": 2023}` | `PNG Contract Volume=20.82308` | `BCM` |
| 2 | `Trade:MidstreamContractInput:R6C4` | `{"From Country": "Algeria", "To Country": "Morocco", "Year": 2023}` | `PNG Contract Volume=0` | `BCM` |
| 3 | `Trade:MidstreamContractInput:R7C4` | `{"From Country": "Algeria", "To Country": "Portugal", "Year": 2023}` | `PNG Contract Volume=2.153989` | `BCM` |
| 4 | `Trade:MidstreamContractInput:R8C4` | `{"From Country": "Algeria", "To Country": "Spain", "Year": 2023}` | `PNG Contract Volume=9.8` | `BCM` |
| 5 | `Trade:MidstreamContractInput:R9C4` | `{"From Country": "Algeria", "To Country": "Tunisia", "Year": 2023}` | `PNG Contract Volume=3.454368` | `BCM` |
| 6 | `Trade:MidstreamContractInput:R10C4` | `{"From Country": "Algeria", "To Country": "Italy", "Year": 2024}` | `PNG Contract Volume=22.5801` | `BCM` |
| 7 | `Trade:MidstreamContractInput:R11C4` | `{"From Country": "Algeria", "To Country": "Morocco", "Year": 2024}` | `PNG Contract Volume=0` | `BCM` |
| 8 | `Trade:MidstreamContractInput:R12C4` | `{"From Country": "Algeria", "To Country": "Portugal", "Year": 2024}` | `PNG Contract Volume=2.33574` | `BCM` |
| 9 | `Trade:MidstreamContractInput:R13C4` | `{"From Country": "Algeria", "To Country": "Spain", "Year": 2024}` | `PNG Contract Volume=9.8` | `BCM` |
| 10 | `Trade:MidstreamContractInput:R14C4` | `{"From Country": "Algeria", "To Country": "Tunisia", "Year": 2024}` | `PNG Contract Volume=3.454368` | `BCM` |

### PowerMix

- 전체 record: 57건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Demand:PowerMixAdjustment:R12C6` | `{"Country": "China", "Energy Source": "Gas", "Year": 2025}` | `PowerMix=0.036` | `%` |
| 2 | `Demand:PowerMixAdjustment:R13C6` | `{"Country": "China", "Energy Source": "Gas", "Year": 2026}` | `PowerMix=0.0346` | `%` |
| 3 | `Demand:PowerMixAdjustment:R14C6` | `{"Country": "China", "Energy Source": "Gas", "Year": 2027}` | `PowerMix=0.0365` | `%` |
| 4 | `Demand:PowerMixAdjustment:R15C6` | `{"Country": "China", "Energy Source": "Gas", "Year": 2028}` | `PowerMix=0.0374` | `%` |
| 5 | `Demand:PowerMixAdjustment:R16C6` | `{"Country": "China", "Energy Source": "Gas", "Year": 2029}` | `PowerMix=0.0372` | `%` |
| 6 | `Demand:PowerMixAdjustment:R17C6` | `{"Country": "China", "Energy Source": "Gas", "Year": 2030}` | `PowerMix=0.0374` | `%` |
| 7 | `Demand:PowerMixAdjustment:R18C6` | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2025}` | `PowerMix=0.3` | `%` |
| 8 | `Demand:PowerMixAdjustment:R19C6` | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2026}` | `PowerMix=0.323` | `%` |
| 9 | `Demand:PowerMixAdjustment:R20C6` | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2027}` | `PowerMix=0.318` | `%` |
| 10 | `Demand:PowerMixAdjustment:R21C6` | `{"Country": "Japan", "Energy Source": "Gas", "Year": 2028}` | `PowerMix=0.309` | `%` |

### RegasAdjustment

- 전체 record: 41,256건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Supply:RegasAdjustment:R11C8` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 1, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 2 | `Supply:RegasAdjustment:R11C9` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 2, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 3 | `Supply:RegasAdjustment:R11C10` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 3, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 4 | `Supply:RegasAdjustment:R11C11` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 4, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 5 | `Supply:RegasAdjustment:R11C12` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 5, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 6 | `Supply:RegasAdjustment:R11C13` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 6, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 7 | `Supply:RegasAdjustment:R11C14` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 7, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 8 | `Supply:RegasAdjustment:R11C15` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 8, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 9 | `Supply:RegasAdjustment:R11C16` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 9, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |
| 10 | `Supply:RegasAdjustment:R11C17` | `{"Continent": "Asia", "Country": "Taiwan (China)", "Life Cycle Category": "Operational", "Month": 10, "Nameplate capacity": 10.5, "Regasification plant": "Yung-An", "Region": "East Asia", "Year": 2023}` | `RegasAdjustment=0.875` | `Mt LNG` |

### RemainingUnrestrictedAmount

- 전체 record: 4건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Trade:TradeRestrictionInput:R6C10` | `{"From Country": "United States", "To Country": "China", "Year": 2025}` | `RemainingUnrestrictedAmount=0` | `MTPA / BCM` |
| 2 | `Trade:TradeRestrictionInput:R7C10` | `{"From Country": "United States", "To Country": "China", "Year": 2026}` | `RemainingUnrestrictedAmount=0` | `MTPA / BCM` |
| 3 | `Trade:TradeRestrictionInput:R8C10` | `{"From Country": "United States", "To Country": "China", "Year": 2027}` | `RemainingUnrestrictedAmount=0` | `MTPA / BCM` |
| 4 | `Trade:TradeRestrictionInput:R9C10` | `{"From Country": "United States", "To Country": "China", "Year": 2028}` | `RemainingUnrestrictedAmount=0` | `MTPA / BCM` |

### ShippingCost

- 전체 record: 7건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Trade:ShippingCostInput:R7C6` | `{"Year": 2024}` | `ShippingCost=81704` | `영향범위별` |
| 2 | `Trade:ShippingCostInput:R8C6` | `{"Year": 2025}` | `ShippingCost=23000` | `영향범위별` |
| 3 | `Trade:ShippingCostInput:R9C6` | `{"Year": 2026}` | `ShippingCost=55000` | `영향범위별` |
| 4 | `Trade:ShippingCostInput:R10C6` | `{"Year": 2027}` | `ShippingCost=55000` | `영향범위별` |
| 5 | `Trade:ShippingCostInput:R11C6` | `{"Year": 2028}` | `ShippingCost=66000` | `영향범위별` |
| 6 | `Trade:ShippingCostInput:R12C6` | `{"Year": 2029}` | `ShippingCost=48000` | `영향범위별` |
| 7 | `Trade:ShippingCostInput:R13C6` | `{"Year": 2030}` | `ShippingCost=56000` | `영향범위별` |

### SupplyDisruption

- 전체 record: 0건
- 조회된 record 없음
- 로딩 경고: `basecase record를 추출하지 못했습니다: candidate_key=diagnostic:SupplyDisruption, sheet=VolumeAdjustment`

### Temperature

- 전체 record: 150건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Demand:WeatherAdjustment:R12C15` | `{"Country": "China", "Month": 1, "Year": 2026}` | `Temperature=2.3` | `℃` |
| 2 | `Demand:WeatherAdjustment:R13C15` | `{"Country": "China", "Month": 2, "Year": 2026}` | `Temperature=5` | `℃` |
| 3 | `Demand:WeatherAdjustment:R14C15` | `{"Country": "China", "Month": 3, "Year": 2026}` | `Temperature=10.4` | `℃` |
| 4 | `Demand:WeatherAdjustment:R15C15` | `{"Country": "China", "Month": 1, "Year": 2027}` | `Temperature=2.3` | `℃` |
| 5 | `Demand:WeatherAdjustment:R16C15` | `{"Country": "China", "Month": 2, "Year": 2027}` | `Temperature=5` | `℃` |
| 6 | `Demand:WeatherAdjustment:R17C15` | `{"Country": "China", "Month": 3, "Year": 2027}` | `Temperature=10.4` | `℃` |
| 7 | `Demand:WeatherAdjustment:R18C15` | `{"Country": "China", "Month": 1, "Year": 2028}` | `Temperature=2.3` | `℃` |
| 8 | `Demand:WeatherAdjustment:R19C15` | `{"Country": "China", "Month": 2, "Year": 2028}` | `Temperature=5` | `℃` |
| 9 | `Demand:WeatherAdjustment:R20C15` | `{"Country": "China", "Month": 3, "Year": 2028}` | `Temperature=10.4` | `℃` |
| 10 | `Demand:WeatherAdjustment:R21C15` | `{"Country": "China", "Month": 1, "Year": 2029}` | `Temperature=2.3` | `℃` |

### User-Adjusted Gas Demand

- 전체 record: 12건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Demand:DemandOutputOverwrite:R8C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 1, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 2 | `Demand:DemandOutputOverwrite:R9C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 2, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 3 | `Demand:DemandOutputOverwrite:R10C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 3, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 4 | `Demand:DemandOutputOverwrite:R11C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 4, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 5 | `Demand:DemandOutputOverwrite:R12C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 5, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 6 | `Demand:DemandOutputOverwrite:R13C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 6, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 7 | `Demand:DemandOutputOverwrite:R14C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 7, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 8 | `Demand:DemandOutputOverwrite:R15C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 8, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 9 | `Demand:DemandOutputOverwrite:R16C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 9, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |
| 10 | `Demand:DemandOutputOverwrite:R17C8` | `{"Country": "China", "Demand Sub-Sector": "Losses", "Month": 10, "Year": 2026}` | `User-Adjusted Gas Demand=0.5` | `BCM / Mt LNG` |

### VolumeCancelled

- 전체 record: 4건

| # | Reference | Axes | Value | Unit |
|---:|---|---|---:|---|
| 1 | `Trade:TradeRestrictionInput:R6C6` | `{"From Country": "United States", "To Country": "China", "Year": 2025}` | `VolumeCancelled=0` | `MTPA / BCM` |
| 2 | `Trade:TradeRestrictionInput:R7C6` | `{"From Country": "United States", "To Country": "China", "Year": 2026}` | `VolumeCancelled=0` | `MTPA / BCM` |
| 3 | `Trade:TradeRestrictionInput:R8C6` | `{"From Country": "United States", "To Country": "China", "Year": 2027}` | `VolumeCancelled=0` | `MTPA / BCM` |
| 4 | `Trade:TradeRestrictionInput:R9C6` | `{"From Country": "United States", "To Country": "China", "Year": 2028}` | `VolumeCancelled=0` | `MTPA / BCM` |

## 해석 포인트

- `Records=0`은 mapping definition은 있으나 현재 Basecase sheet/profile 설정과 row filter 조건으로 값 record가 추출되지 않았다는 뜻이다.
- `matrix_time_columns` parameter는 행의 식별 축과 월별/기간별 컬럼 축을 조합하므로 record 수가 크다. `RegasAdjustment`, `LiqUtilAdjustment`가 대부분의 record를 차지한다.
- `fixed_columns` parameter는 매핑 XLSX의 `basecase_column_roles`에서 canonical parameter와 일치하는 컬럼을 값 컬럼으로 사용하고, 나머지 컬럼을 axes로 보존한다.
- `reference_id`는 `Model:Sheet:R{row}C{col}` 형식이며, LLM 제안 결과가 `source_reference`로 되돌려주는 Basecase 근거 ID다.
- 실제 API flow에서는 scenario event의 L2 event type과 text matching을 통과한 parameter 후보만 이 Basecase 값 목록을 사용한다.

## 검증 메모

- Basecase load 자체는 로컬 코드 import 후 mapping/Basecase 리소스를 직접 읽어 재현했다.
- 테스트 실행은 환경 의존성 부족으로 완료하지 못했다. `python -m pytest tests/test_model_parameter_agent_contract.py -q`는 `pytest` 미설치, `poetry run python -m unittest tests.test_model_parameter_agent_contract`는 `langchain_core` 미설치로 중단됐다.
- Excel 로딩 중 `openpyxl`의 Data Validation extension 경고가 표시됐지만 값 로딩은 완료됐다.
