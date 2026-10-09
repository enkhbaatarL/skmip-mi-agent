---
name: model-parameter-multi-event-quality
description: MI Model Parameter Agent의 Scenario API v4 multi_event_model_lever_dimensions 그룹을 동적으로 발견하고 ordered Event, catalog version/checksum, selected Lever state와 hydrated parameter binding, runtime allowlist 경계, proposal/confirmation persistence를 통합 평가한다. v4 멀티 이벤트 품질 테스트, catalog-pinned Lever 검증, active-but-blocked leakage 진단, active parameter coverage, 동일 Scenario Before/After, expanded Event cohort, 기존 Event 풀 기반 add-only Scenario 재생성 및 기존 Scenario-only 최신 최대 50 Group 대표 3개 campaign 요청에 사용한다.
---

# Model Parameter v4 Multi-Event Quality

Scenario API v4의 선택 Dimension/Lever lineage를 active impact Lever catalog와 대조하고, 운영 matcher와 runtime allowlist 경계를 거친 실제 Model Parameter proposal flow를 평가한다. 기본 실행은 DB read-only discovery다. `--execute`는 사용자가 실제 DB write를 승인한 경우에만 사용한다.

## 필수 참조

작업 전에 다음을 읽는다.

1. `references/quality-matrix.md`: v4 판정 기준과 보고서 증적 계약
2. `tests/manual/model_parameter_agent/runner_common.py`: 공유 proposal/confirmation 실행·DB read-back 계약
3. release acceptance가 범위에 있으면 `.claude/skills/verify-model-parameter-release/SKILL.md`
4. 동일 Scenario Before/After 또는 coverage 확대 campaign이면
   `references/same-cohort-coverage-campaign.md`
5. baseline과 겹치지 않는 Event를 먼저 늘리는 Group/Proposal campaign이면
   `references/expanded-event-cohort-campaign.md`
6. 신규 Group/Scenario 생성 없이 기존 결과에서 최신 최대 50 Group의 대표 trio testset을 만들면
   `references/existing-scenario-pool-campaign.md`

공통 workflow나 release 검증 절차를 이 skill에 복제하지 않는다.

## 실행 전제조건

- runner와 automated test는 같은 Python 환경을 사용한다.
- `envs/.env`와 `APP_CONFIG`가 현재 환경에 유효해야 한다.
- discovery DB에 read 권한이 있고 v4 group/scenario/group-event, active impact Lever/master, proposal schema가 적용되어 있어야 한다.
- proposal `mi_event_id`는 nullable이어야 한다.
- 적합한 실제 v4 scenario가 없으면 결함이 아니라 `COVERAGE LIMIT`이다.
- `--execute`에는 사용자의 명시적 write 승인, 고정된 Basecase/LUT release, LLM 자격, proposal/confirmation write 권한이 필요하다.
- runtime은 승인·승격된 `resources/`만 사용하며 staging 경로인 `new_resources/`를 자동 로드하지 않는다. staging LUT가 없는 것은 정상이고, 파일이 있으면 release 식별과 승격 검증 전 live execute를 금지한다.
- 이 skill은 canonical master, impact Lever catalog, Basecase/LUT, config, workbook, DB schema를 수정하지 않는다.

운영 proposal 경계는 코드의 `MODEL_PARAMETER_PROPOSAL_ALLOWLIST`를 source of truth로 사용한다. runner에 이름 목록을 복제하지 않는다. active master에 있으나 allowlist 밖인 parameter는 `active-but-blocked`로 유지하고, `PROPOSAL_SCOPE_EXCLUDED` 증적과 함께 LLM 이전에 제외한다.

## 실행 절차

### 1. Read-only discovery

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py
```

명시 범위는 둘 중 하나만 지정한다.

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py --scenario-group-id 123
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py --scenario-id 456
```

runner는 다음을 검증한다.

