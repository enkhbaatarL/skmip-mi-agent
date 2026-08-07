# Scenario Group Agent API Request/Response

> 버전: v8

<aside>
💡

시간이 오래 걸리는 시나리오 생성, 시나리오 검토, Signpost 생성은 HTTP 요청에서 접수 상태를 즉시 반환하고, 작업 완료 후 callback으로 최종 결과를 전송합니다.

즉시 응답은 `ScenarioGroupAcceptedOut` 형태이며, 최종 결과 payload는 각 API의 Callback Body를 기준으로 합니다.

테스트 및 로컬 검증용으로 동일한 생성/검증 graph를 HTTP 요청 안에서 끝까지 실행하고 Callback Body를 응답으로 반환하는 sync endpoint도 제공합니다.
sync endpoint는 callback을 전송하지 않으며 운영 트래픽용 API가 아닙니다.

</aside>

```mermaid
sequenceDiagram
    participant Client
    participant Server

    Client->>Server: POST /scenario-groups <br/> body: {miEventId}

    Note over Server: 시나리오 그룹 및 시나리오 생성(id)
    Server-->>Client: 시나리오 그룹 id (접수완료)

    Note over Server: 시나리오그룹(나머지) 시나리오 N개 생성 + DB저장
    Server-->>Client: Callback:시나리오그룹+시나리오 생성결과 <br/>(연결이벤트는 DB에서 검색)

    Client->>Server: <br/><br/><br/><br/>POST /scenario-groups/{scenarioGroupId}/validation
    Note over Server: 검토
    Server-->>Client: 접수완료

    Server-->>Client: Callback:시나리오 검토 결과 (isValid, reason) <br/>

    Client->>Server: <br/><br/><br/><br/>POST /scenario-groups/{scenarioGroupId}/signposts
    Server-->>Client: 접수완료
    Note over Server: Signpost 생성 + DB저장
    Server-->>Client: Callback: Signpost 생성 결과

    Client->>Server: <br/><br/><br/><br/>POST /scenario-groups/{scenarioGroupId}/confirmation
    Note over Server: 생성 확정/스냅샷 저장 + DB저장
    Server-->>Client: 생성 확정 결과 (콜백없음)
```

## Scenario Group과 Scenario 의 status / stage

### Scenario Group (`tmm_mi_scenario_group_m`)

- `status` (DB default: `creating`)
    - `creating`: 시나리오/사인포스트 생성 진행 중
    - `created`: 생성 파이프라인 완료(검토/확정 대기)
    - `realized`: 실현 처리
- `stage` (DB default: `ready`)
    - `ready`: 그룹 생성 직후 초기 상태
    - `scenario_created`: 시나리오 생성 완료
    - `scenario_validated`: 시나리오 검증 완료
    - `signpost_created`: 시나리오별 signpost 생성 완료
    - `completed`: confirmation 완료(스냅샷 저장 완료)

### Scenario (`tmm_mi_scenario_m`)

- `status` (DB default: `creating`)
    - `creating`: 개별 시나리오 생성 중
    - `created`: 생성 완료
    - `realized`: 실현 시나리오로 판정
    - `discarded`: 폐기 시나리오
- `stage`
    - 별도 컬럼 없음. 단계 관리는 시나리오 그룹의 `stage`를 기준으로 동기화한다.
- DB 제약
    - `ck_tmm_mi_scenario_m_02`: `status IN ('creating','created','realized','discarded')`

| API | Scenario Group status | Scenario Group stage | Scenario status |
| --- | --- | --- | --- |
| create scenario | `creating` | `scenario_created` | `creating` |
| validation | `creating` | 성공 `scenario_validated`<br>실패 `scenario_created` | `creating` |
| create signpost | `creating` | `signpost_created` | `created` |
| confirmation | `created` | `completed` | `created` |

## API

### Sync 테스트 API

아래 API는 기존 background API와 같은 request body를 사용하고, response body는 각 API의 Callback Body와 같습니다.
sync endpoint 응답에는 테스트 지표 수집을 위해 `usage`가 추가될 수 있습니다.
`usage.prompt_tokens`, `usage.completion_tokens`, `usage.total_tokens`는 해당 sync 요청 안에서 누적된 LLM token 사용량입니다.

- `POST /scenario-groups/sync`
  - 기존 `POST /scenario-groups`의 prepare 및 생성 graph를 동기 실행
  - Response: `CreateScenariosOut`
