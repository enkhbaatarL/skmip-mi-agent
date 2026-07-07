# MI 수급모델 입력 테이블 범위 맵

작성일: 2026-06-30

이 문서는 시나리오 제안값을 실제 입력 엑셀의 어느 위치에 반영해야 하는지 확인하기 위해, 엔진 코드가 분리해서 읽는 테이블 단위를 모델별로 정리한 것이다.

기준 파일:

- Demand: `test/testset_20260611/복호화_(Base) Demand Model_Input.xlsm`
- Supply: `test/testset_20260611/복호화_(Base) Supply Model_Input.xlsm`
- Trade: `test/testset_20260611/복호화_(Base) Trade Model_Input.xlsm`

## 공통 해석

- `t1`, `t2` 등은 엑셀의 공식 Table 객체명이 아니라 코드의 `TableSpec` 또는 `SheetSpec` 선언 순서에 따른 분리 테이블이다.
- `헤더 범위`는 컬럼명을 만드는 행이다. 값 입력 대상은 보통 `데이터 입력 범위`이다.
- `테스트셋 실제 데이터 범위`는 2026-06-11 테스트셋 파일에서 현재 엔진이 읽는 마지막 행까지 계산한 범위이다.
- 빈 테이블은 예를 들어 `B12:F11`처럼 데이터 행 수가 0으로 표시된다. 이 경우 신규 입력은 시작 행인 `B12:F12`부터 넣으면 된다.
- Supply/Trade는 `anchor_col` 기준으로 마지막 행을 찾는다. 새 행을 추가할 때는 반드시 anchor 컬럼에도 값이 있어야 엔진이 읽는다.

## Demand

소스: `engine/demand/01_Demand_Model_Import_table_input_v0.3.py`

Demand는 `TableSpec`으로 시트별 테이블을 선언한다. `single` 모드는 단일 헤더 행을 사용하고, `multi` 모드는 복수 헤더 행을 합쳐 컬럼명을 만든다. 모든 테이블은 지정된 시작 행부터 아래 전체를 읽은 뒤, 첫 2개 컬럼이 모두 빈 행을 제거한다. 따라서 신규 값을 넣을 때는 각 테이블의 첫 2개 key 컬럼을 비워두면 안 된다.

| 시트 | 테이블 | 출력명 | 헤더 범위 | 데이터 입력 범위 | 현재 행 수 | 주요 컬럼/의미 |
|---|---:|---|---|---|---:|---|
| GDPPopulationAdjustment | t1 | `Demand_Model_Input_GDPPopulationAdjustment_value_based_t1` | `B6:F6` | `B12:F104` | 93 | Year, Country, GDP (BUSD), % change (+/-) |
| GDPPopulationAdjustment | t2 | `Demand_Model_Input_GDPPopulationAdjustment_value_based_t2` | `J6:M6` | `J12:M11` | 0 | Year, Country, Base case Population, Population (Thousands) |
| ElectrificationRateAdjustment | t1 | `Demand_Model_Input_ElectrificationRateAdjustment_value_based_t1` | `B6:F6` | `B12:F11` | 0 | Year, Country, Drive Train, Base case % New Car Sales, % New Car Sales |
| PowerMixAdjustment | t1 | `Demand_Model_Input_PowerMixAdjustment_value_based_t1` | `B6:F6` | `B12:F68` | 57 | Year, Country, Energy Source, Base case % of Power Mix, % Power Mix |
| CoalGasAdjustment | t1 | `Demand_Model_Input_CoalGasAdjustment_value_based_t1` | `B6:E6` | `B12:E11` | 0 | Month-Year, Region, Base Case Coal Futures (USD/t), Coal Futures Price (USD/t) |
| CoalGasAdjustment | t2 | `Demand_Model_Input_CoalGasAdjustment_value_based_t2` | `H6:K6` | `H12:K11` | 0 | Month-Year, Region, Base Case Gas Futures (USD/mmbtu), Gas Futures Price (USD/mmbtu) |
| WeatherAdjustment | t1 | `Demand_Model_Input_WeatherAdjustment_value_based_t1` | `B6:G6` | `B12:G11` | 0 | Year, Month, Country, HDD/CDD, Base Case HDD/CDD |
| WeatherAdjustment | t2 | `Demand_Model_Input_WeatherAdjustment_value_based_t2` | `K6:O6` | `K12:O161` | 150 | Year, Month, Country, Base Case Temperature, Temperature (C) |
| WeatherAdjustment | t3 | `Demand_Model_Input_WeatherAdjustment_value_based_t3` | `T6:X6` | `T12:X11` | 0 | Year, Month, Region, HDD/CDD, HDD/CDD |
| WeatherAdjustment | t4 | `Demand_Model_Input_WeatherAdjustment_value_based_t4` | `AB6:AE6` | `AB12:AE11` | 0 | Year, Month, Region, Absolute Temperature Change (C) |
| PMIAdjustment | t1 | `Demand_Model_Input_PMIAdjustment_value_based_t1` | `B6:F6` | `B12:F60` | 48 | Year, Month, Country, Base Case PMI, PMI |
| PMIAdjustment | t2 | `Demand_Model_Input_PMIAdjustment_value_based_t2` | `J6:L6` | `J12:L11` | 0 | Country, Base Case Reference Country, Reference Country |
| HydrogenAdjustment | t1 | `Demand_Model_Input_HydrogenAdjustment_value_based_t1` | `B6:E6` | `B12:E11` | 0 | Year, Country, Base case production (ktonnes), Hydrogen Production (ktonnes) |
| LNGBunkeringAdjustment | t1 | `Demand_Model_Input_LNGBunkeringAdjustment_value_based_t1` | `B6:E6` | `B12:E11` | 0 | Year, Vessel Type, Base case no., No. of vessels |
| LNGBunkeringAdjustment | t2 | `Demand_Model_Input_LNGBunkeringAdjustment_value_based_t2` | `H6:K6` | `H12:K11` | 0 | Year, Vessel Type, Base case rate, Fuel consumption (MCM/yr) |
| DemandOutputOverwrite | t1 | `Demand_Model_Input_DemandOutputOverwrite_value_based_t1` | `D6:J7` | `D8:J19` | 12 | Demand Model Manual Overwrite Sector Input |
| DemandOutputOverwrite | t2 | `Demand_Model_Input_DemandOutputOverwrite_value_based_t2` | `M6:R7` | `M8:R7` | 0 | Demand Model Manual Overwrite Monthly Input |

