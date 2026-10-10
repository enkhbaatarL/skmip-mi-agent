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
  `model-parameter-proposal-capabilities-v4`의 ID
  `{4, 6, 7, 8, 11, 12, 13, 14, 15, 16, 17, 18, 20, 22, 23, 24}`과 name/target을 읽어
  `runtime-allowed`와 `active-but-blocked`를 나눈다.
- blocked candidate는 Step1.5·Step2·Step3·신규 proposal과 그 결과에서 파생된 Confirmation에 도달하면 안 되며
  `PROPOSAL_SCOPE_EXCLUDED` reason code가 있어야 한다.
- `unchanged`, binding 없는 `price_only`, binding 없음과 catalog상 unsupported 상태를 서로 다른 reason code로
  보존한다. conditional binding이 있는 `price_only`는 근거가 없을 때 Step1.5에서 0건으로 탈락한다.

### Slot, 값과 저장

- 정확히 v4 전략인 요청은 `new-bc-v8` versioned contract를 사용한다. 활성 MI Base workbook은 Object Storage에서
  받은 실제 digest를 요청별로 고정하고, startup/configured-fallback 검증은
  `resources/basecase_v4/new-bc-v2/` packaged baseline digest를 사용한다. v1/v3는
  기존 `resources/basecase/`를 계속 사용해야 한다. startup은 contract schema/path와 Workbook path/digest만 검증하며
  최초 exact v4 materialization이 sheet/header/range/count를 검증하고 process cache해야 한다.
- proposal-only frozen-context guard는 persisted Scenario/Event/Group context 변경을 계속 차단하되, graph가
  request-local state에 추가하는 `mi_base_case_id`는 Scenario mutation으로 판정하지 않는다. 이 예외는 최상위
  request pin 하나에만 적용하고 Scenario/Event/Group field drift는 persistence 전에 실패해야 한다.
- v4 authoritative 2026~2030 record 수는 GDP 815, PMI 5,040, PowerMix 4,200, Temperature 5,040,
  LiqUtilAdjustment 23,820, PipelineAdjustment 420, SupplyDisruption 4,908이어야 한다. legacy adjustment target 관찰치는
  authoritative count나 slot whitelist로 평가하지 않는다.
- v4 ordered Event의 `detail_analysis`는 event당 앞 6,000자까지 Step2·Step3 brief에 포함되고,
  5개 Event와 현재 extend16 catalog를 합친 compact Step2 packet이 byte guard 안인지 자동화로 확인한다.
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
- Step1.5/2/3에서 정상적인 미제안이 발생해도 structured reason code/stage, 종료 단계까지의 candidate/slot/value
  sanitizer 요약과 누적 LLM call을 예외에 안전하게 전달한다. 전체 prompt/messages/Scenario context는 저장하지 않는다.
- proposal-only runner는 이 결과를 일반 `FAIL`이 아닌 Scenario `ABSTAINED`, campaign `REVIEW`로 분류한다.
  구조화 증적이나 필수 step/token 관측이 빠지면 별도 `REVIEW`로 남긴다.
- retry 후 성공해도 앞선 실패 attempt를 지우지 않고 `REVIEW`로 남긴다.
- 활성 MI Base 실행은 graph와 post-graph trace의 `case_id`·`run_seq`·role별 workbook SHA-256이 같아야 한다.
  기본 정책에서 remote와 `verified_cache`의 source 전환은 같은 content identity에서만 허용한다. 승인된
  `active_case_unavailable_mode=configured_fallback` campaign은 remote identity가 관측되기 전의 가용성 실패에만
  등록 Basecase를 사용하고 graph/trace 모두 같은 configured hash를 증적한다. remote metadata 관측 뒤의
  download·hash·contract 실패에는 이 예외를 적용하지 않는다.
- Step1.5/2/3 semantic abstention도 MI Base 준비 뒤 발생하므로 안전 예외 trace에 같은 path-free identity를
  포함한다. 누락 시 특정 fallback을 요구한 campaign은 관측 불완전 `FAIL`이다. semantic abstention과 node failure의
  source·test가 이후 실행에서 identity를 직접 전달하는지 확인하고, 추론 증적을 직접 관측으로 표기하지 않는다.
- CLI는 필수 계약 `FAIL`이나 execution error가 있으면 non-zero로 종료해야 한다.
- 적합한 실제 v4 Scenario가 없거나 read-only라 write 증적이 없는 경우는 `COVERAGE LIMIT`이며 process
  failure가 아니다.

