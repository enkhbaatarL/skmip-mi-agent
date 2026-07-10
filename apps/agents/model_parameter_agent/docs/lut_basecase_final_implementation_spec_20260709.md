# LUT/Basecase 통합 Slot/Value 최종 구현 명세

작성일: 2026-07-09

## 1. 목적

`model_parameter_agent`의 Step2 slot 선택과 Step3 value 산정에서 기존 basecase 엑셀만 사용하던 방식을 확장해,
LUT CSV를 default 전체 기준값으로 함께 사용한다.

이 문서는 아래 내용을 모두 포함한 단일 개발 기준 문서다.

- basecase와 LUT의 slot/value coverage 비교
- basecase 기준 동일 slot을 LUT에서 lookup한 매핑 검증 결과
- 파라미터별 value 변환식과 lookup key
- LiqUtilAdjustment의 `Nameplate Capacity` 단위/컬럼 처리 기준
- Step2/Step3 flow 변경 설계
- 성능, LLM latency, CSV cache, side effect 방어 정책
- 구현 순서와 테스트 기준

## 2. 핵심 결론

전제:

- LUT는 모델의 default 전체 기준값이다.
- basecase는 사용자가 일부 좌표를 override한 값이다.
- 같은 slot에 basecase와 LUT가 모두 있으면 basecase가 우선한다.

최종 정책:

```text
Step2 slot 후보 = LUT slot universe ∪ basecase-only slot

Step3 기준값 = basecase override if exists
             else LUT default if exists
             else warning / value 기준값 없음
```

중요한 구현 원칙:

- Step2에는 LUT 전체 value row를 넣지 않는다. compact slot hierarchy만 준다.
- Step3에는 Step2에서 선택된 slot에 매칭되는 effective reference record만 준다.
- CSV는 요청마다 읽지 않는다. process-level read-only cache와 normalized lookup index를 사용한다.
- LiqUtilAdjustment의 `Nameplate Capacity`는 LUT의 `LNG train capacity (Million tonnes LNG per month) * 12`로 만든 MTPA 값을 사용한다.
- `LNG train nameplate capacity (Bcm per month)`는 단위가 다르므로 slot의 `Nameplate Capacity`에 사용하지 않는다.

## 3. 원본 데이터 경로

Basecase 기준:

- `apps/agents/model_parameter_agent/docs/basecase_load_values_full_20260630.csv`
- 이 파일은 기존 extractor가 `resources/basecase/*.xlsm`에서 읽은 결과와 같은 record 구조다.
- 주요 필드:
  - `parameter`
  - `axes_json`
  - `value`
  - `reference_id`
  - `model_file`
  - `model_sheet`

LUT 기준:

| 파라미터 | LUT 파일 |
|---|---|
| GDP | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_LUT_General_value_based_t6.csv` |
| GDP | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_LUT_BCInput_value_based_t2.csv` |
| PMI | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_Input_PMIInput_value_based_t1.csv` |
| PMI | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_Input_PMIInput_value_based_t2.csv` |
| PowerMix | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_LUT_General_value_based_t6.csv` |
| PowerMix | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_LUT_BCInput_value_based_t3.csv` |
| Temperature | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_LUT_General_value_based_t6.csv` |
| Temperature | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_Input_WeatherInput_value_based_t1.csv` |
| Temperature | `apps/agents/model_parameter_agent/resources/lut/Demand_Model_Input_WeatherInput_value_based_t2.csv` |
| LiqUtilAdjustment | `apps/agents/model_parameter_agent/resources/lut/BCLiquefaction.csv` |

## 4. 현재 코드 영향 지점

현재 propose flow:

```text
load_basecase_samples
-> propose_parameter_slots
-> filter_basecase_records_by_slots
-> propose_parameter_values
```

관련 코드:

- `apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py`
  - `load_basecase_samples()`
  - `propose_parameter_slots()`
  - `filter_basecase_records_by_slots()`
  - `propose_parameter_values()`
  - `_build_basecase_slot_options()`
  - `_build_basecase_value_groups()`
  - `_filter_records_by_selected_slots()`
  - `_patch_basecase_value()`
- `apps/agents/model_parameter_agent/utils/parameter_mapping.py`
  - `build_basecase_records()`
  - `basecase_slot_axis_names_from_candidate()`
  - `basecase_value_field_name_from_candidate()`

현재 문제:

- Step2 slot options가 basecase record에서만 생성된다.
- Step3 value groups도 선택된 basecase record에서만 생성된다.
- basecase에 없는 LUT-only slot은 LLM에게 충분히 제공되지 않는다.

변경 방향:

- `basecase_records`를 단순히 늘리지 않는다.
- `lut_records`와 `basecase_records`를 원천별로 분리한다.
- 동일 좌표를 merge해 `effective_reference_records`를 만든다.

## 5. 전체 데이터 비교 요약

| 파라미터 | basecase slot/value | LUT slot/value | basecase 기준 LUT lookup | 값 차이 |
|---|---:|---:|---:|---:|
| GDP | 93개, 12개국, 2024~2031 | raw GDP 2,365개/169개국, 성장률 2,118개/163개국, 2019~2031 | 93/93, 100.00% | 85개 다름 |
| PMI | 48개, 2개국, 4개 연도, 12개월 | 8,064개, 84개 reference country, 2024~2031, 12개월 | 48/48, 100.00% | 48개 다름 |
| PowerMix | 57개, 11개국, Gas만, 2025~2030 | 8,399개, 84개국, 10개 energy source, 2022~2031 | 57/57, 100.00% | 57개 다름 |
| Temperature | 150개, 10개국, 2026~2030, 1~3월 | 8,064개, 84개국, 2024~2031, 12개월 | 150/150, 100.00% | 150개 다름 |
| LiqUtilAdjustment | 21,656개, 24개국, 311 train, 2023~2031 | 41,103개, 24개국, 350 train, 2017~2031 + 2050 일부 | 21,569/21,656, 99.60% | 20,230개 다름 |

