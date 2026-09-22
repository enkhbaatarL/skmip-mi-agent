# Model Parameter Base Case Mapping

> 현재 문서와 260813 workbook은 0032의 최종 workbook target·unit 정합성을 반영한다.
> 0032 현재 runtime 계약은 `model-parameter-canonical-v4-0032.json`과
> `model-impact-lever-canonical-v4-0032.json`(active Lever 18, active/effective Parameter 14,
> checksum `b9d8c051…000b`)을 따른다. 이 문서의 역사 표를 DB 적용 입력으로 사용하지 않는다.

## 기준과 범위

아래 내용은 0032 v4 master·Impact Lever와 v1/v3 shared dimension mapping을 함께 설명한다. 현재 DB 값의
기계 판정 기준은 `scripts/model_parameter/model-parameter-canonical-v4-0032.json`과
`scripts/model_parameter/model-impact-lever-canonical-v4-0032.json`, v1/v3 mapping의 기계 판정 기준은
`scripts/model_parameter/model-parameter-canonical-v1.json` 중 `dimension_mappings`다.
`scripts/model_parameter/snapshots/external_dev_before_model_parameter_v4_20260813.json`의 128행 mapping은
2026-08-13 변경 전 증적으로 보존한다.

- master 21행·활성 14개
- reference capability: LUT-backed 10개, Basecase-only 4개 활성(비활성 metadata 2개 별도 보존)
- v4 impact Lever: 18개, binding occurrence 16개, effective executable occurrence 14개/고유 활성 parameter 14개
- v1/v3 shared legacy dimension mapping: 129행 (direct 35, routing 6, indirect 55, na 33), 최대 후보 10개
- proposal scope: v1/v3는 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment` 5종; v4 extend7은 이 5종과 `PipelineAdjustment`, `SupplyDisruption`을 DB ID/name/target capability로 허용하며 나머지 활성 후보는 `active-but-blocked`로 분류
- 기존 v1/v3 mapping rollout의 수정 대상: `tmm_mi_model_param_dimension_map`만; master, Impact Lever, Scenario/proposal, DB schema는 변경하지 않음
- 공개 proposal/confirmation API와 payload: 변경 없음
- `new-bc-v3`는 최종 workbook의 대상 시트·헤더·Mt 단위를 고정하고, 0032 DB master·Lever metadata와 업무용 mapping workbook을 함께 정합화함
- audit user/version: `model-parameter-canonical-v4`, impact catalog version `v4`

## v4 `new-bc-v3` read-only proposal overlay

이 overlay는 정확히 `api_version=v4`, `generation_strategy=multi_event_model_lever_dimensions`인 신규
proposal에만 적용한다. `read_only`는 Workbook/reference capability이며 기존 proposal persistence를
비활성화한다는 뜻이 아니다. 계약은
`resources/contracts/model-parameter-workbook-contract-v3.json`이며, workbook artifact는 digest가 변하지 않아
`resources/basecase_v4/new-bc-v1/`을 재사용한다. 기존 `resources/basecase/`와 v1/v3 parser는 유지한다.

| Parameter | authoritative source | exact key·변환 | 2026~2030 records |
|---|---|---|---:|
| GDP | Demand `BCInput` Q:U | Country, Year; GDP level에서 전년 대비 성장률 | 815 |
| PMI | Demand `PMIInput` V:AL | Country, Year, Month | 5,040 |
| PowerMix | Demand `BCInput` Z:AF | Country, Year, Energy Source; 동일 annual 월 반복만 dedupe | 4,200 |
| Temperature | Demand `WeatherInput` EI:EY | Country, Year, Month | 5,040 |
| LiqUtilAdjustment | Supply `BCLiquefaction` B:N | Country, LNG Plant, LNG Plant Train, Year, Month | 23,820 |
| PipelineAdjustment | Supply `BCPipeline` B:F | Pipeline Name, From/To Country, Year, Month; 연간 capacity 월 확장 | 420 |
| SupplyDisruption | Supply `BCProduction` C:K + `SeasonalityLogic.csv` | Country, Year, Month; Mt 원본 계수 집계 | 4,908 |

정상적인 source 부재에만 기존 LUT same-exact-key fallback을 허용한다. source cached error, non-finite 값,
상충 duplicate는 해당 exact key를 차단하므로 LUT로 되살리지 않는다. PowerMix는
`Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other` 10개를 Country/Year atomic
vector로 다룬다. raw source fraction에는 기존 5자리 정밀도 변환이나 재정규화를 적용하지 않으며,
raw source·Basecase/LUT 결합 effective reference·Step3 제안 각각에 각 값 0~1, 합 1±`1e-6`을 요구한다.
LiqUtilAdjustment는 하나의 Lever provenance 안에 exact Plant와 exact Train 둘 모두, slot과 일치하는
구체 기간, Group에 실제로 연결된 source Event와 직접 운영 근거가 있을 때만 Step3로 보내고 음수만
차단하며 1 초과값을 보존한다. `Life Cycle Category` 공란은 exact record를 제외하지 않고 metadata와
Step2 판단용 applicability에서만 생략한다.

아래 master 표의 `parameter_hint`와 model target은 0032 DB canonical을 그대로 설명한다. `new-bc-v3`는
최종 workbook target과 단위를 검증하며 공개 API/persistence shape, legacy mapping, workbook writer·Formula/Query
recalc·model engine은 변경하지 않는다.

## 최종 master


| ID  | use_yn | parameter_name              | parameter_hint                                                                                                                                                                                                                                                                                                                                    |
| --- | ------ | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | N      | CDD                         | Country/year-month CDD value (degree-day)                                                                                                                                                                                                                                                                                                         |
| 2   | N      | Coal Futures Price          | Monthly coal futures price by region (USD/t)                                                                                                                                                                                                                                                                                                      |
| 3   | N      | Gas Futures Price           | Monthly gas futures price by region (USD/mmbtu)                                                                                                                                                                                                                                                                                                   |
| 4   | Y      | GDP                         | 국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. value는 % change를 소수로 입력한다(0.042=4.2%, -0.015=-1.5%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 성장률 자체다. basecase가 있으면 기존 성장률과 이벤트에 명시된 GDP 전망·조정폭을 비교해 최종 성장률로 제안한다.                                                                                                                            |
| 5   | N      | HDD                         | Country/year-month HDD value (degree-day)                                                                                                                                                                                                                                                                                                         |
| 6   | Y      | PMI                         | 국가·연월별 PMI 지수의 최종 입력값이다. value는 PMI index 절대값으로 입력한다(예: 49.5). PMI 기준값은 보통 50이며, 50 초과는 경기 확장/생산활동 증가, 50은 중립, 50 미만은 경기 위축/생산활동 감소를 의미한다. 이 모델에서 PMI는 주로 industrial demand, 즉 산업용 가스 수요를 조정하는 경기 민감도 변수다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month에 적용할 PMI 값 자체다.                                                              |
| 7   | Y      | PowerMix                    | 국가·연도·에너지원별 발전 믹스 비중의 최종 입력값이다. value는 전체 발전량에서 해당 Energy Source가 차지하는 비중을 소수로 입력한다(0.30=30%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Energy Source에 적용할 최종 비중이다. 현재 basecase는 Gas 위주로 제공되므로, 명확한 전원별 사유가 없으면 Gas 비중 조정을 우선 검토하고 상쇄 전원은 rationale에 설명한다.                                                                             |
| 8   | Y      | Temperature                 | 국가·연월별 평균 기온의 최종 입력값이다. value는 섭씨(°C) 절대값으로 입력한다(예: 2.3, -1.5, 31.0). proposedValue는 basecase 대비 편차가 아니라 해당 Country/Year/Month에 적용할 기온 자체다. 한파는 정상 기온 대비 하향, 폭염은 정상 기온 대비 상향 방향으로 조정한다. 국가별 기후 차이가 크므로 basecase가 없는 경우 다른 국가의 기온 수준을 기준값으로 삼지 않는다.                                                                                                |
| 9   | Y      | User-Adjusted Gas Demand    | 국가·연월·수요 하위부문별 가스 수요의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month/Demand Sub-Sector에 적용할 최종 수요량이다. 경제 활동이나 발전 믹스 파라미터로 설명되지 않는 직접 수요 정책·절감·연료 전환이 명시된 경우에 사용한다.                                                                                                                     |
| 10  | N      | ElectrificationRate         | Country/year transportation electrification rate (% new car sales)                                                                                                                                                                                                                                                                                |
| 11  | Y      | Population                  | 국가·연도별 인구의 최종 입력값이다. value는 천 명 단위 절대값으로 입력한다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 인구 자체다. 인구·이민·인구전망 변화가 event에 명시된 경우에만 사용하고, 일반 경기 변화에는 GDP·PMI를 우선한다.                                                                                                                                                                    |
| 12  | Y      | HurricaneIntensity          | 미국 Gulf of Mexico 허리케인의 월별 강도 최종 입력값이다. value는 0~4 정수이며 0은 허리케인 영향 없음, 1~4는 승인된 강도 단계다. event가 GoM 허리케인과 적용 Year/Month를 명시하고 영향 대상 액화 또는 upstream 시설과 연결되는 경우에만 1~4를 제안한다.                                                                                                                                                                      |
| 13  | Y      | LiqProdAdjustment           | 액화 Plant Train·월별 LNG 생산량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. LUT 기준값은 월 생산능력 × 이용률로 계산한다. proposedValue는 증감폭이 아니라 해당 Country/LNG Plant/LNG Plant Train/Year/Month의 최종 생산량이며, 대폭·영구 차질이나 신규 Train ramp-up처럼 생산량 직접 override가 필요한 경우에 사용한다.                                                                                                |
| 14  | Y      | LiqUtilAdjustment           | 액화 Plant Train·월별 가동률의 최종 입력값이다. value는 0~1 소수로 입력한다(1.0=100%, 0.7=70%). 100 같은 percent 표기는 사용하지 않는다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Train/Year/Month에 적용할 가동률 자체다. 기본 범위는 0~1이며, 1 초과는 명확한 근거가 있을 때만 제안한다. Base Case에 존재하는 LNG Plant Train만 수정하고, Country/LNG Plant/Life Cycle Category/Nameplate Capacity는 해당 Train에 종속된 식별 속성으로 맞춘다. |
| 15  | Y      | PipelineAdjustment          | 파이프라인·월별 송출능력의 최종 절대값이다. value는 Mt/y 단위이며 0 이상이다. 연간 LUT capacity는 0.735를 곱해 Mt/y로 변환한 뒤 동일 연도의 12개월 기준값으로 확장한다. proposedValue는 증감폭이 아니라 해당 Pipeline Name/From Country/To Country/Year/Month에 적용할 최종 송출능력이다. |
| 16  | Y      | RegasAdjustment             | 재기화 플랜트·월별 처리용량의 최종 절대값이다. value는 Mt LNG/month 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Continent/Region/Country/Regasification plant/Life Cycle Category/Nameplate capacity/Year/Month에 적용할 최종 처리용량이다. Basecase exact slot만 사용하고 서로 다른 설비나 lifecycle 행을 합치지 않는다.                                                                          |
| 17  | Y      | SupplyDisruption            | 국가·연월별 upstream 가스 공급량의 최종 절대값이다. value는 Mt 단위이며 0 이상이다. LUT 기준값은 BCProduction의 연간 Base case supply에 0.735를 곱해 Mt로 변환하고 동일 Province/PNG-LNG의 원본 월별 Seasonality 계수를 곱한 뒤 Country/Year/Month로 합산한다. 계수를 재정규화하지 않는다. proposedValue는 차질량이 아니라 해당 월에 적용할 최종 공급량이다. |
| 18  | Y      | PNG Contract Volume         | From/To 국가·연도별 PNG 계약 물량의 최종 절대값이다. value는 Mt LNG 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 Unadjusted Gross Gas Import 계약 물량이다. Basecase exact slot만 사용한다. |
| 19  | N      | RemainingUnrestrictedAmount | From/To 국가·연도별 거래 제한 이후 남은 무제한 거래 가능 물량의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 Remaining Unrestricted Amount다. Basecase exact slot만 사용한다. |
| 20  | Y      | ShippingCost                | 연도별 해상 운송비 사용자 입력의 최종 절대값이다. value는 $/d 단위이며 0 이상이다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Year에 적용할 User Input Absolute Value다. Basecase가 제공하는 Year exact slot만 사용하고 영향 범위는 rationale에 보존한다.                                                                                                                                                    |
| 21  | N      | VolumeCancelled             | From/To 국가·연도별 취소 계약 물량의 최종 절대값이다. value는 BCM 단위이며 0 이상이다. proposedValue는 증감폭이 아니라 해당 Year/From Country/To Country에 적용할 취소 물량이다. Basecase exact slot만 사용한다. |




### 모델 대상과 의미 축


| ID  | model_file | model_sheet                   | model_table | semantic_axes                                                                                                                                                                                                                                                                                                                                                                                          |
| --- | ---------- | ----------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Demand     | WeatherAdjustment             | table1      | 평년 대비 기온편차 변환 — 국가·연·월                                                                                                                                                                                                                                                                                                                                                                                 |
| 2   | Demand     | CoalGasAdjustment             | table1      | 석탄 선물가격 strip — 지역·월 (Asia=Newcastle, EU=ARA)                                                                                                                                                                                                                                                                                                                                                          |
| 3   | Demand     | CoalGasAdjustment             | table2      | 가스 선물가격 strip — 지역·월 (Asia=JKM, EU=TTF)                                                                                                                                                                                                                                                                                                                                                                |
| 4   | Demand     | GDPPopulationAdjustment       | table1      | slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: United States, China, Japan, South Korea, Taiwan (China), Belgium, France, Germany, Italy, Netherlands, Spain, India); value=F:% change(+/-), 소수형 전년대비 실질 GDP 성장률                                                                                                                                                                             |
| 5   | Demand     | WeatherAdjustment             | table1      | 평년 대비 기온편차 변환 — 국가·연·월                                                                                                                                                                                                                                                                                                                                                                                 |
| 6   | Demand     | PMIAdjustment                 | table1      | slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Country(국가명; basecase 예: China, Philippines); value=F:PMI, PMI index 절대값                                                                                                                                                                                                                                                                              |
| 7   | Demand     | PowerMixAdjustment            | table1      | slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: China, Japan, South Korea, Taiwan (China), Germany, France, Italy, Spain, Netherlands, Belgium, United Kingdom), D:Energy Source(Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other; basecase 예: Gas); value=F:% Power Mix, 소수형 발전 비중                                                                                       |
| 8   | Demand     | WeatherAdjustment             | table2      | slot=K:Year(YYYY, 2026~2030), L:Month(1~12; basecase 예: 1~3), M:Country(국가명; basecase 예: China, Japan, South Korea, Germany, France, Netherlands, Spain, Italy, Belgium, United Kingdom); value=O:Temperature (°C), 섭씨 절대 기온                                                                                                                                                                         |
| 9   | Demand     | DemandOutputOverwrite         | table1      | slot=D:Country, E:Year(YYYY, 2026~2030), F:Month(1~12), G:Demand Sub-Sector; value=H:User-Adjusted Gas Demand [BCM], 직접 수요 절대값                                                                                                                                                                                                                                                                                  |
| 10  | Demand     | ElectrificationRateAdjustment | table1      | 수송 전기화율 (본 21종 직접 해당 적음)                                                                                                                                                                                                                                                                                                                                                                               |
| 11  | Demand     | GDPPopulationAdjustment       | table2      | slot=J:Year(YYYY, 2026~2030), K:Country(국가명), value=M:Population (Thousands), 천 명 단위 인구 절대값                                                                                                                                                                                                                                                                                                            |
| 12  | Supply     | {USA}Hurricanes               | table1      | slot=B:Year(YYYY, 2026~2030), C:Month(1~12); value=D:Hurricane intensity(0~4 정수, 0=no hurricane)                                                                                                                                                                                                                                                                                                     |
| 13  | Supply     | LiqProdAdjustment             | table1      | slot=Country, LNG Plant, LNG Plant Train, Year(YYYY), Month(1~12); metadata=Life Cycle Category, Nameplate Capacity (MTPA), Period; value=Production (Mt LNG/month), 월 생산능력×이용률                                                                                                                                                                                                                        |
| 14  | Supply     | LiqUtilAdjustment             | table1      | slot=Country(국가명; 예: Algeria, Angola), LNG Plant(예: Arzew GL1Z, Angola LNG), LNG Plant Train(348개 basecase Train 중 선택; 예: Arzew GL1Z T1-T6, Angola LNG T1, Gorgon LNG T1, North West Shelf LNG T1, Sabine Pass LNG Stage 5 Expansion T1), Life Cycle Category(예: Operational), Nameplate Capacity MTPA(숫자; 예: 7.9, 5.2), Year(YYYY), Month(1~12), Period(숫자); value=Utilization Rate, 0~1 소수형 월별 가동률 |
| 15  | Supply     | PipelineAdjustment            | table1      | slot=B:Year, C:Month, D:Pipeline name, E:From country, F:To country; value=H:User adjusted capacity (Mt/y) |
| 16  | Supply     | RegasAdjustment               | table1      | slot=B:Continent, C:Region, D:Country, E:Regasification plant, F:Life Cycle Category, G:Nameplate capacity (MTPA), Year(YYYY, 2026~2030), Month(1~12); value=RegasAdjustment (Mt LNG/month), 재기화 처리용량 절대값                                                                                                                                                                                                  |
| 17  | Supply     | ProductionAdjustment          | table2      | slot=I:Year, J:Month, K:Country; value=M:Volumes (Mt) |
| 18  | Trade      | MidstreamContractInput        | table1      | slot=A:Year, B:From Country, C:To Country; value=D:Unadjusted Gross Gas Import [Mt LNG] |
| 19  | Trade      | TradeRestrictionInput         | table1      | slot=B:Year(YYYY, 2026~2030), C:From Country, D:To Country; value=J:Remaining Unrestricted Amount [BCM], 거래 가능 물량 절대값                                                                                                                                                                                                                                                                                    |
| 20  | Trade      | ShippingCostInput             | table1      | slot=B:Year(YYYY, 2026~2030); value=F:User Input Absolute Value ($/d), 연도별 해상 운송비 절대값                                                                                                                                                                                                                                                                                                                 |
| 21  | Trade      | TradeRestrictionInput         | table1      | slot=B:Year(YYYY, 2026~2030), C:From Country, D:To Country; value=F:Volume [BCM], 취소 계약 물량 절대값                                                                                                                                                                                                                                                                                                           |




### Basecase 읽기 규칙


| ID  | mode                | header | data start | column roles                                                                                            | row filter | year row | month row | period row | value start | value end | stop rule                       |
| --- | ------------------- | ------ | ---------- | ------------------------------------------------------------------------------------------------------- | ---------- | -------- | --------- | ---------- | ----------- | --------- | ------------------------------- |
| 1   | fixed_columns       | 6      | 12         | B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD                                                            | E=CDD      | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 2   | fixed_columns       | 6      | 12         | B:Month-Year,C:Region,E:Coal Futures Price (USD/t)                                                      | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 3   | fixed_columns       | 6      | 12         | H:Month-Year,I:Region,K:Gas Futures Price (USD/mmbtu)                                                   | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 4   | fixed_columns       | 6      | 12         | B:Year,C:Country,F:% change (+/-)                                                                       | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 5   | fixed_columns       | 6      | 12         | B:Year,C:Month,D:Country,E:HDD/CDD,G:HDD/CDD                                                            | E=HDD      | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 6   | fixed_columns       | 6      | 13         | B:Year,C:Month,D:Country,F:PMI                                                                          | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 7   | fixed_columns       | 6      | 12         | B:Year,C:Country,D:Energy Source,F:% Power Mix                                                          | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 8   | fixed_columns       | 6      | 12         | K:Year,L:Month,M:Country,O:Temperature (°C)                                                             | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 9   | fixed_columns       | 7      | 8          | D:Country,E:Year,F:Month,G:Demand Sub-Sector,H:User-Adjusted Gas Demand [BCM]                           | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 10  | fixed_columns       | 6      | 12         | B:Year,C:Country,D:Drive Train,F:% New Car Sales                                                        | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 11  | fixed_columns       | 6      | 12         | J:Year,K:Country,M:Population (Thousands)                                                               | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 12  | fixed_columns       | 7      | 13         | B:Year,C:Month,D:Hurricane intensity                                                                    | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 13  | matrix_time_columns | 10     | 11         | B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)               | —          | 7        | 8         | 9          | G           | DA        | stop_when_all_key_columns_empty |
| 14  | matrix_time_columns | 10     | 11         | B:Country,C:LNG Plant,D:LNG Plant Train,E:Life Cycle Category,F:Nameplate Capacity (MTPA)               | —          | 7        | 8         | 9          | G           | DA        | stop_when_all_key_columns_empty |
| 15  | fixed_columns       | 7      | 13         | B:Year,C:Month,D:Pipeline name,E:From country,F:To country,H:User adjusted capacity (Mt/y)                | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 16  | matrix_time_columns | 10     | 11         | B:Continent,C:Region,D:Country,E:Regasification plant,F:Life Cycle Category,G:Nameplate capacity (MTPA) | —          | 9        | 10        | —          | H           | DK        | stop_when_all_key_columns_empty |
| 17  | fixed_columns       | 7      | 8          | I:Year,J:Month,K:Country,M:Volumes (Mt)                                                                 | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 18  | fixed_columns       | 4      | 5          | A:Year,B:From Country,C:To Country,D:Unadjusted Gross Gas Import [Mt LNG]                               | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 19  | fixed_columns       | 5      | 6          | B:Year,C:From Country,D:To Country,J:Remaining Unrestricted Amount [BCM]                                | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 20  | fixed_columns       | 5      | 6          | B:Year,F:User Input Absolute Value ($/d)                                                                | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |
| 21  | fixed_columns       | 5      | 6          | B:Year,C:From Country,D:To Country,F:Volume [BCM]                                                       | —          | —        | —         | —          | —           | —         | stop_when_all_key_columns_empty |


기본키 및 생성 감사 컬럼은 변경하지 않는다. use_yn, 이름·hint, 모델 대상, semantic_axes, 모든 basecase_* 컬럼, 수정 감사 컬럼과 del_yn만 canonical matrix로 비교·갱신한다.

## LUT canonical 명세


| parameter          | adapter                 | exact key axes                                       | file                                                           | 값/공식                                                               |
| ------------------ | ----------------------- | ---------------------------------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------ |
| GDP                | gdp_growth              | Country, Year                                        | Demand_Model_LUT_BCInput_value_based_t2.csv                    | 당해 GDP / 전년 GDP - 1; exact Year-1 값이 있고 전년 GDP > 0인 경우만 생성         |
| PMI                | pmi_reference           | Country, Year, Month                                 | Demand_Model_Input_PMIInput_value_based_t1.csv + t2.csv        | 수요 국가를 승인 reference country에 연결한 뒤 PMI 절대값                         |
| PowerMix           | tabular(row)            | Country, Year, Energy Source                         | Demand_Model_LUT_BCInput_value_based_t3.csv                    | Power Mix 원본 비중                                                    |
| Temperature        | temperature_degree_days | Country, Year, Month                                 | Demand_Model_Input_WeatherInput_value_based_t1.csv + t2.csv    | HDD>0이면 18-HDD/30, 아니면 CDD>0이면 18+CDD/30, 둘 다 0이면 18°C             |
| Population         | population              | Country, Year                                        | Demand_Model_LUT_BCInput_value_based_t2.csv                    | Population (thousands) 원본 절대값                                      |
| HurricaneIntensity | hurricane_intensity     | Year, Month                                          | BCHurricanes_Impacct_upstreamAssets.csv + BCHurricanes_GoM.csv | 승인 강도표·GoM 시설 구조를 검증하고 무허리케인 기준 0 생성                               |
| LiqProdAdjustment  | liq_prod                | Country, LNG Plant, LNG Plant Train, Year, Month     | BCLiquefaction.csv                                             | 월 생산능력 × 이용률; Closed 시설 제외                                         |
| LiqUtilAdjustment  | liq_util                | Country, LNG Plant, LNG Plant Train, Year, Month     | BCLiquefaction.csv                                             | 월별 LNG plant utilisation 비율                                        |
| PipelineAdjustment | pipeline                | Pipeline Name, From Country, To Country, Year, Month | BCPipeline.csv                                                 | 연간 capacity를 같은 값의 12개월 slot으로 확장                                  |
| SupplyDisruption   | supply_disruption       | Country, Year, Month                                 | BCProduction.csv + SeasonalityLogic.csv                        | 연간 Base case supply × 원본 월 계수 후 Country/Year/Month 합산; 계수 재정규화 안 함 |


모든 경로 prefix는 fundamental_model_artifact/LUT/이다. 활성 LUT는 download, header·horizon 검증과 catalog 생성을 모두 수행한다. adapter schema version은 model-parameter-lut-adapters-v3이다.

### Basecase-only canonical

다음 6개는 master의 `basecase_*`로 읽은 exact slot만 사용한다. 별도 LUT adapter나 nearest/partial-key fallback을 만들지 않으며, Basecase slot이 없으면 해당 slot을 후보에서 제외한다.

| parameter | exact Basecase 기준 |
|---|---|
| User-Adjusted Gas Demand | Country, Year, Month, Demand Sub-Sector |
| RegasAdjustment | Continent, Region, Country, Regasification Plant, Life Cycle Category, Nameplate Capacity (MTPA), Year, Month |
| PNG Contract Volume | Year, From Country, To Country |
| RemainingUnrestrictedAmount | Year, From Country, To Country |
| ShippingCost | Year |
| VolumeCancelled | Year, From Country, To Country |

## v4 Model Impact Lever canonical

v4는 선택 dimension value의 `lever_states`와 아래 active catalog binding을 사용한다. `tmm_mi_model_param_dimension_map`, Event Type, 과거 `lever_mappings`/`lever_refs`/`impact_lever_refs`를 조회하거나 fallback으로 사용하지 않는다.

| Lever code | binding |
|---|---|
| `weather_demand` | Temperature primary; HDD, CDD alternative(비활성 진단) |
| `power_generation_mix` | PowerMix primary |
| `economic_activity` | GDP primary; PMI alternative; Population alternative(인구·이민·인구전망 명시 시) |
| `direct_gas_demand` | User-Adjusted Gas Demand primary |
| `upstream_production` | SupplyDisruption primary |
| `liquefaction_availability` | LiqUtilAdjustment primary; LiqProdAdjustment alternative |
| `regasification_capacity` | RegasAdjustment primary |
| `natural_disaster_disruption` | HurricaneIntensity primary |
| `pipeline_capacity` | PipelineAdjustment primary |
| `shipping_cost` | ShippingCost primary |
| `route_disruption` | ShippingCost primary |
| `contract_volume` | VolumeCancelled primary; PNG Contract Volume alternative |
| `trade_restriction` | RemainingUnrestrictedAmount primary; VolumeCancelled alternative |

세 `price_only` Lever는 binding이 없다. CDD/HDD binding을 포함하면 catalog binding occurrence는 20개이며, 비활성 master binding을 제외한 effective executable occurrence는 18개, 고유 활성 parameter는 16개다. 이 수치는 0029 canonical/catalog capability 기준이다. 현재 0030 v4 extend7은 7개 ID만 proposal 후보로 허용하며 v4 binding은 Step1.5 없이 deterministic candidate로 보존한다.

### 보류와 보조 resource


| 분류  | 이름                          | 설정                           | 사유/용도                                                                                    |
| --- | --------------------------- | ---------------------------- | ---------------------------------------------------------------------------------------- |
| 비활성 | CDD, HDD                    | use_yn=N                     | weather Lever binding capability와 `INACTIVE_MODEL_PARAMETER` 진단은 보존하되 실행 후보에서 제외 |
| 보류  | Coal Futures Price          | enabled=false, futures_price | 2026년 이후 futures strip 부재; 구조만 검증하고 catalog 제외                                           |
| 보류  | Gas Futures Price           | enabled=false, futures_price | 2026년 이후 futures strip 부재; 구조만 검증하고 catalog 제외                                           |
| 보류  | ElectrificationRate         | LUT spec 없음                  | 유효 Basecase·국가/연/Drive Train LUT·승인 mapping 부재                                           |
| 보조  | demand_general_country_list | references                   | Demand_Model_LUT_General_value_based_t6.csv 국가 목록 동기화·header 검증; 독립 parameter record 미생성 |




## v1/v3 legacy Dimension mapping

- 현재 shared mapping은 129행이고 method count는 direct 35, routing 6, indirect 55, na 33이다. 모두 `use_yn='Y'`, `del_yn='N'`이다.
- direct/routing으로 도달하는 후보는 `GDP`, `PMI`, `PowerMix`, `Temperature`, `Population`, `HurricaneIntensity`, `LiqProdAdjustment`, `LiqUtilAdjustment`, `PipelineAdjustment`, `SupplyDisruption` 10개다.
- v1/v3는 이 10개 중 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment`만 허용한다. v4는 여기에 ID 15 `PipelineAdjustment`, ID 17 `SupplyDisruption`을 추가한 extend7 capability를 사용한다.
- 아래 128행·25/2/55/46 설명과 표는 2026-08-13 변경 전 snapshot 증적이다. 현재 DB 상태로 사용하지 않는다.

