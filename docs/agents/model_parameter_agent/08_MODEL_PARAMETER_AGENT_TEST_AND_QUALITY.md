# Model Parameter Agent Skill 사용 가이드

## 이 문서는 누구를 위한 문서인가요?

이 문서는 테스트 script의 옵션을 직접 외우려는 개발자가 아니라, Codex나 Claude에게 자연어로 Model
Parameter Agent 테스트와 품질 평가를 요청하려는 Skill 사용자를 위한 문서다. 테스트는 API `200`만 보는
작업이 아니다. Scenario 근거에서 올바른 파라미터를 찾았는지, 실제 모델의 exact slot을 골랐는지, 제안값과
근거가 타당한지, 사용자의 Confirmation이 DB에 그대로 남았는지를 함께 확인한다.

이 저장소에는 목적별 실행 절차를 담은 Skill이 있다. 사용자는 상세 명령을 외우지 않고 자연어로 범위와
원하는 결과를 말하면 된다.

```text
자연어 요청
  → 목적에 맞는 Skill 선택
  → 현재 DB·코드·resource에서 대상 동적 발견
  → 허용된 범위에서 proposal / confirmation / 모델 실행
  → JSON·DB read-back·token·시간 증적 수집
  → Markdown 또는 Markdown+PNG 보고
```

계획이나 문서 설명만 요청한 경우에는 DB, API, LLM과 LNG 모델을 실행하지 않는다. 실제 실행은 proposal과
confirmation row, resource cache, provider 비용 또는 모델 출력 파일을 만들 수 있으므로 대상 환경과 write
권한을 먼저 확인한다.

## 어떤 Skill을 사용하나요?

| 요청 목적 | 사용할 Skill | 기본 동작 |
| --- | --- | --- |
| Scenario 하나 또는 Event Type별 proposal·Confirmation 확인 | [`model-parameter-agent-test`](../../../.claude/skills/model-parameter-agent-test/SKILL.md) | 현재 DB에서 대상을 찾고 proposal·Confirmation과 DB read-back을 보고 |
| v3 다중 Event sourceRef·mapping·병합 품질 평가 | [`model-parameter-multi-event-quality`](../../../.claude/skills/model-parameter-multi-event-quality/SKILL.md) | 먼저 read-only discovery, 승인된 경우만 `--execute` |
| 여러 v3/v4 Event-set pair를 LNG 가격까지 비교 | [`compare-model-parameter-v3-v4-lng`](../../../.claude/skills/compare-model-parameter-v3-v4-lng/SKILL.md) | pair·case campaign, 확정 입력 export, Demand→Supply→Trade→Output, MD·PNG |
| canonical·LUT·workbook·DB rollback까지 release 전체 검증 | [`verify-model-parameter-release`](../../../.claude/skills/verify-model-parameter-release/SKILL.md) | 정적 검사부터 격리 MySQL, 승인된 target DB와 실제 Flow까지 단계별 검증 |

단일 Scenario 요청에 release 전체 검증을 붙이지 않는다. 반대로 파라미터 rollout의 최종 승인에는
Scenario 하나가 성공했다는 사실만으로 충분하지 않다.

## 먼저 구분해야 하는 네 가지 결과

### 1. 기술 실행 결과

graph, API 또는 LNG engine이 예외 없이 끝났는지를 본다. HTTP 성공이나 process return code는 이 층의
증적이다.

### 2. Proposal 품질

Scenario와 Event에 맞는 파라미터·slot·기간이 선택됐고, 기준값과 제안값의 단위·방향·크기 및 rationale이
납득 가능한지를 본다.

### 3. Persistence와 Confirmation

`PROPOSED` row가 요청 Scenario·Group에 연결됐는지, 빈 Confirmation이 rollback됐는지, 유효한 전체 payload가
`CONFIRMED`로 저장되고 다시 읽히는지를 본다.

### 4. 모델 결과 품질

확정 parameter를 workbook에 반영한 뒤 Demand→Supply→Trade→Output을 실행했을 때 가격과 upstream 결과가
Scenario의 압력 tag와 어떻게 정렬되는지를 본다. 이 평가는 proposal API 성공과 별개다.

다음과 같은 보고는 피한다.

- API 200만 보고 “E2E 성공”이라고 표현
- `PROCESSING` 접수 응답을 proposal 완료로 해석
- proposal 성공 뒤 Confirmation을 실행하지 않고 전체 성공으로 판정
- engine return code 0을 가격 방향 정합성 PASS로 바꿈
- suitable Scenario 부재를 제품 결함으로 처리

