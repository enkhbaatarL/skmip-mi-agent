# Model Parameter Agent Skill 사용 가이드

## 지원 범위

현재 Model Parameter 운영·검증 경로는 Scenario API `v4`의
`multi_event_model_lever_dimensions`만 지원한다. Scenario Group은 기존 v4 API 계약대로
`display_order`가 고정된 Event 1~5개를 가질 수 있다.

다음 경로는 핵심 Skill에서 지원하지 않는다.

- v1 단일 Event 또는 v3 `multi_event_composite_dimensions` proposal 검증
- Event Type별 legacy mapping 품질 평가
- v3/v4 LNG 비교 campaign

과거 코드와 보고서는 회귀 또는 이력 확인에 사용할 수 있지만 현재 release PASS 증적이 될 수 없다.

## 핵심 Skill

| 요청 목적 | Skill | 기본 동작 |
| --- | --- | --- |
| v4 master·Impact Lever·LUT·config·workbook 변경 | [`rollout-model-parameters`](../../../.claude/skills/rollout-model-parameters/SKILL.md) | 하나의 canonical release set에서 구현 산출물을 파생한다. |
| v4 multi-event proposal·Confirmation 품질 | [`model-parameter-multi-event-quality`](../../../.claude/skills/model-parameter-multi-event-quality/SKILL.md) | read-only discovery 후 승인된 경우에만 실제 Flow를 실행한다. |
| v4 release 전체 승인 | [`verify-model-parameter-release`](../../../.claude/skills/verify-model-parameter-release/SKILL.md) | 로컬 회귀, 격리 MySQL, 승인된 target DB와 live Flow를 순서대로 검증한다. |

단순 품질 실행에 release 전체 검증을 붙이지 않는다. 반대로 Scenario 하나가 성공했다는 이유만으로
rollout을 승인하지 않는다.

## 권한 경계

실행 전에 아래 권한을 각각 구분한다.

1. 로컬 automated/static 검사
2. disposable MySQL의 파괴적 SQL 검사
3. target DB dry-run: transaction 안에서 row lock과 DML을 수행한 뒤 rollback
4. target DB commit
5. live proposal·Confirmation row, LLM 비용, resource cache write

앞 단계의 승인이 뒤 단계의 승인을 포함하지 않는다. 계획이나 문서 검토만 요청받았으면 DB, API, LLM을
호출하지 않는다. credential, token, 전체 prompt와 DB 접속 정보는 보고서에 남기지 않는다.

## 신규 파라미터 확장 정합성 게이트

제안 파라미터를 추가·활성화하거나 allow-list를 넓히는 release는 일반 회귀 전에
[파라미터 추가 가이드](06_MODEL_PARAMETER_AGENT_PARAMETER_ADDITION_GUIDE.md)의 파라미터별 정합성
매트릭스를 완성해야 한다. 다음 다섯 데이터 경계를 서로 독립적으로 확인한다.

1. DB 데이터: mgmt versioned DML, Agent canonical master, active Lever binding과 checksum
2. Agent 데이터: proposal capability, workbook contract, runtime allow-list와 출력 `modelTarget`
3. 원본 Excel 데이터: digest가 고정된 workbook의 실제 source sheet/range/header/record
4. 원본의 변형 데이터: CSV/LUT/auxiliary source, adapter·공식·join과 exact-key 결과
5. 최종 모델 입력: 실제 write-target sheet/table/header/key/value field와 단위

원본 reference와 write target을 같은 시트로 가정하지 않는다. 예를 들어 `SupplyDisruption`은
`BCProduction`을 읽지만 결과 target은 `ProductionAdjustment/table2`다. 과거 `VolumeAdjustment` 같은 시트명이
다른 자료에 있어도 현재 target의 별칭으로 허용하지 않는다. sheet/table/header/axis가 exact match하지 않으면
LLM 실행 전 `FAIL`이다. LUT는 정상적으로 원본 exact key가 없을 때의 기준값 fallback일 뿐, 없는 target이나
parser/contract 오류를 복구하는 수단이 아니다.

