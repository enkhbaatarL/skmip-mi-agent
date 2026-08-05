# Scenario Comparison Backoffice Design

## 1. 문서 목적

이 문서는 [`PRD.md`](./PRD.md)에 정의된 Scenario Comparison Backoffice의 화면 구조, frontend 상태, API orchestration, 컴포넌트, 반응형 및 접근성 기준을 정의한다.

Backoffice는 Scenario Group Agent의 sync API를 직접 호출하는 내부 QA용 정적 frontend다. 다음 두 workspace를 분리해 제공한다.

1. v1 단일 이벤트 sync pipeline
2. v2/v3/v4 다중 이벤트 생성 결과 비교

기존 Backoffice FastAPI backend, callback receiver, OAuth mock, SSE, 운영용 Scenario Group 관리 화면은 설계 범위에 포함하지 않는다.

## 2. 설계 원칙

- 두 workflow를 섞지 않는다.
  - v1은 unversioned create부터 confirmation까지 순차 실행한다.
  - v2/v3/v4는 create sync API 결과를 비교하고, 사용자가 요청한 경우에만 별도 의미 품질 평가를 실행한다.
- 화면은 결과보다 실행 조건을 먼저 보여준다.
  - Event, userId, Base URL, comparisonRunId를 항상 확인할 수 있어야 한다.
- 기본 화면은 API 응답을 사용자용 presentation view로 변환한다.
  - 내부 Dimension/Value ID 대신 label, 설명, lineage, 실제 근거를 표시한다.
  - 원본 request/response는 secret redaction 외 의미 변환 없이 Raw 탭과 Evidence Drawer에 별도 증적으로 보존한다.
- 중복 생성보다 안전한 중단을 우선한다.
  - create POST는 자동 재시도하지 않는다.
  - timeout과 취소는 `unknown`으로 보존한다.
- 긴 실행 중에도 기존 결과를 유지한다.
- HTTP 상태와 API body 판정을 분리한다.
- secret은 frontend bundle, browser storage, export 파일에 남기지 않는다.
- 정보 밀도는 높게 유지하되 버전과 단계 상태는 색상 외의 텍스트로도 구분한다.

## 3. 전체 IA

```text
App Shell
  ├─ Header
  │    ├─ Product title
  │    ├─ Agent connection status
  │    └─ Runtime Settings
  ├─ Workspace Tabs
  │    ├─ v1 단일 이벤트
  │    └─ v2/v3/v4 비교
  ├─ Active Workspace
  └─ Evidence Drawer
       ├─ Request
       ├─ Response
       ├─ Raw
       └─ Export
```

별도 landing page, production navigation, account menu, Scenario Group List 화면은 두지 않는다.

## 4. App Shell

### 4.1 Header

왼쪽:

- 제목 `Scenario Comparison`
- 보조 설명 `Scenario Group Agent QA`

오른쪽:

- 연결 상태 badge
  - `연결 안 됨`
  - `확인 중`
  - `연결됨`
  - `연결 실패`
- `Runtime 설정` toggle 또는 button

Header는 workspace를 전환해도 유지한다.

### 4.2 Runtime Settings

desktop에서는 header 아래 compact horizontal panel, 좁은 화면에서는 drawer 또는 stacked panel로 표시한다.

필드:

- `Agent Base URL`
- `userId`
- `Timeout (seconds)`
- 선택적 인증 입력

액션:

- `연결 확인`
- `저장`
- `초기화`

규칙:

- Base URL의 trailing slash는 API client에서 정규화한다.
- userId는 정수만 허용한다.
- timeout 기본값은 1,200초다.
- 실행 중인 workspace가 있으면 해당 실행에 고정된 runtime 값은 변경하지 못한다.
- 인증 값은 memory에만 유지하고 마스킹한다.
- 마지막 Base URL, userId, timeout만 browser storage에 저장할 수 있다.

연결 확인:

- `GET /events?page=1&pageSize=1`을 우선 사용한다.
- 환경에 별도 health endpoint가 있으면 대체 가능하다.
- 연결 실패 시 CORS, mixed content, network, HTTP/API 오류를 구분해 안내한다.

### 4.3 Workspace Tabs

- `v1 단일 이벤트`
- `v2/v3/v4 비교`

각 tab은 다음 상태 dot을 가질 수 있다.