비동기 API는 허용 후보 preflight를 통과하면 HTTP `200`과 `PROCESSING`을 먼저 반환한다. resource runtime은
background graph에서 사용되므로, 접수 뒤 `RUNTIME_REGISTRY_NOT_READY`가 발생해 row가 `FAILED`가 되고
실패 callback이 올 수 있다. 동기 API에서 같은 오류가 발생한 경우에만 그 요청이 즉시 HTTP `503`을 받는다.

## 현재 proposal 범위를 읽는 법

체크인 canonical 기준선에는 master 활성 capability 16개가 있고, 전역 합집합 기준으로 v1/v3 raw
mapping은 10개, v4 raw binding은 16개 활성 parameter에 도달할 수 있다. 이 수치는 live DB 조회 결과나
요청 하나의 후보 수가 아니다. 실제 테스트는 live DB를 동적으로 발견하고, 요청별 lineage·선택 value에서
나온 하위 집합에 다음 runtime allow-list를 적용한다.

- `GDP`
- `PMI`
- `PowerMix`
- `Temperature`
- `LiqUtilAdjustment`

DB/catalog에서 활성이나 allow-list 밖인 항목은 `active-but-blocked`다. 이 항목이 LLM과 proposal row 생성
전에 제외되는 것은 기대 동작이며 빈 coverage 실패가 아니다. 다만 허용 항목인데 mapping·binding, exact slot
또는 persistence 결함 때문에 실행되지 못했다면 실패 원인을 별도로 판정한다.

정확한 경계는 [개요](01_MODEL_PARAMETER_AGENT_OVERVIEW.md), 후보 처리 순서는
[Flow](04_MODEL_PARAMETER_AGENT_FLOW.md), 기준값 규칙은
[Basecase·LUT](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md)를 참고한다.

## 평가 기준

### 1. Scenario grounding

- 요청한 `scenario_id`와 저장된 Scenario·Group이 일치하는가?
- v3는 ordered Group–Event relation과 `sourceRefs`로 원본 Event Type·Dimension을 복원하는가?
- v4는 선택된 value의 Lever state만 사용하고 catalog checksum·Lever code/ID를 검증하는가?
- 관련 없는 Dimension이나 미선택 value가 proposal 근거에 섞이지 않는가?

### 2. Candidate 정확성

- v1/v3 direct·routing 또는 v4 executable binding에서만 raw 후보가 나오는가?
- runtime allow-list 밖 항목이 Step1.5·Step2·Step3 전에 제외되는가?
- 같은 parameter로 수렴한 여러 source의 lineage·Lever provenance가 보존되는가?
- routing 선택과 제외 이유가 Scenario·Event 근거와 맞는가?

### 3. Exact slot과 reference

- model target과 모든 key axis가 등록된 정의와 일치하는가?
- Step2 좌표가 Basecase/LUT exact union 안에 있는가?
- 같은 slot에 Basecase가 있으면 LUT보다 우선하는가?
- LUT-only slot의 저장 `basecaseValue`가 `null`인가?
- partial key, nearest period 또는 다른 시설 fallback이 없는가?

### 4. 제안값과 rationale

- `proposedValue`가 증감량이 아니라 해당 모델 필드의 최종 절대값인가?
- GDP 비율, PMI index, PowerMix share, Temperature, LiqUtil 비율의 단위를 구분하는가?
- Event의 방향·강도·기간과 기준값을 함께 설명하는가?
- parameter rationale과 slot별 rationale이 각각 “왜 이 파라미터인가”와 “왜 이 위치·값인가”에 답하는가?
- 형제 Scenario에서 방향 또는 기간이 달라질 때 제안도 일관되게 달라지는가?

### 5. 저장과 Confirmation

- proposal ID, Scenario ID, Group ID가 DB row와 일치하는가?
- v1은 대표 `mi_event_id`를 사용하고 v3/v4는 `mi_event_id=NULL`인가?
- 빈 `confirmationParameters=[]`가 거절되고 기존 row가 바뀌지 않는가?
- 선택한 E2E test path에서 성공한 proposal을 full payload로 확정하고 DB read-back하는가?
- API 계약상 원래 proposal과 항목·값의 동일성을 강제하지 않으며 수정·추가·삭제·custom parameter가 구조 검증 범위에서 동작하는가?
- 각 value의 `proposedValue` key는 필수지만 `null` 값은 허용되고, non-null 값만 유한 숫자로 검증되는가?
- 재확정이 같은 row의 Confirmation과 시각을 갱신하고 proposal 원본은 보존하는가?

