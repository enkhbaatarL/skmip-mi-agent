# 시나리오 집합 품질 평가

## 범위와 저장 구조

시나리오 집합을 J-01/02/03/04/05/06/11로 평가한다. Event는 근거로 사용하고 Signpost는 채점하지 않는다.
모든 기준을 그룹 전체에 한 번씩 적용하며, 각 위반의 `scenarioIds`로 영향을 받는 시나리오를 연결한다.
운영 코드의 prompt/schema를 사용하며 `tests/manual/quality_eval`의 offline Judge를 호출하지 않는다.

- `tmm_mi_scenario_group_operation_m`: `quality_evaluation` 유형, 실행 상태·heartbeat·오류·시각.
- `tmm_mi_scenario_quality_eval_m`: operation_id PK/FK, request UUID, 고정 입력/hash, 기준 버전, 점수·문제·모델 사용량.
- operation과 평가 입력 접수, 평가 결과와 operation 완료는 각각 같은 transaction으로 저장한다.
- 신규 종합 판정은 항목 FAIL → FAIL, 평균 3 미만 → FAIL,
  평균 4 미만 또는 WARN 항목 존재 → WARN, 나머지 PASS다. 평균은 7개 기준의 산술 평균이다.
- 품질 FAIL도 평가 실행이 정상 종료되면 operation은 succeeded다. 과거 NEEDS_FACT 이력은 그대로 조회한다.

`scenario-set-v3`부터 평가 프롬프트는 `global_pressure_band`를 Base 대비 상대 위치로 해석한다.
Base는 최고 확률 시나리오(동률이면 앞선 display_order)이며, 실제 시장 방향이 상승·하락이어도 자신의
band는 balanced다. 선택값의 pressureContribution 합계와 Base 합계의 차이 및 band_unique의 strong 완화
규칙을 고려한다. narrative·global_pressure_rationale의 실제 시장 방향과 band 명칭이 다르다는 이유만으로
J-05/J-11 등의 위반을 만들지 않는다. 동일 비교 기준에서의 실제 모순은 계속 평가한다.
기존 평가 이력은 변경하지 않으며 새 평가부터 이 기준과 prompt_version을 저장한다.

`scenario-set-v4`는 최초 평가와 재평가 모두에서 관측·통보 사실, 전망, 미래 가정을 구분하도록 명시한다.
통보된 적용 기간의 말일을 실제 정상화 확정일로 해석하지 않으며, 명시적인 회복 가정 자체는 오류로 보지 않는다.
WARN/FAIL은 구체적인 근거·논리 문제에 부여하고 문체 선호나 선택적인 상세 설명만으로 부여하지 않는다.
점수는 기준의 충족 정도, verdict는 남은 문제의 조치 필요성을 나타내므로 높은 평균도 WARN일 수 있다.

UI 권장 표시 조건은 실행 `status=succeeded`, 종합 `verdict=PASS`, `averageScore>=4.0`을 모두 만족할 때
초록색 **수정 불필요**다. 의미는 '현재 평가 기준에서 추가 수정이 필요한 문제가 발견되지 않음'이다.
점수만으로 수정 불필요를 결정하지 않으며 WARN/FAIL/NEEDS_FACT와 미완료·실패한 실행은 초록색 대상이 아니다.
이는 표시 권고이며 UI 코드나 종합 판정 계산 규칙을 변경한 것은 아니다.

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

그룹 소유자와 Validation 통과 상태를 확인한다. requestId는 전역 UUID이고 같은 요청의 재전송은 기존 operation을 반환한다.
다른 그룹에 이미 사용한 UUID는 재사용할 수 없다. 새 평가에는 새 UUID를 사용한다.
Validation 통과 전이거나 queued/running 그룹 작업이 있으면 409다. 기존 API의 userId 전달·조회 접근 관례를 따른다.

POST는 HTTP 202, `data.operationId`와 `data.status`를 반환한다.

```http
GET /scenario-groups/103/quality-evaluations/{operationId}
```