### Group별 대표 Scenario 3개 평가

Group마다 대표 Scenario 3개만 Proposal하는 add-only campaign은 전체 Scenario를 먼저 read-only preflight한다.
같은 Event 입력을 다시 쓰면 `same_logical_inputs/add-only`, baseline과 다른 Event 20개를 먼저 선정하면
`expanded_event_cohort/add-only`로 구분한다. 후자는 baseline/expanded Event ID 완전 비중복, expanded Event 20개
고유성, 신규 Group 20개 순증과 기존 Group 삭제 0을 선택 plan의 hard gate로 둔다. 동일 Event 재생성 증적은
expanded cohort의 최종 KPI와 fixture에서 제외한다.

기존 Scenario-only reference fixture의 Event 40개를 원본 풀로 삼아 **Scenario부터 다시 생성**하는 campaign은
`existing_event_pool/add-only-regenerated-scenarios`로 구분한다. ordered Event ID 40개를 추가·교체 없이 그대로
재사용하고 원본 Group/Scenario는 삭제·수정하지 않는다. Event별 신규 v4 Group 생성, validation, confirmation 뒤
원본 Group 40개 보존·신규 Group 40개 순증·원본/신규 Group ID 비중복·Scenario Lever `v4.1` exact pin을 hard
gate로 둔다. 이 정책은 Event cohort 확장이 아니므로 baseline과 Event ID가 겹치는 것이 정상이다. Signpost는 Model
Parameter Proposal 필수 입력이 아니면 생략할 수 있다.
명시적 LLM validation failure가 Scenario 0건의 미완료 Group을 남기고 active operation이 없음을 read-back으로
증명한 경우에만 별도 1회 bounded retry를 허용한다. 동일 Group 복구인지 새 Group 생성인지 기록하고, 새 Group이면
최초 미완료 Group을 삭제하지 않고 audit으로 남기며 완료 Group 40개와 대표 Scenario/Proposal KPI 분모에서는 제외한다.

baseline·floor·ceiling 대표성을 우선하고, 동일 대표성 후보 사이에서 runtime canonical Parameter type set overlap이
가장 큰 조합을 선택한다. 선정 ID는 Proposal 전에 고정하며 Confirmation과 callback은 호출하지 않는다.

결과는 다음 지표를 분리한다.

- 전체 고정 대표 Scenario 기준 Proposal 성공률과 Group별 triple-success 비율
- Proposal-eligible 기준 preflight→Proposal 전환율, semantic-empty율, 실패 시 무저장 원자성
- triple-success Group 기준 세 Proposal의 canonical Parameter type set 동일률
- type-consistent Group 기준 대표 3개의 전체 proposed value signature가 서로 모두 다른 비율. Parameter별 proposed
  value는 순서 독립 multiset으로 정규화해 cell 배열 순서만 바뀐 경우를 변별로 세지 않는다.
- Parameter와 모든 model slot 좌표가 같은 cell에 한정한 exact-slot 값 변별률
- `scenario_group_id`/`scenario_id`/`mi_event_id=NULL`, persistence integrity, retry/token/p50/p95
- 고정 eligible Scenario ID와 실제 attempt ID exact match, 최종 covered/uncovered/skip Scenario ID 및 Group identity