- 회색: 실행 없음
- 파랑: 실행 중
- 초록: 성공
- 주황: warning 또는 unknown
- 빨강: 실패

tab 전환은 실행을 취소하거나 상태를 초기화하지 않는다.

### 4.4 Evidence Drawer

오른쪽 drawer 또는 화면 하단 panel로 제공한다.

기능:

- API call timeline
- 선택한 call의 URL/method
- request body
- parsed response
- raw response text
- HTTP status와 transport status
- 시작/종료 시각과 elapsed time
- 판정과 오류
- JSON 검색, 접기, 복사
- 현재 실행 bundle export

drawer는 workflow의 주요 콘텐츠 폭을 지나치게 줄이지 않도록 desktop에서 420~560px, tablet/mobile에서는 full-width overlay를 사용한다.

## 5. 공통 Event Selector

### 5.1 선택 모드

segmented control:

- `ID 직접 입력`
- `목록에서 선택`

목록 모드의 filter:

- keyword
- 최신순/오래된순
- status
- Event Type L1/L2
- 추천 항목만
- paging

v1은 Event 한 건만 선택할 수 있다. 비교 workspace는 중복 없는 Event 2~5건을 선택할 수 있다.

### 5.2 Event Table

컬럼:

- 선택
- `miEventId`
- Event 제목
- 발생 시각
- Event Type L1/L2
- JKM
- TTF
- HH
- Scenario 추천 상태
- 기존 Scenario Group 상태

행 선택 후 상세를 조회해 Event summary panel에 표시한다.

### 5.3 Selected Event Card

표시 항목:

- Event ID와 제목
- 한 줄 요약
- 발생 시각
- Event Type
- key bullets
- JKM/TTF/HH 영향
- Scenario 추천 사유
- 기존 Scenario Group ID/status/stage

다중 Event에서는 카드 순서가 manifest의 Event 순서가 된다. drag-and-drop은 제공하지 않고 선택 순서를 명시적으로 표시한다.

### 5.4 상태

- loading: table skeleton
- empty: filter를 유지하고 `조건에 맞는 Event가 없습니다.`
- error: 기존 선택을 유지하고 inline error
- disabled Event: 선택 불가 사유 tooltip 또는 helper text

## 6. v1 단일 이벤트 Workspace

### 6.1 화면 구조

```text
V1 Run Header
  - selected Event
  - scenarioGroupId
  - status/stage
  - elapsed/token

Step Rail
  1. Create
  2. Validation
  3. Signpost
  4. Confirmation

Active Step Content
  - request preview
  - result summary
  - editable Scenario table or Signpost view

Run Timeline
```

초기에는 Event selector와 `Create 실행` 버튼만 활성화한다.

### 6.2 V1 Run Header

표시:

- Event ID와 제목
- `scenarioGroupId`
- 현재 Agent status/stage
- 현재 step
- 전체 elapsed time
- 누적 token usage
- run 상태

액션:

- `새 실행`
- `결과 Export`
- 선택적 `기존 Group 정리`

`새 실행`은 현재 결과가 있으면 export 여부를 확인한 뒤 별도 run state를 만든다.

### 6.3 Step Rail

상태:

- `idle`
- `ready`
- `running`
- `success`
- `warning`
- `error`
- `unknown`

표시 규칙:

- active step은 blue border와 상태 text를 사용한다.
- 완료 step은 check icon과 결과 요약을 표시한다.
- warning은 다음 단계 진행 가능 여부를 helper text로 알린다.
- error/unknown 이후 단계는 잠금 상태와 사유를 표시한다.

### 6.4 Step 1: Create

API:

```http
POST /scenario-groups/sync
```

화면:

- 선택 Event summary
- request preview
- 기존 Scenario Group 경고
- `Create 실행`
- response summary
- Scenario table

성공 표시:

- `result=success`
- Scenario Group ID
- status/stage
- Scenario 수
- dimension 수
- elapsed time
- token usage

실패:

- HTTP 200의 `result=failure`도 error callout으로 표시한다.
- 중복 생성 오류면 기존 Group ID와 soft delete 안내를 보여준다.
- 자동 재시도하지 않는다.

### 6.5 Editable Scenario Table

Create 성공 후 표시한다.

고정 컬럼:

- 순서
- baseline
- title
- narrative
- probability
- role
- pressure band/rationale가 있으면 해당 값