GET은 operation과 평가 상세를 조합한 `data`를 반환한다.
주요 필드는 `status`, `lastError`, `inputSnapshot`, `inputHash`, `promptVersion`, `result`, `verdict`,
`averageScore`, `llmMetadata`다. 다른 그룹의 operation, 삭제된 그룹, 평가가 아닌 operation은 404다.
`result.items[].violations[].evidencePath`는 inputSnapshot 기준 JSON pointer다.
그룹·시나리오 필드는 persistence snake_case, Event payload는 camelCase다.

`scenario-set-v5`부터 외부 사실 확인은 시나리오 평가 범위에서 제외한다. 신규 LLM 응답과 저장 결과에는
`factDependency`, `factCheck`가 없으며 NEEDS_FACT를 생성하지 않는다. 입력 밖의 수치·최신성·출처 확인을
요구하지 않고, 입력 Event와 직접 모순되는 내용·Event의 잘못된 인용·내부 논리 문제만 근거와 함께 평가한다.
따라서 PASS는 외부 사실의 진실성이나 최신성을 보장하지 않는다.

과거 NEEDS_FACT/factCheck 이력은 호환 DTO로 읽으며 덮어쓰지 않는다. 기존 DB 제약도 과거 값을 보존하므로
DDL 변경은 필요 없다. 신규 LLM output schema는 호환 DTO와 분리한다.
`scenario-repair-v3`은 외부 사실 분류에 따른 수정 차단을 제거하고, 입력 근거 내의 수정만 수행한다.
Event 변경, 새로운 사실·수치 생성은 계속 금지한다. narrative 변경 시 description도 서버가 동기화한다.
기존 7개 기준·점수 경계·1회 수정 제한·Signpost 전 실행 조건은 유지한다.

## 자동 평가와 실행 수명

canonical v4 SSE 생성 완료 시에는 평가를 실행하지 않는다.
생성 시나리오의 실제 DB ID와 생성에 연결된 Event snapshot을 입력에 고정한다.
snapshot 없는 구형 그룹의 수동 평가는 평가 시점 Event를 고정하고 source에 명시한다.

v4 `complete_validation()`에서 `canProceed=true`이면 평가 접수 여부를 결정한다.
최초 Validation은 변경이 없어도 평가하며, `mode=changed`이면 수정 반영 후 새 평가를 접수한다.
변경 없는 반복 Validation은 최신 평가 operation이 succeeded이면 건너뛴다. 최신 평가가 실패·중단된 경우 다시 평가한다.
BLOCK에는 평가를 만들지 않는다. 평가 입력과 operation은 Validation 완료와 같은 transaction에서 저장하고,
Validation flow가 완료 후 기존 TaskRunner에 제출한다.
자동 requestId는 원본 operation ID에서 UUID5로 생성하며 입력의 sourceOperationId에 원본 작업을 기록한다.
inputHash에는 sourceOperationId·작업 상태·감사 시각을 포함하지 않는다.

평가 operation도 최신/활성 작업 조회에 포함한다. 평가 중 Validation·Signpost·Confirmation 등 기존 활성 작업
검사를 사용하는 편집은 409로 차단한다. 최신 평가 operation에는 기존 Presentation snapshot을 이어 주고,
평가 대기 상태 때문에 완료된 Event 상호작용 내용을 pending으로 바꾸지 않는다.

실행은 기존 TaskRunner/heartbeat/recovery monitor를 사용한다. 일반 예외는 failed, 취소는 interrupted다.
프로세스 강제 종료 시 monitor가 오래된 queued/running 작업을 interrupted로 정리한다. 자동 재개는 없다.
terminal 상태 이후 도착한 모델 결과는 저장하지 않는다. 평가 중에는 DB transaction을 유지하지 않는다.
외부 검색, Signpost 평가, 평가 완료 callback, 별도 worker queue는 포함하지 않는다.

## Signpost 전 1회 자동 수정·재평가

v4의 `scenario_validated` 단계에서 정상 완료한 최초 평가가 WARN/FAIL이면, 입력 근거로 수정 가능한
위반이 있을 때만 수정·재평가를 한 번 시도한다. PASS와 실행 실패는 대상이 아니며,
Signpost 생성 후나 completed 단계의 수동 평가는 내용을 자동 수정하지 않는다.