type/value 지표에 Proposal 실패나 semantic abstain을 억지로 포함하지 않는다. 대신 전체 Proposal 성공률에 그대로
남기고, triple-success가 아닌 Group의 종류/값/exact-slot은 `N/A`로 표시한다. exact slot 교집합이 없는 Group은
`not comparable`로 집계한다. 선정과 평가는
`tests/manual/model_parameter_agent/evaluate_representative_trios.py`를 사용하며 현재 release identity는
Scenario Lever `v4.1`, Proposal Flow `v4.1.7`을 각각 기록한다.
중단·재개 등으로 실행 증적이 비중복 파일 여러 개라면 `--execution-evidence`를 반복한다. 도구는 release identity가
같은지 검사하고 동일 Scenario attempt가 중복되면 덮어쓰지 않고 실패한다. 코드 수정 뒤 동일 Scenario를 재실행한
증적은 `--post-fix-execution-evidence`와 필수 `--post-fix-reason`으로만 명시 교체하고 원 source/status/stage를
audit에 보존한다. post-fix가 있으면 baseline과 최종 attempt의 Scenario ID 집합이 같은지 hard gate로 확인하고,
성공·semantic abstention·기타 실패·구조화/완전 trace의 개선 전후 수치와 증감을 표로 남긴다. 재사용 요청이 있으면
Proposal 실행 전에 `evaluate_representative_trios.py freeze --plan <plan> --output
tests/fixtures/model_parameter_agent/<dataset>.json`으로 해당 campaign의 고정 cohort를 최초 1회 저장하며 기존 파일을
덮어쓰지 않는다. 기존 expanded Event campaign은 20 Group·60 Scenario 계약을 유지하고, 기존 Event 풀 재생성
campaign은 40 Group·120 대표 Scenario 계약을 사용한다. v4.1.7 Before/After는 기존
`v4_1_2_existing_latest_distinct_representative_trio_40_groups_20261007.json`의 ordered Group/Event/Scenario
ID를 그대로 사용하며 신규·교체 Scenario를 섞지 않는다. fixture의 source Flow 표기는 v4.1.2로 유지하고 실제
실행 manifest의 target Flow `v4.1.7`은 별도 release gate로 검증한다.
이후에는 `--testset-input`으로 fixture SHA-256과 ordered Group/Event/Scenario ID를
plan과 exact 대조하며 fixture를 다시 생성하지 않는다. 고정 assertion은 release contract·Group/Scenario selection이며
LLM 결과 baseline은 회귀 비교용 관측값이다. expanded campaign fixture에는
`selection_policy=expanded_event_cohort/add-only`와 baseline/expanded Event identity도 함께 보존한다. 최종 Markdown은
그룹별 결과, Read-only KPI, Proposal 결과 KPI, 개선 전후 비교 표의 컬럼 정의를 고정 섹션으로 항상 포함한다.
Read-only KPI 표는 대상, release pin, runtime-capable/coverage limit, current write eligible/covered, trio 가용성,
후보 종류 동일, FAIL/hard stop의 핵심 7개로 압축한다. `runtime-capable`은 runtime 후보 존재, `current write
eligible`은 지금 새 Proposal을 쓸 수 있는 상태, `covered`는 기존 Proposal로 인한 중복 쓰기 차단, `coverage limit`은
runtime 후보가 없어 실행하지 않는 상태라고 설명한다. KPI 개선안은 신규 KPI 추가가 아니라 기존 Proposal 성공률,
triple-success, 종류 동일성, Scenario별 값 변별을 높이는 방안으로 작성한다.

공식 release 평가는 항상 같은 고정 cohort를 대상으로 한 live clean 전건 replay이며, 이번 campaign에서 새로 저장된
Proposal ID만 KPI에 사용한다. 이전 campaign의 Scenario별 `PASS→UNPROPOSED` 같은 전이는 원인 분석용 관측값이지
개별 복구 대상이나 release gate가 아니다. 과거 성공 Scenario를 골라 재실행하거나 이전 결과를 재현하도록 강제하지
않으며, 부분 post-fix 결과를 공식 live clean KPI에 합산하지 않는다.

`full-trio success`는 한 Group의 고정 대표 Scenario 3개 모두가 해당 live clean campaign에서 신규 Proposal row를
저장하고, DB read-back `proposal_parameters`에 하나 이상의 유효 value cell을 가진 상태다. 하나라도 semantic
abstention, 기술 실패, capability limit 또는 payload 결손이면 full-trio가 아니다. Parameter type 동일성과 세
Scenario 값 변별은 full-trio 성공 이후에 평가하는 별도 KPI다.

Live campaign 완료 뒤 최종 DB read-back에는 평가 대상 Proposal row의 `proposal_parameters` payload를 포함한다. 고정
testset과 이 read-back을 `evaluate_representative_trios.py final-cohort`에 전달해 `최종 DB 기준 Trio
Parameter·값 변별` Markdown/JSON을 생성한다. release-replay는 과거 blocking 행이 아닌 이번 실행에서 생성된
`final_campaign_readback` ID만 사용한다. 해당 섹션은 전체 고정 Scenario 성공률, full-trio 수, full-trio의
Parameter type set 동일률, type-consistent trio의 전체 proposed-value signature 변별률, exact common slot 값
변별률, scalar exact-slot과 PowerMix atomic-vector 분리 지표, slot rationale의 사용자 설명 7개 섹션 완전성과
내부 구현·평가 용어 노출, 1,200자 초과·평서체 종결 건수를 포함해야 한다. 내부 evidence enum과 policy release/mode는 trace에서 검증하고
공개 rationale 문자열의 필수 항목으로 요구하지 않는다.
evidence schema v6 이상은 secret을 제외한 전체 `model_parameter_*` 로컬·Neuro 선언값, runtime effective 값,
config SHA와 선언 차이를 포함해야 한다. Proposal payload 누락, campaign row 중복, testset/history
scope 또는 Group identity 불일치는 fail-closed다. 일반 `evaluate` 명령도 `--testset-input`과
`--final-history-evidence`가 함께 주어지면 같은 섹션을 자동 부착하며, 이 섹션이 없는 live campaign Report는 완료로
간주하지 않는다.
최종 섹션은 미제안·실패도 Group/Event, 중단 단계, reason code, 확정 가능한 Parameter별로 자동 집계하고,
hotspot별 개선 방향과 안전 경계를 함께 렌더링한다. semantic abstention·기술 실패·capability limit을 분리하며,
Step1.5 미결정 routing은 모든 입력 후보 Parameter의 실패로 중복 집계하지 않는다.