- 필수 테이블/컬럼과 proposal `mi_event_id` nullable 계약
- `api_version=v4`, `generation_strategy=multi_event_model_lever_dimensions` 대상만 discovery
- exact `display_order=1..N`으로 정렬된 1~5개 Event, 중복 및 Dimension `source_event_ids` membership
- scenario group에 저장된 impact catalog version/checksum과 active catalog의 정확한 일치
- 선택 Dimension의 primary Lever code/ID/flag, `lever_states` code/ID/domain과 active catalog의 hydrated `parameter_bindings` 일치
- active master 기반 운영 v4 matcher의 raw 후보와 운영 partition 함수의 `runtime-allowed | active-but-blocked` 분리
- raw/runtime/blocked key 고유성과 disjoint/union 불변식, graph v4 raw trace의 key·canonical target 일치, Step1.5 target별 단일 canonical task와 non-empty merged lineage
- active parameter별 `raw → runtime → selected → proposed → confirmed` matrix

v3 `sourceRefs`, legacy `(event_type_l2_id, dimKey)` mapping, projection 상태는 v4 판정 근거로 사용하지 않는다.

### 2. Discovery gate

- schema, ordered Event, catalog pin, selected Lever/binding lineage 오류는 `FAIL`이며 실행을 막는다.
- 명시한 scenario/group이 v4 대상이 아니거나 없으면 `FAIL`이다.
- 자동 discovery에서 대상이 없으면 `COVERAGE LIMIT`이다.
- `runtime-allowed` raw 후보가 없는 scenario는 정상적으로 실행을 건너뛰고 coverage 한계로 기록한다.
- `active-but-blocked` 후보 자체는 오류가 아니다. runtime/selected/proposed/confirmed 누출 또는 exact reason 누락이 오류다.

### 3. Write 실행

```bash
poetry run python tests/manual/model_parameter_agent/evaluate_multi_event_quality.py \
  --scenario-group-id 123 \
  --execute
```

`--execute`는 먼저 다음 DB/LLM 독립 smoke gate를 실행한다.

```bash
python -m pytest -q -m model_parameter_core \
  tests/automated/test_model_parameter_agent_contract.py \
  tests/automated/test_model_parameter_multi_event_quality.py \
  tests/automated/test_model_parameter_runner_common.py
```

`--execute`는 반드시 `--scenario-id` 또는 `--scenario-group-id`로 write 범위를 명시해야 하며, 미지정 시 DB preflight 전에 `FAIL`한다. smoke 실패 시 proposal/confirmation을 하나도 실행하지 않고 `FAIL`한다. 통과하면 `runner_common.execute_proposal_and_confirmation()`을 scenario마다 정확히 한 번 호출한다. Scenario/DB write를 다시 수행하는 outer retry 옵션은 제공하지 않는다. Agent 내부의 bounded transient LLM retry는 별도 정책이며 attempt/retry 관측성을 남긴다. 실패 후 Scenario 재실행이 필요하면 기존 proposal ID와 실패 증적을 먼저 보존하고 사용자가 별도 실행한다.

v4 persistence의 authoritative link는 `scenario_group_id`이며 API `eventId=null`, DB `mi_event_id=NULL`이어야 한다. empty payload rollback, valid confirmation, reconfirmation, payload 보존은 공유 workflow 결과를 그대로 판정한다.

### 4. 보고서와 CLI 결과

기본 보고서는 `tests/reports/model_parameter_agent/model_parameter_v4_multi_event_quality_<timestamp_microseconds>.md`에 생성된다. `--report-path`를 지정할 수 있다. runner는 DB 작업 전에 보고서 파일을 exclusive-create하며, 같은 경로가 이미 있으면 기존 파일을 덮어쓰지 않고 중단한다.

보고서 필수 항목:

- schema와 `model_parameter_core` gate
- ordered Event와 stored→active catalog version/checksum
- selected Dimension별 source Event, Lever code/ID/direction/domain, hydrated binding
- active parameter boundary matrix와 blocked exact reason
- proposal/API/DB/confirmation 연결, partial proposal ID/failed stage, elapsed/token/retry 관측성
- semantic abstention의 structured reason/stage, Step1.5·2·3 안전 trace, 관측 완전성
- execution error와 review/coverage limit

