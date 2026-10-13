# Model Parameter Agent용 v4 Dimension–Lever Handoff 가이드

## 1. 목적과 범위

이 문서는 Scenario Group Agent v4가 저장한 Scenario를 Model Parameter Agent가
소비할 때 다음 두 가지를 판단하기 위한 구현 가이드다.

- 어떤 DB 데이터와 함수를 조합해 **선택된 Scenario의 lever**를 찾는가
- 찾은 lever를 raw model parameter evidence로 매핑한 뒤 **runtime proposal 허용 후보**로 어떻게 좁히는가

Scenario 생성·저장 계약은 Scenario Group Agent가 소유하고, parameter 후보 선정,
값 산정, proposal 저장 및 confirmation은 Model Parameter Agent가 소유한다. 이
문서는 두 Agent가 현재 공유하는 v4 handoff 실행 계약을 정의한다. runtime DDL은 이
경로에서 수행하지 않는다.

대상은 `generation_strategy = 'multi_event_model_lever_dimensions'`인 신규 v4
Scenario Group이다. v1/v3 Model Parameter proposal에는 공유 DB의 129행 mapping 경로를
사용하고 v4 로직을 소급 적용하지 않는다.

v1/v3 mapping의 현재 method count는 direct 35, routing 6, indirect 55, na 33이며 direct/routing이
도달하는 raw capability는 LUT-backed 10개다. v4는 이 테이블을 조회하거나 fallback으로 사용하지
않으며 v4.1 active Lever의 effective executable Parameter 16개에 도달한다.
실제 runtime proposal은 v1/v3에서 `GDP`, `PMI`, `PowerMix`, `Temperature`, `LiqUtilAdjustment` 5개를
유지하고, v4에서는 LUT-backed 10개와 Basecase-only 6개를 합친 `extend16-v8` capability를 허용한다.
이 제한은 Model Parameter Agent가 source matching 후, 값 제안 LLM과 persistence 전에 적용한다.
v4.1 확장은 기존 v4.0과 master·legacy mapping·workbook artifact를 보존하고 새 version의 Lever binding과
catalog checksum만 side-by-side로 추가한다. capability와 신규 Scenario catalog config는 새 release로 갱신한다.

## 2. 결론: 어디를 정본으로 볼 것인가

lever 후보의 정본은 다음 네 데이터를 조합한 결과다.

| 순서 | DB/필드 | 용도 |
| --- | --- | --- |
| 1 | `tmm_mi_scenario_m.dimension_values` | Scenario가 dimension별로 실제 선택한 `value_id` |
| 2 | `tmm_mi_scenario_group_m.dimension_definitions` | 선택 value의 `lever_states`와 dimension의 `primary_lever_code` |
| 3 | `tmm_mi_model_impact_lever_m` | `lever_code`별 활성 catalog 및 `parameter_bindings` |
| 4 | `tmm_mi_model_param_m` | binding 대상 parameter의 존재 여부와 활성 상태 |

Event 소유권과 provenance는
`tmm_mi_scenario_group_event_m`에서 읽는다. Scenario Group의 제거된
`mi_event_id`, `event_type_l2_id` 컬럼을 참조해서는 안 된다.

핵심 규칙은 다음과 같다.

> 그룹에 정의된 모든 value의 lever를 합치는 것이 아니라, 현재 Scenario가 선택한
> value의 `lever_states`만 후보로 사용한다. `primary_lever_code`는 그 dimension의
> 주된 인과축이며 누락 검증과 우선순위 결정에 사용한다.

## 3. 공용 조회 service

가능하면 ORM을 flow/node에서 직접 조합하지 말고 Model Parameter 소유 service에서
아래 repository/service를 호출한다.