- `POST /v1/scenario-groups/sync`
  - 단일 `miEventId`, 선택 `comparisonRunId`
  - Response: version/strategy, Event, dimension lineage, 공통 table을 포함한
    `VersionedCreateScenariosOut`
- `POST /v2/scenario-groups/sync`
  - 중복 없는 `miEventIds` 2~5개와 필수 `comparisonRunId`
  - Event별 원본 Template dimension 3~6개를 선택하고 key를
    `e{eventId}__{dimKey}`로 namespace한다.
  - v2 전용 compact response schema를 사용하며 v3/v4 상세 diagnostics와 lineage 필드를
    공유하지 않는다.
- `POST /v3/scenario-groups/sync`
  - v2와 같은 요청 계약
  - Event 충격과 관련 상호작용을 3~6개 합성 dimension으로 구성한다.
- `POST /v4/scenario-groups`
  - 요청: `miEventIds` 2~5개, `userId`, 선택적 `comparisonRunId`
  - Template 없이 Event 근거와 모델 영향 레버 카탈로그로 3~6개 dimension을 생성
  - Scenario의 pressure/floor/ceiling은 JKM 기준이며, TTF/HH 특이성이
    명확한 경우에만 row의 `relatedMarkets`에 시장과 근거를 보조정보로 포함
  - 즉시 `ScenarioGroupAcceptedOut`을 반환하고 완료 결과를 기존 scenario callback으로 전달
- `POST /v4/scenario-groups/sync`
  - v4와 같은 요청 계약에 필수 `comparisonRunId`를 추가하고 테스트·비교용으로
    완료 응답을 동기 반환
  - `generationDiagnostics`에 Event 상호작용, covered/uncovered dimension,
    unsupported lever와 전체 parameter coverage 상태를 포함
- `POST /scenario-groups/{scenarioGroupId}/validation/sync`
  - 기존 validation prepare 및 검증 graph를 동기 실행
  - Response: `ValidateScenariosOut`
- `POST /scenario-groups/{scenarioGroupId}/signposts/sync`
  - 기존 signpost prepare 및 생성 graph를 동기 실행
  - Response: `CreateSignpostsOut`

graph 실행 중 오류가 발생하면 HTTP 200에 `{"result": "failure", "reason": "..."}` 형태의 callback body를 반환합니다.
prepare 단계의 입력 오류, 권한 오류, 중복 생성 오류는 기존 exception handler 응답을 따릅니다.

versioned sync endpoint의 생성 오류는
`{"status":"error","message":"...","data":null}` 형태로 반환한다. v2/v3/v4
성공 응답은 `apiVersion`, `generationStrategy`, `comparisonRunId`,
`events`, `dimensionDefinitions`, `table`, `generationDiagnostics`를 포함한다.
`events`는 요청 Event 순서를 유지한다. v2의 각
`dimensionDefinitions[].sourceRef`는 `eventId`, `scenarioDimensionTemplateId`,
`dimKey`만 포함한다. label·description·required는 서버가 입력 Template에서 복원한다.
v2 value에는 `valueId`, `label`, `pressureContribution`만 포함하며
`sourceAssignments`는 없다. v2 diagnostics는 입력 Event 제목·요약·핵심 사실에서
LLM 없이 구성한 compact EventShock,
`unselectedDimensionRefs`, `unrepresentedPressureBands`를 포함한다. v3는 Event별
`{eventId, shockSummary}`와 compact dimension을 반환한다. v3 dimension은
`rationale`, `sourceEventIds`, `(scenarioDimensionTemplateId, dimKey)` 형태의
`sourceRefs`를 가지며 value에는 `valueId`, `label`, `pressureContribution`,
`description`, `derivationRationale`을 포함한다. 신규 두 value 필드는 과거 저장 데이터와의
호환을 위해 nullable이지만 새 v3 생성 결과에서는 빈 문자열을 허용하지 않는다.
v2/v3/v4 `table.rows[].cells`는 저장된 `valueId`가 `dimensionDefinitions[].values[]`와 일치하면
내부 ID 대신 해당 value의 사용자용 `label`을 표시한다. 과거 순번형 value ID도 같은 label 변환을 유지한다.
v3 `generationDiagnostics.templateDimensionSelections`는 Event별 Template 후보의
`relevanceType`, `observedBasis`, `selectionRationale`, 서버가 hydrate한 label·description·required,
enum 예시와 `usedInDimensionIds`를 반환한다. 선택됐지만 합성 dimension에서 사용되지 않은 후보는
`usedInDimensionIds=[]`로 남는다. 이 진단은 기존 Scenario Group JSON 컬럼에 저장하므로 DB migration은 없다.
v4의 각 dimension은 `sourceEventIds`, `sourceImpactPathIds`, `sourceUncertaintyIds`,
`primaryLeverCode`, `primaryImpactLeverId`, `modelSupportStatus`, `values`를 포함한다.
화면용 `label`은 열린 질문인 `description`과 분리되며 핵심 대상과 변화 축을 간결하게 표시한다.
각 value는 구체적인 방향·수준·범위·기간과 Catalog ID를 가진 `leverStates`,
`pressureContribution`, `assumptionRationale`을 제공한다. 기존 `eventGroundings`와
`leverMappings`는 새 v4 생성 응답에서 제거한다.