Demand 입력 시 주의점:

- `GDPPopulationAdjustment`는 GDP 조정과 Population 조정이 같은 시트 안에서 좌우로 분리된다. GDP 값은 t1 `B:F`, Population 값은 t2 `J:M`에 넣어야 한다.
- `WeatherAdjustment`는 네 개 입력 블록으로 분리된다. 현재 로직의 기본 모드는 Temperature 기반이므로 일반 온도 조정은 t2 `K:O`가 우선 후보이고, HDD/CDD 직접 입력은 t1 또는 t3 계열을 확인해야 한다.
- `DemandOutputOverwrite`는 2행 헤더이다. t1은 섹터 단위 수동 덮어쓰기, t2는 월별 수동 덮어쓰기 블록으로 분리된다.
- `PMIAdjustment` t1과 `DemandOutputOverwrite` t1에는 numeric country 행 제거 규칙이 있어, Country 컬럼에 숫자만 들어간 행은 후처리에서 삭제될 수 있다.

## Supply

소스: `engine/supply/input_excel.py`

Supply는 `SheetSpec`으로 테이블을 선언한다. `start_cell`의 행이 헤더이고, 데이터는 다음 행부터 시작한다. 마지막 행은 `anchor_col`의 마지막 유효값으로 결정한다.

| 구분 | 시트 | 출력명 | 테스트셋 실제 데이터 범위 | 헤더 범위 | 데이터 입력 범위 | 현재 행 수 | 종료 기준 |
|---|---|---|---|---|---|---:|---|
| supply | VolumeAdjustment | `VolumeAdjustment` | `H7:P7` | `H7:P7` | `H8:P7` | 0 | anchor `I` |
| supply | {USA}Hurricanes | `USA_Hurricanes` | `B7:E7` | `B7:E7` | `B8:E7` | 0 | anchor `B` |
| supply | LiqUtilAdjustment | `LiqUtilAdjustment` | `D6:DA358` | `D6:DA6` | `D7:DA358` | 352 | anchor `D` |
| supply | LiqProdAdjustment | `LiqProdAdjustment` | `D6:DA358` | `D6:DA6` | `D7:DA358` | 352 | anchor `D` |
| supply | RegasAdjustment | `RegasAdjustment` | `B10:DV454` | `B10:DV10` | `B11:DV454` | 444 | anchor `G` |
| supply | PipelineAdjustment | `PipelineAdjustment` | `A7:I72` | `A7:I7` | `A8:I72` | 65 | anchor `H` |