| 데이터 | 현재 사용 가능한 함수 | 반환/필터 |
| --- | --- | --- |
| Scenario | `ScenarioRepository.fetch_model_by_id(scenario_id)` | `del_yn = 'N'`인 `MiScenarioModel` |
| Scenario Group | `ScenarioGroupRepository.fetch_by_id(scenario_group_id)` | `del_yn = 'N'`인 `MiScenarioGroupModel` |
| Group–Event 관계 | `ScenarioGroupRepository.fetch_group_events(scenario_group_id)` | 활성 관계 전체, `display_order` 순 |
| 활성 lever catalog | `ModelImpactLeverService.load_active_catalog(catalog_version=...)` | 지정 version의 payload 목록, catalog version, checksum |

`ModelImpactLeverService.load_active_catalog(catalog_version=...)`의 공용 구현은
`apps/persistence/model_impact_lever/service.py`에 있다. Scenario/Model Parameter
Agent는 이 service를 공유하며 flow/node가 repository를 직접 호출하지 않는다.
이 함수는 다음 검증까지 수행하므로 단순 catalog row 조회보다 안전하다.

- `use_yn = 'Y'`, `del_yn = 'N'`인 lever만 로드
- 요청한 `catalog_version`만 로드하고 누락·혼합 version을 fail-close
- binding의 `parameter_name`이 `tmm_mi_model_param_m`에 존재하는지 확인
- 비활성 parameter에 대한 `executable` binding을
  `known_unsupported / INACTIVE_MODEL_PARAMETER`로 보정
- DB PK를 제외한 catalog checksum 계산

Scenario Group Agent의 기존 service 경로는 호환 wrapper 역할만 하며 catalog hydration,
master 활성 검증과 checksum 계산의 소유권은 공용 persistence service에 있다.

## 4. 저장 데이터의 현재 형태

DB JSON은 ORM 필드명 기준의 `snake_case`로 저장된다. presentation API의
`camelCase`와 혼동하지 않는다.

### 4.1 Scenario의 선택값

`tmm_mi_scenario_m.dimension_values`는 dimension과 선택 value를 연결한다.

```json
{
  "supply_recovery": "slow_recovery",
  "demand_response": "high_demand"
}
```

### 4.2 Scenario Group의 dimension 정의

`tmm_mi_scenario_group_m.dimension_definitions`의 필요한 부분은 다음과 같다.

```json
[
  {
    "dimension_id": "supply_recovery",
    "label": "공급 회복 속도",
    "source_event_ids": [101, 102],
    "source_impact_path_ids": ["path-1"],
    "source_uncertainty_ids": ["uncertainty-1"],
    "primary_lever_code": "liquefaction_utilization",
    "primary_impact_lever_id": 18,
    "model_support_status": "full",
    "values": [
      {
        "value_id": "slow_recovery",
        "label": "회복 지연",
        "lever_states": [
          {
            "lever_code": "liquefaction_utilization",
            "impact_lever_id": 18,
            "direction": "decrease",
            "level": "material",
            "scope": "affected_region",
            "time_window": "next_3_months"
          }
        ],
        "pressure_contribution": "bullish",
        "assumption_rationale": "설비 정상화가 지연되는 경우"
      }
    ]
  }
]
```

신규 v4 계약에는 과거 필드인 `lever_mappings`, `lever_refs`,
`impact_lever_refs`가 없다. 이 필드들을 fallback 정본으로 사용하면 신규 v4
Scenario에서 후보가 0개가 된다.

## 5. lever 추출 절차

입력은 `scenario_id` 하나면 충분하다.

1. `ScenarioRepository.fetch_model_by_id()`로 Scenario를 조회한다.
2. Scenario의 `scenario_group_id`로
   `ScenarioGroupRepository.fetch_by_id()`를 호출한다.
3. Group의 `generation_strategy`가
   `multi_event_model_lever_dimensions`인지 확인한다. 아니면 기존 버전 경로로
   분기한다.
