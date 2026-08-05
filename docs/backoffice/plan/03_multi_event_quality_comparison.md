# 03. Multi-Event Scenario Quality Comparison Plan

## 1. 목표

동일한 Event 2~5건으로 v2, v3, v4 Scenario Group을 생성한 뒤 domain reviewer가 다음 질문에 답할 수 있는 Backoffice 비교 화면을 구현한다.

- 각 version은 어떤 전략으로 Scenario Group을 구성했는가?
- 어떤 Dimension과 Value를 선택했고 그 근거는 무엇인가?
- 실제 Scenario는 어떻게 구성됐고 글로벌 LNG 가격 방향을 왜 그렇게 판단했는가?
- Event 사실과 Scenario 가정이 일관되는가?
- 성공한 version 가운데 어떤 version이 가장 우수하며 그 근거는 무엇인가?

`comparison_report.md`의 정보 구조를 사용자용 화면의 기준으로 삼되, 원본 JSON은 기본 화면과 분리해 감사·디버깅 증적으로 그대로 보존한다.

## 2. 핵심 결정

- v2/v3/v4 Scenario lifecycle은 create sync API까지만 실행한다. validation, signpost, confirmation은 실행하지 않으며 품질 평가는 별도 읽기 전용 API다.
- v2와 v3를 병렬 실행하고 두 요청이 terminal 상태가 된 뒤 v4를 실행한다.
- create POST는 자동 재시도하지 않는다.
- 의미 품질 평가는 모든 create가 끝난 뒤 사용자가 `품질 평가 실행` 버튼을 눌렀을 때만 실행한다.
- 성공 version이 2개 이상이면 성공한 version끼리 평가한다. 2개 미만이면 `판정 불가`다.
- 브라우저는 외부 LLM API를 직접 호출하지 않는다. Scenario Group Agent의 동기 평가 API가 기존 LLM connector를 사용한다.
- 평가 결과는 DB에 추가 저장하지 않고 frontend run state, sessionStorage, export bundle에 보존한다.
- `mixed`는 optional이다. mixed가 없다는 이유로 감점하지 않는다.
- mixed가 없으면 `mixed_quality`는 `N/A`, `score=null`이며 평균 계산에서 제외한다.
- mixed가 있으면 상승·하락 기여 Value가 실제 조합에 함께 존재하고, 상쇄 관계를 설명하는 근거가 있어야 한다.

## 3. 사용자 경험

### 3.1 비교 결과 정보 구조

```text
Overview
  - 실행 조건과 version 상태
  - Scenario Group 요약
  - 결정적 검사
  - 품질 평가 실행/결과

Dimensions
  - 사용자용 Dimension label과 설명
  - Event lineage
  - Dimension 선택 근거
  - Value label, 가격 기여, Value 근거

Scenarios
  - pressure band 기준 v2/v3/v4 정렬
  - title, narrative, baseline, role, probability
  - 사용자용 Dimension/Value 조합
  - 조합·가격 판단 근거
  - Scenario별 품질 판정

Diagnostics
  - 제외 Scenario/Dimension과 이유
  - Event shock/interaction
  - coverage 및 unsupported lever

Raw
  - create/judge request와 response 원본
  - HTTP 상태, 시간, token usage
```

### 3.2 사용자용 표현 규칙

- 기본 비교 화면에는 내부 `dimensionId`와 `valueId` 대신 `dimensionDefinitions[].label`과 `values[].label`을 표시한다.
- 같은 Dimension label이 중복되면 `Event <lineage>`를 붙여 구분한다.
- v2/v3/v4 응답 필드 차이는 presentation adapter에서 처리하고 원본 응답은 수정하지 않는다.
- Dimension 근거는 version별 실제 필드인 `selectionRationale`, `rationale`, source/event grounding을 사용한다.
- Value 근거는 `sourceAssignments[].rationale`, `assumptionRationale`, `globalPressureContribution` 등 실제 응답 필드만 사용한다.
- 근거가 없으면 추정하지 않고 `제공된 근거 없음`으로 표시한다.
- v4 `relatedMarkets`는 Scenario 관련성 보조정보이며 별도 pressure나 방향 tag로 해석하지 않는다.

## 4. Agent 품질 평가 API

신규 동기 endpoint:

```http
POST /scenario-group-comparisons/judge/sync
```

요청 예시:

```json
{
  "comparisonRunId": "multi-event-unique-id",
  "userId": 10001,
  "versions": [
    { "apiVersion": "v2", "scenarioGroupId": 345 },
    { "apiVersion": "v3", "scenarioGroupId": 346 },
    { "apiVersion": "v4", "scenarioGroupId": 347 }
  ]
}
```

서버 검증:

- version은 중복 없는 v2/v3/v4 2~3개다.
- 모든 Scenario Group이 존재하고 요청 userId가 소유한다.
- 요청 version, 저장된 `apiVersion`, `comparisonRunId`가 일치한다.
- 모든 그룹의 Event ID와 순서가 동일하다.
- 평가 대상 그룹에 Scenario, Dimension, diagnostics가 존재한다.

응답에는 다음을 포함한다.

- version별 네 평가 기준의 score/verdict/rationale/evidence
- version별 Scenario 판단
- strengths, weaknesses
- 적용 가능한 기준의 평균 점수
- 최고 평균 version 전체를 담은 `bestVersions`
- 종합 결론과 LLM token usage

평가 기준:

1. `event_consistency`
2. `lng_dimension_quality`
3. `floor_ceiling_quality`
4. `mixed_quality`

