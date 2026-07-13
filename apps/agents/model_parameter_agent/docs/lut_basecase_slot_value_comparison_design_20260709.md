# LUT/Basecase Slot/Value 비교 및 활용 설계

작성일: 2026-07-09

## 1. 목적

현재 `model_parameter_agent`의 Step2 slot 선택과 Step3 value 산정은 `resources/basecase/*.xlsm`에서 추출한
basecase record를 주 근거로 사용한다. 이번 분석은 아래 전제를 반영한다.

- LUT는 모델의 default 전체 기준값이다.
- basecase는 사용자가 일부 좌표를 override한 값이다.
- 따라서 slot 후보 universe는 LUT를 기본으로 보고, 동일 좌표에 basecase가 있으면 basecase 값을 우선 사용해야 한다.

## 2. 분석 기준

### Basecase 기준

비교 기준은 현재 레포에 있는 basecase 추출 결과 파일이다.

- `apps/agents/model_parameter_agent/docs/basecase_load_values_full_20260630.csv`

이 파일은 기존 extractor가 `resources/basecase/*.xlsm`에서 읽는 record 구조와 같다.

- `axes_json`: slot 좌표
- `value`: basecase value
- `reference_id`: workbook/sheet/cell 참조

### LUT 기준 파일

| 파라미터 | LUT 파일 | 변환 |
|---|---|---|
| GDP | `Demand_Model_LUT_General_value_based_t6.csv`, `Demand_Model_LUT_BCInput_value_based_t2.csv` | GDP 절대값을 국가별 전년 대비 성장률로 변환 |
| PMI | `Demand_Model_Input_PMIInput_value_based_t1.csv`, `Demand_Model_Input_PMIInput_value_based_t2.csv` | 연도 컬럼 `2024.0`~`2031.0`을 long form으로 변환 |
| PowerMix | `Demand_Model_LUT_General_value_based_t6.csv`, `Demand_Model_LUT_BCInput_value_based_t3.csv` | 이미 long form |
| Temperature | `Demand_Model_LUT_General_value_based_t6.csv`, `Demand_Model_Input_WeatherInput_value_based_t1.csv`, `Demand_Model_Input_WeatherInput_value_based_t2.csv` | HDD/CDD에서 temperature 역산 |
| LiqUtilAdjustment | `BCLiquefaction.csv` | plant/train 월별 utilization long form |

Temperature 변환식:

```python
if HDD > 0:
    temperature = 18 - HDD / 30
elif CDD > 0:
    temperature = 18 + CDD / 30
else:
    temperature = 18
```

현재 Weather LUT에는 `HDD <= 0 and CDD <= 0`인 좌표가 없었다.

GDP 변환식:

```python
gdp_growth_rate = GDP_abs_t / GDP_abs_t_minus_1 - 1
```

LiqUtil의 basecase `Nameplate Capacity`는 MTPA 축으로 보인다. `BCLiquefaction.csv`에서는 아래 값이 대응된다.

```python
Nameplate Capacity (MTPA) = LNG train capacity (Million tonnes LNG per month) * 12
```

`LNG train nameplate capacity (Bcm per month)`는 유사한 capacity 성격이지만 단위가 달라 basecase 축과 직접 비교하면 안 된다.
LUT-only slot을 basecase 형태로 만들 때도 `Nameplate Capacity`에는 Bcm/month 컬럼이 아니라 위 MTPA 환산값을 넣어야 한다.

## 3. 전체 비교 요약

| 파라미터 | basecase slot/value | LUT slot/value | 같은 좌표 overlap | 값 차이 |
|---|---:|---:|---:|---:|
| GDP | 93개, 12개국, 2024~2031 | raw GDP 2,365개/169개국, 성장률 2,118개/163개국, 2019~2031 | 93개 | 85개 다름 |
| PMI | 48개, 2개국, 4개 연도, 12개월 | 8,064개, 84개국, 2024~2031, 12개월 | 48개 | 48개 다름 |
| PowerMix | 57개, 11개국, Gas만, 2025~2030 | 8,399개, 84개국, 10개 energy source, 2022~2031 | 57개 | 57개 다름 |
| Temperature | 150개, 10개국, 2026~2030, 1~3월 | 8,064개, 84개국, 2024~2031, 12개월 | 150개 | 150개 다름 |
| LiqUtilAdjustment | 21,656개, 24개국, 311 train, 2023~2031 | 41,103개, 24개국, 350 train, 2017~2031 + 2050 일부 | business key 21,569개 | 20,230개 다름 |

핵심 결론:

- GDP/PMI/PowerMix/Temperature는 basecase가 LUT의 매우 작은 override subset이다.
- LiqUtilAdjustment도 대부분은 `BCLiquefaction.csv`와 겹치지만, lifecycle/nameplate metadata까지 완전 일치시키면 overlap이 크게 줄어든다.
- 현재처럼 basecase만 slot 후보로 쓰면 LUT에만 있는 국가, 월, energy source, plant/train을 Step2에서 놓칠 수 있다.
- Step3 value 산정에서는 같은 좌표에 basecase가 있으면 basecase를 우선하고, 없으면 LUT default를 사용해야 한다.

## 4. 파라미터별 상세 비교

### 4.1 GDP

Basecase:

- 축: `Country`, `Year`
- record: 93개
- 국가: 12개
- 연도: 2024~2031
- 값 범위: `-0.001`~`0.065`

LUT:

- `Full Country List`: 91개국
- GDP absolute value 파일: 169개국
- 성장률 산정 가능 국가: 163개국
  - `Falkland Islands`, `Martinique`, `Neutral Zone`, `Nigeria/Sao Tome JDZ`, `Saint Pierre and Miquelon`, `Western Sahara`는 GDP가 전 기간 0이라 성장률을 만들 수 없다.
- `Full Country List`와 GDP value 파일의 교집합: 84개국
- `Full Country List`에는 있지만 GDP value 파일에는 없는 국가: 7개
  - `Other Africa`, `Other America N`, `Other America S`, `Other Asia`, `Other Australia`, `Other Europe`, `Other Middle East`
- GDP value 파일에는 있지만 `Full Country List`에는 없는 국가: 85개
- 성장률 record: 2,118개
- 성장률 연도: 2019~2031
- 전체 성장률 범위: `-0.3003`~`0.6229`
- `Full Country List` 교집합 국가의 2024~2031 성장률 범위: `-0.0547`~`0.1322`

Overlap:

- basecase 93개 좌표는 모두 LUT 성장률과 매칭된다.
- 같은 좌표 93개 중 85개 값이 다르다.
- 최대 차이 예: Germany 2024 basecase `-0.001`, LUT 성장률 `0.06814`

설계 포인트:

- slot country universe는 `Full Country List` 91개를 사용한다.
- value lookup은 GDP absolute 파일에서 계산한 성장률을 사용한다.
- `Other ...` 7개 국가는 GDP value default가 없으므로 바로 값 산정에 쓰지 않는다.
  - 별도 reference mapping이 없으면 Step2에서 선택하지 않거나 validation warning으로 남긴다.
- `basecaseValue`에는 절대 GDP가 아니라 전년 대비 성장률을 넣어야 한다.
- 성장률 계산에는 전년도 절대 GDP가 필요하므로 첫 해인 2018은 value 후보가 될 수 없다.

### 4.2 PMI

Basecase:

- 축: `Country`, `Year`, `Month`
- record: 48개
- 국가: `China`, `Philippines`
- 연도/월:
  - China: 2025, 2026 전체 12개월
  - Philippines: 2029, 2030 전체 12개월
- 값 범위: `49.0`~`54.0`

LUT:

- `Selection of PMI Reference Country_Demand Location_Country`: 91개
- `Selection of PMI Reference Country_Reference Country_Country`: 84개
- `Base Case PMI Input` value record: 8,064개 = 84개국 * 8개년 * 12개월
- 연도: 2024~2031
- 월: 1~12
- 값 범위: 모든 좌표가 `50.0`
- `50.0`은 실측 신호라기보다 조정 없음 기준선에 가까운 중립 default로 해석한다.

`Other ...` demand country는 reference country로 매핑된다.

| Demand Location Country | Reference Country |
|---|---|
| Other Africa | Iran |
| Other America N | United States |
| Other America S | Brazil |
| Other Asia | Japan |
| Other Australia | Australia |
| Other Europe | Portugal |
| Other Middle East | Qatar |

Overlap:

- basecase 48개 좌표는 모두 LUT와 매칭된다.
- 같은 좌표 48개 모두 값이 다르다.
- 최대 차이: Philippines 2029/2030 일부 월 basecase `54.0`, LUT `50.0`

설계 포인트:

- slot country universe는 Demand Location Country 91개를 우선 사용한다.
- value lookup은 Country가 PMI value table에 없으면 t1의 Reference Country로 변환해서 조회한다.
- 출력 좌표의 `Country`는 모델 input이 기대하는 demand country를 유지하고, 내부 default value lookup만 reference country를 사용한다.
- basecase override는 출력 좌표 Country 기준으로 먼저 찾고, 없으면 reference country default를 사용한다.
- Step3 prompt에는 `lut_value=50`을 "중립 기준선"으로 명시하고, 실제 조정 폭은 basecase override 분포와 시나리오 강도를 함께 근거로 산정하게 한다.

### 4.3 PowerMix

Basecase:

- 축: `Country`, `Year`, `Energy Source`
- record: 57개
- 국가: 11개
- 연도: 2025~2030
- Energy Source: `Gas` 1개
- 값 범위: `0.031`~`0.495`

LUT:

- `Full Country List`: 91개국
- Power Generation value table: 84개국
- `Full Country List`에는 있지만 value table에는 없는 국가: GDP와 같은 `Other ...` 7개국
- record: 8,399개
- 연도: 2022~2031
- Energy Source: 10개
  - `Bioenergy`, `Coal`, `Gas`, `Geothermal`, `Hydro`, `Liquids`, `Nuclear`, `Other`, `Solar`, `Wind`
- 값 범위: `0.0`~`1.0`
- 국가/연도별 10개 energy source 합계는 모두 1.0으로 검증됨

Overlap:

- basecase 57개 좌표는 모두 LUT와 매칭된다.
- 같은 좌표 57개 모두 값이 다르다.
- 최대 차이 예: Belgium 2026 Gas basecase `0.1900`, LUT `0.3984`

설계 포인트:

- slot country universe는 `Full Country List` 91개를 사용하되, value default는 84개국만 존재한다.
- Energy Source universe는 LUT의 10개 source를 사용한다.
- basecase만 쓰면 Gas 외 source는 slot 후보로 거의 나오지 않는다. LUT source 목록을 Step2에 반드시 제공해야 한다.
- Step3에서 특정 source 비중을 바꾸면, 전체 PowerMix 합계 1.0 정합성을 확인해야 한다.
  - 단일 source만 제안하는 현재 응답 구조를 유지할 경우 rationale에 나머지 source와의 보정 필요성을 남긴다.
  - 여러 source를 동시에 제안할 수 있으면 같은 Country/Year의 source 합계가 1.0이 되도록 서버 후처리 또는 검증을 추가한다.
- Value 산정 prompt에는 선택된 source만이 아니라 해당 Country/Year의 전체 energy source mix를 함께 제공해야 재배분 가능 여지를 판단할 수 있다.

### 4.4 Temperature

Basecase:

- 축: `Country`, `Year`, `Month`
- record: 150개
- 국가: 10개
- 연도: 2026~2030
- 월: 1~3월
- 값 범위: `-2.2`~`11.3`

LUT:

- `Full Country List`: 91개국
- Weather value table: 84개국
- `Full Country List`에는 있지만 value table에는 없는 국가: GDP와 같은 `Other ...` 7개국
- HDD/CDD 기반 temperature record: 8,064개 = 84개국 * 8개년 * 12개월
- 연도: 2024~2031
- 월: 1~12
- 값 범위: `-15.3507`~`38.1314`
- 계산 branch:
  - HDD 사용: 3,848개
  - CDD 사용: 4,216개
  - HDD/CDD 모두 0이라 18도로 둔 좌표: 0개
  - HDD와 CDD가 동시에 양수인 좌표: 0개

Overlap:

- basecase 150개 좌표는 모두 LUT와 매칭된다.
- 같은 좌표 150개 모두 값이 다르다.
- 최대 차이 예: Italy 2026~2030 1월 basecase `6.8`, LUT 역산 `3.1126`

설계 포인트:

- slot country universe는 `Full Country List` 91개를 사용하되, value default는 Weather value table의 84개국만 존재한다.
- Step3 value default는 HDD/CDD 원값이 아니라 역산 temperature를 제공한다.
- 계절 이벤트는 LUT의 월별 baseline을 사용해야 한다. basecase만 쓰면 1~3월, 10개국에 과도하게 제한된다.
- `Other ...` 7개국은 temperature default가 없으므로 별도 mapping 없이는 선택 제한 또는 warning 대상이다.
- Sanity range는 전역 최소/최대보다 국가·월별 LUT baseline 대비 delta 기준으로 잡는 편이 안전하다.

### 4.5 LiqUtilAdjustment

Basecase:

- 축: `Country`, `LNG Plant`, `LNG Plant Train`, `Life Cycle Category`, `Nameplate Capacity`, `Year`, `Month`, `Period`
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

- record: 41,103개
- 국가: 24개
- LNG Plant: 90개
- LNG Plant Train: 350개
- Life Cycle Category: 5개
- 연도: 2017~2031, 그리고 2050년 1월 terminal row 일부
- Period: 0~169
- 값 범위: `0.0`~`3.3004`
- `value > 1.0`인 record: 6,232개

Overlap:

- business key `Country + Plant + Train + Year + Month + Period` 기준:
  - common: 21,569개
  - basecase only: 87개
  - LUT only: 19,534개
  - common 중 값 차이: 20,230개
- full key에 `Life Cycle Category + Nameplate Capacity`까지 포함하면:
  - common: 15,903개
  - basecase only: 5,753개
  - LUT only: 25,200개