CLI exit는 mandatory `FAIL`만 1이다. `PASS`, `REVIEW`, `COVERAGE LIMIT`는 0이다.

### 5. Proposal-only uncovered / release-replay campaign

Confirmation 없이 proposal row만 제한 실행해야 하면 quality runner의 `--execute`를 사용하지 않고 별도
uncovered-only runner를 사용한다. 기본은 read-only이며 capability release와 Group 또는 Scenario 범위를
명시한다.

```bash
python tests/manual/model_parameter_agent/run_proposal_only.py \
  --scenario-group-id 123 \
  --capability-release extend16-v8
```

명시적인 proposal write 승인 후에만 같은 명령에 `--execute`를 추가한다. 이 runner는 비삭제 proposal 전체
이력에서 `PROPOSED`/`CONFIRMED` Scenario를 skip하고, `PROCESSING`이 하나라도 있으면 campaign 전체를
hard-stop한다. lifecycle/capability skip Scenario도 history guard 범위에서 제외하지 않는다. `FAILED` 이력만
있거나 이력이 없는 실행 가능 Scenario만 대상으로 하며 write 직전에 resource/context/catalog/input fingerprint와
proposal history를 다시 판정한다. `extend16-v8`은 v4.1 full checksum, 활성 16종 allow-list와
`new-bc-v7` contract SHA, semantic schema와 실제 resource content fingerprint를 묶은 고정 계약이다. 기존 v4.0
Group 검증에는 명시적인 `extend16-v8-v4.0-compat` release를 사용한다. 각 write
직전에는 현재 Scenario뿐 아니라 명시 cohort 전체의 in-flight 상태를 다시 확인한다. Confirmation, callback,
outer retry와 임의 uncovered guard 우회는 제공하지 않는다. 단, 사용자가 같은 고정 Scenario cohort에서 새
Proposal Flow release의 결과를 전건 새로 생성하라고 명시하면 `--execute --replay-covered`를 사용할 수 있다.
이 mode는 기존 행을 갱신·삭제하지 않고 이전 `PROPOSED`만 새 release 실행 대상으로 허용하는 append-only
`release-replay-v1`이다. `CONFIRMED`는 해당 Scenario 실행을 막고 `PROCESSING`은 campaign을 hard-stop한다.
Scenario당 새 Proposal ID는 정확히 하나여야 하며, 완료 뒤 그 ID만 다시 조회한 `final_campaign_readback`을
KPI source of truth로 사용한다. 과거 blocking Proposal과 새 결과를 섞어 최신 행으로 추정하지 않는다.
구조화된 `ModelParameterSemanticEmptyError`는 일반 오류가
아닌 `ABSTAINED` attempt로 보존하고 campaign을 `REVIEW`로 판정한다. 일반 Scenario `FAIL`은 해당 Scenario에
격리해 뒤의 eligible 후보를 계속 실행하지만, resource/context/catalog/input drift, in-flight row와 persistence
integrity 위반으로 인한 `BLOCKED`는 campaign 전체를 즉시 중단한다. Step1.5/2/3 abstention은 full prompt 없이
reason/stage, 후보·slot·value 요약, sanitizer 진단과 누적 LLM call/token/retry를 남겨야 한다. 누락은 `REVIEW`다.

Group 단위 검증이 앞 Scenario 실패에서 중단된 뒤, graph 실행 횟수가 0인 뒤쪽 runtime candidate만
Scenario별로 최초 1회 실행하는 보충 실행은 test orchestration으로 명시한다. 이는 Parameter Agent 운영
Flow 변경이나 retry가 아니다. 이미 graph를 실행해 실패한 동일 Scenario는 자동 재실행하지 않는다. 확정적
코드 수정 뒤 검증 재실행은 최초 증적·수정 이유·새 revision을 보존한 `post-fix re-test`로 별도 집계한다.