4. `ScenarioGroupRepository.fetch_group_events()`로 활성 Event 관계 전체를 읽는다.
   multi-event Group에서 `fetch_single_active_group_event()`를 사용하거나 대표
   Event 하나를 임의로 고르지 않는다.
5. `dimension_values`의 각 `(dimension_id, selected_value_id)`에 대해
   `dimension_definitions`에서 같은 `dimension_id`를 찾는다.
6. 해당 definition의 `values`에서 같은 `value_id`를 찾는다.
7. **선택된 value의 `lever_states`만** 수집한다. 다른 value의 state를 합치지 않는다.
8. `primary_lever_code`가 수집된 state에 포함되었는지 검증한다. 신규 v4 저장
   validation상 항상 포함되어야 하며, 누락은 무시할 fallback 상황이 아니라 손상된
   저장 데이터로 취급한다.
9. 같은 value 안의 lever는 `lever_code` 기준으로 순서를 보존해 중복 제거한다.
10. `source_event_ids`가 활성 Group–Event 관계의 `mi_event_id` 집합에 포함되는지
    검증하고 provenance로 보존한다.

모든 dimension의 모든 value를 순회하면 서로 배타적인 가정의 lever가 한 proposal에
섞인다. 반드시 `dimension_values`가 선택한 value를 먼저 좁힌 뒤 state를 읽어야 한다.

## 6. catalog 연결과 무결성 정책

추출한 state는 안정 식별자인 `lever_code`로 활성 catalog와 연결한다.
`impact_lever_id`만으로 연결하지 않는다. 저장된 ID는 동일 code를 가리키는지 확인하는
무결성 검사용이다.

필수 검증은 다음과 같다.

- `lever_state.impact_lever_id`가 현재 catalog의 같은 `lever_code` ID와 일치하는가
- `primary_impact_lever_id`가 `primary_lever_code`의 현재 ID와 일치하는가
- Group의 `impact_catalog_checksum`이 현재
  `load_active_catalog()` checksum과 일치하는가

checksum이 다르면 과거 Scenario의 의미를 새 catalog로 조용히 재해석하지 않는다.
proposal 생성을 중단하고 재생성 또는 운영자 검토 대상으로 보낸다. version은 진단
정보로 함께 남기되, 실제 내용 동일성은 checksum으로 판단한다.

catalog에 없는 code나 ID 불일치는 후보 없음으로 숨기지 말고 저장 계약/카탈로그
무결성 오류로 처리한다.

## 7. lever에서 parameter 후보로 매핑하는 방향

각 선택 lever의 `parameter_bindings`를 다음 기준으로 분류한다.

| catalog 상태 | 처리 방향 |
| --- | --- |
| `domain = 'price_only'` | 직접 model input을 만들지 않고 가격 영향 context로 보존 |
| binding 없음 | `NO_PARAMETER_BINDING` 미지원 context로 보존 |
| `support_status = 'known_unsupported'` | 후보를 만들지 않고 reason code를 보존 |
| `support_status = 'executable'` | `parameter_name`을 raw candidate evidence로 전달 |

binding의 `role = 'primary'`는 기본 우선 후보, `alternative`는 적용 조건에 따른
대체 후보로 사용한다. 둘 다 `executable`이면 raw 후보가 될 수 있지만, runtime allow-list를
통과한 후보만 routing 대상으로 사용한다. 통과 후보를 동일 조건에서 무작위로 선택하지 않는다.
단일 primary는 결정적으로 선택한다. primary와 alternative가 함께 통과하면 lineage를 모두 보존하고,
v4에서는 Step1.5로 다시 routing하지 않은 채 후속 exact slot/evidence 단계가 applicability와
Scenario/Event/Lever 맥락을 판단한다.

