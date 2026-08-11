# Model Parameter Agent용 v4 Dimension–Lever Handoff 가이드

## 1. 목적과 범위

이 문서는 Scenario Group Agent v4가 저장한 Scenario를 Model Parameter Agent가
소비할 때 다음 두 가지를 판단하기 위한 구현 가이드다.

- 어떤 DB 데이터와 함수를 조합해 **선택된 Scenario의 lever**를 찾는가
- 찾은 lever를 **실행 가능한 model parameter 후보**로 어떤 방향으로 매핑하는가

Scenario 생성·저장 계약은 Scenario Group Agent가 소유하고, parameter 후보 선정,
값 산정, proposal 저장 및 confirmation은 Model Parameter Agent가 소유한다. 이
문서는 handoff 계약만 정의하며 Model Parameter Agent 구현이나 DB migration을
포함하지 않는다.

대상은 `generation_strategy = 'multi_event_model_lever_dimensions'`인 신규 v4
Scenario Group이다. v1/v2/v3 데이터에는 기존 매핑 경로를 사용하고, v4 로직을
소급 적용하지 않는다.

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

## 3. 권장 조회 함수

가능하면 ORM을 flow/node에서 직접 조합하지 말고 Model Parameter 소유 service에서
아래 repository/service를 호출한다.

| 데이터 | 현재 사용 가능한 함수 | 반환/필터 |
| --- | --- | --- |
| Scenario | `ScenarioRepository.fetch_model_by_id(scenario_id)` | `del_yn = 'N'`인 `MiScenarioModel` |
| Scenario Group | `ScenarioGroupRepository.fetch_by_id(scenario_group_id)` | `del_yn = 'N'`인 `MiScenarioGroupModel` |
| Group–Event 관계 | `ScenarioGroupRepository.fetch_group_events(scenario_group_id)` | 활성 관계 전체, `display_order` 순 |
| 활성 lever catalog | `ModelImpactLeverService.load_active_catalog()` | payload 목록, catalog version, checksum |

`ModelImpactLeverService.load_active_catalog()`는 현재
`apps/agents/scenario_group_agent/persistence/model_impact_lever_service.py`에 있다.
이 함수는 다음 검증까지 수행하므로 단순 catalog row 조회보다 안전하다.

- `use_yn = 'Y'`, `del_yn = 'N'`인 lever만 로드
- binding의 `parameter_name`이 `tmm_mi_model_param_m`에 존재하는지 확인
- 비활성 parameter에 대한 `executable` binding을
  `known_unsupported / INACTIVE_MODEL_PARAMETER`로 보정
- DB PK를 제외한 catalog checksum 계산

