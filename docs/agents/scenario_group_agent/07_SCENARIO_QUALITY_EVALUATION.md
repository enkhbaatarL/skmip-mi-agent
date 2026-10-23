# 시나리오 집합 품질 평가

## 범위와 저장 구조

시나리오 집합을 J-01/02/03/04/05/06/11로 평가한다. Event는 근거로 사용하고 Signpost는 채점하지 않는다.
모든 기준을 그룹 전체에 한 번씩 적용하며, 각 위반의 `scenarioIds`로 영향을 받는 시나리오를 연결한다.
운영 코드의 prompt/schema를 사용하며 `tests/manual/quality_eval`의 offline Judge를 호출하지 않는다.

- `tmm_mi_scenario_group_operation_m`: `quality_evaluation` 유형, 실행 상태·heartbeat·오류·시각.
- `tmm_mi_scenario_quality_eval_m`: operation_id PK/FK, request UUID, 고정 입력/hash, 기준 버전, 점수·문제·모델 사용량.
- operation과 평가 입력 접수, 평가 결과와 operation 완료는 각각 같은 transaction으로 저장한다.
- 종합 판정은 확정된 항목 FAIL → FAIL, 외부 사실 확인 필요 → NEEDS_FACT, 평균 3 미만 → FAIL,
  평균 4 미만 또는 WARN 항목 존재 → WARN, 나머지 PASS다. 평균은 7개 기준의 산술 평균이다.
- NEEDS_FACT/품질 FAIL도 평가 실행이 정상 종료되면 operation은 succeeded다.

DB 스키마 정본은 `skmip-mi-agent-mgmt`이며 본 기능은 이미 적용된 DDL에 맞춘다.
Agent ORM은 `apps/persistence/scenario_quality_evaluation/models.py`에 등록한다.

## API

```http
POST /scenario-groups/103/quality-evaluations
Content-Type: application/json

{
  "userId": 10603,
  "requestId": "4e14fef7-3582-46cc-bf93-539e63deae4b"
}
```

그룹 소유자와 생성 완료 상태를 확인한다. requestId는 전역 UUID이고 같은 요청의 재전송은 기존 operation을 반환한다.
다른 그룹에 이미 사용한 UUID는 재사용할 수 없다. 새 평가에는 새 UUID를 사용한다.
생성 중이거나 queued/running 그룹 작업이 있으면 409다. 기존 API의 userId 전달·조회 접근 관례를 따른다.

POST는 HTTP 202, `data.operationId`와 `data.status`를 반환한다.

```http
GET /scenario-groups/103/quality-evaluations/{operationId}
```

GET은 operation과 평가 상세를 조합한 `data`를 반환한다.
주요 필드는 `status`, `lastError`, `inputSnapshot`, `inputHash`, `promptVersion`, `result`, `verdict`,
`averageScore`, `llmMetadata`다. 다른 그룹의 operation, 삭제된 그룹, 평가가 아닌 operation은 404다.
`result.items[].violations[].evidencePath`는 inputSnapshot 기준 JSON pointer다.
그룹·시나리오 필드는 persistence snake_case, Event payload는 camelCase다.

## 자동 평가와 실행 수명

canonical v4 SSE 생성의 completed 저장 transaction에서 평가 operation과 입력을 접수한다.
`run_v4_create_operation()`이 완료 이벤트를 기록한 후 기존 TaskRunner에 평가를 제출한다.
생성 시나리오의 실제 DB ID와 생성에 연결된 Event snapshot을 입력에 고정한다.
snapshot 없는 구형 그룹의 수동 평가는 평가 시점 Event를 고정하고 source에 명시한다.

v4 `complete_validation()`에서 변경 내용이 적용되고 `mode=changed`, `canProceed=true`이면 같은 transaction에서
평가를 접수한다. Validation flow가 완료 후 제출한다. unchanged/BLOCK에는 새 평가를 만들지 않는다.
자동 requestId는 원본 operation ID에서 UUID5로 생성하며 입력의 sourceOperationId에 원본 작업을 기록한다.
inputHash에는 sourceOperationId·작업 상태·감사 시각을 포함하지 않는다.

평가 operation도 최신/활성 작업 조회에 포함한다. 평가 중 Validation·Signpost·Confirmation 등 기존 활성 작업
검사를 사용하는 편집은 409로 차단한다. 최신 평가 operation에는 기존 Presentation snapshot을 이어 주고,
평가 대기 상태 때문에 완료된 Event 상호작용 내용을 pending으로 바꾸지 않는다.

실행은 기존 TaskRunner/heartbeat/recovery monitor를 사용한다. 일반 예외는 failed, 취소는 interrupted다.
프로세스 강제 종료 시 monitor가 오래된 queued/running 작업을 interrupted로 정리한다. 자동 재개는 없다.
terminal 상태 이후 도착한 모델 결과는 저장하지 않는다. 평가 중에는 DB transaction을 유지하지 않는다.
외부 검색, 자동 수정, Signpost 평가, 평가 완료 callback, 별도 worker queue는 포함하지 않는다.

## 검증

```powershell
$env:METADATA_DB_PORT = '3306'
$env:DEBUG = 'false'
.venv/Scripts/python.exe -X utf8 -m pytest tests/automated/test_scenario_quality_evaluation.py -q
```

실제 DB·LLM으로 생성/수정 및 수동 POST/GET을 확인하고 데이터를 보존하려면:

```powershell
.venv/Scripts/python.exe -X utf8 tests/manual/test_scenario_quality_evaluation_live.py `
  --event-ids 69 68 67 --user-id 10603 `
  --output-dir local/output/scenario_quality_live_test/run_name
```

envs/.env를 프로세스에 로드한다. 신규 그룹과 평가 결과를 삭제하지 않으며 외부 프런트엔드 callback만 생략한다.
기존 그룹을 삭제하지 않으므로 Event 조합은 테스트 대상 환경의 점유 상태에 맞게 선택한다.
출력은 summary.json, 생성 SSE, 요청/응답, 평가 JSON, 최종 그룹 snapshot이다.
