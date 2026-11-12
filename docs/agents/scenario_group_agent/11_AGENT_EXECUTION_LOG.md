# Scenario Agent 고수준 실행 로그

## 범위

Event 추천·검증·현행화, canonical v4 시나리오 설계, 품질 평가·수정에 공통 로그를 제공한다.
실행 단계, 근거, 판단 요약, 실제 도구/LLM 호출, 소요 시간, 실패·취소·생략을 기록한다.
모델 내부 사고 원문, 프롬프트 전문, 인증 정보는 이 로그에 넣지 않는다. 근거 문장과 Event 수정 전후 내용은
업무 데이터이므로 기존 서비스 로그와 동일한 접근 제어/보관 정책을 적용한다.
로그를 꾸미기 위한 별도 LLM 호출은 없다. 계획 생성/비교 자체에만 추가 호출 2회가 필요하다.

## 어디서 확인하는가

| 기능 | 조회 위치 | 진행 중 확인 |
| --- | --- | --- |
| 전체 기능 | 서버 stdout의 `[AGENT_EXECUTION]` JSON | 즉시 |
| Event 추천·검증·현행화 | 기존 POST 응답의 추가 필드 `executionLog` | 응답 완료 후. 별도 SSE/조회 endpoint는 추가하지 않음 |
| 시나리오 설계 | 기존 operation 이벤트/SSE의 `payload.executionLog` | 기존 진행 이벤트 단위 |
| 품질 평가·자동 수정 | 기존 operation 이벤트/SSE의 `payload.executionLog` | 주요 단계 경계마다 저장 |
| 수정 계획·비교·선택 | 평가 상세의 `retrySummary.qualityRepair.planning` | 후보 생성 후, 비교 완료 후 |

프런트엔드 타임라인 컴포넌트는 이 저장소의 변경 범위에 포함되지 않는다. 기존 화면이 새 필드를 자동으로
렌더링하지는 않는다. 서버 터미널 또는 API 응답으로 확인할 수 있으며, UI는 아래 계약을 사용해 연결한다.
MLflow 설치·활성화나 새 DB 테이블/마이그레이션은 필요 없다.

## 공통 이벤트 계약

- `runId`: 실행 단위 ID. 설계/평가는 기존 operationId와 동일하다. Event POST는 요청마다 UUID를 생성한다.
- `parentRunId`: 같은 실행에서 이어진 하위 작업의 부모 ID. 독립 POST 요청 간에는 자동 연결하지 않는다.
- `sequence`: 실행 내 순서. 병렬 Event 작업도 하나의 요청 안에서 순서를 부여하고 `eventId`로 구분한다.
- `feature`: event_recommendation / event_verification / event_update / scenario_design / quality_evaluation.
- `phase`: workflow, retrieval, comparison, planning, plan_comparison, selection, self_correction,
  validation, application, evaluation, retry, outcome, call 등.
- `status`: started / completed / failed / interrupted / skipped / warning.
- `summary`: 실제 반환 결과 또는 서버가 확인한 실행 사실의 요약. 모델 내부 추론 원문이 아니다.
- `occurredAt`: UTC 시각. `elapsedMs`: 실행 시작 이후 경과 시간.
- `details`: eventId, groupId, operationId, verificationId, sourceUrls, 기준별 판정, 계획·비교 결과 등.
- 호출은 `phase=call`, `details.kind=tool|llm`, `callId`, `name`, `durationMs`로 연결한다.
  호출 완료는 도구가 응답했다는 뜻이며 업무 판정 통과를 뜻하지 않는다. 검색 응답의 미완료·근거 부족은
  별도 warning 판정으로 표시한다. 취소/예외 메시지는 원문 대신 상태·예외 종류만 기록한다.

operation 이벤트는 단계별 로그 묶음이므로 `runId + sequence`로 중복 제거해 타임라인을 구성한다.
품질 평가 완료 후 자동 수정 B가 생기면 A의 `reevaluationId`를 따라 B도 조회한다.
품질 로그 저장 실패는 서버 경고를 남기고 업무 처리를 계속한다. 이 경우 DB 타임라인 일부가 없을 수 있다.
Event 실패 응답의 HTTP 오류 계약은 유지되며 실패 로그는 서버에서 확인한다.

## 기능별 사실 표현

| 기능 | 기록하는 내용 |
| --- | --- |
| 추천 | 벡터 검색, 게시·미삭제 필터, 후보 ID, 관련성·중복 평가 시작, 최종 추천 근거·인용 |
| 검증 | Event별 웹 검색 호출, 검색 시점·URL, 6개 기준 비교, 원본 판정과 공개 판정, 근거 부족/오류 |
| 현행화 | verificationId의 저장 근거 재사용, 수정안 생성, 허용 필드·인용 확인, 재검증, 반영/생략 사유·전후 변경 |
| 설계 | 고정 실행 흐름, 노드 시작, 실제 LLM 호출, 단계 검증·재시도, 결과 저장 |
| 평가·수정 | 7개 기준 평가, 생성 계획 A/B, 비교·선택, 선택 범위 내 수정, 검증, 저장 후 재평가, 전후 변화 |