- 최초 평가 A 완료와 후속 평가 B 접수는 같은 group row lock/transaction으로 처리한다.
  B가 queued/running인 동안 기존 활성 작업 검사로 Signpost·Confirmation·편집이 차단된다.
- B는 `quality_repair` 단계에서 reason/evidence/suggestedFix를 참고해 서로 다른 수정 계획 A/B를 생성한다.
  서버가 두 계획의 대상 경로·위반 참조·수정 범위를 확인하고, 별도 LLM 호출로 해결 가능성·근거 보존·최소 변경을
  각각 1~5점으로 비교한다. 실행 가능한 계획 중 합계가 높은 계획을 선택한다. 동점은 근거 보존 점수, A 순이다.
  계획 점수는 예상 적합도이며 실제 개선 점수가 아니다. 실행 가능한 계획이 없으면 반영 없이 실패로 종료한다.
  선택한 계획의 targets 범위에서만 실제 수정안을 한 번 생성한다. 계획 생성/비교로 LLM 호출이 2회 추가된다.
  수정 대상은 그룹 설명, 기존 Dimension/선택값 설명, 시나리오 제목·본문·근거·기존 선택값 조합이다.
  Event 원문, ID, 확률, pressureContribution, 시나리오/Dimension 추가·삭제는 허용하지 않는다.
- 기존 v4 구조/조합 검증과 별도 LLM 근거 보존 검증을 통과한 경우에만 수정한다. 수정 전 입력 hash와
  현재 DB 입력을 다시 비교하고, 실제 상대 pressure/role은 서버에서 재계산한다.
- 수정 반영, 새로운 Validation acceptance 기록, B의 수정 후 input_snapshot/hash 갱신은 한 transaction이다.
  이전 Validation 이력은 유지하며 새 fingerprint로 Signpost의 stale 검사를 통과할 수 있게 한다.
  이 내부 Validation 기록은 별도의 자동 평가를 만들지 않는다.
- 수정 후 B를 동일한 품질 평가로 실행한다. B가 WARN/FAIL이어도 C를 만들지 않는다.
  제한은 최초 평가 A별 한 번이며 새로운 명시적 평가 요청은 별도 실행이다.
- `scenario-repair-v2`는 최초 WARN/FAIL 해결에 필요한 최소 수정과 기존 유효 정보 보존을 명시한다.
  재평가는 기존 PASS를 포함한 7개 기준 전체를 유지한다. PASS에서 WARN/FAIL로 바뀐 항목을 위한
  추가 LLM 호출 없이 점수 차이와 기존 PASS → WARN/FAIL 항목을 계산해 실행 로그에 기록한다.
  이는 재평가 결과 설명용이며 채택 gate나 rollback이 아니다. 기존 수정 전 근거 보존 검증과 수정 1회 제한을 유지한다.
- 수정안 없음/검증 차단/입력 변경/LLM 오류이면 B는 failed로 종료하고, 수정 반영 전이라면 원본을 유지한다.
  수정 반영 후 재평가 호출이 실패하면 수정된 데이터는 남고 B의 결과는 null이다.
- A의 입력·결과는 불변이며 B는 새 operation_id/request_id를 가진다. 별도 Scenario snapshot 테이블은 없다.
  성공 경로에서는 평가 상세가 두 건, 수정 검증용 validation operation이 한 건 추가된다.

연결·회차·수정안은 기존 operation의 `retry_summary.qualityRepair` JSON에 저장한다.
A의 `reevaluationId`로 B를 조회하며, B에는 `parentEvaluationId`, `attempt=1`, `state`,
`validationOperationId`, 수정 promptVersion, plan, review, LLM 사용량을 기록한다.
`scenario-repair-v4`부터 `planning`에 후보·비교 평가·선택 ID·선택 규칙·모델 사용량도 저장한다.
후보 생성 직후와 비교 완료 직후 각각 저장해 이후 수정/재평가 실패 시에도 계획을 확인할 수 있다.
실제 패치는 기존 `plan`, 근거 검증은 `review`에 유지한다.
API 응답은 `retrySummary.qualityRepair`로 노출한다. A의 succeeded만으로 전체 흐름 완료를 판단하지 말고
reevaluationId가 있으면 B의 종료 상태까지 조회한다. 새로운 DDL은 필요 없다.
재평가의 점수/판정 개선은 보장하지 않으며, 종료 후 진행 허용 여부는 기존 Validation gate를 따른다.
품질 FAIL만으로 Signpost를 영구 차단하는 별도 규칙은 추가하지 않는다.