해석:

- GDP/PMI/PowerMix/Temperature는 basecase 기준 동일 slot lookup이 모두 성공한다.
- LiqUtilAdjustment는 business key 기준 대부분 매핑되며, 미매핑 87개는 basecase-only slot으로 유지해야 한다.
- 매핑된 row 대부분은 basecase와 LUT 값이 다르다.
- 따라서 값 기준은 반드시 `basecase override > LUT default` 우선순위로 처리해야 한다.

## 6. 파라미터별 상세 명세

### 6.1 GDP

Basecase:

- 축: `Country`, `Year`
- record: 93개
- 국가: 12개
- 연도: 2024~2031
- 값: 전년 대비 GDP 성장률
- 값 범위: `-0.001`~`0.065`

LUT:

- `Demand_Model_LUT_General_value_based_t6.csv`
  - `Full Country List_Country`: 91개국
- `Demand_Model_LUT_BCInput_value_based_t2.csv`
  - raw GDP absolute value: 2,365개 row
  - 국가: 169개
  - 연도: 2018~2031
  - 성장률 산정 가능 국가: 163개
  - 성장률 record: 2,118개
  - 성장률 연도: 2019~2031

성장률 산정 제외 국가:

- `Falkland Islands`
- `Martinique`
- `Neutral Zone`
- `Nigeria/Sao Tome JDZ`
- `Saint Pierre and Miquelon`
- `Western Sahara`

이 6개는 GDP가 전 기간 0이라 성장률을 만들 수 없다.

변환식:

```python
gdp_growth_rate = GDP_abs_t / GDP_abs_t_minus_1 - 1
```

주의:

- 전년도 GDP가 0이면 성장률을 만들지 않는다.
- 2018년은 전년도 값이 없으므로 value 후보에서 제외한다.
- `basecaseValue`에는 절대 GDP가 아니라 전년 대비 성장률을 넣는다.

Lookup key:

```text
Country + Year
```

Slot 정책:

- slot country universe는 `Full Country List_Country` 91개를 사용한다.
- value default는 GDP absolute value 파일에서 성장률로 변환 가능한 국가/연도만 사용한다.
- `Other Africa`, `Other America N`, `Other America S`, `Other Asia`, `Other Australia`, `Other Europe`, `Other Middle East`는 Full Country List에는 있지만 GDP value가 없다.
- 값이 없는 `Other ...` 국가는 별도 mapping 없이는 selected slot으로 확정하지 않거나 warning 처리한다.

Value 정책:

```text
if basecase[Country, Year] exists:
    effective_value = basecase growth rate
elif lut_growth[Country, Year] exists:
    effective_value = lut growth rate
else:
    no baseline value
```

Sanity 정책:

- 전체 GDP LUT 성장률 범위는 소국/위기국 영향으로 넓다.
- 모델 대상국과 2024~2031 구간으로 제한한 LUT 성장률 범위는 약 `-0.0547`~`0.1322`다.
- 제안값 검증은 가능한 경우 이 target 범위를 우선 참고하고, 극단값은 rationale 근거를 요구한다.

매핑 검증:

- basecase 93개 중 LUT lookup 성공 93개
- mapping rate: 100.00%
- same value: 8개
- different value: 85개
- max abs diff: `0.06914`

### 6.2 PMI

Basecase:

- 축: `Country`, `Year`, `Month`
- record: 48개
- 국가: `China`, `Philippines`
- 연도:
  - China: 2025, 2026
  - Philippines: 2029, 2030
- 월: 1~12
- 값 범위: `49.0`~`54.0`

LUT:

- `Demand_Model_Input_PMIInput_value_based_t1.csv`
  - demand location country: 91개
  - reference country: 84개
- `Demand_Model_Input_PMIInput_value_based_t2.csv`
  - reference country 기준 PMI value
  - wide year columns: `2024.0`~`2031.0`
  - long 변환 후 record: 8,064개 = 84개국 * 8개년 * 12개월
  - 값: 전부 `50.0`

`50.0` 해석:

- 실측 신호라기보다 조정 없음 기준선에 가까운 중립 default다.
- Step3 prompt에는 `lut_value=50`을 "중립 기준선"으로 명시한다.

PMI reference mapping:

| Demand Location Country | Reference Country |
|---|---|
| Other Africa | Iran |
| Other America N | United States |
| Other America S | Brazil |
| Other Asia | Japan |
| Other Australia | Australia |
| Other Europe | Portugal |
| Other Middle East | Qatar |

Lookup key:

```text
Country + Year + Month
```

단, Country가 PMI value table에 없으면 t1의 Reference Country로 변환해 lookup한다.

Slot 정책:

- slot country universe는 PMI t1의 demand location country 91개를 사용한다.
- 출력 좌표의 `Country`는 demand location country를 유지한다.
- 내부 default value lookup만 reference country 기준으로 수행한다.

Value 정책:

```text
if basecase[demand_country, Year, Month] exists:
    effective_value = basecase PMI
elif lut_pmi[reference_country, Year, Month] exists:
    effective_value = 50.0
else:
    no baseline value
```