### 변경 전 증적

- 128행 전체는 2026-08-13 외부 개발 DB snapshot과 정확히 같았으며, 당시 v4 rollout은 이 행을 추가·복구·삭제하지 않았다.
- 아래 13행은 이전 local v1 canonical에서는 direct/routing 복구 대상이었지만, 변경 전 외부 DB에서는 `na`/`model_param_id=NULL`이었다. 당시에는 외부 DB를 우선해 v1/v3 후보에서 제외했다.
- 이전 local v1 canonical의 Population `(event type 21, economic_intensity, model_param_id 11)` routing 1행도 변경 전 외부 DB에는 없었다. 당시 Population은 v4 `economic_activity` Lever의 alternative binding으로만 실행했다.
- mapping ID 67·95·105는 method와 model parameter 연결을 바꾸지 않고 comment를 현재 외부 DB snapshot 문자열로 맞췄다.
- null model_param_id인 indirect/na 역사 행은 유지한다. 이 때문에 null을 포함한 SQL UNIQUE의 의미와 별개로, 중복 불변식은 model_param_id가 있는 natural key에 적용한다.
- 이 128행은 변경 전 v1/v3 전용 상태였다. Basecase-only 6개에는 direct/routing row를 추가하지 않았으며 v4 후보 선정에는 사용하지 않는다.


