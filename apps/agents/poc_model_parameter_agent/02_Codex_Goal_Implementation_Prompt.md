# Prompt 2 — Cursor Codex Goal mode
## 승인된 계획 기반 End-to-End 구현·테스트·검증

이제 **Goal mode**로 전환했습니다. 직전 Plan mode에서 작성하고 사용자가 승인한 계획과 최초 요구사항을 권위 있는 기준으로 사용하여, LNG Scenario-to-Parameter Learning Agent를 실제로 구현하십시오.

## 0. Goal

Scaffold나 일부 API 구현에서 멈추지 말고 다음 Goal을 모두 만족할 때까지 구현, 테스트, 실패 분석, 수정, 재실행을 반복하십시오.

```text
React Web + FastAPI API + MySQL + 별도 Learning Worker가 Docker Compose로 실제 기동되고,
예시 Scenario 입력 → 검증 → Plan → Clarification → Parameter 생성 → Plot/Rationale 검토
→ Interim/Final Feedback 저장 → Final Feedback 기반 Child Run Revision 즉시 생성
→ Learning Batch와 Candidate 생성 → Diff/Evaluation → 수동 승인/거절
→ 새 Memory/Skill Version 활성화 → 다음 Run Snapshot 반영
흐름이 브라우저 E2E와 MySQL Integration Test로 검증된 상태
```

## 1. 자율 실행 범위와 중단 기준

다음 작업은 추가 확인 없이 수행하십시오.

- 승인된 범위의 파일 생성·수정
- 필요한 비파괴적 Shell 명령
- 승인된 Dependency 설치
- Alembic Migration 작성·실행
- Local Docker Image Build와 Container 기동·재기동
- Test DB 초기화와 Idempotent Seed
- Unit, Integration, E2E, Smoke Test 실행
- Test 실패와 Runtime 오류 수정
- Lint, Type Check, Build 수행
- Local Screenshot 생성

다음 상황에서는 임의로 진행하지 말고 한 번만 명확히 보고하여 확인을 요청하십시오.

- 승인된 Architecture를 실질적으로 뒤집어야 하는 경우
- 기존 사용자 코드나 DB 데이터를 파괴적으로 삭제해야 하는 경우
- Cloud Resource, 외부 유료 Service, 실제 Credential이 필요한 경우
- MySQL 대신 다른 DB로 변경하려는 경우
- React/Vite/FastAPI 기본 스택을 변경하려는 경우
- Celery, Redis, Kafka, Temporal 등 주요 Infrastructure를 새로 도입하려는 경우
- 요구 범위를 크게 넓히는 경우

단순 구현 세부사항, Naming, 작은 Refactor, Test 보강 때문에 진행을 멈추지 마십시오.

## 2. 구현 우선순위

승인된 계획의 File-by-file 순서를 존중하되, 아래 Dependency 순서를 유지하십시오.

```text
Repository-safe scaffold
→ Configuration / Docker / MySQL
→ SQLAlchemy Model / Alembic / Seed
→ Domain Schema와 결정적 Main Pipeline
→ API와 Transaction Boundary
→ Feedback / Revision Service
→ Learning Worker와 Candidate Approval
→ React Shell과 4개 화면
→ Shared Result Components와 Chart
→ Frontend Tests
→ Backend Unit/Integration Tests
→ Browser E2E와 Screenshot
→ README와 최종 검증
```

기존 저장소가 제공하는 구조와 Convention을 우선 재사용하십시오. 기존 사용자 코드를 Reset, Force Checkout, Clean, 덮어쓰기하지 마십시오.

## 3. 절대 누락하면 안 되는 Product Flow

### Parameter 생성

- Metadata와 Scenario JSON 입력
- Example 1·2·3 Load
- JSON Syntax/Schema Validation
- 9단계 Plan Preview
- Required/Optional Clarification
- Required 미응답 시 실행 잠금
- MySQL에 Run·Artifact·Proposal·Interim Feedback 저장
- Scenario Tab, Pressure Gauge, Dimension Table, Validation
- Clickable Parameter Proposal Table
- Baseline/Proposed Plot + Delta Bar + Tooltip
- Evidence & Rationale Trace + Formula + 전체 Series
- Revision Chain과 Evaluation Invariants
- Final Feedback Scope: Parameter / Scenario / Run
- Final Feedback 제출 즉시 Child Revision 생성

