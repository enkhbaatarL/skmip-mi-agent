# Event 구조화 → Scenario v4 → Model Parameter 증적 가이드

## 1. 목적과 적용 범위

이 문서는 Scenario 생성 이전 단계에서 Event를 구조화하는 개발자가, 현재 Model Parameter Agent의 v4
proposal capability가 요구하는 대상·기간·수치 근거를 잃지 않도록 Event 증적을 설계하는 기준이다.

대상 runtime은 다음 계약으로 한정한다.

- Scenario API `v4`
- `generation_strategy=multi_event_model_lever_dimensions`
- Impact Lever catalog `v4.1`
- Model Parameter proposal capability `extend16-v8`
- 현재 신규 proposal 대상 16종: LUT-backed 10종과 Basecase-only 6종

이 문서는 Event 구조화 단계가 Model Parameter를 직접 선택하도록 요구하지 않는다. Event 구조화의 책임은
원문에서 확인할 수 있는 확정·관측 사실과 미래 주장을 구분하고, 각각의 `대상`, `기간`, `측정값`, `변화`,
`출처`, `주장 주체`를 보존하는 데 있다. Scenario Group Agent가 이 증적과 catalog를 이용해 Impact Lever와
Scenario 분기를 만들고, Model Parameter Agent가 선택된 Lever state와 exact model slot을 연결한다.

```text
Record 원문
  → Event 사실·미래 주장·상충 관계 구조화
  → Scenario v4 Event impact / Lever / Dimension
  → 선택된 Scenario branch
  → exact model slot
  → Model Parameter proposal
```

현재 `EventPayload`는 제목, 한 줄 요약, 핵심 bullet, 상세 분석, 발생 시각, 태그와 source record ID를 전달한다.
아래의 `structuredEvidence`는 구현 완료된 공개 API가 아니라, Event 구조화 보강 시 도입할 목표 계약이다.
실제 필드 추가에는 Event 소유 시스템, DB migration 소유 저장소, Scenario API consumer의 별도 변경이 필요하다.

특히 LNG 뉴스와 리포트는 하나의 Event 안에서도 다음 내용을 함께 포함할 수 있다.

- 이미 발생해 확인된 과거 사실과 현재 관측
- 운영사·정부 등의 발표 계획 또는 미래 예상
- 리서치 기관·시장 참여자의 전망과 조건부 View
- 같은 대상·기간에 대해 서로 양립하기 어려운 복수 전망

따라서 Event는 하나의 일관된 결론이 아니라 여러 증적과 주장을 담는 container로 본다. 미래 주장은 출처가
있더라도 확정 사실이 아니며, 여러 전망을 평균하거나 가장 최근 값을 자동 채택해 Event의 단일 결론으로 만들지
않는다.

## 2. 책임 경계

### Event 구조화가 해야 하는 일

- 원문에서 확정·관측 사실, 발표 계획, 미래 예상, 기관 View를 분리한다.
- 미래 주장의 발화 주체, 발행·관측 시점, 전망 대상 기간과 전제조건을 보존한다.
- 비교 가능한 미래 주장끼리 지지·상충·수정 관계를 명시하되, 판단할 수 없으면 독립 주장으로 남긴다.
- 국가, 설비, Train, Pipeline, 에너지원 같은 대상을 canonical identity에 연결한다.
- 원문 표현과 canonical identity를 함께 보존한다.
- 절대값, 증감량, 증감률, 비중, 지수, 용량, 가동 상태를 구분한다.
- 숫자의 단위와 적용 기간을 함께 보존한다.
- 각 사실을 실제 source record에 연결한다.
- 모호함, 충돌, 미확정 범위를 숨기지 않고 명시적인 진단으로 남긴다.

### Event 구조화가 하지 않는 일

- `parameterName`, model file/sheet/table 또는 model slot을 선택하지 않는다.
- Impact Lever code를 원문 사실처럼 만들어 넣지 않는다.
- Scenario의 미래 선택값이나 최종 제안값을 미리 결정하지 않는다.
- 미래 예상이나 기관 View를 확정 사실로 승격하지 않는다.
- 상충하는 전망을 평균, 다수결, 최신값 우선 또는 confidence 점수만으로 해소하지 않는다.
- 유사 문자열, 같은 국가, 같은 용량만으로 asset을 임의 연결하지 않는다.
- delta나 비율만 있는 사실을 근거 없이 최종 절대값으로 변환하지 않는다.
- incomplete PowerMix를 합계 1로 임의 재정규화하지 않는다.
- Stage, 프로젝트, 지역 단위 사실을 하위 Train 전체로 묵시적으로 확장하지 않는다.
- v4 입력이 부족할 때 legacy dimension mapping이나 과거 proposal을 fallback으로 사용하지 않는다.

## 3. 구조화 완료 수준

Event 전체에 하나의 성공/실패 값을 주지 않고, 증적 항목별로 다음 수준을 기록한다.

| 수준 | 의미 | downstream 사용 범위 |
| --- | --- | --- |
| `NARRATIVE_ONLY` | 주제는 알 수 있지만 대상·기간·측정 의미가 모호함 | Event 조회·요약만 가능 |
| `SCENARIO_READY` | 영향 대상, 방향, 대략적 기간과 전달 경로를 설명 가능 | Scenario impact와 열린 질문 생성 가능 |
| `EXACT_SCOPE_READY` | canonical 대상과 model 시간 grain까지 exact하게 구조화됨 | Model Parameter slot 후보 탐색 가능; 실제 horizon 내 slot 존재 여부는 downstream이 판정 |
| `QUANTIFIED_READY` | exact 대상·기간에 단위와 값 의미가 명확한 수치가 있음 | 값 제안 시 강한 정량 근거로 사용 가능 |

`EXACT_SCOPE_READY`가 아니어도 중요한 Event일 수 있다. 이 경우 Scenario는 생성할 수 있지만 Model Parameter
proposal은 정상적으로 보류될 수 있다. 구조화 단계가 성공률을 높이기 위해 모호한 정보를 꾸며서는 안 된다.

## 4. 목표 증적 계약

권장 형태는 Event 본문과 분리된 versioned JSON이다. 필드명은 구현 협의에서 바꿀 수 있지만 의미와 불변식은
유지한다.

