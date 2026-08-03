# Model Parameter Agent Dimension–Lever 연계 개발 가이드

## 1. 목적과 소유 경계

Scenario Group Agent v4는 Scenario delta와 모델 영향 경로의 정본을 다음 JSON에
저장한다.

- `dimensionDefinitions[].impactLeverRefs[]`: Scenario dimension별 영향 레버
- `eventImpactFacts[].commonImpactLeverRefs[]`: 어떤 dimension에도 포함되지 않은 공통 사실의 영향 레버
- `eventDimensionCoverage[]`: Event별 dimension 연결 여부와 `noDimensionReason`

Model Parameter Agent는 이 저장 결과를 읽어 실행 가능한 모델 파라미터 후보와
매핑 근거를 생성해야 한다. Scenario 생성·검증은 Scenario Group Agent 소유이며,
후보 선정, 제안 응답, proposal DB 저장은 Model Parameter Agent 소유다.

검토 가능한 통합 prototype은 로컬 브랜치
`handoff/model-parameter-mapping-evidence-20260803`에 보존한다. 기능 브랜치에는
Model Parameter Agent 구현을 직접 반영하지 않는다.

- Agent 저장소 prototype commit: `029d291`
- mgmt 저장소 proposal evidence migration commit: `c13e3df`

Scenario 기능 브랜치의 기존 0022에는 impact lever catalog/seed,
`dimension_definitions`, `generation_diagnostics`가 이미 포함되어 있다. 따라서
Scenario의 `impactLeverRefs`와 `noDimensionReason` 저장만으로는 mgmt migration을
추가 수정하지 않는다. 아래 proposal evidence 컬럼 변경만 Model Parameter Agent
담당자의 handoff 범위다.

## 2. Scenario 입력 계약

Scenario dimension의 정본 구조는 다음과 같다.

```json
{
  "dimensionId": "liquefaction_recovery",
  "sourceEventIds": [101],
  "sourceFactIds": ["event_101_liquefaction"],
  "impactLeverRefs": [
    {
      "impactLeverId": 12,
      "leverCode": "liquefaction_availability",
      "sourceFactIds": ["event_101_liquefaction"],
      "mappingRationale": "공급 회복 불확실성을 액화설비 가용성 경로에 연결한다."
    }
  ]
}
```

다음 규칙을 전제로 소비한다.

- Scenario delta는 `dimensionDefinitions[].impactLeverRefs[]`를 우선한다.
- `commonImpactLeverRefs`는 어떤 dimension의 `sourceFactIds`에도 포함되지 않은
  공통 사실에만 존재한다.
- 한 dimension의 `impactLeverRefs[].sourceFactIds` 합집합은
  `dimension.sourceFactIds`와 정확히 일치한다.
- `impactLeverId`, `leverCode`, fact domain은 Scenario 저장 전에 활성 impact lever
  catalog와 검증된다.
- Model Parameter Agent에서 Event fact를 다시 임의의 dimension으로 만들거나 다른
  lever로 재해석하지 않는다.

## 3. 제안 응답 계약

공개 필드명은 `data.parameterMappingEvidence`, Python/DB 필드명은
`parameter_mapping_evidence`를 사용한다. `nonInputItems` 같은 별도 이름을 추가하지
않는다.

각 evidence 항목은 다음 필드를 가진다.

| 필드 | 설명 |
| --- | --- |
| `sourceKind` | `scenario_dimension` 또는 `common_event_fact` |
| `sourceEventIds` | 근거 Event ID 목록 |
| `sourceFactIds` | 해당 lever reference가 직접 참조하는 fact ID 목록 |
| `sourceDimensionId` | dimension 근거일 때 dimension ID |
| `sourceDimensionValue` | 현재 Scenario가 선택한 dimension value |
| `impactLeverId` | 검증된 impact lever PK |
| `leverCode` | 안정적인 catalog code |
| `domain` | `supply`, `demand`, `trade`, `price_only` 등 catalog domain |
| `mappingMethod` | 후보 생성 또는 context 분류 방법 |
| `mappingRole` | 아래 네 처리 결과 중 하나 |
| `parameterNames` | 실제 후보에 연결된 parameter name 목록 |
| `unsupportedReasonCode` | 미지원 사유 코드 |
| `rationale` | 사용자와 운영자가 확인할 수 있는 한국어 매핑 근거 |

`mappingRole`은 다음 값을 사용한다.

- `PROPOSED_INPUT`: 실행 가능한 binding을 통해 실제 제안 파라미터가 생성됨
- `SUPPORTING_CONTEXT`: 실행 후보의 slot/value 판단을 돕는 보조 근거
- `PRICE_ONLY_CONTEXT`: 가격 영향은 있지만 직접 모델 입력이 없음
- `UNSUPPORTED_CONTEXT`: 알려진 미지원 경로로 후보를 만들지 않음