동적 컬럼:

- API table header 순서에 따른 dimension cell

편집:

- title, narrative, probability, dimension cell
- row 추가/삭제
- 원본값으로 row reset
- 전체 reset

규칙:

- API 식별자는 편집 중에도 유지한다.
- display order는 중복되지 않게 다시 계산한다.
- 삭제한 row는 다음 request body에서 제외한다.
- baseline 변경은 명시적 control을 사용한다.
- validation request preview에서 최종 정규화 table을 보여준다.

### 6.6 Step 2: Validation

API:

```http
POST /scenario-groups/{scenarioGroupId}/validation/sync
```

화면:

- validation request preview
- `Validation 실행`
- 결과 badge
- `isValid`, `stage`, reason
- 수정 권장 사항

판정:

- `stage=scenario_validated`: success
- invalid 또는 `stage=scenario_created`: warning
- transport/API failure: error

invalid는 입력값을 유지한다. 사용자가 warning을 확인하면 signpost 단계로 계속할 수 있다.

validation을 다시 실행하는 경우 request preview와 확인 dialog를 거친다.

### 6.7 Step 3: Signpost

API:

```http
POST /scenario-groups/{scenarioGroupId}/signposts/sync
```

화면:

- 현재 Scenario table
- request preview
- `Signpost 실행`
- Scenario별 Signpost accordion
- 결과 요약

Signpost 표시:

- label
- direction
- impact
- core evidence
- 연결 Scenario

성공 판정은 `result=success`다. 실패 시 confirmation을 잠근다.

### 6.8 Step 4: Confirmation

Confirmation 직전에 최신 detail을 조회한다.

```http
GET /scenario-groups/{scenarioGroupId}
```

확정 API:

```http
POST /scenario-groups/{scenarioGroupId}/confirmation
```

화면:

- Scenario Group name/description
- 최종 Scenario table
- Signpost summary
- confirmation request preview
- `Confirmation 실행`
- 최종 status/stage

성공 판정:

- `status=success`
- `data.stage=completed`

완료 후에도 별도 detail 관리 화면으로 이동하지 않는다. 현재 workspace에 final summary와 원본 응답을 유지한다.

## 7. v2/v3/v4 비교 Workspace

### 7.1 화면 단계

```text
1. 비교 조건
2. 실행
3. 비교 결과
4. 선택적 품질 평가
```

### 7.2 비교 조건

필드:

- Event 2~5건
- userId
- `comparisonRunId`

`comparisonRunId`:

- 기본값은 `multi-event-{timestamp}-{random}` 형식이다.
- 사용자가 수정할 수 있으나 실행 시작 시 lock한다.
- 공백과 255자 초과를 허용하지 않는다.

### 7.3 Manifest Summary

실행 전 confirmation panel에서 다음을 보여준다.

- Base URL
- userId
- Event ID와 순서
- Event detail 조회 성공 여부
- comparisonRunId
- 요청 timeout

`비교 실행`을 누르면 manifest를 고정하고 입력 control을 잠근다.

### 7.4 실행 상태 Board

version card 3개를 가로로 배치한다.

각 card:

- v2/v3/v4 label
- generation strategy
- 상태
- 시작/종료 시각
- elapsed time
- HTTP status
- Scenario Group ID
- token usage
- 오류 요약

실행 순서:

```text
v2 ─┐
    ├─ barrier ─→ v4
v3 ─┘
```

- v2와 v3는 동시에 시작한다.
- 둘 다 terminal state가 된 후 v4를 시작한다.
- terminal state는 success, error, unknown이다.
- v4가 시작되기 전 card에 `v2/v3 종료 대기`를 표시한다.
- 동일 version POST는 한 번만 허용한다.
- 취소 또는 timeout은 unknown으로 남긴다.

### 7.5 비교 결과 Navigation

비교 결과 내부 tab:

- `Overview`
- `Dimensions`
- `Scenarios`
- `Diagnostics`
- `Raw`

성공 version이 2개 미만이면 상단에 `비교 판정 불가` callout을 표시하되 성공한 결과의 개별 view는 제공한다.

`Raw`는 기본 해석 화면이 아니다. Group, Dimension, Scenario 탭이 사용자용 label과 근거를 제공하고, Raw는 원본 확인·복사·디버깅이 필요할 때만 사용한다.

### 7.6 Overview