Sanity 정책:

- LUT default `50.0`은 중립 baseline이다.
- PMI 지수 일반 범위로 `30`~`70`을 hard sanity 후보로 둔다.
- 이벤트 충격에 따른 조정 폭은 basecase override 분포와 scenario 강도를 함께 참고한다.

매핑 검증:

- basecase 48개 중 LUT lookup 성공 48개
- mapping rate: 100.00%
- same value: 0개
- different value: 48개
- max abs diff: `4`

### 6.3 PowerMix

Basecase:

- 축: `Country`, `Year`, `Energy Source`
- record: 57개
- 국가: 11개
- 연도: 2025~2030
- Energy Source: `Gas` 1개
- 값 범위: `0.031`~`0.495`

LUT:

- `Demand_Model_LUT_General_value_based_t6.csv`
  - `Full Country List_Country`: 91개국
- `Demand_Model_LUT_BCInput_value_based_t3.csv`
  - value table 국가: 84개
  - record: 8,399개
  - 연도: 2022~2031
  - Energy Source 10종:
    - `Bioenergy`
    - `Coal`
    - `Gas`
    - `Geothermal`
    - `Hydro`
    - `Liquids`
    - `Nuclear`
    - `Other`
    - `Solar`
    - `Wind`
  - 값 범위: `0.0`~`1.0`
  - 국가/연도별 10개 energy source 합계는 모두 1.0

Lookup key:

```text
Country + Year + Energy Source
```

Slot 정책:

- slot country universe는 `Full Country List_Country` 91개를 사용한다.
- value default는 Power Generation table에 있는 84개국만 존재한다.
- Energy Source universe는 LUT의 10개 source를 사용한다.
- basecase에 Gas만 있다고 해서 Energy Source 후보를 Gas로 제한하지 않는다.

Value 정책:

```text
if basecase[Country, Year, Energy Source] exists:
    effective_value = basecase power mix
elif lut_power_mix[Country, Year, Energy Source] exists:
    effective_value = lut power mix
else:
    no baseline value
```

Step3 prompt 정책:

- 선택된 Energy Source만 제공하지 말고 해당 Country/Year의 전체 energy source mix를 함께 제공한다.
- 일부 source만 조정하면 합계 1.0이 깨질 수 있으므로, 검증 또는 rationale 규칙이 필요하다.

매핑 검증:

- basecase 57개 중 LUT lookup 성공 57개
- mapping rate: 100.00%
- same value: 0개
- different value: 57개
- max abs diff: `0.208436`

### 6.4 Temperature

Basecase:

- 축: `Country`, `Year`, `Month`
- record: 150개
- 국가: 10개
- 연도: 2026~2030
- 월: 1~3월
- 값 범위: `-2.2`~`11.3`

LUT:

- `Demand_Model_LUT_General_value_based_t6.csv`
  - `Full Country List_Country`: 91개국
- `Demand_Model_Input_WeatherInput_value_based_t1.csv`
  - Base Case HDD Input
- `Demand_Model_Input_WeatherInput_value_based_t2.csv`
  - Base Case CDD Input
- Weather value table 국가: 84개
- long 변환 후 temperature record: 8,064개 = 84개국 * 8개년 * 12개월
- 연도: 2024~2031
- 월: 1~12
- 파생 기온 범위: `-15.3507`~`38.1314`

Temperature 변환식:

```python
if HDD > 0:
    temperature = 18 - HDD / 30
elif CDD > 0:
    temperature = 18 + CDD / 30
else:
    temperature = 18
```

검증:

- HDD 사용 branch: 3,848개
- CDD 사용 branch: 4,216개
- HDD/CDD 모두 0이라 18도로 둔 좌표: 0개
- HDD와 CDD가 동시에 양수인 좌표: 0개

Lookup key:

```text
Country + Year + Month
```

Slot 정책:

- slot country universe는 `Full Country List_Country` 91개를 사용한다.
- value default는 Weather table에 있는 84개국만 존재한다.
- basecase에 1~3월만 있다고 해서 월 후보를 1~3월로 제한하지 않는다.
- 폭염/여름 이벤트에는 LUT 월별 baseline이 필수다.

Value 정책:

```text
if basecase[Country, Year, Month] exists:
    effective_value = basecase temperature
elif lut_temperature[Country, Year, Month] exists:
    effective_value = derived LUT temperature
else:
    no baseline value
```

Sanity 정책:

- 전역 최소/최대보다 국가·월별 LUT baseline 대비 delta 기준으로 잡는 편이 안전하다.

매핑 검증:

- basecase 150개 중 LUT lookup 성공 150개
- mapping rate: 100.00%
- same value: 0개
- different value: 150개
- max abs diff: `3.687375`

### 6.5 LiqUtilAdjustment

Basecase:

- 축:
  - `Country`
  - `LNG Plant`
  - `LNG Plant Train`
  - `Life Cycle Category`
  - `Nameplate Capacity`
  - `Year`
  - `Month`
  - `Period`
- record: 21,656개
- 국가: 24개
- LNG Plant: 78개
- LNG Plant Train: 311개
- Life Cycle Category: 5개
- 연도: 2023~2031
- Period: 70~168
- 값 범위: `0.0`~`3.3077`
- `value > 1.0`인 record: 7,367개

LUT:

- 파일: `BCLiquefaction.csv`
- record: 41,103개
- 국가: 24개
- LNG Plant: 90개
- LNG Plant Train: 350개
- Life Cycle Category: 5개
- 연도: 2017~2031, 2050년 1월 terminal row 일부
- Period: 0~169
- 값 범위: `0.0`~`3.3004`
- `value > 1.0`인 record: 6,232개