v4 `generationDiagnostics`는 실행 전체에서 고정한 `analysisAsOf`, 수치·기간·현재 시점 해석을
별도 Anchor ID나 source ref 없이 자연어로 보존한 `decisionBasis`, `eventFacts`, `eventExclusions`, `impactPaths`,
`pathUncertainties`, Path ID를 참조하는 `eventInteractions`, `interactionUncertainties`,
`validationWarnings`, `scenarioPressureBreakdowns`를 포함한다. 이 진단은 기존 Scenario Group
JSON 컬럼에 동일하게 저장하므로 DB migration은 없다. 운영 비동기 완료 callback은 기존
`scenarioGroup + table` 계약을 유지하며 전체 분석 graph는 v4 sync 응답과 DB 조회에서 확인한다.
`eventFacts`의 사실 본문은 `observedBasis` 문장이다. 새 v4 생성 결과는 서버가 부여한 `factId`,
`eventId`, 원문 발생시각인 `observedAt`만 함께 제공한다. 영향 제외 이유는 `eventExclusions`에만
저장한다. LLM의 주관적 분류인 `factStatus`와 `confidence`, 과거 `noMaterialImpactReason`은
저장 JSON에 남아 있어도 읽을 때 무시하며 새 응답에는 다시 노출하지 않는다. Impact Path와
Event Interaction도 별도 `priceEffect`를 제공하지 않고 JKM 방향·기간을 자연어 `mechanism`에
보존한다. 최종 계산용 Dimension Value `pressureContribution`과 Scenario `pressureBand`는
폐쇄형 Enum 계약을 유지한다.
v2/v3/v4 각 row는 `pressureTarget="JKM"`, `pressureBand`, `pressureRationale`을 반환한다.
DB의 기존 `global_pressure_band`/`global_pressure_rationale` 컬럼은 migration 없이 persistence
adapter에서만 사용하며 public API에는 노출하지 않는다. `scenarioRole`, `baselineYn`,
`probabilityScore`, v4의 `relatedMarkets`도 함께 반환한다. `baselineYn=Y`는
floor·ceiling·mixed를 포함한 전체 Scenario 중
최고 `probabilityScore` 하나에 서버가 지정한다. `relatedMarkets`는 table header/cell이나
pressure tag가 아니라 Scenario 상세에서만 표시하는 선택적 보조정보이며 TTF/HH만 허용한다.

### 자유 dimension value mapping 승인

- `POST /scenario-groups/{scenarioGroupId}/dimension-mapping-approvals`
- Request: `userId`, `decisions[]`
  (`dimensionValueId`, `mappingVersion`, `approve|reject`)
- LLM을 호출하지 않는다.
- 현재 proposal과 다른 `mappingVersion`은 stale 요청으로 거부한다.
- Validation은 저장된 `dimensionDefinitions`에 없는 자유 value를 source
  dimension에 투영해 pending proposal로 반환한다.
- v2 mapping proposal의 source 식별자는
  `(eventId, scenarioDimensionTemplateId, dimKey)`다.
- v3 mapping proposal의 source 식별자는
  `(scenarioDimensionTemplateId, dimKey)`이며 Event 연결은 `sourceEventIds`가 담당한다.
- v2 compact source와 v4 dimension grounding/lever mapping은 각 버전의 독립 계약을 유지한다.
- 현재 사용 중인 proposal이 모두 승인되면
  `parameterMappingReady=true`가 된다.

### 0) Event 목록/상세 조회

Backoffice Event List와 Event Detail 화면을 위한 조회 API입니다.