버전별 비교 table:

- API status
- generation strategy
- Scenario Group ID/name
- Event 수
- dimension 수
- Scenario 수
- baseline
- floor/ceiling/mixed 수
- pressure band 분포
- probability 합계
- lineage coverage
- diagnostics coverage
- elapsed time
- token usage
- 결정적 검사 결과
- 의미 품질 평가 상태

열은 v2, v3, v4 순서를 고정한다.

v2/v3/v4 모두 `Global LNG pressure` label을 사용한다. v4의
`relatedMarkets`는 기본 표 열이나 pressure 태그가 아니라 Scenario 상세의
보조정보로만 표시한다.

Overview 상단에는 version별 Scenario Group 제목·요약·설명을 분리해 보여준다. ID와 count만으로 그룹 의미를 대신하지 않는다.

### 7.7 Dimensions

두 가지 view를 제공한다.

1. version별 list
2. source lineage matrix

dimension row:

- label
- description
- values
- source Event
- source dimension
- lineage type
- Dimension 선택 근거
- Value별 label, global pressure contribution, 선택/가정 근거
- lever references
- supported/unsupported
- covered/uncovered

version별 차이:

- v2: `e{eventId}__{dimKey}` namespace를 강조한다.
- v3: composite dimension과 다중 source 관계를 표시한다.
- v4: Event grounding, model lever, parameter binding, unsupported reason을 표시한다.

`dimensionId`와 `valueId`는 adapter의 lookup key로만 사용하고 기본 UI에는 사용자용 label을 표시한다. 같은 label이 둘 이상이면 `Event <lineage>`를 붙인다. 실제 응답에 근거가 없으면 `제공된 근거 없음`으로 표시하며 UI가 새 근거를 만들지 않는다.

### 7.8 Scenarios

기본 정렬:

1. floor
2. mixed 또는 내부 band
3. baseline marker
4. ceiling

실제 응답의 role/pressure band를 기준으로 정렬하며 없는 값을 추측하지 않는다.

비교 방식:

- desktop: version column 3개
- tablet/mobile: version switcher와 한 version씩 표시

Scenario card:

- order
- baseline
- role
- title
- narrative
- label 기반 Dimension/Value 조합
- Dimension 선택 근거
- 선택 Value의 실제 근거
- pressure band
- pressure rationale
- probability
- Event coverage
- 의미 품질 평가가 완료된 경우 Scenario별 verdict와 판단 근거

대응 Scenario가 없으면 `생성되지 않음`과 excluded reason을 표시한다.

### 7.9 Diagnostics

공통:

- target pressure bands
- excluded candidates
- excluded dimensions
- covered/uncovered dimensions
- coverage status
- Event impact facts
- Event interactions

v4:

- impact catalog version
- unsupported levers
- unsupported lever details

긴 진단 값은 summary와 expandable raw block을 함께 제공한다.

### 7.10 결정적 검사

version card 및 Overview에 PASS/WARN/FAIL을 표시한다.

검사항목은 M-01~M-08로 고정한다.

- M-01: Scenario 3~5개
- M-02: baseline 정확히 1개
- M-03: Scenario 조합과 pressure band 존재·고유성
- M-04: floor/ceiling 각각 1개, role과 극단 band 정합성, optional mixed 정합성
- M-05: v2/v3/v4 Dimension 각각 3~6개
- M-06: 전체 입력 Event lineage coverage
- M-07: Scenario별 global pressure rationale 존재
- M-08: 생성·제외 결과가 target pressure band 전체를 설명

mixed가 없으면 M-04에서 실패시키지 않는다. mixed가 있으면 비극단 band인지, 선택 Value에 상승·하락 contribution이 함께 존재하는지, `globalPressureRationale`이 상쇄 관계를 설명하는지 확인한다. contribution 의미가 응답만으로 확정되지 않으면 추측하지 않고 WARN으로 표시한다.

결정적 검사는 의미적 LLM 평가가 아니며 우수 version을 직접 선정하지 않는다.

### 7.11 의미 품질 평가

create 결과가 모두 terminal 상태이고 성공 version이 2개 이상이면 Overview에 품질 평가 panel을 표시한다.

미실행 상태:

- 평가 대상 version
- Event/API 증적만 사용한다는 안내
- 추가 LLM 호출로 시간과 token이 사용된다는 안내
- `품질 평가 실행` button