0030 v4 runtime fixture는 active Lever 18개, raw binding occurrence 16개다. 비활성 CDD/HDD
binding을 제외한 effective executable occurrence와 고유 활성 Parameter는 각각 14개다. 이 수치는
catalog capability이며 runtime proposal 범위가 아니다. LUT-backed 활성 10개는
Basecase 우선/LUT fallback capability를 가지고,
`User-Adjusted Gas Demand`, `RegasAdjustment`, `PNG Contract Volume`, `ShippingCost`는 검증된 Basecase
exact slot capability만 가진다.

숫자를 쉽게 풀면 다음과 같다.

- `16건`: Lever catalog에 적힌 “Lever → Parameter 연결선”을 중복 포함해 모두 센 수다.
- `14건`: 그중 현재 꺼져 있는 CDD와 HDD 연결선 2개를 실행 대상에서 뺀 수다.
- `14개`: effective executable 연결선이 가리키는 고유 활성 Parameter 수다.

즉 “파라미터 16개를 제안한다”는 뜻이 아니라, **연결선은 16개이고 그중 유효한 연결선과 catalog에서
도달 가능한 서로 다른 활성 Parameter는 각각 14개**라는 뜻이다.

raw 후보를 만든 뒤 Model Parameter Agent는 다음 runtime proposal allow-list를 적용한다.

```text
GDP
PMI
PowerMix
Temperature
User-Adjusted Gas Demand
Population
HurricaneIntensity
LiqProdAdjustment
LiqUtilAdjustment
PipelineAdjustment
RegasAdjustment
SupplyDisruption
PNG Contract Volume
ShippingCost
```

allow-list 밖의 executable binding은 DB나 catalog에서 비활성으로 바꾸지 않고 proposal 경로에서만
제외하며 내부 non-input evidence에는 `PROPOSAL_SCOPE_EXCLUDED` reason code를 남긴다. 현재 0032 fixture의
effective executable 14개는 v4 allow-list와 일치한다. 외부개발 DB에서 추가로 활성·binding됐지만 capability에
없는 Parameter는 같은 방식으로 제외한다. v1/v3 raw mapping 10개에는 기존 5종 gate를 유지한다.
confirmation은 기존 proposal과 custom parameter 호환을 위해 이 gate의 대상이 아니다.

동일 `parameter_name`이 여러 dimension 또는 lever에서 나오면 proposal parameter는
하나로 중복 제거하되 다음 provenance는 합쳐서 보존한다.

- `dimension_id`, dimension label/rationale
- 선택 `value_id`, value label/assumption rationale
- `source_event_ids`
- `primary_lever_code`인지 여부
- lever의 code, ID, domain
- state의 `direction`, `level`, `scope`, `time_window`
- binding의 role, applicability, support status/reason

서로 다른 lever가 동일 parameter에 상충하는 state를 주면 한 방향으로 덮어쓰지
않는다. 양쪽 근거를 downstream 값 결정 로직에 전달하거나 명시적 review 상태로
분기한다.

## 8. `direction`을 숫자 부호로 바로 바꾸지 않는 이유

`lever_state.direction`은 현실 세계 lever 자체의 변화 방향이다. model parameter의
숫자 부호와 동일하다는 보장은 없다.

예를 들어 `liquefaction_utilization = decrease`는 가격 압력에는 상승 요인이지만,
실제 모델 입력이 가동률인지 공급 차질량인지에 따라 parameter의 증감 방향이 달라질
수 있다. 따라서 다음과 같은 공통 하드코딩은 금지한다.

```text
increase -> +delta
decrease -> -delta
bullish  -> +delta
bearish  -> -delta
```

권장 책임 분리는 다음과 같다.

1. Scenario handoff는 선택된 `lever_state`의 의미를 손실 없이 전달한다.
2. catalog binding은 어떤 canonical `parameter_name`이 적용 가능한지 좁힌다.
3. Model Parameter Agent의 parameter metadata, basecase/LUT, 단위 및 기존 mapper가
   실제 slot/value와 수치 방향을 결정한다.
4. `binding.applicability`, state의 `level/scope/time_window`를 값 결정 조건으로
   사용한다.