```json
{
  "schemaVersion": "event-evidence-v1",
  "eventId": 1475,
  "asOf": "2026-09-18T00:00:00Z",
  "entityCatalogVersion": "energy-assets-2026-09",
  "evidenceItems": [
    {
      "evidenceId": "ev-1475-f1",
      "claimText": "기관 A는 Freeport LNG Train 1의 가동 차질이 2027년 5월까지 지속될 것으로 전망했다.",
      "claimType": "institutional_view",
      "certaintyStatus": "forecast",
      "sourceRecordIds": [91001, 91004],
      "observedAt": "2026-09-17T13:00:00Z",
      "attribution": {
        "organizationId": "org-a",
        "organizationName": "기관 A",
        "publicationDate": "2026-09-17",
        "viewLabel": "base_case",
        "methodology": null
      },
      "effectivePeriod": {
        "start": "2027-04-01",
        "end": "2027-05-31",
        "precision": "month",
        "openEnded": false
      },
      "geographies": [
        {
          "role": "affected",
          "countryCode": "US",
          "canonicalName": "United States",
          "sourceName": "미국"
        }
      ],
      "entities": [
        {
          "entityType": "lng_train",
          "canonicalId": "lng-train-freeport-t1",
          "canonicalName": "Freeport LNG T1",
          "sourceName": "Freeport Train 1",
          "parentEntityIds": ["lng-plant-freeport"],
          "matchMethod": "approved_alias"
        }
      ],
      "metric": {
        "metricType": "lng_train_utilization",
        "value": null,
        "unit": "fraction",
        "valueSemantics": "unknown"
      },
      "change": {
        "direction": "disrupt",
        "directionSubject": "operational_state",
        "magnitude": null,
        "unit": null,
        "comparisonBasis": null
      },
      "scope": {
        "kind": "exact_entity",
        "memberEntityIds": ["lng-train-freeport-t1"],
        "expansionBasis": null
      },
      "readiness": "EXACT_SCOPE_READY",
      "diagnostics": []
    }
  ],
  "unresolvedQuestions": []
}
```

### 4.1 공통 필드 불변식

| 필드 | 필수 규칙 |
| --- | --- |
| `schemaVersion` | 의미가 바뀌면 version을 올린다. 같은 version에서 필드 의미를 바꾸지 않는다. |
| `evidenceId` | Event 안에서 고유하고 재처리 시 안정적이어야 한다. |
| `claimText` | 원문에 근거한 한 가지 사실 또는 주장만 담는다. 서로 다른 대상·기간·수치·발화 주체는 항목을 분리한다. |
| `claimType` | `historical_fact`, `current_observation`, `announced_plan`, `future_expectation`, `institutional_view` 중 정보의 역할을 기록한다. |
| `certaintyStatus` | `confirmed`, `reported`, `estimated`, `forecast`, `opinion` 중 원문이 부여한 확실성 수준을 기록한다. `reported`는 보도의 존재가 확인됐다는 뜻이지 보도된 미래가 확정됐다는 뜻이 아니다. |
| `sourceRecordIds` | 비어 있지 않아야 한다. 서로 다른 출처가 충돌하면 한 항목으로 평균하지 않고 별도 evidence로 보존한다. |
| `observedAt` | 해당 정보가 관측·발표된 시점이다. Event `occurredAt`이나 미래 적용 기간과 혼용하지 않는다. |
| `attribution` | 미래 예상·기관 View에는 발화 주체와 발행일을 필수로 둔다. 출처 매체와 전망 작성 기관을 구분하고, 확인 가능한 경우 view label·방법론을 보존한다. |
| `effectivePeriod` | 영향이 적용되는 기간이다. `start/end/precision/openEnded`를 함께 기록한다. 연·분기·월·일 precision을 보존한다. |
| `geographies` | 국가 중심 모델 축에는 canonical 국가명과 안정적인 코드를 함께 둔다. 지역만 확인되면 국가를 임의 분배하지 않는다. |
| `entities` | canonical ID/name과 원문명, match 방법을 함께 보존한다. |
| `metric` | metric 종류, 값, 단위, 값 의미를 한 묶음으로 기록한다. 값이 없으면 `null`로 두되 metric 종류를 꾸미지 않는다. |
| `change` | 방향과 변화량을 분리한다. 방향은 `increase`, `decrease`, `disrupt`, `recover`, `unchanged` 중 하나이며 `directionSubject`로 metric 변화인지 운영 상태인지 명시한다. 수급 방향을 원문 metric 방향으로 대신하지 않는다. |
| `scope` | exact 단일 대상, 명시된 대상 집합, 상위 그룹, 지역 중 무엇인지 구분한다. |
| `readiness` | 구조화 결과의 실제 완성도를 기록한다. confidence 점수로 필수 필드 누락을 덮지 않는다. |
| `conflictGroupId` | 동일 비교 기준에서 양립하기 어려운 주장을 묶는다. 같은 Event라는 이유만으로 모든 전망을 한 group으로 만들지 않는다. |
| `diagnostics` | 누락, 모호함, 충돌, 승인되지 않은 alias를 reason code로 남긴다. |

### 4.2 주장 유형과 시간 규칙

`claimType`과 `certaintyStatus`는 서로 다른 축이다. `claimType`은 정보가 과거 기준점인지 미래 선택지인지를,
`certaintyStatus`는 원문이 그 내용을 어느 수준으로 단정하는지를 나타낸다. 기관이 강하게 표현한 전망도
`institutional_view + forecast`이지 `historical_fact + confirmed`가 아니다.

| `claimType` | 판단 기준 | Scenario에서의 기본 역할 |
| --- | --- | --- |
| `historical_fact` | 이미 발생했고 신뢰 가능한 출처로 확인된 사실 | 현재 상태와 인과 경로의 anchor |
| `current_observation` | 기준시점 현재의 측정·운영 상태 | 현재 상태 anchor와 변화 출발점 |
| `announced_plan` | 주체가 공식 발표한 계획·일정 | 발표 사실은 anchor, 계획의 실제 이행은 미래 불확실성 |
| `future_expectation` | 운영사·정부·시장 참여자의 미래 예상 | 조건부 미래 가정 또는 Dimension value 근거 |
| `institutional_view` | 기관·리서치 조직의 전망·시나리오 | 출처가 명시된 대안 미래 가정 |

공식 발표도 두 층으로 읽는다. “운영사가 9월 1일 재가동 계획을 발표했다”는 발표 발생 사실이지만, “10월에
재가동된다”는 내용은 아직 미래 계획이다. 하나의 evidence item에 두 의미를 섞지 않고 필요하면 별도 claim으로
분리한다.

- `occurredAt`: 사건이 발생한 시각
- `observedAt`: 출처가 사실을 관측·발표한 시각
- `effectivePeriod`: 모델 영향이 적용될 수 있는 기간
- `asOf`: 구조화 판단 기준 시각

네 시각은 서로 대체할 수 없다. “향후 6개월”은 `asOf` 또는 원문 기준일이 명확할 때만 절대 기간으로
변환한다. “내년”, “Q2”, “여름”처럼 calendar anchor가 필요한 표현은 anchor와 해석 결과를 함께 보존한다.
anchor가 없으면 `SCENARIO_READY`까지만 허용하고 임의 Year/Month를 만들지 않는다.

미래 전망에서 `observedAt`은 전망이 발표·수집된 시각이고 `effectivePeriod`는 전망 대상 기간이다. 최신 발표가
과거 발표보다 늦다는 이유만으로 자동 우선하지 않는다. 같은 주체가 이전 전망을 공식 수정했다고 명시한 경우에만
`supersedes` 관계를 둘 수 있다.

명시 기간이 `2027 Q2`이면 2027년 4~6월에는 사용할 수 있지만 12월에는 사용할 수 없다. 여러 기간이 있으면
하나의 넓은 범위로 합치지 말고 사실별로 보존한다.

### 4.3 상충 전망 식별 규칙

상충 여부는 먼저 다음 comparison key를 정규화한 뒤 판단한다.

```text
metricType + canonical 대상/지역 + forecast subject + comparison horizon/basis + unit + valueSemantics
```

