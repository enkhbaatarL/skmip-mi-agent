# Model Parameter Hint/Comment Final DB Changes

- 작성일: 2026-07-08
- 기준 DB: 로컬 `midb`
- 대상 파라미터: `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment`
- DB 반영 방식: 모든 파라미터 인터뷰 종료 후 한 번에 반영

## GDP

### `tmm_mi_model_param_m`

`model_param_id=4`, `parameter_name=GDP`

`parameter_hint`

```text
국가·연도별 실질 GDP 전년 대비 성장률의 최종 입력값이다. value는 % change를 소수로 입력한다(0.042=4.2%, -0.015=-1.5%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year에 적용할 성장률 자체다. basecase가 있으면 기존 성장률과 이벤트에 명시된 GDP 전망·조정폭을 비교해 최종 성장률로 제안한다.
```

`semantic_axes`

```text
slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: United States, China, Japan, South Korea, Taiwan (China), Belgium, France, Germany, Italy, Netherlands, Spain, India); value=F:% change(+/-), 소수형 전년대비 실질 GDP 성장률
```

### `tmm_mi_model_param_dimension_map`

`model_param_dimension_map_id=127`, `event_type_l2_id=21`, `dimension_key=economic_intensity`, `mapping_method=direct`, `parameter=GDP`

`comment`

```text
event에 명시된 국가별 GDP 성장률 전망, 전망치 수정폭, 하방/상방 시나리오를 우선 사용해 해당 Country/Year의 최종 성장률을 산정한다. 성장률 전망이 정량으로 제시되지 않으면 경기 둔화/회복 강도와 기간을 근거로 basecase 대비 보수적으로 조정한다. LNG 수요 영향률이나 가격 영향률을 GDP 성장률 multiplier로 사용하지 않는다.
```

## PMI

### `tmm_mi_model_param_m`

`model_param_id=6`, `parameter_name=PMI`

`parameter_hint`

```text
국가·연월별 PMI 지수의 최종 입력값이다. value는 PMI index 절대값으로 입력한다(예: 49.5). PMI 기준값은 보통 50이며, 50 초과는 경기 확장/생산활동 증가, 50은 중립, 50 미만은 경기 위축/생산활동 감소를 의미한다. 이 모델에서 PMI는 주로 industrial demand, 즉 산업용 가스 수요를 조정하는 경기 민감도 변수다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Month에 적용할 PMI 값 자체다.
```

`semantic_axes`

```text
slot=B:Year(YYYY, 2026~2030), C:Month(1~12), D:Country(국가명; basecase 예: China, Philippines); value=F:PMI, PMI index 절대값
```

### `tmm_mi_model_param_dimension_map`

`model_param_dimension_map_id=126`, `event_type_l2_id=21`, `dimension_key=economic_intensity`, `mapping_method=direct`, `parameter=PMI`

`comment`

```text
event에 명시된 제조업/서비스업 경기, 생산활동 증가·감소, 산업활동 둔화·회복, 단기 경기 강도를 근거로 해당 Country/Year/Month의 PMI 지수 최종값을 산정한다. basecase가 있으면 기존 PMI 수준과 이벤트 방향을 비교해 보수적으로 조정한다. basecase가 없으면 다른 국가의 PMI 수준을 기준값으로 삼지 않고, 이벤트에 제시된 해당 국가의 경기 방향과 PMI 기준값 50을 중심으로 산정한다.
```

## PowerMix

### `tmm_mi_model_param_m`

`model_param_id=7`, `parameter_name=PowerMix`

`parameter_hint`

```text
국가·연도·에너지원별 발전 믹스 비중의 최종 입력값이다. value는 전체 발전량에서 해당 Energy Source가 차지하는 비중을 소수로 입력한다(0.30=30%). proposedValue는 basecase 대비 증감폭이 아니라 해당 Country/Year/Energy Source에 적용할 최종 비중이다. 현재 basecase는 Gas 위주로 제공되므로, 명확한 전원별 사유가 없으면 Gas 비중 조정을 우선 검토하고 상쇄 전원은 rationale에 설명한다.
```