| mapping ID | event type | dimension key | 이전 local v1 canonical | 변경 전 외부 DB AS-IS | 당시 v1/v3 결과 |
| --- | ---: | --- | --- | --- | --- |
| 2 | 1 | utilization_change_amount | direct → SupplyDisruption | na / NULL | 후보 제외 |
| 5 | 1 | alt_gas_supply_availability | direct → SupplyDisruption | na / NULL | 후보 제외 |
| 9 | 2 | utilization_change_amount | direct → LiqProdAdjustment | na / NULL | 후보 제외 |
| 16 | 3 | target_utilization_at_ramp_up | direct → LiqProdAdjustment | na / NULL | 후보 제외 |
| 18 | 4 | utilization_change_amount | direct → PipelineAdjustment | na / NULL | 후보 제외 |
| 23 | 4 | alt_supply_availability | direct → PipelineAdjustment | na / NULL | 후보 제외 |
| 66 | 11 | affected_facility_type | routing → SupplyDisruption | na / NULL | 후보 제외 |
| 68 | 11 | affected_facility_type | routing → LiqProdAdjustment | na / NULL | 후보 제외 |
| 70 | 11 | affected_facility_type | routing → HurricaneIntensity | na / NULL | 후보 제외 |
| 96 | 17 | supply_disruption_intensity | direct → LiqProdAdjustment | na / NULL | 후보 제외 |
| 97 | 17 | supply_disruption_intensity | direct → SupplyDisruption | na / NULL | 후보 제외 |
| 106 | 18 | supply_disruption_intensity | direct → LiqProdAdjustment | na / NULL | 후보 제외 |
| 107 | 18 | supply_disruption_intensity | direct → SupplyDisruption | na / NULL | 후보 제외 |
| 없음 | 21 | economic_intensity | routing → Population 신규 행 | 행 없음 | Population 후보 없음 |