같은 key에서 값, 방향, 복구 시점 또는 운영 상태가 동시에 성립하기 어려우면 각 claim을 그대로 보존하고 동일한
`conflictGroupId`에 연결한다. 일반 수치 전망은 유효 기간이 겹치거나 같은 horizon을 가리킬 때 비교한다. 반면
`restart_timing`, `outage_duration`처럼 시점·기간 자체가 비교 대상이면 서로 다른 `effectivePeriod`가 바로
divergence 값이므로 key에서 제외한다. 기간·단위·대상·metric 의미가 달라 직접 비교할 수 없으면 상충으로
단정하지 않고 `INCOMPARABLE_CLAIMS`로 남긴다.

claim 간 관계는 근거가 있을 때만 `supports`, `contradicts`, `supersedes`, `refines`, `independent` 중 하나로
표현한다. 다음 처리는 금지한다.

- 수치 평균 또는 방향 다수결로 하나의 전망 만들기
- 가장 최근 전망이나 confidence가 높은 전망으로 나머지 덮어쓰기
- 기관명을 지운 채 “시장 전망”으로 합치기
- 한 출처가 다른 출처를 수정한 것처럼 `supersedes` 처리하기
- 서로 다른 전망 기간을 하나의 넓은 기간으로 합쳐 가짜 충돌 만들기

상충하는 각 claim은 독립적으로 `EXACT_SCOPE_READY` 또는 `QUANTIFIED_READY`일 수 있다. 이는 전망 간 충돌이
해소됐다는 뜻이 아니다. Event 수준에는 별도로 `conflictStatus=unresolved|partially_resolved|resolved`를 두어
Scenario가 아직 표현해야 할 불확실성을 알 수 있게 한다.

### 4.4 대상 식별 규칙

`matchMethod`는 다음 값만 사용한다.

- `exact`: canonical name/code와 원문이 정확히 일치
- `approved_alias`: 승인된 일대일 alias로 연결
- `approved_group_expansion`: 원문이 명시한 그룹을 승인된 member 집합으로 확장
- `unresolved`: 후보가 복수이거나 정본이 없어 미확정

fuzzy score만으로 `exact`를 만들지 않는다. `approved_group_expansion`은 확장된 모든 member ID와 mapping
version, 확장 근거를 남겨야 한다. 예를 들어 “Corpus Christi Stage 3”을 T1~T6으로 확장하려면 실제 asset
registry가 그 관계를 소유해야 하며, 문자열 유사도나 같은 용량을 근거로 삼지 않는다.

## 5. 증적 묶음별 구조화 기준

현재 14개 proposal capability는 다음 여덟 증적 묶음으로 다룬다. Event 구조화 단계는 오른쪽 파라미터명을
출력하지 않고, 각 묶음의 metric/entity contract를 채운다. 파라미터명은 coverage 설명을 위한 참고다.

| 증적 묶음 | 핵심 model grain | downstream coverage |
| --- | --- | --- |
| 국가·기간 단일값 | Country + Year 또는 Country + Year + Month | GDP, PMI, Population, Temperature, SupplyDisruption |
| 구성비·벡터 | Country + Year + 전체 구성원 | PowerMix |
| LNG 물리 자산 | Country + Plant + Train + Year + Month | LiqUtilAdjustment, LiqProdAdjustment |
| Pipeline 네트워크 | Pipeline + From/To Country + Year + Month | PipelineAdjustment |
| 재해·영향 시설 | US GoM + Year + Month + approved facility evidence | HurricaneIntensity |
| 최종 수요 override | Country + Year + Month + Demand Sub-Sector | User-Adjusted Gas Demand |
| Regas 물리 자산 | Continent + Region + Country + Regasification Plant + Lifecycle + Nameplate + Year + Month | RegasAdjustment |
| 중류 계약·운송비 | From/To Country + Year 또는 global Year | PNG Contract Volume, ShippingCost |

### 5.1 국가·기간 단일값 묶음

공통 필수 정보는 canonical Country, effective Year/Month, metric type, 값 의미, 단위, 방향과 source lineage다.
연 단위 근거를 월 단위로 임의 복제하거나, 지역 전망을 구성 국가 전체에 자동 배분하지 않는다.

| metric family | 필요한 구조화 정보 | 주의할 의미 차이 |
| --- | --- | --- |
| 연간 경기·인구 | 국가, 적용 연도, 전망/관측 상태, 수치와 단위 | 실질 GDP 성장률은 fractional YoY growth이고, 인구는 천 명 단위 최종 절대값이다. 일반 경기 기사를 인구 변화로 해석하지 않는다. |
| 월간 산업·기상 | 국가, 적용 연월, 지수/온도 수치, 관측 또는 전망 기준 | PMI는 절대 index이고 Temperature는 월평균 °C다. 폭염이 수요를 늘린다는 사실과 Temperature 값의 증감 방향은 같은 개념이 아니다. |
| 월간 upstream 공급 | 생산 국가, 적용 연월, upstream 범위, 공급량/변화량 단위 | downstream 제안값은 최종 공급량 `Mt`다. “10 Mt 차질”을 “최종 공급량 10 Mt”로 바꾸지 않는다. LNG 액화 Train 차질과 구분한다. |

숫자가 delta나 비율뿐이면 `metric.valueSemantics`를 `delta` 또는 `percentage_change`로 유지한다. 기준값이 같은
evidence에 명시적으로 연결되어 있을 때만 `derivedFinalValue`를 별도 필드로 계산하고 계산식·입력 evidence ID를
남긴다.

`change.direction`은 `directionSubject`가 가리키는 metric 또는 운영 상태의 방향이다. 예를 들어 기온 상승과
가스 수요 증가는 별도 사실이며, Scenario 단계가 계절·지역·용도에 따라 전달 경로를 판단한다.

### 5.2 구성비·벡터 묶음

발전 구성 변화는 한 에너지원만 독립적으로 보는 scalar가 아니다. 최소한 다음을 구조화한다.

- canonical Country와 적용 Year
- 영향을 받는 Energy Source
- 증가하는 구성원과 이를 상쇄하는 감소 구성원
- 원문이 제공한 share의 단위(`fraction` 또는 `%`)
- 전체 vector인지 일부 member만 다룬 partial evidence인지
- 수치가 있는 경우 member별 원본 정밀도

현재 downstream atomic vector 구성원은 `Liquids`, `Hydro`, `Solar`, `Wind`, `Bioenergy`, `Gas`, `Coal`,
`Nuclear`, `Geothermal`, `Other`다. Event가 일부 구성원만 언급하면 `PARTIAL_VECTOR`로 기록하고 나머지 share를
임의 생성하거나 합계 1로 정규화하지 않는다. Scenario 단계는 이 사실로 발전원 전환 방향을 만들 수 있지만,
Model Parameter 값 제안은 전체 exact vector 계약을 별도로 충족해야 한다.

에너지원 명칭 alias는 versioned taxonomy로 관리한다. 예를 들어 `natural gas`, `gas-fired`를 `Gas`로 연결할
수는 있지만, 문맥상 발전 연료가 아닌 가스 수요를 PowerMix 구성원으로 연결해서는 안 된다.

### 5.3 LNG 물리 자산 묶음