`mixed_quality` 규칙:

- mixed 없음: `verdict=N/A`, `score=null`, 평균 제외
- mixed 있음: 비극단 pressure band, 상승·하락 기여의 실제 공존, 상쇄 rationale을 평가
- mixed label만 있고 조합이나 근거가 불충분하면 WARN 또는 FAIL

서버는 LLM이 반환한 기준·version·Scenario 집합을 검증하고 평균과 `bestVersions`를 결정적으로 계산한다. 평가는 선택 Event와 저장된 API 증적만 사용하며 외부 사실을 추가하지 않는다.

## 5. Frontend 구현

### 5.1 타입과 presentation adapter

- v2, v3, v4 Dimension/diagnostics 타입을 실제 응답 shape에 맞는 discriminated union으로 정의한다.
- 공통 view model에는 group metadata, Dimension, Value, Scenario, 근거, lineage를 사용자용 값으로 정규화한다.
- cell value ID를 해당 Dimension의 Value label로 변환한다.
- API response와 raw text는 call record에 원형 그대로 유지한다.

### 5.2 품질 평가 상태

comparison run에 다음 상태를 추가한다.

```ts
interface QualityJudgeState {
  status: "idle" | "ready" | "running" | "success" | "error" | "unknown";
  request?: ComparisonJudgeRequest;
  response?: ComparisonJudgeResponse;
  call?: ApiCallRecord;
  error?: string;
}
```

- create 성공 version이 2개 이상이면 `ready`다.
- 사용자가 버튼을 누르면 평가 endpoint를 한 번 호출한다.
- 평가 실패·timeout은 create 결과를 변경하지 않는다.
- judge는 DB row를 생성하지 않는 읽기 전용 평가이므로 실패 후 명시적 재평가를 허용한다.
- 새로고침 중 `running`이었던 judge는 `unknown`으로 복구하고 재평가 action을 제공한다.

### 5.3 품질 평가 화면

- 미실행 상태에는 평가 기준, 예상 추가 시간·token 사용, `품질 평가 실행` 버튼을 표시한다.
- 성공 후에는 최우수 version, 공동 우수 여부, 평균 점수, 종합 결론을 먼저 표시한다.
- 기준별 score/PASS/WARN/FAIL/N/A와 근거를 version별로 비교한다.
- Scenario card에 해당 Scenario 판단을 연결한다.
- 성공하지 못한 version은 평가에서 제외하고 API 실패 사유를 유지한다.

## 6. 결정적 검사

화면 검사를 `comparison_report.md`의 M-01~M-08 의미와 맞춘다.

| ID | 검사 |
| --- | --- |
| M-01 | Scenario 3~5개 |
| M-02 | baseline 정확히 1개 |
| M-03 | Scenario 조합과 pressure band가 존재하고 중복되지 않음 |
| M-04 | floor/ceiling 각각 1개, role과 극단 band 정합성, optional mixed 정합성 |
| M-05 | version별 Dimension 3~6개 |
| M-06 | 전체 입력 Event lineage coverage |
| M-07 | 모든 Scenario의 global pressure rationale 존재 |
| M-08 | 생성 또는 명시적 제외 사유로 target pressure band 전체 설명 |

M-04에서 mixed 미생성은 PASS다. mixed가 있으면 상승·하락 contribution이 함께 선택됐고 비극단 band이며 상쇄 rationale이 있는지 검사한다. 의미 판단이 필요한 부분은 결정적 검사에서 추측하지 않고 WARN으로 남겨 LLM 평가 근거와 구분한다.

## 7. 저장과 Raw 증적

- 기본 화면은 사용자용 label과 근거를 표시한다.
- Raw 탭과 Evidence Drawer에는 create/judge request, parsed response, raw response text를 secret redaction 외 의미 변환 없이 제공한다.
- sessionStorage와 export에는 judge 상태·응답·token usage를 포함한다.
- 인증 header, password, token, API key 등 secret은 저장·export 전에 제거한다.
- 사용자용 변환 실패가 있어도 Raw 응답은 유실하거나 덮어쓰지 않는다.

## 8. 구현 순서

1. Agent judge API schema, evidence builder, structured-output 평가와 결과 검증을 구현한다.
2. frontend API client와 judge run state·저장·export를 구현한다.
3. 실제 version별 응답 타입과 presentation adapter를 구현한다.
4. Group/Dimension/Scenario 화면을 label·근거 중심으로 개편한다.
5. 품질 평가 summary와 Scenario별 판단 UI를 연결한다.
6. 결정적 검사를 M-01~M-08 및 optional mixed 규칙으로 정렬한다.
7. architecture/API 문서와 자동 테스트를 갱신한다.

## 9. 테스트와 완료 조건

- v2/v3/v4 실제 응답 변형에서 내부 ID가 사용자용 label로 변환된다.
- Scenario Group 제목·요약·설명과 Dimension/Value 선택 근거를 볼 수 있다.
- mixed가 없으면 결정적 검사에서 실패하지 않고 LLM 평가는 N/A로 평균에서 제외한다.
- mixed가 있으면 실제 상·하방 조합과 상쇄 근거를 검증한다.
- 성공 version 2개/3개 평가, 공동 우수, 성공 1개 판정 불가가 동작한다.
- judge 오류 후 create 결과가 유지되고 평가만 재실행할 수 있다.
- 사용자용 화면과 Raw 증적이 분리되고 export에는 둘의 근거가 모두 보존된다.
- Backend pytest/Ruff와 frontend Vitest/typecheck/build가 통과한다.