Model Parameter Agent가 이 함수를 그대로 호출하는 것은 가장 짧은 연동 경로다.
다만 Agent 간 소유 경계를 엄격히 유지하려면 같은 검증을 공용 persistence service로
옮기거나, Model Parameter 소유 adapter가
`ModelImpactLeverRepository.fetch_active_impact_levers()`와
`fetch_parameter_definitions_by_names()`를 감싸도록 한다. flow/node에서 repository를
직접 호출하는 구조는 만들지 않는다.

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
    "primary_lever_code": "liquefaction_availability",
    "primary_impact_lever_id": 12,
    "model_support_status": "full",
    "values": [
      {
        "value_id": "slow_recovery",
        "label": "회복 지연",
        "lever_states": [
          {
            "lever_code": "liquefaction_availability",
            "impact_lever_id": 12,
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

권장 검증은 다음과 같다.

- `lever_state.impact_lever_id`가 현재 catalog의 같은 `lever_code` ID와 일치하는가
- `primary_impact_lever_id`가 `primary_lever_code`의 현재 ID와 일치하는가
- Group의 `impact_catalog_checksum`이 현재
  `load_active_catalog()` checksum과 일치하는가

checksum이 다르면 과거 Scenario의 의미를 새 catalog로 조용히 재해석하지 않는다.
proposal 생성을 중단하고 재생성 또는 운영자 검토 대상으로 보내는 strict 정책을
권장한다. version은 진단 정보로 함께 남기되, 실제 내용 동일성은 checksum으로
판단한다.

catalog에 없는 code나 ID 불일치는 후보 없음으로 숨기지 말고 저장 계약/카탈로그
무결성 오류로 처리한다.

## 7. lever에서 parameter 후보로 매핑하는 방향

각 선택 lever의 `parameter_bindings`를 다음 기준으로 분류한다.

| catalog 상태 | 처리 방향 |
| --- | --- |
| `domain = 'price_only'` | 직접 model input을 만들지 않고 가격 영향 context로 보존 |
| binding 없음 | `NO_PARAMETER_BINDING` 미지원 context로 보존 |
| `support_status = 'known_unsupported'` | 후보를 만들지 않고 reason code를 보존 |
| `support_status = 'executable'` | `parameter_name`을 proposal 후보로 전달 |

binding의 `role = 'primary'`는 기본 우선 후보, `alternative`는 적용 조건에 따른
대체 후보로 사용한다. 둘 다 `executable`이면 후보가 될 수 있지만, 동일 조건에서
무작위로 선택하지 말고 `primary`를 우선하는 결정 규칙을 둔다.

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

예를 들어 `liquefaction_availability = decrease`는 가격 압력에는 상승 요인이지만,
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

`direction = 'unchanged'`는 기본적으로 변화량 후보가 아니라 지지 context다. 단,
해당 parameter mapper에 unchanged를 명시적으로 표현하는 규칙이 있으면 그 규칙을
우선한다.

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

catalog, catalog_version, catalog_checksum = lever_service.load_active_catalog()
catalog_by_code = {lever.lever_code: lever for lever in catalog}
require_same_checksum(group.impact_catalog_checksum, catalog_checksum)

candidate_evidence = []
definition_by_id = {
    item["dimension_id"]: item
    for item in group.dimension_definitions
}

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

parameter_candidates = merge_by_parameter_name(candidate_evidence)
```

## 10. 사용하면 안 되는 데이터와 패턴

- 제거된 `MiScenarioGroupModel.mi_event_id` 또는 `event_type_l2_id` 접근
- Event Type만으로 v4 lever를 다시 추론하는 기존 mapper
- 과거 `lever_mappings`, `lever_refs`, `impact_lever_refs` fixture 의존
- 모든 dimension value의 `lever_states` 합집합
- `tmm_mi_dimension_value_mapping_m`을 v4 lever 선택의 입력 정본으로 사용
- `impact_lever_id`만으로 catalog join
- `pressure_contribution`을 model parameter의 증감 부호로 직접 변환

`tmm_mi_dimension_value_mapping_m`은 기존 proposal/승인 매핑 workflow의 결과
데이터다. 현재 Scenario가 어떤 v4 lever state를 선택했는지는
`dimension_values + dimension_definitions` 조합으로 판단해야 한다.

## 11. 최소 검증 시나리오

담당 구현에서는 최소한 다음 회귀 테스트를 추가한다.

- 신규 v4 fixture에 과거 `lever_mappings`가 없어도 후보가 생성되는지
- 선택되지 않은 value의 lever가 후보에 섞이지 않는지
- 선택 value에 primary와 secondary state가 있으면 둘 다 catalog에 연결되는지
- `primary_lever_code`가 state에 없을 때 손상 데이터로 실패하는지
- multi-event Group의 모든 관계와 `source_event_ids` provenance가 보존되는지
- price-only, binding 없음, inactive parameter, catalog unsupported가 각각 후보에서
  제외되고 reason이 남는지
- 동일 parameter가 여러 lever에서 나올 때 parameter는 중복되지 않고 provenance는
  합쳐지는지
- catalog checksum 변경 시 기존 Scenario를 조용히 재해석하지 않는지
- lever direction과 parameter numeric sign이 다른 mapper 사례가 올바르게 처리되는지

이 계약을 따르면 신규 v4 Scenario의 lever 선택 의미는 Scenario Group Agent에
남고, Model Parameter Agent는 catalog와 자체 값 결정 규칙을 이용해 실행 가능성 및
구체적인 parameter 값을 책임질 수 있다.