read-only는 resource runtime을 bootstrap하지 않는다. `--execute`는 Scenario DB 조회 전에 resource runtime을
고정하고 실제 파일 hash와 등록된 source/schema/fingerprint를 증적한 뒤 0030 proposal schema를 검사한다. graph가
사용한 context는 persistence 직전에 frozen preflight context와 다시 비교한다. execute 증적의 runtime/schema가
미등록이거나 승인된 release contract와 다르면 fail-closed한다. DB uniqueness가 도입되기 전 write pilot은 같은
cohort에 대한 다른 runner/public proposal 요청이 없도록 운영 singleton을 별도로 보장한다.

활성 MI Base가 선택된 실행은 graph가 사용한 `case_id`, `run_seq`, role별 workbook SHA-256을 path-free identity로
남긴다. post-graph trace 보강이 Basecase를 다시 읽을 때도 같은 identity를 명시적으로 재확인하고 선택된 workbook
root/contract를 전달한다. `mi_base`와 `verified_cache` 사이의 transport source 변경은 같은 content identity일 때만
허용한다. 사용자가 Object Storage 불가 시 configured fallback을 명시한 campaign은
`active_case_unavailable_mode=configured_fallback`을 evidence에 기록하고 remote identity 관측 전 가용성 실패에만
적용한다. 이때 graph와 trace 모두 같은 configured workbook hash를 사용해야 하며, remote metadata 관측 뒤의
download/hash/contract 실패를 fallback으로 숨기면 `FAIL`이다.
Step1.5/2/3 semantic abstention도 MI Base 준비 뒤 종료되므로 예외의 안전 trace에 동일한 path-free identity를
반드시 포함한다. 이 identity가 없는 실행 evidence는 요구 fallback campaign의 관측 누락 `FAIL`로 처리하고, 다음 실행
전에 semantic abstention과 node failure source·test가 identity를 직접 전달하는지 확인한다. 추론 증적을 직접 관측으로
표기하면 `FAIL`이다.

### 6. 동일 Scenario Before/After coverage campaign

동일 cohort에서 proposal 결과만 비교하거나, Event 유형을 늘려 proposal count·coverage를 개선하는 작업은
`references/same-cohort-coverage-campaign.md` 절차를 따른다. 핵심 불변 조건은 다음과 같다.

- matcher/config만 바뀌면 Before/After의 catalog pin, Group IDs, Scenario IDs, runtime candidate IDs가 동일해야 한다.
- 사용자가 Event 입력 cohort를 고정 불변조건으로 선언하면 후속 logic/config release에서도 Event·Group·Scenario를
  재생성하거나 교체하지 않는다. 동일 저장 ID의 proposal 결과만 비교한다.
- binding catalog가 바뀌면 기존 pinned Scenario를 덮어쓰지 않는다. 동일 Scenario payload의 read-only matcher
  비교와 같은 Event cohort로 새 version Group을 생성한 end-to-end 비교를 분리해 보고한다.
- 유효 model input과 Lever Full set을 coverage를 위해 변경하지 않는다.
- 표기 차이는 Step2 LLM의 구조화된 원문 Plant/Train 근거와 server-side span/exact-target 검증으로 완화할 수
  있지만 출력은 exact model coordinate다. 동일 evidence의 복수 target 승인을 거절하고 다중 slot은 slot별
  exact 기간 근거 또는 해당 slot을 직접 포함하는 명시 연월·분기·닫힌 범위를 요구한다.
- 기본 After는 Before uncovered 후보만 Scenario별 1회 실행한다. 명시적으로 승인된 새 Flow 전건 replay는
  append-only release-replay를 사용하고, 이번 campaign의 새 Proposal ID read-back만으로 KPI를 다시 계산한다.
- 실패 원인은 error code/message 기준으로 집계하고 해결책을 연결한다. 운영 개선안은 원인 분석 뒤에 제시하며,
  Scenario별 실패 격리와 transient-only bounded retry를 semantic abstain 및 integrity fail-closed와 구분한다.