실행 후:

- 단독 또는 공동 우수 version badge
- version별 적용 가능 기준 평균
- Event 정합성, LNG Dimension, floor/ceiling, mixed 품질의 score/verdict/rationale/evidence
- version별 strengths/weaknesses
- 종합 결론
- Scenario card에 연결되는 Scenario별 판단

mixed 품질은 다음처럼 표시한다.

- mixed 없음: `N/A`, score 없음, 평균 제외
- mixed 있음: 실제 상승·하락 Value 조합과 상쇄 근거를 1~5점으로 평가

품질 평가는 create와 자동 연결하지 않는다. 사용자가 버튼을 눌렀을 때만 `POST /scenario-group-comparisons/judge/sync`를 호출한다. 실패·timeout은 create 결과를 유지한 채 judge 상태만 error/unknown으로 표시하고 `품질 평가 다시 실행`을 제공한다.

## 8. Frontend 상태 설계

### 8.1 공통 타입

```ts
type RunStatus =
  | "idle"
  | "ready"
  | "running"
  | "success"
  | "warning"
  | "error"
  | "unknown";

interface ApiCallRecord {
  id: string;
  workflow: "v1" | "comparison";
  step: string;
  version?: "v2" | "v3" | "v4";
  method: string;
  url: string;
  request?: unknown;
  startedAt: string;
  finishedAt?: string;
  elapsedMs?: number;
  httpStatus?: number;
  transportStatus: "pending" | "success" | "error" | "unknown";
  parsedResponse?: unknown;
  rawResponse?: string;
  judgment?: RunStatus;
  error?: string;
}
```

### 8.2 V1 State

```ts
interface V1RunState {
  runId: string;
  runtime: RuntimeSnapshot;
  event?: EventDetail;
  scenarioGroupId?: number;
  currentStep: "create" | "validation" | "signpost" | "confirmation";
  steps: Record<string, StepState>;
  editableTable?: ScenarioTable;
  scenarioGroup?: ScenarioGroup;
  signposts?: unknown[];
  calls: ApiCallRecord[];
}
```

### 8.3 Comparison State

```ts
interface ComparisonRunState {
  runId: string;
  runtime: RuntimeSnapshot;
  manifest: ComparisonManifest;
  versions: Record<"v2" | "v3" | "v4", VersionRunState>;
  checks: Record<"v2" | "v3" | "v4", DeterministicCheckResult[]>;
  qualityJudge: QualityJudgeState;
  calls: ApiCallRecord[];
}

interface QualityJudgeState {
  status: "idle" | "ready" | "running" | "success" | "error" | "unknown";
  request?: ComparisonJudgeRequest;
  response?: ComparisonJudgeResponse;
  call?: ApiCallRecord;
  error?: string;
}
```

### 8.4 저장 정책

memory:

- 진행 중 request
- AbortController
- 인증값
- 현재 편집 draft

browser storage:

- Base URL, userId, timeout
- 최근 실행 metadata
- 크기 제한 내의 결과
- 품질 평가 상태와 결과

export:

- manifest
- request/response
- 판정
- 시간/token
- 결정적 검사
- 의미 품질 평가 request/response와 우수 version

인증 header와 secret은 storage/export 전에 제거한다.

## 9. API Client와 Orchestration

### 9.1 Agent Client

책임:

- Base URL 정규화
- JSON request/response
- timeout과 AbortController
- raw response 보존
- HTTP/API 오류 분리
- call record 생성
- 민감 header redaction

`fetch`의 network error만으로 서버 실행 실패를 단정하지 않는다. POST 전송 후 응답을 받지 못한 경우 상태는 unknown이 될 수 있다.

### 9.2 V1 Controller

```text
load event detail
  → create
  → normalize editable table
  → validation
  → normalize returned/latest table
  → signpost
  → get detail
  → confirmation
```

각 단계는 사용자의 명시적 action으로 실행한다. controller는 다음 단계의 request를 미리 보내지 않는다.

### 9.3 Comparison Controller

```ts
const [v2, v3] = await Promise.allSettled([
  runVersion("v2", manifest),
  runVersion("v3", manifest),
]);

const v4 = await runVersion("v4", manifest);
```

`runVersion`은 같은 run/version에 대해 한 번만 실행되는 guard를 가진다.