현재는 위 13개 `na/NULL` 행을 표의 이전 local v1 canonical에 적힌 direct/routing으로 복구했고, Population routing 1행을 추가했다. mapping ID 67·95·105는 method·parameter 연결은 유지하고 comment만 현행화했다. 이 mapping-only 변경은 v4 master, Impact Lever catalog, Scenario/proposal 결과를 변경하지 않는다.


legacy direct/routing mapping은 모두 활성·미삭제 master만 참조해야 하며, 모든 event type/dimension key는 활성 scenario dimension template에 존재해야 한다. orphan FK와 `model_param_id`가 있는 natural key 중복은 허용하지 않는다. Basecase-only 6개에 legacy 후보 mapping이 없는 것은 의도된 상태다.

## 충돌 해결 이력


| 충돌                                             | 최종 선택                                                        | 근거와 반영 위치                                                                                                         |
| ---------------------------------------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| v1 mapping 후보는 LUT-backed 10개                            | 0032 master 21행·활성 14행, v1/v3 5종·v4 extend7 7종 proposal scope | 최종 workbook target·unit과 DB canonical/catalog checksum 정합화 |
| 초안의 header/data start/column role과 현재 DB 값이 다름 | 기존 활성 5개는 검증된 DB 값을 유지; 나머지는 실제 workbook 구조와 최종 LUT 계산으로 정규화 | canonical JSON의 21행 전체 basecase_*가 read-back 기준                                                                   |
| Coal/Gas futures를 활성으로 표시                      | enabled=false 및 use_yn=N                                     | 2026년 이후 strip이 제공되기 전 과거값 이월 금지                                                                                  |
| ElectrificationRate 활성 여부                      | use_yn=N, LUT spec 없음                                        | 유효 Basecase/LUT/승인 mapping 부재                                                                                     |
| LiqProdAdjustment 미지원/미대상 안내                   | use_yn=Y, liq_prod adapter, legacy direct/routing 복구, v4 Lever alternative binding | BCLiquefaction 월 생산능력×이용률로 exact slot을 만들고 v1/v3와 v4의 각 후보 소스에서 조건부 후보화 |
| Population의 일반 경제 이벤트 적용 가능성                   | v1/v3 routing 1건과 v4 `economic_activity` alternative binding | 인구·이민·인구전망이 명시된 경우만 선택하고 일반 경기는 GDP·PMI 우선 |
| 신규 활성 6개를 legacy mapping에도 추가할지 여부             | 추가하지 않음                                                   | v4는 Lever-native 전용이며 v1/v3 후보 범위를 바꾸지 않음                                                                                    |
| catalog 변경 뒤 기존 v4 Scenario 처리                         | proposal 차단 후 신규 Scenario 생성                             | 저장된 checksum과 active catalog checksum이 다르면 조용히 재해석하지 않음                                                                    |