- 비교에는 `scripts/compare_same_cohort.py`를 사용하고 전체 coverage와 후보 성공률을 분리해 보고한다.
- 기존 Event 입력을 그대로 두고 Scenario Group을 추가 생성해 생성 변동성과 그룹 내 대표 Scenario 3개의
  Proposal 품질을 평가할 때는 기존 Group을 삭제하지 않는 `same_logical_inputs/add-only` cohort로 기록한다.
  모든 Scenario를 read-only preflight한 뒤 baseline·floor·ceiling 대표성을 우선하고 runtime Parameter set
  overlap을 보조 기준으로 정확히 3개를 고른다. 실행 후보가 3개 미만인 Group도 대표 ID는 3개를 유지하되
  비실행 항목을 coverage limit로 분리한다. 선정·평가는
  `tests/manual/model_parameter_agent/evaluate_representative_trios.py`를 사용한다.
- 기존 Scenario-only fixture의 **Event ID 40개만 원본 풀로 재사용해 Scenario부터 다시 만들기**를 요청하면
  `existing_event_pool/add-only-regenerated-scenarios`로 기록한다. 원본 40 Group은 삭제·수정하지 않고 Event별 새
  v4 Group을 하나씩 생성·validation·confirmation하며 Signpost는 Proposal 입력에 필요하지 않으면 생략한다.
  원본/재생성 Event ID 순서 exact 일치, Event 40개 고유성, 신규 Group 40개 순증, 원본 Group 40개 보존,
  Scenario Lever `v4.1`/Proposal Flow `v4.1.2`를 hard gate로 둔다. 이 모드는 expanded Event cohort가 아니므로
  Event 비중복이나 신규 Event 순증을 요구하지 않는다.
- 사용자가 Event cohort 확장을 먼저 요구하면 `same_logical_inputs/add-only`를 쓰지 않는다. baseline Event ID를
  exclusion set으로 고정하고 서로 다른 신규 Event 20개를 먼저 선택한 `expanded_event_cohort/add-only` campaign을
  만든다. 기존/신규 Event ID 비중복, 신규 Event 20개 고유성, Group 20개 순증과 기존 삭제 0을 hard gate로 두고,
  이후 대표 3개 선정·Proposal KPI·fixture export는 같은 evaluator를 사용한다. 동일 Event를 재생성한 증적은
  audit evidence로만 보존하고 최종 입력에서 제외한다.
- 사용자가 **신규 Scenario 생성 없이 기존 Scenario만** 요구하면 Group create/validation/confirmation을 호출하지
  않는다. exact v4/v4.1 release 계약과 구조 gate를 통과한 Group을 `mod_dtm DESC, scenario_group_id DESC`로
  정렬하고, ordered Event ID 조합별 최신 Group 하나만 남긴 뒤 최대 50개로 제한한다. release 일치 Group 수와
  고유 ordered Event 조합 수가 다르면 과거 중복 Group을 채우기용 표본으로 다시 넣지 않는다.
- 기존 Scenario-only testset은 선택한 Group의 **전체 Scenario**를 read-only preflight한 뒤 Group당 3개를 고른다.
  재사용 가능성은 runtime candidate 존재 여부로 판정하고 기존 Proposal history의 covered 상태는 선택 탈락 사유로
  쓰지 않는다. `runtime-capable`, `current write-eligible`, `covered`, `coverage limit`을 서로 다른 필드/KPI로 남긴다.
  이 모드는 `tests/manual/model_parameter_agent/collect_existing_representative_trios.py`를 사용한다.
- 기존 Scenario-only fixture는 release pin, ordered Group/Event/Scenario identity와 context fingerprint snapshot을
  고정하고 runtime 후보·covered 상태는 collection-time 관측값으로 분리한다. 고유 Event signature·최신 revision은
  100% gate이며 Parameter type 동일률의 분모는 3개 모두 runtime-capable인 Group, role coverage 분모는 selection
  pool에 baseline/floor/ceiling이 모두 존재하는 Group으로 둔다.
- 대표 3개 KPI는 Proposal 성공률과 identity/integrity뿐 아니라 (1) 세 Proposal의 canonical Parameter type set
  동일률, (2) 동일 type에서 순서 독립으로 정규화한 전체 proposed value signature가 대표 3개 모두 서로 다른 비율,
  (3) exact model slot이 공통인 경우 그 slot의 값 변별률을 분리한다. 세 Proposal이 모두 성공한 Group만 type/value
  비교 분모에 넣고 실패·abstain은 숨기지 않는다.