### 6. 시간·token·retry

- Scenario 전체 시간과 Step1.5·Step2·Step3 호출별 시간이 기록되는가?
- provider가 반환한 input/output/total token만 사용하고 누락값을 추정하지 않는가?
- retry가 발생하면 최종 성공과 별도로 `REVIEW` 증적을 남기는가?
- 실패한 attempt의 단계·오류·부분 state가 최종 성공으로 덮이지 않는가?

### 7. 보고서 완전성

- 실행 환경, git 상태, config/resource release와 대상 ID가 식별되는가?
- 실제 요청·응답, proposal row, Confirmation read-back과 오류가 연결되는가?
- `PASS`, `FAIL`, `REVIEW`, `COVERAGE LIMIT`을 구분하는가?
- 실행하지 않은 단계는 `SKIPPED` 또는 `N/A`와 이유로 표시하는가?
- credential, token 값과 전체 민감 prompt가 보고서에 들어가지 않는가?

## 자연어 요청 예시

아래 문장은 그대로 복사한 뒤 ID, 환경과 범위만 바꾸어 사용할 수 있다.

### Scenario 하나를 proposal부터 확정까지

```text
model-parameter-agent-test Skill을 사용해 주세요.

- 실행 환경: 현재 설정의 로컬 DB와 resource
- 대상: scenario_id=<SCENARIO_ID>
- 범위: proposal 생성, 빈 confirmation rollback, 정상 confirmation,
  reconfirmation, DB read-back
- 기존 데이터: 보존

실제 후보·선택 parameter, exact slot, Basecase/LUT 기준값, 제안값과 근거,
Step별 token·시간·retry, proposal ID, confirmation 결과와 보고서 경로를 알려 주세요.
```

동기 graph 실행과 실제 배포 API smoke는 다른 범위다. 외부 VM API를 확인하려면 실행 환경과 base URL을
명시하고, 기존 proposal row 보존 여부도 함께 적는다.

### 특정 파라미터의 현재 coverage

```text
model-parameter-agent-test Skill을 사용해 주세요.

현재 DB에서 GDP에 direct 또는 routing으로 연결된 Event Type을 동적으로 찾고,
Event Type별 Scenario Group 1개와 Scenario 2개씩 proposal·confirmation까지 테스트해 주세요.
과거 Scenario ID를 재사용하지 말고 현재 DB에서 선택해 주세요.

결과는 parameter → Event Type → Scenario 순서로 정리하고, 실행하지 못한 대상은
FAIL과 COVERAGE LIMIT을 구분해 주세요.
```

현재 allow-list 밖의 active parameter를 요청하면 proposal 성공을 만들기 위해 mapping이나 allow-list를
바꾸지 않는다. `active-but-blocked` 제외 경계가 지켜졌는지를 확인한다.

### 겨울 한파와 여름 폭염 Event Type

```text
model-parameter-agent-test Skill을 사용해서 event_type_l2_id 6(겨울 한파)과
7(여름 폭염)의 기존 Scenario를 테스트해 주세요.

빠른 샘플로 Event Type별 Group 1개, Scenario 2개씩 선택하고 proposal과
confirmation DB read-back까지 진행해 주세요. Temperature 후보·slot·값의 방향,
실행시간과 token, retry, 실패 단계와 통합 보고서 경로를 알려 주세요.
```

“폭엄”은 “폭염” 요청으로 해석한다. “각각”인지 여러 Event를 묶은 한 Group인지 결과가 달라지는 요청은
명확히 적는다.

### v3 다중 Event quality discovery만

```text
model-parameter-multi-event-quality Skill을 사용해 주세요.

현재 DB의 v3 multi_event_composite_dimensions Group을 read-only로 발견하고
ordered Event 관계, sourceRefs lineage, legacy mapping eligible 후보,
runtime-allowed와 active-but-blocked coverage를 평가해 주세요.

proposal·confirmation write와 LLM 호출은 하지 말고, schema/lineage FAIL,
warning, COVERAGE LIMIT과 discovery 보고서 경로를 알려 주세요.
```

이 요청은 기본 read-only discovery다. `parameter_mapping_ready=false` 또는 승인 projection 부재만으로
Scenario를 제외하지 않으며, malformed lineage와 단순 mapping 부재는 다른 판정이다.