`semantic_axes`

```text
slot=B:Year(YYYY, 2026~2030), C:Country(국가명; basecase 예: China, Japan, South Korea, Taiwan (China), Germany, France, Italy, Spain, Netherlands, Belgium, United Kingdom), D:Energy Source(Liquids/Hydro/Solar/Wind/Bioenergy/Gas/Coal/Nuclear/Geothermal/Other; basecase 예: Gas); value=F:% Power Mix, 소수형 발전 비중
```

### `tmm_mi_model_param_dimension_map`

`model_param_dimension_map_id=26`, `event_type_l2_id=5`, `dimension_key=capacity_change_scale`, `mapping_method=direct`, `parameter=PowerMix`

`comment`

```text
발전소 용량·가동 변화 규모를 근거로 해당 Country/Year의 Gas PowerMix 최종 비중을 산정한다. capacity_change_scale은 조정폭의 주된 근거로 사용하고, affected_period와 structural_change_yn은 적용 연도와 지속성 판단에 반영한다.
```

`model_param_dimension_map_id=29`, `event_type_l2_id=5`, `dimension_key=alt_energy_absorption`, `mapping_method=direct`, `parameter=PowerMix`

`comment`

```text
발전소 용량·가동 변화로 발생한 전력 공백 또는 증분을 타 에너지원이 얼마나 흡수하는지 반영해 Gas PowerMix 최종 비중을 산정한다. alt_energy_absorption이 낮을수록 Gas 비중 변화를 크게 반영하고, 높을수록 Gas 비중 변화는 작게 둔다.
```

`model_param_dimension_map_id=27`, `event_type_l2_id=5`, `dimension_key=capacity_change_scale`, `mapping_method=na`

`comment`

```text
NULL
```

## Temperature

### `tmm_mi_model_param_m`

`model_param_id=8`, `parameter_name=Temperature`

`parameter_hint`

```text
국가·연월별 평균 기온의 최종 입력값이다. value는 섭씨(°C) 절대값으로 입력한다(예: 2.3, -1.5, 31.0). proposedValue는 basecase 대비 편차가 아니라 해당 Country/Year/Month에 적용할 기온 자체다. 한파는 정상 기온 대비 하향, 폭염은 정상 기온 대비 상향 방향으로 조정한다. 국가별 기후 차이가 크므로 basecase가 없는 경우 다른 국가의 기온 수준을 기준값으로 삼지 않는다.
```

`semantic_axes`

```text
slot=K:Year(YYYY, 2026~2030), L:Month(1~12; basecase 예: 1~3), M:Country(국가명; basecase 예: China, Japan, South Korea, Germany, France, Netherlands, Spain, Italy, Belgium, United Kingdom); value=O:Temperature (°C), 섭씨 절대 기온
```

### `tmm_mi_model_param_dimension_map`

`model_param_dimension_map_id=34`, `event_type_l2_id=6`, `dimension_key=cold_wave_intensity`, `mapping_method=direct`, `parameter=Temperature`

`comment`

```text
event에 명시된 한파 강도와 적용 기간을 근거로 해당 Country/Year/Month의 Temperature 최종값을 산정한다. 한파는 정상 기온 대비 하향 방향으로 반영하고, 해당 국가 기준 겨울 또는 한파가 발생 가능한 계절의 월을 선택한다. cold_wave_intensity의 온도 편차 범위와 peak_timing_pattern을 참고해 월별 조정폭을 차등 적용한다.
```

`model_param_dimension_map_id=40`, `event_type_l2_id=7`, `dimension_key=heatwave_intensity`, `mapping_method=direct`, `parameter=Temperature`

`comment`