5. `pressure_contribution`과 lever `domain`은 결과의 정합성 확인 및 설명 근거로
   사용하며 직접 부호 변환식으로 사용하지 않는다.

`direction = 'unchanged'`는 변화 후보가 아니라 supporting context다. unchanged state만
남거나, 변화가 있는 raw candidate가 모두 runtime allow-list 밖이라 최종 candidate가 0개면
proposal row를 저장하지 않고 `INVALID_REQUEST`로 종료한다.

## 9. 구현 의사코드

아래 코드는 데이터 결합 순서를 설명하기 위한 의사코드다. 실제 session과 오류
처리는 Model Parameter Agent의 기존 service 패턴을 따른다.

```python
scenario = scenario_repository.fetch_model_by_id(scenario_id)
group = group_repository.fetch_by_id(scenario.scenario_group_id)

if group.generation_strategy != "multi_event_model_lever_dimensions":
    return legacy_mapping(scenario, group)

relations = group_repository.fetch_group_events(group.scenario_group_id)
group_event_ids = {relation.mi_event_id for relation in relations}

catalog, catalog_version, catalog_checksum = lever_service.load_active_catalog(
    catalog_version=group.impact_catalog_version,
)
catalog_by_code = {lever.lever_code: lever for lever in catalog}
require_same_checksum(group.impact_catalog_checksum, catalog_checksum)

candidate_evidence = []
definition_by_id = {
    item["dimension_id"]: item
    for item in group.dimension_definitions
}
require_equal_sets(
    scenario.dimension_values.keys(),
    definition_by_id.keys(),
)

for dimension_id, selected_value_id in scenario.dimension_values.items():
    definition = definition_by_id[dimension_id]
    require_subset(definition["source_event_ids"], group_event_ids)

    selected_value = next(
        value
        for value in definition["values"]
        if value["value_id"] == selected_value_id
    )
    states = deduplicate_by_code(selected_value["lever_states"])
    require_code(states, definition["primary_lever_code"])

    for state in states:
        lever = catalog_by_code[state["lever_code"]]
        require_same_id(state["impact_lever_id"], lever.impact_lever_id)
        candidate_evidence.extend(
            map_bindings(
                lever=lever,
                state=state,
                definition=definition,
                selected_value=selected_value,
            )
        )

proposal_source_candidates = filter_by_runtime_proposal_allow_list(
    candidate_evidence,
    allowed={
        "GDP",
        "PMI",
        "PowerMix",
        "Temperature",
        "LiqUtilAdjustment",
    },
)
parameter_candidates = merge_by_parameter_name(proposal_source_candidates)
# 이 다음에만 Step1.5/Step2/Step3와 proposal persistence를 수행한다.
```

## 10. 사용하면 안 되는 데이터와 패턴

- 제거된 `MiScenarioGroupModel.mi_event_id` 또는 `event_type_l2_id` 접근
- Event Type만으로 v4 lever를 다시 추론하는 기존 mapper
- 과거 `lever_mappings`, `lever_refs`, `impact_lever_refs` fixture 의존
- 모든 dimension value의 `lever_states` 합집합
- `tmm_mi_dimension_value_mapping_m`을 v4 lever 선택의 입력 정본으로 사용
- `impact_lever_id`만으로 catalog join
- `pressure_contribution`을 model parameter의 증감 부호로 직접 변환
- runtime proposal allow-list를 건너뛰고 raw binding을 Step1.5·값 제안 또는 persistence로 전달
- 이 Model Parameter 전용 allow-list를 Scenario Group 생성·검증이나 confirmation gate로 재사용

`tmm_mi_dimension_value_mapping_m`은 기존 proposal/승인 매핑 workflow의 결과
데이터다. 현재 Scenario가 어떤 v4 lever state를 선택했는지는
`dimension_values + dimension_definitions` 조합으로 판단해야 한다.