full key overlap이 줄어드는 원인:

- business key common 21,569개 중 lifecycle 차이: 4,496개
  - basecase `Operational` vs LUT `Under Construction`: 4,003개
  - basecase `Speculative` vs LUT `Planned`: 397개
  - basecase `Planned` vs LUT `Under Construction`: 96개
- capacity 차이: 1,170개
- lifecycle과 capacity가 동시에 다른 경우는 없었다.

basecase only business key:

- `Mexico / Mexico Pacific Limited LNG / Mexico Pacific Limited LNG T3 (Phase 2)`: 36개
- `Argentina / Pan American LNG / Pan American LNG`: 27개
- `Mozambique / Coral North FLNG / Coral North FLNG`: 24개

LUT only 중 2024~2031 좌표도 9,032개 존재한다. 예: `Delta LNG`, `Wheatstone LNG`, `Prelude FLNG`, `Baltic LNG`, `Cameroon FLNG` 등.

추가 granularity 확인:

- `LNG plant utilisation %`라는 컬럼명과 달리 값은 train row 단위로 존재한다.
- 같은 plant/year/month 안에서도 train별 값이 다른 경우가 있으므로 plant 평균으로 뭉치지 말고 train 단위로 사용한다.
- 현재 데이터에서 `Country + Plant + Train + Year + Month`가 같은 common row의 `Period` 불일치는 0건이었다.

설계 포인트:

- value merge key는 full key보다 business key를 우선해야 한다.
  - 기본 key: `Country`, `LNG Plant`, `LNG Plant Train`, `Year`, `Month`
  - `Period`는 현재 데이터에서는 Year/Month와 완전히 정렬되어 있으므로 함께 검증하되, 향후 LUT 갱신으로 period 기준이 달라지면 Year/Month를 canonical key로 두고 mismatch warning을 남긴다.
- output slot에는 기존 모델 target과 맞추기 위해 `Life Cycle Category`, `Nameplate Capacity`도 채워야 한다.
  - basecase override가 있으면 basecase metadata를 사용한다.
  - LUT default만 있으면 LUT `Infra Life Cycle`과 `MTPM * 12`로 계산한 MTPA capacity를 사용한다.
  - `LNG train nameplate capacity (Bcm per month)`는 output slot의 `Nameplate Capacity`에 사용하지 않는다.
  - basecase metadata와 LUT 환산 MTPA가 다르면 매핑 실패로 보지 말고 capacity mismatch warning으로 남긴다.
- LUT의 `Closed` lifecycle train은 기본 slot 후보에서 제외하고, basecase에만 있는 `Speculative` slot은 override-only 후보로 유지한다.
- `value > 1.0`이 양쪽 모두에 많으므로 0~1 hard validation은 현재 데이터와 맞지 않는다.
  - 다만 1.0 초과는 rationale 또는 warning에서 고가동/초과가동 가능성으로 표시한다.
- LUT에는 과거 기간과 2050 terminal row가 섞여 있으므로 Step2/Step3 prompt에는 period policy로 현재 이후 target 기간만 필터링해야 한다.

## 5. 현행 코드 영향 지점

현재 propose flow는 아래 순서다.

```text
load_basecase_samples
-> propose_parameter_slots
-> filter_basecase_records_by_slots
-> propose_parameter_values
```

핵심 사용 지점:

- `load_basecase_samples()`
  - `build_basecase_records()`로 basecase record만 로드한다.
- `_build_parameter_slot_tasks()`
  - `_build_basecase_slot_options(basecase_records)` 결과만 Step2 LLM에 제공한다.
- `filter_basecase_records_by_slots()`
  - Step2에서 선택된 slot에 맞는 basecase record만 남긴다.
- `_build_parameter_value_tasks()`
  - `_build_basecase_value_groups(basecase_records)`만 Step3 LLM에 제공한다.
- `_patch_basecase_value()`
  - Step3 LLM이 reference id만 반환한 경우 basecase record에서 값을 채운다.

따라서 LUT를 도입하려면 "basecase_records를 늘린다"가 아니라 "reference records를 원천별로 만들고 effective value를 병합한다"가 안전하다.

## 6. 제안 설계

### 6.1 내부 record 모델

새 내부 record는 아래 형태가 적절하다.

```python
{
    "candidate_key": "...",
    "parameter_name": "GDP",
    "source": "lut",  # or "basecase"
    "reference_id": "lut:Demand_Model_LUT_BCInput_value_based_t2:...",
    "axes": {"Country": "China", "Year": 2026},
    "value_name": "GDP",
    "value": 0.042,
    "metadata": {
        "raw_value": 123.45,
        "transform": "pct_change_from_absolute_gdp",
        "lookup_country": "China",
        "source_file": "..."
    }
}
```

