# Model Parameter Base Case Mapping

> 현재 runtime 계약은 Scenario API `v4`, Impact Lever catalog `v4.1`, Proposal Flow `v4.1.8`,
> proposal capability `extend17-v9`, workbook contract `new-bc-v9`다. v0050은 v4.1 Lever의
> Canal binding과 기존 v4.1 Scenario checksum pin을 함께 갱신하며, 과거 v4/v4.0 catalog·pin은 보존한다.

## 기준과 범위

현재 기계 판정 정본은 다음과 같다.

- Parameter master: `scripts/model_parameter/model-parameter-canonical-v4.1-0050.json`
- Impact Lever: `scripts/model_parameter/model-impact-lever-canonical-v4.1-0050.json`
- v1/v3 shared mapping: `scripts/model_parameter/model-parameter-canonical-v1.json`의
  `dimension_mappings`
- workbook 구조: `resources/contracts/model-parameter-workbook-contract-v9.json`
- proposal capability: `resources/contracts/model-parameter-proposal-capabilities-v5.json`
- 화면 논리 테이블: `resources/contracts/model-parameter-logical-table-catalog-v4.json`

현재 계약의 수량은 다음과 같다.

- master 26행, 활성 18개, 비활성 8개
- 현행 v4.1 proposal Parameter 17개: LUT-backed 10개 + Basecase-only 7개
- v4.0 catalog 호환 전용 활성 Parameter 1개: `CanalToll`
- v4.1 Impact Lever 21행, binding occurrence 56개, conditional occurrence 41개,
  executable 고유 Parameter 17개
- v1/v3 shared legacy dimension mapping 129행
  (direct 35, routing 6, indirect 55, na 33)
- v1/v3 proposal allow-list 5개: `GDP`, `PMI`, `PowerMix`, `Temperature`,
  `LiqUtilAdjustment`

mgmt v0050은 master ID 1~24, 과거 `v4`·`v4.0` Lever catalog, legacy mapping을 보존한다. ID 25·26과 화면 catalog v4를
추가하고, 기존 v4.1 Lever ID 56~76 중 운하 관련 3행만 제자리 갱신한다. 기존 v4.1 Scenario Group의
catalog version은 유지하면서 checksum pin을 새 v4.1 checksum으로 같은 transaction에서 이관한다.

## v4.1 `new-bc-v9` read-only proposal overlay

이 overlay는 정확히 `api_version=v4`,
`generation_strategy=multi_event_model_lever_dimensions`인 proposal에 적용한다. `read_only`는
workbook/reference를 읽기 전용으로 사용한다는 의미이며 proposal persistence를 비활성화한다는 뜻이
아니다.

정상 운영 요청은 활성 MI Base에 연결된 Demand·Supply·Trade workbook을 Object Storage에서 받아
v9 구조 계약과 실제 다운로드 hash로 검증한다. packaged baseline은
`resources/basecase_v4/new-bc-v2/`에 유지되며 startup 검증·검증된 cache fallback에만 사용한다.

v9는 v8의 17개 read 계약을 유지하면서 Trade `ShippingCostInput`의 운하 블록을 다음처럼 분리한다.

| Parameter | model target | exact source | records |
|---|---|---|---:|
| `Suez Canal Cost` | Trade / `ShippingCostInput` / `table4` | 행 39~46 중 Suez, Year, C열 `$ / crossing` | 5 |
| `Panama Canal Cost` | Trade / `ShippingCostInput` / `table5` | 행 50~57 중 Panama, Year, C열 `$ / crossing` | 5 |

ID 24 `CanalToll`은 두 블록을 함께 읽는 v4.0 catalog 호환 계약에만 남는다. v4.1 후보 선정·slot
설정·값 제안에서는 ID 25와 26만 사용하며, Suez 근거로 Panama slot을 만들거나 그 반대 방향으로
복구하지 않는다.

PowerMix는 파라미터를 분리하지 않는다. 동일 `PowerMix` 아래에서 `table1`은
`Year + Country`, `table2`는 `Year + Month + Country` 단위로 처리한다. 각 벡터는 0.01 단위이며
각 국가·연도 또는 국가·연월 합이 정확히 1.00이 되도록 결과 포맷 단계에서 보정한다.

## 최종 master