LUT 컬럼 매핑:

| basecase axis/value | LUT source column | 처리 |
|---|---|---|
| `Country` | `Country` | 그대로 |
| `LNG Plant` | `Plant Name` | 컬럼명 변환 |
| `LNG Plant Train` | `Plant Train` | 컬럼명 변환 |
| `Life Cycle Category` | `Infra Life Cycle` | metadata |
| `Nameplate Capacity` | `LNG train capacity (Million tonnes LNG per month) * 12` | MTPA로 환산 |
| `Year` | `Year` | 그대로 |
| `Month` | `Month` | 그대로 |
| `Period` | `Period` | sanity check |
| `LiqUtilAdjustment` value | `LNG plant utilisation %` | train row 단위 값 |

Nameplate Capacity 중요 규칙:

```python
nameplate_capacity_mtpa = (
    LNG_train_capacity_million_tonnes_lng_per_month * 12
)
```

사용하면 안 되는 컬럼:

```text
LNG train nameplate capacity (Bcm per month)
```

이 컬럼은 Bcm/month 단위라 basecase slot의 `Nameplate Capacity`와 크기가 다르게 보인다. LUT-only slot을 basecase 형태로 만들 때도 이 컬럼을 사용하지 않는다.

Lookup key:

```text
Country + LNG Plant + LNG Plant Train + Year + Month
```

Period:

- 현재 데이터에서 `Country + Plant + Train + Year + Month`가 같은 common row의 Period mismatch는 0개다.
- 따라서 Period는 함께 검증하되 canonical lookup key는 Year/Month 기준으로 둔다.
- 향후 LUT 갱신으로 Period 기준이 달라지면 mismatch warning을 남긴다.

Life Cycle Category / Nameplate Capacity:

- lookup key가 아니다.
- output metadata 및 sanity check 용도다.
- basecase override가 있으면 basecase metadata를 우선한다.
- LUT-only slot이면 LUT metadata를 사용한다.
- basecase metadata와 LUT metadata가 다르면 매핑 실패가 아니라 mismatch warning이다.

Value granularity:

- `LNG plant utilisation %`라는 컬럼명과 달리 값은 train row 단위로 존재한다.
- 같은 plant/year/month 안에서도 train별 값이 다른 경우가 있으므로 plant 평균으로 뭉치지 않는다.

Slot 정책:

- LUT의 `Closed` lifecycle train은 기본 slot 후보에서 제외한다.
- basecase에만 있는 `Speculative` slot은 override-only 후보로 유지한다.
- LUT-only slot을 basecase 형태로 만들 때는:
  - `Country`: LUT `Country`
  - `LNG Plant`: LUT `Plant Name`
  - `LNG Plant Train`: LUT `Plant Train`
  - `Life Cycle Category`: LUT `Infra Life Cycle`
  - `Nameplate Capacity`: LUT `LNG train capacity (Million tonnes LNG per month) * 12`
  - `Year`, `Month`, `Period`: LUT 값

Value 정책:

```text
if basecase[Country, Plant, Train, Year, Month] exists:
    effective_value = basecase LiqUtilAdjustment
    metadata = basecase metadata
elif lut[Country, Plant, Train, Year, Month] exists:
    effective_value = LUT utilisation
    metadata = LUT metadata converted to basecase shape
else:
    no baseline value
```

매핑 검증:

- basecase 21,656개 중 LUT lookup 성공 21,569개
- mapping rate: 99.60%
- same value: 1,339개
- different value: 20,230개
- unmapped: 87개
- max abs diff: `2.333672`
- Period mismatch: 0개
- lifecycle mismatch: 4,496개
- capacity mismatch: 1,170개

Train-level capacity 검증:

- basecase 311개 train은 모두 LUT train과 이름 기준으로 매칭된다.
- `Nameplate Capacity`가 LUT `MTPM * 12`와 정확히 일치하는 train: 297개
- capacity가 다른 train: 14개
  - `Damietta LNG T1`
  - `GLNG T1`, `GLNG T2`
  - `PNG LNG T1`, `PNG LNG T2`
  - `Golden Pass LNG T1`, `Golden Pass LNG T2`, `Golden Pass LNG T3`
  - `QatarGas LNG T8`~`T13`
- 이 mismatch는 lookup 실패가 아니라 basecase가 별도 공칭 명판용량을 관리하는 metadata 차이로 본다.
- LUT `MTPM * 12`는 350개 train 중 348개에서 전 기간 단일 값이다.
- 복수 capacity 값이 있는 LUT train은 `Damietta LNG T1`, `Oman LNG T3 (Qalhat)` 2개다.
  - LUT-only slot에서 복수 값이 나오면 horizon 내 최신값을 사용하고 warning을 남긴다.

Unmapped basecase-only slot:

| Country | LNG Plant | LNG Plant Train | Count |
|---|---|---:|
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 36 |
| Argentina | Pan American LNG | Pan American LNG | 27 |
| Mozambique | Coral North FLNG | Coral North FLNG | 24 |

처리:

- 위 87개는 LUT lookup 실패지만 basecase override로는 유효하다.
- effective reference에는 `basecase_only`로 포함한다.
- Step2 slot option에도 포함하되, `source_summary` 또는 metadata로 basecase-only임을 표시한다.

## 7. 내부 데이터 모델

### 7.1 LutRecord