그리고 동일 좌표를 merge한 effective record를 만든다.

```python
{
    "axes": {...},
    "value_name": "...",
    "effective_value": 0.042,
    "effective_source": "basecase",  # or "lut"
    "basecase_value": 0.042,  # or None
    "lut_value": 0.039,  # or None
    "basecase_reference_id": "Demand:...",
    "lut_reference_id": "lut:..."
}
```

우선순위:

1. 같은 normalized coordinate에 basecase가 있으면 basecase override 사용
2. basecase가 없고 LUT가 있으면 LUT default 사용
3. basecase만 있고 LUT가 없으면 basecase-only override로 포함
4. 둘 다 없으면 slot/value 후보에서 제외하거나 warning 처리

### 6.1.1 LUT Repository

LUT loader는 파라미터별 CSV 처리 로직을 flow/node에 직접 넣지 말고 read-only repository로 분리한다.

```python
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
        """Value를 제외한 유효 slot 축 조합 전집을 반환한다."""

    def records(
        self,
        parameter_name: str,
        *,
        axes_filter: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """basecase record와 같은 형태의 LUT default value record를 반환한다."""
```

파라미터별 spec 책임:

- GDP: absolute GDP long table을 growth rate로 파생하고 `Full Country List` 교집합을 slot 후보로 사용한다.
- PMI: t1 demand country/reference country mapping과 t2 wide year metric을 함께 처리한다.
- PowerMix: Country/Year/Energy Source long table을 그대로 사용하고 source 합계 검증 정보를 만든다.
- Temperature: HDD/CDD wide table을 melt한 뒤 temperature를 파생한다.
- LiqUtilAdjustment: `Closed` train 제외, MTPM→MTPA capacity 변환, train 단위 utilization record를 만든다.

`reference_id`는 basecase cell id와 충돌하지 않도록 `lut:{file_name}:{row_or_cell}` prefix를 사용한다.

### 6.2 Flow 변경안

현재 노드명을 유지하려면 `load_basecase_samples()` 내부에서 확장할 수 있지만, 의미상 아래 이름이 더 정확하다.

```text
load_reference_records
-> propose_parameter_slots
-> filter_reference_records_by_slots
-> propose_parameter_values
```

상태 필드:

```python
basecase_records: list[dict[str, Any]]
lut_records: list[dict[str, Any]]
effective_reference_records: list[dict[str, Any]]
```

API 응답 schema는 당장 바꾸지 않는다.

- 기존 `basecaseValue`에는 effective reference value를 넣는다.
- 내부 rationale/warning에는 `source=basecase_override` 또는 `source=lut_default`를 남긴다.
- API에 `referenceSource` 같은 필드를 추가하는 것은 별도 계약 변경이므로 후속 과제로 분리한다.

### 6.3 Step2 slot 선택

Step2에는 value record 전체를 주지 말고 compact slot option을 준다.

```json
{
  "slot_options": {
    "axis_names": ["Country", "Year", "Energy Source"],
    "axis_values": {"Year": [2024, 2025, ...]},
    "slot_hierarchy_axes": ["Country", "Energy Source"],
    "slot_hierarchy": [...],
    "slot_hierarchy_metadata": [
      {"path": ["Belgium", "Gas"], "overridden_in_basecase": true}
    ],
    "source_summary": {
      "lut_slot_count": 8399,
      "basecase_override_count": 57
    }
  }
}
```

기준:

- hierarchy는 LUT와 basecase의 union으로 만든다.
- 같은 path가 양쪽에 있으면 basecase override가 있음을 metadata로 표시한다.
- slot option에는 `overridden_in_basecase` 또는 source summary를 넣어 LLM이 기존 override slot과 default-only slot을 구분하게 한다.
- basecase에만 있는 path도 포함한다.
- Cartesian product를 만들지 않고 실제 존재하는 row/path만 사용한다.
- `Full Country List`와 value table이 분리된 파라미터는 다음처럼 처리한다.
  - slot country list: `Full Country List` 또는 PMI demand location 91개
  - value availability: 실제 value table 84개
  - value가 없는 `Other ...` 국가는 reference mapping이 있는 경우만 lookup 가능
- slot validation은 basecase slot만 기준으로 보지 말고 `basecase ∪ lut` 기준으로 확장한다.

### 6.4 Step3 value 산정

Step3에는 선택 slot에 맞는 effective value group을 제공한다.

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

LLM에는 아래 원칙을 명시한다.

- `effective_value`가 현재 기준값이다.
- `basecase_value`가 있으면 사용자가 override한 값이므로 `lut_value`보다 우선한다.
- `basecase_value`가 없으면 `lut_value`가 default 기준값이다.
- proposed value가 기준값과 같아도 근거가 있으면 그대로 제안할 수 있다.