신규 파라미터마다 최소한 다음 focused test를 개별 실행한다.

- 대표 exact source record의 좌표·값·단위와 원본 cell을 대조한다.
- 같은 좌표의 변형/LUT 값과 공식 또는 join을 재현하고 fallback 허용·차단 조건을 확인한다.
- runtime proposal의 `parameterName`, `modelTarget`, 전체 axes와 최종 절대값 단위를 write target과 대조한다.
- target sheet/table/header의 실제 존재와 capability·DB tuple의 exact match를 확인한다.
- missing key, duplicate/non-finite source, evidence 부족, 범위 위반과 no-change/보류 경계를 확인한다.

DB/canonical만 맞거나 LUT 테스트만 통과하거나 전체 파라미터 수만 맞으면 release `PASS`가 아니다. target DB
적용을 포함하는 release는 별도 승인 후 read-back까지, DML 작성만 포함하는 작업은 DML/canonical 정적 비교까지
증적으로 구분한다.

## v4 품질 평가 기준

### 입력과 lineage

- Group은 `api_version=v4`, `generation_strategy=multi_event_model_lever_dimensions`여야 한다.
- ordered Event relation은 1~5개이며 중복·누락이 없어야 한다.
- Scenario는 모든 Dimension에서 정확히 한 value를 선택해야 한다.
- 선택 value의 `lever_states`만 사용하며 미선택 value, Event Type, legacy dimension mapping을 fallback으로
  사용하지 않는다.
- Group에 저장된 catalog version/checksum, Lever code/ID와 active catalog가 일치해야 한다.

### 후보 경계

- executable Impact Lever binding에서 raw candidate를 만든다.
- v1/v3는 production `MODEL_PARAMETER_PROPOSAL_ALLOWLIST` 5종을, v4는
  `model-parameter-proposal-capabilities-v3`의 ID `{4, 6, 7, 8, 14, 15, 17}`과 name/target을 읽어
  `runtime-allowed`와 `active-but-blocked`를 나눈다.
- blocked candidate는 Step1.5·Step2·Step3·신규 proposal과 그 결과에서 파생된 Confirmation에 도달하면 안 되며
  `PROPOSAL_SCOPE_EXCLUDED` reason code가 있어야 한다.
- `unchanged`, `price_only`, binding 없음과 catalog상 unsupported 상태를 서로 다른 reason code로 보존한다.

### Slot, 값과 저장

- 정확히 v4 전략인 요청은 `new-bc-v3` versioned contract를 사용하고, 변경되지 않은 workbook artifact는
  `resources/basecase_v4/new-bc-v1/`의 digest를 재사용한다. v1/v3는
  기존 `resources/basecase/`를 계속 사용해야 한다. startup은 contract schema/path와 Workbook path/digest만 검증하며
  최초 exact v4 materialization이 sheet/header/range/count를 검증하고 process cache해야 한다.
- v4 authoritative 2026~2030 record 수는 GDP 815, PMI 5,040, PowerMix 4,200, Temperature 5,040,
  LiqUtilAdjustment 23,820, PipelineAdjustment 420, SupplyDisruption 4,908이어야 한다. legacy adjustment target 관찰치는
  authoritative count나 slot whitelist로 평가하지 않는다.
- v4 ordered Event의 `detail_analysis`는 event당 앞 6,000자까지 Step2·Step3 brief에 포함되고,
  5개 Event와 현재 extend7 catalog를 합친 compact Step2 packet이 byte guard 안인지 자동화로 확인한다.
- Step2 slot은 exact Basecase+LUT union 안에 있어야 한다.
- v4 Step2 compact catalog는 값·reference 없이 terminal별 값이 있는 `Life Cycle Category`를 판단 전용
  `applicability_attributes`로 보존하며, v1/v3와 반환 `slot_axes`에는 이 속성이 없어야 한다.