API와 DB JSON 내부 key는 모두 camelCase로 직렬화한다. 내부 state에서 snake_case
dict를 사용하더라도 저장 직전에 Pydantic 응답 모델로 검증하고
`model_dump(mode="json", by_alias=True)` 결과를 공용한다.

## 4. 후보 생성 순서

1. 선택 Scenario의 `dimensionDefinitions`와 `dimensionValues`를 읽는다.
2. 각 dimension의 `impactLeverRefs`를 우선 순회한다.
3. reference의 `sourceFactIds`에 해당하는 사실만 evidence에 연결한다. dimension의
   전체 fact를 각 reference에 복제하지 않는다.
4. 활성 lever catalog의 `parameterBindings`를 support status별로 분리한다.
5. 실행 가능한 binding만 proposal candidate로 만든다.
6. price-only, known unsupported, 실행 후보를 만들지 않는 binding도 삭제하지 않고
   각각의 `mappingRole` evidence로 남긴다.
7. dimension에 사용되지 않은 fact의 `commonImpactLeverRefs`를 보조 후보/context로
   처리한다.
8. 동일 parameter candidate를 병합할 때 source kind, Event, fact, lever 근거는
   합치되 proposal parameter는 중복 생성하지 않는다.

지원 상태는 Scenario dimension 우선순위를 바꾸는 기준이 아니다. Scenario Group
Agent가 선택한 dimension/lever 관계를 그대로 소비하고, 실행 가능 여부만 Model
Parameter Agent의 처리 결과로 분류한다.

## 5. 저장과 migration

`tmm_mi_model_param_proposal_m`에 다음 컬럼을 추가한다.

```sql
parameter_mapping_evidence JSON NOT NULL DEFAULT (JSON_ARRAY())
```

JSON root가 ARRAY인지 확인하는 check constraint를 함께 둔다. 아직 DB에 반영되지
않은 기존 authoritative migration
`skmip-mi-agent-mgmt/migrations/versions/0022_multi_event_model_lever_scenario_v4.py`
를 수정하며 신규 0023 revision을 만들지 않는다. 동일 변경을 mgmt ORM과
`sql/versions/0022` schema/incremental snapshot에도 반영한다.

동기 실행은 신규 proposal row 생성 시 evidence를 저장하고, background 실행은
PROCESSING row를 PROPOSED로 완료할 때 evidence를 명시적으로 전달해야 한다. 다음 두
실수를 회귀 테스트로 막는다.

- `_to_response_data`가 받지 않는 별도 keyword를 전달해 background 성공 경로가
  `TypeError`로 실패하는 문제
- `complete_proposal_result`에 evidence를 전달하지 않아 DB에 빈 배열이 저장되는 문제

## 6. 예상 변경 위치

Agent 저장소:

- `apps/agents/model_parameter_agent/schemas/api/parameters.py`
- `apps/agents/model_parameter_agent/flows/propose_parameters/api_schema.py`
- `apps/agents/model_parameter_agent/flows/propose_parameters/state.py`
- `apps/agents/model_parameter_agent/flows/propose_parameters/nodes.py`
- `apps/agents/model_parameter_agent/flows/propose_parameters/flow.py`
- `apps/agents/model_parameter_agent/presentation.py`
- `apps/agents/model_parameter_agent/persistence/model_parameter_service.py`
- `apps/persistence/model_parameter/models.py`
- `apps/persistence/model_parameter/repository.py`
- Model Parameter Agent API/DB 문서와 evaluator

mgmt 저장소:

- `migrations/versions/0022_multi_event_model_lever_scenario_v4.py`
- `models/tables.py`
- `sql/versions/0022/0022_01_schema_ddl.sql`
- `sql/versions/0022/0022_04_incremental_apply.sql`

## 7. 필수 테스트

- dimension reference가 common fact보다 먼저 후보화되는지
- 각 evidence가 reference별 `sourceFactIds`만 보존하는지
- 실행 가능, supporting, price-only, unsupported 결과가 모두 보존되는지
- candidate 병합 후 Event/fact/lever provenance가 유실되지 않는지
- sync API 응답과 DB JSON이 동일한 camelCase 계약인지
- background 성공 경로가 실제 response 변환 함수를 사용해 완료되는지
- background 완료 row에 evidence가 빈 배열로 유실되지 않는지
- proposal 저장/조회 round-trip과 confirmation 기존 계약이 유지되는지
- 0022 upgrade/downgrade SQL offline render 및 격리 MySQL 적용이 성공하는지

실제 적용 전에는 Model Parameter Agent 전체 자동화 테스트와 migration 적용 DB에서
sync/background/callback/confirmation end-to-end를 담당자가 수행한다.