서버 sanitizer:

- `_patch_basecase_value()`는 이름을 `_patch_reference_value()`로 바꾸거나 내부적으로 effective reference를 조회한다.
- LLM이 `basecase_reference_ids`를 반환하는 현재 계약은 유지하되, `lut:` prefix reference id도 허용한다.
- API 출력의 `basecaseValue`는 effective value로 scalar화한다.

컨텍스트 크기 제어:

- Step3에는 LUT 전체를 넣지 않고 Step2에서 선택된 slot에 매칭되는 record만 넣는다.
- 필터 후에도 record가 너무 많으면 silent sampling하지 말고 기존 정책처럼 warning/failure로 드러낸다.
- LiqUtilAdjustment는 row 수가 커서 Country/Plant/Train 중 최소한 Country와 Plant 수준까지 좁힌 뒤 value group을 구성하는 것이 안전하다.
- GDP는 value lookup용 현재/미래 좌표와 별도로, 필요하면 같은 국가의 최근 과거 성장률 3~5개만 trend 참고로 제공한다.

## 7. 파라미터별 구현 매핑

| 파라미터 | slot universe | default value lookup | override key |
|---|---|---|---|
| GDP | `Full Country List_Country` 91개 + GDP value table country/year | GDP absolute를 country/year별 성장률로 변환 | `Country + Year` |
| PMI | PMI demand location country 91개, reference country 84개 | `Country + Year + Month`; 없으면 reference country로 lookup | `Country + Year + Month` |
| PowerMix | `Full Country List_Country` 91개 + LUT energy source 10개 | `Country + Year + Energy Source` | `Country + Year + Energy Source` |
| Temperature | `Full Country List_Country` 91개 + month/year | HDD/CDD 역산 `Country + Year + Month` | `Country + Year + Month` |
| LiqUtilAdjustment | `Country + Plant + Train` hierarchy, lifecycle/capacity metadata 포함 | `Country + Plant + Train + Year + Month`, `Period`는 정합성 검증 | business key 우선 |

## 8. 리스크 및 확인 필요 사항

1. `Other ...` 국가 처리
   - PMI는 reference mapping이 있다.
   - GDP/PowerMix/Temperature는 값 lookup mapping이 없다.
   - 별도 정책 없이 `Other ...`를 선택하면 Step3 default value가 비게 된다.

2. 국가/시설 명칭 정규화
   - 현재 비교 대상 basecase 국가는 LUT와 문자열이 일치했지만, 향후 입력/갱신 데이터에서는 표기 차이가 생길 수 있다.
   - Country, Plant, Train, Energy Source는 `_normalize_for_key()` 수준의 공백/대소문자/기호 정규화를 거쳐 매칭한다.
   - 정규화 후에도 매칭되지 않는 slot은 warning으로 노출한다.

3. prompt 크기 증가
   - LUT를 전수 value로 넣으면 특히 LiqUtil에서 prompt가 커진다.
   - Step2는 compact hierarchy만 제공하고, Step3는 선택 slot으로 필터링한 value group만 제공해야 한다.

4. LiqUtil metadata 불일치
   - lifecycle/nameplate까지 exact key로 보면 common이 15,903개로 줄어든다.
   - value merge는 business key 기준, output metadata는 effective source 기준으로 채우는 편이 안전하다.

5. PowerMix 합계 정합성
   - LUT는 country/year별 source 합이 1.0이다.
   - 제안 값이 일부 source만 바꾸면 모델 해석상 합계가 깨질 수 있다.
   - 서버 검증 또는 rationale 규칙이 필요하다.

6. GDP 성장률 계산
   - absolute GDP 파일의 첫 해는 성장률 산정이 불가능하다.
   - GDP가 전 기간 0인 국가는 성장률이 전부 NaN이므로 value default에서 제외해야 한다.
   - 전년도 값이 누락된 국가/연도는 default value를 만들지 않아야 한다.

7. API 계약
   - `basecaseValue` 의미를 effective reference value로 확장하면 외부 필드 변경은 없다.
   - 다만 이름상 혼동이 있으므로 내부 문서와 rationale에는 `basecase override`와 `lut default`를 구분해야 한다.

## 9. 성능 및 운영 고려사항

### 9.1 Prompt 크기

가장 큰 위험은 LUT 전체 value row를 prompt에 넣는 것이다. 특히 LiqUtilAdjustment는 41,103개 row라 전수 입력하면
token 초과와 응답 지연이 발생할 가능성이 높다.

권장 정책:

- Step2 slot 선택에는 value row를 넣지 않는다.
  - 국가/연도/월/source/train 후보를 compact `axis_values`, `slot_hierarchy`, `source_summary`로만 제공한다.
  - LiqUtilAdjustment는 전체 train list를 그대로 펼치지 말고 `Country -> Plant -> Train` hierarchy로 압축한다.
- Step3 value 산정에는 Step2에서 선택된 slot에 매칭되는 effective reference record만 제공한다.
  - PowerMix는 선택된 Country/Year의 전체 source mix만 함께 제공한다.
  - Temperature는 선택된 Country/Year/Month의 baseline과 필요 시 인접 월/전후년 소량만 제공한다.
  - GDP는 선택된 Country/Year의 성장률과 필요 시 같은 국가의 최근 과거 성장률 3~5개만 trend 참고로 제공한다.
- 서버 측에서 deterministic pre-filter를 먼저 수행한다.
  - scenario/event/dimension에서 국가, plant, train, energy source, 기간을 추출할 수 있으면 그 값으로 LUT 후보를 먼저 줄인다.
  - 필터 후에도 후보가 너무 많으면 임의 sampling하지 말고 validation warning 또는 실패로 노출한다.
- 설정값을 basecase와 LUT에 분리한다.
  - 예: `model_parameter_max_lut_slot_options`, `model_parameter_max_effective_reference_records`
  - 기존 `model_parameter_max_value_prompt_basecase_records`와 같은 방어선을 LUT에도 둔다.

피해야 할 방식:

- LUT 전체 CSV row를 그대로 prompt에 넣기
- 전체 국가 × 전체 월 × 전체 energy source를 Cartesian product로 생성하기
- token 초과를 피하려고 근거 없이 random/sample row를 잘라 넣기

### 9.2 LLM 실행 시간

프롬프트가 커지면 LLM latency가 늘고, slot 후보가 많아지면 selected slot 수도 늘어날 수 있다. 현재 flow는 Step2/Step3 LLM 호출이
직렬이므로 한 단계가 커지면 전체 API 시간이 바로 증가한다.

권장 정책:

- 후보 축소는 LLM 전에 서버에서 먼저 한다.
  - 명시 국가/기간/plant가 있으면 해당 후보만 Step2에 제공한다.
  - 명시 대상이 없으면 compact summary만 제공하고 전체 상세 hierarchy는 주지 않는다.
- Step2의 `maxParameterSlots`를 유지하고, LUT 도입 후 파라미터별 상한을 별도로 둘 수 있게 한다.
  - LiqUtilAdjustment처럼 train 단위 후보가 많은 파라미터는 더 낮은 상한이 필요할 수 있다.
- Step3에는 numeric lookup 결과를 서버가 계산해서 넣고, LLM에는 "값을 찾는 작업"이 아니라 "조정 여부와 폭 판단"만 맡긴다.
- LLM call trace에 prompt size, candidate count, selected slot count, effective record count를 추가로 로깅한다.
- timeout이 발생하면 어떤 파라미터/후보 수에서 커졌는지 알 수 있도록 source summary를 warning에 포함한다.

### 9.3 CSV 읽기와 메모리

CSV를 요청마다 읽고 wide table을 매번 melt하면 불필요하게 느려진다. LUT 파일 규모는 현재 기준으로 process memory에 캐시할 수 있는 수준이다.

현재 대략적인 규모:

- `BCLiquefaction.csv`: 41,103 rows
- PowerMix LUT: 8,399 rows
- GDP LUT: 2,365 rows
- PMI/Weather wide table: 각 1,008 rows, long 변환 후 각 8,064 cells 수준

권장 정책:

- `LutRepository`는 process-level read-only cache로 둔다.
  - 앱 시작 시 eager load하거나 첫 요청에서 lazy load한다.
  - 운영에서는 파일이 immutable하다고 보고 요청 중 reload하지 않는다.
  - 개발 편의를 위해서는 mtime/checksum 기반 reload 옵션만 별도로 둔다.
- CSV 원본 DataFrame과 normalized lookup index를 모두 매 요청 state에 넣지 않는다.
  - state에는 선택된 후보에 필요한 record만 넣는다.
  - lookup은 repository 내부 dict/index에서 수행한다.
- 파라미터별 normalized key index를 미리 만든다.
  - GDP: `(Country, Year)`
  - PMI: `(Country, Year, Month)` 및 reference country mapping
  - PowerMix: `(Country, Year, Energy Source)`
  - Temperature: `(Country, Year, Month)`
  - LiqUtilAdjustment: `(Country, LNG Plant, LNG Plant Train, Year, Month)`
- multi-worker 배포에서는 cache가 worker 수만큼 복제된다.
  - 현재 CSV 규모에서는 허용 가능하지만, worker 수 증가 시 메모리 사용량을 로그로 확인한다.
- DataFrame은 read-only로 다루고 mutation이 필요한 경우 request-local copy를 만든다.