- v2/v3 실패도 barrier 완료로 본다.
- v2/v3 promise가 terminal 처리되기 전 v4를 호출하지 않는다.
- v2/v3/v4 request는 동일한 Event, userId, comparisonRunId를 사용한다.
- version별 결과는 독립적으로 보존한다.

품질 평가는 별도 사용자 action이다.

```ts
const successfulGroups = successfulVersions(run).map(({ version, groupId }) => ({
  apiVersion: version,
  scenarioGroupId: groupId,
}));

if (successfulGroups.length >= 2) {
  await runQualityJudge(manifest.comparisonRunId, runtime.userId, successfulGroups);
}
```

- 성공 version 2~3개만 요청한다.
- create 실패 version은 제외하되 실패 사유는 기존 version card에 유지한다.
- judge 호출은 create POST guard와 분리한다.
- judge는 읽기 전용이므로 실패 후 사용자 확인으로 재호출할 수 있다.

### 9.4 API Body 판정

v1:

- create/signpost: `result=success`
- validation: `stage=scenario_validated` 또는 invalid warning
- confirmation: `status=success && data.stage=completed`

comparison:

- HTTP 2xx
- `status=success`
- `data.apiVersion` 일치
- `data.comparisonRunId` 일치
- Event lineage 일치

quality judge:

- HTTP 2xx와 `status=success`
- 요청 version과 응답 version 집합 일치
- 각 version의 필수 평가 기준과 Scenario 판단 집합 일치
- `mixed_quality=N/A`이면 `score=null`
- 평균과 `bestVersions`가 서버 계산 결과와 일치

## 10. 컴포넌트 구조

```text
App
├─ AppHeader
├─ RuntimeSettings
├─ WorkspaceTabs
├─ V1Workspace
│  ├─ EventSelector
│  ├─ V1RunHeader
│  ├─ StepRail
│  ├─ CreateStep
│  ├─ ScenarioTableEditor
│  ├─ ValidationStep
│  ├─ SignpostStep
│  └─ ConfirmationStep
├─ ComparisonWorkspace
│  ├─ MultiEventSelector
│  ├─ ComparisonSetup
│  ├─ ManifestSummary
│  ├─ VersionRunBoard
│  ├─ OverviewComparison
│  ├─ QualityJudgePanel
│  ├─ DimensionComparison
│  ├─ ScenarioComparison
│  └─ DiagnosticsComparison
└─ EvidenceDrawer
```

권장 module:

```text
backoffice/frontend/src/
  api/
    agentClient.ts
    v1Pipeline.ts
    multiEventComparison.ts
    comparisonQualityJudge.ts
  domain/
    apiTypes.ts
    judgments.ts
    deterministicChecks.ts
    comparisonPresentation.ts
    exportBundle.ts
  features/
    runtime/
    event-selector/
    v1-pipeline/
    version-comparison/
    evidence/
  App.tsx
```

## 11. 시각 스타일

### 11.1 Color

```css
:root {
  --color-brand: #2f55d4;
  --color-brand-hover: #2446b8;
  --color-brand-soft: #eaf2ff;

  --color-text: #111827;
  --color-text-secondary: #4b5563;
  --color-text-muted: #7b8794;
  --color-border: #dde3ea;
  --color-divider: #e7ebf0;
  --color-surface: #ffffff;
  --color-surface-soft: #f7f9fb;

  --color-success: #2f9e44;
  --color-warning: #f97316;
  --color-warning-bg: #fff7ed;
  --color-danger: #d64545;
  --color-danger-bg: #fff1f1;
  --color-unknown: #a16207;
}
```

### 11.2 Typography

```css
font-family: Inter, Pretendard, "Noto Sans KR", system-ui, sans-serif;
```

- page title: 28~32px, 700
- section title: 20~24px, 700
- card title: 16~18px, 700
- body: 14~16px
- table/meta: 13~14px
- code/JSON: monospace, 12~13px

### 11.3 Layout

- desktop page padding: 40~48px
- tablet: 24px
- mobile: 16px
- standard gap: 16px
- section gap: 32~40px
- radius: 8px
- input/button height: 40~44px
- version card min width: 300px
- Evidence Drawer width: 420~560px

중첩 card를 과도하게 사용하지 않는다. 실행 상태 card, Event card, Scenario card처럼 독립 객체에만 surface/border를 사용한다.

### 11.4 Status