```text
event에 명시된 폭염 강도와 적용 기간을 근거로 해당 Country/Year/Month의 Temperature 최종값을 산정한다. 폭염은 정상 기온 대비 상향 방향으로 반영하고, 해당 국가 기준 여름 또는 폭염이 발생 가능한 계절의 월을 선택한다. heatwave_intensity의 온도 편차 범위와 peak_timing_pattern을 참고해 월별 조정폭을 차등 적용한다.
```

`model_param_dimension_map_id=33`, `event_type_l2_id=6`, `dimension_key=cold_wave_intensity`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=39`, `event_type_l2_id=7`, `dimension_key=heatwave_intensity`, `mapping_method=na`

`comment`

```text
NULL
```

## LiqUtilAdjustment

### `tmm_mi_model_param_m`

`model_param_id=14`, `parameter_name=LiqUtilAdjustment`

`parameter_hint`

```text
액화 Plant Train·월별 가동률의 최종 입력값이다. value는 0~1 소수로 입력한다(1.0=100%, 0.7=70%). 100 같은 percent 표기는 사용하지 않는다. proposedValue는 basecase 대비 증감폭이 아니라 해당 Train/Year/Month에 적용할 가동률 자체다. 기본 범위는 0~1이며, 1 초과는 명확한 근거가 있을 때만 제안한다. Base Case에 존재하는 LNG Plant Train만 수정하고, Country/LNG Plant/Life Cycle Category/Nameplate Capacity는 해당 Train에 종속된 식별 속성으로 맞춘다.
```

`semantic_axes`

```text
slot=Country(국가명; 예: Algeria, Angola), LNG Plant(예: Arzew GL1Z, Angola LNG), LNG Plant Train(348개 basecase Train 중 선택; 예: Arzew GL1Z T1-T6, Angola LNG T1, Gorgon LNG T1, North West Shelf LNG T1, Sabine Pass LNG Stage 5 Expansion T1), Life Cycle Category(예: Operational), Nameplate Capacity MTPA(숫자; 예: 7.9, 5.2), Year(YYYY), Month(1~12), Period(숫자); value=Utilization Rate, 0~1 소수형 월별 가동률
```

### `tmm_mi_model_param_dimension_map`

`model_param_dimension_map_id=6`, `event_type_l2_id=1`, `dimension_key=alt_gas_supply_availability`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
대체 공급이 LNG 전환으로 설명되는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. alt_gas_supply_availability는 상향 조정 가능한 물량과 배분 강도의 근거로 사용하고, period/onset_pattern/recovery_pattern은 적용 월과 시계열 형태에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.
```

`model_param_dimension_map_id=5`, `event_type_l2_id=1`, `dimension_key=alt_gas_supply_availability`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=1`, `event_type_l2_id=1`, `dimension_key=period`, `mapping_method=indirect`

`comment`

```text
LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.
```

`model_param_dimension_map_id=3`, `event_type_l2_id=1`, `dimension_key=onset_pattern`, `mapping_method=indirect`

`comment`

```text
가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.
```

`model_param_dimension_map_id=4`, `event_type_l2_id=1`, `dimension_key=recovery_pattern`, `mapping_method=indirect`

`comment`

```text
가동률이 basecase 수준으로 회복되는 시점과 월별 회복 경로 판단에 사용한다.
```

`model_param_dimension_map_id=8`, `event_type_l2_id=2`, `dimension_key=utilization_change_amount`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
차질 또는 회복 대상 LNG Plant Train의 가동률 최종값을 산정한다. utilization_change_amount는 basecase 대비 가동률 하향·상향 조정폭의 주된 근거로 사용하고, period/onset_pattern/recovery_pattern은 적용 월과 월별 변화 경로에 반영한다. 단기·부분 차질은 생산량 직접 입력보다 Train 가동률 조정을 우선한다.
```

`model_param_dimension_map_id=12`, `event_type_l2_id=2`, `dimension_key=alt_lng_supply_availability`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
차질로 감소한 LNG 공급을 대체 가능한 다른 공급국/Plant Train의 가동률 상향으로 일부 상쇄한다. alt_lng_supply_availability는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다.
```

`model_param_dimension_map_id=9`, `event_type_l2_id=2`, `dimension_key=utilization_change_amount`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=7`, `event_type_l2_id=2`, `dimension_key=period`, `mapping_method=indirect`