```bash
python tests/manual/model_parameter_agent/evaluate_representative_trios.py final-cohort \
  --testset-input tests/fixtures/model_parameter_agent/<dataset>.json \
  --final-history-evidence <run-dir>/final-full-cohort-read-only.json \
  --output-json <run-dir>/final-cohort-trio-quality-report.json \
  --output-markdown <run-dir>/final-cohort-trio-quality-report.md
```

v4.1.7 완료 기준은 동일 40 Group trio에서 다음과 같이 판정한다.

| 지표 | Gate | Target |
| --- | ---: | ---: |
| Proposal-eligible 성공률 | 70% | 80% |
| Group triple-success | 60% | 70% |
| 과거 campaign 성공 Scenario 유지율 | 관측 전용 | 비-gate |
| catalog 밖 Parameter·존재하지 않는 slot | 0건 | 0건 |
| slot rationale 필수 항목 누락 | 0건 | 0건 |
| slot rationale 내부 구현·평가 용어 노출 | 0건 | 0건 |
| slot rationale 1,200자 초과·평서체 종결 | 0건 | 0건 |
| 부당한 causal assumption | 5% 이하 | 0% |
| 기술적 `FAILED` | 1% 미만 | 0% |

`ABSTAINED_NO_CHANGE`는 resolved no-change로 별도 집계하고, 근거·slot·값 보강이 필요한 actionable semantic
abstention과 분리한다. 수급모델 결과의 가시적 차이는 이 Flow가 강제하지 않으며 완료 gate에 포함하지 않는다.

Live campaign은 전체 120건 완주가 기본이지만, 최소 20건 실행 뒤 성공률이 Gate보다 20%p 이상 낮고 동일 semantic
stage가 실패·기권의 70% 이상을 계속 차지하면 조기 중단할 수 있다. 중단 시까지의 원본 증적과 저장된 성공 Proposal은
보존하고 자동 재시도하지 않는다. 원인 수정 후에는 기존 성공·covered Scenario를 제외한 실패/미제안 Scenario만
별도 `post-fix re-test` 증적으로 실행하며, 최초 실행과 합쳐 하나의 무중단 campaign처럼 보고하지 않는다.
이 부분 실행은 진단용이며, 공식 release KPI 재평가는 고정 cohort 전체의 별도 live clean campaign으로 다시 수행한다.

Object Storage 장애 시 특정 fallback으로 실행해야 하는 campaign은 proposal-only runner에
`--require-mi-base-fallback-mode configured_fallback`을 주고 evaluator에도
`--expected-mi-base-fallback-mode configured_fallback`을 준다. 로드된 정책이 다르면 Scenario 실행 전에 `BLOCKED`,
평가에서는 운영 정합성 `FAIL`로 닫아 파일명이나 운영자 가정만으로 fallback을 판정하지 않는다.
로컬 Object Storage 미연동 때문에 `configured_fallback`을 사용한 결과는 고정 workbook Basecase 기반 평가이며,
active MI Base/Object Storage 연동 검증 결과로 해석하지 않는다.

### 기존 Scenario-only 최신 pool 확장

신규 Group/Scenario 생성 없이 기존 결과로 testset을 확장할 때는
`tests/manual/model_parameter_agent/collect_existing_representative_trios.py`를 사용한다.

```bash
python tests/manual/model_parameter_agent/collect_existing_representative_trios.py \
  --max-groups 50 \
  --inventory-output <run-dir>/inventory.json \
  --preflight-output <run-dir>/read-only-preflight.json \
  --plan-output <run-dir>/representative-trio-plan.json \
  --testset-output tests/fixtures/model_parameter_agent/<dataset>.json \
  --report-json <run-dir>/collection-report.json \
  --report-markdown <run-dir>/collection-report.md
```

