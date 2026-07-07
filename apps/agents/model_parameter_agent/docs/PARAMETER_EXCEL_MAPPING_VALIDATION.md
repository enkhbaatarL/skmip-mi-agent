# Parameter Excel Mapping 검증 결과

> 검증 기준 파일
>
> - 매핑 Excel: `resources/260625_시나리오가정_MI수급모델_input_매핑_vfShare.xlsx`
> - 범위 문서: `docs/model_input_table_ranges_20260630.md`
> - Basecase workbook: `resources/LNG수급모델_운영버전_입력시트_Basecase_20260610/*.xlsm`

## 결론

전체 19개 parameter 중 모델/시트/값 컬럼 관점에서 명확히 맞는 항목이 다수지만,
엔진 입력 range 문서와 완전히 일치하지 않는 항목도 있다.

- `OK`: 현재 매핑이 범위 문서와 대체로 일치
- `OK(확장축)`: 엔진 range보다 왼쪽 축 컬럼을 더 포함하지만 agent slot 추론에는 타당
- `WARN`: 동작은 가능하지만 range 문서와 시작 행 또는 축 컬럼이 어긋남
- `FAIL`: 문서상 입력 대상 블록과 매핑이 다른 블록을 가리킬 가능성이 큼

## 현재 Basecase record 유무

현재 리소스 기준으로 매핑된 Basecase workbook/sheet 자체가 없는 parameter는 없다.
19개 parameter 모두 `model_file + model_sheet`에 해당하는 sheet profile은 존재한다.

다만 `build_basecase_records()`로 실제 값 record가 추출되는지는 다르다.

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

## Parameter별 검증표

| Parameter | 판정 | 근거 | 권고 |
|---|---|---|---|
| CDD | WARN | 문서상 `WeatherAdjustment` t1 데이터 시작은 `B12:G11`이나 매핑은 row 7부터 스캔한다. `E=CDD`, 값 `G`는 방향이 맞다. | `basecase_data_start_row`를 12로 맞추는 편이 안전하다. |
| Coal Futures Price | WARN | 문서상 `CoalGasAdjustment` t1 데이터 시작은 `B12:E11`이나 매핑은 row 7부터 스캔한다. 값 컬럼 `E`는 맞다. | `basecase_data_start_row`를 12로 맞추는 편이 안전하다. |
| Gas Futures Price | WARN | 문서상 `CoalGasAdjustment` t2 데이터 시작은 `H12:K11`이나 매핑은 row 7부터 스캔한다. 값 컬럼 `K`는 맞다. | `basecase_data_start_row`를 12로 맞추는 편이 안전하다. |
| GDP | WARN | 문서상 `GDPPopulationAdjustment` t1 데이터 시작은 `B12:F104`이나 매핑은 row 7부터 스캔한다. 값 컬럼 `F`는 `% change (+/-)`로 현재 추출값과 일치한다. | 시작 행은 12로 정렬 권고. `parameter_name=GDP`가 `% change` 값을 의미한다는 점을 명확히 할 필요가 있다. |
| HDD | WARN | 문서상 `WeatherAdjustment` t1 데이터 시작은 `B12:G11`이나 매핑은 row 7부터 스캔한다. `E=HDD`, 값 `G`는 방향이 맞다. | `basecase_data_start_row`를 12로 맞추는 편이 안전하다. |
| HurricaneIntensity | OK | 문서상 `{USA}Hurricanes` 범위는 `B7:E7`, 데이터 시작 `B8:E7`이다. 매핑은 `B:Year,C:Month,D:HurricaneIntensity`로 입력 값 컬럼을 정확히 가리킨다. | 유지. |
| LiqProdAdjustment | OK(확장축) | 문서상 Supply importer range는 `D6:DA358`이나 실제 시트에는 `B:F`에 Country/Plant/Train/Life Cycle/Capacity 축이 있고 `G:DA`에 월별 값 영역이 있다. 매핑은 agent slot 추론에 필요한 축을 포함한다. | 유지 가능. 단 현재 Basecase 값 영역이 대부분 비어 있어 record 0건으로 로드된다. |
| LiqUtilAdjustment | OK(확장축) | 문서상 range는 `D6:DA358`, 매핑은 `B:F` 축과 `G:DA` value 영역을 사용한다. 실제 시트의 Year/Month/Period rows `7/8/9`, header row `10`, data row `11`과 맞다. | 유지. |
| PipelineAdjustment | WARN | 문서상 `PipelineAdjustment`는 `A7:I72`이고 실제 헤더에 `From country`, `To country`가 있다. 매핑은 `B:Year,C:Month,D:Pipeline name,H:PipelineAdjustment`만 포함한다. semantic axes의 From/To와 불일치한다. | `E:From Country,F:To Country` 축 추가 권고. |
| PMI | WARN | 문서상 `PMIAdjustment` t1 데이터 시작은 `B12:F60`이나 매핑은 row 7부터 스캔한다. 값 컬럼 `F`는 맞다. | `basecase_data_start_row`를 12 또는 실제 첫 유효 row인 13으로 조정 검토. |
| PNG Contract Volume | OK | 문서상 `MidstreamContractInput_ForecastedPNGContractVolume_Imports`는 header `A2:M4`, data `A5:M1104`이다. 매핑은 최종 헤더 row 4와 data row 5, 값 `D`를 사용한다. | 유지. |
| PowerMix | OK | 문서상 `PowerMixAdjustment` t1은 header `B6:F6`, data `B12:F68`이다. 매핑도 header 6, data 12, 값 `F`로 일치한다. | 유지. |
| RegasAdjustment | OK(확장축) | 문서상 range는 `B10:DV454`이나 실제 월별 입력값은 `H:DK`까지이고, `DM:DV`는 Country/연도별 capacity helper 영역이다. 매핑은 `B:G` 축과 `H:DK` 값 영역을 사용해 월별 조정값을 정확히 제한한다. | 유지. |
| RemainingUnrestrictedAmount | OK | 문서상 `TradeRestrictionInput_LNGTradeRestrictions`는 header `B4:K5`, data `B6:K44`이다. 매핑은 row 5/6과 값 `J`를 사용한다. | 유지. |
| ShippingCost | OK | 문서상 `ShippingCostInput_CharterCost_174000cbm_TwoStroke`는 header `A4:G5`, data `A6:G13`이다. 매핑은 row 5/6과 사용자 입력 절대값 컬럼 `F`를 사용한다. | 유지. row 6은 값이 비어 있어 현재 record는 row 7부터 나온다. |
| SupplyDisruption | FAIL | 문서상 engine이 읽는 `VolumeAdjustment` 입력 범위는 `H7:P7`, 데이터 시작 `H8:P7`이며 실제 헤더도 `H:P`에 월별 Country/Volume 입력 블록이 있다. 매핑은 `B:Year,C:Province Country,E:SupplyDisruption`으로 왼쪽의 별도 annual/upstream 블록을 가리킨다. | 매핑 대상 블록을 확정해야 한다. 문서 기준으로는 `I:Year,J:Month,K:Country,M:SupplyDisruption` 또는 실제 입력 value 컬럼 기준 재매핑이 필요하다. |
| Temperature | WARN | 문서상 `WeatherAdjustment` t2 데이터 시작은 `K12:O161`이나 매핑은 row 7부터 스캔한다. 값 컬럼 `O`는 맞다. | `basecase_data_start_row`를 12로 맞추는 편이 안전하다. |
| User-Adjusted Gas Demand | OK | 문서상 `DemandOutputOverwrite` t1은 header `D6:J7`, data `D8:J19`이다. 매핑은 header 7, data 8, 값 `H`로 sector overwrite input을 가리킨다. | 유지. |
| VolumeCancelled | OK | 문서상 `TradeRestrictionInput_LNGTradeRestrictions`는 header `B4:K5`, data `B6:K44`이다. 매핑은 row 5/6과 값 `F`를 사용한다. | 유지. |