### Run History

- Revision, Parent, Feedback, Adjustment, Asset Snapshot을 포함한 목록
- Detail에서 입력, Plan, Artifact, Feedback, 결과 재조회
- 과거 Revision 불변
- `이 리비전에서 이어서 작업`

### 피드백 원장

- Interim/Final 통합 목록
- Context Mapping
- 적용 Adjustment
- Result Run
- Learning Batch
- 실제 저장 Record JSON Accordion

### Learning Pipeline

- 자동 Worker Polling
- Local 수동 `process-pending`
- Batch / Candidate / Asset Version 3개 Tab
- Candidate Source 원문, 분류 근거, Risk, Diff, Evaluation
- 승인·거절
- Base Version Conflict 409와 Transaction Rollback
- 승인 후 새 Active Version

## 4. Frontend 품질 기준

Prototype과 동일한 정보 구조를 가진 Compact Enterprise Dashboard로 완성하십시오.

- 216px Dark Navy Left Rail
- 4개 번호 Navigation
- Sticky Top Bar와 상태 Chip
- Light Blue-gray Canvas, White Surface, Muted Teal Accent
- Border 중심, 2~3px Radius, 13~14px 밀도
- 과도한 Rounded/Pill/Gradient 금지
- Desktop 2열과 Responsive 1열 전환
- Monospace Metadata와 Formula
- Status별 Green/Amber/Red, Demand Red, Supply Blue
- Loading, Empty, Disabled, Error, Success, Toast 상태
- Focus-visible, Label, Keyboard, Reduced Motion
- Table Horizontal Scroll

UI는 API에서 받은 실제 데이터를 렌더링해야 합니다. Prototype처럼 전역 JavaScript Object나 Browser Memory를 DB 대체물로 사용하지 마십시오. 새로고침 후에도 Run과 Feedback이 유지되어야 합니다.

## 5. Backend 및 데이터 무결성 기준

### 통합 Feedback

`feedback` Table 하나에 `interim|final`을 저장하십시오. Final은 Run Revision당 한 번만 허용하고 DB 수준 제약과 Service 수준 검사를 모두 둡니다.

### Final Feedback Revision

Final Feedback API는 원문 저장 후 반드시 Child Run을 생성하고 `result_run_id`를 연결합니다. 해석 규칙이 없어도 값 유지 Revision을 생성합니다.

### Worker

Worker와 `POST /api/learning/process-pending`은 동일한 Application Service를 사용합니다. `FOR UPDATE SKIP LOCKED`와 Idempotency Guard로 중복 Batch/Candidate를 막습니다.

### Approval

Candidate 승인 Transaction은 Base Version을 검증하고, Conflict 시 409와 완전 Rollback을 보장합니다. 거절은 Asset을 변경하지 않습니다.

### Asset Snapshot

각 Run은 사용한 Memory, Skill, Flow Profile, Catalog, Rule Version을 Snapshot으로 저장합니다. 승인 후 생성되는 다음 Run만 새 Version을 사용합니다.

### Deterministic Mock

외부 API Key 없이 Example의 계산, Feedback Adjustment, Learning Classification이 재현되어야 합니다. LLM Adapter 부재로 핵심 Flow가 실패하면 안 됩니다.

## 6. Test 완료 기준

테스트를 작성만 하지 말고 실제 실행하십시오. 실패를 고친 뒤 재실행하여 통과 결과를 확보하십시오.

### 필수 Command 범주

저장소에 맞는 실제 명령을 사용하되 최소 다음을 모두 수행합니다.

```text
Frontend install / typecheck / test / build
Backend unit test
MySQL integration test
Alembic upgrade on clean DB
Seed twice to prove idempotency
Docker compose build and up
API health check
Worker processing check
Browser E2E
Screenshot generation
```

### 필수 E2E Acceptance