- `GET /events`
  - Query: `keyword`, `status`(`new`/`updated`), `eventTypeL1Id`, `eventTypeL2Id`, `recommendedOnly`, `dateFrom`, `dateTo`, `sort`, `page`, `pageSize`
  - Response: `rows`, `pagination`, `source`
  - 각 row는 `miEventId`, title/summary/time/category, Event Type L1/L2, signal/recommended metadata, `relatedScenarioGroup`, `scenarioActionState`를 포함합니다.
  - `scenarioActionState.type`은 `create`, `continue_generation`, `open_detail`, `disabled` 중 하나입니다.
- `GET /events/{mi_event_id}`
  - Response: `event`, `scenarioTemplate`, `source`
  - `event` detail에는 `keyBullets`, `tags`, `detailAnalysis`, `sourceMiRecordIds`, `createdAt`, `updatedAt`, `language`를 포함합니다.
  - `scenarioTemplate`은 event type L2 기준 Template ID/checksum,
    `eventTypeDefinition`, `lngPriceImpactExamples`, raw JSON과 display용
    dimension 목록을 반환합니다. legacy dimension의 description이 없으면
    label을 display fallback으로 사용합니다.

Backoffice Scenario Group List를 위한 목록 API도 제공합니다.

- `GET /scenario-groups`
  - Query: `includeDeleted`, `miEventId`, `keyword`, `status`, `stage`, `sort`
  - Response: `rows`, `meta`
  - 각 row는 scenario group ID/name, base `miEventId`, status/stage, scenario/signpost count, created/updated time, deleted state를 포함합니다.

### 1) 시나리오 그룹 및 시나리오 생성

- Method/Path: `POST /scenario-groups`
- Description: `miEventId`를 기준으로 시나리오 그룹/시나리오를 생성한다.

Request