LNG 설비는 최소 `Country → LNG Plant → LNG Plant Train` 계층과 적용 Year/Month가 필요하다. 다음 정보를 한
evidence item 또는 명시적으로 연결된 evidence 묶음에서 확인할 수 있어야 한다.

- Plant와 Train의 canonical ID/name
- 원문명과 canonical 연결 방법
- 운영 상태와 lifecycle: Operational, Planned, Under Construction, FID, Closed 등
- 차질·감소·회복·증가 방향
- 적용 시작/종료 기간
- 영향 형태: 부분 가동률 변화인지, 생산량 직접 override인지
- 원문에 수치가 있다면 이용률 fraction인지 월 생산량 `Mt LNG/month`인지
- 유지보수, feedgas, shipment, 사고, ramp-up 등 원인과 실제 영향을 구분한 사실
- 운영사 계획과 기관별 전망의 발화 주체, 기준시점, 전제조건

단기·부분 운영 변화는 utilization 성격이고, 대폭·장기 생산 손실, 신규 Train ramp-up, 명시적 생산량 전망은
production override 성격이다. Event 구조화는 이 구분에 필요한 `impactMode`를 다음처럼 기록하되 최종
parameter를 선택하지 않는다.

- `utilization_change`
- `production_override`
- `capacity_change`
- `startup_or_ramp_up`
- `unknown`

원문에 기록된 utilization 값이 1을 초과해도 구조화 단계에서 1로 clamp하지 않고 원 값과 단위를 보존한다.
생산량, 이용률 또는 capacity 중 어떤 metric인지 불명확하면 서로 변환하지 않고 `METRIC_SEMANTICS_UNKNOWN`을
남긴다.

예를 들어 설비 중단은 이미 확인됐지만 재가동 시점에 대해 운영사는 10월, 기관 A는 12월을 예상할 수 있다.
중단 사실은 현재 anchor이고, 10월·12월은 별도 미래 claim이다. 두 시점을 하나의 “11월 예상”으로 평균하지
않으며, Scenario 단계에서 시장 영향이 다른 복구 timing value의 근거로 전달한다.

Plant만 확인되고 Train이 확인되지 않은 경우 다음 중 하나로 처리한다.

1. 원문이 Plant 전체 영향을 명시하고 asset registry가 현재 적용 가능한 Train 집합을 제공하면
   `approved_group_expansion`으로 member를 기록한다.
2. 특정 Train인지 Plant 전체인지 모호하면 `AMBIGUOUS_ASSET_SCOPE`로 남긴다.
3. 같은 이름의 후보가 복수이면 `unresolved`로 남긴다.

2·3번은 Scenario 생성에는 사용할 수 있지만 exact Train slot 근거로 사용하지 않는다. 시설명과 기간이 다른
provenance에 흩어져 있으면 합쳐서 하나의 exact 증적으로 만들지 않는다. 하나의 coherent evidence lineage가
Plant, Train, 기간과 source Event를 함께 뒷받침해야 한다.

### 5.4 Pipeline 네트워크 묶음

Pipeline은 이름만으로 식별하지 않고 다음 tuple을 하나의 route identity로 취급한다.

```text
Pipeline canonical ID/name + From Country + To Country + flow direction
```

필수 구조화 정보는 exact Pipeline, 양 끝 국가, 적용 Year/Month, 변화 방향, metric 의미와 단위다. 다음 개념은
구분한다.

- physical send-out capacity
- actual throughput/flow
- contracted volume
- LNG 해상 route 상태
- 일반적인 국경 또는 지정학적 긴장

현재 proposal capability는 최종 송출용량 `Mt/y`를 대상으로 한다. throughput 감소 기사나 계약량 변경을
capacity 변경으로 승격하지 않는다. 여러 segment 또는 양방향 노선이면 영향 segment와 방향을 분리한다.
노선명이 없고 From/To만 있는 경우 복수 후보가 남으면 `AMBIGUOUS_NETWORK_ASSET`으로 기록한다.

### 5.5 재해·영향 시설 묶음

허리케인 증적은 일반 기상 Event와 물리 공급 차질을 연결하는 별도 묶음이다. 최소 다음을 구조화한다.

- hazard type과 storm canonical identity/name
- 미국 Gulf of Mexico 영향 여부
- 발생/예상 Year와 Month
- 강도 scale, 원 수치, 단위와 출처
- 영향을 받는 approved facility의 canonical ID/name
- 시설 영향이 관측, 발표, 전망 중 무엇인지
- shutdown, evacuation, production loss 등 영향 종류

현재 downstream intensity는 0~4 정수지만, Event 구조화 단계가 Saffir–Simpson category나 풍속을 임의로 0~4로
변환해서는 안 된다. 승인된 변환 계약이 있을 때만 `normalizedMetric`에 변환 version과 계산 근거를 남긴다.
GoM 언급만 있고 영향 시설이 없거나, 시설만 있고 허리케인과의 인과 연결이 없으면 exact proposal evidence가
아니다. 기타 지역의 태풍·홍수·지진은 HurricaneIntensity로 억지 연결하지 않고 실제 영향을 받는 asset 증적
묶음으로 보낸다.

### 5.6 최종 수요 override 묶음

일반적인 수요 증가 기사만으로 최종 수요값을 만들지 않는다. Country, 적용 Year/Month, Demand Sub-Sector가
모두 exact해야 하며, `BCM` 기준의 최종 절대 수요값 또는 이를 계산할 수 있는 동일 lineage의 기준값·변화량이
필요하다. 산업용·발전용·주거용처럼 원문에 없는 하위 부문을 추정 배분하지 않는다. 기온·경기·발전믹스 변화는
각자 별도 증적 묶음이며, 그 영향 방향만으로 User-Adjusted Gas Demand의 숫자를 중복 제안하지 않는다.

미래 수요 전망이 여러 기관에서 충돌하면 기관별 claim과 전제를 유지한다. 예를 들어 같은 국가·월·부문에 대해
정책기관은 절대 수요 8 BCM, 리서치기관은 6 BCM을 제시할 수 있다. 둘을 평균하지 않고 Scenario value의 서로
다른 수요 상태를 지지하는 증적으로 전달한다. exact Basecase row가 없는 국가·월·부문은 Event 구조화가 새
model row를 만들지 않는다.

### 5.7 Regas 물리 자산 묶음

재기화 증적은 LNG 액화 Train이나 Pipeline과 분리한다. 최소한 canonical Continent, Region, Country,
Regasification Plant, Life Cycle Category, Nameplate capacity, 적용 Year/Month와 `Mt LNG/month` 기준 최종
절대 재기화 능력의 근거가 필요하다. 터미널 총용량, send-out, 실제 이용량, 증설 계획, 운영 개시 예상은 서로
다른 metric이므로 원문의 의미를 보존한다.

증설이 확정된 과거 사실이어도 미래 가동 개시월은 운영사 계획과 기관 View가 다를 수 있다. 건설·FID 사실은
anchor로, 개시 시점과 월별 가용능력은 별도 미래 claim으로 둔다. asset registry에 승인된 exact Plant와
Lifecycle/Nameplate 조합이 없으면 유사 터미널이나 같은 국가의 row로 대체하지 않는다. downstream은 기존
matrix cell만 제안할 수 있으므로, Event 구조화가 새 설비 row나 월 열을 암묵적으로 생성해서는 안 된다.