| ID | use_yn | parameter_name | parameter_hint |
|---:|:---:|---|---|
| 1 | N | CDD | 국가·연월별 냉방도일(CDD)의 최종 입력값이다. value는 degree-day 단위이며 0 이상이다. |
| 2 | N | Coal Futures Price | 지역·연월별 석탄 선물가격의 최종 절대값이다. value는 USD/t 단위이며 0 이상이다. |
| 3 | N | Gas Futures Price | 지역·연월별 가스 선물가격의 최종 절대값이다. value는 USD/MMBtu 단위이며 0 이상이다. |
| 4 | Y | GDP | 국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. value는 % change를 소수로 입력한다(0.042=4.2%, -0.015=-1.5%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 성장률 자체다. basecase가 있으면 기존 성장률과 이벤트에 명시된 GDP 전망·조정폭을 비교해 최종 성장률로 제안한다. |
| 5 | N | HDD | 국가·연월별 난방도일(HDD)의 최종 입력값이다. value는 degree-day 단위이며 0 이상이다. |
| 6 | Y | PMI | 국가·연월별 PMI 지수의 최종 입력값이다. value는 PMI index 절대값으로 입력한다(예: 49.5). PMI 기준값은 보통 50이며, 50 초과는 경기 확장/생산활동 증가, 50은 중립, 50 미만은 경기 위축/생산활동 감소를 의미한다. 이 모델에서 PMI는 주로 industrial demand, 즉 산업용 가스 수요를 조정하는 경기 민감도 변수다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month에 적용할 PMI 값 자체다. |
| 7 | Y | PowerMix | 국가·연도·에너지원별 발전 믹스 비중의 최종 입력값이다. value는 전체 발전량에서 해당 Energy Source가 차지하는 비중을 소수로 입력한다(0.30=30%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Energy Source에 적용할 최종 비중이다. 현재 basecase는 Gas 위주로 제공되므로, 명확한 전원별 사유가 없으면 Gas 비중 조정을 우선 검토하고 상쇄 전원은 rationale에 설명한다. |
| 8 | Y | Temperature | 국가·연월별 평균 기온의 최종 입력값이다. value는 섭씨(°C) 절대값으로 입력한다(예: 2.3, -1.5, 31.0). proposedValue는 basecase 대비 편차가 아니라 해당 Country/Year/Month에 적용할 기온 자체다. 한파는 정상 기온 대비 하향, 폭염은 정상 기온 대비 상향 방향으로 조정한다. 국가별 기후 차이가 크므로 basecase가 없는 경우 다른 국가의 기온 수준을 기준값으로 삼지 않는다. |
| 9 | N | User-Adjusted Gas Demand | 국가·연월·수요 하위부문별 가스 수요의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month/Demand Sub-Sector에 적용할 최종 수요량이다. 경제 활동이나 발전 믹스 파라미터로 설명되지 않는 직접 수요 정책·절감·연료 전환이 명시된 경우에 사용한다. |
| 10 | N | ElectrificationRate | 국가·연도·Drive Train별 신규차 판매 비중 입력값이다. value는 workbook의 % New Car Sales 단위를 따른다. |
| 11 | Y | Population | 국가·연도별 인구의 최종 입력값이다. value는 천 명 단위 절대값으로 입력한다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 인구 자체다. 인구·이민·인구전망 변화가 event에 명시된 경우에만 사용하고, 일반 경기 변화에는 GDP·PMI를 우선한다. |
| 12 | Y | HurricaneIntensity | 미국 Gulf of Mexico 허리케인의 월별 강도 최종 입력값이다. value는 0~4 정수이며 0은 허리케인 영향 없음, 1~4는 승인된 강도 단계다. event가 GoM 허리케인과 적용 Year/Month를 명시하고 영향 대상 액화 또는 upstream 시설과 연결되는 경우에만 1~4를 제안한다. |
| 13 | Y | LiqProdAdjustment | 액화 Plant Train·월별 LNG 생산량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. LUT 기준값은 월 생산능력 × 이용률로 계산한다. proposedValue는 증감폭이 아니라 해당 Country/LNG Plant/LNG Plant Train/Year/Month의 최종 생산량이며, 대폭·영구 차질이나 신규 Train ramp-up처럼 생산량 직접 override가 필요한 경우에 사용한다. |
| 14 | Y | LiqUtilAdjustment | 액화 Plant Train·월별 가동률의 최종 입력값이다. value는 0~1 소수로 입력한다(1.0=100%, 0.7=70%). 100 같은 percent 표기는 사용하지 않는다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Train/Year/Month에 적용할 가동률 자체다. 기본 범위는 0~1이며, 1 초과는 명확한 근거가 있을 때만 제안한다. Base Case에 존재하는 LNG Plant Train만 수정하고, Country/LNG Plant/Life Cycle Category/Nameplate Capacity는 해당 Train에 종속된 식별 속성으로 맞춘다. |
| 15 | Y | PipelineAdjustment | 파이프라인·월별 송출능력의 최종 절대값이다. value는 Mt/y 단위이며 0 이상이다. 연간 LUT capacity는 0.735를 곱해 Mt/y로 변환한 뒤 동일 연도의 12개월 기준값으로 확장한다. proposedValue는 증감폭이 아니라 해당 Pipeline Name/From Country/To Country/Year/Month에 적용할 최종 송출능력이다. |
| 16 | Y | RegasAdjustment | 재기화 플랜트·월별 처리용량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Continent/Region/Country/Regasification plant/Life Cycle Category/Nameplate capacity/Year/Month에 적용할 최종 처리용량이다. Basecase exact slot만 사용하고 서로 다른 설비나 lifecycle 행을 합치지 않는다. |
| 17 | Y | SupplyDisruption | 국가·연월별 upstream 가스 공급량의 최종 절대값이다. value는 Mt 단위이며 0 이상이다. LUT 기준값은 BCProduction의 연간 Base case supply에 0.735를 곱해 Mt로 변환하고 동일 Province/PNG-LNG의 원본 월별 Seasonality 계수를 곱한 뒤 Country/Year/Month로 합산한다. 계수를 재정규화하지 않는다. proposedValue는 차질량이 아니라 해당 월에 적용할 최종 공급량이다. |
| 18 | Y | PNG Contract Volume | From/To 국가·연도별 PNG 계약 물량의 최종 절대값이다. value는 Mt LNG 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 Unadjusted Gross Gas Import 계약 물량이다. Basecase exact slot만 사용한다. |
| 19 | N | RemainingUnrestrictedAmount | From/To 국가·연도별 거래 제한 이후 남은 무제한 거래 가능 물량의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 Remaining Unrestricted Amount다. Basecase exact slot만 사용한다. |
| 20 | Y | ShippingCost | 연도별 해상 운송비 사용자 입력의 최종 절대값이다. value는 $/d 단위이며 0 이상이다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Year에 적용할 User Input Absolute Value다. Basecase가 제공하는 Year exact slot만 사용하고 영향 범위는 rationale에 보존한다. |
| 21 | N | VolumeCancelled | From/To 국가·연도별 취소 계약 물량의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 취소 물량이다. Basecase exact slot만 사용한다. |
| 22 | Y | RegionalProductionAdjustment | 권역·연도별 upstream 가스 공급량의 최종 절대값이다. value는 Bcm 단위이며 0 이상이다. proposedValue는 증감폭이나 월별 차질량이 아니라 해당 Year/Province·Basin/Country에 적용할 연간 공급량 자체다. Volumes (Bcm)와 % change는 동시에 사용하지 않는다. |
| 23 | Y | ShippingFuelCost | 연도별 LNG 선박 연료비(IFO380)의 최종 절대값이다. value는 $/tonne 단위이며 0 이상이다. proposedValue는 해당 Year에 적용할 연료비 자체이며 ShippingCost 용선료와 합산하지 않는다. ShippingCostInput의 입력 모드가 Absolute일 때만 적용한다. |
| 24 | Y | CanalToll | 운하·연도별 통항료의 최종 절대값이다. value는 $/crossing 단위이며 0 이상이다. proposedValue는 해당 Canal(Suez/Panama)/Year에 적용할 통항료 자체다. ShippingCostInput의 입력 모드가 Absolute일 때만 적용한다. |
| 25 | Y | Suez Canal Cost | Suez 운하·연도별 통항료의 최종 절대값이다. value는 $/crossing 단위이며 0 이상이다. ShippingCostInput의 Suez 블록만 사용한다. |
| 26 | Y | Panama Canal Cost | Panama 운하·연도별 통항료의 최종 절대값이다. value는 $/crossing 단위이며 0 이상이다. ShippingCostInput의 Panama 블록만 사용한다. |

### 모델 대상과 의미 축

운하 관련 현재 target만 요약하면 다음과 같다. 나머지 1~24행의 전체 target과 `basecase_*` 값은
current canonical JSON과 업무용 Excel의 `Parameter Excel Mapping` sheet가 정본이다.

| ID | parameter | model_file | model_sheet | model_table | semantic axes |
|---:|---|---|---|---|---|
| 24 | `CanalToll` | Trade | `ShippingCostInput` | `table4` | Canal(Suez/Panama), Year; v4.0 catalog 호환 전용 |
| 25 | `Suez Canal Cost` | Trade | `ShippingCostInput` | `table4` | Canal(Suez), Year; Suez block only |
| 26 | `Panama Canal Cost` | Trade | `ShippingCostInput` | `table5` | Canal(Panama), Year; Panama block only |

### Basecase 읽기 공통 규칙

- key column이 모두 비는 첫 행에서 읽기를 멈춘다.
- numeric/finite 값만 허용하고 duplicate exact key의 값이 충돌하면 해당 key를 차단한다.
- 정상적인 source 부재에만 같은 exact key의 LUT fallback을 허용한다. source 오류나 충돌을 LUT로
  되살리지 않는다.
- ID 13·14 matrix target은 Year/Month/Period 행과 `G:CL` 84개월(2025-01~2031-12)만 사용한다.
- `LiqUtilAdjustment`는 최종 target에 존재하는 exact Plant/Train 행만 사용한다.
- active MI Base workbook의 구조와 digest가 검증되지 않으면 제안하지 않는다.

## LUT canonical 명세

| parameter | adapter | exact key axes | file | 값/공식 |
|---|---|---|---|---|
| GDP | gdp_growth | Country, Year | Demand_Model_LUT_BCInput_value_based_t2.csv | 당해 GDP / 전년 GDP - 1; exact Year-1 값이 있고 전년 GDP > 0인 경우만 생성 |
| PMI | pmi_reference | Country, Year, Month | Demand_Model_Input_PMIInput_value_based_t1.csv + t2.csv | 수요 국가를 승인 reference country에 연결한 뒤 PMI 절대값 |
| PowerMix | tabular(row) | Country, Year, Energy Source | Demand_Model_LUT_BCInput_value_based_t3.csv | Power Mix 원본 비중 |
| Temperature | temperature_degree_days | Country, Year, Month | Demand_Model_Input_WeatherInput_value_based_t1.csv + t2.csv | HDD>0이면 18-HDD/30, 아니면 CDD>0이면 18+CDD/30, 둘 다 0이면 18°C |
| Population | population | Country, Year | Demand_Model_LUT_BCInput_value_based_t2.csv | Population (thousands) 원본 절대값 |
| HurricaneIntensity | hurricane_intensity | Year, Month | BCHurricanes_Impacct_upstreamAssets.csv + BCHurricanes_GoM.csv | 승인 강도표·GoM 시설 구조를 검증하고 무허리케인 기준 0 생성 |
| LiqProdAdjustment | liq_prod | Country, LNG Plant, LNG Plant Train, Year, Month | BCLiquefaction.csv | 월 생산능력 × 이용률; Closed 시설 제외 |
| LiqUtilAdjustment | liq_util | Country, LNG Plant, LNG Plant Train, Year, Month | BCLiquefaction.csv | 월별 LNG plant utilisation 비율 |
| PipelineAdjustment | pipeline | Pipeline Name, From Country, To Country, Year, Month | BCPipeline.csv | 연간 capacity를 같은 값의 12개월 slot으로 확장 |
| SupplyDisruption | supply_disruption | Country, Year, Month | BCProduction.csv + SeasonalityLogic.csv | 연간 Base case supply × 원본 월 계수 후 Country/Year/Month 합산; 계수 재정규화 안 함 |

모든 경로 prefix는 `fundamental_model_artifact/LUT/`이다. 활성 LUT는 download, header·horizon 검증과
catalog 생성을 모두 수행한다. adapter schema version은 `model-parameter-lut-adapters-v3`다.

### Basecase-only canonical

다음 활성 8개는 master의 `basecase_*`로 읽은 exact slot만 사용한다. 별도 LUT adapter나
nearest/partial-key fallback을 만들지 않는다. `CanalToll`은 v4.0 catalog 호환 전용이므로 현행 v4.1
proposal에는 나머지 7개만 진입한다.

| parameter | exact Basecase 기준 |
|---|---|
| RegasAdjustment | Continent, Region, Country, Regasification Plant, Life Cycle Category, Nameplate Capacity (MTPA), Year, Month |
| PNG Contract Volume | Year, From Country, To Country |
| ShippingCost | Year |
| RegionalProductionAdjustment | Year, Province/Basin/Country |
| ShippingFuelCost | Year |
| CanalToll | Canal(Suez/Panama), Year; v4.0 catalog compatibility only |
| Suez Canal Cost | Canal(Suez), Year; table4 only |
| Panama Canal Cost | Canal(Panama), Year; table5 only |

비활성 Basecase-only 정의인 `User-Adjusted Gas Demand`, `RemainingUnrestrictedAmount`,
`VolumeCancelled`는 master metadata 재현용으로 보존하지만 proposal capability에는 들어가지 않는다.

## v4.1 Model Impact Lever canonical

v0050은 기존 v4.1 Lever 21행(ID 56~76)을 유지하되 운하 관련 3행의 `CanalToll` occurrence를
`Suez Canal Cost`와 `Panama Canal Cost` 조건부 binding으로 제자리 교체한다. catalog version은
`v4.1` 그대로이고 hydrated checksum만 아래 값으로 개정된다.

- Lever 21개
- binding occurrence 56개
- conditional binding occurrence 41개
- executable 고유 Parameter 17개
- hydrated catalog checksum:
  `467749ea59c3af7e875669be23da00c0fd8ef7c226256f9518a5945e36e4d7c4`

운하와 직접 관련된 binding은 다음과 같다.

| Lever code | v4.1 binding |
|---|---|
| `canal_toll` | Suez Canal Cost, Panama Canal Cost conditional |
| `route_disruption` | ShippingCost, ShippingFuelCost, Suez Canal Cost, Panama Canal Cost conditional |
| `regional_price_spread` | 기존 수요·공급·PNG·운송 후보 + Suez Canal Cost + Panama Canal Cost conditional |

Suez/Panama가 직접 명시되고 물리적 운송 경로·적용 연도가 확인될 때만 해당 파라미터를 고른다.
`tmm_mi_model_param_dimension_map`, 과거 `lever_mappings` 또는 Event Type mapping을 v4 fallback으로
사용하지 않는다.

## v1/v3 legacy Dimension mapping

- shared mapping은 129행이고 method count는 direct 35, routing 6, indirect 55, na 33이다.
- direct/routing으로 도달하는 후보는 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`,
  `HurricaneIntensity`, `LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`,
  `SupplyDisruption` 10개다.
- runtime allow-list는 이 중 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment` 5개다.
- Basecase-only 8개와 신규 운하 Parameter에는 legacy dimension mapping을 추가하지 않는다.
- v0050은 legacy mapping의 행·값·checksum을 변경하지 않는다.

변경 전 2026-08-13 snapshot 128행과 v4 rollout 이력은
`scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json` 및 archive
workbook으로 보존한다. 현재 DB 적용 입력으로 사용하지 않는다.

## 충돌 해결과 호환 원칙

| 항목 | 현재 결정 |
|---|---|
| Suez/Panama가 한 Parameter·한 table로 표현됨 | v0050의 v4.1 개정에서 ID 25/table4와 ID 26/table5로 분리 |
| 기존 `CanalToll` 처리 | ID 24와 v4.0 binding은 보존하고 v4.0 catalog 호환 실행에만 사용 |
| 기존 Scenario 처리 | v4는 그대로 보존; v4.1은 version 유지·checksum만 새 정본으로 transaction 이관 |
| PowerMix yearly/monthly | Parameter는 하나로 유지하고 table1/table2 출력 grain만 구분 |
| Coal/Gas futures | `enabled=false`, `use_yn=N`; 2026년 이후 strip 부재 상태에서 이월 금지 |
| 비활성 direct demand/trade override | metadata만 보존하고 proposal capability에서 제외 |
| legacy mapping | v1/v3 129행과 후보 범위 불변 |

## 업무용 mapping workbook과 검증

현재 업무용 Excel은
`resources/mapping/261016_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.1.xlsx`다.
Parameter 26행, 활성 18개, v4.1 binding 56행, legacy mapping 129행을 포함한다.

직전 `260813_...canonical-v4.xlsx`와 더 오래된 workbook은 `resources/mapping/archive/`에 역사
자료로 보존한다. 동기화 검증은 다음 명령으로 수행한다.

```bash
poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only
```

DB migration 정본은 sibling `skmip-mi-agent-mgmt`의 v0050이다. 적용 전후에는 master 1~24,
v4 Lever, legacy mapping, 비-v4.1 Scenario의 exact snapshot이 보존됐는지와 ID 25·26,
v4.1 21행·binding 56건·새 checksum pin, 화면 catalog v4가 정확히 반영됐는지를 함께 검증한다.