## 11. 최소 회귀 계약

v4 handoff 구현은 최소한 다음 회귀를 계속 만족해야 한다.

- 신규 v4 fixture에 과거 `lever_mappings`가 없어도 후보가 생성되는지
- 선택되지 않은 value의 lever가 후보에 섞이지 않는지
- 선택 value에 primary와 secondary state가 있으면 둘 다 catalog에 연결되는지
- `primary_lever_code`가 state에 없을 때 손상 데이터로 실패하는지
- multi-event Group의 모든 관계와 `source_event_ids` provenance가 보존되는지
- binding 없는 price-only, binding 없음, inactive parameter, catalog unsupported가 각각 후보에서
  제외되고 reason이 남으며 conditional price-only는 근거 판정으로 진행하는지
- v4.1 executable 고유 Parameter 16개와 v1/v3 reachable 10개를 유지하면서 runtime proposal에는 v1/v3 5종과
  v4 extend16 16종이 각각 정확히 남는지
- allow-list 밖의 executable binding만 있는 요청은 Step1.5·값 제안 LLM과 persistence 전에
  종료되는지
- 동일 parameter가 여러 lever에서 나올 때 parameter는 중복되지 않고 provenance는
  합쳐지는지
- catalog checksum 변경 시 기존 Scenario를 조용히 재해석하지 않는지
- lever direction과 parameter numeric sign이 다른 mapper 사례가 올바르게 처리되는지

이 계약을 따르면 신규 v4 Scenario의 lever 선택 의미는 Scenario Group Agent에
남고, Model Parameter Agent는 catalog와 자체 값 결정 규칙을 이용해 실행 가능성 및
구체적인 parameter 값을 책임질 수 있다.

catalog checksum이 바뀌면 parameter master와 Lever catalog를 한 transaction으로
적용한 뒤 신규 v4 Scenario를 생성한다. 기존 v4 Scenario를 새 catalog로 조용히
재해석하지 않는다. 이 변경은 public proposal/confirmation endpoint·payload와 저장
JSON shape을 변경하지 않으며 provenance와 미지원 진단은 내부 state, trace,
validation warning 또는 실패 detail에만 둔다. runtime allow-list 적용도 DB·canonical·Lever
catalog와 workbook artifact를 변경하지 않으며, versioned resource config와 startup validation은
`extend16-v8`/`new-bc-v8` 계약으로 갱신한다. `new-bc-v8`은 ID 13·14 matrix target을
최종 workbook과 동일한 `G:CL` 84개월 범위로 제한하고 mgmt v0044 master와 정합화한다. Scenario Group Agent를 포함한
다른 Agent와 confirmation flow는 기존 동작을 유지한다.

## 12. Model Parameter v4 LLM 입출력 예시

예를 들어 사용자가 “Angola LNG가 2026년 8월에도 저가동”인 기존 분기를 선택했다고
가정한다. 실제 prompt는 Event·Scenario·전체 provenance와 압축된 slot catalog를 더
포함하지만 핵심은 다음 세 단계다.

### Step 1.5 이전: runtime allow-list 적용과 후보 선택

0030 catalog에서 `liquefaction_utilization` ID 18의 raw binding은 다음 하나다.

```json
{
  "leverCode": "liquefaction_utilization",
  "state": {"direction": "decrease", "scope": "Angola LNG", "timeWindow": "2026-08"},
  "candidates": [
    {"parameterName": "LiqUtilAdjustment", "role": "primary", "applicability": "기존 Train의 단기·부분 저가동"}
  ]
}
```

`LiqProdAdjustment`는 이 Lever의 alternative가 아니다. 대폭·영구 생산손실 또는 신규 Train ramp-up은 별도
`liquefaction_production_override` ID 19의 primary binding으로만 도달하며 현재 v4 runtime allow-list 안이다.
위 ID 18 state는 runtime gate를 통과해 다음 후보만 남는다.