1. 예시 1 Load → 검증 → Plan → 실행 → 결과 표시
2. Scenario와 Parameter 선택에 따라 Plot·Trace 전환
3. 예시 3의 Clarification 잠금과 응답 후 실행
4. Interim Feedback이 원장에 저장되고 적용 Badge 표시
5. Final Feedback 제출 → Child Revision과 Revision Chain
6. 동일 Revision Final Feedback 재제출 차단
7. 새로고침 후 데이터 유지
8. Run History Detail과 Artifact 조회
9. Feedback Ledger Raw JSON 확인
10. `process-pending` 또는 Worker로 Candidate 생성
11. Candidate Diff와 Evaluation 표시
12. Candidate 승인 → 새 Asset Version
13. 다음 Run에서 새 Version Snapshot
14. Candidate 거절 시 Asset 무변경
15. Version Conflict 409와 Rollback
16. `process-pending` 재호출 시 중복 Candidate 없음

### Screenshot

최종적으로 다음 화면의 Screenshot을 1440px 기준으로 저장하십시오.

```text
parameter-input-plan
parameter-result
run-history
feedback-ledger
learning-batches
learning-candidates
candidate-detail
asset-versions
```

Screenshot은 최종 보고에서 실제 파일 경로를 알려주십시오.

## 7. 완료 판단 금지 사례

다음 상태에서 완료했다고 말하지 마십시오.

- Frontend가 Static Mock Data만 사용
- MySQL 대신 In-memory 또는 SQLite만 사용
- Worker가 실제 DB를 처리하지 않음
- Final Feedback이 새 Revision을 만들지 않음
- Candidate가 승인 전 자동 적용됨
- Docker Compose가 기동하지 않음
- Test를 작성했지만 실행하지 않음
- jsdom Test만 있고 Browser E2E가 없음
- Plot·Formula·Table이 서로 다른 값을 표시
- 새로고침하면 데이터가 사라짐
- Example 3 Clarification이 실행을 잠그지 않음
- Version Conflict가 일부 변경을 남김
- README 명령이 실제로 동작하지 않음

## 8. 문제 해결 방식

Test나 Docker가 실패하면 첫 실패에서 멈추지 마십시오.

```text
실패 Command와 Log 확인
→ 원인 분류
→ 최소 수정
→ 관련 Test 재실행
→ 전체 Regression 재실행
→ Docker/E2E 재검증
```

환경 제약으로 특정 검증을 수행할 수 없다면, 수행한 시도와 실제 Error를 기록하고 가능한 대체 검증을 수행하십시오. 실행하지 않은 항목을 성공으로 보고하지 마십시오.

## 9. 문서화

README 또는 별도 문서에 다음을 포함하십시오.

- Architecture 개요
- Local Prerequisite
- `.env` 설정
- Docker Compose 실행과 종료
- Migration과 Seed
- Native Web/API/Worker 실행
- Unit/Integration/E2E Test 명령
- Example Flow
- `AGENT_MODE=mock`와 Optional LLM Adapter
- Synthetic Baseline 주의
- `process-pending`의 목적과 금지 범위
- Feedback/Revision과 Learning Candidate 차이
- Version Conflict 동작

## 10. 최종 보고 형식

모든 작업이 끝난 뒤 다음 순서로만 보고하십시오.

```text
1. 구현 요약
2. 주요 Architecture와 선택 이유
3. 생성·수정 파일 요약
4. DB Migration과 Seed 결과
5. 실행한 Test/Build/Compose Command와 결과
6. E2E Acceptance 항목별 PASS/FAIL
7. Screenshot 경로
8. Local 실행 방법
9. 남은 제약 또는 미완료 항목
10. Git diff 요약
```

각 Test는 `실행 명령`, `종료 코드`, `핵심 결과`를 구체적으로 적으십시오. 실패하거나 실행하지 못한 항목은 숨기지 마십시오.

모든 필수 Acceptance가 통과한 경우 마지막 줄에 정확히 다음을 출력하십시오.

```text
GOAL_COMPLETE_LOCAL_E2E_VERIFIED
```

통과하지 못한 필수 항목이 하나라도 있으면 위 문장을 출력하지 말고, 대신 다음 형식으로 끝내십시오.

```text
GOAL_INCOMPLETE: <미완료 핵심 항목>
```