### 5.8 중류 계약·운송비 묶음

이 묶음에는 국가 간 PNG 계약물량과 전 세계 LNG charter rate가 함께 들어오지만 grain과 단위를 섞지 않는다.

| metric family | 필요한 구조화 정보 | 금지되는 해석 |
| --- | --- | --- |
| PNG 계약물량 | 적용 Year, From Country, To Country, 계약 당사자·상태, `Mt LNG` 최종 절대 계약물량 또는 명시적 변화량 | 실제 flow·pipeline capacity·LNG cargo를 계약물량으로 대체하거나 오래된 BCM 표기를 자동 변환 |
| LNG 운송비 | 적용 Year, global charter-rate benchmark의 정의, `$ / d` 절대값, 선형·기간·출처 | 특정 항로 freight, 선박 자산가치, bunker cost를 global ShippingCost로 승격 |

계약 체결·해지·갱신은 확정 상태와 미래 이행 전망을 분리한다. 계약서상 ACQ가 확정돼도 실제 개시연도나
ramp-up은 전망일 수 있다. 운송비 역시 현재 spot 관측과 향후 연평균 기관 전망을 별도 claim으로 둔다. 이 두
metric 모두 등록 LUT가 없는 exact Basecase-only 경로이므로, Event 구조화가 근사 route·인접 연도·다른 운임
benchmark로 빈 slot을 보충하지 않는다.

## 6. Scenario Group Agent Output 설계 가이드

### 6.1 Agent의 판단 관점

Scenario Group Agent는 미래를 확정하거나 기관 전망의 승자를 고르는 주체가 아니다. 다음 세 관점을 유지한다.

1. **증적 정리자**: 확정·관측 사실은 현재 상태의 anchor로, 미래 예상과 기관 View는 출처가 있는 claim으로
   구분한다.
2. **분기 설계자**: 상충 claim이 실제 시장 영향 차이를 만들면 Scenario의 uncertainty와 Dimension value로
   표현한다. 기관 수나 평균값으로 합의 전망을 만들지 않는다.
3. **lineage 관리자**: Event → claim/fact → Impact Path → uncertainty → Dimension value → Scenario 선택의
   연결을 보존한다. Model Parameter에는 선택된 value의 Lever state만 전달한다.

LLM은 문장 해석, claim 분류 후보, 인과 경로와 Scenario 설명을 제안할 수 있다. 서버는 ID, source membership,
comparison key, conflict 관계, catalog pin, Lever binding을 결정적으로 검증하고 부여한다. LLM이 새 출처·기관·
수치·관계를 만들어서는 안 된다.

### 6.2 현재 v4 Output 필드 사용법

아래 필드는 현재 v4 생성 결과에 존재하는 필드다. 미래 claim 전용 필드가 아직 없으므로, 기존 필드를 다음
의미로 제한해야 한다.

표의 `impactAnalysis.*`는 graph 내부 `V4GenerationResult` 기준 경로다. 현재 create API·persistence에서는 같은
내용이 `generationDiagnostics.eventFacts`, `impactPaths`, `pathUncertainties` 등의 평탄화된 진단 필드로
projection된다. 공개 응답에 nested `impactAnalysis`가 이미 존재한다고 해석하면 안 된다.

| 현재 Output | 만들어내는 관점과 방식 |
| --- | --- |
| `impactAnalysis.eventFacts[]` | `observedBasis`, `observedAt`으로 확정 과거와 현재 관측만 기록한다. “기관 A가 전망을 발표했다”는 발표 행위는 사실일 수 있지만 전망 내용 자체를 현재 사실로 넣지 않는다. |
| `impactAnalysis.decisionBasis[]` | Scenario 판단에 실제 사용한 수치·기간·출처를 간결히 설명한다. 현행 스키마에서 미래 claim을 언급해야 할 때는 반드시 `누가/언제/어느 기간을/어떤 조건으로 전망했는지`를 함께 쓴다. 이는 전용 lineage 필드가 생기기 전의 보조 표현이지 fact 승격 수단이 아니다. |
| `impactAnalysis.eventExclusions[]` | 현재 계약의 `no_usable_fact`, `no_material_impact`처럼 Event 전체를 분석에서 제외할 때만 쓴다. 개별 미래 claim의 제외나 상충 해소를 여기에 넣지 않는다. |
| `impactAnalysis.impactPaths[]` | 확인된 anchor에서 시장 영향으로 이어지는 인과를 만들고 `sourceFactIds`를 연결한다. `leverSteps[].scope/timing`은 구조화 entity/effective period를 우선 사용한다. 미래 claim만이 지지하는 경로라면 그 조건부 성격을 mechanism과 uncertainty에서 드러낸다. |
| `impactAnalysis.pathUncertainties[]` | 같은 Path의 규모·범위·시점·지속기간·복구·대체 가능성에 대한 미래 예상과 기관 View 차이를 표현한다. `impactPathIds`, `affectedLeverCode`, `axisType`, `subject`, `reason`, `materiality`가 claim 차이를 실제로 가리켜야 한다. |
| `impactAnalysis.interactions[]`, `interactionUncertainties[]` | 여러 Event 또는 Path의 결합 여부·증폭·완화가 불확실할 때만 만든다. 한 Event 내부의 전망 충돌은 기본적으로 path uncertainty이며, 별도 Event 간 관계가 있을 때 interaction uncertainty로 올린다. |
| `dimensionDefinitions[]` | 시장 결과를 materially 나누는 불확실성을 3~6개 축으로 만든다. `sourceEventIds`, `sourceImpactPathIds`, `sourceUncertaintyIds`를 보존하고 `primaryLeverCode`, `primaryImpactLeverId`는 pinned catalog에서 hydrate한다. 기관 이름이 아니라 복구 시점·가동 수준·물량 등 의미 상태를 Dimension으로 삼는다. |
| `dimensionDefinitions[].values[]` | 상충 claim을 2~4개의 양립 가능한 미래 상태로 묶는다. 같은 상태를 말하는 여러 기관 View는 하나의 value를 함께 지지할 수 있고, 한 기관이 낸 materially 다른 case는 서로 다른 value가 될 수 있다. |
| `values[].leverStates[]` | 해당 value를 선택했을 때의 미래 Lever 상태만 기록한다. `scope`와 `timeWindow`는 claim의 exact 대상·적용기간에서 만들며, 전망값을 관측 사실처럼 표현하지 않는다. |
| `values[].assumptionRationale` | `확인된 anchor → 채택한 미래 claim/가정 → 시장 영향` 순서로 설명한다. 기관 View를 사용하면 기관명, 전망 기준일, 대상 기간을 명시한다. |
| `scenarios[]` | Dimension value의 고유 조합을 만든다. Scenario는 여러 claim 중 일부를 조건부로 채택한 미래 branch이며 모든 미선택 claim이 거짓이라는 판정이 아니다. `baselineYn=Y`도 확정 미래나 기관 합의를 뜻하지 않는다. |
| `excludedDimensions[]` | 현재는 문자열 목록이므로 미채택 Dimension의 사람이 읽을 수 있는 설명만 남긴다. claim-level lineage 저장소로 간주하지 않는다. |
| `validationWarnings[]` | `stage`, `code`, `message`, `referenceIds`로 attribution·기간·metric 의미 누락, fact 승격, 미표현 conflict를 경고한다. claim ID가 도입되면 `referenceIds`에 연결한다. |
| `generationDiagnostics` | 현재 fact/path/uncertainty, 제외, warning, catalog/coverage와 Additional Dimension 상태를 저장·응답하는 진단 경계다. claim 전용 필드는 아직 없으므로 lossless conflict snapshot을 넣으려면 아래 추가안에 맞춰 이 schema도 명시적으로 확장해야 한다. |