## 주요 이슈

### 1. Demand fixed table의 시작 행이 문서보다 빠름

`CDD`, `Coal Futures Price`, `Gas Futures Price`, `GDP`, `HDD`, `PMI`, `Temperature`는
문서상 실제 데이터 시작이 대부분 row 12 이후인데, 매핑은 row 7부터 스캔한다.
현재 extractor는 `#REF!`를 record value로 만들지 않기 때문에 결과가 크게 깨지지는 않지만,
불필요한 스캔과 예외적 오인식 가능성이 있다.

### 2. `SupplyDisruption`은 입력 블록 불일치 가능성이 큼

`VolumeAdjustment` 실제 시트에는 왼쪽 `A:G` 블록과 오른쪽 `H:P` 블록이 함께 있다.
범위 문서는 engine 입력 대상으로 `H:P` 블록만 정리하고 있는데,
현재 매핑은 `B/C/E`를 사용한다. 이 상태는 문서 기준으로는 잘못 매핑된 것으로 보는 것이 맞다.

### 3. `PipelineAdjustment`는 From/To 축 누락

문서와 실제 시트에는 `From country`, `To country` 컬럼이 있지만,
현재 매핑은 `Pipeline name`만 축으로 사용한다. scenario에서 From/To를 특정해야 하는 경우 slot matching 정확도가 떨어질 수 있다.

### 4. Supply matrix 계열은 엔진 range보다 agent 축이 넓음

`LiqProdAdjustment`, `LiqUtilAdjustment`, `RegasAdjustment`는 엔진 importer range와 완전히 같은 범위는 아니지만,
agent가 Country/Plant 등 slot 축을 잡기 위해 왼쪽 축 컬럼을 포함하는 구조라 합리적이다.
특히 `RegasAdjustment`는 문서상 `B:DV`이나 월별 값 영역은 `H:DK`로 제한하는 현재 매핑이 더 정확하다.

## 수정 우선순위

1. `SupplyDisruption`: `VolumeAdjustment`의 실제 입력 대상 블록을 `H:P` 기준으로 재매핑할지 확정.
2. `PipelineAdjustment`: `E:From country`, `F:To country` 축 추가.
3. Demand fixed table의 `basecase_data_start_row`: 문서의 데이터 시작 row에 맞춰 12 계열로 정렬.
4. `GDP`: 값 컬럼 `F`가 `GDP`가 아니라 `% change (+/-)`임을 parameter name/value name에 더 명확히 반영할지 검토.