```text
runtime proposal candidates: LiqUtilAdjustment
```

단일 primary만 남으므로 서버가 결정적으로 선택해 Step1.5 LLM을 생략한다.

### Step 2: 값을 보지 않고 exact slot 선택

```json
{
  "parameterName": "LiqUtilAdjustment",
  "availableAxes": ["Country", "LNG Plant", "LNG Plant Train", "Year", "Month"],
  "scenarioScope": "Angola LNG / 2026-08"
}
```

```json
{
  "slotAxes": {
    "Country": "Angola",
    "LNG Plant": "Angola LNG",
    "LNG Plant Train": "Angola LNG T1",
    "Year": 2026,
    "Month": 8
  }
}
```

### Step 3: 검증된 기준값을 보고 최종 절대값 산정

```json
{
  "parameterName": "LiqUtilAdjustment",
  "referenceValue": 0.90738,
  "parameterHint": "0~1 범위의 월평균 최종 가동률",
  "leverProvenance": [{"direction": "decrease", "level": "material", "scope": "Angola LNG"}]
}
```

```json
{
  "proposedValue": 0.45,
  "rationaleKo": "기준 가동률에서 월 전반의 저가동과 제한적 회복을 반영한 최종 절대값입니다."
}
```

`direction=decrease`를 단순히 음수로 바꾸지 않는다. 이 parameter가 “가동률 최종값”이라는
hint, 단위·범위와 기준값을 함께 해석해 `0.45`를 만든다.

## 13. 기존 v4 그룹에 Scenario 한 행을 수동 추가하는 계약

### 13.1 가장 중요한 결론

분기를 새로 만들지 않는다면 새 Scenario 행에 Lever JSON을 만들거나 저장하지 않는다.

```text
Scenario.dimension_values의 value_id
→ Group.dimension_definitions의 기존 value
→ 그 value에 이미 저장된 lever_states
→ active Lever catalog의 parameter_bindings
→ Model Parameter runtime proposal allow-list
→ Model Parameter 후보
```

Model Parameter Agent는 새 행의 제목이나 Event Type을 보고 Lever를 다시 추론하지 않는다.
선택한 기존 value에 필요한 Lever가 없다면 per-Scenario 임시 Lever를 붙이지 말고, 올바른
catalog로 Scenario Group 전체를 재생성해야 한다.

### 13.2 사람이 보내는 값과 DB에 저장할 값

사람은 기존 table의 모든 Dimension에 대해 한 분기씩 선택하고 이름을 입력한다.

```json
{
  "scenarioId": null,
  "title": "정비 연장과 높은 재고의 상쇄",
  "cells": {
    "facility_recovery": "저가동 지속",
    "europe_inventory": "높은 재고"
  }
}
```

Scenario service는 표시 label을 기존 value의 유일한 `value_id`로 결정적으로 변환해 다음처럼
저장한다. 직접 SQL로 넣는 경우에는 처음부터 이 ID 형태를 써야 한다.

```json
{
  "dimension_values": {
    "facility_recovery": "delayed_recovery",
    "europe_inventory": "high_inventory"
  }
}
```

다음 equality를 저장 전과 Model Parameter handoff에서 모두 지켜야 한다.

```text
list(table.headers[].key)는 중복이 없어야 하고
set(table.headers[].key)
==
set(group.dimension_definitions[].dimension_id)

set(new_scenario.dimension_values.keys())
==
set(group.dimension_definitions[].dimension_id)
```

존재하지 않는 label/ID, 중복 label로 모호한 입력, value ID가 누락·중복된 Group 정의,
일부 Dimension/header 누락, 중복·미등록 header와 새 cell key는 실패시킨다.
같은 Dimension 조합을 가진 기존 Scenario도 중복 생성하지 않는다. Signpost sync 요청은 누락된
기존 row를 삭제 대상으로 보기 때문에 새 행만 보내지 말고 현재 활성 row 전체와 새 행을 함께
보내야 한다.