## 검증

자동 수정의 실제 LLM 검증은 저장된 평가 JSON을 입력으로 격리 SQLite에서 수행할 수 있다.
운영 DB에 접속하지 않고 모든 평가·수정·Validation 기록을 임시 DB에만 저장하며 JSON 결과를 내보낸다.
original_130은 원본 입력, injected_contradiction은 동일 입력의 본문에 모순을 주입한 로컬 음성 테스트다.

```powershell
.venv/Scripts/python.exe -X utf8 tests/manual/test_scenario_quality_repair_live.py `
  --evaluation-json <기존-evaluation.json> --output-dir <새-결과-폴더>
```

자동 회귀: `tests/automated/test_scenario_quality_repair.py`는 수정 1회 제한, 이력 두 건, stale/차단 시
원본 유지, 금지 필드, 완료된 재평가 재실행 방지, Signpost acceptance fingerprint를 검증한다.

```powershell
$env:METADATA_DB_PORT = '3306'
$env:DEBUG = 'false'
.venv/Scripts/python.exe -X utf8 -m pytest tests/automated/test_scenario_quality_evaluation.py -q
```

실제 DB·LLM으로 생성 → 최초 Validation·평가 → 수정 Validation·평가 및 수동 POST/GET을 확인하고 데이터를 보존하려면:

```powershell
.venv/Scripts/python.exe -X utf8 tests/manual/test_scenario_quality_evaluation_live.py `
  --event-ids 69 68 67 --user-id 10603 `
  --output-dir local/output/scenario_quality_live_test/run_name
```

envs/.env를 프로세스에 로드한다. 신규 그룹과 평가 결과를 삭제하지 않으며 외부 프런트엔드 callback만 생략한다.
기존 그룹을 삭제하지 않으므로 Event 조합은 테스트 대상 환경의 점유 상태에 맞게 선택한다.
출력은 summary.json, 생성 SSE, 요청/응답, 평가 JSON, 최종 그룹 snapshot이다.

과거 factCheck 저장·조회 검증용 스크립트(신규 v5 외부 사실 평가에는 사용하지 않음):

```powershell
.venv/Scripts/python.exe -X utf8 tests/manual/test_scenario_fact_check_live.py `
  --event-ids 47 70 --user-id 10603 `
  --output-dir local/output/fact_check_live/run_name
```

Event별 입력·SSE·생성 그룹·평가 API 응답·DB 원본 result_payload·factCheck 항목을 보존한다.
DB와 LLM은 실제 연결을 사용하며 외부 프런트엔드 callback만 생략한다. 자연 생성 결과에
EXTERNAL_FACT_REQUIRED가 없으면 factCheck 목록은 정상적으로 비어 있을 수 있다.


## 고수준 실행 로그

품질 평가 operation의 진행 이벤트 `payload.executionLog`에 Planning → 계획 비교 → 선택 → Self-Correction →
구조/근거 검증 → 실제 반영 → 재평가 → 전후 비교를 기록한다. 서버 로그는 `[AGENT_EXECUTION]`로 필터링한다.
`comparison`은 점수 개선/동일/하락, 새로운 위반, 검토 필요 여부를 제공한다. 저장 후 재평가 실패 시에는
수정 내용이 유지되며 `qualityRepair.state=applied`와 operation 실패 상태를 함께 확인한다.
원본 A의 평가 결과는 변경하지 않는다. 두 계획 비교는 ToT/시뮬레이션 실행으로 표시하지 않는다.
전체 기능의 로그 계약은 [고수준 실행 로그](11_AGENT_EXECUTION_LOG.md)를 참고한다.