Supply BC용 스펙도 코드에는 있지만, 현재 테스트셋 Supply workbook에는 해당 BC 시트들이 없다.

| 구분 | 시트 | 출력명 | 스펙 범위 | 종료 기준 |
|---|---|---|---|---|
| supply_bc | BCProduction | `BCProduction` | `A7:L...` | anchor `K` |
| supply_bc | BCHurricanes | `BCHurricanes_Impacct_upstreamAssets` | `B7:G...` | anchor `G`, `Impact on liquefaction plant:` 직전에서 stop |
| supply_bc | BCHurricanes | `BCHurricanes_Imapct_liquefactionPlant` | `B15:G...` | anchor `G` |
| supply_bc | BCLiquefaction | `BCLiquefaction` | `B7:Q...` | anchor `O` |
| supply_bc | BCRegasification | `BCRegasification` | `A7:P...` | anchor `P` |
| supply_bc | BCPipeline | `BCPipeline` | `B7:F...` | anchor `F` |
| supply_bc | BCHurricanes | `BCHurricanes_GoM` | `I15:K...` | anchor `I` |
| supply_bc | SeasonalityLogic | `SeasonalityLogic` | `B7:G...` | anchor `G` |
| supply_bc | Pre-Seasonality Adj | `Pre_Seasonality_Adj` | `A7:R...` | anchor `A` |

Supply 입력 시 주의점:

- `VolumeAdjustment`는 현재 테스트셋에 데이터 행이 없으므로 신규 값은 `H8:P8`부터 넣으면 된다. 단, anchor 컬럼 `I`가 비면 읽히지 않는다.
- `LiqUtilAdjustment`, `LiqProdAdjustment`, `RegasAdjustment`, `PipelineAdjustment`는 이미 긴 기본 블록이 존재한다. 기존 key 행을 찾아 값을 덮어쓸지, 마지막 아래에 신규 행을 추가할지 정책을 먼저 정해야 한다.
- `BCHurricanes_Impacct_upstreamAssets`는 output 이름에 오타(`Impacct`)가 있지만 코드/파일명 기준으로는 이 이름이 정식 출력명이다.

## Trade

소스: `engine/trade/input_excel.py`

Trade도 `TableSpec`으로 테이블을 선언한다. `start_cell`부터 `header_rows`개 행이 헤더이고, 데이터는 그 다음 행부터 시작한다. 마지막 행은 `anchor_col`에서 찾으며, `allow_gaps=True`인 테이블은 중간 빈 행을 허용하고 최대 200개 연속 빈 행에서 멈춘다.

| 구분 | 시트 | 출력명 | 테스트셋 실제 데이터 범위 | 헤더 범위 | 데이터 입력 범위 | 현재 행 수 | 종료 기준 |
|---|---|---|---|---|---|---:|---|
| trade_input | MidstreamContractInput | `MidstreamContractInput_ForecastedPNGContractVolume_Imports` | `A2:M1104` | `A2:M4` | `A5:M1104` | 1100 | anchor `A`, headers 3 |
| trade_input | MidstreamContractInput | `MidstreamContractInput_LNGContractVolume_Imports` | `Q2:AJ1424` | `Q2:AJ4` | `Q5:AJ1424` | 1420 | anchor `Q`, headers 3 |
| trade_input | TradeRestrictionInput | `TradeRestrictionInput_LNGTradeRestrictions` | `B4:K44` | `B4:K5` | `B6:K44` | 39 | anchor `B`, headers 2, gaps allowed |
| trade_input | ShippingCostInput | `ShippingCostInput_CharterCost_174000cbm_TwoStroke` | `A4:G13` | `A4:G5` | `A6:G13` | 8 | anchor `B`, headers 2 |
| trade_input | ShippingCostInput | `ShippingCostInput_route_cost_O_P_Z` | `O4:Z18931` | `O4:Z4` | `O5:Z18931` | 18927 | anchor `Z`, headers 1 |
| trade_input | TradeRestrictionInput | `TradeRestrictionInput_route_helper_G5_K` | `G5:K44` | `G5:K5` | `G6:K44` | 39 | anchor `G`, headers 1, gaps allowed |

현재 테스트셋 Trade workbook에는 `UpstreamAdjLogicInput` 시트가 없어 아래 두 스펙은 workbook에서 직접 추출되지 않는다.