## 기존 v1/v3 mapping rollout의 적용과 검증

아래 DB 명령은 기존 mapping rollout 절차다. 역사적 runtime allow-list-only v0.2.4에서는 실행하지 않았으며,
당시 DB·canonical·config·workbook은 repository diff와 read-only fingerprint로 불변을 확인했다. 현재
`new-bc-v3`와 0032 migration은 final workbook target·unit metadata를 함께 정합화한다.

1. `poetry run python scripts/model_parameter/apply_model_parameter_v1_v3_mapping.py`로 dry-run한다. live v4 master·Lever canonical을 선검증하고 mapping만 DML한 뒤 129행·35/6/55/33, exact 후보 10개와 전체 불변식을 검증하고 rollback한다.
2. 승인된 DB에는 mgmt 0032 migration을 적용한다. 적용 후 master 21행·활성 14개와 새 catalog checksum을 확인한다.
3. 적용 후 Lever 18개·binding 16/14/14와 shared legacy mapping 129행·method count 35/6/55/33이 정확히 보존되는지 확인한다.
4. `poetry run python scripts/model_parameter/sync_mapping_workbook.py --check-only`로 legacy mapping Excel과 JSON·config·archive의 정합성을 확인한다.
5. 역사적 v4 release replay는 `poetry run python tests/manual/model_parameter_agent/verify_model_parameter_v4_sql_mysql.py`로 격리 MySQL 8의 128행 snapshot에서만 검증한다. 현재 129행 외부 DB의 사후 판정에는 dated v4 runner/SQL을 사용하지 않는다.

0029 업무용 Excel은 `resources/mapping/260813_시나리오가정_MI수급모델_input_매핑_model-parameter-canonical-v4.xlsx`다. parameter 21행·활성 16개, Lever binding과 v1/v3 shared legacy mapping 129행을 함께 보여 준다. 0029 재현 시에는 v4 master·Lever JSON과 v1 mapping JSON의 `dimension_mappings`를 분리해 사용한다.

이전 `260625_...xlsx`, `260702_...v0.4.xlsx`, `260807_...canonical-v1.xlsx`는 `resources/mapping/archive/`의 역사 자료다. 실제 v4 SQL 검증 결과와 외부 DB rollback digest는 실행한 명령·환경·hash와 함께 통합 release report에 기록하며, 이 문서 자체는 아직 수행하지 않은 DB 적용이나 검증 통과를 주장하지 않는다.