`comment`

```text
LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.
```

`model_param_dimension_map_id=10`, `event_type_l2_id=2`, `dimension_key=onset_pattern`, `mapping_method=indirect`

`comment`

```text
가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.
```

`model_param_dimension_map_id=11`, `event_type_l2_id=2`, `dimension_key=recovery_pattern`, `mapping_method=indirect`

`comment`

```text
가동률이 basecase 수준으로 회복되는 시점과 월별 회복 경로 판단에 사용한다.
```

`model_param_dimension_map_id=24`, `event_type_l2_id=4`, `dimension_key=alt_supply_availability`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
파이프라인 공급 차질을 LNG 전환으로 대체하는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. alt_supply_availability는 LNG 전환 가능 물량과 배분 강도의 근거로 사용하고, period/onset_pattern/recovery_pattern/structural_change_yn은 적용 월과 지속성 판단에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.
```

`model_param_dimension_map_id=18`, `event_type_l2_id=4`, `dimension_key=utilization_change_amount`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=19`, `event_type_l2_id=4`, `dimension_key=utilization_change_amount`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=23`, `event_type_l2_id=4`, `dimension_key=alt_supply_availability`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=17`, `event_type_l2_id=4`, `dimension_key=period`, `mapping_method=indirect`

`comment`

```text
LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.
```

`model_param_dimension_map_id=20`, `event_type_l2_id=4`, `dimension_key=structural_change_yn`, `mapping_method=indirect`

`comment`

```text
가동률 조정이 한시적인지 구조적·장기적으로 지속되는지 판단에 사용한다.
```

`model_param_dimension_map_id=21`, `event_type_l2_id=4`, `dimension_key=onset_pattern`, `mapping_method=indirect`

`comment`

```text
가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.
```

`model_param_dimension_map_id=22`, `event_type_l2_id=4`, `dimension_key=recovery_pattern`, `mapping_method=indirect`

`comment`

```text
가동률이 basecase 수준으로 회복되는 시점과 월별 회복 경로 판단에 사용한다.
```

`model_param_dimension_map_id=67`, `event_type_l2_id=11`, `dimension_key=affected_facility_type`, `mapping_method=routing`, `parameter=LiqUtilAdjustment`

`comment`

```text
자연재해가 수출(액화) 시설의 단기·부분 가동 차질을 유발하는 경우 LiqUtilAdjustment를 선택한다. 선택된 경우 설비 용량 자체가 아니라 정전·침수·정비·운영 제약 등으로 기존 LNG Plant Train의 이용률이 낮아지는 상황을 해당 Train/Year/Month의 가동률 하향 조정으로 반영한다. affected_facility_type은 대상 시설이 액화 Plant/Train인지 판단하는 근거로 사용한다.
```

`model_param_dimension_map_id=73`, `event_type_l2_id=11`, `dimension_key=alt_lng_supply_availability`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
자연재해로 감소한 LNG 공급을 대체 가능한 다른 공급국/Plant Train의 가동률 상향으로 일부 상쇄한다. alt_lng_supply_availability는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다.
```

`model_param_dimension_map_id=66`, `event_type_l2_id=11`, `dimension_key=affected_facility_type`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=68`, `event_type_l2_id=11`, `dimension_key=affected_facility_type`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=69`, `event_type_l2_id=11`, `dimension_key=affected_facility_type`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=70`, `event_type_l2_id=11`, `dimension_key=affected_facility_type`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=95`, `event_type_l2_id=17`, `dimension_key=supply_disruption_intensity`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
지정학적 긴장·전쟁으로 영향권 액화시설의 단기·부분 가동 제약이 발생하는 경우, 기존 LNG Plant Train의 가동률을 하향 조정한다. supply_disruption_intensity는 하향 조정폭의 주된 근거로 사용하고, period/supply_disruption_pattern은 적용 월과 월별 변화 경로에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.
```