| 구분 | 시트 | 출력명 | 스펙 범위 | 종료 기준 |
|---|---|---|---|---|
| trade_input | UpstreamAdjLogicInput | `UpstreamAdjLogicInput_T3_T40` | `T3:T...` | anchor `T`, headers 1 |
| trade_input | UpstreamAdjLogicInput | `UpstreamAdjLogicInput_Q3_R674` | `Q3:R...` | anchor `R`, headers 1 |

Trade BC/상수 테이블 중 현재 테스트셋 workbook에서 실제 존재하는 것은 `ShippingCostInput` 내부 하단 블록이다.

| 구분 | 시트 | 출력명 | 테스트셋 실제 데이터 범위 | 헤더 범위 | 데이터 입력 범위 | 현재 행 수 | 종료 기준 |
|---|---|---|---|---|---|---:|---|
| trade_bc | ShippingCostInput | `ShippingCostInput_FuelCost_IFO380` | `A15:G24` | `A15:G16` | `A17:G24` | 8 | anchor `B`, headers 2 |
| trade_bc | ShippingCostInput | `ShippingCostInput_SuezCanal` | `A26:G35` | `A26:G27` | `A28:G35` | 8 | anchor `B`, headers 2 |
| trade_bc | ShippingCostInput | `ShippingCostInput_PanamaCanal` | `A37:G46` | `A37:G38` | `A39:G46` | 8 | anchor `B`, headers 2 |
| trade_bc | ShippingCostInput | `ShippingCostInput_SuezCanalDisruption` | `A48:D57` | `A48:D49` | `A50:D57` | 8 | anchor `B`, headers 2 |
| trade_bc | ShippingCostInput | `ShippingCostInput_PanamaCanalDisruption` | `A59:D68` | `A59:D60` | `A61:D68` | 8 | anchor `B`, headers 2 |

Trade BC용으로 코드에 선언되어 있으나 현재 테스트셋 workbook에 없는 시트/테이블은 다음과 같다.

| 구분 | 시트 | 출력명 | 스펙 범위 | 종료 기준 |
|---|---|---|---|---|
| trade_bc | MidstreamCapacityInput | `MidstreamCapacityInput_PNGInfrastructure_BCM` | `B1:S...` | anchor `B`, headers 3 |
| trade_bc | MidstreamCapacityInput | `MidstreamCapacityInput_ShareOfImports_ThroughEachPipeline` | `DX1:EC...` | anchor `DX`, headers 3 |
| trade_bc | MidstreamCapacityInput | `MidstreamCapacityInput_NordStreamGas_ByImporterCountry` | `FB1:FD...` | anchor `FB`, headers 3 |
| trade_bc | DemandAdjLogicInput | `DemandAdjLogicInput_SelectionOfPremiumMarkets` | `A1:A...` | anchor `A`, headers 2 |
| trade_bc | DemandAdjLogicInput | `DemandAdjLogicInput_DemandAdjustment_1` | `C1:F...` | anchor `C`, headers 1 |
| trade_bc | DemandAdjLogicInput | `DemandAdjLogicInput_DemandAdjustment_2` | `H1:M...` | anchor `H`, headers 2 |
| trade_bc | CostInput | `CostInput_RegasTariff_USD_per_MMbtu` | `A1:F...` | anchor `A`, headers 2 |
| trade_bc | CostInput | `CostInput_LiquefactionCost_USD_per_MMbtu` | `H1:M...` | anchor `H`, headers 2 |
| trade_bc | CostInput | `CostInput_LNGUpstreamCost_USD_per_MMbtu` | `O1:T...` | anchor `O`, headers 2 |
| trade_bc | CostInput | `CostInput_NonLNGUpstreamCost_USD_per_MMbtu` | `V1:AA...` | anchor `V`, headers 2 |
| trade_bc | CostInput | `CostInput_PipelineCost_USD_per_MMbtu` | `AC1:AJ...` | anchor `AC`, headers 2 |
| trade_bc | CostInput | `CostInput_LNGProjects_SRMC_USD_per_kcf` | `AK1:AR...` | anchor `AK`, headers 2 |

Trade 입력 시 주의점:

- Demand/Supply upstream output은 Trade workbook에서 더 이상 직접 파싱하지 않고, upstream 결과 CSV를 기반으로 재구성한다.
- `ShippingCostInput_route_cost_O_P_Z`는 매우 큰 route helper/cost 테이블이다. 시나리오 값 입력 대상인지, 계산용 helper 테이블인지 구분해야 한다.
- `UpstreamAdjLogicInput`, `MidstreamCapacityInput`, `DemandAdjLogicInput`, `CostInput` 계열은 테스트셋 workbook에 없으므로, 값 반영 대상으로 삼으려면 실제 운영 workbook 또는 정적 LUT/BC 입력 경로 중 어느 파일을 수정해야 하는지 먼저 확정해야 한다.