- 운영 설비 차질·회복 Scenario가 명시적인 신규 프로젝트 근거 없이 `FID`·`Planned`·`Under Construction`
  child를 선택하거나, 신규 프로젝트 하나의 근거를 같은 parent의 다른 child 전체로 넓히면 `FAIL`이다.
  여러 Event가 운영·신규 프로젝트 근거를 실제로 함께 제공해 경계가 불명확한 경우만 `REVIEW`로 판정한다.
- 같은 exact slot은 Basecase를 우선하고 LUT를 fallback으로 하나만 사용한다.
- PowerMix raw authoritative source fraction은 기존 5자리 정밀도 변환 없이 보존하고 재정규화하지 않는다.
  Country/Year별 승인된 10-member raw vector, Basecase/LUT 결합 effective vector와 Step3 proposed vector
  각각에서 완전성·중복·유한성·0~1 범위·합 1±`1e-6`을 atomic하게 통과해야 한다. partial group이
  Step3나 persistence에 남으면 `FAIL`이다. Step2 seed의 3축 중복·누락·추가, 비정수 Year 또는 미승인
  Energy Source가 atomic expansion으로 가려져도 `FAIL`이다.
- LiqUtilAdjustment는 Lever·Scenario/Event scope와 applicability 필터 후 exact 후보가 하나면 시설·기간
  문구 일부가 생략돼도 unique-inferred로 허용한다. 동등 후보가 여러 개거나 명시 대상·기간과 모순되면
  Step3 전에 `ABSTAINED_INSUFFICIENT_EVIDENCE`로 제외하고, 1 초과 유효값은 보존한다. lifecycle
  metadata 공란은 exact record를 버리지 않고 applicability에서만 생략해야 한다. 절대 분기·반기와
  교차연도 범위는 연속 월 구간, 상대 기간은 현재 연월 기준의 유한 범위여야 하며 연도 없는 분기·반기를
  일치로 처리하면 `FAIL`이다. 올해/내년 분기의 월 범위를 무시하거나 범위 밖 월·분기·반기, 역전 연도 범위,
  음수·소수 개월을 bare year/양의 기간으로 보정해도 `FAIL`이다.
- PipelineAdjustment와 SupplyDisruption은 각각 exact 5축·3축 reference가 하나로 좁혀질 때 explicit 또는
  unique-inferred 제안을 허용한다. 여러 후보, 대상·기간·단위 모순, ID/name/target drift는 LLM 전에 차단한다.
- Step3 input/reference/result와 최종 DB value 수가 일치해야 한다.
- `proposedValue`는 유한 숫자인 최종 절대값이어야 한다.
- 정량 근거가 부족한 v4 Scenario는 reference 기준의 보수적 모델링 가정을 사용하되, 명확한 방향이면 비영
  변화, 상쇄·불명확이면 설명된 no-change인지 검토한다. parameter 단위·범위 위반과 무관한 Event 숫자 전용은
  `FAIL`, 근거가 약한 크기는 `REVIEW`로 판정한다.
- v4 proposal은 `scenario_group_id`를 authoritative link로 쓰고 `mi_event_id=NULL`이어야 한다.
- endpoint, request/response/callback 필드와 proposal/confirmation 저장 JSON shape에 신규 resource·policy
  필드가 추가되면 `FAIL`이다.
- 빈 Confirmation rollback, 정상 full-payload Confirmation, DB read-back과 reconfirmation을 확인한다.

### 관측성과 판정

- provider가 실제 반환한 Step1.5/2/3 token, 단계별 시간, prompt bytes와 retry를 기록한다.
- retry 후 성공해도 앞선 실패 attempt를 지우지 않고 `REVIEW`로 남긴다.
- CLI는 필수 계약 `FAIL`이나 execution error가 있으면 non-zero로 종료해야 한다.
- 적합한 실제 v4 Scenario가 없거나 read-only라 write 증적이 없는 경우는 `COVERAGE LIMIT`이며 process
  failure가 아니다.

판정은 다음 네 가지를 사용한다.