- success: green + check + `성공`
- warning: orange + warning icon + `경고`
- error: red + error icon + `실패`
- unknown: amber/brown + question icon + `결과 불명`
- running: blue + spinner + `실행 중`

색상만으로 상태를 표현하지 않는다.

## 12. Loading, Empty, Error

Loading:

- Event list는 skeleton
- API 실행은 기존 결과 위에 작은 progress indicator
- 전체 화면을 blank 처리하지 않는다.

Empty:

- Event 미선택: 선택 방법 안내
- v1 미실행: `Event를 선택하고 Create를 실행하세요.`
- comparison 미실행: `Event 2~5건을 선택하세요.`
- 결과 없음: version별 원인 표시

Error:

- 해당 step/version 안에 inline callout
- Evidence Drawer로 이동하는 `원본 보기`
- 다음 안전한 행동 안내
- 입력과 이전 성공 결과 유지

Unknown:

- `서버에서 작업이 완료되었을 수 있습니다. 동일 요청을 자동 재시도하지 않습니다.`
- 새 comparisonRunId로 새 실행하거나 DB 증적을 확인하도록 안내

## 13. 반응형

### Desktop: 1200px 이상

- Runtime Settings horizontal
- v1 step rail + content 2-column 가능
- version card 3개 가로 배치
- Scenario comparison 3-column
- Evidence Drawer side panel

### Tablet: 768~1199px

- Runtime Settings 2-column
- version card horizontal scroll
- wide table horizontal scroll
- Evidence Drawer overlay

### Mobile: 768px 미만

- Runtime Settings stacked drawer
- workspace tab은 sticky
- v1 step rail은 horizontal step chips
- version 결과는 version switcher
- table은 horizontal scroll 또는 key/value card
- Evidence Drawer full-screen
- primary action은 full-width

## 14. 접근성

- 모든 icon button에 accessible name을 제공한다.
- tab, step, dialog, drawer는 keyboard로 조작 가능해야 한다.
- focus ring을 항상 표시한다.
- 상태는 icon, text, color를 함께 사용한다.
- loading 상태는 `aria-busy`와 live region으로 알린다.
- 오류는 field와 `aria-describedby`로 연결한다.
- 가로 스크롤 가능성을 시각적으로 표시하고 keyboard scroll을 지원한다.
- JSON viewer는 screen reader용 raw text 보기와 복사 기능을 제공한다.
- target size는 최소 36px, 권장 40px 이상이다.
- WCAG AA contrast를 목표로 한다.

## 15. 보안과 배포

- 정적 build만 배포한다.
- frontend는 Agent API를 직접 호출한다.
- `/backoffice/api/...` 경로를 사용하지 않는다.
- Agent가 Backoffice origin을 CORS allowlist에 포함해야 한다.
- HTTPS frontend에서 HTTP Agent를 호출하지 않는다.
- build-time 환경 변수에 token을 넣지 않는다.
- request log와 export에서 Authorization, cookie, token 필드를 제거한다.
- 인증이 필요한 경우 session memory에서만 header를 구성한다.

## 16. 구현 완료 기준

- v1과 comparison workspace가 독립 상태로 동작한다.
- callback, SSE, OAuth mock에 의존하는 UI나 client 코드가 없다.
- v1은 네 단계 sync workflow와 최신 detail 조회를 지원한다.
- v2/v3 barrier 후 v4 실행 순서를 코드로 보장한다.
- 동일 version의 create POST가 자동 재시도되지 않는다.
- timeout/cancel은 unknown으로 표현한다.
- 모든 API call을 Evidence Drawer에서 확인할 수 있다.
- 모든 version의 pressure가 `Global LNG pressure`로 일관되며 v4 `relatedMarkets`는 보조정보로만 표시된다.
- 비교 화면은 사용자용 Dimension/Value label과 실제 생성 근거를 제공하고 Raw 원본을 별도 보존한다.
- 결정적 검사 M-01~M-08과 optional mixed 규칙이 동작한다.
- 성공 version 2개 이상에서 사용자가 의미 품질 평가를 실행하고 우수 version과 근거를 확인할 수 있다.
- mixed가 없는 version은 N/A로 표시되고 평균에서 제외된다.
- 품질 평가 결과를 포함한 JSON export가 동작한다.
- secret이 storage와 export에 남지 않는다.