```python
{
    "candidate_key": "...",
    "parameter_name": "GDP",
    "source": "lut",
    "reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:123",
    "axes": {"Country": "China", "Year": 2026},
    "value_name": "GDP",
    "value": 0.042,
    "metadata": {
        "raw_value": 123.45,
        "transform": "pct_change_from_absolute_gdp",
        "lookup_country": "China",
        "source_file": "Demand_Model_LUT_BCInput_value_based_t2.csv"
    }
}
```

### 7.2 EffectiveReferenceRecord

```python
{
    "candidate_key": "...",
    "parameter_name": "GDP",
    "axes": {"Country": "China", "Year": 2026},
    "value_name": "GDP",
    "effective_value": 0.042,
    "effective_source": "basecase",
    "basecase_value": 0.042,
    "lut_value": 0.039,
    "basecase_reference_id": "Demand:GDPPopulationAdjustment:R21C6",
    "lut_reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2.csv:row:...",
    "metadata": {
        "status": "overridden",
        "warnings": []
    }
}
```

`effective_source` 값:

- `basecase`
- `lut`
- `basecase_only`

Merge 우선순위:

1. 같은 normalized coordinate에 basecase가 있으면 basecase override 사용
2. basecase가 없고 LUT가 있으면 LUT default 사용
3. basecase만 있고 LUT가 없으면 basecase-only override로 포함
4. 둘 다 없으면 slot/value 후보에서 제외하거나 warning 처리

## 8. LutRepository 설계

LUT loader는 파라미터별 CSV 처리 로직을 flow/node에 직접 넣지 말고 read-only repository로 분리한다.

권장 파일:

```text
apps/agents/model_parameter_agent/utils/lut.py
```

또는 규모가 커지면:

```text
apps/agents/model_parameter_agent/utils/lut_repository.py
```

Interface:

```python
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LutTableSpec:
    file_name: str
    axis_columns: dict[str, str]
    value_column: str | None
    year_metric_prefix: str | None
    derive: str | None
    slot_filter: str | None


class LutRepository:
    def slots(self, parameter_name: str) -> list[dict[str, Any]]:
        \"\"\"Value를 제외한 유효 slot 축 조합 전집을 반환한다.\"\"\"

    def records(
        self,
        parameter_name: str,
        *,
        axes_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        \"\"\"basecase record와 같은 형태의 LUT default value record를 반환한다.\"\"\"
```

Parameter별 책임:

- GDP
  - absolute GDP long table을 growth rate로 파생
  - `Full Country List` 교집합을 slot 후보로 사용
  - all-zero GDP 국가는 growth record에서 제외
- PMI
  - t1 demand country/reference country mapping 처리
  - t2 wide year metric melt
  - default value 50.0을 neutral baseline으로 표시
- PowerMix
  - Country/Year/Energy Source long table 사용
  - country/year별 source 합계 1.0 검증 정보를 만든다
- Temperature
  - HDD/CDD wide table melt
  - temperature 파생
  - HDD/CDD 동시 양수 여부 검증
- LiqUtilAdjustment
  - `Closed` train 제외
  - MTPM -> MTPA capacity 변환
  - train 단위 utilization record 생성

Reference ID:

```text
lut:{file_name}:{row_or_cell}
```

basecase의 `{model_file}:{sheet}:R{row}C{col}`와 충돌하지 않게 prefix를 둔다.

## 9. Flow 변경 설계

### 9.1 State 확장

현재:

```python
basecase_records: list[dict[str, Any]]
```

추가:

```python
lut_records: list[dict[str, Any]]  # request-local filtered/compact records only
effective_reference_records: list[dict[str, Any]]
```

기존 `basecase_records`는 backward compatibility를 위해 유지한다.
full LUT DataFrame 또는 전체 41k row는 state에 넣지 않고 `LutRepository`의 process-level cache에만 둔다.

### 9.2 Node 변경

현재:

```text
load_basecase_samples
-> propose_parameter_slots
-> filter_basecase_records_by_slots
-> propose_parameter_values
```

권장 의미:

```text
load_reference_records
-> propose_parameter_slots
-> filter_reference_records_by_slots
-> propose_parameter_values
```

실제 함수명은 당장 유지해도 된다. 단 내부 책임은 바꾼다.

`load_basecase_samples()` 내부:

1. 기존 `build_basecase_records()` 호출
2. `LutRepository.records()` 또는 parameter별 slot universe 로드
3. basecase와 LUT를 merge해 effective reference 생성
4. state에 `basecase_records`, 필터된 `lut_records`, `effective_reference_records` 저장
5. full LUT 원본과 lookup index는 state에 저장하지 않음

### 9.3 Step2 Slot 선택 packet

Step2에는 value row 전체를 주지 않고 compact slot option을 준다.

예시:

```json
{
  "slot_options": {
    "axis_names": ["Country", "Year", "Energy Source"],
    "axis_values": {"Year": [2024, 2025, 2026]},
    "slot_hierarchy_axes": ["Country", "Energy Source"],
    "slot_hierarchy": [["Belgium", ["Gas", "Coal", "Solar"]]],
    "slot_hierarchy_metadata": [
      {"path": ["Belgium", "Gas"], "overridden_in_basecase": true}
    ],
    "source_summary": {
      "lut_slot_count": 8399,
      "basecase_override_count": 57,
      "basecase_only_count": 0
    }
  }
}
```

Step2 기준:

- hierarchy는 LUT와 basecase의 union으로 만든다.
- 같은 path가 양쪽에 있으면 `overridden_in_basecase=true` 표시한다.
- basecase에만 있는 path도 포함한다.
- Cartesian product를 만들지 않고 실제 존재하는 row/path만 사용한다.
- slot validation은 basecase 기준이 아니라 `basecase ∪ lut` 기준으로 확장한다.

### 9.4 Step3 Value 산정 packet

Step3에는 선택 slot에 맞는 effective value group만 제공한다.

예시:

```json
{
  "reference_value_groups": [
    {
      "fixed_axes": {"Country": "China", "Energy Source": "Gas"},
      "variable_axis_names": ["Year"],
      "cells": [
        {
          "axes": {"Year": 2026},
          "effective_value": 0.0346,
          "effective_source": "basecase",
          "basecase_value": 0.0346,
          "lut_value": 0.0412,
          "basecase_reference_id": "Demand:...",
          "lut_reference_id": "lut:..."
        }
      ]
    }
  ]
}
```

LLM에 명시할 원칙:

- `effective_value`가 현재 기준값이다.
- `basecase_value`가 있으면 사용자가 override한 값이므로 `lut_value`보다 우선한다.
- `basecase_value`가 없으면 `lut_value`가 default 기준값이다.
- proposed value가 기준값과 같아도 근거가 있으면 그대로 제안할 수 있다.

### 9.5 Sanitizer 변경

현재:

- `_patch_basecase_value()`

변경:

- 이름은 유지해도 되지만 내부는 effective reference 기준으로 patch한다.
- 장기적으로는 `_patch_reference_value()`가 더 정확하다.

기준:

- LLM이 `basecase_reference_ids`를 반환하는 현재 계약은 유지할 수 있다.
- 단, `lut:` prefix reference id도 허용한다.
- API 출력의 `basecaseValue`는 effective value로 scalar화한다.
- rationale/warning에는 source를 구분한다.
  - `basecase_override`
  - `lut_default`
  - `basecase_only`

API schema는 당장 바꾸지 않는다.

## 10. 성능 및 운영 고려사항

### 10.1 Prompt 크기

가장 큰 위험은 LUT 전체 value row를 prompt에 넣는 것이다.

특히 LiqUtilAdjustment는 41,103개 row라 전수 입력하면 token 초과와 응답 지연이 발생할 가능성이 높다.

프롬프트 크기 추정:

| 항목 | 크기/범위 | 토큰 추정 |
|---|---:|---:|
| LiqUtil hierarchy, 경로만 | 약 349 train | 약 4k tokens |
| PowerMix hierarchy | 84개국 × 10 source | 약 2k tokens |
| Country list | 91개국 | 약 300 tokens |
| Step2 전체 증가분 | 파라미터 동시 후보 기준 | 약 5k~7k tokens |
| Step3 effective records | cap 100건 기준 | 약 6k tokens 내외 |

위 추정은 compact hierarchy를 쓴다는 전제다. full LUT value row를 넣으면 이 범위를 크게 초과한다.

권장 정책:

- Step2 slot 선택에는 value row를 넣지 않는다.
- Step2에는 compact `axis_values`, `slot_hierarchy`, `source_summary`만 넣는다.
- LiqUtilAdjustment는 전체 train list를 flat하게 펼치지 말고 `Country -> Plant -> Train` hierarchy로 압축한다.
- Step3 value 산정에는 Step2에서 선택된 slot에 매칭되는 effective reference record만 제공한다.
- 서버 측 deterministic pre-filter를 먼저 수행한다.
- 필터 후에도 후보가 너무 많으면 임의 sampling하지 말고 warning 또는 failure로 드러낸다.

피해야 할 방식:

- LUT 전체 CSV row를 그대로 prompt에 넣기
- 전체 국가 × 전체 월 × 전체 energy source Cartesian product 생성
- token 초과를 피하려고 근거 없이 random/sample row를 잘라 넣기

권장 설정:

```text
model_parameter_max_lut_slot_options
model_parameter_max_effective_reference_records
```

기존:

```text
model_parameter_max_value_prompt_basecase_records
```

와 같은 방어선을 LUT에도 둔다.

### 10.2 LLM 실행 시간

프롬프트가 커지면 LLM latency가 늘고, slot 후보가 많아지면 selected slot 수도 늘어날 수 있다.

현재 flow는 Step2/Step3 LLM 호출이 직렬이므로 한 단계가 커지면 전체 API 시간이 바로 증가한다.
compact hierarchy 기준으로는 호출 횟수는 그대로이고, 입력 증가에 따른 호출당 지연은 대략 +1~2초 수준으로 예상한다.
실제 지연의 주 리스크는 입력보다 selected slot 증가로 인한 출력 길이 증가다.

권장 정책:

- 후보 축소는 LLM 전에 서버에서 먼저 한다.
- 명시 국가/기간/plant가 있으면 해당 후보만 Step2에 제공한다.
- 명시 대상이 없으면 compact summary만 제공하고 전체 상세 hierarchy는 주지 않는다.
- Step2의 `maxParameterSlots`를 유지한다.
- LiqUtilAdjustment처럼 train 단위 후보가 많은 파라미터는 더 낮은 상한을 둘 수 있게 한다.
- Step3에는 numeric lookup 결과를 서버가 계산해서 넣는다.
- LLM에는 "값을 찾는 작업"이 아니라 "조정 여부와 폭 판단"만 맡긴다.

LLM call trace에 추가할 값:

- prompt size
- candidate count
- selected slot count
- effective record count
- LUT source summary

### 10.3 CSV 읽기와 메모리