| 판정 | 의미 |
| --- | --- |
| `PASS` | 실행 범위의 catalog, candidate, slot, persistence 계약이 일치한다. |
| `REVIEW` | 형식은 유효하지만 retry, 관측성 또는 값/rationale의 수동 판단이 필요하다. |
| `FAIL` | 입력, catalog, allow-list, slot, persistence 또는 Confirmation 계약이 깨졌다. |
| `COVERAGE LIMIT` | 실행 가능한 실제 v4 Scenario 또는 승인된 write 증적이 없다. |

## 자동화와 release 순서

명령과 suite membership의 정본은
[`verification-matrix.md`](../../../.claude/skills/verify-model-parameter-release/references/verification-matrix.md)다.

1. dummy config로 `core-smoke`를 실행한다.
2. `new_resources/`를 read-only로 inventory한다. 신규 LUT가 아직 없으면 `NOT PRESENT`로 기록하고,
   staging 파일을 runtime `resources/`와 자동 병합하지 않는다.
3. 변경 영역의 named suite만 반복 실행한다.
4. 최종 worktree에서 전체 `tests/automated`를 한 번 실행한다.
5. SQL artifact가 release 범위이면 disposable MySQL에서 idempotency와 rollback을 검증한다.
6. 별도 승인 후에만 target DB dry-run 또는 commit을 수행한다.
7. 별도 승인 후에만 v4 proposal·Confirmation live 품질 검증을 수행한다.

전체 automated suite는 target DB DML보다 먼저 통과해야 한다. 로컬 mock/unit PASS는 target DB read-back이나
live Confirmation 증적을 대신하지 않는다.

## 요청 예시

### read-only discovery

```text
model-parameter-multi-event-quality Skill을 사용해 주세요.

- 대상: 현재 DB의 v4 multi_event_model_lever_dimensions Group
- write: 없음
- 결과: catalog pin, selected lever state, runtime-allowed/active-but-blocked coverage,
  FAIL과 COVERAGE LIMIT, Markdown 보고서
```

### 특정 Group의 proposal·Confirmation

```text
model-parameter-multi-event-quality Skill을 사용해 주세요.

- 대상: scenario_group_id=<GROUP_ID>
- proposal·Confirmation DB write와 LLM 사용: 승인
- target DB canonical 변경: 금지
- retry: 0

read-only preflight 뒤 selected Lever → raw candidate → allowed candidate → selected → proposed → confirmed
증적과 exact slot/reference, token·시간, proposal ID, Confirmation read-back을 보고해 주세요.
```

### v4 release 검증

```text
verify-model-parameter-release Skill을 사용해 주세요.

- target DB dry-run: 비승인
- target DB commit: 비승인
- disposable MySQL: 승인
- live proposal·Confirmation/LLM: 비승인

v4 canonical·Impact Lever·resource·config·workbook, core/affected/full automated 회귀와 격리 SQL
idempotency/rollback을 검증하고 미실행 단계와 필요한 별도 승인을 명시해 주세요.
```

## 보고서

공식 Markdown은 `tests/reports/model_parameter_agent/` 아래에 한 개만 만든다. runner가 출력한 `REPORT`
경로를 확장하고 같은 실행의 raw 결과와 평가를 별도 파일로 중복하지 않는다. 다음을 포함한다.

- git/config/resource/canonical 식별자와 대상 Group·Scenario ID
- ordered Event와 catalog version/checksum
- raw active, runtime-allowed, active-but-blocked 단계별 수와 reason code
- candidate, slot, lifecycle/applicability 근거, effective reference, proposal/Confirmation DB read-back
- 신규 파라미터별 DB/canonical, Lever, capability, source Excel, transformed/LUT, write target, config,
  runtime output 정합성 PASS/FAIL 행
- 실행 명령, test collected/passed/failed/skipped, token·시간·retry
- `PASS | REVIEW | FAIL | COVERAGE LIMIT` 및 미실행 사유

기존 보고서의 PASS나 하드코딩된 Scenario ID를 현재 worktree의 증적으로 재사용하지 않는다.