- 중단·재개로 비중복 execution evidence가 여러 개면 evaluator에 `--execution-evidence`를 반복한다. release identity
  mismatch나 같은 Scenario attempt 중복은 자동 병합하지 않는다. 코드 수정 뒤 같은 고정 Scenario를 다시 실행한
  증적만 `--post-fix-execution-evidence`와 필수 `--post-fix-reason`으로 명시 교체하며, 원 attempt의 source/status/
  semantic stage를 audit에 보존한다. 사용자가 최종 cohort 재사용을 요청하면 Proposal 실행 **전에** evaluator의
  `freeze` 명령으로 tracked `tests/fixtures/model_parameter_agent/` fixture를 최초 1회 생성하고 덮어쓰기를 금지한다.
  이후에는 `--testset-input`으로 SHA-256과 ordered
  Group/Event/Scenario ID를 plan과 exact 대조한다. 고정 cohort/contract와 변동 가능한 관측 KPI baseline을 분리한다.
  post-fix 보고서는 baseline/final Scenario attempt ID 집합 동일성을 hard gate로 두고 성공, semantic abstention,
  기타 실패, structured/complete trace의 전후 값과 증감을 함께 표시한다.
  특정 MI Base fallback이 campaign 계약이면 runner의 `--require-mi-base-fallback-mode`와 evaluator의
  `--expected-mi-base-fallback-mode`를 같은 값으로 지정한다. 증적 파일명으로 fallback 적용을 추정하지 않는다.
- 실행 attempt Scenario ID 집합은 고정 testset의 proposal-eligible ID 집합과 정확히 같아야 하며 preflight skip ID를
  실행하면 `FAIL`이다. 최종 DB read-back도 건수뿐 아니라 covered/uncovered/skip Scenario ID 집합과 Group identity를
  exact 대조한다.
- Live Proposal campaign의 최종 DB read-back은 평가 대상 Proposal row의 `proposal_parameters`를 함께 스냅샷해야 한다.
  release-replay에서는 `final_campaign_readback`의 신규 ID만 평가 대상으로 삼는다.
  공식 KPI는 매 release마다 고정 cohort 전체를 새로 실행한 live clean campaign의 신규 ID만으로 계산한다.
  이전 campaign의 Scenario별 성공/미제안 전이는 원인 분석용 관측값이며, 과거 성공 Scenario를 개별 복구하거나
  같은 결과가 나오도록 강제하는 release gate로 사용하지 않는다. post-fix 부분 재실행은 명시 요청이 있을 때의
  진단 증적일 뿐 공식 live clean KPI와 합치지 않는다.
  완료 시 `evaluate_representative_trios.py final-cohort`로 고정 testset 전체를 다시 평가해 (1) full-trio Parameter
  type set, (2) 세 Scenario의 전체 proposed-value signature, (3) scalar exact common slot 값 차이와 PowerMix
  atomic-vector 차이, (4) slot별 명시적 rationale 완전성을 Markdown/JSON에 자동 생성한다. Proposal payload 누락,
  동일 Scenario의 campaign row 중복,
  fixture/history scope·Group identity 불일치는 fail-closed다.
- 같은 최종 Report는 미제안·실패를 Scenario Group/Event, 중단 단계, reason code, 확정 가능한 Parameter별로 자동
  집계하고 hotspot별 개선안과 hallucination 방지 경계를 함께 기록한다. `ABSTAINED`, 기술 실패, capability limit은
  서로 섞지 않으며 Step1.5에서 Parameter가 확정되지 않은 사례를 개별 후보 Parameter 실패로 과대 집계하지 않는다.
- `full-trio success`는 고정 Group의 대표 Scenario 3개 모두가 해당 live clean campaign에서 신규 Proposal row를
  저장하고, DB read-back payload에 하나 이상의 유효 value cell을 가진 상태다. 세 Scenario 중 하나라도 semantic
  abstention, 기술 실패, capability limit 또는 payload 결손이면 해당 Group은 full-trio가 아니다. Parameter 종류
  동일성과 값 변별은 full-trio 이후에 계산하는 별도 KPI다.