수집 기준은 다음과 같다.

- Scenario Lever `v4.1`, Proposal Flow `v4.1.7`, API `v4`, strategy
  `multi_event_model_lever_dimensions`를 exact pin한다.
- Group status `created|realized`, stage `completed`, `parameter_mapping_ready=true`와 Dimension/baseline/role/cell
  구조 gate를 통과해야 한다.
- Group을 `mod_dtm DESC, scenario_group_id DESC`로 정렬하고 ordered Event ID tuple별 최신 Group 하나만 유지한다.
- cap은 고유 Event signature에 적용한다. release 일치 Group이 더 많아도 과거 중복 Group으로 50개를 채우지 않는다.
- 선택 Group의 전체 Scenario를 read-only preflight한 뒤 runtime-capable Scenario를 우선해 대표 3개를 고정한다.
  기존 Proposal 때문에 covered인 Scenario도 재사용 testset 후보에서는 제외하지 않되 current write eligibility와 분리한다.
- `runtime-capable`, `current write-eligible`, `covered`, `coverage limit`을 별도 KPI로 기록한다.
- Parameter 종류 동일률의 분모는 3개 모두 runtime-capable인 Group이다. role coverage의 분모는 selection pool에
  baseline/floor/ceiling이 모두 있는 Group이다.
- Proposal 결과 KPI에는 `같은 종류 + Scenario별 다른 제안값`을 고정한다. 분모는 실제 Proposal이 모두 성공하고
  canonical Parameter 종류 집합이 동일한 Group이며, 순서 독립으로 정규화한 전체 Proposal value signature가 대표
  3개 Scenario 사이에서 서로 모두 다르면 변별된 것으로 판정한다. 공통 exact model slot의 값 차이는 별도 보조
  KPI로 유지한다.
- read-only 수집에서는 위 Proposal 결과 KPI를 기존 이력으로 추정하지 않고 `NOT_MEASURED_READ_ONLY`/`N/A`로
  표시한다.

이 모드는 Group/Scenario/Proposal/confirmation/callback을 생성하지 않는다. read-only preflight에는 Object Storage나
MI Base bootstrap이 필요하지 않다. 이후 같은 fixture로 Proposal을 실행하려면 별도 write 승인이 필요하며, Object
Storage 불가 시 승인된 `configured_fallback` 계약을 runner와 evaluator 양쪽에서 exact gate로 확인한다.

여기서 `read-only 수집 리포트`는 기존 DB의 Group/Scenario와 Proposal history를 조회하고 release·구조 gate,
runtime candidate, 현재 write guard 상태만 계산한 결과를 뜻한다. Proposal/LLM 실행이나 Group·Scenario·Proposal
생성, confirmation/callback, Object Storage·MI Base bootstrap은 포함하지 않는다.

최종 collection Markdown/JSON에는 `Read-only KPI`의 의미와 해석 방법을 고정한다. 이 KPI는 기존 저장 데이터와
deterministic preflight로 계산한 cohort 구성·실행 전제·coverage 지표다. collection `PASS`는 선정·release·구조·
preflight 계약 통과를 뜻하며 실제 Proposal 성공이나 제안값 품질 통과를 뜻하지 않는다. `Covered`는 기존 이력으로
현재 중복 write가 막힌 상태, `coverage limit`은 runtime 후보 부재 상태로 각각 실패와 구분한다. 실제 Proposal
성공·semantic abstention·실제 종류/값·exact-slot·token/latency는 미평가임을 명시하고, 실행 간 비교는 동일 fixture
identity·Scenario Lever/Proposal Flow release·context fingerprint에서만 수행한다.

2026-10-07 기준 reference fixture는
`tests/fixtures/model_parameter_agent/v4_1_2_existing_latest_distinct_representative_trio_40_groups_20261007.json`이며,
release 일치 60 Group 중 20개 과거 Event-signature 중복을 제외한 최신 40 Group·120 Scenario를 고정한다.

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
- structured abstention stage/reason funnel, trace 완전성, 성공/전체 시도 latency
- 동일 testset post-fix의 성공·abstention·실패·trace 개선 전후와 Scenario 시도 집합 동일성
- 표 컬럼별 의미와 비교 불가(`N/A`) 규칙
- `PASS | REVIEW | FAIL | COVERAGE LIMIT` 및 미실행 사유

기존 보고서의 PASS나 하드코딩된 Scenario ID를 현재 worktree의 증적으로 재사용하지 않는다.