### 특정 v3 Group을 실제 proposal·confirmation까지

```text
model-parameter-multi-event-quality Skill을 사용해 주세요.

- 대상: scenario_group_id=<GROUP_ID>
- 실행: 실제 proposal·confirmation write 승인
- 기존 Group과 canonical 자료: 변경 금지
- retry: 기본 0

discovery를 먼저 수행한 뒤 source occurrence별 eligible → candidate → selected →
proposed → confirmed matrix, mi_event_id=NULL read-back, Step별 prompt byte·token·시간,
retry와 통합 보고서 경로를 알려 주세요.
```

`--execute`는 proposal과 Confirmation DB row를 생성·변경한다. target DB나 write 권한이 불명확하면
실행하지 않고 discovery까지만 보고한다.

### v3/v4 proposal 차이를 비교

```text
현재 DB에서 ordered Event ID가 동일한 v3/v4 Scenario Group pair를 찾아
Model Parameter proposal과 confirmation 결과를 비교해 주세요.

먼저 SELECT-only로 pair와 coverage를 보여 주고, 기존 pair를 사용할 수 있을 때만
proposal·confirmation을 실행해 주세요. counterpart Group을 새로 만들지 마세요.
version별 후보 출처, parameter·slot·값·rationale, token·시간·retry,
confirmation read-back과 비교 보고서 경로를 알려 주세요.
```

proposal 비교와 LNG engine 가격 비교는 다르다. 모델 계산까지 필요하면 다음 campaign 요청을 사용한다.

### 여러 pair를 LNG 결과까지 비교

```text
compare-model-parameter-v3-v4-lng Skill을 사용해 주세요.

- 대상 환경: <DB/실행 환경>
- 목표: 서로 다른 ordered Event-set pair 3개 이상, engine case 20개 이상
- 기존 pair 우선, 새 counterpart Group 생성은 금지
- proposal·confirmation write와 LLM 실행: 승인
- 공식 산출물: Markdown과 summary PNG

pair discovery, exact proposal ID와 confirmed payload hash 고정, workbook export,
Demand→Supply→Trade→Output 실행, pressure-tag alignment와 model expressiveness를
분리 평가해 주세요. 실패 attempt도 보존하고 v4 isolation, 시간·token·disk,
COVERAGE LIMIT과 공식 파일 경로를 알려 주세요.
```

DB coverage가 목표 pair/case 수보다 적으면 임의로 목표를 낮추지 않고 `COVERAGE LIMIT`으로 보고한다.
Engine PASS, 가격 tag 정합성과 model expressiveness는 각각 독립 판정한다.

### Model Parameter release 전체 검증

```text
verify-model-parameter-release Skill을 사용해 현재 Model Parameter release를 검증해 주세요.

- target DB commit: 하지 않음
- target DB dry-run/DML: 하지 않음
- disposable MySQL static SQL 검증: 포함
- 실제 proposal·confirmation row 생성: <승인/비승인>

canonical fixture, resource release·LUT catalog와 startup warning 경계, config.yaml·ConfigMap parity, workbook/archive,
자동화 회귀, 격리 MySQL idempotency·rollback, 허용된 실제 Flow를 단계별로 확인하고
수행한 명령과 collected/passed/failed/skipped 수, COVERAGE LIMIT, 통합 보고서 경로를 알려 주세요.
```

target DB commit이나 rollback-only DML도 명시적인 대상과 권한이 필요하다. runtime allow-list만 바뀐
release에서는 DB/canonical/config/workbook을 5개 allow-list에 맞춰 다시 쓰지 않는다.

## 프롬프트를 직접 만들 때의 기본 틀

```text
<사용할 Skill 이름>을 사용해 주세요.

- 어디에서: <로컬 / 외부 VM / disposable MySQL / target DB>
- 무엇을: <Scenario ID / Group ID / Event Type / parameter / pair 수>
- 어디까지: <discovery / proposal / confirmation / workbook export / LNG engine>
- 허용하는 write: <없음 / proposal·confirmation / Group 생성 / target DB apply>
- retry와 예산: <횟수 / 시간 / token / case 수>
- 보존: <기존 DB row·실패 attempt·output을 보존할지>
- 받고 싶은 결과: <판정 / 실제 값 / 원인 / 보고서 / PNG>
```