CSV를 요청마다 읽고 wide table을 매번 melt하면 불필요하게 느려진다.

현재 로컬 측정:

| 파일/테이블 | Row/shape | 파일 크기 | pandas 메모리 |
|---|---:|---:|---:|
| `BCLiquefaction.csv` | 41,103 × 16 | 9.09 MB | 27.79 MB |
| PowerMix LUT | 8,399 × 8 | 0.64 MB | 1.94 MB |
| GDP LUT | 2,365 × 6 | 0.13 MB | 0.50 MB |
| PMI reference t1 | 91 × 5 | 0.004 MB | 0.03 MB |
| PMI wide t2 | 1,008 × 12 | 0.07 MB | 0.26 MB |
| Weather HDD wide | 1,008 × 12 | 0.11 MB | 0.26 MB |
| Weather CDD wide | 1,008 × 12 | 0.12 MB | 0.26 MB |
| General country list | 91 × 3 | 0.003 MB | 0.02 MB |

전체 CSV 파일 크기는 약 10.17 MB, pandas 로드 후 메모리는 약 31.06 MB, 현재 로컬 로드 시간은 약 0.14초였다.
파생 long table과 lookup index를 추가해도 process-level cache로 관리 가능한 규모다.

권장 정책:

- `LutRepository`는 process-level read-only cache로 둔다.
- 앱 시작 시 eager load하거나 첫 요청에서 lazy load한다.
- 운영에서는 파일이 immutable하다고 보고 요청 중 reload하지 않는다.
- 개발 편의를 위해서는 mtime/checksum 기반 reload 옵션만 별도로 둔다.
- CSV 원본 DataFrame과 normalized lookup index를 모두 request state에 넣지 않는다.
- state에는 선택된 후보에 필요한 record만 넣는다.
- lookup은 repository 내부 dict/index에서 수행한다.
- DataFrame은 read-only로 다루고 mutation이 필요한 경우 request-local copy를 만든다.

파라미터별 normalized key index:

| 파라미터 | Index key |
|---|---|
| GDP | `(Country, Year)` |
| PMI | `(Country, Year, Month)` + reference country mapping |
| PowerMix | `(Country, Year, Energy Source)` |
| Temperature | `(Country, Year, Month)` |
| LiqUtilAdjustment | `(Country, LNG Plant, LNG Plant Train, Year, Month)` |

Multi-worker 주의:

- cache는 worker 수만큼 복제된다.
- 현재 CSV 규모에서는 허용 가능해 보이나, worker 수 증가 시 memory 사용량을 로그로 확인한다.

### 10.4 Side Effect

LUT 도입은 단순 데이터 추가가 아니라 모델 behavior를 바꾼다.

방어해야 할 부작용:

1. slot 과다 제안
   - LUT universe가 커지면서 LLM이 관련 없는 국가/월/train까지 고를 수 있다.
   - scenario/event/dimension 기반 pre-filter와 `maxParameterSlots`가 필수다.

2. `basecaseValue` 의미 혼동
   - API 필드는 유지하더라도 내부적으로는 effective reference value가 된다.
   - rationale/warning에는 `basecase_override`, `lut_default`, `basecase_only`를 남긴다.

3. `Other ...` 국가
   - PMI는 reference country mapping이 있다.
   - GDP/PowerMix/Temperature는 default value가 없다.
   - 값이 없는 `Other ...`는 selected slot으로 확정하지 않거나 warning을 남긴다.

4. PowerMix 합계 정합성
   - 일부 source만 조정하면 country/year 합계 1.0이 깨질 수 있다.
   - value 검증 또는 rationale 규칙이 필요하다.

5. LiqUtil metadata 불일치
   - Nameplate Capacity와 lifecycle은 lookup key가 아니라 metadata/sanity check다.
   - capacity mismatch를 매핑 실패로 처리하면 정상 lookup이 과도하게 실패한다.

6. 결과 재현성
   - 후보가 많아져 LLM 판단 영역이 넓어진다.
   - 서버 pre-filter, deterministic sort, deterministic cap을 적용해 같은 입력의 prompt가 안정적으로 생성되게 한다.

7. 로그/DB 저장량 증가
   - full LUT record를 llm trace나 proposal DB에 저장하지 않는다.
   - source summary, selected effective records, warning만 저장한다.

## 11. 구현 순서

1. `utils/lut.py` 또는 `utils/lut_repository.py` 추가
   - 파라미터별 LUT loader/normalizer 구현
   - GDP 성장률 변환
   - Temperature HDD/CDD 변환
   - LiqUtil capacity MTPA 변환

2. `LutRepository` cache 구현
   - process-level read-only cache
   - normalized lookup index
   - optional mtime/checksum reload for dev only

3. effective reference merge 유틸 추가
   - normalized coordinate key 생성
   - basecase override 우선순위 적용
   - source summary 생성
     - `basecase_only`
     - `lut_only`
     - `overridden`

4. state 확장
   - `lut_records`
   - `effective_reference_records`
   - 기존 `basecase_records` 유지

5. Step2 packet 변경
   - `_build_basecase_slot_options()`를 source-aware reference option builder로 확장
   - LUT/basecase union hierarchy 제공
   - `overridden_in_basecase` metadata 제공
   - basecase-only slot 포함

6. slot validation 확장
   - 현재 basecase 기준 검증을 `basecase ∪ lut` 기준으로 확장
   - basecase에 없지만 LUT에 있는 slot은 유효 후보로 인정
   - 두 소스 모두에 없는 slot은 warning 또는 invalid 처리