### 13.3 LLM과 서버가 각각 만들어야 하는 것

기존 분기 선택은 사람이 고정하며 LLM이 다른 값으로 바꾸지 않는다.

| 책임 | 생성·검증 항목 |
|---|---|
| 기존 Group 데이터 | v4 API version/strategy, ordered Event 관계, catalog version/checksum, Dimension/Value, source lineage, primary Lever와 각 value의 `lever_states` |
| 신규 행용 Scenario LLM | 선택값을 바꾸지 않은 narrative와 probability/likelihood; 완전한 v4 품질이 필요하면 pressure band·rationale, related market 설명도 생성 |
| Scenario 서버 | label→value ID 변환, 모든 Dimension exact 선택, 중복 조합·scenario 수·display order 검증, baseline/role 재계산, Scenario insert와 group count 갱신 |
| Signpost LLM | 신규·수정 Scenario에 대한 관측 가능한 Signpost 3~6개와 strength·근거·검색 keyword |
| Model Parameter Agent | 선택 value에서 Lever를 추출하고 version별 runtime allow-list(v1/v3 5개, v4 14개)로 제한한 뒤 parameter routing, exact slot 선택, 기준값 기반 최종 절대값과 근거 생성 |

Model Parameter proposal의 최소 실행 조건에는 pressure band·role이 직접 포함되지 않지만, 공식 v4
Scenario 화면·비교·품질 계약을 완성하려면 이를 비워 둔 채 “정상 완료”로 간주하지 않는다.
Scenario를 이미 confirmation한 그룹에 추가했다면 기존 validation, Signpost와 confirmation
snapshot은 새 행을 포함하지 않으므로 해당 lifecycle을 다시 수행한다.

### 13.4 Scenario Agent 개발자 구현 순서

1. Group을 잠그고 `api_version=v4`, strategy, active catalog version/checksum을 확인한다.
2. 활성 Group–Event 관계 1~5개를 `display_order` 순으로 읽고 source Event 부분집합을 확인한다.
3. table header가 기존 Dimension 전체와 exact set이고 중복이 없는지 확인한다.
4. 사람의 cells를 기존 Dimension/Value에 exact lookup한다. label은 유일할 때만 ID로 바꾼다.
5. 모든 Dimension key가 정확히 한 번 있고 기존 Scenario와 조합이 겹치지 않는지 확인한다.
6. Model Parameter Agent가 소유한 production matcher를 non-mutating preflight로 호출해 선택 state 중
   runtime allow-list를 통과한 변화 후보와 exact Basecase/LUT slot이 하나 이상 있는지 확인한다. 없으면
   저장 성공과 proposal 가능을 혼동하지 않도록 명확한 coverage 오류를 반환한다. Scenario Group
   Agent 내부에 allow-list를 복제하거나 자체 생성·validation 규칙으로 사용하지 않는다.
7. LLM에는 고정된 선택값, ordered Event, 기존 value rationale/Lever context를 주고 narrative와
   Scenario-level 품질 필드만 생성하게 한다. 숫자 catalog ID나 새 Lever를 만들게 하지 않는다.
8. 서버가 role/baseline/order를 재계산하고 Scenario insert와 `scenario_count` 갱신을 한 transaction으로
   처리한다.
9. validation → Signpost 재생성 → confirmation snapshot을 다시 수행한 뒤 Model Parameter proposal을
   호출한다.

한 문장으로 요약하면 다음과 같다.

> v4의 새 Scenario 행은 기존 Dimension의 `value_id`를 모두 선택하고, Lever 의미는 Group의 해당
> value에 이미 있어야 한다. LLM은 고정 선택을 설명하는 Scenario 콘텐츠를 만들고, 서버는 catalog
> code/ID·Event lineage·checksum·전체 key set을 검증해야 한다.