추천·검증·현행화·설계의 실행 순서는 `planningMode=fixed_workflow`다.
새 품질 수정 계획만 `planningMode=generated`이며 두 후보를 생성·비교한다.
후보별 수정안 실행/트리 탐색은 하지 않으므로 ToT, Deep Reasoning, Simulating plan으로 표시하지 않는다.
MCP 호출을 새로 추가하지 않는다. 설계 재시도는 `retry`이며 단순 통신 재시도를 Self-Correction으로 과장하지 않는다.

## 시연 순서

1. 서버 로그에서 `[AGENT_EXECUTION]`를 필터링하고 `runId`를 기준으로 확인한다.
2. Event 추천의 후보/선정 이유, 검증의 기준별 판정/검색 URL, 현행화의 실제 전후 변경을 보여준다.
3. 시나리오 설계의 영향 분석 → Dimension → 합성 → 검증 완료를 보여준다.
4. 최초 평가에 수정 가능한 WARN/FAIL이 있는 경우 A/B 계획과 비교 점수·이유, 선택 ID를 보여준다.
5. 수정 반영과 재평가 결과를 보여준다. PASS이면 수정이 생략되므로 계획을 생성한 것처럼 표시하지 않는다.
6. 점수 하락·새로운 위반·재평가 실패도 그대로 표시한다. 저장 후 재평가 방식이므로 자동 rollback하지 않는다.

Event POST 응답에 포함되는 로그는 별도로 DB에 영구 저장하지 않는다. 기존 Event 검증 결과·Snapshot 저장은 유지한다.
로그만으로 품질 개선이 입증되지는 않는다. 개선율은 실제 재평가 결과와 동일한 표본의 전후 비교로 산출한다.


## 콘솔 표시 형식과 원문 보존

2026-11-12부터 다섯 기능 모두 같은 콘솔 formatter를 사용한다.
구분선 → 시각/레벨/`[AGENT_EXECUTION]`/feature/phase/status → 코드 위치 → 전체 JSON 순서로 표시한다.
한글 설명, 영문 식별자, UUID, 출처 URL, 모든 details 필드와 배열 원소를 그대로 보존한다.
JSON은 `ensure_ascii=False, indent=2`로 표시하며 문자열/배열 길이 제한이나 생략 표시를 적용하지 않는다.
긴 문자열은 터미널의 자동 줄바꿈으로 보이며, JSON 문자열 내부의 개행은 `\n`으로 보존된다.
정보가 중복되던 별도 summary 출력은 콘솔에서 JSON 안으로 모으지만, Loguru의 원본 message/agent_execution
및 API/operation payload는 변경하지 않는다. 다른 sink는 기존 원문을 사용할 수 있다.

`START`, `END`, DEBUG, ERROR와 traceback을 필터링하지 않는다. Scenario 실행 안의 일반 로그는
시각/레벨, 코드 위치, 본문을 줄바꿈하여 구분한다. 외부 라이브러리가 stdout/stderr로 직접 출력하는 내용은
Loguru formatter의 대상이 아니며 그대로 남는다. 기존 로그 레벨·log_input/log_output 설정·비밀값 마스킹은 유지한다.

기존 connector의 serialize는 2,000자(일부 결과 1,000자) 제한과 개행 치환이 있었다.
`logged_run` 실행 및 그 하위 작업에서는 context-local `full_console_logs`로 이 제한/치환을 해제한다.
Scenario Agent의 `main.py`는 RequestLoggingMiddleware에 `full_payloads=True`를 전달하여 HTTP DEBUG 본문도
길이 제한 없이 표시한다. 다른 Agent의 기본 middleware/serializer 길이 정책은 변경하지 않는다.
이미 과거 로그에서 잘린 내용은 복원할 수 없다. 새 실행부터 전체 본문이 기록된다.

검증: `tests/automated/test_scenario_console_format.py`는 5개 기능 × 6개 상태의 JSON 왕복 동등성,
긴 문자열·150개 후보·중첩 값·미래 필드·한글·이스케이프 문자, 일반 START/END·오류 traceback,
병렬 작업 간 분리, 취소/오류 후 context 복구, connector 마스킹과 HTTP 요청 본문 보존을 검사한다.
콘솔 scrollback 보관 한도는 터미널 설정에 따르므로 장시간 실행의 전체 보관이 필요하면 별도로 파일에 저장한다.