현재 `V4EventFact`에는 `factId`, `eventId`, `observedBasis`, `observedAt`만 있고 claim type, attribution,
conflict group을 직접 담는 필드는 없다. 따라서 추가 스키마가 구현되기 전에도 미래 예상·기관 View를
`eventFacts`에 밀어 넣어 손실을 감추면 안 된다. upstream `structuredEvidence`, uncertainty lineage,
`assumptionRationale`, validation warning을 호환 경로로 사용한다. 다만 이것만으로 claim-level lineage가 완전히
보존되지는 않는다. lossless 처리는 다음 추가 필드와 `generationDiagnostics` schema 확장이 구현돼야 완성된다.

### 6.3 추가 권장 Output 필드

다음은 **현재 공개 API에 구현됐다고 간주하면 안 되는 추가안**이다. 도입 시 API version, Pydantic schema,
persistence, Presentation projection과 consumer를 함께 변경해야 한다. 기존 `eventFacts`를 과부하하기보다
additive `evidenceClaims`를 두는 방식을 권장한다.

| 추가 Output | 최소 내용 | 목적 |
| --- | --- | --- |
| `impactAnalysis.evidenceClaims[]` | `claimId`, `eventId`, `claimType`, `certaintyStatus`, `claimText`, `observedAt`, `effectivePeriod`, metric/entity/scope, `sourceRecordIds`, attribution | 사실과 미래 claim을 같은 lineage 체계에서 구분 |
| `impactAnalysis.claimRelations[]` | `fromClaimId`, `toClaimId`, `relation`, `reason` | `supports/contradicts/supersedes/refines/independent` 관계를 명시 |
| `impactAnalysis.conflictGroups[]` | `conflictGroupId`, comparison key, `memberClaimIds`, divergence type, `resolutionStatus` | 한 Event 안의 복수 View를 비손실 보존하고 Scenario 반영 여부 추적 |
| `dimensionDefinitions[].sourceClaimIds` | Dimension이 다루는 claim ID 집합 | Event 단위보다 세밀한 uncertainty lineage |
| `dimensionDefinitions[].values[].sourceClaimIds` | 해당 의미 상태를 직접 지지하는 claim ID 집합 | 기관 View와 Dimension value의 연결 보존 |
| `values[].leverStates[].sourceClaimIds` | 개별 Lever 상태의 대상·기간·방향을 지지하는 claim ID 집합 | 하나의 value에 여러 Lever가 있을 때 근거 혼합 방지 |
| `values[].leverStates[].evidenceMode` | `observed_anchor`, `forward_assumption`, `institutional_view` | Lever state가 관측값인지 조건부 미래 가정인지 구분 |
| `scenarios[].adoptedClaimIds` | Scenario 조합이 조건부로 채택한 claim ID | Scenario 서술과 원 전망 간 추적성 제공 |
| `impactAnalysis.conflictCoverage` | represented/unrepresented conflict group ID와 미반영 이유 | 중요한 충돌의 silent drop 방지 |

권장 개념 예시는 다음과 같다.

```json
{
  "evidenceClaims": [
    {
      "claimId": "claim-outage-observed",
      "eventId": 1475,
      "claimType": "current_observation",
      "certaintyStatus": "confirmed",
      "claimText": "Freeport LNG Train 1은 2026년 9월 15일부터 중단 상태다.",
      "observedAt": "2026-09-17T13:00:00Z",
      "effectivePeriod": {"start": "2026-09-15", "end": null},
      "sourceRecordIds": [91001]
    },
    {
      "claimId": "claim-restart-operator",
      "eventId": 1475,
      "claimType": "announced_plan",
      "certaintyStatus": "forecast",
      "claimText": "운영사는 2026년 10월 전면 재가동을 예상한다.",
      "observedAt": "2026-09-17T13:00:00Z",
      "effectivePeriod": {"start": "2026-10-01", "end": "2026-10-31"},
      "sourceRecordIds": [91001],
      "attribution": {
        "organizationName": "운영사",
        "publicationDate": "2026-09-17"
      }
    },
    {
      "claimId": "claim-restart-org-a",
      "eventId": 1475,
      "claimType": "institutional_view",
      "certaintyStatus": "forecast",
      "claimText": "기관 A는 재가동이 2026년 12월까지 지연될 것으로 전망한다.",
      "observedAt": "2026-09-18T09:00:00Z",
      "effectivePeriod": {"start": "2026-12-01", "end": "2026-12-31"},
      "sourceRecordIds": [91004],
      "attribution": {
        "organizationName": "기관 A",
        "publicationDate": "2026-09-18"
      }
    }
  ],
  "conflictGroups": [
    {
      "conflictGroupId": "cg-restart-timing-1",
      "memberClaimIds": ["claim-restart-operator", "claim-restart-org-a"],
      "divergenceType": "timing",
      "resolutionStatus": "unresolved"
    }
  ]
}
```

`adoptedClaimIds`는 해당 Scenario가 가정으로 채택했다는 뜻이며 사실 판정이 아니다. 미선택 claim 전체를
`rejectedClaimIds`로 만드는 것은 피한다. 다른 Scenario에서 채택될 수 있거나 단지 현재 조합에 사용되지 않은
claim까지 거짓으로 오인될 수 있기 때문이다.

### 6.4 상충 View를 Dimension과 Scenario로 바꾸는 규칙

1. 먼저 확정·관측 사실을 공통 anchor로 고정한다. 이미 발생한 사실 자체를 미래 choice로 만들지 않는다.
2. comparison key가 같은 미래 claim을 conflict group으로 모으되 원문과 attribution은 각각 유지한다.
3. 기관별 문장을 그대로 value로 복사하지 않고 시장 영향을 구분하는 의미 상태로 정규화한다. 예를 들어
   `기관 A`, `기관 B`가 아니라 `10월 전면 재가동`, `11월 부분 회복`, `12월 이후 지연`으로 만든다.
4. 같은 의미 상태를 지지하는 복수 claim은 한 value의 `sourceClaimIds`에 함께 연결한다. 다른 전제·물량·기간을
   가진 전망은 별도 value로 둔다.
5. Baseline은 as-of 기준 가장 잘 지지되는 작업 branch 하나다. 다른 View를 폐기하거나 conflict를
   `resolved`로 바꾸지 않는다.
6. 3~6개 Dimension budget 때문에 material conflict를 넣지 못하면 `excludedDimensions`,
   `validationWarnings`, `conflictCoverage.unrepresented`와 Additional Dimension 후보 중 적용 가능한 경로에
   남긴다.