`model_param_dimension_map_id=99`, `event_type_l2_id=17`, `dimension_key=demand_response_alternative_lng`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
수요측이 타 공급원 경유 LNG를 확보하는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. demand_response_alternative_lng는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다.
```

`model_param_dimension_map_id=93`, `event_type_l2_id=17`, `dimension_key=period`, `mapping_method=indirect`

`comment`

```text
LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.
```

`model_param_dimension_map_id=98`, `event_type_l2_id=17`, `dimension_key=supply_disruption_pattern`, `mapping_method=indirect`

`comment`

```text
가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.
```

`model_param_dimension_map_id=94`, `event_type_l2_id=17`, `dimension_key=transport_disruption`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=96`, `event_type_l2_id=17`, `dimension_key=supply_disruption_intensity`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=97`, `event_type_l2_id=17`, `dimension_key=supply_disruption_intensity`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=102`, `event_type_l2_id=17`, `dimension_key=trade_restriction`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=105`, `event_type_l2_id=18`, `dimension_key=supply_disruption_intensity`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
경제 제재·무역 제한으로 영향권 액화시설의 단기·부분 가동 제약이 발생하는 경우, 기존 LNG Plant Train의 가동률을 하향 조정한다. supply_disruption_intensity는 하향 조정폭의 주된 근거로 사용하고, period/supply_disruption_pattern은 적용 월과 월별 변화 경로에 반영한다. Train별 가동률은 0~1 범위와 기존 basecase 수준을 고려해 산정한다.
```

`model_param_dimension_map_id=109`, `event_type_l2_id=18`, `dimension_key=demand_response_alternative_lng`, `mapping_method=direct`, `parameter=LiqUtilAdjustment`

`comment`

```text
수요측이 타 공급원 경유 LNG를 확보하는 경우, 대체 가능한 공급국의 기존 LNG Plant Train 가동률을 상향 조정한다. demand_response_alternative_lng는 대체 가능 물량과 배분 강도의 근거로 사용하고, 기존 basecase 가동률이 높은 Train에는 추가 상향을 제한한다. 제재·무역 제한에서는 대체 공급 형성에 일부 지연이 있을 수 있음을 월별 배분 시 보조적으로 고려한다.
```

`model_param_dimension_map_id=103`, `event_type_l2_id=18`, `dimension_key=period`, `mapping_method=indirect`

`comment`

```text
LiqUtilAdjustment의 Year/Month 적용 기간 판단에 사용한다.
```

`model_param_dimension_map_id=108`, `event_type_l2_id=18`, `dimension_key=supply_disruption_pattern`, `mapping_method=indirect`

`comment`

```text
가동률 변화가 급격히 반영되는지 점진적으로 반영되는지 월별 시계열 형태 판단에 사용한다.
```

`model_param_dimension_map_id=104`, `event_type_l2_id=18`, `dimension_key=transport_disruption`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=106`, `event_type_l2_id=18`, `dimension_key=supply_disruption_intensity`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=107`, `event_type_l2_id=18`, `dimension_key=supply_disruption_intensity`, `mapping_method=na`

`comment`

```text
NULL
```

`model_param_dimension_map_id=112`, `event_type_l2_id=18`, `dimension_key=trade_restriction`, `mapping_method=na`

`comment`

```text
NULL
```

## Event Type 21 Common

### `tmm_mi_model_param_dimension_map`

`model_param_dimension_map_id=125`, `event_type_l2_id=21`, `dimension_key=period`, `mapping_method=indirect`

`comment`

```text
파라미터의 시간축으로 사용될 수 있다(PMI:Year/Month, GDP:Year)
```

`model_param_dimension_map_id=128`, `event_type_l2_id=21`, `dimension_key=demand_impact`, `mapping_method=na`

`comment`

```text
NULL
```