7. Step3 packet 변경
   - `_build_basecase_value_groups()`를 effective reference value group builder로 확장
   - `effective_value`, `basecase_value`, `lut_value`, source reference id 제공
   - PowerMix는 선택 source 외 전체 mix도 함께 제공
   - Temperature는 국가·월별 LUT baseline 기준 delta sanity 정보를 제공

8. sanitizer 보강
   - `lut:` reference id prefix 허용
   - exact coordinate scalar patch는 effective record 기준으로 수행
   - `basecaseValue`는 effective value로 채움

9. logging/trace 보강
   - prompt size
   - candidate count
   - selected slot count
   - effective record count
   - source summary

10. 테스트 추가

## 12. 테스트 기준

### 12.1 LUT loader 단위 테스트

필수 검증:

- GDP
  - raw GDP row count: 2,365
  - country count: 169
  - growth record count: 2,118
  - all-zero GDP 6개국 성장률 제외
- PMI
  - t1 demand country 91개
  - reference country 84개
  - t2 long record 8,064개
  - value 전부 50.0
- PowerMix
  - record 8,399개
  - energy source 10종
  - country/year별 source 합계 1.0
- Temperature
  - derived temperature record 8,064개
  - HDD/CDD 동시 양수 0건
  - 변환식 검증
- LiqUtilAdjustment
  - raw record 41,103개
  - train count 350개
  - `Closed` 제외 정책 검증
  - MTPM * 12 capacity 변환 검증

### 12.2 Basecase-to-LUT mapping 테스트

기대 결과:

| 파라미터 | Basecase rows | Mapped | Unmapped | Mapping rate |
|---|---:|---:|---:|---:|
| GDP | 93 | 93 | 0 | 100.00% |
| PMI | 48 | 48 | 0 | 100.00% |
| PowerMix | 57 | 57 | 0 | 100.00% |
| Temperature | 150 | 150 | 0 | 100.00% |
| LiqUtilAdjustment | 21,656 | 21,569 | 87 | 99.60% |

LiqUtil expected mismatch:

- Period mismatch: 0개
- lifecycle mismatch: 4,496개
- capacity mismatch: 1,170개

LiqUtil expected unmapped:

| Country | LNG Plant | LNG Plant Train | Count |
|---|---|---:|
| Mexico | Mexico Pacific Limited LNG | Mexico Pacific Limited LNG T3 (Phase 2) | 36 |
| Argentina | Pan American LNG | Pan American LNG | 27 |
| Mozambique | Coral North FLNG | Coral North FLNG | 24 |

### 12.3 Merge 테스트

검증:

- 같은 좌표에 basecase와 LUT가 모두 있으면 effective value는 basecase다.
- LUT만 있으면 effective value는 LUT다.
- basecase만 있으면 effective source는 `basecase_only`다.
- source summary count가 기대와 맞는다.

### 12.4 Prompt packet 테스트

검증:

- Step2 slot option에 LUT-only slot이 포함된다.
- Step2 slot option에 basecase-only slot도 포함된다.
- Step2 slot option은 value row 전체를 포함하지 않는다.
- Step3 value group에는 선택된 slot의 effective record만 포함된다.
- PowerMix Step3에는 선택 Country/Year의 전체 energy source mix가 포함된다.
- LiqUtil Step3에는 선택 Country/Plant/Train/Year/Month만 포함된다.

### 12.5 회귀 테스트

검증:

- 기존 basecase-only behavior가 깨지지 않는다.
- 기존 basecase 좌표의 API output `basecaseValue`는 이전과 동일한 scalar를 유지한다.
- 신규 LUT-only slot은 basecase에 없어도 valid로 인정된다.

## 13. 완료 기준

구현 완료 기준:

- LUT repository가 요청마다 CSV를 다시 읽지 않는다.
- Step2가 `basecase ∪ lut` slot universe를 사용한다.
- Step3가 selected slot에 대해 `basecase override > LUT default` effective value를 사용한다.
- GDP와 Temperature 계산형 value가 서버에서 계산된다.
- LiqUtil `Nameplate Capacity`는 MTPA 환산값으로 basecase shape에 맞게 생성된다.
- `LNG train nameplate capacity (Bcm per month)`는 `Nameplate Capacity` slot 생성에 사용되지 않는다.
- prompt 크기 방어 설정이 있다.
- LLM trace에 후보/record count가 남는다.
- 테스트 기준의 mapping rate와 mismatch count가 재현된다.

## 14. 최종 요약

이 변경은 단순히 basecase record에 LUT record를 더하는 작업이 아니다.

정확한 구조는 다음과 같다.

```text
Raw sources:
  basecase_records
  lut_records

Merge:
  effective_reference_records

Step2:
  slot candidates from basecase ∪ lut
  compact hierarchy only

Step3:
  selected slot -> effective reference value
  basecase override wins
  LUT fills basecase-missing slot
```

특히 LiqUtilAdjustment는 아래 기준을 반드시 지킨다.

```text
lookup key:
  Country + LNG Plant + LNG Plant Train + Year + Month

Period:
  sanity check

Life Cycle Category:
  metadata / output axis

Nameplate Capacity:
  metadata / output axis
  LUT-only slot uses:
    LNG train capacity (Million tonnes LNG per month) * 12

Do not use:
  LNG train nameplate capacity (Bcm per month)
```

이 기준이면 slot 선택은 LUT 전체 universe를 활용하면서도, value 산정은 기존 basecase override를 보존하고, basecase에 없는 slot만 LUT default로 안정적으로 보강할 수 있다.