```json
{
  "miEventId": 12345,
  "userId": 10001
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `miEventId` | number | Y | MI Event 식별자 |
| `userId` | number | Y | 요청 사용자 식별자(int) |

Response

```json
{
  "status": "success",
  "message": "성공",
  "data": {
    "scenarioGroupId": 1,
    "status": "creating",
    "stage": "ready"
  }
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | Y | `"success" \| "error"` |
| `message` | string | Y | 처리 결과 메시지 |
| `data.scenarioGroupId` | number | Y | 생성된 시나리오 그룹 ID |
| `data.status` | string | Y | Scenario Group status |
| `data.stage` | string | Y | Scenario Group stage |

Error Response

```json
{
  "status": "error",
  "message": "Event not found for miEventId=113",
  "data": null
}
```

CallBack Body (`CreateScenariosOut`)

> Platform Team에서 정의 예정

```json
{
  "result": "success",
  "reason": null,
  "scenarioGroup": {
    "scenarioGroupId": 12345,
    "miEventId": 998877,
    "eventTypeL2Id": 12,
    "title": "호르무즈 봉쇄 + 전면전",
    "summary": "단기 공급 차질 및 운임 급등 시나리오",
    "description": "상세 설명...",
    "dimensionSelected": ["period_label", "capacity_change", "recovery"],
    "scenarioCount": 5,
    "status": "creating",
    "stage": "scenario_created"
  },
  "table": {
    "headers": [
      { "key": "period_label", "label": "기간", "displayOrder": 1 },
      { "key": "capacity_change", "label": "생산능력 변화", "displayOrder": 2 },
      { "key": "recovery", "label": "공급 복구", "displayOrder": 3 }
    ],
    "rows": [
      {
        "scenarioId": 90001,
        "displayOrder": 1,
        "title": "단기 외교 해결",
        "cells": {
          "period_label": "2026.5월 말 (~2개월)",
          "capacity_change": "15%",
          "recovery": "4~6주 대다수 재기동"
        },
        "baselineYn": "Y"
      }
    ]
  }
}
```

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | Y | `"success" \| "error"` |
| `message` | string | Y | 처리 결과 메시지 |
| `data.scenarioGroup` | object | Y | 시나리오 그룹 메타 정보 |
| `data.scenarioGroup.scenarioGroupId` | number | Y | 시나리오 그룹 ID |
| `data.scenarioGroup.miEventId` | number | Y | 연결된 MI Event ID |
| `data.scenarioGroup.eventTypeL2Id` | number | Y | Event type L2 ID |
| `data.scenarioGroup.title` | string | Y | 시나리오 그룹 제목 |
| `data.scenarioGroup.summary` | string | N | 시나리오 그룹 요약 |
| `data.scenarioGroup.description` | string | N | 시나리오 그룹 상세 설명 |
| `data.scenarioGroup.dimensionSelected` | array(json) | Y | 선택된 테이블 차원 키 목록 |
| `data.scenarioGroup.scenarioCount` | number | Y | 생성 시나리오 개수 |
| `data.scenarioGroup.status` | string | Y | Scenario Group status |
| `data.scenarioGroup.stage` | string | Y | Scenario Group stage |
| `data.table.headers` | array(json) | Y | 테이블 헤더 정의 |
| `data.table.headers[].key` | string | Y | 컬럼 키(예: `period_label`) |
| `data.table.headers[].label` | string | Y | 표시 라벨 |
| `data.table.headers[].displayOrder` | number | Y | 표시 순서 |
| `data.table.rows` | array(json) | Y | 시나리오 행 목록 |
| `data.table.rows[].scenarioId` | number | Y | 시나리오 ID |
| `data.table.rows[].displayOrder` | number | Y | 표시 순서 |
| `data.table.rows[].title` | string | Y | 시나리오 제목 |
| `data.table.rows[].narrative` | string | N | 시나리오 내러티브 |
| `data.table.rows[].cells` | object | Y | 헤더 key별 셀 값 |
| `data.table.rows[].metrics` | object | N | 확률/실현가능성 등 메트릭 |
| `data.table.rows[].baselineYn` | CHAR(1) | N | Baseline 여부(`"Y" \| "N"`) |

### 2) 시나리오 검증

- Method/Path: `POST /scenario-groups/{scenarioGroupId}/validation`
- Description: 생성된 시나리오 그룹의 유효성을 검증한다.
- Path Param: `scenarioGroupId` (int)

Request body

```json
{
  "user_id": "10001",
  "table": {
    "headers": [
      { "key": "period_label", "label": "기간", "displayOrder": 1 },
      { "key": "capacity_change", "label": "생산능력 변화", "displayOrder": 2 },
      { "key": "recovery", "label": "공급 복구", "displayOrder": 3 },
      { "key": "new_dimension", "label": "새로운 분기항목(예시)", "displayOrder": 3 }
    ],
    "rows": [
      {
        "scenarioId": 90001,
        "displayOrder": 1,
        "title": "단기 외교 해결(시나리오명1)",
        "cells": {
          "period_label": "2026.5월 말 (~2개월)",
          "capacity_change": "15%",
          "recovery": "4~6주 대다수 재기동",
          "new_dimension": null
        }
      }
    ]
  }
}
```

> `new_dimension` 처럼 분기 기준 추가로 인해 agent가 자동생성 해야 하는 값인 경우 `null`로 넣어주세요.

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `user_id` | number | Y | 요청 사용자 식별자(int) |
| `scenarioGroup` | object | Y | 검증 대상 시나리오 그룹 정보 |
| `scenarioGroup.scenarioGroupId` | number | Y | 시나리오 그룹 ID |
| `scenarioGroup.miEventId` | number | Y | 연결된 MI Event ID |
| `scenarioGroup.eventTypeL2Id` | number | Y | Event type L2 ID |
| `scenarioGroup.title` | string | Y | 제목 |
| `scenarioGroup.summary` | string | N | 요약 |
| `scenarioGroup.description` | string | N | 상세 설명 |
| `table.headers` | array(json) | Y | 테이블 헤더 정의 |
| `table.rows` | array&lt;object&gt; | Y | 검증 대상 시나리오 행 목록 |
| `table.rows[].scenarioId` | number | Y | 시나리오 ID |
| `table.rows[].cells` | object | Y | 헤더 key별 셀 값 |

Response (`ValidateScenariosOut`)

```json
{
  "status": "success",
  "message": "성공",
  "data": {
    "scenarioGroupId": 1,
    "status": "creating",
    "stage": "scenario_created"
  }
}
```

Error Response

```json
{
  "status": "error",
  "message": "Event not found for ScenarioGroupId=113",
  "data": null
}
```

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | Y | `"success" \| "error"` |
| `message` | string | Y | 처리 결과 메시지 |
| `data.scenarioGroupId` | number | Y | 시나리오 그룹 ID |
| `data.isValid` | boolean | N | 검증 결과(상세 포함 시) |
| `data.reason` | string | N | 검증 사유(상세 포함 시) |
| `data.status` | string | Y | Scenario Group status |
| `data.stage` | string | Y | Scenario Group stage |

Callback Body

```json
{
  "result": "success",
  "isValid": true,
  "reason": "MECE and plausibility checks passed",
  "scenarioGroup": {
    "scenarioGroupId": 12345,
    "status": "creating",
    "stage": "scenario_validated"
  },
  "table": {
    "headers": [
      { "key": "period_label", "label": "기간", "displayOrder": 1 },
      { "key": "capacity_change", "label": "생산능력 변화", "displayOrder": 2 },
      { "key": "recovery", "label": "공급 복구", "displayOrder": 3 },
      { "key": "new_dimension", "label": "새로운 분기항목(예시)", "displayOrder": 3 }
    ],
    "rows": [
      {
        "scenarioId": 90001,
        "displayOrder": 1,
        "title": "단기 외교 해결(시나리오명1)",
        "cells": {
          "period_label": "2026.5월 말 (~2개월)",
          "capacity_change": "15%",
          "recovery": "4~6주 대다수 재기동",
          "new_dimension": "new_value"
        }
      }
    ]
  }
}
```

> `table`은 agent가 자동생성한 값을 포함한 전체 테이블의 header/value를 담습니다. Agent가 자동생성한 값은 DB에는 저장하지 않습니다.

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | Y | `"success" \| "error"` |
| `message` | string | Y | 처리 결과 메시지 |
| `data.scenarioGroupId` | number | Y | 시나리오 그룹 ID |
| `data.isValid` | boolean | Y | 검증 결과 |
| `data.reason` | string | N | 검증 사유/코멘트 |
| `data.table` | object | Y | 검증 후 테이블(헤더/행) |
| `data.table.headers` | array(json) | Y | 테이블 헤더 정의 |
| `data.table.headers[].key` | string | Y | 컬럼 키(예: `period_label`) |
| `data.table.headers[].label` | string | Y | 표시 라벨 |
| `data.table.headers[].displayOrder` | number | Y | 표시 순서 |
| `data.table.rows` | array(json) | Y | 검증 결과 행 목록 |
| `data.table.rows[].scenarioId` | number | Y | 시나리오 ID |
| `data.table.rows[].displayOrder` | number | Y | 표시순서 |
| `data.table.rows[].title` | string | Y | 시나리오 제목 |
| `data.table.rows[].cells` | object | Y | 헤더 key별 셀 값(검증/자동생성 값 포함) |
| `data.status` | string | Y | Scenario Group status |
| `data.stage` | string | Y | Scenario Group stage |

### 3) Signpost 생성

- Method/Path: `POST /scenario-groups/{scenarioGroupId}/signposts`
- Description: 시나리오 그룹 기준 signpost를 생성한다.
- Path Param: `scenarioGroupId` (int)

Request (body)

```json
{
  "userId": 10001,
  "table": {
    "headers": [
      { "key": "period_label", "label": "기간", "displayOrder": 1 },
      { "key": "capacity_change", "label": "생산능력 변화", "displayOrder": 2 },
      { "key": "recovery", "label": "공급 복구", "displayOrder": 3 },
      { "key": "new_dimension", "label": "새로운 분기항목(예시)", "displayOrder": 3 }
    ],
    "rows": [
      {
        "scenarioId": 90001,
        "displayOrder": 1,
        "title": "단기 외교 해결(시나리오명1)",
        "cells": {
          "period_label": "2026.5월 말 (~2개월)",
          "capacity_change": "15%",
          "recovery": "4~6주 대다수 재기동",
          "new_dimension": "new_value"
        }
      },
      {
        "scenarioId": null,
        "displayOrder": 2,
        "title": "중장기 갈등 해소(시나리오명2)",
        "cells": {
          "period_label": "~6개월",
          "capacity_change": "30%",
          "recovery": "9주 대다수 재기동",
          "new_dimension": "new_value"
        }
      }
    ]
  }
}
```

> 검증이 끝난 뒤 사용자가 추가한 신규 시나리오는 `scenarioId: null`로 보내주세요. Signpost 생성 request body의 값으로 scenarioGroup, scenario 테이블을 업데이트합니다.

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `userId` | number | N | 요청 사용자 식별자(int) |
| `table` | object | Y | Signpost 생성을 위한 테이블(헤더/행) |
| `table.headers` | array(json) | Y | 테이블 헤더 정의 |
| `table.headers[].key` | string | Y | 컬럼 키(예: `period_label`) |
| `table.headers[].label` | string | Y | 표시 라벨 |
| `table.headers[].displayOrder` | number | Y | 표시 순서 |
| `table.rows` | array(object) | Y | 대상 시나리오 행 목록 |
| `table.rows[].scenarioId` | number | Y | 시나리오 ID |
| `table.rows[].displayOrder` | number | Y | 표시 순서 |
| `table.rows[].title` | string | Y | 시나리오 제목 |
| `table.rows[].cells` | object | Y | 헤더 key별 셀 값 |

Response (`CreateSignpostsOut`)

```json
{
  "status": "success",
  "message": "성공",
  "data": {
    "scenarioGroupId": 1001,
    "status": "creating",
    "stage": "scenario_validated"
  }
}
```

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | Y | `"success" \| "error"` |
| `message` | string | Y | 처리 결과 메시지 |
| `data.scenarioGroupId` | number | Y | 시나리오 그룹 ID |
| `data.status` | string | Y | Scenario Group status |
| `data.stage` | string | Y | Scenario Group stage |

Error Response

```json
{
  "status": "error",
  "message": "Event not found for ScenarioGroupId=1001",
  "data": null
}
```

Callback Body

```json
{
  "result": "success",
  "reason": null,
  "scenarioGroup": {
    "scenarioGroupId": 12345,
    "miEventId": 998877,
    "eventTypeL2Id": 12,
    "title": "호르무즈 봉쇄 + 전면전",
    "dimensionSelected": ["period_label", "capacity_change", "recovery"],
    "scenarioCount": 5,
    "status": "creating",
    "stage": "signpost_created"
  },
  "table": {
    "headers": [
      { "key": "period_label", "label": "기간", "displayOrder": 1 },
      { "key": "capacity_change", "label": "생산능력 변화", "displayOrder": 2 },
      { "key": "recovery", "label": "공급 복구", "displayOrder": 3 }
    ],
    "rows": [
      {
        "scenarioId": 90001,
        "displayOrder": 1,
        "title": "단기 외교 해결",
        "narrative": "시나리오 내러티브...",
        "cells": {
          "period_label": "2026.5월 말 (~2개월)",
          "capacity_change": "15%",
          "recovery": "4~6주 대다수 재기동"
        },
        "metrics": {
          "probabilityScore": 75.0,
          "probabilityDelta": 0.0
        },
        "baselineYn": "Y",
        "signposts": [
          {
            "signpostId": 1,
            "label": "호르무즈 봉쇄 장기화",
            "probabilityDirectionCode": "sup",
            "probabilityImpactScore": 12.5,
            "signpostReason": "운송 리스크 확대 및 대체 항로 비용 증가",
            "displayOrder": 1,
            "strength": "STRONG"
          }
        ]
      }
    ]
  }
}
```

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | Y | `"success" \| "error"` |
| `message` | string | Y | 처리 결과 메시지 |
| `data.scenarioGroup` | object | Y | 시나리오 그룹 메타 정보 |
| `data.table` | object | Y | 시나리오 테이블(행 + signposts 포함) |
| `data.table.rows[].signposts` | array(json) | Y | 시나리오별 Signpost 목록 |
| `data.table.rows[].signposts[].signpostId` | number | Y | Signpost ID |
| `data.table.rows[].signposts[].label` | string | Y | Signpost 라벨 |
| `data.table.rows[].signposts[].probabilityDirectionCode` | string | N | 확률 방향 코드(phase1에서는 `"sup"` 단일, 가능성강화) |
| `data.table.rows[].signposts[].probabilityImpactScore` | DECIMAL(5,2) | N | 확률 영향 점수 |
| `data.table.rows[].signposts[].signpostReason` | string | N | Signpost 사유 |
| `data.table.rows[].signposts[].displayOrder` | number | N | 표시 순서 |
| `data.table.rows[].signposts[].strength` | string | N | Signpost 강도(예: STRONG/MEDIUM/WEAK) |

### 4) 생성 확정

- Method/Path: `POST /scenario-groups/{scenarioGroupId}/confirmation`
- Description: 시나리오/사인포스트 생성 결과를 확정하고 스냅샷을 남긴다.
- Path Param: `scenarioGroupId` (int)

Request Body:

```json
{
  "scenarioGroup": {
    "title": "호르무즈 봉쇄 + 전면전",
    "summary": "단기 공급 차질 및 운임 급등 시나리오",
    "description": "상세 설명..."
  },
  "table": {
    "headers": [
      { "key": "period_label", "label": "기간", "displayOrder": 1 },
      { "key": "capacity_change", "label": "생산능력 변화", "displayOrder": 2 },
      { "key": "recovery", "label": "공급 복구", "displayOrder": 3 }
    ],
    "rows": [
      {
        "scenarioId": 90001,
        "displayOrder": 1,
        "title": "단기 외교 해결",
        "narrative": "시나리오 내러티브...",
        "cells": {
          "period_label": "2026.5월 말 (~2개월)",
          "capacity_change": "15%",
          "recovery": "4~6주 대다수 재기동"
        },
        "metrics": {
          "probabilityScore": 75.0,
          "probabilityDelta": 0.0
        },
        "baselineYn": "Y",
        "signposts": [
          {
            "signpostId": 1,
            "label": "호르무즈 봉쇄 장기화",
            "probabilityDirectionCode": "sup",
            "signpostReason": "운송 리스크 확대 및 대체 항로 비용 증가",
            "displayOrder": 1,
            "strength": "STRONG",
            "useYn": "Y"
          }
        ]
      }
    ]
  }
}
```

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `scenarioGroup` | object | Y | 확정 대상 시나리오 그룹 |
| `table` | object | Y | 확정 대상 시나리오 테이블(행 + signposts 포함) |

Response (`ConfirmGenerationOut`)

```json
{
  "status": "success",
  "message": "성공",
  "data": {
    "scenarioGroupId": 1001,
    "status": "created",
    "stage": "completed"
  }
}
```

| Path | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | string | Y | `"success" \| "error"` |
| `message` | string | Y | 처리 결과 메시지 |
| `data.scenarioGroupId` | number | Y | 시나리오 그룹 ID |
| `data.status` | string | Y | Scenario Group status |
| `data.stage` | string | Y | Scenario Group stage |

## 공통 응답 필드

- `status`: `"success" | "error"`
- `message`: 처리 결과 메시지

## 수정 이력

| 버전 | 수정내용 | 수정날짜 | 배포여부 (버전) |
| --- | --- | --- | --- |
| v2 | Req/Res body table 추가<br>`summary`, `description` 필수값을 `Y -> N`으로 변경(nullable 반영)<br>Signpost의 `probabilityDirectionCode`, `probabilityImpactScore` 필수값을 `Y -> N`으로 변경(nullable 반영)<br>예시 JSON 3곳에서 `feasibilityScore` 제거<br>Validation 요청의 `user_id` 표기 정리<br>Confirmation response의 `stage`는 `completed`로 반영된 상태 유지 | 26/06/10 | 외부망 배포<br>(v0.0.1) |
| v3 | Request Body의 user_id 를 string -> number(int) 타입으로 변경<br>confirmation API 에서 안쓰는 파라미터 삭제(scenarioGroupId, eventId 등) | 26/06/11 | 외부망 배포<br>(v0.0.2) |
| v4 | Validation API의 Request Body의 scenarioGroup 삭제(사유: 사용자가 수정못하는 영역이라 DB값 읽기로 함) | 26/06/12 | 외부망 배포<br>(v0.0.3) |
| v5 | 시나리오 검증 API의 request에 새로 추가된 dimension에 대한 예시 추가<br>시나리오 검증 API의 Callback Body에 table 필드 추가<br>Signpost 생성 API의 request body로 table 전체 수신<br>signpost 생성 callback body의 signpost 필드(`strength`, `keyword_hint`) 추가<br>확정 API의 request body의 signpost 필드(`strength`, `keyword_hint`) 추가<br>callback body를 platform에서 정의한 callback body(v1) 형식으로 업데이트 | 26/06/15 | - |
| v6 | 시나리오 검증(Validation) request body와 callback body에 `displayOrder`, `title` 추가<br>확률 방향 코드(phase1에서는 `"SUP"`만 있음) | 26/06/16 | - |
| v7 | Signpost 생성 Callback Body를 Platform Callback API(v2)에 맞게 수정<br>`probabilityDirectionCode` 값을 `"sup"`로 변경<br>`probabilityImpactScore` 추가<br>Callback Body에서 `scenarioGroup.summary`, `scenarioGroup.description`, `signposts[].useYn`, `signposts[].keyword_hints` 제거 | 26/06/18 | - |
| v8 | 시나리오 가격 영향 방향 생성을 중단하고 신규 `impact_jkm/ttf/hh`를 `NULL`로 저장<br>공통 Scenario table 및 confirmation request/response에서 `impact` 제거 | 26/07/20 | - |
