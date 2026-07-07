# Parameter Excel Mapping 정리

> 원본 파일: `resources/260625_시나리오가정_MI수급모델_input_매핑_vfShare.xlsx`
> 대상 시트: `Parameter Excel Mapping`
> 기준: 2026-06-30 현재 로컬 리소스 기준

## 개요

- 전체 parameter: 19개
- enabled parameter: 19개
- model 영역: `Demand`, `Supply`, `Trade`
- Basecase 읽기 방식:
  - `fixed_columns`: 지정 컬럼에서 축과 값 컬럼을 읽음
  - `matrix_time_columns`: 행 축과 Year/Month/Period 헤더를 조합해 시간축 matrix 값을 읽음
- 공통 stop rule: `stop_when_all_key_columns_empty`

## 통합 매핑 테이블

| # | Parameter | Model | Sheet | Unit | Semantic axes | Read mode | Header/Data row | Column roles | Row filter | Time header rows | Value columns/name |
|---:|---|---|---|---|---|---|---|---|---|---|---|
| 1 | CDD | Demand | WeatherAdjustment | 냉방도일 | 평년 대비 기온편차 변환 — 국가·연·월 | fixed_columns | 6 / 7 | `B:Year,C:Month,D:Country,E:DegreeDayType,G:CDD` | `E=CDD` | - | - |
| 2 | Coal Futures Price | Demand | CoalGasAdjustment | USD/t | 석탄 선물가격 strip — 지역·월 (Asia=Newcastle, EU=ARA) | fixed_columns | 6 / 7 | `B:Month-Year,C:Region,E:Coal Futures Price` | - | - | - |
| 3 | Gas Futures Price | Demand | CoalGasAdjustment | USD/mmbtu | 가스 선물가격 strip — 지역·월 (Asia=JKM, EU=TTF) | fixed_columns | 6 / 7 | `H:Month-Year,I:Region,K:Gas Futures Price` | - | - | - |
| 4 | GDP | Demand | GDPPopulationAdjustment | BUSD / %change | Real GDP(base 2019) — 국가·연 | fixed_columns | 6 / 7 | `B:Year,C:Country,F:GDP` | - | - | - |
| 5 | HDD | Demand | WeatherAdjustment | 난방도일 | 평년 대비 기온편차 변환 — 국가·연·월 | fixed_columns | 6 / 7 | `B:Year,C:Month,D:Country,E:DegreeDayType,G:HDD` | `E=HDD` | - | - |
| 6 | HurricaneIntensity | Supply | {USA}Hurricanes | [1,2,3,4] | 美 액화시설 허리케인 차질 — 연·월 | fixed_columns | 7 / 8 | `B:Year,C:Month,D:HurricaneIntensity` | - | - | - |
| 7 | LiqProdAdjustment | Supply | LiqProdAdjustment | Mt LNG | 액화시설 생산량 override — Country>Plant>Train·연·월 | matrix_time_columns | 10 / 11 | `B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity` | - | Year 7, Month 8, Period 9 | `G:DA` / LiqProdAdjustment |
| 8 | LiqUtilAdjustment | Supply | LiqUtilAdjustment | % | 액화시설 가동률 override — Country>Plant>Train·연·월 | matrix_time_columns | 10 / 11 | `B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity` | - | Year 7, Month 8, Period 9 | `G:DA` / LiqUtilAdjustment |
| 9 | PipelineAdjustment | Supply | PipelineAdjustment | Bcm/y | PNG 송출 capa override — Pipeline·From·To·연·월 | fixed_columns | 7 / 8 | `B:Year,C:Month,D:Pipeline name,H:PipelineAdjustment` | - | - | - |
| 10 | PMI | Demand | PMIAdjustment | index | 제조업 PMI — 국가·연·월 (산업 수요) | fixed_columns | 6 / 7 | `B:Year,C:Month,D:Country,F:PMI` | - | - | - |
| 11 | PNG Contract Volume | Trade | MidstreamContractInput | BCM | PNG 계약 물량(Nord Stream 재가동·Pipeline Disruption) — From·To·연 | fixed_columns | 4 / 5 | `A:Year,B:From Country,C:To Country,D:PNG Contract Volume` | - | - | - |
| 12 | PowerMix | Demand | PowerMixAdjustment | % | 발전 에너지원 비중 — 국가·에너지원(Gas/Coal/Nuclear/Solar/Wind/...)·연 | fixed_columns | 6 / 12 | `B:Year,C:Country,D:Energy Source,F:PowerMix` | - | - | - |
| 13 | RegasAdjustment | Supply | RegasAdjustment | Mt LNG | 재기화(수입) 설비 capa override — Continent>Region>Country>Plant·연·월 | matrix_time_columns | 10 / 11 | `B:Continent,C:Region,D:Country,E:Regasification plant,F:Life Cycle Category,G:Nameplate capacity` | - | Year 9, Month 10 | `H:DK` / RegasAdjustment |
| 14 | RemainingUnrestrictedAmount | Trade | TradeRestrictionInput | MTPA / BCM | 계약 취소·통과 제약 — From·To·연 | fixed_columns | 5 / 6 | `B:Year,C:From Country,D:To Country,J:RemainingUnrestrictedAmount` | - | - | - |
| 15 | ShippingCost | Trade | ShippingCostInput | 영향범위별 | Charter·Fuel·Suez/Panama Crossing 비용·Disruption 여부 — impact_scope·연 | fixed_columns | 5 / 6 | `B:Year,F:ShippingCost` | - | - | - |
| 16 | SupplyDisruption | Supply | VolumeAdjustment | Bcm / % | Upstream 생산 차질(+/-) — Province·연 (+ 월별 VolumeManualOverwrite) | fixed_columns | 7 / 8 | `B:Year,C:Province Country,E:SupplyDisruption` | - | - | - |
| 17 | Temperature | Demand | WeatherAdjustment | ℃ | 기온 직접 — 국가·연·월 | fixed_columns | 6 / 7 | `K:Year,L:Month,M:Country,O:Temperature` | - | - | - |
| 18 | User-Adjusted Gas Demand | Demand | DemandOutputOverwrite | BCM / Mt LNG | 수요 출력 직접 덮어쓰기 — 국가·연·월·Sub-Sector | fixed_columns | 7 / 8 | `D:Country,E:Year,F:Month,G:Demand Sub-Sector,H:User-Adjusted Gas Demand` | - | - | - |
| 19 | VolumeCancelled | Trade | TradeRestrictionInput | MTPA / BCM | 계약 취소·통과 제약 — From·To·연 | fixed_columns | 5 / 6 | `B:Year,C:From Country,D:To Country,F:VolumeCancelled` | - | - | - |

## 해석 포인트

- `canonical_parameter_name`은 agent 내부 후보 매칭과 LLM 응답 검증의 기준 parameter 이름이다.
- `model_file`과 `model_sheet`는 최종 추천 응답의 모델 타깃으로 사용된다.
- `basecase_column_roles`는 각 Excel 컬럼이 어떤 축 또는 값인지 정의한다.
- `fixed_columns`는 `basecase_column_roles`에서 canonical parameter와 일치하는 컬럼을 값 컬럼으로 사용한다.
- `matrix_time_columns`는 `basecase_value_start_col`부터 `basecase_value_end_col`까지를 시간축 값 영역으로 읽고, `basecase_year_row`, `basecase_month_row`, `basecase_period_row`를 시간 좌표로 사용한다.
- `row_filter`가 있는 `CDD`, `HDD`는 `DegreeDayType` 컬럼이 각각 `CDD`, `HDD`인 행만 읽는다.