### 9.4 Side Effect

LUT 도입은 단순 데이터 추가가 아니라 모델 behavior를 바꾼다. 아래 부작용을 방어해야 한다.

- slot 과다 제안
  - LUT universe가 커지면서 LLM이 관련 없는 국가/월/train까지 고를 수 있다.
  - scenario/event/dimension 기반 pre-filter와 `maxParameterSlots`가 필수다.
- `basecaseValue` 의미 혼동
  - API 필드는 유지하더라도 내부적으로는 effective reference value가 된다.
  - rationale/warning에는 `basecase_override`인지 `lut_default`인지 남겨야 한다.
- `Other ...` 국가
  - PMI는 reference country mapping이 있지만 GDP/PowerMix/Temperature는 default value가 없다.
  - 값이 없는 `Other ...`는 selected slot으로 확정하지 않거나 명시 warning을 남긴다.
- PowerMix 합계 정합성
  - 일부 source만 조정하면 country/year 합계 1.0이 깨질 수 있다.
  - value 검증 또는 rationale 규칙이 필요하다.
- LiqUtil metadata 불일치
  - Nameplate Capacity와 lifecycle은 lookup key가 아니라 metadata/sanity check다.
  - capacity mismatch를 매핑 실패로 처리하면 정상 lookup이 과도하게 실패한다.
- 결과 재현성
  - 후보가 많아져 LLM 판단 영역이 넓어진다.
  - 서버 pre-filter, deterministic sort, deterministic cap을 적용해 같은 입력의 prompt가 안정적으로 생성되게 한다.
- 로그/DB 저장량 증가
  - full LUT record를 llm trace나 proposal DB에 저장하지 않는다.
  - source summary, selected effective records, warning만 저장한다.

## 10. 권장 구현 순서

1. `utils/lut.py` 추가
   - 파라미터별 LUT loader/normalizer 구현
   - GDP, Temperature 변환 포함
   - LiqUtil capacity MTPA 변환 포함

2. effective reference merge 유틸 추가
   - normalized coordinate key 생성
   - basecase override 우선순위 적용
   - `basecase_only`, `lut_only`, `overridden` source summary 생성

3. propose flow state 확장
   - `lut_records`
   - `effective_reference_records`
   - 기존 `basecase_records`는 backward compatibility를 위해 유지

4. slot validation 확장
   - 현재 basecase 기준 검증을 `basecase ∪ lut` 기준으로 확장
   - basecase에 없지만 LUT에 있는 slot은 유효 후보로 인정
   - 두 소스 모두에 없는 slot은 warning 또는 invalid 처리

5. Step2 packet 변경
   - `_build_basecase_slot_options()`를 source-aware reference option builder로 확장
   - LUT/basecase union hierarchy 제공
   - `overridden_in_basecase` metadata 제공

6. Step3 packet 변경
   - `_build_basecase_value_groups()`를 effective reference value group builder로 확장
   - `effective_value`, `basecase_value`, `lut_value`, source reference id 제공
   - PowerMix는 선택 source 외 전체 mix도 함께 제공
   - Temperature는 국가·월별 LUT baseline 기준 delta sanity 정보를 제공

7. sanitizer 보강
   - reference id prefix 허용
   - exact coordinate scalar patch는 effective record 기준으로 수행

8. 테스트
   - 단위 테스트: 각 LUT loader record 수와 핵심 변환값 검증
   - GDP all-zero 국가의 성장률 제외 검증
   - Temperature HDD/CDD 동시 양수 0건 및 변환식 검증
   - LiqUtil Year/Month/Period 정렬 검증
   - merge 테스트: basecase override가 LUT보다 우선하는지 검증
   - prompt packet 테스트: basecase에 없는 LUT-only slot이 Step2 option에 포함되는지 검증
   - 회귀 테스트: 기존 basecase-only 좌표의 출력 `basecaseValue`가 이전과 동일한지 검증

## 11. 결론

LUT를 default, basecase를 override로 해석하는 설계가 현재 데이터 구조와 맞다. 특히 GDP/PMI/PowerMix/Temperature는
basecase가 매우 작은 subset이므로, slot 선택 단계에서 LUT를 포함하지 않으면 모델 입력 가능 범위를 크게 누락한다.

구현상 핵심은 basecase record를 단순히 늘리는 것이 아니라, LUT와 basecase를 source-aware reference로 분리한 뒤
동일 좌표에 대해 effective value를 만들어 Step2/Step3에 제공하는 것이다. 이 방식이면 public API 변경 없이도
기존 `basecaseValue`에는 현재 기준값을 안정적으로 채울 수 있고, 내부적으로는 LUT default와 basecase override를
명확히 구분할 수 있다.