7. unresolved conflict가 있다는 이유만으로 모든 branch를 `INSUFFICIENT_EVIDENCE`로 만들지는 않는다. 사용자가
   선택한 value의 claim이 exact 대상·기간·metric 계약을 충족하면 그 branch의 근거가 될 수 있다. 반대로
   Dimension label이나 다수 기관의 동의만 있고 exact 증적이 없으면 Model Parameter 근거로 승격하지 않는다.

### 6.5 v4 전달·재현 규칙

1. Event impact의 fact/claim은 `evidenceId`, `claimId`, `sourceRecordIds` lineage를 가능한 가장 세밀한 수준으로
   유지한다.
2. Lever step의 `scope`와 `timing`은 구조화된 entity/effective period를 우선 사용한다.
3. 구조화 값이 없을 때만 기존 제목·요약·bullet·상세 분석을 보조 근거로 사용한다.
4. 구조화 증적과 자연어가 충돌하면 조용히 한쪽을 선택하지 않고 validation warning을 남긴다.
5. selected value만 Model Parameter 후보에 기여하게 하고, 선택되지 않은 value의 증적을 섞지 않는다.
6. Event 구조화 단계의 metric type을 특정 Parameter와 일대일 고정하지 않는다. 최종 route는 pinned Impact
   Lever catalog의 binding과 applicability가 결정한다.
7. 기존 v4 Scenario Group은 저장된 catalog pin과 생성 결과를 유지한다. 구조화 schema나 entity catalog가
   바뀌었다고 기존 그룹을 조용히 재해석하지 않는다.

Event evidence version과 entity catalog version은 Scenario 생성 시 사용한 값으로 snapshot하거나
`generation_diagnostics`에 남겨야 한다. 같은 Event가 나중에 재구조화되면 신규 Scenario Group이 어떤 evidence
version을 사용했는지 재현할 수 있어야 한다.

## 7. 진단 reason code

진단은 free text만 남기지 말고 최소 다음 code를 사용한다.

| Code | 의미 |
| --- | --- |
| `MISSING_SOURCE_LINEAGE` | source record 연결이 없음 |
| `MISSING_EFFECTIVE_PERIOD` | 모델 영향 기간을 결정할 근거가 없음 |
| `AMBIGUOUS_TIME_ANCHOR` | 상대 기간의 기준일이 없음 |
| `MISSING_COUNTRY` | 국가 축이 필요한 사실에서 국가가 없음 |
| `AMBIGUOUS_ENTITY` | canonical entity 후보가 복수임 |
| `UNAPPROVED_ALIAS` | alias는 있으나 승인된 정본 매핑이 아님 |
| `AMBIGUOUS_ASSET_SCOPE` | Plant 전체와 특정 Train 범위를 구분할 수 없음 |
| `GROUP_SCOPE_NOT_EXPANDED` | 그룹 영향은 명시됐지만 member expansion 계약이 없음 |
| `AMBIGUOUS_NETWORK_ASSET` | Pipeline/segment/방향을 하나로 식별할 수 없음 |
| `METRIC_SEMANTICS_UNKNOWN` | 절대값·delta·비율 의미가 불명확함 |
| `UNIT_UNKNOWN` | 수치 단위를 확인할 수 없음 |
| `FINAL_VALUE_NOT_DERIVABLE` | 변화량만 있고 기준값이 없어 최종값을 만들 수 없음 |
| `PARTIAL_VECTOR` | 구성비 vector가 일부 member만 포함함 |
| `CONFLICTING_EVIDENCE` | 같은 대상·기간에 양립하기 어려운 출처가 있음 |
| `CLAIM_TYPE_UNKNOWN` | 확정 사실·계획·예상·기관 View 중 정보 역할을 구분할 수 없음 |
| `MISSING_ATTRIBUTION` | 미래 예상·기관 View의 발화 주체 또는 발행일이 없음 |
| `INCOMPARABLE_CLAIMS` | 대상·기간·단위·metric 의미가 달라 직접 비교할 수 없음 |
| `FORECAST_PROMOTED_TO_FACT` | 미래 claim이 현재·과거 사실로 잘못 분류됨 |
| `CONFLICT_NOT_REPRESENTED` | material conflict가 Scenario Dimension/value 또는 명시적 제외 진단에 반영되지 않음 |
| `HAZARD_SCOPE_UNVERIFIED` | GoM/시설/재해 연결 중 하나가 확인되지 않음 |

이 code들은 upstream 품질 진단이다. downstream의 `ABSTAINED_INSUFFICIENT_EVIDENCE`를 미리 출력하거나 대체하지
않는다. Scenario 선택 결과와 model slot 계약까지 적용한 최종 보류 판정은 Model Parameter Agent가 소유한다.

## 8. 예시

### 8.1 좋은 LNG 자산 증적

```text
원문: Freeport LNG Train 1의 계획정비가 연장되어 2027년 4~5월 가동률이 낮아질 전망이다.
```

- Plant: `Freeport LNG` exact/approved alias
- Train: `Freeport LNG T1` exact/approved alias
- effective period: 2027-04-01 ~ 2027-05-31, month precision
- lifecycle: Operational
- impact mode: utilization_change
- direction: decrease 또는 disrupt
- claim type: `future_expectation`; 전망 주체와 발행일을 attribution으로 기록
- source record lineage: 존재
- readiness: `EXACT_SCOPE_READY`; 이용률 수치까지 있으면 `QUANTIFIED_READY`

### 8.2 보강이 필요한 LNG 자산 증적

```text
원문: 미국 LNG 설비의 가동 차질이 당분간 이어질 수 있다.
```

- 국가는 알 수 있지만 Plant, Train, calendar period가 없음
- `AMBIGUOUS_ASSET_SCOPE`, `MISSING_EFFECTIVE_PERIOD`
- readiness: `SCENARIO_READY`
- Scenario에서 시설 범위와 기간을 열린 질문으로 만들 수 있으나 exact slot을 임의 선택하지 않음

### 8.3 좋은 국가·월 증적과 잘못된 변환

```text
원문: 2027년 2월 미국 upstream 생산이 기준 전망보다 2 Mt 감소할 전망이다.
```

올바른 구조화:

- Country=`United States`, Year=2027, Month=2
- metric=`upstream_production`, value semantics=`delta`, value=-2, unit=`Mt`
- 최종 upstream 공급량은 source에 없으므로 `FINAL_VALUE_NOT_DERIVABLE`

잘못된 구조화:

- 최종 공급량을 `2 Mt`로 기록
- `SupplyDisruption` 또는 특정 model target을 Event에 직접 기록

### 8.4 하나의 Event에 상충하는 LNG 전망이 있는 경우

```text
확인 사실: Freeport LNG Train 1은 2026년 9월 15일부터 중단 상태다.
운영사 계획: 2026년 10월 전면 재가동을 예상한다.
기관 A View: 복구가 2026년 12월까지 지연될 것으로 본다.
기관 B View: 2026년 11월 부분 가동 후 점진 회복을 예상한다.
```