필수 정보가 없고 선택에 따라 외부 변경 범위가 달라지면 Skill이 실행 전에 확인한다.

## 결과 파일은 어디에 생기나요?

### 공식 Model Parameter 보고서

```text
tests/reports/model_parameter_agent/
```

단일 Scenario, Event Type, v3 multi-event quality, release verification의 Markdown 보고서는 기본적으로 이
경로 아래에 둔다. runner가 만든 `REPORT` 또는 `REPORT_IN_PROGRESS` 경로를 최종 보고서의 기준으로 사용하고,
같은 요청의 raw 실행 결과와 품질 평가를 불필요하게 두 파일로 나누지 않는다.

### v3/v4 LNG campaign

campaign의 공식 Markdown·PNG와 pair별 JSON, manifest, 실패 attempt 증적은 실행 시 고정한 campaign
artifact 경로에 둔다. 최종 응답은 공식 MD·PNG의 절대경로와 완료·실패·coverage case 수를 함께 알려야 한다.
기존 [historical reports](../../../tests/reports/model_parameter_agent/)는 형식 참고나 과거 증적이며 현재
실행의 성공을 대신하지 않는다.

### 자동화 테스트

자동화 코드는 `tests/automated/test_model_parameter_*.py`에 있다. suite membership과 실행 명령의 정본은
[verification matrix](../../../.claude/skills/verify-model-parameter-release/references/verification-matrix.md)다.
고정된 과거 test count를 현재 계약으로 쓰지 않고, 실행 당시 pytest collected/passed/failed/skipped 수를
보고한다.

## 실행할 때 주의할 점

### 같은 proposal을 무조건 재시도하지 않기

비동기 proposal timeout 뒤 같은 요청을 다시 보내면 새 proposal row가 생길 수 있다. 먼저 callback, 로그와
`tmm_mi_model_param_proposal_m`을 확인해 기존 작업의 실제 상태를 판정한다.

### 기존 row와 실패 attempt 보존하기

테스트가 만든 proposal·Confirmation row는 사용자가 cleanup을 요청하지 않는 한 보존하고 ID를 보고한다.
LNG engine 실패 attempt는 최종 retry가 성공해도 지우거나 성공 결과로 덮지 않는다.

### 현재 DB에서 대상을 다시 찾기

Scenario ID, mapping 후보와 routing winner는 DB 상태에 따라 달라질 수 있다. 문서와 과거 보고서의 ID를
실행 대상으로 그대로 재사용하지 않고 현재 DB에서 다시 확인한다.

### API 성공과 품질 성공 구분하기

API/graph 성공, proposal 내용 품질, Confirmation persistence, 모델 가격 정합성을 각각 표시한다. 어느 한
층의 성공을 다른 층의 PASS로 올리지 않는다.

### FAIL과 COVERAGE LIMIT 구분하기

적합한 기존 Scenario나 동일 ordered Event-set pair가 없는 것은 `COVERAGE LIMIT`이다. 유효한 대상이 있는데
mapping, lineage, exact slot, persistence, rollback 또는 Confirmation 계약이 깨진 것은 `FAIL`이다.

### 실행하지 않은 검사를 통과로 쓰지 않기

DB apply, 실제 LLM, Confirmation, engine 또는 visual PNG 검증을 실행하지 않았다면 `SKIPPED`, `N/A` 또는
`미실행`으로 기록한다. 과거 보고서의 PASS를 현재 worktree의 PASS로 재사용하지 않는다.

## 관련 문서

| 궁금한 내용 | 문서 |
| --- | --- |
| Agent의 역할과 현재 허용 범위 | [처음 이해하기](01_MODEL_PARAMETER_AGENT_OVERVIEW.md) |
| proposal·Confirmation 요청과 오류 | [API Spec](02_MODEL_PARAMETER_AGENT_API_SPEC.md) |
| 후보→slot→값→저장 처리 순서 | [기능 Flow](04_MODEL_PARAMETER_AGENT_FLOW.md) |
| DB table과 상태 전이 | [DB Spec](03_MODEL_PARAMETER_AGENT_DB_SPEC.md) |
| Basecase/LUT exact reference | [Basecase·LUT](05_MODEL_PARAMETER_AGENT_BASECASE_LUT_PARSING.md) |
| parameter rollout 절차 | [파라미터 추가·활성화](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md) |
| release 검증의 상세 suite | [verification matrix](../../../.claude/skills/verify-model-parameter-release/references/verification-matrix.md) |