## Output

소스: `engine/output/src/importing/specs.py`

Output 모델은 입력 제안값을 쓰는 workbook이라기보다 Demand/Supply/Trade 결과를 다시 테이블화하는 downstream import에 가깝다. 그래도 Output importer 역시 시트별 테이블 범위를 고정 스펙으로 갖고 있다.

| 시트 | 테이블 | 헤더 행 | 컬럼 범위 | 값 행 | 비고 |
|---|---:|---|---|---|---|
| Demand | t1 | `1:2` | `A:N` | `3:끝` | Demand 결과 |
| Supply | t1 | `1:2` | `A:N` | `3:끝` | Supply 결과 |
| Disruption | t1 | `1:2` | `B:F` | `3:끝` | Pipeline capacity |
| Disruption | t2 | `1:2` | `J:N` | `3:끝` | Country capacity |
| Disruption | t3 | `1:2` | `W:AA` | `3:끝` | Pipeline share |
| MonthlyPriceHist | t1 | `2:3` | `B:K` | `4:끝` | 월별 가격 이력 |
| MonthlyPriceHist | t2 | `2:3` | `M:S` | `4:끝` | 월별 가격 이력 |
| MonthlyPriceHist | t3 | `83:85` | `V:Z` | `86:88` | 고정 소형 블록 |
| MonthlyPriceInput | t1 | `2` | `L:T` | `3:끝` | 월별 가격 입력 |
| PremiumCalc | t1 | `8:9` | `B:M` | `10:18` | Premium 계산 |
| PremiumCalc | t2 | `24` | `B:D` | `25:33` | Premium 계산 |
| PremiumCalc | t3 | `37:38` | `B:C` | `39:47` | uncontracted volumes base case |
| PremiumCalc | t4 | `51:52` | `B:C` | `53:61` | uncontracted volumes base case |
| PriceLUT | t1 | `3` | `B:C` | `4:빈 행 전` | blank row에서 stop |
| USCostofSupply | t1 | `7` | `B:L` | `8:816` | key col dropna |
| AnnualPriceInput | t1 | `2:3` | `B:D` | `4:끝` | user adjusted JKM |
| AnnualPriceInput | t2 | `2:3` | `F:H` | `4:끝` | TTF user adjusted |
| AnnualPriceInput | t3 | `2:3` | `J:O` | `4:끝` | 연간 가격 입력 |
| AnnualPriceInput | t4 | `2:3` | `Q:S` | `4:끝` | 연간 가격 입력 |
| AnnualPriceInput | t5 | `2:3` | `U:X` | `4:끝` | 연간 가격 입력 |
| AnnualPriceInput | t6 | `2:3` | `AG:AI` | `4:끝` | base case JKM |
| AnnualPriceInput | t7 | `2:3` | `AK:AM` | `4:끝` | TTF user adjusted |
| AnnualPriceInput | t8 | `2:3` | `AO:AT` | `4:끝` | 연간 가격 입력 |
| AnnualPriceInput | t9 | `2:3` | `AV:AW` | `4:끝` | base case USA supply |
| BCPrices | t1 | `6:8` | `B:E` | `8:끝` | HH/East Asia Spot/TTF |
| Trade (Annual) | t1 | `2:3` | `B:L` | `4:끝` | annual trade 결과 |

## 제안값 반영 관점의 우선 수정 대상

현재 매핑 엑셀의 제안값을 실제 workbook에 쓰려면 아래 순서로 대상을 정하는 것이 안전하다.

1. 매핑 파라미터가 Demand/Supply/Trade 중 어느 모델 입력인지 결정한다.
2. 위 표에서 해당 시트와 테이블을 찾는다.
3. 기존 key가 있으면 같은 key 행의 값 컬럼을 업데이트한다.
4. 기존 key가 없으면 데이터 시작 행 또는 현재 마지막 행 아래에 신규 행을 추가한다.
5. Demand는 첫 2개 컬럼, Supply/Trade는 anchor 컬럼을 반드시 채운다.
6. BC/정적 테이블이 테스트셋 workbook에 없는 경우, 운영 workbook 또는 LUT/cache 입력 경로를 먼저 확정한다.