- 공식 live campaign Report는 `최종 DB 기준 Trio Parameter·값 변별` 섹션이 없으면 미완료다. `evaluate`에
  `--testset-input`과 `--final-history-evidence`를 함께 주면 이 섹션을 본문에 자동 부착한다. 실행 증적이 여러 조각이거나
  기존 covered Proposal과 신규 Proposal이 섞인 campaign은 최종 DB read-back을 source of truth로 삼아 별도
  `final-cohort` Report를 생성하고 본문에서 링크·수치를 반영한다. 수동으로 성공 건수만 옮겨 적어 대신하지 않는다.
- Markdown 그룹 표는 triple-success가 아닌 종류/값/exact-slot 지표를 `N/A`로 표시한다. `Read-only KPI`는 핵심
  7개 안팎으로 압축하고 `runtime-capable`, `current write eligible`, `covered`, `coverage limit`을 고정 설명한다.
  `Proposal 결과 KPI`, 그룹 표, post-fix 비교 표의 컬럼 정의도 고정 섹션으로 포함한다. KPI 개선안은 새 지표 제안이
  아니라 Proposal 성공률·triple-success·종류 동일성·Scenario별 값 변별 등 **기존 KPI를 높이는 실행 아이디어**로 쓴다.
- evidence schema v6 이상인 공식 Report에는 실행 시점의 전체 `model_parameter_*` runtime effective 값,
  로컬 `envs/config.yaml`, Neuro `devops/k8s/configmap.yaml` 선언값·SHA와 차이를 자동 포함한다. secret-valued
  항목은 값과 key를 증적에서 제외하거나 마스킹한다. config snapshot이 빠진 Report는 완료로 처리하지 않는다.
- v4.1.2 proposal-only frozen-context 검사는 persisted Scenario/Event/Group drift를 fail-closed로 유지하되,
  graph 실행 중 최상위에 추가되는 request-local `mi_base_case_id` pin은 Scenario mutation으로 분류하지 않는다.
  다른 context 차이는 persistence 전에 계속 차단한다.
- logic/config 변경은 `rollout-model-parameters`, release 검증은 `verify-model-parameter-release`, 배포는
  `mi-vm-deploy`에 handoff한다. 이 quality mode 자체가 DB binding/config를 임의 수정하지 않는다.

## Release gate

release acceptance까지 요청받으면 이 보고서의 mandatory `FAIL`이 0인지 먼저 확인한 뒤 `verify-model-parameter-release`를 사용한다. canonical fixture, LUT startup/guard, YAML/Kubernetes parity, Excel/archive, 전체 regressions, transactional DB 및 static SQL idempotency/rollback은 release skill 범위다.

## 안전 규칙

- 기본 모드에서 graph, callback, confirmation을 호출하지 않는다.
- `--execute` 전 preflight 또는 automated gate 실패가 하나라도 있으면 모든 live write를 막는다.
- unscoped read-only discovery만 허용하고 unscoped `--execute`는 DB 접속 전에 차단한다.
- 기존 보고서 경로는 덮어쓰지 않으며 보고서 예약 실패도 DB 접속 전에 차단한다.
- write-producing Scenario workflow를 자동 retry하지 않는다. 내부 LLM retry는 timeout·transport·HTTP
  408/425/429/5xx로 제한하고 semantic/schema/좌표/integrity 오류에는 적용하지 않는다.
- catalog checksum, Lever ID/binding, group Event membership 오류를 경고로 낮추지 않는다.
- valid but unmapped/non-executable catalog state는 reason code와 함께 coverage 증적으로 보존한다.
- 보고서에 비밀값, DB 자격증명, 전체 prompt 원문을 기록하지 않는다.
- 이 품질 실행에서 production config, catalog, master, Basecase/LUT, workbook, schema, confirmation workflow를 변경하지 않는다.
- `new_resources/`의 user-owned staging 파일을 수정하거나 runtime source로 간주하지 않는다.