구조화 결과는 중단 사실 하나와 미래 claim 세 개다. 세 미래 claim에는 각각 주체, 발표일, 적용기간,
운영 상태를 기록하고 `recovery_timing_and_level` conflict group으로 연결한다. 운영사의 발표가 공식이라는
이유만으로 10월 재가동을 확정 사실로 만들지 않고, 기관 전망끼리 평균해 11월 전면 재가동으로 만들지도 않는다.

Scenario Group Agent는 다음처럼 시장 의미에 따라 Dimension을 설계한다.

```text
Dimension: Freeport T1 복구 시점과 수준
Value A: 10월 전면 재가동      ← 운영사 계획 claim
Value B: 11월 부분 회복        ← 기관 B View claim
Value C: 12월 이후 재가동 지연 ← 기관 A View claim
```

각 value의 `assumptionRationale`에는 공통 anchor인 9월 15일 중단 사실과 해당 미래 claim의 attribution을 함께
쓴다. 구현 후에는 `sourceClaimIds`로 직접 연결한다. Scenario가 Value A를 채택하더라도 Value B·C는 거짓이나
해소된 전망이 아니며 다른 Scenario branch의 근거로 남는다.

## 9. 구현 순서

### Phase 1 — 기존 Event 필드 품질 개선

DB/API 변경 전에 제목·요약·bullet·상세 분석에 다음 내용을 명시적으로 유지한다.

- canonical 후보가 되는 원문 대상명
- 실제 적용 기간과 관측/발표 시점의 구분
- 수치, 단위, 절대값/변화량 의미
- source record별 사실 분리
- 확정·관측 사실과 미래 예상·기관 View의 문장 분리
- 미래 View의 발화 주체·발행일·전제조건과 상충 전망의 병렬 보존

태그만으로 exact 증적을 대체하지 않는다.

### Phase 2 — versioned `structuredEvidence` 도입

- Event 소유 schema와 persistence에 versioned JSON을 추가한다.
- raw source와 derived structure를 분리한다.
- entity resolver와 승인 alias/group expansion registry를 버전 관리한다.
- `claimType`, `certaintyStatus`, attribution, claim relation, conflict group을 versioned contract로 관리한다.
- Event 조회 DTO와 Scenario Group 입력에 structured evidence를 전달한다.
- 기존 Event는 evidence가 없는 상태로도 기존 text 경로에서 읽을 수 있게 한다. `structuredEvidence`가 없다는
  사실과 text 기반 readiness 평가는 구분하고, 구조화하지 않은 Event를 자동으로 `EXACT_SCOPE_READY`로 승격하지
  않는다.

### Phase 3 — Scenario v4 deterministic validation

- evidence/source Event membership을 검증한다.
- entity, period, metric semantics 충돌을 warning 또는 fail-closed로 분류한다.
- 미래 claim의 fact 승격을 차단하고 attribution·comparison key·conflict membership을 검증한다.
- Lever scope/time과 Dimension value lineage에 evidence/claim ID를 보존한다.
- material conflict가 Dimension/value 또는 명시적 제외 진단 중 어느 곳에도 없으면 검증 실패로 처리한다.
- exact 후보가 0/1/복수인지 LLM 선택 결과가 아니라 구조화 증적과 server-side catalog로 계산한다.

### Phase 4 — 운영 관측과 보정

- 증적 묶음별 `NARRATIVE_ONLY → SCENARIO_READY → EXACT_SCOPE_READY → QUANTIFIED_READY` 비율을 측정한다.
- Model Parameter의 abstain reason과 upstream 진단 code를 연결해 누락이 많은 필드를 찾는다.
- 승인 alias/group expansion 추가는 실제 실패 증적과 reviewer 승인을 거쳐 version을 올린다.
- fuzzy matching 임계값을 낮춰 성공률을 높이는 방식으로 보정하지 않는다.

## 10. 테스트와 완료 기준

### 공통 schema 테스트

- evidence ID와 source lineage 고유성
- occurred/observed/effective/as-of 시간 분리
- 상대 기간 anchor, 교차연도와 month precision
- absolute/delta/percentage/index/share 의미 보존
- raw 값과 normalized 값의 단위 변환 재현성
- 충돌 evidence 비병합
- 한 Event 안의 확정 과거·미래 예상·기관 View 동시 보존
- 미래 claim의 `observedAt`과 `effectivePeriod` 분리
- attribution 누락 진단과 서로 다른 기관 View의 비병합
- 수정 발표가 아닌 최신 View의 자동 `supersedes` 차단
- schema/entity catalog version 재현성

### 증적 묶음별 테스트

- 국가·연/월 scalar: 국가·기간 누락, annual→monthly 임의 확장 차단
- vector: partial member, duplicate member, non-finite 값, 합계 불일치와 비정규화 보존
- LNG asset: Plant/Train exact, 승인 alias, Plant 전체 expansion, lifecycle와 기간 불일치
- Pipeline: 이름·From/To·방향 exact, capacity/flow/contract 의미 혼동 차단
- Hurricane: GoM, Year/Month, approved facility, intensity scale/변환 version

### downstream 통합 테스트

- 구조화 evidence → v4 Event fact → impact path → Dimension value → Lever state lineage 보존
- 확정·관측 claim만 `eventFacts`로 내려가고 미래 예상·기관 View는 fact로 승격되지 않음
- 상충 claim이 기관명이 아닌 material 미래 상태의 Dimension value로 표현됨
- 평균·다수결·최신값 우선 없이 각 View attribution과 value lineage 보존
- Baseline 선택 후에도 대안 View와 unresolved conflict가 제거되지 않음
- Dimension budget으로 미반영된 material conflict가 warning/exclusion/coverage에 남음
- selected value만 proposal 후보에 기여
- exact 대상·기간이 있는 positive case의 slot 도달
- 누락·충돌·복수 후보 negative case의 안전한 abstain
- legacy dimension mapping 비사용
- 기존 공개 Scenario/Model Parameter API payload 호환성
- 기존 pinned Scenario Group 비재해석

완료 판정은 proposal 성공 건수만으로 하지 않는다. 잘못된 asset/기간/단위가 proposal로 누출되지 않고, 근거가
충분한 각 증적 묶음의 positive case가 실제 proposal 단계까지 도달해야 한다.

## 11. 정본과 변경 시 함께 볼 문서

- [Scenario Group Agent v4 Flow](03_SCENARIO_GROUP_AGENT_FLOW.md)
- [Scenario Group Agent API Spec](02_SCENARIO_GROUP_AGENT_API_SPEC.md)
- [Model Parameter Agent Flow](../model_parameter_agent/04_MODEL_PARAMETER_AGENT_FLOW.md)
- [Model Parameter Basecase/LUT Parsing](../model_parameter_agent/05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md)
- [Model Parameter 추가·활성화 가이드](../model_parameter_agent/06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)
- [Model Parameter 테스트와 품질 평가](../model_parameter_agent/08_MODEL_PARAMETER_AGENT_TEST_AND_QUALITY.md)

proposal 대상, exact axes, 단위 또는 evidence policy가 변경되면 이 문서를 독립적으로 추정 수정하지 않는다.
versioned proposal capability와 workbook contract를 먼저 변경·검증한 뒤 해당 release에 맞춰 이 문서를 함께
갱신한다.
